#include "EHSettings.h"

#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

const TCHAR* EHActionName(EEHAction Action)
{
	switch (Action)
	{
	case EEHAction::Left: return TEXT("Left");
	case EEHAction::Right: return TEXT("Right");
	case EEHAction::Up: return TEXT("Up");
	case EEHAction::Down: return TEXT("Down");
	case EEHAction::Light: return TEXT("Light");
	case EEHAction::Heavy: return TEXT("Heavy");
	case EEHAction::Special: return TEXT("Special");
	case EEHAction::Throw: return TEXT("Grab");
	case EEHAction::Dodge: return TEXT("Dodge");
	case EEHAction::Block: return TEXT("Block");
	case EEHAction::Pause: return TEXT("Pause");
	case EEHAction::Reset: return TEXT("Reset");
	default: return TEXT("?");
	}
}

FEHBindings FEHBindings::Defaults()
{
	FEHBindings B;
	auto Set = [&B](EEHBindingSet S, EEHAction A, const FKey& K0, const FKey& K1 = EKeys::Invalid) {
		B.Keys[static_cast<int32>(S)][static_cast<int32>(A)][0] = K0;
		B.Keys[static_cast<int32>(S)][static_cast<int32>(A)][1] = K1;
	};
	using S = EEHBindingSet;
	using A = EEHAction;
	Set(S::KeyboardA, A::Left, EKeys::A);
	Set(S::KeyboardA, A::Right, EKeys::D);
	Set(S::KeyboardA, A::Up, EKeys::W);
	Set(S::KeyboardA, A::Down, EKeys::S);
	Set(S::KeyboardA, A::Light, EKeys::J, EKeys::Enter);
	Set(S::KeyboardA, A::Heavy, EKeys::K, EKeys::BackSpace);
	Set(S::KeyboardA, A::Special, EKeys::L);
	Set(S::KeyboardA, A::Throw, EKeys::I);
	Set(S::KeyboardA, A::Dodge, EKeys::O);
	Set(S::KeyboardA, A::Block, EKeys::SpaceBar);
	Set(S::KeyboardA, A::Pause, EKeys::Escape);
	Set(S::KeyboardA, A::Reset, EKeys::R);

	Set(S::KeyboardB, A::Left, EKeys::Left);
	Set(S::KeyboardB, A::Right, EKeys::Right);
	Set(S::KeyboardB, A::Up, EKeys::Up);
	Set(S::KeyboardB, A::Down, EKeys::Down);
	Set(S::KeyboardB, A::Light, EKeys::NumPadOne, EKeys::Comma);
	Set(S::KeyboardB, A::Heavy, EKeys::NumPadTwo, EKeys::Period);
	Set(S::KeyboardB, A::Special, EKeys::NumPadThree, EKeys::Slash);
	Set(S::KeyboardB, A::Throw, EKeys::NumPadFive, EKeys::Semicolon);
	Set(S::KeyboardB, A::Dodge, EKeys::NumPadSix, EKeys::Apostrophe);
	Set(S::KeyboardB, A::Block, EKeys::NumPadZero, EKeys::RightShift);
	Set(S::KeyboardB, A::Pause, EKeys::NumPadNine, EKeys::Equals);
	Set(S::KeyboardB, A::Reset, EKeys::NumPadSeven, EKeys::Hyphen);

	Set(S::Gamepad, A::Left, EKeys::Gamepad_DPad_Left);
	Set(S::Gamepad, A::Right, EKeys::Gamepad_DPad_Right);
	Set(S::Gamepad, A::Up, EKeys::Gamepad_DPad_Up);
	Set(S::Gamepad, A::Down, EKeys::Gamepad_DPad_Down);
	Set(S::Gamepad, A::Light, EKeys::Gamepad_FaceButton_Bottom);
	Set(S::Gamepad, A::Heavy, EKeys::Gamepad_FaceButton_Right);
	Set(S::Gamepad, A::Special, EKeys::Gamepad_FaceButton_Top);
	Set(S::Gamepad, A::Throw, EKeys::Gamepad_FaceButton_Left);
	Set(S::Gamepad, A::Dodge, EKeys::Gamepad_LeftShoulder, EKeys::Gamepad_LeftTrigger);
	Set(S::Gamepad, A::Block, EKeys::Gamepad_RightShoulder, EKeys::Gamepad_RightTrigger);
	Set(S::Gamepad, A::Pause, EKeys::Gamepad_Special_Right);
	Set(S::Gamepad, A::Reset, EKeys::Gamepad_Special_Left);
	return B;
}

EEHAction FEHBindings::Find(EEHBindingSet Set, const FKey& Key) const
{
	if (!Key.IsValid())
	{
		return EEHAction::Count;
	}
	const int32 S = static_cast<int32>(Set);
	for (int32 A = 0; A < EHActionCount; ++A)
	{
		for (int32 K = 0; K < EHKeysPerAction; ++K)
		{
			if (Keys[S][A][K] == Key)
			{
				return static_cast<EEHAction>(A);
			}
		}
	}
	return EEHAction::Count;
}

