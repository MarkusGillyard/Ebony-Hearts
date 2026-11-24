// First-person play in the Drowned Chapel. The director keeps owning settings, menus, devices and
// automation; each frame it turns device state into one FEHFirstPersonInput for the player character.
#include "EHGameDirector.h"
#include "EHUIStyle.h"

#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/LightComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EHMagic.h"
#include "EHAlignment.h"
#include "EHWolf.h"
#include "NavigationSystem.h"
#include "NavigationPath.h"
#include "EHPlayerCharacter.h"
#include "EHViewArms.h"
#include "EHVfx.h"
#include "Kismet/GameplayStatics.h"
#include "UnrealClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Components/PlanarReflectionComponent.h"
#include "Engine/PlanarReflection.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace EHFirstPersonDetail
{
FEHMenuItem FPButton(const FString& Label, TFunction<void()> Activate, const FString& Hint = FString())
{
	FEHMenuItem I;
	I.Label = Label;
	I.Activate = MoveTemp(Activate);
	I.Hint = Hint;
	return I;
}

FEHMenuItem FPHeader(const FString& Label)
{
	FEHMenuItem I;
	I.Label = Label;
	I.bHeader = true;
	return I;
}

// Radial dead zone, rescaled so the response starts at zero just outside it.
FVector2D StickValue(float X, float Y, float DeadZone)
{
	const FVector2D V(X, Y);
	const float Mag = V.Size();
	if (Mag <= DeadZone || Mag <= KINDA_SMALL_NUMBER)
	{
		return FVector2D::ZeroVector;
	}
	const float Scaled = FMath::Clamp((Mag - DeadZone) / (1.0f - DeadZone), 0.0f, 1.0f);
	return V / Mag * Scaled;
}

uint32 Bit(EEHAction A) { return 1u << static_cast<uint32>(A); }

// The player's spells, in the selector's order (the wheel puts the first on the left).
struct FEHSpellEntry
{
	EEHFistAction Action;
	EEHAction Binding;
	const TCHAR* Name;
	FLinearColor Color;
};
const FEHSpellEntry Spells[] = {
	{EEHFistAction::Fireball, EEHAction::FPFireball, TEXT("Fireball"), FLinearColor(1.0f, 0.5f, 0.16f)},
	{EEHFistAction::IceWall, EEHAction::FPIceWall, TEXT("Ice Wall"), FLinearColor(0.45f, 0.75f, 1.0f)},
};
constexpr int32 SpellCount = UE_ARRAY_COUNT(Spells);
// Wheel: the centre angle of spell I (degrees, 0 = right, counter-clockwise); two spells sit left and right.
float WheelAngle(int32 I) { return SpellCount == 2 ? (I == 0 ? 180.0f : 0.0f) : 90.0f - I * 360.0f / SpellCount; }
}
using namespace EHFirstPersonDetail;

bool AEHGameDirector::LoadFirstPersonData()
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *(FPaths::ProjectContentDir() / TEXT("Data/firstperson.json"))))
	{
		DataError = TEXT("First-person data is missing from the package (Content/Data/firstperson.json).");
		return false;
	}
	FString Err;
	if (!FPTuning.Load(Text, Err))
	{
		DataError = Err;
		return false;
	}
	return true;
}

void AEHGameDirector::BeginFirstPerson()
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	AEHPlayerCharacter* Pawn = PC ? Cast<AEHPlayerCharacter>(PC->GetPawn()) : nullptr;
	if (Pawn == nullptr)
	{
		return;
	}
	FPPlayer = Pawn;
	// Input is applied before the character moves in the same frame.
	FPPlayer->AddTickPrerequisiteActor(this);
	FPPlayer->GetCharacterMovement()->AddTickPrerequisiteActor(this);
	FPPlayer->ApplyTuning(FPTuning);
	ApplyFieldOfView();
	FPPlayer->ResetToStart();
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	FPDummy = GetWorld()->SpawnActor<AEHTrainingDummy>(AEHTrainingDummy::StaticClass(), FTransform(FRotator(0, FPTuning.Dummy.SpawnYaw, 0), FPTuning.Dummy.Spawn + FVector(0, 0, 92.0f)), Params);
	if (FPDummy)
	{
		FPDummy->Setup(FPTuning.Dummy, FPTuning.Fists, FPPlayer);
	}
	// The wolves' navigation: built once now from the Chapel's navigation proxies (the map carries no prebuilt
	// tiles); afterwards it updates itself around anything that changes, such as an Ice Wall.
	if (UNavigationSystemV1* NS = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld()))
	{
		const double T0 = FPlatformTime::Seconds();
		NS->Build();
		AutoLogLine(FString::Printf(TEXT("firstperson navigation built in %.0f ms"), (FPlatformTime::Seconds() - T0) * 1000.0));
	}
	SpawnWolf();
	CombatText.Tuning = FPTuning.CombatText;
	CombatText.Clear();
	// A Hero of Humanity is protected by the Chapel's wolves: the nearest one close by takes the blows meant for them.
	FPPlayer->SetAbsorber([this](float Damage, const FVector& From) {
		AEHWolf* W = FPAlignment == EHAlign::Hero ? NearestLiveWolf(FPPlayer->GetActorLocation(), FPTuning.Wolf.AbsorbRange) : nullptr;
		if (W == nullptr)
		{
			return false;
		}
		W->Absorb(Damage);
		AutoLogLine(FString::Printf(TEXT("fp wolf absorbed %.1f for the Hero of Humanity"), Damage));
		return true;
	});
	// The Chapel's water: one sheet per water mesh (the nave's basin at the tuned surface; the undercroft's crypt at its
	// mesh's height), each over its mesh's bounds. The Ice Wall, the player's wading and the ripples all read it.
	FPWater.Sheets.Reset();
	for (TActorIterator<AStaticMeshActor> It(GetWorld()); It; ++It)
	{
		const UStaticMesh* M = It->GetStaticMeshComponent() ? It->GetStaticMeshComponent()->GetStaticMesh() : nullptr;
		const bool bNave = M && M->GetName() == TEXT("SM_Water");
		if (bNave || (M && M->GetName() == TEXT("SM_IX_UnderWater")))
		{
			const FBox B = It->GetComponentsBoundingBox();
			FEHWaterSheet W;
			W.Bounds = FBox2D(FVector2D(B.Min.X, B.Min.Y), FVector2D(B.Max.X, B.Max.Y));
			W.SurfaceZ = bNave ? FPTuning.WaterSurfaceZ : B.Max.Z;
			FPWater.Sheets.Add(W);
		}
	}
	FPPlayer->SetWater(&FPWater);
	InitWorldClock();
	// Load every sound now, during start-up: loading one the first time it plays stalls that frame in a packaged build.
	const double PreloadStart = FPlatformTime::Seconds();
	const int32 Preloaded = Audio.PreloadAll();
	AutoLogLine(FString::Printf(TEXT("firstperson sounds preloaded %d in %.0f ms"), Preloaded, (FPlatformTime::Seconds() - PreloadStart) * 1000.0));
	// The rooms' own sounds (the forge's fire, the brazier, the crypt's tone), placed in the world.
	for (const FEHChapelSound& Snd : FPTuning.Chapel.Sounds)
	{
		Audio.PlayLoopAt(Snd.Name, Snd.At, Snd.Inner, Snd.Falloff, Snd.Volume);
	}
	PC->SetViewTarget(FPPlayer);
	PC->bShowMouseCursor = false;
	PC->SetInputMode(FInputModeGameOnly());
	AutoLogLine(FString::Printf(TEXT("firstperson start body=%d dummy=%d tuning: %s"), FPPlayer->HasBodyPlaceholder() ? 1 : 0, FPDummy && FPDummy->HasModel() ? 1 : 0, *FPTuning.Describe()));
	UE_LOG(LogTemp, Display, TEXT("EbonyHearts: first-person tuning %s"), *FPTuning.Describe());
}

void AEHGameDirector::Rumble(float Large, float Small, float Seconds)
{
	if (!Settings.bVibration || FPDevice < EHDeviceGamepadBase)
	{
		return;
	}
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		// Large motors on the left side, small on the right, as the engine names a pad's two motors.
		PC->PlayDynamicForceFeedback(FMath::Max(Large, Small), Seconds, Large > 0.0f, Small > 0.0f, Large > 0.0f, Small > 0.0f, EDynamicForceFeedbackAction::Start);
		++RumbleCount;
	}
}

void AEHGameDirector::PlayImpact(const TCHAR* Base, int32 Variants, float Volume, float Pitch)
{
	const FString Name = Variants > 1 ? FString::Printf(TEXT("%s_%02d"), Base, FMath::RandRange(1, Variants)) : FString(Base);
	Audio.Play(FName(*Name), EEHSoundCat::Effects, Volume, Pitch * FMath::FRandRange(0.96f, 1.04f));
}

void AEHGameDirector::ApplyFieldOfView()
{
	if (FPPlayer)
	{
		FPPlayer->SetFieldOfView(static_cast<float>(Settings.FieldOfView));
		FPPlayer->SetShakeScale(Settings.bReduceShake ? 0.0f : 1.0f);
	}
}

FEHFirstPersonInput AEHGameDirector::GatherFirstPersonInput(float DeltaSeconds)
{
	FEHFirstPersonInput In;
	// Read and drain every source each frame, so nothing collected during a pause or a menu acts afterwards.
	const FVector2D Mouse = RouterPtr->ConsumeMouseDelta();
	uint32 Presses = RouterPtr->TakePresses(EHDeviceKeyboardA);
	const uint32 KeyHeld = RouterPtr->HeldBits(EHDeviceKeyboardA);
	uint32 PadPresses = 0;
	uint32 PadHeld = 0;
	FVector2D PadMove = FVector2D::ZeroVector;
	FVector2D PadLook = FVector2D::ZeroVector;
	for (const TPair<int32, FEHDevice>& Pair : RouterPtr->Devices())
	{
		if (Pair.Key < EHDeviceGamepadBase || !Pair.Value.bConnected)
		{
			continue;
		}
		const uint32 P = RouterPtr->TakePresses(Pair.Key);
		const FVector2D M = StickValue(Pair.Value.Axes[0], Pair.Value.Axes[1], FPTuning.StickDeadZone);
		const FVector2D L = StickValue(Pair.Value.Axes[2], Pair.Value.Axes[3], FPTuning.StickDeadZone);
		if (P != 0 || M.SizeSquared() > 0.0f || L.SizeSquared() > 0.0f)
		{
			FPDevice = Pair.Key;
		}
		PadPresses |= P;
		PadHeld |= Pair.Value.Held;
		if (M.SizeSquared() > PadMove.SizeSquared()) PadMove = M;
		if (L.SizeSquared() > PadLook.SizeSquared()) PadLook = L;
	}
	if (Presses != 0 || KeyHeld != 0 || !Mouse.IsNearlyZero())
	{
		FPDevice = EHDeviceKeyboardA;
	}
	if (Screen != EEHScreen::FirstPerson || bPaused || FPPlayer == nullptr)
	{
		return In;
	}

	// Movement: keys are digital and normalised on diagonals; the stick keeps its analog size.
	FVector2D KeyMove(((KeyHeld & Bit(EEHAction::FPRight)) ? 1.0f : 0.0f) - ((KeyHeld & Bit(EEHAction::FPLeft)) ? 1.0f : 0.0f),
		((KeyHeld & Bit(EEHAction::FPForward)) ? 1.0f : 0.0f) - ((KeyHeld & Bit(EEHAction::FPBack)) ? 1.0f : 0.0f));
	KeyMove = KeyMove.GetSafeNormal();
	In.Move = KeyMove.SizeSquared() > 0.0f ? KeyMove : PadMove;

	// The spell selector: held, it takes the mouse and the right stick for choosing instead of looking.
	const bool bSelectHeld = ((KeyHeld | PadHeld) & Bit(EEHAction::FPSpellSelect)) != 0;
	EEHFistAction SelectedSpell = EEHFistAction::None;
	if (bSelectHeld && !bSpellSelect && !bPraying)
	{
		OpenSpellSelect();
	}
	const bool bSelectorOwnsLook = bSpellSelect;
	if (bSelectorOwnsLook)
	{
		if (Settings.SpellSelector == 0)
		{
			// Wheel: the mouse moves a pointer (about 120 counts to the rim); a tilted stick points directly.
			SpellPointer += FVector2D(Mouse.X, -Mouse.Y) / 120.0f;
			if (PadLook.Size() > 0.5f)
			{
				SpellPointer = FVector2D(PadLook.X, PadLook.Y);
			}
			if (SpellPointer.Size() > 1.0f)
			{
				SpellPointer = SpellPointer.GetSafeNormal();
			}
			SpellHighlight = -1;
			if (SpellPointer.Size() > 0.35f)
			{
				const float A = FMath::RadiansToDegrees(FMath::Atan2(SpellPointer.Y, SpellPointer.X));
				float Best = 1000.0f;
				for (int32 I = 0; I < SpellCount; ++I)
				{
					const float D = FMath::Abs(FMath::FindDeltaAngleDegrees(A, WheelAngle(I)));
					if (D < Best)
					{
						Best = D;
						SpellHighlight = I;
					}
				}
			}
		}
		else
		{
			// List: the mouse scrolls a row per 60 counts; a flick of the stick moves one row.
			SpellListScroll += Mouse.Y;
			while (SpellListScroll >= 60.0f) { SpellListScroll -= 60.0f; SpellHighlight = FMath::Min(SpellHighlight + 1, SpellCount - 1); }
			while (SpellListScroll <= -60.0f) { SpellListScroll += 60.0f; SpellHighlight = FMath::Max(SpellHighlight - 1, 0); }
			if (SpellHighlight == 0 && SpellListScroll < 0.0f) { SpellListScroll = 0.0f; }
			if (SpellHighlight == SpellCount - 1 && SpellListScroll > 0.0f) { SpellListScroll = 0.0f; }
			if (FMath::Abs(PadLook.Y) > 0.6f && !bSpellStickHeld)
			{
				SpellHighlight = FMath::Clamp(SpellHighlight + (PadLook.Y > 0.0f ? -1 : 1), 0, SpellCount - 1);
				bSpellStickHeld = true;
			}
			else if (FMath::Abs(PadLook.Y) < 0.3f)
			{
				bSpellStickHeld = false;
			}
		}
		if (!bSelectHeld)
		{
			SelectedSpell = CloseSpellSelect(true);
		}
	}
	const FVector2D LookMouse = bSelectorOwnsLook ? FVector2D::ZeroVector : Mouse;
	if (bSelectorOwnsLook)
	{
		PadLook = FVector2D::ZeroVector;
	}
	FPLockRawMouseX = static_cast<float>(LookMouse.X);
	FPLockRawStickX = static_cast<float>(PadLook.X);

	// Look: the mouse in degrees per count; the stick as a turn rate with a response curve, scaled by frame time.
	const float Invert = Settings.bInvertLook ? -1.0f : 1.0f;
	In.Look.X = static_cast<float>(LookMouse.X) * Settings.MouseSensitivity;
	In.Look.Y = -static_cast<float>(LookMouse.Y) * Settings.MouseSensitivity * Invert;
	if (PadLook.SizeSquared() > 0.0f)
	{
		const float Mag = PadLook.Size();
		const FVector2D Curved = PadLook / Mag * FMath::Pow(Mag, FPTuning.StickExponent);
		In.Look.X += Curved.X * FPTuning.StickYawDegPerSecond * Settings.StickSensitivity * DeltaSeconds;
		In.Look.Y += Curved.Y * FPTuning.StickPitchDegPerSecond * Settings.StickSensitivity * DeltaSeconds * Invert;
	}

	const bool bKeyJump = (Presses & Bit(EEHAction::FPJump)) != 0;
	const bool bPadJump = (PadPresses & Bit(EEHAction::FPJump)) != 0;
	In.bJumpPressed = bKeyJump || bPadJump;

	// Crouch: the keyboard holds (or toggles if set); a controller's stick press toggles.
	if ((PadPresses & Bit(EEHAction::FPCrouch)) || (Settings.bCrouchToggle && (Presses & Bit(EEHAction::FPCrouch))))
	{
		bFPCrouchToggled = !bFPCrouchToggled;
		if (bFPCrouchToggled)
		{
			bFPSprintToggled = false;
		}
	}
	// Sprint: the keyboard holds (or toggles if set); a controller's stick press toggles until the player stops.
	if ((PadPresses & Bit(EEHAction::FPSprint)) || (Settings.bSprintToggle && (Presses & Bit(EEHAction::FPSprint))))
	{
		bFPSprintToggled = !bFPSprintToggled;
		if (bFPSprintToggled)
		{
			bFPCrouchToggled = false;
		}
	}
	if (In.bJumpPressed)
	{
		bFPCrouchToggled = false;
	}
	const bool bKeyCrouch = !Settings.bCrouchToggle && (KeyHeld & Bit(EEHAction::FPCrouch)) != 0;
	const bool bKeySprint = !Settings.bSprintToggle && (KeyHeld & Bit(EEHAction::FPSprint)) != 0;
	if (bFPSprintToggled && (In.Move.Y < FPTuning.SprintForwardMin || FPPlayer->IsExhausted()))
	{
		bFPSprintToggled = false;   // a toggled sprint ends when the player stops running forward or runs out
	}
	if (bKeySprint)
	{
		bFPCrouchToggled = false;
	}
	In.bCrouch = bKeyCrouch || bFPCrouchToggled;
	In.bSprint = (bKeySprint || bFPSprintToggled) && !In.bCrouch;

	// Techniques: one press per frame reaches the fists (the straight first, so a jab-straight pressed together
	// still ends on the committed hit); the guard is held on any device.
	const uint32 AnyPress = Presses | PadPresses;
	In.FistPress = (AnyPress & Bit(EEHAction::FPStraight)) ? EEHFistAction::Straight
		: (AnyPress & Bit(EEHAction::FPJab)) ? EEHFistAction::Jab
		: (AnyPress & Bit(EEHAction::FPFireball)) ? EEHFistAction::Fireball
		: (AnyPress & Bit(EEHAction::FPIceWall)) ? EEHFistAction::IceWall : EEHFistAction::None;
	if (bSpellSelect)
	{
		In.FistPress = EEHFistAction::None;   // choosing: nothing else starts
	}
	else if (SelectedSpell != EEHFistAction::None)
	{
		In.FistPress = SelectedSpell;          // released on a spell: cast it now
	}
	bFPInteractPressed = (AnyPress & Bit(EEHAction::FPInteract)) != 0 && !bSpellSelect;
	bFPLockPressed = (AnyPress & Bit(EEHAction::FPLockOn)) != 0 && !bSpellSelect;
	In.bBlock = ((KeyHeld | PadHeld) & Bit(EEHAction::FPBlock)) != 0;
	if (In.FistPress != EEHFistAction::None || In.bBlock)
	{
		bFPSprintToggled = false;
	}
	return In;
}

