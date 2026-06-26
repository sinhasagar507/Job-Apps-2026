# Job-Apps-2026

An AI-assisted, ATS-driven workflow for tailoring resumes and running job-search
outreach, orchestrated through [Claude Code](https://claude.com/claude-code).

A single instruction file (`CLAUDE.md`) turns Claude into a resume strategist,
ATS evaluator, LaTeX editor, and outreach writer: given a job description it
selects the matching base resume, rewrites only the Experience and Projects
sections against the JD, scores the result like an ATS, drafts recruiter/hiring-
manager outreach, logs the application, and compiles a one-page PDF.

## What's here

- **`CLAUDE.md`** - the full workflow: file registry, run modes, bullet/LaTeX
  rules, ATS scoring, outreach templates, and tracker/compile automation.
- **`Resumes_Base/`** - role-specific base resume LaTeX sources (Data Analyst,
  Data Scientist, Data Engineer, Software Engineer).
- **`JobSearch_2026/01_Resumes_Base/`** - rendered base resume PDFs.
- **`JobSearch_2026/00_Admin/`** - Python tooling:
  - `compile_resume.py` / `compile_cover_letter.py` - LaTeX → PDF compile.
  - `tracker_review.py` - daily application-tracker standup (wired as a
    Claude Code `UserPromptSubmit` hook in `.claude/settings.json`).
  - `agent/` - tracker digest + notification helpers.

## How it runs

Open the folder in Claude Code, paste a job description, and Claude executes the
`CLAUDE.md` workflow end to end. Default run mode is `[FAST]`; `[FULL]` produces a
deep audit.

## Not tracked

Personal application data is intentionally git-ignored and stays local: the
application tracker, tailored resumes, cover letters, and follow-ups.
