from __future__ import annotations

from dataclasses import replace
import inspect

import pytest

from acfqp import v075_campaign_reconciliation_v1 as reconciliation
from acfqp import v075_complete_bundle_endpoint_verifier_v1 as endpoint
from acfqp import v075_public_campaign_authority_v1 as public


def _campaign(
    *,
    kinds: dict[
        int, reconciliation.V075ConstructionTerminalEvidenceKindV1
    ]
    | None = None,
    draws: dict[int, int] | None = None,
) -> reconciliation.V075ConstructionCampaignReconciliationV1:
    kinds = {} if kinds is None else kinds
    draws = {} if draws is None else draws
    plan = reconciliation.freeze_v075_scientific_occurrence_plan_v1(
        public.V075PublicFamilyGenerationV1()
    )
    source_work = (
        reconciliation.issue_v075_construction_source_work_fixture_v1(
            plan=plan,
            fixture_nonce="endpoint-source-fixture",
            offline_draw_count=999,
        )
    )
    default_draws = {
        "SOURCE_CONSENSUS_PRIOR": 10,
        "NO_PRIOR": 20,
        "WRONG_CONSENSUS_PRIOR": 25,
        "OOD_ABSTENTION": 30,
        "MATCHED_DIRECT_GROUND": 10,
    }
    verified = []
    for entry in plan.entries:
        evidence = (
            reconciliation.issue_v075_construction_occurrence_fixture_v1(
                plan_entry=entry,
                fixture_nonce=f"endpoint-occurrence-{entry.scientific_ordinal}",
                online_draw_count=draws.get(
                    entry.scientific_ordinal,
                    default_draws[entry.arm] + entry.context_ordinal,
                ),
                terminal_evidence_kind=kinds.get(
                    entry.scientific_ordinal,
                    reconciliation
                    .V075ConstructionTerminalEvidenceKindV1
                    .EXACT_VALID_PLAN,
                ),
            )
        )
        verified.append(
            reconciliation.verify_v075_construction_occurrence_fixture_v1(
                evidence
            )
        )
    return reconciliation.reconcile_v075_construction_fixture_campaign_v1(
        plan=plan,
        source_offline_work=source_work,
        occurrence_verifications=tuple(reversed(verified)),
    )


def _endpoint(
    **kwargs,
) -> endpoint.V075ConstructionCompleteBundleEndpointVerificationV1:
    campaign = _campaign(**kwargs)
    bundle = endpoint.mint_v075_construction_complete_bundle_v1(campaign)
    return endpoint.verify_v075_construction_complete_bundle_endpoint_v1(
        bundle
    )


def test_pass_requires_all_15_exact_valid_plans_and_contextwise_draw_rules() -> None:
    result = _endpoint()
    assert result.verdict is endpoint.V075ScientificEndpointVerdictV1.PASS
    assert result.plan_certificate_count == 15
    assert result.infeasibility_certificate_count == 0
    assert result.noncertificate_count == 0
    assert len(result.context_endpoints) == 3
    assert all(item.context_pass for item in result.context_endpoints)
    assert all(
        item.source_online_draws < item.no_prior_online_draws
        for item in result.context_endpoints
    )
    assert all(
        item.source_online_draws <= item.matched_direct_online_draws
        for item in result.context_endpoints
    )


@pytest.mark.parametrize(
    "draws",
    (
        # Context 0: SOURCE must be strictly lower than NO_PRIOR.
        {0: 20},
        # Context 1: SOURCE must be no greater than MATCHED_DIRECT.
        {5: 13, 9: 12},
    ),
)
def test_complete_valid_contrary_draw_result_is_scientific_fail(
    draws: dict[int, int],
) -> None:
    result = _endpoint(draws=draws)
    assert result.verdict is endpoint.V075ScientificEndpointVerdictV1.FAIL
    assert result.plan_certificate_count == 15
    assert result.noncertificate_count == 0


@pytest.mark.parametrize(
    ("kind", "expected_infeasible", "expected_noncertificate"),
    (
        (
            reconciliation.V075ConstructionTerminalEvidenceKindV1
            .TOTAL_LIFT_FAILED,
            0,
            1,
        ),
        (
            reconciliation.V075ConstructionTerminalEvidenceKindV1
            .CAP_EXHAUSTED,
            0,
            1,
        ),
        (
            reconciliation.V075ConstructionTerminalEvidenceKindV1
            .EXACT_INFEASIBLE,
            1,
            0,
        ),
    ),
)
def test_complete_nonpass_terminal_is_retained_as_scientific_fail(
    kind: reconciliation.V075ConstructionTerminalEvidenceKindV1,
    expected_infeasible: int,
    expected_noncertificate: int,
) -> None:
    result = _endpoint(kinds={7: kind})
    assert result.verdict is endpoint.V075ScientificEndpointVerdictV1.FAIL
    assert result.plan_certificate_count == 14
    assert result.infeasibility_certificate_count == expected_infeasible
    assert result.noncertificate_count == expected_noncertificate
    assert (
        result.plan_certificate_count
        + result.infeasibility_certificate_count
        + result.noncertificate_count
        == 15
    )


