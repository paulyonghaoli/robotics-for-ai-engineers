# Robotics for AI Engineers — Master Plan

**Version:** 1.1 (open questions resolved; video + industry-tooling strategy added) · **Date:** 2026-08-01 · **Status:** governing document — supersedes the original ChatGPT outline; update this file when scope decisions change.

---

## 1. Vision and scale calibration

Build a graduate-level, textbook-scale, *interactive* curriculum equivalent to **6–9 semester credits** (2–3 graduate courses) for ML/DS/DE engineers transitioning into robotics — with every practice element executable: clickable-answer questions, interactive multiple-choice, DataCamp-style in-browser coding, and OMSCS-style autograded projects.

### What 6–9 credits actually means

| Unit | Standard | This project |
|---|---|---|
| 1 graduate credit | ≈ 45 hrs total learner work | — |
| 3-credit course | ≈ 135 hrs (lectures + homework + projects) | 1 "course" = 3–4 modules + 1 graded project sequence |
| 9 credits | ≈ 405 hrs learner work | 3 courses, 10 modules, 4 capstones |
| Major textbook | 600–900 pages | ~75 lessons × 2,500–4,000 words ≈ 700+ page-equivalents |

### The three-course program

| Course | Credits | Modules | Flagship assessment |
|---|---|---|---|
| **I. Foundations of Embodied AI** | 3 | 0 Transition · 1 Geometry · 2 Kinematics & Control · 3 State Estimation | Autograded localization project (GPS+IMU fusion, kidnapped robot) |
| **II. Robot Autonomy** | 3 | 4 Mapping & SLAM · 5 Planning & Decision-Making · 6 ROS 2 | **Capstone 1:** autonomous 2D mobile robot, scenario-scored |
| **III. AI Robotics Systems** | 3 | 7 Perception · 8 Manipulation · 9 Robot Learning · 10 Production Robotics | **Capstones 2–4:** perception stack, robot-learning task, language-conditioned agent |

Honest effort accounting (author side): a full 9-credit interactive textbook is **1,500–2,500 authoring hours**. At 5–7 hrs/week solo that is 5–8 years; with AI-assisted drafting + human verification (the actual workflow), a realistic target is **Course I in ~6 months, Course II in ~12–14 months, Course III in ~24+ months**. Every phase below is independently shippable and portfolio-worthy — the plan's job is to make sure nothing depends on finishing everything.

---

## 2. Assessment system — four tiers

Every lesson and module draws from these four tiers. This is the core product differentiator; design it once, reuse everywhere.

### Tier 1 — Inline concept checks (clickable reveal)
- Short questions embedded in lesson prose; answer hidden behind a click (`pymdownx.details` — already working).
- Zero infrastructure. Target: **4–8 per lesson**.

### Tier 2 — Interactive multiple-choice quizzes
- Rendered by a custom `<quiz-question>` web component; instant grading, per-option explanations (why each distractor is wrong), retry, shuffle.
- Question banks authored as **YAML files** (`curriculum/<module>/questions/*.yaml`), one bank per lesson + a module-level exam bank. Schema: `id, type (single|multi|numeric), prompt (md), options[{text, correct, explanation}], difficulty, tags, source_lesson`.
- Progress stored in `localStorage` (no accounts, no backend); a "My progress" page aggregates it client-side.
- Target: **8–12 per lesson**, plus **25–40 per module exam** → ~900 questions at full scale (write ~450 for Courses I–II first).

### Tier 3 — In-browser coding exercises (DataCamp-style)
- A `<code-exercise>` component: CodeMirror 6 editor + **Pyodide** (CPython in WebAssembly) running in a Web Worker. NumPy, SciPy, and matplotlib (canvas backend) all run in Pyodide — which covers Modules 0–5 and parts of 7 completely.
- Exercise spec (YAML): `starter_code, setup_code (hidden), tests (pytest-style asserts run client-side), hints[] (progressive), solution, expected_plot (optional)`.
- Grading model = DataCamp's: run hidden asserts against the learner's namespace; show which assertion failed with a friendly message.
- Hard limits acknowledged: no ROS 2, no PyTorch, no Gazebo in the browser. Anything heavier than NumPy-scale escalates to Tier 4.
- Target: **2–3 per lesson** in Modules 1–5 (~120 exercises), fewer elsewhere.

