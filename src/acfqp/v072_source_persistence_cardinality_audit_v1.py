"""Static deployment audit for naive V0-068 object-snapshot persistence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "v072_source_persistence_cardinality_audit_v1"
DOMAIN = "acfqp:v072-source-persistence-cardinality-audit:v1"

# Frozen registered counters from the V0-068 source campaign and the broader
# V0-066 graph-family construction.  These are not newly measured claims.
SOURCE_PHYSICAL_UNIQUE_DRAWS = 5_242_880
SOURCE_COMPARISON_DRAWS = 5_451_776
GRAPH_FAMILY_DRAWS = 18_612_224

CONTENT_ID_HEX_CHARACTERS = 64
CANONICAL_JSON_MARGINAL_BYTES_PER_ID = 67

# Every physical ID occurs in (1) a physical row prefix, (2) the physical
# accounting set, and (3) at least one of direct/quotient accounting.
PROVEN_MINIMUM_ID_OCCURRENCES = 3

# Registered checkpoints can retain a prefix four times.  The campaign and
# family-evidence object paths can each retain those rows (8), the three
# accounting sets add 3, and five slots conservatively cover promoted-row
# and structural duplication.  This is an engineering upper estimate, not a
# semantic certificate; the proven lower bound alone rejects deployment.
CONSERVATIVE_UPPER_ID_OCCURRENCES = 16

MAX_DEPLOYABLE_CANONICAL_BUNDLE_BYTES = 256 * 1024 * 1024


def _content_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        DOMAIN.encode("utf-8")
        + b"\x00"
        + canonical_json_bytes(dict(payload))
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class SourcePersistenceCardinalityAuditV1:
    source_physical_unique_draws: int = SOURCE_PHYSICAL_UNIQUE_DRAWS
    source_comparison_draws: int = SOURCE_COMPARISON_DRAWS
    graph_family_draws: int = GRAPH_FAMILY_DRAWS
    marginal_bytes_per_id: int = CANONICAL_JSON_MARGINAL_BYTES_PER_ID
    proven_minimum_id_occurrences: int = PROVEN_MINIMUM_ID_OCCURRENCES
    conservative_upper_id_occurrences: int = (
        CONSERVATIVE_UPPER_ID_OCCURRENCES
    )
    deployment_cap_bytes: int = MAX_DEPLOYABLE_CANONICAL_BUNDLE_BYTES
    full_snapshot_deployable: bool = False
    recommended_persistence: str = (
        "CONTENT_ADDRESSED_DETERMINISTIC_RECONSTRUCTION_RECIPE"
    )

    def __post_init__(self) -> None:
        if (
            self.source_physical_unique_draws
            != SOURCE_PHYSICAL_UNIQUE_DRAWS
            or self.source_comparison_draws != SOURCE_COMPARISON_DRAWS
            or self.graph_family_draws != GRAPH_FAMILY_DRAWS
            or self.marginal_bytes_per_id
            != CANONICAL_JSON_MARGINAL_BYTES_PER_ID
            or self.proven_minimum_id_occurrences
            != PROVEN_MINIMUM_ID_OCCURRENCES
            or self.conservative_upper_id_occurrences
            != CONSERVATIVE_UPPER_ID_OCCURRENCES
            or self.deployment_cap_bytes
            != MAX_DEPLOYABLE_CANONICAL_BUNDLE_BYTES
            or self.full_snapshot_deployable is not False
            or self.recommended_persistence
            != "CONTENT_ADDRESSED_DETERMINISTIC_RECONSTRUCTION_RECIPE"
            or self.source_snapshot_lower_bound_bytes
            <= self.deployment_cap_bytes
        ):
            raise ValueError("source persistence cardinality audit changed")

    @property
    def source_snapshot_lower_bound_bytes(self) -> int:
        return (
            self.source_physical_unique_draws
            * self.proven_minimum_id_occurrences
            * self.marginal_bytes_per_id
        )

    @property
    def source_snapshot_upper_estimate_bytes(self) -> int:
        return (
            self.source_physical_unique_draws
            * self.conservative_upper_id_occurrences
            * self.marginal_bytes_per_id
        )

    @property
    def graph_family_snapshot_lower_bound_bytes(self) -> int:
        return (
            self.graph_family_draws
            * self.proven_minimum_id_occurrences
            * self.marginal_bytes_per_id
        )

    @property
    def graph_family_snapshot_upper_estimate_bytes(self) -> int:
        return (
            self.graph_family_draws
            * self.conservative_upper_id_occurrences
            * self.marginal_bytes_per_id
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_source_persistence_cardinality_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_physical_unique_draws": (
                self.source_physical_unique_draws
            ),
            "source_comparison_draws": self.source_comparison_draws,
            "graph_family_draws": self.graph_family_draws,
            "content_id_hex_characters": CONTENT_ID_HEX_CHARACTERS,
            "canonical_json_marginal_bytes_per_id": (
                self.marginal_bytes_per_id
            ),
            "proven_minimum_id_occurrences": (
                self.proven_minimum_id_occurrences
            ),
            "conservative_upper_id_occurrences": (
                self.conservative_upper_id_occurrences
            ),
            "source_snapshot_lower_bound_bytes": (
                self.source_snapshot_lower_bound_bytes
            ),
            "source_snapshot_upper_estimate_bytes": (
                self.source_snapshot_upper_estimate_bytes
            ),
            "graph_family_snapshot_lower_bound_bytes": (
                self.graph_family_snapshot_lower_bound_bytes
            ),
            "graph_family_snapshot_upper_estimate_bytes": (
                self.graph_family_snapshot_upper_estimate_bytes
            ),
            "deployment_cap_bytes": self.deployment_cap_bytes,
            "full_snapshot_deployable": False,
            "recommended_persistence": self.recommended_persistence,
            "raw_observation_ids_persisted": False,
            "new_observer_draws": 0,
            "official_execution_allowed": False,
        }

    @property
    def audit_id(self) -> str:
        return _content_id(self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


def freeze_source_persistence_cardinality_audit_v1(
) -> SourcePersistenceCardinalityAuditV1:
    return SourcePersistenceCardinalityAuditV1()


__all__ = [
    "CANONICAL_JSON_MARGINAL_BYTES_PER_ID",
    "CONSERVATIVE_UPPER_ID_OCCURRENCES",
    "CONTENT_ID_HEX_CHARACTERS",
    "GRAPH_FAMILY_DRAWS",
    "MAX_DEPLOYABLE_CANONICAL_BUNDLE_BYTES",
    "PROFILE_KEY",
    "PROVEN_MINIMUM_ID_OCCURRENCES",
    "SOURCE_COMPARISON_DRAWS",
    "SOURCE_PHYSICAL_UNIQUE_DRAWS",
    "SourcePersistenceCardinalityAuditV1",
    "freeze_source_persistence_cardinality_audit_v1",
]
