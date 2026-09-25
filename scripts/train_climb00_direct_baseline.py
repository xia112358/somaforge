"""Load the direct-infiller training recipe; delegate CLI to AppLauncher then tyro."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in ('tmp', 'packages/climb00_pipeline', 'packages/somaforge_core'):
    sys.path.insert(0, str(ROOT / relative))


def main():
    from train_full_shared_contact import Config, main as train

    path = ROOT / 'configs/climb00/direct_infiller_v1.json'
    settings = json.loads(path.read_text())['training']
    for key in ('corpus', 'output', 'smoothness_limits_file', 'resume'):
        if settings.get(key) is not None:
            settings[key] = ROOT / settings[key]
    # Official simulator/device flags are parsed inside train() before tyro.
    # Preserve relative paths in the existing cached corpus and evaluation data.
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError(f'Run this baseline from project root: {ROOT}')
    train(default_config=Config(**settings))


if __name__ == '__main__':
    main()
