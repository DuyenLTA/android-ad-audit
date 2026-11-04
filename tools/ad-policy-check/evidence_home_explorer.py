"""After the FO journey reaches Home: visit the screens the policy rules talk about.

rc-check's driver stops at Home; the rules also need
  - utility screens (Privacy, Terms, Rate, Feedback, Share...) and what happens on
    the way back: no resume ad may show (Đối tác #7, #8);
  - content screens, where banners / reward entry points live;
  - the paywall reached from Home (Pro / Premium), for the Sub rules.

Generic on purpose: entries are found by words and ids every Apero app uses, the
visit count is bounded, and anything that looks like a purchase or a destructive
action is never tapped here (the purchase pass is separate, see evidence_sub_purchase).
"""
import asyncio
import json
import re
import time
from pathlib import Path

from adb_sync import a_key, a_tap, a_top_activity, adb, safe_dump
from ui_nodes import center, is_fullscreen_ad_activity, parse_nodes

CLOSE_RE = re.compile(r"^(close|đóng|x|skip|bỏ qua|later|not now|để sau)$", re.I)
SETTINGS_RE = re.compile(r"setting|cài đặt|menu|more$", re.I)
UTILITY_RE = re.compile(r"privacy|policy|chính sách|term|điều khoản|rate|đánh giá|feedback|góp ý|share|chia sẻ|"
                        r"about|version|update|cập nhật", re.I)
PRO_RE = re.compile(r"^(pro|premium|vip|upgrade|go pro|nâng cấp)$|premium|iap|subscription", re.I)
CONTENT_RE = re.compile(r"try now|see all|xem tất cả|create|tạo|generate|start|explore", re.I)
NEVER_RE = re.compile(r"delete|xoá|xóa|remove|log ?out|đăng xuất|subscribe|buy|purchase|continue|tiếp tục|"
                      r"add widget|check-in|restore", re.I)
SAMPLE_RE = re.compile(r"^(sample|ảnh mẫu|mẫu)$", re.I)
NEED_RE = re.compile(r"(choose|chọn)\s*(\d+)\s*(photo|ảnh)", re.I)
GO_RE = re.compile(r"^(continue|generate|tiếp tục|tạo|create)$", re.I)
RESULT_RE = re.compile(r"download|tải xuống|save|lưu|share|chia sẻ|report|báo cáo", re.I)
GENERATE_WAIT_SECONDS = 120
RESUME_WATCH_SECONDS = 6
MAX_UTILITIES = 5
MAX_CONTENT = 2


def _label(n: dict) -> str:
    return (n["text"] or n["desc"] or n["rid"]).strip()


