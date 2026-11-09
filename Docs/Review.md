# Review guide: combat, animation and character pass (2026-11-08)

This guide is for reviewing branch `dev/combat-pass-1108`, which carries the creator's 2026-11-08 combat, animation and
character requests on top of the PR #1 head. It is the implementer's account, not an independent review. Earlier rounds
follow below, unchanged, as history; the 2026-11-08 independent audit (previous round, section 6) applies to its own
candidate, not to this one.

| | |
|---|---|
| Branch | `dev/combat-pass-1108` (local task branch; see [Status](Status.md) for where it is pushed) |
| Base | `release/first-slice` at `ea3ddc655fdf10666ede89f14df201e43b25daad` (PR #1 head, also the merge base) |
| Candidate source | `5d5c316` (code, data and content of the packaged build); later commits change documentation and one test script (`Tests/Auto/virtual_pad.py`, not packaged) only |
| Package | `EbonyHearts-Slice-5d5c316.tar.gz`, Shipping, Linux; identity and checksums in [Validation](Validation.md), "Current candidate" |
| Not done | nothing merged, tagged or released; PR #1 and `release/first-slice` are untouched |

## 1. What changed and where

| Request | Change | Where | Checked by |
|---|---|---|---|
| Crouching | Hold down: the posture lowers over 3 ticks and the hurtbox blends from standing to crouching (Wren 110 cm, Ashka 105 cm), so highs pass over and the guard turns crouching half way down. No walking crouched; hitstun keeps the posture, a knockdown resets it. New clips: crouch, crouching guard, crouching hit and block reactions | `Core/EHMatch.*` (`UpdatePosture`, `PostureHurt`, `IsCrouching`), `EHCombatData.*` (`crouchHurt`, `crouchFrames`), fighter JSON | `crouch_posture_entry_exit_both_sides`, `hit_levels_agree_with_the_crouching_hurtboxes`, `guard_heights_lows_overheads_and_jump_ins`, `reset_clears_state`, `state_hash_covers_every_field` |
| Hit levels | Every hit is high, mid, low or overhead (required in data). Lows are blocked only crouching, overheads only standing; jump attacks are overheads coming down and mids going up. Each fighter gains a low (down + Light) | `EHCombatData.*` (`HitLevel`), `EHMatch.cpp` (`ApplyStrike`, `EffectiveLevel`), `wren.json`, `ashka.json` | the same tests; packaged `lesson` (crouching-guard step) |
| Uppercuts | Down + Heavy: Wren's Rising Uppercut, Ashka's Rising Elbow. Mid, close range, no invulnerability; a hit launches into the normal invulnerable knockdown (nothing follows it); blocked it leaves the user at -20 or worse; its low wind-up passes under highs | `EHMatch.cpp` (`SelectMove`, launch reaction 5), fighter JSON, `moves.py` (keyed clips) | `down_selects_the_uppercut_and_the_low`, `uppercut_anti_air_launch_and_risk`, `throw_and_uppercut_loops_are_bounded`, `cpu_anti_airs_jump_ins` |
| Throws without grappling | One standalone throw per fighter (Throw button): Wren's double-leg takedown, Ashka's Muay Thai clinch trip. `grappling` stays off; the older grab variants stay dormant. Neutral throws are escapable (9 ticks). The thrower closes the gap to the authored hold over 8 frames instead of snapping | `EHCombatData.*` (`throws`, `throwEntryFrames`, `throwId`), `EHMatch.cpp` (`ConnectThrow`, `AdvanceThrow`, `HoldVictim`), `throws.py`, `mocap_clips.json` | `standalone_throws_without_grappling`, `throw_entry_closes_the_gap_without_teleporting`, `corner_throw_release_and_pushback_transfer`, `timeout_throw_boundaries_both_sides`, `throw_ko_stays_down` |
| Combo throws | Light 1 or Light 2 cancels into the throw on hit only: the throw is the combo's next hit, scaled, counted, gauge paid once, and cannot be escaped. A blocked light cannot | `EHMatch.cpp` (`ComboThrowable`, `cancelIntoOnHit`), fighter JSON | `combo_throws_scale_cannot_be_escaped_and_need_a_hit`; route traces (section 2) |
| Jumps (MK-inspired) | Higher, longer and quicker: 115 cm arc (was 90), 34 air ticks (36), 150 cm toward / 122 cm away; landing 4 (5 after an attack). A jump-in's reward depends on how deep it lands; a deep one links into the string, the low or the uppercut. A **standing** guard now blocks jump-ins (they are overheads); a crouching guard does not. Jump-in loops stay impossible | `rules.json`, `EHMatch.cpp` (jump state, `ResolveCollisions`) | `jump_in_reward_depends_on_height`, `deep_jump_in_links_into_ground_offense`, `jump_ins_cannot_loop`, `jump_arc_landing_and_directions`; `review_jump` footage |
| CPU | Guards high or low by what is coming, uses lows, throws and combo throws, anti-airs with the uppercut on timing, escapes throws on a reaction delay (no stale press) | `Core/EHAI.*` | `cpu_anti_airs_jump_ins`, `cpu_throw_escape_uses_reaction_and_no_stale_press`, `cpu_levels_play_legal_complete_matches` |
| Controls | New actions Crouch (down) and Throw: S / Down arrow, U / Numpad 4 / M; D-pad down, left trigger. Settings format 4: an older file gains them where the buttons are free, with a notice. Input log shows down/up and T; move list "Down +" | `Game/EHSettings.*`, `EHInputRouter.cpp`, `EHDirectorFlow.cpp`, `EHDirectorUI.cpp`, `EHAutomation.cpp` | `controls_selftest` (107 + 43 checks), `controls_remap`, `controls_persist`, simulated pads |
| Lesson | Fourteen steps: movement, lights, heavy, block, crouching guard, deflect, jump-in, uppercut anti-air, throw, throw escape, combo throw, punish a blocked uppercut, specials | `EHDirectorFlow.cpp`, `EHGameDirector.h` | packaged `lesson` (`lesson_full.txt`, all 14 steps) |
| Animation audit | Every exported clip measured (fastest joint step, pops, held frames, elbow/knee flips, floor, seams) and listed with its runtime use and source; every flag has a written disposition. New clips cleared of pops and flips | `Tools/Blender/anim/audit_clips.py`, `Tools/Docs/anim_audit_table.py`, [AnimationAudit](AnimationAudit.md) | 155 clips, none unexplained; Unreal import sampled against the source (Validation) |
| Move relationships | Every source state x follow-up pair run through the combat core and tabulated | `Tools/Docs/move_matrix.cpp`, [MoveMatrix](MoveMatrix.md) | regenerated unchanged on the candidate |
| Wren's feet and materials | Layered ankle wraps (under-wrap, five bands, open heel and toes; no spike); scoop-neck top; fabric detail at the right scale (no lattice), with hems and seams | `Tools/Blender/characters/eh_wren.py`, `eh_paint.py`, `eh_specs.py`, `eh_tex.py` | renders before/after; in-game shots (Validation) |
| Ashka's overhaul | Tailored black coat hanging from the shoulders (notched lapels, collar, double-breasted buttons, belt, cuff straps, four-panel skirt); collared shirt and knotted tie; pressed trousers; loafers on a fitted last; layered bangs and braid flyaways; new brows. Blacks stay near-black (coat #101114) | `eh_ashka.py`, `eh_hair*.py`, `eh_garment.py`, `eh_mesh.py`, `characters.json` | as above; rig unchanged (every bone's rest position identical) |
| Unreal import | Coat, outfit and clothes use a two-sided master (`M_CharacterTwoSided`) for single-surface openings and hems | `Tools/Unreal/build_characters.py` | packaged build, art shots |

