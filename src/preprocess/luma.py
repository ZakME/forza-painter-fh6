import os
import cv2
import numpy as np
from pathlib import Path


def luma_band(image_path):
    image_path = Path(image_path)
    bgra = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if bgra is None:
        raise ValueError(f"failed to read image: {image_path}")

    result = _apply_preprocess(bgra)
    output_path = image_path.with_name(f"{image_path.stem}.luma_band{image_path.suffix}")

    # Atomic write: write to a temp file first, then rename.
    # This avoids leaving a partially-written file if the process crashes mid-write.
    tmp_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
    ok = cv2.imwrite(str(tmp_path), result)
    if not ok:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError(f"failed to write preprocessed image: {output_path}")

    try:
        os.replace(str(tmp_path), str(output_path))
    except OSError as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError(f"failed to finalize preprocessed image: {output_path}") from exc

    return output_path


def _apply_preprocess(bgra: np.ndarray) -> np.ndarray:
    if bgra.ndim != 3:
        raise ValueError(f"expected 3D image array, got shape {bgra.shape}")

    channels = bgra.shape[2]
    if channels not in (3, 4):
        raise ValueError(f"expected 3 or 4 channels, got {channels}")

    bgr = np.clip(bgra[..., :3], 0, 255).astype(np.uint8)
    has_alpha = channels == 4
    if has_alpha:
        alpha = np.clip(bgra[..., 3], 0, 255).astype(np.uint8)

    # cv2.imread returns BGR, so we convert BGR->LAB, not RGB->LAB.
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
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
    bgr_out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    if has_alpha:
        out = np.dstack([bgr_out, alpha]).astype(np.uint8)
    else:
        out = bgr_out.astype(np.uint8)
    return out
