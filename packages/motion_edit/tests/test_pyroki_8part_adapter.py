from __future__ import annotations

import unittest

import numpy as np

from motion_edit.generation.pyroki_fullbody_ik import _source_qpos, _world_body_poses


class PyrokiEightPartAdapterTests(unittest.TestCase):
    def test_source_qpos_reorders_named_joints_for_pyroki(self) -> None:
        motion = {
            "joint_pos": np.asarray([[1.0, 2.0, 3.0, 1.0, 0.0, 0.0, 0.0, 10.0, 20.0]], dtype=np.float64),
            "joint_names": np.asarray(["joint_b", "joint_a"]),
        }

        root, cfg, names = _source_qpos(motion, 1, ("joint_a", "joint_b"))

        np.testing.assert_allclose(root[0], [1.0, 2.0, 3.0, 1.0, 0.0, 0.0, 0.0])
        np.testing.assert_allclose(cfg[0], [20.0, 10.0])
        self.assertEqual(names, ["joint_b", "joint_a"])

    def test_world_body_poses_apply_floating_root_transform(self) -> None:
        root = np.asarray([1.0, 2.0, 3.0, np.sqrt(0.5), 0.0, 0.0, np.sqrt(0.5)])
        link_tf_base = np.asarray([[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0]])

        position_w, quat_w = _world_body_poses(root, link_tf_base)

        np.testing.assert_allclose(position_w[0], [1.0, 3.0, 3.0], atol=1.0e-7)
        np.testing.assert_allclose(quat_w[0], root[3:7], atol=1.0e-7)


if __name__ == "__main__":
    unittest.main()
