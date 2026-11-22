# First-person prototype

This branch (`proto/first-person`) turns the Drowned Chapel into a first-person space. Milestone 2, Walk the Chapel:
the player walks, sprints, jumps and crouches through the flooded nave. Milestone 3, Fists: a jab, a straight, a
and a held block, practised on a training dummy (the shove was removed on 2026-11-22: quality over quantity). Milestone 4, Magic: the seven stats, Qhi, Fireball and Ice
Wall, with the wall's water freeze and Fireball's melt. The game starts straight in the Chapel, with no title screen or menus
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
| Block (hold) | Q | L1 / LB |
| Fireball | F | L2 / LT |
| Ice Wall | R | Triangle / Y |
| Choose a spell (hold) | Tab | Square / X |
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

First person keeps its own file, `Saved/EbonyHearts/FirstPersonSettings.json` (format version 9), so the 2.5D
slice's `Settings.json` is never rewritten. On the first launch, when only the slice's file exists, its display,
audio, accessibility and button-prompt values carry over and a notice says so. The fighting layouts load as before but
are not used in first person. The first-person layouts start at the defaults above; no fighting action maps onto a
first-person action. Version 6 adds the two first-person layouts (`fpKeyboard`, `fpController`) and the look,
field-of-view, hold/toggle and Stamina-meter settings; version 7 the four techniques and Controller vibration;
version 8 Fireball and Ice Wall; version 9 removed the shove (its keys are simply free) and added Choose a spell
and the Spell selector setting. Each new action takes its default key only where the player has not already used
that key for something else, and a notice names any that were left for the player to choose.

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
| Jab | 6 / 3 / 10 (0.32 s) | 95 cm | 6 | 4 frames | 80% |
| Straight | 11 / 3 / 18 (0.53 s) | 115 cm | 12 | 7 frames | 70% |
| Block (hold) | rises in 5 frames, lowers in 6 | | stops 70% from within 70° of the view | | 60% |

Damage and the guard's 70% are the prototype plan's proposed values; frames, reach, hitstop and
speeds are engineering starting points (`Content/Data/firstperson.json`, `fists`).

- **Aim.** A strike sweeps a sphere along the view from the eyes. A wall or pier in between stops it (a knock on stone,
  no hit).
- **Combos.** The jab chains into the straight as soon as its active frames end, hit or miss. Any strike's recovery
  hands over to a cast the same way, and a cast's recovery to a strike (see Magic). A press up to 8 frames before a
  technique allows it still counts; a later one is dropped.
- **Guard.** While the guard is held no technique starts; one pressed while it lowers comes out as soon as it is down.
  Sprinting stops for any technique or the guard.
- **Contact.** Hitstop holds the fist and the target together. Meanwhile the striking fist gives back about 3 cm into
  the arm and shudders, and the view holds a small push into the blow with a roll toward the punching hand (none with
  Reduce camera shake). Then everything releases at once. Each hit plays a crack and a low thud, varied in pitch
  (body shots duller), and rumbles the controller (Settings > Controls > Controller vibration). Walls give a short
  jar.
- **Health and death.** The player has 100 Health. A blow that empties it resets the Chapel at once: the player at the
  entrance with full Health and Stamina, the dummy back in place, every technique and its effects cleared. A thin red
  line above Stamina shows Health after a hit (hidden with the Stamina meter set to Off).

### Arms

Placeholder arms cut from the slice's Wren model (`SK_FPArms_Wren`: her upper arms, forearms and gloved hands, on her
skeleton and with her materials; `Tools/Blender/fparms/cut_fp_arms.py` makes it from `SK_Wren.fbx`,
`Tools/Unreal/import_fp_arms.py` imports it). `EHViewArms.*` holds the model's fists from her guard clip, squares her
bladed shoulders to the view and turns them into each blow (the straight drives the right shoulder through), and
reaches each wrist to the technique's fist position by two-bone IK in `EHAnimInstance` (elbows down and out). The arms
are drawn as first-person primitives, with their own 72° field of view and pulled toward the eyes (first-person scale
0.6), so they never clip into walls, and they appear only while a technique or the guard needs them, staying up 0.6 s
after the last one. Each fist arrives at full extension exactly on the technique's first active frame and holds
through hitstop. If the model cannot load, plain engine shapes stand in.

