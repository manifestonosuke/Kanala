# kbs — Kanji BunSeki (漢字分析)

Scrapes kanji entries from `kanji.jitenon.jp` and stores them in a single JSON file. Designed so the data source and the output renderer can each be swapped independently.

**Active planning:** see [`notes/`](./notes/) — one Markdown file per topic for cross-machine context.

## Layout

```
<project root>/
├── kbs.py                      # CLI entry shim — runs kbs.__main__.main
└── kbs/                        # Package (Kanji BunSeki)
    ├── __main__.py             # CLI entry point — `get` and `map` subcommands
    ├── sources.py              # SOURCES registry + DEFAULT — config dicts for all sources
    ├── acquirer.py             # KanjiAcquirer — orchestrator (DI: KanjiSource + Transport)
    ├── store.py                # KanjiStore    — single JSON file of acquired entries
    ├── map.py                  # KanjiMap + build_map — kanji→path lookup table
    ├── transport/
    │   ├── base.py             # Transport ABC — fetch(url) → str
    │   └── http.py             # HttpTransport — requests-based
    ├── source/
    │   └── kanji/
    │       ├── base.py         # KanjiSource ABC — url_for / parse / map_pages / parse_map_page / identifier_from_url
    │       └── jitenon.py      # JitenonKanjiSource — config-driven, BeautifulSoup parsing
    └── display/
        ├── base.py             # Display ABC   — show(kanji, data)
        └── cli.py              # CliDisplay    — terminal output (default)
```

Both `kbs.py` (the shim) and `kbs/` (the package) sit at the project root. Python's package-vs-module precedence means `import kbs` resolves to the directory, while `python kbs.py …` runs the shim as a script.

`transport/` is the I/O layer (how bytes get loaded); `source/` is per-domain
parsing (kanji today, vocabulary potentially later). They compose in the
acquirer: `transport.fetch(source.url_for(id))` → `source.parse(text)`.

## Dependencies

- `requests`
- `beautifulsoup4`

## CLI

Three subcommands. Run from the project root (so `kbs/` is importable):

```bash
python kbs.py get <kanji>              # display the kanji (fetch if not yet in store)
python kbs.py get <kanji> -r           # force a re-fetch even if already in store
python kbs.py get <url>                # fetch by full source URL (always re-fetches)
python kbs.py map                      # rebuild the kanji→path map from the source
python kbs.py build                    # fetch every kanji in the map into the store
python kbs.py build -r                 # re-fetch even entries already in the store
python kbs.py --store path.json ...    # override store path
python kbs.py --map   path.json ...    # override map path
# Equivalent: python -m kbs ...
```

**Default store:** `/data/home/pierre/Perso/Claude/source/<source_name>/kanji.json` (per-source data dir under a hardcoded `SOURCE_BASE`). For the active source `jitenon`, that resolves to `/data/home/pierre/Perso/Claude/source/jitenon/kanji.json`. Override with `--store`.
**Default map:** same dir, `kanji_map.json`. Override with `--map`.

The path constants in `kbs/__main__.py`:

```python
SOURCE_BASE = Path("/data/home/pierre/Perso/Claude/source")
SOURCE_NAME = SOURCES[DEFAULT]["name"]   # e.g. "jitenon"
SOURCE_DIR  = SOURCE_BASE / SOURCE_NAME
KDB_NAME    = SOURCE_DIR / "kanji.json"
KMAP_NAME   = SOURCE_DIR / "kanji_map.json"
```

## Source registry

All sources live in `kbs/sources.py` as a single dictionary, with one entry per source. Each entry is the source's full definition — `base_url`, whether it needs a map, and the class that does the parsing:

```python
SOURCES = {
    "jitenon": {
        "name":      "jitenon",
        "base_url":  "https://kanji.jitenon.jp",
        "needs_map": True,
        "class":     JitenonKanjiSource,
    },
}
DEFAULT = "jitenon"
```

`SOURCES[name]["class"](SOURCES[name])` instantiates the source — the class reads `base_url` (and anything else) from the dict it's given. There's no `BASE` constant on the class; the dict is the only place URLs are configured.

`needs_map = False` would mean the source can resolve a kanji character directly to a URL (e.g. `https://other.example/kanji/生`), no map required — `cmd_get` would skip the map step entirely.

