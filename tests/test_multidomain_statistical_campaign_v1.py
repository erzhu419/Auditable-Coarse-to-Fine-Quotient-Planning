from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import inspect

import pytest

import acfqp.multidomain_statistical_campaign_v1 as campaign_module
from acfqp.domains.g2048 import G2048SafeChainKernel
from acfqp.multidomain_statistical_campaign_v1 import (
    G2048_TOTAL_OFFLINE_SAMPLES,
    HOEFFDING_CONFIDENCE_LOWER,
    HOEFFDING_FAMILY_TAIL_UPPER,
    HOEFFDING_RADIUS,
    IMPLEMENTATION_SHA256,
    CampaignDomain,
    EvidenceLevel,
    MultiDomainStatisticalCampaignInvariantViolation,
    STATISTICAL_CERTIFIED,
    SUCCESS_STATUS,
    build_g2048_statistical_rapm_v1,
    preregister_multidomain_statistical_campaign_v1,
    registered_g2048_aggregated_sample_ledger_v1,
    registered_g2048_d4_statistical_catalogue_v1,
    registered_primitive_schemas_v1,
    run_multidomain_statistical_campaign_v1,
    solve_g2048_statistical_h2_v1,
    verify_g2048_statistical_rapm_v1,
    verify_multidomain_statistical_campaign_v1,
)
from acfqp.query_local_refinement_v1 import canonical_lmb_query_kernel_v1

import test_observation_partial_rapm_v1 as observation_fixture_module


@pytest.fixture(scope="module")
def campaign_contract():
    source = observation_fixture_module.observation_contract.__wrapped__()
    catalogue = registered_g2048_d4_statistical_catalogue_v1()
    ledger = registered_g2048_aggregated_sample_ledger_v1(catalogue)
    preregistration = preregister_multidomain_statistical_campaign_v1(
        source["log"],
        source["profile"],
        source["authority"],
        catalogue,
        ledger,
    )
    lmb_kernel = canonical_lmb_query_kernel_v1()
    result = run_multidomain_statistical_campaign_v1(
        source["log"],
        source["profile"],
        source["authority"],
        catalogue,
        ledger,
        preregistration,
        lmb_kernel,
    )
    return {
        **source,
        "catalogue": catalogue,
        "ledger": ledger,
        "preregistration": preregistration,
        "lmb_kernel": lmb_kernel,
        "result": result,
    }


@pytest.fixture(scope="module")
def verified_campaign(campaign_contract):
    verification = verify_multidomain_statistical_campaign_v1(
        campaign_contract["log"],
        campaign_contract["profile"],
        campaign_contract["authority"],
        campaign_contract["catalogue"],
        campaign_contract["ledger"],
        campaign_contract["preregistration"],
        campaign_contract["lmb_kernel"],
        G2048SafeChainKernel(),
        campaign_contract["result"],
    )
    return {**campaign_contract, "verification": verification}


def test_production_apis_keep_g2048_kernel_and_queries_outside_construction() -> None:
    assert tuple(
        inspect.signature(build_g2048_statistical_rapm_v1).parameters
    ) == ("catalogue", "sample_ledger")
    assert tuple(
        inspect.signature(preregister_multidomain_statistical_campaign_v1).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "g2048_catalogue",
        "g2048_sample_ledger",
    )
    assert tuple(
        inspect.signature(run_multidomain_statistical_campaign_v1).parameters
    ) == (
        "observation_log",
        "semantics_profile",
        "observation_authority",
        "g2048_catalogue",
        "g2048_sample_ledger",
        "preregistration",
        "lmb_kernel",
    )
    assert "g2048_kernel" not in inspect.signature(
        run_multidomain_statistical_campaign_v1
    ).parameters
    assert "g2048_kernel" in inspect.signature(
        verify_multidomain_statistical_campaign_v1
    ).parameters


