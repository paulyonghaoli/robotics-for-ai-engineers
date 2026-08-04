# 12.3 Schema evolution and the archive that reads wrong

**Status:** Code verified · **Prereqs:** lesson 12.1 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13, NumPy ≥ 1.26

---

## A. Why this matters

Eighteen months ago someone changed `speed` from metres per second to kilometres per hour. It was a good change, correctly reviewed, and every consumer was updated the same week.

Everything written before that date is still in the archive, still parses cleanly, and is now wrong by a factor of 3.6. Nothing errors. The training set built last quarter drew from both eras.

This is the failure mode that makes schema evolution different from ordinary versioning: **a stale reader does not crash, it misinterprets.** An unreadable file gets noticed in minutes. A file that reads successfully with the wrong meaning survives into a model, a metric, and a decision — and by the time it surfaces the provenance is gone.

## B. Mental model

**Three kinds of change, and only one of them is safe.**

| Change | Old reader on new data | New reader on old data |
|---|---|---|
| **Add an optional field** | ignores it — fine | field absent — fine, if it has a default |
| **Remove or rename** | missing key — loud failure | missing key — loud failure |
| **Change the *meaning*** | parses — **silently wrong** | parses — **silently wrong** |

The third row is the dangerous one, and it is invisible to every type system. Units, coordinate frames, sign conventions, "is this timestamp capture or receipt", "is yaw measured from north or from the previous heading" — a schema that records types but not *meanings* cannot detect any of it.

**The fix is boring and works: version the schema, store the version in every record, and refuse to read what you do not understand.** A reader that encounters `schema_version=4` when it knows up to 3 must fail, not guess. Guessing is what produced the 3.6× error.

**Migration is a function, not an edit.** `migrate_1_to_2(record)` is testable, reviewable, and composable — `migrate(rec, from=1, to=4)` chains three of them. Editing the archive in place is not any of those, and it destroys your ability to reproduce anything computed before the edit.

## C. Formulation

A record carries its own version:

```
{"schema_version": 2, "speed_mps": 1.4, "t_capture": 1690000000.0}
```

The reader owns a chain of migrations and applies whichever it needs:

$$
\text{read}(r) = m_{k-1 \to k} \circ \cdots \circ m_{v \to v+1}\,(r)
\quad\text{where } v = r.\text{schema\_version}
$$

Three properties are worth enforcing in tests rather than in review comments:

1. **Total.** Every version from the oldest in the archive to current has a path. A gap means a silent subset of your data is unreadable — or worse, readable by an older code path.
2. **Pure.** A migration returns a new record. In-place mutation means running the chain twice gives a different answer than running it once, and something will run it twice.
3. **Fail-closed.** An unknown version raises. There is no safe default for data whose meaning you do not know.

## D. From ML to robotics

Schema versioning is standard data engineering, and robotics adds two things that make the *meaning* changes much more common than in a typical warehouse.

- **Physical quantities carry units and frames**, and both get changed by well-intentioned people. `position` in the map frame versus the odom frame is a rename that never happens — the field keeps its name and changes what it means.
- **The archive spans hardware revisions.** The same field can be produced by a different sensor with a different convention. The record needs to say which, or the migration has nothing to key on.

The habit worth importing from ML: **treat the dataset as an artifact with a version, not as a directory.** The question "which model saw which data" should have an answer that survives the people who built it, and that answer is a schema version plus a content hash rather than a folder name and somebody's memory.

## E. Practice

<code-exercise src="dat-l3-migrate"></code-exercise>

## F. In production

- **MCAP and Protobuf/Flatbuffers carry schemas in-band.** Use it; a self-describing log is worth the bytes.
- **Never edit the archive in place.** Migrate on read, or write a new versioned copy. The old bytes are the only thing that can adjudicate a dispute later.
- **Put the units in the field name.** `speed_mps` cannot silently become km/h — a change of meaning forces a change of name, which forces the loud failure you want.
- **Record the producer version**, not just the schema version. Two robots on different software can write the same schema with different bugs.
- **Test the migration chain end to end**, from the oldest version in the archive to current, on real old records rather than synthetic ones.

## G. Experiment

Take a hundred records at version 1, migrate to version 3, and compare against a hundred records written natively at version 3. They should agree exactly. Then delete one migration from the chain and confirm the reader fails loudly rather than producing a plausible answer — the failure mode you are buying is the one where it *doesn't* fail, so it is worth checking that it does.

## H. Failure modes

- **Meaning changed, name kept.** Units, frames, conventions. Everything parses; nothing is right.
- **A missing link in the chain.** Version 2 records exist and no `2→3` migration does, so they are quietly skipped or read by the wrong path.
- **Defaults that lie.** Filling an absent field with `0.0` instead of `None` turns "we did not measure this" into "we measured zero" — the same bug as [7.6's](../07-perception/06-lab-perception-lied.md) safe default, at rest instead of in flight.
- **In-place mutation in a migration.** Chains stop being idempotent, and re-reads disagree with first reads.
- **Migrating the archive instead of the reader.** Fast, irreversible, and it destroys the ability to reproduce anything computed before the change.

## I. Questions

<quiz-bank src="dat-l3-quiz"></quiz-bank>

## J. References

- Kleppmann, *Designing Data-Intensive Applications*, ch. 4 — encoding and evolution; the forward/backward compatibility framing is the standard one.
- Protocol Buffers documentation on updating message types — the rules, and why field numbers matter more than field names.
- MCAP specification — per-channel schemas in a robotics log container.
- Confluent's Schema Registry compatibility modes — a good taxonomy of what "compatible" can mean, and the fact that it needs a taxonomy at all is the point.

## K. Graded work & portfolio extension

**Graded:** the exercise above.

**Portfolio:** version your capstone's episode records, write the migration chain, and add a test that reads the oldest format you ever wrote and checks it against a freshly-written record of the same episode. The interesting artifact is the test, not the migration — it is evidence that you know a schema change is a data-integrity event rather than a code change.
