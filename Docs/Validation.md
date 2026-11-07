# Validation report

Status of the first playable slice against the acceptance matrix. Each result names the evidence behind it. Evidence
files (logs, screenshots, footage, frame-time captures, resource samples) are kept in the delivery workspace's
`evidence/` folder, outside this repository. The current candidate's runs are under `evidence/rc-4cee9c1/<run>`, the
previous candidate's under `evidence/rc-060a75f/<run>` and the original release's under `evidence/rc-f3ae5ab/<run>`.

## Current candidate `4cee9c1` (2026-11-07, creator playtest round)

**Result: PASS on every objective check run; ready for the creator's next playtest.** This round answers the creator's
playtest of `060a75f` and their later request to repurpose Grab's buttons (see [Review](Review.md)). This is the
engineer's own verification, not an independent review, and nobody has played this build yet.

### Build identity

| Item | Value |
|---|---|
| Source | `4cee9c1` (a fast-forward of `release/first-slice` from `22fa565`), packaged from a working tree with no uncommitted code or data. Later commits change documentation only. |
| Release archive | `EbonyHearts-Slice-4cee9c1.tar.gz`, 326 476 000 bytes, SHA-256 `c5ad9309292571b400aae0aa215d8f66f945e4af6ad576527f171458f924f591` |
| Content hash | `6344d74d93d808fde3bd5148beae6f7cf26412e1e4fb7797e284582a8062d490` (SHA-256 over the pak files, in `VERSION.txt`) |
| Build | Unreal Engine 5.8.4, Shipping, Linux x86-64, Vulkan SM6. 830 packages cooked, 0 warnings, 0 errors. |
| Release check | Extracted into a new folder whose path contains a space; every file matched `EbonyHearts-Slice-4cee9c1.files.sha256`. |
| Test machine | FLOWBOX as described for `060a75f` below (32 GB RAM), with the 3440 × 1440 monitor only; the 4K TV the creator played on was disconnected again. |
| Superseded on the way | `d1ede0e`, `b445999` and `d2f7cb7` (same content; earlier CPU, controls and jump-in code). The `d1ede0e` battery was stopped after its controller runs (all passing) when the CPU anti-air problem below was found; `b445999` and `d2f7cb7` each passed the full battery; `d2f7cb7` was then found to allow a jump-in loop (below). All stay in the release folder; `d2f7cb7`'s results are in `evidence/rc-d2f7cb7`. |

### Results on the candidate

Evidence: `evidence/rc-4cee9c1/battery/<run>`. A pass has exit 0, no `FAIL` or `WARN` line, and the script's own
completion marker.

| Suite | Result | Notes |
|---|---|---|
| Combat core | **PASS** | 44 cases, 890 checks, 0 failures |
| Packaging safety, move tables | **PASS** | 9 tests; `move_tables.py` regenerates the contract unchanged |
| Smoke | **PASS** | No missing animations or sounds; platform check ok |
| Controls | **PASS** | `bindings_selftest` 92 checks (new layout, three buttons per action, a version-2 settings file migrated), `input_selftest` 33 checks (Cross / A jumps in the direction held, L1 / LB blocks), remap, persistence and Controls UI runs |
| Journey | **PASS** | 24/24 screen checks, then Quit through the menu (Training now jumps where it grabbed) |
| Real X11 keyboard | **PASS** | Title, menu, fight (including the I key, now jump), pause, quit |
| Simulated pads | **PASS** | Xbox 360 and DualShock 4 layouts: every button gave its action (Cross / A: jump, confirm in menus; L1 / LB: block); menu-and-fight, disconnect and reconnect, remapping with Swap |
| Matrix | **PASS** | 12/12 complete matches (both fighters, both sides, mirrors, all CPU levels, local versus), 4 099 sounds, no missing animations or sounds; memory 1 492 MiB at the end (peak 1 510) |
| Review scripts | **PASS** | `review_match`, `review_reactions`, `review_flow`, `review_jump`, `review_playtest`. Footage of `review_playtest` on `d2f7cb7` (the same moves and jump-in as this candidate; the loop fix does not change a jump-in that opens contact) and on `060a75f`, side by side and at half speed: `evidence/rc-d2f7cb7/before-after` (the jump-in hits through the held guard and the light string combos after it; on `060a75f` it is blocked) |
| Signature footage | **PASS** | aura and flame rendered |
| Frame times, 1080p windowed, V-Sync on | **PASS** | Fight 60 s: 3 602 frames, median 16.66 ms, p99 16.78, max 17.09, none over 33 ms, GPU median 7.4 ms; menu 20 s: max 17.02 |
| Frame times, default borderless 3440 × 1440 | **PASS** | Fight 60 s: median 16.67 ms, p99 16.78, max 17.04, none over 33 ms, GPU median 10.7 ms; menu 20 s: max 16.87 |
| First match from its start (cold) | **PASS** | 1 501 frames, median 16.67 ms, p99 16.78, max 16.87, none over 33 ms |

The battery's own `review_playtest` capture on this candidate is 38 s and playable (`review-playtest/review-playtest.mp4`).

Not re-run this round, because the code they cover did not change: the one-hour soak, display-mode changes, the monitor
standby probe and the start-up loops (`060a75f`, below). Every run above also started the game cleanly: 21 more starts.

### The new animations, measured

Per-frame joint positions and the checks below, before and after, are kept with the review handoff
(`review-handoff-20261107/anim/measurements`), with contact sheets of both versions in `anim/sheets`.

| Clip | Check | Before | After |
|---|---|---|---|
| Wren, Light 3 (spinning elbow), first active frame | right elbow, forward and height (hitbox x 10-88, y 120-162 cm) | elbow 83 cm out, 130 cm up, below the fist (146 cm), which sat behind her head (renders) | elbow 85 cm out, 139 cm up, 16 cm ahead of the fist |
| | fast or flipping joints (`speeds.py`, `flips.py`) | rear foot 42 cm in one frame (frames 4-5) | none |
| | hand-over into and out of the idle (`transitions.py`) | 1 cm / 0 cm | 1 cm / 0 cm |
| Ashka, Heavy (Body Roundhouse), active frames 16-18 | kicking shin (hitbox x 28-130, y 85-140 cm) | foot forward, body square: a front kick | knee 55 cm out at 100-106 cm, ankle 92-99 cm out at 98-109 cm: the shin level at body height |
| | standing foot | | ball held at 26-27 cm (no slide) |
| | fast or flipping joints, hand-over | no fast joints; 2 cm / 0 cm | none; 3 cm / 0 cm |

### Jumping and the CPU

**A loop found while preparing the review (fixed in `4cee9c1`).** On `d2f7cb7`, after a jump-in hit, jumping again on the
first free frame and attacking on the way up hit before the defender recovered, and each hit renewed the "until the
jumper lands, plus 12" stun: a probe chained 29 hits to a KO, against a standing or a block-holding defender, with either
fighter. The landing-relative stun now applies only to a jump attack that opens contact. `jump_ins_cannot_loop` searches
re-jump routes (toward, up and away; light or heavy at jump frames 5-30; 60-200 cm; standing and blocking defenders):
the longest is 2 hits, 18 on the old code within the test's limits.

A scripted player who does nothing but jump in (toward from mid range, Heavy at the top, a light string on landing)
against each CPU level, 24 matches per level (unchanged by the loop fix; mirrored with the player on the right: Normal
51%, Hard 63%), simulated with the game's own `CpuController` (`Tests/Core` has the
regression check, `cpu_anti_airs_jump_ins`):

| CPU | Jump-in player wins, `22fa565` | now | Jump-ins knocked out of the air, `22fa565` | now |
|---|---|---|---|---|
| Easy | 24 / 24 | 24 / 24 | 14% | 12% |
| Normal | 22 / 24 | 19 / 24 | 18% | 51% |
| Hard | 0 / 24 | 5 / 24 | 64% | 64% |

The Normal CPU used to see a jump only after its full 18-frame reaction delay, when the jump attack was already out.
Normal against Easy, CPU against CPU, wins 19 / 24 (19 / 24 before), and Hard still wins every match against Normal.
Endless jumping still beats Easy and Normal, as it did before this round, because a landed jump-in combo is worth far
more than the jab that anti-airs it; Hard handles it.

## Candidate `060a75f` (2026-11-07, start-up crash round; superseded by `d2f7cb7`)

**Result: PASS on every objective check run; ready for the creator's playtest.** This is the engineer's own
verification of the objective gates, not an independent review, and the creator has not yet played this build. The creator played it on 2026-11-07 (TV, PS4 controller); the current candidate answers that playtest.

### Build identity

| Item | Value |
|---|---|
| Source | `060a75f021693e69acc784585c63a64ee6be47d6` on `release/first-slice` (built from a fresh worktree of that commit, with its LFS content verified). Later commits change documentation only. Base `main` `9a34d03`. |
| Release archive | `EbonyHearts-Slice-060a75f.tar.gz`, 326 474 292 bytes, SHA-256 `06b34f4a09d5c46f850f5d61c642c737d4a8bcdc98032ac5843f206805ba618f` |
| Content hash | `ab51dcadf855e96f685afbe453c4bdb3ad64726286474331e5894eb6ad786481` (SHA-256 over the pak files, in `VERSION.txt`) |
| Build | Unreal Engine 5.8.4 (installed build, CL 58902052), Shipping, Linux x86-64, Vulkan SM6. 823 packages cooked, 0 warnings, 0 errors; code compiled without warnings. A Development package of the same commit was built for diagnosis. |
| Release check | 21 files, no links, no symbols (`.debug`/`.sym` stay with the package); the archive and every extracted file were checked against `SHA256SUMS` and `EbonyHearts-Slice-060a75f.files.sha256` after extracting into a new folder whose path contains spaces. The package contains no crash reporter, so nothing is uploaded; crash dumps stay local. |
| Test machine (FLOWBOX) | AMD Ryzen 7 5700G, **32 GB RAM** (upgraded from 16 GB on 2026-11-05; earlier results were measured with 16 GB), NVIDIA GeForce RTX 2060 6 GB (driver 595.99.02), Linux Mint 22.3 (kernel 7.0.0-42), Cinnamon 6.6 on X11 (Muffin), PipeWire 1.0.5 with the PulseAudio interface, one Samsung LC34G55T 3440 × 1440 165 Hz monitor on DisplayPort with HDMI audio from the GPU. The desktop turns the monitor off after 5 minutes idle. A DualShock 4 (054c:09cc) was connected over Bluetooth. |

### Results on the candidate

All packaged runs below used the extracted release through its own `EbonyHearts.sh`; the battery's first run started
from an empty user profile. Evidence is under `evidence/rc-060a75f/battery/<run>`. A pass has exit 0, no `FAIL` or `WARN` line, and the
script's own completion marker.

| Suite | Result | Notes |
|---|---|---|
| Combat core (`run_core_tests.sh`) | **PASS** | 37 cases, 828 checks, 0 failures (at `060a75f`, clean worktree) |
| Packaging safety (`Tests/Package`) | **PASS** | 9 tests |
| Move tables regenerate unchanged | **PASS** | `Tools/Docs/move_tables.py` |
| Smoke | **PASS** | No missing animations or sounds; `platform_check` ok (game audio output live, start-up prime dropped, display guard on) |
| Controls self-tests, remap, persistence, controls UI | **PASS** | 4 runs |
| Journey | **PASS** | 24/24 screen checks, then Quit through the menu |
| Real X11 keyboard (`xinput_drive.py`) | **PASS** | Title, menu, fight, pause, quit |
| Simulated pads (`virtual_pad.py`) | **PASS** | Xbox 360 and DualShock 4 layouts (every button, R2/RT hold and release), menu-and-fight, disconnect and reconnect mid-match, remapping with Swap. The physical PS4 controller was detected as `PS4 Controller`, PlayStation; its buttons were not pressed |
| Matrix | **PASS** | 12/12 complete matches (both fighters, both sides, mirrors, all CPU levels, local versus), 3 865 sounds |
| Review scripts | **PASS** | `review_reactions`, `review_flow`, `review_jump`; `review_match` played 150 s of a Hard-versus-Hard match without failures (a footage script: it returns to the menu at 150 s, before this match ended) |
| Signature footage | **PASS** | 720 frames recorded; golden aura and crimson flame rendered |
| Display modes after start-up | **PASS** | 21/21 `window_check` (fullscreen, borderless, windowed) |
| Monitor standby during a mode change | **PASS** | 5/5 `display_hotplug_probe`, each disconnect held back inside SDL's fullscreen call; 10 events deferred and replayed |
| Soak | **PASS** | 57.7 minutes, 36 complete matches, 12/12 settings save-and-reload round trips, Training and menu transitions; 0 failures, warnings or stuck states; clean exit. Game memory 1 503 → 1 513 MiB (first and last tenth of the run, peak 1 521); VRAM about 1.0 GB throughout |

**Performance on the candidate** (1920 × 1080 unless noted, 100% render scale, the default High quality; frame
times from every frame of each capture, GPU time from the RHI; resources sampled once a second):

| Capture | Frames | Median | p95 | p99 | Max | Frames > 33 ms | GPU median / p99 | Peak VRAM (game + desktop) | Peak game memory |
|---|---|---|---|---|---|---|---|---|---|
| Fight 60 s, windowed, V-Sync on | 3 601 | 16.67 ms | 16.71 | 16.73 | 16.94 | 0 | 6.11 / 6.90 ms | 1 078 MiB | 1 500 MiB |
| Menu 20 s, windowed, V-Sync on | 1 202 | 16.67 | 16.69 | 16.71 | 16.96 | 0 | 6.43 / 6.83 | | |
| Fight 60 s, windowed, V-Sync off | 8 431 | 7.06 | 7.71 | 8.11 | 9.29 | 0 | 6.71 / 7.45 | 1 056 MiB | 1 530 MiB |
| Menu 20 s, windowed, V-Sync off | 2 827 | 7.02 | 7.52 | 7.66 | 47.63 | 1 | 6.77 / 7.60 | | |
| Fight 60 s, `-fullscreen` 1920 × 1080 | 3 602 | 16.67 | 16.72 | 16.75 | 17.02 | 0 | 9.52 / 9.81 | 1 313 MiB | 1 570 MiB |
| Fight 60 s, default borderless 3440 × 1440 | 3 601 | 16.67 | 16.72 | 16.75 | 16.98 | 0 | 9.40 / 9.78 | 1 408 MiB | 1 539 MiB |
| First match from its start (cold) | 1 502 | 16.67 | 16.73 | 16.77 | 17.02 | 0 | 6.73 / 8.49 | 1 007 MiB | 1 511 MiB |
| Training with the golden aura, 3440 × 1440 | 422 | 16.66 | 16.71 | 16.73 | 16.77 | 0 | 9.45 / 9.66 | | |

