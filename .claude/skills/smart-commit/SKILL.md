---
name: smart-commit
description: Commits all staged/unstaged changes as logical, well-scoped git commits, then updates and prunes the project MEMORY.md file.
user_invocable: true
arguments: []
---

# Smart Commit — Logical commits + memory maintenance

You have been asked to commit recent changes and keep project memory up to date. Follow the steps below precisely.

---

## Step 1 — Survey the working tree

Run these in parallel:
- `git status` — what is modified, untracked, or staged
- `git diff HEAD` — full diff of all changes
- `git log --oneline -10` — recent commit history for context and style

---

## Step 2 — Plan logical commit groups

Analyse the diff and group changes into logical, independently shippable units. Each commit should represent one coherent change (e.g. "feat: DA suburb backfill script", "fix: import script field name", "chore: update migration"). Do NOT batch unrelated changes into a single commit.

For each group:
1. Identify the files involved
2. Draft a commit message in the style of recent commits (infer from `git log`)
3. Stage only those files with `git add <files>` then commit

---

## Step 3 — Execute commits

For each logical group:
1. Stage the relevant files: `git add <specific files>`
2. Commit using a HEREDOC to avoid quoting issues:
```
git commit -m "$(cat <<'EOF'
<type>: <subject>

<optional body>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```
3. Verify with `git status` after each commit

Never use `git add -A` or `git add .` — always add specific files to avoid committing secrets or unrelated files.

---

## Step 4 — Update and prune MEMORY.md + memory files

Read the current memory files at `.claude/projects/-Users-Nathan-IdeaProjects-vibing-realestatev2/memory/`. You must:

### 4a — Update stale entries
For each section of MEMORY.md, cross-check against the current codebase state (read relevant files/run queries as needed). If the committed changes affect any recorded facts, update those memory files now.

### 4b — Remove redundant content
Remove memory content that is:
- Described by something already visible in the code (e.g. file paths, schema migrations already in `db/migrations/`)
- Superseded by newer facts in the same memory file
- No longer true given the changes just committed
- Overly granular detail that clutters the index without aiding future recall

### 4c — Add new memory for non-obvious facts
If the committed changes introduced:
- A new gotcha, constraint, or integration detail not obvious from reading the code
- A decision or tradeoff that future-Claude should know
- A new API endpoint, table, or component that belongs in the index

...write a new or updated memory file and add a pointer to MEMORY.md.

### 4d — Keep MEMORY.md under ~150 lines
If MEMORY.md is approaching 200 lines, consolidate related bullets or remove anything derivable from `git log` or the codebase.

---

## Step 5 — Report

Summarise:
- Which commits were made (type, subject, files)
- Which memory entries were updated, removed, or added
- Any concerns or follow-up items noticed during the sweep
