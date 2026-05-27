# kbs — Kanji BunSeki (漢字分析)

Scrapes kanji entries from multiple online sources (`kanji.jitenon.jp`, `bunka.go.jp`) and stores each source's data in its own JSON file under `data/<source>/<type>/`. Designed so the data source and the output renderer can each be swapped independently.

Two source flavours are supported:
- **Per-kanji** (jitenon): one HTTP request per kanji, mediated by a kanji→path map.
- **Bulk** (bunka.org): one HTTP request returns the whole table, parsed into ~2,136 entries at once. No map.

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
    │   ├── kanji/
    │   │   ├── base.py         # KanjiSource — per-kanji methods + bulk_url/parse_all (default NotImplementedError; sources override what they need)
    │   │   ├── jitenon.py      # JitenonKanjiSource — per-kanji mode, BeautifulSoup parsing
    │   │   └── bunka.py        # BunkaKanjiSource — bulk mode, parses bunka.go.jp 常用漢字索引 table
    │   └── tango/
    │       ├── base.py         # TangoSource ABC — url_for(word) + parse(text, word) → entry dict
    │       └── wiktionary.py   # WiktionaryTangoSource — ja.wiktionary.org parser
    ├── tango.py                # Tango — vocabulary acquirer (DI: TangoSource + Transport)
    ├── kanken.py               # Kanken level vocabulary: LEVEL_TO_STORE, parse_selector(token) → list[str]|None (handles "1", "1.5", "1-3")
    ├── anki/                   # Anki card generation. One file per card type; each card is bound to exactly one source.
    │   ├── base.py             # AnkiCard ABC — NAME/SOURCE/FIELDS/KEY + build(args, data_base) → list[dict]
    │   ├── format.py           # CsvFormat — TSV writer with KEY-based dedup and per-row [r/s] prompt
    │   ├── kankenjiten.py      # KankenjitenCard — bulk: reads jitenon kanji store → 漢字/部首/音読/訓読/意味/分類
    │   └── tangowiki.py        # TangowikiCard — single-entry: fetches a word from wiktionary, interactive 語義 picker
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

Run from the project root (so `kbs/` is importable):

```bash
# Kanji acquisition (per-source)
python kbs.py get <kanji>              # display the kanji (fetch if not yet in store)
python kbs.py get <kanji> -r           # force a re-fetch even if already in store
python kbs.py get <url>                # fetch by full source URL (always re-fetches)
python kbs.py map                      # rebuild the kanji→path map (per-kanji sources only)
python kbs.py build                    # bulk: one fetch of the whole table; per-kanji: iterate the map
python kbs.py build -r                 # re-fetch / overwrite existing entries
python kbs.py --source <name> ...      # pick source (default: jitenon; available: jitenon, bunka.org, wiktionary)
python kbs.py --store path.json ...    # override store path (default derives from --source)
python kbs.py --map   path.json ...    # override map path   (default derives from --source)

# Vocabulary lookup (display only — does NOT write any file)
python kbs.py tango <word>             # fetch from the default tango source, print headword/reading/品詞/語義

# Anki card generation (CSV with dedup prompt)
python kbs.py anki --type kankenjiten <selector> ...   # jitenon kanji cards. Each selector is a kanken level / range / kanji string.
python kbs.py anki --type kankenjiten 10               #   → all 10級 kanji (~80)
python kbs.py anki --type kankenjiten 1.5              #   → all 準1級 kanji
python kbs.py anki --type kankenjiten 1-3              #   → levels 1, 1.5, 2, 2.5, 3 (half-levels included)
python kbs.py anki --type kankenjiten 生学校            #   → just those kanji (must be in the jitenon store)
python kbs.py anki --type kankenjiten 10 生            #   → union of selectors
python kbs.py anki --type tangowiki <word>             # fetch a word, prompt for 語義 selection, append one row
python kbs.py anki --type <type> --out <path>          # override output (default: data/anki/<type>.csv)

# Equivalent: python -m kbs ...
```

### `anki` and `tango`

