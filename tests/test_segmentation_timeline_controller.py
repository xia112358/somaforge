from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from motion_edit.schema import SegmentRecord
from motion_edit.segmentation.session import create_segmentation_edit_session
from motion_edit.storage import io as storage_io
from motion_edit.storage.io import read_canonical_segments, read_draft_segments, write_canonical_segments, write_motion_version
from motion_edit.storage.schema import MotionVersionRecord
from motion_edit.viewer.segmentation_timeline import SegmentationTimelineController


class SegmentationTimelineControllerTests(unittest.TestCase):
    def _patch_storage(self, root: Path):
        return (
            mock.patch.object(storage_io, "SEGMENTS_ROOT", root / "segments"),
            mock.patch.object(storage_io, "MOTION_VERSIONS_ROOT", root / "motion_versions"),
            mock.patch.object(storage_io, "TOKENS_ROOT", root / "tokens"),
        )

    def _seed(self, root: Path) -> None:
        motion = root / "motion_a.npz"
        motion.write_bytes(b"placeholder")
        write_motion_version(MotionVersionRecord(motion_version_id="motion_a_raw", motion_path=str(motion)))
        write_canonical_segments(
            "motion_a_raw",
            [
                SegmentRecord(
                    motion_id="motion_a",
                    segment_id="seg_0",
                    start_frame=0,
                    end_frame=10,
                    source="auto_contact",
                    status="candidate",
                    motion_path=str(motion),
                )
            ],
        )

    def test_boundary_handle_flow_updates_draft_before_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self._patch_storage(root)[0], self._patch_storage(root)[1], self._patch_storage(root)[2]:
                self._seed(root)
                session = create_segmentation_edit_session(
                    "motion_a_raw",
                    session_id="timeline_session",
                    workbench_root=root / "workbench",
                )
                controller = SegmentationTimelineController(session=session)

                controller.select_segment("seg_0")
                controller.begin_boundary_edit()
                controller.preview_boundary(start_frame=2, end_frame=8)

                self.assertEqual(read_canonical_segments("motion_a_raw")[0].start_frame, 0)
                self.assertEqual(controller.state()["selected_segment"]["preview_start_frame"], 2)
                self.assertEqual(controller.state()["selected_segment"]["preview_end_frame"], 8)

                controller.apply_boundary(reason="handle edit")
                draft = read_draft_segments(session)

                self.assertEqual((draft[0].start_frame, draft[0].end_frame), (2, 8))
                self.assertEqual((read_canonical_segments("motion_a_raw")[0].start_frame, read_canonical_segments("motion_a_raw")[0].end_frame), (0, 10))

                controller.save(reason="save timeline edit")
                saved = read_canonical_segments("motion_a_raw")

                self.assertEqual((saved[0].start_frame, saved[0].end_frame), (2, 8))


if __name__ == "__main__":
    unittest.main()
