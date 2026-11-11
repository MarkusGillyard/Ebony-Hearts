// Test support for the display hot-plug probe (automation command display_hotplug_probe).
#include "EHLinuxPlatform.h"

#include <dlfcn.h>

THIRD_PARTY_INCLUDES_START
#include <SDL3/SDL.h>
THIRD_PARTY_INCLUDES_END

namespace EHLinux
{
namespace
{
// Mirrors of the stable Xlib / Xrandr ABI (Xlib.h, Xrandr.h); UE's toolchain ships no X11 headers.
struct FXRROutputChangeNotifyEvent
{
	int type;
	unsigned long serial;
	int send_event;
	void* display;
	unsigned long window;
	int subtype;
	unsigned long output;
	unsigned long crtc;
	unsigned long mode;
	unsigned short rotation;
	unsigned short connection;
	unsigned short subpixel_order;
};

struct FXRRScreenResources
{
	unsigned long timestamp;
	unsigned long configTimestamp;
	int ncrtc;
	unsigned long* crtcs;
	int noutput;
	unsigned long* outputs;
};

struct FXRROutputInfoHead
{
	unsigned long timestamp;
	unsigned long crtc;
	char* name;
	int nameLen;
	unsigned long mm_width;
	unsigned long mm_height;
	unsigned short connection;
};

constexpr int RRNotifyOutputChange = 1;
constexpr unsigned short RRConnected = 0;
constexpr unsigned short RRDisconnected = 1;

template <typename T>
T Sym(void* Lib, const char* Name)
{
	return Lib ? reinterpret_cast<T>(dlsym(Lib, Name)) : nullptr;
}
}

bool QueueOutputChange(void* SdlWindow, bool bConnected, FString& OutError)
{
	SDL_Window* Window = static_cast<SDL_Window*>(SdlWindow);
	void* Display = Window ? SDL_GetPointerProperty(SDL_GetWindowProperties(Window), SDL_PROP_WINDOW_X11_DISPLAY_POINTER, nullptr) : nullptr;
	if (Display == nullptr)
	{
		OutError = TEXT("not an X11 window");
		return false;
	}
	void* X11 = dlopen("libX11.so.6", RTLD_LAZY | RTLD_NOLOAD);
	void* Xrandr = dlopen("libXrandr.so.2", RTLD_LAZY | RTLD_NOLOAD);
	const auto QueryExtension = Sym<int (*)(void*, const char*, int*, int*, int*)>(X11, "XQueryExtension");
	const auto PutBackEvent = Sym<int (*)(void*, void*)>(X11, "XPutBackEvent");
	const auto DefaultRootWindow = Sym<unsigned long (*)(void*)>(X11, "XDefaultRootWindow");
	const auto GetOutputPrimary = Sym<unsigned long (*)(void*, unsigned long)>(Xrandr, "XRRGetOutputPrimary");
	const auto GetResources = Sym<FXRRScreenResources* (*)(void*, unsigned long)>(Xrandr, "XRRGetScreenResourcesCurrent");
	const auto GetOutputInfo = Sym<FXRROutputInfoHead* (*)(void*, FXRRScreenResources*, unsigned long)>(Xrandr, "XRRGetOutputInfo");
	const auto FreeOutputInfo = Sym<void (*)(FXRROutputInfoHead*)>(Xrandr, "XRRFreeOutputInfo");
	const auto FreeResources = Sym<void (*)(FXRRScreenResources*)>(Xrandr, "XRRFreeScreenResources");
	bool bOk = false;
	int Opcode = 0;
	int FirstEvent = 0;
	int FirstError = 0;
	if (!QueryExtension || !PutBackEvent || !DefaultRootWindow || !GetOutputPrimary || !GetResources || !GetOutputInfo || !FreeOutputInfo || !FreeResources)
	{
		OutError = TEXT("libX11/libXrandr functions unavailable");
	}
	else if (!QueryExtension(Display, "RANDR", &Opcode, &FirstEvent, &FirstError))
	{
		OutError = TEXT("no RandR on this display");
	}
	else
	{
		const unsigned long Root = DefaultRootWindow(Display);
		unsigned long Output = GetOutputPrimary(Display, Root);
		if (Output == 0)
		{
			// No primary output set: use the first connected output that drives a CRTC.
			if (FXRRScreenResources* Res = GetResources(Display, Root))
			{
				for (int i = 0; i < Res->noutput && Output == 0; ++i)
				{
					if (FXRROutputInfoHead* Info = GetOutputInfo(Display, Res, Res->outputs[i]))
					{
						if (Info->connection == RRConnected && Info->crtc != 0)
						{
							Output = Res->outputs[i];
						}
						FreeOutputInfo(Info);
					}
				}
				FreeResources(Res);
			}
		}
		if (Output == 0)
		{
			OutError = TEXT("no active XRandR output");
		}
		else
		{
			alignas(long) unsigned char Storage[24 * sizeof(long)] = {};
			FXRROutputChangeNotifyEvent* Ev = reinterpret_cast<FXRROutputChangeNotifyEvent*>(Storage);
			Ev->type = FirstEvent + 1;  // RRNotify
			Ev->send_event = 1;
			Ev->display = Display;
			Ev->window = Root;
			Ev->subtype = RRNotifyOutputChange;
			Ev->output = Output;
			Ev->connection = bConnected ? RRConnected : RRDisconnected;
			PutBackEvent(Display, Storage);
			bOk = true;
		}
	}
	if (Xrandr)
	{
		dlclose(Xrandr);
	}
	if (X11)
	{
		dlclose(X11);
	}
	return bOk;
}

void LeaveMoveOutstanding(void* SdlWindow)
{
	SDL_Window* Window = static_cast<SDL_Window*>(SdlWindow);
	int X = 0;
	int Y = 0;
	if (Window && SDL_GetWindowPosition(Window, &X, &Y))
	{
		SDL_SetWindowPosition(Window, X + 1, Y);
	}
}

FString DescribeDisplays()
{
	int Count = 0;
	SDL_DisplayID* Ids = SDL_GetDisplays(&Count);
	TArray<FString> Names;
	for (int i = 0; i < Count; ++i)
	{
		const char* Name = SDL_GetDisplayName(Ids[i]);
		Names.Add(Name ? FString(UTF8_TO_TCHAR(Name)) : FString(TEXT("?")));
	}
	SDL_free(Ids);
	return FString::Join(Names, TEXT("|"));
}
}
