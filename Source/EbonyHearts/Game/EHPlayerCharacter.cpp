#include "EHPlayerCharacter.h"

#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Controller.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

bool FEHFirstPersonTuning::Load(const FString& Text, FString& OutError)
{
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		OutError = TEXT("Data/firstperson.json is not valid JSON.");
		return false;
	}
	bool bOk = true;
	auto Num = [&](const TCHAR* Name, float& Out, float Min, float Max) {
		double V = 0.0;
		if (!Root->TryGetNumberField(Name, V))
		{
			return;
		}
		if (V < Min || V > Max)
		{
			OutError = FString::Printf(TEXT("Data/firstperson.json: %s = %g is outside %g..%g."), Name, V, Min, Max);
			bOk = false;
			return;
		}
		Out = static_cast<float>(V);
	};
	Num(TEXT("walkSpeed"), WalkSpeed, 50, 2000);
	Num(TEXT("sprintSpeed"), SprintSpeed, 50, 3000);
	Num(TEXT("crouchSpeed"), CrouchSpeed, 20, 2000);
	Num(TEXT("acceleration"), Acceleration, 100, 20000);
	Num(TEXT("brakingDeceleration"), BrakingDeceleration, 100, 20000);
	Num(TEXT("groundFriction"), GroundFriction, 0, 50);
	Num(TEXT("airControl"), AirControl, 0, 1);
	Num(TEXT("jumpVelocity"), JumpVelocity, 0, 2000);
	Num(TEXT("jumpBufferSeconds"), JumpBufferSeconds, 0, 1);
	Num(TEXT("gravityScale"), GravityScale, 0.1f, 5);
	Num(TEXT("stepHeight"), StepHeight, 0, 80);
	Num(TEXT("walkableFloorDegrees"), WalkableFloorDegrees, 5, 80);
	Num(TEXT("capsuleRadius"), CapsuleRadius, 10, 80);
	Num(TEXT("standHeight"), StandHeight, 100, 250);
	Num(TEXT("crouchHeight"), CrouchHeight, 60, 250);
	Num(TEXT("standEyeHeight"), StandEyeHeight, 50, 240);
	Num(TEXT("crouchEyeHeight"), CrouchEyeHeight, 30, 240);
	Num(TEXT("eyeBlendSeconds"), EyeBlendSeconds, 0, 1);
	Num(TEXT("staminaMax"), StaminaMax, 1, 1000);
	Num(TEXT("sprintSecondsFromFull"), SprintSecondsFromFull, 0.5f, 120);
	Num(TEXT("staminaRecoverPerSecond"), StaminaRecoverPerSecond, 0, 1000);
	Num(TEXT("staminaRecoverDelay"), StaminaRecoverDelay, 0, 10);
	Num(TEXT("sprintRestartStamina"), SprintRestartStamina, 0, 1000);
	Num(TEXT("sprintForwardMin"), SprintForwardMin, 0, 1);
	Num(TEXT("stickDeadZone"), StickDeadZone, 0, 0.6f);
	Num(TEXT("stickYawDegPerSecond"), StickYawDegPerSecond, 10, 1000);
	Num(TEXT("stickPitchDegPerSecond"), StickPitchDegPerSecond, 10, 1000);
	Num(TEXT("stickExponent"), StickExponent, 1, 4);
	Num(TEXT("pitchLimit"), PitchLimit, 30, 89.5f);
	Num(TEXT("waterSurfaceZ"), WaterSurfaceZ, -1000, 1000);
	Num(TEXT("killZ"), KillZ, -100000, 0);
	Num(TEXT("spawnYaw"), SpawnYaw, -360, 360);
	Num(TEXT("stepIntervalWalk"), StepIntervalWalk, 0.1f, 3);
	Num(TEXT("stepIntervalSprint"), StepIntervalSprint, 0.1f, 3);
	Num(TEXT("stepIntervalCrouch"), StepIntervalCrouch, 0.1f, 3);
	const TArray<TSharedPtr<FJsonValue>>* SpawnArr = nullptr;
	if (Root->TryGetArrayField(TEXT("spawn"), SpawnArr))
	{
		if (SpawnArr->Num() != 3)
		{
			OutError = TEXT("Data/firstperson.json: spawn must be [x, y, z] in centimetres.");
			return false;
		}
		Spawn = FVector((*SpawnArr)[0]->AsNumber(), (*SpawnArr)[1]->AsNumber(), (*SpawnArr)[2]->AsNumber());
	}
	if (bOk && (CrouchHeight > StandHeight || CrouchEyeHeight > StandEyeHeight || StandEyeHeight > StandHeight || CrouchEyeHeight > CrouchHeight || CapsuleRadius * 2.0f > CrouchHeight))
	{
		OutError = TEXT("Data/firstperson.json: heights must satisfy crouch <= stand, eyes inside the capsule, and capsule diameter <= crouch height.");
		bOk = false;
	}
	return bOk;
}

