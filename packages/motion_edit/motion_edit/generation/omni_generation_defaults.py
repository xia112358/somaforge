from __future__ import annotations

from typing import Any, Callable


OMNI_GENERATION_DEFAULTS: dict[str, float | int] = {
    "contact_laplacian_iters": 3,
    "contact_laplacian_trust": 0.0,
    "temporal_laplacian_weight": 40.0,
    "body_relative_weight": 10.0,
    "q_prior_weight": 0.02,
    "q_smooth_weight": 0.0,
    "mesh_laplacian_weight": 1.0,
}


def install_generation_defaults(function: Callable[..., Any]) -> None:
    """Enable the dual-Laplacian/Omni graph unless callers explicitly override it."""

    defaults = dict(function.__kwdefaults__ or {})
    defaults.update(OMNI_GENERATION_DEFAULTS)
    function.__kwdefaults__ = defaults
