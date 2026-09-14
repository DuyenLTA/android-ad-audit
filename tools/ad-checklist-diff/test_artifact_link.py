import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import artifact_link


def test_each_app_keeps_its_own_link(tmp_path):
    from artifact_link import read_app_link, write_app_link

    links = tmp_path / "links.json"
    write_app_link("com.a", "https://x/a", links_file=links)
    write_app_link("com.b", "https://x/b", links_file=links)

    assert read_app_link("com.a", links_file=links) == "https://x/a"
    assert read_app_link("com.b", links_file=links) == "https://x/b"


def test_republishing_an_app_replaces_its_link(tmp_path):
    from artifact_link import read_app_link, write_app_link

    links = tmp_path / "links.json"
    write_app_link("com.a", "https://x/old", links_file=links)
    write_app_link("com.a", "https://x/new", links_file=links)
    assert read_app_link("com.a", links_file=links) == "https://x/new"


def test_an_app_never_published_has_no_link(tmp_path):
    # The caller publishes a fresh page rather than guessing at a URL.
    from artifact_link import read_app_link

    assert read_app_link("com.nope", links_file=tmp_path / "missing.json") is None


def test_a_machine_with_no_browser_says_so(monkeypatch):
    import artifact_link

    monkeypatch.setattr(artifact_link.webbrowser, "open", lambda url: (_ for _ in ()).throw(OSError()))
    assert artifact_link.open_in_browser("https://x") is False


def _main(monkeypatch, argv, links_file):
    """Run the CLI, returning the URLs it tried to open."""
    opened = []
    monkeypatch.setattr(artifact_link, "LINKS_FILE", links_file)
    monkeypatch.setattr(artifact_link, "open_in_browser", lambda url: opened.append(url) or True)
    monkeypatch.setattr(sys, "argv", ["artifact_link.py"] + argv)
    artifact_link.main()
    return opened


def test_recording_a_link_opens_it_without_being_asked(monkeypatch, tmp_path):
    # The reason this is not a flag: a run that finishes and does not open the
    # page is the failure, and an opt-in flag is a thing to forget.
    opened = _main(monkeypatch, ["--package", "com.x", "https://x/1"], tmp_path / "l.json")
    assert opened == ["https://x/1"]


def test_looking_a_link_up_before_publishing_opens_nothing(monkeypatch, tmp_path):
    links = tmp_path / "l.json"
    artifact_link.write_app_link("com.x", "https://x/1", links)
    assert _main(monkeypatch, ["--package", "com.x", "--show"], links) == []


def test_no_open_suppresses_it(monkeypatch, tmp_path):
    opened = _main(monkeypatch, ["--package", "com.x", "https://x/1", "--no-open"], tmp_path / "l.json")
    assert opened == []


def test_the_old_open_flag_still_parses(monkeypatch, tmp_path):
    # Callers written against the opt-in flag must keep working.
    opened = _main(monkeypatch, ["--package", "com.x", "--open", "https://x/1"], tmp_path / "l.json")
    assert opened == ["https://x/1"]
