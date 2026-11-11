# Combat and art contract

This is the shipped rule set for the first playable slice: Wren Ku and Ashka Rook in The Drowned Chapel. Every number lives
in `Content/Data` (`rules.json`, `Fighters/*.json`). The move tables below are generated from those files by
`Tools/Docs/move_tables.py`, and `Tests/Core` checks the behaviour. Values are tuning proposals that pass the automated
checks. The 2026-11-08 combat pass added crouching, guard heights, lows, the uppercuts, standalone combo-compatible throws
and a retuned jump (decisions and sources: [Research](Research.md)); none of it has been played by the creator yet.

## Controls

Movement is left/right; up jumps and down crouches. There are six combat actions, with no motion inputs and no chords:

| Action | Keyboard (left side) | Keyboard (right side) | PlayStation | Xbox |
|---|---|---|---|---|
| Move | A / D | Left / Right arrows | Left stick / D-pad | Left stick / D-pad |
| Jump | W, or I | Up arrow, Numpad 5, or ; | Cross, or left stick up / D-pad up | A, or left stick up / D-pad up |
| Crouch (hold) | S | Down arrow | Left stick down / D-pad down | Left stick down / D-pad down |
| Light | J, or Enter | Numpad 1, or , | Square | X |
| Heavy | K, or Backspace | Numpad 2, or . | Triangle | Y |
| Special | L | Numpad 3, or / | R1 | RB |
| Throw | U | Numpad 4, or M | L2 | LT |
| Dodge | O | Numpad 6, or ' | Circle | B |
| Block (hold) | Space | Numpad 0, or Right Shift | R2, or L1 | RT, or LB |
| Pause | Escape | Numpad 9, or = | Options | Menu |
| Training reset | R | Numpad 7, or - | Share | View |

Directions modify buttons and are judged when the button is pressed (a press waiting in the buffer keeps them), so a
side switch between the press and the move cannot reverse it: toward or away picks a toward/away move, and **down**
picks the uppercut (down + Heavy) and the low attack (down + Light) ahead of any horizontal direction (down-toward +
Heavy is the uppercut). Down with another button performs that button's standing move. Up wins over down when both are
held. Menus use fixed controls separate from these layouts. Every gameplay action can be remapped, with up to three
buttons each; see [Controls](Controls.md).

**Throws are standalone** (`"throws": true` in `rules.json`): each fighter has one throw on the Throw button, whatever
the stick says. The old grappling set (`"grappling": false`) stays in the data and code but out of play: directional
throw variants (Wren's shoulder throw, Ashka's clinch knees and clinch turn), with their animations. Sustained grappling,
clinch control and ground positions are not part of the game.

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
6. Hits and throws are detected.
7. Facing updates.
8. The round end is checked.

Steps 3 and 6 involve throws only while throws are switched on (`throws` or `grappling`). The posture (crouching) moves
with the actionable step and while in blockstun or landing. Detection outcomes:
- **Strike against strike on the same tick:** both hit (a trade). Trades never count as counter hits.
- **Strike against throw on the same tick:** the strike wins.
- **Throw against throw:** both break apart (tech).
- **Throw against a fighter in strike startup or recovery, guarding (standing or crouching), crouching or rolling:** the
  throw wins. Throws never catch a fighter in the air, knocked down, getting up or briefly after waking or leaving stun.
- **Duplicate hits:** each hit entry of a move instance can connect once.

## Rules

