from __future__ import annotations

from collections import Counter
from dataclasses import replace
import hashlib
import io
import zipfile

import pytest

from acfqp import construction_accounting_owner_event_candidates_v1 as owner_v1
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as occurrence_v2
from acfqp import construction_profile_native_zero_rules_v1 as rules_v1
from acfqp import construction_profile_native_zero_semantic_authority_v1 as zero_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
def _inputs(positive):
    occurrence = occurrence_v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(
        **positive
    )
    transport = positive["request_replay"].request.profile.accounted_profile.transport_profile
    return {
        "occurrence_cutoff_authority": occurrence,
        "owner_candidate_set": positive["owner_event_candidates"],
        "verified_nine_envelope": positive["verified_envelope"],
        "runtime_envelope": positive["runtime_envelope"],
        "request_replay": positive["request_replay"],
        "role_manifest": positive["role_manifest"],
        "operational_output_bytes": positive["operational_output_bytes"],
        "source_archive_raw": transport._archive_bytes,  # noqa: SLF001
    }


@pytest.fixture(scope="module")
def zero_case(positive):
    inputs = _inputs(positive)
    return inputs, zero_v1.issue_k7_profile_native_zero_semantic_authority_v1(
        **inputs
    )


def test_exact_114_path_semantic_authority_and_lock_state(zero_case) -> None:
    inputs, result = zero_case
    replayed = zero_v1.replay_k7_profile_native_zero_semantic_authority_v1(
        result, **inputs
    )
    byte_replay = zero_v1.verify_k7_profile_native_zero_semantic_authority_bytes_v1(
        raw=result.canonical_bytes, **inputs
    )
    registry = rules_v1.official_profile_native_zero_rule_registry_v1()

    assert replayed.envelope_id == result.envelope_id == byte_replay.envelope_id
    assert len(result.attestations) == 114
    assert {row.path for row in result.attestations} == set(registry.by_path)
    assert all(row.value == 0 for row in result.attestations)
    assert Counter(row.reason_code for row in result.attestations) == {
        "K7_PROFILE_BRANCH_NOT_EXECUTED": 62,
        "FORBIDDEN_STAGE_NOT_EXECUTED": 34,
        "LEGACY_OWNER_REPLACED": 16,
        "LEGACY_SEMANTIC_SPLIT_REPLACED": 2,
    }
    document = result.to_document()
    assert document["exact_114_path_set"] is True
    assert document["absence_is_zero_evidence"] is False
    assert document["counter_records_issued"] is False
    assert document["work_vector_issued"] is False
    assert document["comparison_vector_issued"] is False
    assert document["formal_materialization_allowed"] is False
    assert document["official_execution_allowed"] is False


def test_every_rule_obligation_has_exact_nonempty_evidence(zero_case) -> None:
    _inputs_unused, result = zero_case
    rules = rules_v1.official_profile_native_zero_rule_registry_v1().by_path
    for attestation in result.attestations:
        expected = {
            (row.kind.value, row.obligation_key)
            for row in rules[attestation.path].evidence_requirements
        }
        actual = {(row.kind, row.obligation_key) for row in attestation.obligations}
        assert actual == expected
        assert all(row.evidence_ids for row in attestation.obligations)
        assert attestation.to_document()["event_absence_used_as_zero_evidence"] is False


def test_legacy_replacements_are_topological_and_exactly_resolved(zero_case) -> None:
    _inputs_unused, result = zero_case
    rank = {path: index for index, path in enumerate(result.topological_path_order)}
    replacement_rows = [row for row in result.attestations if row.replacements]
    assert len(replacement_rows) == 18
    assert {
        replacement.resolution_kind
        for row in replacement_rows
        for replacement in row.replacements
    } == {"OWNER_PATH_COUNTER_CANDIDATE", "PROFILE_NATIVE_ZERO_ATTESTATION"}
    for row in replacement_rows:
        for replacement in row.replacements:
            if replacement.resolution_kind == "PROFILE_NATIVE_ZERO_ATTESTATION":
                assert replacement.dependency_attestation_rank == rank[
                    replacement.replacement_path
                ]
                assert replacement.dependency_attestation_rank < row.issuance_rank


