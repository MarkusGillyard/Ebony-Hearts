// Menus, character select, pause, settings, results and the interactive lesson.
#include "EHGameDirector.h"

#include "EHFighterVisual.h"
#include "EHVfx.h"
#include "GameFramework/GameUserSettings.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Engine/Engine.h"

namespace EHFlowDetail
{
FEHMenuItem Button(const FString& Label, TFunction<void()> Activate, const FString& Hint = FString())
{
	FEHMenuItem I;
	I.Label = Label;
	I.Activate = MoveTemp(Activate);
	I.Hint = Hint;
	return I;
}

FEHMenuItem Choice(const FString& Label, TFunction<FString()> Value, TFunction<void(int32)> Change, const FString& Hint = FString())
{
	FEHMenuItem I;
	I.Label = Label;
	I.Value = MoveTemp(Value);
	I.Change = MoveTemp(Change);
	I.Hint = Hint;
	return I;
}

FString OnOff(bool b) { return b ? TEXT("On") : TEXT("Off"); }

const TArray<FIntPoint>& Resolutions()
{
	static const TArray<FIntPoint> R = {{1280, 720}, {1600, 900}, {1920, 1080}, {2560, 1440}, {3440, 1440}, {3840, 2160}};
	return R;
}

const TCHAR* DummyName(eh::DummyMode M)
{
	switch (M)
	{
	case eh::DummyMode::Stand: return TEXT("Stand");
	case eh::DummyMode::Block: return TEXT("Block all");
	case eh::DummyMode::BlockAfterHit: return TEXT("Block after first hit");
	case eh::DummyMode::RandomBlock: return TEXT("Random block");
	case eh::DummyMode::TechThrows: return TEXT("Escape grabs");
	case eh::DummyMode::Cpu: return TEXT("CPU");
	}
	return TEXT("?");
}
}
using namespace EHFlowDetail;

void AEHGameDirector::GoTo(EEHScreen Next)
{
	Screen = Next;
	ScreenAge = 0.0f;
	MenuIndex = 0;
	BuildMenu();
	AutoLogLine(FString::Printf(TEXT("screen %d"), static_cast<int32>(Next)));
}

void AEHGameDirector::BuildMenu()
{
	Menu.Reset();
	MenuTitle.Reset();
	MenuOwner = EHDeviceNone;
	switch (Screen)
	{
	case EEHScreen::Main:
		MenuTitle = TEXT("");
		Menu.Add(Button(TEXT("Versus CPU"), [this] { BeginSelect(EEHMode::VersusCpu); }, TEXT("Fight a computer opponent.")));
		Menu.Add(Button(TEXT("Local Versus"), [this] { BeginSelect(EEHMode::Versus); }, TEXT("Two players on one machine.")));
		Menu.Add(Button(TEXT("Training"), [this] { BeginSelect(EEHMode::Training); }, TEXT("Practice with frame data, hitboxes and input history.")));
		Menu.Add(Button(TEXT("Lesson"), [this] { BeginSelect(EEHMode::Tutorial); }, TEXT("Learn the six actions and how they counter each other.")));
		Menu.Add(Button(TEXT("Move List"), [this] { SettingsReturn = EEHScreen::Main; GoTo(EEHScreen::MoveList); }, TEXT("Both fighters' techniques.")));
		Menu.Add(Button(TEXT("Settings"), [this] { SettingsReturn = EEHScreen::Main; SettingsPage = 0; GoTo(EEHScreen::Settings); }, TEXT("Controls, video, audio and accessibility.")));
		Menu.Add(Button(TEXT("Credits"), [this] { GoTo(EEHScreen::Credits); }));
		Menu.Add(Button(TEXT("Quit"), [this] { GoTo(EEHScreen::QuitConfirm); }));
		break;
	case EEHScreen::QuitConfirm:
		MenuTitle = TEXT("Quit to desktop?");
		Menu.Add(Button(TEXT("Quit"), [this] {
			SaveSettings();
			AutoLogLine(TEXT("quit requested"));
			UKismetSystemLibrary::QuitGame(this, GetWorld()->GetFirstPlayerController(), EQuitPreference::Quit, false);
		}));
		Menu.Add(Button(TEXT("Cancel"), [this] { GoTo(EEHScreen::Main); }));
		break;
	case EEHScreen::Results:
		MenuTitle = TEXT("");
		Menu.Add(Button(TEXT("Rematch"), [this] { Rematch(); }));
		Menu.Add(Button(TEXT("Change Fighters"), [this] { const EEHMode M = Mode; LeaveMatch(EEHScreen::Main); BeginSelect(M); }));
		Menu.Add(Button(TEXT("Main Menu"), [this] { LeaveMatch(EEHScreen::Main); }));
		break;
	case EEHScreen::Settings:
		BuildSettingsMenu(SettingsPage);
		break;
	case EEHScreen::Bindings:
		BuildBindingsMenu(BindingSet);
		break;
	case EEHScreen::DisplayConfirm:
		MenuTitle = TEXT("Keep these display settings?");
		Menu.Add(Button(TEXT("Keep"), [this] { bSessionDisplayOverride = false; SaveSettings(); SettingsPage = 2; GoTo(EEHScreen::Settings); }));
		Menu.Add(Button(TEXT("Revert"), [this] { Settings = DisplayRevert; ApplySettings(true); SaveSettings(); SettingsPage = 2; GoTo(EEHScreen::Settings); }));
		DisplayConfirmLeft = 12.0f;
		break;
	case EEHScreen::Match:
		if (bPaused)
		{
			BuildPauseMenu();
		}
		break;
	default:
		break;
	}
}