## 2. Check it yourself

- **Core.** `Tests/Core/run_core_tests.sh`: 52 cases, `1341 checks, 0 failures`.
- **Move matrix.** `Tools/Docs/move_matrix.sh` regenerates `Docs/MoveMatrix.md`; on this candidate it is unchanged.
- **Route traces.** The handoff folder (`review-handoff-20261108/routes`) has a combat-core program printing tick-by-tick
  traces with exact input schedules, each replayed from a fresh match to the same state hash: a combo throw for each
  fighter (Light at tick 0, Light at 14, Throw at 30 for Wren / 31 for Ashka, from 84 cm apart), a deep jump-in into
  the Light string (forward jump at tick 0, Heavy at tick 26, from 140 cm), the uppercut anti-air (down + Heavy at tick
  23 for Wren / 24 for Ashka against a forward jump with Heavy at tick 26), each fighter's low against a crouching
  and a standing guard, and the jump-in loop search against a crouching guard (longest true combo: 1 hit).
- **Training (packaged).** Training options (Esc) > Dummy: Crouch makes the partner crouch-block: lows are blocked, jump-ins hit.
  Light, Light, Throw (U on the left keyboard) while the lights hit throws from the string. Down + Heavy under a
  jump-in knocks the jumper down.
- **Animation.** `Docs/AnimationAudit.md` lists every clip; `Tools/Blender/anim/audit_clips.py` regenerates the CSV.

