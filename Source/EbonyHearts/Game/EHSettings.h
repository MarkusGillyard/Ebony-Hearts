// Player settings: persisted as JSON in the game's own Saved folder (never another project's saves).
#pragma once

#include "CoreMinimal.h"
#include "InputCoreTypes.h"

// Gameplay actions: what the combat simulation and training read. Remappable per player and per device class.
// The order is stable; settings files store each action by its EHActionId string, not by this number.
enum class EEHAction : uint8
{
	Left,
	Right,
	Jump,    // up
	Light,
	Heavy,
	Special,
	Throw,   // Grab / Throw: no default buttons while grappling is switched off (EHFormerGrabKey keeps its old ones)
	Dodge,
	Block,
	Reset,   // training quick reset
	Count
};

// Menu commands: fixed per device class (never remappable), so a player can never lock themselves out of the menus.
enum class EEHNav : uint8
{
	Up,
	Down,
	Left,
	Right,
	Confirm,
	Back,
	Pause,
	Count
};

// One gameplay layout per player and device class. Both keyboard sides share one physical keyboard.
enum class EEHBindingSet : uint8
{
	KeyboardA,   // player one, left side of the keyboard
	KeyboardB,   // player two, right side of the keyboard
	GamepadP1,   // player one's controller layout
	GamepadP2,   // player two's controller layout (Local Versus)
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
constexpr int32 EHNavCount = static_cast<int32>(EEHNav::Count);
constexpr int32 EHSetCount = static_cast<int32>(EEHBindingSet::Count);
constexpr int32 EHKeysPerAction = 3;   // primary, secondary and third button of an action in one layout

inline bool EHIsKeyboardSet(EEHBindingSet Set) { return Set == EEHBindingSet::KeyboardA || Set == EEHBindingSet::KeyboardB; }

// A single binding slot.
struct FEHBindingRef
{
	EEHBindingSet Set = EEHBindingSet::Count;
	EEHAction Action = EEHAction::Count;
	int32 Slot = -1;
	bool IsValid() const { return Set != EEHBindingSet::Count && Action != EEHAction::Count && Slot >= 0; }
};

// How an assignment treats another action that already uses the key.
enum class EEHConflictResolve : uint8
{
	Swap,      // the other action takes the slot's previous key
	Replace,   // the other action loses the key (its slot is cleared)
};

struct FEHBindings
{
	FKey Keys[EHSetCount][EHActionCount][EHKeysPerAction];

	static FEHBindings Defaults();
	const FKey& Get(EEHBindingSet Set, EEHAction Action, int32 Slot) const { return Keys[static_cast<int32>(Set)][static_cast<int32>(Action)][Slot]; }
	// The first bound key of an action (primary, else secondary), or EKeys::Invalid.
	FKey First(EEHBindingSet Set, EEHAction Action) const;
	// Returns the action bound to Key in the set, or EEHAction::Count.
	EEHAction Find(EEHBindingSet Set, const FKey& Key) const;
	// Another slot in the same input context that already uses Key (both keyboard sides share one keyboard), including
	// the action's own other slot. Invalid if the key is free.
	FEHBindingRef FindConflict(EEHBindingSet Set, EEHAction Action, int32 Slot, const FKey& Key) const;
	// Binds Key to (Set, Action, Slot). A conflicting slot of another action is swapped or cleared, never silently
	// duplicated; if the key sits in the action's own other slot, the two slots trade keys.
	void Assign(EEHBindingSet Set, EEHAction Action, int32 Slot, const FKey& Key, EEHConflictResolve Resolve);
	void Clear(EEHBindingSet Set, EEHAction Action, int32 Slot);
	// Restores an action's default keys; other actions using those keys lose them. Returns what was taken, or empty.
	FString ResetAction(EEHBindingSet Set, EEHAction Action);
	void ResetSet(EEHBindingSet Set);
	bool IsUnbound(EEHBindingSet Set, EEHAction Action) const { return !First(Set, Action).IsValid(); }
	// Reports the first duplicate key within an input context, or a reserved key, for one set (or all sets).
	bool HasConflicts(FString* OutReport = nullptr, EEHBindingSet Only = EEHBindingSet::Count) const;
	// Keys a gameplay action may use: no mouse, analog axes or stick directions, and not the fixed pause keys.
	static bool IsBindable(EEHBindingSet Set, const FKey& Key);
};

// Fixed menu controls. Class is KeyboardA, KeyboardB, or GamepadP1 for any controller.
EEHNav EHMenuCommand(EEHBindingSet Class, const FKey& Key);
// The key shown in prompts for a menu command.
FKey EHMenuKey(EEHBindingSet Class, EEHNav Nav);

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
	// Version 1 files keep their keyboard layouts; their controller layout moves to the current default.
	static FEHSettings Load(FString* OutWarning = nullptr, const FString& PathOverride = FString());
	bool Save(const FString& PathOverride = FString()) const;
	void Clamp();
};

// Grab's default buttons before grappling was switched off (slot 0..2, EKeys::Invalid when none): the settings loader
// moves them to their new actions, and they are the defaults to restore if grappling returns.
FKey EHFormerGrabKey(EEHBindingSet Set, int32 Slot);

// Short name used in logs and automation scripts ("Light", "Grab", ...).
const TCHAR* EHActionName(EEHAction Action);
// Stable identifier stored in settings files ("LightAttack", "Grab", ...).
const TCHAR* EHActionId(EEHAction Action);
// Player-facing name ("Light attack", "Grab / Throw", ...).
const TCHAR* EHActionLabel(EEHAction Action);
const TCHAR* EHNavName(EEHNav Nav);
const TCHAR* EHSetId(EEHBindingSet Set);
const TCHAR* EHSetLabel(EEHBindingSet Set);
