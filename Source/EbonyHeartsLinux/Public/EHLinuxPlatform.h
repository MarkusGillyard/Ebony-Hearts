#pragma once

#include "CoreMinimal.h"

namespace EHLinux
{
// Counters the evaluation runs check: which audio output is live, and how display hot-plug events were handled.
struct FPlatformReport
{
	// The game's SDL3 output is the running audio platform.
	bool bAudioOutputActive = false;
	// Mixer buffers handed to SDL from inside its callback.
	uint64 AudioBuffersDelivered = 0;
	// Mixer submissions made from other threads (the render thread's start-up prime, the null device, device
	// swaps). They have no SDL buffer to go to and are dropped.
	uint64 AudioSubmitsDropped = 0;
	bool bDisplayGuardActive = false;
	// XRandR output events held back from SDL until the start of the next frame, and how many were handed back.
	uint64 DisplayEventsDeferred = 0;
	uint64 DisplayEventsReplayed = 0;
};

EBONYHEARTSLINUX_API FPlatformReport GetPlatformReport();

// Test support for the display hot-plug probe. SdlWindow is the native handle of an SDL window (SDL_Window*).
// Places an XRandR output-change event for the window's monitor at the head of its X event queue, as a DisplayPort
// monitor sends when it enters standby (bConnected false) or wakes (true).
EBONYHEARTSLINUX_API bool QueueOutputChange(void* SdlWindow, bool bConnected, FString& OutError);
// Moves the window by one pixel without waiting for the window manager, leaving the request outstanding.
EBONYHEARTSLINUX_API void LeaveMoveOutstanding(void* SdlWindow);
// Names of the displays SDL currently reports.
EBONYHEARTSLINUX_API FString DescribeDisplays();
}
