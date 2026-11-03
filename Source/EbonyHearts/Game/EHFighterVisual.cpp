#include "EHFighterVisual.h"

#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EHAnimInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "ProceduralMeshComponent.h"

namespace EHVisualDetail
{
constexpr float UnitsToCm = 1.0f / static_cast<float>(eh::kUnitsPerCm);
constexpr float TurnTowardCamera = 12.0f;   // degrees: fighters open slightly toward the camera for readability

UStaticMesh* LoadShape(const TCHAR* Path)
{
	return LoadObject<UStaticMesh>(nullptr, Path);
}
}
using namespace EHVisualDetail;

FEHAnimChoice EHChooseAnim(const eh::Match& Match, int32 Player)
{
	const eh::MatchState& S = Match.State();
	const eh::FighterState& F = S.f[Player];
	FEHAnimChoice A;
	if (S.phase == eh::Phase::Intro)
	{
		A.Key = TEXT("Intro");
		A.Frame = S.phaseFrame;
		A.BlendSeconds = 0.0f;
		return A;
	}
	switch (F.state)
	{
	case eh::FState::Neutral:
		A.Key = F.walk > 0 ? FName(TEXT("WalkF")) : (F.walk < 0 ? FName(TEXT("WalkB")) : FName(TEXT("Idle")));
		A.bLoop = true;
		A.BlendSeconds = 0.12f;
		break;
	case eh::FState::Guard:
		A.Key = TEXT("Guard");
		A.bLoop = true;
		A.BlendSeconds = 0.05f;
		break;
	case eh::FState::Attack:
	{
		const eh::MoveDef& M = Match.Character(Player).moves[static_cast<size_t>(F.move)];
		A.Key = FName(UTF8_TO_TCHAR(M.anim.c_str()));
		A.Frame = F.moveFrame;
		A.BlendSeconds = M.kind == eh::MoveKind::Dodge ? 0.04f : 0.035f;
		break;
	}
	case eh::FState::Hitstun:
		A.Key = F.reaction >= 2 ? FName(TEXT("HitHeavy")) : FName(TEXT("HitLight"));
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.025f;
		break;
	case eh::FState::Blockstun:
		A.Key = TEXT("BlockHit");
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.03f;
		break;
	case eh::FState::Knockdown:
		A.Key = F.reaction == 3 ? FName(TEXT("KnockdownLie")) : FName(TEXT("Knockdown"));
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.03f;
		break;
	case eh::FState::Getup:
		A.Key = TEXT("Getup");
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.06f;
		break;
	case eh::FState::Throwing:
	case eh::FState::Thrown:
	{
		const eh::CharacterDef& Owner = Match.Character(F.throwOwner >= 0 ? F.throwOwner : Player);
		const eh::ThrowDef& T = Owner.throws[static_cast<size_t>(F.throwIndex >= 0 ? F.throwIndex : 0)];
		A.Key = FName(UTF8_TO_TCHAR((F.state == eh::FState::Throwing ? T.attackerAnim : T.victimAnim).c_str()));
		A.Frame = FMath::Max(1, F.throwFrame);
		A.BlendSeconds = 0.04f;
		break;
	}
	case eh::FState::Tech:
		A.Key = TEXT("ThrowTech");
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.04f;
		break;
	case eh::FState::KO:
		A.Key = TEXT("KO");
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.04f;
		break;
	case eh::FState::Win:
		A.Key = TEXT("Win");
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.15f;
		break;
	case eh::FState::Defeated:
		A.Key = TEXT("Defeated");
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.15f;
		break;
	}
	return A;
}

AEHFighterVisual::AEHFighterVisual()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	Mesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Root);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	GrayBody = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GrayBody"));
	GrayBody->SetupAttachment(Root);
	GrayHead = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GrayHead"));
	GrayHead->SetupAttachment(Root);
	GrayLimb = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("GrayLimb"));
	GrayLimb->SetupAttachment(Root);
	Marker = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Marker"));
	Marker->SetupAttachment(Root);
	Aura = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("Aura"));
	Aura->SetupAttachment(Root);
	for (UPrimitiveComponent* C : {static_cast<UPrimitiveComponent*>(GrayBody), static_cast<UPrimitiveComponent*>(GrayHead), static_cast<UPrimitiveComponent*>(GrayLimb), static_cast<UPrimitiveComponent*>(Marker), static_cast<UPrimitiveComponent*>(Aura)})
	{
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
	}
	Aura->SetUsingAbsoluteLocation(true);
	Aura->SetUsingAbsoluteRotation(true);
}

