#!/usr/bin/env python3
"""Caption checks for Scan The Good News. They enforce Caleb's writing rules so a draft cannot slip through with AI tells.

  python3 -I tools/checks.py CAPTIONS.json --verses VERSES.json [--context-file CONTEXT.json] [--log data/posts-log.json]

CAPTIONS.json: [{"ref": "John 3:16", "caption": "..."}, ...] in posting order.
Prints a JSON report and exits 0 when every caption passes the hard checks, 2 when any caption fails one.
"fails" must be fixed before a post is scheduled. "warns" should be fixed when the fix is easy.
"verify" lists numbers, quotes and Scripture references in the caption; each one must be checked against the Bible text.
"""
import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent

MIN_WORDS, MAX_WORDS = 35, 70
OVERLAP_FAIL = 6      # words in a row shared with an earlier caption
VERSE_RUN_WARN = 8    # words in a row copied from the verse itself
LOOKBACK = 8          # earlier captions compared for openings

STOCK_FAIL = [
    "not just", "isn't just", "is not just", "more than just", "not only", "here's the thing", "let that sink in", "dive into",
    "dive in", "unpack", "game-changer", "game changer", "in a world where", "imagine if", "journey", "at the end of the day",
    "the truth is", "the reality is", "fair question", "exactly why", "straight from scripture", "no pressure", "a reminder that",
    "powerful reminder", "gentle reminder", "tapestry", "testament", "beacon", "delve", "profound", "resonate", "navigate",
    "unlock", "transformative", "intentional", "in this season", "season of", "step into", "lean into", "sit with", "hold space",
    "take a moment", "pause and", "let's pause", "church family", "faith over", "heart posture", "speak life",
]
STOCK_WARN = ["blessed", "blessing", "amazing", "incredible", "powerful", "so much", "deeply", "gracious", "beautiful",
              "reminds us", "remind us", "we are called", "calls us to", "invites us", "invitation", "every single day", "daily reminder",
              "reflect on", "ponder", "walk in", "lean on", "rooted in", "anchored in", "keep going", "don't give up", "hold on"]
REASSURE = [
    "you are not alone", "you're not alone", "you aren't alone", "don't have to have it all figured out", "it's okay to", "it is okay to",
    "you are enough", "god's got you", "god has got you", "god has a plan for you", "everything happens for a reason", "trust the process",
    "you matter", "better days", "you've got this", "you got this", "one day at a time",
    "you are seen", "he sees you", "be gentle with yourself", "give yourself grace", "you are loved", "you're loved",
]
PROMO = ["scanthegoodnews", "scan the good news", "link in bio", "in our bio", "in my bio", "follow us", "follow for", "follow along", "dm me",
         "dm us", "subscribe", "share this", "tag a friend", "tag someone", "comment below", "drop a", "visit our", "check out", "our website",
         "shirt", "qr code", "scan the qr", "donate", "give toward", "click", "swipe"]
OPENERS = re.compile(r"^(most of us|imagine|picture this|have you ever|ever wonder|ever feel|ever felt|we've all|we all|let's be honest|"
                     r"let's talk|think about it|here's the thing|good morning|happy |hey |hello|friends|today i|today we|did you know|what if)\b")
ANTI_FAIL = [
    (re.compile(r"\b(?:isn't|is not|wasn't|was not|aren't|are not|doesn't|does not|don't|do not|won't|will not|can't|cannot) (?:just|only|merely|simply)\b"),
     "'not just/only X' construction"),
    (re.compile(r"\bnot (?:just|only|merely|simply) [^.?!]{0,70}?\bbut\b"), "'not just X but Y' construction"),
    (re.compile(r"\b(?:less|more) [a-z]+,? (?:and )?(?:less|more) [a-z]+"), "slogan-style 'less X, more Y'"),
]
ANTI_WARN = [
    (re.compile(r"\bnot [^.?!,]{1,50}, but\b"), "'not X, but Y' construction"),
    (re.compile(r"\b(?:it's|it is|this is|that's|that is) not [^.?!]{0,70}[.?!]\s+(?:it's|it is|this is|that's|that is|it)\b"), "tidy two-beat 'It's not X. It's Y.'"),
    (re.compile(r"\b(?:isn't|is not|wasn't|aren't|don't|doesn't|won't|can't) [^.?!]{0,60}[.?!]\s+(?:it|that|this|they|he|she|we|you) (?:can|will|does|is|are|do)\b"),
     "possible tidy two-beat 'X won't Y. It can Z.'"),
    (re.compile(r"\b[a-z]+, [a-z]+,? (?:and|or) [a-z]+\b"), "three single words in a row (rule of three?)"),
]
SIGNATURES = ["friendly reminder that", "take my word for it", "major shout out", "don't just take"]
NUMBER_WORDS = ("two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
                "thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
                "twice")
CONTR = re.compile(r"\b\w+n't\b|\b\w+'(?:re|ve|ll|m|d)\b|\b(?:it|that|let|there|here|what|he|she|who)'s\b", re.I)


def norm(t):
    return (t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            .replace(" ", " "))


def toks(t):
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", norm(t).lower())


