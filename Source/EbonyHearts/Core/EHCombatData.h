// Combat content definitions (fighters, moves, throws, match rules) and their validated loading from JSON.
// Engine-independent: everything is integer frames at 60 Hz and integer distance units (1 cm = 100 units).
#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace eh
{
class JsonValue;

constexpr int32_t kTickHz = 60;
constexpr int32_t kUnitsPerCm = 100;

enum Button : uint8_t
{
	BtnLight = 1 << 0,
	BtnHeavy = 1 << 1,
	BtnSpecial = 1 << 2,
	BtnThrow = 1 << 3,
	BtnDodge = 1 << 4,
	BtnBlock = 1 << 5,
};

// Fighter-relative direction requirement for a move. Forward/Back are resolved against facing when the move starts.
enum class DirReq : uint8_t { Any, Neutral, Forward, Back };

enum class MoveKind : uint8_t { Strike, Throw, Buff, Dodge };

// Axis-aligned box relative to the fighter origin (feet), authored as if facing right. y grows upward.
struct Box
{
	int32_t x0 = 0;
	int32_t y0 = 0;
	int32_t x1 = 0;
	int32_t y1 = 0;
	bool Valid() const { return x1 > x0 && y1 > y0; }
};

// Inclusive 1-based frame range within a move. Empty when last < first.
struct FrameRange
{
	int32_t first = 0;
	int32_t last = -1;
	bool Contains(int32_t frame) const { return frame >= first && frame <= last; }
	bool Empty() const { return last < first; }
};

struct HitDef
{
	FrameRange frames;
	Box box;
	int32_t damage = 0;
	int32_t chip = 0;
	int32_t hitstun = 0;
	int32_t blockstun = 0;
	int32_t hitstop = 0;
	int32_t hitPush = 0;      // units the defender slides on hit
	int32_t blockPush = 0;    // units the defender slides on block
	bool knockdown = false;
	bool knockdownOnCounter = false;
	bool energy = false;      // flame/energy damage (reduced by Spirit Enhanced Strikes defence)
	bool heavy = false;       // presentation: heavy reaction and impact
	std::string react;        // presentation: the defender's reaction clip ("": HitLight, or HitHeavy when heavy)
};

struct TravelSeg
{
	FrameRange frames;
	int32_t vx = 0;           // units per frame, positive = forward
};

struct HurtDef
{
	FrameRange frames;
	Box box;
	bool replaceBase = false;
};

struct AuraDef
{
	int32_t applyFrame = 0;
	int32_t frames = 0;
	int32_t damagePct = 100;      // outgoing strike damage multiplier while active
	int32_t energyTakenPct = 100; // incoming energy damage multiplier while active
};

struct MoveDef
{
	std::string id;
	std::string name;
	std::string anim;
	MoveKind kind = MoveKind::Strike;
	uint8_t button = 0;
	DirReq dir = DirReq::Any;
	bool chainOnly = false;       // reachable only through a cancel (string follow-ups)
	bool air = false;             // performed only in the air (a jump attack); ends on landing
	bool special = false;         // belongs to the special group for "@special" cancels and chip rules
	int32_t total = 0;
	int32_t meterCost = 0;
	std::vector<HitDef> hits;
	std::vector<TravelSeg> travel;
	std::vector<HurtDef> hurt;
	FrameRange airborne;
	FrameRange invulnStrike;
	FrameRange invulnThrow;
	FrameRange noPush;
	FrameRange cancelFrames;
	bool cancelOnHit = false;
	bool cancelOnBlock = false;
	std::vector<std::string> cancelInto;   // move ids or "@special"
	std::vector<int32_t> cancelIndices;    // resolved at load
	// Throw moves
	int32_t throwRange = 0;                // max front-to-front gap in units
	std::string throwForward;              // ThrowDef id when forward/neutral is held
	std::string throwBack;                 // ThrowDef id when back is held
	int32_t throwForwardIndex = -1;
	int32_t throwBackIndex = -1;
	// Buff moves
	AuraDef aura;

	int32_t LastActiveFrame() const;       // 0 when the move has no hits
};

struct ThrowDef
{
	std::string id;
	std::string name;
	std::string attackerAnim;
	std::string victimAnim;
	int32_t duration = 0;
	int32_t damageFrame = 0;
	int32_t damage = 0;
	int32_t holdX = 0;          // victim offset from thrower during the sequence (units, +forward)
	int32_t landX = 0;          // victim landing offset (units, negative lands behind = side switch)
	int32_t victimKnockdown = 0;
	bool landsHeadToward = false;   // presentation: the victim lands on its back with its head toward the thrower
};

struct CharacterDef
{
	std::string id;
	std::string name;
	int32_t maxHealth = 0;
	int32_t walkForward = 0;    // units per frame
	int32_t walkBack = 0;
	int32_t halfWidth = 0;      // pushbox half width
	Box hurt;                   // standing hurtbox
	std::vector<MoveDef> moves;
	std::vector<ThrowDef> throws;

	int32_t FindMove(const std::string& moveId) const;
	int32_t FindThrow(const std::string& throwId) const;
};

struct Rules
{
	int32_t roundFrames = 0;
	int32_t roundsToWin = 0;
	int32_t maxRounds = 0;
	int32_t introFrames = 0;
	int32_t roundEndFrames = 0;
	int32_t startX = 0;
	int32_t stageHalfWidth = 0;
	int32_t maxSeparation = 0;
	int32_t bufferFrames = 0;
	int32_t pushFrames = 0;
	int32_t timedBlockWindow = 0;
	int32_t timedBlockLockout = 0;
	int32_t timedBlockStunReduction = 0; // blockstun frames saved by a timed block
	int32_t throwTechWindow = 0;
	int32_t techFrames = 0;
	int32_t techPush = 0;
	int32_t knockdownFrames = 0;
	int32_t getupFrames = 0;
	int32_t wakeThrowInvuln = 0;
	int32_t stunThrowInvuln = 0;
	int32_t dodgeLockout = 0;
	int32_t counterHitstun = 0;
	int32_t counterDamagePct = 100;
	int32_t punishHitstun = 0;
	int32_t punishDamagePct = 100;
	int32_t hitstunDecayFromHit = 0;
	int32_t hitstunDecayPerHit = 0;
	int32_t minComboHitstun = 0;
	std::vector<int32_t> comboScaling;   // percent per hit index; the last value repeats
	int32_t meterMax = 0;
	int32_t meterHitAttackerPct = 0;
	int32_t meterHitDefenderPct = 0;
	int32_t meterBlockAttacker = 0;
	int32_t meterBlockDefender = 0;
	int32_t meterDeflect = 0;
	int32_t blockHitstopReduction = 0;
	// Jumping: up leaves the floor after jumpSquat frames, flies jumpAir frames on a parabola jumpHeight high (units)
	// moving jumpForward / jumpBack units a frame, and lands into jumpLanding frames of recovery (airAttackLanding
	// after a jump attack). Pushboxes still apply in the air, so a jump cannot pass over the opponent.
	int32_t jumpSquat = 0;
	int32_t jumpAir = 0;
	int32_t jumpLanding = 0;
	int32_t airAttackLanding = 0;
	int32_t jumpHeight = 0;
	int32_t jumpForward = 0;
	int32_t jumpBack = 0;
	int32_t fallSpeed = 0;      // units a frame added to a falling body's speed (hit out of the air)
	// A jump attack that connects with a grounded opponent keeps them in hit- or blockstun until its attacker has
	// landed and recovered, plus this many frames, however high it connected (a timed block still subtracts its
	// reduction from the blockstun).
	int32_t jumpInHitAdvantage = 0;
	int32_t jumpInBlockAdvantage = 0;
	// With false, holding Block does not stop a jump attack: only a timed block (deflect), or a fighter already in
	// blockstun, blocks it. Jumping then answers a held guard, as strikes (anti-air) and deflects answer jumping.
	bool heldBlockStopsJumpIns = true;
	// Grappling (the grab action, throws and their escapes) stays in the data and code but can be switched off:
	// with false, no throw move can start.
	bool grappling = true;
};

// Loaders validate everything the simulation relies on and report the first problem with a JSON path.
bool LoadRules(const JsonValue& root, Rules& out, std::string& error);
bool LoadCharacter(const JsonValue& root, CharacterDef& out, std::string& error);
bool LoadRulesText(const std::string& text, Rules& out, std::string& error);
bool LoadCharacterText(const std::string& text, CharacterDef& out, std::string& error);
}
