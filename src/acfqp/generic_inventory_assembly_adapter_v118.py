"""Anonymous flat adapter for the distinct inventory-assembly domain V118."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp import construction_k7_dependency_derived_program_branch_preregistration_v117 as previous
from acfqp.domains.stochastic_inventory_assembly import (
    InventoryAssemblyAction,
    InventoryAssemblyState,
    InventoryAssemblyStatus,
    generate_stochastic_inventory_assembly,
    select_seeded_inventory_assembly_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4


FAMILY = "STOCHASTIC_INVENTORY_ASSEMBLY"


@dataclass(frozen=True, slots=True)
class InventoryAssemblyFlatAdapterV118:
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
        return action.recipe

    def action(self, key: int) -> Any:
        return InventoryAssemblyAction(key)

    def active(self, state: Any) -> bool:
        return state.status is InventoryAssemblyStatus.ACTIVE

    def success(self, state: Any) -> bool:
        return state.status is InventoryAssemblyStatus.SUCCESS

    def probe_state(self, key: int) -> Any:
        recipe = self.kernel.recipes[key]
        return InventoryAssemblyState(
            recipe.source_stage,
            0,
            0,
            InventoryAssemblyStatus.ACTIVE,
        )

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        return select_seeded_inventory_assembly_outcome_v1(
            self.kernel.step(state, InventoryAssemblyAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def inventory_assembly_config_v118() -> dict[str, Any]:
    config = copy.deepcopy(previous.campaign_config_v117())
    config["families"][FAMILY] = {
        "stage_count": 7,
        "maximum_acquisition_labels": 240,
    }
    return config


def build_inventory_assembly_adapter_v118(
    seed: int,
    config: Mapping[str, Any],
) -> InventoryAssemblyFlatAdapterV118:
    spec = config["families"][FAMILY]
    kernel, witness = generate_stochastic_inventory_assembly(
        stage_count=spec["stage_count"], seed=seed
    )
    del witness
    state_order = list(range(7))
    action_order = list(range(5))
    random.Random(seed ^ 0x118A31).shuffle(state_order)
    random.Random(seed ^ 0x118B43).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + recipe.source_stage,
                    seed * 100 + recipe.destination_stage,
                    recipe.produced_units,
                    recipe.contamination_increment,
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, recipe in enumerate(kernel.recipes)
    )
    tokens = config["terminal_tokens"]

    def encode(state: InventoryAssemblyState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is InventoryAssemblyStatus.ACTIVE
            else "S"
            if state.status is InventoryAssemblyStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.stage,
            state.units,
            state.contamination,
            status,
            kernel.contamination_capacity,
            kernel.target_units,
            seed * 100 + kernel.goal_stage,
        )
        return tuple(semantic[index] for index in state_order)

    return InventoryAssemblyFlatAdapterV118(
        FAMILY, seed, kernel, catalogue, encode
    )


__all__ = (
    "FAMILY",
    "InventoryAssemblyFlatAdapterV118",
    "build_inventory_assembly_adapter_v118",
    "inventory_assembly_config_v118",
)
