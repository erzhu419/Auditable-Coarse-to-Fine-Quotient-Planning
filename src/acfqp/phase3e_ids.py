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
