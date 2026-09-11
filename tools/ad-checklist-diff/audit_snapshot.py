"""Remember each app's last audit so a re-run can report only what changed.

A scheduled audit that re-prints all 76 rows every time is noise: nobody reads
it, so nobody notices the one row that broke. What matters between runs is the
delta -- rows that started failing, rows that got fixed, and ad unit IDs the
build started using.

Snapshots are keyed by package and carry the build's `versionCode`, which is
also the cheap test for "is there anything new to audit at all": same build,
same APK, same answer.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DIR = Path(__file__).parent / "snapshots"


def snapshot_path(package: str, directory: Path | str = DEFAULT_DIR) -> Path:
    return Path(directory) / f"{package}.json"


def save(package: str, result: dict, version_code: str | None, directory=DEFAULT_DIR) -> Path:
    path = snapshot_path(package, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "package": package,
        "version_code": version_code,
        "audited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "result": result,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load(package: str, directory=DEFAULT_DIR) -> dict | None:
    path = snapshot_path(package, directory)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _rows_by_value(result: dict) -> dict[str, dict]:
    return {
        row["value"]: row
        for rows in result.get("sections", {}).values()
        for row in rows
    }


def diff_results(old: dict | None, new: dict) -> dict:
    """What changed between two audits of the same app.

    A first run has no baseline, so everything failing is reported as newly
    broken -- which is correct for a first look, and quiet from then on.
    """
    old_rows = _rows_by_value(old.get("result", {})) if old else {}
    new_rows = _rows_by_value(new)

    broke, fixed, appeared = [], [], []
    for value, row in new_rows.items():
        was = old_rows.get(value)
        if not row["found"] and (was is None or was["found"]):
            broke.append({"label": row["label"], "value": value, "note": row.get("note")})
        elif row["found"] and was is not None and not was["found"]:
            fixed.append({"label": row["label"], "value": value})
        elif value not in old_rows:
            appeared.append({"label": row["label"], "value": value})

    gone = [
        {"label": row["label"], "value": value}
        for value, row in old_rows.items()
        if value not in new_rows
    ]
    old_ids = set((old or {}).get("result", {}).get("leftover_ids", []))
    new_leftover = sorted(set(new.get("leftover_ids", [])) - old_ids)

    return {
        "broke": broke,
        "fixed": fixed,
        "rows_added": appeared,
        "rows_removed": gone,
        "new_leftover_ids": new_leftover,
        "changed": bool(broke or fixed or appeared or gone or new_leftover),
    }


# How an unmatched row should be read, so an agent (or a person) spends
# attention only where the tool genuinely cannot decide.
NOT_IN_BUILD = "không có trong build"
NO_LOG_EVIDENCE = "chưa thấy trong log"
OTHER = "khác"


def triage(result: dict) -> dict[str, list[dict]]:
    """Group unmatched rows by what kind of answer each one needs."""
    buckets: dict[str, list[dict]] = {NOT_IN_BUILD: [], NO_LOG_EVIDENCE: [], OTHER: []}
    for section, rows in result.get("sections", {}).items():
        for row in rows:
            if row["found"]:
                continue
            note = row.get("note") or ""
            if "không tìm thấy ID này trong APK" in note.lower() or "không tìm thấy id này trong apk" in note.lower():
                bucket = NOT_IN_BUILD
            elif "không thấy" in note.lower():
                bucket = NO_LOG_EVIDENCE
            else:
                bucket = OTHER
            buckets[bucket].append(
                {"section": section, "label": row["label"], "value": row["value"], "note": row.get("note")}
            )
    return buckets
