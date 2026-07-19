"""Exact finite automorphisms of tiny Layered Matching Buffer kernels."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations, product

from acfqp.domains.matching_buffer import LMBAction, LMBKernel, LMBState


@dataclass(frozen=True, order=True, slots=True)
class LMBAutomorphism:
    """A tile permutation paired with one global type relabelling.

    Both tuples map source indices to destination indices.  Buffer coordinates
    therefore move according to ``type_permutation`` while removed-mask bits
    and actions move according to ``tile_permutation``.
    """

    tile_permutation: tuple[int, ...]
    type_permutation: tuple[int, ...]


def enumerate_lmb_automorphisms(
    kernel: LMBKernel,
    *,
    candidate_cap: int = 100_000,
) -> tuple[LMBAutomorphism, ...]:
    """Enumerate all exact tile/type relabellings of a tiny registered kernel."""

    if candidate_cap <= 0:
        raise ValueError("LMB automorphism candidate cap must be positive")
    tile_groups = tuple(
        tuple(tile for tile, kind in enumerate(kernel.tile_types) if kind == tile_type)
        for tile_type in range(kernel.type_count)
    )
    candidates = 0
    automorphisms: list[LMBAutomorphism] = []
    for type_permutation in permutations(range(kernel.type_count)):
        if any(
            len(tile_groups[source]) != len(tile_groups[type_permutation[source]])
            for source in range(kernel.type_count)
        ):
            continue
        target_orders = tuple(
            tuple(permutations(tile_groups[type_permutation[source]]))
            for source in range(kernel.type_count)
        )
        for group_images in product(*target_orders):
            candidates += 1
            if candidates > candidate_cap:
                raise RuntimeError("LMB automorphism enumeration exceeded its cap")
            tile_permutation = [-1] * kernel.tile_count
            for source_type, images in enumerate(group_images):
                for source_tile, target_tile in zip(
                    tile_groups[source_type], images
                ):
                    tile_permutation[source_tile] = target_tile
            permutation = tuple(tile_permutation)
            if any(tile < 0 for tile in permutation):
                raise AssertionError("LMB tile automorphism is incomplete")
            if all(
                {permutation[blocker] for blocker in kernel.blockers[source]}
                == set(kernel.blockers[permutation[source]])
                for source in range(kernel.tile_count)
            ):
                automorphisms.append(
                    LMBAutomorphism(permutation, tuple(type_permutation))
                )
    if not automorphisms:
        raise AssertionError("every LMB kernel must have the identity automorphism")
    return tuple(sorted(automorphisms))


def transform_lmb_state(
    kernel: LMBKernel,
    state: LMBState,
    automorphism: LMBAutomorphism,
) -> LMBState:
    if len(automorphism.tile_permutation) != kernel.tile_count:
        raise ValueError("LMB automorphism tile permutation has the wrong size")
    if len(automorphism.type_permutation) != kernel.type_count:
        raise ValueError("LMB automorphism type permutation has the wrong size")
    removed_mask = 0
    for source, target in enumerate(automorphism.tile_permutation):
        if state.removed_mask & (1 << source):
            removed_mask |= 1 << target
    buffer = [0] * kernel.type_count
    for source, target in enumerate(automorphism.type_permutation):
        buffer[target] = state.buffer[source]
    return LMBState(removed_mask, tuple(buffer), state.status)


def transform_lmb_action(
    kernel: LMBKernel,
    action: LMBAction,
    automorphism: LMBAutomorphism,
) -> LMBAction:
    if action.tile < 0 or action.tile >= kernel.tile_count:
        raise ValueError("LMB action tile lies outside the kernel")
    return LMBAction(automorphism.tile_permutation[action.tile])


def lmb_orbit(
    kernel: LMBKernel,
    state: LMBState,
    automorphisms: tuple[LMBAutomorphism, ...] | None = None,
) -> tuple[LMBState, ...]:
    group = (
        enumerate_lmb_automorphisms(kernel)
        if automorphisms is None
        else automorphisms
    )
    return tuple(
        sorted({transform_lmb_state(kernel, state, element) for element in group})
    )


__all__ = [
    "LMBAutomorphism",
    "enumerate_lmb_automorphisms",
    "lmb_orbit",
    "transform_lmb_action",
    "transform_lmb_state",
]
