#include "EHFists.h"

const TCHAR* EHFistActionName(EEHFistAction Action)
{
	switch (Action)
	{
	case EEHFistAction::Jab: return TEXT("Jab");
	case EEHFistAction::Straight: return TEXT("Straight");
	case EEHFistAction::Shove: return TEXT("Shove");
	case EEHFistAction::Fireball: return TEXT("Fireball");
	case EEHFistAction::IceWall: return TEXT("Ice Wall");
	default: return TEXT("None");
	}
}

FEHFistTuning::FEHFistTuning()
{
	// Starting points: the jab is quick and short, the straight slower, longer and twice as strong, the shove a
	// two-handed push that moves the target 2 m. Damage and push distance are the prototype draft's proposals.
	Jab = {6, 3, 10, 95.0f, 18.0f, 6.0f, 4, 0.0f, 0, 0.8f};
	Straight = {11, 3, 18, 115.0f, 18.0f, 12.0f, 7, 0.0f, 0, 0.7f};
	Shove = {9, 4, 18, 100.0f, 26.0f, 0.0f, 4, 200.0f, 15, 0.7f};
	// Casts: a short wind-up (casting next to a target is a risk the shove answers), one release frame, recovery.
	Fireball = {12, 1, 16, 0.0f, 0.0f, 0.0f, 0, 0.0f, 0, 0.6f};
	IceWall = {14, 1, 20, 0.0f, 0.0f, 0.0f, 0, 0.0f, 0, 0.5f};
}

const FEHStrikeDef& FEHFistTuning::Def(EEHFistAction Action) const
{
	switch (Action)
	{
	case EEHFistAction::Straight: return Straight;
	case EEHFistAction::Shove: return Shove;
	case EEHFistAction::Fireball: return Fireball;
	case EEHFistAction::IceWall: return IceWall;
	default: return Jab;
	}
}

bool FEHFistTuning::Load(const TSharedPtr<FJsonObject>& Obj, FString& OutError)
{
	if (!Obj.IsValid())
	{
		return true;
	}
	bool bOk = true;
	auto Num = [&](const TSharedPtr<FJsonObject>& O, const FString& Path, const TCHAR* Name, float& Out, float Min, float Max) {
		double V = 0.0;
		if (!O->TryGetNumberField(Name, V))
		{
			return;
		}
		if (V < Min || V > Max)
		{
			OutError = FString::Printf(TEXT("Data/firstperson.json: fists.%s%s = %g is outside %g..%g."), *Path, Name, V, Min, Max);
			bOk = false;
			return;
		}
		Out = static_cast<float>(V);
	};
	auto Int = [&](const TSharedPtr<FJsonObject>& O, const FString& Path, const TCHAR* Name, int32& Out, int32 Min, int32 Max) {
		float V = static_cast<float>(Out);
		Num(O, Path, Name, V, static_cast<float>(Min), static_cast<float>(Max));
		Out = FMath::RoundToInt(V);
	};
	auto Strike = [&](const TCHAR* Name, FEHStrikeDef& D) {
		const TSharedPtr<FJsonObject>* S = nullptr;
		if (!Obj->TryGetObjectField(Name, S))
		{
			return;
		}
		const FString P = FString(Name) + TEXT(".");
		Int(*S, P, TEXT("startup"), D.Startup, 1, 60);
		Int(*S, P, TEXT("active"), D.Active, 1, 30);
		Int(*S, P, TEXT("recovery"), D.Recovery, 0, 120);
		Num(*S, P, TEXT("reach"), D.Reach, 30, 300);
		Num(*S, P, TEXT("radius"), D.Radius, 2, 80);
		Num(*S, P, TEXT("damage"), D.Damage, 0, 1000);
		Int(*S, P, TEXT("hitstop"), D.Hitstop, 0, 20);
		Num(*S, P, TEXT("push"), D.Push, 0, 1000);
		Int(*S, P, TEXT("pushFrames"), D.PushFrames, 0, 120);
		Num(*S, P, TEXT("moveScale"), D.MoveScale, 0, 1);
	};
	Strike(TEXT("jab"), Jab);
	Strike(TEXT("straight"), Straight);
	Strike(TEXT("shove"), Shove);
	Strike(TEXT("fireballCast"), Fireball);
	Strike(TEXT("iceWallCast"), IceWall);
	Int(Obj, FString(), TEXT("bufferFrames"), BufferFrames, 0, 30);
	Int(Obj, FString(), TEXT("blockRaiseFrames"), BlockRaiseFrames, 1, 30);
	Int(Obj, FString(), TEXT("blockLowerFrames"), BlockLowerFrames, 0, 30);
	Num(Obj, FString(), TEXT("blockReduction"), BlockReduction, 0, 1);
	Num(Obj, FString(), TEXT("blockAngle"), BlockAngle, 10, 180);
	Num(Obj, FString(), TEXT("blockMoveScale"), BlockMoveScale, 0, 1);
	Num(Obj, FString(), TEXT("armsLinger"), ArmsLinger, 0, 5);
	return bOk;
}

FString FEHFistTuning::Describe() const
{
	auto D = [](const TCHAR* N, const FEHStrikeDef& S) {
		return FString::Printf(TEXT("%s %d/%d/%d reach=%.0f r=%.0f dmg=%.0f stop=%d push=%.0f/%d move=%.2f"), N, S.Startup, S.Active, S.Recovery, S.Reach, S.Radius, S.Damage, S.Hitstop, S.Push, S.PushFrames, S.MoveScale);
	};
	return FString::Printf(TEXT("%s; %s; %s; fireball cast %d/%d/%d move=%.2f; ice wall cast %d/%d/%d move=%.2f; buffer=%d block raise=%d lower=%d stop=%.0f%% front=%.0f move=%.2f linger=%.2f"),
		*D(TEXT("jab"), Jab), *D(TEXT("straight"), Straight), *D(TEXT("shove"), Shove), Fireball.Startup, Fireball.Active, Fireball.Recovery,
		Fireball.MoveScale, IceWall.Startup, IceWall.Active, IceWall.Recovery, IceWall.MoveScale, BufferFrames, BlockRaiseFrames, BlockLowerFrames,
		BlockReduction * 100.0f, BlockAngle, BlockMoveScale, ArmsLinger);
}

