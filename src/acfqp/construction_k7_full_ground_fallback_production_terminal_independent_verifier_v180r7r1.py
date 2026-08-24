"""Producer-free replay of the repaired V180r7r1 fallback occurrence.

The verifier does not import the occurrence finalizer or the materialization
producer.  It reconstructs the three retained V6 accounting chains, the
record-by-record V6-to-V9 lifts, the staged 307-module V2 source closure, the
separate construction-work axis, and the terminal serialization fixed point
from retained bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
from typing import Any, Mapping, NoReturn, Sequence

from acfqp import _v075_construction_source_runtime_v2 as source_runtime_v2
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_accounting_registry_v9 as registry_v9
from acfqp import construction_k7_all_path_production_execution_protocol_v180r3 as consumed_protocol
from acfqp import construction_k7_domain_registry_extension_v180r7r1 as domains
from acfqp import construction_k7_domain_registry_extension_v180r7r1m1 as materialization_domains
from acfqp import construction_k7_domain_registry_extension_v180r7r1p as protocol_domains
from acfqp import (
    construction_k7_recovery_eligible_campaign_independent_verifier_v1
    as source_output_verifier,
)
from acfqp.accounting_v1 import (
    ComparisonVectorV1,
    CounterRecordV1,
    LaneEnum,
    NativeZeroAttestationV1,
    ReducerEnum,
    RouteKindEnum,
    WorkVectorV1,
)
from acfqp.actual_accounting_v1 import (
    ActualProjectionProofV1,
    ActualWorkScope,
    derive_actual_projection_v1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


EXPECTED_TERMINAL_BUNDLE_ID = "0" * 64
EXPECTED_TERMINAL_BYTE_COUNT = 0
EXPECTED_TERMINAL_SHA256 = "0" * 64
EXPECTED_VERIFICATION_ID = "0" * 64
EXPECTED_VERIFICATION_BYTE_COUNT = 0
EXPECTED_VERIFICATION_SHA256 = "0" * 64

_FORMALIZATION_CONTRACT_ID = (
    "f392e9178e8c9c69150567ce210ad146ab96d61aa5925c34b133415fa86737fd"
)
_PRESERVED_V180R7_FAILURE_ID = (
    "bd6e022804f5be7dc7ae22e781ce121fe462277858b058bacf8f201f5b234f79"
)
_SOURCE_CATALOG_MANIFEST_ID = (
    "92e4f36212d957d3701591ee689a23e4446d942c4c3e3b562049290c19ad50d0"
)
_SOURCE_CLOSURE_REPAIR_ID = (
    "feb8f6034ef1da9050242fe4e112edb285b77bd63a87642196f8fbc7995544c8"
)
_SOURCE_CLOSURE_ID = (
    "ac3f10ef4eea5c0ecc740d9cecc1991e851a65af198e6696f32bde1965feeb4b"
)
_REACHABLE_SOURCE_FACTS_SHA256 = (
    "a087ecfac3bcd6132a2242a670b9c38273de3e7bd823b5687e8223a73069772d"
)
_MATERIALIZED_SOURCE_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r7r1_materialized_source"
)
_MATERIALIZATION_MANIFEST_RELATIVE_PATH = (
    ".tmp/exact-freeze/v180r7r1_materialized_source_manifest.json"
)
_MATERIALIZATION_MANIFEST_DOMAIN = (
    materialization_domains.
    CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_MANIFEST_V180R7R1M1_DOMAIN
)
_EXPECTED_REACHABLE_MODULE_COUNT = 307
_EXPECTED_REACHABLE_SOURCE_BYTE_COUNT = 15_129_926
_EXPECTED_SOURCE_DIRECTORY_COUNT_BELOW_ROOT = 6
_EXPECTED_RETAINED_VALIDATION_FILE_READ_COUNT = 16
_EXPECTED_RETAINED_VALIDATION_BYTE_COUNT = 3_765_861
_RETAINED_PREDECESSOR_INPUT_FACTS = (
    {
        "role": "SOURCE_BUNDLE_BINDING",
        "relative_path": (
            ".tmp/recovery-eligible-retained-v1/SOURCE_BUNDLE_BINDING.json"
        ),
        "byte_count": 4_405,
        "sha256": (
            "bf5d7f5292a4b38136b141745b9349bc4e86c2ab7e67592e8d25c19b5daa527f"
        ),
    },
    {
        "role": "REUSABLE_RAPM_SNAPSHOT",
        "relative_path": (
            ".tmp/recovery-eligible-retained-v1/REUSABLE_RAPM_SNAPSHOT.json"
        ),
        "byte_count": 388_638,
        "sha256": (
            "18056b6f1aba853cb3b705041be93bce31700c79d45fa894fd956b144f0e7823"
        ),
    },
    {
        "role": "PROOF_DEPENDENCY_TRANSITION",
        "relative_path": (
            ".tmp/recovery-eligible-retained-v1/PROOF_DEPENDENCY_TRANSITION.json"
        ),
        "byte_count": 859_154,
        "sha256": (
            "e2278f8b499b13f45ab1c8fcba29be9665d472d4cd9ab65e1ee124187bfbbe30"
        ),
    },
)
_LOGICAL_OCCURRENCE_ID = hashlib.sha256(
    b"acfqp:v180r7r1:fresh-full-ground-fallback-occurrence\x00ordinal-7"
).hexdigest()
_QUERY_ORDINAL = 7

_ROUTES = (
    RouteKindEnum.ABSTRACT_FAILED_PREFIX,
    RouteKindEnum.LOCAL_ATTEMPT,
    RouteKindEnum.DIRECT_FALLBACK,
)
_SOURCE_VECTOR_KEY_BY_ROUTE = {
    RouteKindEnum.ABSTRACT_FAILED_PREFIX: "supervised_wrapper_work_vector",
    RouteKindEnum.LOCAL_ATTEMPT: "local_recovery_work_vector",
    RouteKindEnum.DIRECT_FALLBACK: "direct_fallback_work_vector",
}
_SOURCE_COMPARISON_KEY_BY_ROUTE = {
    RouteKindEnum.ABSTRACT_FAILED_PREFIX: "supervised_wrapper_comparison_vector",
    RouteKindEnum.LOCAL_ATTEMPT: "local_recovery_comparison_vector",
    RouteKindEnum.DIRECT_FALLBACK: "direct_fallback_comparison_vector",
}
_SOURCE_PROOF_KEY_BY_ROUTE = {
    RouteKindEnum.ABSTRACT_FAILED_PREFIX: "supervised_wrapper_actual_projection_proof",
    RouteKindEnum.LOCAL_ATTEMPT: "local_recovery_actual_projection_proof",
    RouteKindEnum.DIRECT_FALLBACK: "direct_fallback_actual_projection_proof",
}
_SOURCE_SCOPE_BY_ROUTE = {
    RouteKindEnum.ABSTRACT_FAILED_PREFIX: ActualWorkScope.COMMON_PREFIX,
    RouteKindEnum.LOCAL_ATTEMPT: ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
    RouteKindEnum.DIRECT_FALLBACK: ActualWorkScope.MARGINAL_ROUTE_AGGREGATE,
}
_TARGET_SCOPE_BY_ROUTE = {
    RouteKindEnum.ABSTRACT_FAILED_PREFIX: ActualWorkScope.COMMON_PREFIX,
    RouteKindEnum.LOCAL_ATTEMPT: ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    RouteKindEnum.DIRECT_FALLBACK: ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
}
_OUTPUT_ROLES = (
    "BUSINESS_RESULT",
    "OPERATIONAL_TRACE",
    "TERMINAL_ARTIFACT",
    "COUNTER_RECORD_SET",
    "WORK_VECTOR",
    "COMPARISON_VECTOR",
    "ACTUAL_PROJECTION_PROOF",
    "OUTPUT_MANIFEST",
)
_OUTPUT_FILENAMES = {f"{role}.json" for role in _OUTPUT_ROLES}

_TOP_LEVEL_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "development_fixture_only",
    "fallback_execution_protocol_id",
    "finalizer_output_bytes",
    "fixed_point_iteration",
    "formalization_contract_id",
    "fresh_v180r7r1_observed_occurrence_present",
    "historical_summary_translation_used",
    "materialization_is_separate_one_time_construction_axis",
    "materialization_reference_serialization_is_output_metadata_not_construction_work",
    "materialization_work_charged_to_any_route_component",
    "materialized_source_reference",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "output_bytes_fixed_point",
    "partial_campaign_cannot_unlock_any_gate",
    "production_execution_slot",
    "production_occurrence_receipt",
    "production_terminal_bundle_id",
    "registered_counter_to_counter_v6_to_v9_lift_used",
    "schema",
    "source_occurrence_accounting_bundle",
    "source_output_bytes",
    "source_output_inventory",
    "terminal_code",
    "terminal_serialization_bytes_charged_as_output_bytes",
    "three_route_family_vectors_remain_separate",
    "v9_lifted_route_components",
    "v9_paths_absent_from_source_vector_have_explicit_native_zero_lineage",
}
_RECEIPT_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "execution_nonce",
    "fallback_execution_protocol_id",
    "historical_summary_translation_used",
    "logical_occurrence_id",
    "materialization_is_separate_one_time_construction_axis",
    "materialization_work_charged_to_any_route_component",
    "materialized_source_reference",
    "native_v6_counter_records_used",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "predecessor_occurrence_slot_id",
    "preexisting_occurrence_output_used",
    "production_execution_slot_id",
    "production_execution_started_by_this_call",
    "production_occurrence_receipt_id",
    "query_ordinal",
    "registered_v6_to_v9_counter_lift_required",
    "retained_predecessor_input_facts",
    "schema",
    "source_counter_registry_id",
    "source_occurrence_accounting_bundle_id",
    "source_output_bytes",
    "source_output_inventory",
    "source_route_components",
    "source_shared_resource_receipt_ids",
    "source_work_vector_ids",
    "target_counter_registry_id",
    "terminal_code",
    "three_route_components_independent",
}
_REFERENCE_FIELDS = {
    "charged_to_any_route_component",
    "construction_work",
    "materialization_manifest_canonical_byte_count",
    "materialization_manifest_canonical_sha256",
    "materialization_manifest_id",
    "materialized_source_byte_count",
    "materialized_source_module_count",
    "materialized_source_relative_path",
    "materialized_source_tree_id",
    "one_time_construction_axis",
    "schema",
    "scientific_occurrence_execution_work",
    "source_catalog_manifest_id",
    "source_closure_id",
    "source_closure_repair_id",
}
_SOURCE_ROUTE_COMPONENT_FIELDS = {
    "independent_route_component",
    "route_kind",
    "source_actual_projection_proof_id",
    "source_comparison_vector_id",
    "source_work_vector_id",
}
_COMPONENT_FIELDS = {
    "counter_lift_lineage",
    "independent_route_component",
    "materialized_source_construction_work_charged_to_component",
    "source_work_vector",
    "v9_actual_projection_proof",
    "v9_comparison_vector",
    "v9_native_zero_attestation",
    "v9_work_vector",
}
_LINEAGE_FIELDS = {
    "finalizer_output_increment",
    "historical_summary_translation_used",
    "inherited_semantics_exact",
    "lineage_id",
    "materialized_source_construction_work_charged_to_this_route",
    "path",
    "route_kind",
    "schema",
    "source_counter_record_id",
    "source_counter_registry_id",
    "source_value",
    "source_value_plus_finalizer_increment_equals_target_value",
    "source_work_vector_id",
    "target_counter_record_id",
    "target_counter_registry_id",
    "target_path_absent_from_source_vector_native_zero_observation",
    "value",
}
_MATERIALIZATION_MANIFEST_FIELDS = {
    "BREAK_EVEN_GATE",
    "COUNTER_COMPLETENESS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "comparison_vectors_issued",
    "construction_only",
    "construction_producer_source_facts",
    "construction_work",
    "counter_records_issued",
    "directory_fsync_required",
    "fallback_occurrence_started",
    "file_fsync_required",
    "fresh_execution_authorization_issued",
    "manifest_output_relative_path",
    "materialization_manifest_domain",
    "materialization_manifest_id",
    "materialized_root_relative_path",
    "materialized_source_tree",
    "materialized_source_tree_id",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "producer_free_verification_present",
    "production_outcome_accessed",
    "route_work_vectors_issued",
    "same_materialization_identity_rerun_after_progress_forbidden",
    "schema",
    "scientific_occurrence_executed",
    "source_boundary_commit",
    "source_catalog_manifest_canonical_byte_count",
    "source_catalog_manifest_canonical_sha256",
    "source_catalog_manifest_id",
    "source_closure_repair_id",
    "source_inventory_preregistration_id",
    "success_claimed",
    "unchanged_v2_source_closure",
    "unchanged_v2_source_closure_id",
    "write_once_o_excl_required",
}
_MATERIALIZED_TREE_FIELDS = {
    "candidate_catalog_unreachable_files_materialized",
    "construction_only",
    "materialized_root_relative_path",
    "materialized_source_byte_count",
    "materialized_source_file_count",
    "materialized_source_root_relative_path",
    "materialized_source_tree_domain",
    "materialized_source_tree_id",
    "only_exact_reachable_source_facts_materialized",
    "reachable_source_facts",
    "reachable_source_facts_sha256",
    "schema",
    "source_boundary_commit",
    "source_bytes_executed",
    "source_catalog_manifest_id",
    "source_closure_id",
    "source_closure_repair_id",
    "source_inventory_preregistration_id",
}
_CONSTRUCTION_WORK_FIELDS = {
    "construction_producer_identity_reads",
    "construction_work_excluded_from_occurrence_route_vectors",
    "directory_fsync_count",
    "durable_file_write_byte_count",
    "durable_file_write_count",
    "file_fsync_count",
    "live_reachable_source_reads",
    "materialization_manifest_write",
    "materialized_source_writes",
    "materialized_tree_directories",
    "occurrence_comparison_vector_count",
    "occurrence_counter_record_count",
    "occurrence_route_work_vector_count",
    "retained_identity_validation_reads",
    "scope",
    "semantic_file_read_byte_count",
    "semantic_file_read_count",
    "unchanged_v2_materialized_source_replay_reads",
}
_PROTOCOL_FIELDS = {
    "BREAK_EVEN_GATE",
    "COUNTER_COMPLETENESS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "concurrent_workspace_mutation_during_one_shot_occurrence_out_of_scope",
    "construction_only",
    "consumed_v180r3_slot_reused",
    "consumed_v180r7_authorization_reused",
    "counter_record_work_vector_comparison_vector_required",
    "fallback_execution_protocol_id",
    "fresh_process_or_occurrence_boundary_required",
    "fresh_production_occurrence_count",
    "historical_summary_to_counter_translation_forbidden",
    "materialization_manifest_id",
    "materialized_construction_work_is_separate_from_route_vectors",
    "materialized_source_tree_id",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "one_isolated_worker_no_concurrent_campaign",
    "output_fixed_point_required",
    "partial_campaign_cannot_unlock_any_gate",
    "predecessor_production_execution_protocol_id",
    "preserved_v180r7_authorization_id",
    "preserved_v180r7_failure_id",
    "producer_free_replay_required",
    "production_execution_slot",
    "production_outcome_accessed",
    "protocol_frozen_before_any_v180r7r1_outcome",
    "registered_record_to_record_v6_to_v9_lift_required",
    "same_failed_identity_rerun_forbidden",
    "schema",
    "singular_fresh_slot_count",
    "source_closure_repair_id",
    "unchanged_v2_source_closure_id",
}
_AUTHORIZATION_FIELDS = {
    "BREAK_EVEN_GATE",
    "COUNTER_COMPLETENESS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "address_space_hard_cap_bytes",
    "authorization_self_source_bound_by_post_prereg_freeze",
    "concurrent_workspace_mutation_during_one_shot_occurrence_out_of_scope",
    "contract_source_fact_static_import_roots",
    "entrypoint",
    "failed_v180r7_authorization_reused",
    "failure_must_be_written_once",
    "failure_relative_path",
    "fallback_execution_authorization_id",
    "fallback_execution_protocol_id",
    "fresh_fallback_execution_started",
    "historical_summary_to_counter_translation_forbidden",
    "independent_verification_required_after_success",
    "logical_occurrence_id",
    "materialization_manifest_id",
    "materialized_construction_work_charged_to_route_vectors",
    "materialized_source_tree_id",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "one_isolated_worker_no_concurrent_campaign",
    "one_worker_process_required",
    "outcome_free",
    "output_root_must_be_absent",
    "output_root_relative_path",
    "post_prereg_authorization_evidence_freeze_required",
    "preserved_v180r7_authorization_id",
    "preserved_v180r7_failure_id",
    "production_execution_slot",
    "production_outcome_accessed",
    "production_source_fact_static_import_roots",
    "query_ordinal",
    "registered_record_to_record_v6_to_v9_lift_required",
    "resource_caps",
    "retained_predecessor_input_facts",
    "runner_relative_path",
    "runtime_cas_root_must_be_absent",
    "runtime_cas_root_relative_path",
    "same_authorization_rerun_after_progress_or_terminal_forbidden",
    "same_failed_authorization_rerun_forbidden",
    "schema",
    "self_identity_cycle_avoided",
    "source_catalog_manifest_id",
    "source_closure_repair_id",
    "source_fact_byte_count",
    "source_fact_closure_rule",
    "source_fact_exclusions",
    "source_fact_file_count",
    "source_facts",
    "source_facts_sha256",
    "terminal_must_be_written_once",
    "terminal_relative_path",
    "three_route_family_vectors_must_remain_separate",
    "timeout_seconds",
    "unchanged_v2_source_closure_id",
    "verification_relative_path",
    "verification_source_fact_static_import_roots",
}
_AUTHORIZATION_EVIDENCE_FIELDS = {
    "BREAK_EVEN_GATE",
    "COUNTER_COMPLETENESS_GATE",
    "SCALAR_CALIBRATION_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "authorization_canonical_byte_count",
    "authorization_canonical_sha256",
    "authorization_evidence_domain",
    "authorization_evidence_id",
    "authorization_preregistered_before_this_evidence",
    "authorization_self_source_bound_by_this_evidence",
    "authorization_source_fact",
    "evidence_wrapper_self_source_excluded_to_avoid_identity_cycle",
    "execution_chain_source_facts",
    "fallback_execution_authorization_id",
    "fallback_execution_protocol_id",
    "fresh_production_occurrence_count",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "outcome_free",
    "production_outcome_accessed",
    "schema",
    "source_fact_exclusions",
}


class ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error(
    RuntimeError
):
    """The repaired fallback evidence or producer-free replay changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error(
        message
    )


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError, UnicodeError) as error:
        raise ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _fresh_protocol() -> tuple[Any, dict[str, Any], dict[str, Any]]:
    from acfqp import (  # noqa: PLC0415
        construction_k7_full_ground_fallback_execution_protocol_v180r7r1
        as protocol,
    )

    frozen = protocol.freeze_full_ground_fallback_execution_protocol_v180r7r1()
    document = frozen.to_document()
    slot = document.get("production_execution_slot")
    protocol_payload = dict(document)
    protocol_id = protocol_payload.pop("fallback_execution_protocol_id", None)
    if not (
        type(document) is dict
        and set(document) == _PROTOCOL_FIELDS
        and canonical_json_bytes(document) == frozen.canonical_bytes
        and frozen.protocol_id == protocol.EXPECTED_PROTOCOL_ID
        and protocol_id == protocol.EXPECTED_PROTOCOL_ID
        and protocol_id
        == protocol_domains.extension_content_id_v180r7r1p(
            protocol_domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_PROTOCOL_V180R7R1P_DOMAIN,
            protocol_payload,
        )
        and len(frozen.canonical_bytes) == protocol.EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(frozen.canonical_bytes).hexdigest()
        == protocol.EXPECTED_CANONICAL_SHA256
        and type(slot) is dict
        and slot.get("terminal_code") == "FULL_GROUND_FALLBACK"
        and slot.get("logical_occurrence_id") == _LOGICAL_OCCURRENCE_ID
        and slot.get("query_ordinal") == _QUERY_ORDINAL
        and slot.get("preserved_v180r7_failure_id")
        == _PRESERVED_V180R7_FAILURE_ID
        and slot.get("source_closure_repair_id") == _SOURCE_CLOSURE_REPAIR_ID
        and type(slot.get("production_execution_slot_id")) is str
        and type(slot.get("execution_nonce")) is str
        and document.get("production_outcome_accessed") is False
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
        and document.get("one_isolated_worker_no_concurrent_campaign") is True
        and document.get(
            "concurrent_workspace_mutation_during_one_shot_occurrence_out_of_scope"
        )
        is True
    ):
        _fail("fresh V180r7r1 execution protocol changed")
    consumed_rows = [
        row
        for row in consumed_protocol.freeze_all_path_production_execution_protocol_v180r3()
        .to_document()["production_execution_slots"]
        if row["terminal_code"] == "FULL_GROUND_FALLBACK"
    ]
    if not (
        len(consumed_rows) == 1
        and protocol.EXPECTED_PROTOCOL_ID != consumed_protocol.EXPECTED_PROTOCOL_ID
        and slot["production_execution_slot_id"]
        != consumed_rows[0]["production_execution_slot_id"]
        and slot["execution_nonce"] != consumed_rows[0]["execution_nonce"]
    ):
        _fail("V180r7r1 reused the consumed V180r3 fallback slot or nonce")
    return protocol, document, slot


