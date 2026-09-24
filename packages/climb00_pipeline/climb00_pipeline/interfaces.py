"""Strict two-stage runtime interfaces."""

from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from .contracts import SparseKeyframe


class KeyframeSelector(Protocol):
    """Predict exactly one complete next keyframe from the realized boundary."""

    def predict(self, current: SparseKeyframe, terrain_scan: NDArray[np.float32]) -> SparseKeyframe: ...


class TrajectoryInfiller(Protocol):
    """Connect two fixed keyframes without selecting or altering either endpoint."""

    def connect(
        self,
        start: SparseKeyframe,
        end: SparseKeyframe,
        terrain_scan: NDArray[np.float32],
    ) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.bool_]]: ...
