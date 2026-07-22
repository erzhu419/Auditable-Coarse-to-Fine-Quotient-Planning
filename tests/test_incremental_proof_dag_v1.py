"""V0-051 identity-bound incremental proof-DAG regressions."""

import copy
from dataclasses import replace
import hashlib
from pathlib import Path
import inspect

import pytest
import acfqp.certificate_memoization_v1 as memo_module

import acfqp.incremental_proof_dag_v1 as dag_module
from acfqp.incremental_proof_dag_v1 import (
    IncrementalProofDAGInvariantViolation,
    ProofCacheScope,
    ProofNodeKind,
    ProofResolutionOutcome,
    ProofRootRole,
    incremental_proof_dag_semantics_v1,
    require_incremental_proof_dag_family_execution_v1,
    run_identity_bound_incremental_proof_dag_family_v1,
    run_lmb_incremental_proof_dag_control_v1,
    verify_lmb_incremental_proof_dag_control_v1,
)
from tests.test_heldout_family_amortization_v1 import (
    family_contract as family_contract_fixture,
)


EXPECTED_PREFIX_COMPUTES = {
    ProofCacheScope.REQUEST_RESET: (24, 48, 72, 96, 120, 144, 168),
    ProofCacheScope.OCCURRENCE_RESET: (16, 32, 48, 64, 80, 96, 112),
    ProofCacheScope.GLOBAL: (16, 29, 34, 39, 52, 57, 62),
}

EXPECTED_GLOBAL_BY_KIND = {
    ProofNodeKind.U: (1, 20),
    ProofNodeKind.P: (2, 19),
    ProofNodeKind.C: (6, 15),
    ProofNodeKind.D: (6, 15),
    ProofNodeKind.E: (10, 11),
    ProofNodeKind.F: (10, 11),
    ProofNodeKind.G: (6, 15),
    ProofNodeKind.R: (21, 0),
}

EXPECTED_OCCURRENCE_RESET_BY_KIND = {
    ProofNodeKind.U: (7, 14),
    ProofNodeKind.P: (14, 7),
    ProofNodeKind.C: (14, 7),
    ProofNodeKind.D: (14, 7),
    ProofNodeKind.E: (14, 7),
    ProofNodeKind.F: (14, 7),
    ProofNodeKind.G: (14, 7),
    ProofNodeKind.R: (21, 0),
}


def _kind_counts(work, field_name: str) -> dict[ProofNodeKind, int]:
    """Read one axis from the canonical ordered kind-count vector."""

    return {item.kind: getattr(item, field_name) for item in work.kind_counts}


def _execution_for_scope(result, scope: ProofCacheScope):
    return {
        ProofCacheScope.REQUEST_RESET: result.request_reset_execution,
        ProofCacheScope.OCCURRENCE_RESET: result.occurrence_reset_execution,
        ProofCacheScope.GLOBAL: result.global_execution,
    }[scope]


@pytest.fixture(scope="module")
def incremental_contract():
    parent = family_contract_fixture.__wrapped__()
    result = run_lmb_incremental_proof_dag_control_v1(
        parent["log"],
        parent["profile"],
        parent["authority"],
        parent["result"].promotion_build,
    )
    return {**parent, "incremental_result": result}


def test_production_api_is_four_input_and_never_calls_monolithic_auditor(
    incremental_contract, monkeypatch
) -> None:
    contract = incremental_contract
    semantics = incremental_proof_dag_semantics_v1()
    assert semantics.partial_audit_source_sha256 == (
        dag_module.EXPECTED_PARTIAL_AUDIT_SOURCE_SHA256
    )
    assert semantics.family_planner_source_sha256 == (
        dag_module.EXPECTED_FAMILY_PLANNER_SOURCE_SHA256
    )
    assert hashlib.sha256(Path(memo_module.__file__).read_bytes()).hexdigest() == (
        "0558fbb2f2e5f4f35894711903115f80fe5ab4dbe7bd70a2bd19db0da5da1282"
    )

    assert tuple(
        inspect.signature(
            run_identity_bound_incremental_proof_dag_family_v1
        ).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "promotion",
    )
    forbidden = {
        "kernel",
        "source_result",
        "legacy_audit",
        "cold_direct",
        "control_result",
    }
    assert not forbidden & set(
        inspect.signature(
            run_identity_bound_incremental_proof_dag_family_v1
        ).parameters
    )

    def forbidden_auditor(*args, **kwargs):
        raise AssertionError("production DAG called the monolithic V0-043 auditor")

    monkeypatch.setattr(
        dag_module.audit_module,
        "_audit_verified_partial_model_v1",
        forbidden_auditor,
    )
    replay = run_identity_bound_incremental_proof_dag_family_v1(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["result"].promotion_build,
    )
    assert replay.to_document() == (
        contract["incremental_result"].global_execution.to_document()
    )
    assert replay.aggregate_work.target_transition_calls == 0
    assert replay.aggregate_work.target_catalogue_calls == 0


