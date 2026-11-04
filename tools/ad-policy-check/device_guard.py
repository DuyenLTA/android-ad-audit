"""Keep one journey per phone, and notice when something else drives it anyway.

Lock: the same OS file lock rc-check and the build bot hold
(`<check_remote_config>/out/.may-<serial>.lock`), so a policy run, an rc-check
run and a bot install never share a device. The lock frees itself when the
process dies, so no stale lock is left behind.

Guard: a manual session that does not take the lock can still drive the phone.
That happened on the first flow-driven run (04/11/2026): another session launched
a different app with `monkey` mid-journey and every frame after it belonged to
that app. The guard checks each UI dump: a foreground app that is neither ours,
nor system UI, nor somewhere an ad tap legitimately leads, stops the run instead
of grading evidence from the wrong app.
"""
import os
from contextlib import contextmanager
from pathlib import Path

RC_REPO = Path(os.environ.get("RC_RUNNER_REPO", Path.home() / "Desktop" / "check_remote_config"))

# Packages that may own the screen during a normal journey of any app.
ALWAYS_ALLOWED = (
    "android", "com.android.systemui", "com.android.permissioncontroller",
    "com.google.android.permissioncontroller", "com.google.android.gms",
    "com.google.android.apps.nexuslauncher", "com.android.launcher3",
)
# Where tapping an ad may take the phone; only allowed right after our own ad tap.
AD_DESTINATIONS = ("com.android.vending", "com.android.chrome", "com.google.android.youtube",
                   "com.google.android.googlequicksearchbox", "com.google.android.webview")


class ForeignDriverError(RuntimeError):
    """The phone is showing an app this journey did not open."""


def lock_path(serial: str) -> Path:
    return RC_REPO / "out" / f".may-{serial}.lock"


def _try_lock(fd: int) -> bool:
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(fd: int) -> None:
    if os.name == "nt":
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)


@contextmanager
def hold_device(serial: str):
    """Hold the shared device lock for the block; BlockingIOError if another run has it."""
    path = lock_path(serial)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT)
    try:
        if not _try_lock(fd):
            raise BlockingIOError(f"máy {serial} đang có lượt khác giữ {path.name} (bot / rc-check)")
        try:
            yield
        finally:
            _unlock(fd)
    finally:
        os.close(fd)


def foreign_package(dump_packages: set[str], package: str, after_ad_tap: bool) -> str | None:
    """The first on-screen package that should not be there, or None."""
    for pkg in sorted(dump_packages):
        if not pkg or pkg == package or pkg in ALWAYS_ALLOWED:
            continue
        if after_ad_tap and pkg in AD_DESTINATIONS:
            continue
        return pkg
    return None
