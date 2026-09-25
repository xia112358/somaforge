"""Public compatibility and dependency-direction regression checks."""
import importlib
import subprocess
import sys


def test_legacy_module_identity_and_monkeypatch(monkeypatch):
    for legacy, canonical in (
        ('full1000_position_predictor', 'generator.full1000_position_predictor'),
        ('neural_infiller', 'generator.neural_infiller'),
        ('newton_witness_loss', 'contact_solver.newton_witness_loss'),
        ('contracts', 'somaforge_core.motion_contracts'),
    ):
        old = importlib.import_module('climb00_pipeline.' + legacy)
        new = importlib.import_module(canonical)
        assert old is new
        monkeypatch.setattr(old, '_compatibility_probe', object(), raising=False)
        assert new._compatibility_probe is old._compatibility_probe


def test_solver_imports_without_loading_generator():
    subprocess.run([sys.executable, '-c', '''
import importlib, pkgutil, sys
import contact_solver
for module in pkgutil.iter_modules(contact_solver.__path__):
    if module.name != 'research':
        importlib.import_module('contact_solver.' + module.name)
assert not any(n == 'generator' or n.startswith('generator.') for n in sys.modules)
assert not any(n == 'climb00_pipeline' or n.startswith('climb00_pipeline.') for n in sys.modules)
'''], check=True)


def test_shared_types_keep_identity():
    from climb00_pipeline.neural_infiller import InfillerOutput as old_output
    from generator.neural_infiller import InfillerOutput
    from somaforge_core.prediction_contracts import InfillerOutput as shared_output
    from climb00_pipeline.unified_interaction import project_interaction_q_trajectory as old_project
    from contact_solver.trajectory_projection import project_interaction_q_trajectory
    assert old_output is InfillerOutput is shared_output
    assert old_project is project_interaction_q_trajectory
