"""Batch contact-Laplian trajectory solver.

This package contains the full-trajectory least-squares solver used by the
default ``generate-lte-augmentation --mode lte_fullbody`` path. The current
production bridge optimizes semantic ``body_pos_w`` task-space points and writes
an internal generated motion; the legacy external LTE/IK subprocess path is only
used when explicitly selected.
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
