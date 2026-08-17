"""Finite stochastic inventory-assembly kernel.

This domain is intentionally unrelated to graph phase routing.  A controller
chooses a recipe at the current assembly stage.  The recipe deterministically
changes produced units and advances the stage, while contamination has a
two-point support.  The kernel exposes ground transitions only; it does not
provide an abstract state, factorization, certificate, or planner.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import random

from acfqp.core import Outcome


class InventoryAssemblyStatus(str, Enum):
    ACTIVE = "active"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, order=True, slots=True)
class InventoryAssemblyState:
    stage: int
    units: int
    contamination: int
    status: InventoryAssemblyStatus = InventoryAssemblyStatus.ACTIVE


@dataclass(frozen=True, order=True, slots=True)
class InventoryAssemblyAction:
    recipe: int


@dataclass(frozen=True, slots=True)
class InventoryAssemblyRecipe:
    source_stage: int
    destination_stage: int
    produced_units: int
    contamination_increment: int
    high_contamination_probability: Fraction


@dataclass(frozen=True, slots=True)
class InventoryAssemblyGenerationEvidence:
    seed: int
    robust_recipe_path: tuple[int, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class InventoryAssemblyKernel:
    stage_count: int
    contamination_capacity: int
    target_units: int
    recipes: tuple[InventoryAssemblyRecipe, ...]

    def __post_init__(self) -> None:
        if self.stage_count < 4 or self.contamination_capacity <= 0:
            raise ValueError("inventory assembly dimensions changed")
        if self.target_units <= 0 or not self.recipes:
            raise ValueError("inventory assembly target or recipe set changed")
        for recipe in self.recipes:
            if not 0 <= recipe.source_stage < recipe.destination_stage < self.stage_count:
                raise ValueError("inventory recipe must advance through the assembly DAG")
            if recipe.produced_units <= 0 or recipe.contamination_increment <= 0:
                raise ValueError("inventory recipe increments changed")
            if not 0 < recipe.high_contamination_probability < 1:
                raise ValueError("inventory recipe probability changed")
        for stage in range(self.stage_count - 1):
            if not any(recipe.source_stage == stage for recipe in self.recipes):
                raise ValueError("every nonterminal assembly stage needs a recipe")

    @property
    def goal_stage(self) -> int:
        return self.stage_count - 1

    def initial_distribution(self) -> tuple[tuple[Fraction, InventoryAssemblyState], ...]:
        return ((Fraction(1), InventoryAssemblyState(0, 0, 0)),)

    def actions(self, state: InventoryAssemblyState) -> tuple[InventoryAssemblyAction, ...]:
        self._validate_state(state)
        if state.status is not InventoryAssemblyStatus.ACTIVE:
            return ()
        return tuple(
            InventoryAssemblyAction(index)
            for index, recipe in enumerate(self.recipes)
            if recipe.source_stage == state.stage
        )

    def step(
        self,
        state: InventoryAssemblyState,
        action: InventoryAssemblyAction,
    ) -> tuple[Outcome[InventoryAssemblyState], ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise ValueError("inventory assembly action is not legal")
        recipe = self.recipes[action.recipe]
        units = state.units + recipe.produced_units
        outcomes = []
        for increment, probability in (
            (0, 1 - recipe.high_contamination_probability),
            (recipe.contamination_increment, recipe.high_contamination_probability),
        ):
            contamination = state.contamination + increment
            if contamination > self.contamination_capacity:
                status = InventoryAssemblyStatus.FAILURE
            elif recipe.destination_stage == self.goal_stage:
                status = (
                    InventoryAssemblyStatus.SUCCESS
                    if units == self.target_units
                    else InventoryAssemblyStatus.FAILURE
                )
            else:
                status = InventoryAssemblyStatus.ACTIVE
            successor = InventoryAssemblyState(
                recipe.destination_stage,
                units,
                contamination,
                status,
            )
            outcomes.append(
                Outcome(
                    probability,
                    successor,
                    (),
                    failure=status is InventoryAssemblyStatus.FAILURE,
                    terminal=status is not InventoryAssemblyStatus.ACTIVE,
                )
            )
        return tuple(outcomes)

    def _validate_state(self, state: InventoryAssemblyState) -> None:
        if not 0 <= state.stage < self.stage_count:
            raise ValueError("inventory assembly stage changed")
        if state.units < 0 or state.contamination < 0:
            raise ValueError("inventory assembly counters changed")


def select_seeded_inventory_assembly_outcome_v1(
    outcomes: tuple[Outcome[InventoryAssemblyState], ...],
    *,
    seed: int,
    episode_index: int,
    decision_index: int,
) -> tuple[Outcome[InventoryAssemblyState], str]:
    if not outcomes or sum((row.probability for row in outcomes), Fraction()) != 1:
        raise ValueError("inventory assembly outcome distribution changed")
    tape = hashlib.sha256(
        b"acfqp:inventory-assembly-outcome:v1\x00"
        + str(seed).encode("ascii")
        + b"\x00"
        + str(episode_index).encode("ascii")
        + b"\x00"
        + str(decision_index).encode("ascii")
    ).digest()
    draw = Fraction(int.from_bytes(tape, "big"), 1 << (8 * len(tape)))
    cumulative = Fraction()
    for outcome in outcomes:
        cumulative += outcome.probability
        if draw < cumulative:
            return outcome, tape.hex()
    raise AssertionError("inventory assembly draw escaped a unit distribution")


def generate_stochastic_inventory_assembly(
    *,
    stage_count: int,
    seed: int,
) -> tuple[InventoryAssemblyKernel, InventoryAssemblyGenerationEvidence]:
    if stage_count < 4:
        raise ValueError("inventory assembly generator dimensions changed")
    rng = random.Random(seed)
    probabilities = (Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
    path_yields = [3 + rng.randrange(3) for _ in range(stage_count - 1)]
    path_hazards = [1 + rng.randrange(2) for _ in range(stage_count - 1)]
    target_units = sum(path_yields)
    capacity = sum(path_hazards) + 1
    if capacity == target_units:
        capacity += 1
    recipes: list[InventoryAssemblyRecipe] = []
    path_old_indices = []
    for stage in range(stage_count - 1):
        path_old_indices.append(len(recipes))
        recipes.append(
            InventoryAssemblyRecipe(
                stage,
                stage + 1,
                path_yields[stage],
                path_hazards[stage],
                probabilities[(seed + stage) % len(probabilities)],
            )
        )
        if stage + 2 < stage_count:
            # A witness-blind planner may use this shortcut only when the
            # remaining unit equation still closes exactly at the goal.
            shortcut_yield = path_yields[stage] + path_yields[stage + 1]
            if (seed + stage) % 2:
                shortcut_yield += 1
            recipes.append(
                InventoryAssemblyRecipe(
                    stage,
                    stage + 2,
                    shortcut_yield,
                    2 + path_hazards[stage],
                    probabilities[(seed + stage + 1) % len(probabilities)],
                )
            )
    order = list(range(len(recipes)))
    rng.shuffle(order)
    shuffled = tuple(recipes[index] for index in order)
    old_to_new = {old: new for new, old in enumerate(order)}
    robust_path = tuple(old_to_new[index] for index in path_old_indices)
    kernel = InventoryAssemblyKernel(
        stage_count=stage_count,
        contamination_capacity=capacity,
        target_units=target_units,
        recipes=shuffled,
    )
    state = kernel.initial_distribution()[0][1]
    for recipe_index in robust_path:
        outcomes = kernel.step(state, InventoryAssemblyAction(recipe_index))
        state = max(outcomes, key=lambda row: row.next_state.contamination).next_state
    if state.status is not InventoryAssemblyStatus.SUCCESS:
        raise AssertionError("generated inventory assembly robust path is not successful")
    return kernel, InventoryAssemblyGenerationEvidence(seed, robust_path, True)


__all__ = (
    "InventoryAssemblyAction",
    "InventoryAssemblyGenerationEvidence",
    "InventoryAssemblyKernel",
    "InventoryAssemblyRecipe",
    "InventoryAssemblyState",
    "InventoryAssemblyStatus",
    "generate_stochastic_inventory_assembly",
    "select_seeded_inventory_assembly_outcome_v1",
)
