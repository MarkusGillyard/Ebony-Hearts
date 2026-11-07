#include "EHSettings.h"

#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

const TCHAR* EHActionName(EEHAction Action)
{
	switch (Action)
	{
	case EEHAction::Left: return TEXT("Left");
	case EEHAction::Right: return TEXT("Right");
	case EEHAction::Jump: return TEXT("Jump");
	case EEHAction::Light: return TEXT("Light");
	case EEHAction::Heavy: return TEXT("Heavy");
	case EEHAction::Special: return TEXT("Special");
	case EEHAction::Throw: return TEXT("Grab");
	case EEHAction::Dodge: return TEXT("Dodge");
	case EEHAction::Block: return TEXT("Block");
	case EEHAction::Reset: return TEXT("Reset");
	default: return TEXT("?");
	}
}

const TCHAR* EHActionId(EEHAction Action)
{
	switch (Action)
	{
	case EEHAction::Left: return TEXT("MoveLeft");
	case EEHAction::Right: return TEXT("MoveRight");
	case EEHAction::Jump: return TEXT("Jump");
	case EEHAction::Light: return TEXT("LightAttack");
	case EEHAction::Heavy: return TEXT("HeavyAttack");
	case EEHAction::Special: return TEXT("Special");
	case EEHAction::Throw: return TEXT("Grab");
	case EEHAction::Dodge: return TEXT("Dodge");
	case EEHAction::Block: return TEXT("Block");
	case EEHAction::Reset: return TEXT("TrainingReset");
	default: return TEXT("?");
	}
}

const TCHAR* EHActionLabel(EEHAction Action)
{
	switch (Action)
	{
	case EEHAction::Left: return TEXT("Move left");
	case EEHAction::Right: return TEXT("Move right");
	case EEHAction::Jump: return TEXT("Jump");
	case EEHAction::Light: return TEXT("Light attack");
	case EEHAction::Heavy: return TEXT("Heavy attack");
	case EEHAction::Special: return TEXT("Special");
	case EEHAction::Throw: return TEXT("Grab / Throw");
	case EEHAction::Dodge: return TEXT("Dodge / Roll");
	case EEHAction::Block: return TEXT("Block (hold)");
	case EEHAction::Reset: return TEXT("Training reset");
	default: return TEXT("?");
	}
}

const TCHAR* EHNavName(EEHNav Nav)
{
	switch (Nav)
	{
	case EEHNav::Up: return TEXT("Up");
	case EEHNav::Down: return TEXT("Down");
	case EEHNav::Left: return TEXT("Left");
	case EEHNav::Right: return TEXT("Right");
	case EEHNav::Confirm: return TEXT("Confirm");
	case EEHNav::Back: return TEXT("Back");
	case EEHNav::Pause: return TEXT("Pause");
	default: return TEXT("?");
	}
}

const TCHAR* EHSetId(EEHBindingSet Set)
{
	switch (Set)
	{
	case EEHBindingSet::KeyboardA: return TEXT("keyboard1");
	case EEHBindingSet::KeyboardB: return TEXT("keyboard2");
	case EEHBindingSet::GamepadP1: return TEXT("controller1");
	case EEHBindingSet::GamepadP2: return TEXT("controller2");
	default: return TEXT("?");
	}
}

const TCHAR* EHSetLabel(EEHBindingSet Set)
{
	switch (Set)
	{
	case EEHBindingSet::KeyboardA: return TEXT("Keyboard - Player 1 (left side)");
	case EEHBindingSet::KeyboardB: return TEXT("Keyboard - Player 2 (right side)");
	case EEHBindingSet::GamepadP1: return TEXT("Controller - Player 1");
	case EEHBindingSet::GamepadP2: return TEXT("Controller - Player 2");
	default: return TEXT("?");
	}
}

