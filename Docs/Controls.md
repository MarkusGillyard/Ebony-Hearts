# Controls

How Ebony Hearts reads input: the default layouts, the menu controls, and how players change their controls.
Implementation: `Source/EbonyHearts/Game/EHSettings.*` (actions, layouts, defaults, conflict rules, saving),
`EHInputRouter.*` (devices, menu and gameplay maps, triggers) and `EHDirectorFlow.cpp` / `EHDirectorUI.cpp` (the
Controls screens and button prompts).

## Crouch and Throw (settings format 4)

The combat pass of 2026-11-08 added a held **Crouch** action and gave the standalone **Throw** its own buttons again
(see the [Combat contract](CombatContract.md) for what they do). Defaults were chosen from keys and buttons no action
used:

| Action | Keyboard, left side | Keyboard, right side | Controller |
|---|---|---|---|
| Crouch (hold) | S | Down arrow | D-pad down, or left stick down |
| Throw | U | Numpad 4, or M | L2 / LT |

- **Down + Heavy** is the uppercut and **down + Light** the low attack. Down is a direction modifier like toward and
  away, read when the button is pressed (it stays with a press held in the 6-frame buffer); it is not a motion input or
  a chord. Down-toward + Heavy is the uppercut, not toward + Heavy.
- **Up wins over down.** With both held (or a jump button pressed while crouching) the fighter jumps; letting go of
  the jump returns to the crouch. Opposite horizontal directions still cancel each other.
- **The stick.** Each stick axis presses at 55 % and releases below 40 %, so a diagonal must pass that on both axes
  and a resting or slightly drifting stick neither crouches nor jumps. A stick pushed half way down does not crouch.
- **L2 / LT** reads the analog trigger with the same thresholds as R2 / RT (pressed at 30 %, released below 20 %).
- The crouch keys are also the menus' down (S, Down arrow, D-pad down), as the jump keys are the menus' up.
- Cross / A and up still jump; R2 / RT and L1 / LB still block. The buttons that left the old Grab in format 3 keep
  their jobs (Cross / A, I, Numpad 5 and ; jump; L1 / LB blocks).

## Default controller layout

The creator specified the face buttons, Block and Dodge. Special sits on R1 / RB because combat needs a dedicated
Special input; Throw takes the free left trigger. PlayStation and Xbox controllers share one layout by **button
position**: the left face button is Square on PlayStation and X on Xbox, and so on. Controllers of unknown make use the
same positions, and their prompts name buttons by position.

| Action | PlayStation | Xbox | Position |
|---|---|---|---|
| Light attack | Square | X | left face button |
| Heavy attack | Triangle | Y | top face button |
| Dodge / Roll | Circle | B | right face button |
| Block (hold) | R2, or L1 | RT, or LB | right trigger, or left bumper |
| Special | R1 | RB | right bumper |
| Throw | L2 | LT | left trigger |
| Move | Left stick / D-pad | Left stick / D-pad | |
| Jump | Cross, or left stick up / D-pad up | A, or left stick up / D-pad up | bottom face button; hold toward or away to jump that way |
| Crouch (hold) | Left stick down / D-pad down | Left stick down / D-pad down | |
| Pause | Options | Menu | |
| Training reset | Share | View | |

