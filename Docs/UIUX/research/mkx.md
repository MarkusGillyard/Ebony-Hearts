# Mortal Kombat X / XL: UI and UX research for Ebony Hearts

Scope: MKX (April 2015) and MKXL (March 2016) only. No MK11, MK1 or Mobile material. All sources accessed 2026-11-09. Footage timecodes were checked frame by frame. "Concept" means art that did not ship.

## Observations

| # | Topic | Observation | Evidence | Accessed | Version | Confidence | Lesson for the slice |
|---|---|---|---|---|---|---|---|
| 1 | Main menu | Short vertical list (One Player, Two Player, Online, Faction, Krypt, Options, Extras, plus Exit on PC). One-line description of the highlighted item at the bottom. Above it: three promo tiles on shoulder/face buttons and a publisher-account login. | [S1] header screenshot; [S4] Main Menu | 2026-11-09 | MKX PS4, about May 2015 (DLC tile still "coming soon"); [S4] is PC | High | **Adapt** the short list and description line. **Reject** promos and login on the root; they compete with "fight now". |
| 2 | Journey to a fight | **Local:** Two Player → PvP → fighters → variation → stage. **CPU:** One Player → Single Fight → fighters → separate difficulty prompt → stage. **Training:** One Player → Training → Practice → fighters → stage. Dummy settings are in pause. Menus open on their first item; cancel backs out. Story is locked until the tutorial is done. | [S4] One Player, Two Player | 2026-11-09 | PC | High (PC); console button labels uncertain | **Adapt:** MKX takes about 3 / 4 / 7 presses from root to select (local / CPU / training), inferred from menu order. Aim for ≤3 for all. Put difficulty on the select screen. **Reject** locking modes behind the lesson. |
| 3 | Rematch speed | Win card (3:40), then player cards, then a menu (3:43–3:44): rematch is default, with P1 and P2 tags lighting as each confirms; then new fighter; then quit. The next round-start call is at 3:48, about 8 s after the win card. Session W/L/streak under each name goes from 0/0/0 (0:30) to 1/0/1 (3:49). Pause offers restart and exit-to-select ([S3] May 2015). | [V1] 0:30, 3:40–3:49; [S3] | 2026-11-09 | XL/current build (uploaded 2026-05-25) | Medium-high (the video may be cut) | **Adapt** default-focus rematch, confirmation by both players and visible session W/L. Target ≤8 s. **Reject** currency counters on the results screen. |
| 4 | Character select | Two large renders on top, names under them, a two-row portrait strip below with a central random tile, and colour-coded P1/P2 cursors (0:03). After the lock, each side gets a three-icon variation picker with a one-line description (0:45). Stage select then replaces the strip on the same screen, with random, P1 cursor and an interaction toggle; the fighters stay visible (0:20). | [V2] 0:03, 0:20, 0:45 | 2026-11-09 | XL (uploaded 2016-03-17) | High | **Adapt:** fighter → style → stage on one screen, with no context loss and no loads. Two fighters only need two large cards, not a grid. |
| 5 | Select research | The final select was an Axure prototype with controller input, used in testing. The vertical-tile concept "did not test well for the feature set we had." In the prototype GIF, hover swaps the big render instantly. | [S1] captions "Character Select Prototype" / "(Vertical)" | 2026-11-09 | Prototype 2014–15, not shipped as-is | High | **Adapt:** hover is a live preview and a separate press locks. Prototype on a real pad before final art. |
| 6 | Menu breadth | A whiteboard photo counts 92 MKX menu items against 51 for a comparison title (looks like "SS4", probably Super Street Fighter IV), with an average of 42 noted. Branches: Single Player 17, Versus 4, Faction 6, Extras 13. | [S1] image "MKX Menu Exploration" | 2026-11-09 | Pre-release | Medium (handwriting) | **Adapt** item count as a metric; stay well under 42. |
| 7 | Combat HUD | **Top band:** health bars meet at a central countdown timer. Damage is cut from the outer end, with a red lag segment that lingers, then drains (1:00–1:14). A two-segment stamina bar sits under each health bar, and small round markers sit beside the timer. Name, variation and session W/L are in the outer corners. **Bottom corners:** three-stock meter with cost icons, labelled X-ray when full (1:13). The centre stays clear. There is a lowered-health-bar option. | [V1] 0:30, 1:00–1:14, 2:30; [S4] Options | 2026-11-09 | XL/current; the timer became real-time seconds in XL 3/1/2016 [S3] | High (bars, timer, meter); medium (round markers); reason for the lowered option not verified | **Adapt** an edge-only HUD, the lag segment, labelled meter costs and a safe-area option. **Reject** hairline bars, which are hard to read at couch distance. |
| 8 | Callouts | A small "first hit, meter awarded" notice appears under the attacker's name, away from the fighters. XL 10/4/2016 added a counter/punish notice. XL 3/1/2016 made some hit sparks red on hits during the opponent's recovery. A hit counter with damage % was **not verified** in the sampled footage. | [V1] 0:30, 3:50; [S3] | 2026-11-09 | XL patches 2016 | High | **Adapt:** explain rewards in the attacker's corner and signal punishes in-world (spark colour). |
| 9 | Announcements | Big text appears only at state changes: the round-start call (3:48) before control, the finisher prompt (3:24) while the loser is dazed, and the win card on its own screen (3:40). | [V1] 3:24, 3:40, 3:48 | 2026-11-09 | XL/current | Medium-high | **Adapt:** full-size text only when no neutral decision is pending, with our own words and voice. |
| 10 | Training | **Pause:** a cheat-sheet of both fighters' key moves side by side (5:00). Menu: move list, AI options, practice options, record/playback, controller preset, player select, main menu. **Move list:** per variation, with type, damage %, block damage, startup/active/recovery and advantage. Tagged moves stay pinned on screen during play (0:26, 1:40), and an input-history column runs down the left edge. **AI options:** enemy type (including recorded), block, movement, reversal, wakeup, roll, breaker, throw-break and get-up. Irrelevant rows are dimmed, and one button restores defaults (2:20). | [V3] 0:26, 1:40; [V4] 2:20, 5:00 | 2026-11-09 | MKX launch (uploaded 2015-04-17 and 04-20, PS4) | High | **Adapt** all of it: the cheat-sheet, pinned moves, input history and dim-not-hide options map directly onto our 14-step lesson. |
| 11 | Frame data | In the move list at launch; PC Gamer praised startup frames shown in menus. It was corrected in the April 2015 (frame 0 added), May and August 2015, and March and October 2016 patches. 3/29/2016 fixed the training "simulate online delay" option. | [S3]; [S6] | 2026-11-09 | Launch plus patches | High | **Adapt** only if generated from runtime data; hand-entered numbers needed at least 6 rounds of fixes. |
| 12 | Weak spots | The root carries commerce and live-service items. The Krypt is a first-person unlock store that gates fatalities ([S5]). Paid DLC appears on select ([S6]). PC drops cinematics and X-rays to 30 fps ([S6]). Factions, live towers and king-of-the-hill add online clutter. Results screens show currency. | [S1]; [S5]; [S6] | 2026-11-09 | MKX 2015 | High | **Reject** all of these. |
| 13 | UI concepts | Thirteen Factions UI concepts made freelance in 2013–14, which the artist calls a rough mood-setter. They show banner faction choice and tabbed pages paged with the shoulder buttons. | [S2] | 2026-11-09 | **Concept, not shipped** | High | **Adapt** shoulder-button tab paging only. |

