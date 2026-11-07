#include "EHAI.h"

namespace eh
{
namespace aidetail
{
int32_t AbsA(int32_t v) { return v < 0 ? -v : v; }

// Furthest point a strike can reach from the fighter's starting position, including travel before it hits.
int32_t Reach(const MoveDef& m)
{
	if (m.hits.empty())
	{
		return 0;
	}
	int32_t reach = 0;
	for (const HitDef& h : m.hits)
	{
		reach = h.box.x1 > reach ? h.box.x1 : reach;
	}
	const int32_t firstActive = m.hits.front().frames.first;
	for (const TravelSeg& seg : m.travel)
	{
		for (int32_t f = seg.frames.first; f <= seg.frames.last && f < firstActive; ++f)
		{
			reach += seg.vx;
		}
	}
	return reach;
}

int32_t FindByAnim(const CharacterDef& c, const char* id)
{
	return c.FindMove(id);
}
}

using namespace aidetail;

CpuTuning TuningFor(CpuLevel level)
{
	CpuTuning t;
	switch (level)
	{
	case CpuLevel::Easy:
		t = CpuTuning{26, 25, 0, 15, 10, 30, 25, 15, 3};
		break;
	case CpuLevel::Normal:
		t = CpuTuning{18, 55, 5, 45, 35, 12, 40, 55, 6};
		break;
	case CpuLevel::Hard:
		t = CpuTuning{11, 80, 20, 80, 60, 4, 50, 70, 8};
		break;
	}
	return t;
}

void CpuController::Setup(int player, CpuLevel level, uint32_t seed)
{
	*this = CpuController();
	player_ = player;
	tune_ = TuningFor(level);
	rng_ = seed != 0 ? seed : 0x9E3779B9u;
}

uint32_t CpuController::Next()
{
	uint32_t x = rng_;
	x ^= x << 13;
	x ^= x >> 17;
	x ^= x << 5;
	rng_ = x;
	return x;
}

bool CpuController::Roll(int32_t pct)
{
	return static_cast<int32_t>(Next() % 100u) < pct;
}

const MatchState& CpuController::Observed() const
{
	return ObservedAgo(tune_.reactionFrames);
}

const MatchState& CpuController::ObservedAgo(int32_t frames) const
{
	// history_[historyHead_ - 1] is the newest; walk back the given frames (clamped to what is stored).
	int back = frames;
	if (back > historyCount_ - 1)
	{
		back = historyCount_ - 1;
	}
	if (back < 0)
	{
		back = 0;
	}
	const int idx = ((historyHead_ - 1 - back) % kHistory + kHistory) % kHistory;
	return history_[idx];
}

int8_t CpuController::RawX(const Match& match, int8_t dirToward) const
{
	if (dirToward == 0)
	{
		return 0;
	}
	const FighterState& me = match.State().f[player_];
	const FighterState& opp = match.State().f[1 - player_];
	const int32_t side = opp.x > me.x ? 1 : (opp.x < me.x ? -1 : me.facing);
	return static_cast<int8_t>(dirToward * side);
}

void CpuController::Queue(uint8_t button, int8_t dirToward, int32_t delay)
{
	if (pendingDelay_ >= 0 || Roll(tune_.dropPct))
	{
		return;
	}
	pendingButton_ = button;
	pendingDir_ = dirToward;
	pendingDelay_ = delay < 0 ? 0 : delay;
}

InputFrame CpuController::Emit(const Match& match, uint8_t pressed, int8_t dirToward)
{
	InputFrame in;
	in.x = RawX(match, dirToward);
	in.y = jumpNext_ ? 1 : 0;
	jumpNext_ = false;
	in.held = static_cast<uint8_t>(held_ | pressed);
	// A physical button cannot become held without a press: emit the edge so CPU input matches a device.
	in.pressed = static_cast<uint8_t>(pressed | (in.held & ~lastHeld_));
	lastHeld_ = in.held;
	return in;
}

InputFrame CpuController::Decide(const Match& match)
{
	const MatchState& cur = match.State();
	history_[historyHead_] = cur;
	historyHead_ = (historyHead_ + 1) % kHistory;
	if (historyCount_ < kHistory)
	{
		++historyCount_;
	}
	const FighterState& me = cur.f[player_];
	const int opponent = 1 - player_;
	const CharacterDef& mine = match.Character(player_);
	const CharacterDef& theirs = match.Character(opponent);
	if (cur.phase != Phase::Fight)
	{
		held_ = 0;
		lastHeld_ = 0;
		pendingDelay_ = -1;
		guardFrames_ = 0;
		return InputFrame();
	}

	const bool wasHit = lastHealth_ >= 0 && me.health < lastHealth_;
	lastHealth_ = me.health;
	const uint8_t prevHeld = held_;

	// Training dummies react to the live state: they are tools, not opponents.
	if (dummy_ != DummyMode::Cpu)
	{
		held_ = 0;
		uint8_t press = 0;
		const bool techs = dummy_ == DummyMode::Block || dummy_ == DummyMode::TechThrows;
		if (techs && me.state == FState::Thrown && me.throwFrame == 2)
		{
			press = BtnThrow;
		}
		if (dummy_ == DummyMode::Block)
		{
			held_ = BtnBlock;
		}
		else if (dummy_ == DummyMode::BlockAfterHit)
		{
			if (wasHit)
			{
				afterHitFrames_ = 90;
			}
			if (afterHitFrames_ > 0)
			{
				--afterHitFrames_;
				held_ = BtnBlock;
			}
		}
		else if (dummy_ == DummyMode::RandomBlock)
		{
			const FighterState& opp = cur.f[opponent];
			if (opp.state == FState::Attack)
			{
				const int32_t start = cur.frame - opp.moveFrame;
				if (decidedFor_ != start)
				{
					decidedFor_ = start;
					defend_ = Roll(50);
				}
				if (defend_)
				{
					held_ = BtnBlock;
				}
			}
			else if (me.state == FState::Blockstun && (prevHeld & BtnBlock))
			{
				held_ = BtnBlock;
			}
		}
		InputFrame in;
		in.held = static_cast<uint8_t>(held_ | press);
		in.pressed = static_cast<uint8_t>(press | ((held_ & ~prevHeld) & BtnBlock));
		return in;
	}

	const MatchState& obs = Observed();
	const FighterState& opp = obs.f[opponent];
	const int32_t dist = AbsA(cur.f[opponent].x - me.x);    // spacing is judged on current positions
	const int32_t cm = kUnitsPerCm;
	uint8_t press = 0;
	int8_t pressDir = 0;

	if (pendingDelay_ >= 0 && pendingDelay_-- == 0)
	{
		press = pendingButton_;
		pressDir = pendingDir_;
		pendingDelay_ = -1;
	}

	// Throw escape: the window is short, so the CPU answers on a guess rather than on reaction.
	if (me.state == FState::Thrown)
	{
		const int32_t start = cur.frame - me.throwFrame;
		if (techDecidedFor_ != start)
		{
			techDecidedFor_ = start;
			if (Roll(tune_.techPct))
			{
				Queue(BtnThrow, 0, 1 + static_cast<int32_t>(Next() % 7u));
			}
		}
		held_ = 0;
		return Emit(match, press, pressDir);
	}

	// Chain follow-ups while a light string is connecting.
	if (me.state == FState::Attack && me.connected && press == 0)
	{
		const MoveDef& m = mine.moves[static_cast<size_t>(me.move)];
		if (!m.cancelIndices.empty() && m.cancelFrames.Contains(me.moveFrame + 2) && pendingDelay_ < 0)
		{
			const bool finish = me.connectedHit && (m.id == "L2" || Roll(20)) && Roll(60);
			Queue(finish ? BtnSpecial : BtnLight, finish ? static_cast<int8_t>(Roll(50) ? 1 : 0) : 0, 0);
		}
	}

	const bool actionable = me.state == FState::Neutral || me.state == FState::Guard;
	if (guardFrames_ > 0)
	{
		--guardFrames_;
	}

	// Anti-air: a jump coming in is met with a jab (any hit knocks a jumper down), decided once per seen jump. The jab
	// waits until the jumper is about to come into its reach; thrown on sight it often missed short of the jumper.
	// Otherwise the CPU blocks, or, when a held block cannot stop a jump attack, may step back out of its reach.
	const Rules& rules = match.GetRules();
	// A jump is the most visible thing a fighter does: it is noticed in two thirds of the usual reaction time (at the
	// full delay a Normal CPU saw a jump-in only once its attack was already out).
	const MatchState& jumpObs = ObservedAgo(tune_.reactionFrames * 2 / 3);
	const FighterState& jumper0 = jumpObs.f[opponent];
	const bool airAttack = jumper0.state == FState::Attack && jumper0.move >= 0 && theirs.moves[static_cast<size_t>(jumper0.move)].air;
	// While a jump it has seen is coming at it, the CPU does not start a poke from neutral (a slow strike gets stuffed).
	const bool jumpIncoming = jumper0.jumpFrame > rules.jumpSquat && jumper0.jumpDir > 0 && (jumper0.state == FState::Jump || airAttack);
	if (jumpIncoming && actionable && press == 0 && dist < 200 * cm)
	{
		const int32_t jumpStart = jumpObs.frame - jumper0.jumpFrame;
		if (antiAirFor_ != jumpStart)
		{
			antiAirFor_ = jumpStart;
			antiAirArmed_ = -1;
			if (Roll(tune_.antiAirPct))
			{
				antiAirArmed_ = jumpStart;
			}
			else if (!rules.heldBlockStopsJumpIns && Roll(50))
			{
				retreatFrames_ = 30;
			}
			else if (Roll(tune_.blockPct))
			{
				defend_ = true;
				guardFrames_ = 40;
			}
		}
	}
	if (antiAirArmed_ >= 0)
	{
		const FighterState& jumper = cur.f[opponent];
		const bool sameJump = jumper.jumpFrame > 0 && cur.frame - jumper.jumpFrame == antiAirArmed_;
		const int32_t l1 = FindByAnim(mine, "L1");
		const int32_t jabRange = (l1 >= 0 ? Reach(mine.moves[static_cast<size_t>(l1)]) : 80 * cm) + theirs.halfWidth + 15 * cm;
		if (!sameJump)
		{
			antiAirArmed_ = -1;
		}
		// Fire so the jab is out (8 frames after the press) when the jumper arrives in its reach.
		else if (actionable && press == 0 && pendingDelay_ < 0 && jumper.jumpFrame > rules.jumpSquat && dist - 8 * rules.jumpForward <= jabRange)
		{
			antiAirArmed_ = -1;
			retreatFrames_ = 0;
			Queue(BtnLight, 0, 0);
		}
	}
	// Its own jump: an attack on the way down, once per jump.
	if (me.state == FState::Jump && me.y > 0 && press == 0 && pendingDelay_ < 0)
	{
		const Rules& r = rules;
		const int32_t jumpStart = cur.frame - me.jumpFrame;
		if (airAttackFor_ != jumpStart && me.jumpFrame >= r.jumpSquat + r.jumpAir / 2 && dist < 150 * cm)
		{
			airAttackFor_ = jumpStart;
			if (Roll(80))
			{
				Queue(Roll(60) ? BtnHeavy : BtnLight, 0, 0);
			}
		}
	}

	// Defence: the CPU reacts to an attack it has seen and that can reach it.
	if (opp.state == FState::Attack && opp.move >= 0)
	{
		const MoveDef& om = theirs.moves[static_cast<size_t>(opp.move)];
		const int32_t lastActive = om.LastActiveFrame();
		const bool threatening = om.kind == MoveKind::Strike && opp.moveFrame <= lastActive && dist <= Reach(om) + mine.halfWidth + 40 * cm;
		const bool throwThreat = om.kind == MoveKind::Throw && opp.moveFrame <= lastActive && dist < 90 * cm;
		const int32_t start = obs.frame - opp.moveFrame;
		if ((threatening || throwThreat) && decidedFor_ != start)
		{
			decidedFor_ = start;
			defend_ = Roll(tune_.blockPct);
			if (defend_ && throwThreat)
			{
				// Answering a seen grab: escape attempt is handled after the connect; here step back.
				defend_ = false;
				if (actionable && Roll(40))
				{
					Queue(BtnDodge, -1, 0);
				}
			}
			else if (defend_)
			{
				const int32_t framesToActive = om.hits.front().frames.first - (opp.moveFrame + tune_.reactionFrames);
				guardFrames_ = (lastActive - opp.moveFrame) + 12;
				if (Roll(tune_.deflectPct) && framesToActive > 1)
				{
					held_ = 0;   // release so the timed press is a fresh press
					Queue(BtnBlock, 0, framesToActive - 2);
				}
				else if (Roll(15) && dist > 110 * cm && me.dodgeLockout == 0)
				{
					guardFrames_ = 0;
					Queue(BtnDodge, -1, 0);
				}
			}
		}
	}
	// While a timed block press is pending the CPU is deliberately not guarding: that is the risk of trying it.
	const bool deflectPending = pendingDelay_ >= 0 && pendingButton_ == BtnBlock;
	const bool blocking = (guardFrames_ > 0 && defend_ && !deflectPending) || press == BtnBlock;

	// Punish a seen recovery with the fastest strike that reaches.
	if (actionable && !blocking && press == 0 && pendingDelay_ < 0 && opp.state == FState::Attack && opp.move >= 0)
	{
		const MoveDef& om = theirs.moves[static_cast<size_t>(opp.move)];
		const int32_t lastActive = om.kind == MoveKind::Dodge ? om.invulnStrike.last : om.LastActiveFrame();
		const int32_t start = obs.frame - opp.moveFrame;
		if (opp.moveFrame > lastActive && decidedFor_ != start + 100000)
		{
			decidedFor_ = start + 100000;
			if (Roll(tune_.punishPct))
			{
				const int32_t l1 = FindByAnim(mine, "L1");
				const int32_t h = FindByAnim(mine, "H");
				const int32_t gap = dist - theirs.halfWidth;
				if (l1 >= 0 && gap <= Reach(mine.moves[static_cast<size_t>(l1)]))
				{
					Queue(BtnLight, 0, 0);
				}
				else if (h >= 0 && gap <= Reach(mine.moves[static_cast<size_t>(h)]))
				{
					Queue(BtnHeavy, 0, 0);
				}
				else if (gap < 170 * cm)
				{
					Queue(BtnSpecial, 1, 0);
				}
			}
		}
	}

	held_ = blocking ? BtnBlock : 0;
	if (blocking)
	{
		walk_ = 0;
		return Emit(match, static_cast<uint8_t>(press & ~prevHeld), press ? pressDir : 0);
	}

	// Neutral game: hold a preferred range, poke from it, and occasionally commit.
	if (actionable && press == 0 && pendingDelay_ < 0)
	{
		const int32_t hIndex = FindByAnim(mine, "H");
		const int32_t pref = (hIndex >= 0 ? Reach(mine.moves[static_cast<size_t>(hIndex)]) : 120 * cm) + theirs.halfWidth - 10 * cm;
		const int32_t buffIndex = FindByAnim(mine, "BS");
		if (waitFrames_ > 0)
		{
			--waitFrames_;
		}
		if (retreatFrames_ > 0)
		{
			--retreatFrames_;
			walk_ = -1;
			return Emit(match, press, walk_);
		}
		if (buffIndex >= 0 && mine.moves[static_cast<size_t>(buffIndex)].kind == MoveKind::Buff && me.meter >= mine.moves[static_cast<size_t>(buffIndex)].meterCost && me.auraFrames == 0 && dist > 260 * cm)
		{
			Queue(BtnSpecial, -1, 0);
		}
		else if (buffIndex >= 0 && mine.moves[static_cast<size_t>(buffIndex)].kind == MoveKind::Strike && me.meter >= mine.moves[static_cast<size_t>(buffIndex)].meterCost && opp.state == FState::Attack && dist < 130 * cm && Roll(tune_.punishPct / 4))
		{
			Queue(BtnSpecial, -1, 0);
		}
		else if (waitFrames_ == 0 && !jumpIncoming)
		{
			waitFrames_ = 14 + static_cast<int32_t>(Next() % 40u);
			const int32_t gap = dist - theirs.halfWidth;
			const uint32_t roll = Next() % 100u;
			// A guard it has seen held is opened with a grab (grappling on) or, when a held Block cannot stop jump-ins,
			// with a jump-in from mid range.
			const bool jumpOpensGuard = !rules.heldBlockStopsJumpIns && opp.state == FState::Guard;
			if (rules.grappling && dist < 80 * cm && opp.state != FState::Attack && Roll(35))
			{
				Queue(BtnThrow, roll < 50 ? 0 : -1, 0);
			}
			else if (gap <= pref + 60 * cm && gap >= pref - 40 * cm && Roll(jumpOpensGuard ? tune_.jumpPct * 4 : tune_.jumpPct))
			{
				jumpNext_ = true;   // a jump in from mid range
				walk_ = 1;
			}
			else if (gap <= pref + 10 * cm && gap >= pref - 60 * cm)
			{
				if (roll < 35) Queue(BtnHeavy, 0, 0);
				else if (roll < 55) Queue(BtnHeavy, 1, 0);
				else if (roll < 75) Queue(BtnLight, 0, 0);
				else if (roll < 88) Queue(BtnSpecial, 1, 0);
				else Queue(BtnSpecial, 0, 0);
			}
			else if (dist > pref + 160 * cm && Roll(10) && me.dodgeLockout == 0)
			{
				Queue(BtnDodge, 1, 0);
			}
		}
		if (walkFrames_ > 0)
		{
			--walkFrames_;
		}
		else
		{
			walkFrames_ = 8 + static_cast<int32_t>(Next() % 20u);
			const int32_t gap = dist - theirs.halfWidth;
			if (gap > pref + 20 * cm)
			{
				walk_ = Roll(tune_.aggressionPct + 40) ? 1 : 0;
			}
			else if (gap < pref - 70 * cm)
			{
				walk_ = Roll(60) ? -1 : 0;
			}
			else
			{
				const uint32_t r = Next() % 100u;
				walk_ = static_cast<int8_t>(r < static_cast<uint32_t>(tune_.aggressionPct) ? 1 : (r < 70u ? 0 : -1));
			}
		}
	}
	else if (!actionable)
	{
		walk_ = 0;
	}
	return Emit(match, press, press ? pressDir : walk_);
}
}
