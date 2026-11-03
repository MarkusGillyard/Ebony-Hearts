#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"

#include "EHGameMode.generated.h"

// No pawns: the director drives every fighter and the camera.
UCLASS(NotBlueprintable)
class AEHGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AEHGameMode();
	virtual void BeginPlay() override;
};
