#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"

#include "EHGameMode.generated.h"

// The first-person player character is the default pawn; the director runs devices, menus and settings.
UCLASS(NotBlueprintable)
class AEHGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AEHGameMode();
	virtual void BeginPlay() override;
	// The pawn always spawns; the director then places it at the start from Data/firstperson.json.
	virtual APawn* SpawnDefaultPawnAtTransform_Implementation(AController* NewPlayer, const FTransform& SpawnTransform) override;
};
