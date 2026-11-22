// The Drowned Chapel's interactions (interior stage 2): things the player can look at and use with Interact, and
// prayer at the sanctuary's kneeler, which shows the alignment meter (the only place it can be seen). The places and
// their placeholder text are data (Content/Data/firstperson.json, "chapel"), so the creator can rewrite them.
#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

struct FEHInteractable
{
	FString Id;                      // for logs and tests
	FVector At = FVector::ZeroVector;
	float Radius = 60.0f;            // how far off the line of sight it still counts as looked at
	FString Prompt = TEXT("Look");   // after the key: "E  Look"
	FString Text;                    // shown when used (placeholder wording until the creator writes it)
	bool bPray = false;              // the kneeler: Interact kneels and prays
};

struct FEHChapelTuning
{
	TArray<FEHInteractable> Interactables;
	float Reach = 230.0f;            // how far from the eye something can be used
	float MessageSeconds = 5.0f;     // a used thing's text stays this long, or until the player walks away
	float MessageWalkAway = 300.0f;
	float PrayLookScale = 0.4f;      // looking while kneeling is slowed
	FVector PrayLookAt = FVector(0, -2050, 760);   // kneeling turns the view toward this (the rose window)
	float PrayTurnSeconds = 1.2f;
	bool Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError);
};
