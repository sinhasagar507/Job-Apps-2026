# Socrates — An AI-Powered CUDA/GPU Programming Tutor

> A full-stack, locally-hosted, RAG-augmented tutoring platform that teaches GPU/CUDA
> programming through interactive Socratic dialogue, in-browser code compilation, live
> GPU performance telemetry, and auto-generated quizzes.

This document is a self-contained writeup intended for recruiters, hiring managers, and
networking conversations. It covers the problem, the system design, the engineering
decisions, the tech stack, and concrete talking points you can lift into a résumé,
portfolio page, or interview.

---

## 1. The 30-Second Pitch

**Socrates** is an interactive learning platform that turns the hard problem of "learning
GPU programming" into a guided, conversational experience. A student picks a CUDA topic,
chats with an AI tutor that explains concepts step-by-step (rather than dumping answers),
writes and **compiles/runs real C/C++/CUDA/Python code directly in the browser**, watches
**live GPU/CPU utilization for every prompt**, and reinforces learning with **auto-generated
quizzes** that produce personalized feedback on weak areas.

Crucially, the entire AI stack runs **locally via Ollama** — no per-token API costs, full
data privacy, and the ability to hot-swap between four different open-source LLMs
(DeepSeek R1, Qwen 2.5, Mixtral, Llama 3.2) at runtime.

**One-liner for a résumé:**
> Built a full-stack AI tutoring platform for GPU/CUDA programming: a React 19 SPA + Flask
> backend with a local RAG pipeline (sentence-transformers + cosine similarity over an
> NVIDIA CUDA dataset), runtime-selectable local LLMs via Ollama, a sandboxed multi-language
> code-compilation engine, real-time GPU telemetry, and AI-generated quizzes with
> personalized feedback.

---

## 2. The Problem & Motivation

GPU/CUDA programming is notoriously hard to learn:

- **The mental model is alien.** Thread hierarchies (grids/blocks/threads), memory
  coalescing, shared memory banks, and occupancy don't map onto sequential CPU intuition.
- **The toolchain is a barrier.** Most learners don't have an NVIDIA GPU, `nvcc`, and a
  working CUDA toolkit configured — so they can't even run the examples they're reading.
- **Passive content doesn't stick.** Reading docs or watching videos doesn't build the
  "feel" for *why* a kernel is fast or slow.

Socrates attacks all three: a **Socratic tutor** builds the mental model conversationally,
an **in-browser compiler** removes the toolchain barrier, and **live performance metrics +
quizzes** turn passive reading into active, measured practice.

The name "Socrates" reflects the core pedagogy — the tutor is explicitly prompted to
**teach first and quiz second**, asking guiding questions and building concepts up rather
than just handing over code.

---

## 3. What It Does — Feature Tour

| Feature | Description |
|---|---|
| **Conversational AI tutor** | Chat interface backed by a RAG pipeline over real CUDA examples. Maintains per-chat conversation memory for coherent multi-turn dialogue. |
| **Interactive Tutoring Mode** | A dedicated, structured teaching session scoped to a learning module (e.g., "Memory Optimization"). Injects module-specific learning objectives and "common student mistakes" into the system prompt. |
| **Multi-model selection** | Hot-swap between DeepSeek R1, Qwen 2.5, Mixtral, and Llama 3.2 at runtime, with automatic fallback to Llama 3.2 if the chosen model is unavailable. |
| **In-browser code editor + compiler** | A split-pane code canvas with syntax highlighting and line numbers. Compile & run C, C++, CUDA, and Python on the backend and stream results back. |
| **Smart dependency handling** | Static analysis detects missing packages/compilers (`pycuda`, `cupy`, `nvcc`, etc.) *before* execution and returns platform-specific install guidance instead of cryptic stack traces. |
| **Live GPU/system telemetry** | Every prompt reports response time, CPU%, RAM, GPU memory, GPU utilization, and temperature — with rolling 10-reading averages. |
| **Auto-generated quizzes** | The LLM generates 3-question MCQ/true-false quizzes on demand, validated against a strict schema, with a fallback quiz if generation fails. |
| **Personalized quiz feedback** | Scores answers, identifies weak vs. strong topic areas, and (in tutoring mode) generates an AI study plan targeting the learner's gaps. |
| **Persistent history** | Chats and messages persist to Supabase (Postgres), with chat history grouped by recency (Today / Yesterday / Previous 7 days / etc.). |
| **Auth** | Email/password authentication via Supabase Auth. |
| **Companion learning assets** | A Chainlit-based guided "reveal-the-GPU-kernel" experience and a set of Jupyter notebooks benchmarking CPU vs. GPU. |

