"""Producer-free reconstruction of normalized prefix-code prior V131R2."""

from __future__ import annotations

import copy
import hashlib
from math import ceil, gcd, log2
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_normalized_mixture_factor_prior_independent_verifier_v130 as predecessor
from acfqp import construction_k7_fair_unified_factor_prior_ablation_independent_verifier_v129r1 as path_predecessor
from acfqp import construction_k7_generic_quotient_compiler_independent_verifier_v123r1 as generic
from acfqp import construction_k7_standalone_generic_model_independent_verifier_v125 as model
from acfqp import generic_atomic_expression_world_model_v4 as atomic
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    _dependencies,
    _symbols,
    exact_generic_artifact_factor_replay_v121,
    generic_artifact_factor_stop_update_v121,
    instantiate_normalized_subprograms_v121,
)
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    _ast_bits,
    _dependency_binding_bits,
    _unsigned_gamma_bits,
    _utf8_bits,
)
from acfqp.generic_dual_budget_adapter_v119 import (
    FAMILY as DUAL,
    build_dual_budget_adapter_v119,
)
from acfqp.generic_inventory_assembly_adapter_v118 import (
    FAMILY as INVENTORY,
    build_inventory_assembly_adapter_v118,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
)
from acfqp.generic_modular_routing_adapter_v128 import (
    FAMILY as MODULAR,
    build_modular_routing_adapter_v128,
    modular_routing_config_v128,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "8ffa5d72a77d95c9f72e1a9e5b3c9d9e9d823648d219795a557756281bdb55ff"
CAMPAIGN_BYTE_COUNT = 14_522_210
CAMPAIGN_SHA256 = "f1a96f03cfc6982b93d1b55b841ff166826f3d8193d34df6a1c4ec885ca36f54"
PREREGISTRATION_ID = "2ded6e06afbe8653a3486a51c32707ef457d3791baec34e48e32d3553b03d0cf"
V130_CAMPAIGN_ID = predecessor.CAMPAIGN_ID
V130_VERIFICATION_ID = predecessor.VERIFICATION_ID
V131_PREREGISTRATION_ID = "0926a56551766fce74d9a2c026f49072957b1408dff5eebbd072a2f03f95f91c"
V131_PREREGISTRATION_BYTE_COUNT = 61_704
V131_PREREGISTRATION_SHA256 = "0221c0866684a2c55c0ae527664e2d4f551a0207ef08f499871853fdb429b9bb"
V131R1_PREREGISTRATION_ID = "334e4235c604aab1e5d1122cf5daf4d3a69ddef60ce579901ffaf4a272051011"
V131R1_PREREGISTRATION_BYTE_COUNT = 62_158
V131R1_PREREGISTRATION_SHA256 = "f78a4e5c56130d96e24654f3af52d7ca1c2023e514562cc99e73622912e18d4d"
V131R1_FAILED_CAMPAIGN_ID = "ac9f7f2f72d446c768aa0e234f8feb3c7b2514c7092c5ff9d76b4a44171e8e75"
V131R1_FAILED_CAMPAIGN_BYTE_COUNT = 15_999_026
V131R1_FAILED_CAMPAIGN_SHA256 = "bc4fb2adbb0b7e95d4b02ebd8ecd783f5ff962891424b01a8174252f0c82781b"
EXPECTED_OCCURRENCES = (
    (INVENTORY, 1_047_121),
    (INVENTORY, 1_047_122),
    (DUAL, 1_047_123),
    (DUAL, 1_047_124),
    (MODULAR, 1_047_125),
    (MODULAR, 1_047_126),
)
EXPECTED_EPISODES = (356, 357, 358)
VERIFICATION_ID = "0" * 64
EXPECTED_CANONICAL_BYTE_COUNT = 0
EXPECTED_CANONICAL_SHA256 = "0" * 64


_DOMAINS = {
    "dictionary": "acfqp:construction-k7-robust-dictionary-factor-prior-dictionary:v131r2",
    "campaign": "acfqp:construction-k7-robust-dictionary-factor-prior-campaign:v131r2",
    "occurrence": "acfqp:construction-k7-robust-dictionary-factor-prior-occurrence:v131r2",
    "candidate": "acfqp:construction-k7-robust-dictionary-factor-prior-candidate:v131r2",
    "acquisition": "acfqp:construction-k7-robust-dictionary-factor-prior-acquisition-arm:v131r2",
    "sequence": "acfqp:construction-k7-standalone-generic-owned-sequence:v126",
    "verification": "acfqp:construction-k7-robust-dictionary-factor-prior-verification:v131r2",
    "plan": "acfqp:generic-legality-conditioned-quotient-plan:v106",
    "ood": "acfqp:incompatible-schema-no-transfer-control:v99",
    "calibration": "acfqp:source-support-robust-dictionary-calibration:v131r2",
}
_BUILDERS = {
    INVENTORY: build_inventory_assembly_adapter_v118,
    DUAL: build_dual_budget_adapter_v119,
    MODULAR: build_modular_routing_adapter_v128,
}
_PREDECESSOR_NAMES = (
    "v130_campaign",
    "v130_verification",
    "v131_preregistration",
    "v131r1_preregistration",
    "failed_v131r1",
    *predecessor._PREDECESSOR_NAMES,  # noqa: SLF001
)


class ConstructionK7RobustDictionaryFactorPriorIndependentVerifierV131R2Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RobustDictionaryFactorPriorIndependentVerifierV131R2Error(
        message
    )


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V131R2 {key} changed")


def _config() -> dict[str, Any]:
    config = copy.deepcopy(modular_routing_config_v128())
    for family in _BUILDERS:
        config["families"][family]["maximum_acquisition_labels"] = 320
    return config


def _calibration(projection: Mapping[str, Any]) -> dict[str, Any]:
    templates = projection["cross_schema_subprograms"]
    pairs = {
        tuple(pair)
        for template in templates
        for pair in template["source_schema_pairs"]
    }
    observed = sum(len(template["source_schema_pairs"]) for template in templates)
    possible = len(templates) * len(pairs)
    payload = {
        "schema": "acfqp.source_support_robust_dictionary_calibration.v131r2",
        "source_factor_library_id": projection["source_factor_library_id"],
        "artifact_template_count": len(templates),
        "distinct_source_schema_pair_count": len(pairs),
        "observed_template_schema_support_cell_count": observed,
        "possible_template_schema_support_cell_count": possible,
        "robust_dictionary_branch_prefix_bits": 1,
        "artifact_library_index_prefix_bits": max(
            1, ceil(log2(max(2, len(templates))))
        ),
        "artifact_branch_code": "LIBRARY_INDEX_PLUS_ANONYMOUS_DEPENDENCY_BINDING",
        "uniform_tail_branch_code": "FULL_TYPED_ANONYMOUS_AST",
        "prior_odds_derived_from_prefix_codelength_difference": True,
        "fixed_mixture_weight_supplied_by_target": False,
        "target_outcomes_accessed": False,
    }
    return {
        **payload,
        "calibration_id": _content_id(_DOMAINS["calibration"], payload),
    }


def _symbol_binding_bits_v131r2(expression: Any) -> int:
    symbols = _symbols(expression)
    return _unsigned_gamma_bits(len(symbols)) + sum(
        1 + _unsigned_gamma_bits(index) for _kind, index in symbols
    )


def _robust_dictionary(source_library: Mapping[str, Any]) -> dict[str, Any]:
    templates = {
        row["signature_sha256"]: row
        for row in source_library["derived_subprograms"]
    }
    origins = {
        row["signature_sha256"]: row
        for row in source_library["derivation_origins"]
    }
    aliases = ("V117", "V118", "V119")
    _require(
        set(templates) == set(origins) and len(templates) > 0,
        "V131r2 source template inventory changed",
    )
    selected_signatures = []
    holdout_rows = []
    for signature in sorted(templates):
        template = templates[signature]
        generic_bits = 1 + _ast_bits(template["normalized_expression"])
        description_bits = (
            _unsigned_gamma_bits(1)
            + _utf8_bits(template["result_type"])
            + _ast_bits(template["normalized_expression"])
        )
        reference_bits = (
            1 + 1 + _symbol_binding_bits_v131r2(template["normalized_expression"])
        )
        reconstructions = []
        for holdout in aliases:
            retained = [
                row
                for row in origins[signature]["origins"]
                if row["source_campaign_alias"] != holdout
            ]
            retained_aliases = sorted(
                {row["source_campaign_alias"] for row in retained}
            )
            retained_pairs = sorted(
                {tuple(row["source_schema_pair"]) for row in retained}
            )
            generic_total = len(retained) * generic_bits
            dictionary_total = description_bits + len(retained) * reference_bits
            gain = generic_total - dictionary_total
            reconstructions.append(
                {
                    "held_out_source_campaign_alias": holdout,
                    "retained_supporting_source_campaign_aliases": retained_aliases,
                    "retained_distinct_schema_pairs": [
                        list(pair) for pair in retained_pairs
                    ],
                    "retained_origin_count": len(retained),
                    "generic_ast_source_prefix_bits": generic_total,
                    "singleton_dictionary_source_prefix_bits": dictionary_total,
                    "singleton_dictionary_prefix_gain_bits": gain,
                    "eligible_without_held_out_source": (
                        len(retained_aliases) >= 2
                        and len(retained_pairs) >= 2
                        and gain > 0
                    ),
                }
            )
        eligible = all(
            row["eligible_without_held_out_source"] for row in reconstructions
        )
        if eligible:
            selected_signatures.append(signature)
        holdout_rows.append(
            {
                "signature_sha256": signature,
                "leave_one_source_reconstructions": reconstructions,
                "minimum_leave_one_source_prefix_gain_bits": min(
                    row["singleton_dictionary_prefix_gain_bits"]
                    for row in reconstructions
                ),
                "eligible_for_dictionary_search": eligible,
            }
        )
    selected = [templates[signature] for signature in selected_signatures]
    _require(bool(selected), "V131r2 robust dictionary became empty")
    payload = {
        "schema": "acfqp.robust_automatic_factor_dictionary.v131r2",
        "source_artifact_factor_library_id": source_library["factor_library_id"],
        "source_candidate_document_count": source_library["candidate_document_count"],
        "source_template_pool_count": len(templates),
        "selected_template_count": len(selected),
        "selected_subprograms": selected,
        "leave_one_source_campaign_reconstruction": holdout_rows,
        "selection_rule": (
            "SELECT_EXACTLY_EACH_TEMPLATE_WITH_POSITIVE_SINGLETON_PREFIX_GAIN_"
            "UNDER_EVERY_LEAVE_ONE_SOURCE_RECONSTRUCTION"
        ),
        "selection_rule_applied_independently_per_anonymous_template": True,
        "minimum_selected_template_leave_one_source_gain_bits": min(
            row["minimum_leave_one_source_prefix_gain_bits"]
            for row in holdout_rows
            if row["eligible_for_dictionary_search"]
        ),
        "target_occurrences_accessed": False,
        "target_outcomes_accessed": False,
        "failed_v131r1_target_outcome_used_for_selection": False,
        "fixed_template_cardinality_supplied": False,
        "fixed_template_slot_inventory_supplied": False,
        "semantic_family_names_used_for_selection": False,
        "complete_world_model_claimed": False,
    }
    dictionary_id = _content_id(_DOMAINS["dictionary"], payload)
    return {
        **payload,
        "dictionary_id": dictionary_id,
        "v15_partial_synthesizer_projection": {
            "schema": "acfqp.cross_schema_factor_template_projection.v15",
            "source_factor_library_id": dictionary_id,
            "cross_schema_subprograms": selected,
            "target_slot_inventory_supplied": False,
            "semantic_names_supplied": False,
        },
    }


def _artifact_expressions(
    state_width: int,
    action_width: int,
    projection: Mapping[str, Any],
) -> dict[bytes, str]:
    result = {}
    for target in range(state_width):
        for row in instantiate_normalized_subprograms_v121(
            target, state_width, action_width, projection
        ):
            result[canonical_json_bytes(row["expression"])] = row["signature_sha256"]
    return result


def _synthesize(
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    projection: Mapping[str, Any],
    *,
    labels: int,
    enabled: bool,
    config: Mapping[str, Any],
) -> tuple[PartialFactorCandidateV15, dict[str, int]]:
    layout = discover_generic_layout_v5(
        rows, catalogue, layout_domain=config["generic_domains"]["layout"]
    )
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, layout, canonical_occurrence=0
    )
    grouped = atomic._grouped(aligned_rows)  # noqa: SLF001
    binding = atomic._derive_binding(grouped[0], aligned_catalogue)  # noqa: SLF001
    bindings = {0: binding}
    state_width = len(aligned_rows[0].pre)
    action_width = len(aligned_catalogue[0].fields)
    artifact = _artifact_expressions(state_width, action_width, projection)
    calibration = _calibration(projection)
    signature_index = {
        row["signature_sha256"]: index
        for index, row in enumerate(projection["cross_schema_subprograms"])
    }
    assignments = []
    ambiguity = []
    evaluations = selected_count = 0
    for target in range(state_width):
        exact, count = atomic._atomic_expression_candidates(  # noqa: SLF001
            target,
            grouped=grouped,
            bindings=bindings,
            state_width=state_width,
            action_field_width=action_width,
            relation_names=set(binding["relations"]),
            constant_names=set(binding["constants"]),
        )
        evaluations += count
        candidates = []
        for depth, result_type, expression in exact:
            if result_type not in {"INT", "FINITE_INT_SUPPORT"}:
                continue
            encoded = canonical_json_bytes(expression)
            signature = artifact.get(encoded)
            is_artifact = signature in signature_index
            state_dependencies, action_dependencies = _dependencies(expression)
            classification = {
                "state_dependencies": state_dependencies,
                "action_dependencies": action_dependencies,
                "next_dependencies": [],
                "constant_dependencies": [],
                "relation_dependencies": [],
            }
            generic_bits = _ast_bits(expression)
            reference_bits = (
                calibration["artifact_library_index_prefix_bits"]
                + _dependency_binding_bits(classification)
                if is_artifact
                else None
            )
            mixture_bits = 1 + (
                reference_bits if reference_bits is not None else generic_bits
            )
            rank = (
                mixture_bits if enabled else generic_bits,
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
        ) = min(candidates)
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
        selected_count += int(is_artifact)
        ambiguity.append(
            {
                "target_column": target,
                "same_generic_hypothesis_pool_size": len(candidates),
                "artifact_expression_count_in_same_pool": artifact_count,
                "artifact_expression_present_in_pool": artifact_count > 0,
                "artifact_expression_selected": is_artifact,
                "generic_ast_prefix_bits": generic_bits,
                "artifact_reference_prefix_bits": reference_bits,
                "robust_dictionary_branch_prefix_bits": 1,
                "selection_rule": (
                    "OPTIONAL_PREFIX_CODE_BITS_THEN_DEPTH_THEN_AST_MDL_THEN_BYTES"
                ),
            }
        )
    _require(
        len(assignments) >= config["minimum_reusable_factor_count"],
        "V131R2 independent candidate lacks assignments",
    )
    payload = {
        "schema": "acfqp.robust_dictionary_generic_partial_factor_candidate.v131r2",
        "source_factor_library_id": projection["source_factor_library_id"],
        "factor_prior_enabled": enabled,
        "only_arm_switch_is_normalized_factor_prior": True,
        "same_generic_atomic_hypothesis_pool": True,
        "support_label_count_at_issuance": labels,
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
        "minimum_factor_assignment_count": config["minimum_reusable_factor_count"],
        "artifact_expression_selected_count": selected_count,
        "robust_dictionary_calibration": calibration,
        "fixed_two_to_library_cardinality_prior_multiplier_present": False,
        "normalized_artifact_uniform_mixture_prior_present": enabled,
        "target_slot_inventory_supplied_by_prior": False,
        "target_bindings_derived_from_raw_observations": True,
        "semantic_names_used": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    document = {
        **payload,
        "candidate_id": _content_id(_DOMAINS["candidate"], payload),
    }
    return (
        PartialFactorCandidateV15(document, layout, tuple(assignments), aligned_rows),
        {
            "generic_atomic_expression_evaluations": evaluations,
            "artifact_expression_selected_count": selected_count,
        },
    )


def _stop(
    candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    *,
    enabled: bool,
    epoch: int,
    invalidated: int,
    successes: int,
    alpha: int,
) -> dict[str, Any]:
    base = generic_artifact_factor_stop_update_v121(
        candidate,
        rows,
        catalogue,
        candidate_epoch=epoch,
        invalidated_candidate_count=invalidated,
        post_issuance_exact_prediction_success_count=successes,
        global_alpha_denominator=alpha,
    )
    calibration = candidate.public_document["robust_dictionary_calibration"]
    branch_bits = calibration["robust_dictionary_branch_prefix_bits"]
    ambiguity = {
        row["target_column"]: row
        for row in candidate.public_document["binding_ambiguity_inventory"]
    }
    numerator = denominator = 1
    selected = 0
    factors = []
    for assignment in candidate.assignments:
        row = ambiguity[assignment["target_column"]]
        generic_bits = row["generic_ast_prefix_bits"]
        reference_bits = row["artifact_reference_prefix_bits"]
        is_artifact = row["artifact_expression_selected"]
        if not enabled:
            prior_bits = generic_bits
        elif is_artifact and type(reference_bits) is int:
            prior_bits = branch_bits + reference_bits
            selected += 1
        else:
            prior_bits = branch_bits + generic_bits
        saving = generic_bits - prior_bits
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
                "same_generic_hypothesis_pool_size": row[
                    "same_generic_hypothesis_pool_size"
                ],
                "artifact_expression_count_in_same_pool": row[
                    "artifact_expression_count_in_same_pool"
                ],
                "artifact_expression_selected": is_artifact,
                "strict_generic_ast_prefix_bits": generic_bits,
                "robust_dictionary_selected_prefix_bits": prior_bits,
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
        "schema": "acfqp.robust_dictionary_factor_stop_update.v131r2",
        "factor_prior_enabled": enabled,
        "robust_dictionary_component_weights": {
            "artifact_reference_branch_numerator": 1,
            "generic_ast_tail_branch_numerator": 1,
            "common_denominator": 2,
            "source_support_calibration_id": calibration["calibration_id"],
        },
        "per_assignment_normalized_prior_odds": factors,
        "combined_normalized_prior_odds_numerator": numerator,
        "combined_normalized_prior_odds_denominator": denominator,
        "selected_artifact_assignment_count": selected,
        "fixed_two_to_library_cardinality_prior_multiplier_present": False,
        "shared_base_evalue_threshold": base["evalue_threshold"],
        "universal_mixture_evalue_threshold_met": threshold_met,
        "same_stop_rule_function_in_both_arms": True,
        "only_arm_switch_is_normalized_factor_prior": True,
        "stopped": stopped,
    }


