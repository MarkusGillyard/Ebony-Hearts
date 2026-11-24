// The player's alignment: nine tiers, three each of Good, Neutral and Evil, built around the three anchors of the
// creator's design (2026-11-22): Hero of Humanity (the highest good), Platonic (the most middling neutral) and
// Forsaken (the lowest evil). The prototype has no real meter: a developer selector sets the tier directly, and
// harming or killing a Chapel wolf pushes it toward evil. Most characters react to the band; only important ones
// react to single tiers (the wolves single out Hero of Humanity).
#pragma once

#include "CoreMinimal.h"

enum class EEHAlignBand : uint8 { Good, Neutral, Evil };

namespace EHAlign
{
constexpr int32 Count = 9;
constexpr int32 Hero = 0;          // Hero of Humanity, the highest tier of good
constexpr int32 Platonic = 4;      // the most middling neutral: the default
constexpr int32 FirstEvil = 6;     // Ruthless
constexpr int32 Malevolent = 7;
constexpr int32 Forsaken = 8;      // the lowest of the low

inline const TCHAR* Name(int32 Tier)
{
	static const TCHAR* Names[Count] = {
		TEXT("Hero of Humanity"), TEXT("Honorable"), TEXT("Kindhearted"),
		TEXT("Well-meaning"), TEXT("Platonic"), TEXT("Self-serving"),
		TEXT("Ruthless"), TEXT("Malevolent"), TEXT("Forsaken")};
	return Names[FMath::Clamp(Tier, 0, Count - 1)];
}

inline EEHAlignBand Band(int32 Tier)
{
	return Tier < 3 ? EEHAlignBand::Good : (Tier < FirstEvil ? EEHAlignBand::Neutral : EEHAlignBand::Evil);
}

inline const TCHAR* BandName(EEHAlignBand B)
{
	return B == EEHAlignBand::Good ? TEXT("Good") : (B == EEHAlignBand::Neutral ? TEXT("Neutral") : TEXT("Evil"));
}

// Killing a guardian: at least Malevolent, or one tier deeper if already evil (the prototype's reading of "brought
// down to a higher stage of evil"). Hero of Humanity cannot kill one at all.
inline int32 AfterKill(int32 Tier) { return Tier < FirstEvil ? Malevolent : FMath::Min(Forsaken, Tier + 1); }
// Harming one: a tier toward evil.
inline int32 AfterHarm(int32 Tier) { return FMath::Min(Forsaken, Tier + 1); }
}
