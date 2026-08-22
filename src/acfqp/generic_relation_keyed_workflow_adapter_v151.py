"""Opaque flat adapter for the source-unseen relation-keyed workflow."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp.domains.stochastic_relation_keyed_workflow import (
    RelationKeyedWorkflowAction,
    RelationKeyedWorkflowState,
    RelationKeyedWorkflowStatus,
    generate_stochastic_relation_keyed_workflow,
    select_seeded_relation_keyed_workflow_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_packet_batching_adapter_v134 import packet_batching_config_v134


FAMILY = "STOCHASTIC_RELATION_KEYED_WORKFLOW_SOURCE_UNSEEN"


@dataclass(frozen=True, slots=True)
class RelationKeyedWorkflowFlatAdapterV151:
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

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        return select_seeded_relation_keyed_workflow_outcome_v1(
            self.kernel.step(state, RelationKeyedWorkflowAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def relation_keyed_workflow_config_v151() -> dict[str, Any]:
    config = copy.deepcopy(packet_batching_config_v134())
    config["families"][FAMILY] = {
        "stage_count": 8,
        "maximum_acquisition_labels": 1_536,
    }
    return config


def build_relation_keyed_workflow_adapter_v151(
    seed: int, config: Mapping[str, Any]
) -> RelationKeyedWorkflowFlatAdapterV151:
    spec = config["families"][FAMILY]
    kernel, witness = generate_stochastic_relation_keyed_workflow(
        stage_count=spec["stage_count"], seed=seed
    )
    del witness
    state_order = list(range(10))
    action_order = list(range(5))
    random.Random(seed ^ 0x151B31).shuffle(state_order)
    random.Random(seed ^ 0x151C47).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    rule.opaque_mode,
                    seed * 100 + rule.destination_stage,
                    seed * 100 + rule.source_stage,
                    40 + (rule.source_stage % 2),
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )
    tokens = config["terminal_tokens"]

    def encode(state: RelationKeyedWorkflowState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is RelationKeyedWorkflowStatus.ACTIVE
            else "S"
            if state.status is RelationKeyedWorkflowStatus.SUCCESS
            else "F"
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
            70_000 + (seed % 101),
        )
        return tuple(semantic[index] for index in state_order)

    return RelationKeyedWorkflowFlatAdapterV151(FAMILY, seed, kernel, catalogue, encode)


__all__ = (
    "FAMILY",
    "RelationKeyedWorkflowFlatAdapterV151",
    "build_relation_keyed_workflow_adapter_v151",
    "relation_keyed_workflow_config_v151",
)
