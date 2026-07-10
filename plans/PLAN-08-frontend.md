# PLAN-08: Vite + React SPA in the "Kinetic Command" Design Language

Goal: the full frontend from SPEC Doc 07 as a Vite + React SPA, implemented in the Kinetic Command visual system defined by the design files in `..\Design\`: deep matte black, vibrant orange, glassmorphism panels, JetBrains Mono HUD typography, the breathing Hermes orb, and the GATE_LOCKED safety intercept. Static build served by nginx in production, dev proxied to the API so SameSite=Strict cookies work.

Prerequisites: PLAN-03 for data, full value after PLAN-04. Spec references: SPEC Doc 07, 5, 2.2, 2.3, the PLAN-03 WS event contract.

## Design sources (read these before writing any UI code)

```
..\Design\kinetic_command\DESIGN.md                 The design system: tokens, brand, elevation, shapes
..\Design\odin_dashboard\code.html                  Dashboard mockup (canonical layout + tailwind token config)
..\Design\hermes_contextual_chat\code.html          Chat mockup (bubbles, telemetry flow, context panel)
..\Design\odin_file_explorer\code.html              File explorer mockup (tree, dropzone, metrics panel)
..\Design\odin_task_management\code.html            Task board mockup (4-column kanban)
..\Design\odin_optimized_dashboard_hud\code.html    Denser dashboard variant (reference only)
..\Design\a_high_tech_glowing_orange_energy_sphere_or_orb_representing_a_sophisticated_ai\screen.png   Hermes orb mood reference
```

The `screen.png` files inside the mockup folders are broken exports (text placeholders), except the orb render above. The `code.html` files are the ground truth. The mockups embed a Tailwind config block near the top of each file: that block, not the DESIGN.md frontmatter, is what the mockup classes were written against. Copy tokens from the mockup config.

## The design system in five rules

1. **Canvas:** near-black everything. `background: #131313`, sidebar and console on `terminal-black #050505`, containers step up through `#0e0e0e`, `#1c1b1b`, `#20201f`, `#2a2a2a`, `#353535`. Depth comes from tonal layering and glows, never grey drop shadows.
2. **One accent, used loudly:** vibrant orange `#ff6b00` (primary-container) with soft peach `#ffb693` (primary) for text accents, amber `#ffba20` / `#FFB800` for "proactive" signals, `#00E676` status-safe, `#FF3D00` status-critical. Orange glow shadows on anything interactive or alive: `shadow-[0_0_15px_rgba(255,107,0,0.3)]`.
3. **Glassmorphism for elevated surfaces:** panels float over a faintly lit background using translucency plus blur plus a 1px orange-tinted border (the exact recipe is in Step 2). Glass is for widgets, headers, the chat assistant bubble, and modals. Flat tonal surfaces are for the sidebar, console, and inputs.
4. **Dual type:** JetBrains Mono for headlines, labels, data, logs, and timestamps; Inter for body and chat prose. Section headers are `label-caps`: 11px, 700, uppercase, 0.1em tracking, underscore_styled like `PRIORITY_QUEUE`.
5. **Soft-brutalist shapes:** small radii (4 to 8px) on cards and buttons. The single exception is the Hermes orb: a perfect glowing circle that breathes.

## Files (frontend tree)

```
frontend\package.json  vite.config.ts  tsconfig.json  index.html  tailwind.config.js  postcss.config.js
frontend\src\main.tsx  App.tsx  router.tsx
frontend\src\styles\index.css            (tokens, glass, effects, scrollbar, reduced-motion)
frontend\src\assets\                     (orb image if used, self-hosted anything)
frontend\src\lib\api.ts  ws.ts  auth.ts  types.ts  format.ts
frontend\src\stores\ui.ts
frontend\src\hooks\useDashboard.ts  useTasks.ts  useConversations.ts  useFiles.ts  useKnowledge.ts  useMemory.ts
frontend\src\components\AppShell.tsx  Sidebar.tsx  TopBar.tsx  ConsoleDock.tsx  ProtectedRoute.tsx
frontend\src\components\GlassPanel.tsx  HermesOrb.tsx  ProgressRing.tsx  StatChip.tsx  LabelCaps.tsx  Toast.tsx
frontend\src\components\chat\ChatMessage.tsx  TelemetryFlow.tsx  ApprovalModal.tsx  ContextPanel.tsx  ChatInput.tsx  ThreadSidebar.tsx
frontend\src\components\tasks\TaskBoard.tsx  TaskCard.tsx
frontend\src\components\files\FileTree.tsx  UploadDropzone.tsx
frontend\src\pages\Login.tsx  Dashboard.tsx  Chat.tsx  Tasks.tsx  Files.tsx  Knowledge.tsx  Memory.tsx
frontend\Dockerfile
```

