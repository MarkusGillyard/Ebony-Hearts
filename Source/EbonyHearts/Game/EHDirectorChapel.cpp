// The Drowned Chapel's interactions and prayer (interior stage 2). What the player looks at within reach and in plain
// sight shows a prompt; Interact uses it: most things answer with a short placeholder text, the kneeler kneels and
// prays. While praying the player stays down (no walking, techniques or spells; looking is slowed) and the alignment
// meter shows: white for good through grey to black for evil, with a mark at the player's tier. It names no tier: the
// game never tells the player which actions were good or evil. Interact again, or walking, jumping or striking, rises.
#include "Camera/CameraComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "EHGameDirector.h"
#include "EHUIStyle.h"
#include "EHWolf.h"
#include "Engine/World.h"

void AEHGameDirector::UpdateChapel(FEHFirstPersonInput& In, float DeltaSeconds)
{
	const FEHChapelTuning& T = FPTuning.Chapel;
	const bool bInteract = bFPInteractPressed;
	bFPInteractPressed = false;
	PrayAlpha = FMath::FInterpConstantTo(PrayAlpha, bPraying ? 1.0f : 0.0f, DeltaSeconds, bPraying ? 1.6f : 4.0f);
	if (bPraying)
	{
		const bool bRise = bInteract || In.Move.SizeSquared() > 0.09f || In.bJumpPressed || In.FistPress != EEHFistAction::None;
		if (bRise)
		{
			// The press that rises only rises: standing up takes a moment before anything else starts.
			EndPrayer(bInteract ? TEXT("interact") : TEXT("moved"));
			RiseBlockLeft = 0.25f;
			In.FistPress = EEHFistAction::None;
			In.bJumpPressed = false;
			return;
		}
		else
		{
			PrayerSeconds += DeltaSeconds;
			In.Move = FVector2D::ZeroVector;
			In.Look *= T.PrayLookScale;
			if (PrayerSeconds < T.PrayTurnSeconds && FPPlayer)
			{
				// Kneeling turns the view, unhurried, toward the altar and the rose window.
				const FRotator Want = (T.PrayLookAt - FPPlayer->Camera()->GetComponentLocation()).Rotation();
				const FRotator Now = FPPlayer->GetControlRotation();
				const float K = FMath::Clamp(DeltaSeconds * 4.0f / T.PrayTurnSeconds, 0.0f, 1.0f);
				In.Look.X += FRotator::NormalizeAxis(Want.Yaw - Now.Yaw) * K;
				In.Look.Y += FRotator::NormalizeAxis(Want.Pitch - FRotator::NormalizeAxis(Now.Pitch)) * K;
			}
			In.bBlock = false;
			In.bSprint = false;
			In.bCrouch = true;
			FPInteractFocus = -1;
			return;
		}
	}
	if (RiseBlockLeft > 0.0f)
	{
		RiseBlockLeft -= DeltaSeconds;
		In.FistPress = EEHFistAction::None;
		In.bJumpPressed = false;
	}
	// What the player looks at: the nearest interactable whose point lies within its radius of the line of sight,
	// within reach and not behind a wall.
	FPInteractFocus = -1;
	if (FPPlayer && !bSpellSelect)
	{
		const FVector Eye = FPPlayer->Camera()->GetComponentLocation();
		const FVector Fwd = FPPlayer->Camera()->GetForwardVector();
		float Best = T.Reach;
		for (int32 i = 0; i < T.Interactables.Num(); ++i)
		{
			const FEHInteractable& E = T.Interactables[i];
			const FVector V = E.At - Eye;
			const float Along = FVector::DotProduct(V, Fwd);
			if (Along < 0.0f || Along > Best || (V - Fwd * Along).Size() > E.Radius)
			{
				continue;
			}
			FHitResult Hit;
			FCollisionQueryParams Params(TEXT("EHInteract"), false, FPPlayer);
			if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, E.At, ECC_Visibility, Params) && Hit.Distance < V.Size() - E.Radius * 1.5f)
			{
				continue;
			}
			Best = Along;
			FPInteractFocus = i;
		}
		// A calm wolf looked at within reach can be talked to (it is bigger than most things, so a wider reach).
		FPWolfFocus = -1;
		for (int32 i = 0; i < FPWolves.Num(); ++i)
		{
			const AEHWolf* W = FPWolves[i];
			if (W == nullptr || W->IsDead() || !W->IsCalmLike() || W->GetState() == EEHWolfState::Sleep)
			{
				continue;
			}
			const FVector V = W->LockOnPoint() - Eye;
			const float Along = FVector::DotProduct(V, Fwd);
			if (Along < 0.0f || Along > Best + 80.0f || (V - Fwd * Along).Size() > 110.0f)
			{
				continue;
			}
			Best = Along - 80.0f;
			FPWolfFocus = i;
			FPInteractFocus = -1;
		}
	}
	if (bInteract && FPWolfFocus >= 0)
	{
		TalkToWolf(FPWolfFocus);
	}
	if (bInteract && FPInteractFocus >= 0)
	{
		const FEHInteractable& E = T.Interactables[FPInteractFocus];
		AutoLogLine(FString::Printf(TEXT("fp interact %s"), *E.Id));
		if (E.bPray)
		{
			BeginPrayer();
			In.Move = FVector2D::ZeroVector;
			In.bCrouch = true;
		}
		else
		{
			FPMessage = E.Text;
			FPMessageLeft = T.MessageSeconds;
			FPMessageFrom = FPPlayer->FeetLocation();
			++FPMessages;
		}
	}
	if (FPMessageLeft > 0.0f)
	{
		FPMessageLeft -= DeltaSeconds;
		if (FPPlayer && FVector::Dist2D(FPPlayer->FeetLocation(), FPMessageFrom) > T.MessageWalkAway)
		{
			FPMessageLeft = FMath::Min(FPMessageLeft, 0.3f);
		}
	}
}