@pytest.mark.parametrize("attack", ["mutate", "missing", "duplicate"])
def test_portable_bytes_reject_mutation_missing_and_duplicate(zero_case, attack) -> None:
    inputs, result = zero_case
    document = loads_canonical_json(result.canonical_bytes)
    assert type(document) is dict
    rows = document["native_zero_attestations"]
    if attack == "mutate":
        rows[0]["value"] = 1
    elif attack == "missing":
        rows.pop()
    else:
        rows[-1] = rows[0]
    with pytest.raises(
        zero_v1.ConstructionProfileNativeZeroSemanticAuthorityV1Error,
        match="content identity|differs from independent semantic replay",
    ):
        zero_v1.verify_k7_profile_native_zero_semantic_authority_bytes_v1(
            raw=canonical_json_bytes(document), **inputs
        )


def test_transplanted_occurrence_or_candidate_identity_is_rejected(zero_case) -> None:
    inputs, _result = zero_case
    occurrence = inputs["occurrence_cutoff_authority"].occurrence_authority
    original = occurrence.owner_event_candidate_set_id
    object.__setattr__(
        occurrence,
        "owner_event_candidate_set_id",
        hashlib.sha256(b"foreign owner candidate").hexdigest(),
    )
    try:
        with pytest.raises(
            zero_v1.ConstructionProfileNativeZeroSemanticAuthorityV1Error,
            match="prerequisite failed semantic replay",
        ):
            zero_v1.issue_k7_profile_native_zero_semantic_authority_v1(**inputs)
    finally:
        object.__setattr__(occurrence, "owner_event_candidate_set_id", original)


def _augment_archive(raw: bytes) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw), "r") as source, zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_STORED, allowZip64=True
    ) as target:
        for info in source.infolist():
            replacement = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            replacement.compress_type = zipfile.ZIP_STORED
            replacement.create_system = info.create_system
            replacement.external_attr = info.external_attr
            target.writestr(replacement, source.read(info))
        extra = zipfile.ZipInfo(
            "acfqp/unregistered_zero_emitter_attack.py",
            date_time=(1980, 1, 1, 0, 0, 0),
        )
        extra.compress_type = zipfile.ZIP_STORED
        extra.create_system = 3
        extra.external_attr = (0o100444 & 0xFFFF) << 16
        target.writestr(
            extra,
            b"def attack(accounting_runtime):\n"
            b"    accounting_runtime.emit_owned_operation_v1('unregistered.zero.path')\n",
        )
    return output.getvalue()


def test_unregistered_source_emission_capability_defeats_absence_attack(positive) -> None:
    candidate_set = positive["owner_event_candidates"]
    original = candidate_set.execution_binding
    changed = _augment_archive(
        positive["request_replay"].request.profile.accounted_profile.transport_profile._archive_bytes  # noqa: SLF001
    )
    binding = owner_v1.OwnerEventExecutionBindingV1(
        owner_v1._BINDING_ISSUER,  # noqa: SLF001 - source-capability attack
        original.request_id,
        original.route_identity_id,
        original.scientific_occurrence_id,
        original.phase3e_logical_occurrence_id,
        original.production_role_manifest_id,
        original.production_runtime_envelope_id,
        original.broker_transcript_id,
        original.business_bundle_id,
        original.source_snapshot_id,
        hashlib.sha256(changed).hexdigest(),
        len(changed),
        original.postexec_binding_id,
    )
    with pytest.raises(
        zero_v1.ConstructionProfileNativeZeroSemanticAuthorityV1Error,
        match="global loaded-source accounting gateway inventory changed",
    ):
        zero_v1._scan_source_hook_inventory(  # noqa: SLF001
            source_archive_raw=changed,
            execution_binding=binding,
        )


def test_dependency_cycle_and_caller_minting_fail_closed(zero_case) -> None:
    with pytest.raises(
        zero_v1.ConstructionProfileNativeZeroSemanticAuthorityV1Error,
        match="dependency cycle",
    ):
        zero_v1._topological_order({"a": ("b",), "b": ("a",)})  # noqa: SLF001

    _inputs_unused, result = zero_case
    with pytest.raises(
        zero_v1.ConstructionProfileNativeZeroSemanticAuthorityV1Error,
        match="caller-minted",
    ):
        replace(result, _issuer=object())


def test_missing_and_noncanonical_bytes_fail_closed(zero_case) -> None:
    inputs, _result = zero_case
    for raw in (b"", b'{"x": 1}'):
        with pytest.raises(
            zero_v1.ConstructionProfileNativeZeroSemanticAuthorityV1Error,
            match="missing|noncanonical",
        ):
            zero_v1.verify_k7_profile_native_zero_semantic_authority_bytes_v1(
                raw=raw, **inputs
            )
