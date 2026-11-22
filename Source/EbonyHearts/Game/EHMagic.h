// Stats, Qhi and the two prototype spells. Stats are fixed at one set of values (the debug tools change them live in
// development builds); the spells are world actors the player's casts release: a Fireball that flies along the aim
// and an Ice Wall raised in front of the player, which freezes nearby water as it rises.
#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "GameFramework/Actor.h"

#include "EHMagic.generated.h"

class UBoxComponent;
class UMaterialInstanceDynamic;
class UPointLightComponent;
class UStaticMeshComponent;
class AEHIceWall;
class AEHTrainingDummy;
class AEHVfx;

// The seven stats. Health, Qhi and Stamina are pools (their maximum); the other four shape how the pools and the
// physical techniques behave, each measured from Base (10), where everything is at its spec value.
struct FEHPlayerStats
{
	float Health = 100.0f;
	float Qhi = 100.0f;
	float Stamina = 100.0f;
	int32 Intelligence = 10;
	int32 Faith = 10;
	int32 Dexterity = 10;
	int32 MartialProwess = 10;
};

const TCHAR* const EHStatNames[] = {TEXT("health"), TEXT("qhi"), TEXT("stamina"), TEXT("intelligence"), TEXT("faith"), TEXT("dexterity"), TEXT("martial")};

struct FEHMagicTuning
{
	FEHPlayerStats Stats;
	int32 StatBase = 10;
	float QhiRegenPerSecond = 5.0f;     // at base Intelligence and Faith
	float QhiRegenPerPoint = 0.05f;     // each point of Intelligence or Faith above base adds this share
	float QhiRegenDelay = 0.5f;         // seconds after a cast before Qhi flows back
	float QhiPerStrike = 4.0f;          // a physical technique that lands (not guarded)
	float StaminaPerDexterity = 0.05f;  // share of Stamina recovery per point of Dexterity
	float PhysicalPerProwess = 0.05f;   // share of physical damage and shove distance per point of Martial Prowess

	float FireballCost = 20.0f;
	float FireballDamage = 25.0f;
	float FireballSpeed = 2200.0f;      // cm/s
	float FireballRadius = 14.0f;
	float FireballRange = 3000.0f;
	float FireballHitstop = 5.0f;       // frames the target holds on contact

	float IceWallCost = 30.0f;
	float IceWallSeconds = 8.0f;
	float IceWallDistance = 220.0f;     // cm from the player's centre to the wall's
	float IceWallMinDistance = 110.0f;  // nearer than this to an obstruction, the wall is refused
	float IceWallWidth = 300.0f;
	float IceWallHeight = 240.0f;
	float IceWallThickness = 40.0f;
	float IceWallRiseSeconds = 0.3f;    // the start-up that freezes the water
	float IceWallMeltSeconds = 0.5f;
	float IceWallHealth = 60.0f;        // physical damage that shatters it
	float FreezeRadius = 280.0f;        // water within this distance of the wall freezes
	float FreezeSeconds = 2.0f;

	bool Load(const TSharedPtr<FJsonObject>& Root, FString& OutError);
	FString Describe() const;

	float QhiRegen(const FEHPlayerStats& S) const;
	float StaminaScale(const FEHPlayerStats& S) const;
	float PhysicalScale(const FEHPlayerStats& S) const;
};

// The Chapel's water: one sheet at SurfaceZ over the floor, within the water mesh's bounds.
struct FEHWater
{
	float SurfaceZ = 3.0f;
	FBox2D Bounds = FBox2D(FVector2D(-1200, -2000), FVector2D(1200, 600));
	// Depth of water over the floor under XY (0 when dry or outside the water).
	float DepthAt(const UWorld* World, const FVector& At, const AActor* Ignore = nullptr) const;
};

UCLASS(NotBlueprintable)
class AEHFireball : public AActor
{
	GENERATED_BODY()

public:
	AEHFireball();
	virtual void Tick(float DeltaSeconds) override;
	void Launch(const FEHMagicTuning& InTuning, AActor* InCaster, AEHVfx* InVfx, const FVector& Direction);

	enum class EResult : uint8 { Flying, Target, Wall, World, Expired };
	EResult Result() const { return State; }
	TWeakObjectPtr<AEHTrainingDummy> HitTarget;
	TWeakObjectPtr<AEHIceWall> HitWall;
	FVector HitAt = FVector::ZeroVector;
	bool bHandled = false;   // the director has played the result

private:
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Core;
	UPROPERTY()
	TObjectPtr<UPointLightComponent> Light;
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> CoreMaterial;
	FEHMagicTuning Tuning;
	TWeakObjectPtr<AActor> Caster;
	TWeakObjectPtr<AEHVfx> Vfx;
	FVector Velocity = FVector::ZeroVector;
	float Travelled = 0.0f;
	float TrailTimer = 0.0f;
	EResult State = EResult::Flying;
};

UCLASS(NotBlueprintable)
class AEHIceWall : public AActor
{
	GENERATED_BODY()

public:
	AEHIceWall();
	virtual void Tick(float DeltaSeconds) override;
	// Raised at Base (on the floor) facing Facing; Water decides what freezes; Opponents caught near it in water
	// while it rises are frozen.
	void Raise(const FEHMagicTuning& InTuning, const FEHWater& InWater, const FVector& Base, const FVector& Facing, const TArray<AEHTrainingDummy*>& Opponents);
	void Melt();                       // Fireball: gone at once, steam
	bool Damage(float Amount);         // physical strikes; true when it shatters
	bool IsSolid() const { return Phase == EPhase::Rising || Phase == EPhase::Standing; }
	bool IsDone() const { return Phase == EPhase::Done; }
	float HealthLeft() const { return HealthValue; }
	float SecondsLeft() const { return FMath::Max(0.0f, Tuning.IceWallSeconds - Age); }
	int32 Frozen() const { return FrozenCount; }
	bool FroseWater() const { return bSheet; }
	const TCHAR* PhaseName() const;
	enum class EEnd : uint8 { None, Expired, Melted, Shattered };
	EEnd EndReason() const { return End; }

private:
	enum class EPhase : uint8 { Rising, Standing, Melting, Done };
	UPROPERTY()
	TObjectPtr<UBoxComponent> Box;
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Mesh;
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Sheet;
	FEHMagicTuning Tuning;
	FEHWater Water;
	TArray<TWeakObjectPtr<AEHTrainingDummy>> Opponents;
	EPhase Phase = EPhase::Rising;
	EEnd End = EEnd::None;
	float Age = 0.0f;
	float PhaseAge = 0.0f;
	float HealthValue = 60.0f;
	float SheetLeft = 0.0f;
	bool bSheet = false;
	int32 FrozenCount = 0;
	void SetHeightFraction(float F);
	void StartMelt(EEnd Why, float Seconds);
	void FreezeCaught();
};
