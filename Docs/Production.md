# Production and rebuild guide

Everything in the slice is rebuilt from scripts and plain data in this repository. The editable art sources
(`.blend`, generated textures and WAVs) are produced by the same scripts. This guide lists the order and the tools.

## Requirements

- Linux x86-64 with an X11 display, Vulkan SM6 GPU drivers and PipeWire/PulseAudio.
- Unreal Engine **5.8.4** (installed build, changelist 58902052), with its bundled clang toolchain.
- Blender **5.2.2 LTS**. MPFB 2.0.18 is used only as a build tool; it is never shipped.
- Python 3 with Pillow (texture and sheet tools). The audio generator runs on Blender's bundled Python, which
  includes numpy.
- Third-party inputs, used byte-identical to their original downloads (see `Docs/AssetLedger.md`):
  - MakeHuman system assets
  - Poly Haven and ambientCG surfaces
  - Kenney audio packs
  - Google Fonts / NDISCOVER font files (already in `Content/UI/Fonts`)

The working layout used to build this slice keeps the engine, caches, downloads, generated art and packages on a
dedicated drive outside the repository. Paths in the scripts follow that layout. Adjust the root constants at the top
of each script for another machine.

## Order

| Step | Command (from the repository root unless stated) | Output |
|---|---|---|
| 1. Combat core tests | `Tests/Core/run_core_tests.sh` | must report `0 failures` |
| 2. Chapel source art | `Tools/Blender/chapel/run_build.sh` | `sourceart/chapel/` FBX, textures, `layout.json`, review renders |
| 3. Characters | Blender: `Tools/Blender/characters/build_characters.py` (see its header for the exact command) | `sourceart/characters/<char>/` mesh FBX, `.blend`, textures, `bones.json` |
| 4. Animations | `Tools/Blender/anim/build_all.sh [--review]` | `sourceart/anims/<char>/A_*.fbx`, contact sheets |
| 5. Audio | `<blender>/5.2/python/bin/python3.13 -I Tools/Audio/build_audio.py` | `sourceart/audio/<category>/S_*.wav` |
| 6. Effect textures | `python3 Tools/Assets/make_vfx_textures.py <sourceart>/vfx` | `T_FX_*.png` |
| 7. Unreal content | editor Python, in order: `Tools/Unreal/build_content.py`, `build_audio.py`, `build_characters.py` (headless commandlet); `build_level.py` (needs the full editor) | `/Game/...` assets and `/Game/Maps/DrownedChapel` |
| 8. Game code | `Build.sh EbonyHeartsEditor Linux Development -Project=...` | editor module |
| 9. Package | `RunUAT.sh BuildCookRun -project=... -platform=Linux -clientconfig=Shipping -build -cook -stage -package -pak -archive -archivedirectory=<dir> -installed -nocompileeditor -skipbuildeditor -unrealexe=UnrealEditor-Cmd` | standalone package |
| 10. Release | `python3 -I Tools/Package/stage_release.py <archive>/Linux <out> <name> <commit>` | release folder without debug symbols, plus `THIRD_PARTY_NOTICES.txt`, `VERSION.txt`, `<name>.tar.gz`, `SHA256SUMS` and a per-file checksum list |
| 11. Evaluation | launch the packaged game with `-EHAuto=Tests/Auto/<script>.txt -EHEvidence=<dir>` (see below) | logs, perf JSON/CSV and screenshots |
| 12. Move tables | `python3 Tools/Docs/move_tables.py` | regenerates the tables in `Docs/CombatContract.md` |

### Evaluation scripts (`Tests/Auto`)

| Script | Purpose |
|---|---|
| `smoke.txt` | Title, menu, a CPU match segment, frame-time sample, asset report |
| `journey.txt` | Every menu and mode through device presses, with screen checks and a settings save/reload |
| `matrix.txt` | 12 complete matches: both fighters, both sides, mirrors, all CPU levels, local versus |
| `perf.txt`, `perf_cold.txt`, `perf_aura.txt` | 60 s fight and 20 s menu frame-time captures after warm-up; the first match from its start; Training with and without Spirit Enhanced Strikes |
| `soak.txt` | Repeated matches, rematches, pauses, settings round trips and menu transitions (30+ minutes) |
| `signature.txt`, `review.txt` | Training signature moves and a full match, for stills and footage |
| `review_match.txt` | A full bot-versus-CPU match (both Hard) for footage of normal play |
| `review_reactions.txt`, `review_flow.txt`, `review_jump.txt` | Training reviews of the playtest work: light strings from near full reach, Heavy and toward + Heavy (hit reactions); jabs from walking, taps, walk into strikes (movement into strikes); jumps in all directions and jump-ins. Record with `capture.py ... --start-on <evidence>/auto_log.txt:match_start` so two builds' recordings line up |
| `xinput_drive.py` | Drives a running game with real X11 key events (XTest) |
| `virtual_pad.py` | A virtual Xbox 360 pad (uinput): menus and fight, and disconnect/reconnect |
| `capture.py` | Records footage of the game window with GStreamer and extracts frames |
| `sample_resources.py` | Samples VRAM, GPU load and the game's resident memory once a second |

Bot-driven players press keys through the same device router as a player. Footage capture costs CPU, so performance
captures run without it; the resource sampler (one `nvidia-smi` query a second) does run during them.

The task scripts used for this delivery wrap these commands. They run the engine in a write sandbox, check the target
drive before writing, and hold a task lock so only one heavy job runs at a time. They are part of the private
workspace, not this repository.

## Conventions

- **Combat data.** Tuning lives in `Content/Data/rules.json` and `Content/Data/Fighters/*.json`. Data is staged as
  plain files and validated at startup; a bad value stops the game with the file path and the problem rather than
  misbehaving.
- **Presentation data.** Display names, mesh/animation paths, effect bones and sounds per move live in
  `Content/Data/presentation.json`.
- **Animation timing.** Clips are authored at 60 fps, so animation frame N is combat frame N. A move's contact pose is
  keyed on its first active frame from the data, and feet that stay planted are compensated for the root travel the
  simulation applies. Change a move's timing in the data, then rerun step 4.
- **Character skeletons.** These use MPFB's game_engine skeleton (`root`, `pelvis`, `spine_01-03`, ... ) plus twist
  bones and secondary chains (braids, face strands, coat tails). The chains are spring-simulated and baked into every
  clip.
- **Naming.**
  - `SK_<Fighter>`, `A_<Fighter>_<Key>`, `MI_<Fighter>_<Material>`, `T_<Fighter>_<Material>_{D,N,ORM}`
  - Chapel: `SM_<Piece>`, `MI_<Material>`
  - Sounds: `S_<Name>`; variations end in `_01`-`_03`.
- **Textures.** Normal maps are authored in OpenGL convention and flipped to DirectX on import. ORM packs AO,
  roughness and metallic.
- **Axes.** Unreal X is the fighting axis, Z is up, and the camera sits on +Y looking -Y. Blender sources face -Y with
  the character's left on +X.
