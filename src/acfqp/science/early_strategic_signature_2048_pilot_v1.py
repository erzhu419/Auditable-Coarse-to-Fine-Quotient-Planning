"""Deterministic early-strategy evidence for the symbolic 2048 pilot.

The label lane plays a complete game on one spawn-tape root.  The feature
lane independently records exactly the first eight legal, accepted actions on
another root.  Prefix features retain the physical row-major boards and
actions as observed; no D4 canonicalization is applied.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
import json
import math
from pathlib import Path
from typing import Any, NoReturn

from acfqp.domains import standard_2048
from acfqp.science.latent_resource_2048_v1 import (
    STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1,
    encode_standard_2048_state_only_board_v1,
    encode_standard_2048_state_only_state_v1,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_INPUT_DIMENSION_V2,
    HYBRID_PARAMETER_COUNT_V2,
    RESOURCE_CANDIDATE_ARM_V2,
)
from acfqp.science.matched_2048_env_v1 import (
    initial_state_v1,
    legal_action_mask_v1,
    transition_v1,
)
from acfqp.science.matched_double_dqn_2048_hybrid_confirmatory_v2 import (
    observation_vector_hybrid_confirmatory_v2,
)
from acfqp.science.matched_double_dqn_2048_v1 import (
    _network_factory,
    _parameter_count,
)


PREFIX_ACTION_COUNT_V1 = 8
RAW_PREFIX_DIMENSION_V1 = 184
ROTATED_REDUNDANCY_DIMENSION_V1 = 64
STRATEGIC_APPEND_DIMENSION_V1 = 64
AUGMENTED_PREFIX_DIMENSION_V1 = 248
RAW_PREFIX_ARM_V1 = "RAW_PREFIX"
ROTATED_PREFIX_ARM_V1 = "RAW_PLUS_ROTATED_RAW_PREFIX"
STRATEGIC_PREFIX_ARM_V1 = "RAW_PLUS_STRATEGIC_PREFIX"
PREFIX_ARMS_V1 = (
    RAW_PREFIX_ARM_V1,
    ROTATED_PREFIX_ARM_V1,
    STRATEGIC_PREFIX_ARM_V1,
)
TRAJECTORY_SUMMARY_NAMES_V1 = (
    "maximum_tile_corner_residence",
    "fixed_corner_residence",
    "maximum_tile_corner_switch_count",
    "maximum_tile_displacement_count",
    "unique_maximum_tile_cell_count",
    "maximum_rank_gain",
    "prefix_merge_score",
    "minimum_empty_slack",
    "minimum_directional_flow_liquidity",
    "maximum_irreversibility_risk",
    "mean_chosen_action_resource_regret",
    "maximum_chosen_action_resource_regret",
    "resource_optimal_action_match_fraction",
    "action_diversity",
    "immediate_opposite_direction_reversal_fraction",
    "observed_prefix_terminal",
)
_CORNERS = (0, 3, 12, 15)
_OPPOSITE_ACTION_INDEX = {0: 1, 1: 0, 2: 3, 3: 2}


class EarlyStrategicSignature2048PilotV1Error(ValueError):
    """A model, tape pair, prefix, or feature contract is invalid."""


def _fail(message: str) -> NoReturn:
    raise EarlyStrategicSignature2048PilotV1Error(message)


ActionSelectorV1 = Callable[
    [standard_2048.Swipe2048State, tuple[bool, bool, bool, bool]], int
]


@dataclass(frozen=True, slots=True)
class PolicyTraceV1:
    """One deterministic sequence of accepted standard-2048 transitions."""

    tape_root: str
    episode_index: int
    states: tuple[standard_2048.Swipe2048State, ...]
    action_indices: tuple[int, ...]
    merge_scores: tuple[int, ...]
    tape_digests: tuple[str, ...]
    completed_game: bool

    def __post_init__(self) -> None:
        count = len(self.action_indices)
        if (
            type(self.tape_root) is not str
            or not self.tape_root
            or type(self.episode_index) is not int
            or self.episode_index < 0
            or type(self.states) is not tuple
            or len(self.states) != count + 1
            or any(
                type(state) is not standard_2048.Swipe2048State
                for state in self.states
            )
            or type(self.merge_scores) is not tuple
            or len(self.merge_scores) != count
            or any(type(score) is not int or score < 0 for score in self.merge_scores)
            or type(self.tape_digests) is not tuple
            or len(self.tape_digests) != count
            or any(
                type(value) is not str or len(value) != 64
                for value in self.tape_digests
            )
            or type(self.completed_game) is not bool
        ):
            _fail("policy trace shape changed")
        for state in self.states:
            standard_2048.validate_board_v1(state.board)
            if state != standard_2048.state_from_board_v1(state.board):
                _fail("policy trace contains a status-inconsistent state")
        for state, action_index in zip(
            self.states[:-1], self.action_indices, strict=True
        ):
            if (
                type(action_index) is not int
                or not 0 <= action_index < len(standard_2048.ACTION_ORDER)
                or standard_2048.ACTION_ORDER[action_index]
                not in standard_2048.legal_actions_v1(state.board)
            ):
                _fail("policy trace contains a non-accepted action")
        terminal = self.states[-1].status is not standard_2048.Swipe2048Status.ACTIVE
        if self.completed_game is not terminal:
            _fail("policy trace completion flag disagrees with final state")

    @property
    def total_merge_score(self) -> int:
        return sum(self.merge_scores)

    @property
    def maximum_tile_rank(self) -> int:
        return max(max(state.board) for state in self.states)

    def label_document(self) -> dict[str, Any]:
        if not self.completed_game:
            _fail("a label document requires a completed game")
        return {
            "episode_index": self.episode_index,
            "total_merge_score": self.total_merge_score,
            "maximum_tile_rank": self.maximum_tile_rank,
            "decision_count": len(self.action_indices),
            "terminal_status": self.states[-1].status.value,
            "won": self.states[-1].status is standard_2048.Swipe2048Status.WON,
        }


def _validate_tape_request(
    *, tape_root: str, episode_index: int, decision_cap: int
) -> None:
    if (
        type(tape_root) is not str
        or not tape_root
        or type(episode_index) is not int
        or episode_index < 0
        or type(decision_cap) is not int
        or decision_cap <= 0
    ):
        _fail("policy tape request changed")


def _collect_trace_v1(
    action_selector: ActionSelectorV1,
    *,
    tape_root: str,
    episode_index: int,
    accepted_action_limit: int | None,
    decision_cap: int,
) -> PolicyTraceV1:
    _validate_tape_request(
        tape_root=tape_root,
        episode_index=episode_index,
        decision_cap=decision_cap,
    )
    if not callable(action_selector) or (
        accepted_action_limit is not None
        and (
            type(accepted_action_limit) is not int
            or accepted_action_limit <= 0
            or accepted_action_limit > decision_cap
        )
    ):
        _fail("policy collector configuration changed")
    state = initial_state_v1(seed=tape_root, episode_index=episode_index)
    states = [state]
    action_indices: list[int] = []
    merge_scores: list[int] = []
    tape_digests: list[str] = []
    while state.status is standard_2048.Swipe2048Status.ACTIVE:
        if len(action_indices) >= decision_cap:
            _fail("policy episode exceeded the decision cap")
        legal_mask = legal_action_mask_v1(state)
        action_index = action_selector(state, legal_mask)
        if (
            type(action_index) is not int
            or not 0 <= action_index < len(standard_2048.ACTION_ORDER)
            or not legal_mask[action_index]
        ):
            _fail("policy selected an action that was not legal and accepted")
        step = transition_v1(
            state,
            action_index,
            seed=tape_root,
            episode_index=episode_index,
            decision_index=len(action_indices),
        )
        action_indices.append(action_index)
        merge_scores.append(step.merge_score)
        tape_digests.append(step.tape_digest)
        state = step.next_state
        states.append(state)
        if (
            accepted_action_limit is not None
            and len(action_indices) == accepted_action_limit
        ):
            break
    completed = state.status is not standard_2048.Swipe2048Status.ACTIVE
    if (
        accepted_action_limit is not None
        and len(action_indices) != accepted_action_limit
    ):
        _fail("prefix tape terminated before the exact accepted-action count")
    return PolicyTraceV1(
        tape_root=tape_root,
        episode_index=episode_index,
        states=tuple(states),
        action_indices=tuple(action_indices),
        merge_scores=tuple(merge_scores),
        tape_digests=tuple(tape_digests),
        completed_game=completed,
    )


def collect_full_game_v1(
    action_selector: ActionSelectorV1,
    *,
    tape_root: str,
    episode_index: int,
    decision_cap: int = 20_000,
) -> PolicyTraceV1:
    """Play one complete game on the label tape root."""

    trace = _collect_trace_v1(
        action_selector,
        tape_root=tape_root,
        episode_index=episode_index,
        accepted_action_limit=None,
        decision_cap=decision_cap,
    )
    if not trace.completed_game:
        raise AssertionError("unbounded policy collection did not complete")
    return trace


def collect_prefix_v1(
    action_selector: ActionSelectorV1,
    *,
    tape_root: str,
    episode_index: int,
    accepted_action_count: int = PREFIX_ACTION_COUNT_V1,
) -> PolicyTraceV1:
    """Collect exactly the first accepted legal actions on the prefix root."""

    if accepted_action_count != PREFIX_ACTION_COUNT_V1:
        _fail("V1 prefix length must remain exactly eight actions")
    return _collect_trace_v1(
        action_selector,
        tape_root=tape_root,
        episode_index=episode_index,
        accepted_action_limit=accepted_action_count,
        decision_cap=accepted_action_count,
    )


def collect_independent_policy_tapes_v1(
    action_selector: ActionSelectorV1,
    *,
    label_tape_root: str,
    prefix_tape_root: str,
    episode_index: int,
) -> tuple[PolicyTraceV1, PolicyTraceV1]:
    """Collect the label game and eight-action prefix from disjoint roots."""

    if (
        type(label_tape_root) is not str
        or type(prefix_tape_root) is not str
        or not label_tape_root
        or not prefix_tape_root
        or label_tape_root == prefix_tape_root
    ):
        _fail("label and prefix tape roots must be nonempty and independent")
    return (
        collect_full_game_v1(
            action_selector,
            tape_root=label_tape_root,
            episode_index=episode_index,
        ),
        collect_prefix_v1(
            action_selector,
            tape_root=prefix_tape_root,
            episode_index=episode_index,
        ),
    )


def _raw_prefix_v1(prefix: PolicyTraceV1) -> tuple[float, ...]:
    if len(prefix.action_indices) != PREFIX_ACTION_COUNT_V1:
        _fail("raw prefix requires exactly eight accepted actions")
    boards = tuple(
        rank / standard_2048.GOAL_RANK
        for state in prefix.states
        for rank in state.board
    )
    action_one_hot = tuple(
        float(index == action_index)
        for action_index in prefix.action_indices
        for index in range(len(standard_2048.ACTION_ORDER))
    )
    scores = tuple(
        math.log2(value + 1) / standard_2048.GOAL_RANK
        for value in prefix.merge_scores
    )
    result = boards + action_one_hot + scores
    if len(result) != RAW_PREFIX_DIMENSION_V1:
        raise AssertionError("raw prefix dimension changed")
    return result


def _rotated_redundancy_v1(prefix: PolicyTraceV1) -> tuple[float, ...]:
    result = tuple(
        rank / standard_2048.GOAL_RANK
        for state_index in (0, 2, 5, 8)
        for rank in reversed(prefix.states[state_index].board)
    )
    if len(result) != ROTATED_REDUNDANCY_DIMENSION_V1:
        raise AssertionError("rotated raw redundancy dimension changed")
    return result


def _resource_rows_v1(
    prefix: PolicyTraceV1,
) -> tuple[tuple[Fraction, ...], ...]:
    rows = tuple(
        encode_standard_2048_state_only_state_v1(state).resource_vector
        for state in prefix.states
    )
    if len(rows) != PREFIX_ACTION_COUNT_V1 + 1 or any(
        len(row) != STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1 for row in rows
    ):
        raise AssertionError("prefix resource matrix changed")
    return rows


def _pre_spawn_resource_v1(
    state: standard_2048.Swipe2048State, action_index: int
) -> tuple[Fraction, ...]:
    action = standard_2048.ACTION_ORDER[action_index]
    board, _score, changed = standard_2048.swipe_board_v1(state.board, action)
    if not changed:
        _fail("accepted action did not produce a pre-spawn afterstate")
    return encode_standard_2048_state_only_board_v1(board).resource_vector


def _observable_quality_v1(resource: Sequence[Fraction]) -> Fraction:
    if len(resource) < 8:
        raise AssertionError("core resource vector changed")
    return (sum(resource[:7], Fraction()) + (Fraction(1) - resource[7])) / 8


def _representative_max_cell_v1(board: tuple[int, ...]) -> int:
    maximum = max(board)
    return min(index for index, rank in enumerate(board) if rank == maximum)


def _trajectory_summaries_v1(
    prefix: PolicyTraceV1, resources: tuple[tuple[Fraction, ...], ...]
) -> tuple[float, ...]:
    cells = tuple(_representative_max_cell_v1(state.board) for state in prefix.states)
    maximum_corner_cells = tuple(
        tuple(
            corner
            for corner in _CORNERS
            if state.board[corner] == max(state.board)
        )
        for state in prefix.states
    )
    corner_residence = Fraction(
        sum(bool(corners) for corners in maximum_corner_cells),
        9,
    )
    fixed_corner_residence = Fraction(
        max(
            sum(corner in corners for corners in maximum_corner_cells)
            for corner in _CORNERS
        ),
        9,
    )
    observed_corner_identities = tuple(
        corners[0] for corners in maximum_corner_cells if corners
    )
    anchor_switch_count = sum(
        left != right
        for left, right in zip(
            observed_corner_identities[:-1],
            observed_corner_identities[1:],
            strict=True,
        )
    )
    displacement_count = sum(
        left != right
        for left, right in zip(cells[:-1], cells[1:], strict=True)
    )
    unique_maximum_cell_count = len(
        {
            index
            for state in prefix.states
            for index, rank in enumerate(state.board)
            if rank == max(state.board)
        }
    )

    regrets: list[Fraction] = []
    optimal_matches = 0
    for state, action_index in zip(
        prefix.states[:-1], prefix.action_indices, strict=True
    ):
        legal_indices = tuple(
            index
            for index, allowed in enumerate(legal_action_mask_v1(state))
            if allowed
        )
        qualities = {
            index: _observable_quality_v1(_pre_spawn_resource_v1(state, index))
            for index in legal_indices
        }
        best = max(qualities.values())
        actual = qualities[action_index]
        regret = best - actual
        if regret < 0:
            raise AssertionError("observable action regret became negative")
        regrets.append(regret)
        optimal_matches += actual == best

    opposite_reversals = sum(
        right == _OPPOSITE_ACTION_INDEX[left]
        for left, right in zip(
            prefix.action_indices[:-1],
            prefix.action_indices[1:],
            strict=True,
        )
    )
    summaries = (
        float(corner_residence),
        float(fixed_corner_residence),
        float(anchor_switch_count),
        float(displacement_count),
        float(unique_maximum_cell_count),
        float(max(prefix.states[-1].board) - max(prefix.states[0].board)),
        float(prefix.total_merge_score),
        float(min(row[4] for row in resources)),
        float(min(row[6] for row in resources)),
        float(max(row[7] for row in resources)),
        float(sum(regrets, Fraction()) / len(regrets)),
        float(max(regrets)),
        float(Fraction(optimal_matches, PREFIX_ACTION_COUNT_V1)),
        float(
            Fraction(
                len(set(prefix.action_indices)),
                len(standard_2048.ACTION_ORDER),
            )
        ),
        float(Fraction(opposite_reversals, PREFIX_ACTION_COUNT_V1 - 1)),
        float(prefix.states[-1].status is not standard_2048.Swipe2048Status.ACTIVE),
    )
    if len(summaries) != len(TRAJECTORY_SUMMARY_NAMES_V1) or any(
        not math.isfinite(value) for value in summaries
    ):
        raise AssertionError("trajectory summary layout changed")
    return summaries


def strategic_append_v1(prefix: PolicyTraceV1) -> tuple[float, ...]:
    """Return the 64-D state-only, pre-spawn strategic trajectory block."""

    if len(prefix.action_indices) != PREFIX_ACTION_COUNT_V1:
        _fail("strategic append requires exactly eight accepted actions")
    resources = _resource_rows_v1(prefix)
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
        after = _pre_spawn_resource_v1(state, action_index)
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
        + _trajectory_summaries_v1(prefix, resources)
    )
    if len(result) != STRATEGIC_APPEND_DIMENSION_V1 or any(
        not math.isfinite(value) for value in result
    ):
        raise AssertionError("strategic append dimension changed")
    return result


def prefix_feature_vectors_v1(
    prefix: PolicyTraceV1,
) -> dict[str, tuple[float, ...]]:
    """Build the three matched raw/control/candidate feature vectors."""

    raw = _raw_prefix_v1(prefix)
    result = {
        RAW_PREFIX_ARM_V1: raw,
        ROTATED_PREFIX_ARM_V1: raw + _rotated_redundancy_v1(prefix),
        STRATEGIC_PREFIX_ARM_V1: raw + strategic_append_v1(prefix),
    }
    expected = {
        RAW_PREFIX_ARM_V1: RAW_PREFIX_DIMENSION_V1,
        ROTATED_PREFIX_ARM_V1: AUGMENTED_PREFIX_DIMENSION_V1,
        STRATEGIC_PREFIX_ARM_V1: AUGMENTED_PREFIX_DIMENSION_V1,
    }
    if {name: len(vector) for name, vector in result.items()} != expected:
        raise AssertionError("prefix feature family dimensions changed")
    return result


def load_candidate_policy_v1(
    path: str | Path, device_name: str = "cpu"
) -> Any:
    """Load one strict bare 32-D candidate DQN ``state_dict`` checkpoint."""

    if type(device_name) is not str or not device_name:
        _fail("candidate policy device changed")
    checkpoint = Path(path)
    if not checkpoint.is_file():
        _fail("candidate policy checkpoint is not a regular file")
    try:
        import torch
    except ImportError as error:  # pragma: no cover - runtime dependency only
        raise EarlyStrategicSignature2048PilotV1Error(
            "Torch is required to load the candidate policy"
        ) from error
    if device_name.startswith("cuda") and not torch.cuda.is_available():
        _fail("requested candidate-policy CUDA device is unavailable")
    device = torch.device(device_name)
    state_dict = torch.load(checkpoint, map_location=device, weights_only=True)
    model = _network_factory(torch, HYBRID_INPUT_DIMENSION_V2)().to(device)
    expected_keys = set(model.state_dict())
    if (
        not isinstance(state_dict, Mapping)
        or set(state_dict) != expected_keys
        or any(not torch.is_tensor(value) for value in state_dict.values())
    ):
        _fail("checkpoint is not the exact bare candidate state_dict")
    try:
        model.load_state_dict(state_dict, strict=True)
    except (RuntimeError, TypeError) as error:
        raise EarlyStrategicSignature2048PilotV1Error(
            "candidate state_dict tensor shapes changed"
        ) from error
    if _parameter_count(model) != HYBRID_PARAMETER_COUNT_V2:
        _fail("candidate network parameter count changed")
    model.eval()
    return model


def _model_action_selector_v1(model: Any) -> ActionSelectorV1:
    try:
        import torch
    except ImportError as error:  # pragma: no cover - runtime dependency only
        raise EarlyStrategicSignature2048PilotV1Error(
            "Torch is required to execute the candidate policy"
        ) from error
    if not hasattr(model, "parameters") or not callable(model):
        _fail("candidate policy is not one Torch model")
    parameters = tuple(model.parameters())
    if not parameters:
        _fail("candidate policy has no parameters")
    device = parameters[0].device
    model.eval()

    def choose(
        state: standard_2048.Swipe2048State,
        legal_mask: tuple[bool, bool, bool, bool],
    ) -> int:
        observation = observation_vector_hybrid_confirmatory_v2(
            state, RESOURCE_CANDIDATE_ARM_V2
        )
        with torch.no_grad():
            values = model(
                torch.tensor(
                    observation, dtype=torch.float32, device=device
                ).unsqueeze(0)
            )[0]
            mask = torch.tensor(legal_mask, dtype=torch.bool, device=device)
            values = values.masked_fill(~mask, float("-inf"))
            action_index = int(torch.argmax(values).item())
        return action_index

    return choose


def collect_policy_evidence_v1(
    model: Any,
    *,
    label_tape_root: str,
    prefix_tape_root: str,
    episode_indices: Sequence[int],
    prefix_action_count: int = PREFIX_ACTION_COUNT_V1,
) -> dict[str, Any]:
    """Collect JSON-ready full-game labels and the three prefix matrices."""

    if (
        not isinstance(episode_indices, Sequence)
        or isinstance(episode_indices, (str, bytes))
        or not episode_indices
        or any(
            type(index) is not int or index < 0 for index in episode_indices
        )
        or len(set(episode_indices)) != len(episode_indices)
        or prefix_action_count != PREFIX_ACTION_COUNT_V1
    ):
        _fail("evidence episode registry changed")
    selector = _model_action_selector_v1(model)
    label_rows: list[dict[str, Any]] = []
    matrices: dict[str, list[list[float]]] = {arm: [] for arm in PREFIX_ARMS_V1}
    prefix_rows: list[dict[str, Any]] = []
    for episode_index in episode_indices:
        label, prefix = collect_independent_policy_tapes_v1(
            selector,
            label_tape_root=label_tape_root,
            prefix_tape_root=prefix_tape_root,
            episode_index=episode_index,
        )
        label_rows.append(label.label_document())
        features = prefix_feature_vectors_v1(prefix)
        for arm in PREFIX_ARMS_V1:
            matrices[arm].append(list(features[arm]))
        prefix_rows.append(
            {
                "episode_index": episode_index,
                "action_indices": list(prefix.action_indices),
                "merge_scores": list(prefix.merge_scores),
                "tape_digests": list(prefix.tape_digests),
                "final_status": prefix.states[-1].status.value,
            }
        )
    result = {
        "schema": "acfqp.science.early_strategic_signature_2048_pilot_evidence.v1",
        "label_tape_root": label_tape_root,
        "prefix_tape_root": prefix_tape_root,
        "independent_tape_roots": label_tape_root != prefix_tape_root,
        "episode_indices": list(episode_indices),
        "prefix_accepted_legal_action_count": PREFIX_ACTION_COUNT_V1,
        "state_canonicalization_applied": False,
        "label_rows": label_rows,
        "prefix_rows": prefix_rows,
        "prefix_feature_dimensions": {
            RAW_PREFIX_ARM_V1: RAW_PREFIX_DIMENSION_V1,
            ROTATED_PREFIX_ARM_V1: AUGMENTED_PREFIX_DIMENSION_V1,
            STRATEGIC_PREFIX_ARM_V1: AUGMENTED_PREFIX_DIMENSION_V1,
        },
        "prefix_matrices": matrices,
        "strategic_features_use_only_prefix_observations_and_pre_spawn_swipes": True,
    }
    if not result["independent_tape_roots"]:
        _fail("label and prefix tape roots must be independent")
    json.dumps(result, allow_nan=False, sort_keys=True)
    return result


__all__ = (
    "AUGMENTED_PREFIX_DIMENSION_V1",
    "EarlyStrategicSignature2048PilotV1Error",
    "PREFIX_ACTION_COUNT_V1",
    "PREFIX_ARMS_V1",
    "PolicyTraceV1",
    "RAW_PREFIX_ARM_V1",
    "RAW_PREFIX_DIMENSION_V1",
    "ROTATED_PREFIX_ARM_V1",
    "ROTATED_REDUNDANCY_DIMENSION_V1",
    "STRATEGIC_APPEND_DIMENSION_V1",
    "STRATEGIC_PREFIX_ARM_V1",
    "TRAJECTORY_SUMMARY_NAMES_V1",
    "collect_full_game_v1",
    "collect_independent_policy_tapes_v1",
    "collect_policy_evidence_v1",
    "collect_prefix_v1",
    "load_candidate_policy_v1",
    "prefix_feature_vectors_v1",
    "strategic_append_v1",
)
