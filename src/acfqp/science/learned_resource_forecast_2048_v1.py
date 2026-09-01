"""Frozen learned resource-forecast primitives for the 2048 U001 pilot.

This module deliberately separates three operations:

* observable eight-action prefix construction;
* self-supervised targets built only from complete trajectory-lane games; and
* skill-label-free encoder fitting and frozen inference.

The skill classifier and campaign orchestration live elsewhere.  In
particular, no API in this module accepts a skill label or a label-lane row.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
from typing import Any, NoReturn

from acfqp.domains import standard_2048
from acfqp.science.early_strategic_signature_2048_pilot_v1 import PolicyTraceV1
from acfqp.science.latent_resource_2048_v1 import (
    STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1,
    encode_standard_2048_state_only_state_v1,
)
from acfqp.science.latent_resource_hybrid_confirmatory_protocol_v2 import (
    HYBRID_CONFIRMATORY_ARMS_V2,
    HYBRID_INPUT_DIMENSION_V2,
    HYBRID_PARAMETER_COUNT_V2,
    RAW_STANDARD_ARM_V2,
    RAW_STANDARD_INPUT_DIMENSION_V2,
    RAW_STANDARD_PARAMETER_COUNT_V2,
)
from acfqp.science.matched_double_dqn_2048_hybrid_confirmatory_v2 import (
    observation_vector_hybrid_confirmatory_v2,
)
from acfqp.science.matched_double_dqn_2048_v1 import (
    _network_factory,
    _parameter_count,
)


PREFIX_ACTION_COUNT_V1 = 8
PREFIX_TOKEN_WIDTH_V1 = 21
RAW_PREFIX_DIMENSION_V1 = 184
FORECAST_HORIZONS_V1 = (1, 4, 16)
FORECAST_TARGET_WIDTH_PER_HORIZON_V1 = 18
FORECAST_TARGET_DIMENSION_V1 = 54
FORECAST_HIDDEN_WIDTH_V1 = 64
FORECAST_ENCODER_PARAMETER_COUNT_V1 = 16_704
FORECAST_MODEL_PARAMETER_COUNT_V1 = 20_214
MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1 = 32
FORECAST_TRAINING_EPOCHS_V1 = 50
FORECAST_BATCH_SIZE_V1 = 256
FORECAST_ADAM_LEARNING_RATE_V1 = 0.001
TARGET_SHUFFLE_SEED_V1 = 881_002

ALIGNED_TARGET_MODE_V1 = "ALIGNED_RESOURCE_FORECAST"
PLAYER_SHUFFLED_TARGET_MODE_V1 = "PLAYER_SHUFFLED_RESOURCE_FORECAST"
FORECAST_TARGET_MODES_V1 = (
    ALIGNED_TARGET_MODE_V1,
    PLAYER_SHUFFLED_TARGET_MODE_V1,
)

if STATE_ONLY_RESOURCE_VECTOR_DIMENSION_V1 != 16:
    raise AssertionError("state-only forecast resource width changed")


class LearnedResourceForecast2048V1Error(ValueError):
    """A prefix, complete trajectory, lane binding, model, or shape is invalid."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecast2048V1Error(message)


