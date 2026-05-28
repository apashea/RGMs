"""Pass 1 transliteration of ``spm_imshow.m`` (DEM toolbox)."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np


def spm_imshow(I: Any) -> None:
    """Display RGB image or sequence — mirror ``spm_imshow.m``."""
    arr = np.asarray(I, dtype=np.uint8)
    if arr.ndim < 3:
        raise ValueError("spm_imshow expects HxWxC or HxWxCxT uint8 array")
    n_frames = int(arr.shape[3]) if arr.ndim == 4 else 1
    for t in range(n_frames):
        frame = arr[:, :, :, t] if arr.ndim == 4 else arr
        plt.imshow(frame)
        plt.draw()
