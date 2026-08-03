from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
import inspect
import os
import pickle
import signal
from types import SimpleNamespace

import pytest

from acfqp.exact_frozen_memo_v1 import disable_exact_frozen_memoization_v1
from acfqp import construction_accounting_partial_native_v1 as partial_native
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import campaign_v1 as campaign
from acfqp import routing_v1 as routing
from acfqp import v075_k7_child_business_bundle_v1 as business
from acfqp import v075_k7_parent_owned_successor_ipc_v1 as successor
from acfqp import v075_k7_root_cap_accounted_sealed_ipc_v1 as accounted
from acfqp import v075_k7_root_cap_execution_identity_overlay_v1 as execution
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary
from acfqp import v075_k7_root_cap_owned_partial_runner_v1 as owned
from acfqp import v075_k7_successor_portable_replay_v1 as portable_replay
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as portable_evidence
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json
from tests import test_v075_private_observer_boundary_v2 as observer_fixture
from tests.test_v075_observer_signed_multiround_occurrence_runner_v2 import (
    REPOSITORY_ROOT,
    _exact_schedule,
)
from tests.test_v075_portable_occurrence_evidence_bundle_v2 import (
    _rehash_complete_bundle_wrapper,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-k7-child-business-bundle-test:v2\x00"
        + label.encode("utf-8")
    ).hexdigest()


class _Document:
    def __init__(self, document: dict) -> None:
        self._document = document

    def to_document(self) -> dict:
        return deepcopy(self._document)


class _Request:
    def __init__(self) -> None:
        self.profile = SimpleNamespace(profile_id=_id("successor-profile"))
        self.route_identity = SimpleNamespace(route_identity_id=_id("route"))
        self.scientific_occurrence_id = _id("science")
        self.schedule_id = _id("schedule")
        self.occurrence_mapping = SimpleNamespace(
            phase3e_logical_occurrence_id=_id("logical")
        )
        self.signer_registry = SimpleNamespace(
            registry_id=_id("registry"),
            observer_evidence_key=SimpleNamespace(key_id=_id("observer-key")),
        )
        self.opaque_environment_commitment_id = _id("opaque")
        self.sealed_secret_commitment_id = _id("secret")
        self.session_external_id = _id("session")
        self.request_id = _id("request")
        self.canonical_bytes = canonical_json_bytes(
            {"schema": "acfqp.test_request.v1", "request_id": self.request_id}
        )

    def _assert_current(self) -> None:
        return None


class _Replay:
    def __init__(self, request: _Request) -> None:
        self.request = request
        self.replay_id = _id("portable-replay")
        self.profile_closure = SimpleNamespace(
            closure_id=_id("portable-profile-closure"),
            _assert_current=lambda: None,
        )


class _Record:
    def __init__(self, role: str, semantic_id: str, document: dict) -> None:
        self.role = role
        self.semantic_artifact_id = semantic_id
        self.artifact_document = document


class _Portable:
    def __init__(self, occurrence_id: str, result_id: str, session_id: str) -> None:
        self.occurrence_id = occurrence_id
        self.records = (
            _Record("MULTIROUND_RESULT", result_id, {"schema": "result"}),
            _Record(
                "SIGNED_BATCH_JOURNAL_CLOSURE",
                _id("batch-closure"),
                {
                    "schema": "batch-closure",
                    "observer_session_public_id": session_id,
                },
            ),
        )
        payload = {
            "schema": "acfqp.test_portable_evidence.v1",
            "occurrence_id": occurrence_id,
            "result_id": result_id,
            "session_public_id": session_id,
        }
        self.bundle_id = hashlib.sha256(
            b"acfqp:test-k7-child-portable-evidence:v1\x00"
            + canonical_json_bytes(payload)
        ).hexdigest()
        self._document = {**payload, "bundle_id": self.bundle_id}
        self.canonical_bytes = canonical_json_bytes(self._document)

    def to_document(self) -> dict:
        return deepcopy(self._document)


def _content_document(payload: dict, *, domain: str, id_field: str) -> dict:
    return {**payload, id_field: content_id(domain, payload)}


