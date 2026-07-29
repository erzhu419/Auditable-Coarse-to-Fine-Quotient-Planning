from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib

import pytest

from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v073_certificate_boundary_voi_v1 as voi
from acfqp import v073_anytime_adaptive_acquisition_v1 as adaptive
from acfqp import (
    v073_anytime_adaptive_acquisition_independent_verifier_v1
    as independent,
)


@pytest.fixture(scope="module")
def control() -> adaptive.DevelopmentAnytimeThreeArmControlV1:
    return adaptive.build_development_anytime_three_arm_control_v1()


def _run(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
    arm: adaptive.DevelopmentAnytimeArmV1,
) -> adaptive.DevelopmentAnytimeAdaptiveArmRunV1:
    return next(item for item in control.runs if item.arm is arm)


def _fake_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_registered_execution_and_sample_gate_remain_locked() -> None:
    assert adaptive.REGISTERED_EXECUTION_ALLOWED is False
    assert adaptive.SAMPLE_SAVING_CLAIMED is False
    assert adaptive.SAMPLE_EFFICIENCY_GATE_STATUS == "NOT_RUN"
    with pytest.raises(
        adaptive.RegisteredV073AnytimeAdaptiveAcquisitionLocked
    ):
        adaptive.run_registered_v073_anytime_adaptive_acquisition_v1()


def test_all_arms_share_raw_streams_and_anytime_alpha_contract(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
) -> None:
    profile = control.schedule_profile
    assert profile.family_alpha == Fraction(1, 100)
    assert profile.row_alpha == Fraction(1, 200)
    assert profile.row_alpha * profile.row_obligation_count == profile.family_alpha
    assert profile.sequential_profile.checkpoints == (128, 130)
    assert (
        profile.sequential_profile.confidence_accounting
        == "ONE_ALPHA_VILLE_TIME_UNIFORM_NO_CHECKPOINT_ALPHA_SPENDING"
    )
    expected_stream_ids = tuple(
        sorted(item.stream_id for item in control.streams)
    )
    assert all(item.stream_ids == expected_stream_ids for item in control.runs)
    assert all(
        item.schedule_profile_id == profile.schedule_profile_id
        for item in control.runs
    )
    assert (
        control.runs[0].epochs[0]
        == control.runs[1].epochs[0]
        == control.runs[2].epochs[0]
    )


def test_exact_realized_risk_and_earliest_stopping(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
) -> None:
    fixed = _run(
        control, adaptive.DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2
    )
    target = _run(
        control, adaptive.DevelopmentAnytimeArmV1.TARGET_ONLY_VOI
    )
    source = _run(
        control, adaptive.DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI
    )
    assert fixed.epochs[0].audit.root_failure_upper == Fraction(
        10_999_559, 67_108_864
    )
    assert control.threshold.risk_tolerance == Fraction(
        87_433_963, 536_870_912
    )
    assert fixed.epochs[1].audit.root_failure_upper == Fraction(
        43_753_541, 268_435_456
    )
    assert (
        fixed.epochs[1].audit.status
        is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    )
    assert target.epochs[-1].audit.root_failure_upper == Fraction(
        21_840_211, 134_217_728
    )
    assert target.epochs[-1].audit.status is robust.RobustAuditStatus.CERTIFIED
    assert fixed.epochs[-1].audit.root_failure_upper == Fraction(
        86_870_761, 536_870_912
    )
    assert fixed.epochs[-1] == source.epochs[-1]
    assert all(
        item.terminal_code
        is adaptive.DevelopmentRunTerminalCodeV1.PLAN_CERTIFIED
        for item in control.runs
    )


def test_development_accepted_draw_result_and_unexecuted_zero_charge(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
) -> None:
    assert control.incremental_accepted_draw_result == (
        ("FIXED_H1_THEN_H2", 4),
        ("TARGET_ONLY_VOI", 2),
        ("SOURCE_WEIGHTED_VOI", 4),
    )
    assert control.total_accepted_draw_result == (
        ("FIXED_H1_THEN_H2", 260),
        ("TARGET_ONLY_VOI", 258),
        ("SOURCE_WEIGHTED_VOI", 260),
    )
    target = _run(
        control, adaptive.DevelopmentAnytimeArmV1.TARGET_ONLY_VOI
    )
    assert len(target.blocks) == 1
    assert target.common_initial_accepted_draws == 256
    assert target.incremental_accepted_draws == 2
    assert target.total_accepted_draws == 258
    assert target.unexecuted_blocks_charged_draws == 0
    prefix_by_horizon = {
        item.remaining_horizon: item for item in target.epochs[-1].row_prefixes
    }
    assert prefix_by_horizon[2].prefix_draw_count == 130
    assert prefix_by_horizon[1].prefix_draw_count == 128
    assert target.blocks[0].unexecuted_draws_charged == 0
    assert control.sample_saving_claimed is False
    assert control.sample_efficiency_gate_status == "NOT_RUN"


