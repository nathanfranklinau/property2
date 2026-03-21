# PropertyProfiler Design System

**Version:** 1.0 — "Precision Instrument"
**Theme:** Deep violet-ink dark, high-contrast text hierarchy, precision data display.

---

## Design Philosophy

PropertyProfiler is a **precision instrument** — like a high-end navigation system or financial terminal. The interface must feel authoritative, readable, and calm. Data is the hero; chrome is invisible.

**Principles:**
1. **Contrast earns attention.** Hierarchy is created through contrast, not decoration.
2. **Every pixel of chrome should disappear.** Backgrounds, borders, and containers exist to organise information — they should never compete with data.
3. **Color communicates status.** Semantic colors (emerald = positive, amber = caution, red = danger) are functional. Don't use them decoratively.
4. **Density is intentional.** Pack information efficiently, but use spacing to breathe between sections.

---

## Color Palette

### App Shell (hardcoded hex in Tailwind arbitrary values)

| Token | Hex | Usage |
|-------|-----|-------|
| `--pp-bg-app` | `#131320` | Main app background, nav bar, tab bar |
| `--pp-bg-sidebar` | `#1a1a2e` | Right sidebar panel |
| `--pp-bg-map-load` | `#10101e` | Map loading skeleton |

### Surfaces & Overlays (CSS rgba)

| Class / Token | Value | Usage |
|-------|-------|-------|
| `bg-white/[0.025]` | ~rgba(255,255,255,0.025) | Section card backgrounds |
| `bg-white/[0.04]` | ~rgba(255,255,255,0.04) | Hover states |
| `bg-white/[0.05]` | ~rgba(255,255,255,0.05) | Active nav/tab hover |
| `bg-white/[0.10]` | ~rgba(255,255,255,0.10) | Active tab selected state |

### Borders & Dividers

| Class | Value | Usage |
|-------|-------|-------|
| `border-white/[0.08]` | ~rgba(255,255,255,0.08) | Primary borders (nav, sidebar, section cards) |
| `divide-white/[0.055]` | ~rgba(255,255,255,0.055) | Dividers between SidebarRows |
| `border-white/[0.07]` | ~rgba(255,255,255,0.07) | Subdivision search separator |
| `bg-white/[0.12]` | ~rgba(255,255,255,0.12) | Vertical dividers between big numbers |

### Text Hierarchy

| Tailwind Class | Role | Usage |
|-------|------|-------|
| `text-white` | Primary | Page title, address, key values |
| `text-zinc-200` | Elevated values | Big secondary numbers (free space, covered) |
| `text-zinc-300` | Data values | SidebarRow values, section titles |
| `text-zinc-300` | Labels | SidebarRow labels (replaces zinc-400 — more contrast) |
| `text-zinc-400` | Secondary labels | Big number metric labels, unit text |
| `text-zinc-500` | Muted / Icons | Row icons, chevrons, placeholder text |
| `text-zinc-500` | Fine print | Meta details, percentages |

> **Why zinc-300 for labels?** The previous zinc-400 labels blended into the dark background when adjacent to zinc-300 values. Shifting labels to zinc-300 increases readability without flattening the hierarchy — values can still be distinguished by font weight (semibold) and accent color.

---

## Semantic Colors

These are functional — always use them for their designated meaning.

| Color | Tailwind | Meaning |
|-------|----------|---------|
| Emerald | `emerald-400` | Positive, approved, within limits, environmental |
| Teal | `teal-400` | Moderate positive, medium density |
| Blue | `blue-400` | Informational, medium-high density, flood |
| Indigo | `indigo-400` | High density, nearby subdivisions (selected) |
| Purple | `purple-400` | Very high density, exceptional |
| Amber | `amber-400` | Warning, caution, heritage, pending |
| Orange | `orange-400` | Elevated risk, buffer areas |
| Red | `red-400/500` | Danger, refused applications, very high bushfire |
| Zinc | `zinc-400/500` | Neutral, withdrawn, lapsed |

### Badge Pattern
```tsx
<span className="text-[10px] bg-{color}-500/15 border border-{color}-500/25 px-2 py-0.5 rounded-full text-{color}-400">
  Label
</span>
```

---

## Typography

| Element | Classes | Notes |
|---------|---------|-------|
| Page address/title | `text-sm font-semibold text-white` | Top of sidebar |
| Section heading | `text-xs font-semibold tracking-wide text-zinc-200` | SidebarSection title |
| Big number (primary) | `text-4xl font-bold tracking-tight tabular-nums` | Lot size |
| Big number (secondary) | `text-2xl font-semibold tracking-tight tabular-nums text-zinc-200` | Free space, covered |
| Big number label | `text-[11px] text-zinc-400 uppercase tracking-wider font-medium` | "Lot Size", "Free", "Covered" |
| Sidebar row label | `text-xs text-zinc-300` | Standard data row |
| Sidebar row value | `text-xs font-semibold tabular-nums text-zinc-300` | Standard data value |
| Tab label | `text-xs font-medium` | Map tab bar |
| Fine print | `text-[10px] text-zinc-500` | Subtitles, meta, plan details |
| Constraint label | `text-xs text-zinc-300` | Overlay section labels |