def _substrate(monkeypatch: pytest.MonkeyPatch):
    request = _Request()
    replay = _Replay(request)
    session_id = _id("observer-session")
    result_id = _id("multiround-result")
    portable = _Portable(request.scientific_occurrence_id, result_id, session_id)

    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    boundary_profile = boundary.official_k7_root_cap_operation_boundary_manifest_v3()
    execution_profile = execution.official_v075_k7_root_cap_execution_identity_profile_v1()
    cache_profile = owned.official_v075_k7_root_cap_cold_cache_profile_v1()
    cache_epoch_payload = {
        "schema": "acfqp.v075_k7_root_cap_cold_cache_epoch.v1",
        "schema_version": owned.SCHEMA_VERSION,
        "profile_key": owned.PROFILE_KEY,
        "cold_cache_profile_id": cache_profile.profile_id,
        "occurrence_id": request.scientific_occurrence_id,
        "schedule_id": request.schedule_id,
        "session_external_id_sha256": hashlib.sha256(
            request.session_external_id.encode("utf-8")
        ).hexdigest(),
        "exclusive_owned_wrapper_lock_acquired": True,
        "clear_before_preopen_committed": True,
        "clear_after_owned_scope_required": True,
    }
    cache_epoch_document = _content_document(
        cache_epoch_payload,
        domain=owned.COLD_CACHE_EPOCH_DOMAIN,
        id_field="cold_cache_epoch_id",
    )
    unavailable = {
        "kind": partial_native.UNAVAILABLE_KIND,
        "reason": partial_native.UNAVAILABLE_REASON,
    }
    start_payload = {
        "schema": "acfqp.construction_partial_native_occurrence_start.v1",
        "schema_version": partial_native.SCHEMA_VERSION,
        "occurrence_id": request.scientific_occurrence_id,
        "counter_registry_id": registry.registry_id,
        "stage_profile_id": stage.stage_profile_id,
        "boundary_profile_id": boundary_profile.manifest_id,
        "recorder_id": owned.RECORDER_ID,
        "stage_plan": [
            item.value for item in partial_native.ROOT_CAP_FIVE_STAGE_PLAN_V1
        ],
        "predecessor_chain_id": {
            "kind": partial_native.NOT_APPLICABLE_KIND,
            "reason": partial_native.CHAIN_GENESIS_REASON,
        },
        "chain_sequence": 0,
        "coverage_state": partial_native.COVERAGE_STATE,
    }
    start_document = _content_document(
        start_payload,
        domain=partial_native.PARTIAL_NATIVE_OCCURRENCE_START_V1_DOMAIN,
        id_field="occurrence_start_id",
    )
    transcript_payload = {
        "schema": "acfqp.construction_partial_native_occurrence_transcript.v1",
        "schema_version": partial_native.SCHEMA_VERSION,
        "occurrence_start": start_document,
        "chain_nodes": [{"schema": "acfqp.test_terminal_node.v1"}],
        "terminal_kind": "COMPLETED",
        "occurrence_completion_id": _id("completion"),
        "occurrence_abort_id": {"kind": "NOT_APPLICABLE", "reason": "NO_ABORT"},
        "counter_records": unavailable,
        "work_vector": unavailable,
        "comparison_vector": unavailable,
        "actual_projection": unavailable,
        "coverage_state": partial_native.COVERAGE_STATE,
        "absent_native_events_inferred_zero": False,
        "official_execution_allowed": False,
    }
    transcript_document = _content_document(
        transcript_payload,
        domain=partial_native.PARTIAL_NATIVE_OCCURRENCE_TRANSCRIPT_V1_DOMAIN,
        id_field="partial_native_transcript_id",
    )
    owned_payload = {
        "schema": "acfqp.v075_k7_root_cap_owned_partial_result.v1",
        "schema_version": owned.SCHEMA_VERSION,
        "profile_key": owned.PROFILE_KEY,
        "original_result_id": result_id,
        "partial_native_transcript_id": transcript_document[
            "partial_native_transcript_id"
        ],
        "cold_cache_profile_id": cache_profile.profile_id,
        "cold_cache_epoch_id": cache_epoch_document["cold_cache_epoch_id"],
        "counter_registry_id": registry.registry_id,
        "stage_profile_id": stage.stage_profile_id,
        "boundary_profile_id": boundary_profile.manifest_id,
        "execution_profile_id": execution_profile.profile_id,
        "terminal_status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
        "coverage_state": partial_native.COVERAGE_STATE,
        "cold_cache_cleared_before_preopen": True,
        "cold_cache_cleared_after_owned_scope": True,
        "evidence_sink_policy": (
            "COOPERATIVE_SAME_PROCESS_DEFERRED_AFTER_AUTHORITY_CLOSURE"
        ),
        "adversarial_callback_isolation_claimed": False,
        "original_v2_result_bytes_changed": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "official_execution_allowed": False,
        "certificate_issued": False,
    }
    owned_document = _content_document(
        owned_payload,
        domain=owned.OWNED_PARTIAL_RESULT_DOMAIN,
        id_field="owned_partial_result_id",
    )
    wrapped = SimpleNamespace(
        wrapper_id=owned_document["owned_partial_result_id"],
        to_document=lambda: deepcopy(owned_document),
        transcript=SimpleNamespace(
            transcript_id=transcript_document["partial_native_transcript_id"],
            to_document=lambda: deepcopy(transcript_document),
        ),
        cold_cache_profile=SimpleNamespace(
            profile_id=cache_profile.profile_id,
            to_document=cache_profile.to_document,
        ),
        cold_cache_epoch=SimpleNamespace(
            epoch_id=cache_epoch_document["cold_cache_epoch_id"],
            to_document=lambda: deepcopy(cache_epoch_document),
        ),
    )

    def verify_portable(raw: bytes):
        if raw != portable.canonical_bytes:
            raise ValueError("forged portable evidence")
        return portable

    monkeypatch.setattr(
        business.portable_evidence,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        verify_portable,
    )
    monkeypatch.setattr(
        business.portable_replay,
        "V075K7SuccessorPortableRequestReplayV1",
        _Replay,
    )
    secret_hex = b"known-private-seed-value".hex()
    key_hex = b"known-private-key-value".hex()
    authority = business._issue_private_taint_authority(  # noqa: SLF001
        request_replay=replay,
        secret_document={
            "secret_material_id": request.sealed_secret_commitment_id,
            "generation_seed_hex": secret_hex,
            "private_salt_hex": (b"alternate-private-salt").hex(),
        },
        key_document={
            "registered_signer_registry_id": request.signer_registry.registry_id,
            "registered_public_key_id": (
                request.signer_registry.observer_evidence_key.key_id
            ),
            "prime_p_hex": key_hex,
            "prime_q_hex": (b"alternate-prime-value").hex(),
            "private_exponent_hex": (b"alternate-exponent-value").hex(),
        },
    )
    bundle = business._freeze_bundle(  # noqa: SLF001
        request_replay=replay,
        wrapped=wrapped,
        portable_bundle=portable,
        expected_session_public_id=session_id,
        private_taint_authority=authority,
    )
    return request, replay, portable, wrapped, authority, bundle


