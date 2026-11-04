#include "EHVfx.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace EHVfxDetail
{
constexpr int32 PoolSize = 128;
constexpr int32 FirePoolSize = 64;
constexpr float FireFrames = 16.0f;   // T_FX_FireSheet is a 4 x 4 flipbook
const FLinearColor Gold(1.0f, 0.74f, 0.25f);
const FLinearColor GoldMote(1.0f, 0.80f, 0.36f);
// Ashka's Lamplighter Flame is crimson (canon). Keep both flame tones in the red-to-rose range: bright orange-reds shift
// to yellow under the tonemapper once additive intensity climbs, so intensities stay moderate.
const FLinearColor Crimson(0.86f, 0.025f, 0.07f);
const FLinearColor CrimsonHot(1.0f, 0.14f, 0.18f);
// Flame tongues: deep crimson at the thin edges, a hot pale-rose heart where the fire is dense (M_VFX_Fire), and
// embers a shade warmer than the edges so they read as sparks thrown off the fire.
const FLinearColor FireEdge(0.50f, 0.0f, 0.01f);
const FLinearColor FireCore(1.0f, 0.30f, 0.13f);
const FLinearColor EmberColor(1.0f, 0.16f, 0.06f);
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
	FireMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/VFX/M_VFX_Fire.M_VFX_Fire"));
	if (FireMaterial)
	{
		FireParticles.SetNum(FirePoolSize);
		for (int32 i = 0; i < FirePoolSize; ++i)
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
			UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(FireMaterial, this);
			M->SetVectorParameterValue(TEXT("EdgeColor"), FireEdge);
			M->SetVectorParameterValue(TEXT("CoreColor"), FireCore);
			C->SetMaterial(0, M);
			FirePool.Add(C);
			FireMaterials.Add(M);
			FireParticles[i].Index = i;
			FireParticles[i].bFire = true;
		}
	}
}

