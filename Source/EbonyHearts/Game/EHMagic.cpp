#include "EHMagic.h"

#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EHTrainingDummy.h"
#include "EHVfx.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"

bool FEHMagicTuning::Load(const TSharedPtr<FJsonObject>& Root, FString& OutError)
{
	if (!Root.IsValid())
	{
		return true;
	}
	bool bOk = true;
	auto Num = [&](const TSharedPtr<FJsonObject>& O, const TCHAR* Path, const TCHAR* Name, float& Out, float Min, float Max) {
		double V = 0.0;
		if (!O.IsValid() || !O->TryGetNumberField(Name, V))
		{
			return;
		}
		if (V < Min || V > Max)
		{
			OutError = FString::Printf(TEXT("Data/firstperson.json: %s%s = %g is outside %g..%g."), Path, Name, V, Min, Max);
			bOk = false;
			return;
		}
		Out = static_cast<float>(V);
	};
	auto Int = [&](const TSharedPtr<FJsonObject>& O, const TCHAR* Path, const TCHAR* Name, int32& Out, int32 Min, int32 Max) {
		float V = static_cast<float>(Out);
		Num(O, Path, Name, V, static_cast<float>(Min), static_cast<float>(Max));
		Out = FMath::RoundToInt(V);
	};
	auto Obj = [&](const TCHAR* Name) {
		const TSharedPtr<FJsonObject>* O = nullptr;
		return Root->TryGetObjectField(Name, O) ? *O : TSharedPtr<FJsonObject>();
	};
	const TSharedPtr<FJsonObject> St = Obj(TEXT("stats"));
	Num(St, TEXT("stats."), TEXT("health"), Stats.Health, 1, 10000);
	Num(St, TEXT("stats."), TEXT("qhi"), Stats.Qhi, 1, 10000);
	Num(St, TEXT("stats."), TEXT("stamina"), Stats.Stamina, 1, 10000);
	Int(St, TEXT("stats."), TEXT("intelligence"), Stats.Intelligence, 0, 99);
	Int(St, TEXT("stats."), TEXT("faith"), Stats.Faith, 0, 99);
	Int(St, TEXT("stats."), TEXT("dexterity"), Stats.Dexterity, 0, 99);
	Int(St, TEXT("stats."), TEXT("martialProwess"), Stats.MartialProwess, 0, 99);
	Int(St, TEXT("stats."), TEXT("base"), StatBase, 0, 99);
	Num(St, TEXT("stats."), TEXT("qhiRegenPerSecond"), QhiRegenPerSecond, 0, 1000);
	Num(St, TEXT("stats."), TEXT("qhiRegenPerPoint"), QhiRegenPerPoint, 0, 1);
	Num(St, TEXT("stats."), TEXT("qhiRegenDelay"), QhiRegenDelay, 0, 10);
	Num(St, TEXT("stats."), TEXT("qhiPerStrike"), QhiPerStrike, 0, 1000);
	Num(St, TEXT("stats."), TEXT("staminaPerDexterity"), StaminaPerDexterity, 0, 1);
	Num(St, TEXT("stats."), TEXT("physicalPerProwess"), PhysicalPerProwess, 0, 1);
	const TSharedPtr<FJsonObject> F = Obj(TEXT("fireball"));
	Num(F, TEXT("fireball."), TEXT("cost"), FireballCost, 0, 10000);
	Num(F, TEXT("fireball."), TEXT("damage"), FireballDamage, 0, 10000);
	Num(F, TEXT("fireball."), TEXT("speed"), FireballSpeed, 100, 20000);
	Num(F, TEXT("fireball."), TEXT("radius"), FireballRadius, 1, 200);
	Num(F, TEXT("fireball."), TEXT("range"), FireballRange, 100, 20000);
	Num(F, TEXT("fireball."), TEXT("hitstop"), FireballHitstop, 0, 30);
	const TSharedPtr<FJsonObject> W = Obj(TEXT("iceWall"));
	Num(W, TEXT("iceWall."), TEXT("cost"), IceWallCost, 0, 10000);
	Num(W, TEXT("iceWall."), TEXT("seconds"), IceWallSeconds, 0.5f, 120);
	Num(W, TEXT("iceWall."), TEXT("distance"), IceWallDistance, 80, 1000);
	Num(W, TEXT("iceWall."), TEXT("minDistance"), IceWallMinDistance, 60, 1000);
	Num(W, TEXT("iceWall."), TEXT("width"), IceWallWidth, 50, 2000);
	Num(W, TEXT("iceWall."), TEXT("height"), IceWallHeight, 50, 1000);
	Num(W, TEXT("iceWall."), TEXT("thickness"), IceWallThickness, 5, 200);
	Num(W, TEXT("iceWall."), TEXT("riseSeconds"), IceWallRiseSeconds, 0.02f, 5);
	Num(W, TEXT("iceWall."), TEXT("meltSeconds"), IceWallMeltSeconds, 0.02f, 5);
	Num(W, TEXT("iceWall."), TEXT("health"), IceWallHealth, 1, 10000);
	Num(W, TEXT("iceWall."), TEXT("freezeRadius"), FreezeRadius, 0, 2000);
	Num(W, TEXT("iceWall."), TEXT("freezeSeconds"), FreezeSeconds, 0, 30);
	return bOk;
}

