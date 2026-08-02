# 3.6 Lab: catching a lying filter

**Status:** Code verified · **Prereqs:** lessons 3.1–3.5 · **Time:** ~2 h · **Verified:** 2026-08-02, Python 3.13, NumPy ≥ 1.26

---

## A. Why this lab exists

Module 3's through-line has been that a filter's *accuracy* and its *honesty* are different properties. This lab makes you the auditor. You get filters that all look fine by RMSE; your job is to read their consistency statistics and name the lie — the estimation counterpart of Module 1's frame-debugging gauntlet.

**The two instruments:**

- **NEES** (normalized estimation error squared), \((x - \hat{x})^\top P^{-1} (x - \hat{x})\): needs ground truth → simulation-time tool. Should average the state dimension.
- **NIS** (normalized innovation squared), \(y^\top S^{-1} y\): needs only the measurements → runtime tool, your production dashboard. Should average the measurement dimension.

Both are χ²-distributed for a consistent filter. **Above the band: overconfident** (P too small — the dangerous direction: downstream consumers trust a lie). **Below the band: pessimistic** (P too large — wasteful, masks real information). And a *biased* innovation mean signals a modeling error no covariance tuning can fix (lesson 3.1, section H).

## B. The diagnostic table

| Observation | Diagnosis |
|---|---|
| NEES ≈ n, NIS ≈ m, innovations zero-mean & white | Healthy — leave it alone |
| NEES ≫ n while RMSE looks fine | Overconfident (Q or R too small) — the deferred failure |
| NEES ≪ n | Pessimistic (Q or R too large) — laggy, wasteful |
| NEES bad, **NIS perfectly fine** | The state is wrong in a way the measurements *cannot reveal* — an unobservable error (e.g. a constant sensor offset the filter absorbed). **Runtime monitoring will never catch this**; only ground truth does. The single strongest argument for simulation-time auditing. |
| NIS fine, NEES bad, process-driven | Measurement trust OK; *process* model at fault (Q) |
| Innovation mean ≠ 0, persistent | Bias: sensor offset, wrong H, frame bug — go to Module 1, not the tuning knobs |
| Innovations autocorrelated (not white) | Unmodeled dynamics — the filter is systematically late |

## C. The gauntlet

### Case 1: audit four filters

<code-exercise src="est-l6-nees"></code-exercise>

### Case 2: fix the tuning to pass the bands

<code-exercise src="est-l6-tune"></code-exercise>

## D. Diagnosis drills

<quiz-bank src="estimation-l6-drills"></quiz-bank>

## E. Debrief

The auditor's procedure, portable to any filter you ever meet: (1) compute NIS from logs — no ground truth needed; (2) check mean against the χ² band *and* check for bias and autocorrelation; (3) only then touch Q/R — and remember the asymmetry: pessimism costs performance, overconfidence costs *trust*, and every consumer downstream of P inherits the lie. In simulation, add NEES; on hardware, NIS is what you have — which is why `robot_localization` exposes innovation monitoring and why Module 10's fleet dashboards chart it.

## F. Graded work & portfolio extension

**Graded:** the localization project's consistency stretch goal uses exactly these bands.

**Portfolio:** wire NIS monitoring into the capstone's PF stack and plot it through the field-note failures (the max-range bug would have *screamed* on this chart, long before the 16 m divergence) — monitoring that would have caught a real bug is the best possible demo of why monitoring matters.
