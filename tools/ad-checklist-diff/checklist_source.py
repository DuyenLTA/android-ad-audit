"""Fetch and parse the Google Sheet checklist into (section, label, value) rows."""
import csv
import hashlib
import io
import json
import re

import requests

ID_RE = re.compile(r"ca-app-pub-\d+[/~]\d+")


def sheet_csv_url(sheet_url: str) -> str:
    """Convert a Google Sheet share URL into its CSV export URL (preserving the tab, if given)."""
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not m:
        raise SystemExit(f"Not a recognizable Google Sheet URL: {sheet_url}")
    sheet_id = m.group(1)
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    gid = re.search(r"[#&?]gid=(\d+)", sheet_url)
    if gid:
        url += f"&gid={gid.group(1)}"
    return url


def parse_checklist_csv(csv_text: str) -> list[dict]:
    """Parse checklist CSV text into (section, label, value, alt_values) rows.

    Column C is optional: a comma-separated list of alternate log values that
    also count as a match. For rows where the checklist's placement-key name
    doesn't match the internal key name the app actually logs (a naming
    inconsistency in the source app, not something this tool can derive),
    whoever maintains the sheet can note the real key there instead of the
    tool silently reporting a false "Lệch".
    """
    reader = csv.reader(io.StringIO(csv_text))
    rows = []
    section = "(no section)"
    for cols in reader:
        col_a = (cols[0].strip() if len(cols) > 0 else "")
        col_b = (cols[1].strip() if len(cols) > 1 else "")
        col_c = (cols[2].strip() if len(cols) > 2 else "")
        if not col_a and not col_b:
            continue
        if col_a and not col_b:
            section = col_a
            continue
        # Most sections use label|value, but some rows have it swapped
        # (e.g. an ID-shaped value sitting in column A). Detect by shape
        # instead of hardcoding a per-sheet/per-section exception.
        if ID_RE.fullmatch(col_a) and not ID_RE.fullmatch(col_b):
            label, value = col_b, col_a
        else:
            label, value = col_a, col_b
        alt_values = [v.strip() for v in col_c.split(",") if v.strip()]
        rows.append({"section": section, "label": label, "value": value, "alt_values": alt_values})
    return rows


def fetch_checklist(sheet_url: str) -> list[dict]:
    """Download and parse the checklist sheet into (section, label, value) rows."""
    url = sheet_csv_url(sheet_url)
    resp = requests.get(url, allow_redirects=True, timeout=30)
    if resp.status_code != 200 or "text/html" in resp.headers.get("content-type", ""):
        raise SystemExit(
            "Could not download the sheet as CSV (got HTML/error instead). "
            "Check the sheet is shared as 'Anyone with the link can view'."
        )
    return parse_checklist_csv(resp.text)


def checklist_fingerprint(rows: list[dict]) -> str:
    """A short digest of the checklist as parsed, for telling one revision apart.

    The build is only half of what an audit compares: the other half is the
    sheet, and the ads team edits it without anybody reinstalling the app. A run
    keyed on versionCode alone answers a question nobody asked -- "has the build
    changed" -- and quietly serves the previous verdict against a checklist that
    no longer says the same thing.

    Hashes the parsed rows rather than the CSV bytes, so a re-export, a changed
    comment column or a reordered blank line does not read as a new checklist,
    while any change to a section, label, value or alt value does.
    """
    canonical = [
        [r["section"], r["label"], r["value"], sorted(r.get("alt_values") or [])]
        for r in rows
    ]
    blob = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
