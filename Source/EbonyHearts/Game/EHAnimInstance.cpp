#include "EHAnimInstance.h"

#include "Animation/AnimNodeBase.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "TwoBoneIK.h"

namespace EHInertialDetail
{
// Offset remaining at time t of a decay from x0 (>= 0) with initial speed v0 over t1 seconds. Quintic with zero speed and
// acceleration at the end; the initial speed is clamped so the offset never grows, and the duration shortened so the
// curve never overshoots zero.
float Decay(float X0, float V0, float T, float T1)
{
	if (X0 <= 1e-6f || T1 <= 1e-6f || T >= T1)
	{
		return 0.0f;
	}
	V0 = FMath::Min(V0, 0.0f);
	if (V0 < 0.0f)
	{
		T1 = FMath::Min(T1, -5.0f * X0 / V0);
		if (T >= T1)
		{
			return 0.0f;
		}
	}
	const float T1_2 = T1 * T1;
	const float A0 = FMath::Max(0.0f, (-8.0f * V0 * T1 - 20.0f * X0) / T1_2);
	const float A = -(A0 * T1_2 + 6.0f * V0 * T1 + 12.0f * X0) / (2.0f * T1_2 * T1_2 * T1);
	const float B = (3.0f * A0 * T1_2 + 16.0f * V0 * T1 + 30.0f * X0) / (2.0f * T1_2 * T1_2);
	const float C = -(3.0f * A0 * T1_2 + 12.0f * V0 * T1 + 20.0f * X0) / (2.0f * T1_2 * T1);
	const float X = ((((A * T + B) * T + C) * T + 0.5f * A0) * T + V0) * T + X0;
	return FMath::Clamp(X, 0.0f, X0);
}

FQuat Shortest(const FQuat& Q)
{
	return Q.W < 0.0 ? FQuat(-Q.X, -Q.Y, -Q.Z, -Q.W) : Q;
}

// A foot counts as planted up to this height above the reference pose's ankle, and not at all from FullLift up.
constexpr float PlantedSlack = 3.0f;
constexpr float FullLift = 10.0f;

float Planted(float AnkleZ, float RestZ)
{
	return 1.0f - FMath::Clamp((AnkleZ - RestZ - PlantedSlack) / (FullLift - PlantedSlack), 0.0f, 1.0f);
}

int32 CompactIndex(const FBoneContainer& Bones, const TCHAR* Name)
{
	const int32 Mesh = Bones.GetPoseBoneIndexForBoneName(FName(Name));
	return Mesh == INDEX_NONE ? -1 : Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Mesh)).GetInt();
}
}
using namespace EHInertialDetail;

void UEHAnimInstance::SetSample(UAnimSequence* Sequence, double Time)
{
	Current.Sequence = Sequence;
	Current.Time = Time;
}

void UEHAnimInstance::BeginTransition(float Seconds)
{
	++TransitionSerial;
	TransitionSeconds = Seconds;
}

void FEHAnimProxy::ResolveLegs(const FCompactPose& Pose)
{
	const FBoneContainer& Bones = Pose.GetBoneContainer();
	static const TCHAR* Names[2][4] = {{TEXT("thigh_l"), TEXT("calf_l"), TEXT("foot_l"), TEXT("thigh_half_l")},
	                                   {TEXT("thigh_r"), TEXT("calf_r"), TEXT("foot_r"), TEXT("thigh_half_r")}};
	for (int32 S = 0; S < 2; ++S)
	{
		Legs[S] = FEHLeg();
		Legs[S].Thigh = CompactIndex(Bones, Names[S][0]);
		Legs[S].Calf = CompactIndex(Bones, Names[S][1]);
		Legs[S].Foot = CompactIndex(Bones, Names[S][2]);
		Legs[S].ThighHalf = CompactIndex(Bones, Names[S][3]);
	}
	PlantedHeight = 0.0f;
	if (Legs[0].Foot >= 0)
	{
		FCompactPose Ref;
		Ref.SetBoneContainer(&Bones);
		Ref.ResetToRefPose();
		FCSPose<FCompactPose> RefCS;
		RefCS.InitPose(Ref);
		PlantedHeight = static_cast<float>(RefCS.GetComponentSpaceTransform(FCompactPoseBoneIndex(Legs[0].Foot)).GetLocation().Z);
	}
	LegsForBones = Pose.GetNumBones();
}

