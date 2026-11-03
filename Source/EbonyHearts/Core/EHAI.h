// CPU opponent and training dummy. Both produce ordinary InputFrames through the same rules as a player.
// The CPU only sees the opponent through snapshots delayed by its reaction time; it never reads pending inputs.
#pragma once

#include "EHMatch.h"

#include <cstdint>

namespace eh
{
enum class CpuLevel : uint8_t { Easy, Normal, Hard };

enum class DummyMode : uint8_t
{
	Stand,          // no input
	Block,          // holds block and techs throws
	BlockAfterHit,  // blocks for a while after being hit
	RandomBlock,    // blocks each incoming attack half of the time
	TechThrows,     // stands but always escapes throws
	Cpu,            // full CPU behaviour
};

struct CpuTuning
{
	int32_t reactionFrames = 18;   // delay before the CPU sees the opponent's state
	int32_t blockPct = 50;         // chance to defend a seen attack
	int32_t deflectPct = 0;        // chance a defence is a timed block press
	int32_t punishPct = 40;        // chance to punish a seen recovery
	int32_t techPct = 30;          // chance to escape a throw
	int32_t dropPct = 15;          // chance an intended press is not made (execution errors)
	int32_t aggressionPct = 35;    // chance per decision to step in rather than wait
};

CpuTuning TuningFor(CpuLevel level);

class CpuController
{
public:
	void Setup(int player, CpuLevel level, uint32_t seed);
	void SetDummy(DummyMode mode) { dummy_ = mode; }
	DummyMode Dummy() const { return dummy_; }
	// Call once per tick before Match::Tick with the current (pre-tick) match.
	InputFrame Decide(const Match& match);

private:
	static constexpr int kHistory = 64;
	int player_ = 1;
	CpuTuning tune_;
	DummyMode dummy_ = DummyMode::Cpu;
	uint32_t rng_ = 1;
	MatchState history_[kHistory];
	int historyCount_ = 0;
	int historyHead_ = 0;
	uint8_t held_ = 0;
	uint8_t lastHeld_ = 0;    // what was last emitted, so newly held buttons also produce a press edge
	int8_t walk_ = 0;
	int32_t walkFrames_ = 0;
	int32_t guardFrames_ = 0;
	int32_t waitFrames_ = 0;
	int32_t pendingDelay_ = -1;
	uint8_t pendingButton_ = 0;
	int8_t pendingDir_ = 0;
	int32_t decidedFor_ = -1;      // opponent move-start frame the defence decision was made for
	bool defend_ = false;
	int32_t techDecidedFor_ = -1;
	int32_t afterHitFrames_ = 0;
	int32_t lastHealth_ = -1;

	uint32_t Next();
	bool Roll(int32_t pct);
	const MatchState& Observed() const;
	void Queue(uint8_t button, int8_t dirToward, int32_t delay);
	InputFrame Emit(const Match& match, uint8_t pressed, int8_t dirToward);
	int8_t RawX(const Match& match, int8_t dirToward) const;
};
}