## Controller flow and rematch targets
- **Root to select:** ≤3 presses for Local, CPU and Training. MKX takes about 3, 4 and 7.
- **Select:** fighter, then style, then stage, all on one screen. Cancel undoes exactly one lock, and hover previews instantly.
- **Post-match:** rematch has default focus, and each player's tag lights on confirm. Change fighter is one press, and main menu is last. Target ≤8 s from KO card to the next round (MKX: about 8 s).
- **Pause:** restart and exit-to-select in every fight mode; session W/L survives both.

## Distilled principles
1. **The centre belongs to the fighters.** The HUD lives in the edge bands, and big text appears only when no input matters.
2. **Show the change, not just the state.** Use lag segments, reward callouts and punish colour.
3. **Lock choices in sequence on one screen.** Previews are live, locks are explicit, and nothing loads in between.
4. **Make rematch the default.** One press per player, visible session stats, measured in seconds.
5. **Teach where the player already is.** The pause cheat-sheet, pinned moves, input history and move data are one press from the fight.
6. **Prototype on a controller, test with players, count the items.** 92 against 51 was the warning sign.
7. **Show options in context.** Dim irrelevant rows, restore defaults with one button, and offer a safe-area HUD.
8. **Keep the root free of commerce.** No store, login, timed events or currency on the path to a fight.