def _finite_float(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or type(value) not in (int, float):
        _fail(f"{name} must be one finite number")
    result = float(value)
    if not math.isfinite(result):
        _fail(f"{name} must be one finite number")
    return result


def _normalized_merge_score_rank_v1(score: int) -> float:
    if type(score) is not int or score < 0:
        _fail("merge score must be one nonnegative integer")
    result = math.log2(score + 1) / standard_2048.GOAL_RANK
    if not math.isfinite(result) or result < 0.0:
        raise AssertionError("normalized merge-score rank changed")
    return result


def _validate_exact_prefix_v1(prefix: PolicyTraceV1) -> None:
    if type(prefix) is not PolicyTraceV1:
        _fail("prefix must be one exact PolicyTraceV1")
    if (
        len(prefix.action_indices) != PREFIX_ACTION_COUNT_V1
        or len(prefix.states) != PREFIX_ACTION_COUNT_V1 + 1
        or len(prefix.merge_scores) != PREFIX_ACTION_COUNT_V1
    ):
        _fail("prefix must contain exactly eight accepted actions")


def prefix_tokens_v1(prefix: PolicyTraceV1) -> tuple[tuple[float, ...], ...]:
    """Return the observable 8 by 21 transition-token matrix.

    Token ``t`` contains only ``s_t``, ``a_t``, and the merge score emitted by
    that accepted action.  It never reads ``s_8`` or any later state.
    """

    _validate_exact_prefix_v1(prefix)
    rows: list[tuple[float, ...]] = []
    for state, action_index, merge_score in zip(
        prefix.states[:-1],
        prefix.action_indices,
        prefix.merge_scores,
        strict=True,
    ):
        row = (
            *(rank / standard_2048.GOAL_RANK for rank in state.board),
            *(float(index == action_index) for index in range(4)),
            _normalized_merge_score_rank_v1(merge_score),
        )
        if len(row) != PREFIX_TOKEN_WIDTH_V1 or any(
            not math.isfinite(value) for value in row
        ):
            raise AssertionError("prefix token layout changed")
        rows.append(row)
    result = tuple(rows)
    if len(result) != PREFIX_ACTION_COUNT_V1:
        raise AssertionError("prefix token count changed")
    return result


def raw_prefix_v1(prefix: PolicyTraceV1) -> tuple[float, ...]:
    """Return the frozen 184-D raw representation of one eight-action probe."""

    _validate_exact_prefix_v1(prefix)
    result = (
        *(rank / standard_2048.GOAL_RANK for state in prefix.states for rank in state.board),
        *(
            float(index == action_index)
            for action_index in prefix.action_indices
            for index in range(4)
        ),
        *(
            _normalized_merge_score_rank_v1(score)
            for score in prefix.merge_scores
        ),
    )
    if len(result) != RAW_PREFIX_DIMENSION_V1 or any(
        not math.isfinite(value) for value in result
    ):
        raise AssertionError("raw prefix layout changed")
    return result


def deterministic_window_starts_v1(
    transition_count: int,
) -> tuple[int, ...]:
    """Choose at most 32 increasing, episode-spanning eight-step windows."""

    if type(transition_count) is not int or transition_count < PREFIX_ACTION_COUNT_V1:
        _fail("complete trajectory is shorter than one eight-action window")
    available = transition_count - PREFIX_ACTION_COUNT_V1 + 1
    if available <= MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1:
        return tuple(range(available))
    last = available - 1
    denominator = MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1 - 1
    starts = tuple(
        index * last // denominator
        for index in range(MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1)
    )
    if (
        len(starts) != MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1
        or starts[0] != 0
        or starts[-1] != last
        or any(left >= right for left, right in zip(starts[:-1], starts[1:]))
    ):
        raise AssertionError("deterministic trajectory window sampler changed")
    return starts


def _validate_complete_trace_v1(trace: PolicyTraceV1) -> None:
    if type(trace) is not PolicyTraceV1:
        _fail("trajectory must be one exact PolicyTraceV1")
    if (
        not trace.completed_game
        or trace.states[-1].status is standard_2048.Swipe2048Status.ACTIVE
    ):
        _fail("forecast targets require a complete goal-terminated trajectory")
    if len(trace.action_indices) < PREFIX_ACTION_COUNT_V1:
        _fail("complete trajectory is shorter than eight accepted actions")


def forecast_target_v1(
    trace: PolicyTraceV1, *, window_start: int
) -> tuple[float, ...]:
    """Build the frozen 54-D aligned target for one complete-game window."""

    _validate_complete_trace_v1(trace)
    action_count = len(trace.action_indices)
    if (
        type(window_start) is not int
        or window_start < 0
        or window_start + PREFIX_ACTION_COUNT_V1 > action_count
    ):
        _fail("forecast window start is outside the complete trajectory")
    endpoint = window_start + PREFIX_ACTION_COUNT_V1
    values: list[float] = []
    for horizon in FORECAST_HORIZONS_V1:
        target_state_index = min(endpoint + horizon, action_count)
        resource = encode_standard_2048_state_only_state_v1(
            trace.states[target_state_index]
        ).resource_vector
        future_score = sum(trace.merge_scores[endpoint:target_state_index])
        terminal_by_horizon = float(endpoint + horizon >= action_count)
        block = (
            *(float(value) for value in resource),
            _normalized_merge_score_rank_v1(future_score),
            terminal_by_horizon,
        )
        if (
            len(block) != FORECAST_TARGET_WIDTH_PER_HORIZON_V1
            or any(not math.isfinite(value) for value in block)
            or any(not 0.0 <= value <= 1.0 for value in block[:16])
            or block[-1] not in (0.0, 1.0)
        ):
            raise AssertionError("forecast target block changed")
        values.extend(block)
    result = tuple(values)
    if len(result) != FORECAST_TARGET_DIMENSION_V1:
        raise AssertionError("forecast target dimension changed")
    return result


@dataclass(frozen=True, slots=True, order=True)
class ForecastWindowKeyV1:
    """Stable identity of one player-owned trajectory window."""

    player_id: str
    tape_root: str
    episode_index: int
    window_start: int

    def __post_init__(self) -> None:
        if (
            type(self.player_id) is not str
            or not self.player_id
            or type(self.tape_root) is not str
            or not self.tape_root
            or type(self.episode_index) is not int
            or self.episode_index < 0
            or type(self.window_start) is not int
            or self.window_start < 0
        ):
            _fail("forecast window identity changed")


@dataclass(frozen=True, slots=True)
class ForecastExampleV1:
    """One skill-label-free token/target pair with explicit target ownership."""

    key: ForecastWindowKeyV1
    tokens: tuple[tuple[float, ...], ...]
    target: tuple[float, ...]
    target_source_key: ForecastWindowKeyV1

    def __post_init__(self) -> None:
        if (
            type(self.key) is not ForecastWindowKeyV1
            or type(self.target_source_key) is not ForecastWindowKeyV1
            or self.key.player_id != self.target_source_key.player_id
            or type(self.tokens) is not tuple
            or len(self.tokens) != PREFIX_ACTION_COUNT_V1
            or any(
                type(row) is not tuple
                or len(row) != PREFIX_TOKEN_WIDTH_V1
                or any(
                    isinstance(value, bool)
                    or type(value) not in (int, float)
                    or not math.isfinite(float(value))
                    for value in row
                )
                for row in self.tokens
            )
            or type(self.target) is not tuple
            or len(self.target) != FORECAST_TARGET_DIMENSION_V1
            or any(
                isinstance(value, bool)
                or type(value) not in (int, float)
                or not math.isfinite(float(value))
                for value in self.target
            )
        ):
            _fail("forecast example shape, finiteness, or player ownership changed")


def aligned_forecast_examples_v1(
    trace: PolicyTraceV1, *, player_id: str
) -> tuple[ForecastExampleV1, ...]:
    """Materialize every registered aligned window from one complete game."""

    _validate_complete_trace_v1(trace)
    if type(player_id) is not str or not player_id:
        _fail("forecast player identity must be nonempty")
    examples: list[ForecastExampleV1] = []
    for start in deterministic_window_starts_v1(len(trace.action_indices)):
        prefix = PolicyTraceV1(
            tape_root=trace.tape_root,
            episode_index=trace.episode_index,
            states=trace.states[start : start + PREFIX_ACTION_COUNT_V1 + 1],
            action_indices=trace.action_indices[
                start : start + PREFIX_ACTION_COUNT_V1
            ],
            merge_scores=trace.merge_scores[start : start + PREFIX_ACTION_COUNT_V1],
            tape_digests=trace.tape_digests[start : start + PREFIX_ACTION_COUNT_V1],
            completed_game=(
                trace.states[start + PREFIX_ACTION_COUNT_V1].status
                is not standard_2048.Swipe2048Status.ACTIVE
            ),
        )
        key = ForecastWindowKeyV1(
            player_id=player_id,
            tape_root=trace.tape_root,
            episode_index=trace.episode_index,
            window_start=start,
        )
        examples.append(
            ForecastExampleV1(
                key=key,
                tokens=prefix_tokens_v1(prefix),
                target=forecast_target_v1(trace, window_start=start),
                target_source_key=key,
            )
        )
    return tuple(examples)


def player_shuffled_targets_v1(
    aligned_examples: Sequence[ForecastExampleV1],
) -> tuple[ForecastExampleV1, ...]:
    """Apply a fixed no-fixed-point target rotation within every player.

    Window identities, rather than possibly equal numeric target vectors, are
    permuted.  For a player with more than one window every target source is
    different from its input window, and the per-player target multiset is
    preserved exactly.  A singleton necessarily remains unchanged.
    """

    examples = _exact_example_sequence_v1(aligned_examples)
    if any(example.target_source_key != example.key for example in examples):
        _fail("player target shuffling requires aligned input examples")
    by_player: dict[str, list[ForecastExampleV1]] = defaultdict(list)
    for example in examples:
        by_player[example.key.player_id].append(example)
    source_by_key: dict[ForecastWindowKeyV1, ForecastExampleV1] = {}
    shuffle_rng = random.Random(TARGET_SHUFFLE_SEED_V1)
    for player in sorted(by_player):
        player_examples = by_player[player]
        ordered = sorted(player_examples, key=lambda example: example.key)
        source_indices = list(range(len(ordered)))
        # Sattolo's algorithm produces one cycle and therefore no fixed point
        # whenever at least two rows are present.  Players are visited in
        # sorted order so the frozen seed is independent of input row order.
        for index in range(len(source_indices) - 1, 0, -1):
            swap_index = shuffle_rng.randrange(index)
            source_indices[index], source_indices[swap_index] = (
                source_indices[swap_index],
                source_indices[index],
            )
        for index, example in enumerate(ordered):
            source_by_key[example.key] = ordered[source_indices[index]]
    shuffled = tuple(
        ForecastExampleV1(
            key=example.key,
            tokens=example.tokens,
            target=source_by_key[example.key].target,
            target_source_key=source_by_key[example.key].key,
        )
        for example in examples
    )
    _validate_target_permutation_v1(examples, shuffled)
    return shuffled


def _exact_string_set_v1(values: Sequence[str], *, name: str) -> frozenset[str]:
    if (
        not isinstance(values, Sequence)
        or isinstance(values, (str, bytes))
        or not values
        or any(type(value) is not str or not value for value in values)
        or len(set(values)) != len(values)
    ):
        _fail(f"{name} registry must contain unique nonempty strings")
    return frozenset(values)


def validate_disjoint_lane_roots_v1(
    *,
    trajectory_tape_roots: Sequence[str],
    skill_label_tape_roots: Sequence[str],
    probe_tape_roots: Sequence[str],
) -> None:
    """Fail closed unless the three evidence-lane tape registries are disjoint."""

    trajectory = _exact_string_set_v1(
        trajectory_tape_roots, name="trajectory tape"
    )
    label = _exact_string_set_v1(skill_label_tape_roots, name="skill-label tape")
    probe = _exact_string_set_v1(probe_tape_roots, name="probe tape")
    if trajectory & label or trajectory & probe or label & probe:
        _fail("trajectory, skill-label, and probe tape roots must be disjoint")


def _exact_example_sequence_v1(
    examples: Sequence[ForecastExampleV1],
) -> tuple[ForecastExampleV1, ...]:
    if (
        not isinstance(examples, Sequence)
        or isinstance(examples, (str, bytes))
        or not examples
        or any(type(example) is not ForecastExampleV1 for example in examples)
    ):
        _fail("forecast training examples must be one nonempty exact sequence")
    result = tuple(examples)
    keys = tuple(example.key for example in result)
    if len(set(keys)) != len(keys):
        _fail("forecast training examples contain duplicate window identities")
    return result


def _validate_target_permutation_v1(
    aligned: Sequence[ForecastExampleV1],
    shuffled: Sequence[ForecastExampleV1],
) -> None:
    if len(aligned) != len(shuffled):
        raise AssertionError("player target permutation changed row count")
    aligned_by_player: dict[str, list[ForecastWindowKeyV1]] = defaultdict(list)
    shuffled_by_player: dict[str, list[ForecastWindowKeyV1]] = defaultdict(list)
    for original, control in zip(aligned, shuffled, strict=True):
        if original.key != control.key or original.tokens != control.tokens:
            raise AssertionError("player target permutation changed inputs")
        player = original.key.player_id
        aligned_by_player[player].append(original.target_source_key)
        shuffled_by_player[player].append(control.target_source_key)
    if set(aligned_by_player) != set(shuffled_by_player):
        raise AssertionError("player target permutation changed player support")
    for player, original_sources in aligned_by_player.items():
        control_sources = shuffled_by_player[player]
        if sorted(original_sources) != sorted(control_sources):
            raise AssertionError("player target permutation changed target multiset")
        if len(original_sources) > 1:
            controls = [
                row for row in shuffled if row.key.player_id == player
            ]
            if any(row.key == row.target_source_key for row in controls):
                raise AssertionError("player target permutation has a fixed point")


def validate_forecast_training_examples_v1(
    examples: Sequence[ForecastExampleV1],
    *,
    eligible_player_ids: Sequence[str],
    trajectory_tape_roots: Sequence[str],
    ineligible_player_ids: Sequence[str] = (),
    forbidden_tape_roots: Sequence[str] = (),
    target_mode: str,
) -> tuple[ForecastExampleV1, ...]:
    """Validate exact train-player, tape-lane, target-mode, and finite support."""

    rows = _exact_example_sequence_v1(examples)
    eligible = _exact_string_set_v1(eligible_player_ids, name="eligible player")
    trajectory = _exact_string_set_v1(
        trajectory_tape_roots, name="trajectory tape"
    )
    if not isinstance(ineligible_player_ids, Sequence) or isinstance(
        ineligible_player_ids, (str, bytes)
    ):
        _fail("ineligible player registry changed")
    if not isinstance(forbidden_tape_roots, Sequence) or isinstance(
        forbidden_tape_roots, (str, bytes)
    ):
        _fail("forbidden tape registry changed")
    if any(
        type(value) is not str or not value
        for value in (*ineligible_player_ids, *forbidden_tape_roots)
    ):
        _fail("ineligible player or forbidden tape registry changed")
    ineligible = frozenset(ineligible_player_ids)
    forbidden = frozenset(forbidden_tape_roots)
    if (
        len(ineligible) != len(ineligible_player_ids)
        or len(forbidden) != len(forbidden_tape_roots)
        or eligible & ineligible
        or trajectory & forbidden
    ):
        _fail("eligible and ineligible forecast registries overlap or duplicate")
    observed_players = frozenset(row.key.player_id for row in rows)
    observed_roots = frozenset(row.key.tape_root for row in rows)
    source_players = frozenset(row.target_source_key.player_id for row in rows)
    source_roots = frozenset(row.target_source_key.tape_root for row in rows)
    if observed_players != eligible or source_players != eligible:
        _fail("forecast examples do not exactly cover eligible train players")
    if observed_players & ineligible or source_players & ineligible:
        _fail("ineligible test player leaked into forecast training")
    if not observed_roots <= trajectory or not source_roots <= trajectory:
        _fail("non-trajectory tape leaked into forecast training")
    if observed_roots & forbidden or source_roots & forbidden:
        _fail("forbidden label or probe tape leaked into forecast training")
    if target_mode not in FORECAST_TARGET_MODES_V1:
        _fail("forecast target mode is not frozen")
    if target_mode == ALIGNED_TARGET_MODE_V1:
        if any(row.key != row.target_source_key for row in rows):
            _fail("aligned forecast training contains a shuffled target")
    else:
        by_player: dict[str, list[ForecastExampleV1]] = defaultdict(list)
        for row in rows:
            by_player[row.key.player_id].append(row)
        for player_rows in by_player.values():
            if len(player_rows) > 1 and any(
                row.key == row.target_source_key for row in player_rows
            ):
                _fail("player-shuffled forecast control contains a fixed point")
            if sorted(row.key for row in player_rows) != sorted(
                row.target_source_key for row in player_rows
            ):
                _fail("player-shuffled forecast control changed target ownership")
    return rows


def forecast_model_factory_v1(torch: Any):
    """Return the one-layer GRU64 plus linear-54 forecast model factory."""

    if not hasattr(torch, "nn"):
        _fail("forecast model factory requires the Torch module")

    class ResourceForecastModelV1(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.encoder = torch.nn.GRU(
                input_size=PREFIX_TOKEN_WIDTH_V1,
                hidden_size=FORECAST_HIDDEN_WIDTH_V1,
                num_layers=1,
                batch_first=True,
            )
            self.forecast_head = torch.nn.Linear(
                FORECAST_HIDDEN_WIDTH_V1, FORECAST_TARGET_DIMENSION_V1
            )

        def encode(self, tokens):
            if tokens.ndim != 3 or tuple(tokens.shape[1:]) != (
                PREFIX_ACTION_COUNT_V1,
                PREFIX_TOKEN_WIDTH_V1,
            ):
                raise LearnedResourceForecast2048V1Error(
                    "forecast model input must be batch by 8 by 21"
                )
            _output, hidden = self.encoder(tokens)
            return hidden[-1]

        def forward(self, tokens):
            return self.forecast_head(self.encode(tokens))

    def build():
        return ResourceForecastModelV1()

    return build


@dataclass(frozen=True, slots=True)
class ForecastTrainingReceiptV1:
    """Outcome-independent receipt for exactly one frozen encoder fit."""

    target_mode: str
    initialization_seed: int
    example_count: int
    player_count: int
    training_loss_by_epoch: tuple[float, ...]
    device_name: str
    encoder_frozen: bool = True
    forecast_head_discarded: bool = True

    def __post_init__(self) -> None:
        if (
            self.target_mode not in FORECAST_TARGET_MODES_V1
            or type(self.initialization_seed) is not int
            or self.initialization_seed < 0
            or type(self.example_count) is not int
            or self.example_count <= 0
            or type(self.player_count) is not int
            or self.player_count <= 0
            or type(self.training_loss_by_epoch) is not tuple
            or len(self.training_loss_by_epoch) != FORECAST_TRAINING_EPOCHS_V1
            or any(
                type(value) is not float or not math.isfinite(value) or value < 0.0
                for value in self.training_loss_by_epoch
            )
            or type(self.device_name) is not str
            or not self.device_name
            or self.encoder_frozen is not True
            or self.forecast_head_discarded is not True
        ):
            _fail("forecast training receipt changed")

    def document(self) -> dict[str, Any]:
        result = {
            "schema": "acfqp.science.resource_forecast_encoder_receipt.v1",
            "target_mode": self.target_mode,
            "initialization_seed": self.initialization_seed,
            "example_count": self.example_count,
            "player_count": self.player_count,
            "input_shape": [PREFIX_ACTION_COUNT_V1, PREFIX_TOKEN_WIDTH_V1],
            "hidden_width": FORECAST_HIDDEN_WIDTH_V1,
            "target_dimension": FORECAST_TARGET_DIMENSION_V1,
            "optimizer": "ADAM",
            "learning_rate": FORECAST_ADAM_LEARNING_RATE_V1,
            "batch_size": FORECAST_BATCH_SIZE_V1,
            "fixed_epoch_count": FORECAST_TRAINING_EPOCHS_V1,
            "training_loss_by_epoch": list(self.training_loss_by_epoch),
            "device_name": self.device_name,
            "encoder_frozen": self.encoder_frozen,
            "forecast_head_discarded": self.forecast_head_discarded,
            "skill_labels_opened_during_training": False,
        }
        json.dumps(result, allow_nan=False, sort_keys=True)
        return result


def train_forecast_encoder_v1(
    examples: Sequence[ForecastExampleV1],
    *,
    eligible_player_ids: Sequence[str],
    trajectory_tape_roots: Sequence[str],
    target_mode: str,
    initialization_seed: int,
    device_name: str = "cpu",
    ineligible_player_ids: Sequence[str] = (),
    forbidden_tape_roots: Sequence[str] = (),
) -> tuple[Any, ForecastTrainingReceiptV1]:
    """Fit exactly 50 fixed epochs and return only the frozen GRU encoder.

    Supplying the same initialization seed and row order gives the aligned and
    shuffled arms identical initialization and minibatch order.  Hyperparameter
    overrides and early stopping are intentionally absent from this interface.
    """

    rows = validate_forecast_training_examples_v1(
        examples,
        eligible_player_ids=eligible_player_ids,
        trajectory_tape_roots=trajectory_tape_roots,
        ineligible_player_ids=ineligible_player_ids,
        forbidden_tape_roots=forbidden_tape_roots,
        target_mode=target_mode,
    )
    rows = tuple(sorted(rows, key=lambda row: row.key))
    if type(initialization_seed) is not int or initialization_seed < 0:
        _fail("forecast initialization seed must be one nonnegative integer")
    if type(device_name) is not str or not device_name:
        _fail("forecast training device changed")
    try:
        import torch
    except ImportError as error:  # pragma: no cover - experiment dependency only
        raise LearnedResourceForecast2048V1Error(
            "Torch is required to train the resource forecast encoder"
        ) from error
    if device_name.startswith("cuda") and not torch.cuda.is_available():
        _fail("requested forecast-training CUDA device is unavailable")
    device = torch.device(device_name)
    previous_deterministic = torch.are_deterministic_algorithms_enabled()
    previous_warn_only = (
        torch.is_deterministic_algorithms_warn_only_enabled()
        if hasattr(torch, "is_deterministic_algorithms_warn_only_enabled")
        else False
    )
    has_cudnn_flags = hasattr(torch.backends, "cudnn")
    previous_cudnn_benchmark = (
        torch.backends.cudnn.benchmark if has_cudnn_flags else None
    )
    previous_cudnn_deterministic = (
        torch.backends.cudnn.deterministic if has_cudnn_flags else None
    )
    try:
        torch.use_deterministic_algorithms(True)
        if has_cudnn_flags:
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
        torch.manual_seed(initialization_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(initialization_seed)
        model = forecast_model_factory_v1(torch)().to(device)
        if _parameter_count(model.encoder) != FORECAST_ENCODER_PARAMETER_COUNT_V1 or (
            _parameter_count(model) != FORECAST_MODEL_PARAMETER_COUNT_V1
        ):
            raise AssertionError("forecast model parameter count changed")
        optimizer = torch.optim.Adam(
            model.parameters(), lr=FORECAST_ADAM_LEARNING_RATE_V1
        )
        tokens = torch.tensor(
            [[list(token) for token in row.tokens] for row in rows],
            dtype=torch.float32,
        )
        targets = torch.tensor(
            [list(row.target) for row in rows], dtype=torch.float32
        )
        if (
            tuple(tokens.shape)
            != (len(rows), PREFIX_ACTION_COUNT_V1, PREFIX_TOKEN_WIDTH_V1)
            or tuple(targets.shape) != (len(rows), FORECAST_TARGET_DIMENSION_V1)
            or not bool(torch.isfinite(tokens).all())
            or not bool(torch.isfinite(targets).all())
        ):
            _fail("forecast training tensor shape or finiteness changed")
        order_generator = torch.Generator(device="cpu")
        order_generator.manual_seed(initialization_seed)
        losses: list[float] = []
        model.train()
        for _epoch in range(FORECAST_TRAINING_EPOCHS_V1):
            order = torch.randperm(len(rows), generator=order_generator)
            total_squared_error = 0.0
            total_values = 0
            for offset in range(0, len(rows), FORECAST_BATCH_SIZE_V1):
                indices = order[offset : offset + FORECAST_BATCH_SIZE_V1]
                batch_tokens = tokens[indices].to(device)
                batch_targets = targets[indices].to(device)
                predictions = model(batch_tokens)
                loss = torch.nn.functional.mse_loss(predictions, batch_targets)
                if not bool(torch.isfinite(loss)):
                    _fail("forecast training produced a nonfinite loss")
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                batch_values = batch_targets.numel()
                total_squared_error += float(loss.detach().cpu()) * batch_values
                total_values += batch_values
            epoch_loss = total_squared_error / total_values
            if not math.isfinite(epoch_loss) or epoch_loss < 0.0:
                _fail("forecast epoch loss became invalid")
            losses.append(float(epoch_loss))
        encoder = model.encoder
        if any(
            not bool(torch.isfinite(parameter).all())
            for parameter in encoder.parameters()
        ):
            _fail("forecast training produced nonfinite encoder parameters")
        encoder.eval()
        for parameter in encoder.parameters():
            parameter.requires_grad_(False)
        receipt = ForecastTrainingReceiptV1(
            target_mode=target_mode,
            initialization_seed=initialization_seed,
            example_count=len(rows),
            player_count=len({row.key.player_id for row in rows}),
            training_loss_by_epoch=tuple(losses),
            device_name=device_name,
        )
        return encoder, receipt
    finally:
        if hasattr(torch, "is_deterministic_algorithms_warn_only_enabled"):
            torch.use_deterministic_algorithms(
                previous_deterministic, warn_only=previous_warn_only
            )
        else:  # pragma: no cover - retained for older experiment Torch only
            torch.use_deterministic_algorithms(previous_deterministic)
        if has_cudnn_flags:
            torch.backends.cudnn.benchmark = previous_cudnn_benchmark
            torch.backends.cudnn.deterministic = previous_cudnn_deterministic


def _validate_frozen_encoder_v1(encoder: Any) -> tuple[Any, Any]:
    try:
        import torch
    except ImportError as error:  # pragma: no cover - experiment dependency only
        raise LearnedResourceForecast2048V1Error(
            "Torch is required to execute the frozen forecast encoder"
        ) from error
    if (
        not isinstance(encoder, torch.nn.GRU)
        or encoder.input_size != PREFIX_TOKEN_WIDTH_V1
        or encoder.hidden_size != FORECAST_HIDDEN_WIDTH_V1
        or encoder.num_layers != 1
        or not encoder.batch_first
        or encoder.training
        or any(parameter.requires_grad for parameter in encoder.parameters())
        or _parameter_count(encoder) != FORECAST_ENCODER_PARAMETER_COUNT_V1
        or any(
            not bool(torch.isfinite(parameter).all())
            for parameter in encoder.parameters()
        )
    ):
        _fail("forecast encoder is not the exact frozen GRU64")
    parameters = tuple(encoder.parameters())
    if not parameters:
        _fail("frozen forecast encoder has no parameters")
    return torch, parameters[0].device


def frozen_embeddings_v1(
    encoder: Any,
    token_matrices: Sequence[tuple[tuple[float, ...], ...]],
) -> tuple[tuple[float, ...], ...]:
    """Return one frozen 64-D final hidden state per eight-action matrix."""

    torch, device = _validate_frozen_encoder_v1(encoder)
    if (
        not isinstance(token_matrices, Sequence)
        or isinstance(token_matrices, (str, bytes))
        or not token_matrices
    ):
        _fail("frozen embedding input must be one nonempty token sequence")
    checked: list[list[list[float]]] = []
    for matrix in token_matrices:
        if (
            type(matrix) is not tuple
            or len(matrix) != PREFIX_ACTION_COUNT_V1
            or any(type(row) is not tuple or len(row) != PREFIX_TOKEN_WIDTH_V1 for row in matrix)
        ):
            _fail("frozen embedding input must be batch by 8 by 21")
        checked.append(
            [
                [_finite_float(value, name="forecast token") for value in row]
                for row in matrix
            ]
        )
    tensor = torch.tensor(checked, dtype=torch.float32, device=device)
    with torch.no_grad():
        _output, hidden = encoder(tensor)
        embeddings = hidden[-1]
    if (
        tuple(embeddings.shape)
        != (len(checked), FORECAST_HIDDEN_WIDTH_V1)
        or not bool(torch.isfinite(embeddings).all())
    ):
        _fail("frozen forecast embedding shape or finiteness changed")
    return tuple(
        tuple(float(value) for value in row)
        for row in embeddings.detach().cpu().tolist()
    )


def frozen_embedding_v1(
    encoder: Any, tokens: tuple[tuple[float, ...], ...]
) -> tuple[float, ...]:
    """Convenience wrapper for one frozen 64-D prefix embedding."""

    return frozen_embeddings_v1(encoder, (tokens,))[0]


def _generator_network_contract_v1(arm: str) -> tuple[int, int]:
    if arm not in HYBRID_CONFIRMATORY_ARMS_V2:
        _fail("policy-generator arm is not one of the three frozen arms")
    if arm == RAW_STANDARD_ARM_V2:
        return RAW_STANDARD_INPUT_DIMENSION_V2, RAW_STANDARD_PARAMETER_COUNT_V2
    return HYBRID_INPUT_DIMENSION_V2, HYBRID_PARAMETER_COUNT_V2


def load_generator_policy_snapshot_v1(
    path: str | Path, *, arm: str, device_name: str = "cpu"
) -> Any:
    """Load one strict bare inference snapshot for any frozen generator arm."""

    input_dimension, expected_parameter_count = _generator_network_contract_v1(arm)
    if type(device_name) is not str or not device_name:
        _fail("policy snapshot device changed")
    checkpoint = Path(path)
    if not checkpoint.is_file():
        _fail("policy snapshot is not a regular file")
    try:
        import torch
    except ImportError as error:  # pragma: no cover - experiment dependency only
        raise LearnedResourceForecast2048V1Error(
            "Torch is required to load a generator policy snapshot"
        ) from error
    if device_name.startswith("cuda") and not torch.cuda.is_available():
        _fail("requested policy-snapshot CUDA device is unavailable")
    device = torch.device(device_name)
    state_dict = torch.load(checkpoint, map_location=device, weights_only=True)
    model = _network_factory(torch, input_dimension)().to(device)
    if (
        not isinstance(state_dict, Mapping)
        or set(state_dict) != set(model.state_dict())
        or any(not torch.is_tensor(value) for value in state_dict.values())
        or any(not bool(torch.isfinite(value).all()) for value in state_dict.values())
    ):
        _fail("policy snapshot is not the exact bare generator state_dict")
    try:
        model.load_state_dict(state_dict, strict=True)
    except (RuntimeError, TypeError) as error:
        raise LearnedResourceForecast2048V1Error(
            "policy snapshot tensor shapes changed"
        ) from error
    if _parameter_count(model) != expected_parameter_count:
        _fail("policy-generator parameter count changed")
    model.eval()
    return model


def greedy_policy_selector_v1(model: Any, *, arm: str):
    """Return a legal-action-masked greedy selector for any generator arm."""

    input_dimension, expected_parameter_count = _generator_network_contract_v1(arm)
    try:
        import torch
    except ImportError as error:  # pragma: no cover - experiment dependency only
        raise LearnedResourceForecast2048V1Error(
            "Torch is required to execute a generator policy"
        ) from error
    if not isinstance(model, torch.nn.Module) or not callable(model):
        _fail("generator policy must be one Torch model")
    parameters = tuple(model.parameters())
    if (
        not parameters
        or _parameter_count(model) != expected_parameter_count
        or any(
            not bool(torch.isfinite(parameter).all())
            for parameter in parameters
        )
        or not hasattr(model, "__getitem__")
        or not isinstance(model[0], torch.nn.Linear)
        or model[0].in_features != input_dimension
    ):
        _fail("generator policy architecture does not match its arm")
    device = parameters[0].device
    model.eval()

    def choose(
        state: standard_2048.Swipe2048State,
        legal_mask: tuple[bool, bool, bool, bool],
    ) -> int:
        if (
            type(state) is not standard_2048.Swipe2048State
            or type(legal_mask) is not tuple
            or len(legal_mask) != 4
            or any(type(value) is not bool for value in legal_mask)
            or not any(legal_mask)
        ):
            _fail("greedy policy received an invalid state or legal mask")
        observation = observation_vector_hybrid_confirmatory_v2(state, arm)
        if len(observation) != input_dimension or any(
            not math.isfinite(value) for value in observation
        ):
            _fail("generator policy observation changed")
        with torch.no_grad():
            values = model(
                torch.tensor(
                    observation, dtype=torch.float32, device=device
                ).unsqueeze(0)
            )[0]
            mask = torch.tensor(legal_mask, dtype=torch.bool, device=device)
            values = values.masked_fill(~mask, float("-inf"))
            action_index = int(torch.argmax(values).item())
        if not legal_mask[action_index]:
            raise AssertionError("greedy selector returned an illegal action")
        return action_index

    return choose


def load_generator_policy_selector_v1(
    path: str | Path, *, arm: str, device_name: str = "cpu"
):
    """Load one snapshot and bind its matching greedy observation adapter."""

    return greedy_policy_selector_v1(
        load_generator_policy_snapshot_v1(path, arm=arm, device_name=device_name),
        arm=arm,
    )


__all__ = (
    "ALIGNED_TARGET_MODE_V1",
    "FORECAST_ADAM_LEARNING_RATE_V1",
    "FORECAST_BATCH_SIZE_V1",
    "FORECAST_ENCODER_PARAMETER_COUNT_V1",
    "FORECAST_HIDDEN_WIDTH_V1",
    "FORECAST_HORIZONS_V1",
    "FORECAST_TARGET_DIMENSION_V1",
    "FORECAST_TARGET_MODES_V1",
    "FORECAST_MODEL_PARAMETER_COUNT_V1",
    "FORECAST_TRAINING_EPOCHS_V1",
    "ForecastExampleV1",
    "ForecastTrainingReceiptV1",
    "ForecastWindowKeyV1",
    "LearnedResourceForecast2048V1Error",
    "MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1",
    "PLAYER_SHUFFLED_TARGET_MODE_V1",
    "PREFIX_ACTION_COUNT_V1",
    "PREFIX_TOKEN_WIDTH_V1",
    "RAW_PREFIX_DIMENSION_V1",
    "TARGET_SHUFFLE_SEED_V1",
    "aligned_forecast_examples_v1",
    "deterministic_window_starts_v1",
    "forecast_model_factory_v1",
    "forecast_target_v1",
    "frozen_embedding_v1",
    "frozen_embeddings_v1",
    "greedy_policy_selector_v1",
    "load_generator_policy_selector_v1",
    "load_generator_policy_snapshot_v1",
    "player_shuffled_targets_v1",
    "prefix_tokens_v1",
    "raw_prefix_v1",
    "train_forecast_encoder_v1",
    "validate_disjoint_lane_roots_v1",
    "validate_forecast_training_examples_v1",
)
