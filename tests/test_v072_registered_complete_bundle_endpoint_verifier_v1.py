from __future__ import annotations

from dataclasses import replace
import hashlib
from types import SimpleNamespace

import pytest

from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive
from acfqp import v072_registered_cold_h2_orchestrator_v1 as cold
from acfqp import v072_registered_matched_direct_runtime_v1 as direct
from acfqp import (
    v072_registered_complete_bundle_endpoint_verifier_v1 as endpoint,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _unsafe_exact(cls, **values):
    result = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    return result


def _facts(
    *,
    source_draws: int = 100,
    no_prior_draws: int = 200,
    direct_draws: int = 100,
) -> tuple[endpoint._ReplayedOccurrenceEndpointFactV1, ...]:
    terminal_by_arm = {
        "SOURCE_CONSENSUS_PRIOR": (
            "PLAN_CERTIFICATE",
            "CONDITIONAL_PLAN_CERTIFICATE",
            True,
            source_draws,
        ),
        "NO_PRIOR": (
            "PLAN_CERTIFICATE",
            "CONDITIONAL_PLAN_CERTIFICATE",
            True,
            no_prior_draws,
        ),
        "WRONG_CONSENSUS_PRIOR": (
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "NO_POSITIVE_GAIN_NONCERTIFICATE",
            False,
            150,
        ),
        "OOD_ABSTENTION": (
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "NO_POSITIVE_GAIN_NONCERTIFICATE",
            False,
            150,
        ),
        "MATCHED_DIRECT_GROUND": (
            "PLAN_CERTIFICATE",
            "CONDITIONAL_PLAN_CERTIFICATE",
            True,
            direct_draws,
        ),
    }
    output = []
    for context_ordinal, context in enumerate(
        prereg.registered_heldout_public_contexts_v2()
    ):
        for arm_ordinal, arm in enumerate(prereg.ARM_ORDER):
            ordinal = context_ordinal * len(prereg.ARM_ORDER) + arm_ordinal
            terminal_class, terminal_code, exact_pass, draws = terminal_by_arm[
                arm
            ]
            output.append(
                endpoint._ReplayedOccurrenceEndpointFactV1(
                    _id(f"occurrence:{ordinal}"),
                    _id(f"record:{ordinal}"),
                    context.context_id,
                    context.context_key,
                    context_ordinal,
                    arm,
                    arm_ordinal,
                    ordinal,
                    terminal_class,
                    terminal_code,
                    draws,
                    exact_pass,
                )
            )
    return tuple(output)


def test_endpoint_summary_derives_registered_counts_and_both_comparisons() -> None:
    summary = endpoint._derive_registered_endpoint_summary_v1(_facts())
    assert dict(summary.arm_online_draws) == {
        "SOURCE_CONSENSUS_PRIOR": 300,
        "NO_PRIOR": 600,
        "WRONG_CONSENSUS_PRIOR": 450,
        "OOD_ABSTENTION": 450,
        "MATCHED_DIRECT_GROUND": 300,
    }
    assert summary.target_online_draws == 2_100
    assert dict(summary.arm_plan_certificate_counts) == {
        "SOURCE_CONSENSUS_PRIOR": 3,
        "NO_PRIOR": 3,
        "WRONG_CONSENSUS_PRIOR": 0,
        "OOD_ABSTENTION": 0,
        "MATCHED_DIRECT_GROUND": 3,
    }
    assert dict(summary.arm_noncertificate_counts) == {
        "SOURCE_CONSENSUS_PRIOR": 0,
        "NO_PRIOR": 0,
        "WRONG_CONSENSUS_PRIOR": 3,
        "OOD_ABSTENTION": 3,
        "MATCHED_DIRECT_GROUND": 0,
    }
    assert dict(summary.terminal_code_counts)[
        "CONDITIONAL_PLAN_CERTIFICATE"
    ] == 9
    assert dict(summary.terminal_code_counts)[
        "NO_POSITIVE_GAIN_NONCERTIFICATE"
    ] == 6
    assert summary.source_exact_valid_context_count == 3
    assert summary.wrong_control_certificate_count == 0
    assert summary.ood_control_certificate_count == 0
    assert summary.source_coverage_noninferior_to_no_prior is True
    assert summary.source_coverage_noninferior_to_matched_direct is True
    assert summary.primary_operator_endpoint_pass is True
    assert summary.matched_sample_tax_endpoint_pass is True


def test_endpoint_comparisons_are_not_inferred_from_coverage() -> None:
    equal_primary = endpoint._derive_registered_endpoint_summary_v1(
        _facts(source_draws=200, no_prior_draws=200)
    )
    assert equal_primary.source_exact_valid_context_count == 3
    assert equal_primary.primary_operator_endpoint_pass is False
    assert equal_primary.matched_sample_tax_endpoint_pass is False

    above_direct = endpoint._derive_registered_endpoint_summary_v1(
        _facts(source_draws=101, no_prior_draws=200, direct_draws=100)
    )
    assert above_direct.primary_operator_endpoint_pass is True
    assert above_direct.matched_sample_tax_endpoint_pass is False


@pytest.mark.parametrize(
    "attack",
    (
        lambda facts: facts[:-1],
        lambda facts: (facts[1], facts[0], *facts[2:]),
        lambda facts: (*facts[:-1], facts[0]),
    ),
)
def test_endpoint_rejects_missing_reordered_or_reused_occurrences(attack) -> None:
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure
    ):
        endpoint._derive_registered_endpoint_summary_v1(
            tuple(attack(_facts()))
        )


