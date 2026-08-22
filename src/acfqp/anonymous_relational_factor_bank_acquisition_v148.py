"""Matched V148 acquisition using V146 anonymous relational templates.

Both arms derive the same occurrence binding and enumerate the same generic
atomic candidates.  The sole arm switch is whether an exact V146 template
instantiation receives its source-derived reference codelength.
"""

from __future__ import annotations

import hashlib
from math import ceil, log2
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v148 as domains
from acfqp import generic_atomic_expression_world_model_v4 as atomic
from acfqp.anonymous_relational_template_instantiator_v147 import (
    BANK_ID,
    VERIFICATION_ID,
    instantiate_anonymous_relational_templates_v147,
)
from acfqp.fair_unified_factor_prior_ablation_acquisition_v129r1 import (
    fair_witness_blind_path_first_stream_v129r1,
)
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
    GenericArtifactSubprogramInstantiatorV121Error,
    _dependencies,
    exact_generic_artifact_factor_replay_v121,
)
from acfqp.generic_bit_codelength_universal_synthesizer_v14 import (
    _ast_bits,
    _dependency_binding_bits,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
    discover_generic_layout_v5,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.generic_relational_factor_execution_projection_v144 import (
    GenericRelationalFactorExecutionProjectionV144Error,
    compile_relational_factor_execution_projection_v144,
    robust_relational_dictionary_factor_stop_update_v144,
)
from acfqp.phase3e_ids import canonical_json_bytes


class AnonymousRelationalFactorBankAcquisitionV148Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise AnonymousRelationalFactorBankAcquisitionV148Error(message)


def _classification(expression: Any) -> dict[str, Any]:
    tokens = atomic._dependency_tokens(expression)  # noqa: SLF001
    return {
        "state_dependencies": sorted(value for kind, value in tokens if kind == "E00"),
        "action_dependencies": sorted(value for kind, value in tokens if kind == "E01"),
        "next_dependencies": [],
        "constant_dependencies": sorted(value for kind, value in tokens if kind == "E03"),
        "relation_dependencies": sorted(value for kind, value in tokens if kind == "E04"),
    }


def _calibration(template_count: int) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.anonymous_relational_source_calibration.v148",
        "source_factor_library_id": BANK_ID,
        "artifact_template_count": template_count,
        "robust_dictionary_branch_prefix_bits": 1,
        "artifact_library_index_prefix_bits": max(1, ceil(log2(max(2, template_count)))),
        "artifact_branch_code": "BANK_INDEX_PLUS_OBSERVATION_DERIVED_ANONYMOUS_BINDING",
        "uniform_tail_branch_code": "FULL_TYPED_ANONYMOUS_AST",
        "fixed_mixture_weight_supplied_by_target": False,
        "target_outcomes_accessed_by_calibration": False,
    }
    return {
        **payload,
        "calibration_id": domains.extension_content_id_v148(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_CALIBRATION_V148_DOMAIN,
            payload,
        ),
    }


def _prepare_candidate_search_v148(
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    instantiation: Mapping[str, Any],
    *,
    layout_domain: str,
) -> dict[str, Any]:
    layout = discover_generic_layout_v5(rows, catalogue, layout_domain=layout_domain)
    if instantiation.get("layout_id") != layout.layout_id:
        _fail("V148 relational receipt crossed layout identities")
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, layout, canonical_occurrence=0
    )
    grouped = atomic._grouped(aligned_rows)  # noqa: SLF001
    binding = atomic._derive_binding(grouped[0], aligned_catalogue)  # noqa: SLF001
    if binding != instantiation.get("observation_derived_binding"):
        _fail("V148 relational receipt crossed observation bindings")
    bindings = {0: binding}
    state_width = len(aligned_rows[0].pre)
    action_width = len(aligned_catalogue[0].fields)
    artifact = {
        (row["target_column"], canonical_json_bytes(row["bound_expression"])): (
            row["template_signature_sha256"],
            any(token[0] == "E04" for token in row["dependency_tokens"]),
        )
        for row in instantiation["exact_instantiations"]
    }
    template_count = instantiation.get("bank_selected_template_count")
    if type(template_count) is not int or template_count <= 0:
        _fail("V148 source-bank template cardinality changed")
    exact_by_target = {}
    total_evaluations = 0
    for target in range(state_width):
        exact, evaluations = atomic._atomic_expression_candidates(  # noqa: SLF001
            target,
            grouped=grouped,
            bindings=bindings,
            state_width=state_width,
            action_field_width=action_width,
            relation_names=set(binding["relations"]),
            constant_names=set(binding["constants"]),
        )
        exact_by_target[target] = exact
        total_evaluations += evaluations
    return {
        "layout": layout,
        "aligned_rows": aligned_rows,
        "binding": binding,
        "bindings": bindings,
        "state_width": state_width,
        "action_width": action_width,
        "artifact": artifact,
        "calibration": _calibration(template_count),
        "exact_by_target": exact_by_target,
        "total_evaluations": total_evaluations,
    }


