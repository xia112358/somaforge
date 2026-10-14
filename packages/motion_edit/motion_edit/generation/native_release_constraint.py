"""Hard release feasibility from the complete, initialized Newton scene.

Every optimizer candidate is queried afresh; no exported trajectory or witness
cache feeds a second generation pass. Witnesses only provide local derivatives.
"""
import numpy as np
from somaforge_core.newton_contact_query import query_contacts
from somaforge_core.contact_face_selection import select_contact_pairs


class NativeReleaseConstraint:
    def __init__(self, source_mask, fingerprint, state_to_q, witness_jacobian):
        self.absent = ~np.asarray(source_mask, bool)
        self.fingerprint = fingerprint
        self.state_to_q = state_to_q
        self.witness_jacobian = witness_jacobian
        self.last = None
        self.calls = 0
        self.invalid_candidates = 0

    def evaluate(self, x):
        if self.last is not None and np.array_equal(x, self.last[0]):
            return self.last[1:]
        self.calls += 1
        try:
            result = query_contacts(self.state_to_q(x)[None, :])
        except RuntimeError as exc:
            if 'Actual contact face absent:' not in str(exc):raise
            # A trial outside the verified face mapping is unknown, not an
            # invented top contact and never a feasible pose. Derivative-free
            # constrained search can reject this trial and continue internally.
            self.invalid_candidates += 1
            self.active_parts={-1}
            self.last=(np.array(x,copy=True),-np.ones(6),[None]*6,{'body_labels':[]})
            print(f'native-hard-release rejected unknown candidate: {exc}',flush=True)
            return self.last[1:]
        if result['provenance']['model_fingerprint'] != self.fingerprint:
            raise ValueError('Hard constraint worker has a different native model')
        selected = select_contact_pairs(result['pairs'], result['surface_catalog'])
        values = np.ones(6)
        worst = [None]*6
        active_parts={p['part'] for p in selected['contact_pairs'][0] if self.absent[p['part']]}
        if 'candidate_pairs' not in result:raise ValueError('Native candidate distances missing')
        top_faces={int(s['surface']) for s in result['surface_catalog'] if np.allclose(s['normal_w'],[0,0,1],atol=1.e-6,rtol=0)}
        for pair in result['candidate_pairs'][0]:
            p = pair['part']
            if not self.absent[p] or pair['surface'] not in top_faces:
                continue
            # An active contact can never count as numerically feasible, even
            # when its signed gap falls below the optimizer's tolerance.
            gap = pair['dist']-pair['includemargin']
            guard = np.finfo(np.float32).eps*max(1., np.max(np.abs(pair['position_w'])))
            value = gap-guard
            if worst[p] is None or value < values[p]:
                values[p], worst[p] = value, pair
        self.active_parts=active_parts
        self.last = (np.array(x, copy=True), values, worst, result['provenance'])
        return self.last[1:]

    def fun(self, x):
        return self.evaluate(x)[0]

    def jac(self, x):
        _, worst, model = self.evaluate(x)
        return self.witness_jacobian(x, worst, model)

    def feasible(self, x):
        self.evaluate(x)
        return not self.active_parts
