// Placeholder first-person arms: plain shapes posed every frame from the techniques' game state, so a fist reaches
// full extension exactly on the first active frame and holds there through any hitstop. Drawn as first-person
// primitives (their own field of view and depth range), so they never clip into walls. They come into view only
// while a technique or the guard needs them. Final arms and animation are the creator's to author.
#pragma once

#include "Components/SceneComponent.h"
#include "CoreMinimal.h"
#include "EHFists.h"

#include "EHViewArms.generated.h"

class UAnimSequence;
class UMaterialInstanceDynamic;
class USkeletalMeshComponent;
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
	// Placeholder arms cut from a character model (Tools/Blender/fparms), posed by the guard clip for the fists and by
	// two-bone IK for the reach. Without that asset the arms fall back to plain shapes.
	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> ArmsMesh;
	UPROPERTY()
	TObjectPtr<UAnimSequence> FistPose;
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> SkinMaterial;
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> WrapMaterial;
	// A glow in each hand while a spell gathers (fire in the left hand, frost in both for the wall), drawn with the
	// arms so it sits on the hand the player sees.
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Glow[2];
	UPROPERTY()
	TObjectPtr<UMaterialInstanceDynamic> GlowMaterial[2];

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

	// The realistic first-person hands (Tools/Blender/fphands; CC0 base mesh): posed with no clip, by IK for the reach
	// and by rotations for each finger, the wrist's turn and the hand's bend. Each hand's state eases toward a target
	// per technique: curl 0 open .. 1 a tight fist; pronation turns the palm down (degrees); bend tips the hand back.
	bool bRealHands = false;
	struct FHandFrame
	{
		bool bValid = false;
		FVector Lateral = FVector::ZeroVector;      // across the knuckles, index to pinky (component space)
		FVector Forearm = FVector::ZeroVector;      // elbow to wrist
		float FlexSign = 1.0f;                      // which way about Lateral curls a finger toward the palm
		float PronateSign = 1.0f;                   // which way about Forearm turns the palm down
		FVector ThumbAxis = FVector::ZeroVector;    // the thumb folds about this, toward the palm
		float ThumbSweepSign = 1.0f;                // which way about the palm normal sweeps the thumb toward the pinky
		FVector Thumb[3];                           // the thumb's three joints, rest pose
		FVector Knuckles = FVector::ZeroVector;     // wrist to the middle knuckle, rest pose
		FVector Palm = FVector::ZeroVector;         // out of the palm, rest pose
		FQuat RefRotation = FQuat::Identity;        // the hand bone's rest rotation (component space)
	};
	FHandFrame HandFrames[2];
	float Curl[2] = {0.3f, 0.3f};
	float Pronate[2] = {0.0f, 0.0f};
	float Bend[2] = {0.0f, 0.0f};
	float Spread[2] = {0.0f, 0.0f};
	void CacheHandFrames();
	void AddHandRotations(TArray<struct FEHAdditiveRotation>& Out, int32 Hand) const;
	// The hand bone's component-space rotation that points the knuckles along Forward (camera space) with the palm
	// facing Palm.
	FQuat AimHand(int32 Hand, const FVector& Forward, const FVector& PalmDir, const FQuat& CamToCS) const;
	void UpdateHandTargets(const FEHFists& Fists, float DeltaSeconds);
	void PoseArm(FArm& Arm, const FVector& Shoulder, const FVector& Hand, float Side);
	void PoseMeshArms(const FVector& L, const FVector& R);
	void ShowParts(bool bShow);
	void BuildGlows();
	void SetGlow(int32 Hand, const FLinearColor& Color, float Amount);
public:
	bool UsesModelArms() const { return ArmsMesh != nullptr; }
	FString Describe() const;
	UStaticMeshComponent* MakePart(UStaticMesh* Mesh, UMaterialInstanceDynamic* Material);
};
