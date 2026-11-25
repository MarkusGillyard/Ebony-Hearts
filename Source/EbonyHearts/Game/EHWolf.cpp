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
#include "Materials/MaterialInstanceDynamic.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"

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
	case EEHWolfState::Warn: return TEXT("warning");
	case EEHWolfState::Rest: return TEXT("resting");
	case EEHWolfState::Sleep: return TEXT("asleep");
	case EEHWolfState::Wander: return TEXT("wandering");
	case EEHWolfState::Greet: return TEXT("greeting");
	case EEHWolfState::Beside: return TEXT("lying beside the player");
	case EEHWolfState::Sanctuary: return TEXT("standing guard over the prayer");
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
	Num(TEXT("leaveMaxZ"), LeaveMaxZ, -5000, 5000);
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
	Num(TEXT("warnRange"), WarnRange, 0, 5000);
	Num(TEXT("warnRadius"), WarnRadius, 50, 3000);
	Num(TEXT("warnClose"), WarnClose, 0, 3000);
	Num(TEXT("warnSeconds"), WarnSeconds, 0, 600);
	Num(TEXT("alertRange"), AlertRange, 0, 10000);
	Num(TEXT("sanctuaryGuard"), SanctuaryGuard, 50, 3000);
	Num(TEXT("shadowPatience"), ShadowPatience, 1, 3600);
	Num(TEXT("friendRange"), FriendRange, 0, 10000);
	Num(TEXT("noticeRange"), NoticeRange, 0, 3000);
	Num(TEXT("restSeconds"), RestSeconds, 0.5, 600);
	Num(TEXT("sleepSeconds"), SleepSeconds, 0.5, 3600);
	Num(TEXT("wanderRadius"), WanderRadius, 0, 5000);
	Num(TEXT("besideHealth"), BesideHealth, 0, 1);
	Num(TEXT("besideStill"), BesideStill, 0, 60);
	return bOk;
}

FString FEHWolfTuning::Describe() const
{
	return FString::Printf(TEXT("hp=%.0f home=(%.0f,%.0f) leave_y=%.0f calm=%.1fs walk=%.0f run=%.0f follow=%.0f keep=%.0f threat=%.0f disengage=%.1fs/%.0f circle=%.0f "
		"bite %.0f/%.0f dmg=%.0f %d+%d lunge %.0f..%.0f @%.0f dmg=%.0f %d+%d cooldown=%d stun=%d absorb=%.0f protect=%.0f"),
		Health, Home.X, Home.Y, LeaveLineY, CalmSeconds, WalkSpeed, RunSpeed, FollowDistance, KeepDistance, ThreatRange, DisengageSeconds, DisengageDistance,
		CircleRadius, BiteRange, BiteReach, BiteDamage, BiteWindup, BiteRecover, LungeMin, LungeMax, LungeSpeed, LungeDamage, LungeWindup, LungeRecover,
		AttackCooldown, Hitstun, AbsorbRange, ProtectRange) + FString::Printf(TEXT(" warn %.0f/%.0f close=%.0f %.0fs alert=%.0f sanctuary=%.0f shadow=%.0fs friend=%.0f notice=%.0f rest=%.0fs sleep=%.0fs wander=%.0f beside<%.2f after %.1fs"),
		WarnRange, WarnRadius, WarnClose, WarnSeconds, AlertRange, SanctuaryGuard, ShadowPatience, FriendRange, NoticeRange, RestSeconds, SleepSeconds, WanderRadius, BesideHealth, BesideStill);
}

