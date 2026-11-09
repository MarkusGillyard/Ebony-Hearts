# Implementation notes

The working log of the overhaul's code changes on `dev/ui-ux-identity-overhaul`. The branch was cut from PR #1's head
`0471443`.

## Architecture (kept)

The interface stays one painted Slate canvas (`SEHCanvas`, `FEHPainter`) driven by the director and the input router.
Measured, it costs a fraction of a millisecond, so there is no performance case for a widget rewrite. The router gives
keyboard and pad identical navigation. Changes are made in place, screen by screen, behind the shared tokens.

## Changes so far

| Area | Paths | What | Migration |
|---|---|---|---|
| Automation | `EHAutomation.cpp`, `EHGameDirector.h`, `EHDirectorUI.cpp`, `Tests/Auto/ui_plates.txt` | `ui_hidden 0/1` hides the interface for clean captures | None (automation only) |
| Measurement | `EHUICanvas.cpp`, `EHAutomation.cpp`, `Tests/Auto/perf_ui.txt` | The time to build the interface's draw list goes into each perf JSON (`ui_paint_mean_ms`, `_p99_ms`, `_max_ms`) | Perf JSON gains three fields |
| Logo | `Content/UI/T_Logo`, `T_LogoSmall`, `Tools/Assets/make_ui_textures.py`, `Tools/Unreal/import_ui.py`, `EHGameDirector.*`, `EHDirectorUI.cpp`, `Tools/Unreal/build_content.py` | The creator's logo replaces the retired title card | `T_TitleCard` removed; nothing else loaded it |
| Tokens and type | `EHUIStyle.h`, `EHDirectorUI.cpp`, `EHGameDirector.cpp` | Semantic colours, type scale, the 20 pt floor, 40 px glyphs, banner and callout colours | None |
| HUD | `EHDirectorUI.cpp` (`PaintHUD`, `EHUIShapes`) | Dark top band, framed bars, timer plate, crescent round markers, tags, gauges under the names, the Lesson panel moved below | None |
| Select | `EHDirectorUI.cpp` (`PaintSelect`) | Nameplates in the corners (the cards and paragraphs over the fighters are gone), state chips, CPU level and side panel; "press Confirm" wording (it said Light, which is wrong after remapping) | None |
| Results | `EHDirectorUI.cpp` (`PaintResults`), `PaintMenu(TopY)`, `Tests/Auto/ui_results.txt` | Winner, then the menu (Rematch focused) right under it, then the stats with each column named (fighter and player); the menu no longer overprints the table | None |
| Focus and layers | `EHDirectorUI.cpp` | The focus band is a 55% violet band with a light-violet edge, and it is now actually visible: content on rounded plates is drawn a layer up (A16) | None |
| Menus | `EHDirectorFlow.cpp` (`Header`), `EHDirectorUI.cpp` (`PaintMenu`) | Section headers in the training pause (Partner, Positions, Practice aids, More). Navigation skips headers, so every item is the same number of presses away | None |

## Risks and checks

- **Scripts count presses.** Headers are skipped, so counts are unchanged, and the journey script passes.
- **Draw layers.** Slate may batch rounded and plain boxes on the same layer in either order, so anything drawn on a
  rounded plate (bands, frames, hairlines, glyph symbols) goes one layer up (`P.NextLayer()` after the plate). Text
  already sits one layer above its shapes; overlays painted before a modal need two steps to stay under it.
- **Static colour constants.** The old palette names refer to the tokens by reference, so the order of static
  initialisation cannot matter.
