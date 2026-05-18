# forza-painter FH6

[English](README.md) | [中文](README.zh-CN.md)

Generate Forza Horizon 6 Vinyl Group layers from images.

This tool has two jobs:

- Generate geometry JSON with the bundled GPU/OpenCL generator.
- Import JSON into the currently open FH6 Vinyl Group Editor.

Normal use does not require manual memory addresses. For FH6 import, select the game process, enter the template layer count, then import.

## Setup

1. Download this repository as a ZIP and extract it.
2. Install 64-bit Python. Python 3.12 is recommended.
3. Open the extracted folder.
4. Double-click `install_dependencies.bat`.
5. Double-click `start_app.bat`.

If the app does not start, run `check_environment.bat`.

## Generate JSON

1. Open the `Generate JSON` page.
2. Click `Add images` and choose PNG/JPG/BMP images.
3. Select a quality preset.
4. Optional: enable `Use custom settings` to change output layers, resolution, random samples, and mutated samples in the app.
5. Click the fixed bottom `Start generating` button.
6. Wait for the preview and logs to update.

Generated files are saved beside the source image, for example:

```text
image.500.json
image.1000.json
image.3000.json
```

The left panel can scroll. In small windows, the generate button stays fixed at the bottom.

## Quality And Custom Settings

Later presets are usually slower and cleaner.

- `extremely fast`: quick composition tests.
- `fast`: quick usable output.
- `balanced`: recommended default.
- `slow`: higher quality.
- `super slow`: slowest bundled preset for final output.

Custom settings only affect the current run. Common fields:

- `Output layers`: maximum layer count.
- `Max resolution`: maximum processing resolution.
- `Random samples`: more candidates, slower generation.
- `Mutated samples`: more optimization, slower generation.
- `Save checkpoints`: JSON checkpoints to save, for example `500,1000,1500,3000`.

## Prepare FH6

1. Start Forza Horizon 6.
2. Open `Create Vinyl Group` / `Vinyl Group Editor`.
3. Load a template made from many simple sphere layers.
4. `Ungroup` the template.
5. Remember the exact layer count shown in game.
6. Keep this editor open while importing.

Recommended template size: 500 to 3000 layers.

## Import JSON

1. Open the `Import` page.
2. Click `Refresh` and select the running `forzahorizon6.exe`.
3. Enter the current in-game template layer count.
4. Add the generated `.json`, or click `Use generated JSON`.
5. Leave advanced address fields empty.
6. Click `Import JSON`.

The app locates and verifies the current FH6 layer table before writing. If the target cannot be verified safely, it stops before writing.

## Rules

- The template must be ungrouped.
- The layer count in the app must exactly match the game.
- Do not switch game menus while importing.
- After restarting the game, reloading the template, or changing layer count, import again with the new correct count.
- If JSON has fewer layers than the template, unused template layers are hidden.
- If JSON has more layers than the template, extra shapes are trimmed.
- Transparent PNG backgrounds are not imported as visible backgrounds.

## Troubleshooting

### GPU Generator Or OpenCL Error

Update the NVIDIA/AMD/Intel graphics driver. The bundled generator is `forza-painter-geometrize-go.exe` and uses OpenCL.

### Python Or Dependency Error

Run:

```powershell
install_dependencies.bat
```

Then run:

```powershell
check_environment.bat
```

`Core OK` means the Python dependencies are installed.

### `_ARRAY_API not found`, NumPy, Or OpenCV Error

This is an optional preview dependency issue. It does not block JSON generation or FH6 import. Reinstall core dependencies first:

```powershell
python -m pip install -r requirements.txt
```

### `OpenProcess` Or Permission Error

Close the app and run `start_app.bat` as administrator.

JSON generation does not need administrator permission. FH6 import usually does.

### Game Process Not Found

Start FH6 first, then click `Refresh`. If it still does not appear, restart the app.

### No Safe Template Found

Check:

- You are in Vinyl Group Editor.
- The template is ungrouped.
- The layer count is exact.
- You did not switch menus after entering the count.

### Import Looks Cut Off

The template has too few layers. Use a larger template or generate fewer JSON layers.

## Files

Most users only need:

- `install_dependencies.bat`: install Python dependencies.
- `start_app.bat`: start the app.
- `check_environment.bat`: check the environment.
- `clean_runtime_data.bat`: remove runtime caches before publishing or re-zipping.
- `1. drag_image_file_here.bat`: optional shortcut for dragging an image into the app.

Do not publish runtime cache folders such as `webui-data`, `runtime`, `__pycache__`, or `dist`.
