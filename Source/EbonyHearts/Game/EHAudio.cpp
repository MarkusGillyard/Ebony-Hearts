#include "EHAudio.h"

#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace EHAudioDetail
{
const TCHAR* Folder(EEHSoundCat Cat)
{
	switch (Cat)
	{
	case EEHSoundCat::Ui: return TEXT("UI");
	case EEHSoundCat::Ambience: return TEXT("Ambience");
	case EEHSoundCat::Music: return TEXT("Music");
	default: return TEXT("Combat");
	}
}
}

void FEHAudio::Init(UWorld* InWorld)
{
	World = InWorld;
}

void FEHAudio::SetVolumes(int32 Master, int32 Music, int32 Effects, int32 Ambience)
{
	const float M = Master / 100.0f;
	Gain[static_cast<int32>(EEHSoundCat::Effects)] = M * Effects / 100.0f;
	Gain[static_cast<int32>(EEHSoundCat::Ui)] = M * Effects / 100.0f;
	Gain[static_cast<int32>(EEHSoundCat::Ambience)] = M * Ambience / 100.0f;
	Gain[static_cast<int32>(EEHSoundCat::Music)] = M * Music / 100.0f;
	ApplyLoopVolumes();
}

USoundBase* FEHAudio::Find(FName Name, EEHSoundCat Cat)
{
	if (Name.IsNone())
	{
		return nullptr;
	}
	if (TStrongObjectPtr<USoundBase>* Found = Cache.Find(Name))
	{
		return Found->Get();
	}
	const FString Asset = FString::Printf(TEXT("S_%s"), *Name.ToString());
	const FString Path = FString::Printf(TEXT("/Game/Audio/%s/%s.%s"), EHAudioDetail::Folder(Cat), *Asset, *Asset);
	USoundBase* Sound = LoadObject<USoundBase>(nullptr, *Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (Sound == nullptr)
	{
		Missing.Add(Name);
	}
	Cache.Add(Name, TStrongObjectPtr<USoundBase>(Sound));
	return Sound;
}

void FEHAudio::Play(FName Name, EEHSoundCat Cat, float Volume, float Pitch)
{
	UWorld* W = World.Get();
	USoundBase* Sound = Find(Name, Cat);
	const float G = Gain[static_cast<int32>(Cat)] * Volume;
	if (W == nullptr || Sound == nullptr || G <= 0.001f)
	{
		return;
	}
	UGameplayStatics::PlaySound2D(W, Sound, G, Pitch);
	++Played;
}

void FEHAudio::PlayVaried(FName Base, int32 Variants, EEHSoundCat Cat, float Volume)
{
	const int32 Pick = Variants > 1 ? Rng.RandRange(1, Variants) : 1;
	const FName Name(*FString::Printf(TEXT("%s_%02d"), *Base.ToString(), Pick));
	Play(Name, Cat, Volume, Rng.FRandRange(0.96f, 1.04f));
}

void FEHAudio::StartMusic(FName Name, float FadeIn)
{
	if (Name == CurrentMusic && MusicComp.IsValid() && MusicComp->IsPlaying())
	{
		return;
	}
	StopMusic(0.6f);
	UWorld* W = World.Get();
	USoundBase* Sound = Find(Name, EEHSoundCat::Music);
	if (W == nullptr || Sound == nullptr)
	{
		return;
	}
	UAudioComponent* C = UGameplayStatics::CreateSound2D(W, Sound, 1.0f, 1.0f, 0.0f, nullptr, true, false);
	if (C)
	{
		MusicComp.Reset(C);
		CurrentMusic = Name;
		C->SetVolumeMultiplier(Gain[static_cast<int32>(EEHSoundCat::Music)] * MusicDuck);
		C->FadeIn(FadeIn, 1.0f);
	}
}

void FEHAudio::StopMusic(float FadeOut)
{
	if (MusicComp.IsValid())
	{
		MusicComp->FadeOut(FadeOut, 0.0f);
		MusicComp.Reset();
	}
	CurrentMusic = NAME_None;
}

void FEHAudio::StartAmbience(FName Name)
{
	if (AmbienceComp.IsValid() && AmbienceComp->IsPlaying())
	{
		return;
	}
	UWorld* W = World.Get();
	USoundBase* Sound = Find(Name, EEHSoundCat::Ambience);
	if (W == nullptr || Sound == nullptr)
	{
		return;
	}
	UAudioComponent* C = UGameplayStatics::CreateSound2D(W, Sound, 1.0f, 1.0f, 0.0f, nullptr, true, false);
	if (C)
	{
		AmbienceComp.Reset(C);
		C->SetVolumeMultiplier(Gain[static_cast<int32>(EEHSoundCat::Ambience)]);
		C->FadeIn(2.0f, 1.0f);
	}
}

void FEHAudio::StopAmbience()
{
	if (AmbienceComp.IsValid())
	{
		AmbienceComp->FadeOut(1.0f, 0.0f);
		AmbienceComp.Reset();
	}
}

void FEHAudio::SetMusicDuck(float Multiplier)
{
	MusicDuck = Multiplier;
	ApplyLoopVolumes();
}

void FEHAudio::ApplyLoopVolumes()
{
	if (MusicComp.IsValid())
	{
		MusicComp->SetVolumeMultiplier(Gain[static_cast<int32>(EEHSoundCat::Music)] * MusicDuck);
	}
	if (AmbienceComp.IsValid())
	{
		AmbienceComp->SetVolumeMultiplier(Gain[static_cast<int32>(EEHSoundCat::Ambience)]);
	}
}

TArray<FString> FEHAudio::MissingSounds() const
{
	TArray<FString> Out;
	for (const FName& N : Missing)
	{
		Out.Add(N.ToString());
	}
	return Out;
}