The single long frame (47.6 ms) came 17 s into an idle menu capture with V-Sync off; that frame's GPU time was 7.3 ms,
so the stall was on the CPU side; its cause was not identified, and no other capture on the candidate had a frame over
17.1 ms. Start-up to the title screen took 2.2-2.8 s. On Linux the engine draws both fullscreen modes as a
desktop-sized window, so `-fullscreen` at 1920 × 1080 on this 3440 × 1440 monitor costs as much GPU time as the native
resolution. V-Sync paces at 60 Hz on this desktop (see Known limitations).

### EH-07: start-up crashes (two causes), diagnosis and fix

The historical start-up crashes had two unrelated causes, both outside the game's code. Each was reproduced on demand,
fixed in the game's chosen path, and checked by the same binary with and without the fix.

**Evidence kept.** The three game crash dumps still held by `systemd-coredump` were copied out with their SHA-256 before
rotation (it had already removed older editor dumps): `pkg-45-strings` Shipping (fullscreen, 2026-11-04 15:17),
`dev-crashhunt` Development (fullscreen, 15:34) and `pkg-48-victim` Shipping (**windowed** 1920 × 1080, 18:24, not
previously recorded). The packages' `.debug` files symbolize them.

**Cause 1: SDL frees the display its own fullscreen call is using (X11).** The `pkg-45` dump faults on the game thread
in `X11_SetWindowFullscreenViaWM` (SDL 3.4.4, `SDL_x11window.c:1897`), called from `SDL_UpdateFullscreenMode`
(`SDL_video.c:2021`) and `FLinuxWindow::ReshapeWindow`. The `SDL_VideoDisplay` it reads had been freed: its first
16 bytes hold a glibc tcache entry and its internal data pointers are cleared, as `SDL_DelVideoDisplay` leaves them, and
SDL's display list then held only the fallback "Generic X11 Display". The function reads the display's data, then,
while an earlier window request is still outstanding, waits for the window manager (`X11_SyncWindow`), which pumps X
events. When an XRandR output-disconnect event is queued, SDL removes the display there and the function continues with
freed memory. A DisplayPort monitor reports itself disconnected when it goes to standby and reconnected when it wakes;
on the test machine that happens through the desktop's screen-off timer, and SDL's own screensaver reset wakes the
monitor when the game starts. The same code is still in SDL's main branch.
- **Fix** (`Source/EbonyHeartsLinux`, `EHDisplayEventGuard`): an SDL X11 event hook holds XRandR events back and
  re-queues them for an event pump the game runs at the start of the next frame, when no window call is in progress.
  Display changes still apply, one frame later.
- **Reproduction** (`display_hotplug_probe`, `Tests/Auto/display_hotplug.txt`): queue an output disconnect for the
  window's monitor, leave a window move outstanding, and enter fullscreen through `FLinuxWindow::SetWindowMode`. On one
  Development binary, 3 of 3 runs with the guard disabled crashed in `X11_SetWindowFullscreenViaWM` with the same freed
  display; with the guard, 15 of 15 probes passed and the real monitor came back after each simulated wake.
  On the candidate: 5/5 probes on the Shipping release, and the candidate's Development package crashed 3/3 without
  the guard and passed 3/3 with it (see the trials below).

**Cause 2: the engine's SDL audio output writes through a stale pointer into SDL's audio thread.** The two other
dumps (Development fullscreen, Shipping windowed) are identical: SDL's audio thread jumped to address 0 inside
`PULSEAUDIO_PlayDevice` → `pa_stream_write` after returning through a zeroed stack slot. (The "null read in libc"
earlier recorded was the signal-return trampoline in the crash handler's backtrace, not a libc fault.) In UE 5.8.4's
`AudioMixerSDL`, the SDL callback allocates its output buffer on the SDL thread's stack (`SDL_stack_alloc`), stores the
pointer, and never clears it; `SubmitBuffer` copies 12 288 bytes into that pointer. The mixer also calls `SubmitBuffer`
from other threads: the render thread primes the stream once when it starts, and the null-device thread and device
swaps do the same. Run under gdb with the engine's output, an off-thread `SubmitBuffer` wrote to the 12 KB directly
below the SDL audio thread's stack pointer. That memory is unused while the thread waits, and holds live return
addresses while it is inside `pa_stream_write`, which is where both dumps stopped. Writes in steady play survived
(3 × 3 848 repeated submits); the fatal case is the start-up prime meeting the first writes to PulseAudio.
- **Fix** (`Source/EbonyHeartsLinux`, `FSdlAudioOutput`, selected in `Config/Linux/LinuxEngine.ini`): the game's own
  SDL3 output renders each SDL request into a buffer it owns and drops submissions made from any other thread. Output
  format and mix are unchanged (5.1 float at 48 kHz, converted by SDL). Every start drops exactly one submission, the
  render thread's prime (`platform_check ... dropped=1`).
- **Comparison:** with the game's output the repeated off-thread submits were all dropped and audio kept playing.

**Related display defect (P2): borderless window clamped to the work area.** Starting straight into borderless failed
4 of 4 on one Development build: the window manager had no fullscreen state for the window (`_NET_WM_STATE` without
`_NET_WM_STATE_FULLSCREEN`), so it was a decorated window clamped to the work area (3440 × 1368 at y = 32). The engine
sets the mode while SDL's window is still hidden and SDL applies it when the window is shown; that request is lost.
A second request after the window is up fixes it, which is why launches that changed resolution during start-up did
not show the problem. Two changes: the engine's start-up display now always follows the saved settings (it used to keep
whatever the last session ran in, including launch-flag test runs, because the engine saves its settings on exit), and
half a second after each display change the game checks that a fullscreen or borderless window covers its monitor and
repeats the request through the engine's reshape path if it does not (at most twice). `window_check` in every start-up
loop reports the result. On the candidate every borderless start (30 default, 10 after 20 windowed runs, 10 first
runs) needed exactly one re-request and then covered the monitor; fullscreen starts with launch flags and every mode
change after start-up covered it without one.

### Start-up and display trials on the candidate

Every attempt ran `Tests/Auto/launch_quit.txt` through `Tests/Auto/launch_loop.py` (one launch at a time, 1.5 s
apart; evidence under `evidence/rc-060a75f/loops`, `standby` and `ab`). Each start had to exit 0 after the script's
quit, pass `platform_check` and `window_check`, and leave no game process behind.

