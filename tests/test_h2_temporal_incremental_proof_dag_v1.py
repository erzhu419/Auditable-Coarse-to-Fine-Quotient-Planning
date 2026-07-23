"""V0-052 H2 temporal incremental proof-DAG regressions."""

import copy
from dataclasses import replace
import hashlib
import inspect
from pathlib import Path

import pytest

import acfqp.heldout_family_amortization_v1 as family_module
import acfqp.incremental_proof_dag_v1 as whole_horizon_module
import acfqp.multistep_query_refinement_v1 as multistep_module
import acfqp.partial_model_planner_v1 as planner_module
import acfqp.partial_sound_audit_v1 as audit_module
import acfqp.h2_temporal_incremental_proof_dag_v1 as temporal_module
from acfqp.domains.matching_buffer import LMBKernel
from tests.test_multistep_query_refinement_v1 import (
    multistep_contract as multistep_contract_fixture,
)


Slot = temporal_module.H2TemporalProofSlot
Scope = temporal_module.H2TemporalCacheScope
Outcome = temporal_module.H2TemporalResolutionOutcome
Role = temporal_module.H2TemporalProofRole
InvariantViolation = temporal_module.H2TemporalProofDAGInvariantViolation


EXPECTED_SLOT_ORDER = (
    Slot.U1,
    Slot.U0,
    Slot.P1,
    Slot.P0,
    Slot.C0,
    Slot.C1,
    Slot.D,
    Slot.E,
    Slot.F,
    Slot.G,
    Slot.R,
)

EXPECTED_PREFIX_COMPUTES = {
    Scope.REQUEST_RESET: (11, 22, 33, 44, 55),
    Scope.EXACT_PLAN_PARTITIONED: (11, 22, 33, 44, 45),
    Scope.GLOBAL_STAGE_DAG: (11, 19, 27, 34, 35),
}

EXPECTED_TOTAL_COUNTS = {
    Scope.REQUEST_RESET: (55, 0),
    Scope.EXACT_PLAN_PARTITIONED: (45, 10),
    Scope.GLOBAL_STAGE_DAG: (35, 20),
}

EXPECTED_SLOT_COUNTS = {
    Scope.REQUEST_RESET: {
        slot: (5, 0) for slot in EXPECTED_SLOT_ORDER
    },
    Scope.EXACT_PLAN_PARTITIONED: {
        **{slot: (4, 1) for slot in EXPECTED_SLOT_ORDER[:-1]},
        Slot.R: (5, 0),
    },
    Scope.GLOBAL_STAGE_DAG: {
        Slot.U1: (1, 4),
        Slot.U0: (1, 4),
        Slot.P1: (2, 3),
        Slot.P0: (4, 1),
        Slot.C0: (2, 3),
        Slot.C1: (4, 1),
        Slot.D: (4, 1),
        Slot.E: (4, 1),
        Slot.F: (4, 1),
        Slot.G: (4, 1),
        Slot.R: (5, 0),
    },
}

EXPECTED_GROUP_COUNTS = {
    Scope.REQUEST_RESET: {
        "U": (10, 0),
        "P": (10, 0),
        "C": (10, 0),
        "D": (5, 0),
        "E": (5, 0),
        "F": (5, 0),
        "G": (5, 0),
        "R": (5, 0),
    },
    Scope.EXACT_PLAN_PARTITIONED: {
        "U": (8, 2),
        "P": (8, 2),
        "C": (8, 2),
        "D": (4, 1),
        "E": (4, 1),
        "F": (4, 1),
        "G": (4, 1),
        "R": (5, 0),
    },
    Scope.GLOBAL_STAGE_DAG: {
        "U": (2, 8),
        "P": (6, 4),
        "C": (6, 4),
        "D": (4, 1),
        "E": (4, 1),
        "F": (4, 1),
        "G": (4, 1),
        "R": (5, 0),
    },
}

EXPECTED_PARENTS = {
    Slot.U1: (),
    Slot.U0: (Slot.U1,),
    Slot.P1: (),
    Slot.P0: (Slot.P1,),
    Slot.C0: (),
    Slot.C1: (Slot.C0,),
    Slot.D: (Slot.U0, Slot.P0, Slot.C0, Slot.C1),
    Slot.E: (Slot.D,),
    Slot.F: (Slot.D,),
    Slot.G: (Slot.C0, Slot.C1),
    Slot.R: EXPECTED_SLOT_ORDER[:-1],
}

