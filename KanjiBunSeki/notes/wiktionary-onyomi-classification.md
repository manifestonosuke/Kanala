# Wiktionary 呉/漢/唐/慣用 on'yomi classification

**Status:** exploring
**Last touched:** 2026-05-15

## Goal

Enrich each kanji entry with the **historical layer** of its 音読み — 呉音 / 漢音 /
唐音 / 慣用音. jitenon lists all on'yomi in a flat `読み.音.常` array; the
historical layer is missing. We want it because the on'yomi of a kanji often
varies (e.g. 生 → ショウ vs セイ) and the *reason* is which century/region of
Chinese the reading was borrowed from. It's a study aid, not a parsing
convenience.

## Findings

Verified on 生 against `https://ja.wiktionary.org/wiki/生`:

| Field | jitenon | ja.wiktionary |
|---|:-:|:-:|
| 音読み + **呉/漢/唐/慣用 layer** | ✗ flat list | **✓ labeled** |
| 訓読み | ✓ (`い.かす` dot) | ✓ (`い-きる` dash, plus 名乗り) |
| 部首 | ✓ | ✓ |
| 画数 | ✓ (`5:5+0` split) | ✓ (total only) |
| 種別 (教/常/名/人/外) | ✓ | ◯ partial (教 + 学年 marker) |
| 学年 | ✓ | ✓ |
| **漢字検定** | ✓ | **✗** |
| 意味 | ✓ | ✓ |
| Unicode | ✓ | ✓ |
| 漢字構成 | ✓ | ✗ (only loose 関連字) |
| **熟語/用例** | ✗ | **✓ (60+)** |

jitenon wins on 漢字検定, 漢字構成, 画数 detail.
Wiktionary wins on 呉/漢/唐 labels and 熟語 examples.

**Coverage caveat:** only 生 verified (textbook case). Common 常用 kanji should
be well-covered; 準1級 / 1級 / 表外 likely have gaps where `呉音:` / `漢音:`
labels are missing or merged into a generic 音読み list. Implementation must
tolerate this — leave entries unclassified rather than guess.

## Options

### Path A — keep jitenon primary, add Wiktionary as a second source (recommended)

- Add `WiktionaryKanjiSource` in `kbs/source/kanji/wiktionary.py`, register in
  `kbs/sources.py` with `needs_map=False` (the kanji character is the URL
  slug).
- Add a merge step that enriches each jitenon entry's `読み.音` with
  classification dicts from Wiktionary.
- Existing `kanken`, `joyo`, `anki` commands keep working — only `読み.音`
  shape changes, and only for consumers that opt in.

Less disruption, preserves the 漢字検定 / 漢字構成 fields kbs already uses.

### Path B — switch primary to Wiktionary

- Wiktionary becomes the main source, jitenon kept as a supplement for the
  fields Wiktionary lacks (漢字検定, 漢字構成).
- More churn, weaker reason. Not recommended unless we discover Wiktionary
  also has better 意味/学年 data than jitenon.

## Schema (candidate — not decided)

Current shape:

```json
"読み": {
  "音": { "常": ["ショウ", "セイ"], "外": [] },
  "訓": { "常": ["い.かす", ...],   "外": [...] }
}
```

Candidate enriched shape (Path A):

```json
"読み": {
  "音": {
    "常": { "呉": ["ショウ"], "漢": ["セイ"], "唐": [], "慣用": [] },
    "外": { "呉": [],         "漢": [],       "唐": ["サン"], "慣用": [] }
  },
  "訓": { "常": ["い.かす", ...], "外": [...] }   // unchanged
}
```

**Migration impact:** `anki` command currently does
`block.get("常", [])` and expects a flat list. After enrichment that returns a
dict. Either the consumers update, or we keep a parallel flat-list field for
backwards compat. Decision pending.

## Access method

**Do NOT scrape rendered HTML.** Use one of:

1. **MediaWiki API** (per-page, real-time):
   ```
   https://ja.wiktionary.org/w/api.php?action=parse&page=生&format=json&prop=wikitext
   ```
   Returns the page's wikitext — far cleaner to parse than rendered HTML.
   Good for incremental fetches via the existing `Transport` ABC.

2. **Monthly dump** (bulk, offline):
   ```
   https://dumps.wikimedia.org/jawiktionary/
   ```
   ~150 MB compressed, contains every kanji entry. No rate limiting, no
   robots.txt concerns. Best if we ever want to rebuild the whole dataset
   from scratch.

## Next steps

When this is resumed:

1. **Decide the schema first** (not the source code). Sketch the merged
   `読み.音` shape, walk through how `anki`, `joyo`, `kanken` consume it,
   confirm no regressions.
2. Then implement `WiktionaryKanjiSource` against the MediaWiki API.
3. Add a merge command (e.g. `python kbs.py enrich`) that walks the store and
   fills in the historical layer per entry, with one-line-per-fetch progress
   like `build` already does.
4. Update `anki` to surface the labels (e.g. `音: ショウ [呉] セイ [漢]`).
