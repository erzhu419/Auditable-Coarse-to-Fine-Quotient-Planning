"""Anytime prequential calibration for role-free terminal proposals.

V35 could stop as soon as an observed-exact program compressed its training
rows.  The preserved V36 diagnostic showed that this can make a structural
prior stop earlier *and* fail on held-out rows.  V37 keeps V36's outcome-blind
query schedules, but a proposal must predict subsequently acquired queries
before their outcomes are revealed.  A wrong prediction retires the proposal;
the now-observed query may then participate in a fresh proposal.

The evidence threshold is derived from ``confidence_denominator``.  One exact
prequential query contributes one conservative deterministic evidence bit.
This is a construction/calibration convention, not a statistical coverage or
safety guarantee.  Both prior and no-prior arms use this exact state machine.
"""

from __future__ import annotations

import copy
import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp import generic_adaptive_role_free_terminal_acquisition_v35 as v35
from acfqp.generic_relational_terminal_program_independent_replay_v32 import (
    GenericRelationalTerminalProgramIndependentReplayV32Error,
    reconstruct_relational_terminal_program_v32,
)
from acfqp.generic_role_free_acquisition_operator_v36 import (
    schedule_role_free_acquisition_queries_v36,
)
from acfqp.generic_role_free_relational_template_v33 import (
    GenericRoleFreeRelationalTemplateV33Error,
    instantiate_role_free_relational_template_v33,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericPrequentialRoleFreeAcquisitionV37Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericPrequentialRoleFreeAcquisitionV37Error(message)


def _candidate(
    layout: Mapping[str, Any],
    unknown: list[int],
    acquired: list[dict[str, Any]],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    maximum_exact_instantiations: int,
    confidence_denominator: int,
) -> dict[str, Any]:
    evidence = {
        "layout": layout,
        "unknown_residual_target_columns": unknown,
        "raw_transition_rows": acquired,
    }
    try:
        instantiation = None
        if role_free_template_library is None:
            program = reconstruct_relational_terminal_program_v32(
                evidence,
                maximum_program_candidates=maximum_exact_instantiations,
            )
            source = "FINITE_RELATION_GRAMMAR"
            compute = program["relation_feature_evaluation_count"]
        else:
            active_library = v35._observed_class_view(  # noqa: SLF001
                role_free_template_library, acquired
            )
            instantiation = instantiate_role_free_relational_template_v33(
                active_library,
                evidence,
                maximum_exact_instantiations=maximum_exact_instantiations,
            )
            program = instantiation.get("instantiated_terminal_program")
            if type(program) is not dict:
                raise GenericRoleFreeRelationalTemplateV33Error(
                    "V37 prior exposed no exact target instantiation"
                )
            source = "ROLE_FREE_TEMPLATE_LIBRARY"
            compute = instantiation["binding_evaluation_count"]
    except (
        GenericRelationalTerminalProgramIndependentReplayV32Error,
        GenericRoleFreeRelationalTemplateV33Error,
    ) as error:
        return {
            "candidate_present": False,
            "constructor_failure": str(error),
        }

    order = layout.get("state_canonical_to_raw")
    if type(order) is not list:
        _fail("V37 state layout changed")
    challenges = v35._observed_states(acquired, order)  # noqa: SLF001
    consensus = v35._consensus(program, challenges)  # noqa: SLF001
    literal_bits = v35._literal_description_bits(acquired)  # noqa: SLF001
    program_bits = v35._program_description_bits(  # noqa: SLF001
        program,
        role_free_template_library=role_free_template_library,
        instantiation=instantiation,
        state_width=len(order),
    )
    required_gain = math.ceil(math.log2(confidence_denominator))
    mdl_gain = literal_bits - program_bits
    return {
        "candidate_present": True,
        "candidate_source": source,
        "candidate_program": program,
        "candidate_program_id": program["terminal_program_id"],
        "candidate_count": program["decision_tree_candidate_count"],
        "candidate_constructor_compute": compute,
        "candidate_consensus_on_observed_successors": consensus,
        "literal_description_bits": literal_bits,
        "selected_program_description_bits": program_bits,
        "mdl_description_gain_bits": mdl_gain,
        "required_mdl_gain_bits": required_gain,
        "training_calibrated": consensus and mdl_gain >= required_gain,
    }


def _predict_group(
    program: Mapping[str, Any],
    group: list[dict[str, Any]],
    order: list[int],
) -> dict[str, Any]:
    target = program.get("status_target_column")
    tree = program.get("decision_tree")
    if type(target) is not int or type(tree) is not dict:
        _fail("V37 candidate program changed")
    rows = []
    exact = True
    for row in group:
        post = row.get("post_vector")
        if type(post) is not list:
            _fail("V37 post-state evidence changed")
        state = tuple(post[index] for index in order)
        predicted_class, predicted_token = v35._evaluate(tree, state)  # noqa: SLF001
        observed_class = v35._label(row)  # noqa: SLF001
        observed_token = state[target]
        row_exact = (
            predicted_class == observed_class and predicted_token == observed_token
        )
        exact = exact and row_exact
        rows.append(
            {
                "predicted_terminal_class": predicted_class,
                "observed_terminal_class": observed_class,
                "predicted_status_token": predicted_token,
                "observed_status_token": observed_token,
                "exact": row_exact,
            }
        )
    return {"query_exact": exact, "raw_row_predictions": rows}


def acquire_prequential_role_free_terminal_program_v37(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    if type(source_complete_evidence) is not dict:
        _fail("V37 source-complete evidence changed")
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
        _fail("V37 acquisition inventory changed")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list or sorted(order) != list(range(len(order))):
        _fail("V37 state layout changed")
    groups = v35._groups(rows)  # noqa: SLF001
    if len(groups) < 3:
        _fail("V37 needs training, prequential, and held-out queries")

    required_evidence_bits = math.ceil(math.log2(confidence_denominator))
    acquired: list[dict[str, Any]] = []
    proposal_attempts = []
    prequential_ledger = []
    active: dict[str, Any] | None = None
    selected: dict[str, Any] | None = None
    stop: int | None = None
    retired_count = 0

    for query_offset, group in enumerate(groups):
        query_count = query_offset + 1
        if active is not None:
            prediction = _predict_group(active["program"], group, order)
            prequential_ledger.append(
                {
                    "query_index": query_offset,
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
                retired_count += 1

        acquired.extend(group)

        # At least one untouched group remains for a post-stop audit.  That
        # audit never participates in issuance or stopping.
        if (
            active is not None
            and active["evidence_bits"] >= required_evidence_bits
            and query_count < len(groups)
        ):
            selected = active["program"]
            stop = query_count
            break

        if active is None and query_count < len(groups) - 1:
            constructed = _candidate(
                layout,
                unknown,
                acquired,
                role_free_template_library=role_free_template_library,
                maximum_exact_instantiations=maximum_exact_instantiations,
                confidence_denominator=confidence_denominator,
            )
            public_attempt = {
                key: value
                for key, value in constructed.items()
                if key != "candidate_program"
            }
            public_attempt["training_query_count"] = query_count
            proposal_attempts.append(public_attempt)
            if constructed.get("training_calibrated") is True:
                active = {
                    "program": constructed["candidate_program"],
                    "program_id": constructed["candidate_program_id"],
                    "training_query_count": query_count,
                    "evidence_bits": 0,
                    "confirmed_query_count": 0,
                }

    if selected is None or stop is None:
        status = "ABSTAINED_NO_PREQUENTIALLY_CALIBRATED_PROPOSAL"
        heldout = []
        heldout_exact = False
    else:
        heldout = [row for group in groups[stop:] for row in group]
        heldout_exact = all(
            _predict_group(selected, group, order)["query_exact"]
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
        "schema": "acfqp.generic_prequential_role_free_terminal_acquisition.v37",
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
        "witness_blind_query_order": query_order,
        "witness_blind_query_order_sha256": hashlib.sha256(
            canonical_json_bytes(query_order)
        ).hexdigest(),
        "full_query_stream_ground_support_labels": len(groups),
        "proposal_attempts": proposal_attempts,
        "prequential_prediction_ledger": prequential_ledger,
        "retired_failed_proposal_count": retired_count,
        "required_prequential_evidence_bits": required_evidence_bits,
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
        "same_prequential_state_machine_in_both_arms": True,
        "prediction_frozen_before_each_confirmation_outcome": True,
        "failed_proposal_retrained_only_after_failure_observed": True,
        "heldout_rows_accessed_before_stop": False,
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "confidence_denominator": confidence_denominator,
        "automatic_stop_rule": (
            "TRAINING_MDL_AND_OBSERVED_CONSENSUS_THEN_PREQUENTIAL_EXACT_"
            "EVIDENCE_BITS_GE_CEIL_LOG2_CONFIDENCE_DENOMINATOR"
        ),
        "prequential_bit_is_deterministic_calibration_unit_not_probability_bound": True,
        "statistical_coverage_claimed": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
        "future_unseen_dynamics_authority_present": False,
    }
    return {
        **payload,
        "prequential_acquisition_id": hashlib.sha256(
            b"acfqp:generic-prequential-role-free-terminal-acquisition:v37\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def run_outcome_blind_prequential_acquisition_v37(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    schedule = schedule_role_free_acquisition_queries_v36(
        source_complete_evidence,
        role_free_template_library=role_free_template_library,
    )
    ordered = copy.deepcopy(source_complete_evidence)
    ordered["raw_transition_rows"] = schedule["scheduled_raw_transition_rows"]
    acquisition = acquire_prequential_role_free_terminal_program_v37(
        ordered,
        role_free_template_library=role_free_template_library,
        maximum_exact_instantiations=maximum_exact_instantiations,
        confidence_denominator=confidence_denominator,
    )
    payload = {
        "schema": "acfqp.outcome_blind_prequential_acquisition.v37",
        "query_schedule": schedule,
        "prequential_acquisition": acquisition,
        "query_schedule_id": schedule["query_schedule_id"],
        "prequential_acquisition_id": acquisition["prequential_acquisition_id"],
        "outcome_witness_used_for_scheduling": False,
        "same_v37_calibration_engine_in_both_arms": True,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
    }
    return {
        **payload,
        "outcome_blind_acquisition_id": hashlib.sha256(
            b"acfqp:outcome-blind-prequential-acquisition:v37\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = (
    "acquire_prequential_role_free_terminal_program_v37",
    "run_outcome_blind_prequential_acquisition_v37",
)
