#include "EHFighterVisual.h"

#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EHAnimInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "ProceduralMeshComponent.h"

namespace EHVisualDetail
{
constexpr float UnitsToCm = 1.0f / static_cast<float>(eh::kUnitsPerCm);
constexpr float TurnTowardCamera = 12.0f;   // degrees: fighters open slightly toward the camera for readability
constexpr float CloseStagger = 10.0f;       // cm each fighter steps off the line in depth when chest to chest

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
	// Crouching follows the simulation's posture, which lowers or raises one step a frame: the body blends into the crouch
	// (or back up) over about the same frames as the hurtbox, so what can be hit is what is drawn.
	const bool bCrouched = Match.IsCrouching(Player);
	const float PostureBlend = static_cast<float>(FMath::Max(1, Match.GetRules().crouchFrames) + 1) / static_cast<float>(eh::kTickHz);
	switch (F.state)
	{
	case eh::FState::Neutral:
		if (F.posture > 0 && F.lastInput.y < 0)
		{
			A.Key = TEXT("Crouch");
			A.BlendSeconds = PostureBlend;
		}
		else
		{
			A.Key = F.walk > 0 ? FName(TEXT("WalkF")) : (F.walk < 0 ? FName(TEXT("WalkB")) : FName(TEXT("Idle")));
			A.BlendSeconds = F.posture > 0 ? PostureBlend : 0.22f;   // rising out of a crouch is as quick as going down
		}
		A.bLoop = true;
		break;
	case eh::FState::Guard:
		A.Key = (F.posture > 0 && F.lastInput.y < 0) ? FName(TEXT("CrouchGuard")) : FName(TEXT("Guard"));
		A.bLoop = true;
		A.BlendSeconds = F.posture > 0 ? PostureBlend : 0.10f;
		break;
	case eh::FState::Attack:
	{
		const eh::MoveDef& M = Match.Character(Player).moves[static_cast<size_t>(F.move)];
		A.Key = FName(UTF8_TO_TCHAR(M.anim.c_str()));
		A.Frame = F.moveFrame;
		// Blend over most of the startup, so the move is entirely on its own keys by its first active frame.
		int32 FirstActive = M.total;
		for (const eh::HitDef& Hit : M.hits)
		{
			FirstActive = FMath::Min(FirstActive, Hit.frames.first);
		}
		const float Startup = static_cast<float>(FMath::Max(1, FirstActive - 1)) / static_cast<float>(eh::kTickHz);
		A.BlendSeconds = M.kind == eh::MoveKind::Dodge ? 0.08f : FMath::Clamp(0.75f * Startup, 0.05f, 0.15f);
		// The feet take until about the first active frame: from a walk the step in progress lands instead of the
		// foot sliding into the stance in five frames.
		if (M.kind == eh::MoveKind::Strike)
		{
			A.LegBlendSeconds = FMath::Clamp(1.25f * Startup, A.BlendSeconds, 0.16f);
		}
		break;
	}
	case eh::FState::Hitstun:
	{
		if (bCrouched)
		{
			// A crouching fighter is hit where it crouches (only mids and lows reach it) and reels crouched.
			A.Key = TEXT("CrouchHit");
			A.Frame = F.stateFrame;
			A.BlendSeconds = 0.06f;
			break;
		}
		A.Key = F.reaction >= 2 ? FName(TEXT("HitHeavy")) : FName(TEXT("HitLight"));
		// A hit can name its own reaction: a hook turns the head away from it, a body shot folds the body. The clip
		// opens on its impact pose, held through the hitstop, so contact reads on the frame the strike lands.
		const eh::CharacterDef& Attacker = Match.Character(1 - Player);
		if (F.reactMove >= 0 && static_cast<size_t>(F.reactMove) < Attacker.moves.size())
		{
			const eh::MoveDef& M = Attacker.moves[static_cast<size_t>(F.reactMove)];
			if (F.reactHit >= 0 && static_cast<size_t>(F.reactHit) < M.hits.size() && !M.hits[static_cast<size_t>(F.reactHit)].react.empty())
			{
				A.Key = FName(UTF8_TO_TCHAR(M.hits[static_cast<size_t>(F.reactHit)].react.c_str()));
			}
		}
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.06f;
		break;
	}
	case eh::FState::Blockstun:
		A.Key = bCrouched ? FName(TEXT("CrouchBlockHit")) : FName(TEXT("BlockHit"));
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.06f;
		break;
	case eh::FState::Knockdown:
		// Landed from a throw: already lying, head away from the thrower (3) or toward it (4, over the shoulder). Launched
		// by an uppercut (5): lifted off the feet, then down on the back.
		A.Key = F.reaction == 4 ? FName(TEXT("KnockdownLieRev")) : (F.reaction == 3 ? FName(TEXT("KnockdownLie")) : (F.reaction == 5 ? FName(TEXT("KnockdownLaunch")) : FName(TEXT("Knockdown"))));
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.08f;
		break;
	case eh::FState::Getup:
		// From lying head toward the opponent the fighter rises facing away and pivots round to face it.
		A.Key = F.reaction == 4 ? FName(TEXT("GetupRev")) : FName(TEXT("Getup"));
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.15f;
		break;
	case eh::FState::Throwing:
	case eh::FState::Thrown:
	{
		const eh::CharacterDef& Owner = Match.Character(F.throwOwner >= 0 ? F.throwOwner : Player);
		const eh::ThrowDef& T = Owner.throws[static_cast<size_t>(F.throwIndex >= 0 ? F.throwIndex : 0)];
		A.Key = FName(UTF8_TO_TCHAR((F.state == eh::FState::Throwing ? T.attackerAnim : T.victimAnim).c_str()));
		A.Frame = FMath::Max(1, F.throwFrame);
		A.BlendSeconds = 0.10f;
		break;
	}
	case eh::FState::Tech:
		A.Key = TEXT("ThrowTech");
		A.Frame = F.stateFrame;
		// The escape can come on any of the throw's first frames, while the throw is already moving: blend long
		// enough to absorb what the escape's first pose does not match.
		A.BlendSeconds = 0.15f;
		break;
	case eh::FState::KO:
		// Knocked out by a throw: already lying where the throw left the victim, so stay down rather than replay the
		// knockout fall from standing.
		A.Key = F.reaction == 4 ? FName(TEXT("KnockdownLieRev")) : (F.reaction == 3 ? FName(TEXT("KnockdownLie")) : FName(TEXT("KO")));
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.10f;
		break;
	case eh::FState::Jump:
		// One clip runs the squat and the flight on the jump's own clock (a jump attack that ends in the air returns to
		// it mid-flight); forward and back jumps have their own.
		A.Key = F.jumpDir > 0 ? FName(TEXT("JumpF")) : (F.jumpDir < 0 ? FName(TEXT("JumpB")) : FName(TEXT("Jump")));
		A.Frame = FMath::Max(1, static_cast<int32>(F.jumpFrame));
		A.BlendSeconds = 0.06f;
		break;
	case eh::FState::Landing:
		A.Key = TEXT("Land");
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.04f;
		break;
	case eh::FState::Win:
		A.Key = TEXT("Win");
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.30f;
		break;
	case eh::FState::Defeated:
		A.Key = TEXT("Defeated");
		A.Frame = F.stateFrame;
		A.BlendSeconds = 0.30f;
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
		UTexture2D* BoltTex = LoadObject<UTexture2D>(nullptr, TEXT("/Game/VFX/T_FX_Bolt.T_FX_Bolt"));
		AuraMaterial = UMaterialInstanceDynamic::Create(AuraBase, this);
		AuraMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.0f, 0.70f, 0.20f));
		AuraMaterial->SetScalarParameterValue(TEXT("Intensity"), 0.0f);
		AuraCoreMaterial = UMaterialInstanceDynamic::Create(AuraBase, this);
		AuraCoreMaterial->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.0f, 0.93f, 0.74f));
		AuraCoreMaterial->SetScalarParameterValue(TEXT("Intensity"), 0.0f);
		if (BoltTex)
		{
			AuraMaterial->SetTextureParameterValue(TEXT("Tex"), BoltTex);
			AuraCoreMaterial->SetTextureParameterValue(TEXT("Tex"), BoltTex);
		}
	}
	// The energy shell is set once and left on, dark until the aura rises: changing a mesh's overlay rebuilds its
	// render proxy, which would hitch on the frame Spirit Enhanced Strikes lands.
	AuraShellMaterial = nullptr;
	AppliedShell = -1.0f;
	if (!bGraybox && Presentation.AuraBones.Num() > 0)
	{
		if (UMaterialInterface* ShellBase = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/VFX/M_VFX_AuraShell.M_VFX_AuraShell")))
		{
			AuraShellMaterial = UMaterialInstanceDynamic::Create(ShellBase, this);
			AuraShellMaterial->SetScalarParameterValue(TEXT("Intensity"), 0.0f);
		}
	}
	if (!bGraybox)
	{
		Mesh->SetOverlayMaterial(AuraShellMaterial);
	}
	Arcs.Reset();
	NextArcTime = 0.0;
	Anims.Reset();
	Missing.Reset();
	CurrentKey = NAME_None;
	ShownKey = NAME_None;
	bLastWasAttack = false;
	CurrentInstance = -1;
	AuraIntensity = 0.0f;
}

