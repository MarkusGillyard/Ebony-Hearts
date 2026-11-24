#include "EHWolf.h"

#include "AIController.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EHAlignment.h"
#include "EHPlayerCharacter.h"
#include "EHTrainingDummy.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Navigation/PathFollowingComponent.h"

namespace
{
constexpr float Step = 1.0f / 60.0f;
}

const TCHAR* EHWolfStateName(EEHWolfState S)
{
	switch (S)
	{
	case EEHWolfState::Calm: return TEXT("calm");
	case EEHWolfState::Disengage: return TEXT("disengaging");
	case EEHWolfState::Hostile: return TEXT("hostile");
	case EEHWolfState::BiteWindup: return TEXT("bite wind-up");
	case EEHWolfState::Bite: return TEXT("bite");
	case EEHWolfState::LungeWindup: return TEXT("lunge wind-up");
	case EEHWolfState::Lunge: return TEXT("lunge");
	case EEHWolfState::Recover: return TEXT("recovering");
	case EEHWolfState::Hitstun: return TEXT("hurt");
	case EEHWolfState::Protect: return TEXT("protecting");
	case EEHWolfState::Guarding: return TEXT("guarding the Chapel");
	default: return TEXT("dead");
	}
}

bool FEHWolfTuning::Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError)
{
	if (!Obj.IsValid())
	{
		return true;
	}
	bool bOk = true;
	auto Num = [&](const TCHAR* Name, float& Out, float Min, float Max) {
		double V = 0.0;
		if (!Obj->TryGetNumberField(Name, V))
		{
			return;
		}
		if (V < Min || V > Max)
		{
			OutError = FString::Printf(TEXT("Data/firstperson.json: wolf.%s = %g is outside %g..%g."), Name, V, Min, Max);
			bOk = false;
			return;
		}
		Out = static_cast<float>(V);
	};
	auto Int = [&](const TCHAR* Name, int32& Out, int32 Min, int32 Max) {
		float V = static_cast<float>(Out);
		Num(Name, V, static_cast<float>(Min), static_cast<float>(Max));
		Out = FMath::RoundToInt(V);
	};
	auto Vec = [&](const TCHAR* Name, FVector& Out) {
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (Obj->TryGetArrayField(Name, A) && A->Num() == 3)
		{
			Out = FVector((*A)[0]->AsNumber(), (*A)[1]->AsNumber(), (*A)[2]->AsNumber());
		}
	};
	Num(TEXT("health"), Health, 1, 10000);
	Vec(TEXT("home"), Home);
	Vec(TEXT("spawn"), Spawn);
	Num(TEXT("homeYaw"), HomeYaw, -360, 360);
	Num(TEXT("leaveLineY"), LeaveLineY, -5000, 5000);
	Num(TEXT("calmSeconds"), CalmSeconds, 0, 60);
	Num(TEXT("walkSpeed"), WalkSpeed, 50, 2000);
	Num(TEXT("runSpeed"), RunSpeed, 50, 3000);
	Num(TEXT("followDistance"), FollowDistance, 50, 2000);
	Num(TEXT("keepDistance"), KeepDistance, 50, 3000);
	Num(TEXT("threatRange"), ThreatRange, 50, 3000);
	Num(TEXT("disengageSeconds"), DisengageSeconds, 0, 30);
	Num(TEXT("disengageDistance"), DisengageDistance, 50, 3000);
	Num(TEXT("circleRadius"), CircleRadius, 50, 2000);
	Num(TEXT("biteRange"), BiteRange, 30, 1000);
	Num(TEXT("biteReach"), BiteReach, 30, 1000);
	Num(TEXT("biteDamage"), BiteDamage, 0, 1000);
	Int(TEXT("biteWindup"), BiteWindup, 1, 120);
	Int(TEXT("biteRecover"), BiteRecover, 0, 240);
	Num(TEXT("lungeMin"), LungeMin, 50, 3000);
	Num(TEXT("lungeMax"), LungeMax, 50, 3000);
	Num(TEXT("lungeSpeed"), LungeSpeed, 100, 5000);
	Num(TEXT("lungeDamage"), LungeDamage, 0, 1000);
	Int(TEXT("lungeWindup"), LungeWindup, 1, 120);
	Int(TEXT("lungeRecover"), LungeRecover, 0, 240);
	Int(TEXT("attackCooldown"), AttackCooldown, 0, 600);
	Int(TEXT("hitstun"), Hitstun, 0, 120);
	Num(TEXT("absorbRange"), AbsorbRange, 0, 5000);
	Num(TEXT("protectRange"), ProtectRange, 0, 5000);
	return bOk;
}

