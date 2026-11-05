# Controls

How Ebony Hearts reads input: the default layouts, the menu controls, and how players change their controls.
Implementation: `Source/EbonyHearts/Game/EHSettings.*` (actions, layouts, defaults, conflict rules, saving),
`EHInputRouter.*` (devices, menu and gameplay maps, triggers) and `EHDirectorFlow.cpp` / `EHDirectorUI.cpp` (the
Controls screens and button prompts).

## Default controller layout

The creator specified the face buttons, Grab, Block and Dodge. Special sits on R1 / RB because combat needs a dedicated
Special input. PlayStation and Xbox controllers share one layout by **button position**: the left face button is Square on
PlayStation and X on Xbox, and so on. Controllers of unknown make use the same positions, and their prompts name buttons
by position.

| Action | PlayStation | Xbox | Position |
|---|---|---|---|
| Light attack | Square | X | left face button |
| Heavy attack | Triangle | Y | top face button |
| Dodge / Roll | Circle | B | right face button |
| Grab / Throw | Cross, or L1 | A, or LB | bottom face button, or left bumper |
| Block (hold) | R2 | RT | right trigger |
| Special | R1 | RB | right bumper |
| Move | Left stick / D-pad | Left stick / D-pad | |
| Jump | Left stick up / D-pad up | Left stick up / D-pad up | Up from neutral; hold toward or away to jump that way |
| Pause | Options | Menu | |
| Training reset | Share | View | |

Notes:
- **Grab has two separate buttons.** Cross / A and L1 / LB are two bindings for the same action, not a combination.
  Pressing both counts as one grab. The grab stays held until both buttons are released.
- **Block follows the trigger.** R2 / RT blocks while held and stops on release. It reads the analog trigger with fixed
  thresholds: pressed at 30 % travel, released below 20 %. The engine's own digital trigger press is ignored, so one
  squeeze is exactly one press. A controller that never reports an analog trigger falls back to digital presses after its
  third press.
- **Directions modify actions as before.** "Toward" and "away" are judged when the button is pressed. There are no
  motion inputs and no chords.
- **The left stick always moves** and always navigates menus. **Options / Menu always pauses.** Neither can be
  rebound, so no layout can leave a player without movement or a way into the menus.

## Keyboard layouts

These are unchanged from the first slice. Both sides can be remapped separately.

| Action | Player 1 (left side) | Player 2 (right side) |
|---|---|---|
| Move | A / D | Arrow keys |
| Jump | W | Up arrow |
| Light attack | J, or Enter | Numpad 1, or , |
| Heavy attack | K, or Backspace | Numpad 2, or . |
| Special | L | Numpad 3, or / |
| Grab / Throw | I | Numpad 5, or ; |
| Dodge / Roll | O | Numpad 6, or ' |
| Block (hold) | Space | Numpad 0, or Right Shift |
| Pause | Escape | Numpad 9, or = |
| Training reset | R | Numpad 7, or - |

## Menu controls (fixed)

Menus use their own fixed controls, separate from the gameplay layouts. So Cross / A confirms in menus and grabs in a
match, and remapping gameplay can never lock anyone out of Settings.

| Command | Controller | Keyboard, left side | Keyboard, right side |
|---|---|---|---|
| Move the cursor | D-pad, left stick | W A S D | Arrow keys |
| Confirm | Cross / A | Enter, J, Space | Numpad 1, , |
| Back | Circle / B | Backspace, K, Escape | Numpad 2, . |
| Pause (also backs out of menus) | Options / Menu | Escape | Numpad 9, = |

## Players and devices

- **Single-player modes.** In Versus CPU, Training and the Lesson, every controller uses **Controller - Player 1**.
- **Local Versus.** Each player joins by pressing Confirm on their own controller or keyboard side. In a match, the
  controller in player 2's slot uses **Controller - Player 2**.
- **Saving.** Layouts belong to players, not to particular controllers, so unplugging, replugging or swapping a
  controller never changes them.
- **Disconnects.** If a controller disconnects mid-match, the game pauses, and any device can take over that side by
  pressing Confirm.
