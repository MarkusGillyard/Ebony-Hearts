#include "EHTrainingDummy.h"

#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "EHAnimInstance.h"
#include "EHPlayerCharacter.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace EHDummyDetail
{
constexpr float Step = 1.0f / 60.0f;
// Ashka's jab connects on its frame 8. The wind-up stretches its first 3 frames (a readable load), then plays the
// rest of the way to contact at full speed.
constexpr int32 StrikeLoadAnimFrames = 3;
constexpr int32 StrikeContactAnimFrame = 8;
}
using namespace EHDummyDetail;

const TCHAR* EHDummyModeName(EEHDummyMode Mode)
{
	switch (Mode)
	{
	case EEHDummyMode::Guard: return TEXT("Guard");
	case EEHDummyMode::Strikes: return TEXT("Strikes back");
	default: return TEXT("Stand");
	}
}

bool FEHDummyTuning::Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError)
{
	if (!Obj.IsValid())
	{
		return true;
	}
	bool bOk = true;
	auto Num = [&](const TCHAR* Name, float& Out, float Min, float Max) {
		double V = 0.0;
		if (Obj->TryGetNumberField(Name, V))
		{
			if (V < Min || V > Max)
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: dummy.%s = %g is outside %g..%g."), Name, V, Min, Max);
				bOk = false;
				return;
			}
			Out = static_cast<float>(V);
		}
	};
	auto Int = [&](const TCHAR* Name, int32& Out, int32 Min, int32 Max) {
		float V = static_cast<float>(Out);
		Num(Name, V, static_cast<float>(Min), static_cast<float>(Max));
		Out = FMath::RoundToInt(V);
	};
	Num(TEXT("strikeDamage"), StrikeDamage, 0, 1000);
	Int(TEXT("windupFrames"), WindupFrames, StrikeContactAnimFrame - StrikeLoadAnimFrames + 1, 120);
	Int(TEXT("strikeRecovery"), StrikeRecovery, 1, 120);
	Int(TEXT("strikeCooldown"), StrikeCooldown, 0, 600);
	Num(TEXT("strikeRange"), StrikeRange, 50, 500);
	Num(TEXT("strikeReach"), StrikeReach, 50, 500);
	Num(TEXT("strikeArc"), StrikeArc, 5, 180);
	Int(TEXT("hitstunLight"), HitstunLight, 1, 120);
	Int(TEXT("hitstunHeavy"), HitstunHeavy, 1, 120);
	Int(TEXT("blockstun"), Blockstun, 1, 120);
	Num(TEXT("turnRate"), TurnRate, 0, 2000);
	Num(TEXT("spawnYaw"), SpawnYaw, -360, 360);
	const TArray<TSharedPtr<FJsonValue>>* SpawnArr = nullptr;
	if (Obj->TryGetArrayField(TEXT("spawn"), SpawnArr) && SpawnArr->Num() == 3)
	{
		Spawn = FVector((*SpawnArr)[0]->AsNumber(), (*SpawnArr)[1]->AsNumber(), (*SpawnArr)[2]->AsNumber());
	}
	return bOk;
}

AEHTrainingDummy::AEHTrainingDummy(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
	PrimaryActorTick.bCanEverTick = true;
	AutoPossessAI = EAutoPossessAI::Disabled;
	GetCapsuleComponent()->InitCapsuleSize(34.0f, 90.0f);
	GetCapsuleComponent()->SetCollisionProfileName(TEXT("Pawn"));
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetMesh()->SetRelativeLocationAndRotation(FVector(0, 0, -90.0f), FRotator(0, -90.0f, 0));
	GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	GetCharacterMovement()->GravityScale = 1.0f;
	GetCharacterMovement()->bRunPhysicsWithNoController = true;
	GetCharacterMovement()->bOrientRotationToMovement = false;
	bUseControllerRotationYaw = false;
}

