#include "EHVfx.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace EHVfxDetail
{
constexpr int32 PoolSize = 96;
const FLinearColor Gold(1.0f, 0.74f, 0.25f);
// Ashka's Lamplighter Flame is crimson (canon). Keep both flame tones in the red-to-rose range: bright orange-reds shift
// to yellow under the tonemapper once additive intensity climbs, so intensities stay moderate.
const FLinearColor Crimson(0.86f, 0.025f, 0.07f);
const FLinearColor CrimsonHot(1.0f, 0.14f, 0.18f);
const FLinearColor Steel(0.70f, 0.82f, 1.0f);
const FLinearColor Pale(1.0f, 0.95f, 0.85f);
const FLinearColor Water(0.55f, 0.70f, 0.85f);
const TCHAR* TexturePaths[] = {
	TEXT("/Game/VFX/T_FX_Glow.T_FX_Glow"),
	TEXT("/Game/VFX/T_FX_Streak.T_FX_Streak"),
	TEXT("/Game/VFX/T_FX_Ring.T_FX_Ring"),
	TEXT("/Game/VFX/T_FX_Flame.T_FX_Flame"),
	TEXT("/Game/VFX/T_FX_Spark.T_FX_Spark"),
	TEXT("/Game/VFX/T_FX_Splash.T_FX_Splash"),
};
}
using namespace EHVfxDetail;

AEHVfx::AEHVfx()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickGroup = TG_PostUpdateWork;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AEHVfx::Init(bool bInReduceFlash)
{
	bReduceFlash = bInReduceFlash;
	BaseMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/VFX/M_VFX_Additive.M_VFX_Additive"));
	if (BaseMaterial == nullptr)
	{
		return;   // effects are skipped until the effect material exists; gameplay is unaffected
	}
	for (const TCHAR* Path : TexturePaths)
	{
		Textures.Add(LoadObject<UTexture2D>(nullptr, Path));
	}
	UStaticMesh* Quad = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	Particles.SetNum(PoolSize);
	for (int32 i = 0; i < PoolSize; ++i)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(Quad);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		C->SetUsingAbsoluteLocation(true);
		C->SetUsingAbsoluteRotation(true);
		C->SetupAttachment(RootComponent);
		C->RegisterComponent();
		C->SetVisibility(false);
		UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(BaseMaterial, this);
		C->SetMaterial(0, M);
		Pool.Add(C);
		Materials.Add(M);
		Particles[i].Index = i;
	}
}

int32 AEHVfx::ActiveCount() const
{
	int32 N = 0;
	for (const FParticle& P : Particles)
	{
		N += P.bActive ? 1 : 0;
	}
	return N;
}

AEHVfx::FParticle& AEHVfx::Spawn(EEHFxTex Tex, const FVector& Pos, float Life, float Size0, float Size1, const FLinearColor& Color, float Intensity)
{
	// Oldest-first reuse keeps the pool bounded even under constant hits.
	FParticle& P = Particles[Cursor];
	Cursor = (Cursor + 1) % Particles.Num();
	const int32 Index = P.Index;
	P = FParticle();
	P.Index = Index;
	P.bActive = true;
	P.Tex = Tex;
	P.Pos = Pos;
	P.Life = Life;
	P.Size0 = Size0;
	P.Size1 = Size1;
	P.Color = Color;
	P.Intensity = bReduceFlash ? Intensity * 0.45f : Intensity;
	UMaterialInstanceDynamic* M = Materials[Index];
	const int32 T = static_cast<int32>(Tex);
	if (Textures.IsValidIndex(T) && Textures[T])
	{
		M->SetTextureParameterValue(TEXT("Tex"), Textures[T]);
	}
	M->SetVectorParameterValue(TEXT("Color"), Color);
	Pool[Index]->SetVisibility(true);
	return P;
}