**Font:** Geist Sans (loaded via `next/font/google`). `-webkit-font-smoothing: antialiased` applied globally.

---

## Components

### SidebarSection

A titled group of related data rows.

```tsx
<SidebarSection title="Your Property" icon={<GridIcon />} info="optional tooltip text">
  <SidebarRow icon={<PlanIcon />} label="Lot / Plan" value="1 / SP123456" />
</SidebarSection>
```

**Structure:**
- Header: icon + title + optional info (ⓘ) button with hover tooltip
- Card: `rounded-xl border border-white/[0.08] bg-white/[0.025] divide-y divide-white/[0.055]`

### SidebarRow

A single label/value data row.

```tsx
<SidebarRow
  icon={<Icon />}
  label="Label"
  value="Value"
  highlight={false}      // white text for emphasis
  valueColor="text-emerald-400"  // override value color
  tooltip="optional tooltip"
/>
```

**Anatomy:**
- Icon: `text-zinc-500` (20×20 SVG, strokeWidth 1.5)
- Label: `text-xs text-zinc-300`
- Value: `text-xs font-semibold tabular-nums text-zinc-300` (or highlight/valueColor)

### NavIcon

Icon button for the top navigation bar.

```tsx
<NavIcon tooltip="Home" href="/" active badge>
  <HomeIcon />
</NavIcon>
```

**States:**
- Default: `text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.05]`
- Active: `bg-emerald-500/15 text-emerald-400`
- Badge: small emerald dot indicator

### Tab Bar

```tsx
<button className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
  active ? "bg-white/[0.10] text-white" : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.05]"
}`}>
```

---

## Layout

```
┌─────────────────────────────────────────────────────┐
│ Nav (h-auto, px-3 py-2)            bg: #131320      │
├───────────────────────────┬─────────────────────────┤
│                           │                         │
│  Google Map (flex-1)      │  Sidebar (w-[380px])    │
│                           │  bg: #1a1a2e            │
│                           │  overflow-y-auto        │
│                           │  pp-sidebar-scroll      │
│                           │                         │
├───────────────────────────┤                         │
│ Tab Bar (px-2 py-1.5)     │                         │
│ bg: #131320               │                         │
└───────────────────────────┴─────────────────────────┘
```

**Key layout constraints:**
- `h-screen overflow-hidden` on root — no page scroll, internal scrolling only
- Sidebar uses `pp-sidebar-scroll` class for styled thin scrollbar
- Map fills `flex-1` of the left column

---

## Scrollbar

Custom styled for the sidebar:
```css
.pp-sidebar-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.08) transparent;
}
/* 4px wide, rounded, subtle thumb */
```

---

## Spacing System

| Area | Classes |
|------|---------|
| Sidebar outer padding | `p-5 space-y-5` |
| Sidebar row | `px-3 py-2.5` |
| Section card | `rounded-xl` |
| Tab item | `px-3.5 py-2` |
| Nav item | `p-2` |
| Big numbers gap | `gap-4` |
| Big number divider | `w-px h-8 bg-white/[0.12] mb-1` |

---

## Icons

All icons are inline SVG, `strokeWidth={1.5}`, `fill="none"`, `stroke="currentColor"`.

| Size | Classes | Context |
|------|---------|---------|
| Nav | `w-4.5 h-4.5` | Top nav buttons |
| Tab | `w-4 h-4` | Tab bar icons |
| Section header | `w-3.5 h-3.5` | SidebarSection titles |
| Row | `w-3.5 h-3.5` | SidebarRow leading icons |

**Icon colors:**
- Nav (inactive): `text-zinc-400`
- Section title: `text-zinc-300`
- Row leading: `text-zinc-500`
- Constraint/overlay: semantic color (`text-blue-500`, `text-amber-600`, etc.)

---

## Animation & Transition

- All interactive elements: `transition-all` or `transition-colors`
- Spinner: `animate-spin` (SVG)
- Loading skeleton: `animate-pulse`
- Active step indicator: `animate-pulse` (pulsing dot)
- Chevron rotation: `transition-transform` on expand/collapse

---

## Do / Don't

**Do:**
- Use `text-zinc-300` for all data labels and values unless a semantic color applies
- Use `text-zinc-500` for row icons (visible without competing with labels)
- Use `border-white/[0.08]` for all structural borders
- Use semantic colors to communicate status, not decoration

**Don't:**
- Use `text-zinc-600` or `text-zinc-700` for interactive/readable text — reserve for truly decorative elements
- Use `text-zinc-400` for labels (insufficient contrast on `#1a1a2e` background)
- Add decorative gradients or shadows — the design is intentionally flat
- Use more than 2 semantic colors in a single section
