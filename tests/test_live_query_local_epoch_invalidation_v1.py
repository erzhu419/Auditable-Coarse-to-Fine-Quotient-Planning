"""V0-053 live query-local epoch-invalidation regressions."""

import copy
from dataclasses import replace
import hashlib
import inspect
from pathlib import Path

import pytest

import acfqp.h2_temporal_incremental_proof_dag_v1 as temporal_module
import acfqp.live_query_local_epoch_invalidation_v1 as live_module
import acfqp.multistep_query_refinement_v1 as multistep_module
import acfqp.observation_partial_rapm_v1 as observation_model_module
import acfqp.partial_model_planner_v1 as planner_module
import acfqp.partial_sound_audit_v1 as audit_module
from acfqp.h2_temporal_incremental_proof_dag_v1 import (
    H2TemporalProofSlot as Slot,
)
from acfqp.observed_typed_coordinate_synthesis_v1 import (
    synthesize_observed_lmb_partial_rapm_v1,
)
from acfqp.partial_model_planner_v1 import (
    propose_partial_model_plan_from_observed_synthesis_v2,
)
from acfqp.partial_sound_audit_v1 import (
    PartialAuditOutcome,
    audit_partial_fixed_plan_from_observed_synthesis_v2,
)
from tests.test_observation_partial_rapm_v1 import (
    observation_contract as observation_contract_fixture,
)
from tests.test_partial_sound_audit_v1 import _thresholds


EXPECTED_FIRST_MODEL_ID = (
    "e3d550b7d46b516bd443881e14ade00b8a1cc673f141039d09dc585fa2b28fba"
)
EXPECTED_FINAL_MODEL_ID = (
    "a18a29a1c1bd3433ef7ace6d99c67a594a0d587b6b0c2889f71022eaa7437315"
)
EXPECTED_FIRST_PROPOSAL_ID = (
    "b5db44c042eaa656980f942430c2fee6eda6fcf6ec8c0a1af1142b723ec006e4"
)
EXPECTED_FINAL_PROPOSAL_ID = (
    "fb23e41d80f2597622443fe71ac57516ed12298f66a2ad2e56d4c6c8344a8acb"
)
EXPECTED_FIRST_PLAN_ID = (
    "54ae40c2034d85fbe3b3e95dd1a211e17e2f91f4b996365d64b4a520f8caea5e"
)
EXPECTED_FINAL_PLAN_ID = (
    "0a90dfe57c48c76e917b80b546242975f43219b310ccff238bea00bae19ad1eb"
)
EXPECTED_FIRST_AUDIT_ID = (
    "fe94690ae979f233bcb2dfdeeb9516ae1b0c1c21dc3e5f3f2407fd558c50f078"
)
EXPECTED_FINAL_AUDIT_ID = (
    "81f379b9485d1da2aaf56fd20ff75d5c45c8ac4b870cc6e52b795ef6896e9529"
)
EXPECTED_ROUND_TWO_REQUEST_ID = (
    "dc79dda993650f03b335217fbdf98cc10449bb79f7374d0440258996b84b1ccf"
)
EXPECTED_V0047_RESULT_ID = (
    "9a3691831b8103d1523333f50b302a5f099dee9d1b8790a893e5998810866d42"
)
EXPECTED_SEMANTICS_ID = (
    "17a7fb36b05d6dcf9ed319cae706a5a5b0fd496359b66348cc444ea16955f264"
)
EXPECTED_DELTA_ID = (
    "40e6447cfff4526e4b17f4e381bf8067f6dec946a1d3e655a3380c780de053fa"
)
EXPECTED_ORDERING_ID = (
    "e7e0a08ecf6cf5ef04fd990f73065955e6d4412aec5fb474aff1e4660f391da2"
)
EXPECTED_INVALIDATION_ID = (
    "a9657e12ebd46cee061263205d103ff4b82dfd557b3923a843ef00c1b841668c"
)
EXPECTED_CROSS_ARM_ID = (
    "5e8c2d23cfcf96c9d810fac1af3069b83eea2caa1a191c6b02e546a29bf21b56"
)
EXPECTED_RESULT_ID = (
    "5e46f0eda3f6d9c96e955315034829913dc248d09ed1a73ca8384d4cbcd65d44"
)
EXPECTED_STAGE_IDS = (
    "1b67b0e8457e166b32b1ca831393010371ccc86abed2df04287122b6ebe4dfee",
    "f06ace72dc968d920d56fb6f236b5ff964e62c653787ddabdd5e95bb8e4cf9d4",
)
EXPECTED_CHANGED_ROW_IDS = (
    "01f7fb9b87d8ea01b7d57372f250a45dd24bb159f5d833155d8909817a813ad5",
    "2b7caa592afcb07bf3c574b28fd477c167ff69778f39f87b814b306ca3149233",
    "559b1ed86633296b44a161f6935e3eff1d15f644a1a7d4d21db0d7960c955e41",
    "663563cac071a2183ef6a55c502f3d6ff3c8d03f44cdfa99e9c09dce1753b0cf",
    "a7df337de278e35775d71777a00bbd055f113cebd22c6524580860b5d3663633",
    "b1c7998915a60b28bb9a6e498344b57fe35135f4e41b889e87d8dd8065b5ec41",
    "cb190d591f7d18ada5d634de949869f9d535f9991a9b3614b88394501654ba3e",
    "cb3abe034c65e8faac6917f809b571aa105a975ef6b8a44a653ec236ac1b76ef",
    "e53d57a077412b956a92256c43ca556008aa82aa02bafcc9cd045afd0938d54e",
)
EXPECTED_CHANGED_REALIZATION_STATES = (
    "432e49aababf8db6ac959bbebdae6804084c480333b9524369a8ebd63b14d86e",
    "c4be1ba20a5145048808335df23a7adc5e491ddd1467f19c835e89bc94d3c67c",
    "ffc13133675a6fcd362ca3fe297bcc59a84b11a244f2a68e010cf0058a1ada5b",
)
EXPECTED_CHANGED_REALIZATION_ACTIONS = (
    "01cc79bdf454e47bbe035a0021f58ca673d4498de6cfb4c56cdfae8ee0a77ec2",
    "60c5bcf2cc70d3d9498c60e07a0c0c6df982696c784461c2707368f75e3311fc",
)
EXPECTED_PREFIX_COMPUTES = (11, 19, 27, 34, 35, 45, 53, 60, 67, 68)
EXPECTED_PREFIX_HITS = (0, 3, 6, 10, 20, 21, 24, 28, 32, 42)
EXPECTED_SLOT_COUNTS = {
    Slot.U1: (2, 8),
    Slot.U0: (2, 8),
    Slot.P1: (4, 6),
    Slot.P0: (8, 2),
    Slot.C0: (2, 8),
    Slot.C1: (8, 2),
    Slot.D: (8, 2),
    Slot.E: (8, 2),
    Slot.F: (8, 2),
    Slot.G: (8, 2),
    Slot.R: (10, 0),
}

