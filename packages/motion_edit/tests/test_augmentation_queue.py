from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from motion_edit import augmentation
from motion_edit.augmentation import (
    ACCEPTED_MANIFEST_SCHEMA,
    QUEUE_SCHEMA,
    AugmentationAcceptanceReport,
    AugmentationQueue,
    AugmentationQueueJob,
    AugmentationRunConfig,
    run_augmentation_queue,
    validate_generated_augmentation,
)
from motion_edit.cli import build_parser
from somaforge_core.robot_assets import encode_robot_asset_json


class TestAugmentationAcceptance:
    def _write_candidate(self, root: Path, *, anchor_error_m: float = 4.0e-4) -> Path:
        ik_path = root / "candidate.fullbody_ik.npz"
        ik_metadata = {
            "environment_contact_anchor_count_hard": 1,
            "hard_constraint_count": 3,
            "environment_anchor_error_max_m": anchor_error_m,
        }
        np.savez(
            ik_path,
            ik_solver=np.asarray("pyroki_jaxls_whole_trajectory"),
            ik_metadata_json=np.asarray(json.dumps(ik_metadata), dtype=object),
        )

        generation_metadata = {
            "source_plan_id": "plan_a",
            "fullbody_solver": "batch_contact_laplacian",
            "output_kind": "fullbody_ik_after_contact_laplacian_proxy",
            "joint_consistency": "fullbody_ik_subprocess",
            "contact_laplacian_fullbody_ik_motion": str(ik_path),
            "solver_metadata": {"solver": "batch_contact_laplacian"},
            "evaluation_summary": {"edited_contact_target_error_after": {"max": 1.0e-3}},
        }
        candidate = root / "candidate.npz"
        body_quat = np.zeros((3, 2, 4), dtype=np.float64)
        body_quat[..., 0] = 1.0
        np.savez(
            candidate,
            joint_pos=np.zeros((3, 36), dtype=np.float64),
            joint_vel=np.zeros((3, 35), dtype=np.float64),
            joint_names=np.asarray([f"joint_{index}" for index in range(29)]),
            body_pos_w=np.zeros((3, 2, 3), dtype=np.float64),
            body_quat_w=body_quat,
            body_names=np.asarray(["pelvis", "left_ankle_roll_link"]),
            is_qpos=np.asarray(True),
            robot_asset_json=np.asarray(encode_robot_asset_json()),
            motion_edit_generation_metadata=np.asarray(json.dumps(generation_metadata), dtype=object),
        )
        return candidate

    def test_accepts_joint_consistent_whole_trajectory_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            candidate = self._write_candidate(Path(tmp))
            report = validate_generated_augmentation(candidate, expected_plan_id="plan_a")

        assert report.passed, report.errors
        assert report.checks["physics_replay_required"]
        assert report.checks["solver"] == "whole_trajectory_contact_laplacian_then_pyroki"

    def test_rejects_candidate_outside_environment_anchor_tolerance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            candidate = self._write_candidate(Path(tmp), anchor_error_m=8.0e-4)
            report = validate_generated_augmentation(candidate, expected_plan_id="plan_a")

        assert not report.passed
        assert "environment-anchor error" in report.errors[0]


class TestAugmentationQueue:
    def _job(self, root: Path, *, output_name: str = "candidate.npz") -> AugmentationQueueJob:
        return AugmentationQueueJob(
            job_id="plan_a",
            plan_id="plan_a",
            plan_path=str(root / "plan_a.json"),
            source_motion_id="motion_a",
            output_motion_path=str(root / output_name),
            motion_version_id="aug_plan_a",
            output_contact_layer="contact/generated",
        )

    def test_persists_execution_state_separately_from_accepted_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = AugmentationQueue.open(
                state_path=root / "queue.json",
                accepted_manifest_path=root / "accepted.json",
                source_plan_manifest=root / "plans.json",
            )
            queue.ensure_jobs([self._job(root)])
            queue.update(
                "plan_a",
                status="accepted",
                attempts=1,
                acceptance={"passed": True, "checks": {"physics_replay_required": True}},
            )

            state = json.loads((root / "queue.json").read_text(encoding="utf-8"))
            accepted = json.loads((root / "accepted.json").read_text(encoding="utf-8"))
            reopened = AugmentationQueue.open(
                state_path=root / "queue.json",
                accepted_manifest_path=root / "accepted.json",
                source_plan_manifest=root / "plans.json",
            )

        assert state["schema"] == QUEUE_SCHEMA
        assert state["status"] == "complete"
        assert accepted["schema"] == ACCEPTED_MANIFEST_SCHEMA
        assert accepted["count"] == 1
        assert accepted["physics_replay_required"]
        assert reopened.jobs["plan_a"]["status"] == "accepted"

    def test_resume_rejects_changed_immutable_job_definition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = AugmentationQueue.open(
                state_path=root / "queue.json",
                accepted_manifest_path=root / "accepted.json",
                source_plan_manifest=root / "plans.json",
            )
            queue.ensure_jobs([self._job(root)])

            with pytest.raises(ValueError, match="changed immutable field"):
                queue.ensure_jobs([self._job(root, output_name="different.npz")])

    def test_runner_generates_then_accepts_then_registers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "plan_a.json"
            manifest_path = root / "plans.json"
            candidate_path = root / "candidate.npz"
            manifest_path.write_text(json.dumps({"plans": [{"plan_path": plan_path.name}]}), encoding="utf-8")
            plan = SimpleNamespace(
                plan_id="plan_a",
                source_motion_id="motion_a",
                output_motion_path=str(candidate_path),
                output_contact_layer="contact/generated",
                output_segment_layer=None,
            )
            events: list[str] = []

            monkeypatch.setattr(augmentation, "read_contact_edit_plan", lambda _path: plan)

            def fake_generate(**_kwargs: object) -> SimpleNamespace:
                events.append("generate")
                candidate_path.touch()
                return SimpleNamespace(output_motion_path=candidate_path)

            def fake_validate(*_args: object, **_kwargs: object) -> AugmentationAcceptanceReport:
                events.append("accept")
                return AugmentationAcceptanceReport(True, str(candidate_path), "plan_a")

            def fake_register(**_kwargs: object) -> None:
                events.append("register")

            monkeypatch.setattr(augmentation, "_run_one_generation_attempt", fake_generate)
            monkeypatch.setattr(augmentation, "validate_generated_augmentation", fake_validate)
            monkeypatch.setattr(augmentation, "_register_accepted_candidate", fake_register)

            summary = run_augmentation_queue(
                AugmentationRunConfig(
                    plan_manifest=manifest_path,
                    state_path=root / "queue.json",
                    accepted_manifest=root / "accepted.json",
                    register_motion_version=True,
                    max_attempts=1,
                ),
                emit=lambda _message: None,
            )
            state = json.loads((root / "queue.json").read_text(encoding="utf-8"))

        assert events == ["generate", "accept", "register"]
        assert summary.generated == 1
        assert summary.accepted == 1
        assert state["jobs"]["plan_a"]["motion_version_registered"] is True


class TestAugmentationCli:
    def test_public_augmentation_command_uses_queue_contract(self) -> None:
        args = build_parser().parse_args(["generate-augmentations", "--plan-manifest", "plans.json"])

        assert args.func.__name__ == "_cmd_generate_augmentations"
        assert args.fullbody_solver == "batch_contact_laplacian"
        assert args.max_attempts == 2
        assert not args.register_motion_version