def _authorization_evidence(protocol_id: str) -> dict[str, Any]:
    from acfqp import (  # noqa: PLC0415
        construction_k7_full_ground_fallback_execution_authorization_evidence_freeze_v180r7r1
        as evidence,
    )

    freeze_evidence = getattr(
        evidence,
        "freeze_full_ground_fallback_execution_authorization_evidence_v180r7r1",
    )
    frozen = freeze_evidence()
    document = frozen.to_document()
    payload = dict(document)
    evidence_id = payload.pop("authorization_evidence_id", None)
    if not (
        type(document) is dict
        and set(document) == _AUTHORIZATION_EVIDENCE_FIELDS
        and frozenset(_AUTHORIZATION_EVIDENCE_FIELDS)
        == evidence.AUTHORIZATION_EVIDENCE_FIELDS
        and canonical_json_bytes(document) == frozen.canonical_bytes
        and frozen.authorization_evidence_id
        == evidence.EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and evidence_id == evidence.EXPECTED_AUTHORIZATION_EVIDENCE_ID
        and evidence_id
        == _content_id(evidence.AUTHORIZATION_EVIDENCE_DOMAIN, payload)
        and len(frozen.canonical_bytes) == evidence.EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(frozen.canonical_bytes).hexdigest()
        == evidence.EXPECTED_CANONICAL_SHA256
        and frozen.authorization_id == evidence.EXPECTED_AUTHORIZATION_ID
        and document.get("fallback_execution_authorization_id")
        == evidence.EXPECTED_AUTHORIZATION_ID
        and document.get("fallback_execution_protocol_id") == protocol_id
        and document.get("authorization_evidence_domain")
        == evidence.AUTHORIZATION_EVIDENCE_DOMAIN
        and document.get("authorization_self_source_bound_by_this_evidence")
        is True
        and document.get(
            "evidence_wrapper_self_source_excluded_to_avoid_identity_cycle"
        )
        is True
        and document.get("authorization_preregistered_before_this_evidence")
        is True
        and document.get("production_outcome_accessed") is False
        and document.get("fresh_production_occurrence_count") == 0
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("SCALAR_CALIBRATION_GATE") == "NOT_RUN"
        and document.get("BREAK_EVEN_GATE") == "NOT_RUN"
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
        and document.get("outcome_free") is True
    ):
        _fail("fresh V180r7r1 authorization evidence changed")
    authorization_fact = document.get("authorization_source_fact")
    execution_facts = document.get("execution_chain_source_facts")
    exclusions = document.get("source_fact_exclusions")
    if not (
        type(authorization_fact) is dict
        and type(execution_facts) is list
        and len(execution_facts) == 4
        and type(exclusions) is list
        and exclusions == list(evidence.SOURCE_FACT_EXCLUSIONS)
        and exclusions == sorted(set(exclusions))
    ):
        _fail("fresh authorization evidence source inventory changed")
    repository_root = Path(__file__).resolve().parents[2]
    for fact in (authorization_fact, *execution_facts):
        if type(fact) is not dict or set(fact) != {
            "relative_path",
            "byte_count",
            "sha256",
        }:
            _fail("fresh authorization evidence source fact schema changed")
        relative = PurePosixPath(fact["relative_path"])
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or relative.as_posix() != fact["relative_path"]
            or "\\" in fact["relative_path"]
        ):
            _fail("fresh authorization evidence source path changed")
        raw = _read_symlink_free(repository_root / Path(*relative.parts))
        if fact != {
            "relative_path": relative.as_posix(),
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }:
            _fail("fresh authorization evidence source bytes changed")
    if [row["relative_path"] for row in execution_facts] != sorted(
        {row["relative_path"] for row in execution_facts}
    ):
        _fail("authorization evidence execution facts changed order")
    return document


