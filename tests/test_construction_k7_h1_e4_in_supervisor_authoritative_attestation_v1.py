from __future__ import annotations

import copy
import errno
import hashlib
import os
from pathlib import Path
import pickle
import tempfile
import threading

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v10 as domains_v10
from acfqp import construction_k7_h1_domain_registry_extension_v11 as domains_v11
from acfqp import construction_k7_h1_domain_registry_extension_v12 as domains_v12
from acfqp import construction_k7_h1_domain_registry_extension_v13 as domains_v13
from acfqp import construction_k7_h1_e3_bound_output_ordinal_continuation_v1 as e4_v1
from acfqp import construction_k7_h1_e4_in_supervisor_authoritative_attestation_v1 as e5ba_v1
from acfqp import construction_k7_h1_exclusive_native_resource_broker_v1 as e3_v1
from acfqp.phase3e_ids import canonical_json_bytes


@pytest.fixture
def tmp_path() -> Path:
    with tempfile.TemporaryDirectory(prefix="acfqp-e5ba-test-", dir="/tmp") as root:
        yield Path(root)


def _id(label: str) -> str:
    return hashlib.sha256(f"e5ba-test:{label}".encode("utf-8")).hexdigest()


def _prepare(tmp_path: Path) -> e4_v1.H1E3BoundOutputContinuationContextV1:
    return e4_v1.prepare_h1_e3_bound_output_continuation_context_v1(
        output_parent_directory=tmp_path,
        caller_binding_id=_id("caller"),
        lifecycle_snapshot={
            "schema": "acfqp.test.e5ba.lifecycle_snapshot.nonformal.v1",
            "formal_authority_present": False,
        },
        lifecycle_program={
            "schema": "acfqp.test.e5ba.lifecycle_program.nonformal.v1",
            "formal_authority_present": False,
        },
        logical_occurrence_id=_id("occurrence"),
        route_attempt_id=_id("attempt"),
        read_bytes_base=31,
    )


def _unchecked_runtime_type_e3_completion_unit_seam(
    *,
    completion_id: str,
    session_nonce: str,
    context_id: str,
) -> e3_v1.H1ExclusiveBrokerCompletionV1:
    """Unit seam only, never evidence of E3 issuance or object ownership.

    The monkeypatched E4 authority in these focused tests validates call
    routing.  Upstream E3/E4 suites own their semantic-authority coverage.
    """

    document = {
        "schema": "acfqp.test.e5ba.exact_e3_unit_seam.v1",
        "h1_exclusive_broker_completion_id": completion_id,
        "session_nonce": session_nonce,
        "prebound_output_continuation_context_id": context_id,
        "authority_disposition": "BROKER_EXCLUSIVE_PRESENT",
        "h1_exclusive_broker_profile_id": (
            e3_v1.official_h1_exclusive_broker_profile_v1().profile_id
        ),
        "h1_exclusive_broker_source_manifest_id": (
            e3_v1.official_h1_exclusive_broker_source_manifest_v1().manifest_id
        ),
    }
    value = object.__new__(e3_v1.H1ExclusiveBrokerCompletionV1)
    object.__setattr__(value, "payload_bytes", canonical_json_bytes(document))
    object.__setattr__(value, "completion_id", completion_id)
    return value


