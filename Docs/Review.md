# Review guide: combat, animation and character pass (2026-11-08), controls and Ashka (2026-11-09)

## Independent review record (2026-11-11; integration completed)

This section is the current independent review record. The implementer's earlier reviews and failed or superseded
rounds remain below as dated history. The starting identities were PR #2 `bed7fb60d03704cf8e58a000b1fb284968690dc8`
into `release/first-slice` `04714438f6901424ff1cdf6feae126123aae1b5e`, then PR #1 at that release head
into `main` `9a34d030281f3321d41ac64e8a065f8a0336b6dc`. Both PRs were open at the review
start. The actual integration identities and limits are recorded below; these starting refs were not approval.

### Final integration record

| Step | Verified result |
|---|---|
| PR #2 to `release/first-slice` | Merged at reviewed head `4b21045a948f4e0dc0731deb314c3197ccd78477` as `964eeb8c95f38d2c35fee3dde3c8847705cf6bfb`. Its parents are the old release `04714438f6901424ff1cdf6feae126123aae1b5e` and reviewed head; the merge tree is `e1e5769c3b70bd8ef02f606f0a48ff207f2a8653`. The exact-head and release-push `core` checks succeeded. |
| PR #1 to `main` | Merged at combined release head `964eeb8c95f38d2c35fee3dde3c8847705cf6bfb` as `1fe9eec631d0d6f747d6248275feccbbf25713b0`, with parents old main `9a34d030281f3321d41ac64e8a065f8a0336b6dc` and that release head. Its tree is the same `e1e5769c3b70bd8ef02f606f0a48ff207f2a8653`; the updated PR `core` check and post-merge main push run `43059063902` both succeeded. A separate non-authoring combined-tree review found no conflict or source/content delta from the reviewed PR #2 head and freshly passed 1,618 Core checks, zero failures. |

Both PRs had exact-head technical review comments; they were not formal GitHub approvals because the authenticated
account authored the PRs. The creator explicitly authorized qualifying merges, and the normal GitHub merge path was
used with a head-SHA guard after live head/base, checks, reviews and rules were refreshed. Neither merge is a public
release or creator playtest acceptance. The November 9 report of other issues remains open for gradual follow-up;
overall animation transitions and throw feel still need creator judgment. The package and human/hardware limits below
remain in effect.

### Coverage ledger

| Area | Review scope and boundary |
|---|---|
| Combat and AI | Core, fighter/rule JSON, callers, 60 Hz state transitions, throws, jump rules, CPU behavior and Core tests. Found a stale queued CPU input on Training dummy-mode changes. |
| Game and interface | Input routing, settings, menus, two-player ownership, Still Water UI, scale, flow and automation. Found enlarged-scale clipping and character select ownership after pad removal. |
| Assets and motion | Character/animation mapping, editable source provenance, imported content identities, clip audit and prior and current packaged footage. The creator's first prioritized feedback is animation transitions and throws. Pair-generated Ashka clinch-trip motion was rebuilt and inspected in the shipped game; this targeted visual check does not establish creator acceptance or all-transition quality. |
| Platform and delivery | Linux display/audio integration, packaging, LFS, third-party notices, guard/launcher scripts and prior raw evidence. Found unsafe global process cleanup in the startup loop. Prior green CI does not compile or run Unreal. |
| Documentation and research | Current contract, research, status, production, UI reports and historical reviews were reconciled against code. Old jump-in prose and an unimplemented reduced-motion control were labelled correctly; prior results retain their original dates. |

### Issue register

