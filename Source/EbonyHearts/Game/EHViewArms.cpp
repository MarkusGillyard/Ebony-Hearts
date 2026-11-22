#include "EHViewArms.h"

#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EHAnimInstance.h"
#include "Engine/SkeletalMesh.h"
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
// Casts. Fireball: the left hand draws back beside the face while the fire gathers, then throws it forward.
// Ice Wall: both hands sink low and drive forward and up, raising the wall.
const FVector FireLoad(24.0f, -17.0f, -6.0f), FireOut(60.0f, -7.0f, -6.0f);
const FVector IceLoadL(30.0f, -16.0f, -34.0f), IceLoadR(30.0f, 16.0f, -34.0f);
const FVector IceOutL(54.0f, -17.0f, -6.0f), IceOutR(54.0f, 17.0f, -6.0f);

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
	USkeletalMesh* ArmsAsset = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/FPArms/SK_FPArms_Wren.SK_FPArms_Wren"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	FistPose = LoadObject<UAnimSequence>(nullptr, TEXT("/Game/Characters/Wren/Anims/A_Wren_Guard.A_Wren_Guard"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (ArmsAsset && FistPose)
	{
		ArmsMesh = NewObject<USkeletalMeshComponent>(GetOwner(), TEXT("FirstPersonArmsMesh"));
		ArmsMesh->SetupAttachment(this);
		ArmsMesh->SetSkeletalMesh(ArmsAsset);
		ArmsMesh->SetAnimInstanceClass(UEHAnimInstance::StaticClass());
		ArmsMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		ArmsMesh->SetCastShadow(false);
		// Without a physics asset its culling bounds come from the rest pose (arms out at the sides, below the eyes),
		// not from the posed fists in front of the view; widened so the arms are never culled while in view.
		ArmsMesh->SetBoundsScale(4.0f);
		ArmsMesh->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
		ArmsMesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		// The character model faces +Y; turned so it faces along the view.
		ArmsMesh->SetRelativeRotation(FRotator(0.0f, -90.0f, 0.0f));
		ArmsMesh->SetVisibility(false);
		ArmsMesh->RegisterComponent();
		if (UEHAnimInstance* A = Cast<UEHAnimInstance>(ArmsMesh->GetAnimInstance()))
		{
			A->SetSample(FistPose, 0.0);
		}
		BuildGlows();
		return;
	}
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
	BuildGlows();
}

void UEHViewArms::BuildGlows()
{
	UStaticMesh* Quad = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane.Plane"));
	UMaterialInterface* Add = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/VFX/M_VFX_Additive.M_VFX_Additive"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	UTexture* Tex = LoadObject<UTexture>(nullptr, TEXT("/Game/VFX/T_FX_Glow.T_FX_Glow"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!Quad || !Add)
	{
		return;
	}
	for (int32 H = 0; H < 2; ++H)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(GetOwner(), H == 0 ? TEXT("SpellGlowL") : TEXT("SpellGlowR"));
		if (ArmsMesh)
		{
			C->SetupAttachment(ArmsMesh, H == 0 ? TEXT("hand_l") : TEXT("hand_r"));
		}
		else
		{
			C->SetupAttachment(Arms[H].Fist ? static_cast<USceneComponent*>(Arms[H].Fist) : static_cast<USceneComponent*>(this));
		}
		C->SetStaticMesh(Quad);
		GlowMaterial[H] = UMaterialInstanceDynamic::Create(Add, this);
		if (Tex)
		{
			GlowMaterial[H]->SetTextureParameterValue(TEXT("Tex"), Tex);
		}
		C->SetMaterial(0, GlowMaterial[H]);
		C->SetUsingAbsoluteScale(true);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		C->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
		C->SetVisibility(false);
		C->RegisterComponent();
		Glow[H] = C;
	}
}

void UEHViewArms::SetGlow(int32 Hand, const FLinearColor& Color, float Amount)
{
	UStaticMeshComponent* C = Glow[Hand];
	if (C == nullptr)
	{
		return;
	}
	const bool bOn = Amount > 0.01f;
	C->SetVisibility(bOn);
	if (!bOn)
	{
		return;
	}
	// A quad facing the eyes, a little in front of the knuckles.
	const FVector Forward = GetComponentRotation().Vector();
	C->SetWorldRotation(FRotationMatrix::MakeFromZ(-Forward).Rotator());
	C->SetWorldScale3D(FVector(0.025f + 0.045f * Amount));
	GlowMaterial[Hand]->SetVectorParameterValue(TEXT("Color"), Color);
	GlowMaterial[Hand]->SetScalarParameterValue(TEXT("Intensity"), 2.0f + 6.0f * Amount);
}