def test_two_registered_primitive_schemas_have_honest_distinct_claims() -> None:
    schemas = registered_primitive_schemas_v1()
    assert tuple(item.domain for item in schemas) == (
        CampaignDomain.LMB,
        CampaignDomain.G2048,
    )
    assert schemas[0].automatically_selected_within_schema is True
    assert schemas[0].abstraction_prior == (
        "observation_driven_complete_depth2_program_closure"
    )
    assert schemas[1].automatically_selected_within_schema is False
    assert schemas[1].abstraction_prior == (
        "known_exact_d4_automorphism_not_automatically_discovered"
    )
    assert len({item.schema_id for item in schemas}) == 2


def test_preregistration_freezes_twelve_heldout_occurrences_before_models(
    campaign_contract,
) -> None:
    preregistration = campaign_contract["preregistration"]
    assert preregistration.prospective_model_ids_absent is True
    assert preregistration.prospective_plan_ids_absent is True
    assert preregistration.query_family_not_passed_to_model_builders is True
    assert tuple(item.ordinal for item in preregistration.occurrences) == tuple(
        range(12)
    )
    assert sum(
        item.domain is CampaignDomain.LMB
        for item in preregistration.occurrences
    ) == 3
    assert sum(
        item.domain is CampaignDomain.G2048
        for item in preregistration.occurrences
    ) == 9
    assert all(
        item.delta == 0
        for item in preregistration.occurrences
        if item.domain is CampaignDomain.LMB
    )
    assert all(
        item.delta == Fraction(1, 20)
        for item in preregistration.occurrences
        if item.domain is CampaignDomain.G2048
    )
    assert preregistration.to_document().keys().isdisjoint(
        {"lmb_synthesis_result_id", "g2048_model_id", "selected_policy_id"}
    )


def test_exact_rational_hoeffding_union_certificate_is_calibrated(
    campaign_contract,
) -> None:
    model = campaign_contract["result"].g2048_model
    calibration = model.calibration
    assert calibration.radius == HOEFFDING_RADIUS == Fraction(1, 128)
    assert calibration.sample_count_per_row == 65_536
    assert calibration.exponent == 8
    assert calibration.taylor_degree == 13
    assert calibration.taylor_lower > 2800
    assert calibration.per_coordinate_tail_upper == Fraction(1, 1400)
    assert (
        calibration.family_tail_upper
        == HOEFFDING_FAMILY_TAIL_UPPER
        == Fraction(3, 350)
        < Fraction(1, 100)
    )
    assert (
        calibration.confidence_lower
        == HOEFFDING_CONFIDENCE_LOWER
        == Fraction(347, 350)
    )


def test_statistical_model_has_six_binary_simplex_rows_and_no_exact_overclaim(
    campaign_contract,
) -> None:
    ledger = campaign_contract["ledger"]
    model = campaign_contract["result"].g2048_model
    assert ledger.total_sample_count == G2048_TOTAL_OFFLINE_SAMPLES == 393_216
    assert ledger.individual_sample_trace_embedded is False
    assert ledger.trusted_sufficient_statistic_authority is True
    assert len(model.transitions) == 6
    assert model.learned_probability_rows == 6
    assert model.exact_quotient_claimed is False
    assert model.exact_sound_claimed is False
    for row in model.transitions:
        assert len(row.intervals) == 2
        assert sum(item.lower for item in row.intervals) <= 1
        assert sum(item.upper for item in row.intervals) >= 1
        assert row.evidence_level is EvidenceLevel.STATISTICAL_HIGH_PROBABILITY
    assert (
        verify_g2048_statistical_rapm_v1(
            campaign_contract["catalogue"],
            campaign_contract["ledger"],
            model,
        )
        == ()
    )


def test_g2048_robust_planner_enumerates_and_selects_the_safe_h2_schedule(
    campaign_contract,
) -> None:
    model = campaign_contract["result"].g2048_model
    occurrence = next(
        item
        for item in campaign_contract["preregistration"].occurrences
        if item.domain is CampaignDomain.G2048
    )
    certificate = solve_g2048_statistical_h2_v1(
        model, occurrence.occurrence_id
    )
    assert certificate.status == STATISTICAL_CERTIFIED
    assert len(certificate.candidate_policies) == 8
    assert certificate.selected_policy.schedule == (
        "survivor:toward_nonmerged",
        "survivor:away_from_nonmerged",
        "survivor:away_from_nonmerged",
    )
    assert certificate.selected_policy.reward_lower == Fraction(3, 64)
    assert certificate.selected_policy.reward_upper == Fraction(3, 64)
    assert certificate.selected_policy.failure_lower == Fraction(
        9_277_983, 2_147_483_648
    )
    assert certificate.selected_policy.failure_upper == Fraction(
        75_716_127, 2_147_483_648
    )
    assert certificate.selected_policy.failure_upper < Fraction(1, 20)
    assert certificate.normalized_regret_upper == 0
    assert certificate.exact_sound_claimed is False


