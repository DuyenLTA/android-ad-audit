"""Post a short status message to Discord through a channel webhook.

Stdlib only, and deliberately unable to hurt its caller: every failure path
(no webhook, HTTP error, timeout, bad URL) returns False after one stderr line.
A notification is a courtesy on top of the audit -- it must never change an exit
code or a line the calling tool prints to stdout.

Environment:
  DISCORD_WEBHOOK_URL       https://discord.com/api/webhooks/<id>/<token>. Unset -> nothing is sent.
  DISCORD_ADS_TEAM_MENTION  e.g. `<@&roleid>` or `<@userid>`; prefixed to "bug" messages.
  DISCORD_NOTIFY=0          Switch sending off (tests, dry runs).

CLI (for callers that are not Python, e.g. the slash command or cron):
  python discord_notify.py --kind stop --title "..." --line "..." [--action ...] [--link URL]
Always exits 0, even when sending fails.
"""
import argparse
import json
import os
import sys
import urllib.request

TIMEOUT_SECONDS = 5
MAX_CONTENT = 2000  # Discord rejects longer messages
# Cloudflare in front of Discord rejects the default Python-urllib User-Agent.
USER_AGENT = "qa-workflow-bot/1.0"
EMOJI = {"stop": "⛔", "done": "✅", "bug": "🐞"}


def build_text(kind: str, title: str, lines: list[str], action: str | None = None,
               link: str | None = None) -> str:
    """Discord markdown body. Same shape in every repo that posts these messages."""
    lines = list(lines)
    mention = os.environ.get("DISCORD_ADS_TEAM_MENTION", "").strip()
    if kind == "bug" and mention and lines:
        lines[0] = f"{mention} {lines[0]}"
    parts = [f"{EMOJI[kind]} **audit-fanout** · {title}", *lines]
    if action:
        parts.append(f"→ {action}")
    if link:
        parts.append(f"[Mở report](<{link}>)")
    text = "\n".join(parts)
    return text if len(text) <= MAX_CONTENT else text[: MAX_CONTENT - 1] + "…"


def send(kind: str, title: str, lines: list[str], action: str | None = None,
         link: str | None = None) -> bool:
    """True only when Discord accepted (204 No Content, any 2xx) the message. Never raises."""
    if kind not in EMOJI:
        print(f"discord: kind không hợp lệ: {kind!r}", file=sys.stderr)
        return False
    if os.environ.get("DISCORD_NOTIFY") == "0":
        return False
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        print("discord: DISCORD_WEBHOOK_URL chưa đặt, bỏ qua thông báo", file=sys.stderr)
        return False
    try:
        body = json.dumps({
            "content": build_text(kind, title, lines, action, link),
            "allowed_mentions": {"parse": ["roles", "users"]},
        }).encode("utf-8")
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json", "User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return 200 <= response.status < 300
    except Exception as e:  # noqa: BLE001 -- URLError, timeout, bad URL: all mean "not sent"
        # Class name only: the message of a URLError can echo the webhook URL.
        print(f"discord: gửi thất bại ({type(e).__name__})", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Gửi thông báo audit-fanout lên Discord")
    parser.add_argument("--kind", required=True, choices=sorted(EMOJI))
    parser.add_argument("--title", required=True)
    parser.add_argument("--line", action="append", default=[], help="lặp lại được")
    parser.add_argument("--action")
    parser.add_argument("--link")
    args = parser.parse_args()
    send(args.kind, args.title, args.line, args.action, args.link)
    return 0


if __name__ == "__main__":
    try:
        from console_encoding import use_utf8_console
        use_utf8_console()
    except Exception:  # noqa: BLE001 -- console tweak is optional
        pass
    sys.exit(main())
