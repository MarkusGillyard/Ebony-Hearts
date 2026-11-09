# UI/UX research synthesis

What Ebony Hearts takes from Elden Ring (2022) and Mortal Kombat X / XL (2015 / 2016), and what it leaves. The
evidence is in three workstreams, each with its sources, dates, versions and confidence:

- [research/eldenring.md](research/eldenring.md): 12 observations, ER-1 to ER-12.
- [research/mkx.md](research/mkx.md): 13 observations, MK-1 to MK-13. It covers only MKX and MKXL (no later MK games).
- [research/access_ue.md](research/access_ue.md): measurable accessibility targets (Xbox Accessibility Guidelines,
  WCAG 2.2, Game Accessibility Guidelines) and how to measure Slate cost in Unreal.

**Method.** The work used official guides, patch notes, a former NetherRealm UX designer's case study, reviews, and
gameplay footage checked frame by frame at the cited timecodes, all accessed on 2026-11-09. Observations that rest on
low-resolution footage, community posts or blocked primary pages are marked medium or low confidence, or "not
verified". Quotes are kept to a minimum and paraphrased. Nothing from either game is shipped: no screenshots, art,
fonts, sounds or wording.

**How to read the two references.** Elden Ring is the reference for quiet, world-first atmosphere and restraint.
MKX/XL is the reference for fast fighting-game comprehension, fighter presentation and mode flow. Neither outranks
the game's own design. Where they disagree, the fight wins: Elden Ring's habit of hiding information is fine on a
title screen and wrong during a round.

## Side-by-side

