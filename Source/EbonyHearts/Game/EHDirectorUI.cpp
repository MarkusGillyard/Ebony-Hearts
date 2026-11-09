// Screen and HUD painting. Everything is drawn in a 1920x1080 virtual space (see FEHPainter).
#include "EHGameDirector.h"

#include "Engine/GameViewportClient.h"
#include "Engine/Engine.h"
#include "EHFighterVisual.h"
#include "EHUIStyle.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/EngineVersion.h"

namespace EHUIPalette
{
// Older names for the design tokens (EHUIStyle.h), bound by reference so they follow the tokens.
const FLinearColor& Ink = EHStyle::Abyss;
const FLinearColor& Panel = EHStyle::Panel;
const FLinearColor Edge = EHStyle::Alpha(EHStyle::Silver, 0.55f);
const FLinearColor& Bone = EHStyle::TextPrimary;
const FLinearColor& Muted = EHStyle::TextSecondary;
const FLinearColor& Violet = EHStyle::Focus;
const FLinearColor& Gold = EHStyle::P1;
const FLinearColor& Silver = EHStyle::P2;
const FLinearColor& HealthHi = EHStyle::Health;
const FLinearColor& HealthLow = EHStyle::HealthLow;

FLinearColor A(const FLinearColor& C, float Alpha)
{
	return FLinearColor(C.R, C.G, C.B, C.A * Alpha);
}

// A fighter's accent (by character index: 0 Wren, 1 Ashka) for fills and lines, and the variant that passes as text.
const FLinearColor& Accent(int32 Char) { return Char == 0 ? EHStyle::WrenAccent : EHStyle::AshkaAccent; }
const FLinearColor& AccentText(int32 Char) { return Char == 0 ? EHStyle::WrenAccent : EHStyle::AshkaText; }
}
using namespace EHUIPalette;