def test_campaign_closes_partial_lmb_then_reuses_both_models(
    campaign_contract,
) -> None:
    result = campaign_contract["result"]
    assert result.status == SUCCESS_STATUS
    assert result.domain_count == 2
    assert result.lmb_heldout_result.exact_target_transition_query_count == 3
    assert result.lmb_heldout_result.successor_transition_query_count == 0
    lmb = tuple(
        item
        for item in result.occurrences
        if item.occurrence.domain is CampaignDomain.LMB
    )
    g2048 = tuple(
        item
        for item in result.occurrences
        if item.occurrence.domain is CampaignDomain.G2048
    )
    assert tuple(item.exact_target_transition_calls for item in lmb) == (3, 0, 0)
    assert tuple(item.reused_frozen_model for item in lmb) == (False, True, True)
    assert all(item.reward_lower == 1 and item.failure_upper == 0 for item in lmb)
    assert all(item.evidence_level is EvidenceLevel.EXACT_SOUND for item in lmb)
    assert len(g2048) == 9
    assert tuple(item.reused_frozen_model for item in g2048) == (
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    )
    assert all(item.online_statistical_samples == 0 for item in g2048)
    assert all(
        item.evidence_level is EvidenceLevel.STATISTICAL_HIGH_PROBABILITY
        for item in g2048
    )


def test_campaign_preserves_native_sample_tax_without_claiming_savings(
    campaign_contract,
) -> None:
    result = campaign_contract["result"]
    work = result.work
    assert work.logical_occurrences == 12
    assert work.lmb_program_candidates == 6650
    assert work.lmb_plan_candidates == 16
    assert work.lmb_exact_target_transition_calls == 3
    assert work.g2048_offline_logged_samples == 393_216
    assert work.g2048_statistical_policy_candidates == 72
    assert work.g2048_online_samples == 0
    assert work.exact_sound_certificates == 3
    assert work.statistical_high_probability_certificates == 9
    assert work.sample_efficiency_claimed is False
    assert work.official_scalar_cost is None
    assert work.official_n_break_even is None
    assert result.sample_efficiency_claimed is False
    assert result.official_execution_allowed is False


