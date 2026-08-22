"""Opaque flat adapter for the V141-source-unseen maintenance-cascade family."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import random
from typing import Any, Mapping

from acfqp.domains.stochastic_maintenance_cascade import (
    MaintenanceCascadeAction,
    MaintenanceCascadeState,
    MaintenanceCascadeStatus,
    generate_stochastic_maintenance_cascade,
    select_seeded_maintenance_cascade_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_packet_batching_adapter_v134 import packet_batching_config_v134


FAMILY = "STOCHASTIC_MAINTENANCE_CASCADE_V141_SOURCE_UNSEEN"


@dataclass(frozen=True, slots=True)
class MaintenanceCascadeFlatAdapterV144:
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
        return action.task

    def action(self, key: int) -> Any:
        return MaintenanceCascadeAction(key)

    def active(self, state: Any) -> bool:
        return state.status is MaintenanceCascadeStatus.ACTIVE

    def success(self, state: Any) -> bool:
        return state.status is MaintenanceCascadeStatus.SUCCESS

    def probe_state(self, key: int) -> Any:
        rule = self.kernel.rules[key]
        return MaintenanceCascadeState(
            rule.source_zone,
            0,
            0,
            0,
            0,
            rule.source_zone,
            MaintenanceCascadeStatus.ACTIVE,
        )

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        return select_seeded_maintenance_cascade_outcome_v1(
            self.kernel.step(state, MaintenanceCascadeAction(key)),
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def maintenance_cascade_config_v144() -> dict[str, Any]:
    config = copy.deepcopy(packet_batching_config_v134())
    config["families"][FAMILY] = {
        "zone_count": 6,
        "repair_base": 2,
        "maximum_acquisition_labels": 1_024,
    }
    return config


def build_maintenance_cascade_adapter_v144(
    seed: int, config: Mapping[str, Any]
) -> MaintenanceCascadeFlatAdapterV144:
    spec = config["families"][FAMILY]
    kernel, witness = generate_stochastic_maintenance_cascade(
        zone_count=spec["zone_count"],
        repair_base=spec["repair_base"],
        seed=seed,
    )
    del witness
    state_order = list(range(10))
    action_order = list(range(6))
    random.Random(seed ^ 0x144A61).shuffle(state_order)
    random.Random(seed ^ 0x144B73).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + rule.source_zone,
                    seed * 100 + rule.destination_zone,
                    rule.repair_increment,
                    rule.spare_increment,
                    rule.hazard_increment,
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )
    tokens = config["terminal_tokens"]

    def encode(state: MaintenanceCascadeState) -> tuple[int, ...]:
        status = tokens[
            "A"
            if state.status is MaintenanceCascadeStatus.ACTIVE
            else "S"
            if state.status is MaintenanceCascadeStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.zone,
            state.repaired_units,
            state.spare_units,
            state.latent_load,
            state.hazard,
            state.elapsed,
            status,
            kernel.hazard_capacity,
            kernel.repair_target,
            seed * 100 + kernel.goal_zone,
        )
        return tuple(semantic[index] for index in state_order)

    return MaintenanceCascadeFlatAdapterV144(
        FAMILY, seed, kernel, catalogue, encode
    )


__all__ = (
    "FAMILY",
    "MaintenanceCascadeFlatAdapterV144",
    "build_maintenance_cascade_adapter_v144",
    "maintenance_cascade_config_v144",
)
