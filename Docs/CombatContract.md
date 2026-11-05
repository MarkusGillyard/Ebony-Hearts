# Combat and art contract

This is the shipped rule set for the first playable slice: Wren Ku and Ashka Rook in The Drowned Chapel. Every number lives
in `Content/Data` (`rules.json`, `Fighters/*.json`). The move tables below are generated from those files by
`Tools/Docs/move_tables.py`, and `Tests/Core` checks the behaviour. Values are tuning proposals that pass the automated
checks; they have not yet been validated by human playtesting.

## Controls

Movement is left/right. There are six combat actions, with no motion inputs and no chords:

| Action | Keyboard (left side) | Keyboard (right side) | PlayStation | Xbox |
|---|---|---|---|---|
| Move | A / D | Arrow keys | Left stick / D-pad | Left stick / D-pad |
| Light | J, or Enter | Numpad 1, or , | Square | X |
| Heavy | K, or Backspace | Numpad 2, or . | Triangle | Y |
| Special | L | Numpad 3, or / | R1 | RB |
| Grab | I | Numpad 5, or ; | Cross, or L1 | A, or LB |
| Dodge | O | Numpad 6, or ' | Circle | B |
| Block (hold) | Space | Numpad 0, or Right Shift | R2 | RT |
| Pause | Escape | Numpad 9, or = | Options | Menu |
| Training reset | R | Numpad 7, or - | Share | View |

Grab has two independent default controller buttons (Cross / A and L1 / LB). Block reads the analog trigger. Menus use
fixed controls separate from these gameplay layouts. Every gameplay action can be remapped; a taken button is never
silently reassigned (swap, replace or cancel). See [Controls](Controls.md).
Direction modifiers are relative to the opponent: "toward" and "away" are judged when the button is pressed, so a side
switch between the press and the move cannot reverse it.

## Timing model

- **Fixed simulation.** The simulation runs at 60 ticks per second with integer state (distances in 1/100 cm). Render time
  is converted to ticks by `FixedStepClock`. A render frame runs at most 4 ticks, and anything beyond that is dropped
  and counted, so a hitch slows the game briefly rather than resolving unseen combat. Pausing or losing focus resets the
  accumulator, so there is no catch-up burst afterwards.
- **Render rate cannot change outcomes.** Rendering interpolates positions between ticks and samples animation at the
  simulation's frame, so the pose matches the hitboxes and freezes during hitstop. A higher refresh rate cannot speed up
  attacks or move cancel windows. The tests replay one recorded match through clocks driven at 30, 60, 75, 144, 165 and
  240 Hz, with frame-time jitter, and require identical state hashes. Determinism is claimed only for one binary on one
  machine; nothing here is rollback-ready.
- **Frame counting.** Frame 1 of a move is the tick its button is processed. "Startup N" means the hitbox is first active
  on frame N. Stun N means the defender can act on the (N+1)th tick after contact. On-block and on-hit advantage are
  measured live in Training using the same definitions.

## Priority within a tick

Each tick runs in this order:
1. Inputs are buffered.
2. Timers advance.
3. Throws in progress advance, and escape presses are checked.
4. Actionable fighters act: a cancel, a buffered move, block, or walking.
5. Movement, pushboxes, walls and the separation limit are resolved.
6. Hits and grabs are detected.
7. Facing updates.
8. The round end is checked.

Detection outcomes:
- **Strike against strike on the same tick:** both hit (a trade). Trades never count as counter hits.
- **Strike against grab on the same tick:** the strike wins.
- **Grab against grab:** both break apart (tech).
- **Grab against a fighter in strike startup:** the grab wins.
- **Duplicate hits:** each hit entry of a move instance can connect once.

## Rules

