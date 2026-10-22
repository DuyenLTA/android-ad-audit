"""What happens after a report is published: Discord notices and the usage-log row.

`artifact_link.py` calls `announce()` once the URL is recorded. The counts the
agent layer settled (confirmed / disputed / unresolved) exist nowhere on disk by
themselves, so the agent hands them over in a small JSON file:

    {"confirmed": [{"value": "ca-app-pub-.../123", "placement": "Home"}],
     "disputed": 1, "unresolved": 0}

`disputed` / `unresolved` may be a count or a list. Without the file, only what
the triage JSON knows (rows the tool could not settle) is reported.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import discord_notify

TOOL_DIR = Path(__file__).parent
REPO_ROOT = TOOL_DIR.parent.parent
USAGE_LOG = REPO_ROOT / "docs" / "usage-log.md"
MAX_BUG_ROWS = 10
MANUAL_MINUTES = 30


def _count(value) -> int:
    return len(value) if isinstance(value, (list, tuple)) else int(value or 0)


def read_triage_meta(package: str, out_dir: Path | None = None) -> dict:
    """version_code and rows left unsettled, or {} when no triage exists."""
    path = (out_dir or TOOL_DIR / "out") / f"{package}-triage.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    unsettled = sum(len(rows) for rows in payload.get("triage", {}).values())
    return {"version_code": payload.get("version_code"), "unsettled": unsettled}


def read_findings(path: str | Path | None) -> dict | None:
    """Agent-written counts; None when absent or unreadable (never fatal)."""
    if not path:
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return {
            "confirmed": [r for r in data.get("confirmed", []) if isinstance(r, dict)],
            "disputed": _count(data.get("disputed")),
            "unresolved": _count(data.get("unresolved")),
        }
    except (OSError, ValueError, AttributeError, TypeError):
        return None


def append_usage_log(package: str, vc, url: str, findings: dict | None, unsettled: int | None,
                     log_path: Path | None = None, today: datetime | None = None) -> bool:
    """Add one row after the table's last row. False when skipped (no table, duplicate)."""
    log_path = log_path or USAGE_LOG
    try:
        lines = log_path.read_text(encoding="utf-8").split("\n")
    except OSError:
        return False
    rows = [i for i, line in enumerate(lines) if line.startswith("|")]
    if not rows or any(url in line for line in lines):  # same publish recorded twice
        return False
    if findings:
        confirmed = len(findings["confirmed"])
        result = f"{confirmed} xác nhận, {findings['disputed']} tranh chấp, {findings['unresolved']} chưa chốt"
        confirmed_cell = str(confirmed)
    else:
        result = "Sạch" if unsettled == 0 else (f"{unsettled} dòng chưa kết luận" if unsettled else "?")
        confirmed_cell = "?"
    date = (today or datetime.now()).strftime("%d/%m/%Y")
    # Tool time is not recorded by the runner, so the saving cannot be computed.
    row = (f"| {date} | {package} | {vc or '?'} | {result} | {confirmed_cell} | "
           f"[artifact]({url}) | ? | {MANUAL_MINUTES} phút | ? |")
    lines.insert(rows[-1] + 1, row)
    log_path.write_text("\n".join(lines), encoding="utf-8")
    return True


def announce(package: str, url: str, findings_path: str | Path | None = None,
             out_dir: Path | None = None, log_path: Path | None = None) -> None:
    """One Discord message (link attached once) and the usage-log row. Never raises.

    Everything the run settled goes into a single message: separate done / bug /
    needs-review messages each carried the same link and read as noise in the
    channel. Confirmed rows switch it to the `bug` kind so the ads-team mention fires.
    """
    try:
        meta = read_triage_meta(package, out_dir)
        findings = read_findings(findings_path)
        vc = meta.get("version_code")
        lines = []
        if findings:
            lines.append(f"Xác nhận: {len(findings['confirmed'])}, tranh chấp: {findings['disputed']}, "
                         f"chưa chốt: {findings['unresolved']}")
            needs_review = findings["disputed"] + findings["unresolved"]
        else:
            needs_review = meta.get("unsettled") or 0
            if "unsettled" in meta:
                lines.append(f"Dòng chưa kết luận (triage): {meta['unsettled']}")
        confirmed = findings["confirmed"] if findings else []
        if confirmed:
            rows = confirmed[:MAX_BUG_ROWS]
            lines += [f"{r.get('value', '?')} · {r.get('placement', '?')}" for r in rows]
            extra = len(confirmed) - len(rows)
            if extra > 0:
                lines.append(f"… và {extra} dòng nữa")
        if needs_review:
            lines.append(f"Cần người xem lại: {needs_review} dòng")
        if confirmed:
            kind, title = "bug", f"Lỗi checklist xác nhận · {package} vc{vc or '?'}"
            action = "Ads team xác nhận và sửa sheet / log Jira"
        else:
            kind, title = "done", f"Report đã publish · {package} vc{vc or '?'}"
            action = "Xem report rồi quyết từng dòng" if needs_review else None
        discord_notify.send(kind, title, lines, action=action, link=url)
        append_usage_log(package, vc, url, findings, meta.get("unsettled"), log_path)
    except Exception as e:  # noqa: BLE001 -- bookkeeping must not fail the publish step
        print(f"publish_notice: bỏ qua ({type(e).__name__}: {e})", file=sys.stderr)
