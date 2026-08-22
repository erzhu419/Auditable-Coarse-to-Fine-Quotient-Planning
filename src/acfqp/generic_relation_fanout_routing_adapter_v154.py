"""Opaque flat adapters for V154 relation fan-out transfer and OOD control."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp.domains.stochastic_relation_fanout_routing_v154 import (
    RelationFanoutAction,
    RelationFanoutState,
    RelationFanoutStatus,
    generate_stochastic_relation_fanout_routing_v154,
    select_seeded_relation_fanout_outcome_v154,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import (
    quaternary_relation_workflow_config_v153,
)


FAMILY = "STOCHASTIC_RELATION_FANOUT_ROUTING_SOURCE_UNSEEN"
OOD_FAMILY = "STOCHASTIC_RELATION_FANOUT_ROUTING_ANONYMOUS_SCHEMA_INCOMPATIBLE"


@dataclass(frozen=True, slots=True)
class RelationFanoutRoutingFlatAdapterV154:
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
        return action.edge

    def action(self, key):
        return RelationFanoutAction(key)

    def active(self, state):
        return state.status is RelationFanoutStatus.ACTIVE

    def success(self, state):
        return state.status is RelationFanoutStatus.SUCCESS

    def probe_state(self, key):
        rule = self.kernel.rules[key]
        return RelationFanoutState(rule.source, 0, 0, 0, 0, RelationFanoutStatus.ACTIVE)

    def select_outcome(self, state, key, episode_index, decision_index):
        return select_seeded_relation_fanout_outcome_v154(
            self.kernel.step(state, RelationFanoutAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def relation_fanout_routing_config_v154():
    config = copy.deepcopy(quaternary_relation_workflow_config_v153())
    config["families"][FAMILY] = {"maximum_acquisition_labels": 1_536}
    config["families"][OOD_FAMILY] = {"maximum_acquisition_labels": 64}
    return config


def build_relation_fanout_routing_adapter_v154(
    seed: int, config: Mapping[str, Any], *, incompatible: bool = False
):
    del config
    kernel, witness = generate_stochastic_relation_fanout_routing_v154(seed=seed)
    del witness
    state_order = list(range(10))
    action_order = list(range(6))
    random.Random(seed ^ 0x154B73).shuffle(state_order)
    random.Random(seed ^ 0x154C89).shuffle(action_order)
    mode_tokens = sorted({rule.opaque_mode for rule in kernel.rules})
    broken_tokens = {token: 700 + (index % 2) for index, token in enumerate(mode_tokens)}
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    broken_tokens[rule.opaque_mode] if incompatible else rule.opaque_mode,
                    seed * 100 + rule.destination,
                    seed * 100 + rule.source,
                    80 + ((rule.source + rule.risk_increment) % 2),
                    seed * 10_000 + key,
                    120 + (rule.risk_increment % 2),
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )
    tokens = relation_fanout_routing_config_v154()["terminal_tokens"]

    def encode(state: RelationFanoutState):
        status = tokens[
            "A"
            if state.status is RelationFanoutStatus.ACTIVE
            else "S"
            if state.status is RelationFanoutStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.node,
            state.phase,
            state.resource,
            state.checksum,
            state.steps,
            status,
            kernel.modulus,
            kernel.capacity,
            seed * 100 + kernel.goal_node,
            92_000 + (seed % 109),
        )
        return tuple(semantic[index] for index in state_order)

    return RelationFanoutRoutingFlatAdapterV154(
        OOD_FAMILY if incompatible else FAMILY,
        seed,
        kernel,
        catalogue,
        encode,
    )


__all__ = (
    "FAMILY",
    "OOD_FAMILY",
    "build_relation_fanout_routing_adapter_v154",
    "relation_fanout_routing_config_v154",
)