int32 AEHVfx::ActiveCount() const
{
	int32 N = 0;
	for (const TArray<FParticle>* List : {&Particles, &FireParticles})
	{
		for (const FParticle& P : *List)
		{
			N += P.bActive ? 1 : 0;
		}
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

AEHVfx::FParticle& AEHVfx::SpawnFire(const FVector& Pos, float Life, float Size0, float Size1, float Intensity)
{
	if (FireParticles.Num() == 0)
	{
		return Spawn(EEHFxTex::Flame, Pos, Life, Size0, Size1, Crimson, Intensity * 0.6f);
	}
	FParticle& P = FireParticles[FireCursor];
	FireCursor = (FireCursor + 1) % FireParticles.Num();
	const int32 Index = P.Index;
	P = FParticle();
	P.Index = Index;
	P.bActive = true;
	P.bFire = true;
	P.Pos = Pos;
	P.Life = Life;
	P.Size0 = Size0;
	P.Size1 = Size1;
	P.Intensity = bReduceFlash ? Intensity * 0.45f : Intensity;
	FireMaterials[Index]->SetScalarParameterValue(TEXT("Frame"), 0.0f);
	FirePool[Index]->SetVisibility(true);
	return P;
}

void AEHVfx::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	TickPool(Particles, Pool, Materials, DeltaSeconds);
	TickPool(FireParticles, FirePool, FireMaterials, DeltaSeconds);
}

void AEHVfx::TickPool(TArray<FParticle>& List, TArray<TObjectPtr<UStaticMeshComponent>>& Comps, TArray<TObjectPtr<UMaterialInstanceDynamic>>& Mats, float DeltaSeconds)
{
	for (FParticle& P : List)
	{
		if (!P.bActive)
		{
			continue;
		}
		P.Age += DeltaSeconds;
		UStaticMeshComponent* C = Comps[P.Index];
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
		// A flame tongue fades in over its first frames and burns out through its flipbook; sprites fade from birth.
		const float Fade = P.bFire ? FMath::Min(1.0f, T * 10.0f) : (1.0f - T) * (1.0f - T);
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
		Mats[P.Index]->SetScalarParameterValue(TEXT("Intensity"), P.Intensity * Fade);
		if (P.bFire)
		{
			Mats[P.Index]->SetScalarParameterValue(TEXT("Frame"), FMath::Min(FireFrames - 1.0f, FMath::FloorToFloat(T * FireFrames)));
		}
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
	// A few tongues licking up off the limb, each playing out its own life, with an ember or two thrown off.
	for (int32 i = 0; i < 4; ++i)
	{
		const float Size = FMath::FRandRange(9.0f, 15.0f) * Scale;
		FParticle& F = SpawnFire(At + FVector(FMath::FRandRange(-6.0f, 6.0f), 10.0f + i, FMath::FRandRange(-5.0f, 6.0f)),
		                         FMath::FRandRange(0.26f, 0.40f), Size, Size * 1.9f, 3.4f);
		F.Vel = FVector(FMath::FRandRange(-25.0f, 25.0f), 0.0f, FMath::FRandRange(90.0f, 180.0f));
		F.Angle = FMath::FRandRange(-10.0f, 10.0f);
	}
	Ember(At, Scale);
}

void AEHVfx::Ember(const FVector& At, float Scale)
{
	const int32 N = FMath::RandRange(1, 2);
	for (int32 i = 0; i < N; ++i)
	{
		FParticle& E = Spawn(EEHFxTex::Glow, At + FVector(FMath::FRandRange(-8.0f, 8.0f), 12.0f, FMath::FRandRange(0.0f, 12.0f)),
		                     FMath::FRandRange(0.45f, 0.8f), 3.2f * Scale, 1.0f * Scale, EmberColor, 7.0f);
		E.Vel = FVector(FMath::FRandRange(-60.0f, 60.0f), 0.0f, FMath::FRandRange(120.0f, 260.0f));
		E.Gravity = -80.0f;   // heat carries them up
	}
}

void AEHVfx::FlameBurst(const FVector& At, int32 Facing)
{
	if (!BaseMaterial)
	{
		return;
	}
	Spawn(EEHFxTex::Glow, At + FVector(0, 10, 90), 0.30f, 60.0f, 240.0f, Crimson, 3.5f);
	Spawn(EEHFxTex::Ring, At + FVector(0, 10, 90), 0.32f, 50.0f, 280.0f, CrimsonHot, 3.0f);
	// A wall of fire rolling out ahead of her: tongues rising from the floor and from the strike line, larger nearer
	// the body, with embers thrown up through it.
	for (int32 i = 0; i < 24; ++i)
	{
		const float Ahead = FMath::FRandRange(0.0f, 120.0f);
		const FVector Off(Facing * Ahead, 12.0f + i * 0.4f, FMath::FRandRange(0.0f, 150.0f) * (1.0f - Ahead / 240.0f));
		const float Size = FMath::FRandRange(18.0f, 34.0f) * (1.2f - Ahead / 240.0f);
		FParticle& F = SpawnFire(At + Off, FMath::FRandRange(0.34f, 0.56f), Size, Size * 2.0f, 3.6f);
		F.Vel = FVector(Facing * FMath::FRandRange(30.0f, 140.0f), 0.0f, FMath::FRandRange(90.0f, 220.0f));
		F.Angle = FMath::FRandRange(-12.0f, 12.0f);
	}
	for (int32 i = 0; i < 4; ++i)
	{
		Ember(At + FVector(Facing * FMath::FRandRange(10.0f, 110.0f), 0.0f, FMath::FRandRange(20.0f, 140.0f)), 1.4f);
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

void AEHVfx::AuraMote(const FVector& At)
{
	if (!BaseMaterial)
	{
		return;
	}
	// A spark of the aura streaming up off the body.
	FParticle& M = Spawn(EEHFxTex::Glow, At + FVector(FMath::FRandRange(-6.0f, 6.0f), 11.0f, FMath::FRandRange(-6.0f, 6.0f)),
	                     FMath::FRandRange(0.45f, 0.8f), 3.0f, 0.8f, GoldMote, 6.0f);
	M.Vel = FVector(FMath::FRandRange(-18.0f, 18.0f), 0.0f, FMath::FRandRange(55.0f, 130.0f));
	M.Gravity = -60.0f;
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
