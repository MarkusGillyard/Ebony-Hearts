// Scripted evaluation runs for the packaged game: -EHAuto=<script> [-EHEvidence=<dir>].
// Menu steps go through FEHInputRouter exactly like a device press; bot-driven players feed their decisions
// into the router too, so matches exercise the same sampling path as a keyboard or gamepad.
#include "EHGameDirector.h"

#include "AudioDevice.h"
#include "AudioMixerDevice.h"
#include "DynamicRHI.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "HAL/FileManager.h"
#include "EHFighterVisual.h"
#include "EHVfx.h"
#include "HAL/PlatformMemory.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/DateTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "RenderTimer.h"
#include "UnrealClient.h"
#include "Widgets/SWindow.h"
#if EH_LINUX_PLATFORM
#include "EHLinuxPlatform.h"
#endif

namespace EHAutoDetail
{
struct FLoopFrame
{
	int32 StartLine = 0;
	int32 Remaining = 0;
};
TArray<FLoopFrame> Loops;
TArray<TPair<int32, FKey>> PendingRelease;
float StepTimer = 0.0f;
int32 StuckFrames[2] = {0, 0};
int32 LastStateKey[2] = {-1, -1};
TArray<float> GpuTimes;
TArray<float> GameTimes;
TArray<float> RenderTimes;

// Accepts the short name ("Light", "Grab"), the stable id ("LightAttack") or the label ("Light attack").
EEHAction ParseAction(const FString& S)
{
	for (int32 A = 0; A < EHActionCount; ++A)
	{
		const EEHAction Act = static_cast<EEHAction>(A);
		if (S.Equals(EHActionName(Act), ESearchCase::IgnoreCase) || S.Equals(EHActionId(Act), ESearchCase::IgnoreCase) ||
			S.Equals(EHActionLabel(Act), ESearchCase::IgnoreCase) || (Act == EEHAction::Throw && S.Equals(TEXT("Throw"), ESearchCase::IgnoreCase)))
		{
			return Act;
		}
	}
	return EEHAction::Count;
}

EEHNav ParseNav(const FString& S)
{
	for (int32 N = 0; N < EHNavCount; ++N)
	{
		if (S.Equals(EHNavName(static_cast<EEHNav>(N)), ESearchCase::IgnoreCase))
		{
			return static_cast<EEHNav>(N);
		}
	}
	return EEHNav::Count;
}

EEHBindingSet ParseSet(const FString& S)
{
	for (int32 i = 0; i < EHSetCount; ++i)
	{
		if (S.Equals(EHSetId(static_cast<EEHBindingSet>(i)), ESearchCase::IgnoreCase))
		{
			return static_cast<EEHBindingSet>(i);
		}
	}
	return EEHBindingSet::Count;
}

int32 ParseDevice(const FString& S)
{
	if (S == TEXT("kbA")) return EHDeviceKeyboardA;
	if (S == TEXT("kbB")) return EHDeviceKeyboardB;
	if (S.StartsWith(TEXT("pad")))
	{
		return EHDeviceGamepadBase + FCString::Atoi(*S.RightChop(3));
	}
	return EHDeviceKeyboardA;
}

const TCHAR* KindName(EEHDeviceKind K)
{
	switch (K)
	{
	case EEHDeviceKind::PlayStation: return TEXT("playstation");
	case EEHDeviceKind::Xbox: return TEXT("xbox");
	case EEHDeviceKind::Gamepad: return TEXT("generic");
	default: return TEXT("keyboard");
	}
}

float Percentile(TArray<float> Values, float P)
{
	if (Values.Num() == 0)
	{
		return 0.0f;
	}
	Values.Sort();
	const int32 Index = FMath::Clamp(FMath::FloorToInt(P * (Values.Num() - 1)), 0, Values.Num() - 1);
	return Values[Index];
}
}
using namespace EHAutoDetail;

void AEHGameDirector::InitAutomation()
{
	FString ScriptPath;
	if (!FParse::Value(FCommandLine::Get(), TEXT("EHAuto="), ScriptPath))
	{
		return;
	}
	if (FPaths::IsRelative(ScriptPath))
	{
		ScriptPath = FPaths::Combine(FPaths::ProjectDir(), ScriptPath);
	}
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *ScriptPath))
	{
		UE_LOG(LogTemp, Error, TEXT("EbonyHearts automation: cannot read %s"), *ScriptPath);
		return;
	}
	Text.ParseIntoArrayLines(AutoLines);
	if (!FParse::Value(FCommandLine::Get(), TEXT("EHEvidence="), EvidenceDir))
	{
		EvidenceDir = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EbonyHearts"), TEXT("Evidence"), FDateTime::UtcNow().ToString(TEXT("%Y%m%d-%H%M%S")));
	}
	if (!IFileManager::Get().MakeDirectory(*EvidenceDir, true))
	{
		UE_LOG(LogTemp, Error, TEXT("EbonyHearts automation: cannot create evidence directory %s"), *EvidenceDir);
		AutoLines.Empty();
		EvidenceDir.Empty();
		return;
	}
	AutoStart = FPlatformTime::Seconds();
	AutoLogLine(FString::Printf(TEXT("auto start script=%s lines=%d"), *ScriptPath, AutoLines.Num()));
}

void AEHGameDirector::AutoLogLine(const FString& Line)
{
	if (EvidenceDir.IsEmpty())
	{
		return;
	}
	const double T = FPlatformTime::Seconds() - AutoStart;
	const FString Stamped = FString::Printf(TEXT("[%9.3f] %s"), T, *Line);
	AutoLog.Add(Stamped);
	UE_LOG(LogTemp, Display, TEXT("EHAUTO %s"), *Stamped);
	if (!FFileHelper::SaveStringToFile(Stamped + LINE_TERMINATOR, *FPaths::Combine(EvidenceDir, TEXT("auto_log.txt")), FFileHelper::EEncodingOptions::AutoDetect, &IFileManager::Get(), FILEWRITE_Append))
	{
		UE_LOG(LogTemp, Error, TEXT("EbonyHearts automation: cannot append auto_log.txt in %s"), *EvidenceDir);
	}
}

void AEHGameDirector::WriteEvidence(const FString& Name, const FString& Text)
{
	if (!EvidenceDir.IsEmpty())
	{
		if (!FFileHelper::SaveStringToFile(Text, *FPaths::Combine(EvidenceDir, Name)))
		{
			UE_LOG(LogTemp, Error, TEXT("EbonyHearts automation: cannot write %s in %s"), *Name, *EvidenceDir);
		}
	}
}

bool AEHGameDirector::AutoKey(int32 Device, const FString& Name, FKey& OutKey) const
{
	// key:<name> presses a raw key; Left/Right are menu directions off the match screen and movement on it.
	if (Name.StartsWith(TEXT("key:")))
	{
		OutKey = FKey(FName(*Name.RightChop(4)));
		return OutKey.IsValid();
	}
	const EEHBindingSet Set = RouterPtr->SetFor(Device);
	const EEHBindingSet MenuClass = EHIsKeyboardSet(Set) ? Set : EEHBindingSet::GamepadP1;
	const EEHNav N = ParseNav(Name);
	const EEHAction A = ParseAction(Name);
	if (N != EEHNav::Count && (A == EEHAction::Count || Screen != EEHScreen::Match))
	{
		OutKey = EHMenuKey(MenuClass, N);
		return OutKey.IsValid();
	}
	if (A != EEHAction::Count)
	{
		OutKey = Settings.Bindings.First(Set, A);
		return OutKey.IsValid();
	}
	return false;
}

void AEHGameDirector::AutoInject(int32 Device, const FKey& Key)
{
	RouterPtr->InjectKey(Device, Key, true);
	PendingRelease.Add(TPair<int32, FKey>(Device, Key));
}

void AEHGameDirector::AutoReleaseBots()
{
	// Injected presses stay held in the router until released; drop them before slots or devices change hands, so a
	// key a bot held when its match ended cannot carry into the next one.
	for (int32 i = 0; i < 2; ++i)
	{
		for (int32 A = 0; A < EHActionCount; ++A)
		{
			if (AutoBotHeld[i] & (1u << A))
			{
				RouterPtr->InjectAction(SlotDevice[i], static_cast<EEHAction>(A), false);
			}
		}
		AutoBotHeld[i] = 0;
		bAutoBot[i] = false;
	}
}

