"""Test-wide guards: no test may reach a real Discord webhook or write the real usage log."""
import os

import pytest

os.environ["DISCORD_NOTIFY"] = "0"
os.environ.pop("DISCORD_WEBHOOK_URL", None)


@pytest.fixture(autouse=True)
def _usage_log_in_tmp(tmp_path, monkeypatch):
    # Recording a link appends a row to docs/usage-log.md; a test that records a
    # fake link (com.x -> https://x/1) must not leave that row in the real file.
    import publish_notice

    fake = tmp_path / "usage-log.md"
    fake.write_text(publish_notice.USAGE_LOG.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(publish_notice, "USAGE_LOG", fake)
