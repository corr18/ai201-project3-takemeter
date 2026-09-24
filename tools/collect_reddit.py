"""
collect_reddit.py - pull real r/NBA comments into an UNLABELED CSV.

Uses the Arctic Shift public API (arctic-shift.photon-reddit.com) rather
than reddit.com. Two reasons: reddit.com's API makes fetching a specific
past date range awkward, and Arctic Shift serves historical data, which
is what makes the frozen archival window in planning.md section 4
practical at all.

Collects raw comments only. It does NOT assign labels - that is your
judgment and it is the part the assignment grades.

Usage (Colab or local):

    import collect_reddit as cr

    # Top up a thin class with a full-text query:
    cr.collect(query="efficiency", out="stats_batch.csv",
               thread_type="stat_search")

    # Or pull a date window (good for reaction-heavy game nights):
    cr.collect(after="2025-06-23", before="2025-06-24", sort="asc",
               out="g7_batch.csv", thread_type="finals_g7_live")

    # Merge new rows into the main CSV without creating duplicates:
    cr.merge("stats_batch.csv", "../data/takemeter_labeled.csv")

API notes learned the hard way:
  - Parallel requests get you HTTP 422. Requests are serialized here,
    with a pause between them.
  - Full-text `body` search wants a single word of 4+ characters.
    "ppg" (3 chars) and "per 100" (has a space) both 422.
  - `fields` trims the response; without it every comment carries ~50
    metadata keys you don't need.
"""

import csv
import io
import os
import re
import json
import time
import html
import urllib.parse
import urllib.request

API = "https://arctic-shift.photon-reddit.com/api/comments/search"
UA = "python:takemeter-coursework:v1.0 (educational classifier project)"

# The frozen collection window from planning.md section 4: the 2025 NBA
# playoffs, ending with Thunder-Pacers Game 7 on June 22.
WINDOW_AFTER = "2025-04-19"
WINDOW_BEFORE = "2025-06-25"

MIN_WORDS = 3
MAX_WORDS = 180

BOTS = {
    "automoderator", "nba_gamethread_bot", "sneakpeekbot", "remindmebot",
    "totesmessenger", "wikitextbot", "b0trank",
}

JUNK_PATTERNS = [
    r"^\[removed\]$", r"^\[deleted\]$",
    r"^https?://\S+$",
    r"i am a bot",
    r"what'?s the stream", r"any stream", r"stream\?$",
]

FIELDS = ["text", "label", "notes", "source_thread_type", "pre_labeled"]


def _get(url, retries=3):
    """GET with retry, because Arctic Shift 422s under any concurrency."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = 5 * (attempt + 1)
            print(f"    retry in {wait}s ({e})")
            time.sleep(wait)


def _clean(body):
    t = html.unescape(body or "")
    t = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", t)  # md links -> text
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"^&gt;.*$", " ", t, flags=re.M)              # drop quoted lines
    t = re.sub(r"^>.*$", " ", t, flags=re.M)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def _is_junk(text):
    if not text:
        return True
    wc = len(text.split())
    if wc < MIN_WORDS or wc > MAX_WORDS:
        return True
    low = text.lower()
    return any(re.search(p, low) for p in JUNK_PATTERNS)


def norm(text):
    """Dedupe key. Must stay in sync with tools/check-dataset.ps1."""
    t = re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def collect(query=None, after=WINDOW_AFTER, before=WINDOW_BEFORE,
            limit=100, sort="desc", thread_type=None,
            out="reddit_batch.csv", pause=3.0):
    """Fetch comments into an unlabeled CSV.

    query       : single word, 4+ chars, for full-text search. None = date window only.
    after/before: YYYY-MM-DD. Defaults to the frozen playoff window.
    thread_type : value for the source_thread_type column.
    """
    if query and (len(query) < 4 or " " in query):
        raise ValueError("Arctic Shift body search needs one word of 4+ chars")

    params = {
        "subreddit": "nba",
        "limit": str(limit),
        "fields": "body",
        "after": after,
        "before": before,
        "sort": sort,
    }
    if query:
        params["body"] = query

    url = API + "?" + urllib.parse.urlencode(params)
    print(f"GET {url}")
    time.sleep(pause)
    data = _get(url)

    seen, rows = set(), []
    for item in data.get("data", []):
        text = _clean(item.get("body"))
        if _is_junk(text):
            continue
        key = norm(text)
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append({
            "text": text,
            "label": "",                # YOU fill this in
            "notes": "",
            "source_thread_type": thread_type or (f"q_{query}" if query else "window"),
            "pre_labeled": "no",
        })

    with io.open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} usable comments -> {out}")
    print("Labels are EMPTY on purpose. Read each one and label it by hand")
    print("using annotation-guide.md. Do not bulk-fill.")
    return rows


def merge(new_csv, main_csv):
    """Append rows from new_csv into main_csv, skipping near-duplicates."""
    with io.open(main_csv, encoding="utf-8") as f:
        existing = list(csv.DictReader(f))
    seen = {norm(r["text"]) for r in existing}

    with io.open(new_csv, encoding="utf-8") as f:
        incoming = list(csv.DictReader(f))

    added = [r for r in incoming if norm(r["text"]) not in seen
             and not seen.add(norm(r["text"]))]

    with io.open(main_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(existing + added)

    print(f"{len(existing)} existing + {len(added)} new "
          f"({len(incoming) - len(added)} dupes skipped) = {len(existing) + len(added)}")


# Queries that actually yield each class. `stat_backed` is the scarce one;
# these are the terms that worked during the initial collection pass.
SUGGESTED = {
    "stat_backed": ["averaged", "shooting", "efficiency", "percentage",
                    "rebounds", "assists", "splits", "rating"],
    "hot_take": ["overrated", "underrated", "trash", "fraud"],
    "reaction": [],   # use game-night date windows instead, sort="asc"
}
