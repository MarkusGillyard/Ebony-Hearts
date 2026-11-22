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
	case EEHAction::Throw: return TEXT("Throw");
	case EEHAction::Dodge: return TEXT("Dodge");
	case EEHAction::Block: return TEXT("Block");
	case EEHAction::Reset: return TEXT("Reset");
	case EEHAction::Down: return TEXT("Down");
	case EEHAction::FPForward: return TEXT("FPForward");
	case EEHAction::FPBack: return TEXT("FPBack");
	case EEHAction::FPLeft: return TEXT("FPLeft");
	case EEHAction::FPRight: return TEXT("FPRight");
	case EEHAction::FPJump: return TEXT("FPJump");
	case EEHAction::FPCrouch: return TEXT("FPCrouch");
	case EEHAction::FPSprint: return TEXT("FPSprint");
	case EEHAction::FPJab: return TEXT("FPJab");
	case EEHAction::FPStraight: return TEXT("FPStraight");
	case EEHAction::FPShove: return TEXT("FPShove");
	case EEHAction::FPBlock: return TEXT("FPBlock");
	case EEHAction::FPFireball: return TEXT("FPFireball");
	case EEHAction::FPIceWall: return TEXT("FPIceWall");
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
	case EEHAction::Down: return TEXT("Crouch");
	case EEHAction::FPForward: return TEXT("FirstPersonForward");
	case EEHAction::FPBack: return TEXT("FirstPersonBack");
	case EEHAction::FPLeft: return TEXT("FirstPersonLeft");
	case EEHAction::FPRight: return TEXT("FirstPersonRight");
	case EEHAction::FPJump: return TEXT("FirstPersonJump");
	case EEHAction::FPCrouch: return TEXT("FirstPersonCrouch");
	case EEHAction::FPSprint: return TEXT("FirstPersonSprint");
	case EEHAction::FPJab: return TEXT("FirstPersonJab");
	case EEHAction::FPStraight: return TEXT("FirstPersonStraight");
	case EEHAction::FPShove: return TEXT("FirstPersonShove");
	case EEHAction::FPBlock: return TEXT("FirstPersonBlock");
	case EEHAction::FPFireball: return TEXT("FirstPersonFireball");
	case EEHAction::FPIceWall: return TEXT("FirstPersonIceWall");
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
	case EEHAction::Throw: return TEXT("Throw");
	case EEHAction::Dodge: return TEXT("Dodge / Roll");
	case EEHAction::Block: return TEXT("Block (hold)");
	case EEHAction::Reset: return TEXT("Training reset");
	case EEHAction::Down: return TEXT("Crouch (hold)");
	case EEHAction::FPForward: return TEXT("Move forward");
	case EEHAction::FPBack: return TEXT("Move back");
	case EEHAction::FPLeft: return TEXT("Move left");
	case EEHAction::FPRight: return TEXT("Move right");
	case EEHAction::FPJump: return TEXT("Jump");
	case EEHAction::FPCrouch: return TEXT("Crouch");
	case EEHAction::FPSprint: return TEXT("Sprint");
	case EEHAction::FPJab: return TEXT("Jab");
	case EEHAction::FPStraight: return TEXT("Straight");
	case EEHAction::FPShove: return TEXT("Shove");
	case EEHAction::FPBlock: return TEXT("Block (hold)");
	case EEHAction::FPFireball: return TEXT("Fireball");
	case EEHAction::FPIceWall: return TEXT("Ice Wall");
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
	case EEHBindingSet::FPKeyboard: return TEXT("fpKeyboard");
	case EEHBindingSet::FPController: return TEXT("fpController");
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
	case EEHBindingSet::FPKeyboard: return TEXT("Keyboard and mouse");
	case EEHBindingSet::FPController: return TEXT("Controller");
	default: return TEXT("?");
	}
}

TArray<EEHAction> EHActionsFor(EEHBindingSet Set)
{
	using A = EEHAction;
	if (Set == EEHBindingSet::FPKeyboard)
	{
		return {A::FPJab, A::FPStraight, A::FPShove, A::FPBlock, A::FPFireball, A::FPIceWall, A::FPForward, A::FPBack, A::FPLeft, A::FPRight, A::FPJump, A::FPCrouch, A::FPSprint};
	}
	if (Set == EEHBindingSet::FPController)
	{
		// The left stick always moves and the right stick always looks, so only buttons are listed.
		return {A::FPJab, A::FPStraight, A::FPShove, A::FPBlock, A::FPFireball, A::FPIceWall, A::FPJump, A::FPCrouch, A::FPSprint};
	}
	return {A::Light, A::Heavy, A::Dodge, A::Throw, A::Block, A::Special, A::Left, A::Right, A::Jump, A::Down, A::Reset};
}