namespace EHBindingDetail
{
// Sets that share physical keys: both keyboard sides, or a controller layout on its own.
TArray<EEHBindingSet> Context(EEHBindingSet Set)
{
	if (EHIsKeyboardSet(Set))
	{
		return {EEHBindingSet::KeyboardA, EEHBindingSet::KeyboardB};
	}
	return {Set};
}

int32 Idx(EEHBindingSet Set) { return static_cast<int32>(Set); }
int32 Idx(EEHAction Action) { return static_cast<int32>(Action); }
}
using namespace EHBindingDetail;

FKey EHFormerGrabKey(EEHBindingSet Set, int32 Slot)
{
	switch (Set)
	{
	case EEHBindingSet::KeyboardA: return Slot == 0 ? EKeys::I : EKeys::Invalid;
	case EEHBindingSet::KeyboardB: return Slot == 0 ? EKeys::NumPadFive : (Slot == 1 ? EKeys::Semicolon : EKeys::Invalid);
	case EEHBindingSet::GamepadP1:
	case EEHBindingSet::GamepadP2: return Slot == 0 ? EKeys::Gamepad_FaceButton_Bottom : (Slot == 1 ? EKeys::Gamepad_LeftShoulder : EKeys::Invalid);
	default: return EKeys::Invalid;
	}
}

FEHBindings FEHBindings::Defaults()
{
	FEHBindings B;
	auto Set = [&B](EEHBindingSet S, EEHAction A, const FKey& K0, const FKey& K1 = EKeys::Invalid, const FKey& K2 = EKeys::Invalid) {
		B.Keys[Idx(S)][Idx(A)][0] = K0;
		B.Keys[Idx(S)][Idx(A)][1] = K1;
		B.Keys[Idx(S)][Idx(A)][2] = K2;
	};
	// Grappling is switched off, so Grab has no buttons: its former ones (EHFormerGrabKey) jump, and L1 / LB also
	// blocks. The jump buttons jump the way the stick or movement keys point, like up does.
	using S = EEHBindingSet;
	using A = EEHAction;
	Set(S::KeyboardA, A::Left, EKeys::A);
	Set(S::KeyboardA, A::Right, EKeys::D);
	Set(S::KeyboardA, A::Jump, EKeys::W, EKeys::I);
	Set(S::KeyboardA, A::Light, EKeys::J, EKeys::Enter);
	Set(S::KeyboardA, A::Heavy, EKeys::K, EKeys::BackSpace);
	Set(S::KeyboardA, A::Special, EKeys::L);
	Set(S::KeyboardA, A::Dodge, EKeys::O);
	Set(S::KeyboardA, A::Block, EKeys::SpaceBar);
	Set(S::KeyboardA, A::Reset, EKeys::R);

	Set(S::KeyboardB, A::Left, EKeys::Left);
	Set(S::KeyboardB, A::Right, EKeys::Right);
	Set(S::KeyboardB, A::Jump, EKeys::Up, EKeys::NumPadFive, EKeys::Semicolon);
	Set(S::KeyboardB, A::Light, EKeys::NumPadOne, EKeys::Comma);
	Set(S::KeyboardB, A::Heavy, EKeys::NumPadTwo, EKeys::Period);
	Set(S::KeyboardB, A::Special, EKeys::NumPadThree, EKeys::Slash);
	Set(S::KeyboardB, A::Dodge, EKeys::NumPadSix, EKeys::Apostrophe);
	Set(S::KeyboardB, A::Block, EKeys::NumPadZero, EKeys::RightShift);
	Set(S::KeyboardB, A::Reset, EKeys::NumPadSeven, EKeys::Hyphen);

	// Controller layout specified by the creator. Unreal names buttons by position, so PlayStation and Xbox match:
	// FaceButton_Left = Square / X, Top = Triangle / Y, Right = Circle / B, Bottom = Cross / A.
	for (S Pad : {S::GamepadP1, S::GamepadP2})
	{
		Set(Pad, A::Left, EKeys::Gamepad_DPad_Left);
		Set(Pad, A::Right, EKeys::Gamepad_DPad_Right);
		Set(Pad, A::Jump, EKeys::Gamepad_DPad_Up, EKeys::Gamepad_FaceButton_Bottom);   // the left stick's up also jumps (EHInputRouter)
		Set(Pad, A::Light, EKeys::Gamepad_FaceButton_Left);
		Set(Pad, A::Heavy, EKeys::Gamepad_FaceButton_Top);
		Set(Pad, A::Special, EKeys::Gamepad_RightShoulder);
		Set(Pad, A::Dodge, EKeys::Gamepad_FaceButton_Right);
		Set(Pad, A::Block, EKeys::Gamepad_RightTrigger, EKeys::Gamepad_LeftShoulder);
		Set(Pad, A::Reset, EKeys::Gamepad_Special_Left);
	}
	return B;
}

