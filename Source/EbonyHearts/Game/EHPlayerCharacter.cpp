#include "EHPlayerCharacter.h"

#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "EHViewArms.h"
#include "EHMagic.h"
#include "EHWolf.h"
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
	Num(TEXT("playerHealth"), PlayerHealth, 1, 10000);
	const TSharedPtr<FJsonObject>* FistsObj = nullptr;
	if (Root->TryGetObjectField(TEXT("fists"), FistsObj) && !Fists.Load(*FistsObj, OutError))
	{
		return false;
	}
	const TSharedPtr<FJsonObject>* WolfObj = nullptr;
	if (Root->TryGetObjectField(TEXT("wolf"), WolfObj) && !Wolf.Load(*WolfObj, OutError))
	{
		return false;
	}
	const TSharedPtr<FJsonObject>* ChapelObj = nullptr;
	if (Root->TryGetObjectField(TEXT("chapel"), ChapelObj) && !Chapel.Load(*ChapelObj, OutError))
	{
		return false;
	}
	const TSharedPtr<FJsonObject>* DummyObj = nullptr;
	if (Root->TryGetObjectField(TEXT("dummy"), DummyObj) && !Dummy.Load(*DummyObj, OutError))
	{
		return false;
	}
	// The seven stats: Health and Stamina default to the movement milestone's playerHealth and staminaMax; stats.health
	// and stats.stamina, when given, set both.
	Magic.Stats.Health = PlayerHealth;
	Magic.Stats.Stamina = StaminaMax;
	if (!Magic.Load(Root, OutError))
	{
		return false;
	}
	PlayerHealth = Magic.Stats.Health;
	StaminaMax = Magic.Stats.Stamina;
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
		StaminaRecoverDelay, SprintRestartStamina, StickDeadZone, StickYawDegPerSecond, StickPitchDegPerSecond, StickExponent, PitchLimit, WaterSurfaceZ)
		+ FString::Printf(TEXT(" health=%.0f fists: %s; magic: %s; wolf: %s"), PlayerHealth, *Fists.Describe(), *Magic.Describe(), *Wolf.Describe());
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
	// Arms are drawn with their own field of view, pulled toward the eye so they never reach into walls.
	CameraComp->SetEnableFirstPersonFieldOfView(true);
	CameraComp->SetFirstPersonFieldOfView(72.0f);
	CameraComp->SetEnableFirstPersonScale(true);
	// 0.6 keeps the nearest fist (about 20 cm from the eyes) beyond the 10 cm near clip plane.
	CameraComp->SetFirstPersonScale(0.6f);
	Arms = CreateDefaultSubobject<UEHViewArms>(TEXT("ViewArms"));
	Arms->SetupAttachment(CameraComp);

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
	Arms->Build();
	// A spell starts only with the Qhi for it (and, for the wall, room to raise it); the cost is taken as it starts.
	Fists.SetGate([this](EEHFistAction Next) { return !EHIsSpell(Next) || CanCast(Next); });
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
	Fists.Configure(Tuning.Fists);
	Stats = Tuning.Magic.Stats;
	HealthValue = FMath::Min(HealthValue, Tuning.PlayerHealth);
	QhiValue = FMath::Min(QhiValue, Stats.Qhi);
}

void AEHPlayerCharacter::SetStats(const FEHPlayerStats& InStats)
{
	Stats = InStats;
	Tuning.PlayerHealth = Stats.Health;
	Tuning.StaminaMax = Stats.Stamina;
	HealthValue = FMath::Min(HealthValue, Stats.Health);
	StaminaValue = FMath::Min(StaminaValue, Stats.Stamina);
	QhiValue = FMath::Min(QhiValue, Stats.Qhi);
}

void AEHPlayerCharacter::AddQhi(float Amount)
{
	const float Before = QhiValue;
	QhiValue = FMath::Clamp(QhiValue + Amount, 0.0f, Stats.Qhi);
	if (QhiValue != Before)
	{
		QhiIdle = 0.0f;
	}
}

