# The Drowned Chapel: interior

The Drowned Chapel is the game's sanctuary and hub. This document covers the playable interior on the
`proto/chapel-interior` branch. Its design (the spaces, their purposes and the decisions awaiting the creator) is a
proposal until the creator approves it. Story details are kept out of this public document.

Everything built here is a placeholder. The pieces are generated from code with the Chapel's own geometry helpers and
materials, so they read as the same building; the creator authors the final architecture and art.

## Spaces

Coordinates are Unreal centimetres. The nave runs from the entrance (+Y) to the rose window (−Y), and X runs across
it.

| Space | Purpose | Level | Stage 1 |
|---|---|---|---|
| Threshold Hall | Arrival and departure; the Threshold Door leads out to wherever the Chapel stands. Low ceiling (4.6 m) before the 16 m nave. | 0 | Built: walls, floor with a seep channel, ceiling beams, the closed door with light through its seam |
| Loft | An overlook of the whole nave toward the rose window, up a stone stair in the hall | +4.9 m | Built: stair (27 steps), loft room under a barrel vault, balcony on two columns |
| Entrance strip and nave | The existing Chapel: the wolves' ground, wading water, the fight space | 0 / −0.35 m water | Unchanged, except the real west wall and its great arch |
| Sanctuary | Prayer at the altar | +0.45 m | Unchanged (prayer is stage 2) |
| Forge (north transept) | Smithing King Dwar: buying items and upgrading weapons | +0.45 m, dry | Built: opened off the north aisle by two arches, steps, barrel vault, end window, warm light (furnishing is stage 2) |
| Hall of the Six (south transept) | A memorial of past champions, in traces only | +0.45 m, dry | Built: the mirror of the forge's room (alcoves and mural are stage 2) |
| The way down and the undercroft | The way to the Hearted Dungeons, through a flooded crypt under the sanctuary | −3 m, water 0.6 m | Built: doorway in the north aisle's east end (with a window above), 17 steps down, crypt with a central arcade and two vaults, the gate (shut) and a sealed door |

## What changed in the map

`Tools/Unreal/build_chapel_interior.py` makes these changes:
- It removes the grey west-wall placeholder.
- It removes four aisle wall bays (where the transepts open) and the north aisle's east end bay (the way down),
  with their glass, candles and grime decals.
- It places the new pieces with collision from their render geometry and two-sided shadows.
- It adds eleven lights:
  - warm in the hall, transepts and by the great arch;
  - the forge's (the only new shadowed light besides the door seam's);
  - cold in the way down and the crypt;
  - a faint red at the gate and a faint warmth at the sealed door.

Re-running it replaces its own actors (labels `IX_*`, `IXL_*`). The bays it replaced are recorded in the source folder
(`bays.json`), so a re-run can place the arches without the original walls.

## Water

The Chapel's water is now a set of sheets, each over its own area: the nave's basin at the tuned surface (3 cm) and
the crypt's at its mesh's height (−2.4 m). The player's wading depth, the Ice Wall's freezing and the ripples all
read the sheet under them. The Threshold Hall, the loft, the transepts and the stair are dry.

## Navigation

The wolves walk everywhere the player can. The navigation bounds now cover the whole interior, and the new rooms'
floors, every stair step and the wall stubs beside each opening have navigation-only stand-ins
(`Tools/Unreal/adapt_chapel_fp.py`, `IX_NAV`). A friendly wolf follows the player into the forge, up to the loft and
down into the crypt.

## Rebuilding

```bash
blender -b --factory-startup -P Tools/Blender/chapel/chapel_interior.py -- <workspace>/sourceart/chapel_interior
bin/editor_py.sh Tools/Unreal/build_chapel_interior.py
EH_FP_STAGE=nav bin/editor_py.sh Tools/Unreal/adapt_chapel_fp.py
```

(`CHAPEL_SLICE_ROOT` points the Blender script at the slice root, for the kit's configuration.)

## Tests

`Tests/Auto/fp_interior.txt` (development build) walks every new space with real movement:
- the hall, where the door holds;
- the stair up to the loft and out onto the balcony;
- both transepts' steps;
- the way down into the crypt's water, and back up;
- the gate and the sealed door, which hold;
- a friendly wolf following the player into the forge, the loft and the crypt.

It checks the water depth in each place.

## Open

- **Stage 2** (function and furnishing):
  - an Interact input and prompts;
  - prayer at the altar with the alignment meter;
  - the forge's furnishings and a placeholder for Dwar;
  - the Hall of the Six's alcoves and mural slot;
  - the present occupants' camp;
  - the statues and the altar relief.
- **Stage 3:** atmosphere (motes, heat shimmer, sound) and the light following the world's time, once a clock exists.
- **Creator decisions:** the floor plan and every item listed for approval in the private design document.
