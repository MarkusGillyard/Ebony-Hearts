# Independent review: the creator's playtest round

This guide is for reviewing the latest commit on `release/first-slice` (pull request #1): the work on the creator's
playtest of package `pkg-60` (2026-11-04/05). It sits on top of the commits the creator had already reviewed. Each
step, with its measurements, is in the [validation report](Validation.md) (packages `pkg-61` to `pkg-67`); rules and
move data are in the [combat contract](CombatContract.md).

**Build under review:** package `pkg-67-jumpkick` (Shipping, Linux), built from this commit's game code and content;
everything changed after it is documentation and tests. The release archive's name and SHA-256 are in the pull
request description. On that package the smoke test, controls self-tests, 25-step journey and 12-match matrix all
passed with 0 failures and 0 warnings (see the validation report).

## 1. What was asked and what changed

The creator's requests, in their priority order, plus a later note on necks, wrists and fists.

| Request | What changed | Where | Verified by |
|---|---|---|---|
| Punches and elbows look like the arm never extends; no range | Punching arms straighten by IK to 172-180 degrees on their active frames (captured boxing jabs stop at 134-150). Wren's jab is Mixamo's longest jab; Ashka's elbows and Wren's spinning elbow reach their boxes | `Tools/Blender/anim/mocap.py` (`straighten`), `build_mocap.py`, `mocap_clips.json`, `moves.py` (Wren's spinning elbow) | Elbow angle and reach measured at contact; review video (punches from near full reach) |
| More realistic reactions to contact | A hit names its defender's reaction clip (`react` in the fighter data): hooks turn the head away from the side they land on, body shots fold the body, Ashka's body kick crumples toward the kicked side. Reactions open on their impact pose during hitstop instead of holding the guard | `Source/EbonyHearts/Core/EHCombatData.*`, `EHMatch.*` (`reactMove`, `reactHit`), `Game/EHFighterVisual.cpp`, `Content/Data/Fighters/*.json`, `mocap_clips.json` | Core test `hit_reactions_name_their_clip`; head direction measured toward the attacker; smoke test reports no missing animations |
| Necks, wrists and fists bend unnaturally | Arm IK had kept each hand's captured world angle while it moved the forearm (fists cocked 20-160 degrees). A final pass keeps fists within 12 degrees of the forearm (open hands 30), thumbs wrap the fingers, necks bend at most 30 degrees off the chest (42 in rolls, falls and get-ups) | `mocap.py` (`limit_wrists`, `limit_neck`), `animlib.py` (`THUMB_WRAP`), `build_mocap.py`, `build_anims.py` | `build_mocap --joints` prints every clip's worst wrist and neck; `--closeup` renders hands and head |
| Moving and striking with Wren feels disjointed | The legs settle over their own blend time (to about the strike's first active frame) and a far planted foot lifts, so a strike from a walk finishes the step instead of skating 15-26 cm. Wren's idle keeps less foot shuffle. Guard hands turn with the chest | `Game/EHAnimInstance.*`, `EHFighterVisual.*` (`LegBlendSeconds`), `stances.json`, `mocap.py` (`apply_stance`) | Pose gaps measured walk-to-strike; review video (movement into strikes) |
| Ashka looks robotic and stiff | Body kick and teep are Mixamo captures (rear-leg roundhouse, lead-leg thrust kick); her strikes keep more of the guard hand's motion | `mocap_clips.json` | Review video (Heavy and toward + Heavy) |
| Add jumping | Up jumps straight up, toward or away; fighters have a height; no block or grab in the air and any air hit knocks down; pushboxes still apply; light and heavy jump attacks (heavies captured); the CPU anti-airs and jumps in. Jump action on W, Up arrow, D-pad up and the left stick's up | `Core/EHMatch.*`, `EHCombatData.*`, `EHAI.*`, `Content/Data/rules.json` (`jump*`), fighter data (`JL`, `JH`), `Game/EHSettings.*`, `EHInputRouter.cpp`, `EHFighterVisual.cpp`, `EHDirectorUI.cpp` | Three jump core tests and the CPU match test; controls self-test (D-pad up); review video (jumps and jump-ins) |

## 2. Check it yourself

- **Combat core.** From the repository root: `Tests/Core/run_core_tests.sh`. Expect 33 test cases and
  `630 checks, 0 failures`; the CPU test prints how often the CPU jumped, attacked from the air and was anti-aired.
- **Data.** Jump values are the `jump*` keys in `Content/Data/rules.json`; jump attacks are the `air` moves `JL` and
  `JH` in each fighter file; reactions are the `react` keys on hits. `python3 Tools/Docs/move_tables.py` regenerates
  the contract's move tables and should leave them unchanged.
- **Packaged build.** The release archive and its checksum are listed above. Launch the game and, for the automated
  suites, add `-EHAuto=Tests/Auto/<script>.txt -EHEvidence=<dir>` (see [Production](Production.md)): `smoke.txt`,
  `controls_selftest.txt`, `journey.txt`, `matrix.txt`. Each run writes `auto_log.txt`; a pass has no `FAIL` and no
  `WARN` lines.
- **Motion.** `Tests/Auto/review_reactions.txt`, `review_flow.txt` and `review_jump.txt` reproduce the review videos
  in Training. Record with `Tests/Auto/capture.py record "Ebony Hearts" out.mp4 <seconds> --fps 60 --start-on
  <evidence dir>/auto_log.txt:match_start`, which starts on the first match so two builds' recordings line up.
- **Animation sources.** The raw motion capture (Mixamo exports, ACCAD takes) and the Blender character files stay
  outside the repository (licence and size), so the clips cannot be rebuilt from this repository alone. The imported
  clips are in `Content/Characters/*/Anims`; every capture used is listed with its hash in
  [ThirdPartyManifest.json](ThirdPartyManifest.json) and the [asset ledger](AssetLedger.md).

## 3. Where to look closely

- **Jumping changes the simulation.** New state (`FState::Jump`, `Landing`), fields (`y`, `vy`, `jumpFrame`,
  `jumpDir`, all in the state hash) and input (`InputFrame.y`). Boxes rise with the height (`Match::WorldBox`). A hit
  on a fighter in the air sets the knockdown through the existing airborne rule; the arc stops and the body falls.
  The determinism test covers the new fields.
- **The CPU.** Two new tuning values per level (`antiAirPct`, `jumpPct`); the jump-in and anti-air logic is in
  `CpuController::Decide`.
- **Presentation only.** The per-hit reaction, the leg blend and step lift, the lift of a jumping fighter and its
  floor marker never feed back into the simulation.
- **Global animation passes.** The wrist and neck limits apply to every captured clip; a wanted extreme pose would
  be flattened (per-clip `wrist_max` and `neck_max` override them). Guard hands of one-shot clips are now measured from
  the clip's first frame (an anchor-name bug had used the clip's average), which shifts every guarded strike's guard
  hand slightly.
- **Reactions need every clip on every fighter.** A reaction plays on the defender. `build_mocap` refuses to build a
  fighter missing one; `pkg-62` shipped with that gap and its smoke test caught it.

## 4. Open decisions and what is not verified

- **For the creator to decide by feel.** Jump height, timing and distances, and the jump attacks' frame data, are
  first values. Jumps cannot cross over the opponent and there is no crouch or low attack; both are design choices
  left open.
- **Still keyed by script.** Wren's spinning back elbow, Ashka's Flame Burst and clinch, the grabs, the back rolls
  and the light jump attacks. No capture searched so far fits them.
- **Not verified by a person.** The latest build has not been played (the creator played `pkg-60`); physical
  controller buttons; a listening pass. Soak and performance were not re-run since the original release. A rare
  startup crash (about one launch in 30-40) is in the engine's Linux audio backend, before game code runs.

## 5. Commit structure

The pull request's commits are squashes of the local working history: the slice, then one commit per review round.
The latest commit is this playtest round. The local history (which includes an early commit with Python bytecode
caches) is not published. Nothing has been merged, tagged or released; that needs the creator's go-ahead.