FString FEHMagicTuning::Describe() const
{
	return FString::Printf(TEXT("stats health=%.0f qhi=%.0f stamina=%.0f int=%d faith=%d dex=%d martial=%d base=%d; qhi regen=%.1f/s +%.0f%%/pt after %.1fs, per strike=%.0f; "
		"stamina +%.0f%%/dex; physical +%.0f%%/martial; fireball cost=%.0f dmg=%.0f speed=%.0f r=%.0f range=%.0f stop=%.0f; "
		"ice wall cost=%.0f %.1fs at %.0f (min %.0f) %.0fx%.0fx%.0f rise=%.2fs melt=%.2fs hp=%.0f freeze r=%.0f %.1fs"),
		Stats.Health, Stats.Qhi, Stats.Stamina, Stats.Intelligence, Stats.Faith, Stats.Dexterity, Stats.MartialProwess, StatBase,
		QhiRegenPerSecond, QhiRegenPerPoint * 100.0f, QhiRegenDelay, QhiPerStrike, StaminaPerDexterity * 100.0f, PhysicalPerProwess * 100.0f,
		FireballCost, FireballDamage, FireballSpeed, FireballRadius, FireballRange, FireballHitstop,
		IceWallCost, IceWallSeconds, IceWallDistance, IceWallMinDistance, IceWallWidth, IceWallHeight, IceWallThickness, IceWallRiseSeconds,
		IceWallMeltSeconds, IceWallHealth, FreezeRadius, FreezeSeconds);
}

float FEHMagicTuning::QhiRegen(const FEHPlayerStats& S) const
{
	const float Points = static_cast<float>(S.Intelligence - StatBase) + static_cast<float>(S.Faith - StatBase);
	return FMath::Max(0.0f, QhiRegenPerSecond * (1.0f + QhiRegenPerPoint * Points));
}

float FEHMagicTuning::StaminaScale(const FEHPlayerStats& S) const
{
	return FMath::Max(0.0f, 1.0f + StaminaPerDexterity * static_cast<float>(S.Dexterity - StatBase));
}

float FEHMagicTuning::PhysicalScale(const FEHPlayerStats& S) const
{
	return FMath::Max(0.0f, 1.0f + PhysicalPerProwess * static_cast<float>(S.MartialProwess - StatBase));
}

float FEHWater::DepthAt(const UWorld* World, const FVector& At, const AActor* Ignore) const
{
	if (World == nullptr || !Bounds.IsInside(FVector2D(At.X, At.Y)))
	{
		return 0.0f;
	}
	FHitResult Hit;
	FCollisionQueryParams Params(TEXT("EHWater"), false, Ignore);
	const FVector From(At.X, At.Y, SurfaceZ + 60.0f);
	if (!World->LineTraceSingleByObjectType(Hit, From, From - FVector(0, 0, 300.0f), FCollisionObjectQueryParams(ECC_WorldStatic), Params))
	{
		return 0.0f;
	}
	return FMath::Max(0.0f, SurfaceZ - Hit.ImpactPoint.Z);
}

