from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib

import pytest

from acfqp import v073_certificate_boundary_voi_v1 as voi
from acfqp import (
    v073_certificate_boundary_voi_independent_verifier_v1 as independent,
)


@pytest.fixture(scope="module")
def control() -> voi.DevelopmentVOIOpportunityControlV1:
    return voi.build_development_voi_opportunity_control_v1()


def _by_horizon(
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> dict[int, voi.DevelopmentTargetOnlyBoundaryVOIV1]:
    return {
        item.candidate.remaining_horizon: item
        for item in control.no_prior_result.base_vois
    }


def _fake_id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_registered_entry_remains_fail_closed() -> None:
    assert voi.REGISTERED_EXECUTION_ALLOWED is False
    assert voi.REGISTERED_TARGET_OBSERVATIONS == 0
    assert voi.SAMPLE_EFFICIENCY_GATE_STATUS == "NOT_RUN"
    assert voi.SAMPLE_SAVING_CLAIMED is False
    with pytest.raises(voi.RegisteredV073CertificateBoundaryVOILocked):
        voi.run_registered_v073_certificate_boundary_voi_v1()


def test_control_has_exact_failed_boundary_and_two_real_candidates(
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> None:
    assert control.failed_audit.root_failure_upper == Fraction(9, 25)
    assert control.failed_audit.normalized_regret_upper == 0
    assert control.threshold.risk_tolerance == Fraction(7, 20)
    assert control.proof_dag.current_proof_gap == Fraction(1, 100)
    assert len(control.no_prior_result.base_vois) == 2
    assert {
        item.candidate.remaining_horizon
        for item in control.no_prior_result.base_vois
    } == {1, 2}
    assert control.no_prior_result.base_vois == control.source_result.base_vois
    assert (
        control.no_prior_result.schedule.selected_candidate_id
        != control.source_result.schedule.selected_candidate_id
    )


def test_exact_kt_voi_and_stopping_opportunities(
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> None:
    base = _by_horizon(control)
    assert base[2].expected_gap_reduction == Fraction(2033, 228800)
    assert base[2].base_voi_per_draw == Fraction(2033, 457600)
    assert base[2].certifying_fantasy_probability == Fraction(133, 176)
    assert base[1].expected_gap_reduction == Fraction(323, 85800)
    assert base[1].base_voi_per_draw == Fraction(323, 171600)
    assert base[1].certifying_fantasy_probability == 0
    assert (
        control.no_prior_result.schedule.selected_candidate_id
        == base[2].candidate.candidate_id
    )
    assert (
        control.source_result.schedule.selected_candidate_id
        == base[1].candidate.candidate_id
    )


def test_fantasies_are_exact_target_only_and_keep_unknown_inside_other(
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> None:
    for base in control.no_prior_result.base_vois:
        evidence = next(
            item
            for item in control.row_evidence
            if item.evidence_id == base.candidate.row_evidence_id
        )
        assert len(base.fantasies) == 3
        assert sum(
            (item.predictive_probability for item in base.fantasies),
            Fraction(0),
        ) == 1
        for fantasy in base.fantasies:
            assert type(fantasy.predictive_probability) is Fraction
            assert all(
                type(value) is Fraction
                for value in fantasy.posterior_predictive_masses
            )
            assert fantasy.destination_ids == evidence.destination_ids
            assert fantasy.other_destination_id == evidence.other_destination_id
            assert fantasy.unknown_child_destination_ids == ()
            assert fantasy.source_prior_inputs == ()
            assert fantasy.certificate_authority is False
        assert base.source_prior_inputs == ()
        assert base.certificate_authority is False


def test_source_is_disjoint_and_only_multiplies_completed_base_voi(
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> None:
    assert (
        control.target_model.context_id
        not in control.source_prior.source_context_ids
    )
    assert control.source_prior.target_context_ids == ()
    assert control.source_prior.may_certify is False
    assert control.source_prior.may_narrow_confidence is False
    q_by_feature = {
        item.feature_key: item.q for item in control.source_prior.entries
    }
    base = _by_horizon(control)
    assert q_by_feature[base[2].candidate.feature_key] == 0
    assert q_by_feature[base[1].candidate.feature_key] == 1
    no_prior_scores = {
        item.candidate_id: item
        for item in control.no_prior_result.arm_scores
    }
    source_scores = {
        item.candidate_id: item
        for item in control.source_result.arm_scores
    }
    for candidate_id, no_prior in no_prior_scores.items():
        source = source_scores[candidate_id]
        assert source.base_voi_id == no_prior.base_voi_id
        assert source.base_voi_per_draw == no_prior.base_voi_per_draw
        assert source.multiplier == (
            Fraction(1, 2) + Fraction(3, 2) * source.source_q
        )
        assert source.score == source.base_voi_per_draw * source.multiplier
    assert control.no_prior_result.target_draws == 0
    assert control.source_result.target_draws == 0
    assert control.sample_saving_claimed is False
    assert control.sample_efficiency_gate_status == "NOT_RUN"


def test_independent_verifier_replays_all_fantasies(
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> None:
    attestation = (
        independent.verify_v073_certificate_boundary_voi_control_v1(control)
    )
    assert attestation.control_id == control.control_id
    assert attestation.replayed_fantasy_count == 12
    assert attestation.source_target_disjoint is True
    assert attestation.exact_kt_replayed is True
    assert attestation.exact_robust_planner_replayed is True
    assert attestation.source_enters_only_final_multiplier is True
    assert attestation.registered_execution_allowed is False
    assert attestation.registered_target_observations == 0
    assert attestation.sample_saving_claimed is False
    assert attestation.sample_efficiency_gate_status == "NOT_RUN"
    assert len(attestation.attestation_id) == 64


def test_independent_verifier_does_not_call_production_voi_helpers(
    monkeypatch: pytest.MonkeyPatch,
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("production VOI helper was called")

    for name in (
        "score_development_certificate_boundary_voi_v1",
        "build_development_source_voi_prior_v1",
        "freeze_development_failed_proof_dag_v1",
        "_derive_candidates",
        "_candidate_base_voi",
        "_kt_fantasy_probability",
        "_posterior_predictive_masses",
        "_replace_candidate_row_with_point_masses",
        "_portable_feature_key",
        "_proof_gap",
    ):
        monkeypatch.setattr(voi, name, forbidden)
    attestation = (
        independent.verify_v073_certificate_boundary_voi_control_v1(control)
    )
    assert attestation.replayed_fantasy_count == 12


@pytest.mark.parametrize(
    "attack",
    (
        "unknown_child",
        "base_arithmetic",
        "source_score",
        "selected_candidate",
        "source_target_leak",
        "stale_dag",
        "support_leak",
    ),
)
def test_independent_verifier_rejects_leakage_and_replay_attacks(
    control: voi.DevelopmentVOIOpportunityControlV1,
    attack: str,
) -> None:
    attacked = deepcopy(control)
    if attack == "unknown_child":
        fantasy = attacked.no_prior_result.base_vois[0].fantasies[0]
        object.__setattr__(
            fantasy,
            "unknown_child_destination_ids",
            (_fake_id("unregistered-future-child"),),
        )
    elif attack == "base_arithmetic":
        base = attacked.no_prior_result.base_vois[0]
        object.__setattr__(
            base,
            "expected_gap_reduction",
            base.expected_gap_reduction + Fraction(1, 10_000),
        )
    elif attack == "source_score":
        score = attacked.source_result.arm_scores[0]
        object.__setattr__(score, "score", score.score + Fraction(1, 10_000))
    elif attack == "selected_candidate":
        schedule = attacked.source_result.schedule
        replacement = schedule.ordered_candidate_ids[-1]
        object.__setattr__(schedule, "selected_candidate_id", replacement)
    elif attack == "source_target_leak":
        trial = attacked.source_trials[0]
        object.__setattr__(
            trial, "target_context_id", attacked.target_model.context_id
        )
    elif attack == "stale_dag":
        object.__setattr__(
            attacked.proof_dag,
            "current_proof_gap",
            attacked.proof_dag.current_proof_gap + Fraction(1, 100),
        )
    elif attack == "support_leak":
        evidence = attacked.row_evidence[0]
        object.__setattr__(
            evidence,
            "destination_ids",
            tuple(sorted((*evidence.destination_ids, _fake_id("future-child")))),
        )
        object.__setattr__(
            evidence,
            "counts",
            (*evidence.counts, 0),
        )
    else:  # pragma: no cover
        raise AssertionError(attack)
    with pytest.raises(
        independent.V073CertificateBoundaryVOIIndependentVerificationFailure
    ):
        independent.verify_v073_certificate_boundary_voi_control_v1(attacked)


def test_no_prior_arm_rejects_source_prior(
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> None:
    with pytest.raises(voi.V073CertificateBoundaryVOIInvariantViolation):
        voi.score_development_certificate_boundary_voi_v1(
            model=control.target_model,
            threshold=control.threshold,
            failed_audit=control.failed_audit,
            proof_dag=control.proof_dag,
            row_evidence=control.row_evidence,
            next_block_size=control.next_block_size,
            arm=voi.DevelopmentVOIArmV1.NO_PRIOR,
            source_prior=control.source_prior,
        )


def test_stale_dag_and_support_leak_fail_before_scoring(
    control: voi.DevelopmentVOIOpportunityControlV1,
) -> None:
    stale_dag = deepcopy(control.proof_dag)
    object.__setattr__(
        stale_dag,
        "current_proof_gap",
        stale_dag.current_proof_gap + Fraction(1, 100),
    )
    with pytest.raises(voi.V073CertificateBoundaryVOIInvariantViolation):
        voi.score_development_certificate_boundary_voi_v1(
            model=control.target_model,
            threshold=control.threshold,
            failed_audit=control.failed_audit,
            proof_dag=stale_dag,
            row_evidence=control.row_evidence,
            next_block_size=control.next_block_size,
            arm=voi.DevelopmentVOIArmV1.NO_PRIOR,
        )

    leaked = list(deepcopy(control.row_evidence))
    object.__setattr__(
        leaked[0],
        "destination_ids",
        tuple(sorted((*leaked[0].destination_ids, _fake_id("unknown-child")))),
    )
    object.__setattr__(leaked[0], "counts", (*leaked[0].counts, 0))
    with pytest.raises(voi.V073CertificateBoundaryVOIInvariantViolation):
        voi.score_development_certificate_boundary_voi_v1(
            model=control.target_model,
            threshold=control.threshold,
            failed_audit=control.failed_audit,
            proof_dag=control.proof_dag,
            row_evidence=tuple(leaked),
            next_block_size=control.next_block_size,
            arm=voi.DevelopmentVOIArmV1.NO_PRIOR,
        )
