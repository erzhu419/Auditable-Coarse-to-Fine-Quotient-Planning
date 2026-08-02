"""Nonformal complete nine-source envelope with honest local subwindows.

The V2 adapter required all nine source journals to expose one identical
numeric sequence interval.  That is too strong for independent SUM/MAX source
journals: their local event counts differ even when they belong to one attempt
and one measurement window.  This successor binds every source-local closed
interval and cutoff into one content-addressed production envelope instead of
padding, renumbering, or silently dropping events.

This module carries no numeric actual and installs no semantic verifier.  It is
the immutable join consumed by the later nine-path replay authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_RESOURCE_BOUND_SOURCE_V3_DOMAIN,
    V075_K7_PRODUCTION_SHARED_RESOURCE_ENVELOPE_V3_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "3.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.21"
PROFILE_KEY = "construction_shared_resource_live_envelope_v3"

BOUND_SOURCE_V3_DOMAIN = CONSTRUCTION_SHARED_RESOURCE_BOUND_SOURCE_V3_DOMAIN
LIVE_ENVELOPE_V3_DOMAIN = V075_K7_PRODUCTION_SHARED_RESOURCE_ENVELOPE_V3_DOMAIN
REQUESTED_PHASE3E_DOMAIN_TAGS = (
    BOUND_SOURCE_V3_DOMAIN,
    LIVE_ENVELOPE_V3_DOMAIN,
)

_BOUND_SOURCE_ISSUER = object()
_ENVELOPE_ISSUER = object()


class ConstructionSharedResourceLiveEnvelopeV3Error(ValueError):
    """One source or the complete envelope crossed its frozen identity."""


def _fail(message: str) -> NoReturn:
    raise ConstructionSharedResourceLiveEnvelopeV3Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceLiveEnvelopeV3Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


@dataclass(frozen=True, slots=True)
class BoundSharedResourceSourceV3:
    """Content-address one V2 source and its honest local closed interval."""

    _issuer: InitVar[object]
    source: resolution_v2.SharedResourceLiveSourceV2 = field(
        repr=False, compare=False
    )
    required_component_keys: tuple[str, ...]
    required_component_schemas: tuple[str, ...]

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _BOUND_SOURCE_ISSUER
            or type(self.source) is not resolution_v2.SharedResourceLiveSourceV2
        ):
            _fail("bound shared-resource source is caller-minted")
        contract = next(
            (
                row
                for row in resolution_v2
                .official_shared_resource_resolution_catalogue_v2()
                if row.path == self.source.path
            ),
            None,
        )
        if contract is None:
            _fail("bound source path is absent from the fixed catalogue")
        expected_keys = tuple(row.component_key for row in contract.required_components)
        expected_schemas = tuple(
            row.source_schema_id for row in contract.required_components
        )
        actual = tuple(
            (row.component_key, row.source_schema_id)
            for row in self.source.components
        )
        if (
            self.required_component_keys != expected_keys
            or self.required_component_schemas != expected_schemas
            or actual != tuple(zip(expected_keys, expected_schemas))
            or self.source.exact_source_kind is not contract.exact_source_kind
            or self.source.provenance_claims != contract.required_provenance
        ):
            _fail("bound source differs from its exact path contract")

    def _payload(self) -> dict[str, Any]:
        source = self.source
        return {
            "schema": "acfqp.construction_shared_resource_bound_source.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_runtime_envelope_id": source.live_envelope_id,
            "occurrence_id": source.occurrence_id,
            "route_attempt_id": source.route_attempt_id,
            "decision_point_id": source.decision_point_id,
            "measurement_window_id": source.measurement_window_id,
            "source_operational_cutoff_id": source.operational_cutoff_id,
            "path": source.path,
            "exact_source_kind": source.exact_source_kind.value,
            "required_provenance": [row.value for row in source.provenance_claims],
            "source_local_start_sequence": source.covered_start_sequence,
            "source_local_cutoff_sequence": source.covered_cutoff_sequence,
            "required_component_keys": list(self.required_component_keys),
            "required_component_schemas": list(self.required_component_schemas),
            "components": [row.to_internal_document() for row in source.components],
            "source_local_interval_preserved": True,
            "cross_source_padding_or_renumbering": False,
            "semantic_source_verified": False,
            "counter_record_issued": False,
        }

    @property
    def bound_source_id(self) -> str:
        return content_id(BOUND_SOURCE_V3_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bound_shared_resource_source_id": self.bound_source_id}


def bind_shared_resource_source_v3(
    source: resolution_v2.SharedResourceLiveSourceV2,
) -> BoundSharedResourceSourceV3:
    if type(source) is not resolution_v2.SharedResourceLiveSourceV2:
        _fail("source binding requires one exact V2 live source")
    contract = next(
        row
        for row in resolution_v2.official_shared_resource_resolution_catalogue_v2()
        if row.path == source.path
    )
    return BoundSharedResourceSourceV3(
        _BOUND_SOURCE_ISSUER,
        source,
        tuple(row.component_key for row in contract.required_components),
        tuple(row.source_schema_id for row in contract.required_components),
    )


@dataclass(frozen=True, slots=True)
class K7ProductionSharedResourceEnvelopeV3:
    """All nine source closures for one runtime attempt and window."""

    _issuer: InitVar[object]
    production_runtime_envelope_id: str
    counter_registry_id: str
    stage_profile_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    production_runtime_replay_id: str
    terminal_closure_observation_id: str
    bound_sources: tuple[BoundSharedResourceSourceV3, ...] = field(repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ENVELOPE_ISSUER:
            _fail("production shared-resource envelope is caller-minted")
        for value, label in (
            (self.production_runtime_envelope_id, "production runtime envelope"),
            (self.counter_registry_id, "counter registry"),
            (self.stage_profile_id, "stage profile"),
            (self.occurrence_id, "occurrence"),
            (self.route_attempt_id, "route attempt"),
            (self.decision_point_id, "decision point"),
            (self.measurement_window_id, "measurement window"),
            (self.production_runtime_replay_id, "production runtime replay"),
            (self.terminal_closure_observation_id, "terminal closure observation"),
        ):
            _cid(value, label)
        registry = registry_v6.official_counter_registry_v6()
        stage = registry_v6.official_stage_profile_v6(registry)
        expected_paths = resolution_v2.SHARED_RESOURCE_PATHS
        if (
            self.counter_registry_id != registry.registry_id
            or self.stage_profile_id != stage.stage_profile_id
            or type(self.bound_sources) is not tuple
            or any(type(row) is not BoundSharedResourceSourceV3 for row in self.bound_sources)
            or tuple(row.source.path for row in self.bound_sources) != expected_paths
            or len({row.bound_source_id for row in self.bound_sources}) != len(expected_paths)
        ):
            _fail("production envelope lacks the exact ordered nine-source set")
        for row in self.bound_sources:
            source = row.source
            _nonnegative(source.covered_start_sequence, "source local start")
            _nonnegative(source.covered_cutoff_sequence, "source local cutoff")
            if (
                source.live_envelope_id != self.production_runtime_envelope_id
                or source.occurrence_id != self.occurrence_id
                or source.route_attempt_id != self.route_attempt_id
                or source.decision_point_id != self.decision_point_id
                or source.measurement_window_id != self.measurement_window_id
                or source.covered_cutoff_sequence < source.covered_start_sequence
            ):
                _fail("one source crossed the runtime attempt or its local closure")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_k7_production_shared_resource_envelope.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "production_runtime_envelope_id": self.production_runtime_envelope_id,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "occurrence_id": self.occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "measurement_window_id": self.measurement_window_id,
            "production_runtime_replay_id": self.production_runtime_replay_id,
            "terminal_closure_observation_id": self.terminal_closure_observation_id,
            "bound_source_ids": [row.bound_source_id for row in self.bound_sources],
            "source_paths": [row.source.path for row in self.bound_sources],
            "source_local_windows": [
                {
                    "path": row.source.path,
                    "source_operational_cutoff_id": row.source.operational_cutoff_id,
                    "source_local_start_sequence": row.source.covered_start_sequence,
                    "source_local_cutoff_sequence": row.source.covered_cutoff_sequence,
                }
                for row in self.bound_sources
            ],
            "one_runtime_and_measurement_window": True,
            "source_local_cutoffs_retained": True,
            "identical_local_event_counts_required": False,
            "semantic_replayers_issued": False,
            "counter_records_issued": False,
            "formal_vector_authorized": False,
        }

    @property
    def envelope_id(self) -> str:
        return content_id(LIVE_ENVELOPE_V3_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "production_shared_resource_envelope_id": self.envelope_id}


def freeze_k7_production_shared_resource_envelope_v3(
    *,
    production_runtime_envelope_id: str,
    occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    measurement_window_id: str,
    production_runtime_replay_id: str,
    terminal_closure_observation_id: str,
    sources: tuple[resolution_v2.SharedResourceLiveSourceV2, ...],
) -> K7ProductionSharedResourceEnvelopeV3:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    if type(sources) is not tuple:
        _fail("production envelope sources must be one exact tuple")
    return K7ProductionSharedResourceEnvelopeV3(
        _ENVELOPE_ISSUER,
        production_runtime_envelope_id,
        registry.registry_id,
        stage.stage_profile_id,
        occurrence_id,
        route_attempt_id,
        decision_point_id,
        measurement_window_id,
        production_runtime_replay_id,
        terminal_closure_observation_id,
        tuple(bind_shared_resource_source_v3(row) for row in sources),
    )


__all__ = (
    "BOUND_SOURCE_V3_DOMAIN",
    "BoundSharedResourceSourceV3",
    "ConstructionSharedResourceLiveEnvelopeV3Error",
    "K7ProductionSharedResourceEnvelopeV3",
    "LIVE_ENVELOPE_V3_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "bind_shared_resource_source_v3",
    "freeze_k7_production_shared_resource_envelope_v3",
)
