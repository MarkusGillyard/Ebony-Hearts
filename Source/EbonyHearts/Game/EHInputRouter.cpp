#include "EHInputRouter.h"

#include "Framework/Application/SlateApplication.h"
#include "GenericPlatform/GenericPlatformInputDeviceMapper.h"
#include "GenericPlatform/InputDeviceRegistry.h"
#include "HAL/PlatformTime.h"

namespace EHInputDetail
{
constexpr float StickOn = 0.55f;
constexpr float StickOff = 0.40f;
constexpr double RepeatDelay = 0.38;
constexpr double RepeatInterval = 0.085;

uint32 Bit(EEHAction A) { return 1u << static_cast<uint32>(A); }
}
using namespace EHInputDetail;

EEHBindingSet FEHDevice::BindingSet() const
{
	if (Key == EHDeviceKeyboardA) return EEHBindingSet::KeyboardA;
	if (Key == EHDeviceKeyboardB) return EEHBindingSet::KeyboardB;
	return EEHBindingSet::Gamepad;
}

FEHInputRouter::FEHInputRouter(const FEHBindings* InBindings)
	: Bindings(InBindings)
{
	FEHDevice A;
	A.Key = EHDeviceKeyboardA;
	A.Kind = EEHDeviceKind::Keyboard;
	A.Name = TEXT("Keyboard (left)");
	DeviceMap.Add(A.Key, A);
	FEHDevice B = A;
	B.Key = EHDeviceKeyboardB;
	B.Name = TEXT("Keyboard (right)");
	DeviceMap.Add(B.Key, B);
}

void FEHInputRouter::Register()
{
	if (!bRegistered && FSlateApplication::IsInitialized())
	{
		// Index 0 runs before Slate widgets and other processors, so menus and combat never miss input.
		FSlateApplication::Get().RegisterInputPreProcessor(AsShared(), 0);
		ConnectionHandle = IPlatformInputDeviceMapper::Get().GetOnInputDeviceConnectionChange().AddRaw(this, &FEHInputRouter::OnConnectionChange);
		bRegistered = true;
		// Devices already present at startup.
		TArray<FInputDeviceId> Existing;
		IPlatformInputDeviceMapper::Get().GetAllConnectedInputDevices(Existing);
		for (const FInputDeviceId Id : Existing)
		{
			const FString Name = GamepadName(Id);
			if (!Name.IsEmpty())
			{
				Touch(EHDeviceGamepadBase + Id.GetId(), true, Id);
			}
		}
	}
}

void FEHInputRouter::Unregister()
{
	if (bRegistered && FSlateApplication::IsInitialized())
	{
		FSlateApplication::Get().UnregisterInputPreProcessor(AsShared());
		IPlatformInputDeviceMapper::Get().GetOnInputDeviceConnectionChange().Remove(ConnectionHandle);
	}
	bRegistered = false;
}

FString FEHInputRouter::GamepadName(FInputDeviceId DeviceId)
{
	const TOptional<FInputDeviceDescriptor> Desc = FInputDeviceRegistry::FindDescriptor(DeviceId);
	if (Desc.IsSet() && !Desc->HardwareDeviceIdentifier.IsNone())
	{
		return Desc->HardwareDeviceIdentifier.ToString();
	}
	return FString();
}

EEHDeviceKind FEHInputRouter::ClassifyGamepad(const FString& Name)
{
	const FString N = Name.ToLower();
	if (N.Contains(TEXT("ps3")) || N.Contains(TEXT("ps4")) || N.Contains(TEXT("ps5")) || N.Contains(TEXT("dualshock")) || N.Contains(TEXT("dualsense")) ||
		N.Contains(TEXT("playstation")) || N.Contains(TEXT("sony")) || N == TEXT("wireless controller"))
	{
		return EEHDeviceKind::PlayStation;
	}
	if (N.Contains(TEXT("xbox")) || N.Contains(TEXT("x-box")) || N.Contains(TEXT("xinput")))
	{
		return EEHDeviceKind::Xbox;
	}
	return EEHDeviceKind::Gamepad;
}