| Trial | Build | Starts | Result | Notes |
|---|---|---|---|---|
| Exclusive fullscreen 3440 × 1440 | Shipping | 100 | 100 clean | |
| Exclusive fullscreen 1920 × 1080 | Shipping | 100 | 100 clean | |
| Default (saved borderless) | Shipping | 30 | 30 clean | every start needed one fullscreen re-request |
| Windowed 1920 × 1080 | Shipping | 20 | 20 clean | |
| Default, after the windowed runs | Shipping | 10 | 10 clean | all started borderless: the launch flags did not change the saved mode |
| First run, empty profile each time | Shipping | 10 | 10 clean | borderless, one re-request each |
| `-safedisplay` | Shipping | 10 | 10 clean | 1280 × 720 window |
| Exclusive fullscreen 3440 × 1440 | Development | 100 | 100 clean | |
| Fullscreen launch right after forcing the monitor into standby (`xset dpms force off`) | Shipping | 5 | 5 clean | each start's wake-up delivered 2-4 real XRandR output events, held back and applied at the start of a frame; within the 30 s waited, X still listed the output as connected |
| **Total** | | **385** | **385 clean** | 0 crashes, 0 timeouts, 0 leftover processes; every start dropped exactly one off-thread audio submission (the render thread's prime) |

The loops ran with the monitor awake, so they exercise the audio race under the original conditions but not the
display defect, which needs a monitor event during the fullscreen call; the probe and the standby launches cover that.
With the historical rate (1 in 26 to 1 in 40 starts) unchanged, 380 loop starts would have been expected to crash
about 10 to 15 times; no crash is strong evidence against the old rate, not proof that no rare crash remains.

**With and without the fixes, on the candidate's Development package** (same binary; evidence `evidence/rc-060a75f/ab`):

| Check | Without | With |
|---|---|---|
| Monitor standby during a fullscreen change (`display_hotplug.txt`, 5 probes a run) | `-EHNoDisplayEventGuard`: 3/3 runs crashed in `X11_SetWindowFullscreenViaWM` ← `SDL_UpdateFullscreenMode` ← `FLinuxWindow::SetWindowMode` | 3/3 clean |
| Off-thread `SubmitBuffer`, repeated for 8 s (`audio_offthread.txt`) | engine `AudioMixerSDL` (`-ini` override): survived; steady-state writes land in unused stack, and the fatal overlap is the start-up prime meeting the first PulseAudio writes (dumps and gdb above) | game output: all 3 840-3 848 submits dropped, audio kept playing |

**Other start-up and device checks on the Shipping release:**
- **Focus loss.** With the walk key held, focus moved to another window, the key was released there, and focus came back:
  the game released the walk when focus left (1.5 s after the press, before the real key-up), so nothing stayed held
  (`evidence/rc-060a75f/focus`).
- **Audio devices.** The game's stream was moved to a temporary output and back; the default output was switched to that
  output while playing and the game's audio followed it; the temporary output was then removed and the stream returned
  to the HDMI output. Buffers kept flowing throughout (2 621 in 28 s, about 94 a second), and the default output was
  restored (`evidence/rc-060a75f/audio-device`). This checks delivery to the output, not audible sound: the test
  monitor's speakers do not work.
- **Crash reporting.** The package has no crash reporter; nothing was uploaded.

#### Issue register (this round)

| ID | Sev. | Location | Evidence | Root cause | Change | Regression | Status | SHA |
|---|---|---|---|---|---|---|---|---|
| EH-07a | P1 | SDL 3.4.4 `X11_SetWindowFullscreenViaWM` (engine third-party) | `pkg-45` Shipping dump; freed `SDL_VideoDisplay` (tcache entry), generic display left | Display removed by an XRandR disconnect processed inside SDL's own fullscreen call | XRandR events deferred to a frame-start pump | `display_hotplug.txt`; guard off 3/3 crash, on 3/3 pass (candidate); 5/5 probes on Shipping | Fixed | `7b7f42f` |
| EH-07b | P1 | UE 5.8.4 `AudioMixerSDL` (engine) | Development and Shipping dumps, SDL audio thread at PC 0 in `pa_stream_write`; gdb: write at sp−12336..sp−48 of that thread | Stale pointer to an `alloca` buffer written from other threads | Game-owned SDL3 output | `platform_check` `dropped=1` per start; `audio_offthread.txt` | Fixed | `7b7f42f` |
| EH-08 | P2 | Start-up display (`EHGameDirector`, engine `PreExit` save, SDL show) | Borderless starts 4/4 decorated at 3440 × 1368+0+32; `_NET_WM_STATE` lacks fullscreen | Fullscreen request for a hidden window is lost; the engine saved the live session display on exit | Engine ini kept on saved settings; coverage check and one re-request | `window_check` in every loop; `display_modes.txt` | Fixed | `f7ae2ef` |
| EH-09 | P2 | Release staging | Link found mid-copy left a partial release; an existing archive would be overwritten; VERSION said Shipping for any build | Checks ran during copying | Whole-package checks first; exclusive creation | 9 package tests | Fixed | `f6187d8` |
| EH-10 | P3 | Hash test coverage | One field perturbed (Sol's test) | Coverage asserted by reading code | Per-field perturbation test, size guards | `state_hash_covers_every_field` (fails with one field removed) | Fixed | `2401cc9` |
| EH-11 | P3 | Timeout throw tests | One boundary, one thrower | — | Before/on/after, both throwers, next round | `timeout_throw_boundaries_both_sides` | Fixed | `2401cc9` |
| EH-12 | P3 | `Docs/CombatContract.md` | Prose named a belly-to-belly suplex | Pre-`pkg-44` wording | Corrected | — | Fixed | `060a75f` |
| EH-13 | P3 | Current-candidate docs and PR text | README/Status/Review named `f3ae5ab`/`pkg-67`/630 checks as current | Not updated after the last review | Rewritten for `060a75f`; history labelled | — | Fixed | docs commit |
| EH-14 | P3 | `Tools/Blender`, `Tools/Audio` defaults | Fallback paths name the development machine's Blender | Asset pipeline written on one machine | Not changed: overridable (`BLENDER`, `EH_BLENDER`); asset rebuild needs private inputs anyway | — | Open, disclosed | — |


## Original release `f3ae5ab` (2026-11-03, historical): build identity

| Item | Value |
|---|---|
| Source | branch `dev/slice-foundation`, commit `f3ae5ab` (local; not pushed). Later commits change documents only. The same files are published as `release/first-slice`. |
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

## Original release `f3ae5ab` (historical): acceptance matrix

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
| Performance | **PASS** | Packaged on FLOWBOX at 1920 × 1080 and at the native 3440 × 1440, both at 100% render scale. Frame-time medians are 16.67 ms with V-Sync and p99 stays under 17 ms. There are 0 frames over 33 ms across the release's captures. VRAM peaks around 1009 MiB at native resolution (of 6 GB), and engine memory is about 1.5 GB (of 14 GB). Startup to the title screen takes about 2.3 s. See Performance. Re-run on the build under review (2026-11-05): medians 16.67 ms, p99 at most 16.78 ms, 0 frames over 33 ms. |
| Stability | **PASS** | Matrix: 12/12 complete matches with 0 failures. Soak: 52 minutes, 36 complete matches with rematches, pauses, 12 settings save/reload round trips, Training and menu transitions; 0 failures or stuck states, 0 warnings; clean exit. Resident memory 1494 MiB in the first tenth and 1504 MiB in the last (peak 1511), with no sustained growth. VRAM peaked at 1040 MiB total. `matrix`, `soak` (`resources.csv`). Re-run on the build under review (`EbonyHearts-Slice-3602345`, 2026-11-05): 12/12 matrix; a 59-minute, 36-match soak with 0 failures and flat memory. |
| Assets/rights | **PASS** for the recorded inputs | Shipped third-party inputs include CC0 and OFL assets, ACCAD motion under CC BY 3.0, and Mixamo motion under Adobe's terms (`Docs/AssetLedger.md`, `ThirdPartyManifest.json`). The package carries `THIRD_PARTY_NOTICES.txt` and the in-game credits. On 2026-11-05, 89/89 local original-download files matched the manifest SHA-256 values; this does not prove the full asset rebuild. The creator-supplied title card is AI-generated (OpenAI ChatGPT image generation) and was confirmed as an authorized project asset on 2026-11-03 (`Docs/AssetLedger.md`). |
| Reproducibility | **PARTIAL** | Exact commit, content hash and archive checksums are recorded; the clean-directory launch from a path with spaces succeeded. The rebuild order is in `Docs/Production.md`, but raw motion captures and editable character files are external to this repository. A full asset rebuild requires those recorded inputs and was not independently reproduced from this checkout. |
| Preservation | **FAIL** (one historical incident, disclosed) | Legacy checkouts stayed read-only and untouched. Every write went to the task drive through a sandbox. No recursive cleanup ran, and no symbolic-link fixtures were made. However, early in the work the Unreal Editor crashed once and its crash reporter sent one report to Epic Games (2026-11-03 05:17 UTC) before an opt-out was set. Such reports usually contain the engine log, machine details and a minidump, which include project file paths. No further reports were sent. |
| Final review | **PASS** (self-review) | Requirements were checked against the final build's evidence. The material findings were all fixed and retested: lighting, mirrored-mesh culling, prompts, hitches and the settings leak. Remaining limits are listed below. This pass was carried out by the same agent that built the slice, so it is a self-review, not an independent one. |

## Test results (original release and later rounds, historical)

### Combat core

`Tests/Core/run_core_tests.sh`: 33 test cases, 630 checks, 0 failures (26 cases and 257 checks at the original
release). The required combat cases are covered:
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
- per-hit reaction keys recorded on the defender, and malformed ones rejected
- jumping: the arc, squat, landing and distances in all three directions; no block or grab in the air; the anti-air
  knockdown and the fall; jump attacks hitting, blocked and landing into recovery; the CPU jumping in, attacking from
  the air and being anti-aired

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


### Re-run on the build under review (2026-11-05)

The release under review (`EbonyHearts-Slice-3602345`, the `pkg-67-jumpkick` build), extracted to a fresh folder, on
the same machine and method as above (1920 × 1080 window, V-Sync on; evidence `anim-107`):

| Capture | Frames | Median ms | p95 | p99 | Max | 1% low fps | Hitches >33 ms | GPU median / p99 ms | Game / render thread ms | Engine memory, peak |
|---|---|---|---|---|---|---|---|---|---|---|
| Fight, 60 s | 3602 | 16.67 | 16.71 | 16.74 | 17.2 | 59.6 | 0 | 6.86 / 8.32 | 0.76 / 1.36 | 1455 MB |
| Menus, 20 s | 1202 | 16.67 | 16.71 | 16.73 | 16.9 | 59.6 | 0 | 6.76 / 7.90 | 0.73 / 1.37 | 1460 MB |
| First match, cold first launch | 1502 | 16.67 | 16.71 | 16.74 | 16.8 | 59.7 | 0 | 6.87 / 7.94 | 0.75 / 1.35 | 1538 MB |
| Training, no aura / aura / aura again | 602 / 422 / 422 | 16.67 | 16.72 | 16.74-16.78 | 17.7 | 58.6-59.6 | 0 | 6.91-6.99 / 8.15-8.76 | 0.75-0.90 / 1.33-1.44 | 1541 MB |

The game's dropped-tick counter read 13-32 at the end of each capture; it counts from launch, so these come from
loading (no captured frame was long enough to drop a tick). VRAM in use during the fight peaked at 1026 MiB.

**Soak** (`soak.txt`, with the resource sampler): 59 minutes, 36 complete matches with rematches, pauses, settings
round trips, versus and Training; 49 checks passed, 0 failures, 0 warnings, no missing assets. The game's resident
memory held flat (median 1541 MiB in the first quarter, 1542 MiB in the last, peak 1551); VRAM stayed at 1023-1026 MiB.

**Full match** (`review_match.txt`, recorded for review, `anim-108`): Wren as a Hard bot against Ashka on CPU Hard, two
complete rounds (Ashka won 2-0), 0 failures and 0 warnings.

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

## Changes after the release

These commits are on `dev/slice-foundation` only. They are not in the `f3ae5ab` release or in pull request 1. Each was
packaged (Shipping) and tested on FLOWBOX. Evidence is in the workspace's `evidence/` folder.

### Controls (package `pkg-12-controls`)

The controller layout and remapping are described in `Docs/Controls.md`.
- **Self-tests.** 57 binding checks and 30 input-router checks passed: swap, replace, clear, reset, conflicts, the
  version 1 settings migration, trigger thresholds and hysteresis, and the double-press guard.
- **Automation through the real input path.** Remapping passed 20/20 checks and persistence across a restart 9/9 on
  the previous controls package, `pkg-11-controls` (`controls-01`). The menu flow passed 6/6 with 18 screenshots on
  both packages (`controls-01`, `controls-02`). `pkg-12` fixed controller button names, a trigger double press and the
  test profile; the remap and persistence runs were not repeated on it.
- **Simulated controllers.** These were created through the Linux uinput system: an Xbox 360 pad (045e:028e) and a
  DualShock 4 (054c:05c4). They covered the default layout, menus and a fight, disconnect and reconnect, and remapping
  from the pad itself. **No physical controller buttons were pressed.** The creator's PS4 controller was detected as
  a PlayStation pad, and that is all.
- **Regression.** The smoke test, the 25-step journey, the xinput drive and the 12-match matrix all passed, with 0
  failures and 0 warnings.

### Stances and motion capture (package `pkg-14-stances`)

- **What changed.** Wren's MMA stance and Ashka's Muay Thai stance were researched and built (`Docs/Research.md`,
  "Fighting stances"). Both idles now come from ACCAD motion capture placed on those stances, and every scripted move
  shares the same stance values.
- **Review.** Blender frame renders, then in-game captures compared with the previous package. Evidence: `stances-02`
  (`stances_before_after.mp4` and a half-speed copy).
- **Defect found and fixed.** In the first stance build (`pkg-13`), both fighters' upper arms were level with their
  shoulders, so the elbows stuck out. The crouch had lowered the shoulders while the hand targets stayed at a fixed
  height. The hand targets are now solved from the measured shoulder positions. Wren's rear elbow sits 26–31° below
  the shoulder and her lead elbow 14° below; Ashka's elbows sit 10–15° below.
- **Regression.** The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed,
  with 0 failures and 0 warnings. Evidence: `stances-03`.

### Animation realism pass

After the stances, the creator found the movement still unnatural: kicks looked like an action figure, with no
transitions between moves.
- **Transitions.** Moves used to cut over with a 25–50 ms crossfade from a frozen pose. They now use inertial
  blending (`EHAnimInstance`). The new move starts on its first frame at once, so combat timing is unchanged, and the
  difference from the pose on screen eases out over a time set per state: 50–150 ms into strikes (within the startup),
  60 ms into hit reactions, and 220 ms back into stance.
- **Motion capture.** The following now come from ACCAD capture:
  - Wren's roundhouse and spinning back kick.
  - Wren's 720 hook kick and tornado kick: a spinning hook kick and a roundhouse, with a jump, an extra full turn in
    the air and a tucked support leg added (`mocap.add_air`).
  - Ashka's jab, body kick and teep. The teep's landing foot steps back to stance (`mocap.settle_feet`).
  - Ashka's horizontal elbow: a rear hook with the forearm folded so the elbow lands (`mocap.fold_limb`).
  Each is timed so contact falls on the move's first active frame. Kicks keep their captured knee direction and toe
  angle while the foot is off the floor.
- **Scripted moves.** These no longer stop at every key pose. Smooth segments follow a monotone cubic through the
  keys, so motion flows through a key unless the limb reverses there (`animlib.sample`). The knockdown now buckles
  at the knees, sits down and rolls onto the back instead of falling like a plank.
- **Tried and dropped.** A knee strike built from a captured front kick raised the thigh far too high. Ashka's
  knees stay scripted.
- **Review.** Frame sheets of every new move, and in-game before/after footage: `kicks-01` (checkpoint sent to the
  creator) and `anim-01`: every move for both fighters, with the training partner taking the hits, before
  and after, also sent to the creator.
- **Regression.** The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed
  on `pkg-16-anim`, with 0 failures and 0 warnings. Evidence: `anim-02`. The kick checkpoint `pkg-15` also passed
  (`kicks-02`).

### Animation realism, second pass

The creator reviewed the first pass and found every category still off. The reasons given: too fast or jerky, stiff
or robotic, limbs bending or twisting wrong, and floaty or weightless. The creator approved slower timing.
- **Natural speed.** Captured moves were playing 2.5–4× faster than captured to fit their frame data. Eight moves were
  retimed so the motion plays near 1.5×:
  - Wren's roundhouse, startup 12 → 16.
  - Wren's spinning back kick, 15 → 21.
  - Wren's 720 hook kick, 26 → 35.
  - Wren's tornado kick, 13 → 17.
  - Ashka's body kick, 11 → 16.
  - Ashka's teep, 9 → 16.
  - Ashka's jab and elbow: longer recoveries; startups unchanged.

  Every frame range in each move was remapped (hits, cancels, travel, airborne, invulnerability, hurtboxes). Travel
  speed was rescaled so distances are unchanged. Block and hit stun grew with each recovery, so advantage on block and
  on hit is unchanged for every move (`Docs/CombatContract.md`). Two design properties held the limits:
  - The tornado kick still combos after the cross (startup 17 is the slowest that does).
  - A back roll's recovery is still punishable by the roundhouse. Both back rolls are 4 frames longer, which also
    suits a real roll's speed.

  The combat core tests pass (257 checks). One test that assumed the roundhouse's old startup was rewritten relative
  to its hit frame.
- **Posture and guard.**
  - The ACCAD retarget copied that skeleton's steep collarbone slope, so the shoulders read as hunched or shrugged.
    Collarbones, neck and head are now calibrated against ACCAD's neutral standing take. The collarbone slope is set
    by the stance (−3°), with the captured shrugs kept around it.
  - During strikes the hand that isn't striking stays at the guard (`guard` in `mocap_clips.json`) instead of copying
    the performer's dropped guard.
- **Knees and joints.**
  - The stance's knee direction now turns with the hips, so spinning moves no longer buckle the standing knee
    inward.
  - Both characters have new shoulder and hip half-joints (`eh_rig.HALF`). Each sits on the joint and turns half as
    far as the limb's swing, and skin around the joint blends through it. A raised arm or a high kick now bends the
    shoulder and hip round instead of folding them. The builders key the half-joints exactly; the maths was checked
    on the rig to 0.000° across twisting poses.
- **Weight and follow-through.**
  - Jumps land with the hips sinking about 7 cm and recovering while the feet stay planted.
  - Scripted moves have the chest trailing the hips by one frame and the head by two.
  - Light hit reactions snap harder.
- **Downloaded but not used yet.** 21 further CMU takes (get-ups, dive rolls, knee strikes, a female fighter's kicks
  and blocks), 33 MiB, approved by the creator. The game's get-up is 21 frames, about 14× faster than a captured
  get-up, so those moves need a timing decision before capture can help.
- **Review and regression.**
  - Both characters were rebuilt and reimported (meshes, materials, LOD1 and 32 animations each) and packaged as
    `pkg-18-realism`.
  - Every move was recorded before and after (`anim-04`, sent to the creator).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-05`).

### Mixamo motion (package `pkg-19-mixamo`)

The creator found the second pass better, but every group still looked off. The creator chose Mixamo as the
animation source and exported 31 clips from their own Adobe account. Mixamo's FAQ says its animations are royalty
free for commercial projects, including video games (`Docs/AssetLedger.md`). The raw exports stay outside the
repository.
- **Pipeline.** `build_mocap.py` reads Mixamo FBX clips through the same position-aimed retarget as the BVH takes
  (`mocap.FbxSource`). It calibrates against the X Bot T-pose. Clip changes:
  - A time-warp change applies to every clip. Anchors such as the contact frame are now joined by monotone cubics
    rather than straight lines, so playback speed changes smoothly through them instead of jumping.
  - Reactions can set their own pace: explicit anchors give a fast impact and a slower recovery.
  - A clip can be layered onto a scripted pose (the block reaction rides on the guard) or end in one (the knockdown
    settles into the lying pose the get-up starts from).
  - A fall's travel can be shortened.
- **Feet.** The stance layer read foot heights after moving the pelvis to the stance height. So any difference
  between the performer's hip height and the stance lifted or sank both feet: Ashka floated about 2 cm in her idle
  and up to 4 cm in new clips, and Wren's lead foot sank about 1 cm. Feet now keep their captured height above the
  floor, put on each fighter's own ankle height. The fix applies to every captured move.
- **Moves now from Mixamo.**
  - Wren: roundhouse (MMA high kick), spinning back kick, walks (boxing step-drag), intro (warm-up) and win (victory).
  - Ashka: step-in knee, body kick, flame elbow (a stepping elbow, its dip reduced to suit her upright stance) and
    walks; her walks were keyed by script before.
  - Both: light and heavy hits, block, knockdown and KO.
  - The game's frame data is unchanged. Startup and recovery play about 1.5–2× the captured speed. The knockdown plays
    about 2.5× to land inside the 42-frame knockdown, and the KO plays near natural speed.
- **Not used.** Some clips can't fit the current frame data:
  - The captured jab and elbow take 2.4–4× longer to land than the 4–5-frame startups.
  - The get-up takes 8.4 s; the game's get-up is 20 frames.
  - The flying knee and the forward roll travel about 4 m.
  - The two throws take about 3.5 s; the game's throws take 56–64 frames.

  These stay as they were (CMU, ACCAD or script) until their timing is decided.
- **Review and regression.**
  - Every clip was reviewed frame by frame in Blender. Both characters' animations were reimported (32 each) and
    packaged as `pkg-19-mixamo`.
  - The same move script was recorded on `pkg-18-realism` and the new build, side by side (`anim-06`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-07`).

### Rotation transfer and natural timing (package `pkg-20-carry`)

The creator found every group still off: stiff or robotic, limbs bending or twisting wrong, and floaty. Too fast or
jerky was no longer on the list. The creator approved longer move timing where capture needs it.
- **Rotation transfer.** The position-aimed retarget rebuilt each bone's twist from hinge planes. That lost:
  - the head turning on the neck;
  - the feet rolling;
  - the forearm rotating;
  - the spine's own twist.

  It could also flip a straight limb's twist. Mixamo and ACCAD clips now carry their joints' recorded rotations
  (`aim.AimRetarget.carry`). Each bone starts from the aim's frame on the source's neutral pose and turns as its
  source joint turned. Bone directions match the aim to within 0.1° (limbs 0.0°). Twist differs by up to 60° on feet
  and calves and up to 50° on the head: the motion the aim dropped. The elbow stays a hinge:
  - The upper arm and forearm keep the hinge-plane roll, because the two skeletons' forearms rest rolled 41° apart.
  - The hand points where the performer's hand points and takes the performer's forearm rotation.
- **Timing (creator-approved).** Advantage on hit and block is unchanged.

  | Move | Startup / total | Now from |
  |---|---|---|
  | Wren's jab | 5/15 → 7/17 | CMU, about 1.2× captured speed |
  | Wren's cross | 6/19 → 8/23 | CMU, about 1.2× captured speed |
  | Ashka's jab | 5/18 → 8/24 | Mixamo |
  | Ashka's horizontal elbow | 6/26 → 9/30 | Mixamo |
  | Get-up | 20 → 60 frames (`rules.json`) | Mixamo get-up |

  The get-up blends out of the lying pose the knockdown ends in and finishes on the fighter's spot.
- **Core tests.** 257 checks pass. Three tests were updated to follow the data:
  - The invalid-hit test's pattern follows the jab's new frames.
  - The strike-beats-grab test presses the jab earlier by the difference in startup, so both still land on the same
    tick.
  - The loss-of-control bound scales with the get-up (200 + 2 × get-up frames, the same 240 as before for the old
    get-up). The worst random run is now 306 ticks.
- **Seen in review.** Ashka's coat panels follow her thighs, so while she sits during the get-up and the knockdown they
  stand out stiffly instead of draping.
- **Review and regression.**
  - All captured clips were rebuilt and reimported (32 animations per fighter) and packaged as `pkg-20-carry`.
  - The move script was recorded side by side with `pkg-19-mixamo` (`anim-08`, encoded to play on phones).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-09`).
  - The creator has not judged this build yet.

### Coat and captured takedown (package `pkg-21-throws`)

- **Coat.** Ashka's coat tails follow her thighs through rig helpers. When she sat with her knees up, the helpers
  stood the tails up like boards. Each tail's target now swings at most 70° from hanging straight down
  (`animlib._hang`). The spring simulation drapes it from there, so sitting tails lie on the floor and kick flares stay
  within reason. The limit applies to every scripted and captured animation.
- **Double-leg slam.** Wren's forward throw now comes from Mixamo's paired takedown, attacker and victim
  (`build_anims.capture_throw`; `"throws"` in `mocap_clips.json`). Mixamo exports the two sides separately:
  - The victim is turned to face the attacker and shifted so the attacker's hands meet its knees over the grip
    (residual 4–6 cm).
  - The grip, the victim's landing and the end of the attacker's stand-up map to frames 1, 34 (the damage frame,
    unchanged) and the last frame.
  - Each body's travel is scaled so the victim lands near the throw's 120 cm landing point. The victim ends in the
    exact lying pose its knockdown starts from, and Wren ends back in her stance.
  - The throw lasts 74 frames instead of 56, for the stand-up; the creator approved longer throws. Damage, damage
    frame, landing and the victim's knockdown are unchanged. Core tests: 257 checks pass.
  - The other three throws stay scripted: Mixamo has no matching paired clips for them.
- **Review and regression.**
  - All animations were rebuilt (60 scripted and throw clips, 32 captured) and reimported (32 per fighter), and
    packaged as `pkg-21-throws`.
  - The move script was recorded side by side with `pkg-20-carry` (`anim-10`). The review's grab misses at that
    spacing, so a separate clip records the slam in the packaged game (`anim-10/takedown2`): grip, drive, landing,
    Wren standing, Ashka's knockdown and get-up.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-11`).

