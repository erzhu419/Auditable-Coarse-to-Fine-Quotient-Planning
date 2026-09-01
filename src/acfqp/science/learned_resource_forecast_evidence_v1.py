"""Independent per-player evidence lanes for the 2048 U001 pilot.

Trajectory, probe, and skill-label evidence are returned as separate documents.
That separation is intentional: the later analysis can train and freeze both
encoders from trajectory files, generate probe embeddings, and only then open
the label files.  No document embeds content from another evidence lane.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import io
import json
import math
from pathlib import Path
import re
from typing import Any, NoReturn

from acfqp.domains import standard_2048
from acfqp.science.early_strategic_signature_2048_pilot_v1 import (
    ActionSelectorV1,
    PolicyTraceV1,
    collect_full_game_v1,
    collect_prefix_v1,
)
from acfqp.science.learned_resource_forecast_2048_v1 import (
    FORECAST_TARGET_DIMENSION_V1,
    MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1,
    PREFIX_ACTION_COUNT_V1,
    PREFIX_TOKEN_WIDTH_V1,
    ForecastExampleV1,
    aligned_forecast_examples_v1,
    greedy_policy_selector_v1,
    load_generator_policy_snapshot_v1,
    validate_disjoint_lane_roots_v1,
)
from acfqp.science.learned_resource_forecast_protocol_v1 import (
    LABEL_EPISODES_PER_PLAYER_V1,
    LEARNED_RESOURCE_FORECAST_ARMS_V1,
    LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1,
    LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1,
    LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1,
    PROBES_PER_PLAYER_V1,
    TRAJECTORY_EPISODES_PER_TRAIN_PLAYER_V1,
    player_key_v1,
    validate_ratified_learned_resource_forecast_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_learned_resource_pilot_v1 import (
    policy_checkpoint_filename_v1,
)


TRAJECTORY_EVIDENCE_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_player_trajectory_evidence.v1"
)
LABEL_EVIDENCE_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_player_label_evidence.v1"
)
PROBE_EVIDENCE_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_player_probe_evidence.v1"
)
FORECAST_NPZ_SCHEMA_V1 = (
    "acfqp.science.learned_resource_forecast_aligned_examples_npz.v1"
)


class LearnedResourceForecastEvidenceV1Error(ValueError):
    """One player identity, lane, trace, snapshot, or artifact is invalid."""


def _fail(message: str) -> NoReturn:
    raise LearnedResourceForecastEvidenceV1Error(message)


@dataclass(frozen=True, slots=True)
class PlayerEvidenceArtifactsV1:
    """Separated in-memory artifacts for exactly one policy player."""

    trajectory_document: dict[str, Any] | None
    trajectory_examples: tuple[ForecastExampleV1, ...]
    label_document: dict[str, Any]
    probe_document: dict[str, Any]

    def __post_init__(self) -> None:
        if (
            (self.trajectory_document is not None)
            is not bool(self.trajectory_examples)
            or (
                self.trajectory_document is not None
                and type(self.trajectory_document) is not dict
            )
            or type(self.trajectory_examples) is not tuple
            or any(
                type(example) is not ForecastExampleV1
                for example in self.trajectory_examples
            )
            or type(self.label_document) is not dict
            or type(self.probe_document) is not dict
        ):
            _fail("separated player evidence artifact layout changed")

    @property
    def is_train_player(self) -> bool:
        return self.trajectory_document is not None


def expected_player_evidence_execution_id_v1(
    protocol: Mapping[str, Any],
    *,
    base_seed: int,
    generator_arm: str,
    checkpoint: int,
) -> str:
    """Return the sole registered evidence execution ID for one player."""

    if type(protocol) is not dict:
        _fail("player evidence protocol must be one plain object")
    player_key_v1(base_seed, generator_arm, checkpoint)
    identity = protocol.get("pilot_execution_identity")
    if type(identity) is not str or not identity:
        _fail("player evidence protocol has no pilot execution identity")
    return (
        f"{identity}:player-evidence:{generator_arm}:"
        f"seed:{base_seed}:checkpoint:{checkpoint}"
    )


def player_evidence_artifact_basenames_v1(
    *, base_seed: int, generator_arm: str, checkpoint: int
) -> dict[str, str]:
    """Return stable, lane-specific basenames for one player identity."""

    player_key_v1(base_seed, generator_arm, checkpoint)
    stem = (
        f"{generator_arm.lower()}-seed-{base_seed}-checkpoint-{checkpoint}"
    )
    return {
        "trajectory_json": f"{stem}.trajectory.json",
        "trajectory_npz": f"{stem}.trajectory.npz",
        "label_json": f"{stem}.label.json",
        "probe_json": f"{stem}.probe.json",
    }


def _player_identity_document_v1(
    *,
    base_seed: int,
    generator_arm: str,
    checkpoint: int,
    split: str,
) -> dict[str, Any]:
    if split not in ("TRAIN", "TEST"):
        raise AssertionError("player split changed")
    return {
        "player_key": player_key_v1(base_seed, generator_arm, checkpoint),
        "base_training_seed": base_seed,
        "generator_arm": generator_arm,
        "checkpoint_environment_interactions": checkpoint,
        "split": split,
        "generator_arm_checkpoint_seed_are_not_classifier_inputs": True,
    }


def _validate_execution_context_v1(
    protocol: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    base_seed: int,
    generator_arm: str,
    checkpoint: int,
) -> dict[str, Any]:
    if type(context) is not dict:
        _fail("player evidence execution context must be one plain object")
    required_strings = ("execution_id", "source_commit", "hostname", "device")
    if any(
        type(context.get(name)) is not str or not context[name]
        for name in required_strings
    ):
        _fail("player evidence execution context is incomplete")
    if context["execution_id"] != expected_player_evidence_execution_id_v1(
        protocol,
        base_seed=base_seed,
        generator_arm=generator_arm,
        checkpoint=checkpoint,
    ):
        _fail("player evidence execution ID differs from its registered identity")
    if (
        context["source_commit"] != protocol.get("source_commit")
        or re.fullmatch(r"[0-9a-f]{40}", context["source_commit"]) is None
    ):
        _fail("player evidence source commit differs from its ratified protocol")
    try:
        json.dumps(context, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise LearnedResourceForecastEvidenceV1Error(
            "player evidence execution context is not finite JSON"
        ) from error
    return dict(context)


def _complete_episode_summary_v1(trace: PolicyTraceV1) -> dict[str, Any]:
    if type(trace) is not PolicyTraceV1 or not trace.completed_game:
        _fail("complete episode summary requires one goal-terminated trace")
    result = {
        **trace.label_document(),
        "initial_board": list(trace.states[0].board),
        "terminal_board": list(trace.states[-1].board),
        # This compact action sequence makes every complete episode exactly
        # replayable from its registered lane root and episode index.  We do
        # not retain every intermediate board or tape digest: the transition
        # kernel reconstructs those deterministically.
        "accepted_action_indices": list(trace.action_indices),
        "goal_terminated_episode": True,
        "continue_after_2048": False,
    }
    if (
        len(result["initial_board"]) != standard_2048.CELL_COUNT
        or len(result["terminal_board"]) != standard_2048.CELL_COUNT
        or len(result["accepted_action_indices"]) != result["decision_count"]
    ):
        raise AssertionError("complete episode board summary changed")
    return result


def _probe_row_v1(trace: PolicyTraceV1) -> dict[str, Any]:
    if (
        type(trace) is not PolicyTraceV1
        or len(trace.states) != PREFIX_ACTION_COUNT_V1 + 1
        or len(trace.action_indices) != PREFIX_ACTION_COUNT_V1
        or len(trace.merge_scores) != PREFIX_ACTION_COUNT_V1
    ):
        _fail("probe row requires exactly eight accepted actions")
    result = {
        "episode_index": trace.episode_index,
        "boards_s0_through_s8": [list(state.board) for state in trace.states],
        "action_indices_a0_through_a7": list(trace.action_indices),
        "action_names_a0_through_a7": [
            standard_2048.ACTION_ORDER[index].value
            for index in trace.action_indices
        ],
        "merge_scores": list(trace.merge_scores),
        "spawn_tape_digests": list(trace.tape_digests),
        "status_after_eight_actions": trace.states[-1].status.value,
        "exact_accepted_action_count": PREFIX_ACTION_COUNT_V1,
        "later_state_or_episode_outcome_included": False,
    }
    if (
        len(result["boards_s0_through_s8"]) != 9
        or any(len(board) != 16 for board in result["boards_s0_through_s8"])
        or len(result["action_indices_a0_through_a7"]) != 8
        or len(result["action_names_a0_through_a7"]) != 8
        or len(result["merge_scores"]) != 8
        or len(result["spawn_tape_digests"]) != 8
    ):
        raise AssertionError("eight-action probe serialization changed")
    return result


def _lane_tape_roots_v1(
    protocol: Mapping[str, Any], *, player_key: str
) -> dict[str, str]:
    if type(player_key) is not str or not player_key:
        _fail("lane tape binding requires one player identity")
    base_keys = {
        "trajectory": "trajectory_tape_root",
        "label": "label_tape_root",
        "probe": "probe_tape_root",
    }
    roots: dict[str, str] = {}
    for lane, key in base_keys.items():
        base = protocol.get(key)
        if type(base) is not str or not base:
            _fail("ratified protocol is missing one evidence-lane tape root")
        # Every policy player faces the same episode-indexed tapes within a
        # lane.  Player identity belongs to evidence ownership, never to the
        # environment seed; appending it here would destroy matched evaluation.
        roots[lane] = base
    validate_disjoint_lane_roots_v1(
        trajectory_tape_roots=(roots["trajectory"],),
        skill_label_tape_roots=(roots["label"],),
        probe_tape_roots=(roots["probe"],),
    )
    return roots


def _common_lane_document_v1(
    *,
    schema: str,
    protocol: Mapping[str, Any],
    player_identity: Mapping[str, Any],
    execution_context: Mapping[str, Any],
    snapshot_reference: str,
) -> dict[str, Any]:
    if type(snapshot_reference) is not str or not snapshot_reference:
        _fail("player evidence snapshot reference must be nonempty")
    return {
        "schema": schema,
        "protocol_id": protocol["protocol_id"],
        "source_commit": protocol["source_commit"],
        "pilot_execution_identity": protocol["pilot_execution_identity"],
        "player_identity": dict(player_identity),
        "execution_context": dict(execution_context),
        "policy_snapshot": {
            "path": snapshot_reference,
            "artifact_kind": "INFERENCE_ONLY_BARE_ONLINE_STATE_DICT",
        },
        "goal_terminated_episode_definition": (
            "ENDS_ON_REACH_TILE_2048_OR_NO_LEGAL_ACTION"
        ),
        "continue_after_2048_score_game": False,
        "scientific_success_claimed": False,
    }


def _collect_player_evidence_with_selector_v1(
    *,
    protocol: Mapping[str, Any],
    action_selector: ActionSelectorV1,
    base_seed: int,
    generator_arm: str,
    checkpoint: int,
    execution_context: Mapping[str, Any],
    snapshot_reference: str,
    trajectory_episode_count: int,
    label_episode_count: int,
    probe_count: int,
) -> PlayerEvidenceArtifactsV1:
    """Private count-injectable collector used by tiny deterministic tests."""

    validated = validate_ratified_learned_resource_forecast_protocol_v1(protocol)
    if not callable(action_selector):
        _fail("player evidence action selector must be callable")
    if (
        type(base_seed) is not int
        or base_seed not in LEARNED_RESOURCE_FORECAST_TRAINING_SEEDS_V1
        or generator_arm not in LEARNED_RESOURCE_FORECAST_ARMS_V1
        or type(checkpoint) is not int
        or checkpoint not in LEARNED_RESOURCE_FORECAST_CHECKPOINTS_V1
    ):
        _fail("player evidence identity is outside the frozen roster")
    is_train = base_seed in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
    if is_train is (base_seed in LEARNED_RESOURCE_FORECAST_TEST_SEEDS_V1):
        raise AssertionError("train/test seed partition changed")
    if (
        type(trajectory_episode_count) is not int
        or trajectory_episode_count < 0
        or (is_train and trajectory_episode_count == 0)
        or (not is_train and trajectory_episode_count != 0)
        or type(label_episode_count) is not int
        or label_episode_count <= 0
        or type(probe_count) is not int
        or probe_count <= 0
    ):
        _fail("player evidence lane episode counts changed")
    player_key = player_key_v1(base_seed, generator_arm, checkpoint)
    split = "TRAIN" if is_train else "TEST"
    player_identity = _player_identity_document_v1(
        base_seed=base_seed,
        generator_arm=generator_arm,
        checkpoint=checkpoint,
        split=split,
    )
    context = _validate_execution_context_v1(
        validated,
        execution_context,
        base_seed=base_seed,
        generator_arm=generator_arm,
        checkpoint=checkpoint,
    )
    roots = _lane_tape_roots_v1(validated, player_key=player_key)

    trajectory_document: dict[str, Any] | None = None
    trajectory_examples: list[ForecastExampleV1] = []
    if is_train:
        episode_rows: list[dict[str, Any]] = []
        for episode_index in range(trajectory_episode_count):
            trace = collect_full_game_v1(
                action_selector,
                tape_root=roots["trajectory"],
                episode_index=episode_index,
            )
            episode_examples = aligned_forecast_examples_v1(
                trace, player_id=player_key
            )
            if len(episode_examples) > MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1:
                raise AssertionError("trajectory episode exceeded 32 windows")
            trajectory_examples.extend(episode_examples)
            episode_rows.append(
                {
                    **_complete_episode_summary_v1(trace),
                    "forecast_window_count": len(episode_examples),
                }
            )
        if len(trajectory_examples) > (
            trajectory_episode_count * MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1
        ):
            raise AssertionError("player trajectory evidence exceeded its window cap")
        trajectory_document = {
            **_common_lane_document_v1(
                schema=TRAJECTORY_EVIDENCE_SCHEMA_V1,
                protocol=validated,
                player_identity=player_identity,
                execution_context=context,
                snapshot_reference=snapshot_reference,
            ),
            "lane": "SELF_SUPERVISED_TRAJECTORY",
            "trajectory_tape_root": roots["trajectory"],
            "complete_episode_count": trajectory_episode_count,
            "complete_episode_summaries": episode_rows,
            "forecast_example_count": len(trajectory_examples),
            "maximum_forecast_examples": (
                trajectory_episode_count
                * MAX_WINDOWS_PER_COMPLETE_TRAJECTORY_V1
            ),
            "forecast_examples_artifact_schema": FORECAST_NPZ_SCHEMA_V1,
            "forecast_array_contract": {
                "tokens": [len(trajectory_examples), 8, 21],
                "targets": [len(trajectory_examples), 54],
                "episode_index": [len(trajectory_examples)],
                "window_start": [len(trajectory_examples)],
                "tokens_dtype": "float32",
                "targets_dtype": "float32",
                "identity_dtype": "int64",
                "targets_are_aligned": True,
            },
            "skill_label_file_opened": False,
        }

    label_rows: list[dict[str, Any]] = []
    for episode_index in range(label_episode_count):
        trace = collect_full_game_v1(
            action_selector,
            tape_root=roots["label"],
            episode_index=episode_index,
        )
        label_rows.append(_complete_episode_summary_v1(trace))
    total_score_sum = sum(row["total_merge_score"] for row in label_rows)
    mean_total_merge_score = total_score_sum / label_episode_count
    if not math.isfinite(mean_total_merge_score) or mean_total_merge_score < 0.0:
        raise AssertionError("player label mean score changed")
    label_document = {
        **_common_lane_document_v1(
            schema=LABEL_EVIDENCE_SCHEMA_V1,
            protocol=validated,
            player_identity=player_identity,
            execution_context=context,
            snapshot_reference=snapshot_reference,
        ),
        "lane": "INDEPENDENT_SKILL_LABEL",
        "label_tape_root": roots["label"],
        "complete_episode_count": label_episode_count,
        "complete_episode_summaries": label_rows,
        "skill_score": {
            "kind": "MEAN_TOTAL_MERGE_SCORE",
            "total_merge_score_sum": total_score_sum,
            "episode_count": label_episode_count,
            "mean_total_merge_score": mean_total_merge_score,
        },
        "skill_class_assigned": False,
        "train_thresholds_read": False,
    }

    probe_rows: list[dict[str, Any]] = []
    for episode_index in range(probe_count):
        trace = collect_prefix_v1(
            action_selector,
            tape_root=roots["probe"],
            episode_index=episode_index,
        )
        probe_rows.append(_probe_row_v1(trace))
    probe_document = {
        **_common_lane_document_v1(
            schema=PROBE_EVIDENCE_SCHEMA_V1,
            protocol=validated,
            player_identity=player_identity,
            execution_context=context,
            snapshot_reference=snapshot_reference,
        ),
        "lane": "EIGHT_ACTION_NATURAL_OPENING_PROBE",
        "probe_tape_root": roots["probe"],
        "probe_count": probe_count,
        "exact_accepted_actions_per_probe": PREFIX_ACTION_COUNT_V1,
        "probe_rows": probe_rows,
        "skill_label_or_complete_outcome_included": False,
    }

    for document in (trajectory_document, label_document, probe_document):
        if document is not None:
            try:
                json.dumps(document, allow_nan=False, sort_keys=True)
            except (TypeError, ValueError) as error:
                raise LearnedResourceForecastEvidenceV1Error(
                    "player evidence document is not finite JSON"
                ) from error
    return PlayerEvidenceArtifactsV1(
        trajectory_document=trajectory_document,
        trajectory_examples=tuple(trajectory_examples),
        label_document=label_document,
        probe_document=probe_document,
    )


def collect_registered_player_evidence_v1(
    *,
    protocol: Mapping[str, Any],
    snapshot_path: str | Path,
    base_seed: int,
    generator_arm: str,
    checkpoint: int,
    device_name: str,
    execution_context: Mapping[str, Any],
) -> PlayerEvidenceArtifactsV1:
    """Load one registered snapshot and collect all eligible separated lanes."""

    validated = validate_ratified_learned_resource_forecast_protocol_v1(protocol)
    snapshot = Path(snapshot_path)
    expected_name = policy_checkpoint_filename_v1(
        arm=generator_arm, seed=base_seed, checkpoint=checkpoint
    )
    if snapshot.name != expected_name:
        _fail("policy snapshot filename differs from the player identity")
    model = load_generator_policy_snapshot_v1(
        snapshot, arm=generator_arm, device_name=device_name
    )
    selector = greedy_policy_selector_v1(model, arm=generator_arm)
    is_train = base_seed in LEARNED_RESOURCE_FORECAST_TRAIN_SEEDS_V1
    return _collect_player_evidence_with_selector_v1(
        protocol=validated,
        action_selector=selector,
        base_seed=base_seed,
        generator_arm=generator_arm,
        checkpoint=checkpoint,
        execution_context=execution_context,
        snapshot_reference=str(snapshot.resolve()),
        trajectory_episode_count=(
            TRAJECTORY_EPISODES_PER_TRAIN_PLAYER_V1 if is_train else 0
        ),
        label_episode_count=LABEL_EPISODES_PER_PLAYER_V1,
        probe_count=PROBES_PER_PLAYER_V1,
    )


def forecast_examples_npz_bytes_v1(
    examples: Sequence[ForecastExampleV1],
) -> bytes:
    """Serialize aligned examples as one compressed, non-pickle NPZ payload."""

    if (
        not isinstance(examples, Sequence)
        or isinstance(examples, (str, bytes))
        or not examples
        or any(type(example) is not ForecastExampleV1 for example in examples)
    ):
        _fail("trajectory NPZ requires one nonempty exact forecast sequence")
    rows = tuple(examples)
    player_ids = {row.key.player_id for row in rows}
    tape_roots = {row.key.tape_root for row in rows}
    keys = {row.key for row in rows}
    if (
        len(player_ids) != 1
        or len(tape_roots) != 1
        or len(keys) != len(rows)
        or any(row.key != row.target_source_key for row in rows)
    ):
        _fail("trajectory NPZ examples changed player, tape, identity, or alignment")
    try:
        import numpy as np
    except ImportError as error:  # pragma: no cover - execution dependency only
        raise LearnedResourceForecastEvidenceV1Error(
            "NumPy is required to serialize trajectory examples"
        ) from error
    tokens = np.asarray([row.tokens for row in rows], dtype=np.float32)
    targets = np.asarray([row.target for row in rows], dtype=np.float32)
    episode_index = np.asarray(
        [row.key.episode_index for row in rows], dtype=np.int64
    )
    window_start = np.asarray(
        [row.key.window_start for row in rows], dtype=np.int64
    )
    if (
        tokens.shape != (len(rows), PREFIX_ACTION_COUNT_V1, PREFIX_TOKEN_WIDTH_V1)
        or targets.shape != (len(rows), FORECAST_TARGET_DIMENSION_V1)
        or episode_index.shape != (len(rows),)
        or window_start.shape != (len(rows),)
        or not bool(np.isfinite(tokens).all())
        or not bool(np.isfinite(targets).all())
        or bool((episode_index < 0).any())
        or bool((window_start < 0).any())
    ):
        _fail("trajectory NPZ array shape, dtype, or finiteness changed")
    output = io.BytesIO()
    np.savez_compressed(
        output,
        tokens=tokens,
        targets=targets,
        episode_index=episode_index,
        window_start=window_start,
    )
    return output.getvalue()


__all__ = (
    "FORECAST_NPZ_SCHEMA_V1",
    "LABEL_EVIDENCE_SCHEMA_V1",
    "LearnedResourceForecastEvidenceV1Error",
    "PROBE_EVIDENCE_SCHEMA_V1",
    "PlayerEvidenceArtifactsV1",
    "TRAJECTORY_EVIDENCE_SCHEMA_V1",
    "collect_registered_player_evidence_v1",
    "expected_player_evidence_execution_id_v1",
    "forecast_examples_npz_bytes_v1",
    "player_evidence_artifact_basenames_v1",
)
