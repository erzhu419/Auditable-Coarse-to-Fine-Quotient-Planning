"""Independent bytes replay of the campaign orchestration accounting profile."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.accounting_v1 import ReducerEnum, SHARED_AXES
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_VERIFICATION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_VERIFICATION_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.105"
PRODUCER_PROFILE_KEY = (
    "construction_k7_query_bound_campaign_orchestration_accounting_profile_v1"
)
PROFILE_KEY = (
    "construction_k7_query_bound_campaign_orchestration_accounting_profile_"
    "independent_verifier_v1"
)
PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_V1_DOMAIN
)
VERIFICATION_PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_VERIFICATION_PROFILE_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_VERIFICATION_V1_DOMAIN
)
_ISSUER = object()


class ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileIndependentVerifierV1Error(
    ValueError
):
    """The portable campaign-accounting profile differs from exact replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileIndependentVerifierV1Error(
            f"{label} must be one content ID"
        ) from error


def _windows() -> list[dict[str, Any]]:
    return [
        {
            "sequence": 1,
            "window_kind": "PRE_EXECUTION_PREREGISTRATION",
            "prefix_charge_point": "BEFORE_PREFIX_1",
            "cardinality": "EXACTLY_ONCE",
            "included_operations": sorted(
                {
                    "campaign_coordinator_process_launch",
                    "campaign_preregistration_construction_and_semantic_replay",
                    "campaign_preregistration_durable_commit",
                    "preregistration_commit_event_durable_commit",
                }
            ),
            "excluded_operations": sorted(
                {
                    "standalone_campaign_evaluation_verifier",
                    "standalone_preregistration_evaluation_verifier",
                }
            ),
        },
        {
            "sequence": 2,
            "window_kind": "REGISTERED_OCCURRENCE_ACCEPTANCE",
            "prefix_charge_point": "AFTER_EACH_PREFIX_ELEMENT",
            "cardinality": "ONCE_PER_OCCURRENCE",
            "included_operations": sorted(
                {
                    "complete_bundle_operational_verification",
                    "occurrence_commit_event_durable_commit",
                    "preregistered_input_runtime_and_identity_join",
                }
            ),
            "excluded_operations": sorted(
                {
                    "occurrence_accounting_output_fixed_point_and_commit",
                    "scientific_occurrence_execution",
                    "standalone_complete_bundle_evaluation_verifier",
                }
            ),
        },
        {
            "sequence": 3,
            "window_kind": "CAMPAIGN_FINALIZATION",
            "prefix_charge_point": "AFTER_FULL_REGISTERED_PREFIX",
            "cardinality": "EXACTLY_ONCE",
            "included_operations": sorted(
                {
                    "campaign_denominator_closure_render_and_commit",
                    "campaign_result_render_and_commit",
                    "operational_vector_prefix_analysis_replay",
                    "vector_prefix_analysis_and_commit_event",
                }
            ),
            "excluded_operations": sorted(
                {
                    "scientific_planner_reexecution",
                    "standalone_campaign_closure_evaluation_verifier",
                    "standalone_campaign_result_evaluation_verifier",
                }
            ),
        },
    ]


def _methods() -> list[dict[str, str]]:
    return [
        {
            "path": "common.hash_invocations",
            "method": "COORDINATOR_PROCESS_GLOBAL_SHA256_CONSTRUCTOR_METER_WITH_OCCURRENCE_WINDOWS_SUSPENDED",
        },
        {
            "path": "common.integrity_checks",
            "method": "PREREGISTERED_NAMED_CAMPAIGN_INTEGRITY_OBLIGATIONS",
        },
        {
            "path": "common.protocol_checks",
            "method": "PREREGISTERED_NAMED_CAMPAIGN_PROTOCOL_OBLIGATIONS",
        },
        {
            "path": "io.mounted_bytes_peak",
            "method": "VERIFIED_UPPER_BOUND_OF_SIMULTANEOUSLY_VISIBLE_CAMPAIGN_PAYLOAD",
        },
        {
            "path": "io.output_bytes",
            "method": "CAMPAIGN_OWNED_OUTPUT_BYTES_FIXED_POINT_EXCLUDING_OCCURRENCE_BUNDLES",
        },
        {
            "path": "io.read_bytes",
            "method": "PREREGISTERED_PASS_UPPER_BOUND_OVER_CAMPAIGN_OWNED_INPUTS_AND_ARTIFACTS",
        },
        {
            "path": "io.staged_bytes",
            "method": "EXACT_CAMPAIGN_COORDINATOR_SANDBOX_STAGING_TRAFFIC",
        },
        {
            "path": "memory.working_bytes_peak",
            "method": "TRUSTED_PARENT_WAIT4_CAMPAIGN_COORDINATOR_UPPER_BOUND",
        },
        {
            "path": "process.launches",
            "method": "CAMPAIGN_COORDINATOR_LAUNCH_ONLY_OCCURRENCE_LAUNCHES_EXCLUDED",
        },
    ]


