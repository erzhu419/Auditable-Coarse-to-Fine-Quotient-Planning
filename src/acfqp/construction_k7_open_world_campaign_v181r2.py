"""V181r2 matched campaign with durable manifest/arm/block progress.

The producer remains blind to revealed program syntax: it sees opaque widths,
legal actions, raw transitions, and the compiled V181r2 model.  Every queried
acquisition block is durably indexed before the next block; a compile failure
therefore identifies the exact manifest, arm, block, and retained raw rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v181r2 as domains
from acfqp import construction_k7_open_world_manifest_reveals_v181r2 as reveals
from acfqp import construction_k7_open_world_protocol_successor_v181r2 as protocol
from acfqp.open_world_compiled_model_v181r2 import (
    CompiledWorldModelV181R2,
    certify_receding_action_v181r2,
    compile_world_model_v181r2,
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
MAXIMUM_LABEL_COUNT = 512
STABLE_CONFIRMATION_BLOCKS = 2
MAXIMUM_ENUMERATION_EVENTS_PER_EXPRESSION = 2_000_000
MAXIMUM_TARGET_GROUND_LABELS = 32
MAXIMUM_DECISIONS = 64


class OpenWorldCampaignV181R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldCampaignV181R2Error(message)


def _oracle(manifest_index: int) -> OpaqueTransitionOracleV181:
    document = reveals.MANIFEST_DOCUMENTS_V181R2[manifest_index]
    return reveal_opaque_transition_oracle_v181(
        manifest_bytes=canonical_json_bytes(document),
        expected_commitment=protocol.MANIFEST_COMMITMENTS_V181R2[manifest_index],
    )


def _acquisition_input(
    oracle: OpaqueTransitionOracleV181, *, unique_index: int
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    digest = hashlib.sha256(
        b"acfqp:v181r2:witness-blind-acquisition\x00"
        + oracle.manifest_commitment.encode()
        + unique_index.to_bytes(8, "big")
    ).digest()
    state = tuple(
        digest[index] % modulus for index, modulus in enumerate(oracle.moduli)
    )
    action = tuple(
        digest[16 + index] % 3 for index in range(oracle.action_width)
    )
    return state, action


def _projection(model: CompiledWorldModelV181R2) -> dict[str, Any]:
    document = model.to_document()
    return {
        "state_width": document["state_width"],
        "action_width": document["action_width"],
        "coordinates": [
            {
                key: row[key]
                for key in (
                    "coordinate_index",
                    "expression",
                    "exact_on_source",
                    "residual_values",
                    "residual_modulus",
                    "dependencies",
                    "token_length",
                )
            }
            for row in document["coordinates"]
        ],
        "terminal_expression": document["terminal_expression"],
        "terminal_dependencies": document["terminal_dependencies"],
        "factor_boundaries": document["factor_boundaries"],
    }


def _covers(
    model: CompiledWorldModelV181R2, row: RawTransitionObservationV181
) -> bool:
    return (
        row.successor in model.predict_support(row.state, row.action)
        and model.terminal(row.successor) is row.terminal
    )


class DurableProgressV181R2:
    """Append-only exact checkpoints; existing exact bytes finish forward."""

    def __init__(self, directory: Path, execution_preregistration_id: str) -> None:
        if (
            not isinstance(directory, Path)
            or not directory.is_dir()
            or type(execution_preregistration_id) is not str
            or len(execution_preregistration_id) != 64
        ):
            _fail("durable progress binding changed")
        existing = sorted(directory.glob("checkpoint-*.json"))
        if existing:
            _fail("V181r2 scientific progress directory must begin fresh")
        self._directory = directory
        self._execution_preregistration_id = execution_preregistration_id
        self._sequence = 0
        self._previous_id: str | None = None
        self._checkpoint_ids: list[str] = []

    @property
    def checkpoint_ids(self) -> tuple[str, ...]:
        return tuple(self._checkpoint_ids)

    @property
    def last_checkpoint_id(self) -> str | None:
        return self._previous_id

    def append(
        self,
        *,
        stage: str,
        manifest_index: int,
        arm: str | None,
        block_index: int | None,
        observations: Sequence[RawTransitionObservationV181] = (),
        compiled_model: CompiledWorldModelV181R2 | None = None,
        failure: BaseException | None = None,
        row_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        if (
            type(stage) is not str
            or type(manifest_index) is not int
            or not 0 <= manifest_index < 3
            or arm not in {*ARMS, None}
            or (block_index is not None and type(block_index) is not int)
            or any(type(row) is not RawTransitionObservationV181 for row in observations)
            or any(type(value) is not str or len(value) != 64 for value in row_ids)
        ):
            _fail("durable progress checkpoint input changed")
        payload = {
            "schema": "acfqp.open_world_progress_checkpoint.v181r2",
            "execution_preregistration_id": self._execution_preregistration_id,
            "sequence": self._sequence,
            "previous_checkpoint_id": self._previous_id,
            "stage": stage,
            "manifest_index": manifest_index,
            "arm": arm,
            "block_index": block_index,
            "source_label_count": len(observations),
            "source_observations": [row.to_document() for row in observations],
            "compiled_model": (
                compiled_model.to_document() if compiled_model is not None else None
            ),
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
            "progress_checkpoint_id": domains.extension_content_id_v181r2(
                domains.CONSTRUCTION_K7_PROGRESS_CHECKPOINT_V181R2_DOMAIN,
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
                self._directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
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
        self._sequence += 1
        return document


@dataclass(frozen=True, slots=True)
class _AcquisitionV181R2:
    arm: str
    observations: tuple[RawTransitionObservationV181, ...]
    model: CompiledWorldModelV181R2
    block_history: tuple[dict[str, Any], ...]
    stopped: bool
    stable_confirmation_count: int
    recompilation_count: int
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
            "recompilation_count": self.recompilation_count,
            "cumulative_enumeration_events": self.cumulative_enumeration_events,
            "input_archive_size": self.input_archive_size,
            "same_synthesizer_and_stop_rule": True,
            "manifest_program_read_by_acquisition": False,
        }


def _acquire(
    oracle: OpaqueTransitionOracleV181,
    *,
    manifest_index: int,
    arm: str,
    archive: Iterable[ExpressionV181],
    progress: DurableProgressV181R2,
) -> _AcquisitionV181R2:
    frozen_archive = tuple(archive)
    observations: list[RawTransitionObservationV181] = []
    history: list[dict[str, Any]] = []
    previous_model: CompiledWorldModelV181R2 | None = None
    previous_projection: dict[str, Any] | None = None
    stable = 0
    recompilations = 0
    cumulative_events = 0
    stopped = False
    acquisition_occurrence = 20_000 + manifest_index
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
        confirmation_zero_error = previous_model is not None and all(
            _covers(previous_model, row) for row in block
        )
        observations.extend(block)
        if len(observations) < MINIMUM_LABEL_COUNT:
            history.append(
                {
                    "block_index": block_index,
                    "cumulative_source_label_count": len(observations),
                    "compiled": False,
                    "confirmation_zero_error": False,
                    "projection_stable": False,
                    "stable_confirmation_count": stable,
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
        try:
            model = compile_world_model_v181r2(
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
        recompilations += 1
        cumulative_events += model.total_enumeration_events
        projection = _projection(model)
        projection_stable = previous_projection is not None and projection == previous_projection
        stable = stable + 1 if confirmation_zero_error and projection_stable else 0
        history.append(
            {
                "block_index": block_index,
                "cumulative_source_label_count": len(observations),
                "compiled": True,
                "compiled_model_id": model.compiled_model_id,
                "confirmation_zero_error": confirmation_zero_error,
                "projection_stable": projection_stable,
                "stable_confirmation_count": stable,
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
        previous_model = model
        previous_projection = projection
        if stable >= STABLE_CONFIRMATION_BLOCKS:
            stopped = True
            break
    if previous_model is None:
        _fail("acquisition ended without one compiled model")
    result = _AcquisitionV181R2(
        arm,
        tuple(observations),
        previous_model,
        tuple(history),
        stopped,
        stable,
        recompilations,
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
        b"acfqp:v181r2:certificate-failure-fallback\x00"
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
    model: CompiledWorldModelV181R2, row: RawTransitionObservationV181
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


def _episode(
    oracle: OpaqueTransitionOracleV181,
    *,
    manifest_index: int,
    occurrence_index: int,
    acquisition: _AcquisitionV181R2,
    archive: Iterable[ExpressionV181],
) -> dict[str, Any]:
    model = acquisition.model
    training_rows = list(acquisition.observations)
    frozen_archive = tuple(archive)
    state = oracle.initial_state(occurrence_index)
    initial_state = state
    steps: list[dict[str, Any]] = []
    target_ground_labels = 0
    execution_steps = 0
    planning_events = 0
    certificate_events = 0
    recompile_events = 0
    recompile_enumeration_events = 0
    terminal_reached = model.terminal(state)
    for decision_index in range(MAXIMUM_DECISIONS):
        if terminal_reached:
            break
        certificate = certify_receding_action_v181r2(
            model,
            state=state,
            legal_actions=oracle.legal_actions(),
            horizon=oracle.horizon,
        )
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
            query_index=2_000_000 + occurrence_index * 100 + decision_index,
            state=state,
            action=action,
        )
        execution_steps += 1
        support_match = row.successor in model.predict_support(state, action)
        terminal_match = model.terminal(row.successor) is row.terminal
        post_execution_failure = not support_match or not terminal_match
        local_ground = pre_execution_failure or post_execution_failure
        dependencies = _changed_dependencies(model, row) if post_execution_failure else []
        recompiled_model_id = None
        if local_ground:
            target_ground_labels += 1
            training_rows.append(row)
            model = compile_world_model_v181r2(
                tuple(training_rows),
                maximum_enumeration_events_per_expression=(
                    MAXIMUM_ENUMERATION_EVENTS_PER_EXPRESSION
                ),
                archive=frozen_archive,
            )
            recompile_events += 1
            recompile_enumeration_events += model.total_enumeration_events
            recompiled_model_id = model.compiled_model_id
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
                "certificate_failure_before_local_ground": local_ground,
                "certificate_failure_kind": (
                    "PRE_EXECUTION_UNCERTIFIED"
                    if pre_execution_failure
                    else "POST_EXECUTION_MODEL_MISMATCH"
                    if post_execution_failure
                    else None
                ),
                "minimal_invalidated_dependencies": dependencies,
                "recompiled_model_id": recompiled_model_id,
            }
        )
        state = row.successor
        terminal_reached = row.terminal
    payload = {
        "schema": "acfqp.open_world_episode.v181r2",
        "manifest_index": manifest_index,
        "manifest_commitment": oracle.manifest_commitment,
        "arm": acquisition.arm,
        "occurrence_index": occurrence_index,
        "initial_state": list(initial_state),
        "horizon": oracle.horizon,
        "steps": steps,
        "terminal_reached": terminal_reached,
        "final_state": list(state),
        "target_ground_label_count": target_ground_labels,
        "execution_step_count": execution_steps,
        "planning_compute_events": planning_events,
        "certificate_event_count": certificate_events,
        "model_recompilation_count": recompile_events,
        "recompilation_enumeration_events": recompile_enumeration_events,
        "planner_received_raw_source_rows": False,
        "every_local_ground_distinction_has_certificate_failure": all(
            (not step["certificate_failure_before_local_ground"])
            or step["certificate_failure_kind"] is not None
            for step in steps
        ),
    }
    payload["episode_id"] = hashlib.sha256(
        b"acfqp:v181r2:episode\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    return payload


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


def _campaign_payload(
    *,
    execution_preregistration_id: str,
    progress: DurableProgressV181R2,
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
        episodes = {
            ARMS[0]: [
                _episode(
                    oracle,
                    manifest_index=manifest_index,
                    occurrence_index=index,
                    acquisition=prior,
                    archive=archive_before,
                )
                for index in range(12)
            ],
            ARMS[1]: [
                _episode(
                    oracle,
                    manifest_index=manifest_index,
                    occurrence_index=index,
                    acquisition=strict,
                    archive=(),
                )
                for index in range(12)
            ],
        }
        ood_rejected = False
        try:
            prior.model.predict_support(
                (0,) * (prior.model.state_width + 1),
                (0,) * prior.model.action_width,
            )
        except Exception as error:  # noqa: BLE001 - negative control
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
            row_ids=tuple(
                episode["episode_id"]
                for arm in ARMS
                for episode in episodes[arm]
            ),
        )
        reusable_archive = tuple(
            sorted(
                set((*reusable_archive, *prior.model.reusable_subprogram_archive())),
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
        "partial_dynamics_observed_in_all_distributions": all(
            row["partial_dynamics_observed_both_arms"] for row in distributions
        ),
        "strict_ood_rejected_all_distributions": all(
            row["strict_incompatible_schema_ood_control"]["rejected_before_outcome_access"]
            for row in distributions
        ),
        "same_synthesizer_and_stop_rule_both_arms": True,
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
        "schema": "acfqp.open_world_campaign.v181r2",
        "execution_preregistration_id": execution_preregistration_id,
        "protocol_successor_id": protocol.EXPECTED_SUCCESSOR_ID,
        "manifest_reveal_id": reveals.EXPECTED_REVEAL_ID,
        "preserved_v181r1_failure_id": protocol.PRESERVED_V181R1_FAILURE_ID,
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
        "weight_agnostic_total_work_dominance_observed": False,
        "cyclic_residual_resource_failure_corrected": True,
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
            "campaign_id": domains.extension_content_id_v181r2(
                domains.CONSTRUCTION_K7_CAMPAIGN_V181R2_DOMAIN,
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
    candidate["campaign_id"] = domains.extension_content_id_v181r2(
        domains.CONSTRUCTION_K7_CAMPAIGN_V181R2_DOMAIN,
        without_id,
    )
    raw = canonical_json_bytes(candidate)
    if any(candidate["work_vectors"][arm]["OUTPUT_BYTES"] != len(raw) for arm in ARMS):
        for arm in ARMS:
            candidate["work_vectors"][arm]["OUTPUT_BYTES"] = len(raw)
        without_id = dict(candidate)
        without_id.pop("campaign_id", None)
        candidate["campaign_id"] = domains.extension_content_id_v181r2(
            domains.CONSTRUCTION_K7_CAMPAIGN_V181R2_DOMAIN,
            without_id,
        )
        raw = canonical_json_bytes(candidate)
    if any(candidate["work_vectors"][arm]["OUTPUT_BYTES"] != len(raw) for arm in ARMS):
        _fail("final campaign output fixed point changed")
    return candidate, raw


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class OpenWorldCampaignV181R2:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    campaign_id: str
    checkpoint_ids: tuple[str, ...]

    def to_document(self) -> dict[str, Any]:
        return loads_canonical_json(self.canonical_bytes)


def run_open_world_campaign_v181r2(
    *,
    execution_preregistration_id: str,
    progress_directory: Path,
) -> OpenWorldCampaignV181R2:
    progress = DurableProgressV181R2(
        progress_directory, execution_preregistration_id
    )
    document, raw = _fixed_point(
        _campaign_payload(
            execution_preregistration_id=execution_preregistration_id,
            progress=progress,
        )
    )
    return OpenWorldCampaignV181R2(
        _ISSUER,
        raw,
        document["campaign_id"],
        progress.checkpoint_ids,
    )


__all__ = (
    "ARMS",
    "DurableProgressV181R2",
    "OpenWorldCampaignV181R2",
    "OpenWorldCampaignV181R2Error",
    "run_open_world_campaign_v181r2",
)