### Tier 4 — Autograded projects (OMSCS-style)
- Modeled on Georgia Tech's model (Gradescope/RAIT courses): submit code, get a score from a test harness, iterate.
- **Local-first:** each project is a template repo (or `projects/<name>/` folder) with `python -m grader` that runs the public rubric and prints a score breakdown — self-learners get the full OMSCS feedback loop with zero infrastructure.
- **CI mirror:** GitHub Actions runs the same grader on push (GitHub Classroom-compatible for future cohorts; Classroom's autograding consumes exactly this shape).
- **Anti-memorization without hidden tests:** randomize scenario parameters per run (seeded); publish the rubric, not fixed expected outputs. Hidden-test infrastructure is deferred until there's a cohort to protect.
- **Capstone scoring = closed-loop scenario evaluation** (the most OMSCS-like part): `python -m eval run scenarios/` executes the learner's stack headless across N randomized worlds and scores metrics against rubric thresholds:
  - goal success rate ≥ X → 30 pts, collision rate ≤ Y → 20 pts, localization RMSE ≤ Z → 20 pts, planning latency ≤ L → 15 pts, code quality gates (ruff, tests) → 15 pts.
- Target: **1 autograded mini-project per module** (10) + **4 capstones**.

---

## 3. Platform architecture

### Decision: stay on MkDocs Material; build interactivity as framework-agnostic web components

- Interactive components (`quiz-bank`, `code-exercise`) are **dependency-free vanilla JS** in `docs/javascripts/interactive.js` — no build step at all (decided during P1: keeps the toolchain Python-only; CodeMirror 5 and Pyodide load from CDN). They mount from ordinary markdown as raw HTML custom elements (`<quiz-bank src="ID">`), reading JSON that a MkDocs hook generates from the YAML sources at build time.
- Rationale: keeps authoring in markdown (the bottleneck is content, not framework), keeps the site static/free to host, and — because web components are framework-agnostic — **survives a future migration to Docusaurus** if community features ever demand React. Revisit only if/when that happens.
- Everything runs client-side: **no backend, no accounts, no cost**. Progress is `localStorage` + optional export/import as JSON.

### Repo additions

```
apps/interactive/          # web components (TS), esbuild bundle
curriculum/<module>/
  questions/*.yaml         # tier-2 banks
  exercises/*.yaml         # tier-3 specs
projects/<name>/
  grader/                  # tier-4 public rubric tests
  scenarios/               # randomized eval worlds
tools/
  validate_content.py      # CI: schema-check YAML, run every exercise's solution against its own tests
```

### Content-integrity CI (non-negotiable)
Every PR runs: pytest on `robotics_ai/` · ruff/mypy · mkdocs build --strict · **every Tier-3 exercise's reference solution executed against its own tests in Pyodide-equivalent env** · every Tier-2 bank schema-validated · every project grader run against its reference solution. Interactive content that can silently break is worse than static content.

---

## 4. Full content inventory (textbook scale)

Lesson = 2,500–4,000 words following the A–K schema (see CONTRIBUTING.md). Counts are targets; hours are learner-side.

### Course I — Foundations of Embodied AI (3 cr ≈ 135 hrs)

| Module | Lessons | Learner hrs |
|---|---|---|
| **0 · From ML to Robotics** — what changes when models move mass; anatomy of an autonomy stack; closed-loop vs offline eval; roles field guide; math diagnostic | 5 | 12 |
| **1 · Geometry & Motion** — frames & SE(2) ✅; 3D rotations & quaternions; transform trees; twists/velocities; C-space; frame-debugging lab | 6 | 20 |
| **2 · Kinematics & Control** — FK; IK (numeric); Jacobians; dynamics intuition; PID deep-dive; trajectory tracking; diff-drive control; MPC intro | 8 | 30 |
| **3 · State Estimation** — uncertainty & sensor models; Bayes filter; KF; EKF; UKF; particle filter; IMU + fusion; consistency/NEES lab | 8 | 33 |
| Module projects (4 × autograded) + Course I exam banks | — | 40 |

### Course II — Robot Autonomy (3 cr ≈ 135 hrs)

| Module | Lessons | Learner hrs |
|---|---|---|
| **4 · Mapping & SLAM** — occupancy grids; inverse sensor models; scan matching/ICP; landmark EKF-SLAM; pose graphs & loop closure; VO overview | 7 | 28 |
| **5 · Planning & Decision-Making** — search & A*; C-space obstacles; potential fields; PRM; RRT/RRT*; trajectory optimization; local vs global; behavior planning; planning under uncertainty | 9 | 32 |
| **6 · ROS 2** — architecture & DDS; nodes/topics/QoS; services & actions; TF2; URDF; launch & lifecycle; bags & observability; C++ nodes; testing | 9 | 30 |
| **Capstone 1: Autonomous 2D robot** (scenario-autograded) | — | 45 |

### Course III — AI Robotics Systems (3 cr ≈ 135 hrs)

| Module | Lessons | Learner hrs |
|---|---|---|
| **7 · Perception** — camera models & calibration; stereo; optical flow; features & pose; point clouds; PointNet; PointPillars/BEV; camera-LiDAR fusion; tracking | 9 | 35 |
| **8 · Manipulation** — arm kinematics; grasping; collision-aware planning; pick-and-place; force/impedance; visual servoing; TAMP | 7 | 25 |
| **9 · Robot Learning** — imitation (ACT + mini diffusion policy); **the data engine & human-in-the-loop** (interventions, DAgger, dataset hygiene); RL for control; sim-to-real & domain randomization (on our own harness); **world models** (learn the capstone sim's dynamics, plan through it with 2.6's sampling MPC); **VLAs** (π0/OpenVLA-class: inference + honest closed-loop eval, not training); safety & generalist-policy evaluation. Frontier landscape + placement rationale: `docs/frontier.md` (living doc, re-audited per release) | 8 | 30 |
| **10 · Evaluation & Data Systems** — statistical rigor for robot claims (episodes-per-claim, CIs, perturbation testing); scenario-suite design; regression from logs/bags; dataset lifecycle, curation & provenance; drift monitoring; neural real-to-sim evaluation | 7 | 22 |
| **11 · Deployment, Fleet & Safety** — latency budgets; CPU/GPU allocation; edge inference & quantization; model rollout/rollback; fleet telemetry; safety cases for learned components; incident forensics | 7 | 20 |
| Capstones 2–4 (perception stack; robot-learning task; language-conditioned agent) | — | 25 |

**Program totals:** ~83 lessons · ~900 MCQs · ~150 in-browser exercises · 14 autograded artifacts · ≈ 405 learner-hours ⇒ **9 credits defensible** (Courses I+II alone ⇒ 6).

---

## 5. Phased roadmap

Ship order optimizes for: (a) the interaction platform proven early on existing content, (b) each phase independently portfolio-worthy.

| Phase | Contents | Exit criterion |
|---|---|---|
| **P1 — Interactive platform MVP** (platform ✅ 2026-08-01; Module 1 lessons 1.3–1.6 remaining) | `quiz-bank` + `code-exercise` components, YAML schemas, Pyodide worker, content-integrity CI ✅; lesson 1.1 retrofitted with all four tiers ✅; frame-transforms mini-grader ✅; lesson 1.2 quaternions ✅; still to do: lessons 1.3 transform trees, 1.4 twists, 1.5 C-space, 1.6 debugging lab | A stranger can read 1.1, answer MCQs, write+run code in the page, and locally grade a mini-project — **verified end-to-end in browser** |
| **P2 — Course I beta** ✅ **COMPLETE 2026-08-02** | Modules 0–3 fully live (16 lessons), all with quiz banks + in-browser exercises; `robotics_ai.control` + `robotics_ai.estimation` libraries; localization autograded project; consistency lab; math diagnostic; Course I exam form A (16 cross-module questions). 25 banks / 36 exercises / 96 tests, all CI green | Course I ≈ 135 learner-hrs, all CI green — **met** |
| **P3 — Course II / v1.0** ✅ **COMPLETE 2026-08-02** | Modules 4, 5, 9, 10, 11 live (48 lessons total across the curriculum, 56 quiz banks, 71 exercises). Capstone v0–v4 all passing: v1 PF localization 6–11 cm; v2 online mapping 20/20; v3 dynamic obstacles 18/18 at six movers; **v4 SLAM — no map and no pose sensor — 18/24, 0.387 m drift, scored on its own published envelope**. `robotics_ai.planning` + `.mapping`; thirteen debugging field notes in docs/capstone-log.md; `slam_ablation.py` reproduces v4's design decisions with the controller loop cut. Site live on Cloudflare, nine CI gates green via `tools/verify.py`. | End-to-end nav stack scored by `python -m eval`; 6-credit claim defensible — **met** |
| **P4 — Course III** (next) | Module 7 (perception — leverages PointPillars background), Module 8 (manipulation), Module 6 (ROS 2 parallel track, needs the WSL2/devcontainer decision), **capstone v5 = loop closure + pose graph**, which is the specific thing v4's measured envelope says is missing | 9-credit program complete |
| **Continuous** | Question-bank growth, community PRs, version re-verification (pinned ROS distro checks) | — |

**Not building** (unchanged from v0 plan, now with one exception): accounts, backends, LMS, certificates, forums, monetization, humanoids. *Exception:* interactivity and autograding are now in scope — but strictly in their zero-backend forms above.

---

## 5b. Structural decisions (2026-08-02, from the frontier research)

Three changes to the original ten-module outline, each justified by [docs/frontier.md](docs/frontier.md):

1. **Module 10 split into 10 (Evaluation & Data Systems) and 11 (Deployment, Fleet & Safety).** The research ranks evaluation and data infrastructure as the highest-leverage area for this audience — corroborated by real job postings (Figure's data-infrastructure role: $150–400k, *no ML modeling required*). Seven lessons could not carry both halves. **Module 10 is being written early, out of numerical order**, because the capstone harness already exists as its lab.
2. **Module 6 (ROS 2) becomes a parallel track, not a sequential gate.** Everything through the capstone runs in pure Python; gating learners behind a WSL2/Docker install mid-curriculum creates a drop-off cliff for no pedagogical gain. Evidence it isn't universal: ROS 2 is mandatory at Agility/Boston Dynamics/Amazon and absent from frontier VLA-lab postings. Also unblocks the launch critical path.
3. **The diagnostic lab becomes a standard module element.** Lessons 1.6 and 3.6 are the most distinctive pages on the site; the pattern was accidental. Module 4 (SLAM failure gallery) and Module 5 (planner pathologies) labs are queued.

## 6. Resolved questions (decided 2026-08-01)

1. **Numeric-entry questions** — ✅ in scope: Tier-2 schema gets `type: numeric` with `answer`, `tolerance` (absolute or relative), and unit hint in the prompt.
2. **matplotlib in Pyodide** — attempt canvas backend per-exercise; on any flakiness, fall back to compute-only checks + static reference plots. Never let a plot block an exercise from grading.
3. **C++ exercises** — Tier 4 only (autograded repos with gtest); no in-browser C++.
4. **Cohort mode** — deferred until a real cohort exists.

## 7. Video strategy

Text + interactive execution is the product; video is a supplement and never on the critical path.

- **NotebookLM (auto-generated):** feed each module's finished lessons in and generate Audio/Video Overviews as *optional recap material*, clearly labeled "AI-generated summary." Cheap (minutes per module), fine for commute-style review. **Not** used for primary instruction: no control over technical precision (frame-convention errors would be poisonous), weak math rendering, and — for a portfolio project — AI-narrated slideware demonstrates nothing about the author. Regenerate only when a module's content changes materially.
- **Authored videos (high value, small number):** screen recordings of the actual systems running — capstone demo runs, RViz/Foxglove sessions, failure-mode reproductions, PID tuning live. These are the videos employers and learners actually watch, and they cannot be generated. Target: 1 module-intro or demo video per module (~10 total), recorded at phase boundaries (P2/P3), OBS + scripted narration.
- Later polish (P4+, optional): manim-style math animations for the geometry/estimation derivations.

## 8. Industry tooling threads (trending + job-posting-driven)

Tools are woven into existing modules (mostly sections F "framework implementation" and Tier-4 projects), not added as new modules. Each is tagged **[working-skill]** (learner builds with it, appears in projects/autograders) or **[awareness]** (survey lesson section + annotated references only) — this tiering is the guard against scope explosion.

| Module | Working-skill | Awareness |
|---|---|---|
| 3 · Estimation | — | robot_localization (ROS 2 EKF/UKF stack) |
| 4 · SLAM | — | slam_toolbox, Cartographer, ORB-SLAM3 lineage |
| 5 · Planning | **Nav2** (costmaps, planner/controller servers, behavior trees) | BehaviorTree.CPP |
| 6 · ROS 2 | **Foxglove** (viz/observability), **MCAP** (bag format), **ros2_control** basics, colcon/rosdep, **Eigen + gtest** in the C++ lessons | Zenoh RMW, micro-ROS |
| 7 · Perception | **PyTorch**, **Open3D**, one public AV dataset (**nuScenes** mini) for the 3D-detection labs | SAM 2 / Grounding DINO (open-vocab detection), Depth Anything, DINOv2 features, 3D Gaussian Splatting / NeRF |
| 8 · Manipulation | **MoveIt 2** for the pick-and-place project | Task-and-motion-planning frameworks |
| 9 · Robot learning | **MuJoCo** (+ MJX note), **LeRobot** (HF) for imitation-learning labs — ACT and **diffusion policy** implemented at mini scale; **Isaac Lab** for the RL track | π0 / OpenVLA / RT-x-class VLAs (paper-reading + inference-only demo), Genesis, world models |
| 10 · Production | **Docker/devcontainers**, **ONNX Runtime export + quantization** lab, Foxglove data review, **rerun.io** for custom viz | TensorRT/Jetson edge pipeline (hardware-dependent), fleet frameworks |

Job-posting alignment (what these choices target): *Perception* — C++/Eigen, PyTorch, ROS, CUDA-awareness, AV datasets. *Autonomy* — Nav2, ROS 2, behavior trees, C++. *Robot learning* — MuJoCo/Isaac, LeRobot ecosystem, diffusion policies, VLAs. *Platform* — Docker, DDS/middleware, bags/MCAP, observability, edge inference. Re-audit this table against live postings once per phase; trending tools churn fast, so [awareness] items may be swapped freely, [working-skill] items only at phase boundaries.
