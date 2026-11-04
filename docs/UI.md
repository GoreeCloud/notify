# GoreeCloud UI alignment

Authority: [`GoreeCloud/gc-ui`](https://github.com/GoreeCloud/gc-ui), specifically `docs/DESIGN_LANGUAGE.md`, `docs/COMPONENTS.md` and `registry/design-authority.v1.json`.

The initial Notify browser experience adopts the original GC UI language: calm canvases, tonal surfaces and limited lens-like depth; semantic `--gc-` tokens; 4px spacing increments; 12/18/26px rounded shapes; responsive sidebar-to-top navigation; deliberate typography and low-noise color hierarchy; visible keyboard focus and a reduced-motion/contrast fallback.

The web console contains meaningful controls only: authenticated connect/disconnect, channel selection, message composition, live SSE notifications, priority filtering, and clearing the **view** (not deleting server data). Browsers cannot silently authenticate; the token is held in memory only, and the UI clearly warns before attempting remote HTTP credentials.

**Verification gap:** this is a locally original adaptation, not a claim of passing a formal GoreeCloud UI visual acceptance review or using the published `@goreecloud/gc-ui` package. Responsive and assistive-tech visual regression checks remain required for release readiness.