bool AEHPlayerCharacter::CanCast(EEHFistAction Spell) const
{
	const float Cost = Spell == EEHFistAction::Fireball ? Tuning.Magic.FireballCost : Tuning.Magic.IceWallCost;
	if (QhiValue + 0.001f < Cost)
	{
		return false;
	}
	FVector Base, Facing;
	return Spell != EEHFistAction::IceWall || FindIceWallPlacement(Base, Facing);
}

bool AEHPlayerCharacter::FindIceWallPlacement(FVector& OutBase, FVector& OutFacing) const
{
	// Straight ahead along the view's heading, at waist height: the wall stops short of anything solid in the way
	// (characters are not in the way: a wall rising under one pushes it aside), and needs floor under it.
	const FEHMagicTuning& M = Tuning.Magic;
	FVector Forward = GetControlRotation().Vector();
	Forward.Z = 0.0f;
	Forward = Forward.GetSafeNormal(UE_SMALL_NUMBER, GetActorForwardVector());
	const FVector Waist = GetActorLocation();
	FCollisionQueryParams Params(TEXT("EHIceWallRoom"), false, this);
	FCollisionObjectQueryParams Solid;
	Solid.AddObjectTypesToQuery(ECC_WorldStatic);
	Solid.AddObjectTypesToQuery(ECC_WorldDynamic);
	float Dist = M.IceWallDistance;
	FHitResult Hit;
	const float Probe = M.IceWallDistance + M.IceWallThickness * 0.5f + 10.0f;
	if (GetWorld()->SweepSingleByObjectType(Hit, Waist, Waist + Forward * Probe, FQuat::Identity, Solid, FCollisionShape::MakeSphere(20.0f), Params))
	{
		Dist = FMath::Min(Dist, Hit.Distance - M.IceWallThickness * 0.5f - 10.0f);
	}
	if (Dist < M.IceWallMinDistance)
	{
		return false;
	}
	const FVector At = Waist + Forward * Dist;
	FHitResult Floor;
	FCollisionObjectQueryParams Ground(ECC_WorldStatic);
	if (!GetWorld()->LineTraceSingleByObjectType(Floor, At + FVector(0, 0, 40.0f), At - FVector(0, 0, 400.0f), Ground, Params))
	{
		return false;
	}
	OutBase = Floor.ImpactPoint;
	OutFacing = Forward;
	return true;
}