def _successful_unit_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[
    e4_v1.H1E3BoundOutputContinuationContextV1,
    e3_v1.H1ExclusiveBrokerCompletionV1,
    e4_v1.H1E3BoundOutputCompletionV1,
    list[tuple[object, object, object]],
]:
    context = _prepare(tmp_path)
    context_document = e4_v1._verify_live_context(context, require_empty=True)  # noqa: SLF001
    completion_id = _id("e3-completion")
    session_nonce = _id("e3-session")
    e4_completion = e4_v1._run_admitted_output_program(  # noqa: SLF001
        context=context,
        context_document=context_document,
        e3_completion={
            "h1_exclusive_broker_completion_id": completion_id,
            "session_nonce": session_nonce,
        },
        fault=e4_v1.H1E4FaultInjectionV1.NONE,
    )
    assert type(e4_completion) is e4_v1.H1E3BoundOutputCompletionV1
    e3_completion = _unchecked_runtime_type_e3_completion_unit_seam(
        completion_id=completion_id,
        session_nonce=session_nonce,
        context_id=context.context_id,
    )
    calls: list[tuple[object, object, object]] = []

    def authoritative_verifier(*, completion, context, e3_completion) -> bool:
        calls.append((completion, context, e3_completion))
        return True

    monkeypatch.setattr(
        e4_v1,
        "verify_h1_e3_bound_output_completion_v1",
        authoritative_verifier,
    )
    return context, e3_completion, e4_completion, calls


def _issue(
    context: e4_v1.H1E3BoundOutputContinuationContextV1,
    e3_completion: e3_v1.H1ExclusiveBrokerCompletionV1,
    e4_completion: e4_v1.H1E3BoundOutputCompletionV1,
) -> e5ba_v1.H1E4InSupervisorAuthoritativeAttestationV1:
    return e5ba_v1.issue_h1_e4_in_supervisor_authoritative_attestation_v1(
        context=context,
        e3_completion=e3_completion,
        e4_completion=e4_completion,
    )


def test_v13_domains_are_additive_disjoint_and_domain_separated() -> None:
    assert len(domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V13) == 3
    assert len(domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_V13) == 3
    assert domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_V13.isdisjoint(
        domains_v10.K7_H1_DOMAIN_TAG_EXTENSION_V10
    )
    assert domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_V13.isdisjoint(
        domains_v11.K7_H1_DOMAIN_TAG_EXTENSION_V11
    )
    assert domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_V13.isdisjoint(
        domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12
    )
    payload = {"schema": "acfqp.test.e5ba.domain_separation.v1"}
    assert len(
        {
            domains_v13.extension_content_id_v13(domain, payload)
            for domain in domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_V13
        }
    ) == 3
    with pytest.raises(ValueError, match="absent"):
        domains_v13.extension_content_id_v13(
            domains_v11.CONSTRUCTION_K7_H1_E3_BOUND_OUTPUT_COMPLETION_V1_DOMAIN,
            payload,
        )


