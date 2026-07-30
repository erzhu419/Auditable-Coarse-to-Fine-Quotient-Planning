from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import (
    v075_signer_owning_complete_observer_lifecycle_ipc_v1 as ipc,
)
from tests.test_v075_production_private_signer_runtime_v1 import (
    REPOSITORY_ROOT,
    _key_document,
    _registry,
    _write_private_key,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-complete-lifecycle-stage-b-test:v1"
        + b"\x00"
        + label.encode()
    ).hexdigest()


def _secret(marker: str) -> tuple[bytes, str]:
    raw = ipc._secret_raw_for_testing(  # noqa: SLF001
        generation_seed=hashlib.sha512(
            f"{marker}-generation".encode()
        ).digest(),
        private_salt=hashlib.sha512(f"{marker}-salt".encode()).digest(),
    )
    _generated, _salt, commitment = ipc._load_secret(raw)  # noqa: SLF001
    return raw, commitment.commitment_id


def _request(profile, marker: str, commitment_id: str):
    return ipc.freeze_v075_complete_observer_lifecycle_request_v1(
        profile=profile,
        request_nonce=_id(f"{marker}-nonce"),
        occurrence_id=_id(f"{marker}-occurrence"),
        session_external_id=_id(f"{marker}-session"),
        opaque_environment_commitment_id=commitment_id,
        signer_registry=_registry(),
    )


def _execute(
    *,
    profile,
    request,
    secret_raw: bytes,
    private_root: Path,
    key_path: Path,
    service=None,
):
    descriptor = ipc._stage_secret_for_testing(secret_raw)  # noqa: SLF001
    try:
        return ipc.execute_v075_complete_observer_lifecycle_v1(
            service=(
                service
                if service is not None
                else ipc.start_v075_complete_observer_lifecycle_service_v1(
                    profile=profile
                )
            ),
            request_bytes=request.canonical_bytes,
            repository_root=REPOSITORY_ROOT.resolve(),
            signer_private_root=private_root,
            signer_private_key_path=key_path,
            sealed_secret_fd=descriptor,
        )
    finally:
        os.close(descriptor)


def _rehash_result(document: dict[str, Any]) -> bytes:
    payload = {
        key: value for key, value in document.items() if key != "result_id"
    }
    document["result_id"] = ipc._hash("result", payload)  # noqa: SLF001
    return canonical_json_bytes(document)


def _rehash_nested(
    document: dict[str, Any],
    *,
    key: str,
    role: str,
    id_key: str,
) -> None:
    payload = {
        name: value
        for name, value in document[key].items()
        if name != id_key
    }
    document[key][id_key] = ipc._hash(role, payload)  # noqa: SLF001
    document[id_key] = document[key][id_key]


def _rehash_journal(document: dict[str, Any]) -> None:
    journal = document["journal"]
    prior = hashlib.sha256(
        b"acfqp:v075-complete-observer-lifecycle-journal-initial:v1"
    ).hexdigest()
    for entry in journal["entries"]:
        entry["prior_entry_id"] = prior
        payload = {
            key: value
            for key, value in entry.items()
            if key != "journal_entry_id"
        }
        entry["journal_entry_id"] = ipc._hash(  # noqa: SLF001
            "journal_entry",
            payload,
        )
        prior = entry["journal_entry_id"]
    journal["head_id"] = prior
    journal["entry_count"] = len(journal["entries"])
    payload = {
        key: value
        for key, value in journal.items()
        if key != "journal_id"
    }
    journal["journal_id"] = ipc._hash("journal", payload)  # noqa: SLF001
    document["journal_id"] = journal["journal_id"]


