from __future__ import annotations

import ast
from dataclasses import replace
import os
from pathlib import Path

import pytest

from acfqp import campaign_v1
from acfqp import construction_k7_logical_occurrence_closure_v1 as occurrence_closure_v1
from acfqp import (
    construction_k7_production_complete_bundle_independent_verifier_v1
    as complete_v1,
)
from acfqp import construction_k7_production_accounting_pipeline_v1 as pipeline_v1
from tests import (
    test_construction_k7_production_complete_bundle_independent_verifier_v1
    as complete_test,
)


def _archive(positive) -> bytes:
    return (
        positive["request_replay"]
        .request.profile.accounted_profile.transport_profile
        ._archive_bytes  # noqa: SLF001
    )


@pytest.fixture(scope="module")
def assembled_case():
    case = complete_test.synthetic_complete_case.__wrapped__()
    patcher = pytest.MonkeyPatch()
    try:
        complete_test.synthetic_replay.__wrapped__(patcher, case)
        complete = (
            complete_v1.verify_k7_production_complete_bundle_independently_v1(
                semantic_closure_raw=case.semantic_closure.canonical_bytes,
                formal_materialization_raw=case.formal.canonical_bytes,
                terminal_accounting_bundle_raw=case.terminal_bundle.canonical_bytes,
                closure_replay_inputs=case.replay_inputs,
            )
        )
        route = (
            case.replay_inputs["replay_roots"]["request_replay"]
            .request.route_identity
        )
        route.route_identity_id = complete_test._id("route-identity")  # noqa: SLF001
        route.logical_occurrence.rebuild_policy_id = (
            campaign_v1.RebuildPolicyV1().rebuild_policy_id
        )
        route.route_attempt.route_attempt_index = 1
        route.profile.actual_projection_profile_id = complete_test._id(  # noqa: SLF001
            "actual-projection-profile"
        )
        logical = occurrence_closure_v1.issue_k7_logical_occurrence_closure_bundle_v1(
            complete_bundle_verification=complete,
            terminal_accounting_bundle_raw=case.terminal_bundle.canonical_bytes,
            request_route_identity=route,
            rebuild_policy=campaign_v1.RebuildPolicyV1(),
        )
        verified = (
            occurrence_closure_v1
            .verify_k7_logical_occurrence_closure_bundle_bytes_v1(
                raw=logical.canonical_bytes,
                complete_bundle_verification_raw=complete.canonical_bytes,
                semantic_closure_raw=case.semantic_closure.canonical_bytes,
                formal_materialization_raw=case.formal.canonical_bytes,
                terminal_accounting_bundle_raw=case.terminal_bundle.canonical_bytes,
                closure_replay_inputs=case.replay_inputs,
            )
        )
    finally:
        patcher.undo()
    closure_inputs = {
        **case.replay_inputs,
        "verified_nine": object(),
        "owner_candidates": object(),
        "profile_native_zeros": object(),
        "derived_reconciliation": object(),
    }
    result = pipeline_v1.K7ProductionAccountingPipelineResultV1(
        pipeline_v1._RESULT_ISSUER,  # noqa: SLF001
        closure_inputs,
        case.semantic_closure,
        case.formal,
        case.terminal_bundle,
        complete,
        logical,
        verified,
    )
    return case, result


@pytest.fixture(scope="module")
def full_pipeline_case(positive):
    if os.environ.get("ACFQP_RUN_FULL_K7_PIPELINE_REPLAY") != "1":
        pytest.skip("full production-root pipeline is an explicit slow gate")
    result = pipeline_v1.run_k7_production_accounting_pipeline_v1(
        replay_roots=dict(positive),
        source_archive_raw=_archive(positive),
    )
    return positive, result


