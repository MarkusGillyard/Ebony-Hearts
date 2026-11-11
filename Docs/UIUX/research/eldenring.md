# Elden Ring UI/UX research (Ebony Hearts reference)

Scope: Elden Ring base game, 2022. Post-launch patch items are labelled. All sources accessed 2026-11-09.
Footage method: I read YouTube storyboard thumbnails (160×90 or 320×180). Timecodes are only as precise as each video's thumbnail interval, noted per row. I checked one frame at full resolution (row 1).

## Observations

| # | Topic | Observation (specific) | Evidence | Accessed | Game version | Conf. | Transferable? |
|---|---|---|---|---|---|---|---|
| 1 | Title journey | The title screen is a still logo on black with a small "PRESS ANY BUTTON" line and a copyright line beneath. No visible change in thumbnails sampled every 5 s. | [V1] 1:00 (full-res frame); thumbnails 0:05–2:00 | 2026-11-09 | Base, uploaded Jul 2022 | High | **Adapt**: a quiet, dark title holds mood. Make the prompt larger. |
| 2 | Main menu | The title menu is a centred vertical text list: CONTINUE, LOAD GAME, NEW GAME, then a faded item and a down-chevron for more. The selection is a soft horizontal light band, not a box. | [V2] 0:00–0:40 (10-s thumbnails). The official Nightreign manual [S12] lists CONTINUE/LOAD GAME/NEW GAME/SYSTEM and greys out Continue/Load on first play. That is a different game, cited only as an analogue. | 2026-11-09 | Base ≤1.02.x (uploaded 2 Mar 2022) | Medium | **Adapt**: Continue first, highlight band. |
| 3 | Confirm/cancel | Each menu has a bottom legend that names its actions (class select: OK / Back / Show status / Help). Patch 1.12 slowed input in some menus (e.g. conversations) to stop accidental skips. | [V2] 0:50–1:20; [V3] ~4:50, ~19:20, ~21:20; [S5] | 2026-11-09 | Base launch; **1.12 (Jun 2024)** for the input fix | Medium (legend text is low-res) | **Adapt**: label every verb and guard results screens against button-mashing. |
| 4 | Navigation back/out | Quitting goes System → Quit Game → confirm → title → "press any button" → scroll to quit (PC). Players complained about this. | [S9] Steam thread 28 Apr 2022; [S10] menu path | 2026-11-09 | Base 2022 | Medium (community) | **Reject**: a fighting game needs rematch or quit in one step. |
| 5 | Contextual HUD | HUD setting is Auto/On/Off (System → Display and Sound → HUD). Official guide: on Auto "the HUD will automatically be hidden, except for the compass"; △/Y shows it temporarily. Footage shows bars and slots absent while exploring, while equipment slots and the boss bar appear once a fight starts. | [S1] "Game Interface"; [S7]; [S8]; [V3] ~9:00–10:00; [V4] 0:00–0:10 vs 0:11+ (1-s thumbnails). Uncertain whether the [V4] player used Auto. | 2026-11-09 | Base (guide dated 10/11/2021) | High (setting), Medium (footage) | **Adapt** for menus, intros and idle. **Reject** for anything shown during a round. |
| 6 | Area/discovery reveals | Area names appear in large serif, centred over live play, for about 3 s with the HUD minimal ("Limgrave", "Roundtable Hold"). "LOST GRACE DISCOVERED" is gold capitals on a horizontal band with a particle glow. | [V3] ~8:50, ~8:10, ~14:20; [V5] 0:02–0:04 (1-s) | 2026-11-09 | Base ≤1.02.x | High (exists), Medium (timing) | **Adapt**: stage-name reveal before round 1. |
| 7 | Death/victory moments | "YOU DIED" is red serif text centred on a dark band, with the HUD still visible. In one frame the band shows without text, which suggests they fade separately (uncertain). "GREAT ENEMY FELLED" is gold capitals on a lower-centre band for about 3 s, then a fade to black at about 4 s and a loading screen. | [V6] ~0:30, ~0:45 (5-s); [V5] 0:42–0:44, 0:48, 0:49 (1-s); [S11] names the Enemy/Great Enemy Felled tiers | 2026-11-09 | Base ≤1.04.x | Medium | **Adapt**: one line, held still for 2–3 s. **Reject**: the wording and graphic. |
| 8 | Status hierarchy | HP, FP and stamina bars sit at top-left. Weapon, spell and item slots sit bottom-left. The boss name and a long thin red bar sit bottom-centre and appear only when engaged. Runes are shown bottom-right (low-res). | [S1] element list; [V3] ~5:10–5:20; [V4] 0:11–0:24 | 2026-11-09 | Base | High | **Adapt**: separate player and opponent zones by position. **Reject**: the asymmetric layout. |
| 9 | Menu atmosphere/density | Equipment and inventory menus are full-screen dark translucent panels over a fogged world: a slot grid, item detail and a stats column, all in small text. The rest-point menu is a plain text list at top-left over the darkened live scene. | [V3] ~4:50, ~11:10, ~18:10, ~19:20, ~21:40; [S3] reports criticism that icon meanings are unclear; [S6] notes many menus to get lost in | 2026-11-09 | Base launch; **1.12** added "!" new-item marks, a "Recent Items" tab and FP cost display [S5] | High | **Adapt**: dark scrim over the live stage. **Reject**: the density for anything fight-critical. |
| 10 | Text/accessibility | At launch there was no text-size or HUD-size option. Cutscene subtitles had no background and could not be enlarged; in-game subtitles had a darker backing. There was no accessibility tab and no colour-blind modes. | [S6] (PS5, 27 Feb 2022); [S7] (2 Mar 2022); [S13] Eurogamer (25 Apr 2023) names Elden Ring as an example of too-small text | 2026-11-09 | Launch. Patches 1.03/1.12 notes: no such option added. Later versions: **not verified** | High (launch) | **Reject**: ship text scaling and subtitle backgrounds. |
| 11 | Pause/combat lockouts | The game cannot be paused, and menus leave the world running. The official guide says the map cannot be opened during battle. | [S6]; [S1] "Map" | 2026-11-09 | Base | High | **Reject** no-pause for offline play. **Adapt** the battle lock as "no menus mid-round online". |
| 12 | Design intent | Producer Kitao reportedly said network-test feedback showed the HUD and gauges were too simple and basic, so they were redesigned to suit the world. A Ubisoft UX director called it bad UX; Kotaku argued the sparse HUD trusts players to find their way. | [S4] (secondary, citing a GamerBraves interview; the primary page is blocked: **not verified** directly); [S2]; [S3] | 2026-11-09 | Pre-launch to 2022 | Medium | **Adapt**: themed frames, but test readability with players. |

