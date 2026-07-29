"""Lossless frozen-source, occurrence-parallel execution mechanics.

This module is intentionally a new profile.  It does not change or wrap the
frozen V0-072 production runner.  The bounded profile proves only transport
and scheduling mechanics:

* a complete canonical source document is sealed together with its upstream
  identities and its full offline-work vector;
* the caller must supply the expected identities when loading the archive;
* target occurrences are fresh inputs and no target result/cache input is
  accepted by this API;
* process parallelism is a physical choice outside logical identities; and
* child outputs are independently parsed, rebound, and merged in registered
  occurrence order.

Only explicitly registered synthetic workers are included in V1.  A future
scientific runner must add a separately reviewed worker profile rather than
passing an arbitrary Python callback into this process boundary.
"""

from __future__ import annotations

from concurrent.futures import Future, ProcessPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from multiprocessing import get_context
import os
from typing import Any, Mapping, Sequence

from acfqp.phase3e_ids import (
    FROZEN_SOURCE_ARCHIVE_ENVELOPE_DOMAIN,
    FROZEN_SOURCE_CHILD_ATTEMPT_JOURNAL_DOMAIN,
    FROZEN_SOURCE_EXECUTION_BATCH_DOMAIN,
    FROZEN_SOURCE_OCCURRENCE_FAILURE_CLOSURE_DOMAIN,
    FROZEN_SOURCE_OCCURRENCE_INPUT_DOMAIN,
    FROZEN_SOURCE_OCCURRENCE_MERGE_DOMAIN,
    FROZEN_SOURCE_OCCURRENCE_OUTPUT_DOMAIN,
    FROZEN_SOURCE_OFFLINE_WORK_DOMAIN,
    FROZEN_SOURCE_VERIFICATION_ATTESTATION_DOMAIN,
    Phase3EIdentityError,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.39.0"
PROFILE_KEY = "v074_frozen_source_occurrence_parallel_v1"
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_TARGET_PAYLOAD_BYTES = 64 * 1024
MAX_OCCURRENCE_BYTES = 128 * 1024
MAX_OCCURRENCE_RESULT_PAYLOAD_BYTES = 128 * 1024
MAX_OCCURRENCE_OUTPUT_BYTES = 192 * 1024
MAX_CHILD_JOURNAL_BYTES = 256 * 1024
MAX_OCCURRENCES = 256
MAX_WORKERS = 192
MAX_COMPOSITE_PER_OCCURRENCE_OVERHEAD_BYTES = 4 * 1024
MAX_COMPOSITE_FIXED_OVERHEAD_BYTES = MAX_ARCHIVE_BYTES + 8 * 1024 * 1024
MAX_COMPOSITE_ARTIFACT_BYTES = (
    MAX_COMPOSITE_FIXED_OVERHEAD_BYTES
    + MAX_OCCURRENCES
    * (
        MAX_CHILD_JOURNAL_BYTES
        + MAX_OCCURRENCE_OUTPUT_BYTES
        + MAX_COMPOSITE_PER_OCCURRENCE_OVERHEAD_BYTES
    )
)

SOURCE_COUNTER_REGISTRY_ID = hashlib.sha256(
    b"acfqp:v074-frozen-source-counter-registry:v1\x00"
    b"source.accepted_draws|source.kernel_transition_calls|"
    b"source.nonkernel_compute_events|source.output_bytes|"
    b"source.peak_mounted_bytes|source.peak_working_bytes|"
    b"source.process_launches|source.read_bytes|source.staged_bytes"
).hexdigest()
REGISTERED_SOURCE_OFFLINE_COUNTERS = (
    "source.accepted_draws",
    "source.kernel_transition_calls",
    "source.nonkernel_compute_events",
    "source.output_bytes",
    "source.peak_mounted_bytes",
    "source.peak_working_bytes",
    "source.process_launches",
    "source.read_bytes",
    "source.staged_bytes",
)
REGISTERED_CHILD_WORK_COUNTERS = (
    "control.child_completed",
    "control.child_failed",
    "control.child_submit_attempts",
    "control.child_submitted",
    "process.child_process_launches",
    "synthetic.registered_worker_events",
)
REGISTERED_OCCURRENCE_ONLINE_COUNTERS = (
    "synthetic.registered_worker_events",
)

_FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "cache",
        "cache_entry",
        "cache_inputs",
        "cache_key",
        "cached_result",
        "certificate",
        "certificate_id",
        "certificate_payload",
        "post_target",
        "post_target_cache",
        "post_target_cache_entry",
        "post_target_observations",
        "prior_certificate",
        "prior_certificates",
        "prior_output",
        "prior_outputs",
        "prior_result",
        "prior_results",
        "prior_target_result_inputs",
        "result",
        "result_artifact",
        "result_artifact_id",
        "result_id",
        "result_payload",
        "resume",
        "resume_from",
        "resume_token",
        "resume_inputs",
        "reuse",
        "reuse_artifact_id",
        "reuse_from",
        "reuse_inputs",
        "target_cache",
        "target_result",
        "target_result_cache",
        "target_observations",
    }
)
_FORBIDDEN_INPUT_SEMANTICS = frozenset(
    {
        "CACHE_HIT",
        "CACHED_RESULT",
        "INFEASIBILITY_CERTIFICATE",
        "PLAN_CERTIFICATE",
        "POST_TARGET",
        "RESUME",
        "REUSE",
        "TARGET_RESULT",
    }
)


class FrozenSourceOccurrenceInvariantViolation(ValueError):
    """A frozen archive, occurrence, output, or merge failed validation."""


class FrozenSourceOccurrenceExecutionFailure(RuntimeError):
    """One or more children failed; accounting closure remains available."""

    def __init__(
        self,
        *,
        failure_closure: OccurrenceFailureClosureV1,
    ) -> None:
        if type(failure_closure) is not OccurrenceFailureClosureV1:
            _fail("execution failure requires one typed failure closure")
        first = (
            failure_closure.failed_attempts[0]
            if failure_closure.failed_attempts
            else None
        )
        self.failure_closure = failure_closure
        self.failure_closure_id = failure_closure.failure_closure_id
        self.failure_closure_bytes = failure_closure.canonical_bytes
        self.occurrence_ordinal = 0 if first is None else first.ordinal
        self.occurrence_id = (
            failure_closure.execution_batch_id
            if first is None
            else first.occurrence_id
        )
        self.failure_kind = (
            failure_closure.batch_failure_code
            if first is None
            else first.failure_code
        )
        self.partial_outputs_retained_for_accounting = True
        self.partial_outputs_scientifically_merged = False
        super().__init__(
            "occurrence execution failed closed at ordinal "
            f"{self.occurrence_ordinal} ({self.occurrence_id}); "
            f"failure closure={failure_closure.failure_closure_id}; "
            "all child journals were retained but no scientific merge "
            "was produced"
        )


class RegisteredOccurrenceWorkerV1(str, Enum):
    """The complete V1 worker registry.

    ``SAFE_SYNTHETIC_HASH_V1`` produces a deterministic echo/hash result.
    ``SAFE_SYNTHETIC_FAIL_V1`` exists solely to exercise fail-closed process
    handling.  Neither worker carries a scientific claim.
    """

    SAFE_SYNTHETIC_HASH_V1 = "SAFE_SYNTHETIC_HASH_V1"
    SAFE_SYNTHETIC_FAIL_V1 = "SAFE_SYNTHETIC_FAIL_V1"
    SAFE_SYNTHETIC_MARKED_FAILURE_V1 = (
        "SAFE_SYNTHETIC_MARKED_FAILURE_V1"
    )


def _fail(message: str) -> None:
    raise FrozenSourceOccurrenceInvariantViolation(message)


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise FrozenSourceOccurrenceInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _token(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or not value
        or value.strip() != value
        or "\x00" in value
    ):
        _fail(f"{field} must be one nonempty canonical string")
    return value


def _exact_mapping(
    value: Any,
    *,
    keys: set[str],
    field: str,
) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        _fail(f"{field} has an invalid field set")
    return value


