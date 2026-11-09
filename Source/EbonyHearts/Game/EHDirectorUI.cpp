// Screen and HUD painting. Everything is drawn in a 1920x1080 virtual space (see FEHPainter).
#include "EHGameDirector.h"

#include "Engine/GameViewportClient.h"
#include "Engine/Engine.h"
#include "EHFighterVisual.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/EngineVersion.h"

namespace EHUIPalette
{
const FLinearColor Ink(0.010f, 0.010f, 0.016f, 1.0f);
const FLinearColor Panel(0.016f, 0.015f, 0.024f, 0.86f);
const FLinearColor Edge(0.62f, 0.52f, 0.38f, 0.55f);
const FLinearColor Bone(0.93f, 0.89f, 0.81f, 1.0f);
const FLinearColor Muted(0.60f, 0.58f, 0.56f, 1.0f);
const FLinearColor Violet(0.52f, 0.30f, 0.92f, 1.0f);
const FLinearColor Gold(1.00f, 0.77f, 0.32f, 1.0f);
const FLinearColor Silver(0.66f, 0.76f, 0.90f, 1.0f);
const FLinearColor Ocean(0.14f, 0.48f, 0.84f, 1.0f);
const FLinearColor Crimson(0.80f, 0.09f, 0.11f, 1.0f);
const FLinearColor HealthHi(0.86f, 0.80f, 0.64f, 1.0f);
const FLinearColor HealthLow(0.88f, 0.28f, 0.18f, 1.0f);

FLinearColor A(const FLinearColor& C, float Alpha)
{
	return FLinearColor(C.R, C.G, C.B, C.A * Alpha);
}
}
using namespace EHUIPalette;

namespace EHUIText
{
FString CharId(int32 Index) { return Index == 0 ? TEXT("wren") : TEXT("ashka"); }

bool IsFace(const FKey& Key)
{
	return Key == EKeys::Gamepad_FaceButton_Bottom || Key == EKeys::Gamepad_FaceButton_Right || Key == EKeys::Gamepad_FaceButton_Left || Key == EKeys::Gamepad_FaceButton_Top;
}

// Short label drawn inside a prompt box. Face buttons are drawn as glyphs instead (see PaintKeyGlyph).
FString ButtonLabel(EEHDeviceKind Kind, const FKey& Key)
{
	if (Kind == EEHDeviceKind::PlayStation)
	{
		if (Key == EKeys::Gamepad_LeftShoulder) return TEXT("L1");
		if (Key == EKeys::Gamepad_RightShoulder) return TEXT("R1");
		if (Key == EKeys::Gamepad_LeftTrigger) return TEXT("L2");
		if (Key == EKeys::Gamepad_RightTrigger) return TEXT("R2");
		if (Key == EKeys::Gamepad_Special_Right) return TEXT("OPTIONS");
		if (Key == EKeys::Gamepad_Special_Left) return TEXT("SHARE");
		if (Key == EKeys::Gamepad_LeftThumbstick) return TEXT("L3");
		if (Key == EKeys::Gamepad_RightThumbstick) return TEXT("R3");
	}
	if (Kind == EEHDeviceKind::Xbox)
	{
		if (Key == EKeys::Gamepad_FaceButton_Bottom) return TEXT("A");
		if (Key == EKeys::Gamepad_FaceButton_Right) return TEXT("B");
		if (Key == EKeys::Gamepad_FaceButton_Left) return TEXT("X");
		if (Key == EKeys::Gamepad_FaceButton_Top) return TEXT("Y");
		if (Key == EKeys::Gamepad_LeftShoulder) return TEXT("LB");
		if (Key == EKeys::Gamepad_RightShoulder) return TEXT("RB");
		if (Key == EKeys::Gamepad_LeftTrigger) return TEXT("LT");
		if (Key == EKeys::Gamepad_RightTrigger) return TEXT("RT");
		if (Key == EKeys::Gamepad_Special_Right) return TEXT("MENU");
		if (Key == EKeys::Gamepad_Special_Left) return TEXT("VIEW");
		if (Key == EKeys::Gamepad_LeftThumbstick) return TEXT("LS");
		if (Key == EKeys::Gamepad_RightThumbstick) return TEXT("RS");
	}
	if (Kind == EEHDeviceKind::Gamepad)
	{
		// Unknown make: name buttons by position, which is always right.
		if (Key == EKeys::Gamepad_LeftShoulder) return TEXT("L BUMPER");
		if (Key == EKeys::Gamepad_RightShoulder) return TEXT("R BUMPER");
		if (Key == EKeys::Gamepad_LeftTrigger) return TEXT("L TRIGGER");
		if (Key == EKeys::Gamepad_RightTrigger) return TEXT("R TRIGGER");
		if (Key == EKeys::Gamepad_Special_Right) return TEXT("START");
		if (Key == EKeys::Gamepad_Special_Left) return TEXT("SELECT");
		if (Key == EKeys::Gamepad_LeftThumbstick) return TEXT("L STICK");
		if (Key == EKeys::Gamepad_RightThumbstick) return TEXT("R STICK");
	}
	if (Key == EKeys::Gamepad_DPad_Left) return TEXT("D-PAD LEFT");
	if (Key == EKeys::Gamepad_DPad_Right) return TEXT("D-PAD RIGHT");
	if (Key == EKeys::Gamepad_DPad_Up) return TEXT("D-PAD UP");
	if (Key == EKeys::Gamepad_DPad_Down) return TEXT("D-PAD DOWN");
	return Key.GetDisplayName(false).ToString().ToUpper();
}

// Name used in sentences and notices ("Square", "X", "bottom face button", "J").
FString ButtonName(EEHDeviceKind Kind, const FKey& Key)
{
	if (!Key.IsValid())
	{
		return TEXT("nothing");
	}
	if (IsFace(Key))
	{
		const int32 I = Key == EKeys::Gamepad_FaceButton_Bottom ? 0 : (Key == EKeys::Gamepad_FaceButton_Right ? 1 : (Key == EKeys::Gamepad_FaceButton_Left ? 2 : 3));
		static const TCHAR* PS[] = {TEXT("Cross"), TEXT("Circle"), TEXT("Square"), TEXT("Triangle")};
		static const TCHAR* XB[] = {TEXT("A"), TEXT("B"), TEXT("X"), TEXT("Y")};
		static const TCHAR* Pos[] = {TEXT("bottom face button"), TEXT("right face button"), TEXT("left face button"), TEXT("top face button")};
		return Kind == EEHDeviceKind::PlayStation ? PS[I] : (Kind == EEHDeviceKind::Xbox ? XB[I] : Pos[I]);
	}
	if (Kind == EEHDeviceKind::Gamepad)
	{
		if (Key == EKeys::Gamepad_LeftShoulder) return TEXT("left bumper");
		if (Key == EKeys::Gamepad_RightShoulder) return TEXT("right bumper");
		if (Key == EKeys::Gamepad_LeftTrigger) return TEXT("left trigger");
		if (Key == EKeys::Gamepad_RightTrigger) return TEXT("right trigger");
		if (Key == EKeys::Gamepad_Special_Right) return TEXT("Start");
		if (Key == EKeys::Gamepad_Special_Left) return TEXT("Select");
		if (Key == EKeys::Gamepad_LeftThumbstick) return TEXT("left stick button");
		if (Key == EKeys::Gamepad_RightThumbstick) return TEXT("right stick button");
	}
	if (Key.IsGamepadKey())
	{
		const FString L = ButtonLabel(Kind, Key);
		return L.StartsWith(TEXT("D-PAD")) ? L.ToLower().Replace(TEXT("d-pad"), TEXT("D-pad")) : L;
	}
	return Key.GetDisplayName(false).ToString();
}
}
using namespace EHUIText;

EEHDeviceKind AEHGameDirector::PromptKind(int32 Device) const
{
	switch (Settings.PromptStyle)
	{
	case EEHPromptStyle::Keyboard: return EEHDeviceKind::Keyboard;
	case EEHPromptStyle::PlayStation: return EEHDeviceKind::PlayStation;
	case EEHPromptStyle::Xbox: return EEHDeviceKind::Xbox;
	default: break;
	}
	const int32 D = Device == EHDeviceNone ? RouterPtr->MostRecentDevice() : Device;
	return RouterPtr->KindOf(D);
}