## Do not copy
- K-for-C spellings (Kombat, Kombo, Kontrols, Kounter, Krypt, Koins) and these names: X-Ray, Fatality, Brutality, Quitality, Faction Kill, Test Your Might/Luck, Living/Premier Towers, Kombat Kard.
- Announcer wording, voice and delivery.
- The dragon emblem, the medallion and round-marker shapes, the crenellated bar ornaments, the bar-meets-timer silhouette, fonts and colours.
- The exact composition of the select screen (two renders over a bottom strip with a central random tile, the three-circle variation picker).
- The Krypt, Factions and live-tower structures; sounds; the cinematic X-ray presentation.

## Sources (all accessed 2026-11-09)
- [S1] N. Varjavand, MKX UX case study: https://www.nathanvarjavand.com/mortal-kombat-x-1 (text, whiteboard image, select-prototype GIFs, header main-menu screenshot)
- [S2] Davison Carvalho (hellodave), MKX UI concepts (**concept art**): https://art.hellodave.co/proj/mkx
- [S3] WB Games patch notes. Direct fetch returned 403, so they were read through the site's public help-center API. Pages: May 2015 https://mortalkombatgamessupport.wbgames.com/hc/en-us/articles/39907263650835-Mortal-Kombat-X-Patch-Notes-May-2015 ; April 2015 (article 39907164357779); 8/31/2015 (39906966366355); XL 3/1/2016 (39906607853971); 3/29/2016 (39906444383251); XL 10/4/2016 (39906218320787)
- [S4] Accessible Gaming Wiki, "Mortal Kombat X: Menu Breakdown" (PC): https://accessiblegaming.wiki/MortalKombat/MKXMenuGuide
- [S5] D. Daavpuke, NoobFeed review, 10 May 2015: https://www.noobfeed.com/reviews/1138/mortal-kombat-x
- [S6] M. Elliott, PC Gamer review, 21 Apr 2015: https://www.pcgamer.com/mortal-kombat-x-review/
- [V1] YoVideogames, "Mortal Kombat X! Local VS! 2026 Part 1" (has a facecam overlay): https://www.youtube.com/watch?v=_y711Jpbu_I
- [V2] Alson Peng, "Mortal Kombat XL Character Select Screen w/Variations": https://www.youtube.com/watch?v=tG0lGvwOsdE
- [V3] JayTB123, "MKX Tutorial - Simple way to test hit and block advantage in training mode": https://www.youtube.com/watch?v=iHUw3anWoZc
- [V4] JayTB123, "MKX Tutorial - Testing setups using training mode": https://www.youtube.com/watch?v=6QtLl7LR43E
- **Not verified or not accessible:**
  - No official MKX manual was found.
  - SuperCombo wiki and the Test Your Might "MKX System Guide" are behind a bot check or CAPTCHA, so they were not read.
  - The Prima Games interview and the Giant Bomb blog returned 403.
  - A search snippet places Varjavand in the MKX Mobile credits on MobyGames; I did not check it. His console role is as he self-reports it.
