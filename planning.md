# TakeMeter — Planning Document

**Project:** A fine-tuned text classifier that sorts r/NBA comments by *what kind of support a take offers*.
**Written:** before any data collection or annotation.
**Status:** design locked; collection not yet started.

---

## 1. Community

**Chosen community: r/NBA** (~16M subscribers), specifically its comment sections — game threads, post-game threads, the Daily Discussion Thread, and comments on news and `[Highlight]` posts.

r/NBA is a good fit for a discourse-quality classifier for three reasons.

First, **the volume and variance are both enormous.** A single post-game thread produces thousands of comments in an hour, and they range from a one-word scream to a 300-word breakdown of pick-and-roll coverage with per-100 numbers attached. Most communities are either uniformly casual or uniformly analytical; r/NBA is genuinely both, simultaneously, in the same thread. That variance is exactly what a classifier needs — if 90% of a community's posts looked alike there'd be nothing to learn.

Second, **the distinction I want to measure is one the community already polices itself.** "Source?" and "that's a crazy take" and "stat-padder" are native r/NBA vocabulary. Users explicitly reward comments that bring receipts and explicitly dogpile comments that assert without them. I am not imposing an outside notion of quality; I am trying to model a judgment r/NBA already makes constantly in its voting behavior.

Third, **it's fully public.** No authentication, no private channels, no scraping of anything gated. Every example is a publicly visible comment on a public subreddit.

**Why this task is interesting rather than trivial:** the hard part isn't separating a stat-heavy essay from "LETS GOOO." That's easy, and a keyword matcher would do it. The hard part is separating two comments that are *formally identical* — same length, same confidence, same absence of evidence — where one is a take r/NBA broadly agrees with and one is a take r/NBA would argue with. That distinction lives in world knowledge about what the community currently believes, not in surface features of the text. I expect that to be where the model breaks, and I think finding out exactly how it breaks is the most interesting result this project can produce.

---

## 2. Labels

Four labels, ordered by what kind of support the comment offers for what it claims.

### `stat_backed`

**Definition:** The comment makes an evaluative claim and supports it with at least one specific, checkable quantity — a stat line, a percentage, a rank, a split, a record, or a dated comparison — and that number does real work in the argument rather than sitting there for decoration.

*Example 1:* "People saying he fell off should look at the post-All-Star split: 27.4 / 8.1 / 6.3 on 61% TS in 28 games. That's a better stretch than his MVP year."

*Example 2:* "The Pacers defense isn't 'fixed,' they just played the three worst offenses in the league back to back. 118.9 defensive rating on the season, still 27th."

*Uncertain case:* "LeBron is overrated, his playoff record against 1-seeds is under .500." One real number, but it's cherry-picked and the framing is accusatory — see the decorative-stat rule in §3.

### `consensus_take

**Definition:** The comment asserts an evaluative claim with no statistical support, and the claim is one r/NBA broadly agrees with — the kind of comment that draws "yeah, obviously" replies and upvotes rather than argument.

*Example 1:* "Jokic is the best passing big man of all time and it isn't particularly close."

*Example 2:* "Refs have completely lost control of how they call the perimeter. It's different every quarter."

*Uncertain case:* "Embiid's availability is a real part of evaluating him, not an excuse." This was a hot take three years ago and is consensus now — see the drifting-consensus rule in §3.

### `hot_take`

**Definition:** The comment asserts an evaluative claim with no real statistical support, and the claim runs against r/NBA consensus — it's contrarian, provocative, or framed to get a rise, and would predictably draw arguments or downvotes.

*Example 1:* "Jokic is a stat-padder who can't defend. Most overrated MVP winner of the modern era."

*Example 2:* "Wemby is going to be a good player but people are going to feel very stupid about the 'best defender ever' stuff in five years."

*Uncertain case:* "Curry is the most overrated player in league history." Contrarian, obviously — but it's *so* familiar a bait comment that some readers treat it as noise rather than a claim. See §3.

### `reaction`

**Definition:** The comment expresses an in-the-moment emotional response — shock, joy, despair, a joke, a meme — and makes no evaluative claim that survives stripping the emotion away.

