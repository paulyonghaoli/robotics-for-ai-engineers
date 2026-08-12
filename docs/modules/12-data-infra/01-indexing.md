# 12.1 Indexing: you can only find what you decided to record

**Status:** Code verified · **Prereqs:** lessons 10.4, 11.4 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Somebody asks: *"pull every episode where we yielded to a pedestrian approaching from the left."*

There are two hundred thousand episodes. The answer arrives in one of three ways, and which one you get was decided long before the question was asked:

1. **Seconds**, because that attribute is indexed.
2. **Hours**, because you can scan raw logs for it — expensive, but the information is there.
3. **Never**, because nobody recorded which direction pedestrians came from, and no amount of compute recovers it.

The third outcome is the one worth engineering against, and it is invisible until the question arrives. A fleet can be logging faithfully, at enormous cost, and still be unable to answer the question that matters — because logging and *indexing* are different decisions and only one of them gets budgeted.

## B. Mental model

**Three layers, each with a different cost and a different lifetime.**

| Layer | Size | Query cost | Changeable later? |
|---|---|---|---|
| Raw episode data | terabytes | minutes–hours | never — it is what it is |
| Derived features | gigabytes | seconds | yes, by reprocessing raw |
| Index | megabytes | milliseconds | yes, cheaply |

The index is small and rebuildable; the derived features are large and rebuildable; the raw data is enormous and **not** rebuildable. So the real design question is not "what should we index" — indexes are cheap and you can add them tomorrow. It is **"what must the raw data contain so that tomorrow's index is possible at all?"**

**Recall is bounded by the schema, not by the query engine.** This is the asymmetry that makes data infrastructure a design job rather than a plumbing job. A perfect index over an incomplete schema returns confident, fast, wrong answers — specifically, it returns *fewer* episodes than exist, and nothing in the result says so.

## C. Formulation

An **inverted index** maps each attribute value to the episode ids carrying it:

```
index["weather=rain"]      -> {14, 88, 203, ...}
index["outcome=collision"] -> {88, 512, ...}
```

A conjunctive query is then a set intersection, costing O(size of the smallest posting list) rather than O(number of episodes). Intersecting smallest-first matters: the cheapest term should bound the work.

For numeric attributes, bucket before indexing — `speed=[1.0,1.5)` — because exact float keys never match anything.

**The metric that is usually missing.** Precision and recall are normally reported against a ground-truth labelling. Here the honest measurement is different, because the failure is in the schema rather than the ranking:

$$
\text{recall}_{\text{schema}} = \frac{\left|\{\text{episodes findable by any query}\}\right|}{\left|\{\text{episodes that genuinely match}\}\right|}
$$

If the attribute is not recorded, this is zero, and no ranking improvement moves it.

### The question the schema cannot ask — measured

This lesson's archive holds 1,500 episodes, and the safety team's question —
*find every episode where the robot yielded to a pedestrian approaching from
the left* — has exactly 122 true answers sitting in the raw logs. Here is
what each schema can do about it:

| Schema | Fields indexed | Targeted result | Raw logs scanned |
|---|---|---|---|
| v1 | weather, version, outcome | **nothing expressible** — nearest query returns all 1,500 | 1,500 |
| v2 | v1 + ped_present, ped_from_left, yielded | **exactly the 122**, verified against ground truth | 122 |

The v1 index is not wrong; it is *mute*. The pedestrian information exists in
every raw log — the archive faithfully stored it — but the index can only
answer questions phrased in the fields somebody chose to extract, and nobody
chose these. Answering the safety question under v1 means a full scan of
1,500 raw episode logs, which at fleet scale is a reprocessing job measured
in days and dollars; under v2 it is an index lookup touching 122 records.

The asymmetry to internalise: **storage keeps everything, but the schema
decides what you can find**, and the questions that matter most — the safety
inquiries, the regulator's request, the incident retrospective — are
precisely the ones nobody anticipated at schema-design time. That is why
lesson 12.3's migration machinery exists, why raw logs are kept even though
they are painful to scan, and why "add it to the schema when someone asks"
means every novel question costs one full-fleet reprocess before it costs
anything else.

## D. From ML to robotics

Standard data-engineering practice transfers wholesale — inverted indexes, columnar stores, partitioning, bucketing. Three things are specific enough to catch you:

- **The unit is the episode, not the row.** An episode is a variable-length correlated sequence, and a query returns whole episodes. Row-oriented thinking makes you index frames and then discover you cannot express "an episode in which X happened at any point."
- **Time has several meanings.** Sensor capture time, message receipt time, monotonic clock, wall clock. Index on the wrong one and your "episodes from Tuesday" quietly includes anything whose upload was delayed. [7.5](../07-perception/05-bev-fusion.md) met this as a fusion bug; at fleet scale it is a data bug.
- **The robot is part of the key.** Software version, calibration id, hardware revision, tyre wear. An episode without those is not reproducible and barely interpretable, and they are exactly what nobody thinks to log until an incident makes them necessary.

## E. Practice

<code-exercise src="dat-l1-index"></code-exercise>

<code-exercise src="dat-l1-schema-recall"></code-exercise>

## F. In production

Parquet plus a metadata catalogue is the default and is usually right. MCAP has become the standard robotics log container and carries per-channel schemas, which matters for [12.3](../../curriculum.md). Foxglove and rerun.io are the common viewers, and both index on ingest.

The practices that separate teams who can answer questions from teams who cannot:

- **Extract derived features at ingest, not at query time.** You will reprocess the archive far less often than you think, and every reprocess costs a week.
- **Index the *outcome*, not only the inputs.** "Episodes that ended in a disengagement" is the query people actually run, and it requires deciding what counts as a disengagement before you need it.
- **Keep a query log.** The questions people ask are the specification for next quarter's schema, and they are free to collect.

## G. Experiment

Take a synthetic archive and ask a question the schema cannot answer, then measure what it costs to make it answerable: reprocess raw episodes to extract the missing attribute, rebuild the index, re-query. Time each stage. The index rebuild is seconds and the reprocess is the whole afternoon — which is exactly the argument for spending an hour on the schema before the first robot ships.

## H. Failure modes

- **The unaskable question.** The attribute was never recorded; recall is zero and the result set looks normal.
- **Indexing on receipt time.** Delayed uploads land in the wrong day, and the bug appears only for the episodes you most want — the ones from a robot with a connectivity problem.
- **Exact float keys.** `speed=1.2000001` matches nothing. Bucket numeric attributes.
- **Intersecting largest-first.** Correct results, needlessly slow; start from the most selective term.
- **An index that outlives its schema.** Rebuild it when the extractor changes, or it silently answers using last year's definitions.

## I. Questions

<quiz-bank src="dat-l1-quiz"></quiz-bank>

## J. References

- Kleppmann, *Designing Data-Intensive Applications*, ch. 3 — storage and retrieval; the index material transfers directly.
- MCAP specification — the robotics log container, and the schema-per-channel design is worth understanding before you pick a format.
- Foxglove documentation on data management — an unusually concrete description of what fleet-scale indexing looks like in practice.
- Zaharia et al., *Delta Lake* (2020) — versioned tables over object storage, which is the shape most robotics archives converge on.

## K. Graded work & portfolio extension

**Graded:** the two exercises above.

**Portfolio:** take your capstone's evaluation runs, define a five-field episode schema, and build the index and query tool over a few hundred episodes. Then write down three questions your schema *cannot* answer and what recording them would have cost. That last list is the artifact — it demonstrates you understand that the design decision happens before the data exists.
