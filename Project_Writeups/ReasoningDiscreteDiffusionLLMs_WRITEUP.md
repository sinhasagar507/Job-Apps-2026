# Reasoning Capabilities in Discrete Diffusion LLMs — Project Writeup

> A reusable narrative + talking-points document for recruiting, networking, and interviews.
> Skim the top for a recruiter-friendly overview; the deeper sections are for engineers and
> researchers. Copy whichever slice fits the conversation.

---

## 1. The one-liner & elevator pitch

**One-liner:** I studied whether a *diffusion* language model reasons differently from a
standard *autoregressive* (GPT-style) model when both are given the same compute budget — and
I looked inside the model to see *how* it reasons.

**30-second pitch:** Almost every LLM you've heard of generates text left-to-right, one token
at a time (autoregressive). A newer class — *diffusion* language models — instead start from a
fully masked answer and iteratively "denoise" it, filling in tokens in any order over a fixed
number of refinement steps. On a 5-person research team at ASU, I worked on a head-to-head
study of an 8B diffusion model (**LLaDA-8B**) against an 8B autoregressive baseline
(**Llama-3-8B**) on math and logic reasoning benchmarks. My piece was the **evaluation
engine**: I built the multi-GPU benchmarking harness, fixed and rewrote the diffusion
sampler, ran the repairability ("can it fix its own wrong answers?") experiments, and did the
attention-probing analysis that showed *why* the diffusion model behaves differently. The
headline result: the diffusion model's accuracy scales smoothly with how many refinement steps
you give it — from ~25% to ~75% on grade-school math — and its attention is genuinely
bidirectional, unlike the autoregressive model.

**Why it matters:** Diffusion LLMs are an emerging alternative to autoregressive generation
with appealing properties (parallel/iterative decoding, bidirectional context, a tunable
compute-vs-quality knob). Understanding their reasoning behavior — fairly, under matched
compute — is an open research question, and this project contributes concrete benchmarks and
mechanistic evidence.

---

## 2. Project at a glance

