using UnrealBuildTool;

public class EbonyHeartsTarget : TargetRules
{
	public EbonyHeartsTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("EbonyHearts");
	}
}