void AEHGameDirector::TickFirstPerson(float DeltaSeconds)
{
	if (FPPlayer == nullptr)
	{
		BeginFirstPerson();
	}
	FEHFirstPersonInput In = GatherFirstPersonInput(DeltaSeconds);
	const bool bDeveloperKey = RouterPtr->TakeDeveloperKey();
#if !UE_BUILD_SHIPPING
	// F10: the developer panel (stats and resources live). Shipping builds never open it.
	if (bDeveloperKey && Screen == EEHScreen::FirstPerson && FPPlayer)
	{
		if (bPaused && bDevPanel)
		{
			bDevPanel = false;
			SetPaused(false, EHDeviceNone);
		}
		else if (!bPaused)
		{
			SetPaused(true, EHDeviceNone);
			BuildDeveloperPanel();
		}
	}
#else
	(void)bDeveloperKey;
#endif
	if (!bPaused)
	{
		bDevPanel = false;
	}
	else if (bSpellSelect)
	{
		CloseSpellSelect(false);   // pausing cancels the choice
	}
	SpellSelectAlpha = FMath::FInterpConstantTo(SpellSelectAlpha, bSpellSelect ? 1.0f : 0.0f, FApp::GetDeltaTime(), 10.0f);
	if (FPPlayer == nullptr || Screen != EEHScreen::FirstPerson || bPaused)
	{
		return;
	}
	TickWorldClock(FApp::GetDeltaTime());   // real time: the spell selector's slow motion does not slow the world's day
	FPPlayer->SetShadowForm(bFPShadow);
	if (FPExorcism >= 0.0f)
	{
		// The exorcism ending: nothing the player does matters now. Then a new life begins, from the title.
		In = FEHFirstPersonInput();
		FPExorcism += DeltaSeconds;
		if (FPExorcism >= 7.5f)
		{
			bFPShadow = false;
			FPShadowPrayHours = 0.0;
			FPAlignment = EHAlign::Platonic;
			FPPlayer->SetShadowForm(false);
			ResetFirstPerson(TEXT("exorcised"));
			AutoLogLine(TEXT("fp exorcism ends: a new life from the title"));
			GoTo(EEHScreen::Title);
			return;
		}
	}
	UpdateChapel(In, DeltaSeconds);
	UpdateLockOn(In, DeltaSeconds);
	LastFPInput = In;
	FPPlayer->ApplyInput(In, DeltaSeconds);
	if (Vfx)
	{
		Vfx->SetViewPoint(FPPlayer->Camera()->GetComponentLocation());
		Vfx->SetImpactScale(0.3f, 0.5f);
	}
	HurtFlash = FMath::Max(0.0f, HurtFlash - DeltaSeconds * 2.5f);
	if (FrameCaptureLeft > 0)
	{
		// Frame-by-frame review: the world runs at 1/20 speed and one screenshot is taken per combat frame (1/60 s of
		// game time), each when the previous one has been written.
		const double GameTime = GetWorld()->GetTimeSeconds();
		if (GameTime >= FrameCaptureNext && !FScreenshotRequest::IsScreenshotRequested())
		{
			FScreenshotRequest::RequestScreenshot(FPaths::Combine(EvidenceDir, FString::Printf(TEXT("%s_%03d.png"), *FrameCaptureName, FrameCaptureIndex++)), true, false);
			FrameCaptureNext = GameTime + 1.0 / 60.0;
			if (--FrameCaptureLeft == 0)
			{
				UGameplayStatics::SetGlobalTimeDilation(this, 1.0f);
			}
		}
	}
	PlayFirstPersonEvents();
	TickSpells(DeltaSeconds);
	if (Vfx && FPTuning.Chapel.SparkRange > 0.0f && FVector::Dist(FPPlayer->GetActorLocation(), FPTuning.Chapel.SparkAt) < FPTuning.Chapel.SparkRange)
	{
		// Now and then an ember rises off the forge's coals.
		FPSparkLeft -= DeltaSeconds;
		if (FPSparkLeft <= 0.0f)
		{
			Vfx->HearthSpark(FPTuning.Chapel.SparkAt + FVector(FMath::FRandRange(-30.0f, 30.0f), FMath::FRandRange(-80.0f, 80.0f), 0.0f));
			FPSparkLeft = FPTuning.Chapel.SparkGap * FMath::FRandRange(0.3f, 1.7f);
			++FPSparks;
		}
	}
	for (int32 i = 0; i < FPWolves.Num(); ++i)
	{
		AEHWolf* W = FPWolves[i];
		if (W == nullptr)
		{
			continue;
		}
		W->SetAlignment(FPAlignment);
		W->SetSanctuary(bPraying);
		W->SetShadowPlayer(bFPShadow);
		const EEHWolfState WS = W->GetState();
		EEHWolfState& Last = FPWolvesLastState[i];
		if (WS != Last)
		{
			// Placeholder voice: a low rumble as it winds up, the snap of a bite.
			if (WS == EEHWolfState::BiteWindup || WS == EEHWolfState::LungeWindup)
			{
				PlayImpact(TEXT("AuraCharge"), 3, 0.5f, 0.45f);
			}
			else if (WS == EEHWolfState::Lunge)
			{
				PlayImpact(TEXT("WhooshHeavy"), 3, 0.7f, 0.8f);
			}
			AutoLogLine(i == 0 ? FString::Printf(TEXT("fp wolf %s -> %s"), EHWolfStateName(Last), EHWolfStateName(WS))
				: FString::Printf(TEXT("fp wolf %d %s -> %s"), i, EHWolfStateName(Last), EHWolfStateName(WS)));
			CombatTextEvents(i, WS, Last);
			Last = WS;
		}
		if (W->TakeBiteCue())
		{
			PlayImpact(TEXT("Grab"), 1, 0.7f, 1.4f);
		}
	}
	FPWolfLastState = FPWolvesLastState.Num() > 0 ? FPWolvesLastState[0] : EEHWolfState::Calm;
	// The pack judges together: once one wolf has started the fight with an evil aura that would not leave, all do.
	bool bAnyEscalated = false;
	for (const AEHWolf* W : FPWolves)
	{
		bAnyEscalated |= W && !W->IsDead() && W->IsEscalated();
	}
	for (AEHWolf* W : FPWolves)
	{
		if (bAnyEscalated && W && !W->IsDead() && !W->IsEscalated())
		{
			W->Escalate();
			++FPEscalations;
			AutoLogLine(TEXT("fp wolf joins the fight (the pack judges together)"));
		}
	}
	// A Shadow that ignored the wolves' warning to pray.
	if (bFPShadow && FPExorcism < 0.0f)
	{
		for (const AEHWolf* W : FPWolves)
		{
			if (W && !W->IsDead() && W->ShadowOutOfPatience())
			{
				BeginExorcism(TEXT("did not pray"));
				break;
			}
		}
	}
	TickPack(DeltaSeconds);
	CombatTextNearness(GetWorld()->GetTimeSeconds());
	CombatText.Tick(DeltaSeconds);
	// The Qhi line shows while it changes and a moment after; it flashes when a cast is refused.
	const bool bShowQhi = Settings.StaminaMeter == 2 || (Settings.StaminaMeter == 1 && (FPPlayer->QhiFraction() < 0.999f || FPPlayer->SecondsSinceQhiChange() < 1.0f || FPPlayer->SecondsSinceRefused() < 1.0f));
	QhiMeterAlpha = FMath::FInterpConstantTo(QhiMeterAlpha, bShowQhi ? 1.0f : 0.0f, DeltaSeconds, bShowQhi ? 6.0f : 1.5f);
	// The Stamina line fades in while it changes and out a moment after it is full again.
	const bool bShow = Settings.StaminaMeter == 2 || (Settings.StaminaMeter == 1 && (FPPlayer->StaminaFraction() < 0.999f || FPPlayer->SecondsSinceStaminaChange() < 1.0f));
	StaminaMeterAlpha = FMath::FInterpConstantTo(StaminaMeterAlpha, bShow ? 1.0f : 0.0f, DeltaSeconds, bShow ? 6.0f : 1.5f);
}

