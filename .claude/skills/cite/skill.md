---
name: cite
description: Verify a claim against authoritative sources and store the citation in docs/references.csv
user_invocable: true
arguments:
  - name: statement
    description: The claim or statement to verify and cite
    required: true
---

# Cite — Find and record an authoritative source for a claim

You have been asked to verify and cite the following statement:

**"${statement}"**

## Process

### Step 1 — Check existing references
Read `docs/references.csv` and check if this claim (or a closely related one) is already cited.
- If found and status is `verified`, report the existing citation and stop.
- If found and status is `unverified`, proceed to verify it.
- If not found, proceed to search.

### Step 2 — Search for authoritative sources
Use WebSearch to find the claim in authoritative sources. Prioritise in this order:
1. **Government / regulatory sources** (e.g. qld.gov.au, council planning scheme PDFs, legislation)
2. **Official planning scheme documents** (City Plan zone codes, state planning policy)
3. **Professional / industry bodies** (planning institutes, law firms citing legislation)
4. **Reputable secondary sources** (planning consultancies, university publications)

Run multiple searches with different phrasings to triangulate. Use WebFetch to read promising pages and extract the exact figure, section reference, and context.

### Step 3 — Verify the claim
Compare what the authoritative source says against the statement being cited.
- If the claim is **correct**: record it as `verified`
- If the claim is **partially correct** (e.g. right number but wrong scope): record it as `verified` with clarifying notes
- If the claim is **incorrect**: record it as `disputed` and note the correct value
- If **no authoritative source can be found**: record it as `unverified`

Report the finding to the user clearly, including:
- The exact value/fact from the source
- The authority (who published it)
- The document name and section/table reference
- The URL
- Whether our codebase value matches

### Step 4 — Update references.csv
Read the current `docs/references.csv`, then append (or update) a row with:
- `id`: next sequential REF-NNN
- `claim`: the statement being verified
- `value`: the specific figure or fact
- `source_authority`: who published it
- `source_document`: document title
- `source_section`: section, table, or page reference
- `source_url`: direct URL to the source
- `jurisdiction`: e.g. "QLD — Gold Coast"
- `zone_or_scope`: what zone/context this applies to
- `verified_date`: today's date (YYYY-MM-DD)
- `status`: verified | unverified | disputed
- `notes`: any caveats, where this is used in our codebase, discrepancies

Use the Edit tool to append to the CSV — do not rewrite the entire file.

### Step 5 — Flag codebase discrepancies
If the verified value differs from what our code uses (e.g. in `zone-rules.ts` or elsewhere), flag this to the user and suggest whether to update the code.

## Important
- Never fabricate a citation. If you cannot find an authoritative source, say so.
- Prefer primary sources (the actual legislation/planning scheme) over secondary summaries.
- Include the full URL so the user can verify independently.
- PDFs from .gov.au domains are considered authoritative for Australian planning claims.
