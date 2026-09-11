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
import os
import sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from apk_source import apk_ad_ids, base_apk, cache_path, device_version_code
from app_registry import DEFAULT_REGISTRY, load_apps, registry_sheet, sheet_url_for
from audit_pipeline import run_audit
from audit_snapshot import diff_results, load, save, triage
from check_ads import DEFAULT_FILTERS
from device_driver import capture_session
from device_flow import DEFAULT_HOME_MATCH

DEFAULT_OUT_DIR = Path(__file__).parent / "out"


def unsettled_rows(triage_path: Path) -> int | None:
    """How many rows the tool could not settle by itself.

    None means there is no triage yet -- which is not the same as zero, and the
    agent layer has to tell the two apart before deciding it has nothing to do.
    """
    if not triage_path.exists():
        return None
    payload = json.loads(triage_path.read_text(encoding="utf-8"))
    return sum(len(rows) for rows in payload.get("triage", {}).values())


def audit_one(
    app: dict,
    base_sheet: str,
    *,
    out_dir: Path,
    force: bool = False,
    capture_log: str | None = None,
    missed_home: list[str] | None = None,
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
        return {
            "package": package,
            "label": label,
            "skipped": "build chưa đổi",
            "version_code": version_code,
            "unsettled": unsettled_rows(out_dir / f"{package}-triage.json"),
        }

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
        # Kể cả lượt APK-only cũng cắm máy (versionCode đọc từ dumpsys, APK pull
        # về qua adb), nên `pm list packages` luôn trả lời được. Trước đây cờ này
        # tắt theo việc "có capture hay không", làm dòng Package name bị báo lệch
        # ở mọi lượt APK-only dù app đang cài ngay trên máy.
        use_device=True,
    )

    delta = diff_results(previous, result)
    save(package, result, version_code, **snap_kwargs)

    out_dir.mkdir(parents=True, exist_ok=True)
    # Distinct from the snapshot's own `<package>.json`: pointing both at one
    # directory would otherwise have the triage overwrite the baseline, and the
    # next run would see no history at all.
    triage_rows = triage(result)
    triage_path = out_dir / f"{package}-triage.json"

    # Câu hỏi agent hay hỏi nhất về APK là "ID này có trong build không". Quét
    # một lần ở đây mất 0.4s; để agent tự quét thì nó viết lại đoạn zipfile ấy
    # mỗi lượt, chậm hơn hàng trăm lần và thường quên mất dex lưu cả UTF-16LE.
    cached_apk = cache_path(package, version_code) if version_code else None
    build_ad_ids = (
        sorted(apk_ad_ids(cached_apk))
        if cached_apk and os.path.exists(cached_apk)
        else None
    )
    triage_path.write_text(
        json.dumps(
            {
                # Ai đọc triage về sau -- người hay agent -- không có cách nào
                # biết lượt capture sinh ra nó đã đi tới đâu, nên bối cảnh phải
                # nằm ngay trong file. `missed_home` là None khi lượt đó không
                # capture gì cả, khác hẳn với [] nghĩa là mọi luồng đều tới nơi.
                "package": package,
                "version_code": version_code,
                "audited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "capture_log": capture_log,
                "missed_home": missed_home,
                "build_ad_ids": build_ad_ids,
                "delta": delta,
                "triage": triage_rows,
                "empty_filters": empty_filters,
            },
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
        "unsettled": sum(len(rows) for rows in triage_rows.values()),
    }


def capture_and_audit(
    app: dict,
    base_sheet: str,
    *,
    out_dir: Path,
    force: bool = False,
    serial: str | None = None,
    timeout: int = 300,
    snapshots_dir=None,
) -> dict:
    """Device lane for one app: drive the phone, then audit against that capture.

    The APK alone cannot answer every row -- the "Thông số kỹ thuật" section only
    shows up in a log -- so this is the fuller audit, at the cost of needing the
    one phone to itself.
    """
    package = app["package"]
    label = app.get("label") or package

    # The skip has to happen *before* the capture, otherwise the phone spends
    # minutes producing a log that `audit_one` would then decline to look at.
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

    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"{package}-capture.log"
    splash_tap = app.get("splash_tap")
    passes = capture_session(
        package,
        str(log_path),
        serial=serial,
        timeout=timeout,
        home_match=app.get("home_match") or DEFAULT_HOME_MATCH,
        tap_xy=tuple(splash_tap) if splash_tap else None,
    )

    missed_home = [p["pass"] for p in passes if not p["reached_home"]]

    # Already decided to run above; `force` here only stops the second skip check.
    summary = audit_one(
        app,
        base_sheet,
        out_dir=out_dir,
        force=True,
        capture_log=str(log_path),
        missed_home=missed_home,
        snapshots_dir=snapshots_dir,
    )
    summary["capture_log"] = str(log_path)
    summary["missed_home"] = missed_home
    return summary


def run_all(
    apps: list[dict],
    base_sheet: str,
    *,
    out_dir: Path = DEFAULT_OUT_DIR,
    force: bool = False,
    workers: int = 4,
    capture: bool = False,
    serial: str | None = None,
    timeout: int = 300,
    snapshots_dir=None,
) -> list[dict]:
    """Audit every app. APK-only work is parallel -- no device is involved.

    A capture drives the one phone, so that lane runs one app after another no
    matter what `workers` says.
    """
    def work(app):
        try:
            if capture:
                return capture_and_audit(
                    app,
                    base_sheet,
                    out_dir=out_dir,
                    force=force,
                    serial=serial,
                    timeout=timeout,
                    snapshots_dir=snapshots_dir,
                )
            return audit_one(app, base_sheet, out_dir=out_dir, force=force, snapshots_dir=snapshots_dir)
        except SystemExit as e:  # pipeline signals user-facing errors this way
            return {"package": app["package"], "error": str(e)}

    if capture:
        return [work(app) for app in apps]

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(apps) or 1))) as pool:
        return list(pool.map(work, apps))


