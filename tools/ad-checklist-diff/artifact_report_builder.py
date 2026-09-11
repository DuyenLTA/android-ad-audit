"""Render a snapshot into the shareable artifact page for the ads team.

`report_renderer.py` writes the operator's page -- the one the Streamlit app
links to right after a run. This one targets a different reader: the page that
gets published and sent to whoever owns the checklist, so it leads with the
score (how many rows khớp, how many lệch) and only then opens the tables.

What the fan-out proves about the rows the mechanical pass could not settle
differs every run, so that part is not generated: it is written per run and
passed in as an HTML fragment. Everything derived from the snapshot -- score,
section chips, row tables, leftover IDs -- is generated here.
"""
import argparse
import html
import json
from pathlib import Path

from artifact_run_context import capture_warning, delta_note, mode_label

HERE = Path(__file__).parent
TEMPLATE = HERE / "artifact_report_template.html"


def _label_for(package: str, registry_apps: list[dict] | None) -> str:
    """The app's display name from the registry, falling back to its package."""
    for app in registry_apps or []:
        if app.get("package") == package:
            return app.get("label") or package
    return package


def _row_html(row: dict) -> str:
    """One checklist row. A row with no label is the normal half of a double-id pair."""
    failed = not row["found"]
    label = (
        html.escape(row["label"])
        if row["label"]
        else '<span class="twin">↳ cặp normal</span>'
    )
    # Section 3 keeps the placement name in `value` and the real ad unit ID in alt_values.
    alt = (
        f'<span class="altid">{html.escape(row["alt_values"][0])}</span>'
        if row.get("alt_values")
        else ""
    )
    status = (
        '<span class="st st--miss">Lệch</span>'
        if failed
        else '<span class="st st--ok">Khớp</span>'
    )
    note = f'<div class="rownote">{html.escape(row["note"])}</div>' if row.get("note") else ""
    return (
        f'<tr class="{"tr--miss" if failed else ""}">'
        f'<td class="c-label">{label}</td>'
        f'<td class="c-val"><span class="val">{html.escape(row["value"])}</span>{alt}</td>'
        f'<td class="c-st">{status}{note}</td></tr>'
    )


def _section_html(index: int, name: str, rows: list[dict]) -> str:
    matched = sum(1 for r in rows if r["found"])
    frac_class = "frac--ok" if matched == len(rows) else "frac--miss"
    body = "".join(_row_html(r) for r in rows)
    return (
        f'<details class="sec" id="sec{index}" open>'
        f'<summary><span class="sec-name">{html.escape(name)}</span>'
        f'<span class="sec-frac {frac_class}">{matched}/{len(rows)} khớp</span></summary>'
        f'<div class="tbl-scroll"><table>'
        f"<thead><tr><th>Label</th><th>Giá trị (sheet)</th><th>Kết quả</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div></details>"
    )


def _chip_html(index: int, name: str, rows: list[dict]) -> str:
    matched = sum(1 for r in rows if r["found"])
    chip_class = "chip--ok" if matched == len(rows) else "chip--miss"
    return (
        f'<a class="statchip {chip_class}" href="#sec{index}">'
        f'<span class="statchip-name">{html.escape(name)}</span>'
        f'<span class="statchip-frac">{matched}/{len(rows)}</span></a>'
    )


def _leftover_html(ids: list[str], highlight: tuple[str, ...]) -> str:
    """IDs the build uses that no checklist row claims.

    An ID the findings section already explains gets pointed back at it; the
    rest are left unlabelled rather than guessed at.
    """
    items = []
    for ad_id in ids:
        tag = (
            ' <span class="tag">có trong phần điều tra</span>'
            if any(ad_id.endswith(h) for h in highlight)
            else ""
        )
        items.append(f"<li><code>{html.escape(ad_id)}</code>{tag}</li>")
    return "".join(items) or "<li>Không có.</li>"


