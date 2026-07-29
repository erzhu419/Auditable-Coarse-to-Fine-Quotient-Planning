"""Complete development-only adaptive acquisition-to-certificate control.

This module composes the already typed V0-072 authorities.  It does not add
an alternative planner or trust caller-supplied counts/statuses: all terminal
and work fields are derived from independently replayed materializer and
post-build artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import partial_support_robust_planner_v1 as robust
from . import target_preauthorization_selector_v2 as selector
from . import v072_incremental_materializer_v1 as materializer
from . import (
    v072_incremental_materializer_independent_verifier_v1
    as materializer_independent,
)
from . import v072_incremental_postbuild_bridge_v1 as bridge
from . import (
    v072_incremental_postbuild_independent_verifier_v1
    as postbuild_independent,
)
from . import v072_target_selector_component_v1 as selector_component


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_development_complete_adaptive_run_v1"
REGISTERED_EXECUTION_ALLOWED = False

PRIOR_COLD_DRAWS = 4_224
ROUND_ONE_SUFFIX_DRAWS = 35_072
ROUND_TWO_SUFFIX_DRAWS = 18_560

DOMAIN_TAGS = {
    "run": "acfqp:v072-development-complete-adaptive-run:v1",
}


class DevelopmentCompleteAdaptiveRunInvariantViolation(ValueError):
    """A composed adaptive run is incomplete, stale, or mis-accounted."""


class RegisteredV072CompleteAdaptiveRunLocked(RuntimeError):
    """Registered execution remains unavailable."""


class DevelopmentAdaptiveExecutionLaneV1(str, Enum):
    DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY = (
        "DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY"
    )


class DevelopmentCompleteAdaptiveTerminalClassV1(str, Enum):
    PLAN_CERTIFICATE = "PLAN_CERTIFICATE"


class DevelopmentCompleteAdaptiveTerminalCodeV1(str, Enum):
    PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD = (
        "PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD"
    )
    PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD = (
        "PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD"
    )


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise DevelopmentCompleteAdaptiveRunInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise DevelopmentCompleteAdaptiveRunInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class DevelopmentCompleteAdaptivePlanningRunV1:
    """One complete Law-A or Law-B adaptive development occurrence.

    ``round_selections`` records only actual failed-proof recovery selector
    events.  The initial materialization is a frozen development control and
    therefore has no ``PreparedTargetSelectionV2`` event.  ``handoffs`` and
    ``postbuild_results`` record every physical round.
    """

    law_key: materializer.DevelopmentLawKeyV1
    arm: selector.TargetSelectionArmV2
    round_selections: tuple[selector.PreparedTargetSelectionV2, ...]
    selector_verifications: tuple[
        selector_component.V072TargetSelectorSemanticVerificationV1, ...
    ]
    handoffs: tuple[materializer.IncrementalModelRebuildHandoffV1, ...]
    control_materializer_attestation: (
        materializer_independent
        .IndependentIncrementalMaterializerAttestationV1
    )
    handoff_materializer_attestations: tuple[
        materializer_independent
        .IndependentIncrementalMaterializerAttestationV1,
        ...,
    ]
    postbuild_results: tuple[bridge.IncrementalPostbuildResultV1, ...]
    postbuild_independent_attestations: tuple[
        postbuild_independent.IndependentIncrementalPostbuildAttestationV1,
        ...,
    ]
    execution_lane: DevelopmentAdaptiveExecutionLaneV1 = field(
        init=False,
        default=(
            DevelopmentAdaptiveExecutionLaneV1
            .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
        ),
    )
    logical_occurrence_id: str = field(init=False)
    context_id: str = field(init=False)
    terminal_class: DevelopmentCompleteAdaptiveTerminalClassV1 = field(
        init=False,
        default=(
            DevelopmentCompleteAdaptiveTerminalClassV1.PLAN_CERTIFICATE
        ),
    )
    terminal_code: DevelopmentCompleteAdaptiveTerminalCodeV1 = field(
        init=False
    )
    prior_cold_draws: int = field(init=False)
    incremental_suffix_draws: int = field(init=False)
    total_accepted_draws: int = field(init=False)
    _run_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.law_key) is not materializer.DevelopmentLawKeyV1
            or type(self.arm) is not selector.TargetSelectionArmV2
            or type(self.round_selections) is not tuple
            or type(self.selector_verifications) is not tuple
            or type(self.handoffs) is not tuple
            or type(self.control_materializer_attestation)
            is not (
                materializer_independent
                .IndependentIncrementalMaterializerAttestationV1
            )
            or type(self.handoff_materializer_attestations) is not tuple
            or type(self.postbuild_results) is not tuple
            or type(self.postbuild_independent_attestations) is not tuple
            or len(self.handoffs) not in (1, 2)
            or len(self.postbuild_results) != len(self.handoffs)
            or len(self.handoff_materializer_attestations)
            != len(self.handoffs)
            or len(self.postbuild_independent_attestations)
            != len(self.handoffs)
            or len(self.round_selections)
            != len(self.selector_verifications)
            or len(self.round_selections) != len(self.handoffs) - 1
            or any(
                type(item) is not selector.PreparedTargetSelectionV2
                for item in self.round_selections
            )
            or any(
                type(item)
                is not (
                    selector_component
                    .V072TargetSelectorSemanticVerificationV1
                )
                for item in self.selector_verifications
            )
            or any(
                type(item)
                is not materializer.IncrementalModelRebuildHandoffV1
                for item in self.handoffs
            )
            or any(
                type(item)
                is not (
                    materializer_independent
                    .IndependentIncrementalMaterializerAttestationV1
                )
                for item in self.handoff_materializer_attestations
            )
            or any(
                type(item) is not bridge.IncrementalPostbuildResultV1
                for item in self.postbuild_results
            )
            or any(
                type(item)
                is not (
                    postbuild_independent
                    .IndependentIncrementalPostbuildAttestationV1
                )
                for item in self.postbuild_independent_attestations
            )
        ):
            raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                "complete run lacks one exact typed authority chain"
            )

        first = self.handoffs[0]
        occurrence_id = _cid(
            first.request.parent_epoch.logical_occurrence_id,
            "logical occurrence",
        )
        context_id = _cid(
            first.request.parent_epoch.context_id,
            "development context",
        )
        if (
            first.request.parent_epoch.round_index != 1
            or first.request.previous_handoff_id is not None
            or first.law_key is not self.law_key
            or first.request.parent_epoch.arm != self.arm.value
        ):
            raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                "first adaptive round is not the native frozen occurrence"
            )

        control_attestation = self.control_materializer_attestation
        expected_control_run_id = (
            materializer.DevelopmentAcquisitionControlRunV1(
                self.law_key,
                first,
            ).run_id
        )
        if (
            control_attestation.run_id != expected_control_run_id
            or control_attestation.handoff_id != first.handoff_id
            or control_attestation.law_key != self.law_key.value
            or control_attestation.context_id != context_id
            or control_attestation.logical_occurrence_id != occurrence_id
            or control_attestation.transaction_id != first.transaction_id
            or control_attestation.build_epoch_id != first.build_epoch_id
            or control_attestation.round_index != 1
            or control_attestation.previous_handoff_id is not None
            or control_attestation.acquired_child_row_count
            != first.counters.acquired_child_rows
            or control_attestation.exact_draw_count
            != first.counters.accepted_draws
        ):
            raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                "control-role materializer attestation is not bound to round one"
            )
        if (
            control_attestation.attestation_id
            == self.handoff_materializer_attestations[0].attestation_id
        ):
            raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                "control and generic handoff attestation roles were conflated"
            )

        for index, (
            handoff,
            handoff_attestation,
            result,
            attestation,
        ) in enumerate(
            zip(
                self.handoffs,
                self.handoff_materializer_attestations,
                self.postbuild_results,
                self.postbuild_independent_attestations,
                strict=True,
            ),
            start=1,
        ):
            previous_handoff = (
                None if index == 1 else self.handoffs[index - 2]
            )
            previous_result = (
                None if index == 1 else self.postbuild_results[index - 2]
            )
            if (
                handoff.law_key is not self.law_key
                or handoff.request.parent_epoch.arm != self.arm.value
                or handoff.request.parent_epoch.logical_occurrence_id
                != occurrence_id
                or handoff.request.parent_epoch.context_id != context_id
                or handoff.request.parent_epoch.round_index != index
                or handoff.request.previous_handoff_id
                != (
                    None
                    if previous_handoff is None
                    else previous_handoff.handoff_id
                )
                or result.handoff_id != handoff.handoff_id
                or handoff_attestation.handoff_id != handoff.handoff_id
                or handoff_attestation.law_key != self.law_key.value
                or handoff_attestation.context_id != context_id
                or handoff_attestation.logical_occurrence_id
                != occurrence_id
                or handoff_attestation.transaction_id
                != handoff.transaction_id
                or handoff_attestation.build_epoch_id
                != handoff.build_epoch_id
                or handoff_attestation.round_index != index
                or handoff_attestation.previous_handoff_id
                != handoff.request.previous_handoff_id
                or handoff_attestation.acquired_child_row_count
                != handoff.counters.acquired_child_rows
                or handoff_attestation.exact_draw_count
                != handoff.counters.accepted_draws
                or attestation.postbuild_result_id != result.result_id
                or attestation.handoff_id != handoff.handoff_id
                or attestation.audit_id != result.audit_id
                or attestation.audit_status != result.audit_status.value
                or attestation.failed_frontier_id
                != result.failed_frontier_id
                or attestation.round_index != index
                or attestation.materializer_attestation_id
                != handoff_attestation.attestation_id
                or attestation.prior_postbuild_result_id
                != (
                    None
                    if previous_result is None
                    else previous_result.result_id
                )
            ):
                raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                    "adaptive round lineage or independent replay is stale"
                )

        for offset, (selection, verification) in enumerate(
            zip(
                self.round_selections,
                self.selector_verifications,
                strict=True,
            ),
            start=2,
        ):
            handoff = self.handoffs[offset - 1]
            if (
                selection.authorization
                != handoff.request.authorization
                or selection.access_log
                != handoff.request.preauthorization_access
                or selection.authorization.round_index != offset
                or selection.authorization.arm is not self.arm
                or verification.prepared_selection_id
                != selection.prepared_selection_id
                or verification.round_index != offset
                or verification.authorization_id
                != selection.authorization.authorization_id
                or verification.access_log_id
                != selection.access_log.access_log_id
                or verification.arm is not self.arm
                or (
                    verification
                    .previous_materializer_attestation_id
                )
                != self.control_materializer_attestation.attestation_id
            ):
                raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                    "recovery selector event is not bound to its next round"
                )

        if len(self.handoffs) == 1:
            terminal_code = (
                DevelopmentCompleteAdaptiveTerminalCodeV1
                .PLAN_CERTIFIED_AFTER_FIRST_INCREMENTAL_REBUILD
            )
            if (
                self.law_key
                is not materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_A
                or self.postbuild_results[0].audit_status
                is not robust.RobustAuditStatus.CERTIFIED
                or self.round_selections
                or self.selector_verifications
            ):
                raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                    "one-round development occurrence is not Law-A certified"
                )
        else:
            terminal_code = (
                DevelopmentCompleteAdaptiveTerminalCodeV1
                .PLAN_CERTIFIED_AFTER_SECOND_INCREMENTAL_REBUILD
            )
            if (
                self.law_key
                is not materializer.DevelopmentLawKeyV1.HASH_BUCKET_LAW_B
                or self.postbuild_results[0].audit_status
                is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
                or self.postbuild_results[1].audit_status
                is not robust.RobustAuditStatus.CERTIFIED
                or self.postbuild_results[0].failed_frontier_id is None
                or self.postbuild_results[1].failed_frontier_id is not None
            ):
                raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                    "two-round occurrence does not retain failed Law-B work"
                )

        prior_ranges = first.prior_cold_raw_commitment_ranges
        suffix_ranges = tuple(
            item
            for handoff in self.handoffs
            for item in handoff.raw_commitment_ranges
        )
        prior_draws = sum(item.draw_count for item in prior_ranges)
        suffix_draws = sum(
            handoff.counters.accepted_draws for handoff in self.handoffs
        )
        if (
            prior_draws != PRIOR_COLD_DRAWS
            or self.handoffs[0].counters.accepted_draws
            != ROUND_ONE_SUFFIX_DRAWS
            or (
                len(self.handoffs) == 2
                and self.handoffs[1].counters.accepted_draws
                != ROUND_TWO_SUFFIX_DRAWS
            )
            or len({item.stream_id for item in prior_ranges})
            != len(prior_ranges)
            or len({item.range_proof_id for item in prior_ranges})
            != len(prior_ranges)
            or len({item.stream_id for item in suffix_ranges})
            != len(suffix_ranges)
            or len({item.range_proof_id for item in suffix_ranges})
            != len(suffix_ranges)
            or {
                item.stream_id for item in prior_ranges
            }
            & {item.stream_id for item in suffix_ranges}
            or (
                len(self.handoffs) == 2
                and tuple(
                    item.range_proof_id
                    for item in self.handoffs[1]
                    .prior_cold_raw_commitment_ranges
                )
                != tuple(item.range_proof_id for item in prior_ranges)
            )
        ):
            raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                "accepted draws are duplicated, omitted, or double-charged"
            )

        certificate_model_ids = {
            result.model_pair.quotient_planner_projection.planner_model.model_id
            for result in self.postbuild_results
        }
        proposal_model_ids = {
            item.resolution_model_id
            for selection in self.round_selections
            for item in selection.counterfactuals
            if item.resolution_model_id is not None
        }
        if certificate_model_ids & proposal_model_ids:
            raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                "proposal-only resolution model became certificate authority"
            )

        object.__setattr__(self, "logical_occurrence_id", occurrence_id)
        object.__setattr__(self, "context_id", context_id)
        object.__setattr__(self, "terminal_code", terminal_code)
        object.__setattr__(self, "prior_cold_draws", prior_draws)
        object.__setattr__(
            self,
            "incremental_suffix_draws",
            suffix_draws,
        )
        object.__setattr__(
            self,
            "total_accepted_draws",
            prior_draws + suffix_draws,
        )
        object.__setattr__(
            self,
            "_run_id",
            _content_id("run", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_complete_adaptive_run.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "law_key": self.law_key.value,
            "arm": self.arm.value,
            "execution_lane": self.execution_lane.value,
            "logical_occurrence_id": self.logical_occurrence_id,
            "context_id": self.context_id,
            "selection_event_count": len(self.round_selections),
            "materialization_round_count": len(self.handoffs),
            "round_selection_ids": [
                item.prepared_selection_id
                for item in self.round_selections
            ],
            "selector_verification_ids": [
                item.verification_id
                for item in self.selector_verifications
            ],
            "handoff_ids": [
                item.handoff_id for item in self.handoffs
            ],
            "control_materializer_attestation_id": (
                self.control_materializer_attestation.attestation_id
            ),
            "handoff_materializer_attestation_ids": [
                item.attestation_id
                for item in self.handoff_materializer_attestations
            ],
            "materializer_attestation_roles_distinct": (
                self.control_materializer_attestation.attestation_id
                != self.handoff_materializer_attestations[0].attestation_id
            ),
            "postbuild_result_ids": [
                item.result_id for item in self.postbuild_results
            ],
            "postbuild_independent_attestation_ids": [
                item.attestation_id
                for item in self.postbuild_independent_attestations
            ],
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "prior_cold_draws": self.prior_cold_draws,
            "incremental_suffix_draws": self.incremental_suffix_draws,
            "total_accepted_draws": self.total_accepted_draws,
            "prior_cold_work_double_charged": False,
            "failed_intermediate_work_retained": (
                len(self.handoffs) == 2
            ),
            "caller_supplied_status": False,
            "caller_supplied_counts": False,
            "caller_supplied_result": False,
            "proposal_resolution_model_used_for_certificate": False,
            "registered_target_evidence": False,
            "registered_execution_allowed": False,
        }

    @property
    def run_id(self) -> str:
        return self._run_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "run_id": self.run_id}


def run_development_complete_adaptive_planning_control_v1(
    *,
    law_key: materializer.DevelopmentLawKeyV1,
    arm: selector.TargetSelectionArmV2 = (
        selector.TargetSelectionArmV2.NO_PRIOR
    ),
    source_prior: selector.VerifiedSourcePriorBindingV2 | None = None,
    ood_abstention: selector.OodPriorTypedAbstentionV2 | None = None,
    logical_occurrence_id: str | None = None,
) -> DevelopmentCompleteAdaptivePlanningRunV1:
    """Execute a complete development adaptive planning occurrence."""

    first_control = (
        materializer.run_development_incremental_materializer_control_v1(
            law_key,
            arm,
            source_prior,
            ood_abstention,
            logical_occurrence_id,
        )
    )
    first_handoff = first_control.handoff
    first_control_attestation = (
        materializer_independent
        .verify_development_incremental_materializer_control_v1(
            first_control
        )
    )
    first_handoff_attestation = (
        materializer_independent.verify_incremental_materializer_handoff_v1(
            first_handoff
        )
    )
    first_postbuild = bridge.run_incremental_postbuild_bridge_v1(
        handoff=first_handoff,
    )
    first_postbuild_attestation = (
        postbuild_independent.verify_incremental_postbuild_result_v1(
            handoff=first_handoff,
            claimed=first_postbuild,
        )
    )

    if first_postbuild.certified:
        completed = DevelopmentCompleteAdaptivePlanningRunV1(
            law_key=law_key,
            arm=arm,
            round_selections=(),
            selector_verifications=(),
            handoffs=(first_handoff,),
            control_materializer_attestation=(
                first_control_attestation
            ),
            handoff_materializer_attestations=(
                first_handoff_attestation,
            ),
            postbuild_results=(first_postbuild,),
            postbuild_independent_attestations=(
                first_postbuild_attestation,
            ),
        )
        if (
            logical_occurrence_id is not None
            and completed.logical_occurrence_id
            != _cid(logical_occurrence_id, "requested logical occurrence")
        ):
            raise DevelopmentCompleteAdaptiveRunInvariantViolation(
                "native occurrence differs from requested workload identity"
            )
        return completed

    preparation = bridge.prepare_actual_development_round_two_request_v1(
        first_handoff=first_handoff,
        failed_postbuild=first_postbuild,
        arm=arm,
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )
    second_handoff = materializer.materialize_authorized_incremental_round_v1(
        law_key=law_key,
        request=preparation.request,
    )
    second_handoff_attestation = (
        materializer_independent.verify_incremental_materializer_handoff_v1(
            second_handoff,
            previous_handoff=first_handoff,
        )
    )
    second_postbuild = bridge.run_incremental_postbuild_bridge_v1(
        handoff=second_handoff,
        prior_handoff=first_handoff,
        prior_postbuild=first_postbuild,
    )
    second_postbuild_attestation = (
        postbuild_independent.verify_incremental_postbuild_result_v1(
            handoff=second_handoff,
            claimed=second_postbuild,
            prior_handoff=first_handoff,
            prior_postbuild=first_postbuild,
        )
    )
    completed = DevelopmentCompleteAdaptivePlanningRunV1(
        law_key=law_key,
        arm=arm,
        round_selections=(preparation.selection,),
        selector_verifications=(preparation.selector_verification,),
        handoffs=(first_handoff, second_handoff),
        control_materializer_attestation=first_control_attestation,
        handoff_materializer_attestations=(
            first_handoff_attestation,
            second_handoff_attestation,
        ),
        postbuild_results=(first_postbuild, second_postbuild),
        postbuild_independent_attestations=(
            first_postbuild_attestation,
            second_postbuild_attestation,
        ),
    )
    if (
        logical_occurrence_id is not None
        and completed.logical_occurrence_id
        != _cid(logical_occurrence_id, "requested logical occurrence")
    ):
        raise DevelopmentCompleteAdaptiveRunInvariantViolation(
            "native occurrence differs from requested workload identity"
        )
    return completed


def run_registered_v072_complete_adaptive_planning_v1(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise RegisteredV072CompleteAdaptiveRunLocked(
        "registered execution remains locked until confirmatory target "
        "authorities and the frozen campaign manifest are complete"
    )


__all__ = [
    "DevelopmentAdaptiveExecutionLaneV1",
    "DevelopmentCompleteAdaptivePlanningRunV1",
    "DevelopmentCompleteAdaptiveRunInvariantViolation",
    "DevelopmentCompleteAdaptiveTerminalClassV1",
    "DevelopmentCompleteAdaptiveTerminalCodeV1",
    "PRIOR_COLD_DRAWS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_EXECUTION_ALLOWED",
    "ROUND_ONE_SUFFIX_DRAWS",
    "ROUND_TWO_SUFFIX_DRAWS",
    "RegisteredV072CompleteAdaptiveRunLocked",
    "SCHEMA_VERSION",
    "run_development_complete_adaptive_planning_control_v1",
    "run_registered_v072_complete_adaptive_planning_v1",
]
