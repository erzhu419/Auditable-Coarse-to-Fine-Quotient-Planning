"""Fresh V185 campaign for observation-derived composite-macro transfer."""

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
from acfqp.phase3e_ids import canonical_json_bytes


class OpenWorldCompositeMacroCampaignV185Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldCompositeMacroCampaignV185Error(message)


def _oracle(
    document: Mapping[str, Any], commitment: str
) -> CompositeMacroOracleV185:
    return reveal_composite_macro_oracle_v185(
        manifest_bytes=canonical_json_bytes(dict(document)),
        expected_commitment=commitment,
    )


def _compile(
    rows: Sequence[RawMachineTransitionV182],
    macro_library: CompositeMacroLibraryV185 | None,
) -> CompositeMacroCompiledWorldModelV185:
    return compile_adaptive_composite_world_model_v185(
        rows,
        macro_library=macro_library,
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


def _macro_source_document(
    model: CompositeMacroCompiledWorldModelV185,
) -> dict[str, Any]:
    document = model.to_document()
    # The frozen V185 miner accepts both V184 and V185 model schemas but keeps
    # the historical negative-claim spellings at its input boundary.
    return {
        **document,
        "finite_candidate_catalog_used": False,
        "new_primitive_opcode_invented": False,
    }


def _acquisition_input(
    oracle: CompositeMacroOracleV185,
    unique_index: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    digest = hashlib.sha256(
        b"acfqp:v185:witness-blind-composite-macro-acquisition\x00"
        + oracle.manifest_commitment.encode()
        + unique_index.to_bytes(8, "big")
    ).digest()
    state = tuple(digest[(3 * index) % len(digest)] % 5 for index in range(oracle.state_width))
    action = oracle.legal_actions[unique_index % len(oracle.legal_actions)]
    return state, action


def _query_block(
    oracle: CompositeMacroOracleV185,
    *,
    occurrence_index: int,
    block_index: int,
) -> tuple[RawMachineTransitionV182, ...]:
    rows = []
    for local_index in range(protocol.ACQUISITION_BLOCK_SIZE):
        query_index = block_index * protocol.ACQUISITION_BLOCK_SIZE + local_index
        state, action = _acquisition_input(oracle, query_index)
        rows.append(
            oracle.query(
                occurrence_index=occurrence_index,
                query_index=query_index,
                state=state,
                action=action,
            )
        )
    return tuple(rows)


def _acquire(
    oracle: CompositeMacroOracleV185,
    *,
    arm: str,
    occurrence_index: int,
    macro_library: CompositeMacroLibraryV185 | None,
) -> tuple[
    tuple[RawMachineTransitionV182, ...],
    CompositeMacroCompiledWorldModelV185,
    list[dict[str, Any]],
]:
    observations: list[RawMachineTransitionV182] = []
    model: CompositeMacroCompiledWorldModelV185 | None = None
    history: list[dict[str, Any]] = []
    stable = 0
    credit = 0
    for block_index in range(
        protocol.MAXIMUM_TARGET_LABELS_PER_DISTRIBUTION
        // protocol.ACQUISITION_BLOCK_SIZE
    ):
        current = _query_block(
            oracle,
            occurrence_index=occurrence_index,
            block_index=block_index,
        )
        covered = model is not None and all(model.covers(row) for row in current)
        observations.extend(current)
        compiled = False
        events = 0
        references = _macro_references(model) if model is not None else 0
        if len(observations) >= protocol.MINIMUM_TARGET_LABELS_PER_DISTRIBUTION:
            if covered:
                stable += 1
            else:
                model = _compile(observations, macro_library)
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
    _fail(f"V185 acquisition did not stop for {arm}/{oracle.role}")


def _episodes(
    oracle: CompositeMacroOracleV185,
    *,
    distribution_index: int,
    acquisition_rows: Sequence[RawMachineTransitionV182],
    acquisition_model: CompositeMacroCompiledWorldModelV185,
    macro_library: CompositeMacroLibraryV185 | None,
) -> dict[str, Any]:
    rows = list(acquisition_rows)
    model = acquisition_model
    episodes = []
    local_labels = 0
    execution_steps = 0
    planning_events = 0
    certificate_count = 0
    recovery_events = 0
    for occurrence_offset in range(protocol.IID_OCCURRENCES_PER_DISTRIBUTION_PER_ARM):
        occurrence_index = 185_400 + distribution_index * 100 + occurrence_offset
        state = oracle.initial_state(occurrence_index)
        session = CompositeMacroPlannerSessionV185(
            model,
            horizon=protocol.PLANNING_HORIZON,
        )
        steps = []
        for decision_index in range(protocol.MAXIMUM_DECISIONS_PER_OCCURRENCE):
            certificate = session.certify(state)
            certificate_count += 1
            planning_events += certificate.planning_compute_events
            if not certificate.certified:
                if certificate.failure_reason != "NO_HORIZON_CERTIFICATE":
                    _fail("V185 nonsemantic failure attempted a ground query")
                if local_labels >= protocol.MAXIMUM_LOCAL_GROUND_LABELS_PER_DISTRIBUTION_PER_ARM:
                    _fail("V185 local-ground label cap exhausted")
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
                model = _compile(rows, macro_library)
                recovery_events += _synthesis_events(model)
                if not model.covers(observed):
                    _fail("V185 local distinction did not repair current support")
                session = CompositeMacroPlannerSessionV185(
                    model,
                    horizon=protocol.PLANNING_HORIZON,
                )
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
                state = observed.successor
                if observed.terminal:
                    break
                continue
            if certificate.selected_action is None:
                _fail("V185 certified action is absent")
            support = model.predict_support(state, certificate.selected_action)
            observed = oracle.query(
                occurrence_index=occurrence_index,
                query_index=decision_index,
                state=state,
                action=certificate.selected_action,
            )
            execution_steps += 1
            matched = (
                observed.successor in support
                and model.terminal(observed.successor) is observed.terminal
            )
            local = False
            failure = None
            if not matched:
                if local_labels >= protocol.MAXIMUM_LOCAL_GROUND_LABELS_PER_DISTRIBUTION_PER_ARM:
                    _fail("V185 local-ground label cap exhausted")
                local = True
                failure = "MISSING_SUPPORT_OR_TERMINAL"
                local_labels += 1
                rows.append(observed)
                model = _compile(rows, macro_library)
                recovery_events += _synthesis_events(model)
                if not model.covers(observed):
                    _fail("V185 local support repair failed")
                session = CompositeMacroPlannerSessionV185(
                    model,
                    horizon=protocol.PLANNING_HORIZON,
                )
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
            _fail("V185 episode crossed its decision cap")
        episodes.append(
            {
                "occurrence_index": occurrence_index,
                "initial_state": steps[0]["state"],
                "steps": steps,
                "execution_step_count": len(steps),
                "terminal_state": list(state),
                "terminal": True,
                "local_ground_label_count": sum(
                    int(step["local_ground_distinction_acquired"]) for step in steps
                ),
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


def build_open_world_composite_macro_campaign_v185(
    *,
    manifest_documents: Sequence[Mapping[str, Any]],
    manifest_commitments: Sequence[str],
    execution_preregistration_id: str,
) -> dict[str, Any]:
    if (
        type(manifest_documents) not in {tuple, list}
        or type(manifest_commitments) not in {tuple, list}
        or len(manifest_documents) != 6
        or len(manifest_commitments) != 6
        or type(execution_preregistration_id) is not str
        or len(execution_preregistration_id) != 64
    ):
        _fail("V185 campaign denominator or execution identity changed")
    source = _oracle(manifest_documents[0], manifest_commitments[0])
    targets = tuple(
        _oracle(manifest_documents[index], manifest_commitments[index])
        for index in range(1, 5)
    )
    ood = _oracle(manifest_documents[5], manifest_commitments[5])
    if any(target.schema_signature() != source.schema_signature() for target in targets):
        _fail("V185 matched target schema changed")
    if ood.schema_signature() == source.schema_signature():
        _fail("V185 OOD control collapsed")
    source_rows = tuple(
        row
        for block_index in range(protocol.OFFLINE_SOURCE_LABELS // protocol.ACQUISITION_BLOCK_SIZE)
        for row in _query_block(source, occurrence_index=185_250, block_index=block_index)
    )
    source_checkpoint_label_counts = (
        protocol.OFFLINE_SOURCE_LABELS - protocol.ACQUISITION_BLOCK_SIZE,
        protocol.OFFLINE_SOURCE_LABELS,
    )
    source_models = tuple(
        _compile(source_rows[:label_count], None)
        for label_count in source_checkpoint_label_counts
    )
    source_model = source_models[-1]
    macro_library = discover_composite_macro_library_v185(
        tuple(_macro_source_document(model) for model in source_models),
        minimum_occurrences=protocol.MINIMUM_MACRO_OCCURRENCES,
        minimum_operator_count=protocol.MINIMUM_MACRO_OPERATOR_COUNT,
        minimum_mdl_gain_tokens=protocol.MINIMUM_MACRO_MDL_GAIN_TOKENS,
        maximum_macro_count=protocol.MAXIMUM_MACRO_COUNT,
    )
    if not macro_library.macros:
        _fail("V185 source observations yielded no positive-MDL composite macro")
    arm_results = []
    for arm in protocol.ARMS:
        distribution_results = []
        for distribution_index in range(protocol.TARGET_DISTRIBUTION_COUNT):
            target = _oracle(
                manifest_documents[distribution_index + 1],
                manifest_commitments[distribution_index + 1],
            )
            arm_library = (
                macro_library
                if arm == "REVALIDATED_OBSERVATION_DERIVED_COMPOSITE_MACRO_PRIOR"
                else None
            )
            acquisition_rows, acquisition_model, history = _acquire(
                target,
                arm=arm,
                occurrence_index=185_300 + distribution_index,
                macro_library=arm_library,
            )
            episode = _episodes(
                target,
                distribution_index=distribution_index,
                acquisition_rows=acquisition_rows,
                acquisition_model=acquisition_model,
                macro_library=arm_library,
            )
            distribution_results.append(
                {
                    "distribution_index": distribution_index,
                    "manifest_commitment": manifest_commitments[distribution_index + 1],
                    "target_acquisition_label_count": len(acquisition_rows),
                    "target_local_ground_label_count": episode["target_local_ground_label_count"],
                    "target_total_label_count": len(acquisition_rows) + episode["target_local_ground_label_count"],
                    "acquisition_observations": [row.to_document() for row in acquisition_rows],
                    "acquisition_model": acquisition_model.to_document(),
                    "acquisition_model_summary": _model_summary(acquisition_model),
                    "acquisition_history": history,
                    "acquisition_synthesis_candidate_evaluations": sum(
                        row["synthesis_candidate_evaluations"] for row in history
                    ),
                    **episode,
                }
            )
        work = _sum_work(distribution_results)
        arm_results.append(
            {
                "arm": arm,
                "distribution_results": distribution_results,
                "registered_target_work_vector": work,
                "all_registered_episodes_terminal": all(
                    row["terminal_episode_count"]
                    == protocol.IID_OCCURRENCES_PER_DISTRIBUTION_PER_ARM
                    for row in distribution_results
                ),
            }
        )
    by_arm = {row["arm"]: row for row in arm_results}
    prior = by_arm["REVALIDATED_OBSERVATION_DERIVED_COMPOSITE_MACRO_PRIOR"]
    control = by_arm["EMPTY_MACRO_LIBRARY_NO_PRIOR"]
    prior_work = prior["registered_target_work_vector"]
    control_work = control["registered_target_work_vector"]
    componentwise = all(prior_work[axis] <= control_work[axis] for axis in protocol.TOTAL_WORK_AXES)
    strict_axes = [axis for axis in protocol.TOTAL_WORK_AXES if prior_work[axis] < control_work[axis]]
    per_distribution_tax = [
        control_row["target_total_label_count"] - prior_row["target_total_label_count"]
        for prior_row, control_row in zip(prior["distribution_results"], control["distribution_results"], strict=True)
    ]
    if not (
        prior["all_registered_episodes_terminal"] is True
        and control["all_registered_episodes_terminal"] is True
        and all(value > 0 for value in per_distribution_tax)
        and componentwise
        and {"target_labels", "synthesis_candidate_evaluations"}.issubset(strict_axes)
    ):
        _fail("V185 registered sample-tax or target-work comparison failed")
    protocol_document = protocol.freeze_open_world_composite_macro_protocol_v185().to_document()
    macro_events = sum(row.occurrence_count for row in macro_library.macros)
    payload = {
        "schema": "acfqp.open_world_composite_macro_campaign.v185",
        "execution_preregistration_id": execution_preregistration_id,
        "protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "manifest_reveal_id": reveal.EXPECTED_REVEAL_ID,
        "predecessor_campaign_id": protocol_document["predecessor_campaign_id"],
        "predecessor_preserved": True,
        "manifest_commitments": list(manifest_commitments),
        "source_observations": [row.to_document() for row in source_rows],
        "source_label_count": len(source_rows),
        "source_compiled_model": source_model.to_document(),
        "source_model_summary": _model_summary(source_model),
        "source_checkpoint_label_counts": list(source_checkpoint_label_counts),
        "source_checkpoint_models": [model.to_document() for model in source_models],
        "source_checkpoint_model_ids": [model.compiled_model_id for model in source_models],
        "source_checkpoint_models_use_only_registered_source_rows": True,
        "macro_library": macro_library.to_document(),
        "macro_library_id": macro_library.macro_library_id,
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
        "per_distribution_target_labels_avoided": per_distribution_tax,
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
        "campaign_id": domains.extension_content_id_v185(
            domains.CONSTRUCTION_K7_CAMPAIGN_V185_DOMAIN,
            payload,
        ),
    }


def run_open_world_composite_macro_campaign_v185(
    *, execution_preregistration_id: str
) -> dict[str, Any]:
    return build_open_world_composite_macro_campaign_v185(
        manifest_documents=reveal.MANIFEST_DOCUMENTS_V185,
        manifest_commitments=protocol.MANIFEST_COMMITMENTS_V185,
        execution_preregistration_id=execution_preregistration_id,
    )


__all__ = (
    "OpenWorldCompositeMacroCampaignV185Error",
    "build_open_world_composite_macro_campaign_v185",
    "run_open_world_composite_macro_campaign_v185",
)
