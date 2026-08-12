"""Same-window native accounting for the adaptive W5/K6 campaign.

The campaign executes the program-authoritative V3 synthesis route from an
empty immutable catalogue.  Owner-bound hooks aggregate operation events in
the same call window that performs construction, reuse, or the unsupported
closure.  Every non-shared required V7 leaf is then materialized as one exact
``CounterRecordV1`` (including explicit native zeroes) for each route
component.

The nine process/I/O/hash/peak leaves are intentionally absent.  Consequently
this module does not issue a WorkVector, ComparisonVector, Counter Completeness
result, scalar economics result, or official-execution authority.  A later
receipt layer must replace this explicit boundary with independently replayable
complete-window shared-resource evidence.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import importlib
import threading
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_owned_runtime_v1 as owned_runtime
from acfqp import construction_accounting_registry_v7 as registry_v7
from acfqp import construction_k7_adaptive_accounting_phase_v1 as phase_v1
from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import construction_k7_observation_driven_world_model_synthesis_v3 as synthesis_v3
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.accounting_v1 import CounterRecordV1, RouteKindEnum
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_NATIVE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_COMPONENT_NATIVE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_NATIVE_ACCOUNTING_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OPERATION_BOUNDARY_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OPERATION_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_ADAPTIVE_OPERATION_MANIFEST_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.147"
PROFILE_KEY = "construction_k7_adaptive_campaign_native_accounting_v1"
RECORDER_KEY = "construction-k7-adaptive-native-v1"

SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)

PREREGISTRATION_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_ACCOUNTING_PREREGISTRATION_V1_DOMAIN
BOUNDARY_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_OPERATION_BOUNDARY_V1_DOMAIN
MANIFEST_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_OPERATION_MANIFEST_V1_DOMAIN
EVENT_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_OPERATION_EVENT_V1_DOMAIN
COMPONENT_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_COMPONENT_NATIVE_ACCOUNTING_V1_DOMAIN
OCCURRENCE_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_OCCURRENCE_NATIVE_ACCOUNTING_V1_DOMAIN
CAMPAIGN_DOMAIN = CONSTRUCTION_K7_ADAPTIVE_CAMPAIGN_NATIVE_ACCOUNTING_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {
        PREREGISTRATION_DOMAIN,
        BOUNDARY_DOMAIN,
        MANIFEST_DOMAIN,
        EVENT_DOMAIN,
        COMPONENT_DOMAIN,
        OCCURRENCE_DOMAIN,
        CAMPAIGN_DOMAIN,
    }
)
if LOCAL_DOMAINS - PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("adaptive native-accounting domains are not central")

_P = phase_v1.AdaptiveAccountingPhaseV1
_SHARED = frozenset(SHARED_RESOURCE_PATHS)
_BOUNDARY_ISSUER = object()
_MANIFEST_ISSUER = object()
_PREREGISTRATION_ISSUER = object()
_EVENT_ISSUER = object()
_COMPONENT_ISSUER = object()
_OCCURRENCE_ISSUER = object()
_CAMPAIGN_ISSUER = object()
_PROCESS_LOCK = threading.Lock()


class ConstructionK7AdaptiveCampaignNativeAccountingV1Error(RuntimeError):
    """The preregistration, owner binding, event stream, or route changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7AdaptiveCampaignNativeAccountingV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7AdaptiveCampaignNativeAccountingV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive exact integer")
    return value


def _owner(module_name: str, symbol: str) -> tuple[Any, Any]:
    try:
        module = importlib.import_module(module_name)
        selected: Any = module
        for component in symbol.split("."):
            selected = getattr(selected, component)
    except (AttributeError, ImportError) as error:
        raise ConstructionK7AdaptiveCampaignNativeAccountingV1Error(
            f"cannot resolve operation owner {module_name}.{symbol}"
        ) from error
    code = getattr(getattr(selected, "__func__", selected), "__code__", None)
    if code is None:
        _fail(f"operation owner {module_name}.{symbol} has no Python code")
    return module.__dict__, code


