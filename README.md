# TakeMeter

A fine-tuned text classifier that sorts r/NBA comments by **what kind of support a take offers** — does it bring numbers, echo what the sub already believes, swing against the grain, or just scream?

> **Demo video:** Not recorded or linked yet. The assignment requires a 3–5 minute video showing live classifications, one correct and one incorrect prediction, and the evaluation report; add its hosted link here before submission.
> **Labeled dataset:** [`data/takemeter_labeled.csv`](data/takemeter_labeled.csv) — 227 examples, unsplit
> **Design doc:** [`planning.md`](planning.md) — written before data collection
> **Notebook:** [`takemeter_colab.ipynb`](takemeter_colab.ipynb) — the full pipeline, self-contained

---

## Community

**r/NBA** (~16M subscribers) — comment sections from game threads, post-game threads, and news and `[Highlight]` posts. Public content only.

I picked it for three reasons. **The variance is enormous**: one post-game thread produces both a one-word scream and a 300-word pick-and-roll breakdown with per-100 numbers attached, in the same hour. **The community already polices this distinction itself** — "source?", "that's a crazy take", and "stat-padder" are native r/NBA vocabulary, so I'm modeling a judgment the sub already makes rather than imposing an outside notion of quality. And **it's fully public**, no authentication or gated content anywhere in the dataset.

The task isn't trivial, and the reason is worth stating up front: separating a stat-heavy essay from "LETS GOOO" is easy, and a keyword matcher would do it. The hard part is separating two comments that are *formally identical* — same length, same confidence, same absence of numbers — where one is a take r/NBA agrees with and one is a take r/NBA would argue with. That distinction lives in world knowledge about community belief, not in surface features of the text.

---

## Label taxonomy

Four labels, ordered by what kind of support the comment offers. All examples below are verbatim from the collected dataset.

### `stat_backed`

Makes an evaluative claim and supports it with at least one specific, checkable quantity — a stat line, percentage, rank, split, record, or dated comparison — where the number does real argumentative work rather than sitting there for decoration.

> "Kyrie has played in more than 70 games in 3 seasons of his 14 year career, the last time being 9 seasons ago. He averages less than 70% of games played per season over the course of his career."

> "Is his rebounding that bad? He averaged 7 boards per game in 21 MPG."

The second one is short, which matters: `stat_backed` is not a synonym for "long." The per-minute context is what makes 7 boards an argument rather than a fact.

### `consensus_take`

Asserts an evaluative claim with no statistical support, where the claim is one r/NBA broadly agrees with — the kind of comment that draws "yeah, obviously" replies rather than argument.

> "Nash suns were highly flawed. Their offense was potent as anything, but they couldn't defend a team of 5 year olds."

> "We still doing the underestimate the pacers thing? They've been one of the best teams in the league since January"

### `hot_take`

Asserts an evaluative claim with no real statistical support, where the claim runs against r/NBA consensus — contrarian, provocative, or framed to get a rise.

> "Pacers needa do this for the culture man. OKC are the corniest team in the league, can't stand SGA and JW."

> "Giddey could be an all star if people just go based off his stats...wouldnt be surprised if he average 20+/8/8..."

The second one has numbers in it and is still `hot_take`. They're a speculative projection about a future season, not evidence about a past one — nothing to check, so nothing load-bearing.

### `reaction`

Expresses an in-the-moment emotional response — shock, joy, despair, a joke, a meme — and makes no evaluative claim that survives stripping the emotion away.

> "Why am I tearing up and shaking right now. Tf is wrong with me"

> "As a Spurs hater I'd love to see It. As a fan of basketball that would be a fucking tragedy"

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

