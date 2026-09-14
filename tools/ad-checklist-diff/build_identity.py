"""Decide whether the build a run audited is one worth auditing at all.

A checklist lists production values. A dev build serves the AdMob SDK's sample
ad units and points Adjust at sandbox, so nearly every checklist row misses --
and each miss reads like the sheet is wrong. One run spent hours that way: 45
rows reported as mismatches, then the release build of the same app matched all
54. Nothing was wrong except which APK was on the phone.

The signals are already in what the run collected, so nothing extra has to be
captured to notice: the leftover values carry every id and config token the log
printed but the checklist did not claim. Read from there rather than re-reading
the log, so this costs nothing and cannot disagree with the rest of the report.

This reports; it does not block. A run against a dev build is sometimes exactly
what someone wants, and a tool that refuses to run is worse than one that says
plainly what it is looking at.
"""
from apk_verifier import SAMPLE_PUBLISHERS

# Printed by the Adjust SDK when the build points at its test environment.
SANDBOX_MARKER = "sandbox"


def _observed(result: dict) -> list[str]:
    """Every value this run saw: matched rows plus the leftovers."""
    seen = [str(v) for v in (result.get("extra") or [])]
    for rows in (result.get("sections") or {}).values():
        seen += [str(row.get("value", "")) for row in rows if row.get("found")]
    return seen


def dev_build_signals(result: dict | None) -> list[str]:
    """Human-readable signs that this build is a dev/test build, if any."""
    if not result:
        return []
    observed = _observed(result)
    signals = []

    samples = {
        pub
        for pub in SAMPLE_PUBLISHERS
        for value in observed
        if f"ca-app-pub-{pub}" in value
    }
    if samples:
        signals.append(
            "quảng cáo chạy bằng ID mẫu của SDK "
            f"({', '.join(f'ca-app-pub-{p}' for p in sorted(samples))})"
        )

    # Whole-token match: "sandbox" inside a longer string is some other value.
    if any(SANDBOX_MARKER == value.strip().lower() for value in observed):
        signals.append("Adjust đang ở môi trường sandbox")

    return signals
