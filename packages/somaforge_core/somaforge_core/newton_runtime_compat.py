"""API-only bridge for local Isaac Lab 3 and the sole supported Newton build.

No collision algorithm, asset, margin or contact activation is changed here.
"""
from __future__ import annotations

from pathlib import Path
import os

from .newton_collision_compat import SCHEMA, NATIVE_SCHEMA


NEWTON_VERSION = "1.7.0.dev0"
NEWTON_SOURCE_COMMIT = "01381081fa0de0bac8f85f2669777782504787d0"
NEWTON_RUNTIME_ID = f"newton-{NEWTON_VERSION}+{NEWTON_SOURCE_COMMIT}"


def runtime_provenance() -> dict[str, str]:
    """Validate and describe the only Newton runtime accepted by SomaForge."""

    import newton

    module = Path(newton.__file__).resolve()
    expected_text = os.environ.get("SOMAFORGE_NEWTON_ENV")
    if newton.__version__ != NEWTON_VERSION:
        raise RuntimeError(
            f"Unsupported Newton {newton.__version__} at {module}; "
            f"expected {NEWTON_RUNTIME_ID}"
        )
    if expected_text is not None:
        expected = Path(expected_text).resolve()
        if not module.is_relative_to(expected):
            raise RuntimeError(
                f"Newton module {module} is outside required runtime {expected}"
            )
    return {
        "runtime_id": NEWTON_RUNTIME_ID,
        "version": NEWTON_VERSION,
        "source_commit": NEWTON_SOURCE_COMMIT,
        "module": str(module),
    }


def install():
    runtime_provenance()
    if SCHEMA != NATIVE_SCHEMA:
        return
    import newton
    import newton.solvers
    # Upstream's supported compatibility flag keeps the existing actuator
    # coordinate layout; do not silently reinterpret trained policy targets.
    newton.use_coord_layout_targets = False
    # Renamed upstream enum, same bits and semantics for the local Lab API.
    if not hasattr(newton.solvers, 'SolverNotifyFlags'):
        newton.solvers.SolverNotifyFlags = newton.ModelFlags
    from newton.selection import ArticulationView
    if not getattr(ArticulationView, '_somaforge_target_names', False):
        original = ArticulationView.get_attribute
        def get_attribute(self, name, source):
            name = {'joint_target_pos': 'joint_target_q',
                    'joint_target_vel': 'joint_target_qd'}.get(name, name)
            return original(self, name, source)
        ArticulationView.get_attribute = get_attribute
        ArticulationView._somaforge_target_names = True