FKey FEHBindings::First(EEHBindingSet Set, EEHAction Action) const
{
	const FKey& K0 = Get(Set, Action, 0);
	if (K0.IsValid())
	{
		return K0;
	}
	for (int32 K = 1; K < EHKeysPerAction; ++K)
	{
		if (Get(Set, Action, K).IsValid())
		{
			return Get(Set, Action, K);
		}
	}
	return EKeys::Invalid;
}

EEHAction FEHBindings::Find(EEHBindingSet Set, const FKey& Key) const
{
	if (!Key.IsValid())
	{
		return EEHAction::Count;
	}
	const int32 S = Idx(Set);
	for (int32 A = 0; A < EHActionCount; ++A)
	{
		for (int32 K = 0; K < EHKeysPerAction; ++K)
		{
			if (Keys[S][A][K] == Key)
			{
				return static_cast<EEHAction>(A);
			}
		}
	}
	return EEHAction::Count;
}

FEHBindingRef FEHBindings::FindConflict(EEHBindingSet Set, EEHAction Action, int32 Slot, const FKey& Key) const
{
	FEHBindingRef Out;
	if (!Key.IsValid())
	{
		return Out;
	}
	for (EEHBindingSet CS : Context(Set))
	{
		for (int32 CA = 0; CA < EHActionCount; ++CA)
		{
			for (int32 CK = 0; CK < EHKeysPerAction; ++CK)
			{
				const bool bSelf = CS == Set && CA == Idx(Action) && CK == Slot;
				if (!bSelf && Keys[Idx(CS)][CA][CK] == Key)
				{
					Out.Set = CS;
					Out.Action = static_cast<EEHAction>(CA);
					Out.Slot = CK;
					return Out;
				}
			}
		}
	}
	return Out;
}

void FEHBindings::Assign(EEHBindingSet Set, EEHAction Action, int32 Slot, const FKey& Key, EEHConflictResolve Resolve)
{
	FKey& Target = Keys[Idx(Set)][Idx(Action)][Slot];
	const FKey Previous = Target;
	const FEHBindingRef C = FindConflict(Set, Action, Slot, Key);
	if (C.IsValid())
	{
		FKey& Other = Keys[Idx(C.Set)][Idx(C.Action)][C.Slot];
		const bool bOwnOtherSlot = C.Set == Set && C.Action == Action;
		Other = (bOwnOtherSlot || Resolve == EEHConflictResolve::Swap) ? Previous : FKey(EKeys::Invalid);
	}
	Target = Key;
}

void FEHBindings::Clear(EEHBindingSet Set, EEHAction Action, int32 Slot)
{
	Keys[Idx(Set)][Idx(Action)][Slot] = EKeys::Invalid;
}

FString FEHBindings::ResetAction(EEHBindingSet Set, EEHAction Action)
{
	const FEHBindings D = Defaults();
	FString Report;
	for (int32 K = 0; K < EHKeysPerAction; ++K)
	{
		const FKey& Key = D.Get(Set, Action, K);
		const FEHBindingRef C = FindConflict(Set, Action, K, Key);
		if (C.IsValid() && !(C.Set == Set && C.Action == Action))
		{
			Keys[Idx(C.Set)][Idx(C.Action)][C.Slot] = EKeys::Invalid;
			Report += FString::Printf(TEXT("%s%s removed from %s"), Report.IsEmpty() ? TEXT("") : TEXT("; "), *Key.GetDisplayName(false).ToString(), EHActionLabel(C.Action));
		}
	}
	for (int32 K = 0; K < EHKeysPerAction; ++K)
	{
		Keys[Idx(Set)][Idx(Action)][K] = D.Get(Set, Action, K);
	}
	return Report;
}

