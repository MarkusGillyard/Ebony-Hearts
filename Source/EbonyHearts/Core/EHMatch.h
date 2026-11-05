// Authoritative fixed-step (60 Hz) combat simulation. Pure integer state; presentation reads it and never writes it.
#pragma once

#include "EHCombatData.h"

#include <cstdint>
#include <string>
#include <vector>

namespace eh
{
// One tick of player intent. x is raw screen space (-1 left, 0, +1 right) and is interpreted against the
// opponent's side when a press is buffered, so a side switch cannot reverse an input already given.
struct InputFrame
{
	int8_t x = 0;
	int8_t y = 0;          // +1 up (jump), 0 none
	uint8_t held = 0;
	uint8_t pressed = 0;   // buttons that went down since the previous tick
};

enum class FState : uint8_t
{
	Neutral,     // idle or walking; actionable
	Guard,       // holding block; actionable
	Attack,      // performing a move (strikes, throw attempts, buffs and dodges)
	Hitstun,
	Blockstun,
	Knockdown,   // on the ground, fully invulnerable
	Getup,       // rising, fully invulnerable
	Throwing,
	Thrown,
	Tech,        // throw escape recovery, invulnerable
	KO,
	Win,
	Defeated,    // lost on time; standing
	Jump,        // jump squat, then in the air (y > 0); jump attacks come from here
	Landing,     // touching down from a jump; recovering
};

enum class Phase : uint8_t { Intro, Fight, RoundEnd, MatchEnd };
enum class Mode : uint8_t { Versus, Training };

enum class EventType : uint8_t
{
	RoundIntro,
	Fight,
	MoveStart,
	Hit,
	Block,
	Deflect,
	ThrowConnect,
	ThrowTech,
	ThrowDamage,
	Knockdown,
	Getup,
	AuraStart,
	AuraEnd,
	KO,
	Timeout,
	RoundEnd,
	MatchEnd,
	Jump,
	Land,
};

enum EventFlags : uint8_t
{
	EvCounter = 1 << 0,
	EvPunish = 1 << 1,
	EvEnergy = 1 << 2,
	EvHeavy = 1 << 3,
	EvAura = 1 << 4,
	EvCancel = 1 << 5,
	EvTrade = 1 << 6,
	EvKnockdown = 1 << 7,
};

struct Event
{
	EventType type = EventType::Hit;
	int8_t player = -1;     // acting fighter (attacker, thrower, the KO'd fighter, the round winner, ...)
	int16_t move = -1;
	int32_t x = 0;          // world units, contact point when relevant
	int32_t y = 0;
	int32_t value = 0;      // damage, stun, combo count, ... depending on type
	uint8_t flags = 0;
};

struct Buffered
{
	uint8_t button = 0;
	int8_t dir = 0;         // -1 away from opponent, 0 neutral, +1 toward opponent (at press time)
	uint8_t age = 0;
};

constexpr int kBufferCapacity = 8;

struct FighterState
{
	int32_t x = 0;
	int8_t facing = 1;
	FState state = FState::Neutral;
	int32_t stateFrame = 0;
	int8_t walk = 0;
	int16_t move = -1;
	int8_t moveDir = 0;
	int32_t moveFrame = 0;
	uint32_t hitMask = 0;
	bool connected = false;
	bool connectedHit = false;
	int32_t stun = 0;
	int32_t hitstop = 0;
	int32_t pushRemaining = 0;
	int32_t pushFramesLeft = 0;
	int8_t pushSource = -1;
	int32_t health = 0;
	int32_t meter = 0;
	int32_t combo = 0;
	int32_t comboDamage = 0;
	int32_t auraFrames = 0;
	int32_t dodgeLockout = 0;
	int32_t throwInvuln = 0;
	int16_t throwIndex = -1;
	int8_t throwOwner = -1;   // index of the fighter whose ThrowDef is playing (for Thrown/Throwing)
	int32_t throwFrame = 0;
	bool throwKO = false;
	int32_t lastBlockPress = -100000;
	bool lastBlockPressTimed = false;
	bool lastBlockPressDeflected = false;
	int32_t y = 0;            // height of the feet above the floor (units)
	int32_t vy = 0;           // falling speed (units a frame) of a body hit out of the air
	int16_t jumpFrame = 0;    // frames since the jump started (squat, then air); 0 on the ground
	int8_t jumpDir = 0;       // -1 back, 0 straight up, +1 toward the opponent (at the jump start)
	uint8_t reaction = 0;     // presentation: 1 light hit, 2 heavy hit, 3 landed from a throw, 4 landed head toward the thrower
	int16_t reactMove = -1;   // presentation: the opponent's move and hit that put this fighter in hitstun
	int8_t reactHit = -1;
	int32_t roundWins = 0;
	int32_t idleFrames = 0;   // consecutive actionable frames (training refill)
	Buffered buffer[kBufferCapacity];
	uint8_t bufferCount = 0;
	InputFrame lastInput;
};

struct MatchState
{
	Phase phase = Phase::Intro;
	Mode mode = Mode::Versus;
	int32_t phaseFrame = 0;
	int32_t round = 1;
	int32_t timer = 0;
	int32_t frame = 0;
	int8_t roundWinner = -1;   // -1 none, 0/1 fighter, 2 draw
	int8_t matchWinner = -1;
	bool timeout = false;
	bool doubleKO = false;
	FighterState f[2];
	// Live frame-advantage measurement for training: positive favours advAttacker.
	int8_t advAttacker = -1;
	int32_t advStartFrame = 0;
	int32_t advReady[2] = {-1, -1};
	int32_t lastAdvantage = 0;
	int8_t lastAdvantagePlayer = -1;
	bool lastAdvantageValid = false;
};

class Match
{
public:
	bool Setup(const Rules& rules, const CharacterDef& c0, const CharacterDef& c1, Mode mode, std::string& error);
	void Tick(const InputFrame inputs[2]);