EEHBindingSet AEHGameDirector::PromptSet(int32 Device) const
{
	const int32 D = Device == EHDeviceNone ? RouterPtr->MostRecentDevice() : Device;
	if (PromptKind(Device) == EEHDeviceKind::Keyboard)
	{
		return D == EHDeviceKeyboardB ? EEHBindingSet::KeyboardB : EEHBindingSet::KeyboardA;
	}
	return D >= EHDeviceGamepadBase ? RouterPtr->SetFor(D) : EEHBindingSet::GamepadP1;
}

FKey AEHGameDirector::PromptKey(const FEHHint& Hint, int32 Device) const
{
	const EEHBindingSet Set = PromptSet(Device);
	if (Hint.Nav != EEHNav::Count)
	{
		return EHMenuKey(EHIsKeyboardSet(Set) ? Set : EEHBindingSet::GamepadP1, Hint.Nav);
	}
	return Hint.Action == EEHAction::Count ? FKey(EKeys::Invalid) : Settings.Bindings.First(Set, Hint.Action);
}

EEHDeviceKind AEHGameDirector::KindForSet(EEHBindingSet Set) const
{
	if (EHIsKeyboardSet(Set))
	{
		return EEHDeviceKind::Keyboard;
	}
	if (Settings.PromptStyle == EEHPromptStyle::PlayStation) return EEHDeviceKind::PlayStation;
	if (Settings.PromptStyle == EEHPromptStyle::Xbox) return EEHDeviceKind::Xbox;
	const int32 Pad = RouterPtr->MostRecentGamepad();
	return Pad != EHDeviceNone ? RouterPtr->KindOf(Pad) : EEHDeviceKind::Gamepad;
}

FString AEHGameDirector::KeyName(EEHBindingSet Set, const FKey& Key) const
{
	return ButtonName(KindForSet(Set), Key);
}

FString AEHGameDirector::ButtonNameOf(EEHDeviceKind Kind, const FKey& Key)
{
	return ButtonName(Kind, Key);
}

float AEHGameDirector::PaintKeyGlyph(FEHPainter& P, FVector2f Pos, EEHDeviceKind Kind, const FKey& Key, float Height, bool bMeasureOnly)
{
	const float R = Height * 0.5f;
	const FVector2f C = Pos + FVector2f(R, R);
	if (Kind != EEHDeviceKind::Keyboard && IsFace(Key))
	{
		if (bMeasureOnly)
		{
			return Height;
		}
		P.Round(Pos, FVector2f(Height, Height), FLinearColor(0.08f, 0.08f, 0.10f, 0.95f), R);
		P.Frame(Pos + FVector2f(2, 2), FVector2f(Height - 4, Height - 4), A(Bone, 0.25f), 1.0f);
		if (Kind == EEHDeviceKind::PlayStation)
		{
			// Shapes drawn as vectors: cross, circle, square, triangle.
			const float S = R * 0.48f;
			if (Key == EKeys::Gamepad_FaceButton_Bottom)
			{
				const FLinearColor Col(0.55f, 0.70f, 0.95f);
				P.Line({C + FVector2f(-S, -S), C + FVector2f(S, S)}, Col, 2.5f);
				P.Line({C + FVector2f(-S, S), C + FVector2f(S, -S)}, Col, 2.5f);
			}
			else if (Key == EKeys::Gamepad_FaceButton_Right)
			{
				TArray<FVector2f> Pts;
				for (int32 i = 0; i <= 20; ++i)
				{
					const float T = i / 20.0f * 2.0f * PI;
					Pts.Add(C + FVector2f(FMath::Cos(T), FMath::Sin(T)) * S);
				}
				P.Line(Pts, FLinearColor(0.95f, 0.45f, 0.45f), 2.5f);
			}
			else if (Key == EKeys::Gamepad_FaceButton_Left)
			{
				P.Line({C + FVector2f(-S, -S), C + FVector2f(S, -S), C + FVector2f(S, S), C + FVector2f(-S, S), C + FVector2f(-S, -S)}, FLinearColor(0.92f, 0.58f, 0.80f), 2.5f);
			}
			else
			{
				P.Line({C + FVector2f(0, -S * 1.1f), C + FVector2f(S, S * 0.8f), C + FVector2f(-S, S * 0.8f), C + FVector2f(0, -S * 1.1f)}, FLinearColor(0.45f, 0.85f, 0.70f), 2.5f);
			}
		}
		else if (Kind == EEHDeviceKind::Xbox)
		{
			FLinearColor Col = Bone;
			if (Key == EKeys::Gamepad_FaceButton_Bottom) Col = FLinearColor(0.45f, 0.85f, 0.40f);
			if (Key == EKeys::Gamepad_FaceButton_Right) Col = FLinearColor(0.95f, 0.40f, 0.35f);
			if (Key == EKeys::Gamepad_FaceButton_Left) Col = FLinearColor(0.40f, 0.62f, 0.98f);
			if (Key == EKeys::Gamepad_FaceButton_Top) Col = FLinearColor(0.98f, 0.84f, 0.30f);
			P.Text(ButtonLabel(Kind, Key), C, Fonts.Sized(Fonts.BodyBold, Height * 0.55f), Col, 0.5f, 0.5f, false);
		}
		else
		{
			// Unknown make: four dots in a diamond, the pressed position filled.
			const float D = R * 0.42f;
			const float Dot = FMath::Max(3.0f, R * 0.22f);
			const FVector2f Offsets[] = {FVector2f(0, D), FVector2f(D, 0), FVector2f(-D, 0), FVector2f(0, -D)};
			const FKey Order[] = {EKeys::Gamepad_FaceButton_Bottom, EKeys::Gamepad_FaceButton_Right, EKeys::Gamepad_FaceButton_Left, EKeys::Gamepad_FaceButton_Top};
			for (int32 i = 0; i < 4; ++i)
			{
				const bool bOn = Order[i] == Key;
				P.Round(C + Offsets[i] - FVector2f(Dot, Dot), FVector2f(Dot * 2, Dot * 2), bOn ? Bone : A(Bone, 0.22f), Dot);
			}
		}
		return Height;
	}
	const FString Label = Key.IsValid() ? ButtonLabel(Kind, Key) : FString(TEXT("-"));
	const FSlateFontInfo F = Fonts.Sized(Fonts.BodyBold, Height * 0.5f);
	const float W = FMath::Max(Height, P.Measure(Label, F).X + Height * 0.6f);
	if (bMeasureOnly)
	{
		return W;
	}
	P.Round(Pos, FVector2f(W, Height), FLinearColor(0.10f, 0.10f, 0.12f, 0.95f), 4.0f);
	P.Frame(Pos, FVector2f(W, Height), A(Bone, 0.35f), 1.0f);
	P.Text(Label, Pos + FVector2f(W * 0.5f, Height * 0.5f), F, Bone, 0.5f, 0.5f, false);
	return W;
}

float AEHGameDirector::PaintPrompt(FEHPainter& P, FVector2f Pos, const FEHHint& Hint, int32 Device, float Height)
{
	return PaintKeyGlyph(P, Pos, PromptKind(Device), PromptKey(Hint, Device), Height);
}

void AEHGameDirector::PaintPromptRow(FEHPainter& P, FVector2f Pos, const TArray<FEHHint>& Items, int32 Device)
{
	if (!Settings.bInputHints)
	{
		return;
	}
	const FSlateFontInfo F = Fonts.Sized(Fonts.Body, 19.0f);
	float X = Pos.X;
	for (const FEHHint& It : Items)
	{
		X += PaintPrompt(P, FVector2f(X, Pos.Y), It, Device, 30.0f) + 8.0f;
		X += P.Text(It.Label, FVector2f(X, Pos.Y + 15.0f), F, Muted, 0.0f, 0.5f).X + 28.0f;
	}
}

