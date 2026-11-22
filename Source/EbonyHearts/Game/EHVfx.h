// Lightweight pooled sprite effects (impacts, flame, water) driven from simulation events. Presentation only.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"

#include "EHVfx.generated.h"

class UMaterialInstanceDynamic;
class UStaticMeshComponent;
class UTexture2D;

enum class EEHFxTex : uint8 { Glow, Streak, Ring, Flame, Spark, Splash, Count };

UCLASS(NotBlueprintable)
class AEHVfx : public AActor
{
	GENERATED_BODY()

public:
	AEHVfx();
	void Init(bool bReduceFlash);
	void SetReduceFlash(bool b) { bReduceFlash = b; }
	// First person: sprites face this point (the eyes) instead of the side-on camera's +Y.
	void SetViewPoint(const FVector& InView) { ViewPoint = InView; bFaceView = true; }
	// Size and brightness of hits, blocks and sparks (first person sees them at arm's length, not across a stage).
	void SetImpactScale(float Size, float Brightness) { ImpactSize = Size; ImpactBrightness = Brightness; }
	virtual void Tick(float DeltaSeconds) override;

	void Hit(const FVector& At, int32 Facing, bool bHeavy, bool bEnergy, bool bAura, bool bCounter);
	void Block(const FVector& At, int32 Facing, bool bDeflect);
	void Tech(const FVector& At);
	void Flame(const FVector& At, float Scale);
	void FlameBurst(const FVector& At, int32 Facing);
	void AuraFlash(const FVector& At);
	void AuraMote(const FVector& At);
	// An ember rising off a fire (the forge's coals).
	void HearthSpark(const FVector& At) { Ember(At, 0.8f); }
	void Ripple(const FVector& At, float Scale);
	void Splash(const FVector& At, float Scale);
	// Spells (first person): a fireball's trail, its burst, steam off melting ice, and ice breaking.
	void FireTrail(const FVector& At);
	void FireBurst(const FVector& At);
	void Steam(const FVector& At, float Scale);
	void IceBurst(const FVector& At, float Scale);
	bool HasMaterial() const { return BaseMaterial != nullptr; }
	int32 ActiveCount() const;

private:
	struct FParticle
	{
		int32 Index = -1;
		bool bActive = false;
		bool bGround = false;
		float Age = 0.0f;
		float Life = 0.2f;
		FVector Pos = FVector::ZeroVector;
		FVector Vel = FVector::ZeroVector;
		float Gravity = 0.0f;
		float Size0 = 10.0f;
		float Size1 = 20.0f;
		float Stretch = 1.0f;     // x scale multiplier for streaks
		float Angle = 0.0f;       // in-plane rotation (degrees)
		FLinearColor Color = FLinearColor::White;
		float Intensity = 1.0f;
		EEHFxTex Tex = EEHFxTex::Glow;
		bool bFire = false;       // a flame tongue from the fire pool: plays its flipbook over its life
		float Scale = 1.0f;       // size and travel multiplier (impacts seen up close in first person)
	};

	FVector ViewPoint = FVector::ZeroVector;
	float ImpactSize = 1.0f;
	float ImpactBrightness = 1.0f;
	bool bImpact = false;     // set while Hit or Block spawns
	bool bFaceView = false;

	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> Pool;
	UPROPERTY()
	TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
	UPROPERTY()
	TObjectPtr<UMaterialInterface> BaseMaterial;
	UPROPERTY()
	TArray<TObjectPtr<UTexture2D>> Textures;
	// Flame tongues use their own pool so a quad never changes material (that rebuilds its render proxy).
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> FirePool;
	UPROPERTY()
	TArray<TObjectPtr<UMaterialInstanceDynamic>> FireMaterials;
	UPROPERTY()
	TObjectPtr<UMaterialInterface> FireMaterial;

	TArray<FParticle> Particles;
	TArray<FParticle> FireParticles;
	int32 FireCursor = 0;
	int32 Cursor = 0;
	bool bReduceFlash = false;

	FParticle& Spawn(EEHFxTex Tex, const FVector& Pos, float Life, float Size0, float Size1, const FLinearColor& Color, float Intensity);
	// A flame tongue (M_VFX_Fire): dark crimson edges to a hot core; falls back to the flame sprite without the material.
	FParticle& SpawnFire(const FVector& Pos, float Life, float Size0, float Size1, float Intensity);
	void Ember(const FVector& At, float Scale);
	void TickPool(TArray<FParticle>& List, TArray<TObjectPtr<UStaticMeshComponent>>& Comps, TArray<TObjectPtr<UMaterialInstanceDynamic>>& Mats, float DeltaSeconds);
};