---

## 4. System Architecture

Socrates is a multi-component system with a clean separation between the presentation
layer, the application/AI layer, the local model runtime, and persistence.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Browser)                                │
│  React 19 SPA (Create React App)                                         │
│  ┌──────────────┬───────────────┬──────────────┬────────────────────┐   │
│  │ ChatView     │ SplitPane +    │ ModelSelector│ Quiz / QuizFeedback│   │
│  │ + Messages   │ CodeEditor     │              │ + SystemInfo modal │   │
│  └──────────────┴───────────────┴──────────────┴────────────────────┘   │
│        │  REST (/api/*) via http-proxy-middleware → :5001                │
│        │  Supabase JS client (auth + Chats/Messages tables)             │
└────────┼─────────────────────────────────────────────────────────────┬─┘
         │                                                               │
         ▼                                                               ▼
┌────────────────────────────────────────────────┐         ┌────────────────────┐
│        FLASK BACKEND (modular, :5001)            │         │   SUPABASE (Postgres)│
│  app.py → blueprint registration                 │◄───────►│  Auth, Chats,        │
│  ┌────────────┬────────────┬─────────────────┐   │         │  Messages (+ JSON    │
│  │ routes/    │ models/    │ compiler/        │   │         │  quiz_data,          │
│  │  chat      │  rag       │  base            │   │         │  performance_metrics)│
│  │  compile   │  session   │  enhanced        │   │         └────────────────────┘
│  │  deps      │            │  dependencies    │   │
│  │  status    │            │                  │   │
│  ├────────────┴────────────┴─────────────────┤   │
│  │ utils/ gpu_monitor · cleanup · helpers     │   │
│  └────────────────────────────────────────────┘  │
│        │ RAG embeddings (sentence-transformers)   │
│        │ subprocess: gcc / g++ / nvcc / python3   │
│        ▼                                           │
└────────┼───────────────────────────────────────┬─┘
         ▼                                         ▼
┌──────────────────────┐              ┌─────────────────────────────┐
│  OLLAMA (:11434)      │              │  GPU / OS                   │
│  deepseek-r1, qwen2.5 │              │  nvcc toolchain, NVIDIA GPU │
│  mixtral, llama3.2    │              │  (GPUtil / pynvml / PyTorch)│
└──────────────────────┘              └─────────────────────────────┘
```

**Design highlight — dependency-injected blueprints.** `app.py` initializes each subsystem
(RAG, compiler, GPU monitor) once at startup, then injects them into Flask blueprints via
factory functions (`create_chat_blueprint(rag_system)`, etc.). This keeps routes testable
and decoupled from global state, and lets the app **degrade gracefully**: if the enhanced
compiler fails to initialize it falls back to the basic one; if RAG fails the chat route
still returns a useful fallback response.

---

## 5. Tech Stack

**Frontend**
- React 19 (Create React App), functional components + hooks (no Redux — centralized state
  in the root component, props down)
- `react-syntax-highlighter` (VS Code Dark+ theme) + a custom CUDA-aware tokenizer
  (`__global__`, `__device__`, `threadIdx`, `cudaMalloc`, …)
- `@supabase/supabase-js` for auth and data
- `http-proxy-middleware` for dev API proxying
- Per-component CSS, mobile-responsive (NVIDIA-green `#76B900` dark theme)

**Backend**
- Python 3 + Flask + Flask-CORS, organized into a **modular blueprint architecture**
  (routes / models / compiler / utils) with environment-aware config classes
  (Development / Production / Testing)
- RAG: `sentence-transformers` (`all-MiniLM-L6-v2`), `scikit-learn` cosine similarity,
  HuggingFace `datasets` (`SakanaAI/AI-CUDA-Engineer-Archive`)
- LLM runtime: **Ollama** (local), accessed over its HTTP API
- Code execution: Python `subprocess` invoking `gcc` / `g++` / `nvcc` / `python3`
- GPU telemetry: `GPUtil`, `nvidia-ml-py3` (pynvml), `torch.cuda`, `psutil`

**Data & Infra**
- Supabase (Postgres + Auth)
- Docker: a hardened `nvidia/cuda:12.0-devel` sandbox image for code execution
- Chainlit + LangChain (companion guided-learning interface, GPT-4o)
- Jupyter notebooks (CuPy, cuDF, cuML, PyTorch) for CPU-vs-GPU benchmarking

---

## 6. Engineering Deep Dives

These are the parts worth talking through in detail in an interview.

### 6.1 The RAG Pipeline (`models/rag.py`)
- On startup, loads NVIDIA/Sakana's **AI-CUDA-Engineer-Archive** dataset, builds a knowledge
  base of `{operation, cuda_code, speedup}` records, and **pre-computes sentence embeddings**
  for all of them with `all-MiniLM-L6-v2`.
- At query time it embeds the user's question and retrieves the top-K most similar CUDA
  examples via **cosine similarity**, then injects them into the LLM prompt as grounding
  context — so answers reference real, measured CUDA kernels and their speedups.
- **Resilience built in:** if the dataset can't be downloaded it falls back to a small
  in-memory demo set; if no embeddings exist it degrades to general-knowledge prompting.

### 6.2 Runtime-Selectable Local LLMs (`config.py`, `routes/chat.py`)
- Four models are configured (DeepSeek R1, Qwen 2.5, Mixtral, Llama 3.2), each with its own
  temperature, token budget, description, and **fallback model**.
- The frontend's `ModelSelector` persists the choice to `localStorage`; the backend
  validates it and routes generation to the chosen Ollama model.
- `_generate_with_model` tries the primary model and **automatically retries with the
  fallback** (Llama 3.2) on timeout/connection failure — the user gets an answer even when
  a heavyweight model isn't loaded.
- A `/api/model/status/<id>` endpoint queries Ollama's `/api/tags` so the UI can show which
  models are actually installed.

### 6.3 Two-Tier Prompt Engineering (Tutoring vs. Chat)
- **Regular chat** uses RAG context + conversation history for a helpful-assistant prompt.
- **Tutoring mode** assembles a much richer system prompt: it looks up the selected
  **module** (CUDA Basics, Memory Optimization, Kernel Development, Performance Tuning) and
  injects that module's **learning objectives** and **common student mistakes**, plus an
  explicit pedagogical contract: *teach thoroughly first, offer quizzes only after
  substantial teaching or on explicit request.* This is what makes the tutor "Socratic"
  rather than an answer vending machine.

### 6.4 Sandboxed Multi-Language Code Execution (`compiler/`)
- `CodeCompiler` writes user code to a **UUID-namespaced temp directory**, compiles with the
  right toolchain (`gcc -std=c99`, `g++ -std=c++17`, `nvcc -std=c++14`, or runs Python),
  and executes with **strict `subprocess` timeouts** and **output-size caps** to contain
  runaway or malicious code. CUDA runs are pinned with `CUDA_VISIBLE_DEVICES=0`.
- `EnhancedCodeCompiler` adds a **dependency gate**: before running, it statically scans the
  code for required packages/compilers and, if something's missing, returns a friendly,
  platform-aware install guide (pip, conda, Homebrew, apt) instead of a raw `ModuleNotFoundError`.
- A **background cleanup thread** removes stale compilation artifacts on an interval.
- For true isolation, a Docker target runs execution in an `nvidia/cuda:12.0-devel`
  container that is **read-only, network-disabled (`network: none`), memory/CPU-capped,
  `no-new-privileges`, non-root**, with only a tmpfs scratch space.

### 6.5 Real-Time GPU & System Telemetry (`utils/gpu_monitor.py`)
- A **layered detection strategy** for maximum portability: try **GPUtil** first, fall back
  to **PyTorch CUDA** APIs, then **pynvml**, and finally degrade to CPU/RAM-only monitoring
  on machines without an NVIDIA GPU (e.g., macOS dev laptops).
- Captures GPU model, memory used/total, utilization %, and temperature; pairs it with
  `psutil` CPU/RAM stats and maintains **rolling 10-sample averages**.
- Every `/api/chat` response carries a `performance_metrics` block, surfaced per-message in
  the UI's SystemInfo modal — so learners can *see the GPU working* as they experiment.

### 6.6 Quiz Generation & Evaluation (`models/rag.py`, `routes/chat.py`)
- Specific intent detection (regex + keyword phrases) decides whether a message is a genuine
  quiz request vs. a normal question — avoiding the failure mode of "what is X?" triggering a
  quiz.
- The LLM is prompted to emit **strict JSON**; the backend parses it defensively (handles
  ```json fences, brace extraction), **validates the schema** (3 questions, correct option
  counts, valid answer index), and **falls back to a hand-written quiz** if validation fails.
- `/api/evaluate-quiz` scores answers, separates **weak vs. strong topic areas**, and in
  tutoring mode generates a **personalized AI study plan** addressing the missed topics.

### 6.7 Persistence Model (Supabase)
- `Chats` and `Messages` tables back the conversation history; messages store rich JSON
  columns (`quiz_data`, `performance_metrics`) so quizzes and metrics survive reloads.
- The backend pulls conversation context **directly from the `Messages` table by `chat_id`**
  (with a legacy in-memory `SessionManager` as fallback), so context is durable across
  sessions and devices, not just held in server memory.

### 6.8 Companion Learning Assets
- **Chainlit interface** (`chainlit/`): a guided, multi-step flow using LangChain + GPT-4o
  that walks a learner from a CPU operation → progressive AI hints → the GPU kernel → an
  auto-generated **Google Colab notebook** that benchmarks both implementations.
- **Jupyter notebooks**: hands-on CPU-vs-GPU benchmarks (vector add, matmul, Conv2D+ReLU+
  BiasAdd, DataFrame ops, ML) using CuPy/cuDF/cuML/PyTorch with proper `cuda.synchronize()`
  timing and memory profiling — demonstrating real measured speedups (e.g., ~30× on a
  512×512 matmul).

---

## 7. Notable Design Decisions & Trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| **Local LLMs via Ollama** instead of a hosted API | Zero per-token cost, data privacy, offline-capable, freedom to compare models | Requires local compute; heavier models need a capable machine (hence the fallback system) |
| **Modular blueprint backend** (refactored from an ~2,000-line monolith `backend.py`) | Testability, separation of concerns, graceful degradation | More files / indirection vs. a single script |
| **RAG grounding** over fine-tuning | Cheap to update, no training pipeline, cites real examples | Retrieval quality is bounded by the dataset and embedding model |
| **Subprocess + Docker sandbox** for execution | Lets learners run real code without their own toolchain | Security surface area — mitigated with timeouts, output caps, read-only/network-less containers |
| **Supabase** for auth + data | Managed Postgres + auth, fast to build on, shared by frontend and backend | External dependency; schema coupling |
| **No Redux** (centralized hook state) | Lower ceremony for the team's scope | Prop-drilling grows with feature count (a known refactor target) |
| **Teach-first prompt contract** | Aligns with the "Socratic" pedagogy goal | Requires careful prompt engineering and intent detection to avoid over-quizzing |

---

## 8. Results & Outcomes

- A **working end-to-end platform**: authenticated chat → RAG-grounded tutoring → in-browser
  compile/run → live GPU metrics → quiz → personalized feedback, all wired together.
- **Four interchangeable local LLMs** with automatic fallback, removing API cost and lock-in.
- **Cross-platform resilience**: runs (with graceful degradation) on machines without a GPU —
  the GPU monitor and dependency checker detect the environment and adapt rather than crash.
- **Measured GPU speedups** demonstrated in the companion notebooks (e.g., ~30× matmul,
  large speedups on Conv2D and DataFrame workloads) — concrete artifacts that show the
  pedagogy is grounded in real performance data.
- A clean migration story: an early **monolithic Flask backend → modular, blueprint-based
  architecture**, which is a great talking point about refactoring and maintainability.

---

## 9. Challenges Solved (great interview stories)

1. **"How do you teach GPU code to people without a GPU?"** → Layered GPU detection with CPU
   fallback + a dependency analyzer that explains exactly what's missing and how to install
   it per-platform, instead of failing silently.
2. **"How do you safely run arbitrary user-submitted C/CUDA/Python on a server?"** →
   Subprocess isolation with timeouts and output caps, plus a hardened, network-less,
   read-only Docker sandbox with resource limits and a non-root user.
3. **"How do you get reliable structured output (quizzes) from an LLM?"** → Strict JSON
   prompting + defensive parsing + schema validation + a deterministic fallback quiz.
4. **"How do you keep a tutor from just dumping answers?"** → Module-aware prompt
   engineering that encodes learning objectives, common mistakes, and an explicit
   teach-before-test contract, plus intent detection to separate questions from quiz requests.
5. **"How do you keep multi-turn conversations coherent?"** → Pulling conversation context
   from the `Messages` table per `chat_id` so memory is durable and survives reloads.

---

## 10. Team & My Role

Socrates was built as a **collaborative team project** (5 contributors; ASU-affiliated).
The repository's branch structure (`main`, plus per-contributor branches and feature
branches like `course-prompts`, `amogh-mode-slctr`, `susrik_final`) reflects a real
**Git feature-branch + pull-request workflow** with integration merges.

> **Tip for your writeup:** tailor this section to *your* contributions. Based on the branch
> history, individual contributors owned areas such as the GPU monitoring stack, the
> course/module prompt system, the model-selector UI, the sidebar/chat-history UX, and the
> tutoring mode. State clearly which of these you led or built, and what you'd do
> differently next time (e.g., introduce state management on the frontend, add automated
> tests around the compiler, containerize the full stack).

---

## 11. Possible Extensions (shows forward thinking)

- **Streaming responses** end-to-end (the `StreamingMessage` component and a `stream` flag
  already exist; wire SSE/chunked transfer through the chat route).
- **Frontend state management** (Context/`useReducer` or Zustand) to tame prop-drilling.
- **Automated test coverage** for the compiler and RAG layers (pytest scaffolding is present).
- **Vector DB** (FAISS is already a dependency) to scale RAG beyond the in-memory dataset.
- **Full-stack containerization** + CI/CD so the whole platform deploys reproducibly.
- **Progress tracking / spaced repetition** built on the stored quiz results.

---

## 12. Quick Facts Sheet (copy/paste friendly)

- **What:** Full-stack AI tutor for GPU/CUDA programming
- **Frontend:** React 19, Supabase JS, react-syntax-highlighter, custom CUDA tokenizer
- **Backend:** Python/Flask (modular blueprints), env-aware config
- **AI:** Local LLMs via Ollama (DeepSeek R1 / Qwen 2.5 / Mixtral / Llama 3.2) with fallback;
  RAG via sentence-transformers + cosine similarity over NVIDIA's AI-CUDA-Engineer-Archive
- **Code execution:** Sandboxed `subprocess` compilation of C/C++/CUDA/Python; hardened
  Docker (`nvidia/cuda:12.0-devel`, read-only, no-network, resource-capped) execution target
- **Telemetry:** Real-time GPU/CPU/RAM metrics (GPUtil / pynvml / PyTorch / psutil) per prompt
- **Data:** Supabase (Postgres + Auth); chats & messages with JSON quiz/metrics columns
- **Extras:** Chainlit + LangChain (GPT-4o) guided flow; CuPy/cuDF/cuML/PyTorch benchmark notebooks
- **Engineering themes:** RAG, prompt engineering, local-LLM orchestration, sandboxed code
  execution, graceful degradation, monolith→modular refactor, real-time systems telemetry
</content>
</invoke>