def test_profile_freezes_exact_authority_boundary_and_all_downstream_locks() -> None:
    document = e5ba_v1.official_h1_e4_in_supervisor_attestation_profile_v1().to_document()
    assert document["proposed_contract_version"] == "2.0.59-E-C-E5B-A"
    assert document["readiness"] == "E5B_PREREQUISITE_ONLY"
    assert document["authority_disposition"] == (
        "IN_SUPERVISOR_E4_AUTHORITATIVE_ATTESTATION_PRESENT"
    )
    assert document["exact_retained_context_required"] is True
    assert document["exact_e3_completion_runtime_type_required"] is True
    assert document["exact_e4_completion_runtime_type_required"] is True
    assert document["e3_completion_exact_object_identity_retained"] is False
    assert document["e4_completion_exact_object_identity_retained"] is False
    assert document["e4_authoritative_verifier_call_required"] is True
    assert document["same_process_and_preparer_thread_required"] is True
    assert document["authenticated_supervisor_binding_present"] is False
    assert document["eight_output_inode_identities_required"] is True
    assert document["guardian_may_call_e4_authoritative_verifier"] is False
    assert document["guardian_replay_substitutes_same_process_authority"] is False
    assert document["e5b_integrated_route_execution_present"] is False
    assert document["route_wide_actual_peak_authority_present"] is False
    assert document["route_wide_peak_authority_present"] is False
    assert document["production_output_leaf_authority_present"] is False
    assert document["fq11_counter_completeness_present"] is False
    assert document["formal_counter_records_issued"] is False
    assert document["formal_work_vector_issued"] is False
    assert document["formal_comparison_vector_issued"] is False
    assert document["formal_actual_projection_proof_issued"] is False
    assert document["current_access_authority_present"] is False
    assert document["formal_v7_authority_present"] is False
    assert document["peak_scope_status"] == "PEAK_SCOPE_UNRESOLVED"
    assert document["construction_only"] is True
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_exact_inputs_call_e4_authority_and_bind_complete_identity_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    attestation = _issue(context, e3_completion, e4_completion)
    assert calls == [(e4_completion, context, e3_completion)]
    document = attestation.to_document()
    completion = e4_completion.to_document()
    chain = document["identity_chain"]
    assert chain["h1_e3_bound_output_completion_id"] == e4_completion.completion_id
    assert chain["h1_e3_bound_output_continuation_context_id"] == context.context_id
    assert chain["h1_exclusive_broker_completion_id"] == e3_completion.completion_id
    assert chain["h1_e3_bound_output_continuation_profile_id"] == (
        e4_v1.official_h1_e3_bound_output_continuation_profile_v1().profile_id
    )
    assert chain["h1_exclusive_broker_profile_id"] == (
        e3_v1.official_h1_exclusive_broker_profile_v1().profile_id
    )
    assert chain["h1_exclusive_broker_source_identity"][
        "h1_exclusive_broker_source_manifest_id"
    ] == e3_v1.official_h1_exclusive_broker_source_manifest_v1().manifest_id
    assert document["output_directory_identity"] == completion["writer_allocation"][
        "output_directory"
    ]
    assert len(document["persisted_output_identities"]) == 8
    assert len(
        {
            (row["device"], row["inode"])
            for row in document["persisted_output_identities"]
        }
    ) == 8
    assert e5ba_v1.verify_h1_e4_in_supervisor_attestation_structure_v1(
        attestation=document,
        e4_completion=completion,
    )
    assert e5ba_v1.verify_h1_e4_in_supervisor_authoritative_attestation_v1(
        attestation=attestation,
        context=context,
        e3_completion=e3_completion,
        e4_completion=e4_completion,
    )
    assert calls == [
        (e4_completion, context, e3_completion),
        (e4_completion, context, e3_completion),
    ]


@pytest.mark.parametrize("verifier_result", [False, 1, "true"])
def test_authority_requires_the_exact_boolean_true(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    verifier_result: object,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    monkeypatch.setattr(
        e4_v1,
        "verify_h1_e3_bound_output_completion_v1",
        lambda **_kwargs: verifier_result,
    )
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="did not return true",
    ):
        _issue(context, e3_completion, e4_completion)


def test_authority_exception_cannot_issue_an_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )

    def rejected(**_kwargs: object) -> bool:
        raise RuntimeError("injected authority failure")

    monkeypatch.setattr(
        e4_v1,
        "verify_h1_e3_bound_output_completion_v1",
        rejected,
    )
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="authoritative replay failed",
    ):
        _issue(context, e3_completion, e4_completion)


def test_guardian_replays_only_structure_and_persisted_eight_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    attestation = _issue(context, e3_completion, e4_completion)
    assert len(calls) == 1

    def forbidden_authority(**_kwargs: object) -> bool:
        raise AssertionError("guardian called same-process E4 authority")

    monkeypatch.setattr(
        e4_v1,
        "verify_h1_e3_bound_output_completion_v1",
        forbidden_authority,
    )
    replay = e5ba_v1.replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
        attestation=attestation.to_document(),
        e4_completion=e4_completion.to_document(),
        output_directory=context._directory_path,  # noqa: SLF001
    )
    document = replay.to_document()
    assert document["guardian_replay_disposition"] == (
        "STRUCTURAL_AND_PERSISTED_EIGHT_FILE_REPLAY_ONLY"
    )
    assert document["persisted_role_count"] == 8
    assert document["eight_distinct_output_inodes"] is True
    assert document["same_process_e4_authoritative_verifier_invoked"] is False
    assert document["exact_retained_context_available"] is False
    assert document["same_process_authority_reperformed"] is False
    assert document["same_process_authority_inferred"] is False
    assert document["may_substitute_same_process_authority"] is False


