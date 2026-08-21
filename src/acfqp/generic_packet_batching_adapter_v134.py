"""Opaque flat adapter for the source-unseen packet-batching domain V134."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp.domains.stochastic_packet_batching import (
    PacketBatchingAction,
    PacketBatchingState,
    PacketBatchingStatus,
    generate_stochastic_packet_batching,
    select_seeded_packet_batching_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_modular_routing_adapter_v128 import modular_routing_config_v128


FAMILY = "STOCHASTIC_PACKET_BATCHING_SOURCE_UNSEEN"


@dataclass(frozen=True, slots=True)
class PacketBatchingFlatAdapterV134:
    family: str
    seed: int
    kernel: Any
    catalogue: tuple[FlatRawActionV4, ...]
    encode: Any

    def initial(self) -> Any:
        return self.kernel.initial_distribution()[0][1]

    def actions(self, state: Any) -> tuple[Any, ...]:
        return tuple(self.kernel.actions(state))

    def action_key(self, action: Any) -> int:
        return action.route

    def action(self, key: int) -> Any:
        return PacketBatchingAction(key)

    def active(self, state: Any) -> bool:
        return state.status is PacketBatchingStatus.ACTIVE

    def success(self, state: Any) -> bool:
        return state.status is PacketBatchingStatus.SUCCESS

    def probe_state(self, key: int) -> Any:
        route = self.kernel.routes[key]
        return PacketBatchingState(
            route.source, 0, 0, 0, 0, PacketBatchingStatus.ACTIVE
        )

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        return select_seeded_packet_batching_outcome_v1(
            self.kernel.step(state, PacketBatchingAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def packet_batching_config_v134() -> dict[str, Any]:
    config = copy.deepcopy(modular_routing_config_v128())
    config["families"][FAMILY] = {
        "station_count": 8,
        "maximum_acquisition_labels": 384,
    }
    return config


def build_packet_batching_adapter_v134(
    seed: int, config: Mapping[str, Any]
) -> PacketBatchingFlatAdapterV134:
    spec = config["families"][FAMILY]
    kernel, witness = generate_stochastic_packet_batching(
        station_count=spec["station_count"], seed=seed
    )
    del witness
    state_order = list(range(12))
    action_order = list(range(7))
    random.Random(seed ^ 0x134A97).shuffle(state_order)
    random.Random(seed ^ 0x134BB9).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + route.source,
                    seed * 100 + route.destination,
                    route.packet_increment,
                    route.delay_increment,
                    50 + route.parity_scale,
                    100 + route.cost_class,
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, route in enumerate(kernel.routes)
    )
    tokens = config["terminal_tokens"]

    def encode(state: PacketBatchingState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is PacketBatchingStatus.ACTIVE
            else "S"
            if state.status is PacketBatchingStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.station,
            state.packets,
            state.delay,
            state.parity,
            state.steps,
            status,
            1_000 + kernel.delay_capacity,
            2_000 + kernel.target_packets,
            3_000 + kernel.target_parity,
            4_000 + kernel.parity_modulus,
            5_000 + kernel.step_limit,
            seed * 100 + kernel.goal_station,
        )
        return tuple(semantic[index] for index in state_order)

    return PacketBatchingFlatAdapterV134(FAMILY, seed, kernel, catalogue, encode)


__all__ = (
    "FAMILY",
    "PacketBatchingFlatAdapterV134",
    "build_packet_batching_adapter_v134",
    "packet_batching_config_v134",
)
