from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
from somaforge_core.robot_assets import encode_robot_asset_json
import pytest

import motion_edit.generation as generation
import motion_edit.contact.layers as contact_layers
from motion_edit.contact.plans import ContactEditPlan
from motion_edit.generation import contact_aware_preview as preview
from motion_edit.generation.rollout_authority import _load_source_motion
from motion_edit.generation.taskspace_spec import ContactAwareTaskspaceMotion


def _rollout_motion() -> dict[str, np.ndarray]:
    return {
        "robot_asset_json": np.asarray(encode_robot_asset_json()),
        "fps": np.asarray(50.0),
        "joint_pos": np.asarray([[0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]]),
        "joint_vel": np.zeros((1, 7), dtype=np.float64),
        "joint_names": np.asarray(["joint_0"], dtype=object),
        "body_names": np.asarray(["pelvis"], dtype=object),
        "body_pos_w": np.zeros((1, 1, 3), dtype=np.float64),
        "body_quat_w": np.asarray([[[1.0, 0.0, 0.0, 0.0]]], dtype=np.float64),
        "raw_contact_count": np.zeros(1, dtype=np.int32),
        "raw_contact_shape0": np.full((1, 1), -1, dtype=np.int32),
        "raw_contact_shape1": np.full((1, 1), -1, dtype=np.int32),
        "raw_contact_body0": np.full((1, 1), -1, dtype=np.int32),
        "raw_contact_body1": np.full((1, 1), -1, dtype=np.int32),
        "raw_contact_point0_w": np.zeros((1, 1, 3), dtype=np.float64),
        "raw_contact_point1_w": np.zeros((1, 1, 3), dtype=np.float64),
        "raw_contact_normal_w": np.zeros((1, 1, 3), dtype=np.float64),
        "raw_contact_force_w": np.zeros((1, 1, 3), dtype=np.float64),
    }


def test_plan_source_is_the_only_rollout_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source_motion.npz"
    source.touch()
    plan = ContactEditPlan(
        plan_id="plan",
        source_motion_id="motion",
        source_motion_path=str(source),
        source_contact_layer="contact/source",
        status="validated",
        edits=[],
        metadata={"contact_force_source_path": str(source)},
    )
    loaded: list[Path] = []

    def fake_load(path: str | Path):
        loaded.append(Path(path).resolve())
        return _rollout_motion()

    monkeypatch.setattr(preview, "_load_motion_npz", fake_load)
    motion, path = _load_source_motion(plan, preview)

    assert motion["joint_pos"].shape == (1, 8)
    assert path == source.resolve()
    assert loaded == [source.resolve()]


