// The first-person techniques as plain game state: jab, straight, a held block and the two spells' casts,
// stepped at a fixed 60 frames per second. Hit detection, casting, reactions and the arms all read this state, so
// timing, contact and what the player sees come from one place. Frame counts are combat frames (1/60 s).
#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

enum class EEHFistAction : uint8
{
	None,
	Jab,
	Straight,
	Fireball,   // a cast: its single active frame releases the spell
	IceWall,
};

inline bool EHIsSpell(EEHFistAction Action) { return Action == EEHFistAction::Fireball || Action == EEHFistAction::IceWall; }

const TCHAR* EHFistActionName(EEHFistAction Action);

struct FEHStrikeDef
{
	int32 Startup = 6;        // frames before the first active frame
	int32 Active = 3;         // frames that can connect
	int32 Recovery = 10;      // frames after the last active frame
	float Reach = 95.0f;      // cm from the eyes along the aim
	float Radius = 18.0f;     // cm, the swept sphere
	float Damage = 6.0f;
	int32 Hitstop = 3;        // frames both sides hold on contact
	float MoveScale = 0.75f;  // walking speed multiplier during the technique
	int32 Total() const { return Startup + Active + Recovery; }
};

struct FEHFistTuning
{
	FEHStrikeDef Jab;
	FEHStrikeDef Straight;
	FEHStrikeDef Fireball;   // casts: startup, one release frame, recovery and walking speed; the rest is unused
	FEHStrikeDef IceWall;
	int32 BufferFrames = 8;       // a press this many frames before the current technique allows it still counts
	int32 BlockRaiseFrames = 5;   // frames until a raised guard protects
	int32 BlockLowerFrames = 6;   // frames to lower it again before a technique can start
	float BlockReduction = 0.7f;  // share of the damage the guard stops
	float BlockAngle = 70.0f;     // degrees either side of the view that count as the front
	float BlockMoveScale = 0.6f;
	float ArmsLinger = 0.6f;      // seconds the arms stay up after the last technique
	FEHFistTuning();
	// Reads the "fists" object of Data/firstperson.json; missing fields keep their defaults.
	bool Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError);
	const FEHStrikeDef& Def(EEHFistAction Action) const;
	FString Describe() const;
};

struct FEHFistEvent
{
	enum class EKind : uint8 { Start, Active, End, BlockUp, BlockDown, Refused };
	EKind Kind = EKind::Start;
	EEHFistAction Action = EEHFistAction::None;
	int32 ActiveFrame = 0;   // for Active: 0 on the first active frame
};

class FEHFists
{
public:
	void Configure(const FEHFistTuning& InTuning) { Tuning = InTuning; }
	// Asked when a technique is about to start; false refuses it (a spell without the Qhi, or with no room to cast)
	// and reports a Refused event instead. The cost is taken by whoever handles the Start event.
	void SetGate(TFunction<bool(EEHFistAction)> InGate) { Gate = MoveTemp(InGate); }
	void Reset();
	// Input for the next step. A press is held in a short buffer; a press while guarding is dropped.
	void Press(EEHFistAction Action);
	void SetBlockHeld(bool bHeld) { bBlockHeld = bHeld; }
	// One 60 Hz frame. Events are appended.
	void Step(TArray<FEHFistEvent>& OutEvents);
	// Contact: holds the technique for its hitstop (or the given number of frames).
	void OnContact(int32 Frames = -1);

	EEHFistAction Action() const { return Current; }
	int32 Frame() const { return FrameIndex; }
	bool InHitstop() const { return Hitstop > 0; }
	bool IsActiveFrame() const;
	bool HasConnected() const { return bConnected; }
	void MarkConnected() { bConnected = true; }
	// 0 lowered .. 1 fully raised; the guard protects only when fully raised.
	float GuardLevel() const;
	bool IsGuarding() const { return GuardFrames >= Tuning.BlockRaiseFrames && bBlockHeld; }
	bool IsBlockHeld() const { return bBlockHeld; }
	float MoveScale() const;
	// Seconds since the last technique or guard ended (for the arms).
	float IdleSeconds() const { return IdleFrames / 60.0f; }
	const FEHFistTuning& GetTuning() const { return Tuning; }

private:
	FEHFistTuning Tuning;
	EEHFistAction Current = EEHFistAction::None;
	int32 FrameIndex = 0;
	int32 Hitstop = 0;
	bool bConnected = false;
	EEHFistAction Buffered = EEHFistAction::None;
	int32 BufferAge = 0;
	bool bBlockHeld = false;
	int32 GuardFrames = 0;       // frames the guard has been rising (capped at the raise time)
	int32 LowerFrames = 0;       // frames left of lowering
	int32 IdleFrames = 600;
	TFunction<bool(EEHFistAction)> Gate;

	bool CanStart(EEHFistAction Next) const;
	void Start(EEHFistAction Next, TArray<FEHFistEvent>& OutEvents);
};
