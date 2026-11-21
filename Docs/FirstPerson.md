# First-person prototype: Walk the Chapel

This branch (`proto/first-person`) turns the Drowned Chapel into a first-person space: the player walks, sprints,
jumps and crouches through the flooded nave. The game starts straight in the Chapel, with no title screen or menus
before play. The 2.5D slice stays intact in `main`'s history. Its fighting code is still compiled here but is not
reachable from the first-person flow.

Every model, animation and blockout in this build is a placeholder. The game says so in a small line at the bottom
left of the screen.

## Running it

- **Editor or development build:** open the project as usual; `DrownedChapel` is the start map and `EHGameMode`
  spawns the first-person player.
- **Package:** the same Linux Shipping pipeline as the slice (`Docs/Production.md`, steps 9 to 11).
- **Data:** movement tuning is read at start-up from `Content/Data/firstperson.json`. A missing file or an
  out-of-range value stops the game on the error screen, naming the field.

## Default controls

Every gameplay action can be remapped in Settings > Controls. Menu controls are fixed, as in the slice
(`Docs/Controls.md`).

| Action | Keyboard and mouse | Controller |
|---|---|---|
| Move | W A S D (and the arrow keys) | Left stick (always) |
| Look | Mouse (always) | Right stick (always) |
| Jump | Space | A / Cross |
| Crouch | Left Ctrl (and C); hold | Right stick press; toggles |
| Sprint | Left Shift; hold | Left stick press; toggles until you stop moving forward |
| Pause | Escape (fixed) | Menu / Options (fixed) |

- **Keyboard holds and toggles.** Settings > Controls > Keyboard can make sprint and crouch toggle.
- **Look settings.** Mouse sensitivity is in degrees per mouse count (default 0.08). Controller look speed scales the
  stick's full-tilt turn rate (default 100%). Invert look applies to both. Field of view (Video, horizontal degrees,
  default 90) applies immediately.
- **Mouse buttons** can be bound to actions on the keyboard-and-mouse layout. Escape, F10 (reserved for the developer
  panel) and the console key cannot.
- **Sprint rules.** Crouching wins over sprinting. A jump from a crouch stands up first. A jump pressed up to 0.15 s
  before landing still counts.

## Settings file

First person keeps its own file, `Saved/EbonyHearts/FirstPersonSettings.json` (format version 6), so the 2.5D
slice's `Settings.json` is never rewritten. On the first launch, when only the slice's file exists, its display,
audio, accessibility and button-prompt values carry over and a notice says so. The fighting layouts load as before but
are not used in first person. The first-person layouts start at the defaults above; no fighting action maps onto a
first-person action. Version 6 adds the two first-person layouts (`fpKeyboard`, `fpController`) and the look,
field-of-view, hold/toggle and Stamina-meter settings.

## Tuning (`Content/Data/firstperson.json`)

The values in the first table are the proposed starting points from the prototype plan. The engineering values in the
second table are starting points too; the creator's playtest decides all of them.

| Value | Starting point |
|---|---|
| Walk speed | 400 cm/s |
| Sprint speed | 700 cm/s |
| Sprint Stamina cost | a full bar (100) in 6 s of running |

| Value | Starting point | Why |
|---|---|---|
| Crouch speed | 200 cm/s | half walking pace |
| Acceleration and braking | 2400 cm/s² each, ground friction 8 | reaches walking speed in about 0.17 s; stops about as quickly |
| Air control | 0.35 | some steering in the air without strafing freely |
| Jump | 420 cm/s up, gravity × 1 | about 0.9 m high |
| Capsule | radius 34 cm; 180 cm standing, 116 cm crouched | adult proportions |
| Eye height | 165 cm standing, 100 cm crouched; 0.12 s blend | no snap when crouching |
| Step height, walkable slope | 45 cm, 46° | the altar steps and fallen stones are walkable |
| Stamina recovery | 25 per second, starting 0.8 s after the last drain | empty to full in 4 s |
| Exhaustion | sprinting the bar empty stops the sprint until Stamina is back to 20 | no stutter at zero |
| Stick | radial dead zone 0.18; full tilt turns 200°/s across, 140°/s up and down; response curve exponent 2 | |
| Pitch limit | ±85° | |

The player-facing Stamina readout is a thin line below the centre of the view. By default it shows only while
Stamina changes (Settings > Accessibility > Stamina meter: Off, While it changes, Always). It is a placeholder for
the playtest; the creator decides how Stamina is shown.

## The Chapel in first person

The slice built the Chapel for a camera looking down the nave from one side. Walking it from eye height
(`Tests/Auto/fp_audit.txt`, 22 views) showed:

- **Holds up:** the nave, both aisles, the piers and arcades, the vaults, the apse with the rose window, the altar
  and its steps, the pews, the candle stands and the aisles' east walls. The basin's water is about 40 cm deep at
  its centre, so the player wades knee-deep. The stone floor on the entrance strip is under 3 cm of water.
