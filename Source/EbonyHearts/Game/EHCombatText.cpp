#include "EHCombatText.h"

#include "EHUICanvas.h"
#include "EHUIStyle.h"
#include "GameFramework/Actor.h"

const TCHAR* EHLineKindName(EEHLineKind K)
{
	switch (K)
	{
	case EEHLineKind::Friendly: return TEXT("friendly");
	case EEHLineKind::Warning: return TEXT("warning");
	case EEHLineKind::Hostile: return TEXT("hostile");
	default: return TEXT("player");
	}
}

bool FEHCombatTextTuning::Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError)
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
				OutError = FString::Printf(TEXT("Data/firstperson.json: combatText.%s = %g is outside %g..%g."), Name, V, Min, Max);
				bOk = false;
				return;
			}
			Out = static_cast<float>(V);
		}
	};
	Obj->TryGetBoolField(TEXT("enabled"), bEnabled);
	Num(TEXT("chance"), Chance, 0, 1);
	Num(TEXT("globalGap"), GlobalGap, 0, 60);
	Num(TEXT("speakerGap"), SpeakerGap, 0, 120);
	float MaxV = static_cast<float>(MaxVisible);
	Num(TEXT("maxVisible"), MaxV, 1, 8);
	MaxVisible = FMath::RoundToInt(MaxV);
	Num(TEXT("lifeBase"), LifeBase, 0.2f, 10);
	Num(TEXT("lifePerChar"), LifePerChar, 0, 0.5f);
	Num(TEXT("lifeMin"), LifeMin, 0.5f, 10);
	Num(TEXT("lifeMax"), LifeMax, 0.5f, 20);
	Num(TEXT("popSeconds"), PopSeconds, 0, 1);
	Num(TEXT("fadeIn"), FadeIn, 0, 2);
	Num(TEXT("fadeOut"), FadeOut, 0, 2);
	Num(TEXT("maxWidth"), MaxWidth, 120, 1200);
	Num(TEXT("fontSize"), FontSize, 16, 64);
	const TSharedPtr<FJsonObject>* LinesObj = nullptr;
	if (Obj->TryGetObjectField(TEXT("lines"), LinesObj))
	{
		Lines.Reset();
		for (const auto& Pair : (*LinesObj)->Values)
		{
			const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
			if (!Pair.Value->TryGetArray(List))
			{
				OutError = FString::Printf(TEXT("Data/firstperson.json: combatText.lines.%s must be a list."), *Pair.Key);
				return false;
			}
			TArray<FEHCombatLine>& Out = Lines.Add(FString(*Pair.Key));
			for (const TSharedPtr<FJsonValue>& V : *List)
			{
				// A line is a string (the creator's own words) or {"text": ..., "placeholder": true}.
				FEHCombatLine L;
				const TSharedPtr<FJsonObject>* LineObj = nullptr;
				if (V->TryGetString(L.Text))
				{
					L.bPlaceholder = false;
				}
				else if (V->TryGetObject(LineObj))
				{
					(*LineObj)->TryGetStringField(TEXT("text"), L.Text);
					L.bPlaceholder = true;
					(*LineObj)->TryGetBoolField(TEXT("placeholder"), L.bPlaceholder);
				}
				if (!L.Text.IsEmpty())
				{
					Out.Add(L);
				}
			}
		}
	}
	return bOk;
}

FString FEHCombatText::KeyOf(const AActor* Speaker)
{
	return Speaker ? Speaker->GetName() : FString(TEXT("player"));
}