void FEHAnimProxy::LockFeet(FCompactPose& Pose, FCSPose<FCompactPose>& Target, float Fade)
{
	FCSPose<FCompactPose> Shown;
	Shown.InitPose(Pose);
	TArray<FBoneTransform> Out;
	for (FEHLeg& Leg : Legs)
	{
		if (Leg.Weight <= 0.0f || Leg.Thigh < 0 || Leg.Calf < 0 || Leg.Foot < 0)
		{
			continue;
		}
		const FCompactPoseBoneIndex ThighI(Leg.Thigh), CalfI(Leg.Calf), FootI(Leg.Foot);
		FTransform Thigh = Shown.GetComponentSpaceTransform(ThighI);
		FTransform Calf = Shown.GetComponentSpaceTransform(CalfI);
		FTransform Foot = Shown.GetComponentSpaceTransform(FootI);
		const FVector Goal = Target.GetComponentSpaceTransform(FootI).GetLocation() + Leg.FootFrom * Fade;
		const FVector Effector = FMath::Lerp(Foot.GetLocation(), Goal, Leg.Weight);
		// Keep the knee bending the way it bends now.
		const FVector Mid = (Thigh.GetLocation() + Foot.GetLocation()) * 0.5;
		const FVector KneeTarget = Calf.GetLocation() + (Calf.GetLocation() - Mid) * 4.0;
		AnimationCore::SolveTwoBoneIK(Thigh, Calf, Foot, KneeTarget, Effector, false, 1.0, 1.0);
		Out.Add(FBoneTransform(ThighI, Thigh));
		Out.Add(FBoneTransform(CalfI, Calf));
		Out.Add(FBoneTransform(FootI, Foot));
	}
	if (Out.Num() == 0)
	{
		return;
	}
	Out.Sort(FCompareBoneTransformIndex());
	Shown.SafeSetCSBoneTransforms(Out);
	FCSPose<FCompactPose>::ConvertComponentPosesToLocalPoses(Shown, Pose);
	// The hip half-joints take half the thigh's new swing from its reference, as the animations key them.
	for (const FEHLeg& Leg : Legs)
	{
		if (Leg.Weight <= 0.0f || Leg.ThighHalf < 0 || Leg.Calf < 0)
		{
			continue;
		}
		const FCompactPoseBoneIndex ThighI(Leg.Thigh), HalfI(Leg.ThighHalf);
		const FQuat RefThigh = Pose.GetRefPose(ThighI).GetRotation();
		const FVector Axis = Pose.GetRefPose(FCompactPoseBoneIndex(Leg.Calf)).GetTranslation().GetSafeNormal();
		const FQuat Delta = RefThigh.Inverse() * Pose[ThighI].GetRotation();
		const FQuat Swing = FQuat::FindBetweenNormals(Axis, Delta.RotateVector(Axis));
		Pose[HalfI].SetRotation(Pose.GetRefPose(HalfI).GetRotation() * FQuat::Slerp(FQuat::Identity, Swing, 0.5f));
	}
}

void FEHAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	const UEHAnimInstance* Instance = CastChecked<UEHAnimInstance>(InAnimInstance);
	Current = Instance->Current;
	TransitionSerial = Instance->TransitionSerial;
	TransitionSeconds = Instance->TransitionSeconds;
	FrameDelta = FMath::Max(DeltaSeconds, 1e-4f);
	Elapsed = FMath::Min(Elapsed + DeltaSeconds, 1.0e6f);
}

