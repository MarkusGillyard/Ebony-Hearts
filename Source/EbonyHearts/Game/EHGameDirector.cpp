#include "EHGameDirector.h"

#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "EHFighterVisual.h"
#include "EHVfx.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Texture2D.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/GameUserSettings.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace EHDirectorDetail
{
constexpr float VerticalFov = 30.0f;
constexpr float Aspect = 16.0f / 9.0f;
constexpr float MinCamDistance = 560.0f;
constexpr float MaxCamDistance = 860.0f;
constexpr float CamHeight = 135.0f;
constexpr float FloorMargin = 28.0f;

bool ReadContent(const FString& Relative, FString& Out)
{
	return FFileHelper::LoadFileToString(Out, *(FPaths::ProjectContentDir() / Relative));
}

float HorizontalFov()
{
	return 2.0f * FMath::RadiansToDegrees(FMath::Atan(FMath::Tan(FMath::DegreesToRadians(VerticalFov * 0.5f)) * Aspect));
}
}
using namespace EHDirectorDetail;

AEHGameDirector::AEHGameDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PrePhysics;
	PrimaryActorTick.bTickEvenWhenPaused = true;
}

bool AEHGameDirector::LoadData()
{
	FString RulesText;
	FString WrenText;
	FString AshkaText;
	FString PresText;
	if (!ReadContent(TEXT("Data/rules.json"), RulesText) || !ReadContent(TEXT("Data/Fighters/wren.json"), WrenText) ||
		!ReadContent(TEXT("Data/Fighters/ashka.json"), AshkaText) || !ReadContent(TEXT("Data/presentation.json"), PresText))
	{
		DataError = TEXT("Combat data files are missing from the package (Content/Data).");
		return false;
	}
	std::string Err;
	if (!eh::LoadRulesText(std::string(TCHAR_TO_UTF8(*RulesText)), Rules, Err) ||
		!eh::LoadCharacterText(std::string(TCHAR_TO_UTF8(*WrenText)), Chars[0], Err) ||
		!eh::LoadCharacterText(std::string(TCHAR_TO_UTF8(*AshkaText)), Chars[1], Err))
	{
		DataError = FString(UTF8_TO_TCHAR(Err.c_str()));
		return false;
	}
	FString PresError;
	if (!Pres.Load(PresText, PresError))
	{
		DataError = PresError;
		return false;
	}
	// Validate the cross-character setup once so a bad file is reported here, not mid-match.
	eh::Match Probe;
	if (!Probe.Setup(Rules, Chars[0], Chars[1], eh::Mode::Versus, Err))
	{
		DataError = FString(UTF8_TO_TCHAR(Err.c_str()));
		return false;
	}
	return true;
}

void AEHGameDirector::BeginPlay()
{
	Super::BeginPlay();
	Settings = FEHSettings::Load(&SettingsWarning);
	DiskDisplay = Settings;
	if (FParse::Param(FCommandLine::Get(), TEXT("safedisplay")))
	{
		Settings.WindowMode = 2;
		Settings.Resolution = FIntPoint(1280, 720);
	}
	// Launch flags override the saved display mode for this session only (used by evaluation runs).
	int32 ResX = 0;
	int32 ResY = 0;
	if (FParse::Value(FCommandLine::Get(), TEXT("ResX="), ResX) && FParse::Value(FCommandLine::Get(), TEXT("ResY="), ResY))
	{
		Settings.Resolution = FIntPoint(ResX, ResY);
		Settings.WindowMode = FParse::Param(FCommandLine::Get(), TEXT("fullscreen")) ? 0 : 2;
	}
	FParse::Bool(FCommandLine::Get(), TEXT("EHVSync="), Settings.bVSync);
	bSessionDisplayOverride = Settings.WindowMode != DiskDisplay.WindowMode || Settings.Resolution != DiskDisplay.Resolution || Settings.bVSync != DiskDisplay.bVSync;
	RouterPtr = MakeShared<FEHInputRouter>(&Settings.Bindings);
	RouterPtr->Register();
	const bool bDataOk = LoadData();
	FString FontMissing;
	Fonts.Load(FontMissing);
	if (!FontMissing.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("EbonyHearts: fonts missing: %s"), *FontMissing);
	}
	TitleTexture = LoadObject<UTexture2D>(nullptr, TEXT("/Game/UI/T_TitleCard.T_TitleCard"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (TitleTexture)
	{
		TitleBrush.SetResourceObject(TitleTexture);
		// The imported size is the artwork's true aspect even before the texture's platform data has streamed in.
		const FIntPoint Imported = TitleTexture->GetImportedSize();
		TitleBrush.ImageSize = Imported.X > 0 && Imported.Y > 0 ? FVector2D(Imported.X, Imported.Y) : FVector2D(TitleTexture->GetSizeX(), TitleTexture->GetSizeY());
		TitleBrush.DrawAs = ESlateBrushDrawType::Image;
	}
	Audio.Init(GetWorld());
	SpawnWorldActors();
	ApplySettings(true);
	if (GEngine && GEngine->GameViewport)
	{
		Canvas = SNew(SEHCanvas).Director(this);
		GEngine->GameViewport->AddViewportWidgetContent(Canvas.ToSharedRef(), 10);
	}
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		PC->bShowMouseCursor = false;
		PC->SetInputMode(FInputModeGameOnly());
		PC->SetViewTarget(Camera);
	}
	// A showcase match keeps both fighters idling in the Chapel behind the menus.
	SlotChar[0] = 0;
	SlotChar[1] = 1;
	Match = MakeUnique<eh::Match>();
	std::string Err;
	if (bDataOk)
	{
		Match->Setup(Rules, Chars[0], Chars[1], eh::Mode::Training, Err);
		ConfigureVisuals();
	}
	Audio.StartAmbience(TEXT("ChapelBed"));
	Audio.StartMusic(TEXT("Theme"));
	InitAutomation();
	GoTo(bDataOk ? EEHScreen::Title : EEHScreen::Error);
	if (!SettingsWarning.IsEmpty())
	{
		ShowToast(SettingsWarning);
	}
}

