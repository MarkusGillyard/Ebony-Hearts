// Owns the whole player journey: menus, character select, matches (versus CPU, local versus, training and the
// interactive lesson), results, settings and quit. Steps the combat simulation at a fixed 60 Hz from real time and
// turns its events into presentation (animation, effects, sound, camera, HUD).
#pragma once

#include "CoreMinimal.h"
#include "EHAI.h"
#include "EHAudio.h"
#include "EHClock.h"
#include "EHCombatData.h"
#include "EHInputRouter.h"
#include "EHMatch.h"
#include "EHPresentation.h"
#include "EHSettings.h"
#include "EHUICanvas.h"
#include "GameFramework/Actor.h"
#include "GenericPlatform/GenericApplication.h"
#include "GenericPlatform/GenericWindow.h"

#include "EHGameDirector.generated.h"

class ACameraActor;
class AEHFighterVisual;
class AEHVfx;
class UTexture2D;

// Where the game window sits relative to the monitor it is on.
struct FEHWindowFit
{
	FPlatformRect Window;
	FPlatformRect Monitor;
	FPlatformRect WorkArea;
	EWindowMode::Type Mode = EWindowMode::Windowed;
	bool bCoversMonitor = false;
};

// Move id string for a fighter's move index (empty for -1).
inline FString EHMoveId(const eh::Match& Match, int32 Player, int32 Move)
{
	return Move < 0 ? FString() : FString(UTF8_TO_TCHAR(Match.Character(Player).moves[static_cast<size_t>(Move)].id.c_str()));
}

enum class EEHScreen : uint8
{
	Error,
	Title,
	Main,
	Select,
	Match,
	Results,
	Settings,
	Bindings,
	MoveList,
	Credits,
	QuitConfirm,
	DisplayConfirm,
};

enum class EEHMode : uint8
{
	VersusCpu,
	Versus,
	Training,
	Tutorial,
};

struct FEHMenuItem
{
	FString Label;
	TFunction<FString()> Value;          // optional right-hand value
	TFunction<void(int32)> Change;        // left/right
	TFunction<void()> Activate;           // confirm
	// Optional painter for the right-hand value (button glyphs); draws right-aligned at the anchor.
	TFunction<void(FEHPainter&, FVector2f, bool)> PaintValue;
	FString Hint;
	bool bHeader = false;
};

// One entry of a prompt row: a gameplay action or a menu command, and its label.
struct FEHHint
{
	EEHAction Action = EEHAction::Count;
	EEHNav Nav = EEHNav::Count;
	FString Label;
	static FEHHint Act(EEHAction A, const FString& L) { FEHHint H; H.Action = A; H.Label = L; return H; }
	static FEHHint Menu(EEHNav N, const FString& L) { FEHHint H; H.Nav = N; H.Label = L; return H; }
};

struct FEHBanner
{
	FString Text;
	FString Sub;
	float Age = 0.0f;
	float Life = 1.2f;
	FLinearColor Color = FLinearColor::White;
};

struct FEHCallout
{
	FString Text;
	int32 Side = 0;
	float Age = 0.0f;
	float Life = 0.9f;
	FLinearColor Color = FLinearColor::White;
};

struct FEHInputLogEntry
{
	int8 X = 0;
	int8 Y = 0;      // +1 up, -1 down
	uint8 Held = 0;
	int32 Frames = 1;
};

struct FEHStats
{
	int32 Damage[2] = {0, 0};
	int32 MaxCombo[2] = {0, 0};
	int32 Throws[2] = {0, 0};
	int32 Deflects[2] = {0, 0};
	int32 Frames = 0;
};

// What a Lesson step teaches (its goal check and the partner's script).
enum class EEHLessonStep : uint8
{
	Movement,
	Light,
	Heavy,
	Block,
	LowGuard,
	TimedBlock,
	JumpIn,
	AntiAir,
	Throw,
	ThrowEscape,
	ComboThrow,
	Punish,
	Special,
	Done,
};