FString FEHBindings::Assign(EEHBindingSet Set, EEHAction Action, int32 Slot, const FKey& Key)
{
	const int32 S = static_cast<int32>(Set);
	const int32 A = static_cast<int32>(Action);
	const FKey Previous = Keys[S][A][Slot];
	FString Report;
	// Keyboard sets share one physical keyboard, so check both of them.
	TArray<int32> SetsToCheck = {S};
	if (Set == EEHBindingSet::KeyboardA) SetsToCheck.Add(static_cast<int32>(EEHBindingSet::KeyboardB));
	if (Set == EEHBindingSet::KeyboardB) SetsToCheck.Add(static_cast<int32>(EEHBindingSet::KeyboardA));
	for (int32 CS : SetsToCheck)
	{
		for (int32 CA = 0; CA < EHActionCount; ++CA)
		{
			for (int32 CK = 0; CK < EHKeysPerAction; ++CK)
			{
				if ((CS != S || CA != A || CK != Slot) && Keys[CS][CA][CK] == Key)
				{
					Keys[CS][CA][CK] = (CS == S) ? Previous : FKey(EKeys::Invalid);
					Report = FString::Printf(TEXT("%s moved from %s"), *Key.GetDisplayName().ToString(), EHActionName(static_cast<EEHAction>(CA)));
				}
			}
		}
	}
	Keys[S][A][Slot] = Key;
	return Report;
}

bool FEHBindings::HasConflicts(FString* OutReport) const
{
	TMap<FKey, FString> Seen;
	for (int32 S = 0; S < EHSetCount; ++S)
	{
		for (int32 A = 0; A < EHActionCount; ++A)
		{
			for (int32 K = 0; K < EHKeysPerAction; ++K)
			{
				const FKey& Key = Keys[S][A][K];
				if (!Key.IsValid())
				{
					continue;
				}
				// Gamepad keys may repeat across the gamepad set only; keyboard keys must be unique across both keyboard sets.
				const FString Owner = FString::Printf(TEXT("%d/%s"), S == static_cast<int32>(EEHBindingSet::Gamepad) ? 2 : 0, EHActionName(static_cast<EEHAction>(A)));
				if (const FString* Existing = Seen.Find(Key))
				{
					if (OutReport)
					{
						*OutReport = FString::Printf(TEXT("%s bound to %s and %s"), *Key.ToString(), **Existing, *Owner);
					}
					return true;
				}
				Seen.Add(Key, Owner);
			}
		}
	}
	return false;
}

FString FEHSettings::FilePath()
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("EbonyHearts"), TEXT("Settings.json"));
}

void FEHSettings::Clamp()
{
	WindowMode = FMath::Clamp(WindowMode, 0, 2);
	Resolution.X = FMath::Clamp(Resolution.X, 1280, 7680);
	Resolution.Y = FMath::Clamp(Resolution.Y, 720, 4320);
	Quality = FMath::Clamp(Quality, 0, 3);
	FrameCap = (FrameCap == 0 || FrameCap == 60 || FrameCap == 120 || FrameCap == 144 || FrameCap == 165 || FrameCap == 240) ? FrameCap : 0;
	RenderScale = FMath::Clamp(RenderScale, 50, 100);
	MasterVolume = FMath::Clamp(MasterVolume, 0, 100);
	MusicVolume = FMath::Clamp(MusicVolume, 0, 100);
	EffectsVolume = FMath::Clamp(EffectsVolume, 0, 100);
	AmbienceVolume = FMath::Clamp(AmbienceVolume, 0, 100);
	UIScale = FMath::Clamp(UIScale, 0.8f, 1.4f);
	CpuLevel = FMath::Clamp(CpuLevel, 0, 2);
	if (static_cast<uint8>(PromptStyle) > static_cast<uint8>(EEHPromptStyle::Xbox))
	{
		PromptStyle = EEHPromptStyle::Auto;
	}
}