EXPECTED_STAGE1_CONE = (
    Slot.P1,
    Slot.P0,
    Slot.C1,
    Slot.D,
    Slot.E,
    Slot.F,
    Slot.G,
    Slot.R,
)

EXPECTED_STAGE0_CONE = (
    Slot.P0,
    Slot.C0,
    Slot.C1,
    Slot.D,
    Slot.E,
    Slot.F,
    Slot.G,
    Slot.R,
)

EXPECTED_V0047_RESULT_ID = (
    "9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42"
)
EXPECTED_FINAL_V3_MODEL_ID = (
    "a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315"
)
EXPECTED_GRAY_PLAN_IDS = (
    "0a90dfe57c48c76e917b80b546242975f43219b310ccff238bea00bae19ad1eb",
    "125090d288cddb9a5bf42bcfc77ca406b8474d4f3091c0643fb4c3b8de9b21af",
    "88d24a71393c598fba0de332ee8662a23c6532f34c856763d54fcb88ca296841",
    "81e44a708a6b80c43ba4c9cef4254144165cc84f235a649054e7f1158d5b9a73",
)

EXPECTED_LOWER_TERM_NAMES = {
    Slot.U1: ("formula_id", "return_bound_proof_id", "reward_weights_digest"),
    Slot.U0: ("formula_id", "return_bound_proof_id", "reward_weights_digest"),
    Slot.P1: ("formula_id", "return_bound_proof_id", "reward_weights_digest"),
    Slot.P0: ("formula_id", "return_bound_proof_id", "reward_weights_digest"),
    Slot.C0: ("formula_id", "initial_distribution_digest"),
    Slot.C1: ("formula_id",),
    Slot.D: (
        "formula_id",
        "initial_distribution_digest",
        "return_bound_proof_id",
        "reward_weights_digest",
    ),
    Slot.E: ("formula_id", "normalized_regret_tolerance"),
    Slot.F: ("formula_id", "risk_tolerance"),
    Slot.G: ("formula_id",),
}

EXPECTED_LOWER_RESULT_SEMANTICS = {
    Slot.U1: "STAGE_LOCAL_UNRESTRICTED_BELLMAN_T1",
    Slot.U0: "STAGE_LOCAL_UNRESTRICTED_BELLMAN_T0",
    Slot.P1: "STAGE_LOCAL_FIXED_POLICY_BELLMAN_T1",
    Slot.P0: "STAGE_LOCAL_FIXED_POLICY_BELLMAN_T0",
    Slot.C0: "STAGE_LOCAL_FORWARD_REACHABILITY_T0",
    Slot.C1: "STAGE_LOCAL_FORWARD_REACHABILITY_T1",
    Slot.D: "ROOT_SUPPORT_VALUE_RISK_METRICS",
    Slot.E: "REGRET_THRESHOLD_VERDICT",
    Slot.F: "RISK_THRESHOLD_VERDICT",
    Slot.G: "EXTERNAL_COVERAGE_VERDICT",
}


def _execution_for_scope(result, scope):
    return {
        Scope.REQUEST_RESET: result.request_reset_execution,
        Scope.EXACT_PLAN_PARTITIONED: result.exact_plan_partitioned_execution,
        Scope.GLOBAL_STAGE_DAG: result.global_stage_dag_execution,
    }[scope]


def _slot_counts(execution):
    return {
        slot: (
            sum(
                item.logical_slot is slot and item.outcome is Outcome.COMPUTED
                for item in execution.resolutions
            ),
            sum(
                item.logical_slot is slot and item.outcome is Outcome.REUSED
                for item in execution.resolutions
            ),
        )
        for slot in EXPECTED_SLOT_ORDER
    }


def _group_counts(work):
    return {
        item.family: (item.computed, item.reused) for item in work.grouped_counts
    }


def _resolution(execution, receipt, slot):
    resolution_ids = set(receipt.resolution_ids)
    return next(
        item
        for item in execution.resolutions
        if item.resolution_id in resolution_ids and item.logical_slot is slot
    )


def _entry(execution, resolution):
    return next(
        item for item in execution.entry_catalogue if item.entry_id == resolution.entry_id
    )


@pytest.fixture(scope="module")
def h2_temporal_contract():
    parent = multistep_contract_fixture.__wrapped__()
    result = temporal_module.run_lmb_h2_temporal_incremental_proof_dag_control_v1(
        parent["log"],
        parent["profile"],
        parent["authority"],
        parent["result"],
    )
    return {**parent, "source_result": parent["result"], "h2_temporal_result": result}


