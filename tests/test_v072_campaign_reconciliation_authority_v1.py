from __future__ import annotations

from dataclasses import replace
import inspect

import pytest

from acfqp import v072_campaign_reconciliation_authority_v1 as authority
from acfqp import (
    v072_campaign_reconciliation_independent_verifier_v1
    as independent,
)
from acfqp import v072_incremental_materializer_v1 as materializer
from acfqp import v072_matched_direct_ground_baseline_v1 as direct
from acfqp import v072_synthetic_row_observation_adapter_v1 as row_adapter


def _row_occurrence(arm: str) -> authority.ReconciledOperationalOccurrenceV1:
    acquired = row_adapter.acquire_development_synthetic_initial_row_v2(
        arm=arm
    )
    return authority.reconcile_row_core_observation_series_v1(
        discovery_transcript=acquired.discovery_transcript,
        validation_history=acquired.validation_history,
    )


def _campaign(
    *occurrences: authority.ReconciledOperationalOccurrenceV1,
) -> authority.CampaignReconciliationLedgerV1:
    return authority.reconcile_campaign_v1(
        occurrences=tuple(
            sorted(occurrences, key=lambda item: item.occurrence_record_id)
        )
    )


def test_crn_pairing_retains_arm_bound_commitments_and_charges_both_arms() -> None:
    no_prior = _row_occurrence("NO_PRIOR")
    consensus = _row_occurrence("SOURCE_CONSENSUS_PRIOR")
    ledger = _campaign(no_prior, consensus)

    no_prior_by_stage = {
        item.stage: item for item in no_prior.draw_ranges
    }
    consensus_by_stage = {
        item.stage: item for item in consensus.draw_ranges
    }
    assert no_prior_by_stage.keys() == consensus_by_stage.keys()
    for stage in no_prior_by_stage:
        left = no_prior_by_stage[stage]
        right = consensus_by_stage[stage]
        assert left.crn_pairing_group_id == right.crn_pairing_group_id
        assert left.stream_id != right.stream_id
        assert left.first_commitment_id != right.first_commitment_id
        assert left.ordered_commitment_digest != right.ordered_commitment_digest

    assert ledger.logical_occurrence_denominator == 2
    assert ledger.noncertificate_count == 2
    assert ledger.total_accepted_draws == 2 * (64 + 2_048)
    assert ledger.total_random_word_calls == ledger.total_accepted_draws
    assert ledger.total_resident_commitments == ledger.total_accepted_draws
    assert ledger.crn_cost_discount_draws == 0


