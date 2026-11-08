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
- **High/low mixups and crouching.** Deferred. Jumping and jump attacks are in the current slice; a held guard does not stop a jump-in, while a timed deflect or anti-air strike answers it. Grappling is retained in code and data but switched off in the shipped rules.
- **Kameos, finishers and extra fighters (MK1).** Rejected: they would widen the requested cast and scope.
- **An adaptive score.** Deferred: the slice uses event stingers only.

## Martial-arts motion notes

- **Wren's 720 Hook Kick.** Real 720 kicks count the take-off step in the rotation. The animation turns a full 720°: a
  step-turn, a jumping spin with the heel hook landing at about 540° (frame 26, the move's first active frame), then a
  spin-out to the landing.
- **Ashka's Muay Thai.** She keeps a tall, square guard and a rhythmic idle. Her teep (push kick) and body kick make
  contact with the ball of the foot and the shin respectively. Clinch knees and the clinch trip are her grabs.

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
