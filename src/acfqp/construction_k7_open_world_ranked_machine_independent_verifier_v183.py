"""Producer-free reconstruction of the fresh V183 ranked-machine campaign."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v183 as domains
from acfqp import construction_k7_open_world_ranked_machine_manifest_reveal_v183 as reveal
from acfqp import construction_k7_open_world_ranked_machine_protocol_v183 as protocol
from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.open_world_ranked_machine_oracle_v183 import (
    RankedMachineOracleV183,
    reveal_ranked_machine_oracle_v183,
)
from acfqp.open_world_ranked_machine_planner_v183 import RankedMachinePlannerSessionV183
from acfqp.open_world_ranked_machine_v183 import (
    RankedCompiledWorldModelV183,
    compile_ranked_machine_world_model_v183,
)
from acfqp.open_world_universal_machine_v182 import ProgramV182
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


class OpenWorldRankedMachineIndependentVerifierV183Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldRankedMachineIndependentVerifierV183Error(message)


def _oracle(index: int) -> RankedMachineOracleV183:
    return reveal_ranked_machine_oracle_v183(
        manifest_bytes=canonical_json_bytes(reveal.MANIFEST_DOCUMENTS_V183[index]),
        expected_commitment=protocol.MANIFEST_COMMITMENTS_V183[index],
    )


def _compile(
    rows: Sequence[RawMachineTransitionV182],
    archive: Iterable[ProgramV182] = (),
) -> RankedCompiledWorldModelV183:
    return compile_ranked_machine_world_model_v183(
        rows,
        maximum_enumeration_events_per_scalar=protocol.MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR,
        resource_step_cap=protocol.RESOURCE_STEP_CAP,
        maximum_loop_increment_repetitions=protocol.MAXIMUM_LOOP_INCREMENT_REPETITIONS,
        register_count=protocol.REGISTER_COUNT,
        maximum_residual_support=protocol.MAXIMUM_RESIDUAL_SUPPORT,
        archive=archive,
    )


def _synthesis_events(model: RankedCompiledWorldModelV183) -> int:
    return sum(row.enumeration_events for row in model.coordinates) + model.terminal_synthesis.enumeration_events


def _archive_reference_count(model: RankedCompiledWorldModelV183) -> int:
    return sum(int(row.archive_reference_used) for row in model.coordinates) + int(model.terminal_synthesis.archive_reference_used)


def _ranking_proof_count(model: RankedCompiledWorldModelV183) -> int:
    return sum(1 + len(row.termination.loop_proofs) for row in model.coordinates) + 1 + len(model.terminal_synthesis.termination.loop_proofs)


def _acquisition_input(oracle: RankedMachineOracleV183, index: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    digest = hashlib.sha256(
        b"acfqp:v183:witness-blind-acquisition\x00"
        + oracle.manifest_commitment.encode()
        + index.to_bytes(8, "big")
    ).digest()
    state = [digest[0] % 6, 1 + digest[1] % 4]
    state.extend(digest[2 + offset] % 4 for offset in range(oracle.state_width - 2))
    action = oracle.legal_actions[int.from_bytes(digest[16:24], "big") % len(oracle.legal_actions)]
    return tuple(state), action


def _block(
    oracle: RankedMachineOracleV183,
    *,
    occurrence_index: int,
    block_index: int,
) -> tuple[RawMachineTransitionV182, ...]:
    rows = []
    for local in range(protocol.ACQUISITION_BLOCK_SIZE):
        index = block_index * protocol.ACQUISITION_BLOCK_SIZE + local
        state, action = _acquisition_input(oracle, index)
        rows.append(
            oracle.query(
                occurrence_index=occurrence_index,
                query_index=index,
                state=state,
                action=action,
            )
        )
    return tuple(rows)


def _summary(model: RankedCompiledWorldModelV183) -> dict[str, Any]:
    return {
        "compiled_model_id": model.compiled_model_id,
        "source_label_count": len(model.source_observation_ids),
        "synthesis_events": _synthesis_events(model),
        "archive_reference_count": _archive_reference_count(model),
        "ranking_proof_count": _ranking_proof_count(model),
        "coordinate_program_ids": [row.program_id for row in model.coordinates],
        "terminal_program_id": model.terminal_synthesis.program_id,
        "factor_boundaries": [list(row) for row in model.factor_boundaries],
    }


def _schema(oracle: RankedMachineOracleV183) -> dict[str, Any]:
    return {
        "state_width": oracle.state_width,
        "action_width": oracle.action_width,
        "legal_actions": [list(row) for row in oracle.legal_actions],
    }


def _acquire(
    oracle: RankedMachineOracleV183,
    *,
    arm: str,
    archive: Sequence[ProgramV182],
) -> tuple[tuple[RawMachineTransitionV182, ...], RankedCompiledWorldModelV183, list[dict[str, Any]]]:
    observations: list[RawMachineTransitionV182] = []
    model: RankedCompiledWorldModelV183 | None = None
    history = []
    stable = 0
    credit = 0
    for block_index in range(protocol.MAXIMUM_TARGET_LABELS // protocol.ACQUISITION_BLOCK_SIZE):
        current = _block(oracle, occurrence_index=183_300, block_index=block_index)
        covered = model is not None and all(model.covers(row) for row in current)
        observations.extend(current)
        compiled = False
        events = 0
        archive_count = _archive_reference_count(model) if model else 0
        if len(observations) >= protocol.MINIMUM_TARGET_LABELS:
            if covered:
                stable += 1
            else:
                model = _compile(observations, archive)
                compiled = True
                stable = 0
                events = _synthesis_events(model)
                archive_count = _archive_reference_count(model)
                credit = int(
                    arm == "REVALIDATED_RANKED_PROGRAM_PRIOR"
                    and archive_count > 0
                    and all(model.covers(row) for row in observations)
                ) * protocol.REVALIDATED_PRIOR_CONFIRMATION_CREDIT
        history.append(
            {
                "block_index": block_index,
                "cumulative_target_acquisition_labels": len(observations),
                "compiled": compiled,
                "model_reused_without_recompile": covered,
                "confirmation_zero_error": covered,
                "stable_confirmation_count": stable,
                "revalidated_prior_credit": credit,
                "effective_confirmation_count": stable + credit,
                "synthesis_events": events,
                "archive_reference_count": archive_count,
                "compiled_model_id": model.compiled_model_id if model else None,
            }
        )
        if model is not None and stable + credit >= protocol.STABLE_CONFIRMATION_BLOCKS:
            return tuple(observations), model, history
    _fail("V183 replayed acquisition did not stop")


def _initial(
    oracle: RankedMachineOracleV183,
    occurrence_index: int,
    offset: int,
) -> tuple[int, ...]:
    state = list(oracle.initial_state(occurrence_index))
    state[1] = protocol.PLANNING_HORIZON + 1 if offset == 0 else 1 + ((offset - 1) % protocol.PLANNING_HORIZON)
    return tuple(state)


def _episodes(
    oracle: RankedMachineOracleV183,
    *,
    arm: str,
    acquisition_rows: Sequence[RawMachineTransitionV182],
    acquisition_model: RankedCompiledWorldModelV183,
    archive: Sequence[ProgramV182],
) -> dict[str, Any]:
    rows = list(acquisition_rows)
    model = acquisition_model
    episodes = []
    local_labels = 0
    execution_steps = 0
    planning_events = 0
    synthesis_events = 0
    certificate_count = 0
    for offset in range(protocol.IID_OCCURRENCES_PER_ARM):
        occurrence_index = 183_400 + offset
        state = _initial(oracle, occurrence_index, offset)
        session = RankedMachinePlannerSessionV183(model, horizon=protocol.PLANNING_HORIZON)
        steps = []
        for decision_index in range(protocol.MAXIMUM_DECISIONS_PER_OCCURRENCE):
            certificate = session.certify(state)
            certificate_count += 1
            planning_events += certificate.planning_compute_events
            if not certificate.certified:
                if certificate.failure_reason != "NO_HORIZON_CERTIFICATE":
                    _fail("V183 replay compute failure requested a label")
                action = oracle.legal_actions[0]
                observed = oracle.query(
                    occurrence_index=occurrence_index,
                    query_index=decision_index,
                    state=state,
                    action=action,
                )
                local_labels += 1
                execution_steps += 1
                if local_labels > protocol.MAXIMUM_TARGET_GROUND_LABELS_PER_ARM:
                    _fail("V183 replay crossed local-label cap")
                rows.append(observed)
                model = _compile(rows, archive)
                synthesis_events += _synthesis_events(model)
                if not model.covers(observed):
                    _fail("V183 replayed local distinction did not repair coverage")
                session = RankedMachinePlannerSessionV183(model, horizon=protocol.PLANNING_HORIZON)
                steps.append(
                    {
                        "decision_index": decision_index,
                        "state": list(state),
                        "certificate": certificate.to_document(),
                        "selected_action": list(action),
                        "predicted_support": None,
                        "observation": observed.to_document(),
                        "certificate_failure": "NO_HORIZON_CERTIFICATE",
                        "local_ground_distinction_acquired": True,
                        "local_ground_distinction_requires_preceding_failure": True,
                        "compiled_model_id_after_step": model.compiled_model_id,
                    }
                )
                state = observed.successor
                if observed.terminal:
                    break
                continue
            if certificate.selected_action is None:
                _fail("V183 replay certified action is absent")
            support = model.predict_support(state, certificate.selected_action)
            observed = oracle.query(
                occurrence_index=occurrence_index,
                query_index=decision_index,
                state=state,
                action=certificate.selected_action,
            )
            execution_steps += 1
            matched = observed.successor in support and model.terminal(observed.successor) is observed.terminal
            local = False
            failure = None
            if not matched:
                local = True
                failure = "MISSING_SUPPORT_OR_TERMINAL"
                local_labels += 1
                if local_labels > protocol.MAXIMUM_TARGET_GROUND_LABELS_PER_ARM:
                    _fail("V183 replay crossed local-label cap")
                rows.append(observed)
                model = _compile(rows, archive)
                synthesis_events += _synthesis_events(model)
                if not model.covers(observed):
                    _fail("V183 replayed support repair failed")
                session = RankedMachinePlannerSessionV183(model, horizon=protocol.PLANNING_HORIZON)
            steps.append(
                {
                    "decision_index": decision_index,
                    "state": list(state),
                    "certificate": certificate.to_document(),
                    "selected_action": list(certificate.selected_action),
                    "predicted_support": [list(row) for row in support],
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
            _fail("V183 replay crossed episode cap")
        episodes.append(
            {
                "occurrence_index": occurrence_index,
                "initial_state": steps[0]["state"],
                "steps": steps,
                "execution_step_count": len(steps),
                "terminal_state": list(state),
                "terminal": True,
                "local_ground_label_count": sum(int(row["local_ground_distinction_acquired"]) for row in steps),
            }
        )
    return {
        "arm": arm,
        "episodes": episodes,
        "terminal_episode_count": len(episodes),
        "target_local_ground_label_count": local_labels,
        "execution_step_count": execution_steps,
        "planning_compute_events": planning_events,
        "certificate_count": certificate_count,
        "recovery_synthesis_events": synthesis_events,
        "final_compiled_model": model.to_document(),
        "planner_consumed_only_ranked_total_models": True,
        "all_local_ground_labels_followed_certificate_failure": True,
        "compute_cap_failures_requested_ground_labels": False,
    }


def _reconstruct(execution_preregistration_id: str) -> dict[str, Any]:
    source, target, ood = (_oracle(index) for index in range(3))
    if source.schema_signature() != target.schema_signature() or source.schema_signature() == ood.schema_signature():
        _fail("V183 replay schema controls changed")
    source_rows = tuple(
        row
        for block_index in range(protocol.OFFLINE_SOURCE_LABELS // protocol.ACQUISITION_BLOCK_SIZE)
        for row in _block(source, occurrence_index=183_250, block_index=block_index)
    )
    source_model = _compile(source_rows)
    archive = source_model.reusable_program_archive()
    arm_results = []
    for arm in protocol.ARMS:
        arm_archive = archive if arm == "REVALIDATED_RANKED_PROGRAM_PRIOR" else ()
        acquisition_rows, acquisition_model, history = _acquire(target, arm=arm, archive=arm_archive)
        episode_result = _episodes(
            target,
            arm=arm,
            acquisition_rows=acquisition_rows,
            acquisition_model=acquisition_model,
            archive=arm_archive,
        )
        arm_results.append(
            {
                "arm": arm,
                "target_acquisition_label_count": len(acquisition_rows),
                "target_local_ground_label_count": episode_result["target_local_ground_label_count"],
                "target_total_label_count": len(acquisition_rows) + episode_result["target_local_ground_label_count"],
                "acquisition_observations": [row.to_document() for row in acquisition_rows],
                "acquisition_model": acquisition_model.to_document(),
                "acquisition_model_summary": _summary(acquisition_model),
                "acquisition_history": history,
                "acquisition_synthesis_events": sum(row["synthesis_events"] for row in history),
                **episode_result,
            }
        )
    by_arm = {row["arm"]: row for row in arm_results}
    prior = by_arm["REVALIDATED_RANKED_PROGRAM_PRIOR"]
    no_prior = by_arm["EMPTY_ARCHIVE_NO_PRIOR"]
    protocol_document = protocol.freeze_open_world_ranked_machine_protocol_v183().to_document()
    payload = {
        "schema": "acfqp.open_world_ranked_machine_campaign.v183",
        "execution_preregistration_id": execution_preregistration_id,
        "protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "manifest_reveal_id": reveal.EXPECTED_REVEAL_ID,
        "predecessor_campaign_id": protocol_document["predecessor_campaign_id"],
        "predecessor_preserved": True,
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS_V183),
        "source_observations": [row.to_document() for row in source_rows],
        "source_label_count": len(source_rows),
        "source_compiled_model": source_model.to_document(),
        "source_model_summary": _summary(source_model),
        "source_archive_program_count": len(archive),
        "ood_no_transfer_control": {
            "source_schema_signature": _schema(source),
            "ood_schema_signature": _schema(ood),
            "prior_transfer_rejected": True,
            "rejected_before_target_query": True,
            "ood_target_query_count": 0,
        },
        "arm_results": arm_results,
        "prior_target_total_labels": prior["target_total_label_count"],
        "no_prior_target_total_labels": no_prior["target_total_label_count"],
        "target_labels_avoided": no_prior["target_total_label_count"] - prior["target_total_label_count"],
        "all_registered_episodes_terminal": True,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "exact_same_target_observation_stream_until_prior_stop": True,
        "archive_mdl_discount_used": False,
        "all_compiled_programs_have_structural_ranking_proofs": True,
        "total_over_all_finite_nonnegative_values_of_frozen_schema": True,
        "finite_carrier_totality_enumeration_used": False,
        "general_program_termination_decided": False,
        "proof_system_complete_for_all_terminating_programs": False,
        "planner_consumed_only_ranked_total_compiled_models": True,
        "planning_horizon": protocol.PLANNING_HORIZON,
        "planning_horizon_greater_than_two": True,
        "all_local_ground_labels_followed_certificate_failure": True,
        "compute_cap_failures_requested_ground_labels": False,
        "label_axes_separate_from_execution_and_compute": True,
        "proof_language_program_length_unbounded": True,
        "current_occurrence_candidate_set_finite": True,
        "generic_ranked_program_schema_enumerated": True,
        "domain_specific_whole_program_template_used": False,
        "named_domain_family_used": False,
        "named_layout_used": False,
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
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v183(
            domains.CONSTRUCTION_K7_CAMPAIGN_V183_DOMAIN,
            payload,
        ),
    }


def verify_open_world_ranked_machine_campaign_bytes_independently_v183(
    campaign_bytes: bytes,
    *,
    execution_preregistration_id: str,
) -> dict[str, Any]:
    observed = loads_canonical_json(campaign_bytes)
    if type(observed) is not dict or canonical_json_bytes(observed) != campaign_bytes:
        _fail("V183 campaign is not one canonical object")
    expected = _reconstruct(execution_preregistration_id)
    if canonical_json_bytes(expected) != campaign_bytes:
        _fail("V183 producer-free reconstruction changed")
    payload = {
        "schema": "acfqp.open_world_ranked_machine_independent_verification.v183",
        "execution_preregistration_id": execution_preregistration_id,
        "protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "manifest_reveal_id": reveal.EXPECTED_REVEAL_ID,
        "campaign_id": expected["campaign_id"],
        "campaign_byte_count": len(campaign_bytes),
        "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "source_and_target_raw_observations_replayed": True,
        "ranked_termination_certificates_replayed": True,
        "compiled_models_replayed": True,
        "acquisition_stop_rules_replayed": True,
        "receding_plans_replayed": True,
        "certificate_failure_local_recovery_replayed": True,
        "ood_no_transfer_replayed": True,
        "producer_module_imported": False,
        "prior_target_total_labels": expected["prior_target_total_labels"],
        "no_prior_target_total_labels": expected["no_prior_target_total_labels"],
        "target_labels_avoided": expected["target_labels_avoided"],
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "total_work_dominance_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "verification_id": domains.extension_content_id_v183(
            domains.CONSTRUCTION_K7_VERIFICATION_V183_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "OpenWorldRankedMachineIndependentVerifierV183Error",
    "verify_open_world_ranked_machine_campaign_bytes_independently_v183",
)