Scope = live_module.LiveEpochCacheScope
Epoch = live_module.LiveEpochName
Outcome = live_module.LiveEpochResolutionOutcome
InvariantViolation = live_module.LiveEpochInvariantViolation
SLOT_ORDER = tuple(Slot)


def _arm(result, scope):
    return {
        Scope.REQUEST_RESET: result.request_reset_arm,
        Scope.EPOCH_RESET_GLOBAL_DAG: result.epoch_reset_global_arm,
        Scope.GLOBAL_CROSS_EPOCH_FACET_DAG: result.global_cross_epoch_facet_arm,
    }[scope]


def _resolution(arm, epoch, request_index, slot):
    offset = 0 if epoch is Epoch.FIRST else 55
    rows = arm.resolutions[
        offset + 11 * (request_index - 1): offset + 11 * request_index
    ]
    return next(item for item in rows if item.slot is slot)


def _entry(arm, resolution):
    return next(
        item for item in arm.entry_catalogue if item.entry_id == resolution.entry_id
    )


def _binding(arm, resolution):
    return next(
        item
        for item in arm.slice_bindings
        if item.binding_id == resolution.slice_binding_id
    )


def _replace_trace_resolution(
    arm,
    index,
    resolution,
    *,
    entry_catalogue=None,
    slice_bindings=None,
    epoch_post_cache_state_id=None,
):
    """Rebind enclosing receipt/execution IDs around one tampered resolution."""

    resolutions = list(arm.resolutions)
    resolutions[index] = resolution
    first_epoch = arm.first_epoch
    final_epoch = arm.final_epoch
    execution = first_epoch if index < 55 else final_epoch
    local_index = index if index < 55 else index - 55
    receipt_index, slot_index = divmod(local_index, 11)
    receipts = list(execution.request_receipts)
    receipt = receipts[receipt_index]
    receipt_resolution_ids = list(receipt.resolution_ids)
    receipt_resolution_ids[slot_index] = resolution.resolution_id
    receipts[receipt_index] = replace(
        receipt,
        resolution_ids=tuple(receipt_resolution_ids),
        root_entry_id=(
            resolution.entry_id if slot_index == 10 else receipt.root_entry_id
        ),
    )
    execution_resolution_ids = list(execution.resolution_ids)
    execution_resolution_ids[local_index] = resolution.resolution_id
    execution_kwargs = {
        "request_receipts": tuple(receipts),
        "resolution_ids": tuple(execution_resolution_ids),
    }
    if epoch_post_cache_state_id is not None:
        execution_kwargs["post_cache_state_id"] = epoch_post_cache_state_id
    execution = replace(execution, **execution_kwargs)
    return replace(
        arm,
        first_epoch=execution if index < 55 else first_epoch,
        final_epoch=execution if index >= 55 else final_epoch,
        resolutions=tuple(resolutions),
        entry_catalogue=(
            arm.entry_catalogue if entry_catalogue is None else entry_catalogue
        ),
        slice_bindings=(
            arm.slice_bindings if slice_bindings is None else slice_bindings
        ),
    )