FString FEHFirstPersonTuning::Describe() const
{
	return FString::Printf(TEXT("walk=%.0f sprint=%.0f crouch=%.0f accel=%.0f brake=%.0f friction=%.1f air=%.2f jump=%.0f buffer=%.2f gravity=%.2f step=%.0f floor=%.0f capsule=r%.0f/h%.0f/c%.0f eyes=%.0f/%.0f stamina=%.0f sprint_s=%.1f recover=%.0f/s after %.1fs restart=%.0f deadzone=%.2f stick=%.0f/%.0f exp=%.1f pitch=%.0f water_z=%.1f"),
		WalkSpeed, SprintSpeed, CrouchSpeed, Acceleration, BrakingDeceleration, GroundFriction, AirControl, JumpVelocity, JumpBufferSeconds, GravityScale, StepHeight,
		WalkableFloorDegrees, CapsuleRadius, StandHeight, CrouchHeight, StandEyeHeight, CrouchEyeHeight, StaminaMax, SprintSecondsFromFull, StaminaRecoverPerSecond,
		StaminaRecoverDelay, SprintRestartStamina, StickDeadZone, StickYawDegPerSecond, StickPitchDegPerSecond, StickExponent, PitchLimit, WaterSurfaceZ);
}

AEHPlayerCharacter::AEHPlayerCharacter(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	PrimaryActorTick.bCanEverTick = true;
	bUseControllerRotationYaw = true;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;
	AutoPossessPlayer = EAutoReceiveInput::Disabled;

	CameraComp = CreateDefaultSubobject<UCameraComponent>(TEXT("FirstPersonCamera"));
	CameraComp->SetupAttachment(GetCapsuleComponent());
	CameraComp->bUsePawnControlRotation = true;
	CameraComp->SetConstraintAspectRatio(false);

	// The hidden body: never drawn to its own player's camera, still in shadows (and in other views).
	Body = GetMesh();
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->SetCastShadow(true);
	Body->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::WorldSpaceRepresentation);
	Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;

	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->bOrientRotationToMovement = false;
	Move->bUseControllerDesiredRotation = false;
	Move->GetNavAgentPropertiesRef().bCanCrouch = true;
	Move->bCanWalkOffLedgesWhenCrouching = true;
	Move->bMaintainHorizontalGroundVelocity = true;
	JumpMaxHoldTime = 0.0f;
	JumpMaxCount = 1;
}

void AEHPlayerCharacter::BeginPlay()
{
	Super::BeginPlay();
	// Placeholder body: the 2.5D slice's Wren test model with its fighting-stance idle and walk, used only as a stand-in.
	// Nothing here is final art.
	if (USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/Wren/SK_Wren.SK_Wren"), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		Body->SetSkeletalMesh(Mesh);
		Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		BodyIdle = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Characters/Wren/Anims/A_Wren_Idle.A_Wren_Idle"), nullptr, LOAD_NoWarn | LOAD_Quiet);
		BodyWalk = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Characters/Wren/Anims/A_Wren_WalkF.A_Wren_WalkF"), nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (BodyIdle)
		{
			Body->PlayAnimation(BodyIdle, true);
		}
	}
	ApplyTuning(Tuning);
	ResetToStart();
}

FVector AEHPlayerCharacter::FeetLocation() const
{
	return GetActorLocation() - FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
}

