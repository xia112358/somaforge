import pytest


def test_shared_factories_and_idempotent_install():
    from somaforge_core import newton_collision_compat as compat
    from newton._src.geometry import collision_convex,collision_core
    if compat.SCHEMA == compat.NATIVE_SCHEMA:
        before=[getattr(module,name) for module in (collision_convex,collision_core)
                for name in ('create_solve_convex_multi_contact','create_solve_convex_single_contact')]
        assert compat.install()==compat.NATIVE_SCHEMA
        assert compat.install()==compat.NATIVE_SCHEMA
        after=[getattr(module,name) for module in (collision_convex,collision_core)
               for name in ('create_solve_convex_multi_contact','create_solve_convex_single_contact')]
        assert before == after
        return
    from somaforge_core import newton_convex_retry as repaired
    assert compat.install()==repaired.SCHEMA
    assert compat.install()==repaired.SCHEMA
    for name in ('create_solve_convex_multi_contact','create_solve_convex_single_contact'):
        assert getattr(collision_core,name) is getattr(repaired,name)
        assert getattr(collision_convex,name) is getattr(repaired,name)


def test_unreviewed_upstream_fails_closed(monkeypatch):
    from somaforge_core import newton_collision_compat as compat
    monkeypatch.setattr(compat,'UPSTREAM_SHA256','unreviewed')
    monkeypatch.setattr(compat,'NATIVE_HASHES',{'mpr':'unreviewed'})
    with pytest.raises(RuntimeError,match='review'):
        compat.install()


def test_runtime_bridge_native_target_names(monkeypatch):
    from somaforge_core import newton_runtime_compat as runtime
    from somaforge_core import newton_collision_compat as compat
    if compat.SCHEMA != compat.NATIVE_SCHEMA:
        pytest.skip('Native main bridge only')
    import newton
    from newton.selection import ArticulationView
    runtime.install()
    first = ArticulationView.get_attribute
    runtime.install()
    assert ArticulationView.get_attribute is first
    assert newton.solvers.SolverNotifyFlags is newton.ModelFlags
    assert newton.use_coord_layout_targets is False
    class FakeView:
        def _get_attribute_values(self, name, source):
            return name, source
    marker = object()
    assert first(FakeView(), 'joint_target_pos', marker) == ('joint_target_q', marker)
    assert first(FakeView(), 'joint_target_vel', marker) == ('joint_target_qd', marker)
    assert first(FakeView(), 'joint_f', marker) == ('joint_f', marker)