def _slot_counts(arm):
    return {
        slot: (
            sum(
                item.slot is slot and item.outcome is Outcome.COMPUTED
                for item in arm.resolutions
            ),
            sum(
                item.slot is slot and item.outcome is Outcome.REUSED
                for item in arm.resolutions
            ),
        )
        for slot in SLOT_ORDER
    }


@pytest.fixture(scope="module")
def live_contract():
    source = observation_contract_fixture.__wrapped__()
    synthesis = synthesize_observed_lmb_partial_rapm_v1(
        source["log"], source["profile"], source["authority"]
    )
    base_model = synthesis.partial_build_result.model
    initial_state_id = source["observed_by_ground"][source["extra"]].state_id
    thresholds = _thresholds(base_model, initial_state_id, horizon=2)
    base_proposal = propose_partial_model_plan_from_observed_synthesis_v2(
        source["log"], source["profile"], source["authority"], synthesis, thresholds
    )
    assert base_proposal.selected_plan is not None
    failed_audit = audit_partial_fixed_plan_from_observed_synthesis_v2(
        source["log"],
        source["profile"],
        source["authority"],
        synthesis,
        thresholds,
        base_proposal.selected_plan,
    )
    assert failed_audit.audit_result.outcome is PartialAuditOutcome.FAILED_PROOF_FRONTIER
    kernel = multistep_module.canonical_lmb_query_kernel_v1()
    trace = []
    original_acquire = multistep_module._acquire
    original_run_epoch = live_module._run_epoch

    def traced_acquire(round_index, *args, **kwargs):
        trace.append(f"ACQUIRE_{round_index}")
        return original_acquire(round_index, *args, **kwargs)

    def traced_run_epoch(runtime, epoch, *args, **kwargs):
        execution = original_run_epoch(runtime, epoch, *args, **kwargs)
        outcome = execution.request_receipts[-1].audit_result.outcome.value
        trace.append(f"DAG_{epoch.value}_{outcome}")
        return execution

    patcher = pytest.MonkeyPatch()
    patcher.setattr(multistep_module, "_acquire", traced_acquire)
    patcher.setattr(live_module, "_run_epoch", traced_run_epoch)
    try:
        result = live_module.run_lmb_h2_live_query_local_epoch_invalidation_v1(
            source["log"],
            source["profile"],
            source["authority"],
            synthesis,
            thresholds,
            base_proposal,
            failed_audit,
            kernel,
        )
    finally:
        patcher.undo()
    return {
        **source,
        "synthesis": synthesis,
        "thresholds": thresholds,
        "base_proposal": base_proposal,
        "failed_audit": failed_audit,
        "kernel": kernel,
        "live_result": result,
        "live_trace": tuple(trace),
    }


def test_public_api_is_strictly_eight_inputs_and_verifier_is_nine() -> None:
    runner = live_module.run_lmb_h2_live_query_local_epoch_invalidation_v1
    verifier = live_module.verify_lmb_h2_live_query_local_epoch_invalidation_v1
    eight = (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "observed_synthesis_result",
        "thresholds",
        "base_plan_proposal",
        "failed_audit",
        "kernel",
    )
    assert tuple(inspect.signature(runner).parameters) == eight
    assert tuple(inspect.signature(verifier).parameters) == (*eight, "claimed_result")
    forbidden = {
        "source_result",
        "first_model",
        "final_model",
        "rows",
        "selected_plan",
        "cache",
        "closure",
        "expected_outcomes",
        "control_arm",
    }
    assert not forbidden & set(inspect.signature(runner).parameters)


