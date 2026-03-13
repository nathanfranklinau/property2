---
description: "Main instructions file for all rules"
applyTo: "*"
---

# Simplicity & Anti-Overengineering Rules

## Core Principle
- Solve the problem at hand. Do not solve problems that don't exist yet.

## Solution Design
- Prefer the simplest solution that satisfies the requirements
- Do NOT add abstractions, layers, or patterns unless they are needed RIGHT NOW
- Do NOT anticipate future requirements — build for today, refactor when the future arrives
- If a function, a variable, or a plain object works, do not reach for a class
- Avoid design patterns unless the problem clearly calls for one
- Avoid creating new files, modules, or directories unless the code genuinely warrants it

## Code Style
- Short, readable functions over long "flexible" ones
- Inline logic is fine for simple cases — avoid premature extraction
- Duplication is acceptable; over-abstraction is worse than mild repetition
- Prefer explicit code over clever code

## Dependencies & Infrastructure
- Do NOT introduce new libraries or tools without asking first
- Do NOT add configuration systems, plugin architectures, or dynamic loaders unless explicitly requested
- Avoid wrapping native APIs or built-in language features unnecessarily

## When Asked to Improve or Refactor
- Fix what is broken or asked for — do not refactor unrelated code
- Do NOT expand scope beyond the stated task
- If you see an opportunity to simplify, mention it — but do not act on it uninstructed

## Check Yourself Before Responding
- Ask: "Is this the simplest thing that works?"
- Ask: "Am I adding this because it's needed, or because it seems like good practice?"
- If the answer to the second question is yes → remove it

## Fallbacks & Mock Data
- NEVER use fallback values, default data, or mock/stub data unless explicitly told to
- NEVER implement fallback logic or error-recovery paths unless explicitly asked — if something fails, let it fail visibly
- If real data is unavailable, missing, or failing — STOP and tell the user; do not substitute silently
- Do NOT hardcode placeholder values, example responses, or dummy content as a workaround
- Do NOT add "temporary" fallbacks with the intention of replacing them later
- If an API, service, or data source fails — surface the real error; do not mask it with a default
- When a function would return nothing, return nothing (null/empty/error) — do not invent a value