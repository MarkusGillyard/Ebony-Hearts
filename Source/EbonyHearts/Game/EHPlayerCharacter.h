// The first-person player: Unreal character movement and collision, a camera at eye height, Stamina
// for sprinting, and a hidden full-body placeholder that only shadows and reflections show. The director samples the
// devices and hands the pawn one FEHFirstPersonInput per frame, so movement and look follow the game's own remappable
// input path.
#pragma once

#include "CoreMinimal.h"
#include "EHChapel.h"
#include "EHPack.h"
#include "EHCombatText.h"
#include "EHWorldClock.h"
#include "EHFists.h"
#include "EHMagic.h"
#include "EHWolf.h"
#include "EHTrainingDummy.h"
#include "GameFramework/Character.h"

#include "EHPlayerCharacter.generated.h"

class UCameraComponent;
class USpringArmComponent;
class UAnimSequence;
class UEHViewArms;

struct FEHLockOnTuning
{
	float Range = 1800.0f;
	float BreakRange = 2200.0f;
	float ConeDegrees = 55.0f;
	float TrackSpeed = 14.0f;
	float LosGrace = 1.2f;
	float SwitchMouse = 90.0f;
	float SwitchStick = 0.72f;
	float SwitchCooldown = 0.25f;
	bool Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError);
};

// The third-person view: a camera on a boom behind the right shoulder (Data/firstperson.json "thirdPerson").
struct FEHThirdPersonTuning
{
	float Distance = 260.0f;      // cm from the pivot to the camera
	float ShoulderOffset = 45.0f; // cm to the right of the pivot
	float PivotBelowEye = 15.0f;  // cm the pivot sits below the eyes
	float CameraLift = 10.0f;     // cm the camera rises over the pivot
	float ProbeRadius = 12.0f;    // cm; walls pull the camera in rather than clip through
	float LagSpeed = 14.0f;       // position follow rate (0 = rigid)
	float SwitchSeconds = 0.3f;   // the blend between first and third person
	bool Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError);
};

struct FEHFirstPersonTuning
{
	float WalkSpeed = 400.0f;
	float SprintSpeed = 700.0f;
	float CrouchSpeed = 200.0f;
	float Acceleration = 2400.0f;
	float BrakingDeceleration = 2400.0f;
	float GroundFriction = 8.0f;
	float AirControl = 0.35f;
	float JumpVelocity = 420.0f;
	float JumpBufferSeconds = 0.15f;
	float GravityScale = 1.0f;
	float StepHeight = 45.0f;
	float WalkableFloorDegrees = 46.0f;
	float CapsuleRadius = 34.0f;
	float StandHeight = 180.0f;
	float CrouchHeight = 116.0f;
	float StandEyeHeight = 165.0f;
	float CrouchEyeHeight = 100.0f;
	float EyeBlendSeconds = 0.12f;
	float StaminaMax = 100.0f;
	float SprintSecondsFromFull = 6.0f;
	float StaminaRecoverPerSecond = 25.0f;
	float StaminaRecoverDelay = 0.8f;
	float SprintRestartStamina = 20.0f;
	float SprintForwardMin = 0.3f;
	float StickDeadZone = 0.18f;
	float StickYawDegPerSecond = 200.0f;
	float StickPitchDegPerSecond = 140.0f;
	float StickExponent = 2.0f;
	float PitchLimit = 85.0f;
	float WaterSurfaceZ = 3.0f;
	float KillZ = -400.0f;
	FVector Spawn = FVector(0, 300, 0);
	float SpawnYaw = -90.0f;
	float StepIntervalWalk = 0.52f;
	float StepIntervalSprint = 0.36f;
	float StepIntervalCrouch = 0.70f;
	float PlayerHealth = 100.0f;
	FEHFistTuning Fists;
	FEHDummyTuning Dummy;
	FEHMagicTuning Magic;
	FEHWolfTuning Wolf;     // the Chapel wolf (milestone 5)
	FEHChapelTuning Chapel; // the Chapel's interactions and prayer (interior stage 2)
	FEHWorldClockTuning Clock; // Destiny's Ark's time
	FEHPackTuning Pack;     // the Chapel wolves as a pack (milestone 6)
	FEHCombatTextTuning CombatText; // comic-book combat text (milestone 7)
	FEHLockOnTuning LockOn; // Souls-style target lock-on
	FEHThirdPersonTuning ThirdPerson; // the over-the-shoulder view

	// Reads Content/Data/firstperson.json text; a missing field keeps its default, a bad value is reported.
	bool Load(const FString& Text, FString& OutError);
	FString Describe() const;
};

struct FEHFirstPersonInput
{
	FVector2D Move = FVector2D::ZeroVector;   // X right, Y forward; length at most 1
	FVector2D Look = FVector2D::ZeroVector;   // degrees this frame: X yaw right, Y pitch up
	bool bJumpPressed = false;
	bool bCrouch = false;                     // wanted posture (holds and toggles are resolved by the director)
	bool bSprint = false;
	EEHFistAction FistPress = EEHFistAction::None;   // the technique or spell pressed this frame, if any
	bool bBlock = false;                             // the guard button is held
};

