#include "EHViewArms.h"

#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EHAnimInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "AnimationRuntime.h"
#include "Materials/MaterialInterface.h"
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
FVector StrikePath(const FVector& Start, const FVector& Load, const FVector& Out, const FVector& Back, float F, const FEHStrikeDef& D, bool bSnap = false)
{
	if (F < D.Startup)
	{
		const float U = F / D.Startup;
		if (bSnap)
		{
			// The snap: a quick, compact load (the shoulder drawing back), then a release that starts slow and finishes
			// very fast, so nearly all the distance is covered in the last frames before the hit.
			constexpr float LoadShare = 0.30f;
			if (U < LoadShare)
			{
				return FMath::Lerp(Start, Load, Smooth(U / LoadShare));
			}
			const float R = (U - LoadShare) / (1.0f - LoadShare);
			return FMath::Lerp(Load, Out, R * R * R);
		}
		constexpr float LoadShare = 0.35f;
		return U < LoadShare ? FMath::Lerp(Start, Load, Smooth(U / LoadShare)) : FMath::Lerp(Load, Out, Accelerate((U - LoadShare) / (1.0f - LoadShare)));
	}
	if (F < D.Startup + D.Active)
	{
		if (bSnap)
		{
			// Arrives on the first active frame, drives a little through the target, settles back.
			const float A = (F - D.Startup) / FMath::Max(1, D.Active);
			return Out + (Out - Load).GetSafeNormal() * 3.0f * FMath::Sin(A * PI);
		}
		return Out;
	}
	const float T = (F - D.Startup - D.Active) / FMath::Max(1, D.Recovery);
	if (bSnap)
	{
		// Follow-through: the fist drops a little as the arm relaxes on the way back to the guard.
		return FMath::Lerp(Out, Back, Decelerate(T)) + FVector(0.0f, 0.0f, -2.5f * FMath::Sin(FMath::Clamp(T, 0.0f, 1.0f) * PI));
	}
	return FMath::Lerp(Out, Back, Decelerate(T));
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
	// The realistic hands come first; Wren's cut arms (with her guard clip) and then plain shapes are fallbacks.
	if (USkeletalMesh* Hands = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/FPHands/SK_FPHands.SK_FPHands"), nullptr, LOAD_NoWarn | LOAD_Quiet))
	{
		ArmsMesh = NewObject<USkeletalMeshComponent>(GetOwner(), TEXT("FirstPersonArmsMesh"));
		ArmsMesh->SetupAttachment(this);
		ArmsMesh->SetSkeletalMesh(Hands);
		ArmsMesh->SetAnimInstanceClass(UEHAnimInstance::StaticClass());
		ArmsMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		ArmsMesh->SetCastShadow(false);
		ArmsMesh->SetBoundsScale(4.0f);
		ArmsMesh->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
		ArmsMesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
		ArmsMesh->SetRelativeRotation(FRotator(0.0f, -90.0f, 0.0f));
		ArmsMesh->SetVisibility(false);
		ArmsMesh->RegisterComponent();
		FistPose = nullptr;
		bRealHands = true;
		CacheHandFrames();
		BuildGlows();
		return;
	}
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
	FString HandDbg;
	if (bRealHands)
	{
		for (const TCHAR* S : {TEXT("l"), TEXT("r")})
		{
			auto BoneAt = [&](const TCHAR* N) { return Local(FName(*FString::Printf(TEXT("%s_%s"), N, S))); };
			for (const TCHAR* D : {TEXT("thumb"), TEXT("index"), TEXT("middle"), TEXT("ring"), TEXT("pinky")})
			{
				const FVector Root = BoneAt(*FString::Printf(TEXT("%s_01"), D));
				const FVector Tip = BoneAt(*FString::Printf(TEXT("%s_03"), D));
				HandDbg += FString::Printf(TEXT(" %s_%s(root-hand=%s tip-root=%s)"), D, S, *(Root - BoneAt(TEXT("hand"))).ToCompactString(), *(Tip - Root).ToCompactString());
			}
			HandDbg += FString::Printf(TEXT(" %s: knuckles=%s middle_tip=%s index_tip=%s thumb_tip=%s curl=%.2f pron=%.0f"), S,
				*(BoneAt(TEXT("middle_01")) - BoneAt(TEXT("hand"))).GetSafeNormal().ToCompactString(), *(BoneAt(TEXT("middle_03")) - BoneAt(TEXT("middle_01"))).ToCompactString(),
				*(BoneAt(TEXT("index_03")) - BoneAt(TEXT("index_01"))).ToCompactString(), *(BoneAt(TEXT("thumb_03")) - BoneAt(TEXT("hand"))).ToCompactString(),
				Curl[S[0] == 'l' ? 0 : 1], Pronate[S[0] == 'l' ? 0 : 1]);
		}
	}
	return Extra + HandDbg + FString::Printf(TEXT(" arms=model visible=%d rel=%s head=%s upperarm_l=%s hand_l=%s hand_r=%s shownL=%s shownR=%s upperarm_r=%s lowerarm_r=%s"), ArmsMesh->IsVisible() ? 1 : 0,
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
	// blow: the straight drives the right shoulder through, the jab brings the left forward a little. (The realistic
	// hands' rest pose is already square.)
	const float ExtL = FMath::Clamp((L.X - ReadyL.X) / 22.0f, 0.0f, 1.0f);
	const float ExtR = FMath::Clamp((R.X - ReadyR.X) / 22.0f, 0.0f, 1.0f);
	const float Twist = (bRealHands ? 0.0f : -35.0f) - 20.0f * Smooth(ExtR) + 10.0f * Smooth(ExtL);
	const FQuat Half = FRotator(0.0f, Twist * 0.5f, 0.0f).Quaternion();
	TArray<FEHAdditiveRotation> Add = {{TEXT("spine_02"), Half}, {TEXT("spine_03"), Half}};
	if (bRealHands)
	{
		AddHandRotations(Add, 0);
		AddHandRotations(Add, 1);
	}
	A->SetAdditive(Add);
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
	if (bRealHands)
	{
		// Aim each hand: the knuckles toward the target (a little inward and up), the palm turned from facing inward
		// (a vertical fist) toward facing down as it pronates; bent back, the knuckles lift and the palm faces forward
		// (an open, pushing hand).
		const FQuat CamToCS = RelRot.Inverse();
		for (int32 H = 0; H < 2; ++H)
		{
			const float In = H == 0 ? 1.0f : -1.0f;   // toward the midline (camera Y), for this hand
			const FVector Fist = H == 0 ? L : R;
			FVector Fwd = FVector(1.0f, 0.14f * In, 0.32f).GetSafeNormal();
			const float P = FMath::DegreesToRadians(Pronate[H]);
			FVector PalmDir = FVector(0.0f, In * FMath::Cos(P), -FMath::Sin(P));
			const float B = FMath::DegreesToRadians(Bend[H]);
			Fwd = (Fwd * FMath::Cos(B) + FVector(0.0f, 0.0f, 1.0f) * FMath::Sin(B)).GetSafeNormal();
			PalmDir = (PalmDir * FMath::Cos(B) + FVector(1.0f, 0.0f, 0.0f) * FMath::Sin(B)).GetSafeNormal();
			// The high guard, a forearm shield: fists up, knuckles to the sky, the backs of the hands and forearms turned
			// toward the threat (and the viewer sees the backs of them, the way a raised block looks from behind it).
			if (GuardW > 0.01f)
			{
				const FVector GFwd = FVector(0.25f, 0.12f * In, 1.0f).GetSafeNormal();
				const FVector GPalm = FVector(0.55f, 0.85f * In, 0.0f).GetSafeNormal();
				Fwd = FMath::Lerp(Fwd, GFwd, GuardW).GetSafeNormal();
				PalmDir = FMath::Lerp(PalmDir, GPalm, GuardW).GetSafeNormal();
			}
			Limbs[H].bAimEnd = true;
			Limbs[H].EndRotation = AimHand(H, Fwd, PalmDir, CamToCS);
			(void)Fist;
		}
	}
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
	// The realistic arm is about 5 cm shorter to the wrist than the placeholder's: its targets are drawn in toward the
	// shoulder line (scaled forward distance) and lifted a little, so a full extension reaches the middle of the view.
	auto Real = [this](FVector V) { return bRealHands ? FVector(4.0f + V.X * 0.88f, V.Y, V.Z + 3.0f) : V; };
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
			L = StrikePath(StartL, JabLoad, JabOut, ReadyL, F, D, bRealHands);
			R = FMath::Lerp(StartR, ReadyR, GuardIn);
			break;
		case EEHFistAction::Straight:
			R = StrikePath(StartR, StraightLoad, StraightOut, ReadyR, F, D, bRealHands);
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
		// The realistic hands guard lower and further out than the placeholder (chin height, not eye height), so the
		// fists read as fists rather than filling the view from above.
		// The realistic hands' guard is a high block: fists up beside the face, forearms upright in front of it.
		const FVector GL = bRealHands ? FVector(36.0f, -12.0f, -10.0f) : GuardL;
		const FVector GR = bRealHands ? FVector(35.0f, 12.0f, -11.0f) : GuardR;
		const FVector TargetL = FMath::Lerp(DownL, FMath::Lerp(ReadyL, GL, Smooth(Guard)), V);
		const FVector TargetR = FMath::Lerp(DownR, FMath::Lerp(ReadyR, GR, Smooth(Guard)), V);
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
	// A blow landing on the guard drives both fists back toward the face; a strike stopped by a guard rebounds.
	GuardShock *= FMath::Exp(-DeltaSeconds / 0.09f);
	Rebound *= FMath::Exp(-DeltaSeconds / 0.07f);
	if (GuardShock > 0.01f)
	{
		L += FVector(-5.0f, 1.0f, 2.0f) * GuardShock;
		R += FVector(-5.0f, -1.0f, 2.0f) * GuardShock;
	}
	if (Rebound > 0.01f)
	{
		(ReboundHand == 0 ? L : R) += FVector(-7.0f, 0.0f, 1.5f) * Rebound;
	}
	L = Real(L);
	R = Real(R);
	ShownL = L;
	ShownR = R;
	if (bRealHands)
	{
		UpdateHandTargets(Fists, DeltaSeconds);
	}
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

void UEHViewArms::CacheHandFrames()
{
	// Each hand's axes, from the rest pose in component space, so finger curls, the wrist's turn and the hand's bend
	// act about anatomical axes whichever way the skeleton's bones happen to be rolled.
	const USkinnedAsset* Asset = ArmsMesh ? ArmsMesh->GetSkinnedAsset() : nullptr;
	if (Asset == nullptr)
	{
		return;
	}
	const FReferenceSkeleton& Ref = Asset->GetRefSkeleton();
	auto Pos = [&](const TCHAR* Name) -> FVector {
		const int32 I = Ref.FindBoneIndex(Name);
		return I == INDEX_NONE ? FVector::ZeroVector : FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, I).GetLocation();
	};
	for (int32 H = 0; H < 2; ++H)
	{
		const TCHAR* S = H == 0 ? TEXT("l") : TEXT("r");
		auto P = [&](const TCHAR* Bone) { return Pos(*FString::Printf(TEXT("%s_%s"), Bone, S)); };
		FHandFrame& F = HandFrames[H];
		const FVector Wrist = P(TEXT("hand")), Elbow = P(TEXT("lowerarm"));
		const FVector Index = P(TEXT("index_01")), Pinky = P(TEXT("pinky_01")), MiddleTip = P(TEXT("middle_03"));
		F.Lateral = (Pinky - Index).GetSafeNormal();
		F.Forearm = (Wrist - Elbow).GetSafeNormal();
		const FVector HandDir = (MiddleTip - Wrist).GetSafeNormal();
		// Out of the palm: perpendicular to the knuckles' direction and to the line across them, on the side where the
		// thumb sits (the rest pose's palms face partly backward, not simply toward the body).
		FVector Palm = FVector::CrossProduct(HandDir, F.Lateral).GetSafeNormal();
		if (FVector::DotProduct(Palm, P(TEXT("thumb_03")) - Wrist) < 0.0f)
		{
			Palm = -Palm;
		}
		// Rotating d about axis a by +angle moves it along (a x d); flexion moves the fingers toward the palm.
		F.FlexSign = FVector::DotProduct(FVector::CrossProduct(F.Lateral, HandDir), Palm) >= 0.0f ? 1.0f : -1.0f;
		// Pronation turns the palm to face down.
		F.PronateSign = FVector::DotProduct(FVector::CrossProduct(F.Forearm, Palm), FVector(0.0f, 0.0f, -1.0f)) >= 0.0f ? 1.0f : -1.0f;
		const FVector ThumbDir = (P(TEXT("thumb_03")) - P(TEXT("thumb_01"))).GetSafeNormal();
		F.ThumbAxis = FVector::CrossProduct(ThumbDir, Palm).GetSafeNormal();
		// The thumb's sweep across the palm toward the little finger is a turn about the palm's normal.
		F.ThumbSweepSign = FVector::DotProduct(FVector::CrossProduct(Palm, ThumbDir), F.Lateral) >= 0.0f ? 1.0f : -1.0f;
		F.SpreadSign = FVector::DotProduct(FVector::CrossProduct(Palm, HandDir), F.Lateral) >= 0.0f ? 1.0f : -1.0f;
		F.Knuckles = (P(TEXT("middle_01")) - Wrist).GetSafeNormal();
		F.Thumb[0] = P(TEXT("thumb_01"));
		F.Thumb[1] = P(TEXT("thumb_02"));
		F.Thumb[2] = P(TEXT("thumb_03"));
		F.Palm = Palm;
		const int32 HI = Ref.FindBoneIndex(*FString::Printf(TEXT("hand_%s"), S));
		F.RefRotation = HI == INDEX_NONE ? FQuat::Identity : FAnimationRuntime::GetComponentSpaceTransformRefPose(Ref, HI).GetRotation();
		F.bValid = !F.Lateral.IsNearlyZero() && !F.Forearm.IsNearlyZero();
	}
}

void UEHViewArms::AddHandRotations(TArray<FEHAdditiveRotation>& Out, int32 Hand) const
{
	const FHandFrame& F = HandFrames[Hand];
	if (!F.bValid)
	{
		return;
	}
	const TCHAR* S = Hand == 0 ? TEXT("l") : TEXT("r");
	auto Name = [&](const TCHAR* Bone) { return FName(*FString::Printf(TEXT("%s_%s"), Bone, S)); };
	// The hand itself is aimed after the reach (AimHand); here only the fingers, relative to it, in the rest pose.
	const FQuat Turn = FQuat::Identity;
	const FQuat BendQ = FQuat::Identity;
	// Fingers: each joint folds toward the palm about the (turned) knuckles' line; the pinky side folds a little
	// further, as real fists do. Spread fans the fingers apart for an open casting hand.
	const FVector Lat = (BendQ * Turn).RotateVector(F.Lateral);
	const float C = Curl[Hand];
	static const TCHAR* Fingers[4] = {TEXT("index"), TEXT("middle"), TEXT("ring"), TEXT("pinky")};
	static const float Joint[3] = {80.0f, 90.0f, 40.0f};   // a closed fist (tuned so the fingertips rest on the palm, not through it)
	// An open hand fans its fingers apart (index toward the thumb, the little finger furthest out) before any curl.
	static const float Fan[4] = {-13.0f, -2.0f, 8.0f, 18.0f};
	for (int32 I = 0; I < 4; ++I)
	{
		if (Spread[Hand] > 0.01f)
		{
			Out.Add({Name(*FString::Printf(TEXT("%s_01"), Fingers[I])), FQuat(F.Palm, FMath::DegreesToRadians(Fan[I] * Spread[Hand] * F.SpreadSign))});
		}
	}
	for (int32 I = 0; I < 4; ++I)
	{
		const float Extra = 1.0f + 0.06f * I;
		for (int32 K = 0; K < 3; ++K)
		{
			const FQuat Q(Lat, FMath::DegreesToRadians(Joint[K] * C * Extra * F.FlexSign));
			Out.Add({Name(*FString::Printf(TEXT("%s_0%d"), Fingers[I], K + 1)), Q});
		}
	}
	// The thumb swings across the palm toward the little finger and folds over the curled fingers as the fist closes:
	// its base sweeps about the palm's normal and tips in toward the palm; its two joints fold about its own axis.
	// Each thumb bone turns toward a direction set in the hand's own frame (K forward along the knuckles, N out of the
	// palm, X across toward the little finger): the base forward and in front of the palm, the two joints wrapping
	// across the front of the curled fingers. Applied in order, each from where its parent's turn has left it.
	const FVector K = F.Knuckles, N = F.Palm, X = F.Lateral;
	const FVector Want[3] = {(K * 0.80f + N * 0.50f + X * 0.15f).GetSafeNormal(), (K * 0.30f + N * 0.35f + X * 0.90f).GetSafeNormal(),
	                         (K * -0.15f + N * 0.20f + X * 1.0f).GetSafeNormal()};
	const FVector RestDir[3] = {(F.Thumb[1] - F.Thumb[0]).GetSafeNormal(), (F.Thumb[2] - F.Thumb[1]).GetSafeNormal(), (F.Thumb[2] - F.Thumb[1]).GetSafeNormal()};
	FQuat Above = FQuat::Identity;
	if (Spread[Hand] > 0.01f)
	{
		// An open hand also swings the thumb out, away from the fingers.
		Above = FQuat(F.Palm, FMath::DegreesToRadians(-24.0f * Spread[Hand] * F.ThumbSweepSign));
		Out.Add({Name(TEXT("thumb_01")), Above});
	}
	static const TCHAR* ThumbBones[3] = {TEXT("thumb_01"), TEXT("thumb_02"), TEXT("thumb_03")};
	for (int32 K3 = 0; K3 < 3; ++K3)
	{
		const FVector Now = Above.RotateVector(RestDir[K3]);
		const FQuat Q = FQuat::Slerp(FQuat::Identity, FQuat::FindBetweenNormals(Now, Want[K3]), FMath::Clamp(C, 0.0f, 1.0f));
		Out.Add({Name(ThumbBones[K3]), Q});
		Above = Q * Above;
	}
}

void UEHViewArms::UpdateHandTargets(const FEHFists& Fists, float DeltaSeconds)
{
	// What each hand is doing: a relaxed hand when lowered, a fist in the guard and at the ready that clenches tight
	// for a blow and turns over as it lands (the corkscrew), an open throwing hand for a Fireball, open palms driving
	// forward for an Ice Wall.
	const EEHFistAction Action = Fists.Action();
	const FEHFistTuning& T = Fists.GetTuning();
	float TC[2], TP[2], TB[2], TS[2];
	const float Up = Smooth(Visible);
	for (int32 H = 0; H < 2; ++H)
	{
		TC[H] = FMath::Lerp(0.30f, 0.86f + 0.14f * Smooth(Fists.GuardLevel()), Up);
		TP[H] = FMath::Lerp(15.0f, 68.0f, Up);
		TB[H] = 0.0f;
		TS[H] = 0.0f;
	}
	// The high guard: in while the block is held (and not during a technique).
	GuardW = FMath::FInterpTo(GuardW, Action == EEHFistAction::None ? Smooth(Fists.GuardLevel()) : 0.0f, DeltaSeconds, 18.0f);
	float Fast = 0.06f;
	if (Action != EEHFistAction::None)
	{
		const FEHStrikeDef& D = T.Def(Action);
		const float F = static_cast<float>(Fists.Frame());
		const float Out = Smooth((F - D.Startup * 0.35f) / FMath::Max(1.0f, D.Startup * 0.65f));
		const bool bLive = F < D.Startup + D.Active;
		switch (Action)
		{
		case EEHFistAction::Jab:
			TC[0] = 1.0f;
			TP[0] = 68.0f + 22.0f * (bLive ? Out : 0.4f);
			break;
		case EEHFistAction::Straight:
			TC[1] = 1.0f;
			TP[1] = 68.0f + 26.0f * (bLive ? Out : 0.4f);
			break;
		case EEHFistAction::Fireball:
		{
			// The fire gathers in a half-closed hand drawn back, then the hand throws open: fingers straight and
			// spread, the wrist bent back so the full palm faces the target as the fire leaves it.
			const float Open = bLive ? Out : FMath::Clamp(1.0f - (F - D.Startup - D.Active) / FMath::Max(1.0f, D.Recovery * 0.8f), 0.0f, 1.0f);
			TC[0] = FMath::Lerp(0.55f, 0.0f, Open);
			TS[0] = Open;
			TP[0] = FMath::Lerp(40.0f, 82.0f, Open);
			TB[0] = 72.0f * Open;
			break;
		}
		default:
			for (int32 H = 0; H < 2; ++H)
			{
				const float Open = bLive ? Out : FMath::Clamp(1.0f - (F - D.Startup - D.Active) / FMath::Max(1.0f, D.Recovery * 0.8f), 0.0f, 1.0f);
				TC[H] = FMath::Lerp(0.5f, 0.0f, Open);
				TS[H] = Open;
				TP[H] = FMath::Lerp(40.0f, 85.0f, Open);
				TB[H] = 78.0f * Open;
			}
			break;
		}
		Fast = 0.03f;
	}
	const float K = 1.0f - FMath::Exp(-DeltaSeconds / Fast);
	for (int32 H = 0; H < 2; ++H)
	{
		Curl[H] = FMath::Lerp(Curl[H], TC[H], K);
		Pronate[H] = FMath::Lerp(Pronate[H], TP[H], K);
		Bend[H] = FMath::Lerp(Bend[H], TB[H], K);
		Spread[H] = FMath::Lerp(Spread[H], TS[H], K);
	}
}

FQuat UEHViewArms::AimHand(int32 Hand, const FVector& Forward, const FVector& PalmDir, const FQuat& CamToCS) const
{
	const FHandFrame& F = HandFrames[Hand];
	auto Basis = [](const FVector& X0, const FVector& Y0) {
		const FVector X = X0.GetSafeNormal();
		const FVector Y = (Y0 - X * FVector::DotProduct(Y0, X)).GetSafeNormal();
		return FQuat(FMatrix(X, Y, FVector::CrossProduct(X, Y), FVector::ZeroVector));
	};
	const FQuat Rest = Basis(F.Knuckles, F.Palm);
	const FQuat Want = Basis(CamToCS.RotateVector(Forward), CamToCS.RotateVector(PalmDir));
	return (Want * Rest.Inverse()) * F.RefRotation;
}

void UEHViewArms::GuardImpact(float Strength)
{
	GuardShock = FMath::Max(GuardShock, FMath::Clamp(Strength, 0.0f, 1.5f));
}

void UEHViewArms::StrikeRebound(int32 Hand, float Strength)
{
	ReboundHand = Hand;
	Rebound = FMath::Max(Rebound, FMath::Clamp(Strength, 0.0f, 1.5f));
}
