# Label Stress Test

Executed per [planning.md §7a](planning.md), **before** annotation began.

**Method:** Claude was given the four label definitions and the ordered decision procedure from planning.md §2, and asked to generate 10 r/NBA-style comments engineered to sit exactly on the label boundaries — 5 on `consensus_take`/`hot_take`, 3 on `stat_backed`/`hot_take` (decorative-stat cases), 2 on `reaction`/`consensus_take` (embedded-claim cases).

**How to use this file:** label all 10 yourself using *only* the written rules — no improvising. Then check against the answer key below. Any comment you can't resolve from the rules alone is a hole in the taxonomy; fix the definition now, not at example 130.

**These comments are synthetic and never enter the dataset.** They test the definitions, not the model.

---

## The 10 comments

Cover the answer key before you start.

| # | Comment | Your label |
|---|---|---|
| 1 | "Honestly the MVP race is over. It hasn't been close since January." | |
| 2 | "Shai is averaging 32 a game and people still find reasons to say he's not a top-3 player. Wild." | |
| 3 | "The Celtics' whole identity is chucking threes and hoping. That works until it doesn't and everyone knows it." | |
| 4 | "Load management has genuinely ruined the regular season product and the league refuses to admit it." | |
| 5 | "Giannis has zero counters when you build a wall. He's shot 21% from three over his career, that's not a real player in the playoffs." | |
| 6 | "NOOOO WAY. no way he just did that. im actually shaking" | |
| 7 | "Draymond is the most overrated defender of the last decade, it's all reputation at this point." | |
| 8 | "GOAT. 🐐 nobody is touching this man, not now not ever" | |
| 9 | "Their bench is the problem, not the starters — the starting five is +7.1 per 100 and the second unit is -9.4. That's the whole season in two numbers." | |
| 10 | "Tatum is a 'first option on a title team' the same way I'm a 'first option' in my rec league. It's a title people gave him, not one he earned." | |

---

## Answer key + what each one tests

<details>
<summary>Expand after labeling</summary>

| # | Label | Rule applied | What it tests |
|---|---|---|---|
| 1 | `consensus_take` | Reply test — "yeah obviously" reads as normal | "Since January" *sounds* like a dated stat reference but contains no quantity. Tests whether you're matching on stat-flavored vocabulary instead of actual numbers. |
| 2 | `stat_backed` | Load-bearing test — delete "32 a game" and the top-3 argument loses its support | Borderline. One bare stat, but it's the actual premise of the claim rather than decoration. Contrast with #5. |
| 3 | `consensus_take` | Reply test; "everyone knows it" is an explicit consensus appeal | Negative sentiment about a good team. Tests whether you're labeling by sentiment instead of alignment. |
| 4 | `consensus_take` | Reddit-not-media rule | Reads as a spicy sports-talk take, but it's orthodox on r/NBA. The trap: labeling `hot_take` because it feels bold on TV. |
| 5 | `hot_take` | Load-bearing test fails — delete "21% from three" and the assertion is identical with identical force | The decorative-stat case. The number is real, cherry-picked, and doing rhetorical rather than argumentative work. |
| 6 | `reaction` | Strip test — nothing survives | Easy anchor. |
| 7 | `hot_take` | Reply test — "yeah obviously" reads as sarcastic | Straightforward contrarian assertion, no evidence. |
| 8 | `reaction` | Strip-test corollary — chants aren't claims | "Nobody is touching this man" looks like a claim but is hype framing. Tests the chant rule. |
| 9 | `stat_backed` | Load-bearing test — the two numbers *are* the argument | Easy anchor at the other end. Note the scope markers ("per 100"), the tell for load-bearing stats. |
| 10 | `hot_take` | Reply test; no number anywhere | Analogy and rhetorical structure make it *feel* like an argument. Tests whether structure is fooling you into `stat_backed` or `consensus_take` when no evidence is present. |

</details>

---

## Result

`<!-- FILL after you've done it: How many of the 10 did you resolve cleanly from the rules alone? Which ones did you disagree with the key on — and was that because the key was wrong or because the rule was underspecified? What did you change in planning.md §2 or §3 as a result? If nothing needed changing, say so and say which cases you tested, since "the definitions held" is only meaningful if you name what they held against. -->`

**Pairs most at risk, based on this exercise:** #2 vs. #5 is the sharpest test in the set — both are a single stat attached to a player-evaluation claim, and only the load-bearing test separates them. If you found yourself labeling those two the same way, that boundary needs tightening before you annotate 200 examples.