def test_live_order_freezes_first_selected_failure_before_round_two_acquisition(
    live_contract,
) -> None:
    result = live_contract["live_result"]
    assert live_contract["live_trace"][:4] == (
        "ACQUIRE_1",
        "DAG_FIRST_OVERLAY_V3_FAILED_PROOF_FRONTIER",
        "ACQUIRE_2",
        "DAG_FINAL_OVERLAY_V3_CERTIFIED_FIXED_PLAN",
    )
    protocol = result.ordering_protocol
    kinds = tuple(item.event_kind for item in protocol.events)
    assert kinds[5:9] == (
        "FIRST_INDEPENDENT_SELECTED_FAILURE_FROZEN",
        "ROUND_TWO_REQUEST_DERIVED_FROM_FIRST_ROOT",
        "ROUND_TWO_NINE_ROWS_ACQUIRED",
        "FINAL_OVERLAY_EPOCH_FROZEN",
    )
    assert tuple(item.sequence_number for item in protocol.events) == tuple(range(1, 13))
    assert tuple(item.cumulative_transition_calls for item in protocol.events) == (
        0, 0, 4, 4, 4, 4, 4, 13, 13, 13, 13, 13
    )
    assert tuple(item.cumulative_boundary_catalogue_calls for item in protocol.events) == (
        0, 0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3
    )
    assert protocol.first_selected_root_precedes_round_two_request is True
    assert protocol.round_two_request_precedes_round_two_evidence is True
    assert protocol.final_epoch_follows_round_two_evidence is True


def test_canonical_epoch_proposal_plan_audit_and_source_identities(live_contract) -> None:
    result = live_contract["live_result"]
    source = result.live_multistep_result
    arm = result.global_cross_epoch_facet_arm
    first = arm.first_epoch
    final = arm.final_epoch
    assert result.semantics.semantics_id == EXPECTED_SEMANTICS_ID
    assert result.epoch_delta.delta_id == EXPECTED_DELTA_ID
    assert result.ordering_protocol.protocol_id == EXPECTED_ORDERING_ID
    assert result.invalidation_manifest.manifest_id == EXPECTED_INVALIDATION_ID
    assert arm.arm_id == EXPECTED_CROSS_ARM_ID
    assert result.result_id == EXPECTED_RESULT_ID
    assert source.result_id == EXPECTED_V0047_RESULT_ID
    assert source.first_overlay_build.model.model_id == EXPECTED_FIRST_MODEL_ID
    assert source.final_overlay_build.model.model_id == EXPECTED_FINAL_MODEL_ID
    assert source.round_two_request.request_id == EXPECTED_ROUND_TWO_REQUEST_ID
    assert first.model_id == EXPECTED_FIRST_MODEL_ID
    assert final.model_id == EXPECTED_FINAL_MODEL_ID
    assert first.plan_proposal.result_id == EXPECTED_FIRST_PROPOSAL_ID
    assert final.plan_proposal.result_id == EXPECTED_FINAL_PROPOSAL_ID
    assert first.plan_proposal.selected_plan.plan_id == EXPECTED_FIRST_PLAN_ID
    assert final.plan_proposal.selected_plan.plan_id == EXPECTED_FINAL_PLAN_ID
    assert first.selected_plan_audit.result_id == EXPECTED_FIRST_AUDIT_ID
    assert final.selected_plan_audit.result_id == EXPECTED_FINAL_AUDIT_ID
    assert tuple(
        item.stage_id for item in first.plan_proposal.selected_plan.stages
    ) == EXPECTED_STAGE_IDS
    assert tuple(
        item.stage_id for item in final.plan_proposal.selected_plan.stages
    ) == EXPECTED_STAGE_IDS
    assert tuple(
        item.to_document() for item in first.plan_proposal.selected_plan.stages
    ) == tuple(
        item.to_document() for item in final.plan_proposal.selected_plan.stages
    )
    assert first.plan_proposal.selected_semantic_tie_break_key == (
        0, 1, 0, 1, 0, 1, 0, 1
    )
    assert (
        first.plan_proposal.selected_semantic_tie_break_key
        == final.plan_proposal.selected_semantic_tie_break_key
    )
    assert first.request_receipts[-1].audit_result.outcome is (
        PartialAuditOutcome.FAILED_PROOF_FRONTIER
    )
    frontier = first.request_receipts[-1].audit_result.failed_proof_frontier
    assert frontier is not None
    assert (frontier.earliest_time_index, frontier.remaining_horizon) == (1, 1)
    assert final.request_receipts[-1].audit_result.outcome is (
        PartialAuditOutcome.CERTIFIED_FIXED_PLAN
    )
    bounds = final.request_receipts[-1].audit_result.robust_bounds
    assert (
        bounds.policy_reward_lower,
        bounds.policy_reward_upper,
        bounds.policy_failure_lower,
        bounds.policy_failure_upper,
        bounds.normalized_distribution_regret,
        bounds.external_coverage_certified,
    ) == (1, 1, 0, 0, 0, True)