void AEHGameDirector::PlayFirstPersonEvents()
{
	FPPlayer->TakeEvents(FPEvents);
	for (const FEHFirstPersonEvent& E : FPEvents)
	{
		const bool bWet = E.WaterDepth > 0.5f;
		const float Depth = FMath::Clamp(E.WaterDepth / 35.0f, 0.0f, 1.0f);
		switch (E.Kind)
		{
		case FEHFirstPersonEvent::EKind::Step:
			if (bWet)
			{
				Audio.PlayVaried(TEXT("StepWater"), 3, EEHSoundCat::Effects, 0.18f + 0.22f * E.Strength + 0.25f * Depth);
				if (Vfx)
				{
					Vfx->Ripple(FVector(E.Location.X, E.Location.Y, FPWater.SurfaceOr(E.Location, FPTuning.WaterSurfaceZ)), 0.35f + 0.5f * Depth);
				}
			}
			break;
		case FEHFirstPersonEvent::EKind::Jump:
			if (bWet)
			{
				Audio.PlayVaried(TEXT("StepWater"), 3, EEHSoundCat::Effects, 0.3f + 0.2f * Depth);
			}
			break;
		case FEHFirstPersonEvent::EKind::Land:
			if (bWet)
			{
				Audio.PlayVaried(TEXT("StepWater"), 3, EEHSoundCat::Effects, 0.35f + 0.45f * E.Strength);
				if (Vfx)
				{
					Vfx->Ripple(FVector(E.Location.X, E.Location.Y, FPWater.SurfaceOr(E.Location, FPTuning.WaterSurfaceZ)), 0.6f + 0.6f * E.Strength);
					if (E.Strength > 0.5f)
					{
						Vfx->Splash(FVector(E.Location.X, E.Location.Y, FPWater.SurfaceOr(E.Location, FPTuning.WaterSurfaceZ)), 0.6f * E.Strength);
					}
				}
			}
			AutoLogLine(FString::Printf(TEXT("fp land strength=%.2f water=%.1f"), E.Strength, E.WaterDepth));
			break;
		case FEHFirstPersonEvent::EKind::Swing:
			Audio.PlayVaried(E.Action == EEHFistAction::Straight ? FName(TEXT("WhooshHeavy")) : FName(TEXT("WhooshLight")), 3, EEHSoundCat::Effects,
				0.7f);
			AutoLogLine(FString::Printf(TEXT("fp swing %s"), EHFistActionName(E.Action)));
			// The body goes with the blow: the view leans in and turns a little with the throwing shoulder.
			FPPlayer->AddCameraKick(-0.25f, E.Action == EEHFistAction::Straight ? 2.2f : 1.2f, E.Action == EEHFistAction::Straight ? 0.9f : -0.5f);
			if (bFPShadow && NearestLiveWolf(FPPlayer->GetActorLocation(), 1e7f) && FPPlayer->FeetLocation().Y < FPTuning.Wolf.LeaveLineY)
			{
				// "If it does anything but pray": a Shadow raising a hand in the Chapel is exorcised.
				BeginExorcism(TEXT("struck"));
			}
			for (AEHWolf* W : FPWolves)
			{
				if (W && W->NoticeThreat(FPPlayer->Camera()->GetComponentLocation(), FPPlayer->Camera()->GetForwardVector()))
				{
					AutoLogLine(TEXT("fp wolf disengages (threatened)"));
				}
			}
			break;
		case FEHFirstPersonEvent::EKind::Contact:
			if (Cast<AEHWolf>(E.Target.Get()))
			{
				FEHWolfHit R;
				R.Damage = E.Damage;
				R.Reflected = E.Reflected;
				R.bKilled = E.bKilled;
				R.bHarmed = E.Damage > 0.0f;
				R.WolfAt = E.Target->GetActorLocation();
				PlayImpact(E.Action == EEHFistAction::Straight ? TEXT("HitHeavy") : TEXT("HitLight"), 3, 0.85f, 1.25f);
				if (Vfx && R.bHarmed) { Vfx->Hit(E.Location, 1, E.Action == EEHFistAction::Straight, false, false, false); }
				Rumble(0.5f, 0.4f, 0.1f);
				WolfStruck(R, EHFistActionName(E.Action));
				break;
			}
			// Layered impacts: a crack for the knuckles, a low thud for the weight behind them, pitched by technique and
			// target (body shots duller), never twice the same.
			if (E.bBlocked)
			{
				PlayImpact(TEXT("Block"), 2, 0.85f, E.Action == EEHFistAction::Straight ? 0.9f : 1.05f);
				PlayImpact(TEXT("BodyFall"), 2, 0.2f, 1.3f);
				if (Vfx) { Vfx->Block(E.Location, 1, false); }
				Rumble(0.0f, 0.35f, 0.07f);
			}
			else if (E.Action == EEHFistAction::Straight)
			{
				PlayImpact(TEXT("HitHeavy"), 3, 0.95f, E.bBody ? 0.86f : 1.0f);
				PlayImpact(TEXT("BodySlam"), 2, E.bBody ? 0.45f : 0.3f, E.bBody ? 0.85f : 1.15f);
				if (Vfx) { Vfx->Hit(E.Location, 1, true, false, false, false); }
				Rumble(0.8f, 0.55f, E.bBody ? 0.16f : 0.13f);
			}
			else
			{
				PlayImpact(TEXT("HitLight"), 3, 0.9f, E.bBody ? 0.88f : 1.1f);
				if (E.bBody)
				{
					PlayImpact(TEXT("BodyFall"), 2, 0.22f, 1.2f);
				}
				if (Vfx) { Vfx->Hit(E.Location, 1, false, false, false, false); }
				Rumble(E.bBody ? 0.35f : 0.0f, 0.5f, 0.08f);
			}
			// The impact comes back up the arm: a jolt back in the view; a guard stops the fist dead and throws it back.
			if (E.bBlocked)
			{
				FPPlayer->AddCameraKick(0.7f, -2.4f, 0.0f);
				if (UEHViewArms* VA = FPPlayer->ViewArms()) { VA->StrikeRebound(E.Action == EEHFistAction::Jab ? 0 : 1, 1.0f); }
			}
			else
			{
				FPPlayer->AddCameraKick(E.Action == EEHFistAction::Straight ? 0.55f : 0.3f, E.Action == EEHFistAction::Straight ? -1.6f : -0.9f, 0.0f);
			}
			AutoLogLine(FString::Printf(TEXT("fp contact %s damage=%.1f blocked=%d body=%d"), EHFistActionName(E.Action), E.Damage, E.bBlocked ? 1 : 0, E.bBody ? 1 : 0));
			break;
		case FEHFirstPersonEvent::EKind::Wall:
			if (E.bIce)
			{
				if (E.bShattered)
				{
					PlayImpact(TEXT("IceWallShatter"), 1, 0.95f, 1.0f);
				}
				else
				{
					PlayImpact(TEXT("IceWallHit"), 2, 0.72f, 1.0f);
				}
				if (Vfx) { Vfx->IceBurst(E.Location, E.bShattered ? 2.0f : 0.6f); }
				Rumble(E.bShattered ? 0.6f : 0.1f, 0.35f, E.bShattered ? 0.2f : 0.06f);
			}
			else
			{
				PlayImpact(TEXT("Block"), 2, 0.45f, 0.7f);
				Rumble(0.0f, 0.3f, 0.05f);
			}
			AutoLogLine(FString::Printf(TEXT("fp wall %s ice=%d damage=%.1f shattered=%d"), EHFistActionName(E.Action), E.bIce ? 1 : 0, E.Damage, E.bShattered ? 1 : 0));
			break;
		case FEHFirstPersonEvent::EKind::Guarded:
			if (E.bAbsorbed)
			{
				PlayImpact(TEXT("Grab"), 1, 0.6f, 1.2f);
				AutoLogLine(TEXT("fp absorbed by a wolf"));
				break;
			}
			PlayImpact(TEXT("Block"), 2, 0.9f, 0.95f);
			Rumble(0.45f, 0.3f, 0.1f);
			// The blow lands on the forearms: both fists driven back, the view jolted.
			FPPlayer->AddCameraKick(1.1f, -2.8f, FMath::FRandRange(-0.8f, 0.8f));
			if (UEHViewArms* VA = FPPlayer->ViewArms()) { VA->GuardImpact(FMath::Clamp(E.Damage / 3.0f + 0.6f, 0.6f, 1.3f)); }
			++FPGuardedCount;
			AutoLogLine(FString::Printf(TEXT("fp guarded damage=%.1f"), E.Damage));
			break;
		case FEHFirstPersonEvent::EKind::Hurt:
			PlayImpact(TEXT("HitHeavy"), 3, 0.85f, 0.92f);
			HurtFlash = Settings.bReduceFlash ? 0.35f : 1.0f;
			Rumble(0.9f, 0.6f, 0.25f);
			++FPHurtCount;
			FPHurtTimes.Add(GetWorld()->GetTimeSeconds());
			if (CombatText.Offer(TEXT("player.hurt"), nullptr, EEHLineKind::Player, GetWorld()->GetTimeSeconds()))
			{
				AutoLogLine(FString::Printf(TEXT("fp text player: %s"), *CombatText.LastText));
			}
			AutoLogLine(FString::Printf(TEXT("fp hurt damage=%.1f health=%.1f"), E.Damage, FPPlayer->Health()));
			break;
		case FEHFirstPersonEvent::EKind::CastStart:
			if (E.Action == EEHFistAction::Fireball)
			{
				PlayImpact(TEXT("FlameIgnite"), 1, 0.55f, 1.1f);
			}
			else
			{
				PlayImpact(TEXT("IceWallCharge"), 2, 0.68f, 1.0f);
			}
			AutoLogLine(FString::Printf(TEXT("fp cast_start %s qhi=%.1f"), EHFistActionName(E.Action), FPPlayer->Qhi()));
			for (AEHWolf* W : FPWolves)
			{
				if (W && W->NoticeThreat(FPPlayer->Camera()->GetComponentLocation(), FPPlayer->Camera()->GetForwardVector()))
				{
					AutoLogLine(TEXT("fp wolf disengages (threatened)"));
				}
			}
			break;
		case FEHFirstPersonEvent::EKind::Cast:
		{
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			if (E.Action == EEHFistAction::Fireball)
			{
				if (AEHFireball* Ball = GetWorld()->SpawnActor<AEHFireball>(AEHFireball::StaticClass(), FTransform(E.Direction.Rotation(), E.Location), Params))
				{
					Ball->Launch(FPTuning.Magic, FPPlayer, Vfx, E.Direction);
					FPFireballs.Add(Ball);
				}
				PlayImpact(TEXT("FlameRoar"), 3, 0.7f, 1.15f);
				Rumble(0.25f, 0.35f, 0.12f);
			}
			else if (AEHIceWall* Wall = GetWorld()->SpawnActor<AEHIceWall>(AEHIceWall::StaticClass(), FTransform(E.Direction.Rotation(), E.Location), Params))
			{
				TArray<AActor*> Opponents;
				if (FPDummy)
				{
					Opponents.Add(FPDummy);
				}
				for (AEHWolf* W : FPWolves)
				{
					if (W && !W->IsDead())
					{
						Opponents.Add(W);
					}
				}
				Wall->SetVfx(Vfx);
				Wall->Raise(FPTuning.Magic, FPWater, E.Location, E.Direction, Opponents);
				PackRepathSoon();
				// Anyone standing where it rises is pushed out of the ice to the side they stood on.
				for (AActor* A : Opponents)
				{
					const FVector Local = Wall->GetActorTransform().InverseTransformPosition(A->GetActorLocation());
					const float Clear = FPTuning.Magic.IceWallThickness * 0.5f + A->GetSimpleCollisionRadius() + 2.0f;
					if (FMath::Abs(Local.X) < Clear && FMath::Abs(Local.Y) < FPTuning.Magic.IceWallWidth * 0.5f + A->GetSimpleCollisionRadius())
					{
						// To the side it stood on; one caught dead centre goes away from the caster.
						const float Side = Local.X >= -1.0f ? 1.0f : -1.0f;
						const FVector Push = Wall->GetActorForwardVector() * (Side * Clear - Local.X);
						if (AEHTrainingDummy* D = Cast<AEHTrainingDummy>(A)) { D->Displace(Push, Wall); }
						else if (AEHWolf* W = Cast<AEHWolf>(A)) { W->Displace(Push, Wall); }
					}
				}
				FPWalls.Add(Wall);
				++FPWallsRaised;
				if (Vfx)
				{
					// Frost bursting up along its foot, and a cold mist rolling off it.
					const FVector Across = FVector::CrossProduct(FVector::UpVector, E.Direction.GetSafeNormal2D());
					for (int32 k = -2; k <= 2; ++k)
					{
						const FVector P = E.Location + Across * (k * FPTuning.Magic.IceWallWidth * 0.2f);
						Vfx->IceBurst(P + FVector(0, 0, 25.0f), 0.9f);
						Vfx->Steam(P + FVector(0, 0, 10.0f), 0.9f);
					}
				}
				PlayImpact(TEXT("IceWallRaise"), 3, 0.92f, 1.0f);
				Rumble(0.6f, 0.2f, 0.25f);
				AutoLogLine(FString::Printf(TEXT("fp ice_wall at=(%.0f,%.0f,%.0f) froze_water=%d frozen=%d"), E.Location.X, E.Location.Y, E.Location.Z, Wall->FroseWater() ? 1 : 0, Wall->Frozen()));
			}
			AutoLogLine(FString::Printf(TEXT("fp cast %s qhi=%.1f"), EHFistActionName(E.Action), FPPlayer->Qhi()));
			break;
		}
		case FEHFirstPersonEvent::EKind::Refused:
			Audio.Play(TEXT("UiDenied"), EEHSoundCat::Ui, 0.6f);
			if (E.bNoQhi)
			{
				++FPRefusedNoQhi;
			}
			else
			{
				++FPRefusedNoRoom;
			}
			AutoLogLine(FString::Printf(TEXT("fp refused %s %s qhi=%.1f"), EHFistActionName(E.Action), E.bNoQhi ? TEXT("no_qhi") : TEXT("no_room"), FPPlayer->Qhi()));
			break;
		case FEHFirstPersonEvent::EKind::Fizzle:
			Audio.Play(TEXT("UiDenied"), EEHSoundCat::Ui, 0.6f);
			++FPFizzles;
			AutoLogLine(FString::Printf(TEXT("fp fizzle %s qhi=%.1f"), EHFistActionName(E.Action), FPPlayer->Qhi()));
			break;
		case FEHFirstPersonEvent::EKind::Died:
			++FPDeaths;
			AutoLogLine(TEXT("fp died: instant reset"));
			break;
		case FEHFirstPersonEvent::EKind::Reset:
			break;
		}
	}
	const bool bDied = FPEvents.ContainsByPredicate([](const FEHFirstPersonEvent& E) { return E.Kind == FEHFirstPersonEvent::EKind::Died; });
	FPEvents.Reset();
	if (bDied)
	{
		// The prototype's death: straight back to the start, everything restored.
		ResetFirstPerson(TEXT("death"));
	}
}

void AEHGameDirector::TickSpells(float DeltaSeconds)
{
	// Fireballs: play each one's end once, then let it go.
	for (int32 i = FPFireballs.Num() - 1; i >= 0; --i)
	{
		AEHFireball* Ball = FPFireballs[i];
		if (Ball == nullptr)
		{
			FPFireballs.RemoveAt(i);
			continue;
		}
		if (Ball->Result() == AEHFireball::EResult::Flying)
		{
			continue;
		}
		const FVector At = Ball->HitAt;
		switch (Ball->Result())
		{
		case AEHFireball::EResult::Target:
			if (AEHWolf* Wolf = Cast<AEHWolf>(Ball->HitTarget.Get()))
			{
				const FEHWolfHit R = Wolf->ReceivePlayerHit(FPTuning.Magic.FireballDamage, FPPlayer ? FPPlayer->GetActorLocation() : At, At, true);
				++FPFireballHits;
				PlayImpact(TEXT("FlameHit"), 1, 0.95f, 1.0f);
				if (R.Reflected > 0.0f && FPPlayer)
				{
					FPPlayer->ReceiveStrike(R.Reflected, At, true);
				}
				WolfStruck(R, TEXT("Fireball"));
			}
			else if (AEHTrainingDummy* D = Cast<AEHTrainingDummy>(Ball->HitTarget.Get()))
			{
				FEHStrikeDef Def;
				Def.Damage = FPTuning.Magic.FireballDamage;
				Def.Hitstop = FMath::RoundToInt(FPTuning.Magic.FireballHitstop);
				const FEHDummyHit R = D->ReceiveHit(EEHFistAction::Fireball, Def, FPPlayer ? FPPlayer->Camera()->GetComponentLocation() : At - Ball->GetActorForwardVector() * 300.0f, At, 0.0f);
				++FPFireballHits;
				PlayImpact(TEXT("FlameHit"), 1, 0.95f, 1.0f);
				PlayImpact(TEXT("HitHeavy"), 3, 0.5f, 0.8f);
				Rumble(0.3f, 0.5f, 0.12f);
				AutoLogLine(FString::Printf(TEXT("fp fireball hit damage=%.1f blocked=%d"), R.Damage, R.bBlocked ? 1 : 0));
			}
			break;
		case AEHFireball::EResult::Wall:
			if (AEHIceWall* W = Ball->HitWall.Get())
			{
				W->Melt();
				PlayImpact(TEXT("FlameHit"), 1, 0.7f, 0.8f);
				PlayImpact(TEXT("IceWallMelt"), 1, 0.85f, 1.05f);
				if (Vfx)
				{
					// Steam off the melting ice.
					Vfx->Steam(At, 1.4f);
					Vfx->Steam(W->GetActorLocation(), 2.0f);
				}
				AutoLogLine(TEXT("fp fireball melted ice_wall"));
			}
			break;
		case AEHFireball::EResult::World:
			PlayImpact(TEXT("FlameHit"), 1, 0.6f, 1.15f);
			AutoLogLine(TEXT("fp fireball hit world"));
			break;
		default:
			AutoLogLine(TEXT("fp fireball expired"));
			break;
		}
		if (Vfx && Ball->Result() != AEHFireball::EResult::Expired)
		{
			Vfx->FireBurst(At);
		}
		Ball->Destroy();
		FPFireballs.RemoveAt(i);
	}
	// Ice Walls: count how each ended, and clear the ones that are gone.
	for (int32 i = FPWalls.Num() - 1; i >= 0; --i)
	{
		AEHIceWall* W = FPWalls[i];
		if (W == nullptr)
		{
			FPWalls.RemoveAt(i);
			continue;
		}
		if (W->TakeMeltStarted())
		{
			// Turning to water: steam hiss, settling ice creaks and water droplets.
			PlayImpact(TEXT("IceWallMelt"), 1, 0.72f, 0.96f);
			AutoLogLine(TEXT("fp ice_wall melting into water"));
		}
		if (W->TakeEnded())
		{
			PackRepathSoon();
			// Counted the moment it stops being a wall (its water lingers a while after).
			switch (W->EndReason())
			{
			case AEHIceWall::EEnd::Melted: ++FPWallsMelted; break;
			case AEHIceWall::EEnd::Shattered: ++FPWallsShattered; break;
			default: ++FPWallsExpired; break;
			}
			AutoLogLine(FString::Printf(TEXT("fp ice_wall ends (%s)"), W->EndReason() == AEHIceWall::EEnd::Melted ? TEXT("melted") : (W->EndReason() == AEHIceWall::EEnd::Shattered ? TEXT("shattered") : TEXT("expired"))));
		}
		if (W->IsDone())
		{
			W->Destroy();
			FPWalls.RemoveAt(i);
		}
	}
}

void AEHGameDirector::SpawnWolf()
{
	SpawnPack(FPTuning.Pack.Count);
}

void AEHGameDirector::WolfStruck(const FEHWolfHit& R, const TCHAR* What)
{
	// Harming a guardian pushes the player toward evil; killing one brings them down to a deeper evil. A Hero of
	// Humanity cannot harm one: the blow came back to them.
	const int32 Before = FPAlignment;
	if (R.Damage > 0.0f && CombatText.Offer(R.bKilled ? TEXT("player.kill") : TEXT("player.hit"), nullptr, EEHLineKind::Player, GetWorld()->GetTimeSeconds()))
	{
		AutoLogLine(FString::Printf(TEXT("fp text player: %s"), *CombatText.LastText));
	}
	if (R.Reflected > 0.0f)
	{
		++FPReflected;
	}
	if (R.bHarmed)
	{
		++FPWolfHarms;
		FPAlignment = EHAlign::AfterHarm(FPAlignment);
	}
	if (R.bKilled)
	{
		++FPWolfKills;
		FPAlignment = EHAlign::AfterKill(FPAlignment);
		PlayImpact(TEXT("BodyFall"), 2, 0.8f, 1.15f);
	}
	if (R.bHarmed)
	{
		// The others nearby respond to the violence: they are provoked too.
		for (AEHWolf* W : FPWolves)
		{
			if (W && !W->IsDead() && !W->IsProvoked() && FVector::Dist(W->GetActorLocation(), R.WolfAt) <= FPTuning.Wolf.AlertRange)
			{
				W->Alert();
				++FPAlerts;
				AutoLogLine(TEXT("fp wolf alerted by harm to another"));
			}
		}
	}
	for (AEHWolf* W : FPWolves)
	{
		if (W)
		{
			W->SetAlignment(FPAlignment);
		}
	}
	AutoLogLine(FString::Printf(TEXT("fp wolf struck by %s damage=%.1f reflected=%.1f killed=%d alignment %s -> %s"), What, R.Damage, R.Reflected, R.bKilled ? 1 : 0,
		EHAlign::Name(Before), EHAlign::Name(FPAlignment)));
}

