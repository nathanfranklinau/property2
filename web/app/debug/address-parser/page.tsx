"use client";

import { useState, useRef, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ParseResult {
  building_name: string | null;
  unit_type: string | null;
  unit_number: string | null;
  level_type: string | null;
  level_number: string | null;
  lot_number: string | null;
  street_number: string | null;
  street_number_last: string | null;
  street_name: string | null;
  street_type: string | null;
  street_suffix: string | null;
  suburb: string | null;
  state: string | null;
  postcode: string | null;
}

interface LogEntry {
  id: number;
  input: string;
  result: ParseResult | null;
  error: string | null;
  ms: number;
}

const FIELDS: { key: keyof ParseResult; label: string }[] = [
  { key: "building_name",     label: "Building" },
  { key: "unit_type",         label: "Unit Type" },
  { key: "unit_number",       label: "Unit #" },
  { key: "level_type",        label: "Lvl Type" },
  { key: "level_number",      label: "Lvl #" },
  { key: "lot_number",        label: "Lot #" },
  { key: "street_number",     label: "St #" },
  { key: "street_number_last",label: "St # Last" },
  { key: "street_name",       label: "Street" },
  { key: "street_type",       label: "St Type" },
  { key: "street_suffix",     label: "Suffix" },
  { key: "suburb",            label: "Suburb" },
  { key: "state",             label: "State" },
  { key: "postcode",          label: "Postcode" },
];

// ─── CSV export ───────────────────────────────────────────────────────────────

function exportCsv(entries: LogEntry[]) {
  const headers = ["input", ...FIELDS.map(f => f.key), "ms", "error"];
  const rows = entries.map(e => [
    e.input,
    ...FIELDS.map(f => e.result?.[f.key] ?? ""),
    e.ms,
    e.error ?? "",
  ]);
  const csv = [headers, ...rows]
    .map(row => row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(","))
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `parse-address-${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AddressParserDebugPage() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState<LogEntry[]>([]);
  const idRef = useRef(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const parse = useCallback(async () => {
    const address = input.trim();
    if (!address) return;
    setLoading(true);
    const t0 = performance.now();
    try {
      const res = await fetch("/api/debug/parse-address", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address }),
      });
      const ms = Math.round(performance.now() - t0);
      if (!res.ok) {
        const err = await res.text();
        setLog(prev => [{ id: ++idRef.current, input: address, result: null, error: `${res.status}: ${err}`, ms }, ...prev]);
      } else {
        const result: ParseResult = await res.json();
        setLog(prev => [{ id: ++idRef.current, input: address, result, error: null, ms }, ...prev]);
      }
    } catch (e) {
      const ms = Math.round(performance.now() - t0);
      setLog(prev => [{ id: ++idRef.current, input: address, result: null, error: String(e), ms }, ...prev]);
    } finally {
      setLoading(false);
      setInput("");
      inputRef.current?.focus();
    }
  }, [input]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") parse();
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0d0d18",
      color: "#e2e2f0",
      fontFamily: "'Berkeley Mono', 'Fira Code', 'JetBrains Mono', 'Cascadia Code', ui-monospace, monospace",
      padding: "0",
    }}>
      {/* Header */}
      <div style={{
        borderBottom: "1px solid rgba(255,255,255,0.07)",
        padding: "20px 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "rgba(255,255,255,0.02)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: "#4ade80",
            boxShadow: "0 0 8px #4ade80",
            animation: "pulse 2s ease-in-out infinite",
          }} />
          <span style={{ fontSize: 11, letterSpacing: "0.18em", color: "#6a6a84", textTransform: "uppercase" }}>
            Debug
          </span>
          <span style={{ color: "rgba(255,255,255,0.15)", fontSize: 11 }}>/</span>
          <span style={{ fontSize: 13, color: "#a0a0b8", letterSpacing: "0.05em" }}>
            Address Parser
          </span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {log.length > 0 && (
            <>
              <span style={{ fontSize: 11, color: "#5a5a72" }}>{log.length} parsed</span>
              <button
                onClick={() => exportCsv([...log].reverse())}
                style={{
                  fontSize: 11,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  padding: "5px 12px",
                  background: "transparent",
                  border: "1px solid rgba(255,255,255,0.12)",
                  borderRadius: 4,
                  color: "#a0a0b8",
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
                onMouseEnter={e => {
                  (e.target as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.3)";
                  (e.target as HTMLButtonElement).style.color = "#ffffff";
                }}
                onMouseLeave={e => {
                  (e.target as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.12)";
                  (e.target as HTMLButtonElement).style.color = "#a0a0b8";
                }}
              >
                ↓ Export CSV
              </button>
              <button
                onClick={() => setLog([])}
                style={{
                  fontSize: 11,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  padding: "5px 12px",
                  background: "transparent",
                  border: "1px solid rgba(255,255,255,0.06)",
                  borderRadius: 4,
                  color: "#5a5a72",
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
                onMouseEnter={e => {
                  (e.target as HTMLButtonElement).style.color = "#a0a0b8";
                }}
                onMouseLeave={e => {
                  (e.target as HTMLButtonElement).style.color = "#5a5a72";
                }}
              >
                Clear
              </button>
            </>
          )}
        </div>
      </div>

      {/* Input bar */}
      <div style={{
        padding: "24px 32px",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
      }}>
        <div style={{
          display: "flex",
          gap: 10,
          maxWidth: 760,
        }}>
          <div style={{ position: "relative", flex: 1 }}>
            <span style={{
              position: "absolute",
              left: 14,
              top: "50%",
              transform: "translateY(-50%)",
              color: "#4a4a60",
              fontSize: 13,
              pointerEvents: "none",
              fontFamily: "inherit",
            }}>›</span>
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Enter address to parse…"
              autoFocus
              style={{
                width: "100%",
                padding: "11px 14px 11px 30px",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 6,
                color: "#e2e2f0",
                fontSize: 13,
                fontFamily: "inherit",
                outline: "none",
                letterSpacing: "0.02em",
                transition: "border-color 0.15s",
                boxSizing: "border-box",
              }}
              onFocus={e => (e.target.style.borderColor = "rgba(255,255,255,0.25)")}
              onBlur={e => (e.target.style.borderColor = "rgba(255,255,255,0.1)")}
            />
          </div>
          <button
            onClick={parse}
            disabled={loading || !input.trim()}
            style={{
              padding: "11px 22px",
              background: loading ? "rgba(99,102,241,0.3)" : "rgba(99,102,241,0.85)",
              border: "none",
              borderRadius: 6,
              color: "#ffffff",
              fontSize: 12,
              fontFamily: "inherit",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              cursor: loading || !input.trim() ? "not-allowed" : "pointer",
              opacity: !input.trim() ? 0.4 : 1,
              transition: "all 0.15s",
              whiteSpace: "nowrap",
            }}
          >
            {loading ? "Parsing…" : "Parse"}
          </button>
        </div>
        <p style={{ margin: "8px 0 0", fontSize: 11, color: "#4a4a60", letterSpacing: "0.05em" }}>
          Press Enter to parse · results accumulate below
        </p>
      </div>

      {/* Results table */}
      {log.length === 0 ? (
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "80px 32px",
          gap: 12,
          color: "#3a3a50",
        }}>
          <div style={{ fontSize: 32 }}>⌕</div>
          <p style={{ margin: 0, fontSize: 12, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            No addresses parsed yet
          </p>
        </div>
      ) : (
        <div style={{ overflowX: "auto", padding: "0" }}>
          <table style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 12,
            tableLayout: "auto",
          }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
                <th style={thStyle("#1a1a2a", true)}>Input Address</th>
                {FIELDS.map(f => (
                  <th key={f.key} style={thStyle("#1a1a2a", false)}>{f.label}</th>
                ))}
                <th style={thStyle("#1a1a2a", false)}>ms</th>
              </tr>
            </thead>
            <tbody>
              {log.map((entry, idx) => (
                <tr
                  key={entry.id}
                  style={{
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    background: idx === 0 ? "rgba(99,102,241,0.06)" : "transparent",
                    animation: idx === 0 ? "slideIn 0.2s ease-out" : "none",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={e => ((e.currentTarget as HTMLTableRowElement).style.background = "rgba(255,255,255,0.025)")}
                  onMouseLeave={e => ((e.currentTarget as HTMLTableRowElement).style.background = idx === 0 ? "rgba(99,102,241,0.06)" : "transparent")}
                >
                  <td style={{
                    padding: "9px 16px",
                    color: "#c8c8e0",
                    whiteSpace: "nowrap",
                    maxWidth: 280,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    borderRight: "1px solid rgba(255,255,255,0.05)",
                    fontWeight: 500,
                  }}>
                    {entry.error ? (
                      <span style={{ color: "#f87171" }} title={entry.error}>⚠ error</span>
                    ) : entry.input}
                  </td>
                  {FIELDS.map(f => {
                    const val = entry.result?.[f.key];
                    return (
                      <td key={f.key} style={{
                        padding: "9px 12px",
                        color: val ? "#e2e2f0" : "#2a2a3a",
                        whiteSpace: "nowrap",
                        letterSpacing: "0.02em",
                        borderRight: "1px solid rgba(255,255,255,0.03)",
                      }}>
                        {val ?? <span style={{ color: "#2a2a3a" }}>—</span>}
                      </td>
                    );
                  })}
                  <td style={{
                    padding: "9px 12px",
                    color: entry.ms < 100 ? "#4ade80" : entry.ms < 500 ? "#facc15" : "#f87171",
                    whiteSpace: "nowrap",
                    textAlign: "right",
                  }}>
                    {entry.ms}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        input::placeholder { color: #3a3a52; }
      `}</style>
    </div>
  );
}

function thStyle(bg: string, isFirst: boolean): React.CSSProperties {
  return {
    padding: "9px 12px",
    textAlign: "left",
    fontSize: 10,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    color: "#5a5a72",
    background: bg,
    whiteSpace: "nowrap",
    fontWeight: 500,
    position: isFirst ? "sticky" : "static",
    left: isFirst ? 0 : "auto",
    borderRight: "1px solid rgba(255,255,255,0.05)",
    borderBottom: "1px solid rgba(255,255,255,0.07)",
  };
}