| ID | Severity | Confirmed behavior and location | Repair and verification status |
|---|---|---|---|
| EH-SOL-01 | P2 | `EHAI.cpp`: switching Training dummy modes retained queued CPU actions; a pre-fix 256-seed probe observed 33 stale presses. | `026b264`; the 1,618-check Core regression suite and `05978ee` full 28-scenario package battery passed. Core and data are unchanged at `cec9493`. |
| EH-SOL-02 | P2 | At 140% scale, HUD and prompts clipped; Move List initially needed full-scale pagination. | `6c035ca` through `9f6146a`, `8e1707c`, `78158b4`; `05978ee` package screenshots at 1920×1080 and 1280×720 show the crescent and select labels inside the viewport, and both fighters' two Move List pages were reached. |
| EH-SOL-03 | P2 | A disconnected pad could retain a character-select slot and prevent replacement. | `6c035ca`; a `05978ee` packaged Xbox virtual-pad scenario destroyed the joining device and logged a distinct-ID replacement, match start and clean quit. Physical pad behavior remains untested. |
| EH-SOL-04 | P2 | `launch_loop.py` could kill an unrelated, pre-existing game session through global process cleanup. | `6984e05`; three mocked safety cases passed. The exact `cec9493` extracted package completed 20 fresh-profile, 1920×1080 windowed start/platform-check/quit attempts with 20 clean exits, no timeouts, orphans or overlap. This loop did not recreate monitor removal or physical audio-device swaps. |
| EH-SOL-05 | P2 | In the prior shipped Ashka clinch trip, the attacker released at frame 36, ten frames before the victim's frame-46 floor contact; prior footage showed visible disengagement during the fall. | `a2fe27b`, `30d3fa8`, imported as `05978ee`: isolated 12-clip rebuild/import and final packaged `review-combat` footage show clinch contact into the trip and an attached follow-through to floor contact. This targeted observation does not resolve the creator's broader transition/throw judgment. |
| EH-SOL-06 | P2 | The prior package-battery wrapper records run exit codes but does not fail itself when a scenario fails or assert every expected completion marker. | `6f03f99` adds a separate completeness/evidence verifier with five synthetic tests; `8cc2fb3` starts affected scripts from a known menu. The first final battery's incomplete matrix (3/12) was correctly rejected despite wrapper `rc=0`. Completed earlier scenarios and a service-run matrix onward were indexed without altering raw logs; the composite 28-scenario verifier passed. |
| EH-SOL-07 | P3 | Current status documentation omitted the November 9 **Adventure Mode** rename and could leave its conceptual scope ambiguous. | `Docs/Status.md` now identifies the future exploration direction and its separation from the shipped Versus/Training slice; no new mode was implemented. |
| EH-SOL-08 | P2 | The previous throw presentation kept a close-range depth stagger into the paired animation: at a 50 cm center gap the first 60 Hz throw frame could retain about 8.3 cm on each fighter, leaving the authored clinch pair separated by about 16.7 cm. `EHFighterVisual.cpp` did not meet the on-line throw contract. | `cec9493` starts easing both fighters toward the line during the throw attempt and continues through Throwing/Thrown/Tech. Editor and Shipping compilation, cook/package, extracted file hashes, the full 12-match matrix and targeted combat/jump scripts passed. A non-authoring reviewer inspected dense 60 fps frames at first contact for four throw paths and found no obvious lateral gap or snap. The remaining elbow discontinuity is tracked as EH-SOL-10; creator judgment remains separate. |
| EH-SOL-09 | Evidence erratum, no confirmed game defect | An initial visual reading of the `05978ee` results-focus screenshot suggested missing digits and letters. | A non-authoring reviewer compared the source PNG pixels in four text regions before/after focus on both `05978ee` and `cec9493`: zero pixels changed by more than 50 RGB levels. All 240 frames in the `cec9493` focus video retained the Wren damage digits in a bright-pixel audit. The alleged dropout was a viewing artifact; raw captures are retained. This rules out that reported dropout in these captures, not every possible runtime text fault. |
| EH-SOL-10 | P2, animation discontinuity | In the `v4` Ashka Clinch Trip victim clip, Wren's left elbow moved 20.9 cm from frame 16 to 17 while shoulder moved 7.0 cm and wrist 1.2 cm, then the elbow moved only 0.6 cm; the Blender IK pole crossed during the `stumble` key. The arm was occluded in sampled game footage, so player visibility was unproven. | `f3c5abd` changes only the victim elbow pole at `throws.py:213`; an isolated 12-clip rebuild and a separate non-authoring Blender comparison found Wren's f17 elbow step reduced to 8.659 cm and no new flips. Ten clips have no joint-frame position change above 0.01 cm; only the two victim clips change in their left-arm hierarchy. All 12 imported Unreal assets changed hash and the commandlet exited zero with 12/12 import counts. Four bind-pose warnings on the attacker/tech imports match the prior v4 import; no new import warning. The exact `f3c5abd` packaged combat/art scripts passed. A non-authoring reviewer inspected every 60 fps frame around neutral and combo Ashka throws, finding continuous visible arm motion and no new obvious intersection; the elbow remains partly occluded and creator feel acceptance is untested. |

### Evidence index