void AEHTrainingDummy::BeginPlay()
{
	Super::BeginPlay();
	auto Seq = [](const TCHAR* Name) {
		return LoadObject<UAnimSequence>(nullptr, *FString::Printf(TEXT("/Game/Characters/Ashka/Anims/A_Ashka_%s.A_Ashka_%s"), Name, Name), nullptr, LOAD_NoWarn | LOAD_Quiet);
	};
	if (USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/Ashka/SK_Ashka.SK_Ashka"), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		GetMesh()->SetSkeletalMesh(Mesh);
		GetMesh()->SetAnimInstanceClass(UEHAnimInstance::StaticClass());
		AnimIdle = Seq(TEXT("Idle"));
		AnimGuard = Seq(TEXT("Guard"));
		AnimHitLight = Seq(TEXT("HitLight"));
		// Reactions that end back in the stance (the slice's heavy reaction is a knockdown).
		AnimHitHeavy = Seq(TEXT("HitHeadMedium"));
		AnimHitBody = Seq(TEXT("HitBody"));
		AnimBlockHit = Seq(TEXT("BlockHit"));
		AnimStrike = Seq(TEXT("L1"));
	}
}

bool AEHTrainingDummy::HasModel() const
{
	return GetMesh()->GetSkeletalMeshAsset() != nullptr && AnimIdle != nullptr;
}

UEHAnimInstance* AEHTrainingDummy::Anim() const
{
	return Cast<UEHAnimInstance>(GetMesh()->GetAnimInstance());
}

void AEHTrainingDummy::Setup(const FEHDummyTuning& InTuning, const FEHFistTuning& InFists, AEHPlayerCharacter* InPlayer)
{
	Tuning = InTuning;
	Fists = InFists;
	Player = InPlayer;
	ResetDummy();
}

void AEHTrainingDummy::ResetDummy()
{
	GetCharacterMovement()->StopMovementImmediately();
	TeleportTo(Tuning.Spawn + FVector(0, 0, 92.0f), FRotator(0, Tuning.SpawnYaw, 0), false, true);
	State = EState::Idle;
	StateFrame = 0;
	StateLength = 0;
	Hitstop = 0;
	Cooldown = 60;
	PushLeft = 0;
	Accum = 0.0f;
	HitCount = 0;
	BlockCount = 0;
	StrikeCount = 0;
	Total = 0.0f;
	SinceHit = 100.0f;
	Last.Reset();
	ShownSeq = nullptr;
}

void AEHTrainingDummy::SetMode(EEHDummyMode InMode)
{
	Mode = InMode;
	if (State == EState::Windup || State == EState::Recover)
	{
		Enter(EState::Idle, 0);
	}
	Cooldown = 60;
}

FString AEHTrainingDummy::StateName() const
{
	switch (State)
	{
	case EState::Hit: return TEXT("hit");
	case EState::Blocked: return TEXT("blocked");
	case EState::Pushed: return TEXT("pushed");
	case EState::Windup: return TEXT("windup");
	case EState::Recover: return TEXT("recover");
	default: return TEXT("idle");
	}
}

FVector AEHTrainingDummy::LabelLocation() const
{
	return GetActorLocation() + FVector(0, 0, 115.0f);
}

FVector AEHTrainingDummy::ToPlayer2D() const
{
	if (!Player.IsValid())
	{
		return FVector::ZeroVector;
	}
	FVector D = Player->GetActorLocation() - GetActorLocation();
	D.Z = 0.0f;
	return D;
}

void AEHTrainingDummy::Enter(EState Next, int32 Length)
{
	State = Next;
	StateFrame = 0;
	StateLength = Length;
}