def _rehash_complete_child(document: dict[str, Any]) -> None:
    child = document["child_result"]
    child_payload = {
        key: value for key, value in child.items() if key != "child_result_id"
    }
    child["child_result_id"] = ipc._hash(  # noqa: SLF001
        "child_result",
        child_payload,
    )
    document["child_result_id"] = child["child_result_id"]
    document["supervisor"]["child_result_id"] = child["child_result_id"]
    _rehash_nested(
        document,
        key="supervisor",
        role="supervisor",
        id_key="supervisor_id",
    )
    child_raw = canonical_json_bytes(child)
    child_entry = document["journal"]["entries"][1]
    child_entry["message_id"] = child["child_result_id"]
    child_entry["payload_sha256"] = hashlib.sha256(child_raw).hexdigest()
    child_entry["payload_byte_count"] = len(child_raw)
    _rehash_journal(document)


@pytest.fixture(scope="module")
def profile():
    return ipc.freeze_v075_complete_observer_lifecycle_profile_v1(
        timeout_milliseconds=15_000
    )


@pytest.fixture(scope="module")
def honest(profile):
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v075-stage-b-test-",
        dir="/tmp",
    ) as directory:
        private_document = _key_document(_registry())
        private_root, key_path = _write_private_key(
            Path(directory),
            private_document,
        )
        secret_raw, commitment_id = _secret("honest")
        request = _request(profile, "honest", commitment_id)
        service = ipc.start_v075_complete_observer_lifecycle_service_v1(
            profile=profile
        )
        result = _execute(
            profile=profile,
            request=request,
            secret_raw=secret_raw,
            private_root=private_root,
            key_path=key_path,
            service=service,
        )
        replay = ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1(
            raw=result.canonical_bytes,
            request_bytes=request.canonical_bytes,
            profile=profile,
        )
        duplicate = _execute(
            profile=profile,
            request=request,
            secret_raw=secret_raw,
            private_root=private_root,
            key_path=key_path,
            service=service,
        )
        yield {
            "private_document": private_document,
            "private_root": private_root,
            "key_path": key_path,
            "secret_raw": secret_raw,
            "request": request,
            "result": result,
            "replay": replay,
            "duplicate": duplicate,
        }


def test_honest_child_owns_complete_lifecycle_and_public_replay(
    profile,
    honest,
) -> None:
    result = honest["result"]
    document = result.to_document()
    child = document["child_result"]
    assert result.terminal_code == ipc.COMPLETE_TERMINAL_CODE
    assert honest["replay"].result_id == result.result_id
    assert child["lifecycle_status"] == (
        "OPEN_OBSERVE_APPEND_CLOSE_PRIVATE_REPLAY_B3_COMPLETE"
    )
    assert child["child_work"]["observer_session_open_calls"] == 1
    assert child["child_work"]["batch_observe_calls"] == 2
    assert child["child_work"]["journal_append_calls"] == 2
    assert child["child_work"]["batch_closure_calls"] == 1
    assert child["child_work"]["private_replay_calls"] == 1
    assert child["child_work"]["b3_sign_calls"] == 1
    assert child["child_work"]["old_closure_upgrade_calls"] == 0
    assert child["child_work"]["old_b3_upgrade_calls"] == 0
    assert document["process"]["launched"] is True
    assert document["process"]["leader_reaped"] is True
    assert document["supervisor"]["local_process_attestation_only"] is True
    assert document["supervisor"]["cryptographic_process_provenance"] is False
    assert document["supervisor"]["os_sandbox_claimed"] is False
    assert document["public_verifier_proves_public_bytes_only"] is True
    assert document["public_verifier_private_replay_performed"] is False
    assert document["journal"]["entry_count"] == 2
    assert document["journal"]["entries"][1]["message_kind"] == (
        "COMPLETE_LIFECYCLE_CONSTRUCTION_RESULT"
    )
    for key in ipc._locks():  # noqa: SLF001
        assert document[key] is False


