"""Reachable-query frontier consensus for semantic prequential acquisition.

V39 still allowed one wrong proposal after typed class and relation-stratum
coverage.  V40 additionally requires every exact candidate in the current
frontier to agree on all outcome-blind query pre-states.  These are actual
reachable query contexts rather than V35's Cartesian donor counterfactuals.
The check reads no successor or label from an unacquired query.
"""

from __future__ import annotations

import copy
import hashlib
import math
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp import generic_prequential_role_free_acquisition_v37 as v37
from acfqp.generic_relation_covering_schedule_v39 import (
    schedule_relation_covering_queries_v39,
)
from acfqp.generic_semantic_coverage_acquisition_v38 import (
    TERMINAL_CLASS_UNIVERSE_V38,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericFrontierConsensusAcquisitionV40Error(ValueError):
    pass


PRESERVED_V40_RETROSPECTIVE_DIAGNOSTIC = MappingProxyType(
    {
        "schema": "acfqp.frontier_consensus_retrospective_diagnostic.v40",
        "frozen_source_campaign_id": (
            "a8a9ebead0bcfeb1587be1a6b21ddb11189ec74e26d871ab5ada0ec279261e17"
        ),
        "prior_validated_occurrences": 5,
        "prior_failed_noncertificate_occurrences": 1,
        "prior_abstained_occurrences": 0,
        "prior_counterfactual_consumed_labels": 168,
        "strict_validated_occurrences": 4,
        "strict_failed_noncertificate_occurrences": 1,
        "strict_abstained_occurrences": 1,
        "strict_counterfactual_consumed_labels": 205,
        "registered_scientific_result": False,
        "remaining_failure_requires_learned_successor_support": True,
        "failure_preserved": True,
    }
)


def _fail(message: str) -> NoReturn:
    raise GenericFrontierConsensusAcquisitionV40Error(message)


def acquire_frontier_consensus_terminal_program_v40(
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
        or any(value not in TERMINAL_CLASS_UNIVERSE_V38 for value in required_terminal_classes)
    ):
        _fail("V40 semantic acquisition inventory changed")
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
        _fail("V40 source evidence changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V40 state layout changed")
    groups = v35._groups(rows)  # noqa: SLF001
    if len(groups) < 3:
        _fail("V40 needs training, prequential, and held-out queries")
    query_pre_states = tuple(
        sorted(
            {
                tuple(group[0]["pre_vector"][index] for index in order)
                for group in groups
            }
        )
    )
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
            program = constructed.get("candidate_program")
            prestate_consensus = (
                type(program) is dict
                and v35._consensus(program, query_pre_states)  # noqa: SLF001
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
                outcome_blind_query_prestate_challenge_count=len(query_pre_states),
                candidate_frontier_consensus_on_all_query_pre_states=prestate_consensus,
                training_calibrated_after_all_guards=(
                    class_coverage
                    and prestate_consensus
                    and constructed.get("training_calibrated") is True
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
        status = "ABSTAINED_NO_REACHABLE_FRONTIER_CONSENSUS_PROPOSAL"
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
        "schema": "acfqp.generic_frontier_consensus_acquisition.v40",
        "arm": (
            "ROLE_FREE_FACTOR_PRIOR_ON"
            if role_free_template_library is not None
            else "STRICT_NO_ROLE_FREE_FACTOR_PRIOR"
        ),
        "role_free_template_library_id": (
            None if role_free_template_library is None else role_free_template_library.get("template_library_id")
        ),
        "required_terminal_classes": list(required_terminal_classes),
        "witness_blind_query_order": query_order,
        "witness_blind_query_order_sha256": hashlib.sha256(canonical_json_bytes(query_order)).hexdigest(),
        "outcome_blind_query_prestate_challenge_count": len(query_pre_states),
        "full_query_stream_ground_support_labels": len(groups),
        "proposal_attempts": attempts,
        "prequential_prediction_ledger": ledger,
        "retired_failed_proposal_count": retired,
        "required_prequential_evidence_bits": required_bits,
        "prequential_evidence_bits_per_exact_query": 1,
        "stopped_physical_ground_support_labels": stop,
        "selected_terminal_program": selected,
        "selected_terminal_program_id": None if selected is None else selected["terminal_program_id"],
        "heldout_ground_query_count": len(groups) - (stop or len(groups)),
        "heldout_raw_transition_row_count": len(heldout),
        "heldout_exact_prediction": heldout_exact,
        "status": status,
        "same_guard_and_prequential_engine_in_both_arms": True,
        "all_query_prestate_challenges_available_without_outcomes": True,
        "unacquired_successor_or_label_accessed_by_frontier_guard": False,
        "prediction_frozen_before_each_confirmation_outcome": True,
        "heldout_rows_accessed_before_stop": False,
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "confidence_denominator": confidence_denominator,
        "automatic_stop_rule": (
            "TYPED_CLASS_COVERAGE_AND_REACHABLE_QUERY_PRESTATE_FRONTIER_CONSENSUS_"
            "AND_TRAINING_MDL_AND_PREQUENTIAL_EVIDENCE"
        ),
        "statistical_coverage_claimed": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "frontier_consensus_acquisition_id": hashlib.sha256(
            b"acfqp:generic-frontier-consensus-acquisition:v40\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_relation_covering_frontier_consensus_v40(
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
    acquisition = acquire_frontier_consensus_terminal_program_v40(
        ordered,
        role_free_template_library=role_free_template_library,
        required_terminal_classes=required_terminal_classes,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.relation_covering_frontier_consensus.v40",
        "query_schedule": schedule,
        "frontier_consensus_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "frontier_consensus_acquisition_id": acquisition[
            "frontier_consensus_acquisition_id"
        ],
        "outcome_witness_used_for_scheduling_or_frontier_guard": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "relation_covering_acquisition_id": hashlib.sha256(
            b"acfqp:relation-covering-frontier-consensus:v40\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "PRESERVED_V40_RETROSPECTIVE_DIAGNOSTIC",
    "acquire_frontier_consensus_terminal_program_v40",
    "run_relation_covering_frontier_consensus_v40",
)