def _rehash(document: dict) -> bytes:
    payload = dict(document)
    payload.pop("child_business_bundle_id", None)
    document["child_business_bundle_id"] = content_id(
        business.BUNDLE_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_bundle_replays_strict_portable_evidence_and_all_request_coordinates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, portable, wrapped, authority, bundle = _substrate(monkeypatch)
    result = business.verify_v075_k7_child_business_bundle_bytes_v1(
        raw=bundle.canonical_bytes,
        expected_request_replay=replay,
        private_taint_authority=authority,
    )
    document = result.to_document()
    assert document["portable_evidence_bundle_id"] == portable.bundle_id
    assert document["owned_partial_result_id"] == wrapped.wrapper_id
    assert document["request_document_sha256"] == hashlib.sha256(
        request.canonical_bytes
    ).hexdigest()
    assert document["complete_loaded_module_graph_verified"] is False
    assert document["os_process_spawn_exclusion_claimed"] is False
    assert document["counter_records_issued"] is False
    assert document["work_vector_issued"] is False
    assert document["comparison_vector_issued"] is False
    assert document["official_execution_allowed"] is False


def test_exact_raw_validation_transaction_cached_disabled_and_equal_copy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    raw = bundle.canonical_bytes
    equal_copy = bytes(bytearray(raw))
    assert equal_copy == raw
    assert equal_copy is not raw
    original = business._compute_bundle_validation_facts_v1  # noqa: SLF001
    calls = 0

    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(business, "_compute_bundle_validation_facts_v1", counted)
    cached = business.verify_v075_k7_child_business_bundle_public_bytes_v1(
        raw=raw,
        expected_request_replay=replay,
    )
    assert calls == 1
    copied = business.verify_v075_k7_child_business_bundle_public_bytes_v1(
        raw=equal_copy,
        expected_request_replay=replay,
    )
    assert calls == 2
    before_disabled = calls
    with disable_exact_frozen_memoization_v1():
        reference = (
            business.verify_v075_k7_child_business_bundle_public_bytes_v1(
                raw=raw,
                expected_request_replay=replay,
            )
        )
        reference_id = reference.bundle_id
    assert cached.bundle_id == copied.bundle_id == reference_id
    assert calls == before_disabled + 2


def test_exact_raw_validation_rejects_one_byte_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    attacked = bytearray(bundle.canonical_bytes)
    offset = bundle.canonical_bytes.index(request.request_id.encode("ascii"))
    attacked[offset] = ord("0") if attacked[offset] != ord("0") else ord("1")
    with pytest.raises(business.V075K7ChildBusinessBundleV1Error):
        business.verify_v075_k7_child_business_bundle_public_bytes_v1(
            raw=bytes(attacked),
            expected_request_replay=replay,
        )


def test_exact_raw_validation_formula_monkeypatch_invalidates_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    raw = bundle.canonical_bytes
    business.verify_v075_k7_child_business_bundle_public_bytes_v1(
        raw=raw,
        expected_request_replay=replay,
    )
    original = business._validate_bundle_document  # noqa: SLF001

    def altered(document):
        original(document)
        raise business.V075K7ChildBusinessBundleV1Error(
            "exact validation monkeypatch probe"
        )

    monkeypatch.setattr(business, "_validate_bundle_document", altered)
    with pytest.raises(
        business.V075K7ChildBusinessBundleV1Error,
        match="monkeypatch probe",
    ):
        business.verify_v075_k7_child_business_bundle_public_bytes_v1(
            raw=raw,
            expected_request_replay=replay,
        )
    with disable_exact_frozen_memoization_v1():
        with pytest.raises(
            business.V075K7ChildBusinessBundleV1Error,
            match="monkeypatch probe",
        ):
            business.verify_v075_k7_child_business_bundle_public_bytes_v1(
                raw=raw,
                expected_request_replay=replay,
            )


def test_exact_raw_validation_does_not_cross_transaction_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    original = business._compute_bundle_validation_facts_v1  # noqa: SLF001
    calls = 0

    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(business, "_compute_bundle_validation_facts_v1", counted)
    with business._bundle_validation_transaction_v1():  # noqa: SLF001
        for _ in range(2):
            business.verify_v075_k7_child_business_bundle_public_bytes_v1(
                raw=bundle.canonical_bytes,
                expected_request_replay=replay,
            )
    assert calls == 2


def test_exact_raw_validation_disabled_path_bypasses_transaction_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    original = business._compute_bundle_validation_facts_v1  # noqa: SLF001
    calls = 0

    def counted(*args):
        nonlocal calls
        calls += 1
        return original(*args)

    monkeypatch.setattr(business, "_compute_bundle_validation_facts_v1", counted)
    with disable_exact_frozen_memoization_v1():
        for _ in range(2):
            business.verify_v075_k7_child_business_bundle_public_bytes_v1(
                raw=bundle.canonical_bytes,
                expected_request_replay=replay,
            )
    assert calls == 4


def test_portable_schema_in_place_mutation_cannot_reuse_prior_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    nested_registry = (
        business.portable_evidence._SCHEMA_NESTED_PRIMARY_DOCUMENT_IDS  # noqa: SLF001
    )
    probe = "acfqp.transaction-local-schema-mutation-probe.v1"
    original_verifier = (
        business.portable_evidence
        .verify_v075_portable_occurrence_evidence_bundle_bytes_v2
    )

    def state_sensitive_verifier(raw: bytes):
        if probe in nested_registry:
            raise ValueError("in-place portable schema mutation observed")
        return original_verifier(raw)

    monkeypatch.setattr(
        business.portable_evidence,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        state_sensitive_verifier,
    )
    business.verify_v075_k7_child_business_bundle_public_bytes_v1(
        raw=bundle.canonical_bytes,
        expected_request_replay=replay,
    )
    nested_registry[probe] = frozenset({"probe_id"})
    try:
        with pytest.raises(
            business.V075K7ChildBusinessBundleV1Error,
            match="portable evidence bundle semantic/topology replay failed",
        ):
            business.verify_v075_k7_child_business_bundle_public_bytes_v1(
                raw=bundle.canonical_bytes,
                expected_request_replay=replay,
            )
    finally:
        nested_registry.pop(probe)


def test_portable_role_and_global_replacement_cannot_reuse_prior_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    expected_roles = business.portable_evidence.ROLE_SCHEMA_REGISTRY
    expected_scope = business.portable_evidence.TERMINAL_SCOPE
    original_verifier = (
        business.portable_evidence
        .verify_v075_portable_occurrence_evidence_bundle_bytes_v2
    )

    def state_sensitive_verifier(raw: bytes):
        if business.portable_evidence.ROLE_SCHEMA_REGISTRY is not expected_roles:
            raise ValueError("portable role registry replacement observed")
        if business.portable_evidence.TERMINAL_SCOPE != expected_scope:
            raise ValueError("portable global replacement observed")
        return original_verifier(raw)

    monkeypatch.setattr(
        business.portable_evidence,
        "verify_v075_portable_occurrence_evidence_bundle_bytes_v2",
        state_sensitive_verifier,
    )
    business.verify_v075_k7_child_business_bundle_public_bytes_v1(
        raw=bundle.canonical_bytes,
        expected_request_replay=replay,
    )
    monkeypatch.setattr(
        business.portable_evidence,
        "ROLE_SCHEMA_REGISTRY",
        dict(expected_roles),
    )
    with pytest.raises(
        business.V075K7ChildBusinessBundleV1Error,
        match="portable evidence bundle semantic/topology replay failed",
    ):
        business.verify_v075_k7_child_business_bundle_public_bytes_v1(
            raw=bundle.canonical_bytes,
            expected_request_replay=replay,
        )
    monkeypatch.setattr(
        business.portable_evidence,
        "ROLE_SCHEMA_REGISTRY",
        expected_roles,
    )
    monkeypatch.setattr(
        business.portable_evidence,
        "TERMINAL_SCOPE",
        "TRANSACTION_LOCAL_GLOBAL_MUTATION_PROBE",
    )
    with pytest.raises(
        business.V075K7ChildBusinessBundleV1Error,
        match="portable evidence bundle semantic/topology replay failed",
    ):
        business.verify_v075_k7_child_business_bundle_public_bytes_v1(
            raw=bundle.canonical_bytes,
            expected_request_replay=replay,
        )


def test_bundle_external_issuance_seal_rejects_raw_and_fact_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, _replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    forged_id = _id("forged-object-local-bundle-id")
    for name, value in (
        ("_validated_raw", b"{}"),
        ("_validated_bundle_id", forged_id),
    ):
        with pytest.raises(AttributeError):
            object.__setattr__(bundle, name, value)
    object.__setattr__(bundle, "_raw", b"{}")
    with pytest.raises(
        business.V075K7ChildBusinessBundleV1Error,
        match="changed after issuance",
    ):
        _ = bundle.bundle_id


def test_equal_raw_bundles_keep_original_equality_and_independent_seals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, _replay, _portable, _wrapped, _authority, issued = _substrate(
        monkeypatch
    )
    raw = issued.canonical_bytes
    first = business.V075K7ChildBusinessBundleV1(  # noqa: SLF001
        business._BUNDLE_ISSUER,  # noqa: SLF001
        raw,
    )
    second = business.V075K7ChildBusinessBundleV1(  # noqa: SLF001
        business._BUNDLE_ISSUER,  # noqa: SLF001
        raw,
    )
    assert first is not second
    assert first == second
    assert hash(first) == hash(second) == hash((raw,))
    first_record = business._bundle_issuance_record_v1(first)  # noqa: SLF001
    second_record = business._bundle_issuance_record_v1(second)  # noqa: SLF001
    assert first_record is not second_record
    expected_id = second.bundle_id

    object.__setattr__(first, "_raw", b"{}")
    with pytest.raises(
        business.V075K7ChildBusinessBundleV1Error,
        match="changed after issuance",
    ):
        first.bundle_id
    assert second.bundle_id == expected_id


def test_bundle_properties_preserve_original_parse_only_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, _replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    expected_id = bundle.bundle_id
    raw = bundle.canonical_bytes
    original_parser = business._canonical_document  # noqa: SLF001
    parse_calls = 0

    def counted_parser(*args):
        nonlocal parse_calls
        parse_calls += 1
        return original_parser(*args)

    def forbidden_full_validator(document):
        del document
        raise AssertionError("issued child property performed full replay")

    monkeypatch.setattr(business, "_canonical_document", counted_parser)
    monkeypatch.setattr(
        business,
        "_validate_bundle_document",
        forbidden_full_validator,
    )
    assert bundle.bundle_id == expected_id
    assert bundle.to_document()["child_business_bundle_id"] == expected_id
    assert bundle.canonical_bytes == raw
    assert parse_calls == 2


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires POSIX fork")
def test_bundle_issuance_seal_rejects_cross_pid_use(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, _replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    reader, writer = os.pipe()
    child_pid = os.fork()
    if child_pid == 0:  # pragma: no cover - asserted through the pipe
        os.close(reader)
        outcome = b"unexpected-accept"
        try:
            _ = bundle.bundle_id
        except business.V075K7ChildBusinessBundleV1Error:
            outcome = b"rejected"
        except BaseException:
            outcome = b"wrong-error"
        os.write(writer, outcome)
        os.close(writer)
        os._exit(0)
    os.close(writer)
    try:
        outcome = os.read(reader, 64)
    finally:
        os.close(reader)
    waited_pid, status = os.waitpid(child_pid, 0)
    assert waited_pid == child_pid
    assert os.waitstatus_to_exitcode(status) == 0
    assert outcome == b"rejected"


@pytest.mark.skipif(not hasattr(os, "fork"), reason="requires POSIX fork")
def test_bundle_fork_child_reinitializes_parent_held_issuance_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, _replay, _portable, _wrapped, _authority, bundle = _substrate(
        monkeypatch
    )
    reader, writer = os.pipe()
    parent_lock = business._BUNDLE_ISSUANCE_LOCK  # noqa: SLF001
    parent_lock.acquire()
    child_pid = os.fork()
    if child_pid == 0:  # pragma: no cover - asserted through the pipe
        os.close(reader)
        signal.alarm(5)
        outcome = b"unexpected-accept"
        try:
            _ = bundle.bundle_id
        except business.V075K7ChildBusinessBundleV1Error:
            outcome = b"rejected"
        except BaseException:
            outcome = b"wrong-error"
        os.write(writer, outcome)
        signal.alarm(0)
        os.close(writer)
        os._exit(0)
    os.close(writer)
    try:
        outcome = os.read(reader, 64)
    finally:
        parent_lock.release()
        os.close(reader)
    waited_pid, status = os.waitpid(child_pid, 0)
    assert waited_pid == child_pid
    assert os.waitstatus_to_exitcode(status) == 0
    assert outcome == b"rejected"


def test_all_roots_absent_and_request_as_main_attacks_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, authority, bundle = _substrate(monkeypatch)
    changed = bundle.to_document()
    changed["portable_evidence_bundle"] = {
        "schema": "acfqp.test_portable_evidence.v1",
        "all_roots": "ABSENT",
    }
    changed["portable_evidence_bundle_sha256"] = hashlib.sha256(
        canonical_json_bytes(changed["portable_evidence_bundle"])
    ).hexdigest()
    with pytest.raises(business.V075K7ChildBusinessBundleV1Error):
        business.verify_v075_k7_child_business_bundle_bytes_v1(
            raw=_rehash(changed),
            expected_request_replay=replay,
            private_taint_authority=authority,
        )

    changed = bundle.to_document()
    changed["owned_partial_result"] = {
        "schema": "acfqp.test_request.v1",
        "request_id": replay.request.request_id,
    }
    with pytest.raises(business.V075K7ChildBusinessBundleV1Error):
        business.verify_v075_k7_child_business_bundle_bytes_v1(
            raw=_rehash(changed),
            expected_request_replay=replay,
            private_taint_authority=authority,
        )


def test_unknown_field_private_taint_and_nested_semantic_mutations_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, authority, bundle = _substrate(monkeypatch)
    changed = bundle.to_document()
    changed["unreferenced_secret"] = "known-private-seed-value"
    with pytest.raises(business.V075K7ChildBusinessBundleV1Error):
        business.verify_v075_k7_child_business_bundle_bytes_v1(
            raw=_rehash(changed),
            expected_request_replay=replay,
            private_taint_authority=authority,
        )

    changed = bundle.to_document()
    changed["owned_partial_result"]["original_result_id"] = _id("forged-result")
    payload = dict(changed["owned_partial_result"])
    payload.pop("owned_partial_result_id")
    changed["owned_partial_result"]["owned_partial_result_id"] = content_id(
        owned.OWNED_PARTIAL_RESULT_DOMAIN, payload
    )
    changed["owned_partial_result_id"] = changed["owned_partial_result"][
        "owned_partial_result_id"
    ]
    with pytest.raises(business.V075K7ChildBusinessBundleV1Error):
        business.verify_v075_k7_child_business_bundle_bytes_v1(
            raw=_rehash(changed),
            expected_request_replay=replay,
            private_taint_authority=authority,
        )

    with pytest.raises(
        business.V075K7ChildBusinessBundleV1Error,
        match="known private material",
    ):
        authority._scan(  # noqa: SLF001
            raw=b'"alternate_secret_key":"known-private-key-value"',
            request_replay=replay,
        )


@pytest.mark.parametrize(
    "field",
    (
        "phase3e_logical_occurrence_id",
        "observer_evidence_key_id",
        "opaque_environment_commitment_id",
        "session_external_id",
    ),
)
def test_every_redundant_request_coordinate_is_rechecked(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    _request, replay, _portable, _wrapped, authority, bundle = _substrate(monkeypatch)
    changed = bundle.to_document()
    changed[field] = _id(f"forged-{field}")
    with pytest.raises(business.V075K7ChildBusinessBundleV1Error):
        business.verify_v075_k7_child_business_bundle_bytes_v1(
            raw=_rehash(changed),
            expected_request_replay=replay,
            private_taint_authority=authority,
        )


@pytest.mark.parametrize(
    "entry",
    ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"),
)
def test_stdlib_subprocess_guard_is_exact_and_restored(entry: str) -> None:
    original = getattr(business.subprocess, entry)
    with pytest.raises(
        business.V075K7ChildBusinessBundleV1Error,
        match="stdlib subprocess",
    ):
        with business._forbid_stdlib_subprocess_api():  # noqa: SLF001
            getattr(business.subprocess, entry)("git", "status")
    assert getattr(business.subprocess, entry) is original


def test_source_uses_existing_portable_authority_not_a_generic_document_table() -> None:
    source = inspect.getsource(business)
    assert "freeze_v075_portable_occurrence_evidence_bundle_v2" in source
    assert "verify_v075_portable_occurrence_evidence_bundle_bytes_v2" in source
    assert "_DocumentCollector" not in source
    assert "documents" not in business._BUNDLE_FIELDS  # noqa: SLF001


def test_taint_patterns_include_raw_hex_and_base64_forms() -> None:
    seed = bytes.fromhex("11" * 32)
    salt = bytes.fromhex("22" * 32)
    prime = bytes.fromhex("33" * 32)
    patterns = business._taint_patterns(  # noqa: SLF001
        secret_document={
            "generation_seed_hex": seed.hex(),
            "private_salt_hex": salt.hex(),
        },
        key_document={
            "prime_p_hex": prime.hex(),
            "prime_q_hex": (b"D" * 32).hex(),
            "private_exponent_hex": (b"E" * 32).hex(),
        },
    )
    assert seed in patterns
    assert seed.hex().encode() in patterns
    assert __import__("base64").b64encode(seed) in patterns


def _real_request_replay(
    *,
    signer_registry,
    occurrence_id: str,
    schedule_id: str,
    session_external_id: str,
    opaque_environment_commitment_id: str,
):
    old_profile = accounted.freeze_v075_k7_root_cap_accounted_sealed_ipc_profile_v1(
        timeout_milliseconds=5_000
    )
    profile = successor.freeze_v075_k7_parent_owned_successor_ipc_profile_v1(
        accounted_profile=old_profile
    )
    occurrence = campaign.LogicalOccurrenceV1(
        _id("real-workload"),
        _id("real-protocol"),
        1,
        _id("real-structural"),
        _id("real-query"),
        _id("real-selected-plan"),
        _id("real-threshold"),
        _id("real-build-epoch"),
        campaign.RebuildPolicyV1().rebuild_policy_id,
    )
    attempt = campaign.RouteAttemptV1.initial(occurrence)
    context = routing.RouteDecisionContextV1(
        _id("real-preregistration"),
        occurrence.protocol_id,
        old_profile.comparison_profile_id,
        old_profile.counter_registry_id,
        occurrence.structural_id,
        occurrence.query_id,
        occurrence.selected_plan_id,
        occurrence.threshold_profile_id,
        attempt.build_epoch_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
    )
    decision = routing.DecisionPointV1(
        context.route_decision_context_id,
        1,
        _id("real-frontier"),
        _id("real-causal"),
        _id("real-common-prefix"),
    )
    transaction = routing.TransactionV1(
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        decision.decision_point_id,
        1,
        decision.frontier_snapshot_id,
        _id("real-route-cap"),
    )
    route = accounted.freeze_v075_k7_root_cap_accounted_sealed_route_identity_v1(
        profile=old_profile,
        logical_occurrence=occurrence,
        route_attempt=attempt,
        route_context=context,
        decision_point=decision,
        transaction=transaction,
    )
    request = successor.freeze_v075_k7_parent_owned_successor_request_v1(
        profile=profile,
        route_identity=route,
        signer_registry=signer_registry,
        opaque_environment_commitment_id=opaque_environment_commitment_id,
        sealed_secret_commitment_id=_id("real-sealed-secret"),
        session_external_id=session_external_id,
        request_nonce=_id("real-request-nonce"),
        scientific_occurrence_id=occurrence_id,
        schedule_id=schedule_id,
    )
    transport = old_profile.transport_profile
    lifecycle_profile = old_profile.private_replay_profile
    closure = portable_replay.reconstruct_v075_k7_successor_portable_profile_closure_v1(
        source_archive_raw=transport._archive_bytes,  # noqa: SLF001
        transport_profile_raw=canonical_json_bytes(transport.to_document()),
        lifecycle_profile_raw=canonical_json_bytes(lifecycle_profile.to_document()),
        successor_profile_raw=canonical_json_bytes(profile.to_document()),
    )
    return portable_replay.replay_v075_k7_successor_request_bytes_portable_v1(
        raw=request.canonical_bytes,
        profile_closure=closure,
    )


@pytest.fixture(scope="module")
def real_portable_business_bundle():
    marker = "child-business-real-portable-integration"
    generated, salt, namespace, authorization, signer = observer_fixture._fixture(  # noqa: SLF001
        marker
    )
    schedule, verification = _exact_schedule(namespace, context_index=0)
    session_external_id = _id("real-owned-session")
    captured = {}
    wrapped = owned.run_v075_k7_root_cap_owned_partial_v1(
        repository_root=REPOSITORY_ROOT,
        namespace=namespace,
        schedule=schedule,
        schedule_verification=verification,
        authority=authorization,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=session_external_id,
        evidence_sink=captured.update,
    )
    portable_bundle = portable_evidence.freeze_v075_portable_occurrence_evidence_bundle_v2(
        evidence_roots=captured
    )
    replay = _real_request_replay(
        signer_registry=namespace.signer_registry,
        occurrence_id=schedule.occurrence.occurrence_id,
        schedule_id=schedule.schedule_id,
        session_external_id=session_external_id,
        opaque_environment_commitment_id=(
            namespace.environment_commitment.commitment_id
        ),
    )
    authority = business._issue_private_taint_authority(  # noqa: SLF001
        request_replay=replay,
        secret_document={
            "secret_material_id": replay.request.sealed_secret_commitment_id,
            "generation_seed_hex": (b"real-private-seed-pattern").hex(),
            "private_salt_hex": (b"real-private-salt-pattern").hex(),
        },
        key_document={
            "registered_signer_registry_id": namespace.signer_registry.registry_id,
            "registered_public_key_id": (
                namespace.signer_registry.observer_evidence_key.key_id
            ),
            "prime_p_hex": (b"real-private-prime-pattern").hex(),
            "prime_q_hex": (b"real-private-second-prime").hex(),
            "private_exponent_hex": (b"real-private-exponent").hex(),
        },
    )
    bundle = business._freeze_bundle(  # noqa: SLF001
        request_replay=replay,
        wrapped=wrapped,
        portable_bundle=portable_bundle,
        expected_session_public_id=(
            captured["controlled_journal_closure"].batch_closure.session_public_id
        ),
        private_taint_authority=authority,
    )
    return replay, authority, bundle


def test_real_portable_bundle_and_exact_request_replay_integrate(
    real_portable_business_bundle,
) -> None:
    replay, authority, bundle = real_portable_business_bundle
    verified = business.verify_v075_k7_child_business_bundle_bytes_v1(
        raw=bundle.canonical_bytes,
        expected_request_replay=replay,
        private_taint_authority=authority,
    )
    assert verified.bundle_id == bundle.bundle_id

    changed = bundle.to_document()
    portable_document = deepcopy(changed["portable_evidence_bundle"])
    target = next(
        record
        for record in portable_document["artifact_records"]
        if record["role"] == "MULTIROUND_RESULT"
    )
    target["semantic_artifact_id"] = _id("mutated-real-semantic-id")
    attacked_portable_raw = _rehash_complete_bundle_wrapper(portable_document)
    attacked_portable = loads_canonical_json(attacked_portable_raw)
    changed["portable_evidence_bundle"] = attacked_portable
    changed["portable_evidence_bundle_id"] = attacked_portable["bundle_id"]
    changed["portable_evidence_bundle_sha256"] = hashlib.sha256(
        attacked_portable_raw
    ).hexdigest()
    with pytest.raises(business.V075K7ChildBusinessBundleV1Error):
        business.verify_v075_k7_child_business_bundle_bytes_v1(
            raw=_rehash(changed),
            expected_request_replay=replay,
            private_taint_authority=authority,
        )


def test_naked_or_cross_request_taint_authority_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, authority, bundle = _substrate(monkeypatch)
    with pytest.raises(business.V075K7ChildBusinessBundleV1Error):
        business.verify_v075_k7_child_business_bundle_bytes_v1(
            raw=bundle.canonical_bytes,
            expected_request_replay=replay,
            private_taint_authority=(b"attacker-selected-pattern",),  # type: ignore[arg-type]
        )

    crossed_request = _Request()
    crossed_request.request_id = _id("crossed-taint-request")
    crossed_replay = _Replay(crossed_request)
    with pytest.raises(business.V075K7ChildBusinessBundleV1Error):
        authority._scan(  # noqa: SLF001
            raw=bundle.canonical_bytes,
            request_replay=crossed_replay,
        )


def test_private_taint_authority_has_no_exportable_or_mutable_secret_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _request, replay, _portable, _wrapped, authority, _bundle = _substrate(monkeypatch)
    assert "REDACTED" in repr(authority)
    assert not hasattr(authority, "_patterns")
    with pytest.raises(TypeError, match="serialization is forbidden"):
        authority.__reduce__()
    with pytest.raises(TypeError, match="serialization is forbidden"):
        pickle.dumps(authority)
    with pytest.raises(TypeError):
        asdict(authority)  # type: ignore[arg-type]
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(authority, "_patterns", (b"attacker-choice",))
    with pytest.raises(
        business.V075K7ChildBusinessBundleV1Error,
        match="known private material",
    ):
        authority._scan(  # noqa: SLF001
            raw=b'"leak":"known-private-seed-value"',
            request_replay=replay,
        )


def test_signer_and_taint_source_share_one_secure_key_read(monkeypatch) -> None:
    source = inspect.getsource(
        business.execute_v075_k7_child_business_bundle_from_sealed_descriptors_v1
    )
    assert source.count("_load_k7_signer_and_key_document_once") == 1
    helper = inspect.getsource(business._load_k7_signer_and_key_document_once)  # noqa: SLF001
    assert helper.count("_secure_read_private_key") == 1
    assert "load_v075_k7_subprocess_free_observer_evidence_signer_v1" not in source
