# Design research

The combat rules in this slice came from a short study of Killer Instinct (2013), Mortal Kombat 11 and 1, Street
Fighter 6 and Sekiro, made on 2026-11-02 before the rules were written. Other fighters (KOF XV, Granblue Fantasy Versus
Rising, Guilty Gear Strive) were checked where they settle a specific question. Each rule below names its source, what
Ebony Hearts does with it, and the core test that checks it (`Tests/Core/CoreTests.cpp`).

Confidence tags:
- **[P]** Official notes or a developer statement.
- **[S]** A specialist source that was read in full.
- **[X]** A specialist wiki that blocked direct reading; the value comes from a search excerpt and should be re-checked.
- **[C]** A community or press claim.

The numbers in the "Ebony Hearts" column are this game's own tuning. The creator played candidate `4cee9c1` on
2026-11-07 and reported that combat smoothness and jumping need refinement; the tuning remains provisional.

## Adopted

| Rule | Source and principle | Ebony Hearts | Alternative considered | Validation |
|---|---|---|---|---|
| Timed block | MK11 Flawless Block, with a lockout after an empty block [X]; Guilty Gear Strive Instant Block lockout [X]; Sekiro deflect, about 12 f and shrinking with spam [C]. A timed press on the existing block input rewards reading the opponent. Spam penalties keep it from being free. | A fresh Block press 0-3 ticks before contact deflects: 4 fewer blockstun ticks, no chip and extra gauge. Any press that does not deflect locks deflects out for 12 ticks. Holding Block stops ground strikes; a jump attack requires a timed deflect under the shipped rules. | SF6 Perfect Parry on its own input; no timed block | `timed_block_and_mash_lockout` |
| Capped deflect payoff | SF6 Perfect Parry pairs a 2-frame window with punishes scaled to 50% [P]/[X]. A timed defence should not decide rounds by itself. | The deflect pays out in frames and gauge only, with no counterattack, freeze or automatic punish. | MK11's meter-cost Flawless Block attack | `timed_block_and_mash_lockout`, `block_advantage_matches_frame_formula` |
| Strike beats throw; throw escape | SF6: a strike beats a throw on the same frame, and the escape window lasts 9 frames including the connect frame [X], confirmed by a measured community test [S]. | The strike wins on the same tick. The Grab escape window is 9 ticks. A press made before the grab connected does not count. Simultaneous grabs break apart. | MK's direction-guess tech (only one Grab button here) | `throw_tech_window`, `simultaneous_throws_tech_and_strike_beats_throw` |
| Tech while holding Block | MK11 and MK1 forbid a throw tech while blocking [X]. With six buttons that skill test costs more than it adds. | Grab can be pressed while holding Block. Inside the window it escapes; outside it is a real grab attempt that can whiff and be punished. | The MK rule (release Block first) | `throw_tech_window` |
| No throw loops | SF6 limits throw loops through knockdown spacing [X]; KOF XV gives throw protection after blockstun [S]. | 6 ticks of grab invulnerability after waking and 4 after hitstun or blockstun. A corner throw moves the thrower, not the victim, to keep the authored spacing. | Allowing corner loops | `corner_throw_release_and_pushback_transfer`, `no_infinite_or_unbounded_combo_search` |
| Punish and counter hit | SF6 Punish Counter, +4 frames and +20% damage [X]; a counter hit adds +2 [C]. A named, visible bonus teaches whiff punishing. | Counter hit (move in startup or active frames): +2 hitstun and x1.10 damage. Punish (recovery, whiffed grab, dodge recovery): +4 and x1.20. Both are called out on screen. | Raw frame data with no bonus | `damage_scaling_and_counter_hit` |
| Dodge beats strikes, grab beats dodge | KOF XV roll: invulnerable to strikes but throwable, with vulnerable recovery [S]. GBVS Rising evade cannot be teched when thrown [X]. Smash Ultimate stales repeated dodges [S]. | Strike-invulnerable frames 4-15 (forward) or 3-12/13 (back), grabbable on every frame, punishable recovery, and a 14-tick lockout instead of staling. | Backdash only (SF6) | `dodge_invulnerability_recovery_and_lockout` |
| Rolling through the opponent | The research deferred it because rolling through confuses "back" for hold-back blocking. | Adopted: Block is a dedicated button here, so a side switch cannot change what blocks. Directions are judged when the button is pressed. | No cross-through roll | `cross_up_direction_uses_side_at_press` |
| Short, confirmable routes | KI auto-doubles continue only on hit, and its enders choose the outcome [S]. KI's knockdown meter is a hard cap on combo length [S]. | Reduced form: Light 1 > 2 > 3 chain on hit or block, Light into a special on hit or block, and Heavy into a special on hit only. Combo scaling and hitstun decay replace KI's meter as the cap. A randomized search finds no route longer than 5 hits. | Full KI combo grammar with breakers (deferred) | `example_combos_each_fighter`, `no_infinite_or_unbounded_combo_search` |
| Input buffer | KI patch 3.0 put a 5-frame buffer on every character [S]. Buffers forgive human timing without auto-repeat. | 6 ticks, paused during the presser's own hitstop. Holding a button never repeats it. | Strict links (1-frame manuals) | `buffer_window_bounds`, `buffered_press_during_hitstop_chains`, `held_button_does_not_repeat` |
| Readable floor line | MK1's Floyd's Field grass hid fighters below the knee and was criticised for it [C]. Kicks, teeps and rolls are read at shin height. | The chapel's fighting strip is kept clear of foreground props, the water is a thin sheen, and effects stay off the feet. | Stage hazards and interactables (deferred) | Visual review of packaged screenshots and footage (see `Docs/Validation.md`) |
| Fixed-rate simulation | Common practice for fighting games; the earlier Ebony Hearts prototype also used a 60 Hz core. | 60 Hz integer simulation, at most 4 catch-up ticks per frame, and animation sampled from simulation frames. | Variable-step simulation | `replay_determinism_and_render_rate_independence` |

