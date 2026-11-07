#include "EHMatch.h"

namespace eh
{
namespace matchdetail
{
int32_t AbsI(int32_t v) { return v < 0 ? -v : v; }
int32_t SignI(int32_t v) { return (v > 0) - (v < 0); }
int32_t Pct(int32_t v, int32_t pct) { return static_cast<int32_t>((static_cast<int64_t>(v) * pct) / 100); }
bool Overlaps(const Box& a, const Box& b) { return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1; }
void Mix(uint64_t& h, int64_t v)
{
	for (int i = 0; i < 8; ++i)
	{
		h ^= static_cast<uint64_t>((v >> (i * 8)) & 0xFF);
		h *= 1099511628211ULL;
	}
}
}

using namespace matchdetail;

bool Match::Setup(const Rules& rules, const CharacterDef& c0, const CharacterDef& c1, Mode mode, std::string& error)
{
	const CharacterDef* chars[2] = {&c0, &c1};
	for (const CharacterDef* c : chars)
	{
		for (const MoveDef& m : c->moves)
		{
			if (m.meterCost > rules.meterMax)
			{
				error = c->id + "." + m.id + ": meterCost exceeds rules.meterMax";
				return false;
			}
		}
		for (const ThrowDef& t : c->throws)
		{
			if (t.damageFrame <= rules.throwTechWindow)
			{
				error = c->id + "." + t.id + ": damageFrame must come after the throw tech window";
				return false;
			}
		}
		if (c->halfWidth * 2 >= rules.maxSeparation)
		{
			error = c->id + ": pushbox wider than the separation limit";
			return false;
		}
	}
	rules_ = rules;
	chars_[0] = c0;
	chars_[1] = c1;
	s_ = MatchState();
	s_.mode = mode;
	for (FighterState& f : s_.f)
	{
		f.roundWins = 0;
		f.meter = 0;
	}
	ResetRound();
	events_.clear();
	return true;
}

void Match::ResetRound()
{
	for (int i = 0; i < 2; ++i)
	{
		FighterState& f = s_.f[i];
		const int32_t wins = f.roundWins;
		const int32_t meter = f.meter;
		f = FighterState();
		f.roundWins = wins;
		f.meter = meter;
		f.health = chars_[i].maxHealth;
		f.x = (i == 0) ? -rules_.startX : rules_.startX;
		f.facing = (i == 0) ? 1 : -1;
	}
	s_.timer = rules_.roundFrames;
	s_.phaseFrame = 0;
	s_.roundWinner = -1;
	s_.timeout = false;
	s_.doubleKO = false;
	s_.phase = (s_.mode == Mode::Training) ? Phase::Fight : Phase::Intro;
	s_.advAttacker = -1;
	s_.advReady[0] = s_.advReady[1] = -1;
}

void Match::TrainingResetPositions(int layout)
{
	const int32_t edge0 = -rules_.stageHalfWidth + chars_[0].halfWidth;
	const int32_t edge1 = rules_.stageHalfWidth - chars_[1].halfWidth;
	const int32_t gap = 2 * rules_.startX;
	for (int i = 0; i < 2; ++i)
	{
		FighterState& f = s_.f[i];
		const int32_t meter = f.meter;
		f = FighterState();
		f.meter = meter;
		f.health = chars_[i].maxHealth;
	}
	if (layout == 1)
	{
		s_.f[1].x = edge1;
		s_.f[0].x = edge1 - gap;
	}
	else if (layout == 2)
	{
		s_.f[0].x = edge0;
		s_.f[1].x = edge0 + gap;
	}
	else
	{
		s_.f[0].x = -rules_.startX;
		s_.f[1].x = rules_.startX;
	}
	s_.f[0].facing = 1;
	s_.f[1].facing = -1;
	s_.advAttacker = -1;
	s_.lastAdvantageValid = false;
}

void Match::TrainingPlace(int32_t x0, int32_t x1)
{
	TrainingResetPositions(0);
	s_.f[0].x = Clamp(0, x0);
	s_.f[1].x = Clamp(1, x1);
	FaceOpponent(0);
	FaceOpponent(1);
}

void Match::SetMeter(int player, int32_t value)
{
	FighterState& f = s_.f[player];
	f.meter = value < 0 ? 0 : (value > rules_.meterMax ? rules_.meterMax : value);
}

void Match::Emit(EventType type, int player, int move, int32_t x, int32_t y, int32_t value, uint8_t flags)
{
	Event e;
	e.type = type;
	e.player = static_cast<int8_t>(player);
	e.move = static_cast<int16_t>(move);
	e.x = x;
	e.y = y;
	e.value = value;
	e.flags = flags;
	events_.push_back(e);
}

int8_t Match::DirToward(int i, int8_t rawX) const
{
	if (rawX == 0)
	{
		return 0;
	}
	const FighterState& f = s_.f[i];
	const FighterState& o = s_.f[1 - i];
	int32_t side = SignI(o.x - f.x);
	if (side == 0)
	{
		side = f.facing;
	}
	return static_cast<int8_t>((rawX * side) > 0 ? 1 : -1);
}

void Match::FaceOpponent(int i)
{
	FighterState& f = s_.f[i];
	const FighterState& o = s_.f[1 - i];
	if (o.x != f.x)
	{
		f.facing = static_cast<int8_t>(o.x > f.x ? 1 : -1);
	}
}

int32_t Match::Clamp(int i, int32_t x) const
{
	const int32_t lo = -rules_.stageHalfWidth + chars_[i].halfWidth;
	const int32_t hi = rules_.stageHalfWidth - chars_[i].halfWidth;
	return x < lo ? lo : (x > hi ? hi : x);
}

Box Match::WorldBox(int i, const Box& local) const
{
	const FighterState& f = s_.f[i];
	Box w;
	if (f.facing > 0)
	{
		w.x0 = f.x + local.x0;
		w.x1 = f.x + local.x1;
	}
	else
	{
		w.x0 = f.x - local.x1;
		w.x1 = f.x - local.x0;
	}
	w.y0 = local.y0 + f.y;
	w.y1 = local.y1 + f.y;
	return w;
}

void Match::AddMeter(int i, int32_t amount)
{
	FighterState& f = s_.f[i];
	if (f.auraFrames > 0 || amount <= 0)
	{
		return;   // Spirit Enhanced Strikes is spent while active; no gain until it ends
	}
	f.meter += amount;
	if (f.meter > rules_.meterMax)
	{
		f.meter = rules_.meterMax;
	}
}

void Match::SetPush(int i, int32_t amount, int source)
{
	FighterState& f = s_.f[i];
	f.pushRemaining = amount;
	f.pushFramesLeft = rules_.pushFrames;
	f.pushSource = static_cast<int8_t>(source);
}

bool Match::IsActionable(int player) const
{
	const FState st = s_.f[player].state;
	return st == FState::Neutral || st == FState::Guard;
}

bool Match::StrikeHittable(int i) const
{
	const FighterState& f = s_.f[i];
	switch (f.state)
	{
	case FState::Knockdown:
	case FState::Getup:
	case FState::Throwing:
	case FState::Thrown:
	case FState::Tech:
	case FState::KO:
	case FState::Win:
	case FState::Defeated:
		return false;
	case FState::Attack:
		return !chars_[i].moves[static_cast<size_t>(f.move)].invulnStrike.Contains(f.moveFrame);
	default:
		return true;
	}
}

bool Match::IsThrowable(int i) const
{
	const FighterState& f = s_.f[i];
	if (f.throwInvuln > 0 || f.hitstop > 0 || InAir(i))
	{
		return false;
	}
	if (f.state == FState::Neutral || f.state == FState::Guard || f.state == FState::Jump || f.state == FState::Landing)
	{
		return true;
	}
	if (f.state == FState::Attack)
	{
		const MoveDef& m = chars_[i].moves[static_cast<size_t>(f.move)];
		return !m.invulnThrow.Contains(f.moveFrame) && !m.airborne.Contains(f.moveFrame);
	}
	return false;
}

void Match::GetHurtboxes(int player, std::vector<Box>& out) const
{
	out.clear();
	if (!StrikeHittable(player))
	{
		return;
	}
	const FighterState& f = s_.f[player];
	bool replaced = false;
	if (f.state == FState::Attack)
	{
		const MoveDef& m = chars_[player].moves[static_cast<size_t>(f.move)];
		for (const HurtDef& h : m.hurt)
		{
			if (h.frames.Contains(f.moveFrame))
			{
				out.push_back(WorldBox(player, h.box));
				replaced = replaced || h.replaceBase;
			}
		}
	}
	if (!replaced)
	{
		out.push_back(WorldBox(player, chars_[player].hurt));
	}
}

void Match::GetHitboxes(int player, std::vector<Box>& out) const
{
	out.clear();
	const FighterState& f = s_.f[player];
	if (f.state != FState::Attack)
	{
		return;
	}
	const MoveDef& m = chars_[player].moves[static_cast<size_t>(f.move)];
	for (size_t k = 0; k < m.hits.size(); ++k)
	{
		if (m.hits[k].frames.Contains(f.moveFrame) && (f.hitMask & (1u << k)) == 0)
		{
			out.push_back(WorldBox(player, m.hits[k].box));
		}
	}
}

Box Match::GetPushbox(int player) const
{
	const FighterState& f = s_.f[player];
	const int32_t hw = chars_[player].halfWidth;
	return Box{f.x - hw, f.y, f.x + hw, f.y + chars_[player].hurt.y1};
}

void Match::EndToNeutral(int i)
{
	FighterState& f = s_.f[i];
	f.state = FState::Neutral;
	f.stateFrame = 0;
	f.move = -1;
	f.moveFrame = 0;
	f.moveDir = 0;
	f.hitMask = 0;
	f.connected = false;
	f.connectedHit = false;
	f.stun = 0;
	f.walk = 0;
	f.throwIndex = -1;
	f.throwOwner = -1;
	f.throwFrame = 0;
	f.reaction = 0;
	f.reactMove = -1;
	f.reactHit = -1;
	f.jumpFrame = 0;
	f.jumpDir = 0;
	f.airAttackUsed = false;
}

bool Match::InAir(int i) const
{
	const FighterState& f = s_.f[i];
	return f.y > 0 || f.jumpFrame > rules_.jumpSquat;
}

void Match::StartJump(int i, int8_t dir)
{
	FighterState& f = s_.f[i];
	f.state = FState::Jump;
	f.stateFrame = 1;
	f.jumpFrame = 1;
	f.jumpDir = dir;
	f.airAttackUsed = false;
	f.walk = 0;
	f.vy = 0;
	Emit(EventType::Jump, i, -1, f.x, 0, dir, 0);
}

void Match::Land(int i)
{
	FighterState& f = s_.f[i];
	const bool attacking = f.state == FState::Attack;
	const bool jumping = f.state == FState::Jump || attacking;
	f.y = 0;
	f.vy = 0;
	f.jumpFrame = 0;
	f.airAttackUsed = false;
	if (!jumping)
	{
		return;
	}
	const int32_t frames = attacking ? rules_.airAttackLanding : rules_.jumpLanding;
	EndToNeutral(i);
	Emit(EventType::Land, i, -1, f.x, 0, 0, 0);
	if (frames > 0)
	{
		f.state = FState::Landing;
		f.stateFrame = 1;
		f.stun = frames;
	}
}

void Match::Ingest(int i, const InputFrame& in)
{
	FighterState& f = s_.f[i];
	f.lastInput = in;
	if (in.pressed & BtnBlock)
	{
		// A press that did not deflect locks the timed window out for timedBlockLockout frames, so mashing
		// Block never yields deflects; a successful deflect leaves the next press eligible (strings can be read).
		const bool recent = (s_.frame - f.lastBlockPress) < rules_.timedBlockLockout;
		f.lastBlockPressTimed = !(recent && !f.lastBlockPressDeflected);
		f.lastBlockPress = s_.frame;
		f.lastBlockPressDeflected = false;
	}
	// Lowest priority first, so the newest-first buffer scan prefers throw > special > heavy > light > dodge.
	static const uint8_t order[] = {BtnDodge, BtnLight, BtnHeavy, BtnSpecial, BtnThrow};
	const int8_t dir = DirToward(i, in.x);
	for (uint8_t b : order)
	{
		if ((in.pressed & b) == 0)
		{
			continue;
		}
		if (f.bufferCount == kBufferCapacity)
		{
			for (int k = 1; k < kBufferCapacity; ++k)
			{
				f.buffer[k - 1] = f.buffer[k];
			}
			--f.bufferCount;
		}
		f.buffer[f.bufferCount++] = Buffered{b, dir, 0};
	}
}

void Match::AdvanceState(int i, bool allowActions)
{
	(void)allowActions;
	FighterState& f = s_.f[i];
	if (f.hitstop > 0)
	{
		--f.hitstop;   // frozen: no state progress and no buffer ageing
		return;
	}
	int kept = 0;
	for (int k = 0; k < f.bufferCount; ++k)
	{
		Buffered e = f.buffer[k];
		++e.age;
		if (e.age <= rules_.bufferFrames)
		{
			f.buffer[kept++] = e;
		}
	}
	f.bufferCount = static_cast<uint8_t>(kept);

	if (f.throwInvuln > 0)
	{
		--f.throwInvuln;
	}
	const bool dodging = f.state == FState::Attack && chars_[i].moves[static_cast<size_t>(f.move)].kind == MoveKind::Dodge;
	if (f.dodgeLockout > 0 && !dodging)
	{
		--f.dodgeLockout;
	}
	if (f.auraFrames > 0 && --f.auraFrames == 0)
	{
		Emit(EventType::AuraEnd, i, -1, f.x, 0, 0, 0);
	}
	++f.stateFrame;

	if (f.jumpFrame > 0)
	{
		++f.jumpFrame;
		const int64_t t = f.jumpFrame - rules_.jumpSquat;   // frames in the air so far
		const int64_t air = rules_.jumpAir;
		if (t >= air)
		{
			Land(i);
		}
		else if (t > 0)
		{
			f.y = static_cast<int32_t>((4 * static_cast<int64_t>(rules_.jumpHeight) * t * (air - t)) / (air * air));
		}
	}
	else if (f.y > 0)
	{
		f.vy += rules_.fallSpeed;
		f.y = f.y > f.vy ? f.y - f.vy : 0;
		if (f.y == 0)
		{
			f.vy = 0;
		}
	}

	switch (f.state)
	{
	case FState::Attack:
	{
		++f.moveFrame;
		const MoveDef& m = chars_[i].moves[static_cast<size_t>(f.move)];
		if (m.kind == MoveKind::Buff && f.moveFrame == m.aura.applyFrame)
		{
			f.auraFrames = m.aura.frames;
			Emit(EventType::AuraStart, i, f.move, f.x, 0, m.aura.frames, EvAura);
		}
		if (f.moveFrame > m.total)
		{
			if (m.air && f.jumpFrame > 0)
			{
				// A jump attack that finishes before touching down: back to the jump, still in the air.
				f.state = FState::Jump;
				f.move = -1;
				f.moveFrame = 0;
				f.hitMask = 0;
				f.connected = false;
				f.connectedHit = false;
				break;
			}
			if (m.kind == MoveKind::Dodge)
			{
				f.dodgeLockout = rules_.dodgeLockout;
			}
			EndToNeutral(i);
		}
		break;
	}
	case FState::Landing:
		if (--f.stun < 0)
		{
			EndToNeutral(i);
		}
		break;
	case FState::Hitstun:
	case FState::Blockstun:
		if (--f.stun < 0)
		{
			EndToNeutral(i);
			f.combo = 0;
			f.throwInvuln = rules_.stunThrowInvuln;
		}
		break;
	case FState::Tech:
		if (--f.stun < 0)
		{
			EndToNeutral(i);
		}
		break;
	case FState::Knockdown:
		if (--f.stun < 0)
		{
			f.state = FState::Getup;
			f.stateFrame = 1;
			f.stun = rules_.getupFrames;
			Emit(EventType::Getup, i, -1, f.x, 0, 0, 0);
		}
		break;
	case FState::Getup:
		if (--f.stun < 0)
		{
			EndToNeutral(i);
			f.combo = 0;
			f.throwInvuln = rules_.wakeThrowInvuln;
			FaceOpponent(i);
		}
		break;
	default:
		break;
	}
}

void Match::AdvanceThrow(int a)
{
	FighterState& t = s_.f[a];
	FighterState& v = s_.f[1 - a];
	if (t.hitstop > 0)
	{
		return;
	}
	++t.throwFrame;
	v.throwFrame = t.throwFrame;
	const ThrowDef& d = chars_[a].throws[static_cast<size_t>(t.throwIndex)];

	if (s_.phase == Phase::Fight && t.throwFrame <= rules_.throwTechWindow && v.state == FState::Thrown)
	{
		for (int k = 0; k < v.bufferCount; ++k)
		{
			if (v.buffer[k].button == BtnThrow)
			{
				BeginTech(a, 1 - a);
				return;
			}
		}
	}

	// The victim is carried at a fixed offset so both animations stay in contact.
	int32_t hold = t.x + t.facing * d.holdX;
	const int32_t clamped = Clamp(1 - a, hold);
	if (clamped != hold)
	{
		t.x = Clamp(a, t.x - (hold - clamped));
		hold = clamped;
	}
	v.x = hold;

	// RoundEnd lets an existing throw finish visually. Once a timeout result is
	// awarded, its health comparison and winner must remain final.
	if (s_.phase == Phase::Fight && t.throwFrame == d.damageFrame)
	{
		int32_t dmg = d.damage;
		v.health -= dmg;
		AddMeter(a, Pct(dmg, rules_.meterHitAttackerPct));
		AddMeter(1 - a, Pct(dmg, rules_.meterHitDefenderPct));
		if (v.health <= 0)
		{
			if (s_.mode == Mode::Training)
			{
				v.health = 1;
			}
			else
			{
				v.health = 0;
				v.throwKO = true;
			}
		}
		Emit(EventType::ThrowDamage, a, t.throwIndex, v.x, 0, dmg, v.throwKO ? EvKnockdown : 0);
	}

	if (t.throwFrame >= d.duration)
	{
		int32_t landing = t.x + t.facing * d.landX;
		const int32_t lo = -rules_.stageHalfWidth + chars_[1 - a].halfWidth;
		const int32_t hi = rules_.stageHalfWidth - chars_[1 - a].halfWidth;
		// Corner: keep the authored spacing by moving the thrower instead of pushing the victim off stage.
		if (landing < lo)
		{
			t.x = Clamp(a, t.x + (lo - landing));
			landing = lo;
		}
		else if (landing > hi)
		{
			t.x = Clamp(a, t.x - (landing - hi));
			landing = hi;
		}
		v.x = landing;
		const int16_t throwIndex = t.throwIndex;
		const bool ko = v.throwKO;
		EndToNeutral(a);
		EndToNeutral(1 - a);
		FaceOpponent(a);
		FaceOpponent(1 - a);
		if (ko)
		{
			v.state = FState::KO;
			v.stateFrame = 1;
			v.reaction = d.landsHeadToward ? 4 : 3;   // presentation: already on the floor, not falling from a hit
		}
		else
		{
			v.state = FState::Knockdown;
			v.stateFrame = 1;
			v.stun = d.victimKnockdown;
			v.reaction = d.landsHeadToward ? 4 : 3;   // presentation: already on the floor, not falling from a hit
			Emit(EventType::Knockdown, 1 - a, throwIndex, v.x, 0, d.victimKnockdown, 0);
		}
		v.throwKO = false;
	}
}

void Match::BeginTech(int thrower, int victim)
{
	const int pair[2] = {thrower, victim};
	for (int i : pair)
	{
		EndToNeutral(i);
		FighterState& f = s_.f[i];
		f.state = FState::Tech;
		f.stateFrame = 1;
		f.stun = rules_.techFrames;
		f.bufferCount = 0;
		FaceOpponent(i);
		SetPush(i, -f.facing * (rules_.techPush / 2), -1);
	}
	const FighterState& t = s_.f[thrower];
	Emit(EventType::ThrowTech, thrower, -1, (t.x + s_.f[victim].x) / 2, 120 * kUnitsPerCm, 0, 0);
}

int32_t Match::SelectMove(int i, uint8_t button, int8_t dir, bool cancel) const
{
	const CharacterDef& c = chars_[i];
	const FighterState& f = s_.f[i];
	int32_t best = -1;
	int bestScore = -1;
	const size_t count = cancel ? c.moves[static_cast<size_t>(f.move)].cancelIndices.size() : c.moves.size();
	for (size_t n = 0; n < count; ++n)
	{
		const int32_t idx = cancel ? c.moves[static_cast<size_t>(f.move)].cancelIndices[n] : static_cast<int32_t>(n);
		const MoveDef& m = c.moves[static_cast<size_t>(idx)];
		if (m.button != button || (!cancel && m.chainOnly) || m.air != InAir(i) || (m.kind == MoveKind::Throw && !rules_.grappling))
		{
			continue;
		}
		int score = 0;
		if (m.dir == DirReq::Any)
		{
			score = 0;
		}
		else if ((m.dir == DirReq::Forward && dir > 0) || (m.dir == DirReq::Back && dir < 0) || (m.dir == DirReq::Neutral && dir == 0))
		{
			score = 2;
		}
		else
		{
			continue;
		}
		if (score > bestScore)
		{
			best = idx;
			bestScore = score;
		}
	}
	if (best < 0)
	{
		return -1;
	}
	// An unaffordable or unavailable choice does nothing rather than silently substituting another move.
	const MoveDef& chosen = c.moves[static_cast<size_t>(best)];
	if (chosen.meterCost > f.meter)
	{
		return -1;
	}
	if (chosen.kind == MoveKind::Buff && f.auraFrames > 0)
	{
		return -1;
	}
	if (chosen.kind == MoveKind::Dodge && f.dodgeLockout > 0)
	{
		return -1;
	}
	return best;
}

bool Match::StartFromBuffer(int i, bool cancel)
{
	FighterState& f = s_.f[i];
	for (int k = f.bufferCount - 1; k >= 0; --k)
	{
		const Buffered e = f.buffer[k];
		const int32_t idx = SelectMove(i, e.button, e.dir, cancel);
		if (idx < 0)
		{
			continue;
		}
		// Consume this press and anything older; newer unusable presses stay buffered.
		int kept = 0;
		for (int n = k + 1; n < f.bufferCount; ++n)
		{
			f.buffer[kept++] = f.buffer[n];
		}
		f.bufferCount = static_cast<uint8_t>(kept);
		StartMove(i, idx, e.dir, cancel);
		return true;
	}
	return false;
}

void Match::StartMove(int i, int32_t moveIndex, int8_t dir, bool cancel)
{
	FighterState& f = s_.f[i];
	const MoveDef& m = chars_[i].moves[static_cast<size_t>(moveIndex)];
	f.state = FState::Attack;
	f.stateFrame = 1;
	f.move = static_cast<int16_t>(moveIndex);
	f.moveFrame = 1;
	f.moveDir = dir;
	f.hitMask = 0;
	f.connected = false;
	f.connectedHit = false;
	f.walk = 0;
	f.meter -= m.meterCost;
	if (m.air)
	{
		f.airAttackUsed = true;
	}
	Emit(EventType::MoveStart, i, moveIndex, f.x, 0, 0, cancel ? EvCancel : 0);
	if (m.kind == MoveKind::Buff && m.aura.applyFrame == 1)
	{
		f.auraFrames = m.aura.frames;
		Emit(EventType::AuraStart, i, moveIndex, f.x, 0, m.aura.frames, EvAura);
	}
}

bool Match::TryCancel(int i)
{
	FighterState& f = s_.f[i];
	const MoveDef& m = chars_[i].moves[static_cast<size_t>(f.move)];
	if (m.cancelIndices.empty() || !m.cancelFrames.Contains(f.moveFrame) || !f.connected)
	{
		return false;
	}
	const bool allowed = f.connectedHit ? m.cancelOnHit : m.cancelOnBlock;
	return allowed && StartFromBuffer(i, true);
}

void Match::TryActions(int i, const InputFrame& in)
{
	FighterState& f = s_.f[i];
	if (f.hitstop > 0)
	{
		return;
	}
	if (f.state == FState::Attack)
	{
		TryCancel(i);
		return;
	}
	if (f.state == FState::Jump)
	{
		if (InAir(i) && !f.airAttackUsed)
		{
			StartFromBuffer(i, false);
		}
		return;
	}
	if (f.state != FState::Neutral && f.state != FState::Guard)
	{
		return;
	}
	if (s_.advAttacker >= 0 && s_.advReady[i] < 0)
	{
		s_.advReady[i] = s_.frame;
	}
	FaceOpponent(i);
	if (StartFromBuffer(i, false))
	{
		return;
	}
	if (in.held & BtnBlock)
	{
		if (f.state != FState::Guard)
		{
			f.state = FState::Guard;
			f.stateFrame = 1;
		}
		f.walk = 0;
		return;
	}
	if (f.state == FState::Guard)
	{
		f.state = FState::Neutral;
		f.stateFrame = 1;
	}
	if (in.y > 0)
	{
		StartJump(i, DirToward(i, in.x));
		return;
	}
	f.walk = DirToward(i, in.x);
}

void Match::Move(bool allowCollision)
{
	(void)allowCollision;
	int32_t dx[2] = {0, 0};
	int32_t transfer[2] = {0, 0};
	for (int i = 0; i < 2; ++i)
	{
		FighterState& f = s_.f[i];
		if (f.hitstop > 0 || f.state == FState::Thrown || f.state == FState::Throwing)
		{
			continue;
		}
		int32_t vx = 0;
		if (f.state == FState::Neutral && f.walk != 0)
		{
			vx = (f.walk > 0 ? chars_[i].walkForward : -chars_[i].walkBack) * f.facing;
		}
		else if (f.state == FState::Attack)
		{
			const MoveDef& m = chars_[i].moves[static_cast<size_t>(f.move)];
			for (const TravelSeg& seg : m.travel)
			{
				if (seg.frames.Contains(f.moveFrame))
				{
					vx += seg.vx * f.facing;
				}
			}
		}
		if (f.jumpFrame > rules_.jumpSquat && (f.state == FState::Jump || f.state == FState::Attack))
		{
			// In the air the jump carries the body; a jump attack adds no travel of its own.
			vx = (f.jumpDir > 0 ? rules_.jumpForward : (f.jumpDir < 0 ? -rules_.jumpBack : 0)) * f.facing;
		}
		int32_t push = 0;
		if (f.pushFramesLeft > 0)
		{
			push = f.pushRemaining / f.pushFramesLeft;
			f.pushRemaining -= push;
			--f.pushFramesLeft;
		}
		const int32_t target = f.x + vx + push;
		const int32_t clamped = Clamp(i, target);
		// Corner pushback: what the wall absorbs from a hit or block push moves the attacker back instead.
		if (clamped != target && push != 0 && f.pushSource >= 0 && f.pushSource != i)
		{
			const int32_t absorbed = target - clamped;
			if (SignI(absorbed) == SignI(push))
			{
				transfer[f.pushSource] -= (AbsI(absorbed) < AbsI(push)) ? absorbed : push;
			}
		}
		dx[i] = clamped - f.x;
		f.x = clamped;
	}
	for (int i = 0; i < 2; ++i)
	{
		if (transfer[i] != 0)
		{
			const int32_t before = s_.f[i].x;
			s_.f[i].x = Clamp(i, before + transfer[i]);
			dx[i] += s_.f[i].x - before;
		}
	}

	// Pushboxes keep bodies apart except while a move deliberately passes through (forward roll) or a throw scripts positions.
	auto pushEnabled = [this](int i) {
		const FighterState& f = s_.f[i];
		if (f.state == FState::Thrown || f.state == FState::Throwing)
		{
			return false;
		}
		if (f.state == FState::Attack)
		{
			return !chars_[i].moves[static_cast<size_t>(f.move)].noPush.Contains(f.moveFrame);
		}
		return true;
	};
	FighterState& a = s_.f[0];
	FighterState& b = s_.f[1];
	if (pushEnabled(0) && pushEnabled(1))
	{
		const int32_t minGap = chars_[0].halfWidth + chars_[1].halfWidth;
		const int32_t dist = AbsI(a.x - b.x);
		if (dist < minGap)
		{
			int32_t side = SignI(a.x - b.x);   // -1: fighter 0 is on the left
			if (side == 0)
			{
				side = SignI((a.x - dx[0]) - (b.x - dx[1]));
			}
			if (side == 0)
			{
				side = (a.facing > 0) ? -1 : 1;
			}
			const int32_t overlap = minGap - dist;
			const int32_t pa = overlap / 2;
			const int32_t pb = overlap - pa;
			int32_t ax = a.x + side * pa;
			int32_t bx = b.x - side * pb;
			const int32_t axc = Clamp(0, ax);
			bx -= (ax - axc);
			ax = axc;
			const int32_t bxc = Clamp(1, bx);
			ax = Clamp(0, ax - (bx - bxc));
			bx = bxc;
			a.x = ax;
			b.x = bx;
		}
	}

	const int32_t dist = AbsI(a.x - b.x);
	if (dist > rules_.maxSeparation)
	{
		// The camera edge acts as a wall for whoever is retreating.
		const int32_t excess = dist - rules_.maxSeparation;
		const int32_t sideA = SignI(a.x - b.x);
		const int32_t awayA = dx[0] * sideA > 0 ? AbsI(dx[0]) : 0;
		const int32_t awayB = dx[1] * -sideA > 0 ? AbsI(dx[1]) : 0;
		int32_t takeA = excess / 2;
		if (awayA + awayB > 0)
		{
			takeA = static_cast<int32_t>((static_cast<int64_t>(excess) * awayA) / (awayA + awayB));
		}
		const int32_t takeB = excess - takeA;
		a.x -= sideA * takeA;
		b.x += sideA * takeB;
	}
}

void Match::ResolveCollisions()
{
	int strikeHit[2] = {-1, -1};
	bool throwCand[2] = {false, false};
	std::vector<Box> hurt;
	for (int a = 0; a < 2; ++a)
	{
		const FighterState& f = s_.f[a];
		const int d = 1 - a;
		if (f.state != FState::Attack || f.hitstop > 0)
		{
			continue;
		}
		const MoveDef& m = chars_[a].moves[static_cast<size_t>(f.move)];
		if (m.kind == MoveKind::Strike)
		{
			if (!StrikeHittable(d))
			{
				continue;
			}
			GetHurtboxes(d, hurt);
			for (size_t k = 0; k < m.hits.size() && strikeHit[a] < 0; ++k)
			{
				if ((f.hitMask & (1u << k)) != 0 || !m.hits[k].frames.Contains(f.moveFrame))
				{
					continue;
				}
				const Box hb = WorldBox(a, m.hits[k].box);
				for (const Box& h : hurt)
				{
					if (Overlaps(hb, h))
					{
						strikeHit[a] = static_cast<int>(k);
						break;
					}
				}
			}
		}
		else if (m.kind == MoveKind::Throw)
		{
			if ((f.hitMask & 1u) != 0 || !m.hits[0].frames.Contains(f.moveFrame) || !IsThrowable(d))
			{
				continue;
			}
			const FighterState& v = s_.f[d];
			const int32_t gap = AbsI(f.x - v.x) - chars_[a].halfWidth - chars_[d].halfWidth;
			const bool inFront = (v.x - f.x) * f.facing > 0;
			throwCand[a] = inFront && gap <= m.throwRange;
		}
	}

	// Strikes beat throws on the same frame; simultaneous throws break each other.
	const bool throwOk[2] = {throwCand[0] && strikeHit[1] < 0, throwCand[1] && strikeHit[0] < 0};
	if (throwOk[0] && throwOk[1])
	{
		s_.f[0].hitMask |= 1u;
		s_.f[1].hitMask |= 1u;
		BeginTech(0, 1);
		return;
	}
	const bool trade = strikeHit[0] >= 0 && strikeHit[1] >= 0;
	const FighterState before[2] = {s_.f[0], s_.f[1]};
	for (int a = 0; a < 2; ++a)
	{
		if (strikeHit[a] < 0)
		{
			continue;
		}
		const int d = 1 - a;
		const FighterState& atk = before[a];
		const FighterState& def = before[d];
		const MoveDef& m = chars_[a].moves[static_cast<size_t>(atk.move)];
		const HitDef& h = m.hits[static_cast<size_t>(strikeHit[a])];
		// A jump attack keeps a grounded defender in stun until its attacker has landed and recovered, so a jump-in is
		// worth the same at any height: the attacker lands, recovers (airAttackLanding if the attack is still running at
		// touchdown, jumpLanding otherwise) and then has jumpInHit/BlockAdvantage frames on the defender.
		int32_t jumpInRecovery = -1;
		if (m.air && atk.jumpFrame > rules_.jumpSquat)
		{
			const int32_t airLeft = rules_.jumpSquat + rules_.jumpAir - atk.jumpFrame;
			const int32_t attackLeft = m.total - atk.moveFrame + 1;
			jumpInRecovery = (airLeft > 0 ? airLeft : 0) + (airLeft <= attackLeft ? rules_.airAttackLanding : rules_.jumpLanding) - 1;
		}
		FighterState& fa = s_.f[a];
		FighterState& fd = s_.f[d];
		if (!trade)
		{
			fa.hitMask |= 1u << strikeHit[a];
			fa.connected = true;
		}
		const Box hb = WorldBox(a, h.box);
		const int32_t cx = atk.facing > 0 ? (hb.x1 < def.x ? hb.x1 : def.x) : (hb.x0 > def.x ? hb.x0 : def.x);
		const int32_t cy = (hb.y0 + hb.y1) / 2;
		const bool timed = def.lastBlockPressTimed && (s_.frame - def.lastBlockPress) < rules_.timedBlockWindow;
		// A held guard stops ground strikes; against a jump attack it takes a timed press (or blockstun already running)
		// unless the rules let a held Block stop jump-ins too.
		const bool guarding = def.state == FState::Blockstun ||
			(def.state == FState::Guard && (jumpInRecovery < 0 || timed || rules_.heldBlockStopsJumpIns));
		const int dirAway = atk.facing;   // defender slides in the attacker's facing direction

		if (guarding)
		{
			int32_t stun = h.blockstun;
			if (jumpInRecovery >= 0 && jumpInRecovery + rules_.jumpInBlockAdvantage > stun)
			{
				stun = jumpInRecovery + rules_.jumpInBlockAdvantage;
			}
			if (timed)
			{
				stun = stun > rules_.timedBlockStunReduction ? stun - rules_.timedBlockStunReduction : 0;
				fd.lastBlockPressDeflected = true;
			}
			const int32_t stop = h.hitstop > rules_.blockHitstopReduction ? h.hitstop - rules_.blockHitstopReduction : 0;
			int32_t chip = (m.special && !timed) ? h.chip : 0;
			if (chip > 0)
			{
				chip = chip >= fd.health ? (fd.health > 1 ? fd.health - 1 : 0) : chip;   // chip never KOs
				fd.health -= chip;
			}
			fd.state = FState::Blockstun;
			fd.stateFrame = 1;
			fd.stun = stun;
			fd.move = -1;
			fd.walk = 0;
			fd.hitstop = stop;
			fa.hitstop = stop > fa.hitstop ? stop : fa.hitstop;
			SetPush(d, dirAway * h.blockPush, a);
			AddMeter(a, rules_.meterBlockAttacker);
			AddMeter(d, timed ? rules_.meterDeflect : rules_.meterBlockDefender);
			Emit(timed ? EventType::Deflect : EventType::Block, a, atk.move, cx, cy, stun, static_cast<uint8_t>((h.heavy ? EvHeavy : 0) | (h.energy ? EvEnergy : 0)));
		}
		else
		{
			bool counter = false;
			bool punish = false;
			if (!trade && def.state == FState::Attack)
			{
				const MoveDef& dm = chars_[d].moves[static_cast<size_t>(def.move)];
				const int32_t lastActive = dm.kind == MoveKind::Dodge ? dm.invulnStrike.last : dm.LastActiveFrame();
				if (dm.kind != MoveKind::Dodge && def.moveFrame <= (lastActive > 0 ? lastActive : dm.total))
				{
					counter = dm.kind != MoveKind::Buff || def.moveFrame < dm.aura.applyFrame;
					punish = !counter;
				}
				else
				{
					punish = true;
				}
			}
			const bool airborne = def.y > 0 || def.jumpFrame > rules_.jumpSquat ||
				(def.state == FState::Attack && chars_[d].moves[static_cast<size_t>(def.move)].airborne.Contains(def.moveFrame));
			const int32_t combo = (def.state == FState::Hitstun) ? def.combo + 1 : 1;
			const size_t scaleIndex = static_cast<size_t>(combo - 1) < rules_.comboScaling.size() ? static_cast<size_t>(combo - 1) : rules_.comboScaling.size() - 1;
			int32_t dmg = Pct(h.damage, rules_.comboScaling[scaleIndex]);
			uint8_t flags = static_cast<uint8_t>((h.heavy ? EvHeavy : 0) | (h.energy ? EvEnergy : 0) | (trade ? EvTrade : 0));
			if (counter)
			{
				dmg = Pct(dmg, rules_.counterDamagePct);
				flags |= EvCounter;
			}
			if (punish)
			{
				dmg = Pct(dmg, rules_.punishDamagePct);
				flags |= EvPunish;
			}
			if (atk.auraFrames > 0)
			{
				// Spirit Enhanced Strikes is defined on Wren's buff move; the multiplier lives there.
				for (const MoveDef& bm : chars_[a].moves)
				{
					if (bm.kind == MoveKind::Buff)
					{
						dmg = Pct(dmg, bm.aura.damagePct);
						break;
					}
				}
				flags |= EvAura;
			}
			if (h.energy && def.auraFrames > 0)
			{
				for (const MoveDef& bm : chars_[d].moves)
				{
					if (bm.kind == MoveKind::Buff)
					{
						dmg = Pct(dmg, bm.aura.energyTakenPct);
						break;
					}
				}
			}
			if (h.damage > 0 && dmg < 1)
			{
				dmg = 1;
			}
			fd.health -= dmg;
			if (fd.health <= 0)
			{
				fd.health = (s_.mode == Mode::Training) ? 1 : 0;
			}
			const bool knock = h.knockdown || (counter && h.knockdownOnCounter) || airborne;
			fd.move = -1;
			fd.moveFrame = 0;
			fd.hitMask = 0;
			fd.walk = 0;
			fd.combo = combo;
			fd.comboDamage = (combo == 1 ? 0 : def.comboDamage) + dmg;
			fd.reaction = h.heavy ? 2 : 1;
			fd.reactMove = atk.move;
			fd.reactHit = static_cast<int8_t>(strikeHit[a]);
			fd.jumpFrame = 0;   // a jump ends where it is hit; a body in the air falls
			fd.jumpDir = 0;
			fd.stateFrame = 1;
			fd.pushRemaining = 0;
			fd.pushFramesLeft = 0;
			if (knock)
			{
				fd.state = FState::Knockdown;
				fd.stun = rules_.knockdownFrames;
				flags |= EvKnockdown;
			}
			else
			{
				int32_t stun = h.hitstun + (counter ? rules_.counterHitstun : 0) + (punish ? rules_.punishHitstun : 0);
				if (combo >= rules_.hitstunDecayFromHit)
				{
					stun -= rules_.hitstunDecayPerHit * (combo - rules_.hitstunDecayFromHit + 1);
					if (stun < rules_.minComboHitstun)
					{
						stun = rules_.minComboHitstun;
					}
				}
				if (jumpInRecovery >= 0 && jumpInRecovery + rules_.jumpInHitAdvantage > stun)
				{
					stun = jumpInRecovery + rules_.jumpInHitAdvantage;
				}
				fd.state = FState::Hitstun;
				fd.stun = stun;
			}
			fd.hitstop = h.hitstop > fd.hitstop ? h.hitstop : fd.hitstop;
			fa.hitstop = h.hitstop > fa.hitstop ? h.hitstop : fa.hitstop;
			if (!trade)
			{
				fa.connectedHit = true;
			}
			SetPush(d, dirAway * h.hitPush, a);
			AddMeter(a, Pct(dmg, rules_.meterHitAttackerPct));
			AddMeter(d, Pct(dmg, rules_.meterHitDefenderPct));
			Emit(EventType::Hit, a, atk.move, cx, cy, dmg, flags);
			if (knock)
			{
				Emit(EventType::Knockdown, d, atk.move, fd.x, 0, rules_.knockdownFrames, 0);
			}
		}
		// Restart the live advantage measurement from this contact.
		s_.advAttacker = static_cast<int8_t>(a);
		s_.advStartFrame = s_.frame;
		s_.advReady[0] = s_.advReady[1] = -1;
	}

	for (int a = 0; a < 2; ++a)
	{
		if (throwOk[a] && strikeHit[1 - a] < 0)
		{
			ConnectThrow(a);
		}
	}
}

void Match::ConnectThrow(int a)
{
	FighterState& t = s_.f[a];
	FighterState& v = s_.f[1 - a];
	const MoveDef& m = chars_[a].moves[static_cast<size_t>(t.move)];
	const int16_t throwIndex = static_cast<int16_t>(t.moveDir < 0 ? m.throwBackIndex : m.throwForwardIndex);
	const int32_t meter = v.meter;
	EndToNeutral(a);
	t.state = FState::Throwing;
	t.stateFrame = 1;
	t.throwIndex = throwIndex;
	t.throwOwner = static_cast<int8_t>(a);
	t.throwFrame = 0;
	t.hitMask = 1u;
	EndToNeutral(1 - a);
	v.state = FState::Thrown;
	v.stateFrame = 1;
	v.throwIndex = throwIndex;
	v.throwOwner = static_cast<int8_t>(a);
	v.throwFrame = 0;
	v.bufferCount = 0;     // only presses after the grab can escape it
	v.combo = 0;
	v.pushRemaining = 0;
	v.pushFramesLeft = 0;
	v.hitstop = 0;
	v.meter = meter;
	const ThrowDef& d = chars_[a].throws[static_cast<size_t>(throwIndex)];
	int32_t hold = t.x + t.facing * d.holdX;
	const int32_t clamped = Clamp(1 - a, hold);
	if (clamped != hold)
	{
		t.x = Clamp(a, t.x - (hold - clamped));
		hold = clamped;
	}
	v.x = hold;
	Emit(EventType::ThrowConnect, a, throwIndex, (t.x + v.x) / 2, 110 * kUnitsPerCm, 0, 0);
}

void Match::CheckRoundEnd()
{
	if (s_.mode == Mode::Training)
	{
		return;
	}
	const bool ko[2] = {s_.f[0].health <= 0 && s_.f[0].state != FState::Thrown, s_.f[1].health <= 0 && s_.f[1].state != FState::Thrown};
	if (ko[0] || ko[1])
	{
		for (int i = 0; i < 2; ++i)
		{
			if (ko[i])
			{
				FighterState& f = s_.f[i];
				f.state = FState::KO;
				f.stateFrame = 1;
				f.move = -1;
				f.stun = 0;
				Emit(EventType::KO, i, -1, f.x, 0, 0, 0);
			}
		}
		s_.phase = Phase::RoundEnd;
		s_.phaseFrame = 0;
		if (ko[0] && ko[1])
		{
			s_.roundWinner = 2;
			s_.doubleKO = true;
		}
		else
		{
			const int w = ko[0] ? 1 : 0;
			s_.roundWinner = static_cast<int8_t>(w);
			++s_.f[w].roundWins;
		}
		Emit(EventType::RoundEnd, s_.roundWinner, -1, 0, 0, s_.round, 0);
		return;
	}
	if (--s_.timer <= 0)
	{
		s_.timer = 0;
		s_.timeout = true;
		const int64_t p0 = static_cast<int64_t>(s_.f[0].health) * chars_[1].maxHealth;
		const int64_t p1 = static_cast<int64_t>(s_.f[1].health) * chars_[0].maxHealth;
		s_.roundWinner = static_cast<int8_t>(p0 > p1 ? 0 : (p1 > p0 ? 1 : 2));
		if (s_.roundWinner < 2)
		{
			++s_.f[s_.roundWinner].roundWins;
		}
		s_.phase = Phase::RoundEnd;
		s_.phaseFrame = 0;
		Emit(EventType::Timeout, s_.roundWinner, -1, 0, 0, 0, 0);
		Emit(EventType::RoundEnd, s_.roundWinner, -1, 0, 0, s_.round, 0);
	}
}

void Match::UpdateRoundEnd()
{
	if (s_.phaseFrame >= rules_.roundEndFrames / 3 && s_.roundWinner >= 0 && s_.roundWinner < 2)
	{
		FighterState& w = s_.f[s_.roundWinner];
		if (IsActionable(s_.roundWinner))
		{
			w.state = FState::Win;
			w.stateFrame = 1;
		}
		FighterState& l = s_.f[1 - s_.roundWinner];
		if (s_.timeout && IsActionable(1 - s_.roundWinner))
		{
			l.state = FState::Defeated;
			l.stateFrame = 1;
		}
	}
	if (s_.phaseFrame < rules_.roundEndFrames)
	{
		return;
	}
	const int32_t w0 = s_.f[0].roundWins;
	const int32_t w1 = s_.f[1].roundWins;
	if (w0 >= rules_.roundsToWin || w1 >= rules_.roundsToWin || s_.round >= rules_.maxRounds)
	{
		s_.phase = Phase::MatchEnd;
		s_.phaseFrame = 0;
		s_.matchWinner = static_cast<int8_t>(w0 > w1 ? 0 : (w1 > w0 ? 1 : 2));
		Emit(EventType::MatchEnd, s_.matchWinner, -1, 0, 0, 0, 0);
		return;
	}
	++s_.round;
	ResetRound();
}

void Match::TrackAdvantage()
{
	if (s_.advAttacker < 0)
	{
		return;
	}
	if (s_.advReady[0] >= 0 && s_.advReady[1] >= 0)
	{
		const int a = s_.advAttacker;
		s_.lastAdvantage = s_.advReady[1 - a] - s_.advReady[a];
		s_.lastAdvantagePlayer = static_cast<int8_t>(a);
		s_.lastAdvantageValid = true;
		s_.advAttacker = -1;
	}
}

void Match::Tick(const InputFrame inputs[2])
{
	events_.clear();
	++s_.frame;
	++s_.phaseFrame;
	switch (s_.phase)
	{
	case Phase::Intro:
		if (s_.phaseFrame == 1)
		{
			Emit(EventType::RoundIntro, -1, -1, 0, 0, s_.round, 0);
		}
		for (int i = 0; i < 2; ++i)
		{
			++s_.f[i].stateFrame;
			s_.f[i].lastInput = inputs[i];
		}
		if (s_.phaseFrame >= rules_.introFrames)
		{
			s_.phase = Phase::Fight;
			s_.phaseFrame = 0;
			Emit(EventType::Fight, -1, -1, 0, 0, s_.round, 0);
		}
		return;
	case Phase::Fight:
	{
		for (int i = 0; i < 2; ++i)
		{
			Ingest(i, inputs[i]);
		}
		for (int i = 0; i < 2; ++i)
		{
			AdvanceState(i, true);
		}
		for (int i = 0; i < 2; ++i)
		{
			if (s_.f[i].state == FState::Throwing)
			{
				AdvanceThrow(i);
			}
		}
		for (int i = 0; i < 2; ++i)
		{
			TryActions(i, inputs[i]);
		}
		Move(true);
		ResolveCollisions();
		for (int i = 0; i < 2; ++i)
		{
			if (IsActionable(i))
			{
				FaceOpponent(i);
			}
		}
		CheckRoundEnd();
		TrackAdvantage();
		if (s_.mode == Mode::Training)
		{
			// Training refills health once both fighters have been settled for a moment.
			bool settled = true;
			for (int i = 0; i < 2; ++i)
			{
				FighterState& f = s_.f[i];
				f.idleFrames = IsActionable(i) ? f.idleFrames + 1 : 0;
				settled = settled && f.idleFrames >= 45;
			}
			if (settled)
			{
				for (int i = 0; i < 2; ++i)
				{
					s_.f[i].health = chars_[i].maxHealth;
				}
			}
		}
		break;
	}
	case Phase::RoundEnd:
	{
		const InputFrame idle[2] = {};
		for (int i = 0; i < 2; ++i)
		{
			s_.f[i].lastInput = idle[i];
			s_.f[i].bufferCount = 0;
			AdvanceState(i, false);
		}
		for (int i = 0; i < 2; ++i)
		{
			if (s_.f[i].state == FState::Throwing)
			{
				AdvanceThrow(i);
			}
		}
		for (int i = 0; i < 2; ++i)
		{
			if (s_.f[i].state == FState::Neutral || s_.f[i].state == FState::Guard)
			{
				s_.f[i].walk = 0;
				s_.f[i].state = FState::Neutral;
			}
		}
		Move(false);
		UpdateRoundEnd();
		break;
	}
	case Phase::MatchEnd:
		for (int i = 0; i < 2; ++i)
		{
			if (s_.f[i].hitstop > 0)
			{
				--s_.f[i].hitstop;
			}
			++s_.f[i].stateFrame;
		}
		break;
	}
}

uint64_t HashState(const MatchState& state)
{
	uint64_t h = 1469598103934665603ULL;
	Mix(h, static_cast<int64_t>(state.phase));
	Mix(h, static_cast<int64_t>(state.mode));
	Mix(h, state.phaseFrame);
	Mix(h, state.round);
	Mix(h, state.timer);
	Mix(h, state.frame);
	Mix(h, state.roundWinner);
	Mix(h, state.matchWinner);
	Mix(h, state.timeout);
	Mix(h, state.doubleKO);
	Mix(h, state.advAttacker);
	Mix(h, state.advStartFrame);
	Mix(h, state.advReady[0]);
	Mix(h, state.advReady[1]);
	Mix(h, state.lastAdvantage);
	Mix(h, state.lastAdvantagePlayer);
	Mix(h, state.lastAdvantageValid);
	for (const FighterState& f : state.f)
	{
		Mix(h, f.x);
		Mix(h, f.facing);
		Mix(h, static_cast<int64_t>(f.state));
		Mix(h, f.stateFrame);
		Mix(h, f.walk);
		Mix(h, f.move);
		Mix(h, f.moveDir);
		Mix(h, f.moveFrame);
		Mix(h, f.hitMask);
		Mix(h, f.connected);
		Mix(h, f.connectedHit);
		Mix(h, f.stun);
		Mix(h, f.hitstop);
		Mix(h, f.pushRemaining);
		Mix(h, f.pushFramesLeft);
		Mix(h, f.pushSource);
		Mix(h, f.health);
		Mix(h, f.meter);
		Mix(h, f.combo);
		Mix(h, f.comboDamage);
		Mix(h, f.auraFrames);
		Mix(h, f.dodgeLockout);
		Mix(h, f.throwInvuln);
		Mix(h, f.throwIndex);
		Mix(h, f.throwOwner);
		Mix(h, f.throwFrame);
		Mix(h, f.throwKO);
		Mix(h, f.lastBlockPress);
		Mix(h, f.lastBlockPressTimed);
		Mix(h, f.lastBlockPressDeflected);
		Mix(h, f.roundWins);
		Mix(h, f.y);
		Mix(h, f.vy);
		Mix(h, f.jumpFrame);
		Mix(h, f.jumpDir);
		Mix(h, f.airAttackUsed);
		Mix(h, f.reaction);
		Mix(h, f.reactMove);
		Mix(h, f.reactHit);
		Mix(h, f.idleFrames);
		Mix(h, f.bufferCount);
		for (int k = 0; k < f.bufferCount; ++k)
		{
			Mix(h, f.buffer[k].button);
			Mix(h, f.buffer[k].dir);
			Mix(h, f.buffer[k].age);
		}
		Mix(h, f.lastInput.x);
		Mix(h, f.lastInput.y);
		Mix(h, f.lastInput.held);
		Mix(h, f.lastInput.pressed);
	}
	return h;
}

uint64_t Match::Hash() const
{
	return HashState(s_);
}

const char* StateName(FState state)
{
	switch (state)
	{
	case FState::Neutral: return "Neutral";
	case FState::Guard: return "Guard";
	case FState::Attack: return "Attack";
	case FState::Hitstun: return "Hitstun";
	case FState::Blockstun: return "Blockstun";
	case FState::Knockdown: return "Knockdown";
	case FState::Getup: return "Getup";
	case FState::Throwing: return "Throwing";
	case FState::Thrown: return "Thrown";
	case FState::Tech: return "Tech";
	case FState::KO: return "KO";
	case FState::Win: return "Win";
	case FState::Defeated: return "Defeated";
	case FState::Jump: return "Jump";
	case FState::Landing: return "Landing";
	}
	return "?";
}

const char* EventName(EventType type)
{
	switch (type)
	{
	case EventType::RoundIntro: return "RoundIntro";
	case EventType::Fight: return "Fight";
	case EventType::MoveStart: return "MoveStart";
	case EventType::Hit: return "Hit";
	case EventType::Block: return "Block";
	case EventType::Deflect: return "Deflect";
	case EventType::ThrowConnect: return "ThrowConnect";
	case EventType::ThrowTech: return "ThrowTech";
	case EventType::ThrowDamage: return "ThrowDamage";
	case EventType::Knockdown: return "Knockdown";
	case EventType::Getup: return "Getup";
	case EventType::AuraStart: return "AuraStart";
	case EventType::AuraEnd: return "AuraEnd";
	case EventType::KO: return "KO";
	case EventType::Timeout: return "Timeout";
	case EventType::RoundEnd: return "RoundEnd";
	case EventType::MatchEnd: return "MatchEnd";
	case EventType::Jump: return "Jump";
	case EventType::Land: return "Land";
	}
	return "?";
}
}
