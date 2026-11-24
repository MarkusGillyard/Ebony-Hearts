// The Chapel wolves as a pack (milestone 6; EHPack.h): spawning one to four wolves, taking turns, the one-on-one
// when the player is overwhelmed, and re-planning paths when an Ice Wall rises or melts.
#include "EHGameDirector.h"
#include "EHWolf.h"
#include "Engine/World.h"

void AEHGameDirector::SpawnPack(int32 Count)
{
	const FEHPackTuning& T = FPTuning.Pack;
	Count = FMath::Clamp(Count, 1, FMath::Min(4, FMath::Max(1, T.Spawns.Num())));
	while (FPWolves.Num() > Count)
	{
		if (AEHWolf* W = FPWolves.Pop())
		{
			W->Destroy();
		}
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
	while (FPWolves.Num() < Count)
	{
		const int32 i = FPWolves.Num();
		FEHWolfTuning WT = FPTuning.Wolf;
		if (T.Spawns.IsValidIndex(i))
		{
			WT.Spawn = WT.Home = T.Spawns[i].At;
			WT.HomeYaw = T.Spawns[i].Yaw;
		}
		AEHWolf* W = GetWorld()->SpawnActor<AEHWolf>(AEHWolf::StaticClass(), FTransform(FRotator(0, WT.HomeYaw, 0), WT.Spawn + FVector(0, 0, 60.0f)), Params);
		if (W == nullptr)
		{
			break;
		}
		W->SetAlignment(FPAlignment);
		W->Setup(WT, FPPlayer, FPDummy);
		FPWolves.Add(W);
	}
	FPWolf = FPWolves.Num() > 0 ? FPWolves[0] : nullptr;
	FPWolvesLastState.Init(EEHWolfState::Calm, FPWolves.Num());
	ResetPack();
	AutoLogLine(FString::Printf(TEXT("fp pack %d wolves"), FPWolves.Num()));
}

void AEHGameDirector::ResetPack()
{
	PackWaiting.Init(0.0f, FPWolves.Num());
	PackHolder = -1;
	PackHolderAttacks = 0;
	PackHolderSince = 0.0f;
	bPackOverwhelmed = false;
	bOneOnOne = false;
	OneOnOneLeft = 0.0f;
	FPHurtTimes.Reset();
	PackRepathAt.Reset();
	PackPasses = PackMaxAttackers = PackOneOnOnes = 0;
}

void AEHGameDirector::ResetWolves()
{
	for (AEHWolf* W : FPWolves)
	{
		if (W)
		{
			W->ResetWolf();
		}
	}
	ResetPack();
}

bool AEHGameDirector::WolfFighting(const AEHWolf* W) const
{
	// In the fight: alive, hostile and on the Chapel's floor with the player, not frozen. (A provoked wolf guarding the
	// edge while the player is outside is not fighting.)
	return W && !W->IsDead() && W->IsHostile() && !W->IsFrozen() && W->GetState() != EEHWolfState::Guarding;
}

AEHWolf* AEHGameDirector::NearestLiveWolf(const FVector& To, float Within) const
{
	AEHWolf* Best = nullptr;
	float BestD = Within;
	for (AEHWolf* W : FPWolves)
	{
		if (W && !W->IsDead())
		{
			const float D = FVector::Dist2D(W->GetActorLocation(), To);
			if (D <= BestD)
			{
				BestD = D;
				Best = W;
			}
		}
	}
	return Best;
}

void AEHGameDirector::PackRepathSoon()
{
	// The navigation mesh changes when an Ice Wall rises or starts to melt; its tiles rebuild over the next moments. Each
	// wolf re-plans now and twice more as the mesh catches up, so none follows an old path into the wall or stalls.
	const float Now = GetWorld()->GetTimeSeconds();
	for (AEHWolf* W : FPWolves)
	{
		if (W)
		{
			W->RequestRepath();
		}
	}
	PackRepathAt.Add(Now + 0.4f);
	PackRepathAt.Add(Now + 1.2f);
}

void AEHGameDirector::PassTurn(const TArray<int32>& Fighting, const TCHAR* Why)
{
	int32 Next = -1;
	float Longest = -1.0f;
	for (int32 i : Fighting)
	{
		if (i != PackHolder && PackWaiting[i] > Longest)
		{
			Longest = PackWaiting[i];
			Next = i;
		}
	}
	if (Next < 0)
	{
		Next = Fighting.Contains(PackHolder) ? PackHolder : -1;
	}
	if (Next != PackHolder)
	{
		++PackPasses;
		AutoLogLine(FString::Printf(TEXT("fp pack turn: wolf %d -> wolf %d (%s)"), PackHolder, Next, Why));
	}
	PackHolder = Next;
	if (PackHolder >= 0)
	{
		PackWaiting[PackHolder] = 0.0f;
		PackHolderAttacks = FPWolves[PackHolder]->AttacksStarted();
		PackHolderSince = GetWorld()->GetTimeSeconds();
	}
}

void AEHGameDirector::TickPack(float DeltaSeconds)
{
	if (FPPlayer == nullptr || FPWolves.Num() == 0)
	{
		return;
	}
	const FEHPackTuning& T = FPTuning.Pack;
	const float Now = GetWorld()->GetTimeSeconds();
	for (int32 i = PackRepathAt.Num() - 1; i >= 0; --i)
	{
		if (Now >= PackRepathAt[i])
		{
			for (AEHWolf* W : FPWolves)
			{
				if (W)
				{
					W->RequestRepath();
				}
			}
			PackRepathAt.RemoveAt(i);
		}
	}
	FPHurtTimes.RemoveAll([&](double At) { return At < Now - T.HitsWindow; });
	TArray<int32> Fighting;
	int32 Close = 0;
	for (int32 i = 0; i < FPWolves.Num(); ++i)
	{
		if (WolfFighting(FPWolves[i]))
		{
			Fighting.Add(i);
			Close += FVector::Dist2D(FPWolves[i]->GetActorLocation(), FPPlayer->GetActorLocation()) <= T.SurroundRadius ? 1 : 0;
		}
	}
	// Overwhelmed (the creator's rule): Health below half, or surrounded, or hit again and again.
	const bool bWas = bPackOverwhelmed;
	bPackOverwhelmed = Fighting.Num() >= 2 && (FPPlayer->HealthFraction() < T.OverwhelmedHealth || Close >= T.SurroundCount || FPHurtTimes.Num() >= T.HitsCount);
	if (bPackOverwhelmed && !bWas)
	{
		FString Who;
		for (int32 i : Fighting)
		{
			Who += FString::Printf(TEXT(" w%d=%.0fcm/%s/%d"), i, FVector::Dist2D(FPWolves[i]->GetActorLocation(), FPPlayer->GetActorLocation()),
				EHWolfStateName(FPWolves[i]->GetState()), static_cast<int32>(FPWolves[i]->GetPackRole()));
		}
		AutoLogLine(FString::Printf(TEXT("fp pack sees the player overwhelmed (health %.0f%%, %d close, %d hits;%s)"), FPPlayer->HealthFraction() * 100.0f, Close, FPHurtTimes.Num(), *Who));
	}
	if (bPackOverwhelmed)
	{
		if (!bOneOnOne)
		{
			bOneOnOne = true;
			++PackOneOnOnes;
			AutoLogLine(TEXT("fp pack allows a one-on-one"));
		}
		OneOnOneLeft = T.OneOnOneLinger;
	}
	else if (bOneOnOne)
	{
		OneOnOneLeft -= DeltaSeconds;
		if (OneOnOneLeft <= 0.0f || Fighting.Num() < 2)
		{
			bOneOnOne = false;
			AutoLogLine(TEXT("fp pack takes turns again"));
		}
	}
	if (Fighting.Num() < 2)
	{
		// A lone wolf (or none) in the fight: no turns to keep.
		for (AEHWolf* W : FPWolves)
		{
			if (W)
			{
				const EEHPackRole Role = FPWolves.Num() > 1 && W->IsFrozen() ? EEHPackRole::Waiting : EEHPackRole::Free;
				W->SetPackRole(Role, T.HoldBackRadius, T.WaitRadius);
			}
		}
		PackHolder = -1;
		return;
	}
	if (!Fighting.Contains(PackHolder))
	{
		// A wolf may already be attacking when another wolf thaws and the pack reforms.
		for (int32 i : Fighting)
		{
			if (FPWolves[i]->IsAttacking())
			{
				PackHolder = i;
				PackWaiting[i] = 0.0f;
				PackHolderAttacks = FPWolves[i]->AttacksStarted() - 1;
				PackHolderSince = Now;
				break;
			}
		}
	}
	if (!Fighting.Contains(PackHolder))
	{
		PassTurn(Fighting, PackHolder < 0 ? TEXT("the fight starts") : TEXT("out of the fight"));
	}
	else
	{
		AEHWolf* H = FPWolves[PackHolder];
		const bool bFinished = H->AttacksStarted() > PackHolderAttacks && !H->IsAttacking();
		const bool bTimedOut = !H->IsAttacking() && H->SecondsSinceAttack() > T.TurnTimeout && Now - PackHolderSince > T.TurnTimeout;
		if (bFinished && !bOneOnOne)
		{
			PassTurn(Fighting, TEXT("attacked"));
		}
		else if (bTimedOut)
		{
			PassTurn(Fighting, TEXT("could not get at the player"));
		}
	}
	int32 Attacking = 0;
	for (int32 i = 0; i < FPWolves.Num(); ++i)
	{
		AEHWolf* W = FPWolves[i];
		if (W == nullptr)
		{
			continue;
		}
		if (!Fighting.Contains(i))
		{
			const EEHPackRole Role = W->IsFrozen() ? EEHPackRole::Waiting : EEHPackRole::Free;
			W->SetPackRole(Role, T.HoldBackRadius, T.WaitRadius);
			continue;
		}
		W->SetPackRole(i == PackHolder ? EEHPackRole::Attacker : (bOneOnOne ? EEHPackRole::HoldBack : EEHPackRole::Waiting), T.HoldBackRadius, T.WaitRadius);
		if (i != PackHolder)
		{
			PackWaiting[i] += DeltaSeconds;
		}
		Attacking += W->IsAttacking() ? 1 : 0;
	}
	PackMaxAttackers = FMath::Max(PackMaxAttackers, Attacking);
}

bool AEHGameDirector::PackField(const FString& Field, float& V) const
{
	auto Sum = [this](TFunctionRef<int32(const AEHWolf*)> F) {
		int32 N = 0;
		for (const AEHWolf* W : FPWolves)
		{
			N += W ? F(W) : 0;
		}
		return static_cast<float>(N);
	};
	if (Field == TEXT("wolves")) { V = static_cast<float>(FPWolves.Num()); return true; }
	if (Field == TEXT("wolves_alive")) { V = Sum([](const AEHWolf* W) { return W->IsDead() ? 0 : 1; }); return true; }
	if (Field == TEXT("wolves_fighting")) { V = Sum([this](const AEHWolf* W) { return WolfFighting(W) ? 1 : 0; }); return true; }
	if (Field == TEXT("overwhelmed")) { V = bPackOverwhelmed ? 1.0f : 0.0f; return true; }
	if (Field == TEXT("one_on_one")) { V = bOneOnOne ? 1.0f : 0.0f; return true; }
	if (Field == TEXT("one_on_ones")) { V = static_cast<float>(PackOneOnOnes); return true; }
	if (Field == TEXT("pack_passes")) { V = static_cast<float>(PackPasses); return true; }
	if (Field == TEXT("pack_max_attackers")) { V = static_cast<float>(PackMaxAttackers); return true; }
	if (Field == TEXT("pack_holder")) { V = static_cast<float>(PackHolder); return true; }
	if (Field == TEXT("pack_attacks")) { V = Sum([](const AEHWolf* W) { return W->AttacksStarted(); }); return true; }
	if (Field == TEXT("pack_repaths")) { V = Sum([](const AEHWolf* W) { return W->Repaths(); }); return true; }
	if (Field == TEXT("pack_repath_pending")) { V = static_cast<float>(PackRepathAt.Num()); return true; }
	if (Field == TEXT("pack_stuck")) { V = Sum([](const AEHWolf* W) { return W->StuckRepaths(); }); return true; }
	if (Field == TEXT("pack_hits")) { V = static_cast<float>(FPHurtTimes.Num()); return true; }
	if (Field == TEXT("pack_holdback_min"))
	{
		// The nearest a standing-back wolf comes to the player (999999 when none stands back).
		V = 999999.0f;
		for (const AEHWolf* W : FPWolves)
		{
			if (W && FPPlayer && W->GetPackRole() == EEHPackRole::HoldBack)
			{
				V = FMath::Min(V, FVector::Dist2D(W->GetActorLocation(), FPPlayer->GetActorLocation()));
			}
		}
		return true;
	}
	return false;
}