| Rule | Value | Notes |
|---|---|---|
| Input buffer | 6 ticks | A press stays usable for 6 ticks, including the tick it was made on. Buffer ageing pauses during the presser's hitstop. Newest press wins; on the same tick the order is Grab > Special > Heavy > Light > Dodge. Holding a button never repeats it. |
| Cancels | per move | Light 1 > Light 2 > Light 3 on hit or block, and Light 1 / 2 into any special on hit or block. Heavy into a special on hit only. Light 3, toward + Heavy, specials, grabs and dodges never cancel. |
| Hitstop | 7-16 | Both fighters freeze; block hitstop is 2 shorter. |
| Counter hit | +2 hitstun, x1.10 damage | Hitting a move in startup or active frames. Some heavies knock down on counter. |
| Punish | +4 hitstun, x1.20 damage | Hitting a move's recovery, a whiffed grab or a dodge's vulnerable frames. |
| Combo scaling | 100, 100, 80, 70, 60, 50, 40% | Per hit in a combo; the last value repeats. |
| Hitstun decay | -2 per hit from the 3rd | Floor of 8 ticks. Combined with pushback this ends every route; a randomized search finds no combo longer than 5 hits. |
| Knockdown | 42 lying + 60 rising | Fully invulnerable. After waking, the fighter cannot be grabbed for 6 ticks; after leaving hitstun or blockstun, for 4. |
| Block | hold | Instant on an actionable tick. No walking while blocking. Blockstun and pushback are per move. Specials chip, but chip never KOs. |
| Timed block (deflect) | 4-tick window | A fresh Block press 0-3 ticks before contact deflects: 4 fewer blockstun ticks, no chip, more gauge. A press that does not deflect locks out deflects for the next 12 ticks, so mashing never works. Holding Block still blocks everything. |
| Grab | startup 5, active 2 | Range is the gap between the fighters' fronts (Wren 26 cm, Ashka 30 cm). Whiff recovery 26-27. Beats blocking and recovery; cannot grab airborne, stunned, knocked-down or grab-invulnerable fighters. |
| Grab escape | 9 ticks | Press Grab within 9 ticks of being grabbed; both separate 120 cm and recover for 20 ticks. A press made before the grab connected does not count. |
| Dodge | toward = forward roll, otherwise back roll | Strike-invulnerable frames 4-15 (forward) or 3-12/13 (back), but grabbable on every frame. The forward roll passes through the opponent. A 14-tick lockout follows each dodge, and the recovery can be punished. |
| Corners | stage half-width 700 cm | Pushback a wall absorbs moves the attacker back instead. A grab that would land a victim beyond the wall moves the thrower in to keep the authored spacing. |
| Separation | 560 cm | The camera edge acts as a wall for whoever is retreating. |
| Gauge | 0-1000 | Earned: hits 80% of damage dealt and 40% of damage taken; blocking +20 for the attacker and +30 for the defender; deflects +80. No gain while Spirit Enhanced Strikes is active. |
| Rounds | first to 2, 75 s | KO wins the round. On timeout the higher health percentage wins and equal health is a draw. A double KO is a draw. A draw round awards no win. At most 5 rounds; if wins are still level after that, the match is drawn. |
| Rematch / reset | full | A rematch builds a fresh simulation; Training reset rebuilds both fighters (gauge kept). |

## Character kits

Shared structure: each fighter has a Light string, Heavy, toward + Heavy, three specials (neutral, toward, away), Grab
(toward/neutral or away picks the throw) and two dodges. The fighters do not share animations or tuning.

**Wren Ku** is an all-rounder with kicking reach, spinning and flying techniques, and real grappling. Her Light string
is jab, cross, spinning back elbow. Heavy is a long roundhouse kick; toward + Heavy is an advancing spinning back kick.
Her specials:
- **720 Hook Kick** (neutral). The signature technique, deliberately slow: startup 35 and airborne from frame 11. It can
  be read and answered, since hitting her in the air knocks her down. It has big reach and damage, and it is heavily punishable on block (see the table).
- **Tornado Kick** (toward). Travels and ends Light strings.
- **Spirit Enhanced Strikes** (away). Spends a full gauge. The golden lightning aura lasts 8 s (480 ticks), raises
  strike damage to 120% and halves the damage of energy (flame) attacks. It cannot stack, gauge does not build while it
  is active, and it is lost if she is hit before it applies on frame 24.