eh::InputFrame AEHGameDirector::AutoBotInput(int32 Player)
{
	// The bot decides like the CPU, but its decision is applied as device presses and read back through the router.
	const eh::InputFrame Want = AutoBot[Player].Decide(*Match);
	const int32 Device = SlotDevice[Player];
	auto Apply = [&](EEHAction A, bool bHeld, bool bPressed) {
		const uint32 Bit = 1u << static_cast<uint32>(A);
		const bool bWas = (AutoBotHeld[Player] & Bit) != 0;
		if (bPressed && bWas)
		{
			RouterPtr->InjectAction(Device, A, false);
		}
		if (bHeld != bWas || bPressed)
		{
			RouterPtr->InjectAction(Device, A, bHeld || bPressed);
		}
		AutoBotHeld[Player] = (bHeld || bPressed) ? (AutoBotHeld[Player] | Bit) : (AutoBotHeld[Player] & ~Bit);
	};
	Apply(EEHAction::Left, Want.x < 0, false);
	Apply(EEHAction::Right, Want.x > 0, false);
	Apply(EEHAction::Jump, Want.y > 0, false);
	Apply(EEHAction::Down, Want.y < 0, false);
	Apply(EEHAction::Light, (Want.held & eh::BtnLight) != 0, (Want.pressed & eh::BtnLight) != 0);
	Apply(EEHAction::Heavy, (Want.held & eh::BtnHeavy) != 0, (Want.pressed & eh::BtnHeavy) != 0);
	Apply(EEHAction::Special, (Want.held & eh::BtnSpecial) != 0, (Want.pressed & eh::BtnSpecial) != 0);
	Apply(EEHAction::Throw, (Want.held & eh::BtnThrow) != 0, (Want.pressed & eh::BtnThrow) != 0);
	Apply(EEHAction::Dodge, (Want.held & eh::BtnDodge) != 0, (Want.pressed & eh::BtnDodge) != 0);
	Apply(EEHAction::Block, (Want.held & eh::BtnBlock) != 0, (Want.pressed & eh::BtnBlock) != 0);
	RouterPtr->ClearNav();   // bot presses must not drive menus
	const eh::InputFrame Got = RouterPtr->SampleForTick(Device);
	// Release momentary presses so the next tick starts from the bot's held state.
	for (EEHAction A : {EEHAction::Light, EEHAction::Heavy, EEHAction::Special, EEHAction::Throw, EEHAction::Dodge})
	{
		const uint32 Bit = 1u << static_cast<uint32>(A);
		if ((AutoBotHeld[Player] & Bit) && !(Want.held & (A == EEHAction::Light ? eh::BtnLight : A == EEHAction::Heavy ? eh::BtnHeavy : A == EEHAction::Special ? eh::BtnSpecial : A == EEHAction::Throw ? eh::BtnThrow : eh::BtnDodge)))
		{
			RouterPtr->InjectAction(Device, A, false);
			AutoBotHeld[Player] &= ~Bit;
		}
	}
	if (Got.pressed != Want.pressed || Got.x != Want.x || Got.y != Want.y)
	{
		AutoLogLine(FString::Printf(TEXT("WARN router mismatch p%d want(x=%d y=%d p=%d) got(x=%d y=%d p=%d)"), Player, Want.x, Want.y, Want.pressed, Got.x, Got.y, Got.pressed));
	}
	return Got;
}

