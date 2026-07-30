"""Batch-native V2 support-freeze, multistage, and failure authority.

This leaf sits between the exact V2 batch-occurrence lineage and downstream
statistical planning.  It derives support only from signed aggregate rows,
freezes that support before the first validation batch of every row/epoch,
and emits one deterministic append-only lifecycle transcript.

The production verifiers in this module accept canonical bytes only.  They
replay the upstream content identities, the complete batch journal, every
accepted-draw interval, every aggregate commitment, every support freeze, and
the lifecycle hash chain.  They do not open the target, expand per-draw
records, or manufacture any historical observer/authority/namespace claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_private_observer_boundary_v2 as observer_v2
from acfqp import v075_public_graph_semantics_v1 as public_graph


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.46.0"
PROFILE_KEY = "v075_batch_occurrence_lifecycle_authority_v2"

OFFICIAL_EXECUTION_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
PER_DRAW_EXPANSION_ALLOWED = False
TARGET_ACCESS_ALLOWED = False
PRODUCTION_FAILURE_AUTHORITY_READY = False
PRODUCTION_FAILURE_BLOCKER = (
    "production failure closure remains locked until cap, violation, work, "
    "and total-lift semantic authorities are integrated"
)
PRODUCTION_POSITIVE_PATH_READY = False
PRODUCTION_POSITIVE_PATH_BLOCKER = (
    "a preregistered acquisition row/round schedule authority and downstream "
    "V2 lifecycle support-freeze consumer are not yet integrated"
)
LEGACY_OBSERVER_AUTHORITY_PROJECTION_ALLOWED = False
LEGACY_TARGET_NAMESPACE_PROJECTION_ALLOWED = False

MAX_CANONICAL_INPUT_BYTES = 64 * 1024 * 1024
MAX_LIFECYCLE_EVENTS = 131_072
MAX_FAILURE_REFERENCES = 4_096

DOMAIN_TAGS = {
    "support_evidence": "acfqp:v075-batch-support-evidence:v2",
    "support_freeze": "acfqp:v075-batch-support-freeze:v2",
    "event": "acfqp:v075-batch-lifecycle-event:v2",
    "transcript": "acfqp:v075-batch-lifecycle-transcript:v2",
    "construction_lifecycle": (
        "acfqp:v075-construction-batch-occurrence-lifecycle:v2"
    ),
    "production_lifecycle": (
        "acfqp:v075-production-batch-occurrence-lifecycle:v2"
    ),
    "construction_lifecycle_verification": (
        "acfqp:v075-construction-batch-occurrence-lifecycle-verification:v2"
    ),
    "production_lifecycle_verification": (
        "acfqp:v075-production-batch-occurrence-lifecycle-verification:v2"
    ),
    "construction_failure": (
        "acfqp:v075-construction-batch-occurrence-failure-closure:v2"
    ),
    "production_failure": (
        "acfqp:v075-production-batch-occurrence-failure-closure:v2"
    ),
    "construction_failure_verification": (
        "acfqp:v075-construction-batch-occurrence-failure-verification:v2"
    ),
    "production_failure_verification": (
        "acfqp:v075-production-batch-occurrence-failure-verification:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 batch lifecycle V2 domains must be unique")

_INITIAL_EVENT_ID = hashlib.sha256(
    b"acfqp:v075-batch-lifecycle-initial-event:v2"
).hexdigest()


class V075BatchOccurrenceLifecycleV2InvariantViolation(ValueError):
    """A byte, interval, support, phase, closure, or failure invariant failed."""


class V075ProductionFailureAuthorityV2NotReady(RuntimeError):
    """Production failure evidence cannot yet be semantically authorized."""


class V075ProductionPositiveLifecycleV2NotReady(RuntimeError):
    """Observed streams alone cannot establish preregistered schedule coverage."""


def _fail(message: str) -> None:
    raise V075BatchOccurrenceLifecycleV2InvariantViolation(message)


def _content_hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075BatchOccurrenceLifecycleV2InvariantViolation(
            str(error)
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
    except KeyError as error:  # pragma: no cover - internal programming error
        raise RuntimeError(f"unknown V2 lifecycle hash role {role}") from error
    return _content_hash(domain, payload)


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075BatchOccurrenceLifecycleV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field_name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        _fail(f"{field_name} must be canonical nonempty text")
    return value


def _load_document(raw: bytes, field_name: str) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CANONICAL_INPUT_BYTES
    ):
        _fail(f"{field_name} must be bounded nonempty canonical bytes")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075BatchOccurrenceLifecycleV2InvariantViolation(
            f"{field_name} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{field_name} is not one canonical object")
    return document


def _require_exact_keys(
    value: Any,
    expected: frozenset[str],
    field_name: str,
) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != expected:
        _fail(f"{field_name} has missing, unknown, or private fields")
    return value


_OCCURRENCE_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "target_tape_namespace_id",
        "context_id",
        "arm",
        "occurrence_ordinal",
        "threshold_profile_id",
        "cap_profile_id",
        "source_transport_id",
        "occurrence_id",
        "frozen_before_observation",
        "batch_count_at_freeze",
        "observer_calls",
        "kernel_calls",
        "target_accessed",
        "private_material_serialized",
    }
)

_LINEAGE_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "scope",
        "occurrence_identity",
        "occurrence_id",
        "target_tape_namespace_id",
        "context_id",
        "arm",
        "observer_session_public_id",
        "observer_open_binding_id",
        "observer_open_authorization_id",
        "private_reveal_attestation_id",
        "remote_main_anchor_id",
        "closure_id",
        "closure_verification_id",
        "journal_entry_ids",
        "batch_ids",
        "batch_public_verification_ids",
        "batch_sequence_verification_ids",
        "accepted_draw_count",
        "batch_count",
        "stream_count",
        "rsa_batch_signature_count",
        "rsa_closure_signature_count",
        "per_draw_record_count",
        "per_draw_signature_count",
        "private_reveal_attestation_bytes_sha256",
        "authorization_bytes_sha256",
        "namespace_bytes_sha256",
        "closure_bytes_sha256",
        "production_authority_bytes_replayed",
        "authority_version",
        "namespace_version",
        "legacy_v1_authority_projection_used",
        "legacy_v1_namespace_projection_used",
        "private_material_serialized",
        "official_execution_unlocked",
        "scientific_endpoint_credit_allowed",
        "lineage_id",
    }
)

_BINDING_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "observer_open_authorization_id",
        "private_reveal_attestation_id",
        "remote_main_anchor_id",
        "anchor_commit_id",
        "anchor_tree_id",
        "manifest_id",
        "final_preregistration_id",
        "component_registry_id",
        "semantic_registry_binding_id",
        "semantic_artifact_replay_id",
        "workload_id",
        "runner_profile_id",
        "family_generation_id",
        "target_tape_namespace_id",
        "opaque_environment_commitment_id",
        "signer_registry_id",
        "observer_evidence_key_id",
        "authority_version",
        "namespace_version",
        "legacy_v1_authority_projection_issued",
        "legacy_v1_namespace_projection_issued",
        "independent_final_authority_verified",
        "observer_open_authorized",
        "private_material_serialized",
        "binding_id",
    }
)

_REQUEST_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "occurrence_id",
        "observer_session_public_id",
        "observer_open_binding_id",
        "observer_open_authorization_id",
        "private_reveal_attestation_id",
        "remote_main_anchor_id",
        "target_tape_namespace_id",
        "environment_commitment_id",
        "signer_registry_id",
        "context_id",
        "row_binding_id",
        "catalogue_id",
        "stream_id",
        "pairing_group_id",
        "support_epoch_id",
        "observer_epoch_index",
        "lane",
        "arm",
        "accepted_draw_start",
        "accepted_draw_count",
        "accepted_draw_end",
        "accepted_draw_cap",
        "authority_version",
        "namespace_version",
        "per_draw_record_generation_allowed",
        "request_nonce_allowed",
        "reroll_allowed",
        "private_material_serialized",
        "request_id",
    }
)

_OUTCOME_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "next_ranks",
        "failure",
        "terminal",
        "spawn_cell",
        "spawn_rank",
        "realized_row_reward",
        "outcome_id",
        "count",
        "reward_sum",
    }
)

_BATCH_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "request_id",
        "occurrence_id",
        "observer_session_public_id",
        "observer_open_binding_id",
        "observer_open_authorization_id",
        "private_reveal_attestation_id",
        "remote_main_anchor_id",
        "target_tape_namespace_id",
        "environment_commitment_id",
        "context_id",
        "row_binding_id",
        "stream_id",
        "arm",
        "observer_epoch_index",
        "accepted_draw_start",
        "accepted_draw_count",
        "accepted_draw_end",
        "accepted_draw_cap",
        "outcome_aggregate_ids",
        "outcome_aggregate_commitments",
        "reward_sum",
        "failure_count",
        "terminal_count",
        "random_word_count",
        "rejection_count",
        "first_random_word_index",
        "next_random_word_index",
        "transcript_commitment",
        "transcript_scheme",
        "rsa_signatures_per_batch",
        "per_draw_records_created",
        "per_draw_records_serialized",
        "individual_random_words_retained",
        "individual_random_words_serialized",
        "private_law_serialized",
        "private_salt_serialized",
        "private_kernel_serialized",
        "request",
        "outcomes",
        "observer_signature_hex",
        "observer_signature_verified",
        "batch_id",
    }
)

_ENTRY_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "occurrence_id",
        "observer_session_public_id",
        "observer_open_binding_id",
        "sequence_number",
        "previous_entry_id",
        "batch_id",
        "batch",
        "entry_id",
    }
)

_BATCH_CLOSURE_KEYS = frozenset(
    {
        "schema",
        "schema_version",
        "occurrence_id",
        "observer_session_public_id",
        "observer_open_binding_id",
        "observer_open_authorization_id",
        "private_reveal_attestation_id",
        "remote_main_anchor_id",
        "target_tape_namespace_id",
        "environment_commitment_id",
        "entry_ids",
        "batch_ids",
        "stream_ids",
        "entry_count",
        "batch_count",
        "accepted_draw_count",
        "tail_entry_id",
        "journal_role",
        "per_draw_journal_entries",
        "append_only_hash_chain_closed",
        "private_material_serialized",
        "observer_open_binding",
        "entries",
        "observer_signature_hex",
        "observer_signature_verified",
        "closure_id",
    }
)


def _fraction_document(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("V2 lifecycle arithmetic must remain exact")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction_from_document(value: Any, field_name: str) -> Fraction:
    if type(value) is Fraction:
        return value
    if (
        type(value) is not dict
        or frozenset(value) != {"numerator", "denominator"}
        or type(value["numerator"]) is not int
        or type(value["denominator"]) is not int
        or value["denominator"] <= 0
    ):
        _fail(f"{field_name} is not one exact rational")
    result = Fraction(value["numerator"], value["denominator"])
    if _fraction_document(result) != value:
        _fail(f"{field_name} is not reduced canonical rational form")
    return result


class V075BatchLifecycleAuthorityScopeV2(str, Enum):
    CONSTRUCTION_ONLY = "CONSTRUCTION_ONLY"
    PRODUCTION_BYTE_REPLAY = "PRODUCTION_BYTE_REPLAY"


class V075BatchLifecycleEventKindV2(str, Enum):
    DISCOVERY_BATCH = "DISCOVERY_BATCH"
    SUPPORT_FREEZE = "SUPPORT_FREEZE"
    VALIDATION_BATCH = "VALIDATION_BATCH"


class V075BatchLifecycleTerminalCodeV2(str, Enum):
    COMPLETE_OBSERVED_REQUIRED_ROWS_CONSTRUCTION_CONTROL = (
        "COMPLETE_OBSERVED_REQUIRED_ROWS_CONSTRUCTION_CONTROL"
    )


class V075BatchFailureTerminalCodeV2(str, Enum):
    CAP_EXHAUSTED = "CAP_EXHAUSTED"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    POLICY_ABORT_NONCERTIFICATE = "POLICY_ABORT_NONCERTIFICATE"


@dataclass(frozen=True, slots=True)
class _ParsedOutcome:
    outcome_id: str
    next_ranks: tuple[int, ...]
    failure: bool
    terminal: bool
    count: int
    reward_sum: Fraction


@dataclass(frozen=True, slots=True)
class _ParsedBatch:
    batch_id: str
    request_id: str
    occurrence_id: str
    target_tape_namespace_id: str
    context_id: str
    row_binding_id: str
    stream_id: str
    support_epoch_id: str
    arm: str
    lane: str
    observer_epoch_index: int
    accepted_draw_start: int
    accepted_draw_count: int
    accepted_draw_end: int
    accepted_draw_cap: int
    outcomes: tuple[_ParsedOutcome, ...]


def _replay_lineage_document(raw: bytes) -> dict[str, Any]:
    document = _require_exact_keys(
        _load_document(raw, "V2 batch lineage"),
        _LINEAGE_KEYS,
        "V2 batch lineage",
    )
    if (
        document.get("schema") != "acfqp.v075_batch_occurrence_lineage.v2"
        or document.get("schema_version") != "2.0.0"
        or document.get("profile_key")
        != batched_v2.PROFILE_KEY
        or document.get("authority_version") != "V2"
        or document.get("namespace_version") != "V2"
        or document.get("legacy_v1_authority_projection_used") is not False
        or document.get("legacy_v1_namespace_projection_used") is not False
        or document.get("official_execution_unlocked") is not False
        or document.get("scientific_endpoint_credit_allowed") is not False
    ):
        _fail("V2 batch lineage schema, version, or lock state is invalid")
    claimed_id = _cid(document.get("lineage_id"), "V2 batch lineage")
    payload = dict(document)
    payload.pop("lineage_id", None)
    expected_id = _content_hash(
        batched_v2.DOMAIN_TAGS["occurrence_lineage"],
        payload,
    )
    if claimed_id != expected_id:
        _fail("V2 batch lineage content ID differs from canonical replay")
    occurrence = _require_exact_keys(
        document.get("occurrence_identity"),
        _OCCURRENCE_KEYS,
        "V2 batch occurrence identity",
    )
    occurrence_id = _cid(
        occurrence.get("occurrence_id"),
        "V2 lifecycle occurrence",
    )
    occurrence_payload = {
        key: occurrence[key]
        for key in (
            "schema",
            "schema_version",
            "target_tape_namespace_id",
            "context_id",
            "arm",
            "occurrence_ordinal",
            "threshold_profile_id",
            "cap_profile_id",
            "source_transport_id",
        )
    }
    expected_occurrence = _content_hash(
        "acfqp:v075-batch-native-occurrence:v1",
        occurrence_payload,
    )
    batch_ids = document.get("batch_ids")
    if (
        occurrence.get("schema") != "acfqp.v075_batch_native_occurrence.v1"
        or occurrence_id != expected_occurrence
        or occurrence.get("frozen_before_observation") is not True
        or occurrence.get("batch_count_at_freeze") != 0
        or occurrence.get("observer_calls") != 0
        or occurrence.get("kernel_calls") != 0
        or occurrence.get("target_accessed") is not False
        or occurrence.get("private_material_serialized") is not False
        or occurrence_id != document.get("occurrence_id")
        or occurrence.get("target_tape_namespace_id")
        != document.get("target_tape_namespace_id")
        or occurrence.get("context_id") != document.get("context_id")
        or occurrence.get("arm") != document.get("arm")
        or type(batch_ids) is not list
        or not batch_ids
        or len(batch_ids) != len(set(batch_ids))
        or any(_cid(value, "V2 lineage batch") != value for value in batch_ids)
        or document.get("batch_count") != len(batch_ids)
        or document.get("per_draw_record_count") != 0
        or document.get("per_draw_signature_count") != 0
    ):
        _fail("V2 lineage occurrence or aggregate registry is inconsistent")
    return document


def _replay_outcome(document: Any) -> _ParsedOutcome:
    document = _require_exact_keys(
        document,
        _OUTCOME_KEYS,
        "V2 batch outcome",
    )
    try:
        next_ranks = tuple(document["next_ranks"])
        failure = document["failure"]
        terminal = document["terminal"]
        count = document["count"]
        reward_sum = _fraction_from_document(
            document["reward_sum"],
            "V2 batch outcome reward sum",
        )
        realized = _fraction_from_document(
            document["realized_row_reward"],
            "V2 batch outcome realized reward",
        )
        identity_payload = {
            "schema": document["schema"],
            "schema_version": document["schema_version"],
            "next_ranks": list(next_ranks),
            "failure": failure,
            "terminal": terminal,
            "spawn_cell": document["spawn_cell"],
            "spawn_rank": document["spawn_rank"],
            "realized_row_reward": document["realized_row_reward"],
        }
    except (KeyError, TypeError, ValueError) as error:
        if type(error) is V075BatchOccurrenceLifecycleV2InvariantViolation:
            raise
        raise V075BatchOccurrenceLifecycleV2InvariantViolation(
            "V2 batch outcome reconstruction failed"
        ) from error
    if (
        identity_payload["schema"]
        != "acfqp.v075_batch_outcome_aggregate.v2"
        or identity_payload["schema_version"] != observer_v2.SCHEMA_VERSION
        or not next_ranks
        or any(type(item) is not int or item < 0 for item in next_ranks)
        or type(failure) is not bool
        or type(terminal) is not bool
        or type(identity_payload["spawn_cell"]) is not int
        or identity_payload["spawn_cell"] < 0
        or type(identity_payload["spawn_rank"]) is not int
        or identity_payload["spawn_rank"] <= 0
        or type(count) is not int
        or count <= 0
        or reward_sum != realized * count
    ):
        _fail("V2 batch outcome fields are malformed")
    expected_id = _content_hash(
        observer_v2.DOMAIN_TAGS["batch_outcome"],
        identity_payload,
    )
    if _cid(document.get("outcome_id"), "V2 batch outcome") != expected_id:
        _fail("V2 batch outcome identity differs from replay")
    return _ParsedOutcome(
        expected_id,
        next_ranks,
        failure,
        terminal,
        count,
        reward_sum,
    )


def _replay_batch(document: Any) -> _ParsedBatch:
    document = _require_exact_keys(
        document,
        _BATCH_KEYS,
        "V2 signed batch",
    )
    request = _require_exact_keys(
        document["request"],
        _REQUEST_KEYS,
        "V2 batch request",
    )
    outcomes_raw = document.get("outcomes")
    if type(outcomes_raw) is not list or not outcomes_raw:
        _fail("V2 signed batch has no aggregate outcomes")
    outcomes = tuple(_replay_outcome(item) for item in outcomes_raw)
    outcome_ids = tuple(item.outcome_id for item in outcomes)
    if outcome_ids != tuple(sorted(set(outcome_ids))):
        _fail("V2 signed batch outcomes are duplicated or reordered")
    batch_payload = {
        key: value
        for key, value in document.items()
        if key
        not in {
            "request",
            "outcomes",
            "observer_signature_hex",
            "observer_signature_verified",
            "batch_id",
        }
    }
    expected_batch_id = _content_hash(
        observer_v2.DOMAIN_TAGS["batch_artifact"],
        {
            **batch_payload,
            "observer_signature_hex": document.get(
                "observer_signature_hex"
            ),
            "observer_signature_verified": True,
        },
    )
    try:
        accepted_start = request["accepted_draw_start"]
        accepted_count = request["accepted_draw_count"]
        accepted_end = request["accepted_draw_end"]
        accepted_cap = request["accepted_draw_cap"]
        epoch = request["observer_epoch_index"]
        lane = request["lane"]
        commitments = document["outcome_aggregate_commitments"]
    except KeyError as error:
        raise V075BatchOccurrenceLifecycleV2InvariantViolation(
            "V2 batch request or aggregate commitment is incomplete"
        ) from error
    expected_commitments = [
        {
            "outcome_id": item.outcome_id,
            "count": item.count,
            "reward_sum": _fraction_document(item.reward_sum),
        }
        for item in outcomes
    ]
    mirrored_fields = (
        "request_id",
        "occurrence_id",
        "observer_session_public_id",
        "observer_open_binding_id",
        "observer_open_authorization_id",
        "private_reveal_attestation_id",
        "remote_main_anchor_id",
        "target_tape_namespace_id",
        "environment_commitment_id",
        "context_id",
        "row_binding_id",
        "stream_id",
        "arm",
        "observer_epoch_index",
        "accepted_draw_start",
        "accepted_draw_count",
        "accepted_draw_end",
        "accepted_draw_cap",
    )
    if (
        _cid(document.get("batch_id"), "V2 signed batch")
        != expected_batch_id
        or document.get("observer_signature_verified") is not True
        or request.get("schema")
        != "acfqp.v075_batch_observation_request.v2"
        or request.get("authority_version") != "V2"
        or request.get("namespace_version") != "V2"
        or any(request.get(key) != document.get(key) for key in mirrored_fields)
        or request.get("request_id") != document.get("request_id")
        or document.get("outcome_aggregate_ids") != list(outcome_ids)
        or canonical_json_bytes(commitments)
        != canonical_json_bytes(expected_commitments)
        or sum(item.count for item in outcomes) != accepted_count
        or type(accepted_start) is not int
        or type(accepted_count) is not int
        or type(accepted_end) is not int
        or type(accepted_cap) is not int
        or accepted_start <= 0
        or accepted_count <= 0
        or accepted_end != accepted_start + accepted_count - 1
        or accepted_end > accepted_cap
        or type(epoch) is not int
        or epoch < 0
        or lane not in {"DISCOVERY", "VALIDATION"}
        or (lane == "DISCOVERY") != (epoch == 0)
    ):
        _fail("V2 signed batch identity, interval, or aggregate differs")
    return _ParsedBatch(
        expected_batch_id,
        _cid(request["request_id"], "V2 batch request"),
        _cid(request["occurrence_id"], "V2 batch occurrence"),
        _cid(
            request["target_tape_namespace_id"],
            "V2 batch namespace",
        ),
        _cid(request["context_id"], "V2 batch context"),
        _cid(request["row_binding_id"], "V2 batch row"),
        _cid(request["stream_id"], "V2 batch stream"),
        _cid(request["support_epoch_id"], "V2 stream support epoch"),
        _token(request["arm"], "V2 batch arm"),
        lane,
        epoch,
        accepted_start,
        accepted_count,
        accepted_end,
        accepted_cap,
        outcomes,
    )


def _replay_batch_closure_document(
    raw: bytes,
    *,
    lineage: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[_ParsedBatch, ...]]:
    document = _load_document(raw, "V2 batch journal closure")
    _require_exact_keys(
        document,
        _BATCH_CLOSURE_KEYS,
        "V2 batch journal closure",
    )
    binding_document = _require_exact_keys(
        document.get("observer_open_binding"),
        _BINDING_KEYS,
        "V2 observer-open binding",
    )
    binding_payload = dict(binding_document)
    claimed_binding_id = _cid(
        binding_payload.pop("binding_id"),
        "V2 observer-open binding",
    )
    if (
        claimed_binding_id
        != _content_hash(
            observer_v2.DOMAIN_TAGS["open_binding"],
            binding_payload,
        )
        or claimed_binding_id != document.get("observer_open_binding_id")
    ):
        _fail("V2 observer-open binding ID differs from exact replay")
    entries_raw = document.get("entries")
    if (
        document.get("schema")
        != "acfqp.v075_observer_batch_journal_closure.v2"
        or document.get("schema_version") != observer_v2.SCHEMA_VERSION
        or type(entries_raw) is not list
        or not entries_raw
        or len(entries_raw) > observer_v2.MAX_BATCHES_PER_SESSION
        or document.get("entry_count") != len(entries_raw)
        or document.get("batch_count") != len(entries_raw)
        or document.get("journal_role") != "BATCH_NATIVE_ONLY"
        or document.get("per_draw_journal_entries") != 0
        or document.get("append_only_hash_chain_closed") is not True
    ):
        _fail("V2 batch journal closure schema or registry is invalid")
    batches: list[_ParsedBatch] = []
    entry_ids: list[str] = []
    previous: str | None = None
    for index, entry in enumerate(entries_raw, start=1):
        entry = _require_exact_keys(
            entry,
            _ENTRY_KEYS,
            "V2 batch journal entry",
        )
        batch = _replay_batch(entry.get("batch"))
        entry_payload = {
            key: value
            for key, value in entry.items()
            if key not in {"batch", "entry_id"}
        }
        expected_entry_id = _content_hash(
            observer_v2.DOMAIN_TAGS["batch_journal_entry"],
            entry_payload,
        )
        if (
            entry.get("sequence_number") != index
            or entry.get("previous_entry_id") != previous
            or entry.get("batch_id") != batch.batch_id
            or _cid(entry.get("entry_id"), "V2 batch journal entry")
            != expected_entry_id
        ):
            _fail("V2 batch journal hash chain is gapped or transplanted")
        entry_ids.append(expected_entry_id)
        previous = expected_entry_id
        batches.append(batch)
    batch_tuple = tuple(batches)
    closure_payload = {
        key: value
        for key, value in document.items()
        if key
        not in {
            "observer_open_binding",
            "entries",
            "observer_signature_hex",
            "observer_signature_verified",
            "closure_id",
        }
    }
    expected_closure_id = _content_hash(
        observer_v2.DOMAIN_TAGS["batch_journal_closure_artifact"],
        {
            **closure_payload,
            "observer_signature_hex": document.get(
                "observer_signature_hex"
            ),
            "observer_signature_verified": True,
        },
    )
    batch_ids = tuple(item.batch_id for item in batch_tuple)
    if (
        _cid(document.get("closure_id"), "V2 batch journal closure")
        != expected_closure_id
        or document.get("observer_signature_verified") is not True
        or document.get("entry_ids") != entry_ids
        or document.get("batch_ids") != list(batch_ids)
        or document.get("tail_entry_id") != entry_ids[-1]
        or document.get("occurrence_id") != lineage.get("occurrence_id")
        or document.get("target_tape_namespace_id")
        != lineage.get("target_tape_namespace_id")
        or document.get("observer_session_public_id")
        != lineage.get("observer_session_public_id")
        or document.get("observer_open_binding_id")
        != lineage.get("observer_open_binding_id")
        or document.get("batch_ids") != lineage.get("batch_ids")
        or hashlib.sha256(raw).hexdigest()
        != lineage.get("closure_bytes_sha256")
        or expected_closure_id != lineage.get("closure_id")
        or document.get("accepted_draw_count")
        != sum(item.accepted_draw_count for item in batch_tuple)
        or any(
            (
                item.occurrence_id,
                item.target_tape_namespace_id,
                item.context_id,
                item.arm,
            )
            != (
                lineage.get("occurrence_id"),
                lineage.get("target_tape_namespace_id"),
                lineage.get("context_id"),
                lineage.get("arm"),
            )
            for item in batch_tuple
        )
    ):
        _fail("V2 batch closure differs from its batch lineage")
    next_index: dict[str, int] = {}
    caps: dict[str, int] = {}
    request_ids: set[str] = set()
    support_owner: dict[str, tuple[str, int]] = {}
    for batch in batch_tuple:
        expected_start = next_index.get(batch.stream_id, 1)
        prior_cap = caps.setdefault(batch.stream_id, batch.accepted_draw_cap)
        owner = (batch.row_binding_id, batch.observer_epoch_index)
        prior_owner = support_owner.setdefault(batch.support_epoch_id, owner)
        if (
            batch.accepted_draw_start != expected_start
            or batch.accepted_draw_cap != prior_cap
            or batch.request_id in request_ids
            or prior_owner != owner
        ):
            _fail(
                "V2 batch intervals gap/overlap or support epoch transplant "
                "was detected"
            )
        next_index[batch.stream_id] = batch.accepted_draw_end + 1
        request_ids.add(batch.request_id)
    return document, batch_tuple


_SUPPORT_EVIDENCE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchSupportEvidenceV2:
    _issuer: object = field(repr=False, compare=False)
    occurrence_id: str
    target_tape_namespace_id: str
    context_id: str
    row_binding_id: str
    discovery_batch_id: str
    discovery_request_id: str
    discovery_outcome_id: str
    discovery_outcome_count: int
    discovery_reward_sum: Fraction
    next_ranks: tuple[int, ...]
    failure: bool
    terminal: bool
    _evidence_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "V2 support occurrence"),
            (self.target_tape_namespace_id, "V2 support namespace"),
            (self.context_id, "V2 support context"),
            (self.row_binding_id, "V2 support row"),
            (self.discovery_batch_id, "V2 support batch"),
            (self.discovery_request_id, "V2 support request"),
            (self.discovery_outcome_id, "V2 support outcome"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _SUPPORT_EVIDENCE_ISSUER
            or type(self.discovery_outcome_count) is not int
            or self.discovery_outcome_count <= 0
            or type(self.discovery_reward_sum) is not Fraction
            or self.discovery_reward_sum < 0
            or type(self.next_ranks) is not tuple
            or not self.next_ranks
            or any(type(item) is not int or item < 0 for item in self.next_ranks)
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
        ):
            _fail("V2 batch support evidence is malformed or caller-minted")
        object.__setattr__(
            self,
            "_evidence_id",
            _hash("support_evidence", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_support_evidence.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "row_binding_id": self.row_binding_id,
            "source_observer_epoch_index": 0,
            "discovery_batch_id": self.discovery_batch_id,
            "discovery_request_id": self.discovery_request_id,
            "discovery_outcome_id": self.discovery_outcome_id,
            "discovery_outcome_count": self.discovery_outcome_count,
            "discovery_reward_sum": _fraction_document(
                self.discovery_reward_sum
            ),
            "next_ranks": list(self.next_ranks),
            "failure": self.failure,
            "terminal": self.terminal,
            "evidence_granularity": "SIGNED_V2_BATCH_OUTCOME_AGGREGATE",
            "individual_draw_identity_serialized": False,
            "private_material_serialized": False,
        }

    @property
    def evidence_id(self) -> str:
        return self._evidence_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


_SUPPORT_FREEZE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchSupportFreezeV2:
    _issuer: object = field(repr=False, compare=False)
    occurrence_id: str
    row_binding_id: str
    validation_epoch_index: int
    source_stream_support_epoch_id: str
    parent_freeze_id: str | None
    source_discovery_batch_ids: tuple[str, ...]
    support_evidence_ids: tuple[str, ...]
    typed_model_support_evidence_ids: tuple[str, ...]
    _freeze_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "V2 support-freeze occurrence")
        _cid(self.row_binding_id, "V2 support-freeze row")
        _cid(
            self.source_stream_support_epoch_id,
            "V2 source stream support epoch",
        )
        if self.parent_freeze_id is not None:
            _cid(self.parent_freeze_id, "V2 parent support freeze")
        for value in (
            *self.source_discovery_batch_ids,
            *self.support_evidence_ids,
            *self.typed_model_support_evidence_ids,
        ):
            _cid(value, "V2 support-freeze member")
        if (
            self._issuer is not _SUPPORT_FREEZE_ISSUER
            or type(self.validation_epoch_index) is not int
            or self.validation_epoch_index <= 0
            or type(self.source_discovery_batch_ids) is not tuple
            or not self.source_discovery_batch_ids
            or self.source_discovery_batch_ids
            != tuple(sorted(set(self.source_discovery_batch_ids)))
            or type(self.support_evidence_ids) is not tuple
            or not self.support_evidence_ids
            or self.support_evidence_ids
            != tuple(sorted(set(self.support_evidence_ids)))
            or type(self.typed_model_support_evidence_ids) is not tuple
            or not self.typed_model_support_evidence_ids
            or self.typed_model_support_evidence_ids
            != tuple(sorted(set(self.typed_model_support_evidence_ids)))
            or (self.validation_epoch_index == 1)
            != (self.parent_freeze_id is None)
        ):
            _fail("V2 support freeze is malformed or caller-minted")
        object.__setattr__(
            self,
            "_freeze_id",
            _hash("support_freeze", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_support_freeze.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "row_binding_id": self.row_binding_id,
            "validation_epoch_index": self.validation_epoch_index,
            "source_stream_support_epoch_id": (
                self.source_stream_support_epoch_id
            ),
            "parent_freeze_id": self.parent_freeze_id,
            "source_discovery_batch_ids": list(
                self.source_discovery_batch_ids
            ),
            "support_evidence_ids": list(self.support_evidence_ids),
            "typed_model_support_evidence_ids": list(
                self.typed_model_support_evidence_ids
            ),
            "support_selection_rule": (
                "ONE_MIN_OUTCOME_ID_PER_DISTINCT_SUCCESSOR_STATE"
            ),
            "typed_validation_support_chain_semantically_replayed": True,
            "frozen_before_first_validation_batch": True,
            "individual_draw_identity_serialized": False,
            "private_material_serialized": False,
        }

    @property
    def freeze_id(self) -> str:
        return self._freeze_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "freeze_id": self.freeze_id}


_EVENT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchLifecycleEventV2:
    _issuer: object = field(repr=False, compare=False)
    sequence_number: int
    previous_event_id: str
    kind: V075BatchLifecycleEventKindV2
    row_binding_id: str
    observer_epoch_index: int
    batch_id: str | None
    request_id: str | None
    stream_id: str | None
    support_freeze_id: str | None
    accepted_draw_count: int
    _event_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.previous_event_id, "V2 prior lifecycle event")
        _cid(self.row_binding_id, "V2 lifecycle event row")
        for value, label in (
            (self.batch_id, "V2 lifecycle batch"),
            (self.request_id, "V2 lifecycle request"),
            (self.stream_id, "V2 lifecycle stream"),
            (self.support_freeze_id, "V2 lifecycle support freeze"),
        ):
            if value is not None:
                _cid(value, label)
        is_freeze = (
            self.kind is V075BatchLifecycleEventKindV2.SUPPORT_FREEZE
        )
        if (
            self._issuer is not _EVENT_ISSUER
            or type(self.sequence_number) is not int
            or not 1 <= self.sequence_number <= MAX_LIFECYCLE_EVENTS
            or type(self.kind) is not V075BatchLifecycleEventKindV2
            or type(self.observer_epoch_index) is not int
            or self.observer_epoch_index < 0
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count < 0
            or (
                is_freeze
                and (
                    self.batch_id is not None
                    or self.request_id is not None
                    or self.stream_id is not None
                    or self.support_freeze_id is None
                    or self.observer_epoch_index <= 0
                    or self.accepted_draw_count != 0
                )
            )
            or (
                not is_freeze
                and (
                    self.batch_id is None
                    or self.request_id is None
                    or self.stream_id is None
                    or self.accepted_draw_count <= 0
                    or (
                        self.kind
                        is V075BatchLifecycleEventKindV2.DISCOVERY_BATCH
                        and (
                            self.observer_epoch_index != 0
                            or self.support_freeze_id is not None
                        )
                    )
                    or (
                        self.kind
                        is V075BatchLifecycleEventKindV2.VALIDATION_BATCH
                        and (
                            self.observer_epoch_index <= 0
                            or self.support_freeze_id is None
                        )
                    )
                )
            )
        ):
            _fail("V2 lifecycle event is malformed or caller-minted")
        object.__setattr__(
            self,
            "_event_id",
            _hash("event", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_lifecycle_event.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "sequence_number": self.sequence_number,
            "previous_event_id": self.previous_event_id,
            "kind": self.kind.value,
            "row_binding_id": self.row_binding_id,
            "observer_epoch_index": self.observer_epoch_index,
            "batch_id": self.batch_id,
            "request_id": self.request_id,
            "stream_id": self.stream_id,
            "support_freeze_id": self.support_freeze_id,
            "accepted_draw_count": self.accepted_draw_count,
            "per_draw_record_count": 0,
        }

    @property
    def event_id(self) -> str:
        return self._event_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "event_id": self.event_id}


_LIFECYCLE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchOccurrenceLifecycleClosureV2:
    _issuer: object = field(repr=False, compare=False)
    scope: V075BatchLifecycleAuthorityScopeV2
    lineage_id: str
    lineage_bytes_sha256: str
    batch_closure_id: str
    batch_closure_bytes_sha256: str
    occurrence_id: str
    target_tape_namespace_id: str
    context_id: str
    arm: str
    events: tuple[V075BatchLifecycleEventV2, ...]
    support_evidence: tuple[V075BatchSupportEvidenceV2, ...]
    support_freezes: tuple[V075BatchSupportFreezeV2, ...]
    batch_ids: tuple[str, ...]
    accepted_draw_count: int
    required_row_binding_ids: tuple[str, ...]
    required_round_schedule: tuple[tuple[str, tuple[int, ...]], ...]
    transcript_id: str
    terminal_code: V075BatchLifecycleTerminalCodeV2
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.lineage_id, "V2 lifecycle lineage"),
            (self.lineage_bytes_sha256, "V2 lifecycle lineage bytes"),
            (self.batch_closure_id, "V2 lifecycle batch closure"),
            (
                self.batch_closure_bytes_sha256,
                "V2 lifecycle batch closure bytes",
            ),
            (self.occurrence_id, "V2 lifecycle occurrence"),
            (self.target_tape_namespace_id, "V2 lifecycle namespace"),
            (self.context_id, "V2 lifecycle context"),
            (self.transcript_id, "V2 lifecycle transcript"),
        ):
            _cid(value, label)
        _token(self.arm, "V2 lifecycle arm")
        for value in self.batch_ids:
            _cid(value, "V2 lifecycle batch")
        for value in self.required_row_binding_ids:
            _cid(value, "V2 lifecycle required row")
        if (
            self._issuer is not _LIFECYCLE_ISSUER
            or type(self.scope) is not V075BatchLifecycleAuthorityScopeV2
            or type(self.events) is not tuple
            or not self.events
            or len(self.events) > MAX_LIFECYCLE_EVENTS
            or any(
                type(item) is not V075BatchLifecycleEventV2
                for item in self.events
            )
            or type(self.support_evidence) is not tuple
            or not self.support_evidence
            or any(
                type(item) is not V075BatchSupportEvidenceV2
                for item in self.support_evidence
            )
            or self.support_evidence
            != tuple(sorted(self.support_evidence, key=lambda item: item.evidence_id))
            or type(self.support_freezes) is not tuple
            or not self.support_freezes
            or any(
                type(item) is not V075BatchSupportFreezeV2
                for item in self.support_freezes
            )
            or self.support_freezes
            != tuple(
                sorted(
                    self.support_freezes,
                    key=lambda item: (
                        item.row_binding_id,
                        item.validation_epoch_index,
                    ),
                )
            )
            or type(self.batch_ids) is not tuple
            or not self.batch_ids
            or len(self.batch_ids) != len(set(self.batch_ids))
            or type(self.accepted_draw_count) is not int
            or self.accepted_draw_count <= 0
            or type(self.required_row_binding_ids) is not tuple
            or not self.required_row_binding_ids
            or self.required_row_binding_ids
            != tuple(sorted(set(self.required_row_binding_ids)))
            or type(self.required_round_schedule) is not tuple
            or not self.required_round_schedule
            or tuple(item[0] for item in self.required_round_schedule)
            != self.required_row_binding_ids
            or any(
                type(item) is not tuple
                or len(item) != 2
                or _cid(item[0], "V2 scheduled row") != item[0]
                or type(item[1]) is not tuple
                or not item[1]
                or item[1] != tuple(range(1, max(item[1]) + 1))
                for item in self.required_round_schedule
            )
            or type(self.terminal_code)
            is not V075BatchLifecycleTerminalCodeV2
        ):
            _fail("V2 lifecycle closure is malformed or caller-minted")
        prior = _INITIAL_EVENT_ID
        for index, event in enumerate(self.events, start=1):
            if (
                event.sequence_number != index
                or event.previous_event_id != prior
            ):
                _fail("V2 lifecycle event chain is gapped or reordered")
            prior = event.event_id
        expected_transcript = _hash(
            "transcript",
            {
                "schema": "acfqp.v075_batch_lifecycle_transcript.v2",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "event_ids": [item.event_id for item in self.events],
            },
        )
        if self.transcript_id != expected_transcript:
            _fail("V2 lifecycle transcript identity differs from events")
        object.__setattr__(
            self,
            "_closure_id",
            _hash(
                (
                    "production_lifecycle"
                    if self.scope
                    is V075BatchLifecycleAuthorityScopeV2
                    .PRODUCTION_BYTE_REPLAY
                    else "construction_lifecycle"
                ),
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_occurrence_lifecycle.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "lineage_id": self.lineage_id,
            "lineage_bytes_sha256": self.lineage_bytes_sha256,
            "batch_closure_id": self.batch_closure_id,
            "batch_closure_bytes_sha256": self.batch_closure_bytes_sha256,
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "event_ids": [item.event_id for item in self.events],
            "support_evidence_ids": [
                item.evidence_id for item in self.support_evidence
            ],
            "support_freeze_ids": [
                item.freeze_id for item in self.support_freezes
            ],
            "batch_ids": list(self.batch_ids),
            "accepted_draw_count": self.accepted_draw_count,
            "required_row_binding_ids": list(
                self.required_row_binding_ids
            ),
            "required_round_schedule": [
                {
                    "row_binding_id": row_id,
                    "validation_epoch_indices": list(indices),
                }
                for row_id, indices in self.required_round_schedule
            ],
            "transcript_id": self.transcript_id,
            "terminal_code": self.terminal_code.value,
            "support_frozen_before_validation": True,
            "complete_observed_row_round_schedule_covered": True,
            "preregistered_schedule_authority_integrated": False,
            "complete_batch_registry_retained": True,
            "per_draw_record_count": 0,
            "private_material_serialized": False,
            "legacy_v1_projection_used": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "production_positive_path_ready": False,
            "production_positive_path_blocker": (
                PRODUCTION_POSITIVE_PATH_BLOCKER
            ),
            "plan_certificate": False,
            "infeasibility_certificate": False,
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "events": [item.to_document() for item in self.events],
            "support_evidence": [
                item.to_document() for item in self.support_evidence
            ],
            "support_freezes": [
                item.to_document() for item in self.support_freezes
            ],
            "closure_id": self.closure_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _scope_from_lineage(
    lineage: Mapping[str, Any],
) -> V075BatchLifecycleAuthorityScopeV2:
    value = lineage.get("scope")
    if value == "CONSTRUCTION_ONLY":
        return V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY
    if value == "PRODUCTION_BYTE_REPLAY":
        return V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
    _fail("V2 batch lineage carries an unknown authority scope")
    raise AssertionError("unreachable")


def _replay_semantic_stream_registry(
    *,
    streams: tuple[public_graph.V075TransitionStreamIdentityV1, ...],
    batches: tuple[_ParsedBatch, ...],
) -> dict[str, public_graph.V075TransitionStreamIdentityV1]:
    if type(streams) is not tuple or not streams:
        _fail("V2 lifecycle requires one nonempty typed public stream registry")
    replayed: dict[str, public_graph.V075TransitionStreamIdentityV1] = {}
    try:
        for claimed in streams:
            stream = observer_v2._replay_v2_stream_identity(  # noqa: SLF001
                claimed
            )
            if stream.stream_id in replayed:
                _fail("V2 lifecycle public stream registry is duplicated")
            replayed[stream.stream_id] = stream
    except observer_v2.V075PrivateObserverBoundaryV2InvariantViolation as error:
        raise V075BatchOccurrenceLifecycleV2InvariantViolation(
            str(error)
        ) from error
    if set(replayed) != {item.stream_id for item in batches}:
        _fail(
            "V2 lifecycle typed public stream registry is not the exact "
            "observed stream set"
        )
    for batch in batches:
        stream = replayed[batch.stream_id]
        if (
            stream.context_id != batch.context_id
            or stream.row_binding_id != batch.row_binding_id
            or stream.support_epoch_id != batch.support_epoch_id
            or stream.observer_epoch_index != batch.observer_epoch_index
            or stream.lane.value != batch.lane
            or stream.arm != batch.arm
        ):
            _fail(
                "V2 lifecycle batch differs from semantic public stream "
                "replay"
            )
        leaf = stream.pairing_authority.support_chain.leaf
        if (
            leaf.epoch_id != batch.support_epoch_id
            or leaf.epoch_index != batch.observer_epoch_index
            or leaf.row_binding.row_binding_id != batch.row_binding_id
        ):
            _fail("V2 lifecycle support chain leaf was transplanted")
        if batch.lane == "DISCOVERY" and leaf.evidence:
            _fail("V2 DISCOVERY stream carries retrospective support")
        if batch.lane == "VALIDATION" and (
            not leaf.evidence
            or any(
                type(item)
                is not public_graph.V075BatchAggregateSupportEvidenceV1
                for item in leaf.evidence
            )
        ):
            _fail(
                "V2 VALIDATION stream lacks an all-aggregate typed support "
                "chain"
            )
    return replayed


_DERIVATION_CONSTRUCTION_ISSUER = object()
_DERIVATION_PRODUCTION_ISSUER = object()


def _derive_lifecycle(
    *,
    lineage_raw: bytes,
    batch_closure_raw: bytes,
    semantic_streams: tuple[
        public_graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    issuer: object,
) -> V075BatchOccurrenceLifecycleClosureV2:
    lineage = _replay_lineage_document(lineage_raw)
    scope = _scope_from_lineage(lineage)
    if issuer is _DERIVATION_CONSTRUCTION_ISSUER:
        if scope is not V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY:
            _fail("construction derivation rejects production lineage bytes")
    elif issuer is _DERIVATION_PRODUCTION_ISSUER:
        if scope is not V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY:
            _fail("production derivation rejects construction lineage bytes")
    else:
        _fail("V2 lifecycle derivation issuer is not authorized")
    batch_closure, batches = _replay_batch_closure_document(
        batch_closure_raw,
        lineage=lineage,
    )
    streams = _replay_semantic_stream_registry(
        streams=semantic_streams,
        batches=batches,
    )
    discovery_by_row: dict[str, list[_ParsedBatch]] = {}
    evidence_by_key: dict[
        tuple[str, str, str],
        V075BatchSupportEvidenceV2,
    ] = {}
    freeze_by_key: dict[
        tuple[str, int],
        V075BatchSupportFreezeV2,
    ] = {}
    current_epoch_by_row: dict[str, int] = {}
    support_owner: dict[str, tuple[str, int]] = {}
    events: list[V075BatchLifecycleEventV2] = []
    global_validation_started = False

    def append_event(
        *,
        kind: V075BatchLifecycleEventKindV2,
        row_binding_id: str,
        observer_epoch_index: int,
        batch_id: str | None,
        request_id: str | None,
        stream_id: str | None,
        support_freeze_id: str | None,
        accepted_draw_count: int,
    ) -> None:
        prior = _INITIAL_EVENT_ID if not events else events[-1].event_id
        events.append(
            V075BatchLifecycleEventV2(
                _EVENT_ISSUER,
                len(events) + 1,
                prior,
                kind,
                row_binding_id,
                observer_epoch_index,
                batch_id,
                request_id,
                stream_id,
                support_freeze_id,
                accepted_draw_count,
            )
        )

    for batch in batches:
        row = batch.row_binding_id
        if batch.lane == "DISCOVERY":
            if global_validation_started:
                _fail("DISCOVERY occurred after lifecycle validation began")
            discovery_by_row.setdefault(row, []).append(batch)
            append_event(
                kind=V075BatchLifecycleEventKindV2.DISCOVERY_BATCH,
                row_binding_id=row,
                observer_epoch_index=0,
                batch_id=batch.batch_id,
                request_id=batch.request_id,
                stream_id=batch.stream_id,
                support_freeze_id=None,
                accepted_draw_count=batch.accepted_draw_count,
            )
            continue

        global_validation_started = True
        discoveries = discovery_by_row.get(row)
        if not discoveries:
            _fail("VALIDATION occurred before any same-row DISCOVERY")
        epoch = batch.observer_epoch_index
        current = current_epoch_by_row.get(row, 0)
        if epoch not in {current, current + 1} or epoch <= 0:
            _fail("same-row validation epochs are gapped or regressed")
        owner = (row, epoch)
        prior_owner = support_owner.setdefault(batch.support_epoch_id, owner)
        if prior_owner != owner:
            _fail("same support epoch was transplanted across row/round")
        key = (row, epoch)
        if key not in freeze_by_key:
            if epoch != current + 1:
                _fail("validation used a support freeze before it was issued")
            for source in discoveries:
                representatives: dict[
                    tuple[tuple[int, ...], bool],
                    _ParsedOutcome,
                ] = {}
                for outcome in source.outcomes:
                    state_key = (outcome.next_ranks, outcome.failure)
                    prior = representatives.get(state_key)
                    if prior is None or outcome.outcome_id < prior.outcome_id:
                        representatives[state_key] = outcome
                for outcome in representatives.values():
                    evidence_key = (
                        row,
                        source.batch_id,
                        outcome.outcome_id,
                    )
                    evidence_by_key.setdefault(
                        evidence_key,
                        V075BatchSupportEvidenceV2(
                            _SUPPORT_EVIDENCE_ISSUER,
                            batch.occurrence_id,
                            batch.target_tape_namespace_id,
                            batch.context_id,
                            row,
                            source.batch_id,
                            source.request_id,
                            outcome.outcome_id,
                            outcome.count,
                            outcome.reward_sum,
                            outcome.next_ranks,
                            outcome.failure,
                            outcome.terminal,
                        ),
                    )
            row_evidence = tuple(
                sorted(
                    (
                        item
                        for (evidence_row, _batch, _outcome), item
                        in evidence_by_key.items()
                        if evidence_row == row
                    ),
                    key=lambda item: item.evidence_id,
                )
            )
            typed_leaf = streams[
                batch.stream_id
            ].pairing_authority.support_chain.leaf
            typed_evidence = tuple(typed_leaf.evidence)
            source_by_batch_id = {
                item.batch_id: item for item in discoveries
            }
            derived_by_source = {
                (
                    item.discovery_batch_id,
                    item.discovery_outcome_id,
                    item.discovery_outcome_count,
                    item.next_ranks,
                    item.failure,
                ): item
                for item in row_evidence
            }
            typed_keys: set[
                tuple[str, str, int, tuple[int, ...], bool]
            ] = set()
            for item in typed_evidence:
                source = source_by_batch_id.get(item.discovery_batch_id)
                outcomes = (
                    {}
                    if source is None
                    else {
                        value.outcome_id: value
                        for value in source.outcomes
                    }
                )
                outcome = outcomes.get(item.discovery_outcome_id)
                typed_key = (
                    item.discovery_batch_id,
                    item.discovery_outcome_id,
                    item.discovery_outcome_count,
                    item.observed_state.ranks,
                    item.observed_state.failure,
                )
                if (
                    source is None
                    or outcome is None
                    or source.request_id != item.discovery_request_id
                    or item.row_binding.row_binding_id != row
                    or item.source_observer_epoch_index != 0
                    or outcome.count != item.discovery_outcome_count
                    or outcome.next_ranks != item.observed_state.ranks
                    or outcome.failure != item.observed_state.failure
                    or typed_key not in derived_by_source
                    or typed_key in typed_keys
                ):
                    _fail(
                        "typed VALIDATION support is foreign, incomplete, "
                        "or differs from signed local discovery aggregates"
                    )
                typed_keys.add(typed_key)
            if typed_keys != set(derived_by_source):
                _fail(
                    "typed VALIDATION support does not exactly equal the "
                    "deterministic V2 support registry"
                )
            typed_evidence_ids = tuple(
                sorted(item.evidence_id for item in typed_evidence)
            )
            prior_freeze = freeze_by_key.get((row, epoch - 1))
            freeze = V075BatchSupportFreezeV2(
                _SUPPORT_FREEZE_ISSUER,
                batch.occurrence_id,
                row,
                epoch,
                batch.support_epoch_id,
                None if prior_freeze is None else prior_freeze.freeze_id,
                tuple(sorted(item.batch_id for item in discoveries)),
                tuple(item.evidence_id for item in row_evidence),
                typed_evidence_ids,
            )
            freeze_by_key[key] = freeze
            current_epoch_by_row[row] = epoch
            append_event(
                kind=V075BatchLifecycleEventKindV2.SUPPORT_FREEZE,
                row_binding_id=row,
                observer_epoch_index=epoch,
                batch_id=None,
                request_id=None,
                stream_id=None,
                support_freeze_id=freeze.freeze_id,
                accepted_draw_count=0,
            )
        else:
            freeze = freeze_by_key[key]
            current_typed_ids = tuple(
                sorted(
                    item.evidence_id
                    for item in streams[
                        batch.stream_id
                    ].pairing_authority.support_chain.leaf.evidence
                )
            )
            if (
                freeze.source_stream_support_epoch_id
                != batch.support_epoch_id
                or freeze.typed_model_support_evidence_ids
                != current_typed_ids
            ):
                _fail("validation stream changed support within one epoch")
        append_event(
            kind=V075BatchLifecycleEventKindV2.VALIDATION_BATCH,
            row_binding_id=row,
            observer_epoch_index=epoch,
            batch_id=batch.batch_id,
            request_id=batch.request_id,
            stream_id=batch.stream_id,
            support_freeze_id=freeze.freeze_id,
            accepted_draw_count=batch.accepted_draw_count,
        )

    if not global_validation_started or not evidence_by_key or not freeze_by_key:
        _fail("V2 lifecycle requires discovery, support freeze, and validation")
    required_discovery_rows = tuple(
        sorted(
            {
                stream.row_binding_id
                for stream in streams.values()
                if stream.lane.value == "DISCOVERY"
            }
        )
    )
    required_validation_epochs: dict[str, set[int]] = {}
    for stream in streams.values():
        if stream.lane.value == "VALIDATION":
            required_validation_epochs.setdefault(
                stream.row_binding_id,
                set(),
            ).add(stream.observer_epoch_index)
    required_validation_rows = tuple(sorted(required_validation_epochs))
    if (
        not required_discovery_rows
        or required_discovery_rows != required_validation_rows
        or set(discovery_by_row) != set(required_discovery_rows)
        or set(current_epoch_by_row) != set(required_discovery_rows)
    ):
        _fail(
            "COMPLETE lifecycle does not cover every required discovery row "
            "with validation"
        )
    required_schedule = tuple(
        (
            row_id,
            tuple(sorted(required_validation_epochs[row_id])),
        )
        for row_id in required_discovery_rows
    )
    if any(
        indices != tuple(range(1, max(indices) + 1))
        or current_epoch_by_row[row_id] != max(indices)
        for row_id, indices in required_schedule
    ):
        _fail("COMPLETE lifecycle required validation rounds are incomplete")
    event_ids = [item.event_id for item in events]
    transcript_id = _hash(
        "transcript",
        {
            "schema": "acfqp.v075_batch_lifecycle_transcript.v2",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "event_ids": event_ids,
        },
    )
    return V075BatchOccurrenceLifecycleClosureV2(
        _LIFECYCLE_ISSUER,
        scope,
        lineage["lineage_id"],
        hashlib.sha256(lineage_raw).hexdigest(),
        batch_closure["closure_id"],
        hashlib.sha256(batch_closure_raw).hexdigest(),
        lineage["occurrence_id"],
        lineage["target_tape_namespace_id"],
        lineage["context_id"],
        lineage["arm"],
        tuple(events),
        tuple(
            sorted(evidence_by_key.values(), key=lambda item: item.evidence_id)
        ),
        tuple(
            sorted(
                freeze_by_key.values(),
                key=lambda item: (
                    item.row_binding_id,
                    item.validation_epoch_index,
                ),
            )
        ),
        tuple(item.batch_id for item in batches),
        sum(item.accepted_draw_count for item in batches),
        required_discovery_rows,
        required_schedule,
        transcript_id,
        (
            V075BatchLifecycleTerminalCodeV2
            .COMPLETE_OBSERVED_REQUIRED_ROWS_CONSTRUCTION_CONTROL
        ),
    )


def freeze_v075_construction_batch_occurrence_lifecycle_v2(
    *,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    lineage_bytes: bytes,
    batch_closure_bytes: bytes,
) -> V075BatchOccurrenceLifecycleClosureV2:
    """Freeze a construction lifecycle from bytes, never from hidden objects."""

    if (
        type(lineage) is not batched_v2.V075BatchOccurrenceLineageV2
        or lineage.scope
        is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
        or type(lineage_bytes) is not bytes
        or lineage.canonical_bytes != lineage_bytes
        or type(batch_closure_bytes) is not bytes
        or lineage.closure.canonical_bytes != batch_closure_bytes
    ):
        _fail("construction V2 lifecycle inputs are mistyped or transplanted")
    semantic_streams = tuple(
        sorted(
            {
                batch.request.stream_identity.stream_id: (
                    batch.request.stream_identity
                )
                for batch in lineage.batches
            }.values(),
            key=lambda item: item.stream_id,
        )
    )
    result = _derive_lifecycle(
        lineage_raw=lineage_bytes,
        batch_closure_raw=batch_closure_bytes,
        semantic_streams=semantic_streams,
        issuer=_DERIVATION_CONSTRUCTION_ISSUER,
    )
    if result.scope is not V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY:
        _fail("construction lifecycle cannot acquire production scope")
    return result


def _replay_production_lineage_authority_v2(
    *,
    repository_root: str | Path,
    occurrence_identity: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    lineage_bytes: bytes,
    batch_closure_bytes: bytes,
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    known_stream_identities: tuple[
        public_graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[Any],
) -> tuple[
    batched_v2.V075BatchOccurrenceLineageV2,
    batched_v2.V075ProductionBatchOccurrenceLineageVerificationV2,
]:
    """Invoke the upstream RSA/private replay before any production claim."""

    try:
        lineage, verification = (
            batched_v2.freeze_v075_production_batch_occurrence_lineage_v2(
                repository_root=repository_root,
                occurrence_identity=occurrence_identity,
                batch_closure_bytes=batch_closure_bytes,
                private_reveal_attestation_bytes=(
                    private_reveal_attestation_bytes
                ),
                claimed_authorization_bytes=claimed_authorization_bytes,
                namespace_bytes=namespace_bytes,
                known_stream_identities=known_stream_identities,
                private_salt=private_salt,
                private_environment=private_environment,
            )
        )
    except (
        batched_v2.V075BatchedObserverV2InvariantViolation,
        observer_v2.V075PrivateObserverBoundaryV2InvariantViolation,
    ) as error:
        raise V075BatchOccurrenceLifecycleV2InvariantViolation(
            str(error)
        ) from error
    if (
        type(lineage)
        is not batched_v2.V075BatchOccurrenceLineageV2
        or lineage.scope
        is not (
            batched_v2.V075BatchOccurrenceAuthorityScopeV2
            .PRODUCTION_BYTE_REPLAY
        )
        or type(verification)
        is not (
            batched_v2.V075ProductionBatchOccurrenceLineageVerificationV2
        )
        or type(lineage_bytes) is not bytes
        or lineage.canonical_bytes != lineage_bytes
        or lineage.closure.canonical_bytes != batch_closure_bytes
        or verification.lineage_id != lineage.lineage_id
    ):
        _fail(
            "production lifecycle upstream lineage bytes or RSA/private "
            "replay differ"
        )
    return lineage, verification


_LIFECYCLE_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchOccurrenceLifecycleVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    scope: V075BatchLifecycleAuthorityScopeV2
    lifecycle_closure_id: str
    lineage_id: str
    occurrence_id: str
    transcript_id: str
    batch_count: int
    event_count: int
    support_evidence_count: int
    support_freeze_count: int
    accepted_draw_count: int
    upstream_production_lineage_verification_id: str | None
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.lifecycle_closure_id,
            self.lineage_id,
            self.occurrence_id,
            self.transcript_id,
        ):
            _cid(value, "V2 lifecycle verification binding")
        if self.upstream_production_lineage_verification_id is not None:
            _cid(
                self.upstream_production_lineage_verification_id,
                "upstream production lineage verification",
            )
        production = (
            self.scope
            is V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
        )
        if (
            self._issuer is not _LIFECYCLE_VERIFICATION_ISSUER
            or type(self.scope) is not V075BatchLifecycleAuthorityScopeV2
            or any(
                type(value) is not int or value <= 0
                for value in (
                    self.batch_count,
                    self.event_count,
                    self.support_evidence_count,
                    self.support_freeze_count,
                    self.accepted_draw_count,
                )
            )
            or production
            != (self.upstream_production_lineage_verification_id is not None)
        ):
            _fail("V2 lifecycle verification is caller-minted or empty")
        object.__setattr__(
            self,
            "_verification_id",
            _hash(
                (
                    "production_lifecycle_verification"
                    if production
                    else "construction_lifecycle_verification"
                ),
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_batch_occurrence_lifecycle_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "lifecycle_closure_id": self.lifecycle_closure_id,
            "lineage_id": self.lineage_id,
            "occurrence_id": self.occurrence_id,
            "transcript_id": self.transcript_id,
            "batch_count": self.batch_count,
            "event_count": self.event_count,
            "support_evidence_count": self.support_evidence_count,
            "support_freeze_count": self.support_freeze_count,
            "accepted_draw_count": self.accepted_draw_count,
            "upstream_production_lineage_verification_id": (
                self.upstream_production_lineage_verification_id
            ),
            "verification_result": (
                "EXACT_V2_PRODUCTION_BATCH_LIFECYCLE_REPLAY_VERIFIED"
                if self.scope
                is V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
                else "EXACT_V2_CONSTRUCTION_BATCH_LIFECYCLE_BYTES_REPLAY_VERIFIED"
            ),
            "support_freeze_causality_verified": True,
            "batch_intervals_verified": True,
            "production_portable_artifacts_bytes_only": True,
            "trusted_private_inputs_serialized": False,
            "typed_public_streams_semantically_replayed": (
                self.scope
                is V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
            ),
            "per_draw_records_replayed": 0,
            "target_accessed": False,
            "legacy_v1_projection_used": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "production_positive_path_ready": False,
            "production_positive_path_blocker": (
                PRODUCTION_POSITIVE_PATH_BLOCKER
            ),
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_batch_occurrence_lifecycle_bytes_v2(
    *,
    lifecycle_bytes: bytes,
    lineage_bytes: bytes,
    batch_closure_bytes: bytes,
    known_stream_identities: tuple[
        public_graph.V075TransitionStreamIdentityV1,
        ...,
    ],
) -> tuple[
    V075BatchOccurrenceLifecycleClosureV2,
    V075BatchOccurrenceLifecycleVerificationV2,
]:
    """Replay a construction lifecycle; production requires the RSA gate."""

    expected = _derive_lifecycle(
        lineage_raw=lineage_bytes,
        batch_closure_raw=batch_closure_bytes,
        semantic_streams=known_stream_identities,
        issuer=_DERIVATION_CONSTRUCTION_ISSUER,
    )
    if (
        expected.scope
        is not V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail(
            "generic lifecycle byte replay is construction-only; production "
            "requires upstream RSA/private lineage verification"
        )
    claimed = _load_document(lifecycle_bytes, "V2 lifecycle closure")
    if (
        canonical_json_bytes(claimed) != expected.canonical_bytes
        or lifecycle_bytes != expected.canonical_bytes
    ):
        _fail("claimed V2 lifecycle differs from deterministic byte replay")
    verification = V075BatchOccurrenceLifecycleVerificationV2(
        _LIFECYCLE_VERIFICATION_ISSUER,
        V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY,
        expected.closure_id,
        expected.lineage_id,
        expected.occurrence_id,
        expected.transcript_id,
        len(expected.batch_ids),
        len(expected.events),
        len(expected.support_evidence),
        len(expected.support_freezes),
        expected.accepted_draw_count,
        None,
    )
    return expected, verification


def verify_v075_production_batch_occurrence_lifecycle_v2(
    *,
    lifecycle_bytes: bytes,
    lineage_bytes: bytes,
    batch_closure_bytes: bytes,
    repository_root: str | Path,
    occurrence_identity: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    known_stream_identities: tuple[
        public_graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[Any],
) -> tuple[
    V075BatchOccurrenceLifecycleClosureV2,
    V075BatchOccurrenceLifecycleVerificationV2,
]:
    """Reject production credit until a preregistered schedule is authoritative."""

    if not PRODUCTION_POSITIVE_PATH_READY:
        raise V075ProductionPositiveLifecycleV2NotReady(
            PRODUCTION_POSITIVE_PATH_BLOCKER
        )

    replayed_lineage, upstream = _replay_production_lineage_authority_v2(
        repository_root=repository_root,
        occurrence_identity=occurrence_identity,
        lineage_bytes=lineage_bytes,
        batch_closure_bytes=batch_closure_bytes,
        private_reveal_attestation_bytes=private_reveal_attestation_bytes,
        claimed_authorization_bytes=claimed_authorization_bytes,
        namespace_bytes=namespace_bytes,
        known_stream_identities=known_stream_identities,
        private_salt=private_salt,
        private_environment=private_environment,
    )
    expected = _derive_lifecycle(
        lineage_raw=lineage_bytes,
        batch_closure_raw=batch_closure_bytes,
        semantic_streams=tuple(
            sorted(
                {
                    batch.request.stream_identity.stream_id: (
                        batch.request.stream_identity
                    )
                    for batch in replayed_lineage.batches
                }.values(),
                key=lambda item: item.stream_id,
            )
        ),
        issuer=_DERIVATION_PRODUCTION_ISSUER,
    )
    if (
        expected.scope
        is not V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
        or type(lifecycle_bytes) is not bytes
        or lifecycle_bytes != expected.canonical_bytes
    ):
        _fail("claimed production lifecycle differs from authoritative replay")
    verification = V075BatchOccurrenceLifecycleVerificationV2(
        _LIFECYCLE_VERIFICATION_ISSUER,
        V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY,
        expected.closure_id,
        expected.lineage_id,
        expected.occurrence_id,
        expected.transcript_id,
        len(expected.batch_ids),
        len(expected.events),
        len(expected.support_evidence),
        len(expected.support_freezes),
        expected.accepted_draw_count,
        upstream.verification_id,
    )
    return expected, verification


_FAILURE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchOccurrenceFailureClosureV2:
    _issuer: object = field(repr=False, compare=False)
    scope: V075BatchLifecycleAuthorityScopeV2
    lineage_id: str
    lineage_bytes_sha256: str
    batch_closure_id: str
    batch_closure_bytes_sha256: str
    occurrence_id: str
    terminal_code: V075BatchFailureTerminalCodeV2
    abort_stage: str
    observed_batch_ids: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]
    work_artifact_ids: tuple[str, ...]
    lifecycle_closure_id: str | None
    cap_profile_id: str | None
    violation_id: str | None
    policy_abort_failure_probability: Fraction | None
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.lineage_id, "V2 failure lineage"),
            (self.lineage_bytes_sha256, "V2 failure lineage bytes"),
            (self.batch_closure_id, "V2 failure batch closure"),
            (
                self.batch_closure_bytes_sha256,
                "V2 failure batch closure bytes",
            ),
            (self.occurrence_id, "V2 failure occurrence"),
        ):
            _cid(value, label)
        _token(self.abort_stage, "V2 failure abort stage")
        for value in (
            *self.observed_batch_ids,
            *self.source_artifact_ids,
            *self.work_artifact_ids,
        ):
            _cid(value, "V2 failure artifact")
        for value, label in (
            (self.lifecycle_closure_id, "V2 failure lifecycle"),
            (self.cap_profile_id, "V2 failure cap profile"),
            (self.violation_id, "V2 failure violation"),
        ):
            if value is not None:
                _cid(value, label)
        cap = self.terminal_code is V075BatchFailureTerminalCodeV2.CAP_EXHAUSTED
        protocol = (
            self.terminal_code
            is V075BatchFailureTerminalCodeV2.PROTOCOL_FAILURE
        )
        integrity = (
            self.terminal_code
            is V075BatchFailureTerminalCodeV2.INTEGRITY_FAILURE
        )
        policy_abort = (
            self.terminal_code
            is V075BatchFailureTerminalCodeV2.POLICY_ABORT_NONCERTIFICATE
        )
        if (
            self._issuer is not _FAILURE_ISSUER
            or type(self.scope) is not V075BatchLifecycleAuthorityScopeV2
            or type(self.terminal_code) is not V075BatchFailureTerminalCodeV2
            or type(self.observed_batch_ids) is not tuple
            or self.observed_batch_ids
            != tuple(dict.fromkeys(self.observed_batch_ids))
            or len(self.observed_batch_ids) > observer_v2.MAX_BATCHES_PER_SESSION
            or type(self.source_artifact_ids) is not tuple
            or not self.source_artifact_ids
            or self.source_artifact_ids
            != tuple(sorted(set(self.source_artifact_ids)))
            or len(self.source_artifact_ids) > MAX_FAILURE_REFERENCES
            or type(self.work_artifact_ids) is not tuple
            or not self.work_artifact_ids
            or self.work_artifact_ids
            != tuple(sorted(set(self.work_artifact_ids)))
            or len(self.work_artifact_ids) > MAX_FAILURE_REFERENCES
            or cap
            != (
                self.cap_profile_id is not None
                and self.violation_id is None
                and self.lifecycle_closure_id is None
                and self.policy_abort_failure_probability is None
            )
            or (protocol or integrity)
            != (
                self.violation_id is not None
                and self.cap_profile_id is None
                and self.lifecycle_closure_id is None
                and self.policy_abort_failure_probability is None
            )
            or policy_abort
            != (
                self.lifecycle_closure_id is not None
                and self.cap_profile_id is None
                and self.violation_id is None
                and type(self.policy_abort_failure_probability) is Fraction
                and 0 < self.policy_abort_failure_probability <= 1
            )
        ):
            _fail(
                "V2 failure code-specific fields are mixed, missing, or "
                "caller-minted"
            )
        object.__setattr__(
            self,
            "_closure_id",
            _hash(
                (
                    "production_failure"
                    if self.scope
                    is V075BatchLifecycleAuthorityScopeV2
                    .PRODUCTION_BYTE_REPLAY
                    else "construction_failure"
                ),
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batch_occurrence_failure_closure.v2",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "lineage_id": self.lineage_id,
            "lineage_bytes_sha256": self.lineage_bytes_sha256,
            "batch_closure_id": self.batch_closure_id,
            "batch_closure_bytes_sha256": self.batch_closure_bytes_sha256,
            "occurrence_id": self.occurrence_id,
            "terminal_scope": "ROUTE_ATTEMPT",
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": self.terminal_code.value,
            "abort_stage": self.abort_stage,
            "observed_batch_ids": list(self.observed_batch_ids),
            "source_artifact_ids": list(self.source_artifact_ids),
            "work_artifact_ids": list(self.work_artifact_ids),
            "lifecycle_closure_id": self.lifecycle_closure_id,
            "cap_profile_id": self.cap_profile_id,
            "violation_id": self.violation_id,
            "policy_abort_failure_probability": (
                None
                if self.policy_abort_failure_probability is None
                else _fraction_document(
                    self.policy_abort_failure_probability
                )
            ),
            "all_observed_batch_prefix_retained": True,
            "all_work_and_result_references_retained": True,
            "missing_work_inferred_as_zero": False,
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "private_material_serialized": False,
            "legacy_v1_projection_used": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "development_scope_only": (
                self.scope
                is V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY
            ),
            "production_verified": False,
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def freeze_v075_batch_occurrence_failure_closure_v2(
    *,
    lineage_bytes: bytes,
    batch_closure_bytes: bytes,
    terminal_code: V075BatchFailureTerminalCodeV2,
    abort_stage: str,
    observed_batch_count: int,
    source_artifact_ids: tuple[str, ...],
    work_artifact_ids: tuple[str, ...],
    known_stream_identities: tuple[
        public_graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    lifecycle_bytes: bytes | None = None,
    cap_profile_id: str | None = None,
    violation_id: str | None = None,
    policy_abort_failure_probability: Fraction | None = None,
) -> V075BatchOccurrenceFailureClosureV2:
    """Close one noncertificate route attempt while retaining its exact prefix."""

    lineage = _replay_lineage_document(lineage_bytes)
    if (
        _scope_from_lineage(lineage)
        is not V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail(
            "generic failure freeze is construction-only; production "
            "requires upstream RSA/private lineage verification"
        )
    batch_closure, batches = _replay_batch_closure_document(
        batch_closure_bytes,
        lineage=lineage,
    )
    if (
        type(terminal_code) is not V075BatchFailureTerminalCodeV2
        or type(observed_batch_count) is not int
        or not 0 <= observed_batch_count <= len(batches)
        or type(source_artifact_ids) is not tuple
        or type(work_artifact_ids) is not tuple
    ):
        _fail("V2 failure close inputs are mistyped or exceed the prefix")
    lifecycle_id: str | None = None
    if lifecycle_bytes is not None:
        replayed_lifecycle, _verification = (
            verify_v075_batch_occurrence_lifecycle_bytes_v2(
                lifecycle_bytes=lifecycle_bytes,
                lineage_bytes=lineage_bytes,
                batch_closure_bytes=batch_closure_bytes,
                known_stream_identities=known_stream_identities,
            )
        )
        lifecycle_id = replayed_lifecycle.closure_id
    return V075BatchOccurrenceFailureClosureV2(
        _FAILURE_ISSUER,
        _scope_from_lineage(lineage),
        lineage["lineage_id"],
        hashlib.sha256(lineage_bytes).hexdigest(),
        batch_closure["closure_id"],
        hashlib.sha256(batch_closure_bytes).hexdigest(),
        lineage["occurrence_id"],
        terminal_code,
        abort_stage,
        tuple(item.batch_id for item in batches[:observed_batch_count]),
        tuple(sorted(source_artifact_ids)),
        tuple(sorted(work_artifact_ids)),
        lifecycle_id,
        cap_profile_id,
        violation_id,
        policy_abort_failure_probability,
    )


_FAILURE_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075BatchOccurrenceFailureVerificationV2:
    _issuer: object = field(repr=False, compare=False)
    scope: V075BatchLifecycleAuthorityScopeV2
    failure_closure_id: str
    lineage_id: str
    occurrence_id: str
    terminal_code: V075BatchFailureTerminalCodeV2
    observed_batch_count: int
    upstream_production_lineage_verification_id: str | None
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.failure_closure_id,
            self.lineage_id,
            self.occurrence_id,
        ):
            _cid(value, "V2 failure verification binding")
        if self.upstream_production_lineage_verification_id is not None:
            _cid(
                self.upstream_production_lineage_verification_id,
                "V2 failure upstream lineage verification",
            )
        production = (
            self.scope
            is V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
        )
        if (
            self._issuer is not _FAILURE_VERIFICATION_ISSUER
            or type(self.scope) is not V075BatchLifecycleAuthorityScopeV2
            or type(self.terminal_code) is not V075BatchFailureTerminalCodeV2
            or type(self.observed_batch_count) is not int
            or self.observed_batch_count < 0
            or production
            != (self.upstream_production_lineage_verification_id is not None)
        ):
            _fail("V2 failure verification is caller-minted")
        object.__setattr__(
            self,
            "_verification_id",
            _hash(
                (
                    "production_failure_verification"
                    if production
                    else "construction_failure_verification"
                ),
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        production = (
            self.scope
            is V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
        )
        return {
            "schema": (
                "acfqp.v075_batch_occurrence_failure_verification.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "failure_closure_id": self.failure_closure_id,
            "lineage_id": self.lineage_id,
            "occurrence_id": self.occurrence_id,
            "terminal_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_code": self.terminal_code.value,
            "observed_batch_count": self.observed_batch_count,
            "upstream_production_lineage_verification_id": (
                self.upstream_production_lineage_verification_id
            ),
            "verification_result": (
                "EXACT_V2_PRODUCTION_FAILURE_CLOSURE_REPLAY_VERIFIED"
                if production
                else "EXACT_V2_CONSTRUCTION_FAILURE_CLOSURE_BYTES_REPLAY_VERIFIED"
            ),
            "plan_certificate": False,
            "infeasibility_certificate": False,
            "production_portable_artifacts_bytes_only": True,
            "trusted_private_inputs_serialized": False,
            "typed_public_streams_semantically_replayed": (
                self.scope
                is V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
            ),
            "target_accessed": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
            "development_scope_only": (
                self.scope
                is V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY
            ),
            "production_verified": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_v075_batch_occurrence_failure_bytes_v2(
    *,
    failure_bytes: bytes,
    lineage_bytes: bytes,
    batch_closure_bytes: bytes,
    known_stream_identities: tuple[
        public_graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    lifecycle_bytes: bytes | None = None,
) -> tuple[
    V075BatchOccurrenceFailureClosureV2,
    V075BatchOccurrenceFailureVerificationV2,
]:
    """Replay one failure closure from canonical bytes only."""

    document = _load_document(failure_bytes, "V2 failure closure")
    try:
        terminal_code = V075BatchFailureTerminalCodeV2(
            document["terminal_code"]
        )
        probability = (
            None
            if document["policy_abort_failure_probability"] is None
            else _fraction_from_document(
                document["policy_abort_failure_probability"],
                "V2 policy-abort probability",
            )
        )
    except (KeyError, ValueError) as error:
        raise V075BatchOccurrenceLifecycleV2InvariantViolation(
            "V2 failure terminal code or probability is invalid"
        ) from error
    expected = freeze_v075_batch_occurrence_failure_closure_v2(
        lineage_bytes=lineage_bytes,
        batch_closure_bytes=batch_closure_bytes,
        terminal_code=terminal_code,
        abort_stage=document.get("abort_stage"),
        observed_batch_count=len(document.get("observed_batch_ids", [])),
        source_artifact_ids=tuple(document.get("source_artifact_ids", [])),
        work_artifact_ids=tuple(document.get("work_artifact_ids", [])),
        known_stream_identities=known_stream_identities,
        lifecycle_bytes=lifecycle_bytes,
        cap_profile_id=document.get("cap_profile_id"),
        violation_id=document.get("violation_id"),
        policy_abort_failure_probability=probability,
    )
    if failure_bytes != expected.canonical_bytes:
        _fail("claimed V2 failure closure differs from byte replay")
    verification = V075BatchOccurrenceFailureVerificationV2(
        _FAILURE_VERIFICATION_ISSUER,
        V075BatchLifecycleAuthorityScopeV2.CONSTRUCTION_ONLY,
        expected.closure_id,
        expected.lineage_id,
        expected.occurrence_id,
        expected.terminal_code,
        len(expected.observed_batch_ids),
        None,
    )
    return expected, verification


def verify_v075_production_batch_occurrence_failure_v2(
    *,
    failure_bytes: bytes,
    lineage_bytes: bytes,
    batch_closure_bytes: bytes,
    lifecycle_bytes: bytes | None,
    repository_root: str | Path,
    occurrence_identity: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    private_reveal_attestation_bytes: bytes,
    claimed_authorization_bytes: bytes,
    namespace_bytes: bytes,
    known_stream_identities: tuple[
        public_graph.V075TransitionStreamIdentityV1,
        ...,
    ],
    private_salt: bytes,
    private_environment: Iterable[Any],
) -> tuple[
    V075BatchOccurrenceFailureClosureV2,
    V075BatchOccurrenceFailureVerificationV2,
]:
    """Remain closed until every external failure authority is integrated."""

    if not PRODUCTION_FAILURE_AUTHORITY_READY:
        raise V075ProductionFailureAuthorityV2NotReady(
            PRODUCTION_FAILURE_BLOCKER
        )

    replayed_lineage, upstream = _replay_production_lineage_authority_v2(
        repository_root=repository_root,
        occurrence_identity=occurrence_identity,
        lineage_bytes=lineage_bytes,
        batch_closure_bytes=batch_closure_bytes,
        private_reveal_attestation_bytes=private_reveal_attestation_bytes,
        claimed_authorization_bytes=claimed_authorization_bytes,
        namespace_bytes=namespace_bytes,
        known_stream_identities=known_stream_identities,
        private_salt=private_salt,
        private_environment=private_environment,
    )
    lineage = _replay_lineage_document(lineage_bytes)
    batch_closure, batches = _replay_batch_closure_document(
        batch_closure_bytes,
        lineage=lineage,
    )
    document = _load_document(failure_bytes, "production V2 failure closure")
    try:
        terminal_code = V075BatchFailureTerminalCodeV2(
            document["terminal_code"]
        )
        probability = (
            None
            if document["policy_abort_failure_probability"] is None
            else _fraction_from_document(
                document["policy_abort_failure_probability"],
                "production V2 policy-abort probability",
            )
        )
        observed = tuple(document["observed_batch_ids"])
        source_ids = tuple(document["source_artifact_ids"])
        work_ids = tuple(document["work_artifact_ids"])
    except (KeyError, TypeError, ValueError) as error:
        raise V075BatchOccurrenceLifecycleV2InvariantViolation(
            "production V2 failure document is incomplete"
        ) from error
    if observed != tuple(item.batch_id for item in batches[: len(observed)]):
        _fail("production V2 failure observed registry is not one exact prefix")
    lifecycle_id: str | None = None
    if lifecycle_bytes is not None:
        expected_lifecycle = _derive_lifecycle(
            lineage_raw=lineage_bytes,
            batch_closure_raw=batch_closure_bytes,
            semantic_streams=tuple(
                sorted(
                    {
                        batch.request.stream_identity.stream_id: (
                            batch.request.stream_identity
                        )
                        for batch in replayed_lineage.batches
                    }.values(),
                    key=lambda item: item.stream_id,
                )
            ),
            issuer=_DERIVATION_PRODUCTION_ISSUER,
        )
        if (
            expected_lifecycle.scope
            is not V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY
            or lifecycle_bytes != expected_lifecycle.canonical_bytes
        ):
            _fail("production failure carries a foreign lifecycle closure")
        lifecycle_id = expected_lifecycle.closure_id
    expected = V075BatchOccurrenceFailureClosureV2(
        _FAILURE_ISSUER,
        V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY,
        lineage["lineage_id"],
        hashlib.sha256(lineage_bytes).hexdigest(),
        batch_closure["closure_id"],
        hashlib.sha256(batch_closure_bytes).hexdigest(),
        lineage["occurrence_id"],
        terminal_code,
        document.get("abort_stage"),
        observed,
        tuple(sorted(source_ids)),
        tuple(sorted(work_ids)),
        lifecycle_id,
        document.get("cap_profile_id"),
        document.get("violation_id"),
        probability,
    )
    if failure_bytes != expected.canonical_bytes:
        _fail("claimed production V2 failure closure differs from replay")
    verification = V075BatchOccurrenceFailureVerificationV2(
        _FAILURE_VERIFICATION_ISSUER,
        V075BatchLifecycleAuthorityScopeV2.PRODUCTION_BYTE_REPLAY,
        expected.closure_id,
        expected.lineage_id,
        expected.occurrence_id,
        expected.terminal_code,
        len(expected.observed_batch_ids),
        upstream.verification_id,
    )
    return expected, verification


__all__ = [
    "DOMAIN_TAGS",
    "LEGACY_OBSERVER_AUTHORITY_PROJECTION_ALLOWED",
    "LEGACY_TARGET_NAMESPACE_PROJECTION_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PER_DRAW_EXPANSION_ALLOWED",
    "PRODUCTION_FAILURE_AUTHORITY_READY",
    "PRODUCTION_FAILURE_BLOCKER",
    "PRODUCTION_POSITIVE_PATH_BLOCKER",
    "PRODUCTION_POSITIVE_PATH_READY",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "TARGET_ACCESS_ALLOWED",
    "V075BatchFailureTerminalCodeV2",
    "V075BatchLifecycleAuthorityScopeV2",
    "V075BatchLifecycleEventKindV2",
    "V075BatchLifecycleTerminalCodeV2",
    "V075BatchLifecycleEventV2",
    "V075BatchOccurrenceFailureClosureV2",
    "V075BatchOccurrenceFailureVerificationV2",
    "V075BatchOccurrenceLifecycleClosureV2",
    "V075BatchOccurrenceLifecycleV2InvariantViolation",
    "V075BatchOccurrenceLifecycleVerificationV2",
    "V075BatchSupportEvidenceV2",
    "V075BatchSupportFreezeV2",
    "V075ProductionFailureAuthorityV2NotReady",
    "V075ProductionPositiveLifecycleV2NotReady",
    "freeze_v075_batch_occurrence_failure_closure_v2",
    "freeze_v075_construction_batch_occurrence_lifecycle_v2",
    "verify_v075_batch_occurrence_failure_bytes_v2",
    "verify_v075_batch_occurrence_lifecycle_bytes_v2",
    "verify_v075_production_batch_occurrence_failure_v2",
    "verify_v075_production_batch_occurrence_lifecycle_v2",
]