def test_request_rejects_all_posthoc_and_private_input_channels(
    profile,
    honest,
) -> None:
    parameters = inspect.signature(
        ipc.freeze_v075_complete_observer_lifecycle_request_v1
    ).parameters
    for forbidden in (
        "observer_signer",
        "private_verification",
        "private_material",
        "session",
        "closure",
        "b3",
        "observation_result",
        "result",
    ):
        assert forbidden not in parameters
    verifier_parameters = inspect.signature(
        ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1
    ).parameters
    assert tuple(verifier_parameters) == ("raw", "request_bytes", "profile")

    request = honest["request"]
    for injected_key in (
        "observer_signer",
        "source_private_replay_verification",
        "signed_batch_journal_closure",
        "b3_attestation",
        "observation_result",
    ):
        attacked = request.to_document()
        attacked[injected_key] = {"forbidden": True}
        with pytest.raises(
            ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
        ):
            ipc.verify_v075_complete_observer_lifecycle_request_bytes_v1(
                canonical_json_bytes(attacked)
            )


def test_secret_signer_and_nonce_fail_closed(profile, honest) -> None:
    private_root = honest["private_root"]
    key_path = honest["key_path"]
    expected_raw, expected_commitment = _secret("expected-secret")
    wrong_raw, _wrong_commitment = _secret("wrong-secret")
    request = _request(profile, "wrong-secret", expected_commitment)
    mismatch = _execute(
        profile=profile,
        request=request,
        secret_raw=wrong_raw,
        private_root=private_root,
        key_path=key_path,
    )
    assert mismatch.terminal_code == "SECRET_COMMITMENT_MISMATCH"
    ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1(
        raw=mismatch.canonical_bytes,
        request_bytes=request.canonical_bytes,
        profile=profile,
    )
    assert mismatch.to_document()["child_result"]["b3_attestation"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "SECRET_COMMITMENT_MISMATCH",
    }

    with tempfile.TemporaryDirectory(
        prefix="acfqp-v075-stage-b-wrong-key-",
        dir="/tmp",
    ) as directory:
        key_document = _key_document(_registry())
        key_document["registered_public_key_id"] = "0" * 64
        wrong_root, wrong_key = _write_private_key(
            Path(directory),
            key_document,
        )
        signer_request = _request(
            profile,
            "wrong-signer",
            expected_commitment,
        )
        signer_failure = _execute(
            profile=profile,
            request=signer_request,
            secret_raw=expected_raw,
            private_root=wrong_root,
            key_path=wrong_key,
        )
    assert signer_failure.terminal_code == "SIGNER_LOAD_FAILED"
    assert signer_failure.to_document()["journal"]["entries"][1][
        "message_kind"
    ] == "TYPED_LIFECYCLE_CONSTRUCTION_FAILURE"
    ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1(
        raw=signer_failure.canonical_bytes,
        request_bytes=signer_request.canonical_bytes,
        profile=profile,
    )
    assert signer_failure.to_document()["child_result"]["child_work"][
        "private_replay_calls"
    ] == 0

    duplicate = honest["duplicate"].to_document()
    assert duplicate["terminal_code"] == "NONCE_REPLAY_REJECTED"
    assert duplicate["process"]["launched"] is False
    assert duplicate["work"]["process_launches"] == 0
    assert duplicate["journal"]["entry_count"] == 1
    ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1(
        raw=honest["duplicate"].canonical_bytes,
        request_bytes=honest["request"].canonical_bytes,
        profile=profile,
    )


