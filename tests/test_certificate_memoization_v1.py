"""V0-050 exact identity-bound certificate memoization regressions."""

import copy
from dataclasses import replace
import hashlib
import inspect

import pytest

import acfqp.certificate_memoization_v1 as memo_module
from acfqp.certificate_memoization_v1 import (
    AuditExecutionRelation,
    CertificateMemoizationInvariantViolation,
    FixedPlanAuditRole,
    MemoLookupOutcome,
    MemoRouteKind,
    fixed_plan_audit_memo_semantics_v1,
    lookup_fixed_plan_audit_memo_entry_v1,
    require_memoized_heldout_family_execution_v1,
    run_identity_bound_memoized_family_v1,
    run_lmb_certificate_memoization_control_v1,
    verify_lmb_certificate_memoization_control_v1,
)
from tests.test_heldout_family_amortization_v1 import (
    family_contract as family_contract_fixture,
)


@pytest.fixture(scope="module")
def memo_contract():
    parent = family_contract_fixture.__wrapped__()
    result = run_lmb_certificate_memoization_control_v1(
        parent["log"],
        parent["profile"],
        parent["authority"],
        parent["result"],
    )
    return {**parent, "memo_result": result}


def test_memo_runner_is_kernel_source_and_control_blind(memo_contract) -> None:
    contract = memo_contract
    assert tuple(
        inspect.signature(run_identity_bound_memoized_family_v1).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "promotion",
    )
    parameters = inspect.signature(
        run_identity_bound_memoized_family_v1
    ).parameters
    assert "kernel" not in parameters
    assert "source_result" not in parameters
    assert "parent_family_result" not in parameters
    assert "cold_direct" not in parameters
    semantics = fixed_plan_audit_memo_semantics_v1()
    assert semantics.partial_audit_source_sha256 == (
        memo_module.EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256
    )
    assert semantics.family_planner_source_sha256 == (
        memo_module.EXPECTED_FAMILY_PLANNER_SOURCE_SHA256
    )
    assert memo_module.DOMAIN_TAGS["semantics"] != (
        memo_module.DOMAIN_TAGS["planner_semantics"]
    )
    execution = require_memoized_heldout_family_execution_v1(
        contract["memo_result"].memoized_execution
    )
    assert execution.initial_store_empty is True
    assert execution.no_control_warm_start is True


def test_exact_nine_misses_twenty_one_hits_and_prefix_curve(
    memo_contract,
) -> None:
    result = memo_contract["memo_result"]
    execution = result.memoized_execution
    assert result.no_reuse_work.route_kind is MemoRouteKind.NO_REUSE_CONTROL
    assert result.memo_work.route_kind is MemoRouteKind.EXACT_IDENTITY_MEMO
    assert result.no_reuse_work.full_audit_execution_count == 30
    assert result.memo_work.full_audit_execution_count == 9
    assert result.memo_work.memo_hit_count == 21
    assert result.memo_work.memo_miss_count == 9
    assert result.memo_work.cache_insert_count == 9
    assert result.memo_work.plan_candidate_count == 20
    assert result.no_reuse_work.plan_candidate_count == 20
    assert len(execution.final_cache.entries) == 9
    assert tuple(
        item.work.full_audit_execution_count for item in execution.occurrences
    ) == (3, 3, 3, 0, 0, 0, 0, 0, 0, 0)
    assert tuple(item.work.memo_hit_count for item in execution.occurrences) == (
        0,
        0,
        0,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
    )
    assert tuple(item.memo_full_audit_executions for item in execution.prefixes) == (
        3,
        6,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
    )
    assert tuple(item.relation for item in execution.prefixes) == (
        AuditExecutionRelation.EQUAL,
        AuditExecutionRelation.EQUAL,
        AuditExecutionRelation.EQUAL,
        *(AuditExecutionRelation.MEMO_FEWER_FULL_AUDITS for _ in range(7)),
    )
    assert all(item.official_scalar_cost is None for item in execution.prefixes)
    assert all(item.official_N_break_even is None for item in execution.prefixes)


