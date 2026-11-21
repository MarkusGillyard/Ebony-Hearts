# First-person prototype

This branch (`proto/first-person`) turns the Drowned Chapel into a first-person space. Milestone 2, Walk the Chapel:
the player walks, sprints, jumps and crouches through the flooded nave. Milestone 3, Fists: a jab, a straight, a
shove and a held block, practised on a training dummy. The game starts straight in the Chapel, with no title screen or menus
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
| Jab | Left mouse button | R1 / RB |
| Straight | Right mouse button | R2 / RT |
| Shove | E | Circle / B |
| Block (hold) | Q | L1 / LB |
| Pause | Escape (fixed) | Menu / Options (fixed) |

- **Keyboard holds and toggles.** Settings > Controls > Keyboard can make sprint and crouch toggle.
- **Look settings.** Mouse sensitivity is in degrees per mouse count (default 0.08). Controller look speed scales the
  stick's full-tilt turn rate (default 100%). Invert look applies to both. Field of view (Video, horizontal degrees,
  default 90) applies immediately.
- **Mouse buttons** can be bound to actions on the keyboard-and-mouse layout. Escape, F10 (reserved for the developer
  panel) and the console key cannot.
- **Losing focus.** When another window takes focus, the game pauses and forgets every held key and stick, so
  nothing keeps walking. It pauses once, at the moment focus is lost: Slate can report the game inactive for a moment
  after the window returns, and the player can resume at once.
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

## Physical techniques

The techniques are game state stepped at 60 frames per second (`EHFists.*`). Hit detection, the dummy's reactions, the
sounds and the arms all read that state, so what the player sees and what connects come from one place.

| Technique | Frames (startup / active / recovery) | Reach | Damage | Hitstop | Walking speed during it |
|---|---|---|---|---|---|
| Jab | 6 / 3 / 10 (0.32 s) | 95 cm | 6 | 3 frames | 80% |
| Straight | 11 / 3 / 18 (0.53 s) | 115 cm | 12 | 5 frames | 70% |
| Shove | 9 / 4 / 18 (0.52 s) | 100 cm, wider | 0; pushes 2 m over 15 frames | 2 frames | 70% |
| Block (hold) | rises in 5 frames, lowers in 6 | | stops 70% from within 70° of the view | | 60% |

Damage, the shove's 2 m and the guard's 70% are the prototype plan's proposed values; frames, reach, hitstop and
speeds are engineering starting points (`Content/Data/firstperson.json`, `fists`).

- **Aim.** A strike sweeps a sphere along the view from the eyes. A wall or pier in between stops it (a knock on stone,
  no hit).
- **Combos.** The jab chains into the straight as soon as its active frames end, hit or miss. The straight chains
  into nothing. A press up to 8 frames before a technique allows it still counts; a later one is dropped.
- **Guard.** While the guard is held no technique starts; one pressed while it lowers comes out as soon as it is down.
  Sprinting stops for any technique or the guard.
- **Contact.** Hitstop holds the fist and the target together; the view tilts slightly (none with Reduce camera
  shake); a small spark appears at the fist.
- **Health and death.** The player has 100 Health. A blow that empties it resets the Chapel at once: the player at the
  entrance with full Health and Stamina, the dummy back in place, every technique and its effects cleared. A thin red
  line above Stamina shows Health after a hit (hidden with the Stamina meter set to Off).

### Arms

Placeholder arms made of plain shapes (`EHViewArms.*`): shoulders, elbows by two-bone IK, fists. They are drawn as
first-person primitives, with their own 72° field of view and pulled toward the eyes (first-person scale 0.6), so
they never clip into walls, and they appear only while a technique or the guard needs them, staying up 0.6 s after the
last one. Each fist arrives at full extension exactly on the technique's first active frame and holds through hitstop.

### Training dummy