def _source_authorization(
    *, protocol_id: str, slot: Mapping[str, Any]
) -> dict[str, Any]:
    evidence_document = _authorization_evidence(protocol_id)
    from acfqp import (  # noqa: PLC0415
        construction_k7_full_ground_fallback_execution_authorization_v180r7r1
        as authorization,
    )

    frozen = authorization.freeze_full_ground_fallback_execution_authorization_v180r7r1()
    document = frozen.to_document()
    payload = dict(document)
    authorization_id = payload.pop("fallback_execution_authorization_id", None)
    if not (
        type(document) is dict
        and set(document) == _AUTHORIZATION_FIELDS
        and canonical_json_bytes(document) == frozen.canonical_bytes
        and frozen.authorization_id == authorization.EXPECTED_AUTHORIZATION_ID
        and authorization_id == authorization.EXPECTED_AUTHORIZATION_ID
        and authorization_id
        == evidence_document["fallback_execution_authorization_id"]
        and len(frozen.canonical_bytes)
        == evidence_document["authorization_canonical_byte_count"]
        and hashlib.sha256(frozen.canonical_bytes).hexdigest()
        == evidence_document["authorization_canonical_sha256"]
        and authorization_id
        == domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_AUTHORIZATION_V180R7R1_DOMAIN,
            payload,
        )
        and len(frozen.canonical_bytes)
        == authorization.EXPECTED_CANONICAL_BYTE_COUNT
        and hashlib.sha256(frozen.canonical_bytes).hexdigest()
        == authorization.EXPECTED_CANONICAL_SHA256
        and document.get("fallback_execution_protocol_id") == protocol_id
        and document.get("production_execution_slot") == dict(slot)
        and document.get("logical_occurrence_id") == _LOGICAL_OCCURRENCE_ID
        and document.get("query_ordinal") == _QUERY_ORDINAL
        and document.get("preserved_v180r7_failure_id")
        == _PRESERVED_V180R7_FAILURE_ID
        and document.get("source_catalog_manifest_id")
        == _SOURCE_CATALOG_MANIFEST_ID
        and document.get("source_closure_repair_id") == _SOURCE_CLOSURE_REPAIR_ID
        and document.get("materialization_manifest_id")
        == slot.get("materialization_manifest_id")
        and document.get("retained_predecessor_input_facts")
        == sorted(
            (
                {
                    "relative_path": row["relative_path"],
                    "byte_count": row["byte_count"],
                    "sha256": row["sha256"],
                }
                for row in _RETAINED_PREDECESSOR_INPUT_FACTS
            ),
            key=lambda row: row["relative_path"],
        )
        and document.get("production_outcome_accessed") is False
        and document.get("COUNTER_COMPLETENESS_GATE") == "NOT_RUN"
        and document.get("WORKLOAD_ECONOMICS_GATE") == "NOT_RUN"
        and document.get("official_scalar_cost") is None
        and document.get("official_N_break_even") is None
        and document.get("official_execution_allowed") is False
        and document.get("one_isolated_worker_no_concurrent_campaign") is True
        and document.get(
            "concurrent_workspace_mutation_during_one_shot_occurrence_out_of_scope"
        )
        is True
    ):
        _fail("fresh V180r7r1 execution authorization changed")
    _replay_authorization_source_facts(document)
    return document


@dataclass(frozen=True, slots=True)
class _SourceOutputEpoch:
    role_bytes: Mapping[str, bytes]
    inventory: tuple[dict[str, Any], ...]