void AEHGameDirector::PaintBindingValue(FEHPainter& P, FVector2f Right, EEHBindingSet Set, EEHAction Action, int32 OnlySlot, bool bSel)
{
	const EEHDeviceKind Kind = KindForSet(Set);
	const float H = 34.0f;
	const FSlateFontInfo F = Fonts.Sized(Fonts.BodyMedium, 22);
	const bool bCapturing = Screen == EEHScreen::Bindings && CaptureAction == static_cast<int32>(Action) && BindingSet == Set;
	float X = Right.X;
	auto DrawSlot = [&](int32 K) {
		if (bCapturing && CaptureSlot == K)
		{
			const int32 Secs = FMath::CeilToInt(FMath::Max(0.0f, CaptureLeft));
			const FString Wait = EHIsKeyboardSet(Set) ? FString::Printf(TEXT("Press a key... %d"), Secs) : FString::Printf(TEXT("Press a button... %d"), Secs);
			X -= P.Text(Wait, FVector2f(X, Right.Y), F, Gold, 1.0f, 0.5f).X + 18.0f;
			return;
		}
		const FKey Key = Settings.Bindings.Get(Set, Action, K);
		if (!Key.IsValid())
		{
			// An empty slot is shown only on its own row (the list shows just the buttons an action has).
			if (OnlySlot >= 0)
			{
				X -= P.Text(TEXT("-"), FVector2f(X - 8.0f, Right.Y), F, A(Muted, 0.6f), 1.0f, 0.5f).X + 26.0f;
			}
			return;
		}
		const float W = PaintKeyGlyph(P, FVector2f::ZeroVector, Kind, Key, H, true);
		PaintKeyGlyph(P, FVector2f(X - W, Right.Y - H * 0.5f), Kind, Key, H);
		X -= W + 18.0f;
	};
	if (OnlySlot >= 0)
	{
		DrawSlot(OnlySlot);
		return;
	}
	if (!bCapturing && Settings.Bindings.IsUnbound(Set, Action))
	{
		P.Text(TEXT("Unbound"), Right, F, Crimson, 1.0f, 0.5f);
		return;
	}
	for (int32 K = EHKeysPerAction - 1; K >= 0; --K)
	{
		DrawSlot(K);
	}
}

void AEHGameDirector::PaintBackdrop(FEHPainter& P, float Dim)
{
	P.Fill(FLinearColor(0, 0, 0, Dim));
	P.Gradient(FVector2f(P.VirtualMin.X, 780.0f), FVector2f(P.VirtualMax.X - P.VirtualMin.X, 300.0f), FLinearColor(0, 0, 0, 0), FLinearColor(0, 0, 0, 0.7f));
}

void AEHGameDirector::PaintUI(FEHPainter& P)
{
	if (Screen == EEHScreen::Error)
	{
		PaintError(P);
		return;
	}
	if (!bMatchActive || Screen != EEHScreen::Match)
	{
		if (Screen != EEHScreen::Results)
		{
			PaintBackdrop(P, Screen == EEHScreen::Title ? 0.15f : 0.35f);
		}
	}
	switch (Screen)
	{
	case EEHScreen::Title:
		PaintTitle(P);
		break;
	case EEHScreen::Main:
		if (TitleTexture)
		{
			P.Image(TitleBrush, FVector2f(96, 70), FVector2f(600, 600 * TitleBrush.ImageSize.Y / FMath::Max(1.0, TitleBrush.ImageSize.X)), FLinearColor(1, 1, 1, 0.95f));
		}
		PaintMenu(P, FString(), false);
		break;
	case EEHScreen::Select:
		PaintSelect(P);
		break;
	case EEHScreen::Match:
		PaintHUD(P);
		if (Mode == EEHMode::Training)
		{
			PaintTraining(P);
		}
		if (Mode == EEHMode::Tutorial)
		{
			PaintLesson(P);
		}
		if (bPaused)
		{
			P.NextLayer();
			P.Fill(FLinearColor(0, 0, 0, 0.55f));
			if (!DisconnectNotice.IsEmpty())
			{
				P.Round(FVector2f(460, 420), FVector2f(1000, 200), Panel, 8);
				P.Text(TEXT("Controller disconnected"), FVector2f(960, 470), Fonts.Sized(Fonts.Display, 34), Bone, 0.5f, 0.5f);
				P.Text(DisconnectNotice, FVector2f(960, 545), Fonts.Sized(Fonts.Body, 22), Muted, 0.5f, 0.5f);
			}
			else
			{
				PaintMenu(P, MenuTitle, true);
			}
		}
		break;
	case EEHScreen::Results:
		PaintResults(P);
		break;
	case EEHScreen::MoveList:
		PaintMoveList(P);
		break;
	case EEHScreen::Credits:
		PaintCredits(P);
		break;
	case EEHScreen::DisplayConfirm:
		PaintMenu(P, FString::Printf(TEXT("Keep these display settings?  Reverting in %d"), FMath::CeilToInt(DisplayConfirmLeft)), true);
		break;
	default:
		PaintMenu(P, MenuTitle, Screen != EEHScreen::Main);
		break;
	}
	if (ToastAge < 3.0f && !Toast.IsEmpty())
	{
		const float Alpha = FMath::Clamp(3.0f - ToastAge, 0.0f, 1.0f);
		const FSlateFontInfo F = Fonts.Sized(Fonts.BodyMedium, 22);
		const FVector2f Size = P.Measure(Toast, F);
		P.Round(FVector2f(960 - Size.X * 0.5f - 24, 960), FVector2f(Size.X + 48, 52), A(Panel, Alpha), 6);
		P.Text(Toast, FVector2f(960, 986), F, A(Bone, Alpha), 0.5f, 0.5f);
	}
	if (bAnyGraybox && Screen != EEHScreen::Title)
	{
		P.Text(TEXT("DEVELOPMENT GRAYBOX - final character assets not loaded"), FVector2f(960, 1062), Fonts.Sized(Fonts.Body, 16), FLinearColor(1, 0.4f, 0.3f, 0.8f), 0.5f, 1.0f);
	}
}

void AEHGameDirector::PaintError(FEHPainter& P)
{
	P.Fill(Ink);
	P.Text(TEXT("Ebony Hearts could not start"), FVector2f(960, 400), Fonts.Sized(Fonts.Display, 40), Bone, 0.5f, 0.5f);
	P.Text(DataError, FVector2f(960, 480), Fonts.Sized(Fonts.Body, 22), Muted, 0.5f, 0.5f);
	P.Text(TEXT("Press confirm or Escape to quit."), FVector2f(960, 560), Fonts.Sized(Fonts.Body, 20), Muted, 0.5f, 0.5f);
}

void AEHGameDirector::PaintTitle(FEHPainter& P)
{
	const float In = FMath::Clamp(ScreenAge / 1.2f, 0.0f, 1.0f);
	if (TitleTexture)
	{
		const float W = 1280.0f;
		const float H = W * TitleBrush.ImageSize.Y / FMath::Max(1.0, TitleBrush.ImageSize.X);
		// A soft dark band keeps the lettering readable over the lit rose window behind it.
		const float BandTop = 250 - H * 0.5f - 60.0f;
		const float BandHalf = H * 0.5f + 60.0f;
		P.Gradient(FVector2f(P.VirtualMin.X, BandTop), FVector2f(P.VirtualMax.X - P.VirtualMin.X, BandHalf), FLinearColor(0, 0, 0, 0), FLinearColor(0, 0, 0, 0.55f * In));
		P.Gradient(FVector2f(P.VirtualMin.X, BandTop + BandHalf), FVector2f(P.VirtualMax.X - P.VirtualMin.X, BandHalf), FLinearColor(0, 0, 0, 0.55f * In), FLinearColor(0, 0, 0, 0));
		P.Image(TitleBrush, FVector2f(960 - W * 0.5f, 250 - H * 0.5f + (1.0f - In) * 20.0f), FVector2f(W, H), FLinearColor(1, 1, 1, In));
	}
	else
	{
		P.Text(TEXT("EBONY HEARTS"), FVector2f(960, 250), Fonts.Sized(Fonts.Display, 110), A(Bone, In), 0.5f, 0.5f);
	}
	if (ScreenAge < 1.5f)
	{
		// Rasterise the large in-match glyphs (round banners, callouts, combo counter) while nothing is at stake, at
		// near-zero alpha so they are invisible but not culled.
		static const TCHAR* Glyphs = TEXT("ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789 .,'!?-");
		const FLinearColor Ghost(0, 0, 0, 0.01f);
		P.Text(Glyphs, FVector2f(960, 940), Fonts.Sized(Fonts.Display, 104), Ghost, 0.5f, 0.5f, false);
		for (const float Size : {34.0f, 40.0f, 44.0f, 48.0f})
		{
			P.Text(Glyphs, FVector2f(960, 940), Fonts.Sized(Fonts.Display, Size), Ghost, 0.5f, 0.5f, false);
		}
		P.Text(Glyphs, FVector2f(960, 940), Fonts.Sized(Fonts.DisplayLight, 36), Ghost, 0.5f, 0.5f, false);
	}
	const float Pulse = 0.55f + 0.45f * FMath::Sin(static_cast<float>(RenderTime) * 2.4f);
	P.Text(TEXT("Press any button"), FVector2f(960, 820), Fonts.Sized(Fonts.DisplayLight, 30), A(Bone, In * Pulse), 0.5f, 0.5f);
	P.Text(TEXT("© 2026 Markus Gillyard · Cinqic"), FVector2f(960, 1030), Fonts.Sized(Fonts.Body, 17), A(Muted, In), 0.5f, 0.5f);
}

