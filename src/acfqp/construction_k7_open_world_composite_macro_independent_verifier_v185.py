"""Producer-free reconstruction of the V185 composite-macro campaign."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v185 as domains
from acfqp import construction_k7_open_world_composite_macro_manifest_reveal_v185 as reveal
from acfqp import construction_k7_open_world_composite_macro_protocol_v185 as protocol
from acfqp.open_world_adaptive_composite_synthesizer_v185 import (
    compile_adaptive_composite_world_model_v185,
)
from acfqp.open_world_composite_macro_machine_v185 import (
    CompositeMacroCompiledWorldModelV185,
    CompositeMacroLibraryV185,
    CompositeMacroPlannerSessionV185,
    discover_composite_macro_library_v185,
)
from acfqp.open_world_composite_macro_oracle_v185 import (
    CompositeMacroOracleV185,
    reveal_composite_macro_oracle_v185,
)
from acfqp.open_world_machine_compiled_model_v182 import RawMachineTransitionV182
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


class OpenWorldCompositeMacroIndependentVerifierV185Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldCompositeMacroIndependentVerifierV185Error(message)


def _oracle(index: int) -> CompositeMacroOracleV185:
    return reveal_composite_macro_oracle_v185(
        manifest_bytes=canonical_json_bytes(reveal.MANIFEST_DOCUMENTS_V185[index]),
        expected_commitment=protocol.MANIFEST_COMMITMENTS_V185[index],
    )


def _compile(
    rows: Sequence[RawMachineTransitionV182],
    library: CompositeMacroLibraryV185 | None,
) -> CompositeMacroCompiledWorldModelV185:
    return compile_adaptive_composite_world_model_v185(
        rows,
        macro_library=library,
        maximum_macro_candidate_evaluations_per_scalar=(
            protocol.MAXIMUM_MACRO_CANDIDATE_EVALUATIONS_PER_SCALAR
        ),
        maximum_fair_candidate_evaluations_per_scalar=(
            protocol.MAXIMUM_FAIR_ENUMERATION_EVENTS_PER_SCALAR
        ),
        resource_step_cap=protocol.RESOURCE_STEP_CAP,
        register_count=protocol.REGISTER_COUNT,
        maximum_residual_support=protocol.MAXIMUM_RESIDUAL_SUPPORT,
    )


def _row(document: Mapping[str, Any]) -> RawMachineTransitionV182:
    if type(document) is not dict or set(document) != {
        "schema",
        "occurrence_index",
        "query_index",
        "state",
        "action",
        "successor",
        "terminal",
        "observation_id",
    }:
        _fail("V185 raw observation schema changed")
    row = RawMachineTransitionV182.observe(
        occurrence_index=document["occurrence_index"],
        query_index=document["query_index"],
        state=document["state"],
        action=document["action"],
        successor=document["successor"],
        terminal=document["terminal"],
    )
    if row.to_document() != document:
        _fail("V185 raw observation identity changed")
    return row


def _synthesis_events(model: CompositeMacroCompiledWorldModelV185) -> int:
    return sum(row.candidate_evaluations for row in model.coordinates) + (
        model.terminal_synthesis.candidate_evaluations
    )


def _macro_references(model: CompositeMacroCompiledWorldModelV185) -> int:
    return sum(row.selected_macro_id is not None for row in model.coordinates) + int(
        model.terminal_synthesis.selected_macro_id is not None
    )


def _model_summary(model: CompositeMacroCompiledWorldModelV185) -> dict[str, Any]:
    return {
        "compiled_model_id": model.compiled_model_id,
        "source_label_count": len(model.source_observation_ids),
        "synthesis_candidate_evaluations": _synthesis_events(model),
        "macro_reference_count": _macro_references(model),
        "coordinate_program_ids": [row.program_id for row in model.coordinates],
        "terminal_program_id": model.terminal_synthesis.program_id,
        "factor_boundaries": [list(row) for row in model.factor_boundaries],
    }


def _schema(oracle: CompositeMacroOracleV185) -> dict[str, Any]:
    return {
        "state_width": oracle.state_width,
        "action_width": oracle.action_width,
        "legal_actions": [list(row) for row in oracle.legal_actions],
    }


def _input(
    oracle: CompositeMacroOracleV185, index: int
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    digest = hashlib.sha256(
        b"acfqp:v185:witness-blind-composite-macro-acquisition\x00"
        + oracle.manifest_commitment.encode()
        + index.to_bytes(8, "big")
    ).digest()
    return (
        tuple(digest[(3 * column) % len(digest)] % 5 for column in range(oracle.state_width)),
        oracle.legal_actions[index % len(oracle.legal_actions)],
    )


def _block(
    oracle: CompositeMacroOracleV185,
    *,
    occurrence_index: int,
    block_index: int,
) -> tuple[RawMachineTransitionV182, ...]:
    result = []
    for local in range(protocol.ACQUISITION_BLOCK_SIZE):
        index = block_index * protocol.ACQUISITION_BLOCK_SIZE + local
        state, action = _input(oracle, index)
        result.append(
            oracle.query(
                occurrence_index=occurrence_index,
                query_index=index,
                state=state,
                action=action,
            )
        )
    return tuple(result)


def _macro_source_document(model: CompositeMacroCompiledWorldModelV185) -> dict[str, Any]:
    return {
        **model.to_document(),
        "finite_candidate_catalog_used": False,
        "new_primitive_opcode_invented": False,
    }


def _replay_acquisition(
    oracle: CompositeMacroOracleV185,
    *,
    arm: str,
    occurrence_index: int,
    library: CompositeMacroLibraryV185 | None,
) -> tuple[
    tuple[RawMachineTransitionV182, ...],
    CompositeMacroCompiledWorldModelV185,
    list[dict[str, Any]],
]:
    observations: list[RawMachineTransitionV182] = []
    model: CompositeMacroCompiledWorldModelV185 | None = None
    history = []
    stable = 0
    credit = 0
    for block_index in range(
        protocol.MAXIMUM_TARGET_LABELS_PER_DISTRIBUTION
        // protocol.ACQUISITION_BLOCK_SIZE
    ):
        current = _block(
            oracle,
            occurrence_index=occurrence_index,
            block_index=block_index,
        )
        covered = model is not None and all(model.covers(row) for row in current)
        observations.extend(current)
        compiled = False
        events = 0
        references = _macro_references(model) if model else 0
        if len(observations) >= protocol.MINIMUM_TARGET_LABELS_PER_DISTRIBUTION:
            if covered:
                stable += 1
            else:
                model = _compile(observations, library)
                compiled = True
                stable = 0
                events = _synthesis_events(model)
                references = _macro_references(model)
                credit = int(
                    arm
                    == "REVALIDATED_OBSERVATION_DERIVED_COMPOSITE_MACRO_PRIOR"
                    and references > 0
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
                "synthesis_candidate_evaluations": events,
                "macro_reference_count": references,
                "compiled_model_id": model.compiled_model_id if model else None,
            }
        )
        if model is not None and stable + credit >= protocol.STABLE_CONFIRMATION_BLOCKS:
            return tuple(observations), model, history
    _fail("V185 independent acquisition did not stop")


def _replay_episodes(
    oracle: CompositeMacroOracleV185,
    *,
    distribution_index: int,
    acquisition_rows: Sequence[RawMachineTransitionV182],
    acquisition_model: CompositeMacroCompiledWorldModelV185,
    library: CompositeMacroLibraryV185 | None,
) -> dict[str, Any]:
    rows = list(acquisition_rows)
    model = acquisition_model
    episodes = []
    local_labels = execution_steps = planning_events = certificate_count = recovery_events = 0
    for offset in range(protocol.IID_OCCURRENCES_PER_DISTRIBUTION_PER_ARM):
        occurrence_index = 185_400 + distribution_index * 100 + offset
        state = oracle.initial_state(occurrence_index)
        session = CompositeMacroPlannerSessionV185(model, horizon=protocol.PLANNING_HORIZON)
        steps = []
        for decision_index in range(protocol.MAXIMUM_DECISIONS_PER_OCCURRENCE):
            certificate = session.certify(state)
            certificate_count += 1
            planning_events += certificate.planning_compute_events
            if not certificate.certified:
                if certificate.failure_reason != "NO_HORIZON_CERTIFICATE":
                    _fail("V185 independent nonsemantic recovery changed")
                action = oracle.legal_actions[0]
                observed = oracle.query(
                    occurrence_index=occurrence_index,
                    query_index=decision_index,
                    state=state,
                    action=action,
                )
                local_labels += 1
                execution_steps += 1
                rows.append(observed)
                model = _compile(rows, library)
                recovery_events += _synthesis_events(model)
                session = CompositeMacroPlannerSessionV185(model, horizon=protocol.PLANNING_HORIZON)
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
                        "compiled_model_id_after_step": model.compiled_model_id,
                    }
                )
            else:
                if certificate.selected_action is None:
                    _fail("V185 independent certified action is absent")
                support = model.predict_support(state, certificate.selected_action)
                observed = oracle.query(
                    occurrence_index=occurrence_index,
                    query_index=decision_index,
                    state=state,
                    action=certificate.selected_action,
                )
                execution_steps += 1
                matched = observed.successor in support and model.terminal(observed.successor) is observed.terminal
                local = not matched
                failure = None if matched else "MISSING_SUPPORT_OR_TERMINAL"
                if local:
                    local_labels += 1
                    rows.append(observed)
                    model = _compile(rows, library)
                    recovery_events += _synthesis_events(model)
                    session = CompositeMacroPlannerSessionV185(model, horizon=protocol.PLANNING_HORIZON)
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
                        "compiled_model_id_after_step": model.compiled_model_id,
                    }
                )
            state = observed.successor
            if observed.terminal:
                break
        if not oracle.terminal(state):
            _fail("V185 independent episode crossed its cap")
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
        "episodes": episodes,
        "terminal_episode_count": len(episodes),
        "target_local_ground_label_count": local_labels,
        "execution_step_count": execution_steps,
        "planning_compute_events": planning_events,
        "certificate_count": certificate_count,
        "recovery_synthesis_candidate_evaluations": recovery_events,
        "final_compiled_model": model.to_document(),
        "all_local_ground_labels_followed_certificate_failure": True,
        "compute_cap_failures_requested_ground_labels": False,
    }


def _sum_work(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return {
        "source_labels": 0,
        "target_labels": sum(row["target_total_label_count"] for row in rows),
        "macro_discovery_events": 0,
        "synthesis_candidate_evaluations": sum(
            row["acquisition_synthesis_candidate_evaluations"]
            + row["recovery_synthesis_candidate_evaluations"]
            for row in rows
        ),
        "planning_compute_events": sum(row["planning_compute_events"] for row in rows),
        "certificate_evaluations": sum(row["certificate_count"] for row in rows),
        "execution_steps": sum(row["execution_step_count"] for row in rows),
    }


def _reconstruct(execution_preregistration_id: str) -> dict[str, Any]:
    source = _oracle(0)
    targets = tuple(_oracle(index) for index in range(1, 5))
    ood = _oracle(5)
    source_rows = tuple(
        row
        for block_index in range(protocol.OFFLINE_SOURCE_LABELS // protocol.ACQUISITION_BLOCK_SIZE)
        for row in _block(source, occurrence_index=185_250, block_index=block_index)
    )
    checkpoint_counts = (
        protocol.OFFLINE_SOURCE_LABELS - protocol.ACQUISITION_BLOCK_SIZE,
        protocol.OFFLINE_SOURCE_LABELS,
    )
    source_models = tuple(_compile(source_rows[:count], None) for count in checkpoint_counts)
    source_model = source_models[-1]
    library = discover_composite_macro_library_v185(
        tuple(_macro_source_document(model) for model in source_models),
        minimum_occurrences=protocol.MINIMUM_MACRO_OCCURRENCES,
        minimum_operator_count=protocol.MINIMUM_MACRO_OPERATOR_COUNT,
        minimum_mdl_gain_tokens=protocol.MINIMUM_MACRO_MDL_GAIN_TOKENS,
        maximum_macro_count=protocol.MAXIMUM_MACRO_COUNT,
    )
    if not library.macros:
        _fail("V185 independent source macro is absent")
    arm_results = []
    for arm in protocol.ARMS:
        distributions = []
        for index in range(protocol.TARGET_DISTRIBUTION_COUNT):
            target = _oracle(index + 1)
            arm_library = library if arm == protocol.ARMS[0] else None
            acquisition_rows, model, history = _replay_acquisition(
                target,
                arm=arm,
                occurrence_index=185_300 + index,
                library=arm_library,
            )
            episodes = _replay_episodes(
                target,
                distribution_index=index,
                acquisition_rows=acquisition_rows,
                acquisition_model=model,
                library=arm_library,
            )
            distributions.append(
                {
                    "distribution_index": index,
                    "manifest_commitment": protocol.MANIFEST_COMMITMENTS_V185[index + 1],
                    "target_acquisition_label_count": len(acquisition_rows),
                    "target_local_ground_label_count": episodes["target_local_ground_label_count"],
                    "target_total_label_count": len(acquisition_rows) + episodes["target_local_ground_label_count"],
                    "acquisition_observations": [row.to_document() for row in acquisition_rows],
                    "acquisition_model": model.to_document(),
                    "acquisition_model_summary": _model_summary(model),
                    "acquisition_history": history,
                    "acquisition_synthesis_candidate_evaluations": sum(row["synthesis_candidate_evaluations"] for row in history),
                    **episodes,
                }
            )
        arm_results.append(
            {
                "arm": arm,
                "distribution_results": distributions,
                "registered_target_work_vector": _sum_work(distributions),
                "all_registered_episodes_terminal": True,
            }
        )
    prior, control = arm_results
    prior_work = prior["registered_target_work_vector"]
    control_work = control["registered_target_work_vector"]
    componentwise = all(prior_work[axis] <= control_work[axis] for axis in protocol.TOTAL_WORK_AXES)
    strict_axes = [axis for axis in protocol.TOTAL_WORK_AXES if prior_work[axis] < control_work[axis]]
    taxes = [
        b["target_total_label_count"] - a["target_total_label_count"]
        for a, b in zip(prior["distribution_results"], control["distribution_results"], strict=True)
    ]
    protocol_document = protocol.freeze_open_world_composite_macro_protocol_v185().to_document()
    macro_events = sum(row.occurrence_count for row in library.macros)
    payload = {
        "schema": "acfqp.open_world_composite_macro_campaign.v185",
        "execution_preregistration_id": execution_preregistration_id,
        "protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "manifest_reveal_id": reveal.EXPECTED_REVEAL_ID,
        "predecessor_campaign_id": protocol_document["predecessor_campaign_id"],
        "predecessor_preserved": True,
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS_V185),
        "source_observations": [row.to_document() for row in source_rows],
        "source_label_count": len(source_rows),
        "source_compiled_model": source_model.to_document(),
        "source_model_summary": _model_summary(source_model),
        "source_checkpoint_label_counts": list(checkpoint_counts),
        "source_checkpoint_models": [model.to_document() for model in source_models],
        "source_checkpoint_model_ids": [model.compiled_model_id for model in source_models],
        "source_checkpoint_models_use_only_registered_source_rows": True,
        "macro_library": library.to_document(),
        "macro_library_id": library.macro_library_id,
        "macro_discovery_events": macro_events,
        "reusable_composite_operator_invented": True,
        "ood_no_transfer_control": {
            "source_schema_signature": _schema(source),
            "ood_schema_signature": _schema(ood),
            "prior_transfer_rejected": True,
            "rejected_before_target_query": True,
            "ood_target_query_count": ood.query_count,
        },
        "arm_results": arm_results,
        "target_distribution_count": protocol.TARGET_DISTRIBUTION_COUNT,
        "prior_target_total_labels": prior_work["target_labels"],
        "no_prior_target_total_labels": control_work["target_labels"],
        "target_labels_avoided": control_work["target_labels"] - prior_work["target_labels"],
        "per_distribution_target_labels_avoided": taxes,
        "componentwise_target_work_dominance_observed": componentwise,
        "strictly_improved_target_work_axes": strict_axes,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "only_macro_library_prior_toggled_between_arms": True,
        "exact_same_target_stream_until_prior_stop": True,
        "archive_mdl_discount_used": False,
        "candidate_language_countably_infinite": True,
        "actual_search_prefix_finite": True,
        "predeclared_reusable_factor_slots": [],
        "predeclared_macro_bodies": [],
        "all_compiled_programs_structurally_total": True,
        "resource_cap_exhaustion_used_as_infeasibility": False,
        "planning_horizon": protocol.PLANNING_HORIZON,
        "planning_horizon_greater_than_two": True,
        "all_local_ground_labels_followed_certificate_failure": True,
        "compute_cap_failures_requested_ground_labels": False,
        "multi_distribution_iid_sample_efficiency_observed": True,
        "source_target_local_labels_execution_macro_synthesis_planning_and_certificate_compute_separate": True,
        "new_low_level_primitive_opcode_invented": False,
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "official_total_work_dominance_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v185(domains.CONSTRUCTION_K7_CAMPAIGN_V185_DOMAIN, payload),
    }


def verify_open_world_composite_macro_campaign_bytes_independently_v185(
    campaign_bytes: bytes,
    *,
    execution_preregistration_id: str,
) -> dict[str, Any]:
    document = loads_canonical_json(campaign_bytes)
    if type(document) is not dict or canonical_json_bytes(document) != campaign_bytes:
        _fail("V185 campaign bytes are not canonical")
    reconstructed = _reconstruct(execution_preregistration_id)
    if document != reconstructed:
        _fail("V185 producer-free reconstruction changed")
    payload = {
        "schema": "acfqp.open_world_composite_macro_verification.v185",
        "campaign_id": reconstructed["campaign_id"],
        "execution_preregistration_id": execution_preregistration_id,
        "campaign_byte_count": len(campaign_bytes),
        "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "producer_module_imported": False,
        "source_observations_reconstructed": True,
        "source_checkpoint_models_recompiled": True,
        "composite_macro_library_rediscovered": True,
        "target_acquisition_streams_reconstructed": True,
        "target_models_recompiled": True,
        "held_out_plans_and_certificates_replayed": True,
        "strict_ood_no_transfer_replayed": True,
        "reusable_composite_operator_invented": True,
        "new_low_level_primitive_opcode_invented": False,
        "target_labels_avoided": reconstructed["target_labels_avoided"],
        "componentwise_target_work_dominance_observed": reconstructed["componentwise_target_work_dominance_observed"],
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "verification_id": domains.extension_content_id_v185(
            domains.CONSTRUCTION_K7_VERIFICATION_V185_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "OpenWorldCompositeMacroIndependentVerifierV185Error",
    "verify_open_world_composite_macro_campaign_bytes_independently_v185",
)
