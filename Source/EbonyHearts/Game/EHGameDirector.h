// Owns the whole player journey: menus, character select, matches (versus CPU, local versus, training and the
// interactive lesson), results, settings and quit. Steps the combat simulation at a fixed 60 Hz from real time and
// turns its events into presentation (animation, effects, sound, camera, HUD).
#pragma once

#include "CoreMinimal.h"
#include "EHAI.h"
#include "EHAudio.h"
#include "EHClock.h"
#include "EHCombatText.h"
#include "EHCombatData.h"
#include "EHInputRouter.h"
#include "EHMatch.h"
#include "EHAlignment.h"
#include "EHPlayerCharacter.h"
#include "EHPresentation.h"
#include "EHSettings.h"
#include "EHUICanvas.h"
#include "GameFramework/Actor.h"
#include "GenericPlatform/GenericApplication.h"
#include "GenericPlatform/GenericWindow.h"

#include "EHGameDirector.generated.h"

class ACameraActor;
class AEHFighterVisual;
class AEHPlayerCharacter;
class AEHTrainingDummy;
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
	FirstPerson, // first-person play in the Chapel (the prototype's only mode)
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
	// Optional: true while the value differs from what is saved (shown marked until applied).
	TFunction<bool()> Pending;
	// Optional: the sound for confirming this item instead of the usual confirm (one sound per press).
	FName ConfirmSound;
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
	// CPU time spent building the interface's draw list, recorded between perf_begin and perf_end (milliseconds).
	void RecordUiPaint(float Ms) { if (bRecordFrames) { UiPaintTimes.Add(Ms); } }

	// Automation hooks (evaluation runs use the same router path as devices).
	FEHInputRouter* Router() const { return RouterPtr.Get(); }
	EEHScreen CurrentScreen() const { return Screen; }
	const eh::Match* CurrentMatch() const { return Match.IsValid() ? Match.Get() : nullptr; }
	bool IsPaused() const { return bPaused; }

