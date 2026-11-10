# Validation of the interface work

**Independent review update (2026-11-10).** The results below belong to the earlier implementer package `0126cac`.
The current review found clipping at enlarged interface scale and a disconnected selection owner. Repairs are being
qualified on a new candidate. The creator's first identified playtest priority is animation transitions and throws;
no completed human acceptance is recorded. See [`Docs/Review.md`](../Review.md) for fresh evidence and disposition.

Machine: FLOWBOX (AMD Ryzen 7 5700G, 32 GB, NVIDIA GeForce RTX 2060 6 GB, driver 595.99.02), Linux X11.
Packaged Shipping builds from `dev/ui-ux-identity-overhaul`. Evidence is in the delivery workspace under
`evidence/uiux-1109/`. Everything here is the implementer's own testing, plus one independent code review (its
findings are fixed; see `Implementation.md`). Nobody has played these builds with a physical controller yet.

## Status (2026-11-09, final build `0126cac`, direction A)

Done: the shared foundation and direction A (Still Water) on every screen, chosen by the creator.

## Final build `0126cac`

| Check | Result | Evidence |
|---|---|---|
| Full battery (28 runs: smoke, controls self-tests, remap and persistence, Controls UI, journey, full Lesson, keyboard, simulated Xbox and DualShock 4 pads incl. disconnect/reconnect and remap, 12-match matrix, review scripts, footage, frame times) | **PASS**: 28/28, no `FAIL` or `WARN`; 20 starts at 2.28 s on average (at most 2.40); matrix memory 1 513 MiB (peak 1 533); no frame over 33 ms (max 17.6 ms); uncapped fight median 7.6 ms | `battery-0126cac/`, `battery-0126cac.log` |
| Review checks: Video Back, Lesson layout, 140% interface scale, select labels | **PASS** (on `pkg-102`, same code but for the Lesson callout position) | `review-*/` |
| Before and after, every representative screen (title, main menu, select, CPU options, HUD, pause, move list, training pause and overlays, Lesson, Local Versus, video settings, controls, credits, quit, results) | Captured from the battery runs of `84acb66` and `0126cac` | `~/Documents/Ebony Hearts/UIUX_directions_2026-11-09/before_after_all_screens_{1,2}.jpg` |
| Footage | A simulated DualShock 4 driving title → Versus CPU → a fight with every action → out through the menus (19 s); the keyboard journey through every screen (60 s); phone copies (faststart H.264 Main, 960 × 540) | `footage/pad3/`, `footage/journey2/`, `footage/phone_*.mp4` |

### Interface cost, final (`Tests/Auto/perf_ui.txt`, two runs; mean / p99 ms of CPU to build the draw list)

| Screen | Before (`0471443` + timing) | Final (`0126cac`) |
|---|---|---|
| Title (now the key art) | 0.013 / 0.022 | 0.012 / 0.026 |
| Main menu, navigating | 0.047 / 0.29 | 0.049 / 0.22 |
| Fighter select | 0.048 / 0.076 | 0.045 / 0.083 |
| Settings (controls, video) | 0.040–0.048 / 0.074–0.080 | 0.047–0.056 / 0.081–0.091 |
| Move list | 0.126 / 0.19 | 0.221 / 0.37 |
| Fight | 0.030 / 0.085 | 0.039 / 0.077 |
| Training with overlays | 0.095 / 0.27 | 0.097 / 0.20 |

Frame times are unchanged in every scenario (median 16.67 ms, p99 ≤ 16.78 ms at 60 Hz V-Sync, 1080p).

## Earlier builds

