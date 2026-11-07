# Review guide: start-up crash remediation (EH-07)

This guide is for reviewing `release/first-slice` (pull request #1) after the remediation round that followed the
independent review of `1a8f8a9` (2026-11-06, "changes required": an intermittent start-up crash with no verified cause).
The earlier rounds, with their measurements, are in the [validation report](Validation.md); rules and move data are in
the [combat contract](CombatContract.md).

**Candidate:** package built from commit `060a75f` (Shipping, Linux), released as `EbonyHearts-Slice-060a75f.tar.gz`,
SHA-256 `06b34f4a09d5c46f850f5d61c642c737d4a8bcdc98032ac5843f206805ba618f`. Commits after `060a75f` change
documentation only. Results on that package: Validation, "Current candidate" (battery, one-hour soak, 385 clean
starts, the with/without comparisons).

## 1. What changed and where

| Finding | Cause | Change | Where | Checked by |
|---|---|---|---|---|
| EH-07a: start-up SIGSEGV in fullscreen (`pkg-45` dump) | SDL 3.4.4 frees an `SDL_VideoDisplay` when an XRandR output disconnects (monitor standby or wake) while its own fullscreen call, waiting on the window manager, still uses it | XRandR events are held back from SDL and re-queued for an event pump at the start of the next frame | `Source/EbonyHeartsLinux/Private/EHDisplayEventGuard.*` | `display_hotplug.txt`; with the guard disabled (Development only) the same binary crashed 3/3 at the original site |
| EH-07b: start-up SIGSEGV on SDL's audio thread (two dumps, fullscreen and windowed) | UE 5.8.4 `AudioMixerSDL` keeps a pointer to a buffer on the SDL thread's stack and copies into it from other threads; gdb shows the write landing just below that thread's stack pointer | The game's own SDL3 output, selected in `Config/Linux/LinuxEngine.ini`; it renders into a buffer it owns and drops off-thread submissions | `Source/EbonyHeartsLinux/Private/EHSdlAudioOutput.*`, `EbonyHeartsLinuxModule.cpp` | `platform_check` in every run (`dropped=1`: the render thread's start-up prime); `audio_offthread.txt` (Development) |
| P2: borderless window clamped to the work area | The fullscreen request for a window created hidden is lost; the engine also saved each session's live display on exit, so test launch flags decided the next start | The engine's start-up display follows the saved settings; a fullscreen or borderless window that does not cover its monitor half a second after a change is asked again (at most twice) | `Source/EbonyHearts/Game/EHGameDirector.cpp` (`ApplySettings`, `SaveEngineDisplay`, `VerifyFullscreenApplied`) | `window_check` in every start-up loop, `display_modes.txt` |
| Hash coverage not proven per field | — | `HashState()` (same value) and a test that perturbs every field | `Source/EbonyHearts/Core/EHMatch.*`, `Tests/Core/CoreTests.cpp` | `state_hash_covers_every_field` |
| Throw damage at the timeout boundary tested at one point | — | Before / on / after the damage tick, both throwers, into the next round | `Tests/Core/CoreTests.cpp` | `timeout_throw_boundaries_both_sides` |
| Release staging could leave a half-staged release, overwrite an archive, or call a Development build Shipping | — | Whole-package checks before writing; never overwrites | `Tools/Package/stage_release.py` | `Tests/Package/test_stage_release.py` (9 tests) |
| Contract prose named a belly-to-belly suplex | The captured Shoulder Throw replaced it in `pkg-44` | Prose corrected | `Docs/CombatContract.md` | — |

## 2. Check it yourself

- **Core.** `Tests/Core/run_core_tests.sh`: 37 cases, `828 checks, 0 failures`. Remove the `Phase::Fight` condition on
  throw damage in `Match::AdvanceThrow`, or one `Mix` line in `HashState`, and the new tests fail.
- **Packaging.** `python3 -m unittest discover -s Tests/Package -p 'test_*.py'`: 9 tests.
- **Start-up loop.** `python3 Tests/Auto/launch_loop.py --launcher <release>/EbonyHearts.sh --runs 50 --out <empty dir>
  -- -fullscreen -ResX=1920 -ResY=1080`. Every attempt should be `clean`; `attempts.jsonl` has the details.
- **Monitor standby during a mode change.** Launch the release with `-windowed -ResX=1280 -ResY=720
  -EHAuto=<checkout>/Tests/Auto/display_hotplug.txt -EHEvidence=<dir>` (an absolute script path: the package does not
  contain `Tests`); `auto_log.txt` shows `ok display_hotplug_probe ... standby_deferred=1` five times.
- **Comparison without the fixes** needs a Development package: `-EHNoDisplayEventGuard` with `display_hotplug.txt`
  crashes; `-ini:Engine:[Audio]:AudioMixerModuleName=AudioMixerSDL` selects the engine's audio output.

## 3. Where to look closely

- **The audio output replaces an engine module.** It implements the same interface with the same format; device
  enumeration, start, stop, suspend and the null device follow the engine's behaviour. Device changes rely on SDL's
  default-device handling, as the engine's output did; switching the default output while playing moved the game's
  audio to it (Validation). It must be revisited when the engine is updated.
- **Display events arrive one frame late.** SDL learns about a monitor change at the start of the next frame instead
  of mid-frame. The guard is installed only in the game (not the editor) and only matters on X11.
- **The fullscreen re-request** depends on a timing window (half a second after a display change) and acts only when
  the window does not cover its monitor; `window_check ... reasserted=N` shows when it acted.
- **Upstream.** Neither defect is fixed upstream as far as checked (SDL main, UE 5.8.4 source). Draft reports exist in
  the delivery workspace; filing them is the creator's decision.

## 4. Open

- For the creator: physical controller, playtest of feel and balance, motion at game speed, listening (see
  [Status](Status.md)).
- Not verified: hardware other than the test machine; Wayland sessions; monitors that do not disconnect in standby.
- The animation sources (raw captures, `.blend` files) are outside the repository, so clips cannot be rebuilt from a
  checkout alone (unchanged from earlier rounds).

## 5. Commit structure

Six focused commits on top of the reviewed head `1a8f8a9` (platform layer; start-up display; automation and launch loop;
core tests; staging; contract), then documentation. Earlier history is unchanged; nothing has been merged, tagged or
released.
