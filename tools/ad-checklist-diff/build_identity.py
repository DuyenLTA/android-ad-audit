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


def app_lines(lines, package: str) -> list[str] | None:
    """Lines of a device-wide `logcat -v threadtime` capture printed by `package`'s own processes.

    The capture is device-wide: another app built on the same Apero lib, running
    in its dev variant, printed `setupAdjust: sandbox` into the capture of a
    release build and the audit refused it (10/11/2026, AI Art 3.9.0 vs a
    status-saver app restarting in the background). ART logs each process start
    under a tag equal to the last 15 characters of the process name, so the
    app's PIDs can be read from the capture itself. None when no such line is
    found -- the caller then judges the whole capture as before.
    """
    tag = package[-15:]
    lines = list(lines)
    pids = set()
    for line in lines:
        parts = line.split(None, 6)
        if len(parts) >= 6 and parts[2].isdigit() and parts[5].rstrip(":") == tag:
            pids.add(parts[2])
    if not pids:
        return None
    return [ln for ln in lines if (p := ln.split(None, 3)) and len(p) >= 3 and p[2] in pids]


def dev_build_signals(result: dict | None, own_lines: list[str] | None = None) -> list[str]:
    """Human-readable signs that this build is a dev/test build, if any.

    `own_lines`: the audited app's own log lines (`app_lines`). Given, a sign
    counts only when its evidence appears in those lines, not in another app's.
    """
    if not result:
        return []
    observed = _observed(result)
    signals = []
    own_text = "\n".join(own_lines) if own_lines is not None else None

    samples = {
        pub
        for pub in SAMPLE_PUBLISHERS
        for value in observed
        if f"ca-app-pub-{pub}" in value
        and (own_text is None or f"ca-app-pub-{pub}" in own_text)
    }
    if samples:
        signals.append(
            "quảng cáo chạy bằng ID mẫu của SDK "
            f"({', '.join(f'ca-app-pub-{p}' for p in sorted(samples))})"
        )

    # Whole-token match: "sandbox" inside a longer string is some other value.
    if any(SANDBOX_MARKER == value.strip().lower() for value in observed) and (
        own_text is None
        or any(SANDBOX_MARKER in ln.lower() and "adjust" in ln.lower() for ln in own_lines)
    ):
        signals.append("Adjust đang ở môi trường sandbox")

    return signals


def _line_pid(line: str) -> str | None:
    """PID column of a `logcat -v threadtime` line (`MM-DD hh:mm:ss.mmm PID TID L TAG: msg`)."""
    parts = line.split(None, 3)
    return parts[2] if len(parts) >= 3 and parts[2].isdigit() else None


def log_watcher(path: str, flush=None, pids=None):
    """A callable that reports, once, that the log names this a dev build.

    Reads only what has arrived since the last call, so it can be polled on the
    journey's own loop without re-reading a capture that grows to megabytes.
    Returns a reason string, or None to carry on.

    `pids`: callable -> set of PID strings of the audited app. The capture holds
    the whole device log, and other apps built on the same Apero lib print the
    same marker: a phone with a second Apero app in its dev variant stopped the
    audit of a release build (10/11/2026, PID of another package said
    "Config variant dev: true" while the audited app said false). With `pids`,
    only marker lines from the audited app count; a line whose PID cannot be
    read still counts, so a log without threadtime columns is judged as before.
    """
    state = {"offset": 0, "tail": ""}

    def _hit(text: str, marker: str) -> bool:
        if marker not in text:
            return False
        if pids is None:
            return True
        app = None
        for line in text.splitlines():
            if marker not in line:
                continue
            pid = _line_pid(line)
            if pid is None:
                return True
            if app is None:
                app = pids() or set()
            if pid in app:
                return True
        return False

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
            if _hit(text, marker):
                return reason
        return None

    return check