*Example 1:* "BRO WHAT WAS THAT 😭😭 no shot he actually hit that"

*Example 2:* "im so tired of this franchise. every single year. every single year man."

*Uncertain case:* "WHAT A PASS. best passer alive, I don't care." Emotional register, but there's a claim buried in it — see the embedded-claim rule in §3.

### Mutual exclusivity

The labels are mutually exclusive by construction, because they are resolved by an ordered decision procedure rather than by picking whichever fits best:

1. **Does the comment cite a specific, checkable number that does argumentative work?** → `stat_backed`. Stop.
2. **Otherwise, does it assert an evaluative claim?**
   - Claim aligns with r/NBA consensus → `consensus_take`. Stop.
   - Claim runs against r/NBA consensus → `hot_take`. Stop.
3. **No evaluative claim survives** → `reaction`.

Because the rule is ordered, a contrarian comment that brings real numbers is `stat_backed`, not `hot_take` — evidence outranks alignment. This is a deliberate choice: the thing I most want the classifier to be able to find is "this person brought receipts," and I don't want that signal split across two labels based on whether the receipts support a popular conclusion.

### Exhaustiveness

Every r/NBA comment that is *about basketball* lands in one of these four. The residue is off-topic content — pure meme image replies, "what's the stream," flair-checking, moderator notices. I will exclude that at collection time rather than create a catch-all bucket, and I will record how many comments I skipped for this reason so the exclusion is visible rather than hidden. I expect it to be well under 10% of what I read.

---

## 3. Hard edge cases

Four, in descending order of how much trouble I expect them to cause.

### 3a. The decorative stat — `stat_backed` vs. `hot_take`

**The case:** A comment drops one number into what is otherwise a bare assertion. "LeBron is overrated, his playoff record against 1-seeds is under .500."

**Why it's hard:** It has a number. The number is even probably true. But it was selected *because* it supports a predetermined conclusion, and it isn't part of any reasoning — remove the number and the comment says exactly the same thing with the same confidence.

**Decision rule:** Apply the *load-bearing test*. Delete the number from the comment. If what remains is a weaker or incomplete argument, the number was load-bearing → `stat_backed`. If what remains is the identical assertion with the same force, the number was decorative → fall through to step 2 (`hot_take` or `consensus_take`). By this rule the LeBron example is `hot_take`.

**Secondary tell:** load-bearing stats usually come with scope — a date range, a sample size, a comparison group ("since January," "in 28 games," "27th in the league"). Decorative stats are usually bare.

### 3b. Drifting consensus — `consensus_take` vs. `hot_take`

**The case:** A take that used to be contrarian and has become conventional wisdom, or vice versa. "Embiid's availability is part of evaluating him" was a hot take in 2022 and is consensus now.

**Why it's hard:** The label depends on community belief at a moment in time, and community belief moves. This is the single biggest threat to the whole taxonomy, because it means the same sentence has different correct labels in different years.

**Decision rule:** Two parts. (1) **Freeze the reference frame** — I label relative to r/NBA consensus *as of the collection window*, and I will collect all 200 examples from a narrow window (see §4) so the frame doesn't drift inside my own dataset. (2) **Use the reply test as the operational check** — would a reply saying "yeah, obviously" read as normal, or would it read as sarcastic? Normal → `consensus_take`. Sarcastic → `hot_take`. Where I have the actual thread available, I can sanity-check against the real replies and score, though I will not treat score as decisive, since vote counts track timing and thread position as much as content.

### 3c. Reddit-consensus vs. media-consensus

**The case:** r/NBA's consensus is frequently *itself* contrarian relative to national NBA media. "Jokic has been better than the MVP voting suggests" is a spicy take on television and completely orthodox on r/NBA. Similarly, r/NBA has durable in-group positions — anti-ref, anti-Skip-Bayless-discourse, pro-advanced-stats — that would read as edgy elsewhere.

**Why it's hard:** It's easy to slip into labeling by "is this a bold claim in general" rather than "is this a bold claim *here*," which would make my annotations incoherent.

