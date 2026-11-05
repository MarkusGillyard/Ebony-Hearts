using UnrealBuildTool;

public class EbonyHeartsEditorTarget : TargetRules
{
	public EbonyHeartsEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("EbonyHearts");
	}
}
