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
uint32 Bit(EEHNav N) { return 1u << static_cast<uint32>(N); }
int32 RepeatKey(int32 Device, EEHNav N) { return Device * 64 + static_cast<int32>(N); }
bool IsTriggerKey(const FKey& K) { return K == EKeys::Gamepad_LeftTrigger || K == EKeys::Gamepad_RightTrigger; }
}
using namespace EHInputDetail;

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
	// Names come from SDL's controller database on Linux ("PS4 Controller", "Xbox 360 Controller", ...).
	const FString N = Name.ToLower();
	if (N.Contains(TEXT("ps3")) || N.Contains(TEXT("ps4")) || N.Contains(TEXT("ps5")) || N.Contains(TEXT("dualshock")) || N.Contains(TEXT("dualsense")) ||
		N.Contains(TEXT("playstation")) || N.Contains(TEXT("sony")) || N == TEXT("wireless controller"))
	{
		return EEHDeviceKind::PlayStation;
	}
	if (N.Contains(TEXT("xbox")) || N.Contains(TEXT("x-box")) || N.Contains(TEXT("xinput")) || N.Contains(TEXT("x360")))
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
			D.Name = FString::Printf(TEXT("Controller %d"), DeviceKey - EHDeviceGamepadBase);
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

void FEHInputRouter::SetGamepadPlayer(int32 DeviceKey, int32 Player)
{
	if (DeviceKey < EHDeviceGamepadBase)
	{
		return;
	}
	const int32 Before = GamepadPlayer.FindRef(DeviceKey);
	GamepadPlayer.Add(DeviceKey, Player);
	if (Before != Player)
	{
		// Held buttons were looked up in the old layout; drop them so a release cannot be missed.
		if (FEHDevice* D = DeviceMap.Find(DeviceKey))
		{
			D->Held = D->KeyHeld = D->StickHeld = D->SimLatch = 0;
			D->KeysDown.Reset();
		}
	}
}

void FEHInputRouter::ClearGamepadPlayers()
{
	for (const TPair<int32, int32>& Pair : GamepadPlayer)
	{
		if (Pair.Value != 0)
		{
			if (FEHDevice* D = DeviceMap.Find(Pair.Key))
			{
				D->Held = D->KeyHeld = D->StickHeld = D->SimLatch = 0;
				D->KeysDown.Reset();
			}
		}
	}
	GamepadPlayer.Reset();
}

EEHBindingSet FEHInputRouter::SetFor(int32 DeviceKey) const
{
	if (DeviceKey == EHDeviceKeyboardA) return EEHBindingSet::KeyboardA;
	if (DeviceKey == EHDeviceKeyboardB) return EEHBindingSet::KeyboardB;
	return GamepadPlayer.FindRef(DeviceKey) == 1 ? EEHBindingSet::GamepadP2 : EEHBindingSet::GamepadP1;
}

bool FEHInputRouter::SetAction(FEHDevice& Device, EEHAction Action, bool bDown, bool bFromStick)
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
		return true;
	}
	return false;
}

bool FEHInputRouter::SetNav(FEHDevice& Device, EEHNav Command, bool bDown, bool bFromStick)
{
	const uint32 B = Bit(Command);
	const uint32 Before = Device.NavHeld;
	if (bFromStick)
	{
		Device.NavStickHeld = bDown ? (Device.NavStickHeld | B) : (Device.NavStickHeld & ~B);
	}
	else
	{
		Device.NavKeyHeld = bDown ? (Device.NavKeyHeld | B) : (Device.NavKeyHeld & ~B);
	}
	Device.NavHeld = Device.NavKeyHeld | Device.NavStickHeld;
	if (bDown && (Before & B) == 0)
	{
		RepeatTimers.Add(RepeatKey(Device.Key, Command), FPlatformTime::Seconds() + RepeatDelay);
		return true;
	}
	return false;
}

void FEHInputRouter::Pressed(FEHDevice& Device, EEHNav Command, EEHAction Action)
{
	Device.LastActivity = FPlatformTime::Seconds();
	LastDevice = Device.Key;
	if (Device.Key >= EHDeviceGamepadBase)
	{
		LastGamepad = Device.Key;
	}
	Nav.Add(FEHNavEvent{Device.Key, Command, Action, false});
}

