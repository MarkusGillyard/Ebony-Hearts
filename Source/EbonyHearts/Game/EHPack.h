// The Chapel wolves as a pack (milestone 6). Two to four wolves fight together and take turns: one holds the turn
// and may attack; the others circle close and press without attacking. The turn passes, to the wolf that has waited
// longest, when the holder finishes an attack, dies, is frozen, stops fighting (backs off, calms), or cannot get at
// the player for a while (a blocked path). When the player is overwhelmed the pack allows a one-on-one fight: the
// holder fights on alone and the others stand back and watch until it is out of the fight.
//
// Overwhelmed (the creator's rule, 2026-11-23): any of Health below half, three or more wolves close round the
// player, or three hits taken within four seconds. The numbers are data (Content/Data/firstperson.json, "pack").
#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

struct FEHPackSpawn
{
	FVector At = FVector::ZeroVector;   // feet; also the wolf's rest
	float Yaw = 90.0f;
};

struct FEHPackTuning
{
	int32 Count = 1;                    // wolves in the Chapel (development builds can change it live)
	TArray<FEHPackSpawn> Spawns;        // the first is the lone wolf's; one per wolf up to four
	float OverwhelmedHealth = 0.5f;     // Health below this fraction of full
	float SurroundRadius = 400.0f;      // this many wolves this close count as surrounding the player
	int32 SurroundCount = 3;
	int32 HitsCount = 3;                // this many hits taken
	float HitsWindow = 4.0f;            // within this many seconds
	float OneOnOneLinger = 3.0f;        // seconds the one-on-one lasts after the player stops being overwhelmed
	float HoldBackRadius = 650.0f;      // one-on-one: how far the others stand back
	float WaitRadius = 520.0f;          // taking turns: how far the waiting wolves circle (outside SurroundRadius)
	float TurnTimeout = 6.0f;           // a holder that has not attacked for this long passes the turn (blocked, stuck)
	bool Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError);
};