FEHDevice& FEHInputRouter::Touch(int32 DeviceKey, bool bGamepad, FInputDeviceId DeviceId)
{
	FEHDevice* Existing = DeviceMap.Find(DeviceKey);
	if (Existing == nullptr)
	{
		FEHDevice D;
		D.Key = DeviceKey;
		D.Name = GamepadName(DeviceId);
		if (D.Name.IsEmpty())
		{
			D.Name = FString::Printf(TEXT("Controller %d"), DeviceId.GetId());
		}
		D.Kind = bGamepad ? ClassifyGamepad(D.Name) : EEHDeviceKind::Keyboard;
		Existing = &DeviceMap.Add(DeviceKey, D);
	}
	Existing->bConnected = true;
	return *Existing;
}

EEHDeviceKind FEHInputRouter::KindOf(int32 DeviceKey) const
{
	const FEHDevice* D = DeviceMap.Find(DeviceKey);
	return D ? D->Kind : EEHDeviceKind::Keyboard;
}

void FEHInputRouter::SetAction(FEHDevice& Device, EEHAction Action, bool bDown, bool bFromStick)
{
	const uint32 B = Bit(Action);
	const uint32 Before = Device.Held;
	if (bFromStick)
	{
		Device.StickHeld = bDown ? (Device.StickHeld | B) : (Device.StickHeld & ~B);
	}
	else
	{
		Device.KeyHeld = bDown ? (Device.KeyHeld | B) : (Device.KeyHeld & ~B);
	}
	Device.Held = Device.KeyHeld | Device.StickHeld;
	if (bDown && (Before & B) == 0)
	{
		Device.SimLatch |= B;
		Device.LastActivity = FPlatformTime::Seconds();
		LastDevice = Device.Key;
		Nav.Add(FEHNavEvent{Device.Key, Action, false});
		RepeatTimers.Add(Device.Key * 64 + static_cast<int32>(Action), FPlatformTime::Seconds() + RepeatDelay);
	}
}

bool FEHInputRouter::HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	const bool bGamepad = Key.IsGamepadKey();
	if (bCapturing)
	{
		if (InKeyEvent.IsRepeat())
		{
			return true;
		}
		if (Key == EKeys::Escape || Key == EKeys::Gamepad_Special_Right)
		{
			bCaptureCancelled = true;
			bCaptureDone = true;
			bCapturing = false;
			return true;
		}
		const bool bWantGamepad = CaptureSet == EEHBindingSet::Gamepad;
		if (bGamepad == bWantGamepad && !Key.IsMouseButton() && !Key.IsAnalog())
		{
			CapturedKey = Key;
			bCaptureCancelled = false;
			bCaptureDone = true;
			bCapturing = false;
		}
		return true;
	}
	if (InKeyEvent.IsRepeat() || Bindings == nullptr)
	{
		return false;
	}
	if (bGamepad)
	{
		const int32 DeviceKey = EHDeviceGamepadBase + InKeyEvent.GetInputDeviceId().GetId();
		FEHDevice& D = Touch(DeviceKey, true, InKeyEvent.GetInputDeviceId());
		const EEHAction A = Bindings->Find(EEHBindingSet::Gamepad, Key);
		if (A != EEHAction::Count)
		{
			SetAction(D, A, true, false);
		}
		else
		{
			// Unbound keys (including the stick directions Slate synthesizes from analog drift) keep the device alive
			// but do not take over prompts or menus from the device the player is actually using.
			D.LastActivity = FPlatformTime::Seconds();
		}
		return false;
	}
	for (int32 DeviceKey : {EHDeviceKeyboardA, EHDeviceKeyboardB})
	{
		const EEHAction A = Bindings->Find(DeviceKey == EHDeviceKeyboardA ? EEHBindingSet::KeyboardA : EEHBindingSet::KeyboardB, Key);
		if (A != EEHAction::Count)
		{
			SetAction(DeviceMap.FindChecked(DeviceKey), A, true, false);
			return false;
		}
	}
	return false;
}

