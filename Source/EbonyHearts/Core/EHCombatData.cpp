#include "EHCombatData.h"

#include "EHJson.h"

#include <cmath>

namespace eh
{
int32_t MoveDef::LastActiveFrame() const
{
	int32_t last = 0;
	for (const HitDef& hit : hits)
	{
		if (hit.frames.last > last)
		{
			last = hit.frames.last;
		}
	}
	return last;
}

int32_t CharacterDef::FindMove(const std::string& moveId) const
{
	for (size_t i = 0; i < moves.size(); ++i)
	{
		if (moves[i].id == moveId)
		{
			return static_cast<int32_t>(i);
		}
	}
	return -1;
}

int32_t CharacterDef::FindThrow(const std::string& throwId) const
{
	for (size_t i = 0; i < throws.size(); ++i)
	{
		if (throws[i].id == throwId)
		{
			return static_cast<int32_t>(i);
		}
	}
	return -1;
}

namespace dataload
{
// Field readers. Each returns false with "path: reason" in error. Optional readers leave the default untouched.
struct Ctx
{
	std::string& error;
	bool Fail(const std::string& path, const std::string& reason)
	{
		error = path + ": " + reason;
		return false;
	}
};

const JsonValue* Member(const JsonValue& obj, const char* key)
{
	return obj.Find(key);
}

bool RequireObject(Ctx& ctx, const JsonValue& value, const std::string& path)
{
	return value.IsObject() ? true : ctx.Fail(path, "expected an object");
}

bool ReadInt(Ctx& ctx, const JsonValue& obj, const char* key, const std::string& path, int32_t& out, int32_t lo, int32_t hi, bool required)
{
	const JsonValue* v = Member(obj, key);
	const std::string p = path + "." + key;
	if (v == nullptr)
	{
		return required ? ctx.Fail(p, "missing required integer") : true;
	}
	if (!v->IsNumber() || std::floor(v->number) != v->number)
	{
		return ctx.Fail(p, "expected an integer");
	}
	if (v->number < lo || v->number > hi)
	{
		return ctx.Fail(p, "value " + std::to_string(static_cast<long long>(v->number)) + " outside [" + std::to_string(lo) + ", " + std::to_string(hi) + "]");
	}
	out = static_cast<int32_t>(v->number);
	return true;
}

// Distances are authored in centimetres (decimals allowed) and stored as integer units.
bool ReadCm(Ctx& ctx, const JsonValue& obj, const char* key, const std::string& path, int32_t& out, double lo, double hi, bool required)
{
	const JsonValue* v = Member(obj, key);
	const std::string p = path + "." + key;
	if (v == nullptr)
	{
		return required ? ctx.Fail(p, "missing required distance (cm)") : true;
	}
	if (!v->IsNumber())
	{
		return ctx.Fail(p, "expected a number of centimetres");
	}
	if (v->number < lo || v->number > hi)
	{
		return ctx.Fail(p, "distance outside allowed range");
	}
	out = static_cast<int32_t>(std::lround(v->number * kUnitsPerCm));
	return true;
}

bool ReadBool(Ctx& ctx, const JsonValue& obj, const char* key, const std::string& path, bool& out)
{
	const JsonValue* v = Member(obj, key);
	if (v == nullptr)
	{
		return true;
	}
	if (!v->IsBool())
	{
		return ctx.Fail(path + "." + key, "expected true or false");
	}
	out = v->boolean;
	return true;
}

bool ReadString(Ctx& ctx, const JsonValue& obj, const char* key, const std::string& path, std::string& out, bool required)
{
	const JsonValue* v = Member(obj, key);
	const std::string p = path + "." + key;
	if (v == nullptr)
	{
		return required ? ctx.Fail(p, "missing required string") : true;
	}
	if (!v->IsString() || v->text.empty())
	{
		return ctx.Fail(p, "expected a non-empty string");
	}
	out = v->text;
	return true;
}

bool ReadBoxValue(Ctx& ctx, const JsonValue& v, const std::string& p, Box& out)
{
	if (!v.IsArray() || v.items.size() != 4)
	{
		return ctx.Fail(p, "expected [x0, y0, x1, y1] in cm");
	}
	int32_t c[4];
	for (int i = 0; i < 4; ++i)
	{
		if (!v.items[static_cast<size_t>(i)].IsNumber())
		{
			return ctx.Fail(p, "box coordinates must be numbers");
		}
		const double cm = v.items[static_cast<size_t>(i)].number;
		if (std::fabs(cm) > 1000.0)
		{
			return ctx.Fail(p, "box coordinate beyond 1000 cm");
		}
		c[i] = static_cast<int32_t>(std::lround(cm * kUnitsPerCm));
	}
	out = Box{c[0], c[1], c[2], c[3]};
	return out.Valid() ? true : ctx.Fail(p, "box must have x1 > x0 and y1 > y0");
}

bool ReadBox(Ctx& ctx, const JsonValue& obj, const char* key, const std::string& path, Box& out, bool required)
{
	const JsonValue* v = Member(obj, key);
	if (v == nullptr)
	{
		return required ? ctx.Fail(path + "." + key, "missing required box") : true;
	}
	return ReadBoxValue(ctx, *v, path + "." + key, out);
}

bool ReadRange(Ctx& ctx, const JsonValue& obj, const char* key, const std::string& path, FrameRange& out, int32_t total, bool required)
{
	const JsonValue* v = Member(obj, key);
	const std::string p = path + "." + key;
	if (v == nullptr)
	{
		return required ? ctx.Fail(p, "missing required frame range") : true;
	}
	if (!v->IsArray() || v->items.size() != 2 || !v->items[0].IsNumber() || !v->items[1].IsNumber())
	{
		return ctx.Fail(p, "expected [first, last] frames");
	}
	const double a = v->items[0].number;
	const double b = v->items[1].number;
	if (std::floor(a) != a || std::floor(b) != b)
	{
		return ctx.Fail(p, "frames must be integers");
	}
	if (a < 1 || b < a || b > total)
	{
		return ctx.Fail(p, "range [" + std::to_string(static_cast<int>(a)) + ", " + std::to_string(static_cast<int>(b)) + "] must satisfy 1 <= first <= last <= total (" + std::to_string(total) + ")");
	}
	out.first = static_cast<int32_t>(a);
	out.last = static_cast<int32_t>(b);
	return true;
}

bool ParseButton(Ctx& ctx, const std::string& name, const std::string& p, uint8_t& out)
{
	if (name == "light") out = BtnLight;
	else if (name == "heavy") out = BtnHeavy;
	else if (name == "special") out = BtnSpecial;
	else if (name == "throw") out = BtnThrow;
	else if (name == "dodge") out = BtnDodge;
	else return ctx.Fail(p, "unknown button \"" + name + "\" (light, heavy, special, throw, dodge)");
	return true;
}

bool ParseDir(Ctx& ctx, const std::string& name, const std::string& p, DirReq& out)
{
	if (name == "any") out = DirReq::Any;
	else if (name == "neutral") out = DirReq::Neutral;
	else if (name == "forward") out = DirReq::Forward;
	else if (name == "back") out = DirReq::Back;
	else return ctx.Fail(p, "unknown direction \"" + name + "\" (any, neutral, forward, back)");
	return true;
}

bool ParseKind(Ctx& ctx, const std::string& name, const std::string& p, MoveKind& out)
{
	if (name == "strike") out = MoveKind::Strike;
	else if (name == "throw") out = MoveKind::Throw;
	else if (name == "buff") out = MoveKind::Buff;
	else if (name == "dodge") out = MoveKind::Dodge;
	else return ctx.Fail(p, "unknown kind \"" + name + "\" (strike, throw, buff, dodge)");
	return true;
}

bool ParseLevel(Ctx& ctx, const std::string& name, const std::string& p, HitLevel& out)
{
	if (name == "high") out = HitLevel::High;
	else if (name == "mid") out = HitLevel::Mid;
	else if (name == "low") out = HitLevel::Low;
	else if (name == "overhead") out = HitLevel::Overhead;
	else return ctx.Fail(p, "unknown level \"" + name + "\" (high, mid, low, overhead)");
	return true;
}

bool LoadHit(Ctx& ctx, const JsonValue& v, const std::string& p, int32_t total, HitDef& hit)
{
	if (!RequireObject(ctx, v, p)) return false;
	if (!ReadRange(ctx, v, "frames", p, hit.frames, total, true)) return false;
	if (!ReadBox(ctx, v, "box", p, hit.box, true)) return false;
	if (!ReadInt(ctx, v, "damage", p, hit.damage, 0, 600, true)) return false;
	if (!ReadInt(ctx, v, "chip", p, hit.chip, 0, 200, false)) return false;
	if (!ReadInt(ctx, v, "hitstun", p, hit.hitstun, 0, 120, true)) return false;
	if (!ReadInt(ctx, v, "blockstun", p, hit.blockstun, 0, 120, true)) return false;
	if (!ReadInt(ctx, v, "hitstop", p, hit.hitstop, 0, 30, true)) return false;
	if (!ReadCm(ctx, v, "hitPush", p, hit.hitPush, 0.0, 400.0, true)) return false;
	if (!ReadCm(ctx, v, "blockPush", p, hit.blockPush, 0.0, 400.0, true)) return false;
	if (!ReadBool(ctx, v, "knockdown", p, hit.knockdown)) return false;
	if (!ReadBool(ctx, v, "knockdownOnCounter", p, hit.knockdownOnCounter)) return false;
	if (!ReadBool(ctx, v, "energy", p, hit.energy)) return false;
	if (!ReadBool(ctx, v, "heavy", p, hit.heavy)) return false;
	if (!ReadBool(ctx, v, "launch", p, hit.launch)) return false;
	std::string level;
	if (!ReadString(ctx, v, "level", p, level, true) || !ParseLevel(ctx, level, p + ".level", hit.level)) return false;
	if (hit.launch && !hit.knockdown)
	{
		return ctx.Fail(p + ".launch", "a launch is a knockdown (set knockdown)");
	}
	if (!ReadString(ctx, v, "react", p, hit.react, false)) return false;
	if (!hit.react.empty() && hit.react.rfind("Hit", 0) != 0)
	{
		return ctx.Fail(p + ".react", "a reaction clip is named Hit<...> (HitHookR, HitBody, ...)");
	}
	if (!hit.knockdown && hit.hitstun < 1)
	{
		return ctx.Fail(p + ".hitstun", "a hit that does not knock down needs hitstun >= 1");
	}
	if (hit.chip > hit.damage)
	{
		return ctx.Fail(p + ".chip", "chip damage cannot exceed damage");
	}
	return true;
}

bool LoadMove(Ctx& ctx, const JsonValue& v, const std::string& p, MoveDef& m)
{
	if (!RequireObject(ctx, v, p)) return false;
	if (!ReadString(ctx, v, "id", p, m.id, true)) return false;
	if (!ReadString(ctx, v, "name", p, m.name, true)) return false;
	if (!ReadString(ctx, v, "anim", p, m.anim, true)) return false;
	std::string text;
	if (!ReadString(ctx, v, "kind", p, text, true) || !ParseKind(ctx, text, p + ".kind", m.kind)) return false;
	if (!ReadString(ctx, v, "button", p, text, true) || !ParseButton(ctx, text, p + ".button", m.button)) return false;
	text = "any";
	if (!ReadString(ctx, v, "dir", p, text, false) || !ParseDir(ctx, text, p + ".dir", m.dir)) return false;
	if (!ReadBool(ctx, v, "chainOnly", p, m.chainOnly)) return false;
	if (!ReadBool(ctx, v, "air", p, m.air)) return false;
	if (!ReadBool(ctx, v, "down", p, m.down)) return false;
	if (!ReadBool(ctx, v, "crouching", p, m.crouching)) return false;
	m.special = (m.button == BtnSpecial);
	if (m.down && m.air)
	{
		return ctx.Fail(p + ".down", "a down move is performed on the ground");
	}
	if (m.crouching && !m.down)
	{
		return ctx.Fail(p + ".crouching", "a crouching move is selected with down held (set down)");
	}
	if (!ReadInt(ctx, v, "total", p, m.total, 1, 600, true)) return false;
	if (!ReadInt(ctx, v, "meterCost", p, m.meterCost, 0, 100000, false)) return false;

	if (const JsonValue* hits = Member(v, "hits"))
	{
		if (!hits->IsArray() || hits->items.size() > 32)
		{
			return ctx.Fail(p + ".hits", "expected an array of at most 32 hits");
		}
		int32_t previousLast = 0;
		for (size_t i = 0; i < hits->items.size(); ++i)
		{
			HitDef hit;
			const std::string hp = p + ".hits[" + std::to_string(i) + "]";
			if (!LoadHit(ctx, hits->items[i], hp, m.total, hit)) return false;
			if (hit.frames.first <= previousLast)
			{
				return ctx.Fail(hp + ".frames", "hits must be in order and must not overlap");
			}
			previousLast = hit.frames.last;
			m.hits.push_back(hit);
		}
	}
	if (const JsonValue* travel = Member(v, "travel"))
	{
		if (!travel->IsArray())
		{
			return ctx.Fail(p + ".travel", "expected an array");
		}
		for (size_t i = 0; i < travel->items.size(); ++i)
		{
			TravelSeg seg;
			const std::string tp = p + ".travel[" + std::to_string(i) + "]";
			if (!RequireObject(ctx, travel->items[i], tp)) return false;
			if (!ReadRange(ctx, travel->items[i], "frames", tp, seg.frames, m.total, true)) return false;
			if (!ReadCm(ctx, travel->items[i], "vx", tp, seg.vx, -60.0, 60.0, true)) return false;
			m.travel.push_back(seg);
		}
	}
	if (const JsonValue* hurt = Member(v, "hurt"))
	{
		if (!hurt->IsArray())
		{
			return ctx.Fail(p + ".hurt", "expected an array");
		}
		for (size_t i = 0; i < hurt->items.size(); ++i)
		{
			HurtDef h;
			const std::string hp = p + ".hurt[" + std::to_string(i) + "]";
			if (!RequireObject(ctx, hurt->items[i], hp)) return false;
			if (!ReadRange(ctx, hurt->items[i], "frames", hp, h.frames, m.total, true)) return false;
			if (!ReadBox(ctx, hurt->items[i], "box", hp, h.box, true)) return false;
			if (!ReadBool(ctx, hurt->items[i], "replaceBase", hp, h.replaceBase)) return false;
			m.hurt.push_back(h);
		}
	}
	if (!ReadRange(ctx, v, "airborne", p, m.airborne, m.total, false)) return false;
	if (!ReadRange(ctx, v, "invulnStrike", p, m.invulnStrike, m.total, false)) return false;
	if (!ReadRange(ctx, v, "invulnThrow", p, m.invulnThrow, m.total, false)) return false;
	if (!ReadRange(ctx, v, "noPush", p, m.noPush, m.total, false)) return false;
	if (m.air && m.kind != MoveKind::Strike)
	{
		return ctx.Fail(p + ".air", "only strikes can be performed in the air");
	}

	if (const JsonValue* cancel = Member(v, "cancel"))
	{
		const std::string cp = p + ".cancel";
		if (!RequireObject(ctx, *cancel, cp)) return false;
		if (!ReadRange(ctx, *cancel, "frames", cp, m.cancelFrames, m.total, true)) return false;
		if (!ReadBool(ctx, *cancel, "onHit", cp, m.cancelOnHit)) return false;
		if (!ReadBool(ctx, *cancel, "onBlock", cp, m.cancelOnBlock)) return false;
		const JsonValue* into = Member(*cancel, "into");
		if (into == nullptr || !into->IsArray() || into->items.empty())
		{
			return ctx.Fail(cp + ".into", "expected a non-empty array of move ids or \"@special\"");
		}
		for (size_t i = 0; i < into->items.size(); ++i)
		{
			if (!into->items[i].IsString() || into->items[i].text.empty())
			{
				return ctx.Fail(cp + ".into[" + std::to_string(i) + "]", "expected a move id");
			}
			m.cancelInto.push_back(into->items[i].text);
		}
		if (const JsonValue* onHit = Member(*cancel, "intoOnHit"))
		{
			if (!onHit->IsArray())
			{
				return ctx.Fail(cp + ".intoOnHit", "expected an array of move ids");
			}
			for (size_t i = 0; i < onHit->items.size(); ++i)
			{
				if (!onHit->items[i].IsString() || onHit->items[i].text.empty())
				{
					return ctx.Fail(cp + ".intoOnHit[" + std::to_string(i) + "]", "expected a move id");
				}
				m.cancelIntoOnHit.push_back(onHit->items[i].text);
			}
			if (!m.cancelOnHit)
			{
				return ctx.Fail(cp + ".intoOnHit", "hit-only cancels need onHit");
			}
		}
		if (!m.cancelOnHit && !m.cancelOnBlock)
		{
			return ctx.Fail(cp, "a cancel needs onHit and/or onBlock");
		}
	}

	switch (m.kind)
	{
	case MoveKind::Strike:
		if (m.hits.empty()) return ctx.Fail(p + ".hits", "a strike needs at least one hit");
		if (m.button == BtnThrow || m.button == BtnDodge) return ctx.Fail(p + ".button", "strikes use light, heavy or special");
		break;
	case MoveKind::Throw:
		if (m.button != BtnThrow) return ctx.Fail(p + ".button", "throw moves must use the throw button");
		if (m.hits.size() != 1) return ctx.Fail(p + ".hits", "a throw needs exactly one entry describing its active grab frames");
		if (!ReadCm(ctx, v, "throwRange", p, m.throwRange, 1.0, 200.0, true)) return false;
		m.comboRange = m.throwRange;
		if (!ReadCm(ctx, v, "comboRange", p, m.comboRange, 1.0, 200.0, false)) return false;
		if (!ReadString(ctx, v, "throw", p, m.throwId, true)) return false;
		m.throwForward = m.throwId;
		m.throwBack = m.throwId;
		if (!ReadString(ctx, v, "throwForward", p, m.throwForward, false)) return false;
		if (!ReadString(ctx, v, "throwBack", p, m.throwBack, false)) return false;
		if (m.down || m.crouching) return ctx.Fail(p + ".down", "throws are not down moves");
		break;
	case MoveKind::Buff:
	{
		if (m.button != BtnSpecial) return ctx.Fail(p + ".button", "buffs use the special button");
		const JsonValue* aura = Member(v, "aura");
		const std::string ap = p + ".aura";
		if (aura == nullptr || !aura->IsObject()) return ctx.Fail(ap, "a buff needs an aura object");
		if (!ReadInt(ctx, *aura, "applyFrame", ap, m.aura.applyFrame, 1, m.total, true)) return false;
		if (!ReadInt(ctx, *aura, "frames", ap, m.aura.frames, 1, 3600, true)) return false;
		if (!ReadInt(ctx, *aura, "damagePct", ap, m.aura.damagePct, 100, 200, true)) return false;
		if (!ReadInt(ctx, *aura, "energyTakenPct", ap, m.aura.energyTakenPct, 10, 100, true)) return false;
		break;
	}
	case MoveKind::Dodge:
		if (m.button != BtnDodge) return ctx.Fail(p + ".button", "dodges use the dodge button");
		if (!m.hits.empty()) return ctx.Fail(p + ".hits", "dodges cannot hit");
		if (m.invulnStrike.Empty()) return ctx.Fail(p + ".invulnStrike", "a dodge needs strike invulnerability frames");
		if (m.invulnStrike.last >= m.total) return ctx.Fail(p + ".invulnStrike", "a dodge must end with vulnerable recovery");
		break;
	}
	if (m.button == BtnDodge && m.kind != MoveKind::Dodge)
	{
		return ctx.Fail(p + ".kind", "the dodge button only performs dodges");
	}
	if (m.kind != MoveKind::Strike && !m.cancelInto.empty())
	{
		return ctx.Fail(p + ".cancel", "only strikes can cancel");
	}
	return true;
}

bool LoadThrow(Ctx& ctx, const JsonValue& v, const std::string& p, ThrowDef& t)
{
	if (!RequireObject(ctx, v, p)) return false;
	if (!ReadString(ctx, v, "id", p, t.id, true)) return false;
	if (!ReadString(ctx, v, "name", p, t.name, true)) return false;
	if (!ReadString(ctx, v, "attackerAnim", p, t.attackerAnim, true)) return false;
	if (!ReadString(ctx, v, "victimAnim", p, t.victimAnim, true)) return false;
	if (!ReadInt(ctx, v, "duration", p, t.duration, 10, 300, true)) return false;
	if (!ReadInt(ctx, v, "damageFrame", p, t.damageFrame, 1, t.duration, true)) return false;
	if (!ReadInt(ctx, v, "damage", p, t.damage, 0, 600, true)) return false;
	if (!ReadCm(ctx, v, "holdX", p, t.holdX, 20.0, 200.0, true)) return false;
	if (!ReadCm(ctx, v, "landX", p, t.landX, -400.0, 400.0, true)) return false;
	if (!ReadInt(ctx, v, "victimKnockdown", p, t.victimKnockdown, 1, 240, true)) return false;
	if (!ReadBool(ctx, v, "landsHeadToward", p, t.landsHeadToward)) return false;
	if (t.landX > -40 * kUnitsPerCm && t.landX < 40 * kUnitsPerCm)
	{
		return ctx.Fail(p + ".landX", "landing closer than 40 cm would overlap the thrower");
	}
	return true;
}
}

bool LoadCharacter(const JsonValue& root, CharacterDef& out, std::string& error)
{
	using namespace dataload;
	Ctx ctx{error};
	out = CharacterDef();
	const std::string p = "character";
	if (!RequireObject(ctx, root, p)) return false;
	if (!ReadString(ctx, root, "id", p, out.id, true)) return false;
	if (!ReadString(ctx, root, "name", p, out.name, true)) return false;
	if (!ReadInt(ctx, root, "maxHealth", p, out.maxHealth, 1, 100000, true)) return false;
	if (!ReadCm(ctx, root, "walkForward", p, out.walkForward, 0.1, 30.0, true)) return false;
	if (!ReadCm(ctx, root, "walkBack", p, out.walkBack, 0.1, 30.0, true)) return false;
	if (!ReadCm(ctx, root, "halfWidth", p, out.halfWidth, 5.0, 80.0, true)) return false;
	if (!ReadBox(ctx, root, "hurt", p, out.hurt, true)) return false;
	if (!ReadBox(ctx, root, "crouchHurt", p, out.crouchHurt, true)) return false;
	if (out.crouchHurt.y0 != out.hurt.y0 || out.crouchHurt.y1 >= out.hurt.y1)
	{
		return ctx.Fail(p + ".crouchHurt", "a crouching hurtbox stands on the floor and is lower than the standing one");
	}

	const JsonValue* throws = root.Find("throws");
	if (throws != nullptr)
	{
		if (!throws->IsArray()) return ctx.Fail(p + ".throws", "expected an array");
		for (size_t i = 0; i < throws->items.size(); ++i)
		{
			ThrowDef t;
			if (!LoadThrow(ctx, throws->items[i], p + ".throws[" + std::to_string(i) + "]", t)) return false;
			if (out.FindThrow(t.id) >= 0) return ctx.Fail(p + ".throws[" + std::to_string(i) + "].id", "duplicate throw id \"" + t.id + "\"");
			out.throws.push_back(t);
		}
	}

	const JsonValue* moves = root.Find("moves");
	if (moves == nullptr || !moves->IsArray() || moves->items.empty())
	{
		return ctx.Fail(p + ".moves", "expected a non-empty array");
	}
	for (size_t i = 0; i < moves->items.size(); ++i)
	{
		MoveDef m;
		const std::string mp = p + ".moves[" + std::to_string(i) + "]";
		if (!LoadMove(ctx, moves->items[i], mp, m)) return false;
		if (out.FindMove(m.id) >= 0) return ctx.Fail(mp + ".id", "duplicate move id \"" + m.id + "\"");
		if (m.kind == MoveKind::Throw)
		{
			m.throwIndex = out.FindThrow(m.throwId);
			if (m.throwIndex < 0) return ctx.Fail(mp + ".throw", "unknown throw \"" + m.throwId + "\"");
			m.throwForwardIndex = out.FindThrow(m.throwForward);
			m.throwBackIndex = out.FindThrow(m.throwBack);
			if (m.throwForwardIndex < 0) return ctx.Fail(mp + ".throwForward", "unknown throw \"" + m.throwForward + "\"");
			if (m.throwBackIndex < 0) return ctx.Fail(mp + ".throwBack", "unknown throw \"" + m.throwBack + "\"");
		}
		out.moves.push_back(m);
	}

	// Resolve cancels and prove every move is reachable and unambiguous.
	std::vector<bool> reachable(out.moves.size(), false);
	for (size_t i = 0; i < out.moves.size(); ++i)
	{
		MoveDef& m = out.moves[i];
		for (const std::string& target : m.cancelInto)
		{
			if (target == "@special")
			{
				for (size_t j = 0; j < out.moves.size(); ++j)
				{
					if (out.moves[j].special && out.moves[j].kind == MoveKind::Strike && out.moves[j].air == m.air)
					{
						m.cancelIndices.push_back(static_cast<int32_t>(j));
						reachable[j] = true;
					}
				}
				continue;
			}
			const int32_t idx = out.FindMove(target);
			if (idx < 0) return ctx.Fail(p + ".moves[" + std::to_string(i) + "].cancel.into", "unknown move \"" + target + "\"");
			if (static_cast<size_t>(idx) == i) return ctx.Fail(p + ".moves[" + std::to_string(i) + "].cancel.into", "a move cannot cancel into itself");
			if (out.moves[static_cast<size_t>(idx)].kind != MoveKind::Strike) return ctx.Fail(p + ".moves[" + std::to_string(i) + "].cancel.into", "cancels may only target strikes");
			if (out.moves[static_cast<size_t>(idx)].air != m.air) return ctx.Fail(p + ".moves[" + std::to_string(i) + "].cancel.into", "a cancel stays on the ground or in the air");
			m.cancelIndices.push_back(idx);
			reachable[static_cast<size_t>(idx)] = true;
		}
		m.cancelHitOnlyFrom = m.cancelIndices.size();
		for (const std::string& target : m.cancelIntoOnHit)
		{
			const std::string cp = p + ".moves[" + std::to_string(i) + "].cancel.intoOnHit";
			const int32_t idx = out.FindMove(target);
			if (idx < 0) return ctx.Fail(cp, "unknown move \"" + target + "\"");
			if (static_cast<size_t>(idx) == i) return ctx.Fail(cp, "a move cannot cancel into itself");
			const MoveDef& t = out.moves[static_cast<size_t>(idx)];
			if (t.kind != MoveKind::Strike && t.kind != MoveKind::Throw) return ctx.Fail(cp, "hit-only cancels target strikes or the throw");
			if (t.air != m.air) return ctx.Fail(cp, "a cancel stays on the ground or in the air");
			m.cancelIndices.push_back(idx);
		}
		if (!m.chainOnly)
		{
			reachable[i] = true;
			for (size_t j = 0; j < i; ++j)
			{
				const MoveDef& other = out.moves[j];
				if (!other.chainOnly && other.air == m.air && other.down == m.down && other.button == m.button && other.dir == m.dir && other.meterCost == m.meterCost)
				{
					return ctx.Fail(p + ".moves[" + std::to_string(i) + "]", "\"" + m.id + "\" has the same button and direction as \"" + other.id + "\" and could never be performed");
				}
			}
		}
	}
	for (size_t i = 0; i < out.moves.size(); ++i)
	{
		if (!reachable[i])
		{
			return ctx.Fail(p + ".moves[" + std::to_string(i) + "]", "\"" + out.moves[i].id + "\" is chain-only but no move cancels into it");
		}
	}
	bool hasForwardDodge = false;
	bool hasBackDodge = false;
	bool hasThrow = false;
	for (const MoveDef& m : out.moves)
	{
		if (m.kind == MoveKind::Dodge && m.dir == DirReq::Forward) hasForwardDodge = true;
		if (m.kind == MoveKind::Dodge && (m.dir == DirReq::Back || m.dir == DirReq::Any)) hasBackDodge = true;
		if (m.kind == MoveKind::Throw) hasThrow = true;
	}
	if (!hasForwardDodge || !hasBackDodge) return ctx.Fail(p + ".moves", "needs a forward dodge and a back/any dodge");
	if (!hasThrow) return ctx.Fail(p + ".moves", "needs a throw");
	return true;
}

bool LoadRules(const JsonValue& root, Rules& r, std::string& error)
{
	using namespace dataload;
	Ctx ctx{error};
	r = Rules();
	const std::string p = "rules";
	if (!RequireObject(ctx, root, p)) return false;
	if (!ReadInt(ctx, root, "roundFrames", p, r.roundFrames, 600, 36000, true)) return false;
	if (!ReadInt(ctx, root, "roundsToWin", p, r.roundsToWin, 1, 5, true)) return false;
	if (!ReadInt(ctx, root, "maxRounds", p, r.maxRounds, 1, 9, true)) return false;
	if (!ReadInt(ctx, root, "introFrames", p, r.introFrames, 0, 600, true)) return false;
	if (!ReadInt(ctx, root, "roundEndFrames", p, r.roundEndFrames, 1, 600, true)) return false;
	if (!ReadCm(ctx, root, "startX", p, r.startX, 20.0, 600.0, true)) return false;
	if (!ReadCm(ctx, root, "stageHalfWidth", p, r.stageHalfWidth, 100.0, 5000.0, true)) return false;
	if (!ReadCm(ctx, root, "maxSeparation", p, r.maxSeparation, 100.0, 5000.0, true)) return false;
	if (!ReadInt(ctx, root, "bufferFrames", p, r.bufferFrames, 1, 30, true)) return false;
	if (!ReadInt(ctx, root, "pushFrames", p, r.pushFrames, 1, 30, true)) return false;
	if (!ReadInt(ctx, root, "timedBlockWindow", p, r.timedBlockWindow, 0, 20, true)) return false;
	if (!ReadInt(ctx, root, "timedBlockLockout", p, r.timedBlockLockout, 0, 120, true)) return false;
	if (!ReadInt(ctx, root, "timedBlockStunReduction", p, r.timedBlockStunReduction, 0, 30, true)) return false;
	if (!ReadInt(ctx, root, "throwTechWindow", p, r.throwTechWindow, 1, 30, true)) return false;
	if (!ReadInt(ctx, root, "techFrames", p, r.techFrames, 1, 60, true)) return false;
	if (!ReadCm(ctx, root, "techPush", p, r.techPush, 0.0, 300.0, true)) return false;
	if (!ReadInt(ctx, root, "knockdownFrames", p, r.knockdownFrames, 1, 240, true)) return false;
	if (!ReadInt(ctx, root, "getupFrames", p, r.getupFrames, 1, 120, true)) return false;
	if (!ReadInt(ctx, root, "wakeThrowInvuln", p, r.wakeThrowInvuln, 0, 60, true)) return false;
	if (!ReadInt(ctx, root, "stunThrowInvuln", p, r.stunThrowInvuln, 0, 60, true)) return false;
	if (!ReadInt(ctx, root, "dodgeLockout", p, r.dodgeLockout, 0, 120, true)) return false;
	if (!ReadInt(ctx, root, "counterHitstun", p, r.counterHitstun, 0, 30, true)) return false;
	if (!ReadInt(ctx, root, "counterDamagePct", p, r.counterDamagePct, 100, 200, true)) return false;
	if (!ReadInt(ctx, root, "punishHitstun", p, r.punishHitstun, 0, 30, true)) return false;
	if (!ReadInt(ctx, root, "punishDamagePct", p, r.punishDamagePct, 100, 200, true)) return false;
	if (!ReadInt(ctx, root, "hitstunDecayFromHit", p, r.hitstunDecayFromHit, 2, 50, true)) return false;
	if (!ReadInt(ctx, root, "hitstunDecayPerHit", p, r.hitstunDecayPerHit, 1, 30, true)) return false;
	if (!ReadInt(ctx, root, "minComboHitstun", p, r.minComboHitstun, 1, 60, true)) return false;
	if (!ReadInt(ctx, root, "meterMax", p, r.meterMax, 1, 100000, true)) return false;
	if (!ReadInt(ctx, root, "meterHitAttackerPct", p, r.meterHitAttackerPct, 0, 1000, true)) return false;
	if (!ReadInt(ctx, root, "meterHitDefenderPct", p, r.meterHitDefenderPct, 0, 1000, true)) return false;
	if (!ReadInt(ctx, root, "meterBlockAttacker", p, r.meterBlockAttacker, 0, 100000, true)) return false;
	if (!ReadInt(ctx, root, "meterBlockDefender", p, r.meterBlockDefender, 0, 100000, true)) return false;
	if (!ReadInt(ctx, root, "meterDeflect", p, r.meterDeflect, 0, 100000, true)) return false;
	if (!ReadInt(ctx, root, "blockHitstopReduction", p, r.blockHitstopReduction, 0, 20, true)) return false;
	if (!ReadInt(ctx, root, "crouchFrames", p, r.crouchFrames, 1, 10, true)) return false;
	if (!ReadInt(ctx, root, "jumpSquat", p, r.jumpSquat, 1, 15, true)) return false;
	if (!ReadInt(ctx, root, "jumpAir", p, r.jumpAir, 10, 90, true)) return false;
	if (!ReadInt(ctx, root, "jumpLanding", p, r.jumpLanding, 0, 30, true)) return false;
	if (!ReadInt(ctx, root, "airAttackLanding", p, r.airAttackLanding, 0, 30, true)) return false;
	if (!ReadCm(ctx, root, "jumpHeight", p, r.jumpHeight, 20.0, 250.0, true)) return false;
	if (!ReadCm(ctx, root, "jumpForward", p, r.jumpForward, 0.0, 15.0, true)) return false;
	if (!ReadCm(ctx, root, "jumpBack", p, r.jumpBack, 0.0, 15.0, true)) return false;
	if (!ReadCm(ctx, root, "fallSpeed", p, r.fallSpeed, 0.05, 5.0, true)) return false;
	if (!ReadBool(ctx, root, "throws", p, r.throws)) return false;
	if (!ReadInt(ctx, root, "throwEntryFrames", p, r.throwEntryFrames, 1, 20, true)) return false;
	if (!ReadBool(ctx, root, "grappling", p, r.grappling)) return false;
	for (const char* removed : {"jumpInHitAdvantage", "jumpInBlockAdvantage", "heldBlockStopsJumpIns"})
	{
		if (root.Find(removed) != nullptr)
		{
			return ctx.Fail(p + "." + removed, "no longer a rule (jump attacks are overheads; see Docs/CombatContract.md)");
		}
	}
	const JsonValue* scaling = root.Find("comboScaling");
	if (scaling == nullptr || !scaling->IsArray() || scaling->items.empty() || scaling->items.size() > 32)
	{
		return ctx.Fail(p + ".comboScaling", "expected 1-32 percentages");
	}
	for (size_t i = 0; i < scaling->items.size(); ++i)
	{
		const JsonValue& v = scaling->items[i];
		if (!v.IsNumber() || v.number < 10 || v.number > 100 || std::floor(v.number) != v.number)
		{
			return ctx.Fail(p + ".comboScaling[" + std::to_string(i) + "]", "expected an integer percentage in [10, 100]");
		}
		if (i > 0 && v.number > r.comboScaling.back())
		{
			return ctx.Fail(p + ".comboScaling[" + std::to_string(i) + "]", "scaling must not increase later in a combo");
		}
		r.comboScaling.push_back(static_cast<int32_t>(v.number));
	}
	if (r.maxSeparation >= 2 * r.stageHalfWidth) return ctx.Fail(p + ".maxSeparation", "must be smaller than the stage width");
	if (r.startX * 2 >= r.maxSeparation) return ctx.Fail(p + ".startX", "fighters would start beyond the separation limit");
	if (r.roundsToWin > r.maxRounds) return ctx.Fail(p + ".roundsToWin", "cannot exceed maxRounds");
	return true;
}

bool LoadRulesText(const std::string& text, Rules& out, std::string& error)
{
	JsonValue root;
	std::string parseError;
	if (!ParseJson(text, root, parseError))
	{
		error = "rules: JSON " + parseError;
		return false;
	}
	return LoadRules(root, out, error);
}

bool LoadCharacterText(const std::string& text, CharacterDef& out, std::string& error)
{
	JsonValue root;
	std::string parseError;
	if (!ParseJson(text, root, parseError))
	{
		error = "character: JSON " + parseError;
		return false;
	}
	return LoadCharacter(root, out, error);
}
}
