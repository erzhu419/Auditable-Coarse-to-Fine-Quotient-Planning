"""V131 factor prior from a normalized artifact/uniform hypothesis mixture."""

from __future__ import annotations

import hashlib
from math import ceil, gcd, log2
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v131 as domains
from acfqp import generic_atomic_expression_world_model_v4 as atomic
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import (
    fair_witness_blind_path_first_stream_v129r1,
)
from acfqp.automatic_minimal_factor_dictionary_v131 import (
    verify_automatic_minimal_factor_dictionary_v131,
)
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    _dependencies,
    exact_generic_artifact_factor_replay_v121,
    generic_artifact_factor_stop_update_v121,
    instantiate_normalized_subprograms_v121,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
)
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    _ast_bits,
    _dependency_binding_bits,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


class AutomaticDictionaryFactorPriorAcquisitionV131Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AutomaticDictionaryFactorPriorAcquisitionV131Error(message)


def _identifier(domain: str, payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v131(domain, payload)}


def _artifact_expression_signatures(
    state_width: int,
    action_width: int,
    projection: Mapping[str, Any],
) -> dict[bytes, str]:
    result: dict[bytes, str] = {}
    for target in range(state_width):
        for row in instantiate_normalized_subprograms_v121(
            target, state_width, action_width, projection
        ):
            result[canonical_json_bytes(row["expression"])] = row["signature_sha256"]
    return result