def test_production_api_is_four_input_and_forbidden_authorities_are_never_called(
    h2_temporal_contract, monkeypatch
) -> None:
    contract = h2_temporal_contract
    runner = temporal_module.run_h2_temporal_incremental_proof_dag_v1
    assert tuple(inspect.signature(runner).parameters) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "source_result",
    )
    assert not {
        "kernel",
        "promotion",
        "legacy_audit",
        "ground_optimizer",
        "whole_horizon_execution",
        "expected_manifest",
        "plans",
    } & set(inspect.signature(runner).parameters)

    def forbidden(*args, **kwargs):
        raise AssertionError("H2 production path opened a forbidden authority")

    monkeypatch.setattr(audit_module, "_audit_verified_partial_model_v1", forbidden)
    monkeypatch.setattr(LMBKernel, "actions", forbidden)
    monkeypatch.setattr(LMBKernel, "step", forbidden)
    monkeypatch.setattr(LMBKernel, "search", forbidden, raising=False)
    monkeypatch.setattr(family_module, "run_cold_direct_h1_baseline_v1", forbidden)
    monkeypatch.setattr(
        whole_horizon_module,
        "run_identity_bound_incremental_proof_dag_family_v1",
        forbidden,
    )
    for name in ("_compute_u", "_compute_p", "_compute_c", "_compute_d", "_materialize_root"):
        monkeypatch.setattr(whole_horizon_module, name, forbidden)
    monkeypatch.setattr(multistep_module, "canonical_lmb_query_kernel_v1", forbidden)

    replay = runner(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["source_result"],
    )
    expected = contract["h2_temporal_result"].global_stage_dag_execution
    assert type(replay) is temporal_module.H2TemporalProofDAGExecutionV1
    assert replay.to_document() == expected.to_document()


def test_protocol_freezes_four_plan_gray_order_and_five_request_roles(
    h2_temporal_contract,
) -> None:
    execution = h2_temporal_contract["h2_temporal_result"].global_stage_dag_execution
    protocol = execution.protocol
    source = h2_temporal_contract["source_result"]
    assert source.result_id == EXPECTED_V0047_RESULT_ID
    assert source.final_overlay_build.model.model_id == EXPECTED_FINAL_V3_MODEL_ID
    assert protocol.source_result_id == EXPECTED_V0047_RESULT_ID
    assert protocol.source_final_model_id == EXPECTED_FINAL_V3_MODEL_ID
    assert tuple(
        item.contingent_plan.plan_id for item in protocol.gray_plans
    ) == EXPECTED_GRAY_PLAN_IDS
    signatures = tuple(
        item.stage_assignment_ids for item in protocol.gray_plans
    )
    assert len(signatures) == 4
    assert len(set(signatures)) == 4
    assert all(len(item) == 2 for item in signatures)
    changed = tuple(
        tuple(index for index in range(2) if left[index] != right[index])
        for left, right in zip(signatures, signatures[1:])
    )
    assert changed == ((1,), (0,), (1,))
    assert tuple(item.request.role for item in execution.request_receipts) == (
        Role.CANDIDATE_RANKING_AUDIT,
        Role.CANDIDATE_RANKING_AUDIT,
        Role.CANDIDATE_RANKING_AUDIT,
        Role.CANDIDATE_RANKING_AUDIT,
        Role.INDEPENDENT_SELECTED_PLAN_CERTIFICATE,
    )
    assert tuple(item.request.request_index for item in execution.request_receipts) == (
        1, 2, 3, 4, 5
    )


