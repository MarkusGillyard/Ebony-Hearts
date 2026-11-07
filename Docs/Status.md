# Status and handoff

Updated 2026-11-07 (evening).

## Where things stand

**READY FOR THE CREATOR'S NEXT PLAYTEST — NOT APPROVED, NOT MERGED.** The creator played candidate `060a75f` on the
4K TV with the PS4 controller on 2026-11-07 and asked for four things, then for Grab's buttons to be repurposed. All of
it is in the candidate below, and the objective checks in [Validation](Validation.md) pass on it. What remains needs a
person: the creator's play of the changes (below), then a new independent review of the exact pull-request head.

- **Candidate:** `EbonyHearts-Slice-d2f7cb7.tar.gz` (Shipping, Linux), built from commit `d2f7cb7`; SHA-256
  `34555785c4db7f27016350914b177d4178ccfccaab6d522d2a03283be2b06044`. Later commits change documentation and a review
  script only.
- **Pull request #1** (`release/first-slice` → `main`) is open. Nothing has been merged, tagged or released.

## Verified by the creator (2026-11-07, candidate `060a75f`)

- **PS4 controller:** works smoothly in menus and in play.
- **Audio through the TV:** clean.
- Played on the 4K TV (75% render scale, matched to the TV's 59.94 Hz). The punches were judged good enough for now,
  and Wren's kicks and the rolls are kept as they were.

## What changed in this round

1. **Wren's spinning elbow** no longer contorts. At contact her right side is to the opponent and the elbow drives out
   at head height with the fist folded by her head. Before, the fist was behind her head and the arm wrapped round it.
   The left hand guards her face, the head turns ahead of the body, and the knees stay over the feet.
2. **Ashka's Heavy is a real body roundhouse** ("Body Roundhouse"). The hips turn over and the shin lands level at rib
   height. The old clip read as a straight front kick.
3. **Jumping has a job.** Holding Block does not stop a jump attack, so jumping in is how you open a guard. A jump-in
   that hits leaves you 12 frames ahead when you land, enough for your Light string, however high it connected. It
   loses to any strike (anti-air knocks the jumper down) and to a well-timed block (a deflect), which gives the
   defender the turn. One attack per jump. The CPU uses jump-ins against a held guard, and anti-airs by level.
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
tar -xzf EbonyHearts-Slice-d2f7cb7.tar.gz
```

```bash
EbonyHearts-Slice-d2f7cb7/EbonyHearts.sh
```

It starts in your saved display mode. Settings are in `~/.config/Epic/EbonyHearts/Saved/EbonyHearts/Settings.json`.

## For the creator

1. **The two animations at game speed.** Wren: Light three times (the third is the spinning elbow). Ashka: Heavy.
2. **Jumping.** In Training, Pause > Dummy > Block all, then jump toward the partner, press Heavy on the way down and
   Light as you land. Try the Lesson's steps 6 and 7, and Versus CPU on Hard (it anti-airs often). Judge whether
   jumping now earns its place, and whether beating a held block is too strong or too weak.
3. **Grappling gone.** Play a few matches. Nothing should feel missing or broken, and holding Block should no longer
   be safe against everything.
4. **The repurposed buttons.** Cross now jumps (with the stick's direction, like up) and L1 blocks (like R2). Your saved
   controls move over by themselves the first time this build starts, with a notice.
5. **Decide.** Accept the changes or ask for more; then authorize a new independent review of the pull-request head,
   and later any merge.
6. **Optional.** Filing the two upstream bug reports drafted during the start-up crash investigation (SDL, Epic) is
   your call; they are public actions.
7. **Optional display setting.** On the 165 Hz monitor, V-Sync paces the game at 60 Hz in every window mode, so
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
  - combat core (889 checks) and release-staging tests;
  - smoke, controls (including an older settings file moving Grab's buttons to their new jobs), the menu journey,
    real keyboard events and simulated Xbox and DualShock 4 pads (disconnect, reconnect, remapping), 12 complete
    matches, the review scripts and signature footage; frame-time captures at 1080p and the native resolution;
  - a simulated jump-in-only player against every CPU level.
- **Carried over from `060a75f`** (that code has not changed): the 58-minute soak and the 385 clean starts across
  every display mode, monitor standby, focus loss and audio output changes.
- **Verified by the creator** on `060a75f`: the PS4 controller and audio through the TV.
- **Not verified:** a person's play of this candidate (the jump rule, the two animations, the repurposed buttons), and
  hardware other than the test machine (Validation lists it).
