"""Matched decision-point evidence for the exploratory 2048 V2 pilot.

The state-library lane is independent of every learned policy.  It follows a
fixed legal-action priority on a fixed tape and retains the first qualifying
state from each episode.  A policy is then observed for exactly eight accepted
actions from each retained physical board on a second fixed tape.  All feature
coordinates use only those nine observed states, the eight observed actions,
their merge scores, and deterministic pre-spawn swipes.  No state is
canonicalized and no future spawn or game outcome is consulted.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any, NoReturn

from acfqp.domains import standard_2048
from acfqp.science import early_strategic_signature_2048_pilot_v1 as v1
from acfqp.science.latent_resource_2048_v1 import (
    STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1,
)
from acfqp.science.matched_2048_env_v1 import (
    initial_state_v1,
    legal_action_mask_v1,
    transition_v1,
)


DECISION_STATE_COUNT_V2 = 64
DECISION_STATE_LIBRARY_TAPE_ROOT_V2 = "acfqp-decision-point-state-library-v2"
DECISION_PREFIX_TAPE_ROOT_V2 = "acfqp-decision-point-prefix-v2"
DECISION_PREFIX_ACTION_COUNT_V2 = 8
GENERATOR_ACTION_PRIORITY_V2 = (1, 2, 3, 0)  # DOWN, LEFT, RIGHT, UP
GENERATOR_MAX_EPISODES_V2 = 1_000
GENERATOR_MAX_DECISIONS_PER_EPISODE_V2 = 20_000
MINIMUM_DECISION_MAXIMUM_RANK_V2 = 6
MINIMUM_DECISION_EMPTY_CELL_COUNT_V2 = 8

RAW_PREFIX_DIMENSION_V2 = 184
ROTATED_REDUNDANCY_DIMENSION_V2 = 64
DECISION_STRATEGIC_APPEND_DIMENSION_V2 = 64
AUGMENTED_PREFIX_DIMENSION_V2 = 248
RAW_PREFIX_ARM_V2 = v1.RAW_PREFIX_ARM_V1
ROTATED_PREFIX_ARM_V2 = v1.ROTATED_PREFIX_ARM_V1
STRATEGIC_PREFIX_ARM_V2 = v1.STRATEGIC_PREFIX_ARM_V1
DECISION_PREFIX_ARMS_V2 = (
    RAW_PREFIX_ARM_V2,
    ROTATED_PREFIX_ARM_V2,
    STRATEGIC_PREFIX_ARM_V2,
)

# The first three entries describe corner opportunities: a state whose unique
# maximum remains in the initially retained corner and whose legal actions can
# both preserve and break that anchor.  The next three independently compare
# the chosen action with every legal action at each of all eight observed
# states.  Regret is normalized by that state's observable-quality span; a
# zero-span state has zero regret.  No corner-opportunity guard enters them.
DECISION_SUMMARY_NAMES_V2 = (
    "corner_opportunity_fraction",
    "chosen_corner_preservation_fraction",
    "corner_break_fraction",
    "mean_opportunity_normalized_resource_regret",
    "maximum_opportunity_normalized_resource_regret",
    "resource_optimal_action_match_fraction",
    "maximum_tile_corner_residence",
    "initial_anchor_corner_residence",
    "maximum_tile_corner_switch_count",
    "maximum_tile_displacement_count",
    "maximum_rank_gain",
    "prefix_merge_score",
    "minimum_empty_slack",
    "minimum_directional_flow_liquidity",
    "maximum_irreversibility_risk",
    "observed_prefix_terminal",
)

_CORNERS = (0, 3, 12, 15)


class DecisionPointSignature2048PilotV2Error(ValueError):
    """A frozen state, prefix, model, or evidence contract is invalid."""


def _fail(message: str) -> NoReturn:
    raise DecisionPointSignature2048PilotV2Error(message)


ActionSelectorV2 = Callable[
    [standard_2048.Swipe2048State, tuple[bool, bool, bool, bool]], int
]


def _maximum_tile_destination_v2(
    board: tuple[int, ...], action_index: int, maximum_cell: int
) -> int:
    """Track the unique maximum tile itself through one deterministic swipe."""

    action = standard_2048.ACTION_ORDER[action_index]
    if board.count(board[maximum_cell]) != 1:
        _fail("maximum-tile transport requires a unique maximum")
    if action is standard_2048.Swipe2048Action.UP:
        line = tuple(maximum_cell % 4 + 4 * row for row in range(4))
    elif action is standard_2048.Swipe2048Action.DOWN:
        line = tuple(maximum_cell % 4 + 4 * row for row in range(3, -1, -1))
    elif action is standard_2048.Swipe2048Action.LEFT:
        row_start = maximum_cell // 4 * 4
        line = tuple(row_start + column for column in range(4))
    elif action is standard_2048.Swipe2048Action.RIGHT:
        row_start = maximum_cell // 4 * 4
        line = tuple(row_start + column for column in range(3, -1, -1))
    else:  # pragma: no cover - exact enum exhaustiveness
        raise AssertionError("standard 2048 action order changed")
    values = [(board[cell], cell == maximum_cell) for cell in line if board[cell]]
    merged: list[tuple[int, bool]] = []
    index = 0
    while index < len(values):
        rank, tagged = values[index]
        if index + 1 < len(values) and values[index + 1][0] == rank:
            other_tagged = values[index + 1][1]
            if tagged or other_tagged:
                raise AssertionError("a unique maximum tile unexpectedly merged")
            merged.append((rank + 1, False))
            index += 2
        else:
            merged.append((rank, tagged))
            index += 1
    destinations = [line[index] for index, (_rank, tagged) in enumerate(merged) if tagged]
    if len(destinations) != 1:
        raise AssertionError("unique maximum-tile transport lost its identity")
    return destinations[0]


def _action_partition_v2(
    state: standard_2048.Swipe2048State,
    *,
    anchor_corner: int | None = None,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    """Return legal, anchor-preserving, and anchor-breaking action indices."""

    if type(state) is not standard_2048.Swipe2048State:
        _fail("decision action partition requires one exact state")
    board = state.board
    maximum = max(board)
    maximum_cells = tuple(index for index, rank in enumerate(board) if rank == maximum)
    if anchor_corner is None:
        if len(maximum_cells) != 1 or maximum_cells[0] not in _CORNERS:
            return (), (), ()
        anchor_corner = maximum_cells[0]
    if type(anchor_corner) is not int or anchor_corner not in _CORNERS:
        _fail("decision anchor corner changed")
    legal = tuple(
        index
        for index, allowed in enumerate(legal_action_mask_v1(state))
        if allowed
    )
    if (
        state.status is not standard_2048.Swipe2048Status.ACTIVE
        or len(maximum_cells) != 1
        or maximum_cells[0] != anchor_corner
    ):
        return legal, (), ()
    preserving: list[int] = []
    breaking: list[int] = []
    for action_index in legal:
        destination = _maximum_tile_destination_v2(
            board, action_index, anchor_corner
        )
        target = preserving if destination == anchor_corner else breaking
        target.append(action_index)
    return legal, tuple(preserving), tuple(breaking)


def is_eligible_decision_state_v2(
    state: standard_2048.Swipe2048State,
) -> bool:
    """Whether ``state`` has the exact preregistered corner decision."""

    if type(state) is not standard_2048.Swipe2048State:
        return False
    board = state.board
    maximum = max(board)
    maximum_cells = tuple(index for index, rank in enumerate(board) if rank == maximum)
    if (
        state.status is not standard_2048.Swipe2048Status.ACTIVE
        or maximum < MINIMUM_DECISION_MAXIMUM_RANK_V2
        or len(maximum_cells) != 1
        or maximum_cells[0] not in _CORNERS
        or board.count(0) < MINIMUM_DECISION_EMPTY_CELL_COUNT_V2
    ):
        return False
    legal, preserving, breaking = _action_partition_v2(state)
    return len(legal) >= 2 and bool(preserving) and bool(breaking)


@dataclass(frozen=True, slots=True)
class FrozenDecisionStateV2:
    """One physical state plus its independent generator occurrence metadata."""

    state_index: int
    board: tuple[int, ...]
    generator_episode_index: int
    generator_decision_index: int
    generator_preceding_tape_digest: str
    maximum_rank: int
    maximum_corner_cell: int
    empty_cell_count: int
    legal_action_indices: tuple[int, ...]
    corner_preserving_action_indices: tuple[int, ...]
    corner_breaking_action_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            type(self.state_index) is not int
            or self.state_index < 0
            or type(self.generator_episode_index) is not int
            or self.generator_episode_index < 0
            or type(self.generator_decision_index) is not int
            or self.generator_decision_index <= 0
            or type(self.generator_preceding_tape_digest) is not str
            or len(self.generator_preceding_tape_digest) != 64
        ):
            _fail("frozen decision occurrence metadata changed")
        standard_2048.validate_board_v1(self.board)
        state = standard_2048.state_from_board_v1(self.board)
        if not is_eligible_decision_state_v2(state):
            _fail("frozen board is not an eligible decision state")
        legal, preserving, breaking = _action_partition_v2(state)
        maximum = max(self.board)
        maximum_corner = self.board.index(maximum)
        if (
            self.maximum_rank != maximum
            or self.maximum_corner_cell != maximum_corner
            or self.empty_cell_count != self.board.count(0)
            or self.legal_action_indices != legal
            or self.corner_preserving_action_indices != preserving
            or self.corner_breaking_action_indices != breaking
        ):
            _fail("frozen decision metadata disagrees with its physical board")

    @classmethod
    def from_state(
        cls,
        *,
        state_index: int,
        state: standard_2048.Swipe2048State,
        generator_episode_index: int,
        generator_decision_index: int,
        generator_preceding_tape_digest: str,
    ) -> "FrozenDecisionStateV2":
        if not is_eligible_decision_state_v2(state):
            _fail("cannot freeze a non-eligible decision state")
        legal, preserving, breaking = _action_partition_v2(state)
        maximum = max(state.board)
        return cls(
            state_index=state_index,
            board=state.board,
            generator_episode_index=generator_episode_index,
            generator_decision_index=generator_decision_index,
            generator_preceding_tape_digest=generator_preceding_tape_digest,
            maximum_rank=maximum,
            maximum_corner_cell=state.board.index(maximum),
            empty_cell_count=state.board.count(0),
            legal_action_indices=legal,
            corner_preserving_action_indices=preserving,
            corner_breaking_action_indices=breaking,
        )

    def to_document(self) -> dict[str, Any]:
        return {
            "state_index": self.state_index,
            "board": list(self.board),
            "generator_episode_index": self.generator_episode_index,
            "generator_decision_index": self.generator_decision_index,
            "generator_preceding_tape_digest": self.generator_preceding_tape_digest,
            "maximum_rank": self.maximum_rank,
            "maximum_corner_cell": self.maximum_corner_cell,
            "empty_cell_count": self.empty_cell_count,
            "legal_action_indices": list(self.legal_action_indices),
            "corner_preserving_action_indices": list(
                self.corner_preserving_action_indices
            ),
            "corner_breaking_action_indices": list(self.corner_breaking_action_indices),
        }

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> "FrozenDecisionStateV2":
        expected = {
            "state_index",
            "board",
            "generator_episode_index",
            "generator_decision_index",
            "generator_preceding_tape_digest",
            "maximum_rank",
            "maximum_corner_cell",
            "empty_cell_count",
            "legal_action_indices",
            "corner_preserving_action_indices",
            "corner_breaking_action_indices",
        }
        if not isinstance(document, Mapping) or set(document) != expected:
            _fail("frozen decision document fields changed")
        try:
            return cls(
                state_index=document["state_index"],
                board=tuple(document["board"]),
                generator_episode_index=document["generator_episode_index"],
                generator_decision_index=document["generator_decision_index"],
                generator_preceding_tape_digest=document[
                    "generator_preceding_tape_digest"
                ],
                maximum_rank=document["maximum_rank"],
                maximum_corner_cell=document["maximum_corner_cell"],
                empty_cell_count=document["empty_cell_count"],
                legal_action_indices=tuple(document["legal_action_indices"]),
                corner_preserving_action_indices=tuple(
                    document["corner_preserving_action_indices"]
                ),
                corner_breaking_action_indices=tuple(
                    document["corner_breaking_action_indices"]
                ),
            )
        except (KeyError, TypeError) as error:
            raise DecisionPointSignature2048PilotV2Error(
                "frozen decision document values changed"
            ) from error


@lru_cache(maxsize=1)
def build_decision_state_library_v2() -> tuple[FrozenDecisionStateV2, ...]:
    """Build the exact 64-state library without consulting a learned policy."""

    retained: list[FrozenDecisionStateV2] = []
    for episode_index in range(GENERATOR_MAX_EPISODES_V2):
        state = initial_state_v1(
            seed=DECISION_STATE_LIBRARY_TAPE_ROOT_V2,
            episode_index=episode_index,
        )
        preceding_digest = ""
        for decision_index in range(GENERATOR_MAX_DECISIONS_PER_EPISODE_V2 + 1):
            if is_eligible_decision_state_v2(state):
                if not preceding_digest:
                    raise AssertionError("an eligible rank-six state appeared initially")
                retained.append(
                    FrozenDecisionStateV2.from_state(
                        state_index=len(retained),
                        state=state,
                        generator_episode_index=episode_index,
                        generator_decision_index=decision_index,
                        generator_preceding_tape_digest=preceding_digest,
                    )
                )
                break
            if (
                state.status is not standard_2048.Swipe2048Status.ACTIVE
                or decision_index == GENERATOR_MAX_DECISIONS_PER_EPISODE_V2
            ):
                break
            legal_mask = legal_action_mask_v1(state)
            action_index = next(
                index for index in GENERATOR_ACTION_PRIORITY_V2 if legal_mask[index]
            )
            step = transition_v1(
                state,
                action_index,
                seed=DECISION_STATE_LIBRARY_TAPE_ROOT_V2,
                episode_index=episode_index,
                decision_index=decision_index,
            )
            preceding_digest = step.tape_digest
            state = step.next_state
        if len(retained) == DECISION_STATE_COUNT_V2:
            break
    if len(retained) != DECISION_STATE_COUNT_V2:
        _fail("fixed generator did not produce exactly 64 decision states")
    if len({row.generator_episode_index for row in retained}) != len(retained):
        raise AssertionError("more than one state was retained from a generator episode")
    return tuple(retained)


def validate_decision_state_library_v2(
    rows: Sequence[FrozenDecisionStateV2 | Mapping[str, Any]],
) -> tuple[FrozenDecisionStateV2, ...]:
    """Require the supplied rows to equal the independently generated library."""

    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        _fail("decision state library is not a sequence")
    normalized = tuple(
        row
        if type(row) is FrozenDecisionStateV2
        else FrozenDecisionStateV2.from_document(row)
        for row in rows
    )
    if (
        len(normalized) != DECISION_STATE_COUNT_V2
        or tuple(row.state_index for row in normalized)
        != tuple(range(DECISION_STATE_COUNT_V2))
        or normalized != build_decision_state_library_v2()
    ):
        _fail("decision state library differs from the frozen generator output")
    return normalized


def collect_decision_prefix_v2(
    action_selector: ActionSelectorV2,
    frozen_state: FrozenDecisionStateV2,
    *,
    prefix_tape_root: str = DECISION_PREFIX_TAPE_ROOT_V2,
    accepted_action_count: int = DECISION_PREFIX_ACTION_COUNT_V2,
) -> v1.PolicyTraceV1:
    """Execute exactly eight accepted policy actions from one frozen board."""

    if (
        not callable(action_selector)
        or type(frozen_state) is not FrozenDecisionStateV2
        or prefix_tape_root != DECISION_PREFIX_TAPE_ROOT_V2
        or accepted_action_count != DECISION_PREFIX_ACTION_COUNT_V2
    ):
        _fail("decision prefix collection contract changed")
    state = standard_2048.state_from_board_v1(frozen_state.board)
    states = [state]
    action_indices: list[int] = []
    merge_scores: list[int] = []
    tape_digests: list[str] = []
    while len(action_indices) < DECISION_PREFIX_ACTION_COUNT_V2:
        if state.status is not standard_2048.Swipe2048Status.ACTIVE:
            _fail("decision prefix terminated before eight accepted actions")
        legal_mask = legal_action_mask_v1(state)
        action_index = action_selector(state, legal_mask)
        if (
            type(action_index) is not int
            or not 0 <= action_index < len(standard_2048.ACTION_ORDER)
            or not legal_mask[action_index]
        ):
            _fail("policy selected a non-accepted decision-prefix action")
        step = transition_v1(
            state,
            action_index,
            seed=prefix_tape_root,
            episode_index=frozen_state.state_index,
            decision_index=len(action_indices),
        )
        action_indices.append(action_index)
        merge_scores.append(step.merge_score)
        tape_digests.append(step.tape_digest)
        state = step.next_state
        states.append(state)
    return v1.PolicyTraceV1(
        tape_root=prefix_tape_root,
        episode_index=frozen_state.state_index,
        states=tuple(states),
        action_indices=tuple(action_indices),
        merge_scores=tuple(merge_scores),
        tape_digests=tuple(tape_digests),
        completed_game=state.status is not standard_2048.Swipe2048Status.ACTIVE,
    )


def _resource_block_v2(
    prefix: v1.PolicyTraceV1,
) -> tuple[tuple[float, ...], tuple[tuple[Fraction, ...], ...]]:
    """Reuse the exact V1 final/mean/harmful/beneficial 48-D layout."""

    resources = v1._resource_rows_v1(prefix)
    final_resource = tuple(float(value) for value in resources[-1])
    mean_resource = tuple(
        float(sum((row[index] for row in resources), Fraction()) / len(resources))
        for index in range(STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1)
    )
    harmful = [Fraction() for _ in range(8)]
    beneficial = [Fraction() for _ in range(8)]
    for state, action_index, before in zip(
        prefix.states[:-1], prefix.action_indices, resources[:-1], strict=True
    ):
        after = v1._pre_spawn_resource_v1(state, action_index)
        for index in range(8):
            beneficial_delta = (
                before[index] - after[index]
                if index == 7
                else after[index] - before[index]
            )
            beneficial[index] += max(Fraction(), beneficial_delta)
            harmful[index] += max(Fraction(), -beneficial_delta)
    result = (
        final_resource
        + mean_resource
        + tuple(float(value) for value in harmful)
        + tuple(float(value) for value in beneficial)
    )
    if len(result) != 48 or any(not math.isfinite(value) for value in result):
        raise AssertionError("V1-derived 48-D decision resource block changed")
    return result, resources


def opportunity_normalized_resource_regrets_v2(
    prefix: v1.PolicyTraceV1,
) -> tuple[float, ...]:
    """Return one [0,1] legal-action-span-normalized regret per prefix step."""

    if len(prefix.action_indices) != DECISION_PREFIX_ACTION_COUNT_V2:
        _fail("normalized regret requires exactly eight accepted actions")
    initial = prefix.states[0]
    if not is_eligible_decision_state_v2(initial):
        _fail("normalized regret prefix did not start at a frozen decision")
    regrets: list[float] = []
    for state, chosen in zip(
        prefix.states[:-1], prefix.action_indices, strict=True
    ):
        legal = tuple(
            index
            for index, allowed in enumerate(legal_action_mask_v1(state))
            if allowed
        )
        qualities = {
            index: v1._observable_quality_v1(
                v1._pre_spawn_resource_v1(state, index)
            )
            for index in legal
        }
        best = max(qualities.values())
        worst = min(qualities.values())
        span = best - worst
        regret = Fraction() if span == 0 else (best - qualities[chosen]) / span
        if not Fraction() <= regret <= Fraction(1):
            raise AssertionError("opportunity-normalized regret escaped [0,1]")
        regrets.append(float(regret))
    if len(regrets) != DECISION_PREFIX_ACTION_COUNT_V2:
        raise AssertionError("normalized regret did not cover all eight prefix steps")
    return tuple(regrets)


def decision_summaries_v2(
    prefix: v1.PolicyTraceV1,
    resources: tuple[tuple[Fraction, ...], ...] | None = None,
) -> tuple[float, ...]:
    """Return the fixed 16-D decision-opportunity trajectory summary."""

    if len(prefix.action_indices) != DECISION_PREFIX_ACTION_COUNT_V2:
        _fail("decision summaries require exactly eight accepted actions")
    initial = prefix.states[0]
    if not is_eligible_decision_state_v2(initial):
        _fail("decision summary prefix did not start at an eligible state")
    if resources is None:
        resources = v1._resource_rows_v1(prefix)
    if len(resources) != DECISION_PREFIX_ACTION_COUNT_V2 + 1:
        _fail("decision summary resource rows changed")

    anchor = initial.board.index(max(initial.board))
    opportunities = 0
    preservation_choices = 0
    break_choices = 0
    optimal_matches = 0
    normalized_regrets: list[Fraction] = []
    for state, chosen in zip(
        prefix.states[:-1], prefix.action_indices, strict=True
    ):
        legal, preserving, breaking = _action_partition_v2(
            state, anchor_corner=anchor
        )
        if preserving and breaking:
            opportunities += 1
            preservation_choices += chosen in preserving
            break_choices += chosen in breaking
        qualities = {
            index: v1._observable_quality_v1(
                v1._pre_spawn_resource_v1(state, index)
            )
            for index in legal
        }
        best = max(qualities.values())
        worst = min(qualities.values())
        optimal_matches += qualities[chosen] == best
        span = best - worst
        regret = Fraction() if span == 0 else (best - qualities[chosen]) / span
        if not Fraction() <= regret <= Fraction(1):
            raise AssertionError("opportunity-normalized regret escaped [0,1]")
        normalized_regrets.append(regret)
    if opportunities == 0:
        raise AssertionError("an eligible prefix lost its initial opportunity")

    maximum_corner_cells = tuple(
        tuple(
            corner
            for corner in _CORNERS
            if state.board[corner] == max(state.board)
        )
        for state in prefix.states
    )
    observed_corner_identities = tuple(
        corners[0] for corners in maximum_corner_cells if corners
    )
    cells = tuple(v1._representative_max_cell_v1(state.board) for state in prefix.states)
    summaries = (
        float(Fraction(opportunities, DECISION_PREFIX_ACTION_COUNT_V2)),
        float(Fraction(preservation_choices, opportunities)),
        float(Fraction(break_choices, opportunities)),
        float(
            sum(normalized_regrets, Fraction())
            / DECISION_PREFIX_ACTION_COUNT_V2
        ),
        float(max(normalized_regrets)),
        float(Fraction(optimal_matches, DECISION_PREFIX_ACTION_COUNT_V2)),
        float(
            Fraction(
                sum(bool(corners) for corners in maximum_corner_cells),
                DECISION_PREFIX_ACTION_COUNT_V2 + 1,
            )
        ),
        float(
            Fraction(
                sum(anchor in corners for corners in maximum_corner_cells),
                DECISION_PREFIX_ACTION_COUNT_V2 + 1,
            )
        ),
        float(
            sum(
                left != right
                for left, right in zip(
                    observed_corner_identities[:-1],
                    observed_corner_identities[1:],
                    strict=True,
                )
            )
        ),
        float(
            sum(
                left != right
                for left, right in zip(cells[:-1], cells[1:], strict=True)
            )
        ),
        float(max(prefix.states[-1].board) - max(initial.board)),
        float(prefix.total_merge_score),
        float(min(row[4] for row in resources)),
        float(min(row[6] for row in resources)),
        float(max(row[7] for row in resources)),
        float(prefix.states[-1].status is not standard_2048.Swipe2048Status.ACTIVE),
    )
    if len(summaries) != len(DECISION_SUMMARY_NAMES_V2) or any(
        not math.isfinite(value) for value in summaries
    ):
        raise AssertionError("decision summary layout changed")
    return summaries


def strategic_append_v2(prefix: v1.PolicyTraceV1) -> tuple[float, ...]:
    """Return the V1-compatible 48-D resource block plus 16-D decisions."""

    resource_block, resources = _resource_block_v2(prefix)
    result = resource_block + decision_summaries_v2(prefix, resources)
    if len(result) != DECISION_STRATEGIC_APPEND_DIMENSION_V2 or any(
        not math.isfinite(value) for value in result
    ):
        raise AssertionError("decision strategic append dimension changed")
    return result


def decision_prefix_feature_vectors_v2(
    prefix: v1.PolicyTraceV1,
) -> dict[str, tuple[float, ...]]:
    """Build the exact matched 184-D/248-D/248-D feature family."""

    raw = v1._raw_prefix_v1(prefix)
    result = {
        RAW_PREFIX_ARM_V2: raw,
        ROTATED_PREFIX_ARM_V2: raw + v1._rotated_redundancy_v1(prefix),
        STRATEGIC_PREFIX_ARM_V2: raw + strategic_append_v2(prefix),
    }
    expected = {
        RAW_PREFIX_ARM_V2: RAW_PREFIX_DIMENSION_V2,
        ROTATED_PREFIX_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
        STRATEGIC_PREFIX_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
    }
    if {arm: len(vector) for arm, vector in result.items()} != expected:
        raise AssertionError("decision prefix feature dimensions changed")
    return result


def load_candidate_policy_v2(path: str | Path, device_name: str = "cpu") -> Any:
    """Reuse the strict V1 loader for a bare u005 candidate state dictionary."""

    return v1.load_candidate_policy_v1(path, device_name)


def model_action_selector_v2(model: Any) -> ActionSelectorV2:
    """Reuse the frozen V1 candidate observation and masked greedy selector."""

    return v1._model_action_selector_v1(model)


def collect_policy_decision_evidence_v2(
    model: Any,
    *,
    state_library: Sequence[FrozenDecisionStateV2 | Mapping[str, Any]] | None = None,
    prefix_tape_root: str = DECISION_PREFIX_TAPE_ROOT_V2,
) -> dict[str, Any]:
    """Collect JSON-ready 64-state prefix rows and three feature matrices."""

    if prefix_tape_root != DECISION_PREFIX_TAPE_ROOT_V2:
        _fail("decision prefix tape root changed")
    library = (
        build_decision_state_library_v2()
        if state_library is None
        else validate_decision_state_library_v2(state_library)
    )
    selector = model_action_selector_v2(model)
    matrices: dict[str, list[list[float]]] = {
        arm: [] for arm in DECISION_PREFIX_ARMS_V2
    }
    prefix_rows: list[dict[str, Any]] = []
    for frozen in library:
        prefix = collect_decision_prefix_v2(
            selector,
            frozen,
            prefix_tape_root=prefix_tape_root,
        )
        features = decision_prefix_feature_vectors_v2(prefix)
        for arm in DECISION_PREFIX_ARMS_V2:
            matrices[arm].append(list(features[arm]))
        prefix_rows.append(
            {
                "state_index": frozen.state_index,
                "generator_episode_index": frozen.generator_episode_index,
                "generator_decision_index": frozen.generator_decision_index,
                "action_indices": list(prefix.action_indices),
                "merge_scores": list(prefix.merge_scores),
                "tape_digests": list(prefix.tape_digests),
                "final_status": prefix.states[-1].status.value,
            }
        )
    result = {
        "schema": "acfqp.science.decision_point_signature_2048_pilot_evidence.v2",
        "state_library_tape_root": DECISION_STATE_LIBRARY_TAPE_ROOT_V2,
        "prefix_tape_root": prefix_tape_root,
        "state_count": DECISION_STATE_COUNT_V2,
        "state_indices": list(range(DECISION_STATE_COUNT_V2)),
        "prefix_accepted_legal_action_count": DECISION_PREFIX_ACTION_COUNT_V2,
        "state_canonicalization_applied": False,
        "label_lane_present": False,
        "decision_state_rows": [row.to_document() for row in library],
        "prefix_rows": prefix_rows,
        "prefix_feature_dimensions": {
            RAW_PREFIX_ARM_V2: RAW_PREFIX_DIMENSION_V2,
            ROTATED_PREFIX_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
            STRATEGIC_PREFIX_ARM_V2: AUGMENTED_PREFIX_DIMENSION_V2,
        },
        "prefix_matrices": matrices,
        "strategic_features_use_only_observed_prefix_and_pre_spawn_swipes": True,
        "independent_state_generation_and_policy_execution": True,
    }
    json.dumps(result, allow_nan=False, sort_keys=True)
    return result


__all__ = (
    "AUGMENTED_PREFIX_DIMENSION_V2",
    "DECISION_PREFIX_ACTION_COUNT_V2",
    "DECISION_PREFIX_ARMS_V2",
    "DECISION_PREFIX_TAPE_ROOT_V2",
    "DECISION_STATE_COUNT_V2",
    "DECISION_STATE_LIBRARY_TAPE_ROOT_V2",
    "DECISION_STRATEGIC_APPEND_DIMENSION_V2",
    "DECISION_SUMMARY_NAMES_V2",
    "DecisionPointSignature2048PilotV2Error",
    "FrozenDecisionStateV2",
    "GENERATOR_ACTION_PRIORITY_V2",
    "GENERATOR_MAX_DECISIONS_PER_EPISODE_V2",
    "GENERATOR_MAX_EPISODES_V2",
    "MINIMUM_DECISION_EMPTY_CELL_COUNT_V2",
    "MINIMUM_DECISION_MAXIMUM_RANK_V2",
    "RAW_PREFIX_ARM_V2",
    "RAW_PREFIX_DIMENSION_V2",
    "ROTATED_PREFIX_ARM_V2",
    "ROTATED_REDUNDANCY_DIMENSION_V2",
    "STRATEGIC_PREFIX_ARM_V2",
    "build_decision_state_library_v2",
    "collect_decision_prefix_v2",
    "collect_policy_decision_evidence_v2",
    "decision_prefix_feature_vectors_v2",
    "decision_summaries_v2",
    "is_eligible_decision_state_v2",
    "load_candidate_policy_v2",
    "model_action_selector_v2",
    "opportunity_normalized_resource_regrets_v2",
    "strategic_append_v2",
    "validate_decision_state_library_v2",
)
