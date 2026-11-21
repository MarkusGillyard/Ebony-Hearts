// A standing training partner for the physical techniques: it takes hits, guards from the front, gets pushed, and can
// strike back on a slow, readable rhythm so the player's block has something to stop. Stepped at 60 frames per second
// like the techniques. Placeholder model: the 2.5D slice's Ashka test model and her animations, used only as a
// stand-in.
#pragma once

#include "CoreMinimal.h"
#include "EHFists.h"
#include "GameFramework/Character.h"

#include "EHTrainingDummy.generated.h"

class AEHPlayerCharacter;
class UAnimSequence;
class UEHAnimInstance;

enum class EEHDummyMode : uint8
{
	Stand,     // takes every hit
	Guard,     // guards hits from the front
	Strikes,   // strikes at the player when close, and can be hit out of it
	Count
};

const TCHAR* EHDummyModeName(EEHDummyMode Mode);

struct FEHDummyTuning
{
	float StrikeDamage = 10.0f;
	int32 WindupFrames = 24;      // from the start of the wind-up to contact
	int32 StrikeRecovery = 16;
	int32 StrikeCooldown = 70;    // frames between strikes
	float StrikeRange = 170.0f;   // starts a strike when the player is this close (cm, centre to centre)
	float StrikeReach = 165.0f;   // and connects if still this close on contact
	float StrikeArc = 50.0f;      // degrees either side of its facing
	int32 HitstunLight = 16;
	int32 HitstunHeavy = 22;
	int32 Blockstun = 12;
	float TurnRate = 300.0f;      // degrees per second toward the player
	FVector Spawn = FVector(0, -150, 0);
	float SpawnYaw = 90.0f;
	bool Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError);
};

struct FEHDummyHit
{
	EEHFistAction Action = EEHFistAction::None;
	float Damage = 0.0f;          // after the guard
	bool bBlocked = false;
	bool bBody = false;           // landed below the neck
	FVector Location = FVector::ZeroVector;
};

UCLASS(NotBlueprintable)
class AEHTrainingDummy : public ACharacter
{
	GENERATED_BODY()

public:
	AEHTrainingDummy(const FObjectInitializer& ObjectInitializer);
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	void Setup(const FEHDummyTuning& InTuning, const FEHFistTuning& InFists, AEHPlayerCharacter* InPlayer);
	void ResetDummy();
	void SetMode(EEHDummyMode InMode);
	EEHDummyMode GetMode() const { return Mode; }
	// A technique connecting. From is where it came from (the player's eyes), At where it landed, HandSide which of the
	// player's hands threw it (-1 left, +1 right, 0 both).
	FEHDummyHit ReceiveHit(EEHFistAction Action, const FEHStrikeDef& Def, const FVector& From, const FVector& At, float HandSide);
	bool HasModel() const;

	// Readouts for the display and automation.
	int32 Hits() const { return HitCount; }
	int32 Blocks() const { return BlockCount; }
	float TotalDamage() const { return Total; }
	const FString& LastText() const { return Last; }
	float SecondsSinceHit() const { return SinceHit; }
	int32 StrikesThrown() const { return StrikeCount; }
	bool IsWindingUp() const { return State == EState::Windup; }
	// Reaction readouts (degrees, cm/s) for tests and evidence.
	float HeadBackDegrees() const { return HeadBack.X; }
	float ChestBackDegrees() const { return ChestBack.X; }
	float TwistDegrees() const { return ChestTwist.X + HeadTwist.X; }
	float KnockbackSpeed() const { return Knockback.Size(); }
	bool WasBodyShot() const { return bLastBodyShot; }
	// Largest swing since the last hit (signed: back is positive, folding forward negative).
	float PeakHeadBack() const { return PeakHead; }
	float PeakChestBack() const { return PeakChest; }
	FString StateName() const;
	FVector LabelLocation() const;

private:
	enum class EState : uint8 { Idle, Hit, Blocked, Pushed, Windup, Recover };

	UPROPERTY()
	TObjectPtr<UAnimSequence> AnimIdle;
	UPROPERTY()
	TObjectPtr<UAnimSequence> AnimGuard;
	UPROPERTY()
	TObjectPtr<UAnimSequence> AnimHitLight;
	UPROPERTY()
	TObjectPtr<UAnimSequence> AnimHitHeavy;
	UPROPERTY()
	TObjectPtr<UAnimSequence> AnimHitBody;
	UPROPERTY()
	TObjectPtr<UAnimSequence> AnimBlockHit;
	UPROPERTY()
	TObjectPtr<UAnimSequence> AnimStrike;

	TWeakObjectPtr<AEHPlayerCharacter> Player;
	FEHDummyTuning Tuning;
	FEHFistTuning Fists;
	EEHDummyMode Mode = EEHDummyMode::Stand;
	EState State = EState::Idle;
	int32 StateFrame = 0;
	int32 StateLength = 0;
	EEHFistAction LastAction = EEHFistAction::None;
	int32 Hitstop = 0;
	int32 Cooldown = 0;
	FVector PushPerFrame = FVector::ZeroVector;
	int32 PushLeft = 0;
	float Accum = 0.0f;
	UAnimSequence* ShownSeq = nullptr;
	int32 HitCount = 0;
	int32 BlockCount = 0;
	int32 StrikeCount = 0;
	float Total = 0.0f;
	float SinceHit = 100.0f;
	FString Last;

	// Physical reaction: damped springs on the head and chest along the last hit's direction, and a sliding knockback.
	// A hit's kick waits through its hitstop (the frozen moment of contact), then releases.
	struct FSpring
	{
		float X = 0.0f;   // degrees
		float V = 0.0f;   // degrees per second
	};
	FSpring HeadBack, HeadTwist, HeadSide, ChestBack, ChestTwist, ChestSide;
	FVector HitDir = FVector::ForwardVector;   // horizontal, from the attacker through the dummy
	FVector Knockback = FVector::ZeroVector;   // cm/s
	struct FKick
	{
		float HeadBack = 0.0f, HeadTwist = 0.0f, HeadSide = 0.0f, ChestBack = 0.0f, ChestTwist = 0.0f, ChestSide = 0.0f;
		float Knock = 0.0f;
	};
	FKick PendingKick;
	bool bKickPending = false;
	bool bLastBodyShot = false;
	float PeakHead = 0.0f;
	float PeakChest = 0.0f;
	void UpdateReaction(float DeltaSeconds);
	void ApplyReactionPose();

	void StepFrame();
	void Enter(EState Next, int32 Length);
	void UpdateAnimation();
	UEHAnimInstance* Anim() const;
	FVector ToPlayer2D() const;
};