void AEHPlayerCharacter::ReleaseSpell(EEHFistAction Spell)
{
	FEHFirstPersonEvent Out;
	Out.Action = Spell;
	if (Spell == EEHFistAction::Fireball)
	{
		// From the left hand toward whatever the view's centre rests on, so the ball lands where the player aims.
		const FVector Eye = CameraComp->GetComponentLocation();
		const FVector Aim = CameraComp->GetForwardVector();
		const FVector Origin = Eye + Aim * 45.0f - CameraComp->GetRightVector() * 12.0f - CameraComp->GetUpVector() * 14.0f;
		FHitResult Hit;
		FCollisionQueryParams Params(TEXT("EHFireballAim"), false, this);
		FVector Target = Eye + Aim * Tuning.Magic.FireballRange;
		if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, Target, ECC_Visibility, Params) && Hit.Distance > 120.0f)
		{
			Target = Hit.ImpactPoint;
		}
		Out.Kind = FEHFirstPersonEvent::EKind::Cast;
		Out.Location = Origin;
		Out.Direction = (Target - Origin).GetSafeNormal(UE_SMALL_NUMBER, Aim);
		Events.Add(Out);
		++CastCount;
		return;
	}
	FVector Base, Facing;
	if (!FindIceWallPlacement(Base, Facing))
	{
		// The player turned into a pier during the cast: no wall, and the Qhi comes back.
		AddQhi(Tuning.Magic.IceWallCost);
		Out.Kind = FEHFirstPersonEvent::EKind::Fizzle;
		Out.Location = GetActorLocation();
		Events.Add(Out);
		return;
	}
	Out.Kind = FEHFirstPersonEvent::EKind::Cast;
	Out.Location = Base;
	Out.Direction = Facing;
	Events.Add(Out);
	++CastCount;
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
	Fists.Reset();
	FistAccum = 0.0f;
	HealthValue = Tuning.PlayerHealth;
	SinceHurt = 100.0f;
	QhiValue = Stats.Qhi;
	QhiIdle = 10.0f;
	SinceCast = 10.0f;
	SinceRefused = 10.0f;
	KickPitch = KickRoll = KickForward = 0.0f;
	if (Arms)
	{
		Arms->SnapHidden();
	}
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

	// Techniques: presses and the guard go to the fixed-step state; it runs before movement reads its speed limit.
	Fists.SetBlockHeld(In.bBlock);
	if (In.FistPress != EEHFistAction::None)
	{
		Fists.Press(In.FistPress);
	}
	FistAccum = FMath::Min(FistAccum + DeltaSeconds, 0.25f);
	while (FistAccum >= 1.0f / 60.0f)
	{
		FistAccum -= 1.0f / 60.0f;
		StepFists();
	}
	const bool bBusy = Fists.Action() != EEHFistAction::None || Fists.IsBlockHeld();

	// Sprint: forward, on the ground, standing, with Stamina; an emptied bar must refill to the restart level.
	const FVector2D MoveIn = In.Move.GetSafeNormal() * FMath::Min(In.Move.Size(), 1.0f);
	if (bExhausted && StaminaValue >= Tuning.SprintRestartStamina)
	{
		bExhausted = false;
	}
	const bool bCanSprint = In.bSprint && !bBusy && !bWantCrouch && !bIsCrouched && MoveIn.Y >= Tuning.SprintForwardMin && !bExhausted && StaminaValue > 0.0f;
	// Keep sprinting through a jump; only start one on the ground.
	bSprinting = bCanSprint && (bGrounded || bSprinting);
	Move->MaxWalkSpeed = (bSprinting ? Tuning.SprintSpeed : Tuning.WalkSpeed) * Fists.MoveScale();
	Move->MaxWalkSpeedCrouched = Tuning.CrouchSpeed * Fists.MoveScale();

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
			StaminaValue = FMath::Min(Tuning.StaminaMax, StaminaValue + Tuning.StaminaRecoverPerSecond * Tuning.Magic.StaminaScale(Stats) * DeltaSeconds);
		}
	}
	StaminaIdle = StaminaValue != Before ? 0.0f : StaminaIdle + DeltaSeconds;

	// Qhi flows back at the rate Intelligence and Faith set, shortly after the last cast.
	SinceCast += DeltaSeconds;
	SinceRefused += DeltaSeconds;
	QhiIdle += DeltaSeconds;
	if (SinceCast >= Tuning.Magic.QhiRegenDelay && QhiValue < Stats.Qhi)
	{
		AddQhi(Tuning.Magic.QhiRegen(Stats) * DeltaSeconds);
	}

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

void AEHPlayerCharacter::StepFists()
{
	TArray<FEHFistEvent> FistEvents;
	Fists.Step(FistEvents);
	for (const FEHFistEvent& E : FistEvents)
	{
		if (E.Kind == FEHFistEvent::EKind::Start)
		{
			FEHFirstPersonEvent Out;
			Out.Kind = EHIsSpell(E.Action) ? FEHFirstPersonEvent::EKind::CastStart : FEHFirstPersonEvent::EKind::Swing;
			Out.Action = E.Action;
			Out.Location = CameraComp->GetComponentLocation();
			Events.Add(Out);
			if (EHIsSpell(E.Action))
			{
				// One payment per accepted cast, as it starts.
				AddQhi(-(E.Action == EEHFistAction::Fireball ? Tuning.Magic.FireballCost : Tuning.Magic.IceWallCost));
				SinceCast = 0.0f;
			}
		}
		else if (E.Kind == FEHFistEvent::EKind::Refused)
		{
			FEHFirstPersonEvent Out;
			Out.Kind = FEHFirstPersonEvent::EKind::Refused;
			Out.Action = E.Action;
			Out.Location = CameraComp->GetComponentLocation();
			Out.bNoQhi = QhiValue + 0.001f < (E.Action == EEHFistAction::Fireball ? Tuning.Magic.FireballCost : Tuning.Magic.IceWallCost);
			Events.Add(Out);
			SinceRefused = 0.0f;
			++RefusedCount;
		}
		else if (E.Kind == FEHFistEvent::EKind::Active && EHIsSpell(E.Action) && E.Action == Fists.Action())
		{
			ReleaseSpell(E.Action);
		}
		// A technique that chained into the next one in this step has handed over; its frame is not checked again.
		else if (E.Kind == FEHFistEvent::EKind::Active && E.Action == Fists.Action() && !Fists.HasConnected())
		{
			CheckContact(E.Action);
		}
	}
}

