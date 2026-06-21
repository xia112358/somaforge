from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.force_proto import segments_from_masked_motion


class ForceProtoContactTests(unittest.TestCase):
    def test_force_proto_segments_include_structured_contact_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion_a.npz"
            np.savez(
                path,
                proto_start_idx=np.asarray([1]),
                proto_end_idx=np.asarray([4]),
                contact_part_mask=np.asarray(
                    [
                        [False, True],
                        [True, True],
                        [True, False],
                        [False, False],
                        [False, True],
                    ]
                ),
                active_part_mask=np.asarray(
                    [
                        [False, True],
                        [True, False],
                        [True, False],
                        [False, True],
                        [False, True],
                    ]
                ),
                support_part_mask=np.asarray(
                    [
                        [False, True],
                        [False, True],
                        [True, False],
                        [True, False],
                        [False, True],
                    ]
                ),
                contact_body_names=np.asarray(["LF", "RF"]),
            )

            segments = segments_from_masked_motion(path)

        self.assertEqual(len(segments), 1)
        segment = segments[0]
        self.assertEqual((segment.start_frame, segment.end_frame), (1, 4))
        self.assertEqual(segment.contact_start, "11")
        self.assertEqual(segment.contact_end, "00")
        self.assertEqual(segment.metadata["active_body"], "LF")
        self.assertEqual(segment.metadata["support_bodies"], ["RF"])
        self.assertIn("contact_transition", segment.metadata)
        self.assertIn("contact_events", segment.metadata)
        self.assertIn("contact_anchors", segment.metadata)


if __name__ == "__main__":
    unittest.main()

