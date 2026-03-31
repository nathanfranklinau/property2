/**
 * /dev/plan-icons — visual reference for all plan type icons.
 * Development only — not linked from the main app.
 */

import { PlanTypeIcon, getPlanRegistration, PLAN_REGISTRATION_INFO } from "@/components/PlanTypeIcon";

const EXAMPLES: { plan: string; label: string }[] = [
  { plan: "RP79217", label: "RP79217" },
  { plan: "SP133707", label: "SP133707" },
  { plan: "BUP100650", label: "BUP100650" },
  { plan: "GTP11204", label: "GTP11204" },
  { plan: "CP123456", label: "CP123456" },
  { plan: "AP12345", label: "AP12345" },
  { plan: "NR9999", label: "NR9999" },
  { plan: "AG8888", label: "AG8888" },
  { plan: "XY0001", label: "XY0001 (unknown)" },
];

const SIZES = [
  { label: "w-3.5 h-3.5", cls: "w-3.5 h-3.5" },
  { label: "w-4 h-4", cls: "w-4 h-4" },
  { label: "w-5 h-5", cls: "w-5 h-5" },
  { label: "w-6 h-6", cls: "w-6 h-6" },
  { label: "w-8 h-8", cls: "w-8 h-8" },
  { label: "w-12 h-12", cls: "w-12 h-12" },
  { label: "w-20 h-20", cls: "w-20 h-20" },
];

export default function PlanIconsPreview() {
  return (
    <div className="min-h-screen bg-[#111118] text-white p-10 font-mono">
      <h1 className="text-2xl font-bold mb-2">Plan Type Icons</h1>
      <p className="text-zinc-500 text-sm mb-10">
        Component: <code className="text-zinc-300">web/components/PlanTypeIcon.tsx</code>
      </p>

      {/* ── All plan examples in a grid ── */}
      <section className="mb-14">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-5">
          All Plan Types
        </h2>
        <div className="grid grid-cols-3 gap-4">
          {EXAMPLES.map(({ plan, label }) => {
            const reg = getPlanRegistration(plan);
            const info = PLAN_REGISTRATION_INFO[reg];
            return (
              <div
                key={plan}
                className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-5 flex gap-4 items-start"
              >
                <PlanTypeIcon plan={plan} className={`w-8 h-8 flex-shrink-0 ${info.color}`} />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white">{label}</p>
                  <p className={`text-xs font-medium ${info.color} mb-1`}>{info.label}</p>
                  <p className="text-[11px] text-zinc-500 leading-relaxed">{info.description}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <span
                      className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                        info.subdivisible
                          ? "bg-emerald-500/15 text-emerald-400"
                          : "bg-zinc-700/50 text-zinc-400"
                      }`}
                    >
                      {info.subdivisible ? "Subdivisible" : "Not subdivisible"}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Icon size scale ── */}
      <section className="mb-14">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-5">
          Size Scale — Freehold (RP) Icon
        </h2>
        <div className="flex items-end gap-8 flex-wrap">
          {SIZES.map(({ label, cls }) => (
            <div key={label} className="flex flex-col items-center gap-3">
              <PlanTypeIcon plan="RP79217" className={`${cls} text-emerald-400`} />
              <span className="text-[10px] text-zinc-600">{label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── All icons at w-12 side by side ── */}
      <section className="mb-14">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-5">
          All Icons at w-12 — with theme colours
        </h2>
        <div className="flex items-start gap-10 flex-wrap">
          {(["RP79217", "BUP100650", "GTP11204", "CP123456", "AP12345", "XY0001"] as const).map(
            (plan) => {
              const reg = getPlanRegistration(plan);
              const info = PLAN_REGISTRATION_INFO[reg];
              return (
                <div key={plan} className="flex flex-col items-center gap-2">
                  <PlanTypeIcon plan={plan} className={`w-12 h-12 ${info.color}`} />
                  <span className="text-[10px] text-zinc-500">{info.shortLabel}</span>
                </div>
              );
            }
          )}
        </div>
      </section>

      {/* ── Dark background context (how they'll appear in sidebar) ── */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-zinc-500 mb-5">
          Sidebar Context — w-3.5 h-3.5 as row icons
        </h2>
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] divide-y divide-white/[0.04] max-w-sm">
          {EXAMPLES.slice(0, 5).map(({ plan }) => {
            const reg = getPlanRegistration(plan);
            const info = PLAN_REGISTRATION_INFO[reg];
            return (
              <div key={plan} className="flex items-center justify-between px-3 py-2.5 gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <PlanTypeIcon plan={plan} className={`w-3.5 h-3.5 flex-shrink-0 ${info.color}`} />
                  <span className="text-xs text-zinc-400 truncate">Plan Type</span>
                </div>
                <span className="text-xs font-semibold text-zinc-300 flex-shrink-0">
                  {info.label}
                </span>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