void AEHGameDirector::PaintMenu(FEHPainter& P, const FString& Heading, bool bCompact)
{
	const bool bCentered = bCompact;
	const float W = bCentered ? 760.0f : 560.0f;
	// Long menus (bindings, training options) use tighter rows so they never reach the prompt row at the bottom.
	const float RowH = Menu.Num() > 10 ? 46.0f : 56.0f;
	const float HeadH = Heading.IsEmpty() ? 0.0f : 80.0f;
	const float H = HeadH + Menu.Num() * RowH + 40.0f;
	const FVector2f Pos = bCentered ? FVector2f(960 - W * 0.5f, FMath::Max(80.0f, 540 - H * 0.5f)) : FVector2f(96, 380);
	P.Round(Pos, FVector2f(W, H), Panel, 8);
	P.Rect(Pos + FVector2f(0, 0), FVector2f(W, 2), Edge);
	if (!Heading.IsEmpty())
	{
		P.Text(Heading, Pos + FVector2f(36, 46), Fonts.Sized(Fonts.Display, 30), Bone, 0.0f, 0.5f);
		P.Rect(Pos + FVector2f(36, 76), FVector2f(W - 72, 1), A(Edge, 0.6f));
	}
	for (int32 i = 0; i < Menu.Num(); ++i)
	{
		const FEHMenuItem& It = Menu[i];
		const FVector2f Row = Pos + FVector2f(0, HeadH + 20 + i * RowH);
		const bool bSel = i == MenuIndex;
		if (bSel)
		{
			P.Rect(Row + FVector2f(16, 6), FVector2f(W - 32, RowH - 12), FLinearColor(0.20f, 0.14f, 0.30f, 0.55f));
			P.Rect(Row + FVector2f(16, 6), FVector2f(4, RowH - 12), Violet);
		}
		P.Text(It.Label, Row + FVector2f(40, RowH * 0.5f), Fonts.Sized(bSel ? Fonts.BodyBold : Fonts.BodyMedium, 26), bSel ? Bone : Muted, 0.0f, 0.5f);
		if (It.PaintValue)
		{
			It.PaintValue(P, Row + FVector2f(W - 40, RowH * 0.5f), bSel);
		}
		else if (It.Value)
		{
			const FString V = It.Value();
			const FString Shown = It.Change ? FString::Printf(TEXT("‹  %s  ›"), *V) : V;
			P.Text(Shown, Row + FVector2f(W - 40, RowH * 0.5f), Fonts.Sized(Fonts.BodyMedium, 24), bSel ? Gold : Muted, 1.0f, 0.5f);
		}
	}
	const FEHMenuItem* Sel = Menu.IsValidIndex(MenuIndex) ? &Menu[MenuIndex] : nullptr;
	if (Sel && !Sel->Hint.IsEmpty())
	{
		P.Text(Sel->Hint, FVector2f(bCentered ? 960.0f : Pos.X, Pos.Y + H + 34), Fonts.Sized(Fonts.Body, 21), Muted, bCentered ? 0.5f : 0.0f, 0.5f);
	}
	const int32 Owner = MenuOwner != EHDeviceNone ? MenuOwner : RouterPtr->MostRecentDevice();
	if (Screen == EEHScreen::Bindings && CaptureAction >= 0)
	{
		// Escape or Options / Menu cancels a capture; show the one that belongs to the layout being edited.
		const int32 CancelDevice = EHIsKeyboardSet(BindingSet) ? EHDeviceKeyboardA : RouterPtr->MostRecentGamepad();
		PaintPromptRow(P, FVector2f(96, 1000), {FEHHint::Menu(EEHNav::Pause, TEXT("Cancel"))}, CancelDevice);
		return;
	}
	PaintPromptRow(P, FVector2f(96, 1000), {FEHHint::Menu(EEHNav::Confirm, TEXT("Select")), FEHHint::Menu(EEHNav::Back, TEXT("Back"))}, Owner);
}

