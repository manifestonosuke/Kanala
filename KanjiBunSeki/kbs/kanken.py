import re

LEVEL_TO_STORE: dict[str, str] = {
    "1":   "1級",   "1.5": "準1級",
    "2":   "2級",   "2.5": "準2級",
    "3":   "3級",   "4":   "4級",
    "5":   "5級",   "6":   "6級",
    "7":   "7級",   "8":   "8級",
    "9":   "9級",   "10":  "10級",
}
STORE_TO_LEVEL: dict[str, str] = {v: k for k, v in LEVEL_TO_STORE.items()}
DISPLAY_ORDER: tuple[str, ...] = (
    "10", "9", "8", "7", "6", "5", "4", "3", "2.5", "2", "1.5", "1",
)

_LEVEL_RE = re.compile(r"^(?:[1-9]|10)(?:\.5)?$")
_RANGE_RE = re.compile(
    r"^((?:[1-9]|10)(?:\.5)?)-((?:[1-9]|10)(?:\.5)?)$"
)


def parse_selector(token: str) -> list[str] | None:
    """Return canonical level strings for a level/range token, or None if not one.

    "1"    → ["1"]
    "1.5"  → ["1.5"]
    "1-3"  → ["1", "1.5", "2", "2.5", "3"]    (half-levels included)
    "foo"  → None
    """
    m = _RANGE_RE.match(token)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        lo, hi = min(a, b), max(a, b)
        return [lvl for lvl in LEVEL_TO_STORE if lo <= float(lvl) <= hi]
    if _LEVEL_RE.match(token):
        return [token]
    return None
