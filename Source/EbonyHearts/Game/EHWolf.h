// A Chapel wolf (milestone 5): a peaceful guardian first. How it treats the player follows the player's alignment
// band: friendly and protective toward Good, keeping its distance from Neutral, hostile toward Evil (it senses the
// menacing aura). A swing or cast at it that does not connect is a threat: it backs off and gives the player a
// chance to stop. Real harm makes it hostile until the player leaves the Chapel's floor (the Threshold Hall, by the
// door, counts as outside; the loft above it does not) and comes back. A Hero of Humanity cannot harm it: the blow lands on the player instead, and the wolf takes
// blows meant for that player. Movement uses the navigation mesh (an Ice Wall reroutes it); behaviour is stepped at
// 60 Hz like the techniques. The body is a placeholder in parts (Tools/Blender/wolf), posed and animated in code.
#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "EHAlignment.h"
#include "GameFramework/Character.h"

#include "EHWolf.generated.h"

class AEHPlayerCharacter;
class AEHTrainingDummy;
class UStaticMeshComponent;

struct FEHWolfTuning
{
	float Health = 60.0f;
	FVector Home = FVector(320, -1450, 0);   // where it rests (feet), and the yaw it faces
	float HomeYaw = 90.0f;
	float LeaveLineY = 560.0f;     // the Chapel's floor ends here: the Threshold Hall's floor beyond counts as outside
	float LeaveMaxZ = 250.0f;      // ...below this height (the loft above the hall is still inside)
	float CalmSeconds = 3.0f;      // a provoked wolf calms once the player has been outside this long
	float WalkSpeed = 260.0f;
	float RunSpeed = 640.0f;
	float FollowDistance = 240.0f; // a friendly wolf stays about this far from the player
	float KeepDistance = 460.0f;   // a wary wolf keeps at least this far away
	float ThreatRange = 480.0f;    // a swing or cast aimed at it within this range is a threat
	float DisengageSeconds = 3.0f;
	float DisengageDistance = 520.0f;
	float CircleRadius = 330.0f;
	float BiteRange = 150.0f;      // starts a bite this close (centre to centre)
	float BiteReach = 175.0f;      // and connects if still this close and in front
	float BiteDamage = 8.0f;
	int32 BiteWindup = 14;         // frames
	int32 BiteRecover = 24;
	float LungeMin = 300.0f;
	float LungeMax = 620.0f;
	float LungeSpeed = 1050.0f;
	float LungeDamage = 12.0f;
	int32 LungeWindup = 24;
	int32 LungeRecover = 34;
	int32 AttackCooldown = 45;
	int32 Hitstun = 18;
	float AbsorbRange = 1000.0f;   // Hero of Humanity: a wolf this close takes the player's blows
	float ProtectRange = 1200.0f;  // Good: a wolf this close goes for anything striking at the player
	FVector Spawn = FVector(320, -1450, 0);
	bool Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError);
	FString Describe() const;
};

UENUM()
enum class EEHWolfState : uint8
{
	Calm,          // its attitude's resting behaviour (following, keeping its distance, resting at home)
	Disengage,     // backing off from a threat
	Hostile,       // closing and circling
	BiteWindup,
	Bite,
	LungeWindup,
	Lunge,
	Recover,
	Hitstun,
	Protect,       // Good: going for something that threatens the player
	Guarding,      // provoked, but the player is outside: waits at the edge of the Chapel
	Dead,
};

const TCHAR* EHWolfStateName(EEHWolfState S);

// A wolf's part in a pack's fight (milestone 6), set each frame by the director's pack. A lone wolf, or one not
// fighting, is Free and behaves as before.
enum class EEHPackRole : uint8
{
	Free,      // no pack coordination
	Attacker,  // holds the pack's turn: may bite and lunge
	Waiting,   // the pack takes turns: circles close, presses, but does not attack
	HoldBack,  // one-on-one: stands back at a distance and watches
};

// What a strike from the player did to the wolf.
struct FEHWolfHit
{
	float Damage = 0.0f;      // taken by the wolf
	float Reflected = 0.0f;   // Hero of Humanity: lands on the player instead
	bool bKilled = false;
	bool bHarmed = false;
};

UCLASS(NotBlueprintable)
class AEHWolf : public ACharacter
{
	GENERATED_BODY()

public:
	AEHWolf(const FObjectInitializer& ObjectInitializer);
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	void Setup(const FEHWolfTuning& InTuning, AEHPlayerCharacter* InPlayer, AEHTrainingDummy* InDummy);
	void ResetWolf();
	void SetAlignment(int32 Tier) { Alignment = Tier; }

