"""Opaque flat adapter for the held-out stochastic modular-routing family."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp import construction_k7_owned_sequence_cross_family_preregistration_v127 as previous
from acfqp.domains.stochastic_modular_routing import (
    StochasticModularAction,
    StochasticModularState,
    StochasticModularStatus,
    generate_stochastic_modular_routing,
    select_seeded_stochastic_modular_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4


FAMILY = "STOCHASTIC_MODULAR_ROUTING_HELD_OUT"


@dataclass(frozen=True, slots=True)
class ModularRoutingFlatAdapterV128:
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
        return action.edge

    def action(self, key: int) -> Any:
        return StochasticModularAction(key)

    def active(self, state: Any) -> bool:
        return state.status is StochasticModularStatus.ACTIVE

    def success(self, state: Any) -> bool:
        return state.status is StochasticModularStatus.SUCCESS

    def probe_state(self, key: int) -> Any:
        edge = self.kernel.edges[key]
        return StochasticModularState(
            edge.source,
            0,
            0,
            0,
            StochasticModularStatus.ACTIVE,
        )

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        return select_seeded_stochastic_modular_outcome_v1(
            self.kernel.step(state, StochasticModularAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def modular_routing_config_v128() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v127())
    config["families"][FAMILY] = {
        "node_count": 7,
        "modulus": 5,
        "capacity": 24,
        "step_limit": 8,
        "mode_deltas": (1, 2, 3),
        "maximum_acquisition_labels": 2_048,
    }
    return config


def build_modular_routing_adapter_v128(
    seed: int, config: Mapping[str, Any]
) -> ModularRoutingFlatAdapterV128:
    spec = config["families"][FAMILY]
    kernel, witness = generate_stochastic_modular_routing(
        node_count=spec["node_count"],
        modulus=spec["modulus"],
        capacity=spec["capacity"],
        step_limit=spec["step_limit"],
        mode_deltas=tuple(spec["mode_deltas"]),
        seed=seed,
        require_last_mode=True,
    )
    del witness
    state_order = list(range(10))
    action_order = list(range(7))
    random.Random(seed ^ 0x128A71).shuffle(state_order)
    random.Random(seed ^ 0x128B83).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + edge.source,
                    seed * 100 + edge.destination,
                    kernel.mode_deltas[edge.mode],
                    edge.magnitude,
                    edge.cost_class,
                    1,
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, edge in enumerate(kernel.edges)
    )
    tokens = config["terminal_tokens"]

    def encode(state: StochasticModularState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is StochasticModularStatus.ACTIVE
            else "S"
            if state.status is StochasticModularStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.node,
            state.phase,
            state.resource,
            state.steps,
            status,
            kernel.capacity,
            kernel.step_limit,
            kernel.modulus,
            kernel.goal_phase,
            seed * 100 + kernel.goal_node,
        )
        return tuple(semantic[index] for index in state_order)

    return ModularRoutingFlatAdapterV128(FAMILY, seed, kernel, catalogue, encode)


__all__ = (
    "FAMILY",
    "ModularRoutingFlatAdapterV128",
    "build_modular_routing_adapter_v128",
    "modular_routing_config_v128",
)
