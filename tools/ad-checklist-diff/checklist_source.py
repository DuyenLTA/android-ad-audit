"""Fetch and parse the Google Sheet checklist into (section, label, value) rows."""
import csv
import io
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
    """Parse checklist CSV text into (section, label, value) rows."""
    reader = csv.reader(io.StringIO(csv_text))
    rows = []
    section = "(no section)"
    for cols in reader:
        col_a = (cols[0].strip() if len(cols) > 0 else "")
        col_b = (cols[1].strip() if len(cols) > 1 else "")
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
        rows.append({"section": section, "label": label, "value": value})
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