void AEHPlayerCharacter::CheckContact(EEHFistAction Action)
{
	// The strike reaches along the aim from the eyes: a sphere for the target, a line for walls in between. Martial
	// Prowess scales its damage.
	FEHStrikeDef D = Tuning.Fists.Def(Action);
	const float Physical = Tuning.Magic.PhysicalScale(Stats);
	D.Damage *= Physical;
	const FVector Eye = CameraComp->GetComponentLocation();
	const FVector Aim = CameraComp->GetForwardVector();
	const FVector End = Eye + Aim * D.Reach;
	FCollisionQueryParams Params(TEXT("EHFist"), false, this);
	TArray<FHitResult> Hits;
	GetWorld()->SweepMultiByObjectType(Hits, Eye + Aim * 10.0f, End, FQuat::Identity, FCollisionObjectQueryParams(ECC_Pawn), FCollisionShape::MakeSphere(D.Radius), Params);
	// The nearest thing that can be struck: the training dummy or a wolf.
	AActor* Target = nullptr;
	FHitResult TargetHit;
	for (const FHitResult& H : Hits)
	{
		const bool bStrikeable = Cast<AEHTrainingDummy>(H.GetActor()) || (Cast<AEHWolf>(H.GetActor()) && !Cast<AEHWolf>(H.GetActor())->IsDead());
		if (bStrikeable && (Target == nullptr || H.Distance < TargetHit.Distance))
		{
			Target = H.GetActor();
			TargetHit = H;
		}
	}
	if (Target == nullptr)
	{
		// A wolf stands below the line of a punch even when the player looks down at it: a second sweep at its body's
		// height, straight ahead along the view's heading, finds one within the same reach.
		FVector Flat = Aim;
		Flat.Z = 0.0f;
		Flat = Flat.GetSafeNormal();
		const FVector Low = FeetLocation() + FVector(0, 0, 55.0f);
		TArray<FHitResult> LowHits;
		GetWorld()->SweepMultiByObjectType(LowHits, Low + Flat * 10.0f, Low + Flat * (D.Reach + 15.0f), FQuat::Identity, FCollisionObjectQueryParams(ECC_Pawn),
			FCollisionShape::MakeSphere(D.Radius + 8.0f), Params);
		for (const FHitResult& H : LowHits)
		{
			if (AEHWolf* W = Cast<AEHWolf>(H.GetActor()); W && !W->IsDead() && (Target == nullptr || H.Distance < TargetHit.Distance))
			{
				Target = W;
				TargetHit = H;
			}
		}
	}
	FHitResult Wall;
	const bool bWall = GetWorld()->LineTraceSingleByChannel(Wall, Eye, End, ECC_Visibility, Params) && Cast<AEHTrainingDummy>(Wall.GetActor()) == nullptr
		&& Cast<AEHWolf>(Wall.GetActor()) == nullptr;
	if (AEHWolf* Wolf = Cast<AEHWolf>(Target); Wolf && !(bWall && Wall.Distance + 5.0f < TargetHit.Distance))
	{
		const FVector At = TargetHit.ImpactPoint.IsNearlyZero() ? Wolf->GetActorLocation() : FVector(TargetHit.ImpactPoint);
		const FEHWolfHit R = Wolf->ReceivePlayerHit(D.Damage, Eye, At, Action == EEHFistAction::Straight);
		Fists.MarkConnected();
		Fists.OnContact();
		if (R.bHarmed)
		{
			AddQhi(Tuning.Magic.QhiPerStrike);
		}
		Kick(-0.6f, 2.0f, Action == EEHFistAction::Straight ? 1.0f : -0.5f);
		FEHFirstPersonEvent Out;
		Out.Kind = FEHFirstPersonEvent::EKind::Contact;
		Out.Action = Action;
		Out.Location = At;
		Out.Damage = R.Damage;
		Out.Target = Wolf;
		Out.Reflected = R.Reflected;
		Out.bKilled = R.bKilled;
		Events.Add(Out);
		if (R.Reflected > 0.0f)
		{
			// Hero of Humanity: the guardians cannot be harmed by them; the blow lands on the player.
			ReceiveStrike(R.Reflected, At, true);
		}
	}
	else if (AEHTrainingDummy* Dummy = Cast<AEHTrainingDummy>(Target); Dummy && !(bWall && Wall.Distance + 5.0f < TargetHit.Distance))
	{
		AEHTrainingDummy* const DummyTarget = Dummy;
		const FVector At = TargetHit.ImpactPoint.IsNearlyZero() ? DummyTarget->GetActorLocation() : FVector(TargetHit.ImpactPoint);
		const float HandSide = Action == EEHFistAction::Jab ? -1.0f : 1.0f;
		const FEHDummyHit R = DummyTarget->ReceiveHit(Action, D, Eye, At, HandSide);
		Fists.MarkConnected();
		Fists.OnContact();
		if (!R.bBlocked)
		{
			AddQhi(Tuning.Magic.QhiPerStrike);   // a landed technique feeds the pool
		}
		// The view follows the blow: a small push forward into the target and a roll with the punching hand.
		const float Weight = R.bBlocked ? 0.6f : 1.0f;
		if (Action == EEHFistAction::Straight)
		{
			Kick(-0.8f * Weight, 3.0f * Weight, 1.0f * Weight);
		}
		else
		{
			Kick(-0.4f * Weight, 1.6f * Weight, -0.5f * Weight);
		}
		FEHFirstPersonEvent Out;
		Out.Kind = FEHFirstPersonEvent::EKind::Contact;
		Out.Action = Action;
		Out.Location = At;
		Out.Damage = R.Damage;
		Out.bBlocked = R.bBlocked;
		Out.bBody = R.bBody;
		Out.Target = DummyTarget;
		Events.Add(Out);
	}
	else if (bWall)
	{
		// Knuckles on stone: the technique stops connecting for the rest of its active frames, with a short jar.
		Fists.MarkConnected();
		Fists.OnContact(2);
		Kick(-0.25f, -1.0f, 0.0f);
		FEHFirstPersonEvent Out;
		Out.Kind = FEHFirstPersonEvent::EKind::Wall;
		Out.Action = Action;
		Out.Location = Wall.ImpactPoint;
		if (AEHIceWall* Ice = Cast<AEHIceWall>(Wall.GetActor()))
		{
			// Ice gives way to enough blows.
			Out.bIce = true;
			Out.bShattered = Ice->Damage(D.Damage);
			Out.Damage = D.Damage;
		}
		Events.Add(Out);
	}
}

