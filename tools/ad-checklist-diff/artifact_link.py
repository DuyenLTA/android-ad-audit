"""Remember the claude.ai artifact URL that the report file was published to.

The report cannot publish itself: creating an artifact is a Claude Code action
inside a chat turn, and a headless `claude -p` run has no Artifact tool at all
(verified -- `select:Artifact` resolves to nothing there). What *is* stable is
the URL: republishing the same file path updates the same artifact in place.

So the report is written to one fixed path, published once, and the resulting
URL recorded here. From then on the GUI's button opens the shareable artifact
instead of the local page, and Claude republishing that path refreshes it
without the link ever changing.

`published_at` is compared against the report file's mtime so the GUI can say
when the artifact is older than the run just finished.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LINK_FILE = Path(__file__).parent / "artifact-link.json"


def read_link(link_file: Path | None = None) -> dict | None:
    """The recorded artifact URL, or None if the report was never published."""
    link_file = link_file or LINK_FILE
    try:
        data = json.loads(link_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if data.get("url") else None


def write_link(url: str, link_file: Path | None = None) -> dict:
    """Record the artifact URL the report path is published to."""
    link_file = link_file or LINK_FILE
    data = {"url": url, "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    link_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def is_stale(link: dict, report_path: Path) -> bool:
    """True when the report on disk is newer than the published artifact."""
    published_at = link.get("published_at")
    if not published_at or not report_path.exists():
        return False
    try:
        published = datetime.fromisoformat(published_at)
    except ValueError:
        return False
    report_mtime = datetime.fromtimestamp(os.path.getmtime(report_path), timezone.utc)
    return report_mtime > published


if __name__ == "__main__":
    # `python artifact_link.py <url>` -- how Claude records the URL after
    # publishing the report file.
    if len(sys.argv) != 2:
        raise SystemExit("usage: python artifact_link.py <artifact-url>")
    print(write_link(sys.argv[1]))
