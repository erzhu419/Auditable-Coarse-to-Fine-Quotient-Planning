from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_derived_reconciliation_v1 as v1
from acfqp import construction_k7_derived_reconciliation_v2 as v2
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as occurrence_v2
from tests import test_construction_k7_derived_reconciliation_v1 as v1_test


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:test:k7-derived-reconciliation:v2\x00" + label.encode("utf-8")
    ).hexdigest()


@pytest.fixture(scope="module")
def complete(positive):
    authority = (
        occurrence_v2.issue_k7_occurrence_cutoff_semantic_authorities_v2(
            **positive
        )
    )
    readiness = v2.derive_k7_complete_eight_path_reconciliation_v2(
        verified_nine=positive["verified_envelope"],
        authority_bundle=authority,
        route_replay_inputs=positive,
    )
    return positive, authority, readiness


def test_complete_readiness_closes_all_eight_with_stable_public_rows(
    complete,
) -> None:
    positive, authority, readiness = complete
    assert dict(readiness.exact_values) == {
        "process.exit_failures": 0,
        "process.exit_successes": 2,
        "route.attempts": 1,
        "route.failures": 1,
        "route.successes": 0,
        "solver.attempts": 0,
        "solver.failures": 0,
        "solver.successes": 0,
    }
    assert tuple(row.path for row in readiness.proof_rows) == v1.DERIVED_PATHS
    assert set(readiness.exact_proofs_by_path) == set(v1.DERIVED_PATHS)
    assert len({row.proof_id for row in readiness.proof_rows}) == 8
    assert all(row.closure_dependency_paths for row in readiness.proof_rows)
    assert {
        row.path: row.proof_version for row in readiness.proof_rows
    } == {
        path: (
            "V2_ROUTE"
            if path in v2.ROUTE_PATHS
            else (
                v2.MAPPED_SOLVER_PROOF_VERSION
                if path.startswith("solver.")
                else "V1"
            )
        )
        for path in v1.DERIVED_PATHS
    }
    document = readiness.to_document()
    assert document["all_eight_exact"] is True
    assert document["unresolved_paths"] == []
    assert document["counter_record_materialization_eligible"] is True
    assert document["counter_records_issued"] is False
    assert document["formal_vector_authorized"] is False
    assert document["v1_payloads_or_ids_changed"] is False
    assert document["v1_public_derivation_changed"] is False
    assert document["scientific_to_logical_occurrence_mapping_explicit"] is True
    assert document["solver_dependency_uses_successor_mapping"] is True
    replayed = v2.replay_k7_complete_eight_path_reconciliation_v2(
        readiness,
        verified_nine=positive["verified_envelope"],
        authority_bundle=authority,
        route_replay_inputs=positive,
    )
    assert replayed.readiness_id == readiness.readiness_id


def test_route_dependency_binds_transcript_context_and_actual_business_bytes(
    complete,
) -> None:
    positive, authority, readiness = complete
    dependency = readiness.route_dependency_v2
    facts = dependency.by_fact
    occurrence = authority.occurrence_authority
    assert tuple(key for key, _value in dependency.bound_facts) == (
        v2.ROUTE_BOUND_FACT_KEYS
    )
    assert len(facts) == len(dependency.bound_facts)
    assert facts["route_attempt_id"] == occurrence.route_attempt_id
    assert facts["partial_native_transcript_id"] == (
        occurrence.partial_native_transcript_id
    )
    assert facts["partial_native_terminal_id"] == occurrence.transcript_terminal_id
    assert facts["runtime_business_result_id"] == (
        positive["runtime_envelope"].business_result_id
    )
    assert facts["runtime_business_result_sha256"] == (
        positive["runtime_envelope"].business_result_sha256
    )
    assert facts["runtime_business_result_byte_count"] == (
        positive["runtime_envelope"].business_result_byte_count
    )
    assert facts["route_attempt_count"] == 1
    assert facts["route_success_count"] == 0
    assert facts["route_failure_count"] == 1