bool FEHInputRouter::Capture(const FKey& Key, bool bGamepad)
{
	if (!bCapturing)
	{
		return false;
	}
	if (Key == EKeys::Escape || Key == EKeys::Gamepad_Special_Right)
	{
		bCaptureCancelled = true;
		bCaptureDone = true;
		bCapturing = false;
		return true;
	}
	const bool bWantGamepad = !EHIsKeyboardSet(CaptureSet);
	if (bGamepad == bWantGamepad && FEHBindings::IsBindable(CaptureSet, Key))
	{
		CapturedKey = Key;
		bCaptureCancelled = false;
		bCaptureDone = true;
		bCapturing = false;
	}
	return true;   // every press is swallowed while capturing, bindable or not
}

void FEHInputRouter::ProcessGamepadKey(FEHDevice& D, const FKey& Key, bool bDown)
{
	if (Bindings == nullptr)
	{
		return;
	}
	const EEHBindingSet Set = SetFor(D.Key);
	const EEHNav Command = EHMenuCommand(EEHBindingSet::GamepadP1, Key);
	const EEHAction Action = Bindings->Find(Set, Key);
	const bool bNewNav = Command != EEHNav::Count && SetNav(D, Command, bDown, false);
	bool bNewAction = false;
	if (Action != EEHAction::Count)
	{
		if (bDown)
		{
			D.KeysDown.AddUnique(Key);
		}
		else
		{
			D.KeysDown.Remove(Key);
		}
		bNewAction = SetAction(D, Action, bDown || ActionStillHeld(D, Set, Action), false);
	}
	if (bNewNav || bNewAction)
	{
		Pressed(D, bNewNav ? Command : EEHNav::Count, bNewAction ? Action : EEHAction::Count);
	}
	else if (bDown)
	{
		// Unbound keys (including stick directions Slate synthesizes from analog drift) keep the device alive but do
		// not take over prompts or menus from the device the player is actually using.
		D.LastActivity = FPlatformTime::Seconds();
	}
}

bool FEHInputRouter::OnGamepadKey(FEHDevice& D, const FKey& Key, bool bDown)
{
	if (IsTriggerKey(Key))
	{
		// Controllers report the trigger axis, and the engine adds its own digital press at a different threshold,
		// sometimes before the first axis event. The axis alone decides, so one squeeze is exactly one press. Only a
		// controller that keeps sending digital presses without ever reporting an axis falls back to them.
		const uint8 B = Key == EKeys::Gamepad_LeftTrigger ? 1 : 2;
		const bool bWasDown = (D.DigitalTriggerDown & B) != 0;
		D.DigitalTriggerDown = bDown ? (D.DigitalTriggerDown | B) : (D.DigitalTriggerDown & ~B);
		if (bDown && !bWasDown && !D.bAnalogTriggers && D.DigitalTriggerPresses < 255)
		{
			++D.DigitalTriggerPresses;
		}
		if (D.bAnalogTriggers || D.DigitalTriggerPresses < 3)
		{
			return bCapturing;
		}
	}
	if (bDown && Capture(Key, true))
	{
		return true;
	}
	ProcessGamepadKey(D, Key, bDown);
	return false;
}

bool FEHInputRouter::ActionStillHeld(const FEHDevice& D, EEHBindingSet Set, EEHAction Action) const
{
	for (const FKey& K : D.KeysDown)
	{
		if (Bindings->Find(Set, K) == Action)
		{
			return true;
		}
	}
	return false;
}

