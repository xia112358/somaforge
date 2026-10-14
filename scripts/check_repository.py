"""Read-only repository audit; optionally write a JSON report under project tmp/."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RETIRED_SUPPORT_PATHS = (
    'scripts/aggregate_force_support.py',
    'scripts/audit_edited_support.py',
    'packages/somaforge_core/somaforge_core/support_aggregation.py',
    'packages/somaforge_core/tests/test_support_aggregation.py',
)
RETIRED_ENTRYPOINT_PATHS = (
    'scripts/train_climb00_direct_baseline.py',
    'packages/motion_edit/motion_edit/workbench/stable_transition_rebuild.py',
    'packages/motion_edit/motion_edit/generation/newton_collision.py',
    'packages/motion_edit/motion_edit/generation/newton_collision_filter.py',
)
CANONICAL_ENVIRONMENT_PATHS = (
    'scripts/source_somaforge.sh',
    'scripts/setup_isaaclab3_newton.sh',
    'scripts/extract_all_rollout_ref_contact_force_demos.py',
    'packages/motion_edit/motion_edit/physics_retarget/newton_runner.py',
)


def temporary_input_errors(name: str, tree: ast.AST) -> list[str]:
    """Reject temporary code imports and file reads; diagnostic writes are allowed."""
    errors = []
    def temporary_path(node):
        return any(isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and (n.value == 'tmp' or n.value.startswith('tmp/')
                        or '/holosoma/tmp/' in n.value)
                   for n in ast.walk(node))
    def call_name(node):
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute): return call_name(node.value) + '.' + node.attr
        return ''
    temporary_names = set()
    for _ in range(4):
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)): continue
            value = node.value
            if value is None: continue
            if temporary_path(value) or any(isinstance(n, ast.Name) and n.id in temporary_names for n in ast.walk(value)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                temporary_names.update(n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name))
    def temporary_input(node):
        return temporary_path(node) or any(isinstance(n, ast.Name) and n.id in temporary_names for n in ast.walk(node))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None and temporary_input(node.value):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)]
            if any(n.lower().endswith(('manifest', 'corpus', 'checkpoint', 'cache')) for n in names):
                errors.append(f'{name}:{node.lineno}: persistent input/cache assigned a temporary path')
        if not isinstance(node, ast.Call): continue
        function = call_name(node.func)
        if function in ('sys.path.insert', 'sys.path.append') and temporary_path(node):
            errors.append(f'{name}:{node.lineno}: temporary directory on import path')
        if function.endswith('spec_from_file_location') and temporary_path(node):
            errors.append(f'{name}:{node.lineno}: import of temporary source file')
        if isinstance(node.func, ast.Attribute) and node.func.attr in ('read_text', 'read_bytes'):
            if temporary_input(node.func.value):
                errors.append(f'{name}:{node.lineno}: temporary file used as required input')
        if function in ('torch.load', 'np.load', 'numpy.load') and node.args and temporary_input(node.args[0]):
            errors.append(f'{name}:{node.lineno}: temporary data/model used as required input')
    return errors


def audit(root: Path = ROOT) -> dict:
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).splitlines()

    tracked = git('ls-files')
    paths = sorted(set(tracked + git('ls-files', '--others', '--exclude-standard')))
    errors, warnings = [], []
    for name in RETIRED_SUPPORT_PATHS:
        if (root / name).exists():
            errors.append(f'{name}: retired support judgment/aggregation path; use native support evidence')
    for name in RETIRED_ENTRYPOINT_PATHS:
        if (root / name).exists():
            errors.append(f'{name}: retired entrypoint; use the owning package or historical records')
    for name in CANONICAL_ENVIRONMENT_PATHS:
        path = root / name
        if path.is_file() and 'packages/climb00_pipeline' in path.read_text():
            errors.append(f'{name}: default environment must not add the historical compatibility package')
    binaries, temporary_references = [], []
    python_count = 0
    for name in paths:
        path = root / name
        if not path.is_file():
            continue  # staged/working-tree deletions are reported by git status
        if path.suffix in {'.npz', '.pt', '.pth', '.ckpt', '.pyc'}:
            binaries.append(dict(path=name, bytes=path.stat().st_size))
        if path.suffix == '.py' and name.startswith(('packages/', 'scripts/', 'src/', 'tests/')):
            python_count += 1
            try:
                tree = ast.parse(path.read_text(), filename=name)
            except (SyntaxError, UnicodeError) as exc:
                errors.append(f'{name}: {exc}')
                continue
            errors.extend(temporary_input_errors(name, tree))
            for node in ast.walk(tree):
                modules = ([node.module or ''] if isinstance(node, ast.ImportFrom) else
                           [a.name for a in node.names] if isinstance(node, ast.Import) else [])
                if any(m == 'somaforge_core.support_aggregation' for m in modules):
                    errors.append(f'{name}:{node.lineno}: retired support aggregation import')
                retired_newton_import = any(m in ('motion_edit.generation.newton_collision',
                                                  'motion_edit.generation.newton_collision_filter') for m in modules)
                if isinstance(node, ast.ImportFrom) and node.level and name.startswith('packages/motion_edit/motion_edit/generation/'):
                    retired_newton_import |= node.module in ('newton_collision', 'newton_collision_filter')
                if retired_newton_import:
                    errors.append(f'{name}:{node.lineno}: shared Newton geometry belongs to somaforge_core')
                if name.startswith('packages/contact_solver/contact_solver/'):
                    if any(m == 'motion_edit' or m.startswith('motion_edit.') for m in modules):
                        errors.append(f'{name}:{node.lineno}: solver must not import the editing application')
                if name.startswith(('packages/motion_edit/', 'packages/contact_solver/', 'src/holosoma_retargeting/')):
                    if any(m == 'viser' or m.startswith('viser.') or m == 'viser_utils' for m in modules):
                        errors.append(f'{name}:{node.lineno}: retired Viser UI; use motion-edit contact-editor')
            # Canonical implementations must not depend on their historical aliases.
            if name.startswith(('packages/generator/generator/', 'packages/contact_solver/contact_solver/',
                                'packages/somaforge_core/somaforge_core/')):
                for node in ast.walk(tree):
                    modules = ([node.module or ''] if isinstance(node, ast.ImportFrom) else
                               [a.name for a in node.names] if isinstance(node, ast.Import) else [])
                    if any(m == 'climb00_pipeline' or m.startswith('climb00_pipeline.') for m in modules):
                        errors.append(f'{name}:{node.lineno}: production import through historical alias')
        if path.suffix == '.json' and name.startswith('configs/'):
            try:
                json.loads(path.read_text())
            except (ValueError, UnicodeError) as exc:
                errors.append(f'{name}: {exc}')
                continue
            def config_inputs(value, key=''):
                if isinstance(value, dict):
                    for k, v in value.items(): yield from config_inputs(v, k)
                elif isinstance(value, list):
                    for v in value: yield from config_inputs(v, key)
                elif isinstance(value, str) and value.startswith('tmp/') and key not in ('output', 'log'):
                    yield value
            refs = sorted(set(config_inputs(json.loads(path.read_text()))))
            for p in refs:
                temporary_references.append(dict(config=name, path=p, exists=(root/p).exists()))
                errors.append(f'{name}: temporary path used as configuration input: {p}')
        if path.suffix in {'.yaml', '.yml'} and name.startswith('.github/workflows/'):
            for script in re.findall(r'\bpython(?:3)?\s+(scripts/[\w./-]+\.py)\b', path.read_text()):
                if not (root / script).is_file():
                    errors.append(f'{name}: workflow calls missing script {script}')
    for path in root.iterdir():
        if path.is_symlink() and not path.exists():
            errors.append(f'Broken root symlink: {path.name}')
    if binaries:
        warnings.append('Tracked data/examples require dependency review; never blanket-delete them.')
    status = git('status', '--porcelain', '--untracked-files=all')
    return dict(schema='somaforge_repository_audit_v1', root=str(root),
                tracked_files=len(tracked), python_files_parsed=python_count,
                changes=dict(Counter(line[:2] for line in status)),
                tracked_data=binaries, temporary_config_references=temporary_references,
                errors=errors, warnings=warnings,
                scope='Static source/config/import audit; not physics, training or data acceptance')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = audit()
    if args.output:
        output = args.output.resolve()
        if not output.is_relative_to((ROOT/'tmp').resolve()):
            raise ValueError('Diagnostic reports must be stored under project tmp/')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return bool(report['errors'])


if __name__ == '__main__':
    raise SystemExit(main())
