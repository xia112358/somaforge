from __future__ import annotations

from isaaclab_newton.physics import NewtonManager
from isaaclab_newton.sensors.ray_caster.ray_caster import RayCaster as NewtonRayCaster
from loguru import logger


class HolosomaNewtonRayCaster(NewtonRayCaster):
    """Newton RayCaster variant that resolves one scanner frame per environment.

    Isaac Lab's Newton RayCaster expands every registered label for every env.
    In this manually assembled scene path the registered regex can already map
    to all env sensor sites, so the stock resolver produces num_envs squared
    frames. Height scanning expects exactly one scanner frame per env.
    """

    def _initialize_pose_tracking(self) -> None:
        super()._initialize_pose_tracking()
        if self._view_count != self._num_envs:
            raise RuntimeError(
                f"HolosomaNewtonRayCaster resolved {self._view_count} scanner frames for "
                f"{self._num_envs} envs; expected one frame per env."
            )
        logger.info(
            "HolosomaNewtonRayCaster resolved {} scanner frames for {} envs.",
            self._view_count,
            self._num_envs,
        )

    @staticmethod
    def _resolve_site_indices(labels: list[str], prim_expr: str, num_envs: int) -> list[int]:
        site_map = NewtonManager._cl_site_index_map
        site_indices: list[int] = []

        for env_idx in range(num_envs):
            env_candidates: list[int] = []
            for label in labels:
                error_prefix = f"RayCaster target '{prim_expr}' site label '{label}'"
                if label not in site_map:
                    raise ValueError(f"{error_prefix} was not found in NewtonManager._cl_site_index_map.")

                global_idx, per_world = site_map[label]
                if per_world is None:
                    env_candidates.append(global_idx)
                    continue

                if env_idx >= len(per_world):
                    raise ValueError(
                        f"{error_prefix} has {len(per_world)} world entries, expected at least {num_envs}."
                    )

                world_sites = list(per_world[env_idx])
                if len(world_sites) == 1:
                    env_candidates.append(world_sites[0])
                elif len(world_sites) == num_envs:
                    env_candidates.append(world_sites[env_idx])
                else:
                    raise ValueError(
                        f"{error_prefix} resolved {len(world_sites)} sites for env {env_idx}; "
                        "expected either one site or one site per env."
                    )

            if len(env_candidates) == 1:
                site_indices.append(env_candidates[0])
            elif len(env_candidates) == num_envs:
                site_indices.append(env_candidates[env_idx])
            else:
                raise ValueError(
                    f"RayCaster target '{prim_expr}' resolved {len(env_candidates)} candidate sites for env "
                    f"{env_idx}; expected one candidate."
                )

        return site_indices