// Something the presentation reacts to (sounds, ripples).
struct FEHFirstPersonEvent
{
	enum class EKind : uint8 { Step, Jump, Land, Reset, Swing, Contact, Wall, Hurt, Guarded, Died, CastStart, Cast, Refused, Fizzle };
	EKind Kind = EKind::Step;
	FVector Location = FVector::ZeroVector;   // at the feet
	float WaterDepth = 0.0f;                  // cm of water at the feet (0 when dry)
	float Strength = 1.0f;                    // landing speed or step pace, 0..1
	EEHFistAction Action = EEHFistAction::None;
	float Damage = 0.0f;                      // dealt (Contact) or taken (Hurt, Guarded)
	bool bBlocked = false;                    // Contact: the target guarded it
	bool bBody = false;                       // Contact: landed on the body rather than the head
	FVector Direction = FVector::ZeroVector;  // Cast: the spell's line (Fireball) or the wall's facing (Ice Wall)
	bool bNoQhi = false;                      // Refused: not enough Qhi (otherwise no room for the wall)
	bool bIce = false;                        // Wall: the strike landed on an Ice Wall
	bool bShattered = false;                  // Wall: and broke it
	TWeakObjectPtr<AActor> Target;            // Contact: what was struck (the dummy or a wolf)
	float Reflected = 0.0f;                   // Contact: a wolf turned the blow back (Hero of Humanity)
	bool bKilled = false;                     // Contact: the blow killed a wolf
	bool bAbsorbed = false;                   // Guarded / Hurt: a wolf took it instead
};

UCLASS(NotBlueprintable)
class AEHPlayerCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AEHPlayerCharacter(const FObjectInitializer& ObjectInitializer);
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void Landed(const FHitResult& Hit) override;
	virtual void OnStartCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust) override;
	virtual void OnEndCrouch(float HalfHeightAdjust, float ScaledHalfHeightAdjust) override;

	void ApplyTuning(const FEHFirstPersonTuning& InTuning);
	void ApplyInput(const FEHFirstPersonInput& In, float DeltaSeconds);
	void CancelActionsForPrayer();
	void SetFieldOfView(float HorizontalDegrees);
	// Camera kicks from contact and hits are scaled by this (0 with Reduce camera shake).
	void SetShakeScale(float Scale) { ShakeScale = Scale; }
	// A strike against the player from World location From. Returns the damage taken (after the guard).
	// bOwnBlow: the player's own blow turned back on them (no guard, no protector).
	float ReceiveStrike(float Damage, const FVector& From, bool bOwnBlow = false);
	// Asked before a strike lands: true if someone else takes it (a Chapel wolf protecting a Hero of Humanity).
	void SetAbsorber(TFunction<bool(float, const FVector&)> InAbsorber) { Absorber = MoveTemp(InAbsorber); }
	void SetShadowForm(bool bOn) { bShadowForm = bOn; }
	float Health() const { return HealthValue; }
	void SetHealthForTest(float Value) { HealthValue = FMath::Clamp(Value, 1.0f, Tuning.PlayerHealth); }
	float HealthFraction() const { return Tuning.PlayerHealth > 0.0f ? HealthValue / Tuning.PlayerHealth : 0.0f; }
	float SecondsSinceHurt() const { return SinceHurt; }
	const FEHFists& GetFists() const { return Fists; }
	UEHViewArms* ViewArms() const { return Arms; }
	// The view's weight: a kick of pitch, forward travel and roll that springs back (respects reduced shake).
	void AddCameraKick(float PitchDegrees, float ForwardCm, float RollDegrees) { Kick(PitchDegrees, ForwardCm, RollDegrees); }
	bool WasLastStrikeGuarded() const { return bLastStrikeGuarded; }
	// Back to the Chapel's start with full Stamina, standing, at rest.
	void ResetToStart();
	void TakeEvents(TArray<FEHFirstPersonEvent>& Out) { Out.Append(Events); Events.Reset(); }

	float Qhi() const { return QhiValue; }
	float QhiFraction() const { return Stats.Qhi > 0.0f ? QhiValue / Stats.Qhi : 0.0f; }
	float SecondsSinceQhiChange() const { return QhiIdle; }
	float SecondsSinceRefused() const { return SinceRefused; }
	const FEHPlayerStats& GetStats() const { return Stats; }
	// Live stat changes (development tools); pools are clamped to their new maximum.
	void SetStats(const FEHPlayerStats& InStats);
	void SetQhiForTest(float Value) { QhiValue = FMath::Clamp(Value, 0.0f, Stats.Qhi); QhiIdle = 0.0f; }
	// Where an Ice Wall cast now would stand (its base on the floor) and face; false when there is no room.
	bool FindIceWallPlacement(FVector& OutBase, FVector& OutFacing) const;
	int32 SpellsCast() const { return CastCount; }
	int32 SpellsRefused() const { return RefusedCount; }
	float Stamina() const { return StaminaValue; }
	float StaminaFraction() const { return Tuning.StaminaMax > 0.0f ? StaminaValue / Tuning.StaminaMax : 0.0f; }
	float SecondsSinceStaminaChange() const { return StaminaIdle; }
	bool IsSprinting() const { return bSprinting; }
	bool IsExhausted() const { return bExhausted; }
	float WaterDepthAtFeet() const { return WaterDepth; }
	// The Chapel's water sheets (owned by the director); without them the tuned surface covers everything.
	void SetWater(const FEHWater* InWater) { Water = InWater; }
	float EyeHeight() const { return EyeZ; }
	FVector FeetLocation() const;
	// The eyes: every aim, reach and line of sight starts here, in either view.
	UCameraComponent* Camera() const { return CameraComp; }
	// The camera the player is looking through (the eyes, or the third-person camera behind the shoulder).
	UCameraComponent* ViewCamera() const;
	// Switches between first and third person; bInstant skips the blend (loading, tests).
	void SetThirdPerson(bool bOn, bool bInstant = false);
	bool IsThirdPerson() const { return bThirdPerson; }
	// 0 first person .. 1 fully behind the shoulder (the blend in progress).
	float ThirdPersonBlend() const { return ViewBlend; }
	// The clip the visible body is playing (tests and the developer state line).
	FString BodyClipName() const;
	const FEHFirstPersonTuning& GetTuning() const { return Tuning; }
	// Development aid: shows the placeholder body to the player's own camera (shadow and reflection review).
	void SetBodyVisibleToSelf(bool bVisible);
	bool HasBodyPlaceholder() const;