FString FEHWolfTuning::Describe() const
{
	return FString::Printf(TEXT("hp=%.0f home=(%.0f,%.0f) leave_y=%.0f calm=%.1fs walk=%.0f run=%.0f follow=%.0f keep=%.0f threat=%.0f disengage=%.1fs/%.0f circle=%.0f "
		"bite %.0f/%.0f dmg=%.0f %d+%d lunge %.0f..%.0f @%.0f dmg=%.0f %d+%d cooldown=%d stun=%d absorb=%.0f protect=%.0f"),
		Health, Home.X, Home.Y, LeaveLineY, CalmSeconds, WalkSpeed, RunSpeed, FollowDistance, KeepDistance, ThreatRange, DisengageSeconds, DisengageDistance,
		CircleRadius, BiteRange, BiteReach, BiteDamage, BiteWindup, BiteRecover, LungeMin, LungeMax, LungeSpeed, LungeDamage, LungeWindup, LungeRecover,
		AttackCooldown, Hitstun, AbsorbRange, ProtectRange);
}

AEHWolf::AEHWolf(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	PrimaryActorTick.bCanEverTick = true;
	AIControllerClass = AAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	GetCapsuleComponent()->InitCapsuleSize(40.0f, 48.0f);
	GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetMesh()->SetVisibility(false);
	bUseControllerRotationYaw = false;
	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->bOrientRotationToMovement = true;
	Move->RotationRate = FRotator(0, 540, 0);
	Move->MaxWalkSpeed = 260.0f;
	Move->MaxAcceleration = 2200.0f;
	Move->BrakingDecelerationWalking = 2400.0f;
	Move->bUseRVOAvoidance = false;
	Move->NavAgentProps.AgentRadius = 36.0f;
	Move->NavAgentProps.AgentHeight = 96.0f;

	Rig = CreateDefaultSubobject<USceneComponent>(TEXT("Rig"));
	Rig->SetupAttachment(GetCapsuleComponent());
	Rig->SetRelativeLocation(FVector(0, 0, -48.0f));
	auto Part = [this](const TCHAR* Name, USceneComponent* Parent) {
		UStaticMeshComponent* C = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		C->SetupAttachment(Parent);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCanEverAffectNavigation(false);
		C->SetCastShadow(true);
		return C;
	};
	Body = Part(TEXT("Body"), Rig);
	Head = Part(TEXT("Head"), Body);
	Tail = Part(TEXT("Tail"), Body);
	for (int32 i = 0; i < 4; ++i)
	{
		Legs[i] = Part(*FString::Printf(TEXT("Leg%d"), i), Body);
	}
	IceCuff = Part(TEXT("IceCuff"), Rig);
	IceCuff->SetCastShadow(false);
	IceCuff->SetVisibility(false);
	// Placeholder proportions: about 80 cm at the shoulder. Legs: front left, front right, back left, back right.
	Body->SetRelativeLocation(FVector(0, 0, 72.0f));
	Head->SetRelativeLocation(FVector(50.0f, 0, 6.0f));
	Tail->SetRelativeLocation(FVector(-58.0f, 0, 8.0f));
	const FVector LegAt[4] = {FVector(34, 11, -6), FVector(34, -11, -6), FVector(-40, 11, -6), FVector(-40, -11, -6)};
	for (int32 i = 0; i < 4; ++i)
	{
		Legs[i]->SetRelativeLocation(LegAt[i]);
	}
}

