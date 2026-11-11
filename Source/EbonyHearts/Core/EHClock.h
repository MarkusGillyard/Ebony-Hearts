// Converts variable render-frame time into whole 60 Hz simulation ticks.
// Time is accumulated in integer nanoseconds scaled by the tick rate, so there is no floating-point drift and
// the number of ticks depends only on elapsed time, never on how that time was split into render frames.
// Stall policy: at most kMaxCatchUp ticks run per render frame; time beyond that is dropped and counted, so a
// long hitch slows the game briefly instead of spiralling or resolving many ticks of combat unseen.
#pragma once

#include <cstdint>

namespace eh
{
class FixedStepClock
{
public:
	static constexpr int32_t kTickHz = 60;
	static constexpr int32_t kMaxCatchUp = 4;
	static constexpr int64_t kNsPerSecond = 1000000000LL;

	// Adds elapsed wall time and returns how many ticks to simulate now.
	int32_t Advance(int64_t elapsedNs)
	{
		if (elapsedNs < 0)
		{
			elapsedNs = 0;
		}
		accum_ += elapsedNs * kTickHz;
		int32_t ticks = 0;
		while (accum_ >= kNsPerSecond && ticks < kMaxCatchUp)
		{
			accum_ -= kNsPerSecond;
			++ticks;
		}
		if (accum_ >= kNsPerSecond)
		{
			const int64_t whole = accum_ / kNsPerSecond;
			dropped_ += whole;
			accum_ -= whole * kNsPerSecond;
		}
		total_ += ticks;
		return ticks;
	}

	// Fraction of the way to the next tick, for render interpolation only.
	double Alpha() const { return static_cast<double>(accum_) / static_cast<double>(kNsPerSecond); }

	// Pausing or losing focus must not cause a catch-up burst on resume.
	void Reset() { accum_ = 0; }

	int64_t DroppedTicks() const { return dropped_; }
	int64_t TotalTicks() const { return total_; }

private:
	int64_t accum_ = 0;
	int64_t dropped_ = 0;
	int64_t total_ = 0;
};
}
