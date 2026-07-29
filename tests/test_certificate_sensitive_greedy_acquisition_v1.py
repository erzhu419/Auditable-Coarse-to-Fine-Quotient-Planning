from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import hashlib
import inspect

import pytest

import acfqp.certificate_sensitive_greedy_acquisition_v1 as greedy
import acfqp.observation_support_joint_pair_recovery_v1 as joint
import acfqp.partial_support_robust_planner_v1 as robust
from tests.test_partial_support_expansion_authority_v1 import (
    _build_noncausal_fixture,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:test:certificate-sensitive:v1\x00"
        + label.encode()
    ).hexdigest()


class _Target:
    def __init__(self, model, audit, threshold, registry):
        self.model = model
        self.audit = audit
        self.threshold = threshold
        self.registry = registry


@pytest.fixture(scope="module")
def target() -> _Target:
    patcher = pytest.MonkeyPatch()
    try:
        fixture = _build_noncausal_fixture(patcher)
        direct = fixture.bridge.direct_model
        singleton_concretizer = tuple(
            robust.DistinctActionConcretizerEntryV1(
                catalogue.state_coordinate_key,
                catalogue.state_id,
                action.action_coordinate_key,
                (action.action_id,),
            )
            for catalogue in direct.catalogues
            for action in catalogue.actions
        )
        model = robust.build_partial_support_model_v1(
            context_id=direct.context_id,
            root_state_id=direct.root_state_id,
            catalogues=direct.catalogues,
            destinations=direct.destinations,
            rows=direct.rows,
            concretizer_entries=singleton_concretizer,
        )
        audit = robust.solve_quotient_robust_h2_v1(
            model,
            fixture.threshold,
        )
        assert audit.failed_frontier is not None
        projection_by_planner = {
            item.planner_row.row_id: item
            for item in fixture.bridge.row_projections
        }
        assignment = {
            (item.scope_key, item.remaining_horizon):
            item.selected_action_key
            for item in audit.assignments
        }
        planner_row_by_key = {
            (item.state_id, item.remaining_horizon, item.action_id): item
            for item in model.rows
        }
        selected_rows: set[str] = set()
        for entry in model.concretizer_entries:
            horizon = 2 if entry.state_id == model.root_state_id else 1
            if (
                assignment.get((entry.state_coordinate_key, horizon))
                != entry.abstract_action_key
            ):
                continue
            selected_rows.update(
                planner_row_by_key[
                    (entry.state_id, horizon, action_id)
                ].row_id
                for action_id in entry.ground_action_ids
            )
        by_partial = {item.partial_row_id: item for item in fixture.rows}
        candidates = []
        for planner_row_id in audit.failed_frontier.other_positive_row_ids:
            if planner_row_id not in selected_rows:
                continue
            projection = projection_by_planner[planner_row_id]
            row = by_partial[projection.partial_row_id]
            candidates.append(
                joint.JointPairCandidateRowV1(
                    planner_row_id,
                    row.partial_row_id,
                    row.binding.row_id,
                    row.physical_evidence_id,
                    row.support_epoch.support_epoch_id,
                    row.confidence_authority.authority_id,
                    row.binding.remaining_horizon,
                    (_id(f"novel:{planner_row_id}"),),
                )
            )
        candidates = tuple(
            sorted(candidates, key=lambda item: item.candidate_id)
        )
        source_registry = joint.JointPairCandidateRegistryV1(
            model.model_id,
            audit.audit_id,
            audit.failed_frontier.frontier_id,
            fixture.threshold.threshold_profile_id,
            tuple(sorted(item.assignment_id for item in audit.assignments)),
            fixture.bridge.source_partial_row_ids,
            (),
            (),
            (),
            candidates,
        )
        registry = greedy.freeze_target_local_candidate_registry_v1(
            source_registry,
            model=model,
            audit=audit,
            threshold=fixture.threshold,
        )
        yield _Target(model, audit, fixture.threshold, registry)
    finally:
        patcher.undo()