void AEHVfx::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	for (FParticle& P : Particles)
	{
		if (!P.bActive)
		{
			continue;
		}
		P.Age += DeltaSeconds;
		UStaticMeshComponent* C = Pool[P.Index];
		if (P.Age >= P.Life)
		{
			P.bActive = false;
			C->SetVisibility(false);
			continue;
		}
		const float T = P.Age / P.Life;
		P.Vel.Z -= P.Gravity * DeltaSeconds;
		P.Pos += P.Vel * DeltaSeconds;
		const float Size = FMath::Lerp(P.Size0, P.Size1, 1.0f - FMath::Square(1.0f - T));
		const float Fade = (1.0f - T) * (1.0f - T);
		FQuat Q;
		if (P.bGround)
		{
			Q = FQuat(FVector(0, 0, 1), FMath::DegreesToRadians(P.Angle));
		}
		else
		{
			// Plane normal (+Z) turned toward the camera (+Y), then spun in the view plane.
			Q = FQuat(FVector(0, 1, 0), FMath::DegreesToRadians(P.Angle)) * FQuat(FVector(1, 0, 0), FMath::DegreesToRadians(-90.0f));
		}
		C->SetWorldLocationAndRotation(P.Pos, Q);
		C->SetWorldScale3D(FVector(Size * P.Stretch / 100.0f, Size / 100.0f, 1.0f));
		Materials[P.Index]->SetScalarParameterValue(TEXT("Intensity"), P.Intensity * Fade);
	}
}

void AEHVfx::Hit(const FVector& At, int32 Facing, bool bHeavy, bool bEnergy, bool bAura, bool bCounter)
{
	if (!BaseMaterial)
	{
		return;
	}
	const FLinearColor Core = bEnergy ? Crimson : (bAura ? Gold : Pale);
	const float Scale = bHeavy ? 1.5f : 1.0f;
	Spawn(EEHFxTex::Glow, At + FVector(0, 6, 0), 0.12f, 20.0f * Scale, 70.0f * Scale, Core, 7.0f);
	Spawn(EEHFxTex::Spark, At + FVector(0, 7, 0), 0.09f, 30.0f * Scale, 55.0f * Scale, Pale, 9.0f).Angle = FMath::FRandRange(0.0f, 90.0f);
	const int32 Streaks = bHeavy ? 7 : 4;
	for (int32 i = 0; i < Streaks; ++i)
	{
		const float Ang = FMath::FRandRange(-55.0f, 55.0f) + (Facing > 0 ? 0.0f : 180.0f);
		FParticle& S = Spawn(EEHFxTex::Streak, At + FVector(0, 8, 0), 0.14f, 12.0f * Scale, 26.0f * Scale, bAura ? Gold : (bEnergy ? CrimsonHot : Pale), 6.0f);
		S.Angle = -Ang;
		S.Stretch = 3.2f;
		S.Vel = FVector(FMath::Cos(FMath::DegreesToRadians(Ang)), 0.0f, FMath::Sin(FMath::DegreesToRadians(Ang))) * (380.0f * Scale);
	}
	if (bCounter)
	{
		Spawn(EEHFxTex::Ring, At + FVector(0, 9, 0), 0.22f, 30.0f, 140.0f, Gold, 4.0f);
	}
	if (bEnergy)
	{
		Flame(At, 1.2f * Scale);
	}
	if (bAura)
	{
		AuraFlash(At);
	}
}

void AEHVfx::Block(const FVector& At, int32 Facing, bool bDeflect)
{
	if (!BaseMaterial)
	{
		return;
	}
	if (bDeflect)
	{
		Spawn(EEHFxTex::Ring, At + FVector(0, 8, 0), 0.20f, 25.0f, 120.0f, Pale, 8.0f);
		Spawn(EEHFxTex::Glow, At + FVector(0, 8, 0), 0.10f, 30.0f, 80.0f, Gold, 9.0f);
	}
	else
	{
		Spawn(EEHFxTex::Ring, At + FVector(0, 8, 0), 0.14f, 20.0f, 70.0f, Steel, 4.0f);
	}
	for (int32 i = 0; i < 3; ++i)
	{
		const float Ang = FMath::FRandRange(-40.0f, 40.0f) + (Facing > 0 ? 180.0f : 0.0f);
		FParticle& S = Spawn(EEHFxTex::Streak, At + FVector(0, 8, 0), 0.10f, 8.0f, 16.0f, Steel, 4.0f);
		S.Angle = -Ang;
		S.Stretch = 3.0f;
		S.Vel = FVector(FMath::Cos(FMath::DegreesToRadians(Ang)), 0.0f, FMath::Sin(FMath::DegreesToRadians(Ang))) * 260.0f;
	}
}