@dataclass(frozen=True, slots=True)
class AdaptiveOperationBoundaryV1:
    _issuer: InitVar[object]
    dispatch_key: str
    operation_source_module: str
    operation_source_symbol: str
    allowed_phases: tuple[str, ...]
    common_target_path: str
    local_target_path: str | None
    _boundary_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BOUNDARY_ISSUER
            or type(self.dispatch_key) is not str
            or not self.dispatch_key
            or type(self.operation_source_module) is not str
            or type(self.operation_source_symbol) is not str
            or tuple(sorted(self.allowed_phases)) != self.allowed_phases
            or not self.allowed_phases
            or not set(self.allowed_phases) <= {item.value for item in _P}
            or type(self.common_target_path) is not str
            or (
                self.local_target_path is not None
                and type(self.local_target_path) is not str
            )
        ):
            _fail("adaptive operation boundary is caller-minted or malformed")
        object.__setattr__(self, "_boundary_id", content_id(BOUNDARY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_operation_boundary.v1",
            "schema_version": SCHEMA_VERSION,
            "dispatch_key": self.dispatch_key,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "allowed_phases": list(self.allowed_phases),
            "common_target_path": self.common_target_path,
            "local_target_path": self.local_target_path,
            "direct_caller_code_identity_required": True,
            "same_window_aggregation_only": True,
        }

    @property
    def boundary_id(self) -> str:
        current = content_id(BOUNDARY_DOMAIN, self._payload())
        if current != self._boundary_id:
            _fail("adaptive operation boundary identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operation_boundary_id": self.boundary_id}

    def target_path(self, phase: _P) -> str:
        if phase is _P.LOCAL_RECOVERY and self.local_target_path is not None:
            return self.local_target_path
        return self.common_target_path


_BOUNDARY_ROWS = (
    (
        "partial-support.robust-audit-obligation",
        "acfqp.partial_support_robust_planner_v1",
        "_make_audit",
        (_P.ABSTRACT_CERTIFICATE.value, _P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "common.abstract_audit_obligations",
        None,
    ),
    (
        "partial-support.robust-bellman-backup",
        "acfqp.partial_support_robust_planner_v1",
        "_evaluate_ground_row",
        (_P.ABSTRACT_CERTIFICATE.value, _P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "common.abstract_bellman_backups",
        None,
    ),
    (
        "adaptive-world-model.target-ground-draw",
        "acfqp.transition_tuple_observer_v1",
        "OpaqueTargetLocalTransitionStreamV1.draw",
        (_P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "common.model_acquisition_ground_draws",
        "local.model_acquisition_ground_draws",
    ),
    (
        "adaptive-world-model.target-random-word",
        "acfqp.transition_tuple_observer_v1",
        "OpaqueTargetLocalTransitionStreamV1.draw",
        (_P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "common.model_acquisition_random_word_calls",
        "local.model_acquisition_random_word_calls",
    ),
    (
        "adaptive-world-model.target-random-rejection",
        "acfqp.transition_tuple_observer_v1",
        "OpaqueTargetLocalTransitionStreamV1.draw",
        (_P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "common.model_acquisition_rejections",
        "local.model_acquisition_rejections",
    ),
    (
        "adaptive-world-model.outcome-projection",
        "acfqp.observation_support_graph_acquisition_v1",
        "_split_observation",
        (_P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "common.model_outcome_projections",
        "local.model_outcome_projections",
    ),
    (
        "adaptive-world-model.support-confidence-build",
        "acfqp.observation_support_graph_acquisition_v1",
        "_GraphPartialSupportPrefixStreamV1.extend_validation_to",
        (_P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "common.model_support_confidence_builds",
        "local.model_support_confidence_builds",
    ),
    (
        "adaptive-world-model.graph-model-row-build",
        "acfqp.observation_support_graph_model_v1",
        "build_observation_support_graph_models_v1",
        (_P.ABSTRACT_CERTIFICATE.value, _P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "common.model_bridge_rows_built",
        "local.model_bridge_rows_built",
    ),
    (
        "sequential.confidence.exact-reject-comparison",
        "acfqp.sequential_bernoulli_acquisition_v1",
        "_ExactGridRejectionV1.rejects",
        (_P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "build.initial_sequential_exact_likelihood_comparisons",
        "build.open_checkpoint_sequential_exact_likelihood_comparisons",
    ),
    (
        "sequential.confidence.log-search.lower",
        "acfqp.sequential_bernoulli_acquisition_v1",
        "_last_rejected_lower_grid_index",
        (_P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "build.initial_sequential_interval_log_search_evaluations",
        "build.open_checkpoint_sequential_interval_log_search_evaluations",
    ),
    (
        "sequential.confidence.log-search.upper",
        "acfqp.sequential_bernoulli_acquisition_v1",
        "_first_rejected_upper_grid_index",
        (_P.COMMON_PREFIX.value, _P.LOCAL_RECOVERY.value),
        "build.initial_sequential_interval_log_search_evaluations",
        "build.open_checkpoint_sequential_interval_log_search_evaluations",
    ),
    (
        "adaptive-world-model.constructor-program-candidate",
        "acfqp.construction_k7_observed_capability_program_synthesis_v1",
        "synthesize_observed_capability_program_v1",
        (_P.COMMON_PREFIX.value,),
        "common.constructor_program_candidate_evaluations",
        None,
    ),
    (
        "adaptive-world-model.catalogue-selection",
        "acfqp.construction_k7_heldout_reusable_model_catalogue_v1",
        "select_heldout_reusable_model_v1",
        (_P.ABSTRACT_CERTIFICATE.value, _P.COMMON_PREFIX.value),
        "common.model_catalogue_selection_evaluations",
        None,
    ),
    (
        "adaptive-world-model.catalogue-promotion",
        "acfqp.construction_k7_observation_driven_world_model_synthesis_v1",
        "run_observation_driven_world_model_synthesis_v1",
        (_P.LOCAL_RECOVERY.value,),
        "local.model_catalogue_promotion_events",
        "local.model_catalogue_promotion_events",
    ),
    (
        "adaptive-world-model.coordinate-candidate-evaluation",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "local.model_coordinate_candidate_evaluations",
        "local.model_coordinate_candidate_evaluations",
    ),
    (
        "adaptive-world-model.coordinate-candidate-model-row-build",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "local.model_coordinate_candidate_rows_built",
        "local.model_coordinate_candidate_rows_built",
    ),
    (
        "adaptive-world-model.coordinate-candidate-bellman-backup",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "local.model_coordinate_candidate_bellman_backups",
        "local.model_coordinate_candidate_bellman_backups",
    ),
    (
        "adaptive-world-model.coordinate-candidate-audit-obligation",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "local.model_coordinate_candidate_audit_obligations",
        "local.model_coordinate_candidate_audit_obligations",
    ),
    (
        "adaptive-world-model.coordinate-candidate-exact-reject-comparison",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "build.open_checkpoint_sequential_exact_likelihood_comparisons",
        "build.open_checkpoint_sequential_exact_likelihood_comparisons",
    ),
    (
        "adaptive-world-model.coordinate-candidate-log-search-evaluation",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "build.open_checkpoint_sequential_interval_log_search_evaluations",
        "build.open_checkpoint_sequential_interval_log_search_evaluations",
    ),
    (
        "adaptive-world-model.coordinate-candidate-cache-lookup",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "build.open_checkpoint_confidence_cache_lookups",
        "build.open_checkpoint_confidence_cache_lookups",
    ),
    (
        "adaptive-world-model.coordinate-candidate-cache-hit",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "build.open_checkpoint_confidence_cache_hits",
        "build.open_checkpoint_confidence_cache_hits",
    ),
    (
        "adaptive-world-model.coordinate-candidate-cache-miss",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "build.open_checkpoint_confidence_cache_misses",
        "build.open_checkpoint_confidence_cache_misses",
    ),
    (
        "adaptive-world-model.coordinate-child-hash-invocation",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "common.hash_invocations",
        "common.hash_invocations",
    ),
    (
        "adaptive-world-model.coordinate-worker-launch",
        "acfqp.observation_support_coordinate_refinement_v1",
        "_emit_candidate_accounting_v1",
        (_P.LOCAL_RECOVERY.value,),
        "process.launches",
        "process.launches",
    ),
    (
        "adaptive-world-model.main-hash-invocation",
        "acfqp.construction_k7_adaptive_campaign_native_accounting_v1",
        "run_adaptive_campaign_native_accounting_v1",
        (
            _P.ABSTRACT_CERTIFICATE.value,
            _P.COMMON_PREFIX.value,
            _P.LOCAL_RECOVERY.value,
        ),
        "common.hash_invocations",
        None,
    ),
)


def _expected_boundaries() -> tuple[AdaptiveOperationBoundaryV1, ...]:
    return tuple(
        sorted(
            (
                AdaptiveOperationBoundaryV1(_BOUNDARY_ISSUER, *row)
                for row in _BOUNDARY_ROWS
            ),
            key=lambda item: item.dispatch_key,
        )
    )


@dataclass(frozen=True, slots=True)
class AdaptiveOperationManifestV1:
    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    boundaries: tuple[AdaptiveOperationBoundaryV1, ...]
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _MANIFEST_ISSUER
            or self.boundaries != _expected_boundaries()
            or tuple(sorted(self.boundaries, key=lambda item: item.dispatch_key))
            != self.boundaries
            or len({item.dispatch_key for item in self.boundaries})
            != len(self.boundaries)
        ):
            _fail("adaptive operation manifest changed")
        _cid(self.counter_registry_id, "counter registry")
        _cid(self.stage_profile_id, "stage profile")
        object.__setattr__(self, "_manifest_id", content_id(MANIFEST_DOMAIN, self._payload()))

    @property
    def by_dispatch(self) -> Mapping[str, AdaptiveOperationBoundaryV1]:
        return MappingProxyType({item.dispatch_key: item for item in self.boundaries})

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_operation_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "operation_boundary_ids": [item.boundary_id for item in self.boundaries],
            "source_owner_count": len(self.boundaries),
            "post_hoc_summary_relabeling_allowed": False,
            "independent_replay_work_included": False,
        }

    @property
    def manifest_id(self) -> str:
        current = content_id(MANIFEST_DOMAIN, self._payload())
        if current != self._manifest_id:
            _fail("adaptive operation manifest identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "boundaries": [item.to_document() for item in self.boundaries],
            "operation_manifest_id": self.manifest_id,
        }


def official_adaptive_operation_manifest_v1(
    registry: registry_v7.CounterRegistryV7 | None = None,
) -> AdaptiveOperationManifestV1:
    selected = registry or registry_v7.official_counter_registry_v7()
    selected.validate_official_catalogue()
    stage = registry_v7.official_stage_profile_v7(selected)
    result = AdaptiveOperationManifestV1(
        _MANIFEST_ISSUER, selected.registry_id, stage.stage_profile_id, _expected_boundaries()
    )
    if any(
        path not in selected.by_path
        for row in result.boundaries
        for path in (row.common_target_path, row.local_target_path)
        if path is not None
    ):
        _fail("adaptive operation manifest targets an unregistered counter")
    return result


_SPEC_ROWS = (
    (1, "W5_CONSTRUCT", "opaque_graph_w5_v0", "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED"),
    (2, "W5_REUSE", "opaque_graph_w5_v0", "EXISTING_MODEL_REUSED"),
    (3, "K6_CONSTRUCT", "opaque_graph_k6_v0", "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED"),
    (4, "K6_REUSE", "opaque_graph_k6_v0", "EXISTING_MODEL_REUSED"),
    (5, "K6_MINUS_EDGE_UNSUPPORTED", "opaque_graph_k6_minus_edge_v0", "NO_CERTIFIABLE_CONSTRUCTOR"),
)


@dataclass(frozen=True, slots=True)
class AdaptiveAccountingPreregistrationV1:
    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    operation_manifest_id: str
    initial_catalogue_id: str
    occurrence_specs: tuple[tuple[int, str, str, str], ...]
    _preregistration_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PREREGISTRATION_ISSUER or self.occurrence_specs != _SPEC_ROWS:
            _fail("adaptive accounting preregistration changed")
        for value, label in (
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.comparison_profile_id, "comparison profile"),
            (self.actual_projection_profile_id, "actual projection profile"),
            (self.operation_manifest_id, "operation manifest"),
            (self.initial_catalogue_id, "initial catalogue"),
        ):
            _cid(value, label)
        object.__setattr__(
            self,
            "_preregistration_id",
            content_id(PREREGISTRATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_accounting_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "operation_manifest_id": self.operation_manifest_id,
            "initial_catalogue_id": self.initial_catalogue_id,
            "occurrence_specs": [
                {
                    "occurrence_index": index,
                    "occurrence_role": role,
                    "context_key": context,
                    "expected_result_outcome": outcome,
                }
                for index, role, context, outcome in self.occurrence_specs
            ],
            "three_route_families_preregistered": True,
            "same_window_native_accounting_required": True,
            "shared_resource_receipts_present": False,
            "formal_work_vectors_issued": False,
            "counter_completeness_gate_status": "NOT_RUN",
            "official_execution_allowed": False,
        }

    @property
    def preregistration_id(self) -> str:
        current = content_id(PREREGISTRATION_DOMAIN, self._payload())
        if current != self._preregistration_id:
            _fail("adaptive accounting preregistration identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "adaptive_accounting_preregistration_id": self.preregistration_id}


@dataclass(frozen=True, slots=True)
class AdaptiveAggregatedOperationEventV1:
    _issuer: InitVar[object]
    occurrence_id: str
    operation_boundary_id: str
    phase: str
    target_path: str
    emission_call_count: int
    value: int
    _event_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _EVENT_ISSUER
            or self.phase not in {item.value for item in _P}
            or type(self.target_path) is not str
        ):
            _fail("aggregated adaptive event is caller-minted or malformed")
        _cid(self.occurrence_id, "occurrence")
        _cid(self.operation_boundary_id, "operation boundary")
        _positive(self.emission_call_count, "emission call count")
        _positive(self.value, "aggregated event value")
        object.__setattr__(self, "_event_id", content_id(EVENT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_aggregated_operation_event.v1",
            "occurrence_id": self.occurrence_id,
            "operation_boundary_id": self.operation_boundary_id,
            "phase": self.phase,
            "target_path": self.target_path,
            "emission_call_count": self.emission_call_count,
            "value": self.value,
            "reducer": "sum",
            "same_window_native_event": True,
        }

    @property
    def event_id(self) -> str:
        current = content_id(EVENT_DOMAIN, self._payload())
        if current != self._event_id:
            _fail("aggregated adaptive event identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "adaptive_operation_event_id": self.event_id}


_ROUTE_BY_PHASE = {
    _P.COMMON_PREFIX: RouteKindEnum.ABSTRACT_FAILED_PREFIX,
    _P.LOCAL_RECOVERY: RouteKindEnum.LOCAL_ATTEMPT,
    _P.ABSTRACT_CERTIFICATE: RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
}


@dataclass(frozen=True, slots=True)
class AdaptiveNativeComponentV1:
    _issuer: InitVar[object]
    occurrence_id: str
    phase: str
    route_kind: str
    recorder_id: str
    events: tuple[AdaptiveAggregatedOperationEventV1, ...]
    records: tuple[CounterRecordV1, ...]
    _component_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        try:
            selected_phase = _P(self.phase)
            selected_route = RouteKindEnum(self.route_kind)
        except (TypeError, ValueError) as error:
            raise ConstructionK7AdaptiveCampaignNativeAccountingV1Error(
                "adaptive native component phase or route is invalid"
            ) from error
        if (
            _issuer is not _COMPONENT_ISSUER
            or selected_route is not _ROUTE_BY_PHASE[selected_phase]
            or tuple(sorted(self.events, key=lambda item: item.event_id)) != self.events
            or tuple(sorted(self.records, key=lambda item: item.path)) != self.records
        ):
            _fail("adaptive native component is caller-minted or unordered")
        _cid(self.occurrence_id, "occurrence")
        _cid(self.recorder_id, "recorder")
        registry = registry_v7.official_counter_registry_v7()
        expected_paths = tuple(path for path in registry.required_paths if path not in _SHARED)
        if tuple(row.path for row in self.records) != expected_paths:
            _fail("adaptive component omits a non-shared required counter")
        for row in self.records:
            if row.counter_registry_id != registry.registry_id or row.recorder_id != self.recorder_id:
                _fail("adaptive component counter crossed its registry or recorder")
            row.verify_against(registry.by_path[row.path])
        expected_values: dict[str, int] = {}
        for event in self.events:
            if event.occurrence_id != self.occurrence_id or event.phase != self.phase:
                _fail("adaptive component event crossed its occurrence or phase")
            expected_values[event.target_path] = expected_values.get(event.target_path, 0) + event.value
        if any(row.value != expected_values.get(row.path, 0) for row in self.records):
            _fail("adaptive component records differ from its native events")
        object.__setattr__(self, "_component_id", content_id(COMPONENT_DOMAIN, self._payload()))

    @property
    def values(self) -> Mapping[str, int]:
        return MappingProxyType({row.path: row.value for row in self.records})

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_native_component.v1",
            "occurrence_id": self.occurrence_id,
            "phase": self.phase,
            "route_kind": self.route_kind,
            "recorder_id": self.recorder_id,
            "event_ids": [item.event_id for item in self.events],
            "counter_record_ids": [item.record_id for item in self.records],
            "nonshared_required_counter_count": len(self.records),
            "native_zeroes_explicit": True,
            "shared_resource_placeholder_zeroes_issued": False,
            "formal_work_vector_issued": False,
        }

    @property
    def component_id(self) -> str:
        current = content_id(COMPONENT_DOMAIN, self._payload())
        if current != self._component_id:
            _fail("adaptive native component identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "events": [item.to_document() for item in self.events],
            "counter_records": [item.to_dict() for item in self.records],
            "adaptive_native_component_id": self.component_id,
        }


_EXPECTED_PHASES_BY_OUTCOME = {
    "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED": (
        _P.COMMON_PREFIX.value,
        _P.LOCAL_RECOVERY.value,
        _P.ABSTRACT_CERTIFICATE.value,
    ),
    "EXISTING_MODEL_REUSED": (
        _P.COMMON_PREFIX.value,
        _P.ABSTRACT_CERTIFICATE.value,
    ),
    "NO_CERTIFIABLE_CONSTRUCTOR": (_P.COMMON_PREFIX.value,),
}


@dataclass(frozen=True, slots=True)
class AdaptiveOccurrenceNativeAccountingV1:
    _issuer: InitVar[object]
    preregistration_id: str
    occurrence_index: int
    occurrence_role: str
    context_key: str
    context_id: str
    result_outcome: str
    synthesis_result_id: str
    catalogue_id_before: str
    catalogue_id_after: str
    components: tuple[AdaptiveNativeComponentV1, ...]
    shared_events: tuple[AdaptiveAggregatedOperationEventV1, ...]
    _occurrence_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _OCCURRENCE_ISSUER
            or type(self.occurrence_index) is not int
            or not 1 <= self.occurrence_index <= len(_SPEC_ROWS)
            or (self.occurrence_index, self.occurrence_role, self.context_key, self.result_outcome)
            != _SPEC_ROWS[self.occurrence_index - 1]
            or tuple(item.phase for item in self.components)
            != _EXPECTED_PHASES_BY_OUTCOME[self.result_outcome]
            or tuple(sorted(self.shared_events, key=lambda item: item.event_id))
            != self.shared_events
        ):
            _fail("adaptive occurrence is caller-minted or differs from preregistration")
        context = observer_v1.public_context_by_key_v1(self.context_key)
        if context.context_id != self.context_id:
            _fail("adaptive occurrence public context identity changed")
        for value, label in (
            (self.preregistration_id, "preregistration"),
            (self.synthesis_result_id, "synthesis result"),
            (self.catalogue_id_before, "catalogue before"),
            (self.catalogue_id_after, "catalogue after"),
        ):
            _cid(value, label)
        expected_occurrence_id = content_id(
            OCCURRENCE_DOMAIN,
            {
                "schema": "acfqp.construction_k7_adaptive_occurrence_identity.v1",
                "preregistration_id": self.preregistration_id,
                "occurrence_index": self.occurrence_index,
                "occurrence_role": self.occurrence_role,
                "context_id": self.context_id,
            },
        )
        if any(item.occurrence_id != expected_occurrence_id for item in self.components):
            _fail("adaptive component crossed its occurrence identity")
        if any(
            item.occurrence_id != expected_occurrence_id
            or item.target_path not in _SHARED
            for item in self.shared_events
        ):
            _fail("adaptive shared event crossed its occurrence or path registry")
        common = self.components[0].values
        if common["common.constructor_program_candidate_evaluations"] <= 0 or common[
            "common.model_catalogue_selection_evaluations"
        ] <= 0:
            _fail("adaptive occurrence omitted program or catalogue preparation")
        if self.result_outcome == "MODEL_SYNTHESIZED_PROMOTED_AND_REUSED":
            local = self.components[1].values
            expected_draws = 4_096 if self.context_key == "opaque_graph_w5_v0" else 8_192
            if (
                common["common.model_acquisition_ground_draws"] <= 0
                or local["local.model_acquisition_ground_draws"] != expected_draws
                or local["local.model_catalogue_promotion_events"] != 1
                or self.components[2].values["common.abstract_audit_obligations"] <= 0
            ):
                _fail("constructed occurrence did not retain acquisition, refinement, and recertification")
        elif self.result_outcome == "EXISTING_MODEL_REUSED":
            abstract = self.components[1].values
            if (
                abstract["common.abstract_audit_obligations"] <= 0
                or any(
                    abstract[path] != 0
                    for path in abstract
                    if path.startswith("local.model_")
                )
            ):
                _fail("exact reuse did not remain abstract and zero-ground")
        else:
            if any(
                value
                for path, value in common.items()
                if "model_acquisition" in path
                or "model_bridge" in path
                or path.startswith("local.")
                or path.startswith("fallback.")
            ):
                _fail("unsupported occurrence performed ground/model execution")
        object.__setattr__(self, "_occurrence_id", expected_occurrence_id)

    @property
    def occurrence_id(self) -> str:
        return self._occurrence_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_adaptive_occurrence_native_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "occurrence_index": self.occurrence_index,
            "occurrence_role": self.occurrence_role,
            "context_key": self.context_key,
            "context_id": self.context_id,
            "result_outcome": self.result_outcome,
            "synthesis_result_id": self.synthesis_result_id,
            "catalogue_id_before": self.catalogue_id_before,
            "catalogue_id_after": self.catalogue_id_after,
            "component_ids": [item.component_id for item in self.components],
            "shared_native_event_ids": [item.event_id for item in self.shared_events],
            "same_window_native_events_present": True,
            "nonshared_counter_records_complete": True,
            "shared_resource_receipts_present": False,
            "formal_work_vectors_issued": False,
            "counter_completeness_gate_status": "NOT_RUN",
            "official_execution_allowed": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "components": [item.to_document() for item in self.components],
            "shared_native_events": [item.to_document() for item in self.shared_events],
            "adaptive_occurrence_native_accounting_id": self.occurrence_id,
        }


class _AdaptiveAccountingSessionV1:
    def __init__(
        self,
        *,
        occurrence_id: str,
        registry: registry_v7.CounterRegistryV7,
        manifest: AdaptiveOperationManifestV1,
    ) -> None:
        self._owner_thread = threading.get_ident()
        self._occurrence_id = _cid(occurrence_id, "occurrence")
        self._registry = registry
        self._manifest = manifest
        self._local_started = False
        self._terminal = False
        self._buckets: dict[tuple[_P, str, str], list[int]] = {}
        self._owners = {
            item.dispatch_key: _owner(item.operation_source_module, item.operation_source_symbol)
            for item in manifest.boundaries
        }
        if manifest.counter_registry_id != registry.registry_id:
            _fail("adaptive session manifest crossed its counter registry")

    @property
    def is_terminal(self) -> bool:
        return self._terminal

    def emit_operation(
        self,
        dispatch_key: Any,
        amount: Any = 1,
        *,
        caller_module: Any,
        caller_globals: Any,
        caller_code: Any,
    ) -> None:
        if self._terminal or threading.get_ident() != self._owner_thread:
            _fail("adaptive event escaped its live owner thread")
        if type(dispatch_key) is not str or type(amount) is not int or amount <= 0:
            _fail("adaptive event dispatch or amount is invalid")
        boundary = self._manifest.by_dispatch.get(dispatch_key)
        if boundary is None:
            _fail(f"unregistered adaptive operation {dispatch_key!r}")
        expected_globals, expected_code = self._owners[dispatch_key]
        if (
            caller_module != boundary.operation_source_module
            or caller_globals is not expected_globals
            or caller_code is not expected_code
        ):
            _fail("adaptive operation caller differs from its frozen owner")
        raw_phase = phase_v1.current_adaptive_accounting_phase_v1()
        if raw_phase is _P.LOCAL_RECOVERY:
            self._local_started = True
        effective_phase = (
            raw_phase
            if raw_phase is _P.ABSTRACT_CERTIFICATE or not self._local_started
            else _P.LOCAL_RECOVERY
        )
        if effective_phase.value not in boundary.allowed_phases:
            _fail("adaptive operation occurred outside its registered phase")
        path = boundary.target_path(effective_phase)
        key = (effective_phase, dispatch_key, path)
        bucket = self._buckets.setdefault(key, [0, 0])
        bucket[0] += 1
        bucket[1] += amount

    def finish(
        self, result_outcome: str
    ) -> tuple[
        tuple[AdaptiveNativeComponentV1, ...],
        tuple[AdaptiveAggregatedOperationEventV1, ...],
    ]:
        if self._terminal or threading.get_ident() != self._owner_thread:
            _fail("adaptive session terminalization is invalid")
        if result_outcome == "EXISTING_MODEL_REUSED":
            for key in tuple(self._buckets):
                phase, dispatch, path = key
                if phase is _P.COMMON_PREFIX and dispatch.startswith("partial-support.robust-"):
                    value = self._buckets.pop(key)
                    target = (_P.ABSTRACT_CERTIFICATE, dispatch, path)
                    merged = self._buckets.setdefault(target, [0, 0])
                    merged[0] += value[0]
                    merged[1] += value[1]
        phases = tuple(_P(item) for item in _EXPECTED_PHASES_BY_OUTCOME[result_outcome])
        events: dict[_P, list[AdaptiveAggregatedOperationEventV1]] = {item: [] for item in phases}
        shared_events: list[AdaptiveAggregatedOperationEventV1] = []
        for (phase, dispatch, path), (calls, value) in sorted(
            self._buckets.items(), key=lambda item: (item[0][0].value, item[0][1], item[0][2])
        ):
            if phase not in events:
                _fail("adaptive event phase is inconsistent with the route outcome")
            event = AdaptiveAggregatedOperationEventV1(
                _EVENT_ISSUER,
                self._occurrence_id,
                self._manifest.by_dispatch[dispatch].boundary_id,
                phase.value,
                path,
                calls,
                value,
            )
            (shared_events if path in _SHARED else events[phase]).append(event)
        required = tuple(path for path in self._registry.required_paths if path not in _SHARED)
        components: list[AdaptiveNativeComponentV1] = []
        for phase in phases:
            selected_events = tuple(sorted(events[phase], key=lambda item: item.event_id))
            values: dict[str, int] = {}
            for event in selected_events:
                values[event.target_path] = values.get(event.target_path, 0) + event.value
            recorder_id = content_id(
                EVENT_DOMAIN,
                {
                    "schema": "acfqp.construction_k7_adaptive_recorder_identity.v1",
                    "occurrence_id": self._occurrence_id,
                    "phase": phase.value,
                    "recorder_key": RECORDER_KEY,
                },
            )
            records = tuple(
                CounterRecordV1.observe(
                    self._registry,
                    path,
                    values.get(path, 0),
                    recorder_id=recorder_id,
                )
                for path in required
            )
            components.append(
                AdaptiveNativeComponentV1(
                    _COMPONENT_ISSUER,
                    self._occurrence_id,
                    phase.value,
                    _ROUTE_BY_PHASE[phase].value,
                    recorder_id,
                    selected_events,
                    records,
                )
            )
        self._terminal = True
        return (
            tuple(components),
            tuple(sorted(shared_events, key=lambda item: item.event_id)),
        )


@dataclass(frozen=True, slots=True)
class AdaptiveCampaignNativeAccountingResultV1:
    _issuer: InitVar[object]
    preregistration: AdaptiveAccountingPreregistrationV1
    operation_manifest: AdaptiveOperationManifestV1
    occurrences: tuple[AdaptiveOccurrenceNativeAccountingV1, ...]
    final_catalogue_id: str
    _campaign_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CAMPAIGN_ISSUER
            or type(self.preregistration) is not AdaptiveAccountingPreregistrationV1
            or type(self.operation_manifest) is not AdaptiveOperationManifestV1
            or len(self.occurrences) != len(_SPEC_ROWS)
            or tuple(item.occurrence_index for item in self.occurrences) != (1, 2, 3, 4, 5)
            or any(
                item.preregistration_id != self.preregistration.preregistration_id
                for item in self.occurrences
            )
            or self.operation_manifest.manifest_id != self.preregistration.operation_manifest_id
            or self.occurrences[0].catalogue_id_before != self.preregistration.initial_catalogue_id
            or any(
                left.catalogue_id_after != right.catalogue_id_before
                for left, right in zip(self.occurrences, self.occurrences[1:])
            )
            or self.occurrences[-1].catalogue_id_after != self.final_catalogue_id
        ):
            _fail("adaptive campaign native-accounting chain changed")
        _cid(self.final_catalogue_id, "final catalogue")
        object.__setattr__(self, "_campaign_id", content_id(CAMPAIGN_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        outcomes = tuple(item.result_outcome for item in self.occurrences)
        return {
            "schema": "acfqp.construction_k7_adaptive_campaign_native_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "preregistration_id": self.preregistration.preregistration_id,
            "operation_manifest_id": self.operation_manifest.manifest_id,
            "occurrence_ids": [item.occurrence_id for item in self.occurrences],
            "final_catalogue_id": self.final_catalogue_id,
            "logical_occurrence_count": len(self.occurrences),
            "model_construction_count": outcomes.count("MODEL_SYNTHESIZED_PROMOTED_AND_REUSED"),
            "exact_abstract_reuse_count": outcomes.count("EXISTING_MODEL_REUSED"),
            "unsupported_noncertificate_count": outcomes.count("NO_CERTIFIABLE_CONSTRUCTOR"),
            "same_window_native_events_present": True,
            "nonshared_counter_records_complete": True,
            "shared_resource_receipt_paths": list(SHARED_RESOURCE_PATHS),
            "shared_resource_receipts_present": False,
            "formal_work_vectors_issued": False,
            "formal_comparison_vectors_issued": False,
            "independent_complete_bundle_verifier_present": False,
            "counter_completeness_gate_status": "NOT_RUN",
            "workload_economics_gate_status": "NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }

    @property
    def campaign_id(self) -> str:
        current = content_id(CAMPAIGN_DOMAIN, self._payload())
        if current != self._campaign_id:
            _fail("adaptive campaign native-accounting identity changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "preregistration": self.preregistration.to_document(),
            "operation_manifest": self.operation_manifest.to_document(),
            "occurrences": [item.to_document() for item in self.occurrences],
            "adaptive_campaign_native_accounting_id": self.campaign_id,
        }


def _logical(role: str, parent: str) -> str:
    return hashlib.sha256(f"{PROFILE_KEY}:{role}:{parent}".encode()).hexdigest()


class _BusinessHashMeterV1:
    def __init__(self) -> None:
        self.count = 0
        self._original: Any = None
        self._installed: Any = None

    def __enter__(self) -> "_BusinessHashMeterV1":
        self._original = hashlib.sha256

        def metered(*args: Any, **kwargs: Any) -> Any:
            self.count += 1
            return self._original(*args, **kwargs)

        self._installed = metered
        hashlib.sha256 = metered  # type: ignore[assignment]
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        changed = hashlib.sha256 is not self._installed
        hashlib.sha256 = self._original  # type: ignore[assignment]
        if changed:
            _fail("adaptive business-hash meter binding changed")


def run_adaptive_campaign_native_accounting_v1() -> AdaptiveCampaignNativeAccountingResultV1:
    """Execute and natively account the frozen five-occurrence campaign."""

    if not _PROCESS_LOCK.acquire(blocking=False):
        _fail("adaptive native-accounting runner is already active")
    try:
        if owned_runtime._ACTIVE_RUNTIME.get() is not None:  # noqa: SLF001
            _fail("adaptive accounting cannot nest inside another accounting authority")
        registry = registry_v7.official_counter_registry_v7()
        stage = registry_v7.official_stage_profile_v7(registry)
        comparison = registry_v7.official_comparison_profile_v7(registry)
        actual = registry_v7.official_actual_projection_profile_v7(registry, comparison)
        manifest = official_adaptive_operation_manifest_v1(registry)
        catalogue = catalogue_v1.build_heldout_reusable_model_catalogue_snapshot_v1(())
        preregistration = AdaptiveAccountingPreregistrationV1(
            _PREREGISTRATION_ISSUER,
            registry.registry_id,
            stage.stage_profile_id,
            comparison.comparison_profile_id,
            actual.actual_projection_profile_id,
            manifest.manifest_id,
            catalogue.catalogue_id,
            _SPEC_ROWS,
        )
        occurrences: list[AdaptiveOccurrenceNativeAccountingV1] = []
        reuse_bytes_by_family: dict[str, bytes] = {}
        for index, role, context_key, expected_outcome in _SPEC_ROWS:
            context = observer_v1.public_context_by_key_v1(context_key)
            occurrence_id = content_id(
                OCCURRENCE_DOMAIN,
                {
                    "schema": "acfqp.construction_k7_adaptive_occurrence_identity.v1",
                    "preregistration_id": preregistration.preregistration_id,
                    "occurrence_index": index,
                    "occurrence_role": role,
                    "context_id": context.context_id,
                },
            )
            family = "W5" if context_key == "opaque_graph_w5_v0" else "K6"
            selected_reuse = (
                reuse_bytes_by_family.get(family)
                if expected_outcome == "EXISTING_MODEL_REUSED"
                else None
            )
            catalogue_before = catalogue.catalogue_id
            session = _AdaptiveAccountingSessionV1(
                occurrence_id=occurrence_id, registry=registry, manifest=manifest
            )
            token = owned_runtime._ACTIVE_RUNTIME.set(session)  # noqa: SLF001
            try:
                with _BusinessHashMeterV1() as hash_meter:
                    result = synthesis_v3.run_observation_driven_world_model_synthesis_v3(
                        catalogue,
                        context,
                        logical_occurrence_id=_logical(role, preregistration.preregistration_id),
                        occurrence_ordinal=index,
                        selected_reuse_result_bytes=selected_reuse,
                    )
                owned_runtime.emit_owned_operation_v1(
                    "adaptive-world-model.main-hash-invocation",
                    hash_meter.count,
                )
            finally:
                owned_runtime._ACTIVE_RUNTIME.reset(token)  # noqa: SLF001
            executor = result.executor_result.executor_result
            result_outcome = executor.to_document()["result_outcome"]
            if result_outcome != expected_outcome:
                _fail("adaptive synthesis outcome differs from preregistration")
            components, shared_events = session.finish(result_outcome)
            if executor.promotion is not None:
                if executor.reuse_result_document is None:
                    _fail("constructed adaptive occurrence omitted reusable model bytes")
                reuse_bytes_by_family[family] = canonical_json_bytes(
                    executor.reuse_result_document
                )
            catalogue = executor.final_catalogue
            occurrences.append(
                AdaptiveOccurrenceNativeAccountingV1(
                    _OCCURRENCE_ISSUER,
                    preregistration.preregistration_id,
                    index,
                    role,
                    context_key,
                    context.context_id,
                    result_outcome,
                    result.result_id,
                    catalogue_before,
                    catalogue.catalogue_id,
                    components,
                    shared_events,
                )
            )
        return AdaptiveCampaignNativeAccountingResultV1(
            _CAMPAIGN_ISSUER,
            preregistration,
            manifest,
            tuple(occurrences),
            catalogue.catalogue_id,
        )
    finally:
        _PROCESS_LOCK.release()


__all__ = (
    "AdaptiveAccountingPreregistrationV1",
    "AdaptiveAggregatedOperationEventV1",
    "AdaptiveCampaignNativeAccountingResultV1",
    "AdaptiveNativeComponentV1",
    "AdaptiveOccurrenceNativeAccountingV1",
    "AdaptiveOperationBoundaryV1",
    "AdaptiveOperationManifestV1",
    "ConstructionK7AdaptiveCampaignNativeAccountingV1Error",
    "LOCAL_DOMAINS",
    "SHARED_RESOURCE_PATHS",
    "official_adaptive_operation_manifest_v1",
    "run_adaptive_campaign_native_accounting_v1",
)