class HomeExplorer:
    def __init__(self, serial: str, package: str, ev, out_dir: Path):
        self.serial, self.package, self.ev = serial, package, ev
        self.log = out_dir / "utility-visits.jsonl"
        self.t0 = ev.t0

    def _ms(self) -> int:
        return int((time.monotonic() - self.t0) * 1000)

    async def look(self) -> tuple[str, list[dict]]:
        """Dump + screenshot as evidence (and let the prober tap any settled ad on it)."""
        xml = await asyncio.to_thread(self._dump)
        activity = await a_top_activity(self.serial) or ""
        nodes = parse_nodes(xml)
        if activity.startswith(self.package + "/"):
            await self.ev(activity.split("/", 1)[1], xml)
        return activity, nodes

    def _dump(self) -> str:
        return safe_dump(self.serial, "/sdcard/policy-home.xml")

    def _find(self, nodes: list[dict], pattern: re.Pattern, limit: int = 99) -> list[dict]:
        seen, out = set(), []
        for n in nodes:
            lab = _label(n)
            if not lab or lab in seen or NEVER_RE.search(lab) or not pattern.search(lab):
                continue
            target = n if n["clickable"] else self._clickable_parent(nodes, n)
            if target:
                seen.add(lab)
                out.append({**target, "label": lab})
        return out[:limit]

    @staticmethod
    def _clickable_parent(nodes: list[dict], child: dict) -> dict | None:
        b = child["bounds"]
        boxes = [n for n in nodes if n["clickable"] and n["bounds"][0] <= b[0] and n["bounds"][1] <= b[1]
                 and n["bounds"][2] >= b[2] and n["bounds"][3] >= b[3]]
        return min(boxes, key=lambda n: (n["bounds"][2] - n["bounds"][0]) * (n["bounds"][3] - n["bounds"][1])) \
            if boxes else None

    async def back_to_app(self, tries: int = 4, stop_at_ad: bool = False) -> str | None:
        """BACK until an app screen shows. With `stop_at_ad`, stop on a full-screen ad and return it:
        pressing BACK on a resume ad would close the very thing the utility rule watches for."""
        for _ in range(tries):
            act = await a_top_activity(self.serial) or ""
            if stop_at_ad and is_fullscreen_ad_activity(act):
                return act
            if act.startswith(self.package + "/") and not is_fullscreen_ad_activity(act):
                return None
            await a_key(self.serial, "KEYCODE_BACK")
            await asyncio.sleep(1.5)
        return None

    async def close_popups(self) -> None:
        for _ in range(3):
            _act, nodes = await self.look()
            closes = [n for n in nodes if n["clickable"] and CLOSE_RE.match(_label(n))] or \
                     [p for n in nodes if CLOSE_RE.match(_label(n)) and (p := self._clickable_parent(nodes, n))]
            if not closes:
                return
            # The popup drawn last sits on top; its close control comes last in the dump.
            await a_tap(self.serial, *center(closes[-1]["bounds"]))
            await asyncio.sleep(1.5)

    async def _watch_for_ad(self) -> str | None:
        end = time.monotonic() + RESUME_WATCH_SECONDS
        while time.monotonic() < end:
            act = await a_top_activity(self.serial)
            if is_fullscreen_ad_activity(act):
                return act
            await asyncio.sleep(0.5)
        return None

    async def visit_utility(self, node: dict, home_activity: str) -> None:
        t = self._ms()
        await a_tap(self.serial, *center(node["bounds"]))
        await asyncio.sleep(3)
        where, _nodes = await self.look()
        left_app = bool(where) and not where.startswith(self.package + "/")
        ad = None
        if left_app:
            ad = await self.back_to_app(stop_at_ad=True)
            way = "sang app/web khác rồi BACK về"
        else:
            # Shown inside the app: hide and reopen from the launcher, the other case of the rule.
            await a_key(self.serial, "KEYCODE_HOME")
            await asyncio.sleep(4)
            adb(self.serial, "shell", "monkey", "-p", self.package, "-c", "android.intent.category.LAUNCHER", "1")
            way = "mở trong app, ẩn app rồi mở lại"
        ad = ad or await self._watch_for_ad()
        if ad:
            await asyncio.sleep(6)  # let the countdown run before closing
            await self.back_to_app()
        rec = {"t": t, "label": node["label"], "opened": where, "left_app": left_app, "way": way,
               "ad_after": ad, "from": home_activity}
        with self.log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        await self.back_to_app()
        # Back on the screen the entry was on (BACK from an in-app page).
        now = await a_top_activity(self.serial)
        if now != home_activity:
            await a_key(self.serial, "KEYCODE_BACK")
            await asyncio.sleep(1.5)

    async def generate_ai_result(self, nodes: list[dict]) -> bool:
        """On a photo picker that offers sample photos: pick as many as it asks, generate, keep the result screen.

        The AI rule (report button on generated content) needs a real result; sample photos make
        that possible without seeding the phone's gallery.
        """
        label = next((n for n in nodes if SAMPLE_RE.match((n["text"] or "").strip())), None)
        if not label:
            return False
        need = next((int(m.group(2)) for n in nodes if (m := NEED_RE.search(n["text"] or ""))), 1)
        below = sorted((n for n in nodes if n["clickable"] and n["bounds"][1] > label["bounds"][3]
                        and n["bounds"][1] < label["bounds"][3] + 400), key=lambda n: n["bounds"][0])
        for n in below[:need]:
            await a_tap(self.serial, *center(n["bounds"]))
            await asyncio.sleep(1.5)
        _a, nodes = await self.look()
        go = next((p for n in nodes if GO_RE.match((n["text"] or "").strip())
                   and (p := n if n["clickable"] else self._clickable_parent(nodes, n))), None)
        if not go:
            return False
        await a_tap(self.serial, *center(go["bounds"]))
        end = time.monotonic() + GENERATE_WAIT_SECONDS
        while time.monotonic() < end:
            await asyncio.sleep(4)
            act = await a_top_activity(self.serial) or ""
            if is_fullscreen_ad_activity(act):
                continue                      # an ad while generating; the countdown runs on
            _a, nodes = await self.look()
            if sum(1 for n in nodes if RESULT_RE.search(n["text"] or n["desc"])) >= 2:
                await self.close_popups()     # e.g. a "rate us" dialog over the result
                await self.look()
                return True
        return False

    async def explore(self) -> dict:
        await self.close_popups()
        home, nodes = await self.look()
        done = {"utilities": 0, "content": 0, "paywall": False}
        for n in self._find(nodes, CONTENT_RE, MAX_CONTENT):
            await a_tap(self.serial, *center(n["bounds"]))
            await asyncio.sleep(3)
            if await self._watch_for_ad():        # an inter on content entry: let X come, then BACK
                await asyncio.sleep(6)
                await self.back_to_app()
            _a, seen = await self.look()
            done["content"] += 1
            if not done.get("ai_result"):
                done["ai_result"] = await self.generate_ai_result(seen)
                if done["ai_result"]:
                    await a_key(self.serial, "KEYCODE_BACK")
                    await asyncio.sleep(2)
            await a_key(self.serial, "KEYCODE_BACK")
            await asyncio.sleep(2)
            await self.back_to_app()
            await self.close_popups()
        _home, nodes = await self.look()
        settings = self._find(nodes, SETTINGS_RE, 1)
        if settings:
            await a_tap(self.serial, *center(settings[0]["bounds"]))
            await asyncio.sleep(2.5)
            screen, nodes = await self.look()
            for u in self._find(nodes, UTILITY_RE, MAX_UTILITIES):
                await self.visit_utility(u, screen)
                done["utilities"] += 1
            await a_key(self.serial, "KEYCODE_BACK")
            await asyncio.sleep(2)
            await self.back_to_app()
        _home, nodes = await self.look()
        pro = self._find(nodes, PRO_RE, 1)
        if pro:
            await a_tap(self.serial, *center(pro[0]["bounds"]))
            await asyncio.sleep(3)
            await self.look()
            done["paywall"] = True
        return done
