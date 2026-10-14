"""Install shared numeric collision repair before any Newton pipeline is built.

No package files, geometry, margin, gap, sorting, or contact activation changes.
The hash guard intentionally rejects unreviewed upstream collision code changes.
"""
import hashlib
from importlib.metadata import version
from pathlib import Path

LEGACY_SCHEMA='newton_convex_conditional_retry_sat_v2'
NATIVE_SCHEMA='newton_native_main_01381081_v1'
NATIVE_VERSION='1.7.0.dev0'
SCHEMA=NATIVE_SCHEMA if version('newton') == NATIVE_VERSION else LEGACY_SCHEMA
UPSTREAM_SHA256='d9b836df5759caff9e92107c429a41d34367d22b7fc00590b8e94b4d28b38b41'
NATIVE_HASHES={
    'contact_reduction_global': '47aacdf4b087fc7dc604a6145bdd684b34776a1910a8958b7626a453ef54d009',
    'collision_convex': '6c60bfea8a3004eeb495c9e95948d1e497623a56ec65edfc78bebf3e82137fac',
    'collision_core': 'daccb7ad4fe6a2acd0ef5fae83bbd6ba3e655d9e16226677b003e7fc1870de1a',
    'mpr': '92dc1a988df254855593f2f171a83823f44bc4b167e6d105aeeab26f10c16b0e',
    'support_function': '2d2931860de1a47a7b8905e4de66dc09b5a3126e596be6172398cfa716890f6f',
}


def install():
    from newton._src.geometry import collision_convex,collision_core
    if SCHEMA == NATIVE_SCHEMA:
        from importlib import import_module
        for name, expected in NATIVE_HASHES.items():
            module=import_module(f'newton._src.geometry.{name}')
            if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()!=expected:
                raise RuntimeError(f'Newton main {name} changed; review pinned native collision compatibility')
        # Do not replace upstream factories with the legacy retry/SAT copies.
        for name in ('create_solve_convex_multi_contact','create_solve_convex_single_contact'):
            if not getattr(collision_convex,name).__module__.startswith('newton.'):
                raise RuntimeError('Newton main collision factory was replaced; review external patches')
        return SCHEMA
    from . import newton_convex_retry as repaired
    if hashlib.sha256(Path(collision_convex.__file__).read_bytes()).hexdigest()!=UPSTREAM_SHA256:
        raise RuntimeError('Newton convex implementation changed; review conditional retry compatibility')
    for name in ('create_solve_convex_multi_contact','create_solve_convex_single_contact'):
        function=getattr(repaired,name)
        setattr(collision_convex,name,function)
        setattr(collision_core,name,function)
    return SCHEMA


def check_device(device):
    """Warp may only log a device trap; explicitly propagate it to Python."""
    import warp as wp
    from warp._src import context
    device=wp.get_device(device)
    if device.is_cuda:
        error=context.runtime.core.wp_cuda_context_check(device.context)
        if error:
            raise RuntimeError(f'Newton collision/device failure ({error}); check SOMAFORGE_UNRESOLVED_CONVEX_CONTACT diagnostics')


def install_simulation_guard():
    from isaaclab_newton.physics.newton_manager import NewtonManager
    from isaaclab.physics import PhysicsManager
    if getattr(NewtonManager,'_somaforge_collision_guard',False):return
    original=NewtonManager.step.__func__
    def step(cls):
        result=original(cls)
        check_device(PhysicsManager._device)
        return result
    NewtonManager.step=classmethod(step)
    NewtonManager._somaforge_collision_guard=True
