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


class BodyPositionTrajectoryKinematicsProvider:
    """Proxy provider whose variables are semantic point world positions.

    This is an experimental bridge for real rollout diagnostics. It optimizes a
    task-space trajectory over selected semantic points; it is not a robot
    joint-space FK/Jacobian provider.
    """

    def __init__(self, point_names: Sequence[str]):
        if not point_names:
            raise ValueError("point_names must not be empty")
        self._point_names = tuple(str(name) for name in point_names)
        self._index = {name: index for index, name in enumerate(self._point_names)}
        self._nq = 3 * len(self._point_names)

    @property
    def nq(self) -> int:
        return self._nq

    @property
    def point_names(self) -> tuple[str, ...]:
        return self._point_names

    def fk_points(self, q: np.ndarray, point_names: Sequence[str]) -> np.ndarray:
        q_arr = np.asarray(q, dtype=np.float64).reshape(len(self._point_names), 3)
        return np.asarray([q_arr[self._index[str(name)]] for name in point_names], dtype=np.float64)

    def jacobian_points(self, q: np.ndarray, point_names: Sequence[str]) -> np.ndarray:
        np.asarray(q, dtype=np.float64).reshape(self._nq)
        jacobians = []
        for name in point_names:
            key = str(name)
            if key not in self._index:
                raise KeyError(f"unknown point {key!r}")
            jac = np.zeros((3, self._nq), dtype=np.float64)
            base = 3 * self._index[key]
            jac[0, base] = 1.0
            jac[1, base + 1] = 1.0
            jac[2, base + 2] = 1.0
            jacobians.append(jac)
        return np.asarray(jacobians, dtype=np.float64)
