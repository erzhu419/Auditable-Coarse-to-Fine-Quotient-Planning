"""Opaque adapter for V153 observation-backed relational-prior evaluation."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp.domains.stochastic_relation_keyed_workflow import RelationKeyedWorkflowAction, RelationKeyedWorkflowState, RelationKeyedWorkflowStatus
from acfqp.domains.stochastic_quaternary_relation_workflow_v153 import generate_stochastic_quaternary_relation_workflow_v153, select_seeded_quaternary_relation_workflow_outcome_v153
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_packet_batching_adapter_v134 import packet_batching_config_v134


FAMILY = "STOCHASTIC_QUATERNARY_RELATION_WORKFLOW_SOURCE_UNSEEN"


@dataclass(frozen=True, slots=True)
class QuaternaryRelationWorkflowFlatAdapterV153:
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
        return action.rule

    def action(self, key):
        return RelationKeyedWorkflowAction(key)

    def active(self, state):
        return state.status is RelationKeyedWorkflowStatus.ACTIVE

    def success(self, state):
        return state.status is RelationKeyedWorkflowStatus.SUCCESS

    def probe_state(self, key):
        rule = self.kernel.rules[key]
        return RelationKeyedWorkflowState(rule.source_stage, 0, 0, 0, 0, RelationKeyedWorkflowStatus.ACTIVE)

    def select_outcome(self, state, key, episode_index, decision_index):
        return select_seeded_quaternary_relation_workflow_outcome_v153(
            self.kernel.step(state, RelationKeyedWorkflowAction(key)), seed=self.seed, episode_index=episode_index, decision_index=decision_index
        )


def quaternary_relation_workflow_config_v153():
    config = copy.deepcopy(packet_batching_config_v134())
    config["families"][FAMILY] = {"stage_count": 5, "maximum_acquisition_labels": 1_536}
    return config


def build_quaternary_relation_workflow_adapter_v153(seed: int, config: Mapping[str, Any]):
    kernel, witness = generate_stochastic_quaternary_relation_workflow_v153(stage_count=config["families"][FAMILY]["stage_count"], seed=seed)
    del witness
    state_order = list(range(10))
    action_order = list(range(6))
    random.Random(seed ^ 0x153B31).shuffle(state_order)
    random.Random(seed ^ 0x153C47).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple((rule.opaque_mode, seed * 100 + rule.destination_stage, seed * 100 + rule.source_stage, 60 + (rule.source_stage % 4), seed * 10_000 + key, 100 + ((rule.source_stage + key) % 3))[index] for index in action_order),
        )
        for key, rule in enumerate(kernel.rules)
    )
    tokens = config["terminal_tokens"]

    def encode(state: RelationKeyedWorkflowState):
        status = tokens["A" if state.status is RelationKeyedWorkflowStatus.ACTIVE else "S" if state.status is RelationKeyedWorkflowStatus.SUCCESS else "F"]
        semantic = (seed * 100 + state.stage, state.completed, state.reserve, state.noise, state.elapsed, status, kernel.modulus, kernel.completion_target, seed * 100 + kernel.goal_stage, 90_000 + (seed % 107))
        return tuple(semantic[index] for index in state_order)

    return QuaternaryRelationWorkflowFlatAdapterV153(FAMILY, seed, kernel, catalogue, encode)


__all__ = ("FAMILY", "build_quaternary_relation_workflow_adapter_v153", "quaternary_relation_workflow_config_v153")
