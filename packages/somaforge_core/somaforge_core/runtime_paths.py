"""Locations shared by Lab launchers, native Newton workers, and installers."""
from __future__ import annotations

import os
from pathlib import Path

ISAACLAB_COMMIT = "e3f7d9ff1f5d7f8280de3ece9000b7117f66bcf4"
BASE_ENV_NAME = "isaaclab-ga-3.0.0-base"
NEWTON_ENV_NAME = "isaaclab-ga-3.0.0-newton-1.7.0"


def project_root() -> Path:
    return Path(os.environ.get("SOMAFORGE_ROOT", Path(__file__).resolve().parents[3])).resolve()


def isaaclab_path() -> Path:
    return Path(os.environ.get("SOMAFORGE_ISAACLAB_PATH", Path.home() / "isaaclab_3.0_ga")).expanduser().resolve()


def newton_environment() -> Path:
    return project_root() / "runtime/environments" / NEWTON_ENV_NAME


def newton_python() -> Path:
    executable = newton_environment() / "bin/python"
    if not executable.is_file():
        raise RuntimeError(f"Missing SomaForge GA runtime: {executable}. Run scripts/setup_isaaclab3_newton.sh.")
    return executable


def newton_subprocess_environment() -> dict[str, str]:
    """Select the same release for native workers and Kit subprocesses."""
    root, lab = project_root(), isaaclab_path()
    env = dict(os.environ)
    paths = [root, root / "src/holosoma", root / "src/holosoma_retargeting"]
    paths.extend(root / "packages" / package for package in (
        "somaforge_core", "contact_solver", "generator", "motion_edit",
    ))
    paths.extend(sorted(path for path in (lab / "source").iterdir() if path.is_dir()))
    env.update(
        SOMAFORGE_ROOT=str(root), ISAACLAB_PATH=str(lab),
        SOMAFORGE_NEWTON_ENV=str(newton_environment()),
        SOMAFORGE_NEWTON_PROFILE="main", PYTHONNOUSERSITE="1",
        PYTHONPATH=os.pathsep.join(map(str, paths)),
    )
    for name in ("PYTHONHOME", "HOLOSOMA_ISAACLAB3_NEWTON_HEADLESS_EXPERIENCE",
                 "HOLOSOMA_ISAACLAB3_NEWTON_KIT_EXPERIENCE"):
        env.pop(name, None)
    return env
