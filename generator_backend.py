from pathlib import Path
import re

from geometry_json import drawable_shape_count


ROOT = Path(__file__).resolve().parent
SETTINGS_DIR = ROOT / "settings"
GENERATOR_EXE = ROOT / "forza-painter-geometrize-go.exe"
PREVIEW_DIR = ROOT / "runtime" / "previews"
CUSTOM_SETTINGS_DIR = ROOT / "runtime" / "custom-settings"


SETTING_KEYS = (
    "maxPreviewSize",
    "maxResolution",
    "maxThreads",
    "mutatedSamples",
    "posterizeLevels",
    "previewEvery",
    "randomSamples",
    "saveAt",
    "saveEvery",
    "stopAt",
)


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


def load_settings():
    profiles = []
    paths = [path for path in sorted(SETTINGS_DIR.glob("*.ini")) if not path.name.startswith("_")]
    for index, path in enumerate(paths, start=1):
        name = re.sub(r"^[a-z0-9]+[.)]\s*", "", path.stem, flags=re.IGNORECASE)
        name = name.replace(" - ", " / ")
        profiles.append({
            "index": index,
            "path": path,
            "label": f"{index}. {name}",
            "description": setting_description(path),
            "values": parse_settings(path),
        })
    return profiles


def write_custom_settings(base_setting, custom_values):
    values = dict(parse_settings(base_setting["path"]))
    for key, value in custom_values.items():
        value = str(value).strip()
        if value:
            values[key] = value
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


def generated_jsons(image_path):
    image_path = Path(image_path)
    candidates = []
    folder = image_path.parent / image_path.stem
    if folder.exists():
        candidates.extend(folder.rglob("*.json"))
    candidates.extend(image_path.parent.glob(f"{image_path.stem}*.json"))
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
    return PREVIEW_DIR / f"{image_path.stem}.preview.png"


def generated_preview_files(image_path):
    image_path = Path(image_path)
    if not PREVIEW_DIR.exists():
        return []
    return sorted(
        PREVIEW_DIR.glob(f"{image_path.stem}.preview*.png"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def generator_output_base(image_path):
    image_path = Path(image_path)
    return image_path.with_suffix("")


def build_generator_command(image_path, setting):
    image_path = Path(image_path)
    return [
        str(GENERATOR_EXE),
        str(image_path),
        "-settings",
        str(setting["path"]),
        "-output",
        str(generator_output_base(image_path)),
        "-preview",
        str(generator_preview_path(image_path)),
    ]
