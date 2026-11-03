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
| Unreal Engine 5.8.4 | Unreal Engine EULA | Engine | Engine runtime | No |

CC0 needs no attribution, but the in-game credits name the sources as a courtesy. "MakeHuman" is a trademark and
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
- **Animation.** Every animation, authored by script (`Tools/Blender/anim`). No motion capture was used.
- **Audio.** Music (Theme, Battle, Training), the chapel ambience and all synthesized sound layers
  (`Tools/Audio`). No voices.
- **Effects.** Effect textures (`Tools/Assets/make_vfx_textures.py`), effect materials and the drawn button prompts.
- **Code and data.** All game code and data.

## Creator-supplied

- **Title card** (`/Game/UI/T_TitleCard`), SHA-256 `2856a352...0f01bfec`. Supplied by the creator in the project folder.
  Its origin and rights are the creator's to confirm before any public release.

## Rights summary

Every shipped third-party input permits commercial use, modification and distribution of the cooked game. No paid,
login-gated, non-commercial or unclear-licence asset is used. Only the OFL font files are redistributed as raw files.
The other inputs are fetched from their original sources by the build and appear in the package only in cooked form.

## Required notices

The packaged game includes `THIRD_PARTY_NOTICES.txt` (this table in plain text, plus both OFL licence texts) and the
in-game credits. The credits carry the Unreal Engine notice:
"Unreal® Engine, Copyright 1998-2026, Epic Games, Inc. All rights reserved."