void AEHGameDirector::EndPlay(const EEndPlayReason::Type Reason)
{
	if (RouterPtr.IsValid())
	{
		RouterPtr->Unregister();
	}
	if (Canvas.IsValid() && GEngine && GEngine->GameViewport)
	{
		GEngine->GameViewport->RemoveViewportWidgetContent(Canvas.ToSharedRef());
	}
	Canvas.Reset();
	Super::EndPlay(Reason);
}

void AEHGameDirector::SpawnWorldActors()
{
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	for (int32 i = 0; i < 2; ++i)
	{
		Visual[i] = GetWorld()->SpawnActor<AEHFighterVisual>(AEHFighterVisual::StaticClass(), FTransform::Identity, Params);
	}
	Vfx = GetWorld()->SpawnActor<AEHVfx>(AEHVfx::StaticClass(), FTransform::Identity, Params);
	Vfx->Init(Settings.bReduceFlash);
	Camera = GetWorld()->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), FTransform(FRotator(0, -90, 0), CamPos), Params);
	UCameraComponent* Cam = Camera->GetCameraComponent();
	Cam->SetFieldOfView(HorizontalFov());
	Cam->SetConstraintAspectRatio(true);
	Cam->SetAspectRatio(Aspect);
}

void AEHGameDirector::ConfigureVisuals()
{
	const bool bMirror = SlotChar[0] == SlotChar[1];
	bAnyGraybox = false;
	for (int32 i = 0; i < 2; ++i)
	{
		Visual[i]->Setup(Pres.Get(SlotChar[i] == 0 ? TEXT("wren") : TEXT("ashka")), i, bMirror);
		bAnyGraybox = bAnyGraybox || Visual[i]->UsesGraybox();
		PrevX[i] = Match->State().f[i].x;
	}
}

void AEHGameDirector::ApplySettings(bool bDisplay)
{
	Settings.Clamp();
	Audio.SetVolumes(Settings.MasterVolume, Settings.MusicVolume, Settings.EffectsVolume, Settings.AmbienceVolume);
	if (Vfx)
	{
		Vfx->SetReduceFlash(Settings.bReduceFlash);
	}
	CpuLevel = Settings.CpuLevel;
	if (!bDisplay || GEngine == nullptr)
	{
		return;
	}
	UGameUserSettings* G = GEngine->GetGameUserSettings();
	if (G == nullptr)
	{
		return;
	}
	const EWindowMode::Type WM = Settings.WindowMode == 0 ? EWindowMode::Fullscreen : (Settings.WindowMode == 1 ? EWindowMode::WindowedFullscreen : EWindowMode::Windowed);
	G->SetFullscreenMode(WM);
	if (WM != EWindowMode::WindowedFullscreen)
	{
		G->SetScreenResolution(Settings.Resolution);
	}
	else
	{
		G->SetScreenResolution(G->GetDesktopResolution());
	}
	G->SetVSyncEnabled(Settings.bVSync);
	G->SetFrameRateLimit(static_cast<float>(Settings.FrameCap));
	G->SetOverallScalabilityLevel(Settings.Quality);
	// Unreal's resolution scale runs 0-100 %, so the setting is passed as the percentage it shows.
	G->SetResolutionScaleValueEx(static_cast<float>(Settings.RenderScale));
	G->ApplySettings(false);
}