**Decision rule:** `consensus_take` means **r/NBA consensus, explicitly not national-media consensus**. When the two disagree, r/NBA wins. I'm writing this rule down because I expect to violate it by reflex otherwise, and a reflex violation partway through annotation is exactly the kind of inconsistency that produces a model that learns nothing.

### 3d. The embedded claim — `reaction` vs. everything else

**The case:** "WHAT A PASS. best passer alive, I don't care."

**Decision rule:** Strip the emotional framing — the caps, the emoji, the exclamations, the "I don't care." If a claim someone could disagree with survives, label by the claim. If nothing survives, it's `reaction`. Here "best passer alive" survives and is orthodox on r/NBA → `consensus_take`. By contrast, "WHAT A PASS 😭" leaves nothing → `reaction`.

**Corollary for hype:** "MVP! MVP!" and "he's him" are `reaction`, not `consensus_take` — they're chants, not claims, and treating them as claims would flood `consensus_take` with noise.

### How I'll handle ambiguity during annotation

Every comment where I hesitate for more than a few seconds gets logged in the `notes` column with (a) the two labels I was torn between and (b) the rule I applied. If I find myself inventing a *new* rule rather than applying an existing one, I stop, write the rule into this document, and re-check the examples I've already labeled that the new rule touches. The three cases that gave me the most trouble in practice get written up in the README, separately from the anticipated cases above.

---

## 4. Data collection plan

**Source:** r/NBA, public comments only. Different thread types over-produce different labels, so I sample them deliberately rather than uniformly:

| Thread type | Over-produces | Why I'm sampling it |
|---|---|---|
| Game threads | `reaction` | Live, emotional, fast — the reaction motherlode |
| Post-game threads | `stat_backed`, `consensus_take` | People have box scores open and are arguing about what happened |
| Daily Discussion Thread | `consensus_take`, `hot_take` | Low-stakes opinion trading, no specific game anchoring it |
| Comments on news / `[Highlight]` posts | `hot_take` | Player-evaluation arguments, where contrarian takes live |

### Timing problem, and the revision it forced

The plan above assumed an in-season collection window. **It isn't one.** The 2026–27 preseason doesn't tip until October 3 and opening night is October 20, so at the time of collection r/NBA has no game threads and no post-game threads at all — the two sources the table assigns to `reaction` and `stat_backed`. Discovering this before collecting rather than after is the entire reason for writing a plan down first.

Two revisions, each scoped to the label it affects:

**`consensus_take`, `hot_take`, `stat_backed` — collect from the current offseason window.** This turns out to be a strength rather than a compromise. Late-September r/NBA is dominated by media-day coverage, roster-move arguments, and season-preview power rankings, which is *more* argument-dense than a game thread, not less. Offseason discourse is almost entirely player evaluation with nothing happening on the court to point at, which is precisely the environment that produces bare assertions (`hot_take`), conventional wisdom (`consensus_take`), and the "actually, here are his splits" rebuttals (`stat_backed`). Ranking threads in particular attract statistically literate arguing.

**`reaction` — allow a second, earlier window, and here is why that does not break §3b.** The frozen-window rule exists for exactly one purpose: to stabilize the `consensus_take` / `hot_take` boundary, which depends on what r/NBA believes at a moment in time. `reaction` has no claim in it by definition — it fails the strip test — so *there is no consensus for it to be measured against* and no drift for the freeze to protect it from. Reaction comments are therefore window-independent, and I can source them from a narrow archived window (a playoff or Finals series from the season just completed) without introducing the inconsistency §3b guards against.

This is a real exception to a rule I wrote three sections ago, so I'm stating the limit precisely: **the exception covers `reaction` only.** Any comment from the archived window that turns out to carry a claim — which happens, since post-game threads mix screaming with analysis — gets discarded rather than labeled, because labeling it would mean judging last season's consensus against this season's frame. I'll flag those rows as `archived` in `source_thread_type` so the split is auditable afterward.

**Method:** scripted collection of raw comments via [`tools/collect_reddit.py`](tools/collect_reddit.py), then hand-labeling every row. The assignment permits a scraping tool, and the tradeoff it warns about doesn't apply here: the script only removes the copy-paste, not the read. Labels come out of the scraper empty on purpose. I still read all 200 comments one at a time against the rules in §2 and §3, which is the step that actually matters, and the script buys me more time to do it.