bool FEHCombatText::Offer(const FString& Event, const AActor* Speaker, EEHLineKind Kind, float Now, bool bForce)
{
	const TArray<FEHCombatLine>* List = Tuning.Lines.Find(Event);
	if (!Tuning.bEnabled || List == nullptr || List->Num() == 0)
	{
		return false;
	}
	const FString Who = KeyOf(Speaker);
	if (!bForce && !bNatural)
	{
		return false;
	}
	if (!bForce)
	{
		const bool bFirst = !SaidOnce.Contains(Who + TEXT("|") + Event);
		const float* Last = SpeakerLast.Find(Who);
		const bool bSpeaking = Bubbles.ContainsByPredicate([&](const FBubble& B) { return KeyOf(B.Speaker.Get()) == Who && (B.bPlayer == (Speaker == nullptr)); });
		if (bSpeaking || Now - LastAny < Tuning.GlobalGap || (Last && Now - *Last < Tuning.SpeakerGap) || Bubbles.Num() >= Tuning.MaxVisible
			|| (!bFirst && FMath::FRand() >= Tuning.Chance))
		{
			++Refused;
			return false;
		}
	}
	// One line per speaker at a time: a new one replaces it. Full: the oldest gives way (forced lines only get here).
	Bubbles.RemoveAll([&](const FBubble& B) { return B.bPlayer == (Speaker == nullptr) && (Speaker == nullptr || B.Speaker.Get() == Speaker); });
	while (Bubbles.Num() >= Tuning.MaxVisible)
	{
		Bubbles.RemoveAt(0);
	}
	int32& Next = NextLine.FindOrAdd(Event);
	const FEHCombatLine& L = (*List)[Next % List->Num()];
	++Next;
	FBubble B;
	B.Speaker = Speaker;
	B.bPlayer = Speaker == nullptr;
	B.Kind = Kind;
	B.Text = L.Text;
	B.bPlaceholder = L.bPlaceholder;
	B.Life = FMath::Clamp(Tuning.LifeBase + Tuning.LifePerChar * L.Text.Len(), Tuning.LifeMin, Tuning.LifeMax);
	B.Serial = ++Serial;
	Bubbles.Add(B);
	SaidOnce.Add(Who + TEXT("|") + Event);
	SpeakerLast.Add(Who, Now);
	LastAny = Now;
	++Shown;
	++ShownByKind[static_cast<int32>(Kind)];
	MaxVisibleSeen = FMath::Max(MaxVisibleSeen, Bubbles.Num());
	LastText = L.Text;
	return true;
}

void FEHCombatText::Tick(float DeltaSeconds)
{
	for (FBubble& B : Bubbles)
	{
		B.Age += DeltaSeconds;
	}
	Bubbles.RemoveAll([](const FBubble& B) { return B.Age >= B.Life || (!B.bPlayer && !B.Speaker.IsValid()); });
}

void FEHCombatText::Clear()
{
	Bubbles.Reset();
	SpeakerLast.Reset();
	SaidOnce.Reset();
	LastAny = -1000.0f;
}

TArray<FString> FEHCombatText::Wrap(const FString& Text, const FEHPainter& P, const FSlateFontInfo& Font) const
{
	TArray<FString> Words;
	Text.ParseIntoArrayWS(Words);
	TArray<FString> Out;
	FString Cur;
	for (const FString& W : Words)
	{
		const FString Try = Cur.IsEmpty() ? W : Cur + TEXT(" ") + W;
		if (!Cur.IsEmpty() && P.Measure(Try, Font).X > Tuning.MaxWidth)
		{
			Out.Add(Cur);
			Cur = W;
		}
		else
		{
			Cur = Try;
		}
	}
	if (!Cur.IsEmpty())
	{
		Out.Add(Cur);
	}
	return Out;
}