Notes:
- **Jump and Block have two buttons each.** Cross / A and D-pad up (and the left stick's up) all jump; R2 / RT and
  L1 / LB both block. They are separate bindings for the same action, not a combination: pressing two counts as one, and
  the action stays held until all are released.
- **Block follows the trigger.** R2 / RT blocks while held and stops on release. It reads the analog trigger with fixed
  thresholds: pressed at 30 % travel, released below 20 %. The engine's own digital trigger press is ignored, so one
  squeeze is exactly one press. A controller that never reports an analog trigger falls back to digital presses after its
  third press.
- **Directions modify actions.** "Toward", "away" and "down" are judged when the button is pressed. There are no
  motion inputs and no chords.
- **The left stick always moves** (and crouches and jumps) and always navigates menus. **Options / Menu always
  pauses.** Neither can be rebound, so no layout can leave a player without movement or a way into the menus.

## Keyboard layouts

Both sides can be remapped separately.

| Action | Player 1 (left side) | Player 2 (right side) |
|---|---|---|
| Move | A / D | Left / Right arrows |
| Jump | W, or I | Up arrow, Numpad 5, or ; |
| Crouch (hold) | S | Down arrow |
| Light attack | J, or Enter | Numpad 1, or , |
| Heavy attack | K, or Backspace | Numpad 2, or . |
| Special | L | Numpad 3, or / |
| Throw | U | Numpad 4, or M |
| Dodge / Roll | O | Numpad 6, or ' |
| Block (hold) | Space | Numpad 0, or Right Shift |
| Pause | Escape | Numpad 9, or = |
| Training reset | R | Numpad 7, or - |

## Menu controls (fixed)

Menus use their own fixed controls, separate from the gameplay layouts. Cross / A confirms in menus and jumps in a
match under the shipped layout.

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

Each layout lists every action with its buttons: up to three (primary, secondary and third).

**On an action's page you can:**
- **Change** the primary, secondary or third button: choose it, then press the new button.
- **Remove** any of them.
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
  the same check covers both. In a rule set without throws (`"throws"` and `"grappling"` both false), Throw is hidden
  and a button held only by it is taken without asking.
- **Not bindable.** Options / Menu, Escape, Numpad 9, =, analog axes and stick directions are reserved.
- **Missing buttons.** An action may be left without a button. The list then shows **Unbound**, and leaving the layout
  warns about it.

Changes save immediately to `Settings.json` in the game's Saved folder, under format version 4. Each layout is stored by
its id (`controller1`, `controller2`, `keyboard1`, `keyboard2`), and each action by a stable id:
- `MoveLeft`, `MoveRight`, `Jump`, `Crouch`
- `LightAttack`, `HeavyAttack`
- `Special`, `Grab` (the Throw action; its id since version 1), `Dodge`, `Block`
- `TrainingReset`

Loading rules:
- **Version 1 files** from the first slice keep their keyboard layouts. Their controller layout moves to the new default,
  with a notice.
- **Version 1 and 2 files** (before grappling was switched off): Grab's former default buttons leave Grab and take their
  new jobs (jump; L1 / LB block) wherever that slot is free and the button is not used elsewhere, with a notice. A
  button the player had given Grab themselves stays with Grab. This is also how the right keyboard's ; reaches Jump's
  third slot.
- **Version 1-3 files** (before Crouch, and with Throw unbound): Crouch and Throw get their new defaults wherever
  those keys are free in that layout. A key the player gave another action stays with that action; the new action is
  left without it and the notice names it ("S (Crouch (hold)) is used by Special ... Choose one in Settings >
  Controls"). Throw keys the player had chosen themselves stay. Nothing else changes, including video, audio and
  accessibility settings.
- **Broken layouts.** A layout with a duplicate or reserved key resets to its defaults on load, and the other layouts are
  kept.

## Tests

| Test | What it covers | Kind |
|---|---|---|
| `Tests/Auto/controls_selftest.txt` (`bindings_selftest`, `input_selftest`) | The default layouts (Crouch and Throw included) and their PlayStation / Xbox names. Menu vs gameplay roles. Conflict detection, swap, replace, trading slots, clear, reset, independent layouts, bindable keys. Save / load round trip; version-1, 2 and 3 migration (a player's own keys kept, the new action left unbound with a notice); a migrated file reloading without migrating again; conflicting files. Every default button through the router, L2 / LT throw, D-pad and stick crouch with hysteresis, up winning over down, diagonals, trigger thresholds and the early digital press, player 2's layout, live remapping. | Packaged game, injected input |
| `controls_remap.txt`, then `controls_persist.txt` | Remapping through the Controls screen's code, conflict choices, clear and reset, player 2 and keyboard layouts. The results survive a restart and drive gameplay. | Packaged game, injected input |
| `controls_ui.txt` | The real Controls menus: capture, conflict page, Swap, Escape cancel, 6-second timeout, restore-all confirmation. Screenshots of every screen and of the prompts in the move list, Training, Lesson, pause and select screens, in PlayStation and Xbox styles. | Packaged game, injected input |
| `virtual_pad.py layout xbox / ds4` with `controls_pad_layout.txt` | Every default button on a simulated Xbox 360 pad and a simulated DualShock 4, through Linux uinput, SDL and Unreal. The game logs each action, the R2 / RT hold and release, and the detected device kind. | Simulated controller |
| `virtual_pad.py menu-and-fight`, `disconnect`, `remap` | Menus, a full fight with every action, pause and quit. Disconnect and reconnect mid-match. Rebinding entirely with the pad through Settings > Controls. | Simulated controller |

The creator checked a physical PS4 controller on the earlier `060a75f` candidate. A physical button-by-button check
of the revised `4cee9c1` bindings remains unrecorded (see `Docs/Status.md`). Simulated devices go through the same
system path as real ones, but they are not physical hardware.
