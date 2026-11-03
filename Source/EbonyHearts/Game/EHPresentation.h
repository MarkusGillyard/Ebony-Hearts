// Presentation-only data (display names, colours, asset paths, per-move audio/effects hints) loaded from
// Content/Data/presentation.json. Nothing here affects combat outcomes.
#pragma once

#include "CoreMinimal.h"

struct FEHMovePresentation
{
	FName Whoosh;          // sound played when the move starts
	FName Impact;          // override impact sound
	FName FxBone;          // bone the move's effect trails follow
	bool bFlame = false;   // crimson flame accents (Ashka's flame variations)
	float Shake = 0.0f;    // extra camera response on hit, 0-1
};

struct FEHCharacterPresentation
{
	FString Id;
	FText DisplayName;
	FText Title;
	FText Style;
	FText GaugeLabel;
	FString MeshPath;
	FString AnimFolder;
	FString AnimPrefix;
	float MeshYaw = 0.0f;
	float MeshScale = 1.0f;
	FLinearColor Primary = FLinearColor::White;
	FLinearColor Accent = FLinearColor::White;
	FLinearColor Graybox = FLinearColor::Gray;
	FName HeadBone = TEXT("head");
	TArray<FName> AuraBones;
	TMap<FString, FEHMovePresentation> Moves;
	TMap<FString, FText> MoveNotes;
};

struct FEHPresentation
{
	TMap<FString, FEHCharacterPresentation> Characters;
	bool Load(const FString& Text, FString& OutError);
	const FEHCharacterPresentation& Get(const FString& Id) const;
	const FEHMovePresentation* Move(const FString& CharId, const FString& MoveId) const;
};
