from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import textwrap
import time

import pytest

from acfqp import v075_public_replay_occurrence_ipc_v2 as ipc
from tests.test_v075_portable_occurrence_evidence_bundle_v2 import (
    _build_portable_closed_bundle,
)


@pytest.fixture(scope="module")
def portable_bundle_bytes() -> bytes:
    return _build_portable_closed_bundle()[2].canonical_bytes


def _profile(
    raw: bytes,
    *,
    timeout: int = 600,
) -> ipc.V075PublicReplayOccurrenceIPCProfileV2:
    return ipc.freeze_v075_public_replay_occurrence_ipc_profile_v2(
        portable_bundle_bytes=raw,
        process_timeout_seconds=timeout,
    )


@pytest.fixture(scope="module")
def honest_replay(portable_bundle_bytes):
    profile = _profile(portable_bundle_bytes)
    result = ipc.execute_v075_public_replay_occurrence_ipc_v2(
        profile=profile,
        portable_bundle_bytes=portable_bundle_bytes,
    )
    return profile, result


def _attack_script(
    tmp_path: Path,
    *,
    body: str,
) -> Path:
    path = tmp_path / "attack_child.py"
    path.write_text(
        textwrap.dedent(
            f"""
            import sys
            import time

            WIDTH = 8

            def read_frame():
                header = sys.stdin.buffer.read(WIDTH)
                if len(header) != WIDTH:
                    raise SystemExit(91)
                size = int(header.decode("ascii"), 16)
                raw = sys.stdin.buffer.read(size)
                if len(raw) != size:
                    raise SystemExit(92)
                return raw

            def write_frame(raw):
                header = f"{{len(raw):0{{WIDTH}}x}}".encode("ascii")
                sys.stdout.buffer.write(header + raw)
                sys.stdout.buffer.flush()

            read_frame()
            read_frame()
            if sys.stdin.buffer.read(1) != b"":
                raise SystemExit(93)
            {body}
            """
        ),
        encoding="utf-8",
    )
    return path


def _replace_child(
    monkeypatch: pytest.MonkeyPatch,
    path: Path,
) -> None:
    monkeypatch.setattr(
        ipc,
        "_child_argv",
        lambda _registration: [sys.executable, "-I", str(path)],
    )


def _expected_child_bytes(
    raw: bytes,
    profile: ipc.V075PublicReplayOccurrenceIPCProfileV2,
) -> bytes:
    bundle = ipc._verify_bundle(raw)  # noqa: SLF001
    return ipc._expected_child_result(  # noqa: SLF001
        profile,
        bundle,
        raw,
    ).canonical_bytes


def _different(value):
    if type(value) is bool:
        return not value
    if type(value) is int:
        return value + 1
    if type(value) is str:
        if len(value) == 64 and all(
            character in "0123456789abcdef" for character in value
        ):
            replacement = "0" if value[0] != "0" else "1"
            return replacement + value[1:]
        return value + "_MUTATED"
    if type(value) is tuple:
        return tuple(reversed(value))
    raise AssertionError(f"unsupported mutation type: {type(value)!r}")


def _mutate_path(root, path) -> None:
    target = root
    for component in path[:-1]:
        target = (
            target[component]
            if type(component) is int
            else getattr(target, component)
        )
    field_name = path[-1]
    object.__setattr__(
        target,
        field_name,
        _different(getattr(target, field_name)),
    )


