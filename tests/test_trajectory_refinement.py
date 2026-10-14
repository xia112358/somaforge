"""CPU regression tests for provenance, stage gates and native execution export."""
import json
from pathlib import Path
import uuid

import numpy as np
import pytest

from somaforge_core import trajectory_refinement as workflow
from somaforge_core import rollout_dataset as dataset
from somaforge_core.motion_schema import G1_29DOF_JOINT_ORDER, direct_newton_kinematics_provenance, decode_kinematics_provenance
from somaforge_core.newton_contacts import FIELDS
from somaforge_core.newton_runtime_compat import NEWTON_RUNTIME_ID
from somaforge_core.newton_support import SUPPORT_FIELDS, SUPPORT_SCHEMA
from somaforge_core.robot_assets import canonical_g1_source_metadata


@pytest.fixture
def workdir():
    # Retain artifacts under project tmp; never use pytest's auto-deleting tmpdir.
    path = Path(__file__).resolve().parents[1] / "tmp" / "trajectory_refinement_tests" / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


@pytest.fixture(scope="module")
def asset():
    return canonical_g1_source_metadata()


def recording_fixture(path, asset, *, unallocated=False, side=False, task="completion_only"):
    n = 5  # duplicate frame-zero bootstrap, then 1,2,3
    normal = [1., 0., 0.] if side else [0., 0., 1.]
    catalog = [dict(surface=0, normal_w=normal, plane_offset=0.)]
    triangle = [[0., -2., -2.], [0., 2., -2.], [0., 0., 2.]] if side else [[-2., -2., 0.], [2., -2., 0.], [0., 2., 0.]]
    binding = dict(model_fingerprint="synthetic", body_env={"0": 0},
                   shape_surface={"1": [dict(catalog[0], triangles_w=[triangle])]}, surface_catalog=catalog)
    meta = dict(env_id=0, num_envs=1, dt=.02, sim_dt=.005, fps=50, robot_asset=asset,
                newton_runtime=dict(runtime_id=NEWTON_RUNTIME_ID),
                solver_contact_semantics=dict(schema=dataset.CONTACT_SCHEMA),
                solver_support_semantics=dict(schema=SUPPORT_SCHEMA, sampling="same solve; poses separate"),
                dof_names=list(G1_29DOF_JOINT_ORDER), body_names=["left_ankle_roll_link"],
                newton_scene_binding=binding, newton_body_labels=["/World/envs/env_0/Robot/left_ankle_roll_link"],
                episode_done=False)
    q = np.zeros((n, 4)); q[:, 3] = 1
    arrays = dict(_metadata_json=np.asarray(json.dumps(meta)),
                  motion_time_step=np.array([0, 0, 1, 2, 3]), motion_id=np.zeros(n, int),
                  terminated=np.zeros(n, bool), timeout=np.zeros(n, bool),
                  root_pos=np.arange(n*3, dtype=float).reshape(n, 3)/100,
                  root_quat_xyzw=q, root_lin_vel=np.ones((n, 3)), root_ang_vel=np.zeros((n, 3)),
                  dof_pos=np.zeros((n, 29)), dof_vel=np.ones((n, 29)),
                  body_pos_w=np.zeros((n, 1, 3)), body_quat_xyzw=q[:, None],
                  body_lin_vel_w=np.ones((n, 1, 3)), body_ang_vel_w=np.zeros((n, 1, 3)))
    snapshot = dict(count=np.int32(1), active=np.array([True]), constraint_allocated=np.array([not unallocated]),
                    dist=np.array([-.001]), includemargin=np.array([0.]), type=np.array([1]),
                    worldid=np.array([0]), shape0=np.array([0]), shape1=np.array([1]),
                    body0=np.array([0]), body1=np.array([-1]), position_w=np.zeros((1, 3)),
                    efc_address=np.array([[-1 if unallocated else 0]]),
                    frame_w=np.array([[-np.asarray(normal), [0, 1, 0], [1, 0, 0]]]), constraint_rows=np.array([1]))
    snapshot.update({k: np.zeros((1, 3)) for k in SUPPORT_FIELDS})
    snapshot["force_on_body1_w"] = -100*np.asarray(normal)[None]
    for k in (*FIELDS, *SUPPORT_FIELDS):
        arrays["solver_contact_" + k] = np.stack([snapshot[k]]*n)
    for k in ("count", "shape0", "shape1", "body0", "body1"):
        arrays["raw_contact_" + k] = np.stack([snapshot[k]]*n)
    for k in ("point0_w", "point1_w", "normal_w"):
        arrays["raw_contact_" + k] = np.zeros((n, 1, 3))
    np.savez(path, **arrays)
    case = dict(key="any_name", identity="an arbitrary reference", frames=4, fps=50.,
                task=dict(kind=task, max_abnormal_contacts=0), expected_surface_catalog=catalog,
                contract=dict(schema="explicit_action_contact_acceptance_v2", frame_count=4, fps=50,
                              retained_blocks=[[0, 4]], policy=dict(max_dropout_frames=0, stable_frames=3),
                              actions=[dict(id="hold", start=0, end=3,
                                            requirements=[dict(kind="keep", part=0, surface=0)])]))
    return arrays, case