FEHSettings FEHSettings::Load(FString* OutWarning)
{
	FEHSettings S;
	FString Text;
	const FString Path = FilePath();
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		return S;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		IFileManager::Get().Move(*(Path + TEXT(".bad")), *Path, true, true);
		if (OutWarning)
		{
			*OutWarning = TEXT("Settings file was unreadable; defaults restored.");
		}
		return S;
	}
	auto Int = [&Root](const TCHAR* Name, int32& Out) {
		double V = 0;
		if (Root->TryGetNumberField(Name, V)) Out = static_cast<int32>(V);
	};
	auto Bool = [&Root](const TCHAR* Name, bool& Out) {
		bool V = false;
		if (Root->TryGetBoolField(Name, V)) Out = V;
	};
	Int(TEXT("windowMode"), S.WindowMode);
	Int(TEXT("resX"), S.Resolution.X);
	Int(TEXT("resY"), S.Resolution.Y);
	Int(TEXT("quality"), S.Quality);
	Int(TEXT("frameCap"), S.FrameCap);
	Bool(TEXT("vsync"), S.bVSync);
	Int(TEXT("renderScale"), S.RenderScale);
	Int(TEXT("masterVolume"), S.MasterVolume);
	Int(TEXT("musicVolume"), S.MusicVolume);
	Int(TEXT("effectsVolume"), S.EffectsVolume);
	Int(TEXT("ambienceVolume"), S.AmbienceVolume);
	double Scale = S.UIScale;
	if (Root->TryGetNumberField(TEXT("uiScale"), Scale)) S.UIScale = static_cast<float>(Scale);
	Bool(TEXT("reduceShake"), S.bReduceShake);
	Bool(TEXT("reduceFlash"), S.bReduceFlash);
	Bool(TEXT("inputHints"), S.bInputHints);
	int32 Prompt = static_cast<int32>(S.PromptStyle);
	Int(TEXT("promptStyle"), Prompt);
	S.PromptStyle = static_cast<EEHPromptStyle>(FMath::Clamp(Prompt, 0, 3));
	Int(TEXT("cpuLevel"), S.CpuLevel);

	const TSharedPtr<FJsonObject>* BindingsObj = nullptr;
	if (Root->TryGetObjectField(TEXT("bindings"), BindingsObj))
	{
		FEHBindings Loaded = FEHBindings::Defaults();
		for (int32 Set = 0; Set < EHSetCount; ++Set)
		{
			for (int32 A = 0; A < EHActionCount; ++A)
			{
				const FString Field = FString::Printf(TEXT("%d.%s"), Set, EHActionName(static_cast<EEHAction>(A)));
				const TArray<TSharedPtr<FJsonValue>>* Arr = nullptr;
				if ((*BindingsObj)->TryGetArrayField(Field, Arr))
				{
					for (int32 K = 0; K < EHKeysPerAction; ++K)
					{
						const FKey Key = Arr->IsValidIndex(K) ? FKey(FName(*(*Arr)[K]->AsString())) : FKey(EKeys::Invalid);
						Loaded.Keys[Set][A][K] = Key.IsValid() ? Key : FKey(EKeys::Invalid);
					}
				}
			}
		}
		FString Report;
		if (Loaded.HasConflicts(&Report))
		{
			if (OutWarning)
			{
				*OutWarning = FString::Printf(TEXT("Saved controls had a conflict (%s); defaults restored."), *Report);
			}
		}
		else
		{
			S.Bindings = Loaded;
		}
	}
	S.Clamp();
	return S;
}

bool FEHSettings::Save() const
{
	TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
	Root->SetNumberField(TEXT("version"), 1);
	Root->SetNumberField(TEXT("windowMode"), WindowMode);
	Root->SetNumberField(TEXT("resX"), Resolution.X);
	Root->SetNumberField(TEXT("resY"), Resolution.Y);
	Root->SetNumberField(TEXT("quality"), Quality);
	Root->SetNumberField(TEXT("frameCap"), FrameCap);
	Root->SetBoolField(TEXT("vsync"), bVSync);
	Root->SetNumberField(TEXT("renderScale"), RenderScale);
	Root->SetNumberField(TEXT("masterVolume"), MasterVolume);
	Root->SetNumberField(TEXT("musicVolume"), MusicVolume);
	Root->SetNumberField(TEXT("effectsVolume"), EffectsVolume);
	Root->SetNumberField(TEXT("ambienceVolume"), AmbienceVolume);
	Root->SetNumberField(TEXT("uiScale"), UIScale);
	Root->SetBoolField(TEXT("reduceShake"), bReduceShake);
	Root->SetBoolField(TEXT("reduceFlash"), bReduceFlash);
	Root->SetBoolField(TEXT("inputHints"), bInputHints);
	Root->SetNumberField(TEXT("promptStyle"), static_cast<int32>(PromptStyle));
	Root->SetNumberField(TEXT("cpuLevel"), CpuLevel);
	TSharedRef<FJsonObject> BindingsObj = MakeShared<FJsonObject>();
	for (int32 Set = 0; Set < EHSetCount; ++Set)
	{
		for (int32 A = 0; A < EHActionCount; ++A)
		{
			TArray<TSharedPtr<FJsonValue>> Arr;
			for (int32 K = 0; K < EHKeysPerAction; ++K)
			{
				const FKey& Key = Bindings.Keys[Set][A][K];
				Arr.Add(MakeShared<FJsonValueString>(Key.IsValid() ? Key.GetFName().ToString() : FString()));
			}
			BindingsObj->SetArrayField(FString::Printf(TEXT("%d.%s"), Set, EHActionName(static_cast<EEHAction>(A))), Arr);
		}
	}
	Root->SetObjectField(TEXT("bindings"), BindingsObj);
	FString Text;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
	if (!FJsonSerializer::Serialize(Root, Writer))
	{
		return false;
	}
	// Write to a temporary file first so an interrupted save never leaves a truncated settings file.
	const FString Path = FilePath();
	const FString Temp = Path + TEXT(".tmp");
	return FFileHelper::SaveStringToFile(Text, *Temp) && IFileManager::Get().Move(*Path, *Temp, true, true);
}
