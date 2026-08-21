"""Producer-free reconstruction of normalized prefix-code prior V130."""

from __future__ import annotations

import copy
import hashlib
from math import ceil, gcd, log2
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_fair_unified_factor_prior_ablation_independent_verifier_v129r1 as predecessor
from acfqp import construction_k7_generic_quotient_compiler_independent_verifier_v123r1 as generic
from acfqp import construction_k7_standalone_generic_model_independent_verifier_v125 as model
from acfqp import generic_atomic_expression_world_model_v4 as atomic
from acfqp.generic_artifact_derived_factor_projection_v120 import (
    derive_artifact_factor_projection_v120,
)
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    _dependencies,
    exact_generic_artifact_factor_replay_v121,
    generic_artifact_factor_stop_update_v121,
    instantiate_normalized_subprograms_v121,
)
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    _ast_bits,
    _dependency_binding_bits,
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


CAMPAIGN_ID = "96447e0821d622b044daaffa8f9e0c8b0e1814a799b9b40f438ce5b4b8d55cbe"
CAMPAIGN_BYTE_COUNT = 11_815_506
CAMPAIGN_SHA256 = "9c179b4c9b54fa885d85c58608879c8b39649dd5cc8881e2d5a1cd6cfc90a433"
PREREGISTRATION_ID = "ed61ef6b5c0a0cf93d9ebccd34c6e172bf1f32a4709b893c1b8116497e6ce063"
V129R1_CAMPAIGN_ID = predecessor.CAMPAIGN_ID
V129R1_VERIFICATION_ID = predecessor.VERIFICATION_ID
EXPECTED_OCCURRENCES = (
    (INVENTORY, 1_046_101),
    (INVENTORY, 1_046_102),
    (DUAL, 1_046_103),
    (DUAL, 1_046_104),
    (MODULAR, 1_046_105),
    (MODULAR, 1_046_106),
)
EXPECTED_EPISODES = (335, 336, 337)
VERIFICATION_ID = "e5e09c7276660710654fef215ab2f3558a9fbc9b88ed0d01ba9b7b2935ea8225"
EXPECTED_CANONICAL_BYTE_COUNT = 10_530
EXPECTED_CANONICAL_SHA256 = "49ec7bfd4c698d2ea983706feb25fbda95aa81d7782a9dcd57e5f97554db0cfd"


_DOMAINS = {
    "campaign": "acfqp:construction-k7-normalized-mixture-factor-prior-campaign:v130",
    "occurrence": "acfqp:construction-k7-normalized-mixture-factor-prior-occurrence:v130",
    "candidate": "acfqp:construction-k7-normalized-mixture-factor-prior-candidate:v130",
    "acquisition": "acfqp:construction-k7-normalized-mixture-factor-prior-acquisition-arm:v130",
    "sequence": "acfqp:construction-k7-standalone-generic-owned-sequence:v126",
    "verification": "acfqp:construction-k7-normalized-mixture-factor-prior-verification:v130",
    "plan": "acfqp:generic-legality-conditioned-quotient-plan:v106",
    "ood": "acfqp:incompatible-schema-no-transfer-control:v99",
    "calibration": "acfqp:source-support-normalized-mixture-calibration:v130",
}
_BUILDERS = {
    INVENTORY: build_inventory_assembly_adapter_v118,
    DUAL: build_dual_budget_adapter_v119,
    MODULAR: build_modular_routing_adapter_v128,
}
_PREDECESSOR_NAMES = (
    "v129r1_campaign",
    "v129r1_verification",
    *predecessor._PREDECESSOR_NAMES,  # noqa: SLF001
)


