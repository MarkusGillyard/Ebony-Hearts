// Move interaction matrix: for every source move and every follow-up a fighter can do on the ground, what happens when the
// follow-up is pressed as early as possible after the source connects (on hit, and on block), measured by running the
// combat core. Writes a Markdown section to stdout. Build and run: Tools/Docs/move_matrix.sh
#include "EHCombatData.h"
#include "EHMatch.h"

#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

using namespace eh;

namespace
{
std::string Read(const std::string& p)
{
	std::ifstream in(p);
	std::stringstream ss;
	ss << in.rdbuf();
	return ss.str();
}

struct Action
{
	std::string label;
	uint8_t button = 0;
	int8_t x = 0;      // +1 toward
	int8_t y = 0;      // -1 down, +1 up
};

InputFrame Make(const Action& a, int8_t toward)
{
	InputFrame f;
	f.x = static_cast<int8_t>(a.x * toward);
	f.y = a.y;
	f.pressed = a.button;
	f.held = a.button;
	return f;
}

struct Outcome
{
	bool sourceConnected = false;
	bool followStarted = false;
	bool viaCancel = false;
	bool followConnected = false;
	bool followHit = false;
	bool comboKept = false;     // the defender never got an actionable frame between the two
	int gap = 0;                // defender's free frames before the follow-up's first contact (when not kept)
	std::string what;           // what the follow-up did when it connected
	std::string started;        // the move (or "jump") that came out
	bool afterKnockdown = false;
	int startDelay = 0;         // frames from the source's contact to the follow-up's start
	bool movement = false;      // a roll or a jump: it moves, it does not connect
};

// One trial: attacker 0 does the source (a string of presses, each made on the first tick it can be used), then
// presses the follow-up every tick until it starts. The defender stands still or guards at a height.
Outcome Trial(const Rules& r, const CharacterDef& a, const CharacterDef& d, const std::vector<Action>& source, const Action& follow,
	int defence, int32_t dist)
{
	Outcome o;
	Match m;
	std::string err;
	m.Setup(r, a, d, Mode::Training, err);
	m.TrainingPlace(-dist / 2, dist / 2);
	const int8_t toward = 1;
	size_t next = 0;
	bool followPressed = false;
	int startedTick = -1;
	int contactTick = -1;
	o.movement = follow.button == BtnDodge || follow.y > 0;
	int contacts = 0;
	int defenderFree = 0;
	bool counting = false;
	for (int t = 0; t < 240; ++t)
	{
		InputFrame in0;
		const FighterState& f0 = m.State().f[0];
		if (t == 0)
		{
			in0 = Make(source[0], toward);
			next = 1;
		}
		else if (next < source.size() && f0.state == FState::Attack && f0.connected && f0.hitstop == 1)
		{
			in0 = Make(source[next++], toward);   // string presses, made during the hitstop as players do
		}
		else if (next >= source.size() && o.sourceConnected && startedTick < 0)
		{
			in0 = Make(follow, toward);
			followPressed = true;
		}
		InputFrame in1;
		if (defence == 1) in1.held = BtnBlock;
		if (defence == 2) { in1.held = BtnBlock; in1.y = -1; }
		const InputFrame in[2] = {in0, in1};
		m.Tick(in);
		for (const Event& e : m.Events())
		{
			const bool contact = e.player == 0 && (e.type == EventType::Hit || e.type == EventType::Block || e.type == EventType::Deflect || e.type == EventType::ThrowConnect);
			if (contact)
			{
				++contacts;
			}
			if (contact && next >= source.size() && !o.sourceConnected && contacts >= static_cast<int>(source.size()))
			{
				o.sourceConnected = true;
				counting = true;
				contactTick = t;
			}
			else if (contact && startedTick >= 0 && !o.followConnected)
			{
				o.followConnected = true;
				o.followHit = e.type == EventType::Hit || e.type == EventType::ThrowConnect;
				o.what = e.type == EventType::ThrowConnect ? "throw" : (e.type == EventType::Hit ? ((e.flags & EvKnockdown) ? "knockdown" : "hit") : "blocked");
				counting = false;
			}
			if (e.type == EventType::MoveStart && e.player == 0 && followPressed && startedTick < 0)
			{
				startedTick = t;
				o.followStarted = true;
				o.viaCancel = (e.flags & EvCancel) != 0;
				o.started = a.moves[static_cast<size_t>(e.move)].id;
				o.startDelay = t - contactTick;
			}
			if (e.type == EventType::Jump && e.player == 0 && followPressed && startedTick < 0)
			{
				startedTick = t;
				o.followStarted = true;
				o.started = "jump";
				o.startDelay = t - contactTick;
			}
			if (e.type == EventType::Knockdown && e.player == 1 && o.sourceConnected && startedTick < 0)
			{
				o.afterKnockdown = true;
			}
		}
		if (counting && m.IsActionable(1))
		{
			++defenderFree;
		}
		if (o.followConnected || (startedTick >= 0 && t > startedTick + 90))
		{
			break;
		}
	}
	o.comboKept = o.followConnected && defenderFree == 0;
	o.gap = defenderFree;
	return o;
}

std::string Cell(const Outcome& o, bool onHit)
{
	if (!o.sourceConnected)
	{
		return "(source misses)";
	}
	if (!o.followStarted)
	{
		return "x";
	}
	const std::string how = o.started + (o.viaCancel ? " (cancel)" : "");
	if (o.movement)
	{
		return (o.afterKnockdown ? "knockdown first; " : "") + how + " starts " + std::to_string(o.startDelay) + " f after contact";
	}
	if (o.afterKnockdown && !o.followConnected)
	{
		return "knockdown first; " + how + " whiffs";
	}
	if (!o.followConnected)
	{
		return how + " whiffs";
	}
	if (o.comboKept && o.followHit)
	{
		return std::string("**") + (onHit ? (o.viaCancel ? "combo" : "link combo") : "frame trap") + "**: " + how + " " + o.what;
	}
	if (o.comboKept)
	{
		return std::string(onHit ? "kept: " : "blockstring: ") + how + " " + o.what;
	}
	return "gap " + std::to_string(o.gap) + ": " + how + " " + o.what;
}
}