def test_complete_segment_does_not_stitch_or_hide_failed_first_episode():
    np.testing.assert_array_equal(dataset.complete_segment([0, 0, 1, 2, 3], [0]*5, [0]*5, 4), [1, 2, 3, 4])
    assert dataset.complete_segment([0, 1, 0, 1, 2, 3], [0]*6, [0]*6, 4) is None
    assert dataset.complete_segment([0, 1, 2, 3], [0, 0, 1, 0], [0]*4, 4) is None
    assert dataset.complete_segment([0, 1, 2, 3], [0]*4, [0, 1, 0, 0], 4) is None


def test_real_contact_logic_and_pose_preserving_export(workdir, asset):
    path = workdir / "recording.npz"
    arrays, case = recording_fixture(path, asset, task="contact_events")
    report = dataset.inspect_recording(path, case)
    assert report["status"] == "passed" and report["task_passed"] is True
    reference = workdir / "reference.npz"
    reference.write_bytes(b"reference identity")
    case["reference"] = {"motion_file": str(reference)}
    report["context"] = {"trial": 0}
    destination = workdir / "export"
    policy = dict(path="selected.pt", sha256="policy")
    dataset.export_recording(path, case, destination, report, policy)
    dataset.export_recording(path, case, destination, report, policy)  # content-checked resume
    with np.load(destination / "motion.npz") as motion:
        decode_kinematics_provenance(motion["kinematics_provenance_json"], context="exported actual execution")
        np.testing.assert_array_equal(motion["joint_pos"][:, :3], arrays["root_pos"][1:])
        np.testing.assert_array_equal(motion["joint_vel"][:, :3], arrays["root_lin_vel"][1:])
    with np.load(destination / "observations.npz") as observations:
        assert observations["contact_part_mask"][:, 0].all()
        assert not observations["contact_part_mask"][:, 1:].any()
        assert observations["observed_support_normal_force_n"][:, 0].tolist() == [100]*4
        assert json.loads(observations["metadata_json"].item())["clock"]["strict_pose_contact_same_state"] is False


def test_unallocated_actual_contact_is_an_error(workdir, asset):
    path = workdir / "unallocated.npz"
    _, case = recording_fixture(path, asset, unallocated=True)
    with pytest.raises(ValueError, match="Unallocated"):
        dataset.inspect_recording(path, case)


def test_side_contact_excluded_and_fails_gate(workdir, asset):
    path = workdir / "side.npz"
    _, case = recording_fixture(path, asset, side=True)
    payload, report = dataset.read_execution(path, case)
    assert report["status"] == "failed" and report["abnormal_contact_count"] == 4
    assert not payload["contacts"]["contact_part_mask"].any()


def test_missing_evidence_cannot_fall_back_to_force(workdir, asset):
    path = workdir / "incomplete.npz"
    arrays, case = recording_fixture(path, asset)
    arrays.pop("solver_contact_includemargin")
    np.savez(path, **arrays)
    with pytest.raises(KeyError):
        dataset.inspect_recording(path, case)


def test_completion_is_distinct_from_task_acceptance(workdir, asset):
    path = workdir / "task_failure.npz"
    _, case = recording_fixture(path, asset, task="contact_events")
    case["contract"]["actions"][0]["requirements"][0]["part"] = 1
    report = dataset.inspect_recording(path, case)
    assert report["execution_passed"] is True and report["task_passed"] is False
    assert report["status"] == "failed"


def test_changed_recording_blocks_cached_attempt(workdir):
    recording = workdir / "recording.npz"
    recording.write_bytes(b"original")
    context = {"policy": "a"}
    workflow.write_json(workdir / "trial" / "attempt" / "report.json",
                        dict(status="passed", context=context, artifacts=[workflow.fingerprint(recording)]))
    recording.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        workflow.completed_attempt(workdir / "trial", context)