	// The player swung or cast along Aim from Eye: a threat if it is aimed at the wolf and close enough.
	bool NoticeThreat(const FVector& Eye, const FVector& Aim);
	// A strike or spell from the player.
	FEHWolfHit ReceivePlayerHit(float Damage, const FVector& From, const FVector& At, bool bHeavy);
	// Hero of Humanity: take a blow meant for the player (never fatal). True if it did.
	bool Absorb(float Damage);
	// Ice Wall: frozen water holds its feet.
	void Freeze(float Seconds);
	void Displace(const FVector& Offset, AActor* Ignore);

	// The pack (milestone 6).
	void SetPackRole(EEHPackRole InRole, float InHoldBackRadius, float InWaitRadius) { PackRole = InRole; HoldBackRadius = InHoldBackRadius; WaitRadius = InWaitRadius; }
	EEHPackRole GetPackRole() const { return PackRole; }
	bool IsAttacking() const;          // in a bite or lunge, from wind-up to recovery
	int32 AttacksStarted() const { return BiteCount + LungeCount; }
	// The navigation mesh changed nearby (an Ice Wall rose or melted): re-plan the next move now.
	void RequestRepath() { LastMoveTarget = FVector(1e9); RepathCount += 1; }
	int32 Repaths() const { return RepathCount; }
	int32 StuckRepaths() const { return StuckCount; }
	float SecondsSinceAttack() const { return SinceAttack; }
	bool IsDead() const { return State == EEHWolfState::Dead; }
	bool IsFrozen() const { return FrozenLeft > 0.0f; }
	bool IsProvoked() const { return bProvoked; }
	bool IsHostile() const;
	EEHWolfState GetState() const { return State; }
	float HealthValue() const { return HealthNow; }
	void SetHealthForTest(float Value) { HealthNow = FMath::Clamp(Value, 1.0f, Tuning.Health); }
	// A test position: no movement carried over from before it was placed.
	void HaltForTest();
	FVector FeetLocation() const;
	FVector LabelLocation() const { return GetActorLocation() + FVector(0, 0, 95.0f); }
	FString Describe() const;
	// Counters for tests and the developer readout.
	int32 Bites() const { return BiteCount; }
	int32 Lunges() const { return LungeCount; }
	int32 Connected() const { return ConnectCount; }
	int32 Disengages() const { return DisengageCount; }
	int32 Absorbed() const { return AbsorbCount; }
	int32 Protects() const { return ProtectCount; }
	int32 Freezes() const { return FreezeCount; }
	bool PlayerOutside() const;

private:
	UPROPERTY()
	TObjectPtr<USceneComponent> Rig;
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Body;
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Head;
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Tail;
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> Legs[4];
	UPROPERTY()
	TObjectPtr<UStaticMeshComponent> IceCuff;

	FEHWolfTuning Tuning;
	TWeakObjectPtr<AEHPlayerCharacter> Player;
	TWeakObjectPtr<AEHTrainingDummy> Dummy;
	int32 Alignment = EHAlign::Platonic;
	EEHWolfState State = EEHWolfState::Calm;
	int32 StateFrame = 0;
	int32 StateLength = 0;
	int32 Cooldown = 0;
	float Accum = 0.0f;
	float HealthNow = 60.0f;
	bool bProvoked = false;
	float OutsideFor = 0.0f;       // seconds the player has been outside while it is provoked
	float CircleSign = 1.0f;
	int32 CircleFrames = 0;
	FVector WaitGoal = FVector(1e9);   // a waiting wolf's place on the floor, re-chosen every few frames
	int32 WaitGoalFrames = 0;
	FVector FindWaitSpot(float Radius) const;
	FVector DisengageFrom = FVector::ZeroVector;
	bool bLungeHit = false;
	float FrozenLeft = 0.0f;
	float Gait = 0.0f;             // walk cycle phase
	float WagTime = 0.0f;
	float Crouch = 0.0f;           // 0..1, eased
	float HeadThrust = 0.0f;       // 0..1, eased
	float DeadTime = 0.0f;
	FVector LastMoveTarget = FVector(1e9);
	int32 BiteCount = 0, LungeCount = 0, ConnectCount = 0, DisengageCount = 0, AbsorbCount = 0, ProtectCount = 0, FreezeCount = 0;
	EEHPackRole PackRole = EEHPackRole::Free;
	float HoldBackRadius = 650.0f;
	float WaitRadius = 520.0f;
	int32 RepathCount = 0;
	int32 StuckCount = 0;
	int32 StuckFrames = 0;
	float SinceAttack = 0.0f;

	void StepFrame();
	void Enter(EEHWolfState Next, int32 Length);
	void MoveTo(const FVector& Where, float Speed, float Accept = 40.0f);
	void Stop();
	void FaceTowards(const FVector& Where, float DegPerFrame);
	FVector ToPlayer2D() const;
	EEHWolfState Attitude() const;
	void UpdatePose(float DeltaSeconds);
};
