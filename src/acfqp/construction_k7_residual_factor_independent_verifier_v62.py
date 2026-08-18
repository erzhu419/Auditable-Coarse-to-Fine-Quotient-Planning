"""Producer-free exact reconstruction of the V62 residual-factor library."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v62 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


VERIFICATION_ID = "981c040ff7e3a88e75ec8189d09d9c1511b6efd0b9358f7d825b38c978b316d2"
EXPECTED_CANONICAL_BYTE_COUNT = 619
EXPECTED_CANONICAL_SHA256 = "f943ed14b0d1f6afed971635e5c7ba8c44df18cb34b5347c59e05655a70e7869"
_TYPES = ["INT", "FINITE_INT_SUPPORT"]
_OPCODES = [
    ["R00", "SELF", [], "INT"],
    ["R01", "ACTION_FIELD", [], "INT"],
    ["R02", "ANONYMOUS_INTEGER_CONSTANT", [], "INT"],
    ["R03", "INT_ADD", ["INT", "INT"], "INT"],
    ["R04", "FINITE_SUPPORT_PAIR", ["INT", "INT"], "FINITE_INT_SUPPORT"],
]


class ConstructionK7ResidualFactorIndependentVerifierV62Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7ResidualFactorIndependentVerifierV62Error(message)


def _aligned(document: Mapping[str, Any]) -> list[tuple[list[int], list[int], list[int]]]:
    layout = document.get("layout")
    rows = document.get("raw_local_transition_rows")
    if type(layout) is not dict or type(rows) is not list or not rows:
        _fail("V62 source transition evidence changed")
    state_order = layout.get("state_canonical_to_raw")
    action_order = layout.get("action_canonical_to_raw")
    if type(state_order) is not list or type(action_order) is not list:
        _fail("V62 anonymous layout changed")
    result = []
    for row in rows:
        if type(row) is not dict or type(row.get("selected_action")) is not dict:
            _fail("V62 raw transition row changed")
        pre = row.get("pre_vector")
        post = row.get("post_vector")
        action = row["selected_action"].get("anonymous_fields")
        if (
            type(pre) is not list
            or type(post) is not list
            or type(action) is not list
            or len(pre) != len(post)
            or sorted(state_order) != list(range(len(pre)))
            or sorted(action_order) != list(range(len(action)))
        ):
            _fail("V62 raw transition width changed")
        result.append(
            (
                [pre[index] for index in state_order],
                [post[index] for index in state_order],
                [action[index] for index in action_order],
            )
        )
    return result


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
    _fail("V62 expression escaped the finite grammar")


def _bindings(
    rows: list[tuple[list[int], list[int], list[int]]], target: int
) -> list[dict[str, Any]]:
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
    templates: list[tuple[Any, int | None, int | None]] = [(["R00"], None, None)]
    for field in range(field_count):
        templates.extend(
            ((["R01"], field, None), (["R03", ["R00"], ["R01"]], field, None))
        )
        for constant in constants:
            templates.extend(
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
        templates.extend(
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
    result = []
    seen = set()
    for expression, field, constant in templates:
        key = (canonical_json_bytes(expression), field, constant)
        if key in seen:
            continue
        seen.add(key)
        if all(
            post[target] in _value(expression, pre, action, target, field, constant)
            for pre, post, action in rows
        ):
            result.append(
                {
                    "target_column": target,
                    "normalized_expression": expression,
                    "action_field_binding": field,
                    "anonymous_integer_constant_binding": constant,
                }
            )
    return result


def _opcodes(expression: Any) -> set[str]:
    if type(expression) is not list:
        return set()
    result = {expression[0]} if expression and type(expression[0]) is str else set()
    for item in expression[1:]:
        result.update(_opcodes(item))
    return result


def _reconstruct(sources: list[dict[str, Any]], minimum_support: int) -> dict[str, Any]:
    rows = {source["opaque_occurrence"]: _aligned(source) for source in sources}
    targets = {}
    by_expression: dict[bytes, dict[str, list[dict[str, Any]]]] = {}
    expressions = {}
    evaluations = 0
    for source in sources:
        name = source["opaque_occurrence"]
        unknown = source.get("unknown_residual_target_columns")
        if type(unknown) is not list or not unknown or unknown != sorted(set(unknown)):
            _fail("V62 residual target inventory changed")
        targets[name] = set(unknown)
        for target in unknown:
            candidates = _bindings(rows[name], target)
            evaluations += len(candidates) * len(rows[name])
            for binding in candidates:
                encoded = canonical_json_bytes(binding["normalized_expression"])
                expressions[encoded] = binding["normalized_expression"]
                by_expression.setdefault(encoded, {}).setdefault(name, []).append(binding)
    reusable = sorted(
        (encoded for encoded, values in by_expression.items() if len(values) >= minimum_support),
        key=lambda encoded: (len(encoded), encoded),
    )
    universe = {(name, target) for name, values in targets.items() for target in values}

    def coverage(encoded: bytes) -> set[tuple[str, int]]:
        return {
            (name, binding["target_column"])
            for name, bindings in by_expression[encoded].items()
            for binding in bindings
        }

    selected = []
    uncovered = set(universe)
    while True:
        ranked = []
        for encoded in reusable:
            if encoded in selected:
                continue
            new = coverage(encoded) & uncovered
            if not new:
                continue
            excess = 0
            for name, target in new:
                options = []
                for binding in by_expression[encoded][name]:
                    if binding["target_column"] != target:
                        continue
                    options.append(
                        sum(
                            len(
                                _value(
                                    expressions[encoded],
                                    pre,
                                    action,
                                    target,
                                    binding["action_field_binding"],
                                    binding["anonymous_integer_constant_binding"],
                                )
                            )
                            - 1
                            for pre, _post, action in rows[name]
                        )
                    )
                excess += min(options)
            ranked.append((excess, -len(new), len(encoded), encoded))
        if not ranked:
            break
        chosen = min(ranked)[3]
        selected.append(chosen)
        uncovered -= coverage(chosen)
    chosen_bindings = {}
    for point in sorted(universe - uncovered):
        name, target = point
        options = []
        for encoded in selected:
            for binding in by_expression[encoded].get(name, []):
                if binding["target_column"] != target:
                    continue
                excess = sum(
                    len(
                        _value(
                            expressions[encoded],
                            pre,
                            action,
                            target,
                            binding["action_field_binding"],
                            binding["anonymous_integer_constant_binding"],
                        )
                    )
                    - 1
                    for pre, _post, action in rows[name]
                )
                options.append(
                    (excess, len(encoded), encoded, canonical_json_bytes(binding), binding)
                )
        best = min(options)
        chosen_bindings[point] = (best[2], best[4])
    subprograms = []
    covered = set()
    for encoded in selected:
        expression = expressions[encoded]
        selected_targets = []
        for point in sorted(chosen_bindings):
            selected_encoded, binding = chosen_bindings[point]
            if selected_encoded == encoded:
                selected_targets.append({"occurrence": point[0], **binding})
                covered.add(point)
        source_bindings = []
        for name in sorted(by_expression[encoded]):
            ranked = []
            for binding in by_expression[encoded][name]:
                excess = sum(
                    len(
                        _value(
                            expression,
                            pre,
                            action,
                            binding["target_column"],
                            binding["action_field_binding"],
                            binding["anonymous_integer_constant_binding"],
                        )
                    )
                    - 1
                    for pre, _post, action in rows[name]
                )
                ranked.append((excess, canonical_json_bytes(binding), binding))
            source_bindings.append({"occurrence": name, **min(ranked)[2]})
        if selected_targets:
            subprograms.append(
                {
                    "normalized_expression": expression,
                    "expression_sha256": hashlib.sha256(encoded).hexdigest(),
                    "used_opcodes": sorted(_opcodes(expression)),
                    "source_occurrence_support_count": len(source_bindings),
                    "occurrence_bindings": source_bindings,
                    "selected_residual_target_bindings": selected_targets,
                }
            )
    payload = {
        "schema": "acfqp.generic_overlay_residual_factor_library.v18",
        "generic_types": _TYPES,
        "generic_opcode_registry": _OPCODES,
        "occurrence_count": len(sources),
        "residual_target_count": len(universe),
        "minimum_occurrence_support": minimum_support,
        "compiled_subprograms": subprograms,
        "covered_residual_targets": [
            {"occurrence": name, "target_column": target}
            for name, target in sorted(covered)
        ],
        "uncovered_residual_targets": [
            {"occurrence": name, "target_column": target}
            for name, target in sorted(uncovered)
        ],
        "candidate_binding_evaluation_count": evaluations,
        "selection_rule": "GREEDY_MIN_PREDICTIVE_SUPPORT_EXCESS_THEN_MAX_NEW_CROSS_OCCURRENCE_COVERAGE_THEN_CANONICAL_BYTES",
        "all_observed_residual_targets_covered": not uncovered,
        "family_names_available_to_compiler": False,
        "semantic_state_or_action_names_available_to_compiler": False,
        "ground_fact_transfer_across_occurrences_claimed": False,
        "future_transition_prediction_authority_present": False,
        "complete_world_model_claimed": False,
    }
    return {
        **payload,
        "residual_factor_library_id": hashlib.sha256(
            b"acfqp:generic-overlay-residual-factor-library:v18\x00"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def verify_residual_factor_library_bytes_v62(raw: bytes) -> bytes:
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("V62 library artifact is not canonical")
    payload = {key: value for key, value in document.items() if key != "library_artifact_id"}
    if domains.extension_content_id_v62(
        domains.CONSTRUCTION_K7_RESIDUAL_FACTOR_LIBRARY_V62_DOMAIN, payload
    ) != document.get("library_artifact_id"):
        _fail("V62 library artifact ID changed")
    if set(document) != {
        "schema",
        "source_closure",
        "development_sources",
        "compiled_library",
        "accounting",
        "evidence_boundary",
        "complete_residual_world_model_synthesized",
        "global_exact_dynamics_claimed",
        "arbitrary_domain_transfer_claimed",
        "official_execution_allowed",
        "official_scalar_cost",
        "official_N_break_even",
        "WORKLOAD_ECONOMICS_GATE",
        "COUNTER_COMPLETENESS_GATE",
        "library_artifact_id",
    }:
        _fail("V62 top-level schema changed")
    sources = document["development_sources"]
    if type(sources) is not list or len(sources) != 3:
        _fail("V62 development source inventory changed")
    for source in sources:
        source_payload = {key: value for key, value in source.items() if key != "source_id"}
        if domains.extension_content_id_v62(
            domains.CONSTRUCTION_K7_RESIDUAL_FACTOR_SOURCE_V62_DOMAIN,
            source_payload,
        ) != source.get("source_id"):
            _fail("V62 development source ID changed")
        if (
            source.get("retrospective_development_identity") is not True
            or source.get("preregistered_scientific_outcome") is not False
            or source.get("all_local_queries_followed_failed_certificates") is not True
            or source.get("acquisition_ground_support_labels")
            != len(source.get("raw_acquisition_batches", []))
            or type(source.get("failed_certificates")) is not list
            or type(source.get("local_distinctions")) is not list
            or len(source["failed_certificates"]) != len(source["local_distinctions"])
            or source.get("local_ground_support_labels")
            != sum(
                distinction.get("ground_support_labels", -1)
                for distinction in source["local_distinctions"]
            )
            or any(
                certificate.get("failure_index") != index
                or certificate.get("ground_query_performed_before_failure") is not False
                or distinction.get("failure_index") != index
                or distinction.get("query_after_failed_certificate") is not True
                for index, (certificate, distinction) in enumerate(
                    zip(
                        source["failed_certificates"],
                        source["local_distinctions"],
                        strict=True,
                    )
                )
            )
        ):
            _fail("V62 source accounting or claim boundary changed")
    expected_library = _reconstruct(
        sources, document["compiled_library"].get("minimum_occurrence_support")
    )
    if document["compiled_library"] != expected_library:
        _fail("V62 residual-factor library differs from producer-free reconstruction")
    accounting = document["accounting"]
    if accounting != {
        "offline_acquisition_labels": sum(
            source["acquisition_ground_support_labels"] for source in sources
        ),
        "offline_certificate_local_labels": sum(
            source["local_ground_support_labels"] for source in sources
        ),
        "offline_total_labels": sum(
            source["acquisition_ground_support_labels"]
            + source["local_ground_support_labels"]
            for source in sources
        ),
        "offline_execution_steps": sum(source["execution_steps"] for source in sources),
        "offline_planning_compute_events": sum(
            source["planning_compute_events"] for source in sources
        ),
        "compiler_candidate_binding_evaluations": expected_library[
            "candidate_binding_evaluation_count"
        ],
        "all_axes_separate": True,
    }:
        _fail("V62 offline accounting changed")
    if document["evidence_boundary"] != {
        "raw_source_rows_embedded": True,
        "exact_library_reconstruction_required": True,
        "retrospective_development_only": True,
        "fresh_held_out_sample_tax_claim_present": False,
        "ground_fact_transfer_present": False,
        "proposal_only_not_safety_authority": True,
    } or any(
        document[key] is not expected
        for key, expected in (
            ("complete_residual_world_model_synthesized", False),
            ("global_exact_dynamics_claimed", False),
            ("arbitrary_domain_transfer_claimed", False),
            ("official_execution_allowed", False),
        )
    ) or document["official_scalar_cost"] is not None or document["official_N_break_even"] is not None or document["WORKLOAD_ECONOMICS_GATE"] != "NOT_RUN" or document["COUNTER_COMPLETENESS_GATE"] != "NOT_RUN":
        _fail("V62 claim locks changed")
    verification_payload = {
        "schema": "acfqp.residual_factor_library_verification.v62",
        "library_artifact_id": document["library_artifact_id"],
        "source_count": len(sources),
        "raw_transition_row_count": sum(
            len(source["raw_local_transition_rows"]) for source in sources
        ),
        "candidate_binding_evaluation_count": expected_library[
            "candidate_binding_evaluation_count"
        ],
        "compiled_subprogram_count": len(expected_library["compiled_subprograms"]),
        "covered_residual_target_count": len(expected_library["covered_residual_targets"]),
        "uncovered_residual_target_count": len(expected_library["uncovered_residual_targets"]),
        "producer_imported": False,
        "compiler_imported": False,
        "exact_raw_reconstruction_passed": True,
        "scientific_fresh_outcome_verified": False,
        "status": "PRODUCER_FREE_RETROSPECTIVE_PARTIAL_LIBRARY_VERIFIED",
    }
    verification = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v62(
            domains.CONSTRUCTION_K7_RESIDUAL_FACTOR_VERIFICATION_V62_DOMAIN,
            verification_payload,
        ),
    }
    result = canonical_json_bytes(verification)
    if VERIFICATION_ID != "0" * 64 and (
        verification["verification_id"] != VERIFICATION_ID
        or len(result) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(result).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V62 verification changed")
    return result


__all__ = ("verify_residual_factor_library_bytes_v62",)
