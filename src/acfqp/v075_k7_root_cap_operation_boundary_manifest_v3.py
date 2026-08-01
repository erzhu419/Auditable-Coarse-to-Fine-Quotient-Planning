"""Owner-correct operation-boundary schema for the K7 root-cap profile.

The V2 audit located caller modules but did not always reach the primitive
operation.  This V3 successor binds every V6 addition to an exact source
function and event boundary, and freezes the superseded caller-owned V4 paths
as native zero for this profile.  It remains schema-only: no emitter is
installed and no runtime evidence or completeness claim is made.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import re
from typing import Any

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_registry_v4 as registry_v4
from acfqp import construction_accounting_registry_v5 as registry_v5
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import (
    V075_K7_ROOT_CAP_OPERATION_BOUNDARY_MANIFEST_V3_DOMAIN,
    V075_K7_ROOT_CAP_OPERATION_BOUNDARY_V3_DOMAIN,
    content_id,
    parse_content_id,
)
from acfqp.v075_k7_root_cap_operation_site_manifest_v2 import (
    official_k7_root_cap_operation_site_manifest_v2,
)


SCHEMA_VERSION = "3.0.0"
PROFILE_KEY = "v075_nonfresh_k7_root_cap_operation_boundary_manifest_v3"
SCOPE_KEY = "NONFRESH_K7_NO_PRIOR_ADAPTIVE_QUOTIENT_ROOT_CAP"

REGISTERED_TOPOLOGY = "K7"
REGISTERED_CONTEXT_KEY = "heldout_graph_k7_confirmatory_v1"
REGISTERED_ARM = "NO_PRIOR"
REGISTERED_ROUTE = "ADAPTIVE_QUOTIENT"
REGISTERED_TERMINAL_STATUS = "CHILD_ACTION_ROW_CAP_EXCEEDED"

_KEY = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_MODULE = re.compile(r"^acfqp(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_SYMBOL = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")

_ENGINE = "acfqp.h2_graph_transition_engine_v1"
_PRIVATE = "acfqp.v075_private_observer_boundary_v2"
_CONTROL = "acfqp.v075_observer_signed_batch_control_authority_v2"
_LIVE_MODEL = "acfqp.v075_live_incremental_model_authority_v2"
_PLANNING = "acfqp.v075_batch_native_planning_backend_v2"
_SEQUENTIAL = "acfqp.sequential_bernoulli_acquisition_v1"

ROOT_CAP_STAGE_PLAN = (
    registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX,
    registry_v6.ConstructionStageKindV6.INITIAL_ACQUISITION,
    registry_v6.ConstructionStageKindV6.INITIAL_MODEL_BUILD,
    registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX,
    (
        registry_v6.ConstructionStageKindV6
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
)

FORBIDDEN_UNUSED_STAGES = (
    registry_v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION,
    registry_v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING,
    registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT,
    registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
    registry_v6.ConstructionStageKindV6.REBUILD,
)


class V075K7RootCapOperationBoundaryManifestV3Error(ValueError):
    """The owner-correct boundary schema changed or is malformed."""


class OperationBoundaryClassificationV3(str, Enum):
    V6_NATIVE_BOUNDARY_SCHEMA_ONLY = "V6_NATIVE_BOUNDARY_SCHEMA_ONLY"
    V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY = (
        "V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY"
    )
    V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY = (
        "V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY"
    )
    V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY = (
        "V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY"
    )
    OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO = (
        "OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO"
    )
    LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN = (
        "LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN"
    )
    LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN = (
        "LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN"
    )


class CacheSemanticsV3(str, Enum):
    NOT_CACHE_RELATED = "NOT_CACHE_RELATED"
    LOOKUP_ATTEMPT = "LOOKUP_ATTEMPT"
    HIT_CLASSIFICATION_ONLY = "HIT_CLASSIFICATION_ONLY"
    MISS_CLASSIFICATION_ONLY = "MISS_CLASSIFICATION_ONLY"
    MISS_COMPUTATION_ONLY = "MISS_COMPUTATION_ONLY"


_EMITTABLE_CLASSIFICATIONS = {
    OperationBoundaryClassificationV3.V6_NATIVE_BOUNDARY_SCHEMA_ONLY,
    OperationBoundaryClassificationV3.V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY,
    (
        OperationBoundaryClassificationV3
        .V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY
    ),
    (
        OperationBoundaryClassificationV3
        .V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY
    ),
}


@dataclass(frozen=True, slots=True)
class K7RootCapOperationBoundaryV3:
    boundary_key: str
    dispatch_key: str
    stage: registry_v6.ConstructionStageKindV6
    classification: OperationBoundaryClassificationV3
    target_path: str
    registered_owner: str
    reducer: ReducerEnum
    operation_source_module: str
    operation_source_symbol: str
    operation_boundary: str
    cache_semantics: CacheSemanticsV3
    count_rule: str
    failure_rule: str
    replacement_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        try:
            stage = registry_v6.ConstructionStageKindV6(self.stage)
            classification = OperationBoundaryClassificationV3(
                self.classification
            )
            reducer = ReducerEnum(self.reducer)
            cache = CacheSemanticsV3(self.cache_semantics)
        except (TypeError, ValueError) as error:
            raise V075K7RootCapOperationBoundaryManifestV3Error(
                "operation boundary enum changed"
            ) from error
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "classification", classification)
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "cache_semantics", cache)
        if (
            _KEY.fullmatch(self.boundary_key) is None
            or _KEY.fullmatch(self.dispatch_key) is None
            or type(self.target_path) is not str
            or not self.target_path
            or type(self.registered_owner) is not str
            or not self.registered_owner
            or _MODULE.fullmatch(self.operation_source_module) is None
            or _SYMBOL.fullmatch(self.operation_source_symbol) is None
            or any(
                type(value) is not str or not value
                for value in (
                    self.operation_boundary,
                    self.count_rule,
                    self.failure_rule,
                )
            )
            or tuple(sorted(set(self.replacement_paths)))
            != self.replacement_paths
        ):
            raise V075K7RootCapOperationBoundaryManifestV3Error(
                "operation boundary fields are noncanonical"
            )
        legacy = classification in {
            (
                OperationBoundaryClassificationV3
                .LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN
            ),
            (
                OperationBoundaryClassificationV3
                .LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN
            ),
        }
        if legacy != bool(self.replacement_paths):
            raise V075K7RootCapOperationBoundaryManifestV3Error(
                "legacy correction must bind nonempty replacements"
            )
        if (
            classification
            is OperationBoundaryClassificationV3
            .OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO
            and stage not in FORBIDDEN_UNUSED_STAGES
        ) or (
            classification
            not in {
                OperationBoundaryClassificationV3
                .OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO,
                OperationBoundaryClassificationV3
                .LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN,
                OperationBoundaryClassificationV3
                .LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN,
            }
            and stage in FORBIDDEN_UNUSED_STAGES
        ):
            raise V075K7RootCapOperationBoundaryManifestV3Error(
                "outside-fixture boundary has the wrong stage"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_root_cap_operation_boundary.v3",
            "schema_version": SCHEMA_VERSION,
            "boundary_key": self.boundary_key,
            "dispatch_key": self.dispatch_key,
            "stage": self.stage.value,
            "classification": self.classification.value,
            "target_path": self.target_path,
            "registered_owner": self.registered_owner,
            "reducer": self.reducer.value,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "operation_boundary": self.operation_boundary,
            "cache_semantics": self.cache_semantics.value,
            "count_rule": self.count_rule,
            "failure_rule": self.failure_rule,
            "replacement_paths": list(self.replacement_paths),
            "emittable_in_this_fixture": (
                self.classification in _EMITTABLE_CLASSIFICATIONS
            ),
            "emitter_installed": False,
            "runtime_evidence_issued": False,
            "caller_returned_summary_allowed": False,
            "artifact_cardinality_backfill_allowed": False,
        }

    @property
    def boundary_id(self) -> str:
        return content_id(
            V075_K7_ROOT_CAP_OPERATION_BOUNDARY_V3_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "boundary_id": self.boundary_id}


def _stage_for_path(path: str) -> registry_v6.ConstructionStageKindV6:
    if path.startswith("acquisition.initial_"):
        return registry_v6.ConstructionStageKindV6.INITIAL_ACQUISITION
    if path.startswith("acquisition.incremental_"):
        return registry_v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION
    if path.startswith("build.initial_"):
        return registry_v6.ConstructionStageKindV6.INITIAL_MODEL_BUILD
    if path.startswith("build.open_checkpoint_"):
        return registry_v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING
    if path.startswith("audit.dynamic_"):
        return registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX
    if path.startswith("audit.failed_"):
        return registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX
    if path.startswith("closure.reconciliation_"):
        return (
            registry_v6.ConstructionStageKindV6
            .CLOSED_RECONCILIATION_AND_TERMINALIZATION
        )
    raise V075K7RootCapOperationBoundaryManifestV3Error(
        f"path {path!r} has no V3 stage"
    )


def _source_boundary(
    path: str,
) -> tuple[str, str, str, CacheSemanticsV3, str, str]:
    success_only = (
        "increment once after the named operation boundary completes"
    )
    retain_prior = (
        "a failed current operation emits no completed event; all prior "
        "events remain charged"
    )
    if path in {
        "acquisition.initial_outcome_aggregate_rows",
        "acquisition.incremental_outcome_aggregate_rows",
        "closure.reconciliation_private_replay_outcome_aggregate_rows",
    }:
        return (
            _PRIVATE,
            "_StreamingBatchAccumulatorV2.finish",
            (
                "after each V075BatchOutcomeAggregateV2 construction "
                "succeeds inside the canonical aggregate-row materialization"
            ),
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per successfully materialized aggregate row",
            retain_prior,
        )
    if path in {
        "acquisition.initial_support_freezes",
        "acquisition.incremental_support_freezes",
    }:
        return (
            _CONTROL,
            (
                "V075ConstructionControlledPrivateObserverV2."
                "freeze_complete_support_v2"
            ),
            (
                "after the owned support freeze and its deep snapshot are "
                "both appended to the controller collections"
            ),
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per successfully committed complete support freeze",
            retain_prior,
        )
    if path in {
        "build.initial_confidence_event_evaluations",
        "build.open_checkpoint_confidence_event_evaluations",
        "closure.reconciliation_confidence_event_evaluations",
    }:
        return (
            _PLANNING,
            "_checkpoint_interval",
            "at function entry before registered-checkpoint validation",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per invoked confidence-event evaluation",
            "an invoked evaluation remains charged if it later fails",
        )
    if path in {
        "build.initial_interval_row_evaluations",
        "build.open_checkpoint_interval_row_evaluations",
        "closure.reconciliation_interval_row_evaluations",
    }:
        return (
            _PLANNING,
            "_checkpoint_interval",
            "after V075EventIntervalV2 construction returns successfully",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per successfully constructed interval row",
            retain_prior,
        )
    if path in {
        "build.initial_model_rows_built",
        "build.open_checkpoint_model_rows_built",
    }:
        return (
            _LIVE_MODEL,
            "_compile_numerical_row",
            "after exact numerical-row replay returns the compiled live row",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per successfully compiled changed live-model row",
            retain_prior,
        )
    if path in {
        "build.initial_source_units_compiled",
        "build.open_checkpoint_source_units_compiled",
    }:
        return (
            _LIVE_MODEL,
            "_collect_rows",
            "after one _CollectedRow source unit is appended",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per successfully compiled live row-source unit",
            retain_prior,
        )
    if path in {
        "build.initial_policy_assignments_evaluated",
        "build.open_checkpoint_policy_assignments_evaluated",
        "closure.reconciliation_policy_assignments_evaluated",
    }:
        return (
            _PLANNING,
            "plan_v075_construction_numerical_model_v2",
            (
                "after one under-cap combination completes _option_metric "
                "and its policy-assignment record is formed"
            ),
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per successfully evaluated policy assignment",
            retain_prior,
        )
    if path == "audit.failed_child_catalogues_built":
        return (
            "acfqp.v075_live_dynamic_acquisition_authority_v2",
            "_derive_child_states",
            (
                "after a returned V075LegalActionCatalogueV1 passes the "
                "dynamic-owner checks and is accepted as the current child "
                "catalogue"
            ),
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per accepted complete child catalogue",
            retain_prior,
        )
    if path == "closure.reconciliation_outcome_projections":
        return (
            _PLANNING,
            "_compile_aggregate_rows",
            (
                "after one validated batch outcome aggregate is projected "
                "into its descriptor count or OTHER count"
            ),
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per completed closed aggregate-outcome projection",
            retain_prior,
        )
    if "engine_stream_initialization_merges" in path:
        return (
            _ENGINE,
            "DeterministicH2GraphStreamV1.__init__",
            "immediately after H2GraphKernelV1.merge returns",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if "engine_ground_draws" in path:
        return (
            _ENGINE,
            "DeterministicH2GraphStreamV1.draw",
            "after H2GraphSampleV1 construction returns successfully",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if "engine_random_word_calls" in path:
        return (
            _ENGINE,
            "DeterministicH2GraphStreamV1.draw",
            "inside the rejection loop immediately after splitmix64_v1 returns",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once per completed splitmix64_v1 invocation",
            "words completed before a later draw failure remain charged",
        )
    if "engine_rejections" in path:
        return (
            _ENGINE,
            "DeterministicH2GraphStreamV1.draw",
            "inside the word-at-or-above-acceptance-limit branch",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once for every rejected random word",
            "rejections before a later accepted-draw failure remain charged",
        )
    if "observer_accumulator_updates" in path or (
        "private_replay_accumulator_updates" in path
    ):
        return (
            _PRIVATE,
            "_StreamingBatchAccumulatorV2.append",
            "after the transcript state update completes",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if "signed_batches_materialized" in path:
        return (
            _PRIVATE,
            "V075PrivateObserverSessionV2.observe_batch_v2",
            "after V075SignedObservationBatchV2 construction succeeds",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if "signed_batches_committed" in path:
        return (
            _PRIVATE,
            "V075PrivateObserverSessionV2.observe_batch_v2",
            "after journal append and per-stream cap binding both commit",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if "sequential_exact_likelihood_comparisons" in path:
        return (
            _SEQUENTIAL,
            "_ExactGridRejectionV1.rejects",
            "at logical comparison invocation inside an executing cache-miss body",
            CacheSemanticsV3.MISS_COMPUTATION_ONLY,
            "increment once per exact rejection-predicate invocation",
            "an invoked comparison remains charged if later boundary work fails",
        )
    if "sequential_interval_log_search_evaluations" in path:
        return (
            _SEQUENTIAL,
            "_last_rejected_lower_grid_index",
            "immediately before each lower-bound _log_rejects invocation",
            CacheSemanticsV3.MISS_COMPUTATION_ONLY,
            "increment once per invoked log-search predicate",
            "an invoked predicate remains charged if later correction fails",
        )
    if "confidence_cache_lookups" in path:
        return (
            _SEQUENTIAL,
            "_outer_confidence_bounds_accounted_v2",
            (
                "at entry to the future noncached wrapper, immediately "
                "before its cache-info-before snapshot and lookup attempt"
            ),
            CacheSemanticsV3.LOOKUP_ATTEMPT,
            "increment once per cache lookup attempt",
            "the lookup remains charged if checkpoint construction later fails",
        )
    if "confidence_cache_hits" in path:
        return (
            _SEQUENTIAL,
            "_outer_confidence_bounds_accounted_v2",
            (
                "after cache-info before/after deltas classify exactly one "
                "cache hit and the cached body-entry marker is unchanged"
            ),
            CacheSemanticsV3.HIT_CLASSIFICATION_ONLY,
            "increment once for a verified cache hit",
            retain_prior,
        )
    if "confidence_cache_misses" in path:
        return (
            _SEQUENTIAL,
            "_outer_confidence_bounds_accounted_v2",
            (
                "after cache-info before/after deltas classify exactly one "
                "cache miss and exactly one cached body entry"
            ),
            CacheSemanticsV3.MISS_CLASSIFICATION_ONLY,
            "increment once for each executed cache-miss body",
            "the miss remains charged if its computation later fails",
        )
    if "live_model_row_source_bindings_built" in path:
        return (
            _LIVE_MODEL,
            "_row_source_binding",
            "after V075LiveModelRowSourceBindingV2 construction succeeds",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if "replay_checkpoint_evaluations" in path:
        return (
            _PLANNING,
            "_replay_event_interval",
            "after replay checkpoint construction returns successfully",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if "replay_interval_reconstructions" in path:
        return (
            _PLANNING,
            "_replay_event_interval",
            "after reconstructed interval identity and document equality succeed",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if "option_metric_evaluations" in path:
        return (
            _PLANNING,
            "_option_metric",
            "after one option metric returns successfully",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if "policy_assignment_cap_checks" in path:
        return (
            _PLANNING,
            "plan_v075_construction_numerical_model_v2",
            "inside the combination loop immediately before the hard-cap branch",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            "increment once for every combination subjected to the cap predicate",
            "a cap check remains charged when it rejects the sentinel combination",
        )
    open_batch = {
        "typed_record_replays": (
            "_replay_numerical_model",
            "after one exact typed reconstruction is accepted",
        ),
        "row_behaviors_compiled": (
            "_row_behavior",
            "after V075RowBehaviorV2 construction succeeds",
        ),
        "quotient_cells_compiled": (
            "_compile_quotient",
            "after each V075QuotientCellV2 construction succeeds",
        ),
        "semantic_options_compiled": (
            "_options",
            "after each semantic _Option construction succeeds",
        ),
        "concretizer_ground_actions_bound": (
            "_options",
            "after each distinct ground row is bound into a semantic option",
        ),
        "interval_greedy_allocation_steps": (
            "_extreme",
            (
                "after every entered allocation iteration completes its "
                "probability and residual update, including a zero addition "
                "on the iteration that then breaks"
            ),
        ),
        "policy_order_comparisons": (
            "plan_v075_construction_numerical_model_v2",
            (
                "at the diagnostic-key-greater-than-current-diagnostic "
                "predicate when a current diagnostic exists"
            ),
        ),
        "frontier_obligations_built": (
            "_frontier",
            "after each V075FrontierObligationV2 construction succeeds",
        ),
    }
    for suffix, (symbol, boundary) in open_batch.items():
        if path.endswith(suffix):
            if suffix == "interval_greedy_allocation_steps":
                return (
                    _PLANNING,
                    symbol,
                    boundary,
                    CacheSemanticsV3.NOT_CACHE_RELATED,
                    "increment once per completed for-index allocation update",
                    (
                        "a completed update remains charged if later simplex "
                        "validation fails"
                    ),
                )
            return (
                _PLANNING,
                symbol,
                boundary,
                CacheSemanticsV3.NOT_CACHE_RELATED,
                success_only,
                retain_prior,
            )
    if path.endswith("live_model_support_descriptors_compiled"):
        return (
            _LIVE_MODEL,
            "_compile_numerical_row",
            "after each V075SupportDescriptorV2 is appended to live support",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if path.endswith("live_model_outcome_projections"):
        return (
            _LIVE_MODEL,
            "_compile_numerical_row",
            "after each validation aggregate is projected into the count map",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if path.endswith("batch_v2_support_descriptors_compiled"):
        return (
            _PLANNING,
            "_compile_aggregate_rows",
            "after each V075SupportDescriptorV2 construction succeeds",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if path.endswith("batch_v2_model_rows_built"):
        return (
            _PLANNING,
            "_compile_aggregate_rows",
            "after each V075NumericalRowV2 is appended to compiled rows",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    if path.endswith("batch_v2_row_evidence_bindings_built"):
        return (
            _PLANNING,
            "_compile_aggregate_rows",
            "after each V075RowEvidenceBindingV2 append succeeds",
            CacheSemanticsV3.NOT_CACHE_RELATED,
            success_only,
            retain_prior,
        )
    dynamic = {
        "audit.dynamic_root_rows_scanned": (
            "_derive_child_states",
            "at each model-row iteration after the H2 root-row guard passes",
            "increment once per root row entered",
            "an entered row remains charged if its later scan fails",
        ),
        "audit.dynamic_support_descriptors_scanned": (
            "_derive_child_states",
            "at each root support-descriptor loop entry before terminal filtering",
            "increment once per descriptor entered",
            "an entered descriptor remains charged if its later scan fails",
        ),
        "audit.dynamic_causal_edges_built": (
            "_derive_child_states",
            "after V075LiveDynamicChildCausalEdgeV2 construction succeeds",
            success_only,
            retain_prior,
        ),
        "audit.dynamic_child_action_rows_built": (
            "_derive_child_states",
            (
                "after a returned observation_row_binding_v1 value passes "
                "dynamic-authority checks and is accepted into the dynamic "
                "child row collection"
            ),
            "increment once per accepted dynamic-owner child-row bind",
            "an accepted collection bind remains charged if later work fails",
        ),
        "audit.dynamic_row_cap_checks": (
            "_freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2",
            "immediately before the maximum-new-child-action-rows predicate",
            "increment once when the child-row cap predicate is invoked",
            "the check remains charged whether it authorizes or rejects",
        ),
        "audit.dynamic_child_closure_attestations": (
            "freeze_and_attest_v075_live_dynamic_child_closure_owned_v3",
            (
                "after V075LiveDynamicChildClosureVerificationV2 "
                "construction succeeds"
            ),
            success_only,
            retain_prior,
        ),
    }
    if path in dynamic:
        symbol, boundary, count_rule, failure_rule = dynamic[path]
        return (
            "acfqp.v075_live_dynamic_acquisition_authority_v2",
            symbol,
            boundary,
            CacheSemanticsV3.NOT_CACHE_RELATED,
            count_rule,
            failure_rule,
        )
    raise V075K7RootCapOperationBoundaryManifestV3Error(
        f"V6 path {path!r} has no exact source boundary"
    )


def _dispatch_key_for_source(
    source: tuple[str, str, str, CacheSemanticsV3, str, str],
) -> str:
    _module, symbol, event, _cache, _count, _failure = source
    if symbol == "DeterministicH2GraphStreamV1.__init__":
        return "engine.stream-init.merge"
    if symbol == "DeterministicH2GraphStreamV1.draw":
        if "H2GraphSampleV1" in event:
            return "engine.draw.ground-sample"
        if "splitmix64_v1" in event:
            return "engine.draw.random-word"
        if "acceptance-limit" in event:
            return "engine.draw.rejection"
    if symbol == "_StreamingBatchAccumulatorV2.append":
        return "private-observer.accumulator.append"
    if symbol == "_StreamingBatchAccumulatorV2.finish":
        return "private-observer.outcome-aggregate.materialize"
    if symbol.endswith(".freeze_complete_support_v2"):
        return "observer-control.support-freeze.commit"
    if symbol == "V075PrivateObserverSessionV2.observe_batch_v2":
        if "construction" in event:
            return "private-observer.signed-batch.materialize"
        if "journal append" in event:
            return "private-observer.signed-batch.commit"
    if symbol == "_ExactGridRejectionV1.rejects":
        return "sequential.confidence.exact-reject-comparison"
    if symbol == "_last_rejected_lower_grid_index":
        return "sequential.confidence.log-search.lower"
    if symbol == "_first_rejected_upper_grid_index":
        return "sequential.confidence.log-search.upper"
    if symbol == "_outer_confidence_bounds_accounted_v2":
        if "lookup attempt" in event:
            return "sequential.confidence.cache.lookup"
        if "cache hit" in event:
            return "sequential.confidence.cache.hit"
        if "cache miss" in event:
            return "sequential.confidence.cache.miss"
    if symbol == "_row_source_binding":
        return "live-model.row-source-binding"
    if symbol == "_checkpoint_interval":
        if "function entry" in event:
            return "batch-planning.confidence-event.evaluate"
        if "V075EventIntervalV2" in event:
            return "batch-planning.interval-row.construct"
    if symbol == "_replay_event_interval":
        if "checkpoint construction" in event:
            return "batch-planning.replay.checkpoint"
        if "reconstructed interval" in event:
            return "batch-planning.replay.interval-reconstruction"
    if symbol.startswith("_replay_"):
        return "batch-planning.typed-replay." + symbol.removeprefix(
            "_replay_"
        ).replace("_", "-")
    if symbol == "_option_metric":
        return "batch-planning.option-metric"
    if symbol == "plan_v075_construction_numerical_model_v2":
        if "hard-cap" in event:
            return "batch-planning.policy-assignment-cap-check"
        if "under-cap combination" in event:
            return "batch-planning.policy-assignment.success"
        if "diagnostic-key" in event:
            return "batch-planning.policy-order.diagnostic"
        if "feasible-candidate" in event:
            return "batch-planning.policy-order.feasible-best"
    if symbol == "_row_behavior":
        return "batch-planning.row-behavior.compile"
    if symbol == "_compile_quotient":
        return "batch-planning.quotient-cell.compile"
    if symbol == "_options":
        if "semantic _Option" in event:
            return "batch-planning.semantic-option.compile"
        if "distinct ground row" in event:
            return "batch-planning.concretizer-ground-action.bind"
    if symbol == "_extreme":
        return "batch-planning.interval-greedy.extreme"
    if symbol == "_extreme_bounds":
        return "batch-planning.interval-greedy.extreme-bounds"
    if symbol == "_frontier":
        return "batch-planning.frontier-obligation.build"
    if symbol == "_compile_numerical_row":
        if "exact numerical-row replay" in event:
            return "live-model.numerical-row.compile"
        if "SupportDescriptor" in event:
            return "live-model.support-descriptor.compile"
        if "projected into the count map" in event:
            return "live-model.outcome-projection"
    if symbol == "_collect_rows":
        return "live-model.row-source-unit.compile"
    if symbol == "_compile_aggregate_rows":
        if "aggregate is projected" in event:
            return "batch-planning.aggregate.outcome-projection"
        if "SupportDescriptor" in event:
            return "batch-planning.aggregate.support-descriptor.compile"
        if "NumericalRow" in event:
            return "batch-planning.aggregate.model-row.build"
        if "RowEvidenceBinding" in event:
            return "batch-planning.aggregate.row-evidence-binding.build"
    if symbol == "_derive_child_states":
        if "current child catalogue" in event:
            return "dynamic-child.catalogue.accept"
        if "model-row iteration" in event:
            return "dynamic-child.root-row.scan"
        if "support-descriptor" in event:
            return "dynamic-child.support-descriptor.scan"
        if "CausalEdge" in event:
            return "dynamic-child.causal-edge.build"
        if "dynamic child row collection" in event:
            return "dynamic-child.action-row.bind"
    if symbol == "_freeze_v075_live_dynamic_child_closure_from_exact_epoch_v2":
        return "dynamic-child.row-cap.check"
    if symbol == "freeze_and_attest_v075_live_dynamic_child_closure_owned_v3":
        return "dynamic-child.closure.attest"
    raise V075K7RootCapOperationBoundaryManifestV3Error(
        f"operation source {symbol!r} has no canonical dispatch key"
    )


def _boundary(
    *,
    key: str,
    stage: registry_v6.ConstructionStageKindV6,
    classification: OperationBoundaryClassificationV3,
    path: str,
    owner: str,
    reducer: ReducerEnum,
    source: tuple[str, str, str, CacheSemanticsV3, str, str],
    replacements: tuple[str, ...] = (),
    dispatch_key: str | None = None,
) -> K7RootCapOperationBoundaryV3:
    module, symbol, event, cache, count_rule, failure_rule = source
    return K7RootCapOperationBoundaryV3(
        key,
        dispatch_key or _dispatch_key_for_source(source),
        stage,
        classification,
        path,
        owner,
        reducer,
        module,
        symbol,
        event,
        cache,
        count_rule,
        failure_rule,
        tuple(sorted(replacements)),
    )


_TYPED_REPLAY_EXTRA_SITES = (
    "_replay_support_descriptor",
    "_replay_event_interval",
    "_replay_numerical_row",
    "_replay_row_evidence_binding",
    "_replay_construction_planning_input",
    "_replay_construction_lineage",
)


def _multisite_extras(
    path: str,
) -> tuple[
    tuple[str, tuple[str, str, str, CacheSemanticsV3, str, str]],
    ...,
]:
    success_only = (
        "increment once after the named operation boundary completes"
    )
    retain_prior = (
        "a failed current operation emits no completed event; all prior "
        "events remain charged"
    )
    if path.endswith("typed_record_replays"):
        return tuple(
            (
                symbol.removeprefix("_replay_").replace("_", "-"),
                (
                    _PLANNING,
                    symbol,
                    "after exact typed reconstruction equality succeeds",
                    CacheSemanticsV3.NOT_CACHE_RELATED,
                    success_only,
                    retain_prior,
                ),
            )
            for symbol in _TYPED_REPLAY_EXTRA_SITES
        )
    if path.endswith("interval_greedy_allocation_steps"):
        return (
            (
                "lightweight-bounds",
                (
                    _PLANNING,
                    "_extreme_bounds",
                    (
                        "after every entered allocation iteration completes "
                        "its probability and residual update, including a "
                        "zero addition on the iteration that then breaks"
                    ),
                    CacheSemanticsV3.NOT_CACHE_RELATED,
                    "increment once per completed for-index allocation update",
                    (
                        "a completed update remains charged if later simplex "
                        "validation fails"
                    ),
                ),
            ),
        )
    if path.endswith("policy_order_comparisons"):
        return (
            (
                "feasible-best-order",
                (
                    _PLANNING,
                    "plan_v075_construction_numerical_model_v2",
                    (
                        "at the feasible-candidate key-greater-than-current-"
                        "best predicate when a current best exists"
                    ),
                    CacheSemanticsV3.NOT_CACHE_RELATED,
                    "increment once per invoked feasible-policy ordering predicate",
                    "the comparison remains charged if later planning fails",
                ),
            ),
        )
    return ()


def _v6_addition_boundaries(
) -> tuple[K7RootCapOperationBoundaryV3, ...]:
    registry = registry_v6.official_counter_registry_v6()
    base_paths = set(registry_v5.official_counter_registry_v5().by_path)
    result = []
    for path in sorted(set(registry.by_path) - base_paths):
        leaf = registry.by_path[path]
        stage = _stage_for_path(path)
        classification = (
            OperationBoundaryClassificationV3.OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO
            if stage in FORBIDDEN_UNUSED_STAGES
            else (
                OperationBoundaryClassificationV3
                .V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY
                if leaf.lane.value == "diagnostic"
                else (
                    OperationBoundaryClassificationV3
                    .V6_NATIVE_BOUNDARY_SCHEMA_ONLY
                )
            )
        )
        source = _source_boundary(path)
        result.append(
            _boundary(
                key=f"v6.{path.replace('_', '-').replace('.', '-')}",
                stage=stage,
                classification=classification,
                path=path,
                owner=leaf.owner,
                reducer=leaf.reducer,
                source=source,
            )
        )
        for suffix, extra_source in _multisite_extras(path):
            result.append(
                _boundary(
                    key=(
                        f"v6.{path.replace('_', '-').replace('.', '-')}"
                        f".{suffix}"
                    ),
                    stage=stage,
                    classification=classification,
                    path=path,
                    owner=leaf.owner,
                    reducer=leaf.reducer,
                    source=extra_source,
                )
            )
        if "sequential_interval_log_search_evaluations" in path:
            result.append(
                _boundary(
                    key=(
                        f"v6.{path.replace('_', '-').replace('.', '-')}"
                        ".upper-loop"
                    ),
                    stage=stage,
                    classification=classification,
                    path=path,
                    owner=leaf.owner,
                    reducer=leaf.reducer,
                    source=(
                        _SEQUENTIAL,
                        "_first_rejected_upper_grid_index",
                        (
                            "immediately before each upper-bound "
                            "_log_rejects invocation"
                        ),
                        CacheSemanticsV3.MISS_COMPUTATION_ONLY,
                        "increment once per invoked log-search predicate",
                        (
                            "an invoked predicate remains charged if later "
                            "correction fails"
                        ),
                    ),
                )
            )
    return tuple(result)


def _v5_addition_boundaries(
) -> tuple[K7RootCapOperationBoundaryV3, ...]:
    registry = registry_v6.official_counter_registry_v6()
    v5_registry = registry_v5.official_counter_registry_v5()
    v4_paths = set(registry_v4.official_counter_registry_v4().by_path)
    result = []
    for path in sorted(set(v5_registry.by_path) - v4_paths):
        leaf = registry.by_path[path]
        stage = _stage_for_path(path)
        source = _source_boundary(path)
        result.append(
            _boundary(
                key=f"v5.{path.replace('_', '-').replace('.', '-')}",
                stage=stage,
                classification=(
                    OperationBoundaryClassificationV3
                    .V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY
                ),
                path=path,
                owner=leaf.owner,
                reducer=leaf.reducer,
                source=source,
            )
        )
        for suffix, extra_source in _multisite_extras(path):
            result.append(
                _boundary(
                    key=(
                        f"v5.{path.replace('_', '-').replace('.', '-')}"
                        f".{suffix}"
                    ),
                    stage=stage,
                    classification=(
                        OperationBoundaryClassificationV3
                        .V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY
                    ),
                    path=path,
                    owner=leaf.owner,
                    reducer=leaf.reducer,
                    source=extra_source,
                )
            )
    return tuple(result)


_ROOT_ACTIVE_V4_OWNER_MATCHED_PATHS = frozenset(
    {
        "acquisition.initial_outcome_aggregate_rows",
        "acquisition.initial_support_freezes",
        "audit.failed_child_catalogues_built",
        "build.initial_confidence_event_evaluations",
        "build.initial_interval_row_evaluations",
        "build.initial_model_rows_built",
        "build.initial_policy_assignments_evaluated",
        "build.initial_source_units_compiled",
        "closure.reconciliation_confidence_event_evaluations",
        "closure.reconciliation_interval_row_evaluations",
        "closure.reconciliation_outcome_projections",
        "closure.reconciliation_policy_assignments_evaluated",
        "closure.reconciliation_private_replay_outcome_aggregate_rows",
    }
)

_OPEN_V4_OWNER_MATCHED_PATHS = frozenset(
    {
        "acquisition.incremental_outcome_aggregate_rows",
        "acquisition.incremental_support_freezes",
        "build.open_checkpoint_confidence_event_evaluations",
        "build.open_checkpoint_interval_row_evaluations",
        "build.open_checkpoint_model_rows_built",
        "build.open_checkpoint_policy_assignments_evaluated",
        "build.open_checkpoint_source_units_compiled",
    }
)

_V4_OWNER_MATCHED_BOUNDARY_PATHS = (
    _ROOT_ACTIVE_V4_OWNER_MATCHED_PATHS
    | _OPEN_V4_OWNER_MATCHED_PATHS
)


def _v4_owner_matched_boundaries(
) -> tuple[K7RootCapOperationBoundaryV3, ...]:
    registry = registry_v6.official_counter_registry_v6()
    result = []
    for path in sorted(_V4_OWNER_MATCHED_BOUNDARY_PATHS):
        leaf = registry.by_path[path]
        stage = _stage_for_path(path)
        result.append(
            _boundary(
                key=f"v4-owner.{path.replace('_', '-').replace('.', '-')}",
                stage=stage,
                classification=(
                    OperationBoundaryClassificationV3
                    .OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO
                    if path in _OPEN_V4_OWNER_MATCHED_PATHS
                    else (
                        OperationBoundaryClassificationV3
                        .V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY
                    )
                ),
                path=path,
                owner=leaf.owner,
                reducer=leaf.reducer,
                source=_source_boundary(path),
            )
        )
    return tuple(result)


_LEGACY_REPLACEMENTS = {
    "acquisition.initial_observer_accepted_draws": (
        "acquisition.initial_engine_ground_draws",
    ),
    "acquisition.initial_observer_random_word_calls": (
        "acquisition.initial_engine_random_word_calls",
    ),
    "acquisition.initial_observer_rejections": (
        "acquisition.initial_engine_rejections",
    ),
    "acquisition.initial_signed_batches": (
        "acquisition.initial_signed_batches_committed",
        "acquisition.initial_signed_batches_materialized",
    ),
    "acquisition.incremental_observer_accepted_draws": (
        "acquisition.incremental_engine_ground_draws",
    ),
    "acquisition.incremental_observer_random_word_calls": (
        "acquisition.incremental_engine_random_word_calls",
    ),
    "acquisition.incremental_observer_rejections": (
        "acquisition.incremental_engine_rejections",
    ),
    "acquisition.incremental_signed_batches": (
        "acquisition.incremental_signed_batches_committed",
        "acquisition.incremental_signed_batches_materialized",
    ),
    "build.initial_exact_likelihood_comparisons": (
        "build.initial_sequential_exact_likelihood_comparisons",
    ),
    "build.initial_interval_log_search_evaluations": (
        "build.initial_sequential_interval_log_search_evaluations",
    ),
    "build.open_checkpoint_exact_likelihood_comparisons": (
        "build.open_checkpoint_sequential_exact_likelihood_comparisons",
    ),
    "build.open_checkpoint_interval_log_search_evaluations": (
        "build.open_checkpoint_sequential_interval_log_search_evaluations",
    ),
    "build.open_checkpoint_outcome_projections": (
        "build.open_checkpoint_live_model_outcome_projections",
    ),
    "closure.reconciliation_private_replay_ground_steps": (
        "closure.reconciliation_engine_ground_draws",
    ),
    "closure.reconciliation_private_replay_random_word_calls": (
        "closure.reconciliation_engine_random_word_calls",
    ),
    "closure.reconciliation_private_replay_rejections": (
        "closure.reconciliation_engine_rejections",
    ),
    "closure.reconciliation_exact_likelihood_comparisons": (
        "closure.reconciliation_sequential_exact_likelihood_comparisons",
    ),
    "closure.reconciliation_interval_log_search_evaluations": (
        "closure.reconciliation_sequential_interval_log_search_evaluations",
    ),
}


def _legacy_source(path: str) -> tuple[
    str,
    str,
    str,
    CacheSemanticsV3,
    str,
    str,
]:
    replacement = _LEGACY_REPLACEMENTS[path][0]
    return _source_boundary(replacement)


def _legacy_correction_boundaries(
) -> tuple[K7RootCapOperationBoundaryV3, ...]:
    registry = registry_v6.official_counter_registry_v6()
    result = []
    for path, replacements in sorted(_LEGACY_REPLACEMENTS.items()):
        leaf = registry.by_path[path]
        semantic_split = path.endswith("signed_batches")
        result.append(
            _boundary(
                key=f"legacy-zero.{path.replace('_', '-').replace('.', '-')}",
                stage=_stage_for_path(path),
                classification=(
                    OperationBoundaryClassificationV3
                    .LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN
                    if semantic_split
                    else (
                        OperationBoundaryClassificationV3
                        .LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN
                    )
                ),
                path=path,
                owner=leaf.owner,
                reducer=leaf.reducer,
                source=_legacy_source(path),
                replacements=replacements,
                dispatch_key=(
                    "legacy-native-zero."
                    + path.replace("_", "-").replace(".", "-")
                ),
            )
        )
    return tuple(result)


_COMMON_SUM_PENDING_V4_PATHS = frozenset(
    {
        "common.hash_invocations",
        "common.integrity_checks",
        "common.protocol_checks",
        "io.output_bytes",
        "io.read_bytes",
        "io.staged_bytes",
        "process.launches",
    }
)
_CAPACITY_PEAK_PENDING_V4_PATHS = frozenset(
    {"io.mounted_bytes_peak", "memory.working_bytes_peak"}
)


def _unmapped_v4_required_paths_by_reason(
    boundaries: tuple[K7RootCapOperationBoundaryV3, ...],
) -> dict[str, list[str]]:
    registry = registry_v4.official_counter_registry_v4()
    mapped = {row.target_path for row in boundaries}
    unmapped = set(registry.required_paths) - mapped
    derived = {
        path
        for path in unmapped
        if registry.by_path[path].lane.value == "derived_only"
    }
    common = unmapped & _COMMON_SUM_PENDING_V4_PATHS
    capacity = unmapped & _CAPACITY_PEAK_PENDING_V4_PATHS
    native_zero = unmapped - derived - common - capacity
    groups = {
        "COMMON_SUM_PENDING_HOOK": sorted(common),
        "CAPACITY_PEAK_PENDING_HOOK": sorted(capacity),
        "DERIVED_ONLY_RECONCILIATION": sorted(derived),
        "NATIVE_ZERO_NOT_EXECUTED_OR_OUTSIDE_ROOT_CAP": sorted(native_zero),
    }
    flattened = [path for paths in groups.values() for path in paths]
    if len(flattened) != len(set(flattened)) or set(flattened) != unmapped:
        raise V075K7RootCapOperationBoundaryManifestV3Error(
            "unmapped required V4 path report is incomplete or overlapping"
        )
    return groups


@dataclass(frozen=True, slots=True)
class K7RootCapOperationBoundaryManifestV3:
    v2_manifest_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundaries: tuple[K7RootCapOperationBoundaryV3, ...]

    def __post_init__(self) -> None:
        for value in (
            self.v2_manifest_id,
            self.counter_registry_id,
            self.stage_profile_id,
            self.comparison_profile_id,
            self.actual_projection_profile_id,
        ):
            parse_content_id(value)
        if (
            not self.boundaries
            or tuple(sorted(self.boundaries, key=lambda row: row.boundary_key))
            != self.boundaries
            or len({row.boundary_key for row in self.boundaries})
            != len(self.boundaries)
        ):
            raise V075K7RootCapOperationBoundaryManifestV3Error(
                "V3 boundaries must be nonempty, unique, and sorted"
            )

    @property
    def by_key(self) -> dict[str, K7RootCapOperationBoundaryV3]:
        return {row.boundary_key: row for row in self.boundaries}

    @property
    def by_path(self) -> dict[str, tuple[K7RootCapOperationBoundaryV3, ...]]:
        return {
            path: tuple(row for row in self.boundaries if row.target_path == path)
            for path in sorted({row.target_path for row in self.boundaries})
        }

    def _payload(self) -> dict[str, Any]:
        classification_counts = {
            item.value: sum(
                row.classification is item for row in self.boundaries
            )
            for item in OperationBoundaryClassificationV3
        }
        return {
            "schema": (
                "acfqp.v075_k7_root_cap_operation_boundary_manifest.v3"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope_key": SCOPE_KEY,
            "registered_topology": REGISTERED_TOPOLOGY,
            "registered_context_key": REGISTERED_CONTEXT_KEY,
            "registered_arm": REGISTERED_ARM,
            "registered_route": REGISTERED_ROUTE,
            "registered_terminal_status": REGISTERED_TERMINAL_STATUS,
            "v2_manifest_id": self.v2_manifest_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": self.actual_projection_profile_id,
            "stage_plan": [stage.value for stage in ROOT_CAP_STAGE_PLAN],
            "forbidden_unused_stages": [
                stage.value for stage in FORBIDDEN_UNUSED_STAGES
            ],
            "legacy_native_zero_forbidden_paths": sorted(
                _LEGACY_REPLACEMENTS
            ),
            "root_active_v4_owner_matched_paths": sorted(
                _ROOT_ACTIVE_V4_OWNER_MATCHED_PATHS
            ),
            "open_v4_owner_matched_paths": sorted(
                _OPEN_V4_OWNER_MATCHED_PATHS
            ),
            "unmapped_v4_required_paths_by_reason": (
                _unmapped_v4_required_paths_by_reason(self.boundaries)
            ),
            "classification_counts": classification_counts,
            "boundaries": [row.to_document() for row in self.boundaries],
            "runtime_dispatch_selector": [
                "trusted_active_construction_stage_contextvar",
                "dispatch_key",
            ],
            "caller_supplied_stage_dispatch_allowed": False,
            "stage_dispatch_context_must_be_active": True,
            "emittable_stage_dispatch_pairs_are_unique": True,
            "native_zero_stage_dispatch_pairs_are_disjoint": True,
            "v5_leaf_documents_preserved_exactly": True,
            "all_v5_addition_paths_have_exact_boundary_sites": True,
            "all_24_root_owner_matched_v4_paths_accounted_for": True,
            "open_child_promotion_v4_analogues_catalogued": True,
            "typed_record_replay_has_seven_owner_local_helpers": True,
            "greedy_allocation_binds_extreme_and_extreme_bounds": True,
            "zero_addition_break_iteration_is_counted": True,
            "old_mismatched_paths_deleted": False,
            "old_mismatched_paths_native_zero_for_this_profile": True,
            "open_stages_supported_by_v6_registry": True,
            "open_stages_executed_by_this_fixture": False,
            "returned_summary_charging_allowed": False,
            "artifact_cardinality_backfill_allowed": False,
            "cache_hit_exact_or_log_computation_charged": False,
            "confidence_cache_access_wrapper_required": (
                "_outer_confidence_bounds_accounted_v2"
            ),
            "confidence_cache_info_before_after_required": True,
            "confidence_cache_body_entry_marker_required": True,
            "official_cache_lifecycle": (
                "ISOLATED_COLD_CACHE_EPOCH_PER_OCCURRENCE_OR_REPLAY"
            ),
            "process_global_warm_cache_reuse_allowed": False,
            "beta_binomial_cache_accounting": (
                "INTERNAL_TO_ONE_REGISTERED_EXACT_COMPARISON_EVENT_"
                "NO_SEPARATE_V6_CHARGE"
            ),
            "beta_binomial_cache_requires_same_cold_isolated_epoch": True,
            "runtime_emitters_installed": False,
            "live_operation_event_count": 0,
            "all_site_completeness_claimed": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "counter_completeness_gate_passed": False,
            "workload_economics_gate_passed": False,
        }

    @property
    def manifest_id(self) -> str:
        return content_id(
            V075_K7_ROOT_CAP_OPERATION_BOUNDARY_MANIFEST_V3_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}

    def validate_official(self) -> None:
        if self != _expected_manifest():
            raise V075K7RootCapOperationBoundaryManifestV3Error(
                "official K7 root-cap V3 operation boundary manifest changed"
            )


def _expected_manifest() -> K7RootCapOperationBoundaryManifestV3:
    v2 = official_k7_root_cap_operation_site_manifest_v2()
    v2_owner_matched_paths = {
        path
        for site in v2.sites
        if site.classification.value == "DIRECT_VALID_OWNER_MATCHED"
        for path in site.target_paths
    }
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    additions = set(registry.by_path) - set(
        registry_v5.official_counter_registry_v5().by_path
    )
    v5_additions = set(
        registry_v5.official_counter_registry_v5().by_path
    ) - set(registry_v4.official_counter_registry_v4().by_path)
    boundaries = tuple(
        sorted(
            (
                *_v6_addition_boundaries(),
                *_v5_addition_boundaries(),
                *_v4_owner_matched_boundaries(),
                *_legacy_correction_boundaries(),
            ),
            key=lambda row: row.boundary_key,
        )
    )
    by_path = {
        path: tuple(row for row in boundaries if row.target_path == path)
        for path in {row.target_path for row in boundaries}
    }
    emittable_pairs = tuple(
        (row.stage, row.dispatch_key)
        for row in boundaries
        if row.classification in _EMITTABLE_CLASSIFICATIONS
    )
    native_zero_pairs = {
        (row.stage, row.dispatch_key)
        for row in boundaries
        if row.classification not in _EMITTABLE_CLASSIFICATIONS
    }
    if (
        not additions <= set(by_path)
        or not v5_additions <= set(by_path)
        or not _V4_OWNER_MATCHED_BOUNDARY_PATHS <= set(by_path)
        or len(v2_owner_matched_paths) != 24
        or (
            v2_owner_matched_paths - set(_LEGACY_REPLACEMENTS)
            != _ROOT_ACTIVE_V4_OWNER_MATCHED_PATHS
        )
        or len(_OPEN_V4_OWNER_MATCHED_PATHS) != 7
        or not _V4_OWNER_MATCHED_BOUNDARY_PATHS <= set(
            registry_v4.official_counter_registry_v4().by_path
        )
        or set(_LEGACY_REPLACEMENTS) - set(by_path)
        or any(
            boundary.target_path not in registry.by_path
            or boundary.reducer is not registry.by_path[
                boundary.target_path
            ].reducer
            or boundary.target_path
            not in stage.by_stage[boundary.stage].allowed_nonzero_paths
            for boundary in boundaries
        )
        or any(
            registry.by_path[path].owner
            != row.registered_owner
            for path, rows in by_path.items()
            for row in rows
        )
        or any(
            row.registered_owner
            != row.operation_source_module.rsplit(".", 1)[-1]
            for row in boundaries
            if row.classification
            in {
                OperationBoundaryClassificationV3
                .V6_NATIVE_BOUNDARY_SCHEMA_ONLY,
                OperationBoundaryClassificationV3
                .V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY,
                OperationBoundaryClassificationV3
                .V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY,
                OperationBoundaryClassificationV3
                .V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY,
                OperationBoundaryClassificationV3
                .OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO,
            }
        )
        or any(
            replacement not in additions
            for replacements in _LEGACY_REPLACEMENTS.values()
            for replacement in replacements
        )
        or any(
            row.operation_source_module.rsplit(".", 1)[-1]
            == row.registered_owner
            for row in boundaries
            if row.classification
            is OperationBoundaryClassificationV3
            .LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN
        )
        or any(
            row.operation_source_module.rsplit(".", 1)[-1]
            != row.registered_owner
            for row in boundaries
            if row.classification
            is OperationBoundaryClassificationV3
            .LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN
        )
        or any(
            registry.by_path[replacement].owner
            != row.operation_source_module.rsplit(".", 1)[-1]
            for row in boundaries
            if row.classification
            in {
                OperationBoundaryClassificationV3
                .LEGACY_OWNER_MISMATCH_NATIVE_ZERO_FORBIDDEN,
                OperationBoundaryClassificationV3
                .LEGACY_SEMANTIC_SPLIT_NATIVE_ZERO_FORBIDDEN,
            }
            for replacement in row.replacement_paths
        )
        or len(set(emittable_pairs)) != len(emittable_pairs)
        or bool(set(emittable_pairs) & native_zero_pairs)
    ):
        raise V075K7RootCapOperationBoundaryManifestV3Error(
            "V3 boundary coverage, owner, stage, or replacement changed"
        )
    return K7RootCapOperationBoundaryManifestV3(
        v2.manifest_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        boundaries,
    )


@lru_cache(maxsize=1)
def official_k7_root_cap_operation_boundary_manifest_v3(
) -> K7RootCapOperationBoundaryManifestV3:
    result = _expected_manifest()
    result.validate_official()
    return result


__all__ = [
    "CacheSemanticsV3",
    "FORBIDDEN_UNUSED_STAGES",
    "K7RootCapOperationBoundaryManifestV3",
    "K7RootCapOperationBoundaryV3",
    "OperationBoundaryClassificationV3",
    "PROFILE_KEY",
    "ROOT_CAP_STAGE_PLAN",
    "SCHEMA_VERSION",
    "SCOPE_KEY",
    "V075K7RootCapOperationBoundaryManifestV3Error",
    "official_k7_root_cap_operation_boundary_manifest_v3",
]