def _rebuild_acquisition(
    recorded: Mapping[str, Any],
    adapter: Any,
    projection: Mapping[str, Any],
    batches: tuple[tuple[Any, ...], ...],
    *,
    enabled: bool,
    config: Mapping[str, Any],
) -> tuple[PartialFactorCandidateV15, tuple[Any, ...]]:
    target = recorded["ground_support_labels"]
    candidate = None
    issued = invalidated = disagreements = epoch = successes = 0
    previous = None
    history = []
    derivation_compute = selected_artifact = 0
    rows = []
    accepting_label = None
    terminal_stop = None
    for labels, batch in enumerate(batches[:target], 1):
        rows.extend(batch)
        current = tuple(rows)
        if accepting_label is None and any(
            row.terminal_acceptance_after is True for row in batch
        ):
            accepting_label = labels
        if candidate is not None:
            replay = exact_generic_artifact_factor_replay_v121(
                candidate, current, adapter.catalogue
            )
            if replay["exact"] is True:
                successes += 1
            else:
                previous = candidate.public_document["candidate_id"]
                candidate = None
                invalidated += 1
                epoch += 1
                successes = 0
        if candidate is None:
            try:
                candidate, compute = _synthesize(
                    current,
                    adapter.catalogue,
                    projection,
                    labels=labels,
                    enabled=enabled,
                    config=config,
                )
                issued = labels
                derivation_compute += compute[
                    "generic_atomic_expression_evaluations"
                ]
                selected_artifact = compute["artifact_expression_selected_count"]
                if (
                    previous is not None
                    and candidate.public_document["candidate_id"] != previous
                ):
                    disagreements += 1
            except Exception as error:
                history.append(
                    {
                        "support_label_count": labels,
                        "candidate_available": False,
                        "constructor_error_type": type(error).__name__,
                    }
                )
                continue
        stop = _stop(
            candidate,
            current,
            adapter.catalogue,
            enabled=enabled,
            epoch=epoch,
            invalidated=invalidated,
            successes=successes,
            alpha=config["global_alpha_denominator"],
        )
        history.append(
            {
                "support_label_count": labels,
                "candidate_available": True,
                "candidate_id": candidate.public_document["candidate_id"],
                "stopped_by_shared_rule": stop["stopped"],
                "accepting_projection_available": accepting_label is not None,
            }
        )
        if labels == target:
            terminal_stop = stop
    _require(
        candidate is not None
        and terminal_stop is not None
        and terminal_stop["stopped"] is True
        and accepting_label is not None,
        "V131R2 acquisition did not independently stop",
    )
    raw_rows = tuple(rows)
    payload = {
        "schema": "acfqp.robust_dictionary_factor_acquisition_arm.v131r2",
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
        "ground_support_labels": target,
        "raw_transition_count": len(raw_rows),
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in raw_rows])
        ).hexdigest(),
        "candidate": dict(candidate.public_document),
        "candidate_issued_at_support_label": issued,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": disagreements,
        "candidate_epoch": epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "first_accepting_observation_label": accepting_label,
        "terminal_stop_update": dict(terminal_stop),
        "stopping_history": history,
        "derivation_compute_events": derivation_compute,
        "artifact_expression_selected_count": selected_artifact,
        "sample_labels_and_derivation_compute_separate": True,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    rebuilt = {
        **payload,
        "acquisition_id": _content_id(_DOMAINS["acquisition"], payload),
    }
    _require(rebuilt == recorded, "V131R2 acquisition reconstruction changed")
    return candidate, raw_rows


