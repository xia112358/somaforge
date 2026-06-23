from __future__ import annotations

from typing import Protocol, Sequence

import numpy as np


class KinematicsProvider(Protocol):
    @property
    def nq(self) -> int:
        ...

    def fk_points(self, q: np.ndarray, point_names: Sequence[str]) -> np.ndarray:
        ...

    def jacobian_points(self, q: np.ndarray, point_names: Sequence[str]) -> np.ndarray:
        ...


class LinearPointKinematicsProvider:
    """Small deterministic provider for tests.

    FK is linear:

    ``point(name, q) = base_points[name] + weights[name] @ q``

    where ``weights[name]`` has shape ``[3, nq]``.
    """

    def __init__(self, *, base_points: dict[str, np.ndarray], weights: dict[str, np.ndarray]):
        if not weights:
            raise ValueError("weights must not be empty")
        first = np.asarray(next(iter(weights.values())), dtype=np.float64)
        if first.ndim != 2 or first.shape[0] != 3:
            raise ValueError("weights values must have shape [3, nq]")
        self._nq = int(first.shape[1])
        self._base_points = {name: np.asarray(value, dtype=np.float64).reshape(3) for name, value in base_points.items()}
        self._weights = {}
        for name, value in weights.items():
            arr = np.asarray(value, dtype=np.float64)
            if arr.shape != (3, self._nq):
                raise ValueError(f"weights[{name!r}] must have shape {(3, self._nq)}, got {arr.shape}")
            self._weights[str(name)] = arr
            self._base_points.setdefault(str(name), np.zeros(3, dtype=np.float64))

    @property
    def nq(self) -> int:
        return self._nq

    def fk_points(self, q: np.ndarray, point_names: Sequence[str]) -> np.ndarray:
        q_arr = np.asarray(q, dtype=np.float64).reshape(self._nq)
        points = []
        for name in point_names:
            key = str(name)
            if key not in self._weights:
                raise KeyError(f"unknown point {key!r}")
            points.append(self._base_points[key] + self._weights[key] @ q_arr)
        return np.asarray(points, dtype=np.float64)

    def jacobian_points(self, q: np.ndarray, point_names: Sequence[str]) -> np.ndarray:
        np.asarray(q, dtype=np.float64).reshape(self._nq)
        jacobians = []
        for name in point_names:
            key = str(name)
            if key not in self._weights:
                raise KeyError(f"unknown point {key!r}")
            jacobians.append(self._weights[key])
        return np.asarray(jacobians, dtype=np.float64)