void AEHGameDirector::BuildPauseMenu()
{
	Menu.Reset();
	MenuIndex = 0;
	MenuOwner = PauseOwner;
	MenuTitle = TEXT("Paused");
	Menu.Add(Button(TEXT("Resume"), [this] { SetPaused(false, EHDeviceNone); }));
	if (Mode == EEHMode::Training)
	{
		Menu.Add(Choice(TEXT("Dummy"), [this] { return FString(DummyName(Dummy)); }, [this](int32 D) {
			Dummy = static_cast<eh::DummyMode>((static_cast<int32>(Dummy) + D + 6) % 6);
			const int32 DummySlot = SlotCpu[0] ? 0 : 1;
			Cpu[DummySlot].SetDummy(Dummy);
		}, TEXT("What the training partner does.")));
		Menu.Add(Choice(TEXT("CPU level"), [this] { return FString(CpuLevel == 0 ? TEXT("Easy") : (CpuLevel == 1 ? TEXT("Normal") : TEXT("Hard"))); }, [this](int32 D) {
			CpuLevel = (CpuLevel + D + 3) % 3;
			const int32 DummySlot = SlotCpu[0] ? 0 : 1;
			Cpu[DummySlot].Setup(DummySlot, static_cast<eh::CpuLevel>(CpuLevel), static_cast<uint32>(FPlatformTime::Cycles()));
			Cpu[DummySlot].SetDummy(Dummy);
		}, TEXT("Used when the dummy is set to CPU.")));
		Menu.Add(Choice(TEXT("Start position"), [this] { return FString(TrainingLayout == 0 ? TEXT("Centre") : (TrainingLayout == 1 ? TEXT("Opponent cornered") : TEXT("You cornered"))); }, [this](int32 D) { TrainingLayout = (TrainingLayout + D + 3) % 3; }, TEXT("Applied on reset.")));
		Menu.Add(Button(TEXT("Reset positions"), [this] { Match->TrainingResetPositions(TrainingLayout); SetPaused(false, EHDeviceNone); }, TEXT("Also on the Reset button during play.")));
		Menu.Add(Choice(TEXT("Hitboxes"), [this] { return OnOff(bShowHitboxes); }, [this](int32) { bShowHitboxes = !bShowHitboxes; }));
		Menu.Add(Choice(TEXT("Frame data"), [this] { return OnOff(bShowFrameData); }, [this](int32) { bShowFrameData = !bShowFrameData; }));
		Menu.Add(Choice(TEXT("Input history"), [this] { return OnOff(bShowInputs); }, [this](int32) { bShowInputs = !bShowInputs; }));
		Menu.Add(Choice(TEXT("Gauge"), [this] { return FString(bInfiniteMeter ? TEXT("Always full") : TEXT("Normal")); }, [this](int32) { bInfiniteMeter = !bInfiniteMeter; }));
	}
	else if (Mode == EEHMode::Tutorial)
	{
		Menu.Add(Button(TEXT("Restart lesson"), [this] { StartMatch(); }));
		Menu.Add(Button(TEXT("Skip this step"), [this] { LessonCount = 999; SetPaused(false, EHDeviceNone); }));
	}
	else
	{
		Menu.Add(Button(TEXT("Restart match"), [this] { Rematch(); }));
	}
	Menu.Add(Button(TEXT("Move List"), [this] { SettingsReturn = EEHScreen::Match; GoTo(EEHScreen::MoveList); }));
	Menu.Add(Button(TEXT("Settings"), [this] { SettingsReturn = EEHScreen::Match; SettingsPage = 0; GoTo(EEHScreen::Settings); }));
	Menu.Add(Button(TEXT("Change Fighters"), [this] { const EEHMode M = Mode; LeaveMatch(EEHScreen::Main); BeginSelect(M); }));
	Menu.Add(Button(TEXT("Main Menu"), [this] { LeaveMatch(EEHScreen::Main); }));
}

