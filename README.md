# Ebony Hearts

Ebony Hearts is a mature dark fantasy 2.5D fighting game with action RPG influences, set in the mysterious realm of
Destiny's Ark. Featuring precision-focused combat, distinctive stylized visuals, and rich worldbuilding, the game
follows resurrected warriors fighting to claim the power of the Ebony Heart.

This branch holds the first playable slice: **Wren Ku** and **Ashka Rook** fighting in **The Drowned Chapel**.

## Status

**First playable slice: PARTIAL — NOT COMPLETE.**
- **Build.** A packaged Linux build exists and passes its automated acceptance runs on the test machine: menus and
  modes, 12-match matrix, 30+ minute soak, 1080p/60 performance, real keyboard events and a virtual gamepad.
- **Still open.** A physical-controller check, and a human playtest and listening pass.
- **Crash report.** Early in development, one editor crash report was sent to Epic Games before the opt-out was set.

Details: [Docs/Validation.md](Docs/Validation.md) and [Docs/Status.md](Docs/Status.md).

## What is in the slice

- **Fighters.** Wren Ku (MMA, bouncy all-rounder; signature 720 Hook Kick; Spirit Enhanced Strikes, a golden lightning
  aura) and Ashka Rook (Muay Thai, long upright guard; Lamplighter Flame, crimson).
- **Stage.** The Drowned Chapel: a flooded chapel nave lit by moonlight through a rose window, candles and water.
- **Six actions:** light, heavy, special, grab/throw, dodge/roll and block. Movement is left/right, and up jumps
  (straight up, toward or away), with a light and a heavy jump attack each. Each action has a "toward" or "away"
  variant judged when the button is pressed. There are no motion inputs and no chords.
- **Modes.** Versus CPU (Easy, Normal, Hard), local Versus, Training (dummy modes, hitbox and frame-advantage display,
  position reset), and a ten-step guided Lesson. Also results with rematch, settings, a move list, credits and a quit
  confirmation.
- **Settings.**
  - Display: window mode and resolution (with a confirm-or-revert timer), quality, render scale, V-Sync and frame cap.
  - Audio: master, music, effects and ambience volume.
  - Controls: rebindable keyboard and gamepad controls, and on-screen input hints.
  - Accessibility: interface scale, reduced screen shake and reduced flashing.

The rules, move tables and canon boundaries are in [Docs/CombatContract.md](Docs/CombatContract.md).

## Platform

Linux x86-64 (tested on Ubuntu with an NVIDIA GPU and the proprietary Vulkan driver) with X11 or XWayland.
Requires a Vulkan GPU with Shader Model 6 support. The target is 1920 × 1080 at 60 FPS.

Input: keyboard (two layouts, so two players can share one keyboard) and SDL-supported gamepads. In Local Versus each
player joins by pressing Confirm on their own device. If a gamepad disconnects mid-match the game pauses, and any device
can take over that side.

## Controls

| Action | Keyboard (left side) | Keyboard (right side) | PlayStation | Xbox |
|---|---|---|---|---|
| Move | A / D | Arrow keys | Left stick / D-pad | Left stick / D-pad |
| Jump | W | Up arrow | Left stick up / D-pad up | Left stick up / D-pad up |
| Light | J, or Enter | Numpad 1, or , | Square | X |
| Heavy | K, or Backspace | Numpad 2, or . | Triangle | Y |
| Special | L | Numpad 3, or / | R1 | RB |
| Grab | I | Numpad 5, or ; | Cross, or L1 | A, or LB |
| Dodge | O | Numpad 6, or ' | Circle | B |
| Block (hold) | Space | Numpad 0, or Right Shift | R2 | RT |
| Pause | Escape | Numpad 9, or = | Options | Menu |
| Training reset | R | Numpad 7, or - | Share | View |

PlayStation and Xbox share one layout by button position. Menus have their own fixed controls: Cross / A or Enter
confirms, Circle / B or Escape goes back, and Options / Menu pauses. So Cross / A grabs in a match without affecting
menus. Every gameplay action can be remapped under Settings > Controls, with separate controller layouts for players 1
and 2 and for each keyboard side. Details: [Docs/Controls.md](Docs/Controls.md).

## Running the packaged build

Download or copy `EbonyHearts-Slice-<commit>.tar.gz`, check it against `SHA256SUMS`, extract it anywhere (paths with
spaces are fine) and start the launcher:

```bash
sha256sum -c SHA256SUMS
```

```bash
tar -xzf EbonyHearts-Slice-f3ae5ab.tar.gz
```

```bash
EbonyHearts-Slice-f3ae5ab/EbonyHearts.sh
```

The first launch opens borderless at the desktop resolution. `VERSION.txt` in the extracted folder names the source
commit and content hash, and `THIRD_PARTY_NOTICES.txt` holds the licences.

