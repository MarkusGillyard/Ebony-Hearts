#pragma once

#include "CoreMinimal.h"
#include "Delegates/IDelegateInstance.h"

// Xlib's event union, as SDL_system.h declares it.
union _XEvent;

namespace EHLinux
{
// Holds XRandR output events back from SDL until the start of the next frame.
//
// SDL removes a display when an output reports itself disconnected, as a DisplayPort monitor does when it goes to
// standby or wakes. SDL can process that event inside its own fullscreen call, which keeps using the display it
// looked up before waiting on the window manager; it then reads the freed display and crashes (EH-07). Deferring the
// events lets SDL apply every display change from a plain event pump with no window call on the stack.
class FDisplayEventGuard
{
public:
	void Install();
	void Remove();

	bool IsActive() const { return bActive; }
	uint64 Deferred() const { return DeferredCount; }
	uint64 Replayed() const { return ReplayedCount; }

private:
	struct FStoredEvent
	{
		// sizeof(XEvent): Xlib pads the event union to 24 longs.
		long Words[24];
	};

	static bool OnX11Event(void* UserData, ::_XEvent* Event);
	void ResolveRandR(void* InDisplay);
	void ReplayDeferred();

	void* LibX11 = nullptr;
	void* XDisplay = nullptr;
	int (*PutBackEvent)(void*, ::_XEvent*) = nullptr;
	// RandR's RRNotify event type on this display; 0 until known, -1 when the display has no RandR.
	int RRNotifyType = 0;
	TArray<FStoredEvent> Pending;
	bool bReplaying = false;
	bool bActive = false;
	uint64 DeferredCount = 0;
	uint64 ReplayedCount = 0;
	FDelegateHandle FrameHandle;
};
}
