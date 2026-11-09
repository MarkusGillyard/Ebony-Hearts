# Ebony Hearts

Ebony Hearts is a mature dark fantasy 2.5D fighting game with action RPG influences, set in the mysterious realm of
Destiny's Ark. Featuring precision-focused combat, distinctive stylized visuals, and rich worldbuilding, the game
follows resurrected warriors fighting to claim the power of the Ebony Heart.

This branch holds the first playable slice: **Wren Ku** and **Ashka Rook** fighting in **The Drowned Chapel**.

## Status

**Combat, animation and character pass (2026-11-08), the fighting-game control layout and Ashka refined to her
character sheet (version 2 of 2026-11-09): candidate `c6c0de2` ready for independent review and the creator's
playtest. Not merged.**
- **This round** (made on `dev/combat-pass-1108` from PR #1's earlier head `ea3ddc6`, and added to PR #1 on
  2026-11-09 at the creator's request) adds crouching and hit levels, uppercuts, standalone throws that also finish
  combos (Wren's double-leg takedown, Ashka's clinch trip), higher jumps, an audit of every clip and every
  move-to-move relationship, Wren's ankle wraps and materials, the controls, Lesson and CPU for all of it, the
  MK-style default controls, and Ashka Rook to her 2026-11-09 character sheet (version 2: a Gothic-Victorian frock
  coat with crimson lining, blouse, brocade waistcoat, crimson cravat, high-waisted trousers and ankle boots; a loose
  crimson ponytail with a black ribbon; the flame lights her coat's lining; a front kick and a spinning elbow).
- **Candidate.** `EbonyHearts-Slice-c6c0de2.tar.gz` (Shipping, Linux), built from commit `c6c0de2`. Results on the
  test machine are in `Docs/Validation.md` ("Current candidate").
- **Pull request #1** (`release/first-slice` → `main`) carries this work. Its 2026-11-08 independent technical audit
  applies to its earlier head `ea3ddc6` (`Docs/Review.md`, previous round, section 6).
- **Still open.** An independent review of this candidate, the creator's playtest and the merge decision.
- **Crash report.** Early in development, one editor crash report was sent to Epic Games before the opt-out was set.
  The packaged game has no crash reporter.

Details: [Docs/Validation.md](Docs/Validation.md) and [Docs/Status.md](Docs/Status.md).

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

Download or copy `EbonyHearts-Slice-<commit>.tar.gz`, check it against `SHA256SUMS`, extract it anywhere (paths with
spaces are fine) and start the launcher:

```bash
sha256sum -c SHA256SUMS
```

```bash
tar -xzf EbonyHearts-Slice-4cee9c1.tar.gz
```

```bash
EbonyHearts-Slice-4cee9c1/EbonyHearts.sh
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

- **Platform.** Linux only, verified on one machine (Ryzen 7 5700G, 32 GB, RTX 2060 6 GB, Linux Mint 22.3, Cinnamon on
  X11). On Linux the engine draws fullscreen and borderless as a desktop-sized window, so `-fullscreen` at a lower
  resolution costs as much GPU time as the native one. The game carries its own fixes for two engine/SDL defects
  (`Source/EbonyHeartsLinux`, see `Docs/Production.md`); Wayland sessions were not tested.
- **Evaluation.** The creator played the `4cee9c1` candidate on 2026-11-07 and reported that combat smoothness and
  jumping need refinement and the character models need work; this pass answers that. The creator began playing its
  candidate on 2026-11-09; their feedback is not in yet. Automated checks do not settle gameplay feel, balance, or
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
    - the idles, walks and held guards;
    - Wren's jab, cross (and jab-to-cross string), four kicks and Spirit Enhanced Strikes;
    - Ashka's jab, both elbows, step-in knee, flying knee, body roundhouse and teep;
    - Wren's double-leg takedown and shoulder throw (both sides), and the falls in Ashka's older clinch throws;
    - both fighters' forward roll, jump and landing, and heavy jump attack;
    - both fighters' intros, wins and defeated poses;
    - both fighters' hit reactions (by where each hit lands), block, knockdown, KO and get-ups.

    The remaining moves are keyed by script on the same stances: both spinning elbows, Ashka's front kick, both
    uppercuts and low kicks, the crouches and their reactions, the uppercut's launch, Ashka's Flame Burst and clinch
    trip (with its fall), the
    back rolls, the older grabs (kept for when grappling returns) and the light jump attacks. Moves blend into each other with inertial transitions,
    the legs settling over their own time so a strike from a walk finishes the step. Braids and Ashka's ponytail are
    spring-simulated, and they can clip in the most extreme spins.
  - Only Wren's primary outfit is in the slice.
- **Audio.** Music, ambience and most effects are synthesized for the slice, with CC0 layers. There are no voices.
- **Determinism and online.** Replays are deterministic for one binary on one machine. There is no rollback, online
  play or replay saving.

## Rights

Ebony Hearts, its characters and its world belong to Markus Gillyard / Cinqic. All rights reserved. Third-party inputs
and their licences are listed in [Docs/AssetLedger.md](Docs/AssetLedger.md). The packaged game ships
`THIRD_PARTY_NOTICES.txt`. The title card was generated for the game by the creator with OpenAI's ChatGPT image
generation and is used with the creator's authorization; the ledger records its origin and rights.
