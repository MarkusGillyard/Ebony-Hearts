# Status and handoff

Updated 2026-11-05.

## Where things stand

**PARTIAL — NOT COMPLETE.** The slice is implemented, and the packaged Linux build passed every automated acceptance
run on the test machine (see [Validation](Validation.md)). It is not declared complete because:
- **People.** Three checks need a person: physical-controller buttons, a hands-on playtest of the latest build (the
  creator played `pkg-60` on 2026-11-04/05; the work on that feedback is not yet played), and a listening pass on the mix.
- **Crash report.** Early in development, one editor crash report was sent to Epic Games before the opt-out was set.
  It is recorded as a Preservation failure.

**Published.** On 2026-11-03, at the creator's request, `release/first-slice` was pushed to
`MarkusGillyard/Ebony-Hearts` and opened as pull request #1 into `main`. On 2026-11-04 the creator asked for it to be
updated with the animation work, and it was, as squashed commits on top; it is updated the same way after each round.
Nothing has been merged, tagged or released.

**Animation after the creator's reviews (2026-11-03 and 2026-11-04).** Each step, with its measurements, is in the
[validation report](Validation.md) (packages `pkg-21` to `pkg-67`):
- **Captured** (Mixamo and ACCAD): the idles, walks and guards; the jabs, crosses, elbows, knee and kicks; Wren's
  jab-to-cross string; Wren's double-leg slam and shoulder throw; both fighters' forward roll; Wren's power-up; the hit and block
  reactions, knockdowns, KO, both get-ups; the intros, wins and defeated poses.
- **Still keyed by script:** Ashka's two throws up to the trip (their victims then fall as captured), the grabs, the
  back rolls, Ashka's Flame Burst, Wren's spinning back elbow and the two light jump attacks. No capture tried so far fits them; Mixamo has no back roll
  or quick grab.
- **Throws** are drawn as authored (the victim was drawn mirrored), switch sides cleanly, and keep a knocked-out
  victim lying. Both fighters ease into a throw from where they stood, and an escape starts from where the throw was. Rolls stay above the floor, and a fighter knocked down lies on it. **Effects:** the golden aura and the crimson flame were rebuilt.
**After the creator's playtest (2026-11-05)** (packages `pkg-61` to `pkg-67`): punches straighten to full extension
and reach their boxes; each hit names its reaction (hooks turn the head away, body shots fold the body) and reactions
show contact during hitstop; fists stay in line with the forearm, thumbs wrap and necks bend naturally; strikes from a
walk finish the step; guards turn with the body; Ashka's body kick and teep are captured; and **jumping** is in the
game (up on every device; jump attacks; anti-air; the CPU uses both). Jump values are first passes to tune by feel.
On the build under review, performance and a 59-minute soak were re-run and match the original release.
- **Display.** On the test desktop the monitor runs at 165 Hz but V-Sync paces everything at 60 Hz, so motion looks
  like it skips. This is a system setting (see Validation, Known limitations).

## What was delivered

- **Game.** A standalone Linux build of the slice: Wren Ku and Ashka Rook, The Drowned Chapel, the six actions,
  Versus CPU, local Versus, Training, the Lesson, results with rematch, settings, the move list and credits.
- **Release.** `EbonyHearts-Slice-f3ae5ab.tar.gz` (Shipping, commit `f3ae5ab`), SHA-256
  `57886ee502edaf2482939b9d0282cf5d357f6577a3e14436c3264082ff064d74`. It contains `THIRD_PARTY_NOTICES.txt` and
  `VERSION.txt`. A per-file checksum list ships beside the archive.
- **Source and editable content.** This repository: game code, combat data, the scripts that build every asset, the
  Unreal content they produced, and the tests.
- **Documents.**
  - [README](../README.md)
  - [Combat and art contract](CombatContract.md)
  - [Design research](Research.md)
  - [Asset ledger](AssetLedger.md)
  - [Production guide](Production.md)
  - [Validation report](Validation.md)

## How to launch the verified build

```bash
tar -xzf EbonyHearts-Slice-f3ae5ab.tar.gz
```

```bash
EbonyHearts-Slice-f3ae5ab/EbonyHearts.sh
```

The game starts borderless at the desktop resolution. Change the display mode in Settings > Video. To start in a
1920 × 1080 window instead, run:

```bash
EbonyHearts-Slice-f3ae5ab/EbonyHearts.sh -windowed -ResX=1920 -ResY=1080
```

## Implemented, tested, observed and not verified

- **Implemented and tested by automation:**
  - the combat rules (core suite)
  - every menu path
  - 12 complete matches across both fighters, sides, mirrors, CPU levels and local versus
  - a 30+ minute soak
  - real X11 key events
  - a virtual gamepad, including disconnect and reconnect
- **Observed:**
  - packaged screenshots and footage of menus, matches and the signature moves
  - frame-time captures on the test machine
- **Not verified:**
  - **Physical controller.** A PS4 controller was connected and detected throughout testing, but nobody pressed its
    buttons.
  - **Human play.** No human playtest of balance, feel or difficulty took place.
  - **Listening.** No listening test of the mix took place.
  - **Exclusive fullscreen.** Tested since: it works, apart from a rare startup crash in the engine's audio backend
    (about one launch in 30 to 40, in any mode; see Validation, Known limitations).

## Remaining items for the creator

1. **Physical controller check (about 5 minutes).** Launch the build with the PS4 controller connected. Press Cross
   on the title screen and pick Training. Check that each button does what the new layout says:
   - Square: Light. Triangle: Heavy. Circle: Dodge. Cross and L1: Grab. R1: Special.
   - R2: Block while held, stopping on release.
   - D-pad or left stick: walk (toward + a button gives the toward move); up jumps. Options: pause.
   - In menus, Cross confirms and Circle goes back; on-screen prompts show PlayStation shapes.
   - In Settings > Controls > Controller - Player 1, move one action to another button and try Swap.
   Then unplug and replug the controller mid-match. Simulated DualShock 4 and Xbox 360 pads already pass these
   steps, but they are not physical hardware.
2. **Playtest and listening.** Play a few matches against each CPU level and in Training. Note anything that feels
   unfair, slow or unclear, and anything in the mix that is too loud, too quiet or grating.
3. **Title card.** Done on 2026-11-03. The creator confirmed it is an authorized, AI-generated project asset (OpenAI
   ChatGPT image generation). Origin, rights and handling are in the [asset ledger](AssetLedger.md#creator-supplied).
4. **Animation and jumping review.** Watch the latest videos (the creator has been sent each one) and play the latest
   build: punches, reactions, moving into strikes, Ashka's kicks, and jumping (height, speed and the jump attacks).
   For more captured motion (rolls, grabs, Ashka's throws), sign in to Mixamo again in the built-in browser.
5. **Display setting (optional).** For smooth motion on the 165 Hz monitor, either run it at 59.97 Hz, or disable
   compositing for full-screen windows in Cinnamon and play fullscreen.
6. **Merge and release.** `release/first-slice` is published as squashed commits. The local working history,
   which includes an early commit with Python bytecode caches, is not published. Merging pull request #1 into
   `main`, tagging a version and making a GitHub release each need your explicit go-ahead.

## Next safe action

For an independent review of the latest round, start with [Review](Review.md).

Do the controller check, the playtest and the animation review (items 1, 2 and 4 above). After the playtest, the creator plans to have pull
request #1 merged into `main`. Nothing will be merged, tagged or released without that decision.