## Steps in order

### Step 1: scaffold with self-hosted assets

Vite React-TS template, Tailwind, React Router v6, @tanstack/react-query, Zustand. Then:

1. Fonts: `npm install @fontsource/inter @fontsource/jetbrains-mono material-symbols` and import the needed weights (Inter 400/500/700, JetBrains Mono 400/600/700, material-symbols outlined) in `main.tsx`. NEVER link fonts.googleapis.com or use the Tailwind CDN script from the mockups; production CSP is `default-src 'self'` (PLAN-10) and external origins will be blocked.
2. `tailwind.config.js`: copy the `colors`, `borderRadius`, `spacing`, `fontFamily`, and `fontSize` blocks VERBATIM from the `tailwind.config` script at the top of `..\Design\odin_dashboard\code.html` into `theme.extend`. That config is what every mockup class was authored against.
3. `vite.config.ts` dev proxy (unchanged requirement, cookies depend on it):

```ts
server: {
  port: 5173,
  proxy: {
    "/api": { target: "http://localhost:8000", changeOrigin: true },
    "/ws":  { target: "ws://localhost:8000", ws: true },
  },
},
```

### Step 2: the design foundation (styles\index.css + primitives)

`index.css` defines, in this order:

1. Base: `color-scheme: dark;` on `:root`, body `bg-background text-on-surface`, selection `selection:bg-primary-container selection:text-on-primary-container`.
2. **The ambient layer.** Glass over pure black looks like flat grey; blur needs something behind it. Add a fixed, pointer-events-none background layer on the app shell: a radial orange glow anchored top-right (`radial-gradient(600px circle at 85% 10%, rgba(255,107,0,0.07), transparent 60%)`), a second faint amber glow bottom-left, and the dot grid from the mockup (`background-image: radial-gradient(circle, rgba(255,182,147,0.06) 1px, transparent 1px); background-size: 20px 20px;`). Subtle is correct; if you can clearly "see" the gradients, halve the alphas.
3. **The glass recipe** (verbatim from the mockups):

```css
.glass-panel {
  background: rgba(26, 26, 26, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 107, 0, 0.1);
}
```

Usage tiers: `.glass-panel` for widgets/cards/modals; translucent bars use Tailwind utilities `bg-background/80 backdrop-blur-md` (top bar), `bg-surface-container-lowest/80 backdrop-blur-md` (chat input dock), `bg-terminal-black/95` (console, no blur needed); modal overlay `bg-background/80 backdrop-blur-sm`.

4. **Signature effects:**

```css
@keyframes breathe {
  0%, 100% { transform: scale(1);   filter: drop-shadow(0 0 5px rgba(255, 107, 0, 0.4)); }
  50%      { transform: scale(1.1); filter: drop-shadow(0 0 20px rgba(255, 107, 0, 0.7)); }
}
.hermes-orb { animation: breathe 4s ease-in-out infinite; }

.terminal-blink::after { content: '_'; animation: blink 1s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #050505; }
::-webkit-scrollbar-thumb { background: #353535; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #ff6b00; }

.drag-zone-active { border-color: #ff6b00 !important; background: rgba(255, 107, 0, 0.05) !important; }

@media (prefers-reduced-motion: reduce) {
  .hermes-orb, .animate-pulse, .animate-ping, .animate-spin { animation: none !important; }
}
```