bool AEHGameDirector::WriteSettings() const
{
	FEHSettings ToSave = Settings;
	if (bSessionDisplayOverride)
	{
		ToSave.WindowMode = DiskDisplay.WindowMode;
		ToSave.Resolution = DiskDisplay.Resolution;
		ToSave.bVSync = DiskDisplay.bVSync;
	}
	return ToSave.Save();
}

void AEHGameDirector::SaveSettings()
{
	if (!WriteSettings())
	{
		ShowToast(TEXT("Settings could not be saved."));
	}
}

void AEHGameDirector::ShowToast(const FString& Text)
{
	Toast = Text;
	ToastAge = 0.0f;
}

FVector AEHGameDirector::SimToWorld(int32 X, int32 Y) const
{
	return FVector(X / static_cast<float>(eh::kUnitsPerCm), 0.0f, Y / static_cast<float>(eh::kUnitsPerCm));
}

void AEHGameDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	RenderTime += DeltaSeconds;
	ScreenAge += DeltaSeconds;
	ToastAge += DeltaSeconds;
	if (bRecordFrames)
	{
		FrameTimes.Add(DeltaSeconds * 1000.0f);
	}
	HandleConnections();
	TickAutomation(DeltaSeconds);
	HandleNav();

	float Alpha = 0.0f;
	const bool bFocusLost = FSlateApplication::IsInitialized() && !FSlateApplication::Get().IsActive() && !FParse::Param(FCommandLine::Get(), TEXT("EHNoFocusPause"));
	if (bMatchActive && Screen == EEHScreen::Match && bFocusLost && !bPaused && Mode != EEHMode::Training)
	{
		SetPaused(true, SlotDevice[0]);
	}
	if (Match.IsValid() && DataError.IsEmpty())
	{
		// A real match only advances on the match screen while unpaused; the menu showcase always idles.
		const bool bRun = bMatchActive ? (Screen == EEHScreen::Match && !bPaused) : true;
		if (bRun)
		{
			const int32 Steps = Clock.Advance(static_cast<int64>(static_cast<double>(DeltaSeconds) * 1e9));
			for (int32 i = 0; i < Steps; ++i)
			{
				SimStep();
			}
			Alpha = static_cast<float>(Clock.Alpha());
		}
		else
		{
			Clock.Reset();
		}
		UpdatePresentation(DeltaSeconds, Alpha);
	}
}

eh::InputFrame AEHGameDirector::SlotInput(int32 Player)
{
	if (!bMatchActive || Screen != EEHScreen::Match)
	{
		return eh::InputFrame();
	}
	if (bAutoBot[Player])
	{
		return AutoBotInput(Player);
	}
	if (Mode == EEHMode::Tutorial && Player == 1)
	{
		return LessonScriptInput();
	}
	if (SlotCpu[Player])
	{
		return Cpu[Player].Decide(*Match);
	}
	return RouterPtr->SampleForTick(SlotDevice[Player]);
}

void AEHGameDirector::SimStep()
{
	eh::InputFrame In[2];
	for (int32 i = 0; i < 2; ++i)
	{
		In[i] = SlotInput(i);
	}
	for (int32 i = 0; i < 2; ++i)
	{
		PrevX[i] = Match->State().f[i].x;
	}
	Match->Tick(In);
	if (!bMatchActive)
	{
		return;
	}
	for (int32 i = 0; i < 2; ++i)
	{
		RecordInput(i, In[i]);
		UpdateFrameData(i);
	}
	if ((Mode == EEHMode::Training && bInfiniteMeter) || Mode == EEHMode::Tutorial)
	{
		for (int32 i = 0; i < 2; ++i)
		{
			if (Mode == EEHMode::Training || i == 0)
			{
				Match->SetMeter(i, Rules.meterMax);
			}
		}
	}
	++Stats.Frames;
	ProcessEvents();
	const eh::MatchState& S = Match->State();
	if (S.phase == eh::Phase::MatchEnd && !bResultsShown && S.phaseFrame > 150)
	{
		bResultsShown = true;
		LastWinner = S.matchWinner;
		AutoMatches += 1;
		AutoLogLine(FString::Printf(TEXT("match_end mode=%d p0=%s p1=%s winner=%d rounds=%d-%d frames=%d dmg=%d/%d"), static_cast<int32>(Mode),
			SlotChar[0] == 0 ? TEXT("wren") : TEXT("ashka"), SlotChar[1] == 0 ? TEXT("wren") : TEXT("ashka"), S.matchWinner,
			S.f[0].roundWins, S.f[1].roundWins, Stats.Frames, Stats.Damage[0], Stats.Damage[1]));
		GoTo(EEHScreen::Results);
	}
}

