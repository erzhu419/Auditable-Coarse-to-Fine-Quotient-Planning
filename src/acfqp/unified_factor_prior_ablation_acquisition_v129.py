"""Matched acquisition with one grammar, candidate carrier and stop rule.

The two arms observe one witness-blind trajectory.  Both enumerate the same
generic atomic-expression pool and emit the same partial-candidate schema.
The sole arm switch is the registered factor prior: artifact-derived
expressions receive the first ranking bit and the corresponding finite prior
mass in the otherwise identical e-value boundary.  Candidate replay,
hypothesis pool, carrier and stopping function are shared literally.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v129 as domains
from acfqp import generic_atomic_expression_world_model_v4 as atomic
from acfqp import true_bit_symmetric_three_domain_campaign_core_v59 as frontier
from acfqp.generic_artifact_derived_factor_projection_v120 import verify_artifact_factor_projection_v120
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    _dependencies,
    exact_generic_artifact_factor_replay_v121,
    generic_artifact_factor_stop_update_v121,
    instantiate_normalized_subprograms_v121,
)
from acfqp.generic_layout_factorized_world_model_v5 import align_generic_occurrence_v5, discover_generic_layout_v5
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes


class UnifiedFactorPriorAblationAcquisitionV129Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise UnifiedFactorPriorAblationAcquisitionV129Error(message)


def _identifier(domain: str, payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {**payload, key: domains.extension_content_id_v129(domain, payload)}


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


def synthesize_unified_factor_candidate_v129(
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
        _fail("V129 unified candidate contract changed")
    layout = discover_generic_layout_v5(rows, catalogue, layout_domain=layout_domain)
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, layout, canonical_occurrence=0
    )
    grouped = atomic._grouped(aligned_rows)  # noqa: SLF001
    by_occurrence = {0: aligned_catalogue}
    binding = atomic._derive_binding(grouped[0], aligned_catalogue)  # noqa: SLF001
    bindings = {0: binding}
    state_width = len(aligned_rows[0].pre)
    action_width = len(aligned_catalogue[0].fields)
    artifact = _artifact_expression_signatures(state_width, action_width, projection)
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
            # Same grammar and hypothesis pool.  Only the first ranking bit is
            # enabled in the prior arm; the no-prior arm assigns it uniformly.
            rank = (
                0 if not factor_prior_enabled or is_artifact else 1,
                depth,
                atomic._expression_mdl(expression, bindings),  # noqa: SLF001
                encoded,
            )
            candidates.append((rank, result_type, expression, is_artifact, encoded))
        if not candidates:
            continue
        selected = min(candidates)
        _rank, result_type, expression, is_artifact, encoded = selected
        state_dependencies, action_dependencies = _dependencies(expression)
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
                "artifact_expression_present_in_pool": any(row[3] for row in candidates),
                "artifact_expression_selected": is_artifact,
                "selection_rule": "OPTIONAL_ARTIFACT_FIRST_BIT_THEN_DEPTH_THEN_AST_MDL_THEN_BYTES",
            }
        )
    if len(assignments) < minimum_factor_assignment_count:
        _fail("V129 unified grammar did not identify enough partial assignments")
    payload = {
        "schema": "acfqp.unified_generic_partial_factor_candidate.v129",
        "source_factor_library_id": projection["source_factor_library_id"],
        "factor_prior_enabled": factor_prior_enabled,
        "only_arm_switch_is_registered_factor_prior": True,
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
        "target_slot_inventory_supplied_by_prior": False,
        "target_bindings_derived_from_raw_observations": True,
        "semantic_names_used": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    document = _identifier(
        domains.CONSTRUCTION_K7_UNIFIED_FACTOR_CANDIDATE_V129_DOMAIN,
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


def unified_factor_prior_stop_update_v129(
    candidate: PartialFactorCandidateV15,
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    projection: Mapping[str, Any],
    *,
    factor_prior_enabled: bool,
    candidate_epoch: int,
    invalidated_candidate_count: int,
    post_issuance_exact_prediction_success_count: int,
    global_alpha_denominator: int,
) -> dict[str, Any]:
    """Apply one e-value/MDL rule with an explicit finite prior-mass switch."""

    base = generic_artifact_factor_stop_update_v121(
        candidate,
        rows,
        catalogue,
        candidate_epoch=candidate_epoch,
        invalidated_candidate_count=invalidated_candidate_count,
        post_issuance_exact_prediction_success_count=post_issuance_exact_prediction_success_count,
        global_alpha_denominator=global_alpha_denominator,
    )
    registered = {
        row["signature_sha256"]
        for row in projection["cross_schema_subprograms"]
    }
    selected = sum(
        assignment["signature_sha256"] in registered
        for assignment in candidate.assignments
    )
    prior_mass_multiplier = (
        2 ** len(projection["cross_schema_subprograms"])
        if factor_prior_enabled and selected > 0
        else 1
    )
    threshold_met = (
        base["universal_mixture_evalue_numerator"] * prior_mass_multiplier
        >= base["universal_mixture_evalue_denominator"] * base["evalue_threshold"]
    )
    stopped = (
        base["current_partial_factor_replay"]["exact"] is True
        and threshold_met
        and base["raw_partial_outcome_prefix_code_bits"]
        >= base["total_partial_two_part_model_code_bits"]
    )
    return {
        **base,
        "schema": "acfqp.unified_factor_prior_stop_update.v129",
        "factor_prior_enabled": factor_prior_enabled,
        "registered_factor_prior_subprogram_count": len(
            projection["cross_schema_subprograms"]
        ),
        "selected_registered_factor_assignment_count": selected,
        "registered_factor_prior_mass_multiplier": prior_mass_multiplier,
        "shared_base_evalue_threshold": base["evalue_threshold"],
        "universal_mixture_evalue_threshold_met": threshold_met,
        "same_stop_rule_function_in_both_arms": True,
        "only_arm_switch_is_registered_factor_prior": True,
        "stopped": stopped,
    }


def acquire_matched_unified_factor_arms_v129(
    adapter: Any,
    artifact_factor_library: Mapping[str, Any],
    source_campaign_bytes: Mapping[str, bytes],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    verified = verify_artifact_factor_projection_v120(
        artifact_factor_library, source_campaign_bytes
    )
    projection = artifact_factor_library.get("v15_partial_synthesizer_projection")
    if verified["derived_subprogram_count"] != 3 or type(projection) is not dict:
        _fail("V129 artifact projection changed")
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
        frontier.predecessor.predecessor.ground._witness_blind_depth_frontier(adapter), 1
    ):
        if labels > maximum:
            break
        rows.extend(batch)
        batches.append(batch)
        current = tuple(rows)
        if accepting_label is None and any(row.terminal_acceptance_after is True for row in batch):
            accepting_label = labels
        for enabled in (True, False):
            if enabled in results:
                continue
            state = states[enabled]
            candidate = state["candidate"]
            if candidate is not None:
                replay = exact_generic_artifact_factor_replay_v121(candidate, current, adapter.catalogue)
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
                    candidate, compute = synthesize_unified_factor_candidate_v129(
                        current,
                        adapter.catalogue,
                        projection,
                        support_label_count=labels,
                        factor_prior_enabled=enabled,
                        layout_domain=config["generic_domains"]["layout"],
                        minimum_factor_assignment_count=config["minimum_reusable_factor_count"],
                    )
                    state["candidate"] = candidate
                    state["issued"] = labels
                    state["derivation_compute"] += compute["generic_atomic_expression_evaluations"]
                    state["selected_artifact"] = compute["artifact_expression_selected_count"]
                    if state["previous"] is not None and candidate.public_document["candidate_id"] != state["previous"]:
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
            stop = unified_factor_prior_stop_update_v129(
                candidate,
                current,
                adapter.catalogue,
                projection,
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
            arm = "FACTOR_PRIOR_ON" if enabled else "STRICT_NO_PRIOR"
            prefix = tuple(row for selected in batches[:labels] for row in selected)
            payload = {
                "schema": "acfqp.unified_factor_acquisition_arm.v129",
                "family": adapter.family,
                "seed": adapter.seed,
                "arm": arm,
                "factor_prior_enabled": enabled,
                "only_arm_switch_is_registered_factor_prior": True,
                "same_generic_atomic_hypothesis_pool": True,
                "same_candidate_carrier_and_schema": True,
                "same_candidate_replay_function": True,
                "same_stopping_rule_function": True,
                "ground_support_labels": labels,
                "raw_transition_count": len(prefix),
                "raw_transition_sha256": frontier.predecessor.predecessor.ground._raw_sha(prefix),
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
            document = _identifier(
                domains.CONSTRUCTION_K7_UNIFIED_FACTOR_ACQUISITION_ARM_V129_DOMAIN,
                payload,
                "acquisition_id",
            )
            results[enabled] = {
                "document": document,
                "candidate": candidate,
                "rows": prefix,
                "batches": tuple(batches[:labels]),
            }
        if len(results) == 2:
            prior = results[True]
            strict = results[False]
            common = min(len(prior["batches"]), len(strict["batches"]))
            prior_prefix = tuple(row for batch in prior["batches"][:common] for row in batch)
            strict_prefix = tuple(row for batch in strict["batches"][:common] for row in batch)
            if prior_prefix != strict_prefix:
                _fail("V129 matched arms diverged before their common stop")
            return {"FACTOR_PRIOR_ON": prior, "STRICT_NO_PRIOR": strict}
    _fail(f"V129 matched unified acquisition did not close before cap for {adapter.family} seed {adapter.seed}")


__all__ = (
    "acquire_matched_unified_factor_arms_v129",
    "synthesize_unified_factor_candidate_v129",
    "unified_factor_prior_stop_update_v129",
)