### Feet during transitions (package `pkg-22-footlock`)

- **Why.** Transitions are inertialized: every bone's leftover offset from the last shown pose decays to zero. The
  hips' and legs' offsets decay together, so a foot planted in both poses rode along with the hips for the length of
  the blend (0.05–0.22 s) and slid. This is one likely source of the floaty feel.
- **Change.** In `EHAnimInstance`, a foot that is on the floor in both the shown pose and the new animation (within
  3 cm of the reference ankle height, fading out by 10 cm) now eases in a straight line from where it was shown to
  where the new animation puts it, on the same decay curve. The leg reaches it with two-bone IK (`AnimationCore`),
  keeping its knee's bend, and the hip half-joint takes half the thigh's new swing as the animations key it. Feet in
  the air (kicks, knees, falls) are untouched.
- **Review and regression.**
  - The change compiled with no new warnings and was packaged as `pkg-22-footlock` (code only; animations
    unchanged).
  - The move script was recorded side by side with `pkg-21-throws` (`anim-12`). There were no leg pops or twisted
    knees.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-13`).
  - Not measured: how much sliding remains. That needs a person watching it in play.

### Strikes that land, a looser body (package `pkg-23-strikes`)

The creator's verdict on `pkg-22`:
- Wren's kicks improved a lot.
- Both fighters' punches look as if they aren't being thrown.
- Ashka's kicks and knees need much more work.
- Bodies still move without natural flexibility.

Changes:
- **Measured cause.** On the first active frame the striking part sat well short of its hitbox:
  - Wren's jab stayed at her guard, 55 cm out (hitbox to 78).
  - Wren's cross reached 58 cm (hitbox to 85).
  - Ashka's knee reached 28 cm (hitbox to 70).
  - Ashka's horizontal elbow came from the wrong part of its clip, the chamber, with the elbow 39 cm behind her.

  Kicks already reached (Wren 119 of 140 cm, Ashka 134 of 130).
- **Punches.**
  - Wren's jab and cross, and Ashka's jab, now come from Mixamo's boxing jab and cross. These are full-extension
    punches that step in; 50–70% of the step is kept.
  - Ashka's elbow uses the strike itself (frames 40–48 of its clip: the hips turn 36° with the elbow high).
  - Wren's jab is 8/20 (was 7/17) and her cross 9/24 (was 8/23), with advantage on hit and block unchanged.
- **Reach.** A new build step, `mocap.reach`, carries each strike into its hitbox on the active frames:
  - The hips move toward the target (up to 35 cm) with planted feet kept in place by leg IK, so the fighter steps or
    lunges in.
  - Arm strikes lean the spine for any distance left.

  Reach on the first active frame:
  - Wren: jab 0.71 m, cross 0.77 m.
  - Ashka: jab 0.64 m, flame elbow 0.68 m, knee 0.54 m, horizontal elbow 0.48 m (the lean is capped so she doesn't
    fold over).
- **Looser body.**
  - The hand that guards during a strike keeps 60% of the performer's motion (was 30%).
  - The idles keep more of their captured motion:
    - Wren: bounce 0.45, sway 0.7, hands 0.8, feet 0.6 (was 0.3/0.4/0.5/0.4).
    - Ashka: bounce 0.35, sway 0.6, hands 0.7, feet 0.5 (was 0.15/0.3/0.4/0.3).
  - The held guard is now the scripted guard pose with the motion of a captured MMA idle layered on, so it breathes
    and shifts weight instead of holding still.
  - Coat tails swing at most 50° from hanging (was 70°), so kicks no longer carry them out like boards.
- **Credits.** No move uses CMU motion capture any more, so its credit was replaced by a Mixamo courtesy line in the
  in-game credits and the notices, and CMU left the manifest.
- **Tried and dropped.** A forward roll from Mixamo's stand-to-roll clip turned out to be a flying dive with a flip.
  The forward roll stays scripted.
- **Review and regression.**
  - Every animation was rebuilt and reimported, and packaged as `pkg-23-strikes`.
  - The move script was recorded side by side with `pkg-22` (`anim-14`). In game, Wren's jab now extends with a
    step-in; the kicks connect as before.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-15`). Core tests: 257 checks pass.

### Ashka's body kick and teep (package `pkg-24-ashka`)

- **Body kick.** On `pkg-23` in game, Ashka's Mixamo kick moved like a straight-legged side kick. She leaned so far
  back on the follow-through that she looked off balance, and the coat fanned out flat behind her. Her body kick goes
  back to ACCAD's body roundhouse (Male2_G15). It now runs through the rotation transfer, which keeps the hip turn and
  the foot's roll that the old position aim lost. Side by side in review it reads as a Muay Thai roundhouse: she stays
  upright with her guard up, the shin rises into the target, and the coat hangs. It reaches 1.12 m on its first
  active frame (hitbox to 1.30 m).
- **Teep.** It now reaches further: 0.98 m against a 1.21 m target (hitbox to 1.45 m). The hips may move at most
  35 cm, and kicks get no lean.
- **Review and regression.**
  - Ashka's clips were rebuilt and every animation reimported, and packaged as `pkg-24-ashka`.
  - The move script was recorded side by side with `pkg-23` (`anim-16`). In game, the body kick lands on Wren's
    torso.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-17`).

### Follow-through, elbow and teep reach (package `pkg-25-flex`)

- **Follow-through.** In every captured clip the upper spine and neck now trail the body's turns by a frame, and the
  head by two (`mocap.overlap`: 30–35% of the lagging rotation). The torso bends through a motion instead of turning
  as one piece. This is a further step on the creator's note that the bodies lack natural flexibility; the captured
  motion still leads.
- **Reach.** Each strike can set its own reach limits:
  - Ashka's horizontal elbow may lean further and now reaches 0.56 m (target 0.58, was 0.48), with a committed lunge.
  - Her teep may carry the hips further and now reaches 1.13 m (target 1.21, was 0.98).
- **Safety.** At the creator's request, a Claude Code hook now refuses any command that would recursively delete or
  link anything on the storage drive (outside the repository; noted here for the record).
- **Review and regression.**
  - Both fighters' captured clips were rebuilt and every animation reimported, and packaged as `pkg-25-flex`.
  - The move script was recorded side by side with `pkg-24` (`anim-18`). There were no head or neck glitches.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-19`).
- **Tried and not used: a captured flying knee for Ashka.** Mixamo's flying knee covers the move's 1.26 m with a
  running take-off over about 0.7 s, but the game gives it 15 frames (0.25 s). On the hit frame the knee trails behind
  her unless the clip plays about 3× fast. With a startup of about 22 frames (total about 55) it would play near
  1.7×. That is a balance change to a special move, left for the creator to decide; the flying knee stays scripted.

### Captured bow, win and defeated (package `pkg-26-ceremony`)

- **Ashka's intro.** ACCAD's bow-to-ready take (Male2_D8, mirrored to her lead side like her idle): she brings her
  hands together, bows, then rises into her fighting stance. 121 frames, about 1.4× the captured speed.
- **Ashka's win.** The bow from ACCAD's walk-to-bow take (Male2_D7): hands together, a deep bow, then upright.
  121 frames, about 1.45×.
- **Both fighters' defeated pose.** ACCAD's ready-to-relax take (Male2_D4, mirrored): the guard drops and the body
  relaxes, then over the last 30 frames it settles into the scripted dejected slump, so the pose still reads as a
  loss. 91 frames, about 1.4×. Her braid flicks up as the slump settles in (the hair spring reacting).
- **Checked and not usable.** ACCAD's backfists don't spin (−8° of hip turn), so they can't stand in for Wren's
  spinning elbow. ACCAD's lying take holds still, so it adds nothing to lying down.
- **Review and regression.**
  - Both fighters' captured clips were rebuilt and every animation reimported, and packaged as `pkg-26-ceremony`.
  - The new clips were reviewed frame by frame in Blender (`anim-20/ashka_intro_win_defeated.jpg`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-21`).

### Captured flying knee (package `pkg-27-flyknee`)

- **Timing.** The creator approved lengthening move timing where captured motion needs it, keeping advantage the
  same. On that basis Ashka's flying knee went from startup 15 / total 41 to 24 / 52. The hits are now frames 24–26
  and the travel (still 1.26 m) is spread over frames 3–25. Block stun grew by 2 frames, so advantage on block is
  unchanged; the move knocks down on hit. All 257 core checks pass. It's one commit, so it is easy to revert if the
  creator prefers the old timing.
- **Motion.** Mixamo's jumping knee from part of its run-up (frames 9–48), which plays at about 1.5×:
  - Forward travel kept at 90% to match the game's 1.26 m, jump height at 45% so the knee lands inside the hitbox
    instead of a metre above it.
  - No stance layer: it dragged the airborne legs back. The move blends in from her guard instead.
  - The right knee drives up and forward on the active frames and reaches 0.46 m (hitbox 10–85 cm).
- **Review and regression.**
  - Ashka's clips were rebuilt and every animation reimported, and packaged as `pkg-27-flyknee`.
  - The move script was recorded (`anim-22`). In game she crouches, leaps and drives the knee into Wren's body; Wren
    is knocked down.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-23`). Move tables were regenerated.

### Flying knee combos after the jab again (package `pkg-28-fs22`)

- **What broke.** The startup of 24 cut a documented route: the combat contract says the flying knee ends strings, but
  Ashka's jab leaves 22 frames of hitstun, so a jab into the flying knee no longer combo'd. Jab, elbow, flying knee
  still did (27 frames of hitstun). No test covered the shorter route.
- **Fix.** Startup 22 / total 50, the slowest timing that keeps the route. Hits are now frames 22–24 and the travel
  covers frames 3–23. Advantage on hit and on block is unchanged. The take-off now plays at about 1.65× capture
  speed (1.5× before). On the hit frame the knee is 0.49 m ahead of her (hitbox 10–85 cm).
- **Test.** `example_combos_each_fighter` now also checks Light into toward + Special for both fighters (Wren's
  tornado kick links with 0 frames to spare). It fails on the startup-24 data and passes on the new data. All 259
  core checks pass.
- **Every other cancel route still combos.** The one exception is Wren's 720 Hook Kick (startup 35), which never
  combo'd from any string, by design.
- **Review and regression.**
  - Ashka's clips were rebuilt and every animation reimported, and packaged as `pkg-28-fs22`.
  - The move script was recorded side by side with `pkg-27` (`anim-24`). In game it looks the same as before, just
    quicker: she crouches, leaps and drives the knee into Wren's body, and Wren is knocked down. The training display
    reads startup 22.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-25`). Move tables were regenerated.

### Balanced teep and body kick (package `pkg-29-teep`)

- **What was wrong.** ACCAD's push kick (Male2_G17) skips about 0.5 m forward into the kick. The game's teep travels
  6 cm, so the retarget drops that step, and on the hit frame the foot was only 0.55 m out with the knee still
  chambered. The reach step then slid her hips 0.5 m forward over a planted support foot. On the hit frame her hips
  were 64 cm ahead of that foot with the torso upright: a lunge no one could balance, not a teep.
- **Fix (no gameplay change).** Two new reach options for kicks and knees (`mocap.reach`):
  - `skid` lets the support foot slide forward with the hips, the push-off skid real teeps have (here up to 12 cm).
  - `balance` leans the upper body back against the hips' shift past the support foot, so the chest stays over it.
- **Result.**
  - **Teep.** The hip push is capped at 0.3 m. On the hit frame the hips are 39 cm ahead of the support foot
    (the performer's own take has 21 cm), the head is back over the foot, and the foot is 0.93 m out (hitbox
    30–145 cm). She stands upright and leans back, with the knee up and the foot driving forward.
  - **Body kick.** Its hip push is only 7 cm, so it changes little: a slightly stronger lean back.
  - **Step-in knee.** Already balanced (the take leans back over the hips), so it is unchanged.
- **Trade-off.** At the teep's longest range the foot stops short of the opponent's body. Closing that gap
  naturally would need a gameplay change (forward travel with a matching hitbox, or a shorter hitbox), which is the
  creator's call.
- **Review and regression.**
  - The teep and body kick were reviewed frame by frame in Blender, before and after.
  - Ashka's clips were rebuilt and every animation reimported, and packaged as `pkg-29-teep`.
  - The move script was recorded side by side with `pkg-28` (`anim-26`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-27`).

