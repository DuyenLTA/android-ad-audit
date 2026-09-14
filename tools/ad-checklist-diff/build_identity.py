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

# What a dev build says about itself in the log, and how soon. Both of these
# appear within about a second of launch, long before the journey is over, so a
# run that watches for them can stop driving instead of walking every screen of
# a build whose report nobody should read.
DEV_LOG_MARKERS = (
    ("Config variant dev: true", "build tự khai Config variant dev: true"),
    ("setupAdjust: sandbox", "build tự khai Adjust environment = sandbox"),
)

# Enough overlap between reads that a marker landing across a chunk boundary is
# still seen whole.
_TAIL = max(len(marker) for marker, _ in DEV_LOG_MARKERS)


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


def log_watcher(path: str, flush=None):
    """A callable that reports, once, that the log names this a dev build.

    Reads only what has arrived since the last call, so it can be polled on the
    journey's own loop without re-reading a capture that grows to megabytes.
    Returns a reason string, or None to carry on.
    """
    state = {"offset": 0, "tail": ""}

    def check() -> str | None:
        if flush:
            flush()
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                handle.seek(state["offset"])
                chunk = handle.read()
                state["offset"] = handle.tell()
        except OSError:
            # The capture file not being readable yet is not an answer about
            # the build; the next poll asks again.
            return None
        if not chunk:
            return None
        text = state["tail"] + chunk
        state["tail"] = text[-_TAIL:]
        for marker, reason in DEV_LOG_MARKERS:
            if marker in text:
                return reason
        return None

    return check
