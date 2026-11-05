// Full-screen Slate canvas. The director paints every screen and the HUD through FEHPainter in a 1920x1080
// virtual space centred in the viewport; menus are driven by FEHInputRouter, not by Slate focus, so keyboard and
// every gamepad navigate identically.
#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"
#include "Styling/SlateBrush.h"
#include "Widgets/SLeafWidget.h"

class AEHGameDirector;
class FSlateWindowElementList;
class UTexture2D;

struct FEHFonts
{
	FSlateFontInfo Display;      // Cinzel Bold
	FSlateFontInfo DisplayLight; // Cinzel Regular
	FSlateFontInfo Body;         // Alegreya Sans Regular
	FSlateFontInfo BodyMedium;   // Alegreya Sans Medium
	FSlateFontInfo BodyBold;     // Alegreya Sans Bold
	bool bLoaded = false;
	void Load(FString& OutMissing);
	FSlateFontInfo Sized(const FSlateFontInfo& Base, float Size) const;

private:
	TArray<TSharedPtr<const FCompositeFont>> Keep;
};

class FEHPainter
{
public:
	FEHPainter(const FGeometry& InGeo, FSlateWindowElementList& InOut, int32 InLayer, float UIScale);

	FVector2f Origin;      // local position of virtual (0,0)
	float Scale = 1.0f;    // local units per virtual unit
	FVector2f Local;       // widget size in local units
	FVector2f VirtualMin;  // virtual coordinates of the visible area's top-left (can be negative on wide screens)
	FVector2f VirtualMax;
	int32 Layer;

	void Fill(const FLinearColor& Color);                 // whole widget
	void Rect(FVector2f Pos, FVector2f Size, const FLinearColor& Color);
	void Round(FVector2f Pos, FVector2f Size, const FLinearColor& Color, float Radius);
	void Frame(FVector2f Pos, FVector2f Size, const FLinearColor& Color, float Thickness);
	void Gradient(FVector2f Pos, FVector2f Size, const FLinearColor& Top, const FLinearColor& Bottom, int32 Steps = 12);
	void Line(const TArray<FVector2f>& Points, const FLinearColor& Color, float Thickness);
	void Image(const FSlateBrush& Brush, FVector2f Pos, FVector2f Size, const FLinearColor& Tint = FLinearColor::White);
	// Align: 0 = left/top, 0.5 = centre, 1 = right/bottom. Returns the drawn size in virtual units.
	FVector2f Text(const FString& Str, FVector2f Pos, const FSlateFontInfo& Font, const FLinearColor& Color, float AlignX = 0.0f, float AlignY = 0.0f, bool bShadow = true);
	FVector2f Measure(const FString& Str, const FSlateFontInfo& Font) const;
	FVector2f ToVirtual(FVector2f LocalPos) const { return (LocalPos - Origin) / Scale; }
	void NextLayer() { ++Layer; }

private:
	const FGeometry& Geo;
	FSlateWindowElementList& Out;
	FPaintGeometry Paint(FVector2f Pos, FVector2f Size) const;
};

class SEHCanvas : public SLeafWidget
{
public:
	SLATE_BEGIN_ARGS(SEHCanvas) {}
		SLATE_ARGUMENT(TWeakObjectPtr<AEHGameDirector>, Director)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& AllottedGeometry, const FSlateRect& MyCullingRect, FSlateWindowElementList& OutDrawElements, int32 LayerId, const FWidgetStyle& InWidgetStyle, bool bParentEnabled) const override;
	virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(1920.0, 1080.0); }

private:
	TWeakObjectPtr<AEHGameDirector> Director;
};