def test_crash_timeout_and_invalid_child_are_typed(
    profile,
    honest,
    monkeypatch,
) -> None:
    secret_raw, commitment_id = _secret("transport")
    private_root = honest["private_root"]
    key_path = honest["key_path"]

    def crash_argv(**_kwargs):
        return [
            sys.executable,
            "-I",
            "-S",
            "-c",
            "import os; os._exit(17)",
        ]

    with monkeypatch.context() as patch:
        patch.setattr(ipc, "_child_argv", crash_argv)
        crash_request = _request(profile, "crash", commitment_id)
        crashed = _execute(
            profile=profile,
            request=crash_request,
            secret_raw=secret_raw,
            private_root=private_root,
            key_path=key_path,
        )
    assert crashed.terminal_code == "CHILD_CRASH"
    assert crashed.to_document()["work"]["crash_events"] == 1
    ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1(
        raw=crashed.canonical_bytes,
        request_bytes=crash_request.canonical_bytes,
        profile=profile,
    )

    with monkeypatch.context() as patch:
        patch.setattr(
            ipc.stage_a,
            "_exchange",
            lambda *_args, **_kwargs: (None, b"", None, "CHILD_TIMEOUT"),
        )
        timeout_request = _request(profile, "timeout", commitment_id)
        timed_out = _execute(
            profile=profile,
            request=timeout_request,
            secret_raw=secret_raw,
            private_root=private_root,
            key_path=key_path,
        )
    assert timed_out.terminal_code == "CHILD_TIMEOUT"
    assert timed_out.to_document()["work"]["timeout_events"] == 1
    ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1(
        raw=timed_out.canonical_bytes,
        request_bytes=timeout_request.canonical_bytes,
        profile=profile,
    )

    with monkeypatch.context() as patch:
        patch.setattr(
            ipc.stage_a,
            "_exchange",
            lambda *_args, **_kwargs: (b"{}", b"", 0, None),
        )
        invalid_request = _request(profile, "invalid-child", commitment_id)
        invalid = _execute(
            profile=profile,
            request=invalid_request,
            secret_raw=secret_raw,
            private_root=private_root,
            key_path=key_path,
        )
    invalid_document = invalid.to_document()
    assert invalid.terminal_code == "CHILD_RESULT_VALIDATION_FAILED"
    assert invalid_document["journal"]["entries"][1][
        "message_kind"
    ] == "UNTYPED_INVALID_CHILD_RESULT"
    assert invalid_document["child_result"] == {
        "kind": "NOT_APPLICABLE",
        "reason": "NO_VALID_CHILD_RESULT",
    }
    ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1(
        raw=invalid.canonical_bytes,
        request_bytes=invalid_request.canonical_bytes,
        profile=profile,
    )


@pytest.mark.parametrize(
    "field",
    (
        "observer_session_public_id",
        "signed_batch_journal_closure_id",
        "b3_attestation_id",
    ),
)
def test_session_closure_and_b3_transplants_fail_after_rehash(
    honest,
    field,
) -> None:
    attacked = honest["result"].to_document()
    attacked[field] = _id(f"foreign-{field}")
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc.V075CompleteObserverLifecycleIPCResultV1(
            _rehash_result(attacked)
        )


def test_outer_fixture_id_transplant_fails_after_full_rehash(
    profile,
    honest,
) -> None:
    attacked = honest["result"].to_document()
    attacked["child_result"]["fixture_id"] = _id("foreign-fixture")
    _rehash_complete_child(attacked)
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1(
            raw=_rehash_result(attacked),
            request_bytes=honest["request"].canonical_bytes,
            profile=profile,
        )