void AEHGameDirector::TickAutomation(float DeltaSeconds)
{
	for (const TPair<int32, FKey>& R : PendingRelease)
	{
		RouterPtr->InjectKey(R.Key, R.Value, false);
	}
	PendingRelease.Reset();
	if (InputLogLeft > 0.0f)
	{
		// Held gameplay actions per controller, so trigger holds and releases show up in the log.
		InputLogLeft -= DeltaSeconds;
		for (const TPair<int32, FEHDevice>& Pair : RouterPtr->Devices())
		{
			const uint32 Was = InputLogHeld.FindRef(Pair.Key);
			if (Pair.Value.Held != Was)
			{
				for (int32 A = 0; A < EHActionCount; ++A)
				{
					const uint32 Bit = 1u << A;
					if ((Pair.Value.Held ^ Was) & Bit)
					{
						AutoLogLine(FString::Printf(TEXT("held dev=%d kind=%s %s%s"), Pair.Key, KindName(Pair.Value.Kind), (Pair.Value.Held & Bit) ? TEXT("+") : TEXT("-"), EHActionName(static_cast<EEHAction>(A))));
					}
				}
				InputLogHeld.Add(Pair.Key, Pair.Value.Held);
			}
		}
	}
	if (AutoLines.Num() == 0)
	{
		return;
	}
#if !UE_BUILD_SHIPPING
	if (AudioProbeLeft > 0.0f)
	{
		TickAudioProbe(DeltaSeconds);
	}
#endif
	if (bRecordFrames)
	{
		GpuTimes.Add(FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles()));
		GameTimes.Add(FPlatformTime::ToMilliseconds(GGameThreadTime));
		RenderTimes.Add(FPlatformTime::ToMilliseconds(GRenderThreadTime));
	}
	// Watchdog: a fighter frozen in one non-neutral state for 10 s during a running match is reported.
	if (bMatchActive && Screen == EEHScreen::Match && !bPaused)
	{
		for (int32 i = 0; i < 2; ++i)
		{
			const eh::FighterState& F = Match->State().f[i];
			const int32 Key = static_cast<int32>(F.state) * 1000 + F.move;
			const bool bSettled = F.state == eh::FState::Neutral || F.state == eh::FState::Guard || F.state == eh::FState::KO || F.state == eh::FState::Win || F.state == eh::FState::Defeated;
			StuckFrames[i] = (Key == LastStateKey[i] && !bSettled) ? StuckFrames[i] + 1 : 0;
			LastStateKey[i] = Key;
			if (StuckFrames[i] == 600)
			{
				AutoLogLine(FString::Printf(TEXT("FAIL stuck p%d state=%s"), i, UTF8_TO_TCHAR(eh::StateName(F.state))));
			}
		}
	}
	if (AutoWait > 0.0f)
	{
		AutoWait -= DeltaSeconds;
		return;
	}
	StepTimer += DeltaSeconds;
	for (int32 Guard = 0; Guard < 32 && AutoLine < AutoLines.Num(); ++Guard)
	{
		const FString Line = AutoLines[AutoLine].TrimStartAndEnd();
		TArray<FString> T;
		Line.ParseIntoArrayWS(T);
		if (T.Num() == 0 || T[0].StartsWith(TEXT("#")))
		{
			++AutoLine;
			continue;
		}
		const FString& Cmd = T[0];
		auto Arg = [&T](int32 i, const TCHAR* Default) { return T.IsValidIndex(i) ? T[i] : FString(Default); };
		if (Cmd == TEXT("wait"))
		{
			AutoWait = FCString::Atof(*Arg(1, TEXT("1")));
			++AutoLine;
			StepTimer = 0.0f;
			return;
		}
		if (Cmd == TEXT("wait_screen") || Cmd == TEXT("wait_results"))
		{
			const int32 Want = Cmd == TEXT("wait_results") ? static_cast<int32>(EEHScreen::Results) : FCString::Atoi(*Arg(1, TEXT("0")));
			const float Timeout = FCString::Atof(*Arg(Cmd == TEXT("wait_results") ? 1 : 2, TEXT("600")));
			if (static_cast<int32>(Screen) == Want)
			{
				AutoLogLine(FString::Printf(TEXT("ok %s after %.1fs"), *Line, StepTimer));
				StepTimer = 0.0f;
				++AutoLine;
				continue;
			}
			if (StepTimer > Timeout)
			{
				AutoLogLine(FString::Printf(TEXT("FAIL timeout %s (screen=%d)"), *Line, static_cast<int32>(Screen)));
				StepTimer = 0.0f;
				++AutoLine;
				continue;
			}
			return;
		}
		++AutoLine;
		StepTimer = 0.0f;
		if (Cmd == TEXT("log"))
		{
			AutoLogLine(Line.RightChop(4));
		}
		else if (Cmd == TEXT("press"))
		{
			// press <device> <action|menu command|key:Name>: the device's key for it, through the real input path.
			const int32 Device = ParseDevice(Arg(1, TEXT("kbA")));
			FKey Key;
			if (AutoKey(Device, Arg(2, TEXT("Light")), Key))
			{
				AutoInject(Device, Key);
			}
			AutoLogLine(FString::Printf(TEXT("%spress %s %s key=%s screen=%d"), Key.IsValid() ? TEXT("") : TEXT("FAIL "), *Arg(1, TEXT("kbA")), *Arg(2, TEXT("Light")), *Key.ToString(), static_cast<int32>(Screen)));
			AutoWait = 0.12f;
			return;
		}
		else if (Cmd == TEXT("hold") || Cmd == TEXT("release"))
		{
			// hold/release <device> <action|key:Name>: a held direction or Block, for direction + button moves.
			const int32 Device = ParseDevice(Arg(1, TEXT("kbA")));
			FKey Key;
			if (AutoKey(Device, Arg(2, TEXT("Right")), Key))
			{
				RouterPtr->InjectKey(Device, Key, Cmd == TEXT("hold"));
			}
			AutoLogLine(FString::Printf(TEXT("%s%s %s %s key=%s"), Key.IsValid() ? TEXT("") : TEXT("FAIL "), *Cmd, *Arg(1, TEXT("kbA")), *Arg(2, TEXT("Right")), *Key.ToString()));
		}
		else if (Cmd == TEXT("axis"))
		{
			// axis <pad> <Gamepad_RightTriggerAxis|Gamepad_LeftX|...> <value>
			RouterPtr->InjectAnalog(ParseDevice(Arg(1, TEXT("pad0"))), FKey(FName(*Arg(2, TEXT("Gamepad_RightTriggerAxis")))), FCString::Atof(*Arg(3, TEXT("0"))));
			AutoLogLine(FString::Printf(TEXT("axis %s %s %s"), *Arg(1, TEXT("pad0")), *Arg(2, TEXT("")), *Arg(3, TEXT("0"))));
		}
		else if (Cmd == TEXT("devices"))
		{
			for (const TPair<int32, FEHDevice>& Pair : RouterPtr->Devices())
			{
				AutoLogLine(FString::Printf(TEXT("device key=%d name=\"%s\" kind=%s connected=%d layout=%s"), Pair.Key, *Pair.Value.Name, KindName(Pair.Value.Kind), Pair.Value.bConnected, EHSetId(RouterPtr->SetFor(Pair.Key))));
			}
			AutoLogLine(FString::Printf(TEXT("prompt kind=%s last_device=%d last_pad=%d"), KindName(PromptKind(EHDeviceNone)), RouterPtr->MostRecentDevice(), RouterPtr->MostRecentGamepad()));
		}
		else if (Cmd == TEXT("expect_kind"))
		{
			// expect_kind <lastpad|kbA|padN> <playstation|xbox|generic|keyboard>: how prompts would be drawn for it.
			const FString Who = Arg(1, TEXT("lastpad"));
			const int32 Device = Who == TEXT("lastpad") ? RouterPtr->MostRecentGamepad() : ParseDevice(Who);
			const FString Got = Device == EHDeviceNone ? FString(TEXT("none")) : FString(KindName(PromptKind(Device)));
			AutoLogLine(FString::Printf(TEXT("%s expect_kind %s %s (is %s)"), Got == Arg(2, TEXT("")) ? TEXT("ok") : TEXT("FAIL"), *Who, *Arg(2, TEXT("")), *Got));
		}
		else if (Cmd == TEXT("prompt_style"))
		{
			const FString V = Arg(1, TEXT("auto"));
			Settings.PromptStyle = V == TEXT("playstation") ? EEHPromptStyle::PlayStation : (V == TEXT("xbox") ? EEHPromptStyle::Xbox : (V == TEXT("keyboard") ? EEHPromptStyle::Keyboard : EEHPromptStyle::Auto));
			AutoLogLine(FString::Printf(TEXT("prompt_style %s"), *V));
		}
		else if (Cmd == TEXT("log_input"))
		{
			InputLogLeft = FCString::Atof(*Arg(1, TEXT("10")));
			InputLogHeld.Reset();
			AutoLogLine(FString::Printf(TEXT("log_input %.1fs"), InputLogLeft));
		}
		else if (Cmd == TEXT("bindings_selftest"))
		{
			RunBindingsSelfTest();
		}
		else if (Cmd == TEXT("input_selftest"))
		{
			RunInputSelfTest();
		}
		else if (Cmd == TEXT("goto_bindings"))
		{
			// goto_bindings <set>: opens that layout's page like Settings > Controls does.
			AutoReleaseBots();
			if (bMatchActive)
			{
				LeaveMatch(EEHScreen::Main);
			}
			SettingsReturn = EEHScreen::Main;
			BindingSet = ParseSet(Arg(1, TEXT("controller1")));
			BindingPage = 0;
			BindingListIndex = 0;
			GoTo(EEHScreen::Bindings);
		}
		else if (Cmd == TEXT("remap"))
		{
			// remap <set> <action> <slot> <key> [swap|replace|cancel]: the Controls screen's capture path, then its
			// conflict choice when the key is taken.
			const EEHBindingSet Set = ParseSet(Arg(1, TEXT("controller1")));
			const EEHAction A = ParseAction(Arg(2, TEXT("Light")));
			const FKey Key(FName(*Arg(4, TEXT(""))));
			if (Set == EEHBindingSet::Count || A == EEHAction::Count || !FEHBindings::IsBindable(Set, Key))
			{
				AutoLogLine(FString::Printf(TEXT("FAIL remap bad arguments or unbindable key: %s"), *Line));
			}
			else
			{
				BindingSet = Set;
				BindingAction = static_cast<int32>(A);
				CaptureSlot = FMath::Clamp(FCString::Atoi(*Arg(3, TEXT("0"))), 0, EHKeysPerAction - 1);
				BindingPage = 1;
				ApplyCapturedKey(Key);
				const FString Choice = Arg(5, TEXT("swap"));
				if (BindingPage == 2)
				{
					if (Choice == TEXT("cancel"))
					{
						BindingPage = 1;
						BuildBindingsMenu(BindingSet);
					}
					else
					{
						ResolveConflict(Choice == TEXT("swap"));
					}
				}
				AutoLogLine(FString::Printf(TEXT("remap %s %s slot %d -> %s (%s): now [%s, %s]"), EHSetId(Set), EHActionId(A), CaptureSlot, *Key.ToString(), *Choice,
					*Settings.Bindings.Get(Set, A, 0).ToString(), *Settings.Bindings.Get(Set, A, 1).ToString()));
			}
		}
		else if (Cmd == TEXT("clear_binding") || Cmd == TEXT("reset_action"))
		{
			const EEHBindingSet Set = ParseSet(Arg(1, TEXT("controller1")));
			const EEHAction A = ParseAction(Arg(2, TEXT("Light")));
			if (Set == EEHBindingSet::Count || A == EEHAction::Count)
			{
				AutoLogLine(FString::Printf(TEXT("FAIL %s bad arguments"), *Cmd));
			}
			else
			{
				if (Cmd == TEXT("clear_binding"))
				{
					Settings.Bindings.Clear(Set, A, FMath::Clamp(FCString::Atoi(*Arg(3, TEXT("0"))), 0, EHKeysPerAction - 1));
				}
				else
				{
					Settings.Bindings.ResetAction(Set, A);
				}
				SaveSettings();
				RouterPtr->ResetHeld();
				AutoLogLine(FString::Printf(TEXT("%s %s %s: now [%s, %s]"), *Cmd, EHSetId(Set), EHActionId(A), *Settings.Bindings.Get(Set, A, 0).ToString(), *Settings.Bindings.Get(Set, A, 1).ToString()));
			}
		}
		else if (Cmd == TEXT("reset_layout"))
		{
			const FString Which = Arg(1, TEXT("all"));
			if (Which == TEXT("all"))
			{
				Settings.Bindings = FEHBindings::Defaults();
			}
			else
			{
				Settings.Bindings.ResetSet(ParseSet(Which));
			}
			SaveSettings();
			RouterPtr->ResetHeld();
			AutoLogLine(FString::Printf(TEXT("reset_layout %s"), *Which));
		}
		else if (Cmd == TEXT("expect_binding"))
		{
			// expect_binding <set> <action> <slot> <key|none>
			const EEHBindingSet Set = ParseSet(Arg(1, TEXT("controller1")));
			const EEHAction A = ParseAction(Arg(2, TEXT("Light")));
			const int32 Slot = FMath::Clamp(FCString::Atoi(*Arg(3, TEXT("0"))), 0, EHKeysPerAction - 1);
			const FString Want = Arg(4, TEXT("none"));
			const FKey Got = (Set == EEHBindingSet::Count || A == EEHAction::Count) ? FKey(EKeys::Invalid) : Settings.Bindings.Get(Set, A, Slot);
			const bool bOk = Want == TEXT("none") ? !Got.IsValid() : Got == FKey(FName(*Want));
			AutoLogLine(FString::Printf(TEXT("%s expect_binding %s %s %d %s (is %s)"), bOk ? TEXT("ok") : TEXT("FAIL"), *Arg(1, TEXT("")), *Arg(2, TEXT("")), Slot, *Want, Got.IsValid() ? *Got.ToString() : TEXT("none")));
		}
		else if (Cmd == TEXT("training_gauge"))
		{
			bInfiniteMeter = Arg(1, TEXT("full")) == TEXT("full");
			AutoLogLine(FString::Printf(TEXT("training gauge %s"), bInfiniteMeter ? TEXT("always full") : TEXT("normal")));
		}
		else if (Cmd == TEXT("expect_screen"))
		{
			const int32 Want = FCString::Atoi(*Arg(1, TEXT("0")));
			AutoLogLine(FString::Printf(TEXT("%s expect_screen %d (is %d)"), static_cast<int32>(Screen) == Want ? TEXT("ok") : TEXT("FAIL"), Want, static_cast<int32>(Screen)));
		}
		else if (Cmd == TEXT("expect_master_volume"))
		{
			const int32 Want = FCString::Atoi(*Arg(1, TEXT("80")));
			AutoLogLine(FString::Printf(TEXT("%s expect_master_volume %d (is %d)"), Settings.MasterVolume == Want ? TEXT("ok") : TEXT("FAIL"), Want, Settings.MasterVolume));
		}
		else if (Cmd == TEXT("match"))
		{
			// match <wren|ashka> <wren|ashka> <cpu|versus|training> <level 0-2> [left|right]; bots must be set again.
			AutoReleaseBots();
			SlotChar[0] = Arg(1, TEXT("wren")) == TEXT("wren") ? 0 : 1;
			SlotChar[1] = Arg(2, TEXT("ashka")) == TEXT("wren") ? 0 : 1;
			const FString M = Arg(3, TEXT("cpu"));
			Mode = M == TEXT("versus") ? EEHMode::Versus : (M == TEXT("training") ? EEHMode::Training : (M == TEXT("lesson") ? EEHMode::Tutorial : EEHMode::VersusCpu));
			CpuLevel = FCString::Atoi(*Arg(4, TEXT("1")));
			SlotCpu[0] = false;
			SlotCpu[1] = Mode != EEHMode::Versus;
			SlotDevice[0] = EHDeviceKeyboardA;
			SlotDevice[1] = Mode == EEHMode::Versus ? EHDeviceKeyboardB : EHDeviceNone;
			if (Arg(5, TEXT("left")) == TEXT("right"))
			{
				Swap(SlotChar[0], SlotChar[1]);
				SlotCpu[0] = SlotCpu[1];
				SlotCpu[1] = false;
				SlotDevice[1] = EHDeviceKeyboardA;
				SlotDevice[0] = Mode == EEHMode::Versus ? EHDeviceKeyboardB : EHDeviceNone;
			}
			StartMatch();
		}
		else if (Cmd == TEXT("bots"))
		{
			AutoReleaseBots();
			for (int32 i = 0; i < 2; ++i)
			{
				const FString L = Arg(1 + i, TEXT("none"));
				bAutoBot[i] = L != TEXT("none") && !SlotCpu[i];
				AutoBotHeld[i] = 0;
				if (bAutoBot[i])
				{
					AutoBot[i].Setup(i, static_cast<eh::CpuLevel>(FMath::Clamp(FCString::Atoi(*L), 0, 2)), 1000u + static_cast<uint32>(AutoMatches) * 31u + static_cast<uint32>(i));
				}
			}
		}
		else if (Cmd == TEXT("results_pick"))
		{
			const int32 Pick = FCString::Atoi(*Arg(1, TEXT("0")));
			if (Screen == EEHScreen::Results && Menu.IsValidIndex(Pick))
			{
				TFunction<void()> Fn = Menu[Pick].Activate;
				Fn();
			}
			else
			{
				AutoLogLine(FString::Printf(TEXT("FAIL results_pick on screen %d"), static_cast<int32>(Screen)));
			}
		}
		else if (Cmd == TEXT("goto_main"))
		{
			AutoReleaseBots();
			if (bMatchActive)
			{
				LeaveMatch(EEHScreen::Main);
			}
			else
			{
				GoTo(EEHScreen::Main);
			}
		}
		else if (Cmd == TEXT("pause"))
		{
			SetPaused(!bPaused, SlotDevice[0]);
		}
		else if (Cmd == TEXT("settings_roundtrip"))
		{
			const FEHSettings Before = Settings;
			Settings.UIScale = 1.2f;
			Settings.MasterVolume = 55;
			Settings.bReduceShake = true;
			Settings.bReduceFlash = true;
			ApplySettings(false);
			const bool bSaved = WriteSettings();
			const FEHSettings Loaded = FEHSettings::Load();
			// Launch-flag display overrides must not reach the file.
			const bool bDisplayKept = !bSessionDisplayOverride || (Loaded.WindowMode == DiskDisplay.WindowMode && Loaded.Resolution == DiskDisplay.Resolution && Loaded.bVSync == DiskDisplay.bVSync);
			const bool bMatches = FMath::IsNearlyEqual(Loaded.UIScale, 1.2f) && Loaded.MasterVolume == 55 && Loaded.bReduceShake && Loaded.bReduceFlash && bDisplayKept;
			Settings = Before;
			ApplySettings(false);
			WriteSettings();
			AutoLogLine(FString::Printf(TEXT("%s settings_roundtrip saved=%d reloaded_match=%d"), bSaved && bMatches ? TEXT("ok") : TEXT("FAIL"), bSaved, bMatches));
		}
		else if (Cmd == TEXT("screenshot"))
		{
			FScreenshotRequest::RequestScreenshot(FPaths::Combine(EvidenceDir, Arg(1, TEXT("shot")) + TEXT(".png")), true, false);
			AutoLogLine(FString::Printf(TEXT("screenshot %s"), *Arg(1, TEXT("shot"))));
			// The capture happens when this frame renders; hold the script so the next command cannot change the screen first.
			AutoWait = 0.1f;
			return;
		}
		else if (Cmd == TEXT("perf_begin"))
		{
			FrameTimes.Reset();
			GpuTimes.Reset();
			GameTimes.Reset();
			RenderTimes.Reset();
			bRecordFrames = true;
			AutoLogLine(TEXT("perf_begin"));
		}
		else if (Cmd == TEXT("perf_end"))
		{
			bRecordFrames = false;
			const FString Name = Arg(1, TEXT("perf"));
			TArray<float> Sorted = FrameTimes;
			Sorted.Sort();
			float Sum = 0.0f;
			int32 Hitch33 = 0;
			int32 Hitch50 = 0;
			for (float V : FrameTimes)
			{
				Sum += V;
				Hitch33 += V > 33.3f ? 1 : 0;
				Hitch50 += V > 50.0f ? 1 : 0;
			}
			const int32 N = FrameTimes.Num();
			// 1% low: average fps of the slowest 1% of frames.
			float WorstSum = 0.0f;
			const int32 WorstN = FMath::Max(1, N / 100);
			for (int32 i = 0; i < WorstN && i < N; ++i)
			{
				WorstSum += Sorted[N - 1 - i];
			}
			const FPlatformMemoryStats Mem = FPlatformMemory::GetStats();
			FViewport* VP = GEngine && GEngine->GameViewport ? GEngine->GameViewport->Viewport : nullptr;
			const FIntPoint Size = VP ? VP->GetSizeXY() : FIntPoint::ZeroValue;
			const FString Report = FString::Printf(
				TEXT("{\n  \"name\": \"%s\",\n  \"frames\": %d,\n  \"seconds\": %.2f,\n  \"viewport\": [%d, %d],\n  \"mean_ms\": %.3f,\n  \"median_ms\": %.3f,\n  \"p95_ms\": %.3f,\n  \"p99_ms\": %.3f,\n  \"max_ms\": %.3f,\n  \"one_percent_low_fps\": %.2f,\n  \"hitches_over_33ms\": %d,\n  \"hitches_over_50ms\": %d,\n  \"gpu_median_ms\": %.3f,\n  \"gpu_p99_ms\": %.3f,\n  \"game_thread_median_ms\": %.3f,\n  \"render_thread_median_ms\": %.3f,\n  \"used_physical_mb\": %.1f,\n  \"peak_used_physical_mb\": %.1f,\n  \"dropped_sim_ticks\": %lld,\n  \"vfx_active\": %d\n}\n"),
				*Name, N, Sum / 1000.0f, Size.X, Size.Y, N ? Sum / N : 0.0f, Percentile(FrameTimes, 0.5f), Percentile(FrameTimes, 0.95f), Percentile(FrameTimes, 0.99f),
				N ? Sorted.Last() : 0.0f, WorstSum > 0.0f ? 1000.0f / (WorstSum / WorstN) : 0.0f, Hitch33, Hitch50, Percentile(GpuTimes, 0.5f), Percentile(GpuTimes, 0.99f),
				Percentile(GameTimes, 0.5f), Percentile(RenderTimes, 0.5f), Mem.UsedPhysical / 1048576.0, Mem.PeakUsedPhysical / 1048576.0, Clock.DroppedTicks(), Vfx ? Vfx->ActiveCount() : 0);
			WriteEvidence(Name + TEXT(".json"), Report);
			FString Raw;
			for (int32 i = 0; i < N; ++i)
			{
				Raw += FString::Printf(TEXT("%.3f,%.3f\n"), FrameTimes[i], GpuTimes.IsValidIndex(i) ? GpuTimes[i] : 0.0f);
			}
			WriteEvidence(Name + TEXT("_frames.csv"), Raw);
			AutoLogLine(FString::Printf(TEXT("perf_end %s frames=%d median=%.2f p99=%.2f"), *Name, N, Percentile(FrameTimes, 0.5f), Percentile(FrameTimes, 0.99f)));
		}
		else if (Cmd == TEXT("mem"))
		{
			const FPlatformMemoryStats Mem = FPlatformMemory::GetStats();
			AutoLogLine(FString::Printf(TEXT("mem %s used=%.1fMB peak=%.1fMB"), *Arg(1, TEXT("")), Mem.UsedPhysical / 1048576.0, Mem.PeakUsedPhysical / 1048576.0));
		}
		else if (Cmd == TEXT("assets"))
		{
			FString Missing;
			for (int32 i = 0; i < 2; ++i)
			{
				Missing += FString::Join(Visual[i]->MissingAnimations(), TEXT(","));
				if (Visual[i]->UsesGraybox())
				{
					Missing += FString::Printf(TEXT(" [p%d graybox]"), i);
				}
			}
			const FString Sounds = FString::Join(Audio.MissingSounds(), TEXT(","));
			AutoLogLine(FString::Printf(TEXT("%s assets missing_anims=[%s] missing_sounds=[%s] vfx=%d fonts=%d title=%d"), Missing.IsEmpty() && Sounds.IsEmpty() ? TEXT("ok") : TEXT("WARN"), *Missing, *Sounds, Vfx && Vfx->HasMaterial(), Fonts.bLoaded, TitleTexture != nullptr));
		}
		else if (Cmd == TEXT("loop"))
		{
			Loops.Add(FLoopFrame{AutoLine, FCString::Atoi(*Arg(1, TEXT("1")))});
		}
		else if (Cmd == TEXT("endloop"))
		{
			if (Loops.Num() > 0 && --Loops.Last().Remaining > 0)
			{
				AutoLine = Loops.Last().StartLine;
			}
			else if (Loops.Num() > 0)
			{
				Loops.Pop();
			}
		}
		else if (Cmd == TEXT("platform_check"))
		{
#if EH_LINUX_PLATFORM
			const EHLinux::FPlatformReport P = EHLinux::GetPlatformReport();
			AutoLogLine(FString::Printf(TEXT("%s platform_check audio_output=%d delivered=%llu dropped=%llu display_guard=%d deferred=%llu replayed=%llu displays=[%s]"),
				P.bAudioOutputActive && P.bDisplayGuardActive ? TEXT("ok") : TEXT("FAIL"), P.bAudioOutputActive, P.AudioBuffersDelivered, P.AudioSubmitsDropped,
				P.bDisplayGuardActive, P.DisplayEventsDeferred, P.DisplayEventsReplayed, *EHLinux::DescribeDisplays()));
#else
			AutoLogLine(TEXT("ok platform_check (no platform layer on this target)"));
#endif
		}
		else if (Cmd == TEXT("window_check"))
		{
			// Fullscreen and borderless must cover the whole monitor, not just its work area (the panel-sized window).
			FEHWindowFit Fit;
			if (!DescribeGameWindow(Fit))
			{
				AutoLogLine(TEXT("FAIL window_check: no game window"));
			}
			else
			{
				const bool bOk = Fit.Mode == EWindowMode::Windowed || Fit.bCoversMonitor;
				auto Rect = [](const FPlatformRect& R) { return FString::Printf(TEXT("%dx%d+%d+%d"), R.Right - R.Left, R.Bottom - R.Top, R.Left, R.Top); };
				AutoLogLine(FString::Printf(TEXT("%s window_check mode=%s window=%s monitor=%s workarea=%s reasserted=%d"), bOk ? TEXT("ok") : TEXT("FAIL"),
					Fit.Mode == EWindowMode::Fullscreen ? TEXT("fullscreen") : (Fit.Mode == EWindowMode::WindowedFullscreen ? TEXT("borderless") : TEXT("windowed")),
					*Rect(Fit.Window), *Rect(Fit.Monitor), *Rect(Fit.WorkArea), TotalDisplayReasserts));
			}
		}
		else if (Cmd == TEXT("display"))
		{
			// display fullscreen|borderless|windowed [W H]: a display change through the game's own path, for this
			// session only.
			const FString DisplayMode = Arg(1, TEXT("windowed"));
			Settings.WindowMode = DisplayMode == TEXT("fullscreen") ? 0 : (DisplayMode == TEXT("borderless") ? 1 : 2);
			if (T.IsValidIndex(3))
			{
				Settings.Resolution = FIntPoint(FCString::Atoi(*T[2]), FCString::Atoi(*T[3]));
			}
			bSessionDisplayOverride = true;
			ApplySettings(true);
			AutoLogLine(FString::Printf(TEXT("display %s %dx%d"), *DisplayMode, Settings.Resolution.X, Settings.Resolution.Y));
		}
		else if (Cmd == TEXT("display_hotplug_probe"))
		{
			RunDisplayHotplugProbe();
		}
		else if (Cmd == TEXT("audio_offthread_submit"))
		{
#if UE_BUILD_SHIPPING
			AutoLogLine(TEXT("FAIL audio_offthread_submit runs in Development builds only"));
#else
			AudioProbeLeft = FCString::Atof(*Arg(1, TEXT("5")));
			AudioProbeCalls = 0;
			AutoLogLine(FString::Printf(TEXT("audio_offthread_submit start %.1fs"), AudioProbeLeft));
#endif
		}
		else if (Cmd == TEXT("quit"))
		{
			AutoLogLine(FString::Printf(TEXT("quit after %d matches, sounds played %d"), AutoMatches, Audio.PlayedCount()));
			AutoLines.Reset();
			UKismetSystemLibrary::QuitGame(this, GetWorld()->GetFirstPlayerController(), EQuitPreference::Quit, false);
			return;
		}
		else
		{
			AutoLogLine(FString::Printf(TEXT("FAIL unknown command: %s"), *Line));
		}
	}
}

