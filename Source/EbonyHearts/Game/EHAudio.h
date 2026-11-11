// Named sound playback with category volumes. Sounds live under /Game/Audio/<Category>/S_<Name>.
#pragma once

#include "CoreMinimal.h"
#include "Components/AudioComponent.h"
#include "Sound/SoundBase.h"
#include "UObject/StrongObjectPtr.h"

class UAudioComponent;
class USoundBase;
class UWorld;

enum class EEHSoundCat : uint8 { Effects, Ui, Ambience, Music };

class FEHAudio
{
public:
	void Init(UWorld* InWorld);
	void SetVolumes(int32 Master, int32 Music, int32 Effects, int32 Ambience);
	// Plays a one-shot; missing sounds are recorded once and otherwise ignored.
	void Play(FName Name, EEHSoundCat Cat = EEHSoundCat::Effects, float Volume = 1.0f, float Pitch = 1.0f);
	void PlayVaried(FName Base, int32 Variants, EEHSoundCat Cat = EEHSoundCat::Effects, float Volume = 1.0f);
	void StartMusic(FName Name, float FadeIn = 1.5f);
	void StopMusic(float FadeOut = 1.0f);
	void StartAmbience(FName Name);
	void StopAmbience();
	void SetMusicDuck(float Multiplier);
	TArray<FString> MissingSounds() const;
	int32 PlayedCount() const { return Played; }

private:
	TWeakObjectPtr<UWorld> World;
	TMap<FName, TStrongObjectPtr<USoundBase>> Cache;
	TSet<FName> Missing;
	TStrongObjectPtr<UAudioComponent> MusicComp;
	TStrongObjectPtr<UAudioComponent> AmbienceComp;
	FName CurrentMusic;
	float Gain[4] = {1.0f, 1.0f, 1.0f, 1.0f};
	float MusicDuck = 1.0f;
	int32 Played = 0;
	FRandomStream Rng = FRandomStream(1234);

	USoundBase* Find(FName Name, EEHSoundCat Cat);
	void ApplyLoopVolumes();
};