**Exhaustiveness.** Every r/NBA comment that is about basketball lands in one of these four; the residue is off-topic content. That residue was excluded *mechanically at collection time* by [`tools/collect_reddit.py`](tools/collect_reddit.py) rather than bucketed into a catch-all — bot accounts, `[removed]`/`[deleted]`, link-only comments, "what's the stream" variants, and anything under 3 or over 180 words. **I have to report a gap here honestly: the script filters these but never counted them,** so I can't give the skipped-comment tally that `planning.md` said I would. What I can say is that no comment surviving those filters needed a fifth label, and no row in the final 227 is a forced fit.

---

## Data collection and labeling

**Source:** r/NBA public comments, collected through the [Arctic Shift](https://arctic-shift.photon-reddit.com) historical API via [`tools/collect_reddit.py`](tools/collect_reddit.py), rather than through reddit.com — reddit's own API makes fetching a specific past date range awkward.

**Collection window: the 2025 NBA playoffs, April 19 – June 25, 2025**, ending with Thunder–Pacers Game 7 on June 22. The original plan assumed a live in-season window, but collection happened in late September, before the Oct 3 preseason — r/NBA had no game or post-game threads at all. Rather than patch around that, the whole window moved into the archive. That turned out cleaner: one frozen window means one consensus frame for every label, which is exactly what the drifting-consensus rule in [planning.md §3b](planning.md) asks for, and the archive still contains the full range of thread types.

Four sources were sampled, each because it over-produces a different label:

| Source | Rows | Over-produces |
|---|---|---|
| `stat_search` (full-text query) | 85 | `stat_backed` |
| `finals_g1_live` (game thread) | 31 | `reaction` |
| `finals_g7_live` (game thread) | 30 | `reaction` |
| `finals_g7_aftermath` (post-game) | 29 | `consensus_take`, `stat_backed` |
| `take_search` (full-text query) | 29 | `hot_take` |
| `playoffs_general` (date window) | 23 | mixed |

**Sampling is stratified, not random — and this matters for reading the results.** Uniform sampling of r/NBA would return roughly 70% `reaction` and under 5% `stat_backed`, producing a model that predicts `reaction` constantly and looks 70% accurate while having learned nothing. So I collected from each source until its dominant label hit quota, then switched. The consequence: **test-set accuracy here is not an estimate of accuracy on live r/NBA traffic.** It's accuracy on a deliberately balanced sample. That's the right trade for learning boundaries, but it's a real limitation.

**Sampling artifact worth stating plainly.** `stat_backed` is rare enough that date-window sampling alone barely produced it, so those rows were pulled with full-text queries for stat vocabulary (`averaged`, `shooting`, `rebounds`, `assists`). That means the class was *selected for containing stat words*, which inflates the link between stat vocabulary and the label beyond what natural r/NBA traffic would show. If the model ends up keying on digits and the word "averaged," this collection method is part of the cause, not purely a modeling failure. The `source_thread_type` column marks query-sourced rows separately so the effect can be measured rather than guessed at.

### Labeling process, including the part that needs disclosing

Labeling ran in two stages, and the first one was not what [planning.md §7b](planning.md) originally committed to.

**Stage 1 — machine proposal.** All 227 rows were assembled *and labeled* in one pass by Claude (Opus), working from the label definitions and the ordered decision procedure. Every row was marked `pre_labeled=proposed`, and the original machine label is preserved in a `proposed_label` column so it stays auditable after any override.

**Stage 2 — human confirmation.** I reviewed every row through [`tools/review_labels.py`](tools/review_labels.py), a local tool that shows one comment at a time with its proposed label and records accept-or-override per row. **The result was 227 accepted, 0 overridden — an override rate of 0%.**

That number needs its context stated rather than buried, because planning.md pre-registered a near-zero override rate as a warning sign of rubber-stamping. What happened: I had already read the proposed labels before the review tool existed and formed my own judgment on them then, so the pass through the tool confirmed decisions already made rather than making them cold. I agreed with the proposal on every row.

I'm reporting the rate anyway, because **the artifact alone cannot distinguish a genuine confirmation pass from a rubber stamp**, and a reader who wants to discount my review has the number they need to do it. A blind second-annotator check was planned, but it has not been completed; this project therefore has no independent agreement score.

### Label distribution

| Label | Count | Share | Mean words |
|---|---|---|---|
| `stat_backed` | 48 | 21.1% | 43.4 |
| `consensus_take` | 64 | 28.2% | 36.5 |
| `hot_take` | 56 | 24.7% | 29.9 |
| `reaction` | 59 | 26.0% | 11.4 |
| **Total** | **227** | 100% | — |

Every class sits between 21% and 28%, well inside the "at least 20% per label" guidance and nowhere near the 70% imbalance threshold. The validator reports zero near-duplicates — which matters, because a duplicate straddling the 70/15/15 split would inflate test accuracy invisibly. `stat_backed` is the scarce class on r/NBA and needed two extra rounds of stat-vocabulary queries to clear the 20% floor; it remains the smallest class, so its per-class numbers rest on the fewest test examples of any label.

**The length gap is a live leakage risk.** `reaction` averages 11 words; `stat_backed` averages 43. A model can get a long way on length alone without ever learning the load-bearing test, so this gets checked explicitly in the reflection rather than assumed away.

**Test-set size, stated plainly.** 227 examples at a 15% test split gives 35 test comments — roughly 8–9 per class. A single example moves a per-class F1 by roughly 0.12. Per-class numbers below are directional; the confusion matrix and the actual error text carry more weight than any decimal place.

### Three examples that were genuinely hard to label

These are cases I actually hit. The edge cases I *anticipated* before collecting are in [planning.md §3](planning.md) — a separate thing. Twelve of the 227 rows are flagged `HARD` in the `notes` column; these three are the most instructive, and each sits on a different boundary.

**1. "Last year was his third-best shooting year of his career."**
*Torn between:* `stat_backed` and `consensus_take`.
*Why it was hard:* There is no raw number anywhere in it. My definition says "a specific, checkable quantity," and my instinct was that a quantity means digits. But "third-best shooting year of his career" is precisely checkable — you can look it up and be proved wrong — while a comment like "he shot well last year" cannot.
*Decided:* `stat_backed`. **A rank is a quantity.** The load-bearing test settles it cleanly: delete the ranking and nothing is left of the claim. This forced me to stop treating "contains digits" as a proxy for the rule, which turned out to be the same shortcut I later had to check the model for.

**2. "Aww look at the baby back bitch cry after talking shit... Imagine your 'star' having a 6 point game in the NBA finals lmao."**
*Torn between:* `stat_backed` and `hot_take`.
*Why it was hard:* "6 point game in the NBA finals" is a real, specific, checkable number about a real performance. By a literal reading of the `stat_backed` definition it qualifies.
*Decided:* `hot_take`, on the decorative-stat rule from [planning.md §3a](planning.md). The number isn't reasoning, it's ammunition — the comment is an insult that happens to be numerically accurate. Apply the load-bearing test properly and it fails: delete "6 point game" and the comment still says exactly the same thing with exactly the same force, because the force was never coming from the number.

**3. "I have 100% belief."**
*Torn between:* `stat_backed` and `reaction`.
*Why it was hard:* It contains a percentage. A naive reading of step 1 stops right there.
*Decided:* `reaction`. "100%" is an idiom for total conviction, not a statistic — there is nothing to check. The strip test leaves nothing behind: remove the emphasis and no claim anyone could disagree with survives. This is the clearest case in the dataset that the taxonomy is about *argumentative function*, not about surface tokens, and it's the row I'd most want the model to get right.

---

## Fine-tuning approach

**Base model:** `distilbert-base-uncased` (66M parameters) — a distilled BERT that keeps most of BERT-base's language understanding at roughly 40% of the size, which makes it trainable on a free T4 in minutes.

**Setup:** learning rate 2e-5, batch size 16, max sequence length 256, weight decay 0.01, warmup ratio 0.1, seed 42. The dataset is split 70/15/15 into train/validation/test, **stratified by label** — with only 35 test rows, an unstratified draw can easily leave a class with two or three test examples, and per-class F1 on three examples is noise rather than measurement.

**Key hyperparameter decision: epochs are selected by validation macro-F1 rather than fixed at 3.**

The notebook default of 3 epochs is a guess that ignores the dataset. With ~158 training examples and batch size 16, one epoch is only 10 optimizer steps — so 3 epochs is 30 steps total, which can leave the classification head undertrained. But simply raising it to 8 overfits a set this small. Rather than pick a number blind, training runs up to 8 epochs, evaluates on the validation split after each one, and restores the checkpoint with the best validation macro-F1 (`load_best_model_at_end`), with early stopping after 3 epochs without improvement. Macro-F1 is the selection metric for the same reason it's the primary metric in [planning.md §5](planning.md): it refuses to let an easy class subsidize a hard one, whereas selecting on accuracy would happily pick a checkpoint that had given up on `stat_backed`.

Epoch 7 and epoch 8 tied for the best validation macro-F1 (0.5989), so the trainer retained epoch 7. Validation loss continued to fall from 1.0020 at epoch 7 to 0.9971 at epoch 8; macro-F1, the registered selection metric, did not improve.

**Class imbalance handling:** none, and none needed. The distribution spans 21.1% to 28.2%, so the loss was left unweighted; weighting a distribution this even would add a knob without addressing a real problem.

---

## Baseline

**Baseline:** zero-shot classification through Groq with no task-specific training, run against the same stratified test set as DistilBERT. The assignment-specified Llama 4 Scout model was retired. The notebook now uses Groq's [recommended replacement, `openai/gpt-oss-120b`](https://console.groq.com/docs/deprecations). This is a documented deviation from the assignment; the saved metrics still reflect the failed old-model run until the notebook is rerun with the replacement.

The prompt carries the label definitions and the ordered decision procedure verbatim from planning.md, so the zero-shot model gets the same rules as the human review.

**Prompt used:**

```text
You are classifying comments from r/NBA by WHAT KIND OF SUPPORT the take offers.

Apply this decision procedure IN ORDER and stop at the first match:

1. Does the comment cite a specific, checkable number (a stat line, percentage, rank, split,
   record, or dated comparison) that does real argumentative work?
   Test: delete the number. If the argument gets weaker, the number was load-bearing.
   If the identical assertion remains with identical force, the number was decorative -
   do NOT stop here, continue to step 2.
   -> stat_backed

2. Otherwise, does it assert an evaluative claim?
   Test: imagine a reply saying "yeah, obviously."
   - Reads as normal, because r/NBA broadly agrees -> consensus_take
   - Reads as sarcastic, because the claim runs against r/NBA consensus -> hot_take
   Consensus means r/NBA consensus, NOT national NBA media consensus. When they disagree,
   r/NBA wins.

3. No evaluative claim survives stripping the emotion (caps, emoji, exclamations, jokes,
   chants like "MVP! MVP!").
   -> reaction

Order matters: a contrarian comment that brings real load-bearing numbers is stat_backed,
not hot_take. Evidence outranks alignment.

Respond with EXACTLY ONE of these four words and nothing else:
stat_backed
consensus_take
hot_take
reaction
```

Each test comment is sent separately at temperature 0. The replacement uses low reasoning effort with reasoning text disabled and a 128-token completion limit; successful responses are parsed by exact token match first, then substring. Genuine unparseable model responses are scored as wrong rather than dropped.

**Prediction recorded before running anything** (in [planning.md §5](planning.md)): I expected the zero-shot LLM to *beat* DistilBERT on the `consensus_take` / `hot_take` boundary, because that boundary requires knowing what NBA fans believe — world knowledge a 17B internet-trained model has and a 66M DistilBERT fine-tuned on ~158 examples does not. I expected DistilBERT to win on `reaction` and `stat_backed`, where the signal is lexical and learnable from few examples.

The prediction cannot yet be evaluated. The saved test predictions come from the failed Llama 4 Scout call; rerunning the notebook with the replacement is required to measure whether the expected consensus/hot-take advantage holds.

---

## Evaluation report

### Fine-tuned model results

On the 35-row stratified test set, DistilBERT reached **60.0% accuracy**, **0.549 macro-F1**, and **0.535 weighted-F1**. It clears the Tier 1 accuracy and macro-F1 thresholds, but misses the Tier 1 requirement that every class have nonzero F1. Results are noisy at this test size: each class has only 7–10 examples.

| Label | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| `stat_backed` | 0.75 | 0.86 | 0.80 | 7 |
| `consensus_take` | 0.44 | 0.80 | 0.57 | 10 |
| `hot_take` | 0.00 | 0.00 | 0.00 | 9 |
| `reaction` | 0.88 | 0.78 | 0.82 | 9 |

Confusion matrix (rows are true labels; columns are predictions):

| True \\ Predicted | stat_backed | consensus_take | hot_take | reaction |
|---|---:|---:|---:|---:|
| `stat_backed` | 6 | 1 | 0 | 0 |
| `consensus_take` | 0 | 8 | 1 | 1 |
| `hot_take` | 2 | 7 | 0 | 0 |
| `reaction` | 0 | 2 | 0 | 7 |

The model made 14 errors. Eight were across the **consensus/hot-take boundary** (seven hot takes predicted as consensus and one consensus take predicted as hot take). It also missed all nine hot takes as a class, splitting them between `consensus_take` and `stat_backed`. The high `stat_backed` and `reaction` scores are directional only, given the small supports.

### Baseline results need a rerun

The original 35 Groq requests returned HTTP 404 because the specified model was shut down on July 17, 2026, according to [Groq's deprecation notice](https://console.groq.com/docs/deprecations). Those API errors are preserved as `API_ERROR`; their zero-score export has been corrected to null metrics and must not be treated as a model result. The notebook is now configured for Groq's recommended `openai/gpt-oss-120b` replacement, which is a deviation from the exact model named in the course brief. **To produce baseline metrics**, open the notebook in Colab, set the Groq secret, and rerun the notebook so it exports fresh `evaluation_results.json` and `test_predictions.csv`. Until then, there is no valid baseline score and the baseline comparison requirement is incomplete.

### Error examples

These fine-tuned model errors illustrate the observed boundaries:

| True label | Predicted | Example | What failed |
|---|---|---|---|
| `hot_take` | `consensus_take` | “Any OKC championship is based entirely on the refs…” | The model recognized an unsupported evaluation but missed that this claim runs against the community consensus. |
| `hot_take` | `stat_backed` | “That Mavericks team won 57 games and was amazing in the postseason… Ya'll overrate modern role players.” | It appears to have treated the number as sufficient evidence, though the comment's main claim is a broad comparison and the number is not clearly load-bearing. |
| `reaction` | `consensus_take` | “Wow, talk about easy decisions on saving $150M. None of those guys are worth the associated amounts.” | The opinion-like sentence survived the emotional opening, so the model treated the comment as a stable evaluation rather than a reaction. |

### Sample predictions

| Comment (excerpt) | True | Predicted | Confidence |
|---|---|---|---:|
| “47th in points, 115th in rebounds, 142nd in assists…” | `stat_backed` | `stat_backed` | 0.64 |
| “Let's go!!!!!” | `reaction` | `reaction` | 0.65 |
| “Coming for Windhorst's throne” | `reaction` | `reaction` | 0.65 |

The ranking comment is a reasonable `stat_backed` prediction: its specific league ranks are checkable and carry the argument.

### Calibration and success tiers

Mean top-label confidence was 0.458, with expected calibration error (ECE) 0.142. In the `<50%` bucket (25 examples), accuracy was 0.48; in the `50–70%` bucket (10 examples), accuracy was 0.90. Confidence remains uncertain at this small sample size and should not be presented as a reliable probability.

| Criterion | Result |
|---|---|
| Tier 1: accuracy ≥ 0.50 | Met (0.600) |
| Tier 1: macro-F1 ≥ 0.45 | Met (0.549) |
| Tier 1: no class F1 = 0 | Not met (`hot_take` F1 0.00) |
| Tier 1: beats baseline on macro-F1 | Not assessable (baseline API failed) |
| Tier 2: accuracy ≥ 0.70 | Not met (0.600) |
| Tier 2: macro-F1 ≥ 0.65 | Not met (0.549) |
| Tier 2: every class F1 ≥ 0.55 | Not met (`hot_take` 0.00) |
| Tier 2: consensus↔hot errors under half of all errors | Not met (8 of 14) |
| Tier 3: stat-backed precision ≥ 0.80 | Not met (0.75) |
| Tier 3: stat-backed recall ≥ 0.50 | Met (0.86) |

The model captured useful signals for statistical evidence and immediate reactions, but failed to identify any hot takes in this test set. Its decision boundary often collapsed contrarian opinions into consensus, and sometimes mistook hot takes containing numbers for statistical arguments. This is consistent with a model relying on surface cues instead of the intended community-alignment and load-bearing-evidence rules. The targeted baseline comparison remains unavailable because the requested API model has been retired.

---

## Spec reflection

**One way the spec helped.** Requiring the data-collection plan *in writing before collecting* is what caught the calendar problem. Writing out "game threads → `reaction`, post-game threads → `stat_backed`" forced me to check whether those threads existed, and they didn't — collection fell in late September, before the Oct 3 preseason, so r/NBA had no game threads at all. Had I started collecting first and planned afterward, I'd have discovered this with a half-built dataset drawn from whatever the offseason happened to offer, and the `consensus_take` frame would have drifted across it. Instead the whole window moved into the 2025 playoff archive, which fixed the problem and made the taxonomy *more* coherent than the original plan, because every label is now judged against one frozen moment in r/NBA's beliefs.

**One way the implementation diverged, and why.** planning.md §7b committed explicitly to hand-labeling all 200 examples with no LLM pre-labeling, and gave a real reason: the `consensus_take`/`hot_take` boundary is a judgment about community norms that should be mine, and seeding it from the same class of model the baseline is testing contaminates the comparison. **That commitment was reversed.** The dataset was assembled and labeled in a single machine pass, and my involvement became review rather than authorship — which then produced a 0% override rate, the exact symptom §7b was written to detect.

The honest accounting is that the reversal traded annotation integrity for speed, and the cost is real: the ground truth for the hardest boundary is partly a machine's read on what r/NBA believes. The planned zero-shot comparison could have added another model's read of the same question, but the required API model was retired before a valid run could be completed. The planned blind second-annotator check is also incomplete; there are no independent labels or agreement score in this repo. I kept both the original refusal and the reversal in planning.md rather than quietly editing the plan to match what I did, because the reasoning for the refusal is precisely what makes the reversal a risk worth flagging.

---

## AI usage

**1. Label stress-testing, before annotation.** I gave Claude (Opus) the four label definitions, the ordered decision procedure, and all four edge-case rules from planning.md §3, and asked it to generate 10 r/NBA-style comments engineered to sit exactly on the boundaries — five on `consensus_take`/`hot_take`, three decorative-stat cases, two embedded-claim cases. I then labeled all 10 myself using only the written rules. Output is in [`label-stress-test.md`](label-stress-test.md). None of these generated comments entered the dataset; synthetic LLM-written comments have a different texture from real ones and would teach the model the wrong distribution.

**2. Dataset assembly and pre-labeling — the significant one.** I directed Claude to collect r/NBA comments from the archived window through the Arctic Shift API and assemble them into the labeled CSV with a proposed label and an edge-case note on each row. Two things I overrode, both worth recording:

- It initially included two rows that were **its own invented examples from `planning.md`**, not collected comments — precisely the synthetic-data contamination §7a had ruled out. Both were removed. The lesson generalizes: when the same tool writes your examples and collects your data, verify that they stayed separate.
- The first assembly came out at 239 rows with `reaction` at 36%, over the cap I'd set. Trimmed to 204 by dropping the lowest-signal reaction rows — one-to-three-word comments like "Money" and "google it" — which fixed the distribution and removed the noisiest training data in the same move. `stat_backed` was later topped up to clear the 20% floor, bringing the total to 227.

**Annotation disclosure.** Every label in the committed CSV originated as a machine proposal (`proposed_label` column), and my pass over them produced 0 overrides out of 227. The full reasoning, and why I'm reporting that number rather than explaining it away, is in the labeling-process section above.

**3. Tooling.** I directed Claude to build [`tools/review_labels.py`](tools/review_labels.py) (the review interface and its blind second-annotator mode), [`tools/takemeter_app.py`](tools/takemeter_app.py), and [`takemeter_colab.ipynb`](takemeter_colab.ipynb). Two corrections I made to what it produced: the first version of the review tool accepted auto-repeat keystrokes, which meant holding Enter could stamp the entire dataset as reviewed in about a minute — it now ignores repeated keydown events, because a held key is not a judgment about a comment. I also had it add a hard gate in the notebook that refuses to train while any row is still marked `proposed`, rather than relying on my remembering to check.

**4. Failure analysis, after evaluation.** I used Codex to compare the 14 fine-tuned model errors with the 21 correct predictions and check the planned short-comment and digit-presence hypotheses. The directional hot-take-to-consensus error (7 cases) was confirmed; including the one reverse confusion, the consensus/hot-take pair accounts for 8/14 errors. The short-comment hypothesis was not supported: 4/14 errors and 6/21 correct examples were under 15 words, and their average lengths were nearly identical (30.4 vs. 30.6 words). The “any digit means `stat_backed`” hypothesis was also not supported overall: 6/14 errors and 12/21 correct examples contained digits, though two hot takes with numbers were incorrectly predicted as `stat_backed`. Source counts were small, so I did not treat their differences as reliable. I re-read the examples and retained their labels; these look like model boundary errors rather than an obvious inconsistent application of the written rules. The planned LLM comparison could not provide a separate failure analysis because the required Groq model was retired.

### Running the local interface

The notebook's export cell downloads `takemeter_model.zip`. Unzip it into the repository root, then install the runtime and launch the app:

```bash
unzip takemeter_model.zip
pip install torch transformers
python3 tools/takemeter_app.py
```

Open `http://127.0.0.1:8080/` and paste a comment to see the predicted label and all four confidence scores. The model archive is generated by the Colab notebook and is not committed to this repo.

---

## Repo contents

| Path | What it is |
|---|---|
| [`planning.md`](planning.md) | Design doc, written before collection; stretch features planned in §8 |
| [`annotation-guide.md`](annotation-guide.md) | One-page decision procedure used while labeling |
| [`label-stress-test.md`](label-stress-test.md) | Boundary cases generated to test the definitions before annotating |
| [`data/takemeter_labeled.csv`](data/takemeter_labeled.csv) | All 227 labeled examples, unsplit |
| [`takemeter_colab.ipynb`](takemeter_colab.ipynb) | Full pipeline: split, train, baseline, evaluate, calibrate, export |
| [`confusion_matrix.png`](confusion_matrix.png) | Fine-tuned model confusion matrix |
| [`tools/collect_reddit.py`](tools/collect_reddit.py) | Arctic Shift collection script |
| [`tools/review_labels.py`](tools/review_labels.py) | Label review interface; `--mode blind` for the second annotator |
| [`tools/takemeter_app.py`](tools/takemeter_app.py) | Local interface: paste a comment, get label and confidence |
| `evaluation_results.json` | Metrics exported from the notebook |
| `test_predictions.csv` | Every test comment with the fine-tuned prediction and confidence, plus the failed baseline response record |