void AEHGameDirector::BeginPrayer()
{
	if (bPraying)
	{
		return;
	}
	if (bSpellSelect)
	{
		CloseSpellSelect(false);
	}
	bPraying = true;
	PrayerSeconds = 0.0f;
	++FPPrayers;
	FPMessageLeft = 0.0f;
	bFPSprintToggled = false;
	AutoLogLine(FString::Printf(TEXT("fp pray begin alignment=%s"), EHAlign::Name(FPAlignment)));
}

void AEHGameDirector::EndPrayer(const TCHAR* Why)
{
	if (!bPraying)
	{
		return;
	}
	bPraying = false;
	bFPCrouchToggled = false;
	AutoLogLine(FString::Printf(TEXT("fp pray end (%s) after %.1fs"), Why, PrayerSeconds));
}

void AEHGameDirector::PaintChapel(FEHPainter& P)
{
	const FEHChapelTuning& T = FPTuning.Chapel;
	const bool bPad = FPDevice >= EHDeviceGamepadBase;
	const EEHBindingSet Set = bPad ? EEHBindingSet::FPController : EEHBindingSet::FPKeyboard;
	const FKey Key = Settings.Bindings.Get(Set, EEHAction::FPInteract, 0);
	const FString KeyText = Key.IsValid() ? KeyName(Set, Key) : FString(TEXT("Interact (unbound)"));
	if (FPWolfFocus >= 0 && !bPraying && SpellSelectAlpha < 0.01f)
	{
		P.Text(FString::Printf(TEXT("%s   Talk to the wolf"), *KeyText), FVector2f(960.0f, 620.0f), Fonts.Sized(Fonts.BodyMedium, 24), EHStyle::Alpha(EHStyle::TextPrimary, 0.85f), 0.5f, 0.5f);
	}
	if (FPInteractFocus >= 0 && FPInteractFocus < T.Interactables.Num() && !bPraying && SpellSelectAlpha < 0.01f)
	{
		// The prompt: below the centre of the view, quiet, like the other readouts.
		const FString Line = FString::Printf(TEXT("%s   %s"), *KeyText, *T.Interactables[FPInteractFocus].Prompt);
		P.Text(Line, FVector2f(960.0f, 620.0f), Fonts.Sized(Fonts.BodyMedium, 24), EHStyle::Alpha(EHStyle::TextPrimary, 0.85f), 0.5f, 0.5f);
	}
	if (FPMessageLeft > 0.0f && !FPMessage.IsEmpty())
	{
		const float A = FMath::Clamp(FPMessageLeft / 0.3f, 0.0f, 1.0f);
		P.Rect(FVector2f(960.0f - 520.0f, 838.0f), FVector2f(1040.0f, 64.0f), EHStyle::Alpha(EHStyle::Abyss, 0.55f * A));
		P.Text(FPMessage, FVector2f(960.0f, 870.0f), Fonts.Sized(Fonts.Body, 22), EHStyle::Alpha(EHStyle::TextPrimary, 0.9f * A), 0.5f, 0.5f);
	}
	if (PrayAlpha > 0.01f)
	{
		// The alignment meter: white (good) on the left through grey (neutral) to black (evil) on the right, in nine
		// steps, on a dark band so the white end and the black end both read; a mark above the player's tier.
		const float A = PrayAlpha;
		const float W = 720.0f;
		const float H = 14.0f;
		const FVector2f Pos(960.0f - W * 0.5f, 880.0f);
		P.Fill(FLinearColor(0, 0, 0, 0.25f * A));
		P.Rect(Pos - FVector2f(12.0f, 12.0f), FVector2f(W + 24.0f, H + 24.0f), FLinearColor(0.16f, 0.17f, 0.2f, 0.7f * A));
		const int32 N = EHAlign::Count;
		const float Seg = W / static_cast<float>(N);
		for (int32 i = 0; i < N; ++i)
		{
			const float V = 1.0f - static_cast<float>(i) / static_cast<float>(N - 1);
			const float L = FMath::Lerp(0.004f, 0.92f, V * V);
			P.Rect(FVector2f(Pos.X + Seg * i + 1.0f, Pos.Y), FVector2f(Seg - 2.0f, H), FLinearColor(L, L, L, A));
		}
		const float MarkX = Pos.X + Seg * (static_cast<float>(FMath::Clamp(FPAlignment, 0, N - 1)) + 0.5f);
		P.Rect(FVector2f(MarkX - 2.0f, Pos.Y - 22.0f), FVector2f(4.0f, 16.0f), FLinearColor(0.85f, 0.72f, 0.45f, A));
		P.Rect(FVector2f(MarkX - 2.0f, Pos.Y + H + 6.0f), FVector2f(4.0f, 16.0f), FLinearColor(0.85f, 0.72f, 0.45f, A));
		P.Text(FString::Printf(TEXT("%s   Rise"), *KeyText), FVector2f(960.0f, Pos.Y + 70.0f), Fonts.Sized(Fonts.Body, 20),
			EHStyle::Alpha(EHStyle::TextSecondary, 0.7f * A), 0.5f, 0.5f);
	}
}

