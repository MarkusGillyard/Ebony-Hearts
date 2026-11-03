# Validation report

Status of the first playable slice against the acceptance matrix. Each result names the evidence behind it. Evidence
files (logs, screenshots, footage, frame-time captures, resource samples) are kept in the delivery workspace's
`evidence/` folder, outside this repository. The final release's runs are under `evidence/rc-f3ae5ab/<run>`.

## Build identity

| Item | Value |
|---|---|
| Source | branch `dev/slice-foundation`, commit `f3ae5ab` (local; not pushed). Later commits change documents only. |
| Release archive | `EbonyHearts-Slice-f3ae5ab.tar.gz`, SHA-256 `57886ee502edaf2482939b9d0282cf5d357f6577a3e14436c3264082ff064d74` |
| Content hash | `6bd8b055dfa8ac0477bc8b7ff27d5cc8ce86e07841dbc18d4566c0adbd1878b3`: SHA-256 over the pak files, also in the release's `VERSION.txt` |
| Engine and configuration | Unreal Engine 5.8.4 (installed build), Shipping, Linux x86-64, Vulkan SM6. The cook covered 760 packages with 0 warnings and 0 errors. |
| Test machine (FLOWBOX) | AMD Ryzen 7 5700G, 14 GB RAM, NVIDIA GeForce RTX 2060 6 GB (driver 595.99.02), Linux Mint 22.3 (kernel 7.0.0-42), Cinnamon on X11, one 3440 × 1440 165 Hz DisplayPort monitor |

The release was set up for testing in four steps:
- It was extracted from its archive into a new directory whose path contains spaces.
- Every file was checked against `EbonyHearts-Slice-f3ae5ab.files.sha256`.
- Every packaged test below ran from that copy through its own `EbonyHearts.sh`, with the editor closed.
- The first launch used an empty user profile.

The archive contains no symbolic links. Debug symbols stay with the original package and are not shipped.

## Acceptance matrix

