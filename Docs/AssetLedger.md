# Asset ledger and notices

Every asset in the slice is one of three kinds:
- original work made for Ebony Hearts by this repository's scripts
- creator-supplied
- built from the third-party inputs listed here

Original download URLs, acquisition dates and SHA-256 hashes for each third-party input are machine-readable in
`Docs/ThirdPartyManifest.json`, which `Tools/Docs/third_party_manifest.py` generates. Each hash was re-verified against
the original download record before use.

## Third-party inputs

| Input | Licence | Used for | Shipped as | Raw files in this repository |
|---|---|---|---|---|
| MakeHuman system assets (hm08 base mesh, eyes, eyebrows 001/006, eyelashes 01/02) | CC0 1.0 | Base bodies, eyes, brows and lashes of both fighters, reshaped and retextured | Cooked meshes and textures | No (fetched by the build) |
| MPFB 2.0.18 (Blender extension) | GPL-3.0-or-later code; CC0 bundled assets | Build tool for body shaping and the game_engine rig and weights | Not shipped (tool only) | No |
| Poly Haven: monastery_stone_floor, medieval_blocks_03, rusty_metal_04, weathered_planks | CC0 1.0 | Chapel floor, walls, iron and pews; graded, simplified and repacked | Cooked textures | No |
| ambientCG: Rock035, Ivory001B, Fabric066 | CC0 1.0 | Chapel stone dressing, candle wax, altar cloth | Cooked textures | No |
| ambientCG: Fabric001, Fabric034, Fabric040, Fabric066, Leather021, Leather026 | CC0 1.0 | Fabric and leather detail sampled into the fighters' garment textures | Cooked textures | No |
| Kenney: Impact Sounds, Interface Sounds, RPG Audio | CC0 1.0 | Layered under synthesized impacts, falls and steps; processed menu sounds; cloth and creak layers | Cooked audio | No |
| Cinzel 2.000 (Regular, Bold) | SIL OFL 1.1 | Display type | Unmodified font files with `OFL-Cinzel.txt` | Yes (`Content/UI/Fonts`) |
| Alegreya Sans (Regular, Medium, Bold) | SIL OFL 1.1 | Body type | Unmodified font files with `OFL-AlegreyaSans.txt` | Yes (`Content/UI/Fonts`) |
| ACCAD Open Motion Project, Male 2 BVH takes (ACCAD, The Ohio State University) | CC BY 3.0 Unported (attribution required) | Base motion for both fighters' idle stances (Male2_E8_Bounce, Male2_D1_StandToReady), retargeted onto the researched MMA and Muay Thai stances; Wren's 720 hook kick and tornado kick (Male2_G20, G9; both add a jump and an extra turn); Ashka's body kick and teep (Male2_G15, G17); Ashka's bow intro and bow win (Male2_D8_BowToReady, D7_WalkToBow) and both fighters' defeated pose (Male2_D4_ReadyToRelax, settling into the scripted slump) | Cooked animations | No (downloaded from accad.osu.edu) |
| Mixamo animations (Adobe), 29 clips plus the X Bot T-pose, exported from the creator's Adobe account | Mixamo: free; characters and animations are royalty free for personal, commercial and non-profit projects, including video games (Mixamo FAQ, helpx.adobe.com/creative-cloud/faq/mixamo-faq.html) | Base motion for Wren's jab and cross (and her jab-to-cross string, from one performance), roundhouse (MMA high kick), spinning back kick, walks, held guard, intro (boxing warm-up), win (victory), forward roll (a quick shoulder roll), double-leg slam and shoulder throw (each a paired attacker and victim); Ashka's held guard; Ashka's jab, horizontal elbow, step-in knee, flame elbow (stepping elbow), flying knee, walks and forward roll; both fighters' light and heavy hit, block, knockdown and KO reactions and get-ups; the fall of the fighter Ashka throws (a sweep fall, after her keyed clinch). Retargeted, retimed to the combat data, placed on the stances; the block reaction is layered onto the guard and the knockdown ends in the lying pose the get-up starts from | Cooked animations | No (raw exports kept outside the repository) |
| Unreal Engine 5.8.4 | Unreal Engine EULA | Engine | Engine runtime | No |

