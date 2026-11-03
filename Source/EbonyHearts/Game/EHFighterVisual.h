// One fighter on screen. Reads the simulation state each render frame and poses the character accordingly;
// it never changes the simulation.
#pragma once

#include "CoreMinimal.h"
#include "EHMatch.h"
#include "EHPresentation.h"
#include "GameFramework/Actor.h"

#include "EHFighterVisual.generated.h"

class UAnimSequence;
class UEHAnimInstance;
class UMaterialInstanceDynamic;
class UProceduralMeshComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;

struct FEHAnimChoice
{
	FName Key;
	int32 Frame = 1;          // 1-based frame within the animation at 60 fps
	bool bLoop = false;
	int64 Instance = 0;       // changes whenever a new instance of the state/move starts
	float BlendSeconds = 0.08f;
};

// Pure function of simulation state: which animation and frame represent this fighter now.
FEHAnimChoice EHChooseAnim(const eh::Match& Match, int32 Player);

UCLASS(NotBlueprintable)
class AEHFighterVisual : public AActor
{
	GENERATED_BODY()

public:
	AEHFighterVisual();

	void Setup(const FEHCharacterPresentation& InPresentation, int32 InPlayer, bool bMirrorMatch);
	// Alpha: fraction of the way to the next tick (0 while frozen). PrevX/CurX: positions in units.
	void UpdateVisual(const eh::Match& Match, int32 PrevX, float Alpha, float DeltaSeconds, double Time);
	bool UsesGraybox() const { return bGraybox; }
	FVector BoneLocation(FName Bone, const FVector& Fallback) const;
	FVector HeadLocation() const;
	TArray<FString> MissingAnimations() const;
	void SetAuraIntensity(float Intensity) { AuraIntensity = Intensity; }
	void SetFlameIntensity(float Intensity) { FlameIntensity = Intensity; }
	USkeletalMeshComponent* GetMesh() const { return Mesh; }

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<USkeletalMeshComponent> Mesh;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UStaticMeshComponent> GrayBody;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UStaticMeshComponent> GrayHead;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UStaticMeshComponent> GrayLimb;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UStaticMeshComponent> Marker;
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<UProceduralMeshComponent> Aura;

private:
	UPROPERTY()
	TMap<FName, TObjectPtr<UAnimSequence>> Anims;
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> GrayMaterial;
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> MarkerMaterial;
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> AuraMaterial;
	// Per-slot instances of the character materials; their rim turns gold while Spirit Enhanced Strikes is active.
	UPROPERTY()
	TArray<TObjectPtr<UMaterialInstanceDynamic>> BodyMaterials;

	FEHCharacterPresentation Presentation;
	int32 Player = 0;
	bool bGraybox = true;
	TSet<FName> Missing;

	FName CurrentKey;
	int64 CurrentInstance = -1;
	double CurrentTime = 0.0;
	FName PreviousKey;
	double PreviousTime = 0.0;
	float BlendTotal = 0.0f;
	float BlendLeft = 0.0f;
	double LoopTime = 0.0;
	float AuraIntensity = 0.0f;
	float FlameIntensity = 0.0f;
	double AuraSeedTime = 0.0;
	float AppliedRim = -1.0f;
	float AppliedFacingSign = 0.0f;

	UAnimSequence* FindAnim(FName Key);
	void UpdateGraybox(const eh::Match& Match, float DeltaSeconds);
	void UpdateAura(double Time);
};
