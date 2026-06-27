from __future__ import annotations

from types import SimpleNamespace

import torch

from .data import make_synthetic_segments, normalize_segments
from .losses import compute_loss
from .models import GMVQAutoEncoder


def main() -> None:
    torch.manual_seed(0)
    x, _ = make_synthetic_segments(n=32, t=120, d=14, num_modes=6)
    x, _ = normalize_segments(x)
    model = GMVQAutoEncoder(t=120, d=14, latent_dim=16, num_codes=8)
    out = model(x)
    cfg = SimpleNamespace()
    loss, metrics = compute_loss(x, out, model, cfg)

    assert out["x_recon"].shape == x.shape
    assert out["theta"].shape == (32, 16)
    assert out["codes"].shape == (32,)
    assert torch.isfinite(loss)
    assert int(metrics["active_codes"]) >= 1

    print(
        "quick synthetic test passed:",
        f"loss={float(loss.detach()):.4f}",
        f"active_codes={int(metrics['active_codes'])}",
        f"perplexity={float(metrics['perplexity']):.4f}",
    )


if __name__ == "__main__":
    main()
