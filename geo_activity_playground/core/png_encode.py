import io

import numpy as np
from PIL import Image


def rgba_float_to_png(rgba: np.ndarray) -> bytes:
    if rgba.dtype != np.uint8:
        arr = np.clip(rgba * 255.0, 0, 255).astype(np.uint8)
    else:
        arr = rgba
    if arr.ndim != 3 or arr.shape[2] != 4:
        raise ValueError(f"expected HxWx4 RGBA, got shape {arr.shape}")
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGBA").save(buf, format="PNG", compress_level=1)
    return buf.getvalue()