| Gate | Result | Evidence |
|---|---|---|
| Scope | **PASS** | The package and repository contain exactly Wren Ku, Ashka Rook and The Drowned Chapel. Content folders: Audio, Chapel, Characters/{Wren, Ashka, Shared}, Data, Maps/DrownedChapel, UI, VFX. There are no other fighters, stages or legacy assets, and no Grandmaster. |
| Canon | **PASS** (self-audit) | **Wren:** brown double braids, ocean-blue eyes, black and ocean-blue kit, 5'10" scale, the 720 Hook Kick, and Spirit Enhanced Strikes as a golden lightning aura. **Ashka:** crimson braid with bangs and two face strands, crimson eyes, white shirt, black tie and pants, brown loafers, long black trench coat, the crimson cross-shaped lamp tattoo on her chest (mostly covered by her shirt), and her crimson Lamplighter Flame. Gameplay proposals are listed as such and unknown lore is left unresolved (`Docs/CombatContract.md`). Evidence: `characters/lineup_front.png`, `*_face.png`, `ashka_tattoo_check.png`, `rc-f3ae5ab/signature`. This is a self-audit, not a creator review. |
| Controls | **PASS** for keyboard and virtual gamepad; physical gamepad **NOT_VERIFIED** | All six actions on both fighters and both sides (`matrix`, `signature`, `journey`). Keyboard verified both through the router and with real X11 key events (`xinput`). Gamepad verified with a virtual Xbox 360 pad, including disconnect, takeover and resume (`vpad-*`). Rebinding, prompts and pause were exercised. A physical PS4 controller was detected, but nobody pressed its buttons. |
| Combat | **PASS** for automated tests; feel **NOT_VERIFIED** | The core suite passes: 26 cases, 257 checks, 0 failures. That includes a randomized search finding no route longer than 5 hits, and identical replays at 30-240 Hz. The 12-match matrix completed 12/12 matches with 0 failures or stuck states. No human has judged route usability or counterplay. |
| Character quality | **PASS** with stated limits | Finished rigged meshes with materials and LOD1, 32 animations each (moves, reactions, throws and paired victims), and spring-simulated braids, strands and coat. The signature kick, golden aura and crimson flame were inspected in packaged footage (`signature.mp4`, `review.mp4`). Limits: script-built from a MakeHuman base, with modest close-up detail and occasional coat clipping in spins. |
| Chapel quality | **PASS** | 39 meshes, 299 instances and 358k triangles. The fighting strip is clear, the rose-window moonlight falls behind it, and the candles, wet floor and water sheen work. Camera and collision are stable across 12 + 36 matches. Ambience bed and music play. Evidence: `review`, `footage_contact.jpg`. |
| Player journey | **PASS** | In the packaged build: Versus CPU, local Versus, Training, Lesson, results and rematch, settings (saved and reloaded), move list, credits and quit (`journey`, 24/24 screen checks, `matrix`, `soak`). |
| Audio/visual usability | **PASS**; listening **NOT_VERIFIED** | The HUD, callouts, banners and move list are readable at 1080p and 3440 × 1440. Interface scale, reduced flashes and reduced shake are applied and survive a save/reload (`journey`, `soak`). Their visual effect was not separately reviewed. No debug or placeholder output appears in the package. Sounds play at runtime with none missing (10144 sounds played in the soak). Nobody listened to the mix. |
| Performance | **PASS** | Packaged on FLOWBOX at 1920 × 1080 and at the native 3440 × 1440, both at 100% render scale. Frame-time medians are 16.67 ms with V-Sync and p99 stays under 17 ms. There are 0 frames over 33 ms across the release's captures. VRAM peaks around 1009 MiB at native resolution (of 6 GB), and engine memory is about 1.5 GB (of 14 GB). Startup to the title screen takes about 2.3 s. See Performance. |
| Stability | **PASS** | Matrix: 12/12 complete matches with 0 failures. Soak: 52 minutes, 36 complete matches with rematches, pauses, 12 settings save/reload round trips, Training and menu transitions; 0 failures or stuck states, 0 warnings; clean exit. Resident memory 1494 MiB in the first tenth and 1504 MiB in the last (peak 1511), with no sustained growth. VRAM peaked at 1040 MiB total. `matrix`, `soak` (`resources.csv`). |
| Assets/rights | **PASS**; title-card rights to be confirmed | Every shipped third-party input is CC0 or OFL (`Docs/AssetLedger.md`, `ThirdPartyManifest.json`). The package carries `THIRD_PARTY_NOTICES.txt` and the in-game credits. No ripped, paid, non-commercial or unclear-licence material is used. The creator-supplied title card's origin and rights are for the creator to confirm. |
| Reproducibility | **PASS** | Exact commit, content hash and archive checksums are recorded. The rebuild order is in `Docs/Production.md`. Every asset is rebuilt by scripts in this repository, and editable sources are kept in the workspace. The clean-directory launch from a path with spaces succeeded. |
| Preservation | **FAIL** (one historical incident, disclosed) | Legacy checkouts stayed read-only and untouched. Every write went to the task drive through a sandbox. No recursive cleanup ran, and no symbolic-link fixtures were made. However, early in the work the Unreal Editor crashed once and its crash reporter sent one report to Epic Games (2026-11-03 05:17 UTC) before an opt-out was set. Such reports usually contain the engine log, machine details and a minidump, which include project file paths. No further reports were sent. |
| Final review | **PASS** (self-review) | Requirements were checked against the final build's evidence. The material findings were all fixed and retested: lighting, mirrored-mesh culling, prompts, hitches and the settings leak. Remaining limits are listed below. This pass was carried out by the same agent that built the slice, so it is a self-review, not an independent one. |

## Test results

### Combat core

`Tests/Core/run_core_tests.sh`: 26 test cases, 257 checks, 0 failures. The required combat cases are covered:
- both fighters on both sides
- buffering during hitstop and recovery
- held versus pressed buttons
- facing after side switches
- duplicate-hit prevention
- block versus throw
- dodge vulnerability and recovery
- simultaneous hits and throws
- corners and throw release
- combo legality and bounds
- no infinite or unbounded combos
- KO, timeout and draw
- reset
- malformed-data rejection with useful errors
- identical replay hashes with the simulation driven at 30, 60, 75, 144, 165 and 240 Hz with frame-time jitter

### Packaged runs (release f3ae5ab)