def sentences(t):
    t = re.sub(r"\s+", " ", norm(t)).strip()
    t = re.sub(r"\b([A-Z])\.(?=\s[A-Z])", r"\1<DOT>", t)
    out = re.split(r"(?<=[.!?])[\"']?\s+(?=[A-Z0-9\"'])", t)
    return [s.replace("<DOT>", ".") for s in out if s.strip()]


def longest_run(a, b):
    best, where = 0, ""
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best, where = cur[j], " ".join(a[i - cur[j]:i])
        prev = cur
    return best, where


def norm_ref(ref):
    return re.sub(r"\s+", " ", str(ref).strip().lower()).replace("psalms ", "psalm ")


def has_phrase(low, phrase):
    return re.search(r"(?<![a-z'])" + re.escape(phrase) + r"(?![a-z])", low) is not None


def outside_quotes(t):
    return re.sub(r"\"[^\"]*\"", " ", norm(t))


def check_one(cap, ref, verse, context):
    fails, warns = [], []
    t = norm(cap).strip()
    low = re.sub(r"\s+", " ", t.lower())
    words = len(t.split())
    sents = sentences(t)
    lens = [len(s.split()) for s in sents]
    if not MIN_WORDS <= words <= MAX_WORDS:
        fails.append(f"length: {words} words (needs {MIN_WORDS} to {MAX_WORDS})")
    for name, ch in (("em dash", "—"), ("en dash", "–"), ("ellipsis character", "…"), ("semicolon", ";"), ("hashtag", "#"),
                     ("parenthesis", "("), ("slash", "/"), ("asterisk", "*"), ("underscore", "_")):
        if ch in t:
            fails.append(f"punctuation: contains {name}")
    if "..." in t:
        fails.append("punctuation: contains an ellipsis")
    if re.search(r"\s-{1,2}\s", t):
        fails.append("punctuation: a hyphen used as a dash")
    if sum(1 for c in t if ord(c) >= 0x1F000 or 0x2600 <= ord(c) <= 0x27BF or c in "❤️"):
        fails.append("emoji")
    if t.count("!") > 1:
        fails.append("more than one exclamation mark")
    if t.count(":") > 1:
        warns.append("more than one colon")
    if t.count("?") > 2:
        warns.append("more than two questions")
    if "\n" in t:
        warns.append("line breaks: write one plain paragraph")
    if re.search(r"[^\x00-\x7f]", t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')):
        warns.append("non-ASCII characters present")
    for ph in STOCK_FAIL:
        if has_phrase(low, ph):
            fails.append(f"AI-style phrase: '{ph}'")
    for ph in STOCK_WARN:
        if has_phrase(low, ph):
            warns.append(f"greeting-card or sermon-blurb word: '{ph}'")
    for ph in REASSURE:
        if has_phrase(low, ph):
            fails.append(f"reassurance cliche: '{ph}'")
    for ph in PROMO:
        if has_phrase(low, ph):
            fails.append(f"promotion or call to action: '{ph}' (captions are strictly Scripture)")
    if OPENERS.search(low):
        fails.append("relatable-hook opener")
    for rx, label in ANTI_FAIL:
        if rx.search(low):
            fails.append(f"AI construction: {label}")
    for rx, label in ANTI_WARN:
        if rx.search(low):
            warns.append(f"possible AI construction: {label}")
    if any(re.match(r"^[A-Z][a-z]+ over [a-z]+\.?$", s) for s in sents):
        fails.append("slogan-style 'X over Y' sentence")
    if re.match(r"^(it's|it is|this is|that's|that is)\b", low):
        warns.append("opens with It's/This is (Caleb usually drops it)")
    if not any(n >= 21 for n in lens):
        warns.append("no long sentence (21+ words); Caleb runs a quarter to a third of his sentences that long")
    if not any(n <= 8 for n in lens):
        warns.append("no short sentence (8 words or fewer); about one in five of his sentences is that short")
    contr = len(CONTR.findall(t))
    if contr == 0 and words >= 45:
        warns.append("no contractions; he uses about one per 40 to 50 words")
    if contr >= 4:
        warns.append("many contractions; he uses about one per 40 to 50 words")
    oq = outside_quotes(t).lower()
    if re.search(r"\bi (?:remember|used to|was|had|went|saw|felt|learned|prayed|cried|struggled|walked|read|heard|got|lost|found)\b|"
                 r"\bmy (?:mom|mother|dad|father|grandmother|grandfather|grandma|grandpa|wife|husband|friend|friends|pastor|kids|son|daughter|"
                 r"brother|sister|family|church|story|testimony|life|childhood|youth)\b", oq):
        fails.append("personal story or memory in first person (never invent a personal story, memory or feeling)")
    fp = re.findall(r"\b(?:i|i'm|i've|i'd|i'll|me|my|myself)\b", oq)
    if fp:
        warns.append(f"first person singular ({len(fp)}): never invent a personal story, memory or feeling")
    verse_run, verse_phrase = longest_run(toks(t), toks(verse))
    if verse_run >= VERSE_RUN_WARN:
        warns.append(f"copies {verse_run} words in a row from the verse ('{verse_phrase}'); the picture already shows the verse")
    # things the model has to prove against the text
    verify = {"numbers": re.findall(rf"\b(?:\d[\d,]*|(?:{NUMBER_WORDS}))\b", t, flags=re.I),
              "scripture_references": re.findall(r"\b(?:[1-3] )?(?:[A-Z][a-z]+(?: of [A-Z][a-z]+)?) \d+(?::\d+(?:-\d+)?)?|\bverses? \d+(?:-\d+)?|\bchapters? \d+", t),
              "quotes": []}
    pool = toks(verse) + toks(context or "")
    for q in re.findall(r"\"([^\"]{1,120})\"", t):
        qt = toks(q)
        found = bool(qt) and longest_run(qt, pool)[0] == len(qt)
        verify["quotes"].append({"text": q, "found_in_passage": found})
        if not found:
            warns.append(f"quoted text not found in the verse or its context: \"{q}\" (never invent a quote)")
    return dict(ref=ref, words=words, fails=fails, warns=warns, verify=verify,
                stats=dict(sentences=len(sents), sentence_lengths=lens, long_sentences=sum(1 for n in lens if n >= 21),
                           short_sentences=sum(1 for n in lens if n <= 8), contractions=contr,
                           opening=" ".join(t.split()[:4]), closing=sents[-1] if sents else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("captions")
    ap.add_argument("--verses", required=True)
    ap.add_argument("--context-file")
    ap.add_argument("--log", default=str(HERE.parent / "data" / "posts-log.json"))
    args = ap.parse_args()
    caps = json.loads(pathlib.Path(args.captions).read_text(encoding="utf-8"))
    verses = {norm_ref(k): v for k, v in json.loads(pathlib.Path(args.verses).read_text(encoding="utf-8")).items()}
    ctx = {}
    if args.context_file:
        ctx = {norm_ref(k): v for k, v in json.loads(pathlib.Path(args.context_file).read_text(encoding="utf-8")).items()}
    logp = pathlib.Path(args.log)
    log = []
    if logp.exists():
        log = [x for x in json.loads(logp.read_text(encoding="utf-8")).get("posts", []) if x.get("caption")]
        log.sort(key=lambda x: (x.get("date", ""), x.get("time", "")))
    recent = [x["caption"] for x in log][-LOOKBACK:]
    report = []
    for i, c in enumerate(caps):
        key = norm_ref(c["ref"])
        if key not in verses:
            report.append(dict(ref=c["ref"], words=0, fails=[f"no verse text for {c['ref']!r} in the verses file"], warns=[], verify={}, stats={}))
            continue
        report.append(check_one(c["caption"], c["ref"], verses[key], ctx.get(key, "")))
    # checks that compare captions with each other and with what was already posted
    tokens = [toks(c["caption"]) for c in caps]
    for i, c in enumerate(caps):
        rep = report[i]
        if not rep["stats"]:
            continue
        others = [("an earlier post", toks(x["caption"])) for x in log] + [(f"caption {j + 1} in this batch", tokens[j]) for j in range(len(caps)) if j != i]
        for label, tk in others:
            run, phrase = longest_run(tokens[i], tk)
            if run >= OVERLAP_FAIL:
                rep["fails"].append(f"repeats {run} words in a row from {label} ('{phrase}')")
                break
        first3 = " ".join(tokens[i][:3])
        for j, prior in enumerate([toks(x) for x in recent]):
            if " ".join(prior[:3]) == first3:
                rep["fails"].append(f"same opening three words as a recent post ('{first3}')")
                break
        for j in range(len(caps)):
            if j != i and " ".join(tokens[j][:3]) == first3 and j < i:
                rep["fails"].append(f"same opening three words as caption {j + 1} in this batch ('{first3}')")
                break
        low = norm(c["caption"]).lower()
        for sig in SIGNATURES:
            if has_phrase(low, sig):
                if any(has_phrase(norm(x).lower(), sig) for x in recent[-3:]):
                    rep["fails"].append(f"signature phrase '{sig}' was used in one of the last three posts; use it only once in a while")
                elif any(has_phrase(norm(caps[j]["caption"]).lower(), sig) for j in range(i)):
                    rep["fails"].append(f"signature phrase '{sig}' is already used earlier in this batch")
    closers_if = [i for i, r in enumerate(report) if r["stats"] and r["stats"]["closing"].startswith("If ")]
    if len(closers_if) > 2:
        for i in closers_if[2:]:
            report[i]["fails"].append("too many captions in this batch end with a sentence that starts 'If'; vary how they end")
    prev_end = None
    for r in report:
        if not r["stats"]:
            prev_end = None
            continue
        end = (r["stats"]["closing"].split() or [""])[0].lower()
        if prev_end is not None and end == prev_end:
            r["warns"].append(f"ends the same way as the caption before it (its last sentence also starts with '{end}')")
        prev_end = end
    ok = all(not r["fails"] for r in report)
    print(json.dumps(dict(ok=ok, captions=report, batch=dict(count=len(caps), closers_starting_with_if=len(closers_if))), indent=2, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