def _capture_source_output_epoch(root: Path) -> _SourceOutputEpoch:
    """Read every retained role once through one anchored directory handle."""

    directory = _open_directory_symlink_free(root)
    try:
        before = os.fstat(directory)
        names = sorted(os.listdir(directory))
        if set(names) != _OUTPUT_FILENAMES or len(names) != len(
            _OUTPUT_FILENAMES
        ):
            _fail("retained fallback output role set changed")
        role_bytes: dict[str, bytes] = {}
        inventory: list[dict[str, Any]] = []
        for name in names:
            raw = _read_regular_at(directory, name)
            _object(raw, f"retained fallback output {name}")
            role_bytes[name] = raw
            inventory.append(
                {
                    "relative_path": name,
                    "canonical_byte_count": len(raw),
                    "canonical_sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
        after = os.fstat(directory)
        if sorted(os.listdir(directory)) != names or _stat_identity(before) != (
            _stat_identity(after)
        ):
            _fail("retained fallback output changed during epoch capture")
    finally:
        os.close(directory)
    return _SourceOutputEpoch(role_bytes, tuple(inventory))


def _inventory(root: Path) -> list[dict[str, Any]]:
    return list(_capture_source_output_epoch(root).inventory)


def _replay_retained_predecessor_inputs() -> list[dict[str, Any]]:
    repository_root = Path(__file__).resolve().parents[2]
    replayed: list[dict[str, Any]] = []
    for expected in _RETAINED_PREDECESSOR_INPUT_FACTS:
        raw = _read_symlink_free(repository_root / expected["relative_path"])
        observed = {
            "role": expected["role"],
            "relative_path": expected["relative_path"],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        _object(raw, expected["role"])
        if observed != expected:
            _fail("retained V180r7r1 predecessor input changed")
        replayed.append(observed)
    return replayed


@dataclass(frozen=True, slots=True)
class _SourceRouteReplay:
    vectors: tuple[WorkVectorV1, ...]
    comparisons: tuple[ComparisonVectorV1, ...]
    proofs: tuple[ActualProjectionProofV1, ...]
    shared_resource_receipt_ids: tuple[str, ...]
    output_bytes: int

    @property
    def receipt_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "route_kind": vector.route_kind.value,
                "source_work_vector_id": vector.work_vector_id,
                "source_comparison_vector_id": comparison.comparison_vector_id,
                "source_actual_projection_proof_id": proof.actual_projection_proof_id,
                "independent_route_component": True,
            }
            for vector, comparison, proof in zip(
                self.vectors, self.comparisons, self.proofs, strict=True
            )
        ]


def _source_route_chains(
    role_bytes: Mapping[str, bytes],
) -> _SourceRouteReplay:
    work = _object(
        role_bytes["WORK_VECTOR.json"], "source V6 vectors"
    )
    comparisons_document = _object(
        role_bytes["COMPARISON_VECTOR.json"],
        "source V6 comparison vectors",
    )
    proofs_document = _object(
        role_bytes["ACTUAL_PROJECTION_PROOF.json"],
        "source V6 projection proofs",
    )
    if not (
        set(work)
        == {
            "artifact_role",
            "direct_fallback_work_vector",
            "io.output_bytes",
            "local_recovery_work_vector",
            "marginal_route_upper_compliance_authority",
            "route_family_vectors_remain_separate",
            "schema",
            "supervised_wrapper_work_vector",
        }
        and set(comparisons_document)
        == {
            "artifact_role",
            "direct_fallback_comparison_vector",
            "io.output_bytes",
            "local_recovery_comparison_vector",
            "occurrence_reducer_exact_comparison_values",
            "route_choice_authority",
            "schema",
            "supervised_wrapper_comparison_vector",
        }
        and set(proofs_document)
        == {
            "artifact_role",
            "direct_fallback_actual_projection_proof",
            "io.output_bytes",
            "local_recovery_actual_projection_proof",
            "schema",
            "supervised_wrapper_actual_projection_proof",
        }
        and work["artifact_role"] == "WORK_VECTOR"
        and work["schema"]
        == "acfqp.construction_k7_recovery_eligible_work_vector_artifact.v1"
        and comparisons_document["artifact_role"] == "COMPARISON_VECTOR"
        and comparisons_document["schema"]
        == "acfqp.construction_k7_recovery_eligible_comparison_vector_artifact.v1"
        and proofs_document["artifact_role"] == "ACTUAL_PROJECTION_PROOF"
        and proofs_document["schema"]
        == "acfqp.construction_k7_recovery_eligible_projection_artifact.v1"
        and work["route_family_vectors_remain_separate"] is True
        and work["marginal_route_upper_compliance_authority"] is False
        and comparisons_document["route_choice_authority"] is False
        and work["io.output_bytes"] == comparisons_document["io.output_bytes"]
        == proofs_document["io.output_bytes"]
    ):
        _fail("source V6 route artifacts changed")
    registry = registry_v6.official_counter_registry_v6()
    comparison_profile = registry_v6.official_comparison_profile_v6(registry)
    actual_profile = registry_v6.official_actual_projection_profile_v6(
        registry, comparison_profile
    )
    vectors: list[WorkVectorV1] = []
    comparisons: list[ComparisonVectorV1] = []
    proofs: list[ActualProjectionProofV1] = []
    for route in _ROUTES:
        vector = WorkVectorV1.from_dict(
            work[_SOURCE_VECTOR_KEY_BY_ROUTE[route]], registry
        )
        comparison = ComparisonVectorV1.from_dict(
            comparisons_document[_SOURCE_COMPARISON_KEY_BY_ROUTE[route]]
        )
        proof = ActualProjectionProofV1.from_dict(
            proofs_document[_SOURCE_PROOF_KEY_BY_ROUTE[route]]
        )
        expected_comparison, expected_proof = derive_actual_projection_v1(
            vector,
            registry,
            comparison_profile,
            actual_profile,
            source_lane=LaneEnum.OPERATIONAL,
            work_scope=_SOURCE_SCOPE_BY_ROUTE[route],
        )
        if not (
            vector.route_kind is route
            and vector.subject_id == _LOGICAL_OCCURRENCE_ID
            and len(vector.records) == 202
            and comparison == expected_comparison
            and proof == expected_proof
        ):
            _fail("source V6 WorkVector to ComparisonVector to proof chain changed")
        vectors.append(vector)
        comparisons.append(comparison)
        proofs.append(proof)
    if not (
        vectors[0].values["io.output_bytes"] == work["io.output_bytes"]
        and vectors[2].values["fallback.ground_steps"] > 0
        and vectors[2].values["route.attempts"] == 1
        and vectors[2].values["route.successes"] == 1
    ):
        _fail("source V6 full-ground-fallback semantics changed")
    axis_reducers = {row.name: row.reducer for row in comparison_profile.axes}
    reducer_values = [
        {
            "axis": axis,
            "value": (
                sum(dict(row.values)[axis] for row in comparisons)
                if axis_reducers[axis] is ReducerEnum.SUM
                else max(dict(row.values)[axis] for row in comparisons)
            ),
        }
        for axis in sorted(axis_reducers)
    ]
    if comparisons_document["occurrence_reducer_exact_comparison_values"] != (
        reducer_values
    ):
        _fail("source V6 occurrence comparison reduction changed")
    shared_receipt_ids = _replay_source_cross_artifacts(
        role_bytes, tuple(vectors), tuple(comparisons), tuple(proofs)
    )
    return _SourceRouteReplay(
        tuple(vectors),
        tuple(comparisons),
        tuple(proofs),
        shared_receipt_ids,
        work["io.output_bytes"],
    )


def _replay_source_cross_artifacts(
    role_bytes: Mapping[str, bytes],
    vectors: tuple[WorkVectorV1, ...],
    comparisons: tuple[ComparisonVectorV1, ...],
    proofs: tuple[ActualProjectionProofV1, ...],
) -> tuple[str, ...]:
    counter = _object(
        role_bytes["COUNTER_RECORD_SET.json"],
        "source V6 counter records",
    )
    terminal = _object(
        role_bytes["TERMINAL_ARTIFACT.json"],
        "source V6 terminal artifact",
    )
    manifest = _object(
        role_bytes["OUTPUT_MANIFEST.json"],
        "source V6 output manifest",
    )
    component_records = counter.get("component_counter_records")
    receipts = counter.get("shared_resource_receipts")
    receipt_ids: list[str] = []
    if type(receipts) is list:
        for receipt in receipts:
            if type(receipt) is not dict:
                _fail("source shared resource receipt is malformed")
            payload = dict(receipt)
            receipt_id = payload.pop("shared_resource_receipt_id", None)
            if receipt_id != content_id(
                CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_V1_DOMAIN,
                payload,
            ):
                _fail("source shared resource receipt identity changed")
            receipt_ids.append(receipt_id)
    receipt_set = counter.get("shared_resource_receipt_set")
    if type(receipt_set) is not dict:
        _fail("source shared resource receipt set is malformed")
    receipt_set_payload = dict(receipt_set)
    receipt_set_id = receipt_set_payload.pop(
        "shared_resource_receipt_set_id", None
    )
    if not (
        counter.get("schema")
        == "acfqp.construction_k7_recovery_eligible_counter_record_set.v1"
        and counter.get("occurrence_id") == _LOGICAL_OCCURRENCE_ID
        and type(component_records) is list
        and len(component_records) == 3
        and counter.get("component_counter_record_count") == 3 * 202
        and counter.get("counter_records_per_component") == 202
        and component_records
        == [
            {
                "route_kind": vector.route_kind.value,
                "counter_records": [row.to_dict() for row in vector.records],
            }
            for vector in vectors
        ]
        and len(receipt_ids) == 9
        and receipt_set_id
        == content_id(
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_SHARED_RECEIPT_SET_V1_DOMAIN,
            receipt_set_payload,
        )
        and receipt_set.get("shared_resource_receipt_ids") == receipt_ids
    ):
        _fail("source counter-record artifact differs from its WorkVectors")
    if not (
        terminal.get("schema")
        == "acfqp.construction_k7_recovery_eligible_terminal_artifact.v1"
        and terminal.get("occurrence_id") == _LOGICAL_OCCURRENCE_ID
        and terminal.get("component_work_vector_ids")
        == [row.work_vector_id for row in vectors]
        and terminal.get("component_comparison_vector_ids")
        == [row.comparison_vector_id for row in comparisons]
        and terminal.get("component_actual_projection_proof_ids")
        == [row.actual_projection_proof_id for row in proofs]
        and terminal.get("terminal_code") == "FULL_GROUND_FALLBACK"
        and terminal.get("campaign_closure_issued") is False
        and terminal.get("official_execution_allowed") is False
    ):
        _fail("source terminal artifact route identities changed")
    preceding = manifest.get("ordered_preceding_roles")
    if not (
        manifest.get("schema")
        == "acfqp.construction_k7_recovery_eligible_output_manifest.v1"
        and manifest.get("occurrence_id") == _LOGICAL_OCCURRENCE_ID
        and manifest.get("required_role_order") == list(_OUTPUT_ROLES)
        and type(preceding) is list
        and preceding
        == [
            {
                "artifact_role": role,
                "byte_count": len(raw),
                "bytes_sha256": hashlib.sha256(raw).hexdigest(),
            }
            for role in _OUTPUT_ROLES[:-1]
            for raw in (role_bytes[f"{role}.json"],)
        ]
        and manifest.get("output_manifest_self_extent_excluded_from_preceding_rows")
        is True
    ):
        _fail("source output manifest does not bind its preceding retained bytes")
    return tuple(receipt_ids)


def _stat_identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def _absolute_parts(path: Path) -> tuple[str, ...]:
    absolute = Path(os.path.abspath(os.fspath(path)))
    if absolute.anchor != "/" or not absolute.parts[1:]:
        _fail("symlink-free path must name one absolute child")
    return absolute.parts[1:]


def _open_directory_symlink_free(path: Path) -> int:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor = os.open("/", flags)
    try:
        for part in _absolute_parts(path):
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            _fail("retained output directory contains a link or nondirectory")
        return descriptor
    except (OSError, ValueError) as error:
        os.close(descriptor)
        raise ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error(
            "retained output directory contains a link or nondirectory"
        ) from error


def _read_regular_at(directory: int, name: str) -> bytes:
    if (
        type(name) is not str
        or not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
    ):
        _fail("symlink-free child filename is malformed")
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=directory,
        )
    except OSError as error:
        raise ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error(
            "symlink-free regular file cannot be opened"
        ) from error
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            _fail("symlink-free input is not regular")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            _stat_identity(before) != _stat_identity(after)
            or len(raw) != after.st_size
        ):
            _fail("symlink-free input changed during stable read")
        return raw
    finally:
        os.close(descriptor)