def _expected_profile_document() -> dict[str, Any]:
    registry = registry_v6.official_counter_registry_v6()
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    paths = shared_v1.SHARED_RESOURCE_PATHS
    payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_orchestration_accounting_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PRODUCER_PROFILE_KEY,
        "counter_registry_id": registry.registry_id,
        "comparison_profile_id": comparison.comparison_profile_id,
        "actual_projection_profile_id": actual.actual_projection_profile_id,
        "shared_resource_paths": list(paths),
        "shared_comparison_axes": list(SHARED_AXES),
        "shared_resource_reducers": [
            {
                "path": path,
                "reducer": (
                    ReducerEnum.SUM.value
                    if path in shared_v1.SUM_SHARED_RESOURCE_PATHS
                    else ReducerEnum.MAX.value
                ),
            }
            for path in paths
        ],
        "measurement_methods": _methods(),
        "windows": _windows(),
        "prefix_accounting_rule": (
            "PREREGISTRATION_BEFORE_PREFIX_1_ACCEPTANCE_AFTER_EACH_"
            "OCCURRENCE_FINALIZATION_ONLY_AFTER_FULL_PREFIX"
        ),
        "occurrence_bundle_comparison_vectors_retained_separately": True,
        "occurrence_executor_and_finalizer_work_excluded_from_orchestration": True,
        "operational_bundle_acceptance_verification_included": True,
        "standalone_evaluation_verification_excluded": True,
        "occurrence_process_launches_excluded_from_orchestration": True,
        "campaign_coordinator_process_launch_included_exactly_once": True,
        "sum_paths_add_across_campaign_windows": True,
        "peak_paths_max_across_campaign_windows": True,
        "missing_native_zero_forbidden": True,
        "same_leaf_cross_owner_double_charge_forbidden": True,
        "legacy_work_vector_v1_route_kind_reused_for_campaign": False,
        "campaign_scope_work_vector_schema_required": True,
        "campaign_orchestration_measurement_present": False,
        "campaign_orchestration_work_vector_present": False,
        "campaign_orchestration_comparison_vector_present": False,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "campaign_orchestration_accounting_profile_id": content_id(
            PROFILE_DOMAIN, payload
        ),
    }


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignOrchestrationAccountingProfileVerificationV1:
    _issuer: InitVar[object]
    verification_profile_id: str
    producer_profile_id: str
    profile_bytes_sha256: str
    profile_byte_count: int
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or type(self.profile_byte_count) is not int
            or self.profile_byte_count <= 0
        ):
            _fail("campaign accounting profile verification is caller-minted")
        for value, label in (
            (self.verification_profile_id, "verification profile"),
            (self.producer_profile_id, "producer profile"),
            (self.profile_bytes_sha256, "profile bytes"),
            (self.counter_registry_id, "counter registry"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_orchestration_accounting_profile_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": self.verification_profile_id,
            "campaign_orchestration_accounting_profile_id": self.producer_profile_id,
            "profile_bytes_sha256": self.profile_bytes_sha256,
            "profile_byte_count": self.profile_byte_count,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "all_nine_shared_paths_replayed": True,
            "campaign_window_ownership_replayed": True,
            "occurrence_double_charge_exclusions_replayed": True,
            "prefix_charge_points_replayed": True,
            "legacy_route_kind_reuse_rejected": True,
            "producer_module_imported": False,
            "campaign_orchestration_measurement_present": False,
            "campaign_orchestration_work_vector_present": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        expected = content_id(VERIFICATION_DOMAIN, self._payload())
        if expected != self._verification_id:
            _fail("campaign accounting profile verification changed")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_orchestration_accounting_profile_verification_id": (
                self.verification_id
            ),
        }


def verify_query_bound_campaign_orchestration_accounting_profile_bytes_independently_v1(
    profile_bytes: bytes,
) -> QueryBoundCampaignOrchestrationAccountingProfileVerificationV1:
    if type(profile_bytes) is not bytes or not profile_bytes:
        _fail("campaign accounting profile bytes are absent")
    try:
        document = loads_canonical_json(profile_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileIndependentVerifierV1Error(
            "campaign accounting profile is not canonical JSON"
        ) from error
    expected = _expected_profile_document()
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != profile_bytes
        or document != expected
    ):
        _fail("campaign accounting profile differs from independent replay")
    registry = registry_v6.official_counter_registry_v6()
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    verification_profile_payload = {
        "schema": "acfqp.construction_k7_query_bound_campaign_orchestration_accounting_profile_verification_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "producer_import_forbidden": True,
        "exact_nine_path_inventory_required": True,
        "exact_window_ownership_required": True,
        "exact_prefix_charge_points_required": True,
        "occurrence_double_charge_exclusions_required": True,
        "legacy_route_kind_reuse_must_be_false": True,
        "measurement_claim_must_be_false": True,
        "official_execution_allowed": False,
    }
    verification_profile_id = content_id(
        VERIFICATION_PROFILE_DOMAIN, verification_profile_payload
    )
    return QueryBoundCampaignOrchestrationAccountingProfileVerificationV1(
        _ISSUER,
        verification_profile_id,
        expected["campaign_orchestration_accounting_profile_id"],
        hashlib.sha256(profile_bytes).hexdigest(),
        len(profile_bytes),
        registry.registry_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
    )


__all__ = (
    "ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileIndependentVerifierV1Error",
    "QueryBoundCampaignOrchestrationAccountingProfileVerificationV1",
    "verify_query_bound_campaign_orchestration_accounting_profile_bytes_independently_v1",
)
