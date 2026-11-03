#include "EHPresentation.h"

#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace EHPresentationDetail
{
FLinearColor Color(const TSharedPtr<FJsonObject>& Obj, const TCHAR* Field, const FLinearColor& Fallback)
{
	const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
	if (!Obj->TryGetArrayField(Field, Arr) || Arr->Num() < 3)
	{
		return Fallback;
	}
	return FLinearColor(static_cast<float>((*Arr)[0]->AsNumber()), static_cast<float>((*Arr)[1]->AsNumber()), static_cast<float>((*Arr)[2]->AsNumber()), 1.0f);
}
}

bool FEHPresentation::Load(const FString& Text, FString& OutError)
{
	using namespace EHPresentationDetail;
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		OutError = TEXT("presentation.json: not valid JSON");
		return false;
	}
	const TSharedPtr<FJsonObject>* Chars = nullptr;
	if (!Root->TryGetObjectField(TEXT("characters"), Chars))
	{
		OutError = TEXT("presentation.json: missing characters");
		return false;
	}
	for (const auto& Pair : (*Chars)->Values)
	{
		const TSharedPtr<FJsonObject> C = Pair.Value->AsObject();
		if (!C.IsValid())
		{
			OutError = FString::Printf(TEXT("presentation.json: characters.%s is not an object"), *Pair.Key);
			return false;
		}
		FEHCharacterPresentation P;
		P.Id = FString(*Pair.Key);
		P.DisplayName = FText::FromString(C->GetStringField(TEXT("displayName")));
		P.Title = FText::FromString(C->GetStringField(TEXT("title")));
		P.Style = FText::FromString(C->GetStringField(TEXT("style")));
		P.GaugeLabel = FText::FromString(C->GetStringField(TEXT("gaugeLabel")));
		P.MeshPath = C->GetStringField(TEXT("mesh"));
		P.AnimFolder = C->GetStringField(TEXT("animFolder"));
		P.AnimPrefix = C->GetStringField(TEXT("animPrefix"));
		P.MeshYaw = static_cast<float>(C->GetNumberField(TEXT("meshYaw")));
		P.MeshScale = static_cast<float>(C->GetNumberField(TEXT("meshScale")));
		P.Primary = Color(C, TEXT("primary"), FLinearColor::White);
		P.Accent = Color(C, TEXT("accent"), FLinearColor::White);
		P.Graybox = Color(C, TEXT("graybox"), FLinearColor::Gray);
		FString Head;
		if (C->TryGetStringField(TEXT("headBone"), Head))
		{
			P.HeadBone = FName(*Head);
		}
		const TArray<TSharedPtr<FJsonValue>>* Bones = nullptr;
		if (C->TryGetArrayField(TEXT("auraBones"), Bones))
		{
			for (const TSharedPtr<FJsonValue>& B : *Bones)
			{
				P.AuraBones.Add(FName(*B->AsString()));
			}
		}
		const TSharedPtr<FJsonObject>* Moves = nullptr;
		if (C->TryGetObjectField(TEXT("moves"), Moves))
		{
			for (const auto& MovePair : (*Moves)->Values)
			{
				const TSharedPtr<FJsonObject> M = MovePair.Value->AsObject();
				if (!M.IsValid())
				{
					continue;
				}
				FEHMovePresentation MP;
				FString S;
				if (M->TryGetStringField(TEXT("whoosh"), S)) MP.Whoosh = FName(*S);
				if (M->TryGetStringField(TEXT("impact"), S)) MP.Impact = FName(*S);
				if (M->TryGetStringField(TEXT("fxBone"), S)) MP.FxBone = FName(*S);
				M->TryGetBoolField(TEXT("flame"), MP.bFlame);
				double Shake = 0.0;
				if (M->TryGetNumberField(TEXT("shake"), Shake)) MP.Shake = static_cast<float>(Shake);
				const FString MoveKey(*MovePair.Key);
				if (M->TryGetStringField(TEXT("note"), S)) P.MoveNotes.Add(MoveKey, FText::FromString(S));
				P.Moves.Add(MoveKey, MP);
			}
		}
		Characters.Add(P.Id, P);
	}
	if (!Characters.Contains(TEXT("wren")) || !Characters.Contains(TEXT("ashka")))
	{
		OutError = TEXT("presentation.json: needs wren and ashka");
		return false;
	}
	return true;
}

const FEHCharacterPresentation& FEHPresentation::Get(const FString& Id) const
{
	return Characters.FindChecked(Id);
}

const FEHMovePresentation* FEHPresentation::Move(const FString& CharId, const FString& MoveId) const
{
	const FEHCharacterPresentation* C = Characters.Find(CharId);
	return C ? C->Moves.Find(MoveId) : nullptr;
}
