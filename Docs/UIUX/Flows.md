# Flows and navigation

How a player moves through the game, as implemented in `EHDirectorFlow.cpp` (screens and menus) and `EHInputRouter`
(devices). The overhaul keeps these flows; where it changed one, the change is marked.

## Navigation rules (every screen)

- **One set of verbs:** Up/Down move, Left/Right change a value or the fighter, Confirm selects, Back returns. Every
  device sends the same verbs. Prompts show each device's own buttons, follow remapping, and can be hidden
  (Accessibility > Input hints).
- **Owner:** a menu belongs to the device that opened it: the pausing device in a match, the entering device on a
  single-player select. Other devices are ignored there. In Local Versus each player drives only their own cursor.
- **Lists wrap** at both ends. **Section headers** (training pause) are skipped.
- **Back always leaves** the current page:
  - on the main menu it opens Quit confirm;
  - in Settings it saves, and Video discards unapplied changes;
  - in Bindings it leaves the layout;
  - on Display confirm it reverts.
  No screen can trap a player, and a key capture times out or is cancelled with Escape / Options.

## Launch to fight

| Path | Presses (default choices) |
|---|---|
| Title → main menu | Any button |
| Main → Versus CPU → fighter → opponent → CPU level and side → fight | 4 Confirms (5 from the title) |
| Main → Training → fighter → partner → fight | 2 Downs, 3 Confirms |
| Main → Lesson → fighter → fight (the partner is fixed) | 3 Downs, 2 Confirms |
| Main → Local Versus → each player joins (Confirm) → chooses → locks in (Confirm) → either confirms the fight | 1 Down, 1 Confirm, then 2 Confirms per player and 1 to start |
| Results → Rematch | 1 Confirm (Rematch has focus) |
| Results → Change Fighters / Main Menu | 1–2 Downs and a Confirm |
| Main → Quit → confirm | Back (or Up once: lists wrap) and a Confirm |

**Changed:** the results screen shows the decision before the numbers, and the join prompts name Confirm (they said
Light).

## Fighter select

**Single player:** stage 0 is your fighter, stage 1 your opponent (Versus CPU) or partner (Training; the Lesson has
no stage 1), and stage 2 (Versus CPU only) the CPU level and your side. Confirm advances a stage, Back goes back one stage, and from stage 0 to the main menu. The chips
show `YOU / CPU / PARTNER · CHOOSING`, filled once `LOCKED IN`.

**Local Versus:**
- An unjoined device presses Confirm to take the first free slot.
- Left/Right moves that player's cursor.
- Confirm locks in. Back unlocks, then leaves the slot. When both slots are empty, Back returns to the main menu.
- When both are locked, either Confirm starts the fight.

## In a match

- **Pause** (each device's Pause button, or Escape) pauses immediately; the pausing device owns the menu.
  - **Versus:** Resume, Restart match, Move List, Settings, Change Fighters, Main Menu.
  - **Lesson:** Resume, Restart lesson, Skip this step, then the same.
  - **Training:** Resume; **Partner** (dummy, CPU level); **Positions** (start position, reset); **Practice aids**
    (hitboxes, frame data, input history, gauge); **More** (move list, settings, change fighters, main menu).
- **Controller disconnected:** the match pauses with a notice. Any free device pressing Confirm takes over the
  player's slot (a toast names it), and the pause menu returns.
- **Results** follow the final round (see the table above).

## Settings

- Settings → Controls (prompt style, four layouts: pad P1 and P2, keyboard A and B, restore all) · Video · Audio ·
  Accessibility.
- **Video** changes apply only on Apply, then **Display confirm** counts down 12 s and reverts unless Keep is chosen.
  Back on the Video page discards unapplied changes.
- **Bindings:** choose an action, press the new key or button (with a countdown). A conflict offers a swap. There is a
  reset per action, per layout, and for everything.
- Saved settings migrate between formats without losing the player's own choices (format 5; see `Docs/Controls.md`).

## Errors and recovery

- **Bad data:** an error screen states the problem and the file; Confirm or Escape quits.
- **Missing character assets:** a development warning at the bottom of the screen (development builds).
- **Display change that fails or is not kept:** reverts after 12 s.
- **Notices** (migrated settings, a device taking a slot) appear as a toast for 3 s.
