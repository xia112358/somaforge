"""Batch contact-Laplacian trajectory solver.

This package contains the full-trajectory least-squares solver used by the
standard ``generate-ref`` path before force retargeting. The current production
bridge optimizes semantic ``body_pos_w`` task-space points, feeds IK, and then
the force writer emits a WBT-ready policy reference. The geometry-only
``generate-lte-augmentation`` path is diagnostic/hidden and should not be used
as the force-checkpoint payload.
"""

from .kinematics import BodyPositionTrajectoryKinematicsProvider, KinematicsProvider, LinearPointKinematicsProvider
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
    "solve_batch_contact_laplacian",
    "solve_transfer_local_contact_laplacian",
]