namespace EHBindingDetail
{
// Sets that share physical keys: both keyboard sides, or a controller layout on its own.
TArray<EEHBindingSet> Context(EEHBindingSet Set)
{
	if (Set == EEHBindingSet::KeyboardA || Set == EEHBindingSet::KeyboardB)
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
	// The usual fighting-game layout (settings version 5): up jumps and down crouches, on the stick, the D-pad or the
	// movement keys; the face buttons are Light, Heavy, Special and Dodge; R2 / RT blocks and L1 / LB throws, as in
	// Mortal Kombat. The layouts before it are in DefaultsV4.
	using S = EEHBindingSet;
	using A = EEHAction;
	Set(S::KeyboardA, A::Left, EKeys::A);
	Set(S::KeyboardA, A::Right, EKeys::D);
	Set(S::KeyboardA, A::Jump, EKeys::W);
	Set(S::KeyboardA, A::Light, EKeys::J, EKeys::Enter);
	Set(S::KeyboardA, A::Heavy, EKeys::K, EKeys::BackSpace);
	Set(S::KeyboardA, A::Special, EKeys::L);
	Set(S::KeyboardA, A::Dodge, EKeys::O);
	Set(S::KeyboardA, A::Block, EKeys::SpaceBar);
	Set(S::KeyboardA, A::Reset, EKeys::R);
	Set(S::KeyboardA, A::Down, EKeys::S);
	Set(S::KeyboardA, A::Throw, EKeys::U);

	Set(S::KeyboardB, A::Left, EKeys::Left);
	Set(S::KeyboardB, A::Right, EKeys::Right);
	Set(S::KeyboardB, A::Jump, EKeys::Up);
	Set(S::KeyboardB, A::Light, EKeys::NumPadOne, EKeys::Comma);
	Set(S::KeyboardB, A::Heavy, EKeys::NumPadTwo, EKeys::Period);
	Set(S::KeyboardB, A::Special, EKeys::NumPadThree, EKeys::Slash);
	Set(S::KeyboardB, A::Dodge, EKeys::NumPadSix, EKeys::Apostrophe);
	Set(S::KeyboardB, A::Block, EKeys::NumPadZero, EKeys::RightShift);
	Set(S::KeyboardB, A::Reset, EKeys::NumPadSeven, EKeys::Hyphen);
	Set(S::KeyboardB, A::Down, EKeys::Down);
	Set(S::KeyboardB, A::Throw, EKeys::NumPadFour, EKeys::M);

	// Controller layout chosen by the creator (MK-style). Unreal names buttons by position, so PlayStation and Xbox
	// match: FaceButton_Left = Square / X, Top = Triangle / Y, Right = Circle / B, Bottom = Cross / A.
	for (S Pad : {S::GamepadP1, S::GamepadP2})
	{
		Set(Pad, A::Left, EKeys::Gamepad_DPad_Left);
		Set(Pad, A::Right, EKeys::Gamepad_DPad_Right);
		Set(Pad, A::Jump, EKeys::Gamepad_DPad_Up);   // the left stick's up also jumps (EHInputRouter)
		Set(Pad, A::Light, EKeys::Gamepad_FaceButton_Left);
		Set(Pad, A::Heavy, EKeys::Gamepad_FaceButton_Top);
		Set(Pad, A::Special, EKeys::Gamepad_FaceButton_Bottom);
		Set(Pad, A::Dodge, EKeys::Gamepad_FaceButton_Right);
		Set(Pad, A::Block, EKeys::Gamepad_RightTrigger);
		Set(Pad, A::Reset, EKeys::Gamepad_Special_Left);
		Set(Pad, A::Down, EKeys::Gamepad_DPad_Down);   // the left stick's down also crouches (EHInputRouter)
		Set(Pad, A::Throw, EKeys::Gamepad_LeftShoulder);
	}

	// First person: the proposed starting layout (2026-11-21). Look is always the mouse or the right
	// stick and movement always the left stick, so neither is a binding.
	Set(S::FPKeyboard, A::FPForward, EKeys::W, EKeys::Up);
	Set(S::FPKeyboard, A::FPBack, EKeys::S, EKeys::Down);
	Set(S::FPKeyboard, A::FPLeft, EKeys::A, EKeys::Left);
	Set(S::FPKeyboard, A::FPRight, EKeys::D, EKeys::Right);
	Set(S::FPKeyboard, A::FPJump, EKeys::SpaceBar);
	Set(S::FPKeyboard, A::FPCrouch, EKeys::LeftControl, EKeys::C);
	Set(S::FPKeyboard, A::FPSprint, EKeys::LeftShift);
	Set(S::FPController, A::FPJump, EKeys::Gamepad_FaceButton_Bottom);
	Set(S::FPController, A::FPCrouch, EKeys::Gamepad_RightThumbstick);
	Set(S::FPController, A::FPSprint, EKeys::Gamepad_LeftThumbstick);
	// Physical techniques (2026-11-21): the right hand holds both punches and the left holds block, so strikes and
	// stick movement mix without moving a thumb.
	Set(S::FPKeyboard, A::FPJab, EKeys::LeftMouseButton);
	Set(S::FPKeyboard, A::FPStraight, EKeys::RightMouseButton);
	Set(S::FPKeyboard, A::FPShove, EKeys::E);
	Set(S::FPKeyboard, A::FPBlock, EKeys::Q);
	Set(S::FPController, A::FPJab, EKeys::Gamepad_RightShoulder);
	Set(S::FPController, A::FPStraight, EKeys::Gamepad_RightTrigger);
	Set(S::FPController, A::FPShove, EKeys::Gamepad_FaceButton_Right);
	Set(S::FPController, A::FPBlock, EKeys::Gamepad_LeftShoulder);
	// Spells (2026-11-21): the left hand holds block and Fireball, so strikes and spells mix on the triggers.
	Set(S::FPKeyboard, A::FPFireball, EKeys::F);
	Set(S::FPKeyboard, A::FPIceWall, EKeys::R);
	Set(S::FPController, A::FPFireball, EKeys::Gamepad_LeftTrigger);
	Set(S::FPController, A::FPIceWall, EKeys::Gamepad_FaceButton_Top);
	return B;
}

FEHBindings FEHBindings::DefaultsV4()
{
	// Versions 3 and 4: Grab's former buttons (EHFormerGrabKey) jumped and L1 / LB also blocked; Special was on R1 / RB
	// and Throw on L2 / LT. Everything else matches the current layout.
	FEHBindings B = Defaults();
	auto Set = [&B](EEHBindingSet S, EEHAction A, const FKey& K0, const FKey& K1 = EKeys::Invalid, const FKey& K2 = EKeys::Invalid) {
		B.Keys[Idx(S)][Idx(A)][0] = K0;
		B.Keys[Idx(S)][Idx(A)][1] = K1;
		B.Keys[Idx(S)][Idx(A)][2] = K2;
	};
	using S = EEHBindingSet;
	using A = EEHAction;
	Set(S::KeyboardA, A::Jump, EKeys::W, EKeys::I);
	Set(S::KeyboardB, A::Jump, EKeys::Up, EKeys::NumPadFive, EKeys::Semicolon);
	for (S Pad : {S::GamepadP1, S::GamepadP2})
	{
		Set(Pad, A::Jump, EKeys::Gamepad_DPad_Up, EKeys::Gamepad_FaceButton_Bottom);
		Set(Pad, A::Special, EKeys::Gamepad_RightShoulder);
		Set(Pad, A::Block, EKeys::Gamepad_RightTrigger, EKeys::Gamepad_LeftShoulder);
		Set(Pad, A::Throw, EKeys::Gamepad_LeftTrigger);
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
	if (Set == EEHBindingSet::FPKeyboard)
	{
		// Mouse buttons are first-person keys. Escape pauses, F10 is kept for the developer panel and the console key
		// opens the console in development builds.
		const bool bMouse = Key == EKeys::LeftMouseButton || Key == EKeys::RightMouseButton || Key == EKeys::MiddleMouseButton ||
			Key == EKeys::ThumbMouseButton || Key == EKeys::ThumbMouseButton2;
		if (bMouse)
		{
			return true;
		}
		return Key.IsValid() && !Key.IsMouseButton() && !Key.IsAxis1D() && !Key.IsAxis2D() && !Key.IsAxis3D() && !Key.IsGamepadKey() &&
			Key != EKeys::Escape && Key != EKeys::F10 && Key != EKeys::Tilde;
	}
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
	TArray<TArray<EEHBindingSet>> Groups = {{EEHBindingSet::KeyboardA, EEHBindingSet::KeyboardB}, {EEHBindingSet::GamepadP1}, {EEHBindingSet::GamepadP2},
		{EEHBindingSet::FPKeyboard}, {EEHBindingSet::FPController}};
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
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EbonyHearts"), TEXT("FirstPersonSettings.json"));
}

FString FEHSettings::SliceFilePath()
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
	MouseSensitivity = FMath::Clamp(MouseSensitivity, 0.01f, 0.5f);
	StickSensitivity = FMath::Clamp(StickSensitivity, 0.3f, 3.0f);
	FieldOfView = FMath::Clamp(FieldOfView, 70, 110);
	StaminaMeter = FMath::Clamp(StaminaMeter, 0, 2);
	if (static_cast<uint8>(PromptStyle) > static_cast<uint8>(EEHPromptStyle::Xbox))
	{
		PromptStyle = EEHPromptStyle::Auto;
	}
}

FEHSettings FEHSettings::Load(FString* OutWarning, const FString& PathOverride)
{
	FEHSettings S;
	FString Text;
	FString Path = PathOverride.IsEmpty() ? FilePath() : PathOverride;
	bool bFromSlice = false;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		// A first launch starts from the 2.5D slice's file when there is one: its display, audio and accessibility
		// values carry over, and that file is only read, never written.
		if (!PathOverride.IsEmpty() || !FFileHelper::LoadFileToString(Text, *SliceFilePath()))
		{
			return S;
		}
		Path = SliceFilePath();
		bFromSlice = true;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		if (!bFromSlice)
		{
			IFileManager::Get().Move(*(Path + TEXT(".bad")), *Path, true, true);
		}
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
	S.LoadedVersion = Version;
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
	auto Float = [&Root](const TCHAR* Name, float& Out) {
		double V = 0;
		if (Root->TryGetNumberField(Name, V)) Out = static_cast<float>(V);
	};
	Float(TEXT("mouseSensitivity"), S.MouseSensitivity);
	Float(TEXT("stickSensitivity"), S.StickSensitivity);
	Bool(TEXT("invertLook"), S.bInvertLook);
	Int(TEXT("fieldOfView"), S.FieldOfView);
	Bool(TEXT("sprintToggle"), S.bSprintToggle);
	Bool(TEXT("crouchToggle"), S.bCrouchToggle);
	Int(TEXT("staminaMeter"), S.StaminaMeter);
	Bool(TEXT("vibration"), S.bVibration);
	S.bImportedFromSlice = bFromSlice;

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
		// Files before version 5 were written against the older layout; whatever they leave out is that layout's, and
		// the version 5 step below moves it to the current one.
		FEHBindings Loaded = Version < 5 ? FEHBindings::DefaultsV4() : FEHBindings::Defaults();
		if (Version < 4)
		{
			// Crouch did not exist and Throw had no buttons of its own: both start unbound and get their defaults
			// below only where those keys are free, so a layout the player made is never overridden.
			for (int32 Set = 0; Set < EHFightSetCount; ++Set)
			{
				for (int32 K = 0; K < EHKeysPerAction; ++K)
				{
					Loaded.Keys[Set][Idx(EEHAction::Down)][K] = EKeys::Invalid;
					Loaded.Keys[Set][Idx(EEHAction::Throw)][K] = EKeys::Invalid;
				}
			}
		}
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
			const FEHBindings New = FEHBindings::DefaultsV4();
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
			for (int32 Set = 0; Set < EHFightSetCount; ++Set)
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
			for (int32 Set = 0; Set < EHFightSetCount; ++Set)
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
				Notes += FString::Printf(TEXT("%sThe old Grab buttons now jump (L1 / LB blocks)."), Notes.IsEmpty() ? TEXT("") : TEXT(" "));
			}
		}
		if (Version < 4)
		{
			// Throw's and Crouch's new defaults go wherever their keys are free. A key the player gave another action
			// stays theirs: the new action is left without that key and the note says what to do.
			const FEHBindings New = FEHBindings::DefaultsV4();
			FString Taken;
			for (int32 Set = 0; Set < EHFightSetCount; ++Set)
			{
				const EEHBindingSet BS = static_cast<EEHBindingSet>(Set);
				for (EEHAction A : {EEHAction::Down, EEHAction::Throw})
				{
					const bool bHadCustom = !Loaded.IsUnbound(BS, A);
					for (int32 K = 0; K < EHKeysPerAction && !bHadCustom; ++K)
					{
						const FKey Key = New.Keys[Set][Idx(A)][K];
						if (!Key.IsValid())
						{
							continue;
						}
						const FEHBindingRef C = Loaded.FindConflict(BS, A, K, Key);
						if (C.IsValid())
						{
							Taken += FString::Printf(TEXT("%s%s (%s) is used by %s"), Taken.IsEmpty() ? TEXT("") : TEXT("; "), *Key.GetDisplayName(false).ToString(), EHActionLabel(A), EHActionLabel(C.Action));
						}
						else
						{
							Loaded.Keys[Set][Idx(A)][K] = Key;
						}
					}
					if (Loaded.IsUnbound(BS, A))
					{
						Taken += FString::Printf(TEXT("%s%s has no button on %s"), Taken.IsEmpty() ? TEXT("") : TEXT("; "), EHActionLabel(A), EHSetLabel(BS));
					}
				}
			}
			Notes += FString::Printf(TEXT("%sNew: Crouch (hold down) and Throw have their own buttons."), Notes.IsEmpty() ? TEXT("") : TEXT(" "));
			if (!Taken.IsEmpty())
			{
				Notes += FString::Printf(TEXT(" Your own keys were kept: %s. Choose one in Settings > Controls."), *Taken);
			}
		}
		if (Version < 5)
		{
			// Version 5 moved to the usual fighting-game layout: jump on up only (Cross / A, I, Numpad 5 and ; stop
			// jumping), Cross / A is Special, L1 / LB throws and R2 / RT alone blocks. An action still on its old default
			// moves to the new one; an action the player changed stays as they made it. A move that would take a button
			// the player kept on another action is undone, and the notice names it.
			const FEHBindings Old = FEHBindings::DefaultsV4();
			const FEHBindings New = FEHBindings::Defaults();
			const FEHBindings Before = Loaded;
			bool bMoved[EHSetCount][EHActionCount] = {};
			bool bAny = false;
			for (int32 Set = 0; Set < EHFightSetCount; ++Set)
			{
				for (int32 A = 0; A < EHActionCount; ++A)
				{
					bool bOnOld = true;
					bool bChanged = false;
					for (int32 K = 0; K < EHKeysPerAction; ++K)
					{
						bOnOld &= Loaded.Keys[Set][A][K] == Old.Keys[Set][A][K];
						bChanged |= Old.Keys[Set][A][K] != New.Keys[Set][A][K];
					}
					if (bOnOld && bChanged)
					{
						for (int32 K = 0; K < EHKeysPerAction; ++K)
						{
							Loaded.Keys[Set][A][K] = New.Keys[Set][A][K];
						}
						bMoved[Set][A] = true;
						bAny = true;
					}
				}
			}
			// Undoing one move can give back a button another move took, so repeat until nothing collides.
			FString Kept;
			for (bool bUndid = true; bUndid;)
			{
				bUndid = false;
				for (int32 Set = 0; Set < EHFightSetCount && !bUndid; ++Set)
				{
					const EEHBindingSet BS = static_cast<EEHBindingSet>(Set);
					for (int32 A = 0; A < EHActionCount && !bUndid; ++A)
					{
						if (!bMoved[Set][A])
						{
							continue;
						}
						for (int32 K = 0; K < EHKeysPerAction; ++K)
						{
							const FKey Key = Loaded.Keys[Set][A][K];
							if (Key.IsValid() && Loaded.FindConflict(BS, static_cast<EEHAction>(A), K, Key).IsValid())
							{
								for (int32 J = 0; J < EHKeysPerAction; ++J)
								{
									Loaded.Keys[Set][A][J] = Before.Keys[Set][A][J];
								}
								bMoved[Set][A] = false;
								bUndid = true;
								Kept += FString::Printf(TEXT("%s%s on %s"), Kept.IsEmpty() ? TEXT("") : TEXT(", "), EHActionLabel(static_cast<EEHAction>(A)), EHSetLabel(BS));
								break;
							}
						}
					}
				}
			}
			if (bAny)
			{
				Notes += FString::Printf(TEXT("%sControls now use the usual fighting-game layout: up jumps; on a controller Cross / A is Special, L1 / LB throws and R2 / RT blocks."), Notes.IsEmpty() ? TEXT("") : TEXT(" "));
			}
			if (!Kept.IsEmpty())
			{
				Notes += FString::Printf(TEXT(" Kept as you had them, because the new button is one of yours: %s."), *Kept);
			}
		}
		if (Version < 7)
		{
			// Version 7 added the physical techniques to the first-person layouts. Their defaults go wherever the key is
			// free; a key the player already gave another action stays theirs, and the technique is left without it.
			FString Taken;
			for (EEHBindingSet BS : {EEHBindingSet::FPKeyboard, EEHBindingSet::FPController})
			{
				for (EEHAction A : {EEHAction::FPJab, EEHAction::FPStraight, EEHAction::FPShove, EEHAction::FPBlock})
				{
					for (int32 K = 0; K < EHKeysPerAction; ++K)
					{
						const FKey Key = Loaded.Keys[Idx(BS)][Idx(A)][K];
						const FEHBindingRef C = Key.IsValid() ? Loaded.FindConflict(BS, A, K, Key) : FEHBindingRef();
						if (C.IsValid() && C.Action != A)
						{
							Loaded.Keys[Idx(BS)][Idx(A)][K] = EKeys::Invalid;
							Taken += FString::Printf(TEXT("%s%s (%s) is used by %s"), Taken.IsEmpty() ? TEXT("") : TEXT("; "), *Key.GetDisplayName(false).ToString(), EHActionLabel(A), EHActionLabel(C.Action));
						}
					}
				}
			}
			if (Version == 6)
			{
				Notes += FString::Printf(TEXT("%sNew: Jab, Straight, Shove and Block have their own buttons."), Notes.IsEmpty() ? TEXT("") : TEXT(" "));
				if (!Taken.IsEmpty())
				{
					Notes += FString::Printf(TEXT(" Your own keys were kept: %s. Choose one in Settings > Controls."), *Taken);
				}
			}
		}
		if (Version < 8)
		{
			// Version 8 added the spells. As with the techniques, a default key the player already uses stays theirs.
			FString Taken;
			for (EEHBindingSet BS : {EEHBindingSet::FPKeyboard, EEHBindingSet::FPController})
			{
				for (EEHAction A : {EEHAction::FPFireball, EEHAction::FPIceWall})
				{
					for (int32 K = 0; K < EHKeysPerAction; ++K)
					{
						const FKey Key = Loaded.Keys[Idx(BS)][Idx(A)][K];
						const FEHBindingRef C = Key.IsValid() ? Loaded.FindConflict(BS, A, K, Key) : FEHBindingRef();
						if (C.IsValid() && C.Action != A)
						{
							Loaded.Keys[Idx(BS)][Idx(A)][K] = EKeys::Invalid;
							Taken += FString::Printf(TEXT("%s%s (%s) is used by %s"), Taken.IsEmpty() ? TEXT("") : TEXT("; "), *Key.GetDisplayName(false).ToString(), EHActionLabel(A), EHActionLabel(C.Action));
						}
					}
				}
			}
			if (Version >= 6)
			{
				Notes += FString::Printf(TEXT("%sNew: Fireball and Ice Wall have their own buttons."), Notes.IsEmpty() ? TEXT("") : TEXT(" "));
				if (!Taken.IsEmpty())
				{
					Notes += FString::Printf(TEXT(" Your own keys were kept: %s. Choose one in Settings > Controls."), *Taken);
				}
			}
		}
		// A layout with a duplicate or reserved key falls back to its defaults; the others are kept.
		for (EEHBindingSet Set : {EEHBindingSet::KeyboardA, EEHBindingSet::GamepadP1, EEHBindingSet::GamepadP2, EEHBindingSet::FPKeyboard, EEHBindingSet::FPController})
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
	if (bFromSlice)
	{
		// The slice's controls notices are about its own layouts, which first person does not use.
		Notes = TEXT("Display, audio and accessibility settings carried over from the 2.5D slice.");
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
	Root->SetNumberField(TEXT("version"), EHSettingsVersion);
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
	Root->SetNumberField(TEXT("mouseSensitivity"), MouseSensitivity);
	Root->SetNumberField(TEXT("stickSensitivity"), StickSensitivity);
	Root->SetBoolField(TEXT("invertLook"), bInvertLook);
	Root->SetNumberField(TEXT("fieldOfView"), FieldOfView);
	Root->SetBoolField(TEXT("sprintToggle"), bSprintToggle);
	Root->SetBoolField(TEXT("crouchToggle"), bCrouchToggle);
	Root->SetNumberField(TEXT("staminaMeter"), StaminaMeter);
	Root->SetBoolField(TEXT("vibration"), bVibration);
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
