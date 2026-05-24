import cv2
import numpy as np
from pathlib import Path

def luma_band(image_path):
    image_path = Path(image_path)
    rgba = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if rgba is None:
        raise ValueError(f"failed to read image: {image_path}")
    result = _apply_preprocess(rgba)
    output_path = image_path.with_name(f"{image_path.stem}.luma_band{image_path.suffix}")
    cv2.imwrite(str(output_path), result)
    return output_path

def _apply_preprocess(rgba: np.ndarray) -> np.ndarray:
    rgb = np.clip(rgba[..., :3], 0, 255).astype(np.uint8)
    alpha = np.clip(rgba[..., 3], 0, 255).astype(np.uint8)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l = lab[..., 0].astype(np.float32)
    levels = 24.0  # TODO make this a setting
    step = 256.0 / levels
    lq = np.floor(l / step) * step + step * 0.5
    # Keep the band separation, but blend some original luminance back in
    # so the result stays closer to the source and avoids overly harsh steps.
    l_out = lq * 0.82 + l * 0.18
    # Restore a touch of local contrast so the pass doesn't feel slightly washed.
    l_mid = 128.0
    l_out = (l_out - l_mid) * 1.06 + l_mid
    lab[..., 0] = np.clip(l_out, 0, 255).astype(np.uint8)
    rgb_out = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    out = np.dstack([rgb_out, alpha]).astype(np.float32)
    return out