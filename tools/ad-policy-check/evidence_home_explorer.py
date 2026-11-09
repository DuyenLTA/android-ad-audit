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
from device_close_button import find_close_center
from ui_nodes import center, is_fullscreen_ad_activity, parse_nodes

CLOSE_RE = re.compile(r"^(close|đóng|x|skip|bỏ qua|later|not now|để sau)$", re.I)
# Icon-only close buttons carry no text, only an id: the rate dialog's "btnDismiss", "ivClose", "img_close"...
CLOSE_ID_RE = re.compile(r"(^|[_/])(btn|iv|img|ic|image|button)?_?(close|dismiss|cancel|exit)$", re.I)
UPLOAD_RE = re.compile(r"tap to upload|upload (image|photo)|add (image|photo)|tải ảnh|chọn ảnh|thêm ảnh", re.I)
PROMPT_TEXT = "a cute cat in a garden"
SETTINGS_RE = re.compile(r"setting|cài đặt|menu|more$", re.I)
UTILITY_RE = re.compile(r"privacy|policy|chính sách|term|điều khoản|rate|đánh giá|feedback|góp ý|share|chia sẻ|"
                        r"about|version|update|cập nhật", re.I)
PRO_RE = re.compile(r"^(pro|premium|vip|upgrade|go pro|nâng cấp)$|premium|iap|subscription", re.I)
CONTENT_RE = re.compile(r"try now|see all|xem tất cả|create|tạo|generate|start|explore", re.I)
NEVER_RE = re.compile(r"delete|xoá|xóa|remove|log ?out|đăng xuất|subscribe|buy|purchase|continue|tiếp tục|"
                      r"add widget|check-in|restore", re.I)
SAMPLE_RE = re.compile(r"^(sample|ảnh mẫu|mẫu)$", re.I)
NEED_RE = re.compile(r"(choose|chọn)\s*(\d+)\s*(photo|ảnh)", re.I)
WATCH_AD_RE = re.compile(r"watch (an )?ad|xem (quảng cáo|qc)|xem ad", re.I)
CONFIRM_LEAVE_RE = re.compile(r"^(confirm|yes|ok|discard|exit|leave|đồng ý|xác nhận|thoát|có)$", re.I)
REWARD_MAX_SECONDS = 45
PHOTO_DESC_RE = re.compile(r"^(photo|ảnh|image|picture|hình)|photo taken|ảnh chụp", re.I)
DONE_RE = re.compile(r"^(done|add|select|ok|xong|thêm|chọn|use|dùng)$", re.I)
GO_RE = re.compile(r"^(continue|generate|tiếp tục|tạo|create)$", re.I)
RESULT_RE = re.compile(r"download|tải xuống|save|lưu|share|chia sẻ|report|báo cáo", re.I)
GENERATE_WAIT_SECONDS = 120
RESUME_WATCH_SECONDS = 6
MAX_UTILITIES = 5
MAX_CONTENT = 2


def _label(n: dict) -> str:
    return (n["text"] or n["desc"] or n["rid"]).strip()


def photo_tiles(nodes: list[dict]) -> list[dict]:
    """Photo cells of a picker, top-left first. The system picker labels them "Photo taken on …"; other
    pickers get the square cells of at least 200px (tabs and the Cancel button are neither)."""
    def square(n):
        w, h = n["bounds"][2] - n["bounds"][0], n["bounds"][3] - n["bounds"][1]
        return w >= 200 and abs(w - h) <= 0.2 * w
    named = [n for n in nodes if n["clickable"] and PHOTO_DESC_RE.search(n["desc"] or "")]
    tiles = named or [n for n in nodes if n["clickable"] and square(n)]
    return sorted(tiles, key=lambda n: (n["bounds"][1], n["bounds"][0]))


