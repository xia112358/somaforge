from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_MODULE_PREFIXES = ("isaaclab", "isaacsim", "omni")
FORBIDDEN_SYMBOLS = {"AppLauncher", "SimulationContext", "build_simulation_context"}


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
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported_modules: list[str] = []
        referenced_symbols: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.append(node.module or "")
                referenced_symbols.update(alias.name for alias in node.names)
            elif isinstance(node, ast.Name):
                referenced_symbols.add(node.id)
        forbidden_imports = [
            module
            for module in imported_modules
            if module.startswith(FORBIDDEN_MODULE_PREFIXES)
        ]
        forbidden_symbols = sorted(referenced_symbols & FORBIDDEN_SYMBOLS)
        assert not forbidden_imports, f"{path} imports Isaac modules: {forbidden_imports}"
        assert not forbidden_symbols, f"{path} uses Isaac startup symbols: {forbidden_symbols}"
