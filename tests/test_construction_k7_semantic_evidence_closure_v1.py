from __future__ import annotations

from collections import Counter
from dataclasses import replace
import hashlib

import pytest

from acfqp import construction_k7_derived_reconciliation_v1 as derived_v1
from acfqp import construction_k7_derived_reconciliation_v2 as derived_v2
from acfqp import construction_k7_semantic_evidence_closure_v1 as closure_v1
from acfqp import construction_profile_native_zero_semantic_authority_v1 as zero_v1
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from tests import test_construction_profile_native_zero_semantic_authority_v1 as zero_test


@pytest.fixture(scope="module")
def semantic_case(positive):
    zero_inputs = zero_test._inputs(positive)  # noqa: SLF001
    occurrence = zero_inputs["occurrence_cutoff_authority"]
    zeros = zero_v1.issue_k7_profile_native_zero_semantic_authority_v1(
        **zero_inputs
    )
    derived = derived_v2.derive_k7_complete_eight_path_reconciliation_v2(
        verified_nine=positive["verified_envelope"],
        authority_bundle=occurrence,
        route_replay_inputs=positive,
        owner_transcript=positive["owned_result"].transcript,
    )
    inputs = {
        "replay_roots": positive,
        "occurrence_authority": occurrence,
        "verified_nine": positive["verified_envelope"],
        "owner_candidates": positive["owner_event_candidates"],
        "profile_native_zeros": zeros,
        "derived_reconciliation": derived,
    }
    result = closure_v1.issue_k7_semantic_evidence_closure_v1(**inputs)
    return inputs, result


def test_exact_202_path_semantic_partition_and_materialization_lock(semantic_case) -> None:
    inputs, result = semantic_case
    replayed = closure_v1.replay_k7_semantic_evidence_closure_v1(
        result, **inputs
    )
    portable = closure_v1.verify_k7_semantic_evidence_closure_bytes_v1(
        raw=result.canonical_bytes, **inputs
    )
    counts = Counter(row.kind.value for row in result.resolutions)
    assert replayed.closure_id == result.closure_id == portable.closure_id
    assert len(result.resolutions) == 202
    assert counts["SHARED_RESOURCE_EXACT"] == 9
    assert counts["OWNER_EVENT_STREAM"] + counts["OWNER_WINDOW_ZERO"] == 71
    assert counts["OWNER_EVENT_STREAM"] > 0
    assert counts["OWNER_WINDOW_ZERO"] > 0
    assert counts["PROFILE_NATIVE_ZERO"] == 114
    assert counts["DERIVED_RECONCILIATION"] == 8
    document = result.to_document()
    assert document["next_atomic_materialization_authorized"] is True
    assert document["counter_records_issued"] is False
    assert document["work_vector_issued"] is False
    assert document["comparison_vector_issued"] is False
    assert document["official_execution_allowed"] is False


def test_owner_stream_and_owner_window_zero_remain_distinct(semantic_case) -> None:
    inputs, result = semantic_case
    candidates = {
        row.path: row for row in inputs["owner_candidates"].path_candidates
    }
    for path, candidate in candidates.items():
        resolution = result.by_path[path]
        if candidate.value:
            assert resolution.kind is closure_v1.SemanticResolutionKindV1.OWNER_EVENT_STREAM
            assert resolution.value == len(resolution.primitive_evidence_ids)
            assert resolution.primitive_evidence_ids == candidate.ordered_event_ids
        else:
            assert resolution.kind is closure_v1.SemanticResolutionKindV1.OWNER_WINDOW_ZERO
            assert resolution.value == 0
            assert resolution.primitive_evidence_ids == ()
        assert resolution.kind is not closure_v1.SemanticResolutionKindV1.PROFILE_NATIVE_ZERO


def test_every_path_has_unique_evidence_and_recorder_authority(semantic_case) -> None:
    _inputs, result = semantic_case
    primary = [row.primary_evidence_id for row in result.resolutions]
    recorder = [row.recorder_authority_id for row in result.resolutions]
    primitive = [
        evidence
        for row in result.resolutions
        for evidence in row.primitive_evidence_ids
    ]
    assert len(primary) == len(set(primary)) == 202
    assert len(recorder) == len(set(recorder)) == 202
    assert set(primary).isdisjoint(recorder)
    assert len(primitive) == len(set(primitive))