def test_validly_signed_unregistered_draw_caps_fail_public_replay(
    honest,
) -> None:
    request = honest["request"].to_document()
    generated, salt, commitment = ipc._load_secret(  # noqa: SLF001
        honest["secret_raw"]
    )
    registry = _registry()
    signer = (
        ipc.signer_runtime.load_v075_production_observer_evidence_signer_v1(
            repository_root=REPOSITORY_ROOT.resolve(),
            private_root=honest["private_root"],
            private_key_path=honest["key_path"],
            signer_registry=registry,
        )
    )
    base = ipc._fixture_base(  # noqa: SLF001
        commitment=commitment,
        signer_registry=registry,
    )
    private_reveal = (
        ipc.reveal.issue_v075_reveal_verified_private_attestation_v2(
            anchor=base.anchor,
            commitment=base.commitment,
            generated_environment=generated,
            secret_salt=salt,
            signer_registry=registry,
            observer_signer=signer,
        )
    )
    authorization = ipc._authorization(  # noqa: SLF001
        base=base,
        private_reveal=private_reveal,
    )
    binding = ipc.observer._require_exact_v2_binding(  # noqa: SLF001
        authority=authorization,
        namespace=base.namespace,
    )
    streams = ipc._root_streams(base.namespace)  # noqa: SLF001
    streams_by_arm = {item.arm: item for item in streams.streams}
    session = ipc.observer._open_private_observer_from_verified_gate_v2(  # noqa: SLF001
        authority=authorization,
        namespace=base.namespace,
        binding=binding,
        private_salt=salt,
        private_environment=generated.secret_laws_for_commitment(),
        observer_signer=signer,
        session_external_id=request["session_external_id"],
    )
    attacked_plan = tuple(
        {
            **plan,
            "accepted_draw_cap": plan["accepted_draw_cap"] + 10,
        }
        for plan in ipc._REGISTERED_BATCH_PLAN  # noqa: SLF001
    )
    for plan in attacked_plan:
        session.observe_batch_v2(
            occurrence_id=request["occurrence_id"],
            stream_identity=streams_by_arm[plan["arm"]],
            accepted_draw_start=plan["accepted_draw_start"],
            accepted_draw_count=plan["accepted_draw_count"],
            accepted_draw_cap=plan["accepted_draw_cap"],
        )
    closure = session.close_batch_v2()
    used_streams = tuple(
        streams_by_arm[plan["arm"]] for plan in attacked_plan
    )
    attestation = (
        ipc.b3.freeze_v075_observer_signed_private_replay_attestation_v2(
            authority=authorization,
            namespace=base.namespace,
            closure=closure,
            authority_binding=binding,
            used_stream_identities=used_streams,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
        )
    )
    attacked_child = ipc._complete_child_result(  # noqa: SLF001
        request=request,
        base=base,
        private_reveal=private_reveal,
        authorization=authorization,
        binding=binding,
        streams=streams,
        closure=closure,
        attestation=attestation,
        work=honest["result"].to_document()["child_result"]["child_work"],
    )
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc._validate_child_result(  # noqa: SLF001
            attacked_child,
            request=request,
        )


def test_strict_schema_typed_null_and_current_identity_rehash(
    profile,
    honest,
) -> None:
    request = honest["request"].to_document()
    request["schema_version"] = "9.9.9"
    payload = {
        key: value for key, value in request.items() if key != "request_id"
    }
    request["request_id"] = ipc._hash("request", payload)  # noqa: SLF001
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc.verify_v075_complete_observer_lifecycle_request_bytes_v1(
            canonical_json_bytes(request)
        )

    no_child = honest["duplicate"].to_document()
    no_child["child_result"]["hidden"] = True
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc.V075CompleteObserverLifecycleIPCResultV1(
            _rehash_result(no_child)
        )

    attacked = honest["result"].to_document()
    attacked["supervisor"]["hidden"] = True
    _rehash_nested(
        attacked,
        key="supervisor",
        role="supervisor",
        id_key="supervisor_id",
    )
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc.V075CompleteObserverLifecycleIPCResultV1(
            _rehash_result(attacked)
        )

    original = profile._program_id  # noqa: SLF001
    object.__setattr__(profile, "_program_id", _id("stale-program"))
    try:
        with pytest.raises(
            ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
        ):
            profile.to_document()
    finally:
        object.__setattr__(profile, "_program_id", original)
    profile.to_document()


