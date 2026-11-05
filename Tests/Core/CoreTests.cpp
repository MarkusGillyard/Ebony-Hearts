// Behavioural tests for the engine-independent combat core. Build and run with Tests/Core/run_core_tests.sh.
// Every test drives the simulation only through InputFrames, exactly as players and the CPU do.
#include "EHAI.h"
#include "EHClock.h"
#include "EHCombatData.h"
#include "EHJson.h"
#include "EHMatch.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

using namespace eh;

namespace
{
int g_failures = 0;
int g_checks = 0;
std::string g_current;

#define EXPECT_TRUE(cond, msg)                                                                         \
	do                                                                                                 \
	{                                                                                                  \
		++g_checks;                                                                                    \
		if (!(cond))                                                                                   \
		{                                                                                              \
			++g_failures;                                                                              \
			std::printf("  FAIL [%s] %s:%d: %s\n", g_current.c_str(), __FILE__, __LINE__, std::string(msg).c_str()); \
		}                                                                                              \
	} while (0)
#define EXPECT_EQ(a, b, msg) EXPECT_TRUE((a) == (b), std::string(msg) + " (got " + std::to_string(a) + ", expected " + std::to_string(b) + ")")

std::string g_dataDir;
Rules g_rules;
CharacterDef g_wren;
CharacterDef g_ashka;

std::string ReadFile(const std::string& path)
{
	std::ifstream in(path, std::ios::binary);
	std::stringstream ss;
	ss << in.rdbuf();
	return ss.str();
}

const CharacterDef& Fighter(int id) { return id == 0 ? g_wren : g_ashka; }
const char* FighterName(int id) { return id == 0 ? "wren" : "ashka"; }

InputFrame In(int8_t x = 0, uint8_t pressed = 0, uint8_t held = 0)
{
	InputFrame f;
	f.x = x;
	f.pressed = pressed;
	f.held = static_cast<uint8_t>(held | pressed);
	return f;
}

InputFrame Up(int8_t x = 0, uint8_t pressed = 0, uint8_t held = 0)
{
	InputFrame f = In(x, pressed, held);
	f.y = 1;
	return f;
}

Match MakeMatch(int c0, int c1, Mode mode = Mode::Training)
{
	Match m;
	std::string err;
	if (!m.Setup(g_rules, Fighter(c0), Fighter(c1), mode, err))
	{
		std::printf("setup failed: %s\n", err.c_str());
		std::exit(2);
	}
	return m;
}

void Step(Match& m, InputFrame p0 = InputFrame(), InputFrame p1 = InputFrame())
{
	const InputFrame in[2] = {p0, p1};
	m.Tick(in);
}

void Idle(Match& m, int ticks)
{
	for (int i = 0; i < ticks; ++i)
	{
		Step(m);
	}
}

bool HasEvent(const Match& m, EventType t, int player = -2)
{
	for (const Event& e : m.Events())
	{
		if (e.type == t && (player == -2 || e.player == player))
		{
			return true;
		}
	}
	return false;
}

int32_t Cm(double cm) { return static_cast<int32_t>(cm * kUnitsPerCm); }

// Raw x that points toward/away from the opponent for a fighter.
int8_t Toward(const Match& m, int p)
{
	return static_cast<int8_t>(m.State().f[1 - p].x > m.State().f[p].x ? 1 : -1);
}

int32_t Move(int c, const char* id) { return Fighter(c).FindMove(id); }

void Run(const char* name, const std::function<void()>& fn)
{
	g_current = name;
	const int before = g_failures;
	fn();
	std::printf("%s %s\n", g_failures == before ? "PASS" : "FAIL", name);
}

std::string LoadError(const std::string& text)
{
	CharacterDef c;
	std::string err;
	if (LoadCharacterText(text, c, err))
	{
		return "";
	}
	return err;
}

std::string Replace(std::string s, const std::string& from, const std::string& to)
{
	const size_t pos = s.find(from);
	if (pos == std::string::npos)
	{
		std::printf("test setup: pattern not found: %s\n", from.c_str());
		std::exit(2);
	}
	return s.replace(pos, from.size(), to);
}
}

