"""Walk an in-app questionnaire that sits on the Home activity before the real Home shows.

Some apps (AIP920 Lingix 1.6.0) open MainActivity on a "personalise" flow after the template FO is
done: "What should we call you?" (name field), age, English level, minutes a day, then Start. rc-check's
driver already counts that as Home (activity matches), so the Home explorer would look at a form with no
tabs, no ads and no Settings. This walks it with neutral answers: type a name, pick the first option,
press the step's Continue / Next / Start (Skip when offered).

A paywall also has a big "Continue" and pressing it there would start a purchase, so any screen that
shows prices or subscription words stops the walk.
"""
import asyncio
import re

from adb_sync import a_key, a_tap, adb, safe_dump
from ui_nodes import center, parse_nodes

GO_RE = re.compile(r"^(continue|next|start|get started|let'?s go|done|tiếp tục|tiếp theo|bắt đầu|xong)$", re.I)
SKIP_RE = re.compile(r"^(skip|bỏ qua)$", re.I)
PAYWALL_RE = re.compile(r"[₫$€£]\s?\d|\d\s?[₫$€£]|/\s?(week|month|year)|subscri|auto-renew|free trial|restore", re.I)
PLACEHOLDER_RE = re.compile(r"enter|your name|type|nhập|tên của bạn", re.I)
NAME_TEXT = "QA"
MAX_STEPS = 12


def _label(n: dict) -> str:
    # Compose buttons put an arrow glyph after the word: "Continue →".
    return re.sub(r"[^\w' ]+", "", (n["text"] or n["desc"]).strip()).strip()


def _clickable_box(nodes: list[dict], child: dict) -> dict | None:
    """The node itself when clickable, else the smallest clickable node around it."""
    if child["clickable"]:
        return child
    b = child["bounds"]
    boxes = [n for n in nodes if n["clickable"] and n["bounds"][0] <= b[0] and n["bounds"][1] <= b[1]
             and n["bounds"][2] >= b[2] and n["bounds"][3] >= b[3]]
    return min(boxes, key=lambda n: (n["bounds"][2] - n["bounds"][0]) * (n["bounds"][3] - n["bounds"][1]),
               default=None)


def next_action(nodes: list[dict]) -> tuple[str, dict | None, list[dict]]:
    """("stop", None, []) | ("skip", node, []) | ("go", go_button, [option / name field to fill first])."""
    if any(PAYWALL_RE.search(n["text"] or n["desc"] or "") for n in nodes):
        return "stop", None, []
    skip = next((b for n in nodes if SKIP_RE.match(_label(n)) and (b := _clickable_box(nodes, n))), None)
    if skip:
        return "skip", skip, []
    # The step button stays disabled (not clickable, no clickable box around it) until the step is
    # answered: take the label itself then, the answer below enables it before the tap.
    go = next((_clickable_box(nodes, n) or n for n in reversed(nodes) if GO_RE.match(_label(n))), None)
    if not go:
        return "stop", None, []
    field = next((n for n in nodes if "EditText" in n["cls"]), None)
    if field:
        return "go", go, [field]
    # Answer cards: clickable boxes with no label of their own, between the question and the button.
    options = [n for n in nodes if n["clickable"] and not (n["text"] or n["desc"]) and n is not go
               and n["bounds"][3] <= go["bounds"][1] and n["bounds"][1] > 300
               and n["bounds"][2] - n["bounds"][0] > 400]
    return "go", go, options[:1]


async def walk_questionnaire(serial: str, package: str) -> int:
    """Answer the in-app questionnaire if one is up. Returns the number of steps taken (0: none there)."""
    steps, last = 0, None
    for _ in range(MAX_STEPS):
        nodes = parse_nodes(await asyncio.to_thread(safe_dump, serial, "/sdcard/policy-questionnaire.xml"))
        kind, button, fill = next_action(nodes)
        labels = tuple(n["text"] for n in nodes if n["text"])
        if kind == "stop" or labels == last:      # nothing to answer, or the last tap changed nothing
            break
        last = labels
        for f in fill:
            await a_tap(serial, *center(f["bounds"]))
            await asyncio.sleep(0.8)
            # An empty field reports either "" or its own placeholder ("Enter your name") as text.
            if "EditText" in f["cls"] and (not f["text"].strip() or PLACEHOLDER_RE.search(f["text"])):
                await asyncio.to_thread(adb, serial, "shell", "input", "text", NAME_TEXT)
                await asyncio.sleep(0.5)
                await a_key(serial, "KEYCODE_BACK")          # hide the keyboard so the button is where it was
                await asyncio.sleep(0.8)
        await a_tap(serial, *center(button["bounds"]))
        steps += 1
        await asyncio.sleep(2.5)
    return steps
