"""Producer-free deterministic replay of the V182r2 total-machine campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v182r2 as domains
from acfqp import construction_k7_open_world_total_machine_manifest_reveal_v182r2 as reveal
from acfqp import construction_k7_open_world_total_machine_protocol_v182r2 as protocol
from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_machine_oracle_v182 import (
    OpaqueMachineOracleV182,
    reveal_opaque_machine_oracle_v182,
)
from acfqp.open_world_total_machine_model_v182r2 import (
    TotalCompiledMachineWorldModelV182R2,
    compile_total_machine_world_model_v182r2,
)
from acfqp.open_world_total_machine_planner_v182r2 import (
    TotalMachinePlannerSessionV182R2,
)
from acfqp.open_world_universal_machine_v182 import ProgramV182
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


class OpenWorldTotalMachineIndependentVerifierV182R2Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldTotalMachineIndependentVerifierV182R2Error(message)


def _oracle(index: int) -> OpaqueMachineOracleV182:
    return reveal_opaque_machine_oracle_v182(
        manifest_bytes=canonical_json_bytes(reveal.MANIFEST_DOCUMENTS_V182R2[index]),
        expected_commitment=protocol.MANIFEST_COMMITMENTS_V182R2[index],
    )


def _compile(
    oracle: OpaqueMachineOracleV182,
    rows: Sequence[RawMachineTransitionV182],
    archive: Iterable[ProgramV182] = (),
) -> TotalCompiledMachineWorldModelV182R2:
    return compile_total_machine_world_model_v182r2(
        rows,
        state_moduli=oracle.initial_moduli,
        legal_actions=oracle.legal_actions(),
        maximum_enumeration_events_per_scalar=(
            protocol.MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR
        ),
        maximum_instruction_count=protocol.MAXIMUM_INSTRUCTION_COUNT,
        maximum_execution_steps=protocol.MAXIMUM_EXECUTION_STEPS,
        register_count=protocol.REGISTER_COUNT,
        maximum_residual_support=protocol.MAXIMUM_RESIDUAL_SUPPORT,
        archive=archive,
    )


def _synthesis_events(model: TotalCompiledMachineWorldModelV182R2) -> int:
    return sum(
        row.synthesis.synthesis.enumeration_events for row in model.coordinates
    ) + model.terminal_synthesis.synthesis.enumeration_events


def _totality_inputs(model: TotalCompiledMachineWorldModelV182R2) -> int:
    return sum(
        row.synthesis.totality.input_count for row in model.coordinates
    ) + model.terminal_synthesis.totality.input_count


def _archive_reference_count(model: TotalCompiledMachineWorldModelV182R2) -> int:
    return sum(
        int(row.synthesis.synthesis.archive_reference_used)
        for row in model.coordinates
    ) + int(model.terminal_synthesis.synthesis.archive_reference_used)


def _acquisition_input(
    oracle: OpaqueMachineOracleV182, unique_index: int
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    digest = hashlib.sha256(
        b"acfqp:v182r2:witness-blind-acquisition\x00"
        + oracle.manifest_commitment.encode()
        + unique_index.to_bytes(8, "big")
    ).digest()
    return (
        tuple(
            digest[index] % modulus
            for index, modulus in enumerate(oracle.initial_moduli)
        ),
        tuple(
            digest[16 + index] % oracle.action_cardinality
            for index in range(oracle.action_width)
        ),
    )


def _query_block(
    oracle: OpaqueMachineOracleV182,
    *,
    occurrence_index: int,
    block_index: int,
) -> tuple[RawMachineTransitionV182, ...]:
    rows = []
    unique_per_block = (
        protocol.ACQUISITION_BLOCK_SIZE // protocol.ACQUISITION_REPEAT_COUNT
    )
    for local_unique in range(unique_per_block):
        unique_index = block_index * unique_per_block + local_unique
        state, action = _acquisition_input(oracle, unique_index)
        for repeat in range(protocol.ACQUISITION_REPEAT_COUNT):
            query_index = (
                block_index * protocol.ACQUISITION_BLOCK_SIZE
                + local_unique * protocol.ACQUISITION_REPEAT_COUNT
                + repeat
            )
            rows.append(
                oracle.query(
                    occurrence_index=occurrence_index,
                    query_index=query_index,
                    state=state,
                    action=action,
                )
            )
    return tuple(rows)


class _ProgressReplay:
    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id
        self.previous: str | None = None
        self.documents: list[dict[str, Any]] = []

    def append(self, stage: str, payload: dict[str, Any]) -> None:
        body = {
            "schema": "acfqp.open_world_total_machine_progress.v182r2",
            "execution_preregistration_id": self.execution_id,
            "sequence": len(self.documents),
            "previous_checkpoint_id": self.previous,
            "stage": stage,
            "payload": payload,
            "outcome_progress_not_official_claim": True,
            "official_execution_allowed": False,
        }
        document = {
            **body,
            "progress_checkpoint_id": domains.extension_content_id_v182r2(
                domains.CONSTRUCTION_K7_PROGRESS_CHECKPOINT_V182R2_DOMAIN,
                body,
            ),
        }
        self.documents.append(document)
        self.previous = document["progress_checkpoint_id"]

    @property
    def ids(self) -> list[str]:
        return [row["progress_checkpoint_id"] for row in self.documents]


def _acquire(
    oracle: OpaqueMachineOracleV182,
    *,
    arm: str,
    archive: Sequence[ProgramV182],
    progress: _ProgressReplay,
) -> tuple[
    dict[str, Any],
    tuple[RawMachineTransitionV182, ...],
    TotalCompiledMachineWorldModelV182R2,
]:
    observations: list[RawMachineTransitionV182] = []
    history = []
    model: TotalCompiledMachineWorldModelV182R2 | None = None
    stable = 0
    credit = 0
    cumulative_events = 0
    cumulative_totality = 0
    archive_count = 0
    for block_index in range(
        protocol.MAXIMUM_TARGET_LABELS // protocol.ACQUISITION_BLOCK_SIZE
    ):
        block = _query_block(
            oracle,
            occurrence_index=182_300,
            block_index=block_index,
        )
        covered = model is not None and all(model.covers(row) for row in block)
        observations.extend(block)
        compiled = False
        events = 0
        totality_inputs = 0
        if len(observations) >= protocol.MINIMUM_TARGET_LABELS:
            if covered:
                stable += 1
            else:
                model = _compile(oracle, observations, archive)
                compiled = True
                stable = 0
                events = _synthesis_events(model)
                totality_inputs = _totality_inputs(model)
                cumulative_events += events
                cumulative_totality += totality_inputs
                archive_count = _archive_reference_count(model)
                credit = int(
                    arm == "REVALIDATED_TOTAL_MACHINE_PRIOR"
                    and archive_count > 0
                    and all(model.covers(row) for row in observations)
                ) * protocol.REVALIDATED_PRIOR_CONFIRMATION_CREDIT
        history_row = {
            "block_index": block_index,
            "cumulative_source_label_count": len(observations),
            "compiled": compiled,
            "model_reused_without_recompile": covered,
            "confirmation_zero_error": covered,
            "stable_confirmation_count": stable,
            "revalidated_prior_credit": credit,
            "effective_confirmation_count": stable + credit,
            "enumeration_events": events,
            "totality_check_inputs": totality_inputs,
            "compiled_model_id": model.compiled_model_id if model else None,
        }
        history.append(history_row)
        progress.append("TARGET_ACQUISITION_BLOCK", {"arm": arm, **history_row})
        if model is not None and stable + credit >= protocol.STABLE_CONFIRMATION_BLOCKS:
            document = {
                "arm": arm,
                "source_label_count": len(observations),
                "source_observations": [row.to_document() for row in observations],
                "compiled_model": model.to_document(),
                "block_history": history,
                "cumulative_synthesis_events": cumulative_events,
                "cumulative_totality_check_inputs": cumulative_totality,
                "archive_reference_count": archive_count,
                "revalidated_prior_credit": credit,
                "stopped": True,
                "same_synthesizer_and_stop_rule": True,
                "archive_mdl_discount_used": False,
                "witness_blind_acquisition": True,
                "full_finite_carrier_totality_required": True,
            }
            return document, tuple(observations), model
    _fail("V182r2 replayed acquisition did not stop")


def _episodes(
    oracle: OpaqueMachineOracleV182,
    *,
    arm: str,
    acquisition_document: dict[str, Any],
    acquisition_rows: Sequence[RawMachineTransitionV182],
    acquisition_model: TotalCompiledMachineWorldModelV182R2,
    archive: Sequence[ProgramV182],
    progress: _ProgressReplay,
) -> dict[str, Any]:
    model_rows = list(acquisition_rows)
    model = acquisition_model
    episodes = []
    local_labels = 0
    execution_steps = 0
    planning_events = 0
    certificate_count = 0
    recovery_events = 0
    recovery_totality = 0
    for offset in range(protocol.IID_OCCURRENCES_PER_ARM):
        occurrence = 182_400 + offset
        state = oracle.initial_state(occurrence)
        initial_state = state
        session = TotalMachinePlannerSessionV182R2(model, horizon=oracle.horizon)
        steps = []
        for decision in range(protocol.MAXIMUM_DECISIONS_PER_OCCURRENCE):
            certificate = session.certify(state)
            certificate_count += 1
            planning_events += certificate.planning_compute_events
            if not certificate.certified or certificate.selected_action is None:
                _fail("V182r2 replayed plan lacks a certificate")
            predicted = model.predict_support(state, certificate.selected_action)
            observed = oracle.query(
                occurrence_index=occurrence,
                query_index=decision,
                state=state,
                action=certificate.selected_action,
            )
            execution_steps += 1
            matched = observed.successor in predicted and (
                model.terminal(observed.successor) is observed.terminal
            )
            local = not matched
            failure = None if matched else "FAILED_MISSING_SUPPORT_OR_TERMINAL"
            if local:
                local_labels += 1
                if local_labels > protocol.MAXIMUM_TARGET_GROUND_LABELS_PER_ARM:
                    _fail("V182r2 replay crossed its local-ground label cap")
                model_rows.append(observed)
                model = _compile(oracle, model_rows, archive)
                recovery_events += _synthesis_events(model)
                recovery_totality += _totality_inputs(model)
                session = TotalMachinePlannerSessionV182R2(
                    model, horizon=oracle.horizon
                )
                if not model.covers(observed):
                    _fail("V182r2 replayed local distinction did not repair coverage")
            steps.append(
                {
                    "decision_index": decision,
                    "state": list(state),
                    "certificate": certificate.to_document(),
                    "selected_action": list(certificate.selected_action),
                    "predicted_support": [list(row) for row in predicted],
                    "observation": observed.to_document(),
                    "certificate_support_matched": matched,
                    "certificate_failure": failure,
                    "local_ground_distinction_acquired": local,
                    "local_ground_distinction_requires_preceding_failure": True,
                    "compiled_model_id_after_step": model.compiled_model_id,
                }
            )
            state = observed.successor
            if observed.terminal:
                break
        if not oracle.terminal(state):
            _fail("V182r2 replayed episode crossed its decision cap")
        episode = {
            "occurrence_index": occurrence,
            "initial_state": list(initial_state),
            "steps": steps,
            "execution_step_count": len(steps),
            "terminal_state": list(state),
            "terminal": True,
            "local_ground_label_count": sum(
                int(row["local_ground_distinction_acquired"]) for row in steps
            ),
        }
        episodes.append(episode)
        progress.append(
            "TARGET_EPISODE_TERMINAL",
            {
                "arm": arm,
                "occurrence_index": occurrence,
                "execution_step_count": len(steps),
                "local_ground_label_count": episode["local_ground_label_count"],
                "terminal": True,
            },
        )
    return {
        "arm": arm,
        "acquisition": acquisition_document,
        "episodes": episodes,
        "terminal_episode_count": len(episodes),
        "target_acquisition_label_count": len(acquisition_rows),
        "target_local_ground_label_count": local_labels,
        "target_total_label_count": len(acquisition_rows) + local_labels,
        "execution_step_count": execution_steps,
        "planning_compute_events": planning_events,
        "certificate_count": certificate_count,
        "acquisition_synthesis_events": acquisition_document[
            "cumulative_synthesis_events"
        ],
        "acquisition_totality_check_inputs": acquisition_document[
            "cumulative_totality_check_inputs"
        ],
        "recovery_compilation_events": recovery_events,
        "recovery_totality_check_inputs": recovery_totality,
        "planning_consumed_only_totality_checked_compiled_model": True,
        "ground_transition_argument_passed_to_planner": False,
        "all_local_ground_labels_followed_certificate_failure": True,
    }


def _reconstruct(
    execution_id: str,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    source_oracle, target_oracle, ood_oracle = (_oracle(index) for index in range(3))
    if source_oracle.schema_signature() != target_oracle.schema_signature():
        _fail("V182r2 replayed matched schema changed")
    if source_oracle.schema_signature() == ood_oracle.schema_signature():
        _fail("V182r2 replayed OOD schema collapsed")
    progress = _ProgressReplay(execution_id)
    source_rows = []
    for block_index in range(
        protocol.OFFLINE_SOURCE_LABELS // protocol.ACQUISITION_BLOCK_SIZE
    ):
        source_rows.extend(
            _query_block(
                source_oracle,
                occurrence_index=182_250,
                block_index=block_index,
            )
        )
    source_model = _compile(source_oracle, source_rows)
    archive = source_model.reusable_program_archive()
    progress.append(
        "OFFLINE_SOURCE_MODEL_COMPILED",
        {
            "source_label_count": len(source_rows),
            "compiled_model_id": source_model.compiled_model_id,
            "archive_program_count": len(archive),
            "synthesis_events": _synthesis_events(source_model),
            "totality_check_inputs": _totality_inputs(source_model),
        },
    )
    arms = []
    for arm in protocol.ARMS:
        arm_archive = archive if arm == "REVALIDATED_TOTAL_MACHINE_PRIOR" else ()
        acquisition, rows, model = _acquire(
            target_oracle,
            arm=arm,
            archive=arm_archive,
            progress=progress,
        )
        arms.append(
            _episodes(
                target_oracle,
                arm=arm,
                acquisition_document=acquisition,
                acquisition_rows=rows,
                acquisition_model=model,
                archive=arm_archive,
                progress=progress,
            )
        )
    by_arm = {row["arm"]: row for row in arms}
    prior = by_arm["REVALIDATED_TOTAL_MACHINE_PRIOR"]
    no_prior = by_arm["EMPTY_ARCHIVE_NO_PRIOR"]
    protocol_document = (
        protocol.freeze_open_world_total_machine_protocol_v182r2().to_document()
    )
    reveal_document = (
        reveal.freeze_open_world_total_machine_manifest_reveal_v182r2().to_document()
    )
    payload = {
        "schema": "acfqp.open_world_total_machine_campaign.v182r2",
        "execution_preregistration_id": execution_id,
        "protocol_id": protocol_document["protocol_id"],
        "manifest_reveal_id": reveal_document["manifest_reveal_id"],
        "failed_predecessor_failure_id": protocol_document[
            "failed_predecessor_failure_id"
        ],
        "failed_predecessor_preserved": True,
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS_V182R2),
        "source_observations": [row.to_document() for row in source_rows],
        "source_compiled_model": source_model.to_document(),
        "source_label_count": len(source_rows),
        "source_synthesis_events": _synthesis_events(source_model),
        "source_totality_check_inputs": _totality_inputs(source_model),
        "source_archive_program_count": len(archive),
        "ood_no_transfer_control": {
            "source_schema_signature": list(source_oracle.schema_signature()),
            "ood_schema_signature": list(ood_oracle.schema_signature()),
            "prior_transfer_rejected": True,
            "rejected_before_target_query": True,
            "ood_target_query_count": 0,
        },
        "arm_results": arms,
        "prior_target_total_labels": prior["target_total_label_count"],
        "no_prior_target_total_labels": no_prior["target_total_label_count"],
        "target_labels_avoided": (
            no_prior["target_total_label_count"]
            - prior["target_total_label_count"]
        ),
        "all_registered_episodes_terminal": True,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "exact_same_target_observation_stream_until_prior_stop": True,
        "archive_mdl_discount_used": False,
        "all_compiled_programs_total_on_full_registered_finite_carrier": True,
        "finite_carrier_totality_not_unbounded_totality": True,
        "planner_consumed_only_totality_checked_compiled_models": True,
        "all_local_ground_labels_followed_certificate_failure": True,
        "label_axes_separate_from_execution_and_compute": True,
        "progress_checkpoint_ids": progress.ids,
        "progress_checkpoint_count": len(progress.ids),
        "finite_candidate_program_catalog_used": False,
        "named_domain_family_used": False,
        "language_program_length_unbounded": True,
        "occurrence_search_resource_bounded": True,
        "partial_support_probability_authority_present": False,
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "total_work_dominance_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return (
        {
            **payload,
            "campaign_id": domains.extension_content_id_v182r2(
                domains.CONSTRUCTION_K7_CAMPAIGN_V182R2_DOMAIN,
                payload,
            ),
        },
        tuple(progress.documents),
    )


def verify_open_world_total_machine_campaign_independently_v182r2(
    campaign_bytes: bytes,
    progress_root: Path,
    *,
    expected_execution_preregistration_id: str,
) -> dict[str, Any]:
    if type(campaign_bytes) is not bytes or not campaign_bytes:
        _fail("V182r2 campaign bytes are absent")
    retained = loads_canonical_json(campaign_bytes)
    if type(retained) is not dict or canonical_json_bytes(retained) != campaign_bytes:
        _fail("V182r2 campaign is not one canonical object")
    if (
        type(expected_execution_preregistration_id) is not str
        or len(expected_execution_preregistration_id) != 64
        or retained.get("execution_preregistration_id")
        != expected_execution_preregistration_id
    ):
        _fail("V182r2 execution preregistration identity changed")
    expected, progress_documents = _reconstruct(
        expected_execution_preregistration_id
    )
    if retained != expected or canonical_json_bytes(expected) != campaign_bytes:
        _fail("V182r2 producer-free campaign reconstruction changed")
    paths = sorted(progress_root.glob("checkpoint-*.json"))
    if len(paths) != len(progress_documents):
        _fail("V182r2 retained progress denominator changed")
    for path, document in zip(paths, progress_documents, strict=True):
        if path.read_bytes() != canonical_json_bytes(document):
            _fail("V182r2 retained progress bytes changed")
    prior, no_prior = expected["arm_results"]
    payload = {
        "schema": "acfqp.open_world_total_machine_independent_verification.v182r2",
        "campaign_id": expected["campaign_id"],
        "execution_preregistration_id": expected_execution_preregistration_id,
        "protocol_id": expected["protocol_id"],
        "manifest_reveal_id": expected["manifest_reveal_id"],
        "failed_predecessor_failure_id": expected[
            "failed_predecessor_failure_id"
        ],
        "campaign_byte_count": len(campaign_bytes),
        "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "progress_checkpoint_count": len(progress_documents),
        "producer_module_imported": False,
        "exact_campaign_reconstructed_from_committed_manifests": True,
        "all_programs_total_on_full_registered_finite_carrier_verified": True,
        "finite_carrier_totality_not_unbounded_totality": True,
        "all_registered_episodes_terminal": True,
        "prior_target_total_labels": prior["target_total_label_count"],
        "no_prior_target_total_labels": no_prior["target_total_label_count"],
        "target_labels_avoided": expected["target_labels_avoided"],
        "all_local_ground_labels_followed_certificate_failure": True,
        "strict_ood_no_transfer_verified": True,
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "total_work_dominance_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "verification_id": domains.extension_content_id_v182r2(
            domains.CONSTRUCTION_K7_VERIFICATION_V182R2_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "OpenWorldTotalMachineIndependentVerifierV182R2Error",
    "verify_open_world_total_machine_campaign_independently_v182r2",
)
