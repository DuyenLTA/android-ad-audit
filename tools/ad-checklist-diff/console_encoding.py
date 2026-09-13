"""Make this tool's own output survive a non-UTF-8 console.

Every message these scripts print is Vietnamese. Python picks the console's
locale encoding for stdout, which on a Windows machine is cp1252 -- a codec
with no Vietnamese in it. A single `pm clear ... xoá dữ liệu` progress line was
enough to kill a whole capture run with UnicodeEncodeError, after the phone had
already been driven.

The text is not the problem and neither is the console: only the choice of
codec between them. Reconfiguring the streams to UTF-8 fixes it at the one
place it goes wrong, and `errors="replace"` guarantees that a stream which
still cannot represent some character degrades to a visible marker instead of
taking the run down with it.
"""
import sys


def use_utf8_console() -> None:
    """Print UTF-8 on stdout/stderr regardless of the console's locale."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:  # a redirected stream that is not a TextIOWrapper
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):  # already detached, or closed
            pass