void AEHGameDirector::PaintSelect(FEHPainter& P)
{
	const FString Heading = Mode == EEHMode::VersusCpu ? TEXT("Versus CPU") : (Mode == EEHMode::Versus ? TEXT("Local Versus") : (Mode == EEHMode::Training ? TEXT("Training") : TEXT("Lesson")));
	P.Text(Heading, FVector2f(960, 80), Fonts.Sized(Fonts.Display, 44), Bone, 0.5f, 0.5f);
	FString Instruction;
	if (Mode == EEHMode::Versus)
	{
		Instruction = TEXT("Each player presses Confirm on their own controller or keyboard side to join, then chooses and confirms.");
	}
	else if (SelectStage == 0)
	{
		Instruction = TEXT("Choose your fighter");
	}
	else if (SelectStage == 1)
	{
		Instruction = Mode == EEHMode::Training ? TEXT("Choose your training partner") : TEXT("Choose your opponent");
	}
	else
	{
		Instruction = TEXT("Difficulty and side");
	}
	P.Text(Instruction, FVector2f(960, 130), Fonts.Sized(Fonts.BodyMedium, 24), Muted, 0.5f, 0.5f);
	for (int32 c = 0; c < 2; ++c)
	{
		const FEHCharacterPresentation& CP = Pres.Get(CharId(c));
		const FVector2f Pos(c == 0 ? 120.0f : 1240.0f, 640.0f);
		const FVector2f Size(560, 300);
		P.Round(Pos, Size, Panel, 8);
		P.Rect(Pos, FVector2f(Size.X, 4), c == 0 ? Ocean : Crimson);
		P.Text(CP.DisplayName.ToString(), Pos + FVector2f(32, 52), Fonts.Sized(Fonts.Display, 40), Bone, 0.0f, 0.5f);
		P.Text(CP.Title.ToString(), Pos + FVector2f(32, 102), Fonts.Sized(Fonts.DisplayLight, 22), c == 0 ? Gold : FLinearColor(0.95f, 0.45f, 0.40f), 0.0f, 0.5f);
		P.Text(CP.Style.ToString(), Pos + FVector2f(32, 142), Fonts.Sized(Fonts.BodyMedium, 22), Muted, 0.0f, 0.5f);
		const FString Blurb = c == 0
			? TEXT("All-rounder. Reach, spinning and flying kicks, a double-leg takedown;\nthe 720 Hook Kick; golden Spirit Enhanced Strikes.")
			: TEXT("Muay Thai specialist. Teeps, front kicks, spinning elbows, knees and\nclinch trips, with the crimson Lamplighter Flame.");
		P.Text(Blurb, Pos + FVector2f(32, 210), Fonts.Sized(Fonts.Body, 21), Bone, 0.0f, 0.5f);
		// Cursor markers: gold for player one, silver for player two / CPU.
		for (int32 s = 0; s < 2; ++s)
		{
			bool bShow = false;
			bool bLocked = false;
			if (Mode == EEHMode::Versus)
			{
				bShow = SelectDevice[s] != EHDeviceNone && SelectCursor[s] == c;
				bLocked = SelectLocked[s];
			}
			else
			{
				bShow = (s == 0 || SelectStage >= 1) && SelectCursor[s] == c;
				bLocked = SelectStage > s;
			}
			if (!bShow)
			{
				continue;
			}
			const FLinearColor Col = s == 0 ? Gold : Silver;
			const FString Tag = Mode == EEHMode::Versus ? FString::Printf(TEXT("P%d"), s + 1) : (s == 0 ? TEXT("YOU") : (Mode == EEHMode::Training || Mode == EEHMode::Tutorial ? TEXT("PARTNER") : TEXT("CPU")));
			// Tags sit on the card's top edge as tabs, clear of long names such as "Ashka Rook".
			const FVector2f TagPos = Pos + FVector2f(Size.X - 16 - s * 136, -20);
			P.Round(TagPos - FVector2f(120, 0), FVector2f(120, 40), bLocked ? Col : A(Col, 0.35f), 6);
			P.Text(Tag, TagPos - FVector2f(60, -20), Fonts.Sized(Fonts.BodyBold, 20), bLocked ? Ink : Bone, 0.5f, 0.5f, false);
			P.Frame(Pos - FVector2f(4 + s * 6, 4 + s * 6), Size + FVector2f(8 + s * 12, 8 + s * 12), Col, 2.0f);
		}
	}
	if (Mode == EEHMode::VersusCpu && SelectStage == 2)
	{
		const FString Levels[] = {TEXT("Easy"), TEXT("Normal"), TEXT("Hard")};
		P.Round(FVector2f(710, 300), FVector2f(500, 170), Panel, 8);
		for (int32 r = 0; r < 2; ++r)
		{
			const bool bSel = MenuIndex == r;
			const FVector2f Row(740, 340 + r * 70);
			P.Text(r == 0 ? TEXT("CPU level") : TEXT("Your side"), Row + FVector2f(0, 15), Fonts.Sized(Fonts.BodyMedium, 26), bSel ? Bone : Muted, 0.0f, 0.5f);
			const FString V = r == 0 ? Levels[FMath::Clamp(CpuLevel, 0, 2)] : (bPlayerOnRight ? TEXT("Right") : TEXT("Left"));
			P.Text(FString::Printf(TEXT("‹  %s  ›"), *V), Row + FVector2f(440, 15), Fonts.Sized(Fonts.BodyMedium, 26), bSel ? Gold : Muted, 1.0f, 0.5f);
		}
	}
	if (Mode == EEHMode::Versus)
	{
		for (int32 s = 0; s < 2; ++s)
		{
			const FEHDevice* D = RouterPtr->FindDevice(SelectDevice[s]);
			const FString Line = D ? FString::Printf(TEXT("P%d: %s%s"), s + 1, *D->Name, SelectLocked[s] ? TEXT("  - ready") : TEXT("")) : FString::Printf(TEXT("P%d: press Light to join"), s + 1);
			P.Text(Line, FVector2f(s == 0 ? 120.0f : 1800.0f, 580), Fonts.Sized(Fonts.BodyMedium, 22), s == 0 ? Gold : Silver, s == 0 ? 0.0f : 1.0f, 0.5f);
		}
		if (SelectLocked[0] && SelectLocked[1])
		{
			const float Pulse = 0.6f + 0.4f * FMath::Sin(static_cast<float>(RenderTime) * 4.0f);
			P.Text(TEXT("Both ready - press Light to fight"), FVector2f(960, 520), Fonts.Sized(Fonts.Display, 30), A(Gold, Pulse), 0.5f, 0.5f);
		}
	}
	PaintPromptRow(P, FVector2f(96, 1000), {FEHHint::Menu(EEHNav::Left, TEXT("Choose")), FEHHint::Menu(EEHNav::Confirm, TEXT("Confirm")), FEHHint::Menu(EEHNav::Back, TEXT("Back"))}, Mode == EEHMode::Versus ? EHDeviceNone : SelectDevice[0]);
}

