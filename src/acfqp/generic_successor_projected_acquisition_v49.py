"""Acquire a terminal program using successor support, never raw pre-state votes.

V41 correctly learned a conservative successor-support version space, but it
also required every terminal-tree candidate to agree when evaluated directly
on all query *pre-states*.  Terminal programs classify successors, so that
extra test is not a semantic requirement and can reject a valid successor
model.  V49 removes only that misplaced test.  It retains observed-successor
training calibration, semantic-class coverage, projected future successor
support consensus, prequential confirmation, and untouched held-out audit.
"""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp import generic_learned_successor_support_acquisition_v41 as v41
from acfqp import generic_prequential_role_free_acquisition_v37 as v37
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    TERMINAL_CLASS_UNIVERSE_V38,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericSuccessorProjectedAcquisitionV49Error(ValueError):
    pass


_ACQUISITION_DOMAIN = b"acfqp:generic-successor-projected-acquisition:v49\x00"
_BUNDLE_DOMAIN = b"acfqp:relation-covering-successor-projected-acquisition:v49\x00"


def _fail(message: str) -> NoReturn:
    raise GenericSuccessorProjectedAcquisitionV49Error(message)


def acquire_successor_projected_terminal_program_v49(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    successor_prior_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
    successor_confidence_denominator: int = 64,
    maximum_successor_support_states: int = 4096,
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
        or type(successor_confidence_denominator) is not int
        or successor_confidence_denominator < 2
        or type(maximum_successor_support_states) is not int
        or maximum_successor_support_states < 1
    ):
        _fail("V49 acquisition inventory changed")
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
        _fail("V49 source evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V49 state layout changed")
    groups = v35._groups(rows)  # noqa: SLF001
    if len(groups) < 3:
        _fail("V49 needs training, prequential, and held-out queries")

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
            prediction = v37._predict_group(  # noqa: SLF001
                active["program"], group, order
            )
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
            if (
                class_coverage
                and constructed.get("training_calibrated") is True
                and type(program) is dict
            ):
                successor_guard = v41._learned_successor_guard(  # noqa: SLF001
                    layout,
                    acquired,
                    groups[count:],
                    program,
                    successor_prior_library=successor_prior_library,
                    successor_confidence_denominator=(
                        successor_confidence_denominator
                    ),
                    maximum_successor_support_states=(
                        maximum_successor_support_states
                    ),
                )
            else:
                successor_guard = {
                    "successor_model_present": False,
                    "guard_not_attempted_before_semantic_and_training_calibration": True,
                    "learned_successor_frontier_consensus": False,
                }
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
                terminal_frontier_evaluated_on_query_prestates=False,
                observed_successor_training_calibration_required=True,
                learned_successor_guard=successor_guard,
                training_calibrated_after_all_guards=(
                    class_coverage
                    and constructed.get("training_calibrated") is True
                    and type(program) is dict
                    and successor_guard.get(
                        "learned_successor_frontier_consensus"
                    )
                    is True
                ),
            )
            attempts.append(public)
            if public["training_calibrated_after_all_guards"]:
                active = {
                    "program": program,
                    "program_id": constructed["candidate_program_id"],
                    "training_query_count": count,
                    "evidence_bits": 0,
                    "confirmed_query_count": 0,
                }
    if selected is None or stop is None:
        status = "ABSTAINED_NO_SUCCESSOR_PROJECTED_CONSENSUS_PROPOSAL"
        heldout, heldout_exact = [], False
    else:
        heldout = [row for group in groups[stop:] for row in group]
        heldout_exact = all(
            v37._predict_group(selected, group, order)[  # noqa: SLF001
                "query_exact"
            ]
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
    successor_compute = sum(
        attempt["learned_successor_guard"].get(
            "successor_model_selection_compute_events", 0
        )
        + attempt["learned_successor_guard"].get(
            "batch_exact_binding_evaluation_count", 0
        )
        for attempt in attempts
    )
    payload = {
        "schema": "acfqp.generic_successor_projected_acquisition.v49",
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
        "successor_prior_library_id": (
            None
            if successor_prior_library is None
            else successor_prior_library.get("residual_factor_library_id")
        ),
        "successor_point_estimate_confidence_denominator": (
            successor_confidence_denominator
        ),
        "successor_prior_used_to_prune_batch_exact_version_space": False,
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
        "successor_model_derivation_compute_events": successor_compute,
        "terminal_frontier_evaluated_on_query_prestates": False,
        "terminal_program_semantics_apply_to_successors": True,
        "observed_successor_training_calibration_required": True,
        "projected_future_successor_support_consensus_required": True,
        "status_output_coordinate_used_as_successor_guard_input": False,
        "batch_exact_successor_version_space_not_point_estimate": True,
        "only_acquired_transition_outcomes_used_to_fit_successor_models": True,
        "unacquired_successor_or_label_accessed_by_guard": False,
        "heldout_rows_accessed_before_stop": False,
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "statistical_coverage_claimed": False,
        "empirical_successor_support_promoted_to_global_dynamics": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "successor_projected_acquisition_id": hashlib.sha256(
            _ACQUISITION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_relation_covering_successor_projected_acquisition_v49(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    successor_prior_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
    successor_confidence_denominator: int = 64,
    maximum_successor_support_states: int = 4096,
) -> dict[str, Any]:
    schedule = schedule_relation_covering_queries_v39(source_complete_evidence)
    ordered = copy.deepcopy(source_complete_evidence)
    ordered["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
    acquisition = acquire_successor_projected_terminal_program_v49(
        ordered,
        role_free_template_library=role_free_template_library,
        successor_prior_library=successor_prior_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
        successor_confidence_denominator=successor_confidence_denominator,
        maximum_successor_support_states=maximum_successor_support_states,
    )
    payload = {
        "schema": "acfqp.relation_covering_successor_projected_acquisition.v49",
        "query_schedule": schedule,
        "successor_projected_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "successor_projected_acquisition_id": acquisition[
            "successor_projected_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "terminal_frontier_evaluated_on_query_prestates": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "relation_covering_successor_projected_acquisition_id": hashlib.sha256(
            _BUNDLE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "acquire_successor_projected_terminal_program_v49",
    "run_relation_covering_successor_projected_acquisition_v49",
)
