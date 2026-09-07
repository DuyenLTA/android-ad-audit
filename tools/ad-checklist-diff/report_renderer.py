"""Render a diff result into a self-contained HTML report."""
import html


def _status_level(matched: int, total: int) -> str:
    if total == 0 or matched == 0:
        return "fail"
    if matched == total:
        return "pass"
    return "pending"


def render_html(result: dict, empty_filters: list[str], out_path: str) -> None:
    sections = result["sections"]

    total = sum(len(rows) for rows in sections.values())
    matched = sum(1 for rows in sections.values() for r in rows if r["found"])
    pct = round(matched / total * 100) if total else 0

    chip_html = []
    section_html = []
    for name, rows in sections.items():
        section_matched = sum(1 for r in rows if r["found"])
        level = _status_level(section_matched, len(rows))
        chip_html.append(
            f"<span class='section-chip {level}'>{html.escape(name)} "
            f"<b>{section_matched}/{len(rows)}</b></span>"
        )

        row_html = []
        for r in rows:
            status = "pass" if r["found"] else "fail"
            label_txt = "Khớp" if r["found"] else "Lệch"
            note_html = (
                f"<div class='note'>{html.escape(r['note'])}</div>" if r.get("note") else ""
            )
            row_class = "" if r["found"] else " class='row-fail'"
            row_html.append(
                f"<tr{row_class}><td class='cell-label'>{html.escape(r['label'])}</td>"
                f"<td class='cell-mono'>{html.escape(r['value'])}</td>"
                f"<td><span class='status {status}'><span class='dot'></span>{label_txt}</span>"
                f"{note_html}</td></tr>"
            )
        section_html.append(
            f"<details class='section' open><summary>"
            f"<span class='section-title'>{html.escape(name)}</span>"
            f"<span class='section-frac {level}'>{section_matched}/{len(rows)} khớp</span>"
            f"</summary>"
            f"<div class='table-scroll'><table><thead><tr><th>Label</th><th>Giá trị (sheet)</th>"
            f"<th>Kết quả</th></tr></thead><tbody>{''.join(row_html)}</tbody></table></div></details>"
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
  :root{{
    --ink:#10181a;--ink-soft:#56686a;--paper:#eef2f1;--surface:#fff;--surface-alt:#f5f8f7;--line:#d7e1df;
    --accent:#146b6e;--accent-soft:#dcecea;
    --pass:#1f7a4d;--pass-soft:#e2f4e8;
    --fail:#b23b2e;--fail-soft:#fbeae6;
    --pending:#97650f;--pending-soft:#f7ecd7;
  }}
  @media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{
    --ink:#e8efee;--ink-soft:#9fb3b1;--paper:#0d1516;--surface:#141f20;--surface-alt:#182324;--line:#24393a;
    --accent:#55c2bf;--accent-soft:#16302f;
    --pass:#5fce8e;--pass-soft:#16301f;
    --fail:#ef8574;--fail-soft:#341c18;
    --pending:#e0ab54;--pending-soft:#34290f;
  }}}}
  :root[data-theme="dark"]{{
    --ink:#e8efee;--ink-soft:#9fb3b1;--paper:#0d1516;--surface:#141f20;--surface-alt:#182324;--line:#24393a;
    --accent:#55c2bf;--accent-soft:#16302f;
    --pass:#5fce8e;--pass-soft:#16301f;
    --fail:#ef8574;--fail-soft:#341c18;
    --pending:#e0ab54;--pending-soft:#34290f;
  }}
  *{{box-sizing:border-box;}}
  body{{margin:0;background:var(--paper);color:var(--ink);font-family:'Public Sans',sans-serif;line-height:1.5;
    font-variant-numeric:tabular-nums;}}
  .wrap{{max-width:900px;margin:0 auto;padding:2.5rem 1.5rem 4rem;display:flex;flex-direction:column;gap:1.75rem;}}

  .report-head{{display:flex;flex-direction:column;gap:1.1rem;}}
  .eyebrow{{margin:0;font-family:'Manrope',sans-serif;font-weight:800;font-size:0.85rem;
    letter-spacing:0.14em;text-transform:uppercase;color:var(--accent);}}
  h1{{margin:0;font-family:'Manrope',sans-serif;font-weight:800;font-size:2.1rem;
    letter-spacing:0.01em;text-wrap:balance;}}

  .scorecard{{background:var(--surface);border:1px solid var(--line);border-radius:12px;
    padding:1.25rem 1.5rem;display:flex;flex-direction:column;gap:0.6rem;}}
  .score-row{{display:flex;align-items:baseline;gap:0.4rem;}}
  .score-num{{font-family:'Manrope',sans-serif;font-weight:800;font-size:2.6rem;color:var(--pass);
    line-height:1;}}
  .score-den{{font-family:'Manrope',sans-serif;font-weight:700;font-size:1.3rem;color:var(--ink-soft);}}
  .score-label{{font-size:0.85rem;color:var(--ink-soft);}}
  .score-bar{{height:6px;border-radius:99px;background:var(--surface-alt);overflow:hidden;}}
  .score-bar-fill{{height:100%;border-radius:99px;background:var(--pass);}}

  .section-chips{{display:flex;flex-wrap:wrap;gap:0.5rem;}}
  .section-chip{{font-family:'JetBrains Mono',monospace;font-size:0.74rem;padding:0.28rem 0.6rem;
    border-radius:7px;border:1px solid var(--line);background:var(--surface);color:var(--ink-soft);}}
  .section-chip b{{font-weight:600;}}
  .section-chip.pass{{border-color:transparent;background:var(--pass-soft);color:var(--pass);}}
  .section-chip.pending{{border-color:transparent;background:var(--pending-soft);color:var(--pending);}}
  .section-chip.fail{{border-color:transparent;background:var(--fail-soft);color:var(--fail);}}

  .callout{{border:1px solid var(--line);border-left:3px solid var(--pending);background:var(--pending-soft);
    border-radius:0 10px 10px 0;padding:1rem 1.25rem;}}
  .callout h3{{margin:0 0 0.35rem;font-family:'Manrope',sans-serif;font-weight:800;font-size:1.05rem;}}
  .callout p{{margin:0;font-size:0.88rem;color:var(--ink-soft);max-width:65ch;}}
  .chip-list{{display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.6rem;}}
  .chip{{font-family:'JetBrains Mono',monospace;font-size:0.76rem;background:var(--surface);
    border:1px solid var(--line);border-radius:6px;padding:0.3rem 0.55rem;}}

  .sections{{display:flex;flex-direction:column;gap:1rem;}}
  details.section{{background:var(--surface);border:1px solid var(--line);border-radius:12px;overflow:hidden;}}
  summary{{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;
    gap:1rem;padding:0.9rem 1.25rem;flex-wrap:wrap;}}
  summary::-webkit-details-marker{{display:none;}}
  summary::before{{content:'▸';display:inline-block;margin-right:0.6rem;color:var(--ink-soft);
    transition:transform 0.15s ease;}}
  details[open] summary::before{{transform:rotate(90deg);}}
  .section-title{{font-family:'Manrope',sans-serif;font-weight:700;font-size:1.15rem;flex:1;}}
  .section-frac{{font-family:'JetBrains Mono',monospace;font-size:0.72rem;font-weight:600;
    padding:0.18rem 0.55rem;border-radius:20px;}}
  .section-frac.pass{{background:var(--pass-soft);color:var(--pass);}}
  .section-frac.pending{{background:var(--pending-soft);color:var(--pending);}}
  .section-frac.fail{{background:var(--fail-soft);color:var(--fail);}}

  .table-scroll{{overflow-x:auto;border-top:1px solid var(--line);}}
  table{{width:100%;border-collapse:collapse;font-size:0.88rem;min-width:480px;}}
  thead th{{text-align:left;font-family:'JetBrains Mono',monospace;font-size:0.68rem;text-transform:uppercase;
    letter-spacing:0.07em;color:var(--ink-soft);padding:0.6rem 1.25rem;border-bottom:1px solid var(--line);
    background:var(--surface-alt);}}
  tbody td{{padding:0.6rem 1.25rem;border-bottom:1px solid var(--line);}}
  tbody tr:last-child td{{border-bottom:none;}}
  tbody tr.row-fail td:first-child{{box-shadow:inset 3px 0 0 var(--fail);}}
  .cell-mono{{font-family:'JetBrains Mono',monospace;font-size:0.83rem;color:var(--ink-soft);}}
  .status{{display:inline-flex;align-items:center;gap:0.35rem;font-family:'JetBrains Mono',monospace;
    font-size:0.72rem;font-weight:600;padding:0.2rem 0.55rem;border-radius:20px;}}
  .status.pass{{background:var(--pass-soft);color:var(--pass);}}
  .status.fail{{background:var(--fail-soft);color:var(--fail);}}
  .status .dot{{width:6px;height:6px;border-radius:50%;background:currentColor;}}
  .note{{margin-top:0.4rem;font-family:'JetBrains Mono',monospace;font-size:0.76rem;color:var(--ink-soft);
    max-width:52ch;}}
</style>
<div class="wrap">
  <header class="report-head">
    <p class="eyebrow">Ad &amp; Config Checklist</p>
    <h1>Checklist Diff</h1>
    <div class="scorecard">
      <div class="score-row"><span class="score-num">{matched}</span><span class="score-den">/ {total} khớp</span></div>
      <div class="score-bar"><div class="score-bar-fill" style="width:{pct}%"></div></div>
    </div>
    <div class="section-chips">{''.join(chip_html)}</div>
  </header>
  {warning_html}
  <div class="sections">
    {''.join(section_html)}
  </div>
</div>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