def synthesize_anonymous_relational_factor_candidate_v148(
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    instantiation: Mapping[str, Any],
    *,
    support_label_count: int,
    factor_prior_enabled: bool,
    layout_domain: str,
    minimum_factor_assignment_count: int,
    _prepared_search: Mapping[str, Any] | None = None,
) -> tuple[PartialFactorCandidateV15, dict[str, int]]:
    if (
        not rows
        or not catalogue
        or support_label_count <= 0
        or type(factor_prior_enabled) is not bool
        or minimum_factor_assignment_count <= 0
        or instantiation.get("bank_id") != BANK_ID
        or instantiation.get("bank_verification_id") != VERIFICATION_ID
        or instantiation.get("binding_derived_from_raw_observations") is not True
    ):
        _fail("V148 candidate inventory or relational receipt changed")
    prepared = dict(
        _prepared_search
        or _prepare_candidate_search_v148(
            rows, catalogue, instantiation, layout_domain=layout_domain
        )
    )
    layout = prepared["layout"]
    aligned_rows = prepared["aligned_rows"]
    bindings = prepared["bindings"]
    state_width = prepared["state_width"]
    action_width = prepared["action_width"]
    artifact = prepared["artifact"]
    calibration = prepared["calibration"]
    assignments = []
    ambiguity = []
    total_evaluations = prepared["total_evaluations"]
    artifact_selected = relational_artifact_selected = 0
    for target in range(state_width):
        exact = prepared["exact_by_target"][target]
        candidates = []
        for depth, result_type, expression in exact:
            if result_type not in {"INT", "FINITE_INT_SUPPORT"}:
                continue
            encoded = canonical_json_bytes(expression)
            artifact_row = artifact.get((target, encoded))
            signature = artifact_row[0] if artifact_row is not None else None
            is_relational_artifact = (
                artifact_row[1] if artifact_row is not None else False
            )
            classification = _classification(expression)
            generic_bits = _ast_bits(expression)
            reference_bits = (
                calibration["artifact_library_index_prefix_bits"]
                + _dependency_binding_bits(classification)
                if signature is not None
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
                    signature is not None,
                    signature or hashlib.sha256(encoded).hexdigest(),
                    generic_bits,
                    reference_bits,
                    classification,
                    is_relational_artifact,
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
            signature,
            generic_bits,
            reference_bits,
            classification,
            is_relational_artifact,
        ) = min(candidates)
        assignments.append(
            {
                "target_column": target,
                "result_type": result_type,
                "expression": expression,
                "signature_sha256": signature,
                "state_dependencies": classification["state_dependencies"],
                "action_dependencies": classification["action_dependencies"],
            }
        )
        artifact_selected += int(is_artifact)
        relational_artifact_selected += int(
            is_artifact and is_relational_artifact
        )
        ambiguity.append(
            {
                "target_column": target,
                "same_generic_hypothesis_pool_size": len(candidates),
                "artifact_expression_count_in_same_pool": artifact_count,
                "artifact_expression_present_in_pool": artifact_count > 0,
                "artifact_expression_selected": is_artifact,
                "relational_artifact_expression_selected": (
                    is_artifact and is_relational_artifact
                ),
                "generic_ast_prefix_bits": generic_bits,
                "artifact_reference_prefix_bits": reference_bits,
                "selection_rule": "OPTIONAL_PREFIX_CODE_BITS_THEN_DEPTH_THEN_AST_MDL_THEN_BYTES",
            }
        )
    if len(assignments) < minimum_factor_assignment_count:
        _fail("V148 generic grammar did not identify enough partial assignments")
    payload = {
        "schema": "acfqp.anonymous_relational_prior_partial_candidate.v148",
        "source_factor_library_id": BANK_ID,
        "source_factor_library_verification_id": VERIFICATION_ID,
        "anonymous_relational_instantiation_id": instantiation["instantiation_id"],
        "factor_prior_enabled": factor_prior_enabled,
        "only_arm_switch_is_anonymous_relational_prior": True,
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
        "relational_artifact_expression_selected_count": (
            relational_artifact_selected
        ),
        "robust_dictionary_calibration": calibration,
        "normalized_artifact_uniform_mixture_prior_present": factor_prior_enabled,
        "constant_relation_and_coordinate_bindings_derived_from_raw_observations": True,
        "target_slot_inventory_supplied_by_prior": False,
        "semantic_names_used": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    document = {
        **payload,
        "candidate_id": domains.extension_content_id_v148(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_CANDIDATE_V148_DOMAIN,
            payload,
        ),
    }
    return (
        PartialFactorCandidateV15(document, layout, tuple(assignments), aligned_rows),
        {
            "generic_atomic_expression_evaluations": total_evaluations,
            "artifact_expression_selected_count": artifact_selected,
            "relational_artifact_expression_selected_count": (
                relational_artifact_selected
            ),
        },
    )


def acquire_matched_anonymous_relational_factor_bank_arms_v148(
    adapter: Any,
    bank_raw: bytes,
    verification_raw: bytes,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    states = {
        enabled: {
            "candidate": None,
            "execution_candidate": None,
            "instantiation": None,
            "issued": 0,
            "invalidated": 0,
            "disagreements": 0,
            "epoch": 0,
            "successes": 0,
            "previous": None,
            "history": [],
            "derivation_compute": 0,
            "instantiation_compute": 0,
            "selected_artifact": 0,
            "selected_relational_artifact": 0,
            "candidate_replay_errors": 0,
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
        shared_instantiation = None
        shared_prepared_search = None
        for enabled in (True, False):
            if enabled in results:
                continue
            state = states[enabled]
            candidate = state["candidate"]
            if candidate is not None:
                try:
                    replay = exact_generic_artifact_factor_replay_v121(
                        state["execution_candidate"], current, adapter.catalogue
                    )
                except (
                    GenericArtifactSubprogramInstantiatorV121Error,
                    GenericRelationalFactorExecutionProjectionV144Error,
                ) as error:
                    state["previous"] = candidate.public_document["candidate_id"]
                    state["candidate"] = None
                    state["execution_candidate"] = None
                    state["instantiation"] = None
                    state["invalidated"] += 1
                    state["epoch"] += 1
                    state["successes"] = 0
                    state["candidate_replay_errors"] += 1
                    state["history"].append(
                        {
                            "support_label_count": labels,
                            "candidate_available": False,
                            "candidate_replay_error_type": type(error).__name__,
                        }
                    )
                else:
                    if replay["exact"] is True:
                        state["successes"] += 1
                    else:
                        state["previous"] = candidate.public_document["candidate_id"]
                        state["candidate"] = None
                        state["execution_candidate"] = None
                        state["instantiation"] = None
                        state["invalidated"] += 1
                        state["epoch"] += 1
                        state["successes"] = 0
            if state["candidate"] is None:
                try:
                    if shared_instantiation is None:
                        layout = discover_generic_layout_v5(
                            current,
                            adapter.catalogue,
                            layout_domain=config["generic_domains"]["layout"],
                        )
                        shared_instantiation = instantiate_anonymous_relational_templates_v147(
                            bank_raw,
                            verification_raw,
                            current,
                            adapter.catalogue,
                            layout,
                        )
                    if shared_prepared_search is None:
                        shared_prepared_search = _prepare_candidate_search_v148(
                            current,
                            adapter.catalogue,
                            shared_instantiation,
                            layout_domain=config["generic_domains"]["layout"],
                        )
                    candidate, compute = synthesize_anonymous_relational_factor_candidate_v148(
                        current,
                        adapter.catalogue,
                        shared_instantiation,
                        support_label_count=labels,
                        factor_prior_enabled=enabled,
                        layout_domain=config["generic_domains"]["layout"],
                        minimum_factor_assignment_count=config[
                            "minimum_reusable_factor_count"
                        ],
                        _prepared_search=shared_prepared_search,
                    )
                    execution_candidate = compile_relational_factor_execution_projection_v144(
                        candidate, current, adapter.catalogue
                    )
                    state["candidate"] = candidate
                    state["execution_candidate"] = execution_candidate
                    state["instantiation"] = shared_instantiation
                    state["issued"] = labels
                    state["derivation_compute"] += compute[
                        "generic_atomic_expression_evaluations"
                    ]
                    state["instantiation_compute"] += shared_instantiation[
                        "template_binding_evaluation_events"
                    ]
                    state["selected_artifact"] = compute[
                        "artifact_expression_selected_count"
                    ]
                    state["selected_relational_artifact"] = compute[
                        "relational_artifact_expression_selected_count"
                    ]
                    if (
                        state["previous"] is not None
                        and candidate.public_document["candidate_id"] != state["previous"]
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
            execution_candidate = state["execution_candidate"]
            try:
                stop = robust_relational_dictionary_factor_stop_update_v144(
                    candidate,
                    execution_candidate,
                    current,
                    adapter.catalogue,
                    factor_prior_enabled=enabled,
                    candidate_epoch=state["epoch"],
                    invalidated_candidate_count=state["invalidated"],
                    post_issuance_exact_prediction_success_count=state["successes"],
                    global_alpha_denominator=config["global_alpha_denominator"],
                )
            except (
                GenericArtifactSubprogramInstantiatorV121Error,
                GenericRelationalFactorExecutionProjectionV144Error,
            ) as error:
                state["history"].append(
                    {
                        "support_label_count": labels,
                        "candidate_available": True,
                        "candidate_id": candidate.public_document["candidate_id"],
                        "candidate_stop_replayable": False,
                        "candidate_replay_error_type": type(error).__name__,
                    }
                )
                state["previous"] = candidate.public_document["candidate_id"]
                state["candidate"] = None
                state["execution_candidate"] = None
                state["instantiation"] = None
                state["invalidated"] += 1
                state["epoch"] += 1
                state["successes"] = 0
                state["candidate_replay_errors"] += 1
                continue
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
                "schema": "acfqp.anonymous_relational_factor_bank_acquisition_arm.v148",
                "family": adapter.family,
                "seed": adapter.seed,
                "arm": "ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON" if enabled else "STRICT_NO_PRIOR",
                "factor_prior_enabled": enabled,
                "v146_factor_bank_id": BANK_ID,
                "v146_independent_verification_id": VERIFICATION_ID,
                "anonymous_relational_instantiation": state["instantiation"],
                "frozen_v146_bank_consumed_before_registered_target_outcomes": True,
                "binding_derived_from_current_raw_prefix_in_both_arms": True,
                "fair_witness_blind_path_first_backtracking": True,
                "generation_witness_accessed": False,
                "reachable_frontier_exhaustion_used_as_stopping_input": False,
                "only_arm_switch_is_anonymous_relational_prior": True,
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
                "execution_projection": dict(execution_candidate.public_document),
                "candidate_issued_at_support_label": state["issued"],
                "invalidated_candidate_count": state["invalidated"],
                "candidate_program_disagreement_count": state["disagreements"],
                "candidate_replay_error_count": state["candidate_replay_errors"],
                "candidate_epoch": state["epoch"],
                "post_issuance_exact_prediction_success_count": state["successes"],
                "first_accepting_observation_label": accepting_label,
                "terminal_stop_update": dict(stop),
                "stopping_history": list(state["history"]),
                "derivation_compute_events": state["derivation_compute"],
                "template_binding_evaluation_events": state["instantiation_compute"],
                "artifact_expression_selected_count": state["selected_artifact"],
                "relational_artifact_expression_selected_count": state[
                    "selected_relational_artifact"
                ],
                "sample_labels_and_derivation_compute_separate": True,
                "complete_world_model_claimed": False,
                "planning_authority_present": False,
            }
            results[enabled] = {
                "document": {
                    **payload,
                    "acquisition_id": domains.extension_content_id_v148(
                        domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_ACQUISITION_V148_DOMAIN,
                        payload,
                    ),
                },
                "candidate": execution_candidate,
                "source_candidate": candidate,
                "rows": prefix,
                "batches": tuple(batches[:labels]),
            }
        if len(results) == 2:
            prior, strict = results[True], results[False]
            common = min(len(prior["batches"]), len(strict["batches"]))
            if tuple(row for batch in prior["batches"][:common] for row in batch) != tuple(
                row for batch in strict["batches"][:common] for row in batch
            ):
                _fail("V148 matched arms diverged before common stop")
            return {
                "ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON": prior,
                "STRICT_NO_PRIOR": strict,
            }
    _fail(
        f"V148 anonymous-relational acquisition did not close before cap for "
        f"{adapter.family} seed {adapter.seed}"
    )


__all__ = (
    "acquire_matched_anonymous_relational_factor_bank_arms_v148",
    "synthesize_anonymous_relational_factor_candidate_v148",
)