void AEHVfx::Tech(const FVector& At)
{
	if (!BaseMaterial)
	{
		return;
	}
	Spawn(EEHFxTex::Ring, At + FVector(0, 8, 0), 0.25f, 30.0f, 150.0f, Steel, 5.0f);
	Spawn(EEHFxTex::Glow, At + FVector(0, 8, 0), 0.12f, 20.0f, 60.0f, Steel, 5.0f);
}

void AEHVfx::Flame(const FVector& At, float Scale)
{
	if (!BaseMaterial)
	{
		return;
	}
	for (int32 i = 0; i < 4; ++i)
	{
		FParticle& F = Spawn(EEHFxTex::Flame, At + FVector(FMath::FRandRange(-6.0f, 6.0f), 10, FMath::FRandRange(-6.0f, 6.0f)), FMath::FRandRange(0.22f, 0.36f), 18.0f * Scale, 34.0f * Scale, i % 2 ? Crimson : CrimsonHot, 3.2f);
		F.Vel = FVector(FMath::FRandRange(-30.0f, 30.0f), 0.0f, FMath::FRandRange(60.0f, 140.0f));
		F.Angle = FMath::FRandRange(-12.0f, 12.0f);
	}
}

void AEHVfx::FlameBurst(const FVector& At, int32 Facing)
{
	if (!BaseMaterial)
	{
		return;
	}
	Spawn(EEHFxTex::Glow, At + FVector(0, 10, 90), 0.30f, 60.0f, 260.0f, Crimson, 4.5f);
	Spawn(EEHFxTex::Ring, At + FVector(0, 10, 90), 0.32f, 50.0f, 300.0f, CrimsonHot, 4.0f);
	for (int32 i = 0; i < 10; ++i)
	{
		const FVector Off(Facing * FMath::FRandRange(0.0f, 110.0f), 12.0f, FMath::FRandRange(10.0f, 170.0f));
		FParticle& F = Spawn(EEHFxTex::Flame, At + Off, FMath::FRandRange(0.3f, 0.5f), 30.0f, 70.0f, i % 3 ? Crimson : CrimsonHot, 3.2f);
		F.Vel = FVector(Facing * FMath::FRandRange(20.0f, 120.0f), 0.0f, FMath::FRandRange(80.0f, 220.0f));
	}
}

void AEHVfx::AuraFlash(const FVector& At)
{
	if (!BaseMaterial)
	{
		return;
	}
	Spawn(EEHFxTex::Glow, At + FVector(0, 9, 0), 0.16f, 40.0f, 120.0f, Gold, 6.0f);
	for (int32 i = 0; i < 3; ++i)
	{
		FParticle& S = Spawn(EEHFxTex::Streak, At + FVector(0, 9, 0), 0.08f, 20.0f, 30.0f, Gold, 8.0f);
		S.Angle = FMath::FRandRange(0.0f, 180.0f);
		S.Stretch = 5.0f;
	}
}

void AEHVfx::Ripple(const FVector& At, float Scale)
{
	if (!BaseMaterial)
	{
		return;
	}
	FParticle& R = Spawn(EEHFxTex::Ring, FVector(At.X, At.Y, 3.6f), 0.8f, 10.0f * Scale, 55.0f * Scale, Water, 0.35f);
	R.bGround = true;
	R.Angle = FMath::FRandRange(0.0f, 360.0f);
}

void AEHVfx::Splash(const FVector& At, float Scale)
{
	if (!BaseMaterial)
	{
		return;
	}
	Ripple(At, Scale * 1.4f);
	for (int32 i = 0; i < 5; ++i)
	{
		FParticle& S = Spawn(EEHFxTex::Splash, FVector(At.X + FMath::FRandRange(-20.0f, 20.0f), At.Y + 6.0f, 6.0f), FMath::FRandRange(0.35f, 0.55f), 16.0f * Scale, 34.0f * Scale, Water, 1.6f);
		S.Vel = FVector(FMath::FRandRange(-90.0f, 90.0f), 0.0f, FMath::FRandRange(160.0f, 300.0f) * Scale);
		S.Gravity = 900.0f;
	}
}
