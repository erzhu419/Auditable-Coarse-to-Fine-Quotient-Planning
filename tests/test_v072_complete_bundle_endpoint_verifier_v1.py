from __future__ import annotations

import inspect
from itertools import combinations

import pytest

from acfqp import v072_five_arm_confirmatory_campaign_v1 as campaign
from acfqp import v072_complete_bundle_endpoint_verifier_v1 as endpoint
from acfqp import target_preauthorization_selector_v2 as selector


@pytest.fixture(scope="module")
def complete_bundle(
) -> campaign.DevelopmentFiveArmCampaignRunV1:
    return campaign.run_development_five_arm_campaign_v1()


@pytest.fixture(scope="module")
def complete_verification(
    complete_bundle: campaign.DevelopmentFiveArmCampaignRunV1,
) -> endpoint.DevelopmentCompleteBundleIndependentAttestationV1:
    return endpoint.verify_development_complete_bundle_v1(
        bundle=complete_bundle
    )


def test_registered_complete_bundle_verifier_remains_locked() -> None:
    with pytest.raises(
        endpoint.RegisteredCompleteBundleEndpointVerifierLockedV1
    ):
        endpoint.verify_registered_v072_complete_bundle_v1(
            endpoint="CONDITIONAL_PLAN_CERTIFICATE",
            status="PASS",
            accepted_draws=0,
        )
    assert endpoint.REGISTERED_EXECUTION_STATUS.endswith(
        "TARGET_LOCKED_GATE_NOT_RUN"
    )


def test_development_verifier_accepts_only_one_typed_bundle_argument() -> None:
    signature = inspect.signature(
        endpoint.verify_development_complete_bundle_v1
    )
    assert tuple(signature.parameters) == ("bundle",)
    bundle_parameter = signature.parameters["bundle"]
    assert bundle_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    forbidden = {
        "endpoint",
        "status",
        "terminal",
        "outcome",
        "accepted_draws",
        "work",
        "attestation_id",
    }
    assert forbidden.isdisjoint(signature.parameters)


def test_development_verifier_rejects_a_foreign_bundle_type() -> None:
    with pytest.raises(
        endpoint.V072CompleteBundleEndpointVerificationFailure,
        match="exact five-arm campaign type",
    ):
        endpoint.verify_development_complete_bundle_v1(bundle=object())


@pytest.mark.parametrize(
    "forbidden_argument",
    (
        {"endpoint": "CONDITIONAL_PLAN_CERTIFICATE"},
        {"status": "PASS"},
        {"accepted_draws": 1},
    ),
)
def test_development_verifier_rejects_caller_claims(
    forbidden_argument: dict[str, object],
) -> None:
    with pytest.raises(TypeError):
        endpoint.verify_development_complete_bundle_v1(
            bundle=object(),
            **forbidden_argument,
        )


def test_complete_bundle_replays_without_endpoint_authority(
    complete_bundle: campaign.DevelopmentFiveArmCampaignRunV1,
    complete_verification:
        endpoint.DevelopmentCompleteBundleIndependentAttestationV1,
) -> None:
    verified = complete_verification
    assert verified.campaign_id == complete_bundle.campaign_id
    assert verified.logical_occurrence_denominator == 5
    assert verified.online_accepted_draws == 239_744
    assert verified.source_offline_accepted_draws == 129_024
    assert verified.terminal_classes == ("PLAN_CERTIFICATE",) * 5
    assert verified.registered_target_evidence is False
    assert verified.matched_scientific_endpoint_authority is False
    assert verified.sample_efficiency_gate_status == "NOT_RUN"
    assert len(verified.attestation_id) == 64


def test_complete_bundle_has_exact_frozen_order_and_typed_terminals(
    complete_bundle: campaign.DevelopmentFiveArmCampaignRunV1,
) -> None:
    assert tuple(
        item.arm.value for item in complete_bundle.adaptive_runs
    ) + ("MATCHED_DIRECT_GROUND",) == campaign.ARM_ORDER
    assert all(
        item.terminal_class.value == "PLAN_CERTIFICATE"
        and item.terminal_code.value
        == "PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD"
        and len(item.handoffs) == 2
        for item in complete_bundle.adaptive_runs
    )
    assert (
        complete_bundle.direct_run.terminal_class.value
        == "PLAN_CERTIFICATE"
    )
    assert (
        complete_bundle.direct_run.terminal_code.value
        == "MATCHED_DIRECT_GROUND_CERTIFIED"
    )


