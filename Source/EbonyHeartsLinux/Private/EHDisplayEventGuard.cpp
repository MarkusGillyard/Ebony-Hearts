#include "EHDisplayEventGuard.h"

#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/Parse.h"

#include <dlfcn.h>

THIRD_PARTY_INCLUDES_START
#include <SDL3/SDL.h>
THIRD_PARTY_INCLUDES_END

DEFINE_LOG_CATEGORY_STATIC(LogEHDisplay, Log, All);

namespace EHLinux
{
namespace
{
// The fields every Xlib event starts with (XAnyEvent). UE's toolchain ships no X11 headers; SDL loads libX11 itself.
struct FXAnyEvent
{
	int type;
	unsigned long serial;
	int send_event;
	void* display;
	unsigned long window;
};

// randr.h: RRNotify is the extension's second event code.
constexpr int RRNotifyEventOffset = 1;
}

void FDisplayEventGuard::Install()
{
#if !UE_BUILD_SHIPPING
	// Diagnosis only: lets the same Development binary run with and without the guard.
	if (FParse::Param(FCommandLine::Get(), TEXT("EHNoDisplayEventGuard")))
	{
		UE_LOG(LogEHDisplay, Warning, TEXT("Display event guard disabled from the command line."));
		return;
	}
#endif
	SDL_SetX11EventHook(&FDisplayEventGuard::OnX11Event, this);
	FrameHandle = FCoreDelegates::OnBeginFrame.AddRaw(this, &FDisplayEventGuard::ReplayDeferred);
	bActive = true;
}

void FDisplayEventGuard::Remove()
{
	if (!bActive)
	{
		return;
	}
	SDL_SetX11EventHook(nullptr, nullptr);
	FCoreDelegates::OnBeginFrame.Remove(FrameHandle);
	Pending.Reset();
	if (LibX11 != nullptr)
	{
		dlclose(LibX11);
		LibX11 = nullptr;
	}
	bActive = false;
}

bool FDisplayEventGuard::OnX11Event(void* UserData, ::_XEvent* Event)
{
	FDisplayEventGuard& Self = *static_cast<FDisplayEventGuard*>(UserData);
	const FXAnyEvent* Any = reinterpret_cast<const FXAnyEvent*>(Event);
	if (Self.RRNotifyType == 0)
	{
		Self.ResolveRandR(Any->display);
	}
	if (Any->type != Self.RRNotifyType || Self.bReplaying)
	{
		return true;
	}
	FStoredEvent& Stored = Self.Pending.AddDefaulted_GetRef();
	FMemory::Memcpy(&Stored, Event, sizeof(FStoredEvent));
	Self.XDisplay = Any->display;
	++Self.DeferredCount;
	return false;
}

void FDisplayEventGuard::ResolveRandR(void* InDisplay)
{
	RRNotifyType = -1;
	LibX11 = dlopen("libX11.so.6", RTLD_LAZY | RTLD_NOLOAD);
	if (LibX11 == nullptr)
	{
		UE_LOG(LogEHDisplay, Warning, TEXT("libX11 is not loaded; display events go straight to SDL."));
		return;
	}
	using FQueryExtension = int (*)(void*, const char*, int*, int*, int*);
	const FQueryExtension QueryExtension = reinterpret_cast<FQueryExtension>(dlsym(LibX11, "XQueryExtension"));
	PutBackEvent = reinterpret_cast<int (*)(void*, ::_XEvent*)>(dlsym(LibX11, "XPutBackEvent"));
	int Opcode = 0;
	int FirstEvent = 0;
	int FirstError = 0;
	if (QueryExtension != nullptr && PutBackEvent != nullptr && InDisplay != nullptr && QueryExtension(InDisplay, "RANDR", &Opcode, &FirstEvent, &FirstError))
	{
		RRNotifyType = FirstEvent + RRNotifyEventOffset;
		UE_LOG(LogEHDisplay, Log, TEXT("XRandR output events (type %d) are applied at the start of each frame."), RRNotifyType);
	}
	else
	{
		UE_LOG(LogEHDisplay, Warning, TEXT("XRandR is unavailable; display events go straight to SDL."));
	}
}

void FDisplayEventGuard::ReplayDeferred()
{
	if (Pending.Num() == 0 || PutBackEvent == nullptr || XDisplay == nullptr)
	{
		return;
	}
	// XPutBackEvent puts an event at the head of the queue, so hand them back newest first.
	for (int32 i = Pending.Num() - 1; i >= 0; --i)
	{
		PutBackEvent(XDisplay, reinterpret_cast<::_XEvent*>(&Pending[i]));
	}
	ReplayedCount += Pending.Num();
	UE_LOG(LogEHDisplay, Log, TEXT("Applying %d deferred display event(s)."), Pending.Num());
	Pending.Reset();
	// The frame has not started any window work yet, so SDL can add and remove displays here.
	bReplaying = true;
	SDL_PumpEvents();
	bReplaying = false;
}
}
