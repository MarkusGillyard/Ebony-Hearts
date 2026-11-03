# Status and handoff

Updated 2026-11-03.

## Where things stand

**PARTIAL — NOT COMPLETE.** The slice is implemented, and the packaged Linux build passed every automated acceptance
run on the test machine (see [Validation](Validation.md)). It is not declared complete because:
- **People.** Three checks need a person: physical-controller buttons, a hands-on playtest of feel and balance, and a
  listening pass on the mix.
- **Crash report.** Early in development, one editor crash report was sent to Epic Games before the opt-out was set.
  It is recorded as a Preservation failure.

**Published.** On 2026-11-03, at the creator's request, `release/first-slice` was pushed to
`MarkusGillyard/Ebony-Hearts` and opened as pull request #1 into `main`. Nothing has been merged, tagged or released.

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
  - **Exclusive fullscreen.** It was not tested, to avoid changing the test monitor's display mode.

## Remaining items for the creator

1. **Physical controller check (about 5 minutes).** Launch the build with the PS4 controller connected. Press Cross
   on the title screen and pick Versus CPU. In a match, check that each action does what the Controls table says:
   - Cross: Light. Circle: Heavy. Triangle: Special. Square: Grab.
   - L1/L2: Dodge. R1/R2: Block (hold).
   - D-pad or left stick: walk. Options: pause.
   Then unplug and replug the controller mid-match.
2. **Playtest and listening.** Play a few matches against each CPU level and in Training. Note anything that feels
   unfair, slow or unclear, and anything in the mix that is too loud, too quiet or grating.
3. **Title card.** Done on 2026-11-03. The creator confirmed it is an authorized, AI-generated project asset (OpenAI
   ChatGPT image generation). Origin, rights and handling are in the [asset ledger](AssetLedger.md#creator-supplied).
4. **Merge and release.** `release/first-slice` is published as one squashed commit. The local working history,
   which includes an early commit with Python bytecode caches, is not published. Merging pull request #1 into
   `main`, tagging a version and making a GitHub release each need your explicit go-ahead.

## Next safe action

Do the controller check and the playtest (items 1 and 2 above). After the playtest, the creator plans to have pull
request #1 merged into `main`. Nothing will be merged, tagged or released without that decision.
