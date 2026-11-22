#include "EHChapel.h"

bool FEHChapelTuning::Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError)
{
	if (!Obj.IsValid())
	{
		return true;
	}
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
	const TArray<TSharedPtr<FJsonValue>>* Look = nullptr;
	if (Obj->TryGetArrayField(TEXT("prayLookAt"), Look) && Look->Num() == 3)
	{
		PrayLookAt = FVector((*Look)[0]->AsNumber(), (*Look)[1]->AsNumber(), (*Look)[2]->AsNumber());
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
			const TArray<TSharedPtr<FJsonValue>>* At = nullptr;
			if (!O->TryGetStringField(TEXT("id"), E.Id) || !O->TryGetArrayField(TEXT("at"), At) || At->Num() != 3)
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: chapel.interactables[%d] needs an id and \"at\": [x, y, z]."), i);
				return false;
			}
			E.At = FVector((*At)[0]->AsNumber(), (*At)[1]->AsNumber(), (*At)[2]->AsNumber());
			Num(O, FString::Printf(TEXT("interactables[%d]."), i), TEXT("radius"), E.Radius, 5, 500);
			O->TryGetStringField(TEXT("prompt"), E.Prompt);
			O->TryGetStringField(TEXT("text"), E.Text);
			O->TryGetBoolField(TEXT("pray"), E.bPray);
			Interactables.Add(E);
		}
	}
	return bOk;
}