def test_expected_manifest_is_preregistered_and_exact(h2_temporal_contract) -> None:
    result = h2_temporal_contract["h2_temporal_result"]
    manifests = tuple(
        _execution_for_scope(result, scope).expected_reuse_manifest for scope in Scope
    )
    assert all(type(item) is temporal_module.H2TemporalExpectedReuseManifestV1 for item in manifests)
    assert all(item.to_document() == manifests[0].to_document() for item in manifests[1:])
    manifest = manifests[0]
    assert manifest.schedule_codes == ("A0A0", "A0A1", "A1A1", "A1A0")
    assert manifest.selected_request_binding == (
        "WINNER_OF_FROZEN_V0047_NUMERIC_SEMANTIC_RULE"
    )
    assert manifest.frozen_before_arithmetic is True
    assert manifest.post_run_actuals_observed is False
    computed = Outcome.COMPUTED.value
    reused = Outcome.REUSED.value
    assert manifest.expected_outcomes == (
        (Scope.REQUEST_RESET.value, (tuple(computed for _ in EXPECTED_SLOT_ORDER),) * 5),
        (
            Scope.EXACT_PLAN_PARTITIONED.value,
            (
                *(tuple(computed for _ in EXPECTED_SLOT_ORDER) for _ in range(4)),
                tuple(reused for _ in EXPECTED_SLOT_ORDER[:-1]) + (computed,),
            ),
        ),
        (
            Scope.GLOBAL_STAGE_DAG.value,
            (
                tuple(computed for _ in EXPECTED_SLOT_ORDER),
                tuple(
                    computed if slot in EXPECTED_STAGE1_CONE else reused
                    for slot in EXPECTED_SLOT_ORDER
                ),
                tuple(
                    computed if slot in EXPECTED_STAGE0_CONE else reused
                    for slot in EXPECTED_SLOT_ORDER
                ),
                tuple(
                    computed
                    if slot in tuple(
                        item for item in EXPECTED_STAGE1_CONE if item is not Slot.P1
                    )
                    else reused
                    for slot in EXPECTED_SLOT_ORDER
                ),
                tuple(computed if slot is Slot.R else reused for slot in EXPECTED_SLOT_ORDER),
            ),
        ),
    )
    assert manifest.expected_prefix_computes == tuple(
        (scope.value, EXPECTED_PREFIX_COMPUTES[scope]) for scope in Scope
    )


def test_eleven_slot_topology_has_backward_bellman_and_forward_coverage_edges(
    h2_temporal_contract,
) -> None:
    execution = h2_temporal_contract["h2_temporal_result"].global_stage_dag_execution
    for receipt in execution.request_receipts:
        by_slot = {
            slot: _resolution(execution, receipt, slot) for slot in EXPECTED_SLOT_ORDER
        }
        assert tuple(by_slot) == EXPECTED_SLOT_ORDER
        for slot in EXPECTED_SLOT_ORDER:
            entry = _entry(execution, by_slot[slot])
            assert entry.key.ordered_parent_entry_ids == tuple(
                _entry(execution, by_slot[parent]).entry_id
                for parent in EXPECTED_PARENTS[slot]
            )
    assert EXPECTED_PARENTS[Slot.P0] == (Slot.P1,)
    assert EXPECTED_PARENTS[Slot.C1] == (Slot.C0,)
    assert EXPECTED_PARENTS[Slot.P1] == ()
    assert EXPECTED_PARENTS[Slot.C0] == ()


def test_three_arms_have_exact_totals_prefixes_slots_and_grouped_counts(
    h2_temporal_contract,
) -> None:
    result = h2_temporal_contract["h2_temporal_result"]
    for scope in Scope:
        execution = _execution_for_scope(result, scope)
        work = execution.aggregate_work
        assert execution.cache_scope is scope
        assert len(execution.request_receipts) == 5
        assert len(execution.resolutions) == 55
        assert (work.computed, work.reused) == EXPECTED_TOTAL_COUNTS[scope]
        assert tuple(item.computed for item in execution.prefixes) == (
            EXPECTED_PREFIX_COMPUTES[scope]
        )
        assert tuple(item.computed + item.reused for item in execution.prefixes) == (
            11, 22, 33, 44, 55
        )
        assert _slot_counts(execution) == EXPECTED_SLOT_COUNTS[scope]
        assert _group_counts(work) == EXPECTED_GROUP_COUNTS[scope]


