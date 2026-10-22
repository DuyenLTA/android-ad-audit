import json
from datetime import datetime

import pytest

import artifact_link
import audit_runner
import find_app
import publish_notice
import discord_notify

LOG = """# Log

| Ngày | App |
|---|---|
| 01/10/2026 | com.old |

**Tổng:** 1 lần.
"""


@pytest.fixture
def sent(monkeypatch):
    """The notifier is the boundary: record what the hooks hand it."""
    calls = []
    monkeypatch.setattr(discord_notify, "send", lambda *a, **k: calls.append((a, k)) or True)
    return calls


def test_usage_log_row_goes_after_last_table_row(tmp_path):
    log = tmp_path / "usage-log.md"
    log.write_text(LOG, encoding="utf-8")
    findings = {"confirmed": [{"value": "v"}], "disputed": 1, "unresolved": 0}

    assert publish_notice.append_usage_log("com.a", "7", "https://x/a", findings, 2, log,
                                           today=datetime(2026, 10, 22)) is True

    lines = log.read_text(encoding="utf-8").split("\n")
    row = lines.index("| 01/10/2026 | com.old |") + 1
    assert lines[row] == ("| 22/10/2026 | com.a | 7 | 1 xác nhận, 1 tranh chấp, 0 chưa chốt | 1 | "
                          "[artifact](https://x/a) | ? | 30 phút | ? |")
    assert lines[row + 1] == ""
    assert lines[row + 2].startswith("**Tổng:**")
    assert lines[:row] == LOG.split("\n")[:row]  # nothing above the new row moved


def test_usage_log_skips_same_publish_and_missing_file(tmp_path):
    log = tmp_path / "usage-log.md"
    log.write_text(LOG, encoding="utf-8")
    assert publish_notice.append_usage_log("com.a", "7", "https://x/a", None, 0, log) is True
    assert publish_notice.append_usage_log("com.a", "7", "https://x/a", None, 0, log) is False
    assert publish_notice.append_usage_log("com.a", "7", "u", None, 0, tmp_path / "nope.md") is False


def _setup_publish(tmp_path, monkeypatch, findings=None):
    out = tmp_path / "out"
    out.mkdir()
    (out / "com.a-triage.json").write_text(
        json.dumps({"version_code": "9", "triage": {"khác": [{"value": "r"}], "x": []}}), encoding="utf-8")
    log = tmp_path / "usage-log.md"
    log.write_text(LOG, encoding="utf-8")
    monkeypatch.setattr(publish_notice, "TOOL_DIR", tmp_path)
    monkeypatch.setattr(publish_notice, "USAGE_LOG", log)
    monkeypatch.setattr(artifact_link, "LINKS_FILE", tmp_path / "links.json")
    argv = ["artifact_link.py", "--package", "com.a", "https://x/a"]
    if findings is not None:
        f = tmp_path / "f.json"
        f.write_text(json.dumps(findings), encoding="utf-8")
        argv += ["--findings-json", str(f)]
    monkeypatch.setattr("sys.argv", argv)
    return log


def test_recording_a_link_sends_done_with_link_and_logs(tmp_path, monkeypatch, sent):
    log = _setup_publish(tmp_path, monkeypatch)
    artifact_link.main()

    assert [c[0][0] for c in sent] == ["done"]
    args, kwargs = sent[0]
    assert args[1] == "Report đã publish · com.a vc9"
    assert kwargs["link"] == "https://x/a"
    assert "Cần người xem lại: 1 dòng" in args[2]
    assert "com.a" in log.read_text(encoding="utf-8")


def test_confirmed_rows_fold_into_one_bug_message_capped_at_ten(tmp_path, monkeypatch, sent):
    # One message per publish, so the link shows up in the channel exactly once.
    rows = [{"value": f"id{i}", "placement": "Home"} for i in range(12)]
    _setup_publish(tmp_path, monkeypatch, {"confirmed": rows, "disputed": 1, "unresolved": 2})
    artifact_link.main()

    assert [c[0][0] for c in sent] == ["bug"]
    args, kwargs = sent[0]
    lines = args[2]
    assert lines[0] == "Xác nhận: 12, tranh chấp: 1, chưa chốt: 2"
    assert lines[1] == "id0 · Home"
    assert "… và 2 dòng nữa" in lines and lines[-1] == "Cần người xem lại: 3 dòng"
    assert kwargs["action"] == "Ads team xác nhận và sửa sheet / log Jira"
    assert kwargs["link"] == "https://x/a"


def test_notifier_failure_never_breaks_recording(tmp_path, monkeypatch):
    _setup_publish(tmp_path, monkeypatch)
    monkeypatch.setattr(discord_notify, "send", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    artifact_link.main()
    assert artifact_link.read_app_link("com.a", tmp_path / "links.json") == "https://x/a"


def test_show_does_not_notify(tmp_path, monkeypatch, sent):
    _setup_publish(tmp_path, monkeypatch)
    artifact_link.write_app_link("com.a", "https://x/a", tmp_path / "links.json")
    monkeypatch.setattr("sys.argv", ["artifact_link.py", "--package", "com.a", "--show"])
    artifact_link.main()
    assert sent == []


def test_runner_notifies_wrong_build_and_error_only(sent):
    audit_runner.notify_stops([
        {"package": "com.a", "version_code": "3", "wrong_build": ["ID mẫu"]},
        {"package": "com.b", "error": "boom"},
        {"package": "com.c", "delta": {"broke": []}},
    ])
    assert [c[0][:3] for c in sent] == [
        ("stop", "Sai build · com.a vc3", ["ID mẫu"]),
        ("stop", "Lỗi runner · com.b", ["boom"]),
    ]
    assert sent[0][1]["action"] == "Cài bản release rồi chạy lại /audit-fanout com.a"


def _exact_refusal(monkeypatch, message):
    monkeypatch.setattr(find_app, "load_apps", lambda r: [])
    monkeypatch.setattr(find_app, "registry_sheet", lambda r: "sheet")
    monkeypatch.setattr(find_app, "resolve_packages",
                        lambda *a: (_ for _ in ()).throw(SystemExit(message)))
    with pytest.raises(SystemExit):
        find_app._report_exact("com.a", "reg")


def test_find_app_two_tabs_notifies_with_pick_action(monkeypatch, sent):
    _exact_refusal(monkeypatch, "Sheet có 2 tab cùng khai com.a (gid 1, 2). Chọn bừa ...")
    assert sent[0][0][0] == "stop"
    assert sent[0][1]["action"] == "Chọn tab đúng rồi ghi vào apps.json"


def test_find_app_no_tab_notifies_with_ask_ads_team(monkeypatch, sent):
    _exact_refusal(monkeypatch, "Sheet không có tab nào khai com.a: chưa có checklist")
    assert sent[0][1]["action"] == "Nhờ ads-team thêm tab checklist"


def test_find_app_typo_is_left_to_the_agent(monkeypatch, sent):
    _exact_refusal(monkeypatch, "Không phải package id: Nexus. Cần dạng com.abc.xyz")
    assert sent == []
