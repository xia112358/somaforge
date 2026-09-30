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


def audit(root: Path = ROOT) -> dict:
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).splitlines()

    tracked = git('ls-files')
    paths = sorted(set(tracked + git('ls-files', '--others', '--exclude-standard')))
    errors, warnings = [], []
    for name in RETIRED_SUPPORT_PATHS:
        if (root / name).exists():
            errors.append(f'{name}: retired support judgment/aggregation path; use native support evidence')
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
            for node in ast.walk(tree):
                modules = ([node.module or ''] if isinstance(node, ast.ImportFrom) else
                           [a.name for a in node.names] if isinstance(node, ast.Import) else [])
                if any(m == 'somaforge_core.support_aggregation' for m in modules):
                    errors.append(f'{name}:{node.lineno}: retired support aggregation import')
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
            refs = sorted(set(re.findall(r'"(tmp/[^"\n]+)"', path.read_text())))
            temporary_references.extend(dict(config=name, path=p, exists=(root/p).exists()) for p in refs)
    for path in root.iterdir():
        if path.is_symlink() and not path.exists():
            errors.append(f'Broken root symlink: {path.name}')
    if binaries:
        warnings.append('Tracked data/examples require dependency review; never blanket-delete them.')
    if temporary_references:
        warnings.append('Historical config paths still reference tmp; preserve until explicit validated migration.')
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