def test_endpoint_rejects_stale_context_and_route_native_terminal_mismatch() -> None:
    facts = _facts()
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure
    ):
        endpoint._derive_registered_endpoint_summary_v1(
            (
                replace(
                    facts[0],
                    context_id=_id("stale-context"),
                ),
                *facts[1:],
            )
        )
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure
    ):
        replace(
            facts[0],
            terminal_class="PLAN_CERTIFICATE",
            terminal_code="NO_POSITIVE_GAIN_NONCERTIFICATE",
        )
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure
    ):
        replace(
            facts[4],
            terminal_class="ATTEMPT_CLOSURE_NONCERTIFICATE",
            terminal_code="INCREMENTAL_CAP_EXHAUSTED_NONCERTIFICATE",
            exact_evaluation_pass=False,
        )


def test_endpoint_does_not_accept_caller_claims_or_unminted_bundle() -> None:
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure,
        match="internally minted",
    ):
        endpoint.verify_registered_v072_complete_bundle_v1(
            bundle={
                "endpoint": True,
                "status": endpoint.REGISTERED_ENDPOINT_PASS,
                "count": 15,
            }
        )
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure
    ):
        endpoint.RegisteredCampaignCompleteBundleV1(
            object(),
            None,
            None,
            None,
            (),
            (),
            (),
            None,
            None,
        )


def test_source_collision_with_direct_inventory_fails_disjoint_endpoint() -> None:
    source = (_id("source:0"), _id("source:1"))
    adaptive = (_id("adaptive:0"), _id("adaptive:1"))
    direct = (_id("direct:0"), _id("direct:1"))
    assert endpoint._source_target_evidence_disjoint_v1(
        source_raw_ids=source,
        adaptive_target_ids=adaptive,
        direct_target_ids=direct,
    )
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure,
        match="source evidence identity",
    ):
        endpoint._source_target_evidence_disjoint_v1(
            source_raw_ids=source,
            adaptive_target_ids=adaptive,
            direct_target_ids=(direct[0], source[1]),
        )
    with pytest.raises(
        endpoint.V072RegisteredCompleteBundleVerificationFailure,
        match="reused",
    ):
        endpoint._source_target_evidence_disjoint_v1(
            source_raw_ids=source,
            adaptive_target_ids=adaptive,
            direct_target_ids=(direct[0], adaptive[0]),
        )


def test_direct_final_inventory_observation_ids_enter_target_identity_set() -> None:
    adaptive_observation_id = _id("adaptive-observation")
    adaptive_epoch = _unsafe_exact(
        cold.RegisteredColdH2ModelEpochV1,
        acquisitions=(
            SimpleNamespace(
                transcript=SimpleNamespace(
                    entries=(
                        SimpleNamespace(
                            observation=SimpleNamespace(
                                observation_id=adaptive_observation_id
                            )
                        ),
                    )
                )
            ),
        ),
    )
    adaptive_result = _unsafe_exact(
        adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1,
        execution=SimpleNamespace(epochs=(adaptive_epoch,)),
    )
    direct_observation_id = _id("direct-validation-observation")
    discovery_id = _id("direct-discovery-transcript")
    physical_id = _id("direct-physical-evidence")
    direct_checkpoint = SimpleNamespace(
        row_prefixes=(
            SimpleNamespace(
                acquisition_validation_observation_ids=(
                    direct_observation_id,
                ),
                discovery_transcript_id=discovery_id,
            ),
        ),
        row_evidence=(
            SimpleNamespace(physical_evidence_id=physical_id),
        ),
    )
    direct_result = _unsafe_exact(
        direct.RegisteredMatchedDirectOccurrenceResultV1,
        checkpoint_records=(
            SimpleNamespace(inventory_checkpoint=direct_checkpoint),
        ),
        physical_row_count=1,
        stopped_checkpoint=1,
    )
    adaptive_ids, direct_ids = endpoint._target_evidence_identity_sets(
        (adaptive_result, direct_result)
    )
    assert adaptive_ids == (adaptive_observation_id,)
    assert direct_ids == (
        direct_observation_id,
        discovery_id,
        physical_id,
    )


def test_readiness_opens_code_path_but_not_evidence_or_target_tape() -> None:
    readiness = (
        endpoint.inspect_registered_complete_bundle_verifier_readiness_v1()
    )
    document = readiness.to_document()
    assert readiness.bundle_minting_enabled is True
    assert readiness.registered_endpoint_verification_allowed is True
    assert readiness.registered_bundle_available is False
    assert readiness.registered_observations_generated == 0
    assert document["caller_endpoint_argument_allowed"] is False
    assert document["caller_status_argument_allowed"] is False
    assert document["caller_count_argument_allowed"] is False
    assert document["complete_independent_replay_required"] is True
    assert len(readiness.readiness_id) == 64