void AEHFighterVisual::Setup(const FEHCharacterPresentation& InPresentation, int32 InPlayer, bool bMirrorMatch)
{
	Presentation = InPresentation;
	Player = InPlayer;
	USkeletalMesh* SkMesh = Presentation.MeshPath.IsEmpty() ? nullptr : LoadObject<USkeletalMesh>(nullptr, *Presentation.MeshPath);
	bGraybox = SkMesh == nullptr;
	Mesh->SetVisibility(!bGraybox);
	GrayBody->SetVisibility(bGraybox);
	GrayHead->SetVisibility(bGraybox);
	GrayLimb->SetVisibility(false);
	if (!bGraybox)
	{
		// Visuals are reused across matches; drop the previous fighter's per-slot instances before swapping meshes.
		Mesh->EmptyOverrideMaterials();
		Mesh->SetSkeletalMesh(SkMesh);
		Mesh->SetAnimInstanceClass(UEHAnimInstance::StaticClass());
		Mesh->SetRelativeScale3D(FVector(Presentation.MeshScale));
		Mesh->SetCastShadow(true);
		BodyMaterials.Reset();
		for (int32 Slot = 0; Slot < Mesh->GetNumMaterials(); ++Slot)
		{
			// Slots with no rim (the eyes) keep their shared material.
			float BaseRim = 0.0f;
			UMaterialInterface* SlotMaterial = Mesh->GetMaterial(Slot);
			if (SlotMaterial && SlotMaterial->GetScalarParameterValue(FHashedMaterialParameterInfo(TEXT("RimIntensity")), BaseRim) && BaseRim > 0.0f)
			{
				if (UMaterialInstanceDynamic* MID = Mesh->CreateDynamicMaterialInstance(Slot))
				{
					BodyMaterials.Add(MID);
				}
			}
		}
		AppliedRim = -1.0f;
	}
	else
	{
		UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
		GrayMaterial = UMaterialInstanceDynamic::Create(Base, this);
		GrayMaterial->SetVectorParameterValue(TEXT("Color"), Presentation.Graybox);
		GrayBody->SetStaticMesh(LoadShape(TEXT("/Engine/BasicShapes/Cylinder.Cylinder")));
		GrayHead->SetStaticMesh(LoadShape(TEXT("/Engine/BasicShapes/Sphere.Sphere")));
		GrayLimb->SetStaticMesh(LoadShape(TEXT("/Engine/BasicShapes/Cube.Cube")));
		for (UStaticMeshComponent* C : {GrayBody.Get(), GrayHead.Get(), GrayLimb.Get()})
		{
			C->SetMaterial(0, GrayMaterial);
			C->SetCastShadow(true);
		}
	}
	AppliedFacingSign = 0.0f;
	// Side marker: a thin disc under the fighter, warm for player one and cool for player two, so mirror
	// matches stay readable without altering either character's canonical colours.
	Marker->SetStaticMesh(LoadShape(TEXT("/Engine/BasicShapes/Plane.Plane")));
	Marker->SetRelativeScale3D(FVector(1.05f, 1.05f, 1.0f));
	Marker->SetRelativeLocation(FVector(0, 0, 4.0f));
	if (UMaterialInterface* MarkerBase = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/VFX/M_EH_Marker.M_EH_Marker")))
	{
		MarkerMaterial = UMaterialInstanceDynamic::Create(MarkerBase, this);
	}
	else
	{
		MarkerMaterial = UMaterialInstanceDynamic::Create(LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")), this);
	}
	const FLinearColor Side = Player == 0 ? FLinearColor(0.85f, 0.62f, 0.25f) : FLinearColor(0.55f, 0.66f, 0.80f);
	MarkerMaterial->SetVectorParameterValue(TEXT("Color"), Side);
	Marker->SetMaterial(0, MarkerMaterial);
	Marker->SetVisibility(true);
	if (UMaterialInterface* AuraBase = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/VFX/M_VFX_Additive.M_VFX_Additive")))
	{
		AuraMaterial = UMaterialInstanceDynamic::Create(AuraBase, this);
		AuraMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.0f, 0.74f, 0.22f));
		AuraMaterial->SetScalarParameterValue(TEXT("Intensity"), 6.0f);
		Aura->SetMaterial(0, AuraMaterial);
	}
	Anims.Reset();
	Missing.Reset();
	CurrentKey = NAME_None;
	CurrentInstance = -1;
	PreviousKey = NAME_None;
	BlendLeft = 0.0f;
	AuraIntensity = 0.0f;
}

UAnimSequence* AEHFighterVisual::FindAnim(FName Key)
{
	if (Key.IsNone() || bGraybox)
	{
		return nullptr;
	}
	if (TObjectPtr<UAnimSequence>* Found = Anims.Find(Key))
	{
		return Found->Get();
	}
	const FString Name = Presentation.AnimPrefix + Key.ToString();
	const FString Path = Presentation.AnimFolder / Name + TEXT(".") + Name;
	UAnimSequence* Seq = LoadObject<UAnimSequence>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (Seq == nullptr)
	{
		Missing.Add(Key);
	}
	Anims.Add(Key, Seq);
	return Seq;
}

TArray<FString> AEHFighterVisual::MissingAnimations() const
{
	TArray<FString> Out;
	for (const FName& N : Missing)
	{
		Out.Add(N.ToString());
	}
	return Out;
}

FVector AEHFighterVisual::BoneLocation(FName Bone, const FVector& Fallback) const
{
	if (!bGraybox && Mesh->GetSkeletalMeshAsset() && Mesh->GetBoneIndex(Bone) != INDEX_NONE)
	{
		return Mesh->GetBoneLocation(Bone);
	}
	return Fallback;
}

FVector AEHFighterVisual::HeadLocation() const
{
	return BoneLocation(Presentation.HeadBone, GetActorLocation() + FVector(0, 0, 165));
}

void AEHFighterVisual::UpdateVisual(const eh::Match& Match, int32 PrevX, float Alpha, float DeltaSeconds, double Time)
{
	const eh::FighterState& F = Match.State().f[Player];
	const float X = FMath::Lerp(static_cast<float>(PrevX), static_cast<float>(F.x), Alpha) * UnitsToCm;
	FVector Loc(X, 0.0f, 0.0f);
	// Small shake on the defender while hitstop holds both fighters still.
	if (F.hitstop > 0 && (F.state == eh::FState::Hitstun || F.state == eh::FState::Blockstun || F.state == eh::FState::Knockdown))
	{
		Loc.X += FMath::Sin(static_cast<float>(Time) * 95.0f) * 1.6f * FMath::Min(1.0f, F.hitstop / 6.0f);
	}
	SetActorLocation(Loc);

	// Facing left mirrors the fighter instead of turning it, so the stance, lead side and the chest opened toward
	// the camera read the same on both sides of the screen (the simulation is symmetric about the facing).
	const float FacingSign = F.facing > 0 ? 1.0f : -1.0f;
	SetActorScale3D(FVector(FacingSign, 1.0f, 1.0f));
	SetActorRotation(FRotator(0.0f, F.facing > 0 ? TurnTowardCamera : -TurnTowardCamera, 0.0f));
	Mesh->SetRelativeRotation(FRotator(0.0f, Presentation.MeshYaw, 0.0f));
	if (FacingSign != AppliedFacingSign)
	{
		// The mirror reverses triangle winding. Rebuild the render proxies with the final transform whenever the sign
		// changes (and once after Setup): a proxy created before the flip, or deferred while its pipeline states
		// compiled, could otherwise keep the old culling and draw the inside of the mesh.
		Mesh->MarkRenderStateDirty();
		Marker->MarkRenderStateDirty();
		AppliedFacingSign = FacingSign;
	}

	if (bGraybox)
	{
		UpdateGraybox(Match, DeltaSeconds);
		UpdateAura(Time);
		return;
	}

	const FEHAnimChoice Choice = EHChooseAnim(Match, Player);
	const bool bFrozen = F.hitstop > 0;
	double NewTime = 0.0;
	if (Choice.bLoop)
	{
		LoopTime += DeltaSeconds;
		NewTime = LoopTime;
	}
	else
	{
		NewTime = (static_cast<double>(Choice.Frame) - 1.0 + (bFrozen ? 0.0 : Alpha)) / static_cast<double>(eh::kTickHz);
	}
	const bool bRestart = Choice.Key != CurrentKey || (!Choice.bLoop && NewTime + 1e-6 < CurrentTime - 0.5 / eh::kTickHz);
	if (bRestart)
	{
		if (!CurrentKey.IsNone() && Choice.BlendSeconds > 0.0f)
		{
			PreviousKey = CurrentKey;
			PreviousTime = CurrentTime;
			BlendTotal = Choice.BlendSeconds;
			BlendLeft = Choice.BlendSeconds;
		}
		else
		{
			BlendLeft = 0.0f;
		}
		if (Choice.bLoop && Choice.Key != CurrentKey)
		{
			LoopTime = 0.0;
			NewTime = 0.0;
		}
		CurrentKey = Choice.Key;
	}
	CurrentTime = NewTime;
	BlendLeft = FMath::Max(0.0f, BlendLeft - DeltaSeconds);

	UAnimSequence* Cur = FindAnim(CurrentKey);
	UAnimSequence* Prev = BlendLeft > 0.0f ? FindAnim(PreviousKey) : nullptr;
	double CurSample = CurrentTime;
	if (Cur)
	{
		const double Length = Cur->GetPlayLength();
		CurSample = Choice.bLoop ? FMath::Fmod(CurrentTime, FMath::Max(Length, 1e-3)) : FMath::Clamp(CurrentTime, 0.0, Length);
	}
	if (UEHAnimInstance* Inst = Cast<UEHAnimInstance>(Mesh->GetAnimInstance()))
	{
		Inst->SetSamples(Cur, CurSample, Prev, PreviousTime, BlendTotal > 0.0f ? BlendLeft / BlendTotal : 0.0f);
	}
	UpdateAura(Time);
}

void AEHFighterVisual::UpdateGraybox(const eh::Match& Match, float DeltaSeconds)
{
	const eh::FighterState& F = Match.State().f[Player];
	const eh::CharacterDef& C = Match.Character(Player);
	const float Height = (C.hurt.y1 * UnitsToCm);
	const bool bDown = F.state == eh::FState::Knockdown || F.state == eh::FState::KO || F.state == eh::FState::Thrown;
	// Engine cylinder is 100 cm tall and centred; scale and lift it so feet rest on the floor.
	const float BodyH = Height * 0.82f;
	if (bDown)
	{
		GrayBody->SetRelativeRotation(FRotator(90.0f, 0.0f, 0.0f));
		GrayBody->SetRelativeLocation(FVector(-BodyH * 0.4f, 0.0f, 20.0f));
		GrayHead->SetRelativeLocation(FVector(-BodyH * 0.9f, 0.0f, 20.0f));
	}
	else
	{
		GrayBody->SetRelativeRotation(FRotator::ZeroRotator);
		GrayBody->SetRelativeLocation(FVector(0.0f, 0.0f, BodyH * 0.5f));
		GrayHead->SetRelativeLocation(FVector(0.0f, 0.0f, BodyH + Height * 0.09f));
	}
	GrayBody->SetRelativeScale3D(FVector(0.42f, 0.32f, BodyH / 100.0f));
	GrayHead->SetRelativeScale3D(FVector(0.24f));
	FLinearColor Tint = Presentation.Graybox;
	if (F.state == eh::FState::Hitstun) Tint = FLinearColor(0.9f, 0.85f, 0.8f);
	else if (F.state == eh::FState::Blockstun || F.state == eh::FState::Guard) Tint = Presentation.Graybox * 0.5f + FLinearColor(0.1f, 0.15f, 0.35f);
	GrayMaterial->SetVectorParameterValue(TEXT("Color"), Tint);
	// The limb shows active hitboxes so timing reads during graybox play.
	GrayLimb->SetVisibility(false);
	if (F.state == eh::FState::Attack)
	{
		const eh::MoveDef& M = C.moves[static_cast<size_t>(F.move)];
		for (const eh::HitDef& H : M.hits)
		{
			if (H.frames.Contains(F.moveFrame))
			{
				const float Cx = (H.box.x0 + H.box.x1) * 0.5f * UnitsToCm;
				const float Cz = (H.box.y0 + H.box.y1) * 0.5f * UnitsToCm;
				const float Sx = (H.box.x1 - H.box.x0) * UnitsToCm / 100.0f;
				const float Sz = (H.box.y1 - H.box.y0) * UnitsToCm / 100.0f;
				// Undo the open-toward-camera turn so the limb lies on the fighting axis.
				GrayLimb->SetRelativeRotation(FRotator(0.0f, -TurnTowardCamera, 0.0f));
				GrayLimb->SetRelativeLocation(FVector(Cx, 0.0f, Cz));
				GrayLimb->SetRelativeScale3D(FVector(Sx, 0.12f, Sz));
				GrayLimb->SetVisibility(true);
				break;
			}
		}
	}
}

void AEHFighterVisual::UpdateAura(double Time)
{
	// Golden rim on the body: a steady glow with a faint crackle, so the aura reads even between bolt strikes.
	const float Rim = AuraIntensity <= 0.01f ? 0.0f : AuraIntensity * (0.85f + 0.15f * FMath::Sin(static_cast<float>(Time) * 31.0f));
	if (!FMath::IsNearlyEqual(Rim, AppliedRim, 0.01f))
	{
		const FLinearColor RimColor = FMath::Lerp(FLinearColor(0.35f, 0.42f, 0.60f), FLinearColor(1.0f, 0.70f, 0.18f), FMath::Min(1.0f, Rim * 1.2f));
		for (UMaterialInstanceDynamic* MID : BodyMaterials)
		{
			MID->SetVectorParameterValue(TEXT("RimColor"), RimColor);
			MID->SetScalarParameterValue(TEXT("RimIntensity"), 0.35f + 0.55f * Rim);
		}
		AppliedRim = Rim;
	}
	if (AuraIntensity <= 0.01f || AuraMaterial == nullptr)
	{
		if (Aura->GetNumSections() > 0)
		{
			Aura->ClearAllMeshSections();
		}
		return;
	}
	// Re-strike the bolts a few times per second; between strikes they hold, which reads as crackling.
	if (Time - AuraSeedTime < 0.055 && Aura->GetNumSections() > 0)
	{
		AuraMaterial->SetScalarParameterValue(TEXT("Intensity"), 5.0f * AuraIntensity);
		return;
	}
	AuraSeedTime = Time;
	TArray<FVector> Anchors;
	for (const FName& Bone : Presentation.AuraBones)
	{
		Anchors.Add(BoneLocation(Bone, GetActorLocation() + FVector(0, 0, 100)));
	}
	if (Anchors.Num() < 2)
	{
		const FVector Base = GetActorLocation();
		for (float Z : {30.0f, 70.0f, 110.0f, 140.0f, 165.0f})
		{
			Anchors.Add(Base + FVector(0, 0, Z));
		}
	}
	FRandomStream Rng(static_cast<int32>(Time * 1000.0) ^ (Player * 7919));
	TArray<FVector> Verts;
	TArray<int32> Tris;
	TArray<FVector> Normals;
	TArray<FVector2D> UVs;
	TArray<FLinearColor> Colors;
	TArray<FProcMeshTangent> Tangents;
	const int32 Bolts = 5;
	for (int32 B = 0; B < Bolts; ++B)
	{
		const FVector A = Anchors[Rng.RandRange(0, Anchors.Num() - 1)] + Rng.VRand() * 12.0f;
		const FVector Z = Anchors[Rng.RandRange(0, Anchors.Num() - 1)] + Rng.VRand() * 28.0f;
		const int32 Segments = 6;
		FVector Prev = A;
		for (int32 S = 1; S <= Segments; ++S)
		{
			FVector P = FMath::Lerp(A, Z, static_cast<float>(S) / Segments);
			if (S < Segments)
			{
				P += Rng.VRand() * 7.0f;
			}
			// Ribbon facing the camera (+Y): offset along Z-ish perpendicular in the XZ plane.
			const FVector Dir = (P - Prev).GetSafeNormal();
			const FVector Side = FVector::CrossProduct(Dir, FVector(0, 1, 0)).GetSafeNormal() * (0.9f + Rng.FRand() * 0.8f);
			const int32 V0 = Verts.Num();
			Verts.Append({Prev - Side, Prev + Side, P - Side, P + Side});
			for (int32 k = 0; k < 4; ++k)
			{
				Normals.Add(FVector(0, 1, 0));
				Colors.Add(FLinearColor::White);
				Tangents.Add(FProcMeshTangent(1, 0, 0));
			}
			UVs.Append({FVector2D(0, 0), FVector2D(1, 0), FVector2D(0, 1), FVector2D(1, 1)});
			Tris.Append({V0, V0 + 2, V0 + 1, V0 + 1, V0 + 2, V0 + 3});
			Prev = P;
		}
	}
	// The bolt layout always has the same vertex count, so later strikes move the existing vertices. Creating a new
	// section (or setting the material again) rebuilds the render proxy, which hitched while the aura was up.
	const FProcMeshSection* Existing = Aura->GetNumSections() > 0 ? Aura->GetProcMeshSection(0) : nullptr;
	if (Existing && Existing->ProcVertexBuffer.Num() == Verts.Num())
	{
		Aura->UpdateMeshSection_LinearColor(0, Verts, Normals, UVs, Colors, Tangents);
	}
	else
	{
		Aura->CreateMeshSection_LinearColor(0, Verts, Tris, Normals, UVs, Colors, Tangents, false);
		Aura->SetMaterial(0, AuraMaterial);
	}
	AuraMaterial->SetScalarParameterValue(TEXT("Intensity"), 5.0f * AuraIntensity);
}
