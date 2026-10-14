import hashlib
import json
import uuid
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from motion_edit import cli
from motion_edit.contact.plans import ContactEditPlan
from motion_edit.generation.jobs import generate_candidate
from motion_edit.generation.source_prefix_collection import prepare_prefix_collection
from motion_edit.generation.source_prefix_reference import (
    SCHEMA, configure_plan_prefix, prefix_implementation_fingerprints,
)
from somaforge_core.motion_schema import newton_rollout_kinematics_provenance
from somaforge_core.robot_assets import canonical_g1_asset_metadata, encode_robot_asset_json


@pytest.fixture
def work():
    root = Path(__file__).resolve().parents[3]/"tmp/source_prefix_pipeline_tests"/uuid.uuid4().hex
    root.mkdir(parents=True)
    return root


def inputs(work, name="candidate"):
    q = np.zeros((20, 36)); q[:, 3] = 1.
    source = work/"source.npz"
    if not source.exists():
        np.savez(source, joint_pos=q, robot_asset_json=np.asarray(encode_robot_asset_json(canonical_g1_asset_metadata())),
            kinematics_provenance_json=np.asarray(json.dumps(newton_rollout_kinematics_provenance(
                source_path="native.npz", source_sha256="0"*64, output_fps=50., body_names=["pelvis"]))))
    surface = dict(surface_id="ground", object_id="ground", surface_type="plane",
                   origin=[0., 0., 0.], tangent_u=[1., 0., 0.], tangent_v=[0., 1., 0.], normal=[0., 0., 1.])
    plan = ContactEditPlan(plan_id=name, source_motion_path=str(source), source_motion_id="source",
        source_contact_layer=str(work/"contacts"), status="validated", surface_transforms=[dict(
            transform_id="turn", kind="surface_follow", source_surface=surface, target_surface=surface,
            translation_world=[0., 0., 0.])],
        metadata=dict(augmentation_objective="consolidated_v1", free_surface_contacts=True))
    path = work/f"{name}.json"; path.write_text(json.dumps(plan.to_dict()))
    (work/"contacts").mkdir(exist_ok=True)
    config = dict(schema=SCHEMA, hold_frames=5, transition_end_frame=12,
                  surface_transform_id="turn", joint_prior_scale=100., semantic_weight=10000.)
    config_path = work/"prefix.json"; config_path.write_text(json.dumps(config))
    return plan, path, config, config_path


def result(work, config):
    return SimpleNamespace(output_motion_path=work/"generated.npz", taskspace_spec_path=work/"task.npz",
        ik_output_path=work/"ik.npz", diagnostics=dict(augmentation_objective="consolidated_v1",
        free_surface_contacts=True, source_prefix_reference=config,
        root_yaw_condition=dict(reference_delta_degrees=0.), root_yaw_optimized=True))


@pytest.mark.parametrize("batch", [False, True])
def test_single_and_batch_forward_frozen_effective_plan_and_receipt(work, batch):
    _, path, config, config_path = inputs(work)
    before = path.read_bytes()
    args = ["generate-ref", "--source-prefix-config", str(config_path)]
    if batch:
        manifest = work/"manifest.json"; manifest.write_text(json.dumps(dict(plans=[dict(plan_path=path.name)])))
        args += ["--plan-manifest", str(manifest), "--output-motion-dir", str(work)]
    else:
        args += ["--plan", str(path), "--output-motion", str(work/"generated.npz")]
    with patch("motion_edit.generation.generate_contact_aware_pyroki_preview", return_value=result(work, config)) as generate:
        parsed = cli.build_parser().parse_args(args); parsed.func(parsed)
    effective = generate.call_args.args[0]
    assert effective.metadata["source_prefix_reference"] == config
    assert path.read_bytes() == before
    receipt = json.loads((work/"generated.generation.json").read_text())
    assert receipt["source_prefix_configuration"]["sha256"] == hashlib.sha256(config_path.read_bytes()).hexdigest()
    assert receipt["source_prefix_implementation"] == prefix_implementation_fingerprints()
    assert receipt["training_ready"] is False
    snapshot = Path(receipt["plan"])
    assert json.loads(snapshot.read_text())["metadata"]["source_prefix_reference"] == config
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == receipt["plan_sha256"]


