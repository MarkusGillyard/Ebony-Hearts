// Comic-book combat text (milestone 7; EHCombatText.h): what makes the wolves and the player speak.
#include "EHGameDirector.h"
#include "EHWolf.h"
#include "Engine/World.h"

void AEHGameDirector::CombatTextEvents(int32 i, EEHWolfState WS, EEHWolfState Last)
{
	// A wolf's state changed. It speaks in its alignment's voice: hostile trash talk, a neutral warning, or a friendly
	// line (EHAlignment.h; a provoked wolf is hostile whatever the band).
	AEHWolf* W = FPWolves.IsValidIndex(i) ? FPWolves[i].Get() : nullptr;
	if (W == nullptr || W->IsDead())
	{
		return;
	}
	const bool bHostile = W->IsHostile();
	const EEHAlignBand B = EHAlign::Band(FPAlignment);
	const float Now = GetWorld()->GetTimeSeconds();
	const TCHAR* Event = nullptr;
	EEHLineKind Kind = EEHLineKind::Hostile;
	switch (WS)
	{
	case EEHWolfState::BiteWindup:
	case EEHWolfState::LungeWindup:
		Event = TEXT("wolf.hostile.attack");
		break;
	case EEHWolfState::Hitstun:
		Event = bHostile ? TEXT("wolf.hostile.hurt") : (B == EEHAlignBand::Good ? TEXT("wolf.friendly.hurt") : TEXT("wolf.warning.hurt"));
		Kind = bHostile ? EEHLineKind::Hostile : (B == EEHAlignBand::Good ? EEHLineKind::Friendly : EEHLineKind::Warning);
		break;
	case EEHWolfState::Disengage:
		Event = TEXT("wolf.warning.threat");
		Kind = EEHLineKind::Warning;
		break;
	case EEHWolfState::Protect:
		Event = TEXT("wolf.friendly.protect");
		Kind = EEHLineKind::Friendly;
		break;
	case EEHWolfState::Guarding:
		Event = TEXT("wolf.warning.guard");
		Kind = EEHLineKind::Warning;
		break;
	case EEHWolfState::Hostile:
		if (Last == EEHWolfState::Calm || Last == EEHWolfState::Disengage)
		{
			Event = TEXT("wolf.hostile.notice");
		}
		break;
	default:
		break;
	}
	if (Event && CombatText.Offer(Event, W, Kind, Now))
	{
		AutoLogLine(FString::Printf(TEXT("fp text wolf %d %s: %s"), i, EHLineKindName(Kind), *CombatText.LastText));
	}
}

void AEHGameDirector::CombatTextNearness(float Now)
{
	// Calm wolves remark on the player coming close: a friendly greeting (good) or a warning to keep away (neutral).
	// Asked at most every few seconds per wolf, so the chance is per remark, not per frame.
	if (FPPlayer == nullptr)
	{
		return;
	}
	FPWolfIdleTalkAt.SetNum(FPWolves.Num());
	const EEHAlignBand B = EHAlign::Band(FPAlignment);
	if (B == EEHAlignBand::Evil)
	{
		return;
	}
	for (int32 i = 0; i < FPWolves.Num(); ++i)
	{
		AEHWolf* W = FPWolves[i];
		if (W == nullptr || W->IsDead() || W->IsHostile() || Now < FPWolfIdleTalkAt[i])
		{
			continue;
		}
		const float D = FVector::Dist2D(W->GetActorLocation(), FPPlayer->GetActorLocation());
		const bool bGood = B == EEHAlignBand::Good;
		if (D <= (bGood ? 450.0f : 520.0f))
		{
			FPWolfIdleTalkAt[i] = Now + 6.0f;
			const EEHLineKind Kind = bGood ? EEHLineKind::Friendly : EEHLineKind::Warning;
			if (CombatText.Offer(bGood ? TEXT("wolf.friendly.near") : TEXT("wolf.warning.near"), W, Kind, Now))
			{
				AutoLogLine(FString::Printf(TEXT("fp text wolf %d %s: %s"), i, EHLineKindName(Kind), *CombatText.LastText));
			}
		}
	}
}

bool AEHGameDirector::CombatTextField(const FString& Field, float& V) const
{
	const FEHCombatText& C = CombatText;
	if (Field == TEXT("ct_visible")) { V = static_cast<float>(C.Visible()); return true; }
	if (Field == TEXT("ct_shown")) { V = static_cast<float>(C.Shown); return true; }
	if (Field == TEXT("ct_friendly")) { V = static_cast<float>(C.ShownByKind[0]); return true; }
	if (Field == TEXT("ct_warning")) { V = static_cast<float>(C.ShownByKind[1]); return true; }
	if (Field == TEXT("ct_hostile")) { V = static_cast<float>(C.ShownByKind[2]); return true; }
	if (Field == TEXT("ct_player")) { V = static_cast<float>(C.ShownByKind[3]); return true; }
	if (Field == TEXT("ct_max_visible")) { V = static_cast<float>(C.MaxVisibleSeen); return true; }
	if (Field == TEXT("ct_overlaps")) { V = static_cast<float>(C.OverlapsSeen); return true; }
	if (Field == TEXT("ct_offscreen")) { V = static_cast<float>(C.Offscreen); return true; }
	if (Field == TEXT("ct_outside")) { V = static_cast<float>(C.OutsideView); return true; }
	if (Field == TEXT("ct_popping")) { V = static_cast<float>(C.Popping); return true; }
	if (Field == TEXT("ct_placeholders")) { V = static_cast<float>(C.Placeholders); return true; }
	if (Field == TEXT("ct_height")) { V = C.LastHeightPx; return true; }
	if (Field == TEXT("ct_suppressed")) { V = static_cast<float>(C.Suppressed); return true; }
	if (Field == TEXT("ct_refused")) { V = static_cast<float>(C.Refused); return true; }
	return false;
}