| Topic | Elden Ring (evidence) | MKX / XL (evidence) | Ebony Hearts requirement | Adapt / reject | Why | Risk |
|---|---|---|---|---|---|---|
| First launch | A still logo on black, a small "press any button" line, a copyright line; nothing moves for minutes (ER-1) | Goes straight to a busy root with promotion tiles and an account login (MK-1) | A quiet title on the supplied key art or logo, a large prompt, the creator and publisher credit; any button continues | **Adapt** ER's stillness and prompt; **reject** MK's promotions | Sets the tone at no cost and adds no steps | Too small a prompt (ER's is small) |
| Mode selection | A short centred text list, highlighted by a light band, not a box (ER-2) | A short vertical list with a one-line description of the highlighted item (MK-1); 92 menu items against 51 for a rival, with an average of 42 noted (MK-6) | Fight modes first (Versus CPU, Local Versus, Training, Lesson), then Move List, Settings, Credits, Quit; a description line; well under 20 items in total | **Adapt** the band and description; **reject** commerce, live-service items and locks (MK-2, MK-12) | Item count is the measure of friction (MK-6) | Over-grouping hides modes behind submenus |
| Fighter select | Not applicable | Large renders, colour-coded cursors, then style and stage on the **same** screen; hover is a live preview and a separate press locks (MK-4, MK-5) | Two large fighter presentations that do not cover the fighters; clear hovered / chosen / locked / P1 / P2 / CPU / partner states with text labels, not colour alone; CPU level and side on the same screen | **Adapt** one screen, preview on hover, explicit lock; **reject** the bottom portrait strip and random tile (built for big rosters) and any variation or stage systems | Two fighters do not need a grid; one screen avoids loads and lost context | Showing locked or unknown fighters would promise a roster: not allowed |
| Match start | Area name in large serif, held about 3 s while play is live (ER-6) | Round-start call appears only before the player has control (MK-9) | A stage-name reveal before round 1 (The Drowned Chapel) and one round banner, both shown while no input matters, at a fixed size | **Adapt** both | Big text costs nothing when no decision is pending | Banners must not delay control (they are cosmetic) |
| HUD | Bars top-left, slots bottom-left, boss bar bottom-centre; on Auto the HUD hides when not needed (ER-5, ER-8) | Health bars meet at a central timer; damage leaves a lagging segment; meter in the bottom corners; the centre stays clear (MK-7, MK-8) | Symmetric top band: health with a lag segment, names, timer, rounds; fighter gauges near their health bar; nothing in the centre; always visible and opaque during a round | **Adapt** MK's edge-only layout and lag segment; **reject** ER's auto-hide for anything in a round | Fighting needs constant state at a glance; the centre belongs to the fighters | Thin bars read badly at couch distance (MK-7) |
| Pause | Cannot pause; menus leave the world running (ER-11) | Pause offers restart and exit to select (MK-3) | Pause is immediate in offline play; Resume, Restart, Move List, Settings, Change Fighters, Main Menu; the pausing device owns the menu | **Adapt** MK; **reject** ER | Offline play must pause | None (already the game's behaviour) |
| Training / move list | Not applicable | A pause cheat-sheet of both fighters, pinned moves, an input-history column, frame data in the move list, dummy options with dim-not-hide rows and one-button defaults (MK-10); frame data needed six rounds of fixes (MK-11) | Input history, frame data and hitboxes on demand; dummy options grouped; move list with the viewer's own buttons; all numbers generated from the combat data | **Adapt**; frame data **only** from runtime data (already true here) | Teach where the player already is | Density can hide the fight |
| Settings | Settings sit behind system menus; no text-size option at launch (ER-9, ER-10) | Options as plain lists (MK-1, MK-2) | Controls, Video (with confirm-or-revert), Audio, Accessibility; selected, pending and saved values look different | **Adapt** plain lists; **reject** ER's missing text options | The game already has the settings; the gap is how they read | Breaking saved settings: migrate, never reset |
| Navigation speed | Quitting takes several steps through the title (ER-4) | Root to fight in about 3 / 4 / 7 presses; rematch about 8 s from the win card to the next round (MK-2, MK-3) | Root to fight in ≤ 4 presses for every mode; rematch is the default and takes one press; quit in two | **Adapt** MK's targets; **reject** ER's quit path | Fighting games are replayed in short loops | Removing confirmation where it guards a real loss |
| Typography | A display serif for names and reveals; small functional text (ER-6, ER-10) | Condensed sans for numbers and lists (MK-7, uncertain face) | A display face only for titles, names and banners; a readable body face for everything functional; essential text ≥ 26 px at 1080p, nothing below 18 px | **Adapt** the two roles; **reject** small text | Measured floor from XAG 101 (access_ue.md) | Ornate faces at small sizes |
| Motion / sound | Moments of stillness carry big events; banners fade in and out separately (ER-7) | State changes as information events with sound (MK-8, MK-9) | Instant focus feedback, short open/close, cinematic only for title and round start; one sound per action; nothing delays input | **Adapt** both | Responsiveness first, mood second | Animated menus feel slow if they block input |
| Controller UX | A legend names each menu's buttons (ER-3); patch 1.12 slowed input in some menus so dialogue isn't skipped by accident (ER-3) | Menus prototyped and tested on a real controller (MK-5) | Confirm and Back are the same everywhere; prompts show the current device's own buttons; both players' devices are owned and labelled; guard results screens against mashing | **Adapt** both | Already the game's architecture (`EHInputRouter`); keep it | Two-player ownership on shared screens |
| Accessibility | No text scaling, no colour-blind options, cutscene subtitles without a backing at launch (ER-10) | A lowered-health-bar (safe-area) option (MK-7) | Text ≥ 26 px; contrast ≥ 4.5:1 text, 3:1 bars and focus; colour plus a second cue; ≤ 3 flashes/s; keep interface scale, reduce shake, reduce flashes; add reduced motion | **Reject** ER's gaps; **adapt** MK's option | Measured targets in access_ue.md | Violet on black fails contrast unless checked |
| Performance | Not measured here | PC drops cinematics to 30 fps (MK-12) | No sustained frame-time regression; UI draw ≤ 1.0 ms mean, ≤ 2.0 ms p99 at 60 fps; no new hitches | **Reject** frame-rate drops | 60 fps at 1080p is the target | Large textures and per-frame text shaping |

## Patterns that must not be copied

From both games, nothing that identifies them:

- **Elden Ring:**
  - its logotype and ring sigil;
  - the "YOU DIED" / "ENEMY FELLED" style banners and their wording;
  - its terminology (Tarnished, Site of Grace, Runes and the rest);
  - its HUD composition and icons;
  - its fonts, stings and loading-screen format.
- **MKX / XL:**
  - the K-for-C spellings and the names of its systems (X-Ray, Fatality and the rest);
  - the announcer's wording and voice;
  - the dragon emblem and medallion round markers;
  - the bar-meets-timer silhouette with its ornaments;
  - the select-screen composition (renders over a portrait strip with a central random tile);
  - the Krypt, Factions and towers;
  - its fonts and sounds.

Ebony Hearts keeps its own words. The round banners are already its own, and the finisher term **HEARTED** is
reserved for a finisher if one is ever built; none is part of this work.