def test_stage_change_cones_and_historical_suffix_reuse_are_exact(
    h2_temporal_contract,
) -> None:
    execution = h2_temporal_contract["h2_temporal_result"].global_stage_dag_execution
    closures = execution.plan_change_closures
    assert len(closures) == 5
    assert closures[0].changed_time_indices == (0, 1)
    assert closures[0].affected_slots == EXPECTED_SLOT_ORDER
    assert closures[1].changed_time_indices == (1,)
    assert closures[1].affected_slots == EXPECTED_STAGE1_CONE
    assert closures[2].changed_time_indices == (0,)
    assert closures[2].affected_slots == EXPECTED_STAGE0_CONE
    assert closures[3].changed_time_indices == (1,)
    assert closures[3].affected_slots == EXPECTED_STAGE1_CONE
    assert closures[4].changed_time_indices == (0,)
    assert closures[4].affected_slots == EXPECTED_STAGE0_CONE

    first, _, third, fourth, selected = execution.request_receipts
    first_p1 = _resolution(execution, first, Slot.P1)
    third_p1 = _resolution(execution, third, Slot.P1)
    fourth_p1 = _resolution(execution, fourth, Slot.P1)
    fourth_p0 = _resolution(execution, fourth, Slot.P0)
    assert fourth_p1.outcome is Outcome.REUSED
    assert fourth_p1.node_key_id == first_p1.node_key_id
    assert fourth_p1.node_key_id != third_p1.node_key_id
    assert fourth_p0.outcome is Outcome.COMPUTED
    assert fourth_p0.node_key_id not in {
        _resolution(execution, item, Slot.P0).node_key_id
        for item in execution.request_receipts[:3]
    }
    assert all(
        _resolution(execution, selected, slot).outcome is Outcome.REUSED
        for slot in EXPECTED_SLOT_ORDER[:-1]
    )
    assert _resolution(execution, selected, Slot.R).outcome is Outcome.COMPUTED


def test_selected_certificate_shares_lower_nodes_but_has_proposal_bound_root(
    h2_temporal_contract,
) -> None:
    execution = h2_temporal_contract["h2_temporal_result"].global_stage_dag_execution
    candidate = execution.request_receipts[0]
    selected = execution.request_receipts[4]
    assert candidate.request.contingent_plan_id == selected.request.contingent_plan_id
    assert candidate.request.planner_result_id is None
    assert selected.request.planner_result_id == execution.plan_proposal.result_id
    assert tuple(
        _resolution(execution, candidate, slot).node_key_id
        for slot in EXPECTED_SLOT_ORDER[:-1]
    ) == tuple(
        _resolution(execution, selected, slot).node_key_id
        for slot in EXPECTED_SLOT_ORDER[:-1]
    )
    candidate_root = _resolution(execution, candidate, Slot.R)
    selected_root = _resolution(execution, selected, Slot.R)
    assert candidate_root.node_key_id != selected_root.node_key_id
    selected_root_terms = dict(_entry(execution, selected_root).key.identity_terms)
    assert selected_root_terms["planner_result_id"] == execution.plan_proposal.result_id
    assert selected_root_terms["request_id"] == selected.request.request_id
    assert selected_root_terms["role"] == Role.INDEPENDENT_SELECTED_PLAN_CERTIFICATE.value


def test_five_roots_are_byte_identical_to_legacy_audits(h2_temporal_contract) -> None:
    result = h2_temporal_contract["h2_temporal_result"]
    assert len(result.legacy_audit_matches) == 5
    assert all(item.exact_document_match for item in result.legacy_audit_matches)
    execution = result.global_stage_dag_execution
    assert len(execution.request_receipts[:4]) == 4
    assert execution.request_receipts[4].audit_result.to_document() == (
        execution.request_receipts[0].audit_result.to_document()
    )
    assert execution.plan_proposal.selected_plan is not None
    assert execution.plan_proposal.selected_plan.plan_id == EXPECTED_GRAY_PLAN_IDS[0]
    assert execution.plan_proposal.selected_plan.plan_id == (
        execution.request_receipts[4].audit_result.contingent_plan_id
    )


def test_threshold_bound_rows_and_root_only_fields_cannot_sink_below_root(
    h2_temporal_contract,
) -> None:
    execution = h2_temporal_contract["h2_temporal_result"].global_stage_dag_execution
    lower_entries = tuple(
        item for item in execution.entry_catalogue if item.key.slot is not Slot.R
    )
    assert lower_entries
    assert all(item.threshold_bound_v1_row_count == 0 for item in lower_entries)
    assert all(
        item.threshold_bound_v1_row_count > 0
        for item in execution.entry_catalogue
        if item.key.slot is Slot.R
    )
    forbidden_names = {
        "thresholds_id",
        "role",
        "planner_result_id",
        "request_id",
        "plan_id",
    }
    for entry in lower_entries:
        assert not forbidden_names & {name for name, _ in entry.key.identity_terms}
        assert tuple(name for name, _ in entry.key.identity_terms) == (
            EXPECTED_LOWER_TERM_NAMES[entry.key.slot]
        )
        assert entry.result_semantics == EXPECTED_LOWER_RESULT_SEMANTICS[entry.key.slot]

    victim = lower_entries[0]
    with pytest.raises(InvariantViolation):
        replace(victim, threshold_bound_v1_row_count=1)
    with pytest.raises(InvariantViolation):
        replace(
            victim.key,
            identity_terms=tuple(
                sorted((*victim.key.identity_terms, ("thresholds_id", "0" * 64)))
            ),
        )
    bad_semantics = replace(victim, result_semantics="UNREGISTERED_LOWER_RESULT")
    with pytest.raises(InvariantViolation):
        replace(
            execution.arm,
            entry_catalogue=tuple(
                bad_semantics if item.entry_id == victim.entry_id else item
                for item in execution.entry_catalogue
            ),
        )


