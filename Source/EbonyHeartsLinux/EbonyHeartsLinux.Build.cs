using UnrealBuildTool;

// Linux platform layer: the game's SDL3 audio output and the X11 display-event guard.
public class EbonyHeartsLinux : ModuleRules
{
	public EbonyHeartsLinux(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core" });
		PrivateDependencyModuleNames.AddRange(new string[] { "CoreUObject", "Engine", "AudioMixer", "AudioMixerCore" });
		AddEngineThirdPartyPrivateStaticDependencies(Target, "SDL3");
		PublicSystemLibraries.Add("dl");
	}
}
