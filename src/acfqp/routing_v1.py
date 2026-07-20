"""Typed Phase-3E routing contracts for the 1.0.0 protocol.

The historical Phase-3B/3C/3D runners intentionally keep their 0.x artifact
semantics.  This module is the content-addressed boundary consumed by the new
Phase-3E runner: it freezes route caps, binds every marginal upper to one
decision point, selects local work only under strict componentwise dominance,
and keeps cap exhaustion outside the infeasibility-certificate class.

All identifiers emitted here use :mod:`acfqp.phase3e_ids`.  No private JSON or
hash implementation is permitted in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence, TypeVar

from acfqp.accounting_v1 import SHARED_AXES
from acfqp.phase3e_ids import (
    CARDINALITY_EVIDENCE_DOMAIN,
    CARDINALITY_SOURCE_DOMAIN,
    CAUSAL_EVIDENCE_DOMAIN,
    DECISION_POINT_DOMAIN,
    FRONTIER_SNAPSHOT_DOMAIN,
    ROUTE_CAP_PROFILE_DOMAIN,
    ROUTE_DECISION_CONTEXT_DOMAIN,
    ROUTE_DECISION_DOMAIN,
    ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN,
    TERMINAL_ARTIFACT_DOMAIN,
    TRANSACTION_DOMAIN,
    TRUSTED_BUDGET_REPLAY_DOMAIN,
    TYPED_VERIFICATION_ATTESTATION_DOMAIN,
    content_id,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "phase3e_accounted_dynamic_routing_v0"
NOT_APPLICABLE = "NOT_APPLICABLE"
TIGHT_PREEXECUTION_UPPER = "TIGHT_PREEXECUTION_UPPER"


class RoutingV1Error(ValueError):
    """A typed Phase-3E routing object violates the 1.0.0 contract."""


E = TypeVar("E", bound=Enum)


def _enum(value: Any, enum_type: type[E], field: str) -> E:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise RoutingV1Error(f"invalid {field}: {value!r}") from error


def _token(value: Any, field: str) -> str:
    if type(value) is not str or not value:
        raise RoutingV1Error(f"{field} must be a nonempty string")
    return value


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise RoutingV1Error(f"{field} must be a full Phase-3E content ID") from error


def _nonnegative(value: Any, field: str) -> int:
    if type(value) is not int or value < 0:
        raise RoutingV1Error(f"{field} must be a nonnegative exact integer")
    return value


def _positive(value: Any, field: str) -> int:
    result = _nonnegative(value, field)
    if result == 0:
        raise RoutingV1Error(f"{field} must be positive")
    return result


def _fields(document: Mapping[str, Any], expected: set[str], context: str) -> None:
    try:
        require_exact_fields(document, expected, context=context)
    except ValueError as error:
        raise RoutingV1Error(str(error)) from error


def _verify_id(
    document: Mapping[str, Any], id_field: str, domain: str, payload: Mapping[str, Any]
) -> None:
    supplied = _cid(document[id_field], id_field)
    if supplied != content_id(domain, payload):
        raise RoutingV1Error(f"{id_field} content ID mismatch")


@dataclass(frozen=True, slots=True)
class TypedNotApplicable:
    """An explicit typed null; omission and ordinary JSON ``null`` are invalid."""

    reason: str
    kind: str = NOT_APPLICABLE

    def __post_init__(self) -> None:
        if self.kind != NOT_APPLICABLE:
            raise RoutingV1Error("typed-null kind must be NOT_APPLICABLE")
        _token(self.reason, "typed-null reason")

    def to_dict(self) -> dict[str, str]:
        return {"kind": NOT_APPLICABLE, "reason": self.reason}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "TypedNotApplicable":
        _fields(document, {"kind", "reason"}, "typed null")
        return cls(reason=document["reason"], kind=document["kind"])


ContentRef = str | TypedNotApplicable
IndexRef = int | TypedNotApplicable


def _content_ref(value: Any, field: str, *, allow_not_applicable: bool) -> ContentRef:
    if isinstance(value, TypedNotApplicable):
        if not allow_not_applicable:
            raise RoutingV1Error(f"{field} cannot be NOT_APPLICABLE")
        return value
    return _cid(value, field)


def _parse_content_ref(
    value: Any, field: str, *, allow_not_applicable: bool
) -> ContentRef:
    if isinstance(value, Mapping):
        return _content_ref(
            TypedNotApplicable.from_dict(value),
            field,
            allow_not_applicable=allow_not_applicable,
        )
    return _content_ref(value, field, allow_not_applicable=allow_not_applicable)


def _index_ref(value: Any, field: str, *, allow_not_applicable: bool) -> IndexRef:
    if isinstance(value, TypedNotApplicable):
        if not allow_not_applicable:
            raise RoutingV1Error(f"{field} cannot be NOT_APPLICABLE")
        return value
    result = _positive(value, field)
    if result > 2:
        raise RoutingV1Error(f"{field} exceeds the V0 transaction budget of 2")
    return result


def _parse_index_ref(
    value: Any, field: str, *, allow_not_applicable: bool
) -> IndexRef:
    if isinstance(value, Mapping):
        return _index_ref(
            TypedNotApplicable.from_dict(value),
            field,
            allow_not_applicable=allow_not_applicable,
        )
    return _index_ref(value, field, allow_not_applicable=allow_not_applicable)


def _ref_dict(value: ContentRef | IndexRef) -> Any:
    return value.to_dict() if isinstance(value, TypedNotApplicable) else value


class RouteKind(str, Enum):
    LOCAL_ATTEMPT = "LOCAL_ATTEMPT"
    DIRECT_FALLBACK = "DIRECT_FALLBACK"


class CausalOutcome(str, Enum):
    FOUND = "FOUND"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"
    NO_SOUND_COVER = "NO_SOUND_COVER"
    LOCAL_CAP_IMPOSSIBLE = "LOCAL_CAP_IMPOSSIBLE"


class CardinalitySourceKind(str, Enum):
    """Registered kinds of immutable, pre-route cardinality sources.

    A source is not an integer assertion.  It contains the distinct frozen
    member identities from which the cardinality authority recomputes each
    count.  The kind records which pre-execution catalogue supplied those
    identities and prevents an opaque, untyped hash from being treated as a
    cardinality source.
    """

    ACTION_CATALOGUE = "ACTION_CATALOGUE"
    FRONTIER = "FRONTIER"
    PROOF_CIRCUIT_METADATA = "PROOF_CIRCUIT_METADATA"
    ROUTE_CAP_METADATA = "ROUTE_CAP_METADATA"
    IO_MANIFEST = "IO_MANIFEST"
    FALLBACK_SEARCH_BOUND = "FALLBACK_SEARCH_BOUND"


class RouteSelection(str, Enum):
    LOCAL = "LOCAL"
    FALLBACK = "FALLBACK"


class RouteComparison(str, Enum):
    LOCAL_STRICTLY_DOMINATES = "LOCAL_STRICTLY_DOMINATES"
    FALLBACK_DOMINATES = "FALLBACK_DOMINATES"
    EQUAL = "EQUAL"
    INCOMPARABLE = "INCOMPARABLE"
    LOCAL_FORBIDDEN = "LOCAL_FORBIDDEN"
    MISSING_LOCAL_UPPER = "MISSING_LOCAL_UPPER"
    INVALID_LOCAL_UPPER = "INVALID_LOCAL_UPPER"


OFFICIAL_LOCAL_CAPS: tuple[tuple[str, int], ...] = tuple(
    sorted(
        {
            "max_causal_candidate_evaluations": 32,
            "max_materialization_ground_steps": 16,
            "max_materialization_positive_outcomes": 64,
            "max_slice_cells": 64,
            "max_slice_members": 4096,
            "max_slice_actions": 65536,
            "max_slice_successor_rows": 262144,
            "max_cell_policy_assignments": 65536,
            "max_expanded_forms": 65536,
            "max_domain_assignments": 65536,
            "max_form_subset_evaluations": 65536,
            "max_subset_evaluations": 16,
            "max_policy_assignments": 1024,
            "max_root_frontier_points": 128,
            "max_dominance_comparisons": 65536,
            "max_affine_term_evaluations": 65536,
            "max_rational_bits": 512,
            "max_postaudit_ground_steps": 8,
            "max_postaudit_positive_outcomes": 32,
        }.items()
    )
)


@dataclass(frozen=True, slots=True)
class RouteCapProfileV1:
    """The finite V0 local-transaction hard-cap profile frozen by FQ4."""

    limits: tuple[tuple[str, int], ...] = OFFICIAL_LOCAL_CAPS
    max_local_transactions_per_logical_occurrence: int = 2
    profile_key: str = "phase3e_official_local_transaction_caps_v1"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise RoutingV1Error("route-cap schema version mismatch")
        if self.profile_key != "phase3e_official_local_transaction_caps_v1":
            raise RoutingV1Error("route-cap profile key mismatch")
        if self.max_local_transactions_per_logical_occurrence != 2:
            raise RoutingV1Error("V0 allows exactly two local transactions")
        if self.limits != OFFICIAL_LOCAL_CAPS:
            raise RoutingV1Error("route-cap profile differs from the frozen V0 caps")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_cap_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": self.profile_key,
            "max_local_transactions_per_logical_occurrence": 2,
            "limits": [{"name": name, "value": value} for name, value in self.limits],
        }

    @property
    def route_cap_profile_id(self) -> str:
        return content_id(ROUTE_CAP_PROFILE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "route_cap_profile_id": self.route_cap_profile_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RouteCapProfileV1":
        expected = {
            "schema",
            "schema_version",
            "profile_key",
            "max_local_transactions_per_logical_occurrence",
            "limits",
            "route_cap_profile_id",
        }
        _fields(document, expected, "route cap profile")
        if document["schema"] != "acfqp.route_cap_profile.v1":
            raise RoutingV1Error("route-cap schema mismatch")
        rows = document["limits"]
        if type(rows) is not list:
            raise RoutingV1Error("route-cap limits must be a list")
        limits: list[tuple[str, int]] = []
        for row in rows:
            _fields(row, {"name", "value"}, "route-cap limit")
            limits.append((row["name"], row["value"]))
        result = cls(
            tuple(limits),
            document["max_local_transactions_per_logical_occurrence"],
            document["profile_key"],
            document["schema_version"],
        )
        _verify_id(
            document,
            "route_cap_profile_id",
            ROUTE_CAP_PROFILE_DOMAIN,
            result._payload(),
        )
        return result


@dataclass(frozen=True, slots=True)
class RouteDecisionContextV1:
    preregistration_id: str
    protocol_id: str
    comparison_profile_id: str
    counter_registry_id: str
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    build_epoch_id: str
    logical_occurrence_id: str
    route_attempt_id: str

    def __post_init__(self) -> None:
        for field in (
            "preregistration_id",
            "protocol_id",
            "comparison_profile_id",
            "counter_registry_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "build_epoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
        ):
            _cid(getattr(self, field), field)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_decision_context.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "protocol_id": self.protocol_id,
            "comparison_profile_id": self.comparison_profile_id,
            "counter_registry_id": self.counter_registry_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "BuildEpoch_id": self.build_epoch_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
        }

    @property
    def route_decision_context_id(self) -> str:
        return content_id(ROUTE_DECISION_CONTEXT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "route_decision_context_id": self.route_decision_context_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RouteDecisionContextV1":
        expected = {
            "schema",
            "schema_version",
            "preregistration_id",
            "protocol_id",
            "comparison_profile_id",
            "counter_registry_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "BuildEpoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "route_decision_context_id",
        }
        _fields(document, expected, "route decision context")
        if (
            document["schema"] != "acfqp.route_decision_context.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise RoutingV1Error("route decision context schema mismatch")
        result = cls(
            document["preregistration_id"],
            document["protocol_id"],
            document["comparison_profile_id"],
            document["counter_registry_id"],
            document["structural_id"],
            document["query_id"],
            document["selected_plan_id"],
            document["threshold_profile_id"],
            document["BuildEpoch_id"],
            document["logical_occurrence_id"],
            document["route_attempt_id"],
        )
        _verify_id(
            document,
            "route_decision_context_id",
            ROUTE_DECISION_CONTEXT_DOMAIN,
            result._payload(),
        )
        return result


@dataclass(frozen=True, slots=True)
class FrontierSnapshotV1:
    route_decision_context_id: str
    frontier_stage: int
    failed_obligation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.route_decision_context_id, "route_decision_context_id")
        _nonnegative(self.frontier_stage, "frontier_stage")
        if not self.failed_obligation_ids:
            raise RoutingV1Error("frontier snapshot needs a failed proof obligation")
        if (
            tuple(sorted(self.failed_obligation_ids)) != self.failed_obligation_ids
            or len(set(self.failed_obligation_ids)) != len(self.failed_obligation_ids)
        ):
            raise RoutingV1Error("frontier obligation IDs must be unique and sorted")
        for obligation_id in self.failed_obligation_ids:
            _cid(obligation_id, "failed_obligation_id")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frontier_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "frontier_stage": self.frontier_stage,
            "failed_obligation_ids": list(self.failed_obligation_ids),
        }

    @property
    def frontier_snapshot_id(self) -> str:
        return content_id(FRONTIER_SNAPSHOT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "frontier_snapshot_id": self.frontier_snapshot_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "FrontierSnapshotV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "frontier_stage",
            "failed_obligation_ids",
            "frontier_snapshot_id",
        }
        _fields(document, expected, "frontier snapshot")
        if (
            document["schema"] != "acfqp.frontier_snapshot.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["failed_obligation_ids"]) is not list
        ):
            raise RoutingV1Error("frontier snapshot schema mismatch")
        result = cls(
            document["RouteDecisionContext_id"],
            document["frontier_stage"],
            tuple(document["failed_obligation_ids"]),
        )
        _verify_id(
            document,
            "frontier_snapshot_id",
            FRONTIER_SNAPSHOT_DOMAIN,
            result._payload(),
        )
        return result


_FORBIDDEN_REASON = {
    CausalOutcome.CAP_EXHAUSTED: "CAP_EXHAUSTED",
    CausalOutcome.NO_SOUND_COVER: "NO_SOUND_COVER",
    CausalOutcome.LOCAL_CAP_IMPOSSIBLE: "LOCAL_CAP_IMPOSSIBLE",
}


@dataclass(frozen=True, slots=True)
class CausalEvidenceV1:
    frontier_snapshot_id: str
    outcome: CausalOutcome
    local_allowed: bool
    local_forbidden_reason: str | None
    evaluated_candidate_count: int
    cap_id: str
    proof_obligation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.frontier_snapshot_id, "frontier_snapshot_id")
        object.__setattr__(self, "outcome", _enum(self.outcome, CausalOutcome, "causal outcome"))
        _nonnegative(self.evaluated_candidate_count, "evaluated_candidate_count")
        if self.evaluated_candidate_count > 32:
            raise RoutingV1Error("causal candidate count exceeds the frozen cap of 32")
        _cid(self.cap_id, "cap_id")
        if (
            not self.proof_obligation_ids
            or tuple(sorted(self.proof_obligation_ids)) != self.proof_obligation_ids
            or len(set(self.proof_obligation_ids)) != len(self.proof_obligation_ids)
        ):
            raise RoutingV1Error("causal proof-obligation IDs must be nonempty, unique, and sorted")
        for obligation_id in self.proof_obligation_ids:
            _cid(obligation_id, "proof_obligation_id")
        if self.outcome is CausalOutcome.FOUND:
            if self.local_allowed is not True or self.local_forbidden_reason is not None:
                raise RoutingV1Error("FOUND is the only local-allowed causal outcome")
        else:
            expected = _FORBIDDEN_REASON[self.outcome]
            if self.local_allowed is not False or self.local_forbidden_reason != expected:
                raise RoutingV1Error(
                    "negative causal outcome must permanently forbid local with its exact reason"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.causal_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "frontier_snapshot_id": self.frontier_snapshot_id,
            "outcome": self.outcome.value,
            "local_allowed": self.local_allowed,
            "local_forbidden_reason": self.local_forbidden_reason,
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "cap_id": self.cap_id,
            "proof_obligation_ids": list(self.proof_obligation_ids),
        }

    @property
    def causal_evidence_id(self) -> str:
        return content_id(CAUSAL_EVIDENCE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "causal_evidence_id": self.causal_evidence_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "CausalEvidenceV1":
        expected = {
            "schema",
            "schema_version",
            "frontier_snapshot_id",
            "outcome",
            "local_allowed",
            "local_forbidden_reason",
            "evaluated_candidate_count",
            "cap_id",
            "proof_obligation_ids",
            "causal_evidence_id",
        }
        _fields(document, expected, "causal evidence")
        if (
            document["schema"] != "acfqp.causal_evidence.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["proof_obligation_ids"]) is not list
        ):
            raise RoutingV1Error("causal evidence schema mismatch")
        result = cls(
            document["frontier_snapshot_id"],
            document["outcome"],
            document["local_allowed"],
            document["local_forbidden_reason"],
            document["evaluated_candidate_count"],
            document["cap_id"],
            tuple(document["proof_obligation_ids"]),
        )
        _verify_id(
            document,
            "causal_evidence_id",
            CAUSAL_EVIDENCE_DOMAIN,
            result._payload(),
        )
        return result


@dataclass(frozen=True, slots=True)
class FrozenCardinalityCollectionV1:
    """One named collection whose size is recomputed from distinct members."""

    count_name: str
    member_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _token(self.count_name, "cardinality count_name")
        if (
            tuple(sorted(self.member_ids)) != self.member_ids
            or len(set(self.member_ids)) != len(self.member_ids)
        ):
            raise RoutingV1Error(
                "frozen cardinality members must be unique and sorted"
            )
        for member_id in self.member_ids:
            _cid(member_id, "frozen cardinality member_id")

    @property
    def cardinality(self) -> int:
        return len(self.member_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "count_name": self.count_name,
            "member_ids": list(self.member_ids),
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "FrozenCardinalityCollectionV1":
        _fields(document, {"count_name", "member_ids"}, "cardinality collection")
        if type(document["member_ids"]) is not list:
            raise RoutingV1Error("cardinality collection members must be a list")
        return cls(document["count_name"], tuple(document["member_ids"]))


@dataclass(frozen=True, slots=True)
class FrozenCardinalitySourceV1:
    """Typed immutable input consumed by the cardinality authority.

    ``source_artifact_id`` authenticates the complete enumerated source, but
    its hash is never interpreted as a count.  Counts are recomputed as the
    number of distinct member identities in each collection.  Empty
    collections are explicit native zeros.
    """

    route_decision_context_id: str
    route_kind: RouteKind
    route_cap_profile_id: str
    frontier_snapshot_id: ContentRef
    source_kind: CardinalitySourceKind
    source_name: str
    parent_artifact_id: str
    parent_artifact_schema_id: str
    parent_artifact_role: str
    extraction_profile_id: str
    collections: tuple[FrozenCardinalityCollectionV1, ...]
    frozen_at_protocol_step: int
    captured_before_route_decision: bool = True
    depends_on_actual_route_work: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _cid(self.route_decision_context_id, "route_decision_context_id")
        object.__setattr__(
            self, "route_kind", _enum(self.route_kind, RouteKind, "route_kind")
        )
        _cid(self.route_cap_profile_id, "route_cap_profile_id")
        local = self.route_kind is RouteKind.LOCAL_ATTEMPT
        object.__setattr__(
            self,
            "frontier_snapshot_id",
            _content_ref(
                self.frontier_snapshot_id,
                "frontier_snapshot_id",
                allow_not_applicable=not local,
            ),
        )
        object.__setattr__(
            self,
            "source_kind",
            _enum(self.source_kind, CardinalitySourceKind, "source_kind"),
        )
        _token(self.source_name, "source_name")
        _cid(self.parent_artifact_id, "parent_artifact_id")
        _token(self.parent_artifact_schema_id, "parent_artifact_schema_id")
        _token(self.parent_artifact_role, "parent_artifact_role")
        _cid(self.extraction_profile_id, "extraction_profile_id")
        if (
            not self.collections
            or tuple(
                sorted(self.collections, key=lambda row: row.count_name)
            )
            != self.collections
            or len({row.count_name for row in self.collections})
            != len(self.collections)
        ):
            raise RoutingV1Error(
                "frozen cardinality collections must be nonempty, unique, and sorted"
            )
        if (
            type(self.frozen_at_protocol_step) is not int
            or self.frozen_at_protocol_step < 0
        ):
            raise RoutingV1Error(
                "frozen_at_protocol_step must be a nonnegative exact integer"
            )
        if self.captured_before_route_decision is not True:
            raise RoutingV1Error(
                "cardinality source must be captured before route decision"
            )
        if self.depends_on_actual_route_work is not False:
            raise RoutingV1Error(
                "cardinality source cannot depend on actual route work"
            )
        if self.schema_version != SCHEMA_VERSION:
            raise RoutingV1Error("frozen cardinality source version mismatch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_cardinality_source.v1",
            "schema_version": self.schema_version,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "route_kind": self.route_kind.value,
            "route_cap_profile_id": self.route_cap_profile_id,
            "frontier_snapshot_id": _ref_dict(self.frontier_snapshot_id),
            "source_kind": self.source_kind.value,
            "source_name": self.source_name,
            "parent_artifact_id": self.parent_artifact_id,
            "parent_artifact_schema_id": self.parent_artifact_schema_id,
            "parent_artifact_role": self.parent_artifact_role,
            "extraction_profile_id": self.extraction_profile_id,
            "collections": [row.to_dict() for row in self.collections],
            "frozen_at_protocol_step": self.frozen_at_protocol_step,
            "captured_before_route_decision": True,
            "depends_on_actual_route_work": False,
        }

    @property
    def source_artifact_id(self) -> str:
        return content_id(CARDINALITY_SOURCE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "source_artifact_id": self.source_artifact_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "FrozenCardinalitySourceV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "route_kind",
            "route_cap_profile_id",
            "frontier_snapshot_id",
            "source_kind",
            "source_name",
            "parent_artifact_id",
            "parent_artifact_schema_id",
            "parent_artifact_role",
            "extraction_profile_id",
            "collections",
            "frozen_at_protocol_step",
            "captured_before_route_decision",
            "depends_on_actual_route_work",
            "source_artifact_id",
        }
        _fields(document, expected, "frozen cardinality source")
        if (
            document["schema"] != "acfqp.frozen_cardinality_source.v1"
            or type(document["collections"]) is not list
        ):
            raise RoutingV1Error("frozen cardinality source schema mismatch")
        route_kind = _enum(document["route_kind"], RouteKind, "route_kind")
        result = cls(
            document["RouteDecisionContext_id"],
            route_kind,
            document["route_cap_profile_id"],
            _parse_content_ref(
                document["frontier_snapshot_id"],
                "frontier_snapshot_id",
                allow_not_applicable=route_kind is RouteKind.DIRECT_FALLBACK,
            ),
            document["source_kind"],
            document["source_name"],
            document["parent_artifact_id"],
            document["parent_artifact_schema_id"],
            document["parent_artifact_role"],
            document["extraction_profile_id"],
            tuple(
                FrozenCardinalityCollectionV1.from_dict(row)
                for row in document["collections"]
            ),
            document["frozen_at_protocol_step"],
            document["captured_before_route_decision"],
            document["depends_on_actual_route_work"],
            document["schema_version"],
        )
        _verify_id(
            document,
            "source_artifact_id",
            CARDINALITY_SOURCE_DOMAIN,
            result._payload(),
        )
        return result


@dataclass(frozen=True, slots=True)
class CardinalityEvidenceV1:
    route_decision_context_id: str
    route_kind: RouteKind
    route_cap_profile_id: str
    frontier_snapshot_id: ContentRef
    counts: tuple[tuple[str, int], ...]
    source_artifact_ids: tuple[str, ...]
    measured_before_execution: bool = True
    depends_on_actual_route_work: bool = False

    def __post_init__(self) -> None:
        _cid(self.route_decision_context_id, "route_decision_context_id")
        object.__setattr__(self, "route_kind", _enum(self.route_kind, RouteKind, "route_kind"))
        _cid(self.route_cap_profile_id, "route_cap_profile_id")
        local = self.route_kind is RouteKind.LOCAL_ATTEMPT
        object.__setattr__(
            self,
            "frontier_snapshot_id",
            _content_ref(
                self.frontier_snapshot_id,
                "frontier_snapshot_id",
                allow_not_applicable=not local,
            ),
        )
        if not self.counts or tuple(sorted(self.counts)) != self.counts:
            raise RoutingV1Error("cardinality counts must be nonempty and name-sorted")
        if len(dict(self.counts)) != len(self.counts):
            raise RoutingV1Error("cardinality evidence repeats a count")
        for name, value in self.counts:
            _token(name, "cardinality name")
            _nonnegative(value, name)
        if (
            not self.source_artifact_ids
            or tuple(sorted(self.source_artifact_ids)) != self.source_artifact_ids
            or len(set(self.source_artifact_ids)) != len(self.source_artifact_ids)
        ):
            raise RoutingV1Error("cardinality source IDs must be nonempty, unique, and sorted")
        for source_id in self.source_artifact_ids:
            _cid(source_id, "source_artifact_id")
        if self.measured_before_execution is not True:
            raise RoutingV1Error("cardinalities must be frozen before route execution")
        if self.depends_on_actual_route_work is not False:
            raise RoutingV1Error("cardinalities cannot depend on actual route work")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cardinality_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "route_kind": self.route_kind.value,
            "route_cap_profile_id": self.route_cap_profile_id,
            "frontier_snapshot_id": _ref_dict(self.frontier_snapshot_id),
            "counts": [{"name": name, "value": value} for name, value in self.counts],
            "source_artifact_ids": list(self.source_artifact_ids),
            "measured_before_execution": True,
            "depends_on_actual_route_work": False,
        }

    @property
    def cardinality_evidence_id(self) -> str:
        return content_id(CARDINALITY_EVIDENCE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cardinality_evidence_id": self.cardinality_evidence_id,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "CardinalityEvidenceV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "route_kind",
            "route_cap_profile_id",
            "frontier_snapshot_id",
            "counts",
            "source_artifact_ids",
            "measured_before_execution",
            "depends_on_actual_route_work",
            "cardinality_evidence_id",
        }
        _fields(document, expected, "cardinality evidence")
        if (
            document["schema"] != "acfqp.cardinality_evidence.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["counts"]) is not list
            or type(document["source_artifact_ids"]) is not list
        ):
            raise RoutingV1Error("cardinality evidence schema mismatch")
        route_kind = _enum(document["route_kind"], RouteKind, "route_kind")
        counts: list[tuple[str, int]] = []
        for row in document["counts"]:
            _fields(row, {"name", "value"}, "cardinality count")
            counts.append((row["name"], row["value"]))
        result = cls(
            document["RouteDecisionContext_id"],
            route_kind,
            document["route_cap_profile_id"],
            _parse_content_ref(
                document["frontier_snapshot_id"],
                "frontier_snapshot_id",
                allow_not_applicable=route_kind is RouteKind.DIRECT_FALLBACK,
            ),
            tuple(counts),
            tuple(document["source_artifact_ids"]),
            document["measured_before_execution"],
            document["depends_on_actual_route_work"],
        )
        _verify_id(
            document,
            "cardinality_evidence_id",
            CARDINALITY_EVIDENCE_DOMAIN,
            result._payload(),
        )
        return result


@dataclass(frozen=True, slots=True)
class DecisionPointV1:
    route_decision_context_id: str
    transaction_index: IndexRef
    frontier_snapshot_id: ContentRef
    causal_evidence_id: ContentRef
    common_prefix_work_id: str

    def __post_init__(self) -> None:
        _cid(self.route_decision_context_id, "route_decision_context_id")
        object.__setattr__(
            self,
            "transaction_index",
            _index_ref(self.transaction_index, "transaction_index", allow_not_applicable=True),
        )
        object.__setattr__(
            self,
            "frontier_snapshot_id",
            _content_ref(self.frontier_snapshot_id, "frontier_snapshot_id", allow_not_applicable=True),
        )
        object.__setattr__(
            self,
            "causal_evidence_id",
            _content_ref(self.causal_evidence_id, "causal_evidence_id", allow_not_applicable=True),
        )
        _cid(self.common_prefix_work_id, "common_prefix_work_id")
        frontier_na = isinstance(self.frontier_snapshot_id, TypedNotApplicable)
        causal_na = isinstance(self.causal_evidence_id, TypedNotApplicable)
        if frontier_na != causal_na:
            raise RoutingV1Error("frontier and causal evidence applicability must agree")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.decision_point.v1",
            "schema_version": SCHEMA_VERSION,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "transaction_index": _ref_dict(self.transaction_index),
            "frontier_snapshot_id": _ref_dict(self.frontier_snapshot_id),
            "causal_evidence_id": _ref_dict(self.causal_evidence_id),
            "common_prefix_work_id": self.common_prefix_work_id,
        }

    @property
    def decision_point_id(self) -> str:
        return content_id(DECISION_POINT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "decision_point_id": self.decision_point_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "DecisionPointV1":
        expected = {
            "schema",
            "schema_version",
            "RouteDecisionContext_id",
            "transaction_index",
            "frontier_snapshot_id",
            "causal_evidence_id",
            "common_prefix_work_id",
            "decision_point_id",
        }
        _fields(document, expected, "decision point")
        if (
            document["schema"] != "acfqp.decision_point.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise RoutingV1Error("decision-point schema mismatch")
        result = cls(
            document["RouteDecisionContext_id"],
            _parse_index_ref(
                document["transaction_index"],
                "transaction_index",
                allow_not_applicable=True,
            ),
            _parse_content_ref(
                document["frontier_snapshot_id"],
                "frontier_snapshot_id",
                allow_not_applicable=True,
            ),
            _parse_content_ref(
                document["causal_evidence_id"],
                "causal_evidence_id",
                allow_not_applicable=True,
            ),
            document["common_prefix_work_id"],
        )
        _verify_id(document, "decision_point_id", DECISION_POINT_DOMAIN, result._payload())
        return result


@dataclass(frozen=True, slots=True)
class TransactionV1:
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_index: int
    frontier_snapshot_id: str
    route_cap_profile_id: str

    def __post_init__(self) -> None:
        for field in (
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "frontier_snapshot_id",
            "route_cap_profile_id",
        ):
            _cid(getattr(self, field), field)
        _index_ref(self.transaction_index, "transaction_index", allow_not_applicable=False)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.transaction.v1",
            "schema_version": SCHEMA_VERSION,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transaction_index": self.transaction_index,
            "frontier_snapshot_id": self.frontier_snapshot_id,
            "route_cap_profile_id": self.route_cap_profile_id,
        }

    @property
    def transaction_id(self) -> str:
        return content_id(TRANSACTION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "transaction_id": self.transaction_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "TransactionV1":
        expected = {
            "schema",
            "schema_version",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "transaction_index",
            "frontier_snapshot_id",
            "route_cap_profile_id",
            "transaction_id",
        }
        _fields(document, expected, "transaction")
        if (
            document["schema"] != "acfqp.transaction.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise RoutingV1Error("transaction schema mismatch")
        result = cls(
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            document["decision_point_id"],
            document["transaction_index"],
            document["frontier_snapshot_id"],
            document["route_cap_profile_id"],
        )
        _verify_id(document, "transaction_id", TRANSACTION_DOMAIN, result._payload())
        return result


def _upper_values(values: Sequence[tuple[str, int]]) -> tuple[tuple[str, int], ...]:
    result = tuple(values)
    if tuple(axis for axis, _ in result) != SHARED_AXES:
        raise RoutingV1Error(
            "route upper must contain the exact eight shared axes in canonical order"
        )
    for axis, value in result:
        _nonnegative(value, axis)
    return result


@dataclass(frozen=True, slots=True)
class RouteUpperBoundEnvelopeV1:
    preregistration_id: str
    protocol_id: str
    comparison_profile_id: str
    counter_registry_id: str
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    build_epoch_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    transaction_id: ContentRef
    transaction_index: IndexRef
    frontier_snapshot_id: ContentRef
    causal_evidence_id: ContentRef
    route_cap_profile_id: str
    cardinality_evidence_id: str
    formula_id: str
    route_kind: RouteKind
    upper_kind: str
    upper_bounds: tuple[tuple[str, int], ...]
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "preregistration_id",
            "protocol_id",
            "comparison_profile_id",
            "counter_registry_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "build_epoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "route_cap_profile_id",
            "cardinality_evidence_id",
            "formula_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(self, "route_kind", _enum(self.route_kind, RouteKind, "route_kind"))
        local = self.route_kind is RouteKind.LOCAL_ATTEMPT
        object.__setattr__(
            self,
            "transaction_id",
            _content_ref(self.transaction_id, "transaction_id", allow_not_applicable=not local),
        )
        object.__setattr__(
            self,
            "transaction_index",
            _index_ref(self.transaction_index, "transaction_index", allow_not_applicable=not local),
        )
        object.__setattr__(
            self,
            "frontier_snapshot_id",
            _content_ref(
                self.frontier_snapshot_id,
                "frontier_snapshot_id",
                allow_not_applicable=not local,
            ),
        )
        object.__setattr__(
            self,
            "causal_evidence_id",
            _content_ref(
                self.causal_evidence_id,
                "causal_evidence_id",
                allow_not_applicable=not local,
            ),
        )
        transaction_na = isinstance(self.transaction_id, TypedNotApplicable)
        index_na = isinstance(self.transaction_index, TypedNotApplicable)
        if transaction_na != index_na:
            raise RoutingV1Error("transaction ID and index applicability must agree")
        if self.upper_kind != TIGHT_PREEXECUTION_UPPER:
            raise RoutingV1Error("only a tight pre-execution upper can enter route selection")
        if self.schema_version != SCHEMA_VERSION:
            raise RoutingV1Error("route-upper schema version mismatch")
        object.__setattr__(self, "upper_bounds", _upper_values(self.upper_bounds))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.route_upper_bound_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "protocol_id": self.protocol_id,
            "comparison_profile_id": self.comparison_profile_id,
            "counter_registry_id": self.counter_registry_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "BuildEpoch_id": self.build_epoch_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": self.decision_point_id,
            "transaction_id": _ref_dict(self.transaction_id),
            "transaction_index": _ref_dict(self.transaction_index),
            "frontier_snapshot_id": _ref_dict(self.frontier_snapshot_id),
            "causal_evidence_id": _ref_dict(self.causal_evidence_id),
            "route_cap_profile_id": self.route_cap_profile_id,
            "cardinality_evidence_id": self.cardinality_evidence_id,
            "formula_id": self.formula_id,
            "route_kind": self.route_kind.value,
            "upper_kind": self.upper_kind,
            "upper_bounds": [
                {"axis": axis, "value": value} for axis, value in self.upper_bounds
            ],
        }

    @property
    def route_upper_bound_envelope_id(self) -> str:
        return content_id(ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "route_upper_bound_envelope_id": self.route_upper_bound_envelope_id,
        }

    def validate_bindings(
        self,
        context: RouteDecisionContextV1,
        decision_point: DecisionPointV1,
        cardinality: CardinalityEvidenceV1,
        *,
        transaction: TransactionV1 | None = None,
        causal: CausalEvidenceV1 | None = None,
    ) -> None:
        context_fields = (
            "preregistration_id",
            "protocol_id",
            "comparison_profile_id",
            "counter_registry_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "build_epoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
        )
        for field in context_fields:
            if getattr(self, field) != getattr(context, field):
                raise RoutingV1Error(f"stale route upper: {field} mismatch")
        if decision_point.route_decision_context_id != context.route_decision_context_id:
            raise RoutingV1Error("decision point uses another route context")
        if self.decision_point_id != decision_point.decision_point_id:
            raise RoutingV1Error("route upper decision-point mismatch")
        if cardinality.route_decision_context_id != context.route_decision_context_id:
            raise RoutingV1Error("cardinality evidence uses another route context")
        if self.cardinality_evidence_id != cardinality.cardinality_evidence_id:
            raise RoutingV1Error("route upper cardinality-evidence mismatch")
        if self.route_kind is not cardinality.route_kind:
            raise RoutingV1Error("route upper/cardinality route mismatch")
        if self.route_cap_profile_id != cardinality.route_cap_profile_id:
            raise RoutingV1Error("route upper/cardinality cap mismatch")
        if self.route_kind is RouteKind.LOCAL_ATTEMPT:
            if transaction is None or causal is None:
                raise RoutingV1Error("local upper requires transaction and causal evidence")
            if self.transaction_id != transaction.transaction_id:
                raise RoutingV1Error("local upper transaction ID mismatch")
            if self.transaction_index != transaction.transaction_index:
                raise RoutingV1Error("local upper transaction index mismatch")
            if transaction.decision_point_id != decision_point.decision_point_id:
                raise RoutingV1Error("transaction decision-point mismatch")
            if transaction.logical_occurrence_id != context.logical_occurrence_id:
                raise RoutingV1Error("transaction occurrence mismatch")
            if transaction.route_attempt_id != context.route_attempt_id:
                raise RoutingV1Error("transaction route-attempt mismatch")
            if transaction.route_cap_profile_id != self.route_cap_profile_id:
                raise RoutingV1Error("transaction route-cap mismatch")
            if self.frontier_snapshot_id != transaction.frontier_snapshot_id:
                raise RoutingV1Error("transaction frontier mismatch")
            if self.causal_evidence_id != causal.causal_evidence_id:
                raise RoutingV1Error("causal evidence ID mismatch")
            if causal.local_allowed is not True:
                raise RoutingV1Error("negative causal evidence cannot authorize local")
            if causal.frontier_snapshot_id != self.frontier_snapshot_id:
                raise RoutingV1Error("causal evidence frontier mismatch")

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "RouteUpperBoundEnvelopeV1":
        expected = {
            "schema",
            "schema_version",
            "preregistration_id",
            "protocol_id",
            "comparison_profile_id",
            "counter_registry_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "BuildEpoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "transaction_id",
            "transaction_index",
            "frontier_snapshot_id",
            "causal_evidence_id",
            "route_cap_profile_id",
            "cardinality_evidence_id",
            "formula_id",
            "route_kind",
            "upper_kind",
            "upper_bounds",
            "route_upper_bound_envelope_id",
        }
        _fields(document, expected, "route upper")
        if (
            document["schema"] != "acfqp.route_upper_bound_envelope.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["upper_bounds"]) is not list
        ):
            raise RoutingV1Error("route-upper schema mismatch")
        route_kind = _enum(document["route_kind"], RouteKind, "route_kind")
        local = route_kind is RouteKind.LOCAL_ATTEMPT
        bounds: list[tuple[str, int]] = []
        for row in document["upper_bounds"]:
            _fields(row, {"axis", "value"}, "route-upper axis")
            bounds.append((row["axis"], row["value"]))
        result = cls(
            document["preregistration_id"],
            document["protocol_id"],
            document["comparison_profile_id"],
            document["counter_registry_id"],
            document["structural_id"],
            document["query_id"],
            document["selected_plan_id"],
            document["threshold_profile_id"],
            document["BuildEpoch_id"],
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            document["decision_point_id"],
            _parse_content_ref(document["transaction_id"], "transaction_id", allow_not_applicable=not local),
            _parse_index_ref(document["transaction_index"], "transaction_index", allow_not_applicable=not local),
            _parse_content_ref(document["frontier_snapshot_id"], "frontier_snapshot_id", allow_not_applicable=not local),
            _parse_content_ref(document["causal_evidence_id"], "causal_evidence_id", allow_not_applicable=not local),
            document["route_cap_profile_id"],
            document["cardinality_evidence_id"],
            document["formula_id"],
            route_kind,
            document["upper_kind"],
            tuple(bounds),
            document["schema_version"],
        )
        _verify_id(
            document,
            "route_upper_bound_envelope_id",
            ROUTE_UPPER_BOUND_ENVELOPE_DOMAIN,
            result._payload(),
        )
        return result


_UPPER_CONTEXT_FIELDS = (
    "preregistration_id",
    "protocol_id",
    "comparison_profile_id",
    "counter_registry_id",
    "structural_id",
    "query_id",
    "selected_plan_id",
    "threshold_profile_id",
    "build_epoch_id",
    "logical_occurrence_id",
    "route_attempt_id",
    "decision_point_id",
)


@dataclass(frozen=True, slots=True)
class MarginalRouteDecisionV1:
    decision_point_id: str
    causal_evidence_id: ContentRef
    local_upper_id: ContentRef
    fallback_upper_id: str
    selected_route: RouteSelection
    comparison: RouteComparison
    selected_upper_id: str

    def __post_init__(self) -> None:
        _cid(self.decision_point_id, "decision_point_id")
        object.__setattr__(
            self,
            "causal_evidence_id",
            _content_ref(self.causal_evidence_id, "causal_evidence_id", allow_not_applicable=True),
        )
        object.__setattr__(
            self,
            "local_upper_id",
            _content_ref(self.local_upper_id, "local_upper_id", allow_not_applicable=True),
        )
        _cid(self.fallback_upper_id, "fallback_upper_id")
        _cid(self.selected_upper_id, "selected_upper_id")
        object.__setattr__(self, "selected_route", _enum(self.selected_route, RouteSelection, "selected_route"))
        object.__setattr__(self, "comparison", _enum(self.comparison, RouteComparison, "comparison"))
        if self.selected_route is RouteSelection.LOCAL:
            if self.comparison is not RouteComparison.LOCAL_STRICTLY_DOMINATES:
                raise RoutingV1Error("local selection requires strict componentwise dominance")
            if isinstance(self.local_upper_id, TypedNotApplicable):
                raise RoutingV1Error("local selection requires a verified local upper")
            if self.selected_upper_id != self.local_upper_id:
                raise RoutingV1Error("selected local upper ID mismatch")
        elif self.selected_upper_id != self.fallback_upper_id:
            raise RoutingV1Error("fallback selection must bind the fallback upper")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.marginal_route_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "decision_point_id": self.decision_point_id,
            "causal_evidence_id": _ref_dict(self.causal_evidence_id),
            "local_upper_id": _ref_dict(self.local_upper_id),
            "fallback_upper_id": self.fallback_upper_id,
            "selected_route": self.selected_route.value,
            "comparison": self.comparison.value,
            "selected_upper_id": self.selected_upper_id,
        }

    @property
    def route_decision_id(self) -> str:
        return content_id(ROUTE_DECISION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "route_decision_id": self.route_decision_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "MarginalRouteDecisionV1":
        expected = {
            "schema",
            "schema_version",
            "decision_point_id",
            "causal_evidence_id",
            "local_upper_id",
            "fallback_upper_id",
            "selected_route",
            "comparison",
            "selected_upper_id",
            "route_decision_id",
        }
        _fields(document, expected, "marginal route decision")
        if (
            document["schema"] != "acfqp.marginal_route_decision.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise RoutingV1Error("marginal route-decision schema mismatch")
        result = cls(
            document["decision_point_id"],
            _parse_content_ref(
                document["causal_evidence_id"],
                "causal_evidence_id",
                allow_not_applicable=True,
            ),
            _parse_content_ref(
                document["local_upper_id"],
                "local_upper_id",
                allow_not_applicable=True,
            ),
            document["fallback_upper_id"],
            document["selected_route"],
            document["comparison"],
            document["selected_upper_id"],
        )
        _verify_id(
            document,
            "route_decision_id",
            ROUTE_DECISION_DOMAIN,
            result._payload(),
        )
        return result

    @classmethod
    def select(
        cls,
        decision_point: DecisionPointV1,
        fallback_upper: RouteUpperBoundEnvelopeV1,
        *,
        causal: CausalEvidenceV1 | None,
        local_upper: RouteUpperBoundEnvelopeV1 | None,
    ) -> "MarginalRouteDecisionV1":
        if fallback_upper.route_kind is not RouteKind.DIRECT_FALLBACK:
            raise RoutingV1Error("fallback route decision needs a direct-fallback upper")
        if fallback_upper.decision_point_id != decision_point.decision_point_id:
            raise RoutingV1Error("fallback upper is stale for this decision point")
        causal_id: ContentRef = (
            causal.causal_evidence_id
            if causal is not None
            else TypedNotApplicable("no causal search applies to this decision point")
        )
        if causal is not None and causal.local_allowed is not True:
            local_id: ContentRef = (
                local_upper.route_upper_bound_envelope_id
                if local_upper is not None
                else TypedNotApplicable("local route forbidden by causal outcome")
            )
            return cls(
                decision_point.decision_point_id,
                causal_id,
                local_id,
                fallback_upper.route_upper_bound_envelope_id,
                RouteSelection.FALLBACK,
                RouteComparison.LOCAL_FORBIDDEN,
                fallback_upper.route_upper_bound_envelope_id,
            )
        if local_upper is None:
            return cls(
                decision_point.decision_point_id,
                causal_id,
                TypedNotApplicable("verified local upper is missing"),
                fallback_upper.route_upper_bound_envelope_id,
                RouteSelection.FALLBACK,
                RouteComparison.MISSING_LOCAL_UPPER,
                fallback_upper.route_upper_bound_envelope_id,
            )
        if causal is None or causal.local_allowed is not True:
            raise RoutingV1Error("local comparison requires FOUND causal evidence")
        if local_upper.route_kind is not RouteKind.LOCAL_ATTEMPT:
            raise RoutingV1Error("local comparison needs a local-attempt upper")
        if local_upper.decision_point_id != decision_point.decision_point_id:
            raise RoutingV1Error("local upper is stale for this decision point")
        for field in _UPPER_CONTEXT_FIELDS:
            if getattr(local_upper, field) != getattr(fallback_upper, field):
                raise RoutingV1Error(f"route upper identity mismatch: {field}")
        if local_upper.causal_evidence_id != causal.causal_evidence_id:
            raise RoutingV1Error("local upper does not bind the supplied causal evidence")
        local = dict(local_upper.upper_bounds)
        fallback = dict(fallback_upper.upper_bounds)
        if set(local) != set(fallback):
            raise RoutingV1Error("route uppers use different comparison axes")
        local_le = all(local[axis] <= fallback[axis] for axis in local)
        fallback_le = all(fallback[axis] <= local[axis] for axis in local)
        if local_le and any(local[axis] < fallback[axis] for axis in local):
            selected = RouteSelection.LOCAL
            relation = RouteComparison.LOCAL_STRICTLY_DOMINATES
            selected_id = local_upper.route_upper_bound_envelope_id
        else:
            selected = RouteSelection.FALLBACK
            selected_id = fallback_upper.route_upper_bound_envelope_id
            if local_le and fallback_le:
                relation = RouteComparison.EQUAL
            elif fallback_le:
                relation = RouteComparison.FALLBACK_DOMINATES
            else:
                relation = RouteComparison.INCOMPARABLE
        return cls(
            decision_point.decision_point_id,
            causal_id,
            local_upper.route_upper_bound_envelope_id,
            fallback_upper.route_upper_bound_envelope_id,
            selected,
            relation,
            selected_id,
        )


class BudgetOutcome(str, Enum):
    BUDGET_REMAINS = "BUDGET_REMAINS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


# Operational local leaves whose actual values are replayable directly from a
# WorkVectorV1.  Structural compiler cardinalities (cells, members, actions,
# successor rows, policy assignments, and form-subset counts) remain checked by
# CardinalityEvidenceV1; only the compiler event leaves present in FQ11 are
# mapped here.
LOCAL_WORK_CAP_BINDINGS: tuple[tuple[str, str], ...] = (
    ("local.causal_candidate_evaluations", "max_causal_candidate_evaluations"),
    ("local.compiler_domain_assignments", "max_domain_assignments"),
    ("local.compiler_expanded_forms", "max_expanded_forms"),
    ("local.compiler_input_records", "max_slice_successor_rows"),
    ("local.materialization_ground_steps", "max_materialization_ground_steps"),
    ("local.materialization_outcome_rows", "max_materialization_positive_outcomes"),
    ("local.postaudit_ground_steps", "max_postaudit_ground_steps"),
    ("local.postaudit_outcome_rows", "max_postaudit_positive_outcomes"),
    ("local.solver_affine_term_evaluations", "max_affine_term_evaluations"),
    ("local.solver_dominance_comparisons", "max_dominance_comparisons"),
    ("local.solver_frontier_points", "max_root_frontier_points"),
    ("local.solver_policy_assignments", "max_policy_assignments"),
    ("local.solver_subset_evaluations", "max_subset_evaluations"),
)


@dataclass(frozen=True, slots=True)
class TrustedBudgetReplayV1:
    route_cap_profile_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    transaction_ids: tuple[str, ...]
    verified_work_vector_ids: tuple[str, ...]
    trusted_outcome: BudgetOutcome
    next_transaction_index: IndexRef
    worker_claim: ContentRef | str

    def __post_init__(self) -> None:
        for field in ("route_cap_profile_id", "logical_occurrence_id", "route_attempt_id"):
            _cid(getattr(self, field), field)
        if len(self.transaction_ids) > 2:
            raise RoutingV1Error("trusted replay exceeds the two-transaction budget")
        if len(self.transaction_ids) != len(self.verified_work_vector_ids):
            raise RoutingV1Error("each transaction needs one verified work vector")
        if len(set(self.transaction_ids)) != len(self.transaction_ids):
            raise RoutingV1Error("trusted replay repeats a transaction ID")
        if len(set(self.verified_work_vector_ids)) != len(self.verified_work_vector_ids):
            raise RoutingV1Error("trusted replay repeats a work-vector ID")
        for value in self.transaction_ids:
            _cid(value, "transaction_id")
        for value in self.verified_work_vector_ids:
            _cid(value, "verified_work_vector_id")
        object.__setattr__(self, "trusted_outcome", _enum(self.trusted_outcome, BudgetOutcome, "trusted outcome"))
        exhausted = len(self.transaction_ids) == 2
        expected = BudgetOutcome.BUDGET_EXHAUSTED if exhausted else BudgetOutcome.BUDGET_REMAINS
        if self.trusted_outcome is not expected:
            raise RoutingV1Error("trusted budget outcome does not match replayed transactions")
        object.__setattr__(
            self,
            "next_transaction_index",
            _index_ref(
                self.next_transaction_index,
                "next_transaction_index",
                allow_not_applicable=exhausted,
            ),
        )
        if exhausted:
            if not isinstance(self.next_transaction_index, TypedNotApplicable):
                raise RoutingV1Error("exhausted budget cannot expose a next index")
        elif self.next_transaction_index != len(self.transaction_ids) + 1:
            raise RoutingV1Error("trusted replay derived the wrong next transaction index")
        if isinstance(self.worker_claim, TypedNotApplicable):
            pass
        elif self.worker_claim not in {item.value for item in BudgetOutcome}:
            raise RoutingV1Error("worker budget claim is not a recognized untrusted claim")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.trusted_budget_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "route_cap_profile_id": self.route_cap_profile_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "transaction_ids": list(self.transaction_ids),
            "verified_work_vector_ids": list(self.verified_work_vector_ids),
            "trusted_outcome": self.trusted_outcome.value,
            "next_transaction_index": _ref_dict(self.next_transaction_index),
            "worker_claim": _ref_dict(self.worker_claim),
        }

    @property
    def trusted_budget_replay_id(self) -> str:
        return content_id(TRUSTED_BUDGET_REPLAY_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "trusted_budget_replay_id": self.trusted_budget_replay_id,
        }

    @classmethod
    def from_dict(
        cls,
        document: Mapping[str, Any],
        *,
        transactions: Sequence[TransactionV1] | None = None,
        work_vectors: Sequence[Any] | None = None,
        cap_profile: RouteCapProfileV1 | None = None,
        registry: Any | None = None,
    ) -> "TrustedBudgetReplayV1":
        """Load only with the native work needed for a trusted replay.

        A content-consistent document containing bare transaction/WorkVector IDs
        is not budget evidence.  Deserialization therefore repeats the same
        counter and subject checks as :meth:`replay_work_vectors`; callers that
        only possess the JSON document must fail closed.
        """
        expected = {
            "schema",
            "schema_version",
            "route_cap_profile_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "transaction_ids",
            "verified_work_vector_ids",
            "trusted_outcome",
            "next_transaction_index",
            "worker_claim",
            "trusted_budget_replay_id",
        }
        _fields(document, expected, "trusted budget replay")
        if (
            document["schema"] != "acfqp.trusted_budget_replay.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["transaction_ids"]) is not list
            or type(document["verified_work_vector_ids"]) is not list
        ):
            raise RoutingV1Error("trusted budget-replay schema mismatch")
        if transactions is None or work_vectors is None or cap_profile is None:
            raise RoutingV1Error(
                "native transactions, WorkVectors, and cap profile are required; "
                "an ID-only budget document is not trusted evidence"
            )
        worker_claim_value = document["worker_claim"]
        if isinstance(worker_claim_value, Mapping):
            worker_claim: str | TypedNotApplicable = TypedNotApplicable.from_dict(
                worker_claim_value
            )
        else:
            worker_claim = _token(worker_claim_value, "worker_claim")
        result = cls(
            document["route_cap_profile_id"],
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            tuple(document["transaction_ids"]),
            tuple(document["verified_work_vector_ids"]),
            document["trusted_outcome"],
            _parse_index_ref(
                document["next_transaction_index"],
                "next_transaction_index",
                allow_not_applicable=True,
            ),
            worker_claim,
        )
        _verify_id(
            document,
            "trusted_budget_replay_id",
            TRUSTED_BUDGET_REPLAY_DOMAIN,
            result._payload(),
        )
        replayed = cls.replay_work_vectors(
            transactions,
            work_vectors,
            cap_profile,
            worker_claim=worker_claim,
            registry=registry,
        )
        if result != replayed:
            raise RoutingV1Error(
                "trusted budget document does not match native WorkVector replay"
            )
        return result

    @classmethod
    def replay(
        cls,
        transactions: Sequence[TransactionV1],
        verified_work_vector_ids: Sequence[str],
        cap_profile: RouteCapProfileV1,
        *,
        worker_claim: str | TypedNotApplicable,
    ) -> "TrustedBudgetReplayV1":
        del transactions, verified_work_vector_ids, cap_profile, worker_claim
        raise RoutingV1Error(
            "ID-only trusted budget replay is forbidden; use replay_work_vectors"
        )

    @classmethod
    def _from_verified_work_vector_ids(
        cls,
        transactions: Sequence[TransactionV1],
        verified_work_vector_ids: Sequence[str],
        cap_profile: RouteCapProfileV1,
        *,
        worker_claim: str | TypedNotApplicable,
    ) -> "TrustedBudgetReplayV1":
        """Construct after ``replay_work_vectors`` has validated native work."""

        rows = tuple(transactions)
        if not rows:
            raise RoutingV1Error("trusted replay requires at least one completed transaction")
        if len(rows) > cap_profile.max_local_transactions_per_logical_occurrence:
            raise RoutingV1Error("transaction count exceeds the preregistered cap")
        occurrence = rows[0].logical_occurrence_id
        attempt = rows[0].route_attempt_id
        expected_indices = tuple(range(1, len(rows) + 1))
        actual_indices = tuple(row.transaction_index for row in rows)
        if actual_indices != expected_indices:
            raise RoutingV1Error("transaction indices must start at 1 and remain continuous")
        for row in rows:
            if row.logical_occurrence_id != occurrence or row.route_attempt_id != attempt:
                raise RoutingV1Error("trusted replay mixes occurrences or route attempts")
            if row.route_cap_profile_id != cap_profile.route_cap_profile_id:
                raise RoutingV1Error("trusted replay transaction uses another cap profile")
        exhausted = len(rows) == cap_profile.max_local_transactions_per_logical_occurrence
        return cls(
            cap_profile.route_cap_profile_id,
            occurrence,
            attempt,
            tuple(row.transaction_id for row in rows),
            tuple(verified_work_vector_ids),
            BudgetOutcome.BUDGET_EXHAUSTED if exhausted else BudgetOutcome.BUDGET_REMAINS,
            (
                TypedNotApplicable("maximum local transactions already used")
                if exhausted
                else len(rows) + 1
            ),
            worker_claim,
        )

    @classmethod
    def replay_work_vectors(
        cls,
        transactions: Sequence[TransactionV1],
        work_vectors: Sequence[Any],
        cap_profile: RouteCapProfileV1,
        *,
        worker_claim: str | TypedNotApplicable,
        registry: Any | None = None,
    ) -> "TrustedBudgetReplayV1":
        """Replay native local work and reject any actual cap overrun.

        The imports are intentionally local: accounting owns WorkVectorV1 and
        does not depend on routing, so this method adds no module-level cycle.
        Every vector is registry-validated, must be a LOCAL_ATTEMPT vector, and
        must use the transaction ID as its subject identity.  Structural caps
        without native FQ11 leaves are checked earlier by cardinality evidence.
        """

        from acfqp.accounting_v1 import (  # local import prevents a cycle
            RouteKindEnum,
            WorkVectorV1,
            official_counter_registry_v1,
        )

        rows = tuple(transactions)
        vectors = tuple(work_vectors)
        if len(rows) != len(vectors):
            raise RoutingV1Error("each transaction needs exactly one actual WorkVectorV1")
        if not rows:
            raise RoutingV1Error("trusted replay requires at least one completed transaction")
        trusted_registry = registry or official_counter_registry_v1()
        try:
            trusted_registry.validate_official_catalogue()
        except ValueError as error:
            raise RoutingV1Error(f"counter registry is not the official V1 catalogue: {error}") from error
        registered_local_paths = {
            path for path in trusted_registry.required_paths if path.startswith("local.")
        }
        bound_local_paths = {path for path, _ in LOCAL_WORK_CAP_BINDINGS}
        if registered_local_paths != bound_local_paths:
            raise RoutingV1Error("local WorkVector cap binding is incomplete for the registry")
        caps = dict(cap_profile.limits)
        for transaction, vector in zip(rows, vectors):
            if not isinstance(vector, WorkVectorV1):
                raise RoutingV1Error("actual work must be a WorkVectorV1")
            try:
                trusted_registry.validate_vector(vector)
            except ValueError as error:
                raise RoutingV1Error(f"actual WorkVectorV1 validation failed: {error}") from error
            if vector.route_kind is not RouteKindEnum.LOCAL_ATTEMPT:
                raise RoutingV1Error("trusted local replay rejects a non-local work vector")
            if vector.subject_id != transaction.transaction_id:
                raise RoutingV1Error("work-vector/transaction order or subject binding mismatch")
            for path, cap_name in LOCAL_WORK_CAP_BINDINGS:
                actual = vector.value(path)
                hard_cap = caps[cap_name]
                if actual > hard_cap:
                    raise RoutingV1Error(
                        f"actual counter {path}={actual} exceeds {cap_name}={hard_cap}"
                    )
        return cls._from_verified_work_vector_ids(
            rows,
            tuple(vector.work_vector_id for vector in vectors),
            cap_profile,
            worker_claim=worker_claim,
        )


class TerminalClass(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"
    INFEASIBILITY_CERTIFICATE = "INFEASIBILITY_CERTIFICATE"
    ATTEMPT_CLOSURE_NONCERTIFICATE = "ATTEMPT_CLOSURE_NONCERTIFICATE"


class TerminalCode(str, Enum):
    ABSTRACT_CERTIFIED = "ABSTRACT_CERTIFIED"
    LOCAL_GROUND_RECOVERY = "LOCAL_GROUND_RECOVERY"
    FULL_GROUND_FALLBACK = "FULL_GROUND_FALLBACK"
    CACHED_EXACT_INFEASIBLE = "CACHED_EXACT_INFEASIBLE"
    FULL_GROUND_EXACT_INFEASIBLE = "FULL_GROUND_EXACT_INFEASIBLE"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    REBUILD_REQUIRED = "REBUILD_REQUIRED"
    FALLBACK_CAP_EXHAUSTED = "FALLBACK_CAP_EXHAUSTED"
    ATTEMPT_BUDGET_EXHAUSTED = "ATTEMPT_BUDGET_EXHAUSTED"


_TERMINAL_CLASS_BY_CODE = {
    TerminalCode.ABSTRACT_CERTIFIED: TerminalClass.PLAN_CERTIFICATE,
    TerminalCode.LOCAL_GROUND_RECOVERY: TerminalClass.PLAN_CERTIFICATE,
    TerminalCode.FULL_GROUND_FALLBACK: TerminalClass.PLAN_CERTIFICATE,
    TerminalCode.CACHED_EXACT_INFEASIBLE: TerminalClass.INFEASIBILITY_CERTIFICATE,
    TerminalCode.FULL_GROUND_EXACT_INFEASIBLE: TerminalClass.INFEASIBILITY_CERTIFICATE,
    TerminalCode.INTEGRITY_FAILURE: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
    TerminalCode.PROTOCOL_FAILURE: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
    TerminalCode.REBUILD_REQUIRED: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
    TerminalCode.FALLBACK_CAP_EXHAUSTED: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
    TerminalCode.ATTEMPT_BUDGET_EXHAUSTED: TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE,
}


@dataclass(frozen=True, slots=True)
class TerminalArtifactV1:
    terminal_scope: str
    terminal_class: TerminalClass
    terminal_code: TerminalCode
    route_decision_context_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: ContentRef
    transaction_id: ContentRef
    actual_work_vector_id: str
    evidence_attestation_ids: tuple[str, ...]
    actual_comparison_vector_id: ContentRef = TypedNotApplicable(
        "terminal has no marginal actual comparison"
    )
    actual_projection_proof_id: ContentRef = TypedNotApplicable(
        "terminal has no marginal actual projection"
    )
    marginal_work_aggregation_proof_id: ContentRef = TypedNotApplicable(
        "terminal has no marginal aggregation proof"
    )
    route_decision_freeze_attestation_id: ContentRef = TypedNotApplicable(
        "terminal has no successful route freeze"
    )
    access_event_log_id: ContentRef = TypedNotApplicable(
        "terminal has no successful route access log"
    )

    def __post_init__(self) -> None:
        if self.terminal_scope not in {"ROUTE_ATTEMPT", "LOGICAL_OCCURRENCE"}:
            raise RoutingV1Error("terminal_scope must be ROUTE_ATTEMPT or LOGICAL_OCCURRENCE")
        object.__setattr__(self, "terminal_class", _enum(self.terminal_class, TerminalClass, "terminal_class"))
        object.__setattr__(self, "terminal_code", _enum(self.terminal_code, TerminalCode, "terminal_code"))
        if _TERMINAL_CLASS_BY_CODE[self.terminal_code] is not self.terminal_class:
            raise RoutingV1Error("terminal class/code mismatch")
        for field in (
            "route_decision_context_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "actual_work_vector_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(
            self,
            "decision_point_id",
            _content_ref(self.decision_point_id, "decision_point_id", allow_not_applicable=True),
        )
        object.__setattr__(
            self,
            "transaction_id",
            _content_ref(self.transaction_id, "transaction_id", allow_not_applicable=True),
        )
        for field in (
            "actual_comparison_vector_id",
            "actual_projection_proof_id",
            "marginal_work_aggregation_proof_id",
            "route_decision_freeze_attestation_id",
            "access_event_log_id",
        ):
            object.__setattr__(
                self,
                field,
                _content_ref(
                    getattr(self, field), field, allow_not_applicable=True
                ),
            )
        if (
            not self.evidence_attestation_ids
            or tuple(sorted(self.evidence_attestation_ids)) != self.evidence_attestation_ids
            or len(set(self.evidence_attestation_ids)) != len(self.evidence_attestation_ids)
        ):
            raise RoutingV1Error("terminal evidence attestations must be nonempty, unique, and sorted")
        for attestation_id in self.evidence_attestation_ids:
            _cid(attestation_id, "evidence_attestation_id")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.terminal_artifact.v1",
            "schema_version": SCHEMA_VERSION,
            "terminal_scope": self.terminal_scope,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": _ref_dict(self.decision_point_id),
            "transaction_id": _ref_dict(self.transaction_id),
            "actual_work_vector_id": self.actual_work_vector_id,
            "evidence_attestation_ids": list(self.evidence_attestation_ids),
            "actual_comparison_vector_id": _ref_dict(
                self.actual_comparison_vector_id
            ),
            "actual_projection_proof_id": _ref_dict(
                self.actual_projection_proof_id
            ),
            "marginal_work_aggregation_proof_id": _ref_dict(
                self.marginal_work_aggregation_proof_id
            ),
            "route_decision_freeze_attestation_id": _ref_dict(
                self.route_decision_freeze_attestation_id
            ),
            "access_event_log_id": _ref_dict(self.access_event_log_id),
        }

    @property
    def terminal_artifact_id(self) -> str:
        return content_id(TERMINAL_ARTIFACT_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "terminal_artifact_id": self.terminal_artifact_id}

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "TerminalArtifactV1":
        expected = {
            "schema",
            "schema_version",
            "terminal_scope",
            "terminal_class",
            "terminal_code",
            "RouteDecisionContext_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "transaction_id",
            "actual_work_vector_id",
            "evidence_attestation_ids",
            "actual_comparison_vector_id",
            "actual_projection_proof_id",
            "marginal_work_aggregation_proof_id",
            "route_decision_freeze_attestation_id",
            "access_event_log_id",
            "terminal_artifact_id",
        }
        _fields(document, expected, "terminal artifact")
        if (
            document["schema"] != "acfqp.terminal_artifact.v1"
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["evidence_attestation_ids"]) is not list
        ):
            raise RoutingV1Error("terminal artifact schema mismatch")
        result = cls(
            document["terminal_scope"],
            document["terminal_class"],
            document["terminal_code"],
            document["RouteDecisionContext_id"],
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            _parse_content_ref(
                document["decision_point_id"],
                "decision_point_id",
                allow_not_applicable=True,
            ),
            _parse_content_ref(
                document["transaction_id"],
                "transaction_id",
                allow_not_applicable=True,
            ),
            document["actual_work_vector_id"],
            tuple(document["evidence_attestation_ids"]),
            _parse_content_ref(
                document["actual_comparison_vector_id"],
                "actual_comparison_vector_id",
                allow_not_applicable=True,
            ),
            _parse_content_ref(
                document["actual_projection_proof_id"],
                "actual_projection_proof_id",
                allow_not_applicable=True,
            ),
            _parse_content_ref(
                document["marginal_work_aggregation_proof_id"],
                "marginal_work_aggregation_proof_id",
                allow_not_applicable=True,
            ),
            _parse_content_ref(
                document["route_decision_freeze_attestation_id"],
                "route_decision_freeze_attestation_id",
                allow_not_applicable=True,
            ),
            _parse_content_ref(
                document["access_event_log_id"],
                "access_event_log_id",
                allow_not_applicable=True,
            ),
        )
        _verify_id(
            document,
            "terminal_artifact_id",
            TERMINAL_ARTIFACT_DOMAIN,
            result._payload(),
        )
        return result


_ROLE_CONTRACT: Mapping[str, tuple[str, frozenset[str]]] = {
    "EXACT_CACHED_INFEASIBILITY": (
        "ExactCachedInfeasibilityProofV1",
        frozenset({"IDENTICAL_MATCH", "NO_MATCH", "INVALID"}),
    ),
    "ABSTRACT_AUDIT": (
        "AbstractPlanAuditV1",
        frozenset({"PASS", "FAIL", "INVALID"}),
    ),
    "CAUSAL_SEARCH": (
        "CausalEvidenceV1",
        frozenset({item.value for item in CausalOutcome} | {"INVALID"}),
    ),
    "CARDINALITY_EVIDENCE": (
        "CardinalityEvidenceV1",
        frozenset({"VALID", "INVALID"}),
    ),
    "ROUTE_UPPER": (
        "RouteUpperBoundEnvelopeV1",
        frozenset({"VALID", "INVALID"}),
    ),
    "ROUTE_DECISION": (
        "RouteDecisionV1",
        frozenset({"LOCAL", "FALLBACK", "INVALID"}),
    ),
    "LOCAL_SOLVER_RESULT": (
        "LocalTransactionResultV1",
        frozenset({"CANDIDATE_FOUND", "SEARCH_CAP_EXHAUSTED", "NO_FEASIBLE_ASSIGNMENT", "INVALID"}),
    ),
    "POST_AUDIT": (
        "PostAuditCertificateV1",
        frozenset({"CERTIFIED", "FAILED", "INVALID"}),
    ),
    "GROUND_FALLBACK": (
        "GroundFallbackResultV1",
        frozenset({"FEASIBLE_CERTIFIED", "INFEASIBLE_CERTIFIED", "CAP_EXHAUSTED", "INVALID"}),
    ),
    "WORK_VECTOR": (
        "WorkVectorV1",
        frozenset({"VALID", "INVALID"}),
    ),
    "ACTUAL_PROJECTION": (
        "ComparisonVectorV1",
        frozenset({"VALID", "INVALID"}),
    ),
    "TERMINAL_CLASSIFICATION": (
        "TerminalArtifactV1",
        frozenset({item.value for item in TerminalClass} | {"INVALID"}),
    ),
}


@dataclass(frozen=True, slots=True)
class TypedVerificationAttestationV1:
    artifact_id: str
    artifact_schema_id: str
    artifact_role: str
    route_decision_context_id: str
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    build_epoch_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: ContentRef
    transaction_id: ContentRef
    semantic_verifier_id: str
    verification_profile_id: str
    verification_result: str
    verification_work_counter_record_id: str
    verified_at_protocol_step: int

    def __post_init__(self) -> None:
        for field in (
            "artifact_id",
            "route_decision_context_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "build_epoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "semantic_verifier_id",
            "verification_profile_id",
            "verification_work_counter_record_id",
        ):
            _cid(getattr(self, field), field)
        object.__setattr__(
            self,
            "decision_point_id",
            _content_ref(self.decision_point_id, "decision_point_id", allow_not_applicable=True),
        )
        object.__setattr__(
            self,
            "transaction_id",
            _content_ref(self.transaction_id, "transaction_id", allow_not_applicable=True),
        )
        contract = _ROLE_CONTRACT.get(self.artifact_role)
        if contract is None:
            raise RoutingV1Error(f"unknown authoritative artifact role {self.artifact_role!r}")
        expected_schema, outcomes = contract
        if self.artifact_schema_id != expected_schema:
            raise RoutingV1Error("artifact role/schema mismatch")
        if self.verification_result not in outcomes:
            raise RoutingV1Error("verification result is invalid for the artifact role")
        _nonnegative(self.verified_at_protocol_step, "verified_at_protocol_step")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.typed_verification_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "artifact_id": self.artifact_id,
            "artifact_schema_id": self.artifact_schema_id,
            "artifact_role": self.artifact_role,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "BuildEpoch_id": self.build_epoch_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "decision_point_id": _ref_dict(self.decision_point_id),
            "transaction_id": _ref_dict(self.transaction_id),
            "semantic_verifier_id": self.semantic_verifier_id,
            "verification_profile_id": self.verification_profile_id,
            "verification_result": self.verification_result,
            "verification_work_counter_record_id": self.verification_work_counter_record_id,
            "verified_at_protocol_step": self.verified_at_protocol_step,
        }

    @property
    def verification_attestation_id(self) -> str:
        return content_id(TYPED_VERIFICATION_ATTESTATION_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_attestation_id": self.verification_attestation_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "TypedVerificationAttestationV1":
        expected = {
            "schema",
            "schema_version",
            "artifact_id",
            "artifact_schema_id",
            "artifact_role",
            "RouteDecisionContext_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "BuildEpoch_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "transaction_id",
            "semantic_verifier_id",
            "verification_profile_id",
            "verification_result",
            "verification_work_counter_record_id",
            "verified_at_protocol_step",
            "verification_attestation_id",
        }
        _fields(document, expected, "typed verification attestation")
        if (
            document["schema"] != "acfqp.typed_verification_attestation.v1"
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise RoutingV1Error("typed verification-attestation schema mismatch")
        result = cls(
            document["artifact_id"],
            document["artifact_schema_id"],
            document["artifact_role"],
            document["RouteDecisionContext_id"],
            document["structural_id"],
            document["query_id"],
            document["selected_plan_id"],
            document["threshold_profile_id"],
            document["BuildEpoch_id"],
            document["logical_occurrence_id"],
            document["route_attempt_id"],
            _parse_content_ref(
                document["decision_point_id"],
                "decision_point_id",
                allow_not_applicable=True,
            ),
            _parse_content_ref(
                document["transaction_id"],
                "transaction_id",
                allow_not_applicable=True,
            ),
            document["semantic_verifier_id"],
            document["verification_profile_id"],
            document["verification_result"],
            document["verification_work_counter_record_id"],
            document["verified_at_protocol_step"],
        )
        _verify_id(
            document,
            "verification_attestation_id",
            TYPED_VERIFICATION_ATTESTATION_DOMAIN,
            result._payload(),
        )
        return result


def verify_unique_attestation_roles(
    attestations: Sequence[TypedVerificationAttestationV1],
) -> None:
    """Reject reuse of one artifact ID under incompatible evidence roles."""

    roles: dict[str, str] = {}
    for attestation in attestations:
        existing = roles.setdefault(attestation.artifact_id, attestation.artifact_role)
        if existing != attestation.artifact_role:
            raise RoutingV1Error("one artifact ID was reused across incompatible roles")


__all__ = [
    "BudgetOutcome",
    "CardinalityEvidenceV1",
    "CardinalitySourceKind",
    "CausalEvidenceV1",
    "CausalOutcome",
    "DecisionPointV1",
    "FrontierSnapshotV1",
    "FrozenCardinalityCollectionV1",
    "FrozenCardinalitySourceV1",
    "LOCAL_WORK_CAP_BINDINGS",
    "MarginalRouteDecisionV1",
    "OFFICIAL_LOCAL_CAPS",
    "PROFILE_KEY",
    "RouteCapProfileV1",
    "RouteComparison",
    "RouteDecisionContextV1",
    "RouteKind",
    "RouteSelection",
    "RouteUpperBoundEnvelopeV1",
    "RoutingV1Error",
    "SCHEMA_VERSION",
    "TIGHT_PREEXECUTION_UPPER",
    "TerminalArtifactV1",
    "TerminalClass",
    "TerminalCode",
    "TransactionV1",
    "TrustedBudgetReplayV1",
    "TypedNotApplicable",
    "TypedVerificationAttestationV1",
    "verify_unique_attestation_roles",
]