| Run | What it exercised | Result |
|---|---|---|
| `perf-cold` | First launch on a fresh profile; the first match from its start | Pass. |
| `smoke` | Title, menu, CPU match, asset report | Pass: no missing assets. |
| `journey` | Every menu through device presses: Versus CPU select and difficulty/side, pause, move list, Training (options, hitboxes, grab, reset), Lesson, local Versus on one keyboard, Settings (audio, accessibility, video, bindings), settings save/reload, credits, quit confirmation | Pass: 24/24 screen checks, settings save/reload and launch-flag isolation verified. |
| `xinput` | Real X11 key events (XTest): title, menus, a fight with walk/light string/heavy/block/grab, pause, quit through the menu | Pass. The game quit itself through the confirmation. |
| `vpad-menu-and-fight` | Virtual Xbox 360 pad (uinput): menus, select, fight inputs with every action, pause, quit | Pass. |
| `vpad-disconnect` | The same pad destroyed mid-fight and recreated: notice, takeover, resume, quit | Pass. The disconnect and reconnect were logged; the new device took the slot. |
| `signature` | Training with the gauge always full: 720 Hook Kick, Spirit Enhanced Strikes and an aura strike, Flame Elbow, Flying Knee, Flame Burst; footage `signature.mp4` | Pass. |
| `review` | A full CPU match recorded from the package; footage `review.mp4` | Pass: 1 complete match. |
| `matrix` | 12 complete matches: both fighters, both sides, mirrors, CPU Easy/Normal/Hard, local versus on one keyboard | Pass: no missing assets, 12 complete matches. |
| `soak` | Repeated CPU matches with pauses, rematches, settings round trips, mirror versus matches, Training and menu transitions | Pass: settings save/reload and launch-flag isolation verified, no missing assets, 36 complete matches. |

Input evidence types are kept separate:
- **XTest key events:** real X11 input events, sent by a script.
- **Virtual pad:** a kernel-level virtual controller, not a physical one.
- **Physical PS4 controller:** connected and detected, but nobody pressed its buttons.
- **Bot-driven matches:** these feed decisions through the same device router as a keyboard.

No human playtest or listening test took place.

## Performance

**Method.** Captures ran in the packaged Shipping build on FLOWBOX:
- **Fight capture:** a 60 s sample of a bot-versus-CPU fight (Wren, bot Hard, against Ashka on CPU Hard), taken after
  a 20 s warm-up.