Her grabs are a double-leg slam (toward/neutral) and a belly-to-belly suplex (away), which switches sides.

**Ashka Rook** is a composed Muay Thai specialist who controls space with teeps and wins up close with elbows, knees and
the clinch. Her Light string is jab, stepping horizontal elbow, step-in knee. Heavy is a Thai body kick; toward + Heavy
is a long teep with large pushback. Her Lamplighter Flame variations:
- **Flame Elbow** (neutral). A leaping downward elbow wreathed in crimson flame.
- **Flying Knee** (toward). Ends strings.
- **Flame Burst** (away). Spends half a gauge. Invulnerable through frame 10, so it works as a reversal, but it is
  heavily punishable on block.
Her flame attacks deal energy damage, which is what Spirit Enhanced Strikes defends against. Her grabs are clinch knees
(toward/neutral) and a clinch turn trip (away), which switches sides.

Verified example combos (`Tests/Core`, `example_combos_each_fighter`): Light, Light, Light; Light, Light into
toward + Special; and Light into toward + Special, from up to 100 cm, for both fighters.

<!-- move-tables:begin -->

### Wren Ku

Health 1000; walk 2.8 cm/frame forward, 2.4 back; pushbox half-width 24 cm; standing hurtbox [-26, 0, 26, 178] cm.

| Input | Move | Startup | Active | Recovery | Reach (cm) | Damage | On block | On hit | Cancels | Gauge | Notes / counterplay | Anim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Light | Jab | 8 | 2 | 11 | 83 | 30 | +1 | +5 | L2, @special on hit/block (8-19) | - | Fast check. Chains into Cross, cancels into specials. | `L1` |
| Light, Light | Cross | 9 | 2 | 14 | 96 | 36 | -1 | +4 | L3, @special on hit/block (9-21) | - | Second hit of the string. Cancels into the third hit or a special. | `L2` |
| Light x3 | Spinning Back Elbow | 9 | 3 | 19 | 109 | 52 | -7 | +1 | - | - | String ender. Pushes back; punishable up close on block. | `L3` |
| Heavy | Roundhouse Kick | 16 | 3 | 29 | 152 | 88 | -6 | +2 (KD on counter) | @special on hit (16-27) | - | Long kick. Special-cancel on hit; knocks down on counter. | `H` |
| toward + Heavy | Spinning Back Kick | 21 | 3 | 24 | 189 | 100 | -5 | +3 (KD on counter) | - | - | Advancing spin with big pushback; safe at tip range. | `FH` |
| Special | 720 Hook Kick | 35 | 3 | 41 | 231 | 165 (chip 16) | -14 | knockdown | - | - | Signature. Slow, airborne, devastating; very punishable if blocked. | `S` |
| toward + Special | Tornado Kick | 17 | 3 | 33 | 206 | 105 (chip 10) | -10 | knockdown | - | - | Travelling jump kick. Ends light strings; knocks down. | `FS` |
| away + Special | Spirit Enhanced Strikes | applies 24 | - | 44 | - | - | - | - | - | 1000 | Full gauge: more strike damage, half damage from flame for 8 s. | `BS` |
| Grab | Grab | 5 | 2 | 27 | grab 26 | - | - | throw | - | - | Beats blocking. Toward: double-leg slam. Away: shoulder throw, swaps sides. | `T` |
| toward + Dodge | Forward Roll | invuln 4-15 | - | 15 | - | - | - | - | - | - | Rolls through strikes and past the opponent. Can be grabbed. | `DF` |
| Dodge (away/neutral) | Back Roll | invuln 3-13 | - | 19 | - | - | - | - | - | - | Retreating roll. Recovery is punishable. | `DB` |

| Throw | Duration | Damage frame | Damage | Lands | Victim knockdown | Anims |
|---|---|---|---|---|---|---|
| Double-Leg Slam | 74 | 34 | 110 | 120 cm in front | 34 | `ThrowF` / `Victim_WrenThrowF` |
| Shoulder Throw | 72 | 48 | 120 | 110 cm behind (side switch) | 36 | `ThrowB` / `Victim_WrenThrowB` |

