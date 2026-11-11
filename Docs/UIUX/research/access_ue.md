# Ebony Hearts UI: accessibility and Slate acceptance criteria

Accessed 2026-11-09. Versions:
- **XAG**: Xbox Accessibility Guidelines v3.2 (published 2023-06-08; pages updated 2026-06-17).
- **WCAG**: WCAG 2.2 Recommendation (12 Dec 2024).
- **GAG**: gameaccessibilityguidelines.com.
- **Epic** pages are served as "UE 5.9 Documentation". Confirm command names in the 5.8 console.

**Proj** = project choice: no source gives a number.

**Conventions:**
- **Text size** is XAG "body height": highest ascender to lowest descender, in pixels of a 1920x1080 capture. Edge pixels count only if they have ≥2:1 contrast against the background (XAG 101). Measure rendered pixels, not the `FSlateFontInfo` size.
- **Contrast** uses (L1+0.05)/(L2+0.05), unrounded, so 4.499:1 fails. Measure against the lowest-contrast area of the background (XAG 102).
- **Viewing distance:** local two-player play on a TV, so the XAG console values apply. The PC values are the floor.

| Criterion | Measurable target for this game | Source | Notes |
|---|---|---|---|
| Text size | Essential text ≥ **26 px** at 1080p. Nothing below **18 px**. | XAG 101 "Text size" (console 26 / PC 18 px at 1080p; 52/36 at 4K). GAG "Use an easily readable default font size" (28 px TV floor). | Aim for 28 px; logo exempt. Test the smallest window: the canvas shrinks below 1080p. |
| Text scaling, glyphs | Text option up to **200 % (52 px)**, no content loss, no two-way scrolling. The letter inside a prompt glyph meets the text minimum and scales with text. | XAG 101 "Text scaling", "Icons and glyph sizes", "Text spacing"; XAG 112 | Move-list blocks: line spacing ≥ 1.5, ≤ 80 chars/line. |
| Text contrast | ≥ **4.5:1**. ≥ **3:1** for large text (≥ 52 px on TV). Inactive or locked text ≥ **3:1**. High-contrast mode ≥ **7:1**. | XAG 102 "Implementation guidelines" and summary chart; WCAG 1.4.3 (AA) | Violet on black is the risk; HUD text over stage art needs a plate or outline. XAG (not WCAG) covers inactive text. |
| Non-text contrast | ≥ **3:1** against adjacent colours for: health fill vs track, gauge segments, timer, round pips (won vs unwon), slider thumbs, toggles, focus ring. | WCAG 1.4.11 (AA); XAG 102 | Measure at the lightest part of a gradient. |
| Colour independence | Every colour meaning has a second cue: P1/P2 by label and side, recoverable health by pattern, full gauge by icon, locks by an icon. Passes greyscale and deutan, protan and tritan simulation. Key audio cues (round start, KO, low time) also have visual cues. | XAG 103; WCAG 1.4.1 (A); GAG "no essential information … by a fixed colour alone" | GAG notes that UE has a built-in simulator. |
| Focus visibility | Exactly one focus per player at all times. The indicator: a perimeter ≥ **3 px** at 1080p; ≥ **3:1** against both the unfocused state and the surroundings; also a non-colour change (weight, size or marker). It is never offscreen. Dialogs take focus and keep it. | XAG 113; WCAG 2.4.7 (AA), 2.4.11 (AA), 2.4.13 (AAA: 2 CSS px, 3:1) | 3 px is WCAG's 2 px × 26/18 for TV distance (Proj). P1/P2 select cursors differ by label, not only colour. |
| Navigation | Linear lists wrap, with an option to turn that off. Grids need not wrap. The same confirm and back buttons on every screen. Back works from every submenu. Focus order follows the layout. The prompt bar is in a fixed place. The full path from launch to quit works with the keyboard alone and with the D-pad alone, using single presses. **0** focus traps; remap capture mode shows how to exit. | XAG 112; XAG 107; WCAG 2.1.2 (A) | Scripted walk per device |
| Prompts and remapping | Every action can be remapped in-game, per player, on keyboard and pad, including Pause/Esc. Prompts in the HUD, training overlays and move list show the current binding and device within one frame. A reset to defaults exists. | XAG 107; GAG "Allow controls to be remapped" | Binding-conflict handling: Proj. |
| Holds and chords | No menu action needs a hold or a chord. Any hold has a press or toggle alternative. Gameplay chords have an optional simple-input alternative. | XAG 107; GAG "Avoid … buttons to be held down" | |
| Time limits | UI timers that are not core gameplay (select countdown, toasts, tips) can be turned off, extended ≥ **10×**, or dismissed. Warnings give ≥ **20 s** to extend. | XAG 116; WCAG 2.2.1 (A) | The round timer is core gameplay, so it is exempt. |
| Flashing | Captures pass PEAT or Harding:<br>• ≤ **3 flashes/s** over ≥ **20 %** of the screen. A flash is a ≥10 % luminance change where the darker state is < 0.8.<br>• The same applies to saturated red, R/(R+G+B) ≥ 0.8.<br>• No flash sequence lasts > **5 s**.<br>• No high-contrast stripe patterns: > 8 static stripes over ≥ 40 % of the screen, or > 5 moving stripes over ≥ 25 %. | XAG 118; WCAG 2.3.1 (A) and glossary; GAG "Avoid flickering images…" | WCAG's area is 25 % of a 10° field (341x256 at 1024x768). Use XAG's stricter 20 %. Never label a setting "epilepsy safe". |
| Motion | Toggles for screen shake, menu background animation and blinking UI. Anything that moves or blinks on its own for > **5 s** can be paused or hidden. | XAG 117; WCAG 2.2.2 (A); GAG "turn off / hide background movement" | |
| UI draw budget | At 60 fps, Slate game-thread time for the HUD and overlays, over a 3-minute two-player match:<br>• ≤ **1.0 ms** mean, ≤ **2.0 ms** at p99.<br>• Menus ≤ 1.5 ms.<br>• **0** widgets painted twice in a frame.<br>• No Paint or Layout invalidation of the static layer while values are unchanged.<br>• No growth over a 10-minute soak. | Proj; tools below | Record the hardware (FLOWBOX, 32 GB) and the build configuration. |