def test_cache_trace_topology_time_domain_and_owner_attacks_fail_closed(
    h2_temporal_contract,
) -> None:
    execution = h2_temporal_contract["h2_temporal_result"].global_stage_dag_execution
    require = temporal_module.require_h2_temporal_proof_dag_execution_v1
    with pytest.raises(InvariantViolation):
        require(copy.copy(execution))

    def reject_arm(**changes):
        with pytest.raises(InvariantViolation):
            replace(execution.arm, **changes)

    first_receipt = execution.request_receipts[0]
    first_group = execution.resolutions[:11]
    fake_state = hashlib.sha256(b"forged-h2-cache-state").hexdigest()
    reject_arm(
        resolutions=(
            replace(first_group[0], pre_cache_state_id=fake_state),
            *execution.resolutions[1:],
        )
    )
    reject_arm(
        resolutions=(
            replace(first_group[0], post_cache_state_id=fake_state),
            *execution.resolutions[1:],
        )
    )
    reject_arm(
        resolutions=(
            replace(
                first_group[0],
                outcome=Outcome.REUSED,
                post_cache_state_id=first_group[0].pre_cache_state_id,
            ),
            *execution.resolutions[1:],
        )
    )
    reject_arm(
        request_receipts=(
            execution.request_receipts[1],
            execution.request_receipts[0],
            *execution.request_receipts[2:],
        )
    )
    reject_arm(
        resolutions=(
            execution.resolutions[1],
            execution.resolutions[0],
            *execution.resolutions[2:],
        )
    )

    p0 = next(item for item in execution.entry_catalogue if item.key.slot is Slot.P0)
    with pytest.raises(InvariantViolation):
        replace(p0.key, ordered_parent_entry_ids=())
    with pytest.raises(InvariantViolation):
        replace(p0.key, time_index=1)
    with pytest.raises(InvariantViolation):
        replace(p0.key, slot=Slot.P1)

    # Appending an existing key with changed result is an overwrite, not a second proof.
    overwritten = replace(p0, result_digest=hashlib.sha256(b"overwrite").hexdigest())
    reject_arm(entry_catalogue=(*execution.entry_catalogue, overwritten))

    d_entry = next(item for item in execution.entry_catalogue if item.key.slot is Slot.D)
    reordered_d = replace(
        d_entry,
        key=replace(
            d_entry.key,
            ordered_parent_entry_ids=tuple(reversed(d_entry.key.ordered_parent_entry_ids)),
        ),
    )
    reject_arm(
        entry_catalogue=tuple(
            reordered_d if item.entry_id == d_entry.entry_id else item
            for item in execution.entry_catalogue
        )
    )

    assert len(temporal_module.DOMAIN_TAGS) == len(set(temporal_module.DOMAIN_TAGS.values()))
    wrong_domain_id = whole_horizon_module._content_id(
        "node_key", {"foreign_h2_node_key_id": p0.key.node_key_id}
    )
    assert wrong_domain_id != p0.key.node_key_id
    p0_resolution_index = next(
        index
        for index, item in enumerate(execution.resolutions)
        if item.request_id == first_receipt.request.request_id
        and item.logical_slot is Slot.P0
    )
    wrong_domain_resolution = replace(
        execution.resolutions[p0_resolution_index], node_key_id=wrong_domain_id
    )
    wrong_domain_resolutions = tuple(
        wrong_domain_resolution if index == p0_resolution_index else item
        for index, item in enumerate(execution.resolutions)
    )
    reject_arm(resolutions=wrong_domain_resolutions)


