#include "EHGameMode.h"

#include "EHGameDirector.h"
#include "Engine/World.h"

AEHGameMode::AEHGameMode()
{
	DefaultPawnClass = nullptr;
	HUDClass = nullptr;
}

void AEHGameMode::BeginPlay()
{
	Super::BeginPlay();
	FActorSpawnParameters Params;
	Params.Name = TEXT("EbonyHeartsDirector");
	GetWorld()->SpawnActor<AEHGameDirector>(AEHGameDirector::StaticClass(), FTransform::Identity, Params);
}