**Target distribution:** ~50 per label (25% each), with a hard rule that no label exceeds 70 of 200 (35%).

**Sampling correction:** I will *not* sample comments uniformly at random. Uniform sampling of r/NBA would return something like 70% `reaction` and under 5% `stat_backed`, which would produce a model that predicts `reaction` and looks 70% accurate while having learned nothing. Instead I stratify: I collect from each thread type until that type's dominant label hits its quota, then switch. I'll note this in the README, because it means **my test-set accuracy is not an estimate of accuracy on live r/NBA traffic** — it's accuracy on a balanced sample. That's the right trade for learning the boundaries, but it's a real limitation and I'd rather state it than let a grader assume otherwise.

**If a label is underrepresented after 200:** `stat_backed` is the one at risk, since it's genuinely rare. Escalation plan, in order:
1. Targeted search within r/NBA for comments containing stat vocabulary — "per 100," "TS%," "since the All-Star break," "on/off," "eFG."
2. Mine the comment sections of r/NBA OC (original content) stat posts, which attract statistically literate repliers.
3. If still short, collect beyond 200 total rather than rebalance by deleting from other labels — throwing away real labeled data to fix a ratio is worse than a slightly larger dataset.

**File format:** one CSV, `data/takemeter_labeled.csv`, columns `text`, `label`, `notes`, `source_thread_type`. Not pre-split — the notebook does the 70/15/15 split. The extra `source_thread_type` column is for my own analysis; I want to be able to check afterward whether the model is secretly learning "this came from a game thread" instead of learning the label.

**Known limitation I'm accepting up front:** 200 examples with a 15% test split gives a **30-comment test set — about 7 or 8 per class.** Per-class precision and recall on 7 examples move by roughly 0.14 per single example. I'm proceeding at 200 because that's the assignment's bar and annotation quality matters more than volume, but I will report per-class numbers as *directional* rather than precise, and I will lean on the confusion matrix and on reading the actual errors rather than on the third decimal place of an F1 score.

---

## 5. Evaluation metrics

**Accuracy** — reported because it's the headline number and the only one directly comparable to the zero-shot baseline at a glance. It is not sufficient on its own here, for a specific reason: with four classes and any residual imbalance, a degenerate model that always predicts the largest class scores around 30–35%, which is *above* the 25% random-chance floor and can be mistaken for real learning. Accuracy alone can't tell those apart.

**Macro-averaged F1** — my primary metric. Macro-F1 averages per-class F1 with equal weight regardless of class size, so a model that nails `reaction` and whiffs on `stat_backed` gets punished rather than carried. Since the whole point of the project is the *boundaries between* classes, I want the metric that refuses to let one easy class subsidize a hard one.

**Per-class precision, recall, and F1** — because the four labels are not equally important and not equally hard, and one aggregate number hides both facts. Two specific things I'm watching:

- **`stat_backed` precision** matters more than its recall. The realistic downstream use of this classifier is something like a "receipts" filter — surfacing the comments in a 4,000-comment thread that actually brought numbers. For that use, a false positive (promoting an empty take as evidence-backed) is worse than a miss, because misses just leave a good comment buried where it already was, while false positives actively corrupt the filter's value.
- **`reaction` recall** is the sanity check on degeneracy. If `reaction` recall is near 1.0 while everything else sags, the model has learned "predict the easy class" and the aggregate numbers are lying.

**Confusion matrix** — reported as a markdown table, not only as an image. I care about one cell pair above all others: **`consensus_take` ↔ `hot_take`**. Those two labels are formally identical in every surface feature (length, confidence, absence of numbers) and differ only in whether the claim matches what r/NBA currently believes. That is world knowledge, not text structure. My honest prediction is that this is where most errors land, and the *direction* of the confusion will be informative — if `hot_take` gets pulled toward `consensus_take`, the model has learned "unsupported opinion" as a single undifferentiated category, which would mean my two-label distinction collapsed into one from the model's point of view.