void FEHBindings::ResetSet(EEHBindingSet Set)
{
	const FEHBindings D = Defaults();
	for (int32 A = 0; A < EHActionCount; ++A)
	{
		for (int32 K = 0; K < EHKeysPerAction; ++K)
		{
			Keys[Idx(Set)][A][K] = D.Keys[Idx(Set)][A][K];
		}
	}
	// The other keyboard side may have taken one of these keys; it gives it up.
	for (EEHBindingSet Other : Context(Set))
	{
		if (Other == Set)
		{
			continue;
		}
		for (int32 A = 0; A < EHActionCount; ++A)
		{
			for (int32 K = 0; K < EHKeysPerAction; ++K)
			{
				if (Find(Set, Keys[Idx(Other)][A][K]) != EEHAction::Count)
				{
					Keys[Idx(Other)][A][K] = EKeys::Invalid;
				}
			}
		}
	}
}

bool FEHBindings::IsBindable(EEHBindingSet Set, const FKey& Key)
{
	if (!Key.IsValid() || Key.IsMouseButton() || Key.IsAxis1D() || Key.IsAxis2D() || Key.IsAxis3D())
	{
		return false;
	}
	if (EHIsKeyboardSet(Set))
	{
		// Escape and the right side's pause keys always pause, so they are kept out of gameplay layouts.
		return !Key.IsGamepadKey() && Key != EKeys::Escape && Key != EKeys::NumPadNine && Key != EKeys::Equals;
	}
	if (!Key.IsGamepadKey() || Key == EKeys::Gamepad_Special_Right)
	{
		return false;   // Options / Menu always pauses
	}
	// Stick directions are synthesized from the analog stick; the stick always moves and navigates.
	return Key != EKeys::Gamepad_LeftStick_Up && Key != EKeys::Gamepad_LeftStick_Down && Key != EKeys::Gamepad_LeftStick_Left &&
		Key != EKeys::Gamepad_LeftStick_Right && Key != EKeys::Gamepad_RightStick_Up && Key != EKeys::Gamepad_RightStick_Down &&
		Key != EKeys::Gamepad_RightStick_Left && Key != EKeys::Gamepad_RightStick_Right;
}

bool FEHBindings::HasConflicts(FString* OutReport, EEHBindingSet Only) const
{
	TArray<TArray<EEHBindingSet>> Groups = {{EEHBindingSet::KeyboardA, EEHBindingSet::KeyboardB}, {EEHBindingSet::GamepadP1}, {EEHBindingSet::GamepadP2}};
	for (const TArray<EEHBindingSet>& Group : Groups)
	{
		if (Only != EEHBindingSet::Count && !Group.Contains(Only))
		{
			continue;
		}
		TMap<FKey, FString> Seen;
		for (EEHBindingSet S : Group)
		{
			for (int32 A = 0; A < EHActionCount; ++A)
			{
				for (int32 K = 0; K < EHKeysPerAction; ++K)
				{
					const FKey& Key = Keys[Idx(S)][A][K];
					if (!Key.IsValid())
					{
						continue;
					}
					const FString Owner = FString::Printf(TEXT("%s/%s"), EHSetId(S), EHActionId(static_cast<EEHAction>(A)));
					if (!IsBindable(S, Key))
					{
						if (OutReport)
						{
							*OutReport = FString::Printf(TEXT("%s cannot be used by %s"), *Key.ToString(), *Owner);
						}
						return true;
					}
					if (const FString* Existing = Seen.Find(Key))
					{
						if (OutReport)
						{
							*OutReport = FString::Printf(TEXT("%s bound to %s and %s"), *Key.ToString(), **Existing, *Owner);
						}
						return true;
					}
					Seen.Add(Key, Owner);
				}
			}
		}
	}
	return false;
}

