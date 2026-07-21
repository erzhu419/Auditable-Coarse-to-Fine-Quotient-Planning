"""Phase 3E domain-separated content identifiers.

This module is deliberately independent from :mod:`acfqp.artifacts`.  The
legacy artifact helpers remain the authority for the 0.x contracts; Phase 3E
uses full SHA-256 identifiers over a stricter JSON value language and an
explicit domain tag.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from collections.abc import Collection, Mapping
from fractions import Fraction
from types import MappingProxyType
from typing import Any


class Phase3EIdentityError(ValueError):
    """Raised when a Phase 3E identity input is not canonical or well typed."""


ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN = "acfqp:route-upper-bound-envelope:v1"
ROUTE_UPPER_FORMULA_DOMAIN = "acfqp:route-upper-formula:v1"
ROUTE_UPPER_DERIVATION_PROOF_DOMAIN = "acfqp:route-upper-derivation-proof:v1"
COMPARISON_PROFILE_DOMAIN = "acfqp:comparison-profile:v1"
COUNTER_REGISTRY_DOMAIN = "acfqp:counter-registry:v1"
CARDINALITY_EVIDENCE_DOMAIN = "acfqp:cardinality-evidence:v1"
CARDINALITY_SOURCE_DOMAIN = "acfqp:cardinality-source:v1"
ROUTE_CAP_PROFILE_DOMAIN = "acfqp:route-cap-profile:v1"
FRONTIER_SNAPSHOT_DOMAIN = "acfqp:frontier-snapshot:v1"
CAUSAL_EVIDENCE_DOMAIN = "acfqp:causal-evidence:v1"
DECISION_POINT_DOMAIN = "acfqp:decision-point:v1"
TRANSACTION_DOMAIN = "acfqp:transaction:v1"
ROUTE_DECISION_CONTEXT_DOMAIN = "acfqp:route-decision-context:v1"
ROUTE_DECISION_DOMAIN = "acfqp:route-decision:v1"
TRUSTED_BUDGET_REPLAY_DOMAIN = "acfqp:trusted-budget-replay:v1"
TERMINAL_ARTIFACT_DOMAIN = "acfqp:terminal-artifact:v1"
TYPED_VERIFICATION_ATTESTATION_DOMAIN = (
    "acfqp:typed-verification-attestation:v1"
)
COUNTER_RECORD_DOMAIN = "acfqp:counter-record:v1"
WORK_VECTOR_DOMAIN = "acfqp:work-vector:v1"
COMPARISON_VECTOR_DOMAIN = "acfqp:comparison-vector:v1"
NATIVE_ZERO_ATTESTATION_DOMAIN = "acfqp:native-zero-attestation:v1"
RECONCILIATION_PROOF_DOMAIN = "acfqp:reconciliation-proof:v1"
ACTUAL_PROJECTION_PROFILE_DOMAIN = "acfqp:actual-projection-profile:v1"
ACTUAL_PROJECTION_PROOF_DOMAIN = "acfqp:actual-projection-proof:v1"
OCCURRENCE_WORK_SUM_DOMAIN = "acfqp:occurrence-work-sum:v1"
WORKLOAD_VECTOR_SPEC_DOMAIN = "acfqp:workload-vector-spec:v1"
WORKLOAD_VECTOR_PREFIX_DOMAIN = "acfqp:workload-vector-prefix:v1"
WORKLOAD_VECTOR_ANALYSIS_DOMAIN = "acfqp:workload-vector-analysis:v1"
LOGICAL_OCCURRENCE_DOMAIN = "acfqp:logical-occurrence:v1"
ROUTE_ATTEMPT_DOMAIN = "acfqp:route-attempt:v1"
REBUILD_POLICY_DOMAIN = "acfqp:rebuild-policy:v1"
REBUILD_EVENT_DOMAIN = "acfqp:rebuild-event:v1"
BOUNDED_REBUILD_OCCURRENCE_WORK_SUM_DOMAIN = (
    "acfqp:bounded-rebuild-occurrence-work-sum:v1"
)
CAMPAIGN_OCCURRENCE_CLOSURE_DOMAIN = "acfqp:campaign-occurrence-closure:v1"
CAMPAIGN_SUMMARY_DOMAIN = "acfqp:campaign-summary:v1"
ACCESS_EVENT_LOG_DOMAIN = "acfqp:access-event-log:v1"
PROTOCOL_SEQUENCE_PROFILE_DOMAIN = "acfqp:protocol-sequence-profile:v1"
ROUTE_DECISION_FREEZE_ATTESTATION_DOMAIN = (
    "acfqp:route-decision-freeze-attestation:v1"
)
FORBIDDEN_ACCESS_VIOLATION_DOMAIN = "acfqp:forbidden-access-violation:v1"
GROUND_FALLBACK_CAP_PROFILE_DOMAIN = "acfqp:ground-fallback-cap-profile:v1"
SEALED_GROUND_FALLBACK_ROUTE_CAP_PROFILE_DOMAIN = (
    "acfqp:sealed-ground-fallback-route-cap-profile:v1"
)
GROUND_FALLBACK_CARDINALITY_BOUND_DOMAIN = (
    "acfqp:ground-fallback-cardinality-bound:v1"
)
GROUND_FALLBACK_CARDINALITY_SOURCE_DOMAIN = (
    "acfqp:ground-fallback-cardinality-source:v1"
)
GROUND_FALLBACK_PARENT_BINDING_DOMAIN = (
    "acfqp:ground-fallback-parent-binding:v1"
)
GROUND_FALLBACK_EXTRACTION_PROFILE_DOMAIN = (
    "acfqp:ground-fallback-extraction-profile:v1"
)
GROUND_FALLBACK_RESULT_DOMAIN = "acfqp:ground-fallback-result:v1"
GROUND_FALLBACK_ISOLATION_PROFILE_DOMAIN = (
    "acfqp:ground-fallback-isolation-profile:v1"
)
GROUND_FALLBACK_ISOLATED_REQUEST_DOMAIN = (
    "acfqp:ground-fallback-isolated-request:v1"
)
GROUND_FALLBACK_ISOLATED_OUTPUT_DOMAIN = (
    "acfqp:ground-fallback-isolated-output:v1"
)
GROUND_FALLBACK_ISOLATED_ATTESTATION_DOMAIN = (
    "acfqp:ground-fallback-isolated-attestation:v1"
)
LOCAL_PRESELECTION_SOURCE_DOMAIN = "acfqp:local-preselection-source:v1"
LOCAL_CARDINALITY_BOUND_DOMAIN = "acfqp:local-cardinality-bound:v1"
LOCAL_PRESELECTION_PARENT_BINDING_DOMAIN = (
    "acfqp:local-preselection-parent-binding:v1"
)
LOCAL_PRESELECTION_EXTRACTION_PROFILE_DOMAIN = (
    "acfqp:local-preselection-extraction-profile:v1"
)
LOCAL_PROOF_OBLIGATION_DOMAIN = "acfqp:local-proof-obligation:v1"
LOCAL_TRANSACTION_RESULT_DOMAIN = "acfqp:local-transaction-result:v1"
POST_AUDIT_CERTIFICATE_DOMAIN = "acfqp:post-audit-certificate:v1"
PHASE3D_LOCAL_PARENT_BINDING_DOMAIN = (
    "acfqp:phase3d-local-parent-binding:v1"
)
MARGINAL_WORK_AGGREGATION_PROOF_DOMAIN = (
    "acfqp:marginal-work-aggregation-proof:v1"
)
OCCURRENCE_WORK_COMPONENT_REF_DOMAIN = (
    "acfqp:occurrence-work-component-ref:v1"
)
OCCURRENCE_WORK_AGGREGATE_DOMAIN = "acfqp:occurrence-work-aggregate:v1"
OCCURRENCE_PARTIAL_COMMON_ACCOUNTING_DOMAIN = (
    "acfqp:occurrence-partial-common-accounting:v1"
)
OCCURRENCE_FAILURE_EVIDENCE_BINDING_DOMAIN = (
    "acfqp:phase3e-occurrence-failure-evidence-binding:v1"
)
OCCURRENCE_FAILURE_TERMINAL_DOMAIN = (
    "acfqp:phase3e-occurrence-failure-terminal:v1"
)
OCCURRENCE_CLOSURE_EVIDENCE_DOMAIN = (
    "acfqp:phase3e-occurrence-closure-evidence:v1"
)
MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN = (
    "acfqp:model-failure-occurrence-closure:v1"
)
MODEL_FAILURE_PREPARATION_TRACE_DOMAIN = (
    "acfqp:model-failure-preparation-trace:v1"
)
MODEL_FAILURE_PREPARATION_ACCOUNTING_DOMAIN = (
    "acfqp:model-failure-preparation-accounting:v1"
)
OCCURRENCE_CONTROL_FAILURE_DOMAIN = (
    "acfqp:phase3e-occurrence-control-failure:v1"
)
OCCURRENCE_TERMINAL_ARTIFACT_DOMAIN = (
    "acfqp:phase3e-occurrence-terminal-artifact:v1"
)
PRESELECTION_NOT_APPLICABLE_BINDING_DOMAIN = (
    "acfqp:preselection-not-applicable-binding:v1"
)
ACCOUNTING_CORE_SEAL_DOMAIN = "acfqp:accounting-core-seal:v1"
VERIFICATION_CHARGE_PLAN_DOMAIN = "acfqp:verification-charge-plan:v1"
VERIFICATION_CHARGE_ENTRY_DOMAIN = "acfqp:verification-charge-entry:v1"
TWO_STAGE_WORK_AGGREGATE_DOMAIN = "acfqp:two-stage-work-aggregate:v1"
VERIFICATION_CHARGE_MANIFEST_DOMAIN = (
    "acfqp:verification-charge-manifest:v1"
)
VERIFICATION_CHARGE_RECEIPT_DOMAIN = (
    "acfqp:verification-charge-receipt:v1"
)
NONSEMANTIC_VERIFICATION_ATTESTATION_DOMAIN = (
    "acfqp:nonsemantic-verification-attestation:v1"
)
CONTINUATION_WORK_VECTOR_AUTHORITY_DOMAIN = (
    "acfqp:continuation-work-vector-authority:v1"
)
RUNTIME_TREE_MANIFEST_DOMAIN = "acfqp:runtime-tree-manifest:v1"
EXECUTOR_RECIPE_DOMAIN = "acfqp:executor-recipe:v1"
TRUSTED_CONSTRUCTOR_REGISTRY_DOMAIN = (
    "acfqp:trusted-constructor-registry:v1"
)
RUNTIME_MANIFEST_CAP_PROFILE_DOMAIN = (
    "acfqp:runtime-manifest-cap-profile:v1"
)
RUNTIME_FACTORY_CARDINALITY_DOMAIN = (
    "acfqp:runtime-factory-cardinality:v1"
)
SEALED_EXECUTOR_CONSTRUCTION_RECEIPT_DOMAIN = (
    "acfqp:sealed-executor-construction-receipt:v1"
)
SEALED_EXECUTOR_FAILURE_EVIDENCE_DOMAIN = (
    "acfqp:sealed-executor-failure-evidence:v1"
)
SEALED_EXECUTOR_EXECUTION_MERGE_PROOF_DOMAIN = (
    "acfqp:sealed-executor-execution-merge-proof:v1"
)
SEALED_EXECUTOR_FAILURE_MERGE_PROOF_DOMAIN = (
    "acfqp:sealed-executor-failure-merge-proof:v1"
)
RAPM_SOURCE_LEASE_DOMAIN = "acfqp:rapm-source-lease:v1"
SELECTED_CONTINGENT_PLAN_DOMAIN = "acfqp:selected-contingent-plan:v1"
PORTABLE_POLICY_BINDING_DOMAIN = "acfqp:portable-policy-binding:v1"
PORTABLE_SOUND_BELLMAN_PROOF_DOMAIN = (
    "acfqp:portable-sound-bellman-proof:v1"
)
ABSTRACT_PLAN_AUDIT_DOMAIN = "acfqp:abstract-plan-audit:v1"
PLAN_FROZEN_EXACT_CACHE_BINDING_DOMAIN = (
    "acfqp:plan-frozen-exact-cache-binding:v1"
)
VERIFIED_EXACT_INFEASIBILITY_SOURCE_DOMAIN = (
    "acfqp:verified-exact-infeasibility-source:v1"
)
EXACT_CACHED_INFEASIBILITY_PROOF_DOMAIN = (
    "acfqp:exact-cached-infeasibility-proof:v1"
)
EXACT_KERNEL_CONTEXT_IDENTITY_DOMAIN = (
    "acfqp:exact-kernel-context-identity:v1"
)
EXACT_INFEASIBILITY_PROOF_PROFILE_DOMAIN = (
    "acfqp:exact-infeasibility-proof-profile:v1"
)
EXACT_CACHE_PREFLIGHT_REQUEST_DOMAIN = (
    "acfqp:exact-cache-preflight-request:v1"
)
EXACT_CACHE_PREFLIGHT_ENTRY_DOMAIN = "acfqp:exact-cache-preflight-entry:v1"
EXACT_CACHE_PREFLIGHT_RESULT_DOMAIN = "acfqp:exact-cache-preflight-result:v1"
MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN = (
    "acfqp:phase3e-model-only-orchestration-binding:v1"
)
MODEL_ONLY_RESULT_DOMAIN = "acfqp:phase3e-model-only-result:v1"
ABSTRACT_ONLY_OCCURRENCE_WORK_SUM_DOMAIN = (
    "acfqp:abstract-only-occurrence-work-sum:v1"
)
MODEL_ONLY_OPERATIONAL_REQUEST_DOMAIN = (
    "acfqp:model-only-operational-request:v1"
)
MODEL_ONLY_OPERATIONAL_EXECUTION_DOMAIN = (
    "acfqp:model-only-operational-execution:v1"
)
GROUND_BINDING_AFTER_FAILED_AUDIT_DOMAIN = (
    "acfqp:ground-binding-after-failed-audit:v1"
)
MODEL_ONLY_FAILED_PREFIX_ACCOUNTING_AUTHORITY_DOMAIN = (
    "acfqp:model-only-failed-prefix-accounting-authority:v1"
)
DEPENDENT_POSTAUDIT_OBLIGATION_DOMAIN = (
    "acfqp:dependent-postaudit-obligation:v1"
)
DEPENDENT_FRONTIER_DERIVATION_DOMAIN = (
    "acfqp:dependent-frontier-derivation:v1"
)
DEPENDENT_TRANSACTION_BENCHMARK_PROFILE_DOMAIN = (
    "acfqp:dependent-transaction-benchmark-profile:v1"
)
GROUND_DERIVED_TRANSACTION_TWO_FEASIBILITY_AUDIT_DOMAIN = (
    "acfqp:ground-derived-transaction-two-feasibility-audit:v1"
)
RECORDED_WORK_TRANSPORT_DOMAIN = "acfqp:recorded-work-transport:v1"
PHASE3E_BUNDLE_MANIFEST_DOMAIN = "acfqp:phase3e-bundle-manifest:v1"
SELECTED_ROUTE_BUNDLE_MANIFEST_DOMAIN = (
    "acfqp:selected-route-bundle-manifest:v1"
)


PHASE3E_DOMAIN_TAG_REGISTRY: Mapping[str, str] = MappingProxyType(
    {
        "route_upper_bound_envelope": ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN,
        "route_upper_formula": ROUTE_UPPER_FORMULA_DOMAIN,
        "route_upper_derivation_proof": ROUTE_UPPER_DERIVATION_PROOF_DOMAIN,
        "comparison_profile": COMPARISON_PROFILE_DOMAIN,
        "counter_registry": COUNTER_REGISTRY_DOMAIN,
        "cardinality_evidence": CARDINALITY_EVIDENCE_DOMAIN,
        "cardinality_source": CARDINALITY_SOURCE_DOMAIN,
        "route_cap_profile": ROUTE_CAP_PROFILE_DOMAIN,
        "frontier_snapshot": FRONTIER_SNAPSHOT_DOMAIN,
        "causal_evidence": CAUSAL_EVIDENCE_DOMAIN,
        "decision_point": DECISION_POINT_DOMAIN,
        "transaction": TRANSACTION_DOMAIN,
        "route_decision_context": ROUTE_DECISION_CONTEXT_DOMAIN,
        "route_decision": ROUTE_DECISION_DOMAIN,
        "trusted_budget_replay": TRUSTED_BUDGET_REPLAY_DOMAIN,
        "terminal_artifact": TERMINAL_ARTIFACT_DOMAIN,
        "typed_verification_attestation": TYPED_VERIFICATION_ATTESTATION_DOMAIN,
        "counter_record": COUNTER_RECORD_DOMAIN,
        "work_vector": WORK_VECTOR_DOMAIN,
        "comparison_vector": COMPARISON_VECTOR_DOMAIN,
        "native_zero_attestation": NATIVE_ZERO_ATTESTATION_DOMAIN,
        "reconciliation_proof": RECONCILIATION_PROOF_DOMAIN,
        "actual_projection_profile": ACTUAL_PROJECTION_PROFILE_DOMAIN,
        "actual_projection_proof": ACTUAL_PROJECTION_PROOF_DOMAIN,
        "occurrence_work_sum": OCCURRENCE_WORK_SUM_DOMAIN,
        "workload_vector_spec": WORKLOAD_VECTOR_SPEC_DOMAIN,
        "workload_vector_prefix": WORKLOAD_VECTOR_PREFIX_DOMAIN,
        "workload_vector_analysis": WORKLOAD_VECTOR_ANALYSIS_DOMAIN,
        "logical_occurrence": LOGICAL_OCCURRENCE_DOMAIN,
        "route_attempt": ROUTE_ATTEMPT_DOMAIN,
        "rebuild_policy": REBUILD_POLICY_DOMAIN,
        "rebuild_event": REBUILD_EVENT_DOMAIN,
        "bounded_rebuild_occurrence_work_sum": (
            BOUNDED_REBUILD_OCCURRENCE_WORK_SUM_DOMAIN
        ),
        "campaign_occurrence_closure": CAMPAIGN_OCCURRENCE_CLOSURE_DOMAIN,
        "campaign_summary": CAMPAIGN_SUMMARY_DOMAIN,
        "access_event_log": ACCESS_EVENT_LOG_DOMAIN,
        "protocol_sequence_profile": PROTOCOL_SEQUENCE_PROFILE_DOMAIN,
        "route_decision_freeze_attestation": (
            ROUTE_DECISION_FREEZE_ATTESTATION_DOMAIN
        ),
        "forbidden_access_violation": FORBIDDEN_ACCESS_VIOLATION_DOMAIN,
        "ground_fallback_cap_profile": GROUND_FALLBACK_CAP_PROFILE_DOMAIN,
        "sealed_ground_fallback_route_cap_profile": (
            SEALED_GROUND_FALLBACK_ROUTE_CAP_PROFILE_DOMAIN
        ),
        "ground_fallback_cardinality_bound": (
            GROUND_FALLBACK_CARDINALITY_BOUND_DOMAIN
        ),
        "ground_fallback_cardinality_source": (
            GROUND_FALLBACK_CARDINALITY_SOURCE_DOMAIN
        ),
        "ground_fallback_parent_binding": (
            GROUND_FALLBACK_PARENT_BINDING_DOMAIN
        ),
        "ground_fallback_extraction_profile": (
            GROUND_FALLBACK_EXTRACTION_PROFILE_DOMAIN
        ),
        "ground_fallback_result": GROUND_FALLBACK_RESULT_DOMAIN,
        "ground_fallback_isolation_profile": (
            GROUND_FALLBACK_ISOLATION_PROFILE_DOMAIN
        ),
        "ground_fallback_isolated_request": (
            GROUND_FALLBACK_ISOLATED_REQUEST_DOMAIN
        ),
        "ground_fallback_isolated_output": (
            GROUND_FALLBACK_ISOLATED_OUTPUT_DOMAIN
        ),
        "ground_fallback_isolated_attestation": (
            GROUND_FALLBACK_ISOLATED_ATTESTATION_DOMAIN
        ),
        "local_preselection_source": LOCAL_PRESELECTION_SOURCE_DOMAIN,
        "local_cardinality_bound": LOCAL_CARDINALITY_BOUND_DOMAIN,
        "local_preselection_parent_binding": (
            LOCAL_PRESELECTION_PARENT_BINDING_DOMAIN
        ),
        "local_preselection_extraction_profile": (
            LOCAL_PRESELECTION_EXTRACTION_PROFILE_DOMAIN
        ),
        "local_proof_obligation": LOCAL_PROOF_OBLIGATION_DOMAIN,
        "local_transaction_result": LOCAL_TRANSACTION_RESULT_DOMAIN,
        "post_audit_certificate": POST_AUDIT_CERTIFICATE_DOMAIN,
        "phase3d_local_parent_binding": PHASE3D_LOCAL_PARENT_BINDING_DOMAIN,
        "marginal_work_aggregation_proof": (
            MARGINAL_WORK_AGGREGATION_PROOF_DOMAIN
        ),
        "occurrence_work_component_ref": (
            OCCURRENCE_WORK_COMPONENT_REF_DOMAIN
        ),
        "occurrence_work_aggregate": OCCURRENCE_WORK_AGGREGATE_DOMAIN,
        "occurrence_partial_common_accounting": (
            OCCURRENCE_PARTIAL_COMMON_ACCOUNTING_DOMAIN
        ),
        "occurrence_failure_evidence_binding": (
            OCCURRENCE_FAILURE_EVIDENCE_BINDING_DOMAIN
        ),
        "occurrence_failure_terminal": OCCURRENCE_FAILURE_TERMINAL_DOMAIN,
        "occurrence_closure_evidence": OCCURRENCE_CLOSURE_EVIDENCE_DOMAIN,
        "model_failure_occurrence_closure": (
            MODEL_FAILURE_OCCURRENCE_CLOSURE_DOMAIN
        ),
        "model_failure_preparation_trace": (
            MODEL_FAILURE_PREPARATION_TRACE_DOMAIN
        ),
        "model_failure_preparation_accounting": (
            MODEL_FAILURE_PREPARATION_ACCOUNTING_DOMAIN
        ),
        "occurrence_control_failure": OCCURRENCE_CONTROL_FAILURE_DOMAIN,
        "occurrence_terminal_artifact": OCCURRENCE_TERMINAL_ARTIFACT_DOMAIN,
        "preselection_not_applicable_binding": (
            PRESELECTION_NOT_APPLICABLE_BINDING_DOMAIN
        ),
        "accounting_core_seal": ACCOUNTING_CORE_SEAL_DOMAIN,
        "verification_charge_plan": VERIFICATION_CHARGE_PLAN_DOMAIN,
        "verification_charge_entry": VERIFICATION_CHARGE_ENTRY_DOMAIN,
        "two_stage_work_aggregate": TWO_STAGE_WORK_AGGREGATE_DOMAIN,
        "verification_charge_manifest": VERIFICATION_CHARGE_MANIFEST_DOMAIN,
        "verification_charge_receipt": VERIFICATION_CHARGE_RECEIPT_DOMAIN,
        "nonsemantic_verification_attestation": (
            NONSEMANTIC_VERIFICATION_ATTESTATION_DOMAIN
        ),
        "continuation_work_vector_authority": (
            CONTINUATION_WORK_VECTOR_AUTHORITY_DOMAIN
        ),
        "runtime_tree_manifest": RUNTIME_TREE_MANIFEST_DOMAIN,
        "executor_recipe": EXECUTOR_RECIPE_DOMAIN,
        "trusted_constructor_registry": TRUSTED_CONSTRUCTOR_REGISTRY_DOMAIN,
        "runtime_manifest_cap_profile": RUNTIME_MANIFEST_CAP_PROFILE_DOMAIN,
        "runtime_factory_cardinality": RUNTIME_FACTORY_CARDINALITY_DOMAIN,
        "sealed_executor_construction_receipt": (
            SEALED_EXECUTOR_CONSTRUCTION_RECEIPT_DOMAIN
        ),
        "sealed_executor_failure_evidence": (
            SEALED_EXECUTOR_FAILURE_EVIDENCE_DOMAIN
        ),
        "sealed_executor_execution_merge_proof": (
            SEALED_EXECUTOR_EXECUTION_MERGE_PROOF_DOMAIN
        ),
        "sealed_executor_failure_merge_proof": (
            SEALED_EXECUTOR_FAILURE_MERGE_PROOF_DOMAIN
        ),
        "rapm_source_lease": RAPM_SOURCE_LEASE_DOMAIN,
        "selected_contingent_plan": SELECTED_CONTINGENT_PLAN_DOMAIN,
        "portable_policy_binding": PORTABLE_POLICY_BINDING_DOMAIN,
        "portable_sound_bellman_proof": PORTABLE_SOUND_BELLMAN_PROOF_DOMAIN,
        "abstract_plan_audit": ABSTRACT_PLAN_AUDIT_DOMAIN,
        "plan_frozen_exact_cache_binding": (
            PLAN_FROZEN_EXACT_CACHE_BINDING_DOMAIN
        ),
        "verified_exact_infeasibility_source": (
            VERIFIED_EXACT_INFEASIBILITY_SOURCE_DOMAIN
        ),
        "exact_cached_infeasibility_proof": (
            EXACT_CACHED_INFEASIBILITY_PROOF_DOMAIN
        ),
        "exact_kernel_context_identity": EXACT_KERNEL_CONTEXT_IDENTITY_DOMAIN,
        "exact_infeasibility_proof_profile": (
            EXACT_INFEASIBILITY_PROOF_PROFILE_DOMAIN
        ),
        "exact_cache_preflight_request": EXACT_CACHE_PREFLIGHT_REQUEST_DOMAIN,
        "exact_cache_preflight_entry": EXACT_CACHE_PREFLIGHT_ENTRY_DOMAIN,
        "exact_cache_preflight_result": EXACT_CACHE_PREFLIGHT_RESULT_DOMAIN,
        "model_only_orchestration_binding": (
            MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN
        ),
        "model_only_result": MODEL_ONLY_RESULT_DOMAIN,
        "abstract_only_occurrence_work_sum": (
            ABSTRACT_ONLY_OCCURRENCE_WORK_SUM_DOMAIN
        ),
        "model_only_operational_request": MODEL_ONLY_OPERATIONAL_REQUEST_DOMAIN,
        "model_only_operational_execution": (
            MODEL_ONLY_OPERATIONAL_EXECUTION_DOMAIN
        ),
        "ground_binding_after_failed_audit": (
            GROUND_BINDING_AFTER_FAILED_AUDIT_DOMAIN
        ),
        "model_only_failed_prefix_accounting_authority": (
            MODEL_ONLY_FAILED_PREFIX_ACCOUNTING_AUTHORITY_DOMAIN
        ),
        "dependent_postaudit_obligation": (
            DEPENDENT_POSTAUDIT_OBLIGATION_DOMAIN
        ),
        "dependent_frontier_derivation": (
            DEPENDENT_FRONTIER_DERIVATION_DOMAIN
        ),
        "dependent_transaction_benchmark_profile": (
            DEPENDENT_TRANSACTION_BENCHMARK_PROFILE_DOMAIN
        ),
        "ground_derived_transaction_two_feasibility_audit": (
            GROUND_DERIVED_TRANSACTION_TWO_FEASIBILITY_AUDIT_DOMAIN
        ),
        "recorded_work_transport": RECORDED_WORK_TRANSPORT_DOMAIN,
        "phase3e_bundle_manifest": PHASE3E_BUNDLE_MANIFEST_DOMAIN,
        "selected_route_bundle_manifest": (
            SELECTED_ROUTE_BUNDLE_MANIFEST_DOMAIN
        ),
    }
)

PHASE3E_DOMAIN_TAGS = frozenset(PHASE3E_DOMAIN_TAG_REGISTRY.values())

if len(PHASE3E_DOMAIN_TAGS) != len(PHASE3E_DOMAIN_TAG_REGISTRY):  # pragma: no cover
    raise RuntimeError("Phase 3E domain tags must be unique")


_CONTENT_ID_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
_RATIONAL_FIELDS = frozenset({"numerator", "denominator"})


def require_exact_fields(
    document: Mapping[str, Any],
    expected_fields: Collection[str],
    *,
    context: str = "document",
) -> None:
    """Reject missing, extra, or non-string fields in a schema object."""

    if not isinstance(document, Mapping):
        raise Phase3EIdentityError(f"{context} must be an object")
    if any(type(field) is not str for field in expected_fields):
        raise Phase3EIdentityError(f"{context} expected fields must be strings")
    if any(type(field) is not str for field in document):
        raise Phase3EIdentityError(f"{context} field names must be strings")
    expected = frozenset(expected_fields)
    actual = frozenset(document)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        raise Phase3EIdentityError(
            f"{context} field set mismatch: missing={missing}, "
            f"unexpected={unexpected}"
        )


def require_registered_domain_tag(domain_tag: str) -> str:
    """Return a registered tag, rejecting arbitrary or ill-typed domains."""

    if type(domain_tag) is not str:
        raise Phase3EIdentityError("domain tag must be a string")
    if domain_tag not in PHASE3E_DOMAIN_TAGS:
        raise Phase3EIdentityError(f"unregistered Phase 3E domain tag: {domain_tag!r}")
    return domain_tag


def _canonical_value(value: Any, *, location: str, active: set[int]) -> Any:
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise Phase3EIdentityError(f"non-finite float at {location}")
        return 0.0 if value == 0.0 else value
    if isinstance(value, Fraction):
        return {
            "denominator": value.denominator,
            "numerator": value.numerator,
        }

    if type(value) is list:
        identity = id(value)
        if identity in active:
            raise Phase3EIdentityError(f"cyclic value at {location}")
        active.add(identity)
        try:
            return [
                _canonical_value(item, location=f"{location}[{index}]", active=active)
                for index, item in enumerate(value)
            ]
        finally:
            active.remove(identity)

    if type(value) is dict:
        identity = id(value)
        if identity in active:
            raise Phase3EIdentityError(f"cyclic value at {location}")
        if any(type(key) is not str for key in value):
            raise Phase3EIdentityError(f"object keys must be strings at {location}")
        rational_keys = _RATIONAL_FIELDS.intersection(value)
        if rational_keys:
            if frozenset(value) != _RATIONAL_FIELDS:
                raise Phase3EIdentityError(
                    f"rational object has noncanonical fields at {location}"
                )
            numerator = value["numerator"]
            denominator = value["denominator"]
            if type(numerator) is not int or type(denominator) is not int:
                raise Phase3EIdentityError(
                    f"rational numerator and denominator must be integers at {location}"
                )
            if denominator <= 0:
                raise Phase3EIdentityError(
                    f"rational denominator must be positive at {location}"
                )
            if math.gcd(abs(numerator), denominator) != 1:
                raise Phase3EIdentityError(f"rational must be reduced at {location}")
        active.add(identity)
        try:
            return {
                key: _canonical_value(
                    value[key], location=f"{location}.{key}", active=active
                )
                for key in sorted(value)
            }
        finally:
            active.remove(identity)

    raise Phase3EIdentityError(
        f"unsupported canonical JSON type at {location}: "
        f"{type(value).__module__}.{type(value).__qualname__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a supported value to compact, sorted-key UTF-8 JSON bytes."""

    normalized = _canonical_value(value, location="$", active=set())
    try:
        text = json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return text.encode("utf-8", errors="strict")
    except (UnicodeEncodeError, ValueError) as error:
        raise Phase3EIdentityError(f"value is not canonical UTF-8 JSON: {error}") from error


