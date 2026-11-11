# UI audit of the current slice (baseline)

**Baseline:** the PR #1 head `0471443`, whose packaged build is candidate `84acb66` (Shipping, Linux; no code change
since). The machine is FLOWBOX: AMD Ryzen 7 5700G, 32 GB RAM, NVIDIA GeForce RTX 2060 6 GB (driver 595.99.02),
Linux X11. It was checked three ways:
- reading the source (`Source/EbonyHearts/Game/EHDirectorUI.cpp`, `EHDirectorFlow.cpp`, `EHUICanvas.*`,
  `EHGameDirector.h`);
- the packaged journey and controls scripts, run in the candidate's battery;
- frame times from the same battery.

The "before" screenshots are in the delivery workspace, outside this repository:
- `evidence/rc-84acb66/battery/journey/` (`j01_title` to `j16_quit_confirm`);
- `.../controls-ui/` (`ui01` to `ui18`);
- `.../lesson/`.

## How the UI is built

- One full-screen Slate leaf widget (`SEHCanvas`) paints every screen through `FEHPainter` in a 1920 × 1080 virtual
  space. The space is centred and scaled to the window, with the interface-scale setting applied on top.
- Menus are lists of `FEHMenuItem` (label, value, change, activate, hint) built per screen in `BuildMenu`. They are
  navigated through `FEHInputRouter`, not Slate focus, so the keyboard and every gamepad behave identically. The
  pausing device, or the menu's owner, gets the prompts drawn in its own buttons.
- Colours come from a small palette namespace (`EHUIPalette`), but most sizes, positions and many colours are literal
  values in each painter. The code uses 31 distinct font sizes.
- Fonts: Cinzel (display) and Alegreya Sans (body), both SIL OFL, in `Content/UI/Fonts`.
- Title art: `T_TitleCard` (the retired logo, SHA-256 `2856a352…`), drawn on the title and the main menu.
- UI sounds: move, confirm, back, open, close (`Content/Audio/UI`).

## Screen map

```
Title ──any button──▶ Main
Main ─┬─ Versus CPU ─▶ Select (fighter ▶ opponent ▶ CPU level + side) ─▶ Match ─▶ Results ─┬─ Rematch ─▶ Match
      ├─ Local Versus ─▶ Select (each player joins, chooses, locks; "fight") ─▶ Match ─┐    ├─ Change Fighters ─▶ Select
      ├─ Training ─▶ Select (fighter ▶ partner) ─▶ Match (training overlays) ──────────┤    └─ Main Menu ─▶ Main
      ├─ Lesson ─▶ Select (fighter ▶ partner) ─▶ Match (14 lesson steps) ──────────────┘
      ├─ Move List (both fighters, left/right switches)
      ├─ Settings ─┬─ Controls ─▶ prompt style; 4 layouts (pad P1/P2, keyboard A/B) ─▶ action ▶ capture ▶ conflict/swap
      │            ├─ Video (mode, resolution, quality, render scale, frame limit, V-Sync, Apply ▶ Display confirm 12 s)
      │            ├─ Audio (master, music, effects, ambience)
      │            └─ Accessibility (interface scale, reduce shake, reduce flashes, input hints, default CPU level)
      ├─ Credits
      └─ Quit ─▶ Quit confirm
Match ── Pause (owner device) ─▶ Resume, [Training: dummy, CPU level, start position, reset positions, hitboxes,
         frame data, input history, gauge] [Lesson: restart, skip step] [Versus: restart], Move List, Settings,
         Change Fighters, Main Menu
Overlays: toast notices, controller-disconnected pause, banners (round, KO), callouts, combo counter.
Errors: data error screen ("could not start", confirm or Escape quits); missing-asset graybox warning (development).
```

**Presses from the title to a fight with default choices:**
- Versus CPU: 5.
- Training: 6 (the title, two moves down, then confirm the mode, fighter and partner). Lesson: 6 (the title, three
  moves down, then confirm the mode and fighter).
- Local Versus: 2 to reach select, then each player joins, chooses, locks and one confirms the fight.
- Rematch: 1, since it is the results screen's first item.
- Quit: 2 from the main menu.

## Usability findings

P0 broken, P1 major friction, P2 inconsistency, P3 polish. No P0 was found: the 28-run battery and the soak pass.

