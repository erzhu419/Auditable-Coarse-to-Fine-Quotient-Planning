from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import inspect

import pytest

from acfqp import v072_campaign_reconciliation_authority_v1 as reconciliation
from acfqp import (
    v072_campaign_reconciliation_independent_verifier_v1
    as reconciliation_independent,
)
from acfqp import v072_development_complete_adaptive_run_v1 as complete
from acfqp import (
    v072_development_complete_adaptive_run_independent_verifier_v1
    as complete_independent,
)
from acfqp import v072_incremental_materializer_v1 as materializer


def _occurrence(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


@pytest.fixture(scope="module")
def law_a_run() -> complete.DevelopmentCompleteAdaptivePlanningRunV1:
    return complete.run_development_complete_adaptive_planning_control_v1(
        law_key=materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_A,
        logical_occurrence_id=_occurrence("v072-complete-law-a"),
    )


@pytest.fixture(scope="module")
def law_b_run() -> complete.DevelopmentCompleteAdaptivePlanningRunV1:
    return complete.run_development_complete_adaptive_planning_control_v1(
        law_key=materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_B,
        logical_occurrence_id=_occurrence("v072-complete-law-b"),
    )


def test_law_a_closes_after_first_real_rebuild_and_replays(
    law_a_run: complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> None:
    run = law_a_run
    assert run.logical_occurrence_id == _occurrence(
        "v072-complete-law-a"
    )
    assert len(run.handoffs) == 1
    assert len(run.round_selections) == 0
    assert run.prior_cold_draws == 4_224
    assert run.incremental_suffix_draws == 35_072
    assert run.total_accepted_draws == 39_296
    assert run.terminal_code is (
        complete.DevelopmentCompleteAdaptiveTerminalCodeV1
        .PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD
    )
    assert (
        run.control_materializer_attestation.attestation_id
        != run.handoff_materializer_attestations[0].attestation_id
    )
    attestation = (
        complete_independent
        .verify_development_complete_adaptive_run_v1(run)
    )
    assert attestation.complete_run_id == run.run_id


def test_law_b_retains_failed_round_then_certifies_and_reconciles(
    law_b_run: complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> None:
    run = law_b_run
    assert run.logical_occurrence_id == _occurrence(
        "v072-complete-law-b"
    )
    assert len(run.handoffs) == 2
    assert len(run.round_selections) == 1
    assert len(run.selector_verifications) == 1
    assert run.incremental_suffix_draws == 35_072 + 18_560
    assert run.total_accepted_draws == 57_856
    assert run.terminal_code is (
        complete.DevelopmentCompleteAdaptiveTerminalCodeV1
        .PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD
    )
    assert not run.postbuild_results[0].certified
    assert run.postbuild_results[1].certified
    assert (
        run.selector_verifications[0]
        .previous_materializer_attestation_id
        == run.control_materializer_attestation.attestation_id
    )
    assert all(
        postbuild.materializer_attestation_id
        == handoff.attestation_id
        for postbuild, handoff in zip(
            run.postbuild_independent_attestations,
            run.handoff_materializer_attestations,
            strict=True,
        )
    )

    complete_independent.verify_development_complete_adaptive_run_v1(run)
    occurrence = reconciliation.reconcile_complete_adaptive_run_v1(run)
    assert occurrence.terminal_class is (
        reconciliation.ReconciliationTerminalClassV1.PLAN_CERTIFICATE
    )
    assert occurrence.work.accepted_draws == 57_856
    assert occurrence.work.failed_parent_certificate_attempts == 1
    assert occurrence.work.failed_incremental_postbuild_audits == 1
    assert occurrence.work.incremental_postbuild_model_builds == 2
    assert occurrence.work.incremental_postbuild_solver_calls == 2
    assert len(occurrence.additional_access_orders) == 1
    ledger = reconciliation.reconcile_campaign_v1(
        occurrences=(occurrence,)
    )
    replay = (
        reconciliation_independent
        .verify_campaign_reconciliation_independently_v1(ledger)
    )
    assert replay.plan_certificate_count == 1
    assert replay.accepted_draw_commitment_count == 57_856


def test_attestation_role_transplants_fail_closed(
    law_a_run: complete.DevelopmentCompleteAdaptivePlanningRunV1,
    law_b_run: complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> None:
    with pytest.raises(
        complete.DevelopmentCompleteAdaptiveRunInvariantViolation
    ):
        replace(
            law_a_run,
            control_materializer_attestation=(
                law_a_run.handoff_materializer_attestations[0]
            ),
        )
    with pytest.raises(
        complete.DevelopmentCompleteAdaptiveRunInvariantViolation
    ):
        replace(
            law_b_run,
            handoff_materializer_attestations=(
                law_b_run.control_materializer_attestation,
                law_b_run.handoff_materializer_attestations[1],
            ),
        )


def test_independent_replay_rejects_unsafe_count_and_range_reuse_clones(
    law_b_run: complete.DevelopmentCompleteAdaptivePlanningRunV1,
) -> None:
    count_clone = copy.copy(law_b_run)
    object.__setattr__(
        count_clone,
        "total_accepted_draws",
        law_b_run.total_accepted_draws - 1,
    )
    with pytest.raises(
        complete_independent
        .IndependentCompleteAdaptiveRunVerificationFailure
    ):
        complete_independent.verify_development_complete_adaptive_run_v1(
            count_clone
        )

    second = copy.copy(law_b_run.handoffs[1])
    object.__setattr__(
        second,
        "raw_commitment_ranges",
        law_b_run.handoffs[0].raw_commitment_ranges,
    )
    range_clone = copy.copy(law_b_run)
    object.__setattr__(
        range_clone,
        "handoffs",
        (law_b_run.handoffs[0], second),
    )
    with pytest.raises(ValueError):
        complete_independent.verify_development_complete_adaptive_run_v1(
            range_clone
        )


def test_independent_replay_does_not_call_complete_production_hash(
    law_b_run: complete.DevelopmentCompleteAdaptivePlanningRunV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = (
        complete_independent
        .verify_development_complete_adaptive_run_v1(law_b_run)
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("independent verifier called production hash")

    monkeypatch.setattr(complete, "_content_id", forbidden)
    for name in (
        "raw_commitment_id_v1",
        "upstream_stream_id_v1",
        "upstream_raw_commitment_id_v1",
        "upstream_raw_commitment_range_proof_v1",
    ):
        monkeypatch.setattr(materializer, name, forbidden)
    replay = (
        complete_independent
        .verify_development_complete_adaptive_run_v1(law_b_run)
    )
    assert replay.attestation_id == expected.attestation_id


def test_independent_replay_does_not_construct_production_control_wrapper(
    law_b_run: complete.DevelopmentCompleteAdaptivePlanningRunV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError(
            "independent verifier constructed production control wrapper"
        )

    monkeypatch.setattr(
        materializer,
        "DevelopmentAcquisitionControlRunV1",
        forbidden,
    )
    replay = (
        complete_independent
        .verify_development_complete_adaptive_run_v1(law_b_run)
    )
    assert replay.complete_run_id == law_b_run.run_id


def test_complete_adapter_accepts_no_status_count_or_result_inputs() -> None:
    forbidden = {
        "status",
        "count",
        "counts",
        "result",
        "terminal",
        "terminal_class",
        "terminal_code",
        "discount",
    }
    assert forbidden.isdisjoint(
        inspect.signature(
            complete.run_development_complete_adaptive_planning_control_v1
        ).parameters
    )
    assert forbidden.isdisjoint(
        inspect.signature(
            reconciliation.reconcile_complete_adaptive_run_v1
        ).parameters
    )