## Sekiro's timed block in a 1v1 fighter

Sekiro's deflect works because enemy strings are authored, learnable and do not adapt to the player. In a symmetrical
fighter the attacker can delay and feint, so a timed block becomes a read rather than a reaction. It transfers safely
only in a bounded form: a small window, a lockout against mashing, a payoff in frames only, and ordinary held blocking
still working. Sekiro's posture break and its unblockable "perilous" attacks do not transfer. The game has a jump,
but no crouch or low attack; an unblockable designed to defeat jump would leave Dodge as the only answer.

## Rejected or deferred

- **KI combo breakers and white life.** Deferred: they need their own reading UI and teaching, and short routes already
  limit damage.
- **The SF6 Drive system.** Rejected for this slice, as the brief requires.
- **Sekiro posture and Deathblow.** Rejected: a guard-break meter rewards turtling in symmetrical play.
- **High/low mixups and crouching.** Deferred in the first slice; adopted in the 2026-11-08 combat pass (below).
- **Sustained grappling (clinch control, ground positions, submissions, grab minigames).** Rejected for the slice. The
  directional throw variants and clinch knees stay in the data and code behind `"grappling": false`; the standalone
  throws (below) use one throw per fighter.
- **Kameos, finishers and extra fighters (MK1).** Rejected: they would widen the requested cast and scope.
- **An adaptive score.** Deferred: the slice uses event stingers only.

## Combat pass, 2026-11-08: crouch, throws, uppercuts and jumps

The owner's 2026-11-08 directive asked for crouching, standalone combo-compatible throws, a rising uppercut and jumps
inspired by Mortal Kombat. Mortal Kombat 11 was chosen as the one reference entry. What was observed in it comes from the
SuperCombo wiki pages *Mortal Kombat 11/Movement*, */Offense*, */Defense* and */Attack Attributes* (read in full
2026-11-08 [S]); no MK frame counts were found that could be checked, so none are claimed.

