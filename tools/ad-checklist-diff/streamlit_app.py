#!/usr/bin/env python3
"""Local GUI for check_ads.py -- no terminal needed.

Run with: streamlit run streamlit_app.py

This is a LOCAL app (runs adb on your machine). It is not a hosted/shareable
artifact -- the report it produces is a local HTML file rendered inline on
this page. If you want a shareable link, ask Claude to publish the saved
report file as an artifact in a chat turn.
"""
import os
import subprocess
import tempfile
from pathlib import Path

import streamlit as st

from check_ads import (
    diff,
    extract_key_cooccurrences,
    extract_key_value_pairs,
    extract_label_value_pairs,
    extract_values,
    fetch_checklist,
    load_trusted_lines,
    render_html,
)
from package_verifier import verify_package_rows

# Locked to this org's standard logcat filters -- not user-editable.
# UserMessagingPlatform/AdsConsentManager catch the AdMob App ID's own log
# line, which FOR_TESTER/VslTemplate4FirstOpenSDK never print.
# RemoteConfigRepository catches the "ID ads inapp" placement flags (e.g.
# `key=show_native_loading_high, value=true`), which have no dedicated tag
# of their own -- just a generic config dump at app start. inter_ads catches
# the interstitial high/normal price-floor decision (e.g.
# `loadDoubleIds: canShowHigh=true (key=X), canShowNormal=true (key=Y)`),
# which is where the mismatch-note co-occurrence hints come from for those
# rows. If a future app needs different filter names, change this list (or
# use the CLI's --filter flag directly for one-off apps that differ).
FILTERS = [
    "FOR_TESTER",
    "VslTemplate4FirstOpenSDK",
    "UserMessagingPlatform",
    "AdsConsentManager",
    "RemoteConfigRepository",
    "inter_ads",
]

st.set_page_config(page_title="Ad Checklist Diff", page_icon="\U0001f4cb")
st.title("Ad Checklist Diff")
st.caption(
    "Local tool -- runs adb on this machine. Enter the checklist sheet + "
    "filters, click Start, operate the phone (open the app, go to home), "
    "then click Stop to get the diff report."
)

if "capture_proc" not in st.session_state:
    st.session_state.capture_proc = None
    st.session_state.log_path = None
    st.session_state.run_sheet_url = None
    st.session_state.run_filters = None


def device_attached() -> bool:
    try:
        out = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, timeout=10
        ).stdout
    except FileNotFoundError:
        st.error("`adb` not found on PATH -- install Android platform-tools first.")
        return False
    lines = [ln for ln in out.splitlines()[1:] if ln.strip().endswith("device")]
    return len(lines) > 0


def new_temp_path(suffix: str, prefix: str) -> Path:
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    os.close(fd)
    return Path(path)


capturing = st.session_state.capture_proc is not None

sheet_url = st.text_input("Google Sheet checklist URL", disabled=capturing)
st.caption("Filters (fixed): " + ", ".join(f"`{f}`" for f in FILTERS))
filters = FILTERS

col1, col2 = st.columns(2)

if not capturing:
    if col1.button("Start", type="primary", disabled=not sheet_url or not filters, key="start_btn"):
        if not device_attached():
            st.error("No device attached -- check `adb devices` shows your phone.")
        else:
            # Snapshot the inputs at Start time -- they're disabled while
            # capturing, but pin them explicitly so Stop always diffs
            # against what was actually running, not whatever the widgets
            # happen to hold at Stop time.
            st.session_state.run_sheet_url = sheet_url
            st.session_state.run_filters = filters

            subprocess.run(["adb", "logcat", "-c"], capture_output=True)
            log_path = new_temp_path(suffix=".log", prefix="adcheck_")
            log_file = open(log_path, "w", encoding="utf-8")
            proc = subprocess.Popen(["adb", "logcat"], stdout=log_file, stderr=subprocess.STDOUT)
            log_file.close()  # child has its own dup'd fd; parent doesn't need this handle open
            st.session_state.capture_proc = proc
            st.session_state.log_path = log_path
            st.rerun()
else:
    st.info("Capturing -- operate the phone now (open the app, go to home), then click Stop.")
    if col1.button("Stop", type="primary", key="stop_btn"):
        proc = st.session_state.capture_proc
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_path = st.session_state.log_path
        run_sheet_url = st.session_state.run_sheet_url
        run_filters = st.session_state.run_filters
        st.session_state.capture_proc = None

        if not log_path.exists() or log_path.stat().st_size == 0:
            st.error("Captured 0 bytes -- adb may have disconnected. Try again.")
        else:
            try:
                with st.spinner("Diffing against the checklist..."):
                    checklist = fetch_checklist(run_sheet_url)
                    trusted_by_filter = load_trusted_lines(str(log_path), run_filters)
                    empty_filters = [f for f, lines in trusted_by_filter.items() if not lines]
                    all_lines = [line for lines in trusted_by_filter.values() for line in lines]
                    trusted_values = extract_values(all_lines)
                    label_value_pairs = extract_label_value_pairs(all_lines)
                    key_value_pairs = extract_key_value_pairs(all_lines)
                    key_cooccurrences = extract_key_cooccurrences(all_lines)
                    result = diff(
                        checklist, trusted_values, label_value_pairs, key_value_pairs, key_cooccurrences
                    )
                    verify_package_rows(result)

                    report_path = new_temp_path(suffix=".html", prefix="adcheck_report_")
                    render_html(result, empty_filters, str(report_path))
            except SystemExit as e:
                # check_ads' pipeline functions signal user-facing errors
                # (bad sheet URL, sheet not shared, ...) via SystemExit --
                # appropriate for the CLI, but Streamlit's own error
                # boundary only catches Exception, not BaseException, so an
                # uncaught SystemExit here would silently freeze the page
                # instead of showing an error.
                st.error(str(e))
            else:
                st.success(f"Report saved to: {report_path}")
                if empty_filters:
                    st.warning(f"These filters matched 0 log lines: {', '.join(empty_filters)}")
                st.link_button(
                    "\U0001f5a5️ Mở report toàn màn hình",
                    report_path.resolve().as_uri(),
                )
                st.caption(
                    "Link local (file trên máy này) -- không phải link claude.ai chia sẻ được. "
                    "Muốn có link chia sẻ, gửi lại report cho Claude ở 1 lượt chat."
                )
                st.components.v1.html(
                    report_path.read_text(encoding="utf-8"), height=1200, scrolling=True
                )