def test_exact_nine_row_six_realization_epoch_delta_and_ground_accounting(
    live_contract,
) -> None:
    result = live_contract["live_result"]
    delta = result.epoch_delta
    source = result.live_multistep_result
    assert delta.changed_ground_row_ids == EXPECTED_CHANGED_ROW_IDS
    assert delta.changed_realization_pairs == tuple(
        sorted(
            (state_id, action_id)
            for state_id in EXPECTED_CHANGED_REALIZATION_STATES
            for action_id in EXPECTED_CHANGED_REALIZATION_ACTIONS
        )
    )
    assert len(delta.unchanged_ground_row_ids) == 11
    assert delta.direct_changed_slots == ("U1", "U0", "P1", "P0", "C1")
    assert delta.affected_descendant_slots == ("D", "E", "F", "G", "R")
    assert delta.reusable_slots == ("C0",)
    assert (
        delta.first_observed_count,
        delta.first_missing_count,
        delta.final_observed_count,
        delta.final_missing_count,
    ) == (11, 9, 20, 0)
    first_rows = {
        item.ground_row_id: item for item in source.first_overlay_build.model.ground_rows
    }
    final_rows = {
        item.ground_row_id: item for item in source.final_overlay_build.model.ground_rows
    }
    assert set(first_rows) == set(final_rows)
    assert all(
        first_rows[row_id].status.value == "MISSING_VACUOUS"
        and final_rows[row_id].status.value == "OBSERVED_SINGLETON"
        for row_id in EXPECTED_CHANGED_ROW_IDS
    )
    assert all(
        first_rows[row_id].to_document() == final_rows[row_id].to_document()
        for row_id in delta.unchanged_ground_row_ids
    )
    assert sum(not item.failure for item in source.round_two_bundle.evidence) == 3
    assert sum(item.failure for item in source.round_two_bundle.evidence) == 6
    telemetry = source.telemetry
    assert (
        telemetry.round_one_exact_kernel_queries,
        telemetry.boundary_action_catalogue_queries,
        telemetry.round_two_exact_kernel_queries,
        telemetry.cumulative_exact_kernel_queries,
        telemetry.exact_kernel_calls_during_planning_and_audit,
        telemetry.direct_ground_optimization_calls,
    ) == (4, 3, 9, 13, 0, 0)


def test_three_matched_arms_have_exact_totals_prefixes_and_per_slot_counts(
    live_contract,
) -> None:
    result = live_contract["live_result"]
    expected = {
        Scope.REQUEST_RESET: (110, 0),
        Scope.EPOCH_RESET_GLOBAL_DAG: (70, 40),
        Scope.GLOBAL_CROSS_EPOCH_FACET_DAG: (68, 42),
    }
    for scope, totals in expected.items():
        arm = _arm(result, scope)
        assert arm.scope is scope
        assert len(arm.resolutions) == 110
        assert len(arm.first_epoch.request_receipts) == 5
        assert len(arm.final_epoch.request_receipts) == 5
        assert (arm.aggregate_work.computed, arm.aggregate_work.reused) == totals
        assert tuple(
            item.request.schedule_code for item in arm.first_epoch.request_receipts[:4]
        ) == ("A0A0", "A0A1", "A1A1", "A1A0")
        assert tuple(
            item.request.schedule_code for item in arm.final_epoch.request_receipts[:4]
        ) == ("A0A0", "A0A1", "A1A1", "A1A0")
    cross = result.global_cross_epoch_facet_arm
    assert cross.prefix_computes == EXPECTED_PREFIX_COMPUTES
    assert cross.prefix_reuses == EXPECTED_PREFIX_HITS
    assert _slot_counts(cross) == EXPECTED_SLOT_COUNTS
    assert result.avoided_cross_epoch_constructions == 2
    assert (
        result.epoch_reset_global_arm.aggregate_work.computed
        - cross.aggregate_work.computed
    ) == 2


