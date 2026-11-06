#include "AudioMixerDevice.h"
#include "EHDisplayEventGuard.h"
#include "EHLinuxPlatform.h"
#include "EHSdlAudioOutput.h"
#include "Modules/ModuleManager.h"

namespace EHLinux
{
namespace
{
FDisplayEventGuard GDisplayGuard;
}

FPlatformReport GetPlatformReport()
{
	FPlatformReport R;
	R.bAudioOutputActive = FSdlAudioOutput::AnyStreamOpen();
	R.AudioBuffersDelivered = FSdlAudioOutput::BuffersDelivered();
	R.AudioSubmitsDropped = FSdlAudioOutput::SubmitsDropped();
	R.bDisplayGuardActive = GDisplayGuard.IsActive();
	R.DisplayEventsDeferred = GDisplayGuard.Deferred();
	R.DisplayEventsReplayed = GDisplayGuard.Replayed();
	return R;
}
}

// Selected as the audio device module by [Audio] AudioMixerModuleName in Config/Linux/LinuxEngine.ini.
class FEbonyHeartsLinuxModule final : public IAudioDeviceModule
{
public:
	virtual void StartupModule() override
	{
		IAudioDeviceModule::StartupModule();
		FModuleManager::Get().LoadModuleChecked(TEXT("AudioMixerCore"));
		if (!GIsEditor)
		{
			EHLinux::GDisplayGuard.Install();
		}
	}

	virtual void ShutdownModule() override
	{
		EHLinux::GDisplayGuard.Remove();
	}

	virtual bool IsAudioMixerModule() const override { return true; }

	virtual FAudioDevice* CreateAudioDevice() override
	{
		return new Audio::FMixerDevice(new EHLinux::FSdlAudioOutput());
	}

	virtual Audio::IAudioMixerPlatformInterface* CreateAudioMixerPlatformInterface() override
	{
		return new EHLinux::FSdlAudioOutput();
	}
};

IMPLEMENT_MODULE(FEbonyHeartsLinuxModule, EbonyHeartsLinux)