## Slate performance: what to measure and how

**Costs the docs confirm:**
- Painting rebuilds the draw-element list every frame, and the cost scales with the number of live widgets (architecture page).
- Bound attributes poll every frame, so prefer events. Avoid logic in Tick or OnPaint (UMG optimization).
- Layer IDs add draw calls, and Slate cannot batch across clipping zones (clipping page). Keep layer increments and clip pushes in OnPaint to a minimum.
- Rich Text costs much more than plain text. `KerningOnly` text shaping can be faster than `FullShaping`, which helps the timer and counters.
- Render-transform animation forces a Layout invalidation every frame. Colour or material animation is cheaper.
- Retainers use a render target and cost more CPU on repaint. Try an Invalidation Box first. `Slate.EnableGlobalInvalidation` caches the whole window.

**My inferences (not checked against the docs):** per-paint string or array allocation and gradient overdraw. Check them with the Insights `MemAlloc` channel and the GPU figure in `stat unit`.

**OnPaint canvas vs widget tree:** caching works per widget. One leaf widget that paints the whole HUD repaints all of it on any change, and every frame if it is volatile. The fix:
- Split it into a cached static layer (frames, names, portraits).
- Put health, gauge and timer in a volatile layer driven by events.
- Re-shape the timer text only when its value changes.

**Commands:**
- `stat unit`, `stat Slate`/`SlateVerbose`, `stat UI`, `stat startfile`/`stopfile`.
- **Insights:** enable the SlateInsights plugin and launch with `-trace=slate` (add the Cpu and Frame channels). Use `trace.bookmark` at round start and check `Trace.Status`. Then open **Slate Frame View** to see invalidation reasons (LPUCRV flags) and update reasons (UTPV flags).
- **Slate Debugger:**
  - `SlateDebugger.Paint.Enable`
  - `SlateDebugger.Paint.LogWarningIfWidgetIsPaintedMoreThanOnce`
  - `SlateDebugger.Invalidate.Enable`
  - `SlateDebugger.Update.Enable`
  - `SlateDebugger.Start` (focus and navigation events, for trap tests)
- **Widget Reflector:** `WidgetReflector` or Ctrl+Shift+W. Use Paint and Invalidation Debugging, Font Atlases, Show Focus and Widget Events.
- `Slate.ShowClipping`; `Slate.EnableDrawEvents` (RenderDoc).

## Sources (accessed 2026-11-09)
- XAG overview: https://learn.microsoft.com/en-us/xbox/accessibility/guidelines
- Individual XAG pages: https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/ followed by:
  - 101 (Text display)
  - 102 (Contrast)
  - 103 (Additional channels)
  - 107 (Input)
  - 112 (UI navigation)
  - 113 (Focus handling)
  - 116 (Time limits)
  - 117 (Visual distractions and motion)
  - 118 (Photosensitivity)
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- WCAG Understanding pages: https://www.w3.org/WAI/WCAG22/Understanding/ followed by contrast-minimum, non-text-contrast, three-flashes-or-below-threshold, focus-appearance, pause-stop-hide (.html)
- Epic pages: https://dev.epicgames.com/documentation/en-us/unreal-engine/ followed by:
  - understanding-the-slate-ui-architecture-in-unreal-engine
  - invalidation-in-slate-and-umg-for-unreal-engine
  - optimization-guidelines-for-umg-in-unreal-engine
  - slate-insights-in-unreal-engine
  - console-slate-debugger-in-unreal-engine
  - using-the-slate-widget-reflector-in-unreal-engine
  - using-the-slate-clipping-system-in-unreal-engine
  - stat-commands-in-unreal-engine
  - trace-in-unreal-engine-5
  - python-api/class/TextShapingMethod (5.8)
- GAG pages: https://gameaccessibilityguidelines.com/ followed by:
  - use-an-easily-readable-default-font-size
  - provide-high-contrast-between-text-and-background
  - ensure-no-essential-information-is-conveyed-by-a-colour-alone
  - avoid-flickering-images-and-repetitive-patterns
  - allow-controls-to-be-remapped-reconfigured
  - avoid-provide-alternatives-to-requiring-buttons-to-be-held-down
  - provide-an-option-to-turn-off-hide-background-movement

**Not verified:** the Epic API reference pages (for example `MakeShapedText` and `SetColorVisionDeficiencyType`) rendered empty. No source gives a millisecond budget for UI.
