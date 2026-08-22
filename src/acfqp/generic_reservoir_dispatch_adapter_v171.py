"""Opaque flat adapter for the fresh V171 reservoir-dispatch family."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp.domains.stochastic_reservoir_dispatch import (
    ReservoirDispatchAction,
    ReservoirDispatchState,
    ReservoirDispatchStatus,
    generate_stochastic_reservoir_dispatch,
    select_seeded_reservoir_dispatch_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_packet_batching_adapter_v134 import packet_batching_config_v134


FAMILY = "STOCHASTIC_RESERVOIR_DISPATCH_V171_SOURCE_UNSEEN"


@dataclass(frozen=True, slots=True)
class ReservoirDispatchFlatAdapterV171:
    family: str
    seed: int
    kernel: Any
    catalogue: tuple[FlatRawActionV4, ...]
    encode: Any

    def initial(self):
        return self.kernel.initial_distribution()[0][1]

    def actions(self, state):
        return tuple(self.kernel.actions(state))

    def action_key(self, action):
        return action.conduit

    def action(self, key):
        return ReservoirDispatchAction(key)

    def active(self, state):
        return state.status is ReservoirDispatchStatus.ACTIVE

    def success(self, state):
        return state.status is ReservoirDispatchStatus.SUCCESS

    def probe_state(self, key):
        conduit = self.kernel.conduits[key]
        return ReservoirDispatchState(
            conduit.source, 0, 0, 0, 0, 0, ReservoirDispatchStatus.ACTIVE
        )

    def select_outcome(self, state, key, episode_index, decision_index):
        return select_seeded_reservoir_dispatch_outcome_v1(
            self.kernel.step(state, ReservoirDispatchAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def reservoir_dispatch_config_v171() -> dict[str, Any]:
    config = copy.deepcopy(packet_batching_config_v134())
    config["families"][FAMILY] = {
        "basin_count": 8,
        "maximum_acquisition_labels": 2_048,
    }
    return config


def build_reservoir_dispatch_adapter_v171(
    seed: int, config: Mapping[str, Any]
) -> ReservoirDispatchFlatAdapterV171:
    spec = config["families"][FAMILY]
    kernel, witness = generate_stochastic_reservoir_dispatch(
        basin_count=spec["basin_count"], seed=seed
    )
    del witness
    state_order = list(range(13))
    action_order = list(range(8))
    random.Random(seed ^ 0x171B73).shuffle(state_order)
    random.Random(seed ^ 0x171C89).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + conduit.source,
                    seed * 100 + conduit.destination,
                    conduit.delivery_increment,
                    conduit.reserve_increment,
                    50 + conduit.salinity_scale,
                    80 + conduit.stress_increment,
                    120 + ((conduit.source + key) % 4),
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, conduit in enumerate(kernel.conduits)
    )
    tokens = config["terminal_tokens"]

    def encode(state: ReservoirDispatchState):
        status = tokens[
            "A"
            if state.status is ReservoirDispatchStatus.ACTIVE
            else "S"
            if state.status is ReservoirDispatchStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.basin,
            state.delivered,
            state.reserve,
            state.salinity,
            state.stress,
            state.elapsed,
            status,
            1_000 + kernel.stress_capacity,
            2_000 + kernel.delivery_target,
            3_000 + kernel.salinity_target,
            4_000 + kernel.salinity_modulus,
            5_000 + kernel.step_limit,
            seed * 100 + kernel.goal_basin,
        )
        return tuple(semantic[index] for index in state_order)

    return ReservoirDispatchFlatAdapterV171(
        FAMILY, seed, kernel, catalogue, encode
    )


__all__ = (
    "FAMILY",
    "ReservoirDispatchFlatAdapterV171",
    "build_reservoir_dispatch_adapter_v171",
    "reservoir_dispatch_config_v171",
)