| Evidence | Scope and limitation |
|---|---|
| Original-head GitHub `core` checks and `git lfs fsck` | Core/data/Python/package/move tables and LFS presence; no Unreal build or human playtest. |
| Prior `0126cac` UI package and `84acb66` slice package | Their source trees match the original PR runtime source except later documentation; useful regression baselines, not evidence for the repaired source. |
| `evidence/uiux-1109/battery-0126cac.log` and individual run directories | Twenty-eight recorded scenario exits were zero; individual markers were checked because the wrapper's final exit cannot by itself certify the battery. |
| `evidence/rc-84acb66/battery/review-combat/review-combat.mp4` | Prior in-game throw motion; confirms the visual review target, not a post-repair result. |
| New isolated throw FBX stage and clip audit | Generated from retained editable and licensed inputs; numerical clip checks and renders are separate from Unreal import and package review. |
| `tmp/sol-review-throw-stage-v5/audit.csv` and independent FBX comparison | Twelve exported Ashka ThrowC pair/escape clips; zero reported flips, pops or steps above 40 cm. A non-authoring verifier imported all 12 v4/v5 FBX pairs in Blender 5.2.2, sampled 15 joints on every frame, and confirmed the only changed joint-frame positions above 0.01 cm were victim left elbows on frames 14–24. This is a numerical source-asset check, not packaged gameplay observation. |
| `sol-review-05978ee` local Shipping package | UE 5.8.4 Development and Shipping compile, cook/package, 21/21 archive file hashes, archive SHA-256 `289216aae646c2defa441934ce87ecd37594129185f1e3a373900900b4b9935e`. `VERSION` records source `05978eef016a72a481e49fe938f911a84b1c0f88` and content `a468ce65fe95280a47cce3840cff29db82f8d71826b6b088cff4ae09322a6a87`. Local artifact only; source changes after this commit need equivalence assessment. |
| `sol-review-cec9493` local Shipping package | UE 5.8.4 Editor Development and Game Shipping compilation, cook/package, 21/21 extracted file hashes, archive SHA-256 `6b41bef630d9e3cf0021bf83cde30665a352bf6029afbeb747cb47769ef2a3b3`. `VERSION` records source `cec9493f791a843ac74dc533f3711e31f54f84c3`; cooked-content hash is unchanged from `05978ee`. Its executable differs for the throw-depth handoff. The first runtime attempt was rejected by the HDD reserve guard; after removing verified generated duplicates, the exact extracted package ran. |
| `sol-review-f3c5abd` local Shipping package | Shipping BuildCookRun/cook/package succeeded from source `f3c5abd7ee122f1292bb9f250915d20839c4b06a`; archive SHA-256 `989325086e28d35e0df8fb4bfc35f24c4f198b8dc7cfb9e3e5f2a648e9d60107`, content hash `a584f666ecda667b4768855033041959d5effcfa94dfbebb093a93d86d95d269`, 21/21 extracted file hashes passed. Its executable SHA-256 equals the `cec9493` executable; changed package files are cooked containers, manifests and VERSION. Generated stage/BuildCookRun duplicate directories were removed link-safely after archive and extraction verification to preserve the HDD reserve. The archive, checksum list, extracted package, source and logs remain. |
| `review-check/sol-05978ee-motion` and `sol-05978ee-ui-scale` | The `05978ee` package ran scripted 60 fps combat/jump capture and 140% UI navigation without logged FAIL/WARN; screenshots and sampled video frames were inspected. The captures are machine-driven visual samples, not human playtesting. |
| `review-check/sol-05978ee-battery2`, `sol-05978ee-battery3` and `logs/sol-05978ee-battery3-composite.log` | The first process ended after three matrix matches. Its negative verifier reports no done marker and only 3/12 match endings. A user service reran matrix and the remaining scenarios on the same extracted package; the composite index links the first 15 completed scenario directories and retained continuation directories. The separate verifier passed all 28 scenario exits, markers and evidence files. This is a composed set of independent game launches, not one uninterrupted process. |
| `05978ee` package performance on FLOWBOX | Ryzen 7 5700G, RTX 2060 6 GB, Linux/X11. 1080p V-Sync fight p99 16.751 ms (3,602 frames); 1080p no-V-Sync fight p99 10.698 ms (7,837 frames); native 3440×1440 default fight p99 16.746 ms (3,601 frames). Each cited window had zero frames over 33 ms. The `dropped_sim_ticks` field is cumulative since process startup, not a timed-window count. |
| `review-check/sol-05978ee-ui-extras` | Five packaged UI scripts and a distinct-device select replacement returned zero with expected quit/match markers. All 9 enlarged 1280×720 captures, 3 settings, 3 results and 10 plate captures were independently inspected. A later pixel-level check corrected the apparent results-text dropout (EH-SOL-09). Eight UI perf windows had p99 frame times 16.731–16.787 ms, zero frames over 33 ms, and UI paint p99 at most 0.3377 ms. Small white crescents are intentional menu ornaments. |
| `review-check/sol-cec9493-regression2` | The exact `cec9493` extracted package completed a 12-match matrix and 12 further scenarios: review match, reactions, flow, scripted playtest, signature, combat/jump motion capture, art and four performance cases. A separate task-local verifier checked all 13 exits, completion markers, expected asset audit and footage. The matrix logged 12 match endings, `missing_anims=[]`, `missing_sounds=[]` and clean quit. The first reserve-guard refusal remains in `sol-cec9493-regression` as negative evidence. |
| `cec9493` package performance on FLOWBOX | 1080p V-Sync fight p99 16.718 ms (3,601 frames); 1080p no-V-Sync fight p99 8.142 ms (8,348 frames); native 3440×1440 default fight p99 16.743 ms (3,602 frames). Each measured window had zero frames over 33 ms. These are timed render-frame windows, not input-latency or human smoothness measurements. |
| `review-check/sol-cec9493-launch20` | Twenty fresh-profile windowed starts of the exact extracted package. Independent parsing of `attempts.jsonl` found 20/20 zero exits and platform checks, no timeout, process overlap or orphan. Durations were 9.102–9.381 s. The loop used the task's isolated profile, not the owner's live profile; it is a sampled startup check, not proof against the historical display/audio race under all device changes. |
| `review-check/sol-f3c5abd-targeted` | The exact `f3c5abd` extracted package returned zero from review-combat, review-jump and art. The separate verifier found four scripted throw attempts, `missing_anims=[]`, `missing_sounds=[]`, expected quit markers and both 60 fps footage files. A non-authoring reviewer examined every 60 fps frame around contact and fall in neutral and combo Ashka throws, plus sampled recovery frames: visible left-arm motion was continuous and the grapple/trip/recovery sequence had no new obvious intersection. Occlusion prevents a full side-camera judgment of the elbow; automated footage is not human feel acceptance. This specifically checks changed content, not a full 28-scenario repeat. |
| Source and documentation checks | 1,618 Core checks, 10 package and 5 battery-verifier tests, Python compile, LFS fsck and move-table consistency passed at packaged source `05978ee`. The only later runtime source edits are the throw-depth visual handoff and the Ashka victim elbow-pole generator/imports; Core/data/tests/config and the prior test harness are unchanged. `cec9493` compiled Editor/Shipping and ran the full matrix; `f3c5abd` was freshly packaged and ran the changed-content scenarios. Final documentation-only review commits require whitespace/link checks, not an invented runtime rerun. |