def test_voi_is_frozen_before_materialization_and_source_only_changes_rank(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
) -> None:
    target = _run(
        control, adaptive.DevelopmentAnytimeArmV1.TARGET_ONLY_VOI
    )
    source = _run(
        control, adaptive.DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI
    )
    target_decision = target.decisions[0]
    source_decision = source.decisions[0]
    assert target_decision.selected_horizon == 2
    assert source_decision.selected_horizon == 1
    assert target_decision.voi_result is not None
    assert source_decision.voi_result is not None
    assert (
        target_decision.voi_result.base_vois
        == source_decision.voi_result.base_vois
    )
    assert target_decision.source_prior_id is None
    assert source_decision.source_prior_id == control.source_prior.prior_id
    for decision, block in (
        (target_decision, target.blocks[0]),
        (source_decision, source.blocks[0]),
    ):
        assert decision.target_reads_before_freeze == 0
        assert decision.future_outcome_fields_used == ()
        assert (
            block.access_events.index("DECISION_FROZEN")
            < block.access_events.index("SELECTED_RAW_SUFFIX_READ")
        )
    assert all(
        epoch.source_inputs == ()
        and all(prefix.source_inputs == () for prefix in epoch.row_prefixes)
        for run in control.runs
        for epoch in run.epochs
    )
    assert all(
        fantasy.source_prior_inputs == ()
        and fantasy.unknown_child_destination_ids == ()
        for base in source_decision.voi_result.base_vois
        for fantasy in base.fantasies
    )


def test_each_executed_block_has_replayable_slice_and_stop_reason(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
) -> None:
    stream_by_id = {item.stream_id: item for item in control.streams}
    for run in control.runs:
        for index, block in enumerate(run.blocks, start=1):
            stream = stream_by_id[block.stream_id]
            raw_slice = stream.outcomes[block.slice_start:block.slice_end]
            assert block.accepted_draws == len(raw_slice) == 2
            assert block.accepted_successes == sum(raw_slice)
            assert block.pre_epoch_id == run.epochs[index - 1].epoch_id
            assert block.post_epoch_id == run.epochs[index].epoch_id
            expected = (
                adaptive.DevelopmentBlockStopReasonV1.CERTIFIED_AFTER_BLOCK
                if run.epochs[index].audit.status
                is robust.RobustAuditStatus.CERTIFIED
                else (
                    adaptive.DevelopmentBlockStopReasonV1
                    .CONTINUE_FAILED_PROOF
                )
            )
            assert block.stop_reason is expected


def test_independent_verifier_replays_all_blocks_and_draws(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
) -> None:
    attestation = independent.verify_v073_anytime_three_arm_control_v1(
        control
    )
    assert attestation.control_id == control.control_id
    assert attestation.replayed_block_count == 5
    assert attestation.replayed_common_initial_accepted_draws == 768
    assert attestation.replayed_incremental_accepted_draws == 10
    assert attestation.replayed_total_accepted_draws == 778
    assert attestation.replayed_voi_fantasy_count == 18
    assert attestation.unexecuted_draws_verified_zero_charge == 2
    assert attestation.shared_raw_stream_replay_passed is True
    assert attestation.shared_confidence_contract_passed is True
    assert attestation.decision_before_materialization_passed is True
    assert attestation.earliest_certificate_stop_passed is True
    assert attestation.source_proposal_only_passed is True
    assert (
        attestation.controller_stream_accounting_independently_reimplemented
        is True
    )
    assert (
        attestation.planner_replay_boundary
        == adaptive.PLANNER_REPLAY_BOUNDARY
    )
    assert attestation.planner_algorithm_independence_claimed is False
    assert control.planner_algorithm_independence_claimed is False
    assert attestation.sample_saving_claimed is False
    assert attestation.sample_efficiency_gate_status == "NOT_RUN"