void AEHGameDirector::BuildSettingsMenu(int32 Page)
{
	Menu.Reset();
	MenuIndex = 0;
	SettingsPage = Page;
	auto Back = [this] { BuildSettingsMenu(0); };
	switch (Page)
	{
	case 0:
		MenuTitle = TEXT("Settings");
		Menu.Add(Button(TEXT("Controls"), [this] { BuildSettingsMenu(1); }));
		Menu.Add(Button(TEXT("Video"), [this] { BuildSettingsMenu(2); }));
		Menu.Add(Button(TEXT("Audio"), [this] { BuildSettingsMenu(3); }));
		Menu.Add(Button(TEXT("Accessibility"), [this] { BuildSettingsMenu(4); }));
		Menu.Add(Button(TEXT("Back"), [this] {
			SaveSettings();
			if (SettingsReturn == EEHScreen::Match)
			{
				Screen = EEHScreen::Match;
				BuildPauseMenu();
			}
			else
			{
				GoTo(SettingsReturn);
			}
		}));
		break;
	case 1:
		MenuTitle = TEXT("Controls");
		Menu.Add(Choice(TEXT("Button prompts"), [this] {
			switch (Settings.PromptStyle)
			{
			case EEHPromptStyle::Keyboard: return FString(TEXT("Keyboard"));
			case EEHPromptStyle::PlayStation: return FString(TEXT("PlayStation"));
			case EEHPromptStyle::Xbox: return FString(TEXT("Xbox"));
			default: return FString(TEXT("Automatic"));
			}
		}, [this](int32 D) { Settings.PromptStyle = static_cast<EEHPromptStyle>((static_cast<int32>(Settings.PromptStyle) + D + 4) % 4); }, TEXT("Automatic follows the device each player uses.")));
		Menu.Add(Button(TEXT("Keyboard - left side"), [this] { BindingSet = EEHBindingSet::KeyboardA; GoTo(EEHScreen::Bindings); }, TEXT("Player one's default keyboard layout.")));
		Menu.Add(Button(TEXT("Keyboard - right side"), [this] { BindingSet = EEHBindingSet::KeyboardB; GoTo(EEHScreen::Bindings); }, TEXT("Player two's default keyboard layout.")));
		Menu.Add(Button(TEXT("Gamepad"), [this] { BindingSet = EEHBindingSet::Gamepad; GoTo(EEHScreen::Bindings); }));
		Menu.Add(Button(TEXT("Restore default controls"), [this] { Settings.Bindings = FEHBindings::Defaults(); SaveSettings(); ShowToast(TEXT("Default controls restored.")); }));
		Menu.Add(Button(TEXT("Back"), Back));
		break;
	case 2:
		MenuTitle = TEXT("Video");
		Menu.Add(Choice(TEXT("Display mode"), [this] { return FString(Settings.WindowMode == 0 ? TEXT("Fullscreen") : (Settings.WindowMode == 1 ? TEXT("Borderless") : TEXT("Windowed"))); }, [this](int32 D) { Settings.WindowMode = (Settings.WindowMode + D + 3) % 3; }));
		Menu.Add(Choice(TEXT("Resolution"), [this] { return FString::Printf(TEXT("%d x %d"), Settings.Resolution.X, Settings.Resolution.Y); }, [this](int32 D) {
			const TArray<FIntPoint>& R = Resolutions();
			int32 Index = R.IndexOfByKey(Settings.Resolution);
			Index = (Index < 0 ? 2 : (Index + D + R.Num()) % R.Num());
			Settings.Resolution = R[Index];
		}, TEXT("Used in fullscreen and windowed modes.")));
		Menu.Add(Choice(TEXT("Quality"), [this] { const TCHAR* Q[] = {TEXT("Low"), TEXT("Medium"), TEXT("High"), TEXT("Epic")}; return FString(Q[Settings.Quality]); }, [this](int32 D) { Settings.Quality = (Settings.Quality + D + 4) % 4; }));
		Menu.Add(Choice(TEXT("Render scale"), [this] { return FString::Printf(TEXT("%d%%"), Settings.RenderScale); }, [this](int32 D) { Settings.RenderScale = FMath::Clamp(Settings.RenderScale + D * 5, 50, 100); }, TEXT("Below 100% renders fewer pixels and upscales.")));
		Menu.Add(Choice(TEXT("Frame limit"), [this] { return Settings.FrameCap == 0 ? FString(TEXT("Off")) : FString::Printf(TEXT("%d"), Settings.FrameCap); }, [this](int32 D) {
			const int32 Caps[] = {0, 60, 120, 144, 165, 240};
			int32 Index = 0;
			for (int32 i = 0; i < 6; ++i) { if (Caps[i] == Settings.FrameCap) Index = i; }
			Settings.FrameCap = Caps[(Index + D + 6) % 6];
		}, TEXT("Combat always runs at 60 steps per second.")));
		Menu.Add(Choice(TEXT("VSync"), [this] { return OnOff(Settings.bVSync); }, [this](int32) { Settings.bVSync = !Settings.bVSync; }));
		Menu.Add(Button(TEXT("Apply"), [this] {
			DisplayRevert = FEHSettings::Load();
			ApplySettings(true);
			GoTo(EEHScreen::DisplayConfirm);
		}, TEXT("Reverts automatically unless you confirm.")));
		Menu.Add(Button(TEXT("Back"), [this] { Settings = FEHSettings::Load(); BuildSettingsMenu(0); }, TEXT("Discards unapplied video changes.")));
		break;
	case 3:
		MenuTitle = TEXT("Audio");
		Menu.Add(Choice(TEXT("Master"), [this] { return FString::Printf(TEXT("%d"), Settings.MasterVolume); }, [this](int32 D) { Settings.MasterVolume = FMath::Clamp(Settings.MasterVolume + D * 5, 0, 100); ApplySettings(false); Audio.Play(TEXT("UiMove"), EEHSoundCat::Ui); }));
		Menu.Add(Choice(TEXT("Music"), [this] { return FString::Printf(TEXT("%d"), Settings.MusicVolume); }, [this](int32 D) { Settings.MusicVolume = FMath::Clamp(Settings.MusicVolume + D * 5, 0, 100); ApplySettings(false); }));
		Menu.Add(Choice(TEXT("Effects"), [this] { return FString::Printf(TEXT("%d"), Settings.EffectsVolume); }, [this](int32 D) { Settings.EffectsVolume = FMath::Clamp(Settings.EffectsVolume + D * 5, 0, 100); ApplySettings(false); Audio.PlayVaried(TEXT("HitLight"), 3); }));
		Menu.Add(Choice(TEXT("Ambience"), [this] { return FString::Printf(TEXT("%d"), Settings.AmbienceVolume); }, [this](int32 D) { Settings.AmbienceVolume = FMath::Clamp(Settings.AmbienceVolume + D * 5, 0, 100); ApplySettings(false); }));
		Menu.Add(Button(TEXT("Back"), Back));
		break;
	case 4:
		MenuTitle = TEXT("Accessibility");
		Menu.Add(Choice(TEXT("Interface scale"), [this] { return FString::Printf(TEXT("%d%%"), FMath::RoundToInt(Settings.UIScale * 100.0f)); }, [this](int32 D) { Settings.UIScale = FMath::Clamp(Settings.UIScale + D * 0.1f, 0.8f, 1.4f); }));
		Menu.Add(Choice(TEXT("Reduce camera shake"), [this] { return OnOff(Settings.bReduceShake); }, [this](int32) { Settings.bReduceShake = !Settings.bReduceShake; }));
		Menu.Add(Choice(TEXT("Reduce flashes"), [this] { return OnOff(Settings.bReduceFlash); }, [this](int32) { Settings.bReduceFlash = !Settings.bReduceFlash; ApplySettings(false); }, TEXT("Dims impact flashes and the aura.")));
		Menu.Add(Choice(TEXT("Input hints"), [this] { return OnOff(Settings.bInputHints); }, [this](int32) { Settings.bInputHints = !Settings.bInputHints; }, TEXT("Button prompts along the bottom of menus.")));
		Menu.Add(Choice(TEXT("Default CPU level"), [this] { return FString(Settings.CpuLevel == 0 ? TEXT("Easy") : (Settings.CpuLevel == 1 ? TEXT("Normal") : TEXT("Hard"))); }, [this](int32 D) { Settings.CpuLevel = (Settings.CpuLevel + D + 3) % 3; CpuLevel = Settings.CpuLevel; }));
		Menu.Add(Button(TEXT("Back"), Back));
		break;
	default:
		break;
	}
}