@pytest.mark.parametrize(
    ("field", "nested"),
    (
        ("context_index", False),
        ("root_action_index", False),
        ("support_epoch_index", False),
        ("accepted_draw_start", True),
        ("accepted_draw_count", True),
        ("accepted_draw_cap", True),
    ),
)
def test_request_registered_integer_fields_reject_json_booleans(
    honest,
    field,
    nested,
) -> None:
    request = honest["request"].to_document()
    if field in {
        "accepted_draw_start",
        "accepted_draw_count",
        "accepted_draw_cap",
    }:
        request["batch_plan"][0][field] = nested
    else:
        request[field] = nested
    payload = {
        key: value for key, value in request.items() if key != "request_id"
    }
    request["request_id"] = ipc._hash("request", payload)  # noqa: SLF001
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc.verify_v075_complete_observer_lifecycle_request_bytes_v1(
            canonical_json_bytes(request)
        )


def test_failed_child_status_and_lifecycle_prefix_are_exact(honest) -> None:
    request = honest["request"].to_document()
    impossible_prefix = ipc._lifecycle_work(  # noqa: SLF001
        secret_verified=1,
        signer_load_attempts=0,
        signer_load_successes=0,
        reveal_signatures=0,
        session_open_calls=0,
        batch_observe_calls=0,
        accepted_draws=0,
        journal_append_calls=0,
        closure_calls=0,
        private_replay_calls=0,
        b3_sign_calls=0,
        public_replay_calls=0,
    )
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc._validate_child_result(  # noqa: SLF001
            ipc._child_failure(  # noqa: SLF001
                request=request,
                code="LIFECYCLE_EXECUTION_FAILED",
                work=impossible_prefix,
            ),
            request=request,
        )

    exact_signer_failure = ipc._lifecycle_work(  # noqa: SLF001
        secret_verified=1,
        signer_load_attempts=1,
        signer_load_successes=0,
        reveal_signatures=0,
        session_open_calls=0,
        batch_observe_calls=0,
        accepted_draws=0,
        journal_append_calls=0,
        closure_calls=0,
        private_replay_calls=0,
        b3_sign_calls=0,
        public_replay_calls=0,
    )
    failed = ipc._load(  # noqa: SLF001
        ipc._child_failure(  # noqa: SLF001
            request=request,
            code="SIGNER_LOAD_FAILED",
            work=exact_signer_failure,
        ),
        label="test signer failure",
        cap=ipc.MAX_CHILD_RESULT_BYTES,
    )
    failed["lifecycle_status"] = "FORGED_FAILURE_STATUS"
    child_payload = {
        key: value
        for key, value in failed.items()
        if key != "child_result_id"
    }
    failed["child_result_id"] = ipc._hash(  # noqa: SLF001
        "child_result",
        child_payload,
    )
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc._validate_child_result(  # noqa: SLF001
            canonical_json_bytes(failed),
            request=request,
        )


def test_work_journal_and_private_serialization_attacks_fail(
    profile,
    honest,
) -> None:
    attacked = honest["result"].to_document()
    attacked["work"]["source_archive_staged_bytes"] += 1
    _rehash_nested(
        attacked,
        key="work",
        role="work",
        id_key="work_id",
    )
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc.verify_v075_complete_observer_lifecycle_result_bytes_v1(
            raw=_rehash_result(attacked),
            request_bytes=honest["request"].canonical_bytes,
            profile=profile,
        )

    attacked = honest["result"].to_document()
    attacked["journal"]["entries"][0]["payload_sha256"] = _id(
        "foreign-request-payload"
    )
    _rehash_journal(attacked)
    with pytest.raises(
        ipc.V075SignerOwningCompleteLifecycleV1InvariantViolation
    ):
        ipc.V075CompleteObserverLifecycleIPCResultV1(
            _rehash_result(attacked)
        )

    serialized = honest["result"].canonical_bytes.decode("utf-8")
    secret_document = ipc._load(  # noqa: SLF001
        honest["secret_raw"],
        label="test secret",
        cap=ipc.MAX_SECRET_BYTES,
    )
    assert secret_document["generation_seed_hex"] not in serialized
    assert secret_document["private_salt_hex"] not in serialized
    assert "private_exponent_hex" not in serialized
    assert str(honest["private_root"]) not in serialized
    assert str(honest["key_path"]) not in serialized
