from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v18 as domains_v18
from acfqp import construction_k7_h1_two_birth_portable_checkpoint_v1 as producer


HELPER = Path(__file__).with_name(
    "_two_birth_portable_checkpoint_subprocess.py"
)


def _run_real_helper(mode: str) -> dict[str, object]:
    repository = HELPER.parent.parent
    completed = subprocess.run(
        [
            "systemd-run",
            "--user",
            "--scope",
            "--collect",
            "-p",
            "Delegate=yes",
            "-p",
            "TasksMax=infinity",
            f"--working-directory={repository}",
            "env",
            f"PYTHONPATH={repository / 'src'}",
            sys.executable,
            os.fspath(HELPER),
            mode,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return json.loads(completed.stdout.splitlines()[-1])


def _recompute(
    document: dict[str, object], *, domain: str, id_field: str
) -> str:
    payload = dict(document)
    supplied = payload.pop(id_field)
    assert type(supplied) is str
    assert domains_v18.extension_content_id_v18(domain, payload) == supplied
    return supplied


def test_source_closure_is_frozen_with_retained_duplicate_witnesses() -> None:
    lease, document = producer._freeze_source_closure()  # noqa: SLF001
    try:
        assert document["freeze_phase"] == "BEFORE_RAW_TWO_BIRTH_BEGIN"
        assert document["journal_sequence"] == 1
        assert document["source_entry_count"] == 9
        assert len(lease.descriptors) == 18
        lease.revalidate()
        entries = document["source_entries"]
        assert len(entries) == 9
        assert len({item["role"] for item in entries}) == 9
        assert all(item["source_and_witness_same_inode"] for item in entries)
        assert all(item["source_descriptor_cloexec"] for item in entries)
        assert all(item["witness_descriptor_cloexec"] for item in entries)
        assert all(item["descriptor_numbers_serialized"] is False for item in entries)
        assert all(item["absolute_path_serialized"] is False for item in entries)
        for item in entries:
            raw = bytes.fromhex(item["source_bytes_hex"])
            assert len(raw) == item["byte_count"]
            assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        _recompute(
            dict(document),
            domain=(
                domains_v18.CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN
            ),
            id_field="two_birth_execution_source_closure_id",
        )
    finally:
        lease.close()
    assert lease.descriptors == set()


def test_resigned_forged_embedded_source_is_rejected() -> None:
    lease, source = producer._freeze_source_closure()  # noqa: SLF001
    try:
        forged = producer._thaw_json(source)  # noqa: SLF001
        forged["source_entries"][0]["source_bytes_hex"] = b"forged".hex()
        forged["source_entries"][0]["byte_count"] = len(b"forged")
        forged["source_entries"][0]["sha256"] = hashlib.sha256(
            b"forged"
        ).hexdigest()
        forged.pop("two_birth_execution_source_closure_id")
        forged["two_birth_execution_source_closure_id"] = (
            domains_v18.extension_content_id_v18(
                domains_v18.CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
                forged,
            )
        )
        with pytest.raises(
            producer.ConstructionK7H1TwoBirthPortableCheckpointV1Error,
            match="embedded source join",
        ):
            producer._validate_source_closure_document(forged)  # noqa: SLF001
    finally:
        lease.close()


def test_recursive_code_fingerprint_detects_same_bytecode_constant_change() -> None:
    def original() -> str:
        return "AAAA"

    tampered_code = original.__code__.replace(
        co_consts=tuple(
            "BBBB" if item == "AAAA" else item
            for item in original.__code__.co_consts
        )
    )
    tampered = types.FunctionType(tampered_code, original.__globals__)
    assert tampered.__code__.co_code == original.__code__.co_code
    assert hashlib.sha256(tampered.__code__.co_code).digest() == hashlib.sha256(
        original.__code__.co_code
    ).digest()
    original_documents = producer._callable_semantic_documents(  # noqa: SLF001
        original
    )
    tampered_documents = producer._callable_semantic_documents(  # noqa: SLF001
        tampered
    )
    assert original_documents[0] != tampered_documents[0]
    assert original_documents[3] != tampered_documents[3]
    assert original_documents[4] != tampered_documents[4]


def test_callable_fingerprint_binds_defaults_beyond_identical_code() -> None:
    def original(value: str = "AAAA") -> str:
        return value

    tampered = types.FunctionType(
        original.__code__,
        original.__globals__,
        argdefs=("BBBB",),
    )
    original_documents = producer._callable_semantic_documents(  # noqa: SLF001
        original
    )
    tampered_documents = producer._callable_semantic_documents(  # noqa: SLF001
        tampered
    )
    assert original_documents[0] == tampered_documents[0]
    assert original_documents[3] == tampered_documents[3]
    assert original_documents[1] != tampered_documents[1]
    assert original_documents[4] != tampered_documents[4]


def test_resigned_callable_constant_fingerprint_is_rejected() -> None:
    lease, source = producer._freeze_source_closure()  # noqa: SLF001
    try:
        forged = producer._thaw_json(source)  # noqa: SLF001
        binding = forged["callable_authority_bindings"][0]
        constants = binding["code_fingerprint_document"]["co_consts"]
        constants[0] = {"kind": "STR", "value": "same-bytecode-tamper"}
        binding["code_fingerprint_sha256"] = hashlib.sha256(
            producer._fingerprint_canonical_json_bytes(  # noqa: SLF001
                binding["code_fingerprint_document"]
            )
        ).hexdigest()
        binding["callable_semantic_fingerprint_sha256"] = hashlib.sha256(
            producer._fingerprint_canonical_json_bytes(  # noqa: SLF001
                {
                    "schema": "acfqp.python_callable_semantics.v1",
                    "code_fingerprint_document": binding[
                        "code_fingerprint_document"
                    ],
                    "defaults_fingerprint_document": binding[
                        "defaults_fingerprint_document"
                    ],
                    "kwdefaults_fingerprint_document": binding[
                        "kwdefaults_fingerprint_document"
                    ],
                }
            )
        ).hexdigest()
        forged.pop("two_birth_execution_source_closure_id")
        forged["two_birth_execution_source_closure_id"] = (
            domains_v18.extension_content_id_v18(
                domains_v18.CONSTRUCTION_K7_H1_TWO_BIRTH_EXECUTION_SOURCE_CLOSURE_V1_DOMAIN,
                forged,
            )
        )
        with pytest.raises(
            producer.ConstructionK7H1TwoBirthPortableCheckpointV1Error,
            match="callable authority manifest changed",
        ):
            producer._validate_source_closure_document(forged)  # noqa: SLF001
    finally:
        lease.close()


@pytest.mark.parametrize(
    ("module", "attribute"),
    (
        (
            producer.runtime_v1,
            "snapshot_bounded_nested_creator_two_birth_live_prefix_v1",
        ),
        (producer.domains_v18, "extension_content_id_v18"),
        (producer.ids_v1, "canonical_json_bytes"),
    ),
)
def test_external_callable_monkeypatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch, module: object, attribute: str
) -> None:
    monkeypatch.setattr(module, attribute, lambda *args, **kwargs: None)
    with pytest.raises(
        producer.ConstructionK7H1TwoBirthPortableCheckpointV1Error,
        match="callable authority changed",
    ):
        producer._validate_external_authorities()  # noqa: SLF001


def test_internal_credential_builder_monkeypatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(producer, "_credential_bundle", lambda **kwargs: {})
    with pytest.raises(
        producer.ConstructionK7H1TwoBirthPortableCheckpointV1Error,
        match="internal callable authority changed",
    ):
        producer._VALIDATE_INTERNAL_AUTHORITIES()  # noqa: SLF001


def test_graph_is_not_caller_mintable_or_copyable() -> None:
    graph = object.__new__(producer.TwoBirthPortableCheckpointGraphV1)
    with pytest.raises(
        producer.ConstructionK7H1TwoBirthPortableCheckpointV1Error
    ):
        copy.copy(graph)
    with pytest.raises(
        producer.ConstructionK7H1TwoBirthPortableCheckpointV1Error
    ):
        copy.deepcopy(graph)


@pytest.mark.parametrize("mode", (0o755, 0o700))
def test_journal_must_be_private_and_empty(tmp_path: Path, mode: int) -> None:
    journal = tmp_path / "journal"
    journal.mkdir(mode=mode)
    os.chmod(journal, mode)
    if mode == 0o700:
        (journal / "foreign").write_bytes(b"foreign")
    control_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        with pytest.raises(
            producer.ConstructionK7H1TwoBirthPortableCheckpointV1Error,
            match="private, and empty",
        ):
            producer.run_two_birth_portable_checkpoint_producer_v1(
                control_cgroup_fd=control_fd,
                journal_directory=journal,
            )
    finally:
        os.close(control_fd)


def test_authority_and_downstream_claims_remain_locked() -> None:
    assert producer.EXECUTION_SOURCE_CLOSURE_IMPLEMENTATION_PRESENT
    assert producer.NESTED_CREDENTIAL_OBSERVATION_BUNDLE_IMPLEMENTATION_PRESENT
    assert producer.PORTABLE_OBSERVATION_CHECKPOINT_IMPLEMENTATION_PRESENT
    assert producer.DURABLE_PORTABLE_OBSERVATION_GRAPH_IMPLEMENTATION_PRESENT
    assert producer.E5A_RUNTIME_LEASE_JOIN_PRESENT is False
    assert producer.EXACT_TWO_BIRTH_OS_TOPOLOGY_OBSERVED is False
    assert producer.PORTABLE_CHECKPOINT_AUTHORITY_PRESENT is False
    assert producer.TWO_BIRTH_PREFIX_AUTHORITY_PRESENT is False
    assert producer.FIVE_BIRTH_PROCESS_AUTHORITY_PRESENT is False
    assert producer.ACTUAL_OBSERVED_E3_V2_COMPLETION_PRESENT is False
    assert producer.E4_V2_COMPLETION_PRESENT is False
    assert producer.CURRENT_ACCESS_AUTHORITY_PRESENT is False
    assert producer.FORMAL_V7_AUTHORITY_PRESENT is False
    assert producer.OFFICIAL_EXECUTION_ALLOWED is False
    assert producer.OFFICIAL_SCALAR_COST is None
    assert producer.OFFICIAL_N_BREAK_EVEN is None
    assert producer.COUNTER_COMPLETENESS_GATE == "NOT_RUN"
    assert producer.WORKLOAD_ECONOMICS_GATE == "NOT_RUN"


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_checkpoint_graph_is_durable_then_v1_is_normally_closed() -> None:
    result = _run_real_helper("SUCCESS")
    assert result["success"] is True
    assert result["record_count"] == 3
    assert result["record_schemas"] == [
        "acfqp.k7_h1_two_birth_execution_source_closure.v1",
        "acfqp.k7_h1_nested_probe_credential_observation_bundle.v1",
        "acfqp.k7_h1_live_two_birth_prefix_checkpoint.v1",
    ]
    assert result["record_sequences"] == [1, 2, 3]
    assert len(set(result["record_ids"])) == 3
    assert result["source_entry_count"] == 9
    assert result["issuance_state"] == "PROBE_REAPED_SUPERVISOR_LIVE"
    assert result["runtime_state_at_root_commit"] == (
        "PROBE_REAPED_SUPERVISOR_LIVE"
    )
    assert result["expected_success_return_runtime_state"] == "CLOSED"
    assert result["producer_return_runtime_state"] == "CLOSED"
    assert result["shutdown_schema"] == (
        "acfqp.k7_h1_nested_creator_two_birth_raw_result.v1"
    )
    assert result["root_embeds_source"] is True
    assert result["root_embeds_credentials"] is True
    assert result["root_exact_topology"] is False
    assert result["root_authority"] is False
    assert result["root_e5a"] is False
    assert result["root_five_birth"] is False
    assert result["root_official"] is False
    assert result["root_counter_gate"] == "NOT_RUN"
    assert result["root_economics_gate"] == "NOT_RUN"
    assert result["final_population"] == 0
    assert result["direct_children"] == ""


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_forged_snapshot_and_resigned_credential_are_rejected() -> None:
    result = _run_real_helper("FORGED_SNAPSHOT_RESIGN")
    assert "outer birth evidence join changed" in result[
        "forged_snapshot_error"
    ]
    assert result["resigned_credential_id_present"] is True
    assert "credential observation bundle join changed" in result[
        "resigned_credential_error"
    ]


@pytest.mark.parametrize(
    "mode",
    (
        "SOURCE_CLOSURE_FROZEN",
        "RAW_BEGIN_RETURNED",
        "LIVE_SNAPSHOT_FROZEN",
        "SOURCE_RECORD_FILE_FSYNC",
        "CREDENTIAL_RECORD_FILE_FSYNC",
        "CHECKPOINT_RECORD_FILE_FSYNC",
        "CHECKPOINT_RECORD_DIRECTORY_FSYNC",
        "ROOT_DURABLE_COMMIT",
        "RUNTIME_CLOSED",
    ),
)
@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_NESTED_CREATOR") != "1",
    reason="requires a transient delegated systemd user scope",
)
def test_real_faults_emit_failure_only_after_complete_raw_cleanup(mode: str) -> None:
    result = _run_real_helper(mode)
    assert result["success"] is False
    assert result["failure_closure_returned"] is True
    closure = result["failure_closure"]
    assert closure["schema"] == (
        "acfqp.k7_h1_two_birth_protocol_failure_closure.v1"
    )
    assert closure["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert closure["terminal_code"] == "PROTOCOL_FAILURE"
    assert closure["cleanup"]["raw_cleanup_completely_closed"] is True
    assert closure["failure_closure_is_not_infeasibility"] is True
    assert closure["failure_closure_is_not_plan_certificate"] is True
    assert closure["e5a_runtime_lease_join_present"] is False
    assert closure["portable_checkpoint_authority_present"] is False
    assert closure["five_birth_process_authority_present"] is False
    assert closure["official_execution_allowed"] is False
    expected_prefix_count = {
        "SOURCE_CLOSURE_FROZEN": 0,
        "RAW_BEGIN_RETURNED": 0,
        "LIVE_SNAPSHOT_FROZEN": 0,
        "SOURCE_RECORD_FILE_FSYNC": 1,
        "CREDENTIAL_RECORD_FILE_FSYNC": 2,
        "CHECKPOINT_RECORD_FILE_FSYNC": 3,
        "CHECKPOINT_RECORD_DIRECTORY_FSYNC": 3,
        "ROOT_DURABLE_COMMIT": 3,
        "RUNTIME_CLOSED": 3,
    }[mode]
    assert result["record_count"] == expected_prefix_count + 1
    assert len(closure["journal_records_before_failure_closure"]) == (
        expected_prefix_count
    )
    assert closure["raw_begin_returned"] is (
        mode != "SOURCE_CLOSURE_FROZEN"
    )
    if mode == "SOURCE_CLOSURE_FROZEN":
        assert closure["cleanup"]["terminal_method"] == (
            "NO_HANDLE_RUNTIME_ALREADY_CLOSED"
        )
        assert closure["source_closure"]["schema"] == (
            "acfqp.k7_h1_two_birth_execution_source_closure.v1"
        )
        assert closure["source_closure"]["source_entry_count"] == 9
    elif mode == "RUNTIME_CLOSED":
        assert closure["cleanup"]["terminal_method"] == (
            "PUBLIC_NORMAL_CLOSE_ALREADY_COMMITTED"
        )
    else:
        assert closure["cleanup"]["terminal_method"] == "PUBLIC_ABORT"
    if mode in {
        "SOURCE_RECORD_FILE_FSYNC",
        "CREDENTIAL_RECORD_FILE_FSYNC",
        "CHECKPOINT_RECORD_FILE_FSYNC",
    }:
        assert closure["journal_records_before_failure_closure"][-1][
            "file_fsync_complete"
        ] is True
        assert closure["journal_records_before_failure_closure"][-1][
            "directory_fsync_complete"
        ] is False
    _recompute(
        closure,
        domain=(
            domains_v18.CONSTRUCTION_K7_H1_TWO_BIRTH_PROTOCOL_FAILURE_CLOSURE_V1_DOMAIN
        ),
        id_field="two_birth_protocol_failure_closure_id",
    )
    assert result["record_schemas"][-1] == closure["schema"]
    assert result["final_population"] == 0
    assert result["direct_children"] == ""
