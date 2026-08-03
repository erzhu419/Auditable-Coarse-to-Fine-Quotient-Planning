from __future__ import annotations

from dataclasses import replace
import hashlib

import pytest

from acfqp import construction_k7_derived_reconciliation_v1 as v1
from acfqp import construction_k7_derived_reconciliation_v2 as v2
from acfqp import construction_occurrence_identity_cutoff_semantic_authority_v2 as occurrence_v2
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
        path: "V2_ROUTE" if path in v2.ROUTE_PATHS else "V1"
        for path in v1.DERIVED_PATHS
    }
    document = readiness.to_document()
    assert document["all_eight_exact"] is True
    assert document["unresolved_paths"] == []
    assert document["counter_record_materialization_eligible"] is True
    assert document["counter_records_issued"] is False
    assert document["formal_vector_authorized"] is False
    assert document["v1_payloads_or_ids_changed"] is False
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