EEHNav EHMenuCommand(EEHBindingSet Class, const FKey& Key)
{
	if (Class == EEHBindingSet::KeyboardA)
	{
		if (Key == EKeys::W) return EEHNav::Up;
		if (Key == EKeys::S) return EEHNav::Down;
		if (Key == EKeys::A) return EEHNav::Left;
		if (Key == EKeys::D) return EEHNav::Right;
		if (Key == EKeys::Enter || Key == EKeys::J || Key == EKeys::SpaceBar) return EEHNav::Confirm;
		if (Key == EKeys::BackSpace || Key == EKeys::K) return EEHNav::Back;
		if (Key == EKeys::Escape) return EEHNav::Pause;
		return EEHNav::Count;
	}
	if (Class == EEHBindingSet::KeyboardB)
	{
		if (Key == EKeys::Up) return EEHNav::Up;
		if (Key == EKeys::Down) return EEHNav::Down;
		if (Key == EKeys::Left) return EEHNav::Left;
		if (Key == EKeys::Right) return EEHNav::Right;
		if (Key == EKeys::NumPadOne || Key == EKeys::Comma) return EEHNav::Confirm;
		if (Key == EKeys::NumPadTwo || Key == EKeys::Period) return EEHNav::Back;
		if (Key == EKeys::NumPadNine || Key == EKeys::Equals) return EEHNav::Pause;
		return EEHNav::Count;
	}
	if (Key == EKeys::Gamepad_DPad_Up) return EEHNav::Up;
	if (Key == EKeys::Gamepad_DPad_Down) return EEHNav::Down;
	if (Key == EKeys::Gamepad_DPad_Left) return EEHNav::Left;
	if (Key == EKeys::Gamepad_DPad_Right) return EEHNav::Right;
	if (Key == EKeys::Gamepad_FaceButton_Bottom) return EEHNav::Confirm;   // Cross / A
	if (Key == EKeys::Gamepad_FaceButton_Right) return EEHNav::Back;       // Circle / B
	if (Key == EKeys::Gamepad_Special_Right) return EEHNav::Pause;         // Options / Menu
	return EEHNav::Count;
}

FKey EHMenuKey(EEHBindingSet Class, EEHNav Nav)
{
	if (Class == EEHBindingSet::KeyboardA)
	{
		switch (Nav)
		{
		case EEHNav::Up: return EKeys::W;
		case EEHNav::Down: return EKeys::S;
		case EEHNav::Left: return EKeys::A;
		case EEHNav::Right: return EKeys::D;
		case EEHNav::Confirm: return EKeys::Enter;
		case EEHNav::Back: return EKeys::Escape;   // menus treat Pause as Back
		case EEHNav::Pause: return EKeys::Escape;
		default: return EKeys::Invalid;
		}
	}
	if (Class == EEHBindingSet::KeyboardB)
	{
		switch (Nav)
		{
		case EEHNav::Up: return EKeys::Up;
		case EEHNav::Down: return EKeys::Down;
		case EEHNav::Left: return EKeys::Left;
		case EEHNav::Right: return EKeys::Right;
		case EEHNav::Confirm: return EKeys::NumPadOne;
		case EEHNav::Back: return EKeys::NumPadTwo;
		case EEHNav::Pause: return EKeys::NumPadNine;
		default: return EKeys::Invalid;
		}
	}
	switch (Nav)
	{
	case EEHNav::Up: return EKeys::Gamepad_DPad_Up;
	case EEHNav::Down: return EKeys::Gamepad_DPad_Down;
	case EEHNav::Left: return EKeys::Gamepad_DPad_Left;
	case EEHNav::Right: return EKeys::Gamepad_DPad_Right;
	case EEHNav::Confirm: return EKeys::Gamepad_FaceButton_Bottom;
	case EEHNav::Back: return EKeys::Gamepad_FaceButton_Right;
	case EEHNav::Pause: return EKeys::Gamepad_Special_Right;
	default: return EKeys::Invalid;
	}
}

