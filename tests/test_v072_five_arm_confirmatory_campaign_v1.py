from __future__ import annotations

import copy
from dataclasses import replace
import inspect

import pytest

from acfqp import target_preauthorization_selector_v2 as selector
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import verified_source_acquisition_archive_v2 as source_v2
from acfqp import v072_five_arm_confirmatory_campaign_v1 as campaign


@pytest.fixture(scope="module")
def source_authority() -> campaign.DevelopmentSourcePriorAuthorityV1:
    return campaign.freeze_development_source_prior_authority_v1()


@pytest.fixture(scope="module")
def source_attestation(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
) -> campaign.DevelopmentSourcePriorIndependentAttestationV1:
    return (
        campaign.verify_development_source_prior_authority_independently_v1(
            source_authority
        )
    )


def test_registered_five_arm_entry_remains_fail_closed() -> None:
    with pytest.raises(campaign.RegisteredV072FiveArmCampaignLockedV1):
        campaign.run_registered_v072_five_arm_campaign_v1(
            status="CONDITIONAL_PLAN_CERTIFICATE",
            accepted_draws=0,
        )
    assert campaign.REGISTERED_EXECUTION_STATUS.endswith(
        "TARGET_LOCKED_GATE_NOT_RUN"
    )
    assert campaign.SAMPLE_EFFICIENCY_GATE_STATUS == "NOT_RUN"


def test_development_source_prior_is_real_typed_proposal_only_evidence(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
    source_attestation: (
        campaign.DevelopmentSourcePriorIndependentAttestationV1
    ),
) -> None:
    assert len(source_authority.contexts) == 2
    assert len(source_authority.trials) == 504
    assert len(source_authority.consensus) == 252
    assert source_attestation.authority_id == source_authority.authority_id
    assert source_attestation.source_raw_accepted_draws == 504 * 256
    assert source_attestation.applied_consensus_count == 252
    assert all(
        item.disposition
        is source_v2.FeatureConsensusDispositionV2.APPLIED
        for item in source_authority.consensus
    )
    assert any(
        item.multiplier != source_v2.NEUTRAL_PRIOR_MULTIPLIER
        for item in source_authority.consensus
    )
    assert isinstance(
        source_authority.source_prior_binding,
        selector.VerifiedSourcePriorBindingV2,
    )
    assert source_authority.source_prior_binding.may_certify is False
    assert (
        source_authority.ood_abstention.source_numerical_inputs_absent
        is True
    )
    document = source_authority.to_document()
    assert document["source_quantities_are_proposal_only"]
    assert document["source_quantities_in_certificate_inputs"] == 0
    assert document["caller_supplied_gain"] is False
    assert document["caller_supplied_rank"] is False
    assert document["caller_supplied_multiplier"] is False
    assert document["registered_target_evidence"] is False


def test_source_authority_accepts_no_target_or_score_input() -> None:
    assert tuple(
        inspect.signature(
            campaign.freeze_development_source_prior_authority_v1
        ).parameters
    ) == ()
    forbidden = {
        "target",
        "registry",
        "gain",
        "score",
        "rank",
        "multiplier",
        "outcome",
        "status",
    }
    assert forbidden.isdisjoint(
        inspect.signature(
            campaign.freeze_development_source_prior_authority_v1
        ).parameters
    )


