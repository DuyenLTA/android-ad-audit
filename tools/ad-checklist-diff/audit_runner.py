"""Audit every app in the registry, skipping builds already audited.

The fan-out layer. Two things decide how much work a run does:

- **versionCode.** Same build as the last snapshot means the APK is byte-for-
  byte what was already checked, so the app is skipped unless `--force`.
- **Whether a capture is wanted.** APK-only audits touch no device, so they run
  in parallel across apps. A capture drives a phone, and there is one phone, so
  those run one after another.

Output per app: a snapshot, a delta against the previous one, and a triage of
the rows the tool cannot settle by itself -- the short list worth a human's or
an agent's attention.
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from apk_source import base_apk, device_version_code
from app_registry import load_apps, sheet_url_for
from audit_pipeline import run_audit
from audit_snapshot import diff_results, load, save, triage
from check_ads import DEFAULT_FILTERS

DEFAULT_OUT_DIR = Path(__file__).parent / "out"


def audit_one(
    app: dict,
    base_sheet: str,
    *,
    out_dir: Path,
    force: bool = False,
    capture_log: str | None = None,
    snapshots_dir=None,
) -> dict:
    """Audit a single app; returns a summary dict (never raises for one app)."""
    package = app["package"]
    label = app.get("label") or package
    sheet = sheet_url_for(base_sheet, app["gid"])
    snap_kwargs = {"directory": snapshots_dir} if snapshots_dir else {}

    version_code = device_version_code(package)
    previous = load(package, **snap_kwargs)
    if (
        not force
        and previous
        and version_code
        and previous.get("version_code") == version_code
    ):
        return {"package": package, "label": label, "skipped": "build chưa đổi", "version_code": version_code}

    apk_path = None
    if not capture_log:
        apk_path, _ephemeral = base_apk(package)
        if not apk_path:
            return {"package": package, "label": label, "error": "không lấy được APK (máy chưa cắm / app chưa cài)"}

    result, empty_filters = run_audit(
        sheet,
        DEFAULT_FILTERS,
        log_path=capture_log,
        package=package,
        apk_path=apk_path,
        use_device=capture_log is not None,
    )

    delta = diff_results(previous, result)
    save(package, result, version_code, **snap_kwargs)

    out_dir.mkdir(parents=True, exist_ok=True)
    # Distinct from the snapshot's own `<package>.json`: pointing both at one
    # directory would otherwise have the triage overwrite the baseline, and the
    # next run would see no history at all.
    triage_path = out_dir / f"{package}-triage.json"
    triage_path.write_text(
        json.dumps(
            {"delta": delta, "triage": triage(result), "empty_filters": empty_filters},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    total = sum(len(rows) for rows in result["sections"].values())
    matched = sum(1 for rows in result["sections"].values() for r in rows if r["found"])
    return {
        "package": package,
        "label": label,
        "version_code": version_code,
        "score": f"{matched}/{total}",
        "missing": total - matched,
        "delta": delta,
        "triage_path": str(triage_path),
    }


def run_all(
    apps: list[dict],
    base_sheet: str,
    *,
    out_dir: Path = DEFAULT_OUT_DIR,
    force: bool = False,
    workers: int = 4,
) -> list[dict]:
    """Audit every app. APK-only work is parallel -- no device is involved."""
    def work(app):
        try:
            return audit_one(app, base_sheet, out_dir=out_dir, force=force)
        except SystemExit as e:  # pipeline signals user-facing errors this way
            return {"package": app["package"], "error": str(e)}

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(apps) or 1))) as pool:
        return list(pool.map(work, apps))


def print_summary(results: list[dict]) -> None:
    for r in results:
        name = r.get("label") or r["package"]
        if r.get("error"):
            print(f"  [lỗi]  {name}: {r['error']}")
        elif r.get("skipped"):
            print(f"  [bỏ]   {name}: {r['skipped']} (versionCode {r.get('version_code')})")
        else:
            delta = r["delta"]
            flags = []
            if delta["broke"]:
                flags.append(f"{len(delta['broke'])} dòng mới lệch")
            if delta["fixed"]:
                flags.append(f"{len(delta['fixed'])} dòng đã fix")
            if delta["new_leftover_ids"]:
                flags.append(f"{len(delta['new_leftover_ids'])} ID lạ mới")
            state = ", ".join(flags) if flags else "không đổi"
            print(f"  [{r['score']}] {name}: {state}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit toàn bộ app trong registry")
    parser.add_argument("--sheet", required=True, help="URL sheet gốc (gid lấy từ registry)")
    parser.add_argument("--registry", help="apps.json (mặc định cạnh file này)")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--force", action="store_true", help="Chạy cả khi versionCode chưa đổi")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    apps = load_apps(args.registry) if args.registry else load_apps()
    results = run_all(
        apps, args.sheet, out_dir=Path(args.out), force=args.force, workers=args.workers
    )
    print_summary(results)

    if any(r.get("error") for r in results):
        return 1
    return 2 if any(r.get("delta", {}).get("broke") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