void FEHCombatText::Paint(FEHPainter& P, const FEHFonts& Fonts, TFunctionRef<bool(const FVector&, FVector2f&)> ViewTo, bool bReduceFlash)
{
	Offscreen = OutsideView = Popping = Placeholders = Suppressed = 0;
	if (Bubbles.Num() == 0)
	{
		return;
	}
	const float Margin = 24.0f;
	const FVector2f ViewMin = P.VirtualMin + FVector2f(Margin, Margin);
	const FVector2f ViewMax = P.VirtualMax - FVector2f(Margin, Margin);
	struct FLaid
	{
		int32 Index;
		FVector2f Anchor;      // where the tail points (the speaker, or the edge toward it)
		FVector2f Pos, Size;   // the bubble's box
		bool bOff = false;
		TArray<FString> Rows;
		FSlateFontInfo Font;
		float Scale = 1.0f;
		float Alpha = 1.0f;
		bool bHidden = false;
	};
	TArray<FLaid> Laid;
	for (int32 i = 0; i < Bubbles.Num(); ++i)
	{
		const FBubble& B = Bubbles[i];
		FLaid L;
		L.Index = i;
		// The jump-out: a quick overshoot in size; with reduced flashing, a gentle fade instead.
		const float t = B.Age;
		if (!bReduceFlash && t < Tuning.PopSeconds && Tuning.PopSeconds > 0.0f)
		{
			const float u = t / Tuning.PopSeconds;
			L.Scale = 1.0f + 0.35f * FMath::Sin(u * PI) * (1.0f - u) + 0.15f * (1.0f - u);
			++Popping;
		}
		L.Alpha = bReduceFlash && Tuning.FadeIn > 0.0f ? FMath::Clamp(t / Tuning.FadeIn, 0.0f, 1.0f) : 1.0f;
		L.Alpha *= Tuning.FadeOut > 0.0f ? FMath::Clamp((B.Life - t) / Tuning.FadeOut, 0.0f, 1.0f) : 1.0f;
		const bool bShout = B.Kind == EEHLineKind::Hostile;
		L.Font = Fonts.Sized(bShout ? Fonts.Display : Fonts.BodyBold, Tuning.FontSize * (bShout ? 0.92f : 1.0f) * L.Scale);
		L.Rows = Wrap(B.Text, P, L.Font);
		FVector2f TextSize(0.0f, 0.0f);
		for (const FString& R : L.Rows)
		{
			const FVector2f S = P.Measure(R, L.Font);
			TextSize.X = FMath::Max(TextSize.X, S.X);
			TextSize.Y += S.Y;
		}
		const FVector2f Pad(16.0f, 9.0f);
		L.Size = TextSize + Pad * 2.0f + FVector2f(0.0f, B.bPlaceholder ? 22.0f : 0.0f);
		if (B.bPlayer)
		{
			// The player's own lines: a caption low on the screen, a little left of centre.
			L.Anchor = FVector2f(860.0f, P.VirtualMax.Y - 200.0f);
			L.Pos = L.Anchor - FVector2f(L.Size.X * 0.5f, L.Size.Y);
		}
		else
		{
			FVector2f At;
			const AActor* S = B.Speaker.Get();
			const FVector Head = S ? S->GetActorLocation() + FVector(0, 0, 70.0f) : FVector::ZeroVector;
			const bool bOn = S && ViewTo(Head, At) && At.X >= ViewMin.X && At.X <= ViewMax.X && At.Y >= ViewMin.Y && At.Y <= ViewMax.Y;
			if (!bOn)
			{
				// Off screen (or behind the camera): speak from the nearest edge in the speaker's direction.
				L.bOff = true;
				++Offscreen;
				FVector2f Dir = (S && ViewTo(Head, At)) ? (At - FVector2f(960.0f, 540.0f)) : FVector2f(0.0f, 1.0f);
				if (S && !ViewTo(Head, At))
				{
					// Behind: the projection is unusable; use the speaker's side relative to the view instead.
					Dir = FVector2f(1.0f, 0.6f);
				}
				Dir = Dir.GetSafeNormal();
				const FVector2f C(960.0f, 540.0f);
				const float Kx = Dir.X != 0.0f ? ((Dir.X > 0 ? ViewMax.X : ViewMin.X) - C.X) / Dir.X : 1e9f;
				const float Ky = Dir.Y != 0.0f ? ((Dir.Y > 0 ? ViewMax.Y : ViewMin.Y) - C.Y) / Dir.Y : 1e9f;
				At = C + Dir * FMath::Min(Kx, Ky);
			}
			L.Anchor = At;
			// Beside the head: above it and a little to the side, so the speaker stays visible.
			L.Pos = At + FVector2f(24.0f, -L.Size.Y - 36.0f);
		}
		Laid.Add(L);
	}
	// Keep every bubble inside the view, then push apart any that overlap (older ones keep their place).
	auto Clamp = [&](FLaid& L) {
		L.Pos.X = FMath::Clamp(L.Pos.X, ViewMin.X, FMath::Max(ViewMin.X, ViewMax.X - L.Size.X));
		L.Pos.Y = FMath::Clamp(L.Pos.Y, ViewMin.Y, FMath::Max(ViewMin.Y, ViewMax.Y - L.Size.Y));
	};
	auto Overlap = [](const FLaid& A, const FLaid& B, float Gap) {
		return A.Pos.X < B.Pos.X + B.Size.X + Gap && B.Pos.X < A.Pos.X + A.Size.X + Gap && A.Pos.Y < B.Pos.Y + B.Size.Y + Gap && B.Pos.Y < A.Pos.Y + A.Size.Y + Gap;
	};
	auto Free = [&](const FLaid& L, int32 Upto) {
		for (int32 j = 0; j < Upto; ++j)
		{
			if (!Laid[j].bHidden && Overlap(L, Laid[j], 8.0f))
			{
				return false;
			}
		}
		return true;
	};
	for (int32 i = 0; i < Laid.Num(); ++i)
	{
		FLaid& L = Laid[i];
		Clamp(L);
		if (Free(L, i))
		{
			continue;
		}
		// Older lines keep their places. Try beside each of them (above, below, left, right), nearest the wanted
		// place first; with no free place at all this frame the line waits (not drawn) rather than covering another.
		const FVector2f Want = L.Pos;
		TArray<FVector2f> Tries;
		for (int32 j = 0; j < i; ++j)
		{
			const FLaid& O = Laid[j];
			Tries.Add(FVector2f(Want.X, O.Pos.Y - L.Size.Y - 12.0f));
			Tries.Add(FVector2f(Want.X, O.Pos.Y + O.Size.Y + 12.0f));
			Tries.Add(FVector2f(O.Pos.X - L.Size.X - 12.0f, Want.Y));
			Tries.Add(FVector2f(O.Pos.X + O.Size.X + 12.0f, Want.Y));
			Tries.Add(FVector2f(O.Pos.X - L.Size.X - 12.0f, O.Pos.Y));
			Tries.Add(FVector2f(O.Pos.X + O.Size.X + 12.0f, O.Pos.Y));
		}
		Tries.Sort([&](const FVector2f& A, const FVector2f& B) { return FVector2f::DistSquared(A, Want) < FVector2f::DistSquared(B, Want); });
		bool bPlaced = false;
		for (const FVector2f& T : Tries)
		{
			FLaid Try = L;
			Try.Pos = T;
			Clamp(Try);
			if (Free(Try, i))
			{
				L.Pos = Try.Pos;
				bPlaced = true;
				break;
			}
		}
		if (!bPlaced)
		{
			L.bHidden = true;
			++Suppressed;
		}
	}
	int32 Pairs = 0;
	for (int32 i = 0; i < Laid.Num(); ++i)
	{
		if (Laid[i].bHidden)
		{
			continue;
		}
		for (int32 j = 0; j < i; ++j)
		{
			Pairs += !Laid[j].bHidden && Overlap(Laid[i], Laid[j], 0.0f) ? 1 : 0;
		}
		const FLaid& L = Laid[i];
		OutsideView += (L.Pos.X < P.VirtualMin.X || L.Pos.Y < P.VirtualMin.Y || L.Pos.X + L.Size.X > P.VirtualMax.X || L.Pos.Y + L.Size.Y > P.VirtualMax.Y) ? 1 : 0;
	}
	OverlapsSeen = FMath::Max(OverlapsSeen, Pairs);
	// Draw: ink outline, paper, a tail toward the speaker, the words; placeholders carry a visible tag.
	for (const FLaid& L : Laid)
	{
		if (L.bHidden)
		{
			continue;
		}
		const FBubble& B = Bubbles[L.Index];
		const float A = L.Alpha;
		const FLinearColor Paper = B.Kind == EEHLineKind::Hostile ? EHStyle::SRGB(246, 232, 226, A)
			: B.Kind == EEHLineKind::Warning ? EHStyle::SRGB(250, 238, 206, A)
			: B.Kind == EEHLineKind::Friendly ? EHStyle::SRGB(232, 244, 230, A)
			: EHStyle::SRGB(244, 242, 248, A);
		const FLinearColor Ink = B.Kind == EEHLineKind::Hostile ? EHStyle::SRGB(122, 18, 26, A)
			: B.Kind == EEHLineKind::Warning ? EHStyle::SRGB(120, 72, 8, A)
			: B.Kind == EEHLineKind::Friendly ? EHStyle::SRGB(30, 82, 44, A)
			: EHStyle::SRGB(22, 18, 30, A);
		const float Edge = B.Kind == EEHLineKind::Hostile ? 4.0f : 3.0f;
		// Tail: from the bubble's nearest bottom corner region to the anchor (never for captions).
		if (!B.bPlayer)
		{
			const FVector2f Base(FMath::Clamp(L.Anchor.X, L.Pos.X + 18.0f, L.Pos.X + L.Size.X - 18.0f), L.Anchor.Y < L.Pos.Y ? L.Pos.Y : L.Pos.Y + L.Size.Y);
			FVector2f Tip = L.bOff ? Base + (L.Anchor - Base).GetSafeNormal() * 26.0f : Base + (L.Anchor - Base) * 0.7f;
			if (FVector2f::Distance(Tip, Base) > 90.0f)
			{
				Tip = Base + (Tip - Base).GetSafeNormal() * 90.0f;
			}
			if (FVector2f::Distance(Tip, Base) > 6.0f)
			{
				// A wedge: ink fanned from a base 22 units wide to the tip, then paper inside it.
				const float Sgn = L.Anchor.Y < L.Pos.Y ? 1.0f : -1.0f;
				for (int32 k = -5; k <= 5; ++k)
				{
					P.Line({Base + FVector2f(k * 2.2f, Sgn * 2.0f), Tip}, Ink, 3.0f);
				}
				for (int32 k = -3; k <= 3; ++k)
				{
					P.Line({Base + FVector2f(k * 2.0f, Sgn * 3.0f), Base + (Tip - Base) * 0.78f}, Paper, 2.5f);
				}
			}
		}
		P.NextLayer();
		P.Round(L.Pos - FVector2f(Edge, Edge), L.Size + FVector2f(Edge, Edge) * 2.0f, Ink, 14.0f);
		P.NextLayer();
		P.Round(L.Pos, L.Size, Paper, 12.0f);
		P.NextLayer();
		float Y = L.Pos.Y + 12.0f;
		if (B.bPlaceholder)
		{
			P.Text(TEXT("PLACEHOLDER LINE"), FVector2f(L.Pos.X + 20.0f, Y), Fonts.Sized(Fonts.BodyBold, 15.0f), EHStyle::Alpha(Ink, 0.7f * A), 0.0f, 0.0f, false);
			Y += 22.0f;
		}
		for (const FString& R : L.Rows)
		{
			const FVector2f S = P.Text(R, FVector2f(L.Pos.X + L.Size.X * 0.5f, Y), L.Font, Ink, 0.5f, 0.0f, false);
			Y += S.Y;
		}
		P.NextLayer();
		P.NextLayer();
		Placeholders += B.bPlaceholder ? 1 : 0;
		if (B.Serial == Serial)
		{
			LastHeightPx = L.Size.Y / FMath::Max(0.01f, L.Scale) * P.Scale;
		}
	}
}
