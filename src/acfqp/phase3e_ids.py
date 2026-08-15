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


# Large exact mixture masses exceed CPython's default 4,300-digit conversion
# guard.  Keep the allowance local and finite rather than disabling that
# process-wide protection.  The registered V0-068 artifacts are comfortably
# below this ceiling.
MAX_CANONICAL_INTEGER_DECIMAL_DIGITS = 100_000


ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN = "acfqp:route-upper-bound-envelope:v1"
ROUTE_UPPER_FORMULA_DOMAIN = "acfqp:route-upper-formula:v1"
ROUTE_UPPER_DERIVATION_PROOF_DOMAIN = "acfqp:route-upper-derivation-proof:v1"
COMPARISON_PROFILE_DOMAIN = "acfqp:comparison-profile:v1"
COUNTER_REGISTRY_DOMAIN = "acfqp:counter-registry:v1"
CONSTRUCTION_COMPARISON_PROFILE_V2_DOMAIN = (
    "acfqp:comparison-profile:v2"
)
CONSTRUCTION_COUNTER_REGISTRY_V2_DOMAIN = "acfqp:counter-registry:v2"
CONSTRUCTION_COUNTER_RECORD_V2_DOMAIN = "acfqp:counter-record:v2"
CONSTRUCTION_WORK_VECTOR_V2_DOMAIN = "acfqp:work-vector:v2"
CONSTRUCTION_COMPARISON_VECTOR_V2_DOMAIN = (
    "acfqp:comparison-vector:v2"
)
CONSTRUCTION_STAGE_PROFILE_V2_DOMAIN = (
    "acfqp:construction-stage-profile:v2"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V2_DOMAIN = (
    "acfqp:actual-projection-profile:v2"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V2_DOMAIN = (
    "acfqp:actual-projection-proof:v2"
)
CONSTRUCTION_COUNTER_REGISTRY_V3_DOMAIN = "acfqp:counter-registry:v3"
CONSTRUCTION_STAGE_PROFILE_V3_DOMAIN = (
    "acfqp:construction-stage-profile:v3"
)
CONSTRUCTION_COMPARISON_PROFILE_V3_DOMAIN = (
    "acfqp:comparison-profile:v3"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V3_DOMAIN = (
    "acfqp:actual-projection-profile:v3"
)
CONSTRUCTION_LEGACY_MIGRATION_PROFILE_V3_DOMAIN = (
    "acfqp:construction-legacy-counter-migration-profile:v3"
)
CONSTRUCTION_ACCOUNTING_LIFECYCLE_V3_DOMAIN = (
    "acfqp:construction-accounting-lifecycle:v3"
)
CONSTRUCTION_STAGE_INSTANCE_V3_DOMAIN = (
    "acfqp:construction-stage-instance:v3"
)
CONSTRUCTION_STAGE_START_ATTESTATION_V3_DOMAIN = (
    "acfqp:construction-stage-start-attestation:v3"
)
CONSTRUCTION_OPERATION_EVENT_V3_DOMAIN = (
    "acfqp:construction-operation-event:v3"
)
CONSTRUCTION_STAGE_EVENT_TRANSCRIPT_V3_DOMAIN = (
    "acfqp:construction-stage-event-transcript:v3"
)
CONSTRUCTION_STAGE_COMPLETION_ATTESTATION_V3_DOMAIN = (
    "acfqp:construction-stage-completion-attestation:v3"
)
CONSTRUCTION_COUNTER_RECORD_V3_DOMAIN = "acfqp:counter-record:v3"
CONSTRUCTION_WORK_VECTOR_V3_DOMAIN = "acfqp:work-vector:v3"
CONSTRUCTION_COMPARISON_VECTOR_V3_DOMAIN = (
    "acfqp:comparison-vector:v3"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V3_DOMAIN = (
    "acfqp:actual-projection-proof:v3"
)
CONSTRUCTION_COUNTER_REGISTRY_V4_DOMAIN = "acfqp:counter-registry:v4"
CONSTRUCTION_STAGE_PROFILE_V4_DOMAIN = (
    "acfqp:construction-stage-profile:v4"
)
CONSTRUCTION_COMPARISON_PROFILE_V4_DOMAIN = (
    "acfqp:comparison-profile:v4"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V4_DOMAIN = (
    "acfqp:actual-projection-profile:v4"
)
CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN = "acfqp:counter-registry:v5"
CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN = (
    "acfqp:construction-stage-profile:v5"
)
CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN = (
    "acfqp:comparison-profile:v5"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V5_DOMAIN = (
    "acfqp:actual-projection-profile:v5"
)
CONSTRUCTION_COUNTER_REGISTRY_V6_DOMAIN = "acfqp:counter-registry:v6"
CONSTRUCTION_STAGE_PROFILE_V6_DOMAIN = (
    "acfqp:construction-stage-profile:v6"
)
CONSTRUCTION_COMPARISON_PROFILE_V6_DOMAIN = (
    "acfqp:comparison-profile:v6"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V6_DOMAIN = (
    "acfqp:actual-projection-profile:v6"
)
V075_CONSTRUCTION_ACCOUNTING_SCHEMA_CLOSURE_V2_DOMAIN = (
    "acfqp:v075-construction-accounting-schema-closure:v2"
)
V075_CONSTRUCTION_ACCOUNTING_SCHEMA_VERIFICATION_V2_DOMAIN = (
    "acfqp:v075-construction-accounting-schema-independent-verification:v2"
)
V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_V3_DOMAIN = (
    "acfqp:v075-construction-accounting-registry-successor:v3"
)
V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_VERIFICATION_V3_DOMAIN = (
    "acfqp:v075-construction-accounting-registry-successor-verification:v3"
)
V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_SUCCESSOR_V4_DOMAIN = (
    "acfqp:v075-construction-accounting-operation-ownership-successor:v4"
)
V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_VERIFICATION_V4_DOMAIN = (
    "acfqp:v075-construction-accounting-operation-ownership-verification:v4"
)
V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SUCCESSOR_V5_DOMAIN = (
    "acfqp:v075-construction-accounting-known-owner-gap-successor:v5"
)
V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_VERIFICATION_V5_DOMAIN = (
    "acfqp:v075-construction-accounting-known-owner-gap-verification:v5"
)
V075_K7_ROOT_CAP_OPERATION_SITE_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-operation-site:v1"
)
V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-operation-site-manifest:v1"
)
V075_K7_ROOT_CAP_OPERATION_SITE_AUDIT_V2_DOMAIN = (
    "acfqp:v075-k7-root-cap-operation-site-audit:v2"
)
V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V2_DOMAIN = (
    "acfqp:v075-k7-root-cap-operation-site-manifest:v2"
)
V075_K7_ROOT_CAP_OPERATION_BOUNDARY_V3_DOMAIN = (
    "acfqp:v075-k7-root-cap-operation-boundary:v3"
)
V075_K7_ROOT_CAP_OPERATION_BOUNDARY_MANIFEST_V3_DOMAIN = (
    "acfqp:v075-k7-root-cap-operation-boundary-manifest:v3"
)
V075_K7_ROOT_CAP_COLD_CACHE_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-cold-cache-profile:v1"
)
V075_K7_ROOT_CAP_COLD_CACHE_EPOCH_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-cold-cache-epoch:v1"
)
V075_K7_ROOT_CAP_OWNED_PARTIAL_RESULT_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-owned-partial-result:v1"
)
V075_K7_ROOT_CAP_EXECUTION_IDENTITY_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-execution-identity-profile:v1"
)
V075_CONSTRUCTION_ACCOUNTING_OPERATION_BOUNDARY_VERIFICATION_V6_DOMAIN = (
    "acfqp:v075-construction-accounting-operation-boundary-"
    "independent-verification:v6"
)
V075_K7_CAUSAL_PROMOTION_SHARED_MEASUREMENT_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-shared-measurement:v1"
)
V075_K7_CAUSAL_PROMOTION_RUNTIME_PREPARATION_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-runtime-preparation:v1"
)
V075_K7_CAUSAL_PROMOTION_SUPERVISED_REQUEST_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-supervised-request:v1"
)
V075_K7_CAUSAL_PROMOTION_OPERATIONAL_TRACE_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-operational-trace:v1"
)
V075_K7_REUSABLE_MODEL_OPERATIONAL_TRACE_V1_DOMAIN = (
    "acfqp:v075-k7-reusable-model-operational-trace:v1"
)
V075_K7_CAUSAL_RECOVERY_OPERATIONAL_TRACE_V1_DOMAIN = (
    "acfqp:v075-k7-causal-recovery-operational-trace:v1"
)
CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_V1_DOMAIN = (
    "acfqp:construction-k7-causal-recovery-chain:v1"
)
CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-causal-recovery-chain-replay:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_RECOVERY_OVERLAY_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-recovery-overlay:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_VALIDATION_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-validation-request:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_RECOVERY_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-recovery-request:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_NAMESPACE_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-namespace-binding:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_ROW_EXECUTION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-row-execution:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_GROUND_TRANSACTION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-ground-transaction:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_OVERLAY_REPLANNING_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-overlay-replanning:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_VALIDATION_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-transaction-2-validation-request:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_RECOVERY_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-transaction-2-recovery-request:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_NAMESPACE_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-transaction-2-namespace-binding:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_ROW_EXECUTION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-transaction-2-row-execution:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_GROUND_TRANSACTION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-transaction-2-ground-transaction:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_FINAL_LOCAL_REPLANNING_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-final-local-replanning:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-direct-fallback-row:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_INVENTORY_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-direct-fallback-inventory:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_POLICY_DECISION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-direct-fallback-policy-decision:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_WORK_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-direct-fallback-work:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-direct-fallback-result:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-direct-fallback-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTING_BOUNDARY_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-accounting-boundary:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTING_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-accounting-manifest:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_STAGE_RUNTIME_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-stage-runtime-result:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTED_CONTINUATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-accounted-continuation:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_RUNTIME_PREPARATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-runtime-preparation:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_SUPERVISED_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-supervised-request:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_OPERATIONAL_TRACE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-operational-trace:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_SHARED_MEASUREMENT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-shared-measurement:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_SHARED_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-shared-receipt:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_SHARED_RECEIPT_SET_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-shared-receipt-set:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PATH_AGGREGATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-path-aggregation:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_OCCURRENCE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-occurrence-accounting:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_OUTPUT_RENDERER_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-output-renderer:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_OUTPUT_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-output-commit:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-complete-bundle-verification-profile:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-complete-bundle-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-analysis-spec:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-occurrence-row:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_VECTOR_PREFIX_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-vector-prefix:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-analysis:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-analysis-verification-profile:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-analysis-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_INPUT_BLOB_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-input-blob:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTERED_OCCURRENCE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-preregistered-occurrence:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_WORKLOAD_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-workload-spec:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-preregistration:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-preregistration-verification-profile:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-preregistration-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-preregistered-campaign-commit-event:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_OCCURRENCE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-preregistered-campaign-occurrence:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-preregistered-campaign-result:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-preregistered-campaign-verification-profile:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-preregistered-campaign-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-denominator-closure:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-denominator-closure-verification-profile:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-denominator-closure-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-failure-closure:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-failure-closure-verification-profile:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-failure-closure-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_V2_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-prefix-failure-closure:v2"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_VERIFICATION_PROFILE_V2_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-prefix-failure-closure-verification-profile:v2"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_VERIFICATION_V2_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-prefix-failure-closure-verification:v2"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-orchestration-accounting-profile:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-orchestration-accounting-profile-verification-profile:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-campaign-orchestration-accounting-profile-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SNAPSHOT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-reusable-rapm-snapshot:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-reusable-rapm-query-spec:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-reusable-rapm-query-result:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-reusable-rapm-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-reusable-rapm-source-bundle-binding:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-reusable-rapm-source-bundle-binding-verification:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_NODE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-rapm-proof-dependency-node:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_PARTITION_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-rapm-proof-partition-result:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_SEARCH_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-rapm-proof-search-result:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_GRAPH_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-rapm-proof-dependency-graph:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_TRANSITION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-rapm-proof-dependency-transition:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PERSISTENT_PROOF_CACHE_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-persistent-proof-cache:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_QUERY_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-proof-cache-query:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_CONSUMPTION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-proof-cache-consumption:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_NO_REUSE_CONTROL_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-proof-cache-no-reuse-control:v1"
)
CONSTRUCTION_K7_QUERY_BOUND_PERSISTENT_PROOF_CACHE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-query-bound-persistent-proof-cache-verification:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_FIXTURE_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-checkpoint-fixture:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_QUERY_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-checkpoint-query:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_CONSUMPTION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-checkpoint-consumption:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_VALIDATION_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-validation-request:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RECOVERY_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-recovery-request:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NAMESPACE_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-namespace-binding:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ROW_ACQUISITION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-row-acquisition:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_GROUND_TRANSACTION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-ground-transaction:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-world-model-loop:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-world-model-loop-verification:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_EXACT_GROUND_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-exact-ground-row:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_FALLBACK_INVENTORY_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-fallback-inventory:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_FALLBACK_POLICY_DECISION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-fallback-policy-decision:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_FALLBACK_WORK_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-fallback-work:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_DIRECT_FALLBACK_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-direct-fallback-result:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_DIRECT_FALLBACK_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-direct-fallback-verification:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ACCOUNTING_BOUNDARY_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-accounting-boundary:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ACCOUNTING_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-accounting-manifest:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_STAGE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-stage-accounting:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NATIVE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-native-accounting:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RUNTIME_PREPARATION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-runtime-preparation:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SUPERVISED_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-supervised-request:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OPERATIONAL_TRACE_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-operational-trace:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_MEASUREMENT_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-shared-measurement:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-shared-receipt:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_SET_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-shared-receipt-set:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_PATH_AGGREGATION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-path-aggregation:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-occurrence-accounting:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_RENDERER_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-output-renderer:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-output-commit:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INPUT_BLOB_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-campaign-input-blob:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-campaign-occurrence-spec:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_WORKLOAD_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-campaign-workload:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-campaign-preregistration:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-campaign-commit-event:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-campaign-occurrence-row:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-campaign-closure:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-campaign-result:v1"
)
CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-eligible-campaign-independent-verification:v1"
)
CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_EPOCH_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-overlay-promoted-epoch:v1"
)
CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_QUERY_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-overlay-promoted-query:v1"
)
CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_CONSUMPTION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-overlay-promoted-consumption:v1"
)
CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-overlay-promotion-result:v1"
)
CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-recovery-overlay-promotion-independent-verification:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_EPOCH_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-overlay-epoch:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_QUERY_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-overlay-query:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_ABSTRACT_PLAN_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-abstract-plan:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_EXACT_LIFT_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-exact-lift-binding:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-overlay-result:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-overlay-independent-verification:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_STAGE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-stage-accounting:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_MEASUREMENT_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-shared-measurement:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-shared-receipt:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_RECEIPT_SET_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-shared-receipt-set:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_PATH_AGGREGATION_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-path-aggregation:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_OCCURRENCE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-occurrence-accounting:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_OUTPUT_RENDERER_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-output-renderer:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_OUTPUT_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-output-commit:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-campaign-preregistration:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-campaign-occurrence-row:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-campaign-closure:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-campaign-result:v1"
)
CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-positive-promoted-campaign-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_CHECKPOINT_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-checkpoint-preregistration:v1"
)
CONSTRUCTION_K7_HELDOUT_COORDINATE_CHECKPOINT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-coordinate-checkpoint:v1"
)
CONSTRUCTION_K7_HELDOUT_CAUSAL_ROW_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-causal-row-evidence:v1"
)
CONSTRUCTION_K7_HELDOUT_RECOVERY_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-recovery-request:v1"
)
CONSTRUCTION_K7_HELDOUT_VALIDATION_DELTA_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-validation-delta:v1"
)
CONSTRUCTION_K7_HELDOUT_OVERLAY_EPOCH_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-overlay-epoch:v1"
)
CONSTRUCTION_K7_HELDOUT_RECERTIFICATION_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-recertification-result:v1"
)
CONSTRUCTION_K7_HELDOUT_OVERLAY_QUERY_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-overlay-query:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-plan:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-reuse-result:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-reuse-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_STAGE_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-stage-profile:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_OPERATION_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-operation-manifest:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_OPERATION_BOUNDARY_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-operation-boundary:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_STAGE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-stage-accounting:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_MEASUREMENT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-shared-measurement:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-shared-receipt:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_RECEIPT_SET_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-shared-receipt-set:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_PATH_AGGREGATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-path-aggregation:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_OCCURRENCE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-occurrence-accounting:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_OUTPUT_RENDERER_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-output-renderer:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_OUTPUT_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-output-commit:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_OCCURRENCE_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-occurrence-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-campaign-preregistration:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-campaign-occurrence-row:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-campaign-closure:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-campaign-result:v1"
)
CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-abstract-campaign-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-multiquery-campaign-preregistration:v1"
)
CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-multiquery-campaign-occurrence-row:v1"
)
CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-multiquery-campaign-closure:v1"
)
CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-multiquery-campaign-result:v1"
)
CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-multiquery-campaign-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_CHECKPOINT_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-checkpoint-preregistration:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_COORDINATE_CHECKPOINT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-coordinate-checkpoint:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_CAUSAL_ROW_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-causal-row-evidence:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_RECOVERY_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-recovery-request:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_VALIDATION_DELTA_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-validation-delta:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_EPOCH_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-overlay-epoch:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-recertification-result:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-recertification-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_QUERY_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-overlay-query:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_PLAN_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-plan:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-reuse-result:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-reuse-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_STAGE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-stage-accounting:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_SHARED_MEASUREMENT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-shared-measurement:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_SHARED_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-shared-receipt:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_SHARED_RECEIPT_SET_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-shared-receipt-set:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_PATH_AGGREGATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-path-aggregation:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_OCCURRENCE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-occurrence-accounting:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_OUTPUT_RENDERER_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-output-renderer:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_OUTPUT_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-output-commit:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-campaign-preregistration:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-campaign-occurrence-row:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-campaign-closure:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-campaign-result:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_OCCURRENCE_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-occurrence-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-k6-abstract-campaign-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-cross-structural-campaign-preregistration:v1"
)
CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CHILD_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-cross-structural-campaign-child-row:v1"
)
CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-cross-structural-campaign-closure:v1"
)
CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-cross-structural-campaign-result:v1"
)
CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-cross-structural-campaign-independent-verification:v1"
)
CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_ENTRY_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-model-catalogue-entry:v1"
)
CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-model-catalogue:v1"
)
CONSTRUCTION_K7_HELDOUT_MODEL_SELECTION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-model-selection:v1"
)
CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-catalogue-query:v1"
)
CONSTRUCTION_K7_HELDOUT_CATALOGUE_CONSTRUCTION_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-catalogue-construction-request:v1"
)
CONSTRUCTION_K7_HELDOUT_CATALOGUE_ABSTRACT_PLAN_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-catalogue-abstract-plan:v1"
)
CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-catalogue-query-result:v1"
)
CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-catalogue-promotion-preregistration:v1"
)
CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_EVENT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-catalogue-promotion-event:v1"
)
CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-catalogue-promotion-closure:v1"
)
CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-catalogue-promotion-result:v1"
)
CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-heldout-catalogue-promotion-independent-verification:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_DISPATCH_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-synthesis-dispatch:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_PROMOTION_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-synthesis-promotion:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_UNSUPPORTED_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-synthesis-unsupported:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-synthesis-result:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-campaign-preregistration:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_OCCURRENCE_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-campaign-occurrence:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-campaign-closure:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-campaign-result:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-campaign-independent-verification:v1"
)
CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_SIGNATURE_V1_DOMAIN = (
    "acfqp:construction-k7-observed-constructor-signature:v1"
)
CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-observed-constructor-candidate:v1"
)
CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_DECISION_V1_DOMAIN = (
    "acfqp:construction-k7-observed-constructor-decision:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_V2_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-synthesis-v2-result:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_GRAMMAR_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-grammar:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_CORPUS_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-corpus:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-candidate:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_PROPOSAL_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-proposal:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_DECISION_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-decision:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_OBSERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-heldout-observation:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-heldout-preregistration:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_EVALUATION_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-heldout-evaluation:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_CAMPAIGN_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-heldout-campaign:v1"
)
CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-observed-program-heldout-independent-verification:v1"
)
CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_V3_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-observation-driven-synthesis-v3-result:v1"
)
CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-observation-derived-primitive-candidate:v1"
)
CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_BASIS_V1_DOMAIN = (
    "acfqp:construction-k7-observation-derived-primitive-basis:v1"
)
CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_EVALUATION_V1_DOMAIN = (
    "acfqp:construction-k7-observation-derived-primitive-evaluation:v1"
)
CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CAMPAIGN_V1_DOMAIN = (
    "acfqp:construction-k7-observation-derived-primitive-campaign:v1"
)
CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-observation-derived-primitive-independent-verification:v1"
)
CONSTRUCTION_K7_BASIS_HELDOUT_MODEL_TRANSPORT_V1_DOMAIN = (
    "acfqp:construction-k7-basis-heldout-model-transport:v1"
)
CONSTRUCTION_K7_BASIS_HELDOUT_QUERY_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-basis-heldout-query-preregistration:v1"
)
CONSTRUCTION_K7_BASIS_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN = (
    "acfqp:construction-k7-basis-heldout-abstract-plan:v1"
)
CONSTRUCTION_K7_BASIS_HELDOUT_SYNTHESIS_CAMPAIGN_V1_DOMAIN = (
    "acfqp:construction-k7-basis-heldout-synthesis-campaign:v1"
)
CONSTRUCTION_K7_BASIS_HELDOUT_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-basis-heldout-independent-verification:v1"
)
CONSTRUCTION_K7_STANDARD_2048_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-preregistration:v1"
)
CONSTRUCTION_K7_STANDARD_2048_QUOTIENT_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-quotient-row:v1"
)
CONSTRUCTION_K7_STANDARD_2048_WORLD_MODEL_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-world-model:v1"
)
CONSTRUCTION_K7_STANDARD_2048_MODEL_AUDIT_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-model-audit:v1"
)
CONSTRUCTION_K7_STANDARD_2048_ABSTRACT_PLAN_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-abstract-plan:v1"
)
CONSTRUCTION_K7_STANDARD_2048_MATCHED_DIRECT_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-matched-direct:v1"
)
CONSTRUCTION_K7_STANDARD_2048_RECEDING_CAMPAIGN_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-receding-campaign:v1"
)
CONSTRUCTION_K7_STANDARD_2048_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-independent-verification:v1"
)
CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-statistical-preregistration:v1"
)
CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-spawn-observation-archive:v1"
)
CONSTRUCTION_K7_STANDARD_2048_SPAWN_INTERVAL_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-spawn-interval:v1"
)
CONSTRUCTION_K7_STANDARD_2048_PARTIAL_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-partial-row:v1"
)
CONSTRUCTION_K7_STANDARD_2048_PARTIAL_MODEL_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-partial-model:v1"
)
CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_AUDIT_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-statistical-audit:v1"
)
CONSTRUCTION_K7_STANDARD_2048_ROBUST_PLAN_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-robust-plan:v1"
)
CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_MATCHED_DIRECT_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-statistical-matched-direct:v1"
)
CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_EPISODE_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-statistical-episode:v1"
)
CONSTRUCTION_K7_STANDARD_2048_MULTISEED_CAMPAIGN_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-multiseed-campaign:v1"
)
CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-standard-2048-statistical-independent-verification:v1"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_SOURCE_ARCHIVE_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-source-archive:v2"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_VALIDATION_ARCHIVE_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-validation-archive:v2"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PROPOSAL_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-proposal:v2"
)
CONSTRUCTION_K7_STANDARD_2048_PARTIAL_DYNAMICS_INTERVAL_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-partial-dynamics-interval:v2"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PREREGISTRATION_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-preregistration:v2"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_ROW_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-partial-row:v2"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_MODEL_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-partial-model:v2"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_AUDIT_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-audit:v2"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_ROBUST_PLAN_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-robust-plan:v2"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_MATCHED_DIRECT_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-matched-direct:v2"
)
CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_EPISODE_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-fresh-board-episode:v2"
)
CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_CAMPAIGN_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-fresh-board-campaign:v2"
)
CONSTRUCTION_K7_STANDARD_2048_SUPPORT_INDEPENDENT_VERIFICATION_V2_DOMAIN = (
    "acfqp:construction-k7-standard-2048-support-independent-verification:v2"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_PROFILE_V3_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-acquisition-profile:v3"
)
CONSTRUCTION_K7_STANDARD_2048_META_PRIOR_V3_DOMAIN = (
    "acfqp:construction-k7-standard-2048-identity-bound-meta-prior:v3"
)
CONSTRUCTION_K7_STANDARD_2048_ACQUISITION_ARM_V3_DOMAIN = (
    "acfqp:construction-k7-standard-2048-acquisition-arm:v3"
)
CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_CAMPAIGN_V3_DOMAIN = (
    "acfqp:construction-k7-standard-2048-sample-tax-campaign:v3"
)
CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_VERIFICATION_V3_DOMAIN = (
    "acfqp:construction-k7-standard-2048-sample-tax-independent-verification:v3"
)
CONSTRUCTION_K7_STANDARD_2048_AFFINE_META_PRIOR_V4_DOMAIN = (
    "acfqp:construction-k7-standard-2048-affine-meta-prior:v4"
)
CONSTRUCTION_K7_STANDARD_2048_AFFINE_CERTIFICATE_V4_DOMAIN = (
    "acfqp:construction-k7-standard-2048-affine-certificate:v4"
)
CONSTRUCTION_K7_STANDARD_2048_AFFINE_ROUTE_DECISION_V4_DOMAIN = (
    "acfqp:construction-k7-standard-2048-affine-route-decision:v4"
)
CONSTRUCTION_K7_STANDARD_2048_AFFINE_LONG_EPISODE_V4_DOMAIN = (
    "acfqp:construction-k7-standard-2048-affine-long-episode:v4"
)
CONSTRUCTION_K7_STANDARD_2048_AFFINE_CAMPAIGN_V4_DOMAIN = (
    "acfqp:construction-k7-standard-2048-affine-meta-prior-campaign:v4"
)
CONSTRUCTION_K7_STANDARD_2048_AFFINE_VERIFICATION_V4_DOMAIN = (
    "acfqp:construction-k7-standard-2048-affine-independent-verification:v4"
)
CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_PREREGISTRATION_V5_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exchangeability-preregistration:v5"
)
CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_CERTIFICATE_V5_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exchangeability-certificate:v5"
)
CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_ROUTE_DECISION_V5_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exchangeability-route-decision:v5"
)
CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_EPISODE_V5_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exchangeability-episode:v5"
)
CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_CAMPAIGN_V5_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exchangeability-campaign:v5"
)
CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_VERIFICATION_V5_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exchangeability-independent-verification:v5"
)
CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_PREREGISTRATION_V6_DOMAIN = (
    "acfqp:construction-k7-standard-2048-frontier-acquisition-preregistration:v6"
)
CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_CERTIFICATE_V6_DOMAIN = (
    "acfqp:construction-k7-standard-2048-frontier-acquisition-certificate:v6"
)
CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_ROUTE_DECISION_V6_DOMAIN = (
    "acfqp:construction-k7-standard-2048-frontier-acquisition-route-decision:v6"
)
CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_EPISODE_V6_DOMAIN = (
    "acfqp:construction-k7-standard-2048-frontier-acquisition-episode:v6"
)
CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_CAMPAIGN_V6_DOMAIN = (
    "acfqp:construction-k7-standard-2048-frontier-acquisition-campaign:v6"
)
CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_VERIFICATION_V6_DOMAIN = (
    "acfqp:construction-k7-standard-2048-frontier-acquisition-independent-verification:v6"
)
CONSTRUCTION_K7_STANDARD_2048_TARGETED_SOURCE_ARCHIVE_V7_DOMAIN = (
    "acfqp:construction-k7-standard-2048-targeted-source-archive:v7"
)
CONSTRUCTION_K7_STANDARD_2048_TARGETED_VALIDATION_ARCHIVE_V7_DOMAIN = (
    "acfqp:construction-k7-standard-2048-targeted-validation-archive:v7"
)
CONSTRUCTION_K7_STANDARD_2048_TARGETED_PREREGISTRATION_V7_DOMAIN = (
    "acfqp:construction-k7-standard-2048-targeted-preregistration:v7"
)
CONSTRUCTION_K7_STANDARD_2048_TARGETED_CERTIFICATE_V7_DOMAIN = (
    "acfqp:construction-k7-standard-2048-targeted-certificate:v7"
)
CONSTRUCTION_K7_STANDARD_2048_TARGETED_ROUTE_DECISION_V7_DOMAIN = (
    "acfqp:construction-k7-standard-2048-targeted-route-decision:v7"
)
CONSTRUCTION_K7_STANDARD_2048_TARGETED_EPISODE_V7_DOMAIN = (
    "acfqp:construction-k7-standard-2048-targeted-episode:v7"
)
CONSTRUCTION_K7_STANDARD_2048_TARGETED_CAMPAIGN_V7_DOMAIN = (
    "acfqp:construction-k7-standard-2048-targeted-campaign:v7"
)
CONSTRUCTION_K7_STANDARD_2048_TARGETED_VERIFICATION_V7_DOMAIN = (
    "acfqp:construction-k7-standard-2048-targeted-independent-verification:v7"
)
CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_PREREGISTRATION_V8_DOMAIN = (
    "acfqp:construction-k7-standard-2048-h3-reuse-preregistration:v8"
)
CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_INTERVAL_BINDING_V8_DOMAIN = (
    "acfqp:construction-k7-standard-2048-h3-targeted-interval-binding:v8"
)
CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_SUPPORT_PROPOSAL_V8_DOMAIN = (
    "acfqp:construction-k7-standard-2048-h3-targeted-support-proposal:v8"
)
CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_EPISODE_V8_DOMAIN = (
    "acfqp:construction-k7-standard-2048-h3-reuse-episode:v8"
)
CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_CAMPAIGN_V8_DOMAIN = (
    "acfqp:construction-k7-standard-2048-h3-reuse-campaign:v8"
)
CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_VERIFICATION_V8_DOMAIN = (
    "acfqp:construction-k7-standard-2048-h3-reuse-independent-verification:v8"
)
CONSTRUCTION_K7_STANDARD_2048_FACTORED_PREREGISTRATION_V9_DOMAIN = (
    "acfqp:construction-k7-standard-2048-factored-preregistration:v9"
)
CONSTRUCTION_K7_STANDARD_2048_FACTORED_OPERATOR_V9_DOMAIN = (
    "acfqp:construction-k7-standard-2048-factored-spawn-operator:v9"
)
CONSTRUCTION_K7_STANDARD_2048_FACTORED_EPISODE_V9_DOMAIN = (
    "acfqp:construction-k7-standard-2048-factored-episode:v9"
)
CONSTRUCTION_K7_STANDARD_2048_FACTORED_CAMPAIGN_V9_DOMAIN = (
    "acfqp:construction-k7-standard-2048-factored-campaign:v9"
)
CONSTRUCTION_K7_STANDARD_2048_FACTORED_VERIFICATION_V9_DOMAIN = (
    "acfqp:construction-k7-standard-2048-factored-independent-verification:v9"
)
CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_PREREGISTRATION_V10_DOMAIN = (
    "acfqp:construction-k7-standard-2048-meta-route-preregistration:v10"
)
CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_OPERATOR_V10_DOMAIN = (
    "acfqp:construction-k7-standard-2048-meta-route-operator:v10"
)
CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_CERTIFICATE_V10_DOMAIN = (
    "acfqp:construction-k7-standard-2048-meta-route-certificate:v10"
)
CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_EPISODE_V10_DOMAIN = (
    "acfqp:construction-k7-standard-2048-meta-route-episode:v10"
)
CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_CAMPAIGN_V10_DOMAIN = (
    "acfqp:construction-k7-standard-2048-meta-route-campaign:v10"
)
CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_VERIFICATION_V10_DOMAIN = (
    "acfqp:construction-k7-standard-2048-meta-route-independent-verification:v10"
)
CONSTRUCTION_K7_STANDARD_2048_LONG_PREREGISTRATION_V11_DOMAIN = (
    "acfqp:construction-k7-standard-2048-long-preregistration:v11"
)
CONSTRUCTION_K7_STANDARD_2048_LONG_DYNAMICS_IDENTITY_V11_DOMAIN = (
    "acfqp:construction-k7-standard-2048-long-dynamics-identity:v11"
)
CONSTRUCTION_K7_STANDARD_2048_LONG_OPERATOR_BINDING_V11_DOMAIN = (
    "acfqp:construction-k7-standard-2048-long-operator-binding:v11"
)
CONSTRUCTION_K7_STANDARD_2048_LONG_CERTIFICATE_V11_DOMAIN = (
    "acfqp:construction-k7-standard-2048-long-certificate:v11"
)
CONSTRUCTION_K7_STANDARD_2048_LONG_EPISODE_V11_DOMAIN = (
    "acfqp:construction-k7-standard-2048-long-episode:v11"
)
CONSTRUCTION_K7_STANDARD_2048_LONG_NO_TRANSFER_V11_DOMAIN = (
    "acfqp:construction-k7-standard-2048-long-no-transfer:v11"
)
CONSTRUCTION_K7_STANDARD_2048_LONG_CAMPAIGN_V11_DOMAIN = (
    "acfqp:construction-k7-standard-2048-long-campaign:v11"
)
CONSTRUCTION_K7_STANDARD_2048_LONG_VERIFICATION_V11_DOMAIN = (
    "acfqp:construction-k7-standard-2048-long-independent-verification:v11"
)
CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_PREREGISTRATION_V12_DOMAIN = (
    "acfqp:construction-k7-standard-2048-accounted-preregistration:v12"
)
CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_MEASUREMENT_V12_DOMAIN = (
    "acfqp:construction-k7-standard-2048-accounted-measurement:v12"
)
CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_COUNTER_BUNDLE_V12_DOMAIN = (
    "acfqp:construction-k7-standard-2048-accounted-counter-bundle:v12"
)
CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_DECISION_V12_DOMAIN = (
    "acfqp:construction-k7-standard-2048-accounted-decision:v12"
)
CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_EPISODE_V12_DOMAIN = (
    "acfqp:construction-k7-standard-2048-accounted-episode:v12"
)
CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_CAMPAIGN_V12_DOMAIN = (
    "acfqp:construction-k7-standard-2048-accounted-campaign:v12"
)
CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_VERIFICATION_V12_DOMAIN = (
    "acfqp:construction-k7-standard-2048-accounted-independent-verification:v12"
)
CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_OUTPUT_RENDERER_V12_DOMAIN = (
    "acfqp:construction-k7-standard-2048-accounted-output-renderer:v12"
)
CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_OUTPUT_COMMIT_V12_DOMAIN = (
    "acfqp:construction-k7-standard-2048-accounted-output-commit:v12"
)
CONSTRUCTION_K7_STANDARD_2048_COORDINATE_PREREGISTRATION_V13_DOMAIN = (
    "acfqp:construction-k7-standard-2048-coordinate-preregistration:v13"
)
CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CANDIDATE_V13_DOMAIN = (
    "acfqp:construction-k7-standard-2048-coordinate-candidate:v13"
)
CONSTRUCTION_K7_STANDARD_2048_COORDINATE_OBSERVATION_ARCHIVE_V13_DOMAIN = (
    "acfqp:construction-k7-standard-2048-coordinate-observation-archive:v13"
)
CONSTRUCTION_K7_STANDARD_2048_COORDINATE_BASIS_V13_DOMAIN = (
    "acfqp:construction-k7-standard-2048-coordinate-basis:v13"
)
CONSTRUCTION_K7_STANDARD_2048_PARTIAL_QUOTIENT_MODEL_V13_DOMAIN = (
    "acfqp:construction-k7-standard-2048-partial-quotient-model:v13"
)
CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CAMPAIGN_V13_DOMAIN = (
    "acfqp:construction-k7-standard-2048-coordinate-campaign:v13"
)
CONSTRUCTION_K7_STANDARD_2048_COORDINATE_DECISION_V13_DOMAIN = (
    "acfqp:construction-k7-standard-2048-coordinate-decision:v13"
)
CONSTRUCTION_K7_STANDARD_2048_COORDINATE_VERIFICATION_V13_DOMAIN = (
    "acfqp:construction-k7-standard-2048-coordinate-verification:v13"
)
CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PREREGISTRATION_V14_DOMAIN = (
    "acfqp:construction-k7-standard-2048-program-preregistration:v14"
)
CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CANDIDATE_V14_DOMAIN = (
    "acfqp:construction-k7-standard-2048-program-candidate:v14"
)
CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PROPOSAL_V14_DOMAIN = (
    "acfqp:construction-k7-standard-2048-program-proposal:v14"
)
CONSTRUCTION_K7_STANDARD_2048_PROGRAM_LINE_PROOF_V14_DOMAIN = (
    "acfqp:construction-k7-standard-2048-program-line-proof:v14"
)
CONSTRUCTION_K7_STANDARD_2048_FACTORED_WORLD_MODEL_V14_DOMAIN = (
    "acfqp:construction-k7-standard-2048-factored-world-model:v14"
)
CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CAMPAIGN_V14_DOMAIN = (
    "acfqp:construction-k7-standard-2048-program-campaign:v14"
)
CONSTRUCTION_K7_STANDARD_2048_PROGRAM_VERIFICATION_V14_DOMAIN = (
    "acfqp:construction-k7-standard-2048-program-verification:v14"
)
CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_PREREGISTRATION_V15_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exact-factor-preregistration:v15"
)
CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_SOURCE_CLOSURE_V15_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exact-factor-source-closure:v15"
)
CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CERTIFICATE_V15_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exact-factor-certificate:v15"
)
CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_EPISODE_V15_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exact-factor-episode:v15"
)
CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CAMPAIGN_V15_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exact-factor-campaign:v15"
)
CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_VERIFICATION_V15_DOMAIN = (
    "acfqp:construction-k7-standard-2048-exact-factor-verification:v15"
)
CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PREREGISTRATION_V16_DOMAIN = (
    "acfqp:construction-k7-standard-2048-spawn-program-preregistration:v16"
)
CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CANDIDATE_V16_DOMAIN = (
    "acfqp:construction-k7-standard-2048-spawn-program-candidate:v16"
)
CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V16_DOMAIN = (
    "acfqp:construction-k7-standard-2048-spawn-observation-archive:v16"
)
CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PROPOSAL_V16_DOMAIN = (
    "acfqp:construction-k7-standard-2048-spawn-program-proposal:v16"
)
CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_SUPPORT_PROOF_V16_DOMAIN = (
    "acfqp:construction-k7-standard-2048-spawn-program-support-proof:v16"
)
CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_WORLD_MODEL_V16_DOMAIN = (
    "acfqp:construction-k7-standard-2048-synthesized-world-model:v16"
)
CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CAMPAIGN_V16_DOMAIN = (
    "acfqp:construction-k7-standard-2048-spawn-program-campaign:v16"
)
CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_VERIFICATION_V16_DOMAIN = (
    "acfqp:construction-k7-standard-2048-spawn-program-verification:v16"
)
CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_PREREGISTRATION_V17_DOMAIN = (
    "acfqp:construction-k7-standard-2048-synthesized-plan-preregistration:v17"
)
CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CERTIFICATE_V17_DOMAIN = (
    "acfqp:construction-k7-standard-2048-synthesized-plan-certificate:v17"
)
CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_EPISODE_V17_DOMAIN = (
    "acfqp:construction-k7-standard-2048-synthesized-plan-episode:v17"
)
CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CAMPAIGN_V17_DOMAIN = (
    "acfqp:construction-k7-standard-2048-synthesized-plan-campaign:v17"
)
CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_VERIFICATION_V17_DOMAIN = (
    "acfqp:construction-k7-standard-2048-synthesized-plan-verification:v17"
)
CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_KERNEL_V18_DOMAIN = (
    "acfqp:construction-k7-standard-2048-local-repair-kernel:v18"
)
CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_PREREGISTRATION_V18_DOMAIN = (
    "acfqp:construction-k7-standard-2048-local-repair-preregistration:v18"
)
CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_FAILURE_V18_DOMAIN = (
    "acfqp:construction-k7-standard-2048-local-repair-failure:v18"
)
CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_ACQUISITION_V18_DOMAIN = (
    "acfqp:construction-k7-standard-2048-local-repair-acquisition:v18"
)
CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_OVERLAY_V18_DOMAIN = (
    "acfqp:construction-k7-standard-2048-local-repair-overlay:v18"
)
CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CERTIFICATE_V18_DOMAIN = (
    "acfqp:construction-k7-standard-2048-local-repair-certificate:v18"
)
CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_EPISODE_V18_DOMAIN = (
    "acfqp:construction-k7-standard-2048-local-repair-episode:v18"
)
CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CAMPAIGN_V18_DOMAIN = (
    "acfqp:construction-k7-standard-2048-local-repair-campaign:v18"
)
CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_VERIFICATION_V18_DOMAIN = (
    "acfqp:construction-k7-standard-2048-local-repair-verification:v18"
)
CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_PREREGISTRATION_V19_DOMAIN = (
    "acfqp:construction-k7-standard-2048-matched-repair-preregistration:v19"
)
CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_FAILURE_V19_DOMAIN = (
    "acfqp:construction-k7-standard-2048-matched-repair-failure:v19"
)
CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_ACQUISITION_V19_DOMAIN = (
    "acfqp:construction-k7-standard-2048-matched-repair-acquisition:v19"
)
CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_OVERLAY_V19_DOMAIN = (
    "acfqp:construction-k7-standard-2048-matched-repair-overlay:v19"
)
CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CERTIFICATE_V19_DOMAIN = (
    "acfqp:construction-k7-standard-2048-matched-repair-certificate:v19"
)
CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_EPISODE_V19_DOMAIN = (
    "acfqp:construction-k7-standard-2048-matched-repair-episode:v19"
)
CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CAMPAIGN_V19_DOMAIN = (
    "acfqp:construction-k7-standard-2048-matched-repair-campaign:v19"
)
CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_VERIFICATION_V19_DOMAIN = (
    "acfqp:construction-k7-standard-2048-matched-repair-verification:v19"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PREREGISTRATION_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-program-preregistration:v20"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_OBSERVATION_ARCHIVE_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-observation-archive:v20"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CANDIDATE_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-program-candidate:v20"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROPOSAL_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-program-proposal:v20"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROOF_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-program-proof:v20"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_WORLD_MODEL_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-world-model:v20"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PLAN_CERTIFICATE_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-plan-certificate:v20"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_EPISODE_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-program-episode:v20"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CAMPAIGN_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-program-campaign:v20"
)
CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_VERIFICATION_V20_DOMAIN = (
    "acfqp:construction-k7-standard-2048-context-program-verification:v20"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROGRAM_PREREGISTRATION_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-program-preregistration:v21"
)
CONSTRUCTION_K7_STANDARD_2048_STRUCTURAL_CONTEXT_POOL_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-structural-context-pool:v21"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CANDIDATE_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-candidate:v21"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACQUISITION_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-acquisition:v21"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROPOSAL_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-proposal:v21"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROOF_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-proof:v21"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_WORLD_MODEL_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-world-model:v21"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PLAN_CERTIFICATE_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-plan-certificate:v21"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_EPISODE_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-episode:v21"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CAMPAIGN_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-campaign:v21"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_VERIFICATION_V21_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-verification:v21"
)
CONSTRUCTION_K7_STANDARD_2048_COMMIT_REVEAL_TARGET_KERNEL_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-commit-reveal-target-kernel:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PREREGISTRATION_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-preregistration:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_STRUCTURAL_POOL_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-structural-pool:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CANDIDATE_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-candidate:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_ACQUISITION_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-acquisition:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROPOSAL_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-proposal:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROOF_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-proof:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_WORLD_MODEL_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-world-model:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CERTIFICATE_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-certificate:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_EPISODE_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-episode:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CAMPAIGN_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-campaign:v22"
)
CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_VERIFICATION_V22_DOMAIN = (
    "acfqp:construction-k7-standard-2048-blind-expression-verification:v22"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_PREREGISTRATION_V23_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-long-preregistration:v23"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_SOURCE_BINDING_V23_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-long-source-binding:v23"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CERTIFICATE_V23_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-long-certificate:v23"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_EPISODE_V23_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-long-episode:v23"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CAMPAIGN_V23_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-long-campaign:v23"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_VERIFICATION_V23_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-long-verification:v23"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_PREREGISTRATION_V24_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-accounted-preregistration:v24"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_MEASUREMENT_V24_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-accounted-measurement:v24"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_COUNTER_BUNDLE_V24_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-accounted-counter-bundle:v24"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_DECISION_V24_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-accounted-decision:v24"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_EPISODE_V24_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-accounted-episode:v24"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_CAMPAIGN_V24_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-accounted-campaign:v24"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_VERIFICATION_V24_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-accounted-verification:v24"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_SEMANTIC_VERIFICATION_V25_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-accounted-semantic-verification:v25"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V26_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-preregistration:v26"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V26_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-certificate:v26"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V26_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-episode:v26"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V26_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-campaign:v26"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V26_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-verification:v26"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V27_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-preregistration:v27"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V27_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-certificate:v27"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V27_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-episode:v27"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V27_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-campaign:v27"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V27_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-verification:v27"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V28_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-preregistration:v28"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V28_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-certificate:v28"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V28_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-episode:v28"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V28_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-campaign:v28"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V28_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-verification:v28"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V29_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-preregistration:v29"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V29_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-certificate:v29"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V29_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-episode:v29"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V29_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-campaign:v29"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V29_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-verification:v29"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V30_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-preregistration:v30"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V30_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-certificate:v30"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V30_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-episode:v30"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V30_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-campaign:v30"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V30_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-verification:v30"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V31_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-preregistration:v31"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V31_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-certificate:v31"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V31_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-episode:v31"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V31_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-campaign:v31"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V31_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-verification:v31"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V32_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-preregistration:v32"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V32_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-certificate:v32"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V32_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-episode:v32"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V32_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-campaign:v32"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V32_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-verification:v32"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V33_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-preregistration:v33"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V33_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-certificate:v33"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V33_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-episode:v33"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V33_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-campaign:v33"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V33_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-checkpoint-verification:v33"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_PREREGISTRATION_V34_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-full-accounting-preregistration:v34"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_MEASUREMENT_V34_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-full-accounting-measurement:v34"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_COUNTER_BUNDLE_V34_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-full-accounting-counter-bundle:v34"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_SEGMENT_V34_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-full-accounting-segment:v34"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_EPISODE_V34_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-full-accounting-episode:v34"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_CAMPAIGN_V34_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-full-accounting-campaign:v34"
)
CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_VERIFICATION_V34_DOMAIN = (
    "acfqp:construction-k7-standard-2048-expression-full-accounting-verification:v34"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_TARGET_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-target:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PREREGISTRATION_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-preregistration:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_FAILURE_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-failure:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_ACQUISITION_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-acquisition:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CANDIDATE_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-candidate:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_OVERLAY_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-overlay:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CERTIFICATE_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-certificate:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_GROUND_CONTROL_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-ground-control:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_EPISODE_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-episode:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_COUNTER_BUNDLE_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-counter-bundle:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CAMPAIGN_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-campaign:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-verification:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-proposal:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-expression-proof:v35"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V36_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-accounting-preregistration:v36"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_MEASUREMENT_V36_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-accounting-measurement:v36"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_COUNTER_BUNDLE_V36_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-accounting-counter-bundle:v36"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_CAMPAIGN_V36_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-accounting-campaign:v36"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_VERIFICATION_V36_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-accounting-verification:v36"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V37_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-preregistration:v37"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V37_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-certificate:v37"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V37_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-episode:v37"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V37_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-campaign:v37"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V37_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-verification:v37"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V38_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-preregistration:v38"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V38_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-certificate:v38"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V38_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-episode:v38"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V38_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-campaign:v38"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V38_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-verification:v38"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V39_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-preregistration:v39"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V39_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-certificate:v39"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V39_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-episode:v39"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V39_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-campaign:v39"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V39_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-verification:v39"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V40_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-preregistration:v40"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V40_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-certificate:v40"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V40_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-episode:v40"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V40_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-campaign:v40"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V40_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-verification:v40"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V41_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-preregistration:v41"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V41_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-certificate:v41"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V41_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-episode:v41"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V41_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-campaign:v41"
)
CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V41_DOMAIN = (
    "acfqp:construction-k7-standard-2048-adaptive-checkpoint-verification:v41"
)
CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_PREREGISTRATION_V42_DOMAIN = (
    "acfqp:construction-k7-lmb-reusable-world-model-preregistration:v42"
)
CONSTRUCTION_K7_LMB_REUSABLE_PRIMITIVE_PROPOSAL_V42_DOMAIN = (
    "acfqp:construction-k7-lmb-reusable-primitive-proposal:v42"
)
CONSTRUCTION_K7_LMB_LOCAL_GROUND_DISTINCTION_V42_DOMAIN = (
    "acfqp:construction-k7-lmb-local-ground-distinction:v42"
)
CONSTRUCTION_K7_LMB_RECEDING_EPISODE_V42_DOMAIN = (
    "acfqp:construction-k7-lmb-receding-episode:v42"
)
CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_CAMPAIGN_V42_DOMAIN = (
    "acfqp:construction-k7-lmb-reusable-world-model-campaign:v42"
)
CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_VERIFICATION_V42_DOMAIN = (
    "acfqp:construction-k7-lmb-reusable-world-model-verification:v42"
)
CONSTRUCTION_K7_LMB_WITNESS_BLIND_PREREGISTRATION_V43_DOMAIN = (
    "acfqp:construction-k7-lmb-witness-blind-preregistration:v43"
)
CONSTRUCTION_K7_LMB_WITNESS_BLIND_PROPOSAL_V43_DOMAIN = (
    "acfqp:construction-k7-lmb-witness-blind-proposal:v43"
)
CONSTRUCTION_K7_LMB_WITNESS_BLIND_DISTINCTION_V43_DOMAIN = (
    "acfqp:construction-k7-lmb-witness-blind-distinction:v43"
)
CONSTRUCTION_K7_LMB_CROSS_CARDINALITY_EPISODE_V43_DOMAIN = (
    "acfqp:construction-k7-lmb-cross-cardinality-episode:v43"
)
CONSTRUCTION_K7_LMB_WITNESS_BLIND_CAMPAIGN_V43_DOMAIN = (
    "acfqp:construction-k7-lmb-witness-blind-campaign:v43"
)
CONSTRUCTION_K7_LMB_WITNESS_BLIND_VERIFICATION_V43_DOMAIN = (
    "acfqp:construction-k7-lmb-witness-blind-verification:v43"
)
CONSTRUCTION_K7_LMB_DIFFERENCE_GRAMMAR_PREREGISTRATION_V44_DOMAIN = (
    "acfqp:construction-k7-lmb-difference-grammar-preregistration:v44"
)
CONSTRUCTION_K7_LMB_RAW_TRANSITION_OBSERVATION_V44_DOMAIN = (
    "acfqp:construction-k7-lmb-raw-transition-observation:v44"
)
CONSTRUCTION_K7_LMB_DERIVED_TRANSITION_PROGRAM_V44_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-transition-program:v44"
)
CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_DISTINCTION_V44_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-program-distinction:v44"
)
CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_EPISODE_V44_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-program-episode:v44"
)
CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_CAMPAIGN_V44_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-program-campaign:v44"
)
CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_VERIFICATION_V44_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-program-verification:v44"
)
CONSTRUCTION_K7_LMB_DIFFERENCE_GRAMMAR_SUCCESSOR_PREREGISTRATION_V44R1_DOMAIN = (
    "acfqp:construction-k7-lmb-difference-grammar-successor-preregistration:v44r1"
)
CONSTRUCTION_K7_LMB_MODEL_DERIVED_SOURCE_OBSERVATION_V44R1_DOMAIN = (
    "acfqp:construction-k7-lmb-model-derived-source-observation:v44r1"
)
CONSTRUCTION_K7_LMB_DERIVED_TRANSITION_PROGRAM_V44R1_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-transition-program:v44r1"
)
CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_DISTINCTION_V44R1_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-program-distinction:v44r1"
)
CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_EPISODE_V44R1_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-program-episode:v44r1"
)
CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_CAMPAIGN_V44R1_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-program-campaign:v44r1"
)
CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_VERIFICATION_V44R1_DOMAIN = (
    "acfqp:construction-k7-lmb-derived-program-verification:v44r1"
)
CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_PREREGISTRATION_V45_DOMAIN = (
    "acfqp:construction-k7-lmb-anonymous-descriptor-preregistration:v45"
)
CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_OBSERVATION_V45_DOMAIN = (
    "acfqp:construction-k7-lmb-anonymous-descriptor-observation:v45"
)
CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_PROGRAM_V45_DOMAIN = (
    "acfqp:construction-k7-lmb-anonymous-descriptor-program:v45"
)
CONSTRUCTION_K7_LMB_DEPENDENCY_DERIVED_DISTINCTION_V45_DOMAIN = (
    "acfqp:construction-k7-lmb-dependency-derived-distinction:v45"
)
CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_EPISODE_V45_DOMAIN = (
    "acfqp:construction-k7-lmb-anonymous-descriptor-episode:v45"
)
CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_CAMPAIGN_V45_DOMAIN = (
    "acfqp:construction-k7-lmb-anonymous-descriptor-campaign:v45"
)
CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_VERIFICATION_V45_DOMAIN = (
    "acfqp:construction-k7-lmb-anonymous-descriptor-verification:v45"
)
CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_PREREGISTRATION_V46_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-column-preregistration:v46"
)
CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_OBSERVATION_V46_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-column-observation:v46"
)
CONSTRUCTION_K7_LMB_COLUMN_FACTORIZATION_V46_DOMAIN = (
    "acfqp:construction-k7-lmb-column-factorization:v46"
)
CONSTRUCTION_K7_LMB_RELATION_PROGRAM_V46_DOMAIN = (
    "acfqp:construction-k7-lmb-relation-program:v46"
)
CONSTRUCTION_K7_LMB_FACTORIZED_DISTINCTION_V46_DOMAIN = (
    "acfqp:construction-k7-lmb-factorized-distinction:v46"
)
CONSTRUCTION_K7_LMB_FACTORIZED_EPISODE_V46_DOMAIN = (
    "acfqp:construction-k7-lmb-factorized-episode:v46"
)
CONSTRUCTION_K7_LMB_OPAQUE_SCHEMA_OOD_REJECTION_V46_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-schema-ood-rejection:v46"
)
CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_CAMPAIGN_V46_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-column-campaign:v46"
)
CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_VERIFICATION_V46_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-column-verification:v46"
)
CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_SUCCESSOR_PREREGISTRATION_V46R1_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-column-successor-preregistration:v46r1"
)
CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_OBSERVATION_V46R1_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-column-observation:v46r1"
)
CONSTRUCTION_K7_LMB_COLUMN_FACTORIZATION_V46R1_DOMAIN = (
    "acfqp:construction-k7-lmb-column-factorization:v46r1"
)
CONSTRUCTION_K7_LMB_RELATION_PROGRAM_V46R1_DOMAIN = (
    "acfqp:construction-k7-lmb-relation-program:v46r1"
)
CONSTRUCTION_K7_LMB_FACTORIZED_DISTINCTION_V46R1_DOMAIN = (
    "acfqp:construction-k7-lmb-factorized-distinction:v46r1"
)
CONSTRUCTION_K7_LMB_FACTORIZED_EPISODE_V46R1_DOMAIN = (
    "acfqp:construction-k7-lmb-factorized-episode:v46r1"
)
CONSTRUCTION_K7_LMB_OPAQUE_SCHEMA_OOD_REJECTION_V46R1_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-schema-ood-rejection:v46r1"
)
CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_CAMPAIGN_V46R1_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-column-campaign:v46r1"
)
CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_VERIFICATION_V46R1_DOMAIN = (
    "acfqp:construction-k7-lmb-opaque-column-verification:v46r1"
)
CONSTRUCTION_K7_GENERIC_BYTECODE_PREREGISTRATION_V47_DOMAIN = (
    "acfqp:construction-k7-generic-bytecode-preregistration:v47"
)
CONSTRUCTION_K7_GENERIC_RAW_OBSERVATION_V47_DOMAIN = (
    "acfqp:construction-k7-generic-raw-observation:v47"
)
CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47_DOMAIN = (
    "acfqp:construction-k7-generic-bytecode-program:v47"
)
CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47_DOMAIN = (
    "acfqp:construction-k7-generic-local-distinction:v47"
)
CONSTRUCTION_K7_GENERIC_RECEDING_EPISODE_V47_DOMAIN = (
    "acfqp:construction-k7-generic-receding-episode:v47"
)
CONSTRUCTION_K7_GENERIC_STOCHASTIC_PARTIAL_V47_DOMAIN = (
    "acfqp:construction-k7-generic-stochastic-partial:v47"
)
CONSTRUCTION_K7_GENERIC_SAMPLE_TAX_V47_DOMAIN = (
    "acfqp:construction-k7-generic-sample-tax:v47"
)
CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_CAMPAIGN_V47_DOMAIN = (
    "acfqp:construction-k7-generic-cross-domain-campaign:v47"
)
CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_VERIFICATION_V47_DOMAIN = (
    "acfqp:construction-k7-generic-cross-domain-verification:v47"
)
CONSTRUCTION_K7_GENERIC_BYTECODE_FAILURE_V47_DOMAIN = (
    "acfqp:construction-k7-generic-bytecode-failure:v47"
)
CONSTRUCTION_K7_GENERIC_BYTECODE_PREREGISTRATION_V47R1_DOMAIN = (
    "acfqp:construction-k7-generic-bytecode-preregistration:v47r1"
)
CONSTRUCTION_K7_GENERIC_RAW_OBSERVATION_V47R1_DOMAIN = (
    "acfqp:construction-k7-generic-raw-observation:v47r1"
)
CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47R1_DOMAIN = (
    "acfqp:construction-k7-generic-bytecode-program:v47r1"
)
CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47R1_DOMAIN = (
    "acfqp:construction-k7-generic-local-distinction:v47r1"
)
CONSTRUCTION_K7_GENERIC_RECEDING_EPISODE_V47R1_DOMAIN = (
    "acfqp:construction-k7-generic-receding-episode:v47r1"
)
CONSTRUCTION_K7_GENERIC_STOCHASTIC_PARTIAL_V47R1_DOMAIN = (
    "acfqp:construction-k7-generic-stochastic-partial:v47r1"
)
CONSTRUCTION_K7_GENERIC_SAMPLE_TAX_V47R1_DOMAIN = (
    "acfqp:construction-k7-generic-sample-tax:v47r1"
)
CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_CAMPAIGN_V47R1_DOMAIN = (
    "acfqp:construction-k7-generic-cross-domain-campaign:v47r1"
)
CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_VERIFICATION_V47R1_DOMAIN = (
    "acfqp:construction-k7-generic-cross-domain-verification:v47r1"
)
CONSTRUCTION_COUNTER_REGISTRY_V7_DOMAIN = (
    "acfqp:construction-counter-registry:v7"
)
CONSTRUCTION_STAGE_PROFILE_V7_DOMAIN = (
    "acfqp:construction-stage-profile:v7"
)
CONSTRUCTION_COMPARISON_PROFILE_V7_DOMAIN = (
    "acfqp:construction-comparison-profile:v7"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V7_DOMAIN = (
    "acfqp:construction-actual-projection-profile:v7"
)
CONSTRUCTION_COUNTER_REGISTRY_V8_DOMAIN = (
    "acfqp:construction-counter-registry:v8"
)
CONSTRUCTION_STAGE_PROFILE_V8_DOMAIN = (
    "acfqp:construction-stage-profile:v8"
)
CONSTRUCTION_COMPARISON_PROFILE_V8_DOMAIN = (
    "acfqp:construction-comparison-profile:v8"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V8_DOMAIN = (
    "acfqp:construction-actual-projection-profile:v8"
)
CONSTRUCTION_COUNTER_REGISTRY_V9_DOMAIN = (
    "acfqp:construction-counter-registry:v9"
)
CONSTRUCTION_STAGE_PROFILE_V9_DOMAIN = (
    "acfqp:construction-stage-profile:v9"
)
CONSTRUCTION_COMPARISON_PROFILE_V9_DOMAIN = (
    "acfqp:construction-comparison-profile:v9"
)
CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V9_DOMAIN = (
    "acfqp:construction-actual-projection-profile:v9"
)
CONSTRUCTION_K7_ADAPTIVE_OPERATION_BOUNDARY_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-operation-boundary:v1"
)
CONSTRUCTION_K7_ADAPTIVE_OPERATION_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-operation-manifest:v1"
)
CONSTRUCTION_K7_ADAPTIVE_OPERATION_EVENT_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-operation-event:v1"
)
CONSTRUCTION_K7_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-accounting-preregistration:v1"
)
CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_NATIVE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-occurrence-native-accounting:v1"
)
CONSTRUCTION_K7_ADAPTIVE_COMPONENT_NATIVE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-component-native-accounting:v1"
)
CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_NATIVE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-campaign-native-accounting:v1"
)
CONSTRUCTION_K7_ADAPTIVE_ROUTE_INPUT_ENVELOPE_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-route-input-envelope:v1"
)
CONSTRUCTION_K7_ADAPTIVE_SHARED_MEASUREMENT_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-shared-measurement:v1"
)
CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-shared-receipt:v1"
)
CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_SET_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-shared-receipt-set:v1"
)
CONSTRUCTION_K7_ADAPTIVE_PATH_AGGREGATION_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-path-aggregation:v1"
)
CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-occurrence-accounting:v1"
)
CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_ACCOUNTING_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-campaign-accounting:v1"
)
CONSTRUCTION_K7_ADAPTIVE_OUTPUT_RENDERER_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-output-renderer:v1"
)
CONSTRUCTION_K7_ADAPTIVE_OUTPUT_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-output-commit:v1"
)
CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-occurrence-independent-verification:v1"
)
CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-adaptive-campaign-independent-verification:v1"
)
CONSTRUCTION_K7_REUSABLE_BUILD_EPOCH_RESOLUTION_V1_DOMAIN = (
    "acfqp:construction-k7-reusable-build-epoch-resolution:v1"
)
CONSTRUCTION_K7_REUSABLE_BUILD_EPOCH_ENVELOPE_V1_DOMAIN = (
    "acfqp:construction-k7-reusable-build-epoch-envelope:v1"
)
CONSTRUCTION_K7_REUSABLE_ABSTRACT_QUERY_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-reusable-abstract-query-spec:v1"
)
CONSTRUCTION_K7_REUSABLE_ABSTRACT_QUERY_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-reusable-abstract-query-result:v1"
)
V075_K7_CAUSAL_PROMOTION_OUTPUT_COMMIT_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-output-commit:v1"
)
V075_K7_CAUSAL_PROMOTION_PATH_AGGREGATION_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-path-aggregation:v1"
)
V075_K7_CAUSAL_PROMOTION_OCCURRENCE_ACCOUNTING_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-occurrence-accounting:v1"
)
V075_K7_CAUSAL_PROMOTION_OUTPUT_RENDERER_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-output-renderer:v1"
)
V075_K7_CAUSAL_PROMOTION_BUDGET_REPLAY_ATTESTATION_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-budget-replay-attestation:v1"
)
V075_K7_CAUSAL_PROMOTION_ROUTE_CONTEXT_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-route-context:v1"
)
V075_K7_CAUSAL_PROMOTION_ROUTE_ATTEMPT_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-route-attempt:v1"
)
V075_K7_CAUSAL_PROMOTION_TERMINAL_DERIVATION_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-terminal-derivation:v1"
)
V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-complete-bundle-verification-profile:v1"
)
V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-complete-bundle-semantic-verifier:v1"
)
V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN = (
    "acfqp:v075-k7-causal-promotion-complete-bundle-verification:v1"
)
CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_START_V1_DOMAIN = (
    "acfqp:construction-partial-native-occurrence-start:v1"
)
CONSTRUCTION_PARTIAL_NATIVE_STAGE_START_V1_DOMAIN = (
    "acfqp:construction-partial-native-stage-start:v1"
)
CONSTRUCTION_PARTIAL_NATIVE_OPERATION_EVENT_V1_DOMAIN = (
    "acfqp:construction-partial-native-operation-event:v1"
)
CONSTRUCTION_PARTIAL_NATIVE_STAGE_COMPLETION_V1_DOMAIN = (
    "acfqp:construction-partial-native-stage-completion:v1"
)
CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_COMPLETION_V1_DOMAIN = (
    "acfqp:construction-partial-native-occurrence-completion:v1"
)
CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_ABORT_V1_DOMAIN = (
    "acfqp:construction-partial-native-occurrence-abort:v1"
)
CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_TRANSCRIPT_V1_DOMAIN = (
    "acfqp:construction-partial-native-occurrence-transcript:v1"
)
CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN = (
    "acfqp:construction-accounting-evidence-closure-context:v1"
)
CONSTRUCTION_ACCOUNTING_REQUIRED_PATH_RESOLUTION_V1_DOMAIN = (
    "acfqp:construction-accounting-required-path-resolution:v1"
)
CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-accounting-evidence-closure:v1"
)
CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-accounting-evidence-closure-verification:v1"
)
CONSTRUCTION_SHARED_RESOURCE_IDENTITY_BINDING_V1_DOMAIN = (
    "acfqp:construction-shared-resource-identity-binding:v1"
)
CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_WINDOW_V1_DOMAIN = (
    "acfqp:construction-shared-resource-measurement-window:v1"
)
CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_METHOD_V1_DOMAIN = (
    "acfqp:construction-shared-resource-measurement-method:v1"
)
CONSTRUCTION_SHARED_RESOURCE_MONITOR_REGISTRATION_V1_DOMAIN = (
    "acfqp:construction-shared-resource-monitor-registration:v1"
)
CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_REGISTRY_V1_DOMAIN = (
    "acfqp:construction-shared-resource-measurement-registry:v1"
)
CONSTRUCTION_SHARED_RESOURCE_SOURCE_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-shared-resource-source-evidence:v1"
)
CONSTRUCTION_SHARED_RESOURCE_CHARGE_KEY_V1_DOMAIN = (
    "acfqp:construction-shared-resource-charge-key:v1"
)
CONSTRUCTION_SHARED_RESOURCE_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-shared-resource-receipt:v1"
)
CONSTRUCTION_SHARED_RESOURCE_RECEIPT_SET_V1_DOMAIN = (
    "acfqp:construction-shared-resource-receipt-set:v1"
)
CONSTRUCTION_HASH_PURPOSE_REGISTRATION_V1_DOMAIN = (
    "acfqp:construction-hash-purpose-registration:v1"
)
CONSTRUCTION_RECURSION_SAFE_HASH_METER_PROFILE_V1_DOMAIN = (
    "acfqp:construction-recursion-safe-hash-meter-profile:v1"
)
CONSTRUCTION_NAMED_OBLIGATION_V1_DOMAIN = (
    "acfqp:construction-named-obligation:v1"
)
CONSTRUCTION_NAMED_OBLIGATION_REGISTRY_V1_DOMAIN = (
    "acfqp:construction-named-obligation-registry:v1"
)
CONSTRUCTION_ACCOUNTING_REQUIRED_PATH_PARTITION_V1_DOMAIN = (
    "acfqp:construction-accounting-required-path-partition:v1"
)
CONSTRUCTION_ACCOUNTING_COMPLETION_READINESS_BLOCKER_V1_DOMAIN = (
    "acfqp:construction-accounting-completion-readiness-blocker:v1"
)
CONSTRUCTION_ACCOUNTING_COMPLETION_READINESS_V1_DOMAIN = (
    "acfqp:construction-accounting-completion-readiness:v1"
)
CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_V1_DOMAIN = (
    "acfqp:construction-profile-native-zero-rule:v1"
)
CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_REGISTRY_V1_DOMAIN = (
    "acfqp:construction-profile-native-zero-rule-registry:v1"
)
CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_ROW_V1_DOMAIN = (
    "acfqp:construction-profile-native-zero-rule-readiness-row:v1"
)
CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_V1_DOMAIN = (
    "acfqp:construction-profile-native-zero-rule-readiness:v1"
)
CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_SITE_V1_DOMAIN = (
    "acfqp:construction-owner-boundary-coverage-site:v1"
)
CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_PROFILE_V1_DOMAIN = (
    "acfqp:construction-owner-boundary-coverage-profile:v1"
)
CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_V1_DOMAIN = (
    "acfqp:construction-occurrence-identity-join:v1"
)
CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-occurrence-identity-join-verification:v1"
)
CONSTRUCTION_OPERATIONAL_SEQUENCE_MARKER_V1_DOMAIN = (
    "acfqp:construction-operational-sequence-marker:v1"
)
CONSTRUCTION_OPERATIONAL_CUTOFF_ATTESTATION_V1_DOMAIN = (
    "acfqp:construction-operational-cutoff-attestation:v1"
)
CONSTRUCTION_OPERATIONAL_CUTOFF_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-operational-cutoff-verification:v1"
)
CONSTRUCTION_IDENTITY_JOIN_READINESS_V1_DOMAIN = (
    "acfqp:construction-identity-join-readiness:v1"
)
CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_BLOCKER_V1_DOMAIN = (
    "acfqp:construction-accounting-completion-prerequisite-blocker:v1"
)
CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-accounting-completion-prerequisite-manifest:v1"
)
CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_REPLAY_V1_DOMAIN = (
    "acfqp:construction-accounting-completion-prerequisite-replay:v1"
)
CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_EVENT_V1_DOMAIN = (
    "acfqp:construction-shared-resource-live-measurement-event:v1"
)
CONSTRUCTION_SHARED_RESOURCE_LIVE_COMPLETE_WINDOW_ZERO_CLAIM_V1_DOMAIN = (
    "acfqp:construction-shared-resource-live-complete-window-zero-claim:v1"
)
CONSTRUCTION_SHARED_RESOURCE_LIVE_TYPED_UNAVAILABLE_RESOLUTION_V1_DOMAIN = (
    "acfqp:construction-shared-resource-live-typed-unavailable-resolution:v1"
)
CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_ROW_V1_DOMAIN = (
    "acfqp:construction-shared-resource-live-measurement-row:v1"
)
CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_SNAPSHOT_V1_DOMAIN = (
    "acfqp:construction-shared-resource-live-measurement-snapshot:v1"
)
V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROGRAM_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-accounted-sealed-program:v1"
)
V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-accounted-sealed-profile:v1"
)
V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ROUTE_IDENTITY_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-accounted-sealed-route-identity:v1"
)
V075_K7_ROOT_CAP_ACCOUNTED_SEALED_REQUEST_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-accounted-sealed-request:v1"
)
V075_K7_ROOT_CAP_ACCOUNTED_SEALED_BUSINESS_FRAME_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-accounted-sealed-business-frame:v1"
)
V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ACCOUNTING_SUFFIX_FRAME_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-accounted-sealed-accounting-suffix-frame:v1"
)
V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROTOCOL_REPLAY_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-accounted-sealed-protocol-replay:v1"
)
V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_DERIVATION_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-shared-resource-identity-derivation:v1"
)
V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_VERIFICATION_V1_DOMAIN = (
    "acfqp:v075-k7-root-cap-shared-resource-identity-verification:v1"
)
V075_K7_SHARED_RESOURCE_SUPERVISED_SOURCE_ROLE_V1_DOMAIN = (
    "acfqp:v075-k7-shared-resource-supervised-source-role:v1"
)
V075_K7_SHARED_RESOURCE_REBASED_JOURNAL_EVENT_V1_DOMAIN = (
    "acfqp:v075-k7-shared-resource-rebased-journal-event:v1"
)
V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_BRIDGE_V1_DOMAIN = (
    "acfqp:v075-k7-shared-resource-supervised-finalization-bridge:v1"
)
V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_VERIFICATION_V1_DOMAIN = (
    "acfqp:v075-k7-shared-resource-supervised-finalization-verification:v1"
)
CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_ITERATION_V1_DOMAIN = (
    "acfqp:construction-output-bytes-fixed-point-iteration:v1"
)
CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_PROFILE_V1_DOMAIN = (
    "acfqp:construction-output-bytes-fixed-point-profile:v1"
)
CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_RESULT_V1_DOMAIN = (
    "acfqp:construction-output-bytes-fixed-point-result:v1"
)
CONSTRUCTION_OUTPUT_BYTES_RENDERED_ARTIFACT_SET_V1_DOMAIN = (
    "acfqp:construction-output-bytes-rendered-artifact-set:v1"
)
CONSTRUCTION_OUTPUT_BYTES_RENDERED_ARTIFACT_V1_DOMAIN = (
    "acfqp:construction-output-bytes-rendered-artifact:v1"
)
CONSTRUCTION_SHARED_RESOURCE_OUTER_SOURCE_SET_V1_DOMAIN = (
    "acfqp:construction-shared-resource-outer-source-set:v1"
)
CONSTRUCTION_SHARED_RESOURCE_OUTER_RAW_SOURCE_ROW_V1_DOMAIN = (
    "acfqp:construction-shared-resource-outer-raw-source-row:v1"
)
CONSTRUCTION_SHARED_RESOURCE_OUTER_FINALIZATION_V1_DOMAIN = (
    "acfqp:construction-shared-resource-outer-finalization:v1"
)
CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_SCOPE_V1_DOMAIN = (
    "acfqp:construction-shared-resource-global-supervisor-scope:v1"
)
CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_SOURCE_DOCUMENT_V1_DOMAIN = (
    "acfqp:construction-shared-resource-global-supervisor-source-document:v1"
)
CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_EVENT_V1_DOMAIN = (
    "acfqp:construction-shared-resource-global-supervisor-event:v1"
)
CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_EVENT_JOURNAL_V1_DOMAIN = (
    "acfqp:construction-shared-resource-global-supervisor-event-journal:v1"
)
V075_K7_OS_SUPERVISOR_READ_EVIDENCE_V1_DOMAIN = (
    "acfqp:v075-k7-os-supervisor-read-evidence:v1"
)
V075_K7_OS_SUPERVISOR_ADMISSION_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-os-supervisor-admission-profile:v1"
)
V075_K7_OS_SUPERVISOR_ADMISSION_PROBE_V1_DOMAIN = (
    "acfqp:v075-k7-os-supervisor-admission-probe:v1"
)
V075_K7_OS_SUPERVISOR_ADMISSION_RESULT_V1_DOMAIN = (
    "acfqp:v075-k7-os-supervisor-admission-result:v1"
)
V075_K7_PARENT_OWNED_SUCCESSOR_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-parent-owned-successor-profile:v1"
)
V075_K7_SCIENTIFIC_PHASE3E_OCCURRENCE_MAPPING_V1_DOMAIN = (
    "acfqp:v075-k7-scientific-phase3e-occurrence-mapping:v1"
)
V075_K7_PARENT_OWNED_SUCCESSOR_REQUEST_V1_DOMAIN = (
    "acfqp:v075-k7-parent-owned-successor-request:v1"
)
V075_K7_PARENT_OWNED_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN = (
    "acfqp:v075-k7-parent-owned-prelaunch-blocked-result:v1"
)
V075_K7_CGROUP_LEASE_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-cgroup-lease-profile:v1"
)
V075_K7_CGROUP_LEASE_AUTHORITY_V1_DOMAIN = (
    "acfqp:v075-k7-cgroup-lease-authority:v1"
)
V075_K7_CGROUP_LEASE_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN = (
    "acfqp:v075-k7-cgroup-lease-prelaunch-blocked-result:v1"
)
V075_K7_SUCCESSOR_PORTABLE_PROFILE_CLOSURE_V1_DOMAIN = (
    "acfqp:v075-k7-successor-portable-profile-closure:v1"
)
V075_K7_SUCCESSOR_PORTABLE_REQUEST_REPLAY_V1_DOMAIN = (
    "acfqp:v075-k7-successor-portable-request-replay:v1"
)
V075_K7_CHILD_BUSINESS_BUNDLE_V1_DOMAIN = (
    "acfqp:v075-k7-child-business-bundle:v1"
)
V075_K7_ATOMIC_CHILD_BUSINESS_FRAME_V1_DOMAIN = (
    "acfqp:v075-k7-atomic-child-business-frame:v1"
)
V075_K7_ATOMIC_PARENT_EXECUTION_SPEC_V1_DOMAIN = (
    "acfqp:v075-k7-atomic-parent-execution-spec:v1"
)
V075_K7_ATOMIC_PARENT_ACCOUNTING_SUFFIX_V1_DOMAIN = (
    "acfqp:v075-k7-atomic-parent-accounting-suffix:v1"
)
V075_K7_ATOMIC_PARENT_EXECUTION_RESULT_V1_DOMAIN = (
    "acfqp:v075-k7-atomic-parent-execution-result:v1"
)
V075_K7_ATOMIC_PARENT_EXECUTION_FAILURE_V1_DOMAIN = (
    "acfqp:v075-k7-atomic-parent-execution-failure:v1"
)
V075_K7_ATOMIC_SUPERVISOR_RESOURCE_EVIDENCE_V1_DOMAIN = (
    "acfqp:v075-k7-atomic-supervisor-resource-evidence:v1"
)
V075_K7_ATOMIC_SHARED_RESOURCE_REGISTRY_V1_DOMAIN = (
    "acfqp:v075-k7-atomic-shared-resource-registry:v1"
)
V075_K7_ATOMIC_SHARED_RESOURCE_RESOLUTION_V1_DOMAIN = (
    "acfqp:v075-k7-atomic-shared-resource-resolution:v1"
)
V075_K7_ATOMIC_SHARED_RESOURCE_VERIFICATION_V1_DOMAIN = (
    "acfqp:v075-k7-atomic-shared-resource-verification:v1"
)
V075_K7_ATTEMPT_PROCESS_SUPERVISOR_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-attempt-process-supervisor-profile:v1"
)
V075_K7_ATTEMPT_PROCESS_SESSION_START_V1_DOMAIN = (
    "acfqp:v075-k7-attempt-process-session-start:v1"
)
V075_K7_ATTEMPT_PROCESS_LAUNCH_EVENT_V1_DOMAIN = (
    "acfqp:v075-k7-attempt-process-launch-event:v1"
)
V075_K7_ATTEMPT_PROCESS_RAW_JOURNAL_V1_DOMAIN = (
    "acfqp:v075-k7-attempt-process-raw-journal:v1"
)
V075_K7_ATTEMPT_PROCESS_EXECUTION_V1_DOMAIN = (
    "acfqp:v075-k7-attempt-process-execution:v1"
)
V075_K7_ATTEMPT_PROCESS_ENVELOPE_V1_DOMAIN = (
    "acfqp:v075-k7-attempt-process-envelope:v1"
)
V075_K7_ATTEMPT_PROCESS_VERIFICATION_V1_DOMAIN = (
    "acfqp:v075-k7-attempt-process-verification:v1"
)
V075_K7_OUTER_ATTEMPT_CGROUP_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-cgroup-profile:v1"
)
V075_K7_OUTER_ATTEMPT_CGROUP_LEASE_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-cgroup-lease:v1"
)
V075_K7_OUTER_ATTEMPT_CGROUP_BLOCKED_RESULT_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-cgroup-blocked-result:v1"
)
V075_K7_OUTER_ATTEMPT_MEMORY_EVIDENCE_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-memory-evidence:v1"
)
V075_K7_OUTER_ATTEMPT_BROKER_IPC_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-broker-ipc-profile:v1"
)
V075_K7_OUTER_ATTEMPT_BROKER_IPC_FRAME_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-broker-ipc-frame:v1"
)
V075_K7_OUTER_ATTEMPT_BROKER_IPC_TRANSCRIPT_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-broker-ipc-transcript:v1"
)
V075_K7_OUTER_ATTEMPT_BROKER_PREPARATION_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-broker-preparation-profile:v1"
)
V075_K7_OUTER_ATTEMPT_BROKER_EXECUTION_SPEC_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-broker-execution-spec:v1"
)
V075_K7_OUTER_ATTEMPT_PREPARED_BROKER_SESSION_V1_DOMAIN = (
    "acfqp:v075-k7-outer-attempt-prepared-broker-session:v1"
)
V075_K7_TWO_ROLE_BROKER_PROBE_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-two-role-broker-probe-profile:v1"
)
V075_K7_TWO_ROLE_BROKER_PROBE_RESULT_V1_DOMAIN = (
    "acfqp:v075-k7-two-role-broker-probe-result:v1"
)
V075_K7_TWO_ROLE_BROKER_FAILURE_PREFIX_V1_DOMAIN = (
    "acfqp:v075-k7-two-role-broker-failure-prefix:v1"
)
V075_K7_BUSINESS_ENTRY_CORE_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-business-entry-core-profile:v1"
)
V075_K7_BUSINESS_ENTRY_CORE_EMISSION_V1_DOMAIN = (
    "acfqp:v075-k7-business-entry-core-emission:v1"
)
V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-production-role-manifest-profile:v1"
)
V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN = (
    "acfqp:v075-k7-production-role-spec:v1"
)
V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN = (
    "acfqp:v075-k7-production-role-manifest:v1"
)
V075_K7_BROKER_WORKER_ENTRY_CORE_PROFILE_V1_DOMAIN = (
    "acfqp:v075-k7-broker-worker-entry-core-profile:v1"
)
V075_K7_BROKER_OPERATIONAL_OUTPUT_V1_DOMAIN = (
    "acfqp:v075-k7-broker-operational-output:v1"
)
V075_K7_BROKER_OUTPUT_COMMIT_RECEIPT_V1_DOMAIN = (
    "acfqp:v075-k7-broker-output-commit-receipt:v1"
)
V075_K7_BROKER_WORKER_COMPLETION_V1_DOMAIN = (
    "acfqp:v075-k7-broker-worker-completion:v1"
)
V075_K7_PRODUCTION_ROLE_BOOTSTRAP_PROFILE_V2_DOMAIN = (
    "acfqp:v075-k7-production-role-bootstrap-profile:v2"
)
V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V2_DOMAIN = (
    "acfqp:v075-k7-production-role-manifest-profile:v2"
)
V075_K7_PRODUCTION_ROLE_SPEC_V2_DOMAIN = (
    "acfqp:v075-k7-production-role-spec:v2"
)
V075_K7_PRODUCTION_ROLE_MANIFEST_V2_DOMAIN = (
    "acfqp:v075-k7-production-role-manifest:v2"
)
V075_K7_PRODUCTION_ROLE_LAUNCH_CONTEXT_V2_DOMAIN = (
    "acfqp:v075-k7-production-role-launch-context:v2"
)
V075_K7_BROKER_RESOURCE_SESSION_PROFILE_V2_DOMAIN = (
    "acfqp:v075-k7-broker-resource-session-profile:v2"
)
V075_K7_BROKER_ROLE_CAPABILITY_BUNDLE_V2_DOMAIN = (
    "acfqp:v075-k7-broker-role-capability-bundle:v2"
)
V075_K7_BROKER_RESOURCE_SESSION_V2_DOMAIN = (
    "acfqp:v075-k7-broker-resource-session:v2"
)
V075_K7_AUTHENTICATED_BROKER_CHANNEL_PROFILE_V2_DOMAIN = (
    "acfqp:v075-k7-authenticated-broker-channel-profile:v2"
)
V075_K7_AUTHENTICATED_BROKER_FRAME_V2_DOMAIN = (
    "acfqp:v075-k7-authenticated-broker-frame:v2"
)
V075_K7_PRODUCTION_ROLE_SANDBOX_PROFILE_V2_DOMAIN = (
    "acfqp:v075-k7-production-role-sandbox-profile:v2"
)
V075_K7_PRODUCTION_ROLE_POSTEXEC_TIGHTENING_V2_DOMAIN = (
    "acfqp:v075-k7-production-role-postexec-tightening:v2"
)
V075_K7_PRODUCTION_ROLE_LAUNCH_AUTHORITY_PROFILE_V2_DOMAIN = (
    "acfqp:v075-k7-production-role-launch-authority-profile:v2"
)
V075_K7_PRODUCTION_ROLE_LAUNCH_AUTHORITY_V2_DOMAIN = (
    "acfqp:v075-k7-production-role-launch-authority:v2"
)
CONSTRUCTION_SHARED_RESOURCE_TRANSFER_MOUNT_SESSION_V2_DOMAIN = (
    "acfqp:construction-shared-resource-transfer-mount-session:v2"
)
CONSTRUCTION_SHARED_RESOURCE_TRANSFER_PURPOSE_V2_DOMAIN = (
    "acfqp:construction-shared-resource-transfer-purpose:v2"
)
CONSTRUCTION_SHARED_RESOURCE_TRANSFER_PAYLOAD_V2_DOMAIN = (
    "acfqp:construction-shared-resource-transfer-payload:v2"
)
CONSTRUCTION_SHARED_RESOURCE_TRANSFER_ID_V2_DOMAIN = (
    "acfqp:construction-shared-resource-transfer-id:v2"
)
CONSTRUCTION_SHARED_RESOURCE_TRANSFER_CHARGE_KEY_V2_DOMAIN = (
    "acfqp:construction-shared-resource-transfer-charge-key:v2"
)
CONSTRUCTION_SHARED_RESOURCE_TRANSFER_EVENT_V2_DOMAIN = (
    "acfqp:construction-shared-resource-transfer-event:v2"
)
CONSTRUCTION_SHARED_RESOURCE_MOUNT_INTERVAL_V2_DOMAIN = (
    "acfqp:construction-shared-resource-mount-interval:v2"
)
CONSTRUCTION_SHARED_RESOURCE_MOUNT_EVENT_V2_DOMAIN = (
    "acfqp:construction-shared-resource-mount-event:v2"
)
V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN = (
    "acfqp:v075-k7-operational-cutoff-attestation:v2"
)
V075_K7_READ_TRANSFER_JOURNAL_V2_DOMAIN = (
    "acfqp:v075-k7-read-transfer-journal:v2"
)
V075_K7_STAGED_TRANSFER_JOURNAL_V2_DOMAIN = (
    "acfqp:v075-k7-staged-transfer-journal:v2"
)
V075_K7_TRANSFER_CHARGE_REGISTRY_V2_DOMAIN = (
    "acfqp:v075-k7-transfer-charge-registry:v2"
)
V075_K7_MOUNT_PAYLOAD_REGISTRY_V2_DOMAIN = (
    "acfqp:v075-k7-mount-payload-registry:v2"
)
V075_K7_MOUNT_VISIBILITY_JOURNAL_V2_DOMAIN = (
    "acfqp:v075-k7-mount-visibility-journal:v2"
)
CONSTRUCTION_SHARED_RESOURCE_COMMON_SESSION_V2_DOMAIN = (
    "acfqp:construction-shared-resource-common-session:v2"
)
CONSTRUCTION_SHARED_RESOURCE_COMMON_SOURCE_SITE_V2_DOMAIN = (
    "acfqp:construction-shared-resource-common-source-site:v2"
)
CONSTRUCTION_SHARED_RESOURCE_HASH_PURPOSE_V2_DOMAIN = (
    "acfqp:construction-shared-resource-hash-purpose:v2"
)
CONSTRUCTION_SHARED_RESOURCE_NAMED_OBLIGATION_V2_DOMAIN = (
    "acfqp:construction-shared-resource-named-obligation:v2"
)
CONSTRUCTION_SHARED_RESOURCE_BROKER_OBSERVATION_BINDING_V2_DOMAIN = (
    "acfqp:construction-shared-resource-broker-observation-binding:v2"
)
CONSTRUCTION_SHARED_RESOURCE_COMMON_EVENT_V2_DOMAIN = (
    "acfqp:construction-shared-resource-common-event:v2"
)
V075_K7_HASH_EVENT_TRANSCRIPT_V2_DOMAIN = (
    "acfqp:v075-k7-hash-event-transcript:v2"
)
V075_K7_HASH_PURPOSE_REGISTRY_V2_DOMAIN = (
    "acfqp:v075-k7-hash-purpose-registry:v2"
)
V075_K7_LOADED_HASH_SITE_ATTESTATION_V2_DOMAIN = (
    "acfqp:v075-k7-loaded-hash-site-attestation:v2"
)
V075_K7_INTEGRITY_OBLIGATION_REGISTRY_V2_DOMAIN = (
    "acfqp:v075-k7-integrity-obligation-registry:v2"
)
V075_K7_INTEGRITY_OBLIGATION_TRANSCRIPT_V2_DOMAIN = (
    "acfqp:v075-k7-integrity-obligation-transcript:v2"
)
V075_K7_LOADED_INTEGRITY_SITE_ATTESTATION_V2_DOMAIN = (
    "acfqp:v075-k7-loaded-integrity-site-attestation:v2"
)
V075_K7_PROTOCOL_OBLIGATION_REGISTRY_V2_DOMAIN = (
    "acfqp:v075-k7-protocol-obligation-registry:v2"
)
V075_K7_PROTOCOL_OBLIGATION_TRANSCRIPT_V2_DOMAIN = (
    "acfqp:v075-k7-protocol-obligation-transcript:v2"
)
V075_K7_LOADED_PROTOCOL_SITE_ATTESTATION_V2_DOMAIN = (
    "acfqp:v075-k7-loaded-protocol-site-attestation:v2"
)
CONSTRUCTION_SHARED_RESOURCE_OUTPUT_FINALIZATION_SESSION_V2_DOMAIN = (
    "acfqp:construction-shared-resource-output-finalization-session:v2"
)
CONSTRUCTION_SHARED_RESOURCE_DURABLE_WRITE_EVENT_V2_DOMAIN = (
    "acfqp:construction-shared-resource-durable-write-event:v2"
)
CONSTRUCTION_SHARED_RESOURCE_OUTPUT_FIXED_POINT_ITERATION_V2_DOMAIN = (
    "acfqp:construction-shared-resource-output-fixed-point-iteration:v2"
)
V075_K7_DURABLE_OUTPUT_FIXED_POINT_V2_DOMAIN = (
    "acfqp:v075-k7-durable-output-fixed-point:v2"
)
V075_K7_EXCLUSIVE_WRITER_ATTESTATION_V2_DOMAIN = (
    "acfqp:v075-k7-exclusive-writer-attestation:v2"
)
V075_K7_EIGHT_ROLE_OUTPUT_MANIFEST_V2_DOMAIN = (
    "acfqp:v075-k7-eight-role-output-manifest:v2"
)
CONSTRUCTION_SHARED_RESOURCE_WORKING_PROCESS_EVENT_V2_DOMAIN = (
    "acfqp:construction-shared-resource-working-process-event:v2"
)
V075_K7_CGROUP_EMPTY_ATTESTATION_V2_DOMAIN = (
    "acfqp:v075-k7-cgroup-empty-attestation:v2"
)
V075_K7_MEMORY_PEAK_POST_READ_V2_DOMAIN = (
    "acfqp:v075-k7-memory-peak-post-read:v2"
)
V075_K7_MEMORY_PEAK_PRE_READ_V2_DOMAIN = (
    "acfqp:v075-k7-memory-peak-pre-read:v2"
)
V075_K7_SAME_OFD_ATTESTATION_V2_DOMAIN = (
    "acfqp:v075-k7-same-ofd-attestation:v2"
)
V075_K7_NO_SPAWN_ATTESTATION_V2_DOMAIN = (
    "acfqp:v075-k7-no-spawn-attestation:v2"
)
V075_K7_PIDFD_REAP_ATTESTATION_V2_DOMAIN = (
    "acfqp:v075-k7-pidfd-reap-attestation:v2"
)
V075_K7_PROCESS_LIFECYCLE_JOURNAL_V2_DOMAIN = (
    "acfqp:v075-k7-process-lifecycle-journal:v2"
)
CONSTRUCTION_SHARED_RESOURCE_BOUND_SOURCE_V3_DOMAIN = (
    "acfqp:construction-shared-resource-bound-source:v3"
)
V075_K7_PRODUCTION_SHARED_RESOURCE_ENVELOPE_V3_DOMAIN = (
    "acfqp:v075-k7-production-shared-resource-envelope:v3"
)
V075_K7_PRODUCTION_BROKER_RUNTIME_PROFILE_V2_DOMAIN = (
    "acfqp:v075-k7-production-broker-runtime-profile:v2"
)
V075_K7_PRODUCTION_BROKER_RUNTIME_ENVELOPE_V2_DOMAIN = (
    "acfqp:v075-k7-production-broker-runtime-envelope:v2"
)
CONSTRUCTION_SHARED_RESOURCE_SEMANTIC_VERIFIER_V2_DOMAIN = (
    "acfqp:construction-shared-resource-semantic-verifier:v2"
)
CONSTRUCTION_SHARED_RESOURCE_PATH_EXACT_AUTHORIZATION_V1_DOMAIN = (
    "acfqp:construction-shared-resource-path-exact-authorization:v1"
)
V075_K7_VERIFIED_NINE_SHARED_RESOURCE_ENVELOPE_V1_DOMAIN = (
    "acfqp:v075-k7-verified-nine-shared-resource-envelope:v1"
)
CONSTRUCTION_SHARED_CAP_PROFILE_V1_DOMAIN = (
    "acfqp:construction-shared-cap-profile:v1"
)
CONSTRUCTION_SHARED_CAP_FALLBACK_DECISION_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-shared-cap-fallback-decision-candidate:v1"
)
CONSTRUCTION_SHARED_CAP_FALLBACK_DECISION_PREREQUISITE_V1_DOMAIN = (
    "acfqp:construction-shared-cap-fallback-decision-prerequisite:v1"
)
CONSTRUCTION_SHARED_CAP_SESSION_V1_DOMAIN = (
    "acfqp:construction-shared-cap-session:v1"
)
CONSTRUCTION_SHARED_CAP_RESERVATION_V1_DOMAIN = (
    "acfqp:construction-shared-cap-reservation:v1"
)
CONSTRUCTION_SHARED_CAP_MOUNT_TOKEN_V1_DOMAIN = (
    "acfqp:construction-shared-cap-mount-token:v1"
)
CONSTRUCTION_SHARED_CAP_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-shared-cap-receipt:v1"
)
CONSTRUCTION_SHARED_CAP_SNAPSHOT_V1_DOMAIN = (
    "acfqp:construction-shared-cap-snapshot:v1"
)
CONSTRUCTION_K7_DIRECT_FALLBACK_SHARED_SOURCE_SITE_V1_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-shared-source-site:v1"
)
CONSTRUCTION_K7_DIRECT_FALLBACK_SHARED_SOURCE_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-shared-source-manifest:v1"
)
CONSTRUCTION_K7_DIRECT_FALLBACK_AGGREGATE_CAP_FORMULA_SPEC_V1_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-aggregate-cap-formula-spec:v1"
)
CONSTRUCTION_K7_DIRECT_FALLBACK_MANIFEST_BOUND_CAP_JOIN_V1_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-manifest-bound-cap-join:v1"
)
CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-direct-fallback-two-role-recipe-profile:v1"
)
CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-direct-fallback-two-role-recipe:v1"
)
CONSTRUCTION_K7_H1_CURRENT_BUILD_KERNEL_ATTESTATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-build-kernel-attestation:v1"
)
CONSTRUCTION_K7_H1_CURRENT_QUERY_ATTESTATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-query-attestation:v1"
)
CONSTRUCTION_K7_H1_CURRENT_SOURCE_FIXTURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-source-fixture:v1"
)
CONSTRUCTION_K7_H1_DURABLE_PROOF_MATCH_ATTESTATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-durable-proof-match-attestation:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-current-identity:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-current-identity-verification:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_EXECUTION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-execution-profile:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_CONTEXT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-predecision-context:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_INPUT_SET_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-predecision-input-set:v1"
)
CONSTRUCTION_K7_H1_PREDECISION_ACCESS_EVENT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-predecision-access-event:v1"
)
CONSTRUCTION_K7_H1_PREDECISION_ACCESS_LOG_V1_DOMAIN = (
    "acfqp:construction-k7-h1-predecision-access-log:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_CHILD_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-child-result:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-observed-evidence:v1"
)
CONSTRUCTION_K7_H1_PREDECISION_CURRENT_ACCESS_CUTOFF_V1_DOMAIN = (
    "acfqp:construction-k7-h1-predecision-current-access-cutoff:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_ACCESS_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-current-access-authority:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_CONSTRUCTION_FIXTURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-construction-fixture:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_AUTHORITY_BLOCKER_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-authority-blocker:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-fresh-exec-runtime-profile:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_SOURCE_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-fresh-exec-source-manifest:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-fresh-exec-runtime-manifest:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_RUNTIME_UNAVAILABLE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-runtime-unavailable:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-observed-runtime-facts:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-observed-runtime-facts-verification:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_PROFILE_V2_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-profile:v2"
)
CONSTRUCTION_K7_H1_SHARED_CAP_SOURCE_MANIFEST_V2_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-source-manifest:v2"
)
CONSTRUCTION_K7_H1_SHARED_CAP_RUNTIME_V2_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-runtime:v2"
)
CONSTRUCTION_K7_H1_SHARED_CAP_RECEIPT_V2_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-receipt:v2"
)
CONSTRUCTION_K7_H1_SHARED_CAP_EVENT_V2_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-event:v2"
)
CONSTRUCTION_K7_H1_SHARED_CAP_MOUNT_TOKEN_V2_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-mount-token:v2"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OUTPUT_TOKEN_V2_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-output-token:v2"
)
CONSTRUCTION_K7_H1_SHARED_CAP_MEMORY_BINDING_V2_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-memory-binding:v2"
)
CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_BRANCH_DAG_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-output-branch-dag:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_SERIALIZER_UNIVERSE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-output-serializer-universe:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_CONTEXT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-output-operand-context:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_ROLE_UPPER_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-output-role-upper:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_FIXED_POINT_ITERATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-output-fixed-point-iteration:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_BRANCH_FIXED_POINT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-output-branch-fixed-point:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-output-operand-authority:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-output-operand-candidate:v1"
)
CONSTRUCTION_K7_H1_SHARED_RESOURCE_BRANCH_PROGRAM_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-resource-branch-program:v1"
)
CONSTRUCTION_K7_H1_SHARED_COMMON_CATALOGUE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-common-catalogue:v1"
)
CONSTRUCTION_K7_H1_SHARED_IO_CATALOGUE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-io-catalogue:v1"
)
CONSTRUCTION_K7_H1_PHYSICAL_MOUNT_CATALOGUE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-physical-mount-catalogue:v1"
)
CONSTRUCTION_K7_H1_MEMORY_SCOPE_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-memory-scope-authority:v1"
)
CONSTRUCTION_K7_H1_LAUNCH_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-launch-authority:v1"
)
CONSTRUCTION_K7_H1_MEMORY_SCOPE_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-memory-scope-candidate:v1"
)
CONSTRUCTION_K7_H1_LAUNCH_CATALOGUE_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-launch-catalogue-candidate:v1"
)
CONSTRUCTION_K7_H1_SHARED_OPERAND_CONTEXT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-operand-context:v1"
)
CONSTRUCTION_K7_H1_SHARED_OPERAND_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-operand-row:v1"
)
CONSTRUCTION_K7_H1_SHARED_OPERAND_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-operand-authority:v1"
)
CONSTRUCTION_K7_H1_PREDECISION_COMMON_PREFIX_RESERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-predecision-common-prefix-reservation:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-lifecycle-source-manifest:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_PROGRAM_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-lifecycle-program:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_BRANCH_ANALYSIS_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-lifecycle-branch-analysis:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-lifecycle-replay:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-lifecycle-source-authority:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-lifecycle-source-candidate:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_LOCAL_SOURCE_REGISTRY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-local-source-registry:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_PROGRAM_SNAPSHOT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-program-snapshot:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_FINAL_PREREGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-final-preregistration:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_LOCAL_MAIN_ANCHOR_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-local-main-anchor:v1"
)
CONSTRUCTION_K7_H1_CALLER_PINNED_LIFECYCLE_PROVENANCE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-caller-pinned-lifecycle-provenance:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-profile:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SOURCE_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-source-manifest:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RUNTIME_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-runtime:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RESERVATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-reservation:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_NATIVE_CELL_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-native-cell:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_NATIVE_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-native-evidence:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SETTLEMENT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-settlement:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-receipt:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_EVENT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-event:v1"
)
CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SNAPSHOT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-shared-cap-owner-v3-snapshot:v1"
)
CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_GATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-attempt-rejection-gate:v1"
)
CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-attempt-rejection-commit:v1"
)
CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_ACK_V1_DOMAIN = (
    "acfqp:construction-k7-h1-attempt-rejection-ack:v1"
)
CONSTRUCTION_K7_H1_ANCHORED_LIFECYCLE_HANDLER_REGISTRY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-anchored-lifecycle-handler-registry:v1"
)
CONSTRUCTION_K7_H1_ANCHORED_LIFECYCLE_PROGRAM_V1_DOMAIN = (
    "acfqp:construction-k7-h1-anchored-lifecycle-program:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-dispatch-profile:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_EVENT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-dispatch-event:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_TRACE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-dispatch-trace:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_COMPLETE_BRANCH_ANALYSIS_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-complete-branch-analysis:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_CLEANUP_PASS_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-cleanup-pass:v1"
)
CONSTRUCTION_K7_H1_LIFECYCLE_OUTPUT_LEAF_JOIN_V1_DOMAIN = (
    "acfqp:construction-k7-h1-lifecycle-output-leaf-join:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-atomic-bridge-profile:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_EXPORT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-atomic-bridge-export:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_REQUEST_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-atomic-bridge-request:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_COMMIT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-atomic-bridge-commit:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-atomic-bridge-receipt:v1"
)
CONSTRUCTION_K7_H1_POSTFREEZE_CURRENT_ACCESS_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-h1-postfreeze-current-access-authority:v1"
)
CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_ITERATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-joint-output-read-iteration:v1"
)
CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-joint-output-read-fixed-point:v1"
)
CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-branch-aware-output-profile:v1"
)
CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_BUSINESS_FIXTURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-branch-aware-output-business-fixture:v1"
)
CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_BROKER_FIXTURE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-branch-aware-output-broker-fixture:v1"
)
CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_INPUT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-branch-aware-output-input:v1"
)
CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_ROLE_ARTIFACT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-branch-aware-output-role-artifact:v1"
)
CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_ARTIFACT_SET_V1_DOMAIN = (
    "acfqp:construction-k7-h1-branch-aware-output-artifact-set:v1"
)
CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_FIXED_POINT_ITERATION_V1_DOMAIN = (
    "acfqp:construction-k7-h1-branch-aware-output-fixed-point-iteration:v1"
)
CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_FIXED_POINT_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-h1-branch-aware-output-fixed-point-result:v1"
)
CONSTRUCTION_K7_H1_BUSINESS_ADAPTER_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-business-adapter-profile:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_BUSINESS_REQUEST_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-business-request-candidate:v1"
)
CONSTRUCTION_K7_H1_PRODUCTION_BUSINESS_RESULT_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-production-business-result-candidate:v1"
)
CONSTRUCTION_K7_H1_CURRENT_ACCESS_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-current-access-candidate:v1"
)
CONSTRUCTION_K7_H1_FORMAL_V7_DECISION_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-formal-v7-decision-candidate:v1"
)
CONSTRUCTION_K7_H1_SEARCH_SEMANTICS_BRIDGE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-search-semantics-bridge:v1"
)
CONSTRUCTION_K7_H1_BUSINESS_RESULT_COMMIT_RECEIPT_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-business-result-commit-receipt-candidate:v1"
)
CONSTRUCTION_K7_H1_WORKER_RESULT_VERIFICATION_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-worker-result-verification-candidate:v1"
)
CONSTRUCTION_K7_H1_EXECUTION_TOPOLOGY_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-execution-topology-profile:v1"
)
CONSTRUCTION_K7_H1_BROKER_IPC_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-broker-ipc-profile:v1"
)
CONSTRUCTION_K7_H1_BROKER_IPC_BINDING_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-broker-ipc-binding-candidate:v1"
)
CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_READY_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-broker-ipc-worker-ready-candidate:v1"
)
CONSTRUCTION_K7_H1_BROKER_IPC_BUSINESS_REQUEST_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-broker-ipc-business-request-candidate:v1"
)
CONSTRUCTION_K7_H1_BROKER_IPC_BUSINESS_RESULT_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-broker-ipc-business-result-candidate:v1"
)
CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_ACK_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-broker-ipc-worker-ack-candidate:v1"
)
CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_EOF_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-broker-ipc-worker-eof-candidate:v1"
)
CONSTRUCTION_K7_H1_BROKER_IPC_TRANSCRIPT_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-h1-broker-ipc-transcript-candidate:v1"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_SOURCE_AUTHORITY_DOMAIN = (
    "acfqp:construction-accounting-route-segment-source-authority:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_MANIFEST_AUTHORITY_DOMAIN = (
    "acfqp:construction-accounting-route-segment-manifest-authority:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNER_BLOCKER_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owner-blocker:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_START_DOMAIN = (
    "acfqp:construction-accounting-route-segment-start:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_EVENT_DOMAIN = (
    "acfqp:construction-accounting-route-segment-event:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TERMINAL_DOMAIN = (
    "acfqp:construction-accounting-route-segment-terminal:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TRANSCRIPT_DOMAIN = (
    "acfqp:construction-accounting-route-segment-transcript:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_SOURCE_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-engine-source:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_BOUNDARY_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-engine-boundary:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_AUTHORITY_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-engine-authority:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_START_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-start:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_EVENT_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-event:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_EXECUTION_BINDING_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-execution-binding:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_STRUCTURAL_SEMANTICS_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-structural-semantics:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_KERNEL_SEMANTICS_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-kernel-semantics:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_QUERY_SEMANTICS_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-query-semantics:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_THRESHOLD_SEMANTICS_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-threshold-semantics:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_REWARD_SEMANTICS_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-reward-semantics:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_POLICY_CLASS_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-policy-class:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_PROFILE_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-search-profile:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_SEMANTICS_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-search-semantics:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_G2048_TRANSITION_CLOSURE_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-g2048-transition-closure:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_TERMINAL_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-terminal:v4"
)
CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_TRANSCRIPT_DOMAIN = (
    "acfqp:construction-accounting-route-segment-owned-transcript:v4"
)
CONSTRUCTION_OWNER_BOUNDARY_SITE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-owner-boundary-site-closure:v1"
)
CONSTRUCTION_OWNER_PATH_COUNTER_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-owner-path-counter-candidate:v1"
)
CONSTRUCTION_OWNER_EVENT_CANDIDATE_SET_V1_DOMAIN = (
    "acfqp:construction-owner-event-candidate-set:v1"
)
CONSTRUCTION_OWNER_EVENT_EXECUTION_BINDING_V1_DOMAIN = (
    "acfqp:construction-owner-event-execution-binding:v1"
)
CONSTRUCTION_OWNER_SOURCE_CODE_IDENTITY_V1_DOMAIN = (
    "acfqp:construction-owner-source-code-identity:v1"
)
CONSTRUCTION_OWNER_POSTEXEC_BINDING_V1_DOMAIN = (
    "acfqp:construction-owner-postexec-binding:v1"
)
CONSTRUCTION_K7_RECONCILIATION_FORMULA_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-reconciliation-formula-authority:v1"
)
CONSTRUCTION_K7_RECONCILIATION_ARITHMETIC_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-reconciliation-arithmetic-replay:v1"
)
CONSTRUCTION_K7_RECONCILIATION_SEMANTIC_DEPENDENCY_V1_DOMAIN = (
    "acfqp:construction-k7-reconciliation-semantic-dependency:v1"
)
CONSTRUCTION_K7_RECONCILIATION_PATH_PROOF_V1_DOMAIN = (
    "acfqp:construction-k7-reconciliation-path-proof:v1"
)
CONSTRUCTION_K7_RECONCILIATION_BLOCKER_V1_DOMAIN = (
    "acfqp:construction-k7-reconciliation-blocker:v1"
)
CONSTRUCTION_K7_RECONCILIATION_READINESS_V1_DOMAIN = (
    "acfqp:construction-k7-reconciliation-readiness:v1"
)
CONSTRUCTION_K7_OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_V2_DOMAIN = (
    "acfqp:construction-k7-occurrence-identity-semantic-authority:v2"
)
CONSTRUCTION_K7_OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_V2_DOMAIN = (
    "acfqp:construction-k7-operational-cutoff-semantic-authority:v2"
)
CONSTRUCTION_K7_OCCURRENCE_CUTOFF_SEMANTIC_AUTHORITY_BUNDLE_V2_DOMAIN = (
    "acfqp:construction-k7-occurrence-cutoff-semantic-authority-bundle:v2"
)
CONSTRUCTION_K7_PRODUCTION_MEASUREMENT_START_V2_DOMAIN = (
    "acfqp:construction-k7-production-measurement-start:v2"
)
CONSTRUCTION_K7_PRODUCTION_MEASUREMENT_CUTOFF_V2_DOMAIN = (
    "acfqp:construction-k7-production-measurement-cutoff:v2"
)
CONSTRUCTION_K7_PRODUCTION_TERMINAL_CLOSURE_V2_DOMAIN = (
    "acfqp:construction-k7-production-terminal-closure:v2"
)
CONSTRUCTION_K7_ROUTE_TERMINAL_SEMANTIC_DEPENDENCY_V2_DOMAIN = (
    "acfqp:construction-k7-route-terminal-semantic-dependency:v2"
)
CONSTRUCTION_K7_EXACT_ROUTE_DERIVED_PATH_PROOF_V2_DOMAIN = (
    "acfqp:construction-k7-exact-route-derived-path-proof:v2"
)
CONSTRUCTION_K7_COMPLETE_DERIVED_RECONCILIATION_READINESS_V2_DOMAIN = (
    "acfqp:construction-k7-complete-derived-reconciliation-readiness:v2"
)
CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_HOOK_INVENTORY_V1_DOMAIN = (
    "acfqp:construction-k7-native-zero-source-hook-inventory:v1"
)
CONSTRUCTION_K7_NATIVE_ZERO_OWNER_WINDOW_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-native-zero-owner-window-closure:v1"
)
CONSTRUCTION_K7_NATIVE_ZERO_STAGE_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-native-zero-stage-evidence:v1"
)
CONSTRUCTION_K7_NATIVE_ZERO_BRANCH_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-native-zero-branch-evidence:v1"
)
CONSTRUCTION_K7_NATIVE_ZERO_REPLACEMENT_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-native-zero-replacement-evidence:v1"
)
CONSTRUCTION_K7_NATIVE_ZERO_SEMANTIC_VERIFIER_V1_DOMAIN = (
    "acfqp:construction-k7-native-zero-semantic-verifier:v1"
)
CONSTRUCTION_K7_PROFILE_NATIVE_ZERO_ATTESTATION_V1_DOMAIN = (
    "acfqp:construction-k7-profile-native-zero-attestation:v1"
)
CONSTRUCTION_K7_PROFILE_NATIVE_ZERO_ENVELOPE_V1_DOMAIN = (
    "acfqp:construction-k7-profile-native-zero-envelope:v1"
)
CONSTRUCTION_K7_SEMANTIC_PATH_RECORDER_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-semantic-path-recorder-authority:v1"
)
CONSTRUCTION_K7_SEMANTIC_PATH_RESOLUTION_V1_DOMAIN = (
    "acfqp:construction-k7-semantic-path-resolution:v1"
)
CONSTRUCTION_K7_SEMANTIC_EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN = (
    "acfqp:construction-k7-semantic-evidence-closure-context:v1"
)
CONSTRUCTION_K7_SEMANTIC_EVIDENCE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-semantic-evidence-closure:v1"
)
CONSTRUCTION_K7_FORMAL_ACTUAL_PROJECTION_PROOF_V6_DOMAIN = (
    "acfqp:construction-k7-formal-actual-projection-proof:v6"
)
CONSTRUCTION_K7_FORMAL_ACCOUNTING_MATERIALIZATION_BUNDLE_V1_DOMAIN = (
    "acfqp:construction-k7-formal-accounting-materialization-bundle:v1"
)
CONSTRUCTION_K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-root-cap-semantics-profile:v1"
)
CONSTRUCTION_K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-root-cap-exhaustion-evidence:v1"
)
CONSTRUCTION_K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-root-cap-attempt-terminal-authority:v1"
)
CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN = (
    "acfqp:construction-k7-root-cap-terminal-accounting-bundle:v1"
)
CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-root-cap-terminal-accounting-verification:v1"
)
CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-production-complete-bundle-verification-profile:v1"
)
CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN = (
    "acfqp:construction-k7-production-complete-bundle-semantic-verifier:v1"
)
CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_EVALUATION_RECORDER_V1_DOMAIN = (
    "acfqp:construction-k7-production-complete-bundle-evaluation-recorder:v1"
)
CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-production-complete-bundle-verification:v1"
)
CONSTRUCTION_K7_LOGICAL_OCCURRENCE_WORK_SUM_V1_DOMAIN = (
    "acfqp:construction-k7-logical-occurrence-work-sum:v1"
)
CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-logical-occurrence-closure-authority:v1"
)
CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN = (
    "acfqp:construction-k7-logical-occurrence-closure-bundle:v1"
)
CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-logical-occurrence-closure-verification:v1"
)
CONSTRUCTION_K7_CAMPAIGN_REGISTRATION_V1_DOMAIN = (
    "acfqp:construction-k7-campaign-registration:v1"
)
CONSTRUCTION_K7_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-campaign-occurrence-row:v1"
)
CONSTRUCTION_K7_CAMPAIGN_CLOSURE_SUMMARY_V1_DOMAIN = (
    "acfqp:construction-k7-campaign-closure-summary:v1"
)
CONSTRUCTION_K7_CAMPAIGN_CLOSURE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-campaign-closure-verification:v1"
)
CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_SOURCE_V1_DOMAIN = (
    "acfqp:construction-k7-terminal-accounting-coverage-source:v1"
)
CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_ROW_V1_DOMAIN = (
    "acfqp:construction-k7-terminal-accounting-coverage-row:v1"
)
CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_MATRIX_V1_DOMAIN = (
    "acfqp:construction-k7-terminal-accounting-coverage-matrix:v1"
)
CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-terminal-accounting-coverage-replay:v1"
)
CONSTRUCTION_K7_ALL_PATH_ACCOUNTING_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-all-path-accounting-profile:v1"
)
CONSTRUCTION_K7_ALL_PATH_ACCOUNTING_PROFILE_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-all-path-accounting-profile-replay:v1"
)
CONSTRUCTION_K7_V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN = (
    "acfqp:construction-k7-v075-terminal-status-inventory:v1"
)
PHASE3E_EXACT_INFEASIBILITY_DURABLE_PROOF_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-durable-proof:v1"
)
PHASE3E_EXACT_INFEASIBILITY_IDENTITY_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-identity:v1"
)
PHASE3E_EXACT_INFEASIBILITY_STRUCTURAL_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-structural:v1"
)
PHASE3E_EXACT_INFEASIBILITY_QUERY_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-query:v1"
)
PHASE3E_EXACT_INFEASIBILITY_KERNEL_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-kernel:v1"
)
PHASE3E_EXACT_INFEASIBILITY_BUILD_EPOCH_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-build-epoch:v1"
)
PHASE3E_EXACT_INFEASIBILITY_THRESHOLD_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-threshold:v1"
)
PHASE3E_EXACT_INFEASIBILITY_REWARD_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-reward:v1"
)
PHASE3E_EXACT_INFEASIBILITY_POLICY_CLASS_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-policy-class:v1"
)
PHASE3E_EXACT_INFEASIBILITY_SEARCH_PROFILE_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-search-profile:v1"
)
PHASE3E_EXACT_INFEASIBILITY_STATE_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-state:v1"
)
PHASE3E_EXACT_INFEASIBILITY_STATE_ACTION_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-state-action:v1"
)
PHASE3E_EXACT_INFEASIBILITY_SOURCE_PROJECTION_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-source-projection:v1"
)
PHASE3E_EXACT_INFEASIBILITY_VERIFICATION_PROFILE_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-verification-profile:v1"
)
PHASE3E_EXACT_INFEASIBILITY_VERIFICATION_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-verification:v1"
)
PHASE3E_EXACT_INFEASIBILITY_CACHE_CONSUMPTION_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-cache-consumption:v1"
)
PHASE3E_EXACT_INFEASIBILITY_BLOCKER_V1_DOMAIN = (
    "acfqp:phase3e-exact-infeasibility-blocker:v1"
)
CONSTRUCTION_K7_EXPECTED_ARTIFACT_IDENTITY_V1_DOMAIN = (
    "acfqp:construction-k7-expected-artifact-identity:v1"
)
CONSTRUCTION_K7_INTEGRITY_ATTEMPT_CONTEXT_V1_DOMAIN = (
    "acfqp:construction-k7-integrity-attempt-context:v1"
)
CONSTRUCTION_K7_INTEGRITY_ACCESS_EVENT_V1_DOMAIN = (
    "acfqp:construction-k7-integrity-access-event:v1"
)
CONSTRUCTION_K7_INTEGRITY_READ_RECEIPT_V1_DOMAIN = (
    "acfqp:construction-k7-integrity-read-receipt:v1"
)
CONSTRUCTION_K7_INTEGRITY_ACCESS_SEQUENCE_V1_DOMAIN = (
    "acfqp:construction-k7-integrity-access-sequence:v1"
)
CONSTRUCTION_K7_INTEGRITY_PREFIX_RECORDER_V1_DOMAIN = (
    "acfqp:construction-k7-integrity-prefix-recorder:v1"
)
CONSTRUCTION_K7_INTEGRITY_PREFIX_COMPLETENESS_V1_DOMAIN = (
    "acfqp:construction-k7-integrity-prefix-completeness:v1"
)
CONSTRUCTION_K7_INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-integrity-terminal-authority:v1"
)
CONSTRUCTION_K7_INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN = (
    "acfqp:construction-k7-integrity-failure-bundle:v1"
)
CONSTRUCTION_K7_INTEGRITY_FAILURE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-integrity-failure-verification:v1"
)
CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_MANIFEST_V1_DOMAIN = (
    "acfqp:construction-k7-all-path-operation-boundary-manifest:v1"
)
CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_SOURCE_ARCHIVE_V1_DOMAIN = (
    "acfqp:construction-k7-all-path-operation-boundary-source-archive:v1"
)
CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_SITE_V1_DOMAIN = (
    "acfqp:construction-k7-all-path-operation-boundary-site:v1"
)
CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-all-path-operation-boundary-replay:v1"
)
CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_BLOCKER_V1_DOMAIN = (
    "acfqp:construction-k7-all-path-operation-boundary-blocker:v1"
)
CONSTRUCTION_K7_PROTOCOL_REAL_SITE_BLOCKER_V1_DOMAIN = (
    "acfqp:construction-k7-protocol-real-site-blocker:v1"
)
CONSTRUCTION_K7_PROTOCOL_PREFIX_RECORDER_V1_DOMAIN = (
    "acfqp:construction-k7-protocol-prefix-recorder:v1"
)
CONSTRUCTION_K7_PROTOCOL_FAILURE_TERMINAL_AUTHORITY_V1_DOMAIN = (
    "acfqp:construction-k7-protocol-failure-terminal-authority:v1"
)
CONSTRUCTION_K7_PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN = (
    "acfqp:construction-k7-protocol-failure-bundle:v1"
)
CONSTRUCTION_K7_PROTOCOL_FAILURE_VERIFICATION_V1_DOMAIN = (
    "acfqp:construction-k7-protocol-failure-verification:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_SOURCE_ARCHIVE_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-source-archive:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_PATH_GAP_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-path-gap:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COVERAGE_REPORT_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-coverage-report:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_SOURCE_BLOCKER_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-source-blocker:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COVERAGE_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-coverage-replay:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_EXECUTION_WINDOW_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-zero-execution-window:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_PROOF_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-zero-value-proof:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_RESIDUAL_GAP_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-residual-gap:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_CLOSURE_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-zero-value-closure:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-zero-value-closure-replay:v1"
)
CONSTRUCTION_K7_DIRECT_FALLBACK_EXACT_INFEASIBILITY_READINESS_V1_DOMAIN = (
    "acfqp:construction-k7-direct-fallback-exact-infeasibility-readiness:v1"
)
CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN = (
    "acfqp:construction-k7-canonical-infeasible-fallback-preexecution:v1"
)
CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CURRENT_IDENTITY_V1_DOMAIN = (
    "acfqp:construction-k7-canonical-infeasible-fallback-current-identity:v1"
)
CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CARDINALITY_SOURCE_V1_DOMAIN = (
    "acfqp:construction-k7-canonical-infeasible-fallback-cardinality-source:v1"
)
CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_TRANSITION_TRACE_V1_DOMAIN = (
    "acfqp:construction-k7-canonical-infeasible-fallback-transition-trace:v1"
)
CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PATH_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-canonical-infeasible-fallback-path-evidence:v1"
)
CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_ACQUISITION_V1_DOMAIN = (
    "acfqp:construction-k7-canonical-infeasible-fallback-acquisition:v1"
)
CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_SUPPORT_V1_DOMAIN = (
    "acfqp:construction-k7-canonical-infeasible-fallback-support:v1"
)
CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_INVENTORY_CONTEXT_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-pass-retained-v1-inventory-context:v1"
)
CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_SHARED_AGGREGATE_CLAIM_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-pass-legacy-shared-aggregate-claim:v1"
)
CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_OWNER_EVENT_CANDIDATE_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-pass-legacy-owner-event-candidate:v1"
)
CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_RECONCILIATION_CLAIM_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-pass-legacy-reconciliation-claim:v1"
)
CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_FORMAL_BLOCKER_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-pass-retained-v1-formal-blocker:v1"
)
CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_EVIDENCE_INVENTORY_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-pass-retained-v1-evidence-inventory:v1"
)
CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_INVENTORY_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-pass-retained-v1-inventory-replay:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_WINDOW_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-query-owner-window:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_RESOLUTION_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-query-owner-resolution:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_ENVELOPE_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-query-owner-envelope:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-query-owner-replay:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_WINDOW_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-lifecycle-window:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_RESOLUTION_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-lifecycle-resolution:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_ENVELOPE_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-lifecycle-envelope:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-lifecycle-replay:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_WINDOW_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-common-shared-window:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_RESOLUTION_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-common-shared-resolution:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_ENVELOPE_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-common-shared-envelope:v1"
)
CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-certified-common-shared-replay:v1"
)
CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_RUNTIME_PREPARATION_V2_DOMAIN = (
    "acfqp:construction-k7-abstract-accounted-runtime-preparation:v2"
)
CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_WORKER_OUTPUT_V2_DOMAIN = (
    "acfqp:construction-k7-abstract-accounted-worker-output:v2"
)
CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_MEASUREMENT_WINDOW_V2_DOMAIN = (
    "acfqp:construction-k7-abstract-accounted-measurement-window:v2"
)
CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_RESOLUTION_V2_DOMAIN = (
    "acfqp:construction-k7-abstract-accounted-shared-resolution:v2"
)
CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_ENVELOPE_V2_DOMAIN = (
    "acfqp:construction-k7-abstract-accounted-shared-envelope:v2"
)
CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_REPLAY_V2_DOMAIN = (
    "acfqp:construction-k7-abstract-accounted-shared-replay:v2"
)
CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_RUNTIME_WINDOW_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-query-zero-runtime-window:v1"
)
CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_RESOLUTION_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-query-zero-resolution:v1"
)
CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_ENVELOPE_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-query-zero-envelope:v1"
)
CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-abstract-query-zero-replay:v1"
)
CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_PROFILE_V1_DOMAIN = (
    "acfqp:construction-k7-conditional-terminal-normalization-profile:v1"
)
CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_RULE_V1_DOMAIN = (
    "acfqp:construction-k7-conditional-terminal-normalization-rule:v1"
)
CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_EVIDENCE_V1_DOMAIN = (
    "acfqp:construction-k7-conditional-terminal-normalization-evidence:v1"
)
CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_RESULT_V1_DOMAIN = (
    "acfqp:construction-k7-conditional-terminal-normalization-result:v1"
)
CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-conditional-terminal-normalization-replay:v1"
)
CONSTRUCTION_K7_V075_PLAN_ROUTE_PROVENANCE_V1_DOMAIN = (
    "acfqp:construction-k7-v075-plan-route-provenance:v1"
)
CONSTRUCTION_K7_V075_PLAN_ROUTE_NORMALIZATION_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-v075-plan-route-normalization-binding:v1"
)
CONSTRUCTION_K7_V075_PLAN_ROUTE_PROVENANCE_REPLAY_V1_DOMAIN = (
    "acfqp:construction-k7-v075-plan-route-provenance-replay:v1"
)
CONSTRUCTION_K7_V075_BATCHED_CAUSAL_ROUTE_PROVENANCE_V1_DOMAIN = (
    "acfqp:construction-k7-v075-batched-causal-route-provenance:v1"
)
CONSTRUCTION_K7_V075_BATCHED_CAUSAL_ROUTE_NORMALIZATION_BINDING_V1_DOMAIN = (
    "acfqp:construction-k7-v075-batched-causal-route-normalization-binding:v1"
)
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
V072_ANCHORED_CAMPAIGN_ATTEMPT_FAILURE_DOMAIN = (
    "acfqp:v072-anchored-campaign-attempt-failure:v1"
)
V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_DOMAIN = (
    "acfqp:v072-registered-campaign-attempt-journal:v1"
)
V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_OBJECT_DOMAIN = (
    "acfqp:v072-registered-campaign-attempt-journal-object:v1"
)
V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_EVENT_DOMAIN = (
    "acfqp:v072-registered-campaign-attempt-journal-event:v1"
)
FROZEN_SOURCE_ARCHIVE_ENVELOPE_DOMAIN = (
    "acfqp:v074-frozen-source-archive-envelope:v1"
)
FROZEN_SOURCE_OFFLINE_WORK_DOMAIN = (
    "acfqp:v074-frozen-source-offline-work:v1"
)
FROZEN_SOURCE_OCCURRENCE_INPUT_DOMAIN = (
    "acfqp:v074-frozen-source-occurrence-input:v1"
)
FROZEN_SOURCE_OCCURRENCE_OUTPUT_DOMAIN = (
    "acfqp:v074-frozen-source-occurrence-output:v1"
)
FROZEN_SOURCE_CHILD_ATTEMPT_JOURNAL_DOMAIN = (
    "acfqp:v074-frozen-source-child-attempt-journal:v1"
)
FROZEN_SOURCE_OCCURRENCE_FAILURE_CLOSURE_DOMAIN = (
    "acfqp:v074-frozen-source-occurrence-failure-closure:v1"
)
FROZEN_SOURCE_OCCURRENCE_MERGE_DOMAIN = (
    "acfqp:v074-frozen-source-occurrence-merge:v1"
)
FROZEN_SOURCE_VERIFICATION_ATTESTATION_DOMAIN = (
    "acfqp:v074-frozen-source-verification-attestation:v1"
)
FROZEN_SOURCE_EXECUTION_BATCH_DOMAIN = (
    "acfqp:v074-frozen-source-execution-batch:v1"
)


