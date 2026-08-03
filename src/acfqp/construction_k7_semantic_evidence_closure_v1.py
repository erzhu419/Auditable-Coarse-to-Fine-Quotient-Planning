"""Atomic semantic closure for all 202 required K7 accounting paths.

This is the final evidence layer before formal CounterRecord materialization.
It independently replays the complete production roots and then closes the
exact V6 partition:

* 9 exact shared-resource authorizations;
* 71 owner-path candidates, distinguishing positive streams from explicit
  completed-owner-window zeros;
* 114 profile-native-zero attestations; and
* 8 exact derived reconciliation proofs.

Owner-window zero and profile-native zero are intentionally different
resolution kinds.  No missing event is interpreted as zero.  Every path gets
one path-specific primary evidence ID and one path-specific recorder authority
ID, and neither identity may be reused by another path.  Derived formula and
closure dependencies are replayed as a DAG.  The result authorizes only the
next atomic materialization step; it creates no CounterRecord or vector.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_owner_event_candidates_v1 as owner_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_derived_reconciliation_v2 as derived_v2
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as occurrence_v2
from acfqp import construction_profile_native_zero_semantic_authority_v1 as zero_v1
from acfqp import construction_shared_resource_verified_envelope_v1 as verified_v1
from acfqp import v075_k7_broker_worker_entry_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_SEMANTIC_EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN,
    CONSTRUCTION_K7_SEMANTIC_EVIDENCE_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_SEMANTIC_PATH_RECORDER_AUTHORITY_V1_DOMAIN,
    CONSTRUCTION_K7_SEMANTIC_PATH_RESOLUTION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.28"
PROFILE_KEY = "construction_k7_semantic_evidence_closure_v1"
EXPECTED_REQUIRED_PATH_COUNT = 202
EXPECTED_SHARED_PATH_COUNT = 9
EXPECTED_OWNER_PATH_COUNT = 71
EXPECTED_PROFILE_ZERO_PATH_COUNT = 114
EXPECTED_DERIVED_PATH_COUNT = 8

PATH_RECORDER_AUTHORITY_DOMAIN = CONSTRUCTION_K7_SEMANTIC_PATH_RECORDER_AUTHORITY_V1_DOMAIN
PATH_RESOLUTION_DOMAIN = CONSTRUCTION_K7_SEMANTIC_PATH_RESOLUTION_V1_DOMAIN
SEMANTIC_CLOSURE_CONTEXT_DOMAIN = CONSTRUCTION_K7_SEMANTIC_EVIDENCE_CLOSURE_CONTEXT_V1_DOMAIN
SEMANTIC_CLOSURE_DOMAIN = CONSTRUCTION_K7_SEMANTIC_EVIDENCE_CLOSURE_V1_DOMAIN

LOCAL_DOMAINS = frozenset(
    {
        PATH_RECORDER_AUTHORITY_DOMAIN,
        PATH_RESOLUTION_DOMAIN,
        SEMANTIC_CLOSURE_CONTEXT_DOMAIN,
        SEMANTIC_CLOSURE_DOMAIN,
    }
)
if not LOCAL_DOMAINS.issubset(PHASE3E_DOMAIN_TAGS):  # pragma: no cover
    raise RuntimeError("K7 semantic-closure domains must be centrally registered")

_RESOLUTION_ISSUER = object()
_CONTEXT_ISSUER = object()
_CLOSURE_ISSUER = object()


class ConstructionK7SemanticEvidenceClosureV1Error(ValueError):
    """A 202-path evidence family was stale, crossed, missing, or duplicated."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7SemanticEvidenceClosureV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7SemanticEvidenceClosureV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in LOCAL_DOMAINS:
        _fail("semantic closure used an unknown local domain")
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


class SemanticResolutionKindV1(str, Enum):
    SHARED_RESOURCE_EXACT = "SHARED_RESOURCE_EXACT"
    OWNER_EVENT_STREAM = "OWNER_EVENT_STREAM"
    OWNER_WINDOW_ZERO = "OWNER_WINDOW_ZERO"
    PROFILE_NATIVE_ZERO = "PROFILE_NATIVE_ZERO"
    DERIVED_RECONCILIATION = "DERIVED_RECONCILIATION"