def canonical_json(value: Any) -> str:
    """Return the canonical JSON text used by Phase 3E content IDs."""

    return canonical_json_bytes(value).decode("utf-8")


def _reject_json_constant(token: str) -> Any:
    raise Phase3EIdentityError(f"non-finite JSON number is forbidden: {token}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Phase3EIdentityError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _decode_rationals(value: Any, *, location: str) -> Any:
    if type(value) is list:
        return [
            _decode_rationals(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        rational_keys = _RATIONAL_FIELDS.intersection(value)
        if rational_keys:
            if frozenset(value) != _RATIONAL_FIELDS:
                raise Phase3EIdentityError(
                    f"rational object has noncanonical fields at {location}"
                )
            numerator = value["numerator"]
            denominator = value["denominator"]
            if type(numerator) is not int or type(denominator) is not int:
                raise Phase3EIdentityError(
                    f"rational numerator and denominator must be integers at {location}"
                )
            if denominator <= 0:
                raise Phase3EIdentityError(
                    f"rational denominator must be positive at {location}"
                )
            if math.gcd(abs(numerator), denominator) != 1:
                raise Phase3EIdentityError(f"rational must be reduced at {location}")
            return Fraction(numerator, denominator)
        return {
            key: _decode_rationals(item, location=f"{location}.{key}")
            for key, item in value.items()
        }
    if type(value) is float and not math.isfinite(value):
        raise Phase3EIdentityError(f"non-finite float at {location}")
    return value


def loads_canonical_json(data: str | bytes) -> Any:
    """Parse only the exact canonical byte representation.

    Rational-shaped objects are returned as :class:`fractions.Fraction`.
    Whitespace, unsorted keys, duplicate keys, alternate number spellings, and
    unreduced rational records are rejected rather than silently normalized.
    """

    if type(data) is bytes:
        raw = data
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise Phase3EIdentityError("canonical JSON must be valid UTF-8") from error
    elif type(data) is str:
        text = data
        try:
            raw = data.encode("utf-8", errors="strict")
        except UnicodeEncodeError as error:
            raise Phase3EIdentityError("canonical JSON must be valid UTF-8") from error
    else:
        raise Phase3EIdentityError("canonical JSON input must be str or bytes")

    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except Phase3EIdentityError:
        raise
    except (json.JSONDecodeError, ValueError, OverflowError) as error:
        raise Phase3EIdentityError(f"invalid canonical JSON: {error}") from error

    decoded = _decode_rationals(parsed, location="$")
    if canonical_json_bytes(decoded) != raw:
        raise Phase3EIdentityError("JSON bytes are valid but not canonical")
    return decoded


def content_id(domain_tag: str, value: Any) -> str:
    """Return ``SHA256(domain-tag || 0x00 || canonical-json)`` as 64 hex digits."""

    registered = require_registered_domain_tag(domain_tag)
    payload = registered.encode("utf-8") + b"\x00" + canonical_json_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def parse_content_id(value: str) -> str:
    """Validate and return a canonical full lowercase SHA-256 identifier."""

    if type(value) is not str or _CONTENT_ID_PATTERN.fullmatch(value) is None:
        raise Phase3EIdentityError(
            "content ID must be exactly 64 lowercase hexadecimal characters"
        )
    return value


def verify_content_id(domain_tag: str, value: Any, expected_id: str) -> bool:
    """Verify a canonical content ID without accepting truncated identifiers."""

    expected = parse_content_id(expected_id)
    return hmac.compare_digest(content_id(domain_tag, value), expected)