### PR disposition

| PR | Current disposition | Required next gate |
|---|---|
| #2 → `release/first-slice` | Merged as `964eeb8` after exact-head technical review, successful CI and guarded integration; see the final integration record above. | Creator evaluation of broader throw and transition feel remains a development follow-up. |
| #1 → `main` | Merged as `1fe9eec` after fresh combined-tree review, successful PR CI and guarded integration; the post-merge main push check passed. | Retain the package, human and hardware limits. |

The GitHub account available for these merges authored both PRs. It could not provide formal self-approval; the
technical comments and non-authoring checks are recorded with their actual scope. No release occurred in this record.

---

This guide is for reviewing branch `dev/combat-pass-1108`, which carries the creator's 2026-11-08 combat, animation and
character requests on top of the PR #1 head, then the 2026-11-09 fighting-game control layout and Ashka Rook refined to
her new character sheet (and then to its version 2, the same day), then the blocking animations. It is the implementer's account, not an independent review. Earlier rounds
follow below, unchanged, as history; the 2026-11-08 independent audit (previous round, section 6) applies to its own
candidate, not to this one.

| | |
|---|---|
| Branch | `dev/combat-pass-1108`, added to PR #1 on 2026-11-09 at the creator's request (`release/first-slice` fast-forwarded to it) |
| Base | `ea3ddc655fdf10666ede89f14df201e43b25daad`, PR #1's head before this round |
| Candidate source | `84acb66`: the combat pass `5d5c316`, the fighting-game control layout (`1b714fd`) and its settings write-back (`32831cc`), Ashka's refinement to her sheet (`01ce31a`..`2c993b0`) and to its version 2 (`7a1fe65`..`c6c0de2`), the blocking animations (`42e943c`, `0c8a9f5`), the coat tails off the legs (`e08d8a0`, `108455a`), the coat following the thighs (`8c22521`), then the coat's tails simulated as cloth (`77ea4ac`, `84acb66`); later commits change documentation only |
| Package | `EbonyHearts-Slice-84acb66.tar.gz`, Shipping, Linux; identity and checksums in [Validation](Validation.md), "Current candidate" (the evidence of `8c22521`, `108455a`, `0c8a9f5`, `c6c0de2`, `2c993b0`, `32831cc` and `5d5c316` follows it) |
| Not done | nothing merged, tagged or released; `main` is untouched |

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
| Ashka to her character sheet (2026-11-09) | The sheet replaces the earlier one. Outfit: white long-sleeved shirt (now a full shell, draped from the bust, smoothed over small body bumps, tucked into the trousers under a clean waistline), black tie to the waistband, black pants, brown loafers; the coat is no longer built and its tail chains stay in the rig unweighted (skeleton identical). Hair: a loose ponytail (core, layered strand cards, tie, nape gather) on the former braid chain. No chest tattoo. A slightly stronger calm smile. Kit: away + Light front kick (mid, snap kick, special-cancel on hit) and away + Heavy spinning elbow (high, knockdown on counter; Light, Light into it on hit); the CPU uses both. Canon: the public repo carries her look, style, title and friendship with Wren; the rest of the sheet is in a private canon file (the creator's choice) | `Tools/Blender/characters/{eh_ashka,eh_hairstyles,eh_paint,eh_specs,build_characters}.py`, `characters.json`, `Tools/Unreal/build_characters.py` (stale slots), `Content/Data/Fighters/ashka.json`, `presentation.json`, `Core/EHAI.cpp`, `Tools/Blender/anim/moves.py`, `Docs/CombatContract.md` | `ashka_front_kick_and_spinning_elbow`, the move matrix's away columns, clip audit (157), render and in-game before/after, `review_ashka.txt`, the battery, a CPU-vs-CPU probe |
| Ashka to her sheet's version 2 (2026-11-09) | The creator updated her appearance the same day; version 2 is the canon. Frock coat grown and draped from the body: fitted waist, structured shoulders, high stand collar, fronts meeting at one waist button, split coattails just above the knee on the coat-tail chains (weighted again, spring-baked in every clip), the tails' crimson lining its own inner layer joined by a turned edge; silver buttons, a crimson gem brooch; painted black-on-black vine-and-flower embroidery, crimson piping, ice-white cuff and collar trim. Ice-white blouse with a stand collar, chest pleats and lace cuffs; brocade waistcoat with silver buttons and a chain; crimson cravat (knot, puffed front, dark-silver clasp); high-waisted trousers with crimson side stitching; ankle boots. Hair: waves toward the ends, a small black ribbon bow, slightly parted bangs. Face: heart-shaped, cheekbones, slender nose, fuller lips, almond eyes, finer brows (eyebrow005, CC0). A crimson, shadowless light lights the coat's lining during flame moves. Painter: garment parts now come from the nearest vertex (interpolating ids painted a black band at the waist seam); the tails' map is cut into four panels so the atlas packs fully; sleeve folds stay on the sleeves. Kit, CPU and lore unchanged | `Tools/Blender/characters/{eh_ashka,eh_hairstyles,eh_specs,eh_paint,eh_tex}.py`, `characters.json`, `Source/EbonyHearts/Game/{EHFighterVisual,EHGameDirector}.*`, `Content/Characters/Ashka`, `Docs/CombatContract.md`, `Tests/Auto/review_ashka.txt` | skeleton compared bone by bone (88, identical), clip audit (157, values unchanged), renders three ways (2026-11-08, sheet 1, sheet 2) and deformation poses, in-game footage of the moves and the lining light, the battery, the soak |
| Blocking animations (2026-11-09) | The guards looked contorted. Causes, measured and rendered from the shipped clips: the keyed standing guard put the hands on the head (the wrists 17-20 cm forward of the root at 1.52 m, where the leaning stance already has the head) with outward elbow aims, so the elbows flared; Guard and BlockHit layered captured motion as local rotations onto it (the block reaction flung an arm behind the head); the crouch family keyed its hands without the head, which the crouch carries 43-47 cm forward, so the forearms crossed over the head. Fix: the solver places a hand from the posed head joint (`hand_*_head`); one simple keyed guard per fighter (Wren a compact MMA shell, Ashka an upright Muay Thai high guard) with a slow breath; a keyed blocked-hit recoil (18 frames); the crouch keeps its depth with the hands in front of the face (lower when not blocking), elbows down and in, the rear knee forward. No combat code, data, hitbox or timing changed | `Tools/Blender/anim/{animlib.py,moves.py,mocap_clips.json}`, `Tools/Docs/anim_audit_table.py`, `Content/Characters/*/Anims` (16 clips), `Tests/Auto/review_blocking.txt` | clip audit (157), the clips measured and rendered before and after, in-game recordings with the same inputs before and after (both fighters, both sides) and frame-by-frame stills of every guard transition, the battery |
| Open items after the blocking round (2026-11-09) | Ashka's coat tails passed into her rear thigh in the kneeling crouch: the tail springs now push each tail point out of capsules round the thighs and calves (all her clips rebuilt; body identical; no tail pops). Wren's uppercut is finished by the capture build again (its last frames ease into the idle). The Flame Burst's light recorded with the gauge kept full; frame times across eight flame moves measured with and without the light, warm and with an empty shader cache | `Tools/Blender/anim/animlib.py` (`LEG_CAPSULES`), `Content/Characters/Ashka/Anims`, `A_Wren_U`, `Tests/Auto/{review_flame,perf_flame}.txt` | clip audit (157), tail motion old against new for all of her clips, renders with back faces culled, in-game crouch on both sides, `perf_flame` on `2c993b0` and `0c8a9f5`, the battery |
| Ashka's thighs through her coat (2026-11-09) | Measured with the posed meshes and seen in contrasting colours: the thighs passed through the coat's tails in deep leg poses because the tails were skinned to the pelvis and their own bones only. The cloth in front of and beside each thigh now follows it by up to 70% (upper half most, fading toward the hem) | `Tools/Blender/characters/{eh_ashka.py,characters.json}` (`tail_thigh_follow`, `tail_thigh_reach`), `Content/Characters/Ashka/SK_Ashka.uasset` | bones identical (88), renders in contrasting colours before and after (crouch, front kick, knee, roundhouse, flying knee), the crouch in game on both sides before and after, the blocking review, the battery |
| Ashka's coat tails as cloth (2026-11-09, at the creator's go-ahead) | The tails hang from 12 columns of three bones (three per panel; the front opening, slits and vent fall between columns), simulated together: lengths kept, neighbours within 50-112% of their bind spacing except across the openings, a bending term, capsules round thighs and calves (front columns leave a thigh on their own side, so the front panel rides on a raised thigh), the front top bones leaning after the thighs through mid-thigh helpers, per-segment hang limits (top 100°, lower 50°). Fixed on the way: both animation builds fed the thighs' follow constraint back into itself frame by frame (part follows became full ones; loops began with the coat settling). The coat and clothes textures ship from the mesh's own build (the UV packer differs between builds; `8c22521` paired them wrongly) | `Tools/Blender/anim/{animlib.py,mocap.py}` (`_step_coat_grid`, `_hang_grid`, `_leg_push`, `author`, `bake_tracked`), `Tools/Blender/characters/{eh_ashka.py,characters.json}` (`GRID_COLUMNS`, `coat_rig`, `rest_chains`), `Content/Characters/Ashka/` | 130 bones (88 unchanged, 42 added; a rebuild from `rest_chains` reproduces them), renders in contrasting colours before and after from three sides, the crouch in game on both sides, every clip's hem motion (no pops), clip audit, blocking and flame reviews, the battery |
| Default controls (2026-11-09) | The creator chose the usual fighting-game layout (MK-style): up jumps (no jump button), Cross / A Special, L1 / LB Throw, R2 / RT alone Block, R1 / RB and L2 / LT free; W and the Up arrow alone jump on the keyboards. Settings format 5: actions still on their version-4 defaults move, the player's own changes stay, a move that would take a player's button is undone and named; the migrated file is written back once at start-up | `Game/EHSettings.*` (`Defaults`, `DefaultsV4`, `Load`), `EHGameDirector.cpp` (`BeginPlay`), [Controls](Controls.md) | `bindings_selftest` (101), `input_selftest` (44), `controls_remap` / `controls_persist`, simulated pads, the creator's own settings file over two launches |

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
  saturated eyes in neutral light); her bangs look comb-like up close; since 2026-11-09 her ponytail is strand cards
  over a soft core and her shirt follows the bust (no coat); under a bright key her blacks read charcoal (in the
  chapel they read black). Wren's wraps are fixed geometry, not cloth. Triangle counts
  rose 16% (Wren) and 26% (Ashka). Two character builds give identical geometry but not byte-identical files
  (Blender's UV island packer varies; textures differ by at most 8/255).
- **A light wedge under Ashka in her crouch** was a coat panel catching the moonlight; the coat is gone since
  2026-11-09.
- **Ashka's away moves take over away + Light / Heavy for her.** Holding away while pressing Light gives the front kick,
  not the jab (walking back and jabbing is no longer possible for her; Wren is unchanged). Like down + Light, away +
  Light pressed during a string's cancel window continues the string (the move matrix shows it).
- **The spinning elbow's audit disposition:** the elbow point leads the turn at about 36 cm/f at contact, which trips
  the flip test; frames 11-16 were checked (forearm folded, no plane flip). Judge it in the footage
  (`evidence/ashka-1109/footage`).
- **The ponytail and the shirt are fixed geometry**: the ponytail is spring-simulated like the braids were; the shirt
  does not simulate cloth. The ponytail hangs a little off the back at rest because its chain keeps the braid's rest
  pose (the coat was under it).

## 4. Open

- Owner playtest of the new mechanics, art and feel (checklist in [Status](Status.md)).
- Independent review of this candidate.
- Controllers: automated checks used simulated Xbox and DualShock 4 pads. The creator then played `5d5c316` (the
  earlier layout) with a Bluetooth DualShock 4 and reports it works (no per-button log; two earlier attempts logged
  no press because the pad sent nothing; Validation, "Physical DualShock 4"). The 2026-11-09 layout has not been
  played with a physical controller.
- Frame times at the native 3440 × 1440 match the previous release, except one 0.4 s burst of slow frames (worst
  32.8 ms) in one of three candidate captures, cause not found, not repeated (Validation, "Frame times").
- Before/after footage of the art and jump scripts against release `309c87c`, with phone copies, is listed in
  Validation, "Monitor-bound runs".
- Ashka's refinement: nobody has played it; with the CPU on both sides Ashka beats Wren 60 of 96 (63 before her new
  moves; Hard against Hard 22 of 24), a lean that predates this work and that the round did not address.