### Ashka Rook

Health 1000; walk 2.6 cm/frame forward, 2.3 back; pushbox half-width 22 cm; standing hurtbox [-24, 0, 24, 170] cm.

| Input | Move | Startup | Active | Recovery | Reach (cm) | Damage | On block | On hit | Cancels | Gauge | Notes / counterplay | Anim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Light | Jab | 8 | 2 | 15 | 77 | 28 | +2 | +6 | L2, @special on hit/block (8-22) | - | Fast jab. Chains into the elbow, cancels into specials. | `L1` |
| Light, Light | Horizontal Elbow | 9 | 2 | 20 | 99 | 40 | +2 | +6 | L3, @special on hit/block (9-26) | - | Stepping horizontal elbow. Cancels into the knee or a special. | `L2` |
| Light x3 | Step-In Knee | 8 | 3 | 17 | 97 | 54 | -5 | +3 | - | - | Driving knee. String ender. | `L3` |
| Heavy | Body Kick | 16 | 3 | 27 | 138 | 84 | -6 | +3 (KD on counter) | @special on hit (16-27) | - | Muay Thai body kick. Special-cancel on hit. | `H` |
| toward + Heavy | Teep | 16 | 3 | 19 | 152 | 60 | -3 | +1 (KD on counter) | - | - | Teep. Long reach, huge pushback; controls space. | `FH` |
| Special | Flame Elbow | 12 | 3 | 25 | 149 | 115 (chip 12) | -11 | knockdown | - | - | Leaping downward elbow wreathed in crimson flame. Knocks down. | `S` |
| toward + Special | Flying Knee | 22 | 3 | 26 | 207 | 120 (chip 12) | -11 | knockdown | - | - | Flying knee with flame. Ends light strings; knocks down. | `FS` |
| away + Special | Flame Burst | 7 | 4 | 39 | 125 | 115 (chip 12) | -28 | knockdown | - | 500 | Half gauge: invulnerable flame burst. Heavily punishable if blocked. | `BS` |
| Grab | Clinch | 5 | 2 | 26 | grab 30 | - | - | throw | - | - | Beats blocking. Toward: clinch knees. Away: clinch turn, swaps sides. | `T` |
| toward + Dodge | Forward Roll | invuln 4-15 | - | 15 | - | - | - | - | - | - | Rolls through strikes and past the opponent. Can be grabbed. | `DF` |
| Dodge (away/neutral) | Back Roll | invuln 3-12 | - | 18 | - | - | - | - | - | - | Quick retreating roll. Recovery is punishable. | `DB` |

| Throw | Duration | Damage frame | Damage | Lands | Victim knockdown | Anims |
|---|---|---|---|---|---|---|
| Clinch Knees | 64 | 44 | 115 | 115 cm in front | 34 | `ThrowF` / `Victim_AshkaThrowF` |
| Clinch Turn Trip | 56 | 38 | 105 | 105 cm behind (side switch) | 36 | `ThrowB` / `Victim_AshkaThrowB` |

<!-- move-tables:end -->

## Canon boundaries

- **Confirmed canon** (from the character sheets):
  - **Wren:** names, aliases, heights and builds, hair (two braids for Wren, a loose crimson braid with bangs and two
    face-framing strands for Ashka), eye colours, her black and ocean-blue motif, MMA and Look See Do, and her listed
    techniques, including the 720 Hook Kick. Spirit Enhanced Strikes is a golden lightning aura that raises strike damage
    and defence against energy and magical attacks.
  - **Ashka:** her title, her outfit (white long-sleeved shirt, black tie, black pants, brown loafers, long black trench
    coat), the crimson cross-shaped lamp tattoo, Muay Thai and Flame Style, and her listed techniques. Her Lamplighter
    Flame is crimson, and she describes it as purifying.
  - **Relationship:** they are best friends.