### Training dummy

The slice's Ashka test model stands in the nave 4.5 m in front of the start (`EHTrainingDummy.*`). Pause > Training
dummy switches it between **Stand** (takes every hit), **Guard** (blocks hits from its front, 70% stopped) and
**Strikes back** (when the player is within 1.7 m and in front of it, a slow 24-frame wind-up into a 10-damage punch,
then 70 frames before the next; a hit in the wind-up stops it). It turns to face the player and reacts physically rather than playing clips: damped springs on its head and chest
are kicked along the line of the blow when the hitstop ends, on top of its stance. Every reaction drives away from the attacker and settles back
without swinging toward them. A jab snaps the head back and lets go; a straight snaps it hard, turns the shoulders with
the punching hand and slides the body back about 35 cm (out of jab reach, so the straight ends a combination); a
strike landing below the neck drives the chest back first, the head following less; a guarded strike moves only the
arms and chest. Above it a training readout counts hits, blocks and
damage. Reset the dummy puts it back with its count cleared.

## Magic

### Stats and Qhi

All seven stats exist at one fixed set of values (`Content/Data/firstperson.json`, `stats`). Health, Qhi and Stamina
are pools; the other four act through simple shares, measured from a base of 10 where every value is the plan's:

| Stat | Starting value | What it does in the prototype |
|---|---|---|
| Health | 100 | damage taken before the reset |
| Qhi | 100 | the pool spells draw from |
| Stamina | 100 | spent by sprinting |
| Intelligence | 10 | each point above 10 speeds Qhi regeneration by 5% |
| Faith | 10 | each point above 10 speeds Qhi regeneration by 5% |
| Dexterity | 10 | each point above 10 speeds Stamina recovery by 5% |
| Martial Prowess | 10 | each point above 10 adds 5% to the jab's and the straight's damage |

- **Regeneration.** 5 Qhi per second at base Intelligence and Faith, starting 0.5 s after the last cast.
- **Strikes feed Qhi.** A technique that lands restores 4 Qhi; one the target guards does not.
- **Spending.** A spell costs its Qhi once, the moment its cast starts. A cast without enough Qhi is refused: nothing is
  spent, the arms stay down, a short denied sound plays and the Qhi line flashes. Qhi never goes above the pool or
  below zero.
- **Readout.** A thin blue line below Stamina shows Qhi while it changes, following the Stamina meter setting. Like
  the others it is a playtest placeholder.
- **Interpretation.** The plan says which stat affects what but not by how much; the 5% shares are engineering
  starting points. "Physically enhanced spells" do not exist yet, so Martial Prowess touches only the techniques.

### Spells

Casts are part of the same 60 Hz technique state as the strikes, so the buffer, the walking speed and the arms work
the same way. The recovery of any strike hands over to a cast, and the recovery of a cast to a strike, so a straight can
go straight into a Fireball and a Fireball straight into a straight.

| Spell | Cost | Cast (wind-up / release / recovery) | Effect |
|---|---|---|---|
| Fireball | 20 Qhi | 12 / 1 / 16 frames (0.48 s), walking at 60% | a ball of fire from the left hand toward the centre of the view, 22 m/s, 30 m range; 25 damage on contact |
| Ice Wall | 30 Qhi | 14 / 1 / 20 frames (0.58 s), walking at 50% | a wall 3 m wide, 2.4 m high and 0.6 m deep rises 2.2 m ahead across the view in 0.3 s and stands for 8 s |

- **Fireball** hits the first thing in its path: the dummy (a heavy reaction, knocked back about a step; the Guard
  mode stops 70% from the front), an Ice Wall, which melts at once in a burst of steam, or stone. The wind-up is the
  risk: next to a target, a jab or straight comes first.
