"""Acquire terminal and residual frontiers with contextual ordinal dynamics."""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp import generic_frontier_prequential_acquisition_v53 as v53
from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp import generic_prequential_role_free_acquisition_v37 as v37
from acfqp.generic_contextual_ordinal_residual_v54 import (
    predict_version_space_group_v54,
    version_space_v54,
)
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    TERMINAL_CLASS_UNIVERSE_V38,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericContextualOrdinalFrontierAcquisitionV54Error(ValueError):
    pass


_ACQUISITION_DOMAIN = b"acfqp:generic-contextual-ordinal-frontier-acquisition:v54\x00"
_BUNDLE_DOMAIN = b"acfqp:relation-covering-contextual-ordinal-frontier-acquisition:v54\x00"


def _fail(message: str) -> NoReturn:
    raise GenericContextualOrdinalFrontierAcquisitionV54Error(message)


def _readiness(
    evidence: Mapping[str, Any],
    unknown: list[int],
    acquired: list[dict[str, Any]],
    program: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    status_target = program.get("status_target_column")
    if type(status_target) is not int or status_target not in unknown:
        return (
            {
                "status_target_present_in_residual_inventory": False,
                "per_residual_coordinate": [],
                "all_non_status_residual_version_spaces_nonempty": False,
                "contextual_ordinal_candidate_present": False,
                "version_space_selection_compute_events": 0,
            },
            [],
        )
    groups = v42._groups(acquired)  # noqa: SLF001
    spaces = []
    public = []
    compute = 0
    for target in unknown:
        if target == status_target:
            continue
        frontier, evaluations = version_space_v54(evidence, groups, target)
        compute += evaluations
        spaces.append(
            {
                "target_column": target,
                "batch_exact_candidate_count": len(frontier),
                "batch_exact_candidate_frontier": frontier,
            }
        )
        public.append(
            {
                "target_column": target,
                "batch_exact_candidate_count": len(frontier),
                "batch_exact_candidate_frontier_sha256": hashlib.sha256(
                    canonical_json_bytes(frontier)
                ).hexdigest(),
                "contextual_ordinal_candidate_count": sum(
                    row["contextual_action_support_operator_used"] is True
                    for row in frontier
                ),
            }
        )
    return (
        {
            "status_target_present_in_residual_inventory": True,
            "per_residual_coordinate": public,
            "all_non_status_residual_version_spaces_nonempty": bool(public)
            and all(row["batch_exact_candidate_count"] > 0 for row in public),
            "contextual_ordinal_candidate_present": any(
                row["contextual_ordinal_candidate_count"] > 0 for row in public
            ),
            "version_space_selection_compute_events": compute,
        },
        spaces,
    )


def acquire_contextual_ordinal_frontiers_v54(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    if (
        type(source_complete_evidence) is not dict
        or source_complete_evidence.get(
            "contextual_action_supports_derived_from_catalogue_only"
        )
        is not True
        or source_complete_evidence.get(
            "unacquired_successor_or_terminal_used_for_action_supports"
        )
        is not False
        or type(required_terminal_classes) is not tuple
        or tuple(sorted(set(required_terminal_classes))) != required_terminal_classes
        or not required_terminal_classes
        or any(value not in TERMINAL_CLASS_UNIVERSE_V38 for value in required_terminal_classes)
        or type(maximum_exact_instantiations) is not int
        or not 1 <= maximum_exact_instantiations <= 128
        or type(confidence_denominator) is not int
        or confidence_denominator < 2
    ):
        _fail("V54 acquisition inventory changed")
    layout = source_complete_evidence.get("layout")
    unknown = source_complete_evidence.get("unknown_residual_target_columns")
    rows = source_complete_evidence.get("raw_transition_rows")
    if (
        type(layout) is not dict
        or type(unknown) is not list
        or unknown != sorted(set(unknown))
        or type(rows) is not list
        or not rows
    ):
        _fail("V54 source evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V54 state layout changed")
    groups = v35._groups(rows)  # noqa: SLF001
    if len(groups) < 3:
        _fail("V54 needs training, prequential, and held-out queries")

    confidence_bits = math.ceil(math.log2(confidence_denominator))
    required_set = set(required_terminal_classes)
    acquired: list[dict[str, Any]] = []
    attempts = []
    terminal_ledger = []
    residual_ledger = []
    active = None
    selected = None
    selected_spaces = None
    stop = None
    retired = 0
    for offset, group in enumerate(groups):
        count = offset + 1
        if active is not None:
            terminal_prediction = v53._predict_frontier_group(  # noqa: SLF001
                active["program"], group, order
            )
            residual_prediction = predict_version_space_group_v54(
                source_complete_evidence, group, active["version_spaces"]
            )
            terminal_ledger.append(
                {
                    "query_index": offset,
                    "candidate_program_id_before_outcome": active["program_id"],
                    "candidate_training_query_count": active["training_query_count"],
                    "prediction": terminal_prediction,
                    "prediction_frozen_before_query_outcome": True,
                }
            )
            residual_ledger.append(
                {
                    "query_index": offset,
                    "candidate_program_id_before_outcome": active["program_id"],
                    "candidate_training_query_count": active["training_query_count"],
                    "prediction": residual_prediction,
                    "every_residual_candidate_frozen_before_query_outcome": True,
                }
            )
            if terminal_prediction["query_exact"] and residual_prediction["query_exact"]:
                active["evidence_bits"] += 1
                active["confirmed_query_count"] += 1
            else:
                active = None
                retired += 1
        acquired.extend(group)
        if (
            active is not None
            and active["evidence_bits"] >= active["required_evidence_bits"]
            and count < len(groups)
        ):
            selected = active["program"]
            selected_spaces = active["version_spaces"]
            stop = count
            break
        if active is None and count < len(groups) - 1:
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
            public = {key: value for key, value in constructed.items() if key != "candidate_program"}
            public.update(
                training_query_count=count,
                observed_terminal_classes=list(observed_classes),
                required_terminal_classes=list(required_terminal_classes),
                semantic_class_coverage_complete=class_coverage,
                observed_successor_training_calibration_required=True,
                terminal_and_residual_frontiers_prequentially_checked=True,
                residual_successor_version_space_consensus_required=False,
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
                    "required_evidence_bits": (
                        confidence_bits
                        + public["selected_program_description_bits"]
                    ),
                    "evidence_bits": 0,
                    "confirmed_query_count": 0,
                }
    heldout = []
    terminal_heldout_exact = False
    residual_heldout_exact = False
    if selected is not None and selected_spaces is not None and stop is not None:
        heldout_groups = groups[stop:]
        heldout = [row for group in heldout_groups for row in group]
        terminal_heldout_exact = all(
            v53._predict_frontier_group(selected, group, order)["query_exact"]
            for group in heldout_groups
        )
        residual_heldout_exact = all(
            predict_version_space_group_v54(
                source_complete_evidence, group, selected_spaces
            )["query_exact"]
            for group in heldout_groups
        )
    heldout_exact = terminal_heldout_exact and residual_heldout_exact
    status = (
        "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
        if selected is not None and heldout_exact
        else "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        if selected is not None
        else "ABSTAINED_NO_CONTEXTUAL_ORDINAL_FRONTIER_PROPOSAL"
    )
    query_order = [
        {
            "pre_vector": group[0]["pre_vector"],
            "action_key": group[0]["selected_action"]["action_key"],
            "contextual_source_member_index": group[0]["contextual_source_member_index"],
            "raw_transition_row_count": len(group),
        }
        for group in groups
    ]
    payload = {
        "schema": "acfqp.generic_contextual_ordinal_frontier_acquisition.v54",
        "arm": "ROLE_FREE_FACTOR_PRIOR_ON" if role_free_template_library is not None else "STRICT_NO_ROLE_FREE_FACTOR_PRIOR",
        "role_free_template_library_id": None if role_free_template_library is None else role_free_template_library.get("template_library_id"),
        "required_terminal_classes": list(required_terminal_classes),
        "witness_blind_query_order": query_order,
        "witness_blind_query_order_sha256": hashlib.sha256(canonical_json_bytes(query_order)).hexdigest(),
        "full_query_stream_ground_support_labels": len(groups),
        "proposal_attempts": attempts,
        "terminal_prequential_prediction_ledger": terminal_ledger,
        "residual_prequential_prediction_ledger": residual_ledger,
        "retired_failed_proposal_count": retired,
        "base_confidence_evidence_bits": confidence_bits,
        "selected_program_description_bits_added_to_confirmation_budget": (
            None if active is None else active["required_evidence_bits"] - confidence_bits
        ),
        "required_prequential_evidence_bits": (
            None if active is None else active["required_evidence_bits"]
        ),
        "prequential_evidence_bits_per_exact_query": 1,
        "stopped_physical_ground_support_labels": stop,
        "selected_terminal_program": selected,
        "selected_terminal_program_id": None if selected is None else selected["terminal_program_id"],
        "selected_residual_version_spaces": selected_spaces,
        "heldout_ground_query_count": len(groups) - (stop or len(groups)),
        "heldout_raw_transition_row_count": len(heldout),
        "terminal_heldout_exact_prediction": terminal_heldout_exact,
        "residual_heldout_exact_prediction": residual_heldout_exact,
        "heldout_exact_prediction": heldout_exact,
        "status": status,
        "terminal_candidate_derivation_compute_events": sum(row.get("candidate_constructor_compute", 0) for row in attempts),
        "compiler_readiness_compute_events": sum(row["compiler_readiness"]["version_space_selection_compute_events"] for row in attempts),
        "terminal_program_semantics_apply_to_successors": True,
        "every_retained_terminal_frontier_candidate_prequentially_checked": True,
        "every_retained_residual_frontier_candidate_prequentially_checked": True,
        "every_retained_terminal_frontier_candidate_heldout_checked": True,
        "every_retained_residual_frontier_candidate_heldout_checked": True,
        "contextual_action_supports_derived_from_catalogue_only": True,
        "residual_successor_version_space_consensus_required_before_issuance": False,
        "nonempty_residual_version_space_required_before_issuance": True,
        "unacquired_successor_or_label_accessed_by_stopping_rule": False,
        "heldout_rows_accessed_before_stop": False,
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "confirmation_budget_derived_from_candidate_mdl_and_confidence": True,
        "statistical_coverage_claimed": False,
        "empirical_version_space_promoted_to_global_dynamics": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "contextual_ordinal_frontier_acquisition_id": hashlib.sha256(
            _ACQUISITION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_relation_covering_contextual_ordinal_acquisition_v54(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    schedule = schedule_relation_covering_queries_v39(source_complete_evidence)
    ordered = copy.deepcopy(source_complete_evidence)
    ordered["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
    acquisition = acquire_contextual_ordinal_frontiers_v54(
        ordered,
        role_free_template_library=role_free_template_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.relation_covering_contextual_ordinal_frontier_acquisition.v54",
        "query_schedule": schedule,
        "contextual_ordinal_frontier_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "contextual_ordinal_frontier_acquisition_id": acquisition["contextual_ordinal_frontier_acquisition_id"],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "all_terminal_and_residual_frontier_candidates_checked_prequentially": True,
        "contextual_action_supports_derived_from_catalogue_only": True,
        "residual_successor_consensus_used_as_acquisition_gate": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "relation_covering_contextual_ordinal_acquisition_id": hashlib.sha256(
            _BUNDLE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "acquire_contextual_ordinal_frontiers_v54",
    "run_relation_covering_contextual_ordinal_acquisition_v54",
)