def test_isolated_public_replay_round_trip_is_typed_and_non_authorizing(
    portable_bundle_bytes,
    honest_replay,
) -> None:
    profile, result = honest_replay
    replayed = ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
        claimed=result,
        profile=profile,
        portable_bundle_bytes=portable_bundle_bytes,
    )
    document = replayed.to_document()
    child = replayed.child_verification.to_document()

    assert replayed is result
    assert result.profile_id == profile.profile_id
    assert result.portable_bundle_id == profile.portable_bundle_id
    assert child["terminal_code"] == (
        "PORTABLE_GRAPH_REPLAYED_CONSTRUCTION_ONLY"
    )
    assert child["raw_bundle_bytes_verified"] is True
    assert child["semantic_registry_replay_complete"] is False
    assert document["terminal_scope"] == "CONSTRUCTION_PUBLIC_REPLAY_ONLY"
    assert document["terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["official_execution_allowed"] is False
    assert document["production_authorizing"] is False
    assert document["fresh_heldout_accessed"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert len(result.journal.entries) == 3
    assert result.actual_work.process_launches == 1
    assert result.actual_work.parent_to_child_frames == 2
    assert result.actual_work.child_to_parent_frames == 1
    assert result.stderr_byte_count == 0
    program = profile.program_registration
    manifest_modules = {
        item.module_name for item in program.source_manifest.entries
    }
    assert {
        "acfqp.phase3e_ids",
        "acfqp.v075_public_graph_semantics_v1",
        "acfqp.v075_observer_signed_batch_control_authority_v2",
        "acfqp.v075_live_incremental_model_authority_v2",
        "acfqp.v075_live_dynamic_acquisition_authority_v2",
        "acfqp.v075_observer_signed_multiround_occurrence_runner_v2",
        "acfqp.v075_private_observer_boundary_v2",
    } <= manifest_modules
    assert program.interpreter_implementation == sys.implementation.name
    assert program.interpreter_cache_tag == sys.implementation.cache_tag
    assert program.interpreter_executable_byte_count > 0
    assert result.result_id == hashlib.sha256(
        ipc._DOMAINS["result"].encode("utf-8")  # noqa: SLF001
        + b"\x00"
        + ipc._canonical_bytes(result._payload())  # noqa: SLF001
    ).hexdigest()


def test_child_source_has_only_the_registered_public_bundle_boundary() -> None:
    path = Path(ipc.__file__).resolve()
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    forbidden_source_tokens = (
        "private_salt",
        "private_environment",
        "observer_signer",
        "secret_laws",
        "target_tape_namespace",
        "v075_private_observer_boundary",
        "v075_live_dynamic_acquisition_authority",
        "v075_live_incremental_model_authority",
        "v075_observer_signed_batch_control_authority",
        "v075_observer_signed_multiround_occurrence_runner",
    )
    assert not any(token in source for token in forbidden_source_tokens)
    assert not any(
        name.endswith(
            (
                "v075_private_observer_boundary_v2",
                "v075_live_dynamic_acquisition_authority_v2",
                "v075_live_incremental_model_authority_v2",
                "v075_observer_signed_batch_control_authority_v2",
                "v075_observer_signed_multiround_occurrence_runner_v2",
            )
        )
        for name in imports
    )
    assert ipc._VERIFIER_MODULE_NAME in source  # noqa: SLF001
    assert ipc._VERIFIER_CALLABLE in source  # noqa: SLF001


def test_parent_rejects_mutated_bundle_before_process_launch(
    portable_bundle_bytes,
    monkeypatch,
) -> None:
    profile = _profile(portable_bundle_bytes)
    attacked = bytearray(portable_bundle_bytes)
    attacked[-2] = ord("0") if attacked[-2] != ord("0") else ord("1")
    launched = False

    def forbidden_launch(_registration):
        nonlocal launched
        launched = True
        raise AssertionError("mutated bytes must fail before process launch")

    monkeypatch.setattr(ipc, "_child_argv", forbidden_launch)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="raw-byte replay failed|frozen replay profile",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=bytes(attacked),
        )
    assert launched is False


def test_stale_program_digest_is_rejected_before_process_launch(
    portable_bundle_bytes,
    monkeypatch,
) -> None:
    profile = _profile(portable_bundle_bytes)
    object.__setattr__(
        profile.program_registration,
        "ipc_module_sha256",
        "0" * 64,
    )
    launched = False

    def forbidden_launch(_registration):
        nonlocal launched
        launched = True
        raise AssertionError("stale program must fail before process launch")

    monkeypatch.setattr(ipc, "_child_argv", forbidden_launch)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="stale",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )
    assert launched is False


def test_changed_transitive_verifier_source_is_rejected_before_launch(
    portable_bundle_bytes,
    monkeypatch,
) -> None:
    profile = _profile(portable_bundle_bytes)
    original_identity = ipc._source_identity  # noqa: SLF001
    target = "v075_public_graph_semantics_v1.py"
    changed = False

    def changed_identity(path):
        nonlocal changed
        digest, byte_count = original_identity(path)
        if path.name == target:
            changed = True
            replacement = "0" if digest[0] != "0" else "1"
            digest = replacement + digest[1:]
        return digest, byte_count

    monkeypatch.setattr(ipc, "_source_identity", changed_identity)
    launched = False

    def forbidden_launch(_registration):
        nonlocal launched
        launched = True
        raise AssertionError("changed closure must fail before launch")

    monkeypatch.setattr(ipc, "_child_argv", forbidden_launch)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="stale|registration|manifest",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )
    assert changed is True
    assert launched is False