void UEHViewArms::SetFirstPersonRendering(bool bOn)
{
	for (UStaticMeshComponent* C : Parts)
	{
		C->SetFirstPersonPrimitiveType(bOn ? EFirstPersonPrimitiveType::FirstPerson : EFirstPersonPrimitiveType::None);
	}
	if (ArmsMesh)
	{
		ArmsMesh->SetFirstPersonPrimitiveType(bOn ? EFirstPersonPrimitiveType::FirstPerson : EFirstPersonPrimitiveType::None);
	}
}

FString UEHViewArms::Describe() const
{
	if (!ArmsMesh)
	{
		return TEXT("arms=shapes");
	}
	const FTransform Cam = GetComponentTransform();
	auto Local = [&](FName Bone) { return Cam.InverseTransformPosition(ArmsMesh->GetBoneLocation(Bone, EBoneSpaces::WorldSpace)); };
	const FBoxSphereBounds B = ArmsMesh->Bounds;
	const FString Extra = FString::Printf(TEXT(" bounds=%s r=%.1f registered=%d renderstate=%d lod=%d hidden=%d mats=%d"), *Cam.InverseTransformPosition(B.Origin).ToCompactString(), B.SphereRadius,
		ArmsMesh->IsRegistered() ? 1 : 0, ArmsMesh->IsRenderStateCreated() ? 1 : 0, ArmsMesh->GetPredictedLODLevel(), ArmsMesh->bHiddenInGame ? 1 : 0, ArmsMesh->GetNumMaterials());
	return Extra + FString::Printf(TEXT(" arms=model visible=%d rel=%s head=%s upperarm_l=%s hand_l=%s hand_r=%s shownL=%s shownR=%s upperarm_r=%s lowerarm_r=%s"), ArmsMesh->IsVisible() ? 1 : 0,
		*ArmsMesh->GetRelativeLocation().ToCompactString(), *Local(TEXT("head")).ToCompactString(), *Local(TEXT("upperarm_l")).ToCompactString(),
		*Local(TEXT("hand_l")).ToCompactString(), *Local(TEXT("hand_r")).ToCompactString(), *ShownL.ToCompactString(), *ShownR.ToCompactString(),
		*Local(TEXT("upperarm_r")).ToCompactString(), *Local(TEXT("lowerarm_r")).ToCompactString());
}

void UEHViewArms::ShowParts(bool bShow)
{
	for (UStaticMeshComponent* C : Parts)
	{
		C->SetVisibility(bShow);
	}
	if (ArmsMesh)
	{
		ArmsMesh->SetVisibility(bShow);
	}
}

void UEHViewArms::PoseMeshArms(const FVector& L, const FVector& R)
{
	UEHAnimInstance* A = Cast<UEHAnimInstance>(ArmsMesh->GetAnimInstance());
	if (A == nullptr)
	{
		return;
	}
	A->SetSample(FistPose, 0.0);
	// The guard clip stands bladed, right shoulder back. Square the shoulders to the view, then turn them into each
	// blow: the straight drives the right shoulder through, the jab brings the left forward a little.
	const float ExtL = FMath::Clamp((L.X - ReadyL.X) / 22.0f, 0.0f, 1.0f);
	const float ExtR = FMath::Clamp((R.X - ReadyR.X) / 22.0f, 0.0f, 1.0f);
	const float Twist = -35.0f - 20.0f * Smooth(ExtR) + 10.0f * Smooth(ExtL);
	const FQuat Half = FRotator(0.0f, Twist * 0.5f, 0.0f).Quaternion();
	A->SetAdditive({{TEXT("spine_02"), Half}, {TEXT("spine_03"), Half}});
	// Place the model so its head sits just behind and below the eyes: its own shoulders then land where the
	// viewer's would.
	const FVector HeadCS = ArmsMesh->GetBoneLocation(TEXT("head"), EBoneSpaces::ComponentSpace);
	const FQuat RelRot = FRotator(0.0f, -90.0f, 0.0f).Quaternion();
	const FVector EyeToHead(-4.0f, 0.0f, 1.0f);   // puts this model's shoulders about 20 cm below the eyes
	const FVector RelLoc = EyeToHead - RelRot.RotateVector(HeadCS);
	ArmsMesh->SetRelativeLocation(RelLoc);
	auto ToCS = [&](const FVector& Cam) { return RelRot.UnrotateVector(Cam - RelLoc); };
	// The hand bone is the wrist: aim it a fist's length short of where the knuckles go.
	auto Wrist = [&](const FVector& Fist, const FVector& Shoulder) { return Fist - (Fist - Shoulder).GetSafeNormal() * 7.0f; };
	TArray<FEHLimbIK> Limbs;
	Limbs.Add({TEXT("upperarm_l"), TEXT("lowerarm_l"), TEXT("hand_l"), ToCS(Wrist(L, ShoulderL)), RelRot.UnrotateVector(FVector(0.0f, -0.55f, -1.0f))});
	Limbs.Add({TEXT("upperarm_r"), TEXT("lowerarm_r"), TEXT("hand_r"), ToCS(Wrist(R, ShoulderR)), RelRot.UnrotateVector(FVector(0.0f, 0.55f, -1.0f))});
	A->SetLimbIK(Limbs);
}

