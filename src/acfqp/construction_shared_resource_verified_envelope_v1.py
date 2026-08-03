"""Exact nine-path replay authorization for one K7 shared-resource envelope.

The V3 live envelope joins nine honest source-local closures but deliberately
does not interpret their values.  This successor invokes the fixed V2 semantic
authority once for every bound source, freezes one content-addressed exact
authorization per path, and joins those authorizations under the original V3
runtime identity.

This is the last boundary before CounterRecord materialization.  It explicitly
authorizes that *next* step, but it neither creates a CounterRecord nor grants a
WorkVector/ComparisonVector claim.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_shared_resource_live_envelope_v3 as live_v3
from acfqp import construction_shared_resource_resolution_v2 as resolution_v2
from acfqp import construction_shared_resource_semantic_replay_v2 as replay_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_SHARED_RESOURCE_PATH_EXACT_AUTHORIZATION_V1_DOMAIN,
    V075_K7_VERIFIED_NINE_SHARED_RESOURCE_ENVELOPE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.22"
PROFILE_KEY = "construction_shared_resource_verified_envelope_v1"

PATH_EXACT_AUTHORIZATION_V1_DOMAIN = (
    CONSTRUCTION_SHARED_RESOURCE_PATH_EXACT_AUTHORIZATION_V1_DOMAIN
)
VERIFIED_NINE_ENVELOPE_V1_DOMAIN = (
    V075_K7_VERIFIED_NINE_SHARED_RESOURCE_ENVELOPE_V1_DOMAIN
)
REQUESTED_PHASE3E_DOMAIN_TAGS = (
    PATH_EXACT_AUTHORIZATION_V1_DOMAIN,
    VERIFIED_NINE_ENVELOPE_V1_DOMAIN,
)

_PATH_ISSUER = object()
_ENVELOPE_ISSUER = object()


class ConstructionSharedResourceVerifiedEnvelopeV1Error(ValueError):
    """The exact replay result crossed its V3 source or runtime identity."""


def _fail(message: str) -> NoReturn:
    raise ConstructionSharedResourceVerifiedEnvelopeV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceVerifiedEnvelopeV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        _fail(f"{label} must be one nonnegative exact integer")
    return value


def _semantic_document_digest(
    result: replay_v2.SharedResourceSemanticReplayResultV2,
) -> str:
    return hashlib.sha256(
        canonical_json_bytes(result.to_internal_document())
    ).hexdigest()


def _path_payload(
    *,
    source_envelope_id: str,
    production_runtime_envelope_id: str,
    counter_registry_id: str,
    stage_profile_id: str,
    occurrence_id: str,
    route_attempt_id: str,
    decision_point_id: str,
    measurement_window_id: str,
    production_runtime_replay_id: str,
    terminal_closure_observation_id: str,
    bound_source_id: str,
    source: resolution_v2.SharedResourceLiveSourceV2,
    result: replay_v2.SharedResourceSemanticReplayResultV2,
    semantic_replay_document_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.construction_shared_resource_path_exact_authorization.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "source_v3_envelope_id": source_envelope_id,
        "production_runtime_envelope_id": production_runtime_envelope_id,
        "counter_registry_id": counter_registry_id,
        "stage_profile_id": stage_profile_id,
        "occurrence_id": occurrence_id,
        "route_attempt_id": route_attempt_id,
        "decision_point_id": decision_point_id,
        "measurement_window_id": measurement_window_id,
        "production_runtime_replay_id": production_runtime_replay_id,
        "terminal_closure_observation_id": terminal_closure_observation_id,
        "bound_source_id": bound_source_id,
        "path": source.path,
        "exact_value": result.exact_value,
        "reducer": result.reducer.value,
        "semantic_verifier_key": result.semantic_verifier_key,
        "semantic_verifier_id": result.semantic_verifier_id,
        "semantic_replay_document_sha256": semantic_replay_document_sha256,
        "source_operational_cutoff_id": source.operational_cutoff_id,
        "source_local_start_sequence": source.covered_start_sequence,
        "source_local_cutoff_sequence": source.covered_cutoff_sequence,
        "source_component_keys": list(result.component_keys),
        "source_artifact_ids": list(result.source_artifact_ids),
        "source_bytes_sha256": list(result.source_bytes_sha256),
        "source_local_interval_preserved": True,
        "semantic_source_verified": True,
        "counter_record_materialization_eligible": True,
        "counter_record_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "formal_vector_authorized": False,
    }


@dataclass(frozen=True, slots=True)
class K7ValidatedSharedResourcePathSnapshotV1:
    """Immutable non-artifact facts from one exact path validation."""

    authorization_id: str
    source_v3_envelope_id: str
    production_runtime_envelope_id: str
    counter_registry_id: str
    stage_profile_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    production_runtime_replay_id: str
    terminal_closure_observation_id: str
    bound_source_id: str
    path: str
    exact_value: int
    reducer: str
    semantic_verifier_key: str
    semantic_verifier_id: str
    semantic_replay_document_sha256: str
    source_operational_cutoff_id: str
    source_local_start_sequence: int
    source_local_cutoff_sequence: int
    source_component_canonical_bytes: tuple[bytes, ...]
    source_artifact_ids: tuple[str, ...]
    source_bytes_sha256: tuple[str, ...]
    canonical_document_bytes: bytes


@dataclass(frozen=True, slots=True)
class K7VerifiedNineSharedResourceTransactionSnapshotV1:
    """Bounded pair replay containing only immutable primitive facts."""

    source_v3_envelope_id: str
    expected_verified_envelope_id: str
    supplied_verified_envelope_id: str
    expected_authorizations: tuple[K7ValidatedSharedResourcePathSnapshotV1, ...]
    supplied_authorizations: tuple[K7ValidatedSharedResourcePathSnapshotV1, ...]
    expected_canonical_document_bytes: bytes
    supplied_canonical_document_bytes: bytes


@dataclass(frozen=True, slots=True)
class _PathAuthorizationValidationInputV1:
    authorization_id: str
    source_v3_envelope_id: str
    production_runtime_envelope_id: str
    counter_registry_id: str
    stage_profile_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    production_runtime_replay_id: str
    terminal_closure_observation_id: str
    bound_source_id: str
    path: str
    exact_value: int
    reducer: Any
    semantic_verifier_key: str
    semantic_verifier_id: str
    semantic_replay_document_sha256: str
    source_operational_cutoff_id: str
    source_local_start_sequence: int
    source_local_cutoff_sequence: int
    bound_source: live_v3.BoundSharedResourceSourceV3 = field(repr=False)
    semantic_replay_result: replay_v2.SharedResourceSemanticReplayResultV2 = field(
        repr=False
    )


def _path_payload_from_validation_input_v1(
    values: _PathAuthorizationValidationInputV1,
) -> dict[str, Any]:
    return _path_payload(
        source_envelope_id=values.source_v3_envelope_id,
        production_runtime_envelope_id=values.production_runtime_envelope_id,
        counter_registry_id=values.counter_registry_id,
        stage_profile_id=values.stage_profile_id,
        occurrence_id=values.occurrence_id,
        route_attempt_id=values.route_attempt_id,
        decision_point_id=values.decision_point_id,
        measurement_window_id=values.measurement_window_id,
        production_runtime_replay_id=values.production_runtime_replay_id,
        terminal_closure_observation_id=values.terminal_closure_observation_id,
        bound_source_id=values.bound_source_id,
        source=values.bound_source.source,
        result=values.semantic_replay_result,
        semantic_replay_document_sha256=(
            values.semantic_replay_document_sha256
        ),
    )


def _validate_path_authorization_values_once_v1(
    values: _PathAuthorizationValidationInputV1,
) -> K7ValidatedSharedResourcePathSnapshotV1:
    """Strictly validate one row and freeze only immutable replay facts."""

    for value, label in (
        (values.authorization_id, "path authorization"),
        (values.source_v3_envelope_id, "source V3 envelope"),
        (values.production_runtime_envelope_id, "production runtime envelope"),
        (values.counter_registry_id, "counter registry"),
        (values.stage_profile_id, "stage profile"),
        (values.occurrence_id, "occurrence"),
        (values.route_attempt_id, "route attempt"),
        (values.decision_point_id, "decision point"),
        (values.measurement_window_id, "measurement window"),
        (values.production_runtime_replay_id, "production runtime replay"),
        (
            values.terminal_closure_observation_id,
            "terminal closure observation",
        ),
        (values.bound_source_id, "bound source"),
        (values.semantic_verifier_id, "semantic verifier"),
        (values.source_operational_cutoff_id, "source operational cutoff"),
    ):
        _cid(value, label)
    _nonnegative(values.exact_value, "exact shared-resource value")
    _nonnegative(values.source_local_start_sequence, "source local start")
    _nonnegative(values.source_local_cutoff_sequence, "source local cutoff")
    if values.source_local_cutoff_sequence < values.source_local_start_sequence:
        _fail("source local cutoff precedes its start")
    try:
        reducer = ReducerEnum(values.reducer)
    except (TypeError, ValueError) as error:
        raise ConstructionSharedResourceVerifiedEnvelopeV1Error(
            "path authorization reducer is invalid"
        ) from error
    if (
        type(values.bound_source) is not live_v3.BoundSharedResourceSourceV3
        or type(values.semantic_replay_result)
        is not replay_v2.SharedResourceSemanticReplayResultV2
    ):
        _fail("path authorization contains a foreign source or replay result")
    source = values.bound_source.source
    result = values.semantic_replay_result
    if (
        values.bound_source.bound_source_id != values.bound_source_id
        or source.path != values.path
        or source.live_envelope_id != values.production_runtime_envelope_id
        or source.occurrence_id != values.occurrence_id
        or source.route_attempt_id != values.route_attempt_id
        or source.decision_point_id != values.decision_point_id
        or source.measurement_window_id != values.measurement_window_id
        or source.operational_cutoff_id != values.source_operational_cutoff_id
        or source.covered_start_sequence != values.source_local_start_sequence
        or source.covered_cutoff_sequence != values.source_local_cutoff_sequence
        or result.path != values.path
        or result.exact_value != values.exact_value
        or result.reducer is not reducer
        or result.semantic_verifier_key != values.semantic_verifier_key
        or result.semantic_verifier_id != values.semantic_verifier_id
        or result.live_envelope_id != values.production_runtime_envelope_id
        or result.occurrence_id != values.occurrence_id
        or result.route_attempt_id != values.route_attempt_id
        or result.decision_point_id != values.decision_point_id
        or result.measurement_window_id != values.measurement_window_id
        or result.operational_cutoff_id != values.source_operational_cutoff_id
        or result.covered_start_sequence != values.source_local_start_sequence
        or result.covered_cutoff_sequence != values.source_local_cutoff_sequence
        or result.semantic_source_verified is not True
        or result.counter_record_issuance_authorized is not False
        or _semantic_document_digest(result)
        != values.semantic_replay_document_sha256
    ):
        _fail("path authorization was mutated or transplanted")
    digest = values.semantic_replay_document_sha256
    if (
        type(digest) is not str
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        _fail("semantic replay document digest is invalid")
    payload = _path_payload_from_validation_input_v1(values)
    expected = content_id(PATH_EXACT_AUTHORIZATION_V1_DOMAIN, payload)
    if expected != values.authorization_id:
        _fail("path authorization content identity was mutated or transplanted")
    return K7ValidatedSharedResourcePathSnapshotV1(
        authorization_id=values.authorization_id,
        source_v3_envelope_id=values.source_v3_envelope_id,
        production_runtime_envelope_id=values.production_runtime_envelope_id,
        counter_registry_id=values.counter_registry_id,
        stage_profile_id=values.stage_profile_id,
        occurrence_id=values.occurrence_id,
        route_attempt_id=values.route_attempt_id,
        decision_point_id=values.decision_point_id,
        measurement_window_id=values.measurement_window_id,
        production_runtime_replay_id=values.production_runtime_replay_id,
        terminal_closure_observation_id=(
            values.terminal_closure_observation_id
        ),
        bound_source_id=values.bound_source_id,
        path=values.path,
        exact_value=values.exact_value,
        reducer=reducer.value,
        semantic_verifier_key=values.semantic_verifier_key,
        semantic_verifier_id=values.semantic_verifier_id,
        semantic_replay_document_sha256=digest,
        source_operational_cutoff_id=values.source_operational_cutoff_id,
        source_local_start_sequence=values.source_local_start_sequence,
        source_local_cutoff_sequence=values.source_local_cutoff_sequence,
        source_component_canonical_bytes=tuple(
            canonical_json_bytes(component.to_internal_document())
            for component in source.components
        ),
        source_artifact_ids=result.source_artifact_ids,
        source_bytes_sha256=result.source_bytes_sha256,
        canonical_document_bytes=canonical_json_bytes(
            {**payload, "path_exact_authorization_id": values.authorization_id}
        ),
    )


@dataclass(frozen=True, slots=True)
class VerifiedSharedResourcePathAuthorizationV1:
    """Issuer-owned exact value and materialization authority for one path."""

    _issuer: InitVar[object]
    authorization_id: str
    source_v3_envelope_id: str
    production_runtime_envelope_id: str
    counter_registry_id: str
    stage_profile_id: str
    occurrence_id: str
    route_attempt_id: str
    decision_point_id: str
    measurement_window_id: str
    production_runtime_replay_id: str
    terminal_closure_observation_id: str
    bound_source_id: str
    path: str
    exact_value: int
    reducer: ReducerEnum
    semantic_verifier_key: str
    semantic_verifier_id: str
    semantic_replay_document_sha256: str
    source_operational_cutoff_id: str
    source_local_start_sequence: int
    source_local_cutoff_sequence: int
    bound_source: live_v3.BoundSharedResourceSourceV3 = field(
        repr=False, compare=False
    )
    semantic_replay_result: replay_v2.SharedResourceSemanticReplayResultV2 = field(
        repr=False, compare=False
    )

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PATH_ISSUER:
            _fail("path exact authorization is caller-minted")
        try:
            reducer = ReducerEnum(self.reducer)
        except (TypeError, ValueError) as error:
            raise ConstructionSharedResourceVerifiedEnvelopeV1Error(
                "path authorization reducer is invalid"
            ) from error
        object.__setattr__(self, "reducer", reducer)
        _validate_path_authorization_values_once_v1(
            _path_authorization_validation_input_v1(self)
        )

    def _payload(self) -> dict[str, Any]:
        return _path_payload_from_validation_input_v1(
            _path_authorization_validation_input_v1(self)
        )

    def _assert_current(self) -> None:
        self.__post_init__(_PATH_ISSUER)

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {**self._payload(), "path_exact_authorization_id": self.authorization_id}


def _path_authorization_validation_input_v1(
    row: VerifiedSharedResourcePathAuthorizationV1,
) -> _PathAuthorizationValidationInputV1:
    return _PathAuthorizationValidationInputV1(
        authorization_id=row.authorization_id,
        source_v3_envelope_id=row.source_v3_envelope_id,
        production_runtime_envelope_id=row.production_runtime_envelope_id,
        counter_registry_id=row.counter_registry_id,
        stage_profile_id=row.stage_profile_id,
        occurrence_id=row.occurrence_id,
        route_attempt_id=row.route_attempt_id,
        decision_point_id=row.decision_point_id,
        measurement_window_id=row.measurement_window_id,
        production_runtime_replay_id=row.production_runtime_replay_id,
        terminal_closure_observation_id=row.terminal_closure_observation_id,
        bound_source_id=row.bound_source_id,
        path=row.path,
        exact_value=row.exact_value,
        reducer=row.reducer,
        semantic_verifier_key=row.semantic_verifier_key,
        semantic_verifier_id=row.semantic_verifier_id,
        semantic_replay_document_sha256=row.semantic_replay_document_sha256,
        source_operational_cutoff_id=row.source_operational_cutoff_id,
        source_local_start_sequence=row.source_local_start_sequence,
        source_local_cutoff_sequence=row.source_local_cutoff_sequence,
        bound_source=row.bound_source,
        semantic_replay_result=row.semantic_replay_result,
    )


def _freeze_path_authorization(
    *,
    envelope: live_v3.K7ProductionSharedResourceEnvelopeV3,
    source_envelope_id: str,
    bound_source: live_v3.BoundSharedResourceSourceV3,
    result: replay_v2.SharedResourceSemanticReplayResultV2,
) -> VerifiedSharedResourcePathAuthorizationV1:
    source = bound_source.source
    digest = _semantic_document_digest(result)
    payload = _path_payload(
        source_envelope_id=source_envelope_id,
        production_runtime_envelope_id=envelope.production_runtime_envelope_id,
        counter_registry_id=envelope.counter_registry_id,
        stage_profile_id=envelope.stage_profile_id,
        occurrence_id=envelope.occurrence_id,
        route_attempt_id=envelope.route_attempt_id,
        decision_point_id=envelope.decision_point_id,
        measurement_window_id=envelope.measurement_window_id,
        production_runtime_replay_id=envelope.production_runtime_replay_id,
        terminal_closure_observation_id=(
            envelope.terminal_closure_observation_id
        ),
        bound_source_id=bound_source.bound_source_id,
        source=source,
        result=result,
        semantic_replay_document_sha256=digest,
    )
    return VerifiedSharedResourcePathAuthorizationV1(
        _PATH_ISSUER,
        content_id(PATH_EXACT_AUTHORIZATION_V1_DOMAIN, payload),
        source_envelope_id,
        envelope.production_runtime_envelope_id,
        envelope.counter_registry_id,
        envelope.stage_profile_id,
        envelope.occurrence_id,
        envelope.route_attempt_id,
        envelope.decision_point_id,
        envelope.measurement_window_id,
        envelope.production_runtime_replay_id,
        envelope.terminal_closure_observation_id,
        bound_source.bound_source_id,
        source.path,
        result.exact_value,
        result.reducer,
        result.semantic_verifier_key,
        result.semantic_verifier_id,
        digest,
        source.operational_cutoff_id,
        source.covered_start_sequence,
        source.covered_cutoff_sequence,
        bound_source,
        result,
    )


def _envelope_payload(
    *,
    source_envelope: live_v3.K7ProductionSharedResourceEnvelopeV3,
    source_envelope_id: str,
    authorizations: tuple[Any, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v075_k7_verified_nine_shared_resource_envelope.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "source_v3_envelope_id": source_envelope_id,
        "production_runtime_envelope_id": (
            source_envelope.production_runtime_envelope_id
        ),
        "counter_registry_id": source_envelope.counter_registry_id,
        "stage_profile_id": source_envelope.stage_profile_id,
        "occurrence_id": source_envelope.occurrence_id,
        "route_attempt_id": source_envelope.route_attempt_id,
        "decision_point_id": source_envelope.decision_point_id,
        "measurement_window_id": source_envelope.measurement_window_id,
        "production_runtime_replay_id": (
            source_envelope.production_runtime_replay_id
        ),
        "terminal_closure_observation_id": (
            source_envelope.terminal_closure_observation_id
        ),
        "source_paths": [row.path for row in authorizations],
        "path_exact_authorization_ids": [
            row.authorization_id for row in authorizations
        ],
        "exact_values": [
            {
                "path": row.path,
                "value": row.exact_value,
                "reducer": (
                    row.reducer.value
                    if type(row.reducer) is ReducerEnum
                    else row.reducer
                ),
            }
            for row in authorizations
        ],
        "source_local_windows": [
            {
                "path": row.path,
                "source_operational_cutoff_id": row.source_operational_cutoff_id,
                "source_local_start_sequence": row.source_local_start_sequence,
                "source_local_cutoff_sequence": row.source_local_cutoff_sequence,
            }
            for row in authorizations
        ],
        "fixed_semantic_replay_complete": True,
        "ordered_exact_nine_path_set": True,
        "source_local_intervals_preserved": True,
        "identical_local_event_counts_required": False,
        "counter_record_materialization_eligible": True,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "formal_vector_authorized": False,
    }


@dataclass(frozen=True, slots=True)
class _ValidatedNineEnvelopePrimitiveV1:
    verified_envelope_id: str
    source_v3_envelope_id: str
    authorization_snapshots: tuple[
        K7ValidatedSharedResourcePathSnapshotV1, ...
    ]
    canonical_document_bytes: bytes


def _validate_verified_nine_envelope_once_v1(
    envelope: Any,
    *,
    authorization_snapshots: tuple[
        K7ValidatedSharedResourcePathSnapshotV1, ...
    ]
    | None = None,
) -> _ValidatedNineEnvelopePrimitiveV1:
    """Validate one envelope; prevalidated row snapshots avoid a second pass."""

    if type(envelope) is not K7VerifiedNineSharedResourceEnvelopeV1:
        _fail("verified envelope contains a foreign V3 source envelope")
    _cid(envelope.verified_envelope_id, "verified nine-path envelope")
    _cid(envelope.source_v3_envelope_id, "source V3 envelope")
    if type(envelope.source_envelope) is not live_v3.K7ProductionSharedResourceEnvelopeV3:
        _fail("verified envelope contains a foreign V3 source envelope")
    if envelope.source_envelope.envelope_id != envelope.source_v3_envelope_id:
        _fail("source V3 envelope was mutated or transplanted")
    if (
        type(envelope.authorizations) is not tuple
        or any(
            type(row) is not VerifiedSharedResourcePathAuthorizationV1
            for row in envelope.authorizations
        )
        or tuple(row.path for row in envelope.authorizations)
        != resolution_v2.SHARED_RESOURCE_PATHS
        or len({row.authorization_id for row in envelope.authorizations})
        != len(resolution_v2.SHARED_RESOURCE_PATHS)
        or tuple(row.bound_source_id for row in envelope.authorizations)
        != tuple(
            row.bound_source_id for row in envelope.source_envelope.bound_sources
        )
    ):
        _fail("verified envelope lacks the exact ordered distinct nine-path set")
    if authorization_snapshots is None:
        validated = tuple(
            _validate_path_authorization_values_once_v1(
                _path_authorization_validation_input_v1(row)
            )
            for row in envelope.authorizations
        )
    else:
        if (
            type(authorization_snapshots) is not tuple
            or len(authorization_snapshots) != len(envelope.authorizations)
            or any(
                type(row) is not K7ValidatedSharedResourcePathSnapshotV1
                for row in authorization_snapshots
            )
            or tuple(
                (row.path, row.authorization_id, row.bound_source_id)
                for row in envelope.authorizations
            )
            != tuple(
                (row.path, row.authorization_id, row.bound_source_id)
                for row in authorization_snapshots
            )
        ):
            _fail("prevalidated path snapshots differ from the verified envelope")
        validated = authorization_snapshots
    context = (
        envelope.source_v3_envelope_id,
        envelope.source_envelope.production_runtime_envelope_id,
        envelope.source_envelope.counter_registry_id,
        envelope.source_envelope.stage_profile_id,
        envelope.source_envelope.occurrence_id,
        envelope.source_envelope.route_attempt_id,
        envelope.source_envelope.decision_point_id,
        envelope.source_envelope.measurement_window_id,
        envelope.source_envelope.production_runtime_replay_id,
        envelope.source_envelope.terminal_closure_observation_id,
    )
    for row in validated:
        if (
            row.source_v3_envelope_id,
            row.production_runtime_envelope_id,
            row.counter_registry_id,
            row.stage_profile_id,
            row.occurrence_id,
            row.route_attempt_id,
            row.decision_point_id,
            row.measurement_window_id,
            row.production_runtime_replay_id,
            row.terminal_closure_observation_id,
        ) != context:
            _fail("one exact authorization was transplanted across context")
    payload = _envelope_payload(
        source_envelope=envelope.source_envelope,
        source_envelope_id=envelope.source_v3_envelope_id,
        authorizations=validated,
    )
    expected = content_id(VERIFIED_NINE_ENVELOPE_V1_DOMAIN, payload)
    if expected != envelope.verified_envelope_id:
        _fail("verified nine-path envelope content identity was mutated")
    return _ValidatedNineEnvelopePrimitiveV1(
        verified_envelope_id=envelope.verified_envelope_id,
        source_v3_envelope_id=envelope.source_v3_envelope_id,
        authorization_snapshots=validated,
        canonical_document_bytes=canonical_json_bytes(
            {
                **payload,
                "verified_nine_shared_resource_envelope_id": (
                    envelope.verified_envelope_id
                ),
            }
        ),
    )


@dataclass(frozen=True, slots=True)
class K7VerifiedNineSharedResourceEnvelopeV1:
    """Ordered exact replay closure for all nine shared-resource paths."""

    _issuer: InitVar[object]
    verified_envelope_id: str
    source_v3_envelope_id: str
    source_envelope: live_v3.K7ProductionSharedResourceEnvelopeV3 = field(
        repr=False, compare=False
    )
    authorizations: tuple[VerifiedSharedResourcePathAuthorizationV1, ...] = field(
        repr=False
    )

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ENVELOPE_ISSUER:
            _fail("verified nine-path envelope is caller-minted")
        _validate_verified_nine_envelope_once_v1(self)

    def _payload(self) -> dict[str, Any]:
        return _envelope_payload(
            source_envelope=self.source_envelope,
            source_envelope_id=self.source_v3_envelope_id,
            authorizations=self.authorizations,
        )

    def _assert_current(self) -> None:
        self.__post_init__(_ENVELOPE_ISSUER)

    @property
    def by_path(self) -> dict[str, VerifiedSharedResourcePathAuthorizationV1]:
        self._assert_current()
        return {row.path: row for row in self.authorizations}

    def to_document(self) -> dict[str, Any]:
        self._assert_current()
        return {
            **self._payload(),
            "verified_nine_shared_resource_envelope_id": self.verified_envelope_id,
        }


def verify_k7_production_shared_resource_envelope_exact_v1(
    envelope: Any,
) -> K7VerifiedNineSharedResourceEnvelopeV1:
    """Replay all nine V3-bound sources through the fixed semantic catalogue."""

    if type(envelope) is not live_v3.K7ProductionSharedResourceEnvelopeV3:
        _fail("exact nine-path replay requires one exact V3 source envelope")
    source_envelope_id = envelope.envelope_id
    if tuple(row.source.path for row in envelope.bound_sources) != (
        resolution_v2.SHARED_RESOURCE_PATHS
    ):
        _fail("V3 source envelope is not the fixed ordered nine-path set")
    authorizations = []
    for bound_source in envelope.bound_sources:
        try:
            result = replay_v2.verify_shared_resource_source_exact_v2(
                bound_source.source
            )
        except replay_v2.ConstructionSharedResourceSemanticReplayV2Error as error:
            raise ConstructionSharedResourceVerifiedEnvelopeV1Error(
                f"{bound_source.source.path} exact semantic replay failed"
            ) from error
        authorizations.append(
            _freeze_path_authorization(
                envelope=envelope,
                source_envelope_id=source_envelope_id,
                bound_source=bound_source,
                result=result,
            )
        )
    ordered = tuple(authorizations)
    payload = _envelope_payload(
        source_envelope=envelope,
        source_envelope_id=source_envelope_id,
        authorizations=ordered,
    )
    return K7VerifiedNineSharedResourceEnvelopeV1(
        _ENVELOPE_ISSUER,
        content_id(VERIFIED_NINE_ENVELOPE_V1_DOMAIN, payload),
        source_envelope_id,
        envelope,
        ordered,
    )


def _replay_expected_path_snapshot_once_v1(
    *,
    envelope: live_v3.K7ProductionSharedResourceEnvelopeV3,
    source_envelope_id: str,
    bound_source: live_v3.BoundSharedResourceSourceV3,
) -> K7ValidatedSharedResourcePathSnapshotV1:
    try:
        result = replay_v2.verify_shared_resource_source_exact_v2(
            bound_source.source
        )
    except replay_v2.ConstructionSharedResourceSemanticReplayV2Error as error:
        raise ConstructionSharedResourceVerifiedEnvelopeV1Error(
            f"{bound_source.source.path} exact semantic replay failed"
        ) from error
    source = bound_source.source
    digest = _semantic_document_digest(result)
    payload = _path_payload(
        source_envelope_id=source_envelope_id,
        production_runtime_envelope_id=envelope.production_runtime_envelope_id,
        counter_registry_id=envelope.counter_registry_id,
        stage_profile_id=envelope.stage_profile_id,
        occurrence_id=envelope.occurrence_id,
        route_attempt_id=envelope.route_attempt_id,
        decision_point_id=envelope.decision_point_id,
        measurement_window_id=envelope.measurement_window_id,
        production_runtime_replay_id=envelope.production_runtime_replay_id,
        terminal_closure_observation_id=(
            envelope.terminal_closure_observation_id
        ),
        bound_source_id=bound_source.bound_source_id,
        source=source,
        result=result,
        semantic_replay_document_sha256=digest,
    )
    return _validate_path_authorization_values_once_v1(
        _PathAuthorizationValidationInputV1(
            authorization_id=content_id(
                PATH_EXACT_AUTHORIZATION_V1_DOMAIN, payload
            ),
            source_v3_envelope_id=source_envelope_id,
            production_runtime_envelope_id=(
                envelope.production_runtime_envelope_id
            ),
            counter_registry_id=envelope.counter_registry_id,
            stage_profile_id=envelope.stage_profile_id,
            occurrence_id=envelope.occurrence_id,
            route_attempt_id=envelope.route_attempt_id,
            decision_point_id=envelope.decision_point_id,
            measurement_window_id=envelope.measurement_window_id,
            production_runtime_replay_id=envelope.production_runtime_replay_id,
            terminal_closure_observation_id=(
                envelope.terminal_closure_observation_id
            ),
            bound_source_id=bound_source.bound_source_id,
            path=source.path,
            exact_value=result.exact_value,
            reducer=result.reducer,
            semantic_verifier_key=result.semantic_verifier_key,
            semantic_verifier_id=result.semantic_verifier_id,
            semantic_replay_document_sha256=digest,
            source_operational_cutoff_id=source.operational_cutoff_id,
            source_local_start_sequence=source.covered_start_sequence,
            source_local_cutoff_sequence=source.covered_cutoff_sequence,
            bound_source=bound_source,
            semantic_replay_result=result,
        )
    )


def validate_k7_verified_nine_shared_resource_pair_once_v1(
    *,
    source_envelope: Any,
    supplied_verified_envelope: Any,
) -> K7VerifiedNineSharedResourceTransactionSnapshotV1:
    """Replay one expected/supplied pair exactly once for one transaction.

    This deliberately returns no live authorization or mutable document.  It
    is a bounded validation primitive for a caller-owned public transaction;
    the standalone verifier and public artifact properties continue to replay
    their full authoritative checks on every call.
    """

    if type(source_envelope) is not live_v3.K7ProductionSharedResourceEnvelopeV3:
        _fail("exact nine-path pair replay requires one exact V3 source envelope")
    if (
        type(supplied_verified_envelope)
        is not K7VerifiedNineSharedResourceEnvelopeV1
    ):
        _fail("exact nine-path pair replay requires one exact verified envelope")
    source_envelope_id = source_envelope.envelope_id
    if tuple(row.source.path for row in source_envelope.bound_sources) != (
        resolution_v2.SHARED_RESOURCE_PATHS
    ):
        _fail("V3 source envelope is not the fixed ordered nine-path set")
    authorization_rows = supplied_verified_envelope.authorizations
    if (
        type(authorization_rows) is not tuple
        or any(
            type(row) is not VerifiedSharedResourcePathAuthorizationV1
            for row in authorization_rows
        )
    ):
        _fail("verified envelope lacks the exact ordered distinct nine-path set")
    expected = tuple(
        _replay_expected_path_snapshot_once_v1(
            envelope=source_envelope,
            source_envelope_id=source_envelope_id,
            bound_source=bound_source,
        )
        for bound_source in source_envelope.bound_sources
    )
    supplied = tuple(
        _validate_path_authorization_values_once_v1(
            _path_authorization_validation_input_v1(row)
        )
        for row in authorization_rows
    )
    supplied_envelope = _validate_verified_nine_envelope_once_v1(
        supplied_verified_envelope,
        authorization_snapshots=supplied,
    )
    expected_payload = _envelope_payload(
        source_envelope=source_envelope,
        source_envelope_id=source_envelope_id,
        authorizations=expected,
    )
    expected_envelope_id = content_id(
        VERIFIED_NINE_ENVELOPE_V1_DOMAIN,
        expected_payload,
    )
    expected_document_bytes = canonical_json_bytes(
        {
            **expected_payload,
            "verified_nine_shared_resource_envelope_id": expected_envelope_id,
        }
    )
    if (
        expected_envelope_id != supplied_envelope.verified_envelope_id
        or expected_document_bytes != supplied_envelope.canonical_document_bytes
        or supplied_envelope.source_v3_envelope_id != source_envelope_id
        or tuple(row.canonical_document_bytes for row in expected)
        != tuple(row.canonical_document_bytes for row in supplied)
    ):
        _fail("verified nine-source authority was transplanted or stale")
    return K7VerifiedNineSharedResourceTransactionSnapshotV1(
        source_v3_envelope_id=source_envelope_id,
        expected_verified_envelope_id=expected_envelope_id,
        supplied_verified_envelope_id=supplied_envelope.verified_envelope_id,
        expected_authorizations=expected,
        supplied_authorizations=supplied,
        expected_canonical_document_bytes=expected_document_bytes,
        supplied_canonical_document_bytes=(
            supplied_envelope.canonical_document_bytes
        ),
    )


__all__ = (
    "ConstructionSharedResourceVerifiedEnvelopeV1Error",
    "K7ValidatedSharedResourcePathSnapshotV1",
    "K7VerifiedNineSharedResourceEnvelopeV1",
    "K7VerifiedNineSharedResourceTransactionSnapshotV1",
    "PATH_EXACT_AUTHORIZATION_V1_DOMAIN",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "VERIFIED_NINE_ENVELOPE_V1_DOMAIN",
    "VerifiedSharedResourcePathAuthorizationV1",
    "validate_k7_verified_nine_shared_resource_pair_once_v1",
    "verify_k7_production_shared_resource_envelope_exact_v1",
)
