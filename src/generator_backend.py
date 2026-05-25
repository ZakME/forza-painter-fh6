import os
import re
import subprocess
from pathlib import Path

from app_paths import RESOURCE_ROOT, ROOT
from geometry_json import drawable_shape_count


BUNDLED_SETTINGS_DIR = RESOURCE_ROOT / "config" / "settings"
USER_SETTINGS_DIR = ROOT / "config" / "settings"
SETTINGS_DIR = BUNDLED_SETTINGS_DIR
GENERATOR_EXE = RESOURCE_ROOT / "bin" / "forza-painter-geometrize-go.exe"
PREVIEW_DIR = ROOT / "runtime" / "previews"
CUSTOM_SETTINGS_DIR = ROOT / "runtime" / "custom-settings"


SETTING_KEYS = (
    "maxPreviewSize",
    "maxResolution",
    "maxThreads",
    "mutatedSamples",
    "enableProgressiveSampling",
    "progressiveSamplingStart",
    "progressiveSamplingEnd",
    "progressiveSamplingTransition",
    "progressiveSamplingCurve",
    "errorGridSize",
    "forceOpaqueShapes",
    "posterizeLevels",
    "previewEvery",
    "randomSamples",
    "preprocessMode",
    "saveAt",
    "saveEvery",
    "stopAt",
    "loadGeometry",
)

_RESUME_SUPPORT = None


def setting_description(path):
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("description"):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def parse_settings(path):
    values = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    except OSError:
        pass
    return values


def merged_settings_values(base_setting, custom_values):
    values = dict(parse_settings(base_setting["path"]))
    for key, value in custom_values.items():
        value = str(value).strip()
        if value:
            values[key] = value
    return values


def _settings_paths():
    seen = set()
    for source, folder in (("bundled", BUNDLED_SETTINGS_DIR), ("user", USER_SETTINGS_DIR)):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.ini")):
            if path.name.startswith("_"):
                continue
            try:
                key = str(path.resolve()).lower()
            except OSError:
                key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            yield source, path


def load_settings():
    profiles = []
    for index, (source, path) in enumerate(_settings_paths(), start=1):
        name = re.sub(r"^[a-z0-9]+[.)]\s*", "", path.stem, flags=re.IGNORECASE)
        name = name.replace(" - ", " / ")
        if source == "user":
            name = f"User / {name}"
        profiles.append({
            "index": index,
            "source": source,
            "path": path,
            "label": f"{index}. {name}",
            "description": setting_description(path),
            "values": parse_settings(path),
        })
    return profiles


