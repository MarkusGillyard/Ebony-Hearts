# Interface overhaul: handoff (for Markus)

**Where it stands (2026-11-09).** The shared foundation is done and tested on `dev/ui-ux-identity-overhaul`; no art
direction has been chosen yet. A draft pull request into `release/first-slice` carries it for review. **Nothing is
merged.** PR #1, `release/first-slice` and `main` are unchanged by this work.

## What changed (all three directions share it)

- **Logo:** your new crescent logo replaces the retired title card everywhere (your decision, 2026-11-09).
- **Text and colour:**
  - Everything a player needs to read is at least 26 px tall at 1080p, button letters included.
  - One cool silver-and-violet colour system, matched to the logo and contrast-checked.
  - No state is shown by colour alone.
- **Fight HUD:**
  - A dark band keeps the bars readable over the rose window.
  - The timer sits on a solid plate; won rounds show as crescents.
  - Each fighter's gauge sits under their name and says READY or ACTIVE.
- **Fighter select:**
  - The fighters are no longer covered; names sit in the lower corners.
  - Chips say CHOOSING or LOCKED IN.
  - CPU level and side are on the same screen.
  - Local Versus says "press Confirm", which stays right after remapping.
- **Results:** the winner first, then Rematch (focused), then the stats with each column named. The old screen printed
  the menu over the numbers.
- **Menus:**
  - The focus highlight is actually visible now; it was hidden by a drawing-order bug.
  - Training's pause has sections.
  - Unapplied video changes are marked, and Apply counts them.
  - The move list fits at readable sizes.
- **Training and Lesson:** frame advantage is large and signed; the Lesson shows a 14-step progress strip.
- **Motion:** prompts no longer pulse forever.

## What needs your judgment

1. **The art direction:** A Still Water (recommended), B Fractured Divinity, C Drowned Cathedral, or a mix.
   - Mockups: `Directions.md` and `~/Documents/Ebony Hearts/UIUX_directions_2026-11-09/`.
   - Direction A already runs in the game on a local, unpushed preview branch (`dev/ui-ux-direction-a-preview`): your
     key art as the title screen, every menu in its style, short fades and four new interface sounds.
2. **The key art as the title screen**, if A or C. It arrived as a 1536 × 864 JPEG, slightly soft at 1080p; a larger
   or lossless version would sharpen it.
3. **The fonts:** Cinzel and Alegreya Sans are kept unless you want others.
4. **Merging**, later, and only on your word.

## How to run it

- **Build:** `bin/package.sh <label> Shipping` with `EH_REPO_OVERRIDE` set to this checkout (`Docs/Production.md`).
- **Play:** run `EbonyHearts.sh` from `packages/<label>/Linux`.
- **Same checks as here:**
  - `Tests/Auto/journey.txt` (every screen);
  - `ui_results.txt`, `ui_settings.txt`, `perf_ui.txt` (the interface's cost per screen);
  - `ui_plates.txt` (clean captures);
  - the full battery script from the combat pass.
- **Evidence:** `evidence/uiux-1109/` in the delivery workspace.

## Documents

- `Research.md` (and `research/`): Elden Ring, MKX / XL, accessibility and Unreal UI research.
- `LoreMapping.md`: public-safe.
- `Audit.md`: the findings, by severity.
- `Directions.md`: the three directions.
- `DesignSystem.md`: tokens, type, components.
- `Flows.md`: navigation.
- `Implementation.md`: code changes.
- `Validation.md`: tests and numbers.