### Stepping elbow and knee (package `pkg-30-steps`)

- **What was wrong.** The game carries Ashka 27 cm forward on her horizontal elbow and her step-in knee, but in
  both takes the performer stays on the spot. Her feet stayed planted while her body was carried forward, so the
  reach step pushed her hips past her front foot. On the elbow her rear foot came off the floor and she lunged with
  the back leg stretched out. On the knee her support leg trailed diagonally behind her.
- **Fix (no gameplay change).**
  - A new `steps` clip option: the named foot steps forward, lifted a little, and lands one travel ahead, so it is
    back under her once the travel ends. On the elbow the front foot steps on frames 2–7 and the rear foot follows
    on frames 6–12. On the knee the support foot skips forward 3 cm high on frames 2–6.
  - In stepping moves the hips follow the game's travel as it happens, instead of catching up over the whole clip.
  - The reach step now treats a foot as planted by its ball, which stays on the floor when the heel lifts, and
    blends between planted and carried. With the old 6 cm cut-off, the first stepping version made the elbow's rear
    foot jump 37 cm in one frame as it rose past the line.
- **Result.** Elbow: she steps in, stays compact and upright, and the elbow lands at 0.58 m (hitbox 10–72 cm).
  Knee: the support leg is under her hips and she drives the knee up with the torso leaning back; the knee lands at
  0.54 m (hitbox 8–70 cm). On every strike, the largest per-frame jump of a planted foot or the hips is now a normal
  step's.
- **Checked and left alone.** Wren's kicks keep her support foot under her hips; on the spinning back kick she leans
  away from the kick, as she should.
- **Review and regression.**
  - The elbow and knee were reviewed frame by frame in Blender, before and after.
  - Ashka's clips were rebuilt and every animation reimported, and packaged as `pkg-30-steps`.
  - The move script was recorded side by side with `pkg-29` (`anim-28`). Its first jab misses, so its light
    strings never reach the second and third hits. A new string script (`strings_review.txt`, outside the
    repository) walks in first. Recorded on both builds (`anim-30`), the jab, elbow and knee all connect.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-29`).
- **Wren rebuilt with the same code** (package `pkg-31-wren`), so the code in the repository reproduces both
  fighters' clips. The only measurable change is her jab's rear foot, 3 cm on one frame. The same four suites
  passed, with 0 failures and 0 warnings (`anim-31`).

### Flame elbow with planted feet (package `pkg-32-flame`)

- **What was wrong.** Foot planting was off for Ashka's flame elbow; it was turned off while a foot-height bug
  (since fixed) made her look as if she knelt. Without it her feet moved with her body. Through the strike her
  front foot stayed on the floor but slid 79 cm over the move, 44 cm of it after it should have landed.
- **Fix.** Planting is back on. The front foot now lands and stays put through the hit and the follow-through.
  Sliding along the floor dropped from 85 to 59 cm for the front foot and from 35 to 29 cm for the rear. What is
  left is the performer's own low shuffle step at the start and the reset step in recovery. Her hips stay at
  standing height (87–93 cm), so the kneeling look does not return. The elbow still lands at 0.68 m.
- **Review and regression.**
  - Ashka's clips were rebuilt and every animation reimported, and packaged as `pkg-32-flame`.
  - The move script was recorded side by side with `pkg-30` (`anim-32`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-33`).

### Wren's spinning back kick steps back into stance (package `pkg-33-backkick`)

- **What was wrong.** A sweep of every captured strike for foot sliding (the feet in world space, with the game's
  travel added back) found one more: after Wren's spinning back kick lands, her left foot slid 46 cm along the
  floor back into her stance.
- **Fix.** That foot now steps: it lifts up to 11 cm on frames 33–46 and lands where her stance puts it (a step
  option, `[first, last, "body"]`). Sliding in the recovery dropped from 46 to 6 cm. During the spin the ball of her
  support foot sweeps around the heel; that is the performer's own pivot and is unchanged. The rest of the kick is
  unchanged.
- **Other strikes.**
  - The roundhouse, the 720 and Ashka's kicks show only pivots: the ball of the foot moves while the ankle stays.
  - Both jabs end with the front foot gliding back about 25 cm into stance (Wren 27 cm, Ashka 24 cm). That is a
    boxer's push-back shuffle, so it is left as it is.
  - The teep's support foot keeps its 12 cm push-off skid, which slides back in recovery.
- **Option split.** "Hips follow the travel" is now its own clip option (`follow_travel`), used by Ashka's elbow
  and knee; their clips came out identical, checked frame by frame.
- **Review and regression.**
  - Wren's clips were rebuilt and every animation reimported, and packaged as `pkg-33-backkick`.
  - The move script was recorded side by side with `pkg-32` (`anim-34`). In game she steps back into her guard
    after the kick instead of gliding.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-35`).

### Hand-keyed moves: spinning elbow and throws (package `pkg-34-spin`)

The same world-space check, run on the moves that are still keyed by script (the spinning elbow, both bursts, the
rolls, the grab and the three scripted throws):
- **Rolls, bursts and the grab:** sound. The feet leave the floor and go over in the rolls, and the bursts and the
  grab hold their feet.
- **Wren's spinning back elbow.**
  - Before: her whole stance turned about a point between her feet, so both feet swept round the floor (162 cm and
    56 cm of sliding). On frame 5 her lead foot jumped 56 cm while on the floor. On the hit frames the elbow was
    2–7 cm in front of her, short of its hitbox (10–88 cm).
  - Now: the lead foot steps across with the travel and she turns on its ball. The rear foot tucks in and swings
    round in the air (7–11 cm up), lands back in stance, and the lead foot steps back out. Sliding is 11 cm and 25 cm.
    The elbow lands 32–35 cm out, inside the hitbox.
- **Throws that turn round.** Wren's suplex and Ashka's clinch-turn trip each switch sides with a 180° turn. Their
  earlier keys never set a turn, so the sampler snapped the whole turn into a single frame.
  - Suplex: Wren's body mirrored in one frame (her head jumped 123 cm).
  - Clinch-turn trip: Ashka's foot jumped 67 cm and Wren's (as the victim) 107 cm.
  - The suplex's victim also jumped 40 cm.
  - Now every turn starts from 0° and is interpolated. In the suplex Wren comes up out of the bridge, turns on a
    quick pivot hop and settles into her stance facing back.
  - Her worst one-frame head move is now 41 cm, a fast but continuous turn.
  - Her floor sliding dropped from 124/38 to 23/20 cm.
- **Not changed.** In the throws the victim still drops to the floor in a few frames, because the landing sits on
  the throw's damage frame. A slower fall would need the throw timing changed.
- **Review and regression.**
  - The spinning elbow and the suplex were reviewed frame by frame in Blender, before and after.
  - Every animation was rebuilt (the scripted build, then the captured clips over it) and reimported, and packaged
    as `pkg-34-spin`.
  - The light strings and both fighters' throws were recorded on `pkg-33` and `pkg-34` (`anim-36`, folders ending
    `-2`). The first throw recording walked in for 1.2 s, which left the fighters 34 cm apart, outside the 26 cm
    grab range, so every grab missed on both builds. The script now walks for 1.6 s, and the grabs connect.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-37`).

### Clinch knees and clinch-turn footwork (package `pkg-35-clinch`)

- **The clinch knee never rose.** On both knee frames Ashka's right knee stayed at 56 cm, barely above its resting
  49 cm, and her foot pushed out low (45 cm forward, 19 cm up): a straight-legged shove, not a knee.
  - The pose was right; the leg IK failed. The hand-keyed build bakes each frame into the bones, so the IK started
    from the last frame's straight planted leg and could not fold it.
  - Tested on its own from the rest pose, the same target solves cleanly. The leg IK now starts from the rest pose
    every frame (`animlib.Rig.apply`).
  - The knee now drives up to 98 cm, 48 cm out, into the bent-over opponent. Her floor sliding in the throw dropped
    from 14/54 to 8/8 cm.
  - The other hand-keyed moves change by 3 cm or less, except the rolls, whose knees bend in a slightly different
    plane (up to 16 cm).
- **Clinch-turn trip.**
  - Ashka's feet were spun with her body, so they swept round the floor.
  - Now the feet are placed independently of the turn. Her lead foot pivots in place while the rear foot swings
    round into the sweep, then the lead foot steps through and the rear foot steps into her stance facing back.
    Each step lifts 16–17 cm.
  - Swung round by the clinch, Wren (the victim) now stumbles, each foot lifting in turn: her floor dragging
    dropped from 139 to 60 cm.
- **Clinch-knees fall.** The trip and the start of the fall moved from frame 41 to 39; the landing stays on the
  damage frame (44). That gives the fall 5 frames instead of 3, and its worst one-frame move dropped from 107 to
  86 cm. A truly gradual fall would need a longer throw.
- **The rolls' landing** (feet jumping from the tuck to the stance on one frame) was left for the next package. A
  cross-fade made it worse, because the two positions are too far apart for those few frames.
- **Review and regression.**
  - The clinch knee and the clinch turn were reviewed frame by frame in Blender, before and after.
  - Every animation was rebuilt and reimported, and packaged as `pkg-35-clinch`.
  - Both fighters' throws were recorded on `pkg-34` and `pkg-35` (`anim-38`). In game Ashka's long coat and Wren's
    body hide most of the knee; the coat's front panels flare up as it rises.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-39`).

### Rolls (package `pkg-36-rolls`)

- **The back roll was an arch, not a roll.** Its tuck mirrored the forward roll's: chest and head curled back, feet
  and knees aimed behind the pelvis. Rolling back, it opened into a back-handspring arch with the legs folding the
  wrong way (knees dropped to 5–16 cm while the feet stayed higher). Both rolls now curl forward (rounded back, chin
  in, knees to the chest); only the turn and the sit-back differ. She sits back, rolls onto her shoulders with her
  legs over, and comes over into a crouch.
- **Take-off and landing jumps.**
  - The dip before the roll named no pelvis-relative feet, so the sampler applied the tuck's from the dip's first
    frame and the feet jumped into it (up to 60 cm).
  - As the roll came upright the feet switched from the tuck to the stance on one frame (up to 52 cm).
  - Now the feet are keyed in character space onto where the tuck really holds them. That was measured on both
    fighters: within ~2 cm at take-off and ~4 cm at landing.
  - On landing the lead foot comes down on its stance spot and the rear foot swings through the air onto its own.
  - After frame 16 no foot moves more than 15–19 cm in a frame (it was 65–85 cm). Floor sliding is unchanged
    (15–22 cm).
- **The last quarter turn** eased in at double speed straight out of the constant-speed tumble, so the knees
  whipped up to 66 cm in a frame. It now keeps the tumble's speed. The largest moves left are the head diving
  through the first quarter turn, about 50 cm a frame, which is the roll's speed: it is half a second long.
- **Review and regression.**
  - Both rolls were reviewed frame by frame in Blender, before and after.
  - Every animation was rebuilt and reimported, and packaged as `pkg-36-rolls`.
  - The move script, which includes both rolls for both fighters, was recorded on `pkg-35` and `pkg-36`
    (`anim-40`). In game the back roll now sits back, goes over the shoulders tucked and comes up in a crouch.
    Before, it went straight-legged into an arch, then floated in a sitting pose.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-41`).

### Hand-keyed arms (package `pkg-37-arms`)

- **Hands missed their targets.** The arm IK had the same flaw as the legs: it started each frame from the last baked
  arm. Measured as the distance from each hand to its target:
  - Wren's burst missed by up to 19 cm, Ashka's by 27 cm, Ashka's back roll by 20 cm, the throw escapes by 8–10 cm.
  - With the arms also starting from rest, the misses are 2 cm, 10 cm, 6 cm and 4–5 cm.
  - The feet now hit every target exactly.
  - No move gained a new jump. The bursts' elbows move most (28–47 cm), since those were the arms most off target.
- **The rolls' hands jumped like their feet did.** The hands switched between the guard and the tuck in one frame:
  81–94 cm at take-off, 70–86 cm on landing.
  - Now they are keyed onto where the tuck holds them (measured on both fighters) and come up into the guard by
    frame 24.
  - Nothing in either roll now moves more than 49 cm in a frame, and that is the fast dive.
- **Review and regression.**
  - Every animation was rebuilt and reimported, and packaged as `pkg-37-arms`.
  - The move script, which includes both bursts and both rolls, was recorded on `pkg-36` and `pkg-37` (`anim-42`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-43`).

### Captured jabs, cross and elbow; the teep extends (package `pkg-38-strikes`)

- **Creator feedback (2026-11-04).** The punches, knees and elbows of both fighters still needed a lot more work. The
  teep needed to look natural and smooth, and the knee hardly moved.
- **New captures.** Picked from 28 Mixamo candidates by where the fist or elbow travels and how high it lands:
  - Wren's jab is a short lead jab to the head, and her cross is a full cross.
  - Ashka's jab is a medium lead jab to the head. Her horizontal elbow is a capture that throws the elbow itself,
    so the elbow, not the fist, is aimed at the target.
  - The old clips punched at chest height; the new ones land at head height (checked in game).
  - In the hit frame, Wren's jab reaches 0.71 m and her cross 0.77 m; Ashka's jab reaches 0.64 m and her elbow
    0.58 m. All four are on their targets.
- **Teep.** The kicking leg is now solved toward a point ahead at hip height over the active frames, easing in and
  out (`mocap.extend`). The knee chambers bent and then straightens through the hit, and the foot reaches 1.17 m
  ahead instead of 0.93 m.
- **Rejected.**
  - A front snap kick and a side kick as the teep: different mechanics from a push kick.
  - New knee clips: Ashka's knee already reaches 1.05–1.08 m inside its hitbox.