def test_backend_cannot_silently_drop_prefix(work):
    _, path, config, config_path = inputs(work)
    with pytest.raises(ValueError, match="effective plan"):
        generate_candidate(path, output_motion_path=work/"generated.npz", source_prefix_config=config_path,
                           generation_fn=lambda *a, **kw: result(work, None))
    assert not (work/"generated.generation.json").exists()


def test_backend_cannot_silently_drop_root_rotation(work):
    _, path, config, config_path = inputs(work)
    def dropped_heading(*a, **kw):
        value = result(work, config)
        value.diagnostics['root_yaw_condition'] = None
        return value
    with pytest.raises(ValueError, match="root heading"):
        generate_candidate(path, output_motion_path=work/'generated.npz',
                           source_prefix_config=config_path, generation_fn=dropped_heading)
    assert not (work/'generated.generation.json').exists()


def test_standard_batch_requires_prefix_for_all_plans_before_first_solve(work):
    plan, first, config, _ = inputs(work)
    first.write_text(json.dumps(configure_plan_prefix(plan, config).to_dict()))
    _, second, _, _ = inputs(work, 'missing_prefix')
    manifest=work/'manifest.json'
    manifest.write_text(json.dumps(dict(plans=[dict(plan_path=p.name) for p in [first, second]])))
    args=cli.build_parser().parse_args(['generate-ref', '--plan-manifest', str(manifest),
                                      '--output-motion-dir', str(work)])
    with patch('motion_edit.generation.generate_contact_aware_pyroki_preview') as generate:
        with pytest.raises(ValueError, match='Standard augmentation requires'): args.func(args)
        generate.assert_not_called()


def test_standard_batch_uses_authored_prefix_without_cli_flag(work):
    plan, path, config, _ = inputs(work)
    path.write_text(json.dumps(configure_plan_prefix(plan, config).to_dict()))
    manifest=work/'manifest.json';manifest.write_text(json.dumps(dict(plans=[dict(plan_path=path.name)])))
    args=cli.build_parser().parse_args(['generate-ref', '--plan-manifest', str(manifest),
                                      '--output-motion-dir', str(work)])
    with patch('motion_edit.generation.generate_contact_aware_pyroki_preview', return_value=result(work, config)) as generate:
        args.func(args)
    assert generate.call_args.args[0].metadata['source_prefix_reference']==config
    assert generate.call_args.args[0].metadata['root_yaw_condition']['reference_delta_degrees']==0.


def test_batch_validates_all_sources_before_first_solve(work):
    _, first, _, config = inputs(work)
    plan, second, _, _ = inputs(work, "second")
    second.write_text(json.dumps(replace(plan, source_motion_path=str(work/"missing.npz")).to_dict()))
    manifest = work/"manifest.json"; manifest.write_text(json.dumps(dict(plans=[dict(plan_path=p.name) for p in [first, second]])))
    args = cli.build_parser().parse_args(["generate-ref", "--plan-manifest", str(manifest),
        "--output-motion-dir", str(work), "--source-prefix-config", str(config)])
    with patch("motion_edit.generation.generate_contact_aware_pyroki_preview") as generate:
        with pytest.raises(FileNotFoundError): args.func(args)
        generate.assert_not_called()


def test_existing_plan_conflict_is_explicit(work):
    plan, _, config, _ = inputs(work)
    configured = configure_plan_prefix(plan, config)
    with pytest.raises(ValueError, match="conflicts"):
        configure_plan_prefix(configured, dict(config, hold_frames=4))


def test_batch_rejects_configuration_changed_between_candidates(work):
    _, first, config, config_path = inputs(work)
    _, second, _, _ = inputs(work, "second")
    manifest = work/"manifest.json"
    manifest.write_text(json.dumps(dict(plans=[dict(plan_path=p.name) for p in [first, second]])))
    args = cli.build_parser().parse_args(["generate-ref", "--plan-manifest", str(manifest),
        "--output-motion-dir", str(work), "--source-prefix-config", str(config_path)])
    def generation(*a, **kw):
        config_path.write_text(json.dumps(dict(config, hold_frames=4)))
        return result(work, config)
    with patch("motion_edit.generation.generate_contact_aware_pyroki_preview", side_effect=generation) as generate:
        with pytest.raises(ValueError, match="changed during batch"):
            args.func(args)
        assert generate.call_count == 1


