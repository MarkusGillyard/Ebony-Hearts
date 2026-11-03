// Player settings: persisted as JSON in the game's own Saved folder (never another project's saves).
#pragma once

#include "CoreMinimal.h"
#include "InputCoreTypes.h"

enum class EEHAction : uint8
{
	Left,
	Right,
	Up,
	Down,
	Light,
	Heavy,
	Special,
	Throw,
	Dodge,
	Block,
	Pause,
	Reset,   // training quick reset
	Count
};

enum class EEHBindingSet : uint8
{
	KeyboardA,   // player one side of the keyboard
	KeyboardB,   // player two side of the keyboard
	Gamepad,
	Count
};

enum class EEHPromptStyle : uint8
{
	Auto,
	Keyboard,
	PlayStation,
	Xbox,
};

constexpr int32 EHActionCount = static_cast<int32>(EEHAction::Count);
constexpr int32 EHSetCount = static_cast<int32>(EEHBindingSet::Count);
constexpr int32 EHKeysPerAction = 2;

struct FEHBindings
{
	FKey Keys[EHSetCount][EHActionCount][EHKeysPerAction];

	static FEHBindings Defaults();
	// Returns the action bound to Key in the set, or EEHAction::Count.
	EEHAction Find(EEHBindingSet Set, const FKey& Key) const;
	// Assigns Key to (Set, Action, Slot). A conflicting binding in the same set, or in the other keyboard set,
	// is moved to the previous key of the slot being replaced (swap), so no key is ever bound twice.
	// Returns a description of the swap for the UI, or an empty string.
	FString Assign(EEHBindingSet Set, EEHAction Action, int32 Slot, const FKey& Key);
	bool HasConflicts(FString* OutReport = nullptr) const;
};

struct FEHSettings
{
	// Video
	int32 WindowMode = 1;            // 0 fullscreen, 1 windowed fullscreen, 2 windowed
	FIntPoint Resolution = FIntPoint(1920, 1080);
	int32 Quality = 2;               // 0 low, 1 medium, 2 high, 3 epic
	int32 FrameCap = 0;              // 0 = follow vsync/uncapped, otherwise fps
	bool bVSync = true;
	int32 RenderScale = 100;         // percent of output resolution
	// Audio (0-100)
	int32 MasterVolume = 80;
	int32 MusicVolume = 60;
	int32 EffectsVolume = 90;
	int32 AmbienceVolume = 70;
	// Accessibility and interface
	float UIScale = 1.0f;
	bool bReduceShake = false;
	bool bReduceFlash = false;
	bool bInputHints = true;
	EEHPromptStyle PromptStyle = EEHPromptStyle::Auto;
	// Gameplay
	int32 CpuLevel = 1;
	FEHBindings Bindings = FEHBindings::Defaults();

	static FString FilePath();
	// Loads settings; a missing or corrupt file yields defaults (a corrupt file is kept as .bad for inspection).
	static FEHSettings Load(FString* OutWarning = nullptr);
	bool Save() const;
	void Clamp();
};

const TCHAR* EHActionName(EEHAction Action);
