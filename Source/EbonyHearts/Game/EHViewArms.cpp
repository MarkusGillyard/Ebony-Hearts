#include "EHViewArms.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace EHArmsDetail
{
// Camera space, centimetres: X forward, Y right, Z up. The lead (left) hand jabs; the rear (right) hand throws the
// straight. Placeholder proportions for an adult.
const FVector ShoulderL(-4.0f, -18.0f, -20.0f);
const FVector ShoulderR(-4.0f, 18.0f, -20.0f);
constexpr float UpperLength = 31.0f;
constexpr float ForeLength = 30.0f;   // elbow to the middle of the fist
constexpr float FistRadius = 5.0f;

// At full extension a fist sits just below and beside the aim point, where the strike connects.
const FVector DownL(12.0f, -22.0f, -72.0f), DownR(12.0f, 22.0f, -72.0f);
const FVector ReadyL(40.0f, -12.0f, -15.0f), ReadyR(35.0f, 12.0f, -18.0f);
const FVector GuardL(34.0f, -7.0f, -2.0f), GuardR(32.0f, 7.0f, -3.0f);
const FVector JabLoad(33.0f, -13.0f, -14.0f), JabOut(60.0f, -4.0f, -5.0f);
const FVector StraightLoad(27.0f, 15.0f, -18.0f), StraightOut(62.0f, 1.0f, -5.0f);
const FVector ShoveLoadL(29.0f, -14.0f, -16.0f), ShoveLoadR(29.0f, 14.0f, -16.0f);
const FVector ShoveOutL(56.0f, -12.0f, -12.0f), ShoveOutR(56.0f, 12.0f, -12.0f);

float Smooth(float T) { T = FMath::Clamp(T, 0.0f, 1.0f); return T * T * (3.0f - 2.0f * T); }
float Accelerate(float T) { T = FMath::Clamp(T, 0.0f, 1.0f); return T * T; }
float Decelerate(float T) { T = FMath::Clamp(T, 0.0f, 1.0f); return 1.0f - (1.0f - T) * (1.0f - T); }

// A strike's path for the hand that throws it: a short load, then an accelerating extension that arrives on the
// first active frame, a hold while it can connect, and a return to the guard.
FVector StrikePath(const FVector& Start, const FVector& Load, const FVector& Out, const FVector& Back, float F, const FEHStrikeDef& D)
{
	if (F < D.Startup)
	{
		const float U = F / D.Startup;
		constexpr float LoadShare = 0.35f;
		return U < LoadShare ? FMath::Lerp(Start, Load, Smooth(U / LoadShare)) : FMath::Lerp(Load, Out, Accelerate((U - LoadShare) / (1.0f - LoadShare)));
	}
	if (F < D.Startup + D.Active)
	{
		return Out;
	}
	return FMath::Lerp(Out, Back, Decelerate((F - D.Startup - D.Active) / FMath::Max(1, D.Recovery)));
}
}
using namespace EHArmsDetail;

UEHViewArms::UEHViewArms()
{
	PrimaryComponentTick.bCanEverTick = false;
	ShownL = RestL = DownL;
	ShownR = RestR = DownR;
}

UStaticMeshComponent* UEHViewArms::MakePart(UStaticMesh* Mesh, UMaterialInstanceDynamic* Material)
{
	UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(GetOwner());
	C->SetupAttachment(this);
	C->SetStaticMesh(Mesh);
	C->SetMaterial(0, Material);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->SetCastShadow(false);
	C->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
	C->SetVisibility(false);
	C->RegisterComponent();
	Parts.Add(C);
	return C;
}

void UEHViewArms::Build()
{
	UStaticMesh* Cylinder = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	if (!Cylinder || !Sphere || !Base)
	{
		return;
	}
	SkinMaterial = UMaterialInstanceDynamic::Create(Base, this);
	SkinMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.34f, 0.22f, 0.16f));
	WrapMaterial = UMaterialInstanceDynamic::Create(Base, this);
	WrapMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.09f, 0.08f, 0.075f));
	for (FArm& A : Arms)
	{
		A.Upper = MakePart(Cylinder, WrapMaterial);
		A.Fore = MakePart(Cylinder, SkinMaterial);
		A.Fist = MakePart(Sphere, WrapMaterial);
	}
}

void UEHViewArms::SetFirstPersonRendering(bool bOn)
{
	for (UStaticMeshComponent* C : Parts)
	{
		C->SetFirstPersonPrimitiveType(bOn ? EFirstPersonPrimitiveType::FirstPerson : EFirstPersonPrimitiveType::None);
	}
}

void UEHViewArms::SnapHidden()
{
	ShownL = RestL = DownL;
	ShownR = RestR = DownR;
	LastAction = EEHFistAction::None;
	Visible = 0.0f;
	bShown = false;
	for (UStaticMeshComponent* C : Parts)
	{
		C->SetVisibility(false);
	}
}