def test_source_independent_replay_does_not_call_production_helpers(
    monkeypatch: pytest.MonkeyPatch,
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("production source helper was called")

    monkeypatch.setattr(campaign, "_source_tape_replay", forbidden)
    monkeypatch.setattr(
        campaign,
        "_replay_development_source_consensus",
        forbidden,
    )
    attestation = (
        campaign.verify_development_source_prior_authority_independently_v1(
            source_authority
        )
    )
    assert attestation.authority_id == source_authority.authority_id


def test_source_trial_tape_and_consensus_tampering_fail(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
) -> None:
    attacked_tape = copy.deepcopy(source_authority)
    object.__setattr__(
        attacked_tape.trials[0],
        "after_success_count",
        attacked_tape.trials[0].after_success_count + 1,
    )
    with pytest.raises(
        campaign.V072FiveArmCampaignInvariantViolation,
        match="source-prior replay",
    ):
        campaign.verify_development_source_prior_authority_independently_v1(
            attacked_tape
        )

    attacked_consensus = copy.deepcopy(source_authority)
    object.__setattr__(
        attacked_consensus.consensus[0],
        "multiplier",
        source_v2.NEUTRAL_PRIOR_MULTIPLIER,
    )
    with pytest.raises(
        campaign.V072FiveArmCampaignInvariantViolation,
        match="source consensus",
    ):
        campaign.verify_development_source_prior_authority_independently_v1(
            attacked_consensus
        )


def test_source_and_confirmatory_identities_are_disjoint(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
) -> None:
    source_ids = {
        source_authority.source_archive_id,
        source_authority.authority_id,
        source_authority.source_prior_binding.source_prior_binding_id,
        *(item.context_id for item in source_authority.contexts),
        *(item.trial_id for item in source_authority.trials),
    }
    registered_ids = {
        prereg.DRAFT_PREREGISTRATION_ID,
        *prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS,
    }
    assert source_ids.isdisjoint(registered_ids)
    assert all(
        item.to_document()["registered_target_evidence"] is False
        for item in source_authority.trials
    )


def test_protocol_freezes_context_major_arm_order_and_no_early_stop(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
    source_attestation: (
        campaign.DevelopmentSourcePriorIndependentAttestationV1
    ),
) -> None:
    protocol = campaign.freeze_development_five_arm_protocol_v1(
        source_authority=source_authority,
        source_attestation=source_attestation,
    )
    assert protocol.arm_order == prereg.ARM_ORDER
    assert protocol.context_key == (
        "V072_DEVELOPMENT_P4_FIVE_ARM_MECHANICS_V1"
    )
    assert "K4" not in protocol.context_key
    assert protocol.arm_order == (
        "SOURCE_CONSENSUS_PRIOR",
        "NO_PRIOR",
        "WRONG_CONSENSUS_PRIOR",
        "OOD_ABSTENTION",
        "MATCHED_DIRECT_GROUND",
    )
    assert protocol.occurrence_replacement_allowed is False
    assert protocol.campaign_early_stop_allowed is False
    assert protocol.caller_terminal_input_allowed is False
    assert protocol.maximum_adaptive_rounds == 2
    assert protocol.matched_scientific_endpoint_authority is False


def test_protocol_rejects_wrong_attestation_and_rerolled_arm_order(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
    source_attestation: (
        campaign.DevelopmentSourcePriorIndependentAttestationV1
    ),
) -> None:
    wrong = replace(
        source_attestation,
        source_archive_id=source_attestation.authority_id,
    )
    with pytest.raises(
        campaign.V072FiveArmCampaignInvariantViolation,
        match="matching source attestation",
    ):
        campaign.freeze_development_five_arm_protocol_v1(
            source_authority=source_authority,
            source_attestation=wrong,
        )
    protocol = campaign.freeze_development_five_arm_protocol_v1(
        source_authority=source_authority,
        source_attestation=source_attestation,
    )
    with pytest.raises(
        campaign.V072FiveArmCampaignInvariantViolation,
        match="rerolled",
    ):
        replace(protocol, arm_order=tuple(reversed(protocol.arm_order)))


def test_shared_context_binding_preserves_native_p4_and_direct_contexts(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
    source_attestation: (
        campaign.DevelopmentSourcePriorIndependentAttestationV1
    ),
) -> None:
    protocol = campaign.freeze_development_five_arm_protocol_v1(
        source_authority=source_authority,
        source_attestation=source_attestation,
    )
    binding = campaign.freeze_development_shared_context_binding_v1(
        protocol=protocol
    )
    assert binding.mechanics_context_key == protocol.context_key
    assert tuple(
        arm for arm, _ in binding.arm_native_context_bindings
    ) == prereg.ARM_ORDER
    assert len(
        {context_id for _, context_id in binding.arm_native_context_bindings}
    ) == 2
    assert binding.scientific_matched_pair is False
    assert binding.matched_endpoint_authority is False
    assert binding.registered_target_evidence is False


def test_all_five_logical_occurrence_ids_are_arm_bound_and_disjoint(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
    source_attestation: (
        campaign.DevelopmentSourcePriorIndependentAttestationV1
    ),
) -> None:
    protocol = campaign.freeze_development_five_arm_protocol_v1(
        source_authority=source_authority,
        source_attestation=source_attestation,
    )
    occurrence_ids = tuple(
        campaign.development_logical_occurrence_id_v1(
            protocol=protocol,
            arm=arm,
        )
        for arm in prereg.ARM_ORDER
    )
    assert len(occurrence_ids) == len(set(occurrence_ids)) == 5
    with pytest.raises(
        campaign.V072FiveArmCampaignInvariantViolation,
        match="frozen protocol arm",
    ):
        campaign.development_logical_occurrence_id_v1(
            protocol=protocol,
            arm="UNREGISTERED_REPLACEMENT_ARM",
        )


def test_arm_prior_inputs_are_typed_proposal_only_and_not_caller_scores(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
    source_attestation: (
        campaign.DevelopmentSourcePriorIndependentAttestationV1
    ),
) -> None:
    source = campaign.development_prior_inputs_for_arm_v1(
        arm=selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
        source_authority=source_authority,
        source_attestation=source_attestation,
    )
    wrong = campaign.development_prior_inputs_for_arm_v1(
        arm=selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
        source_authority=source_authority,
        source_attestation=source_attestation,
    )
    no_prior = campaign.development_prior_inputs_for_arm_v1(
        arm=selector.TargetSelectionArmV2.NO_PRIOR,
        source_authority=source_authority,
        source_attestation=source_attestation,
    )
    ood = campaign.development_prior_inputs_for_arm_v1(
        arm=selector.TargetSelectionArmV2.OOD_ABSTENTION,
        source_authority=source_authority,
        source_attestation=source_attestation,
    )
    assert source == (source_authority.source_prior_binding, None)
    assert wrong == (source_authority.source_prior_binding, None)
    assert no_prior == (None, None)
    assert ood == (None, source_authority.ood_abstention)
    assert source[0] is not None and source[0].may_certify is False
    assert ood[1] is not None
    assert ood[1].source_numerical_inputs_absent is True


def test_matched_direct_cannot_receive_adaptive_prior_inputs(
    source_authority: campaign.DevelopmentSourcePriorAuthorityV1,
    source_attestation: (
        campaign.DevelopmentSourcePriorIndependentAttestationV1
    ),
) -> None:
    with pytest.raises(
        campaign.V072FiveArmCampaignInvariantViolation,
        match="arm prior resolution",
    ):
        campaign.development_prior_inputs_for_arm_v1(
            arm="MATCHED_DIRECT_GROUND",  # type: ignore[arg-type]
            source_authority=source_authority,
            source_attestation=source_attestation,
        )
