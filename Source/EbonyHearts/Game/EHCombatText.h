// Comic-book combat text (milestone 7): short lines that sometimes jump out beside a speaker mid-fight, with no
// voice. The wolves speak in their alignment's voice (friendly remarks, warnings, hostile trash talk) and the player
// answers. Every line is the creator's to write; until then the lines in Content/Data/firstperson.json
// ("combatText") are visibly marked placeholders that test timing and layout only.
//
// The text is occasional: the first time a speaker has something to say of a kind it says it; after that a line is
// offered by chance, with a gap after any line and a longer one per speaker, and never more than a few at once.
// Placement: beside the speaker's head, pushed apart so bubbles never overlap, kept inside the view (a speaker off
// screen speaks from the nearest edge, its tail pointing the way). The player's lines sit low, as captions.
// Reduced flashing: lines fade in instead of popping. The interface scale setting scales the bubbles with the HUD.
#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

class AActor;
class APlayerController;
class FEHPainter;
struct FEHFonts;

enum class EEHLineKind : uint8
{
	Friendly,
	Warning,
	Hostile,
	Player,
};

const TCHAR* EHLineKindName(EEHLineKind K);

struct FEHCombatLine
{
	FString Text;
	bool bPlaceholder = true;
};

struct FEHCombatTextTuning
{
	bool bEnabled = true;
	float Chance = 0.4f;          // after a speaker's first line of an event, the chance a later one is said
	float GlobalGap = 1.5f;       // seconds after any line before another (natural lines; forced test lines ignore it)
	float SpeakerGap = 5.0f;      // seconds before the same speaker speaks again
	int32 MaxVisible = 3;
	float LifeBase = 1.4f;        // seconds on screen: base + per character, clamped
	float LifePerChar = 0.045f;
	float LifeMin = 2.0f;
	float LifeMax = 3.6f;
	float PopSeconds = 0.18f;     // the jump-out (scale overshoot); reduced flashing fades in over FadeIn instead
	float FadeIn = 0.25f;
	float FadeOut = 0.35f;
	float MaxWidth = 440.0f;      // virtual units (1920 x 1080 canvas) before a line wraps
	float FontSize = 22.0f;
	TMap<FString, TArray<FEHCombatLine>> Lines;   // by event, e.g. "wolf.hostile.attack"
	bool Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError);
};

class FEHCombatText
{
public:
	FEHCombatTextTuning Tuning;

	// A speaker (nullptr: the player) has something to say about Event. Returns true when a line is shown. bForce
	// (development tests) skips the chance and the gaps; when full, the oldest line gives way.
	bool Offer(const FString& Event, const AActor* Speaker, EEHLineKind Kind, float Now, bool bForce = false);
	void Tick(float DeltaSeconds);
	void Clear();                 // reset and death: every line gone, every speaker's memory cleared
	// Lays out and draws every line. ViewTo projects a world point to virtual canvas coordinates (false behind the
	// camera). Speakers that no longer exist lose their lines.
	void Paint(FEHPainter& P, const FEHFonts& Fonts, const FTransform& View, TFunctionRef<bool(const FVector&, FVector2f&)> ViewTo, bool bReduceFlash);

	// Evidence for the automation (fp_expect ct_*).
	int32 Visible() const { return Bubbles.Num(); }
	int32 Shown = 0;
	int32 ShownByKind[4] = {0, 0, 0, 0};
	int32 MaxVisibleSeen = 0;
	int32 OverlapsSeen = 0;       // the most overlapping pairs in any one frame
	float LastOffscreenX = 0.0f; // last off-screen anchor relative to the view centre
	int32 Offscreen = 0;          // visible lines whose speaker is off screen (last frame)
	int32 OutsideView = 0;        // visible lines drawn even partly outside the view (last frame)
	int32 Popping = 0;            // lines in their jump-out (last frame)
	int32 Placeholders = 0;       // visible placeholder lines (last frame)
	float LastHeightPx = 0.0f;    // the newest line's height on screen, in pixels (scales with the interface scale)
	int32 Refused = 0;
	int32 Suppressed = 0;         // lines with no free place this frame (not drawn; last frame)
	bool bNatural = true;         // development tests: false stops lines arising on their own (forced lines still show)
	FString LastText;

private:
	struct FBubble
	{
		TWeakObjectPtr<const AActor> Speaker;
		bool bPlayer = false;
		EEHLineKind Kind = EEHLineKind::Hostile;
		FString Text;
		bool bPlaceholder = true;
		float Age = 0.0f;
		float Life = 2.0f;
		int32 Serial = 0;
	};
	TArray<FBubble> Bubbles;
	TMap<FString, float> SpeakerLast;      // speaker key -> time of its last line
	TSet<FString> SaidOnce;                // speaker key + event: the first line of an event always comes
	TMap<FString, int32> NextLine;         // event -> next line index (lines cycle)
	float LastAny = -1000.0f;
	int32 Serial = 0;
	static FString KeyOf(const AActor* Speaker);
	TArray<FString> Wrap(const FString& Text, const FEHPainter& P, const struct FSlateFontInfo& Font) const;
};
