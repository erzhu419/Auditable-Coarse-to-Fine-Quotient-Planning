"""Dependency-aware portable replay for the eleven public V0-075 roles.

This construction module consumes two strict raw byte inputs:

* one complete portable occurrence-evidence bundle; and
* one portable public-context closure.

Resolving the second input also reads the explicitly supplied repository root
to replay its public remote-anchor and tracked-blob context.  That third local
public context is not a source-authoritative snapshot, and its source manifest
is only an opaque content-ID binding.  This is a production blocker, not an
additional authority claim.

The module never accepts a caller-created typed artifact, a private
environment, a target law, or an observer channel.  It reconstructs the eleven
M0 typed objects and their exact M0 constructor dependencies, but deliberately
leaves signed request/batch/outcome/control semantics to M1.  Consequently it
cannot claim complete M0 role semantics, authorize production, or complete the
aggregate portable registry.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_batch_native_statistical_backend_v1 as identity
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable
from acfqp import v075_portable_public_context_closure_v2 as public_context
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.65.0"
PROFILE_KEY = "v075_portable_public_semantic_replay_v2"

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
FRESH_HELDOUT_ACCESS_ALLOWED = False
OBSERVER_OPEN_ALLOWED = False
PRIVATE_INPUT_CHANNELS_ALLOWED = False
PLAN_CERTIFICATE_ISSUANCE_ALLOWED = False
INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED = False
SOURCE_AUTHORITY_COMPLETE = public_context.SOURCE_AUTHORITY_COMPLETE
CODE_PROVENANCE_COMPLETE = False
ALL_REGISTERED_ARMS_COMPLETE = False
SUPPORTED_ARM_COVERAGE = ("NO_PRIOR",)
M0_ROLE_SEMANTICS_COMPLETE = False
PORTABLE_SEMANTIC_REGISTRY_COMPLETE = False

TERMINAL_SCOPE = "CONSTRUCTION_PORTABLE_PUBLIC_SEMANTIC_REPLAY_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
TERMINAL_CODE = "M0_PUBLIC_ROLE_REPLAYED_SOURCE_AUTHORITY_INCOMPLETE"

MAX_OUTPUT_BYTES = 64 * 1024 * 1024

DOMAIN_TAGS = MappingProxyType(
    {
        "typed_graph": "acfqp:v075-portable-public-m0-typed-graph:v2",
        "record_attestation": (
            "acfqp:v075-portable-public-record-semantic-attestation:v2"
        ),
        "aggregate": "acfqp:v075-portable-public-semantic-replay:v2",
    }
)

M0_ROLE_ORDER = (
    "INITIAL_ROW_INTENT",
    "INITIAL_ACQUISITION_SCHEDULE",
    "INITIAL_ACQUISITION_VERIFICATION",
    "SYMBOLIC_GRAPH_STATE",
    "LEGAL_ACTION_CATALOGUE",
    "OBSERVATION_ROW_BINDING",
    "OBSERVER_SIGNED_SUPPORT_EVIDENCE",
    "SHARED_SUPPORT_EPOCH",
    "SHARED_SUPPORT_CHAIN",
    "PAIRING_AUTHORITY",
    "TRANSITION_STREAM",
)
_M0_ROLES = frozenset(M0_ROLE_ORDER)
_TYPED_CONSUMABLE_DEPENDENCY_ROLES = _M0_ROLES | frozenset(
    {"OCCURRENCE_IDENTITY"}
)


class V075PortablePublicSemanticReplayV2InvariantViolation(ValueError):
    """One public dependency or exact recurrence failed semantic replay."""


class V075PortablePublicSemanticReplayProductionV2NotReady(RuntimeError):
    """M0 closure cannot override the incomplete source authority."""


class V075PortablePublicRoleReplayStatusV2(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


def _fail(message: str) -> NoReturn:
    raise V075PortablePublicSemanticReplayV2InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075PortablePublicSemanticReplayV2InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075PortablePublicSemanticReplayV2InvariantViolation(
            str(error)
        ) from error


def _raw(value: Any) -> bytes:
    to_document = getattr(value, "to_document", None)
    if not callable(to_document):
        _fail("replayed public artifact lacks one canonical document")
    try:
        return canonical_json_bytes(to_document())
    except (TypeError, ValueError) as error:
        raise V075PortablePublicSemanticReplayV2InvariantViolation(
            "replayed public artifact is not canonical"
        ) from error


def _document(record: portable.V075PortableEvidenceArtifactRecordV2) -> dict:
    document = record.artifact_document
    if type(document) is not dict:
        _fail("portable public record document is not one object")
    return document


def _canonical_action(value: Any) -> tuple[int, int, int]:
    if (
        type(value) is not list
        or len(value) != 3
        or any(type(item) is not int or item < 0 for item in value)
    ):
        _fail("portable public action is malformed")
    return (value[0], value[1], value[2])


def _exact_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(f"{label} is not one exact nonnegative integer")
    return value


@dataclass(frozen=True, slots=True)
class _RecordStore:
    records: tuple[portable.V075PortableEvidenceArtifactRecordV2, ...]
    by_role: Mapping[
        str,
        tuple[portable.V075PortableEvidenceArtifactRecordV2, ...],
    ] = field(init=False, repr=False)
    by_semantic_id: Mapping[
        str,
        portable.V075PortableEvidenceArtifactRecordV2,
    ] = field(init=False, repr=False)
    by_record_id: Mapping[
        str,
        portable.V075PortableEvidenceArtifactRecordV2,
    ] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        mutable_roles: dict[
            str,
            list[portable.V075PortableEvidenceArtifactRecordV2],
        ] = {}
        mutable_ids: dict[
            str,
            portable.V075PortableEvidenceArtifactRecordV2,
        ] = {}
        mutable_record_ids: dict[
            str,
            portable.V075PortableEvidenceArtifactRecordV2,
        ] = {}
        for record in self.records:
            mutable_roles.setdefault(record.role, []).append(record)
            if record.semantic_artifact_id in mutable_ids:
                _fail("portable semantic artifact identity is duplicated")
            mutable_ids[record.semantic_artifact_id] = record
            if record.record_id in mutable_record_ids:
                _fail("portable record identity is duplicated")
            mutable_record_ids[record.record_id] = record
        object.__setattr__(
            self,
            "by_role",
            MappingProxyType(
                {
                    role: tuple(items)
                    for role, items in mutable_roles.items()
                }
            ),
        )
        object.__setattr__(
            self,
            "by_semantic_id",
            MappingProxyType(mutable_ids),
        )
        object.__setattr__(
            self,
            "by_record_id",
            MappingProxyType(mutable_record_ids),
        )
        for record in self.records:
            for dependency_id in record.dependency_record_ids:
                dependency = mutable_record_ids.get(dependency_id)
                if dependency is None or dependency.index >= record.index:
                    _fail(
                        "portable declared dependency is missing or not "
                        "strictly earlier"
                    )

    def role(
        self,
        role: str,
        *,
        nonempty: bool = True,
    ) -> tuple[portable.V075PortableEvidenceArtifactRecordV2, ...]:
        result = self.by_role.get(role, ())
        if nonempty and not result:
            _fail(f"portable bundle omits required public role {role}")
        return result

    def sole(
        self,
        role: str,
    ) -> portable.V075PortableEvidenceArtifactRecordV2:
        result = self.role(role)
        if len(result) != 1:
            _fail(f"portable public role {role} is not unique")
        return result[0]

    def document_id(
        self,
        *,
        role: str,
        field_name: str,
        value: str,
    ) -> portable.V075PortableEvidenceArtifactRecordV2:
        exact = _cid(value, f"{role} {field_name}")
        matches = tuple(
            item
            for item in self.role(role)
            if _document(item).get(field_name) == exact
        )
        if len(matches) != 1:
            _fail(
                f"portable public dependency {role}.{field_name} "
                "is missing or ambiguous"
            )
        return matches[0]


def _assert_record_equals(
    record: portable.V075PortableEvidenceArtifactRecordV2,
    expected: Any,
    *,
    semantic_id: str,
) -> None:
    if (
        record.semantic_artifact_id != _cid(
            semantic_id,
            f"{record.role} expected semantic identity",
        )
        or record.canonical_artifact_bytes != _raw(expected)
    ):
        _fail(
            f"{record.role} differs from dependency-aware semantic replay"
        )


def _resolve_public_context(
    *,
    repository_root: str | Path,
    closure: public_context.V075PortablePublicContextEvidenceClosureV2,
) -> public_context.V075PortablePublicContextRawResolutionV2:
    records = {
        item.role: item for item in closure.dependency_records
    }
    order = tuple(
        public_context.V075PortablePublicContextDependencyRoleV2
    )
    if set(records) != set(order):
        _fail("public-context closure omits one exact dependency role")
    try:
        resolution = (
            public_context
            .resolve_v075_portable_public_context_raw_dependencies_v2(
                repository_root=repository_root,
                source_manifest_bytes=closure.source_manifest.canonical_bytes,
                namespace_bytes=records[order[0]].canonical_artifact_bytes,
                observer_open_authorization_bytes=(
                    records[order[1]].canonical_artifact_bytes
                ),
                private_reveal_verification_attestation_bytes=(
                    records[order[2]].canonical_artifact_bytes
                ),
            )
        )
    except Exception as error:
        raise V075PortablePublicSemanticReplayV2InvariantViolation(
            "portable public context failed exact typed reconstruction"
        ) from error
    key = resolution.namespace.signer_registry.observer_evidence_key
    if (
        resolution.source_manifest.manifest_id
        != closure.source_manifest.manifest_id
        or resolution.repository_binding.binding_id
        != closure.repository_binding.binding_id
        or resolution.anchor.anchor_id != closure.remote_main_anchor_id
        or key.key_id != closure.namespace_public_key_id
        or canonical_json_bytes(key.to_document())
        != closure.namespace_public_key_bytes
    ):
        _fail("portable public context or namespace public key was transplanted")
    return resolution


def _replay_initial_authority(
    *,
    repository_root: str | Path,
    namespace: Any,
    store: _RecordStore,
) -> tuple[
    identity.V075BatchNativeOccurrenceIdentityV1,
    acquisition.V075InitialAcquisitionScheduleV2,
    acquisition.V075InitialAcquisitionVerificationV2,
    dict[str, Any],
]:
    occurrence_record = store.sole("OCCURRENCE_IDENTITY")
    occurrence_document = _document(occurrence_record)
    profile = acquisition.freeze_v075_five_arm_acquisition_profile_v2(
        namespace=namespace
    )
    try:
        arm = worker.V075WorkerArmV1(occurrence_document["arm"])
    except (KeyError, TypeError, ValueError) as error:
        raise V075PortablePublicSemanticReplayV2InvariantViolation(
            "portable occurrence arm is invalid"
        ) from error
    candidates = tuple(
        item
        for item in profile.occurrence_slots
        if item.context_id == occurrence_document.get("context_id")
        and item.arm is arm
        and item.occurrence_ordinal
        == occurrence_document.get("occurrence_ordinal")
    )
    if len(candidates) != 1:
        _fail("portable occurrence has no unique preregistered slot")
    schedule_record = store.sole("INITIAL_ACQUISITION_SCHEDULE")
    try:
        schedule, generated_verification = (
            acquisition
            .verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
                repository_root=repository_root,
                namespace=namespace,
                expected_slot=candidates[0],
                occurrence_identity_bytes=(
                    occurrence_record.canonical_artifact_bytes
                ),
                raw=schedule_record.canonical_artifact_bytes,
            )
        )
        verification_record = store.sole(
            "INITIAL_ACQUISITION_VERIFICATION"
        )
        verification = (
            acquisition
            .verify_v075_initial_acquisition_verification_bytes_v2(
                schedule=schedule,
                expected_slot=candidates[0],
                raw=verification_record.canonical_artifact_bytes,
            )
        )
    except Exception as error:
        raise V075PortablePublicSemanticReplayV2InvariantViolation(
            "portable initial acquisition authority failed exact replay"
        ) from error
    if (
        verification != generated_verification
        or verification.verification_id
        != verification_record.semantic_artifact_id
        or schedule.schedule_id != schedule_record.semantic_artifact_id
    ):
        _fail("portable initial acquisition verification was transplanted")

    expected_intents = {
        item.intent_id: item for item in schedule.intents
    }
    actual_intents = {
        item.semantic_artifact_id: item
        for item in store.role("INITIAL_ROW_INTENT")
    }
    if (
        len(expected_intents) != len(schedule.intents)
        or len(actual_intents) != len(store.role("INITIAL_ROW_INTENT"))
        or set(actual_intents) != set(expected_intents)
    ):
        _fail("portable initial row intents are missing, extra, or duplicated")
    for intent_id, expected in expected_intents.items():
        _assert_record_equals(
            actual_intents[intent_id],
            expected,
            semantic_id=intent_id,
        )
    return (
        schedule.occurrence,
        schedule,
        verification,
        expected_intents,
    )


def _registered_contexts(namespace: Any) -> Mapping[str, Any]:
    result = {
        item.context_id: item for item in namespace.family.replicate_contexts
    }
    if not result or len(result) != len(namespace.family.replicate_contexts):
        _fail("verified namespace has an ambiguous public context registry")
    return MappingProxyType(result)


def _replay_states(
    *,
    namespace: Any,
    store: _RecordStore,
) -> dict[str, graph.V075SymbolicGraphStateV1]:
    contexts = _registered_contexts(namespace)
    result: dict[str, graph.V075SymbolicGraphStateV1] = {}
    for record in store.role("SYMBOLIC_GRAPH_STATE"):
        document = _document(record)
        context = contexts.get(document.get("context_id"))
        ranks = document.get("ranks")
        if (
            context is None
            or type(ranks) is not list
            or any(type(item) is not int for item in ranks)
            or type(document.get("failure")) is not bool
        ):
            _fail("portable symbolic state is outside the verified namespace")
        try:
            expected = graph.V075SymbolicGraphStateV1(
                context,
                tuple(ranks),
                document["failure"],
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "portable symbolic state failed structural replay"
            ) from error
        _assert_record_equals(
            record,
            expected,
            semantic_id=expected.state_id,
        )
        result[expected.state_id] = expected
    return result


def _replay_catalogues(
    *,
    store: _RecordStore,
    states: Mapping[str, graph.V075SymbolicGraphStateV1],
) -> dict[str, graph.V075LegalActionCatalogueV1]:
    result: dict[str, graph.V075LegalActionCatalogueV1] = {}
    for record in store.role("LEGAL_ACTION_CATALOGUE"):
        document = _document(record)
        state = states.get(document.get("state_id"))
        remaining = document.get("remaining_horizon")
        if state is None or type(remaining) is not int:
            _fail("portable legal-action catalogue lacks its exact state")
        try:
            expected = graph.V075LegalActionCatalogueV1(
                state.context,
                state,
                remaining,
                graph.legal_action_triples_v1(
                    state.context,
                    state.ranks,
                    state.failure,
                ),
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "portable legal-action catalogue failed exact replay"
            ) from error
        _assert_record_equals(
            record,
            expected,
            semantic_id=expected.catalogue_id,
        )
        result[expected.catalogue_id] = expected
    return result


def _replay_rows(
    *,
    store: _RecordStore,
    catalogues: Mapping[str, graph.V075LegalActionCatalogueV1],
) -> dict[str, graph.V075ObservationRowBindingV1]:
    result: dict[str, graph.V075ObservationRowBindingV1] = {}
    for record in store.role("OBSERVATION_ROW_BINDING"):
        document = _document(record)
        catalogue = catalogues.get(document.get("catalogue_id"))
        if catalogue is None:
            _fail("portable row binding lacks its exact catalogue")
        try:
            expected = graph.observation_row_binding_v1(
                catalogue.context,
                catalogue,
                _canonical_action(document.get("action")),
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "portable observation row failed exact replay"
            ) from error
        _assert_record_equals(
            record,
            expected,
            semantic_id=expected.row_binding_id,
        )
        result[expected.row_binding_id] = expected
    return result


def _support_raw_dependency_records(
    *,
    store: _RecordStore,
    document: Mapping[str, Any],
) -> tuple[
    portable.V075PortableEvidenceArtifactRecordV2,
    portable.V075PortableEvidenceArtifactRecordV2,
    portable.V075PortableEvidenceArtifactRecordV2,
]:
    """Resolve raw M1 references without asserting their typed semantics."""

    request = store.document_id(
        role="SIGNED_BATCH_REQUEST",
        field_name="request_id",
        value=document.get("discovery_request_id"),
    )
    batch = store.document_id(
        role="SIGNED_OBSERVATION_BATCH",
        field_name="batch_id",
        value=document.get("discovery_batch_id"),
    )
    batch_document = _document(batch)
    nested_outcomes = batch_document.get("outcomes")
    exact_nested = (
        [
            item
            for item in nested_outcomes
            if type(item) is dict
            and item.get("outcome_id")
            == document.get("discovery_outcome_id")
            and item.get("count")
            == document.get("discovery_outcome_count")
        ]
        if type(nested_outcomes) is list
        else []
    )
    if len(exact_nested) != 1:
        _fail(
            "support evidence has no unique byte-carried outcome inside "
            "its referenced batch"
        )
    nested_raw = canonical_json_bytes(exact_nested[0])
    outcomes = tuple(
        item
        for item in store.role("SIGNED_BATCH_OUTCOME")
        if item.canonical_artifact_bytes == nested_raw
    )
    if len(outcomes) != 1:
        _fail(
            "support evidence batch outcome bytes have no unique portable "
            "record"
        )
    return request, batch, outcomes[0]


def _assert_support_batch_raw_field_consistency(
    *,
    store: _RecordStore,
    document: Mapping[str, Any],
    observed_state: graph.V075SymbolicGraphStateV1,
) -> None:
    """Check byte-carried cross-references without replaying M1 signatures."""

    request_id = _cid(
        document.get("discovery_request_id"),
        "support evidence discovery request",
    )
    batch_id = _cid(
        document.get("discovery_batch_id"),
        "support evidence discovery batch",
    )
    outcome_id = _cid(
        document.get("discovery_outcome_id"),
        "support evidence discovery outcome",
    )
    request_record, batch_record, outcome_record = (
        _support_raw_dependency_records(
            store=store,
            document=document,
        )
    )
    request = _document(request_record)
    batch = _document(batch_record)
    outcome = _document(outcome_record)
    commitments = batch.get("outcome_aggregate_commitments")
    nested_outcomes = batch.get("outcomes")
    expected_commitment = {
        "outcome_id": outcome_id,
        "count": outcome.get("count"),
        "reward_sum": outcome.get("reward_sum"),
    }
    matching_outcomes = (
        [
            item
            for item in nested_outcomes
            if type(item) is dict
            and item.get("next_ranks") == list(observed_state.ranks)
            and item.get("failure") == observed_state.failure
        ]
        if type(nested_outcomes) is list
        else []
    )
    matching_outcome_ids = tuple(
        _cid(
            item.get("outcome_id"),
            "matching signed observation outcome",
        )
        for item in matching_outcomes
    )
    if (
        request.get("request_id") != request_id
        or batch.get("request_id") != request_id
        or batch.get("batch_id") != batch_id
        or type(batch.get("outcome_aggregate_ids")) is not list
        or outcome_id not in batch["outcome_aggregate_ids"]
        or type(commitments) is not list
        or expected_commitment not in commitments
        or not matching_outcomes
        or min(matching_outcome_ids) != outcome_id
        or outcome.get("count") != document.get("discovery_outcome_count")
        or outcome.get("next_ranks") != list(observed_state.ranks)
        or outcome.get("failure") != observed_state.failure
        or request.get("row_binding_id") != document.get("row_binding_id")
        or request.get("observer_epoch_index")
        != document.get("source_observer_epoch_index")
        or request.get("lane") != "DISCOVERY"
    ):
        _fail(
            "observer-signed support evidence differs from the byte-carried "
            "request/batch/outcome fields; M1 signature semantics remain "
            "unresolved"
        )


def _replay_support_evidence(
    *,
    namespace: Any,
    store: _RecordStore,
    rows: Mapping[str, graph.V075ObservationRowBindingV1],
    states: Mapping[str, graph.V075SymbolicGraphStateV1],
) -> dict[str, graph.V075BatchAggregateSupportEvidenceV1]:
    result: dict[str, graph.V075BatchAggregateSupportEvidenceV1] = {}
    for record in store.role("OBSERVER_SIGNED_SUPPORT_EVIDENCE"):
        document = _document(record)
        row = rows.get(document.get("row_binding_id"))
        state = states.get(document.get("observed_state_id"))
        if row is None or state is None:
            _fail("portable support evidence lacks its row or state")
        _assert_support_batch_raw_field_consistency(
            store=store,
            document=document,
            observed_state=state,
        )
        try:
            expected = graph.bind_batch_aggregate_support_evidence_v1(
                namespace=namespace,
                row_binding=row,
                observed_state=state,
                source_observer_epoch_index=_exact_int(
                    document.get("source_observer_epoch_index"),
                    "support evidence observer epoch",
                ),
                discovery_request_id=document["discovery_request_id"],
                discovery_batch_id=document["discovery_batch_id"],
                discovery_outcome_id=document["discovery_outcome_id"],
                discovery_outcome_count=_exact_int(
                    document.get("discovery_outcome_count"),
                    "support evidence outcome count",
                    minimum=1,
                ),
                observer_signature_hex=document.get(
                    "observer_signature_hex"
                ),
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "portable observer support signature failed exact replay"
            ) from error
        _assert_record_equals(
            record,
            expected,
            semantic_id=expected.evidence_id,
        )
        result[expected.evidence_id] = expected
    return result


def _replay_support_epochs(
    *,
    namespace: Any,
    store: _RecordStore,
    rows: Mapping[str, graph.V075ObservationRowBindingV1],
    evidence: Mapping[
        str,
        graph.V075BatchAggregateSupportEvidenceV1,
    ],
) -> dict[str, graph.V075SharedSupportEpochV1]:
    pending = list(store.role("SHARED_SUPPORT_EPOCH"))
    result: dict[str, graph.V075SharedSupportEpochV1] = {}
    while pending:
        progressed = False
        remaining: list[
            portable.V075PortableEvidenceArtifactRecordV2
        ] = []
        for record in pending:
            document = _document(record)
            parent_id = document.get("parent_epoch_id")
            if parent_id is not None and parent_id not in result:
                remaining.append(record)
                continue
            row = rows.get(document.get("row_binding_id"))
            evidence_ids = document.get("evidence_ids")
            if (
                row is None
                or type(evidence_ids) is not list
                or any(item not in evidence for item in evidence_ids)
            ):
                _fail("portable support epoch lacks exact typed dependencies")
            parent = None if parent_id is None else result[parent_id]
            try:
                expected = graph.derive_shared_support_epoch_v1(
                    namespace=namespace,
                    row_binding=row,
                    epoch_index=_exact_int(
                        document.get("epoch_index"),
                        "support epoch index",
                    ),
                    evidence=tuple(evidence[item] for item in evidence_ids),
                    parent=parent,
                )
            except Exception as error:
                raise V075PortablePublicSemanticReplayV2InvariantViolation(
                    "portable support epoch failed parent recurrence"
                ) from error
            _assert_record_equals(
                record,
                expected,
                semantic_id=expected.epoch_id,
            )
            result[expected.epoch_id] = expected
            progressed = True
        if not progressed:
            _fail("portable support epochs are cyclic or parent-gapped")
        pending = remaining
    return result


def _replay_support_chains(
    *,
    namespace: Any,
    store: _RecordStore,
    rows: Mapping[str, graph.V075ObservationRowBindingV1],
    epochs: Mapping[str, graph.V075SharedSupportEpochV1],
) -> dict[str, graph.V075SharedSupportChainV1]:
    result: dict[str, graph.V075SharedSupportChainV1] = {}
    for record in store.role("SHARED_SUPPORT_CHAIN"):
        document = _document(record)
        row = rows.get(document.get("row_binding_id"))
        epoch_ids = document.get("epoch_ids")
        if (
            row is None
            or type(epoch_ids) is not list
            or not epoch_ids
            or any(item not in epochs for item in epoch_ids)
        ):
            _fail("portable support chain lacks its exact epochs")
        try:
            expected = graph.freeze_shared_support_chain_v1(
                namespace=namespace,
                row_binding=row,
                epochs=tuple(epochs[item] for item in epoch_ids),
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "portable support chain failed exact recurrence"
            ) from error
        _assert_record_equals(
            record,
            expected,
            semantic_id=expected.chain_id,
        )
        result[expected.chain_id] = expected
    return result


def _replay_pairing_authorities(
    *,
    namespace: Any,
    store: _RecordStore,
    rows: Mapping[str, graph.V075ObservationRowBindingV1],
    chains: Mapping[str, graph.V075SharedSupportChainV1],
) -> dict[str, graph.V075FiveArmPairingAuthorityV1]:
    result: dict[str, graph.V075FiveArmPairingAuthorityV1] = {}
    for record in store.role("PAIRING_AUTHORITY"):
        document = _document(record)
        row = rows.get(document.get("row_binding_id"))
        chain = chains.get(document.get("support_chain_id"))
        if row is None or chain is None:
            _fail("portable pairing authority lacks its row or support chain")
        try:
            expected = graph.freeze_five_arm_pairing_authority_v1(
                namespace=namespace,
                row_binding=row,
                support_chain=chain,
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "portable pairing authority failed exact replay"
            ) from error
        _assert_record_equals(
            record,
            expected,
            semantic_id=expected.pairing_authority_id,
        )
        result[expected.pairing_authority_id] = expected
    return result


def _replay_streams(
    *,
    store: _RecordStore,
    pairings: Mapping[str, graph.V075FiveArmPairingAuthorityV1],
) -> dict[str, graph.V075TransitionStreamIdentityV1]:
    result: dict[str, graph.V075TransitionStreamIdentityV1] = {}
    for record in store.role("TRANSITION_STREAM"):
        document = _document(record)
        pairing = pairings.get(document.get("pairing_authority_id"))
        if pairing is None or type(document.get("arm")) is not str:
            _fail("portable transition stream lacks its pairing authority")
        try:
            expected = graph.derive_transition_stream_identity_v1(
                pairing_authority=pairing,
                arm=document["arm"],
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "portable transition stream failed exact replay"
            ) from error
        _assert_record_equals(
            record,
            expected,
            semantic_id=expected.stream_id,
        )
        result[expected.stream_id] = expected
    return result


def _assert_schedule_graph_membership(
    *,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    rows: Mapping[str, graph.V075ObservationRowBindingV1],
) -> None:
    for intent in schedule.intents:
        replayed = rows.get(intent.row_binding.row_binding_id)
        if replayed is None or _raw(replayed) != _raw(intent.row_binding):
            _fail("initial schedule row is absent from the public graph replay")


def _document_references_record(
    value: Any,
    dependency: portable.V075PortableEvidenceArtifactRecordV2,
) -> bool:
    """Return whether exact owner bytes reference one replayed record.

    This mirrors only the two public reference forms that this M0 layer
    actually consumes: a role-bound semantic content ID or a byte-identical
    embedded registered document.  It is not a substitute for replaying the
    dependency's own signature, control, or transport semantics.
    """

    if type(value) is str:
        return value == dependency.semantic_artifact_id
    if type(value) is list:
        return any(
            _document_references_record(item, dependency)
            for item in value
        )
    if type(value) is not dict:
        return False
    if (
        value.get("schema") == dependency.artifact_schema
        and canonical_json_bytes(value)
        == dependency.canonical_artifact_bytes
    ):
        return True
    return any(
        _document_references_record(item, dependency)
        for item in value.values()
    )


@dataclass(frozen=True, slots=True)
class _RecordDependencyCoverage:
    declared_record_ids: tuple[str, ...]
    typed_consumed_record_ids: tuple[str, ...]
    raw_field_checked_record_ids: tuple[str, ...]
    unresolved_record_ids: tuple[str, ...]
    unresolved_roles: tuple[str, ...]
    undeclared_unresolved_reference_record_ids: tuple[str, ...]


def _classify_record_dependency_coverage(
    *,
    record: portable.V075PortableEvidenceArtifactRecordV2,
    store: _RecordStore,
) -> _RecordDependencyCoverage:
    document = _document(record)
    declared = tuple(record.dependency_record_ids)
    declared_set = set(declared)

    typed_expected = {
        dependency.record_id
        for dependency in store.records
        if dependency.record_id != record.record_id
        and dependency.role in _TYPED_CONSUMABLE_DEPENDENCY_ROLES
        and _document_references_record(document, dependency)
    }
    typed_declared = {
        dependency_id
        for dependency_id in declared
        if store.by_record_id[dependency_id].role
        in _TYPED_CONSUMABLE_DEPENDENCY_ROLES
    }
    if typed_expected != typed_declared:
        _fail(
            f"{record.role} declared M0 dependencies differ from the "
            "exact typed dependencies consumed by reconstruction"
        )

    raw_field_checked: set[str] = set()
    if record.role == "OBSERVER_SIGNED_SUPPORT_EVIDENCE":
        raw_field_checked.update(
            item.record_id
            for item in _support_raw_dependency_records(
                store=store,
                document=document,
            )
        )

    unresolved = (declared_set - typed_declared) | raw_field_checked
    undeclared = raw_field_checked - declared_set
    unresolved_roles = {
        store.by_record_id[dependency_id].role
        for dependency_id in unresolved
    }
    return _RecordDependencyCoverage(
        tuple(sorted(declared_set)),
        tuple(sorted(typed_declared)),
        tuple(sorted(raw_field_checked)),
        tuple(sorted(unresolved)),
        tuple(sorted(unresolved_roles)),
        tuple(sorted(undeclared)),
    )


_M0_TYPED_GRAPH_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicM0TypedGraphV2:
    """In-process M0 graph guarded as construction API discipline.

    The issuer gate prevents ordinary caller construction through the public
    API.  It is not a security boundary against arbitrary code already
    executing in the same Python process.
    """

    _issuer: InitVar[object]
    bundle_id: str
    public_context_closure_id: str
    occurrence_id: str
    target_tape_namespace_id: str
    occurrence: identity.V075BatchNativeOccurrenceIdentityV1 = field(
        repr=False
    )
    schedule: acquisition.V075InitialAcquisitionScheduleV2 = field(
        repr=False
    )
    verification: acquisition.V075InitialAcquisitionVerificationV2 = field(
        repr=False
    )
    intents: tuple[acquisition.V075InitialRowIntentV2, ...] = field(
        repr=False
    )
    states: tuple[graph.V075SymbolicGraphStateV1, ...] = field(
        repr=False
    )
    catalogues: tuple[graph.V075LegalActionCatalogueV1, ...] = field(
        repr=False
    )
    rows: tuple[graph.V075ObservationRowBindingV1, ...] = field(
        repr=False
    )
    support_evidence: tuple[
        graph.V075BatchAggregateSupportEvidenceV1,
        ...,
    ] = field(repr=False)
    epochs: tuple[graph.V075SharedSupportEpochV1, ...] = field(
        repr=False
    )
    chains: tuple[graph.V075SharedSupportChainV1, ...] = field(
        repr=False
    )
    pairings: tuple[graph.V075FiveArmPairingAuthorityV1, ...] = field(
        repr=False
    )
    transition_streams: tuple[
        graph.V075TransitionStreamIdentityV1,
        ...,
    ] = field(repr=False)
    _graph_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.bundle_id, "M0 typed graph bundle"),
            (
                self.public_context_closure_id,
                "M0 typed graph public context",
            ),
            (self.occurrence_id, "M0 typed graph occurrence"),
            (
                self.target_tape_namespace_id,
                "M0 typed graph namespace",
            ),
        ):
            _cid(value, label)
        if _issuer is not _M0_TYPED_GRAPH_ISSUER:
            _fail("M0 typed graph is caller-minted")
        _validate_m0_typed_graph(self)
        object.__setattr__(
            self,
            "_graph_id",
            _hash("typed_graph", self._identity_payload()),
        )

    def _ordered_typed_ids(self) -> dict[str, tuple[str, ...]]:
        return {
            "occurrence_id": (self.occurrence.occurrence_id,),
            "schedule_id": (self.schedule.schedule_id,),
            "verification_id": (self.verification.verification_id,),
            "intent_ids": tuple(item.intent_id for item in self.intents),
            "state_ids": tuple(item.state_id for item in self.states),
            "catalogue_ids": tuple(
                item.catalogue_id for item in self.catalogues
            ),
            "row_binding_ids": tuple(
                item.row_binding_id for item in self.rows
            ),
            "support_evidence_ids": tuple(
                item.evidence_id for item in self.support_evidence
            ),
            "epoch_ids": tuple(item.epoch_id for item in self.epochs),
            "chain_ids": tuple(item.chain_id for item in self.chains),
            "pairing_authority_ids": tuple(
                item.pairing_authority_id for item in self.pairings
            ),
            "transition_stream_ids": tuple(
                item.stream_id for item in self.transition_streams
            ),
        }

    def _role_semantic_ids(self) -> dict[str, tuple[str, ...]]:
        return {
            "INITIAL_ROW_INTENT": tuple(
                sorted(item.intent_id for item in self.intents)
            ),
            "INITIAL_ACQUISITION_SCHEDULE": (
                self.schedule.schedule_id,
            ),
            "INITIAL_ACQUISITION_VERIFICATION": (
                self.verification.verification_id,
            ),
            "SYMBOLIC_GRAPH_STATE": tuple(
                item.state_id for item in self.states
            ),
            "LEGAL_ACTION_CATALOGUE": tuple(
                item.catalogue_id for item in self.catalogues
            ),
            "OBSERVATION_ROW_BINDING": tuple(
                item.row_binding_id for item in self.rows
            ),
            "OBSERVER_SIGNED_SUPPORT_EVIDENCE": tuple(
                item.evidence_id for item in self.support_evidence
            ),
            "SHARED_SUPPORT_EPOCH": tuple(
                item.epoch_id for item in self.epochs
            ),
            "SHARED_SUPPORT_CHAIN": tuple(
                item.chain_id for item in self.chains
            ),
            "PAIRING_AUTHORITY": tuple(
                item.pairing_authority_id for item in self.pairings
            ),
            "TRANSITION_STREAM": tuple(
                item.stream_id for item in self.transition_streams
            ),
        }

    @staticmethod
    def _serializable_id_mapping(
        value: Mapping[str, tuple[str, ...]],
    ) -> dict[str, list[str]]:
        return {key: list(ids) for key, ids in value.items()}

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_portable_public_m0_typed_graph.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "portable_bundle_id": self.bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "ordering_rule": (
                "SCHEDULE_INTENT_ORDER_THEN_LEXICOGRAPHIC_CONTENT_ID"
            ),
            "ordered_typed_ids": self._serializable_id_mapping(
                self._ordered_typed_ids()
            ),
            "role_semantic_ids": self._serializable_id_mapping(
                self._role_semantic_ids()
            ),
            "in_memory_only": True,
            "issuer_gate_semantics": (
                "CONSTRUCTION_API_DISCIPLINE_ONLY"
            ),
            "python_process_security_boundary": False,
            "typed_objects_serialized": False,
            "private_material_serialized": False,
            "source_artifacts_serialized": False,
            "source_authority_complete": False,
            "code_provenance_complete": False,
            "all_registered_arms_complete": False,
            "portable_semantic_registry_complete": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
        }

    def _assert_content_id(self) -> None:
        _validate_m0_typed_graph(self)
        if self.graph_id != _hash(
            "typed_graph",
            self._identity_payload(),
        ):
            _fail("M0 typed graph content ID is stale or rehashed")

    @property
    def graph_id(self) -> str:
        return self._graph_id

    @property
    def ordered_typed_ids(self) -> Mapping[str, tuple[str, ...]]:
        return MappingProxyType(self._ordered_typed_ids())

    @property
    def role_semantic_ids(self) -> Mapping[str, tuple[str, ...]]:
        return MappingProxyType(self._role_semantic_ids())

    @property
    def namespace(self) -> Any:
        return self.schedule.profile.namespace

    @property
    def intents_by_id(
        self,
    ) -> Mapping[str, acquisition.V075InitialRowIntentV2]:
        return MappingProxyType(
            {item.intent_id: item for item in self.intents}
        )

    @property
    def states_by_id(
        self,
    ) -> Mapping[str, graph.V075SymbolicGraphStateV1]:
        return MappingProxyType(
            {item.state_id: item for item in self.states}
        )

    @property
    def catalogues_by_id(
        self,
    ) -> Mapping[str, graph.V075LegalActionCatalogueV1]:
        return MappingProxyType(
            {item.catalogue_id: item for item in self.catalogues}
        )

    @property
    def rows_by_id(
        self,
    ) -> Mapping[str, graph.V075ObservationRowBindingV1]:
        return MappingProxyType(
            {item.row_binding_id: item for item in self.rows}
        )

    @property
    def evidence_by_id(
        self,
    ) -> Mapping[str, graph.V075BatchAggregateSupportEvidenceV1]:
        return MappingProxyType(
            {item.evidence_id: item for item in self.support_evidence}
        )

    @property
    def epochs_by_id(
        self,
    ) -> Mapping[str, graph.V075SharedSupportEpochV1]:
        return MappingProxyType(
            {item.epoch_id: item for item in self.epochs}
        )

    @property
    def chains_by_id(
        self,
    ) -> Mapping[str, graph.V075SharedSupportChainV1]:
        return MappingProxyType(
            {item.chain_id: item for item in self.chains}
        )

    @property
    def pairings_by_id(
        self,
    ) -> Mapping[str, graph.V075FiveArmPairingAuthorityV1]:
        return MappingProxyType(
            {
                item.pairing_authority_id: item
                for item in self.pairings
            }
        )

    @property
    def streams_by_id(
        self,
    ) -> Mapping[str, graph.V075TransitionStreamIdentityV1]:
        return MappingProxyType(
            {item.stream_id: item for item in self.transition_streams}
        )

    def __reduce__(self) -> NoReturn:
        raise TypeError("M0 typed graph is in-memory-only")


def _exact_typed_tuple(
    values: Any,
    *,
    exact_type: type,
    identity_attribute: str,
    label: str,
    schedule_order: tuple[Any, ...] | None = None,
) -> tuple[str, ...]:
    if (
        type(values) is not tuple
        or not values
        or any(type(item) is not exact_type for item in values)
    ):
        _fail(f"M0 typed graph {label} have foreign producer types")
    identifiers = tuple(
        _cid(
            getattr(item, identity_attribute),
            f"M0 typed graph {label} identity",
        )
        for item in values
    )
    if len(set(identifiers)) != len(identifiers):
        _fail(f"M0 typed graph {label} identities are duplicated")
    if schedule_order is not None:
        if values != schedule_order:
            _fail(f"M0 typed graph {label} differ from schedule order")
    elif identifiers != tuple(sorted(identifiers)):
        _fail(f"M0 typed graph {label} are not in canonical ID order")
    return identifiers


def _assert_exact_typed_bytes(
    claimed: Any,
    expected: Any,
    *,
    label: str,
) -> None:
    if type(claimed) is not type(expected) or _raw(claimed) != _raw(expected):
        _fail(f"M0 typed graph {label} differs from exact producer replay")


def _validate_m0_typed_graph(
    typed_graph: V075PortablePublicM0TypedGraphV2,
) -> None:
    if (
        type(typed_graph.occurrence)
        is not identity.V075BatchNativeOccurrenceIdentityV1
        or type(typed_graph.schedule)
        is not acquisition.V075InitialAcquisitionScheduleV2
        or type(typed_graph.verification)
        is not acquisition.V075InitialAcquisitionVerificationV2
    ):
        _fail("M0 typed graph initial authority has foreign producer types")
    try:
        replayed_occurrence = (
            identity.replay_v075_batch_native_occurrence_identity_v1(
                typed_graph.occurrence
            )
        )
        replayed_verification = (
            acquisition
            .verify_v075_initial_acquisition_verification_bytes_v2(
                schedule=typed_graph.schedule,
                expected_slot=typed_graph.verification.expected_slot,
                raw=typed_graph.verification.canonical_bytes,
            )
        )
    except Exception as error:
        raise V075PortablePublicSemanticReplayV2InvariantViolation(
            "M0 typed graph initial authority failed exact producer replay"
        ) from error
    _assert_exact_typed_bytes(
        typed_graph.occurrence,
        replayed_occurrence,
        label="occurrence",
    )
    _assert_exact_typed_bytes(
        typed_graph.verification,
        replayed_verification,
        label="initial verification",
    )
    namespace = typed_graph.schedule.profile.namespace
    if (
        typed_graph.occurrence_id
        != typed_graph.occurrence.occurrence_id
        or typed_graph.schedule.occurrence != typed_graph.occurrence
        or typed_graph.verification.schedule != typed_graph.schedule
        or typed_graph.target_tape_namespace_id
        != typed_graph.occurrence.target_tape_namespace_id
        or typed_graph.target_tape_namespace_id
        != namespace.target_tape_namespace_id
    ):
        _fail("M0 typed graph initial authority was transplanted")

    intent_ids = _exact_typed_tuple(
        typed_graph.intents,
        exact_type=acquisition.V075InitialRowIntentV2,
        identity_attribute="intent_id",
        label="initial intents",
        schedule_order=typed_graph.schedule.intents,
    )
    intent_position = {
        intent_id: index for index, intent_id in enumerate(intent_ids)
    }
    if any(
        dependency_id not in intent_position
        or intent_position[dependency_id] >= index
        for index, item in enumerate(typed_graph.intents)
        for dependency_id in item.dependency_intent_ids
    ):
        _fail("M0 typed graph initial intent parent order is invalid")

    _exact_typed_tuple(
        typed_graph.states,
        exact_type=graph.V075SymbolicGraphStateV1,
        identity_attribute="state_id",
        label="states",
    )
    _exact_typed_tuple(
        typed_graph.catalogues,
        exact_type=graph.V075LegalActionCatalogueV1,
        identity_attribute="catalogue_id",
        label="catalogues",
    )
    _exact_typed_tuple(
        typed_graph.rows,
        exact_type=graph.V075ObservationRowBindingV1,
        identity_attribute="row_binding_id",
        label="rows",
    )
    _exact_typed_tuple(
        typed_graph.support_evidence,
        exact_type=graph.V075BatchAggregateSupportEvidenceV1,
        identity_attribute="evidence_id",
        label="support evidence",
    )
    _exact_typed_tuple(
        typed_graph.epochs,
        exact_type=graph.V075SharedSupportEpochV1,
        identity_attribute="epoch_id",
        label="epochs",
    )
    _exact_typed_tuple(
        typed_graph.chains,
        exact_type=graph.V075SharedSupportChainV1,
        identity_attribute="chain_id",
        label="chains",
    )
    _exact_typed_tuple(
        typed_graph.pairings,
        exact_type=graph.V075FiveArmPairingAuthorityV1,
        identity_attribute="pairing_authority_id",
        label="pairings",
    )
    _exact_typed_tuple(
        typed_graph.transition_streams,
        exact_type=graph.V075TransitionStreamIdentityV1,
        identity_attribute="stream_id",
        label="transition streams",
    )
    role_semantic_ids = typed_graph._role_semantic_ids()
    if (
        tuple(role_semantic_ids) != M0_ROLE_ORDER
        or any(
            ids != tuple(sorted(set(ids)))
            for ids in role_semantic_ids.values()
        )
    ):
        _fail("M0 typed graph role semantic IDs are incomplete or unordered")

    states = {item.state_id: item for item in typed_graph.states}
    catalogues = {
        item.catalogue_id: item for item in typed_graph.catalogues
    }
    rows = {item.row_binding_id: item for item in typed_graph.rows}
    evidence = {
        item.evidence_id: item for item in typed_graph.support_evidence
    }
    epochs = {item.epoch_id: item for item in typed_graph.epochs}
    chains = {item.chain_id: item for item in typed_graph.chains}
    pairings = {
        item.pairing_authority_id: item for item in typed_graph.pairings
    }

    for item in typed_graph.states:
        if item.context.context_id != typed_graph.occurrence.context_id:
            _fail("M0 typed graph state crossed occurrence context")
        try:
            expected = graph.V075SymbolicGraphStateV1(
                item.context,
                item.ranks,
                item.failure,
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "M0 typed graph state failed exact producer replay"
            ) from error
        _assert_exact_typed_bytes(item, expected, label="state")

    for item in typed_graph.catalogues:
        state = states.get(item.state.state_id)
        if state is None or item.context.context_id != (
            typed_graph.occurrence.context_id
        ):
            _fail("M0 typed graph catalogue lacks its exact state")
        try:
            expected = graph.V075LegalActionCatalogueV1(
                state.context,
                state,
                item.remaining_horizon,
                graph.legal_action_triples_v1(
                    state.context,
                    state.ranks,
                    state.failure,
                ),
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "M0 typed graph catalogue failed exact producer replay"
            ) from error
        _assert_exact_typed_bytes(item, expected, label="catalogue")

    for item in typed_graph.rows:
        catalogue = catalogues.get(item.catalogue.catalogue_id)
        if catalogue is None:
            _fail("M0 typed graph row lacks its exact catalogue")
        try:
            expected = graph.observation_row_binding_v1(
                catalogue.context,
                catalogue,
                item.action,
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "M0 typed graph row failed exact producer replay"
            ) from error
        _assert_exact_typed_bytes(item, expected, label="row")
    if any(
        rows.get(item.row_binding.row_binding_id) != item.row_binding
        for item in typed_graph.intents
    ):
        _fail("M0 typed graph schedule intent row is absent")

    for item in typed_graph.support_evidence:
        row = rows.get(item.row_binding.row_binding_id)
        state = states.get(item.observed_state.state_id)
        if (
            row is None
            or state is None
            or item.namespace != namespace
        ):
            _fail("M0 typed graph support evidence was transplanted")
        try:
            expected = graph.bind_batch_aggregate_support_evidence_v1(
                namespace=namespace,
                row_binding=row,
                observed_state=state,
                source_observer_epoch_index=(
                    item.source_observer_epoch_index
                ),
                discovery_request_id=item.discovery_request_id,
                discovery_batch_id=item.discovery_batch_id,
                discovery_outcome_id=item.discovery_outcome_id,
                discovery_outcome_count=item.discovery_outcome_count,
                observer_signature_hex=item.observer_signature_hex,
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "M0 typed graph support evidence failed producer replay"
            ) from error
        _assert_exact_typed_bytes(item, expected, label="support evidence")

    for item in typed_graph.epochs:
        row = rows.get(item.row_binding.row_binding_id)
        parent = (
            None
            if item.parent is None
            else epochs.get(item.parent.epoch_id)
        )
        exact_evidence = tuple(
            evidence.get(evidence_item.evidence_id)
            for evidence_item in item.evidence
        )
        if (
            row is None
            or item.namespace != namespace
            or (
                item.parent is not None
                and parent is None
            )
            or any(evidence_item is None for evidence_item in exact_evidence)
        ):
            _fail("M0 typed graph epoch lacks exact typed parents")
        try:
            expected = graph.derive_shared_support_epoch_v1(
                namespace=namespace,
                row_binding=row,
                epoch_index=item.epoch_index,
                evidence=exact_evidence,
                parent=parent,
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "M0 typed graph epoch failed exact parent recurrence"
            ) from error
        _assert_exact_typed_bytes(item, expected, label="support epoch")

    for item in typed_graph.chains:
        row = rows.get(item.row_binding.row_binding_id)
        exact_epochs = tuple(
            epochs.get(epoch.epoch_id) for epoch in item.epochs
        )
        if (
            row is None
            or item.namespace != namespace
            or any(epoch is None for epoch in exact_epochs)
        ):
            _fail("M0 typed graph chain lacks exact typed parents")
        try:
            expected = graph.freeze_shared_support_chain_v1(
                namespace=namespace,
                row_binding=row,
                epochs=exact_epochs,
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "M0 typed graph chain failed exact parent recurrence"
            ) from error
        _assert_exact_typed_bytes(item, expected, label="support chain")

    for item in typed_graph.pairings:
        row = rows.get(item.row_binding.row_binding_id)
        chain = chains.get(item.support_chain.chain_id)
        if (
            row is None
            or chain is None
            or item.namespace != namespace
        ):
            _fail("M0 typed graph pairing lacks exact typed parents")
        try:
            expected = graph.freeze_five_arm_pairing_authority_v1(
                namespace=namespace,
                row_binding=row,
                support_chain=chain,
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "M0 typed graph pairing failed exact parent recurrence"
            ) from error
        _assert_exact_typed_bytes(item, expected, label="pairing authority")

    for item in typed_graph.transition_streams:
        pairing = pairings.get(item.pairing_authority.pairing_authority_id)
        if (
            pairing is None
            or item.arm != typed_graph.occurrence.arm.value
        ):
            _fail("M0 typed graph stream lacks exact typed parents")
        try:
            expected = graph.derive_transition_stream_identity_v1(
                pairing_authority=pairing,
                arm=item.arm,
            )
        except Exception as error:
            raise V075PortablePublicSemanticReplayV2InvariantViolation(
                "M0 typed graph stream failed exact parent recurrence"
            ) from error
        _assert_exact_typed_bytes(item, expected, label="transition stream")


_ATTESTATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicRecordSemanticAttestationV2:
    _issuer: InitVar[object]
    bundle_id: str
    public_context_closure_id: str
    repository_binding_id: str
    source_manifest_id: str
    target_tape_namespace_id: str
    namespace_public_key_id: str
    record_id: str
    record_index: int
    role: str
    semantic_artifact_id: str
    canonical_artifact_sha256: str
    canonical_artifact_byte_count: int
    dependency_record_ids: tuple[str, ...]
    consumed_dependency_record_ids: tuple[str, ...]
    raw_field_checked_dependency_record_ids: tuple[str, ...]
    unresolved_dependency_record_ids: tuple[str, ...]
    unresolved_dependency_roles: tuple[str, ...]
    undeclared_unresolved_reference_record_ids: tuple[str, ...]
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.bundle_id, "M0 portable bundle"),
            (self.public_context_closure_id, "M0 public-context closure"),
            (self.repository_binding_id, "M0 repository binding"),
            (self.source_manifest_id, "M0 source manifest"),
            (self.target_tape_namespace_id, "M0 target namespace"),
            (self.namespace_public_key_id, "M0 namespace public key"),
            (self.record_id, "M0 portable record"),
            (self.semantic_artifact_id, "M0 semantic artifact"),
            (self.canonical_artifact_sha256, "M0 artifact bytes"),
        ):
            _cid(value, label)
        for dependency_id in {
            *self.dependency_record_ids,
            *self.consumed_dependency_record_ids,
            *self.raw_field_checked_dependency_record_ids,
            *self.unresolved_dependency_record_ids,
            *self.undeclared_unresolved_reference_record_ids,
        }:
            _cid(dependency_id, "M0 dependency coverage record")
        if (
            _issuer is not _ATTESTATION_ISSUER
            or type(self.record_index) is not int
            or self.record_index < 0
            or self.role not in _M0_ROLES
            or type(self.canonical_artifact_byte_count) is not int
            or self.canonical_artifact_byte_count <= 0
            or type(self.dependency_record_ids) is not tuple
            or tuple(sorted(set(self.dependency_record_ids)))
            != self.dependency_record_ids
            or tuple(sorted(set(self.consumed_dependency_record_ids)))
            != self.consumed_dependency_record_ids
            or tuple(
                sorted(set(self.raw_field_checked_dependency_record_ids))
            )
            != self.raw_field_checked_dependency_record_ids
            or tuple(sorted(set(self.unresolved_dependency_record_ids)))
            != self.unresolved_dependency_record_ids
            or tuple(sorted(set(self.unresolved_dependency_roles)))
            != self.unresolved_dependency_roles
            or any(
                type(role) is not str or not role
                for role in self.unresolved_dependency_roles
            )
            or tuple(
                sorted(
                    set(
                        self.undeclared_unresolved_reference_record_ids
                    )
                )
            )
            != self.undeclared_unresolved_reference_record_ids
            or not set(self.consumed_dependency_record_ids)
            <= set(self.dependency_record_ids)
            or not set(self.raw_field_checked_dependency_record_ids)
            <= set(self.unresolved_dependency_record_ids)
            or not set(
                self.undeclared_unresolved_reference_record_ids
            )
            <= set(self.unresolved_dependency_record_ids)
        ):
            _fail("M0 public record semantic attestation is malformed")
        object.__setattr__(
            self,
            "_attestation_id",
            _hash("record_attestation", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_portable_public_record_semantic_attestation.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "public_context_closure_id": self.public_context_closure_id,
            "repository_binding_id": self.repository_binding_id,
            "source_manifest_id": self.source_manifest_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "namespace_public_key_id": self.namespace_public_key_id,
            "record_id": self.record_id,
            "record_index": self.record_index,
            "role": self.role,
            "semantic_artifact_id": self.semantic_artifact_id,
            "canonical_artifact_sha256": (
                self.canonical_artifact_sha256
            ),
            "canonical_artifact_byte_count": (
                self.canonical_artifact_byte_count
            ),
            "dependency_record_ids": list(self.dependency_record_ids),
            "declared_dependency_record_ids": list(
                self.dependency_record_ids
            ),
            "consumed_dependency_record_ids": list(
                self.consumed_dependency_record_ids
            ),
            "raw_field_checked_dependency_record_ids": list(
                self.raw_field_checked_dependency_record_ids
            ),
            "unresolved_dependency_record_ids": list(
                self.unresolved_dependency_record_ids
            ),
            "unresolved_dependency_roles": list(
                self.unresolved_dependency_roles
            ),
            "undeclared_unresolved_reference_record_ids": list(
                self.undeclared_unresolved_reference_record_ids
            ),
            "semantic_replay_status": (
                (
                    V075PortablePublicRoleReplayStatusV2.COMPLETE.value
                    if not self.unresolved_dependency_record_ids
                    else V075PortablePublicRoleReplayStatusV2.INCOMPLETE.value
                )
            ),
            "producer_typed_object_reconstructed": True,
            "typed_object_reconstruction_complete": True,
            "declared_dependency_semantics_complete": (
                not self.unresolved_dependency_record_ids
            ),
            "dependency_aware_typed_object_replay_complete": (
                not self.unresolved_dependency_record_ids
            ),
            "raw_field_checks_are_typed_signature_replay": False,
            "canonical_bytes_equal_reconstruction": True,
            "cached_status_or_content_id_trusted": False,
            "namespace_public_key_replayed": True,
            "source_authority_complete": False,
            "source_manifest_authority_status": (
                "OPAQUE_CONTENT_ID_BOUND_UNVERIFIED_BY_THIS_MODULE"
            ),
            "code_provenance_complete": False,
            "all_registered_arms_complete": False,
            "portable_semantic_registry_complete": False,
            "observer_opened": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
        }

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075PortablePublicSemanticReplayResultV2:
    _issuer: InitVar[object]
    bundle_id: str
    occurrence_id: str
    public_context_closure_id: str
    repository_binding_id: str
    source_manifest_id: str
    target_tape_namespace_id: str
    namespace_public_key_id: str
    verified_arm: str
    _typed_graph: V075PortablePublicM0TypedGraphV2 = field(repr=False)
    attestations: tuple[
        V075PortablePublicRecordSemanticAttestationV2,
        ...,
    ]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        for value, label in (
            (self.bundle_id, "M0 aggregate bundle"),
            (self.occurrence_id, "M0 aggregate occurrence"),
            (
                self.public_context_closure_id,
                "M0 aggregate public-context closure",
            ),
            (self.repository_binding_id, "M0 aggregate repository"),
            (self.source_manifest_id, "M0 aggregate source manifest"),
            (self.target_tape_namespace_id, "M0 aggregate namespace"),
            (self.namespace_public_key_id, "M0 aggregate public key"),
        ):
            _cid(value, label)
        roles = {item.role for item in self.attestations}
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.attestations) is not tuple
            or not self.attestations
            or type(self._typed_graph)
            is not V075PortablePublicM0TypedGraphV2
            or any(
                type(item)
                is not V075PortablePublicRecordSemanticAttestationV2
                for item in self.attestations
            )
            or tuple(item.record_index for item in self.attestations)
            != tuple(
                sorted(item.record_index for item in self.attestations)
            )
            or len({item.record_id for item in self.attestations})
            != len(self.attestations)
            or roles != _M0_ROLES
            or not any(
                item.unresolved_dependency_record_ids
                for item in self.attestations
            )
            or any(
                item.bundle_id != self.bundle_id
                or item.public_context_closure_id
                != self.public_context_closure_id
                or item.repository_binding_id
                != self.repository_binding_id
                or item.source_manifest_id != self.source_manifest_id
                or item.target_tape_namespace_id
                != self.target_tape_namespace_id
                or item.namespace_public_key_id
                != self.namespace_public_key_id
                for item in self.attestations
            )
            or self.verified_arm not in SUPPORTED_ARM_COVERAGE
            or self._typed_graph.bundle_id != self.bundle_id
            or self._typed_graph.public_context_closure_id
            != self.public_context_closure_id
            or self._typed_graph.occurrence_id != self.occurrence_id
            or self._typed_graph.target_tape_namespace_id
            != self.target_tape_namespace_id
            or self._typed_graph.occurrence.arm.value != self.verified_arm
        ):
            _fail("M0 public semantic replay aggregate is incomplete")
        self._assert_typed_graph_attestation_binding()
        object.__setattr__(
            self,
            "_result_id",
            _hash("aggregate", self._payload()),
        )

    def _assert_typed_graph_attestation_binding(self) -> None:
        self._typed_graph._assert_content_id()
        attested = {
            role: tuple(
                sorted(
                    item.semantic_artifact_id
                    for item in self.attestations
                    if item.role == role
                )
            )
            for role in M0_ROLE_ORDER
        }
        graph_roles = dict(self._typed_graph.role_semantic_ids)
        if (
            tuple(attested) != M0_ROLE_ORDER
            or tuple(graph_roles) != M0_ROLE_ORDER
            or attested != graph_roles
            or sum(len(ids) for ids in attested.values())
            != len(self.attestations)
            or any(
                len(attested[role]) != len(graph_roles[role])
                for role in M0_ROLE_ORDER
            )
        ):
            _fail(
                "M0 typed graph role semantic IDs differ from record "
                "attestations"
            )

    @property
    def typed_graph(self) -> V075PortablePublicM0TypedGraphV2:
        """Return the graph only after fresh graph/attestation validation."""

        self._assert_typed_graph_attestation_binding()
        return self._typed_graph

    def _payload(self) -> dict[str, Any]:
        self._assert_typed_graph_attestation_binding()
        typed_graph = self._typed_graph
        consumed_dependency_record_ids = sorted(
            {
                dependency_id
                for item in self.attestations
                for dependency_id in item.consumed_dependency_record_ids
            }
        )
        unresolved_dependency_record_ids = sorted(
            {
                dependency_id
                for item in self.attestations
                for dependency_id in item.unresolved_dependency_record_ids
            }
        )
        unresolved_dependency_roles = sorted(
            {
                role
                for item in self.attestations
                for role in item.unresolved_dependency_roles
            }
        )
        undeclared_unresolved_reference_record_ids = sorted(
            {
                dependency_id
                for item in self.attestations
                for dependency_id in (
                    item.undeclared_unresolved_reference_record_ids
                )
            }
        )
        return {
            "schema": "acfqp.v075_portable_public_semantic_replay.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": TERMINAL_CODE,
            "portable_bundle_id": self.bundle_id,
            "occurrence_id": self.occurrence_id,
            "public_context_closure_id": self.public_context_closure_id,
            "repository_binding_id": self.repository_binding_id,
            "source_manifest_id": self.source_manifest_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "namespace_public_key_id": self.namespace_public_key_id,
            "verified_arm": self.verified_arm,
            "m0_typed_graph_id": typed_graph.graph_id,
            "m0_ordered_typed_ids": (
                typed_graph._serializable_id_mapping(
                    typed_graph.ordered_typed_ids
                )
            ),
            "m0_role_semantic_ids": (
                typed_graph._serializable_id_mapping(
                    typed_graph.role_semantic_ids
                )
            ),
            "m0_typed_graph_in_memory_only": True,
            "m0_typed_graph_issuer_gate_semantics": (
                "CONSTRUCTION_API_DISCIPLINE_ONLY"
            ),
            "m0_typed_graph_python_process_security_boundary": False,
            "m0_typed_objects_serialized": False,
            "source_artifacts_serialized": False,
            "supported_arm_coverage": list(SUPPORTED_ARM_COVERAGE),
            "source_consensus_prior_verified_arm": self.verified_arm,
            "source_consensus_prior_all_arm_complete": False,
            "public_tracked_source_transport_replayed": False,
            "m0_role_order": list(M0_ROLE_ORDER),
            "m0_role_count": len(M0_ROLE_ORDER),
            "m0_record_ids": [
                item.record_id for item in self.attestations
            ],
            "m0_attestation_ids": [
                item.attestation_id for item in self.attestations
            ],
            "m0_record_count": len(self.attestations),
            "consumed_dependency_record_ids": (
                consumed_dependency_record_ids
            ),
            "unresolved_dependency_record_ids": (
                unresolved_dependency_record_ids
            ),
            "unresolved_dependency_roles": unresolved_dependency_roles,
            "undeclared_unresolved_reference_record_ids": (
                undeclared_unresolved_reference_record_ids
            ),
            "typed_object_reconstruction_complete": True,
            "declared_dependency_semantics_complete": False,
            "m0_role_semantics_complete": False,
            "all_m0_records_dependency_replayed": False,
            "source_authority_complete": False,
            "source_manifest_authority_status": (
                "OPAQUE_CONTENT_ID_BOUND_UNVERIFIED_BY_THIS_MODULE"
            ),
            "code_provenance_complete": False,
            "all_registered_arms_complete": False,
            "next_required_semantic_stage": (
                "M1_SIGNED_REQUEST_BATCH_OUTCOME_CONTROL_REPLAY"
            ),
            "portable_semantic_registry_complete": False,
            "overall_production_complete": False,
            "observer_opened": False,
            "fresh_heldout_accessed": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    @property
    def canonical_bytes(self) -> bytes:
        raw = canonical_json_bytes(self.to_document())
        if len(raw) > MAX_OUTPUT_BYTES:
            _fail("M0 public semantic replay output exceeds its byte cap")
        return raw

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "attestations": [
                item.to_document() for item in self.attestations
            ],
            "result_id": self.result_id,
        }


def replay_v075_portable_public_semantics_v2(
    *,
    repository_root: str | Path,
    portable_bundle_bytes: bytes,
    public_context_closure_bytes: bytes,
) -> V075PortablePublicSemanticReplayResultV2:
    """Replay all eleven M0 roles without target or private inputs."""

    # Both raw byte authorities are always crossed before any artifact-level
    # semantic result is constructed.
    try:
        bundle = (
            portable
            .verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_bundle_bytes
            )
        )
        closure = (
            public_context
            .verify_v075_portable_public_context_evidence_closure_bytes_v2(
                repository_root=repository_root,
                raw=public_context_closure_bytes,
            )
        )
    except Exception as error:
        raise V075PortablePublicSemanticReplayV2InvariantViolation(
            "M0 input failed portable bundle or public-context raw replay"
        ) from error

    resolution = _resolve_public_context(
        repository_root=repository_root,
        closure=closure,
    )
    namespace = resolution.namespace
    store = _RecordStore(bundle.records)
    occurrence, schedule, verification, intents = (
        _replay_initial_authority(
            repository_root=repository_root,
            namespace=namespace,
            store=store,
        )
    )
    if (
        bundle.occurrence_id != occurrence.occurrence_id
        or occurrence.target_tape_namespace_id
        != namespace.target_tape_namespace_id
    ):
        _fail("portable occurrence and public-context namespace differ")

    states = _replay_states(namespace=namespace, store=store)
    catalogues = _replay_catalogues(store=store, states=states)
    rows = _replay_rows(store=store, catalogues=catalogues)
    _assert_schedule_graph_membership(schedule=schedule, rows=rows)
    evidence = _replay_support_evidence(
        namespace=namespace,
        store=store,
        rows=rows,
        states=states,
    )
    epochs = _replay_support_epochs(
        namespace=namespace,
        store=store,
        rows=rows,
        evidence=evidence,
    )
    chains = _replay_support_chains(
        namespace=namespace,
        store=store,
        rows=rows,
        epochs=epochs,
    )
    pairings = _replay_pairing_authorities(
        namespace=namespace,
        store=store,
        rows=rows,
        chains=chains,
    )
    streams = _replay_streams(store=store, pairings=pairings)

    typed_graph = V075PortablePublicM0TypedGraphV2(
        _M0_TYPED_GRAPH_ISSUER,
        bundle.bundle_id,
        closure.closure_id,
        occurrence.occurrence_id,
        namespace.target_tape_namespace_id,
        occurrence,
        schedule,
        verification,
        tuple(intents[item.intent_id] for item in schedule.intents),
        tuple(sorted(states.values(), key=lambda item: item.state_id)),
        tuple(
            sorted(
                catalogues.values(),
                key=lambda item: item.catalogue_id,
            )
        ),
        tuple(
            sorted(rows.values(), key=lambda item: item.row_binding_id)
        ),
        tuple(
            sorted(evidence.values(), key=lambda item: item.evidence_id)
        ),
        tuple(sorted(epochs.values(), key=lambda item: item.epoch_id)),
        tuple(sorted(chains.values(), key=lambda item: item.chain_id)),
        tuple(
            sorted(
                pairings.values(),
                key=lambda item: item.pairing_authority_id,
            )
        ),
        tuple(sorted(streams.values(), key=lambda item: item.stream_id)),
    )

    m0_records = tuple(
        item for item in bundle.records if item.role in _M0_ROLES
    )
    if {item.role for item in m0_records} != _M0_ROLES:
        _fail("portable bundle does not cover every M0 public role")
    attestations = []
    for record in m0_records:
        coverage = _classify_record_dependency_coverage(
            record=record,
            store=store,
        )
        attestations.append(
            V075PortablePublicRecordSemanticAttestationV2(
                _ATTESTATION_ISSUER,
                bundle.bundle_id,
                closure.closure_id,
                closure.repository_binding.binding_id,
                closure.source_manifest.manifest_id,
                namespace.target_tape_namespace_id,
                closure.namespace_public_key_id,
                record.record_id,
                record.index,
                record.role,
                record.semantic_artifact_id,
                hashlib.sha256(
                    record.canonical_artifact_bytes
                ).hexdigest(),
                len(record.canonical_artifact_bytes),
                coverage.declared_record_ids,
                coverage.typed_consumed_record_ids,
                coverage.raw_field_checked_record_ids,
                coverage.unresolved_record_ids,
                coverage.unresolved_roles,
                coverage.undeclared_unresolved_reference_record_ids,
            )
        )
    return V075PortablePublicSemanticReplayResultV2(
        _RESULT_ISSUER,
        bundle.bundle_id,
        bundle.occurrence_id,
        closure.closure_id,
        closure.repository_binding.binding_id,
        closure.source_manifest.manifest_id,
        namespace.target_tape_namespace_id,
        closure.namespace_public_key_id,
        occurrence.arm.value,
        typed_graph,
        tuple(attestations),
    )


def open_v075_production_from_portable_public_semantics_v2(
    **_unused: Any,
) -> NoReturn:
    raise V075PortablePublicSemanticReplayProductionV2NotReady(
        "M0 typed objects were reconstructed, but declared dependency "
        "semantics, source authority, code provenance, arm coverage, and the "
        "remaining "
        "portable semantic registry are incomplete"
    )


__all__ = [
    "ALL_REGISTERED_ARMS_COMPLETE",
    "CODE_PROVENANCE_COMPLETE",
    "DOMAIN_TAGS",
    "FRESH_HELDOUT_ACCESS_ALLOWED",
    "M0_ROLE_ORDER",
    "M0_ROLE_SEMANTICS_COMPLETE",
    "MAX_OUTPUT_BYTES",
    "OBSERVER_OPEN_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PORTABLE_SEMANTIC_REGISTRY_COMPLETE",
    "PRIVATE_INPUT_CHANNELS_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SOURCE_AUTHORITY_COMPLETE",
    "SUPPORTED_ARM_COVERAGE",
    "V075PortablePublicM0TypedGraphV2",
    "V075PortablePublicRecordSemanticAttestationV2",
    "V075PortablePublicRoleReplayStatusV2",
    "V075PortablePublicSemanticReplayProductionV2NotReady",
    "V075PortablePublicSemanticReplayResultV2",
    "V075PortablePublicSemanticReplayV2InvariantViolation",
    "open_v075_production_from_portable_public_semantics_v2",
    "replay_v075_portable_public_semantics_v2",
]
