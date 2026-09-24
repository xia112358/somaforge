"""Fixed-model contact gradient audit, called before any optimizer exists."""
import hashlib
import importlib.util
import json
from pathlib import Path

import torch


def write_witness_manifest(cfg):
    from somaforge_core.robot_assets import decode_robot_asset_json
    from somaforge_core.newton_contacts import SCHEMA
    from somaforge_core.contact_face_selection import FACE_POLICY
    checkpoint = torch.load(cfg.initial_position_checkpoint, map_location='cpu', weights_only=False)
    asset = checkpoint['robot_asset_json']
    decode_robot_asset_json(asset, context='frozen contact audit')
    samples = torch.load(cfg.data_cache, map_location='cpu', weights_only=False)['samples']
    scenes = {}
    for folder in sorted((cfg.output/'newton_workers').glob('h*')):
        model_file, binding_file = folder/'model.json', folder/'binding.json'
        model = json.loads(model_file.read_text())
        scenes[folder.name] = {'model_fingerprint': model['model_fingerprint'],
            'model': str(model_file.resolve()), 'binding': str(binding_file.resolve()),
            'model_sha256': hashlib.sha256(model_file.read_bytes()).hexdigest(),
            'binding_sha256': hashlib.sha256(binding_file.read_bytes()).hexdigest()}
    witnesses = []
    for path in sorted(cfg.output.glob('witnesses_*.pt')):
        payload = torch.load(path, map_location='cpu', weights_only=False)
        indices = payload['sample_indices'].tolist()
        scene_names = [f"h{float(samples[i]['height']):.8f}" for i in indices]
        if not all(name in scenes for name in scene_names): raise ValueError('Unknown witness scene')
        witnesses.append({'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'sample_indices': indices, 'scene_by_batch_sample': scene_names})
    (cfg.output/'witness_manifest.json').write_text(json.dumps({
        'schema': 'frozen_actual_newton_gradient_witness_manifest_v1',
        'robot_asset_json': asset, 'contact_semantics': SCHEMA, 'face_selection': FACE_POLICY,
        'sampling': 'static query at saved raw predicted q; no integration; same real witnesses reused across derivative variants',
        'indexing': 'pairs.sample indexes the saved q batch; pairs.worldid is the reused solver slot within its scene',
        'scenes': scenes, 'witnesses': witnesses}, indent=2))


def audit(model, cfg, inputs, validation, labels_for, objective):
    import climb00_pipeline.contact_regions as regions

    model.eval()
    original_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    original_mode = model.execution_plan_gradients
    new_objective = regions.unified_region_objective
    archive = Path('tmp/full1000_static_contact_20260924/code_before/packages/climb00_pipeline/climb00_pipeline/contact_regions.py')
    spec = importlib.util.spec_from_file_location('climb00_pipeline._archived_contact_regions', archive)
    old_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_module)

    count = min(cfg.static_audit_samples, len(validation))
    selected = torch.linspace(0, len(validation)-1, count, device=validation.device).long()
    indices = validation[selected]
    batches = [('reference_validation', indices, {k: v[indices] for k, v in inputs.items()})]
    if cfg.static_audit_pool is not None:
        # Pool storage is an observation artifact, not an independent robot
        # checkpoint. Require its matching, asset-validated model checkpoint.
        if cfg.initial_position_checkpoint is None or cfg.static_audit_pool.parent.resolve() != cfg.initial_position_checkpoint.parent.resolve():
            raise ValueError('Audit pool must accompany the loaded checkpoint')
        state = torch.load(cfg.static_audit_pool, map_location=validation.device, weights_only=False)
        checkpoint = torch.load(cfg.initial_position_checkpoint, map_location='cpu', weights_only=False)
        if state['schema'] != 'persistent_parallel_rollout_training_state_v1' or state['step'] != checkpoint['step']:
            raise ValueError('Pool/checkpoint step mismatch')
        pool = state['pool']
        slots = (pool['age'] > 0).nonzero().flatten()[:cfg.static_audit_samples]
        if not len(slots): raise ValueError('Audit pool contains no generated inputs')
        batches.append(('generated_pool_states', pool['indices'][slots],
            {k: v[slots] for k, v in pool['observation'].items()}))

    named = [(name, p) for name, p in model.named_parameters() if p.requires_grad]
    params = [p for _, p in named]
    groups = {
        'all_parameters': tuple(range(len(named))),
        'shared_backbone': tuple(i for i, (n, _) in enumerate(named) if n.startswith(('shared.', 'terrain_reasoning.', 'part_encoder.', 'global_encoder.', 'norm.'))),
        'pose_head': tuple(i for i, (n, _) in enumerate(named) if n.startswith('pose_head.')),
        'role_head': tuple(i for i, (n, _) in enumerate(named) if n.startswith('role_head.')),
        'location_heads': tuple(i for i, (n, _) in enumerate(named) if n.startswith(('location_key.', 'location_query.'))),
        'region_head': tuple(i for i, (n, _) in enumerate(named) if n.startswith(('region_head.', 'region_prior'))),
        'geometry_encoder': tuple(i for i, (n, _) in enumerate(named) if n.startswith('region_geometry_encoder.')),
    }

    def gradient(value, q):
        raw = torch.autograd.grad(value.mean(), params+[q], retain_graph=True, allow_unused=True)
        values = [torch.zeros_like(p) if g is None else g.detach() for p, g in zip(params, raw[:-1])]
        norms = {name: float(sum((values[i].double().square().sum() for i in ids), q.new_zeros((), dtype=torch.float64)).sqrt())
            for name, ids in groups.items()}
        shared = torch.cat([values[i].flatten() for i in groups['shared_backbone']]).cpu()
        pose = torch.zeros_like(q) if raw[-1] is None else raw[-1].detach()
        return norms, shared, pose.cpu()

    def cosine(a, b):
        denominator = a.double().norm()*b.double().norm()
        return None if denominator == 0 else float((a.double()*b.double()).sum()/denominator)

    records = []
    try:
        for source, ids, observation in batches:
            reference = None
            reference_pairs = None
            for mode, enabled, function in (
                ('legacy', False, old_module.unified_region_objective),
                ('plan_gradient_only', True, old_module.unified_region_objective),
                ('full_static', True, new_objective),
            ):
                model.execution_plan_gradients = enabled
                regions.unified_region_objective = function
                prediction = model(**observation)
                if reference is None:
                    reference = {k: getattr(prediction, k).detach().clone() for k in ('qpos', 'conditioned_contact', 'conditioned_points_local', 'planned_regions')}
                for name, value in reference.items():
                    torch.testing.assert_close(getattr(prediction, name), value, rtol=0, atol=0)
                loss, metrics, queried = objective(prediction, observation, ids,
                    labels_for(observation, ids, recursive=source == 'generated_pool_states'))
                if reference_pairs is None:
                    reference_pairs = {k: v.detach().clone() for k, v in queried[0].pair.items()}
                    def cpu(value):
                        if isinstance(value, torch.Tensor): return value.detach().cpu()
                        if isinstance(value, dict): return {k: cpu(v) for k, v in value.items()}
                        if isinstance(value, (list, tuple)): return type(value)(cpu(v) for v in value)
                        return value
                    torch.save({'schema': 'frozen_actual_newton_gradient_witnesses_v1',
                        'sample_indices': ids.cpu(), 'q_world': prediction.qpos.detach().cpu(),
                        'q_local': queried[0].q.detach().cpu(), 'observations': cpu(observation),
                        'world_frame': cpu(queried[0].world_frame), 'newton': cpu(queried[1])},
                        cfg.output/f'witnesses_{source}.pt')
                else:
                    for key, value in reference_pairs.items():
                        torch.testing.assert_close(queried[0].pair[key], value, rtol=0, atol=0, equal_nan=True)
                components = {
                    'planner': metrics['audit_planner'], 'execution': metrics['unified_region_loss'],
                    'imitation': metrics['audit_imitation'], 'layout': metrics['audit_layout'],
                    'joint_limits': metrics['audit_safety'],
                }
                torch.testing.assert_close(sum(components.values()), loss)
                terms = dict(components, total=loss)
                if mode == 'full_static':
                    terms.update(attraction=metrics['unified_attraction_component'],
                        separation=metrics['unified_separation_component'])
                    torch.testing.assert_close(terms['attraction']+terms['separation'], terms['execution'])
                details, vectors, qvectors = {}, {}, {}
                for name, term in terms.items():
                    norms, vectors[name], qvectors[name] = gradient(term, prediction.qpos)
                    details[name] = {'mean_loss': float(term.detach().mean()), 'parameter_gradient_norms': norms,
                        'raw_q_gradient_norm': float(qvectors[name].norm())}
                additive = sum(vectors[name] for name in components)
                torch.testing.assert_close(additive, vectors['total'], atol=2e-4, rtol=2e-4)
                pairs = [('planner', 'execution'), ('planner', 'imitation'), ('execution', 'imitation'), ('execution', 'layout')]
                if mode == 'full_static': pairs.append(('attraction', 'separation'))
                conflicts = {f'{a}__{b}': {'shared_backbone_cosine': cosine(vectors[a], vectors[b]),
                    'raw_q_cosine': cosine(qvectors[a], qvectors[b])} for a, b in pairs}
                total_norm = details['total']['parameter_gradient_norms']['all_parameters']
                record = {'source': source, 'mode': mode, 'sample_indices': ids.cpu().tolist(),
                    'samples': len(ids), 'forward_exact': True, 'components': details, 'gradient_cosines': conflicts,
                    'clip_10_scale_if_training': min(1., 10./max(total_norm, 1e-12)),
                    'valid_gradient_samples': int(metrics['region_gradient_valid'].sum()),
                    'newton_pairs': len(queried[0].pair['dist']),
                    'plan_exact': float(metrics['plan_exact'].mean()),
                    'region_realized': float(metrics['region_plan_realized'].mean()),
                    'mean_max_penetration_cm': float(metrics['penetration_cm'].detach().mean())}
                records.append(record)
                print(json.dumps({'static_gradient_audit': source, 'mode': mode, 'samples': len(ids),
                    'execution_loss': details['execution']['mean_loss'], 'total_gradient_norm': total_norm}), flush=True)
                del prediction, loss, metrics, queried, terms, components, vectors, qvectors
    finally:
        regions.unified_region_objective = new_objective
        model.execution_plan_gradients = original_mode
    for name, value in model.state_dict().items():
        torch.testing.assert_close(value.cpu(), original_state[name], rtol=0, atol=0)
    assert all(p.grad is None for p in model.parameters())
    report = {'schema': 'frozen_contact_gradient_audit_v1', 'parameter_updates': 0,
        'optimizer_constructed': False, 'weights_bitwise_unchanged': True,
        'source_checkpoint': str(cfg.initial_position_checkpoint),
        'source_checkpoint_sha256': hashlib.sha256(cfg.initial_position_checkpoint.read_bytes()).hexdigest(),
        'old_objective_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'identical_raw_newton_pairs_across_variants': True,
        'scope': 'Deterministic fixed batches; one fresh actual Newton query per pose batch, frozen across variants only after bitwise q/scene equality. Gradients before clipping; no training or quality-improvement claim. Raw q norms mix coordinate units.',
        'records': records}
    (cfg.output/'static_gradient_audit.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    write_witness_manifest(cfg)
    print(json.dumps({'static_gradient_audit_complete': True, 'parameter_updates': 0}), flush=True)