void AEHGameDirector::BeginExorcism(const TCHAR* Why)
{
	if (FPExorcism >= 0.0f)
	{
		return;
	}
	FPExorcism = 0.0f;
	++FPExorcisms;
	EndPrayer(TEXT("exorcised"));
	CloseSpellSelect(false);
	PlayImpact(TEXT("AuraCharge"), 3, 0.9f, 0.6f);
	AutoLogLine(FString::Printf(TEXT("fp exorcism begins (the Shadow %s)"), Why));
}

void AEHGameDirector::TalkToWolf(int32 Index)
{
	// Only the trusted get a real conversation; a wary wolf tells the player to pray, relax, or leave it alone. The
	// lines are the creator's to write (Content/Data/firstperson.json, combatText.lines: "wolf.talk.friendly",
	// "wolf.talk.wary"); the placeholders are marked.
	const bool bGood = EHAlign::Band(FPAlignment) == EEHAlignBand::Good;
	const TArray<FEHCombatLine>* Pool = CombatText.Tuning.Lines.Find(bGood ? TEXT("wolf.talk.friendly") : TEXT("wolf.talk.wary"));
	if (Pool == nullptr || Pool->Num() == 0)
	{
		return;
	}
	const FEHCombatLine& L = (*Pool)[FPWolfTalkIndex++ % Pool->Num()];
	FPMessage = FString::Printf(TEXT("Chapel wolf:  %s%s"), L.bPlaceholder ? TEXT("PLACEHOLDER  ") : TEXT(""), *L.Text);
	FPMessageLeft = FPTuning.Chapel.MessageSeconds;
	FPMessageFrom = FPPlayer->FeetLocation();
	++FPWolfTalks;
	AutoLogLine(FString::Printf(TEXT("fp talk wolf %d (%s): %s"), Index, bGood ? TEXT("friendly") : TEXT("wary"), *L.Text));
}

FVector AEHGameDirector::LockOnPoint(const AActor* Target) const
{
	if (const AEHWolf* W = Cast<AEHWolf>(Target))
	{
		return W->LockOnPoint();
	}
	if (const AEHTrainingDummy* D = Cast<AEHTrainingDummy>(Target))
	{
		return D->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f);
	}
	return Target ? Target->GetActorLocation() : FVector::ZeroVector;
}

bool AEHGameDirector::HasLockLineOfSight(const AActor* Target) const
{
	if (!FPPlayer || !Target || !GetWorld())
	{
		return false;
	}
	const FVector Eye = FPPlayer->Camera()->GetComponentLocation();
	const FVector Pt = LockOnPoint(Target);
	FHitResult Hit;
	FCollisionQueryParams Params(TEXT("EHLockOnLOS"), false, FPPlayer);
	Params.AddIgnoredActor(Target);
	return !GetWorld()->LineTraceSingleByChannel(Hit, Eye, Pt, ECC_Visibility, Params);
}

int32 AEHGameDirector::LockTargetIndex() const
{
	const AActor* T = FPLockTarget.Get();
	if (T == nullptr)
	{
		return -1;
	}
	if (T == FPDummy)
	{
		return 100;
	}
	for (int32 i = 0; i < FPWolves.Num(); ++i)
	{
		if (FPWolves[i] == T)
		{
			return i;
		}
	}
	return -1;
}

AActor* AEHGameDirector::FindLockTarget(int32 SwitchDir) const
{
	if (!FPPlayer)
	{
		return nullptr;
	}
	const FEHLockOnTuning& T = FPTuning.LockOn;
	const FVector Eye = FPPlayer->Camera()->GetComponentLocation();
	const FVector Fwd = FPPlayer->Camera()->GetForwardVector();
	const FVector Right = FPPlayer->Camera()->GetRightVector();
	const float MinCos = FMath::Cos(FMath::DegreesToRadians(SwitchDir == 0 ? T.ConeDegrees : 80.0f));

	TArray<AActor*> Candidates;
	for (AEHWolf* W : FPWolves)
	{
		if (W && !W->IsDead())
		{
			Candidates.Add(W);
		}
	}
	if (FPDummy)
	{
		Candidates.Add(FPDummy);
	}

	const AActor* Current = FPLockTarget.Get();
	const FVector CurDir = Current ? (LockOnPoint(Current) - Eye).GetSafeNormal() : Fwd;
	const float CurSide = FVector::DotProduct(CurDir, Right);

	AActor* Best = nullptr;
	float BestScore = 1e9f;
	for (AActor* A : Candidates)
	{
		if (SwitchDir != 0 && A == Current)
		{
			continue;
		}
		const FVector Delta = LockOnPoint(A) - Eye;
		const float Dist = Delta.Size();
		if (Dist < 30.0f || Dist > T.Range)
		{
			continue;
		}
		const FVector Dir = Delta / Dist;
		const float Dot = FVector::DotProduct(Fwd, Dir);
		if (Dot < MinCos)
		{
			continue;
		}
		if (!HasLockLineOfSight(A))
		{
			continue;
		}
		if (SwitchDir != 0)
		{
			const float SideDelta = FVector::DotProduct(Dir, Right) - CurSide;
			if (SideDelta * static_cast<float>(SwitchDir) <= 0.04f)
			{
				continue;
			}
			// Prefer the nearest target in the flicked direction, slightly favouring closer ones.
			const float Score = FMath::Abs(SideDelta) * 1000.0f + Dist * 0.15f;
			if (Score < BestScore)
			{
				BestScore = Score;
				Best = A;
			}
		}
		else
		{
			// Acquire: strongly prefer targets near the centre of the view, with distance as a light tie-breaker.
			const float Angle = FMath::Acos(FMath::Clamp(Dot, -1.0f, 1.0f));
			const float Score = Angle * 1000.0f + Dist * 0.2f;
			if (Score < BestScore)
			{
				BestScore = Score;
				Best = A;
			}
		}
	}
	return Best;
}

void AEHGameDirector::ClearLockOn(const TCHAR* Why)
{
	if (FPLockTarget.IsValid())
	{
		AutoLogLine(FString::Printf(TEXT("fp lock-on cleared (%s)"), Why));
	}
	FPLockTarget.Reset();
	FPLockLostLos = 0.0f;
	FPLockMouseAccum = 0.0f;
	bFPLockStickHeld = false;
}

void AEHGameDirector::UpdateLockOn(FEHFirstPersonInput& In, float DeltaSeconds)
{
	if (!FPPlayer)
	{
		return;
	}
	const FEHLockOnTuning& T = FPTuning.LockOn;
	FPLockSwitchCooldown = FMath::Max(0.0f, FPLockSwitchCooldown - DeltaSeconds);
	if (bPraying || FPExorcism >= 0.0f)
	{
		if (FPLockTarget.IsValid())
		{
			ClearLockOn(TEXT("prayer"));
		}
		return;
	}
	if (bFPLockPressed)
	{
		if (FPLockTarget.IsValid())
		{
			ClearLockOn(TEXT("toggle"));
			PlayImpact(TEXT("UiMove"), 1, 0.4f, 0.9f);
			return;
		}
		if (AActor* Found = FindLockTarget(0))
		{
			FPLockTarget = Found;
			FPLockLostLos = 0.0f;
			FPLockMouseAccum = 0.0f;
			FPLockSwitchCooldown = 0.15f;
			PlayImpact(TEXT("UiMove"), 1, 0.55f, 1.35f);
			AutoLogLine(FString::Printf(TEXT("fp lock-on acquired target=%d"), LockTargetIndex()));
		}
		else if (AController* C = FPPlayer->GetController())
		{
			// Souls fallback: with no target in front, level the view back toward the horizon.
			FRotator R = C->GetControlRotation();
			R.Pitch = 0.0f;
			R.Roll = 0.0f;
			C->SetControlRotation(R);
			AutoLogLine(TEXT("fp lock-on recenter (no target)"));
		}
	}
	AActor* Target = FPLockTarget.Get();
	if (Target == nullptr)
	{
		return;
	}
	if (const AEHWolf* W = Cast<AEHWolf>(Target); W && W->IsDead())
	{
		ClearLockOn(TEXT("target dead"));
		return;
	}
	const FVector Eye = FPPlayer->Camera()->GetComponentLocation();
	const FVector Pt = LockOnPoint(Target);
	if (FVector::Dist(Eye, Pt) > T.BreakRange)
	{
		ClearLockOn(TEXT("out of range"));
		return;
	}
	if (HasLockLineOfSight(Target))
	{
		FPLockLostLos = 0.0f;
	}
	else
	{
		FPLockLostLos += DeltaSeconds;
		if (FPLockLostLos >= T.LosGrace)
		{
			ClearLockOn(TEXT("lost sight"));
			return;
		}
	}
	if (!bSpellSelect)
	{
		int32 SwitchDir = 0;
		if (FMath::Abs(FPLockRawStickX) >= T.SwitchStick && !bFPLockStickHeld && FPLockSwitchCooldown <= 0.0f)
		{
			bFPLockStickHeld = true;
			SwitchDir = FPLockRawStickX > 0.0f ? 1 : -1;
		}
		else if (FMath::Abs(FPLockRawStickX) < 0.35f)
		{
			bFPLockStickHeld = false;
		}
		FPLockMouseAccum = FMath::FInterpTo(FPLockMouseAccum, 0.0f, DeltaSeconds, 5.0f) + FPLockRawMouseX;
		if (SwitchDir == 0 && FMath::Abs(FPLockMouseAccum) >= T.SwitchMouse && FPLockSwitchCooldown <= 0.0f)
		{
			SwitchDir = FPLockMouseAccum > 0.0f ? 1 : -1;
			FPLockMouseAccum = 0.0f;
		}
		if (SwitchDir != 0)
		{
			if (AActor* Next = FindLockTarget(SwitchDir))
			{
				FPLockTarget = Next;
				Target = Next;
				FPLockLostLos = 0.0f;
				FPLockSwitchCooldown = T.SwitchCooldown;
				++FPLockSwitches;
				PlayImpact(TEXT("UiMove"), 1, 0.45f, 1.5f);
				AutoLogLine(FString::Printf(TEXT("fp lock-on switch dir=%d target=%d"), SwitchDir, LockTargetIndex()));
			}
		}
		// Track the locked target smoothly; manual look is suppressed so strafing orbits cleanly around it.
		In.Look = FVector2D::ZeroVector;
		if (AController* C = FPPlayer->GetController())
		{
			FRotator Want = (LockOnPoint(Target) - Eye).Rotation();
			Want.Pitch = FMath::Clamp(FRotator::NormalizeAxis(Want.Pitch), -FPTuning.PitchLimit, FPTuning.PitchLimit);
			Want.Roll = 0.0f;
			FRotator Next = FMath::RInterpTo(C->GetControlRotation(), Want, DeltaSeconds, T.TrackSpeed);
			Next.Pitch = FMath::Clamp(FRotator::NormalizeAxis(Next.Pitch), -FPTuning.PitchLimit, FPTuning.PitchLimit);
			Next.Roll = 0.0f;
			C->SetControlRotation(Next);
		}
	}
}

void AEHGameDirector::PaintLockOn(FEHPainter& P)
{
	const AActor* Target = FPLockTarget.Get();
	if (!Target || !FPPlayer || bPaused || bPraying || FPExorcism >= 0.0f)
	{
		return;
	}
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	FVector2D S;
	if (!PC || !PC->ProjectWorldLocationToScreen(LockOnPoint(Target), S, true))
	{
		return;
	}
	const float AppScale = FMath::Max(0.01f, FSlateApplication::Get().GetApplicationScale());
	const FVector2f At = P.ToVirtual(FVector2f(S.X, S.Y) / AppScale);
	// Souls-style reticle: crisp white-gold core dot with a subtle dark halo and four fine ticks.
	const FLinearColor Halo(0.04f, 0.04f, 0.05f, 0.62f);
	const FLinearColor Core(0.98f, 0.95f, 0.86f, 0.95f);
	const FLinearColor Tick(0.95f, 0.91f, 0.78f, 0.72f);
	P.Round(At - FVector2f(8.0f, 8.0f), FVector2f(16.0f, 16.0f), Halo, 8.0f);
	P.Round(At - FVector2f(4.5f, 4.5f), FVector2f(9.0f, 9.0f), Core, 4.5f);
	P.Rect(At + FVector2f(-18.0f, -1.0f), FVector2f(7.0f, 2.0f), Tick);
	P.Rect(At + FVector2f(11.0f, -1.0f), FVector2f(7.0f, 2.0f), Tick);
	P.Rect(At + FVector2f(-1.0f, -18.0f), FVector2f(2.0f, 7.0f), Tick);
	P.Rect(At + FVector2f(-1.0f, 11.0f), FVector2f(2.0f, 7.0f), Tick);
}

void AEHGameDirector::OpenSpellSelect()
{
	// The world slows to a crawl while the player chooses (it does not stop: choosing still has a cost).
	bSpellSelect = true;
	SpellPointer = FVector2D::ZeroVector;
	SpellListScroll = 0.0f;
	bSpellStickHeld = false;
	SpellHighlight = Settings.SpellSelector == 1 ? 0 : -1;
	UGameplayStatics::SetGlobalTimeDilation(this, 0.25f);
	Audio.Play(TEXT("UiOpen"), EEHSoundCat::Ui, 0.5f);
	AutoLogLine(FString::Printf(TEXT("fp spell_select open (%s)"), Settings.SpellSelector == 1 ? TEXT("list") : TEXT("wheel")));
}

EEHFistAction AEHGameDirector::CloseSpellSelect(bool bCast)
{
	if (!bSpellSelect)
	{
		return EEHFistAction::None;
	}
	bSpellSelect = false;
	UGameplayStatics::SetGlobalTimeDilation(this, 1.0f);
	const EEHFistAction Chosen = bCast && SpellHighlight >= 0 && SpellHighlight < SpellCount ? Spells[SpellHighlight].Action : EEHFistAction::None;
	if (Chosen != EEHFistAction::None)
	{
		++SpellSelectCasts;
	}
	else
	{
		Audio.Play(TEXT("UiClose"), EEHSoundCat::Ui, 0.4f);
	}
	AutoLogLine(FString::Printf(TEXT("fp spell_select close -> %s"), EHFistActionName(Chosen)));
	return Chosen;
}