The slice's Ashka test model stands in the nave 4.5 m in front of the start (`EHTrainingDummy.*`). Pause > Training
dummy switches it between **Stand** (takes every hit), **Guard** (blocks hits from its front, 70% stopped) and
**Strikes back** (when the player is within 1.7 m and in front of it, a slow 24-frame wind-up into a 10-damage punch,
then 70 frames before the next; a hit in the wind-up stops it). It turns to face the player, reacts to each technique,
and is pushed by the shove, sliding along anything it meets. Above it a training readout counts hits, blocks and
damage. Reset the dummy puts it back with its count cleared.

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
| `fp_expect <field> <lt\|gt\|eq\|near> <value> [tolerance]` | all | checks stamina, speed, vz, x, y, z, yaw, pitch, crouched, sprinting, exhausted, falling, water, eye, paused, screen, fov, moved, health, deaths, guarded, hurt, action, guarding, arms, dummy_hits, dummy_blocks, dummy_damage, dummy_strikes, dummy_dist, dummy_moved |
| `fp_mark` | all | remembers the feet position for `fp_expect moved` |
| `fp_reset` | all | what the pause menu's Return to the start does |
| `fp_focus_lost` | all | what losing window focus does (pause, drop held input) |
| `fp_dummy <stand\|guard\|strikes>`, `fp_dummy_reset` | all | what the pause menu's dummy controls do |
| `fp_frames <count> <name>` | all | slows the world to 1/20 and saves one screenshot per combat frame |
| `fp_teleport`, `fp_view`, `fp_box`, `fp_clear_boxes`, `fp_body_visible`, `fp_planar`, `fp_dummy_place`, `fp_health`, `fp_arms_fp` | development only | test positions, a blocking test box, the body and reflection experiments, placing the dummy, test Health, arms drawn as ordinary geometry |

Scripts: `fp_movement.txt` (movement, Stamina, jump, crouch under a low ceiling, controller sticks and dead zone,
mouse look, water and steps, pause, focus loss, reset), `fp_controls_a.txt` and `fp_controls_b.txt` (remapping, then
persistence across a relaunch), `fp_audit.txt`, `fp_presentation.txt`, `fp_reflection_perf.txt`, `fp_perf.txt` and
`fp_perf_cold.txt` (a traversal route captured warm, after one pass, and cold, from start-up; inputs only, so they run
in Shipping) `fp_xinput.txt` with `fp_xinput_drive.py`
(real X11 keyboard and mouse input, and a real focus loss), `fp_pad.txt` with `fp_virtual_pad.py` (a virtual uinput
controller through SDL, including a disconnect), `fp_soak.txt` (the route eight times with pauses and settings
round trips), `fp_import.txt` (a profile that has only the slice's settings file), `fp_fists.txt` (every technique,
chain, buffer, whiff, wall, shove, the dummy's guard from the front and behind, its strike against the guard, a
wind-up interrupted, death, pause and reset mid-technique, the controller), `fp_ship_fists.txt` (the same ground
with inputs only, for Shipping and for footage) and `fp_fists_frames.txt` (frame-by-frame captures).

Scripted controller input uses `pad7`: a real controller connected to the machine takes the first device slots and
would override injected stick values on `pad0`.

The slice's fighting-game scripts (`journey.txt`, `smoke.txt`, `matrix.txt` and the others) drive screens this flow
no longer shows. The combat core tests (`Tests/Core`) are unchanged.

## Known limits

- Fists: the arms are plain shapes and the shove uses the same fists as the punches; final arms and animation are the
  creator's. The guard does not cost Stamina yet; stat scaling and anything gained from landed strikes come with the
  next milestone. The dummy's reactions and punch are the slice's fighting clips.

- Footsteps sound only in water (`S_StepWater`). Dry surfaces (pews, altar steps, rubble) are silent; there is no dry
  step sound yet.
- The placeholder body is a fighting-stance model. Its shadow shows raised guard arms and its walk is a fighting
  shuffle.
- The west wall blockout is plain and very dark. Most of the Chapel's light comes from the east.
- No music plays in first person; the Chapel ambience does.