- **Review and regression.**
  - Both fighters' captured animations were rebuilt and reimported, and packaged as `pkg-38-strikes`.
  - The move script and the light strings were recorded on `pkg-37` and `pkg-38` (`anim-44`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-45`).

### Throws drawn as authored (packages `pkg-40-throws`, `pkg-41-throwko`)

- **Creator feedback (2026-11-04).** The grab and throws looked completely broken and unrealistic.
- **What was wrong.** A throw is authored as a pair in the thrower's space, with the victim at `holdX` facing the
  thrower. The game draws each fighter in its own space, opened 12° toward the camera, and mirrors a fighter that
  faces left. So in every throw:
  - one of the two was drawn mirrored relative to how the pair was authored, so holds on one side of the body met
    the other side;
  - the pair stood 24° off square, with the victim about 9 cm off the line;
  - after a back throw both fighters switch sides, and the game blended from the last pose as the mesh held it,
    which the switch had just mirrored. The thrower twisted through a half turn (the arms-out pose after the suplex);
  - every landing jumped by up to 24° into the knockdown.
- **Fix.**
  - Each victim animation is moved into the space the game draws the victim in, a turn and a mirror per throw
    (`build_anims.stage_transforms`, `transform_pose`). The skeletons are symmetric to within 3 cm.
  - Both bodies end exactly on the first frame of what is drawn after the landing: the thrower in its stance
    (facing the victim after a back throw) and the victim lying at `landX`. Measured: 0 mm on every bone except the
    double-leg's curled fingers (7 cm).
  - The game now cuts instead of blending when a fighter's facing flips (`EHFighterVisual`).
- **Clinch distance.** Ashka's clinch throws held the victim 42 cm away, and the two bodies overlapped through the
  clinch. `holdX` is now 54 cm for both. It only places the victim during the throw; the landing still uses `landX`.
- **Throw knockouts.** A throw that knocked the victim out played the standing knockout fall from the floor. The
  victim now stays down in its lying pose (`reaction` 3 in `KO`). Covered by a new core test, `throw_ko_stays_down`
  (261 checks).
- **Researched, not used.** Mixamo has three two-person throws: Double Leg Takedown (Wren's slam), Shoulder Throw
  and Hell Slammer. The last two land the victim with its head toward the thrower, but the knockdown and get-up
  start lying head away. Using them needs a head-toward knockdown and get-up.
- **Review and regression.**
  - All four throws against both victims were rebuilt and reimported, and packaged as `pkg-40-throws`.
  - The training throw script was recorded on `pkg-38` and `pkg-40` (`anim-46`).
  - With the knockout fix added, the build was packaged as `pkg-41-throwko`. The smoke test, the controls
    self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures and 0 warnings (`anim-48`).

### Hand-overs between the stance and the moves (package `pkg-42-flow`)

- **Creator feedback (2026-11-04).** The flow between the stances and the moves was not smooth and did not look like
  a real fight. The creator pointed to Dead or Alive 5 as the reference for how fighters should move and flow.
- **Research.**
  - Dead or Alive 5's moves were performed by a team of motion actors, with an action coordinator, at a capture
    studio (the game's production credits). Each character's stance, moves and strings come from one performance
    style.
  - Animators' practice for fighting games: start every attack from (or within a few centimetres of) the idle, so the
    blend into it cannot be seen; keep the idle a clean pose to blend from; put the follow-through inside the attack
    and settle back into the stance.
- **Measured.** The worst joint between where one animation hands over and where the next starts, in cm
  (`tools/anim-review/transitions.py`, `loop_phase.py`):
  - The captured moves start 2–8 cm and end 0 cm from the idle.
  - The scripted moves were 12–14 cm off at both ends: Wren's spinning back elbow, both bursts, the grabs and the
    rolls were keyed on the scripted stance, not on the captured idle.
  - Walks started 17–20 cm off (mid-stride).
  - Strings hand over 15–57 cm apart, because the cross's arm is still out when the next hit starts. The game already
    decays that offset over the next move's startup, so contact still lands on the move's own keys.
- **Fix.**
  - The scripted moves now ease in from and out into the idle's first pose, as the captured moves do (`build_mocap`
    `"scripted"` entries). They start 1 cm and end 0 cm from it.
  - Walk loops start on the frame closest to the stance (`"start_frame"`): 9–12 cm.
- **Review and regression.**
  - Every captured and scripted clip was rebuilt and reimported, and packaged as `pkg-42-flow`.
  - The move script and the light strings were recorded on `pkg-41` and `pkg-42` (`anim-50`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-51`).

### The golden aura and the crimson flame (package `pkg-43-aura`)

- **Creator feedback (2026-11-04).** The auras looked so bad overall that a real critique was not possible.
- **What was wrong.**
  - Spirit Enhanced Strikes turned the rim of Wren's body materials gold at up to 0.9 intensity. That tinted her
    whole body, so she read as mustard-coloured. Its lightning was five thin lines with no glow between random bones,
    redrawn wherever they fell about 18 times a second, so they floated loose around her.
  - The Lamplighter Flame was one static teardrop sprite in rose tones, so it read as flat pink cards.
- **Now.**
  - **Energy shell.** A second pass of Wren's own mesh (an overlay material, `M_VFX_AuraShell`): a fresnel rim, so
    the glow sits on her silhouette, carried by two layers of noise streaming upward in world space. Her body keeps
    its own colours; the body rim only warms slightly.
  - **Lightning.** Short arcs between two bones 10–55 cm apart, each end pushed out past her outline toward the
    camera. Each arc has a soft glow, a white-hot core and one fork, lives 3–7 frames, re-strikes its jag once, and
    rides her limbs as she moves.
  - **Motes.** About 30 gold motes a second stream up off her body.
  - **Fire.** Each flame tongue plays a 16-frame flipbook (`T_FX_FireSheet`, procedural): licking up, tearing at the
    tip, burning out. Its density is mapped from deep crimson at the edges to a hot red core (`M_VFX_Fire`). Embers
    rise off it. Flame Burst rolls out a field of 24 tongues. Flame tongues have their own pool, so no quad ever
    changes material.
  - The overlay is set once when the fighter loads and stays dark until the aura rises. Changing a mesh's overlay
    rebuilds its render proxy, which would hitch on the frame the aura lands.
  - The rebuild never re-imports the title card once it exists (`build_content.py`).
- **Review and regression.**
  - Packaged as `pkg-43-aura`. The signature moves were recorded on `pkg-41` and `pkg-43` (`anim-52`).
  - Frame times in Training with and without the aura (`perf_aura`, `anim-53`): median 16.66–16.67 ms and 99th
    percentile 16.75–16.80 ms either way, with no hitches.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-53`).

### Captured shoulder throw, head-toward get-up, close-range stagger (package `pkg-44-shoulder`)

- **Why.** The creator asked for captured throws. Mixamo's other two-person throws (Shoulder Throw, Hell Slammer)
  land the victim on its back with its head toward the thrower (measured: head 1.1 m, feet 2.3 m from the thrower),
  but the knockdown and the get-up started lying head away.
- **Head-toward landing.**
  - A throw can be marked `landsHeadToward` (data). The victim then lies as `KnockdownLieRev` (the knockdown lie
    turned round) and rises with `GetupRev`: the captured get-up turned round, so it sits up facing away, then pivots
    180° over its feet while rising (`build_mocap` `"turn"`, turning its front past the camera). It ends in its stance
    facing the opponent. The timing is unchanged (`reaction` 4, presentation only).
  - A get-up from the stomach was considered. Mixamo's take 3–5 s and ACCAD's 3 s, too slow for the game's 1 s
    get-up.
  - New core test `shoulder_throw_lands_head_toward` (263 checks).
- **Wren's back throw** is now the captured Shoulder Throw (it was the scripted belly-to-belly suplex): she ducks in,
  loads the victim onto her shoulder and throws it over to land behind her.
  - The pair is mirrored and turned as it plays (from 20° at the grip to 113° at the landing), so the victim lands
    on the fight line behind her and she finishes facing it.
  - Its duration is now 72 frames (was 60) and its damage frame 48 (was 38), under the creator's approval to lengthen
    throws; the advantage after it is unchanged.
- **Not used.** The Hell Slammer: in its usable stretch the victim never faces the thrower, so the throw would open
  with a pop. Ashka's two throws stay scripted.
- **Close-range stagger.** Within 75 cm the fighters are eased up to 10 cm apart in depth (the one facing right
  toward the camera), so bodies standing chest to chest no longer pass through each other. It is off during throws
  and throw escapes. Presentation only: the pushboxes are unchanged.
- **Review and regression.**
  - Every animation was rebuilt and reimported (34 per fighter), and packaged as `pkg-44-shoulder`.
  - The training throw script was recorded on `pkg-43` and `pkg-44` (`anim-54`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-55`).

### Wren's jab and cross from one performance (package `pkg-45-strings`)

- **Why.** In the Dead or Alive 5 reference each string is one performance. Wren's cross came from a different capture
  than her jab, so when the jab cancelled into the cross the pose jumped 18 cm at the hand-over.
- **Change.**
  - When the cross cancels out of the jab, the game now plays `L2_from_L1`: the cross from Mixamo's Jab Cross
    (medium), a single performance of both punches. It starts from the jab's own pose at the cancel frame (6 frames
    blended in), so the hand-over is 0 cm. A cross thrown from the stance still uses the standalone capture.
  - A buffered string cancels on the jab's first active frame (frame 8) for both fighters. The new core test
    `string_cancels_on_the_first_active_frame` pins this, since the string clip is built from that frame (265 checks).
  - Ashka's jab-to-elbow capture was not used: it is the elbow capture the creator judged weaker than the current one.
- **Review and regression.**
  - Wren's captured animations were rebuilt and reimported, and packaged as `pkg-45-strings`.
  - The light strings were recorded on `pkg-44` and `pkg-45` at 60 fps (`anim-58`), and the half-speed video keeps every
    frame.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-59`).

### Throws flow out of the grab (package `pkg-46-grab`)

- **Measured.** When a grab connects (its first active frame, 5), the throw takes over. Wren's grab pose was 65 cm from
  the first frame of her captured double-leg and 48 cm from her captured shoulder throw; Ashka's was 25 cm from both
  of hers. The game covered that in a 6-frame blend, a visible snap.
- **Fix.** Each throw's first 8 frames now ease out of the grab's own pose at that frame (`build_anims.grab_connect_pose`),
  so the hand-over is 0 cm for all four throws. Wren now drops from her reach into the double-leg shoot, or turns in
  for the shoulder throw. The throws' ends still hand over exactly (0 mm).
- **Review and regression.**
  - Every throw was rebuilt and reimported, and packaged as `pkg-46-grab`.
  - The training throw script was recorded on `pkg-45` and `pkg-46` at 60 fps (`anim-63`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-64`).

### Every other hand-over measured (package `pkg-47-tech`)

- **Audit.** Every non-attack hand-over was measured: a clip's last frame against the first frame of what plays next
  (`tools/anim-review/handovers.py`, 21 per fighter).
  - **0–2 cm:** the hit reactions, block hits, both get-ups, knockdowns, intros, wins and defeated poses.
  - **Larger, but meant to be:** the guard raise (23–47 cm, the hands coming up) and the hit reactions' first frames
    (10–21 cm, an impact).
  - **Walks:** they stop 11–13 cm off the stance at an arbitrary phase, and the 0.22 s blend covers it.
  - **The one script-keyed clip still off:** the throw escape ended 13–14 cm from the stance. It now settles into it
    (`"scripted"`, end only, since it starts from the grab): 0 cm.
- **Review and regression.**
  - Packaged as `pkg-47-tech`.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-65`).

### The grabbed fighter eases into the throw (package `pkg-48-victim`)

- **Measured.** A grabbed fighter's throw animation started 50–86 cm from the idle they were standing in. The victim
  animations are expressed in the space the game draws them in, so their first frame is the stance with the feet the
  other way round, and the captured victims start in their performers' poses. The game covered that in a 6-frame
  blend.
- **Fix.**
  - `build_mocap` saves each fighter's idle first pose (`idle_pose.json` beside the clips).
  - Each victim animation's first 10 frames now ease out of it, so the throw starts exactly where the victim stood:
    0 cm from the idle. From the guard, only the raised hands differ (23–47 cm).
  - The ends still hand over exactly (0 mm).
- **Review and regression.**
  - Every throw was rebuilt and reimported, and packaged as `pkg-48-victim`.
  - The training throw script was recorded on `pkg-47` and `pkg-48` at 60 fps (`anim-66`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-67`).

### Throw escapes start from where the throw is (package `pkg-50-escape`)

- **Measured** (`tools/anim-review/escapes.py`). An escape can come on any of a throw's first 9 frames
  (`throwTechWindow`; the CPU escapes 1–7 frames after the grab lands). The escape always started from the stance:
  - Wren's throws: 44–95 cm from the thrower and 13–116 cm from the victim over those frames.
  - Ashka's throws: 19–25 cm from the thrower and 13–63 cm from the victim.
  - The escape's shove also reached 87% of its reach in one frame (a 24 cm hand step).
- **Fix.**
  - `build_anims` now builds each body's escape alongside the throw, starting from the throw's frame 2, 5 or 8
    (`ThrowTech_from_<throw animation>_F<n>`). The game plays the one for the frames the escape came on (1–3, 4–6
    or 7–9).
  - Each escape eases out of the throw's pose over 5–16 frames, longer the further it has to go. A fighter caught low
    in Wren's double-leg rises over about a quarter second instead of springing up.
  - The gap is now 0–25 cm, and the escape blends over 0.15 s instead of 0.08 s to cover it.
  - The stock escape's shove builds over four frames (largest hand step 11 cm).
  - Tried and dropped: holding the captured throws near their grip frame during the window. It changed the gaps
    by under 5 cm, because the drift is the ease from the grab and the idle into the capture's grip pose, which the
    throw needs.
- **Review and regression.**
  - Packaged as `pkg-50-escape`. The first package, `pkg-49-escape`, capped the ease at 12 frames, and its review
    showed Wren springing up from the double-leg in about 8 frames; the cap is now 16.
  - A versus script was recorded on `pkg-48` and `pkg-50` at 60 fps (`anim-68`). The second player escapes 6, 9 and
    12 frames after the grab (throw frames 2, 5 and 8), on forward and back throws, with each fighter throwing.
    - Escaping Wren's double-leg late, she sprang from her kneel to standing in about 4 frames on `pkg-48`. On
      `pkg-50` she rises over about 12 while Ashka shoves.
    - Early escapes now shove straight out of the grip.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-70`).

### The rolls stay above the floor (package `pkg-51-rolls`)

- **Measured** (`tools/anim-review/floor.py`, new: each frame's lowest body point, with the top of the head). In all
  four rolls the top of the head went 20–25 cm below the floor for about five frames: the forward roll's frames 7–10
  and the back roll's 10–14. The rolls turn the tucked body about its hips, so the head led into the floor. The other
  hand-keyed moves keep their feet planted (0 cm of sliding) and nothing else goes through the floor; victims' toes
  sink at most 3 cm early in a throw.
- **Fix.**
  - The roll tucks the chin and chest further (`moves.rolls`).
  - `build_mocap` lifts a clip marked `"floor"` wherever a body part would go through the floor
    (`floor_clamp`, the clearance under each bone is the body's thickness there). The lift is widened by a frame
    and smoothed over one, and frames with a foot on the floor are lifted only as far as they need, so the push-off
    and the landing stay planted.
  - Rolls lift by up to 22–25 cm. Nothing goes below the floor now (lowest: a planted toe, −1 cm).
- **Still to note.** At the roll's midpoint the body rests for about 5 frames on the top of the head, with the
  shoulders 40 cm up, because the roll still turns about the hips. Rolling over the shoulders would mean
  re-keying the roll, or a captured back roll (none on Mixamo or CMU).
- **Review and regression.**
  - Packaged as `pkg-51-rolls`.
  - A Training script with both rolls twice for each fighter was recorded on `pkg-50` and `pkg-51` at 60 fps
    (`anim-71`). On `pkg-50` Wren's head sinks into the floor as she goes over; on `pkg-51` it stays at floor level.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-72`).

