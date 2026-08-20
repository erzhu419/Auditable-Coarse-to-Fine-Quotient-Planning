"""Prequentially validate every retained terminal-frontier candidate.

V82 exposed that validating only the selected decision tree permits another
retained MDL-minimal tree to become inconsistent with later acquisition rows.
V53 freezes predictions for every frontier member before each outcome, retires
the proposal if any member is wrong, and applies the same all-frontier rule to
untouched held-out rows.  Residual successor candidates still need only be
nonempty and are all retained for robust planning.
"""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp import generic_prequential_role_free_acquisition_v37 as v37
from acfqp import generic_compiler_ready_acquisition_v52 as v52
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    TERMINAL_CLASS_UNIVERSE_V38,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericFrontierPrequentialAcquisitionV53Error(ValueError):
    pass


_ACQUISITION_DOMAIN = b"acfqp:generic-frontier-prequential-acquisition:v53\x00"
_BUNDLE_DOMAIN = b"acfqp:relation-covering-frontier-prequential-acquisition:v53\x00"


def _fail(message: str) -> NoReturn:
    raise GenericFrontierPrequentialAcquisitionV53Error(message)


def _predict_frontier_group(
    program: Mapping[str, Any],
    group: list[dict[str, Any]],
    order: list[int],
) -> dict[str, Any]:
    target = program.get("status_target_column")
    frontier = program.get("decision_tree_candidate_frontier")
    if type(target) is not int or type(frontier) is not list or not frontier:
        _fail("V53 terminal frontier changed")
    candidate_rows = []
    exact = True
    for candidate in frontier:
        tree = candidate.get("decision_tree") if type(candidate) is dict else None
        index = candidate.get("candidate_index") if type(candidate) is dict else None
        if type(tree) is not dict or type(index) is not int:
            _fail("V53 terminal candidate changed")
        predictions = []
        candidate_exact = True
        for row in group:
            post = row.get("post_vector")
            if type(post) is not list:
                _fail("V53 post-state evidence changed")
            state = tuple(post[column] for column in order)
            predicted_class, predicted_token = v35._evaluate(tree, state)  # noqa: SLF001
            observed_class = v35._label(row)  # noqa: SLF001
            observed_token = state[target]
            row_exact = (
                predicted_class == observed_class
                and predicted_token == observed_token
            )
            candidate_exact = candidate_exact and row_exact
            predictions.append(
                {
                    "predicted_terminal_class": predicted_class,
                    "observed_terminal_class": observed_class,
                    "predicted_status_token": predicted_token,
                    "observed_status_token": observed_token,
                    "exact": row_exact,
                }
            )
        exact = exact and candidate_exact
        candidate_rows.append(
            {
                "candidate_index": index,
                "decision_tree_sha256": candidate.get("decision_tree_sha256"),
                "candidate_exact": candidate_exact,
                "raw_row_predictions": predictions,
            }
        )
    return {
        "query_exact": exact,
        "all_terminal_frontier_candidates_exact": exact,
        "terminal_frontier_candidate_count": len(candidate_rows),
        "candidate_predictions": candidate_rows,
    }


