# kbs — Kanji BunSeki (漢字分析)

A small CLI for fetching and analysing kanji entries from various sources.
Data is parsed into a single JSON store and exposed through subcommands for lookup, classification, and
study-card-style display.

The data source and the renderer are decoupled (see `CLAUDE.md` for the
architecture), so jitenon can be swapped for another source — or the CLI
display swapped for an Anki/Markdown/whatever exporter — without touching the
rest.

## Install

```bash
pip install requests beautifulsoup4
```

Python 3.10+ (the code uses `X | None` annotations).

## Quick start

```bash
# jitenon (per-kanji, default source)
python kbs.py map                # build the kanji→URL-path map (≈12 page fetches)
python kbs.py build              # fetch every kanji in the map into the store (slow once)
python kbs.py joyo               # print every 常用 kanji in the store
python kbs.py anki 生            # study-card view for 生

# bunka (single-page bulk source — 常用漢字索引)
python kbs.py --source bunka.org build   # one fetch → 2,136 entries
python kbs.py --source bunka.org get 追  # store-only read (no network)
```

`python -m kbs …` is equivalent to `python kbs.py …`.

## Sources

| name      | mode       | URL pattern                              | needs map | notes                          |
|-----------|------------|------------------------------------------|-----------|--------------------------------|
| `jitenon`   | per-kanji  | `kanji.jitenon.jp/kanji/{id}`            | yes       | default; rich schema           |
| `bunka.org` | bulk       | `bunka.go.jp/...joyokanjisakuin/index.html` | no   | 常用漢字 only; CP932 page; 付表 unimplemented |

Pick with `--source <name>` (default: `jitenon`). Each source writes to its own
file: `data/<source>/kanji/kanji.json`.

## Subcommands

### `get` — fetch / display a single kanji

```bash
python kbs.py get 生                                     # store-first, then display
python kbs.py get 生 -r                                  # force re-fetch
python kbs.py get https://kanji.jitenon.jp/kanji/043     # fetch by source URL
```

Auto-builds the kanji→path map on first miss, then retries.

### `map` — rebuild the kanji→path lookup table

```bash
python kbs.py map
```

Replaces (not merges) `kanji_map.json`. Pages are walked easiest→hardest
(`kyu10` … `kyu01`); the recorded level for each kanji is the easiest one it
appears on.

### `build` — populate the store from the map

```bash
python kbs.py build              # skip entries already in the store
python kbs.py build -r           # re-fetch everything
```

Resumable: saves after each fetch. On failure, you get an inline summary and a
`Continue? [Y/n]` prompt (Enter = keep going).

### `joyo` — 常用漢字 lookup

```bash
python kbs.py joyo                          # list every joyo kanji in the store
python kbs.py joyo 罪漢字検定               # classify each char
python kbs.py joyo 罪 漢字 検定             # multi-arg form (space-separated chunks)
```

Classify output has up to three rows; empty rows are omitted:

```
joyo     : <chars> : N kanji      # found and marked 常 in 種別
not joyo : <chars> : N kanji      # found but not 常 (or non-kanji char)
unknown  : <chars> : N kanji      # kanji char not in store
```

### `kanken` — 漢字検定 lookup by level

```bash
python kbs.py kanken 1                      # list every 1級 kanji
python kbs.py kanken 1.5                    # 準1級
python kbs.py kanken 10 字生男              # classify against level 10
python kbs.py kanken 罪 漢字検定 生今コ     # no level → aggregate per level
```

Valid levels: `1 1.5 2 2.5 3 4 5 6 7 8 9 10` (the `.5` levels are 準, i.e.
準1級 / 準2級). With a level, behaves like `joyo` (list or 3-bucket classify).
Without a level, all args are treated as kanji and grouped per level:

```
kanken 10 : 字生 : 2 kanji
kanken 9  : 今  : 1 kanji
kanken 8  : 漢定 : 2 kanji
kanken 6  : 罪検 : 2 kanji
unknown   : コ  : 1 kanji
```

### `anki` — compact study-card view

```bash
python kbs.py anki 生
```

```
生
音: ショウ セイ
訓: い.かす い.きる … (いのち うぶ な.す な.る)
部首: 生
意味:
  - いきる。いかす。
  - …
```

`(…)` parens hold 表外 (`外`) readings when present; 常用 (`常`) readings come
first without a label. Empty sections are omitted. Read-only: errors if the
kanji isn't in the store.

## Global options

```bash
--store <path>     # override store JSON (default: ./data/jitenon/kanji/kanji.json)
--map <path>       # override map JSON   (default: ./data/jitenon/kanji/kanji_map.json)
-v / --verbose     # print [v] source-file-check messages to stderr
```

## Data layout

```
<project root>/data/<source>/<type>/
└── e.g. data/jitenon/kanji/
    ├── kanji.json       # the store — top-level keys are kanji chars
    └── kanji_map.json   # { kanji: "<kyu_label>/<source_path>", … }
```

Both files are plain UTF-8 JSON, human-inspectable. See `CLAUDE.md` for the
full per-entry schema (readings buckets, 種別 codes, 分類 history events, etc.).

## Extending

- **New source** — subclass `KanjiSource` (in `kbs/source/kanji/`), register in
  `kbs/sources.py`. No HTTP code in the source — that lives in
  `kbs/transport/`.
- **New transport** — subclass `Transport`, implement `fetch(url) -> str`.
  Useful for caching, fixtures, or async.
- **New display** — subclass `Display` (in `kbs/display/`), implement
  `show(kanji, data)`.

See `CLAUDE.md` for the full extension contract and parsing gotchas.
