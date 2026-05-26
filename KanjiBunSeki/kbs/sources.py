from .source.kanji.bunka import BunkaKanjiSource
from .source.kanji.jitenon import JitenonKanjiSource
from .source.tango.wiktionary import WiktionaryTangoSource

SOURCES = {
    "jitenon": {
        "name":      "jitenon",
        "type":      "kanji",
        "base_url":  "https://kanji.jitenon.jp",
        "needs_map": True,
        "bulk":      False,
        "class":     JitenonKanjiSource,
    },
    "bunka.org": {
        "name":      "bunka.org",
        "type":      "kanji",
        "base_url":  "https://www.bunka.go.jp",
        "needs_map": False,
        "bulk":      True,
        "class":     BunkaKanjiSource,
    },
    "wiktionary": {
        "name":     "wiktionary",
        "type":     "tango",
        "base_url": "https://ja.wiktionary.org",
        "class":    WiktionaryTangoSource,
    },
}

DEFAULT       = "jitenon"
DEFAULT_TANGO = "wiktionary"