def test_complete_failed_trial_is_not_retried_until_success(workdir):
    report = dict(status="failed", context={"seed": 42}, artifacts=[])
    workflow.write_json(workdir / "trial" / "attempt" / "report.json", report)
    assert workflow.completed_attempt(workdir / "trial", {"seed": 42}) == report


def test_train_dry_run_is_single_joint_command_and_no_process(monkeypatch, workdir):
    plan = dict(output_dir=str(workdir), base_checkpoint=str(workdir / "base.pt"),
                max_episode_length_s=22, config=dict(train=dict(num_envs=100, iterations=200, save_interval=20)))
    monkeypatch.setattr(workflow, "checkpoint_info", lambda _: dict(iteration=100, config={}))
    monkeypatch.setattr(workflow, "run_command", lambda *_: pytest.fail("dry run launched a subprocess"))
    report = workflow.train(plan, execute=False, device="cuda:0", visualizer="kit", headless=True)
    command = report["command"]
    assert report["remaining_iterations"] == 200
    assert command[command.index("--motion-manifest") + 1] == str(workdir / "references.json")
    assert "--headless" in command and "--visualizer" not in command
    assert not (workdir / "training").exists()


def test_collection_requires_same_policy_evaluation(monkeypatch, workdir):
    root = workdir / "policy"
    (workdir / "plan.json").write_text("{}")
    workflow.write_json(root / "evaluation_summary.json", dict(checkpoint={"sha256": "old"}, plan_sha256="old"))
    monkeypatch.setattr(workflow, "policy_run", lambda *_: ({"sha256": "new"}, root))
    plan = dict(output_dir=str(workdir), cases=[], config=dict(collection={}))
    with pytest.raises(ValueError, match="frozen policy"):
        workflow.evaluate_or_collect(plan, "collect", "new.pt", execute=False)


def test_evaluation_options_parse_with_existing_tyro_contract():
    import tyro
    from holosoma.config_types.eval_callback import EvaluationConfig
    from holosoma.utils.tyro_utils import TYRO_CONIFG
    plan = dict(output_dir="/project/output")
    cmd = workflow.recording_command(plan, dict(key="arbitrary", frames=20), "/policy.pt", "/recording.npz",
                                     seed=100, noise=0., device="cuda:0", visualizer=None, headless=False)
    parsed, _ = tyro.cli(EvaluationConfig, args=cmd[3:], return_unknown_args=True, config=TYRO_CONIFG)
    assert parsed.recording.config.enabled and parsed.recording.config.record_initial_state
    assert parsed.num_envs == 1 and parsed.max_steps == 30
    assert not parsed.acceptance.config.enabled


def make_generic_input(workdir, asset):
    entries = []
    for i, frames in enumerate((4, 7)):
        path = workdir / f"arbitrary_{i}.npz"
        provenance = direct_newton_kinematics_provenance(
            source_path="source", source_sha256="0"*64, output_fps=50, body_names=["pelvis"])
        q = np.zeros((frames, 36)); q[:, 3] = 1
        body_q = np.zeros((frames, 1, 4)); body_q[..., 0] = 1
        np.savez(path, joint_pos=q, joint_vel=np.zeros((frames, 35)), fps=np.asarray(50.),
                 body_pos_w=np.zeros((frames, 1, 3)), body_quat_w=body_q,
                 body_lin_vel_w=np.zeros((frames, 1, 3)), body_ang_vel_w=np.zeros((frames, 1, 3)),
                 robot_asset_json=np.asarray(json.dumps(asset)),
                 kinematics_provenance_json=np.asarray(json.dumps(provenance)))
        entries.append(dict(motion_id=f"custom/{i}", motion_file=path.name, terrain_id=8))
    (workdir / "terrain.obj").write_text("test terrain identity\n")
    (workdir / "base.pt").write_bytes(b"preflight only fingerprints checkpoint")
    workflow.write_json(workdir / "input.json", dict(motion_files=entries,
                        terrains=[dict(terrain_id=8, terrain_file="terrain.obj")]))
    config = dict(schema=workflow.SCHEMA, input=dict(kind="motion_manifest", path=str(workdir / "input.json")),
                  base_checkpoint=str(workdir / "base.pt"), output_dir=str(workdir / "output"),
                  train=dict(num_envs=12, iterations=100, save_interval=10),
                  evaluation=dict(attempts=2, min_success_rate=1., seed=1, initial_pose_noise=0.),
                  collection=dict(attempts=2, seed=10, initial_pose_noise=0.),
                  task=dict(kind="completion_only", max_abnormal_contacts=0))
    workflow.write_json(workdir / "config.json", config)
    return workdir / "config.json"


