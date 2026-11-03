// Device-level input for the whole game. Reads raw key/gamepad events from Slate (before any widget), keeps
// per-device action state, latches presses so a tap between two simulation ticks is never lost, and turns
// device state into combat InputFrames. Menus read a separate queue of navigation events.
#pragma once

#include "CoreMinimal.h"
#include "EHMatch.h"
#include "EHSettings.h"
#include "Framework/Application/IInputProcessor.h"

enum class EEHDeviceKind : uint8
{
	Keyboard,
	PlayStation,
	Xbox,
	Gamepad,
};

// Device keys: 0 = keyboard set A, 1 = keyboard set B, 100 + id = gamepad with that FInputDeviceId.
constexpr int32 EHDeviceKeyboardA = 0;
constexpr int32 EHDeviceKeyboardB = 1;
constexpr int32 EHDeviceGamepadBase = 100;
constexpr int32 EHDeviceNone = -1;

struct FEHDevice
{
	int32 Key = EHDeviceNone;
	EEHDeviceKind Kind = EEHDeviceKind::Keyboard;
	FString Name;
	bool bConnected = true;
	uint32 Held = 0;          // EEHAction bits, including stick-derived directions
	uint32 KeyHeld = 0;       // EEHAction bits from buttons/keys only
	uint32 StickHeld = 0;     // EEHAction bits from the analog stick
	uint32 SimLatch = 0;      // presses not yet consumed by a simulation tick
	double LastActivity = 0.0;
	EEHBindingSet BindingSet() const;
};

struct FEHNavEvent
{
	int32 Device = EHDeviceNone;
	EEHAction Action = EEHAction::Count;
	bool bRepeat = false;
};

class FEHInputRouter : public IInputProcessor, public TSharedFromThis<FEHInputRouter>
{
public:
	explicit FEHInputRouter(const FEHBindings* InBindings);

	// IInputProcessor
	virtual void Tick(const float DeltaTime, FSlateApplication& SlateApp, TSharedRef<ICursor> Cursor) override;
	virtual bool HandleKeyDownEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent) override;
	virtual bool HandleKeyUpEvent(FSlateApplication& SlateApp, const FKeyEvent& InKeyEvent) override;
	virtual bool HandleAnalogInputEvent(FSlateApplication& SlateApp, const FAnalogInputEvent& InAnalogInputEvent) override;
	virtual const TCHAR* GetDebugName() const override { return TEXT("EbonyHeartsInput"); }

	void Register();
	void Unregister();

	// Combat sample for one tick: directions from held state (opposite directions cancel), presses since the last sample.
	eh::InputFrame SampleForTick(int32 DeviceKey);
	// Drop latched presses (e.g. when a match starts or resumes) so stale menu presses do not become attacks.
	void ClearLatches();

	bool PopNav(FEHNavEvent& Out);
	void ClearNav() { Nav.Reset(); }
	bool IsHeld(int32 DeviceKey, EEHAction Action) const;

	const TMap<int32, FEHDevice>& Devices() const { return DeviceMap; }
	const FEHDevice* FindDevice(int32 DeviceKey) const { return DeviceMap.Find(DeviceKey); }
	int32 MostRecentDevice() const { return LastDevice; }
	EEHDeviceKind KindOf(int32 DeviceKey) const;

	// Rebinding: the next key/button press of a matching device class is captured instead of acting.
	void BeginCapture(EEHBindingSet Set);
	bool IsCapturing() const { return bCapturing; }
	bool TakeCaptured(FKey& OutKey, bool& bOutCancelled);

	// Connection changes since the last call: device key and whether it is now connected.
	bool PopConnectionChange(int32& OutDevice, bool& bOutConnected);

	// Injected input for automated evaluation runs (same path as real devices after the key lookup).
	void InjectAction(int32 DeviceKey, EEHAction Action, bool bDown);

private:
	const FEHBindings* Bindings = nullptr;
	TMap<int32, FEHDevice> DeviceMap;
	TArray<FEHNavEvent> Nav;
	TArray<TPair<int32, bool>> ConnectionChanges;
	int32 LastDevice = EHDeviceKeyboardA;
	bool bRegistered = false;
	bool bCapturing = false;
	EEHBindingSet CaptureSet = EEHBindingSet::KeyboardA;
	FKey CapturedKey;
	bool bCaptureDone = false;
	bool bCaptureCancelled = false;
	FDelegateHandle ConnectionHandle;
	// Menu auto-repeat for held directions.
	TMap<int32, double> RepeatTimers;

	FEHDevice& Touch(int32 DeviceKey, bool bGamepad, FInputDeviceId DeviceId);
	void SetAction(FEHDevice& Device, EEHAction Action, bool bDown, bool bFromStick);
	void OnConnectionChange(EInputDeviceConnectionState State, FPlatformUserId User, FInputDeviceId DeviceId);
	static EEHDeviceKind ClassifyGamepad(const FString& Name);
	static FString GamepadName(FInputDeviceId DeviceId);
};