def _canonical_mapping(value: Any, *, field: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{field} must be one JSON object")
    try:
        canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise FrozenSourceOccurrenceInvariantViolation(
            f"{field} is not canonicalizable JSON"
        ) from error
    return value


def _strict_load(raw: Any, *, maximum_bytes: int, field: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > maximum_bytes:
        _fail(f"{field} bytes are empty, mistyped, or exceed the frozen cap")
    try:
        value = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise FrozenSourceOccurrenceInvariantViolation(
            f"{field} is not strict canonical JSON"
        ) from error
    if type(value) is not dict:
        _fail(f"{field} must decode to one JSON object")
    return value


def _contains_exact_string(value: Any, forbidden: frozenset[str]) -> bool:
    if type(value) is str:
        return value in forbidden
    if type(value) is list:
        return any(_contains_exact_string(item, forbidden) for item in value)
    if type(value) is dict:
        return any(
            key in forbidden or _contains_exact_string(item, forbidden)
            for key, item in value.items()
        )
    return False


def _normalized_input_key(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _reject_forbidden_input_material(value: Any, *, field: str) -> None:
    """Reject every registered cache/result/certificate transport channel.

    This is deliberately recursive and applies to both keys and explicit
    semantic enum values.  V1 is a proposal-only, no-cache mechanics profile;
    extending the accepted vocabulary requires a contract revision.
    """

    if type(value) is str:
        if value.strip().upper().replace("-", "_") in _FORBIDDEN_INPUT_SEMANTICS:
            _fail(f"{field} contains a forbidden post-target semantic")
        return
    if type(value) is list:
        for item in value:
            _reject_forbidden_input_material(item, field=field)
        return
    if type(value) is dict:
        for key, item in value.items():
            if _normalized_input_key(key) in _FORBIDDEN_INPUT_KEYS:
                _fail(f"{field} contains a forbidden cache/reuse/result key")
            _reject_forbidden_input_material(item, field=field)


def _sealed_json_object(
    value: Any,
    *,
    field: str,
    maximum_bytes: int | None = None,
    reject_transport_material: bool = False,
) -> tuple[bytes, dict[str, Any]]:
    canonical = canonical_json_bytes(_canonical_mapping(value, field=field))
    if maximum_bytes is not None and len(canonical) > maximum_bytes:
        _fail(f"{field} exceeds its frozen canonical-byte cap")
    decoded = loads_canonical_json(canonical)
    if type(decoded) is not dict:  # pragma: no cover - canonical constructor
        _fail(f"{field} is no longer a JSON object")
    if reject_transport_material:
        _reject_forbidden_input_material(decoded, field=field)
    return canonical, decoded


@dataclass(frozen=True, slots=True)
class FrozenSourceOfflineWorkV1:
    """Exact source-only work retained once in every merged campaign."""

    counters: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if (
            type(self.counters) is not tuple
            or not self.counters
            or any(
                type(item) is not tuple or len(item) != 2
                for item in self.counters
            )
        ):
            _fail("source offline work must be one nonempty immutable vector")
        names: list[str] = []
        for name, value in self.counters:
            names.append(_token(name, "source offline counter name"))
            if type(value) is not int or value < 0:
                _fail("source offline counter values must be nonnegative ints")
        if tuple(names) != REGISTERED_SOURCE_OFFLINE_COUNTERS:
            _fail(
                "source offline work must contain the complete registered "
                "counter vocabulary, including native zeros"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_source_offline_work.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "counters": [
                {"counter": name, "value": value}
                for name, value in self.counters
            ],
            "source_only": True,
            "offline_work_retained": True,
            "parallel_wall_time_discount_applied": False,
            "counter_registry_id": SOURCE_COUNTER_REGISTRY_ID,
            "native_zero_required": True,
        }

    @property
    def work_id(self) -> str:
        return content_id(FROZEN_SOURCE_OFFLINE_WORK_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}

    @classmethod
    def from_document(cls, document: Any) -> FrozenSourceOfflineWorkV1:
        item = _exact_mapping(
            document,
            keys={
                "schema",
                "schema_version",
                "profile_key",
                "counters",
                "source_only",
                "offline_work_retained",
                "parallel_wall_time_discount_applied",
                "counter_registry_id",
                "native_zero_required",
                "work_id",
            },
            field="source offline work",
        )
        if (
            item["schema"] != "acfqp.frozen_source_offline_work.v1"
            or item["schema_version"] != SCHEMA_VERSION
            or item["profile_key"] != PROFILE_KEY
            or item["source_only"] is not True
            or item["offline_work_retained"] is not True
            or item["parallel_wall_time_discount_applied"] is not False
            or item["counter_registry_id"] != SOURCE_COUNTER_REGISTRY_ID
            or item["native_zero_required"] is not True
            or type(item["counters"]) is not list
        ):
            _fail("source offline work contract changed")
        counters: list[tuple[str, int]] = []
        for index, record in enumerate(item["counters"]):
            parsed = _exact_mapping(
                record,
                keys={"counter", "value"},
                field=f"source offline counters[{index}]",
            )
            counters.append((parsed["counter"], parsed["value"]))
        result = cls(tuple(counters))
        if result.work_id != _cid(item["work_id"], "source offline work"):
            _fail("source offline work content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class FrozenSourceVerificationAttestationV1:
    """Typed source-only attestation bound to exact bytes and work."""

    upstream_archive_id: str
    source_scope_id: str
    semantic_verifier_id: str
    verification_profile_id: str
    counter_registry_id: str
    source_document_sha256: str
    offline_work_id: str

    def __post_init__(self) -> None:
        values = (
            (self.upstream_archive_id, "attested upstream archive"),
            (self.source_scope_id, "attested source scope"),
            (self.semantic_verifier_id, "semantic verifier"),
            (self.verification_profile_id, "verification profile"),
            (self.counter_registry_id, "counter registry"),
            (self.source_document_sha256, "source document digest"),
            (self.offline_work_id, "attested offline work"),
        )
        for value, name in values:
            _cid(value, name)
        if self.counter_registry_id != SOURCE_COUNTER_REGISTRY_ID:
            _fail("source attestation uses an unregistered counter registry")
        if len({value for value, _ in values}) != len(values):
            _fail("source attestation identities must be role-distinct")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_source_verification_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "upstream_archive_id": self.upstream_archive_id,
            "source_scope_id": self.source_scope_id,
            "semantic_verifier_id": self.semantic_verifier_id,
            "verification_profile_id": self.verification_profile_id,
            "counter_registry_id": self.counter_registry_id,
            "source_document_sha256": self.source_document_sha256,
            "offline_work_id": self.offline_work_id,
            "verification_result": "VERIFIED_SOURCE_ONLY",
            "target_authority": False,
        }

    @property
    def attestation_id(self) -> str:
        return content_id(
            FROZEN_SOURCE_VERIFICATION_ATTESTATION_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}

    @classmethod
    def from_document(
        cls,
        document: Any,
    ) -> FrozenSourceVerificationAttestationV1:
        item = _exact_mapping(
            document,
            keys={
                "schema",
                "schema_version",
                "profile_key",
                "upstream_archive_id",
                "source_scope_id",
                "semantic_verifier_id",
                "verification_profile_id",
                "counter_registry_id",
                "source_document_sha256",
                "offline_work_id",
                "verification_result",
                "target_authority",
                "attestation_id",
            },
            field="source verification attestation",
        )
        if (
            item["schema"]
            != "acfqp.frozen_source_verification_attestation.v1"
            or item["schema_version"] != SCHEMA_VERSION
            or item["profile_key"] != PROFILE_KEY
            or item["verification_result"] != "VERIFIED_SOURCE_ONLY"
            or item["target_authority"] is not False
        ):
            _fail("source verification attestation contract changed")
        result = cls(
            upstream_archive_id=item["upstream_archive_id"],
            source_scope_id=item["source_scope_id"],
            semantic_verifier_id=item["semantic_verifier_id"],
            verification_profile_id=item["verification_profile_id"],
            counter_registry_id=item["counter_registry_id"],
            source_document_sha256=item["source_document_sha256"],
            offline_work_id=item["offline_work_id"],
        )
        if result.attestation_id != _cid(
            item["attestation_id"],
            "source verification attestation",
        ):
            _fail("source verification attestation content ID mismatch")
        return result


def mint_frozen_source_verification_attestation_v1(
    *,
    upstream_archive_id: str,
    source_scope_id: str,
    semantic_verifier_id: str,
    verification_profile_id: str,
    source_document: Mapping[str, Any],
    offline_work: FrozenSourceOfflineWorkV1,
) -> FrozenSourceVerificationAttestationV1:
    source_bytes, _ = _sealed_json_object(
        source_document,
        field="source document",
        reject_transport_material=True,
    )
    if type(offline_work) is not FrozenSourceOfflineWorkV1:
        _fail("source attestation requires typed offline work")
    return FrozenSourceVerificationAttestationV1(
        upstream_archive_id=upstream_archive_id,
        source_scope_id=source_scope_id,
        semantic_verifier_id=semantic_verifier_id,
        verification_profile_id=verification_profile_id,
        counter_registry_id=SOURCE_COUNTER_REGISTRY_ID,
        source_document_sha256=hashlib.sha256(source_bytes).hexdigest(),
        offline_work_id=offline_work.work_id,
    )


@dataclass(frozen=True, slots=True)
class FrozenSourceArchiveEnvelopeV1:
    """Complete byte-sealed source input with no target result material."""

    upstream_archive_id: str
    source_scope_id: str
    source_document: Mapping[str, Any]
    offline_work: FrozenSourceOfflineWorkV1
    verification_attestation: FrozenSourceVerificationAttestationV1
    _sealed_source_document_bytes: bytes = field(
        init=False,
        repr=False,
        compare=True,
    )

    def __post_init__(self) -> None:
        if (
            type(self.verification_attestation)
            is not FrozenSourceVerificationAttestationV1
        ):
            _fail("source envelope verification attestation has the wrong type")
        for value, field in (
            (self.upstream_archive_id, "upstream source archive"),
            (self.source_scope_id, "source scope"),
        ):
            _cid(value, field)
        if len(
            {
                self.upstream_archive_id,
                self.verification_attestation.attestation_id,
                self.source_scope_id,
            }
        ) != 3:
            _fail("source envelope identities must be role-distinct")
        canonical_source, sealed_source = _sealed_json_object(
            self.source_document,
            field="source document",
            reject_transport_material=True,
        )
        object.__setattr__(
            self,
            "_sealed_source_document_bytes",
            canonical_source,
        )
        object.__setattr__(
            self,
            "source_document",
            sealed_source,
        )
        if type(self.offline_work) is not FrozenSourceOfflineWorkV1:
            _fail("source envelope offline work has the wrong type")
        if (
            self.verification_attestation.upstream_archive_id
            != self.upstream_archive_id
            or self.verification_attestation.source_scope_id
            != self.source_scope_id
            or self.verification_attestation.source_document_sha256
            != self.source_document_sha256
            or self.verification_attestation.offline_work_id
            != self.offline_work.work_id
        ):
            _fail("source verification attestation binding mismatch")

    @property
    def upstream_verification_id(self) -> str:
        return self.verification_attestation.attestation_id

    @property
    def sealed_source_document(self) -> dict[str, Any]:
        value = loads_canonical_json(self._sealed_source_document_bytes)
        if type(value) is not dict:  # pragma: no cover - constructor defense
            _fail("sealed source document is no longer an object")
        return value

    @property
    def source_document_sha256(self) -> str:
        return hashlib.sha256(
            self._sealed_source_document_bytes
        ).hexdigest()

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_source_archive_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "upstream_archive_id": self.upstream_archive_id,
            "upstream_verification_id": self.upstream_verification_id,
            "verification_attestation": (
                self.verification_attestation.to_document()
            ),
            "semantic_verifier_id": (
                self.verification_attestation.semantic_verifier_id
            ),
            "verification_profile_id": (
                self.verification_attestation.verification_profile_id
            ),
            "counter_registry_id": SOURCE_COUNTER_REGISTRY_ID,
            "source_scope_id": self.source_scope_id,
            "source_document": self.sealed_source_document,
            "source_document_sha256": self.source_document_sha256,
            "offline_work": self.offline_work.to_document(),
            "offline_work_id": self.offline_work.work_id,
            "source_only": True,
            "source_frozen": True,
            "proposal_only": True,
            "may_certify_target": False,
            "included_target_occurrence_ids": [],
            "target_result_or_certificate_reuse_allowed": False,
            "offline_work_retained": True,
        }

    @property
    def archive_id(self) -> str:
        return content_id(
            FROZEN_SOURCE_ARCHIVE_ENVELOPE_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "archive_id": self.archive_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def freeze_source_archive_envelope_v1(
    *,
    upstream_archive_id: str,
    source_scope_id: str,
    source_document: Mapping[str, Any],
    offline_work: FrozenSourceOfflineWorkV1,
    verification_attestation: FrozenSourceVerificationAttestationV1,
) -> FrozenSourceArchiveEnvelopeV1:
    """Seal a complete source document; no target identity is accepted."""

    result = FrozenSourceArchiveEnvelopeV1(
        upstream_archive_id=upstream_archive_id,
        source_scope_id=source_scope_id,
        source_document=source_document,
        offline_work=offline_work,
        verification_attestation=verification_attestation,
    )
    if len(result.canonical_bytes) > MAX_ARCHIVE_BYTES:
        _fail("frozen source archive exceeds its frozen byte cap")
    return result


def load_frozen_source_archive_envelope_v1(
    raw: bytes,
    *,
    expected_archive_id: str,
    expected_upstream_archive_id: str,
    expected_upstream_verification_id: str,
    expected_offline_work_id: str,
) -> FrozenSourceArchiveEnvelopeV1:
    """Load only the exact externally expected source archive identity."""

    document = _strict_load(
        raw,
        maximum_bytes=MAX_ARCHIVE_BYTES,
        field="frozen source archive",
    )
    item = _exact_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "profile_key",
            "upstream_archive_id",
            "upstream_verification_id",
            "verification_attestation",
            "semantic_verifier_id",
            "verification_profile_id",
            "counter_registry_id",
            "source_scope_id",
            "source_document",
            "source_document_sha256",
            "offline_work",
            "offline_work_id",
            "source_only",
            "source_frozen",
            "proposal_only",
            "may_certify_target",
            "included_target_occurrence_ids",
            "target_result_or_certificate_reuse_allowed",
            "offline_work_retained",
            "archive_id",
        },
        field="frozen source archive",
    )
    if (
        item["schema"] != "acfqp.frozen_source_archive_envelope.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["source_only"] is not True
        or item["source_frozen"] is not True
        or item["proposal_only"] is not True
        or item["may_certify_target"] is not False
        or item["included_target_occurrence_ids"] != []
        or item["target_result_or_certificate_reuse_allowed"] is not False
        or item["offline_work_retained"] is not True
    ):
        _fail("frozen source archive contract changed")
    offline_work = FrozenSourceOfflineWorkV1.from_document(
        item["offline_work"]
    )
    attestation = FrozenSourceVerificationAttestationV1.from_document(
        item["verification_attestation"]
    )
    result = FrozenSourceArchiveEnvelopeV1(
        upstream_archive_id=item["upstream_archive_id"],
        source_scope_id=item["source_scope_id"],
        source_document=_canonical_mapping(
            item["source_document"],
            field="source document",
        ),
        offline_work=offline_work,
        verification_attestation=attestation,
    )
    expected = (
        _cid(expected_archive_id, "expected frozen source archive"),
        _cid(expected_upstream_archive_id, "expected upstream source archive"),
        _cid(
            expected_upstream_verification_id,
            "expected upstream source verification",
        ),
        _cid(expected_offline_work_id, "expected source offline work"),
    )
    claimed = (
        _cid(item["archive_id"], "frozen source archive"),
        result.upstream_archive_id,
        result.upstream_verification_id,
        _cid(item["offline_work_id"], "source offline work reference"),
    )
    if claimed != expected:
        _fail("frozen source archive external identity mismatch")
    if (
        result.archive_id != claimed[0]
        or result.offline_work.work_id != claimed[3]
        or item["semantic_verifier_id"] != attestation.semantic_verifier_id
        or item["verification_profile_id"]
        != attestation.verification_profile_id
        or item["counter_registry_id"] != SOURCE_COUNTER_REGISTRY_ID
        or result.source_document_sha256
        != _cid(item["source_document_sha256"], "source document digest")
        or result.canonical_bytes != raw
    ):
        _fail("frozen source archive content replay mismatch")
    return result


@dataclass(frozen=True, slots=True)
class TargetOccurrenceSpecV1:
    ordinal: int
    occurrence_id: str
    target_scope_id: str
    target_payload: Mapping[str, Any]
    _sealed_target_payload_bytes: bytes = field(
        init=False,
        repr=False,
        compare=True,
    )

    def __post_init__(self) -> None:
        if type(self.ordinal) is not int or self.ordinal <= 0:
            _fail("occurrence ordinal must be a positive integer")
        _cid(self.occurrence_id, "target occurrence")
        _cid(self.target_scope_id, "target scope")
        if self.occurrence_id == self.target_scope_id:
            _fail("target occurrence and scope identities must differ")
        canonical, sealed = _sealed_json_object(
            self.target_payload,
            field="target payload",
            maximum_bytes=MAX_TARGET_PAYLOAD_BYTES,
            reject_transport_material=True,
        )
        object.__setattr__(self, "_sealed_target_payload_bytes", canonical)
        object.__setattr__(self, "target_payload", sealed)

    @property
    def sealed_target_payload(self) -> dict[str, Any]:
        value = loads_canonical_json(self._sealed_target_payload_bytes)
        if type(value) is not dict:  # pragma: no cover
            _fail("sealed target payload is no longer an object")
        return value

    def to_batch_document(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "occurrence_id": self.occurrence_id,
            "target_scope_id": self.target_scope_id,
            "target_payload": self.sealed_target_payload,
        }


def derive_frozen_execution_batch_id_v1(
    *,
    source_archive_id: str,
    attempt_nonce_id: str,
    occurrences: tuple[TargetOccurrenceSpecV1, ...],
    worker_key: RegisteredOccurrenceWorkerV1,
) -> str:
    _cid(source_archive_id, "execution batch source archive")
    _cid(attempt_nonce_id, "execution attempt nonce")
    if (
        type(occurrences) is not tuple
        or not occurrences
        or any(type(item) is not TargetOccurrenceSpecV1 for item in occurrences)
        or type(worker_key) is not RegisteredOccurrenceWorkerV1
    ):
        _fail("execution batch inputs are not frozen typed occurrences")
    return content_id(
        FROZEN_SOURCE_EXECUTION_BATCH_DOMAIN,
        {
            "schema": "acfqp.frozen_source_execution_batch.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_archive_id": source_archive_id,
            "attempt_nonce_id": attempt_nonce_id,
            "worker_key": worker_key.value,
            "occurrences": [item.to_batch_document() for item in occurrences],
            "cache_inputs": [],
            "recomputed_without_cache": True,
            "global_nonce_uniqueness_claimed": False,
        },
    )


@dataclass(frozen=True, slots=True)
class BoundOccurrenceInputV1:
    ordinal: int
    occurrence_id: str
    target_scope_id: str
    target_payload: Mapping[str, Any]
    source_archive_id: str
    execution_batch_id: str
    attempt_nonce_id: str
    worker_key: RegisteredOccurrenceWorkerV1
    _sealed_target_payload_bytes: bytes = field(
        init=False,
        repr=False,
        compare=True,
    )

    def __post_init__(self) -> None:
        sealed_spec = TargetOccurrenceSpecV1(
            self.ordinal,
            self.occurrence_id,
            self.target_scope_id,
            self.target_payload,
        )
        _cid(self.source_archive_id, "bound source archive")
        _cid(self.execution_batch_id, "bound execution batch")
        _cid(self.attempt_nonce_id, "bound attempt nonce")
        if type(self.worker_key) is not RegisteredOccurrenceWorkerV1:
            _fail("occurrence worker is not registered")
        object.__setattr__(
            self,
            "_sealed_target_payload_bytes",
            sealed_spec._sealed_target_payload_bytes,
        )
        object.__setattr__(
            self,
            "target_payload",
            sealed_spec.sealed_target_payload,
        )
        if len(self.canonical_bytes) > MAX_OCCURRENCE_BYTES:
            _fail("bound occurrence input envelope exceeds its replay byte cap")

    @property
    def sealed_target_payload(self) -> dict[str, Any]:
        value = loads_canonical_json(self._sealed_target_payload_bytes)
        if type(value) is not dict:  # pragma: no cover
            _fail("bound target payload is no longer an object")
        return value

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_source_occurrence_input.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "ordinal": self.ordinal,
            "occurrence_id": self.occurrence_id,
            "target_scope_id": self.target_scope_id,
            "target_payload": self.sealed_target_payload,
            "source_archive_id": self.source_archive_id,
            "execution_batch_id": self.execution_batch_id,
            "attempt_nonce_id": self.attempt_nonce_id,
            "worker_key": self.worker_key.value,
            "prior_target_result_inputs": [],
            "target_result_reuse_allowed": False,
            "fresh_execution_required": True,
            "global_nonce_uniqueness_claimed": False,
            "execution_recomputed_without_cache": True,
        }

    @property
    def input_id(self) -> str:
        return content_id(
            FROZEN_SOURCE_OCCURRENCE_INPUT_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "input_id": self.input_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _load_bound_occurrence_input_v1(
    raw: bytes,
    *,
    expected_source_archive_id: str,
    expected_execution_batch_id: str,
    expected_attempt_nonce_id: str,
    expected_worker_key: RegisteredOccurrenceWorkerV1,
) -> BoundOccurrenceInputV1:
    document = _strict_load(
        raw,
        maximum_bytes=MAX_OCCURRENCE_BYTES,
        field="bound occurrence input",
    )
    item = _exact_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "profile_key",
            "ordinal",
            "occurrence_id",
            "target_scope_id",
            "target_payload",
            "source_archive_id",
            "execution_batch_id",
            "attempt_nonce_id",
            "worker_key",
            "prior_target_result_inputs",
            "target_result_reuse_allowed",
            "fresh_execution_required",
            "global_nonce_uniqueness_claimed",
            "execution_recomputed_without_cache",
            "input_id",
        },
        field="bound occurrence input",
    )
    if (
        item["schema"] != "acfqp.frozen_source_occurrence_input.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["prior_target_result_inputs"] != []
        or item["target_result_reuse_allowed"] is not False
        or item["fresh_execution_required"] is not True
        or item["global_nonce_uniqueness_claimed"] is not False
        or item["execution_recomputed_without_cache"] is not True
    ):
        _fail("bound occurrence input contract changed")
    try:
        worker_key = RegisteredOccurrenceWorkerV1(item["worker_key"])
    except (TypeError, ValueError) as error:
        raise FrozenSourceOccurrenceInvariantViolation(
            "bound occurrence worker is not registered"
        ) from error
    result = BoundOccurrenceInputV1(
        ordinal=item["ordinal"],
        occurrence_id=item["occurrence_id"],
        target_scope_id=item["target_scope_id"],
        target_payload=_canonical_mapping(
            item["target_payload"],
            field="target payload",
        ),
        source_archive_id=item["source_archive_id"],
        execution_batch_id=item["execution_batch_id"],
        attempt_nonce_id=item["attempt_nonce_id"],
        worker_key=worker_key,
    )
    if (
        result.source_archive_id
        != _cid(expected_source_archive_id, "expected source archive")
        or result.execution_batch_id
        != _cid(expected_execution_batch_id, "expected execution batch")
        or result.attempt_nonce_id
        != _cid(expected_attempt_nonce_id, "expected attempt nonce")
        or result.worker_key is not expected_worker_key
        or result.input_id != _cid(item["input_id"], "occurrence input")
        or result.canonical_bytes != raw
    ):
        _fail("bound occurrence input content or identity mismatch")
    return result