def test_caller_mint_clone_copy_deepcopy_and_pickle_attacks_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    attestation = _issue(context, e3_completion, e4_completion)
    with pytest.raises(e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error):
        e5ba_v1.H1E4InSupervisorAttestationProfileV1(
            object(), canonical_json_bytes({"schema": "caller"})
        )
    with pytest.raises(e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error):
        e5ba_v1.H1E4InSupervisorAuthoritativeAttestationV1(
            object(), attestation.canonical_bytes, os.getpid(), threading.get_ident()
        )
    with pytest.raises(e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error):
        e5ba_v1.H1E4GuardianPersistedReplayV1(
            object(), canonical_json_bytes({"schema": "caller"})
        )
    for arguments in (
        {
            "context": object(),
            "e3_completion": e3_completion,
            "e4_completion": e4_completion,
        },
        {
            "context": context,
            "e3_completion": object(),
            "e4_completion": e4_completion,
        },
        {
            "context": context,
            "e3_completion": e3_completion,
            "e4_completion": object(),
        },
    ):
        with pytest.raises(e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error):
            e5ba_v1.issue_h1_e4_in_supervisor_authoritative_attestation_v1(
                **arguments  # type: ignore[arg-type]
            )
    cloned = e5ba_v1.H1E4InSupervisorAuthoritativeAttestationV1(
        e5ba_v1._ATTESTATION_ISSUER,  # noqa: SLF001 - registry attack
        attestation.canonical_bytes,
        os.getpid(),
        threading.get_ident(),
    )
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="not exact",
    ):
        e5ba_v1.verify_h1_e4_in_supervisor_authoritative_attestation_v1(
            attestation=cloned,
            context=context,
            e3_completion=e3_completion,
            e4_completion=e4_completion,
        )
    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error):
            operation(attestation)


def test_e3_e4_completion_copies_are_only_runtime_type_inputs_not_identity_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    copied_e3 = copy.copy(e3_completion)
    copied_e4 = copy.copy(e4_completion)
    assert copied_e3 is not e3_completion
    assert copied_e4 is not e4_completion
    attestation = _issue(context, copied_e3, copied_e4)
    evidence = attestation.to_document()["same_process_authority_evidence"]
    assert evidence["exact_retained_context_object_verified"] is True
    assert evidence["exact_e3_completion_runtime_type_verified"] is True
    assert evidence["exact_e4_completion_runtime_type_verified"] is True
    assert evidence["e3_completion_exact_object_identity_retained"] is False
    assert evidence["e4_completion_exact_object_identity_retained"] is False
    assert evidence["authenticated_supervisor_binding_present"] is False
    assert calls == [(copied_e4, context, copied_e3)]


def test_foreign_thread_cannot_issue_or_reverify_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    attestation = _issue(context, e3_completion, e4_completion)
    errors: list[BaseException] = []

    def attack() -> None:
        for operation in (
            lambda: _issue(context, e3_completion, e4_completion),
            lambda: e5ba_v1.verify_h1_e4_in_supervisor_authoritative_attestation_v1(
                attestation=attestation,
                context=context,
                e3_completion=e3_completion,
                e4_completion=e4_completion,
            ),
        ):
            try:
                operation()
            except BaseException as error:
                errors.append(error)

    thread = threading.Thread(target=attack)
    thread.start()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert len(errors) == 2
    assert all(
        type(error) is e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error
        for error in errors
    )