void AEHGameDirector::InitWorldClock()
{
	FPClockHours = FPTuning.Clock.StartHour;
	FPClockApplied = -1.0;
	// The window light: the map's shadow-casting directional light (the moon through the glass). A stationary light,
	// so its colour and strength change with the hour but it does not move.
	for (TActorIterator<ADirectionalLight> It(GetWorld()); It; ++It)
	{
		ULightComponent* L = It->GetLightComponent();
		if (L && L->CastShadows && !SkyLightComp.IsValid())
		{
			SkyLightComp = L;
			SkyBaseIntensity = L->Intensity;
		}
	}
	SkyFills.Reset();
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (It->ActorHasTag(TEXT("EHSkyFill")))
		{
			for (ULightComponent* L : TInlineComponentArray<ULightComponent*>(*It))
			{
				FSkyFill& F = SkyFills.AddDefaulted_GetRef();
				F.Light = L;
				F.BaseIntensity = L->Intensity;
				F.BaseColor = L->GetLightColor();
			}
		}
	}
	ClockNightColor = FPTuning.Clock.Keys.Num() > 0 ? FPTuning.Clock.Keys[0].Color : FLinearColor::White;
	for (TActorIterator<AExponentialHeightFog> It(GetWorld()); It; ++It)
	{
		if (UExponentialHeightFogComponent* Fog = It->GetComponent())
		{
			FogComp = Fog;
			FogBase = Fog->FogInscatteringLuminance;
			break;
		}
	}
	// The glass glows with the hour: one dynamic instance per glass material, shared by every pane that uses it.
	TMap<UMaterialInterface*, UMaterialInstanceDynamic*> Mids;
	for (TObjectIterator<UStaticMeshComponent> It; It; ++It)
	{
		if (It->GetWorld() != GetWorld())
		{
			continue;
		}
		for (int32 i = 0; i < It->GetNumMaterials(); ++i)
		{
			UMaterialInterface* M = It->GetMaterial(i);
			if (M == nullptr || !M->GetName().StartsWith(TEXT("MI_Glass")))
			{
				continue;
			}
			UMaterialInstanceDynamic*& Mid = Mids.FindOrAdd(M);
			if (Mid == nullptr)
			{
				Mid = UMaterialInstanceDynamic::Create(M, this);
				float Base = 1.0f;
				M->GetScalarParameterValue(FHashedMaterialParameterInfo(TEXT("Emissive")), Base);
				FGlassGlow& G = GlassGlows.AddDefaulted_GetRef();
				G.Mid = Mid;
				G.Base = Base;
			}
			It->SetMaterial(i, Mid);
		}
	}
	ApplyWorldClock(true);
	AutoLogLine(FString::Printf(TEXT("firstperson clock start hour=%.1f day=%.0fh window_light=%d glass=%d fog=%d fills=%d"), FPClockHours, FPTuning.Clock.DayHours,
		SkyLightComp.IsValid() ? 1 : 0, GlassGlows.Num(), FogComp.IsValid() ? 1 : 0, SkyFills.Num()));
}

