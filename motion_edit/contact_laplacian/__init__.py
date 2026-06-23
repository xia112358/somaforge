"""Experimental batch contact-Laplacian trajectory solver.

This package contains the full-trajectory least-squares solver scaffold and
synthetic kinematics tests. It is not the current production generator for real
robot motions. Production ``generate-lte-augmentation --mode lte_fullbody``
defaults to the task-space LTE plus IK subprocess path unless explicitly asked
to dry-run or experiment with this backend.
"""

from .kinematics import BodyPositionTrajectoryKinematicsProvider, KinematicsProvider, LinearPointKinematicsProvider
from .schema import BatchContactLaplacianConfig, ContactHandleSpec, ContactLaplacianSolveResult, InteractionMeshSpec
from .solver import solve_batch_contact_laplacian

__all__ = [
    "BatchContactLaplacianConfig",
    "ContactHandleSpec",
    "ContactLaplacianSolveResult",
    "InteractionMeshSpec",
    "BodyPositionTrajectoryKinematicsProvider",
    "KinematicsProvider",
    "LinearPointKinematicsProvider",
    "solve_batch_contact_laplacian",
]