@pytest.mark.skipif(not hasattr(os, "fork"), reason="fork is unavailable")
def test_fork_cannot_issue_or_reverify_but_may_run_nonauthoritative_guardian_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    attestation = _issue(context, e3_completion, e4_completion)
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
    child = os.fork()
    if child == 0:  # pragma: no cover - asserted by parent packet
        os.close(read_fd)
        bits = 0
        try:
            _issue(context, e3_completion, e4_completion)
        except e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error:
            bits |= 1
        try:
            e5ba_v1.verify_h1_e4_in_supervisor_authoritative_attestation_v1(
                attestation=attestation,
                context=context,
                e3_completion=e3_completion,
                e4_completion=e4_completion,
            )
        except e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error:
            bits |= 2
        try:
            replay = (
                e5ba_v1.replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
                    attestation=attestation.to_document(),
                    e4_completion=e4_completion.to_document(),
                    output_directory=context._directory_path,  # noqa: SLF001
                )
            )
            if replay.to_document()["may_substitute_same_process_authority"] is False:
                bits |= 4
        except BaseException:
            pass
        os.write(write_fd, bytes([bits]))
        os.close(write_fd)
        os._exit(0)
    os.close(write_fd)
    try:
        assert os.read(read_fd, 1) == b"\x07"
        waited, status = os.waitpid(child, 0)
        assert waited == child
        assert os.waitstatus_to_exitcode(status) == 0
    finally:
        os.close(read_fd)


@pytest.mark.parametrize(
    "field_path,replacement",
    [
        (("guardian_replay_contract", "may_substitute_same_process_authority"), True),
        (("identity_chain", "h1_exclusive_broker_completion_id"), "ab" * 32),
        (("same_process_authority_evidence", "e4_authoritative_verifier_returned_true"), False),
    ],
)
def test_coherently_resigned_attestation_cannot_change_any_bound_semantic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field_path: tuple[str, str],
    replacement: object,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    document = _issue(context, e3_completion, e4_completion).to_document()
    document[field_path[0]][field_path[1]] = replacement
    payload = dict(document)
    payload.pop("h1_e4_in_supervisor_authoritative_attestation_id")
    document["h1_e4_in_supervisor_authoritative_attestation_id"] = (
        domains_v13.extension_content_id_v13(
            domains_v13.CONSTRUCTION_K7_H1_E4_IN_SUPERVISOR_AUTHORITATIVE_ATTESTATION_V1_DOMAIN,
            payload,
        )
    )
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="complete E4 identity reconstruction",
    ):
        e5ba_v1.verify_h1_e4_in_supervisor_attestation_structure_v1(
            attestation=document,
            e4_completion=e4_completion.to_document(),
        )


def test_crossed_exact_e3_identity_fails_even_when_authority_call_returns_true(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, _e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    crossed = _unchecked_runtime_type_e3_completion_unit_seam(
        completion_id=_id("crossed-completion"),
        session_nonce=e4_completion.to_document()["e3_session_nonce"],
        context_id=context.context_id,
    )
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="identity chain crossed",
    ):
        _issue(context, crossed, e4_completion)


def test_guardian_rejects_changed_mode_extra_file_and_crossed_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    attestation = _issue(context, e3_completion, e4_completion).to_document()
    first = context._directory_path / e4_v1.ROLE_FILE_NAMES[e4_v1.ROLE_ORDER[0]]  # noqa: SLF001
    os.chmod(first, 0o600)
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="changed durable output",
    ):
        e5ba_v1.replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
            attestation=attestation,
            e4_completion=e4_completion.to_document(),
            output_directory=context._directory_path,  # noqa: SLF001
        )
    os.chmod(first, 0o400)
    extra = context._directory_path / "foreign"  # noqa: SLF001
    extra.write_bytes(b"x")
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="omitted, extra or renamed",
    ):
        e5ba_v1.replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
            attestation=attestation,
            e4_completion=e4_completion.to_document(),
            output_directory=context._directory_path,  # noqa: SLF001
        )
    extra.unlink()
    crossed = tmp_path / "crossed"
    crossed.mkdir()
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="bound output parent/name",
    ):
        e5ba_v1.replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
            attestation=attestation,
            e4_completion=e4_completion.to_document(),
            output_directory=crossed,
        )