namespace EHMagicDetail
{
UMaterialInterface* IceMaterial()
{
	UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Magic/M_PH_Ice.M_PH_Ice"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	return M ? M : LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
}
}
using namespace EHMagicDetail;

AEHFireball::AEHFireball()
{
	PrimaryActorTick.bCanEverTick = true;
	Core = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Core"));
	RootComponent = Core;
	Core->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Core->SetCastShadow(false);
	Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
	Light->SetupAttachment(Core);
	Light->SetCastShadows(false);
	Light->SetIntensityUnits(ELightUnits::Candelas);
	Light->SetIntensity(60.0f);
	Light->SetAttenuationRadius(650.0f);
	Light->SetLightColor(FLinearColor(1.0f, 0.42f, 0.12f));
}

void AEHFireball::Launch(const FEHMagicTuning& InTuning, AActor* InCaster, AEHVfx* InVfx, const FVector& Direction)
{
	Tuning = InTuning;
	Caster = InCaster;
	Vfx = InVfx;
	Velocity = Direction.GetSafeNormal() * Tuning.FireballSpeed;
	// A hot glowing core (placeholder): a glow card that always faces the eyes; glow sprites trail it.
	if (UStaticMesh* Quad = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane")))
	{
		Core->SetStaticMesh(Quad);
		if (UMaterialInterface* Add = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/VFX/M_VFX_Additive.M_VFX_Additive"), nullptr, LOAD_NoWarn | LOAD_Quiet))
		{
			CoreMaterial = UMaterialInstanceDynamic::Create(Add, this);
			if (UTexture* Glow = LoadObject<UTexture>(nullptr, TEXT("/Game/VFX/T_FX_Glow.T_FX_Glow"), nullptr, LOAD_NoWarn | LOAD_Quiet))
			{
				CoreMaterial->SetTextureParameterValue(TEXT("Tex"), Glow);
			}
			CoreMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.0f, 0.62f, 0.26f));
			CoreMaterial->SetScalarParameterValue(TEXT("Intensity"), 7.0f);
			Core->SetMaterial(0, CoreMaterial);
		}
		Core->SetWorldScale3D(FVector(Tuning.FireballRadius * 4.0f / 100.0f));
	}
}

void AEHFireball::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (State != EResult::Flying)
	{
		return;
	}
	// Swept each frame against characters, the ice and the Chapel; the caster is never hit.
	const FVector From = GetActorLocation();
	const FVector Step = Velocity * DeltaSeconds;
	FCollisionQueryParams Params(TEXT("EHFireball"), false, this);
	if (Caster.IsValid())
	{
		Params.AddIgnoredActor(Caster.Get());
	}
	FCollisionObjectQueryParams Objects;
	Objects.AddObjectTypesToQuery(ECC_WorldStatic);
	Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
	Objects.AddObjectTypesToQuery(ECC_Pawn);
	FHitResult Hit;
	if (GetWorld()->SweepSingleByObjectType(Hit, From, From + Step, FQuat::Identity, Objects, FCollisionShape::MakeSphere(Tuning.FireballRadius), Params))
	{
		HitAt = Hit.ImpactPoint;
		SetActorLocation(Hit.Location);
		if (AEHTrainingDummy* D = Cast<AEHTrainingDummy>(Hit.GetActor()))
		{
			HitTarget = D;
			State = EResult::Target;
		}
		else if (AEHIceWall* W = Cast<AEHIceWall>(Hit.GetActor()))
		{
			HitWall = W;
			State = EResult::Wall;
		}
		else
		{
			State = EResult::World;
		}
		Core->SetVisibility(false);
		Light->SetVisibility(false);
		return;
	}
	SetActorLocation(From + Step);
	Travelled += Step.Size();
	TrailTimer -= DeltaSeconds;
	while (TrailTimer <= 0.0f && Vfx.IsValid())
	{
		TrailTimer += 1.0f / 60.0f;
		Vfx->FireTrail(GetActorLocation() - Velocity * TrailTimer);
	}
	if (const APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		if (PC->PlayerCameraManager)
		{
			const FVector ToEye = PC->PlayerCameraManager->GetCameraLocation() - GetActorLocation();
			Core->SetWorldRotation(FRotationMatrix::MakeFromZ(ToEye.GetSafeNormal()).Rotator());
		}
	}
	Light->SetIntensity(55.0f + 15.0f * FMath::Sin(GetWorld()->GetTimeSeconds() * 37.0f));
	if (Travelled >= Tuning.FireballRange)
	{
		State = EResult::Expired;
		HitAt = GetActorLocation();
		Core->SetVisibility(false);
		Light->SetVisibility(false);
	}
}

