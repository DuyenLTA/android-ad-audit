"""Minimal uiautomator XML reader shared by the evidence collector and the checkers.

Regex rather than ElementTree on purpose: dumps taken mid-transition are sometimes
truncated, and a partial list of nodes is still evidence; a parse error is not.
"""
import re

NODE_RE = re.compile(r"<node [^>]*>")
BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")

# Full-screen ad activities of the networks Apero apps mediate through.
FULLSCREEN_AD_ACTIVITY_MARKERS = (
    "AdActivity",                 # Google Mobile Ads (old + next-gen SDK)
    "AppLovinFullscreenActivity",
    "AudienceNetworkActivity",
    "com.ironsource",
    "com.unity3d.ads",
    "com.vungle",
    "com.mbridge",
    "com.bytedance.sdk.openadsdk",  # Pangle
)


def norm_activity(activity: str | None) -> str:
    """One spelling for an activity: `pkg/.ui.Main` (dumpsys activity) and `pkg/pkg.ui.Main`
    (dumpsys window) name the same screen; comparing them raw made every tap look "handled"."""
    if not activity or "/" not in activity:
        return activity or ""
    pkg, cls = activity.split("/", 1)
    return f"{pkg}/{pkg}{cls}" if cls.startswith(".") else activity


def _attr(node: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', node)
    return m.group(1) if m else ""


def parse_nodes(xml: str) -> list[dict]:
    """Every node with its short resource id, text, desc, class, clickable and bounds."""
    nodes = []
    for raw in NODE_RE.findall(xml or ""):
        m = BOUNDS_RE.search(_attr(raw, "bounds"))
        if not m:
            continue
        rid = _attr(raw, "resource-id")
        nodes.append({
            "rid": rid.split("/", 1)[1] if "/" in rid else rid,
            "text": _attr(raw, "text"),
            "desc": _attr(raw, "content-desc"),
            "cls": _attr(raw, "class"),
            "pkg": _attr(raw, "package"),
            "clickable": _attr(raw, "clickable") == "true",
            "bounds": tuple(int(v) for v in m.groups()),
        })
    return nodes


def area(b: tuple[int, int, int, int]) -> int:
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def intersection(a: tuple, b: tuple) -> int:
    return area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def center(b: tuple) -> tuple[int, int]:
    return (b[0] + b[2]) // 2, (b[1] + b[3]) // 2


def first(nodes: list[dict], pred) -> dict | None:
    return next((n for n in nodes if area(n["bounds"]) > 0 and pred(n)), None)


def is_fullscreen_ad_activity(activity: str | None) -> bool:
    return bool(activity) and any(m in activity for m in FULLSCREEN_AD_ACTIVITY_MARKERS)


def native_parts(nodes: list[dict]) -> dict:
    """Locate the pieces of a Google native ad that the policy rules measure.

    Layouts name the container differently per screen (the Question screen of the
    VSL template has no `nativeAdView` id). Without a known container id, the
    container is inferred as the box around the ad's own parts, marked `inferred`.
    """
    parts = {
        "native": first(nodes, lambda n: n["rid"] in ("nativeAdView", "native_ad_view") or n["rid"].endswith("NativeAdView")),
        "media": first(nodes, lambda n: n["rid"] in ("ad_media", "media_view") or "MediaView" in n["cls"]),
        "cta": first(nodes, lambda n: n["rid"] == "ad_call_to_action"),
        "attribution": first(nodes, lambda n: n["text"].strip() in ("Ad", "AD", "Ads", "Quảng cáo")),
        "adchoices": first(nodes, lambda n: "Ad Choices" in n["desc"] or "AdChoices" in n["desc"]),
        "shimmer": first(nodes, lambda n: "shimmer" in n["rid"].lower() or "loading" in n["rid"].lower()),
    }
    # No known container id: take the smallest node that wraps media + CTA + "Ad" label, i.e. the ad's
    # real container in the tree. AdChoices is deliberately not used to find it, or "AdChoices inside
    # the native" would hold by construction; a bounding box of the parts instead is too tight and
    # pushes a correctly placed AdChoices "outside".
    own = [parts[k] for k in ("media", "cta", "attribution") if parts[k]]
    if parts["native"] is None and parts["cta"] and parts["attribution"] and len(own) >= 3:
        def wraps(n):
            return all(n["bounds"][0] <= o["bounds"][0] and n["bounds"][1] <= o["bounds"][1]
                       and n["bounds"][2] >= o["bounds"][2] and n["bounds"][3] >= o["bounds"][3] for o in own)
        holders = [n for n in nodes if n not in own and area(n["bounds"]) > 0 and wraps(n)]
        if holders:
            box = min(holders, key=lambda n: area(n["bounds"]))["bounds"]
            parts["native"] = {"rid": "", "text": "", "desc": "", "cls": "", "pkg": "", "clickable": False,
                               "bounds": box, "inferred": True}
    return parts


def banner_node(nodes: list[dict]) -> dict | None:
    """App-side banner container: an id naming a banner, shorter than a third of the screen."""
    return first(nodes, lambda n: "banner" in n["rid"].lower() and (n["bounds"][3] - n["bounds"][1]) < 800)
