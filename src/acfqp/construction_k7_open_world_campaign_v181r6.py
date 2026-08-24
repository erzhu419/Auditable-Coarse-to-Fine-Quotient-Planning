"""V181r6 matched campaign with a safe prior and persistent rank cache.

The acquisition policy is witness blind and identical in both arms.  Once a
compiled model covers a fresh confirmation block, adding that block cannot
make a previously infeasible shorter program feasible.  Both arms use the same
confidence formula.  A selected archive reference contributes at most one
confirmation unit only after it has been evaluated on all current raw rows;
the archive never discounts MDL or extends the current grammar.  During
execution, local ground rows remain certificate-failure-only, while one exact
rank cache is retained until the compiled-model identity changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
from typing import Any, Iterable, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v181r6 as domains
from acfqp import construction_k7_open_world_manifest_reveals_v181r6 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r6 as protocol
from acfqp.open_world_compiled_model_v181r6 import (
    CompiledWorldModelV181R6,
    compile_world_model_v181r6,
)
from acfqp.open_world_rank_decreasing_planner_v181r6 import (
    RankDecreasingPlannerSessionV181R6,
)
from acfqp.open_world_transition_oracle_v181 import (
    OpaqueTransitionOracleV181,
    RawTransitionObservationV181,
    reveal_opaque_transition_oracle_v181,
)
from acfqp.open_world_universal_synthesizer_v181 import ExpressionV181
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ARMS = ("REUSED_SUBPROGRAM_PRIOR", "EMPTY_ARCHIVE_NO_PRIOR")
QUERY_BLOCK_SIZE = 16
REPEAT_COUNT = 2
MINIMUM_LABEL_COUNT = 32
MAXIMUM_LABEL_COUNT = 256
STABLE_CONFIRMATION_BLOCKS = 2
MAXIMUM_ENUMERATION_EVENTS_PER_EXPRESSION = 2_000_000
MAXIMUM_TARGET_GROUND_LABELS = 32
MAXIMUM_DECISIONS = 64
IID_OCCURRENCES_PER_ARM = 12


class OpenWorldCampaignV181R6Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldCampaignV181R6Error(message)


def _oracle(manifest_index: int) -> OpaqueTransitionOracleV181:
    document = reveals.MANIFEST_DOCUMENTS_V181R6[manifest_index]
    return reveal_opaque_transition_oracle_v181(
        manifest_bytes=canonical_json_bytes(document),
        expected_commitment=protocol.MANIFEST_COMMITMENTS_V181R6[manifest_index],
    )


def _acquisition_input(
    oracle: OpaqueTransitionOracleV181,
    *,
    unique_index: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    digest = hashlib.sha256(
        b"acfqp:v181r6:witness-blind-acquisition\x00"
        + oracle.manifest_commitment.encode()
        + unique_index.to_bytes(8, "big")
    ).digest()
    state = tuple(
        digest[index] % modulus for index, modulus in enumerate(oracle.moduli)
    )
    action = tuple(digest[16 + index] % 3 for index in range(oracle.action_width))
    return state, action


def _covers(
    model: CompiledWorldModelV181R6,
    row: RawTransitionObservationV181,
) -> bool:
    return (
        row.successor in model.predict_support(row.state, row.action)
        and model.terminal(row.successor) is row.terminal
    )


class DurableProgressV181R6:
    """Append-only exact progress with episode-resolution checkpoints."""

    def __init__(self, directory: Path, execution_preregistration_id: str) -> None:
        if (
            not isinstance(directory, Path)
            or not directory.is_dir()
            or type(execution_preregistration_id) is not str
            or len(execution_preregistration_id) != 64
        ):
            _fail("durable progress binding changed")
        if sorted(directory.glob("checkpoint-*.json")):
            _fail("V181r6 scientific progress directory must begin fresh")
        self._directory = directory
        self._execution_preregistration_id = execution_preregistration_id
        self._sequence = 0
        self._previous_id: str | None = None
        self._checkpoint_ids: list[str] = []
        self._last_resolution: dict[str, Any] | None = None

    @property
    def checkpoint_ids(self) -> tuple[str, ...]:
        return tuple(self._checkpoint_ids)

    @property
    def last_checkpoint_id(self) -> str | None:
        return self._previous_id

    @property
    def last_resolution(self) -> dict[str, Any] | None:
        return dict(self._last_resolution) if self._last_resolution is not None else None

    def append(
        self,
        *,
        stage: str,
        manifest_index: int,
        arm: str | None,
        block_index: int | None,
        occurrence_index: int | None = None,
        decision_index: int | None = None,
        observations: Sequence[RawTransitionObservationV181] = (),
        compiled_model: CompiledWorldModelV181R6 | None = None,
        event_document: dict[str, Any] | None = None,
        failure: BaseException | None = None,
        row_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        if (
            type(stage) is not str
            or type(manifest_index) is not int
            or not 0 <= manifest_index < 3
            or arm not in {*ARMS, None}
            or (block_index is not None and type(block_index) is not int)
            or (occurrence_index is not None and type(occurrence_index) is not int)
            or (decision_index is not None and type(decision_index) is not int)
            or any(type(row) is not RawTransitionObservationV181 for row in observations)
            or (event_document is not None and type(event_document) is not dict)
            or any(type(value) is not str or len(value) != 64 for value in row_ids)
        ):
            _fail("durable progress checkpoint input changed")
        payload = {
            "schema": "acfqp.open_world_progress_checkpoint.v181r6",
            "execution_preregistration_id": self._execution_preregistration_id,
            "sequence": self._sequence,
            "previous_checkpoint_id": self._previous_id,
            "stage": stage,
            "manifest_index": manifest_index,
            "arm": arm,
            "block_index": block_index,
            "occurrence_index": occurrence_index,
            "decision_index": decision_index,
            "source_label_count": len(observations),
            "source_observations": [row.to_document() for row in observations],
            "compiled_model": (
                compiled_model.to_document() if compiled_model is not None else None
            ),
            "event_document": event_document,
            "failure_type": type(failure).__name__ if failure is not None else None,
            "failure_message": str(failure) if failure is not None else None,
            "completed_row_ids": list(row_ids),
            "target_outcome_progress_not_success_claim": True,
            "official_execution_allowed": False,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        }
        document = {
            **payload,
            "progress_checkpoint_id": domains.extension_content_id_v181r6(
                domains.CONSTRUCTION_K7_PROGRESS_CHECKPOINT_V181R6_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        path = self._directory / f"checkpoint-{self._sequence:04d}.json"
        try:
            with path.open("xb") as stream:
                if stream.write(raw) != len(raw):
                    _fail("durable progress short write")
                stream.flush()
                os.fsync(stream.fileno())
            directory_fd = os.open(
                self._directory,
                os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except FileExistsError:
            if path.read_bytes() != raw:
                _fail("existing durable progress checkpoint changed")
        if path.read_bytes() != raw:
            _fail("durable progress reread changed")
        self._previous_id = document["progress_checkpoint_id"]
        self._checkpoint_ids.append(self._previous_id)
        self._last_resolution = {
            "stage": stage,
            "manifest_index": manifest_index,
            "arm": arm,
            "block_index": block_index,
            "occurrence_index": occurrence_index,
            "decision_index": decision_index,
        }
        self._sequence += 1
        return document


@dataclass(frozen=True, slots=True)
class _AcquisitionV181R6:
    arm: str
    observations: tuple[RawTransitionObservationV181, ...]
    model: CompiledWorldModelV181R6
    block_history: tuple[dict[str, Any], ...]
    stopped: bool
    stable_confirmation_count: int
    revalidated_prior_confirmation_credit: int
    effective_confirmation_count: int
    recompilation_count: int
    covered_recompilation_skip_count: int
    cumulative_enumeration_events: int
    input_archive_size: int

    def to_document(self) -> dict[str, Any]:
        return {
            "arm": self.arm,
            "source_label_count": len(self.observations),
            "source_observations": [row.to_document() for row in self.observations],
            "compiled_model": self.model.to_document(),
            "block_history": list(self.block_history),
            "stopped": self.stopped,
            "stable_confirmation_count": self.stable_confirmation_count,
            "revalidated_prior_confirmation_credit": (
                self.revalidated_prior_confirmation_credit
            ),
            "effective_confirmation_count": self.effective_confirmation_count,
            "recompilation_count": self.recompilation_count,
            "covered_recompilation_skip_count": self.covered_recompilation_skip_count,
            "cumulative_enumeration_events": self.cumulative_enumeration_events,
            "input_archive_size": self.input_archive_size,
            "same_synthesizer_and_stop_rule": True,
            "same_confidence_formula_both_arms": True,
            "archive_mdl_discount_used": False,
            "prior_credit_requires_selected_archive_reference": True,
            "prior_credit_revalidated_on_all_current_rows": True,
            "manifest_program_read_by_acquisition": False,
            "zero_error_confirmation_recompile_required": False,
        }


def _acquire(
    oracle: OpaqueTransitionOracleV181,
    *,
    manifest_index: int,
    arm: str,
    archive: Iterable[ExpressionV181],
    progress: DurableProgressV181R6,
) -> _AcquisitionV181R6:
    frozen_archive = tuple(archive)
    observations: list[RawTransitionObservationV181] = []
    history: list[dict[str, Any]] = []
    model: CompiledWorldModelV181R6 | None = None
    stable = 0
    prior_credit = 0
    recompilations = 0
    skipped = 0
    cumulative_events = 0
    stopped = False
    acquisition_occurrence = 40_000 + manifest_index
    for block_index in range(MAXIMUM_LABEL_COUNT // QUERY_BLOCK_SIZE):
        block: list[RawTransitionObservationV181] = []
        for local_unique in range(QUERY_BLOCK_SIZE // REPEAT_COUNT):
            unique_index = block_index * (QUERY_BLOCK_SIZE // REPEAT_COUNT) + local_unique
            state, action = _acquisition_input(oracle, unique_index=unique_index)
            for repeat_index in range(REPEAT_COUNT):
                query_index = (
                    block_index * QUERY_BLOCK_SIZE
                    + local_unique * REPEAT_COUNT
                    + repeat_index
                )
                block.append(
                    oracle.query(
                        occurrence_index=acquisition_occurrence,
                        query_index=query_index,
                        state=state,
                        action=action,
                    )
                )
        covered = model is not None and all(_covers(model, row) for row in block)
        observations.extend(block)
        if len(observations) < MINIMUM_LABEL_COUNT:
            history.append(
                {
                    "block_index": block_index,
                    "cumulative_source_label_count": len(observations),
                    "compiled": False,
                    "model_reused_without_recompile": False,
                    "confirmation_zero_error": False,
                    "stable_confirmation_count": stable,
                    "revalidated_prior_confirmation_credit": prior_credit,
                    "effective_confirmation_count": stable + prior_credit,
                    "enumeration_events": 0,
                }
            )
            progress.append(
                stage="ACQUISITION_BLOCK_RETAINED_BEFORE_MINIMUM",
                manifest_index=manifest_index,
                arm=arm,
                block_index=block_index,
                observations=tuple(observations),
            )
            continue
        if covered:
            stable += 1
            skipped += 1
            assert model is not None
            history.append(
                {
                    "block_index": block_index,
                    "cumulative_source_label_count": len(observations),
                    "compiled": False,
                    "model_reused_without_recompile": True,
                    "confirmation_zero_error": True,
                    "stable_confirmation_count": stable,
                    "revalidated_prior_confirmation_credit": prior_credit,
                    "effective_confirmation_count": stable + prior_credit,
                    "enumeration_events": 0,
                }
            )
            progress.append(
                stage="ACQUISITION_BLOCK_COVERED_NO_RECOMPILE",
                manifest_index=manifest_index,
                arm=arm,
                block_index=block_index,
                observations=tuple(observations),
                compiled_model=model,
                event_document={
                    "covered_observation_count": len(block),
                    "compiled_model_id": model.compiled_model_id,
                    "monotone_constraint_addition_cannot_enable_rejected_program": True,
                    "enumeration_events": 0,
                    "revalidated_prior_confirmation_credit": prior_credit,
                    "effective_confirmation_count": stable + prior_credit,
                },
            )
            if stable + prior_credit >= STABLE_CONFIRMATION_BLOCKS:
                stopped = True
                break
            continue
        try:
            model = compile_world_model_v181r6(
                tuple(observations),
                maximum_enumeration_events_per_expression=(
                    MAXIMUM_ENUMERATION_EVENTS_PER_EXPRESSION
                ),
                archive=frozen_archive,
            )
        except BaseException as error:
            progress.append(
                stage="ACQUISITION_BLOCK_COMPILE_FAILED",
                manifest_index=manifest_index,
                arm=arm,
                block_index=block_index,
                observations=tuple(observations),
                failure=error,
            )
            raise
        stable = 0
        prior_credit = int(
            arm == ARMS[0]
            and model.archive_reference_count > 0
            and model.to_document()["archive_mdl_discount_used"] is False
            and model.to_document()[
                "archive_reference_revalidated_on_current_rows"
            ]
            is True
        )
        recompilations += 1
        cumulative_events += model.total_enumeration_events
        history.append(
            {
                "block_index": block_index,
                "cumulative_source_label_count": len(observations),
                "compiled": True,
                "compiled_model_id": model.compiled_model_id,
                "model_reused_without_recompile": False,
                "confirmation_zero_error": False,
                "stable_confirmation_count": stable,
                "revalidated_prior_confirmation_credit": prior_credit,
                "effective_confirmation_count": stable + prior_credit,
                "enumeration_events": model.total_enumeration_events,
            }
        )
        progress.append(
            stage="ACQUISITION_BLOCK_COMPILED",
            manifest_index=manifest_index,
            arm=arm,
            block_index=block_index,
            observations=tuple(observations),
            compiled_model=model,
        )
    if model is None:
        _fail("acquisition ended without one compiled model")
    result = _AcquisitionV181R6(
        arm,
        tuple(observations),
        model,
        tuple(history),
        stopped,
        stable,
        prior_credit,
        stable + prior_credit,
        recompilations,
        skipped,
        cumulative_events,
        len(frozen_archive),
    )
    progress.append(
        stage="ACQUISITION_ARM_COMPLETE",
        manifest_index=manifest_index,
        arm=arm,
        block_index=history[-1]["block_index"],
        observations=result.observations,
        compiled_model=result.model,
    )
    return result


def _fallback_action(
    oracle: OpaqueTransitionOracleV181,
    *,
    occurrence_index: int,
    decision_index: int,
    state: Sequence[int],
) -> tuple[int, ...]:
    actions = oracle.legal_actions()
    digest = hashlib.sha256(
        b"acfqp:v181r6:certificate-failure-fallback\x00"
        + oracle.manifest_commitment.encode()
        + canonical_json_bytes(
            {
                "occurrence_index": occurrence_index,
                "decision_index": decision_index,
                "state": list(state),
            }
        )
    ).digest()
    return actions[int.from_bytes(digest[:8], "big") % len(actions)]


def _changed_dependencies(
    model: CompiledWorldModelV181R6,
    row: RawTransitionObservationV181,
) -> list[list[Any]]:
    dependencies: set[tuple[str, int]] = set()
    support = model.predict_support(row.state, row.action)
    for coordinate, compiled in enumerate(model.coordinates):
        if row.successor[coordinate] not in {
            successor[coordinate] for successor in support
        }:
            dependencies.update(compiled.dependencies)
    if model.terminal(row.successor) is not row.terminal:
        dependencies.update(model.terminal_dependencies)
    return [list(value) for value in sorted(dependencies)]


@dataclass(frozen=True, slots=True)
class _EpisodeOutcomeV181R6:
    document: dict[str, Any]
    model: CompiledWorldModelV181R6
    training_rows: tuple[RawTransitionObservationV181, ...]
    planner_session: RankDecreasingPlannerSessionV181R6


def _episode(
    oracle: OpaqueTransitionOracleV181,
    *,
    manifest_index: int,
    occurrence_index: int,
    arm: str,
    initial_model: CompiledWorldModelV181R6,
    initial_planner_session: RankDecreasingPlannerSessionV181R6,
    initial_training_rows: Sequence[RawTransitionObservationV181],
    archive: Iterable[ExpressionV181],
    progress: DurableProgressV181R6,
) -> _EpisodeOutcomeV181R6:
    model = initial_model
    planner_session = initial_planner_session
    if planner_session.compiled_model_id != model.compiled_model_id:
        _fail("planner cache crossed a compiled-model identity")
    planner_cache_entries_before_episode = planner_session.cached_subproblem_count
    training_rows = list(initial_training_rows)
    frozen_archive = tuple(archive)
    state = oracle.initial_state(occurrence_index)
    initial_state = state
    steps: list[dict[str, Any]] = []
    target_ground_labels = 0
    execution_steps = 0
    planning_events = 0
    certificate_events = 0
    recompile_events = 0
    covered_recompile_skips = 0
    recompile_enumeration_events = 0
    terminal_reached = model.terminal(state)
    model_id_before_episode = model.compiled_model_id
    for decision_index in range(MAXIMUM_DECISIONS):
        if terminal_reached:
            break
        certificate = planner_session.certify(state)
        certificate_events += 1
        planning_events += certificate.planning_compute_events
        if certificate.certified:
            if certificate.selected_action is None:
                _fail("certified nonterminal plan omitted action")
            action = certificate.selected_action
            plan_mode = "ABSTRACT_CERTIFIED"
            pre_execution_failure = False
        else:
            if target_ground_labels >= MAXIMUM_TARGET_GROUND_LABELS:
                break
            action = _fallback_action(
                oracle,
                occurrence_index=occurrence_index,
                decision_index=decision_index,
                state=state,
            )
            plan_mode = "CERTIFICATE_FAILURE_LOCAL_GROUND_FALLBACK"
            pre_execution_failure = True
        row = oracle.query(
            occurrence_index=occurrence_index,
            query_index=4_000_000 + occurrence_index * 100 + decision_index,
            state=state,
            action=action,
        )
        execution_steps += 1
        support_match = row.successor in model.predict_support(state, action)
        terminal_match = model.terminal(row.successor) is row.terminal
        post_execution_failure = not support_match or not terminal_match
        local_ground = pre_execution_failure or post_execution_failure
        dependencies = _changed_dependencies(model, row) if post_execution_failure else []
        model_id_before = model.compiled_model_id
        recompiled_model_id = None
        if local_ground:
            target_ground_labels += 1
            training_rows.append(row)
        if post_execution_failure:
            model = compile_world_model_v181r6(
                tuple(training_rows),
                maximum_enumeration_events_per_expression=(
                    MAXIMUM_ENUMERATION_EVENTS_PER_EXPRESSION
                ),
                archive=frozen_archive,
            )
            recompile_events += 1
            recompile_enumeration_events += model.total_enumeration_events
            recompiled_model_id = model.compiled_model_id
            planner_session = RankDecreasingPlannerSessionV181R6(
                model,
                legal_actions=oracle.legal_actions(),
                horizon=oracle.horizon,
            )
            progress.append(
                stage="EPISODE_MODEL_MISMATCH_RECOMPILED",
                manifest_index=manifest_index,
                arm=arm,
                block_index=None,
                occurrence_index=occurrence_index,
                decision_index=decision_index,
                compiled_model=model,
                event_document={
                    "execution_observation": row.to_document(),
                    "model_id_before": model_id_before,
                    "model_id_after": model.compiled_model_id,
                    "minimal_invalidated_dependencies": dependencies,
                    "support_match": support_match,
                    "terminal_match": terminal_match,
                },
                row_ids=(row.observation_id,),
            )
        elif local_ground:
            covered_recompile_skips += 1
        steps.append(
            {
                "decision_index": decision_index,
                "state": list(state),
                "plan_mode": plan_mode,
                "certificate": certificate.to_document(),
                "action": list(action),
                "execution_observation": row.to_document(),
                "support_match": support_match,
                "terminal_match": terminal_match,
                "local_ground_distinction_acquired": local_ground,
                "certificate_failure_kinds": [
                    kind
                    for present, kind in (
                        (pre_execution_failure, "PRE_EXECUTION_UNCERTIFIED"),
                        (post_execution_failure, "POST_EXECUTION_MODEL_MISMATCH"),
                    )
                    if present
                ],
                "minimal_invalidated_dependencies": dependencies,
                "model_id_before": model_id_before,
                "recompiled_model_id": recompiled_model_id,
                "covered_local_ground_recompile_skipped": (
                    local_ground and not post_execution_failure
                ),
            }
        )
        state = row.successor
        terminal_reached = row.terminal
    payload = {
        "schema": "acfqp.open_world_episode.v181r6",
        "manifest_index": manifest_index,
        "manifest_commitment": oracle.manifest_commitment,
        "arm": arm,
        "occurrence_index": occurrence_index,
        "initial_state": list(initial_state),
        "horizon": oracle.horizon,
        "model_id_before_episode": model_id_before_episode,
        "model_id_after_episode": model.compiled_model_id,
        "steps": steps,
        "terminal_reached": terminal_reached,
        "final_state": list(state),
        "target_ground_label_count": target_ground_labels,
        "execution_step_count": execution_steps,
        "planning_compute_events": planning_events,
        "certificate_event_count": certificate_events,
        "model_recompilation_count": recompile_events,
        "covered_recompilation_skip_count": covered_recompile_skips,
        "recompilation_enumeration_events": recompile_enumeration_events,
        "planner_received_raw_source_rows": False,
        "planner_cache_entries_before_episode": planner_cache_entries_before_episode,
        "planner_cache_entries_after_episode": planner_session.cached_subproblem_count,
        "planner_cache_discarded_only_after_model_identity_change": True,
        "every_local_ground_distinction_has_certificate_failure": all(
            (not step["local_ground_distinction_acquired"])
            or bool(step["certificate_failure_kinds"])
            for step in steps
        ),
        "every_recompile_has_post_execution_model_mismatch": all(
            step["recompiled_model_id"] is None
            or "POST_EXECUTION_MODEL_MISMATCH"
            in step["certificate_failure_kinds"]
            for step in steps
        ),
        "every_certified_action_has_strict_rank_decrease": all(
            step["plan_mode"] != "ABSTRACT_CERTIFIED"
            or step["certificate"]["strict_rank_decrease_proved"] is True
            for step in steps
        ),
        "every_certificate_uses_persistent_model_bound_rank_cache": all(
            step["certificate"]["persistent_model_bound_rank_cache_used"] is True
            for step in steps
        ),
    }
    payload["episode_id"] = hashlib.sha256(
        b"acfqp:v181r6:episode\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    progress.append(
        stage="EPISODE_COMPLETE",
        manifest_index=manifest_index,
        arm=arm,
        block_index=None,
        occurrence_index=occurrence_index,
        decision_index=(steps[-1]["decision_index"] if steps else None),
        compiled_model=model,
        event_document={
            "episode_id": payload["episode_id"],
            "terminal_reached": terminal_reached,
            "target_ground_label_count": target_ground_labels,
            "execution_step_count": execution_steps,
            "model_recompilation_count": recompile_events,
            "covered_recompilation_skip_count": covered_recompile_skips,
        },
        row_ids=(payload["episode_id"],),
    )
    return _EpisodeOutcomeV181R6(
        payload,
        model,
        tuple(training_rows),
        planner_session,
    )


def _sum_axis(distributions: Sequence[dict[str, Any]], arm: str, key: str) -> int:
    total = 0
    for distribution in distributions:
        acquisition = distribution["acquisitions"][arm]
        episodes = distribution["episodes"][arm]
        if key == "OFFLINE_SOURCE_LABELS":
            total += acquisition["source_label_count"]
        elif key == "TARGET_GROUND_LABELS":
            total += sum(row["target_ground_label_count"] for row in episodes)
        elif key == "EXECUTION_STEPS":
            total += sum(row["execution_step_count"] for row in episodes)
        elif key == "PROGRAM_ENUMERATION_EVENTS":
            total += acquisition["cumulative_enumeration_events"]
            total += sum(row["recompilation_enumeration_events"] for row in episodes)
        elif key == "PLANNING_EVENTS":
            total += sum(row["planning_compute_events"] for row in episodes)
        elif key == "CERTIFICATE_EVENTS":
            total += sum(row["certificate_event_count"] for row in episodes)
        elif key == "MODEL_RECOMPILATIONS":
            total += acquisition["recompilation_count"]
            total += sum(row["model_recompilation_count"] for row in episodes)
        else:
            _fail("unknown work-vector axis")
    return total


def _run_arm_episodes(
    oracle: OpaqueTransitionOracleV181,
    *,
    manifest_index: int,
    acquisition: _AcquisitionV181R6,
    archive: Iterable[ExpressionV181],
    progress: DurableProgressV181R6,
) -> tuple[list[dict[str, Any]], CompiledWorldModelV181R6]:
    model = acquisition.model
    rows: tuple[RawTransitionObservationV181, ...] = acquisition.observations
    documents: list[dict[str, Any]] = []
    planner_session = RankDecreasingPlannerSessionV181R6(
        model,
        legal_actions=oracle.legal_actions(),
        horizon=oracle.horizon,
    )
    for occurrence_index in range(IID_OCCURRENCES_PER_ARM):
        outcome = _episode(
            oracle,
            manifest_index=manifest_index,
            occurrence_index=occurrence_index,
            arm=acquisition.arm,
            initial_model=model,
            initial_planner_session=planner_session,
            initial_training_rows=rows,
            archive=archive,
            progress=progress,
        )
        documents.append(outcome.document)
        model = outcome.model
        rows = outcome.training_rows
        planner_session = outcome.planner_session
    return documents, model


def _campaign_payload(
    *,
    execution_preregistration_id: str,
    progress: DurableProgressV181R6,
) -> dict[str, Any]:
    distributions: list[dict[str, Any]] = []
    reusable_archive: tuple[ExpressionV181, ...] = ()
    for manifest_index in range(3):
        oracle = _oracle(manifest_index)
        archive_before = reusable_archive
        prior = _acquire(
            oracle,
            manifest_index=manifest_index,
            arm=ARMS[0],
            archive=archive_before,
            progress=progress,
        )
        strict = _acquire(
            oracle,
            manifest_index=manifest_index,
            arm=ARMS[1],
            archive=(),
            progress=progress,
        )
        prior_episodes, prior_final_model = _run_arm_episodes(
            oracle,
            manifest_index=manifest_index,
            acquisition=prior,
            archive=archive_before,
            progress=progress,
        )
        strict_episodes, strict_final_model = _run_arm_episodes(
            oracle,
            manifest_index=manifest_index,
            acquisition=strict,
            archive=(),
            progress=progress,
        )
        episodes = {ARMS[0]: prior_episodes, ARMS[1]: strict_episodes}
        ood_rejected = False
        try:
            prior.model.predict_support(
                (0,) * (prior.model.state_width + 1),
                (0,) * prior.model.action_width,
            )
        except Exception as error:  # noqa: BLE001 - registered negative control
            ood_rejected = type(error).__name__ == "OpenWorldCompiledModelV181Error"
        distribution = {
            "manifest_index": manifest_index,
            "manifest_commitment": oracle.manifest_commitment,
            "opaque_schema": {
                "state_width": oracle.state_width,
                "action_width": oracle.action_width,
                "horizon": oracle.horizon,
                "moduli": list(oracle.moduli),
            },
            "prior_archive_size_before_distribution": len(archive_before),
            "acquisitions": {
                ARMS[0]: prior.to_document(),
                ARMS[1]: strict.to_document(),
            },
            "episodes": episodes,
            "final_adaptive_model_ids": {
                ARMS[0]: prior_final_model.compiled_model_id,
                ARMS[1]: strict_final_model.compiled_model_id,
            },
            "strict_incompatible_schema_ood_control": {
                "incompatible_state_width": prior.model.state_width + 1,
                "prior_archive_passed": False,
                "target_oracle_query_count": 0,
                "rejected_before_outcome_access": ood_rejected,
            },
            "partial_dynamics_observed_both_arms": all(
                any(not row.exact_on_source for row in acquisition.model.coordinates)
                for acquisition in (prior, strict)
            ),
        }
        distributions.append(distribution)
        progress.append(
            stage="DISTRIBUTION_COMPLETE",
            manifest_index=manifest_index,
            arm=None,
            block_index=None,
            event_document={
                "episode_count": sum(len(episodes[arm]) for arm in ARMS),
                "prior_final_model_id": prior_final_model.compiled_model_id,
                "strict_final_model_id": strict_final_model.compiled_model_id,
            },
            row_ids=tuple(
                episode["episode_id"]
                for arm in ARMS
                for episode in episodes[arm]
            ),
        )
        reusable_archive = tuple(
            sorted(
                set(
                    (
                        *reusable_archive,
                        *prior_final_model.reusable_subprogram_archive(),
                    )
                ),
                key=repr,
            )
        )
    axes = (
        "OFFLINE_SOURCE_LABELS",
        "TARGET_GROUND_LABELS",
        "EXECUTION_STEPS",
        "PROGRAM_ENUMERATION_EVENTS",
        "PLANNING_EVENTS",
        "CERTIFICATE_EVENTS",
        "MODEL_RECOMPILATIONS",
    )
    work_vectors = {
        arm: {axis: _sum_axis(distributions, arm, axis) for axis in axes}
        for arm in ARMS
    }
    for arm in ARMS:
        work_vectors[arm]["OUTPUT_BYTES"] = 0
    per_distribution = []
    for distribution in distributions:
        labels = {
            arm: distribution["acquisitions"][arm]["source_label_count"]
            + sum(
                episode["target_ground_label_count"]
                for episode in distribution["episodes"][arm]
            )
            for arm in ARMS
        }
        per_distribution.append(
            {
                "manifest_index": distribution["manifest_index"],
                "prior_total_labels": labels[ARMS[0]],
                "strict_total_labels": labels[ARMS[1]],
                "prior_labels_avoided": labels[ARMS[1]] - labels[ARMS[0]],
            }
        )
    all_episodes = [
        episode
        for distribution in distributions
        for arm in ARMS
        for episode in distribution["episodes"][arm]
    ]
    gates = {
        "all_six_acquisitions_stopped": all(
            distribution["acquisitions"][arm]["stopped"]
            for distribution in distributions
            for arm in ARMS
        ),
        "all_72_episodes_terminalized": len(all_episodes) == 72
        and all(row["terminal_reached"] for row in all_episodes),
        "all_local_ground_distinctions_follow_certificate_failure": all(
            row["every_local_ground_distinction_has_certificate_failure"]
            for row in all_episodes
        ),
        "all_recompiles_follow_actual_model_mismatch": all(
            row["every_recompile_has_post_execution_model_mismatch"]
            for row in all_episodes
        ),
        "all_certified_actions_have_strict_terminal_rank_decrease": all(
            row["every_certified_action_has_strict_rank_decrease"]
            for row in all_episodes
        ),
        "all_certificates_use_persistent_model_bound_rank_cache": all(
            row["every_certificate_uses_persistent_model_bound_rank_cache"]
            for row in all_episodes
        ),
        "persistent_rank_cache_retained_across_iid_occurrences": any(
            row["planner_cache_entries_before_episode"] > 0
            for row in all_episodes
        ),
        "partial_dynamics_observed_in_all_distributions": all(
            row["partial_dynamics_observed_both_arms"] for row in distributions
        ),
        "strict_ood_rejected_all_distributions": all(
            row["strict_incompatible_schema_ood_control"][
                "rejected_before_outcome_access"
            ]
            for row in distributions
        ),
        "same_synthesizer_stop_adaptation_and_rank_planner_both_arms": True,
        "planner_consumed_compiled_models_not_raw_rows": all(
            not row["planner_received_raw_source_rows"] for row in all_episodes
        ),
    }
    prior_labels = sum(
        work_vectors[ARMS[0]][axis]
        for axis in ("OFFLINE_SOURCE_LABELS", "TARGET_GROUND_LABELS")
    )
    strict_labels = sum(
        work_vectors[ARMS[1]][axis]
        for axis in ("OFFLINE_SOURCE_LABELS", "TARGET_GROUND_LABELS")
    )
    return {
        "schema": "acfqp.open_world_campaign.v181r6",
        "execution_preregistration_id": execution_preregistration_id,
        "protocol_successor_id": protocol.EXPECTED_SUCCESSOR_ID,
        "manifest_reveal_id": reveals.EXPECTED_REVEAL_ID,
        "preserved_v181r4_campaign_id": protocol.PRESERVED_V181R4_CAMPAIGN_ID,
        "preserved_v181r4_verification_id": protocol.PRESERVED_V181R4_VERIFICATION_ID,
        "preserved_v181r5_failure_id": protocol.PRESERVED_V181R5_FAILURE_ID,
        "v181r5_pre_execution_oracle_access_reclassified_as_success": False,
        "distribution_results": distributions,
        "work_vectors": work_vectors,
        "sample_tax_comparison": {
            "prior_total_labels": prior_labels,
            "strict_total_labels": strict_labels,
            "prior_labels_avoided": strict_labels - prior_labels,
            "per_distribution": per_distribution,
            "bounded_three_distribution_sample_efficiency_observed": all(
                row["prior_labels_avoided"] >= 0 for row in per_distribution
            )
            and any(row["prior_labels_avoided"] > 0 for row in per_distribution),
        },
        "registered_gates": gates,
        "registered_gate_passed": all(gates.values()),
        "durable_progress_checkpoint_ids": list(progress.checkpoint_ids),
        "last_durable_progress_checkpoint_id": progress.last_checkpoint_id,
        "covered_recompilation_skip_count": sum(
            distribution["acquisitions"][arm]["covered_recompilation_skip_count"]
            + sum(
                episode["covered_recompilation_skip_count"]
                for episode in distribution["episodes"][arm]
            )
            for distribution in distributions
            for arm in ARMS
        ),
        "weight_agnostic_total_work_dominance_observed": False,
        "cyclic_residual_resource_failure_corrected": True,
        "predecessor_per_step_recompile_path_removed": True,
        "rank_decreasing_planner_used": True,
        "persistent_model_bound_rank_cache_used": True,
        "archive_mdl_discount_used": False,
        "same_confidence_formula_both_arms": True,
        "predecessor_reset_horizon_procrastination_removed": True,
        "manifest_programs_passed_to_synthesizer_or_planner": False,
        "finite_candidate_program_catalog_used": False,
        "named_target_family_used": False,
        "open_ended_world_model_invention_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "broad_iid_sample_efficiency_claimed": False,
        "total_work_dominance_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }


def _fixed_point(payload: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    candidate = dict(payload)
    for _ in range(20):
        without_id = dict(candidate)
        without_id.pop("campaign_id", None)
        candidate = {
            **without_id,
            "campaign_id": domains.extension_content_id_v181r6(
                domains.CONSTRUCTION_K7_CAMPAIGN_V181R6_DOMAIN,
                without_id,
            ),
        }
        raw = canonical_json_bytes(candidate)
        if all(
            candidate["work_vectors"][arm]["OUTPUT_BYTES"] == len(raw)
            for arm in ARMS
        ):
            break
        for arm in ARMS:
            candidate["work_vectors"][arm]["OUTPUT_BYTES"] = len(raw)
    else:
        _fail("campaign output fixed point did not converge")
    prior = candidate["work_vectors"][ARMS[0]]
    strict = candidate["work_vectors"][ARMS[1]]
    candidate["weight_agnostic_total_work_dominance_observed"] = all(
        prior[axis] <= strict[axis] for axis in prior
    ) and any(prior[axis] < strict[axis] for axis in prior)
    without_id = dict(candidate)
    without_id.pop("campaign_id", None)
    candidate["campaign_id"] = domains.extension_content_id_v181r6(
        domains.CONSTRUCTION_K7_CAMPAIGN_V181R6_DOMAIN,
        without_id,
    )
    raw = canonical_json_bytes(candidate)
    if any(candidate["work_vectors"][arm]["OUTPUT_BYTES"] != len(raw) for arm in ARMS):
        for arm in ARMS:
            candidate["work_vectors"][arm]["OUTPUT_BYTES"] = len(raw)
        without_id = dict(candidate)
        without_id.pop("campaign_id", None)
        candidate["campaign_id"] = domains.extension_content_id_v181r6(
            domains.CONSTRUCTION_K7_CAMPAIGN_V181R6_DOMAIN,
            without_id,
        )
        raw = canonical_json_bytes(candidate)
    if any(candidate["work_vectors"][arm]["OUTPUT_BYTES"] != len(raw) for arm in ARMS):
        _fail("final campaign output fixed point changed")
    return candidate, raw


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldCampaignV181R6:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    checkpoint_ids: tuple[str, ...]

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def run_open_world_campaign_v181r6(
    *,
    execution_preregistration_id: str,
    progress_directory: Path,
) -> OpenWorldCampaignV181R6:
    progress = DurableProgressV181R6(
        progress_directory,
        execution_preregistration_id,
    )
    document, raw = _fixed_point(
        _campaign_payload(
            execution_preregistration_id=execution_preregistration_id,
            progress=progress,
        )
    )
    return OpenWorldCampaignV181R6(
        _ISSUER,
        raw,
        document["campaign_id"],
        progress.checkpoint_ids,
    )


__all__ = (
    "ARMS",
    "DurableProgressV181R6",
    "OpenWorldCampaignV181R6",
    "OpenWorldCampaignV181R6Error",
    "run_open_world_campaign_v181r6",
)
