"""Manifest-driven joint WBT refinement. Planning never starts a simulator.

The controller owns provenance and stage dependencies; physics and optimization
remain in the existing WBT entrypoints. Collection size is entirely data driven.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import shlex
import subprocess
import sys
import uuid

import numpy as np

from .asset_registry import sha256_file
from .motion_schema import decode_kinematics_provenance
from .robot_assets import canonical_g1_asset_metadata, decode_robot_asset_json, somaforge_root

SCHEMA = "somaforge_trajectory_refinement_v1"


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value, *, immutable=False):
    path = Path(path)
    if immutable and path.exists():
        if read_json(path) != value:
            raise ValueError(f"Existing artifact differs; use a new output directory: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if immutable else "w") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def resolve(path, base):
    path = Path(path).expanduser()
    return (path if path.is_absolute() else Path(base) / path).resolve()


def fingerprint(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=sha256_file(path))


def verify_files(files):
    for item in files:
        if sha256_file(Path(item["path"])) != item["sha256"]:
            raise ValueError(f"Input/artifact changed: {item['path']}")


def load_config(path):
    path = Path(path).resolve()
    config = read_json(path)
    if config.get("schema") != SCHEMA:
        raise ValueError(f"Expected configuration schema {SCHEMA}")
    allowed = {"schema", "input", "base_checkpoint", "output_dir", "train", "evaluation", "collection", "task"}
    if set(config) - allowed:
        raise ValueError(f"Unknown configuration keys: {sorted(set(config) - allowed)}")
    for section, fields in {
        "input": {"kind", "path"},
        "train": {"num_envs", "iterations", "save_interval"},
        "evaluation": {"attempts", "min_success_rate", "seed", "initial_pose_noise"},
        "collection": {"attempts", "seed", "initial_pose_noise"},
        "task": {"kind", "contract", "max_abnormal_contacts"},
    }.items():
        if not isinstance(config.get(section), dict) or set(config[section]) - fields:
            raise ValueError(f"Missing or invalid {section} configuration")
    for section, fields in {"train": ("num_envs", "iterations", "save_interval"),
                            "evaluation": ("attempts",), "collection": ("attempts",)}.items():
        for key in fields:
            value = config[section][key]
            if type(value) is not int or value <= 0:
                raise ValueError(f"{section}.{key} must be a positive integer")
    rate = config["evaluation"]["min_success_rate"]
    if not isinstance(rate, (float, int)) or not math.isfinite(rate) or not 0 < rate <= 1:
        raise ValueError("evaluation.min_success_rate must be in (0, 1]")
    for section in ("evaluation", "collection"):
        if type(config[section]["seed"]) is not int or config[section]["seed"] < 0:
            raise ValueError(f"{section}.seed must be a nonnegative integer")
        noise = config[section]["initial_pose_noise"]
        if not isinstance(noise, (float, int)) or not math.isfinite(noise) or noise < 0:
            raise ValueError(f"{section}.initial_pose_noise must be finite and nonnegative")
    task = config["task"]
    if task["kind"] not in ("contact_events", "completion_only"):
        raise ValueError("task.kind must be contact_events or completion_only")
    if type(task["max_abnormal_contacts"]) is not int or task["max_abnormal_contacts"] < 0:
        raise ValueError("task.max_abnormal_contacts must be a nonnegative integer")
    return config, path


def manifest_header(backend):
    asset = canonical_g1_asset_metadata()
    return dict(schema="somaforge_motion_terrain_manifest_v1", schema_version=1,
                robot_asset_id="robot.g1.spherehand", robot_asset_sha256=asset["urdf_sha256"],
                robot_asset_bundle_sha256=asset["asset_bundle_sha256"],
                robot_asset_usd_bundle_sha256=asset["usd_bundle_sha256"], kinematics_backend=backend)


def prepare(config_path, *, execute=False):
    """CPU-only adapter for canonical manifests and native edit collections.

    Config paths are repository relative. Paths inside input manifests/indexes
    and plans are relative to the file that declares them.
    """
    config, config_path = load_config(config_path)
    root = somaforge_root()
    source = resolve(config["input"]["path"], root)
    checkpoint = resolve(config["base_checkpoint"], root)
    output = resolve(config["output_dir"], root)
    data = read_json(source)
    if config["input"]["kind"] not in ("motion_manifest", "native_edit_collection"):
        raise ValueError("Unknown input kind")
    entries = data["motion_files"]
    if not entries:
        raise ValueError("Empty reference collection")
    if "total" in data and data["total"] != len(entries):
        raise ValueError("Input collection total disagrees with its actual entries")
    files = {str(source): fingerprint(source), str(checkpoint): fingerprint(checkpoint)}
    terrain_files = {}
    if config["input"]["kind"] == "motion_manifest":
        terrain_files = {t["terrain_id"]: resolve(t["terrain_file"], source.parent) for t in data["terrains"]}
        if len(terrain_files) != len(data["terrains"]):
            raise ValueError("Duplicate terrain IDs")
    contract = None
    if config["task"]["kind"] == "contact_events" and config["task"].get("contract"):
        contract_path = resolve(config["task"]["contract"], root)
        contract = read_json(contract_path)
        if contract.get("schema") != "explicit_action_contact_acceptance_v2" or not contract.get("actions"):
            raise ValueError("Unsupported or empty contact-event intent contract")
        files[str(contract_path)] = fingerprint(contract_path)
    motions, terrains, cases, identities, backends = [], {}, [], set(), set()
    for index, entry in enumerate(entries):
        identity = str(entry.get("motion_name", entry.get("motion_id", index)))
        if identity in identities:
            raise ValueError(f"Duplicate reference identity: {identity}")
        identities.add(identity)
        native = config["input"]["kind"] == "native_edit_collection"
        motion = resolve(entry["motion" if native else "motion_file"], source.parent)
        files[str(motion)] = fingerprint(motion)
        if entry.get("motion_sha256") and entry["motion_sha256"] != files[str(motion)]["sha256"]:
            raise ValueError(f"Reference differs from its declared hash: {motion}")
        if native:
            plan = resolve(entry["plan"], source.parent)
            files[str(plan)] = fingerprint(plan)
            terrain = resolve(read_json(plan)["metadata"]["target_terrain_mesh"], plan.parent)
        else:
            terrain = terrain_files[entry["terrain_id"]]
        files[str(terrain)] = fingerprint(terrain)
        if not native:
            terrain_entry = next(t for t in data["terrains"] if t["terrain_id"] == entry["terrain_id"])
            if terrain_entry.get("terrain_sha256") and terrain_entry["terrain_sha256"] != files[str(terrain)]["sha256"]:
                raise ValueError(f"Terrain differs from its declared hash: {terrain}")
        terrain_key = str(terrain)
        if terrain_key not in terrains:
            terrains[terrain_key] = dict(terrain_id=len(terrains), terrain_file=terrain_key,
                                        terrain_sha256=files[terrain_key]["sha256"])
        with np.load(motion, allow_pickle=False) as z:
            decode_robot_asset_json(z.get("robot_asset_json"), context=str(motion))
            provenance = decode_kinematics_provenance(z.get("kinematics_provenance_json"), context=str(motion))
            frames, fps = len(z["joint_pos"]), float(np.asarray(z["fps"]).item())
            for key in ("joint_pos", "joint_vel", "body_pos_w", "body_quat_w", "body_lin_vel_w", "body_ang_vel_w"):
                if len(z[key]) != frames or not np.isfinite(z[key]).all():
                    raise ValueError(f"Invalid reference {key}: {motion}")
            if frames < 2 or not math.isfinite(fps) or fps <= 0:
                raise ValueError(f"Invalid reference length/rate: {motion}")
            if z["joint_pos"].shape != (frames, 36) or z["joint_vel"].shape != (frames, 35):
                raise ValueError(f"Reference does not have canonical G1 state dimensions: {motion}")
        backends.add(provenance["kinematics_backend"])
        row = dict(motion_id=index, motion_name=identity, motion_file=str(motion),
                   motion_sha256=files[str(motion)]["sha256"], source_file=str(motion),
                   source_sha256=files[str(motion)]["sha256"], terrain_id=terrains[terrain_key]["terrain_id"],
                   weight=float(entry.get("weight", 1.0)), kinematics_schema=provenance["schema"],
                   kinematics_backend=provenance["kinematics_backend"],
                   velocity_derivation=provenance["velocity_derivation"])
        if not math.isfinite(row["weight"]) or row["weight"] <= 0:
            raise ValueError("Reference sampling weights must be finite and positive")
        case_contract = contract
        if config["task"]["kind"] == "contact_events":
            if entry.get("task_contract"):
                path = resolve(entry["task_contract"], source.parent)
                files[str(path)] = fingerprint(path)
                case_contract = read_json(path)
            if (not case_contract or case_contract.get("schema") != "explicit_action_contact_acceptance_v2"
                    or not case_contract.get("actions")):
                raise ValueError(f"Missing/invalid explicit task contract: {identity}")
        case = dict(key=f"motion_{index:06d}", identity=identity, reference=row, frames=frames, fps=fps,
                    terrain=terrains[terrain_key], task=config["task"], contract=case_contract)
        if case_contract is not None and config["task"]["kind"] == "contact_events":
            if case_contract["frame_count"] != frames or not np.isclose(case_contract["fps"], fps):
                raise ValueError(f"Task clock does not match full reference: {identity}")
            # Only the actual geometry catalog is used; old contact labels and
            # their acceptance flags are never treated as new execution truth.
            labels = resolve(entry["contacts" if native else "contact_catalog_file"], source.parent)
            files[str(labels)] = fingerprint(labels)
            with np.load(labels, allow_pickle=False) as z:
                semantics = json.loads(z["contact_semantics_json"].item())
            case["expected_surface_catalog"] = semantics["scene"]["surface_catalog"]
        motions.append(row)
        cases.append(case)
    if len(backends) != 1:
        raise ValueError("One joint reference manifest must use one kinematics backend")
    if config["train"]["num_envs"] < 3 * len(motions):
        raise ValueError("Joint trainer uses three start probes per motion; increase train.num_envs")
    manifest = dict(manifest_header(backends.pop()), motion_files=motions, terrains=list(terrains.values()),
                    purpose="kinematic references for joint WBT refinement; not executed demonstrations")
    # Pin implementation as well as input files; do not resume across silently
    # changed extraction/acceptance semantics.
    dependencies = [Path(__file__), root / "scripts/train_motion_edit_policy_finetune.py",
                    root / "scripts/run_trajectory_refinement.py",
                    root / "src/holosoma/holosoma/eval_agent.py",
                    root / "src/holosoma/holosoma/agents/callbacks/recording.py",
                    root / "packages/motion_edit/motion_edit/generation/event_acceptance.py"]
    dependencies += [Path(__file__).with_name(name + ".py") for name in
                     ("rollout_dataset", "contact_face_selection", "contact_labels", "newton_contacts",
                      "newton_support", "newton_contact_data", "newton_runtime_compat", "support_semantics")]
    for path in dependencies:
        files[str(path.resolve())] = fingerprint(path)
    plan = dict(schema=SCHEMA, config=config, base_checkpoint=str(checkpoint), output_dir=str(output),
                files=list(files.values()), manifest=manifest, cases=cases,
                max_episode_length_s=max(c["frames"] / c["fps"] for c in cases) + 2,
                gpu_validation="not_run", prepared_reference_count=len(cases))
    if execute:
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / "plan.json", plan, immutable=True)
        write_json(output / "references.json", manifest, immutable=True)
        for case in cases:
            single = dict(manifest, motion_files=[dict(case["reference"], motion_id=0)], terrains=[case["terrain"]])
            write_json(output / "references" / f"{case['key']}.json", single, immutable=True)
    return plan


def load_plan(config_path):
    config, _ = load_config(config_path)
    output = resolve(config["output_dir"], somaforge_root())
    plan = read_json(output / "plan.json")
    if plan["config"] != config:
        raise ValueError("Configuration changed after preparation; use a new output directory")
    verify_files(plan["files"])
    if read_json(output / "references.json") != plan["manifest"]:
        raise ValueError("Prepared joint manifest changed")
    for case in plan["cases"]:
        expected = dict(plan["manifest"], motion_files=[dict(case["reference"], motion_id=0)], terrains=[case["terrain"]])
        if read_json(output / "references" / f"{case['key']}.json") != expected:
            raise ValueError("Prepared per-motion manifest changed")
    return plan


def checkpoint_info(path):
    """Read the local, user-selected checkpoint on CPU; never initialize CUDA."""
    import torch
    from .robot_assets import validate_g1_asset_metadata
    value = torch.load(path, map_location="cpu", weights_only=False)
    validate_g1_asset_metadata(value.get("robot_asset"), context=str(path))
    config = value["experiment_config"]
    if not config["robot"]["asset"]["enable_self_collisions"]:
        raise ValueError("Base checkpoint must already enable self collisions")
    if config["simulator"]["config"]["name"] != "isaaclab3_newton":
        raise ValueError("This backend requires an existing Newton WBT checkpoint")
    return dict(iteration=int(value["iter"]), config=config)


def train_command(plan, checkpoint, iterations, directory, *, device, visualizer, headless):
    cfg = plan["config"]["train"]
    cmd = [sys.executable, str(somaforge_root() / "scripts/train_motion_edit_policy_finetune.py"),
           "--checkpoint", str(checkpoint), "--motion-manifest", str(Path(plan["output_dir"]) / "references.json"),
           "--output-dir", str(directory), "--project", "TrajectoryRefinement", "--name", "joint",
           "--num-envs", str(cfg["num_envs"]), "--iterations", str(iterations),
           "--save-interval", str(cfg["save_interval"]),
           "--max-episode-length-s", str(plan["max_episode_length_s"])]
    return cmd + launcher_flags(device, visualizer, headless)


def launcher_flags(device, visualizer, headless):
    flags = ["--device", device]
    if headless:
        flags += ["--headless"]
    elif visualizer:
        flags += ["--visualizer", visualizer]
    return flags


def recording_command(plan, case, checkpoint, recording, *, seed, noise, device, visualizer, headless):
    manifest = str(Path(plan["output_dir"]) / "references" / f"{case['key']}.json")
    prefix = "--command.setup-terms.motion-command.params.motion-config."
    cmd = [sys.executable, "-m", "holosoma.eval_agent", "--checkpoint", str(checkpoint),
           "--num-envs", "1", "--max-steps", str(case["frames"] + 10),
           "--training.seed", str(seed), "--export-onnx", "False",
           "--recording.config.enabled", "True", "--recording.config.record-initial-state", "True",
           "--recording.config.env-id", "0", "--recording.config.output-path", str(recording),
           "--acceptance.config.enabled", "False", "--push.config.enabled", "False", "--payload.config.enabled", "False",
           "--terrain.terrain-term.motion-matched-manifest", manifest,
           "--video.enabled", "False", "--randomize-tiles", "False", "--xy-offset-range", "0.0"]
    values = {"motion-manifest": manifest, "reset-sampler": "uniform",
              "start-at-timestep-zero-prob": "1.0", "freeze-at-timestep-zero-prob": "0.0",
              "noise-to-initial-pose.overall-noise-scale": str(noise),
              "use-start-probe-envs": "False", "use-group-probe-envs": "False",
              "chain-motion-segments": "False", "hold-at-motion-end-in-eval": "False",
              "local-motion-segment-reference": "False", "canonicalize-motion-order-on-load": "True"}
    for key, value in values.items():
        cmd += [prefix + key, value]
    return cmd + launcher_flags(device, visualizer, headless)


def run_command(command, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    write_json(directory / "command.json", command, immutable=True)
    print(shlex.join(command), flush=True)
    # argv, never a shell; launching is only possible in an explicit execute stage.
    with (directory / "process.log").open("x") as log:
        result = subprocess.run(command, cwd=somaforge_root(), stdout=log, stderr=subprocess.STDOUT, check=False)
    write_json(directory / "process_result.json", dict(returncode=result.returncode), immutable=True)
    if result.returncode:
        raise RuntimeError(f"Process failed ({result.returncode}); see {directory / 'process.log'}")


def train(plan, *, checkpoint=None, execute=False, **launcher):
    root = Path(plan["output_dir"])
    base = Path(plan["base_checkpoint"])
    checkpoint = Path(checkpoint).resolve() if checkpoint else base
    base_info = checkpoint_info(base)
    info = checkpoint_info(checkpoint)
    if info["iteration"] < base_info["iteration"]:
        raise ValueError("Resume checkpoint predates this workflow's base iteration")
    if checkpoint != base:
        if not checkpoint.is_relative_to(root / "training"):
            raise ValueError("Resume checkpoint must belong to this workflow's training directory")
        loaded_manifest = info["config"]["command"]["setup_terms"]["motion_command"]["params"]["motion_config"]["motion_manifest"]
        if Path(loaded_manifest).resolve() != root / "references.json":
            raise ValueError("Resume checkpoint uses a different reference manifest")
    remaining = base_info["iteration"] + plan["config"]["train"]["iterations"] - info["iteration"]
    if remaining <= 0:
        raise ValueError("Configured joint training budget is already exhausted")
    directory = root / "training" / uuid.uuid4().hex
    command = train_command(plan, checkpoint, remaining, directory / "models", **launcher)
    if not execute:
        return dict(command=command, remaining_iterations=remaining, launches=0)
    run_command(command, directory)
    models = list((directory / "models").rglob("model_*.pt"))
    if not models:
        raise ValueError("Training exited without a checkpoint")
    final = max(models, key=lambda p: int(p.stem.split("_")[-1]))
    if checkpoint_info(final)["iteration"] != info["iteration"] + remaining:
        raise ValueError("Training exited before its requested iteration budget was completed")
    receipt = dict(checkpoint=fingerprint(final), source_checkpoint=fingerprint(checkpoint),
                   plan_sha256=sha256_file(root / "plan.json"), iterations=remaining)
    write_json(directory / "completed.json", receipt, immutable=True)
    return receipt


def policy_run(plan, checkpoint):
    checkpoint = Path(checkpoint).resolve()
    info = checkpoint_info(checkpoint)
    manifest = info["config"]["command"]["setup_terms"]["motion_command"]["params"]["motion_config"]["motion_manifest"]
    if Path(manifest).resolve() != Path(plan["output_dir"]) / "references.json":
        raise ValueError("Evaluation checkpoint must be trained on this prepared joint manifest")
    policy = fingerprint(checkpoint)
    return policy, Path(plan["output_dir"]) / "policies" / policy["sha256"]


def completed_attempt(directory, context):
    if not directory.exists():
        return None
    for report_path in sorted(directory.glob("*/report.json")):
        report = read_json(report_path)
        if report.get("context") != context:
            raise ValueError("Attempt provenance differs from the requested policy/reference/seed")
        verify_files(report["artifacts"])
        # Infrastructure errors remain retriable. A fully observed task failure
        # counts as a failed trial and must not be retried until it passes.
        if report["status"] in ("passed", "failed"):
            return report
    return None


def evaluate_or_collect(plan, stage, checkpoint, *, execute=False, **launcher):
    from .rollout_dataset import inspect_recording
    policy, root = policy_run(plan, checkpoint)
    cfg = plan["config"]["evaluation" if stage == "evaluate" else "collection"]
    plan_sha = sha256_file(Path(plan["output_dir"]) / "plan.json")
    cases = plan["cases"]
    if stage == "collect":
        summary = read_json(root / "evaluation_summary.json")
        if summary["checkpoint"] != policy or summary["plan_sha256"] != plan_sha:
            raise ValueError("Evaluation does not belong to this frozen policy/plan")
        verify_files(summary["artifacts"])
        eligible = {row["key"] for row in summary["motions"] if row["eligible"]}
        cases = [c for c in cases if c["key"] in eligible]
        if not cases:
            raise ValueError("No motion has passed this policy's per-motion evaluation gate")
    rows, commands, reports = [], [], []
    for case in cases:
        attempts = []
        for trial in range(cfg["attempts"]):
            seed = cfg["seed"] + trial
            context = dict(checkpoint=policy, plan_sha256=plan_sha, motion=case["reference"]["motion_sha256"],
                           key=case["key"], stage=stage, trial=trial, seed=seed, noise=cfg["initial_pose_noise"])
            slot = root / stage / case["key"] / f"trial_{trial:04d}"
            report = completed_attempt(slot, context)
            if report is None:
                directory = slot / uuid.uuid4().hex
                recording = directory / "recording.npz"
                command = recording_command(plan, case, checkpoint, recording, seed=seed,
                                            noise=cfg["initial_pose_noise"], **launcher)
                if not execute:
                    commands.append(command)
                    continue
                try:
                    verify_files([policy])
                    run_command(command, directory)
                    verify_files([policy])
                    report = inspect_recording(recording, case)
                except (ValueError, KeyError, RuntimeError, OSError) as exc:
                    report = dict(status="unknown", execution_passed=False, task_passed=None, reason=str(exc))
                report.update(context=context, recording=str(recording), artifacts=[])
                if recording.is_file():
                    report["artifacts"].append(fingerprint(recording))
                write_json(directory / "report.json", report, immutable=True)
                report["report_path"] = str(directory / "report.json")
                if report["status"] == "unknown":
                    raise RuntimeError(f"Unknown execution evidence; stopped queue. Inspect {directory / 'report.json'}")
            attempts.append(report)
            if report.get("report_path"):
                reports.append(fingerprint(report["report_path"]))
            else:
                # Reused reports are found by their immutable content/context.
                matches = [p for p in slot.glob("*/report.json") if read_json(p) == report]
                reports.append(fingerprint(matches[0]))
            reports.extend(report["artifacts"])
        passed = sum(a["status"] == "passed" for a in attempts)
        completed = len(attempts) == cfg["attempts"] and all(a["status"] != "unknown" for a in attempts)
        rows.append(dict(key=case["key"], identity=case["identity"], passed=passed, requested=cfg["attempts"],
                         unknown=sum(a["status"] == "unknown" for a in attempts), complete=completed,
                         success_rate=passed / cfg["attempts"],
                         eligible=completed and passed / cfg["attempts"] >= plan["config"]["evaluation"]["min_success_rate"]))
    result = dict(checkpoint=policy, plan_sha256=plan_sha, motions=rows, artifacts=reports,
                  omitted_motion_count=len(plan["cases"]) - len(cases), pending_commands=commands,
                  task_kind=plan["config"]["task"]["kind"],
                  scope=("complete native execution and configured contact-event checks; no undeclared support guarantee"
                         if plan["config"]["task"]["kind"] == "contact_events" else
                         "complete native execution only; task intent and support requirements unverified"))
    if execute:
        write_json(root / ("evaluation_summary.json" if stage == "evaluate" else "collection_summary.json"), result)
    return result


def export_dataset(plan, checkpoint, *, execute=False):
    from .rollout_dataset import export_recording
    policy, root = policy_run(plan, checkpoint)
    summary = read_json(root / "collection_summary.json")
    if summary["checkpoint"] != policy or summary["plan_sha256"] != sha256_file(Path(plan["output_dir"]) / "plan.json"):
        raise ValueError("Collection belongs to another plan/checkpoint")
    verify_files(summary["artifacts"])
    cases = {c["key"]: c for c in plan["cases"]}
    entries = []
    for artifact in summary["artifacts"]:
        path = Path(artifact["path"])
        if path.name != "report.json":
            continue
        report = read_json(path)
        if report["status"] != "passed":
            continue
        case = cases[report["context"]["key"]]
        destination = root / "dataset" / case["key"] / f"trial_{report['context']['trial']:04d}"
        if execute:
            export_recording(Path(report["recording"]), case, destination, report, policy)
            motion = destination / "motion.npz"
            entries.append(dict(motion_id=len(entries), motion_name=f"{case['identity']}/trial_{report['context']['trial']}",
                                motion_file=str(motion), motion_sha256=sha256_file(motion),
                                terrain_id=case["terrain"]["terrain_id"], weight=1.0,
                                source_file=report["recording"], source_sha256=sha256_file(Path(report["recording"])),
                                reference_motion_file=case["reference"]["motion_file"],
                                reference_motion_sha256=case["reference"]["motion_sha256"],
                                observations_file=str(destination / "observations.npz"),
                                observations_sha256=sha256_file(destination / "observations.npz"),
                                kinematics_backend="isaaclab3_newton_rollout", velocity_derivation="newton_simulation_state"))
        else:
            entries.append(dict(reference=case["identity"], recording=report["recording"], destination=str(destination)))
    if not entries:
        raise ValueError("No accepted collection trials to export")
    result = dict(manifest_header("isaaclab3_newton_rollout"), motion_files=entries,
                  terrains=plan["manifest"]["terrains"], checkpoint=policy,
                  source_collection=fingerprint(root / "collection_summary.json"),
                  observation_schema="somaforge_executed_contact_observations_v1",
                  downstream_contract="native solve observations; not fixed-q contact labels",
                  scope=summary["scope"])
    if execute:
        write_json(root / "dataset" / "manifest.json", result, immutable=True)
    return result


def status(plan):
    root = Path(plan["output_dir"])
    return dict(reference_count=len(plan["cases"]), terrain_count=len(plan["manifest"]["terrains"]),
                training_runs=[str(p) for p in sorted((root / "training").glob("*/completed.json"))],
                evaluations=[str(p) for p in sorted((root / "policies").glob("*/evaluation_summary.json"))],
                datasets=[str(p) for p in sorted((root / "policies").glob("*/dataset/manifest.json"))],
                gpu_validation=plan["gpu_validation"])