CC0 needs no attribution, but the in-game credits name the sources as a courtesy. The ACCAD motion capture is CC BY 3.0, so its attribution is required and appears in the in-game credits and `THIRD_PARTY_NOTICES.txt`: "Motion capture: Open Motion Project by ACCAD / The Ohio State University, CC BY 3.0; retargeted and retimed for this game." Mixamo needs no credit; the in-game credits and `THIRD_PARTY_NOTICES.txt` name it as a courtesy. CMU motion capture was used in earlier builds and no longer ships, so its credit was removed. "MakeHuman" is a trademark and
appears only as a credit. The SIL Open Font License texts ship next to the fonts. The fonts are unmodified, so the
licence's reserved-font-name clause does not apply.

Files deliberately excluded:
- MakeHuman hair and eyebrow files whose embedded metadata names a different author than the pack licence
- all MakeHuman skin textures (they carry a stamp)
- any non-commercial or no-derivatives dataset

## Original work (created for this slice)

- **Characters.** Garments, hair and braids, secondary chains, procedural skin/eye/hair/garment textures, and Ashka's
  crimson cross-shaped lamp tattoo emblem. Source: `Tools/Blender/characters`.
- **Chapel.** All stage geometry, the rose-window and lancet stained glass, candle flame, water ripple normal and decal
  atlas. Source: `Tools/Blender/chapel`.
- **Animation.** Both fighters' idle stances are built from ACCAD motion capture placed on stances designed from coaching sources (`Docs/Research.md`, "Fighting stances"; values in `Tools/Blender/anim/stances.json`). Wren's 720 hook kick and tornado kick and Ashka's body kick and teep come
  from ACCAD motion capture, and the Mixamo moves listed above from Mixamo animations, all by
  `Tools/Blender/anim/build_mocap.py`; the clips and timing anchors are listed in `mocap_clips.json`. Every other animation is still authored by script (`Tools/Blender/anim`),
  with motion that flows through its key poses rather than stopping at each one.
- **Audio.** Music (Theme, Battle, Training), the chapel ambience and all synthesized sound layers
  (`Tools/Audio`). No voices.
- **Effects.** Effect textures (`Tools/Assets/make_vfx_textures.py`), effect materials and the drawn button prompts.
- **Code and data.** All game code and data.

## Creator-supplied

- **Title card** (`/Game/UI/T_TitleCard`). Imported unmodified from the creator's file `Ebony Hearts Title Card`
  (PNG, 2172 × 724), SHA-256 `2856a3520ba7def78f39c1daeb6c8e1b4b119c637902d6a55e78598f5a401f0f`.
  - **Origin.** AI-generated. The creator generated it specifically for Ebony Hearts with OpenAI's ChatGPT image
    generation.
  - **Rights.** Confirmed by the creator on 2026-11-03. Under OpenAI's Terms of Use, the creator owns the output as
    between the creator and OpenAI, to the extent permitted by applicable law, and may use, modify, distribute and
    commercially incorporate it in Ebony Hearts. It is an authorized project asset.
  - **Copyright.** Including it does not imply that the unmodified, AI-generated image has exclusive copyright
    protection.
  - **Handling.** Keep the original file. Do not replace or redesign the title card without the creator's approval.

## Rights summary

Every shipped third-party input permits commercial use, modification and distribution of the cooked game. No paid,
login-gated, non-commercial or unclear-licence asset is used. Only the OFL font files are redistributed as raw files.
The other inputs are fetched from their original sources by the build and appear in the package only in cooked form.

## Required notices

The packaged game includes `THIRD_PARTY_NOTICES.txt` (this table in plain text, plus both OFL licence texts) and the
in-game credits. The credits carry the Unreal Engine notice:
"Unreal® Engine, Copyright 1998-2026, Epic Games, Inc. All rights reserved."
