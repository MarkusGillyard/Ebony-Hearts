# Status and handoff

## Independent review update (2026-11-11)

At this review-head snapshot, PR #1 and stacked PR #2 remain open. The creator identified the first
issues from the November 9 playtest to address: transitions between animations look unrealistic, and the throws look
and feel broken. Other playtest concerns will be addressed gradually; this does not constitute acceptance of the
current package. The targeted throw transition, paired fall and victim elbow repairs have been imported and checked in
a fresh local Shipping package; creator judgment of the overall movement and throw feel remains untested. The owner has
authorized integration without another confirmation if all technical and review gates pass. The candidate handoff
below is the implementer's dated record; its older authorization and feedback status statements are superseded by this
update. The current findings and disposition belong in [Review](Review.md).

The longer-term exploration concept was named **Adventure Mode** on November 9 (formerly Proto Mode): exploration
in Destiny's Ark could transition into 2.5D combat, while Versus and Training remain separate. It is a direction for
future architecture, not an implemented mode in this slice. The original stylized dark-fantasy game targets mature
content and an ESRB M 17+ rating; no rating has been awarded.

Updated 2026-11-09 (combat, animation and character pass, the creator's fighting-game control layout, then Ashka Rook
refined to her new character sheet and to its version 2, then the blocking animations and Ashka's coat tails, now
simulated as cloth: candidate `84acb66` built and checked by the implementer; ready for independent review and the
creator's playtest; nothing merged).

## Where things stand

- **This round's work** was made on branch `dev/combat-pass-1108` from the PR #1 head `ea3ddc6` and, at the creator's
  request on 2026-11-09, added to PR #1 (`release/first-slice`, a fast-forward). It answers the creator's 2026-11-08
  requests (crouching, Wren's takedown, Ashka's clinch trip, throws that work inside combos without grappling, higher
  and more useful jumps, uppercuts, an audit of every animation and move relationship, Wren's feet and materials,
  Ashka's overhaul, and the controls for all of it), the 2026-11-09 fighting-game control layout and Ashka's
  refinement to her character sheet of 2026-11-09 and its version 2 (the same day), then the blocking-animation
  refinement you asked for the same day.
- **Candidate:** `EbonyHearts-Slice-84acb66.tar.gz` (Shipping, Linux), built from commit `84acb66`; SHA-256
  `0998f768cdb6697f961191f535bf916cba298fb612c5039121a35bf0b0de5207`. It is `32831cc` (the combat pass `5d5c316`, which
  you played on 2026-11-09, plus the new default controls) with Ashka refined to her sheet's version 2, the guard,
  block and crouch animations rebuilt, and Ashka's coat tails simulated as cloth over her legs. Local review build in the delivery
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
9. **Ashka Rook to her character sheet (version 2 of 2026-11-09).** A Gothic-Victorian ensemble: a jet-black frock
   coat (fitted waist, structured shoulders, high standing collar, split coattails just above the knee with a crimson
   lining, black-on-black floral embroidery, crimson piping, silver buttons, ice-white trim at the cuffs and collar,
   a small crimson gem brooch), an ice-white high-collared blouse with chest pleats and lace cuffs, a black brocade
   waistcoat with silver buttons and a chain, a crimson silk cravat with a dark-silver clasp, high-waisted black
   trousers with crimson side stitching and black ankle boots. Silky crimson hair with waves toward the ends in a
   loose ponytail tied with a small black ribbon, slightly parted bangs and two framing strands; a heart-shaped face,
   almond crimson eyes, fine brows, fuller lips and a gentle smile. When she uses a flame move, the fire lights the
   coat's lining. Where the sheet leaves a choice, the game shows the ribbon (not the clasp), both the chain and the
   brooch, and a vine-and-flower embroidery; you approved these choices and the lining's moderate glow on 2026-11-09. The chest tattoo stays gone, as
   do version 1's shirt, tie and loafers. Her kit gains the
   sheet's front kick (away + Light, a quick snap kick that cancels into a special on hit) and spinning elbow (away +
   Heavy, at head height; Light, Light into it on hit is a combo). Nothing was removed. The select screen calls her
   style "Muay Thai · Lamplighter Flame". Story details from the sheet are kept in a private canon file in the
   workspace (`notes/canon/ashka-rook.md`), as you chose; the repository carries her look, style, title and her
   friendship with Wren.
10. **Blocking animations (2026-11-09, your brief).** The contorted guards are gone. The cause was the poses
    themselves: the standing guard put the hands on top of the head with the elbows flared out, the crouching guards
    crossed the forearms above the head, and the blocked-hit reaction layered a captured recoil that could fling an arm
    behind the head. Now each fighter has one simple guard, kept in front of the face: Wren a compact MMA shell (gloves
    at the temples, elbows on the ribs), Ashka an upright Muay Thai high guard (gloves at the brow, elbows forward). A
    blocked hit pushes the guard back a little and it settles. Crouching keeps its depth (it matches what can be hit)
    with the hands in front of the face, lower when not blocking and up over the face when blocking. No combat rule,
    timing or hitbox changed. Ashka's coat now stays over her legs: at your go-ahead its tails became a simulated
    cloth (12 columns round the coat that keep their spacing, stay out of her legs, ride on a raised thigh and fall off
    the knee), so in the crouch and in kicks the thighs no longer show through it.

## How to test the candidate

```bash
sha256sum -c SHA256SUMS
```

```bash
tar -xzf EbonyHearts-Slice-c6c0de2.tar.gz
```

```bash
EbonyHearts-Slice-c6c0de2/EbonyHearts.sh
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
5. **Ashka and Wren up close.** Training, walk in close on both sides. Does Ashka match her sheet (frock coat and its
   tails, blouse, waistcoat, cravat, trousers, boots, the ribbon in her ponytail, her face)? Do the coattails move
   well when she kicks, and does the lining's glow during her flame moves read? Do Wren's ankle wraps look right?
6. **Controller (new layout).** Cross is Special, L1 throws, R2 blocks, up jumps, down crouches. Does it feel like
   the fighting games you know? Is anything you reach for missing (R1 and L2 are free)?
7. **Ashka's new moves.** Away + Light (front kick) and away + Heavy (spinning elbow); Light, Light, away + Heavy and
   front kick into Special. Do they feel like her Muay Thai, and are the inputs comfortable? Holding away while you
   press Light no longer jabs for her.
8. **Blocking.** Hold Block, crouch-block, let the CPU attack you, and block from both sides of the screen. Do both
   guards look like trained fighters defending (no twisted arms or shoulders)? Is blocking as quick to come up as
   before? Do the standing and crouching guards read clearly apart?

## Implemented, tested, observed and not verified

- **Implemented and tested by automation on the candidate** (Validation, "Current candidate" and "Candidate
  `5d5c316`"): combat core (53 cases, 1361 checks); packaging tests; the packaged battery, 28 runs (smoke, controls
  including version 1-4 settings files migrating, menu journey, the full Lesson, real keyboard events, simulated Xbox
  and DualShock 4 pads on the new layout, the CPU match matrix, review scripts); a copy of your own saved settings
  migrating over two launches; frame-time captures at 1080p and at the monitor's native 3440 × 1440; for `5d5c316`,
  the same against the previous release; an hour-long off-screen soak on `5d5c316`, `2c993b0` and `c6c0de2`.
- **Observed by the implementer** (screenshots and footage): every new move on both fighters, both throws, the new
  character art in the chapel and in neutral light, before and after; before/after recordings of the art and jump
  scripts against the previous release, with phone copies; Ashka's new look (29 three-way render comparisons, the
  2026-11-08 build, sheet version 1 and version 2; an in-game before/after) and her moves, combos and the flame lighting her
  coat in game, with phone copies.
- **Physical controller:** the creator played `5d5c316` (the earlier layout) with a Bluetooth DualShock 4 on
  2026-11-09 and reports "The controller works fine" (their observation in play; no per-button log). Two earlier
  attempts logged no press: the pad's battery ran out, then its Bluetooth link went silent. The new layout has not
  been played with a physical controller yet.
- **Not independently reviewed** and **not accepted by the creator** yet; the creator's playtest feedback is not in.
- **Not verified:** hardware other than the test machine. One of three native-resolution captures of `5d5c316`
  had a single 0.4 s burst of slow frames (worst 32.8 ms) whose cause was not found; it did not recur. Likewise one
  native-resolution capture of `c6c0de2` had a single 46.9 ms frame (a processor-side stall); run again, none. It is
  not the flame light: frame times across eight flame moves are the same with and without it, even with an empty
  shader cache; nothing in the logs or the resource sampler marks that second.
- **Ashka's coat and her legs:** in the crouch her rear thigh used to show through the coat (a dark area beside the
  side slit). `8c22521` fixed it in the crouching guard; since `84acb66` the tails are a simulated cloth and the open
  crouch's notch and the far side of a raised thigh are covered too, on both sides of the screen. Seen straight from
  the front (not a game camera angle) the front panel stands out stiffly from the raised thigh in the crouch. The
  coat swings more freely than before; say if it is too lively.
- **For you to know:** with the CPU playing both, Ashka beats Wren 60 of 96 times (63 before her new moves); at Hard
  against Hard 22 of 24. Balance between the fighters was not part of this work. The first match after installing or
  updating a build compiles shaders on first use (small hitches, none over 33 ms here).
- **Blocking (`0c8a9f5`):** checked in game with recordings and frame-by-frame stills, before and after, both
  fighters, both sides; not yet seen by you or played with a controller. Ashka's new outfit costs
  about 0.3-0.9 ms of GPU time a frame (the coat is a fifth material; she has 66 150 triangles, 47 926 before); the
  game still holds 60 fps with room to spare on this machine.

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