def test_one_entry_closes_nine_sources_formal_vectors_and_occurrence(
    assembled_case,
) -> None:
    _case, result = assembled_case
    document = result.to_document()
    work = result.formal_materialization.work_vector
    comparison = result.formal_materialization.comparison_vector

    assert document["shared_resource_path_count"] == 9
    assert document["counter_record_count"] == 202
    assert document["projection_term_count"] == 182
    assert document["comparison_axis_count"] == 8
    assert len(work.records) == len({row.path for row in work.records}) == 202
    assert comparison.work_vector_id == work.work_vector_id
    assert document["all_nine_shared_resources_replayed"] is True
    assert document["all_202_required_paths_materialized"] is True
    assert (
        document["counter_record_to_work_vector_to_comparison_vector_complete"]
        is True
    )
    assert document["independent_complete_bundle_replay_passed"] is True
    assert document["logical_occurrence_replay_passed"] is True
    assert document["complete_replay_inputs_retained_for_campaign"] is True
    assert document["logical_occurrence_closed"] is True
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert document["terminal_code"] == "ATTEMPT_BUDGET_EXHAUSTED"
    assert document["specific_cause"] == "CHILD_ACTION_ROW_CAP_EXCEEDED"
    assert document["noncertificate_count"] == 1


def test_pipeline_preserves_locked_gate_boundaries(assembled_case) -> None:
    _case, result = assembled_case
    document = result.to_document()
    assert document["counter_completeness_gate_passed"] is False
    assert document["workload_economics_gate_passed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert result.terminal_accounting.to_document()["plan_certificate"] is False
    assert (
        result.terminal_accounting.to_document()["infeasibility_certificate"]
        is False
    )


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_FULL_K7_PIPELINE_REPLAY") != "1",
    reason="explicit second full-root replay is an independent slow gate",
)
def test_full_root_replay_reconstructs_the_same_pipeline(full_pipeline_case) -> None:
    positive, result = full_pipeline_case
    replayed = pipeline_v1.replay_k7_production_accounting_pipeline_v1(
        result,
        replay_roots=dict(positive),
        source_archive_raw=_archive(positive),
    )
    assert replayed.to_document() == result.to_document()
    assert (
        replayed.logical_occurrence_verification.to_document()
        == result.logical_occurrence_verification.to_document()
    )


@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_partial_root_field_sets_return_no_pipeline_result(mutation) -> None:
    roots = {key: object() for key in pipeline_v1._ROOT_KEYS}  # noqa: SLF001
    if mutation == "missing":
        roots.pop("verified_envelope")
    else:
        roots["reported_actual"] = 1
    with pytest.raises(
        pipeline_v1.ConstructionK7ProductionAccountingPipelineV1Error
    ):
        pipeline_v1.run_k7_production_accounting_pipeline_v1(
            replay_roots=roots,
            source_archive_raw=b"frozen-source",
        )


def test_pipeline_result_cannot_be_caller_minted(assembled_case) -> None:
    _case, result = assembled_case
    with pytest.raises(
        pipeline_v1.ConstructionK7ProductionAccountingPipelineV1Error,
        match="caller-minted",
    ):
        replace(result, _issuer=object())


def test_source_module_has_no_test_fixture_dependency() -> None:
    tree = ast.parse(Path(pipeline_v1.__file__).read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert not any(
        name == "tests" or name.startswith("tests.")
        for name in imported_modules
    )


_STAGE_ORDER = (
    "occurrence",
    "zeros",
    "derived",
    "semantic",
    "formal",
    "terminal",
    "complete",
    "logical",
    "logical_verify",
)


def _install_stage_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    case,
    expected,
    fail_at: str | None = None,
) -> list[str]:
    calls: list[str] = []

    def stage(name: str, value):
        def run(**_kwargs):
            calls.append(name)
            if name == fail_at:
                raise RuntimeError(f"{name} failed")
            return value

        return run

    bindings = (
        (
            pipeline_v1.occurrence_v2,
            "issue_k7_occurrence_cutoff_semantic_authorities_v2",
            stage("occurrence", object()),
        ),
        (
            pipeline_v1.zero_v1,
            "issue_k7_profile_native_zero_semantic_authority_v1",
            stage("zeros", object()),
        ),
        (
            pipeline_v1.derived_v2,
            "derive_k7_complete_eight_path_reconciliation_v2",
            stage("derived", object()),
        ),
        (
            pipeline_v1.semantic_v1,
            "issue_k7_semantic_evidence_closure_from_verified_authorities_v1",
            stage("semantic", case.semantic_closure),
        ),
        (
            pipeline_v1.materializer_v1,
            "materialize_k7_formal_accounting_from_verified_semantic_closure_v1",
            stage("formal", case.formal),
        ),
        (
            pipeline_v1.terminal_v1,
            "issue_k7_root_cap_terminal_accounting_from_verified_materialization_v1",
            stage("terminal", case.terminal_bundle),
        ),
        (
            pipeline_v1.complete_v1,
            "verify_k7_production_complete_bundle_independently_v1",
            stage("complete", expected.complete_verification),
        ),
        (
            pipeline_v1.occurrence_closure_v1,
            "issue_k7_logical_occurrence_closure_bundle_v1",
            stage("logical", expected.logical_occurrence_closure),
        ),
        (
            pipeline_v1.occurrence_closure_v1,
            "verify_k7_logical_occurrence_closure_claim_bytes_v1",
            stage("logical_verify", expected.logical_occurrence_verification),
        ),
    )
    for owner, name, replacement in bindings:
        monkeypatch.setattr(owner, name, replacement)
    return calls