@dataclass(frozen=True, slots=True)
class OccurrenceOutputV1:
    occurrence_input_id: str
    ordinal: int
    occurrence_id: str
    target_scope_id: str
    source_archive_id: str
    execution_batch_id: str
    attempt_nonce_id: str
    worker_key: RegisteredOccurrenceWorkerV1
    result_payload: Mapping[str, Any]
    online_work: tuple[tuple[str, int], ...]
    _sealed_result_payload_bytes: bytes = field(
        init=False,
        repr=False,
        compare=True,
    )

    def __post_init__(self) -> None:
        for value, field in (
            (self.occurrence_input_id, "occurrence input"),
            (self.occurrence_id, "output occurrence"),
            (self.target_scope_id, "output target scope"),
            (self.source_archive_id, "output source archive"),
            (self.execution_batch_id, "output execution batch"),
            (self.attempt_nonce_id, "output attempt nonce"),
        ):
            _cid(value, field)
        if type(self.ordinal) is not int or self.ordinal <= 0:
            _fail("output occurrence ordinal is invalid")
        if type(self.worker_key) is not RegisteredOccurrenceWorkerV1:
            _fail("output worker is not registered")
        canonical_result, sealed_result = _sealed_json_object(
            self.result_payload,
            field="occurrence result",
            maximum_bytes=MAX_OCCURRENCE_RESULT_PAYLOAD_BYTES,
        )
        object.__setattr__(
            self,
            "_sealed_result_payload_bytes",
            canonical_result,
        )
        object.__setattr__(self, "result_payload", sealed_result)
        if type(self.online_work) is not tuple or not self.online_work:
            _fail("occurrence online work must be nonempty")
        names: list[str] = []
        for name, value in self.online_work:
            names.append(_token(name, "online counter name"))
            if type(value) is not int or value < 0:
                _fail("online counter values must be nonnegative ints")
        if tuple(names) != REGISTERED_OCCURRENCE_ONLINE_COUNTERS:
            _fail(
                "occurrence online work must contain the exact registered "
                "worker-counter vocabulary"
            )
        if len(self.canonical_bytes) > MAX_OCCURRENCE_OUTPUT_BYTES:
            _fail("occurrence output envelope exceeds its replay byte cap")

    @property
    def sealed_result_payload(self) -> dict[str, Any]:
        value = loads_canonical_json(self._sealed_result_payload_bytes)
        if type(value) is not dict:  # pragma: no cover
            _fail("sealed occurrence result is no longer an object")
        return value

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_source_occurrence_output.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_input_id": self.occurrence_input_id,
            "ordinal": self.ordinal,
            "occurrence_id": self.occurrence_id,
            "target_scope_id": self.target_scope_id,
            "source_archive_id": self.source_archive_id,
            "execution_batch_id": self.execution_batch_id,
            "attempt_nonce_id": self.attempt_nonce_id,
            "worker_key": self.worker_key.value,
            "result_payload": self.sealed_result_payload,
            "online_work": [
                {"counter": name, "value": value}
                for name, value in self.online_work
            ],
            "source_offline_work_recharged": False,
            "target_artifact_reuse_count": 0,
            "fresh_execution_completed": True,
            "scientific_claim": False,
            "physical_pid_in_logical_identity": False,
        }

    @property
    def output_id(self) -> str:
        return content_id(
            FROZEN_SOURCE_OCCURRENCE_OUTPUT_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_id": self.output_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _load_occurrence_output_v1(
    raw: bytes,
    *,
    occurrence_input: BoundOccurrenceInputV1,
) -> OccurrenceOutputV1:
    document = _strict_load(
        raw,
        maximum_bytes=MAX_OCCURRENCE_OUTPUT_BYTES,
        field="occurrence output",
    )
    item = _exact_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_input_id",
            "ordinal",
            "occurrence_id",
            "target_scope_id",
            "source_archive_id",
            "execution_batch_id",
            "attempt_nonce_id",
            "worker_key",
            "result_payload",
            "online_work",
            "source_offline_work_recharged",
            "target_artifact_reuse_count",
            "fresh_execution_completed",
            "scientific_claim",
            "physical_pid_in_logical_identity",
            "output_id",
        },
        field="occurrence output",
    )
    if (
        item["schema"] != "acfqp.frozen_source_occurrence_output.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["source_offline_work_recharged"] is not False
        or item["target_artifact_reuse_count"] != 0
        or item["fresh_execution_completed"] is not True
        or item["scientific_claim"] is not False
        or item["physical_pid_in_logical_identity"] is not False
        or type(item["online_work"]) is not list
    ):
        _fail("occurrence output contract changed")
    try:
        worker_key = RegisteredOccurrenceWorkerV1(item["worker_key"])
    except (TypeError, ValueError) as error:
        raise FrozenSourceOccurrenceInvariantViolation(
            "output occurrence worker is not registered"
        ) from error
    online_work: list[tuple[str, int]] = []
    for index, record in enumerate(item["online_work"]):
        parsed = _exact_mapping(
            record,
            keys={"counter", "value"},
            field=f"online_work[{index}]",
        )
        online_work.append((parsed["counter"], parsed["value"]))
    result = OccurrenceOutputV1(
        occurrence_input_id=item["occurrence_input_id"],
        ordinal=item["ordinal"],
        occurrence_id=item["occurrence_id"],
        target_scope_id=item["target_scope_id"],
        source_archive_id=item["source_archive_id"],
        execution_batch_id=item["execution_batch_id"],
        attempt_nonce_id=item["attempt_nonce_id"],
        worker_key=worker_key,
        result_payload=_canonical_mapping(
            item["result_payload"],
            field="occurrence result",
        ),
        online_work=tuple(online_work),
    )
    expected_binding = (
        occurrence_input.input_id,
        occurrence_input.ordinal,
        occurrence_input.occurrence_id,
        occurrence_input.target_scope_id,
        occurrence_input.source_archive_id,
        occurrence_input.execution_batch_id,
        occurrence_input.attempt_nonce_id,
        occurrence_input.worker_key,
    )
    actual_binding = (
        result.occurrence_input_id,
        result.ordinal,
        result.occurrence_id,
        result.target_scope_id,
        result.source_archive_id,
        result.execution_batch_id,
        result.attempt_nonce_id,
        result.worker_key,
    )
    if (
        actual_binding != expected_binding
        or result.output_id != _cid(item["output_id"], "occurrence output")
        or result.canonical_bytes != raw
    ):
        _fail("occurrence output content or parent binding mismatch")
    return result