**Baseline comparison on the identical test set** — zero-shot `meta-llama/llama-4-scout-17b-16e-instruct` via Groq, prompted with these exact label definitions, scored on the same 30 test comments with the same metrics. I have a real expectation here worth recording in advance so I can't retrofit it: **I expect the zero-shot LLM to beat DistilBERT on `consensus_take` vs. `hot_take`,** because that boundary requires knowing what NBA fans think, which a 17B model trained on the internet has and a 66M-parameter DistilBERT fine-tuned on 140 examples does not. I expect DistilBERT to win on `reaction` and possibly on `stat_backed`, where the signal is lexical and learnable from few examples. If DistilBERT beats the baseline across the board, my first move is to check for test-set leakage rather than to celebrate.

---

## 6. Definition of success

Three tiers, specified now so the result can't be graded against a moving target.

**Tier 1 — the model learned something (minimum bar).**
- Accuracy ≥ 0.50 (vs. 0.25 random chance on four classes)
- Macro-F1 ≥ 0.45
- No class with F1 = 0 — every label was learnable at all
- Beats the zero-shot baseline on macro-F1

Below this tier I'd conclude that 200 examples is too few for a four-way subjective task, which is itself a legitimate finding to report rather than a failure to hide.

**Tier 2 — genuinely useful (the target).**
- Accuracy ≥ 0.70
- Macro-F1 ≥ 0.65
- Every per-class F1 ≥ 0.55
- `consensus_take` ↔ `hot_take` confusion accounts for less than half the total errors

**Tier 3 — deployable in a real community tool (the stretch).**
The concrete deployment I have in mind is a "receipts" sidebar on a long r/NBA thread: automatically surface the comments that brought actual numbers. For that specific product, one metric dominates:
- **`stat_backed` precision ≥ 0.80** — at least four of every five comments the tool promotes as evidence-backed actually are. Below that the sidebar is noise and nobody trusts it.
- `stat_backed` recall ≥ 0.50 is acceptable — catching half the good comments in a thread nobody was reading anyway is still a large improvement over catching none.

**An explicit ceiling.** If accuracy comes in above 0.95, I will treat that as a red flag and not a triumph, and I'll check for test-set leakage, near-duplicate comments across the split, and labels that turned out to be separable on trivial surface cues — emoji density for `reaction`, digit presence for `stat_backed`. A four-way subjective discourse-quality judgment should not be 95% solvable from 140 training examples, and if it appears to be, the most likely explanation is that I accidentally built an easy task.

---

## 7. AI Tool Plan

### 7a. Label stress-testing — *executed before annotation; output in [`label-stress-test.md`](label-stress-test.md)*

**Tool:** Claude (Opus).

**What I gave it:** the four label definitions and the ordered decision procedure from §2, **plus all four edge-case descriptions from §3** — the decorative stat (§3a), drifting consensus (§3b), Reddit-vs-media consensus (§3c), and the embedded claim (§3d). The edge cases matter more than the definitions here: they tell the model where the boundaries actually are, so the comments it generates land on those boundaries instead of on whatever seams it would have guessed at.

**What I asked for:** 10 r/NBA-style comments engineered to sit exactly on the boundaries — five on `consensus_take` / `hot_take`, three on `stat_backed` / `hot_take` (decorative-stat cases), two on `reaction` / `consensus_take` (embedded-claim cases).

**How I'll use the output:** label all 10 myself using only the written rules, with no improvising. Any comment I can't resolve from the rules alone is a hole in the taxonomy, and I fix the definition *before* annotating 200 examples rather than discovering the hole at example 130 and having to re-label backward. The sharpest pair in the generated set is #2 vs. #5 — both attach a single stat to a player-evaluation claim, and only the load-bearing test from §3a separates them. If those two can't be told apart from the written rule, §3a needs rewriting before annotation starts.

**What I'm explicitly not doing:** these generated comments never enter the dataset. They're a test of the definitions, not training data. Synthetic r/NBA comments written by an LLM have a different texture from real ones and would teach the model the wrong distribution.

### 7b. Annotation assistance — *decided: no pre-labeling*