def write_custom_settings(base_setting, custom_values):
    values = merged_settings_values(base_setting, custom_values)
    CUSTOM_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = CUSTOM_SETTINGS_DIR / "custom.ini"
    lines = ["description = Custom UI settings"]
    for key in SETTING_KEYS:
        if key in values:
            lines.append(f"{key} = {values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    setting = dict(base_setting)
    setting["path"] = path
    setting["label"] = "Custom"
    setting["description"] = "Custom UI settings"
    setting["values"] = values
    return setting


def write_user_settings_preset(base_setting, custom_values, output_path, description="User custom settings"):
    values = merged_settings_values(base_setting, custom_values)
    USER_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path)
    if path.suffix.lower() != ".ini":
        path = path.with_suffix(".ini")
    lines = [f"description = {description}"]
    for key in SETTING_KEYS:
        if key in values:
            lines.append(f"{key} = {values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _get_preprocess_mode(values):
    if not values:
        return None
    preprocess_mode = str(values.get("preprocessMode", "")).strip().lower()
    if preprocess_mode == "none" or not preprocess_mode:
        return None
    return preprocess_mode


def _preprocessed_image_path(image_path, mode):
    image_path = Path(image_path)
    return image_path.with_name(f"{image_path.stem}.{mode}{image_path.suffix}")


def preprocess_input_image(image_path, setting):
    image_path = Path(image_path)
    mode = _get_preprocess_mode(setting.get("values", {}))
    if mode is None:
        return image_path

    # Generate output path
    output_path = _preprocessed_image_path(image_path, mode)
    try:
        if output_path.exists() and output_path.stat().st_mtime >= image_path.stat().st_mtime:
            return output_path
    except OSError:
        pass
    
    # Generate preprocessed image
    if mode == "luma_band":
        luma_band = __import__("preprocess.luma", fromlist=["luma_band"]).luma_band
        return luma_band(image_path)
    else:
        raise ValueError(f"unsupported preprocess mode: {mode}")


def generator_supports_resume():
    global _RESUME_SUPPORT
    if _RESUME_SUPPORT is not None:
        return _RESUME_SUPPORT
    if not GENERATOR_EXE.exists():
        _RESUME_SUPPORT = False
        return _RESUME_SUPPORT
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        proc = subprocess.run(
            [str(GENERATOR_EXE), "-help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        _RESUME_SUPPORT = False
        return _RESUME_SUPPORT
    output = (proc.stdout or "") + (proc.stderr or "")
    _RESUME_SUPPORT = "-resume" in output
    return _RESUME_SUPPORT


def discover_geometry_jsons(image_path, input_image=None):
    image_path = Path(image_path)
    input_image = Path(input_image) if input_image is not None else image_path
    paths = []
    seen = set()
    for source in (image_path, input_image):
        for path in generated_jsons(source):
            key = str(path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
    paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return paths


def checkpoint_layer_count(path):
    path = Path(path)
    match = re.search(r"\.(\d+)$", path.stem)
    if match:
        return int(match.group(1))
    return geometry_shape_count(path)


def best_resume_checkpoint(image_path, input_image=None, stop_at=None):
    if not generator_supports_resume():
        return None, 0
    candidates = discover_geometry_jsons(image_path, input_image)
    if not candidates:
        return None, 0
    try:
        target_layers = int(stop_at) if stop_at is not None else 0
    except (TypeError, ValueError):
        target_layers = 0
    best_path = None
    best_layers = 0
    for path in best_geometry_jsons(candidates):
        layers = checkpoint_layer_count(path)
        if layers <= 0:
            continue
        if target_layers and layers >= target_layers:
            continue
        if layers > best_layers:
            best_layers = layers
            best_path = path
    return best_path, best_layers


def prepare_generation_setting(base_setting, custom_values=None, resume_path=None):
    overrides = {key: value for key, value in (custom_values or {}).items() if str(value).strip()}
    if resume_path:
        overrides["loadGeometry"] = str(Path(resume_path).resolve())
    if overrides:
        return write_custom_settings(base_setting, overrides)
    return base_setting


def generated_jsons(image_path):
    image_path = Path(image_path)
    candidates = []
    output_base = generator_output_base(image_path)
    folders = {
        image_path.parent / image_path.stem,
        output_base.parent / output_base.name,
    }
    for folder in folders:
        if folder.exists():
            candidates.extend(folder.rglob("*.json"))
    prefixes = {
        image_path.stem,
        image_path.name,
        output_base.name,
        image_path.stem.split(".", 1)[0],
        output_base.name.split(".", 1)[0],
    }
    patterns = {f"{prefix}*.json" for prefix in prefixes if prefix}
    for pattern in patterns:
        candidates.extend(image_path.parent.glob(pattern))
        if output_base.parent != image_path.parent:
            candidates.extend(output_base.parent.glob(pattern))
    return sorted(set(candidates), key=lambda path: path.stat().st_mtime, reverse=True)


def geometry_shape_count(path):
    return drawable_shape_count(path)


def best_geometry_jsons(paths):
    best_by_stem = {}
    for path in paths:
        path = Path(path)
        base_name = re.sub(r"\.\d+$", "", path.stem)
        key = str(path.with_name(base_name).resolve()).lower()
        score = (geometry_shape_count(path), path.stat().st_mtime)
        current = best_by_stem.get(key)
        if current is None or score > current[0]:
            best_by_stem[key] = (score, path)
    return [item[1] for item in sorted(best_by_stem.values(), key=lambda item: item[1].stat().st_mtime, reverse=True)]


def generator_preview_path(image_path):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    image_path = Path(image_path)
    name_without_suffix = _name_without_suffix(image_path)
    return PREVIEW_DIR / f"{name_without_suffix}.preview.png"


def generated_preview_files(image_path):
    image_path = Path(image_path)
    if not PREVIEW_DIR.exists():
        return []
    # Match previews using full filename
    name_without_suffix = _name_without_suffix(image_path)
    return sorted(
        PREVIEW_DIR.glob(f"{name_without_suffix}.preview*.png"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def generator_output_base(image_path):
    image_path = Path(image_path)
    name_without_suffix = _name_without_suffix(image_path)
    return image_path.with_name(name_without_suffix)


def _name_without_suffix(path):
    path = Path(path)
    return path.name[:-len(path.suffix)] if path.suffix else path.name


def build_generator_command(image_path, setting, resume_path=None):
    image_path = Path(image_path)
    cmd = [
        str(GENERATOR_EXE),
        str(image_path),
        "-settings",
        str(setting["path"]),
        "-output",
        str(generator_output_base(image_path)),
        "-preview",
        str(generator_preview_path(image_path)),
    ]
    if resume_path:
        cmd.extend(["-resume", str(Path(resume_path).resolve())])
    return cmd