def test_prior_arms_remain_proposal_only_and_neutral_controls_match(
    complete_bundle: campaign.DevelopmentFiveArmCampaignRunV1,
) -> None:
    by_arm = {
        item.arm: item for item in complete_bundle.adaptive_runs
    }
    for arm in (
        selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
        selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
    ):
        run = by_arm[arm]
        assert any(
            score.multiplier != 1
            for selection in run.round_selections
            for score in selection.scores
        )
        certificate_model_ids = {
            item.model_pair.quotient_planner_projection.planner_model.model_id
            for item in run.postbuild_results
        }
        proposal_model_ids = {
            item.resolution_model_id
            for selection in run.round_selections
            for item in selection.counterfactuals
            if item.resolution_model_id is not None
        }
        assert certificate_model_ids.isdisjoint(proposal_model_ids)
    neutral = by_arm[selector.TargetSelectionArmV2.NO_PRIOR]
    ood = by_arm[selector.TargetSelectionArmV2.OOD_ABSTENTION]
    def signature(run: object) -> tuple[object, ...]:
        return tuple(
            tuple(
                (
                    next(
                        score.feature_key
                        for score in selection.scores
                        if score.candidate_id == entry.candidate_id
                    ),
                    entry.score,
                    entry.gain,
                    entry.exact_draw_upper,
                    entry.gain_eligible,
                    entry.cap_eligible,
                )
                for entry in selection.schedule.entries
            )
            for selection in run.round_selections
        )

    def selected(run: object) -> tuple[str, ...]:
        return tuple(
            next(
                score.feature_key
                for score in selection.scores
                if score.candidate_id
                == selection.authorization.selected_candidate_id
            )
            for selection in run.round_selections
        )

    assert signature(neutral) == signature(ood)
    assert selected(neutral) == selected(ood)


def test_adaptive_arm_cold_suffix_and_model_identities_are_disjoint(
    complete_bundle: campaign.DevelopmentFiveArmCampaignRunV1,
) -> None:
    inventories = []
    for run in complete_bundle.adaptive_runs:
        inventories.append(
            {
                run.run_id,
                *(item.handoff_id for item in run.handoffs),
                *(
                    proof.range_proof_id
                    for proof in (
                        run.handoffs[0]
                        .prior_cold_raw_commitment_ranges
                    )
                ),
                *(
                    proof.range_proof_id
                    for handoff in run.handoffs
                    for proof in handoff.raw_commitment_ranges
                ),
                *(
                    item.result_id for item in run.postbuild_results
                ),
            }
        )
    assert all(
        not inventories[left] & inventories[right]
        for left, right in combinations(range(4), 2)
    )


def test_parallel_and_serial_campaigns_are_byte_identical(
    complete_bundle: campaign.DevelopmentFiveArmCampaignRunV1,
) -> None:
    serial = (
        campaign
        .replay_development_five_arm_campaign_serial_equivalence_v1(
            complete_bundle
        )
    )
    assert tuple(item.run_id for item in serial.adaptive_runs) == tuple(
        item.run_id for item in complete_bundle.adaptive_runs
    )
    assert tuple(
        item.attestation_id for item in serial.adaptive_attestations
    ) == tuple(
        item.attestation_id
        for item in complete_bundle.adaptive_attestations
    )
    assert serial.direct_run.run_id == complete_bundle.direct_run.run_id
    assert (
        serial.direct_attestation.verification_id
        == complete_bundle.direct_attestation.verification_id
    )
    assert (
        serial.reconciliation_ledger.ledger_id
        == complete_bundle.reconciliation_ledger.ledger_id
    )
    assert (
        serial.reconciliation_attestation.attestation_id
        == complete_bundle.reconciliation_attestation.attestation_id
    )
    assert serial.campaign_id == complete_bundle.campaign_id
    assert serial.to_document() == complete_bundle.to_document()


def test_direct_arm_never_uses_quotient_prior_or_local_recovery(
    complete_bundle: campaign.DevelopmentFiveArmCampaignRunV1,
) -> None:
    direct = complete_bundle.direct_run
    assert direct.source_prior_reads == 0
    assert direct.quotient_planner_calls == 0
    assert direct.local_promotion_calls == 0
    assert direct.fallback_calls == 0
    assert direct.crn_cost_discount_draws == 0


def test_occurrence_identity_transplant_fails_closed(
    complete_bundle: campaign.DevelopmentFiveArmCampaignRunV1,
) -> None:
    epoch = (
        complete_bundle.adaptive_runs[0]
        .handoffs[0].request.parent_epoch
    )
    original = epoch.logical_occurrence_id
    object.__setattr__(
        epoch,
        "logical_occurrence_id",
        complete_bundle.adaptive_runs[1].logical_occurrence_id,
    )
    try:
        with pytest.raises(
            endpoint.V072CompleteBundleEndpointVerificationFailure
        ):
            endpoint.verify_development_complete_bundle_v1(
                bundle=complete_bundle
            )
    finally:
        object.__setattr__(epoch, "logical_occurrence_id", original)


def test_endpoint_replay_never_calls_production_campaign_helpers(
    complete_bundle: campaign.DevelopmentFiveArmCampaignRunV1,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("production campaign helper was called")

    monkeypatch.setattr(
        campaign,
        "run_development_five_arm_campaign_v1",
        forbidden,
    )
    monkeypatch.setattr(campaign, "_content_id", forbidden)
    monkeypatch.setattr(
        campaign,
        "development_logical_occurrence_id_v1",
        forbidden,
    )
    monkeypatch.setattr(
        campaign.DevelopmentFiveArmCampaignRunV1,
        "_payload",
        forbidden,
    )
    verified = endpoint.verify_development_complete_bundle_v1(
        bundle=complete_bundle
    )
    assert verified.campaign_id == complete_bundle.campaign_id