void FEHInputRouter::ProcessKeyboardKey(const FKey& Key, bool bDown, int32 OnlyDevice)
{
	if (Bindings == nullptr)
	{
		return;
	}
	for (int32 DeviceKey : {EHDeviceKeyboardA, EHDeviceKeyboardB})
	{
		if (OnlyDevice != EHDeviceNone && DeviceKey != OnlyDevice)
		{
			continue;
		}
		const EEHBindingSet Set = DeviceKey == EHDeviceKeyboardA ? EEHBindingSet::KeyboardA : EEHBindingSet::KeyboardB;
		FEHDevice& D = DeviceMap.FindChecked(DeviceKey);
		const EEHNav Command = EHMenuCommand(Set, Key);
		const EEHAction Action = Bindings->Find(Set, Key);
		const bool bNewNav = Command != EEHNav::Count && SetNav(D, Command, bDown, false);
		bool bNewAction = false;
		if (Action != EEHAction::Count)
		{
			if (bDown)
			{
				D.KeysDown.AddUnique(Key);
			}
			else
			{
				D.KeysDown.Remove(Key);
			}
			bNewAction = SetAction(D, Action, bDown || ActionStillHeld(D, Set, Action), false);
		}
		if (bNewNav || bNewAction)
		{
			Pressed(D, bNewNav ? Command : EEHNav::Count, bNewAction ? Action : EEHAction::Count);
		}
	}
}

bool FEHInputRouter::HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	const bool bGamepad = Key.IsGamepadKey();
	if (InKeyEvent.IsRepeat())
	{
		return bCapturing;
	}
	if (bGamepad)
	{
		FEHDevice& D = Touch(EHDeviceGamepadBase + InKeyEvent.GetInputDeviceId().GetId(), true, InKeyEvent.GetInputDeviceId());
		return OnGamepadKey(D, Key, true);
	}
	if (Capture(Key, false))
	{
		return true;
	}
	ProcessKeyboardKey(Key, true);
	return false;
}

bool FEHInputRouter::HandleKeyUpEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent)
{
	const FKey Key = InKeyEvent.GetKey();
	if (Key.IsGamepadKey())
	{
		if (FEHDevice* D = DeviceMap.Find(EHDeviceGamepadBase + InKeyEvent.GetInputDeviceId().GetId()))
		{
			OnGamepadKey(*D, Key, false);
		}
		return false;
	}
	ProcessKeyboardKey(Key, false);
	return false;
}

void FEHInputRouter::ProcessAxis(FEHDevice& D, const FKey& Axis, float V)
{
	if (Axis == EKeys::Gamepad_LeftTriggerAxis || Axis == EKeys::Gamepad_RightTriggerAxis)
	{
		const uint8 B = Axis == EKeys::Gamepad_LeftTriggerAxis ? 1 : 2;
		if (!D.bAnalogTriggers)
		{
			// Switching to the axis. Only a digital-only fallback can have reported a press; the axis releases it later.
			D.bAnalogTriggers = true;
			D.TriggerDown = D.DigitalTriggerPresses >= 3 ? D.DigitalTriggerDown : 0;
		}
		const bool bWas = (D.TriggerDown & B) != 0;
		const bool bNow = bWas ? V > TriggerOff : V >= TriggerOn;
		if (bNow == bWas)
		{
			return;
		}
		D.TriggerDown = bNow ? (D.TriggerDown | B) : (D.TriggerDown & ~B);
		const FKey Key = B == 1 ? EKeys::Gamepad_LeftTrigger : EKeys::Gamepad_RightTrigger;
		if (bNow && Capture(Key, true))
		{
			return;
		}
		ProcessGamepadKey(D, Key, bNow);
		return;
	}
	if (Axis != EKeys::Gamepad_LeftX && Axis != EKeys::Gamepad_LeftY)
	{
		return;
	}
	// The left stick always moves (left/right) and navigates menus (all four directions). Hysteresis keeps a resting
	// stick from chattering between states.
	const bool bX = Axis == EKeys::Gamepad_LeftX;
	const EEHNav NavNeg = bX ? EEHNav::Left : EEHNav::Down;
	const EEHNav NavPos = bX ? EEHNav::Right : EEHNav::Up;
	const bool NegHeld = (D.NavStickHeld & Bit(NavNeg)) != 0;
	const bool PosHeld = (D.NavStickHeld & Bit(NavPos)) != 0;
	const bool bNeg = NegHeld ? V < -StickOff : V < -StickOn;
	const bool bPos = PosHeld ? V > StickOff : V > StickOn;
	for (int32 i = 0; i < 2; ++i)
	{
		const EEHNav Command = i == 0 ? NavNeg : NavPos;
		const bool bDown = i == 0 ? bNeg : bPos;
		const bool bNewNav = SetNav(D, Command, bDown, true);
		bool bNewAction = false;
		EEHAction Action = EEHAction::Count;
		if (bX)
		{
			Action = i == 0 ? EEHAction::Left : EEHAction::Right;
			bNewAction = SetAction(D, Action, bDown, true);
		}
		if (bNewNav || bNewAction)
		{
			Pressed(D, bNewNav ? Command : EEHNav::Count, bNewAction ? Action : EEHAction::Count);
		}
	}
}

