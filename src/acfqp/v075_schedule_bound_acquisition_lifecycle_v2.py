"""Schedule-bound construction lifecycle for V0-075 initial acquisition.

This leaf joins the preregistered five-arm V2 static schedule to aggregate-only
construction observations.  It replays the exact profile, occurrence slot,
schedule, batch lineage, and (for adaptive arms) the current batch lifecycle,
then checks the complete initial intent DAG against the actual aggregate
batches and support freezes.

The direct arm is deliberately different: its initial schedule ends after
root discovery and before child expansion, while the upstream batch lifecycle
closure requires validation.  Direct therefore carries an explicit typed
``NOT_APPLICABLE`` lifecycle witness and is derived from the exact aggregate
lineage only.  No validation is invented or borrowed.

This module is construction-only.  It performs no target access, per-draw
replay, private-law access, kernel call, planning, J0 comparison, frontier
ranking, dynamic acquisition round, or certificate issuance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_occurrence_lifecycle_authority_v2 as lifecycle_v2
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition_v2
from acfqp import v075_preopen_target_authorization_v2 as preopen_v2
from acfqp import v075_private_observer_boundary_v2 as observer_v2


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.48.0"
PROFILE_KEY = "v075_schedule_bound_acquisition_lifecycle_v2"
MAX_CANONICAL_INPUT_BYTES = 64 * 1024 * 1024

OFFICIAL_EXECUTION_ALLOWED = False
PRODUCTION_AUTHORIZING = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PER_DRAW_REPLAY_ALLOWED = False
TARGET_ACCESS_ALLOWED = False
FRONTIER_RANKING_EXECUTED = False
DYNAMIC_ACQUISITION_ROUNDS_COMPLETE = False

TERMINAL_SCOPE = "CONSTRUCTION_ONLY"
TERMINAL_CLASS = "ATTEMPT_CLOSURE_NONCERTIFICATE"
DIRECT_LIFECYCLE_NOT_APPLICABLE_REASON = (
    "INITIAL_DIRECT_SCHEDULE_IS_DISCOVERY_ONLY_BEFORE_CHILD_EXPANSION"
)
PRODUCTION_BLOCKER = (
    "schedule-bound initial acquisition is construction-only; production "
    "execution, child expansion, frontier ranking, planning, and certificate "
    "authorities are not integrated"
)

DOMAIN_TAGS = {
    "lifecycle_not_applicable": (
        "acfqp:v075-schedule-bound-lifecycle-not-applicable:v2"
    ),
    "construction_authority_replay": (
        "acfqp:v075-schedule-bound-construction-authority-replay:v2"
    ),
    "intent_match": (
        "acfqp:v075-schedule-bound-initial-intent-match:v2"
    ),
    "result": (
        "acfqp:v075-schedule-bound-initial-acquisition-lifecycle:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 schedule-bound lifecycle domains must be unique")


class V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(ValueError):
    """A schedule, lineage, lifecycle, intent, or aggregate failed replay."""


class V075ScheduleBoundAcquisitionProductionV2NotReady(RuntimeError):
    """The construction leaf cannot authorize a production occurrence."""


def _fail(message: str) -> None:
    raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _strict_document(raw: bytes, field_name: str) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CANONICAL_INPUT_BYTES
    ):
        _fail(f"{field_name} bytes are absent or over cap")
    try:
        value = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            f"{field_name} is not strict canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{field_name} is not one canonical JSON object")
    return value


class V075InitialAcquisitionTerminalCodeV2(str, Enum):
    INITIAL_COMPLETE_AWAITING_SOUND_PLANNER = (
        "INITIAL_COMPLETE_AWAITING_SOUND_PLANNER"
    )
    ROOT_DISCOVERY_COMPLETE_AWAITING_CHILD_EXPANSION = (
        "ROOT_DISCOVERY_COMPLETE_AWAITING_CHILD_EXPANSION"
    )


class V075InitialIntentExecutionStatusV2(str, Enum):
    DISCOVERY_BATCH_MATCHED = "DISCOVERY_BATCH_MATCHED"
    DIRECT_DISCOVERY_BATCH_MATCHED = "DIRECT_DISCOVERY_BATCH_MATCHED"
    SUPPORT_FREEZE_MATCHED = "SUPPORT_FREEZE_MATCHED"
    VALIDATION_BATCH_MATCHED = "VALIDATION_BATCH_MATCHED"
    PENDING_DIRECT_CHILD_EXPANSION = "PENDING_DIRECT_CHILD_EXPANSION"


_NOT_APPLICABLE_ISSUER = object()
_AUTHORITY_REPLAY_ISSUER = object()
_MATCH_ISSUER = object()
_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075InitialLifecycleNotApplicableV2:
    """Typed direct-arm witness; absence is never interpreted as N/A."""

    _issuer: object = field(repr=False, compare=False)
    acquisition_profile_id: str
    occurrence_slot_id: str
    schedule_id: str
    occurrence_id: str
    arm: str
    reason: str
    _witness_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.acquisition_profile_id, "N/A acquisition profile"),
            (self.occurrence_slot_id, "N/A occurrence slot"),
            (self.schedule_id, "N/A initial schedule"),
            (self.occurrence_id, "N/A occurrence"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _NOT_APPLICABLE_ISSUER
            or self.arm != acquisition_v2.DIRECT_ARM.value
            or self.reason != DIRECT_LIFECYCLE_NOT_APPLICABLE_REASON
        ):
            _fail("direct lifecycle N/A witness is caller-minted or malformed")
        object.__setattr__(
            self,
            "_witness_id",
            _hash("lifecycle_not_applicable", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_initial_lifecycle_not_applicable.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "acquisition_profile_id": self.acquisition_profile_id,
            "occurrence_slot_id": self.occurrence_slot_id,
            "schedule_id": self.schedule_id,
            "occurrence_id": self.occurrence_id,
            "arm": self.arm,
            "kind": "NOT_APPLICABLE",
            "reason": self.reason,
            "missing_field_equivalent": False,
            "initial_direct_schedule_discovery_only": True,
            "child_expansion_started": False,
            "validation_invented": False,
        }

    @property
    def witness_id(self) -> str:
        return self._witness_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "witness_id": self.witness_id}


@dataclass(frozen=True, slots=True)
class V075ConstructionLineageAuthorityReplayV2:
    """Exact typed construction-authority binding for one lineage."""

    _issuer: object = field(repr=False, compare=False)
    closure_id: str
    occurrence_id: str
    observer_open_binding_id: str
    observer_open_authorization_id: str
    private_reveal_attestation_id: str
    remote_main_anchor_id: str
    target_tape_namespace_id: str
    private_reveal_attestation_bytes_sha256: str
    authorization_bytes_sha256: str
    namespace_bytes_sha256: str
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.closure_id, "authority replay closure"),
            (self.occurrence_id, "authority replay occurrence"),
            (self.observer_open_binding_id, "authority replay binding"),
            (
                self.observer_open_authorization_id,
                "authority replay authorization",
            ),
            (
                self.private_reveal_attestation_id,
                "authority replay reveal attestation",
            ),
            (self.remote_main_anchor_id, "authority replay remote anchor"),
            (
                self.target_tape_namespace_id,
                "authority replay namespace",
            ),
            (
                self.private_reveal_attestation_bytes_sha256,
                "authority replay reveal bytes",
            ),
            (
                self.authorization_bytes_sha256,
                "authority replay authorization bytes",
            ),
            (
                self.namespace_bytes_sha256,
                "authority replay namespace bytes",
            ),
        ):
            _cid(value, label)
        if self._issuer is not _AUTHORITY_REPLAY_ISSUER:
            _fail("construction authority replay witness is caller-minted")
        object.__setattr__(
            self,
            "_replay_id",
            _hash("construction_authority_replay", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_construction_lineage_authority_replay.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "closure_id": self.closure_id,
            "occurrence_id": self.occurrence_id,
            "observer_open_binding_id": self.observer_open_binding_id,
            "observer_open_authorization_id": (
                self.observer_open_authorization_id
            ),
            "private_reveal_attestation_id": (
                self.private_reveal_attestation_id
            ),
            "remote_main_anchor_id": self.remote_main_anchor_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "private_reveal_attestation_bytes_sha256": (
                self.private_reveal_attestation_bytes_sha256
            ),
            "authorization_bytes_sha256": (
                self.authorization_bytes_sha256
            ),
            "namespace_bytes_sha256": self.namespace_bytes_sha256,
            "construction_authority_semantically_replayed": True,
            "repository_authority_replayed": False,
            "namespace_bytes_bound_by_signed_closure": True,
            "private_law_accessed": False,
            "target_accessed": False,
        }

    @property
    def replay_id(self) -> str:
        return self._replay_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "replay_id": self.replay_id}


@dataclass(frozen=True, slots=True)
class V075InitialIntentExecutionMatchV2:
    """One exact static-intent to aggregate-event match."""

    _issuer: object = field(repr=False, compare=False)
    intent_id: str
    intent_kind: acquisition_v2.V075InitialIntentKindV2
    status: V075InitialIntentExecutionStatusV2
    row_binding_id: str
    proposal_view_id: str | None
    dependency_intent_ids: tuple[str, ...]
    batch_id: str | None
    request_id: str | None
    stream_id: str | None
    support_freeze_id: str | None
    lane: str | None
    observer_epoch_index: int | None
    accepted_draw_start: int | None
    accepted_draw_count: int
    accepted_draw_cap: int
    lifecycle_event_sequence_number: int | None
    _match_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.intent_id, "intent match intent"),
            (self.row_binding_id, "intent match row"),
        ):
            _cid(value, label)
        for value, label in (
            (self.proposal_view_id, "intent match proposal"),
            (self.batch_id, "intent match batch"),
            (self.request_id, "intent match request"),
            (self.stream_id, "intent match stream"),
            (self.support_freeze_id, "intent match support freeze"),
        ):
            if value is not None:
                _cid(value, label)
        if type(self.dependency_intent_ids) is not tuple:
            _fail("intent match dependencies are not one tuple")
        for value in self.dependency_intent_ids:
            _cid(value, "intent match dependency")
        pending = (
            self.status
            is V075InitialIntentExecutionStatusV2
            .PENDING_DIRECT_CHILD_EXPANSION
        )
        is_freeze = (
            self.status
            is V075InitialIntentExecutionStatusV2.SUPPORT_FREEZE_MATCHED
        )
        is_batch = self.status in {
            V075InitialIntentExecutionStatusV2.DISCOVERY_BATCH_MATCHED,
            V075InitialIntentExecutionStatusV2.DIRECT_DISCOVERY_BATCH_MATCHED,
            V075InitialIntentExecutionStatusV2.VALIDATION_BATCH_MATCHED,
        }
        is_direct_batch = (
            self.status
            is (
                V075InitialIntentExecutionStatusV2
                .DIRECT_DISCOVERY_BATCH_MATCHED
            )
        )
        if (
            self._issuer is not _MATCH_ISSUER
            or type(self.intent_kind)
            is not acquisition_v2.V075InitialIntentKindV2
            or type(self.status) is not V075InitialIntentExecutionStatusV2
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count < 0
            or type(self.accepted_draw_cap) is not int
            or self.accepted_draw_cap < 0
            or (
                self.lifecycle_event_sequence_number is not None
                and (
                    type(self.lifecycle_event_sequence_number) is not int
                    or self.lifecycle_event_sequence_number <= 0
                )
            )
            or (
                is_batch
                and (
                    self.batch_id is None
                    or self.request_id is None
                    or self.stream_id is None
                    or self.lane not in {"DISCOVERY", "VALIDATION"}
                    or self.observer_epoch_index is None
                    or self.accepted_draw_start is None
                    or self.accepted_draw_count <= 0
                    or self.accepted_draw_cap <= 0
                    or (
                        self.lifecycle_event_sequence_number is None
                        and not is_direct_batch
                    )
                    or (
                        self.lifecycle_event_sequence_number is not None
                        and is_direct_batch
                    )
                )
            )
            or (
                is_freeze
                and (
                    self.intent_kind
                    is not (
                        acquisition_v2.V075InitialIntentKindV2
                        .SUPPORT_PROMOTION_TEMPLATE
                    )
                    or self.batch_id is not None
                    or self.request_id is not None
                    or self.stream_id is not None
                    or self.support_freeze_id is None
                    or self.lane is not None
                    or self.observer_epoch_index != 1
                    or self.accepted_draw_start is not None
                    or self.accepted_draw_count != 0
                    or self.accepted_draw_cap != 0
                    or self.lifecycle_event_sequence_number is None
                )
            )
            or (
                pending
                and (
                    self.intent_kind
                    is not (
                        acquisition_v2.V075InitialIntentKindV2
                        .SUPPORT_PROMOTION_TEMPLATE
                    )
                    or any(
                        value is not None
                        for value in (
                            self.batch_id,
                            self.request_id,
                            self.stream_id,
                            self.support_freeze_id,
                            self.lane,
                            self.observer_epoch_index,
                            self.accepted_draw_start,
                            self.lifecycle_event_sequence_number,
                        )
                    )
                    or self.accepted_draw_count != 0
                    or self.accepted_draw_cap != 0
                )
            )
        ):
            _fail("initial intent execution match is malformed")
        object.__setattr__(
            self,
            "_match_id",
            _hash("intent_match", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_initial_intent_execution_match.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "intent_id": self.intent_id,
            "intent_kind": self.intent_kind.value,
            "status": self.status.value,
            "row_binding_id": self.row_binding_id,
            "proposal_view_id": self.proposal_view_id,
            "dependency_intent_ids": list(self.dependency_intent_ids),
            "batch_id": self.batch_id,
            "request_id": self.request_id,
            "stream_id": self.stream_id,
            "support_freeze_id": self.support_freeze_id,
            "lane": self.lane,
            "observer_epoch_index": self.observer_epoch_index,
            "accepted_draw_start": self.accepted_draw_start,
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_cap": self.accepted_draw_cap,
            "lifecycle_event_sequence_number": (
                self.lifecycle_event_sequence_number
            ),
            "proposal_input_bound": self.proposal_view_id is not None,
            "proposal_ranking_executed": False,
            "per_draw_records_read": 0,
        }

    @property
    def match_id(self) -> str:
        return self._match_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "match_id": self.match_id}


@dataclass(frozen=True, slots=True)
class V075ScheduleBoundInitialAcquisitionCountersV2:
    """Exact O(batch + outcome-aggregate) replay counters."""

    batch_count: int
    outcome_aggregate_count: int
    discovery_batch_count: int
    validation_batch_count: int
    support_freeze_count: int
    support_evidence_count: int
    lifecycle_event_count: int
    intent_match_count: int
    pending_intent_count: int

    def __post_init__(self) -> None:
        values = (
            self.batch_count,
            self.outcome_aggregate_count,
            self.discovery_batch_count,
            self.validation_batch_count,
            self.support_freeze_count,
            self.support_evidence_count,
            self.lifecycle_event_count,
            self.intent_match_count,
            self.pending_intent_count,
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.batch_count <= 0
            or self.outcome_aggregate_count <= 0
            or self.batch_count
            != self.discovery_batch_count + self.validation_batch_count
        ):
            _fail("initial acquisition replay counters do not reconcile")

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_schedule_bound_initial_acquisition_counters.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "batch_count": self.batch_count,
            "outcome_aggregate_count": self.outcome_aggregate_count,
            "discovery_batch_count": self.discovery_batch_count,
            "validation_batch_count": self.validation_batch_count,
            "support_freeze_count": self.support_freeze_count,
            "support_evidence_count": self.support_evidence_count,
            "lifecycle_event_count": self.lifecycle_event_count,
            "intent_match_count": self.intent_match_count,
            "pending_intent_count": self.pending_intent_count,
            "asymptotic_replay_work": "O(BATCH_COUNT+OUTCOME_AGGREGATE_COUNT)",
            "per_draw_records_read": 0,
            "private_records_read": 0,
            "target_calls": 0,
            "kernel_calls": 0,
            "j0_calls": 0,
            "planner_calls": 0,
        }


LifecycleWitnessV2 = (
    lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2
    | V075InitialLifecycleNotApplicableV2
)


@dataclass(frozen=True, slots=True)
class _DerivedInitialLifecycle:
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2
    lineage: batched_v2.V075BatchOccurrenceLineageV2
    authority_replay: V075ConstructionLineageAuthorityReplayV2
    current_lifecycle: LifecycleWitnessV2
    lifecycle_verification: (
        lifecycle_v2.V075BatchOccurrenceLifecycleVerificationV2 | None
    )
    matches: tuple[V075InitialIntentExecutionMatchV2, ...]
    counters: V075ScheduleBoundInitialAcquisitionCountersV2
    terminal_code: V075InitialAcquisitionTerminalCodeV2


def _replay_profile(
    claimed: acquisition_v2.V075FiveArmAcquisitionProfileV2,
) -> acquisition_v2.V075FiveArmAcquisitionProfileV2:
    if type(claimed) is not acquisition_v2.V075FiveArmAcquisitionProfileV2:
        _fail("schedule-bound lifecycle requires one exact V2 profile")
    try:
        expected = acquisition_v2.freeze_v075_five_arm_acquisition_profile_v2(
            namespace=claimed.namespace
        )
    except Exception as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            "five-arm profile semantic replay failed"
        ) from error
    if (
        expected.profile_id != claimed.profile_id
        or expected.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("five-arm profile differs from exact semantic replay")
    return expected


def _replay_schedule(
    claimed: acquisition_v2.V075InitialAcquisitionScheduleV2,
) -> acquisition_v2.V075InitialAcquisitionScheduleV2:
    if (
        type(claimed)
        is not acquisition_v2.V075InitialAcquisitionScheduleV2
    ):
        _fail("schedule-bound lifecycle requires one exact typed schedule")
    try:
        expected = acquisition_v2.V075InitialAcquisitionScheduleV2(
            acquisition_v2._SCHEDULE_ISSUER,  # type: ignore[attr-defined]
            claimed.profile,
            claimed.occurrence,
            claimed.proposal_view,
            claimed.proposal_use_rule,
            claimed.intents,
        )
    except Exception as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            "initial schedule semantic replay failed"
        ) from error
    if (
        expected.schedule_id != claimed.schedule_id
        or expected.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("initial schedule differs from exact semantic replay")
    return expected


def _replay_construction_authority(
    *,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    construction_authority: preopen_v2.V075ObserverOpenAuthorizationV2,
) -> V075ConstructionLineageAuthorityReplayV2:
    if (
        type(lineage) is not batched_v2.V075BatchOccurrenceLineageV2
        or type(construction_authority)
        is not preopen_v2.V075ObserverOpenAuthorizationV2
    ):
        _fail("construction authority replay inputs are absent or untyped")
    claimed_binding = lineage.closure.authority_binding
    try:
        claimed_reveal = construction_authority.private_reveal_attestation
        reveal = preopen_v2.V075PrivateRevealAttestationV2(
            preopen_v2._REVEAL_ISSUER,  # type: ignore[attr-defined]
            construction_authority.anchor,
            claimed_reveal.private_verification_external_id,
            claimed_reveal.observer_signature_hex,
        )
        claimed_tracked = construction_authority.tracked_blobs
        tracked = preopen_v2.V075TrackedPreopenBlobClosureV2(
            preopen_v2._BLOB_CLOSURE_ISSUER,  # type: ignore[attr-defined]
            construction_authority.anchor,
            claimed_tracked.manifest_bytes_sha256,
            claimed_tracked.final_preregistration_bytes_sha256,
        )
        authority = preopen_v2.V075ObserverOpenAuthorizationV2(
            preopen_v2._AUTHORIZATION_ISSUER,  # type: ignore[attr-defined]
            construction_authority.anchor,
            tracked,
            construction_authority.signer_registry,
            construction_authority.opaque_environment_commitment,
            reveal,
        )
        binding = observer_v2._require_exact_v2_binding(  # type: ignore[attr-defined]
            authority=authority,
            namespace=claimed_binding.namespace,
        )
    except Exception as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            "construction authority semantic replay failed"
        ) from error
    if (
        authority.canonical_bytes != construction_authority.canonical_bytes
        or reveal.canonical_bytes != claimed_reveal.canonical_bytes
        or canonical_json_bytes(binding.to_document())
        != canonical_json_bytes(claimed_binding.to_document())
    ):
        _fail("construction aggregate carries a foreign authority binding")
    return V075ConstructionLineageAuthorityReplayV2(
        _AUTHORITY_REPLAY_ISSUER,
        lineage.closure.closure_id,
        lineage.closure.occurrence_id,
        binding.binding_id,
        binding.authorization_id,
        binding.private_reveal_attestation_id,
        binding.remote_main_anchor_id,
        binding.namespace.target_tape_namespace_id,
        hashlib.sha256(reveal.canonical_bytes).hexdigest(),
        hashlib.sha256(authority.canonical_bytes).hexdigest(),
        hashlib.sha256(binding.namespace.canonical_bytes).hexdigest(),
    )


def _replay_authority_witness(
    claimed: V075ConstructionLineageAuthorityReplayV2,
) -> V075ConstructionLineageAuthorityReplayV2:
    if type(claimed) is not V075ConstructionLineageAuthorityReplayV2:
        _fail("construction authority replay witness is untyped")
    try:
        expected = V075ConstructionLineageAuthorityReplayV2(
            _AUTHORITY_REPLAY_ISSUER,
            claimed.closure_id,
            claimed.occurrence_id,
            claimed.observer_open_binding_id,
            claimed.observer_open_authorization_id,
            claimed.private_reveal_attestation_id,
            claimed.remote_main_anchor_id,
            claimed.target_tape_namespace_id,
            claimed.private_reveal_attestation_bytes_sha256,
            claimed.authorization_bytes_sha256,
            claimed.namespace_bytes_sha256,
        )
    except Exception as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            "construction authority replay witness is invalid"
        ) from error
    if (
        expected.replay_id != claimed.replay_id
        or expected.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("construction authority replay witness differs from replay")
    return expected


def _replay_lineage(
    claimed: batched_v2.V075BatchOccurrenceLineageV2,
    *,
    authority_replay: V075ConstructionLineageAuthorityReplayV2,
) -> batched_v2.V075BatchOccurrenceLineageV2:
    if (
        type(claimed) is not batched_v2.V075BatchOccurrenceLineageV2
        or claimed.scope
        is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail("schedule-bound lifecycle requires construction aggregate lineage")
    try:
        replayed_authority = _replay_authority_witness(authority_replay)
        streams = _semantic_streams(claimed)
        closure = observer_v2.load_observer_batch_journal_closure_bytes_v2(
            raw=claimed.closure.canonical_bytes,
            authority_binding=claimed.closure.authority_binding,
            known_stream_identities=streams,
        )
        batches = tuple(entry.batch for entry in closure.entries)
        binding = closure.authority_binding
        closure_verification = (
            observer_v2.V075ObserverBatchClosureVerificationV2(
                observer_v2._BATCH_CLOSURE_VERIFICATION_ISSUER,  # type: ignore[attr-defined]
                closure.closure_id,
                closure.occurrence_id,
                tuple(batch.batch_id for batch in batches),
                binding.binding_id,
                binding.authorization_id,
                binding.private_reveal_attestation_id,
                binding.remote_main_anchor_id,
                binding.namespace.target_tape_namespace_id,
                len(batches),
                sum(
                    batch.request.accepted_draw_count
                    for batch in batches
                ),
                len(streams),
            )
        )
        if canonical_json_bytes(
            closure_verification.to_document()
        ) != canonical_json_bytes(
            claimed.closure_verification.to_document()
        ):
            _fail(
                "construction aggregate closure verification differs "
                "from signed aggregate replay"
            )
        namespace_bytes_sha256 = hashlib.sha256(
            binding.namespace.canonical_bytes
        ).hexdigest()
        if (
            replayed_authority.closure_id != closure.closure_id
            or replayed_authority.occurrence_id != closure.occurrence_id
            or replayed_authority.observer_open_binding_id
            != binding.binding_id
            or replayed_authority.observer_open_authorization_id
            != binding.authorization_id
            or replayed_authority.private_reveal_attestation_id
            != binding.private_reveal_attestation_id
            or replayed_authority.remote_main_anchor_id
            != binding.remote_main_anchor_id
            or replayed_authority.target_tape_namespace_id
            != binding.namespace.target_tape_namespace_id
            or replayed_authority.namespace_bytes_sha256
            != namespace_bytes_sha256
            or claimed.private_reveal_attestation_bytes_sha256
            != replayed_authority.private_reveal_attestation_bytes_sha256
            or claimed.authorization_bytes_sha256
            != replayed_authority.authorization_bytes_sha256
            or claimed.namespace_bytes_sha256
            != replayed_authority.namespace_bytes_sha256
        ):
            _fail(
                "construction aggregate authority IDs or byte digests "
                "differ from exact repository replay"
            )
        expected = batched_v2.V075BatchOccurrenceLineageV2(
            batched_v2._CONSTRUCTION_LINEAGE_ISSUER,  # type: ignore[attr-defined]
            claimed.scope,
            claimed.occurrence_identity,
            closure,
            closure_verification,
            claimed.public_verifications,
            claimed.sequence_verifications,
            replayed_authority.private_reveal_attestation_bytes_sha256,
            replayed_authority.authorization_bytes_sha256,
            replayed_authority.namespace_bytes_sha256,
            hashlib.sha256(closure.canonical_bytes).hexdigest(),
        )
    except Exception as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            "construction aggregate lineage semantic replay failed"
        ) from error
    if (
        expected.lineage_id != claimed.lineage_id
        or expected.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("construction aggregate lineage differs from exact replay")
    return expected


def _semantic_streams(
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
) -> tuple[Any, ...]:
    streams = {
        batch.request.stream_identity.stream_id: batch.request.stream_identity
        for batch in lineage.batches
    }
    if len(streams) != len(lineage.sequence_verifications):
        _fail("aggregate lineage semantic stream registry is incomplete")
    return tuple(streams[key] for key in sorted(streams))


def _replay_lifecycle(
    claimed: lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2,
    *,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
) -> tuple[
    lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2,
    lifecycle_v2.V075BatchOccurrenceLifecycleVerificationV2,
]:
    if (
        type(claimed)
        is not lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2
        or claimed.scope
        is not lifecycle_v2.V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail("adaptive initial acquisition requires construction lifecycle")
    try:
        expected, verification = (
            lifecycle_v2.verify_v075_batch_occurrence_lifecycle_bytes_v2(
                lifecycle_bytes=claimed.canonical_bytes,
                lineage_bytes=lineage.canonical_bytes,
                batch_closure_bytes=lineage.closure.canonical_bytes,
                known_stream_identities=_semantic_streams(lineage),
            )
        )
    except Exception as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            "construction lifecycle semantic replay failed"
        ) from error
    if (
        expected.closure_id != claimed.closure_id
        or expected.canonical_bytes != claimed.canonical_bytes
    ):
        _fail("construction lifecycle differs from aggregate replay")
    return expected, verification


def _expected_na(
    *,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
) -> V075InitialLifecycleNotApplicableV2:
    return V075InitialLifecycleNotApplicableV2(
        _NOT_APPLICABLE_ISSUER,
        profile.profile_id,
        expected_slot.slot_id,
        schedule.schedule_id,
        schedule.occurrence.occurrence_id,
        schedule.occurrence.arm.value,
        DIRECT_LIFECYCLE_NOT_APPLICABLE_REASON,
    )


def freeze_v075_direct_initial_lifecycle_not_applicable_v2(
    *,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
) -> V075InitialLifecycleNotApplicableV2:
    """Freeze the exact typed N/A witness for a direct discovery-only stage."""

    replayed_profile = _replay_profile(profile)
    replayed_schedule = _replay_schedule(schedule)
    slot = replayed_profile.occurrence_slot_for(
        context_id=replayed_schedule.occurrence.context_id,
        arm=replayed_schedule.occurrence.arm,
    )
    if (
        replayed_schedule.occurrence.arm is not acquisition_v2.DIRECT_ARM
        or replayed_schedule.profile.canonical_bytes
        != replayed_profile.canonical_bytes
        or type(expected_slot)
        is not acquisition_v2.V075PreregisteredOccurrenceSlotV2
        or canonical_json_bytes(expected_slot.to_document())
        != canonical_json_bytes(slot.to_document())
    ):
        _fail("direct lifecycle N/A inputs are transplanted or non-direct")
    return _expected_na(
        profile=replayed_profile,
        expected_slot=slot,
        schedule=replayed_schedule,
    )


def _proposal_id(
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
) -> str | None:
    return (
        None
        if schedule.proposal_view is None
        else schedule.proposal_view.proposal_view_id
    )


def _match_batch(
    *,
    intent: acquisition_v2.V075InitialRowIntentV2,
    batch: Any,
    lifecycle_event: lifecycle_v2.V075BatchLifecycleEventV2 | None,
    proposal_view_id: str | None,
) -> V075InitialIntentExecutionMatchV2:
    request = batch.request
    stream = request.stream_identity
    expected_lane = (
        "DISCOVERY"
        if intent.kind
        is acquisition_v2.V075InitialIntentKindV2.ROOT_DISCOVERY
        else "VALIDATION"
    )
    expected_status = (
        V075InitialIntentExecutionStatusV2.DISCOVERY_BATCH_MATCHED
        if expected_lane == "DISCOVERY"
        else V075InitialIntentExecutionStatusV2.VALIDATION_BATCH_MATCHED
    )
    if (
        stream.row_binding != intent.row_binding
        or stream.row_binding_id != intent.row_binding.row_binding_id
        or stream.lane.value != expected_lane
        or stream.observer_epoch_index != intent.observer_epoch_index
        or request.accepted_draw_start != intent.accepted_draw_start
        or request.accepted_draw_count != intent.accepted_draw_count
        or request.accepted_draw_cap != intent.accepted_draw_cap
        or request.accepted_draw_end
        != intent.accepted_draw_start + intent.accepted_draw_count - 1
        or request.occurrence_id != intent.occurrence_id
        or stream.target_tape_namespace_id != intent.target_tape_namespace_id
        or stream.context_id != intent.occurrence.context_id
        or stream.arm != intent.arm.value
        or stream.row_binding.remaining_horizon != 2
        or lifecycle_event is None
        or lifecycle_event.kind.value != f"{expected_lane}_BATCH"
        or lifecycle_event.batch_id != batch.batch_id
        or lifecycle_event.request_id != request.request_id
        or lifecycle_event.stream_id != stream.stream_id
        or lifecycle_event.row_binding_id != stream.row_binding_id
        or lifecycle_event.observer_epoch_index
        != stream.observer_epoch_index
        or lifecycle_event.accepted_draw_count
        != request.accepted_draw_count
        or (
            expected_lane == "DISCOVERY"
            and lifecycle_event.support_freeze_id is not None
        )
    ):
        _fail("actual aggregate batch differs from its static row intent")
    return V075InitialIntentExecutionMatchV2(
        _MATCH_ISSUER,
        intent.intent_id,
        intent.kind,
        expected_status,
        intent.row_binding.row_binding_id,
        proposal_view_id,
        intent.dependency_intent_ids,
        batch.batch_id,
        request.request_id,
        stream.stream_id,
        lifecycle_event.support_freeze_id,
        expected_lane,
        stream.observer_epoch_index,
        request.accepted_draw_start,
        request.accepted_draw_count,
        request.accepted_draw_cap,
        lifecycle_event.sequence_number,
    )


def _match_direct_discovery(
    *,
    intent: acquisition_v2.V075InitialRowIntentV2,
    batch: Any,
) -> V075InitialIntentExecutionMatchV2:
    request = batch.request
    stream = request.stream_identity
    if (
        intent.kind
        is not acquisition_v2.V075InitialIntentKindV2.ROOT_DISCOVERY
        or stream.row_binding != intent.row_binding
        or stream.row_binding_id != intent.row_binding.row_binding_id
        or stream.lane.value != "DISCOVERY"
        or stream.observer_epoch_index != 0
        or request.accepted_draw_start != 1
        or request.accepted_draw_count != 64
        or request.accepted_draw_count != intent.accepted_draw_count
        or request.accepted_draw_cap != intent.accepted_draw_cap
        or request.occurrence_id != intent.occurrence_id
        or stream.target_tape_namespace_id != intent.target_tape_namespace_id
        or stream.context_id != intent.occurrence.context_id
        or stream.arm != acquisition_v2.DIRECT_ARM.value
        or stream.row_binding.remaining_horizon != 2
    ):
        _fail("direct root discovery aggregate differs from static intent")
    return V075InitialIntentExecutionMatchV2(
        _MATCH_ISSUER,
        intent.intent_id,
        intent.kind,
        (
            V075InitialIntentExecutionStatusV2
            .DIRECT_DISCOVERY_BATCH_MATCHED
        ),
        intent.row_binding.row_binding_id,
        None,
        intent.dependency_intent_ids,
        batch.batch_id,
        request.request_id,
        stream.stream_id,
        None,
        "DISCOVERY",
        0,
        1,
        64,
        intent.accepted_draw_cap,
        None,
    )


def _derive(
    *,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    authority_replay: V075ConstructionLineageAuthorityReplayV2,
    current_lifecycle: LifecycleWitnessV2,
) -> _DerivedInitialLifecycle:
    replayed_profile = _replay_profile(profile)
    replayed_schedule = _replay_schedule(schedule)
    replayed_authority = _replay_authority_witness(authority_replay)
    replayed_lineage = _replay_lineage(
        lineage,
        authority_replay=replayed_authority,
    )
    occurrence = replayed_schedule.occurrence
    slot = replayed_profile.occurrence_slot_for(
        context_id=occurrence.context_id,
        arm=occurrence.arm,
    )
    if (
        replayed_schedule.profile.canonical_bytes
        != replayed_profile.canonical_bytes
        or type(expected_slot)
        is not acquisition_v2.V075PreregisteredOccurrenceSlotV2
        or canonical_json_bytes(expected_slot.to_document())
        != canonical_json_bytes(slot.to_document())
        or slot.target_tape_namespace_id
        != occurrence.target_tape_namespace_id
        or slot.threshold_profile_id != occurrence.threshold_profile_id
        or slot.cap_profile_id != occurrence.cap_profile_id
        or slot.occurrence_ordinal != occurrence.occurrence_ordinal
        or slot.arm is not occurrence.arm
        or replayed_lineage.occurrence_identity.to_document()
        != occurrence.to_document()
    ):
        _fail(
            "profile, slot, schedule, occurrence, or aggregate lineage "
            "was transplanted"
        )

    batches = replayed_lineage.batches
    batch_by_key: dict[tuple[str, str, int], Any] = {}
    for batch in batches:
        stream = batch.request.stream_identity
        key = (
            stream.row_binding_id,
            stream.lane.value,
            stream.observer_epoch_index,
        )
        if key in batch_by_key:
            _fail("one static initial row intent was split across batches")
        batch_by_key[key] = batch
    outcome_count = sum(len(batch.outcomes) for batch in batches)
    proposal_view_id = _proposal_id(replayed_schedule)
    discoveries = tuple(
        item
        for item in replayed_schedule.intents
        if item.kind
        is acquisition_v2.V075InitialIntentKindV2.ROOT_DISCOVERY
    )
    promotions = tuple(
        item
        for item in replayed_schedule.intents
        if item.kind
        is (
            acquisition_v2.V075InitialIntentKindV2
            .SUPPORT_PROMOTION_TEMPLATE
        )
    )
    validations = tuple(
        item
        for item in replayed_schedule.intents
        if item.kind
        is acquisition_v2.V075InitialIntentKindV2.ROOT_VALIDATION
    )
    matches: list[V075InitialIntentExecutionMatchV2] = []

    if occurrence.arm is acquisition_v2.DIRECT_ARM:
        if type(current_lifecycle) is not V075InitialLifecycleNotApplicableV2:
            _fail("direct initial acquisition requires explicit typed N/A")
        expected_na = _expected_na(
            profile=replayed_profile,
            expected_slot=slot,
            schedule=replayed_schedule,
        )
        if current_lifecycle.canonical_bytes != expected_na.canonical_bytes:
            _fail("direct lifecycle N/A witness differs from exact replay")
        if validations or proposal_view_id is not None:
            _fail("direct initial schedule invented validation or proposal")
        expected_batch_keys = tuple(
            (
                item.row_binding.row_binding_id,
                "DISCOVERY",
                0,
            )
            for item in discoveries
        )
        if tuple(batch_by_key) != expected_batch_keys:
            _fail("direct initial batches are omitted, reordered, or non-discovery")
        for intent in discoveries:
            matches.append(
                _match_direct_discovery(
                    intent=intent,
                    batch=batch_by_key[
                        (intent.row_binding.row_binding_id, "DISCOVERY", 0)
                    ],
                )
            )
        for intent in promotions:
            matches.append(
                V075InitialIntentExecutionMatchV2(
                    _MATCH_ISSUER,
                    intent.intent_id,
                    intent.kind,
                    (
                        V075InitialIntentExecutionStatusV2
                        .PENDING_DIRECT_CHILD_EXPANSION
                    ),
                    intent.row_binding.row_binding_id,
                    None,
                    intent.dependency_intent_ids,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    0,
                    0,
                    None,
                )
            )
        if (
            tuple(batch.batch_id for batch in batches)
            != tuple(
                batch_by_key[key].batch_id for key in expected_batch_keys
            )
            or replayed_lineage.accepted_draw_count
            != len(discoveries) * 64
        ):
            _fail("direct root discovery batch order or draw total changed")
        counters = V075ScheduleBoundInitialAcquisitionCountersV2(
            len(batches),
            outcome_count,
            len(discoveries),
            0,
            0,
            0,
            0,
            len(discoveries),
            len(promotions),
        )
        return _DerivedInitialLifecycle(
            replayed_profile,
            slot,
            replayed_schedule,
            replayed_lineage,
            replayed_authority,
            expected_na,
            None,
            tuple(matches),
            counters,
            (
                V075InitialAcquisitionTerminalCodeV2
                .ROOT_DISCOVERY_COMPLETE_AWAITING_CHILD_EXPANSION
            ),
        )

    if (
        type(current_lifecycle)
        is not lifecycle_v2.V075BatchOccurrenceLifecycleClosureV2
        or proposal_view_id is None
    ):
        _fail("adaptive initial acquisition lacks lifecycle or proposal input")
    replayed_lifecycle, lifecycle_verification = _replay_lifecycle(
        current_lifecycle,
        lineage=replayed_lineage,
    )
    expected_batch_keys = tuple(
        (
            item.row_binding.row_binding_id,
            "DISCOVERY",
            0,
        )
        for item in discoveries
    ) + tuple(
        (
            item.row_binding.row_binding_id,
            "VALIDATION",
            1,
        )
        for item in validations
    )
    if tuple(batch_by_key) != expected_batch_keys:
        _fail("adaptive initial batches are omitted, reordered, or foreign")
    event_by_batch = {
        event.batch_id: event
        for event in replayed_lifecycle.events
        if event.batch_id is not None
    }
    freeze_by_row = {
        item.row_binding_id: item
        for item in replayed_lifecycle.support_freezes
        if item.validation_epoch_index == 1
    }
    freeze_event_by_id = {
        event.support_freeze_id: event
        for event in replayed_lifecycle.events
        if event.kind
        is lifecycle_v2.V075BatchLifecycleEventKindV2.SUPPORT_FREEZE
    }
    if (
        len(event_by_batch) != len(batches)
        or len(freeze_by_row) != len(promotions)
        or len(freeze_event_by_id) != len(promotions)
    ):
        _fail("adaptive lifecycle omits or duplicates initial events/freezes")
    discovery_batch_by_row: dict[str, Any] = {}
    for intent in discoveries:
        key = (intent.row_binding.row_binding_id, "DISCOVERY", 0)
        batch = batch_by_key[key]
        discovery_batch_by_row[intent.row_binding.row_binding_id] = batch
        matches.append(
            _match_batch(
                intent=intent,
                batch=batch,
                lifecycle_event=event_by_batch.get(batch.batch_id),
                proposal_view_id=proposal_view_id,
            )
        )
    for intent in promotions:
        row_id = intent.row_binding.row_binding_id
        freeze = freeze_by_row.get(row_id)
        discovery = discovery_batch_by_row.get(row_id)
        freeze_event = (
            None if freeze is None else freeze_event_by_id.get(freeze.freeze_id)
        )
        if (
            freeze is None
            or discovery is None
            or freeze.source_discovery_batch_ids != (discovery.batch_id,)
            or not freeze.support_evidence_ids
            or not freeze.typed_model_support_evidence_ids
            or freeze_event is None
            or freeze_event.row_binding_id != row_id
            or freeze_event.observer_epoch_index != 1
        ):
            _fail("adaptive support freeze is missing, foreign, or incomplete")
        matches.append(
            V075InitialIntentExecutionMatchV2(
                _MATCH_ISSUER,
                intent.intent_id,
                intent.kind,
                V075InitialIntentExecutionStatusV2.SUPPORT_FREEZE_MATCHED,
                row_id,
                proposal_view_id,
                intent.dependency_intent_ids,
                None,
                None,
                None,
                freeze.freeze_id,
                None,
                1,
                None,
                0,
                0,
                freeze_event.sequence_number,
            )
        )
    for intent in validations:
        key = (intent.row_binding.row_binding_id, "VALIDATION", 1)
        batch = batch_by_key[key]
        match = _match_batch(
            intent=intent,
            batch=batch,
            lifecycle_event=event_by_batch.get(batch.batch_id),
            proposal_view_id=proposal_view_id,
        )
        freeze = freeze_by_row[intent.row_binding.row_binding_id]
        if (
            match.support_freeze_id != freeze.freeze_id
            or match.lifecycle_event_sequence_number
            <= freeze_event_by_id[freeze.freeze_id].sequence_number
        ):
            _fail("validation batch did not follow its exact support freeze")
        matches.append(match)

    expected_row_ids = tuple(
        sorted(item.row_binding.row_binding_id for item in discoveries)
    )
    expected_rounds = tuple((row_id, (1,)) for row_id in expected_row_ids)
    expected_draws = sum(
        item.accepted_draw_count
        for item in (*discoveries, *validations)
    )
    if (
        replayed_lifecycle.lineage_id != replayed_lineage.lineage_id
        or replayed_lifecycle.batch_ids
        != tuple(batch.batch_id for batch in batches)
        or replayed_lifecycle.accepted_draw_count != expected_draws
        or replayed_lineage.accepted_draw_count != expected_draws
        or replayed_lifecycle.required_row_binding_ids != expected_row_ids
        or replayed_lifecycle.required_round_schedule != expected_rounds
        or len(replayed_lifecycle.events)
        != len(batches) + len(promotions)
        or tuple(batch.batch_id for batch in batches)
        != tuple(batch_by_key[key].batch_id for key in expected_batch_keys)
    ):
        _fail("adaptive initial lifecycle coverage or aggregate order changed")
    counters = V075ScheduleBoundInitialAcquisitionCountersV2(
        len(batches),
        outcome_count,
        len(discoveries),
        len(validations),
        len(replayed_lifecycle.support_freezes),
        len(replayed_lifecycle.support_evidence),
        len(replayed_lifecycle.events),
        len(matches),
        0,
    )
    return _DerivedInitialLifecycle(
        replayed_profile,
        slot,
        replayed_schedule,
        replayed_lineage,
        replayed_authority,
        replayed_lifecycle,
        lifecycle_verification,
        tuple(matches),
        counters,
        (
            V075InitialAcquisitionTerminalCodeV2
            .INITIAL_COMPLETE_AWAITING_SOUND_PLANNER
        ),
    )


@dataclass(frozen=True, slots=True)
class V075ScheduleBoundInitialAcquisitionLifecycleV2:
    """Exact construction-only closure of the static initial schedule."""

    _issuer: object = field(repr=False, compare=False)
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2 = field(repr=False)
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2 = field(
        repr=False
    )
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2 = field(
        repr=False
    )
    lineage: batched_v2.V075BatchOccurrenceLineageV2 = field(repr=False)
    authority_replay: V075ConstructionLineageAuthorityReplayV2 = field(
        repr=False
    )
    current_lifecycle: LifecycleWitnessV2 = field(repr=False)
    upstream_lifecycle_verification: (
        lifecycle_v2.V075BatchOccurrenceLifecycleVerificationV2 | None
    ) = field(repr=False)
    intent_matches: tuple[V075InitialIntentExecutionMatchV2, ...]
    counters: V075ScheduleBoundInitialAcquisitionCountersV2
    terminal_code: V075InitialAcquisitionTerminalCodeV2
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _RESULT_ISSUER
            or type(self.intent_matches) is not tuple
            or type(self.counters)
            is not V075ScheduleBoundInitialAcquisitionCountersV2
            or type(self.terminal_code)
            is not V075InitialAcquisitionTerminalCodeV2
        ):
            _fail("schedule-bound initial lifecycle is caller-minted")
        expected = _derive(
            profile=self.profile,
            expected_slot=self.expected_slot,
            schedule=self.schedule,
            lineage=self.lineage,
            authority_replay=self.authority_replay,
            current_lifecycle=self.current_lifecycle,
        )
        expected_verification_document = (
            None
            if expected.lifecycle_verification is None
            else expected.lifecycle_verification.to_document()
        )
        actual_verification_document = (
            None
            if self.upstream_lifecycle_verification is None
            else self.upstream_lifecycle_verification.to_document()
        )
        if (
            self.profile.canonical_bytes != expected.profile.canonical_bytes
            or canonical_json_bytes(self.expected_slot.to_document())
            != canonical_json_bytes(expected.expected_slot.to_document())
            or self.schedule.canonical_bytes != expected.schedule.canonical_bytes
            or self.lineage.canonical_bytes != expected.lineage.canonical_bytes
            or self.authority_replay.canonical_bytes
            != expected.authority_replay.canonical_bytes
            or self.current_lifecycle.canonical_bytes
            != expected.current_lifecycle.canonical_bytes
            or actual_verification_document != expected_verification_document
            or self.intent_matches != expected.matches
            or self.counters != expected.counters
            or self.terminal_code is not expected.terminal_code
        ):
            _fail("schedule-bound initial lifecycle differs from exact replay")
        object.__setattr__(
            self,
            "_result_id",
            _hash("result", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        direct = self.schedule.occurrence.arm is acquisition_v2.DIRECT_ARM
        return {
            "schema": (
                "acfqp.v075_schedule_bound_initial_acquisition_lifecycle.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "terminal_scope": TERMINAL_SCOPE,
            "terminal_class": TERMINAL_CLASS,
            "terminal_code": self.terminal_code.value,
            "acquisition_profile_id": self.profile.profile_id,
            "occurrence_slot_id": self.expected_slot.slot_id,
            "schedule_id": self.schedule.schedule_id,
            "occurrence_id": self.schedule.occurrence.occurrence_id,
            "target_tape_namespace_id": (
                self.schedule.occurrence.target_tape_namespace_id
            ),
            "context_id": self.schedule.occurrence.context_id,
            "arm": self.schedule.occurrence.arm.value,
            "lineage_id": self.lineage.lineage_id,
            "construction_authority_replay_id": (
                self.authority_replay.replay_id
            ),
            "current_lifecycle_kind": (
                "NOT_APPLICABLE"
                if direct
                else "CONSTRUCTION_LIFECYCLE_CLOSURE"
            ),
            "current_lifecycle_id": (
                self.current_lifecycle.witness_id
                if direct
                else self.current_lifecycle.closure_id
            ),
            "upstream_lifecycle_verification_id": (
                None
                if self.upstream_lifecycle_verification is None
                else self.upstream_lifecycle_verification.verification_id
            ),
            "proposal_view_id": _proposal_id(self.schedule),
            "proposal_input_bound": not direct,
            "proposal_ranking_executed": False,
            "intent_match_ids": [
                item.match_id for item in self.intent_matches
            ],
            "construction_only": True,
            "attempt_closure_noncertificate": True,
            "full_acquisition_complete": False,
            "dynamic_acquisition_rounds_complete": False,
            "child_expansion_complete": False,
            "sound_planner_executed": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "official_execution_allowed": False,
            "production_authorizing": False,
            "scientific_endpoint_credit_allowed": False,
            "per_draw_records_read": 0,
            "private_material_read": False,
            "target_accessed": False,
            "kernel_calls": 0,
            "j0_calls": 0,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "profile": self.profile.to_document(),
            "expected_slot": self.expected_slot.to_document(),
            "schedule": self.schedule.to_document(),
            "lineage": self.lineage.to_document(),
            "construction_authority_replay": (
                self.authority_replay.to_document()
            ),
            "current_lifecycle": self.current_lifecycle.to_document(),
            "upstream_lifecycle_verification": (
                None
                if self.upstream_lifecycle_verification is None
                else self.upstream_lifecycle_verification.to_document()
            ),
            "intent_matches": [
                item.to_document() for item in self.intent_matches
            ],
            "counters": self.counters.to_document(),
            "result_id": self.result_id,
        }


def freeze_v075_schedule_bound_initial_acquisition_lifecycle_v2(
    *,
    repository_root: str | Path,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    construction_authority: preopen_v2.V075ObserverOpenAuthorizationV2,
    current_lifecycle: LifecycleWitnessV2,
) -> V075ScheduleBoundInitialAcquisitionLifecycleV2:
    """Freeze one exact construction-only initial acquisition terminal."""

    try:
        schedule = acquisition_v2.replay_v075_initial_acquisition_schedule_v2(
            repository_root=repository_root,
            namespace=profile.namespace,
            claimed=schedule,
        )
    except Exception as error:
        raise V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation(
            "repository-bound initial schedule replay failed"
        ) from error
    authority_replay = _replay_construction_authority(
        lineage=lineage,
        construction_authority=construction_authority,
    )
    derived = _derive(
        profile=profile,
        expected_slot=expected_slot,
        schedule=schedule,
        lineage=lineage,
        authority_replay=authority_replay,
        current_lifecycle=current_lifecycle,
    )
    return V075ScheduleBoundInitialAcquisitionLifecycleV2(
        _RESULT_ISSUER,
        derived.profile,
        derived.expected_slot,
        derived.schedule,
        derived.lineage,
        derived.authority_replay,
        derived.current_lifecycle,
        derived.lifecycle_verification,
        derived.matches,
        derived.counters,
        derived.terminal_code,
    )


def verify_v075_schedule_bound_initial_acquisition_lifecycle_bytes_v2(
    *,
    repository_root: str | Path,
    profile: acquisition_v2.V075FiveArmAcquisitionProfileV2,
    expected_slot: acquisition_v2.V075PreregisteredOccurrenceSlotV2,
    schedule: acquisition_v2.V075InitialAcquisitionScheduleV2,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    construction_authority: preopen_v2.V075ObserverOpenAuthorizationV2,
    current_lifecycle: LifecycleWitnessV2,
    raw: bytes,
) -> V075ScheduleBoundInitialAcquisitionLifecycleV2:
    """Rebuild every typed witness and accept exact canonical bytes only."""

    document = _strict_document(raw, "schedule-bound initial lifecycle")
    expected = freeze_v075_schedule_bound_initial_acquisition_lifecycle_v2(
        repository_root=repository_root,
        profile=profile,
        expected_slot=expected_slot,
        schedule=schedule,
        lineage=lineage,
        construction_authority=construction_authority,
        current_lifecycle=current_lifecycle,
    )
    if (
        set(document) != set(expected.to_document())
        or raw != expected.canonical_bytes
    ):
        _fail("schedule-bound initial lifecycle differs from exact byte replay")
    return expected


def open_v075_production_schedule_bound_initial_acquisition_lifecycle_v2(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    """Unconditionally locked until the downstream production chain exists."""

    raise V075ScheduleBoundAcquisitionProductionV2NotReady(PRODUCTION_BLOCKER)


__all__ = [
    "DIRECT_LIFECYCLE_NOT_APPLICABLE_REASON",
    "DOMAIN_TAGS",
    "DYNAMIC_ACQUISITION_ROUNDS_COMPLETE",
    "FRONTIER_RANKING_EXECUTED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PER_DRAW_REPLAY_ALLOWED",
    "PRODUCTION_AUTHORIZING",
    "PRODUCTION_BLOCKER",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TARGET_ACCESS_ALLOWED",
    "TERMINAL_CLASS",
    "TERMINAL_SCOPE",
    "V075InitialAcquisitionTerminalCodeV2",
    "V075InitialIntentExecutionMatchV2",
    "V075InitialIntentExecutionStatusV2",
    "V075InitialLifecycleNotApplicableV2",
    "V075ConstructionLineageAuthorityReplayV2",
    "V075ScheduleBoundAcquisitionLifecycleV2InvariantViolation",
    "V075ScheduleBoundAcquisitionProductionV2NotReady",
    "V075ScheduleBoundInitialAcquisitionCountersV2",
    "V075ScheduleBoundInitialAcquisitionLifecycleV2",
    "freeze_v075_direct_initial_lifecycle_not_applicable_v2",
    "freeze_v075_schedule_bound_initial_acquisition_lifecycle_v2",
    "open_v075_production_schedule_bound_initial_acquisition_lifecycle_v2",
    "verify_v075_schedule_bound_initial_acquisition_lifecycle_bytes_v2",
]