void AEHGameDirector::RecordInput(int32 Player, const eh::InputFrame& In)
{
	// Input history shows held state runs; a new entry starts whenever direction or buttons change.
	TArray<FEHInputLogEntry>& Log = InputLog[Player];
	const uint8 Held = static_cast<uint8>(In.held | In.pressed);
	const int8 X = static_cast<int8>(In.x * Match->State().f[Player].facing);   // shown relative to facing
	if (Log.Num() > 0 && Log.Last().X == X && Log.Last().Held == Held && In.pressed == 0)
	{
		Log.Last().Frames = FMath::Min(Log.Last().Frames + 1, 999);
		return;
	}
	Log.Add(FEHInputLogEntry{X, Held, 1});
	if (Log.Num() > 18)
	{
		Log.RemoveAt(0);
	}
}

void AEHGameDirector::UpdateFrameData(int32 Player)
{
	const eh::FighterState& F = Match->State().f[Player];
	if (F.state != eh::FState::Attack || F.moveFrame != 1)
	{
		return;
	}
	const eh::MoveDef& M = Match->Character(Player).moves[static_cast<size_t>(F.move)];
	LastMoveName[Player] = UTF8_TO_TCHAR(M.name.c_str());
	if (M.hits.empty())
	{
		LastMoveFrames[Player] = FString::Printf(TEXT("Total %d"), M.total);
	}
	else
	{
		const int32 First = M.hits.front().frames.first;
		const int32 Last = M.LastActiveFrame();
		LastMoveFrames[Player] = FString::Printf(TEXT("Startup %d  Active %d  Recovery %d"), First, Last - First + 1, M.total - Last);
	}
}

