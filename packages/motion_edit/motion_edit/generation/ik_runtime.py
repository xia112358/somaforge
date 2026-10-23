"""Default Motion Edit IK runtime, without importing a numerical backend."""
from __future__ import annotations

import argparse
import importlib.abc
import os
from pathlib import Path

IK_BACKEND = 'torch_newton_contact_aware_taskspace'


def default_ik_script():
    return Path(__file__).with_name('torch_newton_ik.py')


class RejectJax(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'jax', 'jaxlib', 'jaxlie', 'jaxls', 'pyroki'}:
            raise ImportError('Motion Edit Torch/Newton forbids '+fullname)
        return None


def add_runtime_arguments(parser):
    parser.add_argument('--device', default=os.environ.get('SOMAFORGE_IK_DEVICE', 'auto'),
        help='auto selects CUDA when available, otherwise CPU')
    parser.add_argument('--compile-kernels', action=argparse.BooleanOptionalAction, default=None,
        help='Defaults to compiled CUDA kernels and eager CPU kernels')


def resolve_runtime(device, compile_kernels):
    import torch
    if device == 'auto':
        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    device = str(torch.device(device))
    return device, device.startswith('cuda') if compile_kernels is None else compile_kernels