bool FEHInputRouter::HandleKeyUpEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent)
{
	if (Bindings == nullptr)
	{
		return false;
	}
	const FKey Key = InKeyEvent.GetKey();
	if (Key.IsGamepadKey())
	{
		const int32 DeviceKey = EHDeviceGamepadBase + InKeyEvent.GetInputDeviceId().GetId();
		if (FEHDevice* D = DeviceMap.Find(DeviceKey))
		{
			const EEHAction A = Bindings->Find(EEHBindingSet::Gamepad, Key);
			if (A != EEHAction::Count)
			{
				SetAction(*D, A, false, false);
			}
		}
		return false;
	}
	for (int32 DeviceKey : {EHDeviceKeyboardA, EHDeviceKeyboardB})
	{
		const EEHAction A = Bindings->Find(DeviceKey == EHDeviceKeyboardA ? EEHBindingSet::KeyboardA : EEHBindingSet::KeyboardB, Key);
		if (A != EEHAction::Count)
		{
			SetAction(DeviceMap.FindChecked(DeviceKey), A, false, false);
		}
	}
	return false;
}

bool FEHInputRouter::HandleAnalogInputEvent(FSlateApplication& SlateApp, const FAnalogInputEvent& InAnalogInputEvent)
{
	const FKey Key = InAnalogInputEvent.GetKey();
	if (Key != EKeys::Gamepad_LeftX && Key != EKeys::Gamepad_LeftY)
	{
		return false;
	}
	const int32 DeviceKey = EHDeviceGamepadBase + InAnalogInputEvent.GetInputDeviceId().GetId();
	FEHDevice& D = Touch(DeviceKey, true, InAnalogInputEvent.GetInputDeviceId());
	const float V = InAnalogInputEvent.GetAnalogValue();
	const EEHAction Neg = (Key == EKeys::Gamepad_LeftX) ? EEHAction::Left : EEHAction::Down;
	const EEHAction Pos = (Key == EKeys::Gamepad_LeftX) ? EEHAction::Right : EEHAction::Up;
	// Hysteresis keeps a resting stick from chattering between states.
	const bool NegHeld = (D.StickHeld & Bit(Neg)) != 0;
	const bool PosHeld = (D.StickHeld & Bit(Pos)) != 0;
	SetAction(D, Neg, NegHeld ? V < -StickOff : V < -StickOn, true);
	SetAction(D, Pos, PosHeld ? V > StickOff : V > StickOn, true);
	return false;
}

void FEHInputRouter::Tick(const float DeltaTime, FSlateApplication& SlateApp, TSharedRef<ICursor> Cursor)
{
	// Menu auto-repeat for held directions only.
	const double Now = FPlatformTime::Seconds();
	for (auto& Pair : DeviceMap)
	{
		FEHDevice& D = Pair.Value;
		for (EEHAction A : {EEHAction::Up, EEHAction::Down, EEHAction::Left, EEHAction::Right})
		{
			if ((D.Held & Bit(A)) == 0)
			{
				continue;
			}
			double& Next = RepeatTimers.FindOrAdd(D.Key * 64 + static_cast<int32>(A), Now + RepeatDelay);
			if (Now >= Next)
			{
				Nav.Add(FEHNavEvent{D.Key, A, true});
				Next = Now + RepeatInterval;
			}
		}
	}
}