void AEHGameDirector::ProcessEvents()
{
	const eh::MatchState& S = Match->State();
	const bool bReduceShake = Settings.bReduceShake;
	for (const eh::Event& E : Match->Events())
	{
		const int32 A = E.player;
		const FVector At = SimToWorld(E.x, E.y);
		const FString CharA = (A >= 0 && A < 2) ? (SlotChar[A] == 0 ? FString(TEXT("wren")) : FString(TEXT("ashka"))) : FString();
		const FString MoveA = (A >= 0 && A < 2) ? EHMoveId(*Match, A, E.move) : FString();
		const FEHMovePresentation* MP = (A >= 0 && A < 2) ? Pres.Move(CharA, MoveA) : nullptr;
		switch (E.type)
		{
		case eh::EventType::RoundIntro:
		{
			const bool bFinal = S.f[0].roundWins == Rules.roundsToWin - 1 && S.f[1].roundWins == Rules.roundsToWin - 1;
			Banners.Add(FEHBanner{bFinal ? TEXT("FINAL ROUND") : FString::Printf(TEXT("ROUND %d"), E.value), FString(), 0.0f, 1.6f, FLinearColor(0.92f, 0.86f, 0.74f)});
			Audio.Play(TEXT("RoundBell"), EEHSoundCat::Effects, 0.9f);
			break;
		}
		case eh::EventType::Fight:
			Banners.Add(FEHBanner{TEXT("FIGHT"), FString(), 0.0f, 0.9f, FLinearColor(1.0f, 0.82f, 0.45f)});
			Audio.Play(TEXT("FightStinger"), EEHSoundCat::Effects, 0.9f);
			break;
		case eh::EventType::MoveStart:
			if (MP && !MP->Whoosh.IsNone())
			{
				Audio.PlayVaried(MP->Whoosh, 3, EEHSoundCat::Effects, 0.55f);
			}
			if (MP && MP->bFlame)
			{
				Audio.Play(TEXT("FlameIgnite"), EEHSoundCat::Effects, 0.6f);
			}
			break;
		case eh::EventType::Hit:
		{
			const bool bHeavy = (E.flags & eh::EvHeavy) != 0;
			const bool bEnergy = (E.flags & eh::EvEnergy) != 0;
			const bool bAura = (E.flags & eh::EvAura) != 0;
			const bool bCounter = (E.flags & eh::EvCounter) != 0;
			Vfx->Hit(At, S.f[A].facing, bHeavy, bEnergy, bAura, bCounter);
			Audio.PlayVaried(bHeavy ? FName(TEXT("HitHeavy")) : FName(TEXT("HitLight")), 3, EEHSoundCat::Effects, 0.95f);
			if (bEnergy)
			{
				Audio.Play(TEXT("FlameHit"), EEHSoundCat::Effects, 0.7f);
			}
			if (bAura)
			{
				Audio.Play(TEXT("AuraHit"), EEHSoundCat::Effects, 0.6f);
			}
			const float Shake = (bHeavy ? 1.0f : 0.35f) + (MP ? MP->Shake : 0.0f);
			CamShake = FMath::Max(CamShake, Shake * (bReduceShake ? 0.25f : 1.0f));
			Stats.Damage[A] += E.value;
			const int32 D = 1 - A;
			Stats.MaxCombo[A] = FMath::Max(Stats.MaxCombo[A], S.f[D].combo);
			LastHitAge[D] = 0.0f;
			if (bCounter)
			{
				Callouts.Add(FEHCallout{TEXT("COUNTER"), A, 0.0f, 0.9f, FLinearColor(1.0f, 0.78f, 0.30f)});
			}
			else if (E.flags & eh::EvPunish)
			{
				Callouts.Add(FEHCallout{TEXT("PUNISH"), A, 0.0f, 0.9f, FLinearColor(0.95f, 0.35f, 0.30f)});
			}
			if (E.flags & eh::EvTrade)
			{
				Callouts.Add(FEHCallout{TEXT("TRADE"), A, 0.0f, 0.7f, FLinearColor(0.8f, 0.8f, 0.8f)});
			}
			break;
		}
		case eh::EventType::Block:
			Vfx->Block(At, S.f[A].facing, false);
			Audio.PlayVaried(TEXT("Block"), 2, EEHSoundCat::Effects, 0.75f);
			break;
		case eh::EventType::Deflect:
			Vfx->Block(At, S.f[A].facing, true);
			Audio.Play(TEXT("Deflect"), EEHSoundCat::Effects, 0.9f);
			Callouts.Add(FEHCallout{TEXT("DEFLECT"), 1 - A, 0.0f, 0.9f, FLinearColor(0.95f, 0.92f, 0.70f)});
			Stats.Deflects[1 - A] += 1;
			break;
		case eh::EventType::ThrowConnect:
			Audio.Play(TEXT("Grab"), EEHSoundCat::Effects, 0.8f);
			break;
		case eh::EventType::ThrowDamage:
			Audio.PlayVaried(TEXT("BodySlam"), 2, EEHSoundCat::Effects, 1.0f);
			Vfx->Splash(SimToWorld(S.f[1 - A].x, 0), 1.3f);
			CamShake = FMath::Max(CamShake, bReduceShake ? 0.3f : 1.1f);
			Stats.Damage[A] += E.value;
			Stats.Throws[A] += 1;
			break;
		case eh::EventType::ThrowTech:
			Vfx->Tech(At);
			Audio.Play(TEXT("Tech"), EEHSoundCat::Effects, 0.85f);
			Callouts.Add(FEHCallout{TEXT("ESCAPE"), 1 - A, 0.0f, 0.9f, FLinearColor(0.70f, 0.85f, 1.0f)});
			break;
		case eh::EventType::AuraStart:
			Vfx->AuraFlash(SimToWorld(S.f[A].x, 110 * eh::kUnitsPerCm));
			Audio.Play(TEXT("AuraIgnite"), EEHSoundCat::Effects, 0.9f);
			Callouts.Add(FEHCallout{TEXT("SPIRIT ENHANCED"), A, 0.0f, 1.2f, FLinearColor(1.0f, 0.80f, 0.35f)});
			break;
		case eh::EventType::AuraEnd:
			Audio.Play(TEXT("AuraFade"), EEHSoundCat::Effects, 0.5f);
			break;
		case eh::EventType::KO:
			Banners.Add(FEHBanner{S.doubleKO ? TEXT("DOUBLE K.O.") : TEXT("K.O."), FString(), 0.0f, 1.8f, FLinearColor(0.85f, 0.12f, 0.10f)});
			Audio.Play(TEXT("KO"), EEHSoundCat::Effects, 1.0f);
			CamShake = FMath::Max(CamShake, bReduceShake ? 0.4f : 1.4f);
			break;
		case eh::EventType::Timeout:
			Banners.Add(FEHBanner{TEXT("TIME"), FString(), 0.0f, 1.6f, FLinearColor(0.9f, 0.85f, 0.75f)});
			Audio.Play(TEXT("KO"), EEHSoundCat::Effects, 0.6f);
			break;
		case eh::EventType::RoundEnd:
			if (E.player == 0 || E.player == 1)
			{
				const FText Name = Pres.Get(SlotChar[E.player] == 0 ? TEXT("wren") : TEXT("ashka")).DisplayName;
				Banners.Add(FEHBanner{FString(), FString::Printf(TEXT("%s takes the round"), *Name.ToString()), 1.4f, 3.0f, FLinearColor::White});
			}
			else
			{
				Banners.Add(FEHBanner{FString(), TEXT("Draw"), 1.4f, 3.0f, FLinearColor::White});
			}
			break;
		case eh::EventType::MatchEnd:
			Audio.SetMusicDuck(0.5f);
			break;
		default:
			break;
		}
		if (Mode == EEHMode::Tutorial)
		{
			UpdateLesson(E);
		}
	}
}

