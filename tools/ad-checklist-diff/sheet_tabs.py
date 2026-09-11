"""Which checklist tab belongs to which app, asked of the sheet itself.

Tab names are project codes and the phone shows a shortened app name, so the two
never match on text. But every tab carries a `Package name` row, and that is an
exact identifier -- so the mapping is read rather than guessed.

The tab list comes from the sheet's own htmlview page, which exposes each tab's
`gid` without needing an API key; the sheet is already shared "anyone with the
link can view" for the checklist download to work at all.

Results are cached per sheet, because tabs change far more slowly than runs
happen. `refresh=True` re-reads when an app was just added.
"""
import json
import os
import re

import requests

from apk_source import CACHE_DIR
from checklist_source import sheet_csv_url
from package_verifier import is_package_name

TAB_CACHE = os.path.join(CACHE_DIR, "sheet-tabs.json")
GID_RE = re.compile(r"gid=(\d+)")
SHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")


def sheet_id(sheet_url: str) -> str:
    found = SHEET_ID_RE.search(sheet_url)
    if not found:
        raise SystemExit(f"Không phải URL Google Sheet: {sheet_url}")
    return found.group(1)


def tab_gids(sheet_url: str, get=requests.get) -> list[str]:
    """Every tab's gid, in the order the sheet lists them."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id(sheet_url)}/htmlview"
    resp = get(url, timeout=30)
    seen, gids = set(), []
    for gid in GID_RE.findall(resp.text):
        if gid not in seen:
            seen.add(gid)
            gids.append(gid)
    return gids


def tab_package(sheet_url: str, gid: str, get=requests.get) -> str | None:
    """The package a tab declares, from its own `Package name` row."""
    url = sheet_csv_url(f"{sheet_url.split('#')[0].split('?')[0]}?gid={gid}")
    resp = get(url, timeout=30)
    for line in resp.text.splitlines():
        for cell in line.split(","):
            cell = cell.strip().strip('"')
            if is_package_name(cell):
                return cell
    return None


def _load_cache() -> dict:
    try:
        with open(TAB_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(TAB_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def gids_by_package(
    sheet_url: str,
    refresh: bool = False,
    gids_fn=tab_gids,
    package_fn=tab_package,
) -> dict[str, list[str]]:
    """package -> the gids whose tab declares it.

    A list, not a single gid: a sheet can hold two tabs for the same app, and
    picking one of them silently is how a run diffs against the wrong checklist.
    """
    cache = _load_cache()
    key = sheet_id(sheet_url)
    if not refresh and key in cache:
        return cache[key]

    mapping: dict[str, list[str]] = {}
    for gid in gids_fn(sheet_url):
        package = package_fn(sheet_url, gid)
        if package:
            mapping.setdefault(package, []).append(gid)

    cache[key] = mapping
    _save_cache(cache)
    return mapping