int main(int argc, char** argv)
{
	const std::string dir = argc > 1 ? argv[1] : "Content/Data";
	Rules r;
	CharacterDef c[2];
	std::string err;
	if (!LoadRulesText(Read(dir + "/rules.json"), r, err) || !LoadCharacterText(Read(dir + "/Fighters/wren.json"), c[0], err) ||
		!LoadCharacterText(Read(dir + "/Fighters/ashka.json"), c[1], err))
	{
		std::fprintf(stderr, "load: %s\n", err.c_str());
		return 1;
	}
	const Action L{"L", BtnLight, 0, 0}, H{"H", BtnHeavy, 0, 0}, FH{"toward+H", BtnHeavy, 1, 0}, CL{"down+L", BtnLight, 0, -1},
		U{"down+H", BtnHeavy, 0, -1}, S{"S", BtnSpecial, 0, 0}, FS{"toward+S", BtnSpecial, 1, 0}, T{"Throw", BtnThrow, 0, 0},
		DF{"toward+Dodge", BtnDodge, 1, 0}, J{"Jump", 0, 1, 1}, BL{"away+L", BtnLight, -1, 0}, BH{"away+H", BtnHeavy, -1, 0};
	struct Source { std::string name; std::vector<Action> presses; };
	const std::vector<Source> sources = {{"L1", {L}}, {"L1 > L2", {L, L}}, {"L1 > L2 > L3", {L, L, L}}, {"H", {H}}, {"toward+H", {FH}},
		{"down+L (low)", {CL}}, {"down+H (uppercut)", {U}}};
	const std::vector<Action> follows = {L, H, FH, CL, U, S, FS, T, DF, J};
	std::printf("<!-- move-matrix:begin -->\n\n");
	std::printf("Generated by `Tools/Docs/move_matrix.sh` from `Content/Data` and the combat core. Each cell: the follow-up "
		"pressed on every tick from the moment the source connects until it starts, at close range (bodies 4 cm apart) "
		"against a defender who stands (on hit) or holds the guard the source needs (on block: lows crouching, the rest standing). "
		"**combo** / **link combo**: the defender never acts before the follow-up connects (cancel or link). "
		"**frame trap**: on block, the defender never acts before the follow-up hits. *gap N*: the defender had N free "
		"frames first (pressure: it can jump, roll, guard, strike or escape). *x*: not available here (no cancel, and "
		"the follow-up never started in the window). *whiffs*: started but out of reach. Rolls and jumps report when they "
		"start. The throw can only connect as a combo throw (cancelled on hit) or on an actionable opponent.\n\n");
	for (int a = 0; a < 2; ++a)
	{
		const CharacterDef& atk = c[a];
		const CharacterDef& def = c[1 - a];
		// A fighter with away moves (Ashka's front kick and spinning elbow) gets them as sources and follow-ups too.
		std::vector<Source> srcs = sources;
		std::vector<Action> fol = follows;
		for (const auto& [id, act] : {std::pair<const char*, Action>{"BL", BL}, std::pair<const char*, Action>{"BH", BH}})
		{
			if (atk.FindMove(id) >= 0)
			{
				srcs.push_back({act.label, {act}});
				fol.push_back(act);
			}
		}
		for (int block = 0; block < 2; ++block)
		{
			std::printf("#### %s vs %s, %s\n\n| Source | ", atk.name.c_str(), def.name.c_str(), block ? "on block" : "on hit");
			for (const Action& f : fol) std::printf("%s | ", f.label.c_str());
			std::printf("\n|---|");
			for (size_t k = 0; k < fol.size(); ++k) std::printf("---|");
			std::printf("\n");
			for (const Source& s : srcs)
			{
				std::printf("| %s | ", s.name.c_str());
				const bool low = s.presses.back().y < 0 && s.presses.back().button == BtnLight;
				const int defence = block ? (low ? 2 : 1) : 0;
				const int32_t dist = (atk.halfWidth + def.halfWidth) + 4 * kUnitsPerCm;
				for (const Action& f : fol)
				{
					const Outcome o = Trial(r, atk, def, s.presses, f, defence, dist);
					std::printf("%s | ", Cell(o, block == 0).c_str());
				}
				std::printf("\n");
			}
			std::printf("\n");
		}
	}
	std::printf("<!-- move-matrix:end -->\n");
	return 0;
}