void AEHGameDirector::PaintHUD(FEHPainter& P)
{
	const eh::MatchState& S = Match->State();
	const FSlateFontInfo NameFont = Fonts.Sized(Fonts.Display, 26);
	for (int32 i = 0; i < 2; ++i)
	{
		const eh::FighterState& F = S.f[i];
		const eh::CharacterDef& C = Match->Character(i);
		const FEHCharacterPresentation& CP = Pres.Get(CharId(SlotChar[i]));
		const bool bLeft = i == 0;
		const float BarW = 700.0f;
		const float BarH = 28.0f;
		const float X = bLeft ? 120.0f : 1800.0f - BarW;
		const float Y = 54.0f;
		const float Pct = FMath::Clamp(static_cast<float>(F.health) / C.maxHealth, 0.0f, 1.0f);
		const float Lag = FMath::Clamp(HealthLag[i], Pct, 1.0f);
		P.Rect(FVector2f(X - 4, Y - 4), FVector2f(BarW + 8, BarH + 8), FLinearColor(0, 0, 0, 0.75f));
		P.Rect(FVector2f(X, Y), FVector2f(BarW, BarH), FLinearColor(0.08f, 0.05f, 0.06f, 0.95f));
		// Bars drain toward the centre of the screen.
		auto Fill = [&](float Amount, const FLinearColor& Col) {
			const float W = BarW * Amount;
			P.Rect(FVector2f(bLeft ? X + BarW - W : X, Y), FVector2f(W, BarH), Col);
		};
		Fill(Lag, FLinearColor(0.75f, 0.12f, 0.10f, 0.9f));
		Fill(Pct, FMath::Lerp(HealthLow, HealthHi, FMath::Clamp(Pct * 1.6f, 0.0f, 1.0f)));
		P.Rect(FVector2f(X, Y), FVector2f(BarW, 3), FLinearColor(1, 1, 1, 0.18f));
		P.Frame(FVector2f(X - 1, Y - 1), FVector2f(BarW + 2, BarH + 2), A(Edge, 0.9f), 1.0f);
		const FString Name = CP.DisplayName.ToString().ToUpper();
		P.Text(Name, FVector2f(bLeft ? X : X + BarW, Y + BarH + 26), NameFont, Bone, bLeft ? 0.0f : 1.0f, 0.5f);
		const FString Who = SlotCpu[i] ? (Mode == EEHMode::Training || Mode == EEHMode::Tutorial ? TEXT("PARTNER") : TEXT("CPU")) : FString::Printf(TEXT("P%d"), i + 1);
		const float NameW = P.Measure(Name, NameFont).X;
		P.Text(Who, FVector2f(bLeft ? X + NameW + 16 : X + BarW - NameW - 16, Y + BarH + 28), Fonts.Sized(Fonts.BodyBold, 18), i == 0 ? Gold : Silver, bLeft ? 0.0f : 1.0f, 0.5f);
		// Round pips beside the timer.
		if (Mode == EEHMode::VersusCpu || Mode == EEHMode::Versus)
		{
			for (int32 r = 0; r < Rules.roundsToWin; ++r)
			{
				const FVector2f Pip(bLeft ? 900.0f - r * 30.0f : 1020.0f + r * 30.0f - 18.0f, Y + BarH + 18);
				P.Round(Pip, FVector2f(18, 18), r < F.roundWins ? (i == 0 ? Gold : Silver) : FLinearColor(0.15f, 0.15f, 0.18f, 0.9f), 9);
			}
		}
		// Gauge along the bottom.
		const float GW = 380.0f;
		const float GX = bLeft ? 120.0f : 1800.0f - GW;
		const float GY = 1000.0f;
		const float Meter = static_cast<float>(F.meter) / Rules.meterMax;
		const FLinearColor GCol = SlotChar[i] == 0 ? Gold : FLinearColor(0.90f, 0.16f, 0.12f);
		P.Rect(FVector2f(GX - 3, GY - 3), FVector2f(GW + 6, 20), FLinearColor(0, 0, 0, 0.7f));
		P.Rect(FVector2f(GX, GY), FVector2f(GW, 14), FLinearColor(0.07f, 0.06f, 0.08f, 0.95f));
		float Shown = Meter;
		FLinearColor ShownCol = GCol;
		if (F.auraFrames > 0)
		{
			Shown = static_cast<float>(F.auraFrames) / 480.0f;
			ShownCol = FMath::Lerp(Gold, FLinearColor::White, 0.25f + 0.25f * FMath::Sin(static_cast<float>(RenderTime) * 9.0f));
		}
		P.Rect(FVector2f(bLeft ? GX : GX + GW * (1.0f - Shown), GY), FVector2f(GW * Shown, 14), ShownCol);
		if (Meter >= 0.5f && SlotChar[i] == 1)
		{
			P.Rect(FVector2f(GX + GW * 0.5f - 1, GY - 2), FVector2f(2, 18), A(Bone, 0.8f));
		}
		const bool bFull = (SlotChar[i] == 0 && F.meter >= Rules.meterMax) || (SlotChar[i] == 1 && F.meter >= Rules.meterMax / 2);
		const FString Label = CP.GaugeLabel.ToString() + (F.auraFrames > 0 ? TEXT("  ACTIVE") : (bFull ? TEXT("  READY") : TEXT("")));
		P.Text(Label, FVector2f(bLeft ? GX : GX + GW, GY - 22), Fonts.Sized(Fonts.BodyBold, 19), bFull || F.auraFrames > 0 ? GCol : Muted, bLeft ? 0.0f : 1.0f, 0.5f);
		// Combo counter on the attacker's side.
		const eh::FighterState& Def = S.f[1 - i];
		if (Def.combo >= 2 && (Def.state == eh::FState::Hitstun || Def.state == eh::FState::Knockdown))
		{
			const float CX = bLeft ? 180.0f : 1740.0f;
			P.Text(FString::Printf(TEXT("%d HITS"), Def.combo), FVector2f(CX, 330), Fonts.Sized(Fonts.Display, 46), Gold, bLeft ? 0.0f : 1.0f, 0.5f);
			P.Text(FString::Printf(TEXT("%d damage"), Def.comboDamage), FVector2f(CX, 378), Fonts.Sized(Fonts.BodyMedium, 22), Bone, bLeft ? 0.0f : 1.0f, 0.5f);
		}
	}
	// Timer.
	if (Mode == EEHMode::VersusCpu || Mode == EEHMode::Versus)
	{
		const int32 Seconds = FMath::CeilToInt(S.timer / static_cast<float>(eh::kTickHz));
		P.Round(FVector2f(910, 36), FVector2f(100, 76), FLinearColor(0, 0, 0, 0.7f), 6);
		P.Text(FString::Printf(TEXT("%d"), Seconds), FVector2f(960, 74), Fonts.Sized(Fonts.Display, 48), Seconds <= 10 ? HealthLow : Bone, 0.5f, 0.5f);
	}
	for (const FEHCallout& C : Callouts)
	{
		const float Alpha = FMath::Clamp((C.Life - C.Age) / 0.25f, 0.0f, 1.0f);
		const float Rise = C.Age * 18.0f;
		P.Text(C.Text, FVector2f(C.Side == 0 ? 180.0f : 1740.0f, 270.0f - Rise), Fonts.Sized(Fonts.Display, 34), A(C.Color, Alpha), C.Side == 0 ? 0.0f : 1.0f, 0.5f);
	}
	for (const FEHBanner& B : Banners)
	{
		const float Alpha = FMath::Clamp(B.Age / 0.12f, 0.0f, 1.0f) * FMath::Clamp((B.Life - B.Age) / 0.3f, 0.0f, 1.0f);
		if (!B.Text.IsEmpty())
		{
			P.Gradient(FVector2f(P.VirtualMin.X, 440), FVector2f(P.VirtualMax.X - P.VirtualMin.X, 200), FLinearColor(0, 0, 0, 0), FLinearColor(0, 0, 0, 0.45f * Alpha), 6);
			// One fixed size (glyphs warmed on the title screen): a growing size made Slate rasterise new large glyphs
			// during round transitions, which hitched.
			P.Text(B.Text, FVector2f(960, 540), Fonts.Sized(Fonts.Display, 104), A(B.Color, Alpha), 0.5f, 0.5f);
		}
		if (!B.Sub.IsEmpty() && B.Age > 0.0f)
		{
			P.Text(B.Sub, FVector2f(960, 640), Fonts.Sized(Fonts.DisplayLight, 36), A(Bone, Alpha), 0.5f, 0.5f);
		}
	}
}

void AEHGameDirector::PaintHitboxes(FEHPainter& P)
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (PC == nullptr || GEngine == nullptr || GEngine->GameViewport == nullptr)
	{
		return;
	}
	FVector2D ViewportSize;
	GEngine->GameViewport->GetViewportSize(ViewportSize);
	if (ViewportSize.X <= 0)
	{
		return;
	}
	const FVector2f PixelToLocal = P.Local / FVector2f(ViewportSize);
	auto Project = [&](float X, float Z, FVector2f& Out) {
		FVector2D Screen;
		if (!UGameplayStatics::ProjectWorldToScreen(PC, FVector(X, 0, Z), Screen, false))
		{
			return false;
		}
		Out = P.ToVirtual(FVector2f(Screen) * PixelToLocal);
		return true;
	};
	auto DrawBox = [&](const eh::Box& B, const FLinearColor& Col) {
		FVector2f A0, A1;
		const float U = 1.0f / eh::kUnitsPerCm;
		if (Project(B.x0 * U, B.y1 * U, A0) && Project(B.x1 * U, B.y0 * U, A1))
		{
			P.Rect(A0, A1 - A0, A(Col, 0.22f));
			P.Frame(A0, A1 - A0, Col, 1.5f);
		}
	};
	std::vector<eh::Box> Boxes;
	for (int32 i = 0; i < 2; ++i)
	{
		DrawBox(Match->GetPushbox(i), FLinearColor(0.95f, 0.85f, 0.25f, 0.8f));
		Match->GetHurtboxes(i, Boxes);
		for (const eh::Box& B : Boxes)
		{
			DrawBox(B, FLinearColor(0.30f, 0.65f, 1.0f, 0.9f));
		}
		Match->GetHitboxes(i, Boxes);
		for (const eh::Box& B : Boxes)
		{
			DrawBox(B, FLinearColor(1.0f, 0.25f, 0.20f, 0.95f));
		}
		const eh::FighterState& F = Match->State().f[i];
		if (F.state == eh::FState::Attack)
		{
			const eh::MoveDef& M = Match->Character(i).moves[static_cast<size_t>(F.move)];
			if (M.kind == eh::MoveKind::Throw && M.hits[0].frames.Contains(F.moveFrame))
			{
				const int32 Front = F.x + F.facing * Match->Character(i).halfWidth;
				const int32 Reach = Front + F.facing * (M.throwRange + Match->Character(1 - i).halfWidth * 2);
				DrawBox(eh::Box{FMath::Min(Front, Reach), 80 * eh::kUnitsPerCm, FMath::Max(Front, Reach), 150 * eh::kUnitsPerCm}, FLinearColor(0.35f, 0.95f, 0.45f, 0.9f));
			}
		}
	}
}