def _read_symlink_free(path: Path) -> bytes:
    parts = _absolute_parts(path)
    parent = Path("/").joinpath(*parts[:-1])
    directory = _open_directory_symlink_free(parent)
    try:
        return _read_regular_at(directory, parts[-1])
    finally:
        os.close(directory)


def _replay_authorization_source_facts(
    authorization_document: Mapping[str, Any],
) -> None:
    facts = authorization_document.get("source_facts")
    if type(facts) is not list or not facts:
        _fail("fresh authorization source facts are absent")
    repository_root = Path(__file__).resolve().parents[2]
    relative_paths: list[str] = []
    for fact in facts:
        if type(fact) is not dict or set(fact) != {
            "relative_path",
            "byte_count",
            "sha256",
        }:
            _fail("fresh authorization source fact schema changed")
        relative = PurePosixPath(fact["relative_path"])
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or relative.as_posix() != fact["relative_path"]
            or "\\" in fact["relative_path"]
        ):
            _fail("fresh authorization source path is malformed")
        raw = _read_symlink_free(repository_root / Path(*relative.parts))
        if fact != {
            "relative_path": relative.as_posix(),
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }:
            _fail("fresh authorization-bound source bytes changed")
        relative_paths.append(relative.as_posix())
    exclusions = authorization_document.get("source_fact_exclusions")
    if not (
        relative_paths == sorted(set(relative_paths))
        and authorization_document.get("source_fact_file_count") == len(facts)
        and authorization_document.get("source_fact_byte_count")
        == sum(row["byte_count"] for row in facts)
        and authorization_document.get("source_facts_sha256")
        == hashlib.sha256(canonical_json_bytes(facts)).hexdigest()
        and type(exclusions) is list
        and exclusions == sorted(set(exclusions))
        and not set(relative_paths).intersection(exclusions)
    ):
        _fail("fresh authorization source-fact closure changed")


def _replay_source_occurrence_semantics(
    role_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    business = _object(
        role_bytes["BUSINESS_RESULT.json"],
        "source V6 business result",
    )
    runtime_preparation = business.get("runtime_preparation")
    if type(runtime_preparation) is not dict:
        _fail("source V6 runtime preparation is absent")
    if set(role_bytes) != _OUTPUT_FILENAMES:
        _fail("source-output epoch role set changed")
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v180r7r1-source-output-replay-"
    ) as temporary:
        snapshot = Path(temporary)
        os.chmod(snapshot, 0o700)
        directory = _open_directory_symlink_free(snapshot)
        try:
            for name in sorted(role_bytes):
                descriptor = os.open(
                    name,
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_CLOEXEC", 0)
                    | getattr(os, "O_NOFOLLOW", 0),
                    0o400,
                    dir_fd=directory,
                )
                try:
                    view = memoryview(role_bytes[name])
                    while view:
                        written = os.write(descriptor, view)
                        if written <= 0:
                            _fail("private replay snapshot short write")
                        view = view[written:]
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            os.fsync(directory)
        finally:
            os.close(directory)
        try:
            replay = source_output_verifier._verify_occurrence_output(  # noqa: SLF001
                snapshot,
                logical_occurrence_id=_LOGICAL_OCCURRENCE_ID,
                prereg_runtime=runtime_preparation,
            )
        except (
            source_output_verifier.
            ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error
        ) as error:
            raise (
                ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error(
                    "bytes-only source occurrence semantic replay failed"
                )
            ) from error
    if type(replay) is not dict:
        _fail("bytes-only source occurrence replay returned no exact receipt")
    return replay


def _content_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode() + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _replay_construction_work(
    work: Any,
    *,
    producer_facts: Any,
    manifest_bytes: int,
) -> dict[str, Any]:
    if not (
        type(work) is dict
        and set(work) == _CONSTRUCTION_WORK_FIELDS
        and type(producer_facts) is list
        and len(producer_facts) == 2
    ):
        _fail("materialization construction-work field set changed")
    producer_bytes = 0
    repository_root = Path(__file__).resolve().parents[2]
    for fact in producer_facts:
        if type(fact) is not dict or set(fact) != {
            "relative_path",
            "byte_count",
            "sha256",
            "excluded_from_frozen_worker_source_catalog",
        }:
            _fail("materialization producer source fact changed")
        raw = _read_symlink_free(repository_root / fact["relative_path"])
        if fact != {
            "relative_path": fact["relative_path"],
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "excluded_from_frozen_worker_source_catalog": True,
        }:
            _fail("materialization producer source bytes changed")
        producer_bytes += len(raw)
    expected = {
        "scope": (
            "COLD_ONE_SHOT_PRODUCER_EXACT_SEMANTIC_FILE_IO;"
            "IMPORT_LOADER_IO_AND_FILESYSTEM_METADATA_EXCLUDED"
        ),
        "retained_identity_validation_reads": {
            "file_count": _EXPECTED_RETAINED_VALIDATION_FILE_READ_COUNT,
            "byte_count": _EXPECTED_RETAINED_VALIDATION_BYTE_COUNT,
            "sha256_file_identity_checks": _EXPECTED_RETAINED_VALIDATION_FILE_READ_COUNT,
        },
        "construction_producer_identity_reads": {
            "file_count": 2,
            "byte_count": producer_bytes,
            "sha256_file_identity_checks": 2,
        },
        "live_reachable_source_reads": {
            "file_count": _EXPECTED_REACHABLE_MODULE_COUNT,
            "byte_count": _EXPECTED_REACHABLE_SOURCE_BYTE_COUNT,
            "sha256_source_fact_checks": _EXPECTED_REACHABLE_MODULE_COUNT,
        },
        "materialized_source_writes": {
            "file_count": _EXPECTED_REACHABLE_MODULE_COUNT,
            "byte_count": _EXPECTED_REACHABLE_SOURCE_BYTE_COUNT,
            "file_fsync_count": _EXPECTED_REACHABLE_MODULE_COUNT,
        },
        "unchanged_v2_materialized_source_replay_reads": {
            "file_count": _EXPECTED_REACHABLE_MODULE_COUNT,
            "byte_count": _EXPECTED_REACHABLE_SOURCE_BYTE_COUNT,
            "caller_supplied_byte_equality_checks": _EXPECTED_REACHABLE_MODULE_COUNT,
            "source_digest_constructions": _EXPECTED_REACHABLE_MODULE_COUNT,
        },
        "materialized_tree_directories": {
            "created_directory_count": _EXPECTED_SOURCE_DIRECTORY_COUNT_BELOW_ROOT + 1,
            "staged_source_directory_count_below_root": _EXPECTED_SOURCE_DIRECTORY_COUNT_BELOW_ROOT,
            "tree_directory_fsync_count": _EXPECTED_SOURCE_DIRECTORY_COUNT_BELOW_ROOT + 1,
            "evidence_parent_directory_fsync_count": 2,
        },
        "materialization_manifest_write": {
            "file_count": 1,
            "byte_count": manifest_bytes,
            "file_fsync_count": 1,
        },
        "semantic_file_read_count": (
            _EXPECTED_RETAINED_VALIDATION_FILE_READ_COUNT
            + 2
            + 2 * _EXPECTED_REACHABLE_MODULE_COUNT
        ),
        "semantic_file_read_byte_count": (
            _EXPECTED_RETAINED_VALIDATION_BYTE_COUNT
            + producer_bytes
            + 2 * _EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
        ),
        "durable_file_write_count": _EXPECTED_REACHABLE_MODULE_COUNT + 1,
        "durable_file_write_byte_count": (
            _EXPECTED_REACHABLE_SOURCE_BYTE_COUNT + manifest_bytes
        ),
        "file_fsync_count": _EXPECTED_REACHABLE_MODULE_COUNT + 1,
        "directory_fsync_count": _EXPECTED_SOURCE_DIRECTORY_COUNT_BELOW_ROOT + 3,
        "occurrence_counter_record_count": 0,
        "occurrence_route_work_vector_count": 0,
        "occurrence_comparison_vector_count": 0,
        "construction_work_excluded_from_occurrence_route_vectors": True,
    }
    if work != expected:
        _fail("materialization construction-work accounting changed")
    return expected


