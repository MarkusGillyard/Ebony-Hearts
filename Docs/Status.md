# Status and handoff

Updated 2026-11-07 (evening).

## Where things stand

**PLAYED BY THE CREATOR, PROBLEMS REMAIN — IN INDEPENDENT REVIEW; NOT APPROVED, NOT MERGED.** The creator played
candidate `060a75f` on the 4K TV with the PS4 controller on 2026-11-07 and asked for four things, then for Grab's buttons
to be repurposed. All of it is in the candidate below, and the objective checks in [Validation](Validation.md) pass on
it. The creator played this candidate on 2026-11-07, covering everything in this round, and reports that problems remain (not yet itemized), and asked for the independent review of the exact pull-request head to go ahead. Merging is not
authorized.

- **Candidate:** `EbonyHearts-Slice-4cee9c1.tar.gz` (Shipping, Linux), built from commit `4cee9c1`; SHA-256
  `c5ad9309292571b400aae0aa215d8f66f945e4af6ad576527f171458f924f591`. Later commits change documentation only.
- **Pull request #1** (`release/first-slice` → `main`) is open. Nothing has been merged, tagged or released.

## Verified by the creator (2026-11-07, candidate `060a75f`)

- **PS4 controller:** works smoothly in menus and in play.
- **Audio through the TV:** clean.
- Played on the 4K TV (75% render scale, matched to the TV's 59.94 Hz). The punches were judged good enough for now,
  and Wren's kicks and the rolls are kept as they were.

## Creator playtest of `4cee9c1` (2026-11-07)

- **Played:** everything in this round: the spinning elbow, the body roundhouse, the jump rules, grappling's removal
  and the repurposed buttons.
- **Result:** problems remain. The creator has not itemized them yet; they will be recorded here when they are.
- **Decision:** proceed with the independent review now; merging is not authorized.

## What changed in this round

1. **Wren's spinning elbow** no longer contorts. At contact her right side is to the opponent and the elbow drives out
   at head height with the fist folded by her head. Before, the fist was behind her head and the arm wrapped round it.
   The left hand guards her face, the head turns ahead of the body, and the knees stay over the feet.
2. **Ashka's Heavy is a real body roundhouse** ("Body Roundhouse"). The hips turn over and the shin lands level at rib
   height. The old clip read as a straight front kick.
3. **Jumping has a job.** Holding Block does not stop a jump attack, so jumping in is how you open a guard. A jump-in
   that hits leaves you 12 frames ahead when you land, enough for your Light string, however high it connected. It
   loses to any strike (anti-air knocks the jumper down) and to a well-timed block (a deflect), which gives the
   defender the turn. One attack per jump. A jump-in only does this when it opens contact, so jump-ins cannot be
   chained into a loop (a loop found while preparing the review was fixed). The CPU uses jump-ins against a held
   guard, and anti-airs by level.
4. **Grappling is out of the game, and kept.** No grabs, throws or escapes in play. Grab is gone from Controls, the
   move list, results, Training options, the CPU and the Lesson, whose steps 6 and 7 now teach the jump-in and the
   anti-air. All grappling code, data, animations and documentation are kept, and one setting brings them back
   (`"grappling": true` in `Content/Data/rules.json`).
5. **Grab's buttons have new jobs** (your request): Cross / A jumps and L1 / LB blocks on the controller; I, Numpad 5
   and ; jump on the keyboards. Each action can now hold up to three buttons, which is what lets the right keyboard keep
   the Up arrow, Numpad 5 and ; all as jump. Saved controls from earlier builds are moved over automatically.

## How to test the candidate

```bash
sha256sum -c SHA256SUMS
```

```bash
tar -xzf EbonyHearts-Slice-4cee9c1.tar.gz
```

```bash
EbonyHearts-Slice-4cee9c1/EbonyHearts.sh
```

It starts in your saved display mode. Settings are in `~/.config/Epic/EbonyHearts/Saved/EbonyHearts/Settings.json`.

## For the creator

1. **List the problems you found** in `4cee9c1`, so they can be fixed and the reviewer can weigh them.
2. **After the independent review,** decide what to fix and, later, any merge.
3. **Optional.** Filing the two upstream bug reports drafted during the start-up crash investigation (SDL, Epic) is
   your call; they are public actions.
4. **Optional display setting.** On the 165 Hz monitor, V-Sync paces the game at 60 Hz in every window mode, so
   motion lands unevenly. For smooth motion run the monitor at 59.97 Hz, or play on the TV (Validation, Known
   limitations).

## History

The slice was published as `release/first-slice` and opened as pull request #1 on 2026-11-03, at the creator's
request, and has been updated after each review round since. The creator played `pkg-60` on 2026-11-04/05 and the
start-up-crash candidate `060a75f` on 2026-11-07 (on the TV, with the PS4 controller); this candidate answers that
second playtest. The title card's origin and authorization were confirmed on 2026-11-03
([asset ledger](AssetLedger.md#creator-supplied)). One editor crash report was sent to Epic Games early in
development, before crash reporting was turned off; the packaged game has no crash reporter.

## Implemented, tested, observed and not verified

- **Tested by automation on the candidate** (details in Validation, "Current candidate"):
  - combat core (890 checks) and release-staging tests;
  - smoke, controls (including an older settings file moving Grab's buttons to their new jobs), the menu journey,
    real keyboard events and simulated Xbox and DualShock 4 pads (disconnect, reconnect, remapping), 12 complete
    matches, the review scripts and signature footage; frame-time captures at 1080p and the native resolution;
  - a simulated jump-in-only player against every CPU level.
- **Carried over from `060a75f`** (that code has not changed): the 58-minute soak and the 385 clean starts across
  every display mode, monitor standby, focus loss and audio output changes.
- **Verified by the creator** on `060a75f`: the PS4 controller and audio through the TV.
- **Played by the creator** on `4cee9c1` (2026-11-07): everything in this round; problems remain, not yet itemized.
- **Not verified:** hardware other than the test machine (Validation lists it).