I considered having an LLM pre-label a batch and reviewing its output. **I'm declining, deliberately, for the `consensus_take` / `hot_take` boundary specifically.** That boundary is the entire intellectual content of this project, and it's a judgment about community norms that I want to be *mine*, consistently applied. An LLM's pre-label would anchor me — reviewing a suggested label is psychologically a different task from making one, and I'd accept plausible-looking wrong labels at a rate I couldn't measure. Given that the baseline comparison is literally "can a zero-shot LLM do this," letting that same class of model seed my ground truth would contaminate the comparison in a way that's hard to reason about.

I will label all 200 by hand.

**Tracking mechanism, specified in advance in case I reverse this.** If I do end up pre-labeling any batch — the one case I'd consider is using an LLM purely to pre-filter obvious `reaction` comments, where the judgment is cheap and the anchoring risk is low — the disclosure trail is already designed:

- **Tool:** Claude (Opus), the same model used for stress-testing, so the disclosure names one tool rather than a vague "an LLM."
- **Row-level tracking:** add a `pre_labeled` column to the CSV with values `no` (default, hand-labeled from scratch), `accepted` (LLM proposed a label and I agreed), or `overridden` (LLM proposed a label and I changed it). A plain flag isn't enough — the accepted/overridden split is what lets me *measure* the anchoring risk instead of just asserting it's low. If my override rate on pre-labeled rows is far below my hesitation rate on hand-labeled rows, that's evidence I was rubber-stamping, and it's visible in the data rather than hidden.
- **Reporting:** the counts for each value go in the README's AI usage section, and I update §7b and the §8 revision log before labeling a single pre-labeled row.

Because the decision is *no*, the CSV ships with four columns (`text`, `label`, `notes`, `source_thread_type`) and no `pre_labeled` column. Its absence is itself the disclosure: every row was labeled by hand.

### 7c. Failure analysis — *will do, after evaluation*

**What:** Export every misclassified test example with its true label, predicted label, and confidence. Give the full list to Claude and ask it to propose systematic patterns — not to explain individual errors.

**Specific hypotheses I'll ask it to test, stated in advance so I'm not just accepting whatever it says:**
- Are errors concentrated in short comments (under ~15 words), where there's simply not enough text to carry the signal?
- Is `consensus_take` ↔ `hot_take` confusion directional — does one label absorb the other, and which way?
- Do errors correlate with specific players? A plausible failure mode is that the model learns "comments about Jokic are positive → `consensus_take`" as a topic shortcut instead of learning the actual claim-alignment rule.
- Does the presence of any digit push a prediction toward `stat_backed` regardless of whether the number is load-bearing? That would mean the model learned §3a's surface tell and skipped §3a's actual rule.

**How I'll verify rather than just repeat it:** for any pattern Claude proposes, I re-read the examples myself and check the pattern against the *correctly* classified examples too. A pattern that's equally present in the successes isn't an explanation of the failures — this is the specific way this kind of analysis goes wrong, and it's easy to miss because a confident narrative about six errors always sounds right. I'll also use the `source_thread_type` column to check whether errors cluster by collection source, which would indicate I introduced a sampling artifact. Patterns I test and reject get written into the README alongside the ones I keep, since a discarded hypothesis is evidence too.

---

## 8. Revision log

| Date | Change |
|---|---|
| *(before collection)* | Initial version — taxonomy, edge-case rules, collection plan, metrics, success tiers, AI tool plan. |
| *(before collection)* | §7a: ran the label stress test, output in [`label-stress-test.md`](label-stress-test.md); recorded that the §3 edge cases were part of the prompt, not just the §2 definitions. §7b: specified the `pre_labeled` tracking column in advance, in case the no-pre-labeling decision gets reversed. |
| *(before collection)* | §4: the original plan assumed an in-season window, but collection falls before the Oct 3 preseason, so game and post-game threads don't exist yet. Re-sourced `consensus_take` / `hot_take` / `stat_backed` to the current offseason window, and carved a `reaction`-only exception to the §3b window freeze — justified because `reaction` carries no claim and so has no consensus to drift against. Switched from manual copy-paste to scripted collection of unlabeled comments ([`tools/collect_reddit.py`](tools/collect_reddit.py)); hand-labeling is unchanged. |

*(Per the assignment, this document gets updated before starting any stretch feature. Log those updates here.)*
