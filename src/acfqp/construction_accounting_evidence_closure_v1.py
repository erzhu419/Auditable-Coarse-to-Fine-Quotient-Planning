"""Fail-closed evidence coverage for the V6 K7 accounting path.

This module closes only the *coverage* question: it records how every
required V6 counter path is intended to be resolved and verifies that no path
was silently treated as zero.  It deliberately does not construct a
``CounterRecord``, ``WorkVector`` or ``ComparisonVector``.  Those artifacts
remain unavailable until the source evidence referenced here has independent
semantic verifiers.

An initialized closure contains every required path in the ``UNRESOLVED``
state.  A path may subsequently be closed by exactly one of four evidence
families:

* a positive, ordered owner-bound event stream;
* one shared-resource receipt reference (including an explicit zero claim);
* one profile-native-zero attestation; or
* one registered derived-reconciliation proof.

Absence of an event is never evidence of zero.  These are structural evidence
references, not semantic attestations.  Resolutions are immutable and
cannot be overwritten, which also prevents two evidence families from
charging the same leaf through this layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Iterable

from acfqp.accounting_v1 import LaneEnum, ReducerEnum
from acfqp.construction_accounting_registry_v6 import (
    CounterRegistryV6,
    official_counter_registry_v6,
    official_stage_profile_v6,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN,
    CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_ACCOUNTING_REQUIRED_PATH_RESOLUTION_V1_DOMAIN,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"

EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN
)
REQUIRED_PATH_RESOLUTION_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_REQUIRED_PATH_RESOLUTION_V1_DOMAIN
)
EVIDENCE_CLOSURE_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_V1_DOMAIN
)
EVIDENCE_CLOSURE_VERIFICATION_V1_DOMAIN = (
    CONSTRUCTION_ACCOUNTING_EVIDENCE_CLOSURE_VERIFICATION_V1_DOMAIN
)


SHARED_RESOURCE_PATHS_V1 = tuple(
    sorted(
        {
            "common.hash_invocations",
            "common.integrity_checks",
            "common.protocol_checks",
            "io.output_bytes",
            "io.read_bytes",
            "io.staged_bytes",
            "process.launches",
            "io.mounted_bytes_peak",
            "memory.working_bytes_peak",
        }
    )
)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")


class ConstructionAccountingEvidenceClosureV1Error(ValueError):
    """A coverage artifact is malformed, incomplete, or identity-stale."""


class RequiredPathResolutionKindV1(str, Enum):
    """The only states/evidence families accepted by the closure."""

    UNRESOLVED = "UNRESOLVED"
    POSITIVE_EVENT_STREAM = "POSITIVE_EVENT_STREAM"
    SHARED_RESOURCE_RECEIPT = "SHARED_RESOURCE_RECEIPT"
    PROFILE_NATIVE_ZERO = "PROFILE_NATIVE_ZERO"
    DERIVED_RECONCILIATION = "DERIVED_RECONCILIATION"


# A concise alias is useful to consumers while retaining the artifact-specific
# public name above.
EvidenceResolutionKindV1 = RequiredPathResolutionKindV1


class EvidenceClosureCoverageStateV1(str, Enum):
    """Structural coverage only; neither state validates source semantics."""

    INCOMPLETE = "STRUCTURAL_COVERAGE_INCOMPLETE"
    COMPLETE_UNVERIFIED = "STRUCTURAL_COVERAGE_COMPLETE_UNVERIFIED"


# Compatibility name for the concurrent readiness consumer.  The enum values
# themselves deliberately no longer say ``COMPLETE_EVIDENCE``.
EvidenceClosureCompletenessV1 = EvidenceClosureCoverageStateV1


def _content_id(domain_tag: str, payload: Any) -> str:
    """Use the central domain-separated content-ID authority."""

    return content_id(domain_tag, payload)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ConstructionAccountingEvidenceClosureV1Error(
            f"{field_name} must be a full content ID"
        ) from error


def _identifier(value: Any, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER.fullmatch(value) is None:
        raise ConstructionAccountingEvidenceClosureV1Error(
            f"{field_name} must be a canonical identifier"
        )
    return value


def _ids(values: Iterable[str], field_name: str) -> tuple[str, ...]:
    result = tuple(values)
    for value in result:
        _cid(value, field_name)
    if len(set(result)) != len(result):
        raise ConstructionAccountingEvidenceClosureV1Error(
            f"{field_name} contains a repeated content ID"
        )
    return result


def _registry(selected: CounterRegistryV6 | None) -> CounterRegistryV6:
    result = selected or official_counter_registry_v6()
    if type(result) is not CounterRegistryV6:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "coverage requires the exact V6 counter-registry type"
        )
    try:
        result.validate_official_catalogue()
    except Exception as error:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "coverage registry is not the official V6 catalogue"
        ) from error
    return result


@dataclass(frozen=True, slots=True)
class EvidenceClosureContextV1:
    """All authorities and executed evidence to which a closure is bound."""

    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    execution_profile_id: str
    transcript_id: str
    terminal_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "execution_profile_id",
            "transcript_id",
            "terminal_id",
        ):
            _cid(getattr(self, field_name), field_name)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_evidence_closure_context.v1",
            "schema_version": SCHEMA_VERSION,
            "counter_registry_id": self.counter_registry_id,
            "stage_profile_id": self.stage_profile_id,
            "boundary_profile_id": self.boundary_profile_id,
            "execution_profile_id": self.execution_profile_id,
            "transcript_id": self.transcript_id,
            "terminal_id": self.terminal_id,
        }

    @property
    def context_id(self) -> str:
        return _content_id(EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_closure_context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class RequiredPathResolutionV1:
    """One immutable required-path state or evidence-backed resolution."""

    context_id: str
    path: str
    reducer: ReducerEnum
    resolution_kind: RequiredPathResolutionKindV1
    resolved_value: int | None
    source_evidence_ids: tuple[str, ...]
    dependency_paths: tuple[str, ...] = ()
    formula_id: str | None = None

    def __post_init__(self) -> None:
        _cid(self.context_id, "context_id")
        _identifier(self.path, "path")
        try:
            reducer = ReducerEnum(self.reducer)
            kind = RequiredPathResolutionKindV1(self.resolution_kind)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingEvidenceClosureV1Error(
                "resolution kind or reducer is invalid"
            ) from error
        object.__setattr__(self, "reducer", reducer)
        object.__setattr__(self, "resolution_kind", kind)
        source_ids = _ids(self.source_evidence_ids, "source_evidence_ids")
        object.__setattr__(self, "source_evidence_ids", source_ids)
        dependencies = tuple(self.dependency_paths)
        if (
            any(_IDENTIFIER.fullmatch(value) is None for value in dependencies)
            or tuple(sorted(dependencies)) != dependencies
            or len(set(dependencies)) != len(dependencies)
            or self.path in dependencies
        ):
            raise ConstructionAccountingEvidenceClosureV1Error(
                "dependency paths must be sorted, unique, canonical, and non-self"
            )
        object.__setattr__(self, "dependency_paths", dependencies)

        if kind is RequiredPathResolutionKindV1.UNRESOLVED:
            if (
                self.resolved_value is not None
                or source_ids
                or dependencies
                or self.formula_id is not None
            ):
                raise ConstructionAccountingEvidenceClosureV1Error(
                    "UNRESOLVED cannot carry a value or evidence"
                )
        else:
            if type(self.resolved_value) is not int or self.resolved_value < 0:
                raise ConstructionAccountingEvidenceClosureV1Error(
                    "resolved evidence must carry a nonnegative exact integer"
                )

        if kind is RequiredPathResolutionKindV1.POSITIVE_EVENT_STREAM:
            if (
                reducer is not ReducerEnum.SUM
                or type(self.resolved_value) is not int
                or self.resolved_value <= 0
                or not source_ids
                or dependencies
                or self.formula_id is not None
            ):
                raise ConstructionAccountingEvidenceClosureV1Error(
                    "positive-event resolution requires positive SUM events only"
                )
        elif kind is RequiredPathResolutionKindV1.SHARED_RESOURCE_RECEIPT:
            if (
                self.path not in SHARED_RESOURCE_PATHS_V1
                or len(source_ids) != 1
                or dependencies
                or self.formula_id is not None
            ):
                raise ConstructionAccountingEvidenceClosureV1Error(
                    "shared-resource resolution requires its one typed receipt"
                )
        elif kind is RequiredPathResolutionKindV1.PROFILE_NATIVE_ZERO:
            if (
                self.resolved_value != 0
                or len(source_ids) != 1
                or dependencies
                or self.formula_id is not None
            ):
                raise ConstructionAccountingEvidenceClosureV1Error(
                    "profile-native-zero requires one explicit zero attestation"
                )
        elif kind is RequiredPathResolutionKindV1.DERIVED_RECONCILIATION:
            if len(source_ids) != 1 or not dependencies or self.formula_id is None:
                raise ConstructionAccountingEvidenceClosureV1Error(
                    "derived reconciliation requires proof, formula, and dependencies"
                )
            _cid(self.formula_id, "formula_id")

    @classmethod
    def unresolved(
        cls,
        *,
        context_id: str,
        path: str,
        reducer: ReducerEnum,
    ) -> "RequiredPathResolutionV1":
        return cls(
            context_id,
            path,
            reducer,
            RequiredPathResolutionKindV1.UNRESOLVED,
            None,
            (),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_required_path_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "path": self.path,
            "reducer": self.reducer.value,
            "resolution_kind": self.resolution_kind.value,
            "resolved_value": self.resolved_value,
            "source_evidence_ids": list(self.source_evidence_ids),
            "dependency_paths": list(self.dependency_paths),
            "formula_id": self.formula_id,
        }

    @property
    def resolution_id(self) -> str:
        return _content_id(REQUIRED_PATH_RESOLUTION_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "required_path_resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class EvidenceClosureV1:
    """Occurrence-level coverage state; never a work or comparison vector."""

    context: EvidenceClosureContextV1
    resolutions: tuple[RequiredPathResolutionV1, ...]

    def __post_init__(self) -> None:
        if type(self.context) is not EvidenceClosureContextV1:
            raise ConstructionAccountingEvidenceClosureV1Error(
                "closure context has a foreign type"
            )
        if (
            not self.resolutions
            or tuple(sorted(self.resolutions, key=lambda row: row.path))
            != self.resolutions
            or len({row.path for row in self.resolutions})
            != len(self.resolutions)
            or any(
                type(row) is not RequiredPathResolutionV1
                or row.context_id != self.context.context_id
                for row in self.resolutions
            )
        ):
            raise ConstructionAccountingEvidenceClosureV1Error(
                "closure resolutions must be nonempty, unique, sorted, and context-bound"
            )

    @property
    def by_path(self) -> dict[str, RequiredPathResolutionV1]:
        return {row.path: row for row in self.resolutions}

    @property
    def unresolved_paths(self) -> tuple[str, ...]:
        return tuple(
            row.path
            for row in self.resolutions
            if row.resolution_kind is RequiredPathResolutionKindV1.UNRESOLVED
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_evidence_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "resolutions": [row.to_document() for row in self.resolutions],
            "missing_paths_inferred_zero": False,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "coverage_only": True,
            "source_evidence_semantics_verified": False,
            "numeric_projection_allowed": False,
            "formal_vector_authorized": False,
        }

    @property
    def closure_id(self) -> str:
        return _content_id(EVIDENCE_CLOSURE_V1_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_closure_id": self.closure_id}


@dataclass(frozen=True, slots=True, init=False)
class EvidenceClosureCoverageReplayV1:
    """Factory-issued structural replay, never authority for accounting values.

    ``init=False`` intentionally prevents callers from manufacturing something
    that looks like a verifier result.  Only
    :func:`verify_evidence_closure_coverage_v1` may issue this object, and its
    serialized contract always denies semantic, numeric, and formal authority.
    """

    context_id: str
    evidence_closure_id: str
    counter_registry_id: str
    coverage_state: EvidenceClosureCoverageStateV1
    required_path_count: int
    resolved_path_count: int
    unresolved_paths: tuple[str, ...]
    resolution_counts: tuple[tuple[str, int], ...]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "coverage replay artifacts can only be issued by the structural replay"
        )

    @classmethod
    def _issue(
        cls,
        *,
        context_id: str,
        evidence_closure_id: str,
        counter_registry_id: str,
        coverage_state: EvidenceClosureCoverageStateV1,
        required_path_count: int,
        resolved_path_count: int,
        unresolved_paths: tuple[str, ...],
        resolution_counts: tuple[tuple[str, int], ...],
    ) -> "EvidenceClosureCoverageReplayV1":
        result = object.__new__(cls)
        for name, value in (
            ("context_id", context_id),
            ("evidence_closure_id", evidence_closure_id),
            ("counter_registry_id", counter_registry_id),
            ("coverage_state", coverage_state),
            ("required_path_count", required_path_count),
            ("resolved_path_count", resolved_path_count),
            ("unresolved_paths", unresolved_paths),
            ("resolution_counts", resolution_counts),
        ):
            object.__setattr__(result, name, value)
        result._validate()
        return result

    def _validate(self) -> None:
        for name in ("context_id", "evidence_closure_id", "counter_registry_id"):
            _cid(getattr(self, name), name)
        try:
            coverage_state = EvidenceClosureCoverageStateV1(self.coverage_state)
        except (TypeError, ValueError) as error:
            raise ConstructionAccountingEvidenceClosureV1Error(
                "structural coverage state enum is invalid"
            ) from error
        object.__setattr__(self, "coverage_state", coverage_state)
        if (
            type(self.required_path_count) is not int
            or type(self.resolved_path_count) is not int
            or not 0 <= self.resolved_path_count <= self.required_path_count
            or tuple(sorted(self.unresolved_paths)) != self.unresolved_paths
            or len(set(self.unresolved_paths)) != len(self.unresolved_paths)
            or self.required_path_count - self.resolved_path_count
            != len(self.unresolved_paths)
        ):
            raise ConstructionAccountingEvidenceClosureV1Error(
                "coverage verification cardinality is inconsistent"
            )
        expected_names = tuple(item.value for item in RequiredPathResolutionKindV1)
        if (
            tuple(name for name, _value in self.resolution_counts)
            != expected_names
            or any(type(value) is not int or value < 0 for _, value in self.resolution_counts)
            or sum(value for _, value in self.resolution_counts)
            != self.required_path_count
        ):
            raise ConstructionAccountingEvidenceClosureV1Error(
                "resolution counts are incomplete or noncanonical"
            )
        if (
            coverage_state
            is EvidenceClosureCoverageStateV1.COMPLETE_UNVERIFIED
        ) != (not self.unresolved_paths):
            raise ConstructionAccountingEvidenceClosureV1Error(
                "structural coverage state does not match unresolved paths"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_accounting_evidence_closure_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "evidence_closure_id": self.evidence_closure_id,
            "counter_registry_id": self.counter_registry_id,
            "coverage_state": self.coverage_state.value,
            "required_path_count": self.required_path_count,
            "resolved_path_count": self.resolved_path_count,
            "unresolved_paths": list(self.unresolved_paths),
            "resolution_counts": [
                {"resolution_kind": name, "count": value}
                for name, value in self.resolution_counts
            ],
            "missing_paths_inferred_zero": False,
            "coverage_only": True,
            "source_evidence_semantics_verified": False,
            "numeric_projection_allowed": False,
            "formal_vector_authorized": False,
        }

    @property
    def completeness(self) -> EvidenceClosureCoverageStateV1:
        """Compatibility view whose value remains explicitly unverified."""

        return self.coverage_state

    @property
    def verification_id(self) -> str:
        return _content_id(
            EVIDENCE_CLOSURE_VERIFICATION_V1_DOMAIN, self._payload()
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "evidence_closure_verification_id": self.verification_id,
        }


def initialize_evidence_closure_v1(
    context: EvidenceClosureContextV1,
    *,
    registry: CounterRegistryV6 | None = None,
) -> EvidenceClosureV1:
    """Create all required rows as ``UNRESOLVED``; never synthesize zeros."""

    if type(context) is not EvidenceClosureContextV1:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "initializer requires an exact evidence-closure context"
        )
    selected = _registry(registry)
    stage_profile = official_stage_profile_v6(selected)
    if (
        context.counter_registry_id != selected.registry_id
        or context.stage_profile_id != stage_profile.stage_profile_id
    ):
        raise ConstructionAccountingEvidenceClosureV1Error(
            "context registry or stage-profile identity is stale"
        )
    return EvidenceClosureV1(
        context,
        tuple(
            RequiredPathResolutionV1.unresolved(
                context_id=context.context_id,
                path=path,
                reducer=selected.by_path[path].reducer,
            )
            for path in selected.required_paths
        ),
    )


def _validate_resolution_for_leaf(
    resolution: RequiredPathResolutionV1,
    registry: CounterRegistryV6,
) -> None:
    if resolution.path not in registry.by_path:
        raise ConstructionAccountingEvidenceClosureV1Error(
            f"unknown V6 counter path {resolution.path!r}"
        )
    leaf = registry.by_path[resolution.path]
    if not leaf.required or resolution.reducer is not leaf.reducer:
        raise ConstructionAccountingEvidenceClosureV1Error(
            f"resolution metadata differs from required leaf {resolution.path!r}"
        )
    kind = resolution.resolution_kind
    if kind is RequiredPathResolutionKindV1.UNRESOLVED:
        return
    if resolution.path in SHARED_RESOURCE_PATHS_V1:
        if kind is not RequiredPathResolutionKindV1.SHARED_RESOURCE_RECEIPT:
            raise ConstructionAccountingEvidenceClosureV1Error(
                f"shared path {resolution.path!r} requires its typed receipt"
            )
        return
    if leaf.lane is LaneEnum.DERIVED_ONLY:
        if kind is not RequiredPathResolutionKindV1.DERIVED_RECONCILIATION:
            raise ConstructionAccountingEvidenceClosureV1Error(
                f"derived path {resolution.path!r} requires reconciliation"
            )
        return
    if kind not in {
        RequiredPathResolutionKindV1.POSITIVE_EVENT_STREAM,
        RequiredPathResolutionKindV1.PROFILE_NATIVE_ZERO,
    }:
        raise ConstructionAccountingEvidenceClosureV1Error(
            f"owner path {resolution.path!r} requires events or explicit zero"
        )


def apply_required_path_resolution_v1(
    closure: EvidenceClosureV1,
    resolution: RequiredPathResolutionV1,
    *,
    registry: CounterRegistryV6 | None = None,
) -> EvidenceClosureV1:
    """Replace one unresolved row exactly once and return a new closure."""

    if type(closure) is not EvidenceClosureV1 or type(resolution) is not RequiredPathResolutionV1:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "resolution application requires exact typed artifacts"
        )
    selected = _registry(registry)
    _validate_closure_shape(closure, selected)
    if resolution.context_id != closure.context.context_id:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "resolution belongs to another closure context"
        )
    _validate_resolution_for_leaf(resolution, selected)
    previous = closure.by_path.get(resolution.path)
    if previous is None:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "resolution path is not required by the bound registry"
        )
    if previous.resolution_kind is not RequiredPathResolutionKindV1.UNRESOLVED:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "a required path cannot be resolved or charged twice"
        )
    if resolution.resolution_kind is RequiredPathResolutionKindV1.UNRESOLVED:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "applying another UNRESOLVED row makes no progress"
        )
    rows = dict(closure.by_path)
    rows[resolution.path] = resolution
    result = EvidenceClosureV1(
        closure.context, tuple(rows[path] for path in sorted(rows))
    )
    _validate_closure_shape(result, selected)
    return result


def resolve_positive_event_stream_v1(
    closure: EvidenceClosureV1,
    *,
    path: str,
    resolved_value: int,
    event_ids: Iterable[str],
    registry: CounterRegistryV6 | None = None,
) -> EvidenceClosureV1:
    selected = _registry(registry)
    leaf = selected.by_path.get(path)
    if leaf is None:
        raise ConstructionAccountingEvidenceClosureV1Error(f"unknown path {path!r}")
    return apply_required_path_resolution_v1(
        closure,
        RequiredPathResolutionV1(
            closure.context.context_id,
            path,
            leaf.reducer,
            RequiredPathResolutionKindV1.POSITIVE_EVENT_STREAM,
            resolved_value,
            tuple(event_ids),
        ),
        registry=selected,
    )


def resolve_shared_resource_receipt_v1(
    closure: EvidenceClosureV1,
    *,
    path: str,
    resolved_value: int,
    receipt_id: str,
    registry: CounterRegistryV6 | None = None,
) -> EvidenceClosureV1:
    selected = _registry(registry)
    leaf = selected.by_path.get(path)
    if leaf is None:
        raise ConstructionAccountingEvidenceClosureV1Error(f"unknown path {path!r}")
    return apply_required_path_resolution_v1(
        closure,
        RequiredPathResolutionV1(
            closure.context.context_id,
            path,
            leaf.reducer,
            RequiredPathResolutionKindV1.SHARED_RESOURCE_RECEIPT,
            resolved_value,
            (receipt_id,),
        ),
        registry=selected,
    )


def resolve_profile_native_zero_v1(
    closure: EvidenceClosureV1,
    *,
    path: str,
    zero_attestation_id: str,
    registry: CounterRegistryV6 | None = None,
) -> EvidenceClosureV1:
    selected = _registry(registry)
    leaf = selected.by_path.get(path)
    if leaf is None:
        raise ConstructionAccountingEvidenceClosureV1Error(f"unknown path {path!r}")
    return apply_required_path_resolution_v1(
        closure,
        RequiredPathResolutionV1(
            closure.context.context_id,
            path,
            leaf.reducer,
            RequiredPathResolutionKindV1.PROFILE_NATIVE_ZERO,
            0,
            (zero_attestation_id,),
        ),
        registry=selected,
    )


def resolve_derived_reconciliation_v1(
    closure: EvidenceClosureV1,
    *,
    path: str,
    resolved_value: int,
    reconciliation_proof_id: str,
    formula_id: str,
    dependency_paths: Iterable[str],
    registry: CounterRegistryV6 | None = None,
) -> EvidenceClosureV1:
    selected = _registry(registry)
    leaf = selected.by_path.get(path)
    if leaf is None:
        raise ConstructionAccountingEvidenceClosureV1Error(f"unknown path {path!r}")
    return apply_required_path_resolution_v1(
        closure,
        RequiredPathResolutionV1(
            closure.context.context_id,
            path,
            leaf.reducer,
            RequiredPathResolutionKindV1.DERIVED_RECONCILIATION,
            resolved_value,
            (reconciliation_proof_id,),
            tuple(sorted(dependency_paths)),
            formula_id,
        ),
        registry=selected,
    )


def _validate_closure_shape(
    closure: EvidenceClosureV1,
    registry: CounterRegistryV6,
) -> None:
    stage_profile = official_stage_profile_v6(registry)
    if (
        closure.context.counter_registry_id != registry.registry_id
        or closure.context.stage_profile_id != stage_profile.stage_profile_id
    ):
        raise ConstructionAccountingEvidenceClosureV1Error(
            "closure context is not bound to the official V6 authorities"
        )
    if tuple(row.path for row in closure.resolutions) != registry.required_paths:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "closure must contain every required V6 path exactly once"
        )
    evidence_owner: dict[str, str] = {}
    for row in closure.resolutions:
        if row.context_id != closure.context.context_id:
            raise ConstructionAccountingEvidenceClosureV1Error(
                "closure contains a foreign resolution"
            )
        _validate_resolution_for_leaf(row, registry)
        for evidence_id in row.source_evidence_ids:
            previous = evidence_owner.setdefault(evidence_id, row.path)
            if previous != row.path:
                raise ConstructionAccountingEvidenceClosureV1Error(
                    "one source-evidence ID cannot resolve multiple paths: "
                    f"{previous!r}, {row.path!r}"
                )
        for dependency in row.dependency_paths:
            target = closure.by_path.get(dependency)
            if target is None:
                raise ConstructionAccountingEvidenceClosureV1Error(
                    f"derived dependency {dependency!r} is not a required path"
                )
            if target.resolution_kind is RequiredPathResolutionKindV1.UNRESOLVED:
                raise ConstructionAccountingEvidenceClosureV1Error(
                    f"derived dependency {dependency!r} remains unresolved"
                )

    # Direct dataclass construction must not bypass the immutable apply API by
    # installing a mutually supporting derived cycle.
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(path: str) -> None:
        if path in visited:
            return
        if path in visiting:
            raise ConstructionAccountingEvidenceClosureV1Error(
                "derived reconciliation dependencies contain a cycle"
            )
        visiting.add(path)
        for dependency in closure.by_path[path].dependency_paths:
            visit(dependency)
        visiting.remove(path)
        visited.add(path)

    for path in registry.required_paths:
        visit(path)


def verify_evidence_closure_coverage_v1(
    closure: EvidenceClosureV1,
    *,
    registry: CounterRegistryV6 | None = None,
) -> EvidenceClosureCoverageReplayV1:
    """Replay structural coverage without validating referenced semantics."""

    if type(closure) is not EvidenceClosureV1:
        raise ConstructionAccountingEvidenceClosureV1Error(
            "coverage verifier requires an exact closure artifact"
        )
    selected = _registry(registry)
    _validate_closure_shape(closure, selected)
    unresolved = closure.unresolved_paths
    counts = tuple(
        (
            kind.value,
            sum(row.resolution_kind is kind for row in closure.resolutions),
        )
        for kind in RequiredPathResolutionKindV1
    )
    return EvidenceClosureCoverageReplayV1._issue(
        context_id=closure.context.context_id,
        evidence_closure_id=closure.closure_id,
        counter_registry_id=selected.registry_id,
        coverage_state=(
            EvidenceClosureCoverageStateV1.INCOMPLETE
            if unresolved
            else EvidenceClosureCoverageStateV1.COMPLETE_UNVERIFIED
        ),
        required_path_count=len(selected.required_paths),
        resolved_path_count=len(selected.required_paths) - len(unresolved),
        unresolved_paths=unresolved,
        resolution_counts=counts,
    )


def require_complete_structural_coverage_v1(
    closure: EvidenceClosureV1,
    *,
    registry: CounterRegistryV6 | None = None,
) -> EvidenceClosureCoverageReplayV1:
    """Require full row coverage while explicitly withholding semantic authority."""

    result = verify_evidence_closure_coverage_v1(closure, registry=registry)
    if (
        result.coverage_state
        is not EvidenceClosureCoverageStateV1.COMPLETE_UNVERIFIED
    ):
        raise ConstructionAccountingEvidenceClosureV1Error(
            "required-path coverage is incomplete; no formal vector is authorized"
        )
    return result


__all__ = [
    "EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN",
    "EVIDENCE_CLOSURE_V1_DOMAIN",
    "EVIDENCE_CLOSURE_VERIFICATION_V1_DOMAIN",
    "EvidenceClosureCoverageReplayV1",
    "EvidenceClosureCoverageStateV1",
    "EvidenceClosureCompletenessV1",
    "EvidenceClosureContextV1",
    "EvidenceClosureV1",
    "EvidenceResolutionKindV1",
    "REQUIRED_PATH_RESOLUTION_V1_DOMAIN",
    "RequiredPathResolutionKindV1",
    "RequiredPathResolutionV1",
    "SCHEMA_VERSION",
    "SHARED_RESOURCE_PATHS_V1",
    "ConstructionAccountingEvidenceClosureV1Error",
    "apply_required_path_resolution_v1",
    "initialize_evidence_closure_v1",
    "resolve_derived_reconciliation_v1",
    "resolve_positive_event_stream_v1",
    "resolve_profile_native_zero_v1",
    "resolve_shared_resource_receipt_v1",
    "require_complete_structural_coverage_v1",
    "verify_evidence_closure_coverage_v1",
]