def test_generic_prepare_and_stale_input_gate(workdir, asset, monkeypatch):
    config = make_generic_input(workdir, asset)
    monkeypatch.setattr(workflow, "run_command", lambda *_: pytest.fail("prepare started a process"))
    plan = workflow.prepare(config)
    assert len(plan["cases"]) == 2 and [c["frames"] for c in plan["cases"]] == [4, 7]
    assert not (workdir / "output").exists()
    workflow.prepare(config, execute=True)
    loaded = workflow.load_plan(config)
    assert len(loaded["manifest"]["motion_files"]) == 2
    assert len(loaded["manifest"]["terrains"]) == 1
    workflow.prepare(config, execute=True)  # identical preparation is idempotent
    (workdir / "terrain.obj").write_text("changed terrain\n")
    with pytest.raises(ValueError, match="changed"):
        workflow.load_plan(config)


def test_manifest_declared_hash_is_not_silently_recomputed(workdir, asset):
    config = make_generic_input(workdir, asset)
    path = workdir / "input.json"
    value = workflow.read_json(path)
    value["motion_files"][0]["motion_sha256"] = "0" * 64
    workflow.write_json(path, value)
    with pytest.raises(ValueError, match="declared hash"):
        workflow.prepare(config)


def test_per_motion_contracts_support_different_trajectory_lengths(workdir, asset):
    config_path = make_generic_input(workdir, asset)
    config = workflow.read_json(config_path)
    config["task"]["kind"] = "contact_events"
    workflow.write_json(config_path, config)
    inputs = workflow.read_json(workdir / "input.json")
    for entry, frames in zip(inputs["motion_files"], (4, 7)):
        contract = dict(schema="explicit_action_contact_acceptance_v2", frame_count=frames, fps=50,
                        actions=[dict(id="task", start=0, end=frames-1, requirements=[])])
        contract_name = f"contract_{frames}.json"
        workflow.write_json(workdir / contract_name, contract)
        entry["task_contract"] = contract_name
        entry["contact_catalog_file"] = "catalog.npz"
    np.savez(workdir / "catalog.npz", contact_semantics_json=np.asarray(json.dumps(
        dict(scene=dict(surface_catalog=[dict(surface=0, normal_w=[0, 0, 1], plane_offset=0)])))))
    workflow.write_json(workdir / "input.json", inputs)
    plan = workflow.prepare(config_path)
    assert [c["contract"]["frame_count"] for c in plan["cases"]] == [4, 7]


def test_full_stage_flow_excludes_failed_motions_and_resumes_without_relaunch(workdir, asset, monkeypatch):
    config = make_generic_input(workdir, asset)
    plan = workflow.prepare(config, execute=True)
    policy = workflow.fingerprint(workdir / "base.pt")
    root = workdir / "output" / "policies" / policy["sha256"]
    monkeypatch.setattr(workflow, "policy_run", lambda *_: (policy, root))
    calls = []

    def simulated_command(command, directory):
        calls.append(command)
        directory.mkdir(parents=True)
        # Four recorded frames: first reference passes, the seven-frame one fails.
        recording_fixture(directory / "recording.npz", asset)

    monkeypatch.setattr(workflow, "run_command", simulated_command)
    launcher = dict(device="cuda:0", visualizer=None, headless=False)
    preview = workflow.evaluate_or_collect(plan, "evaluate", "policy.pt", execute=False, **launcher)
    assert len(preview["pending_commands"]) == 4 and not calls
    evaluated = workflow.evaluate_or_collect(plan, "evaluate", "policy.pt", execute=True, **launcher)
    assert [m["eligible"] for m in evaluated["motions"]] == [True, False]
    assert len(calls) == 4
    workflow.evaluate_or_collect(plan, "evaluate", "policy.pt", execute=True, **launcher)
    assert len(calls) == 4
    collected = workflow.evaluate_or_collect(plan, "collect", "policy.pt", execute=True, **launcher)
    assert collected["omitted_motion_count"] == 1 and len(calls) == 6
    exported = workflow.export_dataset(plan, "policy.pt", execute=True)
    assert len(exported["motion_files"]) == 2
    assert all(e["motion_name"].startswith("custom/0/") for e in exported["motion_files"])
    workflow.export_dataset(plan, "policy.pt", execute=True)
    assert len(calls) == 6