def render(
    snapshot: dict,
    *,
    app_label: str,
    findings_html: str = "",
    notes_html: str = "",
    highlight: tuple[str, ...] = (),
    triage: dict | None = None,
    run: str = "",
    mode: str = "",
    report: str = "",
    template_path: Path = TEMPLATE,
) -> str:
    sections = snapshot["result"]["sections"]
    leftover = snapshot["result"].get("leftover_ids", [])
    total = sum(len(rows) for rows in sections.values())
    matched = sum(1 for rows in sections.values() for r in rows if r["found"])

    chips, tables = [], []
    for i, (name, rows) in enumerate(sections.items(), start=1):
        chips.append(_chip_html(i, name, rows))
        tables.append(_section_html(i, name, rows))

    fields = {
        "TITLE": html.escape(app_label),
        "PKG": html.escape(snapshot["package"]),
        "VC": html.escape(str(snapshot.get("version_code", "?"))),
        "AUDITED_AT": html.escape(snapshot.get("audited_at", "")),
        "TOTAL": str(total),
        "MATCHED": str(matched),
        "MISSED": str(total - matched),
        "LEFTOVER_N": str(len(leftover)),
        "CHIPS": "".join(chips),
        "TABLES": "".join(tables),
        "LEFTOVER": _leftover_html(leftover, highlight),
        "FINDINGS": findings_html,
        "NOTES": notes_html,
        # Bối cảnh của đúng lượt này -- trước đây gõ tay vào template, nên một
        # trang từng khai "delta: không đổi" cạnh run id của lượt khác.
        "RUN": html.escape(run) if run else "không rõ run",
        "MODE": html.escape(mode_label(mode)),
        "DELTA": html.escape(delta_note(triage)),
        "REPORT": html.escape(report),
        "CAPTURE_WARNING": capture_warning(triage),
    }
    page = template_path.read_text(encoding="utf-8")
    for key, value in fields.items():
        page = page.replace("{{" + key + "}}", value)
    return page


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    parser.add_argument("--snapshots", default=str(HERE / "snapshots"))
    parser.add_argument("--registry", default=str(HERE / "apps.json"))
    parser.add_argument("--findings", help="HTML fragment: this run's fan-out findings")
    parser.add_argument("--notes", help="HTML fragment: ghi chú + câu hỏi chưa giải quyết")
    parser.add_argument("--highlight", nargs="*", default=[], help="leftover IDs the findings explain")
    parser.add_argument("--run", default="", help="ID lượt workflow, ví dụ wf_8f6c22cc-5a6")
    parser.add_argument("--mode", default="", choices=["", "capture", "apk", "skip"])
    parser.add_argument("--report", default="", help="đường dẫn báo cáo markdown của lượt này")
    parser.add_argument("--triage", help="mặc định: out/<package>-triage.json")
    parser.add_argument("--out", help="default: out/<package>-artifact.html")
    args = parser.parse_args()

    snapshot = json.loads(
        (Path(args.snapshots) / f"{args.package}.json").read_text(encoding="utf-8")
    )
    registry = Path(args.registry)
    apps = json.loads(registry.read_text(encoding="utf-8")).get("apps") if registry.exists() else None
    findings = Path(args.findings).read_text(encoding="utf-8") if args.findings else ""
    notes = Path(args.notes).read_text(encoding="utf-8") if args.notes else ""

    # Thiếu triage thì trang vẫn dựng được, chỉ là không khai được delta và
    # không cảnh báo được gì về lượt capture.
    triage_path = Path(args.triage or HERE / "out" / f"{args.package}-triage.json")
    triage = (
        json.loads(triage_path.read_text(encoding="utf-8"))
        if triage_path.exists()
        else None
    )

    out = Path(args.out or HERE / "out" / f"{args.package}-artifact.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        render(
            snapshot,
            app_label=_label_for(args.package, apps),
            findings_html=findings,
            notes_html=notes,
            highlight=tuple(args.highlight),
            triage=triage,
            run=args.run,
            mode=args.mode,
            report=args.report,
        ),
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