void AEHGameDirector::PaintTraining(FEHPainter& P)
{
	const eh::MatchState& S = Match->State();
	if (bShowHitboxes)
	{
		PaintHitboxes(P);
	}
	P.NextLayer();
	if (bShowInputs)
	{
		for (int32 i = 0; i < 2; ++i)
		{
			const bool bLeft = i == 0;
			const float X = bLeft ? 120.0f : 1800.0f;
			P.Text(i == 0 ? TEXT("INPUT") : TEXT("PARTNER"), FVector2f(X, 430), Fonts.Sized(Fonts.BodyBold, 16), Muted, bLeft ? 0.0f : 1.0f, 0.5f);
			const TArray<FEHInputLogEntry>& Log = InputLog[i];
			for (int32 k = 0; k < Log.Num() && k < 14; ++k)
			{
				const FEHInputLogEntry& E = Log[Log.Num() - 1 - k];
				FString Line = FString::Printf(TEXT("%3d  %s"), E.Frames, E.X > 0 ? TEXT("→") : (E.X < 0 ? TEXT("←") : TEXT("·")));
				if (E.Held & eh::BtnLight) Line += TEXT(" L");
				if (E.Held & eh::BtnHeavy) Line += TEXT(" H");
				if (E.Held & eh::BtnSpecial) Line += TEXT(" S");
				if (E.Y < 0) Line += TEXT(" ↓");
				if (E.Y > 0) Line += TEXT(" ↑");
				if ((E.Held & eh::BtnThrow) && Rules.ThrowsEnabled()) Line += TEXT(" T");
				if (E.Held & eh::BtnDodge) Line += TEXT(" D");
				if (E.Held & eh::BtnBlock) Line += TEXT(" B");
				P.Text(Line, FVector2f(X, 458 + k * 26), Fonts.Sized(Fonts.BodyMedium, 20), A(Bone, 1.0f - k * 0.05f), bLeft ? 0.0f : 1.0f, 0.5f);
			}
		}
	}
	if (bShowFrameData)
	{
		P.Round(FVector2f(560, 860), FVector2f(800, 104), FLinearColor(0, 0, 0, 0.6f), 6);
		const FString Move = LastMoveName[0].IsEmpty() ? TEXT("-") : LastMoveName[0];
		P.Text(FString::Printf(TEXT("%s   %s"), *Move, *LastMoveFrames[0]), FVector2f(960, 888), Fonts.Sized(Fonts.BodyMedium, 22), Bone, 0.5f, 0.5f);
		FString Adv = TEXT("Advantage -");
		if (S.lastAdvantageValid)
		{
			const int32 V = S.lastAdvantagePlayer == 0 ? S.lastAdvantage : -S.lastAdvantage;
			Adv = FString::Printf(TEXT("Advantage %+d"), V);
		}
		// Crouching is a posture of the neutral, guard, stun and low-attack states; it is shown with the state.
		auto Posture = [this](int32 i) {
			const FString Name = UTF8_TO_TCHAR(eh::StateName(Match->State().f[i].state));
			return Match->IsCrouching(i) ? Name + TEXT(" (crouching)") : Name;
		};
		P.Text(FString::Printf(TEXT("%s    You: %s    Partner: %s"), *Adv, *Posture(0), *Posture(1)), FVector2f(960, 932), Fonts.Sized(Fonts.Body, 20), Muted, 0.5f, 0.5f);
	}
	PaintPromptRow(P, FVector2f(560, 1040), {FEHHint::Menu(EEHNav::Pause, TEXT("Training options")), FEHHint::Act(EEHAction::Reset, TEXT("Reset"))}, SlotDevice[0]);
}

void AEHGameDirector::PaintLesson(FEHPainter& P)
{
	if (!Lesson.IsValidIndex(LessonStep))
	{
		return;
	}
	const FEHTutorialStep& Step = Lesson[LessonStep];
	const FVector2f Pos(460, 150);
	P.Round(Pos, FVector2f(1000, 150), FLinearColor(0, 0, 0, 0.62f), 8);
	P.Rect(Pos, FVector2f(1000, 3), Violet);
	P.Text(FString::Printf(TEXT("%d / %d   %s"), LessonStep + 1, Lesson.Num(), *Step.Title), Pos + FVector2f(32, 36), Fonts.Sized(Fonts.Display, 28), Bone, 0.0f, 0.5f);
	P.Text(Step.Body, Pos + FVector2f(32, 82), Fonts.Sized(Fonts.Body, 22), Bone, 0.0f, 0.5f);
	if (LessonStep < Lesson.Num() - 1)
	{
		const bool bDone = LessonDoneAge >= 0.0f;
		P.Text(bDone ? TEXT("Done") : FString::Printf(TEXT("%d / %d"), FMath::Min(LessonCount, Step.Goal), Step.Goal), Pos + FVector2f(968, 36), Fonts.Sized(Fonts.BodyBold, 24), bDone ? Gold : Muted, 1.0f, 0.5f);
		// Which buttons this step is about.
		TArray<FEHHint> Hints;
		switch (Step.Kind)
		{
		case EEHLessonStep::Movement: Hints = {FEHHint::Act(EEHAction::Left, TEXT("Back")), FEHHint::Act(EEHAction::Right, TEXT("Forward"))}; break;
		case EEHLessonStep::Light: Hints = {FEHHint::Act(EEHAction::Light, TEXT("Light x3"))}; break;
		case EEHLessonStep::Heavy: Hints = {FEHHint::Act(EEHAction::Heavy, TEXT("Heavy"))}; break;
		case EEHLessonStep::Block: case EEHLessonStep::TimedBlock: Hints = {FEHHint::Act(EEHAction::Block, TEXT("Block"))}; break;
		case EEHLessonStep::LowGuard: Hints = {FEHHint::Act(EEHAction::Down, TEXT("Crouch (hold)")), FEHHint::Act(EEHAction::Block, TEXT("Block"))}; break;
		case EEHLessonStep::JumpIn: Hints = {FEHHint::Act(EEHAction::Jump, TEXT("Jump (+ toward)")), FEHHint::Act(EEHAction::Heavy, TEXT("Attack coming down"))}; break;
		case EEHLessonStep::AntiAir: Hints = {FEHHint::Act(EEHAction::Down, TEXT("Down +")), FEHHint::Act(EEHAction::Heavy, TEXT("Uppercut"))}; break;
		case EEHLessonStep::Throw: Hints = {FEHHint::Act(EEHAction::Throw, TEXT("Throw (up close)"))}; break;
		case EEHLessonStep::ThrowEscape: Hints = {FEHHint::Act(EEHAction::Throw, TEXT("Throw to escape"))}; break;
		case EEHLessonStep::ComboThrow: Hints = {FEHHint::Act(EEHAction::Light, TEXT("Light")), FEHHint::Act(EEHAction::Light, TEXT("Light")), FEHHint::Act(EEHAction::Throw, TEXT("Throw"))}; break;
		case EEHLessonStep::Punish: Hints = {FEHHint::Act(EEHAction::Block, TEXT("Block")), FEHHint::Act(EEHAction::Heavy, TEXT("Punish"))}; break;
		case EEHLessonStep::Special: Hints = {FEHHint::Act(EEHAction::Special, TEXT("Special (+ toward / + away)"))}; break;
		default: break;
		}
		const bool bSaved = Settings.bInputHints;
		Settings.bInputHints = true;
		PaintPromptRow(P, Pos + FVector2f(32, 108), Hints, SlotDevice[0]);
		Settings.bInputHints = bSaved;
	}
	else
	{
		const bool bSaved = Settings.bInputHints;
		Settings.bInputHints = true;
		PaintPromptRow(P, Pos + FVector2f(32, 108), {FEHHint::Menu(EEHNav::Confirm, TEXT("Return to the menu, or keep practising"))}, SlotDevice[0]);
		Settings.bInputHints = bSaved;
	}
}

void AEHGameDirector::PaintResults(FEHPainter& P)
{
	P.Fill(FLinearColor(0, 0, 0, 0.45f));
	const eh::MatchState& S = Match->State();
	FString Headline = TEXT("DRAW");
	if (LastWinner == 0 || LastWinner == 1)
	{
		Headline = Pres.Get(CharId(SlotChar[LastWinner])).DisplayName.ToString().ToUpper() + TEXT(" WINS");
	}
	P.Text(Headline, FVector2f(960, 150), Fonts.Sized(Fonts.Display, 76), Bone, 0.5f, 0.5f);
	if (LastWinner == 0 || LastWinner == 1)
	{
		const FString Who = SlotCpu[LastWinner] ? TEXT("CPU") : FString::Printf(TEXT("Player %d"), LastWinner + 1);
		P.Text(Who, FVector2f(960, 222), Fonts.Sized(Fonts.DisplayLight, 28), LastWinner == 0 ? Gold : Silver, 0.5f, 0.5f);
	}
	const FVector2f Table(560, 290);
	P.Round(Table, FVector2f(800, 250), Panel, 8);
	const TCHAR* Labels[] = {TEXT("Rounds"), TEXT("Damage dealt"), TEXT("Longest combo"), TEXT("Throws landed"), TEXT("Deflects")};
	for (int32 r = 0, Row = 0; r < 5; ++r)
	{
		if (r == 3 && !Rules.ThrowsEnabled())
		{
			continue;   // no throws in this rule set
		}
		const float Y = Table.Y + 40 + (Row++) * 42 + (Rules.ThrowsEnabled() ? 0.0f : 21.0f);
		P.Text(Labels[r], FVector2f(960, Y), Fonts.Sized(Fonts.BodyMedium, 22), Muted, 0.5f, 0.5f);
		for (int32 i = 0; i < 2; ++i)
		{
			int32 V = 0;
			switch (r)
			{
			case 0: V = S.f[i].roundWins; break;
			case 1: V = Stats.Damage[i]; break;
			case 2: V = Stats.MaxCombo[i]; break;
			case 3: V = Stats.Throws[i]; break;
			default: V = Stats.Deflects[i]; break;
			}
			P.Text(FString::Printf(TEXT("%d"), V), FVector2f(i == 0 ? 640.0f : 1280.0f, Y), Fonts.Sized(Fonts.BodyBold, 24), i == 0 ? Gold : Silver, 0.5f, 0.5f);
		}
	}
	PaintMenu(P, FString(), true);
}