def _prior(
    target: _Target,
    label: str,
    *,
    feature_schema_id: str,
    reverse: bool,
) -> greedy.SourceFrozenConsensusPriorV1:
    h1 = {
        item.feature.feature_key
        for item in target.registry.candidates
        if item.source_candidate.remaining_horizon == 1
    }
    h2 = {
        item.feature.feature_key
        for item in target.registry.candidates
        if item.source_candidate.remaining_horizon == 2
    }
    assert h1 and h2 and not (h1 & h2)
    trials = []
    for feature in sorted(h1 | h2):
        score = Fraction(
            int((feature in h2) if reverse else (feature in h1))
        )
        for index in range(3):
            trials.append(
                greedy.SourceLocalTrialV1(
                    _id(f"{label}:context:{index}"),
                    _id(f"{label}:model:{index}"),
                    _id(f"{label}:audit:{index}"),
                    _id(f"{label}:raw:{feature}:{index}"),
                    feature,
                    score,
                )
            )
    return greedy.freeze_source_consensus_prior_v1(
        source_family_id=_id(f"{label}:family"),
        source_training_split_id=_id(f"{label}:split"),
        applicable_feature_schema_id=feature_schema_id,
        votes=trials,
    )


@pytest.fixture(scope="module")
def priors(target: _Target):
    source = _prior(
        target,
        "source",
        feature_schema_id=greedy.FEATURE_SCHEMA_ID,
        reverse=False,
    )
    return (
        source,
        _prior(
            target,
            "ood",
            feature_schema_id=_id("ood-feature-schema"),
            reverse=False,
        ),
        source,
    )


@pytest.fixture(scope="module")
def campaign(target: _Target, priors):
    source, ood, wrong = priors
    return greedy.run_certificate_sensitive_matched_campaign_v1(
        model=target.model,
        audit=target.audit,
        threshold=target.threshold,
        registry=target.registry,
        source_prior=source,
        ood_prior=ood,
        wrong_prior=wrong,
        synthetic_materializer=True,
        max_workers=1,
    )


def test_contract_caps_portable_features_and_source_archive(
    target: _Target,
    priors,
) -> None:
    source, _, _ = priors
    caps = greedy.registered_certificate_sensitive_caps_v1()

    assert greedy.CONTRACT_VERSION == "1.35.0"
    assert (
        greedy.PROFILE_KEY
        == "source_frozen_certificate_sensitive_greedy_acquisition_v0"
    )
    assert caps.max_rounds == 2
    assert caps.max_total_single_zero_evaluations == 128
    assert caps.max_incremental_draw_upper == 160_960
    assert caps.pair_subset_enumeration_cap == 0
    assert caps.k3_subset_enumeration_cap == 0
    assert source.source_frozen and source.proposal_only
    assert not source.may_certify
    assert all(item.disagreement == 0 for item in source.consensus)
    assert {
        item.multiplier for item in source.consensus
    } == {Fraction(1, 2), Fraction(2)}
    assert all(item.mean_midrank == item.normalized_midrank for item in source.consensus)
    assert all(item.worst_midrank == item.mean_midrank for item in source.consensus)
    assert all(
        item.feature.ids_stripped for item in target.registry.candidates
    )
    assert all(
        item.feature.selected_row_category
        in {entry.value for entry in robust.SelectedRowCategory}
        for item in target.registry.candidates
    )
    different = _prior(
        target,
        "different-wrong-control",
        feature_schema_id=greedy.FEATURE_SCHEMA_ID,
        reverse=True,
    )
    with pytest.raises(greedy.CertificateSensitiveGreedyInvariantViolation):
        greedy.run_certificate_sensitive_matched_campaign_v1(
            model=target.model,
            audit=target.audit,
            threshold=target.threshold,
            registry=target.registry,
            source_prior=source,
            ood_prior=priors[1],
            wrong_prior=different,
            synthetic_materializer=False,
        )


def test_counterfactual_prepare_cannot_emit_model_epoch_or_certificate(
    target: _Target,
    priors,
) -> None:
    source, _, _ = priors
    run = greedy.run_certificate_sensitive_greedy_acquisition_v1(
        model=target.model,
        audit=target.audit,
        threshold=target.threshold,
        registry=target.registry,
        arm=greedy.MatchedArm.SOURCE_CONSENSUS_PRIOR,
        prior=source,
        synthetic_materializer=False,
    )

    assert (
        run.outcome
        is greedy.GreedyAcquisitionOutcome.AUTHORIZATION_READY
    )
    assert run.pending_prepared_round is not None
    assert run.consumed_rounds == ()
    assert run.certificate is None
    assert run.cumulative_draw_upper == 0
    prepared = run.pending_prepared_round
    assert all(score.counterfactual_model_id for score in prepared.scores)
    assert prepared.access.observer_calls == 0
    assert prepared.access.promotion_calls == 0
    assert prepared.access.full_policy_replans == 0
    assert prepared.access.exact_evaluation_calls == 0