struct FEHTutorialStep
{
	FString Title;
	FString Body;
	int32 Goal = 1;
	EEHLessonStep Kind = EEHLessonStep::Done;
};

UCLASS(NotBlueprintable)
class AEHGameDirector : public AActor
{
	GENERATED_BODY()

public:
	AEHGameDirector();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void Tick(float DeltaSeconds) override;

	void PaintUI(FEHPainter& P);
	float UIScale() const { return Settings.UIScale; }

	// Automation hooks (evaluation runs use the same router path as devices).
	FEHInputRouter* Router() const { return RouterPtr.Get(); }
	EEHScreen CurrentScreen() const { return Screen; }
	const eh::Match* CurrentMatch() const { return Match.IsValid() ? Match.Get() : nullptr; }
	bool IsPaused() const { return bPaused; }

private:
	// Data
	eh::Rules Rules;
	eh::CharacterDef Chars[2];       // 0 Wren, 1 Ashka
	FEHPresentation Pres;
	FString DataError;
	FEHSettings Settings;
	FString SettingsWarning;
	TSharedPtr<FEHInputRouter> RouterPtr;
	FEHAudio Audio;
	FEHFonts Fonts;

	// Flow
	EEHScreen Screen = EEHScreen::Title;
	EEHScreen SettingsReturn = EEHScreen::Main;
	float ScreenAge = 0.0f;
	TArray<FEHMenuItem> Menu;
	int32 MenuIndex = 0;
	FString MenuTitle;
	int32 MenuOwner = EHDeviceNone;  // device allowed to drive the current menu (-1 = any)
	int32 PrimaryDevice = EHDeviceKeyboardA;
	FString Toast;
	float ToastAge = 10.0f;

	// Character select
	EEHMode Mode = EEHMode::VersusCpu;
	int32 SelectCursor[2] = {0, 1};
	bool SelectLocked[2] = {false, false};
	int32 SelectDevice[2] = {EHDeviceNone, EHDeviceNone};
	int32 SelectStage = 0;          // versus CPU: 0 pick yours, 1 pick CPU fighter, 2 difficulty/side
	bool bPlayerOnRight = false;

	// Match
	TUniquePtr<eh::Match> Match;
	eh::CpuController Cpu[2];
	bool SlotCpu[2] = {false, true};
	int32 SlotDevice[2] = {EHDeviceKeyboardA, EHDeviceNone};
	int32 SlotChar[2] = {0, 1};
	int32 CpuLevel = 1;
	eh::FixedStepClock Clock;
	int32 PrevX[2] = {0, 0};
	bool bPaused = false;
	int32 PauseOwner = EHDeviceNone;
	bool bResultsShown = false;
	FEHStats Stats;
	int32 LastWinner = -1;
	float HealthLag[2] = {1.0f, 1.0f};
	float LastHitAge[2] = {10.0f, 10.0f};
	TArray<FEHBanner> Banners;
	TArray<FEHCallout> Callouts;
	FString DisconnectNotice;

	// Training
	eh::DummyMode Dummy = eh::DummyMode::Stand;
	int32 TrainingLayout = 0;
	bool bShowHitboxes = false;
	bool bShowFrameData = true;
	bool bShowInputs = true;
	bool bInfiniteMeter = false;
	TArray<FEHInputLogEntry> InputLog[2];
	FString LastMoveName[2];
	FString LastMoveFrames[2];

	// Tutorial
	TArray<FEHTutorialStep> Lesson;
	int32 LessonStep = 0;
	int32 LessonCount = 0;
	float LessonDoneAge = -1.0f;
	int32 ScriptTimer = 0;
	int8 LessonWalkDir = 0;