def _materialized_source_reference() -> dict[str, Any]:
    repository_root = Path(__file__).resolve().parents[2]
    manifest_path = repository_root / _MATERIALIZATION_MANIFEST_RELATIVE_PATH
    raw = _read_symlink_free(manifest_path)
    document = _object(raw, "V180r7r1 materialization manifest")
    if set(document) != _MATERIALIZATION_MANIFEST_FIELDS:
        _fail("materialization manifest field set changed")
    payload = dict(document)
    manifest_id = payload.pop("materialization_manifest_id", None)
    if not (
        document["schema"]
        == "acfqp.full_ground_fallback_materialized_source_tree_manifest.v180r7r1m1"
        and document["materialization_manifest_domain"]
        == _MATERIALIZATION_MANIFEST_DOMAIN
        and manifest_id
        == materialization_domains.extension_content_id_v180r7r1m1(
            _MATERIALIZATION_MANIFEST_DOMAIN,
            payload,
        )
        and document["source_catalog_manifest_id"] == _SOURCE_CATALOG_MANIFEST_ID
        and document["source_closure_repair_id"] == _SOURCE_CLOSURE_REPAIR_ID
        and document["unchanged_v2_source_closure_id"] == _SOURCE_CLOSURE_ID
        and document["materialized_root_relative_path"]
        == _MATERIALIZED_SOURCE_RELATIVE_PATH
        and document["manifest_output_relative_path"]
        == _MATERIALIZATION_MANIFEST_RELATIVE_PATH
    ):
        _fail("materialization manifest identity changed")
    tree = document["materialized_source_tree"]
    if type(tree) is not dict or set(tree) != _MATERIALIZED_TREE_FIELDS:
        _fail("materialized source-tree field set changed")
    tree_payload = dict(tree)
    tree_id = tree_payload.pop("materialized_source_tree_id", None)
    facts = tree["reachable_source_facts"]
    if not (
        tree_id
        == materialization_domains.extension_content_id_v180r7r1m1(
            materialization_domains.CONSTRUCTION_K7_MATERIALIZED_SOURCE_TREE_V180R7R1M1_DOMAIN,
            tree_payload,
        )
        and document["materialized_source_tree_id"] == tree_id
        and tree["schema"]
        == "acfqp.full_ground_fallback_materialized_source_tree.v180r7r1m1"
        and tree["source_catalog_manifest_id"] == _SOURCE_CATALOG_MANIFEST_ID
        and tree["source_closure_repair_id"] == _SOURCE_CLOSURE_REPAIR_ID
        and tree["source_closure_id"] == _SOURCE_CLOSURE_ID
        and tree["materialized_root_relative_path"]
        == _MATERIALIZED_SOURCE_RELATIVE_PATH
        and tree["materialized_source_root_relative_path"]
        == f"{_MATERIALIZED_SOURCE_RELATIVE_PATH}/src/acfqp"
        and tree["reachable_source_facts_sha256"]
        == _REACHABLE_SOURCE_FACTS_SHA256
        and tree["materialized_source_file_count"]
        == _EXPECTED_REACHABLE_MODULE_COUNT
        and tree["materialized_source_byte_count"]
        == _EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
        and tree["only_exact_reachable_source_facts_materialized"] is True
        and tree["candidate_catalog_unreachable_files_materialized"] is False
        and tree["source_bytes_executed"] is False
        and tree["construction_only"] is True
        and type(facts) is list
        and len(facts) == _EXPECTED_REACHABLE_MODULE_COUNT
        and hashlib.sha256(canonical_json_bytes(facts)).hexdigest()
        == _REACHABLE_SOURCE_FACTS_SHA256
    ):
        _fail("materialized source-tree identity or denominator changed")
    materialized_root = repository_root / _MATERIALIZED_SOURCE_RELATIVE_PATH
    expected_files: set[str] = set()
    module_sources: dict[str, bytes] = {}
    module_paths: dict[str, Path] = {}
    source_bytes = 0
    names: list[str] = []
    for fact in facts:
        if type(fact) is not dict or set(fact) != {
            "module_name",
            "relative_path",
            "source_byte_count",
            "source_sha256",
        }:
            _fail("reachable materialized source fact changed")
        relative = PurePosixPath(fact["relative_path"])
        if (
            relative.is_absolute()
            or not relative.parts
            or relative.parts[0] != "acfqp"
            or relative.suffix != ".py"
            or any(part in {"", ".", ".."} for part in relative.parts)
            or relative.as_posix() != fact["relative_path"]
        ):
            _fail("reachable materialized source path is malformed")
        staged_relative = (PurePosixPath("src") / relative).as_posix()
        path = materialized_root / Path(*PurePosixPath(staged_relative).parts)
        source = _read_symlink_free(path)
        if not (
            len(source) == fact["source_byte_count"]
            and hashlib.sha256(source).hexdigest() == fact["source_sha256"]
            and fact["module_name"] not in module_sources
        ):
            _fail("materialized source bytes changed")
        expected_files.add(staged_relative)
        names.append(fact["module_name"])
        module_sources[fact["module_name"]] = source
        module_paths[fact["module_name"]] = path
        source_bytes += len(source)
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    for path in materialized_root.rglob("*"):
        relative = path.relative_to(materialized_root).as_posix()
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode):
            _fail("materialized tree contains a symlink")
        if stat.S_ISREG(info.st_mode):
            actual_files.add(relative)
        elif stat.S_ISDIR(info.st_mode):
            actual_directories.add(relative)
        else:
            _fail("materialized tree contains a nonregular entry")
    if not (
        names == sorted(set(names))
        and actual_files == expected_files
        and len(actual_directories) == _EXPECTED_SOURCE_DIRECTORY_COUNT_BELOW_ROOT
        and source_bytes == _EXPECTED_REACHABLE_SOURCE_BYTE_COUNT
    ):
        _fail("materialized source inventory changed")
    closure_document = document["unchanged_v2_source_closure"]
    try:
        closure = source_runtime_v2.build_construction_source_closure_v2(
            root_modules=tuple(closure_document["root_modules"]),
            module_sources=module_sources,
            module_paths=module_paths,
        )
    except source_runtime_v2.V075ConstructionSourceRuntimeV2InvariantViolation as error:
        raise ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error(
            "independent unchanged-V2 staged-source replay failed"
        ) from error
    if not (
        closure.closure_id == _SOURCE_CLOSURE_ID
        and closure.to_document() == closure_document
    ):
        _fail("independent unchanged-V2 staged-source closure changed")
    work = _replay_construction_work(
        document["construction_work"],
        producer_facts=document["construction_producer_source_facts"],
        manifest_bytes=len(raw),
    )
    if not (
        document["fresh_execution_authorization_issued"] is False
        and document["fallback_occurrence_started"] is False
        and document["scientific_occurrence_executed"] is False
        and document["production_outcome_accessed"] is False
        and document["counter_records_issued"] is False
        and document["route_work_vectors_issued"] is False
        and document["comparison_vectors_issued"] is False
        and document["producer_free_verification_present"] is False
        and document["success_claimed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["SCALAR_CALIBRATION_GATE"] == "NOT_RUN"
        and document["BREAK_EVEN_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
        and document["construction_only"] is True
    ):
        _fail("materialization claim locks changed")
    return {
        "schema": "acfqp.full_ground_fallback_materialized_source_reference.v180r7r1",
        "materialization_manifest_id": manifest_id,
        "materialization_manifest_canonical_byte_count": len(raw),
        "materialization_manifest_canonical_sha256": hashlib.sha256(raw).hexdigest(),
        "materialized_source_tree_id": tree_id,
        "materialized_source_relative_path": _MATERIALIZED_SOURCE_RELATIVE_PATH,
        "source_catalog_manifest_id": _SOURCE_CATALOG_MANIFEST_ID,
        "source_closure_repair_id": _SOURCE_CLOSURE_REPAIR_ID,
        "source_closure_id": _SOURCE_CLOSURE_ID,
        "materialized_source_module_count": _EXPECTED_REACHABLE_MODULE_COUNT,
        "materialized_source_byte_count": _EXPECTED_REACHABLE_SOURCE_BYTE_COUNT,
        "construction_work": work,
        "one_time_construction_axis": True,
        "charged_to_any_route_component": False,
        "scientific_occurrence_execution_work": False,
    }


def _lineage_and_target(
    *,
    source_vector: WorkVectorV1,
    receipt_id: str,
    finalizer_output_bytes: int,
) -> tuple[list[dict[str, Any]], WorkVectorV1]:
    source_registry = registry_v6.official_counter_registry_v6()
    target_registry = registry_v9.official_counter_registry_v9()
    source_records = {row.path: row for row in source_vector.records}
    recorder_id = hashlib.sha256(
        b"acfqp:v180r7r1:v9-lift-recorder\x00"
        + receipt_id.encode()
        + b"\x00"
        + source_vector.route_kind.value.encode()
    ).hexdigest()
    records = []
    lineage = []
    for path in sorted(target_registry.by_path):
        source_record = source_records.get(path)
        value = source_record.value if source_record is not None else 0
        finalizer_increment = 0
        if (
            source_vector.route_kind is RouteKindEnum.ABSTRACT_FAILED_PREFIX
            and path == "io.output_bytes"
        ):
            value += finalizer_output_bytes
            finalizer_increment = finalizer_output_bytes
        record = CounterRecordV1.observe(
            target_registry, path, value, recorder_id=recorder_id
        )
        records.append(record)
        payload = {
            "schema": "acfqp.full_ground_fallback_v9_lift_lineage.v180r7r1",
            "source_counter_registry_id": source_registry.registry_id,
            "target_counter_registry_id": target_registry.registry_id,
            "source_work_vector_id": source_vector.work_vector_id,
            "route_kind": source_vector.route_kind.value,
            "path": path,
            "source_counter_record_id": (
                source_record.record_id if source_record is not None else None
            ),
            "source_value": source_record.value if source_record is not None else None,
            "target_counter_record_id": record.record_id,
            "value": value,
            "inherited_semantics_exact": source_record is not None,
            "source_value_plus_finalizer_increment_equals_target_value": (
                source_record is not None
                and source_record.value + finalizer_increment == value
            ),
            "finalizer_output_increment": finalizer_increment,
            "target_path_absent_from_source_vector_native_zero_observation": (
                source_record is None
            ),
            "historical_summary_translation_used": False,
            "materialized_source_construction_work_charged_to_this_route": False,
        }
        lineage.append(
            {
                **payload,
                "lineage_id": domains.extension_content_id_v180r7r1(
                    domains.CONSTRUCTION_K7_FALLBACK_V9_LIFT_LINEAGE_V180R7R1_DOMAIN,
                    payload,
                ),
            }
        )
    return lineage, WorkVectorV1(
        target_registry.registry_id,
        source_vector.subject_id,
        source_vector.route_kind,
        tuple(records),
    )


def _expected_component(
    *, source_vector: WorkVectorV1, receipt_id: str, finalizer_output_bytes: int
) -> dict[str, Any]:
    lineage, vector = _lineage_and_target(
        source_vector=source_vector,
        receipt_id=receipt_id,
        finalizer_output_bytes=finalizer_output_bytes,
    )
    registry = registry_v9.official_counter_registry_v9()
    comparison_profile = registry_v9.official_comparison_profile_v9(registry)
    actual_profile = registry_v9.official_actual_projection_profile_v9(
        registry, comparison_profile
    )
    comparison, proof = derive_actual_projection_v1(
        vector,
        registry,
        comparison_profile,
        actual_profile,
        source_lane=LaneEnum.OPERATIONAL,
        work_scope=_TARGET_SCOPE_BY_ROUTE[source_vector.route_kind],
    )
    zero = NativeZeroAttestationV1.derive(vector, registry)
    return {
        "source_work_vector": source_vector.to_dict(),
        "v9_work_vector": vector.to_dict(),
        "v9_comparison_vector": comparison.to_dict(),
        "v9_actual_projection_proof": proof.to_dict(),
        "v9_native_zero_attestation": zero.to_dict(),
        "counter_lift_lineage": lineage,
        "independent_route_component": True,
        "materialized_source_construction_work_charged_to_component": False,
    }


def _replay_terminal_fixed_point(
    *,
    protocol_id: str,
    slot: Mapping[str, Any],
    receipt: Mapping[str, Any],
    source_bundle: Mapping[str, Any],
    inventory: list[dict[str, Any]],
    source_vectors: Sequence[WorkVectorV1],
    materialization_reference: Mapping[str, Any],
) -> bytes:
    source_output_bytes = sum(row["canonical_byte_count"] for row in inventory)
    guess = 0
    for iteration in range(32):
        components = [
            _expected_component(
                source_vector=vector,
                receipt_id=receipt["production_occurrence_receipt_id"],
                finalizer_output_bytes=guess,
            )
            for vector in source_vectors
        ]
        payload = {
            "schema": "acfqp.full_ground_fallback_production_terminal_bundle.v180r7r1",
            "formalization_contract_id": _FORMALIZATION_CONTRACT_ID,
            "fallback_execution_protocol_id": protocol_id,
            "production_execution_slot": dict(slot),
            "terminal_code": "FULL_GROUND_FALLBACK",
            "production_occurrence_receipt": dict(receipt),
            "materialized_source_reference": dict(materialization_reference),
            "source_occurrence_accounting_bundle": dict(source_bundle),
            "source_output_inventory": inventory,
            "v9_lifted_route_components": components,
            "source_output_bytes": source_output_bytes,
            "finalizer_output_bytes": guess,
            "output_bytes_fixed_point": source_output_bytes + guess,
            "fixed_point_iteration": iteration,
            "fresh_v180r7r1_observed_occurrence_present": True,
            "three_route_family_vectors_remain_separate": True,
            "registered_counter_to_counter_v6_to_v9_lift_used": True,
            "v9_paths_absent_from_source_vector_have_explicit_native_zero_lineage": True,
            "materialization_is_separate_one_time_construction_axis": True,
            "materialization_work_charged_to_any_route_component": False,
            (
                "materialization_reference_serialization_is_output_metadata_not_"
                "construction_work"
            ): True,
            "terminal_serialization_bytes_charged_as_output_bytes": True,
            "historical_summary_translation_used": False,
            "development_fixture_only": False,
            "partial_campaign_cannot_unlock_any_gate": True,
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }
        document = {
            **payload,
            "production_terminal_bundle_id": domains.extension_content_id_v180r7r1(
                domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_TERMINAL_V180R7R1_DOMAIN,
                payload,
            ),
        }
        raw = canonical_json_bytes(document)
        if len(raw) == guess:
            return raw
        guess = len(raw)
    _fail("V180r7r1 independent terminal fixed-point replay did not converge")


def verify_full_ground_fallback_terminal_independently_v180r7r1(
    terminal_bytes: bytes, output_root: Path
) -> dict[str, Any]:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        _fail("retained V180r7r1 fallback output root is absent")
    protocol, protocol_document, slot = _fresh_protocol()
    authorization_document = _source_authorization(
        protocol_id=protocol.EXPECTED_PROTOCOL_ID,
        slot=slot,
    )
    materialization_reference = _materialized_source_reference()
    retained_input_facts = _replay_retained_predecessor_inputs()
    if slot.get("materialization_manifest_id") != materialization_reference[
        "materialization_manifest_id"
    ]:
        _fail("fresh execution slot changed its materialization identity")
    source_epoch = _capture_source_output_epoch(output_root)
    inventory = list(source_epoch.inventory)
    source_semantic_replay = _replay_source_occurrence_semantics(
        source_epoch.role_bytes
    )
    routes = _source_route_chains(source_epoch.role_bytes)
    document = _object(terminal_bytes, "V180r7r1 fallback terminal")
    if set(document) != _TOP_LEVEL_FIELDS:
        _fail("V180r7r1 fallback terminal field set changed")
    payload = dict(document)
    bundle_id = payload.pop("production_terminal_bundle_id", None)
    if not (
        document["schema"]
        == "acfqp.full_ground_fallback_production_terminal_bundle.v180r7r1"
        and document["formalization_contract_id"] == _FORMALIZATION_CONTRACT_ID
        and document["fallback_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and document["production_execution_slot"] == slot
        and document["terminal_code"] == "FULL_GROUND_FALLBACK"
        and bundle_id
        == domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_TERMINAL_V180R7R1_DOMAIN,
            payload,
        )
        and (
            EXPECTED_TERMINAL_BUNDLE_ID == "0" * 64
            or (
                bundle_id == EXPECTED_TERMINAL_BUNDLE_ID
                and len(terminal_bytes) == EXPECTED_TERMINAL_BYTE_COUNT
                and hashlib.sha256(terminal_bytes).hexdigest()
                == EXPECTED_TERMINAL_SHA256
            )
        )
    ):
        _fail("V180r7r1 fallback terminal identity changed")
    reference = document["materialized_source_reference"]
    if not (
        type(reference) is dict
        and set(reference) == _REFERENCE_FIELDS
        and reference == materialization_reference
    ):
        _fail("V180r7r1 terminal materialized-source reference changed")
    receipt = document["production_occurrence_receipt"]
    if type(receipt) is not dict or set(receipt) != _RECEIPT_FIELDS:
        _fail("V180r7r1 fallback receipt field set changed")
    receipt_payload = dict(receipt)
    receipt_id = receipt_payload.pop("production_occurrence_receipt_id", None)
    source_registry = registry_v6.official_counter_registry_v6()
    target_registry = registry_v9.official_counter_registry_v9()
    source_bundle = document["source_occurrence_accounting_bundle"]
    if type(source_bundle) is not dict:
        _fail("source occurrence bundle is not an object")
    source_bundle_payload = dict(source_bundle)
    source_bundle_id = source_bundle_payload.pop(
        "occurrence_accounting_bundle_id", None
    )
    if not (
        source_bundle_id
        == content_id(
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_OCCURRENCE_ACCOUNTING_V1_DOMAIN,
            source_bundle_payload,
        )
        and source_bundle["occurrence_id"] == _LOGICAL_OCCURRENCE_ID
        and source_bundle["scientific_terminal_code"] == "FULL_GROUND_FALLBACK"
        and source_bundle["shared_resource_path_count"] == 9
        and len(source_bundle["shared_resource_receipt_ids"]) == 9
        and source_bundle["shared_resource_receipt_ids"]
        == list(routes.shared_resource_receipt_ids)
        and source_bundle["component_work_vector_ids"]
        == [row.work_vector_id for row in routes.vectors]
        and source_bundle["component_comparison_vector_ids"]
        == [row.comparison_vector_id for row in routes.comparisons]
        and source_bundle["component_actual_projection_proof_ids"]
        == [row.actual_projection_proof_id for row in routes.proofs]
        and source_bundle["route_family_work_vectors_issued"] == 3
        and source_bundle["route_family_comparison_vectors_issued"] == 3
        and source_bundle["route_family_actual_projection_proofs_issued"] == 3
        and source_bundle["route_family_exclusivity_preserved"] is True
        and source_bundle["logical_occurrence_campaign_closed"] is False
        and source_bundle["official_execution_allowed"] is False
        and source_semantic_replay["bundle_id"] == source_bundle_id
        and source_semantic_replay["output_commit_id"]
        == source_bundle["output_commit_id"]
        and source_semantic_replay["output_bytes"] == routes.output_bytes
    ):
        _fail("source occurrence accounting bundle identity changed")
    if not (
        receipt_id
        == domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_OCCURRENCE_RECEIPT_V180R7R1_DOMAIN,
            receipt_payload,
        )
        and receipt["fallback_execution_protocol_id"]
        == protocol.EXPECTED_PROTOCOL_ID
        and receipt["production_execution_slot_id"]
        == slot["production_execution_slot_id"]
        and receipt["predecessor_occurrence_slot_id"]
        == slot["predecessor_occurrence_slot_id"]
        and receipt["execution_nonce"] == slot["execution_nonce"]
        and receipt["terminal_code"] == "FULL_GROUND_FALLBACK"
        and receipt["logical_occurrence_id"] == _LOGICAL_OCCURRENCE_ID
        and receipt["query_ordinal"] == _QUERY_ORDINAL
        and receipt["source_occurrence_accounting_bundle_id"] == source_bundle_id
        and receipt["source_counter_registry_id"] == source_registry.registry_id
        and receipt["target_counter_registry_id"] == target_registry.registry_id
        and receipt["source_route_components"] == routes.receipt_rows
        and all(
            type(row) is dict and set(row) == _SOURCE_ROUTE_COMPONENT_FIELDS
            for row in receipt["source_route_components"]
        )
        and receipt["source_work_vector_ids"]
        == [row.work_vector_id for row in routes.vectors]
        and receipt["source_shared_resource_receipt_ids"]
        == source_bundle["shared_resource_receipt_ids"]
        and len(receipt["source_shared_resource_receipt_ids"]) == 9
        and receipt["source_output_inventory"] == inventory
        and receipt["source_output_bytes"] == routes.output_bytes
        == sum(row["canonical_byte_count"] for row in inventory)
        and receipt["retained_predecessor_input_facts"]
        == retained_input_facts
        and receipt["materialized_source_reference"] == materialization_reference
        and receipt["production_execution_started_by_this_call"] is True
        and receipt["preexisting_occurrence_output_used"] is False
        and receipt["native_v6_counter_records_used"] is True
        and receipt["registered_v6_to_v9_counter_lift_required"] is True
        and receipt["three_route_components_independent"] is True
        and receipt["materialization_is_separate_one_time_construction_axis"] is True
        and receipt["materialization_work_charged_to_any_route_component"] is False
        and receipt["historical_summary_translation_used"] is False
        and receipt["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and receipt["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and receipt["official_scalar_cost"] is None
        and receipt["official_N_break_even"] is None
        and receipt["official_execution_allowed"] is False
    ):
        _fail("V180r7r1 fallback receipt semantics changed")
    components = document["v9_lifted_route_components"]
    if type(components) is not list or len(components) != 3:
        _fail("V180r7r1 lifted component denominator changed")
    for component, source_vector in zip(
        components, routes.vectors, strict=True
    ):
        if type(component) is not dict or set(component) != _COMPONENT_FIELDS:
            _fail("V180r7r1 lifted component field set changed")
        if any(
            set(row) != _LINEAGE_FIELDS
            for row in component["counter_lift_lineage"]
        ):
            _fail("V180r7r1 lift lineage field set changed")
        expected = _expected_component(
            source_vector=source_vector,
            receipt_id=receipt_id,
            finalizer_output_bytes=len(terminal_bytes),
        )
        if not (
            component == expected
            and len(component["v9_work_vector"]["records"]) == 269
            and component["independent_route_component"] is True
            and component[
                "materialized_source_construction_work_charged_to_component"
            ]
            is False
        ):
            _fail("V180r7r1 record lift or V9 projection changed")
    if _replay_terminal_fixed_point(
        protocol_id=protocol.EXPECTED_PROTOCOL_ID,
        slot=slot,
        receipt=receipt,
        source_bundle=source_bundle,
        inventory=inventory,
        source_vectors=routes.vectors,
        materialization_reference=materialization_reference,
    ) != terminal_bytes:
        _fail("V180r7r1 producer-free terminal fixed-point bytes changed")
    if not (
        document["source_output_inventory"] == inventory
        and document["source_output_bytes"] == routes.output_bytes
        and document["finalizer_output_bytes"] == len(terminal_bytes)
        and document["output_bytes_fixed_point"]
        == routes.output_bytes + len(terminal_bytes)
        and document["fresh_v180r7r1_observed_occurrence_present"] is True
        and document["three_route_family_vectors_remain_separate"] is True
        and document["registered_counter_to_counter_v6_to_v9_lift_used"] is True
        and document[
            "v9_paths_absent_from_source_vector_have_explicit_native_zero_lineage"
        ]
        is True
        and document["materialization_is_separate_one_time_construction_axis"] is True
        and document["materialization_work_charged_to_any_route_component"] is False
        and document[
            "materialization_reference_serialization_is_output_metadata_not_construction_work"
        ]
        is True
        and document["terminal_serialization_bytes_charged_as_output_bytes"] is True
        and document["historical_summary_translation_used"] is False
        and document["development_fixture_only"] is False
        and document["partial_campaign_cannot_unlock_any_gate"] is True
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
    ):
        _fail("V180r7r1 output fixed point or claim lock changed")
    verification_payload = {
        "schema": "acfqp.full_ground_fallback_execution_verification.v180r7r1",
        "fallback_execution_authorization_id": authorization_document[
            "fallback_execution_authorization_id"
        ],
        "fallback_execution_protocol_id": protocol.EXPECTED_PROTOCOL_ID,
        "production_terminal_bundle_id": bundle_id,
        "production_terminal_byte_count": len(terminal_bytes),
        "production_terminal_bytes_sha256": hashlib.sha256(
            terminal_bytes
        ).hexdigest(),
        "source_occurrence_accounting_bundle_id": source_bundle_id,
        "retained_output_file_count": len(inventory),
        "source_v6_work_vector_count": len(routes.vectors),
        "source_v6_counter_record_count": sum(
            len(row.records) for row in routes.vectors
        ),
        "source_v6_comparison_vector_count": len(routes.comparisons),
        "source_v6_actual_projection_proof_count": len(routes.proofs),
        "lifted_v9_work_vector_count": len(components),
        "lifted_v9_counter_record_count": 3 * 269,
        "shared_resource_receipt_count": 9,
        "materialization_manifest_id": materialization_reference[
            "materialization_manifest_id"
        ],
        "materialized_source_tree_id": materialization_reference[
            "materialized_source_tree_id"
        ],
        "unchanged_v2_source_closure_id": _SOURCE_CLOSURE_ID,
        "materialized_source_module_count": _EXPECTED_REACHABLE_MODULE_COUNT,
        "materialized_source_byte_count": _EXPECTED_REACHABLE_SOURCE_BYTE_COUNT,
        "retained_source_output_bytes_replayed_without_producer_import": True,
        "source_v6_counter_values_rederived_from_operational_trace": True,
        "three_source_v6_route_chains_reconstructed": True,
        "registered_v6_to_v9_counter_lift_reconstructed": True,
        "three_route_family_vectors_remain_separate": True,
        "materialized_source_manifest_replayed_without_producer_import": True,
        "materialized_source_tree_bytes_replayed": True,
        "unchanged_v2_source_closure_rederived": True,
        "construction_axis_replayed_separately": True,
        "construction_work_charged_to_any_route_component": False,
        "terminal_output_fixed_point_replayed": True,
        "fresh_successor_slot_and_nonce_verified": True,
        "fresh_single_path_verified": True,
        "all_ten_paths_verified": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    return {
        **verification_payload,
        "verification_id": domains.extension_content_id_v180r7r1(
            domains.CONSTRUCTION_K7_FALLBACK_EXECUTION_VERIFICATION_V180R7R1_DOMAIN,
            verification_payload,
        ),
    }


_ISSUER = object()


@dataclass(frozen=True, slots=True)
class FullGroundFallbackVerificationV180r7r1:
    _issuer: object = field(repr=False, compare=False)
    canonical_bytes: bytes = field(repr=False)
    verification_id: str

    def to_document(self) -> dict[str, Any]:
        return _object(self.canonical_bytes, "V180r7r1 fallback verification")


def freeze_full_ground_fallback_verification_v180r7r1(
    terminal_bytes: bytes, output_root: Path
) -> FullGroundFallbackVerificationV180r7r1:
    document = verify_full_ground_fallback_terminal_independently_v180r7r1(
        terminal_bytes, output_root
    )
    raw = canonical_json_bytes(document)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        document["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(raw) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        _fail("V180r7r1 frozen fallback verification changed")
    return FullGroundFallbackVerificationV180r7r1(
        _ISSUER,
        raw,
        document["verification_id"],
    )


__all__ = (
    "ConstructionK7FullGroundFallbackIndependentVerifierV180r7r1Error",
    "EXPECTED_TERMINAL_BUNDLE_ID",
    "EXPECTED_TERMINAL_BYTE_COUNT",
    "EXPECTED_TERMINAL_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "EXPECTED_VERIFICATION_BYTE_COUNT",
    "EXPECTED_VERIFICATION_SHA256",
    "freeze_full_ground_fallback_verification_v180r7r1",
    "verify_full_ground_fallback_terminal_independently_v180r7r1",
)