void AEHGameDirector::BuildBindingsMenu(EEHBindingSet Set)
{
	Menu.Reset();
	BindingSet = Set;
	MenuTitle = Set == EEHBindingSet::KeyboardA ? TEXT("Keyboard - left side") : (Set == EEHBindingSet::KeyboardB ? TEXT("Keyboard - right side") : TEXT("Gamepad"));
	for (int32 A = 0; A < EHActionCount; ++A)
	{
		FEHMenuItem I;
		I.Label = EHActionName(static_cast<EEHAction>(A));
		I.Value = [this, A] {
			const int32 S = static_cast<int32>(BindingSet);
			FString Out;
			for (int32 K = 0; K < EHKeysPerAction; ++K)
			{
				const FKey& Key = Settings.Bindings.Keys[S][A][K];
				FString Name = Key.IsValid() ? Key.GetDisplayName(false).ToString() : FString(TEXT("-"));
				if (CaptureAction == A && CaptureSlot == K)
				{
					Name = TEXT("press a key...");
				}
				Out += (K == CaptureSlot ? TEXT("[") + Name + TEXT("]") : Name) + (K == 0 ? TEXT("   ") : TEXT(""));
			}
			return Out;
		};
		I.Change = [this](int32) { CaptureSlot = 1 - CaptureSlot; };
		I.Activate = [this, A] {
			CaptureAction = A;
			RouterPtr->BeginCapture(BindingSet);
		};
		I.Hint = TEXT("Confirm to rebind; left/right picks the primary or alternate key. Escape or Options cancels.");
		Menu.Add(I);
	}
	Menu.Add(Button(TEXT("Back"), [this] { SaveSettings(); SettingsPage = 1; GoTo(EEHScreen::Settings); }));
}

