// Scripted evaluation runs for the packaged game: -EHAuto=<script> [-EHEvidence=<dir>].
// Menu steps go through FEHInputRouter exactly like a device press; bot-driven players feed their decisions
// into the router too, so matches exercise the same sampling path as a keyboard or gamepad.
#include "EHGameDirector.h"

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

namespace EHAutoDetail
{
struct FLoopFrame
{
	int32 StartLine = 0;
	int32 Remaining = 0;
};
TArray<FLoopFrame> Loops;
TArray<TPair<int32, EEHAction>> PendingRelease;
float StepTimer = 0.0f;
int32 StuckFrames[2] = {0, 0};
int32 LastStateKey[2] = {-1, -1};
TArray<float> GpuTimes;
TArray<float> GameTimes;
TArray<float> RenderTimes;

EEHAction ParseAction(const FString& S)
{
	for (int32 A = 0; A < EHActionCount; ++A)
	{
		if (S.Equals(EHActionName(static_cast<EEHAction>(A)), ESearchCase::IgnoreCase))
		{
			return static_cast<EEHAction>(A);
		}
	}
	return EEHAction::Count;
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
	FFileHelper::SaveStringToFile(Stamped + LINE_TERMINATOR, *FPaths::Combine(EvidenceDir, TEXT("auto_log.txt")), FFileHelper::EEncodingOptions::AutoDetect, &IFileManager::Get(), FILEWRITE_Append);
}

void AEHGameDirector::WriteEvidence(const FString& Name, const FString& Text)
{
	if (!EvidenceDir.IsEmpty())
	{
		FFileHelper::SaveStringToFile(Text, *FPaths::Combine(EvidenceDir, Name));
	}
}

void AEHGameDirector::AutoInject(int32 Device, EEHAction Action)
{
	RouterPtr->InjectAction(Device, Action, true);
	PendingRelease.Add(TPair<int32, EEHAction>(Device, Action));
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
	if (Got.pressed != Want.pressed || Got.x != Want.x)
	{
		AutoLogLine(FString::Printf(TEXT("WARN router mismatch p%d want(x=%d p=%d) got(x=%d p=%d)"), Player, Want.x, Want.pressed, Got.x, Got.pressed));
	}
	return Got;
}

void AEHGameDirector::TickAutomation(float DeltaSeconds)
{
	for (const TPair<int32, EEHAction>& R : PendingRelease)
	{
		RouterPtr->InjectAction(R.Key, R.Value, false);
	}
	PendingRelease.Reset();
	if (AutoLines.Num() == 0)
	{
		return;
	}
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
			const EEHAction A = ParseAction(Arg(2, TEXT("Light")));
			AutoInject(ParseDevice(Arg(1, TEXT("kbA"))), A);
			AutoLogLine(FString::Printf(TEXT("press %s %s screen=%d"), *Arg(1, TEXT("kbA")), EHActionName(A), static_cast<int32>(Screen)));
			AutoWait = 0.12f;
			return;
		}
		else if (Cmd == TEXT("hold") || Cmd == TEXT("release"))
		{
			// hold/release <device> <action>: a held direction or Block, for direction + button moves.
			const EEHAction A = ParseAction(Arg(2, TEXT("Right")));
			RouterPtr->InjectAction(ParseDevice(Arg(1, TEXT("kbA"))), A, Cmd == TEXT("hold"));
			AutoLogLine(FString::Printf(TEXT("%s %s %s"), *Cmd, *Arg(1, TEXT("kbA")), EHActionName(A)));
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
