// First-person play in the Drowned Chapel. The director keeps owning settings, menus, devices and
// automation; each frame it turns device state into one FEHFirstPersonInput for the player character.
#include "EHGameDirector.h"
#include "EHUIStyle.h"

#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EHPlayerCharacter.h"
#include "EHVfx.h"
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
	PC->SetViewTarget(FPPlayer);
	PC->bShowMouseCursor = false;
	PC->SetInputMode(FInputModeGameOnly());
	AutoLogLine(FString::Printf(TEXT("firstperson start body=%d tuning: %s"), FPPlayer->HasBodyPlaceholder() ? 1 : 0, *FPTuning.Describe()));
	UE_LOG(LogTemp, Display, TEXT("EbonyHearts: first-person tuning %s"), *FPTuning.Describe());
}

void AEHGameDirector::ApplyFieldOfView()
{
	if (FPPlayer)
	{
		FPPlayer->SetFieldOfView(static_cast<float>(Settings.FieldOfView));
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

	// Look: the mouse in degrees per count; the stick as a turn rate with a response curve, scaled by frame time.
	const float Invert = Settings.bInvertLook ? -1.0f : 1.0f;
	In.Look.X = static_cast<float>(Mouse.X) * Settings.MouseSensitivity;
	In.Look.Y = -static_cast<float>(Mouse.Y) * Settings.MouseSensitivity * Invert;
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
	return In;
}

void AEHGameDirector::TickFirstPerson(float DeltaSeconds)
{
	if (FPPlayer == nullptr)
	{
		BeginFirstPerson();
	}
	const FEHFirstPersonInput In = GatherFirstPersonInput(DeltaSeconds);
	LastFPInput = In;
	if (FPPlayer == nullptr || Screen != EEHScreen::FirstPerson || bPaused)
	{
		return;
	}
	FPPlayer->ApplyInput(In, DeltaSeconds);
	PlayFirstPersonEvents();
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
					Vfx->Ripple(FVector(E.Location.X, E.Location.Y, FPTuning.WaterSurfaceZ), 0.35f + 0.5f * Depth);
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
					Vfx->Ripple(FVector(E.Location.X, E.Location.Y, FPTuning.WaterSurfaceZ), 0.6f + 0.6f * E.Strength);
					if (E.Strength > 0.5f)
					{
						Vfx->Splash(FVector(E.Location.X, E.Location.Y, FPTuning.WaterSurfaceZ), 0.6f * E.Strength);
					}
				}
			}
			AutoLogLine(FString::Printf(TEXT("fp land strength=%.2f water=%.1f"), E.Strength, E.WaterDepth));
			break;
		case FEHFirstPersonEvent::EKind::Reset:
			break;
		}
	}
	FPEvents.Reset();
}

void AEHGameDirector::ResetFirstPerson(const TCHAR* Why)
{
	bFPCrouchToggled = false;
	bFPSprintToggled = false;
	RouterPtr->ResetHeld();
	if (FPPlayer)
	{
		FPPlayer->ResetToStart();
		FPPlayer->TakeEvents(FPEvents);
		FPEvents.Reset();
	}
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
	Menu.Add(FPButton(TEXT("Quit to desktop"), [this] { GoTo(EEHScreen::QuitConfirm); }));
}

void AEHGameDirector::HandleFirstPersonNav(const FEHNavEvent& E)
{
	if (bPaused)
	{
		HandleMenuNav(E);
		return;
	}
	if (E.Nav == EEHNav::Pause && !E.bRepeat)
	{
		SetPaused(true, E.Device);
	}
}

void AEHGameDirector::PaintFirstPerson(FEHPainter& P)
{
	if (FPPlayer && StaminaMeterAlpha > 0.01f && !bPaused)
	{
		// Placeholder readout for the playtest (see Docs/FirstPerson.md): a thin line that shortens as Stamina drains.
		const float W = 280.0f;
		const float Frac = FPPlayer->StaminaFraction();
		const FVector2f Pos(960.0f - W * 0.5f, 1004.0f);
		P.Rect(Pos, FVector2f(W, 4.0f), EHStyle::Alpha(EHStyle::Abyss, 0.45f * StaminaMeterAlpha));
		const FLinearColor Fill = FPPlayer->IsExhausted() ? EHStyle::Alpha(EHStyle::HealthLow, 0.85f * StaminaMeterAlpha) : EHStyle::Alpha(EHStyle::TextPrimary, 0.75f * StaminaMeterAlpha);
		P.Rect(FVector2f(960.0f - W * 0.5f * Frac, Pos.Y), FVector2f(W * Frac, 4.0f), Fill);
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
	return FString::Printf(TEXT("feet=(%.1f,%.1f,%.1f) yaw=%.1f pitch=%.1f speed=%.1f vz=%.1f mode=%d crouched=%d sprinting=%d stamina=%.1f exhausted=%d water=%.1f eye=%.1f cam_z=%.1f resets=%d"),
		Feet.X, Feet.Y, Feet.Z, FRotator::NormalizeAxis(R.Yaw), FRotator::NormalizeAxis(R.Pitch), FPPlayer->GetVelocity().Size2D(), FPPlayer->GetVelocity().Z,
		static_cast<int32>(Move->MovementMode.GetValue()), FPPlayer->bIsCrouched ? 1 : 0, FPPlayer->IsSprinting() ? 1 : 0, FPPlayer->Stamina(), FPPlayer->IsExhausted() ? 1 : 0,
		FPPlayer->WaterDepthAtFeet(), FPPlayer->EyeHeight(), FPPlayer->Camera()->GetComponentLocation().Z, FPResets);
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
	if (Cmd == TEXT("fp_focus_lost"))
	{
		// What the frame loop does when the window loses focus: pause and drop every held input.
		RouterPtr->ResetHeld();
		if (Screen == EEHScreen::FirstPerson && !bPaused)
		{
			SetPaused(true, EHDeviceNone);
		}
		AutoLogLine(TEXT("fp_focus_lost"));
		return true;
	}
#if !UE_BUILD_SHIPPING
	// Development-only test tools: they move the player or change the world, so Shipping builds leave them out.
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