def test_c0_is_the_only_cross_epoch_entry_reuse_and_uses_two_constructions(
    live_contract,
) -> None:
    arm = live_contract["live_result"].global_cross_epoch_facet_arm
    first_c0 = {
        _resolution(arm, Epoch.FIRST, index, Slot.C0).entry_id
        for index in range(1, 6)
    }
    final_c0 = tuple(
        _resolution(arm, Epoch.FINAL, index, Slot.C0) for index in range(1, 6)
    )
    assert len(first_c0) == 2
    assert all(item.outcome is Outcome.REUSED for item in final_c0)
    assert {item.entry_id for item in final_c0} == first_c0
    assert all(
        _binding(arm, item).epoch is Epoch.FINAL
        and _entry(arm, item).key.model_slice_content_id
        in {
            _entry(arm, _resolution(arm, Epoch.FIRST, index, Slot.C0)).key.model_slice_content_id
            for index in range(1, 6)
        }
        for item in final_c0
    )
    first_non_c0 = {
        item.entry_id for item in arm.resolutions[:55] if item.slot is not Slot.C0
    }
    final_non_c0 = {
        item.entry_id for item in arm.resolutions[55:] if item.slot is not Slot.C0
    }
    assert first_non_c0.isdisjoint(final_non_c0)


def test_direct_model_facets_invalidate_u0_p0_and_c1_but_not_c0(live_contract) -> None:
    result = live_contract["live_result"]
    arm = result.global_cross_epoch_facet_arm
    changed = set(result.epoch_delta.changed_ground_row_ids)
    direct = (Slot.U1, Slot.U0, Slot.P1, Slot.P0, Slot.C1)
    for slot in direct:
        before = _resolution(arm, Epoch.FIRST, 1, slot)
        after = _resolution(arm, Epoch.FINAL, 1, slot)
        before_binding = _binding(arm, before)
        after_binding = _binding(arm, after)
        assert changed & set(before_binding.content.input_ground_row_ids)
        assert changed & set(after_binding.content.input_ground_row_ids)
        assert before_binding.content.content_id != after_binding.content.content_id
        assert before.entry_id != after.entry_id
        assert after.outcome is Outcome.COMPUTED
    before_c0 = _resolution(arm, Epoch.FIRST, 1, Slot.C0)
    after_c0 = _resolution(arm, Epoch.FINAL, 1, Slot.C0)
    before_binding = _binding(arm, before_c0)
    after_binding = _binding(arm, after_c0)
    assert not changed & set(before_binding.content.input_ground_row_ids)
    assert before_binding.content.content_id == after_binding.content.content_id
    assert before_c0.entry_id == after_c0.entry_id
    assert after_c0.outcome is Outcome.REUSED

    # D is parent-derived for invalidation, but its value computation also reads
    # the stage-zero realization on the exact initial support.  Keep that direct
    # dependency in the slice key even on this fixture where its rows do not
    # themselves change between epochs.
    for epoch in (Epoch.FIRST, Epoch.FINAL):
        direct_root = _binding(arm, _resolution(arm, epoch, 1, Slot.D)).content
        assert direct_root.facet_kind == "INITIAL_SUPPORT_DIRECT_REALIZATION_V1"
        assert direct_root.stage_assignment_id is not None
        assert direct_root.input_ground_row_ids


def test_equal_g_verdict_is_rederived_because_its_c1_parent_changed(live_contract) -> None:
    arm = live_contract["live_result"].global_cross_epoch_facet_arm
    first_g = _resolution(arm, Epoch.FIRST, 1, Slot.G)
    final_g = _resolution(arm, Epoch.FINAL, 1, Slot.G)
    first_entry = _entry(arm, first_g)
    final_entry = _entry(arm, final_g)
    assert first_entry.result_digest == final_entry.result_digest
    assert first_entry.entry_id != final_entry.entry_id
    assert first_entry.key.ordered_parent_entry_ids != (
        final_entry.key.ordered_parent_entry_ids
    )
    assert final_g.outcome is Outcome.COMPUTED