def load_occurrence_output_v1(
    raw: bytes,
    *,
    occurrence_input: BoundOccurrenceInputV1,
) -> OccurrenceOutputV1:
    """Public strict replay boundary for one generated occurrence output."""

    if type(occurrence_input) is not BoundOccurrenceInputV1:
        _fail("occurrence output replay requires one typed bound input")
    return _load_occurrence_output_v1(
        raw,
        occurrence_input=occurrence_input,
    )


class ChildAttemptStatusV1(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class ChildAttemptJournalV1:
    """One launched child, including its exact retained work boundary."""

    occurrence_input_id: str
    ordinal: int
    occurrence_id: str
    target_scope_id: str
    source_archive_id: str
    worker_key: RegisteredOccurrenceWorkerV1
    status: ChildAttemptStatusV1
    output: OccurrenceOutputV1 | None
    failure_code: str | None
    failure_kind: str | None
    failure_message_sha256: str | None
    work_counters: tuple[tuple[str, int], ...]
    work_tail_unknown: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.occurrence_input_id, "child occurrence input"),
            (self.occurrence_id, "child occurrence"),
            (self.target_scope_id, "child target scope"),
            (self.source_archive_id, "child source archive"),
        ):
            _cid(value, field)
        if (
            type(self.ordinal) is not int
            or self.ordinal <= 0
            or type(self.worker_key) is not RegisteredOccurrenceWorkerV1
            or type(self.status) is not ChildAttemptStatusV1
            or type(self.work_tail_unknown) is not bool
            or type(self.work_counters) is not tuple
            or not self.work_counters
        ):
            _fail("child attempt journal has malformed typed fields")
        names: list[str] = []
        for name, value in self.work_counters:
            names.append(_token(name, "child work counter"))
            if type(value) is not int or value < 0:
                _fail("child work counters must be nonnegative integers")
        if tuple(names) != REGISTERED_CHILD_WORK_COUNTERS:
            _fail(
                "child work counters must contain the complete registered "
                "vocabulary, including native zeros"
            )
        counters = dict(self.work_counters)
        if (
            counters["control.child_submit_attempts"] not in (0, 1)
            or counters["control.child_submitted"] not in (0, 1)
            or counters["process.child_process_launches"] not in (0, 1)
            or counters["control.child_submitted"]
            > counters["control.child_submit_attempts"]
            or counters["process.child_process_launches"]
            > counters["control.child_submitted"]
            or counters.get("control.child_completed", 0)
            + counters.get("control.child_failed", 0)
            != 1
        ):
            _fail("child attempt work does not reconcile")
        if self.status is ChildAttemptStatusV1.COMPLETED:
            if (
                type(self.output) is not OccurrenceOutputV1
                or self.failure_code is not None
                or self.failure_kind is not None
                or self.failure_message_sha256 is not None
                or self.work_tail_unknown is not False
                or counters.get("control.child_completed") != 1
                or counters.get("control.child_failed") != 0
                or counters["control.child_submit_attempts"] != 1
                or counters["control.child_submitted"] != 1
                or counters["process.child_process_launches"] != 1
                or any(
                    counters[name] != value
                    for name, value in self.output.online_work
                )
                or (
                    self.output.occurrence_input_id,
                    self.output.ordinal,
                    self.output.occurrence_id,
                    self.output.target_scope_id,
                    self.output.source_archive_id,
                    self.output.worker_key,
                )
                != (
                    self.occurrence_input_id,
                    self.ordinal,
                    self.occurrence_id,
                    self.target_scope_id,
                    self.source_archive_id,
                    self.worker_key,
                )
            ):
                _fail("completed child journal has inconsistent output")
        else:
            if (
                self.output is not None
                or self.failure_code is None
                or self.failure_kind is None
                or self.failure_message_sha256 is None
                or counters.get("control.child_completed") != 0
                or counters.get("control.child_failed") != 1
            ):
                _fail("failed child journal has inconsistent evidence")
            _token(self.failure_code, "child failure code")
            _token(self.failure_kind, "child failure kind")
            _cid(
                self.failure_message_sha256,
                "child failure message digest",
            )
        if len(self.canonical_bytes) > MAX_CHILD_JOURNAL_BYTES:
            _fail("child journal envelope exceeds its replay byte cap")

    def _payload(self) -> dict[str, Any]:
        failure = (
            {
                "kind": "NOT_APPLICABLE_CHILD_COMPLETED",
            }
            if self.status is ChildAttemptStatusV1.COMPLETED
            else {
                "kind": "CHILD_FAILURE",
                "failure_code": self.failure_code,
                "failure_kind": self.failure_kind,
                "failure_message_sha256": self.failure_message_sha256,
            }
        )
        output = (
            self.output.to_document()
            if self.output is not None
            else {
                "kind": "NOT_AVAILABLE_DUE_TO_CHILD_FAILURE",
            }
        )
        work_tail = (
            {
                "kind": "UNKNOWN_AFTER_LAST_DURABLE_BOUNDARY",
                "must_not_be_interpreted_as_zero": True,
            }
            if self.work_tail_unknown
            else {"kind": "COMPLETE"}
        )
        return {
            "schema": "acfqp.frozen_source_child_attempt_journal.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_input_id": self.occurrence_input_id,
            "ordinal": self.ordinal,
            "occurrence_id": self.occurrence_id,
            "target_scope_id": self.target_scope_id,
            "source_archive_id": self.source_archive_id,
            "worker_key": self.worker_key.value,
            "status": self.status.value,
            "output": output,
            "failure": failure,
            "work_counters": [
                {"counter": name, "value": value}
                for name, value in self.work_counters
            ],
            "work_tail": work_tail,
            "submitted": (
                dict(self.work_counters)["control.child_submitted"] == 1
            ),
            "launched": (
                dict(self.work_counters)[
                    "process.child_process_launches"
                ]
                == 1
            ),
            "scientific_merge_authority": False,
            "physical_pid_in_logical_identity": False,
        }

    @property
    def journal_id(self) -> str:
        return content_id(
            FROZEN_SOURCE_CHILD_ATTEMPT_JOURNAL_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "journal_id": self.journal_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _load_child_attempt_journal_v1(
    raw: bytes,
    *,
    occurrence_input: BoundOccurrenceInputV1,
) -> ChildAttemptJournalV1:
    document = _strict_load(
        raw,
        maximum_bytes=MAX_CHILD_JOURNAL_BYTES,
        field="child attempt journal",
    )
    item = _exact_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_input_id",
            "ordinal",
            "occurrence_id",
            "target_scope_id",
            "source_archive_id",
            "worker_key",
            "status",
            "output",
            "failure",
            "work_counters",
            "work_tail",
            "submitted",
            "launched",
            "scientific_merge_authority",
            "physical_pid_in_logical_identity",
            "journal_id",
        },
        field="child attempt journal",
    )
    if (
        item["schema"]
        != "acfqp.frozen_source_child_attempt_journal.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["scientific_merge_authority"] is not False
        or item["physical_pid_in_logical_identity"] is not False
        or type(item["work_counters"]) is not list
    ):
        _fail("child attempt journal contract changed")
    try:
        status = ChildAttemptStatusV1(item["status"])
        worker_key = RegisteredOccurrenceWorkerV1(item["worker_key"])
    except (TypeError, ValueError) as error:
        raise FrozenSourceOccurrenceInvariantViolation(
            "child attempt journal has an unregistered enum value"
        ) from error
    work_counters: list[tuple[str, int]] = []
    for index, record in enumerate(item["work_counters"]):
        parsed = _exact_mapping(
            record,
            keys={"counter", "value"},
            field=f"child work_counters[{index}]",
        )
        work_counters.append((parsed["counter"], parsed["value"]))
    if status is ChildAttemptStatusV1.COMPLETED:
        failure = _exact_mapping(
            item["failure"],
            keys={"kind"},
            field="completed child failure null",
        )
        if failure["kind"] != "NOT_APPLICABLE_CHILD_COMPLETED":
            _fail("completed child has noncanonical failure null")
        output = _load_occurrence_output_v1(
            canonical_json_bytes(item["output"]),
            occurrence_input=occurrence_input,
        )
        failure_code = None
        failure_kind = None
        failure_message_sha256 = None
    else:
        output_null = _exact_mapping(
            item["output"],
            keys={"kind"},
            field="failed child output null",
        )
        if output_null["kind"] != "NOT_AVAILABLE_DUE_TO_CHILD_FAILURE":
            _fail("failed child has noncanonical output null")
        failure = _exact_mapping(
            item["failure"],
            keys={
                "kind",
                "failure_code",
                "failure_kind",
                "failure_message_sha256",
            },
            field="child failure",
        )
        if failure["kind"] != "CHILD_FAILURE":
            _fail("failed child has a changed failure kind")
        output = None
        failure_code = failure["failure_code"]
        failure_kind = failure["failure_kind"]
        failure_message_sha256 = failure["failure_message_sha256"]
    if item["work_tail"] == {"kind": "COMPLETE"}:
        work_tail_unknown = False
    elif item["work_tail"] == {
        "kind": "UNKNOWN_AFTER_LAST_DURABLE_BOUNDARY",
        "must_not_be_interpreted_as_zero": True,
    }:
        work_tail_unknown = True
    else:
        _fail("child attempt journal has a changed work-tail marker")
    result = ChildAttemptJournalV1(
        occurrence_input_id=item["occurrence_input_id"],
        ordinal=item["ordinal"],
        occurrence_id=item["occurrence_id"],
        target_scope_id=item["target_scope_id"],
        source_archive_id=item["source_archive_id"],
        worker_key=worker_key,
        status=status,
        output=output,
        failure_code=failure_code,
        failure_kind=failure_kind,
        failure_message_sha256=failure_message_sha256,
        work_counters=tuple(work_counters),
        work_tail_unknown=work_tail_unknown,
    )
    counters = dict(result.work_counters)
    if (
        item["submitted"]
        is not (counters["control.child_submitted"] == 1)
        or item["launched"]
        is not (counters["process.child_process_launches"] == 1)
    ):
        _fail("child journal launch-state claim does not match counters")
    expected_binding = (
        occurrence_input.input_id,
        occurrence_input.ordinal,
        occurrence_input.occurrence_id,
        occurrence_input.target_scope_id,
        occurrence_input.source_archive_id,
        occurrence_input.worker_key,
    )
    actual_binding = (
        result.occurrence_input_id,
        result.ordinal,
        result.occurrence_id,
        result.target_scope_id,
        result.source_archive_id,
        result.worker_key,
    )
    if (
        actual_binding != expected_binding
        or result.journal_id != _cid(item["journal_id"], "child journal")
        or result.canonical_bytes != raw
    ):
        _fail("child attempt journal content or parent binding mismatch")
    return result