void UEHViewArms::SnapHidden()
{
	ShownL = RestL = DownL;
	ShownR = RestR = DownR;
	LastAction = EEHFistAction::None;
	Visible = 0.0f;
	bShown = false;
	ShowParts(false);
	SetGlow(0, FLinearColor::Black, 0.0f);
	SetGlow(1, FLinearColor::Black, 0.0f);
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
		case EEHFistAction::Fireball:
			L = StrikePath(StartL, FireLoad, FireOut, ReadyL, F, D);
			R = FMath::Lerp(StartR, ReadyR, GuardIn);
			break;
		default:
			L = StrikePath(StartL, IceLoadL, IceOutL, ReadyL, F, D);
			R = StrikePath(StartR, IceLoadR, IceOutR, ReadyR, F, D);
			break;
		}
		// The spell gathers in the hand through the wind-up and leaves it on release.
		const float Gather = EHIsSpell(Action) && F < D.Startup + D.Active ? Smooth(F / FMath::Max(1, D.Startup)) : 0.0f;
		SetGlow(0, Action == EEHFistAction::IceWall ? FLinearColor(0.45f, 0.75f, 1.0f) : FLinearColor(1.0f, 0.45f, 0.12f), Action == EEHFistAction::IceWall || Action == EEHFistAction::Fireball ? Gather : 0.0f);
		SetGlow(1, FLinearColor(0.45f, 0.75f, 1.0f), Action == EEHFistAction::IceWall ? Gather : 0.0f);
		Visible = 1.0f;
		RestL = L;
		RestR = R;
	}
	else
	{
		SetGlow(0, FLinearColor::Black, 0.0f);
		SetGlow(1, FLinearColor::Black, 0.0f);
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
	// Contact: the striking fist gives back a little into the arm and shudders while the hitstop holds, then eases out.
	if (Action != EEHFistAction::None && Fists.HasConnected() && Fists.InHitstop())
	{
		if (Recoil < 0.99f)
		{
			ShudderTime = 0.0f;
		}
		Recoil = 1.0f;
		ShudderTime += DeltaSeconds;
	}
	else
	{
		Recoil *= FMath::Exp(-DeltaSeconds / 0.05f);
	}
	if (Recoil > 0.01f && Action != EEHFistAction::None)
	{
		const float Shudder = Fists.InHitstop() ? FMath::Sin(ShudderTime * 2.0f * PI * 30.0f) * FMath::Exp(-ShudderTime * 12.0f) : 0.0f;
		const FVector Give = FVector(-2.8f, 0.0f, 0.0f) * Recoil + FVector(0.0f, 0.5f, 0.7f) * Shudder;
		if (Action == EEHFistAction::Jab)
		{
			L += Give;
		}
		if (Action == EEHFistAction::Straight)
		{
			R += Give;
		}
	}
	ShownL = L;
	ShownR = R;
	const bool bShow = Visible > 0.01f || Action != EEHFistAction::None;
	if (bShow != bShown)
	{
		bShown = bShow;
		ShowParts(bShow);
	}
	if (bShown && ArmsMesh)
	{
		PoseMeshArms(L, R);
	}
	else if (bShown)
	{
		PoseArm(Arms[0], ShoulderL, L, -1.0f);
		PoseArm(Arms[1], ShoulderR, R, 1.0f);
	}
}