AEHWolf::AEHWolf(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	PrimaryActorTick.bCanEverTick = true;
	AIControllerClass = AAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	GetCapsuleComponent()->InitCapsuleSize(44.0f, 76.0f);
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
	Move->NavAgentProps.AgentRadius = 40.0f;
	Move->NavAgentProps.AgentHeight = 152.0f;

	Rig = CreateDefaultSubobject<USceneComponent>(TEXT("Rig"));
	Rig->SetupAttachment(GetCapsuleComponent());
	Rig->SetRelativeLocation(FVector(0, 0, -76.0f));
	auto Part = [this](const TCHAR* Name, USceneComponent* Parent) {
		UStaticMeshComponent* C = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		C->SetupAttachment(Parent);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCanEverAffectNavigation(false);
		C->SetCastShadow(true);
		return C;
	};
	Body = Part(TEXT("Body"), Rig);
	Mane = Part(TEXT("Mane"), Body);
	Head = Part(TEXT("Head"), Body);
	Tail = Part(TEXT("Tail"), Body);
	for (int32 i = 0; i < 4; ++i)
	{
		Legs[i] = Part(*FString::Printf(TEXT("Leg%d"), i), Body);
	}
	IceCuff = Part(TEXT("IceCuff"), Rig);
	IceCuff->SetCastShadow(false);
	IceCuff->SetVisibility(false);
	// Horse-sized proportions: ~150 cm at the shoulder. Legs: front left, front right, back left, back right.
	Body->SetRelativeLocation(FVector(0, 0, 124.0f));
	Mane->SetRelativeLocation(FVector(46.0f, 0, 14.0f));
	Head->SetRelativeLocation(FVector(88.0f, 0, 14.0f));
	Tail->SetRelativeLocation(FVector(-92.0f, 0, 12.0f));
	const FVector LegAt[4] = {FVector(64, 24, -8), FVector(64, -24, -8), FVector(-66, 22, -8), FVector(-66, -22, -8)};
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
	Mane->SetStaticMesh(Load(TEXT("SM_PH_Wolf_Mane")));
	Head->SetStaticMesh(Load(TEXT("SM_PH_Wolf_Head")));
	Tail->SetStaticMesh(Load(TEXT("SM_PH_Wolf_Tail")));
	for (UStaticMeshComponent* L : Legs)
	{
		L->SetStaticMesh(Load(TEXT("SM_PH_Wolf_Leg")));
	}
	if (UStaticMesh* Cuff = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Magic/SM_PH_IceCuff.SM_PH_IceCuff"), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		IceCuff->SetStaticMesh(Cuff);
		IceCuff->SetRelativeScale3D(FVector(2.4f, 1.9f, 1.3f));
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

void AEHWolf::SetCoatVariant(int32 Index)
{
	// Individual pack wolves vary in coat darkness and silver sheen (charcoal, darker obsidian, silver-ash, blue-slate).
	static const FLinearColor Coats[4] = {
		FLinearColor(1.00f, 1.00f, 1.00f, 1.0f),
		FLinearColor(0.68f, 0.70f, 0.76f, 1.0f),
		FLinearColor(1.22f, 1.22f, 1.25f, 1.0f),
		FLinearColor(0.76f, 0.82f, 0.94f, 1.0f),
	};
	static const FLinearColor Manes[4] = {
		FLinearColor(1.00f, 1.00f, 1.00f, 1.0f),
		FLinearColor(0.84f, 0.86f, 0.90f, 1.0f),
		FLinearColor(1.12f, 1.12f, 1.14f, 1.0f),
		FLinearColor(0.88f, 0.92f, 1.00f, 1.0f),
	};
	const int32 V = FMath::Abs(Index) % 4;
	auto Tint = [](UStaticMeshComponent* C, const TCHAR* Param, const FLinearColor& Col) {
		if (C && C->GetMaterial(0))
		{
			if (UMaterialInstanceDynamic* MID = C->CreateAndSetMaterialInstanceDynamic(0))
			{
				MID->SetVectorParameterValue(Param, Col);
			}
		}
	};
	Tint(Body, TEXT("CoatTint"), Coats[V]);
	Tint(Head, TEXT("CoatTint"), Coats[V]);
	Tint(Tail, TEXT("CoatTint"), Coats[V]);
	for (UStaticMeshComponent* L : Legs)
	{
		Tint(L, TEXT("CoatTint"), Coats[V]);
	}
	Tint(Mane, TEXT("ManeTint"), Manes[V]);
}

void AEHWolf::HaltForTest()
{
	Stop();
	GetCharacterMovement()->StopMovementImmediately();
	LastMoveTarget = FVector(1e9);
}

void AEHWolf::ResetWolf()
{
	Stop();
	GetCharacterMovement()->StopMovementImmediately();
	GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	TeleportTo(Tuning.Spawn + FVector(0, 0, 78.0f), FRotator(0, Tuning.HomeYaw, 0), false, true);
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
	Rig->SetRelativeLocation(FVector(0, 0, -76.0f));
	GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
	bBiteCue = false;
	BiteCount = LungeCount = ConnectCount = DisengageCount = AbsorbCount = ProtectCount = FreezeCount = 0;
	RepathCount = StuckCount = StuckFrames = WaitGoalFrames = 0;
	Reactions = Rebuffs = 0;
	Tilt = TiltVel = Snap = SnapVel = FVector2D::ZeroVector;
	PeakTilt = 0.0f;
	WaitGoal = FVector(1e9);
	SinceAttack = 0.0f;
	PackRole = EEHPackRole::Free;
	bEscalated = false;
	WarnFor = 0.0f;
	RestLeft = 0.0f;
	AwayFor = 100.0f;
	bGreetDue = false;
	GraceLeft = 0.0f;
	PlayerStillFor = 0.0f;
	Lie = HeadDown = HacklesNow = 0.0f;
	Enter(EEHWolfState::Calm, 0);
}

FVector AEHWolf::FeetLocation() const
{
	return GetActorLocation() - FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
}

FVector AEHWolf::LockOnPoint() const
{
	return FeetLocation() + FVector(0.0f, 0.0f, Body ? Body->GetRelativeLocation().Z : 72.0f);
}

bool AEHWolf::PlayerOutside() const
{
	return Player.IsValid() && Player->FeetLocation().Y > Tuning.LeaveLineY && Player->FeetLocation().Z < Tuning.LeaveMaxZ;
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
	// Prayer is sanctuary: no wolf attacks the one praying, whatever they are. Otherwise a fight when provoked or when an
	// evil aura would not leave; a warning toward an evil aura or a Shadow; calm in its own way toward everyone else.
	if (bSanctuary)
	{
		return EEHWolfState::Sanctuary;
	}
	if (bProvoked || (bEscalated && EHAlign::Band(Alignment) == EEHAlignBand::Evil))
	{
		return EEHWolfState::Hostile;
	}
	if (bShadow || EHAlign::Band(Alignment) == EEHAlignBand::Evil)
	{
		return EEHWolfState::Warn;
	}
	return EEHWolfState::Calm;
}

bool AEHWolf::IsCalmLike() const
{
	switch (State)
	{
	case EEHWolfState::Calm: case EEHWolfState::Rest: case EEHWolfState::Sleep: case EEHWolfState::Wander:
	case EEHWolfState::Greet: case EEHWolfState::Beside: case EEHWolfState::Sanctuary:
		return true;
	default:
		return false;
	}
}

void AEHWolf::StartRest(bool bSleep)
{
	Stop();
	RestLeft = (bSleep ? Tuning.SleepSeconds : Tuning.RestSeconds) * FMath::FRandRange(0.6f, 1.6f);
	Enter(bSleep ? EEHWolfState::Sleep : EEHWolfState::Rest, 0);
}

bool AEHWolf::TryProtect()
{
	// Anything winding up a strike at the player is bitten first.
	if (Player.IsValid() && Dummy.IsValid() && Dummy->IsWindingUp() && FVector::Dist2D(Dummy->GetActorLocation(), GetActorLocation()) < Tuning.ProtectRange
		&& FVector::Dist2D(Dummy->GetActorLocation(), Player->GetActorLocation()) < 400.0f)
	{
		++ProtectCount;
		Enter(EEHWolfState::Protect, 90);
		return true;
	}
	return false;
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

bool AEHWolf::IsAttacking() const
{
	switch (State)
	{
	case EEHWolfState::BiteWindup: case EEHWolfState::Bite: case EEHWolfState::LungeWindup: case EEHWolfState::Lunge:
	case EEHWolfState::Recover:
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

FVector AEHWolf::FindWaitSpot(float Radius) const
{
	// The nearest place on the circle (from the wolf's own bearing, a step ahead in its circling direction, then
	// alternately further each way) that is on the navigation mesh and still about that far from the player.
	const FVector P = Player->GetActorLocation();
	const FVector From = GetActorLocation() - P;
	const float Bearing = FMath::Atan2(From.Y, From.X) + CircleSign * FMath::DegreesToRadians(17.0f);
	const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	FVector Fallback = P + FVector(FMath::Cos(Bearing), FMath::Sin(Bearing), 0.0f) * Radius;
	if (Nav == nullptr)
	{
		return Fallback;
	}
	for (int32 k = 0; k < 16; ++k)
	{
		const float Turn = FMath::DegreesToRadians(22.5f) * ((k + 1) / 2) * (k % 2 == 0 ? 1.0f : -1.0f) * CircleSign;
		const float A = Bearing + Turn;
		const FVector C = P + FVector(FMath::Cos(A), FMath::Sin(A), 0.0f) * Radius;
		FNavLocation On;
		if (Nav->ProjectPointToNavigation(FVector(C.X, C.Y, GetActorLocation().Z), On, FVector(60.0f, 60.0f, 250.0f))
			&& FVector::Dist2D(On.Location, P) >= Radius * 0.85f && FVector::Dist2D(On.Location, C) < 80.0f)
		{
			return On.Location;
		}
	}
	return Fallback;
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
	const bool bWarning = State == EEHWolfState::Warn;
	FVector To = GetActorLocation() - Eye;
	To.Z = 0.0f;
	const float Dist = To.Size();
	FVector A = Aim;
	A.Z = 0.0f;
	if (Dist > Tuning.ThreatRange || FVector::DotProduct(To.GetSafeNormal(), A.GetSafeNormal()) < 0.8f)
	{
		return false;
	}
	if (bWarning && !bShadow)
	{
		// A swing at it from someone it was already warning: the warning is over.
		Escalate();
		return true;
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
	Out.WolfAt = GetActorLocation();
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
	// The body takes the blow: it tips away from it and the head snaps aside (springs that settle on their own); a
	// heavy blow staggers it for longer.
	React(Away.GetSafeNormal(), bHeavy ? 1.15f : 0.7f);
	Enter(EEHWolfState::Hitstun, Tuning.Hitstun + (bHeavy ? 12 : 0));
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

void AEHWolf::SetSanctuary(bool bOn)
{
	if (bSanctuary == bOn)
	{
		return;
	}
	bSanctuary = bOn;
	if (bOn && IsAttacking())
	{
		Stop();
		UCharacterMovementComponent* Movement = GetCharacterMovement();
		Movement->StopMovementImmediately();
		Movement->ClearAccumulatedForces();
		Enter(EEHWolfState::Sanctuary, 0);
	}
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
	SinceAttack = IsAttacking() ? 0.0f : SinceAttack + Step;
	// Moving but going nowhere (a wall the navigation has not caught up with yet, another wolf in the way): re-plan.
	if (AAIController* AI = Cast<AAIController>(Controller); AI && !bFrozen && AI->GetMoveStatus() == EPathFollowingStatus::Moving
		&& GetVelocity().Size2D() < 25.0f && FVector::Dist2D(GetActorLocation(), LastMoveTarget) > 120.0f)
	{
		if (++StuckFrames >= 45)
		{
			StuckFrames = 0;
			++StuckCount;
			LastMoveTarget = FVector(1e9);
			AI->StopMovement();
		}
	}
	else
	{
		StuckFrames = 0;
	}
	const FVector To = ToPlayer2D();
	const float Dist = To.Size();
	const bool bOutside = PlayerOutside();
	// Provoked hostility, and a fight with an evil aura that would not leave, end once the player has left the Chapel's
	// floor for a while (and so comes back to a calm wolf, judged by their alignment again).
	if (bProvoked || bEscalated)
	{
		OutsideFor = bOutside ? OutsideFor + Step : 0.0f;
		if (OutsideFor >= Tuning.CalmSeconds)
		{
			bProvoked = false;
			bEscalated = false;
			OutsideFor = 0.0f;
		}
	}
	// What it knows of the player: how long they have kept still, how long a friend has been away.
	if (Player.IsValid())
	{
		const FVector At = Player->GetActorLocation();
		PlayerStillFor = FVector::Dist2D(At, PlayerLastAt) < 1.5f ? PlayerStillFor + Step : 0.0f;
		PlayerLastAt = At;
	}
	const EEHWolfState Want = Attitude();
	const EEHAlignBand Band = EHAlign::Band(Alignment);
	const bool bFriend = Band == EEHAlignBand::Good && !bShadow && !bOutside && Dist < Tuning.FriendRange;
	if (bFriend && Dist < 900.0f)
	{
		bGreetDue |= AwayFor > 8.0f;
		AwayFor = 0.0f;
	}
	else
	{
		AwayFor += Step;
	}
	GraceLeft = FMath::Max(0.0f, GraceLeft - Step);
	if (bOutside || Want != EEHWolfState::Warn)
	{
		WarnFor = 0.0f;
	}
	// Any calm-like state gives way at once when the attitude changes (a prayer begins or ends, a fight starts).
	if (IsCalmLike())
	{
		const bool bInSanctuary = State == EEHWolfState::Sanctuary;
		if (Want == EEHWolfState::Hostile || Want == EEHWolfState::Warn || (Want == EEHWolfState::Sanctuary) != bInSanctuary)
		{
			if (bInSanctuary && Want == EEHWolfState::Warn)
			{
				GraceLeft = 3.0f;   // the prayer is over: it steps back before its warning can turn into a fight
			}
			Enter(Want, 0);
		}
	}
	switch (State)
	{
	case EEHWolfState::Calm:
	{
		// Attending to the player in its own way, or settling to rest.
		if (!Player.IsValid() || bFrozen)
		{
			break;
		}
		if (bFriend)
		{
			if (bGreetDue && Dist < 450.0f)
			{
				// A friend come back: it greets them, head lowered and tail going.
				bGreetDue = false;
				Stop();
				Enter(EEHWolfState::Greet, 72);
				break;
			}
			if (TryProtect())
			{
				break;
			}
			if (Player->HealthFraction() < Tuning.BesideHealth && PlayerStillFor >= Tuning.BesideStill && Dist < 700.0f)
			{
				// A friend badly hurt and keeping still: it lies down beside them until they recover or move off.
				Enter(EEHWolfState::Beside, 0);
				break;
			}
			// Keeps the player company, a little to one side; when they stay put a while, it lies down near them.
			if (Dist > Tuning.FollowDistance + 80.0f)
			{
				MoveTo(Player->GetActorLocation() - To.GetSafeNormal() * Tuning.FollowDistance, Dist > 600.0f ? Tuning.RunSpeed : Tuning.WalkSpeed, 60.0f);
			}
			else if (PlayerStillFor > 6.0f)
			{
				StartRest(false);
			}
			else
			{
				Stop();
				FaceTowards(Player->GetActorLocation(), 4.0f);
			}
			break;
		}
		if (Band == EEHAlignBand::Neutral && !bOutside && !bShadow)
		{
			// Wary, but still a guardian: it goes for a strike at the player, and keeps its distance.
			if (TryProtect())
			{
				break;
			}
			if (Dist < Tuning.KeepDistance)
			{
				MoveTo(GetActorLocation() - To.GetSafeNormal() * (Tuning.KeepDistance - Dist + 120.0f), Tuning.WalkSpeed, 50.0f);
				break;
			}
		}
		if (FVector::Dist2D(GetActorLocation(), Tuning.Home) > 120.0f)
		{
			MoveTo(Tuning.Home, Tuning.WalkSpeed, 60.0f);
			break;
		}
		// At its place with nothing to attend to: it lies down.
		StartRest(false);
		break;
	}
	case EEHWolfState::Rest:
	case EEHWolfState::Sleep:
	case EEHWolfState::Wander:
	{
		// Life at rest: lying with its head up, asleep, or wandering near its place, now and then. A friend nearby, or a
		// wary wolf crowded, gets up to attend to them; someone passing close wakes a sleeper for a moment.
		if (!Player.IsValid())
		{
			break;
		}
		const bool bCrowded = Band == EEHAlignBand::Neutral && !bOutside && !bShadow && Dist < Tuning.KeepDistance;
		const bool bFriendLeft = bFriend && Dist > Tuning.FollowDistance + 200.0f;   // a friend resting near the player gets up when they move off
		const bool bStrikeAtPlayer = Band != EEHAlignBand::Evil && !bOutside && !bShadow && Dummy.IsValid() && Dummy->IsWindingUp()
			&& FVector::Dist2D(Dummy->GetActorLocation(), Player->GetActorLocation()) < 400.0f && FVector::Dist2D(Dummy->GetActorLocation(), GetActorLocation()) < Tuning.ProtectRange;
		const bool bFriendNeeds = bFriend && ((bGreetDue && Dist < 450.0f)
			|| (Player->HealthFraction() < Tuning.BesideHealth && PlayerStillFor >= Tuning.BesideStill && Dist < 700.0f));
		if (bFriendLeft || bFriendNeeds || bCrowded || bStrikeAtPlayer)
		{
			Enter(EEHWolfState::Calm, 0);
			break;
		}
		if (State == EEHWolfState::Sleep && Dist < Tuning.NoticeRange)
		{
			// Lifts its head to see who passes, then settles again.
			RestLeft = FMath::FRandRange(4.0f, 8.0f);
			Enter(EEHWolfState::Rest, 0);
			break;
		}
		if (State == EEHWolfState::Wander)
		{
			MoveTo(WanderGoal, Tuning.WalkSpeed * 0.6f, 50.0f);
			if (FVector::Dist2D(GetActorLocation(), WanderGoal) < 70.0f || StateFrame > 60 * 25)
			{
				StartRest(false);
			}
			break;
		}
		if (Dist < Tuning.NoticeRange * 1.5f)
		{
			FaceTowards(Player->GetActorLocation(), 1.0f);
		}
		RestLeft -= Step;
		if (RestLeft <= 0.0f)
		{
			if (State == EEHWolfState::Sleep)
			{
				StartRest(false);
			}
			else if (!bFriend && FMath::FRand() < 0.45f)
			{
				// A slow walk to somewhere near its place (or back to it); a friend's wolf stays by the friend.
				FVector Goal = Tuning.Home;
				if (FVector::Dist2D(GetActorLocation(), Tuning.Home) < 150.0f)
				{
					const float A = FMath::FRandRange(0.0f, 2.0f * PI);
					Goal = Tuning.Home + FVector(FMath::Cos(A), FMath::Sin(A), 0.0f) * FMath::FRandRange(0.4f, 1.0f) * Tuning.WanderRadius;
					FNavLocation On;
					const UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
					Goal = Nav && Nav->ProjectPointToNavigation(FVector(Goal.X, Goal.Y, GetActorLocation().Z), On, FVector(150.0f, 150.0f, 300.0f)) ? On.Location : Tuning.Home;
				}
				WanderGoal = Goal;
				Enter(EEHWolfState::Wander, 0);
			}
			else
			{
				StartRest(true);
			}
		}
		break;
	}
	case EEHWolfState::Greet:
		if (Player.IsValid())
		{
			FaceTowards(Player->GetActorLocation(), 6.0f);
		}
		if (StateFrame >= StateLength)
		{
			Enter(EEHWolfState::Calm, 0);
		}
		break;
	case EEHWolfState::Beside:
	{
		// Lies down beside the hurt friend until they recover or move off.
		const bool bMovedOff = PlayerStillFor < 0.1f && StateFrame > 30;
		if (!Player.IsValid() || !bFriend || Player->HealthFraction() >= FMath::Min(1.0f, Tuning.BesideHealth + 0.15f) || bMovedOff)
		{
			Enter(EEHWolfState::Calm, 0);
			break;
		}
		if (Dist > 150.0f)
		{
			const FVector Side = FVector::CrossProduct(FVector::UpVector, To.GetSafeNormal());
			MoveTo(Player->GetActorLocation() + Side * 110.0f, Tuning.WalkSpeed, 30.0f);
		}
		else
		{
			Stop();
			FaceTowards(Player->GetActorLocation(), 2.0f);
		}
		break;
	}
	case EEHWolfState::Sanctuary:
	{
		// The player prays: whatever they are, the wolves stand guard nearby and go for anything that threatens them.
		if (!Player.IsValid() || bFrozen)
		{
			break;
		}
		if (TryProtect())
		{
			break;
		}
		if (FMath::Abs(Dist - Tuning.SanctuaryGuard) > 90.0f)
		{
			MoveTo(Player->GetActorLocation() - To.GetSafeNormal() * Tuning.SanctuaryGuard, Dist > 900.0f ? Tuning.RunSpeed : Tuning.WalkSpeed, 50.0f);
		}
		else
		{
			Stop();
			FaceTowards(GetActorLocation() - To, 2.0f);   // facing outward, watching over them
		}
		break;
	}
	case EEHWolfState::Warn:
	{
		// An evil aura (or a Shadow): hackles up, it holds off and warns. A Shadow is told to pray; anyone else is given
		// the chance to leave. Coming too close, or staying near too long, starts the fight (the director spreads it to
		// the pack); a Shadow that stays in the Chapel without praying runs out of patience (the director exorcises it).
		if (Want != EEHWolfState::Warn)
		{
			Enter(Want, 0);
			break;
		}
		if (!Player.IsValid() || bFrozen)
		{
			break;
		}
		if (bOutside)
		{
			if (FVector::Dist2D(GetActorLocation(), Tuning.Home) > 120.0f)
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
		if (bShadow)
		{
			WarnFor += Step;   // anywhere in the Chapel: only prayer is answer enough
		}
		else if (Dist < Tuning.WarnRange)
		{
			WarnFor += Step;
			if (GraceLeft <= 0.0f && (Dist < Tuning.WarnClose || WarnFor >= Tuning.WarnSeconds))
			{
				Escalate();
				Enter(EEHWolfState::Hostile, 0);
				break;
			}
		}
		else
		{
			WarnFor = FMath::Max(0.0f, WarnFor - Step * 0.5f);
		}
		if (Dist < Tuning.WarnRange + 300.0f && FMath::Abs(Dist - Tuning.WarnRadius) > 100.0f)
		{
			MoveTo(Player->GetActorLocation() - To.GetSafeNormal() * Tuning.WarnRadius, Tuning.WalkSpeed, 50.0f);
		}
		else if (Dist >= Tuning.WarnRange + 300.0f && FVector::Dist2D(GetActorLocation(), Tuning.Home) > 120.0f)
		{
			MoveTo(Tuning.Home, Tuning.WalkSpeed, 60.0f);
		}
		else
		{
			Stop();
		}
		FaceTowards(Player->GetActorLocation(), 5.0f);
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
		if (Want != EEHWolfState::Calm || StateFrame >= StateLength)
		{
			Enter(Want, 0);
		}
		break;
	}
	case EEHWolfState::Protect:
	{
		if (!Dummy.IsValid() || bFrozen)
		{
			Enter(Want, 0);
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
			Enter(Want, 0);
			Cooldown = Tuning.AttackCooldown;
		}
		if (StateFrame >= StateLength)
		{
			Enter(Want, 0);
		}
		break;
	}
	case EEHWolfState::Hostile:
	case EEHWolfState::Guarding:
	{
		if (Want != EEHWolfState::Hostile)
		{
			Enter(Want, 0);
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
		if (PackRole == EEHPackRole::HoldBack)
		{
			// One-on-one: another wolf is fighting; this one stands back and watches.
			if (FMath::Abs(Dist - HoldBackRadius) > 120.0f)
			{
				MoveTo(Player->GetActorLocation() - To.GetSafeNormal() * HoldBackRadius, Dist < HoldBackRadius ? Tuning.WalkSpeed * 1.3f : Tuning.RunSpeed, 60.0f);
			}
			else
			{
				Stop();
				FaceTowards(Player->GetActorLocation(), 4.0f);
			}
			break;
		}
		const bool bMayAttack = PackRole == EEHPackRole::Free || PackRole == EEHPackRole::Attacker;
		// Attack when ready (and when it is this wolf's turn): a bite up close, a lunge from range; otherwise circle at
		// a distance, changing direction. Waiting wolves keep circling just outside the bite.
		if (bMayAttack && Cooldown == 0 && Dist <= Tuning.BiteRange)
		{
			Stop();
			Enter(EEHWolfState::BiteWindup, Tuning.BiteWindup);
			break;
		}
		if (bMayAttack && Cooldown == 0 && Dist >= Tuning.LungeMin && Dist <= Tuning.LungeMax && FMath::FRand() < 0.04f)
		{
			Stop();
			Enter(EEHWolfState::LungeWindup, Tuning.LungeWindup);
			break;
		}
		if (!bMayAttack || Cooldown > 0 || Dist > Tuning.CircleRadius + 150.0f)
		{
			if (--CircleFrames <= 0)
			{
				CircleFrames = FMath::RandRange(70, 160);
				CircleSign = FMath::FRand() < 0.5f ? -1.0f : 1.0f;
			}
			if (PackRole == EEHPackRole::Waiting)
			{
				// Waiting its turn: circle a little wider, outside the distance that counts as surrounding the player,
				// at a place on the floor (between the pews the aisles are narrow).
				if (--WaitGoalFrames <= 0 || FVector::Dist2D(WaitGoal, Player->GetActorLocation()) < WaitRadius * 0.8f)
				{
					WaitGoalFrames = 10;
					WaitGoal = FindWaitSpot(WaitRadius);
				}
				MoveTo(WaitGoal, Dist > WaitRadius + 300.0f ? Tuning.RunSpeed : Tuning.WalkSpeed * 1.3f, 40.0f);
				break;
			}
			const float R = Tuning.CircleRadius;
			const FVector Dir = (-To).GetSafeNormal();
			const FVector Side = FVector::CrossProduct(FVector::UpVector, Dir) * CircleSign;
			const FVector Goal = Player->GetActorLocation() + (Dir * R + Side * 160.0f).GetSafeNormal() * R;
			MoveTo(Goal, Dist > R + 300.0f ? Tuning.RunSpeed : Tuning.WalkSpeed * 1.3f, 40.0f);
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
				if (Player->WasLastStrikeGuarded())
				{
					// Bitten into a guard: the jaws are knocked aside and the wolf is thrown back off balance.
					Rebuff();
					break;
				}
			}
			Enter(EEHWolfState::Recover, Tuning.BiteRecover);
			Cooldown = Tuning.AttackCooldown;
		}
		break;
	case EEHWolfState::LungeWindup:
		if (Player.IsValid())
		{
			FaceTowards(Player->GetActorLocation(), 12.0f);
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
			if (Player->WasLastStrikeGuarded())
			{
				Rebuff();
				break;
			}
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
			Enter(Want, 0);
		}
		break;
	case EEHWolfState::Hitstun:
		if (StateFrame >= StateLength)
		{
			Enter(Want, 0);
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
		Rig->SetRelativeLocation(FVector(0, 0, -76.0f + 36.0f * T));
		return;
	}
	const float Speed = GetVelocity().Size2D();
	const bool bAir = GetCharacterMovement()->IsFalling();
	// Walk cycle: diagonal legs together, faster and longer with speed.
	Gait += DeltaSeconds * (2.0f + Speed / 70.0f) * PI;
	const float Swing = FMath::Clamp(Speed / 500.0f, 0.0f, 1.0f) * 34.0f;
	const float Phase[4] = {0.0f, PI, PI, 0.0f};
	const float WantCrouch = (State == EEHWolfState::BiteWindup || State == EEHWolfState::LungeWindup) ? 1.0f : (State == EEHWolfState::Hostile ? 0.35f : 0.0f);
	Crouch = FMath::FInterpTo(Crouch, WantCrouch + (State == EEHWolfState::Warn ? 0.3f : 0.0f), DeltaSeconds, 12.0f);
	HeadThrust = FMath::FInterpTo(HeadThrust, 0.0f, DeltaSeconds, 7.0f);
	// Lying down (resting, asleep, beside a friend) once it has stopped; the head down asleep or bowed in greeting; the
	// hackles up when warning or fighting. Lying and rising take about half a second.
	const bool bLie = IsLying() && Speed < 30.0f;
	Lie = FMath::FInterpTo(Lie, bLie ? 1.0f : 0.0f, DeltaSeconds, bLie ? 4.0f : 7.0f);
	HeadDown = FMath::FInterpTo(HeadDown, State == EEHWolfState::Sleep ? 1.0f : (State == EEHWolfState::Greet ? 0.75f : 0.0f), DeltaSeconds, 5.0f);
	HacklesNow = FMath::FInterpTo(HacklesNow, (State == EEHWolfState::Warn || IsHostile()) ? 1.0f : 0.0f, DeltaSeconds, 6.0f);
	for (int32 i = 0; i < 4; ++i)
	{
		const float A = bAir ? (i < 2 ? -40.0f : 40.0f) : FMath::Sin(Gait + Phase[i]) * Swing;
		// Lying: the legs fold under the body.
		Legs[i]->SetRelativeRotation(FRotator(FMath::Lerp(A, i < 2 ? -78.0f : 72.0f, Lie), 0, 0));
	}
	// Body: a bob in the stride, low and forward when stalking or winding up.
	const float Bob = FMath::Abs(FMath::Sin(Gait)) * FMath::Clamp(Speed / 500.0f, 0.0f, 1.0f) * 3.0f;
	// The hit reaction's springs: a stiff, quick settle, slightly under-damped so a heavy blow rocks it once.
	auto SpringStep = [DeltaSeconds](FVector2D& X, FVector2D& Vel, float K, float C) {
		const FVector2D Acc = -X * K - Vel * C;
		Vel += Acc * DeltaSeconds;
		X += Vel * DeltaSeconds;
	};
	SpringStep(Tilt, TiltVel, 150.0f, 10.0f);
	SpringStep(Snap, SnapVel, 220.0f, 13.0f);
	PeakTilt = FMath::Max(PeakTilt, Tilt.Size());
	Body->SetRelativeLocation(FVector(0, 0, 124.0f - 20.0f * Crouch - 74.0f * Lie + Bob * 1.4f - 0.35f * FMath::Abs(Tilt.X)));
	Body->SetRelativeRotation(FRotator(-6.0f * Crouch + Tilt.X, 0, Tilt.Y));
	// Ceremonial mane & hackles: flare and rise dramatically in warning or hostility.
	Body->SetRelativeScale3D(FVector(1.0f, 1.0f + 0.03f * HacklesNow, 1.0f + 0.04f * HacklesNow));
	Mane->SetRelativeLocation(FVector(46.0f, 0.0f, 14.0f + 7.0f * HacklesNow));
	Mane->SetRelativeRotation(FRotator(10.0f * HacklesNow, 0.0f, 0.0f));
	Mane->SetRelativeScale3D(FVector(1.0f + 0.06f * HacklesNow, 1.0f + 0.18f * HacklesNow, 1.0f + 0.24f * HacklesNow));
	// Head: looks at the player; low when hostile, up when friendly; snaps forward in a bite.
	float Yaw = 0.0f;
	if (Player.IsValid())
	{
		const FVector Local = GetActorTransform().InverseTransformVectorNoScale(ToPlayer2D());
		Yaw = FMath::Clamp(FMath::RadiansToDegrees(FMath::Atan2(Local.Y, Local.X)), -55.0f, 55.0f);
	}
	if (State == EEHWolfState::Sleep)
	{
		Yaw *= 1.0f - HeadDown;
	}
	const bool bFriendly = IsCalmLike() && !bShadow && EHAlign::Band(Alignment) == EEHAlignBand::Good;
	const float Pitch = FMath::Lerp(bFriendly ? 8.0f : ((IsHostile() || State == EEHWolfState::Warn) ? -14.0f : 0.0f), -34.0f, HeadDown);
	Head->SetRelativeLocation(FVector(88.0f + 24.0f * HeadThrust, 0, 14.0f - 14.0f * Crouch - 16.0f * HeadDown));
	Head->SetRelativeRotation(FRotator(Pitch - 18.0f * HeadThrust + Snap.X, Yaw + Snap.Y, 0));
	// Tail: wags for a friend, hangs for a wary wolf, straight out and stiff when hostile.
	WagTime += DeltaSeconds;
	const float Wag = State == EEHWolfState::Sleep ? 0.0f : (State == EEHWolfState::Greet ? 1.4f : 1.0f);
	const float TailYaw = bFriendly ? FMath::Sin(WagTime * (State == EEHWolfState::Greet ? 15.0f : 11.0f)) * 28.0f * Wag : 0.0f;
	// Low when relaxed, out and stiff when warning or hostile, along the floor when lying.
	const float TailPitch = FMath::Lerp(bFriendly ? 22.0f : ((IsHostile() || State == EEHWolfState::Warn) ? 16.0f : -10.0f), -24.0f, Lie);
	Tail->SetRelativeRotation(FRotator(TailPitch, TailYaw, 0));
}

FString AEHWolf::Describe() const
{
	return FString::Printf(TEXT("%s hp=%.0f provoked=%d escalated=%d warned=%.1fs frozen=%.1f bites=%d lunges=%d connected=%d disengaged=%d absorbed=%d protects=%d"),
		EHWolfStateName(State), HealthNow, bProvoked ? 1 : 0, bEscalated ? 1 : 0, WarnFor, FrozenLeft, BiteCount, LungeCount, ConnectCount, DisengageCount, AbsorbCount, ProtectCount);
}

void AEHWolf::React(const FVector& Away, float Strength)
{
	// Away from the blow, in the wolf's own frame: X forward, Y right. Pushed from the front it rears (pitch up) and
	// the head snaps back; from the side it rolls away and the head snaps aside.
	const FVector L = GetActorTransform().InverseTransformVectorNoScale(Away);
	TiltVel += FVector2D(L.X * 430.0f, -L.Y * 400.0f) * Strength;
	PeakTilt = 0.0f;
	SnapVel += FVector2D(L.X * 520.0f, L.Y * 900.0f) * Strength;
	++Reactions;
}

void AEHWolf::Rebuff()
{
	++Rebuffs;
	HeadThrust = 0.0f;
	if (Player.IsValid())
	{
		FVector Back = GetActorLocation() - Player->GetActorLocation();
		Back.Z = 0.0f;
		if (FrozenLeft <= 0.0f)
		{
			LaunchCharacter(Back.GetSafeNormal() * 360.0f + FVector(0, 0, 60.0f), true, false);
		}
		React(Back.GetSafeNormal(), 0.8f);
	}
	Enter(EEHWolfState::Recover, Tuning.BiteRecover + 16);
	Cooldown = Tuning.AttackCooldown;
}