### Map

`kanji_map.json` is a flat `{kanji_char: "<label>/<path>"}` lookup table, e.g.:

```json
{ "生": "kyu05/kanji/043", "阿": "kyu01/kanjie/2141" }
```

- **Label** is the kanken level the kanji first appeared on while building the map. Sources iterate easiest→hardest (`kyu10` … `kyu01`), so the recorded label is the **easiest** level the kanji belongs to.
- **Path** is the source-specific URL fragment (jitenon partitions ids across `~23` roots like `kanji/`, `kanjie/`, `kanjib/`, …). `JitenonKanjiSource.url_for` strips the leading `kyuXX[j]/` segment and prepends the jitenon base URL.
- Built from 12 pages: `/cat/kyu01`, `/cat/kyu01j`, `/cat/kyu02`, `/cat/kyu02j`, `/cat/kyu03` … `/cat/kyu10` (only `kyu01` and `kyu02` have `j` variants for 準1級/準2級).
- `map` **replaces** the file (not merge) so the on-disk map matches the source's current listings.
- Auto-triggered by `get` when a kanji lookup misses; also runs explicitly via `python kbs.py map`.

### `build` flow

Walks every key in the map and fetches missing entries into the store.

- Skips kanji already in the store (resumable across runs). `-r/--refresh` re-fetches them.
- Saves the store after each fetch (interrupts only lose the in-flight entry).
- One inline line per fetch: `fetching 馬 152ms`. On error: `fetching X FAILED 152ms: <reason>` followed by a `Continue? [Y/n]` prompt — default **Yes** (Enter keeps going); `n` stops.
- Ends with `Built N, skipped M, failed K[, stopped at 「X」]`.
- Requires `cfg["needs_map"]`; sources without a map cannot enumerate, so `build` exits.

### `get` flow

