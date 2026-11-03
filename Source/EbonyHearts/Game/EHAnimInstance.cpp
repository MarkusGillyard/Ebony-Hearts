#include "EHAnimInstance.h"

#include "Animation/AnimNodeBase.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "AnimationRuntime.h"

void UEHAnimInstance::SetSamples(UAnimSequence* CurrentSeq, double CurrentTime, UAnimSequence* PreviousSeq, double PreviousTime, float InPreviousWeight)
{
	Current.Sequence = CurrentSeq;
	Current.Time = CurrentTime;
	Previous.Sequence = PreviousSeq;
	Previous.Time = PreviousTime;
	PreviousWeight = PreviousSeq ? FMath::Clamp(InPreviousWeight, 0.0f, 1.0f) : 0.0f;
}

void FEHAnimProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	const UEHAnimInstance* Instance = CastChecked<UEHAnimInstance>(InAnimInstance);
	Current = Instance->Current;
	Previous = Instance->Previous;
	PreviousWeight = Instance->PreviousWeight;
}

bool FEHAnimProxy::Evaluate(FPoseContext& Output)
{
	if (Current.Sequence == nullptr)
	{
		Output.ResetToRefPose();
		return true;
	}
	FAnimationPoseData OutData(Output);
	Current.Sequence->GetAnimationPose(OutData, FAnimExtractContext(Current.Time));
	if (Previous.Sequence != nullptr && PreviousWeight > KINDA_SMALL_NUMBER)
	{
		FPoseContext Other(Output);
		FAnimationPoseData OtherData(Other);
		Previous.Sequence->GetAnimationPose(OtherData, FAnimExtractContext(Previous.Time));
		FAnimationRuntime::BlendTwoPosesTogetherInPlace(OutData, OtherData, 1.0f - PreviousWeight);
	}
	return true;
}
