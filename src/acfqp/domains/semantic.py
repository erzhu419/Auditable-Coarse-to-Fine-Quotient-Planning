"""Fixed, auditable Phase-0.5 semantic-action adapters.

The vertical slice deliberately uses a small restricted action vocabulary:
``canonical:first`` and ``canonical:last`` denote the first and last primitive
actions in a domain kernel's authoritative order.  If there is only one legal
primitive action, the labels are deduplicated to ``canonical:first``.  This is
not claimed to be a sufficient semantic action basis; it makes the restriction
explicit so the unrestricted ground envelope can audit it.

``restriction_diagnostic`` lists primitives omitted by this vocabulary.  Its
evidence level is ``diagnostic_only``: without a J0 comparison it is neither an
action-restriction value gap nor a regret certificate.

All strategic features below are atomic functions of the current state and
fixed kernel structure.  They contain no policy, value, Q, rollout, or oracle
information, and are returned as exact reduced rationals for stable predicate
threshold identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Generic, Hashable, Protocol, TypeVar, runtime_checkable

from acfqp.core import ActionT, FiniteKernel, StateT
from acfqp.domains.g2048 import G2048Action, G2048Kernel, G2048State
from acfqp.domains.matching_buffer import LMBAction, LMBKernel, LMBState


LabelT = TypeVar("LabelT", bound=Hashable)
FeatureVector = tuple[tuple[str, Fraction], ...]
ActionDistribution = tuple[tuple[Fraction, ActionT], ...]


class BoundaryActionLabel(str, Enum):
    FIRST = "canonical:first"
    LAST = "canonical:last"


@runtime_checkable
class SemanticActionAdapter(Protocol[StateT, ActionT, LabelT]):
    """Ground-independent interface consumed by quotient construction."""

    def labels(
        self, kernel: FiniteKernel[StateT, ActionT], state: StateT
    ) -> tuple[LabelT, ...]:
        """Return available semantic labels in canonical order."""

    def concretize(
        self,
        kernel: FiniteKernel[StateT, ActionT],
        state: StateT,
        label: LabelT,
    ) -> ActionDistribution[ActionT]:
        """Return an exact distribution over legal primitive actions."""

    def features(
        self, kernel: FiniteKernel[StateT, ActionT], state: StateT
    ) -> FeatureVector:
        """Return current-state atomic strategic features."""


@dataclass(frozen=True, slots=True)
class ActionRestrictionDiagnostic(Generic[ActionT, LabelT]):
    primitive_actions: tuple[ActionT, ...]
    semantic_labels: tuple[LabelT, ...]
    represented_actions: tuple[ActionT, ...]
    omitted_actions: tuple[ActionT, ...]
    evidence_level: str = "diagnostic_only"

    @property
    def restriction_active(self) -> bool:
        return bool(self.omitted_actions)


class _BoundaryAdapter(Generic[StateT, ActionT]):
    """Shared fixed first/last vocabulary and exact concretizer."""

    def labels(
        self, kernel: FiniteKernel[StateT, ActionT], state: StateT
    ) -> tuple[BoundaryActionLabel, ...]:
        primitive_actions = tuple(kernel.actions(state))
        if not primitive_actions:
            if kernel.is_terminal(state):
                return ()
            raise RuntimeError(
                "an active state has no primitive action; the domain kernel "
                "must classify dead ends as terminal failure"
            )
        if len(primitive_actions) == 1:
            return (BoundaryActionLabel.FIRST,)
        return (BoundaryActionLabel.FIRST, BoundaryActionLabel.LAST)

    def concretize(
        self,
        kernel: FiniteKernel[StateT, ActionT],
        state: StateT,
        label: BoundaryActionLabel,
    ) -> ActionDistribution[ActionT]:
        available_labels = self.labels(kernel, state)
        if label not in available_labels:
            raise ValueError(f"semantic action {label!r} is unavailable in this state")
        primitive_actions = tuple(kernel.actions(state))
        action = (
            primitive_actions[0]
            if label is BoundaryActionLabel.FIRST
            else primitive_actions[-1]
        )
        return ((Fraction(1), action),)


def restriction_diagnostic(
    adapter: SemanticActionAdapter[StateT, ActionT, LabelT],
    kernel: FiniteKernel[StateT, ActionT],
    state: StateT,
) -> ActionRestrictionDiagnostic[ActionT, LabelT]:
    """Expose syntactically omitted actions without estimating their value."""

    primitive_actions = tuple(kernel.actions(state))
    labels = adapter.labels(kernel, state)
    represented: list[ActionT] = []
    for label in labels:
        distribution = adapter.concretize(kernel, state, label)
        mass = sum((probability for probability, _ in distribution), Fraction(0))
        if mass != 1:
            raise ValueError(f"concretizer distribution for {label!r} has mass {mass}")
        for probability, action in distribution:
            if probability <= 0:
                raise ValueError("concretizer probabilities must be positive")
            if action not in primitive_actions:
                raise ValueError("concretizer emitted an unavailable primitive action")
            if action not in represented:
                represented.append(action)
    omitted = tuple(action for action in primitive_actions if action not in represented)
    return ActionRestrictionDiagnostic(
        primitive_actions,
        labels,
        tuple(represented),
        omitted,
    )


def _feature_vector(**features: int | Fraction) -> FeatureVector:
    """Canonicalize names and values for deterministic predicate generation."""

    return tuple((name, Fraction(value)) for name, value in sorted(features.items()))


@dataclass(frozen=True, slots=True)
class G2048SemanticAdapter(_BoundaryAdapter[G2048State, G2048Action]):
    """Boundary labels plus geometry/capacity features for G2048-Select."""

    def features(self, kernel: G2048Kernel, state: G2048State) -> FeatureVector:
        primitive_actions = tuple(kernel.actions(state))
        occupied = sum(rank != 0 for rank in state.board)
        empty = kernel.cell_count - occupied

        rank_counts: dict[int, int] = {}
        for rank in state.board:
            if rank:
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
        debts = tuple(
            Fraction((2 - rank_counts.get(rank, 0) % 2) % 2, 2)
            for rank in range(1, kernel.rank_cap + 1)
        )
        immediately_matchable_cells = {
            cell
            for action in primitive_actions
            for cell in (action.first, action.second)
        }

        # Every primitive merge releases exactly one board cell before the
        # mandatory exogenous spawn, so the controlled-transition L1 gain is
        # exactly 1 / cell_count whenever an action exists.
        outcomes_per_action = (empty + 1) * len(kernel.spawn_distribution)
        return _feature_vector(
            action_count=len(primitive_actions),
            branching_count=len(primitive_actions) * outcomes_per_action,
            capacity_slack=Fraction(empty, kernel.cell_count),
            empty_count=empty,
            immediate_release_liquidity=(
                Fraction(1, kernel.cell_count) if primitive_actions else Fraction(0)
            ),
            match_debt_mean=sum(debts, Fraction(0)) / len(debts),
            match_debt_min=min(debts),
            match_debt_nonzero_types=sum(debt > 0 for debt in debts),
            max_rank=max(rank_counts, default=0),
            min_rank=min(rank_counts, default=0),
            occupied_count=occupied,
            rank_sum=sum(state.board),
            spatial_match_debt=occupied - len(immediately_matchable_cells),
        )


@dataclass(frozen=True, slots=True)
class LMBSemanticAdapter(_BoundaryAdapter[LMBState, LMBAction]):
    """Boundary labels plus buffer/debt features for Layered Matching Buffer."""

    def features(self, kernel: LMBKernel, state: LMBState) -> FeatureVector:
        primitive_actions = tuple(kernel.actions(state))
        occupancy = sum(state.buffer)
        debt_by_type = tuple(
            Fraction((3 - count % 3) % 3, 3) for count in state.buffer
        )
        immediately_releasing = sum(
            state.buffer[kernel.tile_types[action.tile]] == 2
            for action in primitive_actions
        )
        removed = state.removed_mask.bit_count()

        return _feature_vector(
            action_count=len(primitive_actions),
            branching_count=len(primitive_actions),
            buffer_occupancy=occupancy,
            capacity_slack=(
                Fraction(kernel.capacity - occupancy, kernel.capacity)
                if kernel.capacity
                else Fraction(0)
            ),
            capacity_slack_count=kernel.capacity - occupancy,
            immediate_release_liquidity=(
                Fraction(2 * immediately_releasing, kernel.capacity * len(primitive_actions))
                if primitive_actions and kernel.capacity
                else Fraction(0)
            ),
            match_debt_mean=sum(debt_by_type, Fraction(0)) / len(debt_by_type),
            match_debt_min=min(debt_by_type),
            match_debt_nonzero_types=sum(debt > 0 for debt in debt_by_type),
            max_match_debt=max(debt_by_type, default=Fraction(0)),
            remaining_object_count=kernel.tile_count - removed,
        )