def acquire_frontier_prequential_terminal_program_v53(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    if (
        type(source_complete_evidence) is not dict
        or type(required_terminal_classes) is not tuple
        or tuple(sorted(set(required_terminal_classes))) != required_terminal_classes
        or not required_terminal_classes
        or any(
            value not in TERMINAL_CLASS_UNIVERSE_V38
            for value in required_terminal_classes
        )
        or type(maximum_exact_instantiations) is not int
        or not 1 <= maximum_exact_instantiations <= 128
        or type(confidence_denominator) is not int
        or confidence_denominator < 2
    ):
        _fail("V53 acquisition inventory changed")
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
        _fail("V53 source evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V53 state layout changed")
    groups = v35._groups(rows)  # noqa: SLF001
    if len(groups) < 3:
        _fail("V53 needs training, prequential, and held-out queries")

    required_bits = math.ceil(math.log2(confidence_denominator))
    required_set = set(required_terminal_classes)
    acquired: list[dict[str, Any]] = []
    attempts = []
    ledger = []
    active = None
    selected = None
    stop = None
    retired = 0
    for offset, group in enumerate(groups):
        count = offset + 1
        if active is not None:
            prediction = _predict_frontier_group(active["program"], group, order)
            ledger.append(
                {
                    "query_index": offset,
                    "candidate_program_id_before_outcome": active["program_id"],
                    "candidate_training_query_count": active["training_query_count"],
                    "prediction": prediction,
                    "prediction_frozen_before_query_outcome": True,
                }
            )
            if prediction["query_exact"]:
                active["evidence_bits"] += 1
                active["confirmed_query_count"] += 1
            else:
                active = None
                retired += 1
        acquired.extend(group)
        if (
            active is not None
            and active["evidence_bits"] >= required_bits
            and count < len(groups)
        ):
            selected, stop = active["program"], count
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
            readiness = (
                v52._compiler_readiness(  # noqa: SLF001
                    layout, unknown, acquired, program
                )
                if type(program) is dict
                else {
                    "status_target_present_in_residual_inventory": False,
                    "per_residual_coordinate": [],
                    "all_non_status_residual_version_spaces_nonempty": False,
                    "version_space_selection_compute_events": 0,
                }
            )
            public = {
                key: value
                for key, value in constructed.items()
                if key != "candidate_program"
            }
            public.update(
                training_query_count=count,
                observed_terminal_classes=list(observed_classes),
                required_terminal_classes=list(required_terminal_classes),
                semantic_class_coverage_complete=class_coverage,
                observed_successor_training_calibration_required=True,
                every_terminal_frontier_candidate_prequentially_checked=True,
                residual_successor_version_space_consensus_required=False,
                compiler_readiness=readiness,
                training_calibrated_after_all_acquisition_guards=(
                    class_coverage
                    and constructed.get("training_calibrated") is True
                    and type(program) is dict
                    and readiness[
                        "all_non_status_residual_version_spaces_nonempty"
                    ]
                    is True
                ),
            )
            attempts.append(public)
            if public["training_calibrated_after_all_acquisition_guards"]:
                active = {
                    "program": program,
                    "program_id": constructed["candidate_program_id"],
                    "training_query_count": count,
                    "evidence_bits": 0,
                    "confirmed_query_count": 0,
                }
    if selected is None or stop is None:
        status = "ABSTAINED_NO_FRONTIER_PREQUENTIALLY_EXACT_PROPOSAL"
        heldout, heldout_exact = [], False
    else:
        heldout = [row for group in groups[stop:] for row in group]
        heldout_exact = all(
            _predict_frontier_group(selected, group, order)["query_exact"]
            for group in groups[stop:]
        )
        status = (
            "PROPOSAL_ISSUED_HELDOUT_VALIDATED"
            if heldout_exact
            else "PROPOSAL_ISSUED_HELDOUT_FAILED_NONCERTIFICATE"
        )
    query_order = [
        {
            "pre_vector": group[0]["pre_vector"],
            "action_key": group[0]["selected_action"]["action_key"],
            "raw_transition_row_count": len(group),
        }
        for group in groups
    ]
    payload = {
        "schema": "acfqp.generic_frontier_prequential_acquisition.v53",
        "arm": (
            "ROLE_FREE_FACTOR_PRIOR_ON"
            if role_free_template_library is not None
            else "STRICT_NO_ROLE_FREE_FACTOR_PRIOR"
        ),
        "role_free_template_library_id": (
            None
            if role_free_template_library is None
            else role_free_template_library.get("template_library_id")
        ),
        "required_terminal_classes": list(required_terminal_classes),
        "witness_blind_query_order": query_order,
        "witness_blind_query_order_sha256": hashlib.sha256(
            canonical_json_bytes(query_order)
        ).hexdigest(),
        "full_query_stream_ground_support_labels": len(groups),
        "proposal_attempts": attempts,
        "prequential_prediction_ledger": ledger,
        "retired_failed_proposal_count": retired,
        "required_prequential_evidence_bits": required_bits,
        "prequential_evidence_bits_per_exact_query": 1,
        "stopped_physical_ground_support_labels": stop,
        "selected_terminal_program": selected,
        "selected_terminal_program_id": (
            None if selected is None else selected["terminal_program_id"]
        ),
        "heldout_ground_query_count": len(groups) - (stop or len(groups)),
        "heldout_raw_transition_row_count": len(heldout),
        "heldout_exact_prediction": heldout_exact,
        "status": status,
        "terminal_candidate_derivation_compute_events": sum(
            attempt.get("candidate_constructor_compute", 0) for attempt in attempts
        ),
        "compiler_readiness_compute_events": sum(
            attempt["compiler_readiness"][
                "version_space_selection_compute_events"
            ]
            for attempt in attempts
        ),
        "terminal_program_semantics_apply_to_successors": True,
        "observed_successor_training_calibration_required": True,
        "every_retained_terminal_frontier_candidate_prequentially_checked": True,
        "every_retained_terminal_frontier_candidate_heldout_checked": True,
        "residual_successor_version_space_consensus_required_before_issuance": False,
        "nonempty_residual_version_space_required_before_issuance": True,
        "every_batch_exact_residual_proposal_retained_by_compiler_required": True,
        "unacquired_successor_or_label_accessed_by_stopping_rule": False,
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
        "frontier_prequential_acquisition_id": hashlib.sha256(
            _ACQUISITION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_relation_covering_frontier_prequential_acquisition_v53(
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
    acquisition = acquire_frontier_prequential_terminal_program_v53(
        ordered,
        role_free_template_library=role_free_template_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.relation_covering_frontier_prequential_acquisition.v53",
        "query_schedule": schedule,
        "frontier_prequential_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "frontier_prequential_acquisition_id": acquisition[
            "frontier_prequential_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "all_terminal_frontier_candidates_checked_prequentially": True,
        "residual_successor_consensus_used_as_acquisition_gate": False,
        "nonempty_residual_version_space_used_as_readiness_gate": True,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "relation_covering_frontier_prequential_acquisition_id": hashlib.sha256(
            _BUNDLE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "acquire_frontier_prequential_terminal_program_v53",
    "run_relation_covering_frontier_prequential_acquisition_v53",
)
