"""Small differentiable fixtures for the coupled Torch trajectory checks."""
import numpy as np
import torch
from motion_edit.generation.torch_newton_ik import ARRAY_API as xp


class DifferentiableRobot:
    def forward_kinematics(self, q):
        q = xp.asarray(q)
        return torch.vmap(self.one_pose)(q) if q.ndim == 2 else self.one_pose(q)

    def evaluate(self, q, *, derivatives=False):
        q = xp.asarray(q)
        poses = self.forward_kinematics(q)
        return (poses, torch.vmap(torch.func.jacrev(self.one_pose))(q)) if derivatives else poses


def full_jacobian(function, value):
    state = xp.asarray(value).requires_grad_()
    return torch.autograd.functional.jacobian(function, state, vectorize=True).detach().numpy()


def gradient(function, value):
    state = xp.asarray(value).requires_grad_()
    return torch.autograd.grad(function(state), state)[0].detach().numpy()
