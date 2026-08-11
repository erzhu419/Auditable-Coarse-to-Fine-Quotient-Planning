"""Freeze the native accounting boundary for query-bound campaign work.

Occurrence bundles already charge scientific execution, occurrence-local
supervision, and occurrence output fixed points.  Campaign coordination is a
different owner: it constructs and commits the preregistration, accepts each
completed bundle, maintains the ordered event chain, and finalizes the vector
prefix analysis and denominator closure.

This profile fixes exactly which work belongs to that owner and where it enters
the campaign prefix curve.  It deliberately does not issue measurements or a
``WorkVectorV1``.  The route-scoped V1 work-vector vocabulary has no campaign
route kind, and reusing one would silently misclassify post-route work.  A
later additive recorder must implement this profile and its own campaign-scope
vector before any completeness or economics Gate can run.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.accounting_v1 import ReducerEnum, SHARED_AXES
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.105"
PROFILE_KEY = "construction_k7_query_bound_campaign_orchestration_accounting_profile_v1"
PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_CAMPAIGN_ORCHESTRATION_ACCOUNTING_PROFILE_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({PROFILE_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("campaign orchestration accounting domain is not central")

SHARED_RESOURCE_PATHS = shared_v1.SHARED_RESOURCE_PATHS
SUM_SHARED_RESOURCE_PATHS = shared_v1.SUM_SHARED_RESOURCE_PATHS
MAX_SHARED_RESOURCE_PATHS = shared_v1.MAX_SHARED_RESOURCE_PATHS

_ISSUER = object()


class ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileV1Error(
    ValueError
):
    """The campaign accounting owner, window, or projection changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileV1Error(
            f"{label} must be one content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class CampaignOrchestrationWindowSpecV1:
    sequence: int
    window_kind: str
    prefix_charge_point: str
    cardinality: str
    included_operations: tuple[str, ...]
    excluded_operations: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.sequence) is not int
            or self.sequence <= 0
            or type(self.window_kind) is not str
            or not self.window_kind
            or type(self.prefix_charge_point) is not str
            or not self.prefix_charge_point
            or self.cardinality not in {"EXACTLY_ONCE", "ONCE_PER_OCCURRENCE"}
            or type(self.included_operations) is not tuple
            or not self.included_operations
            or tuple(sorted(set(self.included_operations)))
            != self.included_operations
            or type(self.excluded_operations) is not tuple
            or not self.excluded_operations
            or tuple(sorted(set(self.excluded_operations)))
            != self.excluded_operations
            or set(self.included_operations) & set(self.excluded_operations)
        ):
            _fail("campaign orchestration accounting window changed")

    def to_document(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "window_kind": self.window_kind,
            "prefix_charge_point": self.prefix_charge_point,
            "cardinality": self.cardinality,
            "included_operations": list(self.included_operations),
            "excluded_operations": list(self.excluded_operations),
        }


WINDOWS = (
    CampaignOrchestrationWindowSpecV1(
        1,
        "PRE_EXECUTION_PREREGISTRATION",
        "BEFORE_PREFIX_1",
        "EXACTLY_ONCE",
        tuple(
            sorted(
                {
                    "campaign_coordinator_process_launch",
                    "campaign_preregistration_construction_and_semantic_replay",
                    "campaign_preregistration_durable_commit",
                    "preregistration_commit_event_durable_commit",
                }
            )
        ),
        tuple(
            sorted(
                {
                    "standalone_campaign_evaluation_verifier",
                    "standalone_preregistration_evaluation_verifier",
                }
            )
        ),
    ),
    CampaignOrchestrationWindowSpecV1(
        2,
        "REGISTERED_OCCURRENCE_ACCEPTANCE",
        "AFTER_EACH_PREFIX_ELEMENT",
        "ONCE_PER_OCCURRENCE",
        tuple(
            sorted(
                {
                    "complete_bundle_operational_verification",
                    "occurrence_commit_event_durable_commit",
                    "preregistered_input_runtime_and_identity_join",
                }
            )
        ),
        tuple(
            sorted(
                {
                    "occurrence_accounting_output_fixed_point_and_commit",
                    "scientific_occurrence_execution",
                    "standalone_complete_bundle_evaluation_verifier",
                }
            )
        ),
    ),
    CampaignOrchestrationWindowSpecV1(
        3,
        "CAMPAIGN_FINALIZATION",
        "AFTER_FULL_REGISTERED_PREFIX",
        "EXACTLY_ONCE",
        tuple(
            sorted(
                {
                    "campaign_denominator_closure_render_and_commit",
                    "campaign_result_render_and_commit",
                    "operational_vector_prefix_analysis_replay",
                    "vector_prefix_analysis_and_commit_event",
                }
            )
        ),
        tuple(
            sorted(
                {
                    "scientific_planner_reexecution",
                    "standalone_campaign_closure_evaluation_verifier",
                    "standalone_campaign_result_evaluation_verifier",
                }
            )
        ),
    ),
)

