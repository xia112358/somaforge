from pathlib import Path

import pytest
from somaforge_core.motion_contracts import BODY_NAMES, CONTACT_PARTS
from generator.teacher_data import TeacherDataset


def test_generated_teacher_contract() -> None:
    root = Path(__file__).resolve().parents[3]
    directory = root / "tmp/climb00_privileged_heading_continuous_teacher_1024_v10"
    if not directory.is_dir():
        return
    dataset = TeacherDataset(directory)
    assert dataset.trajectory_count == 1024
    assert len(dataset) == 31312
    segment = dataset.segment(0, 0)
    assert segment.position.shape[1:] == (len(BODY_NAMES), 3)
    assert segment.contact.shape[1] == len(CONTACT_PARTS)
    assert segment.position.shape[0] >= 2
    assert segment.start.rotation6d.shape == (len(BODY_NAMES), 6)
    assert segment.start.vector63.shape == (63,)
    with pytest.raises(ValueError, match="sparse-only teacher"):
        dataset.full_body_segment(0, 0)
