using UnrealBuildTool;

public class EbonyHearts : ModuleRules
{
	public EbonyHearts(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		// Each source file keeps file-local helpers (palettes, bit helpers) in namespaces it opens with "using"; unity
		// blobs would merge those files and make the names collide, so every file compiles on its own.
		bUseUnity = false;
		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "AnimationCore", "InputCore", "ApplicationCore",
			"Slate", "SlateCore", "ProceduralMeshComponent", "AudioMixer", "Json", "RHI", "RenderCore",
			"AIModule", "NavigationSystem", "GameplayTasks"
		});
		// The combat core is plain C++ shared with the standalone test build in Tests/Core.
		PublicIncludePaths.Add(System.IO.Path.Combine(ModuleDirectory, "Core"));
		bool bLinux = Target.Platform == UnrealTargetPlatform.Linux;
		if (bLinux)
		{
			PrivateDependencyModuleNames.Add("EbonyHeartsLinux");
		}
		PrivateDefinitions.Add("EH_LINUX_PLATFORM=" + (bLinux ? "1" : "0"));
	}
}