private:
	// Object references come first: reflected property offsets must stay below 64 KiB, and the settings copies below are large.
	UPROPERTY()
	TObjectPtr<AEHFighterVisual> Visual[2];
	UPROPERTY()
	TObjectPtr<AEHVfx> Vfx;
	UPROPERTY()
	TObjectPtr<ACameraActor> Camera;
	UPROPERTY()
	TObjectPtr<AEHPlayerCharacter> FPPlayer;
	UPROPERTY()
	TObjectPtr<AEHTrainingDummy> FPDummy;
	UPROPERTY()
	TObjectPtr<AEHWolf> FPWolf;
	// The pack (milestone 6): every Chapel wolf; FPWolf is the first.
	UPROPERTY()
	TArray<TObjectPtr<AEHWolf>> FPWolves;
	UPROPERTY()
	TArray<TObjectPtr<AEHFireball>> FPFireballs;
	UPROPERTY()
	TArray<TObjectPtr<AEHIceWall>> FPWalls;

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
	int32 MoveListPage = 0;
	int32 MoveListPageCount = 1;

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
	// The video settings as saved when the Video page opened; values that differ are shown as unapplied.
	FEHSettings VideoSaved;
	void RestoreVideoSaved();
	// Automation only (`ui_hidden 1`): paint nothing, for clean captures of the stage and fighters (UI mockups, art review).
	bool bAutoHideUI = false;
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

	// First person
	bool bFirstPersonMode = true;
	FEHFirstPersonTuning FPTuning;
	bool bFPCrouchToggled = false;   // controller stick press, or the keyboard with toggle crouch
	bool bFPSprintToggled = false;
	bool bFPKeyCrouchHeld = false;
	bool bFPKeySprintHeld = false;
	int32 FPDevice = EHDeviceKeyboardA;   // the device the player last moved or looked with
	float StaminaMeterAlpha = 0.0f;
	int32 FPResets = 0;
	TArray<FEHFirstPersonEvent> FPEvents;
	FEHFirstPersonInput LastFPInput;
	FVector FPMark = FVector::ZeroVector;   // automation: fp_mark / fp_expect moved
	bool bHadFocus = true;
	float HurtFlash = 0.0f;
	int32 FPDeaths = 0;
	int32 FPGuardedCount = 0;
	int32 FPHurtCount = 0;
	// Spells
	FEHWater FPWater;
	float QhiMeterAlpha = 0.0f;
	int32 FPFireballHits = 0;       // fireballs that reached the dummy
	int32 FPWallsMelted = 0;
	int32 FPWallsShattered = 0;
	int32 FPWallsExpired = 0;
	int32 FPWallsRaised = 0;
	int32 FPFizzles = 0;
	int32 FPRefusedNoQhi = 0;
	int32 FPRefusedNoRoom = 0;
	bool bDevPanel = false;          // development builds: F10 panel (stats, resources, dummy)
	// The player's alignment tier (EHAlignment.h): set by the developer selector, pushed toward evil by harming or
	// killing a Chapel wolf. It survives the death reset, so a case can be repeated.
	int32 FPAlignment = EHAlign::Platonic;
	EEHWolfState FPWolfLastState = EEHWolfState::Calm;
	int32 FPWolfHarms = 0;
	int32 FPWolfKills = 0;
	int32 FPReflected = 0;
	// The "Chapel Wolves" document (2026-11-23). The player as a Shadow (New Direction, "Shadows"; set from the
	// developer panel until death and Qhi Stones exist): no spells; the wolves tell them to pray, and striking, or
	// staying in the Chapel without praying, ends the prototype encounter. Three
	// in-game days of prayer at the Chapel restore them.
	bool bFPShadow = false;
	double FPShadowPrayHours = 0.0;
	float FPExorcism = -1.0f;        // seconds into the exorcism ending, or -1
	int32 FPExorcisms = 0;
	int32 FPAlerts = 0;              // wolves provoked by harm to another
	int32 FPEscalations = 0;         // wolves drawn into a fight another wolf started with an evil aura
	int32 FPWolfTalks = 0;
	int32 FPWolfTalkIndex = 0;
	int32 FPWolfFocus = -1;          // the calm wolf looked at within reach (Interact talks to it), or -1
	void BeginExorcism(const TCHAR* Why);
	void TalkToWolf(int32 Index);
	// Souls-style target lock-on: tracks a wolf or the training dummy; mouse/stick flick switches targets.
	TWeakObjectPtr<AActor> FPLockTarget;
	float FPLockLostLos = 0.0f;
	float FPLockSwitchCooldown = 0.0f;
	float FPLockMouseAccum = 0.0f;
	float FPLockRawMouseX = 0.0f;
	float FPLockRawStickX = 0.0f;
	bool bFPLockSelectorOwnsLook = false;
	bool bFPLockStickHeld = false;
	bool bFPLockPressed = false;
	bool bFPViewPressed = false;   // Switch view was pressed this frame
	int32 FPLockSwitches = 0;
	FVector LockOnPoint(const AActor* Target) const;
	bool HasLockLineOfSight(const AActor* Target) const;
	AActor* FindLockTarget(int32 SwitchDir) const;
	void ClearLockOn(const TCHAR* Why);
	void UpdateLockOn(FEHFirstPersonInput& In, float DeltaSeconds);
	void PaintLockOn(FEHPainter& P);
	int32 LockTargetIndex() const;
	void SpawnWolf();
	// The pack (EHDirectorPack.cpp).
	TArray<EEHWolfState> FPWolvesLastState;
	// Comic-book combat text (milestone 7, EHCombatText.h).
	FEHCombatText CombatText;
	TArray<float> FPWolfIdleTalkAt;     // per wolf: when it may next remark on the player's nearness
	void CombatTextEvents(int32 i, EEHWolfState WS, EEHWolfState Last);
	void CombatTextNearness(float Now);
	bool CombatTextField(const FString& Field, float& V) const;
	TArray<float> PackWaiting;          // per wolf: seconds since it last held the turn
	int32 PackHolder = -1;
	int32 PackHolderAttacks = 0;
	float PackHolderSince = 0.0f;
	bool bPackOverwhelmed = false;
	bool bOneOnOne = false;
	float OneOnOneLeft = 0.0f;
	int32 PackPasses = 0;
	int32 PackMaxAttackers = 0;
	int32 PackOneOnOnes = 0;
	TArray<double> FPHurtTimes;
	TArray<float> PackRepathAt;
	void SpawnPack(int32 Count);
	void ResetPack();
	void ResetWolves();
	void TickPack(float DeltaSeconds);
	void PassTurn(const TArray<int32>& Fighting, const TCHAR* Why);
	void PackRepathSoon();
	bool WolfFighting(const AEHWolf* W) const;
	AEHWolf* NearestLiveWolf(const FVector& To, float Within) const;
	bool PackField(const FString& Field, float& V) const;
	void WolfStruck(const FEHWolfHit& R, const TCHAR* What);
	// The spell selector (hold FPSpellSelect): a wheel or a list of every spell; release casts the highlighted one.
	bool bSpellSelect = false;
	int32 SpellHighlight = -1;       // index into the spell list, -1 none (the wheel's centre)
	FVector2D SpellPointer = FVector2D::ZeroVector;   // wheel: where the mouse or stick points (unit circle)
	float SpellListScroll = 0.0f;    // list: mouse travel toward the next row
	bool bSpellStickHeld = false;    // list: the stick's flick already moved one row
	float SpellSelectAlpha = 0.0f;
	int32 SpellSelectCasts = 0;
	void OpenSpellSelect();
	// Closes the selector; with bCast, returns the highlighted spell to cast (None to cancel).
	EEHFistAction CloseSpellSelect(bool bCast);
	void PaintSpellSelect(FEHPainter& P);
	void TickSpells(float DeltaSeconds);
	void ClearSpells();
	// The Chapel's interactions and prayer (EHDirectorChapel.cpp).
	bool bFPInteractPressed = false;  // Interact was pressed this frame
	int32 FPInteractFocus = -1;       // the interactable the player looks at, -1 none
	FString FPMessage;                // a used thing's text, shown for a moment
	float FPMessageLeft = 0.0f;
	FVector FPMessageFrom = FVector::ZeroVector;
	int32 FPMessages = 0;
	bool bPraying = false;
	float PrayAlpha = 0.0f;
	float PrayerSeconds = 0.0f;
	float RiseBlockLeft = 0.0f;
	float FPSparkLeft = 0.0f;         // the forge: seconds to the next ember
	int32 FPSparks = 0;      // after rising from prayer, techniques and spells wait a moment
	int32 FPPrayers = 0;
	// Finds what the player looks at, handles Interact and, while praying, holds the player kneeling.
	void UpdateChapel(FEHFirstPersonInput& In, float DeltaSeconds);
	void BeginPrayer();
	void EndPrayer(const TCHAR* Why);
	void PaintChapel(FEHPainter& P);
	// Destiny's Ark's time (EHWorldClock.h; driven in EHDirectorChapel.cpp).
	double FPClockHours = 0.0;          // hours since hour 0 of day 0
	double FPClockApplied = -1.0;
	FEHClockKey FPClockNow;
	TWeakObjectPtr<class ULightComponent> SkyLightComp;
	float SkyBaseIntensity = 1.0f;
	TWeakObjectPtr<class UExponentialHeightFogComponent> FogComp;
	FLinearColor FogBase = FLinearColor::Black;
	struct FGlassGlow
	{
		TWeakObjectPtr<class UMaterialInstanceDynamic> Mid;
		float Base = 1.0f;
	};
	TArray<FGlassGlow> GlassGlows;
	struct FSkyFill
	{
		TWeakObjectPtr<class ULightComponent> Light;
		float BaseIntensity = 1.0f;
		FLinearColor BaseColor = FLinearColor::White;
	};
	TArray<FSkyFill> SkyFills;
	FLinearColor ClockNightColor = FLinearColor::White;   // the first key's colour: fills keep their own colour at night
	void InitWorldClock();
	void TickWorldClock(float RealSeconds);
	void ApplyWorldClock(bool bForce);
	void BuildDeveloperPanel();
	int32 FrameCaptureLeft = 0;     // automation: fp_frames screenshots every rendered frame
	int32 FrameCaptureIndex = 0;
	double FrameCaptureNext = 0.0;
	FString FrameCaptureName;
	bool LoadFirstPersonData();
	void BeginFirstPerson();
	void TickFirstPerson(float DeltaSeconds);
	FEHFirstPersonInput GatherFirstPersonInput(float DeltaSeconds);
	void PlayFirstPersonEvents();
	void ResetFirstPerson(const TCHAR* Why);
	void BuildFirstPersonPause();
	void HandleFirstPersonNav(const FEHNavEvent& E);
	void PaintFirstPerson(FEHPainter& P);
	void ApplyFieldOfView();
	// Puts the camera where Settings.bThirdPerson says (instantly, or with the switch blend).
	void ApplyCameraView(bool bInstant);
	void ToggleCameraView();
	// Rumble on the controller the player is using (when vibration is on). Large and small motor strengths 0..1.
	void Rumble(float Large, float Small, float Seconds);
	// One variant of a numbered sound (S_<Base>_01..N) at a pitch.
	void PlayImpact(const TCHAR* Base, int32 Variants, float Volume, float Pitch);
	int32 RumbleCount = 0;
	bool RunFirstPersonCommand(const TArray<FString>& T, const FString& Line);
	FString DescribeFirstPerson() const;

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
	TArray<float> UiPaintTimes;
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
	void TitleWordmark(FEHPainter& P, FVector2f Centre, float Scale, float Alpha);
	void PaintTitle(FEHPainter& P);
	// TopY >= 0 places a compact (centred) menu's top edge there instead of centring it vertically.
	void PaintMenu(FEHPainter& P, const FString& Heading, bool bCompact, float TopY = -1.0f);
	void PaintMainMenuA(FEHPainter& P);
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