def test_derived_formula_and_dependency_dag_are_exact(semantic_case) -> None:
    inputs, result = semantic_case
    readiness = inputs["derived_reconciliation"]
    proofs = readiness.exact_proofs_by_path
    for path in derived_v1.DERIVED_PATHS:
        resolution = result.by_path[path]
        assert resolution.kind is closure_v1.SemanticResolutionKindV1.DERIVED_RECONCILIATION
        assert resolution.primary_evidence_id == proofs[path].proof_id
        assert resolution.formula_id == proofs[path].formula_id
        assert resolution.dependency_paths == proofs[path].closure_dependency_paths
    result._verify_dependency_dag()  # noqa: SLF001


@pytest.mark.parametrize("attack", ["mutate", "missing", "duplicate"])
def test_portable_closure_rejects_mutation_missing_and_duplicate(semantic_case, attack) -> None:
    inputs, result = semantic_case
    document = loads_canonical_json(result.canonical_bytes)
    assert type(document) is dict
    rows = document["resolutions"]
    if attack == "mutate":
        rows[0]["value"] += 1
    elif attack == "missing":
        rows.pop()
    else:
        rows[-1] = rows[0]
    with pytest.raises(
        closure_v1.ConstructionK7SemanticEvidenceClosureV1Error,
        match="content identity|differs from independent replay",
    ):
        closure_v1.verify_k7_semantic_evidence_closure_bytes_v1(
            raw=canonical_json_bytes(document), **inputs
        )


def test_incomplete_derived_authority_and_crossed_zero_context_fail(semantic_case) -> None:
    inputs, _result = semantic_case
    incomplete = derived_v1.derive_k7_eight_path_reconciliation_v1(
        verified_nine=inputs["verified_nine"],
        owner_transcript=inputs["replay_roots"]["owned_result"].transcript,
    )
    for replacement in (incomplete, incomplete.status.value):
        bad = dict(inputs)
        bad["derived_reconciliation"] = replacement
        with pytest.raises(
            closure_v1.ConstructionK7SemanticEvidenceClosureV1Error,
            match="exact complete replay roots and typed authorities",
        ):
            closure_v1.issue_k7_semantic_evidence_closure_v1(**bad)

    zeros = inputs["profile_native_zeros"]
    original = zeros.owner_candidate_set_id
    crossed_id = hashlib.sha256(b"crossed-zero").hexdigest()
    object.__setattr__(zeros, "owner_candidate_set_id", crossed_id)
    assert crossed_id != original
    try:
        with pytest.raises(
            closure_v1.ConstructionK7SemanticEvidenceClosureV1Error,
            match="failed independent root replay",
        ):
            closure_v1.issue_k7_semantic_evidence_closure_v1(**inputs)
    finally:
        object.__setattr__(zeros, "owner_candidate_set_id", original)
def test_reused_primary_evidence_cycle_and_caller_minting_fail(semantic_case) -> None:
    _inputs, result = semantic_case
    first, second = result.resolutions[:2]
    crossed = replace(
        second,
        _issuer=closure_v1._RESOLUTION_ISSUER,  # noqa: SLF001
        primary_evidence_id=first.primary_evidence_id,
        recorder_authority_id=closure_v1._path_recorder_authority_id(  # noqa: SLF001
            context_id=second.context_id,
            path=second.path,
            kind=second.kind,
            primary_id=first.primary_evidence_id,
        ),
    )
    rows = list(result.resolutions)
    rows[1] = crossed
    with pytest.raises(
        closure_v1.ConstructionK7SemanticEvidenceClosureV1Error,
        match="reused across paths",
    ):
        closure_v1.K7SemanticEvidenceClosureV1(
            closure_v1._CLOSURE_ISSUER,  # noqa: SLF001
            result.context,
            tuple(rows),
        )

    target = result.by_path["route.failures"]
    original = target.dependency_paths
    object.__setattr__(target, "dependency_paths", ("route.attempts",))
    try:
        with pytest.raises(
            closure_v1.ConstructionK7SemanticEvidenceClosureV1Error,
            match="contains a cycle",
        ):
            result._verify_dependency_dag()  # noqa: SLF001
    finally:
        object.__setattr__(target, "dependency_paths", original)

    with pytest.raises(
        closure_v1.ConstructionK7SemanticEvidenceClosureV1Error,
        match="caller-minted",
    ):
        replace(result, _issuer=object())