- **Missing:** the whole west (entrance) end. The side-on camera never looked that way, so the nave and aisles
  opened onto a void. `PH_Blockout_WestWall`, a grey 1 m grid placeholder, now closes it from the floor to above the
  nave vault.
- **Light leak:** the vault webs and upper walls are single-sided. The low moon shone through them onto the west end
  (rib shadows across the new wall). The shell pieces now cast two-sided shadows, so moonlight enters only through
  the glass. The rose window's light pattern on the nave floor is unchanged.
- **Collision:** the slice imported every piece without collision. Floors, walls, piers, the altar and its steps,
  pews, rubble and candle stands now block with their render geometry (complex as simple). Vaults, upper walls, glass,
  chains, censers, candles, decals and the water stay without collision: they are out of reach or too small to snag on.

`Tools/Unreal/adapt_chapel_fp.py` makes all of these changes in the editor and can be re-run after
`build_level.py`. The audit's views are listed in `fp_audit.txt` (spawn, nave, aisles, apse corners, altar, basin).

Space: the nave between the piers is about 15 m wide and 24 m long, with aisles about 3.6 m wide on both sides and
arcade openings between every pair of piers. That leaves open ground in the nave and routes around any obstacle
placed across it.

## Presentation

- **No body in view.** The player sees no body. A hidden full-body placeholder (the slice's Wren test model with its
  fighting-stance idle and walk) uses Unreal's first-person *world space representation*. It is never drawn to the
  player's own camera but casts shadows: standing in the rose window's moonlight, the player sees their own shadow
  on the floor.
- **Limbs.** None yet. No action in this milestone calls for arms.
- **Reflections.** The project renders reflections with screen-space reflections (no Lumen, no virtual shadow
  maps). Screen-space reflections can only reflect what is on screen, so the hidden body never appears in the water.
  A bounded experiment measured the alternative:

| Configuration (1920 × 1080, quality High, VSync off, development build, one view over the basin) | GPU median | GPU p99 |
|---|---|---|
| Project renderer | 6.27 ms | 6.59 ms |
| Global clip plane enabled (needed for planar reflections), no planar reflection | 6.31 ms | 6.74 ms |
| Planar reflection on the water, 50% resolution | 8.29 ms | 8.59 ms |
| Planar reflection on the water, 100% resolution | 11.01 ms | 11.53 ms |

  A planar reflection mirrors the rose window and the candles in the water, but it did not show the hidden body.
  A copy of the body visible only in scene captures did not show either. The dark, rough water and wet floor
  reflect only faintly, which makes the result harder to judge. Credible self-reflections would need a planar
  water material and a body representation that the capture includes: more work, and about 2 ms of GPU time at half
  resolution. The renderer settings are unchanged. The development commands `fp_planar` and `fp_body_visible`
  reproduce the experiment.

## Automation

The slice's evaluation runner (`-EHAuto=<script> -EHEvidence=<dir>`) drives first person through the same device
path as a player. New commands:

| Command | Builds | What it does |
|---|---|---|
| `look <dx> <dy>` | all | mouse movement in counts through the input router |
| `fp_state [label]` | all | logs position, view, speed, posture, Stamina, water depth and eye height |
| `fp_expect <field> <lt\|gt\|eq\|near> <value> [tolerance]` | all | checks stamina, speed, vz, x, y, z, yaw, pitch, crouched, sprinting, exhausted, falling, water, eye, paused, screen, fov, moved |
| `fp_mark` | all | remembers the feet position for `fp_expect moved` |
| `fp_reset` | all | what the pause menu's Return to the start does |
| `fp_focus_lost` | all | what losing window focus does (pause, drop held input) |
| `fp_teleport`, `fp_view`, `fp_box`, `fp_clear_boxes`, `fp_body_visible`, `fp_planar` | development only | test positions, a blocking test box, the body and reflection experiments |

Scripts: `fp_movement.txt` (movement, Stamina, jump, crouch under a low ceiling, controller sticks and dead zone,
mouse look, water and steps, pause, focus loss, reset), `fp_controls_a.txt` and `fp_controls_b.txt` (remapping, then
persistence across a relaunch), `fp_audit.txt`, `fp_presentation.txt`, `fp_reflection_perf.txt`, `fp_perf.txt` and
`fp_perf_cold.txt` (a traversal route captured warm, after one pass, and cold, from start-up; inputs only, so they run
in Shipping) and `fp_xinput.txt` with `fp_xinput_drive.py`
(real X11 keyboard and mouse input, and a real focus loss).

The slice's fighting-game scripts (`journey.txt`, `smoke.txt`, `matrix.txt` and the others) drive screens this flow
no longer shows. The combat core tests (`Tests/Core`) are unchanged.

## Known limits

- Footsteps sound only in water (`S_StepWater`). Dry surfaces (pews, altar steps, rubble) are silent; there is no dry
  step sound yet.
- The placeholder body is a fighting-stance model. Its shadow shows raised guard arms and its walk is a fighting
  shuffle.
- The west wall blockout is plain and very dark. Most of the Chapel's light comes from the east.
- No music plays in first person; the Chapel ambience does.
