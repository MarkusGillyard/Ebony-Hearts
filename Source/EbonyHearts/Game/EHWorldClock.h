// Destiny's Ark's time (New Direction, "Time"): always moving unless stopped for a reason, one real minute to one
// game hour, a day of 144 hours. While the player prays it runs much faster, and no prayer keeps the player waiting
// more than five real minutes (the prototype's reading: the longest prayer in the design, three days, takes five real
// minutes, about 86 times normal). The pause menu stops it. The Chapel, a pocket realm with no sun of its own, shows
// it through its windows: the window light's colour and strength, the glass's glow, the fog's tint and the general
// fills (tagged EHSkyFill, as daylight through the windows) follow the hour. There is no clock on screen. The numbers
// are data (Content/Data/firstperson.json, "clock").
#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

struct FEHClockKey
{
	float Hour = 0.0f;
	FLinearColor Color = FLinearColor::White;   // the window light's colour
	float Light = 1.0f;                          // its strength, times the map's own
	float Glass = 1.0f;                          // the glass's glow, times the map's own
	float Fog = 1.0f;                            // the fog's brightness, times the map's own
	float Fill = 1.0f;                           // the Chapel's general fills (daylight through the windows), times their own
};

struct FEHWorldClockTuning
{
	float DayHours = 144.0f;
	float RealSecondsPerHour = 60.0f;
	float StartHour = 4.0f;
	float PrayScale = 86.4f;
	TArray<FEHClockKey> Keys;                    // through the day from hour 0; the last wraps to the first
	bool Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError);
	// The light at an hour of the day (0..DayHours), eased between the keys.
	FEHClockKey Sample(float Hour) const;
};