def test_synthetic_actual_round1_fails_round2_full_replan_certifies(
    campaign: greedy.CertificateSensitiveMatchedCampaignV1,
) -> None:
    for run in (
        campaign.source_run,
        campaign.no_prior_run,
        campaign.ood_run,
    ):
        assert (
            run.outcome
            is greedy.GreedyAcquisitionOutcome
            .SYNTHETIC_CONTROL_CERTIFIED_AFTER_ROUND_2
        )
        assert run.synthetic_fixture_only
        assert not run.source_semantic_replay_claimed
        assert not run.fresh_round2_frontier_claimed
        assert not run.independent_verifier_claimed
        assert len(run.consumed_rounds) == 2
        first, second = run.consumed_rounds
        assert not first.robust_audit.certified
        assert first.certificate is None
        assert second.robust_audit.certified
        assert second.certificate is not None
        assert (
            second.certificate.authority
            == greedy.CERTIFICATE_AUTHORITY
        )
        assert second.certificate.prior_certificate_calls == 0
        assert (
            second.certificate.audit_id
            == second.robust_audit.audit_id
        )
        assert (
            second.receipt.evidence_sequence
            >= second.prepared.authorization.target_access_sequence_minimum
        )

    wrong = campaign.wrong_run
    assert (
        wrong.outcome
        is greedy.GreedyAcquisitionOutcome.DRAW_CAP_EXHAUSTED
    )
    assert len(wrong.consumed_rounds) == 1
    assert wrong.certificate is None
    assert wrong.cumulative_draw_upper == 160_960


def test_ood_abstains_exactly_to_no_prior_and_wrong_cannot_certify(
    campaign: greedy.CertificateSensitiveMatchedCampaignV1,
) -> None:
    no_prior = campaign.no_prior_run
    ood = campaign.ood_run
    wrong = campaign.wrong_run

    assert (
        ood.prior_disposition
        is greedy.PriorDisposition.OOD_ABSTAINED
    )
    assert ood.effective_prior_id is None
    assert campaign.ood_exactly_matches_no_prior
    assert ood.effective_schedule_id == no_prior.effective_schedule_id
    assert ood.target_trace_id == no_prior.target_trace_id
    assert ood.selected_candidate_ids == no_prior.selected_candidate_ids
    assert ood.certificate == no_prior.certificate
    assert wrong.certificate is None


def test_no_pair_k3_or_preauthorization_execution(
    campaign: greedy.CertificateSensitiveMatchedCampaignV1,
) -> None:
    for run in (
        campaign.source_run,
        campaign.no_prior_run,
        campaign.ood_run,
        campaign.wrong_run,
    ):
        assert run.pair_subset_enumerations == 0
        assert run.k3_subset_enumerations == 0
        assert not run.confirmatory_result
        assert not run.k6_positive_result_preassumed
        assert not run.sample_efficiency_claimed
        for consumed in run.consumed_rounds:
            access = consumed.prepared.access
            assert access.observer_calls == 0
            assert access.promotion_calls == 0
            assert access.full_policy_replans == 0
            assert access.exact_evaluation_calls == 0
    assert "combinations(" not in inspect.getsource(
        greedy.run_certificate_sensitive_greedy_acquisition_v1
    )
    score_source = inspect.getsource(greedy._score_all)
    assert "ProcessPoolExecutor" not in score_source
    assert "get_context" not in score_source


