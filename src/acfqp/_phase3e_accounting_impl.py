"""Result-blind Phase-3E accounting mechanics and legacy controls.

This module does not authorize an official workload-economics run.  It provides
an explicitly incomplete native registry candidate, a strict preregistration
skeleton, and a diagnostic-only reproduction of the already-published Phase-3B
coarse projection.  Official scalar costs and break-even fields remain ``None``.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from acfqp.artifacts import object_id
from acfqp.work_accounting import (
    BYTE,
    CHARGED_BYTE,
    CHARGED_OP,
    COUNT,
    DERIVED_ALIAS,
    DIAGNOSTIC_CARDINALITY,
    EVALUATION_ONLY,
    OPERATION,
    OPERATIONAL,
    PROVENANCE_ONLY,
    CounterLeaf,
    CounterRecord,
    CounterRegistry,
    CounterValidationError,
    diagnostic_unit_work_v1,
)


ECONOMICS_NOT_RUN = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
COUNTER_COMPLETENESS_NOT_RUN = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
NATIVE_REGISTRY_DRAFT = "DRAFT_NOT_COUNTER_COMPLETE"
ROUTING_MECHANICS_ONLY = "MECHANICS_ONLY_NO_OFFICIAL_ROUTE_SELECTION"
PRECONSTRUCTION_PASS = "PHASE3E_PRECONSTRUCTION_MECHANICS_PASS"
LEGACY_PROJECTION_LABEL = "DIAGNOSTIC_LEGACY_UNIT_WORK_V1_PROJECTION"
UNRESOLVED = "AWAITING_NORMATIVE_PHASE3E_DECISIONS"


def _op(path: str, owner: str, *, scope: str = OPERATIONAL) -> CounterLeaf:
    return CounterLeaf(path, CHARGED_OP, OPERATION, scope, owner)


def _byte(path: str, owner: str, *, scope: str = OPERATIONAL) -> CounterLeaf:
    return CounterLeaf(path, CHARGED_BYTE, BYTE, scope, owner)


def _diagnostic(path: str, owner: str, *, scope: str = OPERATIONAL) -> CounterLeaf:
    return CounterLeaf(path, DIAGNOSTIC_CARDINALITY, COUNT, scope, owner)


def _alias(
    path: str,
    target: str,
    owner: str,
    *,
    scope: str = OPERATIONAL,
    required: bool = True,
) -> CounterLeaf:
    return CounterLeaf(
        path,
        DERIVED_ALIAS,
        OPERATION,
        scope,
        owner,
        required=required,
        alias_of=target,
    )


def phase3e_native_registry_draft() -> CounterRegistry:
    """Return a result-blind candidate registry, never an official registry."""

    leaves = (
        _op("abstract.candidate_evaluations", "abstract_planner"),
        _op("abstract.dominance_comparisons", "abstract_planner"),
        _op("abstract.invocations", "abstract_planner"),
        _op("abstract.nominal_transition_evaluations", "abstract_planner"),
        _diagnostic("abstract.retained_frontier_points", "abstract_planner"),
        _diagnostic("abstract.selected_decisions", "abstract_planner"),
        _op("bind.concretizer_support_checks", "frozen_model_binder"),
        _op("bind.covered_state_bindings", "frozen_model_binder"),
        _op("bind.ground_action_provider_invocations", "frozen_model_binder"),
        _op("bind.ground_actions_scanned", "frozen_model_binder"),
        _op("bind.invocations", "frozen_model_binder"),
        _op("bind.semantic_action_provider_invocations", "frozen_model_binder"),
        _op("bind.semantic_actions_scanned", "frozen_model_binder"),
        _op("bind.serialized_rows", "frozen_model_binder"),
        _op("bind.structural_candidates_scanned", "frozen_model_binder"),
        _op("build.action_provider_invocations", "world_model_builder"),
        _op("build.coverage_state_visits", "world_model_builder"),
        _byte("build.epoch_bytes_produced", "world_model_builder"),
        _op("build.ground_state_action_evaluations", "world_model_builder"),
        _op("build.invocations", "world_model_builder"),
        _op("build.kernel_transition_evaluations", "world_model_builder"),
        _byte("build.model_bytes_produced", "world_model_builder"),
        _op("build.partition_invocations", "world_model_builder"),
        _op("build.positive_outcome_branches", "world_model_builder"),
        _op("build.quotient_invocations", "world_model_builder"),
        _op("build.rapm_invocations", "world_model_builder"),
        _op("build.refinement_rounds", "world_model_builder"),
        _op("build.refinement_splits", "world_model_builder"),
        _op("build.transition_closure_invocations", "world_model_builder"),
        _op("fallback.action_validations", "ground_fallback"),
        _op("fallback.bellman_nodes", "ground_fallback"),
        _byte("fallback.certificate_bytes_produced", "ground_fallback"),
        _op("fallback.dominance_comparisons", "ground_fallback"),
        _op("fallback.invocations", "ground_fallback"),
        _op("fallback.kernel_transition_evaluations", "ground_fallback"),
        _op("fallback.policy_candidate_evaluations", "ground_fallback"),
        _op("fallback.positive_outcome_branches", "ground_fallback"),
        _op("io.artifact_hash_checks", "operational_io"),
        _op("io.artifact_identity_checks", "operational_io"),
        _op("io.artifact_load_invocations", "operational_io"),
        _byte("io.artifact_read_bytes", "operational_io"),
        _op("io.artifact_schema_checks", "operational_io"),
        _op("io.namespace_setup_attempts", "isolated_runtime"),
        _op("io.namespace_setup_failures", "isolated_runtime"),
        _op("io.process_launch_attempts", "isolated_runtime"),
        _op("io.process_launch_failures", "isolated_runtime"),
        _op("io.process_launch_successes", "isolated_runtime"),
        _byte("io.staged_input_bytes", "isolated_runtime"),
        _byte("io.worker_output_bytes", "isolated_runtime"),
        _op("local.authorization_action_checks", "local_authorizer"),
        _diagnostic("local.authorized_outcomes", "local_authorizer"),
        _diagnostic("local.authorized_state_action_pairs", "local_authorizer"),
        _op("local.capability_compiler_assignments", "local_compiler"),
        _op("local.capability_equivalence_checks", "local_compiler"),
        _op("local.capability_form_evaluations", "local_compiler"),
        _op("local.capability_input_context_checks", "local_compiler"),
        _op("local.capability_input_pair_checks", "local_compiler"),
        _op("local.capability_subset_checks", "local_compiler"),
        _op("local.capability_witness_checks", "local_compiler"),
        _op("local.causal_evaluations", "local_causal_auditor"),
        _op("local.failed_proof_node_evaluations", "local_causal_auditor"),
        _op("local.joint_action_port_evaluations", "local_solver"),
        _op("local.joint_affine_form_evaluations", "local_solver"),
        _op("local.joint_affine_term_evaluations", "local_solver"),
        _op("local.joint_dominance_comparisons", "local_solver"),
        _op("local.joint_policy_assignments", "local_solver"),
        _op("local.joint_subset_evaluations", "local_solver"),
        _op("local.materialization_action_checks", "local_materializer"),
        _op("local.materialization_positive_outcomes", "local_materializer"),
        _op("local.materialization_steps", "local_materializer"),
        _diagnostic("local.stitch_decisions", "hybrid_stitcher"),
        _op("local.stitch_invocations", "hybrid_stitcher"),
        _diagnostic("local.theoretical_policy_space", "local_solver"),
        _op("local.transaction_invocations", "local_recovery"),
        _op("post_audit.action_validations", "hybrid_post_auditor"),
        _op("post_audit.bellman_nodes", "hybrid_post_auditor"),
        _op("post_audit.invocations", "hybrid_post_auditor"),
        _op("post_audit.kernel_transition_evaluations", "hybrid_post_auditor"),
        _op("post_audit.positive_outcome_branches", "hybrid_post_auditor"),
        _op("post_audit.realization_rows", "hybrid_post_auditor"),
        _op("pre_audit.action_validations", "exact_plan_auditor"),
        _op("pre_audit.bellman_nodes", "exact_plan_auditor"),
        _op("pre_audit.invocations", "exact_plan_auditor"),
        _op("pre_audit.kernel_transition_evaluations", "exact_plan_auditor"),
        _op("pre_audit.positive_outcome_branches", "exact_plan_auditor"),
        _op("pre_audit.realization_rows", "exact_plan_auditor"),
        _op("rebuild.identity_mismatch_checks", "epoch_router"),
        _op("rebuild.invocations", "epoch_router"),
        _op("router.cache_checks", "dynamic_router"),
        _op("router.componentwise_comparisons", "dynamic_router"),
        _op("router.coverage_checks", "dynamic_router"),
        _op("router.fallback_upper_derivations", "dynamic_router"),
        _op("router.identity_checks", "dynamic_router"),
        _op("router.local_upper_derivations", "dynamic_router"),
        _diagnostic("router.route_decisions", "dynamic_router"),
        _op("router.semantic_checks", "dynamic_router"),
        _op(
            "evaluation.independent_verifier_invocations",
            "independent_verifier",
            scope=EVALUATION_ONLY,
        ),
        _op(
            "evaluation.independent_verifier_kernel_transitions",
            "independent_verifier",
            scope=EVALUATION_ONLY,
        ),
        _op("evaluation.j0_invocations", "evaluation_j0", scope=EVALUATION_ONLY),
        _op(
            "evaluation.j0_policy_candidate_evaluations",
            "evaluation_j0",
            scope=EVALUATION_ONLY,
        ),
        _byte(
            "provenance.manifest_bytes_produced",
            "artifact_writer",
            scope=PROVENANCE_ONLY,
        ),
    )
    return CounterRegistry(
        "phase3e_native_counter_registry_draft_v0",
        "draft-predecision-v2",
        tuple(sorted(leaves, key=lambda leaf: leaf.path)),
    )


def legacy_phase3b_registry() -> CounterRegistry:
    """Return the separate diagnostic registry for published Phase-3B fields."""

    leaves = (
        _op("build.coverage_states", "legacy_phase3b_build"),
        _op("build.ground_state_action_pairs", "legacy_phase3b_build"),
        _byte("build.model_bytes_produced", "legacy_phase3b_build"),
        _op("build.positive_outcomes", "legacy_phase3b_build"),
        _op("build.refinement_rounds", "legacy_phase3b_build"),
        _op(
            "comparator.ground_candidate_evaluations",
            "legacy_phase3b_j0",
            scope=EVALUATION_ONLY,
        ),
        _diagnostic(
            "comparator.ground_invocations_inferred",
            "legacy_phase3b_adapter",
            scope=EVALUATION_ONLY,
        ),
        _alias(
            "compat.abstract_candidate_flat",
            "query.abstract_candidate_evaluations",
            "legacy_phase3b_alias",
        ),
        _alias(
            "compat.full_fallback_candidate_flat",
            "query.full_fallback_candidate_evaluations",
            "legacy_phase3b_alias",
        ),
        _alias(
            "compat.ground_audit_pair_flat",
            "query.ground_audit_pair_proxy",
            "legacy_phase3b_alias",
        ),
        _alias(
            "compat.ground_candidate_flat",
            "comparator.ground_candidate_evaluations",
            "legacy_phase3b_alias",
            scope=EVALUATION_ONLY,
        ),
        _alias(
            "compat.local_candidate_flat",
            "query.local_candidate_evaluations",
            "legacy_phase3b_alias",
        ),
        _op("query.abstract_candidate_evaluations", "legacy_phase3b_planner"),
        _op(
            "query.full_fallback_candidate_evaluations",
            "legacy_phase3b_fallback",
        ),
        _op("query.full_fallback_invocations", "legacy_phase3b_fallback"),
        _op("query.ground_audit_pair_proxy", "legacy_phase3b_audit_proxy"),
        _op("query.local_candidate_evaluations", "legacy_phase3b_local"),
        _op("query.model_load_invocations", "legacy_phase3b_loader"),
        _byte("query.model_read_bytes", "legacy_phase3b_loader"),
        _op("query.portable_audit_pair_proxy", "legacy_phase3b_audit_proxy"),
        _op("query.query_load_invocations", "legacy_phase3b_loader"),
        _byte("query.query_read_bytes", "legacy_phase3b_loader"),
    )
    return CounterRegistry(
        "phase3b_legacy_unit_work_v1_projection",
        "diagnostic-v2",
        tuple(sorted(leaves, key=lambda leaf: leaf.path)),
    )


def _integer(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CounterValidationError(f"legacy {field} must be a nonnegative integer")
    return value


def _mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CounterValidationError(f"legacy {field} must be a mapping")
    return value


def _fraction_payload(value: Fraction | int) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _validate_phase3b_aliases(document: Mapping[str, Any]) -> None:
    queries = document.get("query")
    if not isinstance(queries, (list, tuple)):
        raise CounterValidationError("legacy Phase3B query counters must be a sequence")
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
        for nested, key, flat in alias_pairs:
            nested_row = _mapping(row.get(nested), field=f"query[{index}].{nested}")
            if nested_row.get(key) != row.get(flat):
                raise CounterValidationError(
                    f"legacy alias mismatch at query[{index}].{flat}"
                )


def legacy_phase3b_projection(document: Mapping[str, Any]) -> dict[str, Any]:
    """Reproduce the published coarse numbers without upgrading their status."""

    if document.get("cost_protocol_status") != ECONOMICS_NOT_RUN:
        raise CounterValidationError("legacy source already claims an economics result")
    if document.get("scalar_break_even") is not None:
        raise CounterValidationError("legacy source unexpectedly contains a scalar result")
    _validate_phase3b_aliases(document)
    builds = _mapping(document.get("build"), field="build")
    reconciliation = _mapping(document.get("reconciliation"), field="reconciliation")
    raw_queries = document.get("query")
    if not isinstance(raw_queries, (list, tuple)) or not raw_queries:
        raise CounterValidationError("legacy campaign has no query occurrences")
    queries = tuple(
        _mapping(row, field=f"query[{index}]")
        for index, row in enumerate(raw_queries)
    )

    build_operations = 0
    build_bytes = 0
    for domain, raw_row in builds.items():
        row = _mapping(raw_row, field=f"build.{domain}")
        build_operations += sum(
            _integer(row[field], field=f"build.{domain}.{field}")
            for field in (
                "covered_ground_states",
                "ground_state_action_pairs",
                "ground_one_step_outcomes",
                "behavioral_refinement_rounds",
            )
        )
        build_bytes += _integer(
            row["portable_model_bytes_canonical_json"],
            field=f"build.{domain}.portable_model_bytes_canonical_json",
        )

    per_occurrence_raw: list[dict[str, Any]] = []
    for index, row in enumerate(queries):
        load = _mapping(row.get("load"), field=f"query[{index}].load")
        abstract = _mapping(row.get("abstract_plan"), field=f"query[{index}].abstract")
        portable_audit = _mapping(
            row.get("portable_envelope_audit"),
            field=f"query[{index}].portable_envelope_audit",
        )
        ground_audit = _mapping(
            row.get("ground_certificate_audit"),
            field=f"query[{index}].ground_certificate_audit",
        )
        local = _mapping(row.get("local_ground"), field=f"query[{index}].local")
        fallback = _mapping(
            row.get("full_fallback"), field=f"query[{index}].full_fallback"
        )
        comparator = _mapping(
            row.get("evaluation_only_j0"),
            field=f"query[{index}].evaluation_only_j0",
        )
        world_operations = sum(
            (
                _integer(load["portable_model_loads"], field="model loads"),
                _integer(load["portable_query_loads"], field="query loads"),
                _integer(abstract["composed_candidate_count"], field="abstract candidates"),
                _integer(
                    portable_audit["reachable_cell_horizon_pairs"],
                    field="portable audit pair proxy",
                ),
                _integer(
                    ground_audit["reachable_cell_horizon_pairs"],
                    field="ground audit pair proxy",
                ),
                _integer(local["candidate_count"], field="local candidates"),
                _integer(fallback["invocation_count"], field="fallback invocations"),
                _integer(fallback["candidate_count"], field="fallback candidates"),
            )
        )
        world_bytes = _integer(load["portable_model_bytes"], field="model bytes") + _integer(
            load["portable_query_bytes"], field="query bytes"
        )
        ground_candidates = _integer(
            comparator["composed_candidate_count"], field="ground candidates"
        )
        per_occurrence_raw.append(
            {
                "index": index,
                "ground_query_id": row.get("ground_query_id"),
                "world_operations": world_operations,
                "world_bytes": world_bytes,
                "world_increment": Fraction(world_operations)
                + Fraction(world_bytes, 4096),
                "ground_candidates": ground_candidates,
                "ground_invocation_inferred": True,
                "ground_increment": Fraction(ground_candidates + 1),
            }
        )

    model_loads = sum(row["load"]["portable_model_loads"] for row in queries)
    query_loads = sum(row["load"]["portable_query_loads"] for row in queries)
    abstract_candidates = sum(
        row["abstract_plan"]["composed_candidate_count"] for row in queries
    )
    portable_audit_pairs = sum(
        row["portable_envelope_audit"]["reachable_cell_horizon_pairs"]
        for row in queries
    )
    ground_audit_pairs = sum(
        row["ground_certificate_audit"]["reachable_cell_horizon_pairs"]
        for row in queries
    )
    local_candidates = sum(row["local_ground"]["candidate_count"] for row in queries)
    fallback_invocations = sum(
        row["full_fallback"]["invocation_count"] for row in queries
    )
    fallback_candidates = sum(
        row["full_fallback"]["candidate_count"] for row in queries
    )
    query_operations = sum(row["world_operations"] for row in per_occurrence_raw)
    model_read_bytes = sum(row["load"]["portable_model_bytes"] for row in queries)
    query_read_bytes = sum(row["load"]["portable_query_bytes"] for row in queries)
    query_bytes = model_read_bytes + query_read_bytes
    ground_candidates = sum(row["ground_candidates"] for row in per_occurrence_raw)
    occurrence_count = len(queries)

    expected_reconciliation = {
        "query_occurrence_count": occurrence_count,
        "portable_model_loads": model_loads,
        "portable_query_loads": query_loads,
        "abstract_composed_candidate_count": abstract_candidates,
        "local_ground_candidate_count": local_candidates,
        "full_fallback_invocation_count": fallback_invocations,
        "evaluation_only_j0_composed_candidate_count": ground_candidates,
    }
    if dict(reconciliation) != expected_reconciliation:
        raise CounterValidationError("legacy Phase3B reconciliation totals disagree")

    registry = legacy_phase3b_registry()
    record = CounterRecord.create(
        registry.registry_id,
        "published-phase3b-campaign",
        {
            "build.coverage_states": sum(
                row["covered_ground_states"] for row in builds.values()
            ),
            "build.ground_state_action_pairs": sum(
                row["ground_state_action_pairs"] for row in builds.values()
            ),
            "build.model_bytes_produced": build_bytes,
            "build.positive_outcomes": sum(
                row["ground_one_step_outcomes"] for row in builds.values()
            ),
            "build.refinement_rounds": sum(
                row["behavioral_refinement_rounds"] for row in builds.values()
            ),
            "comparator.ground_candidate_evaluations": ground_candidates,
            "comparator.ground_invocations_inferred": occurrence_count,
            "compat.abstract_candidate_flat": abstract_candidates,
            "compat.full_fallback_candidate_flat": fallback_candidates,
            "compat.ground_audit_pair_flat": ground_audit_pairs,
            "compat.ground_candidate_flat": ground_candidates,
            "compat.local_candidate_flat": local_candidates,
            "query.abstract_candidate_evaluations": abstract_candidates,
            "query.full_fallback_candidate_evaluations": fallback_candidates,
            "query.full_fallback_invocations": fallback_invocations,
            "query.ground_audit_pair_proxy": ground_audit_pairs,
            "query.local_candidate_evaluations": local_candidates,
            "query.model_load_invocations": model_loads,
            "query.model_read_bytes": model_read_bytes,
            "query.portable_audit_pair_proxy": portable_audit_pairs,
            "query.query_load_invocations": query_loads,
            "query.query_read_bytes": query_read_bytes,
        },
    )
    vector = registry.reconcile(record)

    build_cost = Fraction(build_operations) + Fraction(build_bytes, 4096)
    query_cost = Fraction(query_operations) + Fraction(query_bytes, 4096)
    world_cost = build_cost + query_cost
    if diagnostic_unit_work_v1(vector, registry) != world_cost:
        raise CounterValidationError("legacy WorkVector does not reconcile to world total")
    ground_cost = Fraction(ground_candidates + occurrence_count)

    cumulative_world = build_cost
    cumulative_ground = Fraction(0)
    registered_break_even: int | str = "NOT_REACHED"
    occurrence_trace: list[dict[str, Any]] = []
    for prefix, row in enumerate(per_occurrence_raw, start=1):
        cumulative_world += row["world_increment"]
        cumulative_ground += row["ground_increment"]
        crosses = cumulative_world <= cumulative_ground
        if registered_break_even == "NOT_REACHED" and crosses:
            registered_break_even = prefix
        occurrence_trace.append(
            {
                "index": row["index"],
                "prefix_length": prefix,
                "ground_query_id": row["ground_query_id"],
                "world_operations": row["world_operations"],
                "world_bytes": row["world_bytes"],
                "world_increment": _fraction_payload(row["world_increment"]),
                "ground_candidates": row["ground_candidates"],
                "ground_invocation_inferred": True,
                "ground_increment": _fraction_payload(row["ground_increment"]),
                "cumulative_world": _fraction_payload(cumulative_world),
                "cumulative_ground": _fraction_payload(cumulative_ground),
                "diagnostic_crossing_reached": crosses,
            }
        )

    advantages = tuple(
        row["ground_increment"] - row["world_increment"]
        for row in per_occurrence_raw
    )
    if sum(advantages, Fraction(0)) < build_cost:
        worst_order_break_even: int | str = "NOT_REACHED"
    else:
        noncrossing_masks = {0}
        for mask in range(1 << occurrence_count):
            if mask not in noncrossing_masks:
                continue
            for index in range(occurrence_count):
                bit = 1 << index
                if mask & bit:
                    continue
                candidate = mask | bit
                cumulative_advantage = sum(
                    advantages[position]
                    for position in range(occurrence_count)
                    if candidate & (1 << position)
                )
                if cumulative_advantage < build_cost:
                    noncrossing_masks.add(candidate)
        worst_order_break_even = max(
            mask.bit_count() for mask in noncrossing_masks
        ) + 1

    expected = {
        "build_operations": 1022,
        "build_bytes": 207753,
        "query_operations": 185,
        "query_bytes": 1218041,
        "ground_candidates": 114467,
        "ground_invocation_proxy": 11,
        "build_cost": Fraction(4393865, 4096),
        "world_cost": Fraction(3184833, 2048),
        "ground_cost": Fraction(114478),
        "registered_break_even": 1,
        "worst_break_even": 5,
    }
    actual = {
        "build_operations": build_operations,
        "build_bytes": build_bytes,
        "query_operations": query_operations,
        "query_bytes": query_bytes,
        "ground_candidates": ground_candidates,
        "ground_invocation_proxy": occurrence_count,
        "build_cost": build_cost,
        "world_cost": world_cost,
        "ground_cost": ground_cost,
        "registered_break_even": registered_break_even,
        "worst_break_even": worst_order_break_even,
    }
    if actual != expected:
        raise CounterValidationError(
            f"published Phase3B diagnostic projection changed: {actual!r}"
        )

    payload = {
        "schema": "acfqp.legacy_unit_work_projection.phase3e_preconstruction.v1",
        "label": LEGACY_PROJECTION_LABEL,
        "economics_gate_status": ECONOMICS_NOT_RUN,
        "counter_completeness_gate_status": COUNTER_COMPLETENESS_NOT_RUN,
        "registry_id": registry.registry_id,
        "record_id": record.record_id,
        "vector_id": vector.vector_id,
        "official_scalar_cost": None,
        "official_n_break_even": None,
        "diagnostic_unit_work_v1": {
            "definition": (
                "legacy operational proxies: operations + bytes/4096; ground adds "
                "one inferred invocation proxy per registered occurrence"
            ),
            "byte_divisor": 4096,
            "linear_bytes_without_ceiling": True,
            "build": _fraction_payload(build_cost),
            "world_query_campaign": _fraction_payload(query_cost),
            "world_total": _fraction_payload(world_cost),
            "ground_comparator": _fraction_payload(ground_cost),
            "registered_order_n_break_even": registered_break_even,
            "diagnostic_worst_order_n_break_even": worst_order_break_even,
        },
        "per_occurrence_prefix_trace": occurrence_trace,
        "legacy_limitations": (
            "ground comparator invocation count is inferred from occurrence count",
            "portable and live audit cell-horizon pairs are operation proxies",
            "Phase3B performs uncharged repeated audit/planner work not in this schema",
            "order sensitivity is a post-publication diagnostic only",
            "no official scalar, workload robustness, or economics PASS is authorized",
        ),
        "source_counts": {
            "build_operations": build_operations,
            "build_bytes": build_bytes,
            "query_operations": query_operations,
            "query_bytes": query_bytes,
            "ground_candidates": ground_candidates,
            "ground_invocations_inferred": occurrence_count,
            "fallback_invocations": fallback_invocations,
            "fallback_candidates": fallback_candidates,
        },
    }
    return {
        **payload,
        "projection_id": object_id(payload, "legacy-work-projection"),
        "counter_registry": registry.to_dict(),
        "counter_record": record.to_dict(),
        "work_vector": vector.to_dict(),
    }


def phase3e_preregistration_skeleton() -> dict[str, Any]:
    """Return a result-blind skeleton whose unresolved fields prohibit execution."""

    native = phase3e_native_registry_draft()
    payload = {
        "schema": "acfqp.phase3e_preregistration_skeleton.v1",
        "status": UNRESOLVED,
        "official_execution_allowed": False,
        "decision_hash": None,
        "native_counter_registry_status": NATIVE_REGISTRY_DRAFT,
        "counter_registry_candidate_id": native.registry_id,
        "normative_counter_registry_id": None,
        "counter_completeness_gate_status": COUNTER_COMPLETENESS_NOT_RUN,
        "routing_protocol_status": ROUTING_MECHANICS_ONLY,
        "official_scalar_cost_functional": None,
        "official_workload_id": None,
        "reference_machine_profile_id": None,
        "wall_time_protocol_id": None,
        "route_cap_profile_id": None,
        "order_robustness_threshold": None,
        "wall_time_gate_threshold": None,
        "official_n_break_even": None,
        "unresolved_questions": tuple(f"Q{index}" for index in range(1, 12)),
        "unresolved_addenda": (
            "marginal_local_attempt_upper_vs_contingent_local_plus_fallback",
            "scalar_free_vector_routing_vs_scalar_order_break_even_gate",
            "phase3c_phase3d_operational_host_solver_replay_ownership",
            "maximum_rebuild_attempts_and_retry_denominator_ownership",
            "fallback_cap_exhaustion_terminal_status",
            "maximum_local_transactions_and_per_transaction_caps",
            "native_io_and_all_route_counter_completeness",
        ),
        "permitted_before_freeze": (
            "work_vector_and_alias_validation",
            "counter_completeness_negative_tests",
            "route_state_machine_mechanics",
            "artifact_schema_skeleton",
            "legacy_diagnostic_projection",
        ),
        "forbidden_before_freeze": (
            "official_phase3e_workload_execution",
            "official_scalar_break_even",
            "official_wall_time_gate",
            "official_dynamic_route_selection",
            "post_result_threshold_or_route_selection",
        ),
        "economics_gate_status": ECONOMICS_NOT_RUN,
    }
    return {**payload, "skeleton_id": object_id(payload, "phase3e-preregistration")}


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