- **Ice Wall** blocks the player, the dummy, strikes and Fireballs (until one melts it). It stands across the view's
  heading, stopping short of any wall or pier in the way; with less than 1.1 m of room it is refused and costs
  nothing. A dummy standing where it rises is pushed out of the ice on the side it stood on. When its 8 s are up it turns
  to water over 1.6 s: the frost goes, the ice clears and runs wet, the shards thin and shorten where they stand,
  water drips and ripples around the foot, and a glossy puddle spreads under it, drying away over 4 s. The way is open
  the moment it starts to melt. A Fireball melts it the same way in 0.6 s, in a burst of steam. 60 damage of strikes
  (five straights) shatters it instead.
- **Water freeze.** If the wall rises in water, the water within 2.8 m freezes into a sheet. An opponent whose feet
  are in that water at any moment of the 0.3 s rise is trapped for 2 s: it cannot slide or turn, though it
  can still strike. On dry floor nothing freezes.
- **Look.** Plain placeholders: a glow gathers in the casting hand (fire in the left, frost in both for the wall); the
  Fireball is a glowing card with a trail of glow sprites and a point light. The wall is a ridge of leaning,
  faceted crystal shards that pushes up out of the floor in a burst of frost and mist; a faint cold light inside it lights the ice and the floor. The frozen water is an irregular floe and frozen
  feet get a ring of small shards (meshes from `Tools/Blender/magic/make_ice.py`). The ice material
  (`/Game/Magic/M_PH_Ice`, `Tools/Unreal/make_magic_materials.py`) is clear blue, refractive, glossy and frosted at
  its feet and in streaks. The sounds are the slice's (flame ignite,
  roar and hit for Fireball; aura charge, deflect and a body slam for the wall; water steps and a fading hiss as it melts).
- **Navigation.** The wall's blocking box is marked to affect navigation for the wolves of milestone 5; nothing
  navigates yet.

### Spell selector

Hold Choose a spell (Tab, Square / X) to open every spell; the world slows to a quarter speed while it is open, and
the mouse and right stick choose instead of looking. Settings > Controls > Spell selector picks the form:

- **Wheel** (default): the spells sit around a ring (Fireball left, Ice Wall right). Move the mouse or tilt the right
  stick toward one and let go to cast it; letting go at the centre casts nothing.
- **List**: the spells in a column beside the centre, the first lit. Move the mouse up or down, flick the right stick,
  or press W / S or the D-pad to move; let go to cast the lit one.

Each entry shows the spell's cost and its button when it has one, so a spell left without a button (Settings >
Controls) is still one press away. A spell the Qhi cannot pay for is dimmed and is refused like a button press.
Pausing or the reset closes the selector without casting.

### Developer panel (development builds only)

F10 opens a panel with the seven stats (left and right change them live), the current Health, Qhi and Stamina, Empty
Qhi, Default stats and Return to the start. Stat changes last until the game closes and survive the death reset, so a
case can be repeated. Shipping builds compile the panel out; F10 does nothing there.

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
- **Limbs.** The arms of milestone 3 (see Arms above) appear only for techniques and the guard.
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
| `fp_expect <field> <lt\|gt\|eq\|near> <value> [tolerance]` | all | checks stamina, speed, vz, x, y, z, yaw, pitch, crouched, sprinting, exhausted, falling, water, eye, paused, screen, fov, moved, health, deaths, guarded, hurt, action, guarding, arms, dummy_hits, dummy_blocks, dummy_damage, dummy_strikes, dummy_dist, dummy_moved, qhi, qhi_max, health_max, casts, refused, refused_qhi, refused_room, fizzles, fireballs, fireball_hits, walls, walls_raised, walls_melted, walls_shattered, walls_expired, wall_solid, wall_hp, wall_ice_water, wall_dist, puddles, selecting, select_highlight, select_casts, time_dilation, dev_panel, dummy_frozen, dummy_freezes |
| `fp_mark` | all | remembers the feet position for `fp_expect moved` |
| `fp_reset` | all | what the pause menu's Return to the start does |
| `fp_focus_lost` | all | what losing window focus does (pause, drop held input) |
| `fp_dummy <stand\|guard\|strikes>`, `fp_dummy_reset` | all | what the pause menu's dummy controls do |
| `fp_frames <count> <name>` | all | slows the world to 1/20 and saves one screenshot per combat frame |
| `fp_teleport`, `fp_view`, `fp_box`, `fp_clear_boxes`, `fp_body_visible`, `fp_planar`, `fp_dummy_place`, `fp_health`, `fp_arms_fp` | development only | test positions, a blocking test box, the body and reflection experiments, placing the dummy, test Health, arms drawn as ordinary geometry |
| `fp_arms_state` | development only | logs the arms model's placement and bone positions |
| `fp_stat <health\|qhi\|stamina\|intelligence\|faith\|dexterity\|martial> <value>`, `fp_qhi <value>` | development only | the developer panel's stat changes; sets current Qhi |
| `fp_selector <wheel\|list>` | all | what Settings > Controls > Spell selector does |
| `fp_devkey` | all | F10 as the keyboard sends it (opens the developer panel in development builds; nothing in Shipping) |

