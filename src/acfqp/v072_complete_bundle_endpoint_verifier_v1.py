"""Standalone independent replay of the complete V0-072 development bundle.

This module deliberately accepts exactly one typed five-arm bundle.  It never
accepts a caller-supplied endpoint, terminal status, draw count, or
attestation.  Every nested semantic attestation and the campaign identities
are reconstructed from the bundle before a development-only verification
attestation is emitted.

Registered verification remains locked.  A valid development bundle is not a
matched scientific endpoint and is not sample-efficiency evidence.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from fractions import Fraction
import hashlib
from itertools import combinations
import multiprocessing
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import v072_five_arm_confirmatory_campaign_v1 as campaign
from acfqp import (
    v072_five_arm_source_prior_independent_verifier_v1
    as source_independent,
)
from acfqp import (
    v072_development_complete_adaptive_run_independent_verifier_v1
    as adaptive_independent,
)
from acfqp import (
    v072_matched_direct_ground_baseline_independent_verifier_v1
    as direct_independent,
)
from acfqp import (
    v072_campaign_reconciliation_independent_verifier_v1
    as reconciliation_independent,
)
from acfqp import target_preauthorization_selector_v2 as selector


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_complete_bundle_endpoint_verifier_v1"
REGISTERED_EXECUTION_STATUS = (
    "NONAUTHORIZING_DRAFT_TARGET_LOCKED_GATE_NOT_RUN"
)

EXPECTED_CAMPAIGN_SCHEMA_VERSION = "1.0.0"
EXPECTED_CAMPAIGN_CONTRACT_VERSION = "1.36.0"
EXPECTED_CAMPAIGN_PROFILE = "v072_five_arm_confirmatory_campaign_v1"
EXPECTED_ARM_ORDER = (
    "SOURCE_CONSENSUS_PRIOR",
    "NO_PRIOR",
    "WRONG_CONSENSUS_PRIOR",
    "OOD_ABSTENTION",
    "MATCHED_DIRECT_GROUND",
)
ADAPTIVE_ARM_ORDER = EXPECTED_ARM_ORDER[:-1]

OCCURRENCE_DOMAIN = "acfqp:v072-five-arm-dev-occurrence:v1"
CAMPAIGN_DOMAIN = "acfqp:v072-five-arm-dev-campaign:v1"
VERIFICATION_DOMAIN = (
    "acfqp:v072-complete-development-bundle-independent-attestation:v1"
)
SOURCE_ATTESTATION_DOMAIN = (
    "acfqp:v072-five-arm-dev-source-independent-attestation:v1"
)


class V072CompleteBundleEndpointVerificationFailure(ValueError):
    """A complete typed campaign bundle failed standalone replay."""


class DevelopmentCompleteBundleAuthorityPending(RuntimeError):
    """Compatibility name retained from the former fail-closed skeleton."""


class RegisteredCompleteBundleEndpointVerifierLockedV1(RuntimeError):
    """The final manifest/anchor does not authorize registered replay."""


def _fail(message: str) -> None:
    raise V072CompleteBundleEndpointVerificationFailure(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise V072CompleteBundleEndpointVerificationFailure(
            f"complete-bundle content replay failed: {error}"
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072CompleteBundleEndpointVerificationFailure(
            f"{field_name} is not one canonical content ID"
        ) from error


def _protocol_payload(
    bundle: campaign.DevelopmentFiveArmCampaignRunV1,
) -> dict[str, Any]:
    protocol = bundle.protocol
    return {
        "schema": "acfqp.v072_five_arm_dev_protocol.v1",
        "schema_version": EXPECTED_CAMPAIGN_SCHEMA_VERSION,
        "proposed_contract_version": EXPECTED_CAMPAIGN_CONTRACT_VERSION,
        "profile_key": EXPECTED_CAMPAIGN_PROFILE,
        "source_authority_id": protocol.source_authority_id,
        "source_attestation_id": protocol.source_attestation_id,
        "context_key": protocol.context_key,
        "adaptive_law_key": protocol.adaptive_law_key.value,
        "direct_law": protocol.direct_law.value,
        "arm_order": list(protocol.arm_order),
        "maximum_adaptive_rounds": protocol.maximum_adaptive_rounds,
        "occurrence_replacement_allowed": False,
        "campaign_early_stop_allowed": False,
        "caller_terminal_input_allowed": False,
        "registered_target_execution": False,
        "matched_scientific_endpoint_authority": False,
        "development_backends_are_not_a_scientific_matched_pair": True,
        "sample_efficiency_gate_status": "NOT_RUN",
    }


def _source_attestation_id(attestation: Any) -> str:
    return _hash(
        SOURCE_ATTESTATION_DOMAIN,
        {
            "schema": (
                "acfqp.v072_five_arm_dev_source_"
                "independent_attestation.v1"
            ),
            "schema_version": EXPECTED_CAMPAIGN_SCHEMA_VERSION,
            "authority_id": attestation.authority_id,
            "source_archive_id": attestation.source_archive_id,
            "source_prior_binding_id":
                attestation.source_prior_binding_id,
            "source_context_count": attestation.source_context_count,
            "source_trial_count": attestation.source_trial_count,
            "source_raw_accepted_draws":
                attestation.source_raw_accepted_draws,
            "applied_consensus_count":
                attestation.applied_consensus_count,
            "raw_tapes_replayed": True,
            "aggregate_midrank_consensus_replayed": True,
            "caller_quantities_trusted": False,
            "proposal_only": True,
            "may_certify": False,
            "registered_target_evidence": False,
            "verified": True,
        },
    )


def _occurrence_id(
    *,
    protocol_id: str,
    mechanics_context_key: str,
    arm: str,
) -> str:
    if arm not in EXPECTED_ARM_ORDER:
        _fail("complete bundle contains an unknown arm")
    return _hash(
        OCCURRENCE_DOMAIN,
        {
            "schema": "acfqp.v072_five_arm_dev_logical_occurrence.v1",
            "schema_version": EXPECTED_CAMPAIGN_SCHEMA_VERSION,
            "protocol_id": protocol_id,
            "mechanics_context_key": mechanics_context_key,
            "arm": arm,
            "arm_ordinal": EXPECTED_ARM_ORDER.index(arm),
            "occurrence_replacement_allowed": False,
            "registered_target_evidence": False,
        },
    )


def _schedule_signature(run: Any) -> tuple[tuple[tuple[Any, ...], ...], ...]:
    output = []
    for selection in run.round_selections:
        scores = {item.candidate_id: item for item in selection.scores}
        output.append(
            tuple(
                (
                    scores[item.candidate_id].feature_key,
                    item.score,
                    item.gain,
                    item.exact_draw_upper,
                    item.gain_eligible,
                    item.cap_eligible,
                )
                for item in selection.schedule.entries
            )
        )
    return tuple(output)


def _selected_features(run: Any) -> tuple[str, ...]:
    return tuple(
        next(
            item.feature_key
            for item in selection.scores
            if item.candidate_id
            == selection.authorization.selected_candidate_id
        )
        for selection in run.round_selections
    )


def _incremental_stream_map(
    run: Any,
) -> dict[tuple[int, str, str, int], tuple[str, str, tuple[int, ...]]]:
    streams = tuple(
        stream
        for handoff in run.handoffs
        for stream in (
            handoff.parent_validation_stream,
            *(
                value
                for child in handoff.child_rows
                for value in (
                    child.discovery_stream,
                    child.validation_stream,
                )
            ),
        )
    )
    return {
        (
            stream.round_index,
            stream.physical_row_id,
            stream.lane.value,
            stream.draw_count,
        ): (
            stream.seed_id,
            stream.raw_word_digest,
            stream.outcome_bucket_counts,
        )
        for stream in streams
    }


def _evidence_inventory(run: Any) -> set[str]:
    return {
        run.run_id,
        *(item.handoff_id for item in run.handoffs),
        *(item.result_id for item in run.postbuild_results),
        *(
            proof.range_proof_id
            for handoff in run.handoffs
            for proof in handoff.raw_commitment_ranges
        ),
        *(
            proof.range_proof_id
            for proof in run.handoffs[0].prior_cold_raw_commitment_ranges
        ),
        *(
            transcript.upstream_row_evidence_id
            for transcript in (
                run.handoffs[0].request.parent_evidence.upstream_root_rows
            )
        ),
        *(
            stream_id
            for transcript in (
                run.handoffs[0].request.parent_evidence.upstream_root_rows
            )
            for stream_id in (
                transcript.discovery_stream_id,
                transcript.validation_stream_id,
            )
        ),
    }


def _campaign_payload(
    *,
    bundle: campaign.DevelopmentFiveArmCampaignRunV1,
    source_attestation: Any,
    source_attestation_id: str,
    adaptive_attestations: tuple[Any, ...],
    direct_attestation: Any,
    reconciliation_attestation: Any,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_five_arm_development_campaign_run.v1",
        "schema_version": EXPECTED_CAMPAIGN_SCHEMA_VERSION,
        "proposed_contract_version": EXPECTED_CAMPAIGN_CONTRACT_VERSION,
        "profile_key": EXPECTED_CAMPAIGN_PROFILE,
        "source_authority_id": bundle.source_authority.authority_id,
        "source_attestation_id": source_attestation_id,
        "source_offline_accepted_draws":
            source_attestation.source_raw_accepted_draws,
        "protocol_id": bundle.protocol.protocol_id,
        "context_binding_id": bundle.context_binding.binding_id,
        "arm_order": list(EXPECTED_ARM_ORDER),
        "adaptive_run_ids": [
            item.run_id for item in bundle.adaptive_runs
        ],
        "adaptive_attestation_ids": [
            item.attestation_id for item in adaptive_attestations
        ],
        "direct_run_id": bundle.direct_run.run_id,
        "direct_attestation_id": direct_attestation.verification_id,
        "reconciled_occurrence_ids": [
            item.occurrence_record_id
            for item in bundle.reconciled_occurrences
        ],
        "reconciliation_ledger_id":
            bundle.reconciliation_ledger.ledger_id,
        "reconciliation_attestation_id":
            reconciliation_attestation.attestation_id,
        "online_accepted_draws":
            bundle.reconciliation_ledger.total_accepted_draws,
        "logical_occurrence_denominator": 5,
        "all_terminal_artifacts_retained": True,
        "occurrence_replacement_allowed": False,
        "campaign_early_stop_allowed": False,
        "source_quantities_are_proposal_only": True,
        "source_quantities_in_certificate_inputs": 0,
        "crn_cost_discount_draws": 0,
        "caller_supplied_terminal": False,
        "caller_supplied_counts": False,
        "matched_scientific_endpoint_authority": False,
        "registered_target_evidence": False,
        "registered_execution_allowed": False,
        "sample_efficiency_gate_status": "NOT_RUN",
    }


def _verify_adaptive_run_worker_v1(
    run: Any,
) -> adaptive_independent.IndependentCompleteAdaptiveRunAttestationV1:
    """Spawn-safe wrapper around the standalone complete-run verifier."""

    return adaptive_independent.verify_development_complete_adaptive_run_v1(
        run
    )


def _verify_adaptive_runs_parallel_v1(
    runs: tuple[Any, ...],
) -> tuple[
    adaptive_independent.IndependentCompleteAdaptiveRunAttestationV1,
    ...,
]:
    if len(runs) != 4:
        _fail("independent adaptive replay requires four frozen arms")
    with ProcessPoolExecutor(
        max_workers=4,
        mp_context=multiprocessing.get_context("spawn"),
    ) as executor:
        return tuple(
            executor.map(
                _verify_adaptive_run_worker_v1,
                runs,
                chunksize=1,
            )
        )


@dataclass(frozen=True, slots=True)
class DevelopmentCompleteBundleIndependentAttestationV1:
    campaign_id: str
    source_authority_id: str
    source_attestation_id: str
    protocol_id: str
    context_binding_id: str
    adaptive_run_ids: tuple[str, ...]
    adaptive_attestation_ids: tuple[str, ...]
    direct_run_id: str
    direct_verification_id: str
    reconciliation_ledger_id: str
    reconciliation_attestation_id: str
    logical_occurrence_ids: tuple[str, ...]
    logical_occurrence_denominator: int
    source_offline_accepted_draws: int
    online_accepted_draws: int
    terminal_classes: tuple[str, ...]
    terminal_codes: tuple[str, ...]
    verification_result: str = (
        "VALID_DEVELOPMENT_COMPLETE_BUNDLE_NO_ENDPOINT_AUTHORITY"
    )
    registered_target_evidence: bool = False
    matched_scientific_endpoint_authority: bool = False
    sample_efficiency_gate_status: str = "NOT_RUN"

    def __post_init__(self) -> None:
        for value in (
            self.campaign_id,
            self.source_authority_id,
            self.source_attestation_id,
            self.protocol_id,
            self.context_binding_id,
            *self.adaptive_run_ids,
            *self.adaptive_attestation_ids,
            self.direct_run_id,
            self.direct_verification_id,
            self.reconciliation_ledger_id,
            self.reconciliation_attestation_id,
            *self.logical_occurrence_ids,
        ):
            _cid(value, "complete-bundle attestation identity")
        if (
            len(self.adaptive_run_ids) != 4
            or len(self.adaptive_attestation_ids) != 4
            or len(self.logical_occurrence_ids) != 5
            or len(set(self.logical_occurrence_ids)) != 5
            or self.logical_occurrence_denominator != 5
            or self.source_offline_accepted_draws <= 0
            or self.online_accepted_draws <= 0
            or len(self.terminal_classes) != 5
            or len(self.terminal_codes) != 5
            or set(self.terminal_classes) != {"PLAN_CERTIFICATE"}
            or self.registered_target_evidence is not False
            or self.matched_scientific_endpoint_authority is not False
            or self.sample_efficiency_gate_status != "NOT_RUN"
        ):
            _fail("complete-bundle independent attestation is malformed")

    @property
    def attestation_id(self) -> str:
        return _hash(
            VERIFICATION_DOMAIN,
            {
                "schema": (
                    "acfqp.v072_complete_development_bundle_"
                    "independent_attestation.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                "profile_key": PROFILE_KEY,
                "campaign_id": self.campaign_id,
                "source_authority_id": self.source_authority_id,
                "source_attestation_id": self.source_attestation_id,
                "protocol_id": self.protocol_id,
                "context_binding_id": self.context_binding_id,
                "adaptive_run_ids": list(self.adaptive_run_ids),
                "adaptive_attestation_ids":
                    list(self.adaptive_attestation_ids),
                "direct_run_id": self.direct_run_id,
                "direct_verification_id": self.direct_verification_id,
                "reconciliation_ledger_id":
                    self.reconciliation_ledger_id,
                "reconciliation_attestation_id":
                    self.reconciliation_attestation_id,
                "logical_occurrence_ids":
                    list(self.logical_occurrence_ids),
                "logical_occurrence_denominator":
                    self.logical_occurrence_denominator,
                "source_offline_accepted_draws":
                    self.source_offline_accepted_draws,
                "online_accepted_draws": self.online_accepted_draws,
                "terminal_classes": list(self.terminal_classes),
                "terminal_codes": list(self.terminal_codes),
                "verification_result": self.verification_result,
                "registered_target_evidence": False,
                "matched_scientific_endpoint_authority": False,
                "sample_efficiency_gate_status": "NOT_RUN",
                "caller_supplied_endpoint": False,
                "caller_supplied_terminal": False,
                "caller_supplied_counts": False,
                "production_campaign_runner_called": False,
                "production_campaign_content_id_called": False,
            },
        )


def _verify_development_complete_bundle_impl(
    bundle: campaign.DevelopmentFiveArmCampaignRunV1,
) -> DevelopmentCompleteBundleIndependentAttestationV1:
    if type(bundle) is not campaign.DevelopmentFiveArmCampaignRunV1:
        _fail("complete verifier requires the exact five-arm campaign type")
    if (
        EXPECTED_ARM_ORDER != prereg.ARM_ORDER
        or campaign.ARM_ORDER != EXPECTED_ARM_ORDER
        or campaign.ADAPTIVE_ARM_ORDER != ADAPTIVE_ARM_ORDER
    ):
        _fail("campaign arm registry differs from the frozen verifier")

    source_attestation = (
        source_independent
        .verify_development_source_prior_authority_independently_v1(
            bundle.source_authority
        )
    )
    source_attestation_id = _source_attestation_id(source_attestation)
    if (
        bundle.source_attestation != source_attestation
        or bundle.protocol.source_authority_id
        != source_attestation.authority_id
        or bundle.protocol.source_attestation_id
        != source_attestation_id
        or bundle.protocol.arm_order != EXPECTED_ARM_ORDER
        or bundle.protocol.maximum_adaptive_rounds != 2
        or bundle.protocol.occurrence_replacement_allowed
        or bundle.protocol.campaign_early_stop_allowed
        or bundle.protocol.caller_terminal_input_allowed
        or bundle.protocol.registered_target_execution
        or bundle.protocol.matched_scientific_endpoint_authority
    ):
        _fail("source/protocol identity or protocol restrictions differ")
    protocol_id = _hash(CAMPAIGN_DOMAIN, _protocol_payload(bundle))
    if protocol_id != bundle.protocol.protocol_id:
        _fail("protocol content identity differs")

    if (
        type(bundle.adaptive_runs) is not tuple
        or len(bundle.adaptive_runs) != 4
        or tuple(item.arm.value for item in bundle.adaptive_runs)
        != ADAPTIVE_ARM_ORDER
        or type(bundle.adaptive_attestations) is not tuple
        or len(bundle.adaptive_attestations) != 4
    ):
        _fail("adaptive arms are incomplete, reordered, or replaced")
    replayed_adaptive = _verify_adaptive_runs_parallel_v1(
        bundle.adaptive_runs
    )
    if replayed_adaptive != bundle.adaptive_attestations:
        _fail("stored adaptive independent attestations differ")

    source_binding_id = source_attestation.source_prior_binding_id
    ood_id = bundle.source_authority.ood_abstention.abstention_id
    for run in bundle.adaptive_runs:
        arm = run.arm
        expected_source = (
            source_binding_id
            if arm in (
                selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
                selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
            )
            else None
        )
        expected_ood = (
            ood_id
            if arm is selector.TargetSelectionArmV2.OOD_ABSTENTION
            else None
        )
        if (
            run.logical_occurrence_id
            != _occurrence_id(
                protocol_id=protocol_id,
                mechanics_context_key=bundle.protocol.context_key,
                arm=arm.value,
            )
            or run.handoffs[0].request.authorization
            .source_prior_binding_id
            != expected_source
            or run.handoffs[0].request.authorization.ood_abstention_id
            != expected_ood
            or any(
                selection.authorization.source_prior_binding_id
                != expected_source
                or selection.authorization.ood_abstention_id
                != expected_ood
                for selection in run.round_selections
            )
        ):
            _fail("adaptive occurrence or prior input was transplanted")

    by_arm = {item.arm: item for item in bundle.adaptive_runs}
    for arm in (
        selector.TargetSelectionArmV2.SOURCE_CONSENSUS_PRIOR,
        selector.TargetSelectionArmV2.WRONG_CONSENSUS_PRIOR,
    ):
        if not by_arm[arm].round_selections or not any(
            score.multiplier != Fraction(1)
            for selection in by_arm[arm].round_selections
            for score in selection.scores
        ):
            _fail("source/wrong arm did not apply a real proposal multiplier")
    neutral = by_arm[selector.TargetSelectionArmV2.NO_PRIOR]
    ood = by_arm[selector.TargetSelectionArmV2.OOD_ABSTENTION]
    if (
        _schedule_signature(neutral) != _schedule_signature(ood)
        or _selected_features(neutral) != _selected_features(ood)
    ):
        _fail("OOD abstention is not the arm-free no-prior control")

    crn_maps = tuple(
        _incremental_stream_map(item) for item in bundle.adaptive_runs
    )
    common_crn_keys = set.intersection(
        *(set(item) for item in crn_maps)
    )
    if not common_crn_keys or any(
        len({mapping[key] for mapping in crn_maps}) != 1
        for key in common_crn_keys
    ):
        _fail("adaptive arms do not share arm-free CRN words")
    inventories = tuple(
        _evidence_inventory(item) for item in bundle.adaptive_runs
    )
    if any(
        inventories[left] & inventories[right]
        for left, right in combinations(range(4), 2)
    ):
        _fail("cold/suffix/model evidence overlaps across adaptive arms")

    direct_attestation = (
        direct_independent
        .verify_matched_direct_ground_run_independently_v1(
            bundle.direct_run
        )
    )
    if (
        bundle.direct_attestation != direct_attestation
        or bundle.direct_run.logical_occurrence_id
        != _occurrence_id(
            protocol_id=protocol_id,
            mechanics_context_key=bundle.protocol.context_key,
            arm="MATCHED_DIRECT_GROUND",
        )
        or bundle.direct_run.source_prior_reads != 0
        or bundle.direct_run.quotient_planner_calls != 0
        or bundle.direct_run.local_promotion_calls != 0
        or bundle.direct_run.crn_cost_discount_draws != 0
    ):
        _fail("matched-direct occurrence used adaptive/discounted work")

    expected_occurrence_ids = tuple(
        _occurrence_id(
            protocol_id=protocol_id,
            mechanics_context_key=bundle.protocol.context_key,
            arm=arm,
        )
        for arm in EXPECTED_ARM_ORDER
    )
    native_occurrence_ids = tuple(
        item.logical_occurrence_id for item in bundle.adaptive_runs
    ) + (bundle.direct_run.logical_occurrence_id,)
    if (
        native_occurrence_ids != expected_occurrence_ids
        or len(set(native_occurrence_ids)) != 5
        or tuple(item.arm for item in bundle.reconciled_occurrences)
        != EXPECTED_ARM_ORDER
        or tuple(
            item.logical_occurrence_id
            for item in bundle.reconciled_occurrences
        )
        != expected_occurrence_ids
        or bundle.reconciliation_ledger.occurrences
        != bundle.reconciled_occurrences
    ):
        _fail("logical occurrence denominator/order/binding differs")
    reconciliation_attestation = (
        reconciliation_independent
        .verify_campaign_reconciliation_independently_v1(
            bundle.reconciliation_ledger
        )
    )
    if (
        bundle.reconciliation_attestation
        != reconciliation_attestation
        or reconciliation_attestation.logical_occurrence_denominator != 5
        or reconciliation_attestation.noncertificate_count != 0
        or reconciliation_attestation.crn_cost_discount_draws != 0
        or bundle.reconciliation_ledger.total_terminal_artifacts != 5
        or bundle.reconciliation_ledger.registered_target_evidence_count
        != 0
    ):
        _fail("campaign reconciliation replay or denominator differs")

    campaign_payload = _campaign_payload(
        bundle=bundle,
        source_attestation=source_attestation,
        source_attestation_id=source_attestation_id,
        adaptive_attestations=replayed_adaptive,
        direct_attestation=direct_attestation,
        reconciliation_attestation=reconciliation_attestation,
    )
    campaign_id = _hash(CAMPAIGN_DOMAIN, campaign_payload)
    claimed_campaign_id = object.__getattribute__(bundle, "_campaign_id")
    if campaign_id != claimed_campaign_id:
        _fail("complete five-arm campaign content identity differs")

    terminal_classes = tuple(
        item.terminal_class for item in replayed_adaptive
    ) + (direct_attestation.terminal_class,)
    terminal_codes = tuple(
        item.terminal_code for item in replayed_adaptive
    ) + (direct_attestation.terminal_code,)
    return DevelopmentCompleteBundleIndependentAttestationV1(
        campaign_id,
        source_attestation.authority_id,
        source_attestation_id,
        protocol_id,
        bundle.context_binding.binding_id,
        tuple(item.complete_run_id for item in replayed_adaptive),
        tuple(item.attestation_id for item in replayed_adaptive),
        direct_attestation.run_id,
        direct_attestation.verification_id,
        reconciliation_attestation.ledger_id,
        reconciliation_attestation.attestation_id,
        expected_occurrence_ids,
        5,
        source_attestation.source_raw_accepted_draws,
        bundle.reconciliation_ledger.total_accepted_draws,
        terminal_classes,
        terminal_codes,
    )


def verify_development_complete_bundle_v1(
    *,
    bundle: Any,
) -> DevelopmentCompleteBundleIndependentAttestationV1:
    """Independently replay one exact five-arm development bundle."""

    try:
        return _verify_development_complete_bundle_impl(bundle)
    except V072CompleteBundleEndpointVerificationFailure:
        raise
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        RuntimeError,
        AssertionError,
    ) as error:
        raise V072CompleteBundleEndpointVerificationFailure(
            f"nested complete-bundle replay rejected the bundle: {error}"
        ) from error


def verify_registered_v072_complete_bundle_v1(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise RegisteredCompleteBundleEndpointVerifierLockedV1(
        "registered complete-bundle verification remains locked: "
        f"status={REGISTERED_EXECUTION_STATUS}, "
        f"draft_preregistration_id={prereg.DRAFT_PREREGISTRATION_ID}, "
        "confirmatory_execution_manifest_id=null, "
        "anchor_commit_id=null, target_execution_allowed=false"
    )


__all__ = [
    "DevelopmentCompleteBundleAuthorityPending",
    "DevelopmentCompleteBundleIndependentAttestationV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_EXECUTION_STATUS",
    "RegisteredCompleteBundleEndpointVerifierLockedV1",
    "SCHEMA_VERSION",
    "V072CompleteBundleEndpointVerificationFailure",
    "verify_development_complete_bundle_v1",
    "verify_registered_v072_complete_bundle_v1",
]