def test_claim_boundary_and_v0047_v0051_sources_remain_locked(
    h2_temporal_contract,
) -> None:
    result = h2_temporal_contract["h2_temporal_result"]
    semantics = result.global_stage_dag_execution.semantics
    assert result.registered_h2_stage_local_bellman_recurrence_claimed is True
    assert result.general_horizon_incremental_recurrence_claimed is False
    assert result.generic_h_gt_1_recurrence_claimed is False
    assert result.horizon_greater_than_two_claimed is False
    assert result.cross_query_h2_persistence_claimed is False
    assert result.changed_threshold_or_rho_incremental_claimed is False
    assert result.changed_model_incremental_claimed is False
    assert result.changed_reward_incremental_claimed is False
    assert result.closed_loop_local_overlay_invalidation_claimed is False
    assert result.general_cross_query_incremental_proof_claimed is False
    assert result.reward_or_model_epoch_incremental_claimed is False
    assert result.persistent_cache_claimed is False
    assert result.sample_tax_operator_claimed is False
    assert result.sample_reduction_claimed is False
    assert result.total_work_or_wallclock_reduction_claimed is False
    assert result.sample_efficiency_claimed is False
    assert result.workload_economics_claimed is False
    assert result.learned_or_partial_dynamics_claimed is False
    assert result.cross_domain_generalization_claimed is False
    assert result.official_execution_allowed is False
    assert result.official_scalar_cost is None
    assert result.official_N_break_even is None
    assert result.workload_economics_gate == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert result.counter_completeness_gate == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert result.sample_efficiency_gate == "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    with pytest.raises(InvariantViolation):
        replace(result, sample_efficiency_claimed=True)

    assert semantics.multistep_source_sha256 == "d335b509311f6d87a6e2106d1090580f3c7c4cca8cd4eaa4209fff4038e54845"
    assert semantics.partial_model_planner_source_sha256 == "b676c4f91d18ea9406ef1101d7072baccb519a05176496ccf6a867cedb6d4f7d"
    assert semantics.predecessor_incremental_source_sha256 == "f67a5d7fd47eddccca6124c859bf636230f76b228d37dcc399d8e3ce7dbfec6b"
    assert hashlib.sha256(Path(multistep_module.__file__).read_bytes()).hexdigest() == semantics.multistep_source_sha256
    assert hashlib.sha256(Path(planner_module.__file__).read_bytes()).hexdigest() == semantics.partial_model_planner_source_sha256
    assert hashlib.sha256(Path(whole_horizon_module.__file__).read_bytes()).hexdigest() == semantics.predecessor_incremental_source_sha256
    assert semantics.whole_horizon_v0051_helpers_allowed is False


def test_canonical_v0052_identities_are_frozen(h2_temporal_contract) -> None:
    result = h2_temporal_contract["h2_temporal_result"]
    execution = result.global_stage_dag_execution
    actual = {
        "manifest": execution.expected_reuse_manifest.manifest_id,
        "protocol": execution.protocol.protocol_id,
        "semantics": execution.semantics.semantics_id,
        "global_cache": execution.final_cache.cache_id,
        "global_execution": execution.execution_id,
        "result": result.result_id,
    }
    assert actual == {
        "manifest": "e25068045e4585b9d7687fa2d935f2bf5bb8247fe689f6c06405113b34f4138d",
        "protocol": "3f29147af4b527830d73b52751edaeef214244a1cac9b8d0c45493edd28bb5dc",
        "semantics": "d05a05a5b0cee242f586fdadfed64df7082803d9055988fc22b5a521959f5849",
        "global_cache": "79fa6ad025eff7f286d1a690b1a5f9ec28f4363b3105dfec3d0dd33ef32e3f6c",
        "global_execution": "922a0c02e2ff4218a973280c090745bb34d1fd0212b729563229dffd90dd0916",
        "result": "6b6ca2b9925c54845f7bf9930a947bcaac2c0541db339594509218c323186618",
    }


def test_full_independent_v0052_replay_is_byte_identical(h2_temporal_contract) -> None:
    contract = h2_temporal_contract
    verified = temporal_module.verify_lmb_h2_temporal_incremental_proof_dag_control_v1(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["synthesis"],
        contract["thresholds"],
        contract["base_proposal"],
        contract["failed_audit"],
        contract["kernel"],
        contract["source_result"],
        contract["h2_temporal_result"],
    )
    assert verified.to_document() == contract["h2_temporal_result"].to_document()