def test_three_arms_have_exact_context_request_and_resolution_counts(
    incremental_contract,
) -> None:
    result = incremental_contract["incremental_result"]
    expected = {
        ProofCacheScope.REQUEST_RESET: (168, 0),
        ProofCacheScope.OCCURRENCE_RESET: (112, 56),
        ProofCacheScope.GLOBAL: (62, 106),
    }
    for scope, pair in expected.items():
        execution = _execution_for_scope(result, scope)
        assert execution.cache_scope is scope
        assert len(execution.contexts) == 7
        protocol = execution.protocol
        assert type(protocol) is dag_module.IncrementalProofDAGProtocolV1
        assert tuple(item.to_document() for item in protocol.ordered_contexts) == tuple(
            item.context.to_document() for item in execution.contexts
        )
        assert len({item.context_id for item in protocol.ordered_contexts}) == 7
        assert len({
            item.threshold_binding.thresholds.thresholds_id
            for item in execution.contexts
        }) == 7
        assert len({
            item.threshold_binding.binding_id for item in execution.contexts
        }) == 7
        assert protocol.adjacent_change_kinds == (
            "INITIAL_DISTRIBUTION",
            "NORMALIZED_REGRET_TOLERANCE",
            "RISK_TOLERANCE",
            "INITIAL_DISTRIBUTION",
            "NORMALIZED_REGRET_TOLERANCE",
            "RISK_TOLERANCE",
        )
        assert protocol.single_field_adjacency_required is True
        assert len(execution.use_receipts) == 21
        assert sum(
            len(receipt.resolutions) for receipt in execution.use_receipts
        ) == 168
        assert (
            execution.aggregate_work.computed_count,
            execution.aggregate_work.reused_count,
        ) == pair
        assert execution.aggregate_work.proof_request_count == 21
        assert execution.aggregate_work.obligation_resolution_count == 168
        assert sum(len(item.candidate_audit_results) for item in execution.contexts) == 14
        assert len(execution.contexts) == 7
        assert execution.aggregate_work.target_transition_calls == 0
        assert execution.aggregate_work.target_catalogue_calls == 0


def test_per_kind_and_prefix_counts_are_exact(incremental_contract) -> None:
    result = incremental_contract["incremental_result"]
    for scope in ProofCacheScope:
        execution = _execution_for_scope(result, scope)
        assert tuple(
            prefix.cumulative_computed_count
            for prefix in execution.prefixes
        ) == EXPECTED_PREFIX_COMPUTES[scope]
        assert tuple(
            prefix.cumulative_resolution_count
            for prefix in execution.prefixes
        ) == tuple(24 * index for index in range(1, 8))

    request = result.request_reset_execution.aggregate_work
    assert _kind_counts(request, "computed_count") == {
        kind: 21 for kind in ProofNodeKind
    }
    assert _kind_counts(request, "reused_count") == {
        kind: 0 for kind in ProofNodeKind
    }

    occurrence = result.occurrence_reset_execution.aggregate_work
    assert {
        kind: (
            _kind_counts(occurrence, "computed_count")[kind],
            _kind_counts(occurrence, "reused_count")[kind],
        )
        for kind in ProofNodeKind
    } == EXPECTED_OCCURRENCE_RESET_BY_KIND

    global_work = result.global_execution.aggregate_work
    assert {
        kind: (
            _kind_counts(global_work, "computed_count")[kind],
            _kind_counts(global_work, "reused_count")[kind],
        )
        for kind in ProofNodeKind
    } == EXPECTED_GLOBAL_BY_KIND


