"""Prepare independent source-prefix plans from an existing edit collection.

Only authored plans and their native source evidence are reused. Edited poses,
old acceptance flags and cached generation results never become new outputs.
"""
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from somaforge_core.loaded_material_motion import DEFAULT_MATERIAL_RESIDUAL_SCALE_M

from motion_edit.contact.plans import read_contact_edit_plan
from .contract import validate_generation_metadata
from .source_prefix_reference import (
    configure_plan_prefix, load_prefix_configuration, prefix_implementation_fingerprints,
)


def prepare_prefix_collection(collection, output, config_path, *, resume=False,
                              material_motion_residual_scale_m=DEFAULT_MATERIAL_RESIDUAL_SCALE_M):
    from somaforge_core.robot_assets import decode_robot_asset_json
    from somaforge_core.motion_schema import decode_kinematics_provenance
    from somaforge_core.newton_contact_data import load_contact_labels
    from .loaded_material_reference import read_loaded_reference

    collection, output = Path(collection).resolve(), Path(output).resolve()
    config, provenance = load_prefix_configuration(config_path)
    data = json.loads(collection.read_text())
    if "plans" in data:
        entries = [row["plan_path"] for row in data["plans"]]
    else:
        entries = [row["plan"] for row in data["motion_files"]]
    if not entries:
        raise ValueError("Source-prefix preparation requires a nonempty plan collection")
    if not np.isfinite(material_motion_residual_scale_m) or material_motion_residual_scale_m <= 0:
        raise ValueError("Material residual scale must be finite and positive")
    files, prepared, sources, pinned_layers = {}, [], {}, set()

    def pin(path):
        path = Path(path).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if str(path) in files and files[str(path)] != digest:
            raise ValueError("Source-prefix input changed while preparing plans")
        files[str(path)] = digest
        return path

    pin(collection)
    configured = pin(config_path)
    if files[str(configured)] != provenance['sha256']:
        raise ValueError("Source-prefix configuration changed while preparing plans")
    for value in entries:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = collection.parent/path
        path = pin(path)
        plan = read_contact_edit_plan(path)
        validate_generation_metadata(plan.metadata)
        if plan.status not in {"validated", "locked"}:
            raise ValueError("Source-prefix preparation requires validated or locked plans")
        source = Path(plan.source_motion_path).expanduser()
        if not source.is_absolute():
            source = path.parent/source
        source = pin(source)
        layer = Path(plan.source_contact_layer).expanduser()
        if not layer.is_absolute():
            layer = path.parent/layer
        layer = layer.resolve()
        if not layer.is_dir():
            raise FileNotFoundError(f"Source contact layer is missing: {layer}")
        if layer not in pinned_layers:
            for item in sorted(layer.rglob('*')):
                if item.is_file():
                    pin(item)
            pinned_layers.add(layer)
        if source not in sources:
            with np.load(source, allow_pickle=False) as z:
                decode_robot_asset_json(z.get("robot_asset_json"), context=str(source))
                decode_kinematics_provenance(z.get("kinematics_provenance_json"), context=str(source))
            sources[source] = None
        metadata = dict(plan.metadata, source_prefix_parent_plan=dict(path=str(path), sha256=files[str(path)]))
        labels = metadata.get("newton_contact_file")
        if labels:
            label = Path(labels).expanduser()
            if not label.is_absolute():
                label = path.parent/label
            label = pin(label)
            metadata["newton_contact_file"] = str(label)
            if sources[source] != str(label):
                load_contact_labels(source, label)
                sources[source] = str(label)
        # Existing regeneration collections keep observed support in a native
        # source bundle. Carry it into the formal single/batch generator too.
        evidence = metadata.get("source_loaded_material_reference")
        bundle = {k: source.parent/name for k, name in
                  (("sites", "loaded_sites.npz"), ("observations", "observations.npz"),
                   ("phases", "keep_phases.json"))}
        if evidence is None and any(p.exists() for p in bundle.values()):
            if not all(p.is_file() for p in bundle.values()):
                raise ValueError("Incomplete native loaded-material source bundle")
            evidence = dict({k: str(p) for k, p in bundle.items()},
                            sha256={k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in bundle.items()},
                            residual_scale_m=material_motion_residual_scale_m)
        if evidence is not None:
            evidence = dict(evidence, sha256=dict(evidence['sha256']))
            for k in ("sites", "observations", "phases"):
                p = Path(evidence[k]).expanduser()
                if not p.is_absolute():
                    p = path.parent/p
                p = pin(p)
                if files[str(p)] != evidence["sha256"][k]:
                    raise ValueError("Source loaded-material evidence hash changed")
                evidence[k] = str(p)
            paths = tuple(evidence[k] for k in ("sites", "observations", "phases"))
            cache_key = (source, *paths)
            if cache_key not in sources:
                read_loaded_reference(source, *paths)
                sources[cache_key] = True
            metadata["source_loaded_material_reference"] = evidence
        for key in ("source_terrain_mesh", "target_terrain_mesh", "event_phase_file"):
            if metadata.get(key):
                p = Path(metadata[key]).expanduser()
                if not p.is_absolute():
                    p = path.parent/p
                metadata[key] = str(pin(p))
        plan = configure_plan_prefix(replace(plan, source_motion_path=str(source),
                                            source_contact_layer=str(layer), metadata=metadata),
                                     config, provenance)
        if Path(plan.plan_id).name != plan.plan_id or plan.plan_id in {"", ".", ".."}:
            raise ValueError("Plan identity must be a safe filename")
        prepared.append(plan)
    if len({p.plan_id for p in prepared}) != len(prepared):
        raise ValueError("Source-prefix collection has duplicate output identities")
    payloads = {f"plans/{p.plan_id}.json": json.dumps(p.to_dict(), sort_keys=True,
                 ensure_ascii=False, allow_nan=False).encode() for p in prepared}
    signature = dict(schema="source_prefix_collection_preparation_v1", inputs=files,
        source_prefix_reference=config, implementation=prefix_implementation_fingerprints(),
        plan_sha256={name: hashlib.sha256(raw).hexdigest() for name, raw in payloads.items()})
    manifest = dict(schema="contact_edit_plan_manifest_v1", plans=[dict(plan_path=name) for name in payloads],
        source_prefix_reference=config, training_ready=False, generation_started=False,
        reference_role="plans over unchanged native source evidence; no edited poses reused")
    if output.exists():
        if not resume:
            raise FileExistsError("Output exists; use --resume for identical prepared inputs")
        if json.loads((output/"preparation.json").read_text()) != signature:
            raise ValueError("Prepared source-prefix inputs changed; choose a new output version")
        if json.loads((output/"manifest.json").read_text()) != manifest:
            raise ValueError("Prepared source-prefix manifest changed")
        for name, raw in payloads.items():
            if (output/name).read_bytes() != raw:
                raise ValueError("Prepared source-prefix plan changed")
        return manifest
    output.mkdir(parents=True, exist_ok=False)
    (output/"plans").mkdir()
    for name, raw in payloads.items():
        with (output/name).open("xb") as stream:
            stream.write(raw)
    for name, value in (("preparation.json", signature), ("manifest.json", manifest),
                        ("status.json", dict(stage="prepared", total=len(prepared), completed=0,
                                             gpu_started=False, training_ready=False))):
        with (output/name).open("x") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
    return manifest
