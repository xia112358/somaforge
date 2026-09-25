"""Task acceptance tolerances over authoritative Newton facts, not labels."""
from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class InteractionAcceptance:
    shallow_penetration_m: float = 0.001
    extra_activation_margin_fraction: float = 0.05

    def __post_init__(self):
        if not math.isfinite(self.shallow_penetration_m) or self.shallow_penetration_m < 0:
            raise ValueError("Invalid penetration acceptance tolerance")
        if not 0 <= self.extra_activation_margin_fraction <= 1:
            raise ValueError("Invalid extra activation tolerance fraction")


DEFAULT_ACCEPTANCE = InteractionAcceptance()


def acceptance_contract():
    return dict(schema="newton_task_acceptance_v1", **asdict(DEFAULT_ACCEPTANCE),
                contact_truth="unchanged Newton active+allocated primary-face pairs",
                intended_contacts="all required limb/surface pairs must exist")


def contact_acceptance(pairs, intended_contact, intended_surface,
                       limits=DEFAULT_ACCEPTANCE):
    """Consume already selected Newton pairs; inspect EVERY extra pair.

    A tolerated pair is still real contact and stays in the observation.
    Activation overlap is margin-dist, not geometric penetration.
    """
    required = {(i, int(s)) for i, (c, s) in
                enumerate(zip(intended_contact, intended_surface, strict=True)) if c}
    if any(s < 0 for _, s in required):
        raise ValueError("Required contact has unknown surface")
    actual = set()
    ignored = blocking = 0
    maximum = 0.0
    for pair in pairs:
        part, surface = int(pair["part"]), int(pair["surface"])
        distance, margin = float(pair["dist"]), float(pair["includemargin"])
        address = pair.get("efc_address")
        addresses = address if isinstance(address, (list, tuple)) else [address]
        bad_address = address is not None and not any(
            int(value) >= 0 for value in addresses
        )
        if (not pair["allocated"] or not 0 <= part < 6 or
                not math.isfinite(distance) or not math.isfinite(margin) or
                distance >= margin or
                ("constraint_active" in pair and not pair["constraint_active"]) or
                bad_address):
            raise ValueError("Invalid active+allocated Newton pair")
        key = (part, surface)
        actual.add(key)
        if key in required:
            continue
        overlap = margin - distance
        maximum = max(maximum, overlap)
        if margin > 0 and overlap <= limits.extra_activation_margin_fraction * margin:
            ignored += 1
        else:
            blocking += 1
    missing = len(required - actual)
    return dict(contact_accepted=(missing == 0 and blocking == 0),
                missing_required_pairs=missing, ignored_extra_pairs=ignored,
                blocking_extra_pairs=blocking, max_extra_activation_overlap_m=maximum)


def penetration_accepted(depth_m, invalid_witnesses=0, limits=DEFAULT_ACCEPTANCE):
    return (math.isfinite(depth_m) and depth_m >= 0 and invalid_witnesses == 0
            and depth_m <= limits.shallow_penetration_m)
