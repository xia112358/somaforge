"""Explicit v1/v2 architecture selection for scratch training and checkpoints."""
from somaforge_core.robot_assets import decode_robot_asset_json
from generator.structured_position_predictor import StructuredPositionPredictor, STRUCTURED_SCHEMA

LEGACY_SCHEMA = 'full1000_position_predictor_v1'
POSITION_SCHEMAS = (LEGACY_SCHEMA, STRUCTURED_SCHEMA)
ARCHITECTURE_FIELDS = ('width', 'layers', 'location_width', 'body_geometry', 'part_geometry',
                       'region_plan', 'unified_contact', 'event_roles')


def build_position_predictor(config, *, schema=STRUCTURED_SCHEMA):
    """Legacy construction must be requested explicitly; never infer from tensor shapes."""
    if schema not in POSITION_SCHEMAS:
        raise ValueError(f'Unsupported position architecture: {schema}')
    if schema == STRUCTURED_SCHEMA:
        if config.get('architecture') != STRUCTURED_SCHEMA:
            raise ValueError('Structured training/checkpoint requires explicit v2 architecture')
        missing = set(ARCHITECTURE_FIELDS) - config.keys()
        if missing:
            raise ValueError(f'Structured architecture configuration missing: {sorted(missing)}')
        cls = StructuredPositionPredictor
    else:
        if config.get('architecture', LEGACY_SCHEMA) != LEGACY_SCHEMA:
            raise ValueError('Legacy schema/config architecture mismatch')
        from generator.full1000_position_predictor import Full1000PositionPredictor
        cls = Full1000PositionPredictor
    defaults = dict(width=192, layers=3, location_width=32, body_geometry=False,
        part_geometry=False, region_plan=False, unified_contact=False, event_roles=False)
    kwargs = {key: config.get(key, value) for key, value in defaults.items()}
    kwargs.update(execution_plan_gradients=config.get('execution_plan_gradients', False),
                  execution_observation_gradients=config.get('execution_observation_gradients', False))
    return cls(**kwargs)


def load_position_predictor(checkpoint, *, device='cpu'):
    decode_robot_asset_json(checkpoint['robot_asset_json'], context='versioned position checkpoint')
    model = build_position_predictor(checkpoint['config'], schema=checkpoint['schema']).to(device)
    if checkpoint['schema'] == STRUCTURED_SCHEMA:
        if checkpoint.get('architecture_contract') != model.architecture_contract():
            raise ValueError('Checkpoint architecture contract/order mismatch')
    model.load_state_dict(checkpoint['model'], strict=True)
    return model