FString FEHSettings::FilePath()
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EbonyHearts"), TEXT("Settings.json"));
}

void FEHSettings::Clamp()
{
	WindowMode = FMath::Clamp(WindowMode, 0, 2);
	Resolution.X = FMath::Clamp(Resolution.X, 1280, 7680);
	Resolution.Y = FMath::Clamp(Resolution.Y, 720, 4320);
	Quality = FMath::Clamp(Quality, 0, 3);
	FrameCap = (FrameCap == 0 || FrameCap == 60 || FrameCap == 120 || FrameCap == 144 || FrameCap == 165 || FrameCap == 240) ? FrameCap : 0;
	RenderScale = FMath::Clamp(RenderScale, 50, 100);
	MasterVolume = FMath::Clamp(MasterVolume, 0, 100);
	MusicVolume = FMath::Clamp(MusicVolume, 0, 100);
	EffectsVolume = FMath::Clamp(EffectsVolume, 0, 100);
	AmbienceVolume = FMath::Clamp(AmbienceVolume, 0, 100);
	UIScale = FMath::Clamp(UIScale, 0.8f, 1.4f);
	CpuLevel = FMath::Clamp(CpuLevel, 0, 2);
	if (static_cast<uint8>(PromptStyle) > static_cast<uint8>(EEHPromptStyle::Xbox))
	{
		PromptStyle = EEHPromptStyle::Auto;
	}
}

