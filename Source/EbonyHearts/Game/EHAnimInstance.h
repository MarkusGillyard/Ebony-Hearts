// Pose = sequence sampled at a time chosen by the simulation, cross-faded from the previous sequence.
// The game thread sets the two samples every frame; nothing here advances time on its own, so animation
// stays locked to combat frames (and freezes during hitstop) regardless of the render rate.
#pragma once

#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "CoreMinimal.h"

#include "EHAnimInstance.generated.h"

class UAnimSequence;

struct FEHAnimSample
{
	TObjectPtr<UAnimSequence> Sequence = nullptr;
	double Time = 0.0;
};

struct FEHAnimProxy : public FAnimInstanceProxy
{
	FEHAnimProxy() = default;
	explicit FEHAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}

	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

	FEHAnimSample Current;
	FEHAnimSample Previous;
	float PreviousWeight = 0.0f;
};

UCLASS(Transient, NotBlueprintable)
class UEHAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:
	void SetSamples(UAnimSequence* CurrentSeq, double CurrentTime, UAnimSequence* PreviousSeq, double PreviousTime, float PreviousWeight);

	FEHAnimSample Current;
	FEHAnimSample Previous;
	float PreviousWeight = 0.0f;

protected:
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FEHAnimProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete InProxy; }
};
