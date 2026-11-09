# Status and handoff

Updated 2026-11-09 (combat, animation and character pass, the creator's fighting-game control layout, then Ashka Rook
refined to her new character sheet: candidate `2c993b0` built and checked by the implementer; ready for independent
review and the creator's playtest; nothing merged).

## Where things stand

- **This round's work** was made on branch `dev/combat-pass-1108` from the PR #1 head `ea3ddc6` and, at the creator's
  request on 2026-11-09, added to PR #1 (`release/first-slice`, a fast-forward). It answers the creator's 2026-11-08
  requests (crouching, Wren's takedown, Ashka's clinch trip, throws that work inside combos without grappling, higher
  and more useful jumps, uppercuts, an audit of every animation and move relationship, Wren's feet and materials,
  Ashka's overhaul, and the controls for all of it), the 2026-11-09 fighting-game control layout and Ashka's
  refinement to her character sheet of 2026-11-09.
- **Candidate:** `EbonyHearts-Slice-2c993b0.tar.gz` (Shipping, Linux), built from commit `2c993b0`; SHA-256
  `2510f9573253a7a1367f1fdc612fce46c2fd72a8d699e849b5dfc546b7e47a4c`. It is `32831cc` (the combat pass `5d5c316`, which
  you played on 2026-11-09, plus the new default controls) with Ashka refined. Local review build in the delivery
  workspace's `release/` folder; not published.
- **Pull request #1** (`release/first-slice` → `main`) now carries this work. Its 2026-11-08 technical audit
  ([Review](Review.md), previous round, section 6) applies to its earlier head `ea3ddc6`, not to this work. Nothing
  has been merged, tagged or released; merging needs the creator's explicit OK.
- **Results:** [Validation](Validation.md), "Current candidate". **What to check and where:** [Review](Review.md).

## What changed in this round

1. **Crouching.** Hold down (S, Down arrow, D-pad down). Jabs and other highs pass over you; lows must be blocked
   crouching (down + Block). Each fighter has a low kick (down + Light).
2. **Uppercuts.** Down + Heavy: Wren's Rising Uppercut, Ashka's Rising Elbow. They knock jumpers out of the air and
   launch a standing opponent into a knockdown. Blocked, they leave you wide open.
3. **Throws without grappling.** One throw each, on its own button (U / Numpad 4 / M on the keyboards, left trigger
   on a pad): Wren's double-leg takedown and Ashka's Muay Thai clinch trip. A plain throw can be escaped by pressing
   Throw in time. Light, (Light,) Throw while the lights hit throws straight out of the combo, and that one cannot be
   escaped. No holds, ground control or button mashing.
4. **Jumps.** Higher and further (115 cm arc, 150 cm forward), a little quicker. Coming down a jump attack must be
   blocked standing; crouching does not stop it. A deep jump-in leads into your string, low or uppercut. Jumping in
   over and over does not loop.
5. **Characters.** Wren's ankle wraps are now layered wraps with open heels and toes; her top and shorts have clean
   seams and edges, and the fabric no longer shows a diamond pattern. Ashka: see item 9 (the tailored coat of the
   2026-11-08 pass is gone with the new sheet).
6. **Animation.** New crouch, low, uppercut, launch, takedown and clinch-trip motion; every clip in the game measured
   and listed with what uses it ([AnimationAudit](AnimationAudit.md)); every move-to-move transition tabulated
   ([MoveMatrix](MoveMatrix.md)).
7. **Controls, Lesson and CPU.** Crouch and Throw are in Controls (remappable). The Lesson has 14 steps covering all
   of it. The CPU crouch-blocks lows, throws, uppercuts jump-ins and escapes throws on reaction.
8. **The usual fighting-game layout (2026-11-09, your choice).** Up jumps and down crouches; no button jumps. On a
   controller: Square / X Light, Triangle / Y Heavy, Cross / A Special, Circle / B Dodge, R2 / RT Block (hold),
   L1 / LB Throw; R1 / RB and L2 / LT are free. On the keyboards only W and the Up arrow jump now. Saved controls move
   to the new layout where they were still on the old defaults (your own changes stay); the game says so once, on the
   title screen, and saves the result.
9. **Ashka Rook to her character sheet of 2026-11-09.** Her usual clothes: a white long-sleeved shirt, black tie,
   black pants and brown loafers, no coat. Long crimson hair in a loose ponytail, bangs just past the brows and two
   longer side bangs; crimson eyes; a calm smile. The chest tattoo is gone (not in the new sheet). Her kit gains the
   sheet's front kick (away + Light, a quick snap kick that cancels into a special on hit) and spinning elbow (away +
   Heavy, at head height; Light, Light into it on hit is a combo). Nothing was removed. The select screen calls her
   style "Muay Thai · Lamplighter Flame". Story details from the sheet are kept in a private canon file in the
   workspace (`notes/canon/ashka-rook.md`), as you chose; the repository carries her look, style, title and her
   friendship with Wren.

## How to test the candidate

```bash
sha256sum -c SHA256SUMS
```

```bash
tar -xzf EbonyHearts-Slice-2c993b0.tar.gz
```

```bash
EbonyHearts-Slice-2c993b0/EbonyHearts.sh
```

It starts in your saved display mode. Settings are in `~/.config/Epic/EbonyHearts/Saved/EbonyHearts/Settings.json`.

## Playtest checklist for the creator

1. **Lesson, start to finish.** Does each step say clearly what to do, and does the crouch, throw and uppercut
   teaching make sense?
2. **Crouch.** Hold down against the CPU's jab, then its low kick. Does crouching feel quick enough, and is it clear
   from the pose when you are low?
3. **Throws.** Walk up and throw; then Light, Light, Throw in a combo. Does Wren's takedown read as a real shot, and
   Ashka's clinch trip as a Thai clinch sweep? Does either feel too strong?
4. **Jumps and uppercuts.** Jump in on a crouching CPU, then let Hard jump at you and uppercut it. Do the higher jumps
   feel better? Is the uppercut's timing fair?
5. **Ashka and Wren up close.** Training, walk in close on both sides. Does Ashka match her sheet (shirt, tie,
   pants, loafers, loose ponytail, calm smile)? Do Wren's ankle wraps look right?
6. **Controller (new layout).** Cross is Special, L1 throws, R2 blocks, up jumps, down crouches. Does it feel like
   the fighting games you know? Is anything you reach for missing (R1 and L2 are free)?
7. **Ashka's new moves.** Away + Light (front kick) and away + Heavy (spinning elbow); Light, Light, away + Heavy and
   front kick into Special. Do they feel like her Muay Thai, and are the inputs comfortable? Holding away while you
   press Light no longer jabs for her.

## Implemented, tested, observed and not verified

- **Implemented and tested by automation on the candidate** (Validation, "Current candidate" and "Candidate
  `5d5c316`"): combat core (53 cases, 1361 checks); packaging tests; the packaged battery, 28 runs (smoke, controls
  including version 1-4 settings files migrating, menu journey, the full Lesson, real keyboard events, simulated Xbox
  and DualShock 4 pads on the new layout, the CPU match matrix, review scripts); a copy of your own saved settings
  migrating over two launches; frame-time captures at 1080p and at the monitor's native 3440 × 1440; for `5d5c316`,
  the same against the previous release; a 58-minute off-screen soak on both `5d5c316` and `2c993b0`.
- **Observed by the implementer** (screenshots and footage): every new move on both fighters, both throws, the new
  character art in the chapel and in neutral light, before and after; before/after recordings of the art and jump
  scripts against the previous release, with phone copies; Ashka's new look (29 render side-by-sides, an in-game
  before/after) and her new moves and combos in game, with phone copies.