void AEHWolf::BeginPlay()
{
	Super::BeginPlay();
	auto Load = [](const TCHAR* Name) { return LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Game/Wolf/%s.%s"), Name, Name), nullptr, LOAD_NoWarn | LOAD_Quiet); };
	Body->SetStaticMesh(Load(TEXT("SM_PH_Wolf_Body")));
	Head->SetStaticMesh(Load(TEXT("SM_PH_Wolf_Head")));
	Tail->SetStaticMesh(Load(TEXT("SM_PH_Wolf_Tail")));
	for (UStaticMeshComponent* L : Legs)
	{
		L->SetStaticMesh(Load(TEXT("SM_PH_Wolf_Leg")));
	}
	if (UStaticMesh* Cuff = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Magic/SM_PH_IceCuff.SM_PH_IceCuff"), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		IceCuff->SetStaticMesh(Cuff);
		IceCuff->SetRelativeScale3D(FVector(1.5f, 1.2f, 1.0f));
	}
	if (!Controller)
	{
		SpawnDefaultController();
	}
}

void AEHWolf::Setup(const FEHWolfTuning& InTuning, AEHPlayerCharacter* InPlayer, AEHTrainingDummy* InDummy)
{
	Tuning = InTuning;
	Player = InPlayer;
	Dummy = InDummy;
	ResetWolf();
}

void AEHWolf::ResetWolf()
{
	Stop();
	GetCharacterMovement()->StopMovementImmediately();
	GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	TeleportTo(Tuning.Spawn + FVector(0, 0, 50.0f), FRotator(0, Tuning.HomeYaw, 0), false, true);
	HealthNow = Tuning.Health;
	bProvoked = false;
	OutsideFor = 0.0f;
	FrozenLeft = 0.0f;
	Cooldown = 60;
	Accum = 0.0f;
	DeadTime = 0.0f;
	Crouch = HeadThrust = 0.0f;
	IceCuff->SetVisibility(false);
	Rig->SetRelativeRotation(FRotator::ZeroRotator);
	Rig->SetRelativeLocation(FVector(0, 0, -48.0f));
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	bBiteCue = false;
	BiteCount = LungeCount = ConnectCount = DisengageCount = AbsorbCount = ProtectCount = FreezeCount = 0;
	Enter(EEHWolfState::Calm, 0);
}

FVector AEHWolf::FeetLocation() const
{
	return GetActorLocation() - FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
}

bool AEHWolf::PlayerOutside() const
{
	return Player.IsValid() && Player->GetActorLocation().Y > Tuning.LeaveLineY;
}

FVector AEHWolf::ToPlayer2D() const
{
	if (!Player.IsValid())
	{
		return FVector::ZeroVector;
	}
	FVector D = Player->GetActorLocation() - GetActorLocation();
	D.Z = 0.0f;
	return D;
}

EEHWolfState AEHWolf::Attitude() const
{
	// Hostile when provoked, or toward a menacing (evil) aura; otherwise calm in its own way.
	return (bProvoked || EHAlign::Band(Alignment) == EEHAlignBand::Evil) ? EEHWolfState::Hostile : EEHWolfState::Calm;
}

bool AEHWolf::IsHostile() const
{
	switch (State)
	{
	case EEHWolfState::Hostile: case EEHWolfState::BiteWindup: case EEHWolfState::Bite: case EEHWolfState::LungeWindup:
	case EEHWolfState::Lunge: case EEHWolfState::Recover: case EEHWolfState::Guarding:
		return true;
	default:
		return false;
	}
}

void AEHWolf::Enter(EEHWolfState Next, int32 Length)
{
	State = Next;
	StateFrame = 0;
	StateLength = Length;
}

void AEHWolf::MoveTo(const FVector& Where, float Speed, float Accept)
{
	GetCharacterMovement()->MaxWalkSpeed = Speed;
	AAIController* AI = Cast<AAIController>(Controller);
	if (AI == nullptr || FrozenLeft > 0.0f)
	{
		return;
	}
	// Re-plan only when the goal has moved a fair way: the path follows the navigation mesh, which an Ice Wall cuts.
	if (FVector::Dist2D(Where, LastMoveTarget) > 60.0f || AI->GetMoveStatus() == EPathFollowingStatus::Idle)
	{
		LastMoveTarget = Where;
		AI->MoveToLocation(Where, Accept, false, true, true, false, nullptr, true);
	}
}

void AEHWolf::Stop()
{
	if (AAIController* AI = Cast<AAIController>(Controller))
	{
		AI->StopMovement();
	}
	LastMoveTarget = FVector(1e9);
}

void AEHWolf::FaceTowards(const FVector& Where, float DegPerFrame)
{
	FVector D = Where - GetActorLocation();
	D.Z = 0.0f;
	if (!D.IsNearlyZero())
	{
		SetActorRotation(FRotator(0, FMath::FixedTurn(GetActorRotation().Yaw, D.Rotation().Yaw, DegPerFrame), 0));
	}
}

bool AEHWolf::NoticeThreat(const FVector& Eye, const FVector& Aim)
{
	if (IsDead() || IsHostile() || State == EEHWolfState::Hitstun)
	{
		return false;
	}
	FVector To = GetActorLocation() - Eye;
	To.Z = 0.0f;
	const float Dist = To.Size();
	FVector A = Aim;
	A.Z = 0.0f;
	if (Dist > Tuning.ThreatRange || FVector::DotProduct(To.GetSafeNormal(), A.GetSafeNormal()) < 0.8f)
	{
		return false;
	}
	// It backs off and watches, giving the player the chance to stop.
	DisengageFrom = Eye;
	++DisengageCount;
	Enter(EEHWolfState::Disengage, FMath::RoundToInt(Tuning.DisengageSeconds * 60.0f));
	return true;
}

FEHWolfHit AEHWolf::ReceivePlayerHit(float Damage, const FVector& From, const FVector& At, bool bHeavy)
{
	FEHWolfHit Out;
	if (IsDead())
	{
		return Out;
	}
	if (Alignment == EHAlign::Hero)
	{
		// The guardians' bond: a Hero of Humanity cannot harm them; the blow turns back on the player.
		Out.Reflected = Damage;
		return Out;
	}
	Out.Damage = Damage;
	Out.bHarmed = Damage > 0.0f;
	HealthNow = FMath::Max(0.0f, HealthNow - Damage);
	if (Out.bHarmed)
	{
		bProvoked = true;
		OutsideFor = 0.0f;
	}
	FVector Away = GetActorLocation() - From;
	Away.Z = 0.0f;
	if (HealthNow <= 0.0f)
	{
		Out.bKilled = true;
		Stop();
		GetCharacterMovement()->StopMovementImmediately();
		GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Enter(EEHWolfState::Dead, 0);
		return Out;
	}
	Stop();
	if (FrozenLeft <= 0.0f)
	{
		LaunchCharacter(Away.GetSafeNormal() * (bHeavy ? 420.0f : 220.0f) + FVector(0, 0, 80.0f), true, false);
	}
	Enter(EEHWolfState::Hitstun, Tuning.Hitstun);
	return Out;
}

bool AEHWolf::Absorb(float Damage)
{
	if (IsDead())
	{
		return false;
	}
	// The protection is temporary and never costs the wolf its life.
	HealthNow = FMath::Max(1.0f, HealthNow - Damage);
	++AbsorbCount;
	return true;
}

void AEHWolf::Freeze(float Seconds)
{
	if (Seconds <= 0.0f || IsDead())
	{
		return;
	}
	FrozenLeft = FMath::Max(FrozenLeft, Seconds);
	++FreezeCount;
	Stop();
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->StopMovementImmediately();
	Movement->ClearAccumulatedForces();
	if (State == EEHWolfState::BiteWindup || State == EEHWolfState::LungeWindup || State == EEHWolfState::Lunge)
	{
		const int32 Recovery = State == EEHWolfState::BiteWindup ? Tuning.BiteRecover : Tuning.LungeRecover;
		Enter(EEHWolfState::Recover, Recovery);
		Cooldown = Tuning.AttackCooldown;
	}
	IceCuff->SetVisibility(true);
}

void AEHWolf::Displace(const FVector& Offset, AActor* Ignore)
{
	if (Ignore)
	{
		GetCapsuleComponent()->IgnoreActorWhenMoving(Ignore, true);
	}
	AddActorWorldOffset(FVector(Offset.X, Offset.Y, 0.0f), true);
	if (Ignore)
	{
		GetCapsuleComponent()->IgnoreActorWhenMoving(Ignore, false);
	}
}

void AEHWolf::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Accum = FMath::Min(Accum + DeltaSeconds, 0.25f);
	while (Accum >= Step)
	{
		Accum -= Step;
		StepFrame();
	}
	UpdatePose(DeltaSeconds);
}