void AEHGameDirector::PaintSpellSelect(FEHPainter& P)
{
	if (SpellSelectAlpha <= 0.01f || FPPlayer == nullptr)
	{
		return;
	}
	const float A = SpellSelectAlpha;
	const FVector2f C(960.0f, 540.0f);
	// The world dims behind the choice (it is still moving, slowly).
	P.Fill(FLinearColor(0.0f, 0.0f, 0.02f, 0.4f * A));
	const EEHDeviceKind Kind = PromptKind(FPDevice);
	const EEHBindingSet Set = FPDevice >= EHDeviceGamepadBase ? EEHBindingSet::FPController : EEHBindingSet::FPKeyboard;
	auto CostOf = [this](EEHFistAction S) { return S == EEHFistAction::Fireball ? FPTuning.Magic.FireballCost : FPTuning.Magic.IceWallCost; };
	// One entry: the spell's name in its colour, its cost, and its button if it has one.
	auto Entry = [&](int32 I, FVector2f At, float AlignX, bool bLit) {
		const FEHSpellEntry& S = Spells[I];
		const bool bAfford = FPPlayer->Qhi() + 0.001f >= CostOf(S.Action);
		const float Dim = bAfford ? 1.0f : 0.45f;
		const FLinearColor Name = bLit ? FLinearColor(S.Color.R, S.Color.G, S.Color.B, A * Dim) : EHStyle::Alpha(EHStyle::TextPrimary, 0.75f * A * Dim);
		P.Text(S.Name, At, Fonts.Sized(Fonts.Display, bLit ? 34.0f : 30.0f), Name, AlignX, 0.5f);
		const FString Cost = bAfford ? FString::Printf(TEXT("%.0f Qhi"), CostOf(S.Action)) : FString::Printf(TEXT("%.0f Qhi - not enough"), CostOf(S.Action));
		P.Text(Cost, At + FVector2f(0.0f, 30.0f), Fonts.Sized(Fonts.Body, 20.0f), EHStyle::Alpha(bAfford ? EHStyle::TextSecondary : EHStyle::Warning, 0.9f * A), AlignX, 0.5f);
		const FKey Key = Settings.Bindings.Get(Set, S.Binding, 0);
		if (Key.IsValid())
		{
			const float W = PaintKeyGlyph(P, FVector2f::ZeroVector, Kind, Key, 26.0f, true);
			PaintKeyGlyph(P, At + FVector2f(-W * AlignX, 50.0f), Kind, Key, 26.0f);
		}
	};
	if (Settings.SpellSelector == 0)
	{
		// The wheel: a dark ring, a lit sector toward the highlighted spell, a pointer from the centre.
		const float R = 210.0f;
		TArray<FVector2f> Ring;
		for (int32 k = 0; k <= 64; ++k)
		{
			const float T = k / 64.0f * 2.0f * PI;
			Ring.Add(C + FVector2f(FMath::Cos(T), -FMath::Sin(T)) * R);
		}
		P.Line(Ring, EHStyle::Alpha(EHStyle::Abyss, 0.55f * A), 120.0f);
		P.Line(Ring, EHStyle::Alpha(EHStyle::Silver, 0.25f * A), 2.0f);
		for (int32 I = 0; I < SpellCount; ++I)
		{
			const float Ang = FMath::DegreesToRadians(WheelAngle(I));
			const bool bLit = I == SpellHighlight;
			if (bLit)
			{
				TArray<FVector2f> Arc;
				const float Half = FMath::DegreesToRadians(180.0f / SpellCount) * 0.9f;
				for (int32 k = 0; k <= 24; ++k)
				{
					const float T = Ang - Half + 2.0f * Half * k / 24.0f;
					Arc.Add(C + FVector2f(FMath::Cos(T), -FMath::Sin(T)) * R);
				}
				P.Line(Arc, FLinearColor(Spells[I].Color.R, Spells[I].Color.G, Spells[I].Color.B, 0.35f * A), 120.0f);
				P.Line(Arc, FLinearColor(Spells[I].Color.R, Spells[I].Color.G, Spells[I].Color.B, 0.9f * A), 3.0f);
			}
			const FVector2f Dir(FMath::Cos(Ang), -FMath::Sin(Ang));
			const FVector2f At = C + Dir * (R + 110.0f);
			Entry(I, At - FVector2f(0.0f, 28.0f), Dir.X < -0.3f ? 1.0f : (Dir.X > 0.3f ? 0.0f : 0.5f), bLit);
		}
		// The pointer, and the centre (letting go there cancels).
		if (SpellPointer.Size() > 0.05f)
		{
			P.Line({C, C + FVector2f(SpellPointer.X, -SpellPointer.Y) * (R - 70.0f)}, EHStyle::Alpha(EHStyle::TextPrimary, 0.6f * A), 3.0f);
		}
		P.Text(FString::Printf(TEXT("Qhi %.0f"), FPPlayer->Qhi()), C, Fonts.Sized(Fonts.BodyMedium, 26.0f), EHStyle::Alpha(EHStyle::TextPrimary, 0.9f * A), 0.5f, 0.5f);
		P.Text(SpellHighlight < 0 ? TEXT("Point to a spell, let go to cast") : TEXT("Let go to cast"), C + FVector2f(0.0f, 34.0f), Fonts.Sized(Fonts.Body, 18.0f),
			EHStyle::Alpha(EHStyle::TextSecondary, 0.8f * A), 0.5f, 0.5f);
	}
	else
	{
		// The list: one row per spell beside the centre of the view, the highlighted one lit.
		const float RowH = 118.0f;
		const FVector2f Top(C.X + 160.0f, C.Y - RowH * SpellCount * 0.5f);
		P.Round(Top - FVector2f(24.0f, 20.0f), FVector2f(420.0f, RowH * SpellCount + 70.0f), EHStyle::Alpha(EHStyle::Abyss, 0.6f * A), 10.0f);
		for (int32 I = 0; I < SpellCount; ++I)
		{
			const FVector2f Row = Top + FVector2f(0.0f, RowH * I);
			const bool bLit = I == SpellHighlight;
			if (bLit)
			{
				P.Round(Row - FVector2f(12.0f, 8.0f), FVector2f(396.0f, RowH - 8.0f), FLinearColor(Spells[I].Color.R, Spells[I].Color.G, Spells[I].Color.B, 0.22f * A), 8.0f);
			}
			Entry(I, Row + FVector2f(8.0f, 22.0f), 0.0f, bLit);
		}
		P.Text(FString::Printf(TEXT("Qhi %.0f  ·  let go to cast"), FPPlayer->Qhi()), Top + FVector2f(8.0f, RowH * SpellCount + 18.0f), Fonts.Sized(Fonts.Body, 18.0f),
			EHStyle::Alpha(EHStyle::TextSecondary, 0.8f * A), 0.0f, 0.5f);
	}
}

void AEHGameDirector::ClearSpells()
{
	for (AEHFireball* B : FPFireballs)
	{
		if (B)
		{
			B->Destroy();
		}
	}
	for (AEHIceWall* W : FPWalls)
	{
		if (W)
		{
			W->Destroy();
		}
	}
	FPFireballs.Reset();
	FPWalls.Reset();
}

void AEHGameDirector::BuildDeveloperPanel()
{
	// Development builds only (F10): the seven stats live, the resources, and quick resets. Changes last until the
	// game closes; the death reset keeps them so a case can be repeated.
	bDevPanel = true;
	Menu.Reset();
	MenuIndex = 0;
	MenuOwner = EHDeviceNone;
	MenuTitle = TEXT("Developer");
	Menu.Add(FPHeader(TEXT("Alignment")));
	{
		// The nine tiers, from Hero of Humanity to Forsaken; the wolves react at once.
		FEHMenuItem I;
		I.Label = TEXT("Alignment");
		I.Value = [this] { return FString::Printf(TEXT("%s (%s)"), EHAlign::Name(FPAlignment), EHAlign::BandName(EHAlign::Band(FPAlignment))); };
		I.Change = [this](int32 D) { FPAlignment = FMath::Clamp(FPAlignment + D, 0, EHAlign::Count - 1); };
		I.Hint = TEXT("Left: toward Hero of Humanity. Right: toward Forsaken. It survives the death reset.");
		Menu.Add(I);
	}
	{
		FEHMenuItem I;
		I.Label = TEXT("Wolf");
		I.Value = [this] { return FPWolf ? FString::Printf(TEXT("%s · %.0f HP%s"), EHWolfStateName(FPWolf->GetState()), FPWolf->HealthValue(), FPWolf->IsProvoked() ? TEXT(" · provoked") : TEXT("")) : FString(TEXT("-")); };
		I.Hint = TEXT("Good: friendly and protective. Neutral: keeps its distance. Evil, or harmed: hostile.");
		Menu.Add(I);
	}
	Menu.Add(FPButton(TEXT("Reset the wolves"), [this] { ResetWolves(); }, TEXT("Calm, unhurt, at their rest.")));
	{
		FEHMenuItem I;
		I.Label = TEXT("Shadow");
		I.Value = [this] { return FString(bFPShadow ? TEXT("Yes") : TEXT("No")); };
		I.Change = [this](int32) { bFPShadow = !bFPShadow; FPShadowPrayHours = 0.0; };
		I.Hint = TEXT("Play as a Shadow (until death and Qhi Stones exist): no spells; the wolves say pray, or be exorcised.");
		Menu.Add(I);
	}
	{
		// The pack (milestone 6): one to four wolves, spawned at their rests.
		FEHMenuItem I;
		I.Label = TEXT("Wolves");
		I.Value = [this] { return FString::Printf(TEXT("%d"), FPWolves.Num()); };
		I.Change = [this](int32 D) { SpawnPack(FPWolves.Num() + D); };
		I.Hint = TEXT("One to four. Evil (or harmed) wolves fight as a pack, taking turns; an overwhelmed player gets a one-on-one.");
		Menu.Add(I);
	}
	Menu.Add(FPHeader(TEXT("Time")));
	{
		// Destiny's Ark's hour, six at a time: the windows follow it.
		FEHMenuItem I;
		I.Label = TEXT("Hour");
		I.Value = [this] {
			const double H = FMath::Fmod(FPClockHours, static_cast<double>(FPTuning.Clock.DayHours));
			return FString::Printf(TEXT("day %.0f · hour %.0f of %.0f"), FMath::FloorToDouble(FPClockHours / FPTuning.Clock.DayHours) + 1.0, FMath::FloorToDouble(H), FPTuning.Clock.DayHours);
		};
		I.Change = [this](int32 D) {
			FPClockHours = FMath::Max(0.0, FPClockHours + 6.0 * D);
			ApplyWorldClock(true);
		};
		I.Hint = TEXT("Left and right move six hours. One real minute is one hour; praying runs faster; pausing stops it.");
		Menu.Add(I);
	}
	Menu.Add(FPHeader(TEXT("Stats")));
	auto StatItem = [this](const TCHAR* Label, int32 Which, const TCHAR* Hint) {
		FEHMenuItem I;
		I.Label = Label;
		I.Hint = Hint;
		I.Value = [this, Which] {
			const FEHPlayerStats& S = FPPlayer->GetStats();
			const float V[] = {S.Health, S.Qhi, S.Stamina, (float)S.Intelligence, (float)S.Faith, (float)S.Dexterity, (float)S.MartialProwess};
			return FString::Printf(TEXT("%.0f"), V[Which]);
		};
		I.Change = [this, Which](int32 D) {
			FEHPlayerStats S = FPPlayer->GetStats();
			switch (Which)
			{
			case 0: S.Health = FMath::Clamp(S.Health + 10.0f * D, 10.0f, 1000.0f); break;
			case 1: S.Qhi = FMath::Clamp(S.Qhi + 10.0f * D, 10.0f, 1000.0f); break;
			case 2: S.Stamina = FMath::Clamp(S.Stamina + 10.0f * D, 10.0f, 1000.0f); break;
			case 3: S.Intelligence = FMath::Clamp(S.Intelligence + D, 0, 99); break;
			case 4: S.Faith = FMath::Clamp(S.Faith + D, 0, 99); break;
			case 5: S.Dexterity = FMath::Clamp(S.Dexterity + D, 0, 99); break;
			default: S.MartialProwess = FMath::Clamp(S.MartialProwess + D, 0, 99); break;
			}
			FPPlayer->SetStats(S);
		};
		Menu.Add(I);
	};
	StatItem(TEXT("Health"), 0, TEXT("Damage you can take before the reset."));
	StatItem(TEXT("Qhi"), 1, TEXT("The pool spells draw from."));
	StatItem(TEXT("Stamina"), 2, TEXT("Spent by sprinting."));
	StatItem(TEXT("Intelligence"), 3, TEXT("Each point above 10 speeds Qhi regeneration by 5%."));
	StatItem(TEXT("Faith"), 4, TEXT("Each point above 10 speeds Qhi regeneration by 5%."));
	StatItem(TEXT("Dexterity"), 5, TEXT("Each point above 10 speeds Stamina recovery by 5%."));
	StatItem(TEXT("Martial Prowess"), 6, TEXT("Each point above 10 adds 5% to strike damage."));
	Menu.Add(FPHeader(TEXT("Now")));
	{
		FEHMenuItem I;
		I.Label = TEXT("Health · Qhi · Stamina");
		I.Value = [this] { return FString::Printf(TEXT("%.0f · %.0f · %.0f"), FPPlayer->Health(), FPPlayer->Qhi(), FPPlayer->Stamina()); };
		I.Hint = FString::Printf(TEXT("Qhi regenerates %.1f per second at these stats."), FPTuning.Magic.QhiRegen(FPPlayer->GetStats()));
		Menu.Add(I);
	}
	Menu.Add(FPButton(TEXT("Empty Qhi"), [this] { FPPlayer->SetQhiForTest(0.0f); }, TEXT("To feel regeneration and a refused cast.")));
	Menu.Add(FPButton(TEXT("Default stats"), [this] { FPPlayer->SetStats(FPTuning.Magic.Stats); }, TEXT("Back to Content/Data/firstperson.json.")));
	Menu.Add(FPButton(TEXT("Return to the start"), [this] {
		bDevPanel = false;
		SetPaused(false, EHDeviceNone);
		ResetFirstPerson(TEXT("developer"));
	}));
	Menu.Add(FPButton(TEXT("Close (F10)"), [this] { bDevPanel = false; SetPaused(false, EHDeviceNone); }));
}

void AEHGameDirector::ResetFirstPerson(const TCHAR* Why)
{
	ClearSpells();
	CloseSpellSelect(false);
	// The spell counts are per attempt (automation reads them after each reset).
	FPFireballHits = FPWallsMelted = FPWallsShattered = FPWallsExpired = FPWallsRaised = FPFizzles = FPRefusedNoQhi = FPRefusedNoRoom = 0;
	bFPCrouchToggled = false;
	bFPSprintToggled = false;
	RouterPtr->ResetHeld();
	if (FPPlayer)
	{
		FPPlayer->ResetToStart();
		FPPlayer->TakeEvents(FPEvents);
		FPEvents.Reset();
	}
	if (FPDummy)
	{
		FPDummy->ResetDummy();
	}
	ResetWolves();   // the alignment stays: a case can be repeated (and a Shadow stays a Shadow)
	ClearLockOn(TEXT("reset"));
	FPLockSwitches = 0;
	FPExorcism = -1.0f;
	FPWolfFocus = -1;
	CombatText.Clear();
	FPWolfIdleTalkAt.Reset();
	EndPrayer(TEXT("reset"));
	FPMessageLeft = 0.0f;
	FPPrayers = FPMessages = 0;
	HurtFlash = 0.0f;
	++FPResets;
	AutoLogLine(FString::Printf(TEXT("firstperson reset (%s) %s"), Why, *DescribeFirstPerson()));
}

void AEHGameDirector::BuildFirstPersonPause()
{
	Menu.Reset();
	MenuIndex = 0;
	MenuOwner = EHDeviceNone;
	MenuTitle = TEXT("Paused");
	Menu.Add(FPButton(TEXT("Resume"), [this] { SetPaused(false, EHDeviceNone); }));
	Menu.Add(FPButton(TEXT("Return to the start"), [this] {
		SetPaused(false, EHDeviceNone);
		ResetFirstPerson(TEXT("menu"));
	}, TEXT("Back to the Chapel entrance.")));
	Menu.Add(FPButton(TEXT("Settings"), [this] { SettingsReturn = EEHScreen::FirstPerson; SettingsPage = 0; GoTo(EEHScreen::Settings); }, TEXT("Controls, video, audio and accessibility.")));
	Menu.Add(FPHeader(TEXT("Training dummy")));
	{
		FEHMenuItem DummyItem;
		DummyItem.Label = TEXT("Dummy");
		DummyItem.Value = [this] { return FString(FPDummy ? EHDummyModeName(FPDummy->GetMode()) : TEXT("-")); };
		DummyItem.Change = [this](int32 D) {
			if (FPDummy)
			{
				constexpr int32 N = static_cast<int32>(EEHDummyMode::Count);
				FPDummy->SetMode(static_cast<EEHDummyMode>((static_cast<int32>(FPDummy->GetMode()) + D + N) % N));
			}
		};
		DummyItem.Hint = TEXT("Stand takes every hit, Guard blocks from the front, Strikes back throws a slow punch when you are close.");
		Menu.Add(DummyItem);
	}
	Menu.Add(FPButton(TEXT("Reset the dummy"), [this] {
		if (FPDummy)
		{
			FPDummy->ResetDummy();
		}
		SetPaused(false, EHDeviceNone);
	}, TEXT("Back to its place, its count cleared.")));
	Menu.Add(FPButton(FPWolves.Num() > 1 ? TEXT("Reset the wolves") : TEXT("Reset the wolf"), [this] {
		ResetWolves();
		SetPaused(false, EHDeviceNone);
	}, FPWolves.Num() > 1 ? TEXT("The Chapel wolves back at their rest, calm and unhurt.") : TEXT("The Chapel wolf back at its rest, calm and unhurt.")));
	Menu.Add(FPHeader(FString()));
	Menu.Add(FPButton(TEXT("Quit to desktop"), [this] { GoTo(EEHScreen::QuitConfirm); }));
}

