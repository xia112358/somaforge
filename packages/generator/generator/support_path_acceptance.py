"""Bind whole-demonstration-path acceptance to cached predictor samples.

This certifies recorded reference paths, never an unobserved predicted path.
Legacy manifests remain explicitly uncertified; a declared certificate fails
closed on stale evidence, rejected events, or changed frame boundaries.
"""
import hashlib
import json
from pathlib import Path

SCHEMA = 'predictor_event_contact_evidence_v3'


def file_evidence(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def validate_support_paths(manifest_path, samples):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    declarations = manifest.get('support_path_acceptance')
    if declarations is None:
        return dict(status='legacy_unchecked', scope='no_whole_path_certificate')
    if not declarations:
        raise ValueError('Empty support-path certificate declaration')
    accepted = set()
    verified = []
    for declaration in declarations:
        path = Path(declaration['path'])
        if not path.is_absolute():
            path = manifest_path.parent / path
        if file_evidence(path)['sha256'] != declaration['sha256']:
            raise ValueError('Stale support-path certificate')
        certificate = json.loads(path.read_text())
        if certificate.get('schema') != SCHEMA:
            raise ValueError('Unknown support-path acceptance schema')
        from somaforge_core.support_semantics import SUPPORT_ASSESSMENT_SCHEMA
        if certificate.get('support_assessment_schema') != SUPPORT_ASSESSMENT_SCHEMA:
            raise ValueError('Missing unified support assessment schema; re-materialize labels')
        for evidence in certificate['evidence'].values():
            if file_evidence(evidence['path'])['sha256'] != evidence['sha256']:
                raise ValueError('Stale support-path evidence')
        motion_id = int(declaration['motion_id'])
        entry = manifest['motion_files'][motion_id]
        for field, evidence_key in (('motion_file','motion'), ('newton_contact_file','labels')):
            candidate = Path(entry[field])
            if not candidate.is_absolute(): candidate = manifest_path.parent / candidate
            if file_evidence(candidate)['sha256'] != certificate['evidence'][evidence_key]['sha256']:
                raise ValueError('Certificate does not belong to manifest motion/contact entry')
        observation = entry.get('support_observations_file')
        if observation is not None:
            observation_path = Path(observation)
            if not observation_path.is_absolute(): observation_path = manifest_path.parent / observation_path
            evidence = certificate['evidence'].get('support_observations', {})
            digest = file_evidence(observation_path)['sha256']
            if digest != evidence.get('sha256') or digest != entry.get('support_observations_sha256'):
                raise ValueError('Support observations do not belong to the path certificate')
        for row in certificate['segments']:
            if row['accepted']:
                key = (motion_id, int(row['start_frame']), int(row['end_frame']))
                if key in accepted:
                    raise ValueError('Duplicate certified sample boundary')
                accepted.add(key)
        event_path = Path(entry['event_segments_file'])
        if not event_path.is_absolute(): event_path = manifest_path.parent / event_path
        if file_evidence(event_path)['sha256'] != entry['event_segments_sha256']:
            raise ValueError('Stale accepted event table')
        for line in event_path.read_text().splitlines():
            if line.strip():
                event = json.loads(line)
                key = (motion_id,int(event['start_frame']),int(event['end_frame']))
                if key not in accepted:
                    raise ValueError('Manifest event includes a rejected or uncertified path')
        verified.append(str(path.resolve()))
    for sample in samples:
        key = tuple(int(sample[k]) for k in ('motion_id', 'current_frame', 'target_frame'))
        if key not in accepted:
            raise ValueError(f'Predictor sample lacks accepted whole-path evidence: {key}')
    return dict(status='verified_reference_contact_paths', samples=len(samples),
                certificates=verified, predicted_path_status='not_observed',
                force_bearing_slip_status='unknown_without_same_solve_loads')