- **Menu capture:** a 20 s sample on the menus.
- **Cold capture:** the first match after a fresh-profile launch, from its very start (`perf_cold.txt`).
- **Resolutions:** 1920 × 1080 in a window, and the default launch (borderless at the desktop's 3440 × 1440). Render
  scale was 100% and quality High; there is no dynamic resolution.
- **Frame time:** recorded per frame by the game.
- **GPU time:** the engine's GPU frame timer.
- **1% low:** 1000 divided by the mean of the slowest 1% of frame times.
- **Hitches:** frames over 33 ms.
- **VRAM and memory:** total VRAM in use (from `nvidia-smi`, once a second) and the game's resident memory. The
  desktop's own VRAM use is recorded as a baseline.
- **Startup:** time from launch until the game's director is running (title screen).

| Capture | Viewport | V-Sync | Length / frames | Median ms | p95 | p99 | Max | 1% low fps | Hitches >33 ms | GPU median / p99 ms | Game / render thread ms | VRAM, run peak (game / total) | Engine memory, peak | Startup |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Fight, 1080p | 1920 × 1080 | on | 60 s / 3601 | 16.67 | 16.70 | 16.73 | 17.2 | 59.6 | 0 | 6.78 / 7.92 | 0.75 / 1.29 | 774 MiB (1052 total) | 1518 MB | 2.3 s |
| Menus, 1080p | 1920 × 1080 | on | 20 s / 1202 | 16.67 | 16.71 | 16.73 | 16.9 | 59.6 | 0 | 6.99 / 7.91 | 0.73 / 1.31 | 774 MiB (1052 total) | 1526 MB | 2.3 s |
| Fight, 1080p, no sampler | 1920 × 1080 | on | 60 s / 3601 | 16.67 | 16.71 | 16.74 | 17.5 | 59.5 | 0 | 6.88 / 8.35 | 0.81 / 1.27 | not sampled | 1509 MB | 2.3 s |
| Fight, 1080p | 1920 × 1080 | off | 60 s / 8112 | 7.30 | 8.25 | 8.60 | 10.0 | 114.4 | 0 | 6.84 / 8.27 | 0.62 / 1.21 | 752 MiB (1030 total) | 1536 MB | 2.4 s |
| Fight, native (default launch) | 3440 × 1440 | on | 60 s / 3602 | 16.67 | 16.73 | 16.76 | 17.0 | 59.5 | 0 | 9.99 / 10.97 | 0.81 / 1.31 | 1009 MiB (1287 total) | 1507 MB | 2.5 s |
| Menus, native | 3440 × 1440 | on | 20 s / 1202 | 16.67 | 16.73 | 16.77 | 17.2 | 59.2 | 0 | 9.85 / 11.14 | 0.78 / 1.34 | 1009 MiB (1287 total) | 1541 MB | 2.5 s |
| First match, cold first launch | 1920 × 1080 | on | 25 s / 1502 | 16.67 | 16.73 | 16.77 | 17.8 | 59.2 | 0 | 6.89 / 7.92 | 0.81 / 1.30 | 752 MiB (1030 total) | 1538 MB | 2.4 s |

Aura check with the default borderless launch (Training, `perf_aura.txt`; this was the launch whose window came up at 3440 × 1368): no aura 10s: median 16.67, max 16.8 ms, 0 hitches; aura 7s: median 16.67, max 16.8 ms, 0 hitches; aura2 7s: median 16.67, max 16.8 ms, 0 hitches.

**Reading the numbers.**
- **V-Sync pacing.** With V-Sync on, frames are presented at 60 Hz on this desktop, even though the monitor runs at
  165 Hz. The compositor paces windowed and borderless presentation at 60 Hz. Simulation timing is fixed at 60 ticks
  per second either way.
- **Headroom.** With V-Sync off, 1080p frames take a median of 7.30 ms (p99 8.60 ms), about 2.2× headroom over the 16.67 ms budget. The GPU
  takes 6.8 ms at 1080p and 10.0 ms at 3440 × 1440.
- **Investigated hitches.** Earlier candidates showed occasional 50 ms frames: 2-3 a minute at 1080p, and up to 9 a
  minute at 3440 × 1440, clustered at round transitions.
  - **Cause.** Slate was rasterising new large glyphs while the "ROUND"/"K.O." banners grew.
  - **Ruled out.** Control runs without the `nvidia-smi` sampler, and an aura on/off Training capture
    (`perf_aura.txt`), ruled out the sampler and the aura effect.
  - **Fix.** Banners now use one size, and the title screen pre-rasterises those glyphs.
  - **Result.** The final build shows 0 frames over 33 ms across all of its captures (worst frame 17.8 ms).

## Motion and visual review

Every move and reaction animation was reviewed in three ways:
- as frame sheets on the final rigs
- in the running game
- in packaged footage for the signature set and a full match

Defects found and fixed during review:
- lying poses with an arm raised toward the ceiling
- coat panels splaying, and coat or braid chains sinking through the floor
- an orange-yellow flame (now crimson)
- the golden aura reading too faintly, then too strongly (now a gold rim plus lightning bolts)
- fighters' materials swapping between matches
- the mirrored fighter drawing the inside of her mesh on the title screen
- stacked post-process volumes darkening the chapel
- menu prompt glyph spacing and device switching caused by stick drift
- selection tags overlapping long names
- round-banner hitches

## Known limitations

- **Not verified by a person:**
  - physical-controller buttons
  - feel and balance (no human playtest)
  - the audio mix (no listening test)
  - exclusive fullscreen mode switching (borderless and windowed were tested)
- **Art.**
  - The fighters are built by script from a MakeHuman base, so close-up detail (faces, hair cards) is modest.
  - Animation is keyed by script.
  - Coat panels can clip in the most extreme spins.
  - Only Wren's primary outfit is included.
- **Presentation.** At 60 Hz on the test desktop with V-Sync (see Performance).
- **Borderless window.** In 1 of 5 default launches, the borderless window came up constrained to the desktop work
  area (3440 × 1368, above the Cinnamon panel) instead of covering the panel. Play is unaffected.
- **Determinism and online.** Replays are deterministic for one binary on one machine. There is no rollback or online
  play.
- **Config noise.** `Config/DefaultEngine.ini` holds an editor-generated Android File Server block. It is unused (the
  plugin is not shipped).
- **History.** The local history includes an early commit that contained Python bytecode caches. A squashed branch is
  prepared for publication (see `Docs/Status.md`).

## Superseded and failed evidence (kept)

- **Earlier candidates.** These were built, verified and tested, then replaced:
  - `3ad0352`: title-screen mirrored mesh drawn inside out.
  - `684b18d`: prompt and selection-tag defects, and the same mesh problem.
  - `2caf501`: round-banner hitches, and launch flags persisting into settings.
  - `c10cac5`: residual banner hitches, and a test-harness key leak. Its full battery, including a 54-minute soak with
    36 matches and 0 failures, passed (`evidence/rc-c10cac5`).
- **Old journey script.** The first editor journey (`journey-editor-01`) used an outdated script that pressed the
  wrong menu items. It was stopped and the script rewritten.
- **Truncated footage.** A signature recording that outran the game window is kept as
  `rc-2caf501/signature/signature-truncated-failed.mp4`.
- **Dark lighting.** The chapel lighting regression is captured in `review-03`/`review-04`; the fix is in `review-05`.
- **Harness warnings.** The soak on `c10cac5` logged "router mismatch" warnings. These came from the test harness
  (bots' injected keys outliving their match), not from the game. The harness was fixed in `f3ae5ab`.
