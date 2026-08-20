"""Refine V24 proposals by exact state-action batch support equality.

Per-row support excess is not an error for a stochastic kernel: a two-point
support necessarily contains the other outcome when each row is inspected in
isolation.  V27 groups raw transitions by anonymous state-action context and
requires equality between the proposed support and the complete observed
successor-value set for every frozen batch.  This remains empirical proposal
evidence, not global dynamics or safety authority.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes


class GenericBatchExactMultiResidualCompilerV27Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericBatchExactMultiResidualCompilerV27Error(message)


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
    _fail("V27 residual expression escaped the finite grammar")


def _batches(evidence: Mapping[str, Any]) -> list[list[tuple[list[int], list[int], list[int]]]]:
    layout = evidence.get("layout")
    rows = evidence.get("raw_transition_rows")
    if type(layout) is not dict or type(rows) is not list or not rows:
        _fail("V27 raw evidence changed")
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V27 anonymous layout changed")
    grouped: dict[tuple[Any, ...], list[tuple[list[int], list[int], list[int]]]] = {}
    order = []
    for row in rows:
        selected = row.get("selected_action") if type(row) is dict else None
        pre = row.get("pre_vector") if type(row) is dict else None
        post = row.get("post_vector") if type(row) is dict else None
        action = selected.get("anonymous_fields") if type(selected) is dict else None
        key = (
            tuple(pre or ()),
            selected.get("action_key") if type(selected) is dict else None,
        )
        if (
            type(pre) is not list
            or type(post) is not list
            or type(action) is not list
            or len(pre) != len(post)
            or sorted(state_order) != list(range(len(pre)))
            or sorted(action_order) != list(range(len(action)))
            or type(key[1]) is not int
        ):
            _fail("V27 raw transition row changed")
        aligned = (
            [pre[index] for index in state_order],
            [post[index] for index in state_order],
            [action[index] for index in action_order],
        )
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(aligned)
    return [grouped[key] for key in order]


def _templates(
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
                (["R04", ["R00"], ["R03", ["R00"], ["R02"]]], None, constant),
            )
        )
    unique = {}
    for expression, field, constant in result:
        unique.setdefault(
            (canonical_json_bytes(expression), field, constant),
            (expression, field, constant),
        )
    return list(unique.values())


def _nodes(expression: Any) -> int:
    if type(expression) is not list:
        return 0
    return 1 + sum(_nodes(item) for item in expression[1:])


def _signed_integer_bits(value: int | None) -> int:
    return 0 if value is None else 1 + 2 * int(math.log2(abs(value) + 1))


def _description_bits(
    expression: Any,
    field: int | None,
    constant: int | None,
    *,
    target: int,
    state_width: int,
    action_width: int,
    prior_index: int | None,
) -> int:
    del target
    target_bits = max(1, math.ceil(math.log2(max(2, state_width))))
    field_bits = (
        0 if field is None else max(1, math.ceil(math.log2(max(2, action_width))))
    )
    expression_bits = (
        1 + max(1, math.ceil(math.log2(prior_index + 2)))
        if prior_index is not None
        else 2 * _nodes(expression)
    )
    return target_bits + field_bits + _signed_integer_bits(constant) + expression_bits


def _batch_exact_candidate(
    batches: list[list[tuple[list[int], list[int], list[int]]]],
    target: int,
    prior_expressions: list[Any] | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], int]:
    rows = [row for batch in batches for row in batch]
    prior_by_expression = (
        {}
        if prior_expressions is None
        else {
            canonical_json_bytes(expression): index
            for index, expression in enumerate(prior_expressions)
        }
    )
    candidates = []
    evaluations = 0
    for expression, field, constant in _templates(rows, target):
        batch_rows = []
        exact = True
        excess = 0
        for index, batch in enumerate(batches):
            predicted = _value(expression, batch[0][0], batch[0][2], target, field, constant)
            observed = tuple(sorted({post[target] for _pre, post, _action in batch}))
            same = predicted == observed
            exact = exact and same
            excess += len(predicted) - 1
            evaluations += len(batch)
            batch_rows.append(
                {
                    "batch_index": index,
                    "predicted_support": list(predicted),
                    "observed_successor_support": list(observed),
                    "support_equal": same,
                }
            )
        if not exact:
            continue
        prior_index = prior_by_expression.get(canonical_json_bytes(expression))
        candidate = {
            "target_column": target,
            "normalized_expression": expression,
            "action_field_binding": field,
            "anonymous_integer_constant_binding": constant,
            "prior_expression_index": prior_index,
            "predictive_support_excess": sum(
                (len(row["predicted_support"]) - 1) * len(batches[row["batch_index"]])
                for row in batch_rows
            ),
            "batch_support_excess": excess,
        }
        candidate["description_length_bits"] = _description_bits(
            expression,
            field,
            constant,
            target=target,
            state_width=len(rows[0][0]),
            action_width=len(rows[0][2]),
            prior_index=prior_index,
        )
        identity = {
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
            b"acfqp:batch-exact-residual-candidate:v27\x00"
            + canonical_json_bytes(identity)
        ).hexdigest()
        candidates.append((candidate["description_length_bits"], canonical_json_bytes(candidate), candidate, batch_rows))
    if not candidates:
        return None, [], evaluations
    _bits, _encoded, candidate, batch_rows = min(candidates)
    return candidate, batch_rows, evaluations


def compile_batch_exact_multi_residual_support_v27(
    acquisition: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    prior_library: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if (
        type(acquisition) is not dict
        or acquisition.get("schema") != "acfqp.generic_multi_residual_acquisition.v24"
        or acquisition.get("proposal_only_not_safety_authority") is not True
        or acquisition.get("complete_residual_world_model_synthesized") is not False
    ):
        _fail("V27 V24 predecessor changed")
    batches = _batches(evidence)
    prior_expressions = None
    prior_library_id = None
    if prior_library is not None:
        programs = prior_library.get("compiled_subprograms")
        if type(programs) is not list or not programs:
            _fail("V27 residual prior library changed")
        prior_expressions = [row["normalized_expression"] for row in programs]
        prior_library_id = prior_library.get("residual_factor_library_id")
    if acquisition.get("prior_library_id") != prior_library_id:
        _fail("V27 prior arm binding changed")
    targets = acquisition.get("unknown_residual_target_columns")
    target_results = acquisition.get("target_results")
    if (
        type(targets) is not list
        or targets != sorted(set(targets))
        or type(target_results) is not list
        or len(target_results) != len(targets)
    ):
        _fail("V27 target inventory changed")
    refinements = []
    exact_candidates = []
    evaluation_count = 0
    for target, result in zip(targets, target_results, strict=True):
        if type(result) is not dict or result.get("target_column") != target:
            _fail("V27 per-target predecessor changed")
        total = result.get("total_acquisition")
        candidate = total.get("candidate") if type(total) is dict else None
        if type(candidate) is dict and candidate.get("target_column") != target:
            _fail("V27 candidate target changed")
        refined_candidate = None
        batch_rows = []
        if type(candidate) is dict:
            refined_candidate, batch_rows, evaluations = _batch_exact_candidate(
                batches, target, prior_expressions
            )
            evaluation_count += evaluations
        exact = type(refined_candidate) is dict
        refinement = {
            "target_column": target,
            "total_acquisition_id": None
            if type(total) is not dict
            else total.get("total_acquisition_id"),
            "candidate_id": None
            if type(candidate) is not dict
            else candidate.get("candidate_id"),
            "batch_exact_candidate_id": None
            if refined_candidate is None
            else refined_candidate["candidate_id"],
            "original_selected_candidate_retained": (
                type(candidate) is dict
                and refined_candidate is not None
                and candidate.get("normalized_expression")
                == refined_candidate["normalized_expression"]
                and candidate.get("action_field_binding")
                == refined_candidate["action_field_binding"]
                and candidate.get("anonymous_integer_constant_binding")
                == refined_candidate["anonymous_integer_constant_binding"]
            ),
            "batch_support_rows": batch_rows,
            "batch_exact_on_complete_frozen_query_pool": exact,
            "eligible_for_joint_batch_exact_abstract_planning": exact,
        }
        refinements.append(refinement)
        if exact:
            exact_candidates.append(refined_candidate)
    payload = {
        "schema": "acfqp.generic_batch_exact_multi_residual_support.v27",
        "v24_multi_residual_acquisition_id": acquisition.get(
            "multi_residual_acquisition_id"
        ),
        "prior_library_id": prior_library_id,
        "unknown_residual_target_columns": targets,
        "raw_state_action_batch_count": len(batches),
        "shared_physical_ground_support_labels": acquisition.get(
            "shared_physical_ground_support_labels"
        ),
        "target_refinements": refinements,
        "joint_batch_exact_candidates": exact_candidates,
        "joint_batch_exact_target_columns": [
            row["target_column"] for row in exact_candidates
        ],
        "joint_batch_exact_candidate_count": len(exact_candidates),
        "batch_exact_candidate_binding_evaluation_count": evaluation_count,
        "all_targets_batch_exact_on_complete_frozen_query_pool": (
            len(exact_candidates) == len(targets)
        ),
        "per_row_support_excess_not_confused_with_stochastic_batch_mismatch": True,
        "v24_statistical_stop_required_before_batch_exact_reranking": True,
        "empirical_batch_support_equality_only": True,
        "future_unseen_support_authority_present": False,
        "abstract_plan_safety_authority_present": False,
        "global_exact_dynamics_claimed": False,
        "complete_residual_world_model_synthesized": False,
    }
    return {
        **payload,
        "batch_exact_multi_residual_id": hashlib.sha256(
            b"acfqp:generic-batch-exact-multi-residual-support:v27\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def replay_batch_exact_multi_residual_support_v27(
    result: Mapping[str, Any],
    acquisition: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    prior_library: Mapping[str, Any] | None,
) -> dict[str, Any]:
    expected = compile_batch_exact_multi_residual_support_v27(
        acquisition, evidence, prior_library=prior_library
    )
    if result != expected:
        _fail("V27 batch-exact support differs from exact replay")
    return {
        "batch_exact_multi_residual_id": expected["batch_exact_multi_residual_id"],
        "raw_state_action_batch_count": expected["raw_state_action_batch_count"],
        "joint_batch_exact_candidate_count": expected[
            "joint_batch_exact_candidate_count"
        ],
        "all_batch_support_equalities_reconstructed": True,
        "future_unseen_support_authority_present": False,
    }


__all__ = (
    "compile_batch_exact_multi_residual_support_v27",
    "replay_batch_exact_multi_residual_support_v27",
)