FEHDummyHit AEHTrainingDummy::ReceiveHit(EEHFistAction Action, const FEHStrikeDef& Def, const FVector& From, const FVector& At)
{
	FEHDummyHit Out;
	Out.Action = Action;
	Out.Location = At;
	LastAction = Action;
	// A guard covers the front: the attacker must be within the guard's angle of where the dummy faces.
	FVector ToAttacker = From - GetActorLocation();
	ToAttacker.Z = 0.0f;
	const float Angle = FMath::RadiansToDegrees(FMath::Acos(FVector::DotProduct(ToAttacker.GetSafeNormal(), GetActorForwardVector())));
	Out.bBlocked = Mode == EEHDummyMode::Guard && Angle <= Fists.BlockAngle && State != EState::Hit && State != EState::Pushed;
	Out.Damage = Out.bBlocked ? Def.Damage * (1.0f - Fists.BlockReduction) : Def.Damage;
	Total += Out.Damage;
	SinceHit = 0.0f;
	Hitstop = Def.Hitstop;
	if (Out.bBlocked)
	{
		++BlockCount;
		Enter(EState::Blocked, Tuning.Blockstun);
	}
	else
	{
		++HitCount;
		// A hit interrupts a strike in its wind-up: that is the jab's job.
		Enter(Action == EEHFistAction::Shove ? EState::Pushed : EState::Hit, Action == EEHFistAction::Straight ? Tuning.HitstunHeavy : Tuning.HitstunLight);
	}
	if (Action == EEHFistAction::Shove && Def.Push > 0.0f && Def.PushFrames > 0)
	{
		FVector Dir = GetActorLocation() - From;
		Dir.Z = 0.0f;
		PushPerFrame = Dir.GetSafeNormal() * (Def.Push / Def.PushFrames);
		PushLeft = Def.PushFrames;
		if (State == EState::Pushed)
		{
			StateLength = FMath::Max(StateLength, Def.PushFrames + 4);
		}
	}
	Last = Out.bBlocked ? FString::Printf(TEXT("%s blocked: %.1f"), EHFistActionName(Action), Out.Damage)
		: (Out.Damage > 0.0f ? FString::Printf(TEXT("%s: %.0f"), EHFistActionName(Action), Out.Damage) : FString(EHFistActionName(Action)));
	if (Out.bBlocked == false && Cooldown < 30)
	{
		Cooldown = 30;   // a strike never comes straight out of a hit
	}
	return Out;
}

void AEHTrainingDummy::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	SinceHit += DeltaSeconds;
	Accum = FMath::Min(Accum + DeltaSeconds, 0.25f);
	while (Accum >= Step)
	{
		Accum -= Step;
		StepFrame();
	}
	UpdateAnimation();
}

void AEHTrainingDummy::StepFrame()
{
	if (Hitstop > 0)
	{
		--Hitstop;
		return;
	}
	if (PushLeft > 0)
	{
		FHitResult Hit;
		AddActorWorldOffset(PushPerFrame, true, &Hit);
		if (Hit.bBlockingHit)
		{
			// Slide along whatever stopped it (a pier, a pew) instead of sticking to it.
			const FVector Slide = FVector::VectorPlaneProject(PushPerFrame * (1.0f - Hit.Time), Hit.Normal);
			AddActorWorldOffset(FVector(Slide.X, Slide.Y, 0.0f), true);
		}
		--PushLeft;
	}
	if (Cooldown > 0)
	{
		--Cooldown;
	}
	const bool bReacting = State == EState::Hit || State == EState::Blocked || State == EState::Pushed;
	// Turn toward the player except while reeling.
	const FVector To = ToPlayer2D();
	if (!bReacting && !To.IsNearlyZero())
	{
		const float Want = To.Rotation().Yaw;
		const float Yaw = FMath::FixedTurn(GetActorRotation().Yaw, Want, Tuning.TurnRate * Step);
		SetActorRotation(FRotator(0.0f, Yaw, 0.0f));
	}
	++StateFrame;
	switch (State)
	{
	case EState::Idle:
		if (Mode == EEHDummyMode::Strikes && Cooldown == 0 && Player.IsValid() && To.Size() <= Tuning.StrikeRange)
		{
			const float Off = FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw, To.Rotation().Yaw));
			if (Off <= Tuning.StrikeArc)
			{
				Enter(EState::Windup, Tuning.WindupFrames);
			}
		}
		break;
	case EState::Windup:
		if (StateFrame >= StateLength)
		{
			++StrikeCount;
			const float Off = FMath::Abs(FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw, To.Rotation().Yaw));
			if (Player.IsValid() && To.Size() <= Tuning.StrikeReach && Off <= Tuning.StrikeArc)
			{
				Player->ReceiveStrike(Tuning.StrikeDamage, GetActorLocation() + FVector(0, 0, 60.0f));
			}
			Enter(EState::Recover, Tuning.StrikeRecovery);
			Cooldown = Tuning.StrikeCooldown;
		}
		break;
	default:
		if (StateFrame >= StateLength && PushLeft == 0)
		{
			Enter(EState::Idle, 0);
		}
		break;
	}
}