def _verify_sequence(
    sequence: Mapping[str, Any],
    candidate: Mapping[str, Any],
    acquisition_rows: tuple[Any, ...],
    *,
    family: str,
    seed: int,
) -> dict[str, int]:
    _verify_id(sequence, "sequence_id", _DOMAINS["sequence"])
    _require(
        sequence["schema"] == "acfqp.standalone_generic_owned_sequence.v126"
        and sequence["partial_candidate_id"] == candidate["candidate_id"]
        and sequence["family"] == family
        and sequence["seed"] == seed
        and tuple(sequence["episode_indices"]) == EXPECTED_EPISODES,
        "V131R2 owned sequence identity changed",
    )
    dependency = sequence["program_branch_dependency_receipt"]
    _require(
        sequence["program_branch_dependency_receipt_id"]
        == dependency["dependency_receipt_id"]
        and dependency["partial_candidate_id"] == candidate["candidate_id"]
        and dependency["compiled_factor_assignments"]
        == candidate["compiled_factor_assignments"],
        "V131R2 dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in dependency["canonical_action_catalogue"]
    }
    persistent = sequence["persistent_exact_overlay_rows"]
    _require(
        hashlib.sha256(canonical_json_bytes(persistent)).hexdigest()
        == sequence["persistent_exact_overlay_sha256"],
        "V131R2 persistent evidence hash changed",
    )
    acquisition_documents = [row.to_document() for row in acquisition_rows]
    acquisition_unique = {
        model._raw_key(raw): raw for raw in acquisition_documents  # noqa: SLF001
    }
    initial_documents = tuple(
        acquisition_unique[key] for key in sorted(acquisition_unique)
    )
    current = {
        model._raw_key(raw): raw for raw in initial_documents  # noqa: SLF001
    }
    initial_rows = tuple(current.values())
    facts = model._project(initial_rows, candidate, actions)  # noqa: SLF001
    _require(
        facts["model"] == sequence["quotient_models_before_each_episode"][0]
        and model._bootstrap_receipt(initial_rows, facts)  # noqa: SLF001
        == sequence["bootstrap_receipt"]
        and model._match_receipt(facts, initial_rows, None)  # noqa: SLF001
        == sequence["bootstrap_full_rebuild_match"],
        "V131R2 bootstrap reconstruction changed",
    )
    updates = sequence["standalone_model_update_receipts"]
    matches = sequence["standalone_full_rebuild_match_receipts"]
    _require(
        len(sequence["episodes"])
        == len(updates)
        == len(matches)
        == len(EXPECTED_EPISODES),
        "V131R2 episode/receipt cardinality changed",
    )
    rebuilt_models = []
    path_checks = direct = reused = 0
    all_plans = []
    for index, episode in enumerate(sequence["episodes"]):
        before = model._project(tuple(current.values()), candidate, actions)  # noqa: SLF001
        _require(
            before["model"] == sequence["quotient_models_before_each_episode"][index]
            and episode["quotient_graph_before_episode"] == before["model"]
            and episode["standalone_model_state_id_before_episode"]
            == before["state_id"]
            and updates[index]["previous_successor_state_id"] == before["state_id"],
            "V131R2 before-model reconstruction changed",
        )
        rebuilt_models.append(before["model"])
        for wrapper in episode["abstract_plan_receipts"]:
            plan = wrapper["abstract_plan"]
            all_plans.append(plan)
            source = plan["planning_source"]
            if source in {
                "OBSERVATION_QUOTIENT_GRAPH",
                "COMPILED_FACTOR_PROGRAM_FALLBACK",
            }:
                _verify_id(
                    plan, "legality_conditioned_quotient_plan_id", _DOMAINS["plan"]
                )
                _require(
                    tuple(
                        plan["embedded_projected_plan"]["terminal_projection_rule"]
                    )
                    == before["rules"],
                    "V131R2 terminal projection rule changed",
                )
                path_checks += generic._verify_plan(  # noqa: SLF001
                    plan,
                    wrapper["raw_state"],
                    candidate,
                    actions,
                    before["model"],
                    before["rules"],
                )
                if source == "COMPILED_FACTOR_PROGRAM_FALLBACK":
                    direct += 1
                    _require(
                        plan["generic_factor_program_execution_adapter_used"] is True
                        and plan[
                            "legacy_shape_specific_planner_execution_adapter_called"
                        ]
                        is False,
                        "V131R2 direct generic plan changed",
                    )
            elif source in {
                "COMPILED_FACTOR_PROGRAM_MEMOIZED",
                "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
            }:
                reused += 1
                if source == "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER":
                    _require(
                        plan["cached_ordering_used_as_safety_authority"] is False
                        and plan["dependency_revalidation"][
                            "current_quotient_graph_id"
                        ]
                        == before["model"]["quotient_graph_id"],
                        "V131R2 dependency reuse changed",
                    )
            else:
                _fail("V131R2 unknown planning source")
        delta_rows = tuple(episode["raw_incremental_transition_rows"])
        novel_rows = tuple(
            raw for raw in delta_rows if model._raw_key(raw) not in current  # noqa: SLF001
        )
        novel = (
            model._project(novel_rows, candidate, actions)  # noqa: SLF001
            if novel_rows
            else {"raw_keys": frozenset(), "checks": 0}
        )
        for raw in delta_rows:
            current[model._raw_key(raw)] = raw  # noqa: SLF001
        after = model._project(tuple(current.values()), candidate, actions)  # noqa: SLF001
        expected_update = model._update_receipt(  # noqa: SLF001
            before, after, delta_rows, novel
        )
        expected_match = model._match_receipt(  # noqa: SLF001
            after, tuple(current.values()), expected_update
        )
        _require(
            expected_update == updates[index]
            and expected_match == matches[index]
            and episode["standalone_model_update_after_episode"] == expected_update
            and episode["standalone_full_rebuild_match_after_episode"]
            == expected_match
            and episode["quotient_graph_after_episode"] == after["model"]
            and episode["standalone_model_state_id_after_episode"]
            == after["state_id"]
            and after["model"] == sequence["quotient_models_after_each_episode"][index],
            "V131R2 update/full-match reconstruction changed",
        )
        rebuilt_models.append(after["model"])
        _require(
            episode["success"] is True
            and episode[
                "all_incremental_ground_queries_followed_failed_certificates"
            ]
            is True
            and episode["planner_raw_transition_argument_present"] is False,
            "V131R2 certificate discipline changed",
        )
    _require(
        [current[key] for key in sorted(current)] == list(persistent),
        "V131R2 persistent inventory changed",
    )
    actual_compute = sum(
        episode["abstract_planning_compute_events"] for episode in sequence["episodes"]
    )
    uncached_compute = sum(
        plan.get("embedded_projected_plan", {}).get(
            "matched_uncached_projected_planning_compute_events",
            plan["abstract_support_branch_evaluations"],
        )
        for plan in all_plans
    )
    dependency_compute = len(EXPECTED_EPISODES) * (
        len(dependency["compiled_factor_assignments"])
        + len(dependency["canonical_action_catalogue"])
    )
    _require(
        sequence["dependency_receipt_rederivation_count"] == len(EXPECTED_EPISODES)
        and sequence["dependency_derivation_compute_events"] == dependency_compute
        and sequence["actual_new_abstract_planning_compute_events"] == actual_compute
        and sequence["matched_uncached_abstract_planning_compute_events"]
        == uncached_compute
        and sequence["planning_compute_events_avoided_against_uncached"]
        == uncached_compute - actual_compute
        and sequence["direct_generic_factor_program_plan_count"] == direct
        and sequence["owned_episode_loop_implementation_present"] is True
        and sequence["standalone_v125_state_carrier_verified"] is True
        and sequence["retained_v113_state_carrier_present"] is False
        and sequence["retained_v113_sequence_orchestration_present"] is False
        and sequence["retained_v119_sequence_orchestration_present"] is False
        and sequence[
            "compiled_model_cache_or_receipt_used_as_safety_authority"
        ]
        is False,
        "V131R2 sequence accounting/claim boundary changed",
    )
    return {
        "model_epoch_count": len(rebuilt_models),
        "receipt_count": 2 + 2 * len(sequence["episodes"]),
        "plan_path_support_checks": path_checks,
        "reused_plan_count": reused,
        "direct_plan_count": direct,
    }