void AEHGameDirector::HandleFirstPersonNav(const FEHNavEvent& E)
{
	if (bPaused)
	{
		HandleMenuNav(E);
		return;
	}
	if (bSpellSelect && Settings.SpellSelector == 1 && (E.Nav == EEHNav::Up || E.Nav == EEHNav::Down))
	{
		// The list also steps with the D-pad and W / S.
		SpellHighlight = FMath::Clamp(SpellHighlight + (E.Nav == EEHNav::Down ? 1 : -1), 0, SpellCount - 1);
		Audio.Play(TEXT("UiMove"), EEHSoundCat::Ui, 0.4f);
		return;
	}
	if (E.Nav == EEHNav::Pause && !E.bRepeat)
	{
		SetPaused(true, E.Device);
	}
}

void AEHGameDirector::PaintFirstPerson(FEHPainter& P)
{
	const float QhiY = FMath::Min(1014.0f, P.VirtualMax.Y - 28.0f);
	if (FPPlayer && QhiMeterAlpha > 0.01f && !bPaused)
	{
		// Qhi: the same thin line under Stamina, in a cold blue; it flashes the warning colour when a cast is refused.
		const float W = 280.0f;
		const float Frac = FPPlayer->QhiFraction();
		const FVector2f Pos(960.0f - W * 0.5f, QhiY);
		const float Denied = FMath::Clamp(1.0f - FPPlayer->SecondsSinceRefused() / 0.6f, 0.0f, 1.0f);
		P.Rect(Pos, FVector2f(W, 4.0f), EHStyle::Alpha(Denied > 0.0f ? FLinearColor::LerpUsingHSV(EHStyle::Abyss, EHStyle::HealthLow, 0.6f * Denied) : EHStyle::Abyss, 0.45f * QhiMeterAlpha + 0.4f * Denied));
		P.Rect(FVector2f(960.0f - W * 0.5f * Frac, Pos.Y), FVector2f(W * Frac, 4.0f), FLinearColor(0.42f, 0.66f, 1.0f, 0.8f * QhiMeterAlpha));
	}
	if (FPPlayer && StaminaMeterAlpha > 0.01f && !bPaused)
	{
		// Placeholder readout for the playtest (see Docs/FirstPerson.md): a thin line that shortens as Stamina drains.
		const float W = 280.0f;
		const float Frac = FPPlayer->StaminaFraction();
		const FVector2f Pos(960.0f - W * 0.5f, QhiY - 10.0f);
		P.Rect(Pos, FVector2f(W, 4.0f), EHStyle::Alpha(EHStyle::Abyss, 0.45f * StaminaMeterAlpha));
		const FLinearColor Fill = FPPlayer->IsExhausted() ? EHStyle::Alpha(EHStyle::HealthLow, 0.85f * StaminaMeterAlpha) : EHStyle::Alpha(EHStyle::TextPrimary, 0.75f * StaminaMeterAlpha);
		P.Rect(FVector2f(960.0f - W * 0.5f * Frac, Pos.Y), FVector2f(W * Frac, 4.0f), Fill);
	}
	if (FPPlayer && !bPaused)
	{
		// Health: the same thin line, above Stamina, only after being hurt (a playtest readout like Stamina's).
		const float HealthAlpha = FPPlayer->HealthFraction() < 0.999f ? FMath::Clamp(3.0f - FPPlayer->SecondsSinceHurt() * 0.25f, 0.35f, 1.0f) : 0.0f;
		if (HealthAlpha > 0.0f && Settings.StaminaMeter > 0)
		{
			const float W = 280.0f;
			const float Frac = FPPlayer->HealthFraction();
			P.Rect(FVector2f(960.0f - W * 0.5f, QhiY - 20.0f), FVector2f(W, 4.0f), EHStyle::Alpha(EHStyle::Abyss, 0.45f * HealthAlpha));
			P.Rect(FVector2f(960.0f - W * 0.5f * Frac, QhiY - 20.0f), FVector2f(W * Frac, 4.0f), EHStyle::Alpha(EHStyle::HealthLow, 0.85f * HealthAlpha));
		}
		if (HurtFlash > 0.0f)
		{
			// A brief darkening at the edges when a strike lands.
			const float A = 0.45f * HurtFlash;
			P.Gradient(FVector2f(P.VirtualMin.X, P.VirtualMin.Y), FVector2f(P.VirtualMax.X - P.VirtualMin.X, 160.0f), FLinearColor(0.25f, 0, 0, A), FLinearColor(0.25f, 0, 0, 0));
			P.Gradient(FVector2f(P.VirtualMin.X, P.VirtualMax.Y - 160.0f), FVector2f(P.VirtualMax.X - P.VirtualMin.X, 160.0f), FLinearColor(0.25f, 0, 0, 0), FLinearColor(0.25f, 0, 0, A));
		}
		// The dummy's count, above its head: a training readout, placeholder text.
		APlayerController* PC = GetWorld()->GetFirstPlayerController();
		FVector2D Screen2D;
		if (FPDummy && PC && SpellSelectAlpha < 0.01f && FVector::Dist(FPDummy->GetActorLocation(), FPPlayer->GetActorLocation()) < 1500.0f &&
			PC->ProjectWorldLocationToScreen(FPDummy->LabelLocation(), Screen2D, true))
		{
			const FVector2f At = P.ToVirtual(FVector2f(Screen2D.X, Screen2D.Y) / FMath::Max(0.01f, FSlateApplication::Get().GetApplicationScale()));
			const FString Head = FString::Printf(TEXT("Training dummy · %s"), EHDummyModeName(FPDummy->GetMode()));
			const FString Count = FString::Printf(TEXT("Hits %d · Blocked %d · Damage %.0f"), FPDummy->Hits(), FPDummy->Blocks(), FPDummy->TotalDamage());
			P.Text(Head, At, Fonts.Sized(Fonts.BodyMedium, 20), EHStyle::Alpha(EHStyle::TextPrimary, 0.8f), 0.5f, 1.0f);
			P.Text(Count, At + FVector2f(0, 4), Fonts.Sized(Fonts.Body, 18), EHStyle::Alpha(EHStyle::TextSecondary, 0.8f), 0.5f, 0.0f);
			if (FPDummy->SecondsSinceHit() < 1.5f && !FPDummy->LastText().IsEmpty())
			{
				P.Text(FPDummy->LastText(), At + FVector2f(0, 30), Fonts.Sized(Fonts.Body, 18), EHStyle::Alpha(EHStyle::TextPrimary, 0.9f * (1.0f - FPDummy->SecondsSinceHit() / 1.5f)), 0.5f, 0.0f);
			}
		}
	}
#if !UE_BUILD_SHIPPING
	// Development builds: the debug view's readouts, the alignment and the wolf's state above it.
	if (FPPlayer && FPWolf && !bPaused && SpellSelectAlpha < 0.01f)
	{
		P.Text(FString::Printf(TEXT("Alignment: %s (%s)  ·  F10"), EHAlign::Name(FPAlignment), EHAlign::BandName(EHAlign::Band(FPAlignment))),
			FVector2f(P.VirtualMin.X + 28.0f, P.VirtualMin.Y + 24.0f), Fonts.Sized(Fonts.Body, 20), EHStyle::Alpha(EHStyle::TextSecondary, 0.75f), 0.0f, 0.0f);
		for (int32 i = 0; i < FPWolves.Num(); ++i)
		{
			const AEHWolf* W = FPWolves[i];
			FVector2D S2;
			if (W && GetWorld()->GetFirstPlayerController() && GetWorld()->GetFirstPlayerController()->ProjectWorldLocationToScreen(W->LabelLocation(), S2, true) &&
				FVector::Dist(W->GetActorLocation(), FPPlayer->GetActorLocation()) < 2500.0f)
			{
				static const TCHAR* Roles[] = {TEXT(""), TEXT(" · turn"), TEXT(" · waiting"), TEXT(" · standing back")};
				const FVector2f At = P.ToVirtual(FVector2f(S2.X, S2.Y) / FMath::Max(0.01f, FSlateApplication::Get().GetApplicationScale()));
				P.Text(FString::Printf(TEXT("Wolf %d · %s · %.0f HP%s%s"), i + 1, EHWolfStateName(W->GetState()), W->HealthValue(), W->IsProvoked() ? TEXT(" · provoked") : TEXT(""),
					Roles[static_cast<int32>(W->GetPackRole())]), At, Fonts.Sized(Fonts.Body, 18), EHStyle::Alpha(EHStyle::TextPrimary, 0.8f), 0.5f, 1.0f);
			}
		}
	}
#endif
	if (FPPlayer && !bPaused)
	{
		// Combat text: beside each speaker (development labels above stay readable: bubbles sit above them).
		APlayerController* PC = GetWorld()->GetFirstPlayerController();
		const float AppScale = FMath::Max(0.01f, FSlateApplication::Get().GetApplicationScale());
		CombatText.Paint(P, Fonts, FPPlayer->Camera()->GetComponentTransform(), [&](const FVector& World, FVector2f& Out) {
			FVector2D S;
			if (PC == nullptr || !PC->ProjectWorldLocationToScreen(World, S, true))
			{
				return false;
			}
			Out = P.ToVirtual(FVector2f(S.X, S.Y) / AppScale);
			return true;
		}, Settings.bReduceFlash);
	}
	if (!bPaused)
	{
		PaintLockOn(P);
		PaintChapel(P);
		PaintSpellSelect(P);
	}
	if (FPExorcism >= 0.0f)
	{
		// The exorcism: the view whitens, then the ending's words (the creator's to write) over the light.
		P.NextLayer();
		const float W = FMath::Clamp(FPExorcism / 2.5f, 0.0f, 1.0f);
		P.Fill(FLinearColor(0.96f, 0.95f, 0.90f, W * W));
		const float T = FMath::Clamp((FPExorcism - 2.5f) / 1.0f, 0.0f, 1.0f);
		if (T > 0.0f)
		{
			const FLinearColor Ink(0.08f, 0.07f, 0.09f, T);
			P.Text(TEXT("Exorcised"), FVector2f(960.0f, 470.0f), Fonts.Sized(Fonts.DisplayLight, 64), Ink, 0.5f, 0.5f);
			P.Text(TEXT("PLACEHOLDER: a permanent death. The Chapel's wolves banished the Shadow."), FVector2f(960.0f, 560.0f), Fonts.Sized(Fonts.Body, 24), FLinearColor(0.08f, 0.07f, 0.09f, 0.75f * T), 0.5f, 0.5f);
		}
	}
	// Every piece of art in this build is a stand-in; say so where a reviewer will see it.
	P.Text(TEXT("First-person prototype - placeholder art and animation"), FVector2f(P.VirtualMin.X + 28.0f, P.VirtualMax.Y - 24.0f),
		Fonts.Sized(Fonts.Body, 20), EHStyle::Alpha(EHStyle::TextSecondary, 0.55f), 0.0f, 1.0f, false);
	if (bPaused)
	{
		P.NextLayer();
		P.NextLayer();
		P.Fill(FLinearColor(0, 0, 0, 0.55f));
		PaintMenu(P, MenuTitle, true);
	}
}

FString AEHGameDirector::DescribeFirstPerson() const
{
	if (FPPlayer == nullptr)
	{
		return TEXT("no player");
	}
	const UCharacterMovementComponent* Move = FPPlayer->GetCharacterMovement();
	const FVector Feet = FPPlayer->FeetLocation();
	const FRotator R = FPPlayer->GetControlRotation();
	const FEHFists& Fi = FPPlayer->GetFists();
	FString Out = FString::Printf(TEXT("feet=(%.1f,%.1f,%.1f) yaw=%.1f pitch=%.1f speed=%.1f vz=%.1f mode=%d crouched=%d sprinting=%d stamina=%.1f exhausted=%d water=%.1f eye=%.1f cam_z=%.1f resets=%d"),
		Feet.X, Feet.Y, Feet.Z, FRotator::NormalizeAxis(R.Yaw), FRotator::NormalizeAxis(R.Pitch), FPPlayer->GetVelocity().Size2D(), FPPlayer->GetVelocity().Z,
		static_cast<int32>(Move->MovementMode.GetValue()), FPPlayer->bIsCrouched ? 1 : 0, FPPlayer->IsSprinting() ? 1 : 0, FPPlayer->Stamina(), FPPlayer->IsExhausted() ? 1 : 0,
		FPPlayer->WaterDepthAtFeet(), FPPlayer->EyeHeight(), FPPlayer->Camera()->GetComponentLocation().Z, FPResets);
	Out += FString::Printf(TEXT(" health=%.1f action=%s frame=%d guard=%.2f arms=%d deaths=%d"), FPPlayer->Health(), EHFistActionName(Fi.Action()), Fi.Frame(), Fi.GuardLevel(),
		FPPlayer->ViewArms() && FPPlayer->ViewArms()->AreShown() ? 1 : 0, FPDeaths);
	const FEHPlayerStats& St = FPPlayer->GetStats();
	Out += FString::Printf(TEXT(" qhi=%.1f/%.0f stats=%d/%d/%d/%d casts=%d refused=%d fireballs=%d walls=%d"), FPPlayer->Qhi(), St.Qhi, St.Intelligence, St.Faith, St.Dexterity, St.MartialProwess,
		FPPlayer->SpellsCast(), FPPlayer->SpellsRefused(), FPFireballs.Num(), FPWalls.Num());
	for (const AEHIceWall* W : FPWalls)
	{
		if (W)
		{
			Out += FString::Printf(TEXT(" wall=(%.0f,%.0f %s hp=%.0f left=%.1f)"), W->GetActorLocation().X, W->GetActorLocation().Y, W->PhaseName(), W->HealthLeft(), W->SecondsLeft());
		}
	}
	Out += FString::Printf(TEXT(" alignment=%s"), EHAlign::Name(FPAlignment));
	Out += FString::Printf(TEXT(" clock=%.2fh"), FPClockHours);
	if (FPWolf)
	{
		Out += FString::Printf(TEXT(" wolf=(%.0f,%.0f) %s"), FPWolf->GetActorLocation().X, FPWolf->GetActorLocation().Y, *FPWolf->Describe());
	}
	if (FPDummy)
	{
		Out += FString::Printf(TEXT(" dummy=(%.1f,%.1f) %s %s hits=%d blocks=%d damage=%.1f strikes=%d frozen=%.2f"), FPDummy->GetActorLocation().X, FPDummy->GetActorLocation().Y,
			EHDummyModeName(FPDummy->GetMode()), *FPDummy->StateName(), FPDummy->Hits(), FPDummy->Blocks(), FPDummy->TotalDamage(), FPDummy->StrikesThrown(), FPDummy->FrozenSeconds());
	}
	return Out;
}