void AEHGameDirector::TickWorldClock(float RealSeconds)
{
	const FEHWorldClockTuning& C = FPTuning.Clock;
	const double Hours = RealSeconds / C.RealSecondsPerHour * (bPraying ? C.PrayScale : 1.0f);
	FPClockHours += Hours;
	if (bFPShadow && bPraying)
	{
		// Three in-game days of prayer at the Chapel restore a Shadow (about five real minutes of kneeling).
		FPShadowPrayHours += Hours;
		if (FPShadowPrayHours >= 3.0 * C.DayHours)
		{
			bFPShadow = false;
			FPShadowPrayHours = 0.0;
			AutoLogLine(TEXT("fp shadow restored by three days of prayer"));
		}
	}
	ApplyWorldClock(false);
}

void AEHGameDirector::ApplyWorldClock(bool bForce)
{
	// A few hundredths of an hour (about a real second) between updates is plenty for light that changes over hours.
	if (!bForce && FMath::Abs(FPClockHours - FPClockApplied) < 0.02)
	{
		return;
	}
	FPClockApplied = FPClockHours;
	FPClockNow = FPTuning.Clock.Sample(static_cast<float>(FMath::Fmod(FPClockHours, static_cast<double>(FPTuning.Clock.DayHours))));
	if (ULightComponent* L = SkyLightComp.Get())
	{
		L->SetIntensity(SkyBaseIntensity * FPClockNow.Light);
		L->SetLightColor(FPClockNow.Color);
	}
	if (UExponentialHeightFogComponent* Fog = FogComp.Get())
	{
		Fog->SetFogInscatteringColor(FogBase * FPClockNow.Fog);
	}
	// The fills take the day's colour relative to the night's (brightness kept apart): night leaves them as the map
	// has them; day turns their blue toward the daylight's.
	FLinearColor Tint(FPClockNow.Color.R / FMath::Max(ClockNightColor.R, 0.01f), FPClockNow.Color.G / FMath::Max(ClockNightColor.G, 0.01f),
		FPClockNow.Color.B / FMath::Max(ClockNightColor.B, 0.01f), 1.0f);
	Tint /= FMath::Max3(Tint.R, Tint.G, Tint.B);
	Tint.A = 1.0f;
	for (const FSkyFill& F : SkyFills)
	{
		if (ULightComponent* L = F.Light.Get())
		{
			L->SetIntensity(F.BaseIntensity * FPClockNow.Fill);
			L->SetLightColor(F.BaseColor * Tint);
		}
	}
	for (const FGlassGlow& G : GlassGlows)
	{
		if (UMaterialInstanceDynamic* Mid = G.Mid.Get())
		{
			Mid->SetScalarParameterValue(TEXT("Emissive"), G.Base * FPClockNow.Glass);
		}
	}
}