int main(int argc, char** argv)
{
	g_dataDir = argc > 1 ? argv[1] : "Content/Data";
	std::string err;
	if (!LoadRulesText(ReadFile(g_dataDir + "/rules.json"), g_rules, err) ||
		!LoadCharacterText(ReadFile(g_dataDir + "/Fighters/wren.json"), g_wren, err) ||
		!LoadCharacterText(ReadFile(g_dataDir + "/Fighters/ashka.json"), g_ashka, err))
	{
		std::printf("FAIL data load: %s\n", err.c_str());
		return 1;
	}

	Run("data_loads_and_matches_contract", [] {
		EXPECT_EQ(static_cast<int>(g_wren.moves.size()), 13, "Wren move count");
		EXPECT_EQ(static_cast<int>(g_ashka.moves.size()), 13, "Ashka move count");
		for (int c = 0; c < 2; ++c)
		{
			for (const char* id : {"L1", "L2", "L3", "H", "FH", "S", "FS", "BS", "T", "DF", "DB"})
			{
				EXPECT_TRUE(Move(c, id) >= 0, std::string(FighterName(c)) + " has " + id);
			}
		}
		EXPECT_TRUE(g_wren.moves[static_cast<size_t>(Move(0, "BS"))].kind == MoveKind::Buff, "Wren BS is the Spirit Enhanced Strikes buff");
		EXPECT_TRUE(g_ashka.moves[static_cast<size_t>(Move(1, "S"))].hits[0].energy, "Ashka flame specials are energy");
	});

	Run("malformed_content_rejected_with_paths", [] {
		const std::string good = ReadFile(g_dataDir + "/Fighters/wren.json");
		EXPECT_TRUE(LoadError(good).empty(), "baseline loads");
		std::string e = LoadError("{\"id\": \"x\",");
		EXPECT_TRUE(e.find("JSON 1:") != std::string::npos, "parse error has a line/column: " + e);
		e = LoadError(Replace(good, "\"into\": [\"L2\", \"@special\"]", "\"into\": [\"L9\"]"));
		EXPECT_TRUE(e.find("unknown move \"L9\"") != std::string::npos && e.find("moves[0]") != std::string::npos, "unknown cancel target: " + e);
		e = LoadError(Replace(good, "\"into\": [\"L2\", \"@special\"]", "\"into\": [\"@special\"]"));
		EXPECT_TRUE(e.find("chain-only") != std::string::npos, "unreachable chain move: " + e);
		e = LoadError(Replace(good, "\"frames\": [8, 9], \"box\": [18, 128, 78, 156]", "\"frames\": [8, 40], \"box\": [18, 128, 78, 156]"));
		EXPECT_TRUE(e.find("moves[0].hits[0].frames") != std::string::npos, "hit beyond total: " + e);
		e = LoadError(Replace(good, "\"box\": [18, 128, 78, 156]", "\"box\": [78, 128, 18, 156]"));
		EXPECT_TRUE(e.find("x1 > x0") != std::string::npos, "inverted box: " + e);
		e = LoadError(Replace(good, "\"id\": \"L2\"", "\"id\": \"L1\""));
		EXPECT_TRUE(e.find("duplicate move id") != std::string::npos, "duplicate id: " + e);
		e = LoadError(Replace(good, "\"damage\": 30,", ""));
		EXPECT_TRUE(e.find("hits[0].damage: missing") != std::string::npos, "missing field: " + e);
		e = LoadError(Replace(good, "\"dir\": \"forward\", \"total\": 47", "\"dir\": \"any\", \"total\": 47"));
		EXPECT_TRUE(e.find("could never be performed") != std::string::npos, "shadowed move: " + e);
		e = LoadError(Replace(good, "\"throwBack\": \"wren_suplex\"", "\"throwBack\": \"nope\""));
		EXPECT_TRUE(e.find("unknown throw") != std::string::npos, "unknown throw: " + e);
		Rules r;
		std::string rerr;
		const std::string rules = ReadFile(g_dataDir + "/rules.json");
		EXPECT_TRUE(!LoadRulesText(Replace(rules, "[100, 100, 80, 70, 60, 50, 40]", "[100, 120]"), r, rerr) && rerr.find("comboScaling[1]") != std::string::npos, "increasing scaling rejected: " + rerr);
		EXPECT_TRUE(!LoadRulesText(Replace(rules, "\"bufferFrames\": 6", "\"bufferFrames\": 6.5"), r, rerr) && rerr.find("bufferFrames") != std::string::npos, "non-integer rejected: " + rerr);
	});

	Run("startup_matches_data_both_fighters_both_sides", [] {
		for (int c = 0; c < 2; ++c)
		{
			for (int side = 0; side < 2; ++side)
			{
				Match m = MakeMatch(side == 0 ? c : 1 - c, side == 0 ? 1 - c : c);
				const int p = side;   // attacker index
				const int32_t ax = p == 0 ? Cm(-40) : Cm(40);
				m.TrainingPlace(p == 0 ? ax : Cm(-40), p == 0 ? Cm(40) : ax);
				for (const char* id : {"L1", "H", "S"})
				{
					m.TrainingPlace(p == 0 ? Cm(-45) : Cm(-45), p == 0 ? Cm(45) : Cm(45));
					const MoveDef& md = Fighter(c).moves[static_cast<size_t>(Move(c, id))];
					const uint8_t btn = md.button;
					InputFrame press = In(0, btn);
					int hitTick = -1;
					for (int t = 1; t <= 60 && hitTick < 0; ++t)
					{
						Step(m, p == 0 ? press : InputFrame(), p == 1 ? press : InputFrame());
						press = InputFrame();
						if (HasEvent(m, EventType::Hit, p))
						{
							hitTick = t;
						}
					}
					EXPECT_EQ(hitTick, md.hits[0].frames.first, std::string(FighterName(c)) + " " + id + " connects on its first active frame, side " + std::to_string(side));
					Idle(m, 120);
				}
			}
		}
	});

	Run("block_advantage_matches_frame_formula", [] {
		for (int c = 0; c < 2; ++c)
		{
			for (const char* id : {"L1", "H", "FH"})
			{
				Match m = MakeMatch(c, 1 - c);
				m.TrainingPlace(Cm(-45), Cm(45));
				const MoveDef& md = Fighter(c).moves[static_cast<size_t>(Move(c, id))];
				Step(m, In(id[0] == 'F' ? 1 : 0, md.button), In(0, BtnBlock));
				for (int t = 0; t < 120; ++t)
				{
					Step(m, InputFrame(), In(0, 0, BtnBlock));
				}
				const HitDef& h = md.hits[0];
				const int32_t expected = h.blockstun - ((h.frames.last - h.frames.first) + (md.total - h.frames.last));
				EXPECT_TRUE(m.State().lastAdvantageValid, std::string(FighterName(c)) + " " + id + " advantage measured");
				EXPECT_EQ(m.State().lastAdvantage, expected, std::string(FighterName(c)) + " " + id + " on-block advantage");
			}
		}
	});

	Run("buffered_press_during_hitstop_chains", [] {
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-40), Cm(40));
		Step(m, In(0, BtnLight));
		bool sawHitstopPress = false;
		for (int t = 0; t < 40; ++t)
		{
			const bool inStop = m.State().f[0].hitstop > 0;
			InputFrame p0;
			if (inStop && !sawHitstopPress)
			{
				p0 = In(0, BtnLight);
				sawHitstopPress = true;
			}
			Step(m, p0);
		}
		EXPECT_TRUE(sawHitstopPress, "L1 produced hitstop");
		EXPECT_TRUE(m.State().f[1].combo >= 2 || m.State().f[1].health < g_ashka.maxHealth - 30, "press made during hitstop executed L2 as a combo");
	});

	Run("string_cancels_on_the_first_active_frame", [] {
		// The jab's follow-up starts from the jab's pose at the frame it is cancelled on (the captured string clips,
		// "L2_from_L1", start from frame 8), so the cancel frame of a buffered string must not drift: with the press
		// made during hitstop it lands on the hit frame, where the animation holds through the hitstop.
		for (int c = 0; c < 2; ++c)
		{
			Match m = MakeMatch(c, 1 - c);
			m.TrainingPlace(Cm(-40), Cm(40));
			Step(m, In(0, BtnLight));
			int cancelledAt = -1;
			int lastFrame = 1;
			for (int t = 0; t < 40 && cancelledAt < 0; ++t)
			{
				const FighterState& f = m.State().f[0];
				const InputFrame p0 = f.hitstop > 0 ? In(0, BtnLight) : InputFrame();
				lastFrame = f.moveFrame;
				const int32_t before = f.move;
				Step(m, p0);
				if (m.State().f[0].move != before && m.State().f[0].state == FState::Attack)
				{
					cancelledAt = lastFrame;
				}
			}
			const int firstActive = Fighter(c).moves[static_cast<size_t>(Move(c, "L1"))].hits.front().frames.first;
			EXPECT_EQ(cancelledAt, firstActive, std::string(FighterName(c)) + " jab cancels into the second hit on its first active frame");
		}
	});

	Run("buffer_window_bounds", [] {
		// A heavy pressed during the last bufferFrames ticks of recovery comes out on the first free frame;
		// a press older than the window is discarded.
		for (int early : {g_rules.bufferFrames - 1, g_rules.bufferFrames + 2})
		{
			Match m = MakeMatch(0, 1);
			m.TrainingPlace(Cm(-150), Cm(150));
			Step(m, In(0, BtnHeavy));
			const int total = g_wren.moves[static_cast<size_t>(Move(0, "H"))].total;
			int t = 1;
			for (; t < total - early; ++t)
			{
				Step(m);
			}
			Step(m, In(0, BtnLight));
			++t;
			int started = -1;
			for (int k = 0; k < 20 && started < 0; ++k)
			{
				Step(m);
				++t;
				if (HasEvent(m, EventType::MoveStart, 0))
				{
					started = t;
				}
			}
			if (early < g_rules.bufferFrames)
			{
				EXPECT_EQ(started, total + 1, "buffered light starts on the first actionable tick");
			}
			else
			{
				EXPECT_EQ(started, -1, "stale press outside the buffer is dropped");
			}
		}
	});

	Run("held_button_does_not_repeat", [] {
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-200), Cm(200));
		int starts = 0;
		Step(m, In(0, BtnLight));
		starts += HasEvent(m, EventType::MoveStart, 0);
		for (int t = 0; t < 90; ++t)
		{
			Step(m, In(0, 0, BtnLight));
			starts += HasEvent(m, EventType::MoveStart, 0);
		}
		EXPECT_EQ(starts, 1, "holding light performs one jab");
	});

	Run("hit_reactions_name_their_clip", [] {
		// A hit can name its defender's reaction clip (presentation): the defender records which move and hit put it
		// in hitstun, so the visual plays a hook turning the head away or a body shot folding the body.
		for (int c = 0; c < 2; ++c)
		{
			Match m = MakeMatch(c, 1 - c);
			m.TrainingPlace(Cm(-40), Cm(40));
			Step(m, In(0, BtnHeavy));
			bool hit = false;
			for (int t = 0; t < 60 && !hit; ++t)
			{
				Step(m);
				hit = HasEvent(m, EventType::Hit, 0);
			}
			const FighterState& d = m.State().f[1];
			const int32_t h = Move(c, "H");
			EXPECT_TRUE(hit && d.state == FState::Hitstun, std::string(FighterName(c)) + " heavy hits");
			EXPECT_EQ(d.reactMove, h, std::string(FighterName(c)) + " defender records the heavy");
			EXPECT_EQ(d.reactHit, 0, std::string(FighterName(c)) + " defender records the hit");
			const std::string& react = Fighter(c).moves[static_cast<size_t>(h)].hits[0].react;
			EXPECT_TRUE(react.rfind("Hit", 0) == 0, std::string(FighterName(c)) + " heavy names a reaction: " + react);
			EXPECT_TRUE(Fighter(c).moves[static_cast<size_t>(Move(c, "L1"))].hits[0].react.empty(), "a jab keeps the generic reaction");
		}
		const std::string good = ReadFile(g_dataDir + "/Fighters/wren.json");
		const std::string e = LoadError(Replace(good, "\"react\": \"HitHookR\"", "\"react\": \"Hook\""));
		EXPECT_TRUE(e.find("hits[0].react") != std::string::npos, "a reaction not named Hit<...> is rejected: " + e);
	});

	Run("jump_arc_landing_and_directions", [] {
		const Rules& r = g_rules;
		for (int c = 0; c < 2; ++c)
		{
			for (int8_t dir : {static_cast<int8_t>(0), static_cast<int8_t>(1), static_cast<int8_t>(-1)})
			{
				const std::string tag = std::string(FighterName(c)) + " jump dir " + std::to_string(dir);
				Match m = MakeMatch(c, 1 - c);
				m.TrainingPlace(Cm(-150), Cm(150));
				const int32_t x0 = m.State().f[0].x;
				Step(m, Up(dir));   // fighter 0 is on the left, so raw +x is toward the opponent
				EXPECT_TRUE(m.State().f[0].state == FState::Jump && m.State().f[0].y == 0, tag + ": the squat starts on the floor");
				int32_t top = 0;
				int air = 0, landing = 0, squat = 0;
				bool back = false;
				for (int t = 0; t < 120 && !back; ++t)
				{
					Step(m);
					const FighterState& f = m.State().f[0];
					top = f.y > top ? f.y : top;
					air += f.y > 0 ? 1 : 0;
					squat += (f.state == FState::Jump && f.y == 0) ? 1 : 0;
					landing += f.state == FState::Landing ? 1 : 0;
					back = f.state == FState::Neutral;
					EXPECT_TRUE(f.facing == 1, tag + ": keeps facing in the air");
				}
				EXPECT_TRUE(back, tag + ": lands and recovers");
				EXPECT_EQ(squat, r.jumpSquat - 1, tag + ": squat frames after the press");
				EXPECT_EQ(air, r.jumpAir - 1, tag + ": frames in the air");
				EXPECT_TRUE(top >= r.jumpHeight * 95 / 100 && top <= r.jumpHeight, tag + ": apex height " + std::to_string(top));
				EXPECT_EQ(landing, r.jumpLanding, tag + ": landing recovery");
				const int32_t dx = m.State().f[0].x - x0;
				const int32_t want = dir > 0 ? r.jumpForward * (r.jumpAir - 1) : (dir < 0 ? -r.jumpBack * (r.jumpAir - 1) : 0);
				EXPECT_EQ(dx, want, tag + ": distance travelled");
			}
		}
	});

	Run("jumps_cannot_block_or_be_thrown_and_anti_air_knocks_down", [] {
		for (int c = 0; c < 2; ++c)
		{
			const std::string tag = FighterName(c);
			Match m = MakeMatch(c, 1 - c);
			m.TrainingPlace(Cm(-45), Cm(45));
			Step(m, In(), Up());
			while (m.State().f[1].y < Cm(40))
			{
				Step(m, In(), In(0, 0, BtnBlock));
			}
			EXPECT_TRUE(m.State().f[1].state == FState::Jump, tag + ": holding block in the air does not guard");
			EXPECT_TRUE(!m.IsThrowable(1), tag + ": nobody is throwable in the air");
			Step(m, In(0, BtnLight), In(0, 0, BtnBlock));
			bool hit = false, down = false, floor = false;
			for (int t = 0; t < 120; ++t)
			{
				hit = hit || HasEvent(m, EventType::Hit, 0);
				const FighterState& d = m.State().f[1];
				down = down || (d.state == FState::Knockdown && d.y > 0);
				floor = floor || (down && d.y == 0 && (d.state == FState::Knockdown || d.state == FState::Getup));
				Step(m, In(), In(0, 0, BtnBlock));
			}
			EXPECT_TRUE(hit, tag + ": the jab catches the jump");
			EXPECT_TRUE(down, tag + ": a hit in the air knocks down");
			EXPECT_TRUE(floor, tag + ": the body falls to the floor");
		}
	});

	Run("jump_attacks_hit_block_and_land_into_recovery", [] {
		const Rules& r = g_rules;
		for (int c = 0; c < 2; ++c)
		{
			for (int blocking = 0; blocking < 2; ++blocking)
			{
				for (uint8_t button : {BtnLight, BtnHeavy})
				{
					const std::string tag = std::string(FighterName(c)) + (button == BtnLight ? " jump light" : " jump heavy") + (blocking ? " blocked" : "");
					Match m = MakeMatch(c, 1 - c);
					m.TrainingPlace(Cm(-75), Cm(75));
					const InputFrame guard = blocking ? In(0, 0, BtnBlock) : In();
					Step(m, Up(1), guard);
					int32_t lastY = 0;
					bool pressed = false, contact = false, standing = true, recovered = false, airMove = false;
					int landing = 0;
					for (int t = 0; t < 150 && !recovered; ++t)
					{
						const FighterState& a = m.State().f[0];
						const bool falling = a.y > 0 && a.y < lastY;
						lastY = a.y;
						InputFrame in;
						if (!pressed && falling && a.y < Cm(80))
						{
							in = In(0, button);
							pressed = true;
						}
						Step(m, in, guard);
						const FighterState& a2 = m.State().f[0];
						const FighterState& d = m.State().f[1];
						if (a2.state == FState::Attack)
						{
							airMove = airMove || Fighter(c).moves[static_cast<size_t>(a2.move)].air;
						}
						contact = contact || HasEvent(m, blocking ? EventType::Block : EventType::Hit, 0);
						standing = standing && d.state != FState::Knockdown && d.y == 0;
						landing += a2.state == FState::Landing ? 1 : 0;
						recovered = pressed && a2.state == FState::Neutral;
					}
					EXPECT_TRUE(airMove, tag + ": the button gives the jump attack in the air");
					EXPECT_TRUE(contact, tag + (blocking ? ": is blocked" : ": hits"));
					EXPECT_TRUE(standing, tag + ": a standing defender stays on its feet");
					EXPECT_TRUE(recovered, tag + ": the attacker lands and recovers");
					EXPECT_TRUE(landing >= r.jumpLanding, tag + ": lands into recovery (" + std::to_string(landing) + ")");
				}
			}
		}
		// On the ground the same button gives the ground move, never the jump attack.
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-150), Cm(150));
		Step(m, In(0, BtnLight));
		EXPECT_EQ(static_cast<int>(m.State().f[0].move), static_cast<int>(Move(0, "L1")), "light on the ground is the jab");
		const std::string good = ReadFile(g_dataDir + "/Fighters/wren.json");
		const std::string e = LoadError(Replace(good, "\"kind\": \"throw\", \"button\": \"throw\", \"dir\": \"any\",", "\"kind\": \"throw\", \"button\": \"throw\", \"dir\": \"any\", \"air\": true,"));
		EXPECT_TRUE(e.find("only strikes") != std::string::npos, "an air throw is rejected: " + e);
	});

	Run("duplicate_hit_prevention", [] {
		for (int c = 0; c < 2; ++c)
		{
			Match m = MakeMatch(c, 1 - c);
			m.TrainingPlace(Cm(-40), Cm(40));
			int hits = 0;
			Step(m, In(0, BtnHeavy));
			hits += HasEvent(m, EventType::Hit, 0);
			for (int t = 0; t < 60; ++t)
			{
				Step(m);
				hits += HasEvent(m, EventType::Hit, 0);
			}
			EXPECT_EQ(hits, 1, std::string(FighterName(c)) + " multi-frame active heavy hits once");
		}
	});

	Run("throw_beats_block_and_side_switch_on_back_throw", [] {
		for (int c = 0; c < 2; ++c)
		{
			for (int dir : {0, -1})
			{
				Match m = MakeMatch(c, 1 - c);
				m.TrainingPlace(Cm(-35), Cm(35));
				int8_t x = static_cast<int8_t>(dir < 0 ? -Toward(m, 0) : 0);
				Step(m, In(x, BtnThrow), In(0, BtnBlock));
				int connectTick = -1;
				for (int t = 2; t < 140; ++t)
				{
					Step(m, InputFrame(), In(0, 0, BtnBlock));
					if (HasEvent(m, EventType::ThrowConnect, 0) && connectTick < 0)
					{
						connectTick = t;
					}
				}
				EXPECT_TRUE(connectTick > 0, std::string(FighterName(c)) + " throw connects on a blocking opponent");
				EXPECT_TRUE(m.State().f[1].health < Fighter(1 - c).maxHealth || m.State().f[1].health == Fighter(1 - c).maxHealth, "health sane");
				const bool switched = m.State().f[0].x > m.State().f[1].x;
				EXPECT_TRUE(switched == (dir < 0), std::string(FighterName(c)) + (dir < 0 ? " back throw switches sides" : " forward throw keeps sides"));
				EXPECT_TRUE(m.State().f[0].facing == (m.State().f[1].x > m.State().f[0].x ? 1 : -1), "thrower faces the victim after landing");
			}
		}
	});

	Run("shoulder_throw_lands_head_toward", [] {
		// Wren's back throw lands the victim head toward her (reaction 4: the reversed lie and get-up), through the
		// knockdown and the get-up; her forward throw lands it head away (reaction 3).
		for (int dir : {-1, 0})
		{
			Match m = MakeMatch(0, 1);
			m.TrainingPlace(Cm(-35), Cm(35));
			Step(m, In(static_cast<int8_t>(dir < 0 ? -Toward(m, 0) : 0), BtnThrow));
			bool knocked = false, rose = false, kept = true;
			const uint8_t want = dir < 0 ? 4 : 3;
			for (int t = 0; t < 260; ++t)
			{
				Step(m, InputFrame());
				const FighterState& v = m.State().f[1];
				if (v.state == FState::Knockdown || v.state == FState::Getup)
				{
					knocked = knocked || v.state == FState::Knockdown;
					rose = rose || v.state == FState::Getup;
					kept = kept && v.reaction == want;
				}
			}
			EXPECT_TRUE(knocked && rose && kept, dir < 0 ? "back throw: lies and rises head toward the thrower" : "forward throw: lies and rises head away");
		}
	});

	Run("throw_ko_stays_down", [] {
		// A throw that knocks out leaves the victim lying where it landed: the presentation reads reaction 3 and keeps
		// it on the floor instead of replaying the knockout fall from standing.
		Match m = MakeMatch(0, 1, Mode::Versus);
		Idle(m, g_rules.introFrames);
		bool lying = false;
		int guard = 0;
		while (m.State().phase == Phase::Fight && guard++ < 20000)
		{
			const FighterState& w = m.State().f[0];
			const bool canAct = w.state == FState::Neutral && m.State().f[1].state == FState::Neutral;
			const int32_t gap = m.State().f[1].x - w.x;
			Step(m, canAct ? (gap > Cm(60) ? In(1, 0) : In(0, BtnThrow)) : InputFrame());
			if (m.State().f[1].state == FState::KO)
			{
				lying = m.State().f[1].reaction == 3;
			}
		}
		EXPECT_TRUE(m.State().roundWinner == 0, "throws alone win the round");
		EXPECT_TRUE(lying, "a throw KO leaves the victim lying (reaction 3)");
	});

	Run("throw_tech_window", [] {
		for (int late : {0, 1})
		{
			Match m = MakeMatch(1, 0);
			m.TrainingPlace(Cm(-35), Cm(35));
			Step(m, In(0, BtnThrow));
			int t = 0;
			while (m.State().f[1].state != FState::Thrown && t++ < 20)
			{
				Step(m);
			}
			const int wait = late ? g_rules.throwTechWindow + 1 : g_rules.throwTechWindow - 1;
			Idle(m, wait - 1);
			Step(m, InputFrame(), In(0, BtnThrow));
			bool teched = HasEvent(m, EventType::ThrowTech);
			for (int k = 0; k < 80; ++k)
			{
				Step(m);
				teched = teched || HasEvent(m, EventType::ThrowTech);
			}
			if (late)
			{
				EXPECT_TRUE(!teched && m.State().f[1].health < g_wren.maxHealth, "a press after the window does not escape");
			}
			else
			{
				EXPECT_TRUE(teched && m.State().f[1].health == g_wren.maxHealth, "a press inside the window escapes without damage");
			}
		}
	});

	Run("simultaneous_throws_tech_and_strike_beats_throw", [] {
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-35), Cm(35));
		Step(m, In(0, BtnThrow), In(0, BtnThrow));
		bool tech = false;
		for (int t = 0; t < 10; ++t)
		{
			Step(m);
			tech = tech || HasEvent(m, EventType::ThrowTech);
		}
		EXPECT_TRUE(tech, "simultaneous throws break");
		EXPECT_TRUE(m.State().f[0].health == g_wren.maxHealth && m.State().f[1].health == g_ashka.maxHealth, "nobody damaged by a double throw");

		// Ashka's jab is active on the same tick Wren's grab would connect: the jab is pressed earlier by the difference
		// in their startups.
		Match s = MakeMatch(0, 1);
		s.TrainingPlace(Cm(-35), Cm(35));
		const int jabStartup = Fighter(1).moves[static_cast<size_t>(Move(1, "L1"))].hits[0].frames.first;
		const int grabStartup = Fighter(0).moves[static_cast<size_t>(Move(0, "T"))].hits[0].frames.first;
		for (int t = 0; t < jabStartup - grabStartup; ++t)
		{
			Step(s, In(), t == 0 ? In(0, BtnLight) : In());
		}
		Step(s, In(0, BtnThrow), jabStartup == grabStartup ? In(0, BtnLight) : In());
		bool thrown = false;
		bool hit = false;
		for (int t = 0; t < 10; ++t)
		{
			Step(s);
			thrown = thrown || HasEvent(s, EventType::ThrowConnect);
			hit = hit || HasEvent(s, EventType::Hit, 1);
		}
		EXPECT_TRUE(hit && !thrown, "a strike landing on the grab's active frame wins");
	});

	Run("dodge_invulnerability_recovery_and_lockout", [] {
		for (int c = 0; c < 2; ++c)
		{
			const MoveDef& db = Fighter(c).moves[static_cast<size_t>(Move(c, "DB"))];
			// Strike timed into the invulnerable frames whiffs.
			Match m = MakeMatch(1 - c, c);
			m.TrainingPlace(Cm(-60), Cm(60));
			const MoveDef& jab = Fighter(1 - c).moves[static_cast<size_t>(Move(1 - c, "L1"))];
			const int dodgeStart = jab.hits[0].frames.first - db.invulnStrike.first;   // jab active on dodge frame invulnStrike.first
			Step(m, In(0, BtnLight), dodgeStart == 0 ? In(0, BtnDodge) : InputFrame());
			for (int t = 2; t <= 30; ++t)
			{
				Step(m, InputFrame(), t == dodgeStart + 1 ? In(0, BtnDodge) : InputFrame());
				EXPECT_TRUE(!HasEvent(m, EventType::Hit, 0), std::string(FighterName(c)) + " jab during invulnerable dodge frames whiffs");
			}
			// Mashing dodge cannot chain dodges back-to-back.
			Match n = MakeMatch(c, 1 - c);
			n.TrainingPlace(Cm(-100), Cm(200));
			int dodges = 0;
			int invulnTicks = 0;
			for (int t = 0; t < 240; ++t)
			{
				Step(n, In(0, t % 2 == 0 ? BtnDodge : 0));
				dodges += HasEvent(n, EventType::MoveStart, 0);
				const FighterState& f = n.State().f[0];
				if (f.state == FState::Attack && Fighter(c).moves[static_cast<size_t>(f.move)].invulnStrike.Contains(f.moveFrame))
				{
					++invulnTicks;
				}
			}
			const int cycle = db.total + g_rules.dodgeLockout;
			EXPECT_TRUE(dodges <= 240 / cycle + 1, std::string(FighterName(c)) + " dodge mashing is rate-limited: " + std::to_string(dodges));
			EXPECT_TRUE(invulnTicks * 2 < 240, std::string(FighterName(c)) + " mashing dodge leaves the fighter vulnerable most of the time");
		}
		// Punish in recovery is labelled.
		// Ashka backs into the wall so her back roll stays in range of Wren's heavy.
		Match p = MakeMatch(0, 1);
		const int32_t wall = g_rules.stageHalfWidth - g_ashka.halfWidth;
		p.TrainingPlace(wall - Cm(90), wall);
		Step(p, InputFrame(), In(0, BtnDodge));
		const MoveDef& adb = g_ashka.moves[static_cast<size_t>(Move(1, "DB"))];
		Idle(p, adb.invulnStrike.last);
		bool punished = false;
		Step(p, In(0, BtnHeavy));
		for (int t = 0; t < 20; ++t)
		{
			for (const Event& e : p.Events())
			{
				punished = punished || (e.type == EventType::Hit && (e.flags & EvPunish));
			}
			Step(p);
		}
		EXPECT_TRUE(punished, "hitting dodge recovery is a punish");
	});

	Run("simultaneous_hits_trade", [] {
		Match m = MakeMatch(0, 0);
		m.TrainingPlace(Cm(-40), Cm(40));
		Step(m, In(0, BtnLight), In(0, BtnLight));
		bool trade = false;
		for (int t = 0; t < 10; ++t)
		{
			Step(m);
			for (const Event& e : m.Events())
			{
				trade = trade || (e.type == EventType::Hit && (e.flags & EvTrade));
			}
		}
		EXPECT_TRUE(trade, "mirror jabs on the same frame trade");
		EXPECT_EQ(m.State().f[0].health, m.State().f[1].health, "trade is symmetric");
	});

	Run("cross_up_direction_uses_side_at_press", [] {
		// Wren rolls through Ashka; a forward special pressed before the switch must still be the forward special.
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-60), Cm(30));
		Step(m, In(1, BtnDodge));   // toward the opponent: forward roll
		Idle(m, 40);
		EXPECT_TRUE(m.State().f[0].x > m.State().f[1].x, "forward roll passes through the opponent");
		EXPECT_EQ(static_cast<int>(m.State().f[0].facing), -1, "facing flips after the side switch");
		EXPECT_EQ(static_cast<int>(m.State().f[1].facing), 1, "opponent turns too");
		// Raw left is now toward the opponent: it must select the forward special.
		Step(m, In(-1, BtnSpecial));
		EXPECT_TRUE(m.State().f[0].state == FState::Attack && g_wren.moves[static_cast<size_t>(m.State().f[0].move)].id == "FS", "toward-opponent input after a switch gives the forward special");
	});

	Run("corner_throw_release_and_pushback_transfer", [] {
		Match m = MakeMatch(0, 1);
		m.TrainingResetPositions(1);   // Ashka at the right wall
		const int32_t wall = g_rules.stageHalfWidth - g_ashka.halfWidth;
		m.TrainingPlace(wall - Cm(70), wall);
		Step(m, In(0, BtnThrow));
		Idle(m, 120);
		const FighterState& w = m.State().f[0];
		const FighterState& a = m.State().f[1];
		EXPECT_TRUE(a.x <= wall && w.x < a.x, "forward throw into the corner keeps the victim on stage");
		EXPECT_TRUE(a.x - w.x >= g_wren.halfWidth + g_ashka.halfWidth, "no overlap after a corner throw");
		// Corner pushback: Ashka blocks a heavy at the wall; Wren is pushed back instead.
		Match c = MakeMatch(0, 1);
		c.TrainingPlace(wall - Cm(80), wall);
		const int32_t start = c.State().f[0].x;
		Step(c, In(0, BtnHeavy), In(0, BtnBlock));
		for (int t = 0; t < 60; ++t)
		{
			Step(c, InputFrame(), In(0, 0, BtnBlock));
		}
		EXPECT_TRUE(c.State().f[1].x == wall, "defender stays at the wall");
		EXPECT_TRUE(c.State().f[0].x < start + Cm(10), "attacker absorbs the pushback");
	});

	Run("example_combos_each_fighter", [] {
		// Documented routes: L1 > L2 > L3, L1 > L2 > forward special and L1 > forward special, both fighters.
		const char* routes[] = {" L1 L2 L3", " L1 L2 FS", " L1 FS"};
		for (int c = 0; c < 2; ++c)
		{
			for (int ender = 0; ender < 3; ++ender)
			{
				const int links = ender == 2 ? 1 : 2;
				Match m = MakeMatch(c, 1 - c);
				m.TrainingPlace(Cm(-50), Cm(50));
				int maxCombo = 0;
				int presses = 0;
				for (int t = 0; t < 90; ++t)
				{
					InputFrame p0;
					const FighterState& f = m.State().f[0];
					if (t == 0)
					{
						p0 = In(0, BtnLight);
					}
					else if (f.state == FState::Attack && f.connectedHit && f.hitstop == 1 && presses < links)
					{
						++presses;
						p0 = (presses == links && ender > 0) ? In(Toward(m, 0), BtnSpecial) : In(0, BtnLight);
					}
					Step(m, p0);
					maxCombo = m.State().f[1].combo > maxCombo ? m.State().f[1].combo : maxCombo;
				}
				EXPECT_EQ(maxCombo, links + 1, std::string(FighterName(c)) + routes[ender] + " is a " + std::to_string(links + 1) + "-hit combo");
			}
		}
	});

	Run("no_infinite_or_unbounded_combo_search", [] {
		// Random but reproducible offence against a defenceless dummy, many seeds: combos must end.
		int worst = 0;
		int worstStun = 0;
		for (int c = 0; c < 2; ++c)
		{
			for (uint32_t seed = 1; seed <= 300; ++seed)
			{
				Match m = MakeMatch(c, 1 - c);
				m.TrainingPlace(Cm(-50), Cm(50));
				m.SetMeter(0, g_rules.meterMax);
				uint32_t r = seed * 2654435761u;
				int stunRun = 0;
				for (int t = 0; t < 600; ++t)
				{
					r ^= r << 13;
					r ^= r >> 17;
					r ^= r << 5;
					static const uint8_t buttons[] = {0, 0, BtnLight, BtnHeavy, BtnSpecial, BtnThrow};
					const uint8_t b = buttons[r % 6];
					const int8_t x = static_cast<int8_t>(static_cast<int>((r >> 8) % 3) - 1);
					Step(m, In(x, b));
					const FighterState& d = m.State().f[1];
					worst = d.combo > worst ? d.combo : worst;
					stunRun = (d.state == FState::Hitstun || d.state == FState::Knockdown || d.state == FState::Getup || d.state == FState::Thrown) ? stunRun + 1 : 0;
					worstStun = stunRun > worstStun ? stunRun : worstStun;
				}
			}
		}
		EXPECT_TRUE(worst <= 5, "longest random combo " + std::to_string(worst) + " stays short");
		// About two knockdowns' worth of falling and getting up, plus the hits between.
		const int bound = 200 + 2 * g_rules.getupFrames;
		EXPECT_TRUE(worstStun < bound, "longest continuous loss of control " + std::to_string(worstStun) + " ticks is bounded (< " + std::to_string(bound) + ")");
	});

	Run("damage_scaling_and_counter_hit", [] {
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-50), Cm(50));
		std::vector<int32_t> dmg;
		int presses = 0;
		Step(m, In(0, BtnLight));
		for (int t = 0; t < 80; ++t)
		{
			for (const Event& e : m.Events())
			{
				if (e.type == EventType::Hit)
				{
					dmg.push_back(e.value);
				}
			}
			const FighterState& f = m.State().f[0];
			InputFrame p0;
			if (f.state == FState::Attack && f.connectedHit && f.hitstop == 1 && presses < 2)
			{
				++presses;
				p0 = In(0, BtnLight);
			}
			Step(m, p0);
		}
		EXPECT_EQ(static_cast<int>(dmg.size()), 3, "three hits recorded");
		if (dmg.size() == 3)
		{
			EXPECT_EQ(dmg[0], 30, "first hit unscaled");
			EXPECT_EQ(dmg[1], 36, "second hit unscaled");
			EXPECT_EQ(dmg[2], 52 * 80 / 100, "third hit scaled to 80%");
		}
		// Counter hit: Ashka's heavy startup is hit by Wren's jab.
		Match c = MakeMatch(0, 1);
		c.TrainingPlace(Cm(-45), Cm(45));
		Step(c, InputFrame(), In(0, BtnHeavy));
		Step(c, In(0, BtnLight));
		bool counter = false;
		for (int t = 0; t < 10; ++t)
		{
			Step(c);
			for (const Event& e : c.Events())
			{
				counter = counter || (e.type == EventType::Hit && e.player == 0 && (e.flags & EvCounter));
			}
		}
		EXPECT_TRUE(counter, "interrupting startup is a counter hit");
	});

	Run("spirit_enhanced_strikes_bounds", [] {
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-300), Cm(250));
		Step(m, In(-1, BtnSpecial));   // back+special without meter
		EXPECT_TRUE(m.State().f[0].state != FState::Attack, "buff needs a full gauge");
		Idle(m, 5);
		m.SetMeter(0, g_rules.meterMax);
		Step(m, In(-1, BtnSpecial));
		const MoveDef& bs = g_wren.moves[static_cast<size_t>(Move(0, "BS"))];
		EXPECT_EQ(m.State().f[0].meter, 0, "activation spends the gauge");
		Idle(m, bs.aura.applyFrame);
		EXPECT_EQ(m.State().f[0].auraFrames, bs.aura.frames - 1, "aura active with its duration");
		// Boosted jab damage while active.
		m.TrainingPlace(Cm(-40), Cm(40));
		Match ref = MakeMatch(0, 1);
		ref.TrainingPlace(Cm(-40), Cm(40));
		// TrainingPlace clears aura; re-run activation at range then walk in.
		Match a = MakeMatch(0, 1);
		a.TrainingPlace(Cm(-40), Cm(40));
		a.SetMeter(0, g_rules.meterMax);
		Step(a, In(-1, BtnSpecial));
		Idle(a, bs.total + 2);
		int32_t boosted = 0;
		Step(a, In(0, BtnLight));
		for (int t = 0; t < 10 && boosted == 0; ++t)
		{
			for (const Event& e : a.Events())
			{
				if (e.type == EventType::Hit && e.player == 0) boosted = e.value;
			}
			Step(a);
		}
		EXPECT_EQ(boosted, 30 * bs.aura.damagePct / 100, "Spirit Enhanced Strikes raises strike damage");
		// Energy damage taken is reduced: Ashka's flame elbow into an aura-active Wren.
		Match e = MakeMatch(0, 1);
		e.TrainingPlace(Cm(-60), Cm(60));
		e.SetMeter(0, g_rules.meterMax);
		Step(e, In(-1, BtnSpecial));
		Idle(e, bs.total + 2);
		Step(e, InputFrame(), In(0, BtnSpecial));
		int32_t taken = 0;
		for (int t = 0; t < 30 && taken == 0; ++t)
		{
			for (const Event& ev : e.Events())
			{
				if (ev.type == EventType::Hit && ev.player == 1) taken = ev.value;
			}
			Step(e);
		}
		EXPECT_EQ(taken, 115 * bs.aura.energyTakenPct / 100, "aura halves flame (energy) damage");
		// Cannot re-activate while active; ends after its duration.
		e.SetMeter(0, g_rules.meterMax);
		Idle(e, 80);
		Step(e, In(-1, BtnSpecial));
		EXPECT_TRUE(!(e.State().f[0].state == FState::Attack && g_wren.moves[static_cast<size_t>(e.State().f[0].move)].id == "BS"), "no stacking while active");
		Idle(e, bs.aura.frames + 10);
		EXPECT_EQ(e.State().f[0].auraFrames, 0, "aura expires");
	});

	Run("flame_burst_reversal_invulnerable_and_costly", [] {
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-45), Cm(45));
		m.SetMeter(1, 500);
		const MoveDef& fb = g_ashka.moves[static_cast<size_t>(Move(1, "BS"))];
		// Wren's jab is active on Flame Burst frame 3 (invulnerable); the burst then hits.
		Step(m, In(0, BtnLight));
		Step(m);
		Step(m, InputFrame(), In(1, BtnSpecial));   // raw +1 is away from Wren for Ashka on the right
		bool wrenHit = false;
		bool ashkaHit = false;
		for (int t = 0; t < 20; ++t)
		{
			Step(m);
			wrenHit = wrenHit || HasEvent(m, EventType::Hit, 0);
			ashkaHit = ashkaHit || HasEvent(m, EventType::Hit, 1);
		}
		EXPECT_TRUE(!wrenHit && ashkaHit, "Flame Burst passes through the jab and wins");
		EXPECT_EQ(m.State().f[1].meter < 500 ? 1 : 0, 1, "Flame Burst spends 500");
		EXPECT_TRUE(fb.invulnStrike.last < fb.total, "Flame Burst has vulnerable recovery");
	});

	Run("timed_block_and_mash_lockout", [] {
		for (int mash = 0; mash < 2; ++mash)
		{
			Match m = MakeMatch(0, 1);
			m.TrainingPlace(Cm(-45), Cm(45));
			const MoveDef& h = g_wren.moves[static_cast<size_t>(Move(0, "H"))];
			const int active = h.hits[0].frames.first;
			Step(m, In(0, BtnHeavy), InputFrame());
			bool deflect = false;
			bool block = false;
			for (int t = 2; t <= 40; ++t)
			{
				// The mash case presses once more 6 ticks earlier, well inside the lockout, whatever the kick's startup.
				const bool press = t == active - 2 || (mash && t == active - 8);
				Step(m, InputFrame(), press ? In(0, BtnBlock) : In(0, 0, BtnBlock));
				deflect = deflect || HasEvent(m, EventType::Deflect);
				block = block || HasEvent(m, EventType::Block);
			}
			if (mash)
			{
				EXPECT_TRUE(block && !deflect, "a re-press inside the lockout is an ordinary block");
			}
			else
			{
				EXPECT_TRUE(deflect, "a fresh press just before the hit deflects");
			}
		}
	});

		Run("ko_timeout_draw_and_double_ko", [] {
		// KO ends the round and awards it.
		Match m = MakeMatch(0, 1, Mode::Versus);
		Idle(m, g_rules.introFrames);
		EXPECT_TRUE(m.State().phase == Phase::Fight, "intro then fight");
		int guard = 0;
		while (m.State().phase == Phase::Fight && guard++ < 20000)
		{
			const FighterState& w = m.State().f[0];
			const bool canAct = w.state == FState::Neutral;
			const int32_t gap = m.State().f[1].x - w.x;
			Step(m, canAct ? (gap > Cm(90) ? In(1, 0) : In(0, BtnHeavy)) : InputFrame());
		}
		EXPECT_TRUE(m.State().phase == Phase::RoundEnd && m.State().roundWinner == 0, "Wren wins round by KO");
		EXPECT_EQ(m.State().f[0].roundWins, 1, "round awarded");
		Idle(m, g_rules.roundEndFrames);
		EXPECT_EQ(m.State().round, 2, "next round starts");
		EXPECT_EQ(m.State().f[1].health, g_ashka.maxHealth, "health restored");
		// Timeout with equal health is a draw; no round awarded.
		Match t = MakeMatch(0, 1, Mode::Versus);
		Idle(t, g_rules.introFrames + g_rules.roundFrames + 1);
		EXPECT_TRUE(t.State().timeout && t.State().roundWinner == 2, "untouched timeout is a draw");
		EXPECT_EQ(t.State().f[0].roundWins + t.State().f[1].roundWins, 0, "draw awards nothing");
		// Timeout with a lead.
		Match l = MakeMatch(0, 1, Mode::Versus);
		Idle(l, g_rules.introFrames);
		l.TrainingPlace(Cm(-45), Cm(45));
		Step(l, In(0, BtnLight));
		Idle(l, g_rules.roundFrames);
		EXPECT_TRUE(l.State().timeout && l.State().roundWinner == 0, "health lead wins on time");
		// Double KO from a lethal trade.
		Match d = MakeMatch(0, 0, Mode::Versus);
		Idle(d, g_rules.introFrames);
		d.TrainingPlace(Cm(-40), Cm(40));
		// Bring both to low health with mirrored trades.
		int g2 = 0;
		while (d.State().phase == Phase::Fight && g2++ < 5000)
		{
			const bool act = d.State().f[0].state == FState::Neutral && d.State().f[1].state == FState::Neutral;
			Step(d, act ? In(0, BtnLight) : InputFrame(), act ? In(0, BtnLight) : InputFrame());
		}
		EXPECT_TRUE(d.State().doubleKO && d.State().roundWinner == 2, "lethal trade is a double KO draw");
		// Match ends at two round wins; a fresh match resets everything.
		Match full = MakeMatch(0, 1, Mode::Versus);
		CpuController a;
		CpuController b;
		a.Setup(0, CpuLevel::Hard, 7);
		b.Setup(1, CpuLevel::Easy, 9);
		int ticks = 0;
		while (full.State().phase != Phase::MatchEnd && ticks++ < 60 * 60 * 15)
		{
			const InputFrame in[2] = {a.Decide(full), b.Decide(full)};
			full.Tick(in);
		}
		EXPECT_TRUE(full.State().phase == Phase::MatchEnd, "CPU match reaches a result");
		const int w = full.State().matchWinner;
		EXPECT_TRUE(w == 2 || full.State().f[w].roundWins >= g_rules.roundsToWin || full.State().round == g_rules.maxRounds, "winner has the rounds");
		});

		Run("timeout_freezes_throw_damage_after_result", [] {
			Rules shortRound = g_rules;
			shortRound.introFrames = 1;
			shortRound.roundFrames = 6;
			CharacterDef fragile = g_ashka;
			fragile.maxHealth = 100;
			Match m;
			std::string error;
			EXPECT_TRUE(m.Setup(shortRound, g_wren, fragile, Mode::Versus, error), "short match setup");
			Idle(m, shortRound.introFrames);
			m.TrainingPlace(Cm(-35), Cm(35));
			Step(m, In(0, BtnThrow));
			while (m.State().phase == Phase::Fight)
			{
				Step(m);
			}
			EXPECT_TRUE(m.State().timeout && m.State().roundWinner == 2, "throw pending at a tied timeout");
			const int32_t healthAtResult = m.State().f[1].health;
			bool lateDamage = false;
			for (int tick = 0; tick < 70 && m.State().phase == Phase::RoundEnd; ++tick)
			{
				Step(m);
				lateDamage = lateDamage || HasEvent(m, EventType::ThrowDamage);
			}
			EXPECT_EQ(m.State().f[1].health, healthAtResult, "health cannot change after timeout result");
			EXPECT_TRUE(!lateDamage, "no throw damage event after timeout result");
			EXPECT_EQ(m.State().f[0].roundWins + m.State().f[1].roundWins, 0, "late throw cannot change the round award");
		});

	Run("reset_clears_state", [] {
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-40), Cm(40));
		m.SetMeter(0, 1000);
		Step(m, In(-1, BtnSpecial), In(0, BtnHeavy));
		Idle(m, 7);
		m.TrainingResetPositions(0);
		for (int i = 0; i < 2; ++i)
		{
			const FighterState& f = m.State().f[i];
			EXPECT_TRUE(f.state == FState::Neutral && f.move == -1 && f.stun == 0 && f.hitstop == 0 && f.auraFrames == 0 && f.bufferCount == 0 && f.combo == 0 && f.pushFramesLeft == 0 && f.throwIndex == -1, "fighter fully reset");
			EXPECT_EQ(f.health, Fighter(i).maxHealth, "health refilled");
		}
	});

	Run("state_hash_includes_pending_inputs", [] {
		Match heavy = MakeMatch(0, 1);
		Match special = MakeMatch(0, 1);
		heavy.TrainingPlace(Cm(-40), Cm(40));
		special.TrainingPlace(Cm(-40), Cm(40));
		Step(heavy, In(0, BtnLight));
		Step(special, In(0, BtnLight));
		Step(heavy, In(0, BtnHeavy));
		Step(special, In(0, BtnSpecial));
		EXPECT_EQ(heavy.State().f[0].move, special.State().f[0].move, "same visible current move");
		EXPECT_TRUE(heavy.State().f[0].bufferCount > 0 && special.State().f[0].bufferCount > 0, "different pending inputs are buffered");
		EXPECT_TRUE(heavy.Hash() != special.Hash(), "future-affecting buffered input changes the hash");
	});

	Run("replay_determinism_and_render_rate_independence", [] {
		// Record a CPU-vs-CPU match's inputs, then replay them through clocks driven at different render rates.
		Match rec = MakeMatch(0, 1, Mode::Versus);
		CpuController a;
		CpuController b;
		a.Setup(0, CpuLevel::Normal, 11);
		b.Setup(1, CpuLevel::Hard, 12);
		std::vector<InputFrame> tape;
		for (int t = 0; t < 60 * 50; ++t)
		{
			const InputFrame in[2] = {a.Decide(rec), b.Decide(rec)};
			tape.push_back(in[0]);
			tape.push_back(in[1]);
			rec.Tick(in);
		}
		const uint64_t expected = rec.Hash();
		int jumps = 0;
		for (const InputFrame& in : tape)
		{
			jumps += in.y > 0 ? 1 : 0;
		}
		EXPECT_TRUE(jumps > 0, "the recorded match includes jumps, so the height and jump state are replayed too");
		for (int hz : {30, 60, 75, 144, 165, 240})
		{
			Match m = MakeMatch(0, 1, Mode::Versus);
			FixedStepClock clock;
			const int64_t frameNs = FixedStepClock::kNsPerSecond / hz;
			size_t cursor = 0;
			int64_t elapsed = 0;
			while (cursor < tape.size())
			{
				// Jitter the render frame time deterministically by up to +-10% to mimic real pacing.
				const int64_t jitter = ((static_cast<int64_t>(cursor) * 7919) % 21 - 10) * frameNs / 100;
				const int32_t n = clock.Advance(frameNs + jitter);
				elapsed += frameNs + jitter;
				for (int k = 0; k < n && cursor < tape.size(); ++k)
				{
					const InputFrame in[2] = {tape[cursor], tape[cursor + 1]};
					m.Tick(in);
					cursor += 2;
				}
			}
			EXPECT_TRUE(m.Hash() == expected, "replay at " + std::to_string(hz) + " Hz matches the recording");
			EXPECT_EQ(static_cast<int>(clock.DroppedTicks()), 0, "no dropped ticks at " + std::to_string(hz) + " Hz");
		}
		// Stall policy: a 1-second hitch runs at most kMaxCatchUp ticks and drops the rest.
		FixedStepClock c;
		const int32_t n = c.Advance(FixedStepClock::kNsPerSecond);
		EXPECT_EQ(n, FixedStepClock::kMaxCatchUp, "catch-up is capped");
		EXPECT_EQ(static_cast<int>(c.DroppedTicks()), 60 - FixedStepClock::kMaxCatchUp, "excess ticks are dropped and counted");
		c.Reset();
		EXPECT_EQ(c.Advance(FixedStepClock::kNsPerSecond / 120), 0, "after a pause reset there is no burst");
	});

	Run("cpu_levels_play_legal_complete_matches", [] {
		const CpuLevel levels[] = {CpuLevel::Easy, CpuLevel::Normal, CpuLevel::Hard};
		int matches = 0;
		int stuck = 0;
		int outOfBounds = 0;
		int hardWins = 0;
		int hardGames = 0;
		int jumps = 0, jumpAttacks = 0, airDowns = 0;
		for (int c0 = 0; c0 < 2; ++c0)
		{
			for (int c1 = 0; c1 < 2; ++c1)
			{
				for (int l0 = 0; l0 < 3; ++l0)
				{
					for (int l1 = 0; l1 < 3; ++l1)
					{
						Match m = MakeMatch(c0, c1, Mode::Versus);
						CpuController a;
						CpuController b;
						a.Setup(0, levels[l0], 100u + static_cast<uint32_t>(matches));
						b.Setup(1, levels[l1], 200u + static_cast<uint32_t>(matches));
						int ticks = 0;
						int sameState[2] = {0, 0};
						FState last[2] = {FState::Neutral, FState::Neutral};
						while (m.State().phase != Phase::MatchEnd && ticks++ < 60 * 60 * 20)
						{
							const InputFrame in[2] = {a.Decide(m), b.Decide(m)};
							const FighterState before[2] = {m.State().f[0], m.State().f[1]};
							m.Tick(in);
							jumps += HasEvent(m, EventType::Jump) ? 1 : 0;
							for (int i = 0; i < 2; ++i)
							{
								const FighterState& f = m.State().f[i];
								if (f.state == FState::Attack && before[i].state != FState::Attack && m.Character(i).moves[static_cast<size_t>(f.move)].air) ++jumpAttacks;
								if (f.state == FState::Knockdown && before[i].state != FState::Knockdown && f.y > 0) ++airDowns;
								const int32_t lim = g_rules.stageHalfWidth;
								if (f.x < -lim || f.x > lim) ++outOfBounds;
								sameState[i] = (f.state == last[i]) ? sameState[i] + 1 : 0;
								last[i] = f.state;
								const bool settled = f.state == FState::Neutral || f.state == FState::Guard || f.state == FState::KO || f.state == FState::Win || f.state == FState::Defeated;
								if (!settled && sameState[i] > 400) ++stuck;
							}
						}
						++matches;
						EXPECT_TRUE(m.State().phase == Phase::MatchEnd, "match completes");
						if (l0 == 2 && l1 == 0)
						{
							++hardGames;
							hardWins += m.State().matchWinner == 0;
						}
					}
				}
			}
		}
		EXPECT_EQ(stuck, 0, "no fighter stuck in a non-neutral state");
		EXPECT_EQ(outOfBounds, 0, "positions stay on stage");
		std::printf("  info: %d CPU matches; Hard beat Easy %d/%d; %d jumps, %d jump attacks, %d knocked out of the air\n", matches, hardWins, hardGames, jumps, jumpAttacks, airDowns);
		EXPECT_TRUE(jumps > 0 && jumpAttacks > 0 && airDowns > 0, "the CPU jumps in, attacks from the air and is anti-aired");
		EXPECT_TRUE(hardWins * 2 > hardGames, "Hard CPU usually beats Easy CPU");
	});

	Run("training_dummy_modes", [] {
		Match m = MakeMatch(0, 1);
		m.TrainingPlace(Cm(-45), Cm(45));
		CpuController dummy;
		dummy.Setup(1, CpuLevel::Normal, 3);
		dummy.SetDummy(DummyMode::Block);
		bool blocked = false;
		for (int t = 0; t < 60; ++t)
		{
			const InputFrame in[2] = {t == 5 ? In(0, BtnHeavy) : InputFrame(), dummy.Decide(m)};
			m.Tick(in);
			blocked = blocked || HasEvent(m, EventType::Block);
		}
		EXPECT_TRUE(blocked, "block dummy blocks");
		Match n = MakeMatch(0, 1);
		n.TrainingPlace(Cm(-35), Cm(35));
		CpuController tech;
		tech.Setup(1, CpuLevel::Normal, 3);
		tech.SetDummy(DummyMode::TechThrows);
		bool teched = false;
		for (int t = 0; t < 60; ++t)
		{
			const InputFrame in[2] = {t == 2 ? In(0, BtnThrow) : InputFrame(), tech.Decide(n)};
			n.Tick(in);
			teched = teched || HasEvent(n, EventType::ThrowTech);
		}
		EXPECT_TRUE(teched, "tech dummy escapes throws");
	});

	std::printf("\n%d checks, %d failures\n", g_checks, g_failures);
	return g_failures == 0 ? 0 : 1;
}