void UEHViewArms::PoseArm(FArm& Arm, const FVector& Shoulder, const FVector& Hand, float Side)
{
	if (!Arm.Upper)
	{
		return;
	}
	// Two-bone IK, the elbow dropping down and slightly out.
	FVector ToHand = Hand - Shoulder;
	const float Reach = UpperLength + ForeLength - 0.01f;
	const float D = FMath::Clamp(ToHand.Size(), 1.0f, Reach);
	const FVector Dir = ToHand.GetSafeNormal();
	const FVector HandAt = Shoulder + Dir * D;
	FVector Pole = FVector(0.0f, Side * 0.55f, -1.0f);
	Pole = (Pole - Dir * FVector::DotProduct(Pole, Dir)).GetSafeNormal();
	const float X = (UpperLength * UpperLength - ForeLength * ForeLength + D * D) / (2.0f * D);
	const float H = FMath::Sqrt(FMath::Max(0.0f, UpperLength * UpperLength - X * X));
	const FVector Elbow = Shoulder + Dir * X + Pole * H;
	auto Segment = [](UStaticMeshComponent* C, const FVector& A, const FVector& B, float Radius) {
		const FVector Axis = B - A;
		C->SetRelativeLocationAndRotation((A + B) * 0.5f, FRotationMatrix::MakeFromZ(Axis.GetSafeNormal()).Rotator());
		C->SetRelativeScale3D(FVector(Radius / 50.0f, Radius / 50.0f, FMath::Max(Axis.Size(), 0.1f) / 100.0f));
	};
	const FVector Wrist = HandAt - (HandAt - Elbow).GetSafeNormal() * FistRadius;
	Segment(Arm.Upper, Shoulder, Elbow, 5.2f);
	Segment(Arm.Fore, Elbow, Wrist, 4.3f);
	Arm.Fist->SetRelativeLocationAndRotation(HandAt, FRotationMatrix::MakeFromX((HandAt - Elbow).GetSafeNormal()).Rotator());
	Arm.Fist->SetRelativeScale3D(FVector(FistRadius * 2.2f, FistRadius * 1.9f, FistRadius * 1.7f) / 100.0f);
}

void UEHViewArms::UpdateArms(const FEHFists& Fists, float Alpha, float DeltaSeconds)
{
	const EEHFistAction Action = Fists.Action();
	if (Action != LastAction)
	{
		// A new technique starts from wherever the fists are shown now.
		StartL = ShownL;
		StartR = ShownR;
		LastAction = Action;
	}
	const FEHFistTuning& T = Fists.GetTuning();
	FVector L, R;
	if (Action != EEHFistAction::None)
	{
		const FEHStrikeDef& D = T.Def(Action);
		const float F = static_cast<float>(Fists.Frame()) + (Fists.InHitstop() ? 0.0f : Alpha);
		const float GuardIn = Smooth(F / FMath::Max(1, D.Startup));
		switch (Action)
		{
		case EEHFistAction::Jab:
			L = StrikePath(StartL, JabLoad, JabOut, ReadyL, F, D);
			R = FMath::Lerp(StartR, ReadyR, GuardIn);
			break;
		case EEHFistAction::Straight:
			R = StrikePath(StartR, StraightLoad, StraightOut, ReadyR, F, D);
			L = FMath::Lerp(StartL, ReadyL, GuardIn);
			break;
		default:
			L = StrikePath(StartL, ShoveLoadL, ShoveOutL, ReadyL, F, D);
			R = StrikePath(StartR, ShoveLoadR, ShoveOutR, ReadyR, F, D);
			break;
		}
		Visible = 1.0f;
		RestL = L;
		RestR = R;
	}
	else
	{
		// Between techniques the fists settle: up in the guard while it is held, at the ready for a moment after a
		// technique, then down out of view.
		const float Guard = Fists.GuardLevel();
		const bool bUp = Guard > 0.0f || Fists.IdleSeconds() < T.ArmsLinger;
		Visible = FMath::FInterpConstantTo(Visible, bUp ? 1.0f : 0.0f, DeltaSeconds, bUp ? 8.0f : 4.0f);
		const float V = Smooth(Visible);
		const FVector TargetL = FMath::Lerp(DownL, FMath::Lerp(ReadyL, GuardL, Smooth(Guard)), V);
		const FVector TargetR = FMath::Lerp(DownR, FMath::Lerp(ReadyR, GuardR, Smooth(Guard)), V);
		const float K = 1.0f - FMath::Exp(-DeltaSeconds / 0.05f);
		RestL = FMath::Lerp(RestL, TargetL, K);
		RestR = FMath::Lerp(RestR, TargetR, K);
		L = RestL;
		R = RestR;
	}
	ShownL = L;
	ShownR = R;
	const bool bShow = Visible > 0.01f || Action != EEHFistAction::None;
	if (bShow != bShown)
	{
		bShown = bShow;
		for (UStaticMeshComponent* C : Parts)
		{
			C->SetVisibility(bShow);
		}
	}
	if (bShown)
	{
		PoseArm(Arms[0], ShoulderL, L, -1.0f);
		PoseArm(Arms[1], ShoulderR, R, 1.0f);
	}
}
