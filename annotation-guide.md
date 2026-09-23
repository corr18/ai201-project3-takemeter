# Annotation Cheat Sheet

One page. Keep this open in a second window while you label. Full reasoning lives in [planning.md](planning.md) — this is just the decision procedure.

---

## The decision procedure — apply in order, stop at the first hit

```
1. Specific checkable number that does argumentative work?
   └─ YES ──────────────────────────────────────────► stat_backed
   └─ NO, or the number is decorative ──┐
                                        ▼
2. Does it assert an evaluative claim?
   ├─ YES, and r/NBA broadly agrees ───────────────► consensus_take
   ├─ YES, and r/NBA would argue with it ──────────► hot_take
   └─ NO claim survives stripping the emotion ─────► reaction
```

**Order matters.** A contrarian comment with real numbers is `stat_backed`, not `hot_take`. Evidence outranks alignment.

---

## The four tests

**Load-bearing test** (`stat_backed` vs. everything else)
Delete the number. Is the argument weaker? → `stat_backed`. Is it the identical assertion with identical force? → decorative, fall through to step 2.
*Tell:* load-bearing stats carry scope — "since January," "in 28 games," "27th in the league." Decorative stats are bare.

**Reply test** (`consensus_take` vs. `hot_take`)
Imagine a reply saying "yeah, obviously." Does it read as normal, or as sarcastic?
Normal → `consensus_take`. Sarcastic → `hot_take`.

**Reddit-not-media rule** (`consensus_take` vs. `hot_take`)
Consensus means **r/NBA** consensus. When r/NBA disagrees with national NBA media, r/NBA wins. You will violate this by reflex — check yourself on any take that feels "bold on TV."

**Strip test** (`reaction` vs. everything else)
Remove caps, emoji, exclamations, "I don't care." Does a disagreeable claim survive? Label by the claim. Nothing survives? → `reaction`.
*Corollary:* "MVP! MVP!" and "he's him" are chants, not claims → `reaction`.

---

## Skip these — don't label, don't collect

Off-topic content: meme image replies, "what's the stream," flair checks, mod notices, comments that are only a link.
**Keep a tally of how many you skip** — it goes in the README as evidence the taxonomy is exhaustive.

---

## While you label

- **Read every comment.** Do not bulk-skim. Noisy labels produce a noisy model and there is no recovering from it downstream.
- **Hesitated more than a few seconds?** Log it in `notes`: which two labels, and which rule you applied.
- **Inventing a new rule?** Stop. Write it into planning.md §3, then go back and re-check the earlier rows that rule touches.
- **Watch the running counts.** Target ~50 per label. Hard cap: no label above 70.
- **`stat_backed` is the scarce one.** If you're behind on it, switch to post-game threads or search r/NBA for "per 100," "TS%," "on/off," "eFG," "since the All-Star break."

---

## Running tally

Update as you go:

| Label | Target | Current |
|---|---|---|
| `stat_backed` | ~50 | |
| `consensus_take` | ~50 | |
| `hot_take` | ~50 | |
| `reaction` | ~50 | |
| **Total** | **200** | |
| *(skipped as off-topic)* | — | |
