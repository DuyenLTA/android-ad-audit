import artifact_report_builder
from artifact_report_builder import _label_for, render


def _snapshot(rows, leftover=None):
    return {
        "package": "com.a",
        "version_code": "7",
        "audited_at": "2026-01-01T00:00:00+00:00",
        "result": {"sections": {"S1": rows}, "leftover_ids": leftover or []},
    }


def _row(value, found, **extra):
    return {"label": "L", "value": value, "alt_values": [], "found": found, "note": None, **extra}


def test_score_counts_every_row_across_sections(tmp_path):
    tpl = tmp_path / "t.html"
    tpl.write_text("{{MATCHED}}/{{TOTAL}} lệch={{MISSED}}", encoding="utf-8")
    snap = _snapshot([_row("a", True), _row("b", False), _row("c", True)])
    assert render(snap, app_label="A", template_path=tpl) == "2/3 lệch=1"


def test_failing_row_is_marked_so_it_reads_at_a_glance(tmp_path):
    tpl = tmp_path / "t.html"
    tpl.write_text("{{TABLES}}", encoding="utf-8")
    out = render(_snapshot([_row("bad", False, note="không có trong build")]), app_label="A", template_path=tpl)
    assert "tr--miss" in out
    assert "Lệch" in out
    assert "không có trong build" in out


def test_row_without_label_is_named_as_the_normal_half_of_the_pair(tmp_path):
    tpl = tmp_path / "t.html"
    tpl.write_text("{{TABLES}}", encoding="utf-8")
    row = _row("inter_feature", True)
    row["label"] = ""
    out = render(_snapshot([row]), app_label="A", template_path=tpl)
    assert "cặp normal" in out


def test_leftover_id_explained_by_the_findings_points_back_at_them(tmp_path):
    tpl = tmp_path / "t.html"
    tpl.write_text("{{LEFTOVER}}", encoding="utf-8")
    snap = _snapshot([_row("a", True)], leftover=["ca-app-pub-1/2733004612", "ca-app-pub-1/9999"])
    out = render(snap, app_label="A", highlight=("2733004612",), template_path=tpl)
    assert out.count("có trong phần điều tra") == 1


def test_values_from_the_sheet_are_escaped(tmp_path):
    tpl = tmp_path / "t.html"
    tpl.write_text("{{TABLES}}", encoding="utf-8")
    out = render(_snapshot([_row("<script>x</script>", True)]), app_label="A", template_path=tpl)
    assert "<script>" not in out


def test_label_falls_back_to_the_package_when_registry_has_no_entry():
    assert _label_for("com.a", [{"package": "com.b", "label": "B"}]) == "com.a"
    assert _label_for("com.a", [{"package": "com.a", "label": "A"}]) == "A"


# --- The page a run replaces is the only record of what was shown ------------

def test_the_previous_page_is_kept_before_it_is_replaced(tmp_path):
    page = tmp_path / "com.a-artifact.html"
    page.write_text("<p>lượt trước</p>", encoding="utf-8")

    kept = artifact_report_builder.archive_previous(page)
    assert kept is not None and kept.parent.name == "history"
    assert kept.read_text(encoding="utf-8") == "<p>lượt trước</p>"
    # Copied, not moved: a write that fails after this must still leave the
    # published page where it was.
    assert page.exists()


def test_a_first_run_has_nothing_to_keep(tmp_path):
    assert artifact_report_builder.archive_previous(tmp_path / "nope.html") is None


def test_two_archived_pages_do_not_collide(tmp_path):
    import os
    import time

    page = tmp_path / "com.a-artifact.html"
    page.write_text("một", encoding="utf-8")
    first = artifact_report_builder.archive_previous(page)

    page.write_text("hai", encoding="utf-8")
    os.utime(page, (time.time() + 5, time.time() + 5))
    second = artifact_report_builder.archive_previous(page)

    assert first != second
    assert first.read_text(encoding="utf-8") == "một"
    assert second.read_text(encoding="utf-8") == "hai"