def _unsettled_note(result: dict) -> str:
    """The one thing the agent layer needs from the summary, in a fixed shape.

    Printed for every app, skipped ones included: a skip leaves the previous
    triage standing, and whether that triage still holds rows is exactly what
    decides if an agent has any work here.
    """
    count = result.get("unsettled")
    return "" if count is None else f" | chưa kết luận: {count}"


def print_summary(results: list[dict]) -> None:
    for r in results:
        name = r.get("label") or r["package"]
        if r.get("error"):
            print(f"  [lỗi]  {name}: {r['error']}")
        elif r.get("skipped"):
            print(
                f"  [bỏ]   {name}: {r['skipped']} "
                f"(versionCode {r.get('version_code')}){_unsettled_note(r)}"
            )
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
            print(f"  [{r['score']}] {name}: {state}{_unsettled_note(r)}")
            if r.get("missed_home"):
                # A journey that never reached Home captured less than it should
                # have, so its "chưa thấy trong log" rows are not evidence of a bug.
                print(f"         luồng chưa tới Home: {', '.join(r['missed_home'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit toàn bộ app trong registry")
    parser.add_argument(
        "--sheet",
        help="URL sheet gốc (gid lấy từ registry). Bỏ qua nếu registry đã khai \"sheet\"",
    )
    parser.add_argument("--registry", help="apps.json (mặc định cạnh file này)")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--force", action="store_true", help="Chạy cả khi versionCode chưa đổi")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Tự lái máy capture log cho từng app (tuần tự, cần device); mặc định chỉ đọc APK",
    )
    parser.add_argument("--serial", help="adb serial, khi cắm nhiều máy")
    parser.add_argument("--timeout", type=int, default=300, help="Giới hạn mỗi luồng khi capture, giây")
    args = parser.parse_args()

    registry = args.registry or DEFAULT_REGISTRY
    apps = load_apps(registry)
    # The registry already says which tab each app is; letting it say which
    # spreadsheet too is what stops the URL being retyped every run and kept in
    # step by hand wherever the audit is scheduled.
    sheet = args.sheet or registry_sheet(registry)
    if not sheet:
        raise SystemExit(
            f'Thiếu URL sheet: truyền --sheet, hoặc thêm "sheet" vào {registry} '
            "(xem apps.example.json)"
        )

    results = run_all(
        apps,
        sheet,
        out_dir=Path(args.out),
        force=args.force,
        workers=args.workers,
        capture=args.capture,
        serial=args.serial,
        timeout=args.timeout,
    )
    print_summary(results)

    if any(r.get("error") for r in results):
        return 1
    return 2 if any(r.get("delta", {}).get("broke") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