void AEHGameDirector::BeginSelect(EEHMode InMode)
{
	Mode = InMode;
	SelectStage = 0;
	SelectLocked[0] = SelectLocked[1] = false;
	SelectCursor[0] = 0;
	SelectCursor[1] = 1;
	SelectDevice[0] = (InMode == EEHMode::Versus) ? EHDeviceNone : PrimaryDevice;
	SelectDevice[1] = EHDeviceNone;
	bPlayerOnRight = false;
	GoTo(EEHScreen::Select);
}

void AEHGameDirector::HandleSelectNav(const FEHNavEvent& E)
{
	const bool bBack = E.Action == EEHAction::Heavy || E.Action == EEHAction::Pause;
	const bool bOk = E.Action == EEHAction::Light;
	const int32 Dir = E.Action == EEHAction::Left ? -1 : (E.Action == EEHAction::Right ? 1 : 0);
	if (Mode == EEHMode::Versus)
	{
		int32 Slot = SelectDevice[0] == E.Device ? 0 : (SelectDevice[1] == E.Device ? 1 : -1);
		if (Slot < 0)
		{
			if (bOk)
			{
				Slot = SelectDevice[0] == EHDeviceNone ? 0 : (SelectDevice[1] == EHDeviceNone ? 1 : -1);
				if (Slot >= 0)
				{
					SelectDevice[Slot] = E.Device;
					Audio.Play(TEXT("UiConfirm"), EEHSoundCat::Ui);
				}
			}
			else if (bBack && SelectDevice[0] == EHDeviceNone && SelectDevice[1] == EHDeviceNone)
			{
				GoTo(EEHScreen::Main);
			}
			return;
		}
		if (Dir != 0 && !SelectLocked[Slot])
		{
			SelectCursor[Slot] = (SelectCursor[Slot] + Dir + 2) % 2;
			Audio.Play(TEXT("UiMove"), EEHSoundCat::Ui);
		}
		else if (bOk)
		{
			if (!SelectLocked[Slot])
			{
				SelectLocked[Slot] = true;
				Audio.Play(TEXT("UiConfirm"), EEHSoundCat::Ui);
			}
			else if (SelectLocked[0] && SelectLocked[1])
			{
				for (int32 i = 0; i < 2; ++i)
				{
					SlotCpu[i] = false;
					SlotDevice[i] = SelectDevice[i];
					SlotChar[i] = SelectCursor[i];
				}
				StartMatch();
			}
		}
		else if (bBack)
		{
			if (SelectLocked[Slot])
			{
				SelectLocked[Slot] = false;
			}
			else
			{
				SelectDevice[Slot] = EHDeviceNone;
				if (SelectDevice[0] == EHDeviceNone && SelectDevice[1] == EHDeviceNone)
				{
					GoTo(EEHScreen::Main);
				}
			}
			Audio.Play(TEXT("UiBack"), EEHSoundCat::Ui);
		}
		return;
	}

	// Single-player flows are driven by the device that entered the screen.
	if (E.Device != SelectDevice[0])
	{
		return;
	}
	const int32 Stages = (Mode == EEHMode::Tutorial) ? 1 : (Mode == EEHMode::Training ? 2 : 3);
	if (bBack)
	{
		Audio.Play(TEXT("UiBack"), EEHSoundCat::Ui);
		if (SelectStage == 0)
		{
			GoTo(EEHScreen::Main);
		}
		else
		{
			--SelectStage;
		}
		return;
	}
	if (SelectStage < 2)
	{
		if (Dir != 0)
		{
			SelectCursor[SelectStage] = (SelectCursor[SelectStage] + Dir + 2) % 2;
			Audio.Play(TEXT("UiMove"), EEHSoundCat::Ui);
		}
	}
	else
	{
		if (E.Action == EEHAction::Up || E.Action == EEHAction::Down)
		{
			MenuIndex = 1 - MenuIndex;
			Audio.Play(TEXT("UiMove"), EEHSoundCat::Ui);
		}
		else if (Dir != 0)
		{
			if (MenuIndex == 0)
			{
				CpuLevel = FMath::Clamp(CpuLevel + Dir, 0, 2);
			}
			else
			{
				bPlayerOnRight = !bPlayerOnRight;
			}
			Audio.Play(TEXT("UiMove"), EEHSoundCat::Ui);
		}
	}
	if (!bOk)
	{
		return;
	}
	Audio.Play(TEXT("UiConfirm"), EEHSoundCat::Ui);
	if (Mode == EEHMode::Tutorial)
	{
		SelectCursor[1] = 1 - SelectCursor[0];
	}
	if (SelectStage + 1 < Stages)
	{
		++SelectStage;
		MenuIndex = 0;
		return;
	}
	const int32 Human = (Mode == EEHMode::VersusCpu && bPlayerOnRight) ? 1 : 0;
	SlotCpu[Human] = false;
	SlotCpu[1 - Human] = true;
	SlotDevice[Human] = SelectDevice[0];
	SlotDevice[1 - Human] = EHDeviceNone;
	SlotChar[Human] = SelectCursor[0];
	SlotChar[1 - Human] = SelectCursor[1];
	if (Mode == EEHMode::Training || Mode == EEHMode::Tutorial)
	{
		Dummy = eh::DummyMode::Stand;
	}
	StartMatch();
}

