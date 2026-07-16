from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

import numpy as np

from motion_edit.generation.pyroki_trajectory_optimizer import (
    EnvironmentContactAnchors,
    ForceLinearization,
    WholeTrajectoryConfig,
    solve_whole_trajectory,
)
from motion_edit.generation.pyroki_fullbody_ik import solve_pyroki_fullbody_ik


@unittest.skipUnless(
    importlib.util.find_spec("pyroki") is not None and importlib.util.find_spec("jaxls") is not None,
    "PyRoki/JAXLS environment is not installed",
)
class WholeTrajectoryOptimizerTests(unittest.TestCase):
    def _robot(self):
        import pyroki
        import yourdfpy

        repo = Path(__file__).resolve().parents[3]
        urdf_path = repo / "src/holosoma/holosoma/data/robots/g1/g1_29dof_spherehand.urdf"
        return urdf_path, pyroki.Robot.from_urdf(yourdfpy.URDF.load(str(urdf_path), load_meshes=False))

    def test_environment_anchor_and_nonzero_force_displacement_share_one_graph(self) -> None:
        import jax.numpy as jnp

        _urdf_path, robot = self._robot()
        frames = 4
        joint_cfg = np.broadcast_to(
            (np.asarray(robot.joints.lower_limits) + np.asarray(robot.joints.upper_limits)) / 2.0,
            (frames, int(robot.joints.num_actuated_joints)),
        ).copy()
        root = np.zeros((frames, 7), dtype=np.float64)
        root[:, 2] = 0.8
        root[:, 3] = 1.0
        fk = np.asarray(robot.forward_kinematics(jnp.asarray(joint_cfg)))
        link_names = tuple(robot.links.names)
        pelvis = link_names.index("pelvis")
        left_foot = link_names.index("left_ankle_roll_link")
        groups = [np.asarray([pelvis]), np.asarray([left_foot])]
        local_points = fk[:, [pelvis, left_foot], 4:7]
        target_points = local_points + root[:, None, :3]
        force_position = target_points[:, 1:2]
        zeros = np.zeros_like(force_position)
        normals = np.zeros_like(force_position)
        normals[..., 2] = 1.0
        target_normal_displacement = np.zeros((frames, 1), dtype=np.float64)
        target_normal_displacement[[1, 3], 0] = 5.0e-4

        result = solve_whole_trajectory(
            robot=robot,
            root_qpos_init=root,
            joint_cfg_init=joint_cfg,
            target_position_w=target_points,
            target_link_groups=groups,
            target_weights=np.ones((frames, len(groups))),
            force_link_groups=[groups[1]],
            force_linearization=ForceLinearization(
                target_force_w=zeros,
                actual_force_w=zeros,
                contact_mask=np.ones((frames, 1)),
                contact_normals_w=normals,
                reference_link_position_w=force_position,
                target_normal_displacement_m=target_normal_displacement,
            ),
            environment_contacts=EnvironmentContactAnchors(
                anchor_ids=("left_foot_ground",),
                semantic_names=("left_foot",),
                start_frames=np.asarray([1]),
                end_frames=np.asarray([4]),
                representative_frames=np.asarray([2]),
                source_position_w=force_position[2],
                target_position_w=force_position[2] + np.asarray([[5.0e-4, 0.0, 0.0]]),
                edited=np.asarray([True]),
                link_groups=[groups[1]],
            ),
            object_points_w=np.asarray(
                [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                dtype=np.float64,
            ),
            config=WholeTrajectoryConfig(max_iterations=40),
        )

        self.assertEqual(result.root_qpos.shape, root.shape)
        self.assertEqual(result.joint_cfg.shape, joint_cfg.shape)
        self.assertEqual(
            result.metadata["objective_families"],
            ["contact_interaction_laplacian", "temporal_laplacian", "contact_force"],
        )
        self.assertTrue(result.metadata["whole_trajectory_joint_optimization"])
        self.assertEqual(result.metadata["environment_contact_handle_model"], "external_surface_anchor")
        self.assertEqual(result.metadata["hard_constraint_count"], 3)
        self.assertLessEqual(result.metadata["environment_anchor_error_max_m"], 5.0e-4)
        achieved_normal_displacement = np.sum(
            (result.force_solved_position_w - result.force_reference_position_w) * normals,
            axis=2,
        )
        self.assertGreater(achieved_normal_displacement[1, 0], 2.5e-4)
        self.assertGreater(achieved_normal_displacement[3, 0], 2.5e-4)
        self.assertLess(abs(achieved_normal_displacement[2, 0]), 5.0e-4)

    def test_fullbody_entrypoint_uses_whole_trajectory_solver(self) -> None:
        import jax.numpy as jnp

        urdf_path, robot = self._robot()
        frames = 4
        joint_cfg = np.broadcast_to(
            (np.asarray(robot.joints.lower_limits) + np.asarray(robot.joints.upper_limits)) / 2.0,
            (frames, int(robot.joints.num_actuated_joints)),
        ).copy()
        root = np.zeros((frames, 7), dtype=np.float64)
        root[:, 2] = 0.8
        root[:, 3] = 1.0
        fk = np.asarray(robot.forward_kinematics(jnp.asarray(joint_cfg)))
        names = tuple(robot.links.names)
        pelvis = names.index("pelvis")
        left_foot = names.index("left_ankle_roll_link")
        world_position = fk[..., 4:7] + root[:, None, :3]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = directory / "source.npz"
            lte = directory / "lte.npz"
            output = directory / "output.npz"
            np.savez(
                source,
                joint_pos=np.concatenate([root, joint_cfg], axis=1),
                joint_names=np.asarray(robot.joints.actuated_names, dtype=object),
                body_names=np.asarray(["pelvis", "left_ankle_roll_link"], dtype=object),
                fps=np.asarray(50.0),
            )
            np.savez(
                lte,
                source_demo=np.asarray(str(source)),
                pelvis=world_position[:, pelvis],
                left_foot=world_position[:, left_foot],
                orientation_target_left_foot=fk[:, left_foot, :4],
                interaction_object_points_w=np.asarray(
                    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                    dtype=np.float64,
                ),
            )

            solve_pyroki_fullbody_ik(
                lte_path=lte,
                output_path=output,
                robot_urdf=urdf_path,
                max_nfev=2,
            )

            with np.load(output, allow_pickle=False) as result:
                self.assertEqual(str(result["ik_solver"]), "pyroki_jaxls_whole_trajectory")
                self.assertEqual(result["joint_pos"].shape[0], frames)
                self.assertIn("robot_asset_json", result.files)
                self.assertEqual(
                    result["ik_objective_families"].tolist(),
                    ["contact_interaction_laplacian", "temporal_laplacian", "contact_force"],
                )


if __name__ == "__main__":
    unittest.main()