def test_production_campaign_does_not_resolve_or_call_a_g2048_kernel(
    monkeypatch: pytest.MonkeyPatch,
    campaign_contract,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("production campaign called the G2048 kernel")

    monkeypatch.setattr(G2048SafeChainKernel, "step", forbidden)
    replay = run_multidomain_statistical_campaign_v1(
        campaign_contract["log"],
        campaign_contract["profile"],
        campaign_contract["authority"],
        campaign_contract["catalogue"],
        campaign_contract["ledger"],
        campaign_contract["preregistration"],
        campaign_contract["lmb_kernel"],
    )
    assert replay.result_id == campaign_contract["result"].result_id


def test_exact_standalone_verifier_contains_truth_without_promoting_evidence(
    verified_campaign,
) -> None:
    verification = verified_campaign["verification"]
    assert verification.verified
    assert verification.failures == ()
    assert verification.exact_g2048_value == Fraction(3, 64)
    assert verification.exact_g2048_failure == Fraction(99, 5000)
    assert verification.production_g2048_kernel_access == 0
    assert verification.verification_lane == "standalone_evaluation"
    assert verification.exact_sound_statistical_promotion_authorized is False


def test_sample_count_splice_fails_before_statistical_model_construction(
    campaign_contract,
) -> None:
    ledger = campaign_contract["ledger"]
    first = ledger.count_rows[0]
    bad_first = replace(
        first,
        destination_counts=(
            first.destination_counts[0] - 1,
            first.destination_counts[1] + 1,
        ),
    )
    bad_ledger = replace(
        ledger,
        count_rows=(bad_first, *ledger.count_rows[1:]),
    )
    # Alternate valid counts can build a different statistical model, but the
    # source identity was frozen before the held-out campaign.  The old
    # preregistration therefore cannot authorize it.
    changed_model = build_g2048_statistical_rapm_v1(
        campaign_contract["catalogue"], bad_ledger
    )
    assert changed_model.model_id != campaign_contract["result"].g2048_model.model_id
    with pytest.raises(
        MultiDomainStatisticalCampaignInvariantViolation,
        match="reconstruction mismatch",
    ):
        run_multidomain_statistical_campaign_v1(
            campaign_contract["log"],
            campaign_contract["profile"],
            campaign_contract["authority"],
            campaign_contract["catalogue"],
            bad_ledger,
            campaign_contract["preregistration"],
            campaign_contract["lmb_kernel"],
        )


def test_occurrence_order_and_evidence_level_overclaims_fail_closed(
    campaign_contract,
) -> None:
    preregistration = campaign_contract["preregistration"]
    with pytest.raises(MultiDomainStatisticalCampaignInvariantViolation):
        replace(
            preregistration,
            occurrences=(
                preregistration.occurrences[1],
                preregistration.occurrences[0],
                *preregistration.occurrences[2:],
            ),
        )
    statistical = next(
        item
        for item in campaign_contract["result"].occurrences
        if item.occurrence.domain is CampaignDomain.G2048
    )
    with pytest.raises(MultiDomainStatisticalCampaignInvariantViolation):
        replace(statistical, evidence_level=EvidenceLevel.EXACT_SOUND)
    with pytest.raises(MultiDomainStatisticalCampaignInvariantViolation):
        replace(
            campaign_contract["result"],
            statistical_exact_sound_claimed=True,
        )


def test_nested_runtime_substitution_is_rejected_before_content_comparison(
    campaign_contract,
) -> None:
    class Duck:
        pass

    with pytest.raises(
        MultiDomainStatisticalCampaignInvariantViolation,
        match="substituted nested authorities",
    ):
        replace(
            campaign_contract["result"],
            g2048_model=Duck(),  # type: ignore[arg-type]
        )


def test_canonical_ids_and_deterministic_replay_are_frozen(campaign_contract) -> None:
    result = campaign_contract["result"]
    assert campaign_contract["catalogue"].catalogue_id == (
        "1c97e476c25b0a1f0f37ce2796ae4cf9bb138bf29dbd80271792e2ef988dbcb1"
    )
    assert campaign_contract["ledger"].ledger_id == (
        "07793df8d27bacbd68f40b878c8de8483d03c22b6e323d5477dce06806154f7e"
    )
    assert result.g2048_model.model_id == (
        "78a3ed52d6d7284d8690708b2177b962c6cffbd33064925efe66f6fa1f520d9d"
    )
    assert result.result_id == (
        "e536ace0665fc7c01fb6d79a025a17eba4adb1d3950cfe14e7a627cfc6886c78"
    )
    replay = run_multidomain_statistical_campaign_v1(
        campaign_contract["log"],
        campaign_contract["profile"],
        campaign_contract["authority"],
        campaign_contract["catalogue"],
        campaign_contract["ledger"],
        campaign_contract["preregistration"],
        campaign_contract["lmb_kernel"],
    )
    assert replay.to_document() == result.to_document()


def test_implementation_authority_and_public_claim_locks_are_frozen() -> None:
    assert campaign_module._observed_implementation_sha256() == IMPLEMENTATION_SHA256
    assert IMPLEMENTATION_SHA256 == (
        "fe229af2d937dec412d28c3e9f7cefd949038714a9ca3bf46d0dda1ffe9bfdff"
    )
    assert campaign_module.CONTRACT_VERSION == "1.23.0"
    assert "verify_multidomain_statistical_campaign_v1" in campaign_module.__all__