| Rule | Value | Notes |
|---|---|---|
| Input buffer | 6 ticks | A press stays usable for 6 ticks, including the tick it was made on, with the direction and down it was made with. Buffer ageing pauses during the presser's hitstop. Newest press wins; on the same tick the order is Throw > Special > Heavy > Light > Dodge. Holding a button never repeats it. |
| Cancels | per move | Light 1 > Light 2 > Light 3 on hit or block, Light 1 / 2 into any special on hit or block, and Light 1 / 2 into the throw **on hit only** (the combo throw). Heavy into a special on hit only. Light 3, toward + Heavy, the low, the uppercut, specials, throws and dodges never cancel. |
| Hitstop | 7-16 | Both fighters freeze; block hitstop is 2 shorter. |
| Counter hit | +2 hitstun, x1.10 damage | Hitting a move in startup or active frames. Some heavies knock down on counter. |
| Punish | +4 hitstun, x1.20 damage | Hitting a move's recovery, a whiffed throw or a dodge's vulnerable frames. |
| Combo scaling | 100, 100, 80, 70, 60, 50, 40% | Per hit in a combo; the last value repeats. |
| Hitstun decay | -2 per hit from the 3rd | Floor of 8 ticks. Combined with pushback this ends every route; a randomized search finds no combo longer than 5 hits. |
| Knockdown | 42 lying + 60 rising | Fully invulnerable. After waking, the fighter cannot be thrown for 6 ticks; after leaving hitstun or blockstun, for 4. An uppercut's knockdown is drawn as a launch (the body lifts and lands on its back); it is the same invulnerable knockdown, so nothing can follow it up. |
| Crouch | hold down | The posture lowers one step a frame over 3 frames (and rises the same way on release); the hurtbox blends from standing to crouching (Wren 110 cm, Ashka 105 cm tall), so highs pass over a crouching fighter. At least half way down the fighter guards and reels as crouching. No walking while crouched. Hitstun keeps the posture; blockstun and landing can change it; a jump, a standing move, a throw or a knockdown stands the fighter up. Standing moves started from a crouch use the standing hurtbox from their first frame. |
| Hit levels | per hit | **High**: blocked standing; passes over a crouching hurtbox (by its box). **Mid**: blocked standing or crouching. **Low**: blocked only crouching. **Overhead**: blocked only standing. Jump attacks are overheads on the way down and mids on the way up. |
| Block | hold | Instant on an actionable tick. No walking while blocking. Down + Block guards crouching. Blockstun and pushback are per move. Specials chip, but chip never KOs. |
| Timed block (deflect) | 4-tick window | A fresh Block press 0-3 ticks before a blockable hit deflects it: 4 fewer blockstun ticks, no chip, more gauge. A press that does not deflect locks out deflects for the next 12 ticks, so mashing never works. A deflect needs the right guard height. |
| Throw | startup 5, active 2 | From neutral: range is the gap between the fighters' fronts (Wren 26 cm, Ashka 30 cm); whiff recovery 26-27 (punishable). It beats standing and crouching guards, recovery and rolls; it cannot catch a fighter in the air, in hit- or blockstun, knocked down, getting up or throw-invulnerable. The thrower closes the gap to the authored hold over the first 8 frames (nobody teleports). |
| Combo throw | cancelled from Light 1 / 2 on hit | The throw then catches the opponent still reeling from that hit, from a little further (Wren 70 cm: a long shot; Ashka 45 cm: the clinch needs to be close). It is the combo's next hit: scaled by the combo, counted, and paying gauge once from the scaled damage. It cannot be escaped. A blocked light cannot cancel into it; a combo that dropped makes it an ordinary throw attempt. It ends in a knockdown. |
| Throw escape | 9 ticks | Press Throw within 9 ticks of a neutral throw connecting; both separate 120 cm and recover for 20 ticks. A press made before the throw connected does not count. Combo throws cannot be escaped. |
| Dodge | toward = forward roll, otherwise back roll | Strike-invulnerable frames 4-15 (forward) or 3-12/13 (back); throwable on every frame. The forward roll passes through the opponent. A 14-tick lockout follows each dodge, and the recovery can be punished. |
| Corners | stage half-width 700 cm | Pushback a wall absorbs moves the attacker back instead. A throw that would hold or land a victim beyond the wall moves the thrower instead, keeping the authored spacing. |
| Separation | 560 cm | The camera edge acts as a wall for whoever is retreating. |
| Gauge | 0-1000 | Earned: hits 80% of damage dealt and 40% of damage taken; blocking +20 for the attacker and +30 for the defender; deflects +80. No gain while Spirit Enhanced Strikes is active. |
| Rounds | first to 2, 75 s | KO wins the round. On timeout the higher health percentage wins and equal health is a draw. A throw already in progress may finish its animation after time expires, but cannot deal damage after the timeout result. A double KO is a draw. A draw round awards no win. At most 5 rounds; if wins are still level after that, the match is drawn. |
| Jump | up | Up from neutral (or a crouch) jumps straight up, toward or away by the direction held (a held Block comes first). 4 squat ticks on the floor (throwable, hit as standing), 34 ticks in the air on a 115 cm arc covering 150 cm toward or 122 cm away, then 4 ticks of landing recovery (5 after a jump attack). No air control. In the air a fighter cannot block or be thrown, and any hit knocks it down; it falls to the floor. Pushboxes still apply, so a jump cannot pass over the opponent. |
| Jump attacks | Light / Heavy in the air | Each fighter has a light and a heavy jump attack (startup 6 / 8 from the press); landing ends them, and one jump allows one attack. A buffered press in the squat comes out once airborne. **Coming down they are overheads, going up mids.** Their hit- and blockstun count from contact, so their worth depends on how deep they land: a jump-in that hits in the last few frames before landing combos into Light, the low or the uppercut, and one blocked that deep keeps the turn; one that connects high gives it away. A held standing guard blocks them; a crouching guard does not stop the overhead; a deflect works on them like on any blockable hit. Anti-air strikes, above all the uppercut, knock jumpers down. |
| Rematch / reset | full | A rematch builds a fresh simulation; Training reset rebuilds both fighters (gauge kept). |