def test_slot_specific_key_parent_order_and_cache_replay_tampering_fail_closed(
    live_contract,
) -> None:
    arm = live_contract["live_result"].global_cross_epoch_facet_arm
    u1 = _entry(arm, _resolution(arm, Epoch.FIRST, 1, Slot.U1)).key
    d_resolution = _resolution(arm, Epoch.FIRST, 1, Slot.D)
    d_entry = _entry(arm, d_resolution)

    with pytest.raises(InvariantViolation):
        replace(u1, time_index=0)
    with pytest.raises(InvariantViolation):
        replace(d_entry.key, stage_assignment_id=None)
    with pytest.raises(InvariantViolation):
        replace(
            d_entry.key,
            identity_terms=tuple(
                item
                for item in d_entry.key.identity_terms
                if item[0] != "initial_distribution_digest"
            ),
        )

    bad_d_key = replace(
        d_entry.key,
        ordered_parent_entry_ids=tuple(reversed(d_entry.key.ordered_parent_entry_ids)),
    )
    bad_d_entry = replace(d_entry, key=bad_d_key)
    bad_d_resolution = replace(
        d_resolution,
        node_key_id=bad_d_key.node_key_id,
        entry_id=bad_d_entry.entry_id,
    )
    d_index = SLOT_ORDER.index(Slot.D)
    with pytest.raises(InvariantViolation):
        _replace_trace_resolution(
            arm,
            d_index,
            bad_d_resolution,
            entry_catalogue=(*arm.entry_catalogue, bad_d_entry),
        )
    with pytest.raises(InvariantViolation):
        replace(
            arm,
            resolutions=(arm.resolutions[1], arm.resolutions[0], *arm.resolutions[2:]),
        )

    final_c0_index = 55 + SLOT_ORDER.index(Slot.C0)
    final_c0_resolution = arm.resolutions[final_c0_index]
    assert final_c0_resolution.outcome is Outcome.REUSED
    final_c0_entry = _entry(arm, final_c0_resolution)
    fake_c0_key = replace(
        final_c0_entry.key,
        identity_terms=tuple(
            (
                name,
                live_contract["live_result"].semantics.semantics_id
                if name == "initial_distribution_digest"
                else value,
            )
            for name, value in final_c0_entry.key.identity_terms
        ),
    )
    fake_c0_entry = replace(final_c0_entry, key=fake_c0_key)
    fake_c0_resolution = replace(
        final_c0_resolution,
        node_key_id=fake_c0_key.node_key_id,
        entry_id=fake_c0_entry.entry_id,
    )
    with pytest.raises(InvariantViolation):
        _replace_trace_resolution(
            arm,
            final_c0_index,
            fake_c0_resolution,
            entry_catalogue=(*arm.entry_catalogue, fake_c0_entry),
        )

    # A syntactically valid replacement hash cannot stand in for the replayed
    # append-only cache state, even at the final resolution where no following
    # pre-state would otherwise expose the substitution.
    final_resolution = arm.resolutions[-1]
    fake_cache_state_id = live_contract["live_result"].semantics.semantics_id
    bad_final_resolution = replace(
        final_resolution,
        post_cache_state_id=fake_cache_state_id,
    )
    with pytest.raises(InvariantViolation):
        _replace_trace_resolution(
            arm,
            109,
            bad_final_resolution,
            epoch_post_cache_state_id=fake_cache_state_id,
        )


def test_ordering_frontier_and_slice_provenance_tampering_fail_closed(
    live_contract,
) -> None:
    result = live_contract["live_result"]
    events = result.ordering_protocol.events
    bad_event = replace(events[0], artifact_id=events[1].artifact_id)
    bad_protocol = replace(
        result.ordering_protocol,
        events=(bad_event, *events[1:]),
    )
    with pytest.raises(InvariantViolation):
        replace(result, ordering_protocol=bad_protocol, _instance_mint=None)

    arm = result.global_cross_epoch_facet_arm
    first_resolution = arm.resolutions[0]
    first_binding = _binding(arm, first_resolution)
    bad_binding = replace(
        first_binding,
        evidence_bundle_id=result.live_multistep_result.round_two_bundle.bundle_id,
    )
    bad_resolution = replace(
        first_resolution,
        slice_binding_id=bad_binding.binding_id,
    )
    # The original binding is shared by later requests, so retain it and add
    # the forged provenance variant only for this one resolution.
    bad_bindings = (*arm.slice_bindings, bad_binding)
    bad_arm = _replace_trace_resolution(
        arm,
        0,
        bad_resolution,
        slice_bindings=bad_bindings,
    )
    with pytest.raises(InvariantViolation):
        replace(
            result,
            global_cross_epoch_facet_arm=bad_arm,
            _instance_mint=None,
        )