float AEHPlayerCharacter::ReceiveStrike(float Damage, const FVector& From, bool bOwnBlow)
{
	if (!bOwnBlow && Absorber && Absorber(Damage, From))
	{
		// Taken by a guardian wolf instead.
		FEHFirstPersonEvent Out;
		Out.Kind = FEHFirstPersonEvent::EKind::Guarded;
		Out.Location = CameraComp->GetComponentLocation() + CameraComp->GetForwardVector() * 30.0f;
		Out.bAbsorbed = true;
		Events.Add(Out);
		return 0.0f;
	}
	// The guard covers the front of the view; anything else lands in full.
	FVector ToAttacker = From - GetActorLocation();
	ToAttacker.Z = 0.0f;
	FVector Facing = CameraComp->GetForwardVector();
	Facing.Z = 0.0f;
	const float Angle = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(ToAttacker.GetSafeNormal(), Facing.GetSafeNormal()), -1.0f, 1.0f)));
	const bool bGuarded = !bOwnBlow && Fists.IsGuarding() && Angle <= Tuning.Fists.BlockAngle;
	const float Taken = bGuarded ? Damage * (1.0f - Tuning.Fists.BlockReduction) : Damage;
	HealthValue = FMath::Max(0.0f, HealthValue - Taken);
	SinceHurt = 0.0f;
	Kick(bGuarded ? 0.6f : 1.8f, bGuarded ? -1.0f : -3.0f, FMath::FRandRange(-1.2f, 1.2f) * (bGuarded ? 0.3f : 1.0f));
	FEHFirstPersonEvent Out;
	Out.Kind = bGuarded ? FEHFirstPersonEvent::EKind::Guarded : FEHFirstPersonEvent::EKind::Hurt;
	Out.Location = CameraComp->GetComponentLocation() + CameraComp->GetForwardVector() * 30.0f;
	Out.Damage = Taken;
	Out.bBlocked = bGuarded;
	Events.Add(Out);
	if (HealthValue <= 0.0f)
	{
		FEHFirstPersonEvent DeathEvent;
		DeathEvent.Kind = FEHFirstPersonEvent::EKind::Died;
		DeathEvent.Location = FeetLocation();
		Events.Add(DeathEvent);
	}
	return Taken;
}