void AEHGameDirector::UpdatePresentation(float DeltaSeconds, float Alpha)
{
	const eh::MatchState& S = Match->State();
	for (int32 i = 0; i < 2; ++i)
	{
		const eh::FighterState& F = S.f[i];
		const float Frozen = F.hitstop > 0 ? 0.0f : Alpha;
		Visual[i]->UpdateVisual(*Match, PrevX[i], Frozen, DeltaSeconds, RenderTime);
		// Spirit Enhanced Strikes: steady golden lightning that flickers in its last second.
		float Aura = 0.0f;
		if (F.auraFrames > 0)
		{
			Aura = F.auraFrames < 60 ? (FMath::Sin(static_cast<float>(RenderTime) * 40.0f) > 0.0f ? 0.8f : 0.25f) : 1.0f;
		}
		Visual[i]->SetAuraIntensity(Aura);
		// Lamplighter Flame accents ride the striking limb around the active frames of flame moves.
		if (F.state == eh::FState::Attack)
		{
			const eh::MoveDef& M = Match->Character(i).moves[static_cast<size_t>(F.move)];
			const FString CharId = SlotChar[i] == 0 ? TEXT("wren") : TEXT("ashka");
			const FEHMovePresentation* MP = Pres.Move(CharId, UTF8_TO_TCHAR(M.id.c_str()));
			if (MP && MP->bFlame && !M.hits.empty())
			{
				const int32 First = M.hits.front().frames.first;
				if (F.moveFrame >= First - 6 && F.moveFrame <= M.LastActiveFrame() + 4 && FMath::Fmod(RenderTime, 0.05) < DeltaSeconds)
				{
					const FVector Fallback = SimToWorld(F.x + F.facing * 60 * eh::kUnitsPerCm, 120 * eh::kUnitsPerCm);
					Vfx->Flame(Visual[i]->BoneLocation(MP->FxBone, Fallback), M.id == "BS" ? 1.6f : 0.8f);
				}
				if (M.id == "BS" && F.moveFrame == First && F.hitstop == 0)
				{
					Vfx->FlameBurst(SimToWorld(F.x, 0), F.facing);
				}
			}
		}
		// Water underfoot: ripples while walking, a splash when a fighter hits the floor.
		if (F.state == eh::FState::Neutral && F.walk != 0)
		{
			FootTimer[i] += DeltaSeconds;
			if (FootTimer[i] > 0.30f)
			{
				FootTimer[i] = 0.0f;
				Vfx->Ripple(SimToWorld(F.x, 0) + FVector(FMath::FRandRange(-12.0f, 12.0f), FMath::FRandRange(-10.0f, 10.0f), 0), 0.8f);
				Audio.PlayVaried(TEXT("StepWater"), 3, EEHSoundCat::Effects, 0.35f);
			}
		}
		if ((F.state == eh::FState::Knockdown || F.state == eh::FState::KO) && F.stateFrame == 16 && F.hitstop == 0)
		{
			if (LastSplash[i] != S.frame - F.stateFrame)
			{
				LastSplash[i] = S.frame - F.stateFrame;
				Vfx->Splash(SimToWorld(F.x - F.facing * 60 * eh::kUnitsPerCm, 0), 1.2f);
				Audio.PlayVaried(TEXT("BodyFall"), 2, EEHSoundCat::Effects, 0.9f);
			}
		}
		const float Target = static_cast<float>(F.health) / static_cast<float>(Match->Character(i).maxHealth);
		LastHitAge[i] += DeltaSeconds;
		if (LastHitAge[i] > 0.6f || Target > HealthLag[i])
		{
			HealthLag[i] = FMath::FInterpTo(HealthLag[i], Target, DeltaSeconds, 3.0f);
		}
	}
	for (FEHBanner& B : Banners)
	{
		B.Age += DeltaSeconds;
	}
	Banners.RemoveAll([](const FEHBanner& B) { return B.Age > B.Life; });
	for (FEHCallout& C : Callouts)
	{
		C.Age += DeltaSeconds;
	}
	Callouts.RemoveAll([](const FEHCallout& C) { return C.Age > C.Life; });
	UpdateCamera(DeltaSeconds);
}