def test_incremental_adapter_retains_prior_cold_and_incremental_suffix_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = materializer.run_development_incremental_materializer_control_v1(
        materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_A
    )
    occurrence = authority.reconcile_incremental_materializer_run_v1(run)
    suffix = run.handoff.counters.accepted_draws
    prior_cold = sum(
        item.draw_count
        for item in run.handoff.prior_cold_raw_commitment_ranges
    )

    assert prior_cold == 2 * (64 + 2_048)
    assert suffix == 35_072
    assert occurrence.work.accepted_draws == prior_cold + suffix
    assert occurrence.work.cold_discovery_draws == 2 * 64
    assert occurrence.work.cold_validation_draws == 2 * 2_048
    assert occurrence.work.failed_parent_certificate_attempts == 1
    assert occurrence.work.failed_certificate_attempts == 1
    assert occurrence.work.incremental_parent_validation_draws == 2_048
    assert occurrence.work.incremental_child_discovery_draws == 4 * 64
    assert occurrence.work.incremental_child_validation_draws == 4 * 8_192
    assert occurrence.work.resident_commitment_count == 0
    assert (
        occurrence.work.compressed_commitment_count
        == occurrence.work.accepted_draws
    )
    assert occurrence.access_order.authorization_frozen_before_execution
    assert occurrence.access_order.native_zero_values == tuple(
        0 for _ in occurrence.access_order.native_zero_paths
    )
    assert occurrence.terminal_class is (
        authority.ReconciliationTerminalClassV1
        .ATTEMPT_CLOSURE_NONCERTIFICATE
    )
    ledger = _campaign(occurrence)
    attestation = (
        independent.verify_campaign_reconciliation_independently_v1(
            ledger
        )
    )
    assert (
        attestation.accepted_draw_commitment_count
        == prior_cold + suffix
    )
    assert attestation.logical_occurrence_denominator == 1

    def forbidden_production_helper(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("independent replay called a production helper")

    for name in (
        "raw_commitment_id_v1",
        "upstream_stream_id_v1",
        "upstream_raw_commitment_id_v1",
        "upstream_raw_commitment_range_proof_v1",
    ):
        monkeypatch.setattr(
            materializer,
            name,
            forbidden_production_helper,
        )
    replay = independent.verify_campaign_reconciliation_independently_v1(
        ledger
    )
    assert replay.attestation_id == attestation.attestation_id


def test_matched_direct_adapter_retains_failed_checkpoint_and_terminal() -> None:
    run = direct.run_development_matched_direct_ground_baseline_v1()
    occurrence = authority.reconcile_matched_direct_run_v1(run)
    adaptive = tuple(
        _row_occurrence(arm)
        for arm in (
            "SOURCE_CONSENSUS_PRIOR",
            "NO_PRIOR",
            "WRONG_CONSENSUS_PRIOR",
            "OOD_ABSTENTION",
        )
    )
    ordered = (*adaptive, occurrence)
    binding = authority.DevelopmentSharedExperimentalContextBindingV1(
        "V072_DEVELOPMENT_P4_FIVE_ARM_MECHANICS_V1",
        tuple((item.arm, item.context_id) for item in ordered),
    )
    ledger = authority.reconcile_campaign_v1(
        occurrences=ordered,
        order_profile=(
            authority.CampaignOrderProfileV1
            .CONTEXT_MAJOR_FROZEN_ARM_ORDER
        ),
        development_context_binding=binding,
    )
    assert tuple(item.arm for item in ledger.occurrences) == (
        "SOURCE_CONSENSUS_PRIOR",
        "NO_PRIOR",
        "WRONG_CONSENSUS_PRIOR",
        "OOD_ABSTENTION",
        "MATCHED_DIRECT_GROUND",
    )

    assert occurrence.work.failed_direct_checkpoint_attempts >= 1
    assert (
        occurrence.work.failed_certificate_attempts
        == occurrence.work.failed_direct_checkpoint_attempts
    )
    assert occurrence.work.direct_checkpoint_attempts == len(
        run.checkpoint_records
    )
    assert occurrence.work.direct_model_builds == len(run.checkpoint_records)
    assert occurrence.work.direct_solver_calls == len(run.checkpoint_records)
    assert occurrence.work.direct_proof_verifications == len(
        run.checkpoint_records
    )
    assert ledger.logical_occurrence_denominator == 5
    assert ledger.total_terminal_artifacts == 5
    assert ledger.plan_certificate_count == int(run.certified)
    assert ledger.noncertificate_count == 4 + int(not run.certified)
    assert not binding.scientific_matched_pair
    assert not binding.matched_endpoint_authority
    attestation = (
        independent.verify_campaign_reconciliation_independently_v1(
            ledger
        )
    )
    assert attestation.logical_occurrence_denominator == 5


def test_authority_rejects_undercount_discount_terminal_and_duplicate_attacks() -> None:
    occurrence = _row_occurrence("NO_PRIOR")

    with pytest.raises(
        authority.V072CampaignReconciliationInvariantViolation
    ):
        replace(
            occurrence,
            work=replace(
                occurrence.work,
                cold_discovery_draws=63,
                row_core_validation_extension_draws=1,
            ),
        )
    with pytest.raises(
        authority.V072CampaignReconciliationInvariantViolation
    ):
        replace(occurrence.work, crn_cost_discount_draws=1)
    with pytest.raises(
        authority.V072CampaignReconciliationInvariantViolation
    ):
        replace(
            occurrence,
            terminal_class=(
                authority.ReconciliationTerminalClassV1.PLAN_CERTIFICATE
            ),
        )
    with pytest.raises(
        authority.V072CampaignReconciliationInvariantViolation
    ):
        replace(
            occurrence,
            draw_ranges=(
                occurrence.draw_ranges[0],
                occurrence.draw_ranges[0],
            ),
        )
    with pytest.raises(
        authority.V072CampaignReconciliationInvariantViolation
    ):
        authority.CampaignReconciliationLedgerV1(
            (occurrence, occurrence)
        )


def test_adapter_surfaces_accept_no_counts_discounts_or_terminal_outcomes() -> None:
    forbidden = {
        "count",
        "counts",
        "discount",
        "terminal",
        "terminal_class",
        "terminal_code",
        "denominator",
    }
    for function in (
        authority.reconcile_row_core_observation_series_v1,
        authority.reconcile_incremental_materializer_run_v1,
        authority.reconcile_matched_direct_run_v1,
        authority.reconcile_campaign_v1,
    ):
        assert forbidden.isdisjoint(inspect.signature(function).parameters)


def test_registered_reconciliation_remains_locked() -> None:
    with pytest.raises(
        authority.RegisteredCampaignReconciliationLockedV1
    ):
        authority.reconcile_registered_v072_campaign_v1()


def test_independent_verifier_rejects_mutated_ledger_totals() -> None:
    occurrence = _row_occurrence("NO_PRIOR")
    ledger = _campaign(occurrence)
    object.__setattr__(
        ledger,
        "total_accepted_draws",
        ledger.total_accepted_draws - 1,
    )
    with pytest.raises(
        independent.IndependentCampaignReconciliationVerificationFailure
    ):
        independent.verify_campaign_reconciliation_independently_v1(ledger)