void AEHPlayerCharacter::Kick(float PitchDegrees, float ForwardCm, float RollDegrees)
{
	KickPitch = FMath::Clamp(KickPitch + PitchDegrees * ShakeScale, -3.0f, 3.0f);
	KickForward = FMath::Clamp(KickForward + ForwardCm * ShakeScale, -6.0f, 6.0f);
	KickRoll = FMath::Clamp(KickRoll + RollDegrees * ShakeScale, -3.0f, 3.0f);
}

void AEHPlayerCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	SinceHurt += DeltaSeconds;
	UpdateWater();
	UpdateCamera(DeltaSeconds);
	// The kick tilts the view only (the aim, the control rotation, never moves) and settles exponentially, which
	// stays stable at any frame time.
	// While the fists are held in hitstop the kick holds too, so the freeze reads as one solid moment.
	if (!Fists.InHitstop())
	{
		KickPitch *= FMath::Exp(-DeltaSeconds / 0.07f);
		KickRoll *= FMath::Exp(-DeltaSeconds / 0.09f);
		KickForward *= FMath::Exp(-DeltaSeconds / 0.06f);
	}
	CameraComp->ClearAdditiveOffset();
	if (FMath::Abs(KickPitch) + FMath::Abs(KickRoll) + FMath::Abs(KickForward) > 0.001f)
	{
		CameraComp->AddAdditiveOffset(FTransform(FRotator(KickPitch, 0.0f, KickRoll), FVector(KickForward, 0.0f, 0.0f)), 0.0f);
	}
	if (Arms)
	{
		Arms->UpdateArms(Fists, FistAccum * 60.0f, DeltaSeconds);
	}
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
	// Depth is the water's surface over the feet minus the floor under them; dry where no sheet covers the feet.
	const UCharacterMovementComponent* Move = GetCharacterMovement();
	const FVector Feet = FeetLocation();
	float FloorZ = Feet.Z;
	if (Move->IsMovingOnGround() && Move->CurrentFloor.bBlockingHit)
	{
		FloorZ = Move->CurrentFloor.HitResult.ImpactPoint.Z;
	}
	float Surface = Tuning.WaterSurfaceZ;
	if (Water && !Water->SurfaceAt(Feet, Surface))
	{
		WaterDepth = 0.0f;
		return;
	}
	WaterDepth = Feet.Z <= Surface + 2.0f ? FMath::Max(0.0f, Surface - FloorZ) : 0.0f;
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