@pytest.mark.parametrize(
    "kind",
    (
        reconciliation.V075ConstructionTerminalEvidenceKindV1
        .PROTOCOL_FAILURE,
        reconciliation.V075ConstructionTerminalEvidenceKindV1
        .INTEGRITY_FAILURE,
    ),
)
def test_protocol_or_integrity_failure_invalidates_endpoint(
    kind: reconciliation.V075ConstructionTerminalEvidenceKindV1,
) -> None:
    campaign = _campaign(kinds={3: kind})
    bundle = endpoint.mint_v075_construction_complete_bundle_v1(campaign)
    with pytest.raises(
        endpoint.V075CompleteBundleProtocolOrIntegrityFailure
    ):
        endpoint.verify_v075_construction_complete_bundle_endpoint_v1(bundle)


def test_forged_pass_cannot_replace_a_derived_fail() -> None:
    failed = _endpoint(draws={0: 20})
    assert failed.verdict is endpoint.V075ScientificEndpointVerdictV1.FAIL
    with pytest.raises(endpoint.V075CompleteBundleEndpointInvariantViolation):
        replace(
            failed,
            verdict=endpoint.V075ScientificEndpointVerdictV1.PASS,
        )


def test_bundle_minting_replays_reconciliation_and_is_deterministic() -> None:
    campaign = _campaign()
    first = endpoint.mint_v075_construction_complete_bundle_v1(campaign)
    second = endpoint.mint_v075_construction_complete_bundle_v1(campaign)
    assert first == second
    assert first.bundle_id == second.bundle_id
    assert first.canonical_bytes == second.canonical_bytes
    first_endpoint = (
        endpoint.verify_v075_construction_complete_bundle_endpoint_v1(first)
    )
    second_endpoint = (
        endpoint.verify_v075_construction_complete_bundle_endpoint_v1(second)
    )
    assert first_endpoint == second_endpoint
    assert first_endpoint.verification_id == second_endpoint.verification_id


def test_reordered_or_deleted_reconciliation_cannot_be_bundled() -> None:
    campaign = _campaign()
    with pytest.raises(
        reconciliation.V075CampaignReconciliationInvariantViolation
    ):
        replace(campaign, occurrences=tuple(reversed(campaign.occurrences)))
    with pytest.raises(
        reconciliation.V075CampaignReconciliationInvariantViolation
    ):
        replace(campaign, occurrences=campaign.occurrences[:-1])


def test_byte_identical_occurrence_cannot_fill_two_denominator_slots() -> None:
    campaign = _campaign()
    duplicate = campaign.occurrences[:-1] + (campaign.occurrences[0],)
    with pytest.raises(
        reconciliation.V075CampaignReconciliationInvariantViolation
    ):
        replace(campaign, occurrences=duplicate)


def test_endpoint_locks_all_unrun_official_claims() -> None:
    result = _endpoint()
    document = result.to_document()
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate_status"] == "NOT_RUN"
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["construction_fixture_only"] is True
    assert document["production_evidence"] is False


def test_production_endpoint_remains_typed_not_ready() -> None:
    status = endpoint.v075_production_complete_bundle_endpoint_readiness_v1()
    document = status.to_document()
    assert document["production_complete_bundle_protocol_status"] == "NOT_READY"
    assert document["production_endpoint_verification_allowed"] is False
    assert document["construction_fixture_accepted_as_production"] is False
    with pytest.raises(
        endpoint.V075ProductionCompleteBundleEndpointNotReady
    ):
        endpoint.verify_v075_complete_bundle_endpoint_v1()


def test_endpoint_apis_accept_no_status_validity_or_expected_id_authority() -> None:
    for function in (
        endpoint.mint_v075_construction_complete_bundle_v1,
        endpoint.verify_v075_construction_complete_bundle_endpoint_v1,
    ):
        names = set(inspect.signature(function).parameters)
        assert not any(
            fragment in name
            for name in names
            for fragment in ("status", "valid", "expected")
        )
