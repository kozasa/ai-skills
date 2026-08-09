# Publish HTML Communication Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the two HTML communication skills with reproducible Codex and Claude Code setup instructions.

**Architecture:** Keep complete, self-contained skill packages under `skills/`. Use the root README as the installation entry point and per-skill READMEs as operational references. Protect the distribution contract with lightweight Python standard-library tests.

**Tech Stack:** Markdown, Python 3 standard library, HTML/CSS/JavaScript

## Global Constraints

- `ai-skills` is the public canonical source.
- FAST mode must not require network access, package installation, or a build step.
- Setup instructions must cover Codex, Claude Code, repository-local instructions, and agent-driven installation.
- Published skill files must match the already verified source from the Research worktree.

---

### Task 1: Protect the public distribution contract

**Files:**
- Create: `tests/test_public_distribution.py`

**Interfaces:**
- Consumes: repository files and Markdown text
- Produces: a standard-library unittest suite validating required packages and setup instructions

- [x] Write tests that require both skill packages, per-skill READMEs, Codex and Claude Code paths, instruction-file snippets, and the agent setup prompt.
- [x] Run `python3 -m unittest tests.test_public_distribution -v` and verify it fails because the packages and documentation are absent.

### Task 2: Publish the two skill packages

**Files:**
- Create: `skills/human-handoff/**`
- Create: `skills/quick-html/**`
- Create: `skills/human-handoff/README.md`
- Create: `skills/quick-html/README.md`

**Interfaces:**
- Consumes: verified skill sources in `/Users/kozasa/orca/workspaces/Research/tuskfish/skills/`
- Produces: self-contained public skill packages

- [x] Copy the verified skill packages without modifying runtime behavior.
- [x] Add concise public READMEs for purpose, installation, usage, and constraints.
- [x] Run the renderer tests and confirm they pass from the public package.

### Task 3: Document end-to-end setup

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: the two published skill packages
- Produces: manual and agent-driven installation instructions for Codex and Claude Code

- [x] Expand the skill table and document clone/copy commands.
- [x] Add `AGENTS.md` and `CLAUDE.md` auto-trigger snippets plus global-file alternatives.
- [x] Add a copyable prompt that asks an agent to install, configure, and verify the skills.
- [x] Run `python3 -m unittest discover -s tests -v` and all existing skill tests.

### Task 4: Verify the release artifact

**Files:**
- Verify only

**Interfaces:**
- Consumes: complete repository state
- Produces: evidence that distribution is complete and reproducible

- [x] Compare the published runtime files with the Research source using `diff -ru`, excluding public-only README files.
- [x] Render a sample FAST page and verify two conclusion blocks and no remote assets.
- [x] Check Markdown links and inspect `git diff --check` and `git status`.
