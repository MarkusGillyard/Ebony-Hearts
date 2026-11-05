#include "EHUICanvas.h"

#include "Brushes/SlateColorBrush.h"
#include "Brushes/SlateRoundedBoxBrush.h"
#include "EHGameDirector.h"
#include "Fonts/CompositeFont.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"

namespace EHUIDetail
{
const FSlateColorBrush& White()
{
	static const FSlateColorBrush Brush(FLinearColor::White);
	return Brush;
}

const FSlateRoundedBoxBrush& RoundBrush()
{
	static const FSlateRoundedBoxBrush Brush(FLinearColor::White, 6.0f);
	return Brush;
}
}
using namespace EHUIDetail;

void FEHFonts::Load(FString& OutMissing)
{
	auto Make = [this, &OutMissing](const TCHAR* File) -> FSlateFontInfo {
		const FString Path = FPaths::ProjectContentDir() / TEXT("UI/Fonts") / File;
		if (!IFileManager::Get().FileExists(*Path))
		{
			OutMissing += FString(File) + TEXT(" ");
			return FCoreStyle::GetDefaultFontStyle("Regular", 16);
		}
		TSharedPtr<const FCompositeFont> Font = MakeShared<FStandaloneCompositeFont>(NAME_None, Path, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
		Keep.Add(Font);
		return FSlateFontInfo(Font, 16.0f);
	};
	Display = Make(TEXT("Cinzel-Bold.ttf"));
	DisplayLight = Make(TEXT("Cinzel-Regular.ttf"));
	Body = Make(TEXT("AlegreyaSans-Regular.ttf"));
	BodyMedium = Make(TEXT("AlegreyaSans-Medium.ttf"));
	BodyBold = Make(TEXT("AlegreyaSans-Bold.ttf"));
	bLoaded = OutMissing.IsEmpty();
}

FSlateFontInfo FEHFonts::Sized(const FSlateFontInfo& Base, float Size) const
{
	FSlateFontInfo F = Base;
	F.Size = Size;
	return F;
}

FEHPainter::FEHPainter(const FGeometry& InGeo, FSlateWindowElementList& InOut, int32 InLayer, float UIScale)
	: Layer(InLayer)
	, Geo(InGeo)
	, Out(InOut)
{
	Local = FVector2f(InGeo.GetLocalSize());
	// Fit a 16:9 virtual canvas; the UI scale setting enlarges everything around the centre.
	const float Fit = FMath::Min(Local.X / 1920.0f, Local.Y / 1080.0f);
	Scale = Fit * UIScale;
	Origin = (Local - FVector2f(1920.0f, 1080.0f) * Scale) * 0.5f;
	VirtualMin = ToVirtual(FVector2f(0, 0));
	VirtualMax = ToVirtual(Local);
}

FPaintGeometry FEHPainter::Paint(FVector2f Pos, FVector2f Size) const
{
	return Geo.ToPaintGeometry(Size, FSlateLayoutTransform(Scale, Origin + Pos * Scale));
}

void FEHPainter::Fill(const FLinearColor& Color)
{
	FSlateDrawElement::MakeBox(Out, Layer, Geo.ToPaintGeometry(), &White(), ESlateDrawEffect::None, Color);
}

void FEHPainter::Rect(FVector2f Pos, FVector2f Size, const FLinearColor& Color)
{
	FSlateDrawElement::MakeBox(Out, Layer, Paint(Pos, Size), &White(), ESlateDrawEffect::None, Color);
}

void FEHPainter::Round(FVector2f Pos, FVector2f Size, const FLinearColor& Color, float Radius)
{
	FSlateDrawElement::MakeBox(Out, Layer, Paint(Pos, Size), &RoundBrush(), ESlateDrawEffect::None, Color);
}

void FEHPainter::Frame(FVector2f Pos, FVector2f Size, const FLinearColor& Color, float Thickness)
{
	Rect(Pos, FVector2f(Size.X, Thickness), Color);
	Rect(Pos + FVector2f(0, Size.Y - Thickness), FVector2f(Size.X, Thickness), Color);
	Rect(Pos, FVector2f(Thickness, Size.Y), Color);
	Rect(Pos + FVector2f(Size.X - Thickness, 0), FVector2f(Thickness, Size.Y), Color);
}

void FEHPainter::Gradient(FVector2f Pos, FVector2f Size, const FLinearColor& Top, const FLinearColor& Bottom, int32 Steps)
{
	const float H = Size.Y / Steps;
	for (int32 i = 0; i < Steps; ++i)
	{
		const float T = (i + 0.5f) / Steps;
		Rect(Pos + FVector2f(0, H * i), FVector2f(Size.X, H + 0.5f), FMath::Lerp(Top, Bottom, T));
	}
}

void FEHPainter::Line(const TArray<FVector2f>& Points, const FLinearColor& Color, float Thickness)
{
	TArray<FVector2f> LocalPts;
	LocalPts.Reserve(Points.Num());
	for (const FVector2f& P : Points)
	{
		LocalPts.Add(Origin + P * Scale);
	}
	FSlateDrawElement::MakeLines(Out, Layer, Geo.ToPaintGeometry(), MoveTemp(LocalPts), ESlateDrawEffect::None, Color, true, Thickness * Scale);
}

void FEHPainter::Image(const FSlateBrush& Brush, FVector2f Pos, FVector2f Size, const FLinearColor& Tint)
{
	FSlateDrawElement::MakeBox(Out, Layer, Paint(Pos, Size), &Brush, ESlateDrawEffect::None, Tint);
}

FVector2f FEHPainter::Measure(const FString& Str, const FSlateFontInfo& Font) const
{
	const TSharedRef<FSlateFontMeasure> Measurer = FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
	return FVector2f(Measurer->Measure(Str, Font, 1.0f));
}

FVector2f FEHPainter::Text(const FString& Str, FVector2f Pos, const FSlateFontInfo& Font, const FLinearColor& Color, float AlignX, float AlignY, bool bShadow)
{
	const FVector2f Size = Measure(Str, Font);
	const FVector2f TopLeft = Pos - FVector2f(Size.X * AlignX, Size.Y * AlignY);
	if (bShadow)
	{
		const FLinearColor Shadow(0.0f, 0.0f, 0.0f, 0.75f * Color.A);
		FSlateDrawElement::MakeText(Out, Layer, Paint(TopLeft + FVector2f(2.0f, 2.0f), Size), Str, Font, ESlateDrawEffect::None, Shadow);
	}
	FSlateDrawElement::MakeText(Out, Layer + 1, Paint(TopLeft, Size), Str, Font, ESlateDrawEffect::None, Color);
	return Size;
}

void SEHCanvas::Construct(const FArguments& InArgs)
{
	Director = InArgs._Director;
	SetCanTick(false);
	// The UI animates every frame, so it is never cached.
	ForceVolatile(true);
}

int32 SEHCanvas::OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const
{
	if (AEHGameDirector* D = Director.Get())
	{
		FEHPainter P(AllottedGeometry, OutDrawElements, LayerId, D->UIScale());
		D->PaintUI(P);
		return P.Layer + 2;
	}
	return LayerId;
}
