from typing import Optional

from .base import Display


class CliDisplay(Display):
    def show(self, kanji: str, data: Optional[dict]) -> None:
        if data is None:
            print(f"漢字「{kanji}」: データなし")
            return

        print(f"漢字「{kanji}」")
        print(f"  部首    : {data.get('部首', '')}")
        print(f"  画数    : {data.get('画数', '')}")
        shubetsu = data.get("種別", [])
        print(f"  種別    : {' / '.join(shubetsu)}")
        print(f"  学年    : {data.get('学年', '')}")
        print(f"  漢字検定: {data.get('漢字検定', '')}")
        print(f"  Unicode : {data.get('Unicode', '')}")

        yomi = data.get("読み", {})
        if "音" in yomi:
            print("  音読み  :")
            for cat, vals in yomi["音"].items():
                print(f"    [{cat}] {'、'.join(vals)}")
        if "訓" in yomi:
            print("  訓読み  :")
            for cat, vals in yomi["訓"].items():
                print(f"    [{cat}] {'、'.join(vals)}")

        meanings = data.get("意味", [])
        if meanings:
            print("  意味    :")
            for i, m in enumerate(meanings, 1):
                print(f"    {i}. {m}")

        kousei = data.get("漢字構成", [])
        if kousei:
            print(f"  漢字構成: {'、'.join(kousei)}")

        bun = data.get("分類", {})
        if bun:
            print("  分類    :")
            for k, v in bun.items():
                state = "✓" if v[0] else "✗"
                events = "、".join(v[1]) if v[1] else "—"
                print(f"    {k} [{state}]: {events}")