## Character kits

Shared structure: each fighter has a Light string, Heavy, toward + Heavy, a low (down + Light), an uppercut (down +
Heavy), three specials (neutral, toward, away), a light and a heavy jump attack, two dodges and one throw. Ashka also
has two away moves (away + Light, away + Heavy) for the front kick and spinning elbow of her character sheet. The
fighters do not share animations or tuning.

**Wren Ku** is an all-rounder with kicking reach and spinning and flying techniques. Her Light string
is jab, cross, spinning back elbow. Heavy is a long roundhouse kick; toward + Heavy is an advancing spinning back kick.
Her specials:
- **720 Hook Kick** (neutral). The signature technique, deliberately slow: startup 35 and airborne from frame 11. It can
  be read and answered, since hitting her in the air knocks her down. It has big reach and damage, and it is heavily punishable on block (see the table).
- **Tornado Kick** (toward). Travels and ends Light strings.
- **Spirit Enhanced Strikes** (away). Spends a full gauge. The golden lightning aura lasts 8 s (480 ticks), raises
  strike damage to 120% and halves the damage of energy (flame) attacks. It cannot stack, gauge does not build while it
  is active, and it is lost if she is hit before it applies on frame 24.

Her low is a low kick to the shin from the crouch; her uppercut a rising rear uppercut from the crouch. Her throw is
the **double-leg takedown**: a level change and penetration step on the grab's active frames, a drive through and a
finish to the mat, and she is back on her feet before the throw ends; from Light or Light, Light on hit it is her combo
throw (up to 70 cm away). The shoulder throw (data id `wren_suplex`) is kept for the dormant grappling set.

