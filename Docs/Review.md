# Review guide: creator playtest round (2026-11-07)

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

## 1. What changed and where

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

## 2. Check it yourself

- **Core.** `Tests/Core/run_core_tests.sh`: 44 cases, `890 checks, 0 failures`. Set `heldBlockStopsJumpIns` to `true`
  or `jumpInHitAdvantage` to `0` in `rules.json`, remove the `airAttackUsed` check in the jump state, apply the landing-relative stun to every jump attack
  (drop `opensContact`), or let the CPU see jumps only after its full reaction delay, and a new test fails.
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

- The creator played this candidate on 2026-11-07. They later identified combat smoothness and jumping feel as needing
  refinement; the character models are acceptable placeholders that need more work. On 2026-11-08 the creator clarified
  that these are ongoing, nonblocking improvements and should not determine this review's merge-readiness verdict.
  Merging itself is not authorized.
- Not verified: hardware other than the test machine; Wayland sessions.
- The animation sources (raw captures, `.blend` files) are outside the repository, unchanged from earlier rounds.

## 5. Commit structure

Eight commits on top of the previous head `22fa565`: combat rules and tests (`80e57fa`), game layer (`d3548d7`),
animation (`bb4823b`), documentation and move notes (`d1ede0e`), a stronger jump-in test (`37d6ab4`), the CPU's
anti-air (`b445999`), the repurposed buttons (`d2f7cb7`) and the jump-in loop fix (`4cee9c1`), plus documentation of
the results. Earlier history is
unchanged; nothing has been merged, tagged or released.

## 6. Independent PR audit (2026-11-08)

This section records a new review of PR #1, not the engineer's acceptance report above. The live starting head was
`0965ff285d391948c192bd447a586b77d3bc23bd`; the base and merge base were both
`9a34d030281f3321d41ac64e8a065f8a0336b6dc`. At that point GitHub reported the PR open, cleanly mergeable,
with 51 commits, 514 changed files and two passing core checks. There were no open review threads or approvals.
The original source candidate was `4cee9c1`; the later commits up to the starting head changed documentation only.

### Coverage and issue ledger

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

### Evidence and limits

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

### Repaired-package qualification and verdict

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
