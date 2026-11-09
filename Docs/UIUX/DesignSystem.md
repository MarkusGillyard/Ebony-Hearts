# Design system

The rules every screen follows. The tokens live in `Source/EbonyHearts/Game/EHUIStyle.h`; change the look there,
not in the painters.

**Status (2026-11-09).** Direction A, Still Water, chosen by the creator, is applied to every screen: the tokens and
type, the shared layouts, and the ornament, motion and sound below.

## Colour roles

Authored in sRGB and converted to Slate's linear colour. Contrast is given twice: against the menu panel as it
composites over the dark stage (`#171220`), and in brackets against `#282036`, the lightest surface the interface sits
on (a conservative check for translucent panels over brighter parts of the stage).

| Token | Value | Use | Contrast |
|---|---|---|---|
| `Abyss` | `#0B0913` | Deepest background, chip text on filled chips | — |
| `Panel` | `#181322` at 90% | Menus and plates over the stage | — |
| `Plate` | `#120E1A` at 94% | Behind numbers that must never vary: the timer, round markers | — |
| `Track` | `#16121E` at 96% | Empty part of a bar | — |
| `TextPrimary` | `#F3EFF9` | Everything a player reads first | 16.2:1 (13.7) |
| `TextSecondary` | `#9A94AE` | Descriptions, unselected rows and values | 6.3:1 (5.4) |
| `FocusText` | `#C2A2F2` | Violet text (capture prompts, the FIGHT banner, ESCAPE) | 8.5:1 (7.2) |
| `Silver` | `#D6D4E2` | Hairlines, frames, emblem, player 2 | 12.6:1 (10.7) |
| `Focus` | `#A15CE8` | The focus band and marker: **shapes only** | 4.6:1 (3.9); not relied on as text |
| `P1` | `#E3A93C` | Player one's tags and cursor | 8.7:1 (7.4) |
| `P2` | `Silver` | Player two's tags and cursor | 12.6:1 (10.7) |
| `WrenAccent` | `#E3A93C` | Wren's golden Spirit: her gauge, nameplate bar, title | 8.7:1 (7.4) |
| `AshkaAccent` | `#D9343B` | Ashka's crimson Flame: fills and lines only | 3.9:1 (3.3), shapes only |
| `AshkaText` | `#F05A5F` | Ashka's crimson as text (her title) | 5.5:1 (4.7) |
| `Health` / `HealthLow` / `HealthLag` | `#E6E2EC` / `#F0B84E` / `#BE3A4C` | Health, health under 30% (amber plus the bar's length), damage just taken | Against `Track`: 14.4, 10.2, 3.4:1. The lag segment is also 4.2:1 against health and 3.0:1 against amber |
| `Warning` / `Success` | `#F05A5F` / `#7ED6A0` | Errors, the last ten seconds, K.O., PUNISH / a lesson step done | 5.5:1 / 10.5:1 |

**No meaning by colour alone.** Players are named (P1, P2, CPU, PARTNER). Choices say CHOOSING or LOCKED IN, and
locked chips are filled. Won rounds are filled crescents, rounds still to win are outlines. Gauges say READY or
ACTIVE. Low health is amber and also shorter.

## Type

Two families, both under the SIL Open Font License: **Cinzel** for display (titles, names, banners, numbers in the
HUD) and **Alegreya Sans** for everything functional.

| Role | Size (Slate pt) | Notes |
|---|---|---|
| `Banner` | 104 | Round and K.O. banners; one fixed size, pre-rasterised on the title |
| `Title` | 44 | Screen titles, letter-spaced capitals |
| `Heading` | 32 | Panel headings, combo counts |
| `Name` | 30 | Fighter names in the HUD |
| `Menu` | 26 | Menu rows |
| `Body` | 22 | Descriptions, values, table rows |
| `Label` | 20 | **The floor**: tags, gauge labels, prompts, table notes, section headers |

1 pt is 4/3 px on the 1080p canvas. With these fonts, 20 pt is the smallest size whose body height (ascender to
descender) reaches 26 px, the floor for essential text at TV distance (XAG 101, `research/access_ue.md`). Button
glyphs are 40 px tall, so the letter inside is at the floor too. The interface-scale setting multiplies everything.

## Components and states

| Component | States and their cues |
|---|---|
| Menu row | **Normal:** secondary text. **Focused:** primary bold text on a violet band with a violet edge. Values are shown as `‹ value ›` when they can change |
| Menu section header | Small spaced capitals and a hairline. Never focused; navigation skips it |
| Player chip | `WHO · CHOOSING`: outlined in the player's colour. `WHO · LOCKED IN`: filled in the player's colour with dark text |
| Fighter nameplate | Name (display), title (in the fighter's accent), style (secondary), and a vertical accent bar that brightens under a cursor |
| Health bar | Track, then the lagging damage segment, then health. A 2 px silver frame. Drains toward the centre |
| Gauge | Under its owner's name, in the fighter's accent. The frame lights in the accent when READY or ACTIVE. Ashka's half-gauge cost has a tick |
| Round marker | Crescent on a plate beside the timer: filled when won, outline when not |
| Timer | Display numerals on a near-opaque plate with a silver frame; the warning colour in the last ten seconds |
| Prompt row | Device-correct glyph, then the action in primary text. Glyphs follow the owner's device and remapping |

## Layout

- **1920 × 1080 virtual canvas:** centred, scaled to the window, with interface scale on top. Wider screens extend the
  backgrounds, not the content.
- **HUD:** a top band from y = 30 to 172, with a dark gradient behind it to y = 230:
  - health, then name and tag, then gauge, on each side;
  - the timer and round markers in the middle;
  - nothing in the centre of the stage; callouts on the attacker's side at y = 270, the combo count at y = 330;
  - the Lesson panel starts at y = 204, below the HUD.
- **Fighter select:** title at the top; nameplates in the lower corners; CPU level and side in a small panel at the
  bottom centre; prompts on the bottom row. The fighters stay unobstructed between the bands.

## Performance

The interface's draw list costs 0.01–0.13 ms of CPU a frame on average, 0.3 ms at most at p99, before and after these
changes (the move list 0.22 ms since it wraps long notes each frame) (`Tests/Auto/perf_ui.txt`, `ui_paint_*`). The budget is 1.0 ms mean and 2.0 ms p99.

## Still Water: ornament, motion, sound

**Ornament.** Darkness as negative space, silver for structure, violet only for focus and rare moments, and the
logo's crescent as the one recurring emblem. The crescent never stands for lore.
- **Title:** the creator's key art fills the screen (cover; wider screens crop top and bottom), with its wordmark
  painted in. Only the prompt (letter-spaced display capitals) and the credit sit over it, on a dark gradient at the
  bottom.
- **Main menu:** a plain list over the live, darkened chapel:
  - the left of the screen darkens toward the list;
  - the small logo at the top left;
  - a hairline divides the fight modes from the rest;
  - a one-line description of the focused mode.
- **Other menus:** a square dark veil between two silver rules, with the crescent set into the top rule.
- **Focus:** a violet band fading to the right, and the crescent beside the focused row. It sits outside the veil;
  inside, next to the label, a small crescent reads like a tick.

**Motion.**
- Screens fade in over 0.15 s. This is visual only: input acts immediately, and a press during the fade is never
  lost.
- The title fades in over 1.2 s.
- The title prompt breathes for 4 s, then holds.
- Nothing moves during a round except what the fight itself does.

**Sound.** One sound per press, all at the same loudness (−1 dBTP peak, −20 LUFS momentary), synthesised in one soft
mallet style (`Tools/Audio/eh_audio/ui.py`).

| Sound | When |
|---|---|
| `UiMove` | Focus moves, a value changes |
| `UiConfirm` | A menu choice, joining Local Versus |
| `UiBack` | Back, unlocking |
| `UiOpen` / `UiClose` | Pause opens / closes |
| `UiLock` | Locking in a fighter or the match setup |
| `UiDenied` | Something that cannot be done (a third device trying to join a full Local Versus) |
| `UiApply` | Apply and Keep on the video settings |
| `UiWarn` | A controller is lost; the last three seconds before a display change reverts |