void FEHFists::Reset()
{
	Current = EEHFistAction::None;
	FrameIndex = 0;
	Hitstop = 0;
	bConnected = false;
	Buffered = EEHFistAction::None;
	BufferAge = 0;
	bBlockHeld = false;
	GuardFrames = 0;
	LowerFrames = 0;
	IdleFrames = 600;
}

void FEHFists::Press(EEHFistAction Action)
{
	if (Action == EEHFistAction::None || bBlockHeld)
	{
		return;
	}
	Buffered = Action;
	BufferAge = 0;
}

bool FEHFists::IsActiveFrame() const
{
	if (Current == EEHFistAction::None)
	{
		return false;
	}
	const FEHStrikeDef& D = Tuning.Def(Current);
	return FrameIndex >= D.Startup && FrameIndex < D.Startup + D.Active;
}

float FEHFists::GuardLevel() const
{
	const float Raise = FMath::Clamp(static_cast<float>(GuardFrames) / FMath::Max(1, Tuning.BlockRaiseFrames), 0.0f, 1.0f);
	if (LowerFrames > 0)
	{
		return static_cast<float>(LowerFrames) / FMath::Max(1, Tuning.BlockLowerFrames);
	}
	return bBlockHeld ? Raise : 0.0f;
}

float FEHFists::MoveScale() const
{
	if (Current != EEHFistAction::None)
	{
		return Tuning.Def(Current).MoveScale;
	}
	return (bBlockHeld || LowerFrames > 0) ? Tuning.BlockMoveScale : 1.0f;
}

bool FEHFists::CanStart(EEHFistAction Next) const
{
	if (bBlockHeld || LowerFrames > 0)
	{
		return false;
	}
	if (Current == EEHFistAction::None)
	{
		return true;
	}
	// Once the current technique's active frames are over, hit or miss, its recovery can hand over: the jab to the
	// straight, any strike to a cast and any cast to a strike, so punches and spells flow into each other.
	const FEHStrikeDef& D = Tuning.Def(Current);
	if (FrameIndex < D.Startup + D.Active)
	{
		return false;
	}
	return (Current == EEHFistAction::Jab && Next == EEHFistAction::Straight) || EHIsSpell(Current) != EHIsSpell(Next);
}

void FEHFists::Start(EEHFistAction Next, TArray<FEHFistEvent>& OutEvents)
{
	if (Current != EEHFistAction::None)
	{
		OutEvents.Add({FEHFistEvent::EKind::End, Current, 0});
	}
	Current = Next;
	FrameIndex = 0;
	bConnected = false;
	IdleFrames = 0;
	OutEvents.Add({FEHFistEvent::EKind::Start, Current, 0});
}

void FEHFists::OnContact(int32 Frames)
{
	if (Current != EEHFistAction::None)
	{
		Hitstop = Frames >= 0 ? Frames : Tuning.Def(Current).Hitstop;
	}
}

void FEHFists::Step(TArray<FEHFistEvent>& OutEvents)
{
	if (Hitstop > 0)
	{
		--Hitstop;
		return;
	}
	// Guard: rises while held and nothing else runs; lowering blocks techniques for a few frames.
	if (bBlockHeld && Current == EEHFistAction::None)
	{
		if (GuardFrames == 0)
		{
			OutEvents.Add({FEHFistEvent::EKind::BlockUp, EEHFistAction::None, 0});
		}
		GuardFrames = FMath::Min(GuardFrames + 1, Tuning.BlockRaiseFrames);
		LowerFrames = 0;
		IdleFrames = 0;
		Buffered = EEHFistAction::None;
	}
	else if (!bBlockHeld && GuardFrames > 0)
	{
		GuardFrames = 0;
		LowerFrames = Tuning.BlockLowerFrames;
		OutEvents.Add({FEHFistEvent::EKind::BlockDown, EEHFistAction::None, 0});
	}
	else if (LowerFrames > 0)
	{
		--LowerFrames;
		IdleFrames = 0;
	}

	// The current technique advances; it ends after its recovery.
	if (Current != EEHFistAction::None)
	{
		const FEHStrikeDef& D = Tuning.Def(Current);
		if (IsActiveFrame())
		{
			OutEvents.Add({FEHFistEvent::EKind::Active, Current, FrameIndex - D.Startup});
		}
		++FrameIndex;
		if (FrameIndex >= D.Total())
		{
			OutEvents.Add({FEHFistEvent::EKind::End, Current, 0});
			Current = EEHFistAction::None;
			FrameIndex = 0;
			IdleFrames = 0;
		}
	}
	else if (!bBlockHeld && LowerFrames == 0)
	{
		++IdleFrames;
	}

	// A buffered press starts as soon as it is allowed, or expires.
	if (Buffered != EEHFistAction::None)
	{
		if (CanStart(Buffered))
		{
			const EEHFistAction Next = Buffered;
			Buffered = EEHFistAction::None;
			if (!Gate || Gate(Next))
			{
				Start(Next, OutEvents);
			}
			else
			{
				OutEvents.Add({FEHFistEvent::EKind::Refused, Next, 0});
			}
		}
		else if (++BufferAge > Tuning.BufferFrames)
		{
			Buffered = EEHFistAction::None;
		}
	}
}
