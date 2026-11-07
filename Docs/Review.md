# Review guide: creator playtest round (2026-11-07)

This guide is for reviewing `release/first-slice` (pull request #1) after the creator's playtest of candidate `060a75f`
on 2026-11-07. The creator asked for four changes, in this order: a natural spinning elbow for Wren and a proper
body-level roundhouse for Ashka; jumping with a clear purpose that fits the other mechanics; grappling removed from the
playable game but kept for later; and the PlayStation controller and TV audio recorded as verified. Later the same
day they asked for the buttons Grab left unused to be repurposed. Nothing else was in scope: punches, Wren's kicks and the rolls are unchanged. The previous round (the start-up crash, EH-07) is
described in the [validation report](Validation.md), "Candidate `060a75f`"; rules and move data are in the
[combat contract](CombatContract.md).

**Candidate:** package built from commit `d2f7cb7` (Shipping, Linux), released as `EbonyHearts-Slice-d2f7cb7.tar.gz`,
SHA-256 `34555785c4db7f27016350914b177d4178ccfccaab6d522d2a03283be2b06044`. Commits after `d2f7cb7` change documentation
and a review script only. Results: Validation, "Current candidate".

## 1. What changed and where

| Request | Change | Where | Checked by |
|---|---|---|---|
| Wren's spinning elbow contorted | At contact her right fist was behind her head, so the arm wrapped round it and the elbow pointed up, the left hand hung behind her, the knees caved in and the rear foot tucked across. Re-keyed: right side to the opponent, upper arm pointing at them at head height, fist folded by the head, left hand guarding the face, head turning ahead of the body, knees over the feet, rear foot swinging round at hip width, and a recovery key so the elbow does not flip over the arm on the way back. Timing, hitbox and the hand-overs into and out of the move are unchanged (elbow 86 cm out, 139 cm up at the first active frame) | `Tools/Blender/anim/moves.py` (`wren_moves`, Light 3), `Content/Characters/Wren/Anims/A_Wren_L3` | per-frame joint positions, flip, speed, floor and hand-over checks (Validation); `review_playtest.txt` footage |
| Ashka's Body Kick was not a roundhouse | Rebuilt from Mixamo's Mma Medium Kick: the hips turn over and the shin lands level at about 1.05 m, inside the unchanged hitbox. The capture is kept at 85% with a faster retraction, so the follow-through does not tip the body over. The previous source (Roundhouse Kick With The Rear Foot) read as a straight front kick. Renamed "Body Roundhouse" | `Tools/Blender/anim/mocap_clips.json` (`ashka.H`), `Content/Characters/Ashka/Anims/A_Ashka_H`, `Content/Data/Fighters/ashka.json` (name only) | as above |
| Jumping had no purpose | A jump attack that connects with a grounded opponent keeps them in stun until the jumper has landed and recovered, plus 12 ticks on hit or 2 on block, however high it connected; a held Block does not stop it (a timed block does, and usually gives the defender the turn); one attack per jump. Strikes still knock any jumper down. The CPU jumps in more against a guard it has seen held, and now answers jump-ins: it notices a jump in two thirds of its reaction time (at the full delay the Normal CPU saw a jump-in only once its attack was out, and a player who did nothing but jump in beat it 24 matches out of 24), times its anti-air jab to the jumper's arrival, starts no poke while a jump comes at it, and may step back instead of holding a block | `Source/EbonyHearts/Core/EHMatch.cpp` (`ResolveCollisions`, `StartMove`, jump state), `EHCombatData.*`, `Content/Data/rules.json` (`jumpInHitAdvantage`, `jumpInBlockAdvantage`, `heldBlockStopsJumpIns`), `EHAI.*` | `jump_ins_have_landing_relative_advantage`, `jump_ins_beat_a_held_block_but_not_a_deflect`, `jump_in_hit_links_into_a_light`, `one_attack_per_jump`, `cpu_anti_airs_jump_ins`, `cpu_levels_play_legal_complete_matches` |
| Remove grappling, keep the work | `"grappling": false` in `rules.json`: no throw move can start. Grab is hidden from Controls, the move list, the results, the input log and the dummy options; Lesson steps 6 and 7 teach the jump-in and the anti-air instead; the CPU never grabs; texts no longer mention grappling. The grab move, throws, escapes, their code, data, animations and documentation stay, and the original texts and Lesson steps return when the switch is turned back on | `EHMatch.cpp` (`SelectMove`), `EHAI.cpp`, `EHDirectorFlow.cpp`, `EHDirectorUI.cpp`, `presentation.json` | `grappling_off_grab_does_nothing`, the throw tests (switched on locally), `cpu_levels...` (no grabs in 36 CPU matches), packaged controls and journey runs |
| Repurpose Grab's buttons (asked after the first candidate of this round) | Cross / A jumps and L1 / LB blocks; I, Numpad 5 and ; jump. Grab has no default button. Each action can hold three buttons (was two), so the right keyboard keeps Up, Numpad 5 and ; on Jump. Settings format 3: loading a version 1 or 2 file moves Grab's former default buttons to their new jobs where the slot is free, with a notice; a button the player gave Grab themselves stays | `EHSettings.*` (`Defaults`, `EHFormerGrabKey`, `Load`), `EHDirectorFlow.cpp` / `EHDirectorUI.cpp` (third slot), `EHAutomation.cpp` | `bindings_selftest` (new layout, third slot, a version-2 file), `input_selftest` (Cross jumps with the stick's direction, L1 blocks), `controls_remap` / `controls_persist`, simulated pads |
| Controller and TV audio | Recorded as verified by the creator | `Docs/Status.md` | the creator, 2026-11-07 |

Supporting changes: `Tools/Unreal/build_characters.py` can import just named clips (`EH_ANIM_NAMES`);
`Tools/Docs/move_tables.py` prints jump-in advantage from the rules and lists the grab as kept;
`Tests/Auto/review_playtest.txt` records the changed moves and jump-ins.

## 2. Check it yourself

- **Core.** `Tests/Core/run_core_tests.sh`: 43 cases, `889 checks, 0 failures`. Set `heldBlockStopsJumpIns` to `true`
  or `jumpInHitAdvantage` to `0` in `rules.json`, remove the `airAttackUsed` check in the jump state, or let the CPU see
  jumps only after its full reaction delay, and a new test fails.
- **Training.** Pause > Dummy > Block all. Jump toward the partner and press Heavy on the way down, then Light as you
  land: the jump-in hits through the held guard and the Light combos. Lesson steps 6 and 7 cover the same and the
  anti-air.
- **Grappling switch.** Set `"grappling": true` in the staged `Content/Data/rules.json` (it is a plain file in the
  package) to bring grabs, their Lesson steps and texts back.

## 3. Where to look closely

- **A held Block no longer stops jump attacks.** This is the one rule change beyond what was asked for by name: with
  grabs gone nothing else beat a held guard, and the creator asked for jumping to complement the other mechanics. Jumps
  are still visible for 40 ticks and lose to any strike and to a timed block. It is one data switch
  (`heldBlockStopsJumpIns`) if the creator prefers jump-ins to be blockable.
- **Grab has no default button now.** Switching grappling back on also needs Grab given buttons again (Controls lists
  its former defaults, kept in `EHFormerGrabKey`). The Controls list shows only the buttons an action has, so the third
  slot adds no clutter.
- **The CPU sees jumps sooner than other actions** (two thirds of its reaction time). Against a loop of nothing but
  jump-ins, Normal knocks 51% of them out of the air (18% before) and Hard 64%. The loop still beats Normal more often
  than not, as it already did before this round, because a landed jump-in combo is worth far more than a jab; Hard
  beats it. Simulated with `CpuController` (24 matches per level); the test keeps Normal at 35% or more and Hard at 55%.
- **Lesson step numbers** are shared by both variants (grab or jump steps 6 and 7), so the hint and goal code switches
  on the rule instead of shifting indices.

## 4. Open

- For the creator: play the changes (see [Status](Status.md)).
- Not verified: a person's feel for the new jump rule and animations; hardware other than the test machine.
- The animation sources (raw captures, `.blend` files) are outside the repository, unchanged from earlier rounds.

## 5. Commit structure

Seven commits on top of the previous head `22fa565`: combat rules and tests (`80e57fa`), game layer (`d3548d7`),
animation (`bb4823b`), documentation and move notes (`d1ede0e`), a stronger jump-in test (`37d6ab4`), the CPU's
anti-air (`b445999`) and the repurposed buttons (`d2f7cb7`), then documentation of the results. Earlier history is
unchanged; nothing has been merged, tagged or released.
