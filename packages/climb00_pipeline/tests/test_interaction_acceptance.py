import pytest
from climb00_pipeline.interaction_acceptance import (
    contact_acceptance, penetration_accepted,
)


def pair(part, surface=0, overlap=0.0001, margin=0.02):
    return dict(part=part, surface=surface, dist=margin-overlap,
                includemargin=margin, allocated=True, efc_address=0,
                constraint_active=True)


CONTACT = [True, False, False, False, False, False]
SURFACE = [0, -1, -1, -1, -1, -1]


def test_tiny_extra_kept_in_observation_but_accepted():
    pairs = [pair(0), pair(1)]
    pairs[0]['efc_address'] = [3, -1, -1]
    result = contact_acceptance(pairs, CONTACT, SURFACE)
    assert result['contact_accepted'] and result['ignored_extra_pairs'] == 1
    assert len(pairs) == 2


def test_missing_required_and_wrong_surface_never_waived():
    for pairs in ([], [pair(0, surface=1)]):
        assert not contact_acceptance(pairs, CONTACT, SURFACE)['contact_accepted']


def test_every_pair_checked_and_margin_is_pair_specific():
    assert not contact_acceptance([pair(0), pair(1, overlap=.002)], CONTACT, SURFACE)['contact_accepted']
    # Same part on another surface is also an extra, even if a correct pair exists.
    assert not contact_acceptance([pair(0), pair(0, surface=1, overlap=.002)], CONTACT, SURFACE)['contact_accepted']
    assert not contact_acceptance([pair(0), pair(1, overlap=.0002, margin=.001)], CONTACT, SURFACE)['contact_accepted']


def test_invalid_allocations_and_unknown_values_fail_closed():
    for change in (dict(allocated=False), dict(efc_address=-1), dict(efc_address=[-1, -1]), dict(dist=float('nan')),
                   dict(constraint_active=False), dict(includemargin=float('nan'))):
        p = pair(0); p.update(change)
        with pytest.raises(ValueError):
            contact_acceptance([p], CONTACT, SURFACE)


def test_penetration_boundaries_and_unknown_geometry():
    assert penetration_accepted(0) and penetration_accepted(.001)
    assert not penetration_accepted(.00101)
    assert not penetration_accepted(float('nan'))
    assert not penetration_accepted(0, invalid_witnesses=1)
