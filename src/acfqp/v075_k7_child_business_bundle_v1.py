"""Typed, subprocess-free K7 child-business output for the V0-103 successor.

The child consumes a freshly reconstructed V0-105 request authority, verifies
the sealed source/runtime and lifecycle-secret descriptors, reconstructs the
registered K7 ``NO_PRIOR`` schedule, loads the observer signer without Git or
another subprocess, and invokes the existing owned partial runner exactly
once.  Its evidence roots are frozen by the pre-existing strict V2 portable
evidence-bundle authority; this module does not invent a second document DAG.

The output is only the first of the two V0-103 frames.  It contains no parent
accounting suffix and grants no CounterRecord, WorkVector, ComparisonVector,
terminal, certificate, scientific endpoint, or official authority.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import InitVar, dataclass
from functools import wraps
import hashlib
import os
from pathlib import Path
import subprocess
import threading
from typing import Any, Mapping, NoReturn

from acfqp import construction_accounting_partial_native_v1 as partial_native
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import v075_batch_native_statistical_backend_v1 as backend
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary
from acfqp import v075_k7_root_cap_owned_partial_runner_v1 as owned_runner
from acfqp import v075_k7_successor_portable_replay_v1 as portable_replay
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable_evidence
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_production_private_signer_runtime_v1 as signer_runtime
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_reveal_verifying_attestation_authority_v2 as reveal
from acfqp import v075_signer_owning_complete_observer_lifecycle_ipc_v1 as lifecycle
from acfqp import v075_signer_owning_sealed_observer_ipc_v1 as sealed_transport
from acfqp.phase3e_ids import (
    V075_K7_CHILD_BUSINESS_BUNDLE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.98.0"
PROFILE_KEY = "v075_k7_child_business_bundle_v1"
BUSINESS_FRAME_ROLE = "CHILD_OWNED_K7_BUSINESS"
BUNDLE_DOMAIN = V075_K7_CHILD_BUSINESS_BUNDLE_V1_DOMAIN
MAX_BUNDLE_BYTES = 64 * 1024 * 1024

EVIDENCE_ROOT_ROLES = portable_evidence.REQUIRED_ROOT_NAMES
_OPTIONAL_EMPTY_SCALARS = frozenset(
    {
        "child_execution_ledger",
        "child_execution_verification",
        "child_replanning_barrier",
        "child_replanning_barrier_verification",
    }
)
_OPTIONAL_EMPTY_VECTORS = frozenset(
    {
        "promotion_decisions",
        "promotion_decision_verifications",
        "promotion_replanning_barriers",
        "promotion_replanning_barrier_verifications",
    }
)
_SECRET_TAINT_FIELDS = frozenset({"generation_seed_hex", "private_salt_hex"})
_KEY_TAINT_FIELDS = frozenset(
    {"prime_p_hex", "prime_q_hex", "private_exponent_hex"}
)
_BUNDLE_ISSUER = object()
_PRIVATE_TAINT_ISSUER = object()
_SUBPROCESS_GUARD_LOCK = threading.Lock()
_PRIVATE_TAINT_LOCK = threading.Lock()
_PRIVATE_TAINT_RECORDS: dict[
    object,
    tuple[int, str, str, str, str, tuple[bytes, ...]],
] = {}


class V075K7ChildBusinessBundleV1Error(RuntimeError):
    """The K7 child business execution or raw replay failed closed."""


def _fail(message: str) -> NoReturn:
    raise V075K7ChildBusinessBundleV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075K7ChildBusinessBundleV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _hash(payload: Mapping[str, Any]) -> str:
    return content_id(BUNDLE_DOMAIN, dict(payload))


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_BUNDLE_BYTES:
        _fail(f"{label} bytes are empty, mistyped, or over cap")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise V075K7ChildBusinessBundleV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical JSON document")
    return value


def _artifact_document(value: Any, label: str) -> dict[str, Any]:
    method = getattr(value, "to_document", None)
    if not callable(method):
        _fail(f"{label} lacks one canonical-document interface")
    try:
        document = method()
        raw = canonical_json_bytes(document)
    except Exception as error:
        raise V075K7ChildBusinessBundleV1Error(
            f"{label} canonical document failed"
        ) from error
    if type(document) is not dict or loads_canonical_json(raw) != document:
        _fail(f"{label} is not one canonical document")
    return document


def _locks() -> dict[str, bool]:
    return {
        "accounting_cutoff_declared": False,
        "parent_accounting_suffix_issued": False,
        "terminal_artifact_issued": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "actual_projection_proof_issued": False,
        "formal_vector_authorized": False,
        "official_execution_allowed": False,
        "plan_certificate": False,
        "infeasibility_certificate": False,
    }


@contextmanager
def _forbid_stdlib_subprocess_api() -> Any:
    """Block the stdlib subprocess entry points on the single-thread child."""

    if threading.active_count() != 1:
        _fail("subprocess-free child business requires one Python thread")
    if not _SUBPROCESS_GUARD_LOCK.acquire(blocking=False):
        _fail("subprocess-free child business guard is already active")
    names = (
        "Popen",
        "run",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
    )
    originals = {name: getattr(subprocess, name) for name in names}

    def forbidden(*args: Any, **kwargs: Any) -> NoReturn:
        del args, kwargs
        _fail("child business attempted a stdlib subprocess invocation")

    try:
        for name in names:
            setattr(subprocess, name, forbidden)
        yield
    finally:
        for name, value in originals.items():
            setattr(subprocess, name, value)
        _SUBPROCESS_GUARD_LOCK.release()


def _subprocess_api_guarded(function: Any) -> Any:
    @wraps(function)
    def guarded(*args: Any, **kwargs: Any) -> Any:
        with _forbid_stdlib_subprocess_api():
            return function(*args, **kwargs)

    return guarded


def _secret_document(raw: bytes) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise V075K7ChildBusinessBundleV1Error(
            "lifecycle secret is not canonical JSON"
        ) from error
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != raw
        or set(document) != lifecycle._SECRET_KEYS  # noqa: SLF001
    ):
        _fail("lifecycle secret schema or canonical bytes changed")
    _cid(document.get("secret_material_id"), "lifecycle secret")
    return document


def _taint_patterns(
    *,
    secret_document: Mapping[str, Any],
    key_document: Mapping[str, Any],
) -> tuple[bytes, ...]:
    patterns: set[bytes] = set()
    for document, fields in (
        (secret_document, _SECRET_TAINT_FIELDS),
        (key_document, _KEY_TAINT_FIELDS),
    ):
        for name in fields:
            value = document.get(name)
            if type(value) is not str or len(value) < 16:
                _fail("private taint source is missing or malformed")
            encoded = value.encode("ascii", errors="strict")
            patterns.add(encoded)
            try:
                decoded = bytes.fromhex(value)
            except ValueError as error:
                raise V075K7ChildBusinessBundleV1Error(
                    "private taint source is not canonical hexadecimal"
                ) from error
            patterns.add(decoded)
            patterns.add(base64.b64encode(decoded))
    return tuple(sorted(patterns))


def _assert_no_private_taint(raw: bytes, patterns: tuple[bytes, ...]) -> None:
    if (
        type(patterns) is not tuple
        or not patterns
        or any(type(item) is not bytes or len(item) < 8 for item in patterns)
    ):
        _fail("private taint scan lacks exact nonempty byte patterns")
    if any(pattern in raw for pattern in patterns):
        _fail("child business output contains known private material")


class V075K7ChildPrivateTaintAuthorityV1:
    """Nonserializable, request-bound authority for child-local taint scans."""

    # Secret patterns never occupy object attributes.  This blocks dataclass,
    # slots, vars, reduce and reflective state exporters from returning them.
    __slots__ = ()

    def __init__(
        self,
        issuer: object,
        request_id: str,
        sealed_secret_commitment_id: str,
        signer_registry_id: str,
        observer_evidence_key_id: str,
        patterns: tuple[bytes, ...],
    ) -> None:
        if issuer is not _PRIVATE_TAINT_ISSUER:
            _fail("private taint authority is caller-minted")
        for value, label in (
            (request_id, "taint request"),
            (sealed_secret_commitment_id, "taint secret commitment"),
            (signer_registry_id, "taint signer registry"),
            (observer_evidence_key_id, "taint observer key"),
        ):
            _cid(value, label)
        _assert_no_private_taint(b"", patterns)
        record = (
            os.getpid(),
            request_id,
            sealed_secret_commitment_id,
            signer_registry_id,
            observer_evidence_key_id,
            patterns,
        )
        with _PRIVATE_TAINT_LOCK:
            if self in _PRIVATE_TAINT_RECORDS:
                _fail("private taint authority identity was reused")
            _PRIVATE_TAINT_RECORDS[self] = record

    def _record(self) -> tuple[int, str, str, str, str, tuple[bytes, ...]]:
        with _PRIVATE_TAINT_LOCK:
            record = _PRIVATE_TAINT_RECORDS.get(self)
        if record is None or record[0] != os.getpid():
            _fail("private taint authority is stale or crossed between processes")
        return record

    def __repr__(self) -> str:
        record = self._record()
        return (
            "<V075K7ChildPrivateTaintAuthorityV1 "
            f"request_id={record[1]} private_patterns=REDACTED>"
        )

    def __reduce__(self) -> object:
        raise TypeError("private taint authority serialization is forbidden")

    def __reduce_ex__(self, protocol: int) -> object:
        del protocol
        raise TypeError("private taint authority serialization is forbidden")

    def _assert_for_request_replay(
        self,
        request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    ) -> None:
        if (
            type(request_replay)
            is not portable_replay.V075K7SuccessorPortableRequestReplayV1
        ):
            _fail("private taint authority requires the exact request replay")
        request = request_replay.request
        (
            _owner_pid,
            request_id,
            sealed_secret_commitment_id,
            signer_registry_id,
            observer_evidence_key_id,
            _patterns,
        ) = self._record()
        if (
            request_id != request.request_id
            or sealed_secret_commitment_id != request.sealed_secret_commitment_id
            or signer_registry_id != request.signer_registry.registry_id
            or observer_evidence_key_id
            != request.signer_registry.observer_evidence_key.key_id
        ):
            _fail("private taint authority crossed its sealed request identity")

    def _scan(
        self,
        *,
        raw: bytes,
        request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    ) -> None:
        self._assert_for_request_replay(request_replay)
        _assert_no_private_taint(raw, self._record()[5])


def _issue_private_taint_authority(
    *,
    request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    secret_document: Mapping[str, Any],
    key_document: Mapping[str, Any],
) -> V075K7ChildPrivateTaintAuthorityV1:
    request = request_replay.request
    if (
        secret_document.get("secret_material_id")
        != request.sealed_secret_commitment_id
        or key_document.get("registered_signer_registry_id")
        != request.signer_registry.registry_id
        or key_document.get("registered_public_key_id")
        != request.signer_registry.observer_evidence_key.key_id
    ):
        _fail("private taint sources crossed the sealed request identity")
    return V075K7ChildPrivateTaintAuthorityV1(
        _PRIVATE_TAINT_ISSUER,
        request.request_id,
        request.sealed_secret_commitment_id,
        request.signer_registry.registry_id,
        request.signer_registry.observer_evidence_key.key_id,
        _taint_patterns(
            secret_document=secret_document,
            key_document=key_document,
        ),
    )


def _load_k7_signer_and_key_document_once(
    *,
    repository_root: Path,
    private_root: Path,
    private_key_path: Path,
    signer_registry: Any,
) -> tuple[Any, Mapping[str, Any]]:
    """Secure-read one key once, then derive both signer and taint source."""

    repository = signer_runtime._verified_k7_repository_root_without_subprocess_v1(  # noqa: SLF001
        repository_root
    )
    private_directory = signer_runtime._require_path(  # noqa: SLF001
        private_root, "private key root"
    )
    key_path = signer_runtime._require_path(  # noqa: SLF001
        private_key_path, "private key path"
    )
    signer_runtime._verify_k7_strictly_external_private_location_v1(  # noqa: SLF001
        repository_root=repository,
        private_root=private_directory,
        private_key_path=key_path,
    )
    key_raw = signer_runtime._secure_read_private_key(  # noqa: SLF001
        private_root=private_directory,
        private_key_path=key_path,
    )
    key_document = signer_runtime._load_key_document(key_raw)  # noqa: SLF001
    public_key, private_exponent = signer_runtime._validate_private_key(  # noqa: SLF001
        document=key_document,
        signer_registry=signer_registry,
    )
    signer = signer_runtime.V075ProductionObserverEvidenceSignerV1(
        signer_runtime._LOADER_ISSUER,  # noqa: SLF001
        public_key,
        private_exponent,
    )
    challenge = (
        b"acfqp:v075-production-private-signer-load-challenge:v1"
        + b"\x00"
        + bytes.fromhex(signer_registry.registry_id)
    )
    signer.sign_observer_evidence_v1(challenge)
    return signer, key_document


def _derive_exact_no_prior_schedule(
    *,
    repository_root: Path,
    namespace: Any,
) -> tuple[Any, Any]:
    arm = worker.V075WorkerArmV1.NO_PRIOR
    context = namespace.family.replicate_contexts[0]
    occurrence = backend.freeze_v075_batch_native_occurrence_identity_from_namespace_v2(
        namespace=namespace,
        context=context,
        arm=arm,
        occurrence_ordinal=acquisition.ARM_ORDER.index(arm),
        threshold_profile=namespace.workload.threshold_profile,
        cap_profile=namespace.workload.cap_profile,
        source_prior_transport=None,
    )
    schedule = acquisition.freeze_v075_occurrence_initial_acquisition_schedule_v2(
        repository_root=repository_root,
        namespace=namespace,
        occurrence=occurrence,
    )
    slot = schedule.profile.occurrence_slot_for(
        context_id=context.context_id,
        arm=arm,
    )
    replayed, verification = (
        acquisition.verify_v075_occurrence_initial_acquisition_schedule_bytes_v2(
            repository_root=repository_root,
            namespace=namespace,
            expected_slot=slot,
            occurrence_identity_bytes=canonical_json_bytes(
                occurrence.to_document()
            ),
            raw=schedule.canonical_bytes,
        )
    )
    if replayed.canonical_bytes != schedule.canonical_bytes:
        _fail("exact NO_PRIOR schedule replay changed canonical bytes")
    return schedule, verification


def _require_root_graph(
    *,
    roots: Mapping[str, Any],
    schedule: Any,
    verification: Any,
    wrapped: Any,
) -> None:
    if type(roots) is not dict or tuple(roots) != EVIDENCE_ROOT_ROLES:
        _fail("construction evidence root registry changed")
    if (
        roots["initial_schedule"] is not schedule
        or roots["initial_schedule_verification"] is not verification
        or roots["multiround_result"] is not wrapped.result
        or roots["root_model_epoch"] is not roots["final_model_epoch"]
    ):
        _fail("construction evidence roots crossed the executed result")
    for role in _OPTIONAL_EMPTY_SCALARS:
        if roots[role] is not None:
            _fail("root-cap K7 unexpectedly materialized a child branch")
    for role in _OPTIONAL_EMPTY_VECTORS:
        if roots[role] != ():
            _fail("root-cap K7 unexpectedly materialized a promotion branch")


def _one_portable_record(
    bundle: portable_evidence.V075PortableOccurrenceEvidenceBundleV2,
    role: str,
) -> Any:
    matches = tuple(item for item in bundle.records if item.role == role)
    if len(matches) != 1:
        _fail(f"portable evidence lacks exactly one {role} record")
    return matches[0]


def _verify_content_id_document(
    *,
    document: Any,
    expected_fields: frozenset[str],
    schema: str,
    id_field: str,
    domain: str,
    label: str,
) -> dict[str, Any]:
    if type(document) is not dict or set(document) != expected_fields:
        _fail(f"{label} fields changed")
    payload = dict(document)
    claimed = _cid(payload.pop(id_field), label)
    if payload.get("schema") != schema or content_id(domain, payload) != claimed:
        _fail(f"{label} content identity changed")
    return document


_OWNED_FIELDS = frozenset(
    {
        "schema", "schema_version", "profile_key", "original_result_id",
        "partial_native_transcript_id", "cold_cache_profile_id",
        "cold_cache_epoch_id", "counter_registry_id", "stage_profile_id",
        "boundary_profile_id", "execution_profile_id", "terminal_status",
        "coverage_state", "cold_cache_cleared_before_preopen",
        "cold_cache_cleared_after_owned_scope", "evidence_sink_policy",
        "adversarial_callback_isolation_claimed", "original_v2_result_bytes_changed",
        "counter_records_issued", "work_vector_issued",
        "comparison_vector_issued", "official_execution_allowed",
        "certificate_issued", "owned_partial_result_id",
    }
)
_CACHE_PROFILE_FIELDS = frozenset(
    {
        "schema", "schema_version", "profile_key", "clear_authority_module",
        "clear_authority_symbol", "isolation_authority_symbol",
        "cleared_cache_symbols", "clear_before_preopen_required",
        "clear_after_owned_scope_required", "exclusive_owned_wrapper",
        "registered_cache_users_share_isolation_lock",
        "cache_state_changes_numerical_result", "cold_cache_profile_id",
    }
)
_CACHE_EPOCH_FIELDS = frozenset(
    {
        "schema", "schema_version", "profile_key", "cold_cache_profile_id",
        "occurrence_id", "schedule_id", "session_external_id_sha256",
        "exclusive_owned_wrapper_lock_acquired", "clear_before_preopen_committed",
        "clear_after_owned_scope_required", "cold_cache_epoch_id",
    }
)
_TRANSCRIPT_FIELDS = frozenset(
    {
        "schema", "schema_version", "occurrence_start", "chain_nodes",
        "terminal_kind", "occurrence_completion_id", "occurrence_abort_id",
        "counter_records", "work_vector", "comparison_vector",
        "actual_projection", "coverage_state",
        "absent_native_events_inferred_zero", "official_execution_allowed",
        "partial_native_transcript_id",
    }
)


def _validate_known_child_documents(
    *,
    document: Mapping[str, Any],
    portable_bundle: portable_evidence.V075PortableOccurrenceEvidenceBundleV2,
) -> None:
    owned = _verify_content_id_document(
        document=document["owned_partial_result"],
        expected_fields=_OWNED_FIELDS,
        schema="acfqp.v075_k7_root_cap_owned_partial_result.v1",
        id_field="owned_partial_result_id",
        domain=owned_runner.OWNED_PARTIAL_RESULT_DOMAIN,
        label="owned partial result",
    )
    cache_profile = _verify_content_id_document(
        document=document["cold_cache_profile"],
        expected_fields=_CACHE_PROFILE_FIELDS,
        schema="acfqp.v075_k7_root_cap_cold_cache_profile.v1",
        id_field="cold_cache_profile_id",
        domain=owned_runner.COLD_CACHE_PROFILE_DOMAIN,
        label="cold cache profile",
    )
    cache_epoch = _verify_content_id_document(
        document=document["cold_cache_epoch"],
        expected_fields=_CACHE_EPOCH_FIELDS,
        schema="acfqp.v075_k7_root_cap_cold_cache_epoch.v1",
        id_field="cold_cache_epoch_id",
        domain=owned_runner.COLD_CACHE_EPOCH_DOMAIN,
        label="cold cache epoch",
    )
    transcript = _verify_content_id_document(
        document=document["partial_native_transcript"],
        expected_fields=_TRANSCRIPT_FIELDS,
        schema="acfqp.construction_partial_native_occurrence_transcript.v1",
        id_field="partial_native_transcript_id",
        domain=partial_native.PARTIAL_NATIVE_OCCURRENCE_TRANSCRIPT_V1_DOMAIN,
        label="partial-native transcript",
    )
    result_record = _one_portable_record(portable_bundle, "MULTIROUND_RESULT")
    batch_record = _one_portable_record(
        portable_bundle, "SIGNED_BATCH_JOURNAL_CLOSURE"
    )
    start = transcript.get("occurrence_start")
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    boundary_profile = boundary.official_k7_root_cap_operation_boundary_manifest_v3()
    execution_profile = execution.official_v075_k7_root_cap_execution_identity_profile_v1()
    expected_cache_profile = (
        owned_runner.official_v075_k7_root_cap_cold_cache_profile_v1().to_document()
    )
    unavailable = {
        "kind": partial_native.UNAVAILABLE_KIND,
        "reason": partial_native.UNAVAILABLE_REASON,
    }
    if (
        owned["owned_partial_result_id"] != document["owned_partial_result_id"]
        or transcript["partial_native_transcript_id"]
        != document["partial_native_transcript_id"]
        or cache_profile["cold_cache_profile_id"]
        != document["cold_cache_profile_id"]
        or cache_epoch["cold_cache_epoch_id"] != document["cold_cache_epoch_id"]
        or owned["original_result_id"] != result_record.semantic_artifact_id
        or owned["partial_native_transcript_id"]
        != transcript["partial_native_transcript_id"]
        or owned["cold_cache_profile_id"] != cache_profile["cold_cache_profile_id"]
        or owned["cold_cache_epoch_id"] != cache_epoch["cold_cache_epoch_id"]
        or owned["schema_version"] != owned_runner.SCHEMA_VERSION
        or owned["profile_key"] != owned_runner.PROFILE_KEY
        or owned["terminal_status"] != "CHILD_ACTION_ROW_CAP_EXCEEDED"
        or owned["coverage_state"] != partial_native.COVERAGE_STATE
        or owned["cold_cache_cleared_before_preopen"] is not True
        or owned["cold_cache_cleared_after_owned_scope"] is not True
        or owned["evidence_sink_policy"]
        != "COOPERATIVE_SAME_PROCESS_DEFERRED_AFTER_AUTHORITY_CLOSURE"
        or owned["adversarial_callback_isolation_claimed"] is not False
        or owned["original_v2_result_bytes_changed"] is not False
        or owned["counter_registry_id"] != registry.registry_id
        or owned["stage_profile_id"] != stage.stage_profile_id
        or owned["boundary_profile_id"] != boundary_profile.manifest_id
        or owned["execution_profile_id"] != execution_profile.profile_id
        or cache_profile != expected_cache_profile
        or cache_epoch["schema_version"] != owned_runner.SCHEMA_VERSION
        or cache_epoch["profile_key"] != owned_runner.PROFILE_KEY
        or cache_epoch["exclusive_owned_wrapper_lock_acquired"] is not True
        or cache_epoch["clear_before_preopen_committed"] is not True
        or cache_epoch["clear_after_owned_scope_required"] is not True
        or cache_epoch["cold_cache_profile_id"]
        != cache_profile["cold_cache_profile_id"]
        or cache_epoch["occurrence_id"] != document["scientific_occurrence_id"]
        or cache_epoch["schedule_id"] != document["schedule_id"]
        or cache_epoch["session_external_id_sha256"]
        != hashlib.sha256(document["session_external_id"].encode("utf-8")).hexdigest()
        or type(start) is not dict
        or set(start)
        != {
            "schema", "schema_version", "occurrence_id", "counter_registry_id",
            "stage_profile_id", "boundary_profile_id", "recorder_id", "stage_plan",
            "predecessor_chain_id", "chain_sequence", "coverage_state",
            "occurrence_start_id",
        }
        or start.get("schema")
        != "acfqp.construction_partial_native_occurrence_start.v1"
        or start.get("schema_version") != partial_native.SCHEMA_VERSION
        or content_id(
            partial_native.PARTIAL_NATIVE_OCCURRENCE_START_V1_DOMAIN,
            {key: value for key, value in start.items() if key != "occurrence_start_id"},
        )
        != start.get("occurrence_start_id")
        or start.get("occurrence_id") != document["scientific_occurrence_id"]
        or start.get("counter_registry_id") != owned["counter_registry_id"]
        or start.get("stage_profile_id") != owned["stage_profile_id"]
        or start.get("boundary_profile_id") != owned["boundary_profile_id"]
        or start.get("recorder_id") != owned_runner.RECORDER_ID
        or start.get("stage_plan")
        != [item.value for item in partial_native.ROOT_CAP_FIVE_STAGE_PLAN_V1]
        or start.get("predecessor_chain_id")
        != {
            "kind": partial_native.NOT_APPLICABLE_KIND,
            "reason": partial_native.CHAIN_GENESIS_REASON,
        }
        or start.get("chain_sequence") != 0
        or start.get("coverage_state") != partial_native.COVERAGE_STATE
        or type(transcript["chain_nodes"]) is not list
        or not transcript["chain_nodes"]
        or transcript["terminal_kind"] != "COMPLETED"
        or transcript["coverage_state"] != partial_native.COVERAGE_STATE
        or transcript["official_execution_allowed"] is not False
        or transcript["absent_native_events_inferred_zero"] is not False
        or any(
            transcript[name] != unavailable
            for name in (
                "counter_records", "work_vector", "comparison_vector",
                "actual_projection",
            )
        )
        or owned["counter_records_issued"] is not False
        or owned["work_vector_issued"] is not False
        or owned["comparison_vector_issued"] is not False
        or owned["official_execution_allowed"] is not False
        or owned["certificate_issued"] is not False
        or batch_record.artifact_document.get("observer_session_public_id")
        != document["observer_session_public_id"]
    ):
        _fail("child artifact identities or nonformal locks crossed")


_BUNDLE_FIELDS = frozenset(
    {
        "schema", "schema_version", "proposed_contract_version", "profile_key",
        "frame_role", "portable_profile_closure_id", "portable_request_replay_id",
        "successor_profile_id", "request_id", "request_document_sha256",
        "route_identity_id", "scientific_occurrence_id", "schedule_id",
        "phase3e_logical_occurrence_id", "signer_registry_id",
        "observer_evidence_key_id", "opaque_environment_commitment_id",
        "sealed_secret_commitment_id", "session_external_id",
        "observer_session_public_id", "sealed_transport_runtime_check_completed",
        "complete_loaded_module_graph_verified", "private_descriptor_verified",
        "stdlib_subprocess_api_guard_completed", "os_process_spawn_exclusion_claimed",
        "parent_cgroup_process_exclusion_required", "owned_runner_invocation_count",
        "fresh_exec_request_reconstruction_implemented",
        "live_parent_request_object_accepted", "portable_evidence_bundle_id",
        "portable_evidence_bundle_sha256", "portable_evidence_bundle",
        "owned_partial_result_id", "owned_partial_result",
        "partial_native_transcript_id", "partial_native_transcript",
        "cold_cache_profile_id", "cold_cache_profile", "cold_cache_epoch_id",
        "cold_cache_epoch", "known_private_value_taint_scan_completed",
        "known_private_value_match_count", "owned_partial_raw_semantic_replay_complete",
        "parent_suffix_required", "accounting_cutoff_declared",
        "parent_accounting_suffix_issued", "terminal_artifact_issued",
        "counter_records_issued", "work_vector_issued", "comparison_vector_issued",
        "actual_projection_proof_issued", "formal_vector_authorized",
        "official_execution_allowed", "plan_certificate", "infeasibility_certificate",
        "child_business_bundle_id",
    }
)


def _validate_bundle_document(document: Mapping[str, Any]) -> None:
    if type(document) is not dict or set(document) != _BUNDLE_FIELDS:
        _fail("child business bundle fields changed")
    payload = dict(document)
    claimed = _cid(payload.pop("child_business_bundle_id"), "business bundle")
    if (
        document["schema"] != "acfqp.v075_k7_child_business_bundle.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["frame_role"] != BUSINESS_FRAME_ROLE
        or _hash(payload) != claimed
    ):
        _fail("child business bundle identity changed")
    for name in (
        "portable_profile_closure_id", "portable_request_replay_id",
        "successor_profile_id", "request_id", "request_document_sha256",
        "route_identity_id", "scientific_occurrence_id", "schedule_id",
        "phase3e_logical_occurrence_id", "signer_registry_id",
        "observer_evidence_key_id", "opaque_environment_commitment_id",
        "sealed_secret_commitment_id", "session_external_id",
        "observer_session_public_id", "portable_evidence_bundle_id",
        "portable_evidence_bundle_sha256", "owned_partial_result_id",
        "partial_native_transcript_id", "cold_cache_profile_id",
        "cold_cache_epoch_id",
    ):
        _cid(document[name], name)
    if (
        document["sealed_transport_runtime_check_completed"] is not True
        or document["complete_loaded_module_graph_verified"] is not False
        or document["private_descriptor_verified"] is not True
        or document["stdlib_subprocess_api_guard_completed"] is not True
        or document["os_process_spawn_exclusion_claimed"] is not False
        or document["parent_cgroup_process_exclusion_required"] is not True
        or type(document["owned_runner_invocation_count"]) is not int
        or document["owned_runner_invocation_count"] != 1
        or document["fresh_exec_request_reconstruction_implemented"] is not True
        or document["live_parent_request_object_accepted"] is not False
        or document["known_private_value_taint_scan_completed"] is not True
        or type(document["known_private_value_match_count"]) is not int
        or document["known_private_value_match_count"] != 0
        or document["owned_partial_raw_semantic_replay_complete"] is not False
        or document["parent_suffix_required"] is not True
        or any(document[name] is not False for name in _locks())
    ):
        _fail("child business authority or claim locks changed")
    portable_raw = canonical_json_bytes(document["portable_evidence_bundle"])
    if (
        hashlib.sha256(portable_raw).hexdigest()
        != document["portable_evidence_bundle_sha256"]
    ):
        _fail("portable evidence bundle digest changed")
    try:
        portable_bundle = (
            portable_evidence.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
                portable_raw
            )
        )
    except Exception as error:
        raise V075K7ChildBusinessBundleV1Error(
            "portable evidence bundle semantic/topology replay failed"
        ) from error
    if (
        portable_bundle.bundle_id != document["portable_evidence_bundle_id"]
        or portable_bundle.occurrence_id != document["scientific_occurrence_id"]
    ):
        _fail("portable evidence bundle crossed the child occurrence")
    _validate_known_child_documents(
        document=document,
        portable_bundle=portable_bundle,
    )


@dataclass(frozen=True, slots=True)
class V075K7ChildBusinessBundleV1:
    _issuer: InitVar[object]
    _raw: bytes

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BUNDLE_ISSUER or type(self._raw) is not bytes:
            _fail("child business bundle is caller-minted")
        _validate_bundle_document(_canonical_document(self._raw, "business bundle"))

    @property
    def bundle_id(self) -> str:
        return self.to_document()["child_business_bundle_id"]

    @property
    def canonical_bytes(self) -> bytes:
        return self._raw

    def to_document(self) -> dict[str, Any]:
        return _canonical_document(self._raw, "business bundle")


def _freeze_bundle(
    *,
    request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    wrapped: owned_runner.V075K7RootCapOwnedPartialResultV1,
    portable_bundle: portable_evidence.V075PortableOccurrenceEvidenceBundleV2,
    expected_session_public_id: str,
    private_taint_authority: V075K7ChildPrivateTaintAuthorityV1,
) -> V075K7ChildBusinessBundleV1:
    request = request_replay.request
    _cid(expected_session_public_id, "observer session public identity")
    verified_portable = (
        portable_evidence.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            portable_bundle.canonical_bytes
        )
    )
    if verified_portable.bundle_id != portable_bundle.bundle_id:
        _fail("fresh portable evidence bundle failed immediate replay")
    owned_document = _artifact_document(wrapped, "owned partial result")
    transcript_document = _artifact_document(
        wrapped.transcript, "partial-native transcript"
    )
    cache_profile_document = _artifact_document(
        wrapped.cold_cache_profile, "cold cache profile"
    )
    cache_epoch_document = _artifact_document(
        wrapped.cold_cache_epoch, "cold cache epoch"
    )
    portable_document = portable_bundle.to_document()
    payload = {
        "schema": "acfqp.v075_k7_child_business_bundle.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "frame_role": BUSINESS_FRAME_ROLE,
        "portable_profile_closure_id": request_replay.profile_closure.closure_id,
        "portable_request_replay_id": request_replay.replay_id,
        "successor_profile_id": request.profile.profile_id,
        "request_id": request.request_id,
        "request_document_sha256": hashlib.sha256(request.canonical_bytes).hexdigest(),
        "route_identity_id": request.route_identity.route_identity_id,
        "scientific_occurrence_id": request.scientific_occurrence_id,
        "schedule_id": request.schedule_id,
        "phase3e_logical_occurrence_id": (
            request.occurrence_mapping.phase3e_logical_occurrence_id
        ),
        "signer_registry_id": request.signer_registry.registry_id,
        "observer_evidence_key_id": request.signer_registry.observer_evidence_key.key_id,
        "opaque_environment_commitment_id": request.opaque_environment_commitment_id,
        "sealed_secret_commitment_id": request.sealed_secret_commitment_id,
        "session_external_id": request.session_external_id,
        "observer_session_public_id": expected_session_public_id,
        "sealed_transport_runtime_check_completed": True,
        "complete_loaded_module_graph_verified": False,
        "private_descriptor_verified": True,
        "stdlib_subprocess_api_guard_completed": True,
        "os_process_spawn_exclusion_claimed": False,
        "parent_cgroup_process_exclusion_required": True,
        "owned_runner_invocation_count": 1,
        "fresh_exec_request_reconstruction_implemented": True,
        "live_parent_request_object_accepted": False,
        "portable_evidence_bundle_id": portable_bundle.bundle_id,
        "portable_evidence_bundle_sha256": hashlib.sha256(
            portable_bundle.canonical_bytes
        ).hexdigest(),
        "portable_evidence_bundle": portable_document,
        "owned_partial_result_id": wrapped.wrapper_id,
        "owned_partial_result": owned_document,
        "partial_native_transcript_id": wrapped.transcript.transcript_id,
        "partial_native_transcript": transcript_document,
        "cold_cache_profile_id": wrapped.cold_cache_profile.profile_id,
        "cold_cache_profile": cache_profile_document,
        "cold_cache_epoch_id": wrapped.cold_cache_epoch.epoch_id,
        "cold_cache_epoch": cache_epoch_document,
        "known_private_value_taint_scan_completed": True,
        "known_private_value_match_count": 0,
        "owned_partial_raw_semantic_replay_complete": False,
        "parent_suffix_required": True,
        **_locks(),
    }
    raw = canonical_json_bytes(
        {**payload, "child_business_bundle_id": _hash(payload)}
    )
    if len(raw) > MAX_BUNDLE_BYTES:
        _fail("child business bundle exceeds the atomic runtime output cap")
    if type(private_taint_authority) is not V075K7ChildPrivateTaintAuthorityV1:
        _fail("child bundle requires one exact private taint authority")
    private_taint_authority._scan(
        raw=raw,
        request_replay=request_replay,
    )
    return V075K7ChildBusinessBundleV1(_BUNDLE_ISSUER, raw)


@_subprocess_api_guarded
def execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1(
    *,
    request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    source_archive_fd: int,
    sealed_secret_fd: int,
    repository_root: str | Path,
    signer_private_root: Path,
    signer_private_key_path: Path,
) -> V075K7ChildBusinessBundleV1:
    """Execute exactly one sealed K7 business occurrence."""

    if (
        type(request_replay)
        is not portable_replay.V075K7SuccessorPortableRequestReplayV1
    ):
        _fail("child business requires the exact fresh-exec request replay")
    request_replay.profile_closure._assert_current()  # noqa: SLF001
    _cid(request_replay.replay_id, "portable request replay")
    request = request_replay.request
    request._assert_current()  # noqa: SLF001
    transport = request.profile.accounted_profile.transport_profile
    try:
        sealed_transport._assert_child_runtime(  # noqa: SLF001
            expected_runtime_id=transport.runtime_id,
            expected_source_snapshot_id=transport.source_snapshot_id,
            expected_archive_sha256=transport.source_archive_sha256,
            expected_archive_size=transport.source_archive_byte_count,
            archive_fd=source_archive_fd,
        )
    except Exception as error:
        raise V075K7ChildBusinessBundleV1Error(
            "sealed source/runtime verification failed"
        ) from error
    try:
        secret_raw = sealed_transport._read_sealed_fd(  # noqa: SLF001
            sealed_secret_fd,
            cap=lifecycle.MAX_SECRET_BYTES,
        )
        secret_document = _secret_document(secret_raw)
        generated, salt, commitment = lifecycle._load_secret(secret_raw)  # noqa: SLF001
    except Exception as error:
        if isinstance(error, V075K7ChildBusinessBundleV1Error):
            raise
        raise V075K7ChildBusinessBundleV1Error(
            "sealed lifecycle-secret reconstruction failed"
        ) from error
    if (
        secret_document["secret_material_id"]
        != request.sealed_secret_commitment_id
        or commitment.commitment_id != request.opaque_environment_commitment_id
    ):
        _fail("sealed secret or environment commitment differs from the request")

    repository = Path(repository_root).resolve()
    try:
        signer, key_document = _load_k7_signer_and_key_document_once(
            repository_root=repository,
            private_root=signer_private_root,
            private_key_path=signer_private_key_path,
            signer_registry=request.signer_registry,
        )
    except Exception as error:
        raise V075K7ChildBusinessBundleV1Error(
            "subprocess-free registry-bound signer load failed"
        ) from error
    if signer.public_verification_key_v1() != request.signer_registry.observer_evidence_key:
        _fail("loaded observer signer differs from the request registry")
    taint_authority = _issue_private_taint_authority(
        request_replay=request_replay,
        secret_document=secret_document,
        key_document=key_document,
    )

    try:
        base = lifecycle._fixture_base(  # noqa: SLF001
            commitment=commitment,
            signer_registry=request.signer_registry,
        )
        private_reveal = reveal.issue_v075_reveal_verified_private_attestation_v2(
            anchor=base.anchor,
            commitment=base.commitment,
            generated_environment=generated,
            secret_salt=salt,
            signer_registry=request.signer_registry,
            observer_signer=signer,
        )
        authority = lifecycle._authorization(  # noqa: SLF001
            base=base,
            private_reveal=private_reveal,
        )
        binding = observer._require_exact_v2_binding(  # noqa: SLF001
            authority=authority,
            namespace=base.namespace,
        )
        expected_session_id = lifecycle._expected_session_public_id(  # noqa: SLF001
            binding=binding,
            session_external_id=request.session_external_id,
        )
        schedule, verification = _derive_exact_no_prior_schedule(
            repository_root=repository,
            namespace=base.namespace,
        )
    except Exception as error:
        if isinstance(error, V075K7ChildBusinessBundleV1Error):
            raise
        raise V075K7ChildBusinessBundleV1Error(
            "registered K7 fixture/schedule reconstruction failed"
        ) from error
    if (
        schedule.occurrence.occurrence_id != request.scientific_occurrence_id
        or schedule.schedule_id != request.schedule_id
        or base.namespace.signer_registry is not request.signer_registry
        or base.commitment.commitment_id != request.opaque_environment_commitment_id
    ):
        _fail("request scientific, schedule, registry, or commitment identity crossed")

    captured: list[dict[str, Any]] = []

    def capture(values: Mapping[str, Any]) -> None:
        if captured:
            _fail("owned runner emitted construction evidence more than once")
        if tuple(values) != EVIDENCE_ROOT_ROLES:
            _fail("owned runner construction evidence root registry changed")
        captured.append(dict(values))

    try:
        wrapped = owned_runner.run_v075_k7_root_cap_owned_partial_v1(
            repository_root=repository,
            namespace=base.namespace,
            schedule=schedule,
            schedule_verification=verification,
            authority=authority,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
            session_external_id=request.session_external_id,
            evidence_sink=capture,
        )
    except Exception as error:
        raise V075K7ChildBusinessBundleV1Error(
            "owned K7 business runner failed"
        ) from error
    if len(captured) != 1:
        _fail("owned runner did not emit exactly one construction evidence graph")
    roots = captured[0]
    _require_root_graph(
        roots=roots,
        schedule=schedule,
        verification=verification,
        wrapped=wrapped,
    )
    controlled = roots["controlled_journal_closure"]
    if (
        controlled.batch_closure.session_public_id != expected_session_id
        or controlled.batch_closure.occurrence_id != request.scientific_occurrence_id
    ):
        _fail("observer session or occurrence identity changed during execution")
    try:
        portable_bundle = portable_evidence.freeze_v075_portable_occurrence_evidence_bundle_v2(
            evidence_roots=roots
        )
    except Exception as error:
        raise V075K7ChildBusinessBundleV1Error(
            "typed portable evidence freeze failed"
        ) from error
    return _freeze_bundle(
        request_replay=request_replay,
        wrapped=wrapped,
        portable_bundle=portable_bundle,
        expected_session_public_id=expected_session_id,
        private_taint_authority=taint_authority,
    )


def verify_v075_k7_child_business_bundle_bytes_v1(
    *,
    raw: bytes,
    expected_request_replay: portable_replay.V075K7SuccessorPortableRequestReplayV1,
    private_taint_authority: V075K7ChildPrivateTaintAuthorityV1,
) -> V075K7ChildBusinessBundleV1:
    """Strictly replay the child frame against its exact request and secrets."""

    if (
        type(expected_request_replay)
        is not portable_replay.V075K7SuccessorPortableRequestReplayV1
    ):
        _fail("business bundle replay requires the exact request replay")
    expected_request_replay.profile_closure._assert_current()  # noqa: SLF001
    expected = expected_request_replay.request
    document = _canonical_document(raw, "business bundle")
    _validate_bundle_document(document)
    if type(private_taint_authority) is not V075K7ChildPrivateTaintAuthorityV1:
        _fail("business replay requires one exact private taint authority")
    private_taint_authority._scan(
        raw=raw,
        request_replay=expected_request_replay,
    )
    if (
        document["portable_profile_closure_id"]
        != expected_request_replay.profile_closure.closure_id
        or document["portable_request_replay_id"] != expected_request_replay.replay_id
        or document["successor_profile_id"] != expected.profile.profile_id
        or document["request_id"] != expected.request_id
        or document["request_document_sha256"]
        != hashlib.sha256(expected.canonical_bytes).hexdigest()
        or document["route_identity_id"] != expected.route_identity.route_identity_id
        or document["scientific_occurrence_id"] != expected.scientific_occurrence_id
        or document["schedule_id"] != expected.schedule_id
        or document["phase3e_logical_occurrence_id"]
        != expected.occurrence_mapping.phase3e_logical_occurrence_id
        or document["signer_registry_id"] != expected.signer_registry.registry_id
        or document["observer_evidence_key_id"]
        != expected.signer_registry.observer_evidence_key.key_id
        or document["opaque_environment_commitment_id"]
        != expected.opaque_environment_commitment_id
        or document["sealed_secret_commitment_id"]
        != expected.sealed_secret_commitment_id
        or document["session_external_id"] != expected.session_external_id
    ):
        _fail("business bundle crossed its exact V0-103 request")
    return V075K7ChildBusinessBundleV1(_BUNDLE_ISSUER, raw)


__all__ = [
    "BUSINESS_FRAME_ROLE",
    "BUNDLE_DOMAIN",
    "EVIDENCE_ROOT_ROLES",
    "MAX_BUNDLE_BYTES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075K7ChildBusinessBundleV1",
    "V075K7ChildBusinessBundleV1Error",
    "V075K7ChildPrivateTaintAuthorityV1",
    "execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1",
    "verify_v075_k7_child_business_bundle_bytes_v1",
]
