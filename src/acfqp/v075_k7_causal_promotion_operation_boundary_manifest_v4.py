"""Operation-boundary successor for the causal-promotion K7 occurrence.

The historical root-cap V3 manifest is an exact negative-control profile: it
forbids both open stages because that fixture stops at the child-row cap.  The
causal V3 occurrence now executes signed child acquisition and two validation
promotions, so those same owner-local operation sites are live rather than
native zero.

This additive manifest preserves every V3 boundary document except the 43
open-stage rows whose classification changes from
``OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO`` to their original V4/V5/V6 native
family.  It installs no runtime by itself and issues no accounting artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any

from acfqp.accounting_v1 import LaneEnum, ReducerEnum
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as root_v3


SCHEMA_VERSION = "4.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.76"
PROFILE_KEY = "v075_k7_causal_promotion_operation_boundary_manifest_v4"
SCOPE_KEY = "NONFRESH_K7_CAUSAL_PROMOTION_BUDGET_EXHAUSTED"
MANIFEST_DOMAIN = "acfqp:v075-k7-causal-promotion-operation-manifest:v4"
BOUNDARY_DOMAIN = "acfqp:v075-k7-causal-promotion-operation-boundary:v4"

REGISTERED_TOPOLOGY = "K7"
REGISTERED_CONTEXT_KEY = "heldout_graph_k7_confirmatory_v1"
REGISTERED_ARM = "NO_PRIOR"
REGISTERED_ROUTE = "ADAPTIVE_QUOTIENT"
REGISTERED_TERMINAL_CODE = "ATTEMPT_BUDGET_EXHAUSTED"

OPEN_STAGES = frozenset(
    {
        registry_v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION,
        registry_v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING,
    }
)
CAUSAL_PROMOTION_STAGE_KINDS = (
    registry_v6.ConstructionStageKindV6.PREOPEN_COMMON_PREFIX,
    registry_v6.ConstructionStageKindV6.INITIAL_ACQUISITION,
    registry_v6.ConstructionStageKindV6.INITIAL_MODEL_BUILD,
    registry_v6.ConstructionStageKindV6.FAILED_ABSTRACT_PREFIX,
    registry_v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION,
    registry_v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING,
    (
        registry_v6.ConstructionStageKindV6
        .CLOSED_RECONCILIATION_AND_TERMINALIZATION
    ),
)
FORBIDDEN_STAGES = (
    registry_v6.ConstructionStageKindV6.LOCAL_ATTEMPT,
    registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK,
    registry_v6.ConstructionStageKindV6.REBUILD,
)
EXPECTED_RECLASSIFIED_BOUNDARY_COUNT = 43
_BOUNDARY_ISSUER = object()


class V075K7CausalPromotionOperationBoundaryManifestV4Error(ValueError):
    """The causal-promotion boundary successor changed or is malformed."""


def _native_classification(
    boundary: root_v3.K7RootCapOperationBoundaryV3,
    registry: registry_v6.CounterRegistryV6,
) -> root_v3.OperationBoundaryClassificationV3:
    if boundary.boundary_key.startswith("v6."):
        return (
            root_v3.OperationBoundaryClassificationV3
            .V6_DIAGNOSTIC_BOUNDARY_SCHEMA_ONLY
            if registry.by_path[boundary.target_path].lane
            is LaneEnum.DIAGNOSTIC
            else (
                root_v3.OperationBoundaryClassificationV3
                .V6_NATIVE_BOUNDARY_SCHEMA_ONLY
            )
        )
    if boundary.boundary_key.startswith("v5."):
        return (
            root_v3.OperationBoundaryClassificationV3
            .V5_PRESERVED_NATIVE_BOUNDARY_SCHEMA_ONLY
        )
    if boundary.boundary_key.startswith("v4-owner."):
        return (
            root_v3.OperationBoundaryClassificationV3
            .V4_OWNER_MATCHED_NATIVE_BOUNDARY_SCHEMA_ONLY
        )
    raise V075K7CausalPromotionOperationBoundaryManifestV4Error(
        "open native-zero boundary has no preserved owner family"
    )


def _manifest_id(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        MANIFEST_DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class K7CausalPromotionOperationBoundaryV4:
    _issuer: object = field(repr=False, compare=False)
    predecessor_boundary_id: str
    boundary_key: str
    dispatch_key: str
    stage: registry_v6.ConstructionStageKindV6
    classification: root_v3.OperationBoundaryClassificationV3
    target_path: str
    registered_owner: str
    reducer: ReducerEnum
    operation_source_module: str
    operation_source_symbol: str
    operation_boundary: str
    cache_semantics: root_v3.CacheSemanticsV3
    count_rule: str
    failure_rule: str
    replacement_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        parse_content_id(self.predecessor_boundary_id)
        try:
            stage = registry_v6.ConstructionStageKindV6(self.stage)
            classification = root_v3.OperationBoundaryClassificationV3(
                self.classification
            )
            reducer = ReducerEnum(self.reducer)
            cache = root_v3.CacheSemanticsV3(self.cache_semantics)
        except (TypeError, ValueError) as error:
            raise V075K7CausalPromotionOperationBoundaryManifestV4Error(
                "causal-promotion boundary enum changed"
            ) from error
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "classification", classification)
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "cache_semantics", cache)
        if (
            self._issuer is not _BOUNDARY_ISSUER
            or type(self.boundary_key) is not str
            or not self.boundary_key
            or type(self.dispatch_key) is not str
            or not self.dispatch_key
            or type(self.target_path) is not str
            or not self.target_path
            or type(self.registered_owner) is not str
            or not self.registered_owner
            or type(self.operation_source_module) is not str
            or not self.operation_source_module
            or type(self.operation_source_symbol) is not str
            or not self.operation_source_symbol
            or type(self.operation_boundary) is not str
            or not self.operation_boundary
            or type(self.count_rule) is not str
            or not self.count_rule
            or type(self.failure_rule) is not str
            or not self.failure_rule
            or type(self.replacement_paths) is not tuple
        ):
            raise V075K7CausalPromotionOperationBoundaryManifestV4Error(
                "causal-promotion boundary is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_k7_causal_promotion_operation_boundary.v4"
            ),
            "schema_version": SCHEMA_VERSION,
            "predecessor_boundary_id": self.predecessor_boundary_id,
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
            "emittable_in_causal_promotion_fixture": (
                self.classification in root_v3._EMITTABLE_CLASSIFICATIONS  # noqa: SLF001
            ),
            "runtime_evidence_issued": False,
        }

    @property
    def boundary_id(self) -> str:
        return hashlib.sha256(
            BOUNDARY_DOMAIN.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(self._payload())
        ).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "boundary_id": self.boundary_id}


def _successor_boundary(
    predecessor: root_v3.K7RootCapOperationBoundaryV3,
    registry: registry_v6.CounterRegistryV6,
) -> K7CausalPromotionOperationBoundaryV4:
    classification = (
        _native_classification(predecessor, registry)
        if predecessor.stage in OPEN_STAGES
        and predecessor.classification
        is (
            root_v3.OperationBoundaryClassificationV3
            .OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO
        )
        else predecessor.classification
    )
    return K7CausalPromotionOperationBoundaryV4(
        _BOUNDARY_ISSUER,
        predecessor.boundary_id,
        predecessor.boundary_key,
        predecessor.dispatch_key,
        predecessor.stage,
        classification,
        predecessor.target_path,
        predecessor.registered_owner,
        predecessor.reducer,
        predecessor.operation_source_module,
        predecessor.operation_source_symbol,
        predecessor.operation_boundary,
        predecessor.cache_semantics,
        predecessor.count_rule,
        predecessor.failure_rule,
        predecessor.replacement_paths,
    )


@dataclass(frozen=True, slots=True)
class K7CausalPromotionOperationBoundaryManifestV4:
    predecessor_manifest_id: str
    counter_registry_id: str
    stage_profile_id: str
    comparison_profile_id: str
    actual_projection_profile_id: str
    boundaries: tuple[K7CausalPromotionOperationBoundaryV4, ...]

    def __post_init__(self) -> None:
        for value in (
            self.predecessor_manifest_id,
            self.counter_registry_id,
            self.stage_profile_id,
            self.comparison_profile_id,
            self.actual_projection_profile_id,
        ):
            parse_content_id(value)
        if (
            type(self.boundaries) is not tuple
            or tuple(sorted(self.boundaries, key=lambda row: row.boundary_key))
            != self.boundaries
            or len({row.boundary_key for row in self.boundaries})
            != len(self.boundaries)
        ):
            raise V075K7CausalPromotionOperationBoundaryManifestV4Error(
                "causal-promotion boundaries must be unique and sorted"
            )

    @property
    def by_key(self) -> dict[str, K7CausalPromotionOperationBoundaryV4]:
        return {row.boundary_key: row for row in self.boundaries}

    @property
    def by_path(
        self,
    ) -> dict[str, tuple[K7CausalPromotionOperationBoundaryV4, ...]]:
        return {
            path: tuple(
                row for row in self.boundaries if row.target_path == path
            )
            for path in sorted({row.target_path for row in self.boundaries})
        }

    def _payload(self) -> dict[str, Any]:
        predecessor = root_v3.official_k7_root_cap_operation_boundary_manifest_v3()
        reclassified = tuple(
            row
            for row in self.boundaries
            if row.stage in OPEN_STAGES
            and row.classification
            in root_v3._EMITTABLE_CLASSIFICATIONS  # noqa: SLF001
        )
        return {
            "schema": (
                "acfqp.v075_k7_causal_promotion_operation_boundary_"
                "manifest.v4"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope_key": SCOPE_KEY,
            "registered_topology": REGISTERED_TOPOLOGY,
            "registered_context_key": REGISTERED_CONTEXT_KEY,
            "registered_arm": REGISTERED_ARM,
            "registered_route": REGISTERED_ROUTE,
            "registered_terminal_code": REGISTERED_TERMINAL_CODE,
            "predecessor_manifest_id": self.predecessor_manifest_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "comparison_profile_id": self.comparison_profile_id,
            "actual_projection_profile_id": (
                self.actual_projection_profile_id
            ),
            "stage_kinds": [
                stage.value for stage in CAUSAL_PROMOTION_STAGE_KINDS
            ],
            "repeatable_stage_kinds": [
                stage.value for stage in sorted(OPEN_STAGES, key=lambda x: x.value)
            ],
            "forbidden_stage_kinds": [
                stage.value for stage in FORBIDDEN_STAGES
            ],
            "boundary_count": len(self.boundaries),
            "reclassified_open_boundary_count": len(reclassified),
            "reclassified_open_boundary_ids": [
                row.boundary_id for row in reclassified
            ],
            "boundaries": [row.to_document() for row in self.boundaries],
            "predecessor_boundary_count_preserved": (
                len(self.boundaries) == len(predecessor.boundaries)
            ),
            "closed_root_boundaries_preserved_exactly": True,
            "open_native_zero_reclassification_only": True,
            "local_fallback_rebuild_remain_native_zero": True,
            "runtime_emitters_installed": False,
            "live_operation_event_count": 0,
            "counter_records_issued": 0,
            "work_vector_issued": False,
            "official_execution_allowed": False,
            "counter_completeness_gate_passed": False,
        }

    @property
    def manifest_id(self) -> str:
        return _manifest_id(self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_id": self.manifest_id}

    def validate_official(self) -> None:
        if self != _expected_manifest():
            raise V075K7CausalPromotionOperationBoundaryManifestV4Error(
                "official causal-promotion manifest changed"
            )


def _expected_manifest() -> K7CausalPromotionOperationBoundaryManifestV4:
    predecessor = root_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    actual = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    boundaries = tuple(
        _successor_boundary(row, registry) for row in predecessor.boundaries
    )
    changed = tuple(
        (before, after)
        for before, after in zip(predecessor.boundaries, boundaries)
        if before.classification is not after.classification
    )
    emittable_pairs = tuple(
        (row.stage, row.dispatch_key)
        for row in boundaries
        if row.classification in root_v3._EMITTABLE_CLASSIFICATIONS  # noqa: SLF001
    )
    if (
        len(changed) != EXPECTED_RECLASSIFIED_BOUNDARY_COUNT
        or any(
            before.stage not in OPEN_STAGES
            or before.classification
            is not (
                root_v3.OperationBoundaryClassificationV3
                .OUTSIDE_ROOT_CAP_FIXTURE_NATIVE_ZERO
            )
            or after.classification
            not in root_v3._EMITTABLE_CLASSIFICATIONS  # noqa: SLF001
            or after.predecessor_boundary_id != before.boundary_id
            or after.boundary_key != before.boundary_key
            or after.dispatch_key != before.dispatch_key
            or after.target_path != before.target_path
            or after.registered_owner != before.registered_owner
            or after.reducer is not before.reducer
            or after.operation_source_module != before.operation_source_module
            or after.operation_source_symbol != before.operation_source_symbol
            or after.operation_boundary != before.operation_boundary
            or after.cache_semantics is not before.cache_semantics
            or after.count_rule != before.count_rule
            or after.failure_rule != before.failure_rule
            or after.replacement_paths != before.replacement_paths
            for before, after in changed
        )
        or len(set(emittable_pairs)) != len(emittable_pairs)
        or any(
            row.stage in FORBIDDEN_STAGES
            and row.classification
            in root_v3._EMITTABLE_CLASSIFICATIONS  # noqa: SLF001
            for row in boundaries
        )
    ):
        raise V075K7CausalPromotionOperationBoundaryManifestV4Error(
            "causal-promotion open-boundary reclassification changed"
        )
    return K7CausalPromotionOperationBoundaryManifestV4(
        predecessor.manifest_id,
        registry.registry_id,
        stage.stage_profile_id,
        comparison.comparison_profile_id,
        actual.actual_projection_profile_id,
        boundaries,
    )


def official_k7_causal_promotion_operation_boundary_manifest_v4(
) -> K7CausalPromotionOperationBoundaryManifestV4:
    result = _expected_manifest()
    result.validate_official()
    return result


__all__ = (
    "CAUSAL_PROMOTION_STAGE_KINDS",
    "EXPECTED_RECLASSIFIED_BOUNDARY_COUNT",
    "K7CausalPromotionOperationBoundaryV4",
    "K7CausalPromotionOperationBoundaryManifestV4",
    "OPEN_STAGES",
    "PROFILE_KEY",
    "SCHEMA_VERSION",
    "V075K7CausalPromotionOperationBoundaryManifestV4Error",
    "official_k7_causal_promotion_operation_boundary_manifest_v4",
)