	// Presentation
	UPROPERTY()
	TObjectPtr<AEHFighterVisual> Visual[2];
	UPROPERTY()
	TObjectPtr<AEHVfx> Vfx;
	UPROPERTY()
	TObjectPtr<ACameraActor> Camera;
	UPROPERTY()
	TObjectPtr<UTexture2D> TitleTexture;
	FSlateBrush TitleBrush;
	FVector CamPos = FVector(0, 600, 140);
	float CamShake = 0.0f;
	float CamPunch = 0.0f;
	float MenuOrbit = 0.0f;
	double RenderTime = 0.0;
	TSharedPtr<SEHCanvas> Canvas;
	bool bAnyGraybox = false;
	float FootTimer[2] = {0.0f, 0.0f};
	int64 LastSplash[2] = {-1, -1};
	bool bMatchActive = false;

	// Display change safety
	FEHSettings DisplayRevert;
	// Display values from the settings file; launch flags override them for the session only.
	FEHSettings DiskDisplay;
	bool bSessionDisplayOverride = false;
	float DisplayConfirmLeft = 0.0f;
	// After each display change: seconds until the fullscreen check, and how often it had to ask again.
	static constexpr float DisplayVerifyDelay = 0.5f;
	static constexpr int32 MaxDisplayReasserts = 2;
	float DisplayVerifyIn = 0.0f;
	int32 DisplayReasserts = 0;
	int32 TotalDisplayReasserts = 0;

	// Automation
	FString AutoScript;
	TArray<FString> AutoLines;
	int32 AutoLine = 0;
	float AutoWait = 0.0f;
	bool bAutoBot[2] = {false, false};
	eh::CpuController AutoBot[2];
	uint32 AutoBotHeld[2] = {0, 0};
	FString EvidenceDir;
	TArray<FString> AutoLog;
	TArray<float> FrameTimes;
	bool bRecordFrames = false;
	float InputLogLeft = 0.0f;       // automation: log every press and held-state change while > 0
	TMap<int32, uint32> InputLogHeld;
	int32 AutoMatches = 0;
	double AutoStart = 0.0;
	float AudioProbeLeft = 0.0f;     // automation: seconds of off-thread audio submits left (Development builds)
	int64 AudioProbeCalls = 0;

	// Lifecycle helpers
	bool LoadData();
	void ApplySettings(bool bDisplay);
	void SaveSettings();
	// Writes the settings file; display values overridden by launch flags keep their saved values.
	bool WriteSettings();
	// Writes the engine's GameUserSettings.ini, which sizes the window before BeginPlay, with the saved display values,
	// and leaves the engine's settings object on them.
	void SaveEngineDisplay(const FEHSettings& Saved);
	bool DescribeGameWindow(FEHWindowFit& Out) const;
	void VerifyFullscreenApplied();
	void ShowToast(const FString& Text);

	// Flow
	void GoTo(EEHScreen Next);
	void BuildMenu();
	void HandleNav();
	void HandleMenuNav(const FEHNavEvent& E);
	void HandleSelectNav(const FEHNavEvent& E);
	void HandleMatchNav(const FEHNavEvent& E);
	void HandleConnections();
	void RefreshDisconnectNotice();
	void BeginSelect(EEHMode InMode);
	void StartMatch();
	void Rematch();
	void LeaveMatch(EEHScreen To);
	void SetPaused(bool bPause, int32 Owner);
	void BuildPauseMenu();
	void BuildSettingsMenu(int32 Page);
	void BuildBindingsMenu(EEHBindingSet Set);
	int32 SettingsPage = 0;
	// Controls: one layout (BindingSet) at a time. Pages: 0 action list, 1 one action, 2 conflict, 3 restore confirm.
	EEHBindingSet BindingSet = EEHBindingSet::KeyboardA;
	bool bResetAllLayouts = false;   // page 3 restores every layout, not just BindingSet
	int32 BindingPage = 0;
	int32 BindingAction = 0;
	int32 BindingListIndex = 0;
	int32 CaptureAction = -1;        // >= 0 while waiting for the new button
	int32 CaptureSlot = 0;
	float CaptureLeft = 0.0f;        // an unanswered capture cancels itself after this many seconds
	FKey PendingKey;
	FEHBindingRef PendingConflict;
	void BeginBindingCapture(int32 Slot);
	// Applies a captured key: free keys are bound at once; a key another action uses opens the conflict page.
	void ApplyCapturedKey(const FKey& Key);
	void ResolveConflict(bool bSwap);
	void BindingsChanged(const FString& Message);
	EEHDeviceKind KindForSet(EEHBindingSet Set) const;
	void PaintBindingValue(FEHPainter& P, FVector2f Right, EEHBindingSet Set, EEHAction Action, int32 OnlySlot, bool bSel);
	FString KeyName(EEHBindingSet Set, const FKey& Key) const;
	// The name a player sees for a button on a device kind ("Square", "X", "bottom face button", "J").
	static FString ButtonNameOf(EEHDeviceKind Kind, const FKey& Key);
	void AssignGamepadPlayers();

