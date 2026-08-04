# 12.4 Lab: the dataset that could not be rebuilt

**Status:** Code verified · **Prereqs:** lessons 12.1–12.3 · **Time:** ~2 h · **Verified:** 2026-08-03, Python 3.13

---

## A. Why this lab exists

Nothing is broken. No disk failed, no file is corrupt, and the archive holds every episode the fleet has ever run.

Seven people ask seven reasonable questions in one week and six of them cannot be answered. That gap — between "we have the data" and "we can answer the question" — is what this module has been about, and this lab is where the bill arrives. Every failure below was created months or years earlier by a decision that looked free at the time.

The other labs in this curriculum hand you a broken thing to fix. This one hands you a working system and asks what it cannot do, which is a harder thing to see and the more useful skill.

## B. The diagnostic table

| Symptom | Cause | Lesson |
|---|---|---|
| The dataset was defined by a filter; re-running it gives a different set | **Unpinned manifest** — a description is not a dataset | [12.3](03-schema-evolution.md) |
| Episodes pinned and present, re-run gives a different number | **Nondeterministic harness** — nothing to compare against | [12.2](02-replay-determinism.md) |
| The field the question needs does not exist in any record | **Not recorded** — no compute recovers it | [12.1](01-indexing.md) |
| The field exists on part of the archive | **Partially recorded** — computable, and about a different population | [12.1](01-indexing.md) |
| One concept, two spellings, two units | **Unit mixture** — the aggregate is wrong and looks fine | [12.3](03-schema-evolution.md) |
| Joined against a table describing the fleet *now* | **Stale join** — state-at-capture was never recorded | [12.1](01-indexing.md) |

## C. The week's requests

Seven requests, one archive, two years, two schema versions.

<code-exercise src="dat-l4-archive"></code-exercise>

The verdicts you should arrive at:

| request | diagnosis | evidence |
|---|---|---|
| R1 rebuild the v3.2 training set | unpinned-manifest | 37 episodes at build, 40 today |
| R2 pedestrian approached from the left | not-recorded | coverage 0.00 |
| R3 reproduce the published 0.94 | nondeterministic | pinned and present, still moves |
| R4 mean speed | unit-mixture | coverage 1.00, two spellings |
| R5 episodes on the recalled lidar | stale-join | 35% of episodes predate their own hardware entry |
| R6 takeover rate | partially-recorded | coverage 0.45 |
| R7 episodes per robot | **answerable** | full coverage, one spelling, no join |

Two of these are worth sitting with.

**R4** is the only one that produces a number. Coverage is 1.0, the mean computes, and it is wrong — an average of metres per second and kilometres per hour. The thing that saved you is not a validator; it is that the two eras happened to use two different *names*. Had both been called `speed`, nothing anywhere in the stack would have flagged it, and the number would have gone into a slide.

**R7** matters because it is answerable. A data platform that returns a number for every question is not trustworthy on any of them, and the credibility of the one clean answer comes entirely from having said "no" to the other six.

## D. Diagnosis drills

<quiz-bank src="dat-l4-drills"></quiz-bank>

## E. Debrief

Three habits close out the module.

**1. Pin datasets by content, not by description.** A filter is not a dataset. It is a function whose output depends on the archive's state when you run it, and the archive's state changes. An immutable manifest — a list of episode ids and a content hash — costs a few lines and is the precondition for everything else here: "reproduce this result" has no meaning until "this" refers to a fixed set of bytes.

**2. Record the state at capture, not the state today.** The hardware table, the calibration, the config, the software version: all of them are mutable, all of them get joined against later, and all of them are wrong for historical data. Stamping the value into each record is redundant and cheap; maintaining a table with validity intervals is elegant and nobody does it correctly. Prefer the redundant version.

**3. Partial coverage is the dangerous case, not zero coverage.** Zero coverage announces itself — the field is not there, and you go and add it. Partial coverage computes an answer about whichever subset happened to record the field, and that subset is never random: it is the newer software, the newer robots, the newer routes. The probe is the same one line in every case, and running it before answering is the whole discipline.

And the thread through Module 12: **every one of these failures was created by someone with good intentions and no downside in view.** Nobody chose not to record pedestrian approach direction; it just was not on the list. Nobody chose an unpinned manifest; a filter was the obvious way to describe a dataset. The reason to learn this module is that the cost lands two years later, on somebody who cannot fix it.

## F. Graded work & portfolio extension

**Graded:** the seven-request triage. The probes transfer directly — `coverage`, `spellings_used`, and a stale-join check are worth running against any dataset before you report a number from it.

**Portfolio:** run the same triage against your own capstone archive. Write down five questions you would want to ask about it in a year — not the ones you can answer now — and check which are already impossible. Then fix the cheap ones: pin the manifests, stamp the config hash and stack version into every episode record, and add the one field whose absence would hurt most. The interesting artifact is the list of questions you found you *could not* answer, since that is the analysis nobody does until it is too late to act on.