- **Gameplay proposals, not canon:**
  - all frame data and damage
  - the gauge and its labels (SPIRIT, FLAME)
  - the 8 s aura duration and its multipliers
  - Flame Burst's invulnerability and gauge cost
  - which techniques sit on which buttons
  - throw choices
  - the CPU's behaviour
  - Wren's and Ashka's fighting each other as a versus/sparring setup, which carries no story meaning
- **Deliberately unresolved:**
  - the origins and rules of Look See Do and the Fighting Spirit of Humanity
  - the full properties of the Lamplighter Flame, including any mechanical "purifying" effect (none is implemented)
  - Ashka's background, origin and her people's disappearance
  - how the tournament-era biographies relate to the concept's Forsaken / Drowning War premise
  - The Drowned Chapel's place in the world's history
  No scene in this slice depends on resolving these.
- **Wren's established outfit and other outfits:** her established in-game outfit, BJJ gi, Muay Thai gear and black
  military uniform remain documented options. Only the primary outfit ships in this slice (see the Status document for
  what was and was not produced).

## Production conventions

- **Axes.**
  - Unreal world: X is the fighting axis (screen right), Z is up, the fighting plane is at Y = 0, the camera sits on
    +Y looking -Y, and the background recedes toward -Y.
  - Blender source: X right, +Y into depth, Z up, metres. FBX import flips Y.
  - Fighters face +X when the simulation's facing is +1 and open 12° toward the camera. A fighter facing -1 is
    mirrored along X, not turned.
  - When a fighter's facing flips, its next animation starts without a blend (a blend would start from the old
    pose, now mirrored). An animation that switches sides must end on the next one's first frame as drawn after
    the flip.
  - Within 75 cm of each other the fighters are staggered up to 10 cm apart in depth (the one facing right toward
    the camera), so bodies standing chest to chest do not pass through each other. The stagger is off during throws
    and throw escapes, which are authored on the line. Presentation only.
- **Units.** Data is authored in centimetres and frames (60 Hz). The simulation uses integer units of 1/100 cm.
- **Animation keys.** Asset `A_<Fighter>_<Key>` under `/Game/Characters/<Fighter>/Anims`, authored at 60 fps. The
  animation frame must equal the move frame, so contact happens on the move's first active frame.
  - Move keys come from the `anim` field.
  - State keys: `Idle`, `WalkF`, `WalkB`, `Guard`, `BlockHit`, `HitLight`, `HitHeavy`, `Knockdown`, `KnockdownLie`
    (lying after a throw lands, and held when a throw knocks out), `KnockdownLieRev` and `GetupRev` (the same after a
    throw marked `landsHeadToward`: lying head toward the thrower, and rising facing away then pivoting round), `Getup`, `ThrowTech`, `KO`, `Win`, `Defeated`, `Intro`, plus
    `Victim_<Thrower><Throw>` for each throw (both fighters need all four victim animations).
  - Optional string keys `<Move>_from_<Previous>` (for example `L2_from_L1`): played instead of `<Move>` when it
    cancels out of `<Previous>`, so a captured combo can supply both hits. A string key starts from `<Previous>`'s pose
    at its first active frame, where a buffered string cancels (checked by a core test).
  - Optional throw escape keys `ThrowTech_from_<throw animation>_F<n>`, n = 2, 5 or 8 (for example
    `ThrowTech_from_ThrowF_F5` for a thrower, `ThrowTech_from_Victim_WrenThrowB_F2` for a victim): played instead
    of `ThrowTech` when the escape comes on throw frames 1–3, 4–6 or 7–9. Each starts from that throw animation's frame
    n, so the escape begins where the pair was; `build_anims` makes them with the throws.
  - Throws are authored as a pair in the thrower's space, the victim at `holdX` facing the thrower. Each victim
    animation is exported in the space the game draws the victim in (its own, opened toward the camera and
    mirrored when facing left), so the pair meets as authored.
- **Presentation data.** `Content/Data/presentation.json` holds display names, mesh and animation paths, effect bones
  and sound names. It never changes combat outcomes.
- **Sounds.** `/Game/Audio/<Combat|UI|Ambience|Music>/S_<Name>`. Names that end in `_01`-`_03` are random variations.