bool AEHPlayerCharacter::HasBodyPlaceholder() const
{
	return Body && Body->GetSkeletalMeshAsset() != nullptr;
}

void AEHPlayerCharacter::ApplyTuning(const FEHFirstPersonTuning& InTuning)
{
	Tuning = InTuning;
	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->MaxWalkSpeed = Tuning.WalkSpeed;
	Move->MaxWalkSpeedCrouched = Tuning.CrouchSpeed;
	Move->MaxAcceleration = Tuning.Acceleration;
	Move->BrakingDecelerationWalking = Tuning.BrakingDeceleration;
	Move->GroundFriction = Tuning.GroundFriction;
	Move->AirControl = Tuning.AirControl;
	Move->JumpZVelocity = Tuning.JumpVelocity;
	Move->GravityScale = Tuning.GravityScale;
	Move->MaxStepHeight = Tuning.StepHeight;
	Move->SetWalkableFloorAngle(Tuning.WalkableFloorDegrees);
	Move->SetCrouchedHalfHeight(Tuning.CrouchHeight * 0.5f);
	if (!bIsCrouched)
	{
		GetCapsuleComponent()->SetCapsuleSize(Tuning.CapsuleRadius, Tuning.StandHeight * 0.5f);
	}
	Body->SetRelativeLocationAndRotation(FVector(0, 0, -Tuning.StandHeight * 0.5f), FRotator(0, -90, 0));
	BaseEyeHeight = Tuning.StandEyeHeight - Tuning.StandHeight * 0.5f;
	CrouchedEyeHeight = Tuning.CrouchEyeHeight - Tuning.CrouchHeight * 0.5f;
	StaminaValue = FMath::Min(StaminaValue, Tuning.StaminaMax);
}

void AEHPlayerCharacter::SetFieldOfView(float HorizontalDegrees)
{
	CameraComp->SetFieldOfView(HorizontalDegrees);
}

void AEHPlayerCharacter::SetBodyVisibleToSelf(bool bVisible)
{
	Body->SetFirstPersonPrimitiveType(bVisible ? EFirstPersonPrimitiveType::None : EFirstPersonPrimitiveType::WorldSpaceRepresentation);
	Body->SetOwnerNoSee(!bVisible);
}

void AEHPlayerCharacter::ResetToStart()
{
	UnCrouch();
	GetCharacterMovement()->bWantsToCrouch = false;
	StopJumping();
	GetCharacterMovement()->StopMovementImmediately();
	TeleportTo(Tuning.Spawn + FVector(0, 0, Tuning.StandHeight * 0.5f + 2.0f), FRotator(0, Tuning.SpawnYaw, 0), false, true);
	if (AController* C = GetController())
	{
		C->SetControlRotation(FRotator(0, Tuning.SpawnYaw, 0));
	}
	GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	StaminaValue = Tuning.StaminaMax;
	StaminaIdle = 10.0f;
	SinceDrain = 10.0f;
	bSprinting = false;
	bExhausted = false;
	bWantCrouch = false;
	JumpBuffer = 0.0f;
	EyeZ = Tuning.StandEyeHeight;
	StepTimer = 0.0f;
	bWasFalling = false;
	Emit(FEHFirstPersonEvent::EKind::Reset, 0.0f);
}

void AEHPlayerCharacter::Emit(FEHFirstPersonEvent::EKind Kind, float Strength)
{
	FEHFirstPersonEvent E;
	E.Kind = Kind;
	E.Location = FeetLocation();
	E.WaterDepth = WaterDepth;
	E.Strength = FMath::Clamp(Strength, 0.0f, 1.0f);
	Events.Add(E);
}

