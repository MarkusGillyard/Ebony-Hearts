#include "EHGameMode.h"

#include "EHGameDirector.h"
#include "EHPlayerCharacter.h"
#include "Engine/World.h"

AEHGameMode::AEHGameMode()
{
	DefaultPawnClass = AEHPlayerCharacter::StaticClass();
	HUDClass = nullptr;
}

APawn* AEHGameMode::SpawnDefaultPawnAtTransform_Implementation(AController* NewPlayer, const FTransform& SpawnTransform)
{
	FActorSpawnParameters Params;
	Params.Instigator = GetInstigator();
	Params.ObjectFlags |= RF_Transient;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	UClass* PawnClass = GetDefaultPawnClassForController(NewPlayer);
	return PawnClass ? GetWorld()->SpawnActor<APawn>(PawnClass, SpawnTransform, Params) : nullptr;
}

void AEHGameMode::BeginPlay()
{
	Super::BeginPlay();
	FActorSpawnParameters Params;
	Params.Name = TEXT("EbonyHeartsDirector");
	GetWorld()->SpawnActor<AEHGameDirector>(AEHGameDirector::StaticClass(), FTransform::Identity, Params);
}
