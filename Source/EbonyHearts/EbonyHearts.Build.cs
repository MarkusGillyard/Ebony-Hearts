using UnrealBuildTool;

public class EbonyHearts : ModuleRules
{
	public EbonyHearts(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "AnimationCore", "InputCore", "ApplicationCore",
			"Slate", "SlateCore", "ProceduralMeshComponent", "AudioMixer", "Json", "RHI", "RenderCore"
		});
		// The combat core is plain C++ shared with the standalone test build in Tests/Core.
		PublicIncludePaths.Add(System.IO.Path.Combine(ModuleDirectory, "Core"));
	}
}