void AEHTrainingDummy::UpdateAnimation()
{
	UEHAnimInstance* A = Anim();
	if (A == nullptr || AnimIdle == nullptr)
	{
		return;
	}
	UAnimSequence* Seq = AnimIdle;
	double Time = 0.0;
	const double F = static_cast<double>(StateFrame) + (Hitstop > 0 ? 0.0 : Accum / Step);
	auto Looped = [](UAnimSequence* S, double T) { const double L = FMath::Max(0.01, static_cast<double>(S->GetPlayLength())); return FMath::Fmod(T, L); };
	auto Spread = [](UAnimSequence* S, double Frame, int32 Length) {
		const double L = static_cast<double>(S->GetPlayLength());
		return FMath::Clamp(Frame / FMath::Max(1, Length), 0.0, 1.0) * L * 0.98;
	};
	switch (State)
	{
	case EState::Hit:
		Seq = LastAction == EEHFistAction::Straight && AnimHitHeavy ? AnimHitHeavy.Get() : (AnimHitLight ? AnimHitLight.Get() : AnimIdle.Get());
		Time = Spread(Seq, F, StateLength);
		break;
	case EState::Pushed:
		Seq = AnimHitBody ? AnimHitBody.Get() : AnimIdle.Get();
		Time = Spread(Seq, F, StateLength);
		break;
	case EState::Blocked:
		Seq = AnimBlockHit ? AnimBlockHit.Get() : AnimIdle.Get();
		Time = Spread(Seq, F, StateLength);
		break;
	case EState::Windup:
	case EState::Recover:
		if (AnimStrike)
		{
			Seq = AnimStrike;
			double AnimFrame = 0.0;
			if (State == EState::Windup)
			{
				const int32 Load = Tuning.WindupFrames - (StrikeContactAnimFrame - StrikeLoadAnimFrames);
				AnimFrame = F < Load ? F * StrikeLoadAnimFrames / FMath::Max(1, Load) : StrikeLoadAnimFrames + (F - Load);
			}
			else
			{
				const double Rest = static_cast<double>(AnimStrike->GetPlayLength()) * 60.0 - StrikeContactAnimFrame;
				AnimFrame = StrikeContactAnimFrame + F * Rest / FMath::Max(1, Tuning.StrikeRecovery);
			}
			Time = FMath::Min(AnimFrame / 60.0, static_cast<double>(AnimStrike->GetPlayLength()) * 0.99);
		}
		break;
	default:
		Seq = Mode == EEHDummyMode::Stand ? AnimIdle.Get() : (AnimGuard ? AnimGuard.Get() : AnimIdle.Get());
		Time = Looped(Seq, GetWorld()->GetTimeSeconds());
		break;
	}
	A->SetSample(Seq, Time);
	if (Seq != ShownSeq)
	{
		A->BeginTransition(ShownSeq == nullptr ? 0.0f : 0.1f);
		ShownSeq = Seq;
	}
}