eh::InputFrame FEHInputRouter::SampleForTick(int32 DeviceKey)
{
	eh::InputFrame F;
	FEHDevice* D = DeviceMap.Find(DeviceKey);
	if (D == nullptr || !D->bConnected)
	{
		return F;
	}
	const bool L = (D->Held & Bit(EEHAction::Left)) != 0;
	const bool R = (D->Held & Bit(EEHAction::Right)) != 0;
	F.x = static_cast<int8_t>((R ? 1 : 0) - (L ? 1 : 0));
	auto Map = [](uint32 Bits) {
		uint8 Out = 0;
		if (Bits & Bit(EEHAction::Light)) Out |= eh::BtnLight;
		if (Bits & Bit(EEHAction::Heavy)) Out |= eh::BtnHeavy;
		if (Bits & Bit(EEHAction::Special)) Out |= eh::BtnSpecial;
		if (Bits & Bit(EEHAction::Throw)) Out |= eh::BtnThrow;
		if (Bits & Bit(EEHAction::Dodge)) Out |= eh::BtnDodge;
		if (Bits & Bit(EEHAction::Block)) Out |= eh::BtnBlock;
		return Out;
	};
	F.pressed = Map(D->SimLatch);
	F.held = static_cast<uint8_t>(Map(D->Held) | F.pressed);
	D->SimLatch = 0;
	return F;
}

void FEHInputRouter::ClearLatches()
{
	for (auto& Pair : DeviceMap)
	{
		Pair.Value.SimLatch = 0;
	}
	Nav.Reset();
}

bool FEHInputRouter::PopNav(FEHNavEvent& Out)
{
	if (Nav.Num() == 0)
	{
		return false;
	}
	Out = Nav[0];
	Nav.RemoveAt(0);
	return true;
}

bool FEHInputRouter::IsHeld(int32 DeviceKey, EEHAction Action) const
{
	const FEHDevice* D = DeviceMap.Find(DeviceKey);
	return D && (D->Held & Bit(Action)) != 0;
}

void FEHInputRouter::BeginCapture(EEHBindingSet Set)
{
	bCapturing = true;
	bCaptureDone = false;
	bCaptureCancelled = false;
	CaptureSet = Set;
	CapturedKey = EKeys::Invalid;
}

bool FEHInputRouter::TakeCaptured(FKey& OutKey, bool& bOutCancelled)
{
	if (!bCaptureDone)
	{
		return false;
	}
	bCaptureDone = false;
	OutKey = CapturedKey;
	bOutCancelled = bCaptureCancelled;
	// The capturing press must not also act on the menu or a match.
	for (auto& Pair : DeviceMap)
	{
		Pair.Value.SimLatch = 0;
	}
	Nav.Reset();
	return true;
}

void FEHInputRouter::OnConnectionChange(EInputDeviceConnectionState State, FPlatformUserId User, FInputDeviceId DeviceId)
{
	const int32 DeviceKey = EHDeviceGamepadBase + DeviceId.GetId();
	const bool bConnected = State == EInputDeviceConnectionState::Connected;
	if (bConnected)
	{
		FEHDevice& D = Touch(DeviceKey, true, DeviceId);
		const FString Name = GamepadName(DeviceId);
		if (!Name.IsEmpty())
		{
			D.Name = Name;
			D.Kind = ClassifyGamepad(Name);
		}
	}
	else if (FEHDevice* D = DeviceMap.Find(DeviceKey))
	{
		D->bConnected = false;
		D->Held = D->KeyHeld = D->StickHeld = 0;
		D->SimLatch = 0;
	}
	ConnectionChanges.Add(TPair<int32, bool>(DeviceKey, bConnected));
}

bool FEHInputRouter::PopConnectionChange(int32& OutDevice, bool& bOutConnected)
{
	if (ConnectionChanges.Num() == 0)
	{
		return false;
	}
	OutDevice = ConnectionChanges[0].Key;
	bOutConnected = ConnectionChanges[0].Value;
	ConnectionChanges.RemoveAt(0);
	return true;
}

void FEHInputRouter::InjectAction(int32 DeviceKey, EEHAction Action, bool bDown)
{
	if (FEHDevice* D = DeviceMap.Find(DeviceKey))
	{
		SetAction(*D, Action, bDown, false);
	}
}
