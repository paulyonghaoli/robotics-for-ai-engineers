# The frontier: where robotics is going (and where you fit)

**Living document · Researched 2026-08-02** (~250 web searches across models, data/sim infrastructure, industry deployment, and academic open problems). Frontier content churns fast: names here are coordinates, not gospel. Claims are marked **[V]** verified against primary sources, **[C]** company claim unverified externally, **[U]** single/secondary source — treat with suspicion.

---

## The one-sentence summary

**In 2026 the field's self-diagnosis inverted: the bottleneck is no longer architecture or compute — it is data composition, evaluation rigor, and reliability.** Everything below follows from that, including why an ML/data engineer is unusually well-positioned right now.

---

## 1. The evaluation crisis (read this first)

This is the most important development of 2026 and the least covered in popular writing.

**The numbers** (from *"What Are We Actually Benchmarking in Robot Manipulation?"*, [arXiv:2606.04233](https://arxiv.org/pdf/2606.04233), TTIC/UChicago, June 2026, plus a corpus analysis of [1,228 VLA papers](https://labelstud.io/blog/vla-robot-data-problem/)):

- **Only ~20% of state-of-the-art claims** on the two dominant benchmarks (LIBERO, SimplerEnv) are **provably statistically significant**. Most papers report a bare success rate with no confidence interval. [V]
- **LIBERO success collapses from ~95% to under 30%** under modest perturbations — camera viewpoint, initial robot state. Some models were shown to execute by **memorizing trajectories rather than using visual feedback**. [V]
- A **0.09B-parameter probe with no language encoder and no robotics pretraining** scores at or near the best reported LIBERO result. [V]
- **79 papers reported LIBERO results in March 2026 alone**; 300+ overall. Treat any 2026 paper leading with a LIBERO number as uninformative.
- Real-world evaluations typically use **≤25 rollouts with no confidence intervals**. [V]
- On **VLA-REPLICA** ([arXiv:2605.20774](https://arxiv.org/html/2605.20774)) — a deliberately cheap ($1,050), reproducible standardized rig — the best model scores **54% in-distribution**: π0.5 54%, π0 34%, SmolVLA 26%, ACT 18%. [V]

**What's emerging in response:** [RoboArena](https://arxiv.org/abs/2506.18123) (distributed double-blind pairwise A/B on real hardware, now the de facto real-world ranking), AI2's [`vla-evaluation-harness`](https://github.com/allenai/vla-evaluation-harness) (18 benchmarks, 13+ model servers — the closest thing to `lm-eval-harness` for robotics), [RoboDojo](https://arxiv.org/html/2607.04434v1) (42 sim + 18 real tasks with standardized lighting, reset procedure, and deployment interface).

**A cautionary case study in metric design.** California's AV disengagement reports — the one intervention metric a regulator actually mandates — are nearly useless, and instructively so. They measure the **safety-driver test fleet**: Waymo's 3.3M reported California test miles are a rounding error against the **4M+ fully autonomous miles it drives per week**. "Disengagement" is self-defined with no severity weighting, so a near-miss and a cautious pull-over count identically; a company testing on easy suburban arterials posts better numbers than one probing hard edge cases (Zoox's 60,682 miles/disengagement vs Waymo's 19,234 reflects different operating domains, not 3× the competence); and mature programs look worse precisely because they moved their hard miles to driverless operation, which is excluded. The DMV itself plans to **retire the metric in 2026**. A metric that measures the wrong population, self-defines its event, ignores severity, and rewards easy testing is a design failure worth studying before you write your own rubric.

**Why this matters for you:** the field is desperate for people who can design honest evaluations — scenario suites, confidence intervals, seed sweeps, reference-solution calibration, perturbation testing. That is a *data-engineering and experimental-design* skill, not a modeling skill, and it's in shortage. This curriculum's capstone harness is deliberately built this way; §7 below turns it into an explicit teaching thread.

---

## 2. Data: composition beat volume

The second big 2026 inversion. Specific, load-bearing findings:

- **Negative transfer is real.** Pooling heterogeneous robot datasets can make your model *worse* — naive cross-embodiment scaling has plateaued. [V]
- **A curated 5% coreset recovers 85–90%** of full-dataset performance. Most collected data is dead weight. [V]
- **Collection protocol diversity** (lighting, backgrounds, distractors) is the single largest generalization factor; in-distribution-only data gives near-zero transfer.
- **The language channel is barely used.** Instruction augmentation moved one task **from 0% to 90% success** — meaning language was doing nothing before. Counterfactual relabeling added **+27 points** on navigation *with no new data collection*. [V]
- **Failure data is thrown away.** Pipelines are success-demonstration-centric. Counter-datasets appearing in 2026: RoboFAC (9,440 erroneous trajectories), ViFailback (58,000 failure-diagnosis pairs); AgiBot World 2026 ships explicit error-recovery trajectories.
- **Tactile, force, and audio are nearly absent** from VLA corpora — one 123-paper slice contained *zero* tactile-centric work.
- **Provenance is structurally missing** across the major datasets: no contact-force ledger, no generation lineage, no physics-consistency hash, no failure logs. [U]

**Supply diversified away from teleoperation:** ABC-130K (3,500 hours real teleop with end-effector *forces*, fully open, [arXiv:2606.27375](https://arxiv.org/abs/2606.27375)); million-hour Apache-2.0 egocentric human video; **€490 robot-free handheld collectors** ([Grabette](https://huggingface.co/blog/grabette), HF + Pollen, July 2026) claiming ~3× teleop throughput. Teleop cost fell to roughly **$118/hr fully loaded** [U] but remains the expensive path.

**Standards:** LeRobotDataset won *distribution* (all six major dataset lineages now redistribute through it), v3.0 made multi-TB streaming practical. ISO/WD 26264-1 (humanoid robot datasets) reached Working Draft in June 2026 — the earliest ISO stage, years from binding. [U]

---

## 3. Models: world-action models displaced VLM-backbone VLAs

The 2026 architectural shift is **WAMs** — video-diffusion backbones that denoise video and action tokens jointly, no separate inverse-dynamics module.

| Model | Org | Date | Weights | Note |
|---|---|---|---|---|
| **GR00T N2 / DreamZero** | NVIDIA | announced Mar 2026, ships end-2026 | TBD | Wan-2.1-video backbone; #1 on RoboArena and MolmoSpaces [C] |
| **π0.7** | Physical Intelligence | Apr 2026 | Closed | First credible **compositional generalization**; zero-shot cross-embodiment laundry folding |
| **Gemini Robotics 2** | Google DeepMind | Jul 30, 2026 | Closed (ER 2 preview) | Whole-body control, multi-robot collaboration; On-Device 2 adapts from **<200 examples** |
| **Cosmos 3** | NVIDIA | Jun 2026 | Open (OpenMDW) | Omnimodal: language/image/video/audio/**action** in one model |
| **LingBot-VLA 2.0** | Robbyant | Jul 2026 | **Apache-2.0, 6B** | ~130 ms on an RTX 4090D; 60k hrs |
| **GEN-1** | Generalist AI | Apr 2026 | Closed | Pretrained on **zero robot data** (human wearables only); reports 1 hour of robot data to adapt [C] |

**The cost nobody advertises:** WAMs process ~10× longer token sequences at ~7.4× training cost, and run **590–800 ms per action chunk vs ~190 ms for π0.5** — a 3–4× inference slowdown. [V, NVIDIA's own writeup]

**And the honest capability ceiling**, from DeepMind's own published numbers on Gemini Robotics 2 with dexterous hands: unscrew bulb 92%, but **tie trash bag 44%, ziplock 40%, screw bulb 36%, dustpan 32%**; picking from floor **45.7%**. [V] A task that succeeds 32% of the time is not deployable labor.

---

## 4. The classical comeback is real (and program-level)

This is the finding most likely to surprise someone who reads only AI news — and it directly validates Courses I–II.

- **RSS 2026 ran four explicitly classical/hybrid workshops**: *Sampling-Based Optimization for Robotics*; *The Geometry of Motion: Physics-Informed Structures for Learning and Control*; *Planning and Control with Imperfect Sensors and Perception*; *From Imitation to Certification: Learning, Reasoning, and Formal Methods*. [V]
- **RSS 2026's Test of Time award** went to Deimel & Brock (2014) — the compliant, underactuated **hand**. A morphology-as-computation award in 2026 is a statement.
- **ICRA 2026 award finalists are strikingly hybrid** [V]: *Push Anything* (contact-implicit **MPC**); *ActivePusher* (**residual physics**); *SymSkill* (**neuro-symbolic** co-invention); *Ro-To-Go!* (**signal temporal logic**); *HITTER* (hierarchical planning + learning); dexterity solved at the **mechanism** level via passive rollers; geometry-aware VO with **high-gain observers**.
- **TiPToP** ([arXiv:2603.09971](https://arxiv.org/abs/2603.09971)) composes vision foundation models with **GPU-accelerated TAMP** to solve multi-step manipulation from RGB + language **with zero robot training data** — the strongest single classical-comeback datapoint of the year.
- **The deployed humanoid architecture is MPC + learned residuals**, not a monolithic VLA. [U]
- Ken Goldberg, whose "100,000-year data gap" argument recirculated in June 2026: *"most roboticists still believe in… physics, math, and models of the environment."*

**Everything in Modules 1–5 is on this list.** Geometry, estimation, MPC, sampling-based planning, planning under uncertainty — these are not legacy content the frontier moved past; they are what the frontier is reaching back for.

---

## 5. Reality check: what's actually deployed

| Claim | Verified reality |
|---|---|
| Amazon warehouse robots | **1,000,000+ across 300+ facilities** [V] — the one genuinely huge deployment. But Amazon **shelved its flagship Blue Jay robot in Feb 2026** on manufacturing cost and cut 100+ robotics jobs in March. |
| Waymo | **220.6M rider-only miles** through March 2026; 82% fewer injury crashes vs human benchmark; 11 cities [V]. The only company with real autonomous scale. |
| Figure at BMW | **One robot.** BMW's own release confirms it. Figure is valued at **$39B** with zero named customers and zero disclosed units sold. [V] |
| Agility / GXO | **65,000+ hours across 9 facilities** [V] — the honest counterexample, with customer-side confirmation. Revenue ~$37M against a $2.5B valuation. |
| Tesla Optimus | **Zero.** Musk, Q4 2025: *"not in usage in our factories in a material way."* [V] |
| Boston Dynamics | Marked **flat at ~$3.3B since 2021** in a real cash transaction (Hyundai buying SoftBank's stake) — while pre-revenue Figure is marked at $39B. Private marks here are not price discovery. |

Add: the **first wave of humanoid company shutdowns** began in 2026 — Cartwheel Robotics dead after four years, K-Scale Labs shut with under a month of runway (its post-mortem named **actuator engineering** as the critical unsolved problem). Funding is barbelled (median round $145M, essentially nothing between $20M and $50M). And the volume leader's economics are turning: **Unitree's Q1 2026 revenue grew 68.5% while net profit fell 47.7%** [V, Caixin] — a commoditization signal, not scaling-into-margin.

**Gill Pratt**, who ran the DARPA Robotics Challenge, in IEEE Spectrum (April 2026): *"We are approaching what (I hope!) is a peak of inflated expectations for humanoids."* His technical critique is that current systems are reactive pattern-matchers — *"if I see the world like this, I act on the world like that"* — and his proposed realistic model is explicitly Waymo-shaped: *"most of the time they do their own work, and every once in a while, they raise their hand for help."*

### The intervention-rate blackout

**No humanoid company publishes an intervention or autonomy rate. Not one.** A targeted search across Figure, Tesla, 1X, Agility, and Apptronik returned zero disclosed figures. Senator Markey's office investigated the AV industry and reported that **every company refused to disclose intervention frequency**.

The single published human-in-the-loop ratio in the entire industry is Waymo's, forced out by a Senate hearing in February 2026: **~70 Remote Assistance agents on duty worldwide against a 3,000-vehicle fleet — roughly 1 agent per 43 vehicles** [V]. Agents respond to requests *initiated by the vehicle* and give advice the Driver may reject; they cannot drive. Waymo has **never disclosed how often those requests occur**, and the number is absent even from its TÜV SÜD third-party audit.

**Why this is the most important missing number in robotics economics:** every analyst model of humanoid cost-per-hour prices declining hardware BOM and *assumes autonomy arrives*. None price the teleoperation labor sitting behind current deployments. If a humanoid needs one remote operator per N robots, the cost-per-hour floor is set by **operator wages ÷ N**, not by BOM. Nobody has published N for humanoids — and 1X sells NEO with "Scheduled Expert Mode," a human in a VR headset in your home, as a *product feature*.

The counterexample worth respecting: Figure's May 2026 endurance run — three robots, one shared policy, 24 hours, 28,000+ parcels at ~3 s each, claimed zero teleoperation with onboard inference [C]. Genuinely impressive, and still: **one task, structured environment, no intervention data published, CEO statement rather than audited record.**

**Rodney Brooks's 2026 scorecard** names three failure modes of the current approach: *collecting the wrong data*, *learning the wrong thing*, and possibly *learning being the wrong approach entirely* — with the specific technical argument that the human hand's ~17,000 mechanoreceptors have no analogue in any training corpus, and *"we do not have such a tradition for touch data."* DeepMind's own 32% dustpan number is consistent with Brooks, not with the marketing.

---

## 6. What the research community says is unsolved

From the RSS 2026 workshop slate (32 workshops = a community-authored list of open problems) and ICRA/IROS/CoRL 2026 CFPs:

1. **Long-horizon reliability** — the most repeated theme. Compound-error arithmetic is brutal: *95% per-step success gives 60% over a 10-step chain.* Named sub-problems: on-policy progress estimation under partial observability, run-time failure detection, and **metrics for long-horizon performance**.
2. **Failure recovery** — now has *two* dedicated RSS workshops (*Failure Is Not the End*, *Open-World Navigation… Robustness and Failure Recovery*).
3. **Multi-finger dexterity** — 4th consecutive RSS dexterity workshop; the hardest measured gap.
4. **Tactile and force sensing** — the biggest *emerging* area: 4+ dedicated 2026 venues, an RSS Early Career Spotlight (Wenzhen Yuan), and the explicit framing that touch *"remains far less developed and standardized than vision, proprioception, or language."*
5. **Formal safety for learned components** — a new standing venue (Safe Physical AI, Bremen, Aug 2026); new attack surfaces including **semantic jailbreaks and "freezing attacks"** on VLAs; benchmarks SafeVLA-Bench and HazardArena.
6. **Memory for long-horizon tasks** — genuinely new in 2026: Physical Intelligence's Multi-Scale Embodied Memory enabling tasks **longer than ten minutes**.
7. **Test-time verification over policy scaling** — [arXiv:2602.12281](https://arxiv.org/abs/2602.12281) reports **+22% in-distribution / +45% real-world** from scaling *verification* rather than policy learning **on identical data**. The LLM's role is shifting from task decomposer to **action verifier**.
8. **Robot data governance** — now a policy conversation: China released national standards in March 2026 with 40+ training centers; the US "lacks a national robotics data strategy."

The community's own framing, from a peer-reviewed April 2026 survey: *"future advances in VLA will depend less on model architecture and more on the co-design of high-fidelity data engines and structured evaluation protocols."*

---

## 7. What this means for this curriculum

**Validated, keep going:**
- **Courses I–II (geometry → estimation → mapping → planning → control) are not legacy.** §4 shows the frontier reaching back for exactly this material.
- **Evaluation-first pedagogy** — our capstone's randomized scenarios, published rubric, and reference-stack calibration turn out to be the discipline the field is in crisis over.

**Sharpened — what I'm adding to the curriculum as a result:**

1. **Statistical rigor as an explicit lesson.** The field can't compute confidence intervals on 25 rollouts; we already run seed sweeps but teach it implicitly. A short lesson — how many episodes for a claim, CIs on success rates, perturbation testing, the 0.09B-probe cautionary tale — turns out to be one of the more useful things here, and it's now [lesson 10.1](modules/10-evaluation/01-statistical-rigor.md).
2. **A tactile/force section** (awareness tier) in perception — currently absent from our plan, and the single biggest emerging modality gap.
3. **Failure data and recovery as a first-class topic** — our capstone stumbled into recovery behaviors; the field now has two workshops on it. Fold into the Module 9 data-engine lesson: failure taxonomies, intervention capture, recovery-conditioned training.
4. **Neural / real-to-sim evaluation** — new since our last snapshot and now credible: [RoboWorld](https://arxiv.org/html/2607.01060v3) reproduced an entire real-world leaderboard at **Pearson r = 0.989** in 100 H100-hours; 3DGS soft-body eval at r > 0.9. The pitch shifted from *simulate to train* to **simulate to evaluate** — which is our capstone harness's thesis, at industrial scale.
5. **Data curation with numbers** — negative transfer, the 5% coreset, instruction augmentation's 0%→90%. These are concrete, teachable, and change how anyone builds a robot dataset.
6. **Memory and long-horizon** — add to Module 9's outline.

**Hiring evidence** (from actual 2026 job postings, not recruiter blogs) — worth knowing if you're
making this transition too:

- **Figure — Helix AI Engineer, Data Infrastructure: $150–400k, and requires no ML modeling at all.** 4+ years backend, Linux, Python, Postgres/Elasticsearch/Redis, SLURM/Kubernetes, Terraform, dataset/annotation tooling. This is a distributed-systems job serving robot data.
- **Agility — Data Platform**: Spark/Kafka/Beam/Flink, Parquet/Arrow/Iceberg, Avro/Protobuf, OpenTelemetry/Prometheus, **bonus: mcap, ROS bags, Foxglove.** A conventional big-data role with robot formats bolted on.
- Skill frequency across postings: **Python universal · PyTorch universal on the learning side · C++ required wherever code touches the robot · Isaac Sim/MuJoCo the default sim stack · Slurm appears repeatedly · evaluation infrastructure rising fast and rarely in job titles.**
- **ROS 2 is nuanced**: dominant middleware standard, but *conspicuously absent* from frontier VLA-lab postings. Learn it for Agility/Boston Dynamics/Amazon; you can skip it at Figure/PI/NVIDIA-GR00T. (This is why our ROS 2 module should be a parallel track, not a prerequisite gate.)
- The humanoid industry's **largest employment category is humans generating training data** — Figure runs a 9-role Data Collection department; Tesla pays $25–48/hr for mocap-suit data collectors.

**The ranking, updated:**

1. **Robot data infrastructure & evaluation** — validated hard by both the research crisis (§1–2) and the salary data above. Least crowded, and the closest fit to what a data or ML engineer already knows.
2. **Classical stack fluency** — now with a *rising* premium (§4), not a declining one. This is what Courses I–II cover.
3. **Honest small-scale imitation learning** — credible entry artifact, especially with failure data and proper evaluation.
4. **LLM-as-verifier integration** — the 2026 twist for anyone arriving from LLM/agent work: the interesting role isn't task decomposition, it's action verification and test-time search.
5. **VLA research itself** — publication volume grew 5× YoY while measured capability didn't. Crowded; reach it through 1–4.

---

## Source caveats

Several widely-repeated figures could **not** be verified against primary sources and are excluded or flagged above: Skild Brain's specs (500B params), Egocentric-1M's hour count, the "only ~200 humanoids doing economically productive work" claim (attributed to McKinsey via WSJ; traceable only to a low-authority blog), and all teleoperation cost figures. This space is heavily polluted by AI-generated SEO sites publishing confident, uncheckable deployment numbers — the most reliable predictor of a company's honesty is **whether its customer will confirm the number**.
