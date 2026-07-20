"""Strict public boundary for Phase-3E preconstruction accounting.

The implementation module contains the result-blind mechanics.  This boundary
first validates the one historical Phase-3B document shape with exact integer
semantics so Python's ``True == 1`` and ``1.0 == 1`` rules cannot validate a
forged alias or reconciliation value.
"""

from __future__ import annotations

from typing import Any, Mapping

from acfqp import _phase3e_accounting_impl as _impl
from acfqp.work_accounting import CounterValidationError


COUNTER_COMPLETENESS_NOT_RUN = _impl.COUNTER_COMPLETENESS_NOT_RUN
ECONOMICS_NOT_RUN = _impl.ECONOMICS_NOT_RUN
LEGACY_PROJECTION_LABEL = _impl.LEGACY_PROJECTION_LABEL
NATIVE_REGISTRY_DRAFT = _impl.NATIVE_REGISTRY_DRAFT
PRECONSTRUCTION_PASS = _impl.PRECONSTRUCTION_PASS
ROUTING_MECHANICS_ONLY = _impl.ROUTING_MECHANICS_ONLY
UNRESOLVED = _impl.UNRESOLVED


def _mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CounterValidationError(f"legacy {field} must be a mapping")
    return value


def _exact_fields(
    document: Mapping[str, Any], expected: set[str], *, field: str
) -> None:
    if set(document) != expected:
        missing = sorted(expected - set(document))
        extra = sorted(set(document) - expected)
        raise CounterValidationError(
            f"legacy {field} field set mismatch; missing={missing!r}, extra={extra!r}"
        )


def _integer(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CounterValidationError(
            f"legacy {field} must be a nonnegative exact integer"
        )
    return value


def _strict_phase3b_document(document: Mapping[str, Any]) -> None:
    _exact_fields(
        document,
        {
            "cost_protocol_status",
            "scalar_break_even",
            "reason",
            "build",
            "query",
            "reconciliation",
        },
        field="root",
    )
    if document["cost_protocol_status"] != ECONOMICS_NOT_RUN:
        raise CounterValidationError("legacy source already claims an economics result")
    if document["scalar_break_even"] is not None:
        raise CounterValidationError("legacy scalar_break_even must be explicit null")
    if not isinstance(document["reason"], str) or not document["reason"]:
        raise CounterValidationError("legacy reason must be nonempty text")

    builds = _mapping(document["build"], field="build")
    _exact_fields(builds, {"g2048", "lmb"}, field="build")
    build_fields = {
        "covered_ground_states",
        "ground_state_action_pairs",
        "ground_one_step_outcomes",
        "behavioral_refinement_rounds",
        "portable_model_bytes_canonical_json",
    }
    for domain, raw_row in builds.items():
        row = _mapping(raw_row, field=f"build.{domain}")
        _exact_fields(row, build_fields, field=f"build.{domain}")
        for key, value in row.items():
            _integer(value, field=f"build.{domain}.{key}")

    queries = document["query"]
    if not isinstance(queries, (list, tuple)):
        raise CounterValidationError("legacy query must be a sequence")
    if len(queries) != 11:
        raise CounterValidationError(
            "legacy published Phase3B projection requires exactly 11 occurrences"
        )
    query_fields = {
        "ground_query_id",
        "load",
        "abstract_plan",
        "portable_envelope_audit",
        "ground_certificate_audit",
        "local_ground",
        "full_fallback",
        "evaluation_only_j0",
        "abstract_composed_candidate_count",
        "audit_reachable_cell_horizon_pairs",
        "local_ground_candidate_count",
        "full_fallback_candidate_count",
        "evaluation_only_j0_composed_candidate_count",
    }
    nested_fields = {
        "load": {
            "portable_model_loads",
            "portable_query_loads",
            "portable_model_bytes",
            "portable_query_bytes",
        },
        "abstract_plan": {
            "composed_candidate_count",
            "pareto_frontier_points",
            "selected_decision_nodes",
        },
        "portable_envelope_audit": {"reachable_cell_horizon_pairs"},
        "ground_certificate_audit": {"reachable_cell_horizon_pairs"},
        "local_ground": {"candidate_count"},
        "full_fallback": {"invocation_count", "candidate_count"},
        "evaluation_only_j0": {"composed_candidate_count"},
    }
    alias_pairs = (
        ("abstract_plan", "composed_candidate_count", "abstract_composed_candidate_count"),
        (
            "ground_certificate_audit",
            "reachable_cell_horizon_pairs",
            "audit_reachable_cell_horizon_pairs",
        ),
        ("local_ground", "candidate_count", "local_ground_candidate_count"),
        ("full_fallback", "candidate_count", "full_fallback_candidate_count"),
        (
            "evaluation_only_j0",
            "composed_candidate_count",
            "evaluation_only_j0_composed_candidate_count",
        ),
    )
    for index, raw_row in enumerate(queries):
        row = _mapping(raw_row, field=f"query[{index}]")
        _exact_fields(row, query_fields, field=f"query[{index}]")
        if not isinstance(row["ground_query_id"], str) or not row["ground_query_id"]:
            raise CounterValidationError(
                f"legacy query[{index}].ground_query_id must be nonempty text"
            )
        nested: dict[str, Mapping[str, Any]] = {}
        for name, fields in nested_fields.items():
            nested[name] = _mapping(row[name], field=f"query[{index}].{name}")
            _exact_fields(nested[name], fields, field=f"query[{index}].{name}")
            for key, value in nested[name].items():
                _integer(value, field=f"query[{index}].{name}.{key}")
        for flat in (
            "abstract_composed_candidate_count",
            "audit_reachable_cell_horizon_pairs",
            "local_ground_candidate_count",
            "full_fallback_candidate_count",
            "evaluation_only_j0_composed_candidate_count",
        ):
            _integer(row[flat], field=f"query[{index}].{flat}")
        for name, nested_key, flat in alias_pairs:
            if nested[name][nested_key] != row[flat]:
                raise CounterValidationError(
                    f"legacy alias mismatch at query[{index}].{flat}"
                )

    reconciliation = _mapping(document["reconciliation"], field="reconciliation")
    reconciliation_fields = {
        "query_occurrence_count",
        "portable_model_loads",
        "portable_query_loads",
        "abstract_composed_candidate_count",
        "local_ground_candidate_count",
        "full_fallback_invocation_count",
        "evaluation_only_j0_composed_candidate_count",
    }
    _exact_fields(reconciliation, reconciliation_fields, field="reconciliation")
    for key, value in reconciliation.items():
        _integer(value, field=f"reconciliation.{key}")


def phase3e_native_registry_draft():
    return _impl.phase3e_native_registry_draft()


def legacy_phase3b_registry():
    return _impl.legacy_phase3b_registry()


def legacy_phase3b_projection(document: Mapping[str, Any]) -> dict[str, Any]:
    _strict_phase3b_document(document)
    return _impl.legacy_phase3b_projection(document)


def phase3e_preregistration_skeleton() -> dict[str, Any]:
    return _impl.phase3e_preregistration_skeleton()


__all__ = [
    "COUNTER_COMPLETENESS_NOT_RUN",
    "ECONOMICS_NOT_RUN",
    "LEGACY_PROJECTION_LABEL",
    "NATIVE_REGISTRY_DRAFT",
    "PRECONSTRUCTION_PASS",
    "ROUTING_MECHANICS_ONLY",
    "UNRESOLVED",
    "legacy_phase3b_projection",
    "legacy_phase3b_registry",
    "phase3e_native_registry_draft",
    "phase3e_preregistration_skeleton",
]
