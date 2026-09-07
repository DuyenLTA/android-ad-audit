"""Render a diff result into a self-contained HTML report."""
import html


def render_html(result: dict, empty_filters: list[str], out_path: str) -> None:
    sections = result["sections"]

    total = sum(len(rows) for rows in sections.values())
    matched = sum(1 for rows in sections.values() for r in rows if r["found"])

    section_html = []
    for name, rows in sections.items():
        section_matched = sum(1 for r in rows if r["found"])
        row_html = []
        for r in rows:
            status = "pass" if r["found"] else "fail"
            label_txt = "Khớp" if r["found"] else "Lệch"
            note_html = (
                f"<div class='note'>{html.escape(r['note'])}</div>" if r.get("note") else ""
            )
            row_html.append(
                f"<tr><td class='cell-label'>{html.escape(r['label'])}</td>"
                f"<td class='cell-mono'>{html.escape(r['value'])}</td>"
                f"<td><span class='status {status}'><span class='dot'></span>{label_txt}</span>"
                f"{note_html}</td></tr>"
            )
        section_html.append(
            f"<section><div class='section-head'><h2>{html.escape(name)}</h2>"
            f"<span class='filter-tag'>{section_matched}/{len(rows)} khớp</span></div>"
            f"<div class='table-scroll'><table><thead><tr><th>Label</th><th>Giá trị (sheet)</th>"
            f"<th>Kết quả</th></tr></thead><tbody>{''.join(row_html)}</tbody></table></div></section>"
        )

    warning_html = ""
    if empty_filters:
        chips = "".join(f"<span class='chip'>{html.escape(f)}</span>" for f in empty_filters)
        warning_html = (
            "<div class='callout'><h3>Filter không khớp dòng log nào trong lần capture này</h3>"
            "<p>Các dòng \"Lệch\" liên quan tới filter này có thể chỉ vì log chưa capture đúng "
            "vùng, không hẳn là app bị lỗi thật -- capture lại rồi chạy lại trước khi kết luận.</p>"
            f"<div class='chip-list'>{chips}</div></div>"
        )

    page = f"""<title>Ad Checklist Diff</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@700;800&family=Public+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{{--ink:#14171c;--ink-soft:#4b525c;--paper:#f2f3f5;--surface:#fff;--line:#dadfe3;
    --accent:#1f6f78;--accent-soft:#e4eeee;--pass:#2e7d4f;--pass-soft:#e5f3ea;
    --fail:#c0392b;--fail-soft:#fbe9e7;--pending:#b8790c;--pending-soft:#faf1de;}}
  @media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--ink:#e8eaed;--ink-soft:#a7adb6;
    --paper:#101317;--surface:#171b20;--line:#2a2f36;--accent:#5fc2cb;--accent-soft:#1a2f31;
    --pass:#5fbd85;--pass-soft:#16261c;--fail:#e2695a;--fail-soft:#2b1a18;
    --pending:#dba53f;--pending-soft:#2b2415;}}}}
  :root[data-theme="dark"]{{--ink:#e8eaed;--ink-soft:#a7adb6;--paper:#101317;--surface:#171b20;
    --line:#2a2f36;--accent:#5fc2cb;--accent-soft:#1a2f31;--pass:#5fbd85;--pass-soft:#16261c;
    --fail:#e2695a;--fail-soft:#2b1a18;--pending:#dba53f;--pending-soft:#2b2415;}}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--paper);color:var(--ink);font-family:'Public Sans',sans-serif;line-height:1.5;}}
  h1,h2{{font-family:'Manrope',sans-serif;margin:0;}}
  .wrap{{max-width:900px;margin:0 auto;padding:2rem 1.5rem 4rem;display:flex;flex-direction:column;gap:2rem;}}
  .scorecard{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:1rem 1.25rem;}}
  .scorecard .num{{font-family:'Manrope',sans-serif;font-weight:800;font-size:1.8rem;color:var(--pass);}}
  .section-head{{display:flex;justify-content:space-between;align-items:baseline;gap:1rem;margin-bottom:0.75rem;flex-wrap:wrap;}}
  .filter-tag{{font-family:'JetBrains Mono',monospace;font-size:0.72rem;background:var(--accent-soft);color:var(--accent);
    padding:0.15rem 0.5rem;border-radius:5px;font-weight:600;}}
  .table-scroll{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--surface);}}
  table{{width:100%;border-collapse:collapse;font-size:0.88rem;min-width:480px;}}
  thead th{{text-align:left;font-family:'JetBrains Mono',monospace;font-size:0.68rem;text-transform:uppercase;
    letter-spacing:0.07em;color:var(--ink-soft);padding:0.6rem 1rem;border-bottom:1px solid var(--line);}}
  tbody td{{padding:0.55rem 1rem;border-bottom:1px solid var(--line);}}
  tbody tr:last-child td{{border-bottom:none;}}
  .cell-mono{{font-family:'JetBrains Mono',monospace;font-size:0.83rem;color:var(--ink-soft);}}
  .status{{display:inline-flex;align-items:center;gap:0.35rem;font-family:'JetBrains Mono',monospace;
    font-size:0.72rem;font-weight:600;padding:0.2rem 0.55rem;border-radius:20px;}}
  .status.pass{{background:var(--pass-soft);color:var(--pass);}}
  .status.fail{{background:var(--fail-soft);color:var(--fail);}}
  .status .dot{{width:6px;height:6px;border-radius:50%;background:currentColor;}}
  .note{{margin-top:0.3rem;font-size:0.78rem;color:var(--ink-soft);}}
  .callout{{border:1px solid var(--line);border-left:3px solid var(--pending);background:var(--pending-soft);
    border-radius:0 8px 8px 0;padding:1rem 1.25rem;}}
  .chip-list{{display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.5rem;}}
  .chip{{font-family:'JetBrains Mono',monospace;font-size:0.76rem;background:var(--surface);
    border:1px solid var(--line);border-radius:6px;padding:0.3rem 0.55rem;}}
</style>
<div class="wrap">
  <h1>Ad &amp; Config Checklist Diff</h1>
  <div class="scorecard"><div class="num">{matched} / {total}</div><div>dòng checklist khớp</div></div>
  {warning_html}
  {''.join(section_html)}
</div>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
