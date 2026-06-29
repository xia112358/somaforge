# GMVQ Ref Integration Scripts

This directory is for glue scripts owned by `holosoma_newton`.

Keep generic model code in `gmvq-vae` and editor/cut tooling in `motion_edit`.
Scripts here may call those repos, but should not duplicate their source code.

Expected local layout:

```text
/home/xiaz/
  motion_edit/
  gmvq-vae/
  holosoma_isaaclab3_newton/
```

Use `check_workspace.py` before running training/eval commands to catch the most
common data mixup: using rollout state as the VAE ref source.