### Lying on the floor, not above it (package `pkg-52-lying`)

- **Measured** (`floor.py`). The hand-keyed lying pose was about 10 cm above the floor: hips 23–24 cm and upper spine
  22–23 cm up. The captured knockout lies with them at 13–14 cm and 11–12 cm. That pose is where a knockdown
  settles, where every throw lands its victim and where both get-ups start, so knocked-down fighters hovered.
- **Fix.** The lying pose's hips are 10 cm lower (`moves.lying`). The lying clips, the knockdown, both get-ups and
  all four throws (with their escapes) were rebuilt. Lying now measures hips 14 cm, upper spine 13 cm and the top
  of the head 15–16 cm, as the captured knockout does. The hand-overs are unchanged: knockdown to lying and lying to
  get-up 0–0.1 cm, the throws' ends 0 mm.
- **Review and regression.**
  - Packaged as `pkg-52-lying`.
  - The training throw script was recorded on `pkg-51` and `pkg-52` (`anim-73`). The lying victim is low in the
    frame and dark against the floor there, so the recording shows little; the heights above are measured on the
    clips.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-74`).

### No more one-frame jumps in the knees and the spin (package `pkg-53-pops`)

- **Measured** (`tools/anim-review/stepping.py` on every clip: the largest one-frame move of the main joints, against
  the frames either side). Three clips jumped:
  - Ashka's Clinch Knees: the right knee moved 69–71 cm in one frame as each knee came up, and the foot 60 cm into the
    sweep. The keys switched the foot from a planted target to a body-space one, and a switch of control happens
    on the key itself, so the foot held still and then jumped. `"snap"` eases also put 60% of each knee into its
    first frame.
  - Wren's spinning back elbow: the turn went from 0 to 60 degrees in one frame as it began, and the hips with it (a
    channel missing from a key takes the next key's value; her stance has no spin). A `"snap"` into the strike and an
    `"out"` back to the guard moved her 106 degrees and her arms 47 cm in single frames.
  - Ashka's Clinch Turn Trip: 15 cm, within what a fast step does.
- **Fix.**
  - The clinch knees keep the foot in world space throughout (a throw has no root travel), on smooth curves.
  - The spinning elbow keys its spin from 0, with an extra key midway, and flows through the strike.
  - The knee now moves at most 22 cm a frame and the sweep 29. The spin's fastest point is the rear foot swinging round
    the pivot at 37 cm a frame, steady rather than a spike: the move turns 200 degrees in 6 frames about a pivot 40 cm
    ahead, which only a new capture or new timing would change.
- **Review and regression.**
  - Packaged as `pkg-53-pops`.
  - A Training script with Wren's light string into the spinning elbow twice and Ashka's Clinch Knees twice was
    recorded on `pkg-52` and `pkg-53` at 60 fps (`anim-75`). The spin now turns through, strikes and comes back to
    the stance one even step at a time. After the rebuild the audit flags only the Clinch Turn Trip's 15 cm step.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-76`).

### Hand and foot controls hand over smoothly; thrown victims fall slower (package `pkg-54-switch`)

- **Measured** (`tools/anim-review/speeds.py`, new: every frame where a main joint moves more than 40 cm). The
  victims of Ashka's two throws moved a hand 80–90 cm and the head 68–73 cm in single frames as they fell. A real
  fist or foot peaks near 25–35 cm a frame, and the captured victims stay under 40.
  - Before landing, the victim's hands are in character space. The lying pose holds them pelvis-relative. A channel
    missing from a key takes the next key's value, so the hands jumped to the lying pose the frame after the
    previous key.
  - The Clinch Knees left the fall 8 frames, eased "in" (three times its mean speed at the end).
- **Fix.**
  - `animlib`: when a hand or foot changes control between two keys (character space, pelvis-relative,
    absolute or held in the world), the rig now places it from both controls and moves it between them over the
    segment. It used to hold on one and jump on a key. All hand-keyed clips and throws were rebuilt.
  - A `"fall"` ease (quadratic, like a falling body) for both landings. The Clinch Knees bring the two knees a
    little closer together, so the trip starts at frame 30 and the victim falls over 14 frames. The victim's arms fly
    out to the sides as it is tripped.
  - The victims now peak at 41–56 cm a frame (a hand flung out), the head at 38. No clip has a one-frame spike
    (`stepping.py`), nothing goes through the floor, and the hand-overs are unchanged.
- **Still fast (over 40 cm a frame).** The rolls' arms and dive (40–51 cm, a 0.5 s roll) and Ashka's burst
  gesture (47). Also the foot of Wren's flying spin kick, which turns a full circle in 10 frames (56–77 cm). Slowing
  these would mean new timing or captures.
- **Review and regression.**
  - Packaged as `pkg-54-switch`.
  - The every-move Training script was recorded on `pkg-53` and `pkg-54` at 60 fps (`anim-77`). Nothing looks
    broken in either fighter's moves.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-78`).

### Elbows that do not flip (package `pkg-55-elbows`)

- **Measured** (`speeds.py`, then the arm's joints frame by frame).
  - **Rolls:** the elbows jumped 44–51 cm in single frames as the body dove and came up. Each elbow aims at a
    point kept in character space from where the shoulder would be standing, so as the torso went upside down
    the aim stayed put and the elbow swung across.
  - **Ashka's burst:** the palms thrust 48 cm in one frame (a `"snap"` over two frames). In the recovery the hands
    came back to within 14 cm of the shoulders. A fully folded arm has no defined bend, and the elbow swung 42 cm
    in one frame.
- **Fix.**
  - `animlib`: a numeric `elbow_follow` channel. Above 0 the elbow aims from where the shoulder really is and turns
    with the chest. Being a number, it eases in and out with the keys. The rolls turn it on from the dip, and the
    forward roll keeps it while rising. The back roll hands back to the stance's aim as it rises, since keeping it
    swung an elbow 48 cm there.
  - Ashka's burst thrusts over three frames on an `"out"`, still landing on frame 7. The recovering hands stop a
    little further out than the coil.
  - The rolls' elbows now move at most 36 cm a frame and the burst's palms 33. What is left over 40 is the forward
    roll's dive (the head, 42–44 cm) and the back roll's legs swinging over (37–42), both the moves' own timing.
- **Review and regression.**
  - Packaged as `pkg-55-elbows`.
  - A Training script with both rolls twice for each fighter and Ashka's burst twice was recorded on `pkg-54` and
    `pkg-55` at 60 fps (`anim-79`). The burst coils, thrusts as the flame erupts and settles.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-80`).

### One continuous fall in the Clinch Knees (package `pkg-56-fall`)

- **Measured** (hips and head frame by frame through the fall). `pkg-54` split the Clinch Knees victim's fall into
  two `"fall"` segments that each start from rest. The body fell at 12.6 cm a frame at frame 36, then 1.0 at 37: it
  stalled in mid-air and fell again.
- **Fix.** One fall from the held clinch (frame 30) to the floor on the damage frame (44). It accelerates from rest
  as she is tripped: the hips reach 14 cm a frame and the head 31 at impact. The hands go out to where the lying pose
  holds them over the whole fall; a hand peaks at 43–46 cm in the last frame (it was 50–56). The Clinch Turn Trip's
  victim stumbles, steadies for two frames and falls, as it did before.
- **Tried and dropped.** Evening the forward roll's turn (30 degrees a frame in the dive, 22.5 after it) slowed the
  head but swung an elbow 45–49 cm a frame in the dive.
- **Review and regression.**
  - Packaged as `pkg-56-fall`.
  - The training throw script was recorded on `pkg-55` and `pkg-56` at 60 fps (`anim-81`). No limb flips in any
    victim (`flips.py`).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-82`).

### Ashka's throws give their falls time (package `pkg-57-throwtime`)

- **Timing.** This uses the creator's approval to lengthen throws with advantage unchanged, as for Wren's two.
  - The Clinch Knees now last 74 frames (was 64) with damage on frame 54 (was 44).
  - The Clinch Turn Trip lasts 66 (was 56) with damage on 48 (was 38).
  - The victim's knockdown after the throw (`victimKnockdown`) is unchanged, so the advantage after each throw is
    the same. The lie between landing and the throw's end is unchanged too (20 and 18 frames).
  - All 265 core checks pass. The move table in `CombatContract.md` was regenerated.
- **Motion.** The extra frames go to the falls: 24 frames (0.4 s) in the Clinch Knees and 22 in the Turn Trip, from
  rest, accelerating like a falling body. Ashka holds her sweep while the victim falls, then steps round.
  - At impact the victim's head moves 18.6 cm a frame (was 31.5) and the hips 8.5.
  - The fastest limb is an elbow at 29–32 cm (hands were 42–46).
  - No flips; the throws' hand-overs are still 0 mm.
- **Not changed.**
  - The forward roll's dive (the head about 43 cm a frame): the rolls are hand-keyed dodges whose timing sets
    their invulnerability.
  - Wren's tornado kick (the foot up to 77 cm a frame): what makes it fast is the full turn added to a captured
    roundhouse, not the capture. Lengthening its startup from 17 to 22 frames was tried, with advantage
    unchanged and the turn spread over the longer jump. It broke Wren's L1 → Tornado Kick and L1 → L2 → Tornado
    Kick combos, which the core tests pin: the kick no longer lands inside the earlier hits' hitstun. It also
    pushed the longest stretch without control past its bound, so it was reverted.
  - Both are the creator's call.
- **Review and regression.**
  - Packaged as `pkg-57-throwtime`.
  - The training throw script was recorded on `pkg-56` and `pkg-57` at 60 fps (`anim-83`). In the Clinch Knees
    the victim now tips back and goes down over about 16 frames after the trip, instead of dropping.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-84`). The CPU matches throw and are thrown with the new timings.

### A captured forward roll (package `pkg-58-roll`)

- **Source.** The creator signed in to Mixamo again on 2026-11-05. Nine candidates were exported and kept outside the
  repository (hashes in the download log). Probed with `tools/anim-review`:
  - **Used:** Quick Roll To Run, a quick shoulder roll out of a run.
  - **Not used:**
    - Dive Roll: a 4-second leaping dive over 3.6 m.
    - Run To Rolling: turns sideways as it rises.
    - Au To Role: a cartwheel that drifts 4.7 m sideways.
    - Standing Yell: starts from a deep crouch.
    - Yelling Out: tried on Wren's Spirit Enhanced Strikes; with her stance it read as one arm swung back, not a
      gathering of power, so the hand-keyed version stays.
  - **Kept for later:** Sprinting Forward Roll (another shoulder roll) and Rockin' Shackle A (a grab and arm twist).
  - Mixamo has no back roll, so the back roll stays hand-keyed.
- **Build.** Both fighters' forward roll (`DF`) now comes from the capture, from its dive to its rise.
  - Its dive, inverted moment, back contact and rise land on frames 6, 10, 14 and 20 of the 30.
  - Its travel is scaled to the game's 1.53 m, and the body keeps pace with the game's travel.
  - The hands are open for the floor.
  - `build_mocap`'s floor lift now also runs on captured clips marked `"floor"` and checks the toes. The roll's
    lowest point is 0 cm, and the back roll, rebuilt with the same lift, is unchanged.
- **Measured.** It is a real roll: the hands reach the floor (frames 6–9), the head passes 13 cm over it (frame 10),
  the body rolls across the upper back onto the hips (19 cm, frames 12–15) and rises over a knee. The hand-keyed
  roll balanced for about 5 frames on the top of the head. The roll starts 6–8 cm from the idle and ends on it
  (0 cm). The fastest part is the hands reaching for the floor (42–45 cm a frame; the hand-keyed roll's dive moved
  the head 42–44). No flips.
- **Credits.** The ledger and `ThirdPartyManifest.json` now list every Mixamo clip the build uses (28, with
  hashes). Earlier additions were missing: the jab, cross and elbow captures, the jab-to-cross string, the shoulder
  throw pair and the roll. `AssetLedger.md` matches.
- **Review and regression.**
  - Packaged as `pkg-58-roll`.
  - The roll script was recorded on `pkg-57` and `pkg-58` at 60 fps (`anim-85`). In game she leans and dives, rolls
    over the shoulder onto her back, sits, rises on one knee and is in stance by frame 30.
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-86`).

### Ashka's throws end in a captured fall (package `pkg-59-fall`)

- **Source.** Mixamo's Sweep Fall (downloaded 2026-11-04): a fighter with the guard up has the feet swept, goes up
  with the arms flung back, falls flat and lands on the back. Rendered on Wren it reads as a real trip fall.
- **Build.** `build_anims` can now hand a keyed throw's victim over to a captured fall (`"victim_falls"` in
  `mocap_clips.json`, `captured_fall`).
  - From a chosen frame the victim follows the capture. It is placed where the keys have the hips then, and turned
    to face the way they do (by hip line).
  - It eases in over 6 frames.
  - The capture's landing goes on the damage frame, and any gap to the lying spot is spread over the fall.
  - The throw's end blend then settles the body into the lying pose the knockdown starts from.
  - The Clinch Knees hand over at frame 30 (after the second knee) and the Clinch Turn Trip at frame 26 (after
    the swing).
  - The landings moved 19–28 cm onto the lying spot, and the facing is within 6–22 degrees of the lying pose. The
    throws' end hand-overs are still 0 mm.
- **Measured.** The victims now move at most 30 cm a frame (the keyed falls: 29–32), with no spikes (worst ratio 1.9),
  no flips and nothing through the floor.
- **Review and regression.**
  - Packaged as `pkg-59-fall`.
  - The training throw script was recorded on `pkg-58` and `pkg-59` at 60 fps (`anim-87`). In the Clinch Knees
    Wren is swept with her arms flung up, falls back flat and lands legs-up on her back.
  - Sweep Fall is now credited in the asset ledger and `ThirdPartyManifest.json` (29 Mixamo clips).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-88`).

### Wren's power-up from a capture (package `pkg-60-powerup`)

- **Source.** Mixamo's Standing 2H Cast Spell 01 ("two-handed casting spell, upward pull"). The creator signed in on
  2026-11-05.
  - Its shape is the one Wren's Spirit Enhanced Strikes was keyed to: sink and gather, then rise and open. She sinks
    into a deep crouch with the hands at the knees, then rises with both arms raised overhead.
  - Anchors put the deepest gather on frame 12 and the arms opening on frame 24, where the aura applies.
  - Its own forward drift is cut to 30%.
- **Ruled out.**
  - For Ashka's Flame Burst: the two-handed magic attacks. The burst erupts on frame 7, and fitting their coil and
    thrust into that would run them about 5×.
  - For Wren: Wide Arm Spell Casting, which steps half a metre sideways.
  - Searched with nothing usable: a back roll (Mixamo has only back flips), a spinning elbow or backfist, and a
    forward two-handed grab.
- **Measured.** At most 29 cm a frame (the hands), no spikes or flips, nothing through the floor. It starts 8 cm from
  the idle and ends on it.
- **Review and regression.**
  - Packaged as `pkg-60-powerup`.
  - A Training script with each fighter's burst twice, full gauge, was recorded on `pkg-59` and `pkg-60` at 60 fps
    (`anim-89`). Wren gathers in a deep crouch, rises, and the golden aura flares as her arms open overhead.
  - Credited in the asset ledger and `ThirdPartyManifest.json` (30 Mixamo clips).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-90`).