AEHIceWall::AEHIceWall()
{
	PrimaryActorTick.bCanEverTick = true;
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Block"));
	RootComponent = Box;
	// Blocks everything that moves, and the view traces that strikes use; it can affect navigation once wolves walk.
	// A dynamic object, so floor and water probes (static geometry only) never take it for the floor.
	Box->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Box->SetCanEverAffectNavigation(true);
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Ice"));
	Mesh->SetupAttachment(Box);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetCanEverAffectNavigation(false);
	Sheet = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("FrozenWater"));
	Sheet->SetupAttachment(Box);
	Sheet->SetUsingAbsoluteRotation(true);
	Sheet->SetUsingAbsoluteScale(true);
	Sheet->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Sheet->SetCastShadow(false);
	Sheet->SetCanEverAffectNavigation(false);
	Sheet->SetVisibility(false);
}

const TCHAR* AEHIceWall::PhaseName() const
{
	switch (Phase)
	{
	case EPhase::Rising: return TEXT("rising");
	case EPhase::Standing: return TEXT("standing");
	case EPhase::Melting: return TEXT("melting");
	default: return TEXT("done");
	}
}

void AEHIceWall::Raise(const FEHMagicTuning& InTuning, const FEHWater& InWater, const FVector& Base, const FVector& Facing, const TArray<AEHTrainingDummy*>& InOpponents)
{
	Tuning = InTuning;
	Water = InWater;
	HealthValue = Tuning.IceWallHealth;
	for (AEHTrainingDummy* D : InOpponents)
	{
		Opponents.Add(D);
	}
	// The wall stands across the line of the cast, sunk 10 cm into the floor so no light shows under it.
	FVector F = Facing;
	F.Z = 0.0f;
	SetActorLocationAndRotation(Base + FVector(0, 0, Tuning.IceWallHeight * 0.5f - 10.0f), F.Rotation());
	Box->SetBoxExtent(FVector(Tuning.IceWallThickness * 0.5f, Tuning.IceWallWidth * 0.5f, Tuning.IceWallHeight * 0.5f));
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMesh* Disc = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	UMaterialInterface* Ice = IceMaterial();
	if (Cube)
	{
		Mesh->SetStaticMesh(Cube);
		Mesh->SetMaterial(0, Ice);
	}
	// Water within reach freezes into a sheet just above the surface, for as long as anything caught stays trapped.
	const FVector Feet(Base.X, Base.Y, Base.Z);
	bSheet = Tuning.FreezeRadius > 0.0f && Water.DepthAt(GetWorld(), Feet, this) > 0.5f;
	if (bSheet && Disc)
	{
		Sheet->SetStaticMesh(Disc);
		// The frozen water is thinner and darker than the wall: a sheen on the surface rather than a slab.
		UMaterialInstanceDynamic* Thin = UMaterialInstanceDynamic::Create(Ice, this);
		Thin->SetScalarParameterValue(TEXT("Opacity"), 0.35f);
		Thin->SetScalarParameterValue(TEXT("Glow"), 0.25f);
		Sheet->SetMaterial(0, Thin);
		Sheet->SetWorldLocationAndRotation(FVector(Base.X, Base.Y, Water.SurfaceZ + 0.6f), FRotator::ZeroRotator);
		Sheet->SetWorldScale3D(FVector(Tuning.FreezeRadius * 2.0f / 100.0f, Tuning.FreezeRadius * 2.0f / 100.0f, 0.012f));
		Sheet->SetVisibility(true);
		SheetLeft = FMath::Max(Tuning.FreezeSeconds, Tuning.IceWallRiseSeconds);
	}
	Phase = EPhase::Rising;
	Age = PhaseAge = 0.0f;
	SetHeightFraction(0.08f);
	FreezeCaught();
}