def test_legacy_planner_audit_and_certificate_artifacts_match_exactly(
    incremental_contract,
) -> None:
    result = incremental_contract["incremental_result"]
    assert len(result.legacy_audit_matches) == 21
    assert all(item.exact_document_match for item in result.legacy_audit_matches)
    for request_context, occurrence_context, global_context in zip(
        result.request_reset_execution.contexts,
        result.occurrence_reset_execution.contexts,
        result.global_execution.contexts,
    ):
        assert request_context.plan_proposal.to_document() == (
            occurrence_context.plan_proposal.to_document()
        ) == global_context.plan_proposal.to_document()
        assert request_context.candidate_audit_results == (
            occurrence_context.candidate_audit_results
        ) == global_context.candidate_audit_results
        assert request_context.selected_plan_audit.to_document() == (
            occurrence_context.selected_plan_audit.to_document()
        ) == global_context.selected_plan_audit.to_document()
    assert all(
        context.selected_plan_audit.audit_result.outcome
        is dag_module.PartialAuditOutcome.CERTIFIED_FIXED_PLAN
        for context in result.global_execution.contexts
    )
    for context in result.global_execution.contexts:
        assert context.selected_plan_audit.audit_result.thresholds_id == (
            context.threshold_binding.thresholds.thresholds_id
        )
        assert context.plan_proposal.selected_plan is not None
        assert context.plan_proposal.selected_plan.plan_id == (
            context.selected_plan_audit.audit_result.contingent_plan_id
        )


def test_changed_facets_recompute_exact_descendant_closures(
    incremental_contract,
) -> None:
    closures = incremental_contract[
        "incremental_result"
    ].global_execution.change_closures
    assert len(closures) == 7
    expected = (
        (("INITIAL_CONTEXT",), tuple(ProofNodeKind)),
        (("INITIAL_DISTRIBUTION",), (ProofNodeKind.C, ProofNodeKind.D, ProofNodeKind.E,
                   ProofNodeKind.F, ProofNodeKind.G, ProofNodeKind.R)),
        (("NORMALIZED_REGRET_TOLERANCE",), (ProofNodeKind.E, ProofNodeKind.R)),
        (("RISK_TOLERANCE",), (ProofNodeKind.F, ProofNodeKind.R)),
        (("INITIAL_DISTRIBUTION",), (ProofNodeKind.C, ProofNodeKind.D, ProofNodeKind.E,
                   ProofNodeKind.F, ProofNodeKind.G, ProofNodeKind.R)),
        (("NORMALIZED_REGRET_TOLERANCE",), (ProofNodeKind.E, ProofNodeKind.R)),
        (("RISK_TOLERANCE",), (ProofNodeKind.F, ProofNodeKind.R)),
    )
    assert tuple(
        (item.directly_changed_facets, item.recomputed_kinds) for item in closures
    ) == expected
    assert all(item.expected_new_nodes_by_kind == item.actual_new_nodes_by_kind for item in closures)


def test_root_is_role_bound_while_lower_nodes_are_shared(
    incremental_contract,
) -> None:
    receipts = incremental_contract[
        "incremental_result"
    ].global_execution.use_receipts[:3]
    assert tuple(item.audit_role for item in receipts) == (
        ProofRootRole.CANDIDATE_RANKING_AUDIT,
        ProofRootRole.CANDIDATE_RANKING_AUDIT,
        ProofRootRole.INDEPENDENT_SELECTED_PLAN_CERTIFICATE,
    )
    selected = receipts[2]
    matching_candidate = next(
        item
        for item in receipts[:2]
        if item.contingent_plan_id == selected.contingent_plan_id
    )
    assert selected.planner_result_id is not None
    assert matching_candidate.planner_result_id is None
    assert tuple(
        item.node_key_id for item in matching_candidate.resolutions[:-1]
    ) == tuple(item.node_key_id for item in selected.resolutions[:-1])
    assert matching_candidate.resolutions[-1].kind is ProofNodeKind.R
    assert selected.resolutions[-1].kind is ProofNodeKind.R
    assert matching_candidate.resolutions[-1].node_key_id != (
        selected.resolutions[-1].node_key_id
    )