void AEHGameDirector::UpdateCamera(float DeltaSeconds)
{
	const eh::MatchState& S = Match->State();
	const float TanH = FMath::Tan(FMath::DegreesToRadians(HorizontalFov() * 0.5f));
	FVector Target;
	if (Screen == EEHScreen::Match || Screen == EEHScreen::Results)
	{
		const float X0 = S.f[0].x / static_cast<float>(eh::kUnitsPerCm);
		const float X1 = S.f[1].x / static_cast<float>(eh::kUnitsPerCm);
		const float Sep = FMath::Abs(X0 - X1);
		const float Dist = FMath::Clamp((Sep * 0.5f + 150.0f) / TanH, MinCamDistance, MaxCamDistance);
		const float HalfView = Dist * TanH;
		const float Edge = Rules.stageHalfWidth / static_cast<float>(eh::kUnitsPerCm) + 70.0f;
		const float Mid = FMath::Clamp((X0 + X1) * 0.5f, -Edge + HalfView, Edge - HalfView);
		Target = FVector(Mid, Dist, CamHeight);
	}
	else
	{
		// Menus: a slow drift across the nave that keeps both fighters and the rose window in view.
		MenuOrbit += DeltaSeconds * 0.08f;
		Target = FVector(FMath::Sin(MenuOrbit) * 120.0f, 840.0f, CamHeight);
	}
	const float Rate = (Screen == EEHScreen::Match) ? 9.0f : 2.0f;
	CamPos = FMath::VInterpTo(CamPos, Target, DeltaSeconds, Rate);
	// Tilt up as far as the framing allows: the floor line stays FloorMargin below the bottom edge at the
	// fighting plane, so feet are never cropped and a wider shot reveals more of the rose window.
	const float BottomAngle = FMath::RadiansToDegrees(FMath::Atan((CamPos.Z + FloorMargin) / FMath::Max(CamPos.Y, 1.0f)));
	const float Pitch = VerticalFov * 0.5f - BottomAngle;
	CamShake = FMath::Max(0.0f, CamShake - DeltaSeconds * 4.5f);
	const float Amp = CamShake * CamShake * 3.2f;
	const FVector Shake(FMath::Sin(static_cast<float>(RenderTime) * 71.0f) * Amp, 0.0f, FMath::Sin(static_cast<float>(RenderTime) * 53.0f + 1.3f) * Amp);
	Camera->SetActorLocationAndRotation(CamPos + Shake, FRotator(Pitch, -90.0f, 0.0f));
}

void AEHGameDirector::StartMatch()
{
	Match = MakeUnique<eh::Match>();
	const bool bTraining = Mode == EEHMode::Training || Mode == EEHMode::Tutorial;
	std::string Err;
	if (!Match->Setup(Rules, Chars[SlotChar[0]], Chars[SlotChar[1]], bTraining ? eh::Mode::Training : eh::Mode::Versus, Err))
	{
		DataError = UTF8_TO_TCHAR(Err.c_str());
		GoTo(EEHScreen::Error);
		return;
	}
	const uint32 Seed = static_cast<uint32>(FPlatformTime::Cycles());
	for (int32 i = 0; i < 2; ++i)
	{
		Cpu[i].Setup(i, static_cast<eh::CpuLevel>(FMath::Clamp(CpuLevel, 0, 2)), Seed + i * 7919u);
		InputLog[i].Reset();
		LastMoveName[i].Reset();
		LastMoveFrames[i].Reset();
		HealthLag[i] = 1.0f;
	}
	if (Mode == EEHMode::Training)
	{
		const int32 DummySlot = SlotCpu[0] ? 0 : 1;
		Cpu[DummySlot].SetDummy(Dummy);
		Match->TrainingResetPositions(TrainingLayout);
	}
	ConfigureVisuals();
	Clock.Reset();
	bMatchActive = true;
	bPaused = false;
	bResultsShown = false;
	Stats = FEHStats();
	Banners.Reset();
	Callouts.Reset();
	DisconnectNotice.Reset();
	AssignGamepadPlayers();
	RouterPtr->ClearLatches();
	if (Mode == EEHMode::Tutorial)
	{
		SetupLesson();
	}
	Audio.SetMusicDuck(1.0f);
	Audio.StartMusic(bTraining ? TEXT("Training") : TEXT("Battle"));
	AutoLogLine(FString::Printf(TEXT("match_start mode=%d p0=%d p1=%d cpu=%d/%d level=%d"), static_cast<int32>(Mode), SlotChar[0], SlotChar[1], SlotCpu[0], SlotCpu[1], CpuLevel));
	GoTo(EEHScreen::Match);
}

