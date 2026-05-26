from .source.kanji.bunka import BunkaKanjiSource
from .source.kanji.jitenon import JitenonKanjiSource

SOURCES = {
    "jitenon": {
        "name":      "jitenon",
        "base_url":  "https://kanji.jitenon.jp",
        "needs_map": True,
        "bulk":      False,
        "class":     JitenonKanjiSource,
    },
    "bunka.org": {
        "name":      "bunka.org",
        "base_url":  "https://www.bunka.go.jp",
        "needs_map": False,
        "bulk":      True,
        "class":     BunkaKanjiSource,
    },
}

DEFAULT = "jitenon"
