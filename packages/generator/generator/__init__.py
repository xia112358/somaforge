"""Motion predictors, infillers, datasets, and generation training."""
from importlib import import_module

_EXPORTS = {'ContactPlanQInfiller': ('generator.contact_q_generator', 'ContactPlanQInfiller'),
 'ContactQPrediction': ('generator.contact_q_generator', 'ContactQPrediction'),
 'ContactTransitionPlan': ('generator.contact_q_generator', 'ContactTransitionPlan'),
 'SequentialContactQPredictor': ('generator.contact_q_generator', 'SequentialContactQPredictor'),
 'ContactAwareQInfillerLoss': ('generator.neural_infiller', 'ContactAwareQInfillerLoss'),
 'G1ActionMedoidQDeformer': ('generator.neural_infiller', 'G1ActionMedoidQDeformer'),
 'G1ConstrainedKeypointInfiller': ('generator.neural_infiller', 'G1ConstrainedKeypointInfiller'),
 'G1ContactAwareQInfiller': ('generator.neural_infiller', 'G1ContactAwareQInfiller'),
 'InfillerLoss': ('generator.neural_infiller', 'InfillerLoss'),
 'constrained_infiller_loss': ('generator.neural_infiller', 'constrained_infiller_loss'),
 'contact_aware_q_infiller_loss': ('generator.neural_infiller', 'contact_aware_q_infiller_loss'),
 'TeacherDataset': ('generator.teacher_data', 'TeacherDataset'),
 'InteractionInfillerLoss': ('generator.unified_interaction', 'InteractionInfillerLoss'),
 'InteractionQInfiller': ('generator.unified_interaction', 'InteractionQInfiller'),
 'UnifiedInteractionLoss': ('generator.unified_interaction', 'UnifiedInteractionLoss'),
 'UnifiedInteractionPredictor': ('generator.unified_interaction', 'UnifiedInteractionPredictor'),
 'interaction_infiller_loss': ('generator.unified_interaction', 'interaction_infiller_loss'),
 'unified_interaction_loss': ('generator.unified_interaction', 'unified_interaction_loss')}
__all__ = list(_EXPORTS)

def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module, attribute = _EXPORTS[name]
    value = getattr(import_module(module), attribute)
    globals()[name] = value
    return value
