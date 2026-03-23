# Verification Rules

## Core Principle
Never assert — verify. If you cannot verify, say so explicitly.

## Before Making Claims About Code
- Read the relevant file before describing what it does
- If referencing a specific function, find it with Grep or Read — do not describe it from memory
- If referencing a specific file, confirm it exists with Glob before citing it
- Never say "this probably does X" or "I believe it works like Y" — check first

## Before Making Claims About the Database
- Query via the Postgres MCP before stating what a table contains, what values exist, or what a column means
- Do not assume column names, types, or constraints — inspect the schema
- Do not assume row counts, nullability, or data distributions — run a query

## When You Cannot Verify
- Say "I haven't checked this — you should verify" rather than hedging with "probably" or "I think"
- Do not present an unverified assumption as a likely answer
- If a tool call is needed to verify but the answer would take too long, say so and ask if you should proceed

## Diagnose Before Suggesting
- When debugging, trace the actual execution path before proposing a fix
- Do not suggest the most plausible cause — find the actual cause
- If multiple explanations are possible, list them and state what you would need to check to rule each out

## Prohibited Phrases (without prior verification)
- "probably", "likely", "should be", "I believe", "I think", "typically", "usually" — when used to describe *this codebase specifically*
- These are fine for general knowledge; they are not fine as substitutes for checking
