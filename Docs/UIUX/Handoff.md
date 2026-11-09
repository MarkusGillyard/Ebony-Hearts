# Interface overhaul: handoff (for Markus)

**Where it stands (2026-11-09).** Done and tested on `dev/ui-ux-identity-overhaul`, in pull request #2 into
`release/first-slice`, ready for your review. You chose direction **A, Still Water**, and it is applied to every
screen. **Nothing is merged.** PR #1, `release/first-slice` and `main` are unchanged by this work.

You started the build on 2026-11-09; your controller died after about a minute, and you have many issues that are
not itemized yet. An independent review of this pull request and of PR #1's latest round is prepared (its brief is
outside the repository). The issues you name go into the next fix round.

## Direction A: Still Water

- **Title screen:** your key art, with only the prompt and the credit over it.
- **Main menu:** a plain list over the darkened chapel, with the crescent marking the choice.
- **Other menus:** a dark veil between silver rules, with the crescent set into the top rule.
- **Motion:** screens fade in over 0.15 s (they never delay a press).
- **Sounds:** four new interface cues: lock-in, unavailable, apply, warning.

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

1. **Play it** with your controller, on your screen and through your speakers (the new sounds have not been heard by
   anyone yet).
2. **The key art's resolution:** it arrived as a 1536 × 864 JPEG and is slightly soft at 1080p and above; a larger or
   lossless version would sharpen the title.
3. **Merging** PR #2 (and later PR #1), only on your word.

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
