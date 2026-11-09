"""Tap each kind of ad once and record whether the tap went anywhere.

Policy: "Bắt buộc có xử lý khi click vào ad / CTA". Handled = within a few
seconds the foreground leaves the app (browser, Play Store) or the ad SDK opens
its own activity. After looking, BACK returns to the app; the flow runner then
carries on and closes the ad itself.

Every device the team uses is an AdMob test device, so tapping ads is allowed.
Each kind is probed a bounded number of times so a journey full of ads does not
turn into a journey full of browser trips.
"""
import asyncio
import json
import re
import time
from pathlib import Path

from adb_sync import a_key, a_tap, a_top_activity, safe_dump
from device_close_button import find_close_center
from ui_nodes import norm_activity, banner_node, center, first, is_fullscreen_ad_activity, native_parts, parse_nodes

HANDLED_WAIT_SECONDS = 3.0
MAX_BACKS = 3
MAX_FULLSCREEN_PROBES = 3
# Returning from Chrome / Play, the app re-resumes (and may reload its native). A tap
# by the flow runner in that moment was swallowed and the journey stalled on Language.
RETURN_SETTLE_SECONDS = 3.0
# Full-screen ads whose X is drawn outside the accessibility tree: tap after this long
# (short: rc-check's driver BACK-closes a test ad with no X node after ~5s).
FULLSCREEN_MIN_SHOWN_SECONDS = 2.0
# A tap may leave the phone in Play / Chrome for a while; the guard tolerates that this long.
AFTER_TAP_GRACE_SECONDS = 15
# Call-to-action words of full-screen creatives (test and real). Tapping the middle of a
# video creative often does nothing, which would read as "click not handled".
PAYWALL_MARKERS = ("Billing", "Paywall", "Premium", "Subscription", "Iap", "Purchase")
PRIVACY_RE = re.compile(r"privacy|quyền riêng tư|chính sách bảo mật", re.I)
FULLSCREEN_CTA_WORDS = ("learn more", "install", "open", "visit", "download", "get", "shop", "play")