def test_rebase_maps_prefix_boundaries_to_native_clock_without_resampling_source(work):
    from motion_edit.generation.rebase_edit_plan import rebase_plan
    source = work/"native.npz"; source.write_bytes(b"unchanged")
    prefix = dict(schema=SCHEMA, hold_frames=5, transition_end_frame=8,
                  surface_transform_id="turn", joint_prior_scale=100., semantic_weight=10000.)
    plan = dict(plan_id="edit", source_motion_path="old.npz", pose_edits=[], edits=[],
                metadata=dict(free_surface_reference_offsets={}, source_prefix_reference=prefix))
    updated = rebase_plan(plan, [], [], [dict(segment_id="a", start_frame=0, end_frame=39)],
        [dict(segment_id="a", start_frame=0, end_frame=19)], source=source, layer=work,
        labels=work/"labels.npz", events=work/"events.jsonl", initial_q=np.zeros(36))
    mapped = updated["metadata"]["source_prefix_reference"]
    assert mapped["hold_frames"] == 3
    assert mapped["transition_end_frame"] == 4
    assert plan["metadata"]["source_prefix_reference"] == prefix
    assert source.read_bytes() == b"unchanged"


def test_invalid_plan_aborts_collection_preparation_before_outputs(work):
    plan, path, _, config_path = inputs(work)
    bad = replace(plan, plan_id="bad", surface_transforms=[])
    bad_path = work/"bad.json"; bad_path.write_text(json.dumps(bad.to_dict()))
    collection = work/"index.json"
    collection.write_text(json.dumps(dict(motion_files=[dict(plan=p.name) for p in [path, bad_path]])))
    out = work/"version"
    with pytest.raises(ValueError, match="transform"):
        prepare_prefix_collection(collection, out, config_path)
    assert not out.exists()


def test_prepare_collection_is_idempotent_and_rejects_changed_config_or_plan(work):
    _, path, config, config_path = inputs(work)
    collection = work/"index.json"; collection.write_text(json.dumps(dict(motion_files=[dict(plan=path.name)])))
    out = work/"version"
    manifest = prepare_prefix_collection(collection, out, config_path)
    assert manifest["generation_started"] is False
    assert manifest["training_ready"] is False
    assert len(manifest["plans"]) == 1
    assert prepare_prefix_collection(collection, out, config_path, resume=True) == manifest
    assert not (out/"motions").exists()
    config_path.write_text(json.dumps(dict(config, hold_frames=4)))
    with pytest.raises(ValueError, match="inputs changed"):
        prepare_prefix_collection(collection, out, config_path, resume=True)
    config_path.write_text(json.dumps(config))
    (out/manifest["plans"][0]["plan_path"]).write_text("changed")
    with pytest.raises(ValueError, match="plan changed"):
        prepare_prefix_collection(collection, out, config_path, resume=True)


def test_completed_generation_rejects_missing_prefix_and_changed_implementation(work):
    from motion_edit.generation.regenerate_edits import (
        GENERATION_SCHEMA, generation_objective, validate_completed_generation,
    )
    plan, path, config, _ = inputs(work)
    path.write_text(json.dumps(configure_plan_prefix(plan, config).to_dict()))
    paths = {key: work/key for key in ("sites", "observations", "phases", "motion", "labels", "events", "contract")}
    for key, p in paths.items(): p.write_text(key)
    digests = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()}
    objective = generation_objective(.01, .01, 4)
    record = dict(schema=GENERATION_SCHEMA, requested_objective=objective, effective_objective=objective,
        plan_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), loaded_reference=dict(
            **{k: str(paths[k]) for k in ("sites", "observations", "phases")},
            sha256={k: digests[k] for k in ("sites", "observations", "phases")}, residual_scale_m=.01),
        event_reference=dict(**{k: str(paths[k]) for k in ("motion", "labels", "events", "contract")},
            sha256={k: digests[k] for k in ("motion", "labels", "events", "contract")}),
        source_prefix_reference=config, source_prefix_implementation=prefix_implementation_fingerprints())
    validate_completed_generation(record, path, .01)
    with pytest.raises(ValueError, match="missing source prefix"):
        validate_completed_generation(dict(record, source_prefix_reference=None), path, .01)
    with pytest.raises(ValueError, match="implementation"):
        validate_completed_generation(dict(record, source_prefix_implementation={}), path, .01)
