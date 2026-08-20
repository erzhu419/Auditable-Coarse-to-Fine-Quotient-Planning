"""Semantic-class coverage guard for prequential world-model proposals.

V71 showed that six exact consecutive predictions can still miss a later
terminal class.  V38 therefore requires the acquired evidence to cover the
finite typed terminal-class universe before a candidate may enter the V37
prequential state machine.  The rule has no label-count floor and no fixed
confirmation block: its prerequisites are semantic coverage, MDL/consensus,
and confidence-derived prequential evidence.
"""

from __future__ import annotations

import copy
import hashlib
import math
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp import generic_prequential_role_free_acquisition_v37 as v37
from acfqp.generic_role_free_acquisition_operator_v36 import (
    schedule_role_free_acquisition_queries_v36,
)
from acfqp.phase3e_ids import canonical_json_bytes


TERMINAL_CLASS_UNIVERSE_V38 = ("ACCEPT", "ACTIVE", "REJECT")
PRESERVED_V38_RETROSPECTIVE_DIAGNOSTIC = MappingProxyType(
    {
        "schema": "acfqp.semantic_coverage_retrospective_diagnostic.v38",
        "frozen_source_campaign_id": (
            "a8a9ebead0bcfeb1587be1a6b21ddb11189ec74e26d871ab5ada0ec279261e17"
        ),
        "joint_validated_occurrences": 5,
        "joint_failed_noncertificate_occurrences": 1,
        "joint_abstained_occurrences": 0,
        "joint_counterfactual_consumed_labels": 136,
        "strict_validated_occurrences": 3,
        "strict_failed_noncertificate_occurrences": 2,
        "strict_abstained_occurrences": 1,
        "strict_counterfactual_consumed_labels": 186,
        "registered_scientific_result": False,
        "sample_tax_claimed": False,
        "failure_preserved": True,
    }
)


class GenericSemanticCoverageAcquisitionV38Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericSemanticCoverageAcquisitionV38Error(message)


def acquire_semantic_coverage_terminal_program_v38(
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
        or tuple(sorted(set(required_terminal_classes)))
        != required_terminal_classes
        or not required_terminal_classes
        or any(
            value not in TERMINAL_CLASS_UNIVERSE_V38
            for value in required_terminal_classes
        )
    ):
        _fail("V38 semantic acquisition inventory changed")
    layout = source_complete_evidence.get("layout")
    unknown = source_complete_evidence.get("unknown_residual_target_columns")
    rows = source_complete_evidence.get("raw_transition_rows")
    if (
        type(layout) is not dict
        or type(unknown) is not list
        or unknown != sorted(set(unknown))
        or type(rows) is not list
        or not rows
        or type(maximum_exact_instantiations) is not int
        or not 1 <= maximum_exact_instantiations <= 128
        or type(confidence_denominator) is not int
        or confidence_denominator < 2
    ):
        _fail("V38 source evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V38 state layout changed")
    groups = v35._groups(rows)  # noqa: SLF001
    if len(groups) < 3:
        _fail("V38 needs training, prequential, and held-out queries")
    required_bits = math.ceil(math.log2(confidence_denominator))
    required_set = set(required_terminal_classes)
    acquired: list[dict[str, Any]] = []
    attempts = []
    ledger = []
    active: dict[str, Any] | None = None
    selected = None
    stop = None
    retired = 0

    for offset, group in enumerate(groups):
        count = offset + 1
        if active is not None:
            prediction = v37._predict_group(active["program"], group, order)  # noqa: SLF001
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
            observed_classes = tuple(sorted({v35._label(row) for row in acquired}))  # noqa: SLF001
            class_coverage = set(observed_classes) == required_set
            constructed = v37._candidate(  # noqa: SLF001
                layout,
                unknown,
                acquired,
                role_free_template_library=role_free_template_library,
                maximum_exact_instantiations=maximum_exact_instantiations,
                confidence_denominator=confidence_denominator,
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
                training_calibrated_after_semantic_coverage=(
                    class_coverage and constructed.get("training_calibrated") is True
                ),
            )
            attempts.append(public)
            if public["training_calibrated_after_semantic_coverage"]:
                active = {
                    "program": constructed["candidate_program"],
                    "program_id": constructed["candidate_program_id"],
                    "training_query_count": count,
                    "evidence_bits": 0,
                    "confirmed_query_count": 0,
                }

    if selected is None or stop is None:
        status = "ABSTAINED_NO_SEMANTICALLY_COVERED_PREQUENTIAL_PROPOSAL"
        heldout, heldout_exact = [], False
    else:
        heldout = [row for group in groups[stop:] for row in group]
        heldout_exact = all(
            v37._predict_group(selected, group, order)["query_exact"]  # noqa: SLF001
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
        "schema": "acfqp.generic_semantic_coverage_acquisition.v38",
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
        "same_semantic_coverage_and_prequential_engine_in_both_arms": True,
        "prediction_frozen_before_each_confirmation_outcome": True,
        "heldout_rows_accessed_before_stop": False,
        "semantic_class_coverage_is_typed_not_fixed_label_floor": True,
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "confidence_denominator": confidence_denominator,
        "automatic_stop_rule": (
            "TYPED_SEMANTIC_CLASS_COVERAGE_AND_TRAINING_MDL_CONSENSUS_AND_"
            "PREQUENTIAL_EVIDENCE_BITS_GE_CEIL_LOG2_CONFIDENCE_DENOMINATOR"
        ),
        "statistical_coverage_claimed": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "semantic_coverage_acquisition_id": hashlib.sha256(
            b"acfqp:generic-semantic-coverage-acquisition:v38\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_outcome_blind_semantic_coverage_acquisition_v38(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    required_terminal_classes: tuple[str, ...] = TERMINAL_CLASS_UNIVERSE_V38,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    schedule = schedule_role_free_acquisition_queries_v36(
        source_complete_evidence,
        role_free_template_library=role_free_template_library,
    )
    ordered = copy.deepcopy(source_complete_evidence)
    ordered["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
    acquisition = acquire_semantic_coverage_terminal_program_v38(
        ordered,
        role_free_template_library=role_free_template_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.outcome_blind_semantic_coverage_acquisition.v38",
        "query_schedule": schedule,
        "semantic_coverage_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "semantic_coverage_acquisition_id": acquisition[
            "semantic_coverage_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "outcome_blind_acquisition_id": hashlib.sha256(
            b"acfqp:outcome-blind-semantic-coverage-acquisition:v38\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "PRESERVED_V38_RETROSPECTIVE_DIAGNOSTIC",
    "TERMINAL_CLASS_UNIVERSE_V38",
    "acquire_semantic_coverage_terminal_program_v38",
    "run_outcome_blind_semantic_coverage_acquisition_v38",
)
