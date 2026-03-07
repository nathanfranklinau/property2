import { Pool } from "pg";

// Singleton pool — reused across all API route invocations in dev and prod.
// Next.js hot-reload in dev can create multiple module instances, so we
// attach the pool to the global object to prevent connection exhaustion.

declare global {
  // eslint-disable-next-line no-var
  var _pgPool: Pool | undefined;
}

function createPool(): Pool {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL environment variable is not set");
  }
  return new Pool({
    connectionString: process.env.DATABASE_URL,
    max: 3,
    idleTimeoutMillis: 10_000,
    connectionTimeoutMillis: 5_000,
    allowExitOnIdle: true,
  });
}

export const db: Pool =
  globalThis._pgPool ?? (globalThis._pgPool = createPool());