def test_threshold_bound_v1_rows_are_rejected_below_root(
    incremental_contract,
) -> None:
    cache = incremental_contract[
        "incremental_result"
    ].global_execution.final_cache
    lower = next(
        item for item in cache.entries if item.key.kind is not ProofNodeKind.R
    )
    with pytest.raises(IncrementalProofDAGInvariantViolation):
        replace(lower, threshold_bound_v1_row_count=1)
    root = next(item for item in cache.entries if item.key.kind is ProofNodeKind.R)
    assert root.threshold_bound_v1_row_count > 0
    semantics = incremental_proof_dag_semantics_v1()
    assert semantics.threshold_bound_v1_rows_only_at_root is True
    assert semantics.monolithic_auditor_production_calls == 0


def test_graph_facet_cache_trace_and_owner_attacks_fail_closed(
    incremental_contract,
) -> None:
    execution = incremental_contract["incremental_result"].global_execution
    with pytest.raises(IncrementalProofDAGInvariantViolation):
        require_incremental_proof_dag_family_execution_v1(copy.copy(execution))

    cache = execution.final_cache
    d_entry = next(item for item in cache.entries if item.key.kind is ProofNodeKind.D)
    missing_parent_key = replace(
        d_entry.key,
        dependency_node_ids=d_entry.key.dependency_node_ids[:-1],
    )
    missing_parent_entry = replace(d_entry, key=missing_parent_key)
    replaced_entries = tuple(
        sorted(
            (
                missing_parent_entry if item.entry_id == d_entry.entry_id else item
                for item in cache.entries
            ),
            key=lambda item: item.key.node_key_id,
        )
    )
    with pytest.raises(IncrementalProofDAGInvariantViolation):
        replace(
            execution,
            _instance_mint=None,
            final_cache=replace(cache, entries=replaced_entries),
        )

    u_entry = next(item for item in cache.entries if item.key.kind is ProofNodeKind.U)
    p_entry = next(item for item in cache.entries if item.key.kind is ProofNodeKind.P)
    extra_edge_key = replace(
        p_entry.key,
        dependency_node_ids=(u_entry.key.node_key_id,),
    )
    extra_edge_entry = replace(p_entry, key=extra_edge_key)
    extra_edge_entries = tuple(
        sorted(
            (
                extra_edge_entry if item.entry_id == p_entry.entry_id else item
                for item in cache.entries
            ),
            key=lambda item: item.key.node_key_id,
        )
    )
    with pytest.raises(IncrementalProofDAGInvariantViolation):
        replace(
            execution,
            _instance_mint=None,
            final_cache=replace(cache, entries=extra_edge_entries),
        )

    cycle_key = replace(
        u_entry.key,
        dependency_node_ids=(d_entry.key.node_key_id,),
    )
    cycle_entry = replace(u_entry, key=cycle_key)
    cycle_entries = tuple(
        sorted(
            (
                cycle_entry if item.entry_id == u_entry.entry_id else item
                for item in cache.entries
            ),
            key=lambda item: item.key.node_key_id,
        )
    )
    with pytest.raises(IncrementalProofDAGInvariantViolation):
        replace(
            execution,
            _instance_mint=None,
            final_cache=replace(cache, entries=cycle_entries),
        )

    c_entry = next(item for item in cache.entries if item.key.kind is ProofNodeKind.C)
    stale_key = replace(
        c_entry.key,
        identity_terms=tuple(
            (
                name,
                hashlib.sha256(b"stale-rho-facet").hexdigest()
                if name == "initial_state_id"
                else value,
            )
            for name, value in c_entry.key.identity_terms
        ),
    )
    stale_entry = replace(c_entry, key=stale_key)
    stale_entries = tuple(
        sorted(
            (
                stale_entry if item.entry_id == c_entry.entry_id else item
                for item in cache.entries
            ),
            key=lambda item: item.key.node_key_id,
        )
    )
    with pytest.raises(IncrementalProofDAGInvariantViolation):
        replace(
            execution,
            _instance_mint=None,
            final_cache=replace(cache, entries=stale_entries),
        )

    with pytest.raises(IncrementalProofDAGInvariantViolation):
        replace(
            execution,
            _instance_mint=None,
            final_cache=replace(cache, entries=cache.entries[:-1]),
        )
    def reject_trace(receipts: tuple) -> None:
        contexts = tuple(
            replace(
                context,
                request_receipt_ids=tuple(
                    receipt.receipt_id
                    for receipt in receipts[3 * index : 3 * index + 3]
                ),
            )
            for index, context in enumerate(execution.contexts)
        )
        with pytest.raises(IncrementalProofDAGInvariantViolation):
            replace(
                execution,
                _instance_mint=None,
                contexts=contexts,
                use_receipts=receipts,
            )

    fake_state = hashlib.sha256(b"forged-cache-state").hexdigest()
    first = execution.use_receipts[0]
    assert first.resolutions[0].pre_cache_state_id == dag_module._cache_state_id({})
    bad_pre = replace(
        first.resolutions[0],
        pre_cache_state_id=fake_state,
    )
    bad_pre_receipt = replace(
        first,
        resolutions=(bad_pre, *first.resolutions[1:]),
    )
    reject_trace((bad_pre_receipt, *execution.use_receipts[1:]))

    bad_post = replace(
        first.resolutions[0],
        post_cache_state_id=fake_state,
    )
    bad_post_receipt = replace(
        first,
        resolutions=(bad_post, *first.resolutions[1:]),
    )
    reject_trace((bad_post_receipt, *execution.use_receipts[1:]))

    forged = replace(
        execution.use_receipts[0].resolutions[0],
        outcome=ProofResolutionOutcome.REUSED,
    )
    forged_receipt = replace(
        execution.use_receipts[0],
        resolutions=(forged, *execution.use_receipts[0].resolutions[1:]),
    )
    reject_trace((forged_receipt, *execution.use_receipts[1:]))

    reject_trace(
        (
            execution.use_receipts[1],
            execution.use_receipts[0],
            *execution.use_receipts[2:],
        )
    )