def load_child_attempt_journal_v1(
    raw: bytes,
    *,
    occurrence_input: BoundOccurrenceInputV1,
) -> ChildAttemptJournalV1:
    """Public strict replay boundary for one child work/result journal."""

    if type(occurrence_input) is not BoundOccurrenceInputV1:
        _fail("child journal replay requires one typed bound input")
    return _load_child_attempt_journal_v1(
        raw,
        occurrence_input=occurrence_input,
    )


def _aggregate_child_work_v1(
    journals: tuple[ChildAttemptJournalV1, ...],
) -> tuple[tuple[str, int], ...]:
    aggregate: dict[str, int] = {}
    for journal in journals:
        for name, value in journal.work_counters:
            aggregate[name] = aggregate.get(name, 0) + value
    return tuple(sorted(aggregate.items()))


@dataclass(frozen=True, slots=True)
class OccurrenceFailureClosureV1:
    """Accounting/provenance closure with no scientific merge authority."""

    source_archive: FrozenSourceArchiveEnvelopeV1
    inputs: tuple[BoundOccurrenceInputV1, ...]
    child_journals: tuple[ChildAttemptJournalV1, ...]
    execution_batch_id: str
    attempt_nonce_id: str
    batch_failure_code: str | None = None
    _diagnostic_child_pids: tuple[int | None, ...] = field(
        default=(),
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.source_archive) is not FrozenSourceArchiveEnvelopeV1
            or type(self.inputs) is not tuple
            or type(self.child_journals) is not tuple
            or not self.inputs
            or len(self.inputs) != len(self.child_journals)
            or (
                not any(
                    item.status is ChildAttemptStatusV1.FAILED
                    for item in self.child_journals
                )
                and self.batch_failure_code is None
            )
        ):
            _fail("failure closure has an invalid shape or no failure")
        _cid(self.execution_batch_id, "failure closure execution batch")
        _cid(self.attempt_nonce_id, "failure closure attempt nonce")
        if self.batch_failure_code is not None:
            _token(self.batch_failure_code, "batch failure code")
        if self._diagnostic_child_pids and (
            len(self._diagnostic_child_pids) != len(self.inputs)
            or any(
                value is not None
                and (type(value) is not int or value <= 0)
                for value in self._diagnostic_child_pids
            )
        ):
            _fail("failure closure has malformed physical PID diagnostics")
        observed_pids = tuple(
            value
            for value in self._diagnostic_child_pids
            if value is not None
        )
        if (
            len(set(observed_pids)) != len(observed_pids)
            and self.batch_failure_code != "PROCESS_REUSE_DETECTED"
        ):
            _fail("process reuse is not closed by its stable batch failure")
        if tuple(item.ordinal for item in self.inputs) != tuple(
            range(1, len(self.inputs) + 1)
        ):
            _fail("failure closure inputs changed registered order")
        for occurrence_input, journal in zip(
            self.inputs,
            self.child_journals,
        ):
            if (
                occurrence_input.source_archive_id
                != self.source_archive.archive_id
                or occurrence_input.execution_batch_id
                != self.execution_batch_id
                or occurrence_input.attempt_nonce_id != self.attempt_nonce_id
                or (
                    journal.occurrence_input_id,
                    journal.ordinal,
                    journal.occurrence_id,
                )
                != (
                    occurrence_input.input_id,
                    occurrence_input.ordinal,
                    occurrence_input.occurrence_id,
                )
                or journal.journal_id
                != _load_child_attempt_journal_v1(
                    journal.canonical_bytes,
                    occurrence_input=occurrence_input,
                ).journal_id
            ):
                _fail("failure closure contains a foreign child journal")
        if len(self.canonical_bytes) > MAX_COMPOSITE_ARTIFACT_BYTES:
            _fail("failure closure envelope exceeds its replay byte cap")

    @property
    def completed_attempts(self) -> tuple[ChildAttemptJournalV1, ...]:
        return tuple(
            item
            for item in self.child_journals
            if item.status is ChildAttemptStatusV1.COMPLETED
        )

    @property
    def failed_attempts(self) -> tuple[ChildAttemptJournalV1, ...]:
        return tuple(
            item
            for item in self.child_journals
            if item.status is ChildAttemptStatusV1.FAILED
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_source_occurrence_failure_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_archive_id": self.source_archive.archive_id,
            "execution_batch_id": self.execution_batch_id,
            "attempt_nonce_id": self.attempt_nonce_id,
            "source_offline_work_id": self.source_archive.offline_work.work_id,
            "source_offline_work": (
                self.source_archive.offline_work.to_document()
            ),
            "occurrence_input_ids": [item.input_id for item in self.inputs],
            "child_journal_ids": [
                item.journal_id for item in self.child_journals
            ],
            "child_journals": [
                item.to_document() for item in self.child_journals
            ],
            "completed_output_ids": [
                item.output.output_id
                for item in self.completed_attempts
                if item.output is not None
            ],
            "failed_occurrence_ids": [
                item.occurrence_id for item in self.failed_attempts
            ],
            "batch_failure": (
                {"kind": "NOT_APPLICABLE"}
                if self.batch_failure_code is None
                else {
                    "kind": "STABLE_BATCH_FAILURE",
                    "failure_code": self.batch_failure_code,
                }
            ),
            "aggregate_known_child_work": [
                {"counter": name, "value": value}
                for name, value in _aggregate_child_work_v1(
                    self.child_journals
                )
            ],
            "unknown_work_tail_count": sum(
                item.work_tail_unknown for item in self.child_journals
            ),
            "scheduled_child_count": len(self.child_journals),
            "submitted_child_count": sum(
                dict(item.work_counters)["control.child_submitted"]
                for item in self.child_journals
            ),
            "launched_child_count": sum(
                dict(item.work_counters)["process.child_process_launches"]
                for item in self.child_journals
            ),
            "completed_child_count": len(self.completed_attempts),
            "failed_child_count": len(self.failed_attempts),
            "logical_occurrence_denominator": len(self.inputs),
            "canonical_journal_order": "ASCENDING_REGISTERED_ORDINAL",
            "all_available_child_journals_retained": True,
            "all_launched_child_journals_retained": not any(
                item.work_tail_unknown for item in self.child_journals
            ),
            "completed_outputs_retained_for_accounting": True,
            "scientific_occurrence_merge": {
                "kind": "NOT_PRODUCED_DUE_TO_CHILD_FAILURE",
            },
            "scientific_merge_authority": False,
            "source_offline_work_charged_exactly_once": True,
            "target_artifact_reuse_count": 0,
            "physical_worker_count_in_logical_identity": False,
            "physical_pid_in_logical_identity": False,
            "execution_recomputed_without_cache": True,
            "global_nonce_uniqueness_claimed": False,
        }

    @property
    def failure_closure_id(self) -> str:
        return content_id(
            FROZEN_SOURCE_OCCURRENCE_FAILURE_CLOSURE_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "failure_closure_id": self.failure_closure_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    @property
    def diagnostic_child_pids(self) -> tuple[int | None, ...]:
        return self._diagnostic_child_pids


def load_occurrence_failure_closure_v1(
    raw: bytes,
    *,
    source_archive: FrozenSourceArchiveEnvelopeV1,
    occurrence_inputs: tuple[BoundOccurrenceInputV1, ...],
    expected_failure_closure_id: str,
) -> OccurrenceFailureClosureV1:
    """Strictly replay one retained, non-scientific failure closure."""

    document = _strict_load(
        raw,
        maximum_bytes=MAX_COMPOSITE_ARTIFACT_BYTES,
        field="occurrence failure closure",
    )
    item = _exact_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "profile_key",
            "source_archive_id",
            "execution_batch_id",
            "attempt_nonce_id",
            "source_offline_work_id",
            "source_offline_work",
            "occurrence_input_ids",
            "child_journal_ids",
            "child_journals",
            "completed_output_ids",
            "failed_occurrence_ids",
            "batch_failure",
            "aggregate_known_child_work",
            "unknown_work_tail_count",
            "launched_child_count",
            "scheduled_child_count",
            "submitted_child_count",
            "completed_child_count",
            "failed_child_count",
            "logical_occurrence_denominator",
            "canonical_journal_order",
            "all_launched_child_journals_retained",
            "all_available_child_journals_retained",
            "completed_outputs_retained_for_accounting",
            "scientific_occurrence_merge",
            "scientific_merge_authority",
            "source_offline_work_charged_exactly_once",
            "target_artifact_reuse_count",
            "physical_worker_count_in_logical_identity",
            "physical_pid_in_logical_identity",
            "execution_recomputed_without_cache",
            "global_nonce_uniqueness_claimed",
            "failure_closure_id",
        },
        field="occurrence failure closure",
    )
    if (
        item["schema"]
        != "acfqp.frozen_source_occurrence_failure_closure.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["source_archive_id"] != source_archive.archive_id
        or item["source_offline_work_id"]
        != source_archive.offline_work.work_id
        or item["source_offline_work"]
        != source_archive.offline_work.to_document()
        or item["canonical_journal_order"]
        != "ASCENDING_REGISTERED_ORDINAL"
        or item["all_available_child_journals_retained"] is not True
        or item["completed_outputs_retained_for_accounting"] is not True
        or item["scientific_occurrence_merge"]
        != {"kind": "NOT_PRODUCED_DUE_TO_CHILD_FAILURE"}
        or item["scientific_merge_authority"] is not False
        or item["source_offline_work_charged_exactly_once"] is not True
        or item["target_artifact_reuse_count"] != 0
        or item["physical_worker_count_in_logical_identity"] is not False
        or item["physical_pid_in_logical_identity"] is not False
        or item["execution_recomputed_without_cache"] is not True
        or item["global_nonce_uniqueness_claimed"] is not False
        or type(item["child_journals"]) is not list
    ):
        _fail("occurrence failure closure contract changed")
    journals = tuple(
        _load_child_attempt_journal_v1(
            canonical_json_bytes(document_item),
            occurrence_input=occurrence_input,
        )
        for occurrence_input, document_item in zip(
            occurrence_inputs,
            item["child_journals"],
        )
    )
    batch_failure = item["batch_failure"]
    if batch_failure == {"kind": "NOT_APPLICABLE"}:
        batch_failure_code = None
    else:
        parsed_batch_failure = _exact_mapping(
            batch_failure,
            keys={"kind", "failure_code"},
            field="batch failure",
        )
        if parsed_batch_failure["kind"] != "STABLE_BATCH_FAILURE":
            _fail("failure closure has a changed batch-failure kind")
        batch_failure_code = parsed_batch_failure["failure_code"]
    result = OccurrenceFailureClosureV1(
        source_archive=source_archive,
        inputs=occurrence_inputs,
        child_journals=journals,
        execution_batch_id=item["execution_batch_id"],
        attempt_nonce_id=item["attempt_nonce_id"],
        batch_failure_code=batch_failure_code,
    )
    if (
        len(journals) != len(occurrence_inputs)
        or item["occurrence_input_ids"]
        != [value.input_id for value in occurrence_inputs]
        or item["child_journal_ids"]
        != [value.journal_id for value in journals]
        or item["completed_output_ids"]
        != [
            value.output.output_id
            for value in result.completed_attempts
            if value.output is not None
        ]
        or item["failed_occurrence_ids"]
        != [value.occurrence_id for value in result.failed_attempts]
        or item["aggregate_known_child_work"]
        != [
            {"counter": name, "value": value}
            for name, value in _aggregate_child_work_v1(journals)
        ]
        or item["unknown_work_tail_count"]
        != sum(value.work_tail_unknown for value in journals)
        or item["all_launched_child_journals_retained"]
        is not (not any(value.work_tail_unknown for value in journals))
        or item["scheduled_child_count"] != len(journals)
        or item["submitted_child_count"]
        != sum(
            dict(value.work_counters)["control.child_submitted"]
            for value in journals
        )
        or item["launched_child_count"]
        != sum(
            dict(value.work_counters)["process.child_process_launches"]
            for value in journals
        )
        or item["completed_child_count"] != len(result.completed_attempts)
        or item["failed_child_count"] != len(result.failed_attempts)
        or item["logical_occurrence_denominator"] != len(occurrence_inputs)
        or result.failure_closure_id
        != _cid(
            item["failure_closure_id"],
            "occurrence failure closure",
        )
        or result.failure_closure_id
        != _cid(
            expected_failure_closure_id,
            "expected occurrence failure closure",
        )
        or result.canonical_bytes != raw
    ):
        _fail("occurrence failure closure content replay mismatch")
    return result