| | |
|---|---|
| **Project** | Reasoning Capabilities in Discrete Diffusion Large Language Models |
| **Context** | ASU CSE 576 — Topics in Natural Language Processing |
| **Team** | EchoAgents (5 members); mentor: Shri Kumbhar |
| **My role** | Evaluation & benchmarking lead (LLaDA side): eval harness, diffusion sampler, repairability study, attention probing, repo architecture |
| **Models compared** | `GSAI-ML/LLaDA-8B-Instruct` (discrete diffusion) vs `Llama-3-8B-Instruct` (autoregressive) |
| **Benchmarks** | GSM8K, LogiQA, GPQA-Diamond, AIME 2025 (primary); MATH-500, Countdown, Sudoku (auxiliary) |
| **Core idea** | Compare the two paradigms under **matched decoding compute**, then probe *how* each reasons internally |
| **Stack** | PyTorch 2.6, HF Transformers 4.49, PEFT/LoRA, accelerate + DDP, DeepSpeed, bitsandbytes, TRL, wandb, SLURM/A100 |
| **Built on** | The open-source [`d1`](https://github.com/dllm-reasoning/d1) codebase (vendored upstream), extended for new datasets, metrics, and a corrected sampler |

---

## 3. The problem & research questions

**Background.** Autoregressive (AR) LLMs generate left-to-right with causal attention — each
token only "sees" the tokens before it. Discrete **diffusion** LLMs (dLLMs) work differently:
they begin with a fully *masked* answer region and run a fixed number of **denoising steps**,
each step predicting tokens for masked positions and re-masking the least-confident ones.
Decoding is **bidirectional** (a token can attend to text on both sides) and **iterative**
(more steps = more refinement). That "number of steps" is a direct, tunable
**compute knob** — which makes a fair comparison against AR models genuinely tricky.

**The fairness problem.** AR and diffusion models spend compute in completely different ways,
so naive accuracy comparisons are misleading. The project's framing is **compute-parity**:
hold decoding compute comparable across paradigms before comparing reasoning quality.

**Three research questions (the three objectives):**

1. **Benchmarking** — Under matched decoding compute, how do diffusion and autoregressive
   models compare on math and logic reasoning?
2. **Repairability** — Given a second chance, can the model *self-correct* a wrong answer
   without breaking answers it already got right — and at what compute cost?
3. **Mechanistic** — *How* does diffusion reasoning happen internally? What do the attention
   patterns reveal about where and how information flows?

---

## 4. What I built (my contributions)

This is the part to lead with in "what did *you* do?" conversations. Everything below is work
I personally owned within the larger team effort.

### Objective 1 — Compute-parity benchmarking harness
*(`objective1_benchmarking/`)*

I built the evaluation engine that produced the team's LLaDA benchmark numbers:

- **Multi-GPU evaluation harness** (`eval_sft_task2.py`) — DDP across GPUs with:
  - **Resume-safe JSONL streaming**: counts completed examples and restarts mid-sweep without
    redoing work (essential for long runs on shared/preemptible GPUs).
  - **Out-of-memory (OOM) fallback**: catches CUDA OOM and retries with a reduced footprint
    rather than crashing the whole sweep.
  - **LoRA-checkpoint loading**: evaluates both the base model and the fine-tuned (SFT)
    adapter from a single harness.
  - **Telemetry**: records latency, peak VRAM, and token counts per run for compute accounting.
- **New dataset wrappers** — LogiQA (4-way MCQ logic), GPQA-Diamond (expert QA, with local
  Arrow-shard support), and AIME 2025 (competition math), each with unified prompt formatting
  and answer parsing.
- **Reproducible sweep drivers** (`run_eval_all.sh`, `run_eval_all_gpqa.sh`) — drive a full
  benchmark × step-budget grid, with DONE markers, automatic retries, and dynamic port
  selection to avoid collisions on shared nodes.

### Diffusion sampler rewrite
*(`objective1_benchmarking/generate.py`)*

I rewrote the core token-sampling routine and **fixed a real numerical bug** in the upstream
implementation:

- The upstream Gumbel-Max sampler computed `(-log u) ** temperature`, which is *not* correct
  Gumbel noise. I replaced it with a proper **Gumbel-Max** formulation `(logits / T) +
  Gumbel(0,1)` with safe clamping to avoid `log(0)`.
- Added **top-k / top-p (nucleus) filtering** and a **repetition penalty** for higher-quality
  generations.
- Cleaner **block-wise step allocation** with low-confidence remasking — the model decodes the
  answer in blocks and spends its diffusion-step budget where it's least certain.

### Objective 2 — Repairability study
*(`objective2_repairability/LlaDA_repairability_sagar.ipynb`)*

I designed and measured whether a "second chance" helps the diffusion model, comparing three
decoding strategies on GSM8K:

| Strategy | How it works | Cost (gens/question) |
|---|---|---|
| **Base** | Single deterministic decode (T=0) | 1× |
| **Self-Consistency (SC)** | k=5 sampled chains (T=0.7, p=0.9), majority vote | 5× |
| **Guided Retry (GR)** | Show the model its first answer, ask it to re-check, decode again | 2× |

Metrics I defined to capture the real tradeoff:
- **Repair success** = fraction of initially *wrong* answers that became correct.
- **Over-repair** = fraction of initially *correct* answers that got broken.

This frames self-correction honestly: a strategy that fixes wrong answers but breaks right
ones isn't a free win, and the compute cost has to be in the picture.

### Objective 3 — Attention probing
*(attention-map entropy study + BI/ALI metrics)*

I did the mechanistic analysis that explains *why* the diffusion model behaves differently:

- **Attention-map entropy study** — how focused vs. diffuse the model's attention is across
  layers during answer generation.
- **Bidirectionality Index (BI)** — for each generated token, how much attention flows
  *forward* (to future tokens) vs. backward. This produced the project's signature finding:
  **LLaDA is genuinely bidirectional (BI ≈ 0.3–0.4)** with a mid-layer prompt↔answer
  "reasoning corridor," while the autoregressive model stays prompt-anchored (**BI ≈ 0**).
- **Attention Localization Index (ALI)** — whether attention over the answer region is
  concentrated or spread out.

*(The diffusion-trajectory mechanistic probing — flip-localization, correctness probes, and
causal interventions — was owned by a teammate.)*

### Compute-parity telemetry & scoring
*(`llada_parity_metrics_verbose.py`, `parse_boxed_accuracy.py`, `run_llada_metrics_on_jsonl.py`)*

- Pairing logic that matches AR vs. diffusion runs by comparable compute.
- Robust answer extraction from `\boxed{...}` and `<answer>...</answer>` for both numeric and
  multiple-choice tasks.
- Aggregate latency / peak-memory / GPU-seconds reporting for the parity analysis.

### Repo architecture
I reorganized the codebase into a clean, reproducible **objective-based structure**: the
upstream `d1` codebase is vendored *untouched*, and each objective folder **imports shared
modules via `sys.path`** rather than copying them (local overrides — like my rewritten
sampler — take precedence, while unchanged datasets/parsers are imported from `d1/eval`). This
removed duplication and kept the project honest about what's upstream vs. ours.

---

## 5. Methods & techniques (technical deep-dive)

For ML-literate audiences.

**Discrete diffusion generation.** Masked denoising over a fixed answer window: initialize all
answer positions to a mask token, then for each diffusion step predict logits for masked
positions, sample (Gumbel-Max with temperature, top-k/top-p, repetition penalty), and re-mask
the lowest-confidence predictions. Generation proceeds **block-wise**, allocating steps per
block. The **diffusion-step budget** is the key compute dial; classifier-free guidance (CFG)
is supported.

**Compute-parity methodology.** Because AR and diffusion models spend compute so differently,
the comparison controls for decoding compute (via step budgets and matched telemetry) before
comparing accuracy. This is the crux of a fair head-to-head and the reason the harness records
latency / VRAM / token counts on every run.

**Masked SFT for dLLMs** *(built on d1's `dLLMTrainer`)*. Supervised fine-tuning for diffusion
models uses an **absorbing-state / timestep-weighted loss**: each example is noised to a random
timestep `t` (Bernoulli masking at rate `t`), loss is computed only on masked completion tokens
(completion-only), and scaled by `1/t` so noisier examples weigh more. LoRA adapters
(r=128, α=256) keep training cheap. The evaluated SFT variant is a LoRA checkpoint
(`checkpoint-942`) trained on the `llada_mix_temp07` data mixture.

**diffu-GRPO (RL), available in the stack.** The d1 codebase also includes diffusion-policy RL
(GRPO) with PPO-style importance-ratio clipping, KL-to-reference regularization, efficient
masked-token log-probability estimation over multiple iterations, and task-specific reward
functions (correctness / XML-format / symbolic equivalence). I'm noting this for completeness
of the platform — it was part of the broader stack/team scope rather than my individual focus.

**Attention probing (my work).** From LLaDA's segment-masked attention tensors I computed the
attention-map entropy study, the **Bidirectionality Index** (forward-vs-backward attention
mass per generated token), and the **Attention Localization Index** (positional entropy of
attention over the generated region), across selected layers.

---

## 6. Results & findings

> **Attribution note:** the benchmark numbers below are **team results produced by the
> Objective 1 evaluation harness I built and ran**. They reflect the team report / current
> sweeps at 8B scale.

**Headline — accuracy scales monotonically with diffusion-step budget (LLaDA-SFT):**

| Setting | GSM8K | LogiQA | GPQA-Diamond | AIME 2025 |
|---|:--:|:--:|:--:|:--:|
| LLaDA-SFT, 16 steps | 24.6% | 39.3% | 22.6% | 0.0% |
| LLaDA-SFT, 32 steps | 34.3% | 41.9% | 24.7% | 0.0% |
| LLaDA-SFT, 64 steps | 56.1% | 43.5% | 24.8% | 0.0% |
| LLaDA-SFT, 256 steps | **75.3%** | **47.4%** | **28.0%** | 0.0% |
| Llama-3-SFT (greedy, ref.) | ~56% | ~40% | — | — |

Takeaways:
- **More refinement steps → better reasoning**, smoothly, on GSM8K, LogiQA, and GPQA. The
  diffusion-step budget is a genuine quality dial.
- **GSM8K roughly triples** (24.6% → 75.3%) from 16 to 256 steps; at high step counts the
  diffusion model surpasses the AR reference on GSM8K.
- **AIME 2025 stays at 0%** — competition-level math is out of reach at 8B scale regardless of
  steps (honest headroom, not a measurement artifact).

**Mechanistic finding (my attention probing):** LLaDA shows **genuinely bidirectional
attention** (BI ≈ 0.3–0.4) with a mid-layer prompt↔answer "reasoning corridor," whereas the
autoregressive model stays prompt-anchored (BI ≈ 0). This is concrete evidence that the
diffusion model uses its bidirectional context rather than just emulating left-to-right
decoding.

**Repairability (my study):** the framework quantifies, for each second-chance strategy, how
many wrong answers get repaired vs. how many right answers get broken — and at what compute
cost (1× / 5× / 2× generations) — so "self-correction" is evaluated honestly rather than
cherry-picked.

---

## 7. Engineering challenges & what I learned

- **Long sweeps on shared GPUs** demanded resume-safety and OOM recovery — a crashed job at
  hour 6 of a 4-benchmark × 4-budget grid can't mean starting over. I designed the harness
  around JSONL line-counting and DONE markers.
- **A subtle numerical bug** in the upstream sampler (incorrect Gumbel noise) was producing
  miscalibrated sampling; finding and fixing it taught me to verify "borrowed" math, not trust
  it.
- **Fair compute accounting** across two very different generation paradigms is a design
  problem, not just a coding one — deciding *what* to hold constant is the real research
  contribution.
- **Keeping a large vendored codebase clean** via import-based dedup (vs. copy-paste) kept the
  project reproducible and made it obvious what was ours vs. upstream.
- **Collaborating across a 5-person split** (LLaDA vs. LLaMA sides, benchmarking vs.
  mechanistic probing) required clear interfaces and honest ownership boundaries.

---

## 8. Resume bullets (copy-paste)

- Built a **resume-safe, multi-GPU (DDP) evaluation harness** for an 8B discrete-diffusion LLM
  (LLaDA-8B), sweeping 4 reasoning benchmarks × 4 compute budgets; demonstrated accuracy
  scaling from **24.6% → 75.3% on GSM8K** with diffusion-step budget.
- **Rewrote the diffusion sampler and fixed a numerical bug** in the upstream Gumbel-Max
  implementation; added top-k/top-p nucleus filtering and repetition penalty, improving
  generation quality.
- Designed a **repairability study** (base vs. self-consistency vs. guided-retry) with
  *repair-success* / *over-repair* metrics and explicit compute-cost accounting to evaluate
  LLM self-correction honestly.
- Ran **mechanistic attention probing** (attention-map entropy, Bidirectionality Index,
  Attention Localization Index); showed LLaDA's attention is **genuinely bidirectional
  (BI ≈ 0.3–0.4)** vs. an autoregressive baseline's prompt-anchored attention (BI ≈ 0).
- Engineered a **compute-parity benchmarking methodology** with latency/VRAM/token telemetry
  to fairly compare diffusion vs. autoregressive reasoning.
- Architected the repository into a clean **objective-based structure** with import-based
  deduplication against the vendored upstream codebase for reproducibility.

---

## 9. Talking points / likely interview Q&A

**Q: What's a diffusion language model, in one breath?**
Instead of writing text left-to-right, it starts from a fully masked answer and iteratively
fills it in over a fixed number of refinement steps, attending to context on both sides. More
steps = more refinement.

**Q: What does "compute-parity" mean and why does it matter?**
Diffusion and autoregressive models spend compute in totally different ways, so comparing raw
accuracy is misleading. Compute-parity means holding decoding compute comparable before
comparing reasoning quality — otherwise you're measuring budget, not capability.

**Q: What did *you* personally build?**
The evaluation harness (multi-GPU, resume-safe, with telemetry), the diffusion sampler rewrite
(including a bug fix), the repairability experiments, and the attention-probing analysis
(entropy study, BI, ALI). Plus the repo architecture. Teammates owned the LLaMA baselines and
the diffusion-trajectory mechanistic probing.

**Q: What was the hardest bug?**
The upstream sampler computed Gumbel noise incorrectly (`(-log u) ** T` instead of proper
Gumbel-Max). It "worked" enough to not crash, which made it sneaky. I replaced it with the
correct formulation and added nucleus filtering.

**Q: What's the most interesting finding?**
Two: (1) diffusion accuracy scales smoothly with step budget — a clean compute-vs-quality
dial; and (2) the diffusion model's attention is genuinely bidirectional with a mid-layer
"reasoning corridor," unlike the autoregressive baseline. The second is mechanistic evidence
that it's *using* its architecture, not imitating AR decoding.

**Q: What were the limitations?**
8B-scale headroom is real — AIME 2025 stayed at 0% no matter the step budget. Results are at
8B scale on a fixed benchmark set, and the SFT used LoRA rather than full fine-tuning.

**Q: What would you do next?**
Push to larger models, add full compute-parity curves against the AR baseline across all
benchmarks, explore RL (diffu-GRPO) on top of SFT, and connect the attention "reasoning
corridor" to the diffusion-trajectory probing for a unified mechanistic story.

---

## 10. Glossary

- **LLaDA** — an 8B discrete-diffusion (masked-denoising) instruction-tuned LLM.
- **dLLM** — diffusion large language model; generates by iterative denoising rather than
  left-to-right.
- **Autoregressive (AR)** — standard left-to-right, causal-attention generation (e.g., Llama-3).
- **SFT** — supervised fine-tuning. **LoRA** — low-rank adapters that fine-tune cheaply.
- **GRPO / diffu-GRPO** — group-relative policy optimization; RL fine-tuning, adapted for
  masked diffusion models.
- **GSM8K / LogiQA / GPQA-Diamond / AIME 2025** — math + logic + expert-QA reasoning
  benchmarks.
- **BI (Bidirectionality Index)** — share of a token's attention flowing to future tokens.
- **ALI (Attention Localization Index)** — how concentrated attention is over the answer region.
- **Remasking** — re-masking the least-confident predicted tokens between diffusion steps.
- **Compute-parity** — matching decoding compute across paradigms for a fair comparison.