def _verify_occurrence(
    row: Mapping[str, Any], projection: Mapping[str, Any]
) -> dict[str, Any]:
    family = row["target_family"]
    seed = row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row["schema"] == "acfqp.robust_dictionary_factor_prior_occurrence.v131r2"
        and tuple(row["episode_indices"]) == EXPECTED_EPISODES,
        "V131R2 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", _DOMAINS["occurrence"])
    config = _config()
    adapter = _BUILDERS[family](seed, config)
    strict_labels = row["strict_no_prior_acquisition"]["ground_support_labels"]
    stream = path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(strict_labels))
    prior_candidate, prior_rows = _rebuild_acquisition(
        row["normalized_factor_prior_acquisition"],
        adapter,
        projection,
        batches,
        enabled=True,
        config=config,
    )
    strict_candidate, strict_rows = _rebuild_acquisition(
        row["strict_no_prior_acquisition"],
        adapter,
        projection,
        batches,
        enabled=False,
        config=config,
    )
    prior_sequence = _verify_sequence(
        row["normalized_factor_prior_owned_sequence"],
        prior_candidate.public_document,
        prior_rows,
        family=family,
        seed=seed,
    )
    strict_sequence = _verify_sequence(
        row["strict_no_prior_owned_sequence"],
        strict_candidate.public_document,
        strict_rows,
        family=family,
        seed=seed,
    )
    prior_doc = row["normalized_factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    sample_tax = {
        "normalized_factor_prior_ground_support_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_ground_support_labels": strict_doc["ground_support_labels"],
        "ground_support_labels_avoided_by_normalized_factor_prior": reduction,
        "same_fair_witness_blind_path_first_backtracking_policy": True,
        "same_raw_transition_prefix_through_common_label": prior_rows
        == strict_rows[: len(prior_rows)],
        "same_generic_atomic_hypothesis_pool": True,
        "same_candidate_carrier_and_schema": True,
        "same_candidate_replay_function": True,
        "same_stopping_rule_function": True,
        "only_arm_switch_is_normalized_factor_prior": True,
        "fixed_two_to_library_cardinality_prior_multiplier_present": False,
        "robust_dictionary_selected_from_source_candidate_artifacts": True,
        "fixed_template_cardinality_supplied": False,
        "sample_labels_and_derivation_compute_separate": True,
    }
    _require(row["sample_tax_comparison"] == sample_tax, "V131R2 sample tax changed")
    prior_owned = row["normalized_factor_prior_owned_sequence"]
    strict_owned = row["strict_no_prior_owned_sequence"]
    accounting = {
        "normalized_factor_prior_acquisition_labels": prior_doc[
            "ground_support_labels"
        ],
        "strict_no_prior_acquisition_labels": strict_doc["ground_support_labels"],
        "acquisition_labels_avoided_by_normalized_factor_prior": reduction,
        "normalized_factor_prior_certificate_local_labels": prior_owned[
            "certificate_ground_support_labels_paid_once"
        ],
        "strict_no_prior_certificate_local_labels": strict_owned[
            "certificate_ground_support_labels_paid_once"
        ],
        "normalized_factor_prior_lifetime_target_labels": prior_owned[
            "lifetime_target_ground_support_labels"
        ],
        "strict_no_prior_lifetime_target_labels": strict_owned[
            "lifetime_target_ground_support_labels"
        ],
        "normalized_factor_prior_execution_steps": prior_owned["execution_step_count"],
        "strict_no_prior_execution_steps": strict_owned["execution_step_count"],
        "normalized_factor_prior_derivation_compute_events": prior_doc[
            "derivation_compute_events"
        ],
        "strict_no_prior_derivation_compute_events": strict_doc[
            "derivation_compute_events"
        ],
        "normalized_factor_prior_planning_compute_events": prior_owned[
            "actual_new_abstract_planning_compute_events"
        ],
        "strict_no_prior_planning_compute_events": strict_owned[
            "actual_new_abstract_planning_compute_events"
        ],
        "sample_labels_execution_steps_derivation_and_planning_compute_separate": True,
        "scalar_cost_aggregation_performed": False,
    }
    gate = {
        "normalized_factor_prior_stops_before_strict_no_prior": True,
        "same_raw_transition_prefix_through_common_label": True,
        "same_synthesizer_representation_and_stop_rule": True,
        "only_arm_switch_is_normalized_factor_prior": True,
        "fixed_two_to_library_cardinality_prior_multiplier_absent": True,
        "robust_dictionary_selected_before_target_outcomes": True,
        "leave_one_source_campaign_reconstruction_present": True,
        "both_arm_receding_episodes_succeed": True,
        "both_arms_use_certificate_failure_only_local_ground_distinctions": True,
        "both_planners_consume_compiled_model_without_raw_rows": True,
        "retained_sequence_orchestration_absent": True,
        "passed": True,
    }
    _require(
        reduction > 0
        and row["robust_factor_dictionary_id"]
        == projection["source_factor_library_id"]
        and row["robust_factor_dictionary_selected_template_count"]
        == len(projection["cross_schema_subprograms"])
        and row["accounting"] == accounting
        and row["registered_gate"] == gate
        and row["registered_workload_sample_efficiency_improvement_observed"] is True
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["complete_ground_world_model_synthesized"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["official_N_break_even"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and row["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V131R2 occurrence Gate/accounting changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "normalized_factor_prior_labels": prior_doc["ground_support_labels"],
        "strict_no_prior_labels": strict_doc["ground_support_labels"],
        "labels_avoided": reduction,
        "normalized_factor_prior_sequence": prior_sequence,
        "strict_no_prior_sequence": strict_sequence,
        "accounting": accounting,
    }


def freeze_robust_dictionary_factor_prior_verification_v131r2(
    campaign_raw: bytes,
    predecessor_artifacts: Mapping[str, bytes],
    source_campaign_bytes: Mapping[str, bytes],
) -> bytes:
    _require(
        tuple(sorted(predecessor_artifacts)) == tuple(sorted(_PREDECESSOR_NAMES)),
        "V131R2 predecessor inventory changed",
    )
    campaign = loads_canonical_json(campaign_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V131R2 frozen campaign identity/bytes changed",
    )
    _verify_id(campaign, "campaign_id", _DOMAINS["campaign"])
    p = predecessor_artifacts
    v130_inputs = {
        key: p[key] for key in predecessor._PREDECESSOR_NAMES  # noqa: SLF001
    }
    expected_predecessor = (
        predecessor.freeze_normalized_mixture_factor_prior_verification_v130(
            p["v130_campaign"], v130_inputs, dict(source_campaign_bytes)
        )
    )
    _require(
        expected_predecessor == p["v130_verification"],
        "V131R2 producer-free V130 predecessor changed",
    )
    v131 = loads_canonical_json(p["v131_preregistration"])
    v131r1 = loads_canonical_json(p["v131r1_preregistration"])
    failed_v131r1 = loads_canonical_json(p["failed_v131r1"])
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["v130_success_campaign_id"] == V130_CAMPAIGN_ID
        and campaign["v130_success_verification_id"] == V130_VERIFICATION_ID
        and canonical_json_bytes(v131) == p["v131_preregistration"]
        and len(p["v131_preregistration"]) == V131_PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(p["v131_preregistration"]).hexdigest()
        == V131_PREREGISTRATION_SHA256
        and v131["preregistration_id"] == V131_PREREGISTRATION_ID
        and canonical_json_bytes(v131r1) == p["v131r1_preregistration"]
        and len(p["v131r1_preregistration"])
        == V131R1_PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(p["v131r1_preregistration"]).hexdigest()
        == V131R1_PREREGISTRATION_SHA256
        and v131r1["preregistration_id"] == V131R1_PREREGISTRATION_ID
        and v131r1["frozen_pre_outcome_withdrawn_predecessor"][
            "v131_preregistration_id"
        ]
        == V131_PREREGISTRATION_ID
        and canonical_json_bytes(failed_v131r1) == p["failed_v131r1"]
        and len(p["failed_v131r1"]) == V131R1_FAILED_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(p["failed_v131r1"]).hexdigest()
        == V131R1_FAILED_CAMPAIGN_SHA256
        and failed_v131r1["campaign_id"] == V131R1_FAILED_CAMPAIGN_ID
        and failed_v131r1["registered_gate"]["passed"] is False
        and failed_v131r1["preregistration_id"] == V131R1_PREREGISTRATION_ID,
        "V131R2 predecessor joins changed",
    )
    source_library = derive_artifact_factor_projection_v120(
        dict(source_campaign_bytes)
    )
    dictionary = _robust_dictionary(source_library)
    projection = dictionary["v15_partial_synthesizer_projection"]
    _require(
        campaign["robust_factor_dictionary_id"] == dictionary["dictionary_id"]
        and campaign["robust_factor_dictionary_selected_template_count"]
        == dictionary["selected_template_count"],
        "V131R2 robust factor dictionary changed",
    )
    rows = tuple(
        _verify_occurrence(row, projection) for row in campaign["target_occurrences"]
    )
    _require(
        tuple((row["family"], row["seed"]) for row in rows)
        == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V131R2 target occurrence identities changed",
    )
    ood = campaign["incompatible_schema_no_transfer_control"]
    _require(
        ood["control_id"]
        == _content_id(
            _DOMAINS["ood"],
            {key: value for key, value in ood.items() if key != "control_id"},
        )
        and ood["strict_ood_no_transfer"] is True
        and ood["learned_structure_prior_delivered"] is False
        and ood["target_outcomes_accessed"] is False,
        "V131R2 strict OOD control changed",
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {
        key: sum(row["accounting"][key] for row in rows) for key in numeric
    }
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    gate = {
        "required_target_occurrence_count": 6,
        "passed_target_occurrence_count": 6,
        "every_occurrence_has_strictly_positive_label_reduction": True,
        "fixed_two_to_library_cardinality_prior_multiplier_absent_everywhere": True,
        "robust_dictionary_selected_before_target_outcomes": True,
        "robust_dictionary_cardinality_not_preregistered": True,
        "leave_one_source_campaign_reconstruction_verified": True,
        "same_synthesizer_representation_and_stop_rule_in_every_occurrence": True,
        "both_arm_receding_episodes_succeed_everywhere": True,
        "strict_incompatible_schema_no_transfer_verified": True,
        "passed": True,
    }
    _require(
        campaign["accounting"] == accounting
        and campaign["registered_gate"] == gate
        and campaign[
            "registered_workload_sample_efficiency_improvement_observed"
        ]
        is True
        and campaign["sample_efficiency_improvement_claim_scope"]
        == "ONLY_THE_PREREGISTERED_V131R2_THREE_FAMILY_WORKLOAD"
        and campaign[
            "fixed_two_to_library_cardinality_prior_multiplier_present"
        ]
        is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V131R2 campaign Gate/accounting changed",
    )
    payload = {
        "schema": "acfqp.robust_dictionary_factor_prior_verification.v131r2",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v130_predecessor_verification_id": V130_VERIFICATION_ID,
        "v131_withdrawn_preregistration_id": V131_PREREGISTRATION_ID,
        "v131r1_failed_campaign_id": V131R1_FAILED_CAMPAIGN_ID,
        "robust_factor_dictionary_id": dictionary["dictionary_id"],
        "robust_factor_dictionary_selected_template_count": dictionary[
            "selected_template_count"
        ],
        "robust_dictionary_calibration": _calibration(projection),
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_path_first_batch_reconstruction": True,
        "producer_free_prefix_code_candidate_and_stop_reconstruction": True,
        "producer_free_robust_dictionary_reconstruction": True,
        "producer_free_raw_transition_model_epoch_reconstruction": True,
        "producer_free_receipt_and_plan_reconstruction": True,
        "fixed_two_to_library_cardinality_prior_multiplier_present": False,
        "registered_workload_sample_efficiency_improvement_independently_verified": True,
        "sample_efficiency_improvement_claim_scope": (
            "ONLY_THE_PREREGISTERED_V131R2_THREE_FAMILY_WORKLOAD"
        ),
        "arbitrary_unseen_domain_transfer_claimed": False,
        "complete_ground_world_model_synthesized": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": _content_id(_DOMAINS["verification"], payload),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V131R2 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_robust_dictionary_factor_prior_verification_v131r2",
)