def _synthetic_route_dependency(
    *,
    verified,
    transcript,
    scientific_occurrence_id: str,
) -> v2.K7RouteTerminalSemanticDependencyV2:
    source = verified.source_envelope
    authority_bundle_id = _id("mapped-authority-bundle")
    sha_keys = {
        "operational_output_sha256",
        "runtime_business_result_sha256",
        "source_archive_sha256",
        "transcript_document_sha256",
    }
    count_values = {
        "charged_output_bytes": 1,
        "ordered_chain_node_count": len(transcript.nodes),
        "route_attempt_count": 1,
        "route_failure_count": 1,
        "route_success_count": 0,
        "runtime_business_result_byte_count": 1,
        "source_archive_byte_count": 1,
    }
    special_values = {
        "authority_bundle_id": authority_bundle_id,
        "counter_registry_id": source.counter_registry_id,
        "logical_occurrence_id": source.occurrence_id,
        "partial_native_terminal_id": transcript.nodes[-1].chain_id,
        "partial_native_transcript_id": transcript.transcript_id,
        "route_attempt_outcome": "FAILURE",
        "scientific_occurrence_id": scientific_occurrence_id,
        "stage_profile_id": source.stage_profile_id,
        "terminal_kind": "COMPLETED",
        "terminal_status": "CHILD_ACTION_ROW_CAP_EXCEEDED",
        "verified_nine_envelope_id": verified.verified_envelope_id,
    }
    facts = tuple(
        (
            key,
            special_values.get(
                key,
                count_values.get(
                    key,
                    "a" * 64 if key in sha_keys else _id(f"mapped-{key}"),
                ),
            ),
        )
        for key in v2.ROUTE_BOUND_FACT_KEYS
    )
    return v2.K7RouteTerminalSemanticDependencyV2(
        v2._ROUTE_DEPENDENCY_ISSUER,  # noqa: SLF001 - exact unit predecessor
        source.counter_registry_id,
        source.stage_profile_id,
        source.occurrence_id,
        verified.verified_envelope_id,
        authority_bundle_id,
        facts,
        (
            ("root_terminal.route_failures", 1),
            ("root_terminal.route_successes", 0),
        ),
        ("synthetic_occurrence_mapping_replayed",),
    )


def test_solver_exclusion_uses_explicit_scientific_to_logical_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verified = v1_test._verified_nine(tmp_path, monkeypatch)  # noqa: SLF001
    scientific_occurrence_id = _id("scientific-occurrence")
    assert scientific_occurrence_id != verified.source_envelope.occurrence_id
    transcript = v1_test._completed_root_cap_transcript(  # noqa: SLF001
        scientific_occurrence_id
    )
    route_dependency = _synthetic_route_dependency(
        verified=verified,
        transcript=transcript,
        scientific_occurrence_id=scientific_occurrence_id,
    )

    with pytest.raises(
        v1.ConstructionK7DerivedReconciliationV1Error,
        match="cannot prove solver exclusion",
    ):
        v1.derive_solver_stage_exclusion_dependency_v1(
            verified=verified,
            transcript=transcript,
        )

    mapped = v2._derive_occurrence_mapped_solver_dependency_v2(  # noqa: SLF001
        verified_nine=verified,
        owner_transcript=transcript,
        route_dependency=route_dependency,
    )
    assert mapped.occurrence_id == verified.source_envelope.occurrence_id
    assert route_dependency.dependency_id in mapped.source_ids
    assert dict(mapped.exact_values) == {
        "root_stage_profile.solver_failures": 0,
        "root_stage_profile.solver_successes": 0,
    }
    assert (
        "scientific_to_logical_occurrence_mapping_replayed"
        in mapped.semantic_checks
    )

    base, process_dependency, solver_dependency = (
        v2._assemble_occurrence_mapped_v1_shape_v2(  # noqa: SLF001
            verified_nine=verified,
            owner_transcript=transcript,
            route_dependency=route_dependency,
        )
    )
    route_proofs = v2._route_proofs_v2(  # noqa: SLF001
        verified_nine=verified,
        dependency=route_dependency,
    )
    values = {
        **{row.path: row.value for row in base.proofs},
        **{row.path: row.value for row in route_proofs},
    }
    readiness = v2.K7CompleteDerivedReconciliationReadinessV2(
        v2._READINESS_ISSUER,  # noqa: SLF001 - exact unit issuance
        base,
        process_dependency,
        solver_dependency,
        route_dependency,
        route_proofs,
        tuple((path, values[path]) for path in v1.DERIVED_PATHS),
    )
    assert {
        row.path: row.proof_version for row in readiness.proof_rows
    } == {
        path: (
            "V2_ROUTE"
            if path in v2.ROUTE_PATHS
            else (
                v2.MAPPED_SOLVER_PROOF_VERSION
                if path.startswith("solver.")
                else "V1"
            )
        )
        for path in v1.DERIVED_PATHS
    }
    assert readiness.to_document()[
        "scientific_to_logical_occurrence_mapping_explicit"
    ] is True

    crossed = _synthetic_route_dependency(
        verified=verified,
        transcript=transcript,
        scientific_occurrence_id=_id("foreign-scientific-occurrence"),
    )
    with pytest.raises(
        v2.ConstructionK7DerivedReconciliationV2Error,
        match="mapping cannot prove",
    ):
        v2._derive_occurrence_mapped_solver_dependency_v2(  # noqa: SLF001
            verified_nine=verified,
            owner_transcript=transcript,
            route_dependency=crossed,
        )


