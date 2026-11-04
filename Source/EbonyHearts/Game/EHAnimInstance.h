// Pose = sequence sampled at a time chosen by the simulation. The game thread sets the sample every frame; nothing
// here advances time on its own, so animation stays locked to combat frames (and freezes during hitstop) regardless of
// the render rate.
//
// Transitions are inertialized rather than cross-faded: the new sequence plays from its first frame at once (so the
// pose on screen never lags the combat state), and the difference from the last displayed pose is carried as a
// per-bone offset that decays to zero along a quintic curve, continuing the old pose's velocity. Nothing is sampled
// from the previous sequence.
//
// Planted feet are the exception: decaying the hips' and legs' offsets would carry a planted foot along with them, so
// during a transition each foot that is on the floor in both poses eases in a straight line from where it was shown
// to where the new animation puts it, and the leg reaches it (two-bone IK).
#pragma once

#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "BonePose.h"
#include "CoreMinimal.h"

#include "EHAnimInstance.generated.h"

class UAnimSequence;

struct FEHAnimSample
{
	TObjectPtr<UAnimSequence> Sequence = nullptr;
	double Time = 0.0;
};

// One bone's decaying offset: a rotation about a fixed axis and a translation along a fixed direction.
struct FEHBoneOffset
{
	FVector3f Axis = FVector3f::ZAxisVector;
	float Angle = 0.0f;
	float AngleSpeed = 0.0f;
	FVector3f Dir = FVector3f::ZAxisVector;
	float Dist = 0.0f;
	float DistSpeed = 0.0f;
};

// One leg for the transition foot lock (compact pose indices; -1 until resolved for the current bone container).
struct FEHLeg
{
	int32 Thigh = -1;
	int32 Calf = -1;
	int32 Foot = -1;
	int32 ThighHalf = -1;   // shoulder/hip half-joint beside the thigh (half its swing), or -1
	FVector FootFrom = FVector::ZeroVector;   // shown foot minus the new animation's foot, at the transition start
	float Weight = 0.0f;                      // how planted the foot is in both poses (0..1)
};

struct FEHAnimProxy : public FAnimInstanceProxy
{
	FEHAnimProxy() = default;
	explicit FEHAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

	FEHAnimSample Current;
	int32 TransitionSerial = 0;
	float TransitionSeconds = 0.0f;

	// Proxy-owned state (animation thread).
	int32 HandledSerial = 0;
	float Elapsed = 0.0f;
	float Duration = 0.0f;
	float FrameDelta = 1.0f / 60.0f;
	TArray<FEHBoneOffset> Offsets;
	TArray<FTransform> Shown1;   // the pose displayed last frame
	TArray<FTransform> Shown2;   // and the frame before
	FEHLeg Legs[2];
	int32 LegsForBones = -1;     // bone count the leg indices were resolved for
	float PlantedHeight = 0.0f;  // ankle height (component space) of the reference pose

private:
	void ResolveLegs(const FCompactPose& Pose);
	void LockFeet(FCompactPose& Pose, FCSPose<FCompactPose>& Target, float Fade);
};

UCLASS(Transient, NotBlueprintable)
class UEHAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	void SetSample(UAnimSequence* Sequence, double Time);
	// Starts a transition to the sequence set this frame. Seconds <= 0 cuts with no blend.
	void BeginTransition(float Seconds);

	FEHAnimSample Current;
	int32 TransitionSerial = 0;
	float TransitionSeconds = 0.0f;

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FEHAnimProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }
};