private:
	UPROPERTY()
	TObjectPtr<UCameraComponent> CameraComp;
	UPROPERTY()
	TObjectPtr<USkeletalMeshComponent> Body;
	UPROPERTY()
	TObjectPtr<UEHViewArms> Arms;
	UPROPERTY()
	TObjectPtr<USpringArmComponent> Boom;
	UPROPERTY()
	TObjectPtr<UCameraComponent> ThirdCamera;
	// Wren's clips from the 2.5D slice, by role (see UpdateBody).
	UPROPERTY()
	TMap<FName, TObjectPtr<UAnimSequence>> BodyClips;
	FName BodyClip;
	double BodyTime = 0.0;
	EEHFistAction BodyAction = EEHFistAction::None;
	bool bThirdPerson = false;
	bool bBodyShownForReview = false;   // fp_body_visible
	float ViewBlend = 0.0f;
	void UpdateView(float DeltaSeconds);
	void ApplyViewVisibility();

	FEHFirstPersonTuning Tuning;
	float StaminaValue = 100.0f;
	float StaminaIdle = 10.0f;     // seconds since Stamina last changed
	float SinceDrain = 10.0f;
	bool bSprinting = false;
	bool bExhausted = false;       // emptied by sprinting: no sprint until SprintRestartStamina
	bool bWantCrouch = false;
	float JumpBuffer = 0.0f;
	float EyeZ = 165.0f;           // smoothed eye height above the feet
	float WaterDepth = 0.0f;
	float StepTimer = 0.0f;
	float FallStartZ = 0.0f;
	bool bWasFalling = false;
	TArray<FEHFirstPersonEvent> Events;
	TFunction<bool(float, const FVector&)> Absorber;
	FEHFists Fists;
	float FistAccum = 0.0f;
	float HealthValue = 100.0f;
	float SinceHurt = 100.0f;
	float ShakeScale = 1.0f;
	float KickPitch = 0.0f;        // degrees, decaying camera kick
	float KickRoll = 0.0f;         // degrees
	float KickForward = 0.0f;      // cm along the view
	FEHPlayerStats Stats;
	float QhiValue = 100.0f;
	float QhiIdle = 10.0f;         // seconds since Qhi last changed
	float SinceCast = 10.0f;
	float SinceRefused = 10.0f;
	int32 CastCount = 0;
	int32 RefusedCount = 0;
	bool CanCast(EEHFistAction Spell) const;
	bool bShadowForm = false;   // a Shadow cannot use Qhi-based spells (New Direction, "Playing as a Shadow")
	void ReleaseSpell(EEHFistAction Spell);
	void AddQhi(float Amount);

	void UpdateWater();
	const FEHWater* Water = nullptr;
	void UpdateCamera(float DeltaSeconds);
	void UpdateBody();
	void Emit(FEHFirstPersonEvent::EKind Kind, float Strength);
	void StepFists();
	void CheckContact(EEHFistAction Action);
	void Kick(float PitchDegrees, float ForwardCm = 0.0f, float RollDegrees = 0.0f);
	bool bLastStrikeGuarded = false;
};
