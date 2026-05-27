import csv
import sys
from pathlib import Path


class CsvFormat:
    """Tab-separated. Reads existing rows, prompts [r/s] on duplicates by KEY."""

    EXT = "csv"
    DELIMITER = "\t"

    def write(
        self, rows: list[dict], out: Path, fields: list[str], key: str,
    ) -> tuple[int, int, int]:
        out.parent.mkdir(parents=True, exist_ok=True)
        existing = self._read_keys(out, fields, key)

        added = replaced = skipped = 0
        kept: dict[str, dict] = dict(existing)

        for row in rows:
            k = row[key]
            if k in existing:
                if self._ask_replace(k):
                    kept[k] = row
                    replaced += 1
                else:
                    skipped += 1
            else:
                kept[k] = row
                added += 1

        self._write_all(out, fields, kept.values())
        return added, replaced, skipped

    def _read_keys(
        self, out: Path, fields: list[str], key: str,
    ) -> dict[str, dict]:
        if not out.exists():
            return {}
        key_idx = fields.index(key)
        result: dict[str, dict] = {}
        with out.open("r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=self.DELIMITER)
            for cols in reader:
                if len(cols) < len(fields):
                    continue
                result[cols[key_idx]] = dict(zip(fields, cols))
        return result

    def _write_all(self, out: Path, fields: list[str], rows) -> None:
        with out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(
                f,
                delimiter=self.DELIMITER,
                quoting=csv.QUOTE_MINIMAL,
                lineterminator="\n",
            )
            for row in rows:
                writer.writerow([row.get(field, "") for field in fields])

    @staticmethod
    def _ask_replace(key_value: str) -> bool:
        while True:
            try:
                ans = input(
                    f"「{key_value}」 already exists. Replace or skip? [r/s] "
                ).strip().lower()
            except EOFError:
                sys.exit(f"\nNo answer for 「{key_value}」 — aborting.")
            if ans == "r":
                return True
            if ans == "s":
                return False
