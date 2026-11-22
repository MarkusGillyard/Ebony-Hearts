#include "EHWorldClock.h"

bool FEHWorldClockTuning::Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError)
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
				OutError = FString::Printf(TEXT("Data/firstperson.json: clock.%s%s = %g is outside %g..%g."), *Where, Name, V, Min, Max);
				bOk = false;
				return;
			}
			Out = static_cast<float>(V);
		}
	};
	Num(Obj, TEXT(""), TEXT("dayHours"), DayHours, 1, 10000);
	Num(Obj, TEXT(""), TEXT("realSecondsPerHour"), RealSecondsPerHour, 0.01f, 36000);
	Num(Obj, TEXT(""), TEXT("startHour"), StartHour, 0, 10000);
	Num(Obj, TEXT(""), TEXT("prayScale"), PrayScale, 1, 100000);
	const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
	if (Obj->TryGetArrayField(TEXT("keys"), List))
	{
		Keys.Reset();
		for (int32 i = 0; i < List->Num() && bOk; ++i)
		{
			const TSharedPtr<FJsonObject>* It = nullptr;
			const TArray<TSharedPtr<FJsonValue>>* Col = nullptr;
			if (!(*List)[i]->TryGetObject(It) || !(*It)->TryGetArrayField(TEXT("color"), Col) || Col->Num() != 3)
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: clock.keys[%d] needs \"hour\" and \"color\": [r, g, b]."), i);
				return false;
			}
			FEHClockKey K;
			const FString Where = FString::Printf(TEXT("keys[%d]."), i);
			Num(*It, Where, TEXT("hour"), K.Hour, 0, DayHours);
			K.Color = FLinearColor((*Col)[0]->AsNumber(), (*Col)[1]->AsNumber(), (*Col)[2]->AsNumber(), 1.0f);
			Num(*It, Where, TEXT("light"), K.Light, 0, 20);
			Num(*It, Where, TEXT("glass"), K.Glass, 0, 20);
			Num(*It, Where, TEXT("fog"), K.Fog, 0, 20);
			Num(*It, Where, TEXT("fill"), K.Fill, 0, 20);
			if (Keys.Num() > 0 && K.Hour <= Keys.Last().Hour)
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: clock.keys[%d] must come after the key before it."), i);
				return false;
			}
			Keys.Add(K);
		}
	}
	return bOk;
}

FEHClockKey FEHWorldClockTuning::Sample(float Hour) const
{
	if (Keys.Num() == 0)
	{
		return FEHClockKey();
	}
	if (Keys.Num() == 1)
	{
		return Keys[0];
	}
	const float H = FMath::Fmod(FMath::Fmod(Hour, DayHours) + DayHours, DayHours);
	int32 Next = 0;
	while (Next < Keys.Num() && Keys[Next].Hour <= H)
	{
		++Next;
	}
	const FEHClockKey& A = Keys[(Next - 1 + Keys.Num()) % Keys.Num()];
	const FEHClockKey& B = Keys[Next % Keys.Num()];
	float Span = B.Hour - A.Hour;
	float Into = H - A.Hour;
	if (Span <= 0.0f)
	{
		Span += DayHours;
	}
	if (Into < 0.0f)
	{
		Into += DayHours;
	}
	const float T = FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp(Into / Span, 0.0f, 1.0f));
	FEHClockKey Out;
	Out.Hour = H;
	Out.Color = FLinearColor::LerpUsingHSV(A.Color, B.Color, T);
	Out.Light = FMath::Lerp(A.Light, B.Light, T);
	Out.Glass = FMath::Lerp(A.Glass, B.Glass, T);
	Out.Fog = FMath::Lerp(A.Fog, B.Fog, T);
	Out.Fill = FMath::Lerp(A.Fill, B.Fill, T);
	return Out;
}