- **Physical controller:** the creator played `5d5c316` (the earlier layout) with a Bluetooth DualShock 4 on
  2026-11-09 and reports "The controller works fine" (their observation in play; no per-button log). Two earlier
  attempts logged no press: the pad's battery ran out, then its Bluetooth link went silent. The new layout has not
  been played with a physical controller yet.
- **Not independently reviewed** and **not accepted by the creator** yet; the creator's playtest feedback is not in.
- **Not verified:** hardware other than the test machine. One of three native-resolution captures of `5d5c316`
  had a single 0.4 s burst of slow frames (worst 32.8 ms) whose cause was not found; it did not recur.
- **For you to know:** with the CPU playing both, Ashka beats Wren 60 of 96 times (63 before her new moves); at Hard
  against Hard 22 of 24. Balance between the fighters was not part of this work. The first match after installing or
  updating a build compiles shaders on first use (small hitches, none over 33 ms here).

---

## Previous round (2026-11-07 playtest; independent audit 2026-11-08)

### Where things stand

**TECHNICALLY READY FOR OWNER MERGE DECISION; NOT MERGED.** The creator played
candidate `060a75f` on the 4K TV with the PS4 controller on 2026-11-07 and asked for four things, then for Grab's buttons
to be repurposed. All of it is in the candidate below, and the objective checks in [Validation](Validation.md) pass on
it. The creator played this candidate on 2026-11-07 and reported that combat smoothness and jumping need refinement;
the character models are acceptable placeholders but need further work. The creator clarified on 2026-11-08 that these
are ongoing, nonblocking improvements and should not hold up the technical merge-readiness verdict. The independent
review and its repaired-package qualification are recorded in [Review](Review.md), section 6. Merging is not authorized.

