#!/usr/bin/env python3
"""Posting dates, the monthly cap, the verse bank and the posting log for the Instagram run.

  python3 -I tools/planner.py settings                        validate data/settings.json and print it
  python3 -I tools/planner.py plan [--metricool M.json] [--count N] [--today YYYY-MM-DD] [--ignore-ahead]
      exit 0 = dates chosen, 3 = paused in settings, 4 = posts are already far enough ahead, 2 = problem
  python3 -I tools/planner.py bank [--tone TONE]               verses not used yet, grouped by tone
  python3 -I tools/planner.py add ENTRIES.json                 append new posts to the log (validated)
  python3 -I tools/planner.py status --uuid U --status S       change a post's status ("--date D" works too)
  python3 -I tools/planner.py show [--days N]                  recent and upcoming posts

M.json is what Metricool says is scheduled: [{"uuid": "...", "date": "YYYY-MM-DD"}, ...]. Those posts count toward the monthly cap.
Common options: --log data/posts-log.json  --settings data/settings.json  --bank data/verse-bank.json
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parent / "data"
STATUSES = {"pending", "draft", "scheduled", "published", "failed", "removed"}
REQUIRED = ["date", "time", "timezone", "ref", "translation", "tone", "kind", "look", "image", "image_url", "caption", "alt", "status"]
DEFAULTS = {"paused": False, "mode": "schedule", "posts_per_batch": 5, "post_time": "10:00", "timezone": "America/New_York",
            "weekdays": [0, 1, 2, 3, 4], "monthly_cap": 20, "min_lead_days": 4, "skip_if_ahead_days": 8, "skip_dates": []}


def norm_ref(ref):
    return re.sub(r"\s+", " ", str(ref).strip().lower()).replace("psalms ", "psalm ")


def load_settings(path):
    p = pathlib.Path(path)
    raw = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    s = dict(DEFAULTS)
    s.update({k: v for k, v in raw.items() if k in DEFAULTS})
    problems = []
    if not isinstance(s["paused"], bool):
        problems.append("paused must be true or false")
    if s["mode"] not in ("schedule", "draft"):
        problems.append("mode must be 'schedule' or 'draft'")
    if not (isinstance(s["posts_per_batch"], int) and 1 <= s["posts_per_batch"] <= 7):
        problems.append("posts_per_batch must be a whole number from 1 to 7")
    m = re.fullmatch(r"(\d{2}):(\d{2})", str(s["post_time"]))
    if not m or not (6 <= int(m.group(1)) <= 21 and int(m.group(2)) < 60):
        problems.append("post_time must be HH:MM between 06:00 and 21:59")
    try:
        ZoneInfo(s["timezone"])
    except Exception:
        problems.append(f"timezone {s['timezone']!r} is not a valid IANA name")
    if not (isinstance(s["weekdays"], list) and s["weekdays"] and all(isinstance(x, int) and 0 <= x <= 6 for x in s["weekdays"])):
        problems.append("weekdays must be a list of numbers 0 (Monday) to 6 (Sunday)")
    if not (isinstance(s["monthly_cap"], int) and 1 <= s["monthly_cap"] <= 60):
        problems.append("monthly_cap must be a whole number from 1 to 60")
    if not (isinstance(s["min_lead_days"], int) and 2 <= s["min_lead_days"] <= 30):
        problems.append("min_lead_days must be a whole number from 2 to 30")
    if not (isinstance(s["skip_if_ahead_days"], int) and 2 <= s["skip_if_ahead_days"] <= 60):
        problems.append("skip_if_ahead_days must be a whole number from 2 to 60")
    if not (isinstance(s["skip_dates"], list) and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(x)) for x in s["skip_dates"])):
        problems.append("skip_dates must be a list of YYYY-MM-DD dates")
    return s, problems


def load_log(path):
    p = pathlib.Path(path)
    if not p.exists():
        return {"about": "", "posts": []}
    return json.loads(p.read_text(encoding="utf-8"))


def save_log(path, data):
    data["posts"].sort(key=lambda x: (x.get("date", ""), x.get("time", "")))
    pathlib.Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def today_in(tzname, override=None):
    if override:
        return dt.date.fromisoformat(override)
    return dt.datetime.now(ZoneInfo(tzname)).date()


def cmd_settings(args):
    s, problems = load_settings(args.settings)
    print(json.dumps(dict(settings=s, problems=problems), indent=2))
    return 2 if problems else 0


# --------------------------------------------------------------------------- plan
def cmd_plan(args):
    s, problems = load_settings(args.settings)
    if problems:
        print(json.dumps(dict(ok=False, problems=problems), indent=2))
        return 2
    if s["paused"]:
        print(json.dumps(dict(ok=True, paused=True, note="data/settings.json says paused: do nothing except report that the run is paused")))
        return 3
    log = load_log(args.log)["posts"]
    today = today_in(s["timezone"], args.today)
    tz = ZoneInfo(s["timezone"])
    known = {}
    for x in log:
        key = x.get("metricool_uuid") or f"log:{x['date']}:{x['ref']}"
        known[key] = (x["date"], x.get("status") != "removed")
    extra = json.loads(pathlib.Path(args.metricool).read_text(encoding="utf-8")) if args.metricool else []
    for m in extra:
        known[m["uuid"]] = (m["date"][:10], True)   # Metricool is authoritative and always counts
    counts = Counter(d[:7] for d, counts_ in known.values() if counts_)
    all_dates = [x["date"] for x in log]
    if all_dates and not args.ignore_ahead:
        ahead = (dt.date.fromisoformat(max(all_dates)) - today).days
        if ahead >= s["skip_if_ahead_days"]:
            print(json.dumps(dict(ok=True, skip=True, ahead_by_days=ahead, last_logged_date=max(all_dates),
                                  note=f"posts are already logged {ahead} days ahead (limit {s['skip_if_ahead_days']}); nothing to add this run")))
            return 4
    earliest = today + dt.timedelta(days=s["min_lead_days"])
    cursor = max(earliest, dt.date.fromisoformat(max(all_dates)) + dt.timedelta(days=1)) if all_dates else earliest
    want = args.count or s["posts_per_batch"]
    chosen, skipped = [], []
    d = cursor
    h, mi = (int(x) for x in s["post_time"].split(":"))
    while len(chosen) < want and (d - cursor).days < 150:
        iso = d.isoformat()
        month = iso[:7]
        if d.weekday() not in s["weekdays"] or iso in s["skip_dates"]:
            d += dt.timedelta(days=1)
            continue
        if counts[month] >= s["monthly_cap"]:
            skipped.append(dict(date=iso, reason=f"{month} already has {counts[month]} posts (monthly cap {s['monthly_cap']}); moving to the next month"))
            d = (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
            continue
        local = dt.datetime(d.year, d.month, d.day, h, mi, tzinfo=tz)
        chosen.append(dict(date=iso, time=s["post_time"], timezone=s["timezone"], dateTime=local.strftime("%Y-%m-%dT%H:%M:%S"),
                           iso=local.isoformat(), weekday=d.strftime("%A")))
        counts[month] += 1
        d += dt.timedelta(days=1)
    out = dict(ok=True, paused=s["paused"], mode=s["mode"], today=today.isoformat(), first_possible=cursor.isoformat(), dates=chosen,
               skipped=skipped, month_counts=dict(sorted(counts.items())), settings=s)
    if len(chosen) < want:
        out["ok"] = False
        out["problems"] = [f"only {len(chosen)} dates found"]
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 2


# --------------------------------------------------------------------------- bank
def cmd_bank(args):
    bank = json.loads(pathlib.Path(args.bank).read_text(encoding="utf-8"))["verses"]
    used = {norm_ref(x["ref"]) for x in load_log(args.log)["posts"]}
    left = [v for v in bank if norm_ref(v["ref"]) not in used]
    by = defaultdict(list)
    for v in left:
        by[v["tone"]].append(v)
    print(f"{len(left)} of {len(bank)} verses unused")
    for tone in sorted(by):
        if args.tone and tone != args.tone:
            continue
        print(f"\n{tone} ({len(by[tone])}):")
        print("  " + "; ".join(f"{v['ref']} ({v['words']}w)" for v in by[tone]))
    return 0


# --------------------------------------------------------------------------- log
def cmd_add(args):
    data = load_log(args.log)
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    problems = []
    taken_dates = {x["date"] for x in data["posts"] if x.get("status") != "removed"}
    used_refs = {norm_ref(x["ref"]) for x in data["posts"]}
    for e in entries:
        miss = [k for k in REQUIRED if not e.get(k)]
        if miss:
            problems.append(f"{e.get('date')}: missing {miss}")
            continue
        if e["status"] not in STATUSES:
            problems.append(f"{e['date']}: bad status {e['status']!r}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]):
            problems.append(f"bad date {e['date']!r}")
        if e["date"] in taken_dates:
            problems.append(f"{e['date']}: a post is already logged for that date")
        if norm_ref(e["ref"]) in used_refs:
            problems.append(f"{e['ref']}: already used")
        if not str(e["image_url"]).startswith("https://raw.githubusercontent.com/cvance248/STGN-images/"):
            problems.append(f"{e['date']}: image_url must point at the STGN-images repo")
        taken_dates.add(e["date"])
        used_refs.add(norm_ref(e["ref"]))
    if problems:
        print(json.dumps(dict(ok=False, problems=problems), indent=2))
        return 2
    data["posts"].extend(entries)
    save_log(args.log, data)
    print(json.dumps(dict(ok=True, added=len(entries), total=len(data["posts"]))))
    return 0


def cmd_status(args):
    if bool(args.uuid) == bool(args.date):
        print("give exactly one of --uuid or --date")
        return 2
    if args.status not in STATUSES:
        print(f"status must be one of {sorted(STATUSES)}")
        return 2
    data = load_log(args.log)
    hits = [x for x in data["posts"] if (args.uuid and x.get("metricool_uuid") == args.uuid) or (args.date and x.get("date") == args.date)]
    if len(hits) != 1:
        print(f"expected exactly one matching post, found {len(hits)}")
        return 2
    hits[0]["status"] = args.status
    if args.uuid_set:
        hits[0]["metricool_uuid"] = args.uuid_set
    save_log(args.log, data)
    print(json.dumps(dict(ok=True, date=hits[0]["date"], ref=hits[0]["ref"], status=args.status)))
    return 0


def cmd_show(args):
    s, _ = load_settings(args.settings)
    today = today_in(s["timezone"])
    for x in load_log(args.log)["posts"]:
        d = dt.date.fromisoformat(x["date"])
        if (d - today).days < -args.days:
            continue
        print(f"{x['date']} {x['time']}  {x['status']:<9} {x['ref']:<16} {x['look']:<22} {x.get('metricool_uuid') or '-'}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default=str(DATA / "posts-log.json"))
    ap.add_argument("--settings", default=str(DATA / "settings.json"))
    ap.add_argument("--bank", default=str(DATA / "verse-bank.json"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("settings").set_defaults(fn=cmd_settings)
    p = sub.add_parser("plan")
    p.add_argument("--metricool")
    p.add_argument("--count", type=int)
    p.add_argument("--today")
    p.add_argument("--ignore-ahead", action="store_true", help="plan even if posts are already logged far ahead")
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("bank")
    p.add_argument("--tone")
    p.set_defaults(fn=cmd_bank)
    p = sub.add_parser("add")
    p.add_argument("entries")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("status")
    p.add_argument("--uuid")
    p.add_argument("--date")
    p.add_argument("--status", required=True)
    p.add_argument("--uuid-set", help="also record a new Metricool uuid")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("show")
    p.add_argument("--days", type=int, default=14)
    p.set_defaults(fn=cmd_show)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