- **Prompts.** Button prompts follow the device each player last used: PlayStation shapes, Xbox letters, a
  position-based diamond for unknown controllers, or key names on a keyboard. Settings > Controls > Button prompts can
  force PlayStation, Xbox or keyboard prompts. Controllers are identified by the name SDL reports; for example, a
  DualShock 4 reports "PS4 Controller".

## Changing controls

Open **Settings > Controls**, then pick a layout:
- Controller - Player 1
- Controller - Player 2
- Keyboard - Player 1 (left side)
- Keyboard - Player 2 (right side)

Each layout lists every action with its primary and secondary buttons.

**On an action's page you can:**
- **Change** the primary or secondary button: choose it, then press the new button.
- **Remove** the primary or secondary button.
- **Reset** the action to its default.

**Under the list:**
- **Restore this layout's defaults** (asks for confirmation).
- **Restore all default controls**, on the Controls page (asks for confirmation).

**Rules:**
- **Cancelling.** Options / Menu or Escape cancels a change, and an unanswered change cancels itself after 6 seconds.
  Every press while waiting goes to the change, never to the menu or a match.
- **Taken buttons.** If the new button already belongs to another action, nothing changes until the player chooses:
  - **Swap:** the other action takes this slot's previous button.
  - **Replace:** the other action loses the button.
  - **Cancel.**

  A button from the action's own other slot simply trades places. Both keyboard sides share one physical keyboard, so
  the same check covers both.
- **Not bindable.** Options / Menu, Escape, Numpad 9, =, analog axes and stick directions are reserved.
- **Missing buttons.** An action may be left without a button. The list then shows **Unbound**, and leaving the layout
  warns about it.

Changes save immediately to `Settings.json` in the game's Saved folder, under format version 2. Each layout is stored by
its id (`controller1`, `controller2`, `keyboard1`, `keyboard2`), and each action by a stable id:
- `MoveLeft`, `MoveRight`
- `LightAttack`, `HeavyAttack`
- `Special`, `Grab`, `Dodge`, `Block`
- `TrainingReset`

Loading rules:
- **Version 1 files** from the first slice keep their keyboard layouts. Their controller layout moves to the new default,
  with a notice.
- **Broken layouts.** A layout with a duplicate or reserved key resets to its defaults on load, and the other layouts are
  kept.

## Tests

| Test | What it covers | Kind |
|---|---|---|
| `Tests/Auto/controls_selftest.txt` (`bindings_selftest`, `input_selftest`) | The default layout and its PlayStation / Xbox names. Menu vs gameplay roles. Conflict detection, swap, replace, trading slots, clear, reset, independent layouts, bindable keys. Save / load round trip, version-1 migration, conflicting files. Every default button through the router, both grab buttons, trigger thresholds and the early digital press, directions, player 2's layout, live remapping. | Packaged game, injected input |
| `controls_remap.txt`, then `controls_persist.txt` | Remapping through the Controls screen's code, conflict choices, clear and reset, player 2 and keyboard layouts. The results survive a restart and drive gameplay. | Packaged game, injected input |
| `controls_ui.txt` | The real Controls menus: capture, conflict page, Swap, Escape cancel, 6-second timeout, restore-all confirmation. Screenshots of every screen and of the prompts in the move list, Training, Lesson, pause and select screens, in PlayStation and Xbox styles. | Packaged game, injected input |
| `virtual_pad.py layout xbox / ds4` with `controls_pad_layout.txt` | Every default button on a simulated Xbox 360 pad and a simulated DualShock 4, through Linux uinput, SDL and Unreal. The game logs each action, the R2 / RT hold and release, and the detected device kind. | Simulated controller |
| `virtual_pad.py menu-and-fight`, `disconnect`, `remap` | Menus, a full fight with every action, pause and quit. Disconnect and reconnect mid-match. Rebinding entirely with the pad through Settings > Controls. | Simulated controller |

A physical controller check is still needed (see `Docs/Status.md`). Simulated devices go through the same system path
as real ones, but they are not physical hardware.