void AEHWolf::StepFrame()
{
	++StateFrame;
	if (Cooldown > 0)
	{
		--Cooldown;
	}
	if (State == EEHWolfState::Dead)
	{
		return;
	}
	if (FrozenLeft > 0.0f)
	{
		FrozenLeft = FMath::Max(0.0f, FrozenLeft - Step);
		GetCharacterMovement()->StopMovementImmediately();
		IceCuff->SetVisibility(FrozenLeft > 0.0f);
	}
	const bool bFrozen = FrozenLeft > 0.0f;
	const FVector To = ToPlayer2D();
	const float Dist = To.Size();
	const bool bOutside = PlayerOutside();
	// Provoked hostility ends once the player has left the Chapel's floor for a while (and so comes back to a calm
	// wolf). A menacing aura keeps it hostile regardless.
	if (bProvoked)
	{
		OutsideFor = bOutside ? OutsideFor + Step : 0.0f;
		if (OutsideFor >= Tuning.CalmSeconds)
		{
			bProvoked = false;
			OutsideFor = 0.0f;
		}
	}
	const EEHWolfState Want = Attitude();
	const EEHAlignBand Band = EHAlign::Band(Alignment);
	switch (State)
	{
	case EEHWolfState::Calm:
	{
		if (Want == EEHWolfState::Hostile)
		{
			Enter(EEHWolfState::Hostile, 0);
			break;
		}
		if (!Player.IsValid() || bFrozen)
		{
			break;
		}
		if (Band == EEHAlignBand::Good && !bOutside)
		{
			// Friendly: keeps the player company, a little to one side.
			if (Dist > Tuning.FollowDistance + 80.0f)
			{
				MoveTo(Player->GetActorLocation() - To.GetSafeNormal() * Tuning.FollowDistance, Dist > 600.0f ? Tuning.RunSpeed : Tuning.WalkSpeed, 60.0f);
			}
			else
			{
				Stop();
				FaceTowards(Player->GetActorLocation(), 4.0f);
			}
			// Protects: anything winding up a strike at the player is bitten first.
			if (Dummy.IsValid() && Dummy->IsWindingUp() && FVector::Dist2D(Dummy->GetActorLocation(), GetActorLocation()) < Tuning.ProtectRange
				&& FVector::Dist2D(Dummy->GetActorLocation(), Player->GetActorLocation()) < 400.0f)
			{
				++ProtectCount;
				Enter(EEHWolfState::Protect, 90);
			}
		}
		else if (Band == EEHAlignBand::Neutral && Dist < Tuning.KeepDistance && !bOutside)
		{
			// Wary: keeps its distance, watching.
			MoveTo(GetActorLocation() - To.GetSafeNormal() * (Tuning.KeepDistance - Dist + 120.0f), Tuning.WalkSpeed, 50.0f);
		}
		else if (FVector::Dist2D(GetActorLocation(), Tuning.Home) > 120.0f && (Band != EEHAlignBand::Good || bOutside))
		{
			MoveTo(Tuning.Home, Tuning.WalkSpeed, 60.0f);
		}
		else
		{
			Stop();
			FaceTowards(Player->GetActorLocation(), 2.0f);
		}
		break;
	}
	case EEHWolfState::Disengage:
	{
		// Backs off from where the threat came from, facing it.
		FVector Away = GetActorLocation() - DisengageFrom;
		Away.Z = 0.0f;
		if (Away.Size() < Tuning.DisengageDistance && !bFrozen)
		{
			MoveTo(DisengageFrom + Away.GetSafeNormal() * (Tuning.DisengageDistance + 60.0f), Tuning.RunSpeed, 50.0f);
		}
		else
		{
			Stop();
			FaceTowards(DisengageFrom, 6.0f);
		}
		if (Want == EEHWolfState::Hostile || StateFrame >= StateLength)
		{
			Enter(Want == EEHWolfState::Hostile ? EEHWolfState::Hostile : EEHWolfState::Calm, 0);
		}
		break;
	}
	case EEHWolfState::Protect:
	{
		if (!Dummy.IsValid() || bFrozen)
		{
			Enter(EEHWolfState::Calm, 0);
			break;
		}
		const float D = FVector::Dist2D(Dummy->GetActorLocation(), GetActorLocation());
		if (D > Tuning.BiteRange)
		{
			MoveTo(Dummy->GetActorLocation(), Tuning.RunSpeed, 30.0f);
		}
		else
		{
			Stop();
			FaceTowards(Dummy->GetActorLocation(), 20.0f);
			FEHStrikeDef Def;
			Def.Damage = Tuning.BiteDamage;
			Def.Hitstop = 3;
			Dummy->ReceiveHit(EEHFistAction::Jab, Def, GetActorLocation() + FVector(0, 0, 40.0f), Dummy->GetActorLocation() + FVector(0, 0, 10.0f), 0.0f);
			++BiteCount;
			HeadThrust = 1.0f;
			Enter(EEHWolfState::Calm, 0);
			Cooldown = Tuning.AttackCooldown;
		}
		if (StateFrame >= StateLength)
		{
			Enter(EEHWolfState::Calm, 0);
		}
		break;
	}
	case EEHWolfState::Hostile:
	case EEHWolfState::Guarding:
	{
		if (Want != EEHWolfState::Hostile)
		{
			Enter(EEHWolfState::Calm, 0);
			break;
		}
		if (!Player.IsValid() || bFrozen)
		{
			break;
		}
		if (bOutside)
		{
			// The player has left the Chapel's floor: it holds the edge and waits.
			if (State != EEHWolfState::Guarding)
			{
				Enter(EEHWolfState::Guarding, 0);
			}
			const FVector Edge(FMath::Clamp(Player->GetActorLocation().X, -700.0f, 700.0f), Tuning.LeaveLineY - 220.0f, GetActorLocation().Z);
			MoveTo(Edge, Tuning.WalkSpeed, 60.0f);
			FaceTowards(Player->GetActorLocation(), 6.0f);
			break;
		}
		if (State == EEHWolfState::Guarding)
		{
			Enter(EEHWolfState::Hostile, 0);
		}
		// Attack when ready: a bite up close, a lunge from range; otherwise circle at a distance, changing direction.
		if (Cooldown == 0 && Dist <= Tuning.BiteRange)
		{
			Stop();
			Enter(EEHWolfState::BiteWindup, Tuning.BiteWindup);
			break;
		}
		if (Cooldown == 0 && Dist >= Tuning.LungeMin && Dist <= Tuning.LungeMax && FMath::FRand() < 0.04f)
		{
			Stop();
			Enter(EEHWolfState::LungeWindup, Tuning.LungeWindup);
			break;
		}
		if (Cooldown > 0 || Dist > Tuning.CircleRadius + 150.0f)
		{
			if (--CircleFrames <= 0)
			{
				CircleFrames = FMath::RandRange(70, 160);
				CircleSign = FMath::FRand() < 0.5f ? -1.0f : 1.0f;
			}
			const FVector Dir = (-To).GetSafeNormal();
			const FVector Side = FVector::CrossProduct(FVector::UpVector, Dir) * CircleSign;
			const FVector Goal = Player->GetActorLocation() + (Dir * Tuning.CircleRadius + Side * 160.0f).GetSafeNormal() * Tuning.CircleRadius;
			MoveTo(Goal, Dist > Tuning.CircleRadius + 300.0f ? Tuning.RunSpeed : Tuning.WalkSpeed * 1.3f, 40.0f);
		}
		else
		{
			// Ready and close enough: come in for the bite.
			MoveTo(Player->GetActorLocation(), Tuning.RunSpeed, 20.0f);
		}
		break;
	}
	case EEHWolfState::BiteWindup:
		if (Player.IsValid())
		{
			FaceTowards(Player->GetActorLocation(), 8.0f);
		}
		if (StateFrame >= StateLength)
		{
			++BiteCount;
			bBiteCue = true;
			HeadThrust = 1.0f;
			const float Off = Player.IsValid() ? FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw, To.Rotation().Yaw)) : 999.0f;
			if (Player.IsValid() && Dist <= Tuning.BiteReach && Off <= 45.0f)
			{
				++ConnectCount;
				Player->ReceiveStrike(Tuning.BiteDamage, GetActorLocation() + GetActorForwardVector() * 60.0f + FVector(0, 0, 40.0f));
			}
			Enter(EEHWolfState::Recover, Tuning.BiteRecover);
			Cooldown = Tuning.AttackCooldown;
		}
		break;
	case EEHWolfState::LungeWindup:
		if (Player.IsValid())
		{
			FaceTowards(Player->GetActorLocation(), 6.0f);
		}
		if (StateFrame >= StateLength)
		{
			++LungeCount;
			bLungeHit = false;
			if (!bFrozen)
			{
				LaunchCharacter(GetActorForwardVector() * Tuning.LungeSpeed + FVector(0, 0, 260.0f), true, true);
			}
			Enter(EEHWolfState::Lunge, 40);
		}
		break;
	case EEHWolfState::Lunge:
		if (!bLungeHit && Player.IsValid() && Dist <= 120.0f)
		{
			bLungeHit = true;
			++ConnectCount;
			Player->ReceiveStrike(Tuning.LungeDamage, GetActorLocation() + FVector(0, 0, 40.0f));
		}
		if ((StateFrame > 8 && GetCharacterMovement()->IsMovingOnGround()) || StateFrame >= StateLength)
		{
			Enter(EEHWolfState::Recover, Tuning.LungeRecover);
			Cooldown = Tuning.AttackCooldown;
		}
		break;
	case EEHWolfState::Recover:
		Stop();
		if (StateFrame >= StateLength)
		{
			Enter(Want == EEHWolfState::Hostile ? EEHWolfState::Hostile : EEHWolfState::Calm, 0);
		}
		break;
	case EEHWolfState::Hitstun:
		if (StateFrame >= StateLength)
		{
			Enter(Want == EEHWolfState::Hostile ? EEHWolfState::Hostile : EEHWolfState::Calm, 0);
		}
		break;
	default:
		break;
	}
}

