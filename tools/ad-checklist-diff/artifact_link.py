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

Each audited app has its own artifact, so those URLs are kept per package in
`artifact-links.json`. Without that record a later run has no way to know an app
already has a page, and publishes a second one -- the shared link people already
have then quietly stops being the current report.
"""
import argparse
import json
import os
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

LINK_FILE = Path(__file__).parent / "artifact-link.json"
LINKS_FILE = Path(__file__).parent / "artifact-links.json"


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


def read_app_links(links_file: Path | None = None) -> dict:
    """Every app's artifact URL, keyed by package."""
    links_file = links_file or LINKS_FILE
    try:
        return json.loads(links_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_app_link(package: str, links_file: Path | None = None) -> str | None:
    """The page this app already has, so a rerun updates it instead of forking."""
    return (read_app_links(links_file).get(package) or {}).get("url")


def write_app_link(package: str, url: str, links_file: Path | None = None) -> dict:
    links_file = links_file or LINKS_FILE
    links = read_app_links(links_file)
    links[package] = {
        "url": url,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    links_file.write_text(
        json.dumps(links, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return links[package]


def open_in_browser(url: str) -> bool:
    """Open the page. False when there is no browser to open it in."""
    try:
        return webbrowser.open(url)
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Ghi / mở link artifact")
    parser.add_argument("url", nargs="?", help="URL vừa publish")
    parser.add_argument("--package", help="ghi link cho riêng app này")
    parser.add_argument("--show", action="store_true", help="in link đã lưu")
    parser.add_argument("--open", action="store_true", help="mở link trong trình duyệt")
    args = parser.parse_args()

    if args.package:
        if args.url:
            write_app_link(args.package, args.url)
        url = args.url or read_app_link(args.package)
        if not url:
            raise SystemExit(f"Chưa có link nào cho {args.package}")
        print(url)
        if args.open and not open_in_browser(url):
            print("Không mở được trình duyệt ở máy này.", file=sys.stderr)
        return

    if args.show:
        link = read_link()
        print(link["url"] if link else "(chưa publish lần nào)")
        return
    if not args.url:
        raise SystemExit("usage: python artifact_link.py [--package <pkg>] <artifact-url>")
    print(write_link(args.url))


if __name__ == "__main__":
    main()
