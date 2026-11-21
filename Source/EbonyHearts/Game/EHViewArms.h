// Placeholder first-person arms: plain shapes posed every frame from the techniques' game state, so a fist reaches
// full extension exactly on the first active frame and holds there through any hitstop. Drawn as first-person
// primitives (their own field of view and depth range), so they never clip into walls. They come into view only
// while a technique or the guard needs them. Final arms and animation are the creator's to author.
#pragma once

#include "Components/SceneComponent.h"
#include "CoreMinimal.h"
#include "EHFists.h"

#include "EHViewArms.generated.h"

class UMaterialInstanceDynamic;
class UStaticMeshComponent;

UCLASS(NotBlueprintable)
class UEHViewArms : public USceneComponent
{
	GENERATED_BODY()

public:
	UEHViewArms();
	void Build();
	// Alpha: progress toward the next 60 Hz frame, for smooth motion at any render rate.
	void UpdateArms(const FEHFists& Fists, float Alpha, float DeltaSeconds);
	void SnapHidden();
	bool AreShown() const { return bShown; }
	// Development aid: draw the arms as ordinary world geometry instead of first-person primitives.
	void SetFirstPersonRendering(bool bOn);
	// Camera-space fist positions (cm), for evidence and tests.
	FVector FistPosition(int32 Hand) const { return Hand == 0 ? ShownL : ShownR; }

private:
	struct FArm
	{
		UStaticMeshComponent* Upper = nullptr;
		UStaticMeshComponent* Fore = nullptr;
		UStaticMeshComponent* Fist = nullptr;
	};

	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> Parts;
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> SkinMaterial;
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> WrapMaterial;

	FArm Arms[2];   // 0 left (lead hand: the jab), 1 right (rear hand: the straight)
	FVector ShownL = FVector::ZeroVector;
	FVector ShownR = FVector::ZeroVector;
	FVector RestL = FVector::ZeroVector;
	FVector RestR = FVector::ZeroVector;
	FVector StartL = FVector::ZeroVector;   // where each fist was when the current technique began
	FVector StartR = FVector::ZeroVector;
	EEHFistAction LastAction = EEHFistAction::None;
	float Visible = 0.0f;                   // 0 lowered out of view .. 1 up
	float Recoil = 0.0f;                    // 1 at contact, easing to 0 after the hitstop
	float ShudderTime = 0.0f;
	bool bShown = false;

	void PoseArm(FArm& Arm, const FVector& Shoulder, const FVector& Hand, float Side);
	UStaticMeshComponent* MakePart(UStaticMesh* Mesh, UMaterialInstanceDynamic* Material);
};