MEASUREMENT_METHODS = (
    (
        "common.hash_invocations",
        "COORDINATOR_PROCESS_GLOBAL_SHA256_CONSTRUCTOR_METER_WITH_OCCURRENCE_WINDOWS_SUSPENDED",
    ),
    (
        "common.integrity_checks",
        "PREREGISTERED_NAMED_CAMPAIGN_INTEGRITY_OBLIGATIONS",
    ),
    (
        "common.protocol_checks",
        "PREREGISTERED_NAMED_CAMPAIGN_PROTOCOL_OBLIGATIONS",
    ),
    (
        "io.mounted_bytes_peak",
        "VERIFIED_UPPER_BOUND_OF_SIMULTANEOUSLY_VISIBLE_CAMPAIGN_PAYLOAD",
    ),
    (
        "io.output_bytes",
        "CAMPAIGN_OWNED_OUTPUT_BYTES_FIXED_POINT_EXCLUDING_OCCURRENCE_BUNDLES",
    ),
    (
        "io.read_bytes",
        "PREREGISTERED_PASS_UPPER_BOUND_OVER_CAMPAIGN_OWNED_INPUTS_AND_ARTIFACTS",
    ),
    (
        "io.staged_bytes",
        "EXACT_CAMPAIGN_COORDINATOR_SANDBOX_STAGING_TRAFFIC",
    ),
    (
        "memory.working_bytes_peak",
        "TRUSTED_PARENT_WAIT4_CAMPAIGN_COORDINATOR_UPPER_BOUND",
    ),
    (
        "process.launches",
        "CAMPAIGN_COORDINATOR_LAUNCH_ONLY_OCCURRENCE_LAUNCHES_EXCLUDED",
    ),
)


@dataclass(frozen=True, slots=True)
class QueryBoundCampaignOrchestrationAccountingProfileV1:
    _issuer: InitVar[object]
    counter_registry_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    windows: tuple[CampaignOrchestrationWindowSpecV1, ...]
    measurement_methods: tuple[tuple[str, str], ...]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or self.windows != WINDOWS
            or self.measurement_methods != MEASUREMENT_METHODS
            or tuple(row.sequence for row in self.windows) != (1, 2, 3)
            or tuple(path for path, _method in self.measurement_methods)
            != SHARED_RESOURCE_PATHS
        ):
            _fail("campaign orchestration accounting profile is caller-minted")
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
        ):
            _cid(value, label)
        object.__setattr__(self, "_profile_id", content_id(PROFILE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        reducers = [
            {
                "path": path,
                "reducer": (
                    ReducerEnum.SUM.value
                    if path in SUM_SHARED_RESOURCE_PATHS
                    else ReducerEnum.MAX.value
                ),
            }
            for path in SHARED_RESOURCE_PATHS
        ]
        return {
            "schema": "acfqp.construction_k7_query_bound_campaign_orchestration_accounting_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "shared_resource_paths": list(SHARED_RESOURCE_PATHS),
            "shared_comparison_axes": list(SHARED_AXES),
            "shared_resource_reducers": reducers,
            "measurement_methods": [
                {"path": path, "method": method}
                for path, method in self.measurement_methods
            ],
            "windows": [row.to_document() for row in self.windows],
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

    @property
    def profile_id(self) -> str:
        expected = content_id(PROFILE_DOMAIN, self._payload())
        if expected != self._profile_id:
            _fail("campaign orchestration accounting profile changed after issuance")
        return expected

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "campaign_orchestration_accounting_profile_id": self.profile_id,
        }


def freeze_query_bound_campaign_orchestration_accounting_profile_v1(
) -> QueryBoundCampaignOrchestrationAccountingProfileV1:
    registry = registry_v6.official_counter_registry_v6()
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(registry, comparison)
    return QueryBoundCampaignOrchestrationAccountingProfileV1(
        _ISSUER,
        registry.registry_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        WINDOWS,
        MEASUREMENT_METHODS,
    )


def verify_query_bound_campaign_orchestration_accounting_profile_bytes_v1(
    profile_bytes: bytes,
) -> QueryBoundCampaignOrchestrationAccountingProfileV1:
    if type(profile_bytes) is not bytes or not profile_bytes:
        _fail("campaign orchestration profile bytes are absent")
    try:
        document = loads_canonical_json(profile_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileV1Error(
            "campaign orchestration profile is not canonical JSON"
        ) from error
    expected = freeze_query_bound_campaign_orchestration_accounting_profile_v1()
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != profile_bytes
        or document != expected.to_document()
    ):
        _fail("campaign orchestration profile differs from exact replay")
    return expected


__all__ = (
    "CampaignOrchestrationWindowSpecV1",
    "ConstructionK7QueryBoundCampaignOrchestrationAccountingProfileV1Error",
    "MEASUREMENT_METHODS",
    "QueryBoundCampaignOrchestrationAccountingProfileV1",
    "SHARED_RESOURCE_PATHS",
    "WINDOWS",
    "freeze_query_bound_campaign_orchestration_accounting_profile_v1",
    "verify_query_bound_campaign_orchestration_accounting_profile_bytes_v1",
)
