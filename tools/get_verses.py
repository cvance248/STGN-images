#!/usr/bin/env python3
"""Exact KJV text from the public-domain dataset aruljohn/Bible-kjv (fetched from raw.githubusercontent.com).

  python3 -I tools/get_verses.py --out verses.json [--cache DIR] [--context 3] [--count WORD] [--chapter-info] REF [REF ...]

REF looks like "Isaiah 41:10", "Psalm 119:105" or "Ephesians 5:15-16".
  --out FILE        write {"Isaiah 41:10": "<verse text>", ...} (the file make_pictures.py and checks.py read)
  --cache DIR       where the downloaded book files are kept (default /tmp/stgn-bible)
  --context N       also print N verses before and after each reference, so the verse is read in its setting
  --context-out F   with --context, write {"ref": "<verse plus its neighbours>"} to F (checks.py uses it to verify quotes)
  --count WORD      print how many times WORD (whole word, case-sensitive) appears in each verse, to check a claim
  --chapter-info    print how many verses the chapter has and how many chapters the book has
Text is printed exactly as it will be set on the picture. Never retype or "fix" a verse by hand.
"""
import argparse
import json
import pathlib
import re
import sys
import time
import urllib.request

BASE = "https://raw.githubusercontent.com/aruljohn/Bible-kjv/master/"
BOOKS = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings",
         "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes",
         "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah",
         "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts",
         "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
         "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John",
         "2 John", "3 John", "Jude", "Revelation"]
CANON = {b.lower(): b for b in BOOKS}
CANON.update({"psalm": "Psalms", "song of songs": "Song of Solomon", "songs of solomon": "Song of Solomon", "revelations": "Revelation"})


def parse_ref(ref):
    m = re.fullmatch(r"\s*((?:[1-3]\s*)?[A-Za-z][A-Za-z ]*?)\s+(\d+):(\d+)(?:\s*[-–]\s*(\d+))?\s*", ref)
    if not m:
        raise SystemExit(f"cannot read reference {ref!r}; use a form like 'John 3:16' or 'Ephesians 5:15-16'")
    book = re.sub(r"^([1-3])\s*", r"\1 ", re.sub(r"\s+", " ", m.group(1).strip())).lower()
    if book not in CANON:
        raise SystemExit(f"unknown book {m.group(1)!r} in {ref!r}")
    ch, v1 = int(m.group(2)), int(m.group(3))
    v2 = int(m.group(4)) if m.group(4) else v1
    if v2 < v1:
        raise SystemExit(f"verse range runs backwards in {ref!r}")
    return CANON[book], ch, v1, v2


def display_ref(book, ch, v1, v2):
    name = "Psalm" if book == "Psalms" else book
    return f"{name} {ch}:{v1}" + (f"-{v2}" if v2 != v1 else "")


def load_book(book, cache):
    path = cache / (book.replace(" ", "") + ".json")
    if not path.exists():
        url = BASE + book.replace(" ", "") + ".json"
        last = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    data = r.read()
                json.loads(data.decode("utf-8"))  # must be valid before it is cached
                path.write_bytes(data)
                break
            except Exception as e:  # network hiccup or bad file: try again
                last = e
                time.sleep(2 * (attempt + 1))
        else:
            raise SystemExit(f"could not download {url}: {last}")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("refs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default="/tmp/stgn-bible")
    ap.add_argument("--context", type=int, default=0)
    ap.add_argument("--context-out")
    ap.add_argument("--count")
    ap.add_argument("--chapter-info", action="store_true")
    args = ap.parse_args()
    cache = pathlib.Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    result, contexts = {}, {}
    for ref in args.refs:
        book, ch, v1, v2 = parse_ref(ref)
        data = load_book(book, cache)
        chapter = next((c for c in data["chapters"] if int(c["chapter"]) == ch), None)
        if chapter is None:
            raise SystemExit(f"{book} has no chapter {ch}")
        by_num = {int(v["verse"]): re.sub(r"\s+", " ", v["text"]).strip() for v in chapter["verses"]}
        missing = [n for n in range(v1, v2 + 1) if n not in by_num]
        if missing:
            raise SystemExit(f"{book} {ch} has no verse(s) {missing}")
        text = " ".join(by_num[n] for n in range(v1, v2 + 1))
        key = display_ref(book, ch, v1, v2)
        result[key] = text
        print(f"{key}  ({len(text.split())} words)\n  {text}")
        if args.count is not None:
            n = len(re.findall(r"(?<![A-Za-z'])" + re.escape(args.count) + r"(?![A-Za-z'])", text))
            print(f"  '{args.count}' appears {n} time(s)")
        if args.chapter_info:
            print(f"  {book} {ch} has {len(by_num)} verses; {book} has {len(data['chapters'])} chapters")
        if args.context:
            lo, hi = max(1, v1 - args.context), min(max(by_num), v2 + args.context)
            print("  context:")
            for n in range(lo, hi + 1):
                mark = ">" if v1 <= n <= v2 else " "
                print(f"   {mark} {n} {by_num[n]}")
            contexts[key] = " ".join(by_num[n] for n in range(lo, hi + 1))
        print()
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.context_out:
        pathlib.Path(args.context_out).write_text(json.dumps(contexts, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
