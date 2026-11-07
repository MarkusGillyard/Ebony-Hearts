// Device-level input for the whole game. Reads raw key/gamepad events from Slate (before any widget), keeps
// per-device state, latches presses so a tap between two simulation ticks is never lost, and turns device state into
// combat InputFrames. Two maps run side by side on every press: the fixed menu map (EHMenuCommand) feeds a queue of
// menu commands, and the player's remappable gameplay layout feeds combat. So Cross / A confirms in menus and jumps in
// a match, and no remapping can take menu navigation away.
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
	Gamepad,   // controller of unknown make: prompts name buttons by position
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
	uint32 NavHeld = 0;       // EEHNav bits (menu auto-repeat)
	uint32 NavKeyHeld = 0;
	uint32 NavStickHeld = 0;
	uint8 TriggerDown = 0;    // bit 0 left trigger, bit 1 right trigger, as judged from the analog axis
	uint8 DigitalTriggerDown = 0;
	bool bAnalogTriggers = false;   // has reported a trigger axis: the engine's digital trigger presses are ignored
	uint8 DigitalTriggerPresses = 0;   // digital trigger presses seen before any axis (a digital-only controller)
	TArray<FKey> KeysDown;          // gameplay-bound keys held now: an action stays held while any of its keys is down
	double LastActivity = 0.0;
};

// One press: the menu command and/or the gameplay action it produced on its device.
struct FEHNavEvent
{
	int32 Device = EHDeviceNone;
	EEHNav Nav = EEHNav::Count;
	EEHAction Action = EEHAction::Count;
	bool bRepeat = false;
};

class FEHInputRouter : public IInputProcessor, public TSharedFromThis<FEHInputRouter>
{
public:
	// Analog trigger thresholds (fraction of full travel): pressed at TriggerOn, released below TriggerOff.
	static constexpr float TriggerOn = 0.30f;
	static constexpr float TriggerOff = 0.20f;

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
	// Forget held gameplay state, e.g. after the bindings change under a held key.
	void ResetHeld();

	bool PopNav(FEHNavEvent& Out);
	void ClearNav() { Nav.Reset(); }
	bool IsHeld(int32 DeviceKey, EEHAction Action) const;

	const TMap<int32, FEHDevice>& Devices() const { return DeviceMap; }
	const FEHDevice* FindDevice(int32 DeviceKey) const { return DeviceMap.Find(DeviceKey); }
	int32 MostRecentDevice() const { return LastDevice; }
	// The most recently used controller, or EHDeviceNone if none has been used.
	int32 MostRecentGamepad() const { return LastGamepad; }
	EEHDeviceKind KindOf(int32 DeviceKey) const;

	// Which player's controller layout a gamepad uses (0 or 1). Unassigned gamepads use player one's layout.
	void SetGamepadPlayer(int32 DeviceKey, int32 Player);
	void ClearGamepadPlayers();
	// The gameplay layout a device uses right now.
	EEHBindingSet SetFor(int32 DeviceKey) const;

	// Rebinding: the next bindable press of the set's device class is captured instead of acting. Escape or
	// Options / Menu cancels.
	void BeginCapture(EEHBindingSet Set);
	void CancelCapture();
	bool IsCapturing() const { return bCapturing; }
	bool TakeCaptured(FKey& OutKey, bool& bOutCancelled);

	// Connection changes since the last call: device key and whether it is now connected.
	bool PopConnectionChange(int32& OutDevice, bool& bOutConnected);

	// Injected input for automated evaluation runs.
	// A gameplay action only (CPU bots driving a slot).
	void InjectAction(int32 DeviceKey, EEHAction Action, bool bDown);
	// A physical key or button on a device, through the same menu and gameplay maps as real input.
	void InjectKey(int32 DeviceKey, const FKey& Key, bool bDown);
	// An analog axis (stick or trigger) on a gamepad.
	void InjectAnalog(int32 DeviceKey, const FKey& Axis, float Value);
	// Removes a device created by injected input (self-tests), so it never shows up as a real controller.
	void ForgetDevice(int32 DeviceKey);

	static EEHDeviceKind ClassifyGamepad(const FString& Name);

private:
	const FEHBindings* Bindings = nullptr;
	TMap<int32, FEHDevice> DeviceMap;
	TMap<int32, int32> GamepadPlayer;
	TArray<FEHNavEvent> Nav;
	TArray<TPair<int32, bool>> ConnectionChanges;
	int32 LastDevice = EHDeviceKeyboardA;
	int32 LastGamepad = EHDeviceNone;
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
	// Returns true on a new press.
	bool SetAction(FEHDevice& Device, EEHAction Action, bool bDown, bool bFromStick);
	bool SetNav(FEHDevice& Device, EEHNav Command, bool bDown, bool bFromStick);
	void Pressed(FEHDevice& Device, EEHNav Command, EEHAction Action);
	// A key event from the engine (or an injected one): applies the trigger rules, then the capture, then the maps.
	bool OnGamepadKey(FEHDevice& Device, const FKey& Key, bool bDown);
	// A gamepad key on a device, after the trigger rules.
	void ProcessGamepadKey(FEHDevice& Device, const FKey& Key, bool bDown);
	// Held state for an action, given the keys still down on that device.
	bool ActionStillHeld(const FEHDevice& Device, EEHBindingSet Set, EEHAction Action) const;
	void ProcessKeyboardKey(const FKey& Key, bool bDown, int32 OnlyDevice = EHDeviceNone);
	void ProcessAxis(FEHDevice& Device, const FKey& Axis, float Value);
	// The capture swallows the press; returns true if it did.
	bool Capture(const FKey& Key, bool bGamepad);
	void OnConnectionChange(EInputDeviceConnectionState State, FPlatformUserId User, FInputDeviceId DeviceId);
	static FString GamepadName(FInputDeviceId DeviceId);
};