void AEHGameDirector::HandleMenuNav(const FEHNavEvent& E)
{
	if (MenuOwner != EHDeviceNone && E.Device != MenuOwner)
	{
		return;
	}
	if (Menu.Num() == 0)
	{
		return;
	}
	MenuIndex = FMath::Clamp(MenuIndex, 0, Menu.Num() - 1);
	switch (E.Action)
	{
	case EEHAction::Up:
	case EEHAction::Down:
	{
		const int32 Step = E.Action == EEHAction::Up ? -1 : 1;
		for (int32 Guard = 0; Guard < Menu.Num(); ++Guard)
		{
			MenuIndex = (MenuIndex + Step + Menu.Num()) % Menu.Num();
			if (!Menu[MenuIndex].bHeader)
			{
				break;
			}
		}
		Audio.Play(TEXT("UiMove"), EEHSoundCat::Ui, 0.6f);
		break;
	}
	case EEHAction::Left:
	case EEHAction::Right:
		if (Menu[MenuIndex].Change)
		{
			Menu[MenuIndex].Change(E.Action == EEHAction::Left ? -1 : 1);
			Audio.Play(TEXT("UiMove"), EEHSoundCat::Ui, 0.6f);
		}
		break;
	case EEHAction::Light:
		if (E.bRepeat)
		{
			break;
		}
		Audio.Play(TEXT("UiConfirm"), EEHSoundCat::Ui, 0.8f);
		if (Menu[MenuIndex].Activate)
		{
			TFunction<void()> Fn = Menu[MenuIndex].Activate;   // the menu may be rebuilt inside
			Fn();
		}
		else if (Menu[MenuIndex].Change)
		{
			Menu[MenuIndex].Change(1);
		}
		break;
	case EEHAction::Heavy:
	case EEHAction::Pause:
		Audio.Play(TEXT("UiBack"), EEHSoundCat::Ui, 0.8f);
		if (Screen == EEHScreen::Match && bPaused)
		{
			SetPaused(false, EHDeviceNone);
		}
		else if (Screen == EEHScreen::Settings)
		{
			if (SettingsPage == 0)
			{
				Menu.Last().Activate();
			}
			else
			{
				if (SettingsPage == 2)
				{
					Settings = FEHSettings::Load();
				}
				SaveSettings();
				BuildSettingsMenu(0);
			}
		}
		else if (Screen == EEHScreen::Bindings)
		{
			Menu.Last().Activate();
		}
		else if (Screen == EEHScreen::QuitConfirm)
		{
			GoTo(EEHScreen::Main);
		}
		else if (Screen == EEHScreen::Main && E.Action == EEHAction::Heavy)
		{
			GoTo(EEHScreen::QuitConfirm);
		}
		else if (Screen == EEHScreen::DisplayConfirm)
		{
			Menu.Last().Activate();
		}
		break;
	default:
		break;
	}
}

void AEHGameDirector::HandleMatchNav(const FEHNavEvent& E)
{
	if (bPaused)
	{
		// A disconnected player's slot can be taken over by any free device pressing confirm.
		if (!DisconnectNotice.IsEmpty() && E.Action == EEHAction::Light && E.Device != SlotDevice[0] && E.Device != SlotDevice[1])
		{
			for (int32 i = 0; i < 2; ++i)
			{
				const FEHDevice* D = RouterPtr->FindDevice(SlotDevice[i]);
				if (!SlotCpu[i] && (D == nullptr || !D->bConnected))
				{
					SlotDevice[i] = E.Device;
					ShowToast(FString::Printf(TEXT("Player %d is now using %s"), i + 1, *RouterPtr->FindDevice(E.Device)->Name));
				}
			}
			DisconnectNotice.Reset();
			PauseOwner = E.Device;
			BuildPauseMenu();
			return;
		}
		if (DisconnectNotice.IsEmpty())
		{
			HandleMenuNav(E);
		}
		return;
	}
	const bool bPlayerDevice = (!SlotCpu[0] && E.Device == SlotDevice[0]) || (!SlotCpu[1] && E.Device == SlotDevice[1]);
	if (E.Action == EEHAction::Pause && !E.bRepeat && (bPlayerDevice || Mode != EEHMode::Versus))
	{
		SetPaused(true, E.Device);
	}
	else if (E.Action == EEHAction::Reset && Mode == EEHMode::Training && bPlayerDevice && !E.bRepeat)
	{
		Match->TrainingResetPositions(TrainingLayout);
		for (int32 i = 0; i < 2; ++i)
		{
			PrevX[i] = Match->State().f[i].x;
		}
		Vfx->Ripple(FVector::ZeroVector, 0.5f);
	}
	else if (Mode == EEHMode::Tutorial && LessonStep >= Lesson.Num() - 1 && E.Action == EEHAction::Light && bPlayerDevice && LessonDoneAge > 1.0f)
	{
		LeaveMatch(EEHScreen::Main);
	}
}