def _stub_roots(case) -> dict[str, object]:
    roots = {key: object() for key in pipeline_v1._ROOT_KEYS}  # noqa: SLF001
    roots["request_replay"] = case.replay_inputs["replay_roots"]["request_replay"]
    return roots


def test_orchestrator_requires_every_stage_before_returning(
    monkeypatch: pytest.MonkeyPatch,
    assembled_case,
) -> None:
    case, expected = assembled_case
    calls = _install_stage_stubs(monkeypatch, case=case, expected=expected)
    result = pipeline_v1.run_k7_production_accounting_pipeline_v1(
        replay_roots=_stub_roots(case),
        source_archive_raw=b"frozen-source",
    )
    assert result.to_document() == expected.to_document()
    assert tuple(calls) == _STAGE_ORDER


def test_pipeline_uses_verified_proof_dag_without_replaying_predecessors(
    monkeypatch: pytest.MonkeyPatch,
    assembled_case,
) -> None:
    case, expected = assembled_case
    _install_stage_stubs(monkeypatch, case=case, expected=expected)

    def repeated_predecessor_replay(**_kwargs):
        raise AssertionError("pipeline recursively replayed a verified predecessor")

    for owner, name in (
        (
            pipeline_v1.semantic_v1,
            "issue_k7_semantic_evidence_closure_v1",
        ),
        (
            pipeline_v1.materializer_v1,
            "materialize_k7_formal_accounting_v1",
        ),
        (
            pipeline_v1.terminal_v1,
            "issue_k7_root_cap_terminal_accounting_bundle_v1",
        ),
        (
            pipeline_v1.occurrence_closure_v1,
            "verify_k7_logical_occurrence_closure_bundle_bytes_v1",
        ),
    ):
        monkeypatch.setattr(owner, name, repeated_predecessor_replay)
    result = pipeline_v1.run_k7_production_accounting_pipeline_v1(
        replay_roots=_stub_roots(case),
        source_archive_raw=b"frozen-source",
    )
    assert result.to_document() == expected.to_document()


@pytest.mark.parametrize(
    "fail_at",
    ("occurrence", "semantic", "formal", "complete", "logical_verify"),
)
def test_any_failed_stage_returns_no_pipeline_result(
    fail_at: str,
    monkeypatch: pytest.MonkeyPatch,
    assembled_case,
) -> None:
    case, expected = assembled_case
    calls = _install_stage_stubs(
        monkeypatch,
        case=case,
        expected=expected,
        fail_at=fail_at,
    )
    with pytest.raises(
        pipeline_v1.ConstructionK7ProductionAccountingPipelineV1Error,
        match="failed full-root replay",
    ):
        pipeline_v1.run_k7_production_accounting_pipeline_v1(
            replay_roots=_stub_roots(case),
            source_archive_raw=b"frozen-source",
        )
    assert tuple(calls) == _STAGE_ORDER[: _STAGE_ORDER.index(fail_at) + 1]