def test_tamper_leak_and_stale_identity_fail_closed(
    target: _Target,
    priors,
    campaign: greedy.CertificateSensitiveMatchedCampaignV1,
) -> None:
    source, _, _ = priors
    changed_prior = _prior(
        target,
        "changed-source",
        feature_schema_id=greedy.FEATURE_SCHEMA_ID,
        reverse=True,
    )
    first = campaign.source_run.consumed_rounds[0]
    with pytest.raises(greedy.CertificateSensitiveGreedyInvariantViolation):
        replace(first.prepared.access, observer_calls=1)
    with pytest.raises(greedy.CertificateSensitiveGreedyInvariantViolation):
        replace(
            first.receipt,
            evidence_sequence=first.prepared.authorization.authorization_sequence,
        )
    with pytest.raises(greedy.CertificateSensitiveGreedyInvariantViolation):
        replace(
            target.registry.candidates[0],
            incremental_draw_upper=1,
        )
    prepared = first.prepared
    admissible = tuple(
        item
        for item in prepared.scores
        if (
            item.slack_gain > 0
            and item.score_id
            != prepared.authorization.selected_score_id
        )
    )
    assert admissible
    nonbest = admissible[0]
    with pytest.raises(greedy.CertificateSensitiveGreedyInvariantViolation):
        replace(
            prepared,
            authorization=replace(
                prepared.authorization,
                selected_score_id=nonbest.score_id,
                selected_candidate_id=nonbest.candidate_id,
                selected_source_candidate_id=nonbest.source_candidate_id,
                selected_planner_row_id=nonbest.planner_row_id,
                selected_draw_upper=nonbest.draw_upper,
                cumulative_draw_upper_after_selection=nonbest.draw_upper,
            ),
        )

    certified = campaign.source_run.consumed_rounds[-1]
    assert certified.certificate is not None
    with pytest.raises(greedy.CertificateSensitiveGreedyInvariantViolation):
        replace(
            certified,
            certificate=replace(
                certified.certificate,
                root_failure_upper=Fraction(999),
                normalized_regret_upper=Fraction(999),
            ),
        )

    feature = target.registry.candidates[0].feature.feature_key
    leaked_trials = tuple(
        greedy.SourceLocalTrialV1(
            target.model.model_id if index == 0 else _id(f"leak:c:{index}"),
            _id(f"leak:m:{index}"),
            _id(f"leak:a:{index}"),
            _id(f"leak:r:{index}"),
            feature,
            Fraction(1),
        )
        for index in range(2)
    )
    leaked = greedy.freeze_source_consensus_prior_v1(
        source_family_id=_id("leak:family"),
        source_training_split_id=_id("leak:split"),
        applicable_feature_schema_id=greedy.FEATURE_SCHEMA_ID,
        votes=leaked_trials,
    )
    with pytest.raises(greedy.CertificateSensitiveGreedyInvariantViolation):
        greedy.run_certificate_sensitive_greedy_acquisition_v1(
            model=target.model,
            audit=target.audit,
            threshold=target.threshold,
            registry=target.registry,
            arm=greedy.MatchedArm.SOURCE_CONSENSUS_PRIOR,
            prior=leaked,
        )
    target_evidence_trials = list(source.trials)
    target_evidence_trials[0] = replace(
        target_evidence_trials[0],
        raw_roll_forward_evidence_id=(
            target.registry.candidates[0]
            .source_candidate.physical_evidence_id
        ),
    )
    target_evidence_prior = greedy.freeze_source_consensus_prior_v1(
        source_family_id=_id("target-evidence-leak:family"),
        source_training_split_id=_id("target-evidence-leak:split"),
        applicable_feature_schema_id=greedy.FEATURE_SCHEMA_ID,
        votes=target_evidence_trials,
    )
    with pytest.raises(greedy.CertificateSensitiveGreedyInvariantViolation):
        greedy.run_certificate_sensitive_greedy_acquisition_v1(
            model=target.model,
            audit=target.audit,
            threshold=target.threshold,
            registry=target.registry,
            arm=greedy.MatchedArm.SOURCE_CONSENSUS_PRIOR,
            prior=target_evidence_prior,
        )

    stale = greedy.verify_certificate_sensitive_greedy_run_v1(
        model=target.model,
        audit=target.audit,
        threshold=target.threshold,
        registry=target.registry,
        arm=greedy.MatchedArm.SOURCE_CONSENSUS_PRIOR,
        prior=changed_prior,
        claimed=campaign.source_run,
        synthetic_materializer=True,
    )
    assert not stale.valid
    assert stale.replayed_run_id != stale.claimed_run_id
    assert source.prior_id != changed_prior.prior_id


def test_same_implementation_replay_and_worker_hint_identity(
    target: _Target,
    priors,
    campaign: greedy.CertificateSensitiveMatchedCampaignV1,
) -> None:
    source, ood, wrong = priors
    verification = greedy.verify_certificate_sensitive_greedy_run_v1(
        model=target.model,
        audit=target.audit,
        threshold=target.threshold,
        registry=target.registry,
        arm=greedy.MatchedArm.SOURCE_CONSENSUS_PRIOR,
        prior=source,
        claimed=campaign.source_run,
        synthetic_materializer=True,
    )
    assert verification.valid
    assert verification.same_implementation_replay
    assert not verification.independent_verifier
    assert verification.replayed_run_id == campaign.source_run.run_id

    parallel = greedy.run_certificate_sensitive_matched_campaign_v1(
        model=target.model,
        audit=target.audit,
        threshold=target.threshold,
        registry=target.registry,
        source_prior=source,
        ood_prior=ood,
        wrong_prior=wrong,
        synthetic_materializer=True,
        max_workers=2,
    )
    assert parallel == campaign
    assert parallel.campaign_id == campaign.campaign_id
