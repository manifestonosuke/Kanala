from .source.kanji.jitenon import JitenonKanjiSource

SOURCES = {
    "jitenon": {
        "name":      "jitenon",
        "base_url":  "https://kanji.jitenon.jp",
        "needs_map": True,
        "class":     JitenonKanjiSource,
    },
}

DEFAULT = "jitenon"