class ConstructionK7NormalizedMixtureFactorPriorIndependentVerifierV130Error(
    ValueError
):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7NormalizedMixtureFactorPriorIndependentVerifierV130Error(
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
    _require(document.get(key) == _content_id(domain, payload), f"V130 {key} changed")


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
        "schema": "acfqp.source_support_normalized_mixture_calibration.v130",
        "source_factor_library_id": projection["source_factor_library_id"],
        "artifact_template_count": len(templates),
        "distinct_source_schema_pair_count": len(pairs),
        "observed_template_schema_support_cell_count": observed,
        "possible_template_schema_support_cell_count": possible,
        "normalized_mixture_branch_prefix_bits": 1,
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
                "normalized_mixture_branch_prefix_bits": 1,
                "selection_rule": (
                    "OPTIONAL_PREFIX_CODE_BITS_THEN_DEPTH_THEN_AST_MDL_THEN_BYTES"
                ),
            }
        )
    _require(
        len(assignments) >= config["minimum_reusable_factor_count"],
        "V130 independent candidate lacks assignments",
    )
    payload = {
        "schema": "acfqp.normalized_mixture_generic_partial_factor_candidate.v130",
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
        "normalized_mixture_calibration": calibration,
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
    calibration = candidate.public_document["normalized_mixture_calibration"]
    branch_bits = calibration["normalized_mixture_branch_prefix_bits"]
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
                "normalized_mixture_selected_prefix_bits": prior_bits,
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
        "schema": "acfqp.normalized_mixture_factor_stop_update.v130",
        "factor_prior_enabled": enabled,
        "normalized_mixture_component_weights": {
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
        "V130 acquisition did not independently stop",
    )
    raw_rows = tuple(rows)
    payload = {
        "schema": "acfqp.normalized_mixture_factor_acquisition_arm.v130",
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
    _require(rebuilt == recorded, "V130 acquisition reconstruction changed")
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
        "V130 owned sequence identity changed",
    )
    dependency = sequence["program_branch_dependency_receipt"]
    _require(
        sequence["program_branch_dependency_receipt_id"]
        == dependency["dependency_receipt_id"]
        and dependency["partial_candidate_id"] == candidate["candidate_id"]
        and dependency["compiled_factor_assignments"]
        == candidate["compiled_factor_assignments"],
        "V130 dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in dependency["canonical_action_catalogue"]
    }
    persistent = sequence["persistent_exact_overlay_rows"]
    _require(
        hashlib.sha256(canonical_json_bytes(persistent)).hexdigest()
        == sequence["persistent_exact_overlay_sha256"],
        "V130 persistent evidence hash changed",
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
        "V130 bootstrap reconstruction changed",
    )
    updates = sequence["standalone_model_update_receipts"]
    matches = sequence["standalone_full_rebuild_match_receipts"]
    _require(
        len(sequence["episodes"])
        == len(updates)
        == len(matches)
        == len(EXPECTED_EPISODES),
        "V130 episode/receipt cardinality changed",
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
            "V130 before-model reconstruction changed",
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
                    "V130 terminal projection rule changed",
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
                        "V130 direct generic plan changed",
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
                        "V130 dependency reuse changed",
                    )
            else:
                _fail("V130 unknown planning source")
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
            "V130 update/full-match reconstruction changed",
        )
        rebuilt_models.append(after["model"])
        _require(
            episode["success"] is True
            and episode[
                "all_incremental_ground_queries_followed_failed_certificates"
            ]
            is True
            and episode["planner_raw_transition_argument_present"] is False,
            "V130 certificate discipline changed",
        )
    _require(
        [current[key] for key in sorted(current)] == list(persistent),
        "V130 persistent inventory changed",
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
        "V130 sequence accounting/claim boundary changed",
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
        and row["schema"] == "acfqp.normalized_mixture_factor_prior_occurrence.v130"
        and tuple(row["episode_indices"]) == EXPECTED_EPISODES,
        "V130 occurrence identity changed",
    )
    _verify_id(row, "occurrence_id", _DOMAINS["occurrence"])
    config = _config()
    adapter = _BUILDERS[family](seed, config)
    strict_labels = row["strict_no_prior_acquisition"]["ground_support_labels"]
    stream = predecessor._path_first_batches(adapter)  # noqa: SLF001
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
        "sample_labels_and_derivation_compute_separate": True,
    }
    _require(row["sample_tax_comparison"] == sample_tax, "V130 sample tax changed")
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
        "both_arm_receding_episodes_succeed": True,
        "both_arms_use_certificate_failure_only_local_ground_distinctions": True,
        "both_planners_consume_compiled_model_without_raw_rows": True,
        "retained_sequence_orchestration_absent": True,
        "passed": True,
    }
    _require(
        reduction > 0
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
        "V130 occurrence Gate/accounting changed",
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


def freeze_normalized_mixture_factor_prior_verification_v130(
    campaign_raw: bytes,
    predecessor_artifacts: Mapping[str, bytes],
    source_campaign_bytes: Mapping[str, bytes],
) -> bytes:
    _require(
        tuple(sorted(predecessor_artifacts)) == tuple(sorted(_PREDECESSOR_NAMES)),
        "V130 predecessor inventory changed",
    )
    campaign = loads_canonical_json(campaign_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V130 frozen campaign identity/bytes changed",
    )
    _verify_id(campaign, "campaign_id", _DOMAINS["campaign"])
    p = predecessor_artifacts
    v129r1_inputs = {
        key: p[key] for key in predecessor._PREDECESSOR_NAMES  # noqa: SLF001
    }
    expected_predecessor = (
        predecessor.freeze_fair_unified_factor_prior_ablation_verification_v129r1(
            p["v129r1_campaign"], v129r1_inputs, dict(source_campaign_bytes)
        )
    )
    _require(
        expected_predecessor == p["v129r1_verification"],
        "V130 producer-free V129r1 predecessor changed",
    )
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["v129r1_success_campaign_id"] == V129R1_CAMPAIGN_ID
        and campaign["v129r1_success_verification_id"] == V129R1_VERIFICATION_ID,
        "V130 predecessor joins changed",
    )
    library = derive_artifact_factor_projection_v120(dict(source_campaign_bytes))
    projection = library["v15_partial_synthesizer_projection"]
    _require(
        campaign["artifact_factor_library_id"] == library["factor_library_id"],
        "V130 artifact factor library changed",
    )
    rows = tuple(
        _verify_occurrence(row, projection) for row in campaign["target_occurrences"]
    )
    _require(
        tuple((row["family"], row["seed"]) for row in rows)
        == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V130 target occurrence identities changed",
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
        "V130 strict OOD control changed",
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
        == "ONLY_THE_PREREGISTERED_V130_THREE_FAMILY_WORKLOAD"
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
        "V130 campaign Gate/accounting changed",
    )
    payload = {
        "schema": "acfqp.normalized_mixture_factor_prior_verification.v130",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v129r1_predecessor_verification_id": V129R1_VERIFICATION_ID,
        "normalized_mixture_calibration": _calibration(projection),
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_path_first_batch_reconstruction": True,
        "producer_free_prefix_code_candidate_and_stop_reconstruction": True,
        "producer_free_raw_transition_model_epoch_reconstruction": True,
        "producer_free_receipt_and_plan_reconstruction": True,
        "fixed_two_to_library_cardinality_prior_multiplier_present": False,
        "registered_workload_sample_efficiency_improvement_independently_verified": True,
        "sample_efficiency_improvement_claim_scope": (
            "ONLY_THE_PREREGISTERED_V130_THREE_FAMILY_WORKLOAD"
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
            "V130 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_normalized_mixture_factor_prior_verification_v130",
)