def test_roles_are_separate_and_all_artifacts_match_no_reuse_and_cold(
    memo_contract,
) -> None:
    contract = memo_contract
    result = contract["memo_result"]
    execution = result.memoized_execution
    assert sum(
        item.memo_key.audit_role
        is FixedPlanAuditRole.CANDIDATE_RANKING_AUDIT
        for item in execution.final_cache.entries
    ) == 6
    assert sum(
        item.memo_key.audit_role
        is FixedPlanAuditRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE
        for item in execution.final_cache.entries
    ) == 3
    for no_reuse, memo, matched in zip(
        contract["result"].matched_occurrences,
        execution.occurrences,
        result.matched_occurrences,
    ):
        assert no_reuse.threshold_binding.to_document() == (
            memo.threshold_binding.to_document()
        )
        assert no_reuse.warm_plan.to_document() == memo.plan_proposal.to_document()
        assert no_reuse.warm_audit.to_document() == memo.plan_audit.to_document()
        assert memo.plan_audit.audit_result.thresholds_id == (
            memo.threshold_binding.thresholds.thresholds_id
        )
        bounds = memo.plan_audit.audit_result.robust_bounds
        assert bounds.policy_reward_lower == no_reuse.cold_direct.optimal_reward
        assert bounds.policy_failure_upper == (
            no_reuse.cold_direct.failure_probability
        )
        assert bounds.normalized_distribution_regret == (
            no_reuse.cold_direct.normalized_regret
        )
        assert matched.exact_planner_artifact_match is True
        assert matched.exact_audit_artifact_match is True
    assert result.telemetry.audit_execution_reduction.numerator == 7
    assert result.telemetry.audit_execution_reduction.denominator == 10
    assert result.telemetry.incremental_proof_claimed is False
    assert result.telemetry.sample_efficiency_claimed is False
    assert result.telemetry.overall_workload_economics_claimed is False


def test_actual_full_auditor_is_called_exactly_nine_times(
    memo_contract, monkeypatch
) -> None:
    contract = memo_contract
    original = memo_module._audit_verified_partial_model_v1
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(memo_module, "_audit_verified_partial_model_v1", counted)
    execution = run_identity_bound_memoized_family_v1(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["result"].promotion_build,
    )
    assert calls == 9
    assert execution.to_document() == (
        contract["memo_result"].memoized_execution.to_document()
    )


def test_model_query_threshold_plan_and_role_changes_invalidate_hits(
    memo_contract,
) -> None:
    cache = memo_contract["memo_result"].memoized_execution.final_cache
    entry = next(
        item
        for item in cache.entries
        if item.memo_key.audit_role
        is FixedPlanAuditRole.CANDIDATE_RANKING_AUDIT
    )
    key = entry.memo_key
    assert lookup_fixed_plan_audit_memo_entry_v1(cache, key) is entry
    mutable_identity_fields = (
        "structural_id",
        "environment_instance_id",
        "base_model_id",
        "source_refinement_result_id",
        "family_protocol_id",
        "family_promotion_result_id",
        "family_eligibility_proof_id",
        "promoted_model_id",
        "observation_log_id",
        "semantics_profile_id",
        "observation_authority_id",
        "target_query_id",
        "threshold_binding_id",
        "thresholds_id",
        "return_bound_proof_id",
        "contingent_plan_id",
        "planner_semantics_id",
        "memo_semantics_id",
    )
    for field_name in mutable_identity_fields:
        fake = hashlib.sha256(f"changed:{field_name}".encode()).hexdigest()
        changed = replace(key, **{field_name: fake})
        assert lookup_fixed_plan_audit_memo_entry_v1(cache, changed) is None
    role_changed = replace(
        key,
        audit_role=FixedPlanAuditRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE,
        planner_result_id=hashlib.sha256(b"changed:planner-result").hexdigest(),
    )
    assert lookup_fixed_plan_audit_memo_entry_v1(cache, role_changed) is None
    selected_entry = next(
        item
        for item in cache.entries
        if item.memo_key.audit_role
        is FixedPlanAuditRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE
    )
    selected_key = selected_entry.memo_key
    selected_result_changed = replace(
        selected_key,
        planner_result_id=hashlib.sha256(
            b"changed:selected-planner-result-only"
        ).hexdigest(),
    )
    assert lookup_fixed_plan_audit_memo_entry_v1(
        cache, selected_result_changed
    ) is None
    with pytest.raises(CertificateMemoizationInvariantViolation):
        replace(key, thresholds_id="not-a-content-id")

    receipts = memo_contract["memo_result"].memoized_execution.use_receipts
    first = receipts[0]
    repeated = receipts[9]
    assert first.target_query_id == repeated.target_query_id
    assert first.memo_key_id == repeated.memo_key_id
    assert first.occurrence_id != repeated.occurrence_id
    assert first.outcome is MemoLookupOutcome.MISS_FULL_AUDIT_EXECUTED
    assert repeated.outcome is MemoLookupOutcome.HIT_EXACT_IDENTITY
    assert repeated.source_miss_occurrence_id == first.occurrence_id


