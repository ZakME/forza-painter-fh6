"""Script to rewrite workflow.py with setup-only functions."""
import sys
sys.path.insert(0, "src")

# New workflow.py content - setup-only, no subprocess
content = '''\
"""Core orchestration for region-focused iterative painting.

Setup-only functions that prepare files and return commands.
The actual subprocess management (Popen, stdout streaming, file polling)
happens in app.py worker threads.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image

from generator_backend import GENERATOR_EXE, parse_settings
from region_painter.ini_manager import modify_ini
from region_painter.image_processor import apply_selection_mask
from region_painter.preview_renderer import load_shapes_from_json, render_preview
from region_painter.state_manager import StateManager

ProgressCallback = Callable[[str], None]


def prepare_first_pass(
    image_path, settings_path, first_layers, output_dir,
    exe_path="", on_progress=None,
):
    """Prepare first pass. Returns dict with cmd, paths, state. Does NOT run exe."""
    image_path = Path(image_path).resolve()
    settings_path = Path(settings_path).resolve()
    output_dir = Path(output_dir)
    exe = Path(exe_path) if exe_path else Path(str(GENERATOR_EXE))
    if not exe.exists():
        return {"error": f"Generator exe not found: {exe}"}
    values = parse_settings(settings_path)
    total_budget = int(values.get("stopAt", 3000))
    max_resolution = int(values.get("maxResolution", 1200))
    max_preview_size = int(values.get("maxPreviewSize", 500))
    first_layers = min(first_layers, total_budget)
    _p(on_progress, f"Total budget: {total_budget}, first pass: {first_layers}")
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_ini = output_dir / "temp.ini"
    base_json = output_dir / "base.json"
    preview_png = output_dir / "preview.png"
    target_png = output_dir / "target.png"
    img = Image.open(image_path).convert("RGBA")
    orig_w, orig_h = img.size
    if max(orig_w, orig_h) > max_resolution:
        ratio = max_resolution / max(orig_w, orig_h)
        img = img.resize((max(1, int(orig_w * ratio)), max(1, int(orig_h * ratio))), Image.LANCZOS)
    working_w, working_h = img.size
    img.save(target_png, "PNG")
    modify_ini(settings_path, temp_ini, stop_at=first_layers)
    state = StateManager(output_dir)
    state.init_first_pass(
        original_image=str(image_path), original_ini=str(settings_path),
        total_budget=total_budget, working_width=working_w, working_height=working_h,
        max_resolution=max_resolution, max_preview_size=max_preview_size,
    )
    state.target_path = str(target_png)
    state.base_json = str(base_json)
    state.preview_path = str(preview_png)
    cmd = [str(exe), str(target_png), "-settings", str(temp_ini),
           "-output", str(base_json.with_suffix("")),
           "-preview", str(preview_png.with_suffix(""))]
    _p(on_progress, f"Command: {cmd[0]} ...")
    return {"cmd": cmd, "output_dir": str(output_dir), "target_png": str(target_png),
            "preview_png": str(preview_png), "base_json": str(base_json),
            "total_budget": total_budget, "max_preview_size": max_preview_size, "state": state}


def finalize_first_pass(prep):
    """Post-process after first-pass exe finishes."""
    output_dir = Path(prep["output_dir"])
    base_json = Path(prep["base_json"])
    target_png = Path(prep["target_png"])
    preview_png = Path(prep["preview_png"])
    max_preview_size = prep.get("max_preview_size", 500)
    state = prep["state"]
    json_files = sorted(output_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not json_files:
        return {"ok": False, "error": "No JSON output found after generation."}
    actual_json = json_files[0]
    if actual_json != base_json:
        import shutil
        shutil.copy2(actual_json, base_json)
    shapes = load_shapes_from_json(base_json)
    layers = max(0, len(shapes) - 1)
    try:
        render_preview(target_png, shapes, preview_png, max_preview_size)
    except Exception:
        pass
    state.base_json = str(base_json)
    state.add_pass(mask_path=None, layers=layers, json_path=str(base_json))
    return {"ok": True, "layers": layers, "preview_png": str(preview_png)}


def prepare_region_pass(
    output_dir, region_layers, selection_mask,
    exe_path="", on_progress=None,
):
    """Prepare region pass. Returns dict with cmd, paths, state. Does NOT run exe."""
    output_dir = Path(output_dir)
    exe = Path(exe_path) if exe_path else Path(str(GENERATOR_EXE))
    if not exe.exists():
        return {"error": f"Generator exe not found: {exe}"}
    state = StateManager(output_dir)
    if not state.is_first_pass_done:
        return {"error": "First pass has not been completed."}
    if region_layers > state.remaining_budget:
        region_layers = state.remaining_budget
    if region_layers <= 0:
        return {"error": "No remaining budget for region pass."}
    new_stop_at = state.used_layers + region_layers
    target_png = Path(state.target_path)
    pass_n = len(state.passes) + 1
    region_target = output_dir / f"region_target_pass{pass_n}.png"
    try:
        apply_selection_mask(target_png, selection_mask, region_target, feather_radius=0)
    except Exception as exc:
        return {"error": f"Failed to apply selection mask: {exc}"}
    mask_png = output_dir / f"pass_{pass_n}_mask.png"
    selection_mask.save(mask_png, "PNG")
    settings_path = Path(state._data.get("original_ini", ""))
    temp_ini = output_dir / "temp.ini"
    if not settings_path.exists():
        return {"error": f"Original settings INI not found: {settings_path}"}
    modify_ini(settings_path, temp_ini, stop_at=new_stop_at)
    base_json = Path(state.base_json)
    cmd = [str(exe), str(region_target), "-resume", str(base_json), "-settings", str(temp_ini)]
    _p(on_progress, f"Command: {cmd[0]} ...")
    return {"cmd": cmd, "output_dir": str(output_dir), "target_png": str(target_png),
            "preview_png": state.preview_path, "base_json": str(base_json),
            "mask_png": str(mask_png), "new_stop_at": new_stop_at,
            "region_layers": region_layers, "state": state,
            "max_preview_size": state.max_preview_size}


def finalize_region_pass(prep):
    """Post-process after region-pass exe finishes."""
    state = prep["state"]
    base_json = Path(prep["base_json"])
    target_png = Path(prep["target_png"])
    preview_png = Path(prep["preview_png"])
    mask_png = prep.get("mask_png", "")
    max_preview_size = prep.get("max_preview_size", 500)
    shapes = load_shapes_from_json(base_json)
    total_layers = max(0, len(shapes) - 1)
    new_layers = total_layers - state.used_layers
    try:
        render_preview(target_png, shapes, preview_png, max_preview_size)
    except Exception:
        pass
    state.add_pass(mask_path=str(mask_png), layers=new_layers, json_path=str(base_json))
    return {"ok": True, "new_total": total_layers, "preview_png": str(preview_png)}


def get_status(output_dir):
    """Return a summary of the current workflow state."""
    state = StateManager(output_dir)
    return {
        "total_budget": state.total_budget,
        "used_layers": state.used_layers,
        "remaining": state.remaining_budget,
        "passes": state.passes,
        "is_first_pass_done": state.is_first_pass_done,
    }


def finalize(output_dir, dest_path):
    """Copy the final JSON to dest_path."""
    import shutil
    output_dir = Path(output_dir)
    dest_path = Path(dest_path)
    state = StateManager(output_dir)
    base_json = Path(state.base_json)
    if not base_json.exists():
        return {"ok": False, "error": f"Base JSON not found: {base_json}"}
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base_json, dest_path)
    return {"ok": True, "output": str(dest_path)}


def _p(callback, msg):
    if callback:
        callback(msg)
'''

target = "src/region_painter/workflow.py"
with open(target, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Written {target} ({len(content)} bytes)")