**Ashka Rook** is a composed Muay Thai specialist who controls space with teeps and front kicks and wins up close
with elbows and knees. Her Light string is jab, stepping horizontal elbow, step-in knee. Heavy is a roundhouse to the
body (the hips turn over and the shin lands level); toward + Heavy is a long teep with large pushback. Away + Light is
a quick lead-leg front kick (a snap kick to the body, unlike the teep's push), which cancels into a special on hit;
away + Heavy is a spinning elbow (sok klap) at head height, which a crouch ducks and which knocks down on a counter
hit; from Light, Light (the elbow) on hit it is a combo ender. Her Lamplighter Flame variations:
- **Flame Elbow** (neutral). A leaping downward elbow wreathed in crimson flame.
- **Flying Knee** (toward). Ends strings.
- **Flame Burst** (away). Spends half a gauge. Invulnerable through frame 10, so it works as a reversal, but it is
  heavily punishable on block.
Her flame attacks deal energy damage, which is what Spirit Enhanced Strikes defends against. Her low is a low teep to
the lead shin; her uppercut a rising elbow (sok ngat). Her throw is the **clinch trip**: she locks the plum, breaks the
posture, steers the head round on her planted rear foot and sweeps the loaded ankle with her lead foot; the opponent
lands on the back in front of her. From Light, Light on hit it is her combo throw (the elbow brings her close; up to 45
cm). Clinch knees and the clinch turn are kept for the dormant grappling set.

Verified example combos (`Tests/Core`, `example_combos_each_fighter`, `combo_throws_scale_cannot_be_escaped_and_need_a_hit`,
`deep_jump_in_links_into_ground_offense`, `ashka_front_kick_and_spinning_elbow`): Light, Light, Light; Light, Light
into toward + Special; Light into toward + Special; **Light, Light into Throw** (and Light into Throw); and a deep
jump-in into Light, the low or the uppercut, for both fighters. Ashka also has Light, Light into away + Heavy (the
spinning elbow, 3 hits) and away + Light into Special (front kick, Flame Elbow, 2 hits). True strike-to-throw routes, reproducible in Training against the standing partner from the reset
position after walking in:
- **Wren:** Light (jab) on hit, then Throw while it hits (8-19 frames into the jab) → 30 + 110 = 140 damage, 2 hits.
  Light, Light, Throw → 30 + 36 + 88 = 154, 3 hits (the takedown scaled to 80 %).
- **Ashka:** Light, Light (jab, elbow) on hit, then Throw → 28 + 40 + 80 = 148, 3 hits. Light, Throw also combos when
  the jab lands close (the clinch needs 45 cm or less).
Pressure, not combos: a blocked light leaves the opponent in blockstun, which a throw cannot catch; walking in and
throwing after it is a read the opponent can beat with a jump, a roll, a strike or an escape.

<!-- move-tables:begin -->

### Wren Ku

Health 1000; walk 2.8 cm/frame forward, 2.4 back; pushbox half-width 24 cm; standing hurtbox [-26, 0, 26, 178] cm; crouching hurtbox [-30, 0, 34, 110] cm.

| Input | Move | Level | Startup | Active | Recovery | Reach (cm) | Damage | On block | On hit | Cancels | Gauge | Notes / counterplay | Anim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Light | Jab | high | 8 | 2 | 11 | 83 | 30 | +1 | +5 | L2, @special on hit/block; T on hit (8-19) | - | Fast high check. Into Cross, a special, or the throw on hit. | `L1` |
| Light, Light | Cross | high | 9 | 2 | 14 | 96 | 36 | -1 | +4 | L3, @special on hit/block; T on hit (9-21) | - | Second hit (high). Into the elbow, a special, or the takedown. | `L2` |
| Light x3 | Spinning Back Elbow | high | 9 | 3 | 19 | 109 | 52 | -7 | +1 | - | - | String ender. Pushes back; punishable up close on block. | `L3` |
| Heavy | Roundhouse Kick | high | 16 | 3 | 29 | 152 | 88 | -6 | +2 (KD on counter) | @special on hit (16-27) | - | Long high kick (ducked by a crouch). Special-cancel on hit. | `H` |
| toward + Heavy | Spinning Back Kick | mid | 21 | 3 | 24 | 189 | 100 | -5 | +3 (KD on counter) | - | - | Advancing spin with big pushback; safe at tip range. | `FH` |
| down + Light | Low Kick | low | 7 | 2 | 14 | 102 | 26 | -4 | +3 | - | - | Low: block it crouching. A quick poke from the crouch. | `CL` |
| down + Heavy | Rising Uppercut | mid | 10 | 4 | 39 | 74 | 120 | -26 | launch, knockdown | - | - | Anti-air: rises under jump-ins and launches. Risky if blocked. | `U` |
| Special | 720 Hook Kick | high | 35 | 3 | 41 | 231 | 165 (chip 16) | -14 | knockdown | - | - | Signature. Slow, airborne, devastating; punishable if blocked. | `S` |
| toward + Special | Tornado Kick | overhead | 17 | 3 | 33 | 206 | 105 (chip 10) | -10 | knockdown | - | - | Travelling jump kick: an overhead. Ends strings; knocks down. | `FS` |
| away + Special | Spirit Enhanced Strikes | - | applies 24 | - | 44 | - | - | - | - | - | 1000 | Full gauge: more strike damage, half damage from flame for 8 s. | `BS` |
| In a jump: Light | Jumping Punch | overhead (mid rising) | 6 | 6 | until landing | 66 | 40 | blockstun 14 from contact | hitstun 18 from contact | - | - | Overhead coming down: beats a crouching guard. Deep, it combos. | `JL` |
| In a jump: Heavy | Flying Kick | overhead (mid rising) | 8 | 7 | until landing | 96 | 60 | blockstun 16 from contact | hitstun 22 from contact | - | - | Flying kick. Overhead coming down; deep, it leads into a combo. | `JH` |
| Throw | Double-Leg Takedown | throw | 5 | 2 | 27 | grab 26, combo 70 | 110 (scaled in a combo) | - | throw | - | - | Beats any guard up close. After a hit it can't be escaped. | `T` |
| toward + Dodge | Forward Roll | - | invuln 4-15 | - | 15 | - | - | - | - | - | - | Rolls through strikes and past the opponent. | `DF` |
| Dodge (away/neutral) | Back Roll | - | invuln 3-13 | - | 19 | - | - | - | - | - | - | Retreating roll. Recovery is punishable. | `DB` |

| Throw | In play | Duration | Damage frame | Damage | Lands | Victim knockdown | Anims |
|---|---|---|---|---|---|---|---|
| Double-Leg Takedown | yes | 74 | 34 | 110 | 120 cm in front | 34 | `ThrowF` / `Victim_WrenThrowF` |
| Shoulder Throw | grappling only (off) | 72 | 48 | 120 | 110 cm behind (side switch) | 36 | `ThrowB` / `Victim_WrenThrowB` |

### Ashka Rook

Health 1000; walk 2.6 cm/frame forward, 2.3 back; pushbox half-width 22 cm; standing hurtbox [-24, 0, 24, 170] cm; crouching hurtbox [-28, 0, 32, 105] cm.

| Input | Move | Level | Startup | Active | Recovery | Reach (cm) | Damage | On block | On hit | Cancels | Gauge | Notes / counterplay | Anim |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Light | Jab | high | 8 | 2 | 15 | 77 | 28 | +2 | +6 | L2, @special on hit/block; T on hit (8-22) | - | Fast high jab. Into the elbow, a special, or the throw on hit. | `L1` |
| Light, Light | Horizontal Elbow | high | 9 | 2 | 20 | 99 | 40 | +2 | +6 | L3, @special on hit/block; T, BH on hit (9-26) | - | Stepping elbow (high). Into the knee or a special; on hit the clinch trip or the spinning elbow. | `L2` |
| Light x3 | Step-In Knee | mid | 8 | 3 | 17 | 97 | 54 | -5 | +3 | - | - | Driving knee. String ender. | `L3` |
| Heavy | Body Roundhouse | mid | 16 | 3 | 27 | 138 | 84 | -6 | +3 (KD on counter) | @special on hit (16-27) | - | Muay Thai roundhouse to the body. Special-cancel on hit. | `H` |
| toward + Heavy | Teep | mid | 16 | 3 | 19 | 152 | 60 | -3 | +1 (KD on counter) | - | - | Teep. Long reach, huge pushback; controls space. | `FH` |
| away + Light | Front Kick | mid | 10 | 2 | 15 | 131 | 38 | -3 | +4 | @special on hit (10-21) | - | Quick snap kick to the body. Keeps people off; into a special on hit. | `BL` |
| away + Heavy | Spinning Elbow | high | 14 | 3 | 24 | 118 | 92 | -9 | +0 (KD on counter) | - | - | Spinning elbow to the head. Ducked by a crouch; Light, Light into it on hit. | `BH` |
| down + Light | Low Teep | low | 8 | 2 | 15 | 110 | 30 | -4 | +2 | - | - | Low: block it crouching. Pushes the opponent away. | `CL` |
| down + Heavy | Rising Elbow | mid | 9 | 4 | 36 | 62 | 110 | -23 | launch, knockdown | - | - | Anti-air: rises under jump-ins and launches. Risky if blocked. | `U` |
| Special | Flame Elbow | overhead | 12 | 3 | 25 | 149 | 115 (chip 12) | -11 | knockdown | - | - | Leaping flame elbow: an overhead. Knocks down. | `S` |
| toward + Special | Flying Knee | mid | 22 | 3 | 26 | 207 | 120 (chip 12) | -11 | knockdown | - | - | Flying knee with flame. Ends light strings; knocks down. | `FS` |
| away + Special | Flame Burst | mid | 7 | 4 | 39 | 125 | 115 (chip 12) | -28 | knockdown | - | 500 | Half gauge: invulnerable flame burst. Heavily punishable if blocked. | `BS` |
| In a jump: Light | Jumping Elbow | overhead (mid rising) | 6 | 6 | until landing | 60 | 42 | blockstun 14 from contact | hitstun 18 from contact | - | - | Elbow coming down: an overhead. Deep, it combos on landing. | `JL` |
| In a jump: Heavy | Jumping Knee | overhead (mid rising) | 8 | 7 | until landing | 70 | 62 | blockstun 16 from contact | hitstun 22 from contact | - | - | Jumping knee. Overhead coming down; deep, it leads into a combo. | `JH` |
| Throw | Clinch Trip | throw | 5 | 2 | 26 | grab 30, combo 45 | 100 (scaled in a combo) | - | throw | - | - | Beats any guard up close. After a hit it can't be escaped. | `T` |
| toward + Dodge | Forward Roll | - | invuln 4-15 | - | 15 | - | - | - | - | - | - | Rolls through strikes and past the opponent. | `DF` |
| Dodge (away/neutral) | Back Roll | - | invuln 3-12 | - | 18 | - | - | - | - | - | - | Quick retreating roll. Recovery is punishable. | `DB` |

| Throw | In play | Duration | Damage frame | Damage | Lands | Victim knockdown | Anims |
|---|---|---|---|---|---|---|---|
| Clinch Trip | yes | 62 | 46 | 100 | 100 cm in front | 34 | `ThrowC` / `Victim_AshkaThrowC` |
| Clinch Knees | grappling only (off) | 74 | 54 | 115 | 115 cm in front | 34 | `ThrowF` / `Victim_AshkaThrowF` |
| Clinch Turn Trip | grappling only (off) | 66 | 48 | 105 | 105 cm behind (side switch) | 36 | `ThrowB` / `Victim_AshkaThrowB` |

<!-- move-tables:end -->

## Canon boundaries

- **Confirmed canon** (from the character sheets):
  - **Wren:** name, alias, height and build, two braids, eye colour, her black and ocean-blue motif, MMA and Look See
    Do, and her listed techniques, including the 720 Hook Kick. Spirit Enhanced Strikes is a golden lightning aura that
    raises strike damage and defence against energy and magical attacks.
  - **Ashka** (her character sheet, version 2 of 2026-11-09, which replaces the earlier ones): Ashka Rook, The Last
    Lamplighter; a former Muay Thai fighter and Lamplighter; 5'7" (170 cm), lean, slender and athletic. Long, silky
    crimson hair with subtle waves toward the ends, in a loosely gathered ponytail secured with a small black ribbon
    or an elegant clasp; soft, slightly parted bangs just past her eyebrows and two longer strands framing her face.
    A heart-shaped face, deep crimson almond-shaped eyes with long dark lashes, fine brows, full lips and a gentle,
    calm smile. A Gothic-Victorian ensemble: a jet-black frock coat (fitted waist, structured shoulders, high
    standing collar, split coattails just above the knee, black-on-black floral embroidery, subtle crimson piping,
    silver buttons, ice-white detail at the inner cuffs and collar, crimson lining); an ice-white high-collared
    blouse with pleats down the chest and lace at the cuffs; a jet-black brocade waistcoat with silver buttons; a
    crimson silk cravat with a small dark-silver clasp; high-waisted black trousers with crimson stitching down the
    outer seams; polished black Victorian ankle boots with low heels and crimson accents; optionally a slender silver
    chain and a small crimson gemstone brooch. When she channels her flame, it briefly lights the coat's lining.
    Muay Thai and Lamplighter Flame Style; her signature techniques are Lamplighter Flame variations, spinning
    elbows, the flying knee, the teep, the front kick and clinch trips. Her Lamplighter Flame is crimson, and she
    describes it as purifying. No longer canon: the earliest sheet's trench coat, braid and chest tattoo, and version
    1's white shirt, black tie, black pants and brown loafers.
  - **Relationship:** Wren and Ashka are best friends.
- **Gameplay proposals, not canon:**
  - all frame data and damage
  - the gauge and its labels (SPIRIT, FLAME)
  - the 8 s aura duration and its multipliers
  - Flame Burst's invulnerability and gauge cost
  - which techniques sit on which buttons, and which Lamplighter Flame variations exist (Flame Elbow, the flying
    knee's flame, Flame Burst)
  - throw choices
  - the CPU's behaviour
  - how Ashka's look reads the sheet where it leaves a choice: the ribbon (a small bow) rather than the clasp, both
    the chain and the brooch shown, the embroidery's motif (a trailing vine with leaves and small flowers), and how
    brightly the flame lights the lining
  - Wren's and Ashka's fighting each other as a versus/sparring setup, which carries no story meaning
- **Deliberately unresolved:**
  - the origins and rules of Look See Do and the Fighting Spirit of Humanity
  - the full properties of the Lamplighter Flame, including any mechanical "purifying" effect (none is implemented)
  - Ashka's background and origin (unknown in her sheet), and anything her sheet leaves open
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
  - Optional hit reaction keys: a hit's `react` names the clip its defender plays in hitstun (`Hit<...>`, for
    example `HitHookR`, a hook landing on the defender's right side, or `HitBody`, a body shot that folds it), in place
    of `HitLight` / `HitHeavy`. Facing left mirrors a fighter, so a strike from the attacker's right lands on the
    defender's right. A reaction plays on the defender, so every fighter needs every reaction any fighter's hits
    name (`build_mocap` refuses to build otherwise). It opens on its impact pose, held through the hitstop. A missing
    clip falls back to `HitLight` / `HitHeavy` and is listed as missing. Presentation only.
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
