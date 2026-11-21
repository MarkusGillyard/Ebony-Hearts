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
	// A technique connecting. From is where it came from (the player's eyes).
	FEHDummyHit ReceiveHit(EEHFistAction Action, const FEHStrikeDef& Def, const FVector& From, const FVector& At);
	bool HasModel() const;

	// Readouts for the display and automation.
	int32 Hits() const { return HitCount; }
	int32 Blocks() const { return BlockCount; }
	float TotalDamage() const { return Total; }
	const FString& LastText() const { return Last; }
	float SecondsSinceHit() const { return SinceHit; }
	int32 StrikesThrown() const { return StrikeCount; }
	bool IsWindingUp() const { return State == EState::Windup; }
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

	void StepFrame();
	void Enter(EState Next, int32 Length);
	void UpdateAnimation();
	UEHAnimInstance* Anim() const;
	FVector ToPlayer2D() const;
};
