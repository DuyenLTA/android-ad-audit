"""Download the Apero ads/subscription policy sheet and parse each tab into rules.

The policy sheet is written for people, not tools:
  - column A (N°) has gaps (1, 3, 12, 14 ...) and is sometimes empty;
  - column B (ad format / package type) is only filled on the first row of a group;
  - most rules live in column C, but some groups put a heading in C and the actual
    requirements on the following rows in column D with C left empty.

So a rule's text is column D when present, else column C; its topic is the last
non-empty column C; its group is the last non-empty column B. Rules are keyed by
(tab, N°) because N° is what QA quotes; a rule without N° gets a key derived from
its text so it can still be mapped and tracked.
"""
import csv
import hashlib
import io
import re
import sys
from pathlib import Path

import requests

# Shared sheet helpers live next door; the folder name has a hyphen so it is not a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ad-checklist-diff"))
from checklist_source import sheet_get  # noqa: E402

SHEET_ID = "17r_R39x2F8RyQDBgHUeq5jWwzAGS92yQNb9RXS4-NLA"
# Tab title -> gid. Titles are what QA and the checker map refer to.
TAB_GIDS = {"Ad_VN": "0", "Đối tác": "28661939", "Sub_VN": "1287330092", "Ads_ENG": "1833695982"}


def normalize_text(text: str) -> str:
    """Collapse whitespace so a re-typed line break does not read as a changed rule."""
    return re.sub(r"\s+", " ", text or "").strip()


def text_hash(text: str) -> str:
    """Short digest of a rule's wording, used to notice when a mapped rule was edited."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()[:8]


def _cell(cols: list[str], i: int) -> str:
    return cols[i].strip() if len(cols) > i else ""


def parse_policy_csv(csv_text: str, tab: str) -> list[dict]:
    """Parse one tab's CSV export into rule dicts (header row skipped)."""
    rows = list(csv.reader(io.StringIO(csv_text)))
    rules: list[dict] = []
    group = ""
    topic = ""
    for cols in rows[1:]:
        no, col_b, col_c, col_d = (_cell(cols, i) for i in range(4))
        if col_b:
            group = normalize_text(col_b)
        if col_c:
            topic = normalize_text(col_c)
        text = col_d or col_c
        if not text:
            continue
        rules.append({
            "tab": tab,
            "no": no or f"h{text_hash(text)}",
            "group": group,
            "topic": topic,
            "text": normalize_text(text),
            "good_example": _cell(cols, 4),
            "bad_example": _cell(cols, 5),
            "note": _cell(cols, 7),
            "text_hash": text_hash(text),
        })
    return rules


def tab_csv_url(tab: str) -> str:
    if tab not in TAB_GIDS:
        raise SystemExit(f"Unknown policy tab '{tab}'. Known: {', '.join(TAB_GIDS)}")
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={TAB_GIDS[tab]}"


def fetch_policy_tab(tab: str) -> list[dict]:
    """Download and parse one tab. Exits with a readable message on network/share errors."""
    url = tab_csv_url(tab)
    try:
        resp = sheet_get(url)
    except requests.RequestException as exc:
        raise SystemExit(f"Could not reach the policy sheet ({type(exc).__name__}): {url}")
    if resp.status_code != 200 or "text/html" in resp.headers.get("content-type", ""):
        raise SystemExit(
            f"Could not download policy tab '{tab}' as CSV (HTTP {resp.status_code}). "
            "Check the sheet is shared as 'Anyone with the link can view'."
        )
    resp.encoding = "utf-8"
    return parse_policy_csv(resp.text, tab)


def fetch_policy_rules(tabs: list[str]) -> list[dict]:
    """All rules of the given tabs, in sheet order."""
    rules: list[dict] = []
    for tab in tabs:
        rules.extend(fetch_policy_tab(tab))
    return rules