| # | Sev. | Finding | Reproduce | Evidence | Status |
|---|---|---|---|---|---|
| A1 | P1 | **Essential text under the readability floor.** At 1080p these render below the 26 px body height that XAG 101 sets for TV distance: the prompt row (Select / Back) 24 px, the player tags P1 / CPU / PARTNER 23 px, gauge labels (SPIRIT, FLAME READY) 23 px, button letters inside glyphs about 19 px, move-list headers and notes 23–24 px, the input-history labels 21 px | Any menu, any match, the move list | `Fonts.Sized` values (16–19 pt) measured with the bundled fonts: below 20 pt renders under 26 px | Fixed (`dcb67a4`, `4c9cc21`) |
| A2 | P1 | **The HUD fights the stage.** The timer and the inner ends of both health bars sit over the lit rose window; the timer's plate is translucent, so its contrast changes with the window behind it | Start any versus match; compare j04 / j05 | `j04_match_intro`, `j05_pause` | Fixed (`dcb67a4`) |
| A3 | P1 | **Fighter cards cover the fighters.** The two select cards sit across the fighters' legs and bodies, and the explanatory paragraph is the largest block on screen | Versus CPU ▶ select | `j03_select`, `j10a_versus_select` | Fixed (`dcb67a4`) |
| A4 | P1 | **The logo is retired.** The title and main menu show the old title card; the creator replaced it with the crescent logo on 2026-11-09 | Launch | `j01_title`, `j02_main` | Fixed (`3aa3601`) |
| A5 | P2 | **One generic panel for every purpose.** Main menu, pause, settings, quit and results all use the same grey rounded panel and violet bar; there is no hierarchy between a mode choice, a setting and a destructive confirmation | Any menu | `j02`, `j05`, `j11`, `j16` | Fixed (direction A: veils, rules, the crescent) |
| A6 | P2 | **Mixed palette.** Warm bone, gold and brown edges, from before the logo, sit beside violet focus. Gold means P1, a selected value, the combo counter and Wren's gauge all at once | Any screen | `EHUIPalette` | Fixed (`dcb67a4`) |
| A7 | P2 | **Local Versus join wording disagrees.** The headline says each player presses Confirm to join; the per-player line says "press Light to join"; Light is Confirm by default, but a remapped player sees two names | Local Versus with one remapped layout | `PaintSelect` | Fixed (`dcb67a4`) |
| A8 | P2 | **Gauges are far from their owners.** The Spirit and Flame gauges sit at the bottom corners, about 950 px from the health bars, with 14 px tall fills; "READY" is shown by colour plus text | Any versus match | `j04` | Fixed (`dcb67a4`) |
| A9 | P2 | **The training pause is one long list** of 14 items mixing dummy settings, overlays and navigation | Training ▶ pause | `j07a_training_pause` | Fixed (`dcb67a4`) |
| A10 | P2 | **Move-list density.** 15 rows of 21–22 pt text plus 19 pt notes in one panel; the startup and damage columns are close together | Main ▶ Move List | `j06_movelist` | Fixed (`4c9cc21`) |
| A11 | P2 | **Pending vs saved values look the same** on the Video page until Apply; only the hint says so | Settings ▶ Video, change a value | `j13_video` | Fixed (`4c9cc21`) |
| A12 | P3 | **No transitions.** Screens cut instantly (only the title fades in), so moving between menus has no sense of place | Navigate any menus | — | Fixed (direction A: 0.15 s fades) |
| A13 | P3 | **The title prompt pulses forever** (sine on alpha) and is small against the art | Launch, wait | `j01_title` | Fixed (`4c9cc21`) |
| A15 | P1 | **The results menu overprints the stats table.** The menu is centred on the screen and the table sits at y = 290–540, so "Rematch" is drawn across the rows of numbers | Finish any match | `rc-84acb66/battery/matrix/m01_results.png` | Fixed (`f866dc9`) |
| A16 | P2 | **The focus band was mostly hidden.** The menu panel (a rounded box) and the selection band (a plain box) shared a draw layer, and Slate may batch them in either order: the 90% panel was drawn over the band, leaving a faint stripe | Any menu | `j02_main` (the band barely shows) | Fixed (`f866dc9`) |
| A14 | P3 | **Results lead with stats, not the decision.** The stats table sits above the Rematch / Change Fighters / Main Menu menu | Finish a match | `PaintResults` | Fixed (`f866dc9`) |

## Preserve, improve, replace, remove

| Component | Decision | Why |
|---|---|---|
| One canvas, 1920 × 1080 virtual space, interface scale | **Preserve** | Simple, fast and already resolution-safe; no need for a widget framework for this many screens |
| Router-driven navigation, per-device ownership, prompts in each device's buttons | **Preserve** | Cross-device parity is tested (controls self-tests, simulated pads) and is correct |
| Menu data model (`FEHMenuItem`), settings, bindings capture and conflict flow, display confirm-or-revert | **Preserve** | Functionally complete; restyle only |
| Palette namespace and literal sizes and colours | **Replace** with semantic design tokens (text, focus, panel, health, gauge, warning) and a type scale | A6, A1; one place to change the look |
| Generic panel | **Replace** with a small set of primitives: heading, menu row, value row, confirmation, prompt bar, nameplate, bar | A5 |
| Title and main menu art | **Replace** with the new logo and key art | A4 |
| Select layout | **Improve**: fighters unobstructed, short lines, explicit states | A3, A7 |
| HUD | **Improve**: a solid backing for the timer and bars, gauges next to health, larger labels | A1, A2, A8 |
| Training pause | **Improve**: grouped sections | A9 |
| Move list | **Improve**: larger text, clearer columns | A10 |
| Results | **Improve**: decision first, stats second | A14 |
| Banner pre-warm on the title (rasterising large glyphs while nothing is at stake) | **Preserve** | Prevents a known hitch at round start |
| Development graybox warning | **Preserve** (development only) | Truthful failure state |
| Fonts (Cinzel, Alegreya Sans) | **Keep for now**, decide with the art direction | Licensed (OFL), readable; Cinzel's capitals echo the logo's Roman forms |

## Baseline performance (candidate `84acb66`, battery)

| Scenario | Result |
|---|---|
| Menu, 1080p, V-Sync | median 16.67 ms, p99 16.77 ms, max 17.44 ms |
| Menu, 1080p, uncapped | median 7.78 ms, p99 9.29 ms |
| Fight, 1080p, uncapped | median 7.85 ms, p99 9.65 ms |
| Fight, 3440 × 1440, V-Sync | median 16.67 ms, p99 16.78 ms, max 16.88 ms |
| Starts | 2.26 s average to the game (at most 2.44 s, 20 starts) |
| Memory | 1 480–1 487 MiB over a 57-minute soak |

Slate's own draw time was not recorded by the battery. Phase 2 adds a `stat slate` / Insights capture of the
baseline before anything changes, as `research/access_ue.md` describes.
