"""Strict-owner audit of the nonfresh V0-075 K7 root-cap operation sites.

The V1 site manifest is immutable, but its ``DIRECT_NATIVE_HOOK_REQUIRED``
label was only a proposed hook placement.  It was not a semantic proof that
the operation executing on the batch-native K7 path was owned by the owner
frozen in counter registry V4.  This audit-only successor preserves the V1
manifest identity and classifies the current path without installing a sink
or issuing accounting evidence.

Only an operation whose actual source module equals every referenced V4 leaf
owner is ``DIRECT_VALID_OWNER_MATCHED``.  Registered families inherited from
the learned-support, semantic-instrumentation, or generic abstract-planner
architecture are native zero on this batch-V2 path.  Common/hash/I/O/process
and peak work remains pending.  Batch-V2 LP, quotient, option, concretizer,
and selection work has no native counter family or emitter yet and is recorded
as an explicit gap rather than charged to a merely similar legacy leaf.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import re
from typing import Any

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v4 as registry_v4
from acfqp.phase3e_ids import (
    V075_K7_ROOT_CAP_OPERATION_SITE_AUDIT_V2_DOMAIN,
    V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V2_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp.v075_k7_root_cap_operation_site_manifest_v1 import (
    official_k7_root_cap_operation_site_manifest_v1,
)


SCHEMA_VERSION = "2.0.0"
PROFILE_KEY = "v075_nonfresh_k7_root_cap_operation_site_manifest_v2"
SCOPE_KEY = "NONFRESH_K7_NO_PRIOR_ADAPTIVE_QUOTIENT_ROOT_CAP"

REGISTERED_TOPOLOGY = "K7"
REGISTERED_CONTEXT_KEY = "heldout_graph_k7_confirmatory_v1"
REGISTERED_ARM = "NO_PRIOR"
REGISTERED_ROUTE = "ADAPTIVE_QUOTIENT"
REGISTERED_SCIENTIFIC_ACCEPTED_DRAWS = 4_224
AUDITED_ACQUISITION_OUTCOME_AGGREGATE_ROWS = 41
AUDITED_CLOSURE_REPLAY_GROUND_STEPS = 4_224
AUDITED_CLOSURE_REPLAY_OUTCOME_AGGREGATE_ROWS = 41
REGISTERED_TERMINAL_STATUS = "CHILD_ACTION_ROW_CAP_EXCEEDED"
REGISTERED_TERMINAL_SCOPE = "CONSTRUCTION_OCCURRENCE_ONLY"
REGISTERED_TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"

_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_MODULE = re.compile(r"^acfqp(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


class V075K7RootCapOperationSiteManifestV2Error(ValueError):
    """The strict-owner K7 operation-site audit changed or is malformed."""


class OperationSiteClassificationV2(str, Enum):
    DIRECT_VALID_OWNER_MATCHED = "DIRECT_VALID_OWNER_MATCHED"
    NATIVE_ZERO_NOT_EXECUTED = "NATIVE_ZERO_NOT_EXECUTED"
    REQUIRED_PENDING_HOOK = "REQUIRED_PENDING_HOOK"
    DERIVED_ONLY_RECONCILIATION = "DERIVED_ONLY_RECONCILIATION"
    MISSING_COUNTER_FAMILY = "MISSING_COUNTER_FAMILY"


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

_INHERITED_ZERO_OWNERS = frozenset(
    {
        "abstract_auditor",
        "abstract_planner",
        "v075_learned_support_quotient_planners_v1",
        "v075_semantic_replay_instrumentation_v2",
    }
)

_MISSING_FAMILIES = (
    "batch_v2_concretizer_work",
    "batch_v2_interval_lp_work",
    "batch_v2_option_enumeration_work",
    "batch_v2_quotient_compilation_work",
    "batch_v2_selection_work",
)

_RUNNER = "acfqp.v075_observer_signed_multiround_occurrence_runner_v2"
_CONTROL = "acfqp.v075_observer_signed_batch_control_authority_v2"
_PRIVATE = "acfqp.v075_private_observer_boundary_v2"
_LIVE_MODEL = "acfqp.v075_live_incremental_model_authority_v2"
_PLANNING = "acfqp.v075_batch_native_planning_backend_v2"
_DYNAMIC = "acfqp.v075_live_dynamic_acquisition_authority_v2"


@lru_cache(maxsize=1)
def _v4_profiles() -> tuple[Any, Any, Any, Any]:
    registry = registry_v4.official_counter_registry_v4()
    stage = registry_v4.official_stage_profile_v4(registry)
    comparison = registry_v4.official_comparison_profile_v4(registry)
    actual = registry_v4.official_actual_projection_profile_v4(
        registry, comparison
    )
    return registry, stage, comparison, actual


def _classification(value: Any) -> OperationSiteClassificationV2:
    try:
        return OperationSiteClassificationV2(value)
    except (TypeError, ValueError) as error:
        raise V075K7RootCapOperationSiteManifestV2Error(
            f"unknown operation-site classification {value!r}"
        ) from error


@dataclass(frozen=True, slots=True)
class K7RootCapOperationSiteAuditV2:
    site_key: str
    stages: tuple[registry_v4.ConstructionStageKindV4, ...]
    classification: OperationSiteClassificationV2
    target_paths: tuple[str, ...]
    reducer: ReducerEnum | None
    operation_source_module: str | None
    operation_source_symbol: str | None
    emitter_module: str | None
    emitter_symbol: str | None
    missing_counter_family: str | None
    audit_basis: str

    def __post_init__(self) -> None:
        if (
            type(self.site_key) is not str
            or _KEY.fullmatch(self.site_key) is None
            or type(self.audit_basis) is not str
            or not self.audit_basis
        ):
            raise V075K7RootCapOperationSiteManifestV2Error(
                "operation-site audit key or basis is noncanonical"
            )
        if (
            not self.stages
            or len(set(self.stages)) != len(self.stages)
            or any(stage not in ROOT_CAP_STAGE_PLAN for stage in self.stages)
            or tuple(sorted(self.stages, key=ROOT_CAP_STAGE_PLAN.index))
            != self.stages
        ):
            raise V075K7RootCapOperationSiteManifestV2Error(
                "operation-site audit has a foreign stage set"
            )
        classification = _classification(self.classification)
        object.__setattr__(self, "classification", classification)
        for module, symbol in (
            (self.operation_source_module, self.operation_source_symbol),
            (self.emitter_module, self.emitter_symbol),
        ):
            if (module is None) != (symbol is None):
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "operation source and emitter fields must be typed pairs"
                )
            if module is not None and (
                type(module) is not str
                or _MODULE.fullmatch(module) is None
                or type(symbol) is not str
                or _SYMBOL.fullmatch(symbol) is None
            ):
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "operation source or emitter is noncanonical"
                )

        if tuple(sorted(self.target_paths)) != self.target_paths or len(
            set(self.target_paths)
        ) != len(self.target_paths):
            raise V075K7RootCapOperationSiteManifestV2Error(
                "operation-site target paths must be unique and sorted"
            )
        registry, stage_profile, _comparison, _actual = _v4_profiles()
        if self.target_paths:
            if self.reducer is None:
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "registered target paths require one reducer"
                )
            try:
                reducer = ReducerEnum(self.reducer)
            except (TypeError, ValueError) as error:
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "unknown operation-site reducer"
                ) from error
            object.__setattr__(self, "reducer", reducer)
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
                    raise V075K7RootCapOperationSiteManifestV2Error(
                        f"target {path!r} differs from V4 ownership"
                    )
        elif self.reducer is not None:
            raise V075K7RootCapOperationSiteManifestV2Error(
                "a leafless audit finding cannot declare a reducer"
            )

        if classification is OperationSiteClassificationV2.DIRECT_VALID_OWNER_MATCHED:
            if (
                not self.target_paths
                or self.operation_source_module is None
                or self.emitter_module is not None
                or self.missing_counter_family is not None
            ):
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "direct-valid audit target cannot claim a live emitter"
                )
            owner = self.operation_source_module.rsplit(".", 1)[-1]
            if any(registry.by_path[path].owner != owner for path in self.target_paths):
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "direct-valid source owner differs from V4 leaf metadata"
                )
        elif classification is OperationSiteClassificationV2.NATIVE_ZERO_NOT_EXECUTED:
            if (
                not self.target_paths
                or self.operation_source_module is not None
                or self.emitter_module is not None
                or self.missing_counter_family is not None
            ):
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "native-zero site cannot claim an operation or emitter"
                )
        elif classification is OperationSiteClassificationV2.REQUIRED_PENDING_HOOK:
            if (
                not self.target_paths
                or self.operation_source_module is None
                or self.emitter_module is not None
                or self.missing_counter_family is not None
            ):
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "pending site must name a hook target but no emitter"
                )
        elif (
            classification
            is OperationSiteClassificationV2.DERIVED_ONLY_RECONCILIATION
        ):
            if (
                not self.target_paths
                or self.operation_source_module is None
                or self.emitter_module is not None
                or self.missing_counter_family is not None
                or any(
                    registry.by_path[path].lane.value != "derived_only"
                    for path in self.target_paths
                )
            ):
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "derived-only reconciliation cannot issue a native record"
                )
        elif classification is OperationSiteClassificationV2.MISSING_COUNTER_FAMILY:
            if (
                self.target_paths
                or self.reducer is not None
                or self.operation_source_module is None
                or self.emitter_module is not None
                or self.missing_counter_family not in _MISSING_FAMILIES
            ):
                raise V075K7RootCapOperationSiteManifestV2Error(
                    "missing counter family must remain leafless and emitterless"
                )

    def _payload(self) -> dict[str, Any]:
        registry, stage, _comparison, _actual = _v4_profiles()
        return {
            "schema": "acfqp.v075_k7_root_cap_operation_site_audit.v2",
            "schema_version": SCHEMA_VERSION,
            "scope_key": SCOPE_KEY,
            "counter_registry_id": registry.registry_id,
            "stage_profile_id": stage.stage_profile_id,
            "site_key": self.site_key,
            "stages": [item.value for item in self.stages],
            "classification": self.classification.value,
            "target_paths": list(self.target_paths),
            "reducer": None if self.reducer is None else self.reducer.value,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "emitter_module": self.emitter_module,
            "emitter_symbol": self.emitter_symbol,
            "missing_counter_family": self.missing_counter_family,
            "audit_basis": self.audit_basis,
            "caller_totals_allowed": False,
            "live_evidence_issuer": False,
        }

    @property
    def site_audit_id(self) -> str:
        return content_id(
            V075_K7_ROOT_CAP_OPERATION_SITE_AUDIT_V2_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "site_audit_id": self.site_audit_id}


def _site(
    site_key: str,
    stage: registry_v4.ConstructionStageKindV4,
    classification: OperationSiteClassificationV2,
    target_paths: tuple[str, ...] = (),
    *,
    reducer: ReducerEnum | None = ReducerEnum.SUM,
    source_module: str | None = None,
    source_symbol: str | None = None,
    missing_counter_family: str | None = None,
    audit_basis: str,
) -> K7RootCapOperationSiteAuditV2:
    return K7RootCapOperationSiteAuditV2(
        site_key,
        (stage,),
        classification,
        tuple(sorted(target_paths)),
        reducer if target_paths else None,
        source_module,
        source_symbol,
        None,
        None,
        missing_counter_family,
        audit_basis,
    )


def _common_pending_sites() -> tuple[K7RootCapOperationSiteAuditV2, ...]:
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
                    stage,
                    OperationSiteClassificationV2.REQUIRED_PENDING_HOOK,
                    _COMMON_SUM_PATHS,
                    source_module=module,
                    source_symbol=symbol,
                    audit_basis=(
                        "common/hash/I/O/process accounting has no direct "
                        "operation-site emitter"
                    ),
                ),
                _site(
                    f"{prefix}.capacity-peaks-pending",
                    stage,
                    OperationSiteClassificationV2.REQUIRED_PENDING_HOOK,
                    _COMMON_MAX_PATHS,
                    reducer=ReducerEnum.MAX,
                    source_module=module,
                    source_symbol=symbol,
                    audit_basis=(
                        "mounted and working-set peaks have no trusted "
                        "measurement hook"
                    ),
                ),
            )
        )
    return tuple(result)


def _direct_valid_sites() -> tuple[K7RootCapOperationSiteAuditV2, ...]:
    direct = OperationSiteClassificationV2.DIRECT_VALID_OWNER_MATCHED
    acquisition = registry_v4.ConstructionStageKindV4.INITIAL_ACQUISITION
    build = registry_v4.ConstructionStageKindV4.INITIAL_MODEL_BUILD
    failed = registry_v4.ConstructionStageKindV4.FAILED_ABSTRACT_PREFIX
    closed = (
        registry_v4.ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    )
    return (
        _site(
            "initial-acquisition.private-observer-batch",
            acquisition,
            direct,
            (
                "acquisition.initial_observer_accepted_draws",
                "acquisition.initial_observer_random_word_calls",
                "acquisition.initial_observer_rejections",
                "acquisition.initial_outcome_aggregate_rows",
                "acquisition.initial_signed_batches",
            ),
            source_module=_PRIVATE,
            source_symbol="V075PrivateObserverSessionV2.observe_batch_v2",
            audit_basis="actual batch source equals the V4 private-observer owner",
        ),
        _site(
            "initial-acquisition.support-freeze",
            acquisition,
            direct,
            ("acquisition.initial_support_freezes",),
            source_module=_CONTROL,
            source_symbol=(
                "V075ConstructionControlledPrivateObserverV2."
                "freeze_complete_support_v2"
            ),
            audit_basis="actual support-freeze source equals the V4 owner",
        ),
        _site(
            "initial-build.row-and-source",
            build,
            direct,
            (
                "build.initial_model_rows_built",
                "build.initial_source_units_compiled",
            ),
            source_module=_LIVE_MODEL,
            source_symbol="_build_epoch",
            audit_basis="live epoch builder equals both V4 row owners",
        ),
        _site(
            "initial-build.batch-confidence",
            build,
            direct,
            (
                "build.initial_confidence_event_evaluations",
                "build.initial_exact_likelihood_comparisons",
                "build.initial_interval_log_search_evaluations",
                "build.initial_interval_row_evaluations",
            ),
            source_module=_PLANNING,
            source_symbol="_checkpoint_interval",
            audit_basis="batch-V2 confidence source equals the V4 owner",
        ),
        _site(
            "initial-build.batch-policy-assignments",
            build,
            direct,
            ("build.initial_policy_assignments_evaluated",),
            source_module=_PLANNING,
            source_symbol="plan_v075_construction_numerical_model_v2",
            audit_basis="batch-V2 policy-assignment source equals the V4 owner",
        ),
        _site(
            "failed-prefix.child-catalogue",
            failed,
            direct,
            ("audit.failed_child_catalogues_built",),
            source_module=_DYNAMIC,
            source_symbol="_derive_child_states",
            audit_basis="child-catalogue source equals the V4 dynamic owner",
        ),
        _site(
            "closed.private-observer-replay",
            closed,
            direct,
            (
                "closure.reconciliation_private_replay_ground_steps",
                "closure.reconciliation_private_replay_outcome_aggregate_rows",
                "closure.reconciliation_private_replay_random_word_calls",
                "closure.reconciliation_private_replay_rejections",
            ),
            source_module=_PRIVATE,
            source_symbol="verify_loaded_private_observer_batch_closure_v2",
            audit_basis=(
                "private closure verifier is the actual replay source and "
                "equals the V4 owner"
            ),
        ),
        _site(
            "closed.batch-compiler",
            closed,
            direct,
            (
                "closure.reconciliation_confidence_event_evaluations",
                "closure.reconciliation_exact_likelihood_comparisons",
                "closure.reconciliation_interval_log_search_evaluations",
                "closure.reconciliation_interval_row_evaluations",
                "closure.reconciliation_outcome_projections",
            ),
            source_module=_PLANNING,
            source_symbol="compile_v075_construction_planning_input_v2",
            audit_basis="closed batch compiler equals these V4 owners",
        ),
        _site(
            "closed.batch-policy-assignments",
            closed,
            direct,
            ("closure.reconciliation_policy_assignments_evaluated",),
            source_module=_PLANNING,
            source_symbol="plan_v075_construction_numerical_model_v2",
            audit_basis="closed batch policy source equals the V4 owner",
        ),
    )


def _native_zero_sites() -> tuple[K7RootCapOperationSiteAuditV2, ...]:
    zero = OperationSiteClassificationV2.NATIVE_ZERO_NOT_EXECUTED
    acquisition = registry_v4.ConstructionStageKindV4.INITIAL_ACQUISITION
    build = registry_v4.ConstructionStageKindV4.INITIAL_MODEL_BUILD
    failed = registry_v4.ConstructionStageKindV4.FAILED_ABSTRACT_PREFIX
    closed = (
        registry_v4.ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    )
    return (
        _site(
            "initial-acquisition.no-child-catalogue",
            acquisition,
            zero,
            ("acquisition.initial_child_catalogues_built",),
            audit_basis="the K7 root schedule acquires root rows only",
        ),
        _site(
            "initial-acquisition.no-projection",
            acquisition,
            zero,
            ("acquisition.initial_outcome_projections",),
            audit_basis="current K7 projection occurs during model build",
        ),
        _site(
            "initial-acquisition.no-prior",
            acquisition,
            zero,
            ("acquisition.initial_proposal_entries_bound",),
            audit_basis="registered arm is NO_PRIOR",
        ),
        _site(
            "initial-build.owner-mismatched-outcome-projection",
            build,
            zero,
            ("build.initial_outcome_projections",),
            audit_basis=(
                "actual live-model source differs from the V4 batch-backend owner"
            ),
        ),
        _site(
            "initial-build.no-prior",
            build,
            zero,
            ("build.initial_proposal_entries_bound",),
            audit_basis="registered arm is NO_PRIOR",
        ),
        _site(
            "initial-build.inherited-learned-support",
            build,
            zero,
            (
                "build.initial_concretizer_ground_actions_compiled",
                "build.initial_deterministic_tie_breaks",
                "build.initial_dominance_comparisons",
                "build.initial_interval_lp_allocations",
                "build.initial_quotient_cells_compiled",
                "build.initial_semantic_actions_compiled",
            ),
            audit_basis=(
                "learned-support planner family is not executed by batch-V2 K7"
            ),
        ),
        _site(
            "initial-build.inherited-semantic-instrumentation",
            build,
            zero,
            (
                "build.initial_semantic_record_replays",
                "build.initial_semantic_role_closures",
            ),
            audit_basis=(
                "semantic replay instrumentation is not executed by batch-V2 K7"
            ),
        ),
        _site(
            "failed-prefix.inherited-abstract-planner",
            failed,
            zero,
            (
                "common.abstract_audit_obligations",
                "common.abstract_bellman_backups",
            ),
            audit_basis=(
                "generic abstract auditor/planner counters are not the K7 "
                "dynamic-closure implementation"
            ),
        ),
        _site(
            "closed.no-child-catalogue",
            closed,
            zero,
            ("closure.reconciliation_child_catalogues_built",),
            audit_basis="closed compiler replay does not derive another catalogue",
        ),
        _site(
            "closed.owner-mismatched-model-and-source",
            closed,
            zero,
            (
                "closure.reconciliation_model_rows_built",
                "closure.reconciliation_source_units_compiled",
            ),
            audit_basis=(
                "actual closed batch compiler differs from the V4 live-model owner"
            ),
        ),
        _site(
            "closed.no-prior",
            closed,
            zero,
            ("closure.reconciliation_proposal_entries_bound",),
            audit_basis="registered arm is NO_PRIOR",
        ),
        _site(
            "closed.inherited-learned-support",
            closed,
            zero,
            (
                "closure.reconciliation_concretizer_ground_actions_compiled",
                "closure.reconciliation_deterministic_tie_breaks",
                "closure.reconciliation_dominance_comparisons",
                "closure.reconciliation_interval_lp_allocations",
                "closure.reconciliation_quotient_cells_compiled",
                "closure.reconciliation_semantic_actions_compiled",
            ),
            audit_basis=(
                "learned-support planner family is not executed by batch-V2 K7"
            ),
        ),
        _site(
            "closed.inherited-semantic-instrumentation",
            closed,
            zero,
            (
                "closure.reconciliation_semantic_record_replays",
                "closure.reconciliation_semantic_role_closures",
            ),
            audit_basis=(
                "semantic replay instrumentation is not executed by batch-V2 K7"
            ),
        ),
    )


def _route_pending_site() -> K7RootCapOperationSiteAuditV2:
    closed = (
        registry_v4.ConstructionStageKindV4
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    )
    return _site(
        "closed.route-reconciliation-pending",
        closed,
        OperationSiteClassificationV2.DERIVED_ONLY_RECONCILIATION,
        ("route.attempts", "route.failures", "route.successes"),
        source_module=_RUNNER,
        source_symbol="_closed_result",
        audit_basis=(
            "route attempts/successes/failures are derived-only reconciliation "
            "views and never native records"
        ),
    )


def _missing_counter_family_sites(
) -> tuple[K7RootCapOperationSiteAuditV2, ...]:
    symbols = {
        "batch_v2_concretizer_work": "_option_metric",
        "batch_v2_interval_lp_work": "_extreme",
        "batch_v2_option_enumeration_work": "_options",
        "batch_v2_quotient_compilation_work": "_compile_quotient",
        "batch_v2_selection_work": (
            "plan_v075_construction_numerical_model_v2"
        ),
    }
    result = []
    for stage in (
        registry_v4.ConstructionStageKindV4.INITIAL_MODEL_BUILD,
        (
            registry_v4.ConstructionStageKindV4
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        ),
    ):
        prefix = "initial-build" if stage.value == "INITIAL_MODEL_BUILD" else "closed"
        for family in _MISSING_FAMILIES:
            result.append(
                _site(
                    f"{prefix}.missing.{family.replace('_', '-')}",
                    stage,
                    OperationSiteClassificationV2.MISSING_COUNTER_FAMILY,
                    source_module=_PLANNING,
                    source_symbol=symbols[family],
                    missing_counter_family=family,
                    audit_basis=(
                        "actual batch-V2 work has no V4 leaf and no native emitter"
                    ),
                )
            )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class K7RootCapOperationSiteManifestV2:
    v1_operation_site_manifest_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    sites: tuple[K7RootCapOperationSiteAuditV2, ...]

    def __post_init__(self) -> None:
        for value in (
            self.v1_operation_site_manifest_id,
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
            or len({item.site_audit_id for item in self.sites}) != len(self.sites)
        ):
            raise V075K7RootCapOperationSiteManifestV2Error(
                "site audits must be nonempty, unique, and sorted"
            )
        ownership = set()
        for site in self.sites:
            for stage in site.stages:
                for path in site.target_paths:
                    key = (stage, path)
                    if key in ownership:
                        raise V075K7RootCapOperationSiteManifestV2Error(
                            "one stage/path has multiple audit classifications"
                        )
                    ownership.add(key)

    @property
    def by_key(self) -> dict[str, K7RootCapOperationSiteAuditV2]:
        return {item.site_key: item for item in self.sites}

    def _payload(self) -> dict[str, Any]:
        counts = {
            classification.value: sum(
                item.classification is classification for item in self.sites
            )
            for classification in OperationSiteClassificationV2
        }
        return {
            "schema": "acfqp.v075_k7_root_cap_operation_site_manifest.v2",
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
            "audited_deterministic_trace_facts": {
                "acquisition_outcome_aggregate_rows": (
                    AUDITED_ACQUISITION_OUTCOME_AGGREGATE_ROWS
                ),
                "closure_replay_ground_steps": (
                    AUDITED_CLOSURE_REPLAY_GROUND_STEPS
                ),
                "closure_replay_outcome_aggregate_rows": (
                    AUDITED_CLOSURE_REPLAY_OUTCOME_AGGREGATE_ROWS
                ),
            },
            "trace_facts_are_live_accounting_evidence": False,
            "registered_terminal_status": REGISTERED_TERMINAL_STATUS,
            "registered_terminal_scope": REGISTERED_TERMINAL_SCOPE,
            "registered_terminal_class": REGISTERED_TERMINAL_CLASS,
            "stage_plan": [item.value for item in ROOT_CAP_STAGE_PLAN],
            "forbidden_unused_stages": [
                item.value for item in FORBIDDEN_UNUSED_STAGES
            ],
            "v1_operation_site_manifest_id": self.v1_operation_site_manifest_id,
            "v1_direct_native_semantic_audit_passed": False,
            "v1_sink_imported_or_reused": False,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "sites": [item.to_document() for item in self.sites],
            "site_count": len(self.sites),
            "classification_counts": counts,
            "direct_valid_requires_exact_v4_owner_match": True,
            "native_emitter_installed": False,
            "derived_only_reconciliation_issues_native_record": False,
            "inherited_learned_support_is_native_zero": True,
            "inherited_semantic_instrumentation_is_native_zero": True,
            "inherited_abstract_planner_is_native_zero": True,
            "missing_counter_families": list(_MISSING_FAMILIES),
            "missing_counter_families_have_leaf": False,
            "missing_counter_families_have_emitter": False,
            "closure_private_replay_source": (
                "acfqp.v075_private_observer_boundary_v2."
                "verify_loaded_private_observer_batch_closure_v2"
            ),
            "operation_site_instrumentation_complete": False,
            "counter_family_complete": False,
            "hash_check_io_peak_granularity_profile_complete": False,
            "live_operation_event_count": 0,
            "live_counter_record_count": 0,
            "work_vector_count": 0,
            "comparison_vector_count": 0,
            "actual_projection_proof_count": 0,
            "caller_totals_allowed": False,
            "legacy_summary_translation_allowed": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
        }

    @property
    def manifest_id(self) -> str:
        return content_id(
            V075_K7_ROOT_CAP_OPERATION_SITE_MANIFEST_V2_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}

    def validate_official(self) -> None:
        if self != _expected_manifest():
            raise V075K7RootCapOperationSiteManifestV2Error(
                "official strict-owner K7 operation-site audit changed"
            )


def _expected_manifest() -> K7RootCapOperationSiteManifestV2:
    v1 = official_k7_root_cap_operation_site_manifest_v1()
    v1.validate_official()
    registry, stage, comparison, actual = _v4_profiles()
    sites = tuple(
        sorted(
            (
                *_common_pending_sites(),
                *_direct_valid_sites(),
                *_native_zero_sites(),
                _route_pending_site(),
                *_missing_counter_family_sites(),
            ),
            key=lambda item: item.site_key,
        )
    )
    expected_missing = {
        (stage, family)
        for stage in (
            registry_v4.ConstructionStageKindV4.INITIAL_MODEL_BUILD,
            (
                registry_v4.ConstructionStageKindV4
                .CLOSED_RECONCILIATION_AND_TERMINALIZATION
            ),
        )
        for family in _MISSING_FAMILIES
    }
    observed_missing = {
        (item.stages[0], item.missing_counter_family)
        for item in sites
        if item.classification
        is OperationSiteClassificationV2.MISSING_COUNTER_FAMILY
    }
    if observed_missing != expected_missing:
        raise V075K7RootCapOperationSiteManifestV2Error(
            "batch-V2 missing counter-family audit changed"
        )
    inherited_paths = {
        path
        for item in sites
        if item.classification
        is OperationSiteClassificationV2.NATIVE_ZERO_NOT_EXECUTED
        for path in item.target_paths
        if registry.by_path[path].owner in _INHERITED_ZERO_OWNERS
    }
    expected_inherited = {
        path
        for stage_kind in ROOT_CAP_STAGE_PLAN
        for path in stage.by_stage[stage_kind].allowed_nonzero_paths
        if registry.by_path[path].owner in _INHERITED_ZERO_OWNERS
    }
    if inherited_paths != expected_inherited:
        raise V075K7RootCapOperationSiteManifestV2Error(
            "inherited architecture native-zero classification changed"
        )
    return K7RootCapOperationSiteManifestV2(
        v1.manifest_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        sites,
    )


@lru_cache(maxsize=1)
def official_k7_root_cap_operation_site_manifest_v2(
) -> K7RootCapOperationSiteManifestV2:
    result = _expected_manifest()
    result.validate_official()
    return result


__all__ = [
    "AUDITED_ACQUISITION_OUTCOME_AGGREGATE_ROWS",
    "AUDITED_CLOSURE_REPLAY_GROUND_STEPS",
    "AUDITED_CLOSURE_REPLAY_OUTCOME_AGGREGATE_ROWS",
    "FORBIDDEN_UNUSED_STAGES",
    "K7RootCapOperationSiteAuditV2",
    "K7RootCapOperationSiteManifestV2",
    "OperationSiteClassificationV2",
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
    "V075K7RootCapOperationSiteManifestV2Error",
    "official_k7_root_cap_operation_site_manifest_v2",
]