def popup_closes(nodes: list[dict], package: str) -> list[dict]:
    """Close controls of a popup: by label first, then icon-only buttons known by their id."""
    return [n for n in nodes if n["clickable"] and CLOSE_RE.match(_label(n))] or \
        [p for n in nodes if CLOSE_RE.match(_label(n)) and (p := HomeExplorer._clickable_parent(nodes, n))] or \
        [n for n in nodes if n["clickable"] and n["pkg"] == package and not (n["text"] or n["desc"])
         and CLOSE_ID_RE.search(n["rid"])]


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
            closes = popup_closes(nodes, self.package)
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

    def gallery_box(self, nodes: list[dict], need_label: dict | None) -> dict | None:
        """The box that opens the photo picker: the "Tap to Upload" area, else the biggest app box above
        "Choose N photo" (the sample row is replaced by a native ad when the app is not Pro)."""
        # The section title ("Upload image") matches too but is not tappable: take the first that is.
        for n in nodes:
            if UPLOAD_RE.search(n["text"] or n["desc"] or ""):
                target = n if n["clickable"] else self._clickable_parent(nodes, n)
                if target:
                    return target
        if not need_label:
            return None
        boxes = [n for n in nodes if n["clickable"] and n["pkg"] == self.package
                 and n["bounds"][3] <= need_label["bounds"][1] and n["bounds"][1] > 200]
        return max(boxes, key=lambda n: (n["bounds"][2] - n["bounds"][0]) * (n["bounds"][3] - n["bounds"][1])) \
            if boxes else None

    async def fill_prompt(self, nodes: list[dict]) -> None:
        """Image/Text-to-X screens keep Generate disabled until the prompt box has text."""
        box = next((n for n in nodes if "EditText" in n["cls"] and n["pkg"] == self.package), None)
        if not box:
            return
        await a_tap(self.serial, *center(box["bounds"]))
        await asyncio.sleep(1)
        adb(self.serial, "shell", "input", "text", PROMPT_TEXT.replace(" ", "%s"))
        await asyncio.sleep(1)
        # Hide the keyboard so Generate is not covered; BACK only while it shows, or BACK leaves the screen.
        if "mInputShown=true" in await asyncio.to_thread(adb, self.serial, "shell", "dumpsys", "input_method"):
            await a_key(self.serial, "KEYCODE_BACK")
            await asyncio.sleep(1)

    async def pick_from_gallery(self, nodes: list[dict], need_label: dict | None, need: int) -> bool:
        """Open the gallery box and pick N photos from whatever picker opens, then come back."""
        box = self.gallery_box(nodes, need_label)
        if not box:
            return False
        picked = 0
        for _ in range(need):
            await a_tap(self.serial, *center(box["bounds"]))
            await asyncio.sleep(3.5)
            xml = await asyncio.to_thread(self._dump)
            await asyncio.to_thread(self.ev.save, xml)      # the picker screen, whoever owns it
            tiles = photo_tiles(parse_nodes(xml))
            if not tiles:
                await self.back_to_app()
                return picked > 0
            await a_tap(self.serial, *center(tiles[min(picked, len(tiles) - 1)]["bounds"]))
            await asyncio.sleep(2)
            after = parse_nodes(await asyncio.to_thread(self._dump))
            done = next((n for n in after if n["clickable"] and DONE_RE.match((n["text"] or n["desc"]).strip())), None)
            if done:
                await a_tap(self.serial, *center(done["bounds"]))
                await asyncio.sleep(2)
            await self.back_to_app(tries=2)
            picked += 1
            _a, nodes = await self.look()
            if not any(n["desc"] == "Empty Slot" for n in nodes):
                break
        return picked > 0

    async def generate_ai_result(self, nodes: list[dict]) -> bool:
        """On a photo picker that offers sample photos: pick as many as it asks, generate, keep the result screen.

        The AI rule (report button on generated content) needs a real result; sample photos make
        that possible without seeding the phone's gallery.
        """
        label = next((n for n in nodes if SAMPLE_RE.match((n["text"] or "").strip())), None)
        if not label and any(NEED_RE.search(n["text"] or "") for n in nodes):
            # A photo picker whose sample row is still loading (seen on Pixel 4): look again.
            for _ in range(3):
                await asyncio.sleep(2)
                _a, nodes = await self.look()
                label = next((n for n in nodes if SAMPLE_RE.match((n["text"] or "").strip())), None)
                if label:
                    break
        need_label = next((n for n in nodes if NEED_RE.search(n["text"] or "")), None)
        upload = any(UPLOAD_RE.search(n["text"] or n["desc"] or "") for n in nodes)
        if not label and not need_label and not upload:
            return False
        need = int(NEED_RE.search(need_label["text"]).group(2)) if need_label else 1
        if label:
            below = sorted((n for n in nodes if n["clickable"] and n["bounds"][1] > label["bounds"][3]
                            and n["bounds"][1] < label["bounds"][3] + 400), key=lambda n: n["bounds"][0])
            for n in below[:need]:
                await a_tap(self.serial, *center(n["bounds"]))
                await asyncio.sleep(1.5)
        elif not await self.pick_from_gallery(nodes, need_label, need):
            return False
        _a, nodes = await self.look()
        await self.fill_prompt(nodes)
        _a, nodes = await self.look()
        go = next((p for n in nodes if GO_RE.match((n["text"] or "").strip())
                   and (p := n if n["clickable"] else self._clickable_parent(nodes, n))), None)
        if not go:
            return False
        await a_tap(self.serial, *center(go["bounds"]))
        end = time.monotonic() + GENERATE_WAIT_SECONDS
        watched = False
        while time.monotonic() < end:
            await asyncio.sleep(4)
            act = await a_top_activity(self.serial) or ""
            if is_fullscreen_ad_activity(act):
                continue                      # an ad while generating; the countdown runs on
            _a, nodes = await self.look()
            gate = next((n for n in nodes if WATCH_AD_RE.search(n["text"] or n["desc"])), None)
            if gate and not watched:
                # Free users generate after a rewarded ad ("Watch Ad (0/1)"): this is the reward placement.
                watched = True
                await self.watch_reward(gate, nodes)
                end = time.monotonic() + GENERATE_WAIT_SECONDS
                continue
            if sum(1 for n in nodes if RESULT_RE.search(n["text"] or n["desc"])) >= 2:
                await self.close_popups()     # e.g. a "rate us" dialog over the result
                await self.look()
                return True
        return False

    async def watch_reward(self, gate: dict, nodes: list[dict]) -> None:
        """Open the rewarded ad from its entry point and let it run until its close control shows.

        The creative is not tapped here (the reward would be lost and nothing generated); the entry tap
        itself is recorded as the reward click probe: handled = a full-screen ad opened.
        """
        target = gate if gate["clickable"] else (self._clickable_parent(nodes, gate) or gate)
        before = await a_top_activity(self.serial) or ""
        t = self._ms()
        self.ev.prober.reward_running = True
        await a_tap(self.serial, *center(target["bounds"]))
        opened = None
        for _ in range(12):
            await asyncio.sleep(1)
            act = await a_top_activity(self.serial) or ""
            if is_fullscreen_ad_activity(act):
                opened = act
                break
        rec = {"t": t, "kind": "reward", "activity": before, "tap": list(center(target["bounds"])),
               "after": opened or (await a_top_activity(self.serial) or ""), "handled": bool(opened),
               "left_app": False, "entry_label": gate["text"] or gate["desc"]}
        with self.ev.prober.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        clicked = False
        if opened:
            end = time.monotonic() + REWARD_MAX_SECONDS + 15
            while time.monotonic() < end:
                await asyncio.sleep(3)
                if not is_fullscreen_ad_activity(await a_top_activity(self.serial)):
                    break
                xml = await asyncio.to_thread(self._dump)
                xy = find_close_center(xml) if xml else None
                if xy and time.monotonic() > end - REWARD_MAX_SECONDS + 15:   # at least 15s watched
                    if not clicked:
                        # Close control shown = reward earned: now the creative can be tapped without
                        # losing it ("click vào ad có xử lý" for the reward placement).
                        clicked = True
                        ad_nodes = parse_nodes(xml)
                        cta = next((n for n in ad_nodes if n["text"].strip().lower() in
                                    ("learn more", "install", "open", "visit", "download", "get")), None)
                        cxy = center(cta["bounds"]) if cta else (540, 1300)
                        act = await a_top_activity(self.serial) or ""
                        await self.ev.prober._tap_and_observe("reward_creative", act, cxy)
                        continue
                    await a_tap(self.serial, *xy)
            if is_fullscreen_ad_activity(await a_top_activity(self.serial)):
                await a_key(self.serial, "KEYCODE_BACK")
            await asyncio.sleep(2)
        self.ev.prober.reward_running = False

    async def leave_result(self) -> None:
        """BACK out of a generated result; apps ask "Are you sure?" before dropping it."""
        await a_key(self.serial, "KEYCODE_BACK")
        await asyncio.sleep(2)
        for _ in range(3):
            nodes = parse_nodes(await asyncio.to_thread(self._dump))
            ok = next((n for n in nodes if n["clickable"] and CONFIRM_LEAVE_RE.match((n["text"] or n["desc"]).strip())), None)
            if not ok:
                return
            await a_tap(self.serial, *center(ok["bounds"]))
            await asyncio.sleep(2)

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
                await self.leave_result()
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
