"""Opaque flat adapter for the source-unseen dual-budget domain V119."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp import construction_k7_fourth_family_inventory_preregistration_v118 as previous
from acfqp.domains.stochastic_dual_budget_composition import (
    DualBudgetAction,
    DualBudgetState,
    DualBudgetStatus,
    generate_stochastic_dual_budget_composition,
    select_seeded_dual_budget_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4


FAMILY = "STOCHASTIC_DUAL_BUDGET_COMPOSITION"


@dataclass(frozen=True, slots=True)
class DualBudgetFlatAdapterV119:
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
        return DualBudgetAction(key)

    def active(self, state: Any) -> bool:
        return state.status is DualBudgetStatus.ACTIVE

    def success(self, state: Any) -> bool:
        return state.status is DualBudgetStatus.SUCCESS

    def probe_state(self, key: int) -> Any:
        rule = self.kernel.rules[key]
        return DualBudgetState(
            rule.source_stage,
            0,
            0,
            0,
            0,
            DualBudgetStatus.ACTIVE,
        )

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        return select_seeded_dual_budget_outcome_v1(
            self.kernel.step(state, DualBudgetAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def dual_budget_config_v119() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v118())
    config["families"][FAMILY] = {
        "stage_count": 7,
        "maximum_acquisition_labels": 320,
    }
    return config


def build_dual_budget_adapter_v119(
    seed: int, config: Mapping[str, Any]
) -> DualBudgetFlatAdapterV119:
    spec = config["families"][FAMILY]
    kernel, witness = generate_stochastic_dual_budget_composition(
        stage_count=spec["stage_count"], seed=seed
    )
    del witness
    state_order = list(range(10))
    action_order = list(range(7))
    random.Random(seed ^ 0x119A53).shuffle(state_order)
    random.Random(seed ^ 0x119B67).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + rule.source_stage,
                    seed * 100 + rule.destination_stage,
                    rule.primary_increment,
                    rule.reserve_increment,
                    rule.hazard_increment,
                    rule.checksum_multiplier,
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )
    tokens = config["terminal_tokens"]

    def encode(state: DualBudgetState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is DualBudgetStatus.ACTIVE
            else "S"
            if state.status is DualBudgetStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.stage,
            state.primary,
            state.reserve,
            state.hazard,
            state.checksum,
            status,
            kernel.hazard_capacity,
            kernel.target_primary,
            kernel.target_reserve,
            seed * 100 + kernel.goal_stage,
        )
        return tuple(semantic[index] for index in state_order)

    return DualBudgetFlatAdapterV119(FAMILY, seed, kernel, catalogue, encode)


__all__ = (
    "FAMILY",
    "DualBudgetFlatAdapterV119",
    "build_dual_budget_adapter_v119",
    "dual_budget_config_v119",
)