FEHSettings FEHSettings::Load(FString* OutWarning, const FString& PathOverride)
{
	FEHSettings S;
	FString Text;
	const FString Path = PathOverride.IsEmpty() ? FilePath() : PathOverride;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		return S;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		IFileManager::Get().Move(*(Path + TEXT(".bad")), *Path, true, true);
		if (OutWarning)
		{
			*OutWarning = TEXT("Settings file was unreadable; defaults restored.");
		}
		return S;
	}
	auto Int = [&Root](const TCHAR* Name, int32& Out) {
		double V = 0;
		if (Root->TryGetNumberField(Name, V)) Out = static_cast<int32>(V);
	};
	auto Bool = [&Root](const TCHAR* Name, bool& Out) {
		bool V = false;
		if (Root->TryGetBoolField(Name, V)) Out = V;
	};
	int32 Version = 1;
	Int(TEXT("version"), Version);
	Int(TEXT("windowMode"), S.WindowMode);
	Int(TEXT("resX"), S.Resolution.X);
	Int(TEXT("resY"), S.Resolution.Y);
	Int(TEXT("quality"), S.Quality);
	Int(TEXT("frameCap"), S.FrameCap);
	Bool(TEXT("vsync"), S.bVSync);
	Int(TEXT("renderScale"), S.RenderScale);
	Int(TEXT("masterVolume"), S.MasterVolume);
	Int(TEXT("musicVolume"), S.MusicVolume);
	Int(TEXT("effectsVolume"), S.EffectsVolume);
	Int(TEXT("ambienceVolume"), S.AmbienceVolume);
	double Scale = S.UIScale;
	if (Root->TryGetNumberField(TEXT("uiScale"), Scale)) S.UIScale = static_cast<float>(Scale);
	Bool(TEXT("reduceShake"), S.bReduceShake);
	Bool(TEXT("reduceFlash"), S.bReduceFlash);
	Bool(TEXT("inputHints"), S.bInputHints);
	int32 Prompt = static_cast<int32>(S.PromptStyle);
	Int(TEXT("promptStyle"), Prompt);
	S.PromptStyle = static_cast<EEHPromptStyle>(FMath::Clamp(Prompt, 0, 3));
	Int(TEXT("cpuLevel"), S.CpuLevel);

	auto ReadSlots = [](const TArray<TSharedPtr<FJsonValue>>& Arr, FKey Out[EHKeysPerAction]) {
		for (int32 K = 0; K < EHKeysPerAction; ++K)
		{
			const FKey Key = Arr.IsValidIndex(K) ? FKey(FName(*Arr[K]->AsString())) : FKey(EKeys::Invalid);
			Out[K] = Key.IsValid() ? Key : FKey(EKeys::Invalid);
		}
	};
	FString Notes;
	const TSharedPtr<FJsonObject>* BindingsObj = nullptr;
	if (Root->TryGetObjectField(TEXT("bindings"), BindingsObj))
	{
		FEHBindings Loaded = FEHBindings::Defaults();
		if (Version >= 2)
		{
			for (int32 Set = 0; Set < EHSetCount; ++Set)
			{
				const TSharedPtr<FJsonObject>* SetObj = nullptr;
				if (!(*BindingsObj)->TryGetObjectField(EHSetId(static_cast<EEHBindingSet>(Set)), SetObj))
				{
					continue;
				}
				for (int32 A = 0; A < EHActionCount; ++A)
				{
					const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
					if ((*SetObj)->TryGetArrayField(EHActionId(static_cast<EEHAction>(A)), Arr))
					{
						ReadSlots(*Arr, Loaded.Keys[Set][A]);
					}
				}
			}
		}
		else
		{
			// Version 1 stored "<set>.<name>" with sets 0/1 keyboard and 2 gamepad. Keyboard layouts carry over; the
			// controller layout changed to the creator's layout, so it starts from the new default.
			for (int32 Set = 0; Set < 2; ++Set)
			{
				for (int32 A = 0; A < EHActionCount; ++A)
				{
					const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
					const FString Field = FString::Printf(TEXT("%d.%s"), Set, EHActionName(static_cast<EEHAction>(A)));
					if ((*BindingsObj)->TryGetArrayField(Field, Arr))
					{
						ReadSlots(*Arr, Loaded.Keys[Set][A]);
					}
				}
			}
			Notes = TEXT("Controller layout updated to the new default; keyboard layouts kept.");
		}
		if (Version < 3)
		{
			// Grappling was switched off in version 3 and Grab's default buttons got new jobs (jump; L1 / LB block).
			// Those buttons leave Grab and take their new job wherever its slot is free and the button is not used
			// elsewhere; a button the player gave Grab themselves stays with Grab. (Files before version 3 also had no
			// third slot, which is how the right keyboard's ; arrives.)
			const FEHBindings New = FEHBindings::Defaults();
			auto IsFormer = [](EEHBindingSet InSet, const FKey& Key) {
				for (int32 F = 0; F < EHKeysPerAction; ++F)
				{
					if (Key.IsValid() && Key == EHFormerGrabKey(InSet, F))
					{
						return true;
					}
				}
				return false;
			};
			bool bMoved = false;
			for (int32 Set = 0; Set < EHSetCount; ++Set)
			{
				const EEHBindingSet BS = static_cast<EEHBindingSet>(Set);
				for (int32 K = 0; K < EHKeysPerAction; ++K)
				{
					FKey& Key = Loaded.Keys[Set][Idx(EEHAction::Throw)][K];
					if (IsFormer(BS, Key))
					{
						Key = EKeys::Invalid;
					}
				}
			}
			for (int32 Set = 0; Set < EHSetCount; ++Set)
			{
				const EEHBindingSet BS = static_cast<EEHBindingSet>(Set);
				for (int32 A = 0; A < EHActionCount; ++A)
				{
					for (int32 K = 0; K < EHKeysPerAction; ++K)
					{
						const FKey Key = New.Keys[Set][A][K];
						if (IsFormer(BS, Key) && !Loaded.Keys[Set][A][K].IsValid() && !Loaded.FindConflict(BS, static_cast<EEHAction>(A), K, Key).IsValid())
						{
							Loaded.Keys[Set][A][K] = Key;
							bMoved = true;
						}
					}
				}
			}
			if (bMoved)
			{
				Notes += FString::Printf(TEXT("%sGrab is switched off: its buttons now jump (L1 / LB blocks)."), Notes.IsEmpty() ? TEXT("") : TEXT(" "));
			}
		}
		// A layout with a duplicate or reserved key falls back to its defaults; the others are kept.
		for (EEHBindingSet Set : {EEHBindingSet::KeyboardA, EEHBindingSet::GamepadP1, EEHBindingSet::GamepadP2})
		{
			FString Report;
			if (Loaded.HasConflicts(&Report, Set))
			{
				if (EHIsKeyboardSet(Set))
				{
					Loaded.ResetSet(EEHBindingSet::KeyboardA);
					Loaded.ResetSet(EEHBindingSet::KeyboardB);
				}
				else
				{
					Loaded.ResetSet(Set);
				}
				Notes += FString::Printf(TEXT("%sSaved controls had a conflict (%s); that layout was reset."), Notes.IsEmpty() ? TEXT("") : TEXT(" "), *Report);
			}
		}
		S.Bindings = Loaded;
	}
	if (OutWarning && !Notes.IsEmpty())
	{
		*OutWarning = Notes;
	}
	S.Clamp();
	return S;
}