def test_independent_verifier_does_not_call_production_orchestration(
    monkeypatch: pytest.MonkeyPatch,
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("production adaptive orchestration was called")

    for name in (
        "build_development_anytime_three_arm_control_v1",
        "_make_prefix",
        "_build_epoch",
        "_prepare_decision",
        "_run_arm",
    ):
        monkeypatch.setattr(adaptive, name, forbidden)
    monkeypatch.setattr(
        voi, "score_development_certificate_boundary_voi_v1", forbidden
    )
    monkeypatch.setattr(
        voi, "freeze_development_failed_proof_dag_v1", forbidden
    )
    attestation = independent.verify_v073_anytime_three_arm_control_v1(
        control
    )
    assert attestation.replayed_block_count == 5


@pytest.mark.parametrize(
    "attack",
    (
        "source_leak_into_cs",
        "early_peek",
        "stale_dag",
        "wrong_stop",
        "wrong_selection",
        "charge_unexecuted",
        "raw_suffix_change",
        "checkpoint_change",
        "accepted_total_change",
        "planner_independence_overclaim",
    ),
)
def test_independent_verifier_rejects_protocol_and_leakage_attacks(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
    attack: str,
) -> None:
    attacked = deepcopy(control)
    target = _run(
        attacked, adaptive.DevelopmentAnytimeArmV1.TARGET_ONLY_VOI
    )
    if attack == "source_leak_into_cs":
        object.__setattr__(
            target.epochs[0].row_prefixes[0],
            "source_inputs",
            (attacked.source_prior.prior_id,),
        )
    elif attack == "early_peek":
        object.__setattr__(
            target.decisions[0],
            "target_reads_before_freeze",
            1,
        )
    elif attack == "stale_dag":
        assert target.epochs[0].proof_dag is not None
        object.__setattr__(
            target.epochs[0].proof_dag,
            "current_proof_gap",
            target.epochs[0].proof_dag.current_proof_gap
            + Fraction(1, 1_000_000),
        )
    elif attack == "wrong_stop":
        object.__setattr__(
            target.blocks[0],
            "stop_reason",
            adaptive.DevelopmentBlockStopReasonV1.CONTINUE_FAILED_PROOF,
        )
    elif attack == "wrong_selection":
        object.__setattr__(target.decisions[0], "selected_horizon", 1)
    elif attack == "charge_unexecuted":
        object.__setattr__(
            target, "unexecuted_blocks_charged_draws", 2
        )
    elif attack == "raw_suffix_change":
        stream = next(
            item for item in attacked.streams if item.remaining_horizon == 1
        )
        changed = list(stream.outcomes)
        changed[-1] = not changed[-1]
        object.__setattr__(stream, "outcomes", tuple(changed))
    elif attack == "checkpoint_change":
        checkpoint = target.epochs[0].row_prefixes[0].checkpoint
        object.__setattr__(
            checkpoint,
            "lower_probability",
            checkpoint.lower_probability + Fraction(1, 65_536),
        )
    elif attack == "accepted_total_change":
        object.__setattr__(
            target,
            "total_accepted_draws",
            target.total_accepted_draws + 2,
        )
    elif attack == "planner_independence_overclaim":
        object.__setattr__(
            attacked, "planner_algorithm_independence_claimed", True
        )
    else:  # pragma: no cover
        raise AssertionError(attack)
    with pytest.raises(
        independent.V073AnytimeAdaptiveIndependentVerificationFailure
    ):
        independent.verify_v073_anytime_three_arm_control_v1(attacked)


def test_source_and_fixed_same_path_have_identical_target_authorities(
    control: adaptive.DevelopmentAnytimeThreeArmControlV1,
) -> None:
    fixed = _run(
        control, adaptive.DevelopmentAnytimeArmV1.FIXED_H1_THEN_H2
    )
    source = _run(
        control, adaptive.DevelopmentAnytimeArmV1.SOURCE_WEIGHTED_VOI
    )
    assert [item.selected_horizon for item in fixed.decisions] == [1, 2]
    assert [item.selected_horizon for item in source.decisions] == [1, 2]
    assert fixed.epochs == source.epochs
    assert [item.stream_id for item in fixed.blocks] == [
        item.stream_id for item in source.blocks
    ]
    assert [item.accepted_successes for item in fixed.blocks] == [
        item.accepted_successes for item in source.blocks
    ]
    assert (
        fixed.incremental_accepted_draws
        == source.incremental_accepted_draws
        == 4
    )
    assert fixed.total_accepted_draws == source.total_accepted_draws == 260