bool AEHGameDirector::RunFirstPersonCommand(const TArray<FString>& T, const FString& Line)
{
	const FString& Cmd = T[0];
	auto Arg = [&T](int32 i, const TCHAR* Default) { return T.IsValidIndex(i) ? T[i] : FString(Default); };
	auto F = [&](int32 i, float Default) { return T.IsValidIndex(i) ? FCString::Atof(*T[i]) : Default; };
	if (Cmd == TEXT("look"))
	{
		// look <dx> <dy>: mouse movement in counts through the router, as the device would send it.
		RouterPtr->InjectMouseMove(FVector2D(F(1, 0.0f), F(2, 0.0f)));
		return true;
	}
	if (Cmd == TEXT("fp_state"))
	{
		AutoLogLine(FString::Printf(TEXT("fp_state %s %s"), *Arg(1, TEXT("")), *DescribeFirstPerson()));
		return true;
	}
	if (Cmd == TEXT("fp_mark"))
	{
		// fp_mark: remembers where the feet are, for fp_expect moved.
		FPMark = FPPlayer ? FPPlayer->FeetLocation() : FVector::ZeroVector;
		AutoLogLine(FString::Printf(TEXT("fp_mark (%.1f,%.1f,%.1f)"), FPMark.X, FPMark.Y, FPMark.Z));
		return true;
	}
	if (Cmd == TEXT("fp_reset"))
	{
		ResetFirstPerson(TEXT("script"));
		return true;
	}
	if (Cmd == TEXT("fp_expect"))
	{
		// fp_expect <field> <lt|gt|eq|near> <value> [tolerance]
		if (FPPlayer == nullptr)
		{
			AutoLogLine(FString::Printf(TEXT("FAIL %s (no player)"), *Line));
			return true;
		}
		const FString Field = Arg(1, TEXT("stamina"));
		const FVector Feet = FPPlayer->FeetLocation();
		const FRotator R = FPPlayer->GetControlRotation();
		float V = 0.0f;
		if (Field == TEXT("stamina")) V = FPPlayer->Stamina();
		else if (Field == TEXT("speed")) V = FPPlayer->GetVelocity().Size2D();
		else if (Field == TEXT("vz")) V = FPPlayer->GetVelocity().Z;
		else if (Field == TEXT("x")) V = Feet.X;
		else if (Field == TEXT("y")) V = Feet.Y;
		else if (Field == TEXT("z")) V = Feet.Z;
		else if (Field == TEXT("yaw")) V = FRotator::NormalizeAxis(R.Yaw);
		else if (Field == TEXT("pitch")) V = FRotator::NormalizeAxis(R.Pitch);
		else if (Field == TEXT("crouched")) V = FPPlayer->bIsCrouched ? 1.0f : 0.0f;
		else if (Field == TEXT("sprinting")) V = FPPlayer->IsSprinting() ? 1.0f : 0.0f;
		else if (Field == TEXT("exhausted")) V = FPPlayer->IsExhausted() ? 1.0f : 0.0f;
		else if (Field == TEXT("falling")) V = FPPlayer->GetCharacterMovement()->IsFalling() ? 1.0f : 0.0f;
		else if (Field == TEXT("water")) V = FPPlayer->WaterDepthAtFeet();
		else if (Field == TEXT("eye")) V = FPPlayer->EyeHeight();
		else if (Field == TEXT("paused")) V = bPaused ? 1.0f : 0.0f;
		else if (Field == TEXT("screen")) V = static_cast<float>(static_cast<int32>(Screen));
		else if (Field == TEXT("fov")) V = FPPlayer->Camera()->FieldOfView;
		else if (Field == TEXT("moved")) V = FVector::Dist(FPPlayer->FeetLocation(), FPMark);
		else if (Field == TEXT("health")) V = FPPlayer->Health();
		else if (Field == TEXT("deaths")) V = static_cast<float>(FPDeaths);
		else if (Field == TEXT("guarded")) V = static_cast<float>(FPGuardedCount);
		else if (Field == TEXT("rumbles")) V = static_cast<float>(RumbleCount);
		else if (FPDummy && Field == TEXT("dummy_headback")) V = FPDummy->HeadBackDegrees();
		else if (FPDummy && Field == TEXT("dummy_chestback")) V = FPDummy->ChestBackDegrees();
		else if (FPDummy && Field == TEXT("dummy_body")) V = FPDummy->WasBodyShot() ? 1.0f : 0.0f;
		else if (FPDummy && Field == TEXT("dummy_headpeak")) V = FPDummy->PeakHeadBack();
		else if (FPDummy && Field == TEXT("dummy_chestpeak")) V = FPDummy->PeakChestBack();
		else if (Field == TEXT("hurt")) V = static_cast<float>(FPHurtCount);
		else if (Field == TEXT("qhi")) V = FPPlayer->Qhi();
		else if (Field == TEXT("qhi_max")) V = FPPlayer->GetStats().Qhi;
		else if (Field == TEXT("health_max")) V = FPPlayer->GetStats().Health;
		else if (Field == TEXT("casts")) V = static_cast<float>(FPPlayer->SpellsCast());
		else if (Field == TEXT("refused")) V = static_cast<float>(FPPlayer->SpellsRefused());
		else if (Field == TEXT("refused_qhi")) V = static_cast<float>(FPRefusedNoQhi);
		else if (Field == TEXT("refused_room")) V = static_cast<float>(FPRefusedNoRoom);
		else if (Field == TEXT("fizzles")) V = static_cast<float>(FPFizzles);
		else if (Field == TEXT("fireballs")) V = static_cast<float>(FPFireballs.Num());
		else if (Field == TEXT("fireball_hits")) V = static_cast<float>(FPFireballHits);
		else if (Field == TEXT("walls")) V = static_cast<float>(FPWalls.FilterByPredicate([](const AEHIceWall* W) { return W && W->IsSolid(); }).Num());
		else if (Field == TEXT("puddles")) V = static_cast<float>(FPWalls.FilterByPredicate([](const AEHIceWall* W) { return W && W->HasPuddle(); }).Num());
		else if (Field == TEXT("walls_raised")) V = static_cast<float>(FPWallsRaised);
		else if (Field == TEXT("walls_melted")) V = static_cast<float>(FPWallsMelted);
		else if (Field == TEXT("walls_shattered")) V = static_cast<float>(FPWallsShattered);
		else if (Field == TEXT("walls_expired")) V = static_cast<float>(FPWallsExpired);
		else if (Field == TEXT("wall_solid")) V = FPWalls.Num() > 0 && FPWalls.Last() && FPWalls.Last()->IsSolid() ? 1.0f : 0.0f;
		else if (Field == TEXT("wall_hp")) V = FPWalls.Num() > 0 && FPWalls.Last() ? FPWalls.Last()->HealthLeft() : 0.0f;
		else if (Field == TEXT("wall_ice_water")) V = FPWalls.Num() > 0 && FPWalls.Last() && FPWalls.Last()->FroseWater() ? 1.0f : 0.0f;
		else if (Field == TEXT("wall_dist")) V = FPWalls.Num() > 0 && FPWalls.Last() ? FVector::Dist2D(FPWalls.Last()->GetActorLocation(), FPPlayer->GetActorLocation()) : 0.0f;
		else if (Field == TEXT("dev_panel")) V = bDevPanel ? 1.0f : 0.0f;
		else if (Field == TEXT("selecting")) V = bSpellSelect ? 1.0f : 0.0f;
		else if (Field == TEXT("alignment")) V = static_cast<float>(FPAlignment);
		else if (Field == TEXT("wolf_harms")) V = static_cast<float>(FPWolfHarms);
		else if (Field == TEXT("wolf_kills")) V = static_cast<float>(FPWolfKills);
		else if (Field == TEXT("reflected")) V = static_cast<float>(FPReflected);
		else if (FPWolf && Field == TEXT("wolf_state")) V = static_cast<float>(static_cast<int32>(FPWolf->GetState()));
		else if (FPWolf && Field == TEXT("wolf_calm")) V = FPWolf->IsCalmLike() ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_lying")) V = FPWolf->IsLying() ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_asleep")) V = FPWolf->GetState() == EEHWolfState::Sleep ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_warning")) V = FPWolf->GetState() == EEHWolfState::Warn ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_escalated")) V = FPWolf->IsEscalated() ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_sanctuary")) V = FPWolf->GetState() == EEHWolfState::Sanctuary ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_greeting")) V = FPWolf->GetState() == EEHWolfState::Greet ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_beside")) V = FPWolf->GetState() == EEHWolfState::Beside ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_hackles")) V = FPWolf->Hackles();
		else if (FPWolf && Field == TEXT("wolf_warned_for")) V = FPWolf->WarnedFor();
		else if (Field == TEXT("wolf_alerts")) V = static_cast<float>(FPAlerts);
		else if (Field == TEXT("wolf_escalations")) V = static_cast<float>(FPEscalations);
		else if (Field == TEXT("wolf_talks")) V = static_cast<float>(FPWolfTalks);
		else if (Field == TEXT("wolf_focus")) V = static_cast<float>(FPWolfFocus);
		else if (Field == TEXT("shadow")) V = bFPShadow ? 1.0f : 0.0f;
		else if (Field == TEXT("shadow_pray_hours")) V = static_cast<float>(FPShadowPrayHours);
		else if (Field == TEXT("exorcising")) V = FPExorcism >= 0.0f ? 1.0f : 0.0f;
		else if (Field == TEXT("exorcisms")) V = static_cast<float>(FPExorcisms);
		else if (Field == TEXT("locked_on")) V = FPLockTarget.IsValid() ? 1.0f : 0.0f;
		else if (Field == TEXT("lock_target")) V = static_cast<float>(LockTargetIndex());
		else if (Field == TEXT("lock_switches")) V = static_cast<float>(FPLockSwitches);
		else if (FPWolf && Field == TEXT("wolf_hostile")) V = FPWolf->IsHostile() ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_provoked")) V = FPWolf->IsProvoked() ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_dead")) V = FPWolf->IsDead() ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_frozen")) V = FPWolf->IsFrozen() ? 1.0f : 0.0f;
		else if (FPWolf && Field == TEXT("wolf_health")) V = FPWolf->HealthValue();
		else if (FPWolf && Field == TEXT("wolf_dist")) V = FVector::Dist2D(FPWolf->GetActorLocation(), FPPlayer->GetActorLocation());
		else if (Field == TEXT("clock_hour")) V = static_cast<float>(FMath::Fmod(FPClockHours, static_cast<double>(FPTuning.Clock.DayHours)));
		else if (Field == TEXT("clock_day")) V = static_cast<float>(FMath::FloorToDouble(FPClockHours / FPTuning.Clock.DayHours));
		else if (Field == TEXT("sky_light")) V = FPClockNow.Light;
		else if (Field == TEXT("glass_glow")) V = FPClockNow.Glass;
		else if (Field == TEXT("placed_loops")) V = static_cast<float>(Audio.PlacedLoopCount());
		else if (Field == TEXT("sparks")) V = static_cast<float>(FPSparks);
		else if (PackField(Field, V)) {}
		else if (CombatTextField(Field, V)) {}
		else if (Field == TEXT("praying")) V = bPraying ? 1.0f : 0.0f;
		else if (Field == TEXT("prayers")) V = static_cast<float>(FPPrayers);
		else if (Field == TEXT("prayer_seconds")) V = PrayerSeconds;
		else if (Field == TEXT("interact_focus")) V = static_cast<float>(FPInteractFocus);
		else if (Field == TEXT("interact_messages")) V = static_cast<float>(FPMessages);
		else if (FPWolf && Field == TEXT("wolf_home_dist")) V = FVector::Dist2D(FPWolf->FeetLocation(), FPTuning.Wolf.Home);
		else if (FPWolf && Field == TEXT("wolf_bites")) V = static_cast<float>(FPWolf->Bites());
		else if (FPWolf && Field == TEXT("wolf_lunges")) V = static_cast<float>(FPWolf->Lunges());
		else if (FPWolf && Field == TEXT("wolf_connected")) V = static_cast<float>(FPWolf->Connected());
		else if (FPWolf && Field == TEXT("wolf_reactions")) V = static_cast<float>(FPWolf->HitReactions());
		else if (FPWolf && Field == TEXT("wolf_rebuffs")) V = static_cast<float>(FPWolf->RebuffCount());
		else if (FPWolf && Field == TEXT("wolf_tilt")) V = FPWolf->ReactionTilt();
		else if (FPWolf && Field == TEXT("wolf_tilt_peak")) V = FPWolf->ReactionPeak();
		else if (FPWolf && Field == TEXT("wolf_disengages")) V = static_cast<float>(FPWolf->Disengages());
		else if (FPWolf && Field == TEXT("wolf_absorbed")) V = static_cast<float>(FPWolf->Absorbed());
		else if (FPWolf && Field == TEXT("wolf_protects")) V = static_cast<float>(FPWolf->Protects());
		else if (FPWolf && Field == TEXT("wolf_freezes")) V = static_cast<float>(FPWolf->Freezes());
		else if (FPWolf && Field == TEXT("wolf_y")) V = FPWolf->GetActorLocation().Y;
		else if (FPWolf && Field == TEXT("wolf_path"))
		{
			// Navigation path length from the wolf to the player (-1 when there is none): an Ice Wall lengthens it.
			const UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(), FPWolf->FeetLocation(), FPPlayer->FeetLocation(), FPWolf);
			V = Path && Path->IsValid() && !Path->IsPartial() ? Path->GetPathLength() : -1.0f;
		}
		else if (Field == TEXT("select_highlight")) V = static_cast<float>(SpellHighlight);
		else if (Field == TEXT("select_casts")) V = static_cast<float>(SpellSelectCasts);
		else if (Field == TEXT("time_dilation")) V = UGameplayStatics::GetGlobalTimeDilation(this);
		else if (FPDummy && Field == TEXT("dummy_frozen")) V = FPDummy->IsFrozen() ? 1.0f : 0.0f;
		else if (FPDummy && Field == TEXT("dummy_freezes")) V = static_cast<float>(FPDummy->TimesFrozen());
		else if (Field == TEXT("action")) V = static_cast<float>(static_cast<int32>(FPPlayer->GetFists().Action()));
		else if (Field == TEXT("guarding")) V = FPPlayer->GetFists().IsGuarding() ? 1.0f : 0.0f;
		else if (Field == TEXT("arms")) V = FPPlayer->ViewArms() && FPPlayer->ViewArms()->AreShown() ? 1.0f : 0.0f;
		else if (FPDummy && Field == TEXT("dummy_hits")) V = static_cast<float>(FPDummy->Hits());
		else if (FPDummy && Field == TEXT("dummy_blocks")) V = static_cast<float>(FPDummy->Blocks());
		else if (FPDummy && Field == TEXT("dummy_damage")) V = FPDummy->TotalDamage();
		else if (FPDummy && Field == TEXT("dummy_strikes")) V = static_cast<float>(FPDummy->StrikesThrown());
		else if (FPDummy && Field == TEXT("dummy_dist")) V = FVector::Dist2D(FPDummy->GetActorLocation(), FPPlayer->GetActorLocation());
		else if (FPDummy && Field == TEXT("dummy_moved")) V = FVector::Dist2D(FPDummy->GetActorLocation(), FPTuning.Dummy.Spawn);
		else
		{
			AutoLogLine(FString::Printf(TEXT("FAIL %s (unknown field)"), *Line));
			return true;
		}
		const FString Op = Arg(2, TEXT("eq"));
		const float Want = F(3, 0.0f);
		const float Tol = F(4, 0.5f);
		const bool bOk = Op == TEXT("lt") ? V < Want : (Op == TEXT("gt") ? V > Want : (Op == TEXT("near") ? FMath::Abs(V - Want) <= Tol : FMath::IsNearlyEqual(V, Want, 0.01f)));
		AutoLogLine(FString::Printf(TEXT("%s %s (is %.2f)"), bOk ? TEXT("ok") : TEXT("FAIL"), *Line, V));
		return true;
	}
	if (Cmd == TEXT("fp_dummy"))
	{
		// fp_dummy <stand|guard|strikes>
		const FString M = Arg(1, TEXT("stand"));
		if (FPDummy)
		{
			FPDummy->SetMode(M == TEXT("guard") ? EEHDummyMode::Guard : (M == TEXT("strikes") ? EEHDummyMode::Strikes : EEHDummyMode::Stand));
		}
		AutoLogLine(FString::Printf(TEXT("%s%s"), FPDummy ? TEXT("") : TEXT("FAIL "), *Line));
		return true;
	}
	if (Cmd == TEXT("fp_dummy_reset"))
	{
		if (FPDummy)
		{
			FPDummy->ResetDummy();
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_wolf_reset"))
	{
		// What the pause menu's Reset the wolf does.
		ResetWolves();
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_selector"))
	{
		// fp_selector <wheel|list>: what Settings > Controls > Spell selector does.
		Settings.SpellSelector = Arg(1, TEXT("wheel")) == TEXT("list") ? 1 : 0;
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_devkey"))
	{
		// fp_devkey: F10 as the keyboard sends it (development builds open the panel; Shipping ignores it).
		RouterPtr->InjectDeveloperKey();
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_focus_lost"))
	{
		// What the frame loop does when the window loses focus: pause and drop every held input.
		RouterPtr->ResetForFocusLoss();
		if (Screen == EEHScreen::FirstPerson && !bPaused)
		{
			SetPaused(true, EHDeviceNone);
		}
		AutoLogLine(TEXT("fp_focus_lost"));
		return true;
	}
#if !UE_BUILD_SHIPPING
	// Development-only test tools: they move the player or change the world, so Shipping builds leave them out.
	if (Cmd == TEXT("fp_frames"))
	{
		// fp_frames <count> <name>: one screenshot per rendered frame, starting next frame.
		FrameCaptureLeft = FMath::Clamp(FCString::Atoi(*Arg(1, TEXT("30"))), 1, 600);
		FrameCaptureName = Arg(2, TEXT("frame"));
		FrameCaptureIndex = 0;
		FrameCaptureNext = 0.0;
		UGameplayStatics::SetGlobalTimeDilation(this, 0.05f);
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_stat"))
	{
		// fp_stat <health|qhi|stamina|intelligence|faith|dexterity|martial> <value>: the developer panel's stat change.
		if (FPPlayer)
		{
			FEHPlayerStats S = FPPlayer->GetStats();
			const FString N = Arg(1, TEXT(""));
			const float V = F(2, 10.0f);
			if (N == TEXT("health")) S.Health = V;
			else if (N == TEXT("qhi")) S.Qhi = V;
			else if (N == TEXT("stamina")) S.Stamina = V;
			else if (N == TEXT("intelligence")) S.Intelligence = FMath::RoundToInt(V);
			else if (N == TEXT("faith")) S.Faith = FMath::RoundToInt(V);
			else if (N == TEXT("dexterity")) S.Dexterity = FMath::RoundToInt(V);
			else if (N == TEXT("martial")) S.MartialProwess = FMath::RoundToInt(V);
			else
			{
				AutoLogLine(FString::Printf(TEXT("FAIL %s (unknown stat)"), *Line));
				return true;
			}
			FPPlayer->SetStats(S);
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_align"))
	{
		// fp_align <0..8>: the developer selector's alignment tier (0 Hero of Humanity, 4 Platonic, 8 Forsaken).
		FPAlignment = FMath::Clamp(FCString::Atoi(*Arg(1, TEXT("4"))), 0, EHAlign::Count - 1);
		AutoLogLine(FString::Printf(TEXT("%s -> %s"), *Line, EHAlign::Name(FPAlignment)));
		return true;
	}
	if (Cmd == TEXT("fp_wolf_rest"))
	{
		// fp_wolf_rest <0|1> [wolf index]: lie down now (1: asleep), as at rest.
		const int32 Index = T.Num() > 2 ? FCString::Atoi(*T[2]) : 0;
		if (AEHWolf* W = FPWolves.IsValidIndex(Index) ? FPWolves[Index].Get() : nullptr)
		{
			W->RestForTest(FCString::Atoi(*Arg(1, TEXT("0"))) != 0);
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_escalate"))
	{
		// fp_escalate: the warning an evil aura gets is over at once and the fight starts (pack tests start there).
		for (AEHWolf* W : FPWolves)
		{
			if (W && !W->IsDead())
			{
				W->Escalate();
			}
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_shadow_hours"))
	{
		// fp_shadow_hours <h>: in-game hours a Shadow has already prayed (three days, 432 hours, restore it).
		FPShadowPrayHours = F(1, 0.0f);
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_shadow"))
	{
		// fp_shadow <0|1>: the player as a Shadow (the developer panel's Shadow item).
		bFPShadow = FCString::Atoi(*Arg(1, TEXT("1"))) != 0;
		FPShadowPrayHours = 0.0;
		AutoLogLine(FString::Printf(TEXT("%s -> shadow=%d"), *Line, bFPShadow ? 1 : 0));
		return true;
	}
	if (Cmd == TEXT("fp_clock"))
	{
		// fp_clock <hour>: sets the hour of the current day (0 = midnight; the day is clock.dayHours long).
		const double Day = FMath::FloorToDouble(FPClockHours / FPTuning.Clock.DayHours);
		FPClockHours = Day * FPTuning.Clock.DayHours + FMath::Clamp(F(1, 0.0f), 0.0f, FPTuning.Clock.DayHours - 0.001f);
		ApplyWorldClock(true);
		AutoLogLine(FString::Printf(TEXT("%s -> hour %.2f light %.2f glass %.2f"), *Line, FMath::Fmod(FPClockHours, (double)FPTuning.Clock.DayHours), FPClockNow.Light, FPClockNow.Glass));
		return true;
	}
	if (Cmd == TEXT("fp_wolves"))
	{
		// fp_wolves <1..4>: the pack's size (what the developer panel's Wolves does).
		SpawnPack(FMath::RoundToInt(F(1, 1.0f)));
		AutoLogLine(FString::Printf(TEXT("%s -> %d"), *Line, FPWolves.Num()));
		return true;
	}
	if (Cmd == TEXT("fp_pack_ring"))
	{
		// fp_pack_ring <radius>: every living wolf placed round the player at this distance, at rest, facing them.
		const float R = F(1, 300.0f);
		int32 N = 0;
		for (int32 i = 0; i < FPWolves.Num(); ++i)
		{
			AEHWolf* W = FPWolves[i];
			if (W && !W->IsDead() && FPPlayer)
			{
				const float A = 2.0f * PI * i / FMath::Max(1, FPWolves.Num());
				const FVector At = FPPlayer->GetActorLocation() + FVector(FMath::Cos(A), FMath::Sin(A), 0.0f) * R;
				W->TeleportTo(FVector(At.X, At.Y, FPPlayer->FeetLocation().Z + 60.0f), (FPPlayer->GetActorLocation() - At).Rotation(), false, true);
				W->HaltForTest();
				++N;
			}
		}
		AutoLogLine(FString::Printf(TEXT("%s -> %d"), *Line, N));
		return true;
	}
	if (Cmd == TEXT("fp_hurt"))
	{
		// fp_hurt <damage>: a blow from straight ahead, as a strike would land (testing the pack's three-hits rule).
		if (FPPlayer)
		{
			FPPlayer->ReceiveStrike(F(1, 5.0f), FPPlayer->GetActorLocation() + FPPlayer->GetActorForwardVector() * 80.0f, true);
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_say"))
	{
		// fp_say <wolf index | player> <event> [friendly|warning|hostile|player]: a line said at once (no chance, no gaps).
		const FString Who = Arg(1, TEXT("player"));
		const FString Event = Arg(2, TEXT("wolf.hostile.attack"));
		const FString KindName = Arg(3, Who == TEXT("player") ? TEXT("player") : TEXT("hostile"));
		const EEHLineKind Kind = KindName == TEXT("friendly") ? EEHLineKind::Friendly : KindName == TEXT("warning") ? EEHLineKind::Warning
			: KindName == TEXT("player") ? EEHLineKind::Player : EEHLineKind::Hostile;
		const int32 i = FCString::Atoi(*Who);
		const AActor* Speaker = Who == TEXT("player") ? nullptr : (FPWolves.IsValidIndex(i) ? FPWolves[i].Get() : nullptr);
		const bool bShown = (Who == TEXT("player") || Speaker) && CombatText.Offer(Event, Speaker, Kind, GetWorld()->GetTimeSeconds(), true);
		AutoLogLine(FString::Printf(TEXT("%s -> %s"), *Line, bShown ? *CombatText.LastText : TEXT("(nothing)")));
		return true;
	}
	if (Cmd == TEXT("fp_setting"))
	{
		// fp_setting <reduceflash 0|1 | uiscale 0.8..1.4>: what the Accessibility settings change, for the text tests.
		const FString N = Arg(1, TEXT(""));
		if (N == TEXT("reduceflash"))
		{
			Settings.bReduceFlash = F(2, 0.0f) > 0.5f;
		}
		else if (N == TEXT("uiscale"))
		{
			Settings.UIScale = FMath::Clamp(F(2, 1.0f), 0.8f, 1.4f);
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_text_natural"))
	{
		// fp_text_natural <0|1>: lines arising on their own off/on (forced fp_say lines still show).
		CombatText.bNatural = F(1, 1.0f) > 0.5f;
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_text_stats"))
	{
		// Clears the combat text's running evidence (the most visible, the most overlaps) for the next case.
		CombatText.MaxVisibleSeen = CombatText.Visible();
		CombatText.OverlapsSeen = 0;
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_wolf_kill"))
	{
		// fp_wolf_kill <index>: a wolf dies at once (testing the pack's turns), with no alignment change.
		const int32 i = FMath::RoundToInt(F(1, 0.0f));
		if (FPWolves.IsValidIndex(i) && FPWolves[i])
		{
			FPWolves[i]->SetHealthForTest(1.0f);
			FPWolves[i]->ReceivePlayerHit(5.0f, FPWolves[i]->GetActorLocation() + FVector(100, 0, 0), FPWolves[i]->GetActorLocation(), false);
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_hide"))
	{
		// fp_hide <mesh name prefix | lights> <0|1>: hides static meshes whose mesh name starts with the prefix, or
		// switches off the interior's lights (tagged EHInterior); for measuring what a view's frame time is made of.
		const FString What = Arg(1, TEXT(""));
		const bool bHide = F(2, 1.0f) > 0.5f;
		int32 N = 0;
		for (TActorIterator<AActor> It(GetWorld()); It; ++It)
		{
			if (What == TEXT("lights"))
			{
				if (It->ActorHasTag(TEXT("EHInterior")))
				{
					for (ULightComponent* L : TInlineComponentArray<ULightComponent*>(*It))
					{
						L->SetVisibility(!bHide);
						++N;
					}
				}
				continue;
			}
			const AStaticMeshActor* SMA = Cast<AStaticMeshActor>(*It);
			const UStaticMesh* M = SMA && SMA->GetStaticMeshComponent() ? SMA->GetStaticMeshComponent()->GetStaticMesh() : nullptr;
			if (M && M->GetName().StartsWith(What))
			{
				It->SetActorHiddenInGame(bHide);
				++N;
			}
		}
		AutoLogLine(FString::Printf(TEXT("%s -> %d"), *Line, N));
		return true;
	}
	if (Cmd == TEXT("fp_wolf_freeze"))
	{
		if (FPWolf)
		{
			FPWolf->Freeze(2.0f);
		}
		AutoLogLine(FPWolf ? TEXT("ok fp_wolf_freeze") : TEXT("FAIL fp_wolf_freeze (no wolf)"));
		return true;
	}
	if (Cmd == TEXT("fp_wolf_place"))
	{
		// fp_wolf_place <x> <y> [yaw] [health] [wolf index, from 0]
		const int32 Index = T.Num() > 5 ? FCString::Atoi(*T[5]) : 0;
		if (AEHWolf* W = FPWolves.IsValidIndex(Index) ? FPWolves[Index].Get() : nullptr)
		{
			W->TeleportTo(FVector(F(1, 0.0f), F(2, -1450.0f), 125.0f), FRotator(0, F(3, 90.0f), 0), false, true);
			W->HaltForTest();
			if (T.Num() > 4 && FCString::Atof(*T[4]) > 0.0f)
			{
				W->SetHealthForTest(F(4, 60.0f));
			}
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_qhi"))
	{
		// fp_qhi <value>: sets the current Qhi (clamped to the pool).
		if (FPPlayer)
		{
			FPPlayer->SetQhiForTest(F(1, 0.0f));
		}
		AutoLogLine(FString::Printf(TEXT("%s -> %.1f"), *Line, FPPlayer ? FPPlayer->Qhi() : 0.0f));
		return true;
	}
	if (Cmd == TEXT("fp_teleport"))
	{
		// fp_teleport <x> <y> <z feet> [yaw] [pitch]
		if (FPPlayer)
		{
			const FVector Feet(F(1, 0.0f), F(2, 0.0f), F(3, 0.0f));
			FPPlayer->TeleportTo(Feet + FVector(0, 0, FPPlayer->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.0f), FRotator(0, F(4, -90.0f), 0), false, true);
			FPPlayer->GetCharacterMovement()->StopMovementImmediately();
			if (AController* C = FPPlayer->GetController())
			{
				C->SetControlRotation(FRotator(F(5, 0.0f), F(4, -90.0f), 0));
			}
		}
		AutoLogLine(FString::Printf(TEXT("%s -> %s"), *Line, *DescribeFirstPerson()));
		return true;
	}
	if (Cmd == TEXT("fp_arms_state"))
	{
		AutoLogLine(FString::Printf(TEXT("fp_arms_state %s"), FPPlayer && FPPlayer->ViewArms() ? *FPPlayer->ViewArms()->Describe() : TEXT("-")));
		return true;
	}
	if (Cmd == TEXT("fp_arms_fp"))
	{
		// fp_arms_fp <0|1>: first-person primitives on or off for the arms.
		if (FPPlayer && FPPlayer->ViewArms())
		{
			FPPlayer->ViewArms()->SetFirstPersonRendering(Arg(1, TEXT("1")) != TEXT("0"));
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_health"))
	{
		if (FPPlayer)
		{
			FPPlayer->SetHealthForTest(F(1, 100.0f));
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_dummy_place"))
	{
		// fp_dummy_place <x> <y> <yaw>
		if (FPDummy)
		{
			FPDummy->TeleportTo(FVector(F(1, 0.0f), F(2, -150.0f), 92.0f), FRotator(0, F(3, 90.0f), 0), false, true);
		}
		AutoLogLine(Line);
		return true;
	}
	if (Cmd == TEXT("fp_view"))
	{
		// fp_view <yaw> <pitch>: points the camera without moving.
		if (FPPlayer && FPPlayer->GetController())
		{
			FPPlayer->GetController()->SetControlRotation(FRotator(F(2, 0.0f), F(1, -90.0f), 0));
		}
		return true;
	}
	if (Cmd == TEXT("fp_box"))
	{
		// fp_box <x> <y> <z> <half x> <half y> <half z>: a labelled blocking test box (low ceilings, obstructions).
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		const FVector Centre(F(1, 0.0f), F(2, 0.0f), F(3, 0.0f));
		const FVector Half(F(4, 50.0f), F(5, 50.0f), F(6, 50.0f));
		AStaticMeshActor* Box = GetWorld()->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform(FRotator::ZeroRotator, Centre), Params);
		if (Box)
		{
			Box->SetMobility(EComponentMobility::Movable);
			Box->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")));
			Box->SetActorScale3D(Half / 50.0f);
			Box->GetStaticMeshComponent()->SetCollisionProfileName(TEXT("BlockAll"));
			Box->Tags.Add(TEXT("EHTestFixture"));
		}
		AutoLogLine(FString::Printf(TEXT("%s%s"), Box ? TEXT("") : TEXT("FAIL "), *Line));
		return true;
	}
	if (Cmd == TEXT("fp_planar"))
	{
		// fp_planar <on|off> [screen percent]: a planar reflection on the water plane, for the reflection experiment.
		// It only draws when the renderer allows global clip planes (r.AllowGlobalClipPlane=1, a start-up setting).
		static TWeakObjectPtr<APlanarReflection> Planar;
		if (Planar.IsValid())
		{
			Planar->Destroy();
			Planar.Reset();
		}
		if (Arg(1, TEXT("on")) == TEXT("on"))
		{
			FActorSpawnParameters Params;
			Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			Planar = GetWorld()->SpawnActor<APlanarReflection>(APlanarReflection::StaticClass(), FTransform(FRotator::ZeroRotator, FVector(0, -700, FPTuning.WaterSurfaceZ)), Params);
			if (Planar.IsValid())
			{
				UPlanarReflectionComponent* C = Planar->GetPlanarReflectionComponent();
				C->ScreenPercentage = FMath::Clamp(static_cast<int32>(F(2, 50.0f)), 25, 100);
				C->DistanceFromPlaneFadeoutStart = 40.0f;
				C->DistanceFromPlaneFadeoutEnd = 60.0f;
				Planar->SetActorScale3D(FVector(30.0f, 30.0f, 1.0f));
			}
		}
		const IConsoleVariable* Clip = IConsoleManager::Get().FindConsoleVariable(TEXT("r.AllowGlobalClipPlane"));
		AutoLogLine(FString::Printf(TEXT("%s planar=%d r.AllowGlobalClipPlane=%d"), *Line, Planar.IsValid() ? 1 : 0, Clip ? Clip->GetInt() : -1));
		return true;
	}
	if (Cmd == TEXT("fp_clear_boxes"))
	{
		int32 Removed = 0;
		for (TActorIterator<AStaticMeshActor> It(GetWorld()); It; ++It)
		{
			if (It->Tags.Contains(TEXT("EHTestFixture")))
			{
				It->Destroy();
				++Removed;
			}
		}
		AutoLogLine(FString::Printf(TEXT("fp_clear_boxes %d"), Removed));
		return true;
	}
	if (Cmd == TEXT("fp_body_visible"))
	{
		if (FPPlayer)
		{
			FPPlayer->SetBodyVisibleToSelf(Arg(1, TEXT("1")) != TEXT("0"));
		}
		AutoLogLine(Line);
		return true;
	}
#endif
	return false;
}