void AEHGameDirector::PaintMoveList(FEHPainter& P)
{
	P.Fill(FLinearColor(0, 0, 0, 0.55f));
	const int32 C = SelectCursor[0];
	const FEHCharacterPresentation& CP = Pres.Get(CharId(C));
	const eh::CharacterDef& Def = Chars[C];
	P.Text(CP.DisplayName.ToString(), FVector2f(960, 70), Fonts.Sized(Fonts.Display, 44), Bone, 0.5f, 0.5f);
	P.Text(TEXT("‹  Move List  ›"), FVector2f(960, 118), Fonts.Sized(Fonts.DisplayLight, 22), Muted, 0.5f, 0.5f);
	P.Round(FVector2f(220, 160), FVector2f(1480, 800), Panel, 8);
	const FSlateFontInfo Head = Fonts.Sized(Fonts.BodyBold, 19);
	const FSlateFontInfo Row = Fonts.Sized(Fonts.Body, 21);
	const float Cols[] = {260, 620, 860, 1000, 1110};
	P.Text(TEXT("Technique"), FVector2f(Cols[0], 196), Head, Muted, 0.0f, 0.5f);
	P.Text(TEXT("Input"), FVector2f(Cols[1], 196), Head, Muted, 0.0f, 0.5f);
	P.Text(TEXT("Startup"), FVector2f(Cols[2], 196), Head, Muted, 0.0f, 0.5f);
	P.Text(TEXT("Damage"), FVector2f(Cols[3], 196), Head, Muted, 0.0f, 0.5f);
	P.Text(TEXT("Notes"), FVector2f(Cols[4], 196), Head, Muted, 0.0f, 0.5f);
	int32 Line = 0;
	for (const eh::MoveDef& M : Def.moves)
	{
		if (M.kind == eh::MoveKind::Throw && !Rules.ThrowsEnabled())
		{
			continue;   // the throw stays in the data but is not part of this rule set
		}
		const FString Id = UTF8_TO_TCHAR(M.id.c_str());
		// Inputs are drawn with the viewer's own buttons: direction words, then the action's button glyph.
		const FString DirText = M.air ? TEXT("In a jump: ") : (M.down ? TEXT("Down + ") : (M.dir == eh::DirReq::Forward ? TEXT("Toward + ") : (M.dir == eh::DirReq::Back ? TEXT("Away + ") : TEXT(""))));
		const EEHAction Act = M.button == eh::BtnLight ? EEHAction::Light : (M.button == eh::BtnHeavy ? EEHAction::Heavy : (M.button == eh::BtnSpecial ? EEHAction::Special : (M.button == eh::BtnThrow ? EEHAction::Throw : EEHAction::Dodge)));
		int32 Repeats = 1;
		FString Suffix;
		if (Id == TEXT("L2")) Repeats = 2;
		if (Id == TEXT("L3")) Repeats = 3;
		if (M.kind == eh::MoveKind::Dodge && M.dir == eh::DirReq::Any) Suffix = TEXT("  away or neutral");
		const FString Startup = M.hits.empty() ? FString(TEXT("-")) : FString::Printf(TEXT("%d"), M.hits.front().frames.first);
		const FString Damage = M.kind == eh::MoveKind::Throw ? FString::Printf(TEXT("%d"), Def.throws[static_cast<size_t>(M.throwIndex)].damage) : (M.hits.empty() ? FString(TEXT("-")) : FString::Printf(TEXT("%d"), M.hits.front().damage));
		const FText* Note = CP.MoveNotes.Find(Id);
		const float Y = 228 + Line * 48;   // 15 rows fit the panel
		P.Text(UTF8_TO_TCHAR(M.name.c_str()), FVector2f(Cols[0], Y), Fonts.Sized(Fonts.BodyBold, 22), Bone, 0.0f, 0.5f);
		{
			float X = Cols[1];
			if (!DirText.IsEmpty())
			{
				X += P.Text(DirText, FVector2f(X, Y), Row, Gold, 0.0f, 0.5f).X + 4.0f;
			}
			for (int32 r = 0; r < Repeats; ++r)
			{
				X += PaintPrompt(P, FVector2f(X, Y - 15.0f), FEHHint::Act(Act, FString()), EHDeviceNone, 30.0f) + 6.0f;
			}
			if (!Suffix.IsEmpty())
			{
				P.Text(Suffix, FVector2f(X, Y), Fonts.Sized(Fonts.Body, 19), Muted, 0.0f, 0.5f);
			}
		}
		P.Text(Startup, FVector2f(Cols[2], Y), Row, Bone, 0.0f, 0.5f);
		P.Text(Damage, FVector2f(Cols[3], Y), Row, Bone, 0.0f, 0.5f);
		P.Text(Note ? Note->ToString() : FString(), FVector2f(Cols[4], Y), Fonts.Sized(Fonts.Body, 19), Muted, 0.0f, 0.5f);
		++Line;
	}
	PaintPromptRow(P, FVector2f(96, 1000), {FEHHint::Menu(EEHNav::Left, TEXT("Other fighter")), FEHHint::Menu(EEHNav::Back, TEXT("Back"))}, EHDeviceNone);
}

void AEHGameDirector::PaintCredits(FEHPainter& P)
{
	P.Fill(FLinearColor(0, 0, 0, 0.6f));
	const TCHAR* Lines[] = {
		TEXT("EBONY HEARTS"),
		TEXT(""),
		TEXT("Created by Markus Gillyard"),
		TEXT("Published by Cinqic"),
		TEXT(""),
		TEXT("Character bodies built from MakeHuman system assets (CC0 1.0)"),
		TEXT("Surface textures: Poly Haven and ambientCG (CC0 1.0)"),
		TEXT("Interface and impact sounds include Kenney audio packs (CC0 1.0)"),
		TEXT("Motion capture: Open Motion Project by ACCAD / The Ohio State University (CC BY 3.0)"),
		TEXT("Animation: Mixamo (Adobe), used royalty free"),
		TEXT("Fonts: Cinzel and Alegreya Sans, SIL Open Font License 1.1"),
		TEXT(""),
		TEXT("Unreal® Engine, Copyright 1998-2026, Epic Games, Inc. All rights reserved."),
		TEXT("Full third-party notices are in the game folder (THIRD_PARTY_NOTICES.txt)."),
	};
	float Y = 200.0f;
	for (int32 i = 0; i < UE_ARRAY_COUNT(Lines); ++i)
	{
		const bool bTitle = i == 0;
		P.Text(Lines[i], FVector2f(960, Y), bTitle ? Fonts.Sized(Fonts.Display, 48) : Fonts.Sized(Fonts.Body, 24), bTitle ? Bone : Muted, 0.5f, 0.5f);
		Y += bTitle ? 70.0f : 44.0f;
	}
	PaintPromptRow(P, FVector2f(96, 1000), {FEHHint::Menu(EEHNav::Back, TEXT("Back"))}, EHDeviceNone);
}
