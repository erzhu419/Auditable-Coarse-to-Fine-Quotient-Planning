from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

import acfqp.transfer_guided_acquisition_preregistration_v1 as prereg


def test_public_contexts_freeze_three_unseen_seven_vertex_geometries() -> None:
    contexts = prereg.registered_heldout_public_contexts_v2()
    assert tuple(item.context_key for item in contexts) == (
        "heldout_graph_k7_confirmatory_v1",
        "heldout_graph_w7_confirmatory_v1",
        "heldout_graph_k7_minus_two_confirmatory_v1",
    )
    assert tuple(item.topology.topology_id for item in contexts) == (
        "c4ad4934340b4fe0854a7f85d778a6ebec9a52337da6577426d5585a155a7b21",
        "1e8b9ee52ed801d75d3ad6e5038b3abf6e4e6e639312b4eb57b45d4bd060a19e",
        "4504dbc17e530161ca185d58efeae68e571a58190dca579f987a57700267a428",
    )
    assert tuple(
        item.maximum_physical_rows_per_confidence_epoch
        for item in contexts
    ) == (96, 48, 96)
    assert all(item.root_ranks == (1, 1, 2, 0, 0, 0, 0) for item in contexts)
    assert tuple(item.context_id for item in contexts) == (
        "5bf58b73e363ff73f65d778f039b46ec96d2176082b9c935423f3ef9bb45681a",
        "48a6f36af9ef5ff1ba9920d783d2435cedd9458c8383f48ccf40412ff55f0dda",
        "52363b3d6e6508e6734418103be98da18cd7aafe6657d24de16c2547c630ba7a",
    )


def test_public_documents_do_not_serialize_hidden_spawn_laws() -> None:
    for context in prereg.registered_heldout_public_contexts_v2():
        document = context.to_document()
        encoded = repr(document).lower()
        assert "rank_probabilities" not in document
        assert "spawn" not in encoded
        assert document["hidden_law_serialized"] is False
        assert document["target_execution_allowed"] is False


def test_environment_manifest_is_separate_frozen_and_preexecution() -> None:
    manifest = prereg.frozen_heldout_environment_manifest_v1()
    assert len(manifest.laws) == 3
    assert manifest.target_tapes_opened is False
    assert manifest.target_observations_generated == 0
    assert all(
        sum(
            (probability for _, probability in law.rank_probabilities),
            Fraction(0),
        )
        == 1
        for law in manifest.laws
    )
    assert all(
        law.role == "ENVIRONMENT_AUTHORITY_ONLY" for law in manifest.laws
    )
    assert tuple(item.law_id for item in manifest.laws) == (
        "434f67074a8be498fd8cc532fe780f4227f6f8233bc90a62fab6e8cb595a5f71",
        "801683343ef1973337e534f2d36ac6c8493717d240ef05677abd3a2abb72559c",
        "b0803f306f3d5ac79abd6e87fc713caedcceae3411f3172f88d103cb7b540347",
    )
    assert (
        manifest.manifest_id
        == "f1b158319b5c059786829fc6b5ca4cda60e0b49e9e173a3c70daa4c8a04100da"
    )


def test_preregistration_freezes_arms_caps_endpoints_and_all_gate_locks() -> None:
    frozen = prereg.freeze_transfer_guided_acquisition_preregistration_v1()
    document = frozen.to_document()
    assert frozen.arm_order == prereg.ARM_ORDER
    assert frozen.terminal_codes == prereg.TERMINAL_CODES
    assert frozen.physical_row_cap_sum_per_confidence_epoch == 240
    assert frozen.maximum_confidence_epochs_per_physical_row == 3
    assert frozen.maximum_promotions_per_physical_row == 2
    assert frozen.maximum_promotion_authorities_per_context == 2
    assert (
        frozen.maximum_arm_bound_row_epoch_authorities_per_arm
        == 2 * frozen.physical_row_cap_sum_per_confidence_epoch
        == 480
    )
    assert 480 <= frozen.family_row_epoch_cap == 512
    assert frozen.maximum_campaign_row_epoch_authorities == 2_400
    assert frozen.row_epoch_beta == Fraction(1, 300_000)
    assert frozen.campaign_joint_tail_upper == Fraction(1, 125)
    assert frozen.campaign_confidence_lower == Fraction(124, 125)
    assert frozen.initial_discovery_draws_per_physical_row == 64
    assert frozen.initial_validation_draws_per_physical_row == 2_048
    assert frozen.maximum_initial_accepted_draw_cap_per_arm == 506_880
    assert frozen.promotion_validation_draws_per_round == 2_048
    assert frozen.new_child_discovery_draws_per_physical_row == 64
    assert frozen.new_child_validation_draws_per_physical_row == 8_192
    assert frozen.maximum_new_child_action_rows_across_rounds == 19
    assert (
        frozen.maximum_two_round_incremental_draw_cap_per_arm
        == 160_960
    )
    assert frozen.confirmatory_execution_manifest_id is None
    assert frozen.confirmatory_profile_finalized is False
    assert (
        frozen.preregistration_id
        == prereg.DRAFT_PREREGISTRATION_ID
        == "7639f1ee57ee2d9a8c871a5f0270d15fdd92f712a735e2ae89b6155e057ba5c2"
    )
    assert prereg.SUPERSEDED_DRAFT_PREREGISTRATION_IDS == (
        "8b1e4747bb364ccddc04bb45d97a061c621650c907d31c979673f312acdffd29",
        "e368be24adad7870d95c8e5059455d31e035783394e48040d113258388eaf4d4",
    )
    assert frozen.anchor_commit_id is None
    assert frozen.target_execution_allowed is False
    assert document["sample_efficiency_gate_status"] == "NOT_RUN"
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["context_arm_occurrences"]["occurrence_count"] == 15
    assert document["formal_exact_iid_implementation_claimed"] is False
    assert document["formal_exact_iid_plan_certificate"] is False
    assert document["confirmatory_execution_manifest_id"] is None