void AEHPlayerCharacter::ApplyInput(const FEHFirstPersonInput& In, float DeltaSeconds)
{
	AController* C = GetController();
	if (C == nullptr || DeltaSeconds <= 0.0f)
	{
		return;
	}
	// Look: degrees straight onto the control rotation (no engine input scales), pitch clamped short of vertical.
	FRotator R = C->GetControlRotation();
	R.Pitch = FMath::Clamp(FRotator::NormalizeAxis(R.Pitch) + In.Look.Y, -Tuning.PitchLimit, Tuning.PitchLimit);
	R.Yaw = FRotator::NormalizeAxis(R.Yaw + In.Look.X);
	R.Roll = 0.0f;
	C->SetControlRotation(R);

	UCharacterMovementComponent* Move = GetCharacterMovement();
	const bool bGrounded = Move->IsMovingOnGround();

	// Posture first: crouching wins over sprinting, and a crouch that is blocked overhead stays down until clear
	// (the movement component retries standing every tick).
	bWantCrouch = In.bCrouch;
	if (bWantCrouch && !bIsCrouched)
	{
		Crouch();
	}
	else if (!bWantCrouch && (bIsCrouched || Move->bWantsToCrouch))
	{
		UnCrouch();
	}

	// Sprint: forward, on the ground, standing, with Stamina; an emptied bar must refill to the restart level.
	const FVector2D MoveIn = In.Move.GetSafeNormal() * FMath::Min(In.Move.Size(), 1.0f);
	if (bExhausted && StaminaValue >= Tuning.SprintRestartStamina)
	{
		bExhausted = false;
	}
	const bool bCanSprint = In.bSprint && !bWantCrouch && !bIsCrouched && MoveIn.Y >= Tuning.SprintForwardMin && !bExhausted && StaminaValue > 0.0f;
	// Keep sprinting through a jump; only start one on the ground.
	bSprinting = bCanSprint && (bGrounded || bSprinting);
	Move->MaxWalkSpeed = bSprinting ? Tuning.SprintSpeed : Tuning.WalkSpeed;

	const FRotator YawOnly(0.0f, R.Yaw, 0.0f);
	const FVector Forward = YawOnly.Vector();
	const FVector Right = FRotationMatrix(YawOnly).GetUnitAxis(EAxis::Y);
	AddMovementInput(Forward, MoveIn.Y);
	AddMovementInput(Right, MoveIn.X);

	// Stamina drains while actually running fast, and recovers after a pause.
	const float Speed2D = GetVelocity().Size2D();
	const float Before = StaminaValue;
	if (bSprinting && Speed2D > Tuning.WalkSpeed * 0.5f && bGrounded)
	{
		StaminaValue = FMath::Max(0.0f, StaminaValue - Tuning.StaminaMax / Tuning.SprintSecondsFromFull * DeltaSeconds);
		SinceDrain = 0.0f;
		if (StaminaValue <= 0.0f)
		{
			bExhausted = true;
			bSprinting = false;
		}
	}
	else
	{
		SinceDrain += DeltaSeconds;
		if (SinceDrain >= Tuning.StaminaRecoverDelay)
		{
			StaminaValue = FMath::Min(Tuning.StaminaMax, StaminaValue + Tuning.StaminaRecoverPerSecond * DeltaSeconds);
		}
	}
	StaminaIdle = StaminaValue != Before ? 0.0f : StaminaIdle + DeltaSeconds;

	// Jump: a press shortly before landing still counts; a jump from a crouch stands up first.
	if (In.bJumpPressed)
	{
		JumpBuffer = FMath::Max(Tuning.JumpBufferSeconds, DeltaSeconds);
	}
	if (bPressedJump)
	{
		StopJumping();
	}
	if (JumpBuffer > 0.0f)
	{
		if (bIsCrouched)
		{
			UnCrouch();
		}
		else if (CanJump())
		{
			Jump();
			JumpBuffer = 0.0f;
			Emit(FEHFirstPersonEvent::EKind::Jump, Speed2D / FMath::Max(1.0f, Tuning.SprintSpeed));
		}
		JumpBuffer -= DeltaSeconds;
	}

	// Footsteps.
	if (bGrounded && Speed2D > 40.0f)
	{
		const float Interval = bIsCrouched ? Tuning.StepIntervalCrouch : (Speed2D > Tuning.WalkSpeed * 1.2f ? Tuning.StepIntervalSprint : Tuning.StepIntervalWalk);
		StepTimer += DeltaSeconds * FMath::Clamp(Speed2D / (bIsCrouched ? Tuning.CrouchSpeed : (bSprinting ? Tuning.SprintSpeed : Tuning.WalkSpeed)), 0.4f, 1.2f);
		if (StepTimer >= Interval)
		{
			StepTimer -= Interval;
			Emit(FEHFirstPersonEvent::EKind::Step, Speed2D / FMath::Max(1.0f, Tuning.SprintSpeed));
		}
	}
	else if (bGrounded)
	{
		StepTimer = 0.0f;
	}
}

void AEHPlayerCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	UpdateWater();
	UpdateCamera(DeltaSeconds);
	UpdateBody();
	const bool bFalling = GetCharacterMovement()->IsFalling();
	if (bFalling && !bWasFalling)
	{
		FallStartZ = GetActorLocation().Z;
	}
	bWasFalling = bFalling;
	if (GetActorLocation().Z < Tuning.KillZ)
	{
		// Out of the map (should not be reachable): back to the start rather than falling forever.
		ResetToStart();
	}
}

void AEHPlayerCharacter::Landed(const FHitResult& Hit)
{
	Super::Landed(Hit);
	const float Drop = FMath::Max(0.0f, FallStartZ - GetActorLocation().Z);
	UpdateWater();
	Emit(FEHFirstPersonEvent::EKind::Land, FMath::Clamp((Drop + 40.0f) / 200.0f, 0.2f, 1.0f));
	StepTimer = 0.0f;
}

void AEHPlayerCharacter::OnStartCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust)
{
	Super::OnStartCrouch(HalfHeightAdjust, ScaledHalfHeightAdjust);
	// The engine moves the mesh with the shrunk capsule; the eyes are blended in UpdateCamera instead of snapping.
	Body->SetRelativeLocation(FVector(0, 0, -Tuning.CrouchHeight * 0.5f));
}

void AEHPlayerCharacter::OnEndCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust)
{
	Super::OnEndCrouch(HalfHeightAdjust, ScaledHalfHeightAdjust);
	Body->SetRelativeLocation(FVector(0, 0, -Tuning.StandHeight * 0.5f));
}

void AEHPlayerCharacter::UpdateWater()
{
	// The Chapel's water is one sheet at WaterSurfaceZ over the floor: depth is the surface minus the floor under the feet.
	const UCharacterMovementComponent* Move = GetCharacterMovement();
	const FVector Feet = FeetLocation();
	float FloorZ = Feet.Z;
	if (Move->IsMovingOnGround() && Move->CurrentFloor.bBlockingHit)
	{
		FloorZ = Move->CurrentFloor.HitResult.ImpactPoint.Z;
	}
	WaterDepth = Feet.Z <= Tuning.WaterSurfaceZ + 2.0f ? FMath::Max(0.0f, Tuning.WaterSurfaceZ - FloorZ) : 0.0f;
}

void AEHPlayerCharacter::UpdateCamera(float DeltaSeconds)
{
	const float Target = bIsCrouched ? Tuning.CrouchEyeHeight : Tuning.StandEyeHeight;
	const float Alpha = Tuning.EyeBlendSeconds > 0.0f ? 1.0f - FMath::Exp(-DeltaSeconds / Tuning.EyeBlendSeconds) : 1.0f;
	EyeZ = FMath::Lerp(EyeZ, Target, Alpha);
	if (FMath::Abs(EyeZ - Target) < 0.05f)
	{
		EyeZ = Target;
	}
	const float HalfHeight = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	CameraComp->SetRelativeLocation(FVector(0, 0, EyeZ - HalfHeight));
}

void AEHPlayerCharacter::UpdateBody()
{
	if (!HasBodyPlaceholder())
	{
		return;
	}
	const bool bWalking = GetVelocity().Size2D() > 40.0f;
	if (bWalking != bBodyWalking)
	{
		bBodyWalking = bWalking;
		UAnimSequence* Anim = bWalking ? BodyWalk : BodyIdle;
		if (Anim)
		{
			Body->PlayAnimation(Anim, true);
		}
	}
	if (bWalking && BodyWalk)
	{
		Body->SetPlayRate(FMath::Clamp(GetVelocity().Size2D() / FMath::Max(1.0f, Tuning.WalkSpeed), 0.5f, 1.8f));
	}
	else
	{
		Body->SetPlayRate(1.0f);
	}
}
