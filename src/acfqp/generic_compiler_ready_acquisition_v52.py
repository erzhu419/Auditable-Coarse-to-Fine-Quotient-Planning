"""Acquire a terminal proposal only after its joint model is compiler-ready.

V51 correctly retained residual ambiguity, but it could stop before any
batch-exact residual expression existed for the acquisition prefix.  V52 adds
only a non-emptiness guard for every non-status residual coordinate.  It does
not require candidates to agree: every surviving expression remains available
for the joint compiler and robust planner.
"""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp import generic_joint_successor_version_space_planner_v42 as v42
from acfqp import generic_prequential_role_free_acquisition_v37 as v37
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    TERMINAL_CLASS_UNIVERSE_V38,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericCompilerReadyAcquisitionV52Error(ValueError):
    pass


_ACQUISITION_DOMAIN = b"acfqp:generic-compiler-ready-acquisition:v52\x00"
_BUNDLE_DOMAIN = b"acfqp:relation-covering-compiler-ready-acquisition:v52\x00"


def _fail(message: str) -> NoReturn:
    raise GenericCompilerReadyAcquisitionV52Error(message)


def _compiler_readiness(
    layout: Mapping[str, Any],
    unknown: list[int],
    acquired: list[dict[str, Any]],
    program: Mapping[str, Any],
) -> dict[str, Any]:
    status_target = program.get("status_target_column")
    if type(status_target) is not int or status_target not in unknown:
        return {
            "status_target_present_in_residual_inventory": False,
            "per_residual_coordinate": [],
            "all_non_status_residual_version_spaces_nonempty": False,
            "version_space_selection_compute_events": 0,
        }
    groups = v42._groups(acquired)  # noqa: SLF001
    batches = v42._aligned_batches(layout, groups)  # noqa: SLF001
    rows = []
    compute = 0
    for target in unknown:
        if target == status_target:
            continue
        frontier, evaluations = v42._version_space(batches, target)  # noqa: SLF001
        compute += evaluations
        rows.append(
            {
                "target_column": target,
                "batch_exact_candidate_count": len(frontier),
                "batch_exact_candidate_frontier_sha256": hashlib.sha256(
                    canonical_json_bytes(frontier)
                ).hexdigest(),
            }
        )
    return {
        "status_target_present_in_residual_inventory": True,
        "per_residual_coordinate": rows,
        "all_non_status_residual_version_spaces_nonempty": bool(rows)
        and all(row["batch_exact_candidate_count"] > 0 for row in rows),
        "version_space_selection_compute_events": compute,
    }


def acquire_compiler_ready_terminal_program_v52(
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
        _fail("V52 acquisition inventory changed")
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
        _fail("V52 source evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V52 state layout changed")
    groups = v35._groups(rows)  # noqa: SLF001
    if len(groups) < 3:
        _fail("V52 needs training, prequential, and held-out queries")

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
            readiness = (
                _compiler_readiness(layout, unknown, acquired, program)
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
        status = "ABSTAINED_NO_COMPILER_READY_TERMINAL_PROPOSAL"
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
    payload = {
        "schema": "acfqp.generic_compiler_ready_acquisition.v52",
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
        "compiler_ready_acquisition_id": hashlib.sha256(
            _ACQUISITION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_relation_covering_compiler_ready_acquisition_v52(
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
    acquisition = acquire_compiler_ready_terminal_program_v52(
        ordered,
        role_free_template_library=role_free_template_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.relation_covering_compiler_ready_acquisition.v52",
        "query_schedule": schedule,
        "compiler_ready_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "compiler_ready_acquisition_id": acquisition[
            "compiler_ready_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_unacquired_guard": False,
        "residual_successor_consensus_used_as_acquisition_gate": False,
        "nonempty_residual_version_space_used_as_readiness_gate": True,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "relation_covering_compiler_ready_acquisition_id": hashlib.sha256(
            _BUNDLE_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "acquire_compiler_ready_terminal_program_v52",
    "run_relation_covering_compiler_ready_acquisition_v52",
)