void AEHGameDirector::RunDisplayHotplugProbe()
{
#if EH_LINUX_PLATFORM
	// A monitor entering standby while the game goes fullscreen: the disconnect is queued and a window-manager request
	// is left outstanding, so SDL's fullscreen call waits on the window manager with the disconnect next in its queue.
	TSharedPtr<SWindow> Window = GEngine && GEngine->GameViewport ? GEngine->GameViewport->GetWindow() : nullptr;
	TSharedPtr<FGenericWindow> Native = Window.IsValid() ? Window->GetNativeWindow() : nullptr;
	if (!Native.IsValid() || Native->GetWindowMode() != EWindowMode::Windowed)
	{
		AutoLogLine(TEXT("FAIL display_hotplug_probe needs a windowed game window"));
		return;
	}
	void* Handle = Native->GetOSWindowHandle();
	const EHLinux::FPlatformReport Before = EHLinux::GetPlatformReport();
	FString Error;
	if (!EHLinux::QueueOutputChange(Handle, false, Error))
	{
		AutoLogLine(FString::Printf(TEXT("FAIL display_hotplug_probe: %s"), *Error));
		return;
	}
	EHLinux::LeaveMoveOutstanding(Handle);
	Native->SetWindowMode(EWindowMode::Fullscreen);
	const EHLinux::FPlatformReport Mid = EHLinux::GetPlatformReport();
	// The monitor wakes while the game returns to a window.
	const bool bWakeQueued = EHLinux::QueueOutputChange(Handle, true, Error);
	Native->SetWindowMode(EWindowMode::Windowed);
	AutoLogLine(FString::Printf(TEXT("%s display_hotplug_probe standby_deferred=%llu wake_queued=%d displays=[%s]"),
		bWakeQueued ? TEXT("ok") : TEXT("FAIL"), Mid.DisplayEventsDeferred - Before.DisplayEventsDeferred, bWakeQueued, *EHLinux::DescribeDisplays()));
#else
	AutoLogLine(TEXT("ok display_hotplug_probe (no platform layer on this target)"));
#endif
}

