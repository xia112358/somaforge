from __future__ import annotations

from pathlib import Path


FORBIDDEN = (
    "import isaaclab",
    "from isaaclab",
    "import isaacsim",
    "from isaacsim",
    "import omni",
    "from omni",
    "AppLauncher",
    "SimulationContext",
    "build_simulation_context",
)


def test_contact_aware_generation_and_direct_newton_do_not_start_isaac() -> None:
    package_root = Path(__file__).resolve().parents[1]
    repo_root = package_root.parents[1]
    paths = (
        package_root / "motion_edit" / "generation" / "contact_aware_preview.py",
        package_root / "motion_edit" / "generation" / "newton_direct_fk.py",
        package_root / "motion_edit" / "generation" / "pyroki_fullbody_ik.py",
        repo_root / "scripts" / "generate_contact_aware_edited_motion.py",
        repo_root / "scripts" / "canonicalize_motion_newton_direct.py",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        violations = [token for token in FORBIDDEN if token in source]
        assert not violations, f"{path} starts or imports Isaac through {violations}"