def test_all_ten_roots_match_independent_legacy_audits(live_contract) -> None:
    contract = live_contract
    arm = contract["live_result"].global_cross_epoch_facet_arm
    source = contract["live_result"].live_multistep_result
    for execution, build, rebase in (
        (arm.first_epoch, source.first_overlay_build, source.first_threshold_rebase),
        (arm.final_epoch, source.final_overlay_build, source.final_threshold_rebase),
    ):
        for receipt in execution.request_receipts:
            expected = audit_module._audit_verified_partial_model_v1(
                build.model,
                contract["log"],
                contract["profile"],
                contract["authority"],
                rebase.rebased_thresholds,
                receipt.request.contingent_plan,
            )
            assert receipt.audit_result.to_document() == expected.to_document()


def test_claim_gate_source_and_owner_locks_fail_closed(live_contract) -> None:
    result = live_contract["live_result"]
    assert result.registered_h2_live_query_local_epoch_invalidation_claimed is True
    assert result.live_closed_loop_claimed is True
    for name in (
        "semantic_policy_change_claimed",
        "generic_changed_model_incremental_proof_claimed",
        "generic_h_gt_1_recurrence_claimed",
        "persistent_cache_claimed",
        "cross_query_cache_claimed",
        "sample_reduction_claimed",
        "sample_efficiency_claimed",
        "total_work_reduction_claimed",
        "workload_economics_claimed",
        "learned_dynamics_claimed",
        "coordinate_invention_claimed",
        "official_execution_allowed",
    ):
        assert getattr(result, name) is False
    assert result.official_scalar_cost is None
    assert result.official_N_break_even is None
    assert result.workload_economics_gate == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert result.counter_completeness_gate == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert result.sample_efficiency_gate == "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    assert result.sample_efficiency_gate_blocks_mainline is False
    with pytest.raises(InvariantViolation):
        live_module.require_live_query_local_epoch_invalidation_result_v1(copy.copy(result))
    with pytest.raises(InvariantViolation):
        replace(result, semantic_policy_change_claimed=True)
    with pytest.raises(InvariantViolation):
        replace(
            result.epoch_delta,
            changed_ground_row_ids=result.epoch_delta.changed_ground_row_ids[:-1],
        )
    with pytest.raises(InvariantViolation):
        replace(
            result.ordering_protocol,
            events=(
                result.ordering_protocol.events[1],
                result.ordering_protocol.events[0],
                *result.ordering_protocol.events[2:],
            ),
        )
    with pytest.raises(InvariantViolation):
        replace(result.global_cross_epoch_facet_arm, prefix_computes=(0,) * 10)

    semantics = result.semantics
    assert semantics.audit_source_sha256 == live_module.EXPECTED_AUDIT_SOURCE_SHA256
    assert semantics.planner_source_sha256 == live_module.EXPECTED_PLANNER_SOURCE_SHA256
    assert semantics.multistep_source_sha256 == live_module.EXPECTED_MULTISTEP_SOURCE_SHA256
    assert semantics.temporal_source_sha256 == live_module.EXPECTED_TEMPORAL_SOURCE_SHA256
    assert semantics.observation_model_source_sha256 == (
        live_module.EXPECTED_OBSERVATION_MODEL_SOURCE_SHA256
    )
    for module, expected in (
        (audit_module, semantics.audit_source_sha256),
        (planner_module, semantics.planner_source_sha256),
        (multistep_module, semantics.multistep_source_sha256),
        (temporal_module, semantics.temporal_source_sha256),
        (observation_model_module, semantics.observation_model_source_sha256),
    ):
        assert hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() == expected


def test_independent_live_and_legacy_replay_are_byte_identical(live_contract) -> None:
    contract = live_contract
    report = live_module.verify_lmb_h2_live_query_local_epoch_invalidation_v1(
        contract["log"],
        contract["profile"],
        contract["authority"],
        contract["synthesis"],
        contract["thresholds"],
        contract["base_proposal"],
        contract["failed_audit"],
        contract["kernel"],
        contract["live_result"],
    )
    assert report.claimed_result_id == contract["live_result"].result_id
    assert report.replayed_result_id == contract["live_result"].result_id
    assert report.legacy_multistep_result_id == EXPECTED_V0047_RESULT_ID
    assert report.exact_document_match is True
    assert report.legacy_exact_document_match is True
    assert report.evaluation_lane_only is True
    assert report.included_in_operational_work is False
    assert (
        report.evaluation_transition_calls,
        report.evaluation_boundary_catalogue_calls,
    ) == (26, 6)