def derive_automatic_dictionary_calibration_v131(
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the observation-free prefix code for artifact/AST mixture arms."""

    templates = projection.get("cross_schema_subprograms")
    if type(templates) is not list or not templates:
        _fail("V131 automatic-dictionary source support changed")
    schema_pairs = {
        tuple(pair)
        for template in templates
        for pair in template.get("source_schema_pairs", ())
    }
    if not schema_pairs:
        _fail("V131 automatic-dictionary source schema pairs changed")
    observed = sum(len(template.get("source_schema_pairs", ())) for template in templates)
    possible = len(templates) * len(schema_pairs)
    if observed <= 0 or observed > possible:
        _fail("V131 automatic-dictionary support coverage changed")
    library_index_bits = max(1, ceil(log2(max(2, len(templates)))))
    payload = {
        "schema": "acfqp.source_support_automatic_dictionary_calibration.v131",
        "source_factor_library_id": projection["source_factor_library_id"],
        "artifact_template_count": len(templates),
        "distinct_source_schema_pair_count": len(schema_pairs),
        "observed_template_schema_support_cell_count": observed,
        "possible_template_schema_support_cell_count": possible,
        "automatic_dictionary_branch_prefix_bits": 1,
        "artifact_library_index_prefix_bits": library_index_bits,
        "artifact_branch_code": "LIBRARY_INDEX_PLUS_ANONYMOUS_DEPENDENCY_BINDING",
        "uniform_tail_branch_code": "FULL_TYPED_ANONYMOUS_AST",
        "prior_odds_derived_from_prefix_codelength_difference": True,
        "fixed_mixture_weight_supplied_by_target": False,
        "target_outcomes_accessed": False,
    }
    return {
        **payload,
        "calibration_id": hashlib.sha256(
            b"acfqp:source-support-automatic-dictionary-calibration:v131\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def synthesize_automatic_dictionary_factor_candidate_v131(
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    projection: Mapping[str, Any],
    *,
    support_label_count: int,
    factor_prior_enabled: bool,
    layout_domain: str,
    minimum_factor_assignment_count: int,
) -> tuple[PartialFactorCandidateV15, dict[str, int]]:
    if (
        not rows
        or not catalogue
        or support_label_count <= 0
        or type(factor_prior_enabled) is not bool
        or minimum_factor_assignment_count <= 0
    ):
        _fail("V131 automatic-dictionary candidate contract changed")
    layout = discover_generic_layout_v5(rows, catalogue, layout_domain=layout_domain)
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, layout, canonical_occurrence=0
    )
    grouped = atomic._grouped(aligned_rows)  # noqa: SLF001
    binding = atomic._derive_binding(grouped[0], aligned_catalogue)  # noqa: SLF001
    bindings = {0: binding}
    state_width = len(aligned_rows[0].pre)
    action_width = len(aligned_catalogue[0].fields)
    artifact = _artifact_expression_signatures(
        state_width, action_width, projection
    )
    calibration = derive_automatic_dictionary_calibration_v131(projection)
    signature_index = {
        row["signature_sha256"]: index
        for index, row in enumerate(projection["cross_schema_subprograms"])
    }
    assignments = []
    ambiguity = []
    total_evaluations = artifact_selected = 0
    relations = set(binding["relations"])
    constants = set(binding["constants"])
    for target in range(state_width):
        exact, evaluations = atomic._atomic_expression_candidates(  # noqa: SLF001
            target,
            grouped=grouped,
            bindings=bindings,
            state_width=state_width,
            action_field_width=action_width,
            relation_names=relations,
            constant_names=constants,
        )
        total_evaluations += evaluations
        candidates = []
        for depth, result_type, expression in exact:
            if result_type not in {"INT", "FINITE_INT_SUPPORT"}:
                continue
            encoded = canonical_json_bytes(expression)
            is_artifact = encoded in artifact
            state_dependencies, action_dependencies = _dependencies(expression)
            classification = {
                "state_dependencies": state_dependencies,
                "action_dependencies": action_dependencies,
                "next_dependencies": [],
                "constant_dependencies": [],
                "relation_dependencies": [],
            }
            generic_bits = _ast_bits(expression)
            signature = artifact.get(encoded)
            reference_bits = (
                calibration["artifact_library_index_prefix_bits"]
                + _dependency_binding_bits(classification)
                if signature in signature_index
                else None
            )
            mixture_bits = 1 + (
                reference_bits if reference_bits is not None else generic_bits
            )
            rank = (
                mixture_bits if factor_prior_enabled else generic_bits,
                depth,
                atomic._expression_mdl(expression, bindings),  # noqa: SLF001
                encoded,
            )
            candidates.append(
                (
                    rank,
                    result_type,
                    expression,
                    is_artifact,
                    encoded,
                    generic_bits,
                    reference_bits,
                    state_dependencies,
                    action_dependencies,
                )
            )
        if not candidates:
            continue
        artifact_count = sum(row[3] for row in candidates)
        selected = min(candidates)
        (
            _rank,
            result_type,
            expression,
            is_artifact,
            encoded,
            generic_bits,
            reference_bits,
            state_dependencies,
            action_dependencies,
        ) = selected
        signature = artifact.get(encoded, hashlib.sha256(encoded).hexdigest())
        assignments.append(
            {
                "target_column": target,
                "result_type": result_type,
                "expression": expression,
                "signature_sha256": signature,
                "state_dependencies": state_dependencies,
                "action_dependencies": action_dependencies,
            }
        )
        artifact_selected += int(is_artifact)
        ambiguity.append(
            {
                "target_column": target,
                "same_generic_hypothesis_pool_size": len(candidates),
                "artifact_expression_count_in_same_pool": artifact_count,
                "artifact_expression_present_in_pool": artifact_count > 0,
                "artifact_expression_selected": is_artifact,
                "generic_ast_prefix_bits": generic_bits,
                "artifact_reference_prefix_bits": reference_bits,
                "automatic_dictionary_branch_prefix_bits": 1,
                "selection_rule": (
                    "OPTIONAL_PREFIX_CODE_BITS_THEN_DEPTH_THEN_AST_MDL_THEN_BYTES"
                ),
            }
        )
    if len(assignments) < minimum_factor_assignment_count:
        _fail("V131 unified grammar did not identify enough partial assignments")
    payload = {
        "schema": "acfqp.automatic_dictionary_generic_partial_factor_candidate.v131",
        "source_factor_library_id": projection["source_factor_library_id"],
        "factor_prior_enabled": factor_prior_enabled,
        "only_arm_switch_is_normalized_factor_prior": True,
        "same_generic_atomic_hypothesis_pool": True,
        "support_label_count_at_issuance": support_label_count,
        "raw_transition_count_at_issuance": len(rows),
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "layout": layout.to_document(),
        "state_width": state_width,
        "action_field_width": action_width,
        "compiled_factor_assignments": assignments,
        "unknown_residual_target_columns": sorted(
            set(range(state_width)) - {row["target_column"] for row in assignments}
        ),
        "binding_ambiguity_inventory": ambiguity,
        "minimum_factor_assignment_count": minimum_factor_assignment_count,
        "artifact_expression_selected_count": artifact_selected,
        "automatic_dictionary_calibration": calibration,
        "fixed_two_to_library_cardinality_prior_multiplier_present": False,
        "normalized_artifact_uniform_mixture_prior_present": factor_prior_enabled,
        "target_slot_inventory_supplied_by_prior": False,
        "target_bindings_derived_from_raw_observations": True,
        "semantic_names_used": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    document = _identifier(
        domains.CONSTRUCTION_K7_AUTOMATIC_DICTIONARY_FACTOR_CANDIDATE_V131_DOMAIN,
        payload,
        "candidate_id",
    )
    return (
        PartialFactorCandidateV15(document, layout, tuple(assignments), aligned_rows),
        {
            "generic_atomic_expression_evaluations": total_evaluations,
            "artifact_expression_selected_count": artifact_selected,
        },
    )


def automatic_dictionary_factor_stop_update_v131(
    candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    *,
    factor_prior_enabled: bool,
    candidate_epoch: int,
    invalidated_candidate_count: int,
    post_issuance_exact_prediction_success_count: int,
    global_alpha_denominator: int,
) -> dict[str, Any]:
    """Apply the source-support-calibrated normalized structural mixture."""

    base = generic_artifact_factor_stop_update_v121(
        candidate,
        rows,
        catalogue,
        candidate_epoch=candidate_epoch,
        invalidated_candidate_count=invalidated_candidate_count,
        post_issuance_exact_prediction_success_count=(
            post_issuance_exact_prediction_success_count
        ),
        global_alpha_denominator=global_alpha_denominator,
    )
    numerator = denominator = 1
    selected_artifact = 0
    factors = []
    ambiguity = {
        row["target_column"]: row
        for row in candidate.public_document["binding_ambiguity_inventory"]
    }
    calibration = candidate.public_document["automatic_dictionary_calibration"]
    branch_bits = calibration["automatic_dictionary_branch_prefix_bits"]
    for assignment in candidate.assignments:
        row = ambiguity[assignment["target_column"]]
        pool = row["same_generic_hypothesis_pool_size"]
        artifact_count = row["artifact_expression_count_in_same_pool"]
        is_artifact = row["artifact_expression_selected"]
        generic_bits = row["generic_ast_prefix_bits"]
        reference_bits = row["artifact_reference_prefix_bits"]
        strict_bits = generic_bits
        if not factor_prior_enabled:
            prior_bits = strict_bits
        elif is_artifact and type(reference_bits) is int:
            prior_bits = branch_bits + reference_bits
            selected_artifact += 1
        else:
            prior_bits = branch_bits + generic_bits
        saving = strict_bits - prior_bits
        part_numerator = 2 ** max(0, saving)
        part_denominator = 2 ** max(0, -saving)
        numerator *= part_numerator
        denominator *= part_denominator
        divisor = gcd(numerator, denominator)
        numerator //= divisor
        denominator //= divisor
        factors.append(
            {
                "target_column": assignment["target_column"],
                "same_generic_hypothesis_pool_size": pool,
                "artifact_expression_count_in_same_pool": artifact_count,
                "artifact_expression_selected": is_artifact,
                "strict_generic_ast_prefix_bits": strict_bits,
                "automatic_dictionary_selected_prefix_bits": prior_bits,
                "prefix_codelength_saving_bits": saving,
                "prior_odds_numerator": part_numerator,
                "prior_odds_denominator": part_denominator,
            }
        )
    threshold_met = (
        base["universal_mixture_evalue_numerator"] * numerator
        >= base["universal_mixture_evalue_denominator"]
        * base["evalue_threshold"]
        * denominator
    )
    stopped = (
        base["current_partial_factor_replay"]["exact"] is True
        and threshold_met
        and base["raw_partial_outcome_prefix_code_bits"]
        >= base["total_partial_two_part_model_code_bits"]
    )
    return {
        **base,
        "schema": "acfqp.automatic_dictionary_factor_stop_update.v131",
        "factor_prior_enabled": factor_prior_enabled,
        "automatic_dictionary_component_weights": {
            "artifact_reference_branch_numerator": 1,
            "generic_ast_tail_branch_numerator": 1,
            "common_denominator": 2,
            "source_support_calibration_id": calibration["calibration_id"],
        },
        "per_assignment_normalized_prior_odds": factors,
        "combined_normalized_prior_odds_numerator": numerator,
        "combined_normalized_prior_odds_denominator": denominator,
        "selected_artifact_assignment_count": selected_artifact,
        "fixed_two_to_library_cardinality_prior_multiplier_present": False,
        "shared_base_evalue_threshold": base["evalue_threshold"],
        "universal_mixture_evalue_threshold_met": threshold_met,
        "same_stop_rule_function_in_both_arms": True,
        "only_arm_switch_is_normalized_factor_prior": True,
        "stopped": stopped,
    }


def acquire_matched_automatic_dictionary_factor_arms_v131(
    adapter: Any,
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    source_artifact_library = config.get("source_artifact_factor_library")
    if type(source_artifact_library) is not dict:
        _fail("V131 source artifact library is absent")
    verified = verify_automatic_minimal_factor_dictionary_v131(
        artifact_factor_library,
        source_artifact_library,
        source_campaign_bytes,
    )
    projection = artifact_factor_library.get("v15_partial_synthesizer_projection")
    if (
        verified["selected_template_count"] <= 0
        or verified["leave_one_source_campaign_reconstruction_verified"] is not True
        or type(projection) is not dict
    ):
        _fail("V131 artifact projection changed")
    states = {
        enabled: {
            "candidate": None,
            "issued": 0,
            "invalidated": 0,
            "disagreements": 0,
            "epoch": 0,
            "successes": 0,
            "previous": None,
            "history": [],
            "derivation_compute": 0,
            "selected_artifact": 0,
        }
        for enabled in (True, False)
    }
    results: dict[bool, dict[str, Any]] = {}
    rows: list[Any] = []
    batches: list[tuple[Any, ...]] = []
    accepting_label = None
    maximum = config["families"][adapter.family]["maximum_acquisition_labels"]
    for labels, batch in enumerate(
        fair_witness_blind_path_first_stream_v129r1(adapter), 1
    ):
        if labels > maximum:
            break
        rows.extend(batch)
        batches.append(batch)
        current = tuple(rows)
        if accepting_label is None and any(
            row.terminal_acceptance_after is True for row in batch
        ):
            accepting_label = labels
        for enabled in (True, False):
            if enabled in results:
                continue
            state = states[enabled]
            candidate = state["candidate"]
            if candidate is not None:
                replay = exact_generic_artifact_factor_replay_v121(
                    candidate, current, adapter.catalogue
                )
                if replay["exact"] is True:
                    state["successes"] += 1
                else:
                    state["previous"] = candidate.public_document["candidate_id"]
                    state["candidate"] = None
                    state["invalidated"] += 1
                    state["epoch"] += 1
                    state["successes"] = 0
            if state["candidate"] is None:
                try:
                    candidate, compute = synthesize_automatic_dictionary_factor_candidate_v131(
                        current,
                        adapter.catalogue,
                        projection,
                        support_label_count=labels,
                        factor_prior_enabled=enabled,
                        layout_domain=config["generic_domains"]["layout"],
                        minimum_factor_assignment_count=config[
                            "minimum_reusable_factor_count"
                        ],
                    )
                    state["candidate"] = candidate
                    state["issued"] = labels
                    state["derivation_compute"] += compute[
                        "generic_atomic_expression_evaluations"
                    ]
                    state["selected_artifact"] = compute[
                        "artifact_expression_selected_count"
                    ]
                    if (
                        state["previous"] is not None
                        and candidate.public_document["candidate_id"]
                        != state["previous"]
                    ):
                        state["disagreements"] += 1
                except Exception as error:
                    state["history"].append(
                        {
                            "support_label_count": labels,
                            "candidate_available": False,
                            "constructor_error_type": type(error).__name__,
                        }
                    )
                    continue
            candidate = state["candidate"]
            stop = automatic_dictionary_factor_stop_update_v131(
                candidate,
                current,
                adapter.catalogue,
                factor_prior_enabled=enabled,
                candidate_epoch=state["epoch"],
                invalidated_candidate_count=state["invalidated"],
                post_issuance_exact_prediction_success_count=state["successes"],
                global_alpha_denominator=config["global_alpha_denominator"],
            )
            state["history"].append(
                {
                    "support_label_count": labels,
                    "candidate_available": True,
                    "candidate_id": candidate.public_document["candidate_id"],
                    "stopped_by_shared_rule": stop["stopped"],
                    "accepting_projection_available": accepting_label is not None,
                }
            )
            if stop["stopped"] is not True or accepting_label is None:
                continue
            prefix = tuple(row for selected in batches[:labels] for row in selected)
            payload = {
                "schema": "acfqp.automatic_dictionary_factor_acquisition_arm.v131",
                "family": adapter.family,
                "seed": adapter.seed,
                "arm": "NORMALIZED_FACTOR_PRIOR_ON" if enabled else "STRICT_NO_PRIOR",
                "factor_prior_enabled": enabled,
                "fair_witness_blind_path_first_backtracking": True,
                "generation_witness_accessed": False,
                "reachable_frontier_exhaustion_used_as_stopping_input": False,
                "only_arm_switch_is_normalized_factor_prior": True,
                "same_generic_atomic_hypothesis_pool": True,
                "same_candidate_carrier_and_schema": True,
                "same_candidate_replay_function": True,
                "same_stopping_rule_function": True,
                "ground_support_labels": labels,
                "raw_transition_count": len(prefix),
                "raw_transition_sha256": hashlib.sha256(
                    canonical_json_bytes([row.to_document() for row in prefix])
                ).hexdigest(),
                "candidate": dict(candidate.public_document),
                "candidate_issued_at_support_label": state["issued"],
                "invalidated_candidate_count": state["invalidated"],
                "candidate_program_disagreement_count": state["disagreements"],
                "candidate_epoch": state["epoch"],
                "post_issuance_exact_prediction_success_count": state["successes"],
                "first_accepting_observation_label": accepting_label,
                "terminal_stop_update": dict(stop),
                "stopping_history": list(state["history"]),
                "derivation_compute_events": state["derivation_compute"],
                "artifact_expression_selected_count": state["selected_artifact"],
                "sample_labels_and_derivation_compute_separate": True,
                "complete_world_model_claimed": False,
                "planning_authority_present": False,
            }
            document = {
                **payload,
                "acquisition_id": domains.extension_content_id_v131(
                    domains.CONSTRUCTION_K7_AUTOMATIC_DICTIONARY_FACTOR_ACQUISITION_ARM_V131_DOMAIN,
                    payload,
                ),
            }
            results[enabled] = {
                "document": document,
                "candidate": candidate,
                "rows": prefix,
                "batches": tuple(batches[:labels]),
            }
        if len(results) == 2:
            prior, strict = results[True], results[False]
            common = min(len(prior["batches"]), len(strict["batches"]))
            if tuple(
                row for batch in prior["batches"][:common] for row in batch
            ) != tuple(
                row for batch in strict["batches"][:common] for row in batch
            ):
                _fail("V131 matched arms diverged before their common stop")
            return {
                "NORMALIZED_FACTOR_PRIOR_ON": prior,
                "STRICT_NO_PRIOR": strict,
            }
    _fail(
        f"V131 automatic-dictionary acquisition did not close before cap for "
        f"{adapter.family} seed {adapter.seed}"
    )


__all__ = (
    "acquire_matched_automatic_dictionary_factor_arms_v131",
    "derive_automatic_dictionary_calibration_v131",
    "automatic_dictionary_factor_stop_update_v131",
    "synthesize_automatic_dictionary_factor_candidate_v131",
)