#if !UE_BUILD_SHIPPING
void AEHGameDirector::TickAudioProbe(float DeltaSeconds)
{
	// The audio render thread submits one buffer of silence from its own thread when the stream starts; this repeats
	// that call from the game thread while SDL keeps requesting audio.
	static TArray<uint8> Silence;
	if (Silence.Num() == 0)
	{
		Silence.SetNumZeroed(1 << 16);
	}
	FAudioDeviceHandle Main = GEngine ? GEngine->GetMainAudioDevice() : FAudioDeviceHandle();
	Audio::FMixerDevice* Mixer = Main.IsValid() ? static_cast<Audio::FMixerDevice*>(Main.GetAudioDevice()) : nullptr;
	Audio::IAudioMixerPlatformInterface* Platform = Mixer ? Mixer->GetAudioMixerPlatform() : nullptr;
	if (Platform == nullptr)
	{
		AutoLogLine(TEXT("FAIL audio_offthread_submit: no audio mixer platform"));
		AudioProbeLeft = 0.0f;
		return;
	}
	for (int32 i = 0; i < 8; ++i)
	{
		Platform->SubmitBuffer(Silence.GetData());
		++AudioProbeCalls;
	}
	AudioProbeLeft -= DeltaSeconds;
	if (AudioProbeLeft <= 0.0f)
	{
		AutoLogLine(FString::Printf(TEXT("ok audio_offthread_submit calls=%lld"), AudioProbeCalls));
	}
}
#endif

// ---------------------------------------------------------------------------------------------------------------
// Self-tests for the control system, run in the packaged game so they cover the shipped code.

