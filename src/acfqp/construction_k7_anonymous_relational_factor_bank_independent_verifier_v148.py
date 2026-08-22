"""Producer-free verification of the frozen V148 campaign.

This module deliberately does not import the V148 producer, campaign core,
acquisition implementation, or the V147 instantiator.  It reconstructs their
observable semantics from the frozen source bank and raw transition stream.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import copy
import hashlib
from itertools import product
from math import ceil, log2
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v148 as domains
from acfqp import construction_k7_certificate_local_recovery_union_independent_verifier_v145 as previous
from acfqp import generic_atomic_expression_world_model_v4 as atomic
from acfqp.agreement_shielded_cross_family_campaign_core_v99 import (
    incompatible_schema_no_transfer_control_v99,
)
from acfqp.generic_artifact_subprogram_instantiator_v121 import (
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
from acfqp.generic_maintenance_cascade_adapter_v144 import (
    FAMILY,
    build_maintenance_cascade_adapter_v144,
    maintenance_cascade_config_v144,
)
from acfqp.generic_partial_factor_proposal_v15 import PartialFactorCandidateV15
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_ID = "d555b567fafef5053dbfdcd6fae725b4913e989a7888e70c0021248e370e5a57"
CAMPAIGN_BYTE_COUNT = 18_492_453
CAMPAIGN_SHA256 = "edd853eba70e28bb8efc94015fde5f81b3146db7d57cfe5688bb64e632581979"
PREREGISTRATION_ID = "b8e2e47d301a77134e90e27beecd263be211ce383c90fa959d3eae26261c7900"
PREREGISTRATION_BYTE_COUNT = 8_523
PREREGISTRATION_SHA256 = "bed3f6a36aea6601f495602db0ec712e5431012f89f1370574367aaf3c4fee21"
BANK_ID = "78bb4dae4682ed0cedb7a7781caca4af04986f0db86d7086a0786166d07020b5"
BANK_BYTE_COUNT = 4_033
BANK_SHA256 = "eb733aad5d7b5aed20933366ba4b6f8c9d24338b20a4437ef11ffbf4f0a99fe6"
BANK_VERIFICATION_ID = "7531dcc153b64ba8c23ae70fce84650b0be0550acaf3db915b106adf2bd6e63b"
BANK_VERIFICATION_BYTE_COUNT = 1_028
BANK_VERIFICATION_SHA256 = "891b48ce7d035ea8e56f68a3e3dc6a8838cbd62dfabf7af6a86a5d81f14a7e80"
EXPECTED_OCCURRENCES = tuple((FAMILY, seed) for seed in range(1_047_311, 1_047_317))
EXPECTED_EPISODES = (521, 522, 523, 524)
VERIFICATION_ID = "442393a952009697d0881e5b8d934f1ca570c838c483f757740024f77a685280"
EXPECTED_CANONICAL_BYTE_COUNT = 12_340
EXPECTED_CANONICAL_SHA256 = "edc41ed8f339f216938cdb547e0217344913b58d4141a6236a588e32a60b6388"

_V147_INSTANTIATION_DOMAIN = "acfqp:construction-k7-anonymous-relational-instantiation:v147"
_V144_EXECUTION_DOMAIN = "acfqp:construction-k7-relational-factor-execution-projection:v144"
_V144R1_SEQUENCE_DOMAIN = "acfqp:construction-k7-relational-overlay-sequence:v144r1"


class ConstructionK7AnonymousRelationalFactorBankIndependentVerifierV148Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AnonymousRelationalFactorBankIndependentVerifierV148Error(message)


def _require(condition: bool, message: str) -> None:
    if condition is not True:
        _fail(message)


def _content_id(domain: str, payload: Any) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()


def _verify_id(document: Mapping[str, Any], key: str, domain: str) -> None:
    payload = {name: value for name, value in document.items() if name != key}
    _require(document.get(key) == _content_id(domain, payload), f"V148 {key} changed")


def _symbols(expression: Any) -> tuple[tuple[str, int], ...]:
    found: set[tuple[str, int]] = set()

    def visit(value: Any) -> None:
        if type(value) is not list or not value:
            return
        if (
            len(value) == 2
            and value[0] in {"S", "A", "K", "R"}
            and type(value[1]) is int
        ):
            found.add((value[0], value[1]))
            return
        for item in value[1:]:
            visit(item)

    visit(expression)
    return tuple(sorted(found))


def _bind(
    expression: Any,
    *,
    target: int,
    assignment: Mapping[tuple[str, int], Any],
) -> Any:
    if type(expression) is not list or not expression:
        return expression
    if expression == ["S", "SELF"]:
        return ["E00", target]
    if len(expression) == 2 and expression[0] in {"S", "A", "K", "R"}:
        value = assignment[(expression[0], expression[1])]
        if expression[0] == "S":
            return ["E00", value]
        if expression[0] == "A":
            return ["E01", value]
        if expression[0] == "K":
            return ["E03", value]
        return value
    return [
        expression[0],
        *(_bind(item, target=target, assignment=assignment) for item in expression[1:]),
    ]


def _exact(
    expression: Any,
    result_type: str,
    target: int,
    rows: tuple[Any, ...],
    binding: Mapping[str, Any],
) -> tuple[bool, int]:
    checks = 0
    for row in rows:
        try:
            value = atomic._evaluate(  # noqa: SLF001
                expression,
                state=row.pre,
                next_values={},
                action=row.action,
                binding=binding,
            )
        except Exception:
            return False, checks
        checks += 1
        if result_type == "INT":
            if type(value) is not int or value != row.post[target]:
                return False, checks
        elif result_type == "FINITE_INT_SUPPORT":
            if not hasattr(value, "values") or row.post[target] not in value.values:
                return False, checks
        else:
            return False, checks
    return True, checks


def _instantiate(
    bank: Mapping[str, Any],
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    layout: Any,
) -> dict[str, Any]:
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, layout, canonical_occurrence=0
    )
    binding = atomic._derive_binding(aligned_rows, aligned_catalogue)  # noqa: SLF001
    domains_by_kind = {
        "S": tuple(range(len(aligned_rows[0].pre))),
        "A": tuple(range(len(aligned_catalogue[0].fields))),
        "K": tuple(sorted(binding["constants"])),
        "R": tuple(sorted(binding["relations"])),
    }
    exact_rows = []
    evaluations = 0
    for template in bank["selected_subprograms"]:
        symbols = _symbols(template["normalized_expression"])
        choices = [domains_by_kind[kind] for kind, _index in symbols]
        if any(not choice for choice in choices):
            continue
        for values in product(*choices):
            assignment = dict(zip(symbols, values, strict=True))
            for target in range(len(aligned_rows[0].pre)):
                expression = _bind(
                    template["normalized_expression"],
                    target=target,
                    assignment=assignment,
                )
                exact, checks = _exact(
                    expression, template["result_type"], target, aligned_rows, binding
                )
                evaluations += checks
                if exact:
                    exact_rows.append(
                        {
                            "template_signature_sha256": template[
                                "signature_sha256"
                            ],
                            "target_column": target,
                            "result_type": template["result_type"],
                            "bound_expression": expression,
                            "symbol_binding": [
                                {
                                    "symbol_kind": kind,
                                    "normalized_index": index,
                                    "bound_token": assignment[(kind, index)],
                                }
                                for kind, index in symbols
                            ],
                            "dependency_tokens": [
                                list(token)
                                for token in sorted(
                                    atomic._dependency_tokens(expression)  # noqa: SLF001
                                )
                            ],
                        }
                    )
    unique = {canonical_json_bytes(row): row for row in exact_rows}
    exact_rows = [unique[key] for key in sorted(unique)]
    relational = [
        row
        for row in exact_rows
        if any(token[0] == "E04" for token in row["dependency_tokens"])
    ]
    _require(bool(relational), "V148 no independent relational instantiation")
    payload = {
        "schema": "acfqp.anonymous_relational_template_instantiation.v147",
        "bank_id": BANK_ID,
        "bank_verification_id": BANK_VERIFICATION_ID,
        "layout_id": layout.layout_id,
        "source_raw_transition_count": len(rows),
        "source_raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in rows])
        ).hexdigest(),
        "bank_selected_template_count": len(bank["selected_subprograms"]),
        "bank_selected_relational_template_count": sum(
            row.get("relation_symbol_count", 0) > 0
            for row in bank["selected_subprograms"]
        ),
        "observation_derived_binding": copy.deepcopy(binding),
        "exact_instantiations": exact_rows,
        "exact_instantiation_count": len(exact_rows),
        "exact_relational_instantiation_count": len(relational),
        "template_binding_evaluation_events": evaluations,
        "constant_and_relation_symbol_names_supplied_by_bank": False,
        "target_coordinate_roles_supplied_by_bank": False,
        "binding_derived_from_raw_observations": True,
        "exact_rows_are_program_proposals_not_planning_authority": True,
        "new_target_outcomes_accessed": False,
        "complete_world_model_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    return {
        **payload,
        "instantiation_id": _content_id(_V147_INSTANTIATION_DOMAIN, payload),
    }


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
        "artifact_library_index_prefix_bits": max(
            1, ceil(log2(max(2, template_count)))
        ),
        "artifact_branch_code": "BANK_INDEX_PLUS_OBSERVATION_DERIVED_ANONYMOUS_BINDING",
        "uniform_tail_branch_code": "FULL_TYPED_ANONYMOUS_AST",
        "fixed_mixture_weight_supplied_by_target": False,
        "target_outcomes_accessed_by_calibration": False,
    }
    return {
        **payload,
        "calibration_id": _content_id(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_CALIBRATION_V148_DOMAIN,
            payload,
        ),
    }


def _prepare_search(
    rows: tuple[Any, ...],
    catalogue: tuple[Any, ...],
    instantiation: Mapping[str, Any],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    layout = discover_generic_layout_v5(
        rows, catalogue, layout_domain=config["generic_domains"]["layout"]
    )
    _require(layout.layout_id == instantiation["layout_id"], "V148 layout join changed")
    aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
        rows, catalogue, layout, canonical_occurrence=0
    )
    grouped = atomic._grouped(aligned_rows)  # noqa: SLF001
    binding = atomic._derive_binding(grouped[0], aligned_catalogue)  # noqa: SLF001
    _require(
        binding == instantiation["observation_derived_binding"],
        "V148 binding join changed",
    )
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
    exact_by_target = {}
    evaluations = 0
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
        exact_by_target[target] = exact
        evaluations += count
    return {
        "layout": layout,
        "aligned_rows": aligned_rows,
        "bindings": bindings,
        "state_width": state_width,
        "action_width": action_width,
        "artifact": artifact,
        "calibration": _calibration(instantiation["bank_selected_template_count"]),
        "exact_by_target": exact_by_target,
        "evaluations": evaluations,
    }


def _synthesize(
    rows: tuple[Any, ...],
    instantiation: Mapping[str, Any],
    prepared: Mapping[str, Any],
    *,
    enabled: bool,
    labels: int,
    minimum: int,
) -> tuple[PartialFactorCandidateV15, dict[str, int]]:
    layout = prepared["layout"]
    bindings = prepared["bindings"]
    state_width = prepared["state_width"]
    action_width = prepared["action_width"]
    artifact = prepared["artifact"]
    calibration = prepared["calibration"]
    assignments = []
    ambiguity = []
    selected_count = selected_relational = 0
    for target in range(state_width):
        candidates = []
        for depth, result_type, expression in prepared["exact_by_target"][target]:
            if result_type not in {"INT", "FINITE_INT_SUPPORT"}:
                continue
            encoded = canonical_json_bytes(expression)
            artifact_row = artifact.get((target, encoded))
            signature = artifact_row[0] if artifact_row is not None else None
            relational = artifact_row[1] if artifact_row is not None else False
            classification = _classification(expression)
            generic_bits = _ast_bits(expression)
            reference_bits = (
                calibration["artifact_library_index_prefix_bits"]
                + _dependency_binding_bits(classification)
                if signature is not None
                else None
            )
            rank = (
                1 + (reference_bits if reference_bits is not None else generic_bits)
                if enabled
                else generic_bits,
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
                    relational,
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
            relational,
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
        selected_count += int(is_artifact)
        selected_relational += int(is_artifact and relational)
        ambiguity.append(
            {
                "target_column": target,
                "same_generic_hypothesis_pool_size": len(candidates),
                "artifact_expression_count_in_same_pool": artifact_count,
                "artifact_expression_present_in_pool": artifact_count > 0,
                "artifact_expression_selected": is_artifact,
                "relational_artifact_expression_selected": is_artifact and relational,
                "generic_ast_prefix_bits": generic_bits,
                "artifact_reference_prefix_bits": reference_bits,
                "selection_rule": "OPTIONAL_PREFIX_CODE_BITS_THEN_DEPTH_THEN_AST_MDL_THEN_BYTES",
            }
        )
    _require(len(assignments) >= minimum, "V148 independent candidate is too small")
    payload = {
        "schema": "acfqp.anonymous_relational_prior_partial_candidate.v148",
        "source_factor_library_id": BANK_ID,
        "source_factor_library_verification_id": BANK_VERIFICATION_ID,
        "anonymous_relational_instantiation_id": instantiation["instantiation_id"],
        "factor_prior_enabled": enabled,
        "only_arm_switch_is_anonymous_relational_prior": True,
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
        "minimum_factor_assignment_count": minimum,
        "artifact_expression_selected_count": selected_count,
        "relational_artifact_expression_selected_count": selected_relational,
        "robust_dictionary_calibration": calibration,
        "normalized_artifact_uniform_mixture_prior_present": enabled,
        "constant_relation_and_coordinate_bindings_derived_from_raw_observations": True,
        "target_slot_inventory_supplied_by_prior": False,
        "semantic_names_used": False,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    document = {
        **payload,
        "candidate_id": _content_id(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_CANDIDATE_V148_DOMAIN,
            payload,
        ),
    }
    return (
        PartialFactorCandidateV15(
            document, layout, tuple(assignments), prepared["aligned_rows"]
        ),
        {
            "generic_atomic_expression_evaluations": prepared["evaluations"],
            "artifact_expression_selected_count": selected_count,
            "relational_artifact_expression_selected_count": selected_relational,
        },
    )


def _rebuild_acquisition(
    recorded: Mapping[str, Any],
    adapter: Any,
    bank: Mapping[str, Any],
    batches: tuple[tuple[Any, ...], ...],
    *,
    enabled: bool,
    config: Mapping[str, Any],
) -> tuple[PartialFactorCandidateV15, tuple[Any, ...]]:
    _verify_id(
        recorded,
        "acquisition_id",
        domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_ACQUISITION_V148_DOMAIN,
    )
    target = recorded["ground_support_labels"]
    source = execution = instantiation = None
    issued = invalidated = disagreements = epoch = successes = 0
    previous_id = None
    history = []
    derivation = binding_compute = selected = selected_relational = replay_errors = 0
    rows = []
    accepting = None
    terminal_stop = None
    for labels, batch in enumerate(batches[:target], 1):
        rows.extend(batch)
        current = tuple(rows)
        if accepting is None and any(row.terminal_acceptance_after is True for row in batch):
            accepting = labels
        if source is not None:
            replay = exact_generic_artifact_factor_replay_v121(
                execution, current, adapter.catalogue
            )
            if replay["exact"] is True:
                successes += 1
            else:
                previous_id = source.public_document["candidate_id"]
                source = execution = instantiation = None
                invalidated += 1
                epoch += 1
                successes = 0
        if source is None:
            try:
                layout = discover_generic_layout_v5(
                    current,
                    adapter.catalogue,
                    layout_domain=config["generic_domains"]["layout"],
                )
                instantiation = _instantiate(bank, current, adapter.catalogue, layout)
                prepared = _prepare_search(current, adapter.catalogue, instantiation, config)
                source, compute = _synthesize(
                    current,
                    instantiation,
                    prepared,
                    enabled=enabled,
                    labels=labels,
                    minimum=config["minimum_reusable_factor_count"],
                )
                execution = previous._lower_candidate(  # noqa: SLF001
                    source, current, adapter.catalogue
                )
                issued = labels
                derivation += compute["generic_atomic_expression_evaluations"]
                binding_compute += instantiation["template_binding_evaluation_events"]
                selected = compute["artifact_expression_selected_count"]
                selected_relational = compute[
                    "relational_artifact_expression_selected_count"
                ]
                if previous_id is not None and source.public_document["candidate_id"] != previous_id:
                    disagreements += 1
            except Exception as error:
                source = execution = instantiation = None
                history.append(
                    {
                        "support_label_count": labels,
                        "candidate_available": False,
                        "constructor_error_type": previous._acquisition_error_name(  # noqa: SLF001
                            error
                        ),
                    }
                )
                continue
        try:
            stop = previous._relational_stop(  # noqa: SLF001
                source,
                execution,
                current,
                adapter.catalogue,
                enabled=enabled,
                epoch=epoch,
                invalidated=invalidated,
                successes=successes,
                alpha=config["global_alpha_denominator"],
            )
        except Exception as error:
            history.append(
                {
                    "support_label_count": labels,
                    "candidate_available": True,
                    "candidate_id": source.public_document["candidate_id"],
                    "candidate_stop_replayable": False,
                    "candidate_replay_error_type": previous._acquisition_error_name(  # noqa: SLF001
                        error
                    ),
                }
            )
            previous_id = source.public_document["candidate_id"]
            source = execution = instantiation = None
            invalidated += 1
            epoch += 1
            successes = 0
            replay_errors += 1
            continue
        history.append(
            {
                "support_label_count": labels,
                "candidate_available": True,
                "candidate_id": source.public_document["candidate_id"],
                "stopped_by_shared_rule": stop["stopped"],
                "accepting_projection_available": accepting is not None,
            }
        )
        if labels == target:
            terminal_stop = stop
    _require(
        source is not None
        and execution is not None
        and instantiation is not None
        and terminal_stop is not None
        and terminal_stop["stopped"] is True
        and accepting is not None,
        "V148 acquisition did not independently close",
    )
    raw_rows = tuple(rows)
    payload = {
        "schema": "acfqp.anonymous_relational_factor_bank_acquisition_arm.v148",
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": "ANONYMOUS_RELATIONAL_FACTOR_PRIOR_ON" if enabled else "STRICT_NO_PRIOR",
        "factor_prior_enabled": enabled,
        "v146_factor_bank_id": BANK_ID,
        "v146_independent_verification_id": BANK_VERIFICATION_ID,
        "anonymous_relational_instantiation": instantiation,
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
        "ground_support_labels": target,
        "raw_transition_count": len(raw_rows),
        "raw_transition_sha256": hashlib.sha256(
            canonical_json_bytes([row.to_document() for row in raw_rows])
        ).hexdigest(),
        "candidate": dict(source.public_document),
        "execution_projection": dict(execution.public_document),
        "candidate_issued_at_support_label": issued,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": disagreements,
        "candidate_replay_error_count": replay_errors,
        "candidate_epoch": epoch,
        "post_issuance_exact_prediction_success_count": successes,
        "first_accepting_observation_label": accepting,
        "terminal_stop_update": dict(terminal_stop),
        "stopping_history": history,
        "derivation_compute_events": derivation,
        "template_binding_evaluation_events": binding_compute,
        "artifact_expression_selected_count": selected,
        "relational_artifact_expression_selected_count": selected_relational,
        "sample_labels_and_derivation_compute_separate": True,
        "complete_world_model_claimed": False,
        "planning_authority_present": False,
    }
    rebuilt = {
        **payload,
        "acquisition_id": _content_id(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_ACQUISITION_V148_DOMAIN,
            payload,
        ),
    }
    if rebuilt != recorded:
        changed = sorted(
            key for key in set(rebuilt) | set(recorded) if rebuilt.get(key) != recorded.get(key)
        )
        detail = None
        if "stopping_history" in changed:
            detail = next(
                (
                    (index, left, right)
                    for index, (left, right) in enumerate(
                        zip(rebuilt["stopping_history"], recorded["stopping_history"], strict=False)
                    )
                    if left != right
                ),
                (len(rebuilt["stopping_history"]), len(recorded["stopping_history"])),
            )
        _fail(f"V148 acquisition reconstruction changed: {changed}; history={detail!r}")
    return execution, raw_rows


def _verify_sequence(
    sequence: Mapping[str, Any],
    candidate: PartialFactorCandidateV15,
    acquisition_rows: tuple[Any, ...],
    *,
    seed: int,
) -> dict[str, int]:
    _verify_id(sequence, "sequence_id", _V144R1_SEQUENCE_DOMAIN)
    _require(
        sequence["schema"]
        == "acfqp.certificate_local_relational_overlay_owned_sequence.v144r1"
        and sequence["partial_candidate_id"] == candidate.public_document["candidate_id"]
        and sequence["family"] == FAMILY
        and sequence["seed"] == seed
        and tuple(sequence["episode_indices"]) == EXPECTED_EPISODES
        and sequence["total_query_local_exact_overlay_edge_count"] == 0,
        "V148 sequence identity changed",
    )
    dependency = sequence["program_branch_dependency_receipt"]
    _require(
        sequence["program_branch_dependency_receipt_id"]
        == dependency["dependency_receipt_id"]
        and dependency["partial_candidate_id"] == candidate.public_document["candidate_id"]
        and dependency["compiled_factor_assignments"]
        == candidate.public_document["compiled_factor_assignments"],
        "V148 dependency receipt changed",
    )
    actions = {
        action["action_key"]: tuple(action["canonical_anonymous_fields"])
        for action in dependency["canonical_action_catalogue"]
    }
    deduplicated = {
        previous.base.model._raw_key(row.to_document()): row.to_document()  # noqa: SLF001
        for row in acquisition_rows
    }
    current = {key: deduplicated[key] for key in sorted(deduplicated)}
    base_before = previous.base.model._project(  # noqa: SLF001
        tuple(current.values()), candidate.public_document, actions
    )
    model_before = previous._wrap_model(base_before["model"])  # noqa: SLF001
    rules_before = tuple(
        previous.derive_generic_terminal_rules_v122(
            candidate,
            model_before["projected_edge_rows"],
            model_before["projected_terminal_rows"],
        )
    )
    state_before = previous._state_id(  # noqa: SLF001
        base_before["state_id"], model_before, rules_before
    )
    _require(
        model_before == sequence["quotient_models_before_each_episode"][0]
        and previous._bootstrap(  # noqa: SLF001
            base_before, state_before, model_before, tuple(current.values())
        )
        == sequence["bootstrap_receipt"]
        and previous._match(  # noqa: SLF001
            state_before, model_before, tuple(current.values()), None
        )
        == sequence["bootstrap_full_rebuild_match"],
        "V148 bootstrap reconstruction changed",
    )
    path_checks = direct = reused = 0
    for index, episode in enumerate(sequence["episodes"]):
        base_before = previous.base.model._project(  # noqa: SLF001
            tuple(current.values()), candidate.public_document, actions
        )
        model_before = previous._wrap_model(base_before["model"])  # noqa: SLF001
        rules_before = tuple(
            previous.derive_generic_terminal_rules_v122(
                candidate,
                model_before["projected_edge_rows"],
                model_before["projected_terminal_rows"],
            )
        )
        state_before = previous._state_id(  # noqa: SLF001
            base_before["state_id"], model_before, rules_before
        )
        _require(
            model_before == sequence["quotient_models_before_each_episode"][index]
            and episode["quotient_graph_before_episode"] == model_before
            and episode["standalone_model_state_id_before_episode"] == state_before,
            "V148 before-model reconstruction changed",
        )
        for wrapper in episode["abstract_plan_receipts"]:
            plan = wrapper["abstract_plan"]
            source = plan["planning_source"]
            if source in {
                "OBSERVATION_QUOTIENT_GRAPH",
                "COMPILED_FACTOR_PROGRAM_FALLBACK",
            }:
                previous.base._verify_id(  # noqa: SLF001
                    plan,
                    "legality_conditioned_quotient_plan_id",
                    previous.base._DOMAINS["plan"],  # noqa: SLF001
                )
                _require(
                    tuple(plan["embedded_projected_plan"]["terminal_projection_rule"])
                    == rules_before,
                    "V148 plan terminal rules changed",
                )
                path_checks += previous.base.generic._verify_plan(  # noqa: SLF001
                    plan,
                    wrapper["raw_state"],
                    candidate.public_document,
                    actions,
                    model_before,
                    rules_before,
                )
                direct += source == "COMPILED_FACTOR_PROGRAM_FALLBACK"
            elif source in {
                "COMPILED_FACTOR_PROGRAM_MEMOIZED",
                "DEPENDENCY_REVALIDATED_PRIOR_QUOTIENT_ORDER",
            }:
                reused += 1
                _require(
                    plan["partial_candidate_id"] == candidate.public_document["candidate_id"]
                    and plan["quotient_graph_id"] == model_before["quotient_graph_id"],
                    "V148 cached plan binding changed",
                )
            else:
                _fail("V148 unknown planning source")
        delta = tuple(episode["raw_incremental_transition_rows"])
        novel = tuple(
            row
            for row in delta
            if previous.base.model._raw_key(row) not in current  # noqa: SLF001
        )
        novel_facts = (
            previous.base.model._project(  # noqa: SLF001
                novel, candidate.public_document, actions
            )
            if novel
            else {"raw_keys": frozenset(), "checks": 0}
        )
        for row in delta:
            current[previous.base.model._raw_key(row)] = row  # noqa: SLF001
        base_after = previous.base.model._project(  # noqa: SLF001
            tuple(current.values()), candidate.public_document, actions
        )
        model_after = previous._wrap_model(base_after["model"])  # noqa: SLF001
        rules_after = tuple(
            previous.derive_generic_terminal_rules_v122(
                candidate,
                model_after["projected_edge_rows"],
                model_after["projected_terminal_rows"],
            )
        )
        state_after = previous._state_id(  # noqa: SLF001
            base_after["state_id"], model_after, rules_after
        )
        base_update = previous.base.model._update_receipt(  # noqa: SLF001
            base_before, base_after, delta, novel_facts
        )
        update = previous._update(  # noqa: SLF001
            state_before,
            state_after,
            model_before,
            model_after,
            base_update,
            len(delta),
        )
        match = previous._match(  # noqa: SLF001
            state_after, model_after, tuple(current.values()), update
        )
        _require(
            update == sequence["standalone_model_update_receipts"][index]
            and match == sequence["standalone_full_rebuild_match_receipts"][index]
            and episode["standalone_model_update_after_episode"] == update
            and episode["standalone_full_rebuild_match_after_episode"] == match
            and episode["quotient_graph_after_episode"] == model_after
            and episode["standalone_model_state_id_after_episode"] == state_after
            and model_after == sequence["quotient_models_after_each_episode"][index]
            and episode["success"] is True
            and episode["all_incremental_ground_queries_followed_failed_certificates"]
            is True
            and episode["planner_raw_transition_argument_present"] is False,
            f"V148 episode {index} reconstruction changed",
        )
    persistent = [current[key] for key in sorted(current)]
    _require(
        persistent == sequence["persistent_exact_overlay_rows"]
        and hashlib.sha256(canonical_json_bytes(persistent)).hexdigest()
        == sequence["persistent_exact_overlay_sha256"]
        and sequence["query_local_relational_overlay_model_present"] is True
        and sequence["source_partial_program_mutated_after_certificate_failure"] is False
        and sequence["every_uncompiled_edge_is_certificate_local"] is True
        and sequence["overlay_promoted_to_global_dynamics"] is False
        and sequence["query_local_overlay_used_as_safety_authority"] is False
        and sequence["every_new_ground_query_followed_a_failed_certificate"] is True
        and sequence[
            "planner_consumed_compiled_successor_without_raw_transition_argument"
        ]
        is True
        and sequence["complete_ground_world_model_synthesized"] is False
        and sequence["official_execution_allowed"] is False,
        "V148 sequence evidence boundary changed",
    )
    return {
        "plan_path_support_checks": path_checks,
        "direct_plan_count": direct,
        "reused_plan_count": reused,
        "certificate_local_labels": sequence[
            "certificate_ground_support_labels_paid_once"
        ],
        "query_local_exact_overlay_edges": sequence[
            "total_query_local_exact_overlay_edge_count"
        ],
        "execution_steps": sequence["execution_step_count"],
        "planning_compute_events": sequence["actual_new_abstract_planning_compute_events"],
    }


def _verify_occurrence(args: tuple[Mapping[str, Any], Mapping[str, Any]]) -> dict[str, Any]:
    row, bank = args
    family, seed = row["target_family"], row["seed"]
    _require(
        (family, seed) in EXPECTED_OCCURRENCES
        and row["schema"] == "acfqp.anonymous_relational_factor_bank_occurrence.v148"
        and tuple(row["episode_indices"]) == EXPECTED_EPISODES,
        "V148 occurrence identity changed",
    )
    _verify_id(
        row,
        "occurrence_id",
        domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_OCCURRENCE_V148_DOMAIN,
    )
    config = maintenance_cascade_config_v144()
    config["families"][FAMILY]["maximum_acquisition_labels"] = 1_024
    adapter = build_maintenance_cascade_adapter_v144(seed, config)
    prior_doc = row["anonymous_relational_factor_prior_acquisition"]
    strict_doc = row["strict_no_prior_acquisition"]
    stream = previous.base.path_predecessor._path_first_batches(adapter)  # noqa: SLF001
    batches = tuple(next(stream) for _ in range(strict_doc["ground_support_labels"]))
    prior_candidate, prior_rows = _rebuild_acquisition(
        prior_doc, adapter, bank, batches, enabled=True, config=config
    )
    strict_candidate, strict_rows = _rebuild_acquisition(
        strict_doc, adapter, bank, batches, enabled=False, config=config
    )
    prior_sequence = _verify_sequence(
        row["anonymous_relational_factor_prior_owned_sequence"],
        prior_candidate,
        prior_rows,
        seed=seed,
    )
    strict_sequence = _verify_sequence(
        row["strict_no_prior_owned_sequence"], strict_candidate, strict_rows, seed=seed
    )
    reduction = strict_doc["ground_support_labels"] - prior_doc["ground_support_labels"]
    _require(
        row["paired_label_reduction"] == reduction
        and row["sample_efficiency_direction"]
        == ("POSITIVE" if reduction > 0 else "NEGATIVE" if reduction < 0 else "ZERO")
        and row["registered_gate"]["passed"] is True
        and row["registered_gate"][
            "anonymous_relational_template_selected_in_prior_arm"
        ]
        is True
        and row["registered_gate"][
            "planner_consumes_lowered_relational_execution_projection"
        ]
        is True
        and row["registered_gate"]["sound_certificate_local_recovery_union"] is True
        and row["complete_ground_world_model_synthesized"] is False
        and row["arbitrary_unseen_domain_transfer_claimed"] is False
        and row["official_execution_allowed"] is False
        and row["official_scalar_cost"] is None
        and row["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN",
        "V148 occurrence Gate changed",
    )
    return {
        "occurrence_id": row["occurrence_id"],
        "family": family,
        "seed": seed,
        "prior_labels": prior_doc["ground_support_labels"],
        "strict_labels": strict_doc["ground_support_labels"],
        "labels_avoided": reduction,
        "prior_sequence": prior_sequence,
        "strict_sequence": strict_sequence,
        "accounting": row["accounting"],
    }


def freeze_anonymous_relational_factor_bank_verification_v148(
    campaign_raw: bytes,
    preregistration_raw: bytes,
    bank_raw: bytes,
    bank_verification_raw: bytes,
) -> bytes:
    campaign = loads_canonical_json(campaign_raw)
    registration = loads_canonical_json(preregistration_raw)
    bank = loads_canonical_json(bank_raw)
    bank_verification = loads_canonical_json(bank_verification_raw)
    _require(
        canonical_json_bytes(campaign) == campaign_raw
        and len(campaign_raw) == CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_raw).hexdigest() == CAMPAIGN_SHA256
        and campaign.get("campaign_id") == CAMPAIGN_ID,
        "V148 frozen campaign identity changed",
    )
    _verify_id(
        campaign,
        "campaign_id",
        domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_CAMPAIGN_V148_DOMAIN,
    )
    _require(
        canonical_json_bytes(registration) == preregistration_raw
        and len(preregistration_raw) == PREREGISTRATION_BYTE_COUNT
        and hashlib.sha256(preregistration_raw).hexdigest() == PREREGISTRATION_SHA256
        and registration.get("preregistration_id") == PREREGISTRATION_ID,
        "V148 frozen preregistration identity changed",
    )
    _verify_id(
        registration,
        "preregistration_id",
        domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_PREREGISTRATION_V148_DOMAIN,
    )
    _require(
        canonical_json_bytes(bank) == bank_raw
        and len(bank_raw) == BANK_BYTE_COUNT
        and hashlib.sha256(bank_raw).hexdigest() == BANK_SHA256
        and bank.get("bank_id") == BANK_ID
        and canonical_json_bytes(bank_verification) == bank_verification_raw
        and len(bank_verification_raw) == BANK_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(bank_verification_raw).hexdigest()
        == BANK_VERIFICATION_SHA256
        and bank_verification.get("verification_id") == BANK_VERIFICATION_ID
        and bank_verification.get("bank_id") == BANK_ID
        and registration["frozen_v146_factor_bank"] == bank
        and registration["frozen_v146_independent_verification"] == bank_verification
        and registration["target_occurrences"]
        == [{"family": family, "seed": seed} for family, seed in EXPECTED_OCCURRENCES]
        and tuple(registration["target_episode_indices"]) == EXPECTED_EPISODES
        and registration["target_worker_count"] == 2
        and registration["claim_boundary"]["target_outcomes_accessed"] is False,
        "V148 frozen source bank or registered contract changed",
    )
    with ProcessPoolExecutor(max_workers=2) as executor:
        rows = tuple(
            executor.map(
                _verify_occurrence,
                ((row, bank) for row in campaign["target_occurrences"]),
            )
        )
    _require(
        tuple((row["family"], row["seed"]) for row in rows) == EXPECTED_OCCURRENCES
        and campaign["target_occurrence_ids"]
        == [row["occurrence_id"] for row in rows],
        "V148 occurrence inventory changed",
    )
    numeric = [
        key for key, value in rows[0]["accounting"].items() if type(value) is int
    ]
    accounting = {key: sum(row["accounting"][key] for row in rows) for key in numeric}
    accounting.update(
        sample_labels_execution_steps_derivation_and_planning_compute_separate=True,
        scalar_cost_aggregation_performed=False,
    )
    reductions = tuple(row["labels_avoided"] for row in rows)
    local_labels = (
        accounting["anonymous_relational_prior_certificate_local_labels"]
        + accounting["strict_no_prior_certificate_local_labels"]
    )
    gate = campaign["registered_gate"]
    _require(
        campaign["preregistration_id"] == PREREGISTRATION_ID
        and campaign["accounting"] == accounting
        and campaign["incompatible_schema_no_transfer_control"]
        == incompatible_schema_no_transfer_control_v99()
        and gate["passed"] is True
        and gate["aggregate_paired_acquisition_label_reduction"]
        == sum(reductions)
        == 48
        and gate["positive_reduction_occurrence_count"] == 6
        and gate["zero_reduction_occurrence_count"] == 0
        and gate["negative_reduction_occurrence_count"] == 0
        and gate["certificate_failure_local_recovery_exercised_at_least_once"]
        is (local_labels > 0)
        and local_labels == 46
        and accounting["anonymous_relational_prior_query_local_overlay_edges"]
        + accounting["strict_no_prior_query_local_overlay_edges"]
        == 0
        and campaign["registered_workload_sample_efficiency_improvement_observed"]
        is True
        and campaign["complete_ground_world_model_synthesized"] is False
        and campaign["arbitrary_unseen_domain_transfer_claimed"] is False
        and campaign["official_execution_allowed"] is False
        and campaign["official_scalar_cost"] is None
        and campaign["official_N_break_even"] is None
        and campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN",
        "V148 aggregate Gate changed",
    )
    payload = {
        "schema": "acfqp.anonymous_relational_factor_bank_verification.v148",
        "campaign_id": CAMPAIGN_ID,
        "preregistration_id": PREREGISTRATION_ID,
        "v146_factor_bank_id": BANK_ID,
        "v146_independent_verification_id": BANK_VERIFICATION_ID,
        "verified_occurrences": list(rows),
        "verified_accounting": accounting,
        "producer_free_anonymous_constant_relation_and_coordinate_binding_reconstruction": True,
        "producer_free_matched_candidate_and_stop_reconstruction": True,
        "producer_free_relational_expression_lowering_reconstruction": True,
        "producer_free_model_epoch_and_local_recovery_receipt_reconstruction": True,
        "producer_free_abstract_plan_support_reconstruction": True,
        "registered_workload_sample_efficiency_improvement_independently_verified": True,
        "sample_efficiency_improvement_claim_scope": campaign[
            "sample_efficiency_improvement_claim_scope"
        ],
        "complete_world_model_claimed": False,
        "arbitrary_unseen_domain_transfer_claimed": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": domains.extension_content_id_v148(
            domains.CONSTRUCTION_K7_ANONYMOUS_RELATIONAL_PRIOR_VERIFICATION_V148_DOMAIN,
            payload,
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64:
        _require(
            document["verification_id"] == VERIFICATION_ID
            and len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
            and hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256,
            "V148 frozen verification changed",
        )
    return raw


__all__ = (
    "VERIFICATION_ID",
    "freeze_anonymous_relational_factor_bank_verification_v148",
)
