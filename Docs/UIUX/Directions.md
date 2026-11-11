# Art directions for the interface

**Decision (the creator, 2026-11-09): A, Still Water.** The key art becomes the title screen; the fonts stay. B and
C below are kept as the record of what was considered.

Three treatments of the same screens: title, main menu, fighter select and the in-fight HUD. Each is drawn at
1920 × 1080 on clean plates of the real stage and fighters. The plates come from the packaged game with the interface
hidden (`Tests/Auto/ui_plates.txt`, the automation command `ui_hidden`). Each treatment uses the creator's new logo
and key art and the game's own fonts.

The mockups are in the delivery workspace, outside this repository, at `evidence/uiux-1109/mockups/`: `A1`–`A4`,
`B1`–`B4`, `C1`–`C4` and `directions_sheet.jpg`. The plates are in `evidence/uiux-1109/plates/`.

All three share the same information architecture, layout and measured rules, so the decision is about look, not
usability:

- **Text and contrast:**
  - essential text is at least 26 px at 1080p;
  - text contrast is at least 4.5:1, and bars and the focus marker at least 3:1 (`research/access_ue.md`);
  - violet `#A15CE8` is used only for shapes (3.9:1 on panels). Text on focus stays Moonlight, and violet text uses
    `#C2A2F2` (7.2:1).
- **States** carry a label and a shape, not only a colour:
  - P1 and CPU tags;
  - "LOCKED IN" (filled) against "CHOOSING" (outlined);
  - won rounds as filled crescents, rounds still to win as faint ones.
- **The HUD** stays in a top band:
  - health with a lagging damage segment;
  - names and tags under the bars;
  - each fighter's gauge directly under its owner's health bar, not in the bottom corners;
  - nothing in the centre;
  - a dark band behind it so the rose window cannot reduce its contrast.
- **Fighter select** keeps the fighters visible. Short nameplates sit in the lower corners, and CPU level and side are
  on the same screen.
- **Character colours** stay on their own side: gold for Wren's Spirit, crimson for Ashka's Flame.

## A. Still Water (recommended)

Maximum restraint. The full key art is the title screen; its wordmark is part of the painting. The menus float over the
live, darkened chapel as a plain text list. Focus is a soft violet band with the crescent as its marker, separated by
silver hairlines. The HUD is clean silver on near-black.

- **For:**
  - It reads best in motion and at a distance.
  - It costs almost nothing to draw (no textures besides the logo and the key art).
  - It keeps the stage, The Drowned Chapel, visible on every screen.
  - It follows the research most closely: Elden Ring's stillness, MKX's clean edges.
  - Easiest to extend to new screens.
- **Against:** the plainest of the three. Its character comes from the logo, the key art, the crescent and the
  restraint, not from ornament.

## B. Fractured Divinity

More ornament from the logo itself.
- **Title:** the logo glows violet over the live chapel.
- **Menus:** centred in cut-corner tablets with fine fracture lines.
- **HUD:** slanted, bevelled silver bars, with a glowing crescent around the timer.

- **For:** the most distinctive at a glance, and the closest to the logo's own cracked silver.
- **Against:**
  - The ornament competes with text and with the fight.
  - The fracture detail turns into noise at small sizes.
  - Cut-corner panels need more care on every new screen.
  - Glows must be watched for contrast and for flashing.

## C. Drowned Cathedral

Architecture as the frame. The key art is the title, inside a pointed-arch border. The menu sits in a tall arch over
the chapel. At select, each fighter stands under an arch outline in their colour. The timer is housed in an arch, and
the health bars end in pointed caps.

- **For:** cinematic, and it ties the interface to the stage's gothic architecture.
- **Against:**
  - Arches take space: the menu column is narrow, and the select arches cross the fighters.
  - It is the hardest to keep consistent on dense screens (settings, move list).

## What the decision covers

1. **The direction:** A, B or C, or a named mix (for example, A with B's title).
2. **The title screen:**
   - the full key art with its painted wordmark (A and C), or
   - the standalone logo over the live chapel (B).

   The key art arrived as a 1536 × 864 JPEG, so at 1920 × 1080 it is upscaled 1.25× and slightly soft; a larger or
   lossless version would sharpen it. Using the key art behind menus would need a version without the wordmark: a crop
   still shows it, and the logo would appear twice.
3. **The fonts:** keep Cinzel for display and Alegreya Sans for body (recommended; both are licensed and readable, and
   Cinzel's Roman capitals sit well with the logo's lettering), or ask for alternatives.

Already decided by the creator on 2026-11-09: the old title card is retired, and the new crescent logo replaces it
everywhere.
