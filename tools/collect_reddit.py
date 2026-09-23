"""
collect_reddit.py - pull real r/NBA comments into an UNLABELED CSV.

Run this in Colab (it has outbound internet; some local networks block
Reddit). It collects raw comments only. It does NOT assign labels -
that is your judgment and it is the part the assignment grades.

Usage in a Colab cell:

    !wget -q https://raw.githubusercontent.com/corr18/ai201-project3-takemeter/main/tools/collect_reddit.py
    import collect_reddit as cr

    # See what's on the sub right now, grouped by likely thread type:
    cr.show_threads()

    # Then pull comments from the threads you want:
    cr.collect(["1abc234", "1def567"], thread_type="postgame", out="batch1.csv")

Then download the CSV, paste the rows into data/takemeter_labeled.csv,
and fill in the empty `label` column by hand.
"""

import csv
import re
import time
import html
import json
import urllib.request

UA = "python:takemeter-coursework:v1.0 (educational classifier project)"

# Comments shorter/longer than this are dropped. Very short ones are
# usually "this" or "lol" and carry no signal; very long ones get
# truncated by DistilBERT anyway.
MIN_WORDS = 3
MAX_WORDS = 180

BOTS = {
    "automoderator", "nba_gamethread_bot", "sneakpeekbot", "remindmebot",
    "totesmessenger", "wikitextbot", "imagesofnetwork", "b0trank",
}

# Substrings that mark a comment as not-a-take: bot output, meta chatter,
# or link-only replies. Tuned for r/NBA specifically.
JUNK_PATTERNS = [
    r"^\[removed\]$", r"^\[deleted\]$",
    r"^https?://\S+$",              # link-only
    r"i am a bot", r"^&gt;", r"^>",  # bot boilerplate, quote-only replies
    r"what'?s the stream", r"any stream", r"stream\?$",
]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _clean(body):
    """Normalize a raw comment body to a single line of plain text."""
    t = html.unescape(body or "")
    t = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", t)  # markdown links -> text
    t = re.sub(r"https?://\S+", " ", t)                      # bare urls
    t = re.sub(r"\s+", " ", t)                               # collapse newlines
    return t.strip()


def _is_junk(text, author):
    if not text:
        return True
    if (author or "").lower() in BOTS:
        return True
    wc = len(text.split())
    if wc < MIN_WORDS or wc > MAX_WORDS:
        return True
    low = text.lower()
    return any(re.search(p, low) for p in JUNK_PATTERNS)


def _norm(text):
    """Aggressive normalization for dedupe - must match tools/check-dataset.ps1."""
    t = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return re.sub(r"\s+", " ", t).strip()


def show_threads(limit=40):
    """Print current r/NBA threads, guessing thread_type from the title.

    Use this to pick which threads to pull from. planning.md section 4 wants
    you sampling different thread types on purpose, because each one
    over-produces a different label.
    """
    data = _get(f"https://www.reddit.com/r/nba/hot.json?limit={limit}")
    rows = []
    for child in data["data"]["children"]:
        d = child["data"]
        title = d["title"]
        low = title.lower()
        if low.startswith("game thread"):
            ttype = "game"
        elif low.startswith("post game thread") or low.startswith("postgame"):
            ttype = "postgame"
        elif "daily discussion" in low or "free talk" in low:
            ttype = "daily"
        elif low.startswith("[highlight]"):
            ttype = "highlight"
        else:
            ttype = "news"
        rows.append((ttype, d["id"], d["num_comments"], title[:78]))

    rows.sort()
    print(f"{'type':<10} {'id':<9} {'cmts':>6}  title")
    print("-" * 100)
    for ttype, pid, n, title in rows:
        print(f"{ttype:<10} {pid:<9} {n:>6}  {title}")
    print("\nPick ids and run: cr.collect(['id1','id2'], thread_type='postgame')")
    return rows


def collect(post_ids, thread_type="news", out="reddit_batch.csv",
            per_thread=60, sort="top", pause=2.0):
    """Fetch comments from the given submission ids into an unlabeled CSV.

    post_ids    : list of reddit submission ids (from show_threads)
    thread_type : label for the source_thread_type column
    per_thread  : cap per thread, so one huge thread can't dominate
    sort        : 'top' for substantive comments, 'new' for raw reactions
    """
    seen, rows = set(), []

    for pid in post_ids:
        url = f"https://www.reddit.com/comments/{pid}.json?limit=200&sort={sort}"
        try:
            data = _get(url)
        except Exception as e:
            print(f"  {pid}: FAILED ({e})")
            continue

        kept = 0
        # data[0] is the submission, data[1] is the comment tree
        for child in data[1]["data"]["children"]:
            if kept >= per_thread:
                break
            d = child.get("data", {})
            if child.get("kind") != "t1":
                continue
            text = _clean(d.get("body"))
            if _is_junk(text, d.get("author")):
                continue
            key = _norm(text)
            if not key or key in seen:
                continue
            seen.add(key)
            rows.append({
                "text": text,
                "label": "",                       # YOU fill this in
                "notes": "",
                "source_thread_type": thread_type,
            })
            kept += 1

        print(f"  {pid}: kept {kept}")
        time.sleep(pause)   # be polite to reddit

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "label", "notes", "source_thread_type"])
        w.writeheader()
        w.writerows(rows)

    print(f"\n{len(rows)} unique comments -> {out}")
    print("Labels are EMPTY on purpose. Read each comment and label it by hand")
    print("using annotation-guide.md. Do not bulk-fill.")
    return rows