	const MatchState& State() const { return s_; }
	const std::vector<Event>& Events() const { return events_; }
	const CharacterDef& Character(int player) const { return chars_[player]; }
	const Rules& GetRules() const { return rules_; }
	uint64_t Hash() const;

	// Training controls. Called between ticks by the presentation layer.
	void TrainingResetPositions(int layout);   // 0 centre, 1 opponent at right wall, 2 player at left wall
	void TrainingPlace(int32_t x0, int32_t x1); // exact placement (units), fresh fighter states
	void SetMeter(int player, int32_t value);

	// World-space boxes for the debug overlay (units). Hurtboxes are empty while invulnerable.
	void GetHurtboxes(int player, std::vector<Box>& out) const;
	void GetHitboxes(int player, std::vector<Box>& out) const;
	Box GetPushbox(int player) const;
	bool IsActionable(int player) const;
	bool IsThrowable(int player) const;

private:
	Rules rules_;
	CharacterDef chars_[2];
	MatchState s_;
	std::vector<Event> events_;

	void ResetRound();
	void Emit(EventType type, int player, int move, int32_t x, int32_t y, int32_t value, uint8_t flags);
	void Ingest(int i, const InputFrame& in);
	void AdvanceState(int i, bool allowActions);
	void AdvanceThrow(int thrower);
	void TryActions(int i, const InputFrame& in);
	bool TryCancel(int i);
	bool StartFromBuffer(int i, bool cancel);
	int32_t SelectMove(int i, uint8_t button, int8_t dir, bool cancel) const;
	void StartMove(int i, int32_t moveIndex, int8_t dir, bool cancel);
	void EndToNeutral(int i);
	void Move(bool allowCollision);
	void ResolveCollisions();
	void ApplyStrike(int a, int k, bool trade);
	void ConnectThrow(int a);
	void BeginTech(int thrower, int victim);
	void CheckRoundEnd();
	void UpdateRoundEnd();
	void TrackAdvantage();
	void FaceOpponent(int i);
	void SetPush(int i, int32_t amount, int source);
	int32_t Clamp(int i, int32_t x) const;
	Box WorldBox(int i, const Box& local) const;
	void AddMeter(int i, int32_t amount);
	bool StrikeHittable(int i) const;
	int8_t DirToward(int i, int8_t rawX) const;
	bool InAir(int i) const;                  // past the jump squat (or still falling from a hit)
	void StartJump(int i, int8_t dir);
	void Land(int i);
};

// Human-readable names for logs, tests and the training overlay.
const char* StateName(FState state);
const char* EventName(EventType type);
}