- **`anki`** is the only way to write cards. Each `--type` is bound to **exactly one source** (e.g. `kankenjiten` → jitenon; `tangowiki` → wiktionary) — the type implies the source, so the global `--source` flag is ignored for `anki`. Output is always tab-separated CSV at `data/anki/<type>.csv`. Each card type declares its own `FIELDS` (CSV columns) and `KEY` (the field used to detect duplicates). When a row with an existing key is about to be written, the user is prompted per row: `「<key>」 already exists. Replace or skip? [r/s]`. Each card module also decides its own interactivity and required positional args — e.g. `tangowiki` requires exactly one word and prompts for 語義 selection inside its `build()`; `kankenjiten` requires ≥1 selector (level/range/kanji-string) and errors otherwise. Kanken level vocabulary (`1`, `1.5`, `2.5`, `1-3`, etc.) is centralised in `kbs/kanken.py` and shared by `kankenjiten.build()` and `cmd_kanken`.
- **`tango`** is display-only. It fetches a word and prints headword / reading / 品詞 / numbered 語義. No prompt, no file write. To add a vocabulary card, use `anki --type tangowiki <word>`.

For **bulk sources** (e.g. `bunka.org`):
- `build` is the only fetch path. It downloads the index page once and writes every entry.
- `get` is store-only — it reads `data/<source>/kanji/kanji.json` and never hits the network. Run `build` first.
- `map` is rejected (no map concept).

**Default store:** `<project root>/data/<source_name>/<type>/kanji.json`. For the active source `jitenon` (kanji type), that resolves to `<project root>/data/jitenon/kanji/kanji.json`. Override with `--store`.
**Default map:** same dir, `kanji_map.json`. Override with `--map`.

Layout: `data/` holds scraped JSON, organised `<source>/<type>/` (e.g. `data/jitenon/kanji/`, `data/bunka.org/kanji/`, future `data/jitenon/vocabulary/`). Code lives in `kbs/source/<type>/<source>.py` — the data tree mirrors it inverted (source-first vs type-first) because data is partitioned per source.

The path constants in `kbs/__main__.py`:

```python
DATA_BASE   = Path(__file__).resolve().parent.parent / "data"
SOURCE_NAME = SOURCES[DEFAULT]["name"]   # e.g. "jitenon"
DATA_DIR    = DATA_BASE / SOURCE_NAME / "kanji"
KDB_NAME    = DATA_DIR / "kanji.json"
KMAP_NAME   = DATA_DIR / "kanji_map.json"
```

## Source registry

All sources live in `kbs/sources.py` as a single dictionary, with one entry per source. Each entry is the source's full definition — `base_url`, whether it needs a map, and the class that does the parsing:

```python
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
```

`SOURCES[name]["class"](SOURCES[name])` instantiates the source — the class reads `base_url` (and anything else) from the dict it's given. There's no `BASE` constant on the class; the dict is the only place URLs are configured.

Flag semantics (cmd_* dispatches on these):
- `needs_map = True` → `cmd_get` consults `kanji_map.json` to resolve a kanji char to a fetch path. `False` would mean the source can produce a URL directly from the char.
- `bulk = True` → source has no per-kanji URL; `cmd_build` calls `KanjiAcquirer.acquire_all()` once. `cmd_get` becomes store-only. `cmd_map` is rejected.

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

Subclass `KanjiSource` (in `source/kanji/`). Implement only the methods relevant to your mode — all base methods raise `NotImplementedError` by default.

**Per-kanji mode** (jitenon-style — one URL per kanji):
- `url_for(identifier) -> str` — build a fetch URL from a map value or path
- `parse(text) -> {"kanji": str, "data": dict}` — entry HTML → dict
- `map_pages() -> [(label, url), ...]` — pages to scrape for the map, ordered easiest-first
- `parse_map_page(text) -> {kanji: path}` — extract kanji→path entries from a map page
- `identifier_from_url(url) -> str | None` — recognise a full entry URL and return its path identifier

Set `"bulk": False, "needs_map": True` (or `False` if the source can map char → URL directly).

**Bulk mode** (bunka.org-style — one URL returns the whole table):
- `bulk_url() -> str` — the single page to fetch
- `parse_all(text) -> {kanji_char: data}` — extract all entries in one pass

Set `"bulk": True, "needs_map": False`. The acquirer's `acquire_all()` will fetch once and stamp `取得日時` on every entry.

Either way, register in `kbs/sources.py`. No HTTP code in the source — that lives in `transport/`.

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

### jitenon

URL pattern: `https://kanji.jitenon.jp/kanji/{id:03d}` (zero-padded 3-digit id).
Main info table CSS selector: `table.kanjirighttb`.
Composition section: `<h2 id="m_kousei">` → following `<ul><li><a>...</a></li></ul>`.
Unicode value: `<table class="moji_code">` row with `<th>Unicode</th>`.

### bunka.org

Single page: `https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/kanji/joyokanjisakuin/index.html`.
Table selector: `<table class="display">` — 2,136 rows + header.
Columns: `漢字 / 音訓 / 例 / 備考`. The `例` column is currently unused (could be parsed later to derive reading-example pairs).
Encoding: **CP932** (header omits charset; `HttpTransport` falls back to `apparent_encoding`).