void AEHGameDirector::HandleNav()
{
	if (Screen == EEHScreen::DisplayConfirm)
	{
		DisplayConfirmLeft -= GetWorld()->GetDeltaSeconds();
		if (DisplayConfirmLeft <= 0.0f)
		{
			Menu.Last().Activate();   // revert
			return;
		}
	}
	if (Screen == EEHScreen::Bindings && CaptureAction >= 0)
	{
		FKey Key;
		bool bCancelled = false;
		if (RouterPtr->TakeCaptured(Key, bCancelled))
		{
			if (!bCancelled)
			{
				const FString Report = Settings.Bindings.Assign(BindingSet, static_cast<EEHAction>(CaptureAction), CaptureSlot, Key);
				SaveSettings();
				ShowToast(Report.IsEmpty() ? FString::Printf(TEXT("%s set to %s"), EHActionName(static_cast<EEHAction>(CaptureAction)), *Key.GetDisplayName(false).ToString()) : Report);
			}
			CaptureAction = -1;
		}
		return;
	}
	FEHNavEvent E;
	while (RouterPtr->PopNav(E))
	{
		switch (Screen)
		{
		case EEHScreen::Error:
			if (E.Action == EEHAction::Light || E.Action == EEHAction::Pause)
			{
				UKismetSystemLibrary::QuitGame(this, GetWorld()->GetFirstPlayerController(), EQuitPreference::Quit, false);
			}
			break;
		case EEHScreen::Title:
			if (ScreenAge > 0.5f && !E.bRepeat)
			{
				PrimaryDevice = E.Device;
				Audio.Play(TEXT("UiConfirm"), EEHSoundCat::Ui);
				GoTo(EEHScreen::Main);
			}
			break;
		case EEHScreen::Select:
			HandleSelectNav(E);
			break;
		case EEHScreen::Match:
			HandleMatchNav(E);
			break;
		case EEHScreen::MoveList:
			if (E.Action == EEHAction::Left || E.Action == EEHAction::Right)
			{
				SelectCursor[0] = 1 - SelectCursor[0];
				Audio.Play(TEXT("UiMove"), EEHSoundCat::Ui, 0.6f);
			}
			else if (E.Action == EEHAction::Heavy || E.Action == EEHAction::Pause || E.Action == EEHAction::Light)
			{
				Audio.Play(TEXT("UiBack"), EEHSoundCat::Ui, 0.8f);
				if (SettingsReturn == EEHScreen::Match)
				{
					Screen = EEHScreen::Match;
					BuildPauseMenu();
				}
				else
				{
					GoTo(EEHScreen::Main);
				}
			}
			break;
		case EEHScreen::Credits:
			if (E.Action == EEHAction::Heavy || E.Action == EEHAction::Pause || E.Action == EEHAction::Light)
			{
				GoTo(EEHScreen::Main);
			}
			break;
		default:
			if (Screen == EEHScreen::Main)
			{
				PrimaryDevice = E.Device;
			}
			HandleMenuNav(E);
			break;
		}
		if (Screen == EEHScreen::Bindings && CaptureAction >= 0)
		{
			break;   // the next press belongs to the rebinding capture
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------
// Interactive lesson. The partner (slot 1) runs a short script per step; goals are checked against combat events.

void AEHGameDirector::SetupLesson()
{
	Lesson.Reset();
	Lesson.Add({TEXT("Movement"), TEXT("Walk toward your opponent, then away. Movement is separate from the six actions."), 2});
	Lesson.Add({TEXT("Light"), TEXT("Light is fast and safe. Press it three times to run your short string."), 1});
	Lesson.Add({TEXT("Heavy"), TEXT("Heavy reaches further and hits harder, but a miss leaves you open. Land one."), 1});
	Lesson.Add({TEXT("Block"), TEXT("Hold Block to stop strikes. You cannot move while blocking. Block three strikes."), 3});
	Lesson.Add({TEXT("Timed block"), TEXT("Press Block just before a strike lands to deflect it and recover sooner. Mashing does not work."), 1});
	Lesson.Add({TEXT("Grab"), TEXT("Blocking stops strikes but not grabs. Grab your guarding opponent up close."), 1});
	Lesson.Add({TEXT("Escape"), TEXT("When you are grabbed, press Grab straight away to break free."), 1});
	Lesson.Add({TEXT("Punish"), TEXT("Block or dodge the heavy kick, then hit back while it recovers."), 1});
	Lesson.Add({TEXT("Special"), TEXT("Special changes with direction: neutral, toward, and away (which spends gauge). Use all three."), 3});
	Lesson.Add({TEXT("Lesson complete"), TEXT("Strikes beat grabs, grabs beat blocks, blocks beat strikes, and dodges beat everything you read correctly."), 1});
	LessonStep = 0;
	LessonCount = 0;
	LessonDoneAge = -1.0f;
	ScriptTimer = 0;
}

void AEHGameDirector::UpdateLesson(const eh::Event& E)
{
	if (LessonStep >= Lesson.Num() - 1 || LessonDoneAge >= 0.0f)
	{
		return;
	}
	const FString Move = (E.player == 0) ? EHMoveId(*Match, 0, E.move) : FString();
	bool bProgress = false;
	switch (LessonStep)
	{
	case 1: bProgress = E.type == eh::EventType::MoveStart && E.player == 0 && Move == TEXT("L3"); break;
	case 2: bProgress = E.type == eh::EventType::Hit && E.player == 0 && (Move == TEXT("H") || Move == TEXT("FH")); break;
	case 3: bProgress = (E.type == eh::EventType::Block || E.type == eh::EventType::Deflect) && E.player == 1; break;
	case 4: bProgress = E.type == eh::EventType::Deflect && E.player == 1; break;
	case 5: bProgress = E.type == eh::EventType::ThrowConnect && E.player == 0; break;
	case 6: bProgress = E.type == eh::EventType::ThrowTech; break;
	case 7: bProgress = E.type == eh::EventType::Hit && E.player == 0 && (E.flags & eh::EvPunish); break;
	case 8:
		if (E.type == eh::EventType::MoveStart && E.player == 0 && (Move == TEXT("S") || Move == TEXT("FS") || Move == TEXT("BS")))
		{
			static const TCHAR* Order[] = {TEXT("S"), TEXT("FS"), TEXT("BS")};
			bProgress = LessonCount < 3 && Move == Order[LessonCount];
		}
		break;
	default:
		break;
	}
	if (bProgress)
	{
		++LessonCount;
		Audio.Play(TEXT("UiConfirm"), EEHSoundCat::Ui, 0.7f);
	}
}

eh::InputFrame AEHGameDirector::LessonScriptInput()
{
	eh::InputFrame In;
	const eh::MatchState& S = Match->State();
	// Step completion and advancement happen here because some goals are states, not events.
	if (LessonStep == 0 && S.f[0].state == eh::FState::Neutral && S.f[0].walk != 0)
	{
		if (S.f[0].walk != LessonWalkDir)
		{
			LessonWalkDir = S.f[0].walk;
			++LessonCount;
		}
	}
	if (LessonDoneAge < 0.0f && LessonStep < Lesson.Num() - 1 && LessonCount >= Lesson[LessonStep].Goal)
	{
		LessonDoneAge = 0.0f;
	}
	if (LessonDoneAge >= 0.0f)
	{
		LessonDoneAge += 1.0f / eh::kTickHz;
		if (LessonDoneAge > 1.2f && LessonStep < Lesson.Num() - 1)
		{
			++LessonStep;
			LessonCount = 0;
			LessonDoneAge = LessonStep == Lesson.Num() - 1 ? 0.0f : -1.0f;
			ScriptTimer = 0;
			Match->TrainingResetPositions(0);
			Audio.Play(TEXT("RoundBell"), EEHSoundCat::Effects, 0.5f);
		}
	}
	++ScriptTimer;
	const eh::FighterState& Me = S.f[1];
	const eh::FighterState& You = S.f[0];
	const int32 Gap = FMath::Abs(You.x - Me.x);
	const int8 Toward = static_cast<int8>(You.x > Me.x ? 1 : -1);
	const int32 Cm = eh::kUnitsPerCm;
	auto Approach = [&](int32 Range) { if (Gap > Range) In.x = Toward; };
	switch (LessonStep)
	{
	case 3:
		Approach(105 * Cm);
		if (Gap <= 110 * Cm && ScriptTimer % 70 == 0) In.pressed = eh::BtnLight;
		break;
	case 4:
		Approach(150 * Cm);
		if (Gap <= 160 * Cm && ScriptTimer % 100 == 0) In.pressed = eh::BtnHeavy;
		break;
	case 5:
		In.held = eh::BtnBlock;
		break;
	case 6:
		Approach(60 * Cm);
		if (Gap <= 75 * Cm && ScriptTimer % 90 == 0) In.pressed = eh::BtnThrow;
		break;
	case 7:
		Approach(150 * Cm);
		if (Gap <= 160 * Cm && ScriptTimer % 95 == 0) In.pressed = eh::BtnHeavy;
		break;
	default:
		break;
	}
	In.held |= In.pressed;
	return In;
}