def test_status_only_missing_replay_and_old_v1_are_rejected(complete) -> None:
    positive, authority, readiness = complete
    with pytest.raises(
        v2.ConstructionK7DerivedReconciliationV2Error,
        match="exact occurrence/cutoff authority",
    ):
        v2.derive_route_terminal_semantic_dependency_v2(
            verified_nine=positive["verified_envelope"],
            authority_bundle={"terminal_status": "CHILD_ACTION_ROW_CAP_EXCEEDED"},
            replay_inputs=positive,
        )
    missing = dict(positive)
    missing.pop("operational_output_bytes")
    with pytest.raises(
        v2.ConstructionK7DerivedReconciliationV2Error,
        match="exact independent replay input set",
    ):
        v2.derive_route_terminal_semantic_dependency_v2(
            verified_nine=positive["verified_envelope"],
            authority_bundle=authority,
            replay_inputs=missing,
        )
    with pytest.raises(
        v2.ConstructionK7DerivedReconciliationV2Error,
        match="exact V2 readiness",
    ):
        v2.replay_k7_complete_eight_path_reconciliation_v2(
            readiness.base_v1_readiness,
            verified_nine=positive["verified_envelope"],
            authority_bundle=authority,
            route_replay_inputs=positive,
        )


def test_duplicate_bound_fact_key_is_rejected(complete) -> None:
    _positive, _authority, readiness = complete
    dependency = readiness.route_dependency_v2
    duplicate = tuple(
        sorted((*dependency.bound_facts, dependency.bound_facts[0]))
    )
    with pytest.raises(
        v2.ConstructionK7DerivedReconciliationV2Error,
        match="duplicate key",
    ):
        replace(
            dependency,
            _issuer=v2._ROUTE_DEPENDENCY_ISSUER,  # noqa: SLF001 - attack
            bound_facts=duplicate,
        )


def test_transplanted_authority_and_rewritten_raw_bytes_are_rejected(
    complete,
) -> None:
    positive, authority, _readiness = complete
    occurrence = replace(
        authority.occurrence_authority,
        _issuer=occurrence_v2._OCCURRENCE_ISSUER,  # noqa: SLF001 - attack
        route_attempt_id=_id("foreign-route-attempt"),
    )
    cutoff = replace(
        authority.cutoff_authority,
        _issuer=occurrence_v2._CUTOFF_ISSUER,  # noqa: SLF001 - attack
        occurrence_authority_id=occurrence.authority_id,
    )
    transplanted = replace(
        authority,
        _issuer=occurrence_v2._BUNDLE_ISSUER,  # noqa: SLF001 - attack
        occurrence_authority=occurrence,
        cutoff_authority=cutoff,
    )
    with pytest.raises(
        v2.ConstructionK7DerivedReconciliationV2Error,
        match="independent replay failed",
    ):
        v2.derive_route_terminal_semantic_dependency_v2(
            verified_nine=positive["verified_envelope"],
            authority_bundle=transplanted,
            replay_inputs=positive,
        )

    rewritten = dict(positive)
    raw = rewritten["operational_output_bytes"]
    rewritten["operational_output_bytes"] = raw[:-1] + bytes((raw[-1] ^ 1,))
    with pytest.raises(
        v2.ConstructionK7DerivedReconciliationV2Error,
        match="independent replay failed",
    ):
        v2.derive_route_terminal_semantic_dependency_v2(
            verified_nine=positive["verified_envelope"],
            authority_bundle=authority,
            replay_inputs=rewritten,
        )


def test_forged_route_outcome_value_and_postissuance_mutation_fail_closed(
    complete,
) -> None:
    _positive, _authority, readiness = complete
    attempts, failures, successes = readiness.route_proofs_v2
    forged_failure = replace(
        failures,
        _issuer=v2._ROUTE_PROOF_ISSUER,  # noqa: SLF001 - attack
        value=0,
    )
    forged_attempt = replace(
        attempts,
        _issuer=v2._ROUTE_PROOF_ISSUER,  # noqa: SLF001 - attack
        value=0,
        derived_dependency_proof_ids=(
            forged_failure.proof_id,
            successes.proof_id,
        ),
    )
    with pytest.raises(
        v2.ConstructionK7DerivedReconciliationV2Error,
        match="V2 route proof DAG",
    ):
        replace(
            readiness,
            _issuer=v2._READINESS_ISSUER,  # noqa: SLF001 - attack
            route_proofs_v2=(forged_attempt, forged_failure, successes),
        )

    original = failures.value
    object.__setattr__(failures, "value", 99)
    try:
        with pytest.raises(
            v2.ConstructionK7DerivedReconciliationV2Error,
            match="route path proof changed",
        ):
            readiness.to_document()
    finally:
        object.__setattr__(failures, "value", original)