@dataclass(frozen=True, slots=True)
class K7SemanticPathResolutionV1:
    _issuer: InitVar[object]
    context_id: str
    path: str
    semantics_id: str
    owner: str
    unit: str
    lane: str
    scope: str
    reducer: str
    comparison_axis: str | None
    kind: SemanticResolutionKindV1
    value: int
    primary_evidence_id: str
    recorder_authority_id: str
    primitive_evidence_ids: tuple[str, ...]
    formula_id: str | None
    dependency_paths: tuple[str, ...]
    _resolution_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESOLUTION_ISSUER:
            _fail("semantic path resolution is caller-minted")
        for value, label in (
            (self.context_id, "semantic closure context"),
            (self.primary_evidence_id, "primary path evidence"),
            (self.recorder_authority_id, "path recorder authority"),
            *((value, "primitive path evidence") for value in self.primitive_evidence_ids),
        ):
            _cid(value, label)
        try:
            kind = SemanticResolutionKindV1(self.kind)
        except (TypeError, ValueError) as error:
            raise ConstructionK7SemanticEvidenceClosureV1Error(
                "semantic path resolution kind is invalid"
            ) from error
        object.__setattr__(self, "kind", kind)
        registry = registry_v6.official_counter_registry_v6()
        leaf = registry.by_path.get(self.path)
        if (
            leaf is None
            or not leaf.required
            or self.semantics_id != leaf.semantics_id
            or self.owner != leaf.owner
            or self.unit != leaf.unit
            or self.lane != leaf.lane.value
            or self.scope != leaf.scope
            or self.reducer != leaf.reducer.value
            or self.comparison_axis != leaf.comparison_axis
            or type(self.value) is not int
            or self.value < 0
            or type(self.primitive_evidence_ids) is not tuple
            or len(set(self.primitive_evidence_ids)) != len(self.primitive_evidence_ids)
            or type(self.dependency_paths) is not tuple
            or tuple(sorted(self.dependency_paths)) != self.dependency_paths
            or len(set(self.dependency_paths)) != len(self.dependency_paths)
            or self.path in self.dependency_paths
        ):
            _fail("semantic path resolution differs from its exact V6 leaf")
        if kind is SemanticResolutionKindV1.SHARED_RESOURCE_EXACT:
            if self.primitive_evidence_ids or self.formula_id is not None or self.dependency_paths:
                _fail("shared exact resolution contains foreign event/formula evidence")
        elif kind is SemanticResolutionKindV1.OWNER_EVENT_STREAM:
            if (
                self.reducer != "sum"
                or self.value <= 0
                or len(self.primitive_evidence_ids) != self.value
                or self.formula_id is not None
                or self.dependency_paths
            ):
                _fail("owner event stream is not one positive exact unit stream")
        elif kind is SemanticResolutionKindV1.OWNER_WINDOW_ZERO:
            if (
                self.value != 0
                or self.primitive_evidence_ids
                or self.formula_id is not None
                or self.dependency_paths
            ):
                _fail("owner-window zero contains events or formula evidence")
        elif kind is SemanticResolutionKindV1.PROFILE_NATIVE_ZERO:
            if (
                self.value != 0
                or self.primitive_evidence_ids
                or self.formula_id is not None
                or self.dependency_paths
            ):
                _fail("profile-native zero contains owner events or formula evidence")
        else:
            if self.formula_id is None or not self.dependency_paths or self.primitive_evidence_ids:
                _fail("derived reconciliation lacks formula/DAG evidence")
            _cid(self.formula_id, "derived formula")
        expected_recorder = _path_recorder_authority_id(
            context_id=self.context_id,
            path=self.path,
            kind=kind,
            primary_id=self.primary_evidence_id,
        )
        if self.recorder_authority_id != expected_recorder:
            _fail("path recorder authority crossed its path/evidence identity")
        object.__setattr__(
            self,
            "_resolution_id",
            _local_id(PATH_RESOLUTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_semantic_path_resolution.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane,
            "scope": self.scope,
            "reducer": self.reducer,
            "comparison_axis": self.comparison_axis,
            "resolution_kind": self.kind.value,
            "value": self.value,
            "observed": True,
            "primary_evidence_id": self.primary_evidence_id,
            "recorder_authority_id": self.recorder_authority_id,
            "primitive_evidence_ids": list(self.primitive_evidence_ids),
            "formula_id": self.formula_id,
            "dependency_paths": list(self.dependency_paths),
            "missing_event_inferred_zero": False,
            "counter_record_issued": False,
        }

    @property
    def resolution_id(self) -> str:
        if _local_id(PATH_RESOLUTION_DOMAIN, self._payload()) != self._resolution_id:
            _fail("semantic path resolution changed after issuance")
        return self._resolution_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantic_path_resolution_id": self.resolution_id}


@dataclass(frozen=True, slots=True)
class K7SemanticEvidenceClosureContextV1:
    _issuer: InitVar[object]
    counter_registry_id: str
    stage_profile_id: str
    boundary_profile_id: str
    execution_profile_id: str
    occurrence_authority_bundle_id: str
    occurrence_authority_id: str
    cutoff_authority_id: str
    verified_nine_envelope_id: str
    owner_candidate_set_id: str
    profile_native_zero_envelope_id: str
    derived_reconciliation_readiness_id: str
    production_runtime_envelope_id: str
    portable_request_replay_id: str
    source_snapshot_id: str
    scientific_occurrence_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    terminal_closure_observation_id: str
    _context_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _CONTEXT_ISSUER:
            _fail("semantic closure context is caller-minted")
        for name in (
            "counter_registry_id",
            "stage_profile_id",
            "boundary_profile_id",
            "execution_profile_id",
            "occurrence_authority_bundle_id",
            "occurrence_authority_id",
            "cutoff_authority_id",
            "verified_nine_envelope_id",
            "owner_candidate_set_id",
            "profile_native_zero_envelope_id",
            "derived_reconciliation_readiness_id",
            "production_runtime_envelope_id",
            "portable_request_replay_id",
            "source_snapshot_id",
            "scientific_occurrence_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "decision_point_id",
            "measurement_window_id",
            "terminal_closure_observation_id",
        ):
            _cid(getattr(self, name), name)
        object.__setattr__(
            self,
            "_context_id",
            _local_id(SEMANTIC_CLOSURE_CONTEXT_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_semantic_evidence_closure_context.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            **{
                name: getattr(self, name)
                for name in (
                    "counter_registry_id",
                    "stage_profile_id",
                    "boundary_profile_id",
                    "execution_profile_id",
                    "occurrence_authority_bundle_id",
                    "occurrence_authority_id",
                    "cutoff_authority_id",
                    "verified_nine_envelope_id",
                    "owner_candidate_set_id",
                    "profile_native_zero_envelope_id",
                    "derived_reconciliation_readiness_id",
                    "production_runtime_envelope_id",
                    "portable_request_replay_id",
                    "source_snapshot_id",
                    "scientific_occurrence_id",
                    "logical_occurrence_id",
                    "route_attempt_id",
                    "decision_point_id",
                    "measurement_window_id",
                    "terminal_closure_observation_id",
                )
            },
        }

    @property
    def context_id(self) -> str:
        if _local_id(SEMANTIC_CLOSURE_CONTEXT_DOMAIN, self._payload()) != self._context_id:
            _fail("semantic closure context changed after issuance")
        return self._context_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantic_evidence_closure_context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class K7SemanticEvidenceClosureV1:
    _issuer: InitVar[object]
    context: K7SemanticEvidenceClosureContextV1
    resolutions: tuple[K7SemanticPathResolutionV1, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CLOSURE_ISSUER
            or type(self.context) is not K7SemanticEvidenceClosureContextV1
            or type(self.resolutions) is not tuple
            or len(self.resolutions) != EXPECTED_REQUIRED_PATH_COUNT
            or tuple(row.path for row in self.resolutions)
            != tuple(sorted(row.path for row in self.resolutions))
            or len({row.path for row in self.resolutions}) != EXPECTED_REQUIRED_PATH_COUNT
            or any(row.context_id != self.context.context_id for row in self.resolutions)
        ):
            _fail("semantic evidence closure is caller-minted, missing, or duplicated")
        registry = registry_v6.official_counter_registry_v6()
        if tuple(row.path for row in self.resolutions) != registry.required_paths:
            _fail("semantic closure path set differs from exact V6 required paths")
        counts = CounterKind.counts(self.resolutions)
        if (
            counts[SemanticResolutionKindV1.SHARED_RESOURCE_EXACT] != EXPECTED_SHARED_PATH_COUNT
            or counts[SemanticResolutionKindV1.OWNER_EVENT_STREAM]
            + counts[SemanticResolutionKindV1.OWNER_WINDOW_ZERO]
            != EXPECTED_OWNER_PATH_COUNT
            or counts[SemanticResolutionKindV1.PROFILE_NATIVE_ZERO]
            != EXPECTED_PROFILE_ZERO_PATH_COUNT
            or counts[SemanticResolutionKindV1.DERIVED_RECONCILIATION]
            != EXPECTED_DERIVED_PATH_COUNT
        ):
            _fail("semantic closure does not preserve the exact 9+71+114+8 partition")
        primary = [row.primary_evidence_id for row in self.resolutions]
        recorder = [row.recorder_authority_id for row in self.resolutions]
        if (
            len(set(primary)) != len(primary)
            or len(set(recorder)) != len(recorder)
            or set(primary) & set(recorder)
        ):
            _fail("one evidence or recorder authority ID was reused across paths/roles")
        evidence_owner: dict[str, str] = {}
        for row in self.resolutions:
            for evidence_id in (row.primary_evidence_id, *row.primitive_evidence_ids):
                previous = evidence_owner.setdefault(evidence_id, row.path)
                if previous != row.path:
                    _fail("one evidence ID resolves multiple semantic paths")
        self._verify_dependency_dag()
        object.__setattr__(
            self,
            "_closure_id",
            _local_id(SEMANTIC_CLOSURE_DOMAIN, self._payload()),
        )

    @property
    def by_path(self) -> dict[str, K7SemanticPathResolutionV1]:
        return {row.path: row for row in self.resolutions}

    def _verify_dependency_dag(self) -> None:
        by_path = self.by_path
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(path: str) -> None:
            if path in visited:
                return
            if path in visiting:
                _fail("semantic closure derived dependency DAG contains a cycle")
            visiting.add(path)
            for dependency in by_path[path].dependency_paths:
                if dependency not in by_path:
                    _fail("semantic closure derived dependency is missing")
                visit(dependency)
            visiting.remove(path)
            visited.add(path)

        for path in by_path:
            visit(path)

    def _payload(self) -> dict[str, Any]:
        counts = CounterKind.counts(self.resolutions)
        return {
            "schema": "acfqp.construction_k7_semantic_evidence_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context": self.context.to_document(),
            "required_path_count": len(self.resolutions),
            "resolution_counts": [
                {"resolution_kind": kind.value, "count": counts[kind]}
                for kind in SemanticResolutionKindV1
            ],
            "resolutions": [row.to_document() for row in self.resolutions],
            "semantic_replay_complete": True,
            "every_path_resolved_exactly_once": True,
            "missing_event_inferred_zero": False,
            "owner_window_zero_distinct_from_profile_native_zero": True,
            "next_atomic_materialization_authorized": True,
            "counter_records_issued": False,
            "work_vector_issued": False,
            "comparison_vector_issued": False,
            "formal_vectors_issued": False,
            "official_execution_allowed": False,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "central_domain_registration_pending": False,
        }

    @property
    def closure_id(self) -> str:
        if _local_id(SEMANTIC_CLOSURE_DOMAIN, self._payload()) != self._closure_id:
            _fail("semantic evidence closure changed after issuance")
        return self._closure_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantic_evidence_closure_id": self.closure_id}


class CounterKind:
    """Tiny namespace kept out of the serialized contract."""

    @staticmethod
    def counts(
        rows: tuple[K7SemanticPathResolutionV1, ...],
    ) -> dict[SemanticResolutionKindV1, int]:
        result = {kind: 0 for kind in SemanticResolutionKindV1}
        for row in rows:
            result[row.kind] += 1
        return result


def _path_recorder_authority_id(
    *, context_id: str, path: str, kind: SemanticResolutionKindV1, primary_id: str
) -> str:
    return _local_id(
        PATH_RECORDER_AUTHORITY_DOMAIN,
        {
            "schema": "acfqp.construction_k7_semantic_path_recorder_authority.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": context_id,
            "path": path,
            "resolution_kind": kind.value,
            "primary_evidence_id": primary_id,
            "path_specific": True,
            "counter_record_issuance_deferred": True,
        },
    )


def _rederive_complete_reconciliation(
    *,
    verified_nine: verified_v1.K7VerifiedNineSharedResourceEnvelopeV1,
    occurrence_authority: occurrence_v2.K7OccurrenceCutoffSemanticAuthorityBundleV2,
    replay_roots: Mapping[str, Any],
) -> derived_v2.K7CompleteDerivedReconciliationReadinessV2:
    """Recompute all three semantic families and the exact eight proof DAG."""

    owner_result = replay_roots.get("owned_result")
    transcript = getattr(owner_result, "transcript", None)
    return derived_v2.derive_k7_complete_eight_path_reconciliation_v2(
        verified_nine=verified_nine,
        authority_bundle=occurrence_authority,
        route_replay_inputs=dict(replay_roots),
        owner_transcript=transcript,
    )


def _replay_roots(
    *,
    replay_roots: Any,
    occurrence_authority: Any,
    verified_nine: Any,
    owner_candidates: Any,
    profile_native_zeros: Any,
    derived_reconciliation: Any,
) -> tuple[Any, Any, Any, Any]:
    if (
        type(replay_roots) is not dict
        or tuple(sorted(replay_roots)) != derived_v2.ROUTE_AUTHORITY_REPLAY_INPUT_KEYS
        or type(occurrence_authority)
        is not occurrence_v2.K7OccurrenceCutoffSemanticAuthorityBundleV2
        or type(verified_nine) is not verified_v1.K7VerifiedNineSharedResourceEnvelopeV1
        or type(owner_candidates) is not owner_v1.OwnerEventCandidateSetV1
        or type(profile_native_zeros) is not zero_v1.K7ProfileNativeZeroEnvelopeV1
        or type(derived_reconciliation)
        is not derived_v2.K7CompleteDerivedReconciliationReadinessV2
    ):
        _fail("semantic closure requires exact complete replay roots and typed authorities")
    try:
        replayed_occurrence = (
            occurrence_v2.replay_k7_occurrence_cutoff_semantic_authorities_v2(
                occurrence_authority, **replay_roots
            )
        )
        replayed_verified = verified_v1.verify_k7_production_shared_resource_envelope_exact_v1(
            replay_roots["source_envelope"]
        )
        output = worker_v1.verify_v075_k7_broker_operational_output_bytes_v1(
            raw=replay_roots["operational_output_bytes"],
            expected_request_replay=replay_roots["request_replay"],
            expected_binding=replay_roots["runtime_envelope"].binding,
        )
        business_raw = canonical_json_bytes(output.to_document()["business_result"])
        replayed_owner = owner_v1.derive_v075_k7_owner_event_candidates_v1(
            role_manifest=replay_roots["role_manifest"],
            runtime_envelope=replay_roots["runtime_envelope"],
            business_bundle_raw=business_raw,
        )
        transport = replay_roots[
            "request_replay"
        ].request.profile.accounted_profile.transport_profile
        replayed_zero = zero_v1.replay_k7_profile_native_zero_semantic_authority_v1(
            profile_native_zeros,
            occurrence_cutoff_authority=occurrence_authority,
            owner_candidate_set=owner_candidates,
            verified_nine_envelope=verified_nine,
            runtime_envelope=replay_roots["runtime_envelope"],
            request_replay=replay_roots["request_replay"],
            role_manifest=replay_roots["role_manifest"],
            operational_output_bytes=replay_roots["operational_output_bytes"],
            source_archive_raw=transport._archive_bytes,  # noqa: SLF001
        )
        replayed_derived = derived_v2.replay_k7_complete_eight_path_reconciliation_v2(
            derived_reconciliation,
            verified_nine=verified_nine,
            authority_bundle=occurrence_authority,
            route_replay_inputs=dict(replay_roots),
            owner_transcript=replay_roots["owned_result"].transcript,
        )
    except Exception as error:
        raise ConstructionK7SemanticEvidenceClosureV1Error(
            "one semantic evidence family failed independent root replay"
        ) from error
    if (
        replayed_occurrence.to_document() != occurrence_authority.to_document()
        or replayed_verified.to_document() != verified_nine.to_document()
        or replayed_owner.to_document() != owner_candidates.to_document()
        or replayed_zero.to_document() != profile_native_zeros.to_document()
        or replayed_derived.to_document() != derived_reconciliation.to_document()
        or derived_reconciliation.to_document().get("all_eight_exact") is not True
        or derived_reconciliation.to_document().get("unresolved_paths") != []
        or len(derived_reconciliation.exact_values) != EXPECTED_DERIVED_PATH_COUNT
    ):
        _fail("one semantic evidence authority differs from exact independent replay")
    return replayed_occurrence, replayed_verified, replayed_owner, replayed_derived


def _issue(
    *,
    replay_roots: Any,
    occurrence_authority: Any,
    verified_nine: Any,
    owner_candidates: Any,
    profile_native_zeros: Any,
    derived_reconciliation: Any,
) -> K7SemanticEvidenceClosureV1:
    occurrence, verified, owners, derived = _replay_roots(
        replay_roots=replay_roots,
        occurrence_authority=occurrence_authority,
        verified_nine=verified_nine,
        owner_candidates=owner_candidates,
        profile_native_zeros=profile_native_zeros,
        derived_reconciliation=derived_reconciliation,
    )
    occurrence_row = occurrence.occurrence_authority
    cutoff = occurrence.cutoff_authority
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    source = verified.source_envelope
    if (
        profile_native_zeros.counter_registry_id != registry.registry_id
        or profile_native_zeros.stage_profile_id != stage.stage_profile_id
        or profile_native_zeros.occurrence_authority_id != occurrence_row.authority_id
        or profile_native_zeros.cutoff_authority_id != cutoff.authority_id
        or profile_native_zeros.verified_nine_envelope_id != verified.verified_envelope_id
        or profile_native_zeros.owner_candidate_set_id != owners.candidate_set_id
        or derived.route_dependency_v2.verified_nine_envelope_id
        != verified.verified_envelope_id
        or source.counter_registry_id != registry.registry_id
        or source.stage_profile_id != stage.stage_profile_id
    ):
        _fail("semantic evidence families crossed their exact occurrence context")
    context = K7SemanticEvidenceClosureContextV1(
        _CONTEXT_ISSUER,
        registry.registry_id,
        stage.stage_profile_id,
        occurrence_row.boundary_profile_id,
        occurrence_row.execution_profile_id,
        occurrence.bundle_id,
        occurrence_row.authority_id,
        cutoff.authority_id,
        verified.verified_envelope_id,
        owners.candidate_set_id,
        profile_native_zeros.envelope_id,
        derived.readiness_id,
        occurrence_row.production_runtime_envelope_id,
        occurrence_row.portable_request_replay_id,
        occurrence_row.source_snapshot_id,
        occurrence_row.scientific_occurrence_id,
        occurrence_row.logical_occurrence_id,
        occurrence_row.route_attempt_id,
        occurrence_row.decision_point_id,
        occurrence_row.measurement_window_id,
        occurrence_row.terminal_closure_observation_id,
    )

    shared = verified.by_path
    owner_by_path = {row.path: row for row in owners.path_candidates}
    zero_by_path = {row.path: row for row in profile_native_zeros.attestations}
    derived_by_path = derived.exact_proofs_by_path
    partitions = (set(shared), set(owner_by_path), set(zero_by_path), set(derived_by_path))
    union = set().union(*partitions)
    if (
        tuple(map(len, partitions))
        != (
            EXPECTED_SHARED_PATH_COUNT,
            EXPECTED_OWNER_PATH_COUNT,
            EXPECTED_PROFILE_ZERO_PATH_COUNT,
            EXPECTED_DERIVED_PATH_COUNT,
        )
        or sum(map(len, partitions)) != len(union)
        or union != set(registry.required_paths)
    ):
        _fail("semantic authority families do not form the exact disjoint 202-path set")

    rows: list[K7SemanticPathResolutionV1] = []
    for path in registry.required_paths:
        leaf = registry.by_path[path]
        primitive: tuple[str, ...] = ()
        formula_id: str | None = None
        dependencies: tuple[str, ...] = ()
        if path in shared:
            authority = shared[path]
            kind = SemanticResolutionKindV1.SHARED_RESOURCE_EXACT
            value = authority.exact_value
            primary = authority.authorization_id
        elif path in owner_by_path:
            candidate = owner_by_path[path]
            if candidate.value > 0:
                if candidate.evidence_kind != owner_v1.POSITIVE_KIND:
                    _fail("positive owner candidate lacks ordered-stream evidence")
                kind = SemanticResolutionKindV1.OWNER_EVENT_STREAM
                primitive = candidate.ordered_event_ids
            else:
                if candidate.evidence_kind != owner_v1.ZERO_KIND:
                    _fail("owner zero lacks completed owner-window zero evidence")
                kind = SemanticResolutionKindV1.OWNER_WINDOW_ZERO
            value = candidate.value
            primary = candidate.candidate_id
        elif path in zero_by_path:
            attestation = zero_by_path[path]
            kind = SemanticResolutionKindV1.PROFILE_NATIVE_ZERO
            value = attestation.value
            primary = attestation.attestation_id
        else:
            proof = derived_by_path[path]
            kind = SemanticResolutionKindV1.DERIVED_RECONCILIATION
            value = proof.value
            primary = proof.proof_id
            formula_id = proof.formula_id
            dependencies = proof.closure_dependency_paths
        recorder = _path_recorder_authority_id(
            context_id=context.context_id,
            path=path,
            kind=kind,
            primary_id=primary,
        )
        rows.append(
            K7SemanticPathResolutionV1(
                _RESOLUTION_ISSUER,
                context.context_id,
                path,
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.lane.value,
                leaf.scope,
                leaf.reducer.value,
                leaf.comparison_axis,
                kind,
                value,
                primary,
                recorder,
                primitive,
                formula_id,
                dependencies,
            )
        )
    return K7SemanticEvidenceClosureV1(
        _CLOSURE_ISSUER,
        context,
        tuple(rows),
    )


def issue_k7_semantic_evidence_closure_v1(**kwargs: Any) -> K7SemanticEvidenceClosureV1:
    """Independently replay and close the exact 202-path semantic partition."""

    return _issue(**kwargs)


def replay_k7_semantic_evidence_closure_v1(
    claimed: Any, **kwargs: Any
) -> K7SemanticEvidenceClosureV1:
    if type(claimed) is not K7SemanticEvidenceClosureV1:
        _fail("semantic closure replay requires one exact typed closure")
    expected = _issue(**kwargs)
    if claimed.closure_id != expected.closure_id or claimed.to_document() != expected.to_document():
        _fail("semantic evidence closure differs from independent replay")
    return expected


def verify_k7_semantic_evidence_closure_bytes_v1(
    *, raw: bytes, **kwargs: Any
) -> K7SemanticEvidenceClosureV1:
    if type(raw) is not bytes or not raw:
        _fail("semantic evidence closure bytes are missing")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7SemanticEvidenceClosureV1Error(
            "semantic evidence closure bytes are noncanonical"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail("semantic evidence closure bytes are noncanonical")
    claimed_id = document.get("semantic_evidence_closure_id")
    payload = dict(document)
    payload.pop("semantic_evidence_closure_id", None)
    if type(claimed_id) is not str or _local_id(SEMANTIC_CLOSURE_DOMAIN, payload) != claimed_id:
        _fail("semantic evidence closure content identity changed")
    expected = _issue(**kwargs)
    if document != expected.to_document():
        _fail("semantic evidence closure bytes differ from independent replay")
    return expected


__all__ = (
    "ConstructionK7SemanticEvidenceClosureV1Error",
    "K7SemanticEvidenceClosureContextV1",
    "K7SemanticEvidenceClosureV1",
    "K7SemanticPathResolutionV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SemanticResolutionKindV1",
    "issue_k7_semantic_evidence_closure_v1",
    "replay_k7_semantic_evidence_closure_v1",
    "verify_k7_semantic_evidence_closure_bytes_v1",
)