## 3. Where to look closely

- **A held standing guard blocks jump-ins again.** The previous round let jump attacks through a held Block; this round
  makes them overheads (blocked standing, beat a crouching guard), the way MK-style games pair jumps with crouching
  lows. A jump-in now opens a defender who crouches, and throws open a defender who stands still.
- **Combo throws cannot be escaped** (they are the next hit of a combo, so there is nothing to react to); neutral
  throws can. The combo-throw range is longer for Wren (70 cm, a shot) than for Ashka (45 cm, a clinch).
- **Down + Light during a string's cancel window continues the string** (Light 2), as the move matrix shows: the low
  needs a press outside a cancel window. Deliberate (it keeps strings reliable), documented in the contract.
- **The uppercut has no invulnerability**; it wins against jump-ins by timing and its low wind-up, and against a jab
  timed into its startup. Blocked, it is a large punish (the Lesson teaches that).
- **Art limits** the art pass left: Ashka's face is still a MakeHuman head with painted shading (heavy brows, very
  saturated eyes in neutral light); her bangs look comb-like up close; the braid is woven tubes; the coat still
  shows some bust shaping and its front panels ride on the thigh in kicks and crouches; under a bright key her
  blacks read charcoal (in the chapel they read black). Wren's wraps are fixed geometry, not cloth. Triangle counts
  rose 16% (Wren) and 26% (Ashka). Two character builds give identical geometry but not byte-identical files
  (Blender's UV island packer varies; textures differ by at most 8/255).
- **A light wedge under Ashka in her crouch** is a coat panel catching the moonlight; it was there before this pass.

## 4. Open

- Owner playtest of the new mechanics, art and feel (checklist in [Status](Status.md)).
- Independent review of this candidate.
- Physical controllers were simulated (virtual Xbox and DualShock 4 pads), not held.

## 5. Commit structure

Eleven commits on `ea3ddc6`: combat core and data with tests (`a8cc695`), controls, Lesson and presentation
(`4fc8704`), motion for the new moves (`96275a9`), the move matrix and contract prose (`cf675e1`), the Lesson punish
step (`61badfc`), the clip audit and its fixes (`c6de32d`), the audit table and production notes (`5dfe4c2`), README
and research (`c425f4e`), controls tests (`f11f04e`), the character art (`8677cb2`) and the imported meshes and
rebuilt clips (`5d5c316`), then documentation of the results.

---

## Previous round: creator playtest round (2026-11-07)

This guide is for reviewing `release/first-slice` (pull request #1) after the creator's playtest of candidate `060a75f`
on 2026-11-07. The creator asked for four changes, in this order: a natural spinning elbow for Wren and a proper
body-level roundhouse for Ashka; jumping with a clear purpose that fits the other mechanics; grappling removed from the
playable game but kept for later; and the PlayStation controller and TV audio recorded as verified. Later the same
day they asked for the buttons Grab left unused to be repurposed. Nothing else was in scope: punches, Wren's kicks and the rolls are unchanged. The previous round (the start-up crash, EH-07) is
described in the [validation report](Validation.md), "Candidate `060a75f`"; rules and move data are in the
[combat contract](CombatContract.md).

**Candidate:** package built from commit `4cee9c1` (Shipping, Linux), released as `EbonyHearts-Slice-4cee9c1.tar.gz`,
SHA-256 `c5ad9309292571b400aae0aa215d8f66f945e4af6ad576527f171458f924f591`. Commits after `4cee9c1` change
documentation only up to the initial independent-review head `0965ff2`. Subsequent repairs and their package are in
section 6. Results for the creator-played candidate: Validation, "Current candidate".

### 1. What changed and where

| Request | Change | Where | Checked by |
|---|---|---|---|
| Wren's spinning elbow contorted | At contact her right fist was behind her head, so the arm wrapped round it and the elbow pointed up, the left hand hung behind her, the knees caved in and the rear foot tucked across. Re-keyed: right side to the opponent, upper arm pointing at them at head height, fist folded by the head, left hand guarding the face, head turning ahead of the body, knees over the feet, rear foot swinging round at hip width, and a recovery key so the elbow does not flip over the arm on the way back. Timing, hitbox and the hand-overs into and out of the move are unchanged (elbow 85 cm out, 139 cm up at the first active frame; it was 83 cm out, 130 cm up) | `Tools/Blender/anim/moves.py` (`wren_moves`, Light 3), `Content/Characters/Wren/Anims/A_Wren_L3` | per-frame joint positions, flip, speed, floor and hand-over checks (Validation); `review_playtest.txt` footage |
| Ashka's Body Kick was not a roundhouse | Rebuilt from Mixamo's Mma Medium Kick: the hips turn over and the shin lands level at about 1.05 m, inside the unchanged hitbox. The capture is kept at 85% with a faster retraction, so the follow-through does not tip the body over. The previous source (Roundhouse Kick With The Rear Foot) read as a straight front kick. Renamed "Body Roundhouse" | `Tools/Blender/anim/mocap_clips.json` (`ashka.H`), `Content/Characters/Ashka/Anims/A_Ashka_H`, `Content/Data/Fighters/ashka.json` (name only) | as above |
| Jumping had no purpose | A jump attack that connects with a grounded opponent keeps them in stun until the jumper has landed and recovered, plus 12 ticks on hit or 2 on block, however high it connected; a held Block does not stop it (a timed block does, and usually gives the defender the turn); one attack per jump. Strikes still knock any jumper down. The CPU jumps in more against a guard it has seen held, and now answers jump-ins: it notices a jump in two thirds of its reaction time (at the full delay the Normal CPU saw a jump-in only once its attack was out, and a player who did nothing but jump in beat it 24 matches out of 24), times its anti-air jab to the jumper's arrival, starts no poke while a jump comes at it, and may step back instead of holding a block | `Source/EbonyHearts/Core/EHMatch.cpp` (`ResolveCollisions`, `StartMove`, jump state), `EHCombatData.*`, `Content/Data/rules.json` (`jumpInHitAdvantage`, `jumpInBlockAdvantage`, `heldBlockStopsJumpIns`), `EHAI.*` | `jump_ins_have_landing_relative_advantage`, `jump_ins_beat_a_held_block_but_not_a_deflect`, `jump_in_hit_links_into_a_light`, `one_attack_per_jump`, `cpu_anti_airs_jump_ins`, `cpu_levels_play_legal_complete_matches` |
| Remove grappling, keep the work | `"grappling": false` in `rules.json`: no throw move can start. Grab is hidden from Controls, the move list, the results, the input log and the dummy options; Lesson steps 6 and 7 teach the jump-in and the anti-air instead; the CPU never grabs; texts no longer mention grappling. The grab move, throws, escapes, their code, data, animations and documentation stay, and the original texts and Lesson steps return when the switch is turned back on | `EHMatch.cpp` (`SelectMove`), `EHAI.cpp`, `EHDirectorFlow.cpp`, `EHDirectorUI.cpp`, `presentation.json` | `grappling_off_grab_does_nothing`, the throw tests (switched on locally), `cpu_levels...` (no grabs in 36 CPU matches), packaged controls and journey runs |
| Repurpose Grab's buttons (asked after the first candidate of this round) | Cross / A jumps and L1 / LB blocks; I, Numpad 5 and ; jump. Grab has no default button. Each action can hold three buttons (was two), so the right keyboard keeps Up, Numpad 5 and ; on Jump. Settings format 3: loading a version 1 or 2 file moves Grab's former default buttons to their new jobs where the slot is free, with a notice; a button the player gave Grab themselves stays | `EHSettings.*` (`Defaults`, `EHFormerGrabKey`, `Load`), `EHDirectorFlow.cpp` / `EHDirectorUI.cpp` (third slot), `EHAutomation.cpp` | `bindings_selftest` (new layout, third slot, a version-2 file), `input_selftest` (Cross jumps with the stick's direction, L1 blocks), `controls_remap` / `controls_persist`, simulated pads |
| Jump-in loop (found while preparing this review) | After a jump-in hit, jumping again at once and attacking on the way up renewed the landing-relative stun on every hit: an unescapable loop to KO (29 hits in a probe, through a held Block too). The landing-relative stun now applies only to a jump attack that opens contact; on a defender already in hit- or blockstun a jump attack takes its own stun with decay | `EHMatch.cpp` (`ResolveCollisions`) | `jump_ins_cannot_loop` (longest re-jump route 2 hits; 18 before the fix) |
| Controller and TV audio | Recorded as verified by the creator | `Docs/Status.md` | the creator, 2026-11-07 |

Supporting changes: `Tools/Unreal/build_characters.py` can import just named clips (`EH_ANIM_NAMES`);
`Tools/Docs/move_tables.py` prints jump-in advantage from the rules and lists the grab as kept;
`Tests/Auto/review_playtest.txt` records the changed moves and jump-ins.

### 2. Check it yourself

- **Core.** `Tests/Core/run_core_tests.sh`: 44 cases, `890 checks, 0 failures`. Set `heldBlockStopsJumpIns` to `true`
  or `jumpInHitAdvantage` to `0` in `rules.json`, remove the `airAttackUsed` check in the jump state, apply the landing-relative stun to every jump attack
  (drop `opensContact`), or let the CPU see jumps only after its full reaction delay, and a new test fails.
- **Training.** Pause > Dummy > Block all. Jump toward the partner and press Heavy on the way down, then Light as you
  land: the jump-in hits through the held guard and the Light combos. Lesson steps 6 and 7 cover the same and the
  anti-air.
- **Grappling switch.** Set `"grappling": true` in the staged `Content/Data/rules.json` (it is a plain file in the
  package) to bring grabs, their Lesson steps and texts back.

### 3. Where to look closely

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

### 4. Open

- The creator played this candidate on 2026-11-07. They later identified combat smoothness and jumping feel as needing
  refinement; the character models are acceptable placeholders that need more work. On 2026-11-08 the creator clarified
  that these are ongoing, nonblocking improvements and should not determine this review's merge-readiness verdict.
  Merging itself is not authorized.
- Not verified: hardware other than the test machine; Wayland sessions.
- The animation sources (raw captures, `.blend` files) are outside the repository, unchanged from earlier rounds.

### 5. Commit structure

Eight commits on top of the previous head `22fa565`: combat rules and tests (`80e57fa`), game layer (`d3548d7`),
animation (`bb4823b`), documentation and move notes (`d1ede0e`), a stronger jump-in test (`37d6ab4`), the CPU's
anti-air (`b445999`), the repurposed buttons (`d2f7cb7`) and the jump-in loop fix (`4cee9c1`), plus documentation of
the results. Earlier history is
unchanged; nothing has been merged, tagged or released.

### 6. Independent PR audit (2026-11-08)

This section records a new review of PR #1, not the engineer's acceptance report above. The live starting head was
`0965ff285d391948c192bd447a586b77d3bc23bd`; the base and merge base were both
`9a34d030281f3321d41ac64e8a065f8a0336b6dc`. At that point GitHub reported the PR open, cleanly mergeable,
with 51 commits, 514 changed files and two passing core checks. There were no open review threads or approvals.
The original source candidate was `4cee9c1`; the later commits up to the starting head changed documentation only.

#### Coverage and issue ledger

| Area | Independent coverage | Result |
|---|---|---|
| PR and repository | Full Git file inventory (514 tracked files, including 344 LFS objects), PR file and commit pagination, branch diff, review/issue comments, GitHub checks, merge status and ruleset query; no repository `AGENTS.md` | No unseen review thread or active worktree change at start; GitHub's `main` branch-protection API returned 404 and the repository ruleset list was empty, so repository protection is not a substitute for owner authorization |
| Combat and AI | Core timing, collision, jump, block, throw switch, CPU, data tables and tests; historical run output re-parsed | No confirmed active core defect. The dormant CPU throw-tech queue remains a future issue if grappling is re-enabled |
| Input and UI | Router, settings, menus, pause and disconnect ownership, automation scripts | **P2 fixed:** leaving a non-video settings page by its Back button did not save edits; a later Video Back could reload old values. **P2 fixed:** replacement controller ownership could leave pause unusable, or assign one controller to two local-versus slots |
| Presentation and content | Visual, animation, audio, VFX and UI paths; all named clips and sounds resolved; 339 Unreal packages have valid package magic, LFS fsck passed | No missing referenced asset found. A sound-name-only cache could collide if future assets reuse a name across categories; no current collision exists |
| Platform and package | Linux startup, display/audio code, package tooling, manifest and raw evidence; independent package extraction and hash checks | **P2 fixed:** Ashka's active body-roundhouse Mixamo input was absent from the source manifest, and ACCAD was credited for the wrong kick. The raw Mixamo source matched the recorded download hash. **P2 conditional risk:** SDL's variable audio callback request can exceed the fixed queued buffer; no dropout was demonstrated on this PulseAudio path |
| Documentation | README, contracts, status, research, production, validation, provenance and review versus source and raw evidence | **P2 fixed:** stale package commands and claims that jump was deferred, held Block stopped every attack, and the latest candidate had not been played. Current owner feedback is recorded separately from automated results |

The settings and controller changes are in `6eebee0`; the provenance repair and a missing-source regression guard are
in `263a3a7`; documentation corrections are in `309c87c` and this audit follow-up. Existing raw assets, engine files,
history, creative rules and the private `private/plans` area were not changed or published. The private third-party
source ledger was corrected in place after a byte-for-byte backup under the review evidence directory; the repo
manifest is generated from that ledger.

Lower-priority follow-ups: the digital-only trigger fallback suppresses its first two presses on a controller without
an analog trigger (P3, no failure on the tested DualShock/Xbox analog paths); CPU throw-tech can retain a pending
input if grappling is turned back on (P3, inactive with `grappling: false`); the sound cache keys only by sound name
although categories also select assets (P3, no current cross-category collision). These are recorded for later work,
not counted as demonstrated defects in the playable configuration.

| ID | Severity and location | Evidence, cause, disposition |
|---|---|---|
| PR1-01 | P2, `Source/EbonyHearts/Game/EHDirectorFlow.cpp:174,727` | Audio 80→85 was lost when its on-screen Back did not save and Video Back reloaded disk settings. Save on non-video Back (`6eebee0`); packaged regression now retains 85. |
| PR1-02 | P2, `Source/EbonyHearts/Game/EHGameDirector.cpp:850-915`, `EHDirectorFlow.cpp:758-779` | A disconnected pause owner could leave the replacement unable to navigate, and one pad could fill two disconnected versus slots. Transfer owner and fill at most one slot (`6eebee0`); distinct-key virtual takeover passed, dual-human variant remains source-path verified only. |
| PR1-03 | P2, `Docs/ThirdPartyManifest.json:578`, `Tools/Docs/third_party_manifest.py:60` | Active `ashka.H` references `K_MmaKick_Medium.fbx`, previously absent from the manifest. Raw copies match SHA-256 `f2488866df1ed1654ff72a5b30a5d12ae11ae0d1f7a51923ddf2382e0a883eeb`; ledger, manifest and missing-capture guard corrected (`263a3a7`, ten package tests). |
| PR1-04 | P2, README and `Docs/CombatContract.md`, `Docs/Research.md`, `Docs/Validation.md` | Stale commands/playtest claims and rule descriptions conflicted with current source and owner feedback. Reconciled in `309c87c` and follow-up documentation commits; source and dated historical results were kept distinct. |
| PR1-05 | P2 conditional, `Source/EbonyHeartsLinux/Private/EHSdlAudioOutput.cpp:238-263` | SDL may request more bytes than the fixed one-buffer callback supplies. No dropout was reproduced on the tested PulseAudio sink; retain as bounded platform risk pending a variable-request/device reproduction. |
| PR1-06 | P3, `Source/EbonyHearts/Game/EHInputRouter.cpp:283-287`; `Source/EbonyHearts/Core/EHAI.cpp:231-240`; `Source/EbonyHearts/Game/EHAudio.cpp:37` | Digital-only trigger, dormant throw-tech queue, and future same-name/cross-category sound collision risks respectively. No observed failure in the enabled configuration; follow up when those paths or assets are exercised. |

#### Evidence and limits

- The original core suite was rerun: 44 cases, 890 checks, zero failures. Python compilation and the original nine
  package tests passed; the added provenance guard made ten passing package tests. LFS fsck passed.
- The `4cee9c1` archive was freshly extracted into a path with spaces. Its SHA-256 was
  `c5ad9309292571b400aae0aa215d8f66f945e4af6ad576527f171458f924f591`; all 21 per-file hashes matched.
  A fresh packaged smoke exited zero and reported no missing animation or sound. This proves that archive still runs
  on the review machine, not that the new repairs have passed packaged runtime checks.
- The historical `060a75f` startup data was parsed attempt by attempt: 385 clean exits with no timeout, orphaned
  process or failed audio/display marker. Historical performance CSVs also matched the reported frame-time statistics.
  These are historical observations of unchanged startup code, not fresh 385-start results for the repaired head.
- The host currently enumerates a Sony DualShock 4 over Bluetooth (vendor `054c`, product `09cc`, `js0`). Detection
  alone does not establish that buttons, trigger, pause recovery or feel work in the new package. The creator's earlier
  physical PS4 and TV-audio checks apply to `060a75f`. The later physical input observations are recorded below.

#### Repaired-package qualification and verdict

Editor and Shipping code compiled with UE 5.8.4, and `BuildCookRun` completed with `BUILD SUCCESSFUL` from
`309c87c072851526650d8c1b0daec87b0bcccc8b`. The staged review archive is
`EbonyHearts-Slice-309c87c.tar.gz`, SHA-256
`ed7943fbe0ca854f7a6f17abf6cb8064835e1b8ba5a0f7d01447025352c97cd6`, with content hash
`4ac5b6961abc40b7a8af4fca5161fd0ae18a9b2a99d56d527c9d8aed6425c607`. All 21 files in the archive
matched their recorded hashes after fresh extraction into a path with spaces. This is a local review artifact; it has
not been published as a release.
From its containing directory, run `sha256sum -c SHA256SUMS`, extract with
`tar -xzf EbonyHearts-Slice-309c87c.tar.gz -C '<new empty review directory>'`, then from that directory run
`sha256sum -c <containing directory>/EbonyHearts-Slice-309c87c.files.sha256` and launch the extracted
`EbonyHearts.sh` with an isolated `-UserDir=<writable directory>`. Do not use this review archive as a public release.
The Git tree contains the playable game, code and cooked inputs, but the editable `.blend` and original capture files
remain on the private HDD; the repo manifest records their source hashes. A clone alone cannot regenerate every
animation from raw editable sources.

The extracted package passed `smoke.txt` (no missing animation or sound; audio output delivered 2,792 buffers with
one initial drop; display guard active; 724 sampled frames, median 16.67 ms and p99 16.75 ms), `journey.txt` (all
scripted screens and settings transitions), and the new `settings_video_preserves_audio.txt` (80 to 85, then 85
after Video Back). Each exited zero and had no automation FAIL/WARN. The full match matrix was deliberately stopped
after two complete matches while prioritizing the changed controller path; its third match was interrupted, so this
is **not** a complete fresh matrix pass. The unchanged combat core had a complete historical matrix and its 44-test
suite was rerun at the repaired source (890 checks, zero failures).

Simulated DualShock 4 and Xbox 360 pads each navigated into a match, disconnected, reconnected and quit through the
UI. SDL reused the same device key on these reconnects. A separate test kept a second virtual pad connected while
the first pad owned pause, disconnected the first, and used the second pad to take over and navigate to Quit; the log
showed distinct keys 101 and 102 and a clean exit. The two-human-slot guard was source reviewed independently but
was not exercised dynamically. During this review, the creator pressed a physical Bluetooth DualShock 4: Linux
reported Cross, L1 and R2 events, and the package advanced from title to a match without scripted navigation.
Options was requested but no corresponding event was captured in the bounded input window. These observations prove
real input reached the host and some menu navigation reached the game; they do not settle combat feel or every binding.
The owner's settings file was restored to its exact pre-test SHA-256
`2ab7d6ee683f7fc1ed74fdb1f4e31203fb1dcd1479b17a4b704c7d999aabdbdc`; later runs used Unreal's
isolated `-UserDir` option.
Packaged binding/router self-tests, remap/conflict/cancel and a second-process persistence check also passed with no
automation FAIL/WARN. The existing `4cee9c1` review-playtest video was decoded and sampled as a 39-frame sequence:
both fighters, jump arcs, strike contact and hit effects are visible, with no gross rendering failure in those samples.
Sampling cannot judge smoothness between frames or settle the creator's animation and jumping feedback.

A separate read-only AI verifier checked the changed settings and controller paths for counterexamples, reran all ten
package tests and `git diff --check`, and checked all 32 active mocap FBX references against the manifest and both
raw copies of Ashka's kick. It found no confirmed regression. It is procedural non-authoring verification, not a
human approval, a GitHub review approval or a physical playtest.

The Shipping package was built from `309c87c072851526650d8c1b0daec87b0bcccc8b`. Subsequent review commits
change README and `Docs/Review.md`, `Docs/Status.md`, and `Docs/Validation.md` only; no source, content, config,
package tool or test file differs from that built revision. The PR branch is `release/first-slice` against `main`;
the reviewed base is `9a34d030281f3321d41ac64e8a065f8a0336b6dc`. The exact final PR head and current GitHub
conflict/check state are recorded in the PR review comment because a commit cannot contain its own hash. The
authenticated account owns this PR and cannot supply an independent GitHub approval.

**Technical verdict: ready for owner merge decision.** No confirmed merge-blocking defect remains on the tested
Linux/X11 path after these repairs. The conditional SDL callback size concern, the untested two-human replacement
path, Wayland and other hardware remain explicit, nonblocking limits. The creator clarified on 2026-11-08 that combat
smoothness, jumping and placeholder-model work are ongoing improvements and do not block this merge-readiness verdict.
This does not claim those improvements are finished or that the game has been accepted as final. The authenticated
owner account cannot furnish a formal independent GitHub approval. **Merge authorization is still absent:** PR #1
must remain open until the creator explicitly authorizes integration.
