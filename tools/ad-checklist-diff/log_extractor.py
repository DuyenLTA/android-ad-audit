"""Select trusted logcat lines by --filter substring and pull candidate values out of them."""
import re

from checklist_source import ID_RE

BRACKET_RE = re.compile(r"\[([^\]]*)\]")


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

    Three shapes are supported (all seen in real captures):
      1. `TAG: Adjust config token: uz6fb8kyeww0`      -> trailing value after last colon
      2. `TAG: LFO1: [id1, id2, id3]`                  -> bracket-list members
      3. `... ca-app-pub-123/456 ...` anywhere in line -> AdMob app/unit IDs
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

        # Independent of whether the line also had a bracket list -- a line
        # can have both a leading `[tag]`-style marker and a trailing
        # `Label: value`.
        last_colon = line.rstrip("\n").rfind(":")
        if last_colon != -1:
            tail = line[last_colon + 1 :].strip()
            if tail and not tail.startswith("["):
                values.add(tail)
    return values
