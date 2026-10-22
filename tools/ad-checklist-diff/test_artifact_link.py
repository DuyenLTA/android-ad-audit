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


def _main(monkeypatch, argv, links_file):
    """Run the CLI, returning the URLs it tried to open in a browser."""
    import webbrowser

    opened = []
    monkeypatch.setattr(artifact_link, "LINKS_FILE", links_file)
    monkeypatch.setattr(webbrowser, "open", lambda url, *a, **k: opened.append(url) or True)
    monkeypatch.setattr(sys, "argv", ["artifact_link.py"] + argv)
    artifact_link.main()
    return opened


def test_recording_a_link_prints_it_and_opens_no_browser(monkeypatch, tmp_path, capsys):
    # The Discord notice carries the link; popping a browser on every run is noise.
    links = tmp_path / "l.json"
    assert _main(monkeypatch, ["--package", "com.x", "https://x/1"], links) == []
    assert capsys.readouterr().out.strip() == "https://x/1"
    assert artifact_link.read_app_link("com.x", links) == "https://x/1"


def test_looking_a_link_up_before_publishing_opens_nothing(monkeypatch, tmp_path):
    links = tmp_path / "l.json"
    artifact_link.write_app_link("com.x", "https://x/1", links)
    assert _main(monkeypatch, ["--package", "com.x", "--show"], links) == []


def test_the_old_open_flags_still_parse(monkeypatch, tmp_path):
    # Callers written when recording a link opened the browser must keep working.
    for flag in ("--open", "--no-open"):
        assert _main(monkeypatch, ["--package", "com.x", flag, "https://x/1"], tmp_path / "l.json") == []