def test_trace_cache_and_owner_authority_attacks_fail_closed(memo_contract) -> None:
    result = memo_contract["memo_result"]
    execution = result.memoized_execution
    copied = copy.copy(execution)
    with pytest.raises(CertificateMemoizationInvariantViolation):
        require_memoized_heldout_family_execution_v1(copied)
    with pytest.raises(CertificateMemoizationInvariantViolation):
        replace(execution, initial_store_empty=False)
    with pytest.raises(CertificateMemoizationInvariantViolation):
        replace(
            execution.final_cache,
            entries=execution.final_cache.entries[:-1],
        )
    with pytest.raises(CertificateMemoizationInvariantViolation):
        replace(result.telemetry, incremental_proof_claimed=True)
    with pytest.raises(CertificateMemoizationInvariantViolation):
        replace(result.telemetry, sample_efficiency_claimed=True)
    forged_receipt = replace(
        execution.use_receipts[3],
        pre_cache_state_id=hashlib.sha256(b"forged-state").hexdigest(),
    )
    with pytest.raises(CertificateMemoizationInvariantViolation):
        replace(
            execution,
            use_receipts=(
                execution.use_receipts[:3]
                + (forged_receipt,)
                + execution.use_receipts[4:]
            ),
        )
    forged_prefix = replace(
        execution.prefixes[0],
        occurrence_ids=(
            execution.occurrences[1].occurrence.occurrence_id,
        ),
    )
    with pytest.raises(CertificateMemoizationInvariantViolation):
        replace(
            execution,
            prefixes=(
                forged_prefix,
                *execution.prefixes[1:],
            ),
        )


def test_canonical_v0050_identities_are_frozen(memo_contract) -> None:
    result = memo_contract["memo_result"]
    actual = {
        "semantics": result.memoized_execution.memo_semantics.semantics_id,
        "cache": result.memoized_execution.final_cache.cache_id,
        "execution": result.memoized_execution.execution_id,
        "telemetry": result.telemetry.telemetry_id,
        "result": result.result_id,
    }
    assert actual == {
        "semantics": "0d52e0035d291bc976d341022548fc30b61fcc979f2166e49f47a8ab54fbca20",
        "cache": "4ea5007ce76a5c46dd9094002b4ed5de4133243a187e554a8170a4e73ce04d3b",
        "execution": "d7c343e451c5e0f7237bce0d8c0d379ff5ea18ece211d9d829a00c462f4dce38",
        "telemetry": "db318d45cc41f22ea6c7f1a9a6a66dd7a325dfdc9d2f474f29227978007ffa73",
        "result": "fa96c8645b507b145eb9821f2436e9aa68321460343529203878c33c653b13c7",
    }


def test_full_independent_v0050_replay_is_byte_identical(memo_contract) -> None:
    contract = memo_contract
    verified = verify_lmb_certificate_memoization_control_v1(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["synthesis"],
        contract["source_thresholds"],
        contract["source_proposal"],
        contract["source_failed_audit"],
        contract["protocol"],
        contract["source_result"],
        contract["kernel"],
        contract["result"],
        contract["memo_result"],
    )
    assert verified.to_document() == contract["memo_result"].to_document()