## 5. Commit structure

Eleven commits on `ea3ddc6`: combat core and data with tests (`a8cc695`), controls, Lesson and presentation
(`4fc8704`), motion for the new moves (`96275a9`), the move matrix and contract prose (`cf675e1`), the Lesson punish
step (`61badfc`), the clip audit and its fixes (`c6de32d`), the audit table and production notes (`5dfe4c2`), README
and research (`c425f4e`), controls tests (`f11f04e`), the character art (`8677cb2`) and the imported meshes and
rebuilt clips (`5d5c316`), then documentation of the results. On 2026-11-09: the fighting-game control layout
(`1b714fd`) and the settings write-back (`32831cc`), then documentation; then Ashka: the character generator
(`01ce31a`), the moves, CPU and tests (`31914ba`), the keyed clips and the clip audit (`8c943d5`), the imported
content (`730a169`) and the docs (`2c993b0`), then documentation of the results; then Ashka to her sheet's version 2:
the character painter's part sampling (`7a1fe65`), the generator (`f3dfa92`), the flame lighting her coat's lining
(`d23854f`), the imported content (`b06b019`) and the public canon (`c6c0de2`), then documentation of the results;
then the blocking animations: the guards and the solver (`42e943c`) and the rebuilt clips (`0c8a9f5`), then
documentation of the results; then the coat tails kept off the legs, with the flame review and flame perf scripts
(`e08d8a0`), and the reimported clips (`108455a`), then documentation of the results; then the coat following the
thighs (`8c22521`), then documentation of the results; then the coat's tails as cloth (`77ea4ac`) and the reimported
skeleton, mesh, textures and clips (`84acb66`), then documentation of the results.

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