PHASE3E_DOMAIN_TAG_REGISTRY: Mapping[str, str] = MappingProxyType(
    {
        "route_upper_bound_envelope": ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN,
        "route_upper_formula": ROUTE_UPPER_FORMULA_DOMAIN,
        "route_upper_derivation_proof": ROUTE_UPPER_DERIVATION_PROOF_DOMAIN,
        "comparison_profile": COMPARISON_PROFILE_DOMAIN,
        "counter_registry": COUNTER_REGISTRY_DOMAIN,
        "construction_comparison_profile_v2": (
            CONSTRUCTION_COMPARISON_PROFILE_V2_DOMAIN
        ),
        "construction_counter_registry_v2": (
            CONSTRUCTION_COUNTER_REGISTRY_V2_DOMAIN
        ),
        "construction_counter_record_v2": (
            CONSTRUCTION_COUNTER_RECORD_V2_DOMAIN
        ),
        "construction_work_vector_v2": (
            CONSTRUCTION_WORK_VECTOR_V2_DOMAIN
        ),
        "construction_comparison_vector_v2": (
            CONSTRUCTION_COMPARISON_VECTOR_V2_DOMAIN
        ),
        "construction_stage_profile_v2": (
            CONSTRUCTION_STAGE_PROFILE_V2_DOMAIN
        ),
        "construction_actual_projection_profile_v2": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V2_DOMAIN
        ),
        "construction_actual_projection_proof_v2": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V2_DOMAIN
        ),
        "construction_counter_registry_v3": (
            CONSTRUCTION_COUNTER_REGISTRY_V3_DOMAIN
        ),
        "construction_stage_profile_v3": (
            CONSTRUCTION_STAGE_PROFILE_V3_DOMAIN
        ),
        "construction_comparison_profile_v3": (
            CONSTRUCTION_COMPARISON_PROFILE_V3_DOMAIN
        ),
        "construction_actual_projection_profile_v3": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V3_DOMAIN
        ),
        "construction_legacy_migration_profile_v3": (
            CONSTRUCTION_LEGACY_MIGRATION_PROFILE_V3_DOMAIN
        ),
        "construction_accounting_lifecycle_v3": (
            CONSTRUCTION_ACCOUNTING_LIFECYCLE_V3_DOMAIN
        ),
        "construction_stage_instance_v3": (
            CONSTRUCTION_STAGE_INSTANCE_V3_DOMAIN
        ),
        "construction_stage_start_attestation_v3": (
            CONSTRUCTION_STAGE_START_ATTESTATION_V3_DOMAIN
        ),
        "construction_operation_event_v3": (
            CONSTRUCTION_OPERATION_EVENT_V3_DOMAIN
        ),
        "construction_stage_event_transcript_v3": (
            CONSTRUCTION_STAGE_EVENT_TRANSCRIPT_V3_DOMAIN
        ),
        "construction_stage_completion_attestation_v3": (
            CONSTRUCTION_STAGE_COMPLETION_ATTESTATION_V3_DOMAIN
        ),
        "construction_counter_record_v3": (
            CONSTRUCTION_COUNTER_RECORD_V3_DOMAIN
        ),
        "construction_work_vector_v3": (
            CONSTRUCTION_WORK_VECTOR_V3_DOMAIN
        ),
        "construction_comparison_vector_v3": (
            CONSTRUCTION_COMPARISON_VECTOR_V3_DOMAIN
        ),
        "construction_actual_projection_proof_v3": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROOF_V3_DOMAIN
        ),
        "construction_counter_registry_v4": (
            CONSTRUCTION_COUNTER_REGISTRY_V4_DOMAIN
        ),
        "construction_stage_profile_v4": (
            CONSTRUCTION_STAGE_PROFILE_V4_DOMAIN
        ),
        "construction_comparison_profile_v4": (
            CONSTRUCTION_COMPARISON_PROFILE_V4_DOMAIN
        ),
        "construction_actual_projection_profile_v4": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V4_DOMAIN
        ),
        "construction_counter_registry_v5": (
            CONSTRUCTION_COUNTER_REGISTRY_V5_DOMAIN
        ),
        "construction_stage_profile_v5": (
            CONSTRUCTION_STAGE_PROFILE_V5_DOMAIN
        ),
        "construction_comparison_profile_v5": (
            CONSTRUCTION_COMPARISON_PROFILE_V5_DOMAIN
        ),
        "construction_actual_projection_profile_v5": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V5_DOMAIN
        ),
        "construction_counter_registry_v6": (
            CONSTRUCTION_COUNTER_REGISTRY_V6_DOMAIN
        ),
        "construction_stage_profile_v6": (
            CONSTRUCTION_STAGE_PROFILE_V6_DOMAIN
        ),
        "construction_comparison_profile_v6": (
            CONSTRUCTION_COMPARISON_PROFILE_V6_DOMAIN
        ),
        "construction_actual_projection_profile_v6": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V6_DOMAIN
        ),
        "v075_construction_accounting_schema_closure_v2": (
            V075_CONSTRUCTION_ACCOUNTING_SCHEMA_CLOSURE_V2_DOMAIN
        ),
        "v075_construction_accounting_schema_verification_v2": (
            V075_CONSTRUCTION_ACCOUNTING_SCHEMA_VERIFICATION_V2_DOMAIN
        ),
        "v075_construction_accounting_registry_successor_v3": (
            V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_V3_DOMAIN
        ),
        "v075_construction_accounting_registry_successor_verification_v3": (
            V075_CONSTRUCTION_ACCOUNTING_REGISTRY_SUCCESSOR_VERIFICATION_V3_DOMAIN
        ),
        "v075_construction_accounting_operation_ownership_successor_v4": (
            V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_SUCCESSOR_V4_DOMAIN
        ),
        "v075_construction_accounting_operation_ownership_verification_v4": (
            V075_CONSTRUCTION_ACCOUNTING_OPERATION_OWNERSHIP_VERIFICATION_V4_DOMAIN
        ),
        "v075_construction_accounting_known_owner_gap_successor_v5": (
            V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_SUCCESSOR_V5_DOMAIN
        ),
        "v075_construction_accounting_known_owner_gap_verification_v5": (
            V075_CONSTRUCTION_ACCOUNTING_KNOWN_OWNER_GAP_VERIFICATION_V5_DOMAIN
        ),
        "v075_k7_root_cap_operation_site_v1": (
            V075_K7_ROOT_CAP_OPERATION_SITE_V1_DOMAIN
        ),
        "v075_k7_root_cap_operation_site_manifest_v1": (
            V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V1_DOMAIN
        ),
        "v075_k7_root_cap_operation_site_audit_v2": (
            V075_K7_ROOT_CAP_OPERATION_SITE_AUDIT_V2_DOMAIN
        ),
        "v075_k7_root_cap_operation_site_manifest_v2": (
            V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V2_DOMAIN
        ),
        "v075_k7_root_cap_operation_boundary_v3": (
            V075_K7_ROOT_CAP_OPERATION_BOUNDARY_V3_DOMAIN
        ),
        "v075_k7_root_cap_operation_boundary_manifest_v3": (
            V075_K7_ROOT_CAP_OPERATION_BOUNDARY_MANIFEST_V3_DOMAIN
        ),
        "v075_k7_root_cap_cold_cache_profile_v1": (
            V075_K7_ROOT_CAP_COLD_CACHE_PROFILE_V1_DOMAIN
        ),
        "v075_k7_root_cap_cold_cache_epoch_v1": (
            V075_K7_ROOT_CAP_COLD_CACHE_EPOCH_V1_DOMAIN
        ),
        "v075_k7_root_cap_owned_partial_result_v1": (
            V075_K7_ROOT_CAP_OWNED_PARTIAL_RESULT_V1_DOMAIN
        ),
        "v075_k7_root_cap_execution_identity_profile_v1": (
            V075_K7_ROOT_CAP_EXECUTION_IDENTITY_PROFILE_V1_DOMAIN
        ),
        "v075_construction_accounting_operation_boundary_verification_v6": (
            V075_CONSTRUCTION_ACCOUNTING_OPERATION_BOUNDARY_VERIFICATION_V6_DOMAIN
        ),
        "v075_k7_causal_promotion_shared_measurement_v1": (
            V075_K7_CAUSAL_PROMOTION_SHARED_MEASUREMENT_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_runtime_preparation_v1": (
            V075_K7_CAUSAL_PROMOTION_RUNTIME_PREPARATION_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_supervised_request_v1": (
            V075_K7_CAUSAL_PROMOTION_SUPERVISED_REQUEST_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_operational_trace_v1": (
            V075_K7_CAUSAL_PROMOTION_OPERATIONAL_TRACE_V1_DOMAIN
        ),
        "v075_k7_reusable_model_operational_trace_v1": (
            V075_K7_REUSABLE_MODEL_OPERATIONAL_TRACE_V1_DOMAIN
        ),
        "v075_k7_causal_recovery_operational_trace_v1": (
            V075_K7_CAUSAL_RECOVERY_OPERATIONAL_TRACE_V1_DOMAIN
        ),
        "construction_k7_causal_recovery_chain_v1": (
            CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_V1_DOMAIN
        ),
        "construction_k7_causal_recovery_chain_replay_v1": (
            CONSTRUCTION_K7_CAUSAL_RECOVERY_CHAIN_REPLAY_V1_DOMAIN
        ),
        "construction_k7_query_bound_recovery_overlay_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_RECOVERY_OVERLAY_V1_DOMAIN
        ),
        "construction_k7_query_bound_validation_request_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_VALIDATION_REQUEST_V1_DOMAIN
        ),
        "construction_k7_query_bound_recovery_request_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_RECOVERY_REQUEST_V1_DOMAIN
        ),
        "construction_k7_query_bound_namespace_binding_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_NAMESPACE_BINDING_V1_DOMAIN
        ),
        "construction_k7_query_bound_row_execution_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_ROW_EXECUTION_V1_DOMAIN
        ),
        "construction_k7_query_bound_ground_transaction_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_GROUND_TRANSACTION_V1_DOMAIN
        ),
        "construction_k7_query_bound_overlay_replanning_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_OVERLAY_REPLANNING_V1_DOMAIN
        ),
        "construction_k7_query_bound_transaction_2_validation_request_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_VALIDATION_REQUEST_V1_DOMAIN
        ),
        "construction_k7_query_bound_transaction_2_recovery_request_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_RECOVERY_REQUEST_V1_DOMAIN
        ),
        "construction_k7_query_bound_transaction_2_namespace_binding_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_NAMESPACE_BINDING_V1_DOMAIN
        ),
        "construction_k7_query_bound_transaction_2_row_execution_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_ROW_EXECUTION_V1_DOMAIN
        ),
        "construction_k7_query_bound_transaction_2_ground_transaction_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_GROUND_TRANSACTION_V1_DOMAIN
        ),
        "construction_k7_query_bound_final_local_replanning_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_FINAL_LOCAL_REPLANNING_V1_DOMAIN
        ),
        "construction_k7_query_bound_direct_fallback_row_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_ROW_V1_DOMAIN
        ),
        "construction_k7_query_bound_direct_fallback_inventory_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_INVENTORY_V1_DOMAIN
        ),
        "construction_k7_query_bound_direct_fallback_policy_decision_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_POLICY_DECISION_V1_DOMAIN
        ),
        "construction_k7_query_bound_direct_fallback_work_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_WORK_V1_DOMAIN
        ),
        "construction_k7_query_bound_direct_fallback_result_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_RESULT_V1_DOMAIN
        ),
        "construction_k7_query_bound_direct_fallback_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_DIRECT_FALLBACK_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_accounting_boundary_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTING_BOUNDARY_V1_DOMAIN
        ),
        "construction_k7_query_bound_accounting_manifest_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTING_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_query_bound_stage_runtime_result_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_STAGE_RUNTIME_RESULT_V1_DOMAIN
        ),
        "construction_k7_query_bound_accounted_continuation_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTED_CONTINUATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_runtime_preparation_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_RUNTIME_PREPARATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_supervised_request_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_SUPERVISED_REQUEST_V1_DOMAIN
        ),
        "construction_k7_query_bound_operational_trace_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_OPERATIONAL_TRACE_V1_DOMAIN
        ),
        "construction_k7_query_bound_shared_measurement_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_SHARED_MEASUREMENT_V1_DOMAIN
        ),
        "construction_k7_query_bound_shared_receipt_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_SHARED_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_query_bound_shared_receipt_set_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_SHARED_RECEIPT_SET_V1_DOMAIN
        ),
        "construction_k7_query_bound_path_aggregation_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PATH_AGGREGATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_occurrence_accounting_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_OCCURRENCE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_query_bound_output_renderer_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_OUTPUT_RENDERER_V1_DOMAIN
        ),
        "construction_k7_query_bound_output_commit_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_OUTPUT_COMMIT_V1_DOMAIN
        ),
        "construction_k7_query_bound_complete_bundle_verification_profile_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_query_bound_complete_bundle_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_analysis_spec_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_SPEC_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_occurrence_row_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_vector_prefix_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_VECTOR_PREFIX_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_analysis_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_analysis_verification_profile_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_analysis_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ANALYSIS_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_input_blob_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_INPUT_BLOB_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_preregistered_occurrence_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTERED_OCCURRENCE_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_workload_spec_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_WORKLOAD_SPEC_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_preregistration_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_preregistration_verification_profile_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_preregistration_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREREGISTRATION_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_preregistered_campaign_commit_event_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN
        ),
        "construction_k7_query_bound_preregistered_campaign_occurrence_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_OCCURRENCE_V1_DOMAIN
        ),
        "construction_k7_query_bound_preregistered_campaign_result_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_RESULT_V1_DOMAIN
        ),
        "construction_k7_query_bound_preregistered_campaign_verification_profile_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_query_bound_preregistered_campaign_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PREREGISTERED_CAMPAIGN_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_denominator_closure_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_denominator_closure_verification_profile_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_denominator_closure_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_DENOMINATOR_CLOSURE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_failure_closure_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_failure_closure_verification_profile_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_failure_closure_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_FAILURE_CLOSURE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_prefix_failure_closure_v2": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_V2_DOMAIN
        ),
        "construction_k7_query_bound_campaign_prefix_failure_closure_verification_profile_v2": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_VERIFICATION_PROFILE_V2_DOMAIN
        ),
        "construction_k7_query_bound_campaign_prefix_failure_closure_verification_v2": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_PREFIX_FAILURE_CLOSURE_VERIFICATION_V2_DOMAIN
        ),
        "construction_k7_query_bound_campaign_orchestration_accounting_profile_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_orchestration_accounting_profile_verification_profile_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_query_bound_campaign_orchestration_accounting_profile_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_reusable_rapm_snapshot_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SNAPSHOT_V1_DOMAIN
        ),
        "construction_k7_query_bound_reusable_rapm_query_spec_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_SPEC_V1_DOMAIN
        ),
        "construction_k7_query_bound_reusable_rapm_query_result_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_RESULT_V1_DOMAIN
        ),
        "construction_k7_query_bound_reusable_rapm_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_V1_DOMAIN
        ),
        "construction_k7_query_bound_reusable_rapm_source_bundle_binding_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_query_bound_rapm_proof_dependency_node_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_NODE_V1_DOMAIN
        ),
        "construction_k7_query_bound_rapm_proof_partition_result_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_PARTITION_RESULT_V1_DOMAIN
        ),
        "construction_k7_query_bound_rapm_proof_search_result_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_SEARCH_RESULT_V1_DOMAIN
        ),
        "construction_k7_query_bound_rapm_proof_dependency_graph_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_GRAPH_V1_DOMAIN
        ),
        "construction_k7_query_bound_rapm_proof_dependency_transition_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_RAPM_PROOF_DEPENDENCY_TRANSITION_V1_DOMAIN
        ),
        "construction_k7_query_bound_persistent_proof_cache_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PERSISTENT_PROOF_CACHE_V1_DOMAIN
        ),
        "construction_k7_query_bound_proof_cache_query_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_QUERY_V1_DOMAIN
        ),
        "construction_k7_query_bound_proof_cache_consumption_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_CONSUMPTION_V1_DOMAIN
        ),
        "construction_k7_query_bound_proof_cache_no_reuse_control_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PROOF_CACHE_NO_REUSE_CONTROL_V1_DOMAIN
        ),
        "construction_k7_query_bound_persistent_proof_cache_verification_v1": (
            CONSTRUCTION_K7_QUERY_BOUND_PERSISTENT_PROOF_CACHE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_checkpoint_fixture_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_FIXTURE_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_checkpoint_query_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_QUERY_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_checkpoint_consumption_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_CONSUMPTION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_validation_request_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_VALIDATION_REQUEST_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_recovery_request_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RECOVERY_REQUEST_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_namespace_binding_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NAMESPACE_BINDING_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_row_acquisition_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ROW_ACQUISITION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_ground_transaction_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_GROUND_TRANSACTION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_world_model_loop_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_world_model_loop_verification_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_exact_ground_row_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_EXACT_GROUND_ROW_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_fallback_inventory_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_FALLBACK_INVENTORY_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_fallback_policy_decision_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_FALLBACK_POLICY_DECISION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_fallback_work_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_FALLBACK_WORK_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_direct_fallback_result_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_DIRECT_FALLBACK_RESULT_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_direct_fallback_verification_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_DIRECT_FALLBACK_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_accounting_boundary_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ACCOUNTING_BOUNDARY_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_accounting_manifest_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ACCOUNTING_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_stage_accounting_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_STAGE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_native_accounting_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NATIVE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_runtime_preparation_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RUNTIME_PREPARATION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_supervised_request_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SUPERVISED_REQUEST_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_operational_trace_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OPERATIONAL_TRACE_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_shared_measurement_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_MEASUREMENT_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_shared_receipt_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_shared_receipt_set_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_SET_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_path_aggregation_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_PATH_AGGREGATION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_occurrence_accounting_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_output_renderer_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_RENDERER_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_output_commit_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OUTPUT_COMMIT_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_campaign_input_blob_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INPUT_BLOB_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_campaign_occurrence_spec_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_SPEC_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_campaign_workload_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_WORKLOAD_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_campaign_preregistration_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_campaign_commit_event_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_COMMIT_EVENT_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_campaign_occurrence_row_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_campaign_closure_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_campaign_result_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_RESULT_V1_DOMAIN
        ),
        "construction_k7_recovery_eligible_campaign_independent_verification_v1": (
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_recovery_overlay_promoted_epoch_v1": (
            CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_EPOCH_V1_DOMAIN
        ),
        "construction_k7_recovery_overlay_promoted_query_v1": (
            CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_QUERY_V1_DOMAIN
        ),
        "construction_k7_recovery_overlay_promoted_consumption_v1": (
            CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_CONSUMPTION_V1_DOMAIN
        ),
        "construction_k7_recovery_overlay_promotion_result_v1": (
            CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_RESULT_V1_DOMAIN
        ),
        "construction_k7_recovery_overlay_promotion_independent_verification_v1": (
            CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_overlay_epoch_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_EPOCH_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_overlay_query_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_QUERY_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_abstract_plan_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_ABSTRACT_PLAN_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_exact_lift_binding_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_EXACT_LIFT_BINDING_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_overlay_result_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_RESULT_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_overlay_independent_verification_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_OVERLAY_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_stage_accounting_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_STAGE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_shared_measurement_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_MEASUREMENT_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_shared_receipt_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_shared_receipt_set_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_SHARED_RECEIPT_SET_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_path_aggregation_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_PATH_AGGREGATION_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_occurrence_accounting_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_OCCURRENCE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_output_renderer_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_OUTPUT_RENDERER_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_output_commit_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_OUTPUT_COMMIT_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_campaign_preregistration_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_campaign_occurrence_row_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_campaign_closure_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_campaign_result_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_RESULT_V1_DOMAIN
        ),
        "construction_k7_positive_promoted_campaign_independent_verification_v1": (
            CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_checkpoint_preregistration_v1": (
            CONSTRUCTION_K7_HELDOUT_CHECKPOINT_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_heldout_coordinate_checkpoint_v1": (
            CONSTRUCTION_K7_HELDOUT_COORDINATE_CHECKPOINT_V1_DOMAIN
        ),
        "construction_k7_heldout_causal_row_evidence_v1": (
            CONSTRUCTION_K7_HELDOUT_CAUSAL_ROW_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_heldout_recovery_request_v1": (
            CONSTRUCTION_K7_HELDOUT_RECOVERY_REQUEST_V1_DOMAIN
        ),
        "construction_k7_heldout_validation_delta_v1": (
            CONSTRUCTION_K7_HELDOUT_VALIDATION_DELTA_V1_DOMAIN
        ),
        "construction_k7_heldout_overlay_epoch_v1": (
            CONSTRUCTION_K7_HELDOUT_OVERLAY_EPOCH_V1_DOMAIN
        ),
        "construction_k7_heldout_recertification_result_v1": (
            CONSTRUCTION_K7_HELDOUT_RECERTIFICATION_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_overlay_query_v1": (
            CONSTRUCTION_K7_HELDOUT_OVERLAY_QUERY_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_plan_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_reuse_result_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_reuse_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_stage_profile_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_STAGE_PROFILE_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_operation_manifest_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_OPERATION_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_operation_boundary_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_OPERATION_BOUNDARY_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_stage_accounting_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_STAGE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_shared_measurement_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_MEASUREMENT_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_shared_receipt_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_shared_receipt_set_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_SHARED_RECEIPT_SET_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_path_aggregation_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_PATH_AGGREGATION_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_occurrence_accounting_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_OCCURRENCE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_output_renderer_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_OUTPUT_RENDERER_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_output_commit_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_OUTPUT_COMMIT_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_occurrence_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_OCCURRENCE_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_campaign_preregistration_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_campaign_occurrence_row_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_campaign_closure_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_campaign_result_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_abstract_campaign_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_multiquery_campaign_preregistration_v1": (
            CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_heldout_multiquery_campaign_occurrence_row_v1": (
            CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
        ),
        "construction_k7_heldout_multiquery_campaign_closure_v1": (
            CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_heldout_multiquery_campaign_result_v1": (
            CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_multiquery_campaign_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_checkpoint_preregistration_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_CHECKPOINT_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_coordinate_checkpoint_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_COORDINATE_CHECKPOINT_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_causal_row_evidence_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_CAUSAL_ROW_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_recovery_request_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_RECOVERY_REQUEST_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_validation_delta_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_VALIDATION_DELTA_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_overlay_epoch_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_EPOCH_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_recertification_result_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_recertification_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_overlay_query_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_QUERY_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_plan_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_PLAN_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_reuse_result_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_reuse_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_stage_accounting_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_STAGE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_shared_measurement_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_SHARED_MEASUREMENT_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_shared_receipt_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_SHARED_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_shared_receipt_set_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_SHARED_RECEIPT_SET_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_path_aggregation_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_PATH_AGGREGATION_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_occurrence_accounting_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_OCCURRENCE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_output_renderer_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_OUTPUT_RENDERER_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_output_commit_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_OUTPUT_COMMIT_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_campaign_preregistration_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_campaign_occurrence_row_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_campaign_closure_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_campaign_result_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_occurrence_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_OCCURRENCE_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_k6_abstract_campaign_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_cross_structural_campaign_preregistration_v1": (
            CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_heldout_cross_structural_campaign_child_row_v1": (
            CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CHILD_ROW_V1_DOMAIN
        ),
        "construction_k7_heldout_cross_structural_campaign_closure_v1": (
            CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_heldout_cross_structural_campaign_result_v1": (
            CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_cross_structural_campaign_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_heldout_model_catalogue_entry_v1": (
            CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_ENTRY_V1_DOMAIN
        ),
        "construction_k7_heldout_model_catalogue_v1": (
            CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_V1_DOMAIN
        ),
        "construction_k7_heldout_model_selection_v1": (
            CONSTRUCTION_K7_HELDOUT_MODEL_SELECTION_V1_DOMAIN
        ),
        "construction_k7_heldout_catalogue_query_v1": (
            CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_V1_DOMAIN
        ),
        "construction_k7_heldout_catalogue_construction_request_v1": (
            CONSTRUCTION_K7_HELDOUT_CATALOGUE_CONSTRUCTION_REQUEST_V1_DOMAIN
        ),
        "construction_k7_heldout_catalogue_abstract_plan_v1": (
            CONSTRUCTION_K7_HELDOUT_CATALOGUE_ABSTRACT_PLAN_V1_DOMAIN
        ),
        "construction_k7_heldout_catalogue_query_result_v1": (
            CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_catalogue_promotion_preregistration_v1": (
            CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_heldout_catalogue_promotion_event_v1": (
            CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_EVENT_V1_DOMAIN
        ),
        "construction_k7_heldout_catalogue_promotion_closure_v1": (
            CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_heldout_catalogue_promotion_result_v1": (
            CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_RESULT_V1_DOMAIN
        ),
        "construction_k7_heldout_catalogue_promotion_independent_verification_v1": (
            CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_observation_driven_synthesis_dispatch_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_DISPATCH_V1_DOMAIN
        ),
        "construction_k7_observation_driven_synthesis_promotion_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_PROMOTION_V1_DOMAIN
        ),
        "construction_k7_observation_driven_synthesis_unsupported_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_UNSUPPORTED_V1_DOMAIN
        ),
        "construction_k7_observation_driven_synthesis_result_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_RESULT_V1_DOMAIN
        ),
        "construction_k7_observation_driven_campaign_preregistration_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_observation_driven_campaign_occurrence_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_OCCURRENCE_V1_DOMAIN
        ),
        "construction_k7_observation_driven_campaign_closure_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_observation_driven_campaign_result_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_RESULT_V1_DOMAIN
        ),
        "construction_k7_observation_driven_campaign_independent_verification_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_observed_constructor_signature_v1": (
            CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_SIGNATURE_V1_DOMAIN
        ),
        "construction_k7_observed_constructor_candidate_v1": (
            CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_observed_constructor_decision_v1": (
            CONSTRUCTION_K7_OBSERVED_CONSTRUCTOR_DECISION_V1_DOMAIN
        ),
        "construction_k7_observation_driven_synthesis_v2_result_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_V2_RESULT_V1_DOMAIN
        ),
        "construction_k7_observed_program_grammar_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_GRAMMAR_V1_DOMAIN
        ),
        "construction_k7_observed_program_corpus_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_CORPUS_V1_DOMAIN
        ),
        "construction_k7_observed_program_candidate_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_observed_program_proposal_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_PROPOSAL_V1_DOMAIN
        ),
        "construction_k7_observed_program_decision_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_DECISION_V1_DOMAIN
        ),
        "construction_k7_observed_program_heldout_observation_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_OBSERVATION_V1_DOMAIN
        ),
        "construction_k7_observed_program_heldout_preregistration_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_observed_program_heldout_evaluation_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_EVALUATION_V1_DOMAIN
        ),
        "construction_k7_observed_program_heldout_campaign_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_CAMPAIGN_V1_DOMAIN
        ),
        "construction_k7_observed_program_heldout_independent_verification_v1": (
            CONSTRUCTION_K7_OBSERVED_PROGRAM_HELDOUT_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_observation_driven_synthesis_v3_result_v1": (
            CONSTRUCTION_K7_OBSERVATION_DRIVEN_SYNTHESIS_V3_RESULT_V1_DOMAIN
        ),
        "construction_k7_observation_derived_primitive_candidate_v1": (
            CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_observation_derived_primitive_basis_v1": (
            CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_BASIS_V1_DOMAIN
        ),
        "construction_k7_observation_derived_primitive_evaluation_v1": (
            CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_EVALUATION_V1_DOMAIN
        ),
        "construction_k7_observation_derived_primitive_campaign_v1": (
            CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_CAMPAIGN_V1_DOMAIN
        ),
        "construction_k7_observation_derived_primitive_independent_verification_v1": (
            CONSTRUCTION_K7_OBSERVATION_DERIVED_PRIMITIVE_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_basis_heldout_model_transport_v1": (
            CONSTRUCTION_K7_BASIS_HELDOUT_MODEL_TRANSPORT_V1_DOMAIN
        ),
        "construction_k7_basis_heldout_query_preregistration_v1": (
            CONSTRUCTION_K7_BASIS_HELDOUT_QUERY_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_basis_heldout_abstract_plan_v1": (
            CONSTRUCTION_K7_BASIS_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN
        ),
        "construction_k7_basis_heldout_synthesis_campaign_v1": (
            CONSTRUCTION_K7_BASIS_HELDOUT_SYNTHESIS_CAMPAIGN_V1_DOMAIN
        ),
        "construction_k7_basis_heldout_independent_verification_v1": (
            CONSTRUCTION_K7_BASIS_HELDOUT_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_standard_2048_preregistration_v1": (
            CONSTRUCTION_K7_STANDARD_2048_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_standard_2048_quotient_row_v1": (
            CONSTRUCTION_K7_STANDARD_2048_QUOTIENT_ROW_V1_DOMAIN
        ),
        "construction_k7_standard_2048_world_model_v1": (
            CONSTRUCTION_K7_STANDARD_2048_WORLD_MODEL_V1_DOMAIN
        ),
        "construction_k7_standard_2048_model_audit_v1": (
            CONSTRUCTION_K7_STANDARD_2048_MODEL_AUDIT_V1_DOMAIN
        ),
        "construction_k7_standard_2048_abstract_plan_v1": (
            CONSTRUCTION_K7_STANDARD_2048_ABSTRACT_PLAN_V1_DOMAIN
        ),
        "construction_k7_standard_2048_matched_direct_v1": (
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_DIRECT_V1_DOMAIN
        ),
        "construction_k7_standard_2048_receding_campaign_v1": (
            CONSTRUCTION_K7_STANDARD_2048_RECEDING_CAMPAIGN_V1_DOMAIN
        ),
        "construction_k7_standard_2048_independent_verification_v1": (
            CONSTRUCTION_K7_STANDARD_2048_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_standard_2048_statistical_preregistration_v1": (
            CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_standard_2048_spawn_observation_archive_v1": (
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V1_DOMAIN
        ),
        "construction_k7_standard_2048_spawn_interval_v1": (
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_INTERVAL_V1_DOMAIN
        ),
        "construction_k7_standard_2048_partial_row_v1": (
            CONSTRUCTION_K7_STANDARD_2048_PARTIAL_ROW_V1_DOMAIN
        ),
        "construction_k7_standard_2048_partial_model_v1": (
            CONSTRUCTION_K7_STANDARD_2048_PARTIAL_MODEL_V1_DOMAIN
        ),
        "construction_k7_standard_2048_statistical_audit_v1": (
            CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_AUDIT_V1_DOMAIN
        ),
        "construction_k7_standard_2048_robust_plan_v1": (
            CONSTRUCTION_K7_STANDARD_2048_ROBUST_PLAN_V1_DOMAIN
        ),
        "construction_k7_standard_2048_statistical_matched_direct_v1": (
            CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_MATCHED_DIRECT_V1_DOMAIN
        ),
        "construction_k7_standard_2048_statistical_episode_v1": (
            CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_EPISODE_V1_DOMAIN
        ),
        "construction_k7_standard_2048_multiseed_campaign_v1": (
            CONSTRUCTION_K7_STANDARD_2048_MULTISEED_CAMPAIGN_V1_DOMAIN
        ),
        "construction_k7_standard_2048_statistical_independent_verification_v1": (
            CONSTRUCTION_K7_STANDARD_2048_STATISTICAL_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_standard_2048_support_source_archive_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_SOURCE_ARCHIVE_V2_DOMAIN
        ),
        "construction_k7_standard_2048_support_validation_archive_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_VALIDATION_ARCHIVE_V2_DOMAIN
        ),
        "construction_k7_standard_2048_support_proposal_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PROPOSAL_V2_DOMAIN
        ),
        "construction_k7_standard_2048_partial_dynamics_interval_v2": (
            CONSTRUCTION_K7_STANDARD_2048_PARTIAL_DYNAMICS_INTERVAL_V2_DOMAIN
        ),
        "construction_k7_standard_2048_support_preregistration_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PREREGISTRATION_V2_DOMAIN
        ),
        "construction_k7_standard_2048_support_partial_row_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_ROW_V2_DOMAIN
        ),
        "construction_k7_standard_2048_support_partial_model_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_PARTIAL_MODEL_V2_DOMAIN
        ),
        "construction_k7_standard_2048_support_audit_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_AUDIT_V2_DOMAIN
        ),
        "construction_k7_standard_2048_support_robust_plan_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_ROBUST_PLAN_V2_DOMAIN
        ),
        "construction_k7_standard_2048_support_matched_direct_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_MATCHED_DIRECT_V2_DOMAIN
        ),
        "construction_k7_standard_2048_fresh_board_episode_v2": (
            CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_EPISODE_V2_DOMAIN
        ),
        "construction_k7_standard_2048_fresh_board_campaign_v2": (
            CONSTRUCTION_K7_STANDARD_2048_FRESH_BOARD_CAMPAIGN_V2_DOMAIN
        ),
        "construction_k7_standard_2048_support_independent_verification_v2": (
            CONSTRUCTION_K7_STANDARD_2048_SUPPORT_INDEPENDENT_VERIFICATION_V2_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_profile_v3": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_PROFILE_V3_DOMAIN
        ),
        "construction_k7_standard_2048_meta_prior_v3": (
            CONSTRUCTION_K7_STANDARD_2048_META_PRIOR_V3_DOMAIN
        ),
        "construction_k7_standard_2048_acquisition_arm_v3": (
            CONSTRUCTION_K7_STANDARD_2048_ACQUISITION_ARM_V3_DOMAIN
        ),
        "construction_k7_standard_2048_sample_tax_campaign_v3": (
            CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_CAMPAIGN_V3_DOMAIN
        ),
        "construction_k7_standard_2048_sample_tax_verification_v3": (
            CONSTRUCTION_K7_STANDARD_2048_SAMPLE_TAX_VERIFICATION_V3_DOMAIN
        ),
        "construction_k7_standard_2048_affine_meta_prior_v4": (
            CONSTRUCTION_K7_STANDARD_2048_AFFINE_META_PRIOR_V4_DOMAIN
        ),
        "construction_k7_standard_2048_affine_certificate_v4": (
            CONSTRUCTION_K7_STANDARD_2048_AFFINE_CERTIFICATE_V4_DOMAIN
        ),
        "construction_k7_standard_2048_affine_route_decision_v4": (
            CONSTRUCTION_K7_STANDARD_2048_AFFINE_ROUTE_DECISION_V4_DOMAIN
        ),
        "construction_k7_standard_2048_affine_long_episode_v4": (
            CONSTRUCTION_K7_STANDARD_2048_AFFINE_LONG_EPISODE_V4_DOMAIN
        ),
        "construction_k7_standard_2048_affine_campaign_v4": (
            CONSTRUCTION_K7_STANDARD_2048_AFFINE_CAMPAIGN_V4_DOMAIN
        ),
        "construction_k7_standard_2048_affine_verification_v4": (
            CONSTRUCTION_K7_STANDARD_2048_AFFINE_VERIFICATION_V4_DOMAIN
        ),
        "construction_k7_standard_2048_exchangeability_preregistration_v5": (
            CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_PREREGISTRATION_V5_DOMAIN
        ),
        "construction_k7_standard_2048_exchangeability_certificate_v5": (
            CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_CERTIFICATE_V5_DOMAIN
        ),
        "construction_k7_standard_2048_exchangeability_route_decision_v5": (
            CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_ROUTE_DECISION_V5_DOMAIN
        ),
        "construction_k7_standard_2048_exchangeability_episode_v5": (
            CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_EPISODE_V5_DOMAIN
        ),
        "construction_k7_standard_2048_exchangeability_campaign_v5": (
            CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_CAMPAIGN_V5_DOMAIN
        ),
        "construction_k7_standard_2048_exchangeability_verification_v5": (
            CONSTRUCTION_K7_STANDARD_2048_EXCHANGEABILITY_VERIFICATION_V5_DOMAIN
        ),
        "construction_k7_standard_2048_frontier_acquisition_preregistration_v6": (
            CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_PREREGISTRATION_V6_DOMAIN
        ),
        "construction_k7_standard_2048_frontier_acquisition_certificate_v6": (
            CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_CERTIFICATE_V6_DOMAIN
        ),
        "construction_k7_standard_2048_frontier_acquisition_route_decision_v6": (
            CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_ROUTE_DECISION_V6_DOMAIN
        ),
        "construction_k7_standard_2048_frontier_acquisition_episode_v6": (
            CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_EPISODE_V6_DOMAIN
        ),
        "construction_k7_standard_2048_frontier_acquisition_campaign_v6": (
            CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_CAMPAIGN_V6_DOMAIN
        ),
        "construction_k7_standard_2048_frontier_acquisition_verification_v6": (
            CONSTRUCTION_K7_STANDARD_2048_FRONTIER_ACQUISITION_VERIFICATION_V6_DOMAIN
        ),
        "construction_k7_standard_2048_targeted_source_archive_v7": (
            CONSTRUCTION_K7_STANDARD_2048_TARGETED_SOURCE_ARCHIVE_V7_DOMAIN
        ),
        "construction_k7_standard_2048_targeted_validation_archive_v7": (
            CONSTRUCTION_K7_STANDARD_2048_TARGETED_VALIDATION_ARCHIVE_V7_DOMAIN
        ),
        "construction_k7_standard_2048_targeted_preregistration_v7": (
            CONSTRUCTION_K7_STANDARD_2048_TARGETED_PREREGISTRATION_V7_DOMAIN
        ),
        "construction_k7_standard_2048_targeted_certificate_v7": (
            CONSTRUCTION_K7_STANDARD_2048_TARGETED_CERTIFICATE_V7_DOMAIN
        ),
        "construction_k7_standard_2048_targeted_route_decision_v7": (
            CONSTRUCTION_K7_STANDARD_2048_TARGETED_ROUTE_DECISION_V7_DOMAIN
        ),
        "construction_k7_standard_2048_targeted_episode_v7": (
            CONSTRUCTION_K7_STANDARD_2048_TARGETED_EPISODE_V7_DOMAIN
        ),
        "construction_k7_standard_2048_targeted_campaign_v7": (
            CONSTRUCTION_K7_STANDARD_2048_TARGETED_CAMPAIGN_V7_DOMAIN
        ),
        "construction_k7_standard_2048_targeted_verification_v7": (
            CONSTRUCTION_K7_STANDARD_2048_TARGETED_VERIFICATION_V7_DOMAIN
        ),
        "construction_k7_standard_2048_h3_reuse_preregistration_v8": (
            CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_PREREGISTRATION_V8_DOMAIN
        ),
        "construction_k7_standard_2048_h3_targeted_interval_binding_v8": (
            CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_INTERVAL_BINDING_V8_DOMAIN
        ),
        "construction_k7_standard_2048_h3_targeted_support_proposal_v8": (
            CONSTRUCTION_K7_STANDARD_2048_H3_TARGETED_SUPPORT_PROPOSAL_V8_DOMAIN
        ),
        "construction_k7_standard_2048_h3_reuse_episode_v8": (
            CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_EPISODE_V8_DOMAIN
        ),
        "construction_k7_standard_2048_h3_reuse_campaign_v8": (
            CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_CAMPAIGN_V8_DOMAIN
        ),
        "construction_k7_standard_2048_h3_reuse_verification_v8": (
            CONSTRUCTION_K7_STANDARD_2048_H3_REUSE_VERIFICATION_V8_DOMAIN
        ),
        "construction_k7_standard_2048_factored_preregistration_v9": (
            CONSTRUCTION_K7_STANDARD_2048_FACTORED_PREREGISTRATION_V9_DOMAIN
        ),
        "construction_k7_standard_2048_factored_operator_v9": (
            CONSTRUCTION_K7_STANDARD_2048_FACTORED_OPERATOR_V9_DOMAIN
        ),
        "construction_k7_standard_2048_factored_episode_v9": (
            CONSTRUCTION_K7_STANDARD_2048_FACTORED_EPISODE_V9_DOMAIN
        ),
        "construction_k7_standard_2048_factored_campaign_v9": (
            CONSTRUCTION_K7_STANDARD_2048_FACTORED_CAMPAIGN_V9_DOMAIN
        ),
        "construction_k7_standard_2048_factored_verification_v9": (
            CONSTRUCTION_K7_STANDARD_2048_FACTORED_VERIFICATION_V9_DOMAIN
        ),
        "construction_k7_standard_2048_meta_route_preregistration_v10": (
            CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_PREREGISTRATION_V10_DOMAIN
        ),
        "construction_k7_standard_2048_meta_route_operator_v10": (
            CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_OPERATOR_V10_DOMAIN
        ),
        "construction_k7_standard_2048_meta_route_certificate_v10": (
            CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_CERTIFICATE_V10_DOMAIN
        ),
        "construction_k7_standard_2048_meta_route_episode_v10": (
            CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_EPISODE_V10_DOMAIN
        ),
        "construction_k7_standard_2048_meta_route_campaign_v10": (
            CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_CAMPAIGN_V10_DOMAIN
        ),
        "construction_k7_standard_2048_meta_route_verification_v10": (
            CONSTRUCTION_K7_STANDARD_2048_META_ROUTE_VERIFICATION_V10_DOMAIN
        ),
        "construction_k7_standard_2048_long_preregistration_v11": (
            CONSTRUCTION_K7_STANDARD_2048_LONG_PREREGISTRATION_V11_DOMAIN
        ),
        "construction_k7_standard_2048_long_dynamics_identity_v11": (
            CONSTRUCTION_K7_STANDARD_2048_LONG_DYNAMICS_IDENTITY_V11_DOMAIN
        ),
        "construction_k7_standard_2048_long_operator_binding_v11": (
            CONSTRUCTION_K7_STANDARD_2048_LONG_OPERATOR_BINDING_V11_DOMAIN
        ),
        "construction_k7_standard_2048_long_certificate_v11": (
            CONSTRUCTION_K7_STANDARD_2048_LONG_CERTIFICATE_V11_DOMAIN
        ),
        "construction_k7_standard_2048_long_episode_v11": (
            CONSTRUCTION_K7_STANDARD_2048_LONG_EPISODE_V11_DOMAIN
        ),
        "construction_k7_standard_2048_long_no_transfer_v11": (
            CONSTRUCTION_K7_STANDARD_2048_LONG_NO_TRANSFER_V11_DOMAIN
        ),
        "construction_k7_standard_2048_long_campaign_v11": (
            CONSTRUCTION_K7_STANDARD_2048_LONG_CAMPAIGN_V11_DOMAIN
        ),
        "construction_k7_standard_2048_long_verification_v11": (
            CONSTRUCTION_K7_STANDARD_2048_LONG_VERIFICATION_V11_DOMAIN
        ),
        "construction_k7_standard_2048_accounted_preregistration_v12": (
            CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_PREREGISTRATION_V12_DOMAIN
        ),
        "construction_k7_standard_2048_accounted_measurement_v12": (
            CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_MEASUREMENT_V12_DOMAIN
        ),
        "construction_k7_standard_2048_accounted_counter_bundle_v12": (
            CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_COUNTER_BUNDLE_V12_DOMAIN
        ),
        "construction_k7_standard_2048_accounted_decision_v12": (
            CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_DECISION_V12_DOMAIN
        ),
        "construction_k7_standard_2048_accounted_episode_v12": (
            CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_EPISODE_V12_DOMAIN
        ),
        "construction_k7_standard_2048_accounted_campaign_v12": (
            CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_CAMPAIGN_V12_DOMAIN
        ),
        "construction_k7_standard_2048_accounted_verification_v12": (
            CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_VERIFICATION_V12_DOMAIN
        ),
        "construction_k7_standard_2048_accounted_output_renderer_v12": (
            CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_OUTPUT_RENDERER_V12_DOMAIN
        ),
        "construction_k7_standard_2048_accounted_output_commit_v12": (
            CONSTRUCTION_K7_STANDARD_2048_ACCOUNTED_OUTPUT_COMMIT_V12_DOMAIN
        ),
        "construction_k7_standard_2048_coordinate_preregistration_v13": (
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_PREREGISTRATION_V13_DOMAIN
        ),
        "construction_k7_standard_2048_coordinate_candidate_v13": (
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CANDIDATE_V13_DOMAIN
        ),
        "construction_k7_standard_2048_coordinate_observation_archive_v13": (
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_OBSERVATION_ARCHIVE_V13_DOMAIN
        ),
        "construction_k7_standard_2048_coordinate_basis_v13": (
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_BASIS_V13_DOMAIN
        ),
        "construction_k7_standard_2048_partial_quotient_model_v13": (
            CONSTRUCTION_K7_STANDARD_2048_PARTIAL_QUOTIENT_MODEL_V13_DOMAIN
        ),
        "construction_k7_standard_2048_coordinate_campaign_v13": (
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_CAMPAIGN_V13_DOMAIN
        ),
        "construction_k7_standard_2048_coordinate_decision_v13": (
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_DECISION_V13_DOMAIN
        ),
        "construction_k7_standard_2048_coordinate_verification_v13": (
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_VERIFICATION_V13_DOMAIN
        ),
        "construction_k7_standard_2048_program_preregistration_v14": (
            CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PREREGISTRATION_V14_DOMAIN
        ),
        "construction_k7_standard_2048_program_candidate_v14": (
            CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CANDIDATE_V14_DOMAIN
        ),
        "construction_k7_standard_2048_program_proposal_v14": (
            CONSTRUCTION_K7_STANDARD_2048_PROGRAM_PROPOSAL_V14_DOMAIN
        ),
        "construction_k7_standard_2048_program_line_proof_v14": (
            CONSTRUCTION_K7_STANDARD_2048_PROGRAM_LINE_PROOF_V14_DOMAIN
        ),
        "construction_k7_standard_2048_factored_world_model_v14": (
            CONSTRUCTION_K7_STANDARD_2048_FACTORED_WORLD_MODEL_V14_DOMAIN
        ),
        "construction_k7_standard_2048_program_campaign_v14": (
            CONSTRUCTION_K7_STANDARD_2048_PROGRAM_CAMPAIGN_V14_DOMAIN
        ),
        "construction_k7_standard_2048_program_verification_v14": (
            CONSTRUCTION_K7_STANDARD_2048_PROGRAM_VERIFICATION_V14_DOMAIN
        ),
        "construction_k7_standard_2048_exact_factor_preregistration_v15": (
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_PREREGISTRATION_V15_DOMAIN
        ),
        "construction_k7_standard_2048_exact_factor_source_closure_v15": (
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_SOURCE_CLOSURE_V15_DOMAIN
        ),
        "construction_k7_standard_2048_exact_factor_certificate_v15": (
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CERTIFICATE_V15_DOMAIN
        ),
        "construction_k7_standard_2048_exact_factor_episode_v15": (
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_EPISODE_V15_DOMAIN
        ),
        "construction_k7_standard_2048_exact_factor_campaign_v15": (
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CAMPAIGN_V15_DOMAIN
        ),
        "construction_k7_standard_2048_exact_factor_verification_v15": (
            CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_VERIFICATION_V15_DOMAIN
        ),
        "construction_k7_standard_2048_spawn_program_preregistration_v16": (
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PREREGISTRATION_V16_DOMAIN
        ),
        "construction_k7_standard_2048_spawn_program_candidate_v16": (
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CANDIDATE_V16_DOMAIN
        ),
        "construction_k7_standard_2048_spawn_observation_archive_v16": (
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_OBSERVATION_ARCHIVE_V16_DOMAIN
        ),
        "construction_k7_standard_2048_spawn_program_proposal_v16": (
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_PROPOSAL_V16_DOMAIN
        ),
        "construction_k7_standard_2048_spawn_program_support_proof_v16": (
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_SUPPORT_PROOF_V16_DOMAIN
        ),
        "construction_k7_standard_2048_synthesized_world_model_v16": (
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_WORLD_MODEL_V16_DOMAIN
        ),
        "construction_k7_standard_2048_spawn_program_campaign_v16": (
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_CAMPAIGN_V16_DOMAIN
        ),
        "construction_k7_standard_2048_spawn_program_verification_v16": (
            CONSTRUCTION_K7_STANDARD_2048_SPAWN_PROGRAM_VERIFICATION_V16_DOMAIN
        ),
        "construction_k7_standard_2048_synthesized_plan_preregistration_v17": (
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_PREREGISTRATION_V17_DOMAIN
        ),
        "construction_k7_standard_2048_synthesized_plan_certificate_v17": (
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CERTIFICATE_V17_DOMAIN
        ),
        "construction_k7_standard_2048_synthesized_plan_episode_v17": (
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_EPISODE_V17_DOMAIN
        ),
        "construction_k7_standard_2048_synthesized_plan_campaign_v17": (
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_CAMPAIGN_V17_DOMAIN
        ),
        "construction_k7_standard_2048_synthesized_plan_verification_v17": (
            CONSTRUCTION_K7_STANDARD_2048_SYNTHESIZED_PLAN_VERIFICATION_V17_DOMAIN
        ),
        "construction_k7_standard_2048_local_repair_kernel_v18": (
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_KERNEL_V18_DOMAIN
        ),
        "construction_k7_standard_2048_local_repair_preregistration_v18": (
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_PREREGISTRATION_V18_DOMAIN
        ),
        "construction_k7_standard_2048_local_repair_failure_v18": (
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_FAILURE_V18_DOMAIN
        ),
        "construction_k7_standard_2048_local_repair_acquisition_v18": (
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_ACQUISITION_V18_DOMAIN
        ),
        "construction_k7_standard_2048_local_repair_overlay_v18": (
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_OVERLAY_V18_DOMAIN
        ),
        "construction_k7_standard_2048_local_repair_certificate_v18": (
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CERTIFICATE_V18_DOMAIN
        ),
        "construction_k7_standard_2048_local_repair_episode_v18": (
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_EPISODE_V18_DOMAIN
        ),
        "construction_k7_standard_2048_local_repair_campaign_v18": (
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_CAMPAIGN_V18_DOMAIN
        ),
        "construction_k7_standard_2048_local_repair_verification_v18": (
            CONSTRUCTION_K7_STANDARD_2048_LOCAL_REPAIR_VERIFICATION_V18_DOMAIN
        ),
        "construction_k7_standard_2048_matched_repair_preregistration_v19": (
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_PREREGISTRATION_V19_DOMAIN
        ),
        "construction_k7_standard_2048_matched_repair_failure_v19": (
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_FAILURE_V19_DOMAIN
        ),
        "construction_k7_standard_2048_matched_repair_acquisition_v19": (
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_ACQUISITION_V19_DOMAIN
        ),
        "construction_k7_standard_2048_matched_repair_overlay_v19": (
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_OVERLAY_V19_DOMAIN
        ),
        "construction_k7_standard_2048_matched_repair_certificate_v19": (
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CERTIFICATE_V19_DOMAIN
        ),
        "construction_k7_standard_2048_matched_repair_episode_v19": (
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_EPISODE_V19_DOMAIN
        ),
        "construction_k7_standard_2048_matched_repair_campaign_v19": (
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_CAMPAIGN_V19_DOMAIN
        ),
        "construction_k7_standard_2048_matched_repair_verification_v19": (
            CONSTRUCTION_K7_STANDARD_2048_MATCHED_REPAIR_VERIFICATION_V19_DOMAIN
        ),
        "construction_k7_standard_2048_context_program_preregistration_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PREREGISTRATION_V20_DOMAIN
        ),
        "construction_k7_standard_2048_context_observation_archive_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_OBSERVATION_ARCHIVE_V20_DOMAIN
        ),
        "construction_k7_standard_2048_context_program_candidate_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CANDIDATE_V20_DOMAIN
        ),
        "construction_k7_standard_2048_context_program_proposal_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROPOSAL_V20_DOMAIN
        ),
        "construction_k7_standard_2048_context_program_proof_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_PROOF_V20_DOMAIN
        ),
        "construction_k7_standard_2048_context_world_model_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_WORLD_MODEL_V20_DOMAIN
        ),
        "construction_k7_standard_2048_context_plan_certificate_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PLAN_CERTIFICATE_V20_DOMAIN
        ),
        "construction_k7_standard_2048_context_program_episode_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_EPISODE_V20_DOMAIN
        ),
        "construction_k7_standard_2048_context_program_campaign_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_CAMPAIGN_V20_DOMAIN
        ),
        "construction_k7_standard_2048_context_program_verification_v20": (
            CONSTRUCTION_K7_STANDARD_2048_CONTEXT_PROGRAM_VERIFICATION_V20_DOMAIN
        ),
        "construction_k7_standard_2048_expression_program_preregistration_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROGRAM_PREREGISTRATION_V21_DOMAIN
        ),
        "construction_k7_standard_2048_structural_context_pool_v21": (
            CONSTRUCTION_K7_STANDARD_2048_STRUCTURAL_CONTEXT_POOL_V21_DOMAIN
        ),
        "construction_k7_standard_2048_expression_candidate_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CANDIDATE_V21_DOMAIN
        ),
        "construction_k7_standard_2048_expression_acquisition_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACQUISITION_V21_DOMAIN
        ),
        "construction_k7_standard_2048_expression_proposal_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROPOSAL_V21_DOMAIN
        ),
        "construction_k7_standard_2048_expression_proof_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PROOF_V21_DOMAIN
        ),
        "construction_k7_standard_2048_expression_world_model_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_WORLD_MODEL_V21_DOMAIN
        ),
        "construction_k7_standard_2048_expression_plan_certificate_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_PLAN_CERTIFICATE_V21_DOMAIN
        ),
        "construction_k7_standard_2048_expression_episode_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_EPISODE_V21_DOMAIN
        ),
        "construction_k7_standard_2048_expression_campaign_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CAMPAIGN_V21_DOMAIN
        ),
        "construction_k7_standard_2048_expression_verification_v21": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_VERIFICATION_V21_DOMAIN
        ),
        "construction_k7_standard_2048_commit_reveal_target_kernel_v22": (
            CONSTRUCTION_K7_STANDARD_2048_COMMIT_REVEAL_TARGET_KERNEL_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_preregistration_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PREREGISTRATION_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_structural_pool_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_STRUCTURAL_POOL_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_candidate_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CANDIDATE_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_acquisition_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_ACQUISITION_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_proposal_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROPOSAL_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_proof_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_PROOF_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_world_model_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_WORLD_MODEL_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_certificate_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CERTIFICATE_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_episode_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_EPISODE_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_campaign_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_CAMPAIGN_V22_DOMAIN
        ),
        "construction_k7_standard_2048_blind_expression_verification_v22": (
            CONSTRUCTION_K7_STANDARD_2048_BLIND_EXPRESSION_VERIFICATION_V22_DOMAIN
        ),
        "construction_k7_standard_2048_expression_long_preregistration_v23": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_PREREGISTRATION_V23_DOMAIN
        ),
        "construction_k7_standard_2048_expression_long_source_binding_v23": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_SOURCE_BINDING_V23_DOMAIN
        ),
        "construction_k7_standard_2048_expression_long_certificate_v23": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CERTIFICATE_V23_DOMAIN
        ),
        "construction_k7_standard_2048_expression_long_episode_v23": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_EPISODE_V23_DOMAIN
        ),
        "construction_k7_standard_2048_expression_long_campaign_v23": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_CAMPAIGN_V23_DOMAIN
        ),
        "construction_k7_standard_2048_expression_long_verification_v23": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_LONG_VERIFICATION_V23_DOMAIN
        ),
        "construction_k7_standard_2048_expression_accounted_preregistration_v24": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_PREREGISTRATION_V24_DOMAIN
        ),
        "construction_k7_standard_2048_expression_accounted_measurement_v24": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_MEASUREMENT_V24_DOMAIN
        ),
        "construction_k7_standard_2048_expression_accounted_counter_bundle_v24": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_COUNTER_BUNDLE_V24_DOMAIN
        ),
        "construction_k7_standard_2048_expression_accounted_decision_v24": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_DECISION_V24_DOMAIN
        ),
        "construction_k7_standard_2048_expression_accounted_episode_v24": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_EPISODE_V24_DOMAIN
        ),
        "construction_k7_standard_2048_expression_accounted_campaign_v24": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_CAMPAIGN_V24_DOMAIN
        ),
        "construction_k7_standard_2048_expression_accounted_verification_v24": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_VERIFICATION_V24_DOMAIN
        ),
        "construction_k7_standard_2048_expression_accounted_semantic_verification_v25": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_ACCOUNTED_SEMANTIC_VERIFICATION_V25_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_preregistration_v26": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V26_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_certificate_v26": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V26_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_episode_v26": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V26_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_campaign_v26": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V26_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_verification_v26": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V26_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_preregistration_v27": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V27_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_certificate_v27": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V27_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_episode_v27": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V27_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_campaign_v27": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V27_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_verification_v27": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V27_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_preregistration_v28": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V28_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_certificate_v28": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V28_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_episode_v28": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V28_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_campaign_v28": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V28_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_verification_v28": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V28_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_preregistration_v29": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V29_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_certificate_v29": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V29_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_episode_v29": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V29_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_campaign_v29": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V29_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_verification_v29": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V29_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_preregistration_v30": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V30_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_certificate_v30": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V30_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_episode_v30": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V30_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_campaign_v30": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V30_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_verification_v30": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V30_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_preregistration_v31": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V31_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_certificate_v31": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V31_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_episode_v31": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V31_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_campaign_v31": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V31_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_verification_v31": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V31_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_preregistration_v32": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V32_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_certificate_v32": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V32_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_episode_v32": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V32_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_campaign_v32": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V32_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_verification_v32": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V32_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_preregistration_v33": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_PREREGISTRATION_V33_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_certificate_v33": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CERTIFICATE_V33_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_episode_v33": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_EPISODE_V33_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_campaign_v33": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_CAMPAIGN_V33_DOMAIN
        ),
        "construction_k7_standard_2048_expression_checkpoint_verification_v33": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_CHECKPOINT_VERIFICATION_V33_DOMAIN
        ),
        "construction_k7_standard_2048_expression_full_accounting_preregistration_v34": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_PREREGISTRATION_V34_DOMAIN
        ),
        "construction_k7_standard_2048_expression_full_accounting_measurement_v34": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_MEASUREMENT_V34_DOMAIN
        ),
        "construction_k7_standard_2048_expression_full_accounting_counter_bundle_v34": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_COUNTER_BUNDLE_V34_DOMAIN
        ),
        "construction_k7_standard_2048_expression_full_accounting_segment_v34": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_SEGMENT_V34_DOMAIN
        ),
        "construction_k7_standard_2048_expression_full_accounting_episode_v34": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_EPISODE_V34_DOMAIN
        ),
        "construction_k7_standard_2048_expression_full_accounting_campaign_v34": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_CAMPAIGN_V34_DOMAIN
        ),
        "construction_k7_standard_2048_expression_full_accounting_verification_v34": (
            CONSTRUCTION_K7_STANDARD_2048_EXPRESSION_FULL_ACCOUNTING_VERIFICATION_V34_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_target_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_TARGET_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_preregistration_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PREREGISTRATION_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_failure_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_FAILURE_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_acquisition_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_ACQUISITION_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_candidate_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CANDIDATE_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_overlay_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_OVERLAY_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_certificate_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CERTIFICATE_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_ground_control_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_GROUND_CONTROL_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_episode_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_EPISODE_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_counter_bundle_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_COUNTER_BUNDLE_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_campaign_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_CAMPAIGN_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_verification_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_VERIFICATION_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_proposal_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROPOSAL_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_expression_proof_v35": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_EXPRESSION_PROOF_V35_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_accounting_preregistration_v36": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V36_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_accounting_measurement_v36": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_MEASUREMENT_V36_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_accounting_counter_bundle_v36": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_COUNTER_BUNDLE_V36_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_accounting_campaign_v36": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_CAMPAIGN_V36_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_accounting_verification_v36": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_ACCOUNTING_VERIFICATION_V36_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_preregistration_v37": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V37_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_certificate_v37": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V37_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_episode_v37": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V37_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_campaign_v37": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V37_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_verification_v37": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V37_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_preregistration_v38": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V38_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_certificate_v38": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V38_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_episode_v38": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V38_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_campaign_v38": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V38_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_verification_v38": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V38_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_preregistration_v39": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V39_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_certificate_v39": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V39_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_episode_v39": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V39_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_campaign_v39": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V39_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_verification_v39": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V39_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_preregistration_v40": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V40_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_certificate_v40": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V40_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_episode_v40": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V40_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_campaign_v40": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V40_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_verification_v40": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V40_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_preregistration_v41": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_PREREGISTRATION_V41_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_certificate_v41": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CERTIFICATE_V41_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_episode_v41": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_EPISODE_V41_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_campaign_v41": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_CAMPAIGN_V41_DOMAIN
        ),
        "construction_k7_standard_2048_adaptive_checkpoint_verification_v41": (
            CONSTRUCTION_K7_STANDARD_2048_ADAPTIVE_CHECKPOINT_VERIFICATION_V41_DOMAIN
        ),
        "construction_k7_lmb_reusable_world_model_preregistration_v42": (
            CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_PREREGISTRATION_V42_DOMAIN
        ),
        "construction_k7_lmb_reusable_primitive_proposal_v42": (
            CONSTRUCTION_K7_LMB_REUSABLE_PRIMITIVE_PROPOSAL_V42_DOMAIN
        ),
        "construction_k7_lmb_local_ground_distinction_v42": (
            CONSTRUCTION_K7_LMB_LOCAL_GROUND_DISTINCTION_V42_DOMAIN
        ),
        "construction_k7_lmb_receding_episode_v42": (
            CONSTRUCTION_K7_LMB_RECEDING_EPISODE_V42_DOMAIN
        ),
        "construction_k7_lmb_reusable_world_model_campaign_v42": (
            CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_CAMPAIGN_V42_DOMAIN
        ),
        "construction_k7_lmb_reusable_world_model_verification_v42": (
            CONSTRUCTION_K7_LMB_REUSABLE_WORLD_MODEL_VERIFICATION_V42_DOMAIN
        ),
        "construction_k7_lmb_witness_blind_preregistration_v43": (
            CONSTRUCTION_K7_LMB_WITNESS_BLIND_PREREGISTRATION_V43_DOMAIN
        ),
        "construction_k7_lmb_witness_blind_proposal_v43": (
            CONSTRUCTION_K7_LMB_WITNESS_BLIND_PROPOSAL_V43_DOMAIN
        ),
        "construction_k7_lmb_witness_blind_distinction_v43": (
            CONSTRUCTION_K7_LMB_WITNESS_BLIND_DISTINCTION_V43_DOMAIN
        ),
        "construction_k7_lmb_cross_cardinality_episode_v43": (
            CONSTRUCTION_K7_LMB_CROSS_CARDINALITY_EPISODE_V43_DOMAIN
        ),
        "construction_k7_lmb_witness_blind_campaign_v43": (
            CONSTRUCTION_K7_LMB_WITNESS_BLIND_CAMPAIGN_V43_DOMAIN
        ),
        "construction_k7_lmb_witness_blind_verification_v43": (
            CONSTRUCTION_K7_LMB_WITNESS_BLIND_VERIFICATION_V43_DOMAIN
        ),
        "construction_k7_lmb_difference_grammar_preregistration_v44": (
            CONSTRUCTION_K7_LMB_DIFFERENCE_GRAMMAR_PREREGISTRATION_V44_DOMAIN
        ),
        "construction_k7_lmb_raw_transition_observation_v44": (
            CONSTRUCTION_K7_LMB_RAW_TRANSITION_OBSERVATION_V44_DOMAIN
        ),
        "construction_k7_lmb_derived_transition_program_v44": (
            CONSTRUCTION_K7_LMB_DERIVED_TRANSITION_PROGRAM_V44_DOMAIN
        ),
        "construction_k7_lmb_derived_program_distinction_v44": (
            CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_DISTINCTION_V44_DOMAIN
        ),
        "construction_k7_lmb_derived_program_episode_v44": (
            CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_EPISODE_V44_DOMAIN
        ),
        "construction_k7_lmb_derived_program_campaign_v44": (
            CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_CAMPAIGN_V44_DOMAIN
        ),
        "construction_k7_lmb_derived_program_verification_v44": (
            CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_VERIFICATION_V44_DOMAIN
        ),
        "construction_k7_lmb_difference_grammar_successor_preregistration_v44r1": (
            CONSTRUCTION_K7_LMB_DIFFERENCE_GRAMMAR_SUCCESSOR_PREREGISTRATION_V44R1_DOMAIN
        ),
        "construction_k7_lmb_model_derived_source_observation_v44r1": (
            CONSTRUCTION_K7_LMB_MODEL_DERIVED_SOURCE_OBSERVATION_V44R1_DOMAIN
        ),
        "construction_k7_lmb_derived_transition_program_v44r1": (
            CONSTRUCTION_K7_LMB_DERIVED_TRANSITION_PROGRAM_V44R1_DOMAIN
        ),
        "construction_k7_lmb_derived_program_distinction_v44r1": (
            CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_DISTINCTION_V44R1_DOMAIN
        ),
        "construction_k7_lmb_derived_program_episode_v44r1": (
            CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_EPISODE_V44R1_DOMAIN
        ),
        "construction_k7_lmb_derived_program_campaign_v44r1": (
            CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_CAMPAIGN_V44R1_DOMAIN
        ),
        "construction_k7_lmb_derived_program_verification_v44r1": (
            CONSTRUCTION_K7_LMB_DERIVED_PROGRAM_VERIFICATION_V44R1_DOMAIN
        ),
        "construction_k7_lmb_anonymous_descriptor_preregistration_v45": (
            CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_PREREGISTRATION_V45_DOMAIN
        ),
        "construction_k7_lmb_anonymous_descriptor_observation_v45": (
            CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_OBSERVATION_V45_DOMAIN
        ),
        "construction_k7_lmb_anonymous_descriptor_program_v45": (
            CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_PROGRAM_V45_DOMAIN
        ),
        "construction_k7_lmb_dependency_derived_distinction_v45": (
            CONSTRUCTION_K7_LMB_DEPENDENCY_DERIVED_DISTINCTION_V45_DOMAIN
        ),
        "construction_k7_lmb_anonymous_descriptor_episode_v45": (
            CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_EPISODE_V45_DOMAIN
        ),
        "construction_k7_lmb_anonymous_descriptor_campaign_v45": (
            CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_CAMPAIGN_V45_DOMAIN
        ),
        "construction_k7_lmb_anonymous_descriptor_verification_v45": (
            CONSTRUCTION_K7_LMB_ANONYMOUS_DESCRIPTOR_VERIFICATION_V45_DOMAIN
        ),
        "construction_k7_lmb_opaque_column_preregistration_v46": (
            CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_PREREGISTRATION_V46_DOMAIN
        ),
        "construction_k7_lmb_opaque_column_observation_v46": (
            CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_OBSERVATION_V46_DOMAIN
        ),
        "construction_k7_lmb_column_factorization_v46": (
            CONSTRUCTION_K7_LMB_COLUMN_FACTORIZATION_V46_DOMAIN
        ),
        "construction_k7_lmb_relation_program_v46": (
            CONSTRUCTION_K7_LMB_RELATION_PROGRAM_V46_DOMAIN
        ),
        "construction_k7_lmb_factorized_distinction_v46": (
            CONSTRUCTION_K7_LMB_FACTORIZED_DISTINCTION_V46_DOMAIN
        ),
        "construction_k7_lmb_factorized_episode_v46": (
            CONSTRUCTION_K7_LMB_FACTORIZED_EPISODE_V46_DOMAIN
        ),
        "construction_k7_lmb_opaque_schema_ood_rejection_v46": (
            CONSTRUCTION_K7_LMB_OPAQUE_SCHEMA_OOD_REJECTION_V46_DOMAIN
        ),
        "construction_k7_lmb_opaque_column_campaign_v46": (
            CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_CAMPAIGN_V46_DOMAIN
        ),
        "construction_k7_lmb_opaque_column_verification_v46": (
            CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_VERIFICATION_V46_DOMAIN
        ),
        "construction_k7_lmb_opaque_column_successor_preregistration_v46r1": (
            CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_SUCCESSOR_PREREGISTRATION_V46R1_DOMAIN
        ),
        "construction_k7_lmb_opaque_column_observation_v46r1": (
            CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_OBSERVATION_V46R1_DOMAIN
        ),
        "construction_k7_lmb_column_factorization_v46r1": (
            CONSTRUCTION_K7_LMB_COLUMN_FACTORIZATION_V46R1_DOMAIN
        ),
        "construction_k7_lmb_relation_program_v46r1": (
            CONSTRUCTION_K7_LMB_RELATION_PROGRAM_V46R1_DOMAIN
        ),
        "construction_k7_lmb_factorized_distinction_v46r1": (
            CONSTRUCTION_K7_LMB_FACTORIZED_DISTINCTION_V46R1_DOMAIN
        ),
        "construction_k7_lmb_factorized_episode_v46r1": (
            CONSTRUCTION_K7_LMB_FACTORIZED_EPISODE_V46R1_DOMAIN
        ),
        "construction_k7_lmb_opaque_schema_ood_rejection_v46r1": (
            CONSTRUCTION_K7_LMB_OPAQUE_SCHEMA_OOD_REJECTION_V46R1_DOMAIN
        ),
        "construction_k7_lmb_opaque_column_campaign_v46r1": (
            CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_CAMPAIGN_V46R1_DOMAIN
        ),
        "construction_k7_lmb_opaque_column_verification_v46r1": (
            CONSTRUCTION_K7_LMB_OPAQUE_COLUMN_VERIFICATION_V46R1_DOMAIN
        ),
        "construction_k7_generic_bytecode_preregistration_v47": (
            CONSTRUCTION_K7_GENERIC_BYTECODE_PREREGISTRATION_V47_DOMAIN
        ),
        "construction_k7_generic_raw_observation_v47": (
            CONSTRUCTION_K7_GENERIC_RAW_OBSERVATION_V47_DOMAIN
        ),
        "construction_k7_generic_bytecode_program_v47": (
            CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47_DOMAIN
        ),
        "construction_k7_generic_local_distinction_v47": (
            CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47_DOMAIN
        ),
        "construction_k7_generic_receding_episode_v47": (
            CONSTRUCTION_K7_GENERIC_RECEDING_EPISODE_V47_DOMAIN
        ),
        "construction_k7_generic_stochastic_partial_v47": (
            CONSTRUCTION_K7_GENERIC_STOCHASTIC_PARTIAL_V47_DOMAIN
        ),
        "construction_k7_generic_sample_tax_v47": (
            CONSTRUCTION_K7_GENERIC_SAMPLE_TAX_V47_DOMAIN
        ),
        "construction_k7_generic_cross_domain_campaign_v47": (
            CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_CAMPAIGN_V47_DOMAIN
        ),
        "construction_k7_generic_cross_domain_verification_v47": (
            CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_VERIFICATION_V47_DOMAIN
        ),
        "construction_k7_generic_bytecode_failure_v47": (
            CONSTRUCTION_K7_GENERIC_BYTECODE_FAILURE_V47_DOMAIN
        ),
        "construction_k7_generic_bytecode_preregistration_v47r1": (
            CONSTRUCTION_K7_GENERIC_BYTECODE_PREREGISTRATION_V47R1_DOMAIN
        ),
        "construction_k7_generic_raw_observation_v47r1": (
            CONSTRUCTION_K7_GENERIC_RAW_OBSERVATION_V47R1_DOMAIN
        ),
        "construction_k7_generic_bytecode_program_v47r1": (
            CONSTRUCTION_K7_GENERIC_BYTECODE_PROGRAM_V47R1_DOMAIN
        ),
        "construction_k7_generic_local_distinction_v47r1": (
            CONSTRUCTION_K7_GENERIC_LOCAL_DISTINCTION_V47R1_DOMAIN
        ),
        "construction_k7_generic_receding_episode_v47r1": (
            CONSTRUCTION_K7_GENERIC_RECEDING_EPISODE_V47R1_DOMAIN
        ),
        "construction_k7_generic_stochastic_partial_v47r1": (
            CONSTRUCTION_K7_GENERIC_STOCHASTIC_PARTIAL_V47R1_DOMAIN
        ),
        "construction_k7_generic_sample_tax_v47r1": (
            CONSTRUCTION_K7_GENERIC_SAMPLE_TAX_V47R1_DOMAIN
        ),
        "construction_k7_generic_cross_domain_campaign_v47r1": (
            CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_CAMPAIGN_V47R1_DOMAIN
        ),
        "construction_k7_generic_cross_domain_verification_v47r1": (
            CONSTRUCTION_K7_GENERIC_CROSS_DOMAIN_VERIFICATION_V47R1_DOMAIN
        ),
        "construction_counter_registry_v7": (
            CONSTRUCTION_COUNTER_REGISTRY_V7_DOMAIN
        ),
        "construction_stage_profile_v7": (
            CONSTRUCTION_STAGE_PROFILE_V7_DOMAIN
        ),
        "construction_comparison_profile_v7": (
            CONSTRUCTION_COMPARISON_PROFILE_V7_DOMAIN
        ),
        "construction_actual_projection_profile_v7": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V7_DOMAIN
        ),
        "construction_counter_registry_v8": (
            CONSTRUCTION_COUNTER_REGISTRY_V8_DOMAIN
        ),
        "construction_stage_profile_v8": (
            CONSTRUCTION_STAGE_PROFILE_V8_DOMAIN
        ),
        "construction_comparison_profile_v8": (
            CONSTRUCTION_COMPARISON_PROFILE_V8_DOMAIN
        ),
        "construction_actual_projection_profile_v8": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V8_DOMAIN
        ),
        "construction_counter_registry_v9": (
            CONSTRUCTION_COUNTER_REGISTRY_V9_DOMAIN
        ),
        "construction_stage_profile_v9": (
            CONSTRUCTION_STAGE_PROFILE_V9_DOMAIN
        ),
        "construction_comparison_profile_v9": (
            CONSTRUCTION_COMPARISON_PROFILE_V9_DOMAIN
        ),
        "construction_actual_projection_profile_v9": (
            CONSTRUCTION_ACTUAL_PROJECTION_PROFILE_V9_DOMAIN
        ),
        "construction_k7_adaptive_operation_boundary_v1": (
            CONSTRUCTION_K7_ADAPTIVE_OPERATION_BOUNDARY_V1_DOMAIN
        ),
        "construction_k7_adaptive_operation_manifest_v1": (
            CONSTRUCTION_K7_ADAPTIVE_OPERATION_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_adaptive_operation_event_v1": (
            CONSTRUCTION_K7_ADAPTIVE_OPERATION_EVENT_V1_DOMAIN
        ),
        "construction_k7_adaptive_accounting_preregistration_v1": (
            CONSTRUCTION_K7_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_adaptive_occurrence_native_accounting_v1": (
            CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_NATIVE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_adaptive_component_native_accounting_v1": (
            CONSTRUCTION_K7_ADAPTIVE_COMPONENT_NATIVE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_adaptive_campaign_native_accounting_v1": (
            CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_NATIVE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_adaptive_route_input_envelope_v1": (
            CONSTRUCTION_K7_ADAPTIVE_ROUTE_INPUT_ENVELOPE_V1_DOMAIN
        ),
        "construction_k7_adaptive_shared_measurement_v1": (
            CONSTRUCTION_K7_ADAPTIVE_SHARED_MEASUREMENT_V1_DOMAIN
        ),
        "construction_k7_adaptive_shared_receipt_v1": (
            CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_adaptive_shared_receipt_set_v1": (
            CONSTRUCTION_K7_ADAPTIVE_SHARED_RECEIPT_SET_V1_DOMAIN
        ),
        "construction_k7_adaptive_path_aggregation_v1": (
            CONSTRUCTION_K7_ADAPTIVE_PATH_AGGREGATION_V1_DOMAIN
        ),
        "construction_k7_adaptive_occurrence_accounting_v1": (
            CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_adaptive_campaign_accounting_v1": (
            CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_ACCOUNTING_V1_DOMAIN
        ),
        "construction_k7_adaptive_output_renderer_v1": (
            CONSTRUCTION_K7_ADAPTIVE_OUTPUT_RENDERER_V1_DOMAIN
        ),
        "construction_k7_adaptive_output_commit_v1": (
            CONSTRUCTION_K7_ADAPTIVE_OUTPUT_COMMIT_V1_DOMAIN
        ),
        "construction_k7_adaptive_occurrence_independent_verification_v1": (
            CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_adaptive_campaign_independent_verification_v1": (
            CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_INDEPENDENT_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_reusable_build_epoch_resolution_v1": (
            CONSTRUCTION_K7_REUSABLE_BUILD_EPOCH_RESOLUTION_V1_DOMAIN
        ),
        "construction_k7_reusable_build_epoch_envelope_v1": (
            CONSTRUCTION_K7_REUSABLE_BUILD_EPOCH_ENVELOPE_V1_DOMAIN
        ),
        "construction_k7_reusable_abstract_query_spec_v1": (
            CONSTRUCTION_K7_REUSABLE_ABSTRACT_QUERY_SPEC_V1_DOMAIN
        ),
        "construction_k7_reusable_abstract_query_result_v1": (
            CONSTRUCTION_K7_REUSABLE_ABSTRACT_QUERY_RESULT_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_output_commit_v1": (
            V075_K7_CAUSAL_PROMOTION_OUTPUT_COMMIT_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_path_aggregation_v1": (
            V075_K7_CAUSAL_PROMOTION_PATH_AGGREGATION_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_occurrence_accounting_v1": (
            V075_K7_CAUSAL_PROMOTION_OCCURRENCE_ACCOUNTING_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_output_renderer_v1": (
            V075_K7_CAUSAL_PROMOTION_OUTPUT_RENDERER_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_budget_replay_attestation_v1": (
            V075_K7_CAUSAL_PROMOTION_BUDGET_REPLAY_ATTESTATION_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_route_context_v1": (
            V075_K7_CAUSAL_PROMOTION_ROUTE_CONTEXT_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_route_attempt_v1": (
            V075_K7_CAUSAL_PROMOTION_ROUTE_ATTEMPT_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_terminal_derivation_v1": (
            V075_K7_CAUSAL_PROMOTION_TERMINAL_DERIVATION_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_complete_bundle_verification_profile_v1": (
            V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_complete_bundle_semantic_verifier_v1": (
            V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN
        ),
        "v075_k7_causal_promotion_complete_bundle_verification_v1": (
            V075_K7_CAUSAL_PROMOTION_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN
        ),
        "construction_partial_native_occurrence_start_v1": (
            CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_START_V1_DOMAIN
        ),
        "construction_partial_native_stage_start_v1": (
            CONSTRUCTION_PARTIAL_NATIVE_STAGE_START_V1_DOMAIN
        ),
        "construction_partial_native_operation_event_v1": (
            CONSTRUCTION_PARTIAL_NATIVE_OPERATION_EVENT_V1_DOMAIN
        ),
        "construction_partial_native_stage_completion_v1": (
            CONSTRUCTION_PARTIAL_NATIVE_STAGE_COMPLETION_V1_DOMAIN
        ),
        "construction_partial_native_occurrence_completion_v1": (
            CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_COMPLETION_V1_DOMAIN
        ),
        "construction_partial_native_occurrence_abort_v1": (
            CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_ABORT_V1_DOMAIN
        ),
        "construction_partial_native_occurrence_transcript_v1": (
            CONSTRUCTION_PARTIAL_NATIVE_OCCURRENCE_TRANSCRIPT_V1_DOMAIN
        ),
        "construction_accounting_evidence_closure_context_v1": (
            CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN
        ),
        "construction_accounting_required_path_resolution_v1": (
            CONSTRUCTION_ACCOUNTING_REQUIRED_PATH_RESOLUTION_V1_DOMAIN
        ),
        "construction_accounting_evidence_closure_v1": (
            CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_V1_DOMAIN
        ),
        "construction_accounting_evidence_closure_verification_v1": (
            CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_VERIFICATION_V1_DOMAIN
        ),
        "construction_shared_resource_identity_binding_v1": (
            CONSTRUCTION_SHARED_RESOURCE_IDENTITY_BINDING_V1_DOMAIN
        ),
        "construction_shared_resource_measurement_window_v1": (
            CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_WINDOW_V1_DOMAIN
        ),
        "construction_shared_resource_measurement_method_v1": (
            CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_METHOD_V1_DOMAIN
        ),
        "construction_shared_resource_monitor_registration_v1": (
            CONSTRUCTION_SHARED_RESOURCE_MONITOR_REGISTRATION_V1_DOMAIN
        ),
        "construction_shared_resource_measurement_registry_v1": (
            CONSTRUCTION_SHARED_RESOURCE_MEASUREMENT_REGISTRY_V1_DOMAIN
        ),
        "construction_shared_resource_source_evidence_v1": (
            CONSTRUCTION_SHARED_RESOURCE_SOURCE_EVIDENCE_V1_DOMAIN
        ),
        "construction_shared_resource_charge_key_v1": (
            CONSTRUCTION_SHARED_RESOURCE_CHARGE_KEY_V1_DOMAIN
        ),
        "construction_shared_resource_receipt_v1": (
            CONSTRUCTION_SHARED_RESOURCE_RECEIPT_V1_DOMAIN
        ),
        "construction_shared_resource_receipt_set_v1": (
            CONSTRUCTION_SHARED_RESOURCE_RECEIPT_SET_V1_DOMAIN
        ),
        "construction_hash_purpose_registration_v1": (
            CONSTRUCTION_HASH_PURPOSE_REGISTRATION_V1_DOMAIN
        ),
        "construction_recursion_safe_hash_meter_profile_v1": (
            CONSTRUCTION_RECURSION_SAFE_HASH_METER_PROFILE_V1_DOMAIN
        ),
        "construction_named_obligation_v1": (
            CONSTRUCTION_NAMED_OBLIGATION_V1_DOMAIN
        ),
        "construction_named_obligation_registry_v1": (
            CONSTRUCTION_NAMED_OBLIGATION_REGISTRY_V1_DOMAIN
        ),
        "construction_accounting_required_path_partition_v1": (
            CONSTRUCTION_ACCOUNTING_REQUIRED_PATH_PARTITION_V1_DOMAIN
        ),
        "construction_accounting_completion_readiness_blocker_v1": (
            CONSTRUCTION_ACCOUNTING_COMPLETION_READINESS_BLOCKER_V1_DOMAIN
        ),
        "construction_accounting_completion_readiness_v1": (
            CONSTRUCTION_ACCOUNTING_COMPLETION_READINESS_V1_DOMAIN
        ),
        "construction_profile_native_zero_rule_v1": (
            CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_V1_DOMAIN
        ),
        "construction_profile_native_zero_rule_registry_v1": (
            CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_REGISTRY_V1_DOMAIN
        ),
        "construction_profile_native_zero_rule_readiness_row_v1": (
            CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_ROW_V1_DOMAIN
        ),
        "construction_profile_native_zero_rule_readiness_v1": (
            CONSTRUCTION_PROFILE_NATIVE_ZERO_RULE_READINESS_V1_DOMAIN
        ),
        "construction_owner_boundary_coverage_site_v1": (
            CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_SITE_V1_DOMAIN
        ),
        "construction_owner_boundary_coverage_profile_v1": (
            CONSTRUCTION_OWNER_BOUNDARY_COVERAGE_PROFILE_V1_DOMAIN
        ),
        "construction_occurrence_identity_join_v1": (
            CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_V1_DOMAIN
        ),
        "construction_occurrence_identity_join_verification_v1": (
            CONSTRUCTION_OCCURRENCE_IDENTITY_JOIN_VERIFICATION_V1_DOMAIN
        ),
        "construction_operational_sequence_marker_v1": (
            CONSTRUCTION_OPERATIONAL_SEQUENCE_MARKER_V1_DOMAIN
        ),
        "construction_operational_cutoff_attestation_v1": (
            CONSTRUCTION_OPERATIONAL_CUTOFF_ATTESTATION_V1_DOMAIN
        ),
        "construction_operational_cutoff_verification_v1": (
            CONSTRUCTION_OPERATIONAL_CUTOFF_VERIFICATION_V1_DOMAIN
        ),
        "construction_identity_join_readiness_v1": (
            CONSTRUCTION_IDENTITY_JOIN_READINESS_V1_DOMAIN
        ),
        "construction_accounting_completion_prerequisite_blocker_v1": (
            CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_BLOCKER_V1_DOMAIN
        ),
        "construction_accounting_completion_prerequisite_manifest_v1": (
            CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_MANIFEST_V1_DOMAIN
        ),
        "construction_accounting_completion_prerequisite_replay_v1": (
            CONSTRUCTION_ACCOUNTING_COMPLETION_PREREQUISITE_REPLAY_V1_DOMAIN
        ),
        "construction_shared_resource_live_measurement_event_v1": (
            CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_EVENT_V1_DOMAIN
        ),
        "construction_shared_resource_live_complete_window_zero_claim_v1": (
            CONSTRUCTION_SHARED_RESOURCE_LIVE_COMPLETE_WINDOW_ZERO_CLAIM_V1_DOMAIN
        ),
        "construction_shared_resource_live_typed_unavailable_resolution_v1": (
            CONSTRUCTION_SHARED_RESOURCE_LIVE_TYPED_UNAVAILABLE_RESOLUTION_V1_DOMAIN
        ),
        "construction_shared_resource_live_measurement_row_v1": (
            CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_ROW_V1_DOMAIN
        ),
        "construction_shared_resource_live_measurement_snapshot_v1": (
            CONSTRUCTION_SHARED_RESOURCE_LIVE_MEASUREMENT_SNAPSHOT_V1_DOMAIN
        ),
        "v075_k7_root_cap_accounted_sealed_program_v1": (
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROGRAM_V1_DOMAIN
        ),
        "v075_k7_root_cap_accounted_sealed_profile_v1": (
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROFILE_V1_DOMAIN
        ),
        "v075_k7_root_cap_accounted_sealed_route_identity_v1": (
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ROUTE_IDENTITY_V1_DOMAIN
        ),
        "v075_k7_root_cap_accounted_sealed_request_v1": (
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_REQUEST_V1_DOMAIN
        ),
        "v075_k7_root_cap_accounted_sealed_business_frame_v1": (
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_BUSINESS_FRAME_V1_DOMAIN
        ),
        "v075_k7_root_cap_accounted_sealed_accounting_suffix_frame_v1": (
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_ACCOUNTING_SUFFIX_FRAME_V1_DOMAIN
        ),
        "v075_k7_root_cap_accounted_sealed_protocol_replay_v1": (
            V075_K7_ROOT_CAP_ACCOUNTED_SEALED_PROTOCOL_REPLAY_V1_DOMAIN
        ),
        "v075_k7_root_cap_shared_resource_identity_derivation_v1": (
            V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_DERIVATION_V1_DOMAIN
        ),
        "v075_k7_root_cap_shared_resource_identity_verification_v1": (
            V075_K7_ROOT_CAP_SHARED_RESOURCE_IDENTITY_VERIFICATION_V1_DOMAIN
        ),
        "v075_k7_shared_resource_supervised_source_role_v1": (
            V075_K7_SHARED_RESOURCE_SUPERVISED_SOURCE_ROLE_V1_DOMAIN
        ),
        "v075_k7_shared_resource_rebased_journal_event_v1": (
            V075_K7_SHARED_RESOURCE_REBASED_JOURNAL_EVENT_V1_DOMAIN
        ),
        "v075_k7_shared_resource_supervised_finalization_bridge_v1": (
            V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_BRIDGE_V1_DOMAIN
        ),
        "v075_k7_shared_resource_supervised_finalization_verification_v1": (
            V075_K7_SHARED_RESOURCE_SUPERVISED_FINALIZATION_VERIFICATION_V1_DOMAIN
        ),
        "construction_output_bytes_fixed_point_iteration_v1": (
            CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_ITERATION_V1_DOMAIN
        ),
        "construction_output_bytes_fixed_point_profile_v1": (
            CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_PROFILE_V1_DOMAIN
        ),
        "construction_output_bytes_fixed_point_result_v1": (
            CONSTRUCTION_OUTPUT_BYTES_FIXED_POINT_RESULT_V1_DOMAIN
        ),
        "construction_output_bytes_rendered_artifact_set_v1": (
            CONSTRUCTION_OUTPUT_BYTES_RENDERED_ARTIFACT_SET_V1_DOMAIN
        ),
        "construction_output_bytes_rendered_artifact_v1": (
            CONSTRUCTION_OUTPUT_BYTES_RENDERED_ARTIFACT_V1_DOMAIN
        ),
        "construction_shared_resource_outer_source_set_v1": (
            CONSTRUCTION_SHARED_RESOURCE_OUTER_SOURCE_SET_V1_DOMAIN
        ),
        "construction_shared_resource_outer_raw_source_row_v1": (
            CONSTRUCTION_SHARED_RESOURCE_OUTER_RAW_SOURCE_ROW_V1_DOMAIN
        ),
        "construction_shared_resource_outer_finalization_v1": (
            CONSTRUCTION_SHARED_RESOURCE_OUTER_FINALIZATION_V1_DOMAIN
        ),
        "construction_shared_resource_global_supervisor_scope_v1": (
            CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_SCOPE_V1_DOMAIN
        ),
        "construction_shared_resource_global_supervisor_source_document_v1": (
            CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_SOURCE_DOCUMENT_V1_DOMAIN
        ),
        "construction_shared_resource_global_supervisor_event_v1": (
            CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_EVENT_V1_DOMAIN
        ),
        "construction_shared_resource_global_supervisor_event_journal_v1": (
            CONSTRUCTION_SHARED_RESOURCE_GLOBAL_SUPERVISOR_EVENT_JOURNAL_V1_DOMAIN
        ),
        "v075_k7_os_supervisor_read_evidence_v1": (
            V075_K7_OS_SUPERVISOR_READ_EVIDENCE_V1_DOMAIN
        ),
        "v075_k7_os_supervisor_admission_profile_v1": (
            V075_K7_OS_SUPERVISOR_ADMISSION_PROFILE_V1_DOMAIN
        ),
        "v075_k7_os_supervisor_admission_probe_v1": (
            V075_K7_OS_SUPERVISOR_ADMISSION_PROBE_V1_DOMAIN
        ),
        "v075_k7_os_supervisor_admission_result_v1": (
            V075_K7_OS_SUPERVISOR_ADMISSION_RESULT_V1_DOMAIN
        ),
        "v075_k7_parent_owned_successor_profile_v1": (
            V075_K7_PARENT_OWNED_SUCCESSOR_PROFILE_V1_DOMAIN
        ),
        "v075_k7_scientific_phase3e_occurrence_mapping_v1": (
            V075_K7_SCIENTIFIC_PHASE3E_OCCURRENCE_MAPPING_V1_DOMAIN
        ),
        "v075_k7_parent_owned_successor_request_v1": (
            V075_K7_PARENT_OWNED_SUCCESSOR_REQUEST_V1_DOMAIN
        ),
        "v075_k7_parent_owned_prelaunch_blocked_result_v1": (
            V075_K7_PARENT_OWNED_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN
        ),
        "v075_k7_cgroup_lease_profile_v1": (
            V075_K7_CGROUP_LEASE_PROFILE_V1_DOMAIN
        ),
        "v075_k7_cgroup_lease_authority_v1": (
            V075_K7_CGROUP_LEASE_AUTHORITY_V1_DOMAIN
        ),
        "v075_k7_cgroup_lease_prelaunch_blocked_result_v1": (
            V075_K7_CGROUP_LEASE_PRELAUNCH_BLOCKED_RESULT_V1_DOMAIN
        ),
        "v075_k7_successor_portable_profile_closure_v1": (
            V075_K7_SUCCESSOR_PORTABLE_PROFILE_CLOSURE_V1_DOMAIN
        ),
        "v075_k7_successor_portable_request_replay_v1": (
            V075_K7_SUCCESSOR_PORTABLE_REQUEST_REPLAY_V1_DOMAIN
        ),
        "v075_k7_child_business_bundle_v1": (
            V075_K7_CHILD_BUSINESS_BUNDLE_V1_DOMAIN
        ),
        "v075_k7_atomic_child_business_frame_v1": (
            V075_K7_ATOMIC_CHILD_BUSINESS_FRAME_V1_DOMAIN
        ),
        "v075_k7_atomic_parent_execution_spec_v1": (
            V075_K7_ATOMIC_PARENT_EXECUTION_SPEC_V1_DOMAIN
        ),
        "v075_k7_atomic_parent_accounting_suffix_v1": (
            V075_K7_ATOMIC_PARENT_ACCOUNTING_SUFFIX_V1_DOMAIN
        ),
        "v075_k7_atomic_parent_execution_result_v1": (
            V075_K7_ATOMIC_PARENT_EXECUTION_RESULT_V1_DOMAIN
        ),
        "v075_k7_atomic_parent_execution_failure_v1": (
            V075_K7_ATOMIC_PARENT_EXECUTION_FAILURE_V1_DOMAIN
        ),
        "v075_k7_atomic_supervisor_resource_evidence_v1": (
            V075_K7_ATOMIC_SUPERVISOR_RESOURCE_EVIDENCE_V1_DOMAIN
        ),
        "v075_k7_atomic_shared_resource_registry_v1": (
            V075_K7_ATOMIC_SHARED_RESOURCE_REGISTRY_V1_DOMAIN
        ),
        "v075_k7_atomic_shared_resource_resolution_v1": (
            V075_K7_ATOMIC_SHARED_RESOURCE_RESOLUTION_V1_DOMAIN
        ),
        "v075_k7_atomic_shared_resource_verification_v1": (
            V075_K7_ATOMIC_SHARED_RESOURCE_VERIFICATION_V1_DOMAIN
        ),
        "v075_k7_attempt_process_supervisor_profile_v1": (
            V075_K7_ATTEMPT_PROCESS_SUPERVISOR_PROFILE_V1_DOMAIN
        ),
        "v075_k7_attempt_process_session_start_v1": (
            V075_K7_ATTEMPT_PROCESS_SESSION_START_V1_DOMAIN
        ),
        "v075_k7_attempt_process_launch_event_v1": (
            V075_K7_ATTEMPT_PROCESS_LAUNCH_EVENT_V1_DOMAIN
        ),
        "v075_k7_attempt_process_raw_journal_v1": (
            V075_K7_ATTEMPT_PROCESS_RAW_JOURNAL_V1_DOMAIN
        ),
        "v075_k7_attempt_process_execution_v1": (
            V075_K7_ATTEMPT_PROCESS_EXECUTION_V1_DOMAIN
        ),
        "v075_k7_attempt_process_envelope_v1": (
            V075_K7_ATTEMPT_PROCESS_ENVELOPE_V1_DOMAIN
        ),
        "v075_k7_attempt_process_verification_v1": (
            V075_K7_ATTEMPT_PROCESS_VERIFICATION_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_cgroup_profile_v1": (
            V075_K7_OUTER_ATTEMPT_CGROUP_PROFILE_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_cgroup_lease_v1": (
            V075_K7_OUTER_ATTEMPT_CGROUP_LEASE_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_cgroup_blocked_result_v1": (
            V075_K7_OUTER_ATTEMPT_CGROUP_BLOCKED_RESULT_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_memory_evidence_v1": (
            V075_K7_OUTER_ATTEMPT_MEMORY_EVIDENCE_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_broker_ipc_profile_v1": (
            V075_K7_OUTER_ATTEMPT_BROKER_IPC_PROFILE_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_broker_ipc_frame_v1": (
            V075_K7_OUTER_ATTEMPT_BROKER_IPC_FRAME_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_broker_ipc_transcript_v1": (
            V075_K7_OUTER_ATTEMPT_BROKER_IPC_TRANSCRIPT_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_broker_preparation_profile_v1": (
            V075_K7_OUTER_ATTEMPT_BROKER_PREPARATION_PROFILE_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_broker_execution_spec_v1": (
            V075_K7_OUTER_ATTEMPT_BROKER_EXECUTION_SPEC_V1_DOMAIN
        ),
        "v075_k7_outer_attempt_prepared_broker_session_v1": (
            V075_K7_OUTER_ATTEMPT_PREPARED_BROKER_SESSION_V1_DOMAIN
        ),
        "v075_k7_two_role_broker_probe_profile_v1": (
            V075_K7_TWO_ROLE_BROKER_PROBE_PROFILE_V1_DOMAIN
        ),
        "v075_k7_two_role_broker_probe_result_v1": (
            V075_K7_TWO_ROLE_BROKER_PROBE_RESULT_V1_DOMAIN
        ),
        "v075_k7_two_role_broker_failure_prefix_v1": (
            V075_K7_TWO_ROLE_BROKER_FAILURE_PREFIX_V1_DOMAIN
        ),
        "v075_k7_business_entry_core_profile_v1": (
            V075_K7_BUSINESS_ENTRY_CORE_PROFILE_V1_DOMAIN
        ),
        "v075_k7_business_entry_core_emission_v1": (
            V075_K7_BUSINESS_ENTRY_CORE_EMISSION_V1_DOMAIN
        ),
        "v075_k7_production_role_manifest_profile_v1": (
            V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V1_DOMAIN
        ),
        "v075_k7_production_role_spec_v1": (
            V075_K7_PRODUCTION_ROLE_SPEC_V1_DOMAIN
        ),
        "v075_k7_production_role_manifest_v1": (
            V075_K7_PRODUCTION_ROLE_MANIFEST_V1_DOMAIN
        ),
        "v075_k7_broker_worker_entry_core_profile_v1": (
            V075_K7_BROKER_WORKER_ENTRY_CORE_PROFILE_V1_DOMAIN
        ),
        "v075_k7_broker_operational_output_v1": (
            V075_K7_BROKER_OPERATIONAL_OUTPUT_V1_DOMAIN
        ),
        "v075_k7_broker_output_commit_receipt_v1": (
            V075_K7_BROKER_OUTPUT_COMMIT_RECEIPT_V1_DOMAIN
        ),
        "v075_k7_broker_worker_completion_v1": (
            V075_K7_BROKER_WORKER_COMPLETION_V1_DOMAIN
        ),
        "v075_k7_production_role_bootstrap_profile_v2": (
            V075_K7_PRODUCTION_ROLE_BOOTSTRAP_PROFILE_V2_DOMAIN
        ),
        "v075_k7_production_role_manifest_profile_v2": (
            V075_K7_PRODUCTION_ROLE_MANIFEST_PROFILE_V2_DOMAIN
        ),
        "v075_k7_production_role_spec_v2": (
            V075_K7_PRODUCTION_ROLE_SPEC_V2_DOMAIN
        ),
        "v075_k7_production_role_manifest_v2": (
            V075_K7_PRODUCTION_ROLE_MANIFEST_V2_DOMAIN
        ),
        "v075_k7_production_role_launch_context_v2": (
            V075_K7_PRODUCTION_ROLE_LAUNCH_CONTEXT_V2_DOMAIN
        ),
        "v075_k7_broker_resource_session_profile_v2": (
            V075_K7_BROKER_RESOURCE_SESSION_PROFILE_V2_DOMAIN
        ),
        "v075_k7_broker_role_capability_bundle_v2": (
            V075_K7_BROKER_ROLE_CAPABILITY_BUNDLE_V2_DOMAIN
        ),
        "v075_k7_broker_resource_session_v2": (
            V075_K7_BROKER_RESOURCE_SESSION_V2_DOMAIN
        ),
        "v075_k7_authenticated_broker_channel_profile_v2": (
            V075_K7_AUTHENTICATED_BROKER_CHANNEL_PROFILE_V2_DOMAIN
        ),
        "v075_k7_authenticated_broker_frame_v2": (
            V075_K7_AUTHENTICATED_BROKER_FRAME_V2_DOMAIN
        ),
        "v075_k7_production_role_sandbox_profile_v2": (
            V075_K7_PRODUCTION_ROLE_SANDBOX_PROFILE_V2_DOMAIN
        ),
        "v075_k7_production_role_postexec_tightening_v2": (
            V075_K7_PRODUCTION_ROLE_POSTEXEC_TIGHTENING_V2_DOMAIN
        ),
        "v075_k7_production_role_launch_authority_profile_v2": (
            V075_K7_PRODUCTION_ROLE_LAUNCH_AUTHORITY_PROFILE_V2_DOMAIN
        ),
        "v075_k7_production_role_launch_authority_v2": (
            V075_K7_PRODUCTION_ROLE_LAUNCH_AUTHORITY_V2_DOMAIN
        ),
        "construction_shared_resource_transfer_mount_session_v2": (
            CONSTRUCTION_SHARED_RESOURCE_TRANSFER_MOUNT_SESSION_V2_DOMAIN
        ),
        "construction_shared_resource_transfer_purpose_v2": (
            CONSTRUCTION_SHARED_RESOURCE_TRANSFER_PURPOSE_V2_DOMAIN
        ),
        "construction_shared_resource_transfer_payload_v2": (
            CONSTRUCTION_SHARED_RESOURCE_TRANSFER_PAYLOAD_V2_DOMAIN
        ),
        "construction_shared_resource_transfer_id_v2": (
            CONSTRUCTION_SHARED_RESOURCE_TRANSFER_ID_V2_DOMAIN
        ),
        "construction_shared_resource_transfer_charge_key_v2": (
            CONSTRUCTION_SHARED_RESOURCE_TRANSFER_CHARGE_KEY_V2_DOMAIN
        ),
        "construction_shared_resource_transfer_event_v2": (
            CONSTRUCTION_SHARED_RESOURCE_TRANSFER_EVENT_V2_DOMAIN
        ),
        "construction_shared_resource_mount_interval_v2": (
            CONSTRUCTION_SHARED_RESOURCE_MOUNT_INTERVAL_V2_DOMAIN
        ),
        "construction_shared_resource_mount_event_v2": (
            CONSTRUCTION_SHARED_RESOURCE_MOUNT_EVENT_V2_DOMAIN
        ),
        "v075_k7_operational_cutoff_attestation_v2": (
            V075_K7_OPERATIONAL_CUTOFF_ATTESTATION_V2_DOMAIN
        ),
        "v075_k7_read_transfer_journal_v2": (
            V075_K7_READ_TRANSFER_JOURNAL_V2_DOMAIN
        ),
        "v075_k7_staged_transfer_journal_v2": (
            V075_K7_STAGED_TRANSFER_JOURNAL_V2_DOMAIN
        ),
        "v075_k7_transfer_charge_registry_v2": (
            V075_K7_TRANSFER_CHARGE_REGISTRY_V2_DOMAIN
        ),
        "v075_k7_mount_payload_registry_v2": (
            V075_K7_MOUNT_PAYLOAD_REGISTRY_V2_DOMAIN
        ),
        "v075_k7_mount_visibility_journal_v2": (
            V075_K7_MOUNT_VISIBILITY_JOURNAL_V2_DOMAIN
        ),
        "construction_shared_resource_common_session_v2": (
            CONSTRUCTION_SHARED_RESOURCE_COMMON_SESSION_V2_DOMAIN
        ),
        "construction_shared_resource_common_source_site_v2": (
            CONSTRUCTION_SHARED_RESOURCE_COMMON_SOURCE_SITE_V2_DOMAIN
        ),
        "construction_shared_resource_hash_purpose_v2": (
            CONSTRUCTION_SHARED_RESOURCE_HASH_PURPOSE_V2_DOMAIN
        ),
        "construction_shared_resource_named_obligation_v2": (
            CONSTRUCTION_SHARED_RESOURCE_NAMED_OBLIGATION_V2_DOMAIN
        ),
        "construction_shared_resource_broker_observation_binding_v2": (
            CONSTRUCTION_SHARED_RESOURCE_BROKER_OBSERVATION_BINDING_V2_DOMAIN
        ),
        "construction_shared_resource_common_event_v2": (
            CONSTRUCTION_SHARED_RESOURCE_COMMON_EVENT_V2_DOMAIN
        ),
        "v075_k7_hash_event_transcript_v2": (
            V075_K7_HASH_EVENT_TRANSCRIPT_V2_DOMAIN
        ),
        "v075_k7_hash_purpose_registry_v2": (
            V075_K7_HASH_PURPOSE_REGISTRY_V2_DOMAIN
        ),
        "v075_k7_loaded_hash_site_attestation_v2": (
            V075_K7_LOADED_HASH_SITE_ATTESTATION_V2_DOMAIN
        ),
        "v075_k7_integrity_obligation_registry_v2": (
            V075_K7_INTEGRITY_OBLIGATION_REGISTRY_V2_DOMAIN
        ),
        "v075_k7_integrity_obligation_transcript_v2": (
            V075_K7_INTEGRITY_OBLIGATION_TRANSCRIPT_V2_DOMAIN
        ),
        "v075_k7_loaded_integrity_site_attestation_v2": (
            V075_K7_LOADED_INTEGRITY_SITE_ATTESTATION_V2_DOMAIN
        ),
        "v075_k7_protocol_obligation_registry_v2": (
            V075_K7_PROTOCOL_OBLIGATION_REGISTRY_V2_DOMAIN
        ),
        "v075_k7_protocol_obligation_transcript_v2": (
            V075_K7_PROTOCOL_OBLIGATION_TRANSCRIPT_V2_DOMAIN
        ),
        "v075_k7_loaded_protocol_site_attestation_v2": (
            V075_K7_LOADED_PROTOCOL_SITE_ATTESTATION_V2_DOMAIN
        ),
        "construction_shared_resource_output_finalization_session_v2": (
            CONSTRUCTION_SHARED_RESOURCE_OUTPUT_FINALIZATION_SESSION_V2_DOMAIN
        ),
        "construction_shared_resource_durable_write_event_v2": (
            CONSTRUCTION_SHARED_RESOURCE_DURABLE_WRITE_EVENT_V2_DOMAIN
        ),
        "construction_shared_resource_output_fixed_point_iteration_v2": (
            CONSTRUCTION_SHARED_RESOURCE_OUTPUT_FIXED_POINT_ITERATION_V2_DOMAIN
        ),
        "v075_k7_durable_output_fixed_point_v2": (
            V075_K7_DURABLE_OUTPUT_FIXED_POINT_V2_DOMAIN
        ),
        "v075_k7_exclusive_writer_attestation_v2": (
            V075_K7_EXCLUSIVE_WRITER_ATTESTATION_V2_DOMAIN
        ),
        "v075_k7_eight_role_output_manifest_v2": (
            V075_K7_EIGHT_ROLE_OUTPUT_MANIFEST_V2_DOMAIN
        ),
        "construction_shared_resource_working_process_event_v2": (
            CONSTRUCTION_SHARED_RESOURCE_WORKING_PROCESS_EVENT_V2_DOMAIN
        ),
        "v075_k7_cgroup_empty_attestation_v2": (
            V075_K7_CGROUP_EMPTY_ATTESTATION_V2_DOMAIN
        ),
        "v075_k7_memory_peak_post_read_v2": (
            V075_K7_MEMORY_PEAK_POST_READ_V2_DOMAIN
        ),
        "v075_k7_memory_peak_pre_read_v2": (
            V075_K7_MEMORY_PEAK_PRE_READ_V2_DOMAIN
        ),
        "v075_k7_same_ofd_attestation_v2": (
            V075_K7_SAME_OFD_ATTESTATION_V2_DOMAIN
        ),
        "v075_k7_no_spawn_attestation_v2": (
            V075_K7_NO_SPAWN_ATTESTATION_V2_DOMAIN
        ),
        "v075_k7_pidfd_reap_attestation_v2": (
            V075_K7_PIDFD_REAP_ATTESTATION_V2_DOMAIN
        ),
        "v075_k7_process_lifecycle_journal_v2": (
            V075_K7_PROCESS_LIFECYCLE_JOURNAL_V2_DOMAIN
        ),
        "construction_shared_resource_bound_source_v3": (
            CONSTRUCTION_SHARED_RESOURCE_BOUND_SOURCE_V3_DOMAIN
        ),
        "v075_k7_production_shared_resource_envelope_v3": (
            V075_K7_PRODUCTION_SHARED_RESOURCE_ENVELOPE_V3_DOMAIN
        ),
        "v075_k7_production_broker_runtime_profile_v2": (
            V075_K7_PRODUCTION_BROKER_RUNTIME_PROFILE_V2_DOMAIN
        ),
        "v075_k7_production_broker_runtime_envelope_v2": (
            V075_K7_PRODUCTION_BROKER_RUNTIME_ENVELOPE_V2_DOMAIN
        ),
        "construction_shared_resource_semantic_verifier_v2": (
            CONSTRUCTION_SHARED_RESOURCE_SEMANTIC_VERIFIER_V2_DOMAIN
        ),
        "construction_shared_resource_path_exact_authorization_v1": (
            CONSTRUCTION_SHARED_RESOURCE_PATH_EXACT_AUTHORIZATION_V1_DOMAIN
        ),
        "v075_k7_verified_nine_shared_resource_envelope_v1": (
            V075_K7_VERIFIED_NINE_SHARED_RESOURCE_ENVELOPE_V1_DOMAIN
        ),
        "construction_shared_cap_profile_v1": (
            CONSTRUCTION_SHARED_CAP_PROFILE_V1_DOMAIN
        ),
        "construction_shared_cap_fallback_decision_candidate_v1": (
            CONSTRUCTION_SHARED_CAP_FALLBACK_DECISION_CANDIDATE_V1_DOMAIN
        ),
        "construction_shared_cap_fallback_decision_prerequisite_v1": (
            CONSTRUCTION_SHARED_CAP_FALLBACK_DECISION_PREREQUISITE_V1_DOMAIN
        ),
        "construction_shared_cap_session_v1": (
            CONSTRUCTION_SHARED_CAP_SESSION_V1_DOMAIN
        ),
        "construction_shared_cap_reservation_v1": (
            CONSTRUCTION_SHARED_CAP_RESERVATION_V1_DOMAIN
        ),
        "construction_shared_cap_mount_token_v1": (
            CONSTRUCTION_SHARED_CAP_MOUNT_TOKEN_V1_DOMAIN
        ),
        "construction_shared_cap_receipt_v1": (
            CONSTRUCTION_SHARED_CAP_RECEIPT_V1_DOMAIN
        ),
        "construction_shared_cap_snapshot_v1": (
            CONSTRUCTION_SHARED_CAP_SNAPSHOT_V1_DOMAIN
        ),
        "construction_k7_direct_fallback_shared_source_site_v1": (
            CONSTRUCTION_K7_DIRECT_FALLBACK_SHARED_SOURCE_SITE_V1_DOMAIN
        ),
        "construction_k7_direct_fallback_shared_source_manifest_v1": (
            CONSTRUCTION_K7_DIRECT_FALLBACK_SHARED_SOURCE_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_direct_fallback_aggregate_cap_formula_spec_v1": (
            CONSTRUCTION_K7_DIRECT_FALLBACK_AGGREGATE_CAP_FORMULA_SPEC_V1_DOMAIN
        ),
        "construction_k7_direct_fallback_manifest_bound_cap_join_v1": (
            CONSTRUCTION_K7_DIRECT_FALLBACK_MANIFEST_BOUND_CAP_JOIN_V1_DOMAIN
        ),
        "construction_k7_h1_direct_fallback_two_role_recipe_profile_v1": (
            CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_direct_fallback_two_role_recipe_v1": (
            CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_V1_DOMAIN
        ),
        "construction_k7_h1_current_build_kernel_attestation_v1": (
            CONSTRUCTION_K7_H1_CURRENT_BUILD_KERNEL_ATTESTATION_V1_DOMAIN
        ),
        "construction_k7_h1_current_query_attestation_v1": (
            CONSTRUCTION_K7_H1_CURRENT_QUERY_ATTESTATION_V1_DOMAIN
        ),
        "construction_k7_h1_current_source_fixture_v1": (
            CONSTRUCTION_K7_H1_CURRENT_SOURCE_FIXTURE_V1_DOMAIN
        ),
        "construction_k7_h1_durable_proof_match_attestation_v1": (
            CONSTRUCTION_K7_H1_DURABLE_PROOF_MATCH_ATTESTATION_V1_DOMAIN
        ),
        "construction_k7_h1_production_current_identity_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_V1_DOMAIN
        ),
        "construction_k7_h1_production_current_identity_verification_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_execution_profile_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_EXECUTION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_predecision_context_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_CONTEXT_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_predecision_input_set_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_INPUT_SET_V1_DOMAIN
        ),
        "construction_k7_h1_predecision_access_event_v1": (
            CONSTRUCTION_K7_H1_PREDECISION_ACCESS_EVENT_V1_DOMAIN
        ),
        "construction_k7_h1_predecision_access_log_v1": (
            CONSTRUCTION_K7_H1_PREDECISION_ACCESS_LOG_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_child_result_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_CHILD_RESULT_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_observed_evidence_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_h1_predecision_current_access_cutoff_v1": (
            CONSTRUCTION_K7_H1_PREDECISION_CURRENT_ACCESS_CUTOFF_V1_DOMAIN
        ),
        "construction_k7_h1_production_current_access_authority_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_ACCESS_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_construction_fixture_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_CONSTRUCTION_FIXTURE_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_authority_blocker_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_AUTHORITY_BLOCKER_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_fresh_exec_runtime_profile_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_fresh_exec_source_manifest_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_SOURCE_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_fresh_exec_runtime_manifest_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_runtime_unavailable_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_RUNTIME_UNAVAILABLE_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_observed_runtime_facts_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_observed_runtime_facts_verification_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_profile_v2": (
            CONSTRUCTION_K7_H1_SHARED_CAP_PROFILE_V2_DOMAIN
        ),
        "construction_k7_h1_shared_cap_source_manifest_v2": (
            CONSTRUCTION_K7_H1_SHARED_CAP_SOURCE_MANIFEST_V2_DOMAIN
        ),
        "construction_k7_h1_shared_cap_runtime_v2": (
            CONSTRUCTION_K7_H1_SHARED_CAP_RUNTIME_V2_DOMAIN
        ),
        "construction_k7_h1_shared_cap_receipt_v2": (
            CONSTRUCTION_K7_H1_SHARED_CAP_RECEIPT_V2_DOMAIN
        ),
        "construction_k7_h1_shared_cap_event_v2": (
            CONSTRUCTION_K7_H1_SHARED_CAP_EVENT_V2_DOMAIN
        ),
        "construction_k7_h1_shared_cap_mount_token_v2": (
            CONSTRUCTION_K7_H1_SHARED_CAP_MOUNT_TOKEN_V2_DOMAIN
        ),
        "construction_k7_h1_shared_cap_output_token_v2": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OUTPUT_TOKEN_V2_DOMAIN
        ),
        "construction_k7_h1_shared_cap_memory_binding_v2": (
            CONSTRUCTION_K7_H1_SHARED_CAP_MEMORY_BINDING_V2_DOMAIN
        ),
        "construction_k7_h1_production_output_branch_dag_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_BRANCH_DAG_V1_DOMAIN
        ),
        "construction_k7_h1_production_output_serializer_universe_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_SERIALIZER_UNIVERSE_V1_DOMAIN
        ),
        "construction_k7_h1_production_output_operand_context_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_CONTEXT_V1_DOMAIN
        ),
        "construction_k7_h1_production_output_role_upper_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_ROLE_UPPER_V1_DOMAIN
        ),
        "construction_k7_h1_production_output_fixed_point_iteration_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_FIXED_POINT_ITERATION_V1_DOMAIN
        ),
        "construction_k7_h1_production_output_branch_fixed_point_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_BRANCH_FIXED_POINT_V1_DOMAIN
        ),
        "construction_k7_h1_production_output_operand_authority_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_h1_production_output_operand_candidate_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_OUTPUT_OPERAND_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_shared_resource_branch_program_v1": (
            CONSTRUCTION_K7_H1_SHARED_RESOURCE_BRANCH_PROGRAM_V1_DOMAIN
        ),
        "construction_k7_h1_shared_common_catalogue_v1": (
            CONSTRUCTION_K7_H1_SHARED_COMMON_CATALOGUE_V1_DOMAIN
        ),
        "construction_k7_h1_shared_io_catalogue_v1": (
            CONSTRUCTION_K7_H1_SHARED_IO_CATALOGUE_V1_DOMAIN
        ),
        "construction_k7_h1_physical_mount_catalogue_v1": (
            CONSTRUCTION_K7_H1_PHYSICAL_MOUNT_CATALOGUE_V1_DOMAIN
        ),
        "construction_k7_h1_memory_scope_authority_v1": (
            CONSTRUCTION_K7_H1_MEMORY_SCOPE_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_h1_launch_authority_v1": (
            CONSTRUCTION_K7_H1_LAUNCH_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_h1_memory_scope_candidate_v1": (
            CONSTRUCTION_K7_H1_MEMORY_SCOPE_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_launch_catalogue_candidate_v1": (
            CONSTRUCTION_K7_H1_LAUNCH_CATALOGUE_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_shared_operand_context_v1": (
            CONSTRUCTION_K7_H1_SHARED_OPERAND_CONTEXT_V1_DOMAIN
        ),
        "construction_k7_h1_shared_operand_row_v1": (
            CONSTRUCTION_K7_H1_SHARED_OPERAND_ROW_V1_DOMAIN
        ),
        "construction_k7_h1_shared_operand_authority_v1": (
            CONSTRUCTION_K7_H1_SHARED_OPERAND_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_h1_predecision_common_prefix_reservation_v1": (
            CONSTRUCTION_K7_H1_PREDECISION_COMMON_PREFIX_RESERVATION_V1_DOMAIN
        ),
        "construction_k7_h1_production_lifecycle_source_manifest_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_h1_production_lifecycle_program_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_PROGRAM_V1_DOMAIN
        ),
        "construction_k7_h1_production_lifecycle_branch_analysis_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_BRANCH_ANALYSIS_V1_DOMAIN
        ),
        "construction_k7_h1_production_lifecycle_replay_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_REPLAY_V1_DOMAIN
        ),
        "construction_k7_h1_production_lifecycle_source_authority_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_h1_production_lifecycle_source_candidate_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_SOURCE_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_local_source_registry_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_LOCAL_SOURCE_REGISTRY_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_program_snapshot_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_PROGRAM_SNAPSHOT_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_final_preregistration_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_FINAL_PREREGISTRATION_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_local_main_anchor_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_LOCAL_MAIN_ANCHOR_V1_DOMAIN
        ),
        "construction_k7_h1_caller_pinned_lifecycle_provenance_v1": (
            CONSTRUCTION_K7_H1_CALLER_PINNED_LIFECYCLE_PROVENANCE_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_profile_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_source_manifest_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SOURCE_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_runtime_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RUNTIME_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_reservation_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RESERVATION_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_native_cell_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_NATIVE_CELL_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_native_evidence_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_NATIVE_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_settlement_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SETTLEMENT_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_receipt_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_event_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_EVENT_V1_DOMAIN
        ),
        "construction_k7_h1_shared_cap_owner_v3_snapshot_v1": (
            CONSTRUCTION_K7_H1_SHARED_CAP_OWNER_V3_SNAPSHOT_V1_DOMAIN
        ),
        "construction_k7_h1_attempt_rejection_gate_v1": (
            CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_GATE_V1_DOMAIN
        ),
        "construction_k7_h1_attempt_rejection_commit_v1": (
            CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_COMMIT_V1_DOMAIN
        ),
        "construction_k7_h1_attempt_rejection_ack_v1": (
            CONSTRUCTION_K7_H1_ATTEMPT_REJECTION_ACK_V1_DOMAIN
        ),
        "construction_k7_h1_anchored_lifecycle_handler_registry_v1": (
            CONSTRUCTION_K7_H1_ANCHORED_LIFECYCLE_HANDLER_REGISTRY_V1_DOMAIN
        ),
        "construction_k7_h1_anchored_lifecycle_program_v1": (
            CONSTRUCTION_K7_H1_ANCHORED_LIFECYCLE_PROGRAM_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_dispatch_profile_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_dispatch_event_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_EVENT_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_dispatch_trace_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_DISPATCH_TRACE_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_complete_branch_analysis_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_COMPLETE_BRANCH_ANALYSIS_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_cleanup_pass_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_CLEANUP_PASS_V1_DOMAIN
        ),
        "construction_k7_h1_lifecycle_output_leaf_join_v1": (
            CONSTRUCTION_K7_H1_LIFECYCLE_OUTPUT_LEAF_JOIN_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_atomic_bridge_profile_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_atomic_bridge_export_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_EXPORT_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_atomic_bridge_request_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_REQUEST_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_atomic_bridge_commit_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_COMMIT_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_atomic_bridge_receipt_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_ATOMIC_BRIDGE_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_h1_postfreeze_current_access_authority_v1": (
            CONSTRUCTION_K7_H1_POSTFREEZE_CURRENT_ACCESS_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_h1_joint_output_read_iteration_v1": (
            CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_ITERATION_V1_DOMAIN
        ),
        "construction_k7_h1_joint_output_read_fixed_point_v1": (
            CONSTRUCTION_K7_H1_JOINT_OUTPUT_READ_FIXED_POINT_V1_DOMAIN
        ),
        "construction_k7_h1_branch_aware_output_profile_v1": (
            CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_branch_aware_output_business_fixture_v1": (
            CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_BUSINESS_FIXTURE_V1_DOMAIN
        ),
        "construction_k7_h1_branch_aware_output_broker_fixture_v1": (
            CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_BROKER_FIXTURE_V1_DOMAIN
        ),
        "construction_k7_h1_branch_aware_output_input_v1": (
            CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_INPUT_V1_DOMAIN
        ),
        "construction_k7_h1_branch_aware_output_role_artifact_v1": (
            CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_ROLE_ARTIFACT_V1_DOMAIN
        ),
        "construction_k7_h1_branch_aware_output_artifact_set_v1": (
            CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_ARTIFACT_SET_V1_DOMAIN
        ),
        "construction_k7_h1_branch_aware_output_fixed_point_iteration_v1": (
            CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_FIXED_POINT_ITERATION_V1_DOMAIN
        ),
        "construction_k7_h1_branch_aware_output_fixed_point_result_v1": (
            CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_FIXED_POINT_RESULT_V1_DOMAIN
        ),
        "construction_k7_h1_business_adapter_profile_v1": (
            CONSTRUCTION_K7_H1_BUSINESS_ADAPTER_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_production_business_request_candidate_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_BUSINESS_REQUEST_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_production_business_result_candidate_v1": (
            CONSTRUCTION_K7_H1_PRODUCTION_BUSINESS_RESULT_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_current_access_candidate_v1": (
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_formal_v7_decision_candidate_v1": (
            CONSTRUCTION_K7_H1_FORMAL_V7_DECISION_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_search_semantics_bridge_v1": (
            CONSTRUCTION_K7_H1_SEARCH_SEMANTICS_BRIDGE_V1_DOMAIN
        ),
        "construction_k7_h1_business_result_commit_receipt_candidate_v1": (
            CONSTRUCTION_K7_H1_BUSINESS_RESULT_COMMIT_RECEIPT_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_worker_result_verification_candidate_v1": (
            CONSTRUCTION_K7_H1_WORKER_RESULT_VERIFICATION_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_execution_topology_profile_v1": (
            CONSTRUCTION_K7_H1_EXECUTION_TOPOLOGY_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_broker_ipc_profile_v1": (
            CONSTRUCTION_K7_H1_BROKER_IPC_PROFILE_V1_DOMAIN
        ),
        "construction_k7_h1_broker_ipc_binding_candidate_v1": (
            CONSTRUCTION_K7_H1_BROKER_IPC_BINDING_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_broker_ipc_worker_ready_candidate_v1": (
            CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_READY_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_broker_ipc_business_request_candidate_v1": (
            CONSTRUCTION_K7_H1_BROKER_IPC_BUSINESS_REQUEST_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_broker_ipc_business_result_candidate_v1": (
            CONSTRUCTION_K7_H1_BROKER_IPC_BUSINESS_RESULT_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_broker_ipc_worker_ack_candidate_v1": (
            CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_ACK_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_broker_ipc_worker_eof_candidate_v1": (
            CONSTRUCTION_K7_H1_BROKER_IPC_WORKER_EOF_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_h1_broker_ipc_transcript_candidate_v1": (
            CONSTRUCTION_K7_H1_BROKER_IPC_TRANSCRIPT_CANDIDATE_V1_DOMAIN
        ),
        "construction_accounting_route_segment_v4_source_authority": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_SOURCE_AUTHORITY_DOMAIN
        ),
        "construction_accounting_route_segment_v4_manifest_authority": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_MANIFEST_AUTHORITY_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owner_blocker": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNER_BLOCKER_DOMAIN
        ),
        "construction_accounting_route_segment_v4_start": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_START_DOMAIN
        ),
        "construction_accounting_route_segment_v4_event": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_EVENT_DOMAIN
        ),
        "construction_accounting_route_segment_v4_terminal": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TERMINAL_DOMAIN
        ),
        "construction_accounting_route_segment_v4_transcript": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_TRANSCRIPT_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_engine_source": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_SOURCE_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_engine_boundary": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_BOUNDARY_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_engine_authority": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_ENGINE_AUTHORITY_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_start": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_START_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_event": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_EVENT_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_execution_binding": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_EXECUTION_BINDING_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_structural_semantics": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_STRUCTURAL_SEMANTICS_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_kernel_semantics": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_KERNEL_SEMANTICS_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_query_semantics": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_QUERY_SEMANTICS_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_threshold_semantics": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_THRESHOLD_SEMANTICS_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_reward_semantics": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_REWARD_SEMANTICS_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_policy_class": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_POLICY_CLASS_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_search_profile": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_PROFILE_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_search_semantics": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_SEARCH_SEMANTICS_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_g2048_transition_closure": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_G2048_TRANSITION_CLOSURE_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_terminal": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_TERMINAL_DOMAIN
        ),
        "construction_accounting_route_segment_v4_owned_transcript": (
            CONSTRUCTION_ACCOUNTING_ROUTE_SEGMENT_V4_OWNED_TRANSCRIPT_DOMAIN
        ),
        "construction_owner_boundary_site_closure_v1": (
            CONSTRUCTION_OWNER_BOUNDARY_SITE_CLOSURE_V1_DOMAIN
        ),
        "construction_owner_path_counter_candidate_v1": (
            CONSTRUCTION_OWNER_PATH_COUNTER_CANDIDATE_V1_DOMAIN
        ),
        "construction_owner_event_candidate_set_v1": (
            CONSTRUCTION_OWNER_EVENT_CANDIDATE_SET_V1_DOMAIN
        ),
        "construction_owner_event_execution_binding_v1": (
            CONSTRUCTION_OWNER_EVENT_EXECUTION_BINDING_V1_DOMAIN
        ),
        "construction_owner_source_code_identity_v1": (
            CONSTRUCTION_OWNER_SOURCE_CODE_IDENTITY_V1_DOMAIN
        ),
        "construction_owner_postexec_binding_v1": (
            CONSTRUCTION_OWNER_POSTEXEC_BINDING_V1_DOMAIN
        ),
        "construction_k7_reconciliation_formula_authority_v1": (
            CONSTRUCTION_K7_RECONCILIATION_FORMULA_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_reconciliation_arithmetic_replay_v1": (
            CONSTRUCTION_K7_RECONCILIATION_ARITHMETIC_REPLAY_V1_DOMAIN
        ),
        "construction_k7_reconciliation_semantic_dependency_v1": (
            CONSTRUCTION_K7_RECONCILIATION_SEMANTIC_DEPENDENCY_V1_DOMAIN
        ),
        "construction_k7_reconciliation_path_proof_v1": (
            CONSTRUCTION_K7_RECONCILIATION_PATH_PROOF_V1_DOMAIN
        ),
        "construction_k7_reconciliation_blocker_v1": (
            CONSTRUCTION_K7_RECONCILIATION_BLOCKER_V1_DOMAIN
        ),
        "construction_k7_reconciliation_readiness_v1": (
            CONSTRUCTION_K7_RECONCILIATION_READINESS_V1_DOMAIN
        ),
        "construction_k7_occurrence_identity_semantic_authority_v2": (
            CONSTRUCTION_K7_OCCURRENCE_IDENTITY_SEMANTIC_AUTHORITY_V2_DOMAIN
        ),
        "construction_k7_operational_cutoff_semantic_authority_v2": (
            CONSTRUCTION_K7_OPERATIONAL_CUTOFF_SEMANTIC_AUTHORITY_V2_DOMAIN
        ),
        "construction_k7_occurrence_cutoff_semantic_authority_bundle_v2": (
            CONSTRUCTION_K7_OCCURRENCE_CUTOFF_SEMANTIC_AUTHORITY_BUNDLE_V2_DOMAIN
        ),
        "construction_k7_production_measurement_start_v2": (
            CONSTRUCTION_K7_PRODUCTION_MEASUREMENT_START_V2_DOMAIN
        ),
        "construction_k7_production_measurement_cutoff_v2": (
            CONSTRUCTION_K7_PRODUCTION_MEASUREMENT_CUTOFF_V2_DOMAIN
        ),
        "construction_k7_production_terminal_closure_v2": (
            CONSTRUCTION_K7_PRODUCTION_TERMINAL_CLOSURE_V2_DOMAIN
        ),
        "construction_k7_route_terminal_semantic_dependency_v2": (
            CONSTRUCTION_K7_ROUTE_TERMINAL_SEMANTIC_DEPENDENCY_V2_DOMAIN
        ),
        "construction_k7_exact_route_derived_path_proof_v2": (
            CONSTRUCTION_K7_EXACT_ROUTE_DERIVED_PATH_PROOF_V2_DOMAIN
        ),
        "construction_k7_complete_derived_reconciliation_readiness_v2": (
            CONSTRUCTION_K7_COMPLETE_DERIVED_RECONCILIATION_READINESS_V2_DOMAIN
        ),
        "construction_k7_native_zero_source_hook_inventory_v1": (
            CONSTRUCTION_K7_NATIVE_ZERO_SOURCE_HOOK_INVENTORY_V1_DOMAIN
        ),
        "construction_k7_native_zero_owner_window_closure_v1": (
            CONSTRUCTION_K7_NATIVE_ZERO_OWNER_WINDOW_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_native_zero_stage_evidence_v1": (
            CONSTRUCTION_K7_NATIVE_ZERO_STAGE_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_native_zero_branch_evidence_v1": (
            CONSTRUCTION_K7_NATIVE_ZERO_BRANCH_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_native_zero_replacement_evidence_v1": (
            CONSTRUCTION_K7_NATIVE_ZERO_REPLACEMENT_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_native_zero_semantic_verifier_v1": (
            CONSTRUCTION_K7_NATIVE_ZERO_SEMANTIC_VERIFIER_V1_DOMAIN
        ),
        "construction_k7_profile_native_zero_attestation_v1": (
            CONSTRUCTION_K7_PROFILE_NATIVE_ZERO_ATTESTATION_V1_DOMAIN
        ),
        "construction_k7_profile_native_zero_envelope_v1": (
            CONSTRUCTION_K7_PROFILE_NATIVE_ZERO_ENVELOPE_V1_DOMAIN
        ),
        "construction_k7_semantic_path_recorder_authority_v1": (
            CONSTRUCTION_K7_SEMANTIC_PATH_RECORDER_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_semantic_path_resolution_v1": (
            CONSTRUCTION_K7_SEMANTIC_PATH_RESOLUTION_V1_DOMAIN
        ),
        "construction_k7_semantic_evidence_closure_context_v1": (
            CONSTRUCTION_K7_SEMANTIC_EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN
        ),
        "construction_k7_semantic_evidence_closure_v1": (
            CONSTRUCTION_K7_SEMANTIC_EVIDENCE_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_formal_actual_projection_proof_v6": (
            CONSTRUCTION_K7_FORMAL_ACTUAL_PROJECTION_PROOF_V6_DOMAIN
        ),
        "construction_k7_formal_accounting_materialization_bundle_v1": (
            CONSTRUCTION_K7_FORMAL_ACCOUNTING_MATERIALIZATION_BUNDLE_V1_DOMAIN
        ),
        "construction_k7_root_cap_semantics_profile_v1": (
            CONSTRUCTION_K7_ROOT_CAP_SEMANTICS_PROFILE_V1_DOMAIN
        ),
        "construction_k7_root_cap_exhaustion_evidence_v1": (
            CONSTRUCTION_K7_ROOT_CAP_EXHAUSTION_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_root_cap_attempt_terminal_authority_v1": (
            CONSTRUCTION_K7_ROOT_CAP_ATTEMPT_TERMINAL_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_root_cap_terminal_accounting_bundle_v1": (
            CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_BUNDLE_V1_DOMAIN
        ),
        "construction_k7_root_cap_terminal_accounting_verification_v1": (
            CONSTRUCTION_K7_ROOT_CAP_TERMINAL_ACCOUNTING_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_production_complete_bundle_verification_profile_v1": (
            CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_production_complete_bundle_semantic_verifier_v1": (
            CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_SEMANTIC_VERIFIER_V1_DOMAIN
        ),
        "construction_k7_production_complete_bundle_evaluation_recorder_v1": (
            CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_EVALUATION_RECORDER_V1_DOMAIN
        ),
        "construction_k7_production_complete_bundle_verification_v1": (
            CONSTRUCTION_K7_PRODUCTION_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_logical_occurrence_work_sum_v1": (
            CONSTRUCTION_K7_LOGICAL_OCCURRENCE_WORK_SUM_V1_DOMAIN
        ),
        "construction_k7_logical_occurrence_closure_authority_v1": (
            CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_logical_occurrence_closure_bundle_v1": (
            CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN
        ),
        "construction_k7_logical_occurrence_closure_verification_v1": (
            CONSTRUCTION_K7_LOGICAL_OCCURRENCE_CLOSURE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_campaign_registration_v1": (
            CONSTRUCTION_K7_CAMPAIGN_REGISTRATION_V1_DOMAIN
        ),
        "construction_k7_campaign_occurrence_row_v1": (
            CONSTRUCTION_K7_CAMPAIGN_OCCURRENCE_ROW_V1_DOMAIN
        ),
        "construction_k7_campaign_closure_summary_v1": (
            CONSTRUCTION_K7_CAMPAIGN_CLOSURE_SUMMARY_V1_DOMAIN
        ),
        "construction_k7_campaign_closure_verification_v1": (
            CONSTRUCTION_K7_CAMPAIGN_CLOSURE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_terminal_accounting_coverage_source_v1": (
            CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_SOURCE_V1_DOMAIN
        ),
        "construction_k7_terminal_accounting_coverage_row_v1": (
            CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_ROW_V1_DOMAIN
        ),
        "construction_k7_terminal_accounting_coverage_matrix_v1": (
            CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_MATRIX_V1_DOMAIN
        ),
        "construction_k7_terminal_accounting_coverage_replay_v1": (
            CONSTRUCTION_K7_TERMINAL_ACCOUNTING_COVERAGE_REPLAY_V1_DOMAIN
        ),
        "construction_k7_all_path_accounting_profile_v1": (
            CONSTRUCTION_K7_ALL_PATH_ACCOUNTING_PROFILE_V1_DOMAIN
        ),
        "construction_k7_all_path_accounting_profile_replay_v1": (
            CONSTRUCTION_K7_ALL_PATH_ACCOUNTING_PROFILE_REPLAY_V1_DOMAIN
        ),
        "construction_k7_v075_terminal_status_inventory_v1": (
            CONSTRUCTION_K7_V075_TERMINAL_STATUS_INVENTORY_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_durable_proof_v1": (
            PHASE3E_EXACT_INFEASIBILITY_DURABLE_PROOF_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_identity_v1": (
            PHASE3E_EXACT_INFEASIBILITY_IDENTITY_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_structural_v1": (
            PHASE3E_EXACT_INFEASIBILITY_STRUCTURAL_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_query_v1": (
            PHASE3E_EXACT_INFEASIBILITY_QUERY_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_kernel_v1": (
            PHASE3E_EXACT_INFEASIBILITY_KERNEL_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_build_epoch_v1": (
            PHASE3E_EXACT_INFEASIBILITY_BUILD_EPOCH_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_threshold_v1": (
            PHASE3E_EXACT_INFEASIBILITY_THRESHOLD_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_reward_v1": (
            PHASE3E_EXACT_INFEASIBILITY_REWARD_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_policy_class_v1": (
            PHASE3E_EXACT_INFEASIBILITY_POLICY_CLASS_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_search_profile_v1": (
            PHASE3E_EXACT_INFEASIBILITY_SEARCH_PROFILE_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_state_v1": (
            PHASE3E_EXACT_INFEASIBILITY_STATE_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_state_action_v1": (
            PHASE3E_EXACT_INFEASIBILITY_STATE_ACTION_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_source_projection_v1": (
            PHASE3E_EXACT_INFEASIBILITY_SOURCE_PROJECTION_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_verification_profile_v1": (
            PHASE3E_EXACT_INFEASIBILITY_VERIFICATION_PROFILE_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_verification_v1": (
            PHASE3E_EXACT_INFEASIBILITY_VERIFICATION_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_cache_consumption_v1": (
            PHASE3E_EXACT_INFEASIBILITY_CACHE_CONSUMPTION_V1_DOMAIN
        ),
        "phase3e_exact_infeasibility_blocker_v1": (
            PHASE3E_EXACT_INFEASIBILITY_BLOCKER_V1_DOMAIN
        ),
        "construction_k7_expected_artifact_identity_v1": (
            CONSTRUCTION_K7_EXPECTED_ARTIFACT_IDENTITY_V1_DOMAIN
        ),
        "construction_k7_integrity_attempt_context_v1": (
            CONSTRUCTION_K7_INTEGRITY_ATTEMPT_CONTEXT_V1_DOMAIN
        ),
        "construction_k7_integrity_access_event_v1": (
            CONSTRUCTION_K7_INTEGRITY_ACCESS_EVENT_V1_DOMAIN
        ),
        "construction_k7_integrity_read_receipt_v1": (
            CONSTRUCTION_K7_INTEGRITY_READ_RECEIPT_V1_DOMAIN
        ),
        "construction_k7_integrity_access_sequence_v1": (
            CONSTRUCTION_K7_INTEGRITY_ACCESS_SEQUENCE_V1_DOMAIN
        ),
        "construction_k7_integrity_prefix_recorder_v1": (
            CONSTRUCTION_K7_INTEGRITY_PREFIX_RECORDER_V1_DOMAIN
        ),
        "construction_k7_integrity_prefix_completeness_v1": (
            CONSTRUCTION_K7_INTEGRITY_PREFIX_COMPLETENESS_V1_DOMAIN
        ),
        "construction_k7_integrity_terminal_authority_v1": (
            CONSTRUCTION_K7_INTEGRITY_TERMINAL_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_integrity_failure_bundle_v1": (
            CONSTRUCTION_K7_INTEGRITY_FAILURE_BUNDLE_V1_DOMAIN
        ),
        "construction_k7_integrity_failure_verification_v1": (
            CONSTRUCTION_K7_INTEGRITY_FAILURE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_all_path_operation_boundary_manifest_v1": (
            CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_MANIFEST_V1_DOMAIN
        ),
        "construction_k7_all_path_operation_boundary_source_archive_v1": (
            CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_SOURCE_ARCHIVE_V1_DOMAIN
        ),
        "construction_k7_all_path_operation_boundary_site_v1": (
            CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_SITE_V1_DOMAIN
        ),
        "construction_k7_all_path_operation_boundary_replay_v1": (
            CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_REPLAY_V1_DOMAIN
        ),
        "construction_k7_all_path_operation_boundary_blocker_v1": (
            CONSTRUCTION_K7_ALL_PATH_OPERATION_BOUNDARY_BLOCKER_V1_DOMAIN
        ),
        "construction_k7_protocol_real_site_blocker_v1": (
            CONSTRUCTION_K7_PROTOCOL_REAL_SITE_BLOCKER_V1_DOMAIN
        ),
        "construction_k7_protocol_prefix_recorder_v1": (
            CONSTRUCTION_K7_PROTOCOL_PREFIX_RECORDER_V1_DOMAIN
        ),
        "construction_k7_protocol_failure_terminal_authority_v1": (
            CONSTRUCTION_K7_PROTOCOL_FAILURE_TERMINAL_AUTHORITY_V1_DOMAIN
        ),
        "construction_k7_protocol_failure_bundle_v1": (
            CONSTRUCTION_K7_PROTOCOL_FAILURE_BUNDLE_V1_DOMAIN
        ),
        "construction_k7_protocol_failure_verification_v1": (
            CONSTRUCTION_K7_PROTOCOL_FAILURE_VERIFICATION_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_source_archive_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_SOURCE_ARCHIVE_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_path_gap_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_PATH_GAP_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_coverage_report_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COVERAGE_REPORT_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_source_blocker_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_SOURCE_BLOCKER_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_coverage_replay_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COVERAGE_REPLAY_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_zero_execution_window_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_EXECUTION_WINDOW_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_zero_value_proof_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_PROOF_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_residual_gap_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_RESIDUAL_GAP_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_zero_value_closure_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_CLOSURE_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_zero_value_replay_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_ZERO_VALUE_REPLAY_V1_DOMAIN
        ),
        "construction_k7_direct_fallback_exact_infeasibility_readiness_v1": (
            CONSTRUCTION_K7_DIRECT_FALLBACK_EXACT_INFEASIBILITY_READINESS_V1_DOMAIN
        ),
        "construction_k7_canonical_infeasible_fallback_preexecution_v1": (
            CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN
        ),
        "construction_k7_canonical_infeasible_fallback_current_identity_v1": (
            CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CURRENT_IDENTITY_V1_DOMAIN
        ),
        "construction_k7_canonical_infeasible_fallback_cardinality_source_v1": (
            CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CARDINALITY_SOURCE_V1_DOMAIN
        ),
        "construction_k7_canonical_infeasible_fallback_transition_trace_v1": (
            CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_TRANSITION_TRACE_V1_DOMAIN
        ),
        "construction_k7_canonical_infeasible_fallback_path_evidence_v1": (
            CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PATH_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_canonical_infeasible_fallback_acquisition_v1": (
            CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_ACQUISITION_V1_DOMAIN
        ),
        "construction_k7_canonical_infeasible_fallback_support_v1": (
            CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_SUPPORT_V1_DOMAIN
        ),
        "construction_k7_abstract_pass_retained_v1_inventory_context_v1": (
            CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_INVENTORY_CONTEXT_V1_DOMAIN
        ),
        "construction_k7_abstract_pass_legacy_shared_aggregate_claim_v1": (
            CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_SHARED_AGGREGATE_CLAIM_V1_DOMAIN
        ),
        "construction_k7_abstract_pass_legacy_owner_event_candidate_v1": (
            CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_OWNER_EVENT_CANDIDATE_V1_DOMAIN
        ),
        "construction_k7_abstract_pass_legacy_reconciliation_claim_v1": (
            CONSTRUCTION_K7_ABSTRACT_PASS_LEGACY_RECONCILIATION_CLAIM_V1_DOMAIN
        ),
        "construction_k7_abstract_pass_retained_v1_formal_blocker_v1": (
            CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_FORMAL_BLOCKER_V1_DOMAIN
        ),
        "construction_k7_abstract_pass_retained_v1_evidence_inventory_v1": (
            CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_EVIDENCE_INVENTORY_V1_DOMAIN
        ),
        "construction_k7_abstract_pass_retained_v1_inventory_replay_v1": (
            CONSTRUCTION_K7_ABSTRACT_PASS_RETAINED_V1_INVENTORY_REPLAY_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_query_owner_window_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_WINDOW_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_query_owner_resolution_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_RESOLUTION_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_query_owner_envelope_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_ENVELOPE_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_query_owner_replay_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_QUERY_OWNER_REPLAY_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_lifecycle_window_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_WINDOW_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_lifecycle_resolution_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_RESOLUTION_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_lifecycle_envelope_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_ENVELOPE_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_lifecycle_replay_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_LIFECYCLE_REPLAY_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_common_shared_window_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_WINDOW_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_common_shared_resolution_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_RESOLUTION_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_common_shared_envelope_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_ENVELOPE_V1_DOMAIN
        ),
        "construction_k7_abstract_certified_common_shared_replay_v1": (
            CONSTRUCTION_K7_ABSTRACT_CERTIFIED_COMMON_SHARED_REPLAY_V1_DOMAIN
        ),
        "construction_k7_abstract_accounted_runtime_preparation_v2": (
            CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_RUNTIME_PREPARATION_V2_DOMAIN
        ),
        "construction_k7_abstract_accounted_worker_output_v2": (
            CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_WORKER_OUTPUT_V2_DOMAIN
        ),
        "construction_k7_abstract_accounted_measurement_window_v2": (
            CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_MEASUREMENT_WINDOW_V2_DOMAIN
        ),
        "construction_k7_abstract_accounted_shared_resolution_v2": (
            CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_RESOLUTION_V2_DOMAIN
        ),
        "construction_k7_abstract_accounted_shared_envelope_v2": (
            CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_ENVELOPE_V2_DOMAIN
        ),
        "construction_k7_abstract_accounted_shared_replay_v2": (
            CONSTRUCTION_K7_ABSTRACT_ACCOUNTED_SHARED_REPLAY_V2_DOMAIN
        ),
        "construction_k7_abstract_query_zero_runtime_window_v1": (
            CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_RUNTIME_WINDOW_V1_DOMAIN
        ),
        "construction_k7_abstract_query_zero_resolution_v1": (
            CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_RESOLUTION_V1_DOMAIN
        ),
        "construction_k7_abstract_query_zero_envelope_v1": (
            CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_ENVELOPE_V1_DOMAIN
        ),
        "construction_k7_abstract_query_zero_replay_v1": (
            CONSTRUCTION_K7_ABSTRACT_QUERY_ZERO_REPLAY_V1_DOMAIN
        ),
        "construction_k7_conditional_terminal_normalization_profile_v1": (
            CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_PROFILE_V1_DOMAIN
        ),
        "construction_k7_conditional_terminal_normalization_rule_v1": (
            CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_RULE_V1_DOMAIN
        ),
        "construction_k7_conditional_terminal_normalization_evidence_v1": (
            CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_EVIDENCE_V1_DOMAIN
        ),
        "construction_k7_conditional_terminal_normalization_result_v1": (
            CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_RESULT_V1_DOMAIN
        ),
        "construction_k7_conditional_terminal_normalization_replay_v1": (
            CONSTRUCTION_K7_CONDITIONAL_TERMINAL_NORMALIZATION_REPLAY_V1_DOMAIN
        ),
        "construction_k7_v075_plan_route_provenance_v1": (
            CONSTRUCTION_K7_V075_PLAN_ROUTE_PROVENANCE_V1_DOMAIN
        ),
        "construction_k7_v075_plan_route_normalization_binding_v1": (
            CONSTRUCTION_K7_V075_PLAN_ROUTE_NORMALIZATION_BINDING_V1_DOMAIN
        ),
        "construction_k7_v075_plan_route_provenance_replay_v1": (
            CONSTRUCTION_K7_V075_PLAN_ROUTE_PROVENANCE_REPLAY_V1_DOMAIN
        ),
        "construction_k7_v075_batched_causal_route_provenance_v1": (
            CONSTRUCTION_K7_V075_BATCHED_CAUSAL_ROUTE_PROVENANCE_V1_DOMAIN
        ),
        "construction_k7_v075_batched_causal_route_normalization_binding_v1": (
            CONSTRUCTION_K7_V075_BATCHED_CAUSAL_ROUTE_NORMALIZATION_BINDING_V1_DOMAIN
        ),
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
        "v072_anchored_campaign_attempt_failure": (
            V072_ANCHORED_CAMPAIGN_ATTEMPT_FAILURE_DOMAIN
        ),
        "v072_registered_campaign_attempt_journal": (
            V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_DOMAIN
        ),
        "v072_registered_campaign_attempt_journal_object": (
            V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_OBJECT_DOMAIN
        ),
        "v072_registered_campaign_attempt_journal_event": (
            V072_REGISTERED_CAMPAIGN_ATTEMPT_JOURNAL_EVENT_DOMAIN
        ),
        "frozen_source_archive_envelope": (
            FROZEN_SOURCE_ARCHIVE_ENVELOPE_DOMAIN
        ),
        "frozen_source_offline_work": (
            FROZEN_SOURCE_OFFLINE_WORK_DOMAIN
        ),
        "frozen_source_occurrence_input": (
            FROZEN_SOURCE_OCCURRENCE_INPUT_DOMAIN
        ),
        "frozen_source_occurrence_output": (
            FROZEN_SOURCE_OCCURRENCE_OUTPUT_DOMAIN
        ),
        "frozen_source_child_attempt_journal": (
            FROZEN_SOURCE_CHILD_ATTEMPT_JOURNAL_DOMAIN
        ),
        "frozen_source_occurrence_failure_closure": (
            FROZEN_SOURCE_OCCURRENCE_FAILURE_CLOSURE_DOMAIN
        ),
        "frozen_source_occurrence_merge": (
            FROZEN_SOURCE_OCCURRENCE_MERGE_DOMAIN
        ),
        "frozen_source_verification_attestation": (
            FROZEN_SOURCE_VERIFICATION_ATTESTATION_DOMAIN
        ),
        "frozen_source_execution_batch": (
            FROZEN_SOURCE_EXECUTION_BATCH_DOMAIN
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


def _unlimited_decimal_integer(value: int) -> str:
    """Render an internally bounded exact integer without Python's digit cap."""

    if type(value) is not int:
        raise Phase3EIdentityError("canonical integer renderer received non-int")
    if value == 0:
        return "0"
    # 100,000 decimal digits require fewer than 332,194 binary digits.
    if abs(value).bit_length() > 332_193:
        raise Phase3EIdentityError(
            "canonical integer exceeds the local decimal-digit ceiling"
        )
    sign = "-" if value < 0 else ""
    remaining = abs(value)
    base = 1_000_000_000
    chunks: list[int] = []
    while remaining:
        remaining, chunk = divmod(remaining, base)
        chunks.append(chunk)
    rendered = sign + str(chunks[-1]) + "".join(
        f"{chunk:09d}" for chunk in reversed(chunks[:-1])
    )
    if len(rendered) - len(sign) > MAX_CANONICAL_INTEGER_DECIMAL_DIGITS:
        raise Phase3EIdentityError(
            "canonical integer exceeds the local decimal-digit ceiling"
        )
    return rendered


def _unlimited_canonical_json_text(value: Any) -> str:
    """Serialize normalized JSON while preserving stdlib canonical bytes."""

    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if type(value) is int:
        return _unlimited_decimal_integer(value)
    if type(value) in {str, float}:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    if type(value) is list:
        return "[" + ",".join(
            _unlimited_canonical_json_text(item) for item in value
        ) + "]"
    if type(value) is dict:
        return "{" + ",".join(
            json.dumps(
                key,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            + ":"
            + _unlimited_canonical_json_text(value[key])
            for key in sorted(value)
        ) + "}"
    raise Phase3EIdentityError(
        "unlimited canonical serializer received an unnormalized value"
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
    except ValueError as error:
        if "Exceeds the limit" not in str(error):
            raise Phase3EIdentityError(
                f"value is not canonical UTF-8 JSON: {error}"
            ) from error
        try:
            return _unlimited_canonical_json_text(normalized).encode(
                "utf-8",
                errors="strict",
            )
        except (UnicodeEncodeError, ValueError) as fallback_error:
            raise Phase3EIdentityError(
                f"value is not canonical UTF-8 JSON: {fallback_error}"
            ) from fallback_error
    except UnicodeEncodeError as error:
        raise Phase3EIdentityError(
            f"value is not canonical UTF-8 JSON: {error}"
        ) from error


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


def _parse_unlimited_decimal_integer(token: str) -> int:
    """Parse a JSON integer without changing Python's process-wide limit."""

    if type(token) is not str or not token:
        raise ValueError("empty canonical integer")
    negative = token[0] == "-"
    digits = token[1:] if negative else token
    if not digits or not digits.isascii() or not digits.isdigit():
        raise ValueError("invalid canonical integer")
    if len(digits) > MAX_CANONICAL_INTEGER_DECIMAL_DIGITS:
        raise ValueError("canonical integer exceeds the local digit ceiling")
    value = 0
    first = len(digits) % 9
    cursor = 0
    if first:
        value = int(digits[:first])
        cursor = first
    while cursor < len(digits):
        value = value * 1_000_000_000 + int(digits[cursor : cursor + 9])
        cursor += 9
    return -value if negative else value


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
            parse_int=_parse_unlimited_decimal_integer,
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
