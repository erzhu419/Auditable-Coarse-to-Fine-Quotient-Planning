"""Adaptive acquisition driven by abstract-successor candidate disagreement."""

from __future__ import annotations

import copy
import hashlib
from itertools import product
import math
from typing import Any, Mapping, NoReturn

from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp import generic_frontier_prequential_acquisition_v53 as v53
from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp import generic_prequential_role_free_acquisition_v37 as v37
from acfqp.generic_context_stratified_schedule_v55 import (
    schedule_context_stratified_queries_v55,
)
from acfqp.generic_contextual_ordinal_frontier_acquisition_v54 import _readiness
from acfqp.generic_contextual_ordinal_residual_v54 import (
    _supports,
    _value,
    predict_version_space_group_v54,
)
from acfqp.generic_relational_terminal_program_v28 import (
    evaluate_relational_terminal_program_v28,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    TERMINAL_CLASS_UNIVERSE_V38,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericProjectedDisagreementAcquisitionV56Error(ValueError):
    pass


_ACQUISITION_DOMAIN = b"acfqp:generic-projected-disagreement-acquisition:v56\x00"
_BUNDLE_DOMAIN = b"acfqp:projected-disagreement-contextual-acquisition:v56\x00"


def _fail(message: str) -> NoReturn:
    raise GenericProjectedDisagreementAcquisitionV56Error(message)


def _leaf_tokens(tree: Mapping[str, Any]) -> set[int]:
    kind = tree.get("kind") if type(tree) is dict else None
    if kind == "LEAF":
        token = tree.get("status_token")
        if type(token) is not int:
            _fail("V56 terminal leaf changed")
        return {token}
    if kind == "RELATION":
        return _leaf_tokens(tree.get("when_true")) | _leaf_tokens(
            tree.get("when_false")
        )
    _fail("V56 terminal tree changed")


def projected_disagreement_score_v56(
    source_complete_evidence: Mapping[str, Any],
    group: list[dict[str, Any]],
    program: Mapping[str, Any],
    version_spaces: list[dict[str, Any]],
) -> dict[str, Any]:
    layout = source_complete_evidence.get("layout")
    assignments = source_complete_evidence.get("known_partial_factor_assignments")
    frontier = program.get("decision_tree_candidate_frontier")
    status_target = program.get("status_target_column")
    if (
        type(layout) is not dict
        or type(assignments) is not list
        or type(frontier) is not list
        or not frontier
        or type(status_target) is not int
        or type(group) is not list
        or not group
    ):
        _fail("V56 projected-disagreement inventory changed")
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V56 layout projection changed")
    first = group[0]
    selected = first.get("selected_action") if type(first) is dict else None
    pre = first.get("pre_vector") if type(first) is dict else None
    action = selected.get("anonymous_fields") if type(selected) is dict else None
    context = first.get("contextual_source_member_index") if type(first) is dict else None
    if (
        type(pre) is not list
        or type(action) is not list
        or type(context) is not int
        or any(row.get("contextual_source_member_index") != context for row in group)
    ):
        _fail("V56 query projection changed")
    canonical_state = tuple(pre[index] for index in state_order)
    canonical_action = tuple(action[index] for index in action_order)
    supports = _supports(source_complete_evidence)
    partial = {row.get("target_column"): row for row in assignments}
    residual = {
        row.get("target_column"): row.get("batch_exact_candidate_frontier")
        for row in version_spaces
        if type(row) is dict
    }
    if None in partial or None in residual or set(partial) & set(residual):
        _fail("V56 modeled-coordinate inventory changed")
    targets = sorted((*partial, *residual))
    coordinate_supports = []
    for target in targets:
        if target in partial:
            values = v42._partial_support(  # noqa: SLF001
                partial[target], canonical_state, canonical_action
            )
        else:
            candidates = residual[target]
            if type(candidates) is not list or not candidates:
                _fail("V56 residual frontier changed")
            values_set = set()
            for candidate in candidates:
                values_set.update(
                    _value(
                        candidate.get("normalized_expression"),
                        canonical_state,
                        canonical_action,
                        target,
                        candidate.get("action_field_binding"),
                        candidate.get("anonymous_integer_constant_binding"),
                        context,
                        supports,
                    )
                )
            values = tuple(sorted(values_set))
        if not values:
            _fail("V56 projected coordinate support became empty")
        coordinate_supports.append(values)
    trees = []
    token_universe = set()
    for row in frontier:
        tree = row.get("decision_tree") if type(row) is dict else None
        if type(tree) is not dict:
            _fail("V56 terminal frontier changed")
        trees.append(tree)
        token_universe.update(_leaf_tokens(tree))
    projected_states = []
    for values in product(*coordinate_supports):
        base = list(canonical_state)
        for target, value in zip(targets, values, strict=True):
            base[target] = value
        for token in sorted(token_universe):
            row = list(base)
            row[status_target] = token
            projected_states.append(tuple(row))
    per_state_disagreement = []
    evaluation_count = 0
    for state in projected_states:
        predictions = []
        for tree in trees:
            result = evaluate_relational_terminal_program_v28(
                {
                    "schema": "acfqp.generic_relational_terminal_program.v28",
                    "decision_tree": tree,
                },
                state,
            )
            predictions.append(
                (result["terminal_class"], result["status_token"])
            )
            evaluation_count += 1
        distinct = len(set(predictions))
        if distinct > 1:
            per_state_disagreement.append(distinct - 1)
    return {
        "candidate_disagreement_score": sum(per_state_disagreement),
        "projected_disagreement_state_count": len(per_state_disagreement),
        "projected_state_count": len(projected_states),
        "terminal_candidate_count": len(trees),
        "projection_compute_events": evaluation_count,
        "pre_state_and_action_only_query_projection": True,
        "unacquired_post_state_or_label_accessed": False,
    }


def acquire_projected_disagreement_frontiers_v56(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    if (
        type(source_complete_evidence) is not dict
        or type(source_complete_evidence.get("known_partial_factor_assignments"))
        is not list
        or type(required_terminal_classes) is not tuple
        or tuple(sorted(set(required_terminal_classes))) != required_terminal_classes
        or not required_terminal_classes
        or any(value not in TERMINAL_CLASS_UNIVERSE_V38 for value in required_terminal_classes)
        or type(maximum_exact_instantiations) is not int
        or not 1 <= maximum_exact_instantiations <= 128
        or type(confidence_denominator) is not int
        or confidence_denominator < 2
    ):
        _fail("V56 acquisition inventory changed")
    layout = source_complete_evidence.get("layout")
    unknown = source_complete_evidence.get("unknown_residual_target_columns")
    if type(layout) is not dict or type(unknown) is not list:
        _fail("V56 source evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V56 state layout changed")
    base_schedule = schedule_context_stratified_queries_v55(
        source_complete_evidence
    )
    base_groups = v42._groups(  # noqa: SLF001
        base_schedule["scheduled_raw_transition_rows"]
    )
    if len(base_groups) < 3:
        _fail("V56 needs training, prequential, and held-out queries")
    remaining = [(index, group) for index, group in enumerate(base_groups)]
    required_set = set(required_terminal_classes)
    confidence_bits = math.ceil(math.log2(confidence_denominator))
    acquired = []
    attempts = []
    terminal_ledger = []
    residual_ledger = []
    selection_ledger = []
    active = None
    selected_program = None
    selected_spaces = None
    stop = None
    retired = 0
    while remaining:
        if active is None:
            selected_offset = 0
            score_rows = []
            selection_mode = "BASE_CONTEXT_RELATION_ORDER"
        else:
            score_rows = []
            for offset, (base_index, group) in enumerate(remaining):
                score = projected_disagreement_score_v56(
                    source_complete_evidence,
                    group,
                    active["program"],
                    active["version_spaces"],
                )
                score_rows.append((offset, base_index, score))
            selected_offset = min(
                score_rows,
                key=lambda row: (
                    -row[2]["candidate_disagreement_score"],
                    -row[2]["projected_disagreement_state_count"],
                    row[1],
                ),
            )[0]
            selection_mode = "MAX_PROJECTED_CANDIDATE_DISAGREEMENT"
        base_index, group = remaining.pop(selected_offset)
        query_index = len(selection_ledger)
        selected_score = (
            None
            if active is None
            else next(row[2] for row in score_rows if row[0] == selected_offset)
        )
        selection_ledger.append(
            {
                "query_index": query_index,
                "base_context_stratified_query_index": base_index,
                "selection_mode": selection_mode,
                "candidate_program_id_before_outcome": None if active is None else active["program_id"],
                "selected_query_score": selected_score,
                "candidate_query_score_evaluation_count": len(score_rows),
                "all_candidate_projection_compute_events": sum(
                    row[2]["projection_compute_events"] for row in score_rows
                ),
                "remaining_query_count_before_selection": len(remaining) + 1,
                "selection_frozen_before_query_outcome": True,
                "unacquired_post_state_or_label_accessed": False,
            }
        )
        if active is not None:
            terminal_prediction = v53._predict_frontier_group(  # noqa: SLF001
                active["program"], group, order
            )
            residual_prediction = predict_version_space_group_v54(
                source_complete_evidence, group, active["version_spaces"]
            )
            terminal_ledger.append(
                {
                    "query_index": query_index,
                    "candidate_program_id_before_outcome": active["program_id"],
                    "prediction": terminal_prediction,
                    "prediction_frozen_before_query_outcome": True,
                }
            )
            residual_ledger.append(
                {
                    "query_index": query_index,
                    "candidate_program_id_before_outcome": active["program_id"],
                    "prediction": residual_prediction,
                    "every_residual_candidate_frozen_before_query_outcome": True,
                }
            )
            if terminal_prediction["query_exact"] and residual_prediction["query_exact"]:
                active["evidence_bits"] += 1
            else:
                active = None
                retired += 1
        acquired.extend(group)
        count = len(selection_ledger)
        if (
            active is not None
            and active["evidence_bits"] >= active["required_evidence_bits"]
            and remaining
        ):
            selected_program = active["program"]
            selected_spaces = active["version_spaces"]
            stop = count
            break
        if active is None and len(remaining) >= 2:
            observed_classes = tuple(
                sorted({v35._label(row) for row in acquired})  # noqa: SLF001
            )
            class_coverage = set(observed_classes) == required_set
            constructed = v37._candidate(  # noqa: SLF001
                layout,
                unknown,
                acquired,
                role_free_template_library=role_free_template_library,
                maximum_exact_instantiations=maximum_exact_instantiations,
                confidence_denominator=confidence_denominator,
            )
            program = constructed.get("candidate_program")
            readiness, spaces = (
                _readiness(source_complete_evidence, unknown, acquired, program)
                if type(program) is dict
                else _readiness(source_complete_evidence, unknown, acquired, {})
            )
            public = {
                key: value for key, value in constructed.items()
                if key != "candidate_program"
            }
            public.update(
                training_query_count=count,
                observed_terminal_classes=list(observed_classes),
                required_terminal_classes=list(required_terminal_classes),
                semantic_class_coverage_complete=class_coverage,
                observed_successor_training_calibration_required=True,
                terminal_and_residual_frontiers_prequentially_checked=True,
                compiler_readiness=readiness,
                training_calibrated_after_all_acquisition_guards=(
                    class_coverage
                    and constructed.get("training_calibrated") is True
                    and type(program) is dict
                    and readiness["all_non_status_residual_version_spaces_nonempty"] is True
                ),
            )
            attempts.append(public)
            if public["training_calibrated_after_all_acquisition_guards"]:
                active = {
                    "program": program,
                    "program_id": constructed["candidate_program_id"],
                    "version_spaces": spaces,
                    "training_query_count": count,
                    "required_evidence_bits": confidence_bits
                    + public["selected_program_description_bits"],
                    "evidence_bits": 0,
                }
    heldout_groups = [group for _index, group in remaining]
    heldout = [row for group in heldout_groups for row in group]
    terminal_heldout_exact = (
        selected_program is not None
        and all(
            v53._predict_frontier_group(selected_program, group, order)["query_exact"]
            for group in heldout_groups
        )
    )
    residual_heldout_exact = (
        selected_spaces is not None
        and all(
            predict_version_space_group_v54(
                source_complete_evidence, group, selected_spaces
            )["query_exact"]
            for group in heldout_groups
        )
    )
    heldout_exact = terminal_heldout_exact and residual_heldout_exact
    status = (
        "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        if selected_program is not None and heldout_exact
        else "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        if selected_program is not None
        else "ABSTAINED_NO_PROJECTED_DISAGREEMENT_PROPOSAL"
    )
    payload = {
        "schema": "acfqp.generic_projected_disagreement_acquisition.v56",
        "arm": "ROLE_FREE_FACTOR_PRIOR_ON" if role_free_template_library is not None else "STRICT_NO_ROLE_FREE_FACTOR_PRIOR",
        "role_free_template_library_id": None if role_free_template_library is None else role_free_template_library.get("template_library_id"),
        "required_terminal_classes": list(required_terminal_classes),
        "source_context_stratified_query_schedule_id": base_schedule[
            "context_stratified_query_schedule_id"
        ],
        "adaptive_query_selection_ledger": selection_ledger,
        "executed_raw_transition_rows": copy.deepcopy(acquired),
        "executed_query_count": len(selection_ledger),
        "full_query_stream_ground_support_labels": len(base_groups),
        "proposal_attempts": attempts,
        "terminal_prequential_prediction_ledger": terminal_ledger,
        "residual_prequential_prediction_ledger": residual_ledger,
        "retired_failed_proposal_count": retired,
        "base_confidence_evidence_bits": confidence_bits,
        "stopped_physical_ground_support_labels": stop,
        "selected_terminal_program": selected_program,
        "selected_terminal_program_id": None if selected_program is None else selected_program["terminal_program_id"],
        "selected_residual_version_spaces": selected_spaces,
        "heldout_ground_query_count": len(heldout_groups),
        "heldout_raw_transition_row_count": len(heldout),
        "terminal_heldout_exact_prediction": terminal_heldout_exact,
        "residual_heldout_exact_prediction": residual_heldout_exact,
        "heldout_exact_prediction": heldout_exact,
        "status": status,
        "terminal_candidate_derivation_compute_events": sum(row.get("candidate_constructor_compute", 0) for row in attempts),
        "compiler_readiness_compute_events": sum(row["compiler_readiness"]["version_space_selection_compute_events"] for row in attempts),
        "query_selection_projection_compute_events": sum(
            row["all_candidate_projection_compute_events"]
            for row in selection_ledger
        ),
        "every_retained_terminal_frontier_candidate_prequentially_checked": True,
        "every_retained_residual_frontier_candidate_prequentially_checked": True,
        "every_retained_terminal_frontier_candidate_heldout_checked": True,
        "every_retained_residual_frontier_candidate_heldout_checked": True,
        "candidate_disagreement_scheduling_uses_only_abstract_successor_support": True,
        "unacquired_post_state_or_label_accessed_by_query_selection": False,
        "confirmation_budget_derived_from_candidate_mdl_and_confidence": True,
        "residual_successor_version_space_consensus_required_before_issuance": False,
        "heldout_rows_accessed_before_stop": False,
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "statistical_coverage_claimed": False,
        "empirical_version_space_promoted_to_global_dynamics": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "projected_disagreement_acquisition_id": hashlib.sha256(
            _ACQUISITION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_projected_disagreement_acquisition_v56(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    acquisition = acquire_projected_disagreement_frontiers_v56(
        source_complete_evidence,
        role_free_template_library=role_free_template_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.projected_disagreement_contextual_acquisition.v56",
        "projected_disagreement_acquisition": acquisition,
        "projected_disagreement_acquisition_id": acquisition[
            "projected_disagreement_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "adaptive_selection_uses_model_projected_successors": True,
        "all_terminal_and_residual_frontier_candidates_checked_prequentially": True,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "projected_disagreement_contextual_acquisition_id": hashlib.sha256(
            _BUNDLE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "acquire_projected_disagreement_frontiers_v56",
    "projected_disagreement_score_v56",
    "run_projected_disagreement_acquisition_v56",
)
