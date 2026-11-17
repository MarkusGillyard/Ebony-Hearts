# Ebony Hearts

Ebony Hearts is a mature dark fantasy 2.5D fighting game with action RPG influences, set in the mysterious realm of
Destiny's Ark. Featuring precision-focused combat, distinctive stylized visuals, and rich worldbuilding, the game
follows resurrected warriors fighting to claim the power of the Ebony Heart.

This branch holds the first playable slice: **Wren Ku** and **Ashka Rook** fighting in **The Drowned Chapel**.

## Status

The first fighting slice and Still Water interface are integrated into `main`. PRs
[#2](https://github.com/MarkusGillyard/Ebony-Hearts/pull/2),
[#1](https://github.com/MarkusGillyard/Ebony-Hearts/pull/1), and
[#3](https://github.com/MarkusGillyard/Ebony-Hearts/pull/3) merged on 2026-11-11.
The repository audit began on 2026-11-17 at `5a51e96e72a7f678340cd191de42f36e45f92a47`;
[Status](Docs/Status.md), [Review](Docs/Review.md), and [Validation](Docs/Validation.md) record its
qualification and remaining limits. Integration does not establish creator acceptance of combat or animation feel.
No GitHub release or tag exists as of the audit's initial inventory; review packages are local engineering artifacts.

The current priority is reliable, polished fighting mechanics. **Adventure Mode** (formerly Proto Mode) is a future
concept for 3D exploration transitioning into 2.5D combat; it is not implemented. PC development and an eventual Steam
release are intended. The game is intended to be free, has no fixed release deadline, and targets mature content;
no ESRB rating has been awarded. Online play and console ports are outside the current slice.

## What is in the slice

- **Fighters.** Wren Ku (MMA, bouncy all-rounder; signature 720 Hook Kick; Spirit Enhanced Strikes, a golden lightning
  aura) and Ashka Rook, The Last Lamplighter (Muay Thai, long upright guard; front kick, spinning elbow, flying knee,
  teep, clinch trip; Lamplighter Flame, crimson).
- **Stage.** The Drowned Chapel: a flooded chapel nave lit by moonlight through a rose window, candles and water.
- **Six actions:** light, heavy, special, throw, dodge/roll and block. Movement is left/right; up jumps (straight up,
  toward or away) and down crouches. Directions modify buttons, judged when the button is pressed: toward / away pick
  a toward/away move, and down + Heavy is the uppercut, down + Light the low attack. There are no motion inputs and no
  chords.
- **How they fit together.** A standing guard stops high, mid and overhead hits; a crouching guard (down + Block)
  stops lows and mids, and crouching ducks highs. Jump attacks coming down are overheads, so jumping in opens a
  crouching guard, and a deep jump-in leads into a ground string. The uppercut (down + Heavy) knocks jumpers out of
  the air and launches, but is badly punished if blocked. Throws beat any guard up close; a throw right after a light
  that hits is a combo throw that cannot be escaped, and a neutral throw can be escaped with Throw. A well-timed block
  (deflect) shortens blockstun. Rolls pass through strikes but leave a punishable recovery.
- **Throws are standalone.** Each fighter has one throw: Wren's double-leg takedown and Ashka's Muay Thai clinch trip.
  There is no clinch state, ground position or grappling minigame; the old directional throw set stays in the code
  and data, switched off (`"grappling": false` in `Content/Data/rules.json`).
- **Modes.** Versus CPU (Easy, Normal, Hard), local Versus, Training (dummy modes including crouch, hitbox and
  frame-advantage display, position reset), and a 14-step guided Lesson. Also results with rematch, settings, a move
  list, credits and a quit confirmation.
- **Settings.**
  - Display: window mode and resolution (with a confirm-or-revert timer), quality, render scale, V-Sync and frame cap.
  - Audio: master, music, effects and ambience volume.
  - Controls: rebindable keyboard and gamepad controls, and on-screen input hints.
  - Accessibility: interface scale, reduced screen shake and reduced flashing.

The rules, move tables and canon boundaries are in [Docs/CombatContract.md](Docs/CombatContract.md).

## Platform

Linux x86-64 with X11 (tested on Linux Mint 22.3, Ubuntu-based, with an NVIDIA GPU and the proprietary Vulkan driver;
XWayland and Wayland sessions were not tested).
Requires a Vulkan GPU with Shader Model 6 support. The target is 1920 × 1080 at 60 FPS.

Input: keyboard (two layouts, so two players can share one keyboard) and SDL-supported gamepads. In Local Versus each
player joins by pressing Confirm on their own device. If a gamepad disconnects mid-match the game pauses, and any device
can take over that side.

## Controls

| Action | Keyboard (left side) | Keyboard (right side) | PlayStation | Xbox |
|---|---|---|---|---|
| Move | A / D | Left / Right arrows | Left stick / D-pad | Left stick / D-pad |
| Jump | W | Up arrow | Left stick up / D-pad up | Left stick up / D-pad up |
| Crouch (hold) | S | Down arrow | Left stick down / D-pad down | Left stick down / D-pad down |
| Light | J, or Enter | Numpad 1, or , | Square | X |
| Heavy | K, or Backspace | Numpad 2, or . | Triangle | Y |
| Special | L | Numpad 3, or / | Cross | A |
| Throw | U | Numpad 4, or M | L1 | LB |
| Dodge | O | Numpad 6, or ' | Circle | B |
| Block (hold) | Space | Numpad 0, or Right Shift | R2 | RT |
| Pause | Escape | Numpad 9, or = | Options | Menu |
| Training reset | R | Numpad 7, or - | Share | View |

PlayStation and Xbox share one layout by button position; it follows Mortal Kombat's (R1 / RB and L2 / LT are left
free). Menus have their own fixed controls: Cross / A or Enter confirms, Circle / B or Escape goes back, and Options /
Menu pauses. Down + Heavy is the uppercut and down + Light the low attack; up wins over down when both are held. Every
gameplay action can be remapped under Settings > Controls, with separate controller layouts for players 1 and 2 and for
each keyboard side. Saved controls from earlier builds move to this layout where they were still on the old defaults;
anything the player changed stays. Details: [Docs/Controls.md](Docs/Controls.md).

## Running the packaged build

Obtain a local review package `EbonyHearts-Slice-<commit>.tar.gz` from the project owner (none is published on GitHub).
Use the exact name supplied with its checksums; the commands below use a placeholder. Copy it, check it against `SHA256SUMS`, extract it anywhere (paths with
spaces are fine) and start the launcher:

```bash
sha256sum -c SHA256SUMS
```

```bash
tar -xzf "EbonyHearts-Slice-<commit>.tar.gz"
```

```bash
"EbonyHearts-Slice-<commit>/EbonyHearts.sh"
```

The first launch opens borderless at the desktop resolution. `VERSION.txt` in the extracted folder names the source
commit and content hash, and `THIRD_PARTY_NOTICES.txt` holds the licences.

Useful command-line options (each lasts for that run only; the saved settings are not changed):
- `-ResX=1920 -ResY=1080 -fullscreen`, or `-windowed`
- `-EHVSync=0` turns V-Sync off.
- `-safedisplay` starts in a 1280 × 720 window and ignores saved display settings.

Settings are saved to `~/.config/Epic/EbonyHearts/Saved/EbonyHearts/Settings.json`. Delete that file to restore the
defaults.

## Building from source

Requirements for code and packaging: Unreal Engine 5.8.4 (installed build) with its bundled clang toolchain,
Git LFS, and a Linux Vulkan environment. Set `UE_ROOT` to the installed engine directory containing `Engine/`.
Fetch the actual imported assets with `git lfs install` and `git lfs pull`; a pointer-only checkout cannot cook the game.
Blender 5.2.2 and Python 3 with Pillow are additional requirements for rebuilding source art. The full asset rebuild order (combat tests, chapel, characters, animation, audio, effects, Unreal import,
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
- [Docs/Review.md](Docs/Review.md): findings, review dispositions, architecture, and the dated integration record.
- [Docs/Status.md](Docs/Status.md): where things stand and what is left for the creator.

## Known limitations

- **Platform.** Linux only, verified on one machine (Ryzen 7 5700G, 32 GB, RTX 2060 6 GB, Linux Mint 22.3, Cinnamon on
  X11). On Linux the engine draws fullscreen and borderless as a desktop-sized window, so `-fullscreen` at a lower
  resolution costs as much GPU time as the native one. The game carries its own fixes for two engine/SDL defects
  (`Source/EbonyHeartsLinux`, see `Docs/Production.md`); Wayland sessions were not tested.
- **Evaluation.** The creator played `4cee9c1` on 2026-11-07 and began another playtest on 2026-11-09.
  Their identified priorities are unrealistic animation transitions and broken-looking/feeling throws. Targeted
  repairs were integrated, but overall movement and throw feel still require creator judgment. Automated checks do not settle gameplay feel, balance, or
  acceptance of the tuning values (see the combat contract). The creator verified TV audio on the earlier `060a75f`
  candidate; an independent listening check of this candidate has not been recorded.
- **Controllers.** Gamepads were verified with simulated Xbox 360 and DualShock 4 pads, including disconnect, reconnect
  and remapping. The creator physically checked a PS4 controller on `060a75f`, and played the `5d5c316` candidate with
  a Bluetooth DualShock 4 and reported that it works; that session has no per-button log.
- **Art.**
  - The fighters are built by script from a MakeHuman base. They read well at gameplay distance; close-up detail is
    modest: Ashka's face is a MakeHuman head with painted shading, her bangs and ponytail are hair cards, and her
    shirt and Wren's ankle wraps are fixed geometry rather than simulated cloth.
  - Both fighters stand in researched stances (Wren MMA, Ashka Muay Thai; see `Docs/Research.md`). Most motion comes
    from motion capture (ACCAD and Mixamo):
    - the idles and walks;
    - Wren's jab, cross (and jab-to-cross string), four kicks and Spirit Enhanced Strikes;
    - Ashka's jab, both elbows, step-in knee, flying knee, body roundhouse and teep;
    - Wren's double-leg takedown and shoulder throw (both sides), and the falls in Ashka's older clinch throws;
    - both fighters' forward roll, jump and landing, and heavy jump attack;
    - both fighters' intros, wins and defeated poses;
    - both fighters' hit reactions (by where each hit lands), knockdown, KO and get-ups.

    The guards and blocked-hit reactions are keyed since 2026-11-09. Other moves keyed by script on the same stances include: both spinning elbows, Ashka's front kick, both
    uppercuts and low kicks, the crouches and their reactions, the uppercut's launch, Ashka's Flame Burst and clinch
    trip (with its fall), the
    back rolls, the older grabs (dormant experiments; no return is scheduled) and the light jump attacks. Moves blend into each other with inertial transitions,
    the legs settling over their own time so a strike from a walk finishes the step. Braids and Ashka's ponytail are
    spring-simulated, and they can clip in the most extreme spins.
  - Only Wren's primary outfit is in the slice.
- **Audio.** Music, ambience and most effects are synthesized for the slice, with CC0 layers. There are no voices.
- **Determinism and online.** Replays are deterministic for one binary on one machine. There is no rollback, online
  play or replay saving.

## Rights

Ebony Hearts, its characters and its world belong to Markus Gillyard / Cinqic. All rights reserved. Third-party inputs
and their licences are listed in [Docs/AssetLedger.md](Docs/AssetLedger.md). The packaged game ships
`THIRD_PARTY_NOTICES.txt`. The current logo and key art were supplied by the creator; their creation methods are not verified. The retired
title card has a separately recorded AI origin. The ledger preserves these provenance distinctions.