class ClickProber:
    def __init__(self, serial: str, package: str, screen: tuple[int, int], out_dir: Path, t0: float):
        self.serial = serial
        self.package = package
        self.width, self.height = screen
        self.log_path = out_dir / "click-probes.jsonl"
        self.t0 = t0
        self.in_fullscreen = False
        self.fullscreen_tapped = False
        self.fullscreen_probes = 0
        self.fullscreen_seen = 0
        self.fullscreen_since = 0.0
        self.native_done: set[str] = set()
        self.banner_done: set[str] = set()
        self.paywall_link_done = False
        self.last_tap = 0.0
        self.reward_running = False

    def recently_tapped(self) -> bool:
        return time.monotonic() - self.last_tap < AFTER_TAP_GRACE_SECONDS

    def _ms(self) -> int:
        return int((time.monotonic() - self.t0) * 1000)

    async def _foreground(self) -> str | None:
        try:
            return norm_activity(await a_top_activity(self.serial))
        except Exception:
            return None

    async def _tap_and_observe(self, kind: str, activity: str, xy: tuple[int, int], extra: dict | None = None) -> dict:
        before = norm_activity(activity)
        t = self._ms()
        self.last_tap = time.monotonic()
        await a_tap(self.serial, *xy)
        after = before
        deadline = time.monotonic() + HANDLED_WAIT_SECONDS
        while time.monotonic() < deadline:
            await asyncio.sleep(0.5)
            after = await self._foreground() or after
            if after != before:
                break
        left_app = bool(after) and not after.startswith(self.package + "/")
        # An ad tap is handled when it leads out of the app (browser / Play / another app) or opens a
        # full-screen ad page. A plain change to another app screen may be the app's own navigation
        # behind the ad: "unclear", for a person to look at.
        if after == before:
            handled = False
        elif left_app or is_fullscreen_ad_activity(after) or kind == "paywall_privacy":
            handled = True
        else:
            handled = "unclear"
        record = {"t": t, "kind": kind, "activity": before, "tap": list(xy),
                  "after": after, "handled": handled, "left_app": left_app, **(extra or {})}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        # Come back to where the tap started, so the flow runner finds its screen.
        for _ in range(MAX_BACKS):
            now = await self._foreground()
            if now == before or (now and now.startswith(self.package + "/") and not left_app):
                break
            await a_key(self.serial, "KEYCODE_BACK")
            await asyncio.sleep(1.5)
        await asyncio.sleep(RETURN_SETTLE_SECONDS)
        return record

    def _cta_after_pause(self) -> tuple[int, int] | None:
        """A first tap on a video creative often only pauses it and reveals a CTA ("More", "Install"...)."""
        nodes = parse_nodes(safe_dump(self.serial, "/sdcard/policy-probe.xml"))
        cta = first(nodes, lambda n: (n["text"] or n["desc"]).strip().lower() in FULLSCREEN_CTA_WORDS + ("more",))
        return center(cta["bounds"]) if cta else None

    async def _close_fullscreen_with_back(self) -> None:
        """After a tap the creative is paused and its X may never come; BACK closes it."""
        for _ in range(MAX_BACKS):
            if not is_fullscreen_ad_activity(await self._foreground()):
                return
            await a_key(self.serial, "KEYCODE_BACK")
            await asyncio.sleep(1.5)

    async def _probe_fullscreen(self, activity: str, nodes: list[dict], xml: str) -> bool:
        if not self.in_fullscreen:          # a new full-screen ad just opened
            self.in_fullscreen = True
            self.fullscreen_tapped = False
            self.fullscreen_seen += 1
            self.fullscreen_since = time.monotonic()
        # The first full-screen ad of a journey is never tapped: it is the one the video
        # measures for "close button within 15s". Tapping pauses a video creative and its
        # X then never appears (seen on device), which would make that measurement lie.
        if self.fullscreen_seen < 2 or self.fullscreen_tapped or self.fullscreen_probes >= MAX_FULLSCREEN_PROBES:
            return False
        close_visible = find_close_center(xml) is not None
        shown_long_enough = time.monotonic() - self.fullscreen_since >= FULLSCREEN_MIN_SHOWN_SECONDS
        if not (close_visible or shown_long_enough):
            return False
        self.fullscreen_tapped = True
        self.fullscreen_probes += 1
        await self.tap_fullscreen("fullscreen", activity, nodes)
        await self._close_fullscreen_with_back()
        return True

    async def tap_fullscreen(self, kind: str, activity: str, nodes: list[dict]) -> None:
        """Tap a full-screen creative's CTA (or its middle); if that only paused it, tap the CTA it revealed."""
        cta = first(nodes, lambda n: n["text"].strip().lower() in FULLSCREEN_CTA_WORDS)
        # No labelled CTA: middle of the creative, below the header where close/skip live.
        xy = center(cta["bounds"]) if cta else (self.width // 2, int(self.height * 0.55))
        rec = await self._tap_and_observe(kind, activity, xy)
        if rec["handled"] is False and is_fullscreen_ad_activity(await self._foreground()):
            xy2 = await asyncio.to_thread(self._cta_after_pause)
            if xy2:
                await self._tap_and_observe(kind, activity, xy2, {"follow_up_of": rec["t"]})

    async def maybe_probe(self, activity: str | None, nodes: list[dict], xml: str) -> bool:
        """Probe at most one ad on this screen. True when a tap happened (caller re-dumps)."""
        if not activity:
            return False
        if is_fullscreen_ad_activity(activity):
            if self.reward_running:       # a rewarded ad being watched for its reward: hands off
                return False
            return await self._probe_fullscreen(activity, nodes, xml)
        self.in_fullscreen = False
        if not activity.startswith(self.package + "/"):
            return False
        if not self.paywall_link_done and any(m in activity for m in PAYWALL_MARKERS):
            link = first(nodes, lambda n: bool(PRIVACY_RE.search(n["text"] or n["desc"])))
            if link:
                self.paywall_link_done = True
                await self._tap_and_observe("paywall_privacy", activity, center(link["bounds"]))
                # An in-app page is still "the app": leave it so the driver finds the paywall again.
                if await self._foreground() != activity:
                    await a_key(self.serial, "KEYCODE_BACK")
                    await asyncio.sleep(RETURN_SETTLE_SECONDS)
                return True
        parts = native_parts(nodes)
        # Only a settled native: AdChoices is drawn by the SDK once a real ad is bound, and
        # the loading shimmer is gone. Tapping earlier hit the view while the app was
        # swapping a freshly loaded ad into it, and read as "click not handled".
        settled = parts["adchoices"] is not None and parts["shimmer"] is None
        if parts["native"] and parts["cta"] and settled and activity not in self.native_done:
            self.native_done.add(activity)
            await self._tap_and_observe("native_cta", activity, center(parts["cta"]["bounds"]))
            return True
        banner = banner_node(nodes)
        if banner and activity not in self.banner_done:
            self.banner_done.add(activity)
            await self._tap_and_observe("banner", activity, center(banner["bounds"]))
            return True
        return False
