#include "EHChapel.h"

bool FEHChapelTuning::Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError)
{
	if (!Obj.IsValid())
	{
		return true;
	}
	auto ReadPoint = [](const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, FVector& Out) {
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (!Object->TryGetArrayField(Name, Values) || Values->Num() != 3 || Values->ContainsByPredicate([](const TSharedPtr<FJsonValue>& Value) {
			return !Value.IsValid() || Value->Type != EJson::Number || !FMath::IsFinite(Value->AsNumber());
		}))
		{
			return false;
		}
		Out = FVector((*Values)[0]->AsNumber(), (*Values)[1]->AsNumber(), (*Values)[2]->AsNumber());
		return true;
	};
	bool bOk = true;
	auto Num = [&](const TSharedPtr<FJsonObject>& O, const FString& Where, const TCHAR* Name, float& Out, float Min, float Max) {
		double V = 0.0;
		if (O->TryGetNumberField(Name, V))
		{
			if (V < Min || V > Max)
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: chapel.%s%s = %g is outside %g..%g."), *Where, Name, V, Min, Max);
				bOk = false;
				return;
			}
			Out = static_cast<float>(V);
		}
	};
	Num(Obj, TEXT(""), TEXT("reach"), Reach, 50, 1000);
	Num(Obj, TEXT(""), TEXT("messageSeconds"), MessageSeconds, 0.5f, 60);
	Num(Obj, TEXT(""), TEXT("messageWalkAway"), MessageWalkAway, 50, 5000);
	Num(Obj, TEXT(""), TEXT("prayLookScale"), PrayLookScale, 0, 1);
	Num(Obj, TEXT(""), TEXT("prayTurnSeconds"), PrayTurnSeconds, 0.05f, 10);
	if (Obj->HasField(TEXT("prayLookAt")) && !ReadPoint(Obj, TEXT("prayLookAt"), PrayLookAt))
	{
		OutError = TEXT("Data/firstperson.json: chapel.prayLookAt must contain three finite coordinates.");
		return false;
	}
	Num(Obj, TEXT(""), TEXT("sparkRange"), SparkRange, 0, 10000);
	Num(Obj, TEXT(""), TEXT("sparkGap"), SparkGap, 0.05f, 30);
	if (Obj->HasField(TEXT("sparkAt")) && !ReadPoint(Obj, TEXT("sparkAt"), SparkAt))
	{
		OutError = TEXT("Data/firstperson.json: chapel.sparkAt must contain three finite coordinates.");
		return false;
	}
	const TArray<TSharedPtr<FJsonValue>>* SoundList = nullptr;
	if (Obj->TryGetArrayField(TEXT("sounds"), SoundList))
	{
		Sounds.Reset();
		for (int32 i = 0; i < SoundList->Num() && bOk; ++i)
		{
			const TSharedPtr<FJsonObject>* It = nullptr;
			FEHChapelSound S;
			FString Name;
			if (!(*SoundList)[i]->TryGetObject(It) || !(*It)->TryGetStringField(TEXT("name"), Name) || !ReadPoint(*It, TEXT("at"), S.At))
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: chapel.sounds[%d] needs a name and \"at\": [x, y, z]."), i);
				return false;
			}
			S.Name = FName(*Name);
			const FString Where = FString::Printf(TEXT("sounds[%d]."), i);
			Num(*It, Where, TEXT("inner"), S.Inner, 0, 10000);
			Num(*It, Where, TEXT("falloff"), S.Falloff, 1, 20000);
			Num(*It, Where, TEXT("volume"), S.Volume, 0, 4);
			Sounds.Add(S);
		}
	}
	const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
	if (Obj->TryGetArrayField(TEXT("interactables"), List))
	{
		Interactables.Reset();
		for (int32 i = 0; i < List->Num() && bOk; ++i)
		{
			const TSharedPtr<FJsonObject>* It = nullptr;
			if (!(*List)[i]->TryGetObject(It))
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: chapel.interactables[%d] is not an object."), i);
				return false;
			}
			FEHInteractable E;
			const TSharedPtr<FJsonObject>& O = *It;
			if (!O->TryGetStringField(TEXT("id"), E.Id) || !ReadPoint(O, TEXT("at"), E.At))
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: chapel.interactables[%d] needs an id and \"at\": [x, y, z]."), i);
				return false;
			}
			Num(O, FString::Printf(TEXT("interactables[%d]."), i), TEXT("radius"), E.Radius, 5, 500);
			O->TryGetStringField(TEXT("prompt"), E.Prompt);
			O->TryGetStringField(TEXT("text"), E.Text);
			O->TryGetBoolField(TEXT("pray"), E.bPray);
			Interactables.Add(E);
		}
	}
	return bOk;
}
