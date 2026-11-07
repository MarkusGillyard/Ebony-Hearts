# Status and handoff

Updated 2026-11-07.

## Where things stand

**READY FOR THE CREATOR'S PLAYTEST — NOT APPROVED, NOT MERGED.** The start-up crash that blocked the last review
(EH-07) had two causes, both outside the game's code; both are fixed in the game's start-up path and checked on the
candidate below. The objective checks in [Validation](Validation.md) pass on that candidate. What remains needs a
person: the creator's hands-on test (below), then a new independent review of the exact pull-request head.

- **Candidate:** `EbonyHearts-Slice-060a75f.tar.gz` (Shipping, Linux), built from commit `060a75f`; SHA-256
  `06b34f4a09d5c46f850f5d61c642c737d4a8bcdc98032ac5843f206805ba618f`. Later commits on the branch change documentation only.
- **Pull request #1** (`release/first-slice` → `main`) is open. Nothing has been merged, tagged or released.

## What changed in this round

- **Start-up crash (EH-07).** SDL could free a monitor's display while the game changed into fullscreen if the monitor
  went to standby or woke at that moment; and the engine's SDL audio output could overwrite the stack of SDL's audio
  thread when audio started. The game now applies monitor hot-plug events at the start of a frame and uses its own
  SDL audio output. Details, crash dumps and the with/without comparisons: Validation, "Current candidate".
- **Borderless window.** Starting in borderless sometimes left a window with a title bar, short of the desktop panel.
  The game now checks and corrects it; and launch flags (`-fullscreen`, `-windowed`, `-safedisplay`) no longer change
  the mode the next normal launch starts in.
- **Tests.** A start-up loop that classifies every launch, window and platform checks in every packaged run, hot-plug
  and audio probes, combat-state hash coverage and throw-timeout boundaries (828 core checks), and safer release
  staging.

## How to test the candidate

```bash
sha256sum -c SHA256SUMS
```

```bash
tar -xzf EbonyHearts-Slice-060a75f.tar.gz
```

```bash
EbonyHearts-Slice-060a75f/EbonyHearts.sh
```

It starts borderless at the desktop resolution, or in your saved mode. Settings are in
`~/.config/Epic/EbonyHearts/Saved/EbonyHearts/Settings.json`.

## For the creator

1. **Physical controller (about 10 minutes).** With the PS4 controller connected, press Cross on the title screen and
   pick Training:
   - Square: Light. Triangle: Heavy. Circle: Dodge. Cross and L1: Grab. R1: Special. R2: Block while held.
   - D-pad or left stick: walk; up jumps. Options: pause.
   - In menus, Cross confirms and Circle goes back; prompts show PlayStation shapes.
   - Settings > Controls > Controller - Player 1: move one action to another button, try Swap, then restore.
   - Unplug or switch the controller off mid-match and back on.
2. **Play.** Training, Versus CPU at every level, and local Versus if a second player is available. Judge
   responsiveness, spacing, combos and throws, jumping, readability, fairness and fun.
3. **Motion at game speed.** Punch reach, guards and stances, hit reactions, necks, wrists and thumbs, transitions,
   Wren's and Ashka's throws, jumps and jump attacks, cloth and coat clipping, the golden aura and the crimson flame.
4. **Listening.** Select the TV or soundbar as the output first (the monitor's speakers do not work; the game follows
   a change of output while it runs). Music, ambience and effects: balance, clipping and fatigue.
5. **Decide.** Accept the tuning or ask for changes; then authorize a new independent review of the pull-request head,
   and later any merge.
6. **Optional.** Filing the two upstream bug reports drafted during the investigation (SDL, Epic) is your call; they
   are public actions.
7. **Optional display setting.** On the 165 Hz monitor, V-Sync paces the game at 60 Hz in every window mode, so
   motion lands unevenly. For smooth motion, run the monitor at 59.97 Hz, or disable compositing for full-screen
   windows in Cinnamon and play fullscreen (Validation, Known limitations).

## History

The slice was published as `release/first-slice` and opened as pull request #1 on 2026-11-03, at the creator's
request, and has been updated with squashed commits after each review round since. The creator played `pkg-60` on
2026-11-04/05; the work on that feedback (punches, reactions, wrists and necks, flow, Ashka's kicks, jumping) is in the
candidate but has not been played yet. The title card's origin and authorization were confirmed on 2026-11-03
([asset ledger](AssetLedger.md#creator-supplied)). One editor crash report was sent to Epic Games early in
development, before crash reporting was turned off; the packaged game has no crash reporter.

## Implemented, tested, observed and not verified

- **Tested by automation on the candidate** (details in Validation, "Current candidate"):
  - combat core (828 checks) and release-staging tests;
  - smoke, controls, the menu journey, real keyboard events and simulated Xbox and DualShock 4 pads (including
    disconnect, reconnect and remapping), 12 complete matches, the motion review scripts and signature footage;
  - a 58-minute soak (36 matches, flat memory) and frame-time captures at 1080p and the native resolution;
  - 385 starts across every display mode, first runs and launches from monitor standby, all clean; mode changes,
    monitor standby during a mode change, focus loss and audio output changes.
- **Observed only:** the PS4 controller was detected as a PlayStation pad; nobody pressed its buttons.
- **Not verified:** physical controller buttons, a person's playtest of feel and balance, a listening pass, and
  hardware other than the test machine (Validation lists it).