| Question | Observed in MK11 [S] | Ebony Hearts | Why | Validation |
|---|---|---|---|---|
| What crouching does | After a couple of frames of animation the crouch lowers the hurtbox; many highs (and MK's throws) whiff on it. | Down lowers the posture one step a frame over 3 frames, blending the hurtbox to a crouching box (Wren 110 cm, Ashka 105 cm tall). No crouch walking. Highs pass over by geometry. | A reaction-speed duck that matches what is drawn; no new movement mode. | `crouch_posture_entry_exit_both_sides`, `hit_levels_agree_with_the_crouching_hurtboxes` |
| Guard heights | Lows must be blocked crouching, overheads standing. Holding block blocks either side (no cross-up guard). | Standing guard: high, mid, overhead. Crouching guard (down + Block): low, mid. Every hit names its level and the boxes agree with it. | The smallest set that makes the posture a decision: crouching ducks highs and blocks lows, but loses to overheads and throws. | `guard_heights_lows_overheads_and_jump_ins` |
| Lows and overheads | Pokes such as D1/D3/D4 are lows; jump attacks overheads. | One low per fighter (down + Light: Wren's low kick, Ashka's low teep), +2/+3 on hit and -4 on block. Overheads: falling jump attacks, Wren's tornado kick, Ashka's flame elbow. | Without a low a crouching guard would beat everything on the ground. | same |
| Jump attacks | Rising jump attacks hit mid, falling ones overhead. Jump-ins combo into a string when the string is buffered at once. Players cannot block in the air. | The same rising/falling rule. The jump-in's stun counts from contact, so a deep jump-in leads into Light, the low or the uppercut and a high one does not; the former landing-relative stun and the "held Block cannot stop a jump attack" rule are removed (the loader rejects their fields). | Replaces the unusual 2026-11-07 rule, which made blocking meaningless against jumps once crouching existed; the reward now depends on how deep the jump-in lands. | `jump_in_reward_depends_on_height`, `deep_jump_in_links_into_ground_offense`, `jump_ins_cannot_loop` |
| Jump arc | Tall, quick, committed jumps; forward jumps cover real distance. | 4 squat frames, 34 in the air, 115 cm high, 150 cm forward and 122 cm back (was 36 frames and 90 cm): about 40 % more gravity, so no hanging at the apex. No air control; one attack per jump. | "Decisive, not floaty"; a shorter jump keeps the uppercut a reaction rather than a guess, at the cost of a slightly tighter anti-air window. | `jump_arc_landing_and_directions`, `cpu_anti_airs_jump_ins` |
| Rotation in the air | MK forward jumps are flips for many characters; neutral jumps are upright. | Evaluated and not adopted: both fighters jump upright with a tuck (Wren springier, Ashka compact). A jump attack can start on any airborne frame, and blending from a half-turned flip into an upright strike would spin the body through the transition; the camera-side silhouette also reads better upright at this distance. | Keeps every jump attack's start continuous; the fighters still differ in posture. | `audit_clips.py` (no pops or flips in the jump and jump-attack clips) |
| Passing over the opponent | MK jumps can land on the other side; with block a button, cross-ups do not change how to guard. | Kept out: pushboxes still apply in the air. | No left/right guard exists to mix up, and a body clearing a 178 cm opponent would need a jump far above the slice's grounded realism. Rolls already pass through. | `one_attack_per_jump`, `jump_attacks_hit_block_and_land_into_recovery` |
| The uppercut | Every character's D2 is the universal anti-air and punish, launches, and is badly punishable. | Down + Heavy: Wren's rising rear uppercut (startup 10), Ashka's rising elbow (sok ngat, startup 9). A crouching wind-up (highs pass over it), a tall mid hitbox, a launch into the knockdown (no juggles), -26 / -23 on block. No invulnerability. | MK's role without its juggle system; the crouching wind-up is visible and is what wins anti-air trades. | `uppercut_anti_air_launch_and_risk` |
| Throws | Throws are highs (crouching ducks them) and are escaped by a button shortly after the first hit; they cannot be escaped while blocking; command throws do not land in hitstun. | One throw per fighter on its own button. Throws catch crouching fighters too (unlike MK11), so a crouching guard has an answer up close. Neutral throws are escaped with Throw within 9 frames; a throw cancelled from a light that hit (a combo throw) catches the reeling opponent, counts as the next hit (scaling, gauge once), and cannot be escaped. | The owner asked for combo-compatible throws; making only hit-confirmed cancels eligible keeps every blocked jab from becoming a guaranteed throw. | `standalone_throws_without_grappling`, `combo_throws_scale_cannot_be_escaped_and_need_a_hit`, `throw_entry_closes_the_gap_without_teleporting`, `throw_and_uppercut_loops_are_bounded` |
| CPU escapes | — | The CPU notices a grab after its difficulty's delay (3-9 frames on Hard, up to 15 on Easy) and may miss the 9-frame window; presses queued before the grab are dropped. | The dormant queue issue PR1-06 noted: a stale press could fire into or after the throw. | `cpu_throw_escape_uses_reaction_and_no_stale_press` |

**Wren's double-leg takedown.** MMA double-leg: level change (hips drop, back straight, head up), penetration step
with the lead knee driving forward, hands behind both knees, head tight to the side, then drive through and finish.
The grab (the shot) now carries the level change and the penetration step on its active frames; the captured Mixamo
pair (Double Leg Takedown attacker/victim) supplies the drive and the fall, retimed so she is back on her feet by
about frame 60 of 74 and never holds a ground position.

**Ashka's clinch trip.** From Nong-O Gaiyanghadao's clinch sweep (Evolve University, "Nong-O Gaiyanghadao Teaches How
To Sweep From The Clinch", read 2026-11-08 [S]): control the head and shoulders, push one side and pull the other while
turning the upper body toward the pulling side, and sweep the support foot low at the ankle as the hips turn. In the
game she locks the plum, breaks the posture by pulling the head down, steers it to her right on her planted rear foot,
and sweeps the loaded lead ankle with the inside of her lead foot; the opponent lands on the back in front of her and
she squares up. No side switch, no knees from the clinch, and no clinch state: the clinch exists only inside the throw.
The Evolve "knee bump dump" (single-collar tie, inside trip, swing) was the second reference considered.

## Martial-arts motion notes

- **Wren's 720 Hook Kick.** Real 720 kicks count the take-off step in the rotation. The animation turns a full 720°: a
  step-turn, a jumping spin with the heel hook landing at about 540° (frame 26, the move's first active frame), then a
  spin-out to the landing.
- **Ashka's Muay Thai.** She keeps a tall, square guard and a rhythmic idle. Her teep (push kick) and body kick make
  contact with the ball of the foot and the shin respectively. Her throw is the clinch trip (above); her uppercut is the
  rising elbow (sok ngat) and her low is a teep to the lead shin.
- **Ashka's front kick and spinning elbow (2026-11-09).** Her character sheet lists both beside the teep. In Muay Thai
  the teep is a push: the knee chambers and the sole drives straight through to move the opponent away. The front kick
  is kept distinct as a snap: the lead knee lifts and the ball of the foot snaps up into the body and comes straight
  back, quicker and shorter than the teep. The spinning elbow is sok klap (the spinning back elbow): the
  lead foot steps across, the back turns through, and the rear elbow slashes round horizontally at head height, the
  other hand guarding the face. Both are keyed by script on her stance (no capture was available for them).

## Fighting stances

The creator asked for a simple traditional MMA stance with a little bounce, like Jon Jones's, for Wren, and a
traditional Muay Thai stance for Ashka. Coaching articles and fight analysis gave the following. The values live in
`Tools/Blender/anim/stances.json`, written for a 1.75 m body and scaled to each fighter. Both fighters stand orthodox.

**Wren: MMA**
- **Feet.** Wider than a boxing stance, so she can sprawl or shoot without stepping first. The lead toes point at the
  opponent and the rear foot turns about 45° out, with the rear heel slightly up.
- **Body.** Weight close to even, knees bent 25–30°, hips about 9 cm lower than standing. The hips turn about 28° and
  the chest about 35° (bladed), with the torso tipped 8° forward.
- **Hands.** The lead hand reaches about 45 cm out in front of her chin, at chin height, with a soft elbow, measuring
  range as Jones does. The rear fist sits at the jaw with the elbow tucked down over the ribs.
- **Bounce.** No source measures Jones's bounce, so she gets a small, grounded spring: 2–3 cm at the hips, about
  1.8 bounces a second. It is not a boxer's hop.

**Ashka: Muay Thai**
- **Body.** Tall and nearly square to the opponent, hips forward and under the shoulders. Hips turn about 12°, the
  chest about 10°.
- **Feet.** About shoulder width with a short stagger, rear foot 45° out. Weight biased to the back foot (about
  40/60), rear heel up, lead foot light.
- **Hands.** High guard: gloves in front of the face, up to the brow, palms facing each other. Elbows below the hands,
  in front of the chest and close to the body.
- **Rhythm.** A slow front-to-back rock, not a bounce: 2.5 cm of hip travel, with a small dip as each leg takes the
  weight. The lead heel lifts a few centimetres as she rocks back.

**Faults avoided:** feet on one line, locked legs or arms, flat feet, flared or raised elbows, the wrong discipline's
stance, everything moving at once (the head stays steadier than the hips), and sliding feet.

**How they are built.** Both idles start from ACCAD motion capture: a boxer's bounce for Wren and a ready stance for
Ashka. The capture's joint positions drive the rig, so the source skeleton's rest pose does not matter
(`Tools/Blender/anim/aim.py`). A stance layer then places the hips, chest, head, feet and hands on the values above
while keeping the captured motion around them (`apply_stance` in `Tools/Blender/anim/mocap.py`). Ashka's rock is added
on top. The hand targets come from her real shoulder positions in the stance, so the elbows hang below the shoulders.
