"""Select trusted logcat lines by --filter substring and pull candidate values out of them."""
import re

from checklist_source import ID_RE

BRACKET_RE = re.compile(r"\[([^\]]*)\]")
KEY_VALUE_RE = re.compile(r"key=([\w.]+),\s*value=(\w+)")
KEY_MENTION_RE = re.compile(r"key=([\w.]+)")
SHOW_PREFIX = "show_"


def load_trusted_lines(log_path: str, filters: list[str]) -> dict[str, list[str]]:
    """Return, per --filter substring, every log line that contains it.

    Keeping this per-filter (rather than one flat pool) lets the caller warn
    when a given --filter matched zero lines -- a strong signal that this
    run's capture doesn't cover that area at all, distinct from a value
    genuinely being absent from lines that *were* captured.
    """
    trusted: dict[str, list[str]] = {flt: [] for flt in filters}
    filters_lower = [(flt, flt.lower()) for flt in filters]
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            low = line.lower()
            for flt, flt_lower in filters_lower:
                if flt_lower in low:
                    trusted[flt].append(line)
    return trusted


def extract_values(lines: list[str]) -> set[str]:
    """Pull candidate config/ID values out of trusted log lines.

    Four shapes are supported (all seen in real captures):
      1. `TAG: Adjust config token: uz6fb8kyeww0`      -> trailing value after last colon
      2. `TAG: LFO1: [id1, id2, id3]`                  -> bracket-list members
      3. `... ca-app-pub-123/456 ...` anywhere in line -> AdMob app/unit IDs
      4. `RemoteConfigRepository: key=show_native_loading_high, value=true`
         -> remote-config flag key, both as printed and with a leading
         `show_` stripped (checklist placement keys are written without it).
         Only counts when value=true -- a flag logged as false is not a match.
    """
    values = set()
    for line in lines:
        for m in ID_RE.finditer(line):
            values.add(m.group(0))

        for bracket in BRACKET_RE.finditer(line):
            for item in bracket.group(1).split(","):
                item = item.strip()
                if item:
                    values.add(item)

        for m in KEY_VALUE_RE.finditer(line):
            key, flag_value = m.group(1), m.group(2)
            if flag_value.lower() != "true":
                continue
            values.add(key)
            if key.startswith(SHOW_PREFIX):
                values.add(key[len(SHOW_PREFIX):])

        # Independent of whether the line also had a bracket list -- a line
        # can have both a leading `[tag]`-style marker and a trailing
        # `Label: value`.
        last_colon = line.rstrip("\n").rfind(":")
        if last_colon != -1:
            tail = line[last_colon + 1 :].strip()
            if tail and not tail.startswith("["):
                values.add(tail)
    return values


def extract_label_value_pairs(lines: list[str]) -> dict[str, str]:
    """Map label -> actual logged value for `... TAG: <Label>: <value>` lines.

    Only meaningful for checklist rows whose label is itself a human-readable
    description (Adjust/Facebook config in section 1) that the app logs
    verbatim -- used to show what the log *actually* has for a mismatched
    row, instead of only "not found". A line needs 3+ ": "-separated parts
    (tag, label, value) to count -- fewer than that means there's no
    separate label to key off, only a bare tag+value.
    """
    pairs: dict[str, str] = {}
    for line in lines:
        parts = line.rstrip("\n").split(": ")
        if len(parts) >= 3:
            label, value = parts[-2].strip(), parts[-1].strip()
            if label and value:
                pairs[label] = value
    return pairs


def extract_key_value_pairs(lines: list[str]) -> dict[str, str]:
    """Map remote-config flag key -> its logged true/false value (both the
    raw key and, if prefixed, the `show_`-stripped form) -- lets a mismatched
    row report "flag exists but is false" instead of only "not found"."""
    pairs: dict[str, str] = {}
    for line in lines:
        for m in KEY_VALUE_RE.finditer(line):
            key, flag_value = m.group(1), m.group(2)
            pairs[key] = flag_value
            if key.startswith(SHOW_PREFIX):
                pairs[key[len(SHOW_PREFIX):]] = flag_value
    return pairs


def extract_key_cooccurrences(lines: list[str]) -> dict[str, set[str]]:
    """Map each `key=X` mention to the other key= mentions on the *same log
    line* (only lines with 2+ distinct keys count -- a lone key on a line has
    no "buddy" to report).

    This is how the Home/inter_feature_high naming mismatch was originally
    (and correctly) spotted: a `loadDoubleIds` line logs
    `canShowHigh=true (key=enable_401_home_a_inter_high), canShowNormal=true
    (key=show_inter_feature)` -- once `show_inter_feature` is confirmed as
    the matched sibling row's key, its co-occurring `enable_401_home_a_inter_high`
    is a much more targeted FYI candidate for the mismatched row than a
    global list of every key mentioned anywhere in the capture (which turned
    out to be mostly unrelated feature flags, not ad placements)."""
    cooccurrences: dict[str, set[str]] = {}
    for line in lines:
        keys_on_line = {m.group(1) for m in KEY_MENTION_RE.finditer(line)}
        if len(keys_on_line) < 2:
            continue
        for key in keys_on_line:
            cooccurrences.setdefault(key, set()).update(keys_on_line - {key})
    return cooccurrences