def test_claim_boundary_remains_locked(incremental_contract) -> None:
    result = incremental_contract["incremental_result"]
    assert result.registered_h1_changed_query_incremental_proof_claimed is True
    assert result.identity_bound_incremental_proof_claimed is False
    assert result.cross_identity_unaffected_obligation_reuse_claimed is False
    assert result.general_cross_identity_incremental_proof_claimed is False
    assert result.higher_horizon_incremental_bellman_claimed is False
    assert result.reward_or_model_epoch_incremental_claimed is False
    assert result.persistent_cache_claimed is False
    assert result.sample_tax_operator_claimed is False
    assert result.sample_efficiency_claimed is False
    assert result.total_work_or_wallclock_reduction_claimed is False
    assert result.learned_or_partial_dynamics_claimed is False
    assert result.cross_domain_generalization_claimed is False
    assert result.official_execution_allowed is False
    assert result.official_scalar_cost is None
    assert result.official_N_break_even is None
    assert (
        result.workload_economics_gate == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
    assert (
        result.counter_completeness_gate == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert (
        result.sample_efficiency_gate == "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    )
    with pytest.raises(IncrementalProofDAGInvariantViolation):
        replace(result, sample_efficiency_claimed=True)


def test_canonical_v0051_identities_are_frozen(incremental_contract) -> None:
    result = incremental_contract["incremental_result"]
    actual = {
        "protocol": result.global_execution.protocol.protocol_id,
        "semantics": result.global_execution.semantics.semantics_id,
        "global_cache": result.global_execution.final_cache.cache_id,
        "global_execution": result.global_execution.execution_id,
        "result": result.result_id,
    }
    assert actual == {
        "protocol": "b2cd30af3237849564f91ea0afdfa435b4c3a9d326bb37b1328e5366cea20696",
        "semantics": "dfd4fc7b5947fe577c6a379c023596fb9895f2e363a7b4bf09dffca5fa233dcf",
        "global_cache": "d1dea47c694c46c30b45cd8cdc2487b3c612044c20eb41903233fa535f62dae7",
        "global_execution": "4867e54dacd64bccd6e6ed084d6e37198256fa0a142bad4bbcb26a439404b8a5",
        "result": "23bd8600fa3bb21de226c7ec9e631ddf20c971a308f27f059f19a2c939166fa6",
    }


def test_full_independent_v0051_replay_is_byte_identical(
    incremental_contract,
) -> None:
    contract = incremental_contract
    verified = verify_lmb_incremental_proof_dag_control_v1(
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
        contract["incremental_result"],
    )
    assert verified.to_document() == (
        contract["incremental_result"].to_document()
    )