	// Simulation
	void SimStep();
	eh::InputFrame SlotInput(int32 Player);
	eh::InputFrame LessonScriptInput();
	void ProcessEvents();
	void UpdateLesson(const eh::Event& E);
	void SetupLesson();
	void RecordInput(int32 Player, const eh::InputFrame& In);
	void UpdateFrameData(int32 Player);

	// Presentation
	void UpdatePresentation(float DeltaSeconds, float Alpha);
	void UpdateCamera(float DeltaSeconds);
	void SpawnWorldActors();
	void ConfigureVisuals();
	FVector SimToWorld(int32 X, int32 Y) const;

	// UI painting
	void PaintBackdrop(FEHPainter& P, float Dim);
	void PaintTitle(FEHPainter& P);
	void PaintMenu(FEHPainter& P, const FString& Heading, bool bCompact);
	void PaintSelect(FEHPainter& P);
	void PaintHUD(FEHPainter& P);
	void PaintTraining(FEHPainter& P);
	void PaintLesson(FEHPainter& P);
	void PaintResults(FEHPainter& P);
	void PaintMoveList(FEHPainter& P);
	void PaintCredits(FEHPainter& P);
	void PaintError(FEHPainter& P);
	// Draws one key or button glyph at Pos (or only measures it) and returns its width.
	float PaintKeyGlyph(FEHPainter& P, FVector2f Pos, EEHDeviceKind Kind, const FKey& Key, float Height, bool bMeasureOnly = false);
	// The button a device's player presses for a gameplay action or a menu command, drawn as a glyph.
	float PaintPrompt(FEHPainter& P, FVector2f Pos, const FEHHint& Hint, int32 Device, float Height = 30.0f);
	void PaintPromptRow(FEHPainter& P, FVector2f Pos, const TArray<FEHHint>& Items, int32 Device);
	EEHDeviceKind PromptKind(int32 Device) const;
	// The layout a prompt for this device reads: its keyboard side, or its controller layout.
	EEHBindingSet PromptSet(int32 Device) const;
	FKey PromptKey(const FEHHint& Hint, int32 Device) const;
	void PaintHitboxes(FEHPainter& P);

	// Automation
	void InitAutomation();
	void TickAutomation(float DeltaSeconds);
	void RunDisplayHotplugProbe();
	void TickAudioProbe(float DeltaSeconds);
	void AutoLogLine(const FString& Line);
	void WriteEvidence(const FString& Name, const FString& Text);
	// press/hold/release by name: a gameplay action presses the device's bound key, a menu command its fixed key.
	bool AutoKey(int32 Device, const FString& Name, FKey& OutKey) const;
	void AutoInject(int32 Device, const FKey& Key);
	void RunBindingsSelfTest();
	void RunInputSelfTest();
	eh::InputFrame AutoBotInput(int32 Player);
	void AutoReleaseBots();
};