void AEHGameDirector::Rematch()
{
	StartMatch();
}

void AEHGameDirector::LeaveMatch(EEHScreen To)
{
	bPaused = false;
	bMatchActive = false;
	RouterPtr->ClearGamepadPlayers();
	// Return to the idle showcase behind the menus.
	Mode = EEHMode::VersusCpu;
	std::string Err;
	Match = MakeUnique<eh::Match>();
	Match->Setup(Rules, Chars[SlotChar[0]], Chars[SlotChar[1]], eh::Mode::Training, Err);
	ConfigureVisuals();
	Audio.SetMusicDuck(1.0f);
	Audio.StartMusic(TEXT("Theme"));
	GoTo(To);
}

void AEHGameDirector::SetPaused(bool bPause, int32 Owner)
{
	bPaused = bPause;
	PauseOwner = Owner;
	Audio.SetMusicDuck(bPause ? 0.45f : 1.0f);
	Audio.Play(bPause ? FName(TEXT("UiOpen")) : FName(TEXT("UiClose")), EEHSoundCat::Ui, 0.7f);
	if (bPause)
	{
		BuildPauseMenu();
	}
	else
	{
		Menu.Reset();
		RouterPtr->ClearLatches();
		Clock.Reset();
	}
}

void AEHGameDirector::HandleConnections()
{
	int32 Device = EHDeviceNone;
	bool bConnected = false;
	while (RouterPtr->PopConnectionChange(Device, bConnected))
	{
		const FEHDevice* D = RouterPtr->FindDevice(Device);
		const FString Name = D ? D->Name : TEXT("Controller");
		static const TCHAR* Kinds[] = {TEXT("keyboard"), TEXT("playstation"), TEXT("xbox"), TEXT("generic")};
		AutoLogLine(FString::Printf(TEXT("device %s key=%d name=%s kind=%s"), bConnected ? TEXT("connected") : TEXT("disconnected"), Device, *Name,
			Kinds[static_cast<int32>(RouterPtr->KindOf(Device))]));
		if (!bConnected && Screen == EEHScreen::Match && (SlotDevice[0] == Device || SlotDevice[1] == Device))
		{
			const int32 Player = SlotDevice[0] == Device ? 0 : 1;
			DisconnectNotice = FString::Printf(TEXT("Player %d's controller disconnected. Reconnect it, or press a button on another device to take over."), Player + 1);
			if (!bPaused)
			{
				SetPaused(true, EHDeviceNone);
			}
		}
		else if (bConnected)
		{
			ShowToast(FString::Printf(TEXT("%s connected"), *Name));
			if (!DisconnectNotice.IsEmpty())
			{
				for (int32 i = 0; i < 2; ++i)
				{
					const FEHDevice* Slot = RouterPtr->FindDevice(SlotDevice[i]);
					if (!SlotCpu[i] && (Slot == nullptr || !Slot->bConnected))
					{
						SlotDevice[i] = Device;
					}
				}
				AssignGamepadPlayers();
				DisconnectNotice.Reset();
			}
		}
	}
}

void AEHGameDirector::AssignGamepadPlayers()
{
	// In Local Versus each controller uses its player's layout; in every other mode the one human uses player one's.
	RouterPtr->ClearGamepadPlayers();
	if (bMatchActive && Mode == EEHMode::Versus)
	{
		for (int32 i = 0; i < 2; ++i)
		{
			if (!SlotCpu[i])
			{
				RouterPtr->SetGamepadPlayer(SlotDevice[i], i);
			}
		}
	}
}