@pytest.mark.parametrize(
    "change",
    (
        {"maximum_confidence_epochs_per_physical_row": 2},
        {"maximum_confidence_epochs_per_physical_row": 4},
        {"maximum_promotions_per_physical_row": 1},
        {"maximum_promotions_per_physical_row": 3},
        {"maximum_promotion_authorities_per_context": 1},
        {"maximum_promotion_authorities_per_context": 3},
        {"maximum_arm_bound_row_epoch_authorities_per_arm": 720},
    ),
)
def test_epoch_and_schedule_caps_cannot_be_conflated(
    change: dict[str, int],
) -> None:
    frozen = prereg.freeze_transfer_guided_acquisition_preregistration_v1()
    with pytest.raises(
        prereg.TransferGuidedAcquisitionPreregistrationInvariantViolation
    ):
        replace(frozen, **change)


def test_environment_and_public_roles_are_content_separated() -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    law = prereg.frozen_heldout_environment_manifest_v1().laws[0]
    assert context.context_id != law.law_id
    assert (
        prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        .preregistration_id
        not in {
            context.context_id,
            law.law_id,
            prereg.frozen_heldout_environment_manifest_v1().manifest_id,
        }
    )


def test_mutating_context_law_or_execution_state_fails_closed() -> None:
    context = prereg.registered_heldout_public_contexts_v2()[0]
    with pytest.raises(
        prereg.TransferGuidedAcquisitionPreregistrationInvariantViolation
    ):
        replace(context, risk_tolerance=Fraction(1, 10))

    manifest = prereg.frozen_heldout_environment_manifest_v1()
    with pytest.raises(
        prereg.TransferGuidedAcquisitionPreregistrationInvariantViolation
    ):
        replace(manifest, target_tapes_opened=True)
    with pytest.raises(
        prereg.TransferGuidedAcquisitionPreregistrationInvariantViolation
    ):
        replace(
            manifest.laws[0],
            rank_probabilities=((1, Fraction(1)),),
        )

    frozen = prereg.freeze_transfer_guided_acquisition_preregistration_v1()
    with pytest.raises(
        prereg.TransferGuidedAcquisitionPreregistrationInvariantViolation
    ):
        replace(frozen, target_execution_allowed=True)
    with pytest.raises(
        prereg.TransferGuidedAcquisitionPreregistrationInvariantViolation
    ):
        replace(frozen, row_epoch_beta=Fraction(1, 64_000))
    with pytest.raises(
        prereg.TransferGuidedAcquisitionPreregistrationInvariantViolation
    ):
        replace(
            frozen,
            maximum_two_round_incremental_draw_cap_per_arm=160_959,
        )
    with pytest.raises(
        prereg.TransferGuidedAcquisitionPreregistrationInvariantViolation
    ):
        replace(
            frozen,
            confirmatory_execution_manifest_id="a" * 64,
        )


def test_freeze_is_deterministic_and_has_no_observation_side_effect() -> None:
    first = prereg.freeze_transfer_guided_acquisition_preregistration_v1()
    second = prereg.freeze_transfer_guided_acquisition_preregistration_v1()
    assert first == second
    assert first.preregistration_id == second.preregistration_id
    assert (
        prereg.frozen_heldout_environment_manifest_v1()
        .target_observations_generated
        == 0
    )


def test_contaminated_development_family_is_explicitly_retired() -> None:
    document = (
        prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        .to_document()
    )
    retired = tuple(document["retired_development_dry_run_ids"])
    assert retired == prereg.RETIRED_DEVELOPMENT_DRY_RUN_IDS
    assert len(retired) == 8
    current = {
        *document["context_ids"],
        document["environment_manifest_id"],
        document["preregistration_id"],
    }
    assert current.isdisjoint(retired)
    assert (
        document["retired_development_dry_run_disposition"]
        == "DEVELOPMENT_SYNTHETIC_DRY_RUN_NOT_REGISTERED_TARGET_TAPE"
    )


def test_schedule_confidence_and_endpoint_semantics_are_frozen() -> None:
    document = (
        prereg.freeze_transfer_guided_acquisition_preregistration_v1()
        .to_document()
    )
    initial = document["initial_acquisition_schedule"]
    incremental = document["incremental_acquisition_schedule"]
    confidence = document["confidence_allocation"]
    direct = document["matched_direct_ground_profile"]

    assert initial["starts_cold"] is True
    assert initial["source_or_v068_target_rows_imported"] is False
    assert initial["accepted_draws_enter_online_endpoint"] is True
    assert incremental["fresh_parent_discovery_forbidden"] is True
    assert confidence["maximum_campaign_row_epoch_authorities"] == 2_400
    assert confidence["campaign_joint_tail_upper"] == {
        "numerator": 1,
        "denominator": 125,
    }
    assert confidence["proof_rule"] == (
        "FINITE_UNION_BOUND_NO_INDEPENDENCE_REQUIRED"
    )
    assert direct["validation_checkpoints"] == [2_048, 4_096, 8_192, 16_384]
    assert document["intermediate_peeking_allowed"] is False
    assert document["third_adaptive_round_allowed"] is False
    assert document["source_positive_coverage_required"] == {
        "required_contexts": 3,
        "registered_contexts": 3,
    }