1. Resolve the target argument:
   - **URL** (`http(s)://…`) → `source.identifier_from_url(url)`. Rejected if not recognised by the source. Always re-fetches (URL input is explicit intent).
   - **Single character** → store-first:
     - Already in store and no `--refresh` → display the stored entry, done.
     - Otherwise (not in store, or `--refresh`):
       - If `cfg["needs_map"]`: consult the map. If missing, auto-rebuild the map once and retry. If still missing, fail.
       - If `cfg["needs_map"]` is False: pass the kanji character directly as the identifier.
   - **Anything else** (multi-char that isn't a URL) → rejected.
2. Fetch (`HttpTransport` → `source.parse`). The acquirer stamps `取得日時`.
3. Save (silent overwrite — explicit `--refresh` or URL input is the user's "yes"). Display.

## JSON schema

Top-level keys = the kanji character itself. One file accumulates all entries.

```json
{
  "<kanji>": {
    "読み": {
      "音": { "常": [...], "外": [...] },
      "訓": { "常": [...], "外": [...] }
    },
    "部首":     "<radical char>",
    "画数":     "<total>:<bushu>+<rest>",
    "種別":     [ "教" | "常" | "名" | "人" | "外", ... ],
    "学年":     "小1" | ... | "小6" | "中" | "高" | "",
    "漢字検定": "<級>",
    "意味":     [ "...", ... ],
    "Unicode":  "U+XXXX",
    "漢字構成": [ "<component kanji>", ... ],
    "取得日時": "<ISO 8601 local timestamp, e.g. 2026-05-14T15:23:45+09:00>",
    "分類": {
      "教":   [<currentlyIn: bool>, [<event>, ...]],
      "常":   [<currentlyIn: bool>, [<event>, ...]],
      "人名": [<currentlyIn: bool>, [<event>, ...]],
      "当":   [<currentlyIn: bool>, [<event>, ...]]
    }
  }
}
```

### Reading buckets

Mapped from jitenon's `yomi_iconN.svg` icons:

| Icon | Source label             | Bucket |
|------|--------------------------|--------|
| 1    | 小学校で習う読み         | `常`   |
| 2    | 中学校で習う読み         | `常`   |
| 3    | 高校で習う読み           | `常`   |
| 4    | 表外読み                 | `外`   |

Okurigana is rendered with dot notation: `い（かす）` → `い.かす`.

### 種別 codes

| Source            | Code |
|-------------------|------|
| 教育漢字          | `教` |
| 常用漢字          | `常` |
| 名前に使える漢字  | `名` |
| 人名用漢字        | `人` |
| 表外漢字          | `外` |

### 分類 — historical category memberships

Each entry: `[currentlyIn, [event_newest_first, ...]]`.

Event encoding:

| List type | Event format             | Examples                                |
|-----------|--------------------------|-----------------------------------------|
| 当 / 常 / 人名 | `年` (add), `-年` (remove) | `"昭56"`, `"-平22"`                     |
| 教             | `年:学年`, `年:0` (remove) | `"昭33:2"`, `"平29:1"`, `"平29:0"`      |

The acquirer initialises `分類` from the current 種別 with empty event lists; historical years are not extracted from jitenon and should be enriched by hand.

## Adding a new source

Subclass `KanjiSource` (in `source/kanji/`) and implement:

- `url_for(identifier) -> str` — build a fetch URL from a map value or path
- `parse(text) -> {"kanji": str, "data": dict}` — entry HTML → dict
- `map_pages() -> [(label, url), ...]` — pages to scrape for the map, ordered easiest-first
- `parse_map_page(text) -> {kanji: path}` — extract kanji→path entries from a map page
- `identifier_from_url(url) -> str | None` — recognise a full entry URL and return its path identifier

Wire it into `KanjiAcquirer`, `build_map`, and the URL passthrough in `cmd_acquire` (all driven by these five methods). No HTTP code in the source — that lives in `transport/`.

## Adding a new transport

Subclass `Transport` (in `transport/`) and implement `fetch(url) -> str`. Useful for caching, offline fixtures, or async fetching. The source doesn't change.

## Adding a new display

Subclass `Display` and implement `show(kanji, data)`. Pass it to `query()` or call directly in a new CLI command.

## Example

```bash
python kbs.py map              # build kanji_map.json once
python kbs.py get 生            # fetch 生, save, display (auto-builds map if needed)
python kbs.py get 生            # second call: served from store, no network
python kbs.py get 生 -r         # force re-fetch and overwrite
```

## Page mapping

URL pattern: `https://kanji.jitenon.jp/kanji/{id:03d}` (zero-padded 3-digit id).
Main info table CSS selector: `table.kanjirighttb`.
Composition section: `<h2 id="m_kousei">` → following `<ul><li><a>...</a></li></ul>`.
Unicode value: `<table class="moji_code">` row with `<th>Unicode</th>`.

## Notes for future Claude sessions

**Working language.** Pierre studies Japanese — for any 日本語 topic (kanji explanations, readings, meanings, page summaries), respond in 日本語 by default, not English. Earlier in this project he pushed back with "why are you showing english?" Code and software-engineering discussion stay English. When unsure, ask which language he prefers rather than silently defaulting.

**JSON field labels.** Keep Japanese terms (`読み`, `部首`, `意味`, `分類`, …) — don't romanise or translate without being asked.

**Design cadence.** He iterates carefully on data schemas before coding ("do not code now", "show the full result for 生", many small rounds compacting the structure). Don't rush to implementation; align on the schema/architecture first.

**Parsing gotchas baked into `JitenonKanjiSource`:**
- BS4's `html.parser` produces a `RubyTextString` subclass for `<rt>` content; `Tag.get_text()` and `.strings` *skip* it. Use the `_full_text()` helper (walks `.descendants` and includes every `NavigableString` that isn't `Comment`/`CData`) when you want furigana inline (e.g. for `意味`). Use `_label()` (which decomposes `<rt>` first) when you want clean labels.
- The page uses full-width characters: `＋` for stroke-count split (`生５＋０`), and `０-９` for digits. `ZEN_TO_HAN` translates both `＋／－` and the digits — apply it before any regex on numeric fields.
- The 種別 row is a slash-separated string of `<a>` links; the categorisation `名前に使える漢字` does NOT imply a separate 人名 entry in `分類` if the kanji is also 常用 (`名前に使える` = 常用 ∪ 人名用). Only emit `"人名"` when `名` is present AND `常` is absent.

**`分類` history is not on jitenon.** The page only tells us current membership. The script seeds `分類` entries with `[true, []]`; the year history (`"昭56"`, `"平29:1"`, etc.) has to be added by hand or from another source.