- **Creator-played candidate:** `EbonyHearts-Slice-4cee9c1.tar.gz` (Shipping, Linux), built from commit `4cee9c1`;
  SHA-256 `c5ad9309292571b400aae0aa215d8f66f945e4af6ad576527f171458f924f591`.
- **Repaired review candidate:** `EbonyHearts-Slice-309c87c.tar.gz`, built from `309c87c`; SHA-256
  `ed7943fbe0ca854f7a6f17abf6cb8064835e1b8ba5a0f7d01447025352c97cd6`. Commits after `309c87c`
  change documentation only; this archive is local review evidence, not a published release.
- **Pull request #1** (`release/first-slice` → `main`) is open. Nothing has been merged, tagged or released.

### Verified by the creator (2026-11-07, candidate `060a75f`)

- **PS4 controller:** works smoothly in menus and in play.
- **Audio through the TV:** clean.
- Played on the 4K TV (75% render scale, matched to the TV's 59.94 Hz). The punches were judged good enough for now,
  and Wren's kicks and the rolls are kept as they were.

### Creator playtest of `4cee9c1` (2026-11-07)

- **Played:** everything in this round: the spinning elbow, the body roundhouse, the jump rules, grappling's removal
  and the repurposed buttons.
- **Result:** combat smoothness and jumping still need refinement. The character models are acceptable placeholders
  and need more work. These are ongoing, nonblocking improvements by the creator's 2026-11-08 clarification.
- **Decision:** technical review is ready for the creator's merge decision; merging is not authorized yet.

### What changed in this round

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

### How to test the candidate

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

### For the creator

1. **Decide whether to authorize merging PR #1.** Technical readiness does not itself authorize integration.
2. **Continue combat smoothness, jumping and model refinements** on your schedule; specific examples can guide later
   work without holding this PR's technical verdict open.
3. **Optional.** Filing the two upstream bug reports drafted during the start-up crash investigation (SDL, Epic) is
   your call; they are public actions.
4. **Optional display setting.** On the 165 Hz monitor, V-Sync paces the game at 60 Hz in every window mode, so
   motion lands unevenly. For smooth motion run the monitor at 59.97 Hz, or play on the TV (Validation, Known
   limitations).

### History

The slice was published as `release/first-slice` and opened as pull request #1 on 2026-11-03, at the creator's
request, and has been updated after each review round since. The creator played `pkg-60` on 2026-11-04/05 and the
start-up-crash candidate `060a75f` on 2026-11-07 (on the TV, with the PS4 controller); this candidate answers that
second playtest. The title card's origin and authorization were confirmed on 2026-11-03
([asset ledger](AssetLedger.md#creator-supplied)). One editor crash report was sent to Epic Games early in
development, before crash reporting was turned off; the packaged game has no crash reporter.

### Implemented, tested, observed and not verified

- **Tested by automation on the candidate** (details in Validation, "Current candidate"):
  - combat core (890 checks) and release-staging tests;
  - smoke, controls (including an older settings file moving Grab's buttons to their new jobs), the menu journey,
    real keyboard events and simulated Xbox and DualShock 4 pads (disconnect, reconnect, remapping), 12 complete
    matches, the review scripts and signature footage; frame-time captures at 1080p and the native resolution;
  - a simulated jump-in-only player against every CPU level.
- **Carried over from `060a75f`** (that code has not changed): the 58-minute soak and the 385 clean starts across
  every display mode, monitor standby, focus loss and audio output changes.
- **Verified by the creator** on `060a75f`: the PS4 controller and audio through the TV.
- **Played by the creator** on `4cee9c1` (2026-11-07): combat smoothness and jumping need refinement, and the
  character models remain placeholders.
- **Not verified:** hardware other than the test machine (Validation lists it).
