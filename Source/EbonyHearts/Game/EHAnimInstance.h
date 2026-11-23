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
// to where the new animation puts it, and the leg reaches it (two-bone IK). A foot with far to go (a strike started
// mid-step) lifts on the way, so it steps there rather than sliding along the floor.
//
// The legs can settle over a longer time than the rest of the body (BeginTransition's LegSeconds): a strike's arms are
// on their own keys by its first active frame, while the feet finish the step the walk was in.
#pragma once

#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "BonePose.h"
#include "CoreMinimal.h"

#include "EHAnimInstance.generated.h"

class UAnimSequence;

// A rotation added on top of the sampled pose, about the bone's own origin, given in component space. Used for
// reactions driven by game state (a head snapping back from a hit) that no clip contains.
struct FEHAdditiveRotation
{
	FName Bone;
	FQuat Rotation = FQuat::Identity;
};

// Two-bone IK for one limb, in component space: the hand reaches Target (clamped to the limb's length) with the elbow
// bending toward Pole. The hand keeps its pose relative to the forearm.
struct FEHLimbIK
{
	FName Upper;
	FName Lower;
	FName End;
	FVector Target = FVector::ZeroVector;
	FVector Pole = FVector(0, 0, -1);
	// Optional: after the reach, turn the end bone (with everything below it) to this component-space rotation, so a
	// hand can aim its knuckles or palm independently of the forearm's direction.
	bool bAimEnd = false;
	FQuat EndRotation = FQuat::Identity;
	// Optional anatomy: the elbow bends only on its hinge (each bone's hinge axis in its own space), so the upper arm's
	// roll and the forearm's neutral turn follow the elbow instead of the shortest rotation; and the hand's turn about
	// the forearm (pronation, supination) is shared along it by twist bones, as the radius rolls around the ulna.
	bool bHinge = false;
	FVector HingeUpper = FVector::ZeroVector;
	FVector HingeLower = FVector::ZeroVector;
	FName Twist[2];
	float TwistShare[2] = {0.5f, 0.85f};
	FQuat LowerToEndRef = FQuat::Identity;   // the end bone's rest rotation relative to the lower bone
	// Optional: straighten the wrist by this much (0..1) after the aim, turning the end bone so the line from it to
	// EndTip (the middle knuckle) runs on along the forearm, as a closed fist does to punch or guard.
	FName EndTip;
	float Straight = 0.0f;
	// Relative: Target is an offset (component space) from where the animation put the end bone, which keeps its
	// rotation; the arm reaches there on its hinge (a keyed clip nudged by a blow or lowered out of view).
	bool bRelative = false;
};

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
	float TransitionLegSeconds = 0.0f;

	// Proxy-owned state (animation thread).
	int32 HandledSerial = 0;
	float Elapsed = 0.0f;
	float Duration = 0.0f;
	float LegDuration = 0.0f;    // the legs' own decay time (>= Duration)
	TArray<uint8> IsLegBone;     // per compact bone: 1 for thighs, calves, feet, balls and hip half-joints
	float FrameDelta = 1.0f / 60.0f;
	TArray<FEHBoneOffset> Offsets;
	TArray<FTransform> Shown1;   // the pose displayed last frame
	TArray<FTransform> Shown2;   // and the frame before
	FEHLeg Legs[2];
	TArray<FEHAdditiveRotation> Additive;   // parents before children
	TArray<FEHLimbIK> LimbIK;
	int32 LegsForBones = -1;     // bone count the leg indices were resolved for
	float PlantedHeight = 0.0f;  // ankle height (component space) of the reference pose

private:
	void ResolveLegs(const FCompactPose& Pose);
	void LockFeet(FCompactPose& Pose, FCSPose<FCompactPose>& Target, float Fade);
	void ApplyAdditive(FCompactPose& Pose) const;
	void ApplyLimbIK(FCompactPose& Pose) const;
	// Turns Bone about its own origin by a component-space rotation (its children follow).
	static void RotateBoneCS(FCompactPose& Pose, const FCompactPoseBoneIndex Bone, const FQuat& DeltaCS);
	static FCompactPoseBoneIndex FindBone(const FCompactPose& Pose, const FName Name);
};

UCLASS(Transient, NotBlueprintable)
class UEHAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	void SetSample(UAnimSequence* Sequence, double Time);
	// Starts a transition to the sequence set this frame. Seconds <= 0 cuts with no blend. LegSeconds (when longer)
	// is the legs' own blend time.
	void BeginTransition(float Seconds, float LegSeconds = 0.0f);
	// Rotations added on top of the pose every frame until replaced; list parents before their children.
	void SetAdditive(const TArray<FEHAdditiveRotation>& InAdditive) { Additive = InAdditive; }
	void SetLimbIK(const TArray<FEHLimbIK>& InLimbs) { LimbIK = InLimbs; }

	FEHAnimSample Current;
	int32 TransitionSerial = 0;
	float TransitionSeconds = 0.0f;
	float TransitionLegSeconds = 0.0f;
	TArray<FEHAdditiveRotation> Additive;
	TArray<FEHLimbIK> LimbIK;

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FEHAnimProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }
};