5. **Primitives:**
- `GlassPanel.tsx`: div with `glass-panel p-4 rounded-xl` plus an optional `label` prop rendering the label-caps header row with a bottom `border-glass-border` divider, exactly like the mockup widgets.
- `HermesOrb.tsx`: pure CSS orb (no hotlinked image; the mockups' googleusercontent URLs are dead ends and CSP-blocked). A circle with `background: radial-gradient(circle at 35% 30%, #ffdbcc 0%, #ff6b00 35%, #7a3000 75%, #351000 100%)`, class `hermes-orb`, size via prop. Props: `state: "idle" or "thinking"`; thinking drops the animation duration to 1.5s. Optionally crop the Design folder's orb render into `src\assets\hermes-orb.png` as a masked circle instead; either passes.
- `ProgressRing.tsx`: the SVG from the dashboard mockup (r=42, stroke-width 6, `stroke-dasharray 263.8`, offset computed from percent, `stroke-linecap round`, drop-shadow glow in the ring color, centered mono percentage).
- `StatChip.tsx`: the header stat block: `bg-surface-container px-4 py-2 border-l-2` with a color prop for the border, label-caps title at 50% opacity, headline-md mono value.
- `LabelCaps.tsx`: span with `text-label-caps font-label-caps uppercase tracking-widest`.

### Step 3: api.ts, auth.ts, token strategy (unchanged engineering)

- Access token in memory only (module variable + Zustand), NEVER localStorage. Refresh token stays in the httpOnly cookie.
- Fetch wrapper: `credentials: "include"`, `Authorization: Bearer`, `X-Interface-Origin: web`. On 401: single-flight refresh, retry once, then logout and route to /login.

### Step 4: AppShell (the three-zone layout every page shares)

Matches the dashboard and chat mockups exactly:

- **Sidebar** (fixed left, `w-sidebar-width` = 280px, `bg-terminal-black`, `border-r border-glass-border`): brand header = small orb + "ODIN" in headline-md primary + "System Active" label-caps at 60% opacity. Nav items: `flex items-center px-4 py-3 space-x-3 rounded-xl` with a material symbol + label-caps text; inactive = `text-on-surface-variant hover:text-primary hover:bg-surface-container-high`; active = `bg-primary-container text-on-primary-container shadow-[0_0_15px_rgba(255,107,0,0.3)] scale-95`. Items: Dashboard (grid_view), Chat (forum), Tasks (checklist), Files (folder_open), Knowledge (auto_stories), Memory (psychology). The mockups also show a Learning item (school): render it disabled with a "SOON" label-caps tag; there is no /learning route in this build. Footer group above the border: Sync (sync) opening a Syncthing status toast, Settings (settings).
- **TopBar** (h-16, `bg-background/80 backdrop-blur-md border-b border-glass-border`): left = `ORCHESTRATOR // ODIN_V1` in label-caps tertiary-container plus the active-project tabs (primary underline on the active one); center = the Hermes orb (state "thinking" while any run is active, driven by `runs:active` from the dashboard payload or an open stream); right = search input styled `bg-surface-container-low rounded-full text-code-sm text-primary` with placeholder `QUERY_SYSTEM...` (wired to the PLAN-03 message search), notification bell with an orange dot when unread > 0, and the user chip.
- **ConsoleDock** (fixed bottom, `bg-terminal-black/95 border-t border-glass-border`): on the Dashboard it is the full 200px console (Step 6); on other pages it collapses to a 48px status strip: terminal icon, last activity_log line in `text-code-sm text-status-safe/80`, connection dot (ping animation when the events WS is live), and a blinking `odin@system:~$ _` cursor at idle.
- z-index ladder (document it in AppShell): sidebar 50, top bar 40, console 40, toasts 90, GATE_LOCKED modal 100. Anything portal-rendered goes to document.body; backdrop-filter creates stacking contexts that will otherwise clip popovers.

### Step 5: Login.tsx (TOTP-aware, in-theme)

Centered `glass-panel rounded-xl` card (max-w-sm) on the ambient background with a large idle orb above it. Inputs are terminal-styled: `bg-terminal-black border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary/30 rounded-lg font-code-sm`. Submit is the primary button: solid `bg-primary-container text-on-primary-container font-bold` with glow. The TOTP step swaps in a 6-digit code field; the 423 lockout renders the countdown as a disabled state in status-critical. The 2FA setup panel (post-login, in Settings) renders the provisioning URI as a QR (bundled `qrcode` package, no CDN) inside a glass panel and confirms with a test code.

### Step 6: Dashboard.tsx (per odin_dashboard\code.html)

- **Header row:** greeting in `font-headline-lg text-primary uppercase tracking-tighter`: "GOOD MORNING, {FIRSTNAME}" from the dashboard payload with a live `Weekday, Month D, YYYY // HH:MM:SS` mono line under it, updating every second. Right side: two StatChips (unread notifications count in primary; active runs count in tertiary).
- **Bento grid** (`grid grid-cols-12 gap-gutter`), left column `lg:col-span-4`:
  - `PRIORITY_QUEUE` GlassPanel (DASH-02, 03): each task row = `bg-surface-container-high/40 p-2 flex justify-between border-l-2` with the border color by priority (status-critical for high with a pulsing dot, primary for medium, on-surface-variant at 60% opacity for low), title in 11px bold mono, status/project in 9px uppercase under it, due date right-aligned mono, and a small action button (solid primary `RESOLVE`-style for high, outlined `VIEW` for others) opening the task. Rows are drag-handles for reorder (PATCH priority on drop between groups).
  - `ACTIVE_STREAMS` GlassPanel (DASH-05): grid of ProgressRings fed by `task.progress` events (label under each ring in 9px label-caps). Empty state: a dim "NO ACTIVE STREAMS" label-caps line.
- Right column `lg:col-span-8`:
  - A visualization GlassPanel (h-64) with the dot-grid overlay and a big centered status line (`SYSTEM NOMINAL` in headline-lg primary) plus a one-line summary (tasks due today, docs indexed this week). Decorative; do not block on data.
  - `RECENT_UPDATES` GlassPanel (DASH-04): the mono table from the mockup: label-caps 9px header row at 40% opacity, 11px mono body rows, `hover:bg-primary/5`, file-type material symbol in tertiary, click-to-download on the row action.
- **The 200px console** (dashboard only): left pane = live terminal feed of activity_log + notification events from the events WS, formatted `[HH:MM:SS] LEVEL: message` with WARN in system-amber and INFO in status-safe, capped at 200 lines; right pane (w-80, `border-l border-glass-border`) = `HERMES_DIRECT` mini chat (DASH-06): a ping-dot header, the last 2 exchanges, and a terminal-black input; submitting creates/continues a conversation and navigates to `/chat/:id`.

### Step 7: ws.ts and Chat.tsx (per hermes_contextual_chat\code.html)

ws.ts engineering is unchanged: `POST /api/v1/ws-ticket` first, then connect; fresh ticket per reconnect attempt; 4401 means fetch a new ticket; events socket app-wide, chat socket per conversation.

Chat layout, three zones inside the shell:

- **ThreadSidebar** (w-72, `bg-surface-container-lowest border-r border-glass-border`): conversations grouped by project then date (CHAT-01); active thread = `bg-surface-container-high rounded-lg border-l-2 border-primary`; others hover to surface-container-low. A "Knowledge Bases" group below lists indexed KB documents for the linked project with a green `Active` chip (from the KB status endpoint).
- **Message area:**
  - User message: right-aligned, `max-w-[80%] bg-surface-container-high px-5 py-4 rounded-xl rounded-tr-none border border-glass-border`, timestamp under it as `USER // 14:40:21` in label-caps at 40% opacity.
  - Assistant message: left-aligned, `max-w-[85%] glass-panel rounded-xl rounded-tl-none` with the glowing accent: an absolute 1px-wide full-height `bg-primary shadow-[0_0_10px_rgba(255,107,0,0.5)]` bar on the left edge. Timestamp `ODIN // 14:41:05` in primary at 60%. Markdown via a sanitizing renderer; code blocks render as the mockup: `bg-terminal-black rounded-lg border border-outline-variant` with a label-caps header (`PYTHON // FILE.PY`), status-safe mono text, and a copy icon appearing on hover.
  - **TelemetryFlow** (tool.start / tool.result events): the indented block from the mockup: `border-l-2 border-primary/20 ml-4 pl-6 py-2`, a status-safe row with a spinning `sync` symbol and `EXECUTING: {tool}` in code-sm uppercase, then the result summary inside a `bg-terminal-black/50 border border-outline-variant/30 rounded-lg p-3` log box. On tool.result flip the spinner to a check (status-safe) or an error mark (status-critical).
  - **Streaming:** deltas append to a ref-buffered bubble flushed on animation frames. While streaming, the live bubble uses SOLID `bg-surface-container-low` and swaps its classes to `glass-panel` on message.done (repainting inside a backdrop-filtered element every frame is the number one jank source in this design).
- **ChatInput** (bottom dock, `bg-surface-container-lowest/80 backdrop-blur-md border-t border-glass-border`): auto-growing textarea styled `bg-terminal-black border border-outline-variant focus:border-primary rounded-xl`, attach_file icon (chat upload, CHAT-05) and mic icon (disabled placeholder for now), and the send button: `bg-primary-container h-14 w-14 rounded-xl` with glow, `hover:scale-105 active:scale-95`. Under it the status row: `Secure Channel` dot plus the token-budget total from the last POST metadata, both in 10px label-caps at 40%.
- **ContextPanel** (w-80, right, hidden below xl, CHAT-03): `ACTIVE CONTEXT` project card (label-caps header with `border-b border-primary/20`), `ACTIVE MEMORIES` list: psychology symbol in tertiary + memory key + `Recall weight: 0.942` in 10px (weight = 1 minus distance, from POST metadata if provided, else omit the number), and at the bottom `TOKEN BUDGET`: the glowing 1px progress bar (`bg-primary h-full shadow-[0_0_10px_rgba(255,107,0,0.5)]`) showing total vs model limit with two terminal-black tiles (provider, latency of last turn).
- **ApprovalModal (GATE_LOCKED, per the dashboard mockup's safety intercept):** full-screen overlay `bg-background/80 backdrop-blur-sm z-[100]`, centered `w-[400px] bg-terminal-black border-2 border-primary shadow-[0_0_50px_rgba(255,107,0,0.4)]`; header bar `bg-primary p-3` with a lock symbol and `GATE_LOCKED` in on-primary bold; body: the sentence ("Hermes requests {tool}"), an args preview in a `bg-surface-container p-3 text-code-sm` block, a "remember for this project" checkbox, then `APPROVE_EXECUTION` (full-width solid primary, `active:scale-95`) and `ABORT_SEQUENCE` (full-width outlined, label-caps). Driven by `gate.locked` events AND reconstructable from the persisted marker message on reload.

### Step 8: Tasks.tsx (per odin_task_management\code.html)

A four-column kanban board, each column headed by a label-caps title with its accent color:

| Column | Header color | Contents |
|---|---|---|
| QUEUE | on-surface | tasks with status `todo` |
| ACTIVE_PROCESSING | primary | tasks with status `in_progress` |
| SAFETY_INTERCEPTS | system-amber | pending GATE_LOCKED approvals (from gate.locked events / marker messages), each card opening the ApprovalModal |
| ARCHIVED | status-safe | status `done`, with a toggle to include `archived` |

Cards are GlassPanels (p-3, rounded-lg) with priority border-l-2 color coding, subtask progress (`2/5` mono chip), due date, and an expand revealing the subtask checklist and the changelog (from PLAN-03). Dragging a card between QUEUE and ACTIVE_PROCESSING PATCHes status (the SAFETY_INTERCEPTS column is not a drop target). `task.changed` events invalidate the board query. Filters (project, priority) as label-caps pill toggles above the board.

### Step 9: Files.tsx and Knowledge.tsx (per odin_file_explorer\code.html)

- Files: left = the lazy tree in a GlassPanel (folders dirs-first, material symbols, mono 13px names, hover primary tint); center = the selected directory as the mono table (name, size, mtime, download/delete row actions); the whole center is an UploadDropzone: on dragover apply `.drag-zone-active` (orange border + tint), upload with a progress bar (XHR for progress), surface the 50 MB / allowlist rejections as toasts. Right = `SYSTEM METRICS` panel with StatChips (file count, workspace size, last sync) and the conflict notices (`.sync-conflict` notifications) in system-amber.
- Knowledge: upload zone + document status table (processing spinner in tertiary, indexed check in status-safe, warning rows in system-amber for scanned PDFs), the semantic search box styled like the top-bar search, results as GlassPanels showing the chunk text, score bar, and citation chip `[Source: file.pdf, p.4]` in label-caps; a note composer (terminal textarea) for KB-03.

### Step 10: Memory.tsx

Three tabs in label-caps (ACTIVE / SUGGESTIONS / REVIEW). Active: rows with the psychology symbol, key, value, access count, edit/archive actions. Suggestions: each card shows the proposed value; conflicts render the existing explicit memory beside it in a status-critical bordered panel with "KEEPS EXPLICIT" messaging; approve = solid primary, reject = outlined. Review: the stale list plus a capacity bar (active count vs 1000) in the glowing-bar style.

### Step 11: production Dockerfile (unchanged)

Multi-stage `node:20` build then `nginx:alpine` serving `dist/` with SPA fallback and immutable cache headers on hashed assets. `VITE_API_BASE=/api/v1` stays relative; fonts and icons are bundled so the PLAN-10 CSP (`default-src 'self'`) passes untouched.

## Edge cases a weaker model would miss

1. **The mockups' external resources are landmines.** Google Fonts links, the Tailwind CDN script, and the googleusercontent orb images must NOT be carried into the app: production CSP is `default-src 'self'` and all of them die. Self-host fonts and icons (Step 1), draw the orb in CSS (Step 2).
2. **Copy the Tailwind tokens from the MOCKUP config, not DESIGN.md.** The two disagree on borderRadius (DESIGN.md says `full: 9999px`; the mockup config says `full: 0.75rem`, and every mockup class was written against the mockup values). Mixing them turns every `rounded-full` chip into a pill and every card square. Mockup config wins.
3. **Glass needs light behind it.** Without the ambient glow layer (Step 2.2), `rgba(26,26,26,0.6)` + blur over `#131313` renders as flat grey and the whole effect silently disappears. If a panel looks flat, the background layer is missing or z-ordered wrong, not the panel.
4. **Never stream tokens into a backdrop-filtered element.** Repainting inside `backdrop-filter` recomposites the blur every frame; at Opus streaming speed that is visible jank. Solid surface while streaming, swap to glass on message.done (Step 7). Same rule for the live console feed: the console is `bg-terminal-black/95` WITHOUT blur on purpose.
5. **Limit concurrent blur surfaces.** Glass on widgets, top bar, input dock, and one modal is fine; do not add backdrop-blur to every row, chip, and hover state. If scrolling the dashboard stutters, count the blur layers first.
6. **backdrop-filter creates stacking contexts.** Dropdowns/popovers rendered inside a GlassPanel get clipped; portal them to document.body and follow the z-index ladder in Step 4.
7. **Reduced motion is not optional.** The breathe, ping, pulse, spin, and blink animations all stop under `prefers-reduced-motion: reduce` (Step 2.4 handles it); the orb then signals "thinking" by swapping to a brighter static glow.
8. **The mockups' 9 to 10px microtext is decorative only.** Real interactive text keeps a floor: 11px label-caps for labels, 13px code-sm for data, 14px+ for body. Sub-11px mono on Windows ClearType is unreadable.
9. **Uppercase underscore labels are presentational.** `PRIORITY_QUEUE` is fine visually, but give interactive elements human-readable `aria-label`s ("Priority queue"); never screen-read underscores.
10. **The Learning nav item has no route.** Render it disabled with a SOON tag rather than a dead link (matches mockups without inventing a page).
11. **SAFETY_INTERCEPTS is not a task status.** The kanban column is populated from pending approvals, not from the tasks table; dragging into it is meaningless and must be disabled.
12. **Access token in memory only; single-flight refresh; fresh WS ticket per reconnect; Vite proxy or the Strict cookie dies.** (Carried from the engineering plan; still the top functional traps.)
13. **Orange-on-black contrast:** body text stays `on-surface #e5e2e1`; peach `#ffb693` is for accents and headings, never long paragraphs; 50%-opacity text never sits on interactive controls.

## Acceptance criteria (verify each)

Use the browser preview tooling against `http://localhost:5173` with the dev stack up.

1. `npm run build` succeeds; serving `dist/` shows ZERO requests to external origins in the network tab (fonts, icons, orb all self-hosted).
2. Login page: glass card over the ambient glow, orb breathing above it; login with the seed user lands on the dashboard; reload keeps the session.
3. Dashboard matches the mockup structure: uppercase mono greeting with live clock, PRIORITY_QUEUE rows with colored left borders and pulsing critical dot, ACTIVE_STREAMS rings, RECENT_UPDATES mono table with hover tint, 200px console at the bottom streaming real activity events, HERMES_DIRECT mini chat that promotes to /chat on submit.
4. Screenshot proof of glassmorphism: a widget screenshot where the blurred ambient glow is visible through a `glass-panel` (the panel edge shows the 1px orange-tinted border).
5. Chat: user bubble right with cut top-right corner, assistant bubble glass with glowing left accent bar, `ODIN // HH:MM:SS` timestamps, a TelemetryFlow block appears during a tool call, code blocks show the header + hover copy icon, streaming stays smooth (no visible jank) and the live bubble turns glass when done.
6. GATE_LOCKED: request a file write; the modal appears with the orange header, args box, and APPROVE_EXECUTION; approving writes the file; reloading mid-gate re-shows the modal from the marker message.
7. Tasks: four columns with the correct header colors; dragging QUEUE to ACTIVE_PROCESSING persists status todo to in_progress; a pending approval shows in SAFETY_INTERCEPTS and opens the modal.
8. Files: dragging a file over the pane lights the orange drag-zone; a 50 MB+ upload shows the rejection toast; Knowledge shows the document reaching indexed and a search result with a citation chip.
9. The Hermes orb switches to the fast "thinking" animation while a chat run is active and returns to idle after message.done.
10. With OS reduced-motion enabled, no element animates, and the app remains fully usable.
11. Emulate a mid-range device (4x CPU throttle in devtools): dashboard scroll and chat streaming stay usable; if not, reduce blur surfaces per edge case 5 and re-verify.