@dataclass(frozen=True, slots=True)
class CanonicalOccurrenceMergeV1:
    source_archive: FrozenSourceArchiveEnvelopeV1
    inputs: tuple[BoundOccurrenceInputV1, ...]
    outputs: tuple[OccurrenceOutputV1, ...]
    child_journals: tuple[ChildAttemptJournalV1, ...]
    execution_batch_id: str
    attempt_nonce_id: str
    _diagnostic_child_pids: tuple[int, ...] = field(
        default=(),
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.source_archive) is not FrozenSourceArchiveEnvelopeV1
            or type(self.inputs) is not tuple
            or type(self.outputs) is not tuple
            or type(self.child_journals) is not tuple
            or not self.inputs
            or len(self.inputs) != len(self.outputs)
            or len(self.inputs) != len(self.child_journals)
        ):
            _fail("canonical occurrence merge has an invalid shape")
        _cid(self.execution_batch_id, "canonical merge execution batch")
        _cid(self.attempt_nonce_id, "canonical merge attempt nonce")
        if tuple(item.ordinal for item in self.inputs) != tuple(
            range(1, len(self.inputs) + 1)
        ):
            _fail("canonical occurrence inputs are not contiguous and ordered")
        if tuple(item.ordinal for item in self.outputs) != tuple(
            item.ordinal for item in self.inputs
        ):
            _fail("canonical occurrence outputs changed registered order")
        if len({item.occurrence_id for item in self.inputs}) != len(self.inputs):
            _fail("canonical occurrence merge contains duplicate occurrences")
        if any(
            item.status is not ChildAttemptStatusV1.COMPLETED
            for item in self.child_journals
        ):
            _fail("successful canonical merge contains a failed child journal")
        if (
            self._diagnostic_child_pids
            and (
                len(self._diagnostic_child_pids) != len(self.inputs)
                or len(set(self._diagnostic_child_pids)) != len(self.inputs)
                or any(
                    type(value) is not int or value <= 0
                    for value in self._diagnostic_child_pids
                )
            )
        ):
            _fail("physical child PID diagnostics show process reuse")
        for occurrence_input, output, journal in zip(
            self.inputs,
            self.outputs,
            self.child_journals,
        ):
            if (
                occurrence_input.source_archive_id
                != self.source_archive.archive_id
                or occurrence_input.execution_batch_id
                != self.execution_batch_id
                or occurrence_input.attempt_nonce_id != self.attempt_nonce_id
                or output.occurrence_input_id != occurrence_input.input_id
                or journal.output is None
                or journal.output.output_id != output.output_id
                or journal.journal_id
                != _load_child_attempt_journal_v1(
                    journal.canonical_bytes,
                    occurrence_input=occurrence_input,
                ).journal_id
                or output.output_id
                != _load_occurrence_output_v1(
                    output.canonical_bytes,
                    occurrence_input=occurrence_input,
                ).output_id
            ):
                _fail("canonical merge contains a foreign occurrence output")
        if len(self.canonical_bytes) > MAX_COMPOSITE_ARTIFACT_BYTES:
            _fail("canonical merge envelope exceeds its replay byte cap")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.frozen_source_occurrence_merge.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "source_archive_id": self.source_archive.archive_id,
            "execution_batch_id": self.execution_batch_id,
            "attempt_nonce_id": self.attempt_nonce_id,
            "upstream_archive_id": (
                self.source_archive.upstream_archive_id
            ),
            "upstream_verification_id": (
                self.source_archive.upstream_verification_id
            ),
            "source_offline_work_id": self.source_archive.offline_work.work_id,
            "source_offline_work": (
                self.source_archive.offline_work.to_document()
            ),
            "occurrence_input_ids": [item.input_id for item in self.inputs],
            "occurrence_output_ids": [
                item.output_id for item in self.outputs
            ],
            "occurrence_outputs": [
                item.to_document() for item in self.outputs
            ],
            "child_journal_ids": [
                item.journal_id for item in self.child_journals
            ],
            "child_journals": [
                item.to_document() for item in self.child_journals
            ],
            "aggregate_known_child_work": [
                {"counter": name, "value": value}
                for name, value in _aggregate_child_work_v1(
                    self.child_journals
                )
            ],
            "unknown_work_tail_count": 0,
            "occurrence_journal_entries": [
                {
                    "ordinal": occurrence_input.ordinal,
                    "occurrence_id": occurrence_input.occurrence_id,
                    "occurrence_input_id": occurrence_input.input_id,
                    "occurrence_output_id": output.output_id,
                    "event": "OCCURRENCE_COMPLETED",
                }
                for occurrence_input, output in zip(
                    self.inputs,
                    self.outputs,
                )
            ],
            "journal_entry_count": len(self.outputs),
            "journal_merge_complete": True,
            "logical_occurrence_denominator": len(self.inputs),
            "canonical_merge_order": "ASCENDING_REGISTERED_ORDINAL",
            "physical_completion_order_discarded": True,
            "source_offline_work_charged_exactly_once": True,
            "target_artifact_reuse_count": 0,
            "all_occurrences_freshly_executed": True,
            "execution_recomputed_without_cache": True,
            "global_nonce_uniqueness_claimed": False,
            "parallelism_is_physical_only": True,
            "physical_worker_count_in_logical_identity": False,
            "physical_pid_in_logical_identity": False,
            "partial_output_publication_allowed": False,
            "scientific_claim": False,
        }

    @property
    def merge_id(self) -> str:
        return content_id(
            FROZEN_SOURCE_OCCURRENCE_MERGE_DOMAIN,
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "merge_id": self.merge_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    @property
    def diagnostic_child_pids(self) -> tuple[int, ...]:
        return self._diagnostic_child_pids


def load_canonical_occurrence_merge_v1(
    raw: bytes,
    *,
    source_archive: FrozenSourceArchiveEnvelopeV1,
    occurrence_inputs: tuple[BoundOccurrenceInputV1, ...],
    expected_merge_id: str,
) -> CanonicalOccurrenceMergeV1:
    """Strictly replay every input/output/journal binding in a success merge."""

    if (
        type(source_archive) is not FrozenSourceArchiveEnvelopeV1
        or type(occurrence_inputs) is not tuple
        or not occurrence_inputs
        or any(
            type(item) is not BoundOccurrenceInputV1
            for item in occurrence_inputs
        )
    ):
        _fail("canonical merge replay requires typed archive and inputs")
    document = _strict_load(
        raw,
        maximum_bytes=MAX_COMPOSITE_ARTIFACT_BYTES,
        field="canonical occurrence merge",
    )
    item = _exact_mapping(
        document,
        keys={
            "schema",
            "schema_version",
            "profile_key",
            "source_archive_id",
            "execution_batch_id",
            "attempt_nonce_id",
            "upstream_archive_id",
            "upstream_verification_id",
            "source_offline_work_id",
            "source_offline_work",
            "occurrence_input_ids",
            "occurrence_output_ids",
            "occurrence_outputs",
            "child_journal_ids",
            "child_journals",
            "aggregate_known_child_work",
            "unknown_work_tail_count",
            "occurrence_journal_entries",
            "journal_entry_count",
            "journal_merge_complete",
            "logical_occurrence_denominator",
            "canonical_merge_order",
            "physical_completion_order_discarded",
            "source_offline_work_charged_exactly_once",
            "target_artifact_reuse_count",
            "all_occurrences_freshly_executed",
            "execution_recomputed_without_cache",
            "global_nonce_uniqueness_claimed",
            "parallelism_is_physical_only",
            "physical_worker_count_in_logical_identity",
            "physical_pid_in_logical_identity",
            "partial_output_publication_allowed",
            "scientific_claim",
            "merge_id",
        },
        field="canonical occurrence merge",
    )
    if (
        item["schema"] != "acfqp.frozen_source_occurrence_merge.v1"
        or item["schema_version"] != SCHEMA_VERSION
        or item["profile_key"] != PROFILE_KEY
        or item["source_archive_id"] != source_archive.archive_id
        or item["upstream_archive_id"] != source_archive.upstream_archive_id
        or item["upstream_verification_id"]
        != source_archive.upstream_verification_id
        or item["source_offline_work_id"]
        != source_archive.offline_work.work_id
        or item["source_offline_work"]
        != source_archive.offline_work.to_document()
        or type(item["occurrence_outputs"]) is not list
        or type(item["child_journals"]) is not list
        or item["unknown_work_tail_count"] != 0
        or item["journal_merge_complete"] is not True
        or item["canonical_merge_order"]
        != "ASCENDING_REGISTERED_ORDINAL"
        or item["physical_completion_order_discarded"] is not True
        or item["source_offline_work_charged_exactly_once"] is not True
        or item["target_artifact_reuse_count"] != 0
        or item["all_occurrences_freshly_executed"] is not True
        or item["execution_recomputed_without_cache"] is not True
        or item["global_nonce_uniqueness_claimed"] is not False
        or item["parallelism_is_physical_only"] is not True
        or item["physical_worker_count_in_logical_identity"] is not False
        or item["physical_pid_in_logical_identity"] is not False
        or item["partial_output_publication_allowed"] is not False
        or item["scientific_claim"] is not False
    ):
        _fail("canonical occurrence merge contract changed")
    worker_keys = {value.worker_key for value in occurrence_inputs}
    if len(worker_keys) != 1:
        _fail("canonical merge inputs changed the registered worker")
    worker_key = next(iter(worker_keys))
    replay_specs = tuple(
        TargetOccurrenceSpecV1(
            ordinal=value.ordinal,
            occurrence_id=value.occurrence_id,
            target_scope_id=value.target_scope_id,
            target_payload=value.sealed_target_payload,
        )
        for value in occurrence_inputs
    )
    if (
        derive_frozen_execution_batch_id_v1(
            source_archive_id=source_archive.archive_id,
            attempt_nonce_id=item["attempt_nonce_id"],
            occurrences=replay_specs,
            worker_key=worker_key,
        )
        != item["execution_batch_id"]
    ):
        _fail("canonical merge execution batch does not replay")
    replayed_inputs = tuple(
        _load_bound_occurrence_input_v1(
            value.canonical_bytes,
            expected_source_archive_id=source_archive.archive_id,
            expected_execution_batch_id=item["execution_batch_id"],
            expected_attempt_nonce_id=item["attempt_nonce_id"],
            expected_worker_key=worker_key,
        )
        for value in occurrence_inputs
    )
    outputs = tuple(
        _load_occurrence_output_v1(
            canonical_json_bytes(output_document),
            occurrence_input=occurrence_input,
        )
        for occurrence_input, output_document in zip(
            replayed_inputs,
            item["occurrence_outputs"],
        )
    )
    journals = tuple(
        _load_child_attempt_journal_v1(
            canonical_json_bytes(journal_document),
            occurrence_input=occurrence_input,
        )
        for occurrence_input, journal_document in zip(
            replayed_inputs,
            item["child_journals"],
        )
    )
    result = CanonicalOccurrenceMergeV1(
        source_archive=source_archive,
        inputs=replayed_inputs,
        outputs=outputs,
        child_journals=journals,
        execution_batch_id=item["execution_batch_id"],
        attempt_nonce_id=item["attempt_nonce_id"],
    )
    if (
        item["occurrence_input_ids"]
        != [value.input_id for value in replayed_inputs]
        or item["occurrence_output_ids"]
        != [value.output_id for value in outputs]
        or item["child_journal_ids"]
        != [value.journal_id for value in journals]
        or result.merge_id != _cid(item["merge_id"], "canonical merge")
        or result.merge_id
        != _cid(expected_merge_id, "expected canonical merge")
        or result.to_document() != document
        or result.canonical_bytes != raw
    ):
        _fail("canonical occurrence merge content replay mismatch")
    return result


_CHILD_SOURCE_ARCHIVE: FrozenSourceArchiveEnvelopeV1 | None = None


def _initialize_child_source_v1(
    archive_bytes: bytes,
    expected_archive_id: str,
    expected_upstream_archive_id: str,
    expected_upstream_verification_id: str,
    expected_offline_work_id: str,
) -> None:
    global _CHILD_SOURCE_ARCHIVE
    _CHILD_SOURCE_ARCHIVE = load_frozen_source_archive_envelope_v1(
        archive_bytes,
        expected_archive_id=expected_archive_id,
        expected_upstream_archive_id=expected_upstream_archive_id,
        expected_upstream_verification_id=(
            expected_upstream_verification_id
        ),
        expected_offline_work_id=expected_offline_work_id,
    )


def _registered_worker_result_v1(
    archive: FrozenSourceArchiveEnvelopeV1,
    occurrence: BoundOccurrenceInputV1,
) -> OccurrenceOutputV1:
    if (
        occurrence.worker_key
        is RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_FAIL_V1
    ):
        raise RuntimeError("registered synthetic fail-closed worker")
    if (
        occurrence.worker_key
        is RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_MARKED_FAILURE_V1
        and occurrence.target_payload.get("synthetic_failure") is True
    ):
        raise RuntimeError("registered marked synthetic child failure")
    if occurrence.worker_key not in (
        RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_HASH_V1,
        RegisteredOccurrenceWorkerV1.SAFE_SYNTHETIC_MARKED_FAILURE_V1,
    ):  # pragma: no cover - enum exhaustiveness defense
        _fail("unregistered occurrence worker reached dispatch")
    target_bytes = canonical_json_bytes(occurrence.sealed_target_payload)
    return OccurrenceOutputV1(
        occurrence_input_id=occurrence.input_id,
        ordinal=occurrence.ordinal,
        occurrence_id=occurrence.occurrence_id,
        target_scope_id=occurrence.target_scope_id,
        source_archive_id=archive.archive_id,
        execution_batch_id=occurrence.execution_batch_id,
        attempt_nonce_id=occurrence.attempt_nonce_id,
        worker_key=occurrence.worker_key,
        result_payload={
            "kind": "SAFE_SYNTHETIC_HASH_RESULT_V1",
            "source_document_sha256": archive.source_document_sha256,
            "target_payload_sha256": hashlib.sha256(target_bytes).hexdigest(),
            "target_payload": occurrence.sealed_target_payload,
        },
        online_work=(("synthetic.registered_worker_events", 1),),
    )


def _execute_child_occurrence_v1(
    occurrence_bytes: bytes,
    expected_worker_key: str,
    expected_execution_batch_id: str,
    expected_attempt_nonce_id: str,
) -> tuple[bytes, int]:
    archive = _CHILD_SOURCE_ARCHIVE
    if archive is None:
        raise RuntimeError("child source archive was not initialized")
    try:
        worker_key = RegisteredOccurrenceWorkerV1(expected_worker_key)
    except ValueError as error:
        raise RuntimeError("child worker key is not registered") from error
    occurrence = _load_bound_occurrence_input_v1(
        occurrence_bytes,
        expected_source_archive_id=archive.archive_id,
        expected_execution_batch_id=expected_execution_batch_id,
        expected_attempt_nonce_id=expected_attempt_nonce_id,
        expected_worker_key=worker_key,
    )
    return (
        _run_child_attempt_v1(archive, occurrence).canonical_bytes,
        os.getpid(),
    )


_REGISTERED_FAILURE_CODES = {
    "registered synthetic fail-closed worker": (
        "REGISTERED_SYNTHETIC_FAIL_V1"
    ),
    "registered marked synthetic child failure": (
        "REGISTERED_SYNTHETIC_MARKED_FAILURE_V1"
    ),
}


def _failure_fields_v1(
    error: BaseException,
) -> tuple[str, str, str, bool]:
    message = str(error)
    failure_code = _REGISTERED_FAILURE_CODES.get(
        message,
        "UNEXPECTED_REGISTERED_WORKER_EXCEPTION",
    )
    failure_kind = (
        "REGISTERED_SYNTHETIC_WORKER_FAILURE"
        if failure_code in _REGISTERED_FAILURE_CODES.values()
        else "UNEXPECTED_REGISTERED_WORKER_FAILURE"
    )
    message_digest = hashlib.sha256(
        (
            "acfqp:v074-stable-child-failure-detail:v1\x00"
            + failure_code
        ).encode("utf-8")
    ).hexdigest()
    return (
        failure_code,
        failure_kind,
        message_digest,
        failure_code == "UNEXPECTED_REGISTERED_WORKER_EXCEPTION",
    )


def _run_child_attempt_v1(
    archive: FrozenSourceArchiveEnvelopeV1,
    occurrence: BoundOccurrenceInputV1,
) -> ChildAttemptJournalV1:
    try:
        output = _registered_worker_result_v1(archive, occurrence)
    except Exception as error:
        (
            failure_code,
            failure_kind,
            failure_message_sha256,
            work_tail_unknown,
        ) = _failure_fields_v1(error)
        return ChildAttemptJournalV1(
            occurrence_input_id=occurrence.input_id,
            ordinal=occurrence.ordinal,
            occurrence_id=occurrence.occurrence_id,
            target_scope_id=occurrence.target_scope_id,
            source_archive_id=occurrence.source_archive_id,
            worker_key=occurrence.worker_key,
            status=ChildAttemptStatusV1.FAILED,
            output=None,
            failure_code=failure_code,
            failure_kind=failure_kind,
            failure_message_sha256=failure_message_sha256,
            work_counters=(
                ("control.child_completed", 0),
                ("control.child_failed", 1),
                ("control.child_submit_attempts", 1),
                ("control.child_submitted", 1),
                ("process.child_process_launches", 1),
                ("synthetic.registered_worker_events", 1),
            ),
            work_tail_unknown=work_tail_unknown,
        )
    return ChildAttemptJournalV1(
        occurrence_input_id=occurrence.input_id,
        ordinal=occurrence.ordinal,
        occurrence_id=occurrence.occurrence_id,
        target_scope_id=occurrence.target_scope_id,
        source_archive_id=occurrence.source_archive_id,
        worker_key=occurrence.worker_key,
        status=ChildAttemptStatusV1.COMPLETED,
        output=output,
        failure_code=None,
        failure_kind=None,
        failure_message_sha256=None,
        work_counters=(
            ("control.child_completed", 1),
            ("control.child_failed", 0),
            ("control.child_submit_attempts", 1),
            ("control.child_submitted", 1),
            ("process.child_process_launches", 1),
            *output.online_work,
        ),
        work_tail_unknown=False,
    )


def _parent_failure_journal_v1(
    occurrence: BoundOccurrenceInputV1,
    *,
    failure_code: str,
    failure_kind: str,
    submit_attempted: bool,
    submitted: bool,
    work_tail_unknown: bool,
) -> ChildAttemptJournalV1:
    _token(failure_code, "parent failure code")
    _token(failure_kind, "parent failure kind")
    message_digest = hashlib.sha256(
        (
            "acfqp:v074-stable-parent-failure-detail:v1\x00"
            + failure_code
            + "\x00"
            + failure_kind
        ).encode("utf-8")
    ).hexdigest()
    return ChildAttemptJournalV1(
        occurrence_input_id=occurrence.input_id,
        ordinal=occurrence.ordinal,
        occurrence_id=occurrence.occurrence_id,
        target_scope_id=occurrence.target_scope_id,
        source_archive_id=occurrence.source_archive_id,
        worker_key=occurrence.worker_key,
        status=ChildAttemptStatusV1.FAILED,
        output=None,
        failure_code=failure_code,
        failure_kind=failure_kind,
        failure_message_sha256=message_digest,
        work_counters=(
            ("control.child_completed", 0),
            ("control.child_failed", 1),
            ("control.child_submit_attempts", int(submit_attempted)),
            ("control.child_submitted", int(submitted)),
            ("process.child_process_launches", 0),
            ("synthetic.registered_worker_events", 0),
        ),
        work_tail_unknown=work_tail_unknown,
    )


def _validate_schedule_v1(
    archive: FrozenSourceArchiveEnvelopeV1,
    occurrences: Sequence[TargetOccurrenceSpecV1],
    worker_key: RegisteredOccurrenceWorkerV1,
    *,
    execution_batch_id: str,
    attempt_nonce_id: str,
) -> tuple[BoundOccurrenceInputV1, ...]:
    if (
        type(occurrences) is not tuple
        or not occurrences
        or len(occurrences) > MAX_OCCURRENCES
        or any(type(item) is not TargetOccurrenceSpecV1 for item in occurrences)
    ):
        _fail("occurrence schedule is empty, mutable, mistyped, or over cap")
    if type(worker_key) is not RegisteredOccurrenceWorkerV1:
        _fail("occurrence worker is not registered")
    _cid(execution_batch_id, "execution batch")
    _cid(attempt_nonce_id, "attempt nonce")
    if tuple(item.ordinal for item in occurrences) != tuple(
        range(1, len(occurrences) + 1)
    ):
        _fail("occurrence schedule must be contiguous in registered order")
    occurrence_ids = tuple(item.occurrence_id for item in occurrences)
    if len(set(occurrence_ids)) != len(occurrence_ids):
        _fail("occurrence schedule contains duplicate occurrence identities")
    target_ids = frozenset(
        (
            *(item.occurrence_id for item in occurrences),
            *(item.target_scope_id for item in occurrences),
        )
    )
    source_ids = {
        archive.archive_id,
        archive.upstream_archive_id,
        archive.upstream_verification_id,
        archive.source_scope_id,
        archive.offline_work.work_id,
        archive.verification_attestation.semantic_verifier_id,
        archive.verification_attestation.verification_profile_id,
        archive.verification_attestation.counter_registry_id,
    }
    if (
        target_ids & source_ids
        or execution_batch_id in source_ids | set(target_ids)
        or attempt_nonce_id in source_ids | set(target_ids) | {execution_batch_id}
    ):
        _fail("source and target identity roles overlap")
    if _contains_exact_string(archive.sealed_source_document, target_ids):
        _fail("frozen source document contains a registered target identity")
    source_identity_set = frozenset(source_ids)
    if any(
        _contains_exact_string(
            item.sealed_target_payload,
            source_identity_set,
        )
        for item in occurrences
    ):
        _fail("target payload contains a registered source identity")
    inputs = tuple(
        BoundOccurrenceInputV1(
            ordinal=item.ordinal,
            occurrence_id=item.occurrence_id,
            target_scope_id=item.target_scope_id,
            target_payload=item.sealed_target_payload,
            source_archive_id=archive.archive_id,
            execution_batch_id=execution_batch_id,
            attempt_nonce_id=attempt_nonce_id,
            worker_key=worker_key,
        )
        for item in occurrences
    )
    if any(len(item.canonical_bytes) > MAX_OCCURRENCE_BYTES for item in inputs):
        _fail("one occurrence input exceeds the frozen byte cap")
    return inputs


def run_frozen_source_occurrences_v1(
    archive_bytes: bytes,
    *,
    expected_archive_id: str,
    expected_upstream_archive_id: str,
    expected_upstream_verification_id: str,
    expected_offline_work_id: str,
    expected_execution_batch_id: str,
    attempt_nonce_id: str,
    occurrences: tuple[TargetOccurrenceSpecV1, ...],
    worker_key: RegisteredOccurrenceWorkerV1,
    max_workers: int,
) -> CanonicalOccurrenceMergeV1:
    """Execute every occurrence once and merge independent of worker count.

    Every occurrence uses a fresh ``spawn`` process. ``max_workers`` limits
    concurrent processes only; ``max_tasks_per_child=1`` prevents PID/global
    state reuse even for sequential execution. A child or process-boundary
    failure produces one deterministic accounting/provenance closure.
    """

    if (
        type(max_workers) is not int
        or not 1 <= max_workers <= MAX_WORKERS
    ):
        _fail("max_workers is outside the frozen [1, 192] range")
    archive = load_frozen_source_archive_envelope_v1(
        archive_bytes,
        expected_archive_id=expected_archive_id,
        expected_upstream_archive_id=expected_upstream_archive_id,
        expected_upstream_verification_id=(
            expected_upstream_verification_id
        ),
        expected_offline_work_id=expected_offline_work_id,
    )
    attempt_nonce = _cid(attempt_nonce_id, "execution attempt nonce")
    derived_batch_id = derive_frozen_execution_batch_id_v1(
        source_archive_id=archive.archive_id,
        attempt_nonce_id=attempt_nonce,
        occurrences=occurrences,
        worker_key=worker_key,
    )
    if derived_batch_id != _cid(
        expected_execution_batch_id,
        "expected execution batch",
    ):
        _fail("execution batch identity does not bind the frozen schedule")
    inputs = _validate_schedule_v1(
        archive,
        occurrences,
        worker_key,
        execution_batch_id=derived_batch_id,
        attempt_nonce_id=attempt_nonce,
    )
    journals_by_index: list[ChildAttemptJournalV1 | None] = [
        None for _ in inputs
    ]
    pids_by_index: list[int | None] = [None for _ in inputs]
    futures: list[tuple[int, Future[tuple[bytes, int]]]] = []
    executor: ProcessPoolExecutor | None = None
    batch_failure_code: str | None = None
    try:
        try:
            executor = ProcessPoolExecutor(
                max_workers=min(max_workers, len(inputs)),
                mp_context=get_context("spawn"),
                initializer=_initialize_child_source_v1,
                initargs=(
                    archive_bytes,
                    archive.archive_id,
                    archive.upstream_archive_id,
                    archive.upstream_verification_id,
                    archive.offline_work.work_id,
                ),
                max_tasks_per_child=1,
            )
        except Exception:
            for index, occurrence in enumerate(inputs):
                journals_by_index[index] = _parent_failure_journal_v1(
                    occurrence,
                    failure_code="PROCESS_POOL_START_FAILURE",
                    failure_kind="PARENT_PROCESS_SUPERVISOR_FAILURE",
                    submit_attempted=False,
                    submitted=False,
                    work_tail_unknown=False,
                )
        if executor is not None:
            submit_stopped = False
            for index, occurrence in enumerate(inputs):
                if submit_stopped:
                    journals_by_index[index] = _parent_failure_journal_v1(
                        occurrence,
                        failure_code="BATCH_ABORTED_BEFORE_SUBMIT",
                        failure_kind="PARENT_PROCESS_SUPERVISOR_FAILURE",
                        submit_attempted=False,
                        submitted=False,
                        work_tail_unknown=False,
                    )
                    continue
                try:
                    future = executor.submit(
                        _execute_child_occurrence_v1,
                        occurrence.canonical_bytes,
                        worker_key.value,
                        derived_batch_id,
                        attempt_nonce,
                    )
                    futures.append((index, future))
                except Exception:
                    journals_by_index[index] = _parent_failure_journal_v1(
                        occurrence,
                        failure_code="PROCESS_SUBMIT_FAILURE",
                        failure_kind="PARENT_PROCESS_SUPERVISOR_FAILURE",
                        submit_attempted=True,
                        submitted=False,
                        work_tail_unknown=False,
                    )
                    submit_stopped = True
            for index, future in futures:
                occurrence = inputs[index]
                try:
                    journal_bytes, physical_pid = future.result()
                    if type(physical_pid) is not int or physical_pid <= 0:
                        raise FrozenSourceOccurrenceInvariantViolation(
                            "child returned an invalid physical PID diagnostic"
                        )
                    journal = _load_child_attempt_journal_v1(
                        journal_bytes,
                        occurrence_input=occurrence,
                    )
                    pids_by_index[index] = physical_pid
                    journals_by_index[index] = journal
                except Exception:
                    journals_by_index[index] = _parent_failure_journal_v1(
                        occurrence,
                        failure_code="PROCESS_BOUNDARY_FAILURE",
                        failure_kind="PARENT_PROCESS_BOUNDARY_FAILURE",
                        submit_attempted=True,
                        submitted=True,
                        work_tail_unknown=True,
                    )
    finally:
        if executor is not None:
            try:
                executor.shutdown(wait=True, cancel_futures=False)
            except Exception:
                batch_failure_code = "PROCESS_POOL_SHUTDOWN_FAILURE"
    if any(item is None for item in journals_by_index):
        for index, item in enumerate(journals_by_index):
            if item is None:
                journals_by_index[index] = _parent_failure_journal_v1(
                    inputs[index],
                    failure_code="PROCESS_SUPERVISOR_ACCOUNTING_GAP",
                    failure_kind="PARENT_PROCESS_SUPERVISOR_FAILURE",
                    submit_attempted=False,
                    submitted=False,
                    work_tail_unknown=True,
                )
    frozen_journals = tuple(
        item
        for item in journals_by_index
        if item is not None
    )
    observed_pids = tuple(
        value for value in pids_by_index if value is not None
    )
    if len(set(observed_pids)) != len(observed_pids):
        batch_failure_code = "PROCESS_REUSE_DETECTED"
    if any(
        item.status is ChildAttemptStatusV1.FAILED
        for item in frozen_journals
    ) or batch_failure_code is not None:
        closure = OccurrenceFailureClosureV1(
            source_archive=archive,
            inputs=inputs,
            child_journals=frozen_journals,
            execution_batch_id=derived_batch_id,
            attempt_nonce_id=attempt_nonce,
            batch_failure_code=batch_failure_code,
            _diagnostic_child_pids=tuple(pids_by_index),
        )
        if len(closure.canonical_bytes) > MAX_COMPOSITE_ARTIFACT_BYTES:
            _fail("generated failure closure exceeds its replay byte cap")
        raise FrozenSourceOccurrenceExecutionFailure(
            failure_closure=closure,
        )
    outputs = tuple(
        item.output
        for item in frozen_journals
        if item.output is not None
    )
    merge = CanonicalOccurrenceMergeV1(
        source_archive=archive,
        inputs=inputs,
        outputs=outputs,
        child_journals=frozen_journals,
        execution_batch_id=derived_batch_id,
        attempt_nonce_id=attempt_nonce,
        _diagnostic_child_pids=tuple(observed_pids),
    )
    if len(merge.canonical_bytes) > MAX_COMPOSITE_ARTIFACT_BYTES:
        _fail("generated canonical merge exceeds its replay byte cap")
    replayed_merge = load_canonical_occurrence_merge_v1(
        merge.canonical_bytes,
        source_archive=archive,
        occurrence_inputs=inputs,
        expected_merge_id=merge.merge_id,
    )
    if (
        replayed_merge.merge_id != merge.merge_id
        or replayed_merge.canonical_bytes != merge.canonical_bytes
    ):
        _fail("generated canonical merge failed immediate strict replay")
    return merge


__all__ = [
    "CanonicalOccurrenceMergeV1",
    "ChildAttemptJournalV1",
    "ChildAttemptStatusV1",
    "FrozenSourceArchiveEnvelopeV1",
    "FrozenSourceVerificationAttestationV1",
    "FrozenSourceOccurrenceExecutionFailure",
    "FrozenSourceOccurrenceInvariantViolation",
    "FrozenSourceOfflineWorkV1",
    "MAX_ARCHIVE_BYTES",
    "MAX_COMPOSITE_ARTIFACT_BYTES",
    "MAX_COMPOSITE_FIXED_OVERHEAD_BYTES",
    "MAX_COMPOSITE_PER_OCCURRENCE_OVERHEAD_BYTES",
    "MAX_OCCURRENCES",
    "MAX_OCCURRENCE_BYTES",
    "MAX_OCCURRENCE_OUTPUT_BYTES",
    "MAX_OCCURRENCE_RESULT_PAYLOAD_BYTES",
    "MAX_TARGET_PAYLOAD_BYTES",
    "MAX_WORKERS",
    "OccurrenceFailureClosureV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RegisteredOccurrenceWorkerV1",
    "REGISTERED_OCCURRENCE_ONLINE_COUNTERS",
    "REGISTERED_SOURCE_OFFLINE_COUNTERS",
    "SOURCE_COUNTER_REGISTRY_ID",
    "TargetOccurrenceSpecV1",
    "derive_frozen_execution_batch_id_v1",
    "freeze_source_archive_envelope_v1",
    "load_frozen_source_archive_envelope_v1",
    "load_child_attempt_journal_v1",
    "load_canonical_occurrence_merge_v1",
    "load_occurrence_failure_closure_v1",
    "load_occurrence_output_v1",
    "mint_frozen_source_verification_attestation_v1",
    "run_frozen_source_occurrences_v1",
]
