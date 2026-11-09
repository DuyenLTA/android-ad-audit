"""AI chat apps gate extra messages behind a rewarded ad: chat until the free messages run out.

Seen on AIP920 Lingix 1.6.0: Home lists AI tutors; a chat gives 2 free messages, then a popup
"You've used all your free chats today" offers "Watch Ad (0/3)" (RC `show_reward_chat`). Neither the
FO driver nor the Home explorer's content pass ever sends a message, so the reward rules came out N/A on
"not seen" - which is not a basis. This opens the first chat card, switches to typing when the chat
starts in voice mode, sends short messages until a watch-ad gate shows (bounded), then hands the gate to
`HomeExplorer.watch_reward`. Every chat screen goes through `look()`, so the frames also carry the
"Report answer" control under the AI reply (AI report rule, chat branch).
"""
import asyncio
import re

from adb_sync import a_key, a_tap, a_top_activity, adb
from ui_nodes import center, is_fullscreen_ad_activity, parse_nodes

SEND_RE = re.compile(r"^(send|gửi)$", re.I)
TEXT_MODE_RE = re.compile(r"switch input mode|keyboard|bàn phím|type|nhập", re.I)
WATCH_AD_RE = re.compile(r"watch (an )?ad|xem (quảng cáo|qc)|xem ad", re.I)
MESSAGE = "Hello"
MAX_MESSAGES = 5
REPLY_WAIT_SECONDS = 90
STOP_RE = re.compile(r"^(stop|dừng)$", re.I)


def _label(n: dict) -> str:
    return (n["text"] or n["desc"]).strip()


AD_MARK_RE = re.compile(r"^(ad|ads|quảng cáo|sponsored)$|adchoices|ad choices", re.I)


def _inside(n: dict, box: dict) -> bool:
    a, b = n["bounds"], box["bounds"]
    return b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]


def chat_cards(nodes: list[dict], width: int, height: int) -> list[dict]:
    """Big tappable cards of the Home list (a tutor / character each), top first. The tab bar and native
    ads placed between the cards (an "Ad" badge / AdChoices inside) are left out."""
    cards = [n for n in nodes if n["clickable"] and n["bounds"][2] - n["bounds"][0] > 0.7 * width
             and n["bounds"][3] - n["bounds"][1] > 250 and n["bounds"][1] > 0.12 * height
             and n["bounds"][3] < 0.8 * height]
    cards = [c for c in cards if not any(AD_MARK_RE.search(_label(n)) and _inside(n, c) for n in nodes)]
    return sorted(cards, key=lambda n: n["bounds"][1])


def send_button(nodes: list[dict]) -> dict | None:
    return next((n for n in nodes if SEND_RE.match(_label(n))), None)


def watch_ad_gate(nodes: list[dict]) -> dict | None:
    return next((n for n in nodes if WATCH_AD_RE.search(_label(n))), None)


async def chat_until_reward(explorer, width: int, height: int) -> bool:
    """True when a rewarded ad gate was found (and watched) from an AI chat."""
    _act, nodes = await explorer.look()
    cards = chat_cards(nodes, width, height)
    if not cards:
        return False
    await a_tap(explorer.serial, *center(cards[0]["bounds"]))
    await asyncio.sleep(3)
    if await explorer._watch_for_ad():          # inter on opening the chat
        await explorer.close_fullscreen_ad()
    _act, nodes = await explorer.look()
    if not send_button(nodes):
        toggles = [n for n in nodes if TEXT_MODE_RE.search(n["desc"])]
        if not toggles:
            await _leave(explorer)
            return False
        await a_tap(explorer.serial, *center(toggles[-1]["bounds"]))   # voice | text: text is the last one
        await asyncio.sleep(1.5)
        _act, nodes = await explorer.look()
    found = False
    for _ in range(MAX_MESSAGES):
        gate = watch_ad_gate(nodes)
        if gate:
            await explorer.watch_reward(gate, nodes)
            found = True
            break
        field = next((n for n in nodes if "EditText" in n["cls"]), None)
        if not field or not send_button(nodes):
            break
        await a_tap(explorer.serial, *center(field["bounds"]))
        await asyncio.sleep(0.8)
        await asyncio.to_thread(adb, explorer.serial, "shell", "input", "text", MESSAGE)
        await asyncio.sleep(0.6)
        # The keyboard moved the input bar up: find Send again where it is now.
        send = send_button(parse_nodes(await asyncio.to_thread(explorer._dump)))
        if not send:
            break
        await a_tap(explorer.serial, *center(send["bounds"]))
        nodes = await _wait_reply(explorer)
    await _leave(explorer)
    return found


async def _wait_reply(explorer) -> list[dict]:
    """While the AI answers (or speaks it) Send turns into Stop; wait until Send or a gate is back."""
    nodes: list[dict] = []
    for _ in range(REPLY_WAIT_SECONDS // 3):
        await asyncio.sleep(3)
        nodes = parse_nodes(await asyncio.to_thread(explorer._dump))
        if watch_ad_gate(nodes) or send_button(nodes):
            break
    else:
        # Still answering / reading it aloud after the wait: Stop ends the voice, the reply stays.
        stop = next((n for n in nodes if STOP_RE.match(_label(n))), None)
        if stop:
            await a_tap(explorer.serial, *center(stop["bounds"]))
            await asyncio.sleep(2)
    _act, nodes = await explorer.look()          # evidence: the reply with its Report control, or the gate
    return nodes


async def _leave(explorer) -> None:
    """BACK until the chat (input bar / voice-text switch) is gone: the keyboard, a reward popup or the
    chat itself each take one. Leaving a chat shows an inter on this app; it is closed by its Close."""
    for _ in range(5):
        if is_fullscreen_ad_activity(await a_top_activity(explorer.serial)):
            await explorer.close_fullscreen_ad()
            continue
        await explorer.close_popups()             # the watch-ad popup comes back after each reward
        nodes = parse_nodes(await asyncio.to_thread(explorer._dump))
        if not any("EditText" in n["cls"] or TEXT_MODE_RE.search(n["desc"]) for n in nodes):
            break
        await a_key(explorer.serial, "KEYCODE_BACK")
        await asyncio.sleep(2.5)
    await explorer.back_to_app()
    await explorer.close_popups()