bool FEHSettings::Save(const FString& PathOverride) const
{
	TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetNumberField(TEXT("version"), 3);
	Root->SetNumberField(TEXT("windowMode"), WindowMode);
	Root->SetNumberField(TEXT("resX"), Resolution.X);
	Root->SetNumberField(TEXT("resY"), Resolution.Y);
	Root->SetNumberField(TEXT("quality"), Quality);
	Root->SetNumberField(TEXT("frameCap"), FrameCap);
	Root->SetBoolField(TEXT("vsync"), bVSync);
	Root->SetNumberField(TEXT("renderScale"), RenderScale);
	Root->SetNumberField(TEXT("masterVolume"), MasterVolume);
	Root->SetNumberField(TEXT("musicVolume"), MusicVolume);
	Root->SetNumberField(TEXT("effectsVolume"), EffectsVolume);
	Root->SetNumberField(TEXT("ambienceVolume"), AmbienceVolume);
	Root->SetNumberField(TEXT("uiScale"), UIScale);
	Root->SetBoolField(TEXT("reduceShake"), bReduceShake);
	Root->SetBoolField(TEXT("reduceFlash"), bReduceFlash);
	Root->SetBoolField(TEXT("inputHints"), bInputHints);
	Root->SetNumberField(TEXT("promptStyle"), static_cast<int32>(PromptStyle));
	Root->SetNumberField(TEXT("cpuLevel"), CpuLevel);
	TSharedRef<FJsonObject> BindingsObj = MakeShared<FJsonObject>();
	for (int32 Set = 0; Set < EHSetCount; ++Set)
	{
		TSharedRef<FJsonObject> SetObj = MakeShared<FJsonObject>();
		for (int32 A = 0; A < EHActionCount; ++A)
		{
			TArray<TSharedPtr<FJsonValue>> Arr;
			for (int32 K = 0; K < EHKeysPerAction; ++K)
			{
				const FKey& Key = Bindings.Keys[Set][A][K];
				Arr.Add(MakeShared<FJsonValueString>(Key.IsValid() ? Key.GetFName().ToString() : FString()));
			}
			SetObj->SetArrayField(EHActionId(static_cast<EEHAction>(A)), Arr);
		}
		BindingsObj->SetObjectField(EHSetId(static_cast<EEHBindingSet>(Set)), SetObj);
	}
	Root->SetObjectField(TEXT("bindings"), BindingsObj);
	FString Text;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
	if (!FJsonSerializer::Serialize(Root, Writer))
	{
		return false;
	}
	// Write to a temporary file first so an interrupted save never leaves a truncated settings file.
	const FString Path = PathOverride.IsEmpty() ? FilePath() : PathOverride;
	if (!IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path), true))
	{
		return false;
	}
	const FString Temp = Path + TEXT(".tmp");
	return FFileHelper::SaveStringToFile(Text, *Temp) && IFileManager::Get().Move(*Path, *Temp, true, true);
}
