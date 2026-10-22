"""Native workers use maintained packages without inheriting legacy search paths."""
from pathlib import Path
import os

import pytest

from somaforge_core import runtime_paths


@pytest.fixture
def worker_environment(monkeypatch):
    root = Path('/workspace')
    lab = Path('/isaaclab')
    monkeypatch.setattr(runtime_paths, 'project_root', lambda: root)
    monkeypatch.setattr(runtime_paths, 'isaaclab_path', lambda: lab)

    def directories(path):
        # Enumerating workspace packages would reintroduce arbitrary local code.
        assert path == lab / 'source'
        return iter([path / 'isaaclab_tasks', path / 'README.md', path / 'isaaclab'])

    monkeypatch.setattr(Path, 'iterdir', directories)
    monkeypatch.setattr(Path, 'is_dir', lambda path: path.suffix != '.md')
    return root, lab


def test_worker_paths_include_only_maintained_packages_and_sorted_lab_modules(worker_environment):
    root, lab = worker_environment
    env = runtime_paths.newton_subprocess_environment()
    paths = env['PYTHONPATH'].split(os.pathsep)
    assert paths == list(map(str, [
        root, root / 'src/holosoma', root / 'src/holosoma_retargeting',
        root / 'packages/somaforge_core', root / 'packages/contact_solver',
        root / 'packages/generator', root / 'packages/motion_edit',
        lab / 'source/isaaclab', lab / 'source/isaaclab_tasks',
    ]))
    assert env['SOMAFORGE_NEWTON_ENV'] == str(root / 'runtime/environments' / runtime_paths.NEWTON_ENV_NAME)
    assert env['SOMAFORGE_ROOT'] == str(root)
    assert env['ISAACLAB_PATH'] == str(lab)


def test_worker_environment_drops_ambient_paths_without_mutating_parent(worker_environment, monkeypatch):
    inherited = {
        'PYTHONPATH': '/old/packages/climb00_pipeline:/unrelated',
        'PYTHONHOME': '/other/python',
        'HOLOSOMA_ISAACLAB3_NEWTON_HEADLESS_EXPERIENCE': '/old/headless.kit',
        'HOLOSOMA_ISAACLAB3_NEWTON_KIT_EXPERIENCE': '/old/window.kit',
        'CUDA_VISIBLE_DEVICES': '2',
    }
    for key, value in inherited.items():
        monkeypatch.setenv(key, value)
    before = dict(os.environ)
    env = runtime_paths.newton_subprocess_environment()
    assert 'climb00_pipeline' not in env['PYTHONPATH'] and '/unrelated' not in env['PYTHONPATH']
    for key in inherited.keys() - {'PYTHONPATH', 'CUDA_VISIBLE_DEVICES'}:
        assert key not in env
    assert env['CUDA_VISIBLE_DEVICES'] == '2' and env['PYTHONNOUSERSITE'] == '1'
    assert dict(os.environ) == before
