# TakeMeter

A fine-tuned text classifier that sorts r/NBA comments by **what kind of support a take offers** — does it bring numbers, echo what the sub already believes, swing against the grain, or just scream?

> **Demo video:** `<!-- FILL: paste link here (3–5 min) -->`
> **Labeled dataset:** [`data/takemeter_labeled.csv`](data/takemeter_labeled.csv)
> **Design doc:** [`planning.md`](planning.md) — written before data collection
> **Colab notebook:** `<!-- FILL: paste shareable Colab link -->`

---

## Community

**r/NBA** (~16M subscribers) — comment sections from game threads, post-game threads, the Daily Discussion Thread, and comments on news and `[Highlight]` posts. Public content only.

I picked it for three reasons. **The variance is enormous**: one post-game thread produces both a one-word scream and a 300-word pick-and-roll breakdown with per-100 numbers attached, in the same hour. **The community already polices this distinction itself** — "source?", "that's a crazy take", and "stat-padder" are native r/NBA vocabulary, so I'm modeling a judgment the sub already makes rather than imposing an outside notion of quality. And **it's fully public**, no authentication or gated content anywhere in the dataset.

The task isn't trivial, and the reason is worth stating up front: separating a stat-heavy essay from "LETS GOOO" is easy, and a keyword matcher would do it. The hard part is separating two comments that are *formally identical* — same length, same confidence, same absence of numbers — where one is a take r/NBA agrees with and one is a take r/NBA would argue with. That distinction lives in world knowledge about community belief, not in surface features of the text.

---

## Label taxonomy

Four labels, ordered by what kind of support the comment offers.

### `stat_backed`
Makes an evaluative claim and supports it with at least one specific, checkable quantity — a stat line, percentage, rank, split, record, or dated comparison — where the number does real argumentative work rather than sitting there for decoration.

1. `<!-- FILL: real collected example -->`
2. `<!-- FILL: real collected example -->`

### `consensus_take`
Asserts an evaluative claim with no statistical support, where the claim is one r/NBA broadly agrees with — the kind of comment that draws "yeah, obviously" replies rather than argument.

1. `<!-- FILL: real collected example -->`
2. `<!-- FILL: real collected example -->`

### `hot_take`
Asserts an evaluative claim with no real statistical support, where the claim runs against r/NBA consensus — contrarian, provocative, or framed to get a rise.

1. `<!-- FILL: real collected example -->`
2. `<!-- FILL: real collected example -->`

### `reaction`
Expresses an in-the-moment emotional response — shock, joy, despair, a joke, a meme — and makes no evaluative claim that survives stripping the emotion away.

1. `<!-- FILL: real collected example -->`
2. `<!-- FILL: real collected example -->`

### How the labels stay mutually exclusive

They're resolved by an **ordered decision procedure**, not by picking whichever fits best:

1. Specific checkable number doing argumentative work? → `stat_backed`
2. Otherwise, asserts an evaluative claim? → `consensus_take` if r/NBA agrees, `hot_take` if it wouldn't
3. No claim survives stripping the emotion → `reaction`

Order matters: a contrarian comment that brings real numbers is `stat_backed`, not `hot_take`. Evidence outranks alignment, deliberately — the signal I most want findable is "this person brought receipts," and splitting it across two labels based on whether the receipts support a popular conclusion would destroy that.

Three supporting tests do the actual work at the boundaries:

- **Load-bearing test** — delete the number. If the argument gets weaker, it was load-bearing (`stat_backed`). If the identical assertion remains with identical force, the stat was decorative and the comment falls through to step 2.
- **Reply test** — imagine a reply saying "yeah, obviously." Reads as normal → `consensus_take`. Reads as sarcastic → `hot_take`.
- **Strip test** — remove caps, emoji, exclamations. If a disagreeable claim survives, label by the claim; if nothing survives, `reaction`. ("MVP! MVP!" is a chant, not a claim.)

**Exhaustiveness:** off-topic content (meme replies, "what's the stream," flair checks) is excluded at collection time rather than bucketed into a catch-all. I skipped `<!-- FILL: N -->` comments for this reason out of `<!-- FILL: N -->` read, about `<!-- FILL: N -->`%.

---

## Data collection and labeling

**Source:** r/NBA, public comments, collected within a single narrow in-season window so that "r/NBA consensus" means one fixed thing across the whole dataset. Four thread types, each chosen because it over-produces a different label:

| Thread type | Over-produces | Why sampled |
|---|---|---|
| Game threads | `reaction` | Live and emotional |
| Post-game threads | `stat_backed`, `consensus_take` | Box scores are open, people are arguing about what happened |
| Daily Discussion Thread | `consensus_take`, `hot_take` | Low-stakes opinion trading with no game anchoring it |
| News / `[Highlight]` comments | `hot_take` | Player-evaluation arguments, where contrarian takes live |

**Collection window: the 2025 NBA playoffs, April 19 – June 25, 2025**, ending with Thunder–Pacers Game 7 on June 22. The original plan assumed a live in-season window, but collection happened in late September, before the Oct 3 preseason — r/NBA had no game or post-game threads at all. Rather than patch around that, the whole window moved into the archive. That turned out cleaner: one frozen window means one consensus frame for every label, which is exactly what the drifting-consensus rule in [planning.md §3b](planning.md) asks for, and the archive still contains the full range of thread types the table above depends on.

**Source:** the [Arctic Shift](https://arctic-shift.photon-reddit.com) public API rather than reddit.com directly, via [`tools/collect_reddit.py`](tools/collect_reddit.py). Arctic Shift serves historical Reddit data, which is what makes an archived window practical.

**Sampling artifact worth stating plainly.** `stat_backed` is rare enough that date-window sampling alone barely produced it, so those rows were pulled with full-text queries for stat vocabulary (`averaged`, `shooting`). That means the class was *selected for containing stat words*, which inflates the link between stat vocabulary and the label beyond what natural r/NBA traffic would show. If the model ends up keying on digits and the word "averaged," this collection method is part of the cause, not purely a modeling failure. The `source_thread_type` column marks query-sourced rows (`stat_search`, `take_search`) separately from date-window rows (`finals_g7_live`, `finals_g1_live`, `finals_g7_aftermath`, `playoffs_general`) so the effect can be measured instead of guessed at.

> ### ⚠️ Labels in the committed CSV are machine-proposed and awaiting review
>
> All 204 rows were assembled *and labeled* in one pass by Claude (Opus), and every row is marked `pre_labeled=proposed`. **No human review pass has happened yet, and the dataset should not be trained on until it has.** Beyond the fact that annotation is the graded work here, there's a methodological reason: the `consensus_take` / `hot_take` boundary is defined as alignment with what r/NBA believed at the time, and an LLM's read on that is the *same class of judgment the zero-shot baseline is being tested on*. Machine ground truth plus a machine baseline measures agreement between two models as much as it measures task difficulty. Review flips each row to `accepted` or `overridden`; the split between those two is then reportable evidence about how much the proposals were actually scrutinized. Full reasoning in [planning.md §7b](planning.md).

**Sampling is stratified, not random — and this matters for reading the results.** Uniform sampling of r/NBA would return roughly 70% `reaction` and under 5% `stat_backed`, producing a model that predicts `reaction` constantly and looks 70% accurate while having learned nothing. So I collected from each thread type until its dominant label hit quota, then switched. The consequence: **test-set accuracy here is not an estimate of accuracy on live r/NBA traffic.** It's accuracy on a deliberately balanced sample. That's the right trade for learning boundaries, but it's a real limitation.

### Label distribution

*(Machine-proposed — will shift after the human review pass.)*

| Label | Count | Share | Mean words |
|---|---|---|---|
| `stat_backed` | 48 | 21.1% | 43.4 |
| `consensus_take` | 64 | 28.2% | 36.5 |
| `hot_take` | 56 | 24.7% | 29.9 |
| `reaction` | 59 | 26.0% | 11.4 |
| **Total** | **227** | 100% | — |

Every class sits between 21% and 28%. No label approaches the 70-row cap from planning.md, and the validator reports zero near-duplicates — which matters, because a duplicate straddling the 70/15/15 split would inflate test accuracy invisibly.

`stat_backed` is the scarce class on r/NBA and needed two extra rounds of stat-vocabulary queries (`rebounds`, `assists`) to clear the 20% floor. It remains the smallest class, so its per-class numbers rest on the fewest test examples of any label.

**The length gap is a live leakage risk.** `reaction` averages 11 words; `stat_backed` averages 43. A model can get a long way on length alone without ever learning the load-bearing test, so this gets checked explicitly in the reflection section rather than assumed away.

**Test-set size, stated plainly.** 227 examples with a 15% test split gives roughly 34 test comments — about 8 per class. A single example moves a per-class F1 by roughly 0.12. Per-class numbers below are directional; the confusion matrix and the actual error text carry more weight than any decimal place.

### Three examples that were genuinely hard to label

> These are cases I actually hit during annotation. The edge cases I *anticipated* before collecting are in [planning.md §3](planning.md) — separate thing.

**1.** `<!-- FILL: the comment text -->`
*Torn between:* `<!-- FILL -->` and `<!-- FILL -->`.
*Why it was hard:* `<!-- FILL -->`
*Decided:* `<!-- FILL -->`, because `<!-- FILL: which rule you applied -->`

**2.** `<!-- FILL: the comment text -->`
*Torn between:* `<!-- FILL -->` and `<!-- FILL -->`.
*Why it was hard:* `<!-- FILL -->`
*Decided:* `<!-- FILL -->`, because `<!-- FILL -->`

**3.** `<!-- FILL: the comment text -->`
*Torn between:* `<!-- FILL -->` and `<!-- FILL -->`.
*Why it was hard:* `<!-- FILL -->`
*Decided:* `<!-- FILL -->`, because `<!-- FILL -->`

---

## Fine-tuning approach

**Base model:** `distilbert-base-uncased` (66M parameters) — a distilled BERT that keeps most of BERT-base's language understanding at roughly 40% of the size, which makes it trainable on a free T4 in minutes.

**Setup:** `<!-- FILL: epochs, learning rate, batch size, max sequence length -->`. Split 70/15/15 into train/validation/test, handled by the notebook, stratified by label.

**Key hyperparameter decision:** `<!-- FILL -->`

> *Guidance for filling this in — pick the one you actually wrestled with and say what you observed, not just what you set. The most likely candidate is **epochs**: 3 is the notebook default, but 140 training examples is tiny, and DistilBERT will typically overfit within a few epochs. If you watched validation loss turn upward while training loss kept dropping, say at which epoch and what you did about it. Second most likely is **learning rate**: 2e-5 is standard for BERT fine-tuning; if you tried 5e-5 or 3e-5 and it destabilized, that's a real finding. Delete this blockquote when you write the real answer.*

**Class imbalance handling:** `<!-- FILL: did you weight the loss, or leave it? If your distribution came out near-even, say so and say you didn't need to. -->`

---

## Baseline

Zero-shot classification with `meta-llama/llama-4-scout-17b-16e-instruct` via Groq, no task-specific training, scored on the **identical test set** as the fine-tuned model.

**Prompt used:**

```text
<!-- FILL: paste your exact Groq prompt here, verbatim -->
```

**Collection method:** each test comment sent as a separate request, temperature `<!-- FILL -->`, model instructed to output only the bare label name. Unparseable responses: `<!-- FILL: N -->` of `<!-- FILL: N -->` (`<!-- FILL -->`%).

**Prediction I recorded before running anything** (in [planning.md §5](planning.md)): I expected the zero-shot LLM to *beat* DistilBERT on the `consensus_take` / `hot_take` boundary, because that boundary requires knowing what NBA fans believe — world knowledge a 17B internet-trained model has and a 66M DistilBERT fine-tuned on 140 examples does not. I expected DistilBERT to win on `reaction` and `stat_backed`, where the signal is lexical and learnable from few examples.

**What actually happened:** `<!-- FILL: was the prediction right? Say so plainly either way — a wrong prediction you recorded in advance is a better result than a vague one you didn't. -->`

---

## Evaluation report

### Headline comparison

| Metric | Zero-shot Llama-4-Scout | Fine-tuned DistilBERT |
|---|---|---|
| Accuracy | `<!-- FILL -->` | `<!-- FILL -->` |
| Macro-F1 | `<!-- FILL -->` | `<!-- FILL -->` |
| Weighted F1 | `<!-- FILL -->` | `<!-- FILL -->` |

Random-chance accuracy on four classes is 0.25. Always-predict-the-largest-class is roughly `<!-- FILL -->`.

**Test set is 30 comments — about 7 or 8 per class.** Every per-class number below moves by roughly 0.14 per single example. They are directional, not precise, and the confusion matrix plus the actual error text carry more weight here than any decimal place.

### Per-class metrics

**Zero-shot Llama-4-Scout**

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `stat_backed` | | | | |
| `consensus_take` | | | | |
| `hot_take` | | | | |
| `reaction` | | | | |

**Fine-tuned DistilBERT**

| Label | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| `stat_backed` | | | | |
| `consensus_take` | | | | |
| `hot_take` | | | | |
| `reaction` | | | | |

### Confusion matrix — fine-tuned DistilBERT

Rows are true labels, columns are predictions. Supplementary image: [`confusion_matrix.png`](confusion_matrix.png)

| True \ Predicted | `stat_backed` | `consensus_take` | `hot_take` | `reaction` |
|---|---|---|---|---|
| **`stat_backed`** | | | | |
| **`consensus_take`** | | | | |
| **`hot_take`** | | | | |
| **`reaction`** | | | | |

`<!-- FILL: 2–3 sentences reading the matrix. Which off-diagonal cell is largest? Is the confusion directional — does one label absorb the other, or do they trade errors symmetrically? Direction is the informative part. -->`

### Three wrong predictions, analyzed

**1.** `<!-- FILL: comment text -->`
True: `<!-- FILL -->` · Predicted: `<!-- FILL -->` · Confidence: `<!-- FILL -->`
`<!-- FILL: Why did it fail? Work through the four guiding questions — which boundary is this, why is that boundary hard, is it a labeling problem or a data problem, what would fix it. "The model got it wrong" is not analysis. -->`

**2.** `<!-- FILL: comment text -->`
True: `<!-- FILL -->` · Predicted: `<!-- FILL -->` · Confidence: `<!-- FILL -->`
`<!-- FILL -->`

**3.** `<!-- FILL: comment text -->`
True: `<!-- FILL -->` · Predicted: `<!-- FILL -->` · Confidence: `<!-- FILL -->`
`<!-- FILL -->`

### Systematic error patterns

`<!-- FILL: What holds across the errors rather than within one? Hypotheses worth testing, stated in planning.md §7c before I looked:
     - Are errors concentrated in short comments (<15 words)?
     - Is consensus_take ↔ hot_take confusion directional?
     - Do errors cluster by player name — did the model learn "Jokic comments are positive" as a topic shortcut?
     - Does any digit push toward stat_backed regardless of whether the number is load-bearing?
     Report the patterns you confirmed AND the ones you tested and rejected. A rejected hypothesis is evidence too.
     Critically: check each pattern against the CORRECTLY classified examples. A pattern equally present in the
     successes doesn't explain the failures — that's the specific way this analysis goes wrong. -->`

### Sample classifications

Five comments run through the fine-tuned model:

| # | Comment | Predicted | Confidence | Correct? |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

**Why #`<!-- FILL -->` is a reasonable prediction:** `<!-- FILL: one or two sentences on what in the text the model plausibly keyed on, and why that lines up with the label definition rather than with a surface shortcut. -->`

---

## Reflection: what the model learned vs. what I intended

`<!-- FILL: This is the highest-value section in the report and it is NOT a list of wrong predictions — it's the gap between your definitions and the model's actual decision boundary.

Some framing to push against, using your own taxonomy:

INTENDED for stat_backed: "a number that does argumentative work" — the load-bearing test.
PLAUSIBLY LEARNED: "contains digits, or contains stat vocabulary like TS%/per-100." Check this directly: find a
decorative-stat comment you labeled hot_take and see what the model predicted. If it says stat_backed with high
confidence, the model learned the surface tell and skipped the rule entirely — which means the single most
interesting distinction in the taxonomy was never actually transmitted.

INTENDED for consensus_take vs. hot_take: alignment with community belief.
PLAUSIBLY LEARNED: sentiment, or hedging language, or just "which players are mentioned." If hot_take predictions
track negative sentiment about any player, the model learned a sentiment classifier wearing your taxonomy's
clothes — it would call a negative-but-orthodox take a hot_take and a positive-but-contrarian take a consensus_take.
That's a specific, checkable claim. Check it.

INTENDED for reaction: no claim survives the strip test.
PLAUSIBLY LEARNED: caps, emoji, and short length. Test with a long, calm, claim-free comment and with a
short, all-caps comment that does contain a real claim.

Also address what the model MISSED, not just what it substituted. And be honest about the possibility that
consensus_take and hot_take collapsed into one undifferentiated "unsupported opinion" category from the model's
point of view — if the confusion matrix shows them trading errors heavily in both directions, that's what happened,
and it's a genuine finding about whether 200 examples can transmit world knowledge. -->`

---

## Spec reflection

**One way the spec helped:** `<!-- FILL -->`

**One way the implementation diverged from it, and why:** `<!-- FILL: Be specific and honest. Divergence is expected and saying "it didn't" reads as not having noticed. Likely candidates: a label definition you had to sharpen mid-annotation; the stratified-rather-than-random sampling decision; a hyperparameter you changed off the notebook default; the AI-pre-labeling decision if you reversed it. -->`

---

## AI usage

**1. Label stress-testing (before annotation).** I gave Claude the four label definitions and the ordered decision procedure and asked it to generate 10 r/NBA-style comments engineered to sit exactly on the boundaries. I labeled all 10 myself using only the written rules. `<!-- FILL: what came back, which ones you couldn't resolve from the rules alone, and what you changed in the definitions as a result. If nothing broke, say that — but say which cases you tested. -->` None of these generated comments entered the dataset; synthetic LLM-written comments have a different texture from real ones and would have taught the model the wrong distribution.

**2. Failure analysis (after evaluation).** I gave Claude the full list of misclassified test examples with true labels, predicted labels, and confidences, and asked it to propose *systematic* patterns rather than explain individual errors. `<!-- FILL: what it proposed, which patterns you confirmed by re-reading the examples, and — importantly — which you rejected and why. Note anything you had to override. -->` I verified each proposed pattern against the correctly-classified examples as well, since a pattern equally present in the successes doesn't explain the failures.

**3. Repo and document scaffolding.** I used Claude to draft the structure of this README and of `planning.md`, and to pressure-test the label taxonomy during design — including talking me out of `<!-- FILL: e.g. an earlier label pair, or the 4-labels-at-200-examples sizing question -->`. `<!-- FILL: what you overrode or rewrote. -->`

**4. Dataset assembly and pre-labeling — the big one.** I directed Claude to collect r/NBA comments from an archived window through the Arctic Shift API and assemble them into the labeled CSV. It produced 204 verbatim comments with a proposed label and an edge-case note on each. Two things I overrode during that process, both worth recording:

- It initially included two rows that were **its own invented examples from `planning.md`**, not collected comments — precisely the synthetic-data contamination §7a had ruled out. Both were removed. The lesson generalizes: when the same tool writes your examples and collects your data, verify that they stayed separate.
- The first assembly came out at 239 rows with `reaction` at 36%, over the 70-row cap I'd set. Trimmed to 204 by dropping the lowest-signal reaction rows (one-to-three-word comments like "Money" and "google it"), which fixed the distribution and removed the noisiest training data in the same move.

**Annotation disclosure — the original plan was reversed.** [planning.md §7b](planning.md) committed to no LLM pre-labeling, for reasons I still think are right. In practice **every label in the committed CSV is machine-proposed** (`pre_labeled=proposed` on all 204 rows) and awaits human review. Keeping both the original refusal and the reversal in the document is deliberate: the reasoning for the refusal is exactly what makes the reversal a risk worth flagging rather than a detail to bury.

---

## Did it hit the success criteria?

Thresholds were set in [planning.md §6](planning.md) *before* any results existed.

| Tier | Criterion | Target | Actual | Met? |
|---|---|---|---|---|
| 1 — learned something | Accuracy | ≥ 0.50 | | |
| 1 | Macro-F1 | ≥ 0.45 | | |
| 1 | No class with F1 = 0 | — | | |
| 1 | Beats baseline on macro-F1 | — | | |
| 2 — genuinely useful | Accuracy | ≥ 0.70 | | |
| 2 | Macro-F1 | ≥ 0.65 | | |
| 2 | Every per-class F1 | ≥ 0.55 | | |
| 2 | `consensus_take`↔`hot_take` < half of all errors | — | | |
| 3 — deployable | `stat_backed` precision | ≥ 0.80 | | |
| 3 | `stat_backed` recall | ≥ 0.50 | | |

`<!-- FILL: 2–3 sentences. Which tier did you actually reach? If you missed Tier 2, say so plainly — a missed threshold you set in advance and reported honestly is worth more than a threshold quietly lowered to match the result. -->`

---

## Repo contents

| Path | What it is |
|---|---|
| [`planning.md`](planning.md) | Design doc, written before collection |
| [`annotation-guide.md`](annotation-guide.md) | One-page decision procedure used while labeling |
| [`data/takemeter_labeled.csv`](data/takemeter_labeled.csv) | All 200 labeled examples, unsplit |
| `evaluation_results.json` | Metrics exported from the notebook |
| `confusion_matrix.png` | Supplementary image of the matrix above |