### Punches extend and elbows reach (package `pkg-61-punches`)

- **Why.** The creator's playtest of `pkg-60` (2026-11-04/05): the punches and elbows looked like the arm never
  extended, with no range. Measured, the jabs landed with the elbow at 129-132 degrees (fist 66-71 cm out against
  72-78 cm boxes) and Wren's spinning back elbow reached 29-34 cm against an 88 cm box. Captured boxing jabs on Mixamo
  stop at 134-150 degrees.
- **Change.**
  - A clip option, `straighten`, extends the punching arm by IK to about 172 degrees over its active frames, ramping
    in and out.
  - Wren's jab comes from Mixamo's Long Head Jab (its longest, src 9/15/24); both her crosses are straightened.
  - Ashka's jab is retimed (src 7/12/22) and straightened; her horizontal elbow and Flame Elbow reach further
    (66-68 cm and 81-87 cm, from 58-61 and 74-80).
  - Wren's spinning back elbow is re-aimed with its pivot 8 cm further in.
- **Measured.** Jabs and crosses land at 172-180 degrees: Wren's fist 72 cm out (box 78; the knuckles sit about
  8 cm past the wrist), her crosses 78 cm (box 85), Ashka's jab 67 cm (box 72). Wren's elbow reaches 80-83 cm on its
  active frames. No flips; nothing over 35 cm a frame in the punches.
- **Review and regression.**
  - Packaged as `pkg-61-punches`; each fighter's light string and single jabs recorded on `pkg-60` and `pkg-61`
    (`anim-91`). The arms extend at contact. That script walked the fighters chest to chest (inside the jab's
    reach), so the next review walks them in to near the jab's full reach.
  - Credited (31 Mixamo clips).
  - The smoke test, the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures
    and 0 warnings (`anim-92`).

### Hit reactions by where the hit lands; straight wrists, wrapped thumbs, natural necks (package `pkg-62-reactions`)

- **Why.** The creator's playtest asked for more realistic reactions to contact, and noted that the necks, wrists and
  fists bent or extended unnaturally.
- **Reactions.**
  - Every hit had played one straight head-snap. A hit can now name its defender's clip (`react` in the fighter
    data; see the combat contract): hooks and the spinning elbow from the attacker's right turn the head away
    (`HitHookR`, `HitHookRHeavy`); the teep, knee and spinning back kick fold the body (`HitBody`, `HitBodyHeavy`);
    Ashka's body kick crumples the defender toward the kicked side (`HitBodyR`).
  - Measured toward the attacker, the hook throws the head 19 cm away and turns the body 82 degrees; the body hit
    folds it 17 cm forward and 50 cm down over the blow, as in the captures.
  - Each reaction opens on its impact pose and holds it through the hitstop; before, the defender held the guard for
    the 7-16 hitstop frames and only then reacted.
  - The jab and cross reactions use a clean straight-punch capture (the head snaps straight back, 21 cm for the
    cross); the jab keeps 60% of its motion.
  - Mixamo boxing hit reactions: 18 exported, 7 used (credited; 36 Mixamo clips).
- **Wrists, fists, necks.**
  - Arm IK had kept each hand's captured world orientation while it moved the forearm (placing a guard, extending a
    punch), cocking fists back 20-60 degrees and up to 160 in hit reactions. A final pass keeps every fist within
    12 degrees of the forearm's line (open hands 30), keeping the forearm's twist.
  - The thumb folds over the curled fingers; it had stuck out past the fist or up like a thumbs-up.
  - The neck and head nod and tilt at most 30 degrees off the chest (42 for rolls, falls and get-ups); hit reactions
    had bent it 45-65.
  - Measured on every clip after the rebuild: wrists at most 12 degrees (open-handed rolls 23), necks at most 30
    (knockdowns, KOs and get-ups 33-36; the keyed back roll's chin tuck 48).
- **Tools.** `build_mocap --closeup` renders the hands and head; `--joints` prints each clip's worst wrist and neck;
  `capture.py --start-on <log>:match_start` starts both builds' recordings on the same game event, so before/after
  videos line up.
- **Review and regression.**
  - Packaged as `pkg-62-reactions`. A Training script walks each fighter to near the jab's full reach and throws the
    light string twice, Heavy and toward + Heavy (Ashka also the Flame Elbow); recorded on `pkg-60` and `pkg-62`
    (`anim-94`), aligned on the first match.
  - The core tests pass (276 checks, including `hit_reactions_name_their_clip`).
  - The smoke test warned `missing_anims=[HitHookRHeavy]` (`anim-95`): a reaction plays on the defender, but each
    fighter had been given only the reactions its own hits name, so Ashka fell back to the generic heavy hit for
    Wren's roundhouse (and Wren for Ashka's body kick). Fixed in `pkg-63` (every fighter gets every reaction;
    `build_mocap` now refuses to build otherwise). The controls self-tests passed; the rest of the run was stopped in
    favour of `pkg-63`.

### Movement into strikes, guards that turn with the body, Ashka's kicks (package `pkg-63-flow`)

- **Why.** The creator found moving and striking with Wren felt disjointed, and Ashka's kicks robotic and stiff.
- **Measured first** (`walk_to_strike.py`, poses in the game root's space):
  - A strike started mid-walk left the lead foot 15-26 cm from where the strike begins, for the game's 0.05-0.15 s
    blend to cover (a skate along the floor).
  - Wren's idle had kept 60% of its performer's foot shuffle; strikes started up to 7.5 cm off it (Ashka 3).
  - Guarded strikes held the non-striking hand at the stance guard by the chest's position only, so it floated in
    place while the body twisted (both fighters; most visible on Ashka, whose strikes kept 50-60% of the guard hand's
    captured motion).
- **Changes.**
  - The legs settle over their own blend time (up to the strike's first active frame, at most 0.16 s) while the arms
    still meet their keys on time, and a planted foot with more than 6 cm to go lifts (up to 7 cm) on the way: a
    strike from a walk finishes the step instead of sliding into stance.
  - Wren's idle keeps 25% of the foot shuffle (her feet now 3-4 cm from a strike's start).
  - Guard hands turn and lean with the chest; their captured motion is measured in the chest's own frame. (The same
    code had also measured one-shot clips' hands from the clip's average rather than its first frame; fixed.)
  - Ashka's body kick is Mixamo's rear-leg roundhouse (hips turn over, torso leans back, the kicking-side arm swings),
    her teep the lead-leg thrust kick (knee chambered, relaxed arms, steps down forward; credited, 38 Mixamo clips),
    both keeping 85% of the
    guard hand's motion; her jab, horizontal elbow and Flame Elbow keep 75%.
  - Every fighter has every hit reaction (the `pkg-62` gap).
- **Review and regression.** Packaged as `pkg-63-flow`. Recorded against `pkg-60` (what the creator played), each
  pair aligned on the first match: punches and reactions (`anim-96`) and movement into strikes (`anim-97`: jabs from
  walking forward and back, taps, walk into Heavy and into the light string). The smoke test (no missing animations),
  the controls self-tests, the 25-step journey and the 12-match matrix all passed, with 0 failures and 0 warnings
  (`anim-98`).

### Jumping (packages `pkg-64-jump` to `pkg-66-jump`)

- **Why.** The creator's playtest: there was no jump, and jumping is a big part of fighting games.
- **Simulation** (rules in `rules.json`, see the combat contract). Up from neutral jumps straight up, toward or away:
  a 4-tick squat on the floor, 36 ticks in the air on a 90 cm arc (126 cm toward, 105 cm away), 4 ticks of landing
  recovery (6 after a jump attack). Fighters have a height; their boxes rise with it. In the air a fighter cannot
  block or be grabbed, and any hit knocks it down and it falls. Pushboxes still apply (no crossing over). Jump attacks
  are moves marked `air`: Wren's Jumping Punch and Flying Kick, Ashka's Jumping Elbow and Jumping Knee. The CPU meets
  a seen jump-in with a jab or a block and jumps in now and then.
- **Input and presentation.** A Jump action: W, Up arrow, D-pad up and the left stick's up, remappable and saved by
  name. The fighter is lifted by the simulation's height (the floor marker stays down); jump and landing sounds; the
  move list shows "In a jump:".
- **Animation.** The jump and landing come from Mixamo's Jumping From Action Idle (credited; 39 Mixamo clips), with
  the guard held up (20% of the performer's arm swing), the rise left to the game (`root_z_cap`) and the squat dip
  scaled to fit the 4-tick squat; forward and back jumps lean with the travel. The landing absorbs at 55%. The four
  jump attacks are keyed by script on an airborne guard (legs drawn up). `pkg-64` showed hands moving 44-52 cm a frame
  in the squat and a forearm flip in Wren's punch recovery, and the audit of `pkg-65` showed the jump attacks' strikes
  moving 41-47 cm in a single frame; `pkg-65` and `pkg-66` fix them (every jump clip under 35 cm a frame, no flips).
- **Tests.** Core: the arc, squat, landing and distances in all three directions; no block or grab in the air, the
  anti-air knockdown and the fall; jump attacks hit and are blocked and land into recovery; in 36 CPU matches the CPU
  jumped 133 times, attacked from the air 74 times and was knocked out of the air 49 times; the replay-determinism
  test's recorded match now must include jumps (33 cases, 630 checks).
  The controls self-test checks D-pad up.
- **Review and regression.** `pkg-64` recorded jumping straight up, forward and back and a jump-in for each fighter
  (`anim-99`); `pkg-66` was recorded the same way with the jump-ins timed nearer the top of the arc (`anim-103`).
  The smoke test, the controls self-tests (now checking D-pad up for Jump), the 25-step journey and the 12-match
  matrix all passed on `pkg-66`, with 0 failures and 0 warnings (`anim-104`).

### Captured jump heavies (package `pkg-67-jumpkick`)

- **Change.** The heavy jump attacks were keyed poses (Wren's read as a lunge). Wren's Flying Kick now comes from
  Mixamo's Flying Sidekick From A Run (the body laid back, the lead leg driven out level through the active frames),
  Ashka's Jumping Knee from her own flying-knee capture (the knee driven up mid-leap, ending before the combo's
  punch). As with the jump, the game supplies the height and travel (`root_z_cap`, no root travel). Credited (40
  Mixamo clips). The light jump attacks stay keyed.
- **Measured.** Wrists within 11 degrees, necks within 19; under 35 cm a frame; no flips.
- **Review and regression.** The jump review recorded on `pkg-67` (`anim-105`): the flying kick connects at head
  height with the body laid back. The smoke test, the controls self-tests, the 25-step journey and the 12-match
  matrix all passed, with 0 failures and 0 warnings (`anim-106`).

## Known limitations

- **Not verified by a person:**
  - physical-controller buttons
  - feel and balance of the latest build (the creator played `pkg-60` on 2026-11-04/05; the work on that feedback,
    including jumping, has not been played yet)
  - the audio mix (no listening test)
  - exclusive fullscreen mode switching (borderless and windowed were tested)
- **Jumping (first pass).** Jumps cannot cross over the opponent (pushboxes apply in the air), there is no crouch or
  low attack to beat them, and the height, timing and jump-attack frame data are first values to tune by feel.
- **Art.**
  - The fighters are built by script from a MakeHuman base, so close-up detail (faces, hair cards) is modest.
  - Most motion comes from motion capture (ACCAD, Mixamo) placed on researched stances (after the release; see
    "Changes after the release"):
    - the idles, walks and held guards;
    - the jabs, crosses, elbows, knee and kicks;
    - Wren's double-leg slam and shoulder throw;
    - the intros, wins and defeated poses;
    - the hit, block, knockdown, KO and both get-ups.

    Wren's spinning elbow, both bursts, the rolls, the grabs and Ashka's two throws are still keyed by
    script on the same stances. The creator's playtest on 2026-11-03 rejected the scripted animation as
    unnatural; the creator has judged videos of the replacements but has not played them.
  - Coat panels can clip in the most extreme spins.
  - Walking all the way in brings the fighters chest to chest (the pushboxes keep their hips 46 cm apart). They are
    staggered 20 cm apart in depth there, so the bodies no longer pass through each other, but guarding arms can
    still cross.
  - Only Wren's primary outfit is included.
- **Presentation.** At 60 Hz on the test desktop with V-Sync (see Performance). The test monitor now runs at 165 Hz,
  but V-Sync still paces the game at exactly 60 Hz there in windowed, borderless and fullscreen modes (`anim-56`:
  16.667 ms frames). V-Sync off with a 120 fps limit gives a steady 8.334 ms, so the 60 Hz clock is the desktop's,
  not the game's. Frames at 60 fps land unevenly on a 165 Hz screen (three refreshes, three, three, then two), which
  looks like skipped frames on smooth motion. The desktop is Cinnamon 6.6.9 (Muffin 6.6.3) on X11 with one monitor
  (DP-4) on the NVIDIA driver 595.99, and Muffin is set to keep compositing full-screen windows. The game's own
  request to bypass the compositor (`SDL_VIDEO_X11_NET_WM_BYPASS_COMPOSITOR=1`) still left it at 60 Hz (`anim-60`).
  Remedies are system settings: run the monitor at 59.97 Hz, or let full-screen windows bypass the compositor
  (Cinnamon: disable compositing for full-screen windows) and play fullscreen.
- **Start-up crash (EH-07), resolved in `060a75f`.** Historical loops recorded 1 crash in 26 Shipping and 1 in 40
  Development exclusive-fullscreen starts (`anim-60`, `anim-61`), and one more in a windowed Shipping run (`anim-68`)
  that was not recorded at the time. The earlier note placed it at audio start-up with an unverified cause. It had two
  causes, an SDL display use-after-free on monitor standby or wake and a stale pointer in the engine's SDL audio
  output; see "Current candidate", EH-07, for the diagnosis, fixes and trials.
- **Borderless window (P2), resolved in `060a75f`.** Some default launches came up as a decorated window clamped to the
  desktop work area (3440 × 1368, above the Cinnamon panel). Starting straight into borderless loses the fullscreen
  request; see "Current candidate", EH-07.
- **Determinism and online.** Replays are deterministic for one binary on one machine. There is no rollback or online
  play.
- **Config noise.** `Config/DefaultEngine.ini` holds an editor-generated Android File Server block. It is unused (the
  plugin is not shipped).
- **History.** The local history includes an early commit that contained Python bytecode caches. Only the squashed branch
  `release/first-slice` is published (see `Docs/Status.md`).

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
