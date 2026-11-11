// Interface design tokens (UI/UX overhaul, 2026-11-09): semantic colours and the type scale every screen uses.
// Colours are authored in sRGB (as picked and contrast-checked, see Docs/UIUX/DesignSystem.md) and converted to the
// linear colours Slate draws with. Change the look here, not in the painters.
#pragma once

#include "CoreMinimal.h"

namespace EHStyle
{
inline FLinearColor SRGB(uint8 R, uint8 G, uint8 B, float Alpha = 1.0f)
{
	FLinearColor C(FColor(R, G, B, 255));
	C.A = Alpha;
	return C;
}

// Surfaces.
inline const FLinearColor Abyss = SRGB(11, 9, 19);              // #0B0913 deepest background
inline const FLinearColor Panel = SRGB(24, 19, 34, 0.90f);      // translucent obsidian behind menus and plates
inline const FLinearColor Plate = SRGB(18, 14, 26, 0.94f);      // near-opaque behind numbers that must not vary (timer)
inline const FLinearColor Track = SRGB(22, 18, 30, 0.96f);      // empty part of a bar
// Text (contrast against the panel over the dark stage: TextPrimary 16.2:1, TextSecondary 6.3:1, FocusText 8.5:1).
inline const FLinearColor TextPrimary = SRGB(243, 239, 249);    // #F3EFF9 moonlight
inline const FLinearColor TextSecondary = SRGB(154, 148, 174);  // #9A94AE descriptions, unselected values
inline const FLinearColor FocusText = SRGB(194, 162, 242);      // #C2A2F2 violet that passes as text
// Lines and ornament.
inline const FLinearColor Silver = SRGB(214, 212, 226);         // #D6D4E2 hairlines, frames, emblem
// Focus: shapes only (4.6:1 on the panel, 3.9:1 on the lightest surface #282036: not relied on as text).
inline const FLinearColor Focus = SRGB(161, 92, 232);           // #A15CE8
// Players (identity is always also written: P1, P2, CPU, PARTNER).
inline const FLinearColor P1 = SRGB(227, 169, 60);              // #E3A93C
inline const FLinearColor P2 = Silver;
// Fighters' accents, kept to their own side of the screen.
inline const FLinearColor WrenAccent = SRGB(227, 169, 60);      // golden Spirit
inline const FLinearColor AshkaAccent = SRGB(217, 52, 59);      // crimson Lamplighter Flame (fills, lines)
inline const FLinearColor AshkaText = SRGB(240, 90, 95);        // the crimson that passes as text (4.7:1)
// Bars.
inline const FLinearColor Health = SRGB(230, 226, 236);
inline const FLinearColor HealthLow = SRGB(240, 184, 78);       // under 30%: amber, plus the bar's length
inline const FLinearColor HealthLag = SRGB(190, 58, 76);        // #BE3A4C damage just taken (>= 3:1 against track, health, amber)
// Meaning.
inline const FLinearColor Warning = SRGB(240, 90, 95);
inline const FLinearColor Success = SRGB(126, 214, 160);

inline FLinearColor Alpha(const FLinearColor& C, float A)
{
	return FLinearColor(C.R, C.G, C.B, C.A * A);
}

// Type scale, in Slate points (1 pt = 4/3 px at the 1080p virtual canvas). With the bundled fonts, 20 pt is the
// smallest size whose body height (ascender to descender) reaches 26 px, the floor for essential text at TV distance
// (Xbox Accessibility Guideline 101); nothing a player needs is set smaller.
namespace Type
{
inline constexpr float Banner = 104.0f;   // round and KO banners (display)
inline constexpr float Title = 44.0f;     // screen titles (display)
inline constexpr float Heading = 32.0f;   // panel headings, combo counts (display)
inline constexpr float Name = 30.0f;      // fighter names in the HUD (display)
inline constexpr float Menu = 26.0f;      // menu rows (body)
inline constexpr float Body = 22.0f;      // descriptions, values, table rows (body)
inline constexpr float Label = 20.0f;     // the minimum: tags, gauge labels, prompts, table notes (body)
}

// Button glyphs: the letter inside is half the glyph's height, so 40 px keeps it at the 20 pt minimum.
inline constexpr float GlyphHeight = 40.0f;
}
