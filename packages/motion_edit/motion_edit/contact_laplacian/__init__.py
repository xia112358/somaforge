"""Task-space propagation used by the contact-aware generation backend.

This geometry stage is not contact truth; edited candidates require fresh
Newton verification before any training-data admission.
"""

from .kinematics import BodyPositionTrajectoryKinematicsProvider, KinematicsProvider, LinearPointKinematicsProvider
from .omniretarget_mesh import (
    OmniRetargetInteractionMesh,
    build_omniretarget_interaction_mesh,
    sample_terrain_mesh_points,
)
from .schema import BatchContactLaplacianConfig, ContactHandleSpec, ContactLaplacianSolveResult, InteractionMeshSpec
from .solver import solve_batch_contact_laplacian
from .transfer_solver import TransferLocalContactLaplacianConfig, TransferWindowSpec, solve_transfer_local_contact_laplacian

__all__ = [
    "BatchContactLaplacianConfig",
    "ContactHandleSpec",
    "ContactLaplacianSolveResult",
    "InteractionMeshSpec",
    "TransferLocalContactLaplacianConfig",
    "TransferWindowSpec",
    "BodyPositionTrajectoryKinematicsProvider",
    "KinematicsProvider",
    "LinearPointKinematicsProvider",
    "OmniRetargetInteractionMesh",
    "build_omniretarget_interaction_mesh",
    "sample_terrain_mesh_points",
    "solve_batch_contact_laplacian",
    "solve_transfer_local_contact_laplacian",
]
