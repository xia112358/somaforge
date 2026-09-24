"""Cache identity includes actual motions, terrain, labels and label policy."""
import hashlib
import json
from pathlib import Path
import numpy as np
from .contact_face_selection import effective_contact_contract as label_contract


def contact_dataset_fingerprint(manifest_path):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    def resolve(value):
        path = Path(value)
        return path if path.is_absolute() else manifest_path.parent/path
    rows = []
    for entry in manifest['motion_files']:
        motion = resolve(entry['motion_file'])
        if not entry.get('newton_contact_file'):
            raise ValueError('Contact cache requires explicit labels for every motion')
        labels = resolve(entry['newton_contact_file'])
        with np.load(motion, allow_pickle=False) as z:
            fps = float(z['fps'].reshape(-1)[0])
        rows.append(dict(motion_id=entry['motion_id'], terrain_id=entry['terrain_id'],
                         motion_sha256=hashlib.sha256(motion.read_bytes()).hexdigest(),
                         labels_sha256=hashlib.sha256(labels.read_bytes()).hexdigest(),
                         contract=label_contract(fps)))
        if entry.get('event_segments_file'):
            rows[-1]['event_segments_sha256'] = hashlib.sha256(resolve(entry['event_segments_file']).read_bytes()).hexdigest()
            rows[-1]['event_contract'] = manifest['event_contract']
    terrain = [(t['terrain_id'],hashlib.sha256(resolve(t['terrain_file']).read_bytes()).hexdigest())
               for t in manifest['terrains']]
    payload = dict(schema='somaforge_contact_dataset_identity_v1',rows=rows,terrains=terrain)
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def validate_contact_cache(cache, manifest_path):
    field = 'contact_dataset_fingerprint'
    if field not in cache or str(np.asarray(cache[field]).item()) != contact_dataset_fingerprint(manifest_path):
        raise ValueError('Cache contact dataset/policy mismatch or missing provenance; rebuild cache')
