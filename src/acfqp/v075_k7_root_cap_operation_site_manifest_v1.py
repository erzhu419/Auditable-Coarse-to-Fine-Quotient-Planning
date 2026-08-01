"""Exact operation-site plan for the nonfresh V0-075 K7 root-cap path.

This module freezes where contract-1.87 native accounting hooks must live.  It
does not install those hooks, execute an occurrence, or issue live accounting
evidence.  In particular, a source symbol appearing here is an audited hook
target, not a claim that the source currently calls this module.

The small context-local adapter is intentionally narrower than a totals API:
one exact site may emit one exact registry leaf at a time into an issuer-owned
``ConstructionActiveStageV3``.  It rejects a foreign registry/profile, an
inactive or wrong stage, an unregistered site/path pair, and a reducer mismatch.
Legacy counter dictionaries and caller-supplied WorkVectors are never accepted.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import re
from typing import Any, Iterator

from acfqp.accounting_v1 import ReducerEnum
from acfqp.construction_accounting_live_v3 import (
    ConstructionActiveStageV3,
    ConstructionOperationEventV3,
)
from acfqp import construction_accounting_registry_v4 as registry_v4
from acfqp.phase3e_ids import (
    V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V1_DOMAIN,
    V075_K7_ROOT_CAP_OPERATION_SITE_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v075_nonfresh_k7_root_cap_operation_site_manifest_v1"
SCOPE_KEY = "NONFRESH_K7_NO_PRIOR_ADAPTIVE_QUOTIENT_ROOT_CAP"

REGISTERED_TOPOLOGY = "K7"
REGISTERED_CONTEXT_KEY = "heldout_graph_k7_confirmatory_v1"
REGISTERED_ARM = "NO_PRIOR"
REGISTERED_ROUTE = "ADAPTIVE_QUOTIENT"
REGISTERED_SCIENTIFIC_ACCEPTED_DRAWS = 4_224
REGISTERED_TERMINAL_STATUS = "CHILD_ACTION_ROW_CAP_EXCEEDED"
REGISTERED_TERMINAL_SCOPE = "CONSTRUCTION_OCCURRENCE_ONLY"
REGISTERED_TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"

_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_MODULE = re.compile(r"^acfqp(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")

_SINK_ISSUER = object()
_ACTIVE_SINK: ContextVar[_BoundOperationSiteSinkV1 | None]


class V075K7RootCapOperationSiteManifestV1Error(ValueError):
    """The exact site manifest or its context-local sink was misused."""


class OperationSiteProofModeV1(str, Enum):
    DIRECT_NATIVE_HOOK_REQUIRED = "DIRECT_NATIVE_HOOK_REQUIRED"
    REQUIRED_PENDING_HOOK = "REQUIRED_PENDING_HOOK"


ROOT_CAP_STAGE_PLAN = (
    registry_v4.ConstructionStageKindV4.PREOPEN_COMMON_PREFIX,
    registry_v4.ConstructionStageKindV4.INITIAL_ACQUISITION,
    registry_v4.ConstructionStageKindV4.INITIAL_MODEL_BUILD,
    registry_v4.ConstructionStageKindV4.FAILED_ABSTRACT_PREFIX,
    (
        registry_v4.ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
)

FORBIDDEN_UNUSED_STAGES = (
    registry_v4.ConstructionStageKindV4.OPEN_INCREMENTAL_ACQUISITION,
    registry_v4.ConstructionStageKindV4.OPEN_CHECKPOINT_REPLANNING,
    registry_v4.ConstructionStageKindV4.LOCAL_ATTEMPT,
    registry_v4.ConstructionStageKindV4.DIRECT_FALLBACK,
    registry_v4.ConstructionStageKindV4.REBUILD,
)

_COMMON_SUM_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "process.exit_failures",
    "process.exit_successes",
    "process.launches",
)
_COMMON_MAX_PATHS = (
    "io.mounted_bytes_peak",
    "memory.working_bytes_peak",
)

_DIRECT_NATIVE_TARGETS = frozenset(
    {
        "acquisition.initial_observer_accepted_draws",
        "acquisition.initial_observer_random_word_calls",
        "acquisition.initial_observer_rejections",
        "acquisition.initial_outcome_aggregate_rows",
        "acquisition.initial_signed_batches",
        "acquisition.initial_support_freezes",
        "audit.failed_child_catalogues_built",
        "build.initial_concretizer_ground_actions_compiled",
        "build.initial_confidence_event_evaluations",
        "build.initial_deterministic_tie_breaks",
        "build.initial_dominance_comparisons",
        "build.initial_exact_likelihood_comparisons",
        "build.initial_interval_log_search_evaluations",
        "build.initial_interval_lp_allocations",
        "build.initial_interval_row_evaluations",
        "build.initial_model_rows_built",
        "build.initial_outcome_projections",
        "build.initial_policy_assignments_evaluated",
        "build.initial_quotient_cells_compiled",
        "build.initial_semantic_actions_compiled",
        "build.initial_semantic_record_replays",
        "build.initial_semantic_role_closures",
        "build.initial_source_units_compiled",
        "closure.reconciliation_concretizer_ground_actions_compiled",
        "closure.reconciliation_confidence_event_evaluations",
        "closure.reconciliation_deterministic_tie_breaks",
        "closure.reconciliation_dominance_comparisons",
        "closure.reconciliation_exact_likelihood_comparisons",
        "closure.reconciliation_interval_log_search_evaluations",
        "closure.reconciliation_interval_lp_allocations",
        "closure.reconciliation_interval_row_evaluations",
        "closure.reconciliation_model_rows_built",
        "closure.reconciliation_outcome_projections",
        "closure.reconciliation_policy_assignments_evaluated",
        "closure.reconciliation_private_replay_ground_steps",
        "closure.reconciliation_private_replay_outcome_aggregate_rows",
        "closure.reconciliation_private_replay_random_word_calls",
        "closure.reconciliation_private_replay_rejections",
        "closure.reconciliation_quotient_cells_compiled",
        "closure.reconciliation_semantic_actions_compiled",
        "closure.reconciliation_semantic_record_replays",
        "closure.reconciliation_semantic_role_closures",
        "closure.reconciliation_source_units_compiled",
        "common.abstract_audit_obligations",
        "common.abstract_bellman_backups",
        "route.failures",
    }
)


@lru_cache(maxsize=1)
def _v4_profiles() -> tuple[Any, Any, Any, Any]:
    registry = registry_v4.official_counter_registry_v4()
    stage = registry_v4.official_stage_profile_v4(registry)
    comparison = registry_v4.official_comparison_profile_v4(registry)
    actual = registry_v4.official_actual_projection_profile_v4(
        registry, comparison
    )
    return registry, stage, comparison, actual


def _proof_mode(value: Any) -> OperationSiteProofModeV1:
    try:
        return OperationSiteProofModeV1(value)
    except (TypeError, ValueError) as error:
        raise V075K7RootCapOperationSiteManifestV1Error(
            f"unknown operation-site proof mode {value!r}"
        ) from error


def _reducer(value: Any) -> ReducerEnum:
    try:
        return ReducerEnum(value)
    except (TypeError, ValueError) as error:
        raise V075K7RootCapOperationSiteManifestV1Error(
            f"unknown operation-site reducer {value!r}"
        ) from error


@dataclass(frozen=True, slots=True)
class K7RootCapOperationSiteV1:
    site_key: str
    source_module: str
    source_symbol: str
    stages: tuple[registry_v4.ConstructionStageKindV4, ...]
    target_paths: tuple[str, ...]
    reducer: ReducerEnum
    proof_mode: OperationSiteProofModeV1

    def __post_init__(self) -> None:
        if (
            type(self.site_key) is not str
            or _KEY.fullmatch(self.site_key) is None
            or type(self.source_module) is not str
            or _MODULE.fullmatch(self.source_module) is None
            or type(self.source_symbol) is not str
            or _SYMBOL.fullmatch(self.source_symbol) is None
        ):
            raise V075K7RootCapOperationSiteManifestV1Error(
                "operation-site source or key is noncanonical"
            )
        if (
            not self.stages
            or len(set(self.stages)) != len(self.stages)
            or any(stage not in ROOT_CAP_STAGE_PLAN for stage in self.stages)
            or tuple(
                sorted(self.stages, key=ROOT_CAP_STAGE_PLAN.index)
            )
            != self.stages
        ):
            raise V075K7RootCapOperationSiteManifestV1Error(
                "operation site has a foreign or noncanonical stage set"
            )
        if (
            not self.target_paths
            or tuple(sorted(self.target_paths)) != self.target_paths
            or len(set(self.target_paths)) != len(self.target_paths)
        ):
            raise V075K7RootCapOperationSiteManifestV1Error(
                "operation-site target paths must be nonempty and sorted"
            )
        reducer = _reducer(self.reducer)
        mode = _proof_mode(self.proof_mode)
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "proof_mode", mode)
        registry, stage_profile, _comparison, _actual = _v4_profiles()
        for path in self.target_paths:
            leaf = registry.by_path.get(path)
            if (
                leaf is None
                or not leaf.required
                or leaf.reducer is not reducer
                or any(
                    path
                    not in stage_profile.by_stage[stage].allowed_nonzero_paths
                    for stage in self.stages
                )
            ):
                raise V075K7RootCapOperationSiteManifestV1Error(
                    f"site target {path!r} differs from v4 ownership"
                )

    def _payload(self) -> dict[str, Any]:
        registry, stage, _comparison, _actual = _v4_profiles()
        return {
            "schema": "acfqp.v075_k7_root_cap_operation_site.v1",
            "schema_version": SCHEMA_VERSION,
            "scope_key": SCOPE_KEY,
            "counter_registry_id": registry.registry_id,
            "stage_profile_id": stage.stage_profile_id,
            "site_key": self.site_key,
            "source_module": self.source_module,
            "source_symbol": self.source_symbol,
            "stages": [item.value for item in self.stages],
            "target_paths": list(self.target_paths),
            "reducer": self.reducer.value,
            "proof_mode": self.proof_mode.value,
            "legacy_summary_translation_allowed": False,
            "caller_totals_allowed": False,
        }

    @property
    def site_id(self) -> str:
        return content_id(
            V075_K7_ROOT_CAP_OPERATION_SITE_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "site_id": self.site_id}


def _site(
    site_key: str,
    source_module: str,
    source_symbol: str,
    stage: registry_v4.ConstructionStageKindV4,
    target_paths: tuple[str, ...],
    *,
    reducer: ReducerEnum = ReducerEnum.SUM,
    proof_mode: OperationSiteProofModeV1 = (
        OperationSiteProofModeV1.DIRECT_NATIVE_HOOK_REQUIRED
    ),
) -> K7RootCapOperationSiteV1:
    return K7RootCapOperationSiteV1(
        site_key,
        source_module,
        source_symbol,
        (stage,),
        tuple(sorted(target_paths)),
        reducer,
        proof_mode,
    )


_RUNNER = "acfqp.v075_observer_signed_multiround_occurrence_runner_v2"
_CONTROL = "acfqp.v075_observer_signed_batch_control_authority_v2"
_LIVE_MODEL = "acfqp.v075_live_incremental_model_authority_v2"
_PLANNING = "acfqp.v075_batch_native_planning_backend_v2"
_DYNAMIC = "acfqp.v075_live_dynamic_acquisition_authority_v2"


def _common_pending_sites() -> tuple[K7RootCapOperationSiteV1, ...]:
    sources = {
        registry_v4.ConstructionStageKindV4.PREOPEN_COMMON_PREFIX: (
            _RUNNER,
            "run_v075_construction_observer_signed_multiround_occurrence_v2",
        ),
        registry_v4.ConstructionStageKindV4.INITIAL_ACQUISITION: (
            _RUNNER,
            "_execute_initial_root_schedule",
        ),
        registry_v4.ConstructionStageKindV4.INITIAL_MODEL_BUILD: (
            _RUNNER,
            "_freeze_root_epoch",
        ),
        registry_v4.ConstructionStageKindV4.FAILED_ABSTRACT_PREFIX: (
            _DYNAMIC,
            "freeze_and_attest_v075_live_dynamic_child_closure_owned_v3",
        ),
        (
            registry_v4.ConstructionStageKindV4
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        ): (_RUNNER, "_close_and_reconcile"),
    }
    result = []
    for stage in ROOT_CAP_STAGE_PLAN:
        module, symbol = sources[stage]
        prefix = stage.value.lower().replace("_", "-")
        result.extend(
            (
                _site(
                    f"{prefix}.common-sum-pending",
                    module,
                    symbol,
                    stage,
                    _COMMON_SUM_PATHS,
                    proof_mode=(
                        OperationSiteProofModeV1.REQUIRED_PENDING_HOOK
                    ),
                ),
                _site(
                    f"{prefix}.capacity-peaks-pending",
                    module,
                    symbol,
                    stage,
                    _COMMON_MAX_PATHS,
                    reducer=ReducerEnum.MAX,
                    proof_mode=(
                        OperationSiteProofModeV1.REQUIRED_PENDING_HOOK
                    ),
                ),
            )
        )
    return tuple(result)


def _direct_native_sites() -> tuple[K7RootCapOperationSiteV1, ...]:
    acquisition = registry_v4.ConstructionStageKindV4.INITIAL_ACQUISITION
    build = registry_v4.ConstructionStageKindV4.INITIAL_MODEL_BUILD
    failed = registry_v4.ConstructionStageKindV4.FAILED_ABSTRACT_PREFIX
    closed = (
        registry_v4.ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    )
    return (
        _site(
            "initial-acquisition.observer-batch",
            _CONTROL,
            "V075ConstructionControlledPrivateObserverV2.execute_batch_intent_v2",
            acquisition,
            (
                "acquisition.initial_observer_accepted_draws",
                "acquisition.initial_observer_random_word_calls",
                "acquisition.initial_observer_rejections",
                "acquisition.initial_outcome_aggregate_rows",
                "acquisition.initial_signed_batches",
            ),
        ),
        _site(
            "initial-acquisition.support-freeze",
            _CONTROL,
            "V075ConstructionControlledPrivateObserverV2.freeze_complete_support_v2",
            acquisition,
            ("acquisition.initial_support_freezes",),
        ),
        _site(
            "initial-build.discovery-outcome-projection",
            _LIVE_MODEL,
            "_compile_numerical_row",
            build,
            ("build.initial_outcome_projections",),
        ),
        _site(
            "initial-build.row-and-source",
            _LIVE_MODEL,
            "_build_epoch",
            build,
            (
                "build.initial_model_rows_built",
                "build.initial_source_units_compiled",
            ),
        ),
        _site(
            "initial-build.validation-confidence",
            _PLANNING,
            "_checkpoint_interval",
            build,
            (
                "build.initial_confidence_event_evaluations",
                "build.initial_exact_likelihood_comparisons",
                "build.initial_interval_log_search_evaluations",
                "build.initial_interval_lp_allocations",
                "build.initial_interval_row_evaluations",
            ),
        ),
        _site(
            "initial-build.semantic-quotient",
            _PLANNING,
            "_compile_quotient",
            build,
            (
                "build.initial_concretizer_ground_actions_compiled",
                "build.initial_quotient_cells_compiled",
                "build.initial_semantic_actions_compiled",
                "build.initial_semantic_record_replays",
                "build.initial_semantic_role_closures",
            ),
        ),
        _site(
            "initial-build.policy-search",
            _PLANNING,
            "plan_v075_construction_numerical_model_v2",
            build,
            (
                "build.initial_deterministic_tie_breaks",
                "build.initial_dominance_comparisons",
                "build.initial_policy_assignments_evaluated",
            ),
        ),
        _site(
            "failed-prefix.child-catalogue",
            _DYNAMIC,
            "_derive_child_states",
            failed,
            ("audit.failed_child_catalogues_built",),
        ),
        _site(
            "failed-prefix.audit-obligation",
            _DYNAMIC,
            "_freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2",
            failed,
            (
                "common.abstract_audit_obligations",
                "common.abstract_bellman_backups",
            ),
        ),
        _site(
            "closed.private-observer-replay",
            _CONTROL,
            "V075ConstructionControlledPrivateObserverV2.close_and_reconcile_v2",
            closed,
            (
                "closure.reconciliation_private_replay_ground_steps",
                "closure.reconciliation_private_replay_outcome_aggregate_rows",
                "closure.reconciliation_private_replay_random_word_calls",
                "closure.reconciliation_private_replay_rejections",
            ),
        ),
        _site(
            "closed.compiler",
            _PLANNING,
            "compile_v075_construction_planning_input_v2",
            closed,
            (
                "closure.reconciliation_confidence_event_evaluations",
                "closure.reconciliation_exact_likelihood_comparisons",
                "closure.reconciliation_interval_log_search_evaluations",
                "closure.reconciliation_interval_lp_allocations",
                "closure.reconciliation_interval_row_evaluations",
                "closure.reconciliation_model_rows_built",
                "closure.reconciliation_outcome_projections",
                "closure.reconciliation_semantic_record_replays",
                "closure.reconciliation_semantic_role_closures",
                "closure.reconciliation_source_units_compiled",
            ),
        ),
        _site(
            "closed.planner",
            _PLANNING,
            "plan_v075_construction_numerical_model_v2",
            closed,
            (
                "closure.reconciliation_concretizer_ground_actions_compiled",
                "closure.reconciliation_deterministic_tie_breaks",
                "closure.reconciliation_dominance_comparisons",
                "closure.reconciliation_policy_assignments_evaluated",
                "closure.reconciliation_quotient_cells_compiled",
                "closure.reconciliation_semantic_actions_compiled",
            ),
        ),
        _site(
            "closed.route-failure",
            _RUNNER,
            "_closed_result",
            closed,
            ("route.failures",),
        ),
    )


@dataclass(frozen=True, slots=True)
class K7RootCapOperationSiteManifestV1:
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    sites: tuple[K7RootCapOperationSiteV1, ...]

    def __post_init__(self) -> None:
        for value in (
            self.counter_registry_id,
            self.stage_profile_id,
            self.comparison_profile_id,
            self.actual_projection_profile_id,
        ):
            parse_content_id(value)
        if (
            not self.sites
            or tuple(sorted(self.sites, key=lambda item: item.site_key))
            != self.sites
            or len({item.site_key for item in self.sites}) != len(self.sites)
            or len({item.site_id for item in self.sites}) != len(self.sites)
        ):
            raise V075K7RootCapOperationSiteManifestV1Error(
                "operation-site records must be nonempty, unique, and sorted"
            )
        ownership = set()
        for site in self.sites:
            for stage in site.stages:
                for path in site.target_paths:
                    key = (stage, path)
                    if key in ownership:
                        raise V075K7RootCapOperationSiteManifestV1Error(
                            "one stage/path has more than one operation site"
                        )
                    ownership.add(key)

    @property
    def by_key(self) -> dict[str, K7RootCapOperationSiteV1]:
        return {item.site_key: item for item in self.sites}

    @property
    def by_id(self) -> dict[str, K7RootCapOperationSiteV1]:
        return {item.site_id: item for item in self.sites}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_root_cap_operation_site_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope_key": SCOPE_KEY,
            "registered_topology": REGISTERED_TOPOLOGY,
            "registered_context_key": REGISTERED_CONTEXT_KEY,
            "registered_arm": REGISTERED_ARM,
            "registered_route": REGISTERED_ROUTE,
            "registered_scientific_accepted_draws": (
                REGISTERED_SCIENTIFIC_ACCEPTED_DRAWS
            ),
            "registered_terminal_status": REGISTERED_TERMINAL_STATUS,
            "registered_terminal_scope": REGISTERED_TERMINAL_SCOPE,
            "registered_terminal_class": REGISTERED_TERMINAL_CLASS,
            "stage_plan": [item.value for item in ROOT_CAP_STAGE_PLAN],
            "forbidden_unused_stages": [
                item.value for item in FORBIDDEN_UNUSED_STAGES
            ],
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": (
                self.actual_projection_profile_id
            ),
            "sites": [item.to_document() for item in self.sites],
            "site_count": len(self.sites),
            "direct_native_hook_site_count": sum(
                item.proof_mode
                is OperationSiteProofModeV1.DIRECT_NATIVE_HOOK_REQUIRED
                for item in self.sites
            ),
            "required_pending_hook_site_count": sum(
                item.proof_mode
                is OperationSiteProofModeV1.REQUIRED_PENDING_HOOK
                for item in self.sites
            ),
            "operation_site_instrumentation_complete": False,
            "hash_check_io_peak_granularity_profile_complete": False,
            "live_operation_event_count": 0,
            "live_counter_record_count": 0,
            "work_vector_count": 0,
            "comparison_vector_count": 0,
            "actual_projection_proof_count": 0,
            "legacy_summary_translation_allowed": False,
            "caller_totals_allowed": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def manifest_id(self) -> str:
        return content_id(
            V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V1_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}

    def validate_official(self) -> None:
        if self != _expected_manifest():
            raise V075K7RootCapOperationSiteManifestV1Error(
                "official K7 root-cap operation-site manifest changed"
            )


def _expected_manifest() -> K7RootCapOperationSiteManifestV1:
    registry, stage, comparison, actual = _v4_profiles()
    sites = tuple(
        sorted(
            (*_common_pending_sites(), *_direct_native_sites()),
            key=lambda item: item.site_key,
        )
    )
    direct_targets = {
        path
        for site in sites
        if site.proof_mode
        is OperationSiteProofModeV1.DIRECT_NATIVE_HOOK_REQUIRED
        for path in site.target_paths
    }
    if direct_targets != _DIRECT_NATIVE_TARGETS:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "audited direct-native operation families changed"
        )
    pending = tuple(
        site
        for site in sites
        if site.proof_mode
        is OperationSiteProofModeV1.REQUIRED_PENDING_HOOK
    )
    if (
        len(pending) != 2 * len(ROOT_CAP_STAGE_PLAN)
        or {
            (site.stages[0], site.reducer, site.target_paths)
            for site in pending
        }
        != {
            (stage_kind, ReducerEnum.SUM, _COMMON_SUM_PATHS)
            for stage_kind in ROOT_CAP_STAGE_PLAN
        }
        | {
            (stage_kind, ReducerEnum.MAX, _COMMON_MAX_PATHS)
            for stage_kind in ROOT_CAP_STAGE_PLAN
        }
    ):
        raise V075K7RootCapOperationSiteManifestV1Error(
            "required pending common/hash/I/O/process/peak sites changed"
        )
    return K7RootCapOperationSiteManifestV1(
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        sites,
    )


@lru_cache(maxsize=1)
def official_k7_root_cap_operation_site_manifest_v1(
) -> K7RootCapOperationSiteManifestV1:
    result = _expected_manifest()
    result.validate_official()
    return result


@dataclass(frozen=True, slots=True)
class _BoundOperationSiteSinkV1:
    issuer: object
    active_stage: ConstructionActiveStageV3
    manifest_id: str

    def __post_init__(self) -> None:
        if self.issuer is not _SINK_ISSUER:
            raise V075K7RootCapOperationSiteManifestV1Error(
                "operation-site sink is caller-minted"
            )
        parse_content_id(self.manifest_id)


_ACTIVE_SINK = ContextVar(
    "acfqp_v075_k7_root_cap_operation_site_sink_v1",
    default=None,
)


@contextmanager
def activate_k7_root_cap_operation_site_sink_v1(
    active_stage: ConstructionActiveStageV3,
) -> Iterator[None]:
    """Bind one issuer-owned v4 stage; nesting and foreign profiles fail."""

    manifest = official_k7_root_cap_operation_site_manifest_v1()
    if type(active_stage) is not ConstructionActiveStageV3:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "operation-site sink requires one exact active stage"
        )
    if (
        active_stage.start.counter_registry_id
        != manifest.counter_registry_id
        or active_stage.start.stage_profile_id != manifest.stage_profile_id
        or active_stage.start.stage_kind not in ROOT_CAP_STAGE_PLAN
    ):
        raise V075K7RootCapOperationSiteManifestV1Error(
            "active stage differs from the exact K7 root-cap v4 profile"
        )
    if _ACTIVE_SINK.get() is not None:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "operation-site sink cannot be nested"
        )
    token: Token[_BoundOperationSiteSinkV1 | None] = _ACTIVE_SINK.set(
        _BoundOperationSiteSinkV1(
            _SINK_ISSUER,
            active_stage,
            manifest.manifest_id,
        )
    )
    try:
        yield
    finally:
        _ACTIVE_SINK.reset(token)


def _bound_site(
    *,
    site_id: str,
    path: str,
    reducer: ReducerEnum,
) -> tuple[_BoundOperationSiteSinkV1, K7RootCapOperationSiteV1]:
    bound = _ACTIVE_SINK.get()
    if type(bound) is not _BoundOperationSiteSinkV1:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "no active K7 root-cap operation-site sink"
        )
    try:
        parse_content_id(site_id)
    except ValueError as error:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "unknown operation-site identity"
        ) from error
    manifest = official_k7_root_cap_operation_site_manifest_v1()
    if bound.manifest_id != manifest.manifest_id:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "bound operation-site manifest is stale"
        )
    site = manifest.by_id.get(site_id)
    if site is None:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "unknown operation-site identity"
        )
    if (
        site.proof_mode
        is not OperationSiteProofModeV1.DIRECT_NATIVE_HOOK_REQUIRED
    ):
        raise V075K7RootCapOperationSiteManifestV1Error(
            "pending operation site cannot issue native evidence"
        )
    if bound.active_stage.start.stage_kind not in site.stages:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "operation site emitted in the wrong construction stage"
        )
    if path not in site.target_paths:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "operation site emitted an unregistered target path"
        )
    if site.reducer is not reducer:
        raise V075K7RootCapOperationSiteManifestV1Error(
            "operation site used the wrong reducer adapter"
        )
    return bound, site


def add_k7_root_cap_native_operation_v1(
    *,
    site_id: str,
    path: str,
    amount: int = 1,
) -> ConstructionOperationEventV3:
    """Emit one direct native SUM observation, never a totals mapping."""

    bound, site = _bound_site(
        site_id=site_id,
        path=path,
        reducer=ReducerEnum.SUM,
    )
    return bound.active_stage.add(
        path,
        amount,
        operation_site_id=site.site_id,
    )


def observe_k7_root_cap_native_peak_v1(
    *,
    site_id: str,
    path: str,
    value: int,
) -> ConstructionOperationEventV3:
    """Emit one direct native MAX observation, never a totals mapping."""

    bound, site = _bound_site(
        site_id=site_id,
        path=path,
        reducer=ReducerEnum.MAX,
    )
    return bound.active_stage.observe_peak(
        path,
        value,
        operation_site_id=site.site_id,
    )


__all__ = [
    "FORBIDDEN_UNUSED_STAGES",
    "K7RootCapOperationSiteManifestV1",
    "K7RootCapOperationSiteV1",
    "OperationSiteProofModeV1",
    "PROFILE_KEY",
    "REGISTERED_ARM",
    "REGISTERED_CONTEXT_KEY",
    "REGISTERED_ROUTE",
    "REGISTERED_SCIENTIFIC_ACCEPTED_DRAWS",
    "REGISTERED_TERMINAL_CLASS",
    "REGISTERED_TERMINAL_SCOPE",
    "REGISTERED_TERMINAL_STATUS",
    "REGISTERED_TOPOLOGY",
    "ROOT_CAP_STAGE_PLAN",
    "SCHEMA_VERSION",
    "SCOPE_KEY",
    "V075K7RootCapOperationSiteManifestV1Error",
    "activate_k7_root_cap_operation_site_sink_v1",
    "add_k7_root_cap_native_operation_v1",
    "observe_k7_root_cap_native_peak_v1",
    "official_k7_root_cap_operation_site_manifest_v1",
]