Useful command-line options:
- `-ResX=1920 -ResY=1080 -fullscreen`, or `-windowed`
- `-EHVSync=0` turns V-Sync off for this run only; the setting itself is not changed.
- `-safedisplay` starts in a 1280 × 720 window and ignores saved display settings.

Settings are saved to `~/.config/Epic/EbonyHearts/Saved/EbonyHearts/Settings.json`. Delete that file to restore the
defaults.

## Building from source

Requirements: Unreal Engine 5.8.4 (installed build) with its bundled clang toolchain, Blender 5.2.2, and Python 3 with
Pillow. The full asset rebuild order (combat tests, chapel, characters, animation, audio, effects, Unreal import,
code and package) is in [Docs/Production.md](Docs/Production.md).

Build only the code and package (assuming the imported `Content/` is present):

```bash
"$UE_ROOT/Engine/Build/BatchFiles/Linux/Build.sh" EbonyHeartsEditor Linux Development -Project="$PWD/EbonyHearts.uproject"
```

```bash
"$UE_ROOT/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun -project="$PWD/EbonyHearts.uproject" -platform=Linux \
  -clientconfig=Shipping -build -cook -stage -package -pak -archive -archivedirectory="$PWD/../package" \
  -installed -nocompileeditor -skipbuildeditor -unrealexe=UnrealEditor-Cmd
```

Run the combat core tests (no engine needed):

```bash
Tests/Core/run_core_tests.sh
```

## Documents

- [Docs/CombatContract.md](Docs/CombatContract.md): rules, timing model, move tables, canon boundaries and conventions.
- [Docs/Production.md](Docs/Production.md): rebuild order and production conventions.
- [Docs/AssetLedger.md](Docs/AssetLedger.md) and [Docs/ThirdPartyManifest.json](Docs/ThirdPartyManifest.json): asset
  provenance, licences and notices.
- [Docs/Research.md](Docs/Research.md): the design decisions taken from fighting-game references, and how each was tested.
- [Docs/Validation.md](Docs/Validation.md): acceptance matrix, build identity, test results and performance.
- [Docs/Review.md](Docs/Review.md): a guide for independent review of the latest round: what changed, where, and how
  to check it.
- [Docs/Status.md](Docs/Status.md): where things stand and what is left for the creator.

## Known limitations

- **Platform.** Linux only. The build was verified on one machine (Ryzen 7 5700G, RTX 2060 6 GB, Linux Mint 22.3,
  X11). Exclusive fullscreen mode switching was not exercised; borderless and windowed were. In 1 of 5 launches on
  Cinnamon, the borderless window stopped above the desktop panel.
- **Evaluation.** Nobody has playtested the slice by hand, and nobody has listened to the mix. Every frame, damage and
  CPU value is an untested tuning proposal (see the combat contract).
- **Controllers.** Gamepads were verified with a virtual Xbox 360 pad, including disconnect and reconnect. A physical
  PS4 controller was detected, but nobody pressed its buttons.
- **Art.**
  - The fighters are built by script from a MakeHuman base. They read well at gameplay distance, but close-up detail
    (faces, hair cards) is modest.
  - Both fighters stand in researched stances (Wren MMA, Ashka Muay Thai; see `Docs/Research.md`). Most motion comes
    from motion capture (ACCAD and Mixamo):
    - the idles, walks and held guards;
    - Wren's jab, cross (and jab-to-cross string), four kicks and Spirit Enhanced Strikes;
    - Ashka's jab, both elbows, step-in knee, flying knee, body kick and teep;
    - Wren's double-leg slam and shoulder throw (both sides), and the falls of the fighters Ashka throws;
    - both fighters' forward roll, jump and landing, and heavy jump attack;
    - both fighters' intros, wins and defeated poses;
    - both fighters' hit reactions (by where each hit lands), block, knockdown, KO and get-ups.

    The remaining moves are keyed by script on the same stances: Wren's spinning elbow, Ashka's Flame Burst, the back
    rolls, grabs, Ashka's clinch and the light jump attacks. Moves blend into each other with inertial transitions,
    the legs settling over their own time so a strike from a walk finishes the step. Coat panels
    and braids are spring-simulated, and they can clip in the most extreme spins.
  - Only Wren's primary outfit is in the slice.
- **Audio.** Music, ambience and most effects are synthesized for the slice, with CC0 layers. There are no voices.
- **Determinism and online.** Replays are deterministic for one binary on one machine. There is no rollback, online
  play or replay saving.

## Rights

Ebony Hearts, its characters and its world belong to Markus Gillyard / Cinqic. All rights reserved. Third-party inputs
and their licences are listed in [Docs/AssetLedger.md](Docs/AssetLedger.md). The packaged game ships
`THIRD_PARTY_NOTICES.txt`. The title card was generated for the game by the creator with OpenAI's ChatGPT image
generation and is used with the creator's authorization; the ledger records its origin and rights.
