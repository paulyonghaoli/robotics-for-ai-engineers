# 10.4 Dataset lifecycle: curation, provenance, versioning

**Status:** Code verified · **Prereqs:** lesson 10.1 · **Time:** ~2.5 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

In 2026 the robot-learning field publicly changed its mind about what the bottleneck is. The old answer was "not enough data." The new one, from a corpus analysis of 1,228 vision-language-action papers, is that **the data we have is poorly annotated, dangerously homogeneous, and largely untested** — and the numbers behind that are startling:

- Pooling heterogeneous robot datasets can make a model **worse** (negative transfer). Naive cross-embodiment scaling has plateaued.
- A curated **5% coreset recovers 85–90%** of full-dataset performance. Most collected data is dead weight.
- Diverse instruction augmentation moved one task **from 0% to 90% success** — the language channel had been doing nothing.
- **Failure data is thrown away** almost universally, despite recovery being a named open problem.

If you come from data engineering, read that list again, because every item is a problem you already know how to attack. This is the least-crowded door into robotics for someone with your background, and this lesson is its core.

## B. Mental model

A robot dataset is not a pile of trajectories — it's a **pipeline with a lifecycle**: collect → validate → curate → version → train → measure → feed back. Four properties decide whether it's an asset or a liability:

1. **Provenance.** For any trajectory: which robot, which firmware, which operator, which calibration, which scene, and — for synthetic data — which generator and seed. Missing provenance is why "the model got worse and we don't know which data did it" is a common sentence.
2. **Composition, not volume.** *Which* trajectories, in what mix. The 5%-coreset result says selection dominates size, and negative transfer says more can be strictly worse.
3. **Coverage.** Lesson 10.2's argument applied to training data: diversity of lighting, background, distractors, and initial conditions predicts generalization far better than hours collected.
4. **Immutability + versioning.** A dataset you can silently mutate is one whose experiments cannot be reproduced. Datasets get versions, exactly like models.

The engineering instinct that transfers most directly: **a trajectory is a row with very expensive provenance.** Everything you know about schema evolution, dedup, lineage, and quality gates applies — the rows just cost $100/hour to collect instead of arriving free from a web service.

## C. Formulation

**Deduplication.** Robot data is full of near-duplicates — a teleoperator repeating a pick fifteen times with millimetre variation. Exact hashing finds nothing; you need similarity over trajectory features, then keep one representative per cluster. This is what makes a 5% coreset possible.

**Coreset selection.** Given a budget \(k\), choose the subset maximizing coverage of the feature space. A greedy farthest-point traversal — repeatedly add the trajectory farthest from everything already chosen — is simple, has a bounded approximation guarantee, and dramatically outperforms random sampling for the same \(k\).

**Provenance record.** Minimum viable schema per trajectory:

```
trajectory_id, collected_at, robot_id, firmware_version, calibration_id,
operator_id, scene_id, task_label, outcome (success|failure|intervention),
source (teleop|scripted|sim|generated), generator_seed, parent_dataset_version
```

The two fields most often missing are `outcome` (because failures were discarded) and `generator_seed` (because nobody expected to need to regenerate synthetic data). Both are cheap to record and expensive to reconstruct.

### Curation, priced: coverage per label

The coreset argument in one table. Twelve hundred logged trajectories,
described by four features each, and a labelling budget to spend; coverage
scored over the binned feature space:

| Budget | Farthest-point selection | Random selection |
|---|---|---|
| 25 | **0.812** | 0.344 |
| 100 | **1.000** | 0.675 |
| 400 | 1.000 | 0.981 |

Farthest-point sampling reaches *complete* coverage of the feature space at
a budget of 100, where random sampling has covered two-thirds; random needs
the full 400 to approach what curation achieved with a quarter of it. The
mechanism is the same one behind lesson 9.3's budget study: random sampling
reproduces the collection distribution, so it spends most of its budget
re-buying the dense middle — the ten-thousandth straight-corridor cruise —
while the rare corners that actually stretch a model wait at the tail.
Farthest-point inverts that, spending every label on the most novel thing
remaining.

A 4× labelling-cost difference at equal coverage is the business case for
curation infrastructure in one line, and it compounds: the same selection
logic that stretches a labelling budget also picks which episodes to keep
when storage forces deletion, which is this lesson's lifecycle point — the
dataset you can afford to keep should be chosen by coverage, not by arrival
order.

## D. From ML to robotics

- **This is feature-store discipline** with harder constraints: no backfill (you can't re-run yesterday's physical world) and expensive rows.
- **Negative transfer is a distribution-mixing problem** you've met in multi-source training — pooling sources with different label semantics or dynamics hurts, and the fix is the same: measure per-source contribution rather than assuming additivity.
- **The failure-data gap is a labeling-policy problem.** Somebody decided "we collect demonstrations," and that decision silently discarded the most informative samples. Interventions and recoveries are worth more per sample than clean demonstrations.

## E. Practice

<code-exercise src="eval-l4-coreset"></code-exercise>

<code-exercise src="eval-l4-provenance"></code-exercise>

## F. In production