def test_status_only_child_output_is_rejected(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    profile = _profile(portable_bundle_bytes)
    child = _attack_script(
        tmp_path,
        body=(
            "write_frame("
            "b'{\"status\":\"PORTABLE_GRAPH_REPLAYED_CONSTRUCTION_ONLY\"}'"
            ")"
        ),
    )
    _replace_child(monkeypatch, child)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="independent host reconstruction",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_extra_child_frame_is_rejected(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    profile = _profile(portable_bundle_bytes)
    expected_hex = _expected_child_bytes(
        portable_bundle_bytes,
        profile,
    ).hex()
    child = _attack_script(
        tmp_path,
        body=(
            f"raw = bytes.fromhex({expected_hex!r}); "
            "write_frame(raw); write_frame(raw)"
        ),
    )
    _replace_child(monkeypatch, child)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="extra stdout",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_stderr_is_rejected_even_with_exact_typed_result(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    profile = _profile(portable_bundle_bytes)
    expected_hex = _expected_child_bytes(
        portable_bundle_bytes,
        profile,
    ).hex()
    child = _attack_script(
        tmp_path,
        body=(
            f"write_frame(bytes.fromhex({expected_hex!r})); "
            "sys.stderr.buffer.write(b'x'); sys.stderr.buffer.flush()"
        ),
    )
    _replace_child(monkeypatch, child)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="stderr",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_timeout_is_enforced_and_process_group_is_terminated(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    profile = _profile(portable_bundle_bytes, timeout=1)
    child = _attack_script(tmp_path, body="time.sleep(5)")
    _replace_child(monkeypatch, child)
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="timeout",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_large_bundle_write_shares_deadline_with_stalled_reader(
    portable_bundle_bytes,
    monkeypatch,
    tmp_path,
) -> None:
    assert len(portable_bundle_bytes) > 1024 * 1024
    profile = _profile(portable_bundle_bytes, timeout=1)
    verified = ipc._verify_bundle(portable_bundle_bytes)  # noqa: SLF001
    exact_profile = ipc._require_exact_profile(profile)  # noqa: SLF001
    monkeypatch.setattr(
        ipc,
        "_verify_bundle",
        lambda raw: verified
        if raw == portable_bundle_bytes
        else (_ for _ in ()).throw(AssertionError("unexpected bytes")),
    )
    monkeypatch.setattr(
        ipc,
        "_require_exact_profile",
        lambda claimed: exact_profile
        if claimed is profile
        else (_ for _ in ()).throw(AssertionError("unexpected profile")),
    )
    child = tmp_path / "stalled_reader.py"
    child.write_text(
        "import time\ntime.sleep(5)\n",
        encoding="utf-8",
    )
    _replace_child(monkeypatch, child)
    started = time.monotonic()
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="timeout",
    ):
        ipc.execute_v075_public_replay_occurrence_ipc_v2(
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )
    assert time.monotonic() - started < 3


def test_result_and_journal_transplants_fail_independent_verification(
    portable_bundle_bytes,
    honest_replay,
) -> None:
    profile, result = honest_replay
    copied = deepcopy(result)
    object.__setattr__(
        copied.actual_work,
        "parent_to_child_payload_bytes",
        copied.actual_work.parent_to_child_payload_bytes + 1,
    )
    with pytest.raises(
        ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
        match="independent verification",
    ):
        ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
            claimed=copied,
            profile=profile,
            portable_bundle_bytes=portable_bundle_bytes,
        )


def test_every_result_identity_journal_and_work_field_is_reconstructed(
    portable_bundle_bytes,
    honest_replay,
    monkeypatch,
) -> None:
    profile, result = honest_replay
    verified_bundle = ipc._verify_bundle(  # noqa: SLF001
        portable_bundle_bytes
    )
    monkeypatch.setattr(
        ipc,
        "_verify_bundle",
        lambda raw: verified_bundle
        if raw == portable_bundle_bytes
        else (_ for _ in ()).throw(AssertionError("unexpected bytes")),
    )
    paths = [
        ("profile_id",),
        ("occurrence_id",),
        ("portable_bundle_id",),
        ("stderr_sha256",),
        ("stderr_byte_count",),
        ("_result_id",),
        ("child_verification", "profile_id"),
        ("child_verification", "program_registration_id"),
        ("child_verification", "occurrence_id"),
        ("child_verification", "portable_bundle_id"),
        ("child_verification", "portable_bundle_sha256"),
        ("child_verification", "portable_bundle_byte_count"),
        ("child_verification", "artifact_count"),
        ("child_verification", "root_binding_count"),
        ("child_verification", "_child_result_id"),
        ("journal", "entries"),
        ("journal", "_journal_id"),
        ("actual_work", "process_launches"),
        ("actual_work", "parent_to_child_frames"),
        ("actual_work", "child_to_parent_frames"),
        ("actual_work", "parent_to_child_payload_bytes"),
        ("actual_work", "child_to_parent_payload_bytes"),
        ("actual_work", "framing_bytes"),
        ("actual_work", "protocol_checks"),
        ("actual_work", "raw_bundle_verifier_calls_parent"),
        ("actual_work", "raw_bundle_verifier_calls_child"),
        ("actual_work", "process_exit_code"),
        ("actual_work", "_work_id"),
    ]
    entry_fields = (
        "sequence_number",
        "direction",
        "message_kind",
        "message_id",
        "message_byte_count",
        "message_sha256",
        "previous_entry_id",
        "_entry_id",
    )
    paths.extend(
        ("journal", "entries", index, field_name)
        for index in range(3)
        for field_name in entry_fields
    )
    for path in paths:
        attacked = deepcopy(result)
        _mutate_path(attacked, path)
        with pytest.raises(
            ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation,
            match="independent verification",
        ):
            ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
                claimed=attacked,
                profile=profile,
                portable_bundle_bytes=portable_bundle_bytes,
            )


def test_profile_program_manifest_and_cached_ids_are_reconstructed(
    portable_bundle_bytes,
    honest_replay,
    monkeypatch,
) -> None:
    profile, result = honest_replay
    verified_bundle = ipc._verify_bundle(  # noqa: SLF001
        portable_bundle_bytes
    )
    monkeypatch.setattr(
        ipc,
        "_verify_bundle",
        lambda raw: verified_bundle
        if raw == portable_bundle_bytes
        else (_ for _ in ()).throw(AssertionError("unexpected bytes")),
    )
    paths = (
        ("occurrence_id",),
        ("portable_bundle_id",),
        ("portable_bundle_sha256",),
        ("portable_bundle_byte_count",),
        ("process_timeout_seconds",),
        ("_profile_id",),
        ("program_registration", "ipc_module_sha256"),
        ("program_registration", "verifier_module_sha256"),
        ("program_registration", "interpreter_implementation"),
        ("program_registration", "interpreter_version"),
        ("program_registration", "interpreter_cache_tag"),
        ("program_registration", "interpreter_executable_sha256"),
        ("program_registration", "interpreter_executable_byte_count"),
        ("program_registration", "_registration_id"),
        ("program_registration", "source_manifest", "_manifest_id"),
        (
            "program_registration",
            "source_manifest",
            "entries",
            0,
            "source_sha256",
        ),
        (
            "program_registration",
            "source_manifest",
            "entries",
            0,
            "source_byte_count",
        ),
    )
    for path in paths:
        attacked_profile = deepcopy(profile)
        _mutate_path(attacked_profile, path)
        with pytest.raises(
            ipc.V075PublicReplayOccurrenceIPCV2InvariantViolation
        ):
            ipc.verify_v075_public_replay_occurrence_ipc_result_v2(
                claimed=result,
                profile=attacked_profile,
                portable_bundle_bytes=portable_bundle_bytes,
            )


def test_production_entrypoint_and_all_module_locks_remain_closed() -> None:
    assert ipc.PROPOSED_CONTRACT_VERSION == "1.62.0"
    assert ipc.OFFICIAL_EXECUTION_ALLOWED is False
    assert ipc.PRODUCTION_AUTHORIZING is False
    assert ipc.FRESH_HELDOUT_ACCESS_ALLOWED is False
    assert ipc.SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED is False
    assert ipc.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert ipc.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert ipc.SEMANTIC_REGISTRY_REPLAY_COMPLETE is False
    with pytest.raises(ipc.V075PublicReplayProductionV2NotReady):
        ipc.open_v075_production_public_replay_occurrence_ipc_v2()