void AEHGameDirector::RunBindingsSelfTest()
{
	int32 Checks = 0;
	int32 Fails = 0;
	auto Check = [&](bool bOk, const FString& What) {
		++Checks;
		if (!bOk)
		{
			++Fails;
			AutoLogLine(FString::Printf(TEXT("FAIL bindings_selftest: %s"), *What));
		}
	};
	using S = EEHBindingSet;
	using A = EEHAction;
	const FEHBindings D = FEHBindings::Defaults();

	// 1. The creator's controller layout, identical for both players' layouts.
	for (S Pad : {S::GamepadP1, S::GamepadP2})
	{
		const FString P = EHSetId(Pad);
		Check(D.Get(Pad, A::Light, 0) == EKeys::Gamepad_FaceButton_Left, P + TEXT(" light = Square / X"));
		Check(D.Get(Pad, A::Heavy, 0) == EKeys::Gamepad_FaceButton_Top, P + TEXT(" heavy = Triangle / Y"));
		Check(D.Get(Pad, A::Dodge, 0) == EKeys::Gamepad_FaceButton_Right, P + TEXT(" dodge = Circle / B"));
		Check(D.Get(Pad, A::Throw, 0) == EKeys::Gamepad_LeftTrigger && !D.Get(Pad, A::Throw, 1).IsValid(), P + TEXT(" throw = L2 / LT"));
		Check(D.Get(Pad, A::Down, 0) == EKeys::Gamepad_DPad_Down && !D.Get(Pad, A::Down, 1).IsValid(), P + TEXT(" crouch = D-pad down (and the stick's down)"));
		Check(D.Get(Pad, A::Jump, 1) == EKeys::Gamepad_FaceButton_Bottom, P + TEXT(" jump slot 2 = Cross / A"));
		Check(D.Get(Pad, A::Block, 0) == EKeys::Gamepad_RightTrigger, P + TEXT(" block = R2 / RT"));
		Check(D.Get(Pad, A::Block, 1) == EKeys::Gamepad_LeftShoulder, P + TEXT(" block slot 2 = L1 / LB"));
		Check(D.Get(Pad, A::Special, 0) == EKeys::Gamepad_RightShoulder, P + TEXT(" special = R1 / RB"));
		Check(D.Get(Pad, A::Left, 0) == EKeys::Gamepad_DPad_Left && D.Get(Pad, A::Right, 0) == EKeys::Gamepad_DPad_Right, P + TEXT(" movement = D-pad"));
		Check(D.Get(Pad, A::Jump, 0) == EKeys::Gamepad_DPad_Up, P + TEXT(" jump = D-pad up"));
		for (A Act : {A::Light, A::Heavy, A::Dodge, A::Special})
		{
			Check(!D.Get(Pad, Act, 1).IsValid(), P + TEXT(" no hidden second button on ") + EHActionId(Act));
		}
		for (int32 a = 0; a < EHActionCount; ++a)
		{
			Check(!D.Get(Pad, static_cast<A>(a), 2).IsValid(), P + TEXT(" no third button on ") + EHActionId(static_cast<A>(a)));
		}
		for (int32 k = 0; k < EHKeysPerAction; ++k)
		{
			const FKey Former = EHFormerGrabKey(Pad, k);
			Check(!Former.IsValid() || D.Find(Pad, Former) != A::Count, P + TEXT(" every former grab button has a new job"));
		}
	}
	Check(EHMenuCommand(S::GamepadP1, EKeys::Gamepad_Special_Right) == EEHNav::Pause && !FEHBindings::IsBindable(S::GamepadP1, EKeys::Gamepad_Special_Right),
		TEXT("Options / Menu always pauses and cannot be bound"));

	// 2. PlayStation and Xbox names for the same physical buttons.
	struct FName2 { A Act; int32 Slot; const TCHAR* PS; const TCHAR* XB; };
	const FName2 Names[] = {{A::Light, 0, TEXT("Square"), TEXT("X")}, {A::Heavy, 0, TEXT("Triangle"), TEXT("Y")}, {A::Dodge, 0, TEXT("Circle"), TEXT("B")},
		{A::Jump, 1, TEXT("Cross"), TEXT("A")}, {A::Block, 1, TEXT("L1"), TEXT("LB")}, {A::Block, 0, TEXT("R2"), TEXT("RT")}, {A::Special, 0, TEXT("R1"), TEXT("RB")},
		{A::Throw, 0, TEXT("L2"), TEXT("LT")}};
	for (const FName2& N : Names)
	{
		const FKey K = D.Get(S::GamepadP1, N.Act, N.Slot);
		const FString PS = ButtonNameOf(EEHDeviceKind::PlayStation, K);
		const FString XB = ButtonNameOf(EEHDeviceKind::Xbox, K);
		Check(PS == N.PS && XB == N.XB, FString::Printf(TEXT("%s names: %s / %s (want %s / %s)"), EHActionId(N.Act), *PS, *XB, N.PS, N.XB));
	}
	Check(ButtonNameOf(EEHDeviceKind::PlayStation, EKeys::Gamepad_Special_Right) == TEXT("OPTIONS") && ButtonNameOf(EEHDeviceKind::Xbox, EKeys::Gamepad_Special_Right) == TEXT("MENU"), TEXT("pause names"));
	Check(ButtonNameOf(EEHDeviceKind::Gamepad, EKeys::Gamepad_FaceButton_Bottom) == TEXT("bottom face button"), TEXT("generic controllers name buttons by position"));

	// 3. Menus and gameplay are separate: Cross / A confirms in menus and jumps in a match; Circle / B backs out and dodges.
	Check(EHMenuCommand(S::GamepadP1, EKeys::Gamepad_FaceButton_Bottom) == EEHNav::Confirm && D.Find(S::GamepadP1, EKeys::Gamepad_FaceButton_Bottom) == A::Jump, TEXT("Cross: confirm in menus, jump in play"));
	// The keyboards' former grab keys jump too: I on the left side, Numpad 5 and ; on the right.
	Check(D.Get(S::KeyboardA, A::Jump, 0) == EKeys::W && D.Get(S::KeyboardA, A::Jump, 1) == EKeys::I, TEXT("keyboard left: jump = W or I"));
	Check(D.Get(S::KeyboardB, A::Jump, 0) == EKeys::Up && D.Get(S::KeyboardB, A::Jump, 1) == EKeys::NumPadFive && D.Get(S::KeyboardB, A::Jump, 2) == EKeys::Semicolon,
		TEXT("keyboard right: jump = Up, Numpad 5 or ;"));
	Check(D.Get(S::KeyboardA, A::Down, 0) == EKeys::S && D.Get(S::KeyboardA, A::Throw, 0) == EKeys::U, TEXT("keyboard left: crouch = S, throw = U"));
	Check(D.Get(S::KeyboardB, A::Down, 0) == EKeys::Down && D.Get(S::KeyboardB, A::Throw, 0) == EKeys::NumPadFour && D.Get(S::KeyboardB, A::Throw, 1) == EKeys::M,
		TEXT("keyboard right: crouch = Down, throw = Numpad 4 or M"));
	Check(EHMenuCommand(S::KeyboardA, EKeys::S) == EEHNav::Down && EHMenuCommand(S::KeyboardB, EKeys::Down) == EEHNav::Down && EHMenuCommand(S::GamepadP1, EKeys::Gamepad_DPad_Down) == EEHNav::Down,
		TEXT("the crouch keys are the menus' down too"));
	Check(EHMenuCommand(S::GamepadP1, EKeys::Gamepad_FaceButton_Right) == EEHNav::Back && D.Find(S::GamepadP1, EKeys::Gamepad_FaceButton_Right) == A::Dodge, TEXT("Circle: back in menus, dodge in play"));
	Check(EHMenuCommand(S::GamepadP1, EKeys::Gamepad_FaceButton_Left) == EEHNav::Count, TEXT("Square has no menu role"));

	// 4. Conflicts are never silent: detect, swap, replace, own-slot trade, clear, reset.
	FEHBindings B = D;
	FEHBindingRef C = B.FindConflict(S::GamepadP1, A::Light, 0, EKeys::Gamepad_FaceButton_Top);
	Check(C.IsValid() && C.Set == S::GamepadP1 && C.Action == A::Heavy && C.Slot == 0, TEXT("conflict with Heavy found"));
	B.Assign(S::GamepadP1, A::Light, 0, EKeys::Gamepad_FaceButton_Top, EEHConflictResolve::Swap);
	Check(B.Get(S::GamepadP1, A::Light, 0) == EKeys::Gamepad_FaceButton_Top && B.Get(S::GamepadP1, A::Heavy, 0) == EKeys::Gamepad_FaceButton_Left, TEXT("swap"));
	FString Report;
	Check(!B.HasConflicts(&Report), TEXT("no duplicate after swap ") + Report);
	B = D;
	B.Assign(S::GamepadP1, A::Light, 0, EKeys::Gamepad_FaceButton_Top, EEHConflictResolve::Replace);
	Check(B.Get(S::GamepadP1, A::Light, 0) == EKeys::Gamepad_FaceButton_Top && B.IsUnbound(S::GamepadP1, A::Heavy), TEXT("replace leaves Heavy unbound"));
	const FString Taken = B.ResetAction(S::GamepadP1, A::Heavy);
	Check(B.Get(S::GamepadP1, A::Heavy, 0) == EKeys::Gamepad_FaceButton_Top && B.IsUnbound(S::GamepadP1, A::Light) && !Taken.IsEmpty(), TEXT("reset action takes its default back and reports it"));
	B = D;
	B.Assign(S::GamepadP1, A::Block, 1, EKeys::Gamepad_RightTrigger, EEHConflictResolve::Replace);
	Check(B.Get(S::GamepadP1, A::Block, 1) == EKeys::Gamepad_RightTrigger && B.Get(S::GamepadP1, A::Block, 0) == EKeys::Gamepad_LeftShoulder, TEXT("a key from the action's other slot trades slots"));
	B = D;
	B.Assign(S::GamepadP1, A::Light, 2, EKeys::Gamepad_RightThumbstick, EEHConflictResolve::Replace);
	Check(B.Get(S::GamepadP1, A::Light, 2) == EKeys::Gamepad_RightThumbstick && B.Find(S::GamepadP1, EKeys::Gamepad_RightThumbstick) == A::Light && B.First(S::GamepadP1, A::Light) == EKeys::Gamepad_FaceButton_Left,
		TEXT("a third button for an action"));
	B = D;
	B.Assign(S::GamepadP1, A::Light, 1, EKeys::Gamepad_RightThumbstick, EEHConflictResolve::Replace);
	Check(B.Find(S::GamepadP1, EKeys::Gamepad_RightThumbstick) == A::Light && B.Find(S::GamepadP1, EKeys::Gamepad_FaceButton_Left) == A::Light, TEXT("two buttons for one action"));
	B.Clear(S::GamepadP1, A::Block, 1);
	Check(B.Find(S::GamepadP1, EKeys::Gamepad_LeftShoulder) == A::Count && B.Find(S::GamepadP1, EKeys::Gamepad_RightTrigger) == A::Block, TEXT("clear one block slot"));
	B.ResetSet(S::GamepadP1);
	bool bSame = true;
	for (int32 a = 0; a < EHActionCount; ++a)
	{
		for (int32 k = 0; k < EHKeysPerAction; ++k)
		{
			bSame &= B.Keys[static_cast<int32>(S::GamepadP1)][a][k] == D.Keys[static_cast<int32>(S::GamepadP1)][a][k];
		}
	}
	Check(bSame, TEXT("restore layout defaults"));
	B = D;
	B.Assign(S::GamepadP2, A::Light, 0, EKeys::Gamepad_FaceButton_Top, EEHConflictResolve::Swap);
	Check(B.Get(S::GamepadP1, A::Light, 0) == EKeys::Gamepad_FaceButton_Left, TEXT("player 2's layout is independent of player 1's"));
	C = D.FindConflict(S::KeyboardA, A::Light, 0, EKeys::NumPadOne);
	Check(C.IsValid() && C.Set == S::KeyboardB && C.Action == A::Light, TEXT("both keyboard sides share one keyboard"));
	Check(!FEHBindings::IsBindable(S::KeyboardA, EKeys::Escape) && !FEHBindings::IsBindable(S::GamepadP1, EKeys::Gamepad_LeftStick_Up) &&
		!FEHBindings::IsBindable(S::GamepadP1, EKeys::Gamepad_RightTriggerAxis) && FEHBindings::IsBindable(S::GamepadP1, EKeys::Gamepad_RightTrigger) &&
		FEHBindings::IsBindable(S::GamepadP1, EKeys::Gamepad_Special_Left) && !FEHBindings::IsBindable(S::GamepadP1, EKeys::J) &&
		!FEHBindings::IsBindable(S::KeyboardA, EKeys::Gamepad_FaceButton_Bottom), TEXT("bindable keys"));
	Check(!D.HasConflicts(&Report), TEXT("defaults have no conflicts ") + Report);

	// 5. Save and load: a round trip, a version-1 file, and a file with a conflict.
	const FString Dir = FPaths::Combine(EvidenceDir.IsEmpty() ? FPaths::ProjectSavedDir() : EvidenceDir, TEXT("selftest"));
	IFileManager::Get().MakeDirectory(*Dir, true);
	FEHSettings T = Settings;
	T.Bindings = D;
	T.Bindings.Assign(S::GamepadP2, A::Light, 0, EKeys::Gamepad_FaceButton_Bottom, EEHConflictResolve::Swap);
	T.Bindings.Assign(S::KeyboardA, A::Light, 0, EKeys::U, EEHConflictResolve::Replace);
	T.Bindings.Clear(S::GamepadP1, A::Block, 1);
	T.Bindings.Assign(S::KeyboardB, A::Light, 2, EKeys::NumPadFour, EEHConflictResolve::Replace);
	const FString RoundPath = FPaths::Combine(Dir, TEXT("roundtrip.json"));
	Check(T.Save(RoundPath), TEXT("save"));
	const FString FreshPath = FPaths::Combine(Dir, TEXT("new-profile"), TEXT("Settings.json"));
	Check(T.Save(FreshPath), TEXT("save creates an absent settings parent directory"));
	FString Warning;
	const FEHSettings L = FEHSettings::Load(&Warning, RoundPath);
	bSame = Warning.IsEmpty();
	for (int32 s = 0; s < EHSetCount; ++s)
	{
		for (int32 a = 0; a < EHActionCount; ++a)
		{
			for (int32 k = 0; k < EHKeysPerAction; ++k)
			{
				bSame &= L.Bindings.Keys[s][a][k] == T.Bindings.Keys[s][a][k];
			}
		}
	}
	Check(bSame, TEXT("custom layouts survive save and load ") + Warning);
	const FString V1Path = FPaths::Combine(Dir, TEXT("version1.json"));
	FFileHelper::SaveStringToFile(TEXT("{\"version\":1,\"bindings\":{\"0.Light\":[\"U\",\"Enter\"],\"0.Pause\":[\"Escape\",\"\"],\"2.Light\":[\"Gamepad_FaceButton_Bottom\",\"\"],\"2.Grab\":[\"Gamepad_FaceButton_Left\",\"\"]}}"), *V1Path);
	Warning.Reset();
	const FEHSettings V1 = FEHSettings::Load(&Warning, V1Path);
	Check(V1.Bindings.Get(S::KeyboardA, A::Light, 0) == EKeys::U && V1.Bindings.Get(S::KeyboardA, A::Light, 1) == EKeys::Enter, TEXT("version-1 keyboard layout kept"));
	Check(V1.Bindings.Get(S::GamepadP1, A::Light, 0) == EKeys::Gamepad_FaceButton_Left && V1.Bindings.Get(S::GamepadP1, A::Jump, 1) == EKeys::Gamepad_FaceButton_Bottom && !Warning.IsEmpty(),
		TEXT("version-1 controller layout moves to the new default, with a notice"));
	Check(V1.Bindings.IsUnbound(S::KeyboardA, A::Throw) && V1.Bindings.Get(S::KeyboardA, A::Down, 0) == EKeys::S && Warning.Contains(TEXT("Throw")),
		TEXT("version 1: the player's U stays on Light, so Throw is left for them to choose (named in the notice); S crouches ") + Warning);
	// A version-2 file (two slots, Grab on its old buttons): the old grab buttons move to jump and block, a grab button
	// the player had chosen stays with Grab, and the right keyboard's third jump key arrives.
	const FString V2Path = FPaths::Combine(Dir, TEXT("version2.json"));
	FFileHelper::SaveStringToFile(TEXT("{\"version\":2,\"bindings\":{")
		TEXT("\"controller1\":{\"Jump\":[\"Gamepad_DPad_Up\",\"\"],\"Grab\":[\"Gamepad_FaceButton_Bottom\",\"Gamepad_LeftShoulder\"],\"Block\":[\"Gamepad_RightTrigger\",\"\"]},")
		TEXT("\"controller2\":{\"Grab\":[\"Gamepad_LeftTrigger\",\"\"],\"Block\":[\"Gamepad_RightTrigger\",\"Gamepad_LeftShoulder\"],\"Jump\":[\"Gamepad_DPad_Up\",\"\"]},")
		TEXT("\"keyboard1\":{\"Jump\":[\"W\",\"\"],\"Grab\":[\"I\",\"\"]},")
		TEXT("\"keyboard2\":{\"Jump\":[\"Up\",\"\"],\"Grab\":[\"NumPadFive\",\"Semicolon\"]}}}"), *V2Path);
	Warning.Reset();
	const FEHSettings V2 = FEHSettings::Load(&Warning, V2Path);
	Check(V2.Bindings.Get(S::GamepadP1, A::Jump, 1) == EKeys::Gamepad_FaceButton_Bottom && V2.Bindings.Get(S::GamepadP1, A::Block, 1) == EKeys::Gamepad_LeftShoulder &&
		V2.Bindings.Get(S::GamepadP1, A::Throw, 0) == EKeys::Gamepad_LeftTrigger && !Warning.IsEmpty(), TEXT("version 2: Cross jumps, L1 blocks and L2 throws, with a notice ") + Warning);
	Check(V2.Bindings.Get(S::GamepadP2, A::Throw, 0) == EKeys::Gamepad_LeftTrigger && V2.Bindings.Get(S::GamepadP2, A::Jump, 1) == EKeys::Gamepad_FaceButton_Bottom,
		TEXT("version 2: a player's own grab button stays; the default jump button is free and arrives"));
	Check(V2.Bindings.Get(S::KeyboardA, A::Jump, 1) == EKeys::I && V2.Bindings.Get(S::KeyboardB, A::Jump, 1) == EKeys::NumPadFive &&
		V2.Bindings.Get(S::KeyboardB, A::Jump, 2) == EKeys::Semicolon && !V2.Bindings.HasConflicts(&Report), TEXT("version 2: keyboard grab keys jump ") + Report);
	// A version-3 file (Grab empty, no Crouch): Throw and Crouch take their defaults where free; a key the player gave
	// another action stays theirs, the new action is left unbound and the notice says so. Nothing else changes.
	const FString V3Path = FPaths::Combine(Dir, TEXT("version3.json"));
	FFileHelper::SaveStringToFile(TEXT("{\"version\":3,\"masterVolume\":55,\"bindings\":{")
		TEXT("\"controller1\":{\"Grab\":[\"\",\"\",\"\"],\"Block\":[\"Gamepad_RightTrigger\",\"Gamepad_LeftTrigger\",\"\"],\"Jump\":[\"Gamepad_DPad_Up\",\"Gamepad_FaceButton_Bottom\",\"\"]},")
		TEXT("\"controller2\":{\"Grab\":[\"\",\"\",\"\"]},")
		TEXT("\"keyboard1\":{\"Special\":[\"S\",\"\",\"\"],\"Grab\":[\"\",\"\",\"\"]},")
		TEXT("\"keyboard2\":{\"Grab\":[\"\",\"\",\"\"]}}}"), *V3Path);
	Warning.Reset();
	const FEHSettings V3 = FEHSettings::Load(&Warning, V3Path);
	Check(V3.MasterVolume == 55 && V3.Bindings.Get(S::KeyboardA, A::Special, 0) == EKeys::S && V3.Bindings.IsUnbound(S::KeyboardA, A::Down) && V3.Bindings.Get(S::KeyboardA, A::Throw, 0) == EKeys::U,
		TEXT("version 3: S stays on the player's Special; Crouch is left for them; Throw gets U"));
	Check(V3.Bindings.Get(S::GamepadP1, A::Block, 1) == EKeys::Gamepad_LeftTrigger && V3.Bindings.IsUnbound(S::GamepadP1, A::Throw) && V3.Bindings.Get(S::GamepadP1, A::Down, 0) == EKeys::Gamepad_DPad_Down,
		TEXT("version 3: L2 stays on the player's Block; Throw is left for them; the D-pad crouches"));
	Check(V3.Bindings.Get(S::GamepadP2, A::Throw, 0) == EKeys::Gamepad_LeftTrigger && V3.Bindings.Get(S::KeyboardB, A::Throw, 0) == EKeys::NumPadFour && V3.Bindings.Get(S::KeyboardB, A::Down, 0) == EKeys::Down,
		TEXT("version 3: untouched layouts get the new defaults"));
	Check(Warning.Contains(TEXT("Crouch")) && Warning.Contains(TEXT("Throw")) && !V3.Bindings.HasConflicts(&Report), TEXT("version 3: the notice names what was left unbound ") + Warning + Report);
	const FString V4Path = FPaths::Combine(Dir, TEXT("version4.json"));
	Check(V3.Save(V4Path), TEXT("save the migrated file"));
	Warning.Reset();
	const FEHSettings V4 = FEHSettings::Load(&Warning, V4Path);
	Check(Warning.IsEmpty() && V4.Bindings.IsUnbound(S::KeyboardA, A::Down) && V4.Bindings.Get(S::KeyboardA, A::Special, 0) == EKeys::S,
		TEXT("a version-4 file loads as saved, without migrating again ") + Warning);
	const FString BadPath = FPaths::Combine(Dir, TEXT("conflict.json"));
	FFileHelper::SaveStringToFile(TEXT("{\"version\":2,\"bindings\":{\"controller1\":{\"LightAttack\":[\"Gamepad_FaceButton_Top\",\"\"]},\"controller2\":{\"LightAttack\":[\"Gamepad_LeftThumbstick\",\"\"]}}}"), *BadPath);
	Warning.Reset();
	const FEHSettings Bad = FEHSettings::Load(&Warning, BadPath);
	Check(Bad.Bindings.Get(S::GamepadP1, A::Light, 0) == EKeys::Gamepad_FaceButton_Left && Bad.Bindings.Get(S::GamepadP2, A::Light, 0) == EKeys::Gamepad_LeftThumbstick && !Warning.IsEmpty(),
		TEXT("a conflicting layout resets alone; the other layout is kept"));
	AutoLogLine(FString::Printf(TEXT("%s bindings_selftest checks=%d failures=%d"), Fails == 0 ? TEXT("ok") : TEXT("FAIL"), Checks, Fails));
}