Scripts: `fp_movement.txt` (movement, Stamina, jump, crouch under a low ceiling, controller sticks and dead zone,
mouse look, water and steps, pause, focus loss, reset), `fp_controls_a.txt` and `fp_controls_b.txt` (remapping, then
persistence across a relaunch), `fp_audit.txt`, `fp_presentation.txt`, `fp_reflection_perf.txt`, `fp_perf.txt` and
`fp_perf_cold.txt` (a traversal route captured warm, after one pass, and cold, from start-up; inputs only, so they run
in Shipping) `fp_xinput.txt` with `fp_xinput_drive.py`
(real X11 keyboard and mouse input, and a real focus loss), `fp_pad.txt` with `fp_virtual_pad.py` (a virtual uinput
controller through SDL, including a disconnect), `fp_soak.txt` (the route eight times with pauses and settings
round trips), `fp_import.txt` (a profile that has only the slice's settings file), `fp_fists.txt` (every technique,
chain, buffer, whiff, wall, the dummy's guard from the front and behind, its strike against the guard, a
wind-up interrupted, death, pause and reset mid-technique, the controller), `fp_ship_fists.txt` (the same ground
with inputs only, for Shipping and for footage), `fp_fists_frames.txt` (frame-by-frame captures), `fp_magic.txt`
(stats, Qhi and both spells: one payment per cast, refusal, clamping, regeneration by stat, Qhi from strikes,
Dexterity and Martial Prowess, the wall blocking, freezing in and out of water, melting, obstruction, expiry,
breaking, both proximities, casts before and after strikes, the controller, pause, reset, death, the meltwater,
the spell wheel and list with mouse, stick and keys, the developer panel), `fp_ship_magic.txt` (the spells with inputs only, for Shipping and for footage; it expects F10 to do nothing)
and `fp_perf_magic.txt` (a warm frame-time capture with walls and Fireballs in play).

Scripted controller input uses `pad7`: a real controller connected to the machine takes the first device slots and
would override injected stick values on `pad0`.

The slice's fighting-game scripts (`journey.txt`, `smoke.txt`, `matrix.txt` and the others) drive screens this flow
no longer shows. The combat core tests (`Tests/Core`) are unchanged.

## Known limits

- Fists: the arms are Wren's, cut from her test model, and both casts use the same fists as the punches;
  final arms and animation are the creator's. The guard does not cost Stamina yet. The dummy's punch is the slice's
  fighting clip.
- Magic: the stat shares are engineering guesses; the ice, fire and their sounds are placeholders; the frozen sheet is
  a plain disc that can reach over a dry edge; nothing navigates around the wall until the wolves arrive. Enchanted
  strikes and lesser ice spells that strengthen the wall wait for their own specs.

- Footsteps sound only in water (`S_StepWater`). Dry surfaces (pews, altar steps, rubble) are silent; there is no dry
  step sound yet.
- The placeholder body is a fighting-stance model. Its shadow shows raised guard arms and its walk is a fighting
  shuffle.
- The west wall blockout is plain and very dark. Most of the Chapel's light comes from the east.
- No music plays in first person; the Chapel ambience does.