void AEHWolf::UpdatePose(float DeltaSeconds)
{
	if (State == EEHWolfState::Dead)
	{
		// Collapses onto its side.
		DeadTime += DeltaSeconds;
		const float T = FMath::Clamp(DeadTime / 0.5f, 0.0f, 1.0f);
		Rig->SetRelativeRotation(FRotator(0, 0, 88.0f * T * T));
		Rig->SetRelativeLocation(FVector(0, 0, -48.0f + 22.0f * T));
		return;
	}
	const float Speed = GetVelocity().Size2D();
	const bool bAir = GetCharacterMovement()->IsFalling();
	// Walk cycle: diagonal legs together, faster and longer with speed.
	Gait += DeltaSeconds * (2.0f + Speed / 70.0f) * PI;
	const float Swing = FMath::Clamp(Speed / 500.0f, 0.0f, 1.0f) * 34.0f;
	const float Phase[4] = {0.0f, PI, PI, 0.0f};
	const float WantCrouch = (State == EEHWolfState::BiteWindup || State == EEHWolfState::LungeWindup) ? 1.0f : (State == EEHWolfState::Hostile ? 0.35f : 0.0f);
	Crouch = FMath::FInterpTo(Crouch, WantCrouch, DeltaSeconds, 12.0f);
	HeadThrust = FMath::FInterpTo(HeadThrust, 0.0f, DeltaSeconds, 7.0f);
	for (int32 i = 0; i < 4; ++i)
	{
		const float A = bAir ? (i < 2 ? -40.0f : 40.0f) : FMath::Sin(Gait + Phase[i]) * Swing;
		Legs[i]->SetRelativeRotation(FRotator(A, 0, 0));
	}
	// Body: a bob in the stride, low and forward when stalking or winding up.
	const float Bob = FMath::Abs(FMath::Sin(Gait)) * FMath::Clamp(Speed / 500.0f, 0.0f, 1.0f) * 3.0f;
	Body->SetRelativeLocation(FVector(0, 0, 72.0f - 12.0f * Crouch + Bob));
	Body->SetRelativeRotation(FRotator(-6.0f * Crouch, 0, 0));
	// Head: looks at the player; low when hostile, up when friendly; snaps forward in a bite.
	float Yaw = 0.0f;
	if (Player.IsValid())
	{
		const FVector Local = GetActorTransform().InverseTransformVectorNoScale(ToPlayer2D());
		Yaw = FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X)), -55.0f, 55.0f);
	}
	const bool bFriendly = State == EEHWolfState::Calm && EHAlign::Band(Alignment) == EEHAlignBand::Good;
	const float Pitch = bFriendly ? 8.0f : (IsHostile() ? -14.0f : 0.0f);
	Head->SetRelativeLocation(FVector(50.0f + 16.0f * HeadThrust, 0, 6.0f - 8.0f * Crouch));
	Head->SetRelativeRotation(FRotator(Pitch - 18.0f * HeadThrust, Yaw, 0));
	// Tail: wags for a friend, hangs for a wary wolf, straight out and stiff when hostile.
	WagTime += DeltaSeconds;
	const float TailYaw = bFriendly ? FMath::Sin(WagTime * 11.0f) * 28.0f : 0.0f;
	const float TailPitch = bFriendly ? 22.0f : (IsHostile() ? 16.0f : -10.0f);
	Tail->SetRelativeRotation(FRotator(TailPitch, TailYaw, 0));
}

FString AEHWolf::Describe() const
{
	return FString::Printf(TEXT("%s hp=%.0f provoked=%d frozen=%.1f bites=%d lunges=%d connected=%d disengaged=%d absorbed=%d protects=%d"),
		EHWolfStateName(State), HealthNow, bProvoked ? 1 : 0, FrozenLeft, BiteCount, LungeCount, ConnectCount, DisengageCount, AbsorbCount, ProtectCount);
}