def test_generation_uses_one_rollout_source_everywhere(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "source_motion.npz"
    source_terrain = tmp_path / "source_terrain.obj"
    target_terrain = source_terrain
    source_path.touch()
    source = _rollout_motion()
    plan = ContactEditPlan(
        plan_id="plan",
        source_motion_id="motion",
        source_motion_path=str(source_path),
        source_contact_layer="contact/source",
        status="validated",
        edits=[],
        metadata={
            "contact_force_source_path": str(source_path),
            "augmentation_objective": "consolidated_v1",
            "free_surface_contacts": True,
            "source_terrain_mesh": str(source_terrain),
            "target_terrain_mesh": str(target_terrain),
        },
    )
    output = tmp_path / "output.npz"
    work = tmp_path / "work"
    captured: dict[str, object] = {}

    def fake_load(path: str | Path):
        resolved = Path(path).resolve()
        if resolved == source_path.resolve():
            return source
        if resolved.name.endswith("pyroki_preview.npz"):
            return {}
        raise AssertionError(f"unexpected motion load: {resolved}")

    monkeypatch.setattr(preview, "_load_motion_npz", fake_load)
    monkeypatch.setattr(preview, "validate_contact_edit_plan", lambda *args, **kwargs: [])
    monkeypatch.setattr(preview, "_resolve_layers_root", lambda *args, **kwargs: tmp_path)
    monkeypatch.setattr(
        contact_layers,
        "read_verified_contact_graph",
        lambda *args, **kwargs: SimpleNamespace(motion_id="motion", anchors=[]),
    )
    monkeypatch.setattr(
        preview,
        "expand_task_variant_plan",
        lambda *args, **kwargs: SimpleNamespace(
            edits=[], surfaces=[], metadata={}, warnings=[]
        ),
    )

    def fake_proxy(*, motion, source_motion, **kwargs):
        captured["proxy_motion"] = motion
        captured["proxy_path"] = Path(source_motion).resolve()
        return (
            {
                "keypoint_pelvis": np.zeros((1, 3), dtype=np.float64),
                "body_pos_w": np.zeros((1, 1, 3), dtype=np.float64),
                "body_lin_vel_w": np.zeros((1, 1, 3), dtype=np.float64),
            },
            [],
            {},
        )

    monkeypatch.setattr(preview, "_batch_contact_laplacian_proxy_motion", fake_proxy)
    monkeypatch.setattr(preview, "apply_pose_edits_to_proxy", lambda proxy, edits: (proxy, {}))

    def fake_bind(graph, *, source_motion_path, **kwargs):
        captured["binding_path"] = Path(source_motion_path).resolve()
        return [], {"warnings": []}

    monkeypatch.setattr(contact_layers, "verified_source_patches", fake_bind)

    def fake_build(*, source_motion, contact_pose_motion, semantic_names, semantic_targets_w, **kwargs):
        captured["taskspace_source"] = source_motion
        captured["taskspace_contact_pose"] = contact_pose_motion
        return ContactAwareTaskspaceMotion(
            motion_id="motion",
            fps=50.0,
            frame_start=0,
            frame_end=1,
            semantic_names=tuple(semantic_names),
            semantic_targets_w=np.asarray(semantic_targets_w, dtype=np.float64),
            semantic_weights=np.ones((1, len(tuple(semantic_names))), dtype=np.float64),
            contacts=(),
            source_qpos=np.asarray(source_motion["joint_pos"], dtype=np.float64),
            source_qvel=np.asarray(source_motion["joint_vel"], dtype=np.float64),
            source_reference_weights=np.zeros_like(
                np.asarray(source_motion["joint_pos"], dtype=np.float64)
            ),
            boundary_weights=np.zeros(1, dtype=np.float64),
            metadata={},
        )

    monkeypatch.setattr(preview, "build_contact_aware_taskspace_motion", fake_build)
    monkeypatch.setattr(
        preview,
        "_task_visualization_proxy",
        lambda *, proxy, source_motion: proxy,
    )
    def fake_write(path, spec):
        captured["taskspace_metadata"] = dict(spec.metadata)
        Path(path).touch()

    monkeypatch.setattr(
        preview,
        "write_contact_aware_taskspace_motion",
        fake_write,
    )

    def fake_run(*, source_motion_path, ik_output_path, **kwargs):
        captured["pyroki_source_path"] = Path(source_motion_path).resolve()
        Path(ik_output_path).touch()

    monkeypatch.setattr(preview, "_run_pyroki_preview_subprocess", fake_run)

    def fake_merge(*, source_motion, **kwargs):
        captured["merge_source"] = source_motion
        return {"motion_edit_generation_metadata": np.asarray("{}")}

    monkeypatch.setattr(preview, "merge_pyroki_preview_motion", fake_merge)
    monkeypatch.setattr(preview, "_stamp_robot_asset", lambda generated: generated)

    generation.generate_contact_aware_pyroki_preview(
        plan,
        output_motion_path=output,
        intermediate_dir=work,
        overwrite=True,
    )

    assert captured["proxy_motion"] is source
    assert captured["binding_path"] == source_path.resolve()
    assert captured["taskspace_source"] is source
    assert captured["taskspace_contact_pose"] is source
    assert captured["merge_source"] is source
    assert captured["proxy_path"] == source_path.resolve()
    assert captured["pyroki_source_path"] == source_path.resolve()
    assert captured["taskspace_metadata"] == {
        "collision_reference_motion": str(source_path.resolve()),
        "contact_patch_source_motion": str(source_path.resolve()),
        "contact_target_pose_source_motion": str(source_path.resolve()),
        "cross_reference_mixing": False,
        "environment_collision_contract": (
            "source_relative_one_sided_penetration"
        ),
        "joint_initializer_source_motion": str(source_path.resolve()),
        "reference_authority": "rollout_source_only",
        "reference_role_contract": "single_rollout_source",
        "semantic_source_motion": str(source_path.resolve()),
        "source_terrain_mesh": str(source_terrain.resolve()),
        "target_terrain_mesh": str(target_terrain.resolve()),
        "normalize_contact_group_weights": False,
        "augmentation_objective": "consolidated_v1",
        "free_surface_contacts": True,
        "convex_surface_targets": False,
        "surface_reference_ratio": 0.01,
        "support_surface_transforms": [],
    }
    assert output.is_file()

    with np.load(output, allow_pickle=True) as data:
        assert str(np.asarray(data["source_motion_path"]).item()) == str(
            source_path.resolve()
        )
        assert "force_rollout_source_path" not in data.files