bool FEHAnimProxy::Evaluate(FPoseContext& Output)
{
	if (Current.Sequence == nullptr)
	{
		Output.ResetToRefPose();
		Shown1.Reset();
		Shown2.Reset();
		Offsets.Reset();
		return true;
	}
	FAnimationPoseData OutData(Output);
	Current.Sequence->GetAnimationPose(OutData, FAnimExtractContext(Current.Time));
	FCompactPose& Pose = Output.Pose;
	const int32 NumBones = Pose.GetNumBones();
	if (LegsForBones != NumBones)
	{
		ResolveLegs(Pose);
	}
	// The new animation's own pose, before any transition offset: where its feet are planted.
	FCSPose<FCompactPose> Target;
	const bool bTransition = TransitionSerial != HandledSerial || (Offsets.Num() == NumBones && Elapsed < Duration);
	if (bTransition && Legs[0].Foot >= 0)
	{
		Target.InitPose(Pose);
	}

	if (TransitionSerial != HandledSerial)
	{
		HandledSerial = TransitionSerial;
		Offsets.Reset();
		Elapsed = 0.0f;
		Duration = TransitionSeconds;
		for (FEHLeg& Leg : Legs)
		{
			Leg.Weight = 0.0f;
		}
		if (Duration > 0.0f && Shown1.Num() == NumBones && Legs[0].Foot >= 0)
		{
			// Each foot planted in both the shown pose and the new one eases from one to the other.
			FCompactPose Old;
			Old.CopyBonesFrom(Pose);
			for (const FCompactPoseBoneIndex Bone : Old.ForEachBoneIndex())
			{
				Old[Bone] = Shown1[Bone.GetInt()];
			}
			FCSPose<FCompactPose> OldCS;
			OldCS.InitPose(Old);
			for (FEHLeg& Leg : Legs)
			{
				if (Leg.Foot < 0)
				{
					continue;
				}
				const FCompactPoseBoneIndex FootI(Leg.Foot);
				const FVector From = OldCS.GetComponentSpaceTransform(FootI).GetLocation();
				const FVector To = Target.GetComponentSpaceTransform(FootI).GetLocation();
				Leg.FootFrom = From - To;
				Leg.Weight = FMath::Min(Planted(static_cast<float>(From.Z), PlantedHeight), Planted(static_cast<float>(To.Z), PlantedHeight));
			}
		}
		if (Duration > 0.0f && Shown1.Num() == NumBones)
		{
			const bool bSpeed = Shown2.Num() == NumBones;
			Offsets.SetNum(NumBones);
			for (const FCompactPoseBoneIndex Bone : Pose.ForEachBoneIndex())
			{
				const int32 I = Bone.GetInt();
				const FTransform& Now = Pose[Bone];
				FEHBoneOffset& O = Offsets[I];
				// Rotation offset applied on the left: shown = offset * new.
				FVector Axis;
				double Angle = 0.0;
				Shortest(Shown1[I].GetRotation() * Now.GetRotation().Inverse()).ToAxisAndAngle(Axis, Angle);
				if (Angle > 1e-5)
				{
					O.Axis = FVector3f(Axis);
					O.Angle = static_cast<float>(Angle);
					if (bSpeed)
					{
						FVector SpinAxis;
						double Spin = 0.0;
						Shortest(Shown1[I].GetRotation() * Shown2[I].GetRotation().Inverse()).ToAxisAndAngle(SpinAxis, Spin);
						O.AngleSpeed = static_cast<float>(FVector::DotProduct(SpinAxis * Spin, Axis)) / FrameDelta;
					}
				}
				const FVector Move = Shown1[I].GetTranslation() - Now.GetTranslation();
				const double Dist = Move.Size();
				if (Dist > 1e-4)
				{
					O.Dir = FVector3f(Move / Dist);
					O.Dist = static_cast<float>(Dist);
					if (bSpeed)
					{
						const FVector Vel = (Shown1[I].GetTranslation() - Shown2[I].GetTranslation()) / FrameDelta;
						O.DistSpeed = static_cast<float>(FVector::DotProduct(Vel, Move / Dist));
					}
				}
			}
		}
	}

	if (Offsets.Num() == NumBones && Elapsed < Duration)
	{
		for (const FCompactPoseBoneIndex Bone : Pose.ForEachBoneIndex())
		{
			const FEHBoneOffset& O = Offsets[Bone.GetInt()];
			FTransform& T = Pose[Bone];
			const float Angle = Decay(O.Angle, O.AngleSpeed, Elapsed, Duration);
			if (Angle > 0.0f)
			{
				T.SetRotation((FQuat(FVector(O.Axis), Angle) * T.GetRotation()).GetNormalized());
			}
			const float Dist = Decay(O.Dist, O.DistSpeed, Elapsed, Duration);
			if (Dist > 0.0f)
			{
				T.AddToTranslation(FVector(O.Dir) * Dist);
			}
		}
		if (Legs[0].Foot >= 0)
		{
			LockFeet(Pose, Target, Decay(1.0f, 0.0f, Elapsed, Duration));
		}
	}
	else if (Offsets.Num() > 0 && Elapsed >= Duration)
	{
		Offsets.Reset();
	}

	// Remember what was shown for the next transition's offset and speed.
	Swap(Shown1, Shown2);
	Shown1.SetNum(NumBones, EAllowShrinking::No);
	for (const FCompactPoseBoneIndex Bone : Pose.ForEachBoneIndex())
	{
		Shown1[Bone.GetInt()] = Pose[Bone];
	}
	return true;
}
