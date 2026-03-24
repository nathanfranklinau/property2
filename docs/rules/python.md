# Python Rules

_Applies to: `data-layer/` — FastAPI service, import scripts, and tests._

---

## Guiding Philosophy

Follow PEP 8 (style) and PEP 20 (Zen of Python). The principles that matter most here:

- **Explicit is better than implicit** — no magic, no hidden behaviour
- **Simple is better than complex** — clarity beats cleverness, always
- **Readability counts** — code is read far more than it is written
- **If the implementation is hard to explain, it's a bad idea**

---

## Testing

Tests are not optional — they are how you know the code works.

- Write tests immediately after new logic. No test = no confidence it works.
- Test real behaviour, not implementation details. Tests break when the feature breaks, not when internals change.
- **No mocking of internal functions.** If you feel the urge to mock something you own, the code needs restructuring — not the test.
- **Unit / integration tests:** hit the real DB, no mocks.
- **Playwright / E2E tests:** these *are* the network boundary — no restrictions, run against real endpoints.
- Each test has one reason to fail. One assertion concept per test.
- Test names are sentences: `test_parse_location_address_returns_none_for_bare_lot_ref`.
- Flaky tests are fixed or deleted immediately. Never committed and ignored.

---

## Functions

- Functions do one thing. If you need "and" to describe it, consider splitting — but don't split for the sake of it. Function explosion is as bad as monoliths.
- Split when a function has genuinely distinct responsibilities, or when a piece would be independently testable.
- Pure functions over stateful ones wherever possible — same inputs, same outputs, no side effects.
- Prefer the simplest solution that reads clearly. Three readable lines beat a clever one-liner.

---

## Types & Safety

- Type every function signature — parameters and return type. Always.
- Use `X | None` when a value can be absent. Never leave it implicit.
- Use `TypedDict` or `dataclass` for structured data passed between functions. A dict with multiple keys is a type waiting to happen.
- Use `Literal` for fixed sets of valid values — statuses, plan prefixes, categories. Catches typos at type-check time, not runtime.
- `typing.cast()` makes no runtime guarantee — use `assert isinstance()` if you actually need the check.
- Never use mutable default arguments: `def f(x=[])` is a bug. Use `None` and assign inside.

---

## Error Handling

- Let errors surface. Do not catch exceptions to silence them.
- Catch the specific exception, not `Exception`. `except ValueError` not `except Exception`.
- Never `pass` in an except block. At minimum, log it.
- If a function can fail, surface it in the return type (`X | None`) or raise explicitly. Do not return `{}` or `""` as a silent failure.
- Scripts that fail must exit with a non-zero code and a clear message.

---

## Code Style

- `snake_case` — variables, functions, modules, files.
- `UPPER_SNAKE_CASE` — module-level constants.
- `PascalCase` — classes only.
- Boolean variables and functions: `is_`, `has_`, `should_` prefix.
- Names describe *what*, not *how*. `parse_address` not `run_regex_on_string`.
- No abbreviations unless universally understood (`url`, `id`, `db`).
- Line length ≤ 100 characters. Enforced via `ruff` or `flake8`.
- Declare variables immediately before use — minimises scroll-back and scope pollution.
- Keyword-only arguments (`*` separator) when positional order at the call site would be ambiguous.

---

## Documentation

**Document the WHY, not the WHAT.** The code already says what it does.

```python
# Bad — restates the code
count += 1  # increment counter

# Good — explains intent and constraint
# lot 9999 is QLD cadastre's sentinel for common property rows;
# more reliable than checking plan prefix alone
```

- Comment design decisions and the alternatives that were rejected.
- Document constraints imposed by external systems (API quirks, data format oddities, DB conventions).
- Inline comments belong *before* the non-obvious line, not after.
- A well-placed inline comment is worth more than a docstring that restates the signature.

---

## Edge Cases

Before writing defensive code for an edge case, reason through it:

1. **Can this actually happen** given the real data and system?
2. **What's the impact** — silent corruption, visible error, or nothing?
3. **Is code the right response** — or is a comment explaining why it's safe to ignore sufficient?

Not every edge case needs handling. "This only occurs if X, which is impossible because Y" is a complete resolution — document it inline and move on. Defensive code for impossible scenarios is noise that obscures real logic.

---

## FastAPI Routes

- Route handlers are thin: validate input, call a function, return the result. Business logic lives elsewhere.
- Use Pydantic models for request bodies and response shapes. No raw dicts crossing the API boundary.
- `async def` only when the function awaits something. Don't make everything async by default.
- Return meaningful HTTP status codes: `404` not found, `422` bad input, `500` unexpected failure.

---

## Import Scripts

- **Idempotent by default.** Running twice must not corrupt data — use `INSERT ... ON CONFLICT DO NOTHING` or pre-checks.
- Use explicit transactions. If part of a batch fails, roll it back cleanly.
- Log progress at meaningful intervals — not every row, not never.
- Never hardcode credentials — read from env.

---

## Modules & Imports

- Flat module structure over deep nesting. Prefer `from da_common import parse_address` over three levels of sub-packages.
- No `*` imports.
- Prefer explicit imports: `from module import specific_thing`.
- No side effects at import time — avoid module-level code that runs on import (slow startup, test brittleness, circular imports). Use `@cache` or lazy init patterns.

---

## Dependencies

- No new packages without asking first — check the stdlib before reaching for a library.
- Pin versions in `requirements.txt`: `requests==2.31.0` not `requests`.
- No `print()` in service layer code — use `logging`. `print()` is acceptable in one-off scripts.
- No `time.sleep()` as a fix — it always signals something needs to be done properly.
