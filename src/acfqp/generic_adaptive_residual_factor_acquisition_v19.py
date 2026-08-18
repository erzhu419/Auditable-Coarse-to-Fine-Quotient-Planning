"""Adaptive residual-factor proposal acquisition from certificate-local rows.

Both arms use this exact synthesizer and stopping rule.  The only switch is
whether a frozen list of normalized expressions receives the short prior code.
All proposals remain statistical action-ordering hints: none can discharge a
ground safety obligation.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


GENERIC_RESIDUAL_OPCODES_V19 = ("R00", "R01", "R02", "R03", "R04")


class GenericAdaptiveResidualFactorAcquisitionV19Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericAdaptiveResidualFactorAcquisitionV19Error(message)


def _aligned_batches(
    evidence: Mapping[str, Any],
) -> list[list[tuple[list[int], list[int], list[int]]]]:
    layout = evidence.get("layout")
    raw_rows = evidence.get("raw_transition_rows")
    if type(layout) is not dict or type(raw_rows) is not list or not raw_rows:
        _fail("V19 residual evidence changed")
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V19 residual layout changed")
    grouped: list[tuple[tuple[Any, ...], list[tuple[list[int], list[int], list[int]]]]] = []
    locations: dict[tuple[Any, ...], int] = {}
    for row in raw_rows:
        if type(row) is not dict or type(row.get("selected_action")) is not dict:
            _fail("V19 residual raw row changed")
        pre = row.get("pre_vector")
        post = row.get("post_vector")
        selected = row["selected_action"]
        action = selected.get("anonymous_fields")
        key = (tuple(pre or ()), selected.get("action_key"))
        if (
            type(pre) is not list
            or type(post) is not list
            or type(action) is not list
            or len(pre) != len(post)
            or sorted(state_order) != list(range(len(pre)))
            or sorted(action_order) != list(range(len(action)))
            or type(selected.get("action_key")) is not int
        ):
            _fail("V19 residual row width changed")
        aligned = (
            [pre[index] for index in state_order],
            [post[index] for index in state_order],
            [action[index] for index in action_order],
        )
        if key not in locations:
            locations[key] = len(grouped)
            grouped.append((key, []))
        grouped[locations[key]][1].append(aligned)
    return [batch for _key, batch in grouped]


def _value(
    expression: Any,
    pre: list[int],
    action: list[int],
    target: int,
    field: int | None,
    constant: int | None,
) -> tuple[int, ...]:
    if expression == ["R00"]:
        return (pre[target],)
    if expression == ["R01"] and field is not None:
        return (action[field],)
    if expression == ["R02"] and constant is not None:
        return (constant,)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R03":
        left = _value(expression[1], pre, action, target, field, constant)
        right = _value(expression[2], pre, action, target, field, constant)
        if len(left) == len(right) == 1:
            return (left[0] + right[0],)
    if type(expression) is list and len(expression) == 3 and expression[0] == "R04":
        left = _value(expression[1], pre, action, target, field, constant)
        right = _value(expression[2], pre, action, target, field, constant)
        if len(left) == len(right) == 1:
            return tuple(sorted({left[0], right[0]}))
    _fail("V19 residual expression escaped the finite grammar")


def _generic_templates(
    rows: list[tuple[list[int], list[int], list[int]]], target: int
) -> list[tuple[Any, int | None, int | None]]:
    field_count = len(rows[0][2])
    constants = sorted(
        {
            value
            for pre, post, action in rows
            for value in (
                post[target],
                post[target] - pre[target],
                *(
                    post[target] - pre[target] - action[field]
                    for field in range(field_count)
                ),
            )
        }
    )
    result: list[tuple[Any, int | None, int | None]] = [(["R00"], None, None)]
    for field in range(field_count):
        result.extend(
            ((["R01"], field, None), (["R03", ["R00"], ["R01"]], field, None))
        )
        for constant in constants:
            result.extend(
                (
                    (["R03", ["R03", ["R00"], ["R01"]], ["R02"]], field, constant),
                    (
                        [
                            "R04",
                            ["R00"],
                            ["R03", ["R03", ["R00"], ["R01"]], ["R02"]],
                        ],
                        field,
                        constant,
                    ),
                )
            )
    for constant in constants:
        result.extend(
            (
                (["R02"], None, constant),
                (["R03", ["R00"], ["R02"]], None, constant),
                (
                    ["R04", ["R00"], ["R03", ["R00"], ["R02"]]],
                    None,
                    constant,
                ),
            )
        )
    return result


def _binding_templates_for_expression(
    expression: Any,
    rows: list[tuple[list[int], list[int], list[int]]],
    target: int,
) -> list[tuple[Any, int | None, int | None]]:
    encoded = canonical_json_bytes(expression)
    return [
        row
        for row in _generic_templates(rows, target)
        if canonical_json_bytes(row[0]) == encoded
    ]


def _nodes(expression: Any) -> int:
    if type(expression) is not list:
        return 0
    return 1 + sum(_nodes(item) for item in expression[1:])


def _signed_integer_bits(value: int | None) -> int:
    if value is None:
        return 0
    magnitude = abs(value)
    return 1 + 2 * int(math.log2(magnitude + 1))


def _binding_code_bits(
    candidate: Mapping[str, Any],
    *,
    state_width: int,
    action_width: int,
    prior_index: int | None,
) -> int:
    target_bits = max(1, math.ceil(math.log2(max(2, state_width))))
    field_bits = (
        0
        if candidate["action_field_binding"] is None
        else max(1, math.ceil(math.log2(max(2, action_width))))
    )
    constant_bits = _signed_integer_bits(
        candidate["anonymous_integer_constant_binding"]
    )
    expression_bits = (
        1 + max(1, math.ceil(math.log2(prior_index + 2)))
        if prior_index is not None
        else 2 * _nodes(candidate["normalized_expression"])
    )
    return target_bits + field_bits + constant_bits + expression_bits


def _candidates(
    rows: list[tuple[list[int], list[int], list[int]]],
    targets: list[int],
    prior_expressions: list[Any] | None,
) -> tuple[list[dict[str, Any]], int]:
    result = []
    evaluations = 0
    expressions = (
        prior_expressions
        if prior_expressions is not None
        else None
    )
    for target in targets:
        templates = (
            [
                template
                for expression in expressions
                for template in _binding_templates_for_expression(
                    expression, rows, target
                )
            ]
            if expressions is not None
            else _generic_templates(rows, target)
        )
        seen = set()
        for expression, field, constant in templates:
            key = (canonical_json_bytes(expression), field, constant)
            if key in seen:
                continue
            seen.add(key)
            evaluations += len(rows)
            excess = 0
            exact = True
            for pre, post, action in rows:
                support = _value(expression, pre, action, target, field, constant)
                if post[target] not in support:
                    exact = False
                    break
                excess += len(support) - 1
            if exact:
                prior_index = None
                if expressions is not None:
                    prior_index = next(
                        index
                        for index, value in enumerate(expressions)
                        if canonical_json_bytes(value) == canonical_json_bytes(expression)
                    )
                candidate = {
                    "target_column": target,
                    "normalized_expression": expression,
                    "action_field_binding": field,
                    "anonymous_integer_constant_binding": constant,
                    "prior_expression_index": prior_index,
                    "predictive_support_excess": excess,
                }
                candidate["description_length_bits"] = _binding_code_bits(
                    candidate,
                    state_width=len(rows[0][0]),
                    action_width=len(rows[0][2]),
                    prior_index=prior_index,
                )
                identity_payload = {
                    key: candidate[key]
                    for key in (
                        "target_column",
                        "normalized_expression",
                        "action_field_binding",
                        "anonymous_integer_constant_binding",
                        "prior_expression_index",
                    )
                }
                candidate["candidate_id"] = hashlib.sha256(
                    b"acfqp:adaptive-residual-factor-candidate:v19\x00"
                    + canonical_json_bytes(identity_payload)
                ).hexdigest()
                result.append(candidate)
    result.sort(
        key=lambda candidate: (
            candidate["predictive_support_excess"],
            candidate["description_length_bits"],
            canonical_json_bytes(candidate),
        )
    )
    return result, evaluations


def _predicts(
    candidate: Mapping[str, Any],
    batch: list[tuple[list[int], list[int], list[int]]],
) -> bool:
    return all(
        post[candidate["target_column"]]
        in _value(
            candidate["normalized_expression"],
            pre,
            action,
            candidate["target_column"],
            candidate["action_field_binding"],
            candidate["anonymous_integer_constant_binding"],
        )
        for pre, post, action in batch
    )


def _context_key(batch: list[tuple[list[int], list[int], list[int]]]) -> bytes:
    return canonical_json_bytes(
        [{"pre": pre, "action": action} for pre, _post, action in batch]
    )


def _disagreement_count(
    candidates: list[dict[str, Any]],
    batch: list[tuple[list[int], list[int], list[int]]],
) -> int:
    signatures = set()
    for candidate in candidates:
        signatures.add(
            canonical_json_bytes(
                {
                    "target_column": candidate["target_column"],
                    "supports": [
                        list(
                            _value(
                                candidate["normalized_expression"],
                                pre,
                                action,
                                candidate["target_column"],
                                candidate["action_field_binding"],
                                candidate["anonymous_integer_constant_binding"],
                            )
                        )
                        for pre, _post, action in batch
                    ],
                }
            )
        )
    return len(signatures)


def acquire_adaptive_residual_factor_v19(
    evidence: Mapping[str, Any],
    *,
    prior_library: Mapping[str, Any] | None,
    confidence_denominator: int = 64,
) -> dict[str, Any]:
    if type(confidence_denominator) is not int or confidence_denominator < 2:
        _fail("V19 confidence denominator changed")
    targets = evidence.get("unknown_residual_target_columns")
    if type(targets) is not list or not targets or targets != sorted(set(targets)):
        _fail("V19 residual target inventory changed")
    batches = _aligned_batches(evidence)
    prior_expressions = None
    prior_library_id = None
    if prior_library is not None:
        programs = prior_library.get("compiled_subprograms")
        if type(programs) is not list or not programs:
            _fail("V19 prior library changed")
        prior_expressions = [program["normalized_expression"] for program in programs]
        prior_library_id = prior_library.get("residual_factor_library_id")
    rows: list[tuple[list[int], list[int], list[int]]] = []
    remaining = list(enumerate(batches))
    selected_batch_indices = []
    candidate = None
    available_candidates: list[dict[str, Any]] = []
    issued_at = None
    invalidated = 0
    changed = 0
    previous = None
    evidence_rows = 0
    evaluation_count = 0
    prediction_checks = 0
    history = []
    confidence_bits = math.ceil(math.log2(confidence_denominator))
    for label_count in range(1, len(batches) + 1):
        ranked_queries = []
        for original_index, batch in remaining:
            disagreement = _disagreement_count(available_candidates, batch)
            ranked_queries.append(
                (-disagreement, _context_key(batch), original_index, batch)
            )
        _negative_disagreement, _context, selected_index, batch = min(ranked_queries)
        remaining = [row for row in remaining if row[0] != selected_index]
        selected_batch_indices.append(selected_index)
        rows.extend(batch)
        candidate_survived = False
        if candidate is not None:
            prediction_checks += len(batch)
            if _predicts(candidate, batch):
                evidence_rows += len(batch)
                candidate_survived = True
            else:
                previous = candidate["candidate_id"]
                invalidated += 1
        available_candidates, evaluations = _candidates(
            rows, targets, prior_expressions
        )
        evaluation_count += evaluations
        selected_candidate = available_candidates[0] if available_candidates else None
        if (
            selected_candidate is None
            or candidate is None
            or selected_candidate["candidate_id"] != candidate["candidate_id"]
        ):
            old_id = None if candidate is None else candidate["candidate_id"]
            candidate = selected_candidate
            issued_at = None if candidate is None else label_count
            evidence_rows = 0
            if old_id is not None and candidate is not None and candidate["candidate_id"] != old_id:
                changed += 1
            if previous is not None and candidate is not None and candidate["candidate_id"] != previous:
                changed += 1
        elif not candidate_survived:
            issued_at = label_count
            evidence_rows = 0
        required = (
            None
            if candidate is None
            else candidate["description_length_bits"] + confidence_bits
        )
        stopped = (
            candidate is not None
            and evidence_rows >= required
            and label_count > issued_at
        )
        history.append(
            {
                "ground_support_labels": label_count,
                "selected_raw_query_batch_index": selected_index,
                "pre_query_candidate_disagreement_count": -_negative_disagreement,
                "candidate_id": None if candidate is None else candidate["candidate_id"],
                "candidate_issued_at_label": issued_at,
                "post_issuance_predictive_evidence_rows": evidence_rows,
                "required_true_bit_evidence": required,
                "stopped": stopped,
            }
        )
        if stopped:
            payload = {
                "schema": "acfqp.adaptive_residual_factor_acquisition.v19",
                "arm": (
                    "RESIDUAL_FACTOR_PRIOR_ON"
                    if prior_library is not None
                    else "STRICT_NO_RESIDUAL_FACTOR_PRIOR"
                ),
                "prior_library_id": prior_library_id,
                "prior_expression_count": 0 if prior_expressions is None else len(prior_expressions),
                "ground_support_labels": label_count,
                "raw_transition_rows_consumed": sum(
                    len(batches[index]) for index in selected_batch_indices
                ),
                "selected_raw_query_batch_indices": selected_batch_indices,
                "candidate": candidate,
                "candidate_issued_at_label": issued_at,
                "invalidated_candidate_count": invalidated,
                "candidate_change_count": changed,
                "post_issuance_predictive_evidence_rows": evidence_rows,
                "confidence_denominator": confidence_denominator,
                "confidence_penalty_bits": confidence_bits,
                "candidate_binding_evaluation_count": evaluation_count,
                "predictive_row_check_count": prediction_checks,
                "history": history,
                "same_generic_synthesizer_and_stop_rule": True,
                "query_selection_uses_state_and_action_context_but_not_successor_outcome": True,
                "reachable_frontier_exhaustion_consumed": False,
                "fixed_label_floor": None,
                "fixed_confirmation_block": None,
                "proposal_only_not_safety_authority": True,
                "ground_fact_transfer_present": False,
                "complete_residual_world_model_synthesized": False,
            }
            return {
                **payload,
                "acquisition_id": hashlib.sha256(
                    b"acfqp:adaptive-residual-factor-acquisition:v19\x00"
                    + canonical_json_bytes(payload)
                ).hexdigest(),
            }
    _fail("V19 adaptive residual acquisition did not stop on available evidence")


def replay_adaptive_residual_factor_v19(
    acquisition: Mapping[str, Any], evidence: Mapping[str, Any]
) -> dict[str, Any]:
    candidate = acquisition.get("candidate")
    if type(candidate) is not dict:
        _fail("V19 replay candidate changed")
    batches = _aligned_batches(evidence)
    failed_batches = [
        index for index, batch in enumerate(batches) if not _predicts(candidate, batch)
    ]
    failed_rows = sum(len(batches[index]) for index in failed_batches)
    total_rows = sum(len(batch) for batch in batches)
    return {
        "acquisition_id": acquisition.get("acquisition_id"),
        "full_query_stream_label_count": len(batches),
        "full_query_stream_raw_transition_count": total_rows,
        "post_stop_raw_transition_count": total_rows
        - acquisition.get("raw_transition_rows_consumed", 0),
        "failed_query_batch_indices": failed_batches,
        "failed_query_batch_count": len(failed_batches),
        "failed_raw_transition_count": failed_rows,
        "supported_raw_transition_count": total_rows - failed_rows,
        "exact_support_on_full_frozen_query_stream": not failed_batches,
        "held_out_tail_failure_is_recoverable_only_by_certificate_local_ground_query": bool(
            failed_batches
        ),
        "future_transition_prediction_authority_present": False,
    }


__all__ = (
    "acquire_adaptive_residual_factor_v19",
    "replay_adaptive_residual_factor_v19",
)