## Design principles for a dark-fantasy fighting game

1. **Hide the frame, never the fight.** Decorative elements can fade in menus, intros and idle. HP, timer, round markers and meters stay fixed and fully opaque for the whole round.
2. **Stillness as punctuation.** Round call, KO and result each get one centred line over a dark band. Everything else holds still for 2–3 s and a sound sting carries the moment. Allow a skip after about 1 s, and never stack banners.
3. **Darken, don't box.** Put translucent dark scrims and soft highlight bands over the live chapel stage. Get text contrast from the scrim, never from whatever happens to be behind it.
4. **Two type roles, one size floor.** Use a display serif only for names and banners, and a sturdy body face for all functional text. Set a minimum size at 1080p and ship text scaling and subtitle backgrounds from day one.
5. **Label every verb on both devices.** Show a persistent legend (Confirm/Back/etc.) with keyboard and controller glyphs. Keep cancel consistent everywhere and guard against button-mashing through results and dialogue.
6. **Shallow paths back to play.** Title to fight in three confirms or fewer. Results screen gives Rematch, Character Select and Menu in one step. Quit to desktop directly. Settings reachable from title and pause, and in offline play pause actually pauses.
7. **Hierarchy by position, size and redundancy.** The largest critical bars sit symmetrically at the top, with secondary gauges smaller and lower. Signal states with shape or icon as well as colour.