def test_guardian_rejects_changed_bytes_and_replacement_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    attestation = _issue(context, e3_completion, e4_completion).to_document()
    role = e4_v1.ROLE_ORDER[0]
    target = context._directory_path / e4_v1.ROLE_FILE_NAMES[role]  # noqa: SLF001
    original = target.read_bytes()
    os.chmod(target, 0o600)
    changed = bytes([original[0] ^ 1]) + original[1:]
    target.write_bytes(changed)
    os.chmod(target, 0o400)
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="changed durable output",
    ):
        e5ba_v1.replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
            attestation=attestation,
            e4_completion=e4_completion.to_document(),
            output_directory=context._directory_path,  # noqa: SLF001
        )
    os.chmod(target, 0o600)
    target.write_bytes(original)
    replaced = target.with_name("replacement")
    replaced.write_bytes(original)
    os.chmod(replaced, 0o400)
    target.unlink()
    replaced.rename(target)
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="changed durable output",
    ):
        e5ba_v1.replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
            attestation=attestation,
            e4_completion=e4_completion.to_document(),
            output_directory=context._directory_path,  # noqa: SLF001
        )


def test_guardian_rejects_parent_rename_symlink_swap_after_parent_fd_is_pinned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    attestation = _issue(context, e3_completion, e4_completion).to_document()
    parent = context._directory_path.parent  # noqa: SLF001
    moved_parent = parent.with_name(f"{parent.name}-moved")
    real_open = os.open
    swapped = False

    def swapping_open(path, flags, mode=0o777, *, dir_fd=None):
        nonlocal swapped
        if (
            not swapped
            and dir_fd is not None
            and path == context._directory_path.name  # noqa: SLF001
        ):
            parent.rename(moved_parent)
            os.symlink(moved_parent, parent)
            swapped = True
        if dir_fd is None:
            return real_open(path, flags, mode)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(e5ba_v1.os, "open", swapping_open)
    try:
        with pytest.raises(
            e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
            match="output directory changed",
        ):
            e5ba_v1.replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
                attestation=attestation,
                e4_completion=e4_completion.to_document(),
                output_directory=context._directory_path,  # noqa: SLF001
            )
        assert swapped is True
    finally:
        if parent.is_symlink():
            parent.unlink()
        if moved_parent.exists():
            moved_parent.rename(parent)


def test_guardian_rejects_first_file_replacement_during_later_file_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, e3_completion, e4_completion, _calls = _successful_unit_seam(
        tmp_path, monkeypatch
    )
    attestation = _issue(context, e3_completion, e4_completion).to_document()
    first_role = e4_v1.ROLE_ORDER[0]
    first_path = context._directory_path / e4_v1.ROLE_FILE_NAMES[first_role]  # noqa: SLF001
    first_bytes = first_path.read_bytes()
    real_pread_exact = e5ba_v1._pread_exact  # noqa: SLF001
    read_count = 0

    def replacing_pread_exact(descriptor: int, extent: int) -> bytes:
        nonlocal read_count
        read_count += 1
        if read_count == 2:
            replacement = first_path.with_name("mid-loop-replacement")
            replacement.write_bytes(first_bytes)
            os.chmod(replacement, 0o400)
            first_path.unlink()
            replacement.rename(first_path)
        return real_pread_exact(descriptor, extent)

    monkeypatch.setattr(e5ba_v1, "_pread_exact", replacing_pread_exact)
    with pytest.raises(
        e5ba_v1.ConstructionK7H1E4InSupervisorAttestationV1Error,
        match="output directory changed",
    ):
        e5ba_v1.replay_h1_e4_attestation_and_persisted_files_for_guardian_v1(
            attestation=attestation,
            e4_completion=e4_completion.to_document(),
            output_directory=context._directory_path,  # noqa: SLF001
        )
    assert read_count == 8
