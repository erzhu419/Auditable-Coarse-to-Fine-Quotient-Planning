from __future__ import annotations

from dataclasses import fields
import inspect
from typing import Any

import pytest

from acfqp import exact_lazy_h2_robust_planner_v1 as lazy
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v072_cold_h2_model_builders_v1 as model_builders
from acfqp import v072_matched_direct_ground_baseline_v1 as baseline
from acfqp import (
    v072_matched_direct_ground_baseline_independent_verifier_v1
    as independent,
)


def _forbidden(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("forbidden non-direct route was invoked")


@pytest.fixture(scope="module")
def certified_run() -> baseline.MatchedDirectGroundRunV1:
    patcher = pytest.MonkeyPatch()
    patcher.setattr(
        model_builders,
        "build_v072_cold_h2_models_v1",
        _forbidden,
        raising=True,
    )
    patcher.setattr(
        lazy,
        "solve_exact_lazy_quotient_h2_v1",
        _forbidden,
        raising=True,
    )
    try:
        yield baseline.run_development_matched_direct_ground_baseline_v1(
            law=(
                baseline.DevelopmentMatchedDirectLawV1
                .FAILURE_RESIDUE_1_OF_100
            )
        )
    finally:
        patcher.undo()


@pytest.fixture(scope="module")
def noncertificate_run() -> baseline.MatchedDirectGroundRunV1:
    return baseline.run_development_matched_direct_ground_baseline_v1(
        law=(
            baseline.DevelopmentMatchedDirectLawV1
            .FAILURE_RESIDUE_3_OF_100
        )
    )


def _unsafe(value: Any, **changes: Any) -> Any:
    result = object.__new__(type(value))
    for member in fields(value):
        object.__setattr__(
            result,
            member.name,
            changes.get(member.name, getattr(value, member.name)),
        )
    return result


def _replace_record(
    run: baseline.MatchedDirectGroundRunV1,
    index: int,
    record: baseline.MatchedDirectCheckpointRecordV1,
) -> baseline.MatchedDirectGroundRunV1:
    records = list(run.checkpoint_records)
    records[index] = record
    return _unsafe(run, checkpoint_records=tuple(records))


def test_synchronous_schedule_stops_at_first_sound_certificate(
    certified_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    assert certified_run.terminal_class is (
        baseline.MatchedDirectTerminalClassV1.PLAN_CERTIFICATE
    )
    assert certified_run.terminal_code is (
        baseline.MatchedDirectTerminalCodeV1
        .MATCHED_DIRECT_GROUND_CERTIFIED
    )
    assert certified_run.stopped_checkpoint == 4_096
    assert tuple(
        item.evidence.checkpoint
        for item in certified_run.checkpoint_records
    ) == (2_048, 4_096)
    assert tuple(
        item.status for item in certified_run.checkpoint_records
    ) == (
        baseline.MatchedDirectCheckpointStatusV1.NOT_CERTIFIED,
        baseline.MatchedDirectCheckpointStatusV1.CERTIFIED,
    )
    assert (
        certified_run.checkpoint_records[0]
        .planner_result.audit.root_failure_upper
        > certified_run.checkpoint_records[0]
        .direct_snapshot.threshold_profile.risk_tolerance
    )
    assert (
        certified_run.checkpoint_records[1]
        .planner_result.audit.root_failure_upper
        <= certified_run.checkpoint_records[1]
        .direct_snapshot.threshold_profile.risk_tolerance
    )


def test_every_checkpoint_is_complete_and_prefix_preserving(
    certified_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    first, second = certified_run.checkpoint_records
    assert len(first.evidence.acquisitions) == 2
    assert len(second.evidence.acquisitions) == 2
    assert {
        item.row.physical_row_id for item in first.evidence.acquisitions
    } == {
        item.row.physical_row_id for item in second.evidence.acquisitions
    }
    first_by_row = {
        item.row.physical_row_id: item
        for item in first.evidence.acquisitions
    }
    for current in second.evidence.acquisitions:
        old = first_by_row[current.row.physical_row_id]
        assert current.discovery_transcript is old.discovery_transcript
        assert current.support_epoch is old.support_epoch
        assert current.validation_history[:-1] == old.validation_history
        assert (
            current.validation_history[-1].previous_transcript_id
            == old.validation_history[-1].transcript_id
        )
        assert current.validation_history[-1].previous_draw_count == 2_048
        assert (
            current.validation_history[-1]
            .work.newly_observed_draws
            == 2_048
        )


def test_direct_snapshot_has_no_quotient_source_or_concretizer(
    certified_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    for record in certified_run.checkpoint_records:
        snapshot = record.direct_snapshot
        assert snapshot.closure_bundle.arm == baseline.ARM
        assert (
            snapshot.closure_bundle.consumer_profile.consumer_routes
            == ("DIRECT",)
        )
        assert snapshot.direct_model.concretizer_entries == ()
        assert snapshot.direct_model.relational_context_id is None
        assert snapshot.direct_model.source_skeleton_id is None
        assert snapshot.direct_model.coordinate_profile_id is None
        assert snapshot.planner_model.concretizer_entries == ()
        assert len(snapshot.collapse_proof.entries) == 2
        assert all(
            entry.failure_value == 1
            and entry.continuation_reward_lower == 0
            and entry.source_other_mass_id
            != entry.planner_other_mass_id
            for entry in snapshot.collapse_proof.entries
        )
        assert record.work.source_prior_reads == 0
        assert record.work.quotient_model_builds == 0
        assert record.work.quotient_planner_calls == 0
        assert record.work.selected_row_acquisition_calls == 0
        assert record.work.local_promotion_calls == 0
        assert record.work.fallback_calls == 0
        assert record.work.hidden_law_queries == 0
        assert record.work.exact_ground_evaluator_calls == 0


def test_work_charges_cold_and_extensions_without_crn_discount(
    certified_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    first, second = certified_run.checkpoint_records
    assert first.work.discovery_new_draws == 2 * 64
    assert first.work.validation_new_draws == 2 * 2_048
    assert first.work.accepted_new_draws == 2 * (64 + 2_048)
    assert second.work.discovery_new_draws == 0
    assert second.work.validation_new_draws == 2 * 2_048
    assert (
        certified_run.total_accepted_draws
        == certified_run.total_random_word_calls
        == 2 * (64 + 4_096)
    )
    assert certified_run.crn_cost_discount_draws == 0


def test_independent_schedule_model_and_lazy_proof_replay(
    certified_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    result = independent.verify_matched_direct_ground_run_independently_v1(
        certified_run
    )
    assert result.run_id == certified_run.run_id
    assert result.stopped_checkpoint == 4_096
    assert result.checkpoint_record_count == 2
    assert result.physical_row_count == 2
    assert result.verified_direct_model_count == 2
    assert result.verified_lazy_proof_count == 2
    assert result.forbidden_route_invocation_count == 0
    assert result.exact_evaluator_supplement_count == 0


def test_control_keys_are_outcome_blind_and_draws_derive_outcomes() -> None:
    values = tuple(item.value for item in baseline.DevelopmentMatchedDirectLawV1)
    assert values == (
        "FAILURE_RESIDUE_1_OF_100",
        "FAILURE_RESIDUE_3_OF_100",
    )
    assert all(
        token not in " ".join(values).lower()
        for token in ("certif", "success", "result", "stop", "feasible")
    )
    source = inspect.getsource(baseline._raw_observation)
    assert "MatchedDirectCheckpointStatusV1" not in source
    assert "terminal_code" not in source
    row = baseline.development_matched_direct_physical_rows_v1()[0]
    acquisition = baseline.acquire_development_matched_direct_row_v1(
        row,
        law=(
            baseline.DevelopmentMatchedDirectLawV1
            .FAILURE_RESIDUE_1_OF_100
        ),
    )
    observations = acquisition.discovery_transcript.observations
    assert observations[0].outcome_document["failure"] is True
    assert observations[1].outcome_document["failure"] is False


def test_final_checkpoint_failure_is_typed_noncertificate_without_supplement(
    noncertificate_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    assert noncertificate_run.stopped_checkpoint == 16_384
    assert noncertificate_run.terminal_class is (
        baseline.MatchedDirectTerminalClassV1
        .ATTEMPT_CLOSURE_NONCERTIFICATE
    )
    assert noncertificate_run.terminal_code is (
        baseline.MatchedDirectTerminalCodeV1
        .MAXIMUM_DIRECT_CHECKPOINT_EXHAUSTED
    )
    assert all(
        item.status
        is baseline.MatchedDirectCheckpointStatusV1.NOT_CERTIFIED
        for item in noncertificate_run.checkpoint_records
    )
    assert noncertificate_run.exact_ground_evaluator_calls == 0
    assert noncertificate_run.fallback_calls == 0
    verified = independent.verify_matched_direct_ground_run_independently_v1(
        noncertificate_run
    )
    assert verified.stopped_checkpoint == 16_384
    assert verified.exact_evaluator_supplement_count == 0


def test_independent_verifier_rejects_partial_checkpoint(
    certified_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    record = certified_run.checkpoint_records[0]
    evidence = _unsafe(
        record.evidence,
        acquisitions=record.evidence.acquisitions[:-1],
    )
    attacked = _replace_record(
        certified_run,
        0,
        _unsafe(record, evidence=evidence),
    )
    with pytest.raises(
        independent.V072MatchedDirectIndependentVerificationFailure
    ):
        independent.verify_matched_direct_ground_run_independently_v1(
            attacked
        )


def test_independent_verifier_rejects_row_reset_and_early_stop(
    certified_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    second = certified_run.checkpoint_records[1]
    acquisition = second.evidence.acquisitions[0]
    reset = _unsafe(
        acquisition,
        validation_history=(acquisition.validation_history[-1],),
    )
    evidence = _unsafe(
        second.evidence,
        acquisitions=(reset, second.evidence.acquisitions[1]),
    )
    attacked = _replace_record(
        certified_run,
        1,
        _unsafe(second, evidence=evidence),
    )
    with pytest.raises(
        independent.V072MatchedDirectIndependentVerificationFailure
    ):
        independent.verify_matched_direct_ground_run_independently_v1(
            attacked
        )

    first = certified_run.checkpoint_records[0]
    early = _unsafe(
        certified_run,
        checkpoint_records=(first,),
        terminal_class=(
            baseline.MatchedDirectTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
        ),
        terminal_code=(
            baseline.MatchedDirectTerminalCodeV1
            .MAXIMUM_DIRECT_CHECKPOINT_EXHAUSTED
        ),
        stopped_checkpoint=2_048,
        total_accepted_draws=2 * (64 + 2_048),
        total_random_word_calls=2 * (64 + 2_048),
    )
    with pytest.raises(
        independent.V072MatchedDirectIndependentVerificationFailure,
        match="final checkpoint",
    ):
        independent.verify_matched_direct_ground_run_independently_v1(early)


def test_independent_verifier_rejects_forbidden_work_and_undercount(
    certified_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    first = certified_run.checkpoint_records[0]
    forbidden_work = _unsafe(first.work, quotient_planner_calls=1)
    attacked = _replace_record(
        certified_run,
        0,
        _unsafe(first, work=forbidden_work),
    )
    with pytest.raises(
        independent.V072MatchedDirectIndependentVerificationFailure,
        match="work",
    ):
        independent.verify_matched_direct_ground_run_independently_v1(
            attacked
        )

    undercounted = _unsafe(
        certified_run,
        total_accepted_draws=certified_run.total_accepted_draws - 1,
    )
    with pytest.raises(
        independent.V072MatchedDirectIndependentVerificationFailure,
        match="aggregate work",
    ):
        independent.verify_matched_direct_ground_run_independently_v1(
            undercounted
        )


def test_independent_verifier_rejects_model_transplant(
    certified_run: baseline.MatchedDirectGroundRunV1,
) -> None:
    first, second = certified_run.checkpoint_records
    transplanted = _unsafe(
        second,
        direct_snapshot=first.direct_snapshot,
        model_verification=first.model_verification,
    )
    attacked = _replace_record(certified_run, 1, transplanted)
    with pytest.raises(
        independent.V072MatchedDirectIndependentVerificationFailure
    ):
        independent.verify_matched_direct_ground_run_independently_v1(
            attacked
        )


def test_registered_target_remains_hard_locked() -> None:
    assert (
        baseline.REGISTERED_TARGET_EXECUTION_STATUS
        == "LOCKED_NONAUTHORIZING_DRAFT"
    )
    with pytest.raises(
        baseline.RegisteredMatchedDirectGroundExecutionLockedV1
    ):
        baseline.run_registered_matched_direct_ground_baseline_v1()
