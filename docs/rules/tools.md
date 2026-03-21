# Tool Usage Rules

## Git Commits

Every completed task should result in a git commit. Commit regularly — do not batch up large amounts of unrelated changes.

## Postgres MCP

Use the Postgres MCP server to retrieve data from PostgreSQL.

**Use it for:** SELECT queries, schema inspection, counts, aggregations, checking relationships.

**Never use it for:** INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, TRUNCATE.
