"""Adaptive terminal-program acquisition with an optional role-free prior.

Both arms use the same witness-blind state-action query order and the same
candidate-consensus stopping rule.  The prior arm instantiates frozen V33
templates; the strict arm runs the independent finite V32 relation grammar.
Held-out rows are inspected only after the stop and cannot alter the program.
This is a retrospective acquisition construction, not online execution.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp.generic_relational_terminal_program_independent_replay_v32 import (
    GenericRelationalTerminalProgramIndependentReplayV32Error,
    reconstruct_relational_terminal_program_v32,
)
from acfqp.generic_role_free_relational_template_v33 import (
    GenericRoleFreeRelationalTemplateV33Error,
    instantiate_role_free_relational_template_v33,
)
from acfqp.phase3e_ids import canonical_json_bytes


class GenericAdaptiveRoleFreeTerminalAcquisitionV35Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericAdaptiveRoleFreeTerminalAcquisitionV35Error(message)


def _label(row: Mapping[str, Any]) -> str:
    legal = row.get("legal_action_keys_after")
    terminal = row.get("terminal_acceptance_after")
    if type(legal) is not list:
        _fail("V35 legal-action evidence changed")
    if legal:
        if terminal is not None:
            _fail("V35 active row carried a terminal label")
        return "ACTIVE"
    if terminal is True:
        return "ACCEPT"
    if terminal is False:
        return "REJECT"
    _fail("V35 terminal row omitted its label")


def _relation(opcode: str, left: int, right: int, state: tuple[int, ...]) -> bool:
    if opcode == "EQ":
        return state[left] == state[right]
    if opcode == "LT":
        return state[left] < state[right]
    if opcode == "LE":
        return state[left] <= state[right]
    if opcode == "GT":
        return state[left] > state[right]
    if opcode == "GE":
        return state[left] >= state[right]
    _fail("V35 terminal relation opcode changed")


def _evaluate(node: Any, state: tuple[int, ...]) -> tuple[str, int]:
    while type(node) is dict and node.get("kind") == "RELATION":
        left, right = node.get("left_column"), node.get("right_column")
        if type(left) is not int or type(right) is not int:
            _fail("V35 terminal relation columns changed")
        node = node["when_true"] if _relation(
            node.get("opcode"), left, right, state
        ) else node["when_false"]
    if type(node) is not dict or node.get("kind") != "LEAF":
        _fail("V35 terminal tree leaf changed")
    return node.get("terminal_class"), node.get("status_token")


def _groups(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    order = []
    for row in rows:
        action = row.get("selected_action") if type(row) is dict else None
        pre = row.get("pre_vector") if type(row) is dict else None
        if type(action) is not dict or type(pre) is not list or type(
            action.get("action_key")
        ) is not int:
            _fail("V35 raw transition row changed")
        key = (tuple(pre), action["action_key"])
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(row)
    return [grouped[key] for key in order]


def _challenge_states(
    rows: list[dict[str, Any]], state_order: list[int]
) -> tuple[tuple[int, ...], ...]:
    observed = [tuple(row["post_vector"][index] for index in state_order) for row in rows]
    result = set(observed)
    for state in observed:
        for column in range(len(state)):
            for donor in observed:
                changed = list(state)
                changed[column] = donor[column]
                result.add(tuple(changed))
    return tuple(sorted(result))


def _observed_states(
    rows: list[dict[str, Any]], state_order: list[int]
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        sorted(
            {
                tuple(row["post_vector"][index] for index in state_order)
                for row in rows
            }
        )
    )


def _signed_integer_bits(value: int) -> int:
    return 1 + 2 * math.ceil(math.log2(abs(value) + 1))


def _literal_description_bits(rows: list[dict[str, Any]]) -> int:
    return sum(
        2
        + sum(_signed_integer_bits(value) for value in row["post_vector"])
        for row in rows
    )


def _program_description_bits(
    program: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    instantiation: Mapping[str, Any] | None,
    state_width: int,
) -> int:
    column_bits = max(1, math.ceil(math.log2(max(2, state_width))))
    tokens = program.get("status_token_by_terminal_class")
    if type(tokens) is not dict:
        _fail("V35 terminal token mapping changed")
    token_bits = sum(_signed_integer_bits(value) for value in tokens.values())
    if role_free_template_library is None:
        frontier = program.get("decision_tree_candidate_frontier")
        if type(frontier) is not list or not frontier:
            _fail("V35 strict tree frontier changed")
        return 8 * frontier[0]["decision_tree_byte_count"] + token_bits
    if type(instantiation) is not dict:
        _fail("V35 prior instantiation receipt changed")
    selected = instantiation.get("selected_instantiation")
    if type(selected) is not dict:
        _fail("V35 prior selected instantiation changed")
    template_count = role_free_template_library.get("role_free_template_count")
    binding = selected.get("target_role_binding")
    if type(template_count) is not int or type(binding) is not list:
        _fail("V35 prior code inventory changed")
    return (
        max(1, math.ceil(math.log2(max(2, template_count))))
        + len(binding) * column_bits
        + column_bits
        + token_bits
    )


def _consensus(program: Mapping[str, Any], challenges: tuple[tuple[int, ...], ...]) -> bool:
    frontier = program.get("decision_tree_candidate_frontier")
    if type(frontier) is not list or not frontier:
        _fail("V35 terminal candidate frontier changed")
    for state in challenges:
        outcomes = {
            _evaluate(row.get("decision_tree"), state)
            for row in frontier
            if type(row) is dict
        }
        if len(outcomes) != 1:
            return False
    return True


def _template_classes(node: Mapping[str, Any]) -> set[str]:
    if node.get("kind") == "LEAF":
        return {node.get("terminal_class")}
    return _template_classes(node["when_true"]) | _template_classes(
        node["when_false"]
    )


def _observed_class_view(
    library: Mapping[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    observed = {_label(row) for row in rows}
    templates = [
        row
        for row in library.get("role_free_templates", [])
        if _template_classes(row["role_free_decision_tree"]) <= observed
    ]
    if not templates:
        raise GenericRoleFreeRelationalTemplateV33Error(
            "V35 prior has no template whose leaf inventory is observed"
        )
    payload = {
        key: value
        for key, value in library.items()
        if key not in ("template_library_id", "role_free_templates", "role_free_template_count")
    }
    payload["role_free_templates"] = templates
    payload["role_free_template_count"] = len(templates)
    return {
        **payload,
        "template_library_id": hashlib.sha256(
            b"acfqp:generic-role-free-relational-template-library:v33\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def acquire_adaptive_role_free_terminal_program_v35(
    source_complete_evidence: Mapping[str, Any],
    *,
    role_free_template_library: Mapping[str, Any] | None,
    maximum_exact_instantiations: int = 32,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    if type(source_complete_evidence) is not dict:
        _fail("V35 source-complete evidence changed")
    layout = source_complete_evidence.get("layout")
    unknown = source_complete_evidence.get("unknown_residual_target_columns")
    rows = source_complete_evidence.get("raw_transition_rows")
    if (
        type(layout) is not dict
        or type(unknown) is not list
        or unknown != sorted(set(unknown))
        or type(rows) is not list
        or not rows
        or type(confidence_denominator) is not int
        or confidence_denominator < 2
    ):
        _fail("V35 source evidence inventory changed")
    groups = _groups(rows)
    if len(groups) < 2:
        _fail("V35 requires at least one acquisition and one held-out query")
    order = layout.get("state_canonical_to_raw")
    if type(order) is not list:
        _fail("V35 state layout changed")
    arm = (
        "ROLE_FREE_FACTOR_PRIOR_ON"
        if role_free_template_library is not None
        else "STRICT_NO_ROLE_FREE_FACTOR_PRIOR"
    )
    attempts = []
    selected = None
    stop = None
    for count in range(1, len(groups)):
        acquired = [row for group in groups[:count] for row in group]
        candidate_evidence = {
            "layout": layout,
            "unknown_residual_target_columns": unknown,
            "raw_transition_rows": acquired,
        }
        try:
            instantiation = None
            if role_free_template_library is None:
                program = reconstruct_relational_terminal_program_v32(
                    candidate_evidence,
                    maximum_program_candidates=maximum_exact_instantiations,
                )
                candidate_source = "FINITE_RELATION_GRAMMAR"
                candidate_compute = program["relation_feature_evaluation_count"]
            else:
                active_library = _observed_class_view(
                    role_free_template_library, acquired
                )
                instantiation = instantiate_role_free_relational_template_v33(
                    active_library,
                    candidate_evidence,
                    maximum_exact_instantiations=maximum_exact_instantiations,
                )
                program = instantiation.get("instantiated_terminal_program")
                if type(program) is not dict:
                    raise GenericRoleFreeRelationalTemplateV33Error(
                        "V35 prior exposed no exact target instantiation"
                    )
                candidate_source = "ROLE_FREE_TEMPLATE_LIBRARY"
                candidate_compute = instantiation["binding_evaluation_count"]
        except (
            GenericRelationalTerminalProgramIndependentReplayV32Error,
            GenericRoleFreeRelationalTemplateV33Error,
        ) as error:
            attempts.append(
                {
                    "physical_ground_support_labels": count,
                    "candidate_present": False,
                    "candidate_consensus_on_observation_derived_challenges": False,
                    "constructor_failure": str(error),
                }
            )
            continue
        observed_challenges = _observed_states(acquired, order)
        counterfactual_challenges = _challenge_states(acquired, order)
        observed_consensus = _consensus(program, observed_challenges)
        counterfactual_consensus = _consensus(program, counterfactual_challenges)
        literal_bits = _literal_description_bits(acquired)
        program_bits = _program_description_bits(
            program,
            role_free_template_library=role_free_template_library,
            instantiation=instantiation,
            state_width=len(order),
        )
        mdl_gain = literal_bits - program_bits
        required_gain = math.ceil(math.log2(confidence_denominator))
        calibrated = observed_consensus and mdl_gain >= required_gain
        attempts.append(
            {
                "physical_ground_support_labels": count,
                "candidate_present": True,
                "candidate_source": candidate_source,
                "candidate_program_id": program["terminal_program_id"],
                "candidate_count": program["decision_tree_candidate_count"],
                "candidate_constructor_compute": candidate_compute,
                "observed_successor_state_count": len(observed_challenges),
                "counterfactual_challenge_state_count": len(
                    counterfactual_challenges
                ),
                "candidate_consensus_on_observed_successors": observed_consensus,
                "candidate_consensus_on_counterfactual_challenges": (
                    counterfactual_consensus
                ),
                "literal_description_bits": literal_bits,
                "selected_program_description_bits": program_bits,
                "mdl_description_gain_bits": mdl_gain,
                "required_mdl_gain_bits": required_gain,
                "candidate_consensus_on_observation_derived_challenges": calibrated,
            }
        )
        if calibrated:
            selected = program
            stop = count
            break
    if selected is None or stop is None:
        status = "ABSTAINED_NO_CALIBRATED_CONSENSUS_BEFORE_HELDOUT"
        heldout = []
        heldout_exact = False
    else:
        heldout = [row for group in groups[stop:] for row in group]
        status_target = selected["status_target_column"]
        heldout_exact = True
        for row in heldout:
            state = tuple(row["post_vector"][index] for index in order)
            label, token = _evaluate(selected["decision_tree"], state)
            if label != _label(row) or token != state[status_target]:
                heldout_exact = False
                break
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
        "schema": "acfqp.generic_adaptive_role_free_terminal_acquisition.v35",
        "arm": arm,
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
        "acquisition_attempts": attempts,
        "stopped_physical_ground_support_labels": stop,
        "selected_terminal_program": selected,
        "selected_terminal_program_id": (
            None if selected is None else selected["terminal_program_id"]
        ),
        "heldout_ground_query_count": len(groups) - (stop or len(groups)),
        "heldout_raw_transition_row_count": len(heldout),
        "heldout_exact_prediction": heldout_exact,
        "status": status,
        "same_candidate_consensus_stopping_rule_for_both_arms": True,
        "heldout_rows_accessed_before_stop": False,
        "heldout_outcomes_changed_selected_program": False,
        "confidence_denominator": confidence_denominator,
        "automatic_stop_rule": (
            "OBSERVED_CANDIDATE_CONSENSUS_AND_MDL_GAIN_GE_LOG2_CONFIDENCE_DENOMINATOR"
        ),
        "fixed_label_floor_present": False,
        "fixed_confirmation_block_present": False,
        "retrospective_acquisition_only": True,
        "online_execution_integrated": False,
        "proposal_only_not_safety_authority": True,
        "future_unseen_dynamics_authority_present": False,
    }
    return {
        **payload,
        "adaptive_acquisition_id": hashlib.sha256(
            b"acfqp:generic-adaptive-role-free-terminal-acquisition:v35\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


__all__ = ("acquire_adaptive_role_free_terminal_program_v35",)