bool FEHInputRouter::HandleAnalogInputEvent(FSlateApplication& SlateApp, const FAnalogInputEvent& InAnalogInputEvent)
{
	const FKey Key = InAnalogInputEvent.GetKey();
	if (Key != EKeys::Gamepad_LeftX && Key != EKeys::Gamepad_LeftY && Key != EKeys::Gamepad_LeftTriggerAxis && Key != EKeys::Gamepad_RightTriggerAxis)
	{
		return false;
	}
	FEHDevice& D = Touch(EHDeviceGamepadBase + InAnalogInputEvent.GetInputDeviceId().GetId(), true, InAnalogInputEvent.GetInputDeviceId());
	ProcessAxis(D, Key, InAnalogInputEvent.GetAnalogValue());
	return false;
}

void FEHInputRouter::Tick(const float DeltaTime, FSlateApplication& SlateApp, TSharedRef<ICursor> Cursor)
{
	// Menu auto-repeat for held directions only.
	const double Now = FPlatformTime::Seconds();
	for (auto& Pair : DeviceMap)
	{
		FEHDevice& D = Pair.Value;
		for (EEHNav N : {EEHNav::Up, EEHNav::Down, EEHNav::Left, EEHNav::Right})
		{
			if ((D.NavHeld & Bit(N)) == 0)
			{
				continue;
			}
			double& Next = RepeatTimers.FindOrAdd(RepeatKey(D.Key, N), Now + RepeatDelay);
			if (Now >= Next)
			{
				Nav.Add(FEHNavEvent{D.Key, N, EEHAction::Count, true});
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

void FEHInputRouter::ResetHeld()
{
	for (auto& Pair : DeviceMap)
	{
		FEHDevice& D = Pair.Value;
		D.KeyHeld = D.SimLatch = 0;
		D.Held = D.StickHeld;
		D.KeysDown.Reset();
	}
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

void FEHInputRouter::CancelCapture()
{
	if (bCapturing)
	{
		bCapturing = false;
		bCaptureCancelled = true;
		bCaptureDone = true;
	}
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
		D->Held = D->KeyHeld = D->StickHeld = D->SimLatch = 0;
		D->NavHeld = D->NavKeyHeld = D->NavStickHeld = 0;
		D->TriggerDown = D->DigitalTriggerDown = 0;
		D->KeysDown.Reset();
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

void FEHInputRouter::InjectKey(int32 DeviceKey, const FKey& Key, bool bDown)
{
	if (DeviceKey < EHDeviceGamepadBase)
	{
		if (!(bDown && Capture(Key, false)))
		{
			ProcessKeyboardKey(Key, bDown, DeviceKey);
		}
		return;
	}
	FEHDevice& D = Touch(DeviceKey, true, FInputDeviceId::CreateFromInternalId(DeviceKey - EHDeviceGamepadBase));
	OnGamepadKey(D, Key, bDown);
}

void FEHInputRouter::InjectAnalog(int32 DeviceKey, const FKey& Axis, float Value)
{
	FEHDevice& D = Touch(DeviceKey, true, FInputDeviceId::CreateFromInternalId(DeviceKey - EHDeviceGamepadBase));
	ProcessAxis(D, Axis, Value);
}

void FEHInputRouter::ForgetDevice(int32 DeviceKey)
{
	DeviceMap.Remove(DeviceKey);
	GamepadPlayer.Remove(DeviceKey);
	if (LastGamepad == DeviceKey)
	{
		LastGamepad = EHDeviceNone;
	}
	if (LastDevice == DeviceKey)
	{
		LastDevice = EHDeviceKeyboardA;
	}
	Nav.RemoveAll([DeviceKey](const FEHNavEvent& E) { return E.Device == DeviceKey; });
}