Cell parsing:
- 漢字: `"新 （旧）"` (full-width parens) → `漢字 = 新`, `康熙 = 旧`. Plain `"新"` → `康熙 = ""`.
- 音訓: whitespace-separated. Tokens entirely katakana → `音`; entirely hiragana → `訓`. All readings land in the `常` bucket (no 外 distinction on bunka.org).
- 例: skipped for now.
- 備考: raw cell text (often contains hints like `"明日（あす）"` or cross-references like `"⇔火"`).

**Schema** (`bunka.org.struct` is the source-of-truth spec):

```json
{
  "明": {
    "康熙": "",
    "読み": { "音": {"常": ["メイ","ミョウ"]}, "訓": {"常": ["あかり", ...]} },
    "備考": "明日（あす） ⇔開ける，空ける",
    "付表": {},
    "取得日時": "2026-05-19T21:09:51+09:00"
  }
}
```

`付表` is intentionally left empty: the bunka.org HTML index page does not expose it. The 付表 (jukujikun/ateji) is only published inside the PDF `joyokanjihyobesi_20101130.pdf`. Implementing it is a separate task that requires PDF parsing. When that lands, beware: 備考 already carries hints like `"明日（あす）"` for some kanji — those are not 付表 entries proper, just remarks.

## Notes for future Claude sessions

**Working language.** Pierre studies Japanese — for any 日本語 topic (kanji explanations, readings, meanings, page summaries), respond in 日本語 by default, not English. Earlier in this project he pushed back with "why are you showing english?" Code and software-engineering discussion stay English. When unsure, ask which language he prefers rather than silently defaulting.

**JSON field labels.** Keep Japanese terms (`読み`, `部首`, `意味`, `分類`, …) — don't romanise or translate without being asked.

**Design cadence.** He iterates carefully on data schemas before coding ("do not code now", "show the full result for 生", many small rounds compacting the structure). Don't rush to implementation; align on the schema/architecture first.

**Parsing gotchas baked into `JitenonKanjiSource`:**
- BS4's `html.parser` produces a `RubyTextString` subclass for `<rt>` content; `Tag.get_text()` and `.strings` *skip* it. Use the `_full_text()` helper (walks `.descendants` and includes every `NavigableString` that isn't `Comment`/`CData`) when you want furigana inline (e.g. for `意味`). Use `_label()` (which decomposes `<rt>` first) when you want clean labels.
- The page uses full-width characters: `＋` for stroke-count split (`生５＋０`), and `０-９` for digits. `ZEN_TO_HAN` translates both `＋／－` and the digits — apply it before any regex on numeric fields.
- The 種別 row is a slash-separated string of `<a>` links; the categorisation `名前に使える漢字` does NOT imply a separate 人名 entry in `分類` if the kanji is also 常用 (`名前に使える` = 常用 ∪ 人名用). Only emit `"人名"` when `名` is present AND `常` is absent.

**`分類` history is not on jitenon.** The page only tells us current membership. The script seeds `分類` entries with `[true, []]`; the year history (`"昭56"`, `"平29:1"`, etc.) has to be added by hand or from another source.

**Parsing gotchas baked into `BunkaKanjiSource`:**
- The page is served as **CP932** with no `Content-Type` charset. `requests.text` would mangle it (defaults to ISO-8859-1); `HttpTransport` now sets `resp.encoding = resp.apparent_encoding` when the header is missing or ISO-8859-1. CP932 (not strict `shift_jis`) is needed because the table contains characters in the IBM/NEC extension areas (`0xfa…` bytes).
- 漢字 cell uses **full-width** parens `（）` and a full-width space between the new form and the old form. Match with `[（(]…[）)]` to be permissive.
- 訓 readings have **no okurigana dot** (e.g. `あわれむ`, not `あ.われむ`). bunka.org's schema is intentionally simpler than jitenon's — don't try to align them.
- 備考 is the raw column text and often contains 熟字訓 hints in parens (`"明日（あす）"`) and cross-references (`"⇔火"`). Don't try to parse these into structured fields without a separate spec.

**Encoding fallback in `HttpTransport`.** Any new Japanese source that omits the HTTP charset header will be auto-decoded via `apparent_encoding` (chardet). Stable for CP932 / Shift_JIS / EUC-JP pages; if a future source has a known stable encoding, prefer setting it explicitly in the source rather than relying on detection.