## Do not copy

- The ELDEN RING logotype and ring sigil, and the gold-on-black title composition built around them.
- Banner wording and treatment: "YOU DIED", "ENEMY FELLED", "GREAT ENEMY FELLED", "LOST GRACE DISCOVERED" (other tier strings: not verified), and their red or gold serif-on-band styling.
- Terminology: Tarnished, Site of Grace, Runes, Flasks, Ashes of War, Great Runes.
- HUD composition: three stacked bars top-left, cross-shaped slots bottom-left, boss bar bottom-centre, compass top-centre. Also the icon art.
- Fonts: the UI typeface is not officially documented. Fan claims name Agmena or a modified Mantinia, both commercial faces (**not verified**). Neither should be used to evoke the game.
- Audio: death and felled stings, the grace-discovery cue, menu sounds and title music.
- The loading-screen format (item render plus lore text) and the menu iconography.

## Sources

- [S1] https://en.bandainamcoent.eu/elden-ring/news/elden-ring-starter-guide-tips-know-playing-the-game (verified; dated 10/11/2021)
- [S2] https://www.denofgeek.com/games/elden-ring-criticized-game-developers-tweets-controversy
- [S3] https://kotaku.com/elden-ring-ui-ux-user-experience-interface-fromsoftware-1848637410
- [S4] https://www.epicdope.com/elden-ring-hud-changing-due-to-feedback-from-fans (primary: https://www.gamerbraves.com/elden-ring-s-yasuhiro-kitao-says-margit-was-overtuned-for-beta-and-more-in-new-interview/ — blocked, not verified)
- [S5] https://www.bandainamcoent.com/news/elden-ring-patch-notes-version-1-12
- [S6] https://caniplaythat.com/2022/02/27/elden-ring-lacking-accessibility-unintentional-barriers-and-land-jellyfish/ and https://caniplaythat.com/2022/02/28/elden-ring-accessibility-menu-deep-dive/
- [S7] https://www.gamegrin.com/articles/how-accessible-is-elden-ring/
- [S8] https://samurai-gamers.com/elden-ring/recommended-game-settings
- [S9] https://steamcommunity.com/app/1245620/discussions/0/3279193518777533976
- [S10] https://segmentnext.com/elden-ring/save-and-quit
- [S11] https://eldenring.wiki.fextralife.com/Bosses
- [S12] https://en.bandainamcoent.eu/elden-ring/news/elden-ring-nightreign-starter-manual-ps5 (Nightreign, 2025; analogue only)
- [S13] https://www.eurogamer.net/why-do-so-many-modern-games-have-tiny-text
- Context: https://www.theringer.com/2022/4/5/23010795/elden-ring-vs-horizon-forbidden-west-open-world-games ; https://eldenring.wiki.gg/wiki/HUD ; https://eldenring.wiki.gg/wiki/Map ; https://mp1st.com/news/elden-ring-update-1-03-patch-notes-new-features-added-more (1.03 NPC map icons, Mar 2022)
- Footage:
  - [V1] https://www.youtube.com/watch?v=2UKNcPxulJw (title screen, 5-s thumbnails)
  - [V2] https://www.youtube.com/watch?v=PN7YFKHOR9Y (FightinCowboy, 10-s thumbnails)
  - [V3] https://www.youtube.com/watch?v=xjBrZIELCA4 (IGN, 24 Feb 2022, 10-s thumbnails)
  - [V4] https://www.youtube.com/watch?v=dsC0meGu1Ow (1-s thumbnails)
  - [V5] https://www.youtube.com/watch?v=E3w8B1opUVE (1-s thumbnails)
  - [V6] https://www.youtube.com/watch?v=WmC6Xw8AuR0 (5-s thumbnails)
