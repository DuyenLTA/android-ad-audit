import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import discord_notify


class _Hook:
    """Local stand-in for Discord's webhook: records bodies, answers with `status`."""

    def __init__(self, status=204, delay=0.0):
        self.headers = []
        self.bodies, self.status, self.delay = [], status, delay
        hook = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                hook.bodies.append(json.loads(body))
                hook.headers.append(dict(self.headers))
                if hook.delay:
                    threading.Event().wait(hook.delay)
                try:
                    self.send_response(hook.status)
                    self.end_headers()
                except OSError:  # client already gave up (timeout test)
                    pass

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/hook"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def hook(monkeypatch):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.delenv("DISCORD_ADS_TEAM_MENTION", raising=False)
    made = []

    def make(**kw):
        h = _Hook(**kw)
        made.append(h)
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", h.url)
        return h

    yield make
    for h in made:
        h.close()


def test_stop_message_format(hook):
    h = hook()
    ok = discord_notify.send("stop", "Sai build · com.a vc3", ["dòng 1", "dòng 2"],
                           action="Cài bản release", link="https://x/y")
    assert ok is True
    assert h.bodies[0]["content"] == (
        "⛔ **audit-fanout** · Sai build · com.a vc3\ndòng 1\ndòng 2\n"
        "→ Cài bản release\n[Mở report](<https://x/y>)"
    )


def test_done_message_without_action_or_link(hook):
    h = hook()
    discord_notify.send("done", "Xong", ["a"])
    assert h.bodies[0]["content"] == "✅ **audit-fanout** · Xong\na"


def test_bug_message_gets_mention_on_first_line_only(hook, monkeypatch):
    h = hook()
    monkeypatch.setenv("DISCORD_ADS_TEAM_MENTION", "<@&123>")
    discord_notify.send("bug", "Lỗi", ["r1", "r2"], action="Sửa sheet")
    assert h.bodies[0]["content"] == "🐞 **audit-fanout** · Lỗi\n<@&123> r1\nr2\n→ Sửa sheet"


def test_mention_is_not_added_to_other_kinds(hook, monkeypatch):
    h = hook()
    monkeypatch.setenv("DISCORD_ADS_TEAM_MENTION", "<@456>")
    discord_notify.send("stop", "T", ["r1"])
    assert "<@456>" not in h.bodies[0]["content"]


def test_unset_webhook_returns_false_with_one_stderr_line(monkeypatch, capsys):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert discord_notify.send("stop", "T", []) is False
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == "discord: DISCORD_WEBHOOK_URL chưa đặt, bỏ qua thông báo"


def test_http_500_returns_false_without_raising(hook, capsys):
    hook(status=500)
    assert discord_notify.send("stop", "T", []) is False
    assert "discord: gửi thất bại" in capsys.readouterr().err


def test_timeout_returns_false_without_raising(hook, monkeypatch, capsys):
    hook(delay=1.0)
    monkeypatch.setattr(discord_notify, "TIMEOUT_SECONDS", 0.2)
    assert discord_notify.send("stop", "T", []) is False
    assert "discord: gửi thất bại" in capsys.readouterr().err


def test_unreachable_url_never_leaks_webhook(monkeypatch, capsys):
    monkeypatch.setenv("DISCORD_NOTIFY", "1")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "http://127.0.0.1:1/secret-token")
    assert discord_notify.send("stop", "T", []) is False
    assert "secret-token" not in capsys.readouterr().err


def test_notify_zero_sends_nothing(hook, monkeypatch):
    h = hook()
    monkeypatch.setenv("DISCORD_NOTIFY", "0")
    assert discord_notify.send("stop", "T", []) is False
    assert h.bodies == []


def test_cli_exits_zero_even_when_sending_fails(monkeypatch):
    monkeypatch.setattr("sys.argv", ["discord_notify.py", "--kind", "stop", "--title", "T", "--line", "a"])
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert discord_notify.main() == 0


def test_cli_forwards_all_arguments(monkeypatch):
    calls = []
    monkeypatch.setattr(discord_notify, "send", lambda *a: calls.append(a) or True)
    monkeypatch.setattr("sys.argv", ["discord_notify.py", "--kind", "stop", "--title", "T",
                                     "--line", "a", "--line", "b", "--action", "X", "--link", "U"])
    discord_notify.main()
    assert calls == [("stop", "T", ["a", "b"], "X", "U")]


def test_request_headers_payload_and_204_is_success(hook):
    h = hook()
    assert discord_notify.send("done", "T", ["a"]) is True
    assert h.headers[0]["Content-Type"] == "application/json"
    assert h.headers[0]["User-Agent"] == "qa-workflow-bot/1.0"
    assert h.bodies[0]["allowed_mentions"] == {"parse": ["roles", "users"]}


def test_content_is_truncated_to_discord_limit(hook):
    h = hook()
    discord_notify.send("stop", "T", ["x" * 3000])
    content = h.bodies[0]["content"]
    assert len(content) == 2000 and content.endswith("…")