UAnimSequence* AEHFighterVisual::FindAnim(FName Key, bool bOptional)
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
	if (Seq == nullptr && !bOptional)
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
	// The pushboxes let the hips come within 46 cm, where the two bodies would pass through each other. Close in, ease
	// them apart in depth (the fighter facing right toward the camera), so they stand staggered as real fighters do.
	// Not during throws or their escapes, which are authored on the line.
	{
		const eh::FighterState& O = Match.State().f[1 - Player];
		auto Paired = [](const eh::FighterState& S)
		{
			return S.state == eh::FState::Throwing || S.state == eh::FState::Thrown || S.state == eh::FState::Tech;
		};
		const float Gap = FMath::Abs(static_cast<float>(O.x - F.x)) * UnitsToCm;
		const float Target = (Paired(F) || Paired(O)) ? 0.0f : (F.facing > 0 ? 1.0f : -1.0f) * CloseStagger * FMath::Clamp((75.0f - Gap) / 25.0f, 0.0f, 1.0f);
		DepthOffset = FMath::FInterpTo(DepthOffset, Target, DeltaSeconds, 10.0f);
		Loc.Y += DepthOffset;
	}
	// Small shake on the defender while hitstop holds both fighters still.
	if (F.hitstop > 0 && (F.state == eh::FState::Hitstun || F.state == eh::FState::Blockstun || F.state == eh::FState::Knockdown))
	{
		Loc.X += FMath::Sin(static_cast<float>(Time) * 95.0f) * 1.6f * FMath::Min(1.0f, F.hitstop / 6.0f);
	}
	// A jump (or a body hit out of the air) lifts the whole fighter; the side marker stays on the floor.
	const float Height = static_cast<float>(F.y) * UnitsToCm;
	Loc.Z += Height;
	Marker->SetRelativeLocation(FVector(0, 0, 4.0f - Height));
	SetActorLocation(Loc);

	// Facing left mirrors the fighter instead of turning it, so the stance, lead side and the chest opened toward
	// the camera read the same on both sides of the screen (the simulation is symmetric about the facing).
	const float FacingSign = F.facing > 0 ? 1.0f : -1.0f;
	SetActorScale3D(FVector(FacingSign, 1.0f, 1.0f));
	SetActorRotation(FRotator(0.0f, F.facing > 0 ? TurnTowardCamera : -TurnTowardCamera, 0.0f));
	Mesh->SetRelativeRotation(FRotator(0.0f, Presentation.MeshYaw, 0.0f));
	const bool bFacingFlipped = AppliedFacingSign != 0.0f && FacingSign != AppliedFacingSign;
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

	FEHAnimChoice Choice = EHChooseAnim(Match, Player);
	if (F.state == eh::FState::Hitstun && !bGraybox && FindAnim(Choice.Key) == nullptr)
	{
		// A hit's own reaction clip is missing from this fighter's set (reported by MissingAnimations): use the generic one.
		Choice.Key = F.reaction >= 2 ? FName(TEXT("HitHeavy")) : FName(TEXT("HitLight"));
	}
	else if (F.state == eh::FState::Knockdown && F.reaction == 5 && !bGraybox && FindAnim(Choice.Key) == nullptr)
	{
		Choice.Key = TEXT("Knockdown");   // reported as missing; the plain knockdown still lands the body
	}
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
	UEHAnimInstance* Inst = Cast<UEHAnimInstance>(Mesh->GetAnimInstance());
	if (bRestart)
	{
		if (Inst)
		{
			// A blend would start from the previous pose as it was held in the mesh's space, which the facing flip has
			// just mirrored: after a back throw that is the thrower's turned-round finish shown facing away. Animations
			// that switch sides end in the pose the next one starts from as seen after the flip, so cut straight to it.
			Inst->BeginTransition(CurrentKey.IsNone() || bFacingFlipped ? 0.0f : Choice.BlendSeconds, Choice.LegBlendSeconds);
		}
		if (Choice.bLoop && Choice.Key != CurrentKey)
		{
			LoopTime = 0.0;
			NewTime = 0.0;
		}
		const FName PreviousKey = CurrentKey;
		CurrentKey = Choice.Key;
		// A move cancelled out of another plays that string's own follow-up when one was captured
		// ("<Move>_from_<Previous>": the two hits from one performance), so the string flows as one motion.
		ShownKey = Choice.Key;
		if (bLastWasAttack && F.state == eh::FState::Attack && !PreviousKey.IsNone() && PreviousKey != Choice.Key)
		{
			const FName Variant(*FString::Printf(TEXT("%s_from_%s"), *Choice.Key.ToString(), *PreviousKey.ToString()));
			if (FindAnim(Variant, true))
			{
				ShownKey = Variant;
			}
		}
		// An escaped throw starts from where the throw was: "ThrowTech_from_<throw anim>_F<n>" begins on the throw's
		// frame 2, 5 or 8, for an escape on frames 1-3, 4-6 or 7-9 (the pair is already easing into the throw).
		else if (F.state == eh::FState::Tech && !PreviousKey.IsNone())
		{
			const int32 ThrowFrame = FMath::RoundToInt(static_cast<float>(CurrentTime) * eh::kTickHz) + 1;
			const int32 Start = 2 + 3 * FMath::Clamp((ThrowFrame - 1) / 3, 0, 2);
			const FName Variant(*FString::Printf(TEXT("ThrowTech_from_%s_F%d"), *PreviousKey.ToString(), Start));
			if (FindAnim(Variant, true))
			{
				ShownKey = Variant;
			}
		}
	}
	bLastWasAttack = F.state == eh::FState::Attack;
	CurrentTime = NewTime;

	UAnimSequence* Cur = FindAnim(ShownKey);
	double CurSample = CurrentTime;
	if (Cur)
	{
		const double Length = Cur->GetPlayLength();
		CurSample = Choice.bLoop ? FMath::Fmod(CurrentTime, FMath::Max(Length, 1e-3)) : FMath::Clamp(CurrentTime, 0.0, Length);
	}
	if (Inst)
	{
		Inst->SetSample(Cur, CurSample);
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

bool AEHFighterVisual::RandomAuraPoint(FVector& Out) const
{
	if (bGraybox || AuraIntensity <= 0.01f || Presentation.AuraBones.Num() == 0)
	{
		return false;
	}
	const FName Bone = Presentation.AuraBones[FMath::RandRange(0, Presentation.AuraBones.Num() - 1)];
	Out = BoneLocation(Bone, GetActorLocation() + FVector(0, 0, 100));
	return true;
}

void AEHFighterVisual::UpdateAura(double Time)
{
	// Spirit Enhanced Strikes: energy streaming off the body (the overlay shell), short lightning arcs crackling
	// between nearby limbs, and a warmer rim on the body's own materials. The body keeps its own colours.
	const float Level = AuraIntensity <= 0.01f ? 0.0f : AuraIntensity;
	const float Rim = Level * (0.85f + 0.15f * FMath::Sin(static_cast<float>(Time) * 31.0f));
	if (!FMath::IsNearlyEqual(Rim, AppliedRim, 0.01f))
	{
		// Only a touch warmer: a strong rim tints the whole body and drowns her own colours.
		const FLinearColor RimColor = FMath::Lerp(FLinearColor(0.35f, 0.42f, 0.60f), FLinearColor(0.80f, 0.62f, 0.38f), 0.5f * FMath::Min(1.0f, Rim));
		for (UMaterialInstanceDynamic* MID : BodyMaterials)
		{
			MID->SetVectorParameterValue(TEXT("RimColor"), RimColor);
			MID->SetScalarParameterValue(TEXT("RimIntensity"), 0.35f + 0.08f * Rim);
		}
		AppliedRim = Rim;
	}
	if (AuraShellMaterial)
	{
		const float Shell = Level * 1.7f * (0.85f + 0.15f * FMath::Sin(static_cast<float>(Time) * 17.0f));
		if (!FMath::IsNearlyEqual(Shell, AppliedShell, 0.01f))
		{
			AuraShellMaterial->SetScalarParameterValue(TEXT("Intensity"), Shell);
			AppliedShell = Shell;
		}
	}
	const int32 NumBones = Presentation.AuraBones.Num();
	if (Level <= 0.0f || AuraMaterial == nullptr || NumBones < 2 || bGraybox)
	{
		if (Aura->GetNumSections() > 0)
		{
			Aura->ClearAllMeshSections();
		}
		Arcs.Reset();
		return;
	}

	constexpr int32 MaxArcs = 4;
	constexpr int32 MainSegs = 8;
	constexpr int32 BranchSegs = 3;
	if (Arcs.Num() != MaxArcs)
	{
		Arcs.SetNum(MaxArcs);
	}
	TArray<FVector> Bones;
	Bones.Reserve(NumBones);
	for (const FName& Bone : Presentation.AuraBones)
	{
		Bones.Add(BoneLocation(Bone, GetActorLocation() + FVector(0, 0, 100)));
	}
	const FVector Centre = BoneLocation(TEXT("spine_02"), GetActorLocation() + FVector(0, 0, 110));

	// Strike a new arc at irregular intervals (more often at full strength), between two bones a hand or a forearm
	// apart, each end pushed out past the body's outline and toward the camera so it reads against the silhouette.
	if (Time >= NextArcTime)
	{
		int32 Slot = 0;
		for (int32 i = 1; i < MaxArcs; ++i)
		{
			if (Arcs[i].Born + Arcs[i].Life < Arcs[Slot].Born + Arcs[Slot].Life)
			{
				Slot = i;
			}
		}
		FAuraArc& A = Arcs[Slot];
		A.From = FMath::RandRange(0, NumBones - 1);
		A.To = (A.From + 1) % NumBones;
		float Best = 1e9f;
		for (int32 Try = 0; Try < 8; ++Try)
		{
			const int32 C = FMath::RandRange(0, NumBones - 1);
			const float D = FVector::Dist(Bones[A.From], Bones[C]);
			const float Score = FMath::Abs(D - 32.0f);
			if (C != A.From && D > 10.0f && Score < Best)
			{
				Best = Score;
				A.To = C;
			}
		}
		auto Outward = [&](const FVector& P)
		{
			FVector Out = P - Centre;
			Out.Y = 0.0f;
			return Out.GetSafeNormal() * FMath::FRandRange(4.0f, 10.0f) + FVector(FMath::FRandRange(-3.0f, 3.0f), 9.0f, FMath::FRandRange(-3.0f, 3.0f));
		};
		A.OffFrom = Outward(Bones[A.From]);
		A.OffTo = Outward(Bones[A.To]);
		A.Born = Time;
		A.Life = FMath::FRandRange(0.05f, 0.11f);
		A.Seed = FMath::Rand();
		NextArcTime = Time + FMath::FRandRange(0.02f, 0.09f) / FMath::Max(0.3f, Level);
	}

	TArray<FVector> Verts[2];
	TArray<int32> Tris;
	TArray<FVector> Normals;
	TArray<FVector2D> UVs;
	TArray<FLinearColor> Colors;
	TArray<FProcMeshTangent> Tangents;
	const float Widths[2] = {6.0f, 1.1f};   // glow, core
	const FVector Collapsed = GetActorLocation();
	auto Quad = [&](const FVector& P0, const FVector& P1, float Fade, int32 Layer)
	{
		const FVector Dir = (P1 - P0).GetSafeNormal();
		const FVector Side = FVector::CrossProduct(Dir, FVector(0, 1, 0)).GetSafeNormal() * Widths[Layer] * 0.5f;
		Verts[Layer].Append({P0 - Side, P0 + Side, P1 - Side, P1 + Side});
		if (Layer == 0)
		{
			const int32 V0 = (Verts[0].Num() - 4);
			Tris.Append({V0, V0 + 2, V0 + 1, V0 + 1, V0 + 2, V0 + 3});
			for (int32 k = 0; k < 4; ++k)
			{
				Normals.Add(FVector(0, 1, 0));
				Colors.Add(FLinearColor(Fade, Fade, Fade, Fade));
				Tangents.Add(FProcMeshTangent(1, 0, 0));
			}
			UVs.Append({FVector2D(0, 0), FVector2D(1, 0), FVector2D(0, 1), FVector2D(1, 1)});
		}
	};
	for (const FAuraArc& A : Arcs)
	{
		const float Age = static_cast<float>(Time - A.Born);
		const bool bAlive = A.Born >= 0.0 && Age < A.Life;
		// The jag re-strikes once mid-life, which reads as crackle; between re-strikes the shape holds still.
		FRandomStream Rng(A.Seed + (bAlive ? static_cast<int32>(Age / 0.035f) : 0));
		const FVector P0 = Bones[A.From] + A.OffFrom;
		const FVector P1 = Bones[A.To] + A.OffTo;
		const float Fade = bAlive ? 1.0f - FMath::Square(Age / A.Life) : 0.0f;
		const float Len = FVector::Dist(P0, P1);
		const FVector Along = (P1 - P0).GetSafeNormal();
		const FVector Perp = FVector::CrossProduct(Along, FVector(0, 1, 0)).GetSafeNormal();
		FVector Points[MainSegs + 1];
		for (int32 k = 0; k <= MainSegs; ++k)
		{
			const float T = static_cast<float>(k) / MainSegs;
			const float Pin = FMath::Sin(T * PI);   // ends stay on their anchors
			Points[k] = FMath::Lerp(P0, P1, T) + Perp * Rng.FRandRange(-0.22f, 0.22f) * Len * Pin + FVector(0, Rng.FRandRange(-2.0f, 2.0f), 0) * Pin;
		}
		const int32 Fork = 2 + Rng.RandRange(0, 3);
		const float Turn = (Rng.FRand() < 0.5f ? -1.0f : 1.0f) * Rng.FRandRange(25.0f, 50.0f);
		const FVector ForkDir = Along.RotateAngleAxis(Turn, FVector(0, 1, 0));
		FVector Branch[BranchSegs + 1];
		Branch[0] = Points[Fork];
		for (int32 k = 1; k <= BranchSegs; ++k)
		{
			Branch[k] = Branch[k - 1] + ForkDir * (Len * 0.38f / BranchSegs) + Perp * Rng.FRandRange(-0.08f, 0.08f) * Len;
		}
		for (int32 Layer = 0; Layer < 2; ++Layer)
		{
			for (int32 k = 0; k < MainSegs; ++k)
			{
				Quad(bAlive ? Points[k] : Collapsed, bAlive ? Points[k + 1] : Collapsed + FVector(0, 0, 0.01f), Fade, Layer);
			}
			for (int32 k = 0; k < BranchSegs; ++k)
			{
				Quad(bAlive ? Branch[k] : Collapsed, bAlive ? Branch[k + 1] : Collapsed + FVector(0, 0, 0.01f), Fade * 0.7f, Layer);
			}
		}
	}
	// The layout always has the same vertex count, so later frames move the existing vertices. Creating a section (or
	// setting its material again) rebuilds the render proxy, which hitched while the aura was up.
	for (int32 Layer = 0; Layer < 2; ++Layer)
	{
		const FProcMeshSection* Existing = Aura->GetNumSections() > Layer ? Aura->GetProcMeshSection(Layer) : nullptr;
		if (Existing && Existing->ProcVertexBuffer.Num() == Verts[Layer].Num())
		{
			Aura->UpdateMeshSection_LinearColor(Layer, Verts[Layer], Normals, UVs, Colors, Tangents);
		}
		else
		{
			Aura->CreateMeshSection_LinearColor(Layer, Verts[Layer], Tris, Normals, UVs, Colors, Tangents, false);
			Aura->SetMaterial(Layer, Layer == 0 ? AuraMaterial.Get() : AuraCoreMaterial.Get());
		}
	}
	AuraMaterial->SetScalarParameterValue(TEXT("Intensity"), 3.2f * Level);
	AuraCoreMaterial->SetScalarParameterValue(TEXT("Intensity"), 12.0f * Level);
}