namespace EHUIShapes
{
void Crescent(FEHPainter& P, FVector2f C, float R, const FLinearColor& Col, bool bFilled);
float Chip(FEHPainter& P, const FEHFonts& Fonts, FVector2f Pos, const FString& Text, const FLinearColor& Col, bool bFilled, bool bAlignRight);
}

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
		P.NextLayer();
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
			P.Text(ButtonLabel(Kind, Key), C, Fonts.Sized(Fonts.BodyBold, FMath::Max(Height * 0.55f, EHStyle::Type::Label)), Col, 0.5f, 0.5f, false);
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
	const FSlateFontInfo F = Fonts.Sized(Fonts.BodyBold, FMath::Max(Height * 0.5f, EHStyle::Type::Label));
	const float W = FMath::Max(Height, P.Measure(Label, F).X + Height * 0.6f);
	if (bMeasureOnly)
	{
		return W;
	}
	P.Round(Pos, FVector2f(W, Height), FLinearColor(0.10f, 0.10f, 0.12f, 0.95f), 4.0f);
	P.NextLayer();
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
	const FSlateFontInfo F = Fonts.Sized(Fonts.BodyMedium, EHStyle::Type::Label + 2.0f);
	const float G = EHStyle::GlyphHeight;
	float X = Pos.X;
	for (const FEHHint& It : Items)
	{
		X += PaintPrompt(P, FVector2f(X, Pos.Y - (G - 30.0f) * 0.5f), It, Device, G) + 10.0f;
		X += P.Text(It.Label, FVector2f(X, Pos.Y + 15.0f), F, Bone, 0.0f, 0.5f).X + 32.0f;
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
			X -= P.Text(Wait, FVector2f(X, Right.Y), F, EHStyle::FocusText, 1.0f, 0.5f).X + 18.0f;
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
		P.Text(TEXT("Unbound"), Right, F, EHStyle::Warning, 1.0f, 0.5f);
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
	if (bAutoHideUI && Screen != EEHScreen::Error)
	{
		return;
	}
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
	// Screens fade in over 0.15 s. Visual only: input acts at once, and a press during the fade is never lost.
	if (Screen != EEHScreen::Match && Screen != EEHScreen::Title && Screen != EEHScreen::Error)
	{
		P.Opacity = FMath::Clamp(ScreenAge / 0.15f, 0.0f, 1.0f);
	}
	switch (Screen)
	{
	case EEHScreen::Title:
		PaintTitle(P);
		break;
	case EEHScreen::Main:
		PaintMainMenuA(P);
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
			// Two layers up: text is drawn one layer above its shapes, so one step would leave the overlays' text level
			// with the pause panel and let it show through.
			P.NextLayer();
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
	namespace St = EHStyle;
	const float In = FMath::Clamp(ScreenAge / 1.2f, 0.0f, 1.0f);
	if (KeyArtTexture)
	{
		// Still Water: the key art fills the screen (cover: wider screens crop top and bottom), its wordmark is part of
		// the painting, and only the prompt and the credit sit over it.
		const float Wide = P.VirtualMax.X - P.VirtualMin.X;
		const float Tall = P.VirtualMax.Y - P.VirtualMin.Y;
		const float Aspect = KeyArtBrush.ImageSize.X / FMath::Max(1.0, KeyArtBrush.ImageSize.Y);
		const float DrawW = FMath::Max(Wide, Tall * Aspect);
		const float DrawH = DrawW / Aspect;
		P.Fill(St::Abyss);
		P.Image(KeyArtBrush, FVector2f(960 - DrawW * 0.5f, 540 - DrawH * 0.5f), FVector2f(DrawW, DrawH), FLinearColor(1, 1, 1, In));
		P.Gradient(FVector2f(P.VirtualMin.X, 820), FVector2f(Wide, P.VirtualMax.Y - 820), St::Alpha(St::Abyss, 0.0f), St::Alpha(St::Abyss, 0.9f * In));
	}
	else if (TitleTexture)
	{
		const float W = 1280.0f;
		const float H = W * TitleBrush.ImageSize.Y / FMath::Max(1.0, TitleBrush.ImageSize.X);
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
	// The prompt breathes for its first seconds, then holds still (nothing blinks on its own for more than 5 s).
	const float Pulse = ScreenAge < 4.0f ? 0.55f + 0.45f * FMath::Sin(static_cast<float>(RenderTime) * 2.4f) : 1.0f;
	FSlateFontInfo PromptF = Fonts.Sized(Fonts.Display, 26.0f);
	PromptF.LetterSpacing = 300;
	P.Text(TEXT("PRESS ANY BUTTON"), FVector2f(960, 952), PromptF, A(St::Silver, In * Pulse), 0.5f, 0.5f);
	P.Text(TEXT("© 2026 Markus Gillyard  ·  Cinqic"), FVector2f(960, 1032), Fonts.Sized(Fonts.BodyMedium, St::Type::Label), A(Muted, In), 0.5f, 0.5f);
}

// Still Water's main menu: a plain list over the darkened chapel, a violet band fading to the right, and the crescent
// marking the focused row.
void AEHGameDirector::PaintMainMenuA(FEHPainter& P)
{
	namespace St = EHStyle;
	const float Tall = P.VirtualMax.Y - P.VirtualMin.Y;
	// Left-to-right darkening (the painter's gradient is vertical, so draw it as columns).
	const int32 Cols = 24;
	for (int32 c = 0; c < Cols; ++c)
	{
		const float T = static_cast<float>(c) / (Cols - 1);
		const float X0 = P.VirtualMin.X + (1180.0f - P.VirtualMin.X) * c / Cols;
		const float X1 = P.VirtualMin.X + (1180.0f - P.VirtualMin.X) * (c + 1) / Cols;
		P.Rect(FVector2f(X0, P.VirtualMin.Y), FVector2f(X1 - X0, Tall), St::Alpha(St::Abyss, 0.94f * (1.0f - T * T)));
	}
	if (LogoSmallTexture || TitleTexture)
	{
		const FSlateBrush& Logo = LogoSmallTexture ? LogoSmallBrush : TitleBrush;
		P.Image(Logo, FVector2f(96, 56), FVector2f(700, 700 * Logo.ImageSize.Y / FMath::Max(1.0, Logo.ImageSize.X)), FLinearColor(1, 1, 1, 1));
	}
	P.NextLayer();
	const float X = 150.0f;
	float Y = 392.0f;
	const float RowH = 62.0f;
	for (int32 i = 0; i < Menu.Num(); ++i)
	{
		const FEHMenuItem& It = Menu[i];
		if (It.bHeader)
		{
			P.Rect(FVector2f(X, Y + 14), FVector2f(360, 1), St::Alpha(St::Silver, 0.35f));
			Y += 30.0f;
			continue;
		}
		const bool bSel = i == MenuIndex;
		if (bSel)
		{
			const int32 Steps = 32;
			for (int32 k = 0; k < Steps; ++k)
			{
				const float T = static_cast<float>(k) / Steps;
				const float X0 = FMath::RoundToFloat(X - 30 + 620.0f * k / Steps);
				const float X1 = FMath::RoundToFloat(X - 30 + 620.0f * (k + 1) / Steps);
				P.Rect(FVector2f(X0, Y - 4), FVector2f(X1 - X0, 54), St::Alpha(St::Focus, 0.62f * (1.0f - T)));
			}
			EHUIShapes::Crescent(P, FVector2f(X - 52, Y + 18), 14.0f, St::Silver, true);
		}
		P.Text(It.Label, FVector2f(X, Y + 23), Fonts.Sized(bSel ? Fonts.BodyBold : Fonts.BodyMedium, St::Type::Menu + 2.0f), bSel ? St::TextPrimary : St::Alpha(St::Silver, 0.82f), 0.0f, 0.5f);
		Y += RowH;
	}
	const FEHMenuItem* Sel = Menu.IsValidIndex(MenuIndex) ? &Menu[MenuIndex] : nullptr;
	if (Sel && !Sel->Hint.IsEmpty())
	{
		P.Text(Sel->Hint, FVector2f(X - 2, Y + 36), Fonts.Sized(Fonts.Body, St::Type::Body), St::TextSecondary, 0.0f, 0.5f);
	}
	const int32 Owner = MenuOwner != EHDeviceNone ? MenuOwner : RouterPtr->MostRecentDevice();
	PaintPromptRow(P, FVector2f(96, 1000), {FEHHint::Menu(EEHNav::Confirm, TEXT("Select")), FEHHint::Menu(EEHNav::Back, TEXT("Back"))}, Owner);
}

void AEHGameDirector::PaintMenu(FEHPainter& P, const FString& Heading, bool bCompact, float TopY)
{
	const bool bCentered = bCompact;
	const float W = bCentered ? 760.0f : 560.0f;
	// Long menus (bindings, training options) use tighter rows so they never reach the prompt row at the bottom.
	int32 Headers = 0;
	for (const FEHMenuItem& It : Menu)
	{
		Headers += It.bHeader ? 1 : 0;
	}
	const float RowH = Menu.Num() - Headers > 10 ? 46.0f : 56.0f;
	const float HeaderH = 34.0f;
	const float HeadH = Heading.IsEmpty() ? 0.0f : 80.0f;
	const float H = HeadH + (Menu.Num() - Headers) * RowH + Headers * HeaderH + 40.0f;
	const FVector2f Pos = bCentered ? FVector2f(960 - W * 0.5f, TopY >= 0.0f ? TopY : FMath::Max(80.0f, 540 - H * 0.5f)) : FVector2f(96, 380);
	// Still Water: a square dark veil between two silver rules, the crescent set into the top one.
	P.Rect(Pos, FVector2f(W, H), EHStyle::Alpha(EHStyle::Abyss, 0.86f));
	P.NextLayer();
	P.Rect(Pos + FVector2f(0, 0), FVector2f(W * 0.5f - 22, 1), EHStyle::Alpha(EHStyle::Silver, 0.55f));
	P.Rect(Pos + FVector2f(W * 0.5f + 22, 0), FVector2f(W * 0.5f - 22, 1), EHStyle::Alpha(EHStyle::Silver, 0.55f));
	P.Rect(Pos + FVector2f(0, H - 1), FVector2f(W, 1), EHStyle::Alpha(EHStyle::Silver, 0.55f));
	EHUIShapes::Crescent(P, Pos + FVector2f(W * 0.5f, -2), 10.0f, EHStyle::Silver, true);
	if (!Heading.IsEmpty())
	{
		P.Text(Heading, Pos + FVector2f(36, 46), Fonts.Sized(Fonts.Display, 30), Bone, 0.0f, 0.5f);
		P.Rect(Pos + FVector2f(36, 76), FVector2f(W - 72, 1), A(Edge, 0.6f));
	}
	float RowY = HeadH + 20;
	for (int32 i = 0; i < Menu.Num(); ++i)
	{
		const FEHMenuItem& It = Menu[i];
		const FVector2f Row = Pos + FVector2f(0, RowY);
		if (It.bHeader)
		{
			// Section label: small spaced capitals and a hairline, never focused.
			FSlateFontInfo HF = Fonts.Sized(Fonts.BodyBold, EHStyle::Type::Label);
			HF.LetterSpacing = 140;
			const float TW = P.Text(It.Label.ToUpper(), Row + FVector2f(40, HeaderH * 0.55f), HF, EHStyle::TextSecondary, 0.0f, 0.5f).X;
			P.Rect(Row + FVector2f(40 + TW + 14, HeaderH * 0.55f), FVector2f(FMath::Max(0.0f, W - 80 - TW - 14), 1), A(Edge, 0.5f));
			RowY += HeaderH;
			continue;
		}
		RowY += RowH;
		const bool bSel = i == MenuIndex;
		if (bSel)
		{
			// Focus: a violet band fading to the right, the crescent marking the row (shape), bold primary text.
			// Steps abut exactly: overlapping translucent steps would double their alpha in thin seams.
			const int32 Steps = 32;
			for (int32 k = 0; k < Steps; ++k)
			{
				const float T = static_cast<float>(k) / Steps;
				const float X0 = FMath::RoundToFloat(16 + (W - 32) * k / Steps);
				const float X1 = FMath::RoundToFloat(16 + (W - 32) * (k + 1) / Steps);
				P.Rect(Row + FVector2f(X0, 6), FVector2f(X1 - X0, RowH - 12), EHStyle::Alpha(EHStyle::Focus, 0.62f - 0.42f * T));
			}
			// Outside the veil, as on the main menu: beside the label a small crescent reads like a tick.
			EHUIShapes::Crescent(P, Row + FVector2f(-20, RowH * 0.5f - 5), 10.0f, EHStyle::Silver, true);
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
			// An unapplied value: light violet plus a dot (not colour alone); the Apply row counts them.
			const bool bPending = It.Pending && It.Pending();
			const float TW = P.Text(Shown, Row + FVector2f(W - 40, RowH * 0.5f), Fonts.Sized(Fonts.BodyMedium, 24), bPending ? EHStyle::FocusText : (bSel ? Bone : Muted), 1.0f, 0.5f).X;
			if (bPending)
			{
				P.Round(Row + FVector2f(W - 40 - TW - 24, RowH * 0.5f - 6), FVector2f(12, 12), EHStyle::FocusText, 6);
			}
		}
	}
	const FEHMenuItem* Sel = Menu.IsValidIndex(MenuIndex) ? &Menu[MenuIndex] : nullptr;
	if (Sel && !Sel->Hint.IsEmpty())
	{
		P.Text(Sel->Hint, FVector2f(bCentered ? 960.0f : Pos.X, Pos.Y + H + 34), Fonts.Sized(Fonts.Body, EHStyle::Type::Body), Muted, bCentered ? 0.5f : 0.0f, 0.5f);
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

namespace EHUIShapes
{
// The crescent emblem from the logo, open at the top: a filled crescent for "done" (a won round, a locked choice), a
// thin outline for "not yet". Drawn as concentric arcs whose span shrinks inward, which tapers the horns.
void Crescent(FEHPainter& P, FVector2f C, float R, const FLinearColor& Col, bool bFilled)
{
	auto Arc = [&](float Radius, float Span, float Thick, const FLinearColor& LineCol) {
		TArray<FVector2f> Pts;
		const int32 N = 24;
		for (int32 i = 0; i <= N; ++i)
		{
			const float T = FMath::DegreesToRadians(90.0f - Span * 0.5f + Span * i / N);
			Pts.Add(C + FVector2f(FMath::Cos(T), FMath::Sin(T)) * Radius);
		}
		P.Line(Pts, LineCol, Thick);
	};
	if (bFilled)
	{
		const int32 Rings = FMath::Max(3, FMath::RoundToInt(R * 0.22f));
		for (int32 k = 0; k < Rings; ++k)
		{
			const float F = static_cast<float>(k) / Rings;
			Arc(R * (1.0f - 0.36f * F), 230.0f * (1.0f - 0.55f * F), 2.2f, Col);
		}
	}
	else
	{
		Arc(R, 230.0f, 2.0f, Col);
		Arc(R * 0.66f, 120.0f, 1.5f, EHUIPalette::A(Col, 0.8f));
	}
}

// A small rounded label: filled in the player's colour when final (locked in), outlined while still open.
float Chip(FEHPainter& P, const FEHFonts& Fonts, FVector2f Pos, const FString& Text, const FLinearColor& Col, bool bFilled, bool bAlignRight)
{
	const FSlateFontInfo F = Fonts.Sized(Fonts.BodyBold, EHStyle::Type::Label);
	const float W = P.Measure(Text, F).X + 36.0f;
	const float H = 40.0f;
	const FVector2f At(bAlignRight ? Pos.X - W : Pos.X, Pos.Y);
	if (bFilled)
	{
		P.Round(At, FVector2f(W, H), Col, H * 0.5f);
		P.Text(Text, At + FVector2f(W * 0.5f, H * 0.5f), F, EHStyle::Abyss, 0.5f, 0.5f, false);
	}
	else
	{
		P.Round(At, FVector2f(W, H), EHStyle::Alpha(EHStyle::Abyss, 0.7f), H * 0.5f);
		P.NextLayer();
		P.Frame(At + FVector2f(2, 2), FVector2f(W - 4, H - 4), Col, 2.0f);
		P.Text(Text, At + FVector2f(W * 0.5f, H * 0.5f), F, Col, 0.5f, 0.5f, false);
	}
	return W;
}
}

void AEHGameDirector::PaintSelect(FEHPainter& P)
{
	namespace St = EHStyle;
	const float Wide = P.VirtualMax.X - P.VirtualMin.X;
	// Dark bands top and bottom keep the text readable over the chapel; the fighters stay clear in between.
	P.Gradient(FVector2f(P.VirtualMin.X, P.VirtualMin.Y), FVector2f(Wide, 220.0f - P.VirtualMin.Y), St::Alpha(St::Abyss, 0.85f), St::Alpha(St::Abyss, 0.0f));
	P.Gradient(FVector2f(P.VirtualMin.X, 700.0f), FVector2f(Wide, P.VirtualMax.Y - 700.0f), St::Alpha(St::Abyss, 0.0f), St::Alpha(St::Abyss, 0.92f));
	const FString Heading = Mode == EEHMode::VersusCpu ? TEXT("VERSUS CPU") : (Mode == EEHMode::Versus ? TEXT("LOCAL VERSUS") : (Mode == EEHMode::Training ? TEXT("TRAINING") : TEXT("LESSON")));
	FSlateFontInfo HeadFont = Fonts.Sized(Fonts.Display, St::Type::Title);
	HeadFont.LetterSpacing = 120;
	P.Text(Heading, FVector2f(960, 66), HeadFont, St::TextPrimary, 0.5f, 0.5f);
	FString Instruction;
	if (Mode == EEHMode::Versus)
	{
		Instruction = TEXT("Each player presses Confirm on their own controller or keyboard side to join, then chooses and locks in.");
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
		Instruction = TEXT("CPU level and your side");
	}
	P.Text(Instruction, FVector2f(960, 120), Fonts.Sized(Fonts.BodyMedium, St::Type::Body + 2.0f), St::TextSecondary, 0.5f, 0.5f);
	for (int32 c = 0; c < 2; ++c)
	{
		const FEHCharacterPresentation& CP = Pres.Get(CharId(c));
		const bool bRight = c == 1;
		const float X = bRight ? 1800.0f : 120.0f;
		const float AlignX = bRight ? 1.0f : 0.0f;
		const float Y = 742.0f;
		// Who is on this fighter: one chip per player, filled once locked in.
		float ChipX = X;
		bool bAnyCursor = false;
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
			bAnyCursor = true;
			const FString Who = Mode == EEHMode::Versus ? FString::Printf(TEXT("P%d"), s + 1) : (s == 0 ? TEXT("YOU") : (Mode == EEHMode::Training || Mode == EEHMode::Tutorial ? TEXT("PARTNER") : TEXT("CPU")));
			const FString Tag = Who + (bLocked ? TEXT("  ·  LOCKED IN") : TEXT("  ·  CHOOSING"));
			const FLinearColor& Col = s == 0 ? St::P1 : St::P2;
			const float W = EHUIShapes::Chip(P, Fonts, FVector2f(ChipX, Y), Tag, Col, bLocked, bRight);
			ChipX += bRight ? -(W + 12.0f) : (W + 12.0f);
		}
		// The fighter's accent bar beside the plate; brighter under a cursor.
		P.Rect(FVector2f(bRight ? X + 14.0f : X - 18.0f, Y + 62.0f), FVector2f(4.0f, 148.0f), bAnyCursor ? Accent(c) : A(Accent(c), 0.45f));
		P.Text(CP.DisplayName.ToString().ToUpper(), FVector2f(X, Y + 96.0f), Fonts.Sized(Fonts.Display, 52.0f), St::TextPrimary, AlignX, 0.5f);
		P.Text(CP.Title.ToString(), FVector2f(X, Y + 150.0f), Fonts.Sized(Fonts.DisplayLight, St::Type::Body + 4.0f), AccentText(c), AlignX, 0.5f);
		P.Text(CP.Style.ToString(), FVector2f(X, Y + 192.0f), Fonts.Sized(Fonts.BodyMedium, St::Type::Body), St::TextSecondary, AlignX, 0.5f);
	}
	if (Mode == EEHMode::VersusCpu && SelectStage == 2)
	{
		const FString Levels[] = {TEXT("Easy"), TEXT("Normal"), TEXT("Hard")};
		const FVector2f Box(700, 838);
		P.Round(Box, FVector2f(520, 128), St::Panel, 8);
		P.NextLayer();
		P.Frame(Box, FVector2f(520, 128), A(St::Silver, 0.35f), 1.0f);
		for (int32 r = 0; r < 2; ++r)
		{
			const bool bSel = MenuIndex == r;
			const FVector2f Row(Box.X, Box.Y + 14 + r * 52);
			if (bSel)
			{
				P.Rect(Row + FVector2f(12, 0), FVector2f(496, 48), St::Alpha(St::Focus, 0.30f));
				P.Rect(Row + FVector2f(12, 0), FVector2f(4, 48), St::Focus);
			}
			P.Text(r == 0 ? TEXT("CPU level") : TEXT("Your side"), Row + FVector2f(36, 24), Fonts.Sized(bSel ? Fonts.BodyBold : Fonts.BodyMedium, St::Type::Menu - 2.0f), bSel ? St::TextPrimary : St::TextSecondary, 0.0f, 0.5f);
			const FString V = r == 0 ? Levels[FMath::Clamp(CpuLevel, 0, 2)] : (bPlayerOnRight ? TEXT("Right") : TEXT("Left"));
			P.Text(FString::Printf(TEXT("‹  %s  ›"), *V), Row + FVector2f(484, 24), Fonts.Sized(Fonts.BodyBold, St::Type::Menu - 2.0f), bSel ? St::TextPrimary : St::TextSecondary, 1.0f, 0.5f);
		}
	}
	if (Mode == EEHMode::Versus)
	{
		for (int32 s = 0; s < 2; ++s)
		{
			const FEHDevice* D = RouterPtr->FindDevice(SelectDevice[s]);
			const FString Line = D ? FString::Printf(TEXT("P%d  ·  %s"), s + 1, *D->Name) : FString::Printf(TEXT("P%d  ·  press Confirm to join"), s + 1);
			P.Text(Line, FVector2f(s == 0 ? 120.0f : 1800.0f, 690), Fonts.Sized(Fonts.BodyBold, St::Type::Label + 2.0f), s == 0 ? St::P1 : St::P2, s == 0 ? 0.0f : 1.0f, 0.5f);
		}
		if (SelectLocked[0] && SelectLocked[1])
		{
			P.Text(TEXT("Both ready  ·  press Confirm to fight"), FVector2f(960, 900), Fonts.Sized(Fonts.Display, St::Type::Heading), St::FocusText, 0.5f, 0.5f);
		}
	}
	PaintPromptRow(P, FVector2f(700, 1012), {FEHHint::Menu(EEHNav::Left, TEXT("Choose")), FEHHint::Menu(EEHNav::Confirm, TEXT("Lock in")), FEHHint::Menu(EEHNav::Back, TEXT("Back"))}, Mode == EEHMode::Versus ? EHDeviceNone : SelectDevice[0]);
}

void AEHGameDirector::PaintHUD(FEHPainter& P)
{
	namespace St = EHStyle;
	const eh::MatchState& S = Match->State();
	const float Wide = P.VirtualMax.X - P.VirtualMin.X;
	// A dark band behind the top of the HUD so the lit rose window behind it cannot lower its contrast.
	P.Gradient(FVector2f(P.VirtualMin.X, P.VirtualMin.Y), FVector2f(Wide, 230.0f - P.VirtualMin.Y), St::Alpha(St::Abyss, 0.80f), St::Alpha(St::Abyss, 0.0f));
	const FSlateFontInfo NameFont = Fonts.Sized(Fonts.Display, St::Type::Name);
	const bool bVersus = Mode == EEHMode::VersusCpu || Mode == EEHMode::Versus;
	for (int32 i = 0; i < 2; ++i)
	{
		const eh::FighterState& F = S.f[i];
		const eh::CharacterDef& C = Match->Character(i);
		const int32 Char = SlotChar[i];
		const FEHCharacterPresentation& CP = Pres.Get(CharId(Char));
		const bool bLeft = i == 0;
		const float BarW = 720.0f;
		const float BarH = 30.0f;
		const float X = bLeft ? 110.0f : 1810.0f - BarW;
		const float Y = 46.0f;
		const float Pct = FMath::Clamp(static_cast<float>(F.health) / C.maxHealth, 0.0f, 1.0f);
		const float Lag = FMath::Clamp(HealthLag[i], Pct, 1.0f);
		P.Rect(FVector2f(X, Y), FVector2f(BarW, BarH), St::Track);
		// Bars drain toward the centre of the screen: the outer end empties first.
		auto Fill = [&](float Amount, const FLinearColor& Col) {
			const float W = BarW * Amount;
			P.Rect(FVector2f(bLeft ? X + BarW - W : X, Y), FVector2f(W, BarH), Col);
		};
		Fill(Lag, St::HealthLag);
		Fill(Pct, Pct < 0.3f ? St::HealthLow : St::Health);
		P.Rect(FVector2f(X, Y), FVector2f(BarW, 3), FLinearColor(1, 1, 1, 0.18f));
		P.Frame(FVector2f(X - 2, Y - 2), FVector2f(BarW + 4, BarH + 4), St::Alpha(St::Silver, 0.7f), 2.0f);
		// Name and who plays it.
		const FString Name = CP.DisplayName.ToString().ToUpper();
		P.Text(Name, FVector2f(bLeft ? X : X + BarW, Y + BarH + 30), NameFont, St::TextPrimary, bLeft ? 0.0f : 1.0f, 0.5f);
		const FString Who = SlotCpu[i] ? (Mode == EEHMode::Training || Mode == EEHMode::Tutorial ? TEXT("PARTNER") : TEXT("CPU")) : FString::Printf(TEXT("P%d"), i + 1);
		const float NameW = P.Measure(Name, NameFont).X;
		const FLinearColor& WhoCol = SlotCpu[i] ? St::Silver : (i == 0 ? St::P1 : St::P2);
		{
			const FSlateFontInfo TF = Fonts.Sized(Fonts.BodyBold, St::Type::Label);
			const float TW = P.Measure(Who, TF).X + 22.0f;
			const FVector2f TP(bLeft ? X + NameW + 16.0f : X + BarW - NameW - 16.0f - TW, Y + BarH + 14);
			P.Round(TP, FVector2f(TW, 32), St::Alpha(St::Abyss, 0.75f), 5);
			P.NextLayer();
			P.Frame(TP, FVector2f(TW, 32), WhoCol, 2.0f);
			P.Text(Who, TP + FVector2f(TW * 0.5f, 16), TF, WhoCol, 0.5f, 0.5f, false);
		}
		// Rounds beside the timer: filled crescents for rounds won, outlines for rounds still to win.
		if (bVersus)
		{
			const float PlateX = bLeft ? 812.0f : 1024.0f;
			P.Round(FVector2f(PlateX, 128), FVector2f(84, 40), St::Plate, 8);
			P.NextLayer();
			for (int32 r = 0; r < Rules.roundsToWin; ++r)
			{
				const FVector2f Ctr(bLeft ? 874.0f - r * 40.0f : 1046.0f + r * 40.0f, 141.0f);
				EHUIShapes::Crescent(P, Ctr, 13.0f, r < F.roundWins ? St::Silver : St::Alpha(St::Silver, 0.55f), r < F.roundWins);
			}
		}
		// The fighter's gauge, under their own name.
		const float GW = 420.0f;
		const float GX = bLeft ? 110.0f : 1810.0f - GW;
		const float GY = 150.0f;
		const float Meter = static_cast<float>(F.meter) / Rules.meterMax;
		const FLinearColor& GCol = Accent(Char);
		const bool bFull = (Char == 0 && F.meter >= Rules.meterMax) || (Char == 1 && F.meter >= Rules.meterMax / 2);
		P.Rect(FVector2f(GX, GY), FVector2f(GW, 14), St::Track);
		float Shown = Meter;
		FLinearColor ShownCol = GCol;
		if (F.auraFrames > 0)
		{
			Shown = static_cast<float>(F.auraFrames) / 480.0f;
			ShownCol = FMath::Lerp(GCol, FLinearColor::White, 0.25f + 0.25f * FMath::Sin(static_cast<float>(RenderTime) * 9.0f));
		}
		P.Rect(FVector2f(bLeft ? GX : GX + GW * (1.0f - Shown), GY), FVector2f(GW * Shown, 14), ShownCol);
		P.Frame(FVector2f(GX - 2, GY - 2), FVector2f(GW + 4, 18), bFull || F.auraFrames > 0 ? GCol : St::Alpha(St::Silver, 0.45f), 2.0f);
		if (Char == 1)
		{
			// Ashka's flame moves cost half the gauge: a tick marks the half.
			P.Rect(FVector2f(GX + GW * 0.5f - 1, GY - 5), FVector2f(2, 24), St::Alpha(St::TextPrimary, 0.85f));
		}
		const FString Label = CP.GaugeLabel.ToString() + (F.auraFrames > 0 ? TEXT("  ·  ACTIVE") : (bFull ? TEXT("  ·  READY") : TEXT("")));
		P.Text(Label, FVector2f(bLeft ? GX + GW + 16.0f : GX - 16.0f, GY + 7.0f), Fonts.Sized(Fonts.BodyBold, St::Type::Label), bFull || F.auraFrames > 0 ? AccentText(Char) : St::TextSecondary, bLeft ? 0.0f : 1.0f, 0.5f);
		// Combo counter on the attacker's side.
		const eh::FighterState& Def = S.f[1 - i];
		if (Def.combo >= 2 && (Def.state == eh::FState::Hitstun || Def.state == eh::FState::Knockdown))
		{
			const float CX = bLeft ? 110.0f : 1810.0f;
			P.Text(FString::Printf(TEXT("%d HITS"), Def.combo), FVector2f(CX, 330), Fonts.Sized(Fonts.Display, 46), St::TextPrimary, bLeft ? 0.0f : 1.0f, 0.5f);
			P.Text(FString::Printf(TEXT("%d damage"), Def.comboDamage), FVector2f(CX, 378), Fonts.Sized(Fonts.BodyMedium, St::Type::Body), St::TextSecondary, bLeft ? 0.0f : 1.0f, 0.5f);
		}
	}
	// Timer on a near-opaque plate, so its contrast never depends on the stage.
	if (bVersus)
	{
		const int32 Seconds = FMath::CeilToInt(S.timer / static_cast<float>(eh::kTickHz));
		P.Round(FVector2f(902, 30), FVector2f(116, 92), St::Plate, 10);
		P.NextLayer();
		P.Frame(FVector2f(902, 30), FVector2f(116, 92), St::Alpha(St::Silver, 0.6f), 2.0f);
		P.Text(FString::Printf(TEXT("%d"), Seconds), FVector2f(960, 76), Fonts.Sized(Fonts.Display, 50), Seconds <= 10 ? St::Warning : St::TextPrimary, 0.5f, 0.5f);
	}
	for (const FEHCallout& Co : Callouts)
	{
		const float Fade = FMath::Clamp((Co.Life - Co.Age) / 0.25f, 0.0f, 1.0f);
		const float Rise = Co.Age * 18.0f;
		P.Text(Co.Text, FVector2f(Co.Side == 0 ? 110.0f : 1810.0f, 270.0f - Rise), Fonts.Sized(Fonts.Display, 34), A(Co.Color, Fade), Co.Side == 0 ? 0.0f : 1.0f, 0.5f);
	}
	for (const FEHBanner& B : Banners)
	{
		const float Fade = FMath::Clamp(B.Age / 0.12f, 0.0f, 1.0f) * FMath::Clamp((B.Life - B.Age) / 0.3f, 0.0f, 1.0f);
		if (!B.Text.IsEmpty())
		{
			P.Gradient(FVector2f(P.VirtualMin.X, 440), FVector2f(Wide, 200), FLinearColor(0, 0, 0, 0), FLinearColor(0, 0, 0, 0.45f * Fade), 6);
			// One fixed size (glyphs warmed on the title screen): a growing size made Slate rasterise new large glyphs
			// during round transitions, which hitched.
			P.Text(B.Text, FVector2f(960, 540), Fonts.Sized(Fonts.Display, 104), A(B.Color, Fade), 0.5f, 0.5f);
		}
		if (!B.Sub.IsEmpty() && B.Age > 0.0f)
		{
			P.Text(B.Sub, FVector2f(960, 640), Fonts.Sized(Fonts.DisplayLight, 36), A(St::TextPrimary, Fade), 0.5f, 0.5f);
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
			P.Text(i == 0 ? TEXT("INPUT") : TEXT("PARTNER"), FVector2f(X, 430), Fonts.Sized(Fonts.BodyBold, EHStyle::Type::Label), Muted, bLeft ? 0.0f : 1.0f, 0.5f);
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
				P.Text(Line, FVector2f(X, 460 + k * 28), Fonts.Sized(Fonts.BodyMedium, EHStyle::Type::Label), A(Bone, 1.0f - k * 0.04f), bLeft ? 0.0f : 1.0f, 0.5f);
			}
		}
	}
	if (bShowFrameData)
	{
		namespace St = EHStyle;
		// The number a player acts on (frame advantage) large and signed; the move and the states beside it.
		const FVector2f Box(520, 846);
		P.Round(Box, FVector2f(880, 124), St::Plate, 8);
		P.NextLayer();
		P.Frame(Box, FVector2f(880, 124), St::Alpha(St::Silver, 0.35f), 1.0f);
		FSlateFontInfo LabelF = Fonts.Sized(Fonts.BodyBold, St::Type::Label);
		LabelF.LetterSpacing = 120;
		P.Text(TEXT("ADVANTAGE"), Box + FVector2f(40, 30), LabelF, St::TextSecondary, 0.0f, 0.5f);
		FString AdvText = TEXT("-");
		FLinearColor AdvCol = St::TextSecondary;
		if (S.lastAdvantageValid)
		{
			const int32 V = S.lastAdvantagePlayer == 0 ? S.lastAdvantage : -S.lastAdvantage;
			AdvText = V == 0 ? FString(TEXT("0")) : FString::Printf(TEXT("%+d"), V);
			AdvCol = V > 0 ? St::Success : (V < 0 ? St::Warning : St::TextPrimary);
		}
		P.Text(AdvText, Box + FVector2f(40, 82), Fonts.Sized(Fonts.Display, 44), AdvCol, 0.0f, 0.5f);
		P.Rect(Box + FVector2f(220, 22), FVector2f(1, 80), St::Alpha(St::Silver, 0.35f));
		const FString Move = LastMoveName[0].IsEmpty() ? TEXT("-") : LastMoveName[0];
		const float MoveW = P.Text(Move, Box + FVector2f(250, 40), Fonts.Sized(Fonts.BodyBold, St::Type::Body), St::TextPrimary, 0.0f, 0.5f).X;
		P.Text(LastMoveFrames[0], Box + FVector2f(250 + MoveW + 18, 40), Fonts.Sized(Fonts.Body, St::Type::Body), St::TextSecondary, 0.0f, 0.5f);
		// Crouching is a posture of the neutral, guard, stun and low-attack states; it is shown with the state.
		auto Posture = [this](int32 i) {
			const FString Name = UTF8_TO_TCHAR(eh::StateName(Match->State().f[i].state));
			return Match->IsCrouching(i) ? Name + TEXT(" (crouching)") : Name;
		};
		P.Text(FString::Printf(TEXT("You: %s     Partner: %s"), *Posture(0), *Posture(1)), Box + FVector2f(250, 86), Fonts.Sized(Fonts.Body, St::Type::Label), St::TextPrimary, 0.0f, 0.5f);
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
	// Below the HUD's name and gauge rows (which end at about y = 172).
	const FVector2f Pos(460, 204);
	P.Round(Pos, FVector2f(1000, 172), FLinearColor(0, 0, 0, 0.62f), 8);
	P.NextLayer();
	P.Rect(Pos, FVector2f(1000, 3), Violet);
	P.Text(FString::Printf(TEXT("%d / %d   %s"), LessonStep + 1, Lesson.Num(), *Step.Title), Pos + FVector2f(32, 36), Fonts.Sized(Fonts.Display, 28), Bone, 0.0f, 0.5f);
	// Progress through the lesson: one segment per step; done steps filled, the current one outlined (shape and fill,
	// not colour alone), later ones dim.
	{
		const int32 N = Lesson.Num();
		const float Gap = 6.0f;
		const float SegW = (1000.0f - 64.0f - Gap * (N - 1)) / FMath::Max(1, N);
		for (int32 k = 0; k < N; ++k)
		{
			const FVector2f SP = Pos + FVector2f(32 + k * (SegW + Gap), 156);
			if (k < LessonStep || (k == LessonStep && LessonDoneAge >= 0.0f))
			{
				P.Rect(SP, FVector2f(SegW, 6), EHStyle::Success);
			}
			else if (k == LessonStep)
			{
				P.Frame(SP - FVector2f(0, 1), FVector2f(SegW, 8), EHStyle::FocusText, 2.0f);
			}
			else
			{
				P.Rect(SP, FVector2f(SegW, 6), EHStyle::Alpha(EHStyle::Silver, 0.25f));
			}
		}
	}
	P.Text(Step.Body, Pos + FVector2f(32, 82), Fonts.Sized(Fonts.Body, 22), Bone, 0.0f, 0.5f);
	if (LessonStep < Lesson.Num() - 1)
	{
		const bool bDone = LessonDoneAge >= 0.0f;
		P.Text(bDone ? TEXT("Done") : FString::Printf(TEXT("%d / %d"), FMath::Min(LessonCount, Step.Goal), Step.Goal), Pos + FVector2f(968, 36), Fonts.Sized(Fonts.BodyBold, 24), bDone ? EHStyle::Success : Muted, 1.0f, 0.5f);
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
	namespace St = EHStyle;
	P.Fill(FLinearColor(0, 0, 0, 0.45f));
	const eh::MatchState& S = Match->State();
	// The decision first: who won, then what to do next (Rematch has focus), then the numbers.
	FString Headline = TEXT("DRAW");
	if (LastWinner == 0 || LastWinner == 1)
	{
		Headline = Pres.Get(CharId(SlotChar[LastWinner])).DisplayName.ToString().ToUpper() + TEXT(" WINS");
	}
	P.Text(Headline, FVector2f(960, 130), Fonts.Sized(Fonts.Display, 76), St::TextPrimary, 0.5f, 0.5f);
	auto WhoOf = [this](int32 i) { return SlotCpu[i] ? FString(TEXT("CPU")) : FString::Printf(TEXT("Player %d"), i + 1); };
	if (LastWinner == 0 || LastWinner == 1)
	{
		P.Text(WhoOf(LastWinner), FVector2f(960, 200), Fonts.Sized(Fonts.DisplayLight, 28), LastWinner == 0 ? St::P1 : St::P2, 0.5f, 0.5f);
	}
	PaintMenu(P, FString(), true, 246.0f);
	const FVector2f Table(560, 500);
	const bool bThrows = Rules.ThrowsEnabled();
	const int32 Rows = bThrows ? 5 : 4;
	P.Round(Table, FVector2f(800, 70 + Rows * 42), St::Panel, 8);
	P.NextLayer();
	// Column heads: each fighter and who played it, so the numbers are never ambiguous.
	for (int32 i = 0; i < 2; ++i)
	{
		const FString Head = Pres.Get(CharId(SlotChar[i])).DisplayName.ToString().ToUpper() + TEXT("  ·  ") + WhoOf(i).ToUpper();
		P.Text(Head, FVector2f(i == 0 ? 640.0f : 1280.0f, Table.Y + 30), Fonts.Sized(Fonts.BodyBold, St::Type::Label), i == 0 ? St::P1 : St::P2, 0.5f, 0.5f);
	}
	P.Rect(FVector2f(Table.X + 30, Table.Y + 54), FVector2f(740, 1), A(Edge, 0.6f));
	const TCHAR* Labels[] = {TEXT("Rounds"), TEXT("Damage dealt"), TEXT("Longest combo"), TEXT("Throws landed"), TEXT("Deflects")};
	for (int32 r = 0, Row = 0; r < 5; ++r)
	{
		if (r == 3 && !bThrows)
		{
			continue;   // no throws in this rule set
		}
		const float Y = Table.Y + 82 + (Row++) * 42;
		P.Text(Labels[r], FVector2f(960, Y), Fonts.Sized(Fonts.BodyMedium, St::Type::Body), St::TextSecondary, 0.5f, 0.5f);
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
			P.Text(FString::Printf(TEXT("%d"), V), FVector2f(i == 0 ? 640.0f : 1280.0f, Y), Fonts.Sized(Fonts.BodyBold, St::Type::Body + 2.0f), St::TextPrimary, 0.5f, 0.5f);
		}
	}
}

void AEHGameDirector::PaintMoveList(FEHPainter& P)
{
	namespace St = EHStyle;
	P.Fill(FLinearColor(0, 0, 0, 0.55f));
	const int32 C = SelectCursor[0];
	const FEHCharacterPresentation& CP = Pres.Get(CharId(C));
	const eh::CharacterDef& Def = Chars[C];
	P.Text(CP.DisplayName.ToString(), FVector2f(960, 70), Fonts.Sized(Fonts.Display, St::Type::Title), St::TextPrimary, 0.5f, 0.5f);
	P.Text(TEXT("‹  Move List  ›"), FVector2f(960, 118), Fonts.Sized(Fonts.DisplayLight, St::Type::Body), St::TextSecondary, 0.5f, 0.5f);
	const float Left = 100.0f;
	const float Right = 1820.0f;
	P.Round(FVector2f(Left, 160), FVector2f(Right - Left, 822), St::Panel, 8);
	P.NextLayer();
	const FSlateFontInfo Head = Fonts.Sized(Fonts.BodyBold, St::Type::Label);
	const FSlateFontInfo RowF = Fonts.Sized(Fonts.Body, St::Type::Body);
	const FSlateFontInfo NoteF = Fonts.Sized(Fonts.Body, St::Type::Label);
	const float Cols[] = {140, 440, 712, 812, 912};
	const float NoteW = Right - Cols[4] - 24.0f;
	P.Text(TEXT("Technique"), FVector2f(Cols[0], 196), Head, St::TextSecondary, 0.0f, 0.5f);
	P.Text(TEXT("Input"), FVector2f(Cols[1], 196), Head, St::TextSecondary, 0.0f, 0.5f);
	P.Text(TEXT("Startup"), FVector2f(Cols[2], 196), Head, St::TextSecondary, 0.0f, 0.5f);
	P.Text(TEXT("Damage"), FVector2f(Cols[3], 196), Head, St::TextSecondary, 0.0f, 0.5f);
	P.Text(TEXT("Notes"), FVector2f(Cols[4], 196), Head, St::TextSecondary, 0.0f, 0.5f);
	// Collect the rows first: a note wider than its column wraps onto a second line, and the spacing adapts so every
	// row fits above the prompt row.
	struct FRow
	{
		const eh::MoveDef* Move = nullptr;
		FString Id;
		TArray<FString> Note;
	};
	TArray<FRow> Rows;
	int32 ExtraLines = 0;
	for (const eh::MoveDef& M : Def.moves)
	{
		if (M.kind == eh::MoveKind::Throw && !Rules.ThrowsEnabled())
		{
			continue;   // the throw stays in the data but is not part of this rule set
		}
		FRow R;
		R.Move = &M;
		R.Id = UTF8_TO_TCHAR(M.id.c_str());
		const FText* Note = CP.MoveNotes.Find(R.Id);
		TArray<FString> Words;
		(Note ? Note->ToString() : FString()).ParseIntoArray(Words, TEXT(" "));
		FString LineText;
		for (const FString& Word : Words)
		{
			const FString Try = LineText.IsEmpty() ? Word : LineText + TEXT(" ") + Word;
			if (!LineText.IsEmpty() && P.Measure(Try, NoteF).X > NoteW && R.Note.Num() == 0)
			{
				R.Note.Add(LineText);
				LineText = Word;
			}
			else
			{
				LineText = Try;
			}
		}
		if (!LineText.IsEmpty())
		{
			R.Note.Add(LineText);
		}
		ExtraLines += FMath::Max(0, R.Note.Num() - 1);
		Rows.Add(MoveTemp(R));
	}
	const float Top = 222.0f;
	const float Bottom = 970.0f;
	const float ExtraH = 26.0f;
	const float RowH = FMath::Clamp((Bottom - Top - ExtraLines * ExtraH) / FMath::Max(1, Rows.Num()), 36.0f, 48.0f);
	float Y = Top + RowH * 0.5f;
	for (const FRow& R : Rows)
	{
		const eh::MoveDef& M = *R.Move;
		const float Extra = R.Note.Num() > 1 ? ExtraH : 0.0f;
		const float Mid = Y + Extra * 0.5f;
		// Inputs are drawn with the viewer's own buttons: direction words, then the action's button glyph.
		const FString DirText = M.air ? TEXT("In a jump: ") : (M.down ? TEXT("Down + ") : (M.dir == eh::DirReq::Forward ? TEXT("Toward + ") : (M.dir == eh::DirReq::Back ? TEXT("Away + ") : TEXT(""))));
		const EEHAction Act = M.button == eh::BtnLight ? EEHAction::Light : (M.button == eh::BtnHeavy ? EEHAction::Heavy : (M.button == eh::BtnSpecial ? EEHAction::Special : (M.button == eh::BtnThrow ? EEHAction::Throw : EEHAction::Dodge)));
		int32 Repeats = 1;
		FString Suffix;
		if (R.Id == TEXT("L2")) Repeats = 2;
		if (R.Id == TEXT("L3")) Repeats = 3;
		if (M.kind == eh::MoveKind::Dodge && M.dir == eh::DirReq::Any) Suffix = TEXT("  away or neutral");
		const FString Startup = M.hits.empty() ? FString(TEXT("-")) : FString::Printf(TEXT("%d"), M.hits.front().frames.first);
		const FString Damage = M.kind == eh::MoveKind::Throw ? FString::Printf(TEXT("%d"), Def.throws[static_cast<size_t>(M.throwIndex)].damage) : (M.hits.empty() ? FString(TEXT("-")) : FString::Printf(TEXT("%d"), M.hits.front().damage));
		P.Text(UTF8_TO_TCHAR(M.name.c_str()), FVector2f(Cols[0], Mid), Fonts.Sized(Fonts.BodyBold, St::Type::Body), St::TextPrimary, 0.0f, 0.5f);
		{
			float X = Cols[1];
			if (!DirText.IsEmpty())
			{
				X += P.Text(DirText, FVector2f(X, Mid), RowF, St::FocusText, 0.0f, 0.5f).X + 4.0f;
			}
			const float G = 34.0f;
			for (int32 r = 0; r < Repeats; ++r)
			{
				X += PaintPrompt(P, FVector2f(X, Mid - G * 0.5f), FEHHint::Act(Act, FString()), EHDeviceNone, G) + 6.0f;
			}
			if (!Suffix.IsEmpty())
			{
				P.Text(Suffix, FVector2f(X, Mid), Fonts.Sized(Fonts.Body, St::Type::Label), St::TextSecondary, 0.0f, 0.5f);
			}
		}
		P.Text(Startup, FVector2f(Cols[2], Mid), RowF, St::TextPrimary, 0.0f, 0.5f);
		P.Text(Damage, FVector2f(Cols[3], Mid), RowF, St::TextPrimary, 0.0f, 0.5f);
		for (int32 l = 0; l < R.Note.Num(); ++l)
		{
			P.Text(R.Note[l], FVector2f(Cols[4], Mid + (l - (R.Note.Num() - 1) * 0.5f) * ExtraH), NoteF, St::TextSecondary, 0.0f, 0.5f);
		}
		Y += RowH + Extra;
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