**LeRobotDataset** won distribution — all six major dataset lineages now redistribute through it, and v3.0's multi-episode files plus streaming made multi-terabyte datasets practical to consume. **ISO/WD 26264-1** (humanoid robot datasets) reached Working Draft in June 2026, covering lifecycle, provenance, and traceability — the earliest ISO stage, years from binding, but a signal about where this is heading. Dedup tooling remains conspicuously immature: SCIZOR and SIEVE are research prototypes, and there is nothing resembling FineWeb or NeMo Curator for trajectories. **That gap is an opportunity, not a warning.**

## G. Experiment

Take the capstone's episode logs (`results.json` records seed, success, collisions, path ratio, latency). Treat each episode as a training sample and ask the dataset questions of it: how much of the metric space do 8 episodes cover versus 100? Which episodes would a greedy coreset keep? Do the kept episodes preserve the success rate of the full set? This is coreset selection on data you generated, where you can check the answer.

## H. Failure modes

- **No provenance** — a bad batch is undiscoverable and unremovable after the fact.
- **Dedup by exact hash** — finds nothing on continuous sensor data; you need similarity.
- **Mutable datasets** — silent edits mean two people report different results from "the same" data.
- **Pooling by default** — assuming more sources is monotonically better, when negative transfer says otherwise. Measure per-source contribution.
- **Discarding failures** — throwing away the samples that teach recovery, then wondering why the policy can't recover.
- **Coresets chosen by loss** — selecting "hard" examples by model loss couples your dataset to the model that scored it, and bakes that model's blind spots into every future one.

## I. Questions

1. *(Concept)* Why can adding data make a robot policy worse, when adding data rarely hurts a supervised classifier?
2. *(Calculation)* 40,000 trajectories, 5% coreset recovering 88% of performance. If collection costs $120/hour at 12 trajectories/hour, what did the redundant 95% cost?
3. *(Debugging)* Performance dropped after ingesting a new batch. What provenance fields let you find the cause in minutes rather than weeks?
4. *(System design)* Design the ingestion pipeline for a 10-robot fleet producing 500 trajectories/day: schema, validation gates, dedup, versioning, and what you keep from failed runs.

??? note "Answer sketches"
    **1.** Because the label is embodiment-specific. Two trajectories with near-identical observations but different robots, calibrations, or teleoperators carry *contradictory* action targets, so the policy is fit toward an average of incompatible action distributions rather than either one — negative transfer. A classifier's extra data usually shares label semantics across sources, and its added rows are near-duplicates that cost only compute; here they actively move the conditional mean and crowd out the rare behaviours that carry the signal.

    **2.** 38,000 redundant trajectories ÷ 12 per hour × $120 ≈ **$380,000** — for the last 12% of performance. That arithmetic is why curation is a funded engineering discipline rather than a nice-to-have.

    **3.** `parent_dataset_version` plus `collected_at` isolate the batch; then slicing it by `robot_id`, `firmware_version`, `calibration_id`, `operator_id`, and `scene_id` finds the shared attribute — a miscalibrated arm, one operator's habit, a firmware bump — and `source`/`generator_seed` does the same for synthetic rows. The fix is a re-run with the offending slice held out, measuring per-source contribution rather than trusting that pooling helps; without those fields the only available move is bisecting retrains over the whole batch, which is the weeks-not-minutes version.

    **4.** Ingest against the section C schema with every field required at write time, and gate on it: reject (to a quarantine bucket, never delete) any trajectory missing `outcome`, `calibration_id`, or — for synthetic rows — `generator_seed`, plus sanity checks on duration, sensor ranges, and dropped frames. Dedup nightly by similarity over trajectory features, keeping one representative per cluster and *recording cluster ids* so the discards stay recoverable; 5,000 trajectories/day makes this the difference between a coreset and a landfill. Version by immutable daily append-only snapshots with a weekly tagged release that names its `parent_dataset_version` and carries the coreset manifest — and keep every failure and intervention, labelled as such, since those are the recovery data the field is documented to throw away.

### Interactive quiz

<quiz-bank src="eval-l4-data"></quiz-bank>

## J. References

| Reference | Type | Difficulty | Why read it |
|---|---|---|---|
| [What 1,228 VLA papers say about the robot data problem](https://labelstud.io/blog/vla-robot-data-problem/) | analysis | introductory | The corpus study behind this lesson's numbers |
| [LeRobotDataset v3.0](https://huggingface.co/docs/lerobot/main/en/lerobot-dataset-v3) | docs | intermediate | The de-facto standard format |
| [VLA datasets & benchmarks survey (arXiv:2604.23001)](https://arxiv.org/pdf/2604.23001) | paper | intermediate | Argues data infrastructure is now a first-class research problem |

## K. Graded work & portfolio extension

**Graded:** the coreset and provenance exercises are the module's core skills.

**Portfolio:** build a small dataset-quality tool — ingest LeRobot-format episodes, report coverage and near-duplicate clusters, and emit a provenance-completeness score. It's a weekend of work, it addresses a documented gap, and it's precisely the artifact the data-infrastructure roles in [the frontier map](../../frontier.md) are hiring for.
