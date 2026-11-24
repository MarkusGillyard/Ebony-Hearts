#include "EHPack.h"

bool FEHPackTuning::Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError)
{
	if (!Obj.IsValid())
	{
		return true;
	}
	bool bOk = true;
	auto Num = [&](const TCHAR* Name, float& Out, float Min, float Max) {
		double V = 0.0;
		if (Obj->TryGetNumberField(Name, V))
		{
			if (V < Min || V > Max)
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: pack.%s = %g is outside %g..%g."), Name, V, Min, Max);
				bOk = false;
				return;
			}
			Out = static_cast<float>(V);
		}
	};
	auto Int = [&](const TCHAR* Name, int32& Out, int32 Min, int32 Max) {
		float V = static_cast<float>(Out);
		Num(Name, V, static_cast<float>(Min), static_cast<float>(Max));
		Out = FMath::RoundToInt(V);
	};
	Int(TEXT("count"), Count, 1, 4);
	Num(TEXT("overwhelmedHealth"), OverwhelmedHealth, 0, 1);
	Num(TEXT("surroundRadius"), SurroundRadius, 50, 3000);
	Int(TEXT("surroundCount"), SurroundCount, 2, 4);
	Int(TEXT("hitsCount"), HitsCount, 1, 20);
	Num(TEXT("hitsWindow"), HitsWindow, 0.5f, 60);
	Num(TEXT("oneOnOneLinger"), OneOnOneLinger, 0, 60);
	Num(TEXT("holdBackRadius"), HoldBackRadius, 200, 3000);
	Num(TEXT("waitRadius"), WaitRadius, 100, 3000);
	Num(TEXT("turnTimeout"), TurnTimeout, 1, 60);
	const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
	if (Obj->TryGetArrayField(TEXT("spawns"), List))
	{
		Spawns.Reset();
		for (int32 i = 0; i < List->Num(); ++i)
		{
			const TArray<TSharedPtr<FJsonValue>>* P = nullptr;
			if (!(*List)[i]->TryGetArray(P) || P->Num() != 3 || P->ContainsByPredicate([](const TSharedPtr<FJsonValue>& Value) {
				return !Value.IsValid() || Value->Type != EJson::Number || !FMath::IsFinite(Value->AsNumber());
			}) || FMath::Abs((*P)[2]->AsNumber()) > 360.0)
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: pack.spawns[%d] must contain finite x and y coordinates and a yaw in -360..360 degrees."), i);
				return false;
			}
			FEHPackSpawn S;
			S.At = FVector((*P)[0]->AsNumber(), (*P)[1]->AsNumber(), 0.0);
			S.Yaw = static_cast<float>((*P)[2]->AsNumber());
			Spawns.Add(S);
		}
		if (Spawns.Num() < 4)
		{
			OutError = TEXT("Data/firstperson.json: pack.spawns needs four places (one per wolf).");
			return false;
		}
	}
	return bOk;
}