void AEHGameDirector::RunInputSelfTest()
{
	int32 Checks = 0;
	int32 Fails = 0;
	auto Check = [&](bool bOk, const FString& What) {
		++Checks;
		if (!bOk)
		{
			++Fails;
			AutoLogLine(FString::Printf(TEXT("FAIL input_selftest: %s"), *What));
		}
	};
	FEHInputRouter& R = *RouterPtr;
	const int32 Dev = EHDeviceGamepadBase + 77;   // a test-only device, removed again at the end
	const FEHBindings Saved = Settings.Bindings;
	Settings.Bindings = FEHBindings::Defaults();
	R.ClearNav();
	auto Sample = [&]() { return R.SampleForTick(Dev); };
	auto Tap = [&](const FKey& K) {
		R.InjectKey(Dev, K, true);
		const eh::InputFrame F = Sample();
		R.InjectKey(Dev, K, false);
		Sample();
		return F;
	};
	eh::InputFrame F0;
	auto LastNav = [&]() {
		EEHNav Out = EEHNav::Count;
		FEHNavEvent E;
		while (R.PopNav(E))
		{
			if (E.Device == Dev && E.Nav != EEHNav::Count)
			{
				Out = E.Nav;
			}
		}
		return Out;
	};

	// Every default button gives exactly its one action.
	struct FCase { FKey Key; uint8 Btn; const TCHAR* What; };
	const FCase Cases[] = {{EKeys::Gamepad_FaceButton_Left, eh::BtnLight, TEXT("Square / X -> light")}, {EKeys::Gamepad_FaceButton_Top, eh::BtnHeavy, TEXT("Triangle / Y -> heavy")},
		{EKeys::Gamepad_FaceButton_Right, eh::BtnDodge, TEXT("Circle / B -> dodge")}, {EKeys::Gamepad_LeftShoulder, eh::BtnBlock, TEXT("L1 / LB -> block")},
		{EKeys::Gamepad_RightShoulder, eh::BtnSpecial, TEXT("R1 / RB -> special")}};
	for (const FCase& Case : Cases)
	{
		const eh::InputFrame F = Tap(Case.Key);
		Check(F.pressed == Case.Btn && F.x == 0 && F.y == 0, FString::Printf(TEXT("%s (pressed=%d)"), Case.What, F.pressed));
	}
	{
		const eh::InputFrame F = Tap(EKeys::Gamepad_FaceButton_Bottom);
		Check(F.y == 1 && F.pressed == 0 && F.x == 0, TEXT("Cross / A -> jump"));
	}
	// L2 / LT is the throw (through the trigger axis), and down crouches from the D-pad or the stick.
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftTriggerAxis, 0.8f);
	Check((Sample().pressed & eh::BtnThrow) != 0, TEXT("L2 / LT -> throw"));
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftTriggerAxis, 0.0f);
	Sample();
	R.InjectKey(Dev, EKeys::Gamepad_DPad_Down, true);
	Check(Sample().y == -1, TEXT("D-pad down -> crouch"));
	R.InjectKey(Dev, EKeys::Gamepad_FaceButton_Bottom, true);
	Check(Sample().y == 1, TEXT("Cross while crouching jumps (up wins over down)"));
	R.InjectKey(Dev, EKeys::Gamepad_FaceButton_Bottom, false);
	Check(Sample().y == -1, TEXT("back to crouching when the jump button is let go"));
	R.InjectKey(Dev, EKeys::Gamepad_DPad_Down, false);
	Check(Sample().y == 0, TEXT("D-pad down released"));
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftY, -0.5f);
	Check(Sample().y == 0, TEXT("a half-way stick does not crouch"));
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftY, -0.9f);
	Check(Sample().y == -1, TEXT("left stick down -> crouch"));
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftY, -0.45f);
	Check(Sample().y == -1, TEXT("hysteresis: still crouched just inside the release threshold"));
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftY, -0.2f);
	Check(Sample().y == 0, TEXT("stick released: standing"));
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftX, 0.7f);
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftY, -0.7f);
	F0 = Sample();
	Check(F0.y == -1 && F0.x == 1, TEXT("a diagonal down-toward: both directions"));
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftX, 0.0f);
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftY, 0.0f);
	Sample();
	LastNav();
	// Menu roles of the same buttons.
	LastNav();
	Tap(EKeys::Gamepad_FaceButton_Bottom);
	Check(LastNav() == EEHNav::Confirm, TEXT("Cross / A confirms in menus"));
	Tap(EKeys::Gamepad_FaceButton_Right);
	Check(LastNav() == EEHNav::Back, TEXT("Circle / B backs out of menus"));
	Tap(EKeys::Gamepad_FaceButton_Left);
	Check(LastNav() == EEHNav::Count, TEXT("Square / X does nothing in menus"));
	Tap(EKeys::Gamepad_Special_Right);
	Check(LastNav() == EEHNav::Pause, TEXT("Options / Menu pauses"));

	// Directions (toward / away is judged from x when a button is pressed).
	R.InjectKey(Dev, EKeys::Gamepad_DPad_Right, true);
	eh::InputFrame F = Sample();
	Check(F.x == 1, TEXT("D-pad right"));
	R.InjectKey(Dev, EKeys::Gamepad_FaceButton_Top, true);
	F = Sample();
	Check(F.x == 1 && F.pressed == eh::BtnHeavy, TEXT("toward + heavy in one tick"));
	R.InjectKey(Dev, EKeys::Gamepad_FaceButton_Top, false);
	R.InjectKey(Dev, EKeys::Gamepad_DPad_Right, false);
	R.InjectKey(Dev, EKeys::Gamepad_DPad_Left, true);
	Check(Sample().x == -1, TEXT("D-pad left"));
	R.InjectKey(Dev, EKeys::Gamepad_DPad_Left, false);
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftX, 0.9f);
	Check(Sample().x == 1, TEXT("left stick right"));
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftX, 0.0f);
	Check(Sample().x == 0, TEXT("left stick centred"));
	LastNav();

	// A jump button jumps the way the stick points, and two jump buttons at once are one jump held until both are up.
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftX, 0.9f);
	R.InjectKey(Dev, EKeys::Gamepad_FaceButton_Bottom, true);
	F = Sample();
	Check(F.y == 1 && F.x == 1, TEXT("stick toward + Cross: a jump toward"));
	R.InjectKey(Dev, EKeys::Gamepad_DPad_Up, true);
	R.InjectKey(Dev, EKeys::Gamepad_FaceButton_Bottom, false);
	Check(Sample().y == 1, TEXT("jump still held by D-pad up"));
	R.InjectKey(Dev, EKeys::Gamepad_DPad_Up, false);
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftX, 0.0f);
	F = Sample();
	Check(F.y == 0 && F.x == 0, TEXT("jump released"));
	// L1 / LB blocks while held, alongside the trigger.
	R.InjectKey(Dev, EKeys::Gamepad_LeftShoulder, true);
	F = Sample();
	Check((F.held & eh::BtnBlock) != 0 && (F.pressed & eh::BtnBlock) != 0, TEXT("L1 / LB: block pressed"));
	Check((Sample().held & eh::BtnBlock) != 0, TEXT("L1 / LB: block held"));
	R.InjectKey(Dev, EKeys::Gamepad_LeftShoulder, false);
	Check((Sample().held & eh::BtnBlock) == 0, TEXT("L1 / LB: block released"));

	// The engine's digital trigger press can arrive before the first axis event; it must not become a second press.
	R.InjectKey(Dev, EKeys::Gamepad_RightTrigger, true);
	Check((Sample().pressed & eh::BtnBlock) == 0, TEXT("an early digital trigger press waits for the axis"));
	R.InjectAnalog(Dev, EKeys::Gamepad_RightTriggerAxis, 0.15f);
	R.InjectAnalog(Dev, EKeys::Gamepad_RightTriggerAxis, 0.6f);
	F = Sample();
	Check((F.pressed & eh::BtnBlock) != 0, TEXT("then the axis presses block once"));
	R.InjectKey(Dev, EKeys::Gamepad_RightTrigger, false);
	R.InjectAnalog(Dev, EKeys::Gamepad_RightTriggerAxis, 0.0f);
	Check((Sample().held & eh::BtnBlock) == 0, TEXT("and releases it"));
	// R2 / RT: hold to block, release to stop, with fixed analog thresholds.
	R.InjectAnalog(Dev, EKeys::Gamepad_RightTriggerAxis, FEHInputRouter::TriggerOn - 0.05f);
	Check((Sample().held & eh::BtnBlock) == 0, TEXT("trigger below the press threshold"));
	R.InjectAnalog(Dev, EKeys::Gamepad_RightTriggerAxis, FEHInputRouter::TriggerOn + 0.05f);
	F = Sample();
	Check((F.held & eh::BtnBlock) != 0 && (F.pressed & eh::BtnBlock) != 0, TEXT("trigger pressed: block"));
	R.InjectAnalog(Dev, EKeys::Gamepad_RightTriggerAxis, FEHInputRouter::TriggerOn - 0.05f);
	Check((Sample().held & eh::BtnBlock) != 0, TEXT("still blocking between the thresholds"));
	R.InjectAnalog(Dev, EKeys::Gamepad_RightTriggerAxis, FEHInputRouter::TriggerOff - 0.05f);
	Check((Sample().held & eh::BtnBlock) == 0, TEXT("trigger released: block ends"));
	R.InjectKey(Dev, EKeys::Gamepad_RightTrigger, true);
	Check((Sample().held & eh::BtnBlock) == 0, TEXT("the engine's digital trigger press is ignored once the axis is known"));
	R.InjectKey(Dev, EKeys::Gamepad_RightTrigger, false);

	// Player 2's layout applies only to the controller in player 2's Local Versus slot.
	Settings.Bindings.Assign(EEHBindingSet::GamepadP2, EEHAction::Light, 0, EKeys::Gamepad_FaceButton_Top, EEHConflictResolve::Swap);
	R.SetGamepadPlayer(Dev, 1);
	Check(Tap(EKeys::Gamepad_FaceButton_Left).pressed == eh::BtnHeavy && Tap(EKeys::Gamepad_FaceButton_Top).pressed == eh::BtnLight, TEXT("player 2 layout in player 2's slot"));
	R.ClearGamepadPlayers();
	Check(Tap(EKeys::Gamepad_FaceButton_Left).pressed == eh::BtnLight, TEXT("player 1 layout elsewhere"));

	// Remapping changes the action a button produces at once.
	Settings.Bindings = FEHBindings::Defaults();
	Settings.Bindings.Assign(EEHBindingSet::GamepadP1, EEHAction::Block, 0, EKeys::Gamepad_LeftTrigger, EEHConflictResolve::Replace);
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftTriggerAxis, 0.9f);
	Check((Sample().held & eh::BtnBlock) != 0, TEXT("block moved to L2 / LT"));
	R.InjectAnalog(Dev, EKeys::Gamepad_LeftTriggerAxis, 0.0f);
	R.InjectAnalog(Dev, EKeys::Gamepad_RightTriggerAxis, 0.9f);
	Check((Sample().held & eh::BtnBlock) == 0, TEXT("R2 / RT no longer blocks"));
	R.InjectAnalog(Dev, EKeys::Gamepad_RightTriggerAxis, 0.0f);

	Settings.Bindings = Saved;
	R.ForgetDevice(Dev);
	R.ClearLatches();
	AutoLogLine(FString::Printf(TEXT("%s input_selftest checks=%d failures=%d"), Fails == 0 ? TEXT("ok") : TEXT("FAIL"), Checks, Fails));
}
