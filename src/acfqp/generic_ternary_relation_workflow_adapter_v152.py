"""Opaque adapter for changed-cardinality relational transfer in V152."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp.domains.stochastic_relation_keyed_workflow import (
    RelationKeyedWorkflowAction,
    RelationKeyedWorkflowState,
    RelationKeyedWorkflowStatus,
)
from acfqp.domains.stochastic_ternary_relation_workflow_v152 import (
    generate_stochastic_ternary_relation_workflow_v152,
    select_seeded_ternary_relation_workflow_outcome_v152,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_packet_batching_adapter_v134 import packet_batching_config_v134


FAMILY = "STOCHASTIC_TERNARY_RELATION_WORKFLOW_SOURCE_UNSEEN"


@dataclass(frozen=True, slots=True)
class TernaryRelationWorkflowFlatAdapterV152:
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
        return action.rule

    def action(self, key: int) -> Any:
        return RelationKeyedWorkflowAction(key)

    def active(self, state: Any) -> bool:
        return state.status is RelationKeyedWorkflowStatus.ACTIVE

    def success(self, state: Any) -> bool:
        return state.status is RelationKeyedWorkflowStatus.SUCCESS

    def probe_state(self, key: int) -> Any:
        rule = self.kernel.rules[key]
        return RelationKeyedWorkflowState(
            rule.source_stage, 0, 0, 0, 0, RelationKeyedWorkflowStatus.ACTIVE
        )

    def select_outcome(self, state: Any, key: int, episode_index: int, decision_index: int):
        return select_seeded_ternary_relation_workflow_outcome_v152(
            self.kernel.step(state, RelationKeyedWorkflowAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def ternary_relation_workflow_config_v152() -> dict[str, Any]:
    config = copy.deepcopy(packet_batching_config_v134())
    config["families"][FAMILY] = {"stage_count": 7, "maximum_acquisition_labels": 1_536}
    return config


def build_ternary_relation_workflow_adapter_v152(seed: int, config: Mapping[str, Any]):
    spec = config["families"][FAMILY]
    kernel, witness = generate_stochastic_ternary_relation_workflow_v152(
        stage_count=spec["stage_count"], seed=seed
    )
    del witness
    state_order = list(range(10))
    action_order = list(range(6))
    random.Random(seed ^ 0x152B31).shuffle(state_order)
    random.Random(seed ^ 0x152C47).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    rule.opaque_mode,
                    seed * 100 + rule.destination_stage,
                    seed * 100 + rule.source_stage,
                    50 + (rule.source_stage % 3),
                    seed * 10_000 + key,
                    90 + ((rule.source_stage + key) % 2),
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )
    tokens = config["terminal_tokens"]

    def encode(state: RelationKeyedWorkflowState) -> tuple[int, ...]:
        status = tokens[
            "A" if state.status is RelationKeyedWorkflowStatus.ACTIVE else "S" if state.status is RelationKeyedWorkflowStatus.SUCCESS else "F"
        ]
        semantic = (
            seed * 100 + state.stage,
            state.completed,
            state.reserve,
            state.noise,
            state.elapsed,
            status,
            kernel.modulus,
            kernel.completion_target,
            seed * 100 + kernel.goal_stage,
            80_000 + (seed % 103),
        )
        return tuple(semantic[index] for index in state_order)

    return TernaryRelationWorkflowFlatAdapterV152(FAMILY, seed, kernel, catalogue, encode)


__all__ = (
    "FAMILY",
    "build_ternary_relation_workflow_adapter_v152",
    "ternary_relation_workflow_config_v152",
)
