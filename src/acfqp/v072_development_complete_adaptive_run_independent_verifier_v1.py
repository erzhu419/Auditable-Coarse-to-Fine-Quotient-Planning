"""Independent replay of the complete V0-072 development adaptive run."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import partial_support_robust_planner_v1 as robust
from . import v072_development_complete_adaptive_run_v1 as claimed_types
from . import v072_incremental_materializer_v1 as materializer
from . import (
    v072_incremental_materializer_independent_verifier_v1
    as materializer_independent,
)
from . import (
    v072_incremental_postbuild_independent_verifier_v1
    as postbuild_independent,
)
from . import v072_target_selector_component_v1 as selector_independent


SCHEMA_VERSION = "1.0.0"
VERIFICATION_PROFILE = (
    "v072_development_complete_adaptive_run_independent_verifier_v1"
)
RUN_DOMAIN = "acfqp:v072-development-complete-adaptive-run:v1"
ATTESTATION_DOMAIN = (
    "acfqp:v072-development-complete-adaptive-run-independent-attestation:v1"
)


class IndependentCompleteAdaptiveRunVerificationFailure(ValueError):
    """The claimed complete run differs from independent typed replay."""


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            f"independent complete-run content replay failed: {error}"
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            f"{field_name} is not one content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class IndependentCompleteAdaptiveRunAttestationV1:
    complete_run_id: str
    law_key: str
    arm: str
    logical_occurrence_id: str
    context_id: str
    materialization_round_count: int
    selection_event_count: int
    control_materializer_attestation_id: str
    handoff_materializer_attestation_ids: tuple[str, ...]
    selector_verification_ids: tuple[str, ...]
    postbuild_independent_attestation_ids: tuple[str, ...]
    terminal_class: str
    terminal_code: str
    prior_cold_draws: int
    incremental_suffix_draws: int
    total_accepted_draws: int

    def __post_init__(self) -> None:
        for value in (
            self.complete_run_id,
            self.logical_occurrence_id,
            self.context_id,
            self.control_materializer_attestation_id,
            *self.handoff_materializer_attestation_ids,
            *self.selector_verification_ids,
            *self.postbuild_independent_attestation_ids,
        ):
            _cid(value, "complete-run attestation identity")
        if (
            self.law_key not in ("HASH_BUCKET_LAW_A", "HASH_BUCKET_LAW_B")
            or not self.arm
            or self.materialization_round_count not in (1, 2)
            or self.selection_event_count
            != self.materialization_round_count - 1
            or len(self.handoff_materializer_attestation_ids)
            != self.materialization_round_count
            or len(self.selector_verification_ids)
            != self.selection_event_count
            or len(self.postbuild_independent_attestation_ids)
            != self.materialization_round_count
            or self.terminal_class != "PLAN_CERTIFICATE"
            or self.terminal_code not in (
                "PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD",
                "PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD",
            )
            or self.prior_cold_draws
            != claimed_types.PRIOR_COLD_DRAWS
            or self.incremental_suffix_draws
            not in (
                claimed_types.ROUND_ONE_SUFFIX_DRAWS,
                claimed_types.ROUND_ONE_SUFFIX_DRAWS
                + claimed_types.ROUND_TWO_SUFFIX_DRAWS,
            )
            or self.total_accepted_draws
            != self.prior_cold_draws + self.incremental_suffix_draws
        ):
            raise IndependentCompleteAdaptiveRunVerificationFailure(
                "complete-run attestation is malformed"
            )

    @property
    def attestation_id(self) -> str:
        return _hash(
            ATTESTATION_DOMAIN,
            {
                "schema": (
                    "acfqp.v072_development_complete_adaptive_run_"
                    "independent_attestation.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "verification_profile": VERIFICATION_PROFILE,
                "complete_run_id": self.complete_run_id,
                "law_key": self.law_key,
                "arm": self.arm,
                "logical_occurrence_id": self.logical_occurrence_id,
                "context_id": self.context_id,
                "materialization_round_count":
                    self.materialization_round_count,
                "selection_event_count": self.selection_event_count,
                "control_materializer_attestation_id":
                    self.control_materializer_attestation_id,
                "handoff_materializer_attestation_ids":
                    list(self.handoff_materializer_attestation_ids),
                "selector_verification_ids":
                    list(self.selector_verification_ids),
                "postbuild_independent_attestation_ids":
                    list(self.postbuild_independent_attestation_ids),
                "terminal_class": self.terminal_class,
                "terminal_code": self.terminal_code,
                "prior_cold_draws": self.prior_cold_draws,
                "incremental_suffix_draws":
                    self.incremental_suffix_draws,
                "total_accepted_draws": self.total_accepted_draws,
                "production_complete_runner_called": False,
                "production_complete_content_id_called": False,
            },
        )


def verify_development_complete_adaptive_run_v1(
    claimed: claimed_types.DevelopmentCompleteAdaptivePlanningRunV1,
) -> IndependentCompleteAdaptiveRunAttestationV1:
    """Replay both attestation roles, selector, post-build, counts, and ID."""

    if type(claimed) is not (
        claimed_types.DevelopmentCompleteAdaptivePlanningRunV1
    ):
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            "complete adaptive claim has a foreign type"
        )
    handoffs = claimed.handoffs
    results = claimed.postbuild_results
    replayed_control = (
        materializer_independent
        .verify_development_control_handoff_role_v1(
            handoffs[0]
        )
    )
    replayed_handoffs = []
    replayed_postbuilds = []
    for index, (handoff, result) in enumerate(
        zip(handoffs, results, strict=True),
    ):
        previous_handoff = None if index == 0 else handoffs[index - 1]
        previous_result = None if index == 0 else results[index - 1]
        replayed_handoffs.append(
            materializer_independent
            .verify_incremental_materializer_handoff_v1(
                handoff,
                previous_handoff=previous_handoff,
            )
        )
        replayed_postbuilds.append(
            postbuild_independent.verify_incremental_postbuild_result_v1(
                handoff=handoff,
                claimed=result,
                prior_handoff=previous_handoff,
                prior_postbuild=previous_result,
            )
        )
    replayed_handoff_tuple = tuple(replayed_handoffs)
    replayed_postbuild_tuple = tuple(replayed_postbuilds)
    if (
        claimed.control_materializer_attestation != replayed_control
        or claimed.handoff_materializer_attestations
        != replayed_handoff_tuple
        or claimed.postbuild_independent_attestations
        != replayed_postbuild_tuple
        or replayed_control.logical_occurrence_id
        != handoffs[0].request.parent_epoch.logical_occurrence_id
        or any(
            item.logical_occurrence_id
            != handoffs[0].request.parent_epoch.logical_occurrence_id
            for item in replayed_handoff_tuple
        )
        or replayed_control.attestation_id
        == replayed_handoff_tuple[0].attestation_id
        or any(
            postbuild.materializer_attestation_id
            != handoff.attestation_id
            for postbuild, handoff in zip(
                replayed_postbuild_tuple,
                replayed_handoff_tuple,
                strict=True,
            )
        )
    ):
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            "control/generic materializer attestation roles were transplanted"
        )

    replayed_selectors = []
    for selection in claimed.round_selections:
        first_result = results[0]
        audit = first_result.planner_result.solve_result.audit
        if audit is None:
            raise IndependentCompleteAdaptiveRunVerificationFailure(
                "selector predecessor lacks one failed post-build audit"
            )
        replayed_selectors.append(
            selector_independent.verify_target_selection_semantically_v1(
                model=(
                    first_result.model_pair.quotient_planner_projection
                    .planner_model
                ),
                audit=audit,
                threshold=first_result.model_pair.threshold_profile,
                registry=selection.registry,
                arm=claimed.arm,
                claimed=selection,
                previous_development_authorization=(
                    handoffs[0].request.authorization
                ),
                previous_materializer_attestation_id=(
                    replayed_control.attestation_id
                ),
                source_prior=selection.source_prior_binding,
                ood_abstention=selection.ood_abstention,
            )
        )
    replayed_selector_tuple = tuple(replayed_selectors)
    if claimed.selector_verifications != replayed_selector_tuple:
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            "recovery selector semantic verification differs"
        )

    round_count = len(handoffs)
    if (
        round_count == 1
        and (
            claimed.law_key
            is not materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_A
            or results[0].audit_status
            is not robust.RobustAuditStatus.CERTIFIED
        )
    ):
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            "one-round terminal is not independently certified Law A"
        )
    if (
        round_count == 2
        and (
            claimed.law_key
            is not materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_B
            or results[0].audit_status
            is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
            or results[1].audit_status
            is not robust.RobustAuditStatus.CERTIFIED
        )
    ):
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            "two-round terminal does not retain failed-then-certified Law B"
        )

    prior_cold_draws = sum(
        item.draw_count
        for item in handoffs[0].prior_cold_raw_commitment_ranges
    )
    prior_ranges = handoffs[0].prior_cold_raw_commitment_ranges
    suffix_ranges = tuple(
        item
        for handoff in handoffs
        for item in handoff.raw_commitment_ranges
    )
    prior_stream_ids = {
        item.stream_id for item in prior_ranges
    }
    suffix_stream_ids = {
        item.stream_id for item in suffix_ranges
    }
    if (
        len(prior_stream_ids) != len(prior_ranges)
        or len({item.range_proof_id for item in prior_ranges})
        != len(prior_ranges)
        or len(suffix_stream_ids) != len(suffix_ranges)
        or len({item.range_proof_id for item in suffix_ranges})
        != len(suffix_ranges)
        or prior_stream_ids & suffix_stream_ids
        or (
            len(handoffs) == 2
            and tuple(
                item.range_proof_id
                for item in handoffs[1].prior_cold_raw_commitment_ranges
            )
            != tuple(item.range_proof_id for item in prior_ranges)
        )
    ):
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            "cold/suffix commitment ranges are omitted, reused, or double charged"
        )
    certificate_model_ids = {
        item.model_pair.quotient_planner_projection.planner_model.model_id
        for item in results
    }
    proposal_resolution_model_ids = {
        item.resolution_model_id
        for selection in claimed.round_selections
        for item in selection.counterfactuals
        if item.resolution_model_id is not None
    }
    if certificate_model_ids & proposal_resolution_model_ids:
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            "proposal-only resolution model became certificate authority"
        )
    incremental_suffix_draws = sum(
        item.exact_draw_count for item in replayed_handoff_tuple
    )
    total_accepted_draws = prior_cold_draws + incremental_suffix_draws
    terminal_code = (
        "PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD"
        if round_count == 1
        else "PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD"
    )
    if (
        claimed.execution_lane.value
        != "DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY"
        or claimed.logical_occurrence_id
        != handoffs[0].request.parent_epoch.logical_occurrence_id
        or claimed.context_id
        != handoffs[0].request.parent_epoch.context_id
        or claimed.terminal_class.value != "PLAN_CERTIFICATE"
        or claimed.terminal_code.value != terminal_code
        or claimed.prior_cold_draws != prior_cold_draws
        or claimed.incremental_suffix_draws
        != incremental_suffix_draws
        or claimed.total_accepted_draws != total_accepted_draws
    ):
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            "derived complete-run terminal or accepted-draw total differs"
        )

    payload = {
        "schema": "acfqp.v072_development_complete_adaptive_run.v1",
        "schema_version": claimed_types.SCHEMA_VERSION,
        "proposed_contract_version":
            claimed_types.PROPOSED_CONTRACT_VERSION,
        "profile_key": claimed_types.PROFILE_KEY,
        "law_key": claimed.law_key.value,
        "arm": claimed.arm.value,
        "execution_lane": (
            "DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY"
        ),
        "logical_occurrence_id": claimed.logical_occurrence_id,
        "context_id": claimed.context_id,
        "selection_event_count": len(replayed_selector_tuple),
        "materialization_round_count": round_count,
        "round_selection_ids": [
            item.prepared_selection_id
            for item in replayed_selector_tuple
        ],
        "selector_verification_ids": [
            item.verification_id for item in replayed_selector_tuple
        ],
        "handoff_ids": [
            item.handoff_id for item in replayed_handoff_tuple
        ],
        "control_materializer_attestation_id":
            replayed_control.attestation_id,
        "handoff_materializer_attestation_ids": [
            item.attestation_id for item in replayed_handoff_tuple
        ],
        "materializer_attestation_roles_distinct": True,
        "postbuild_result_ids": [
            item.postbuild_result_id for item in replayed_postbuild_tuple
        ],
        "postbuild_independent_attestation_ids": [
            item.attestation_id for item in replayed_postbuild_tuple
        ],
        "terminal_class": "PLAN_CERTIFICATE",
        "terminal_code": terminal_code,
        "prior_cold_draws": prior_cold_draws,
        "incremental_suffix_draws": incremental_suffix_draws,
        "total_accepted_draws": total_accepted_draws,
        "prior_cold_work_double_charged": False,
        "failed_intermediate_work_retained": round_count == 2,
        "caller_supplied_status": False,
        "caller_supplied_counts": False,
        "caller_supplied_result": False,
        "proposal_resolution_model_used_for_certificate": False,
        "registered_target_evidence": False,
        "registered_execution_allowed": False,
    }
    replayed_run_id = _hash(RUN_DOMAIN, payload)
    claimed_run_id = object.__getattribute__(claimed, "_run_id")
    if replayed_run_id != claimed_run_id:
        raise IndependentCompleteAdaptiveRunVerificationFailure(
            "complete adaptive run content identity differs"
        )
    return IndependentCompleteAdaptiveRunAttestationV1(
        replayed_run_id,
        claimed.law_key.value,
        claimed.arm.value,
        claimed.logical_occurrence_id,
        claimed.context_id,
        round_count,
        len(replayed_selector_tuple),
        replayed_control.attestation_id,
        tuple(
            item.attestation_id for item in replayed_handoff_tuple
        ),
        tuple(item.verification_id for item in replayed_selector_tuple),
        tuple(
            item.attestation_id for item in replayed_postbuild_tuple
        ),
        "PLAN_CERTIFICATE",
        terminal_code,
        prior_cold_draws,
        incremental_suffix_draws,
        total_accepted_draws,
    )


__all__ = [
    "IndependentCompleteAdaptiveRunAttestationV1",
    "IndependentCompleteAdaptiveRunVerificationFailure",
    "SCHEMA_VERSION",
    "VERIFICATION_PROFILE",
    "verify_development_complete_adaptive_run_v1",
]