void AEHIceWall::SetHeightFraction(float F)
{
	// The ice grows up out of the floor (the blocking box is whole from the first frame: nothing slips through).
	const float H = FMath::Max(0.02f, F) * Tuning.IceWallHeight;
	Mesh->SetRelativeScale3D(FVector(Tuning.IceWallThickness / 100.0f, Tuning.IceWallWidth / 100.0f, H / 100.0f));
	Mesh->SetRelativeLocation(FVector(0, 0, -Tuning.IceWallHeight * 0.5f + H * 0.5f));
}

void AEHIceWall::FreezeCaught()
{
	if (!bSheet)
	{
		return;
	}
	for (const TWeakObjectPtr<AEHTrainingDummy>& D : Opponents)
	{
		if (!D.IsValid() || D->IsFrozen())
		{
			continue;
		}
		const FVector Feet = D->FeetLocation();
		if (FVector::Dist2D(Feet, Sheet->GetComponentLocation()) <= Tuning.FreezeRadius && Water.DepthAt(GetWorld(), Feet, D.Get()) > 0.5f)
		{
			D->Freeze(Tuning.FreezeSeconds);
			++FrozenCount;
		}
	}
}

void AEHIceWall::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	Age += DeltaSeconds;
	PhaseAge += DeltaSeconds;
	if (bSheet && SheetLeft > 0.0f)
	{
		SheetLeft -= DeltaSeconds;
		if (SheetLeft <= 0.0f)
		{
			Sheet->SetVisibility(false);
		}
	}
	switch (Phase)
	{
	case EPhase::Rising:
	{
		const float T = FMath::Clamp(PhaseAge / Tuning.IceWallRiseSeconds, 0.0f, 1.0f);
		SetHeightFraction(1.0f - FMath::Square(1.0f - T));
		FreezeCaught();
		if (T >= 1.0f)
		{
			Phase = EPhase::Standing;
			PhaseAge = 0.0f;
		}
		break;
	}
	case EPhase::Standing:
		if (Age >= Tuning.IceWallSeconds)
		{
			StartMelt(EEnd::Expired, Tuning.IceWallMeltSeconds);
		}
		break;
	case EPhase::Melting:
	{
		const float T = FMath::Clamp(PhaseAge / FMath::Max(0.01f, Tuning.IceWallMeltSeconds), 0.0f, 1.0f);
		SetHeightFraction(1.0f - T);
		if (T >= 1.0f)
		{
			Mesh->SetVisibility(false);
			if (!bSheet || SheetLeft <= 0.0f)
			{
				Phase = EPhase::Done;
			}
		}
		break;
	}
	default:
		break;
	}
}

void AEHIceWall::StartMelt(EEnd Why, float Seconds)
{
	if (Phase == EPhase::Melting || Phase == EPhase::Done)
	{
		return;
	}
	End = Why;
	// The path is open the moment it starts to go.
	Box->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Phase = EPhase::Melting;
	PhaseAge = 0.0f;
	Tuning.IceWallMeltSeconds = Seconds;
}

void AEHIceWall::Melt()
{
	StartMelt(EEnd::Melted, Tuning.IceWallMeltSeconds);
}

bool AEHIceWall::Damage(float Amount)
{
	if (!IsSolid())
	{
		return false;
	}
	HealthValue = FMath::Max(0.0f, HealthValue - Amount);
	if (HealthValue <= 0.0f)
	{
		StartMelt(EEnd::Shattered, 0.12f);
		return true;
	}
	return false;
}