| Check | Result | Evidence |
|---|---|---|
| Full battery on `92cc208`, the shared branch's head (the same 28 runs) | **PASS**: 28/28, no `FAIL` or `WARN`; 20 starts at 2.24 s on average (at most 2.43); matrix memory 1 515 MiB (peak 1 533); no frame over 33 ms (max 18.6 ms); uncapped fight median 7.6 ms | `battery-92cc208/`, `battery-92cc208.log` |
| Full battery on `f866dc9` (28 runs: smoke, controls self-tests, remap and persistence, Controls UI, journey, full Lesson, keyboard, simulated Xbox and DualShock 4 pads incl. disconnect/reconnect and remap, 12-match matrix, review scripts, footage, frame times) | **PASS**: 28/28, no `FAIL` or `WARN`; 20 starts at 2.25 s on average (at most 2.40); matrix memory 1 505 MiB (peak 1 523); every V-Sync run without a frame over 33 ms (max 17.4 ms); uncapped fight median 8.0 ms (7.7–7.9 on the last three candidates, within their spread; the interface itself measures 0.04 ms) | `battery-f866dc9/`, `battery-f866dc9.log` |
| Journey on each later build (every screen, keyboard) | **PASS**, no `FAIL` | `journey-tokens*`, `journey-focus*`, `journey-layers`, `check93-journey` |
| Results screens (CPU and local versus) | Decision first, columns named, no overprint | `results1/` |
| Video page: unapplied marking, Back discards | **PASS** after a fix. The first run's own screenshots showed a bug, which an independent code review caught: under a launch-flag display (here `-windowed`), Back reloaded the saved file and showed its values (Borderless) instead of the screen's (Windowed). Back now restores the values the page opened with | `check93-ui_settings/` (the bug), `review-ui_settings/` (fixed) |
| Training frame data and the Lesson's progress strip; the full Lesson | The full Lesson (`lesson_full.txt`) completes; journey **PASS** | `check94-journey/`, `check94-lesson_full/` |
| 2560 × 1440 (16:9) | Journey **PASS**; the canvas scales uniformly | `journey-2560/` |
| Colour vision (protanopia, deuteranopia, tritanopia; Machado 2009 at full severity, applied to screenshots) | No state is lost: the focus band shifts toward blue or grey but stays distinct from the panel; player colours shift, while the P1, CPU and state words, the filled-versus-outlined chips and the dot on unapplied values carry the meaning | `colour-vision/cvd_sheet.jpg` |
| 3440 × 1440 (21:9) | Layouts hold. The stage is pillarboxed to 16:9 as before; the interface stays in that safe area, and its bands span the width | `journey-3440/` |

### Interface cost at `92cc208` (mean / p99 ms)

| Screen | Before (`0471443` + timing) | After (`92cc208`, two runs) |
|---|---|---|
| Title | 0.013 / 0.022 | 0.013 / 0.024 |
| Main menu, navigating | 0.047 / 0.29 | 0.047 / 0.23 |
| Fighter select | 0.048 / 0.076 | 0.045 / 0.080 |
| Settings (controls, video) | 0.040–0.048 / 0.074–0.080 | 0.041–0.049 / 0.080–0.084 |
| Move list | 0.126 / 0.19 | 0.222 / 0.32 (wraps long notes each frame) |
| Fight | 0.030 / 0.085 | 0.038 / 0.082 |
| Training with overlays | 0.095 / 0.27 | 0.098 / 0.22 |

Frame times are unchanged in every scenario (median 16.67 ms, p99 ≤ 16.80 ms at 60 Hz V-Sync, 1080p). The budget is
1.0 ms mean and 2.0 ms p99.

## Accessibility checks so far

- **Text size:** essential text is 20 pt or larger (26 px or more of body height at 1080p), measured with the bundled
  fonts. Only the development-build graybox warning is smaller.
- **Contrast:** the token table in `DesignSystem.md` gives every ratio against the panel and the lightest surface. The
  damage-lag colour was brightened to clear 3:1 against the empty track.
- **Not colour alone:** players, choice states, rounds, gauges, low health and unapplied values each have a word, a
  shape or a length as well.
- **Focus:** one visible focus per menu (a 55% violet band with a light-violet edge, plus bold primary text).
- **Motion:** nothing blinks on its own for more than 5 s; no new flashing.

## Not verified

- **The creator's playtest.** On 2026-11-09 the creator started the `0126cac` build; after about a minute their
  controller died. They report many issues, not yet itemized. Until they are, this work has not passed a human
  playtest.
- Hands-on play with a physical controller (simulated Xbox and DualShock 4 pads pass).
- Listening to the four new sounds (generated at the house loudness and checked by measurement; this machine plays
  audio only through the TV or soundbar, which were not used).
- At interface scales above 100% the HUD's outer ends and the bottom prompt row move off screen. This was already so
  before this work (the scale enlarges everything around the centre); menus now fit.
