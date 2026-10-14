"""Do not turn broken augmentation source events into accepted training labels."""
import importlib.util
from pathlib import Path
import pytest


def test_production_event_failure_blocks_the_stage_without_filtering():
    path = Path(__file__).resolve().parents[3] / 'scripts/soften_edit_collection.py'
    spec = importlib.util.spec_from_file_location('soft_collection', path)
    module = importlib.util.module_from_spec(spec)
    # The script also imports the neighbouring CLI helper.
    import sys
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    rows = [dict(motion_id='valid', event_acceptance=dict(passed=True)),
            dict(motion_id='broken_keep', event_acceptance=dict(passed=False)),
            dict(motion_id='unknown')]
    index = dict(schema='native_execution_edit_collection_v1', motion_files=rows)
    with pytest.raises(ValueError, match='broken_keep, unknown'):
        module.require_source_event_preservation(index)
    assert index['motion_files'] == rows and len(rows) == 3
    rows[1]['event_acceptance']['passed'] = True
    rows[2]['event_acceptance'] = dict(passed=True)
    module.require_source_event_preservation(index)
