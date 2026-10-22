"""Remember the claude.ai artifact URL that each app's report was published to.

The report cannot publish itself: creating an artifact is a Claude Code action
inside a chat turn, and a headless `claude -p` run has no Artifact tool at all
(verified -- `select:Artifact` resolves to nothing there). What *is* stable is
the URL: republishing the same file path updates the same artifact in place.

Each audited app has its own artifact, so those URLs are kept per package in
`artifact-links.json`. Without that record a later run has no way to know an app
already has a page, and publishes a second one -- the shared link people already
have then quietly stops being the current report.

Recording a URL does not open a browser: the Discord notice sent by
`publish_notice.announce` carries the link, and that is where people pick it up.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import publish_notice
from console_encoding import use_utf8_console

LINKS_FILE = Path(__file__).parent / "artifact-links.json"


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Ghi / tra link artifact")
    parser.add_argument("url", nargs="?", help="URL vừa publish")
    parser.add_argument("--package", required=True, help="app cần ghi / tra link")
    parser.add_argument("--show", action="store_true", help="in link đã lưu")
    parser.add_argument(
        "--findings-json",
        help="JSON agent ghi: confirmed [{value, placement}], disputed, unresolved -- cho thông báo Discord + usage-log",
    )
    # No-ops kept so callers written when recording a link opened the browser still parse.
    parser.add_argument("--open", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-open", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.url:
        write_app_link(args.package, args.url)
        # A fresh publish is the moment the report is final: tell Discord and log it.
        publish_notice.announce(args.package, args.url, args.findings_json)
    url = args.url or read_app_link(args.package)
    if not url:
        raise SystemExit(f"Chưa có link nào cho {args.package}")
    print(url)


if __name__ == "__main__":
    use_utf8_console()
    main()
