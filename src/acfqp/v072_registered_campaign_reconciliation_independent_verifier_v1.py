"""Independent replay of the registered V0-072 15-occurrence ledger.

The verifier does not call the production reconciliation authority.  It
replays the authority/plan/source graph, both route-native independent
verifiers, terminal/evaluation bindings, native work lanes, all aggregates,
and every reconciliation content ID from duplicated formulas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import observation_support_campaign_v1 as source_campaign
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import verified_source_acquisition_archive_v2 as source_archive
from acfqp import (
    verified_source_acquisition_archive_independent_verifier_v2
    as source_archive_independent,
)
from acfqp import v072_independent_exact_ground_evaluator_v1 as evaluator
from acfqp import v072_registered_adaptive_quotient_runtime_v1 as adaptive
from acfqp import (
    v072_registered_adaptive_quotient_runtime_independent_verifier_v1
    as adaptive_independent,
)
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_registered_cold_h2_orchestrator_v1 as cold_runtime
from acfqp import v072_registered_incremental_epoch_materializer_v1 as incremental
from acfqp import v072_registered_matched_direct_runtime_v1 as direct
from acfqp import v072_registered_operational_terminal_authority_v1 as terminal
from acfqp import (
    v072_registered_campaign_reconciliation_v1 as claimed_types,
)
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe
from acfqp import v072_verified_source_archive_component_v1 as source_component


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = (
    "v072_registered_campaign_reconciliation_independent_verifier_v1"
)
VERIFICATION_DOMAIN = (
    "acfqp:v072-registered-campaign-reconciliation-"
    "independent-verification:v1"
)
DOMAINS = {
    "typed_na": "acfqp:v072-registered-reconciliation-typed-na:v1",
    "source_offline": (
        "acfqp:v072-registered-reconciliation-source-offline:v1"
    ),
    "work": "acfqp:v072-registered-reconciliation-occurrence-work:v1",
    "occurrence": "acfqp:v072-registered-reconciliation-occurrence:v1",
    "totals": "acfqp:v072-registered-reconciliation-totals:v1",
    "campaign": "acfqp:v072-registered-campaign-reconciliation:v1",
}


class IndependentRegisteredCampaignReconciliationFailure(ValueError):
    """The claimed ledger differs from exact independent replay."""


def _fail(message: str) -> None:
    raise IndependentRegisteredCampaignReconciliationFailure(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise IndependentRegisteredCampaignReconciliationFailure(
            f"independent content replay failed: {error}"
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise IndependentRegisteredCampaignReconciliationFailure(
            f"{label} is not one content ID"
        ) from error


def _expected_plan(
    chain_id: str,
) -> consumer.RegisteredCampaignExecutionPlanV1:
    return consumer.RegisteredCampaignExecutionPlanV1(
        chain_id,
        tuple(
            consumer.RegisteredOccurrenceExecutionPlanV1(chain_id, template)
            for template in consumer.registered_occurrence_templates_v1()
        ),
    )


def _source_payload(
    replay: source_recipe.SourceReconstructionReplayV1,
    raw_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_registered_source_offline_accounting.v1",
        "schema_version": claimed_types.SCHEMA_VERSION,
        "source_recipe_id": replay.recipe_id,
        "source_campaign_id": replay.source_campaign.campaign_id,
        "source_campaign_verification_id": (
            replay.source_verification.verification_id
        ),
        "source_archive_id": replay.archive.archive_id,
        "production_archive_verification_id": (
            replay.production_verification.verification_id
        ),
        "independent_archive_attestation_id": (
            replay.independent_attestation.verification_id
        ),
        "source_component_id": replay.component.component_id,
        "physical_raw_observation_ids": list(raw_ids),
        "unique_physical_raw_draws": len(raw_ids),
        "online_draws_charged": 0,
        "lane": "SOURCE_ARCHIVE_OFFLINE",
        "union_not_cumulative_prefix_sum": True,
    }


def _replay_source(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    replay: source_recipe.SourceReconstructionReplayV1,
    claimed: claimed_types.RegisteredSourceOfflineAccountingV1,
) -> None:
    if (
        type(replay) is not source_recipe.SourceReconstructionReplayV1
        or type(claimed)
        is not claimed_types.RegisteredSourceOfflineAccountingV1
        or replay.recipe_id
        != authority_chain.manifest.global_bindings[
            "source_reconstruction_recipe_id"
        ]
        or type(replay.source_campaign)
        is not source_campaign.ObservationSupportCampaignV1
        or type(replay.source_verification)
        is not source_campaign.ObservationSupportCampaignVerificationV1
        or type(replay.archive)
        is not source_archive.VerifiedSourceAcquisitionArchiveV2
        or type(replay.production_verification)
        is not source_archive.VerifiedSourceAcquisitionArchiveVerificationV2
        or type(replay.independent_attestation)
        is not source_archive_independent.IndependentSourceAcquisitionArchiveVerificationV2
        or type(replay.component)
        is not source_component.V072VerifiedSourceArchiveComponentV1
        or replay.source_verification.campaign_id
        != replay.source_campaign.campaign_id
        or replay.source_verification.replayed_campaign_id
        != replay.source_campaign.campaign_id
    ):
        _fail("source reconstruction replay has a foreign type or identity")
    production = source_archive.verify_verified_source_acquisition_archive_v2(
        source_campaign=replay.source_campaign,
        source_verification=replay.source_verification,
        claimed=replay.archive,
    )
    independent = (
        source_archive_independent
        .verify_source_acquisition_archive_independently_v2(
            source_campaign=replay.source_campaign,
            source_verification=replay.source_verification,
            claimed=replay.archive,
        )
    )
    component = source_component.bind_v072_verified_source_archive_component_v1(
        archive=replay.archive,
        production_verification=production,
        independent_attestation=independent,
    )
    bindings = authority_chain.manifest.global_bindings
    if (
        production != replay.production_verification
        or independent != replay.independent_attestation
        or component != replay.component
        or bindings["source_archive_id"] != replay.archive.archive_id
        or bindings["source_archive_verification_attestation_id"]
        != independent.verification_id
    ):
        _fail("source archive dual replay/component binding differs")
    raw_ids = tuple(
        sorted(
            {
                raw_id
                for result in replay.source_campaign.context_results
                for raw_id in result.accounting.physical_unique_observation_ids
            }
        )
    )
    if (
        len(raw_ids) != replay.source_campaign.physical_unique_observer_draws
        or len(raw_ids)
        != replay.source_campaign.counters.physical_unique_observer_draws
        or claimed.physical_raw_observation_ids != raw_ids
        or claimed.unique_physical_raw_draws != len(raw_ids)
        or claimed.online_draws_charged != 0
    ):
        _fail("source offline union/count was altered or mixed online")
    payload = _source_payload(replay, raw_ids)
    expected_id = _hash(DOMAINS["source_offline"], payload)
    if (
        claimed.accounting_id != expected_id
        or claimed.to_document() != {**payload, "accounting_id": expected_id}
    ):
        _fail("source offline accounting content ID differs")


def _occurrence_identity(
    anchor_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
) -> evaluator.RegisteredOccurrenceIdentityV1:
    template = plan.template
    return evaluator.RegisteredOccurrenceIdentityV1(
        anchor_id,
        template.context_id,
        template.context_key,
        template.arm,
        template.context_ordinal,
        template.arm_ordinal,
        template.occurrence_ordinal,
    )


def _evaluation_values(
    evaluation: evaluator.RegisteredIndependentExactGroundEvaluationResultV1 | None,
) -> tuple[str | None, int, int, int, int, int, int, int]:
    if evaluation is None:
        return (None, 0, 0, 0, 0, 0, 0, 0)
    work = evaluation.work
    return (
        work.work_id,
        work.evaluation_exact_atom_api_calls,
        work.exact_rows_reconstructed,
        work.exact_atoms_reconstructed,
        work.dp_candidate_extensions,
        work.dp_dominance_comparisons,
        work.dp_frontier_points_retained,
        work.selected_policy_assignments_checked,
    )


def _check_certificate(
    *,
    anchor_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    operational_artifact_id: str,
    runtime_verification_id: str,
    authority: Any,
    evaluation: Any,
) -> None:
    if (
        type(authority)
        is not terminal.RegisteredOperationalTerminalAuthorityResultV1
        or type(evaluation)
        is not evaluator.RegisteredIndependentExactGroundEvaluationResultV1
    ):
        _fail("certified occurrence lacks exact terminal/evaluation types")
    bundle = authority.evaluator_bundle
    terminal_artifact = bundle.operational_terminal
    policy = bundle.selected_policy
    expected_occurrence = _occurrence_identity(anchor_id, plan)
    policy_runtime_verification = getattr(
        policy,
        "independent_runtime_verification_id",
        runtime_verification_id,
    )
    policy_route = getattr(
        policy,
        "route_kind",
        plan.template.route_kind.value,
    )
    if (
        terminal_artifact.occurrence != expected_occurrence
        or policy.occurrence != expected_occurrence
        or terminal_artifact.terminal_code
        != "CONDITIONAL_PLAN_CERTIFICATE"
        or terminal_artifact.operational_result_artifact_id
        != operational_artifact_id
        or policy.operational_policy_source_artifact_id
        != operational_artifact_id
        or policy_runtime_verification != runtime_verification_id
        or policy_route != plan.template.route_kind.value
        or terminal_artifact.selected_policy_id != policy.selected_policy_id
        or evaluation.anchor_id != anchor_id
        or evaluation.occurrence != expected_occurrence
        or evaluation.operational_terminal_id
        != terminal_artifact.terminal_id
        or evaluation.operational_selected_policy_id
        != policy.selected_policy_id
        or evaluation.status
        is not (
            evaluator.RegisteredExactGroundEvaluationStatusV1
            .CERTIFICATE_METRICS_PASS
        )
        or evaluation.certificate_metrics_pass is not True
        or evaluation.execution_lane != evaluator.EVALUATION_LANE
        or evaluation.operational_work_included is not False
    ):
        _fail("certified terminal/policy/exact evaluation was transplanted")


ADAPTIVE_TERMINAL_CODES = {
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED: (
        "CONDITIONAL_PLAN_CERTIFICATE"
    ),
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.EXACT_DP_RESOURCE_EXHAUSTED: (
        "EXACT_DP_RESOURCE_EXHAUSTED_NONCERTIFICATE"
    ),
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.NO_SOUND_COVER: (
        "NO_POSITIVE_GAIN_NONCERTIFICATE"
    ),
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.ACQUISITION_CAP_EXHAUSTED: (
        "INCREMENTAL_CAP_EXHAUSTED_NONCERTIFICATE"
    ),
    adaptive.RegisteredAdaptiveOccurrenceStatusV1.NOT_CERTIFIED_MAX_ROUNDS: (
        "TWO_ROUND_CAP_EXHAUSTED_NONCERTIFICATE"
    ),
}


def _typed_na_payload(
    *,
    occurrence_id: str,
    role: str,
    terminal_code: str,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_registered_reconciliation_typed_na.v1",
        "schema_version": claimed_types.SCHEMA_VERSION,
        "kind": "NOT_APPLICABLE",
        "occurrence_id": occurrence_id,
        "role": role,
        "terminal_code": terminal_code,
        "reason_code": "ROUTE_NATIVE_NONCERTIFICATE",
        "caller_supplied": False,
    }


def _work_payload(
    *,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    operational_work_id: str,
    runtime_verification_id: str,
    online: int,
    replay: int,
    evaluation_values: tuple[str | None, int, int, int, int, int, int, int],
) -> dict[str, Any]:
    (
        evaluation_work_id,
        atom_calls,
        rows,
        atoms,
        candidate_extensions,
        dominance,
        frontier,
        policy_assignments,
    ) = evaluation_values
    return {
        "schema": "acfqp.v072_registered_occurrence_lane_accounting.v1",
        "schema_version": claimed_types.SCHEMA_VERSION,
        "occurrence_id": plan.occurrence_id,
        "route_kind": plan.template.route_kind.value,
        "operational_route_work_id": operational_work_id,
        "runtime_independent_verification_id": runtime_verification_id,
        "online_acquisition_draws": online,
        "target_replay_draws": replay,
        "exact_evaluation_work_id": evaluation_work_id,
        "exact_evaluation_atom_calls": atom_calls,
        "exact_evaluation_rows": rows,
        "exact_evaluation_atoms": atoms,
        "exact_evaluation_candidate_extensions": candidate_extensions,
        "exact_evaluation_dominance_comparisons": dominance,
        "exact_evaluation_frontier_points": frontier,
        "exact_evaluation_policy_assignments": policy_assignments,
        "source_offline_draws": 0,
        "crn_discount_draws": 0,
        "online_replay_evaluation_source_lanes_separate": True,
    }


def _replay_occurrence(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor_id: str,
    final_preregistration_id: str,
    plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    context: prereg.HeldoutPublicGraphContextV2,
    claimed: claimed_types.RegisteredReconciledOccurrenceV1,
) -> dict[str, Any]:
    if (
        type(claimed) is not claimed_types.RegisteredReconciledOccurrenceV1
        or claimed.occurrence_plan != plan
    ):
        _fail("reconciled occurrence was omitted, reordered, or replaced")
    route = claimed.route_result
    if plan.template.route_kind is consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT:
        if type(route) is not adaptive.RegisteredAdaptiveQuotientVerifiedRuntimeResultV1:
            _fail("adaptive occurrence has a foreign route result")
        execution = route.execution
        runtime_verification = (
            adaptive_independent
            .verify_registered_adaptive_runtime_independently_v1(
                authority_chain=authority_chain,
                anchor=authority_chain.remote_main_anchor,
                occurrence_plan=plan,
                context=context,
                claimed=execution,
            )
        )
        if (
            runtime_verification != route.independent_verification
            or runtime_verification != claimed.runtime_verification
            or execution.authority_chain_id != authority_chain.chain_id
            or execution.anchor_id != anchor_id
            or execution.occurrence_plan != plan
            or execution.context != context
        ):
            _fail("adaptive route/runtime verification identity differs")
        terminal_code = ADAPTIVE_TERMINAL_CODES[execution.status]
        certified = (
            execution.status
            is adaptive.RegisteredAdaptiveOccurrenceStatusV1.CERTIFIED
        )
        final_epoch = execution.epochs[-1]
        if type(final_epoch) is cold_runtime.RegisteredColdH2ModelEpochV1:
            acquisitions = final_epoch.acquisitions
        elif type(final_epoch) is incremental.RegisteredIncrementalH2ModelEpochV1:
            acquisitions = final_epoch.acquisition_history
        else:
            _fail("adaptive final epoch has a foreign type")
        online = sum(len(item.transcript.entries) for item in acquisitions)
        if (
            len({item.acquisition_id for item in acquisitions})
            != len(acquisitions)
            or online != execution.work.producer_draw_calls
            or online != execution.work.unique_online_sample_evidence_draws
            or execution.work.total_observer_draw_calls
            != online + execution.work.replay_draw_calls
        ):
            _fail("adaptive failed/incremental draws were omitted")
        replay = execution.work.replay_draw_calls
        operational_work_id = execution.work.work_id
        operational_artifact_id = execution.result_id
        route_result_id = route.verified_result_id
        model_epoch_id = final_epoch.epoch_id
        planner_model_id = (
            final_epoch.model_pair.quotient_planner_model.model_id
        )
    else:
        if type(route) is not direct.RegisteredMatchedDirectOccurrenceResultV1:
            _fail("matched-direct occurrence has a foreign route result")
        try:
            canonical_direct_plan = (
                direct.registered_matched_direct_occurrence_plan_v1(
                    anchor=authority_chain.remote_main_anchor,
                    context=context,
                )
            )
        except (ValueError, RuntimeError) as error:
            raise IndependentRegisteredCampaignReconciliationFailure(
                "canonical matched-direct occurrence plan replay failed"
            ) from error
        template = plan.template
        if (
            type(canonical_direct_plan)
            is not direct.RegisteredMatchedDirectOccurrencePlanV1
            or canonical_direct_plan.anchor_id != anchor_id
            or canonical_direct_plan.context_id != template.context_id
            or canonical_direct_plan.context_key != template.context_key
            or canonical_direct_plan.context_ordinal
            != template.context_ordinal
            or canonical_direct_plan.arm != template.arm
            or canonical_direct_plan.arm_ordinal != template.arm_ordinal
            or canonical_direct_plan.occurrence_ordinal
            != template.occurrence_ordinal
        ):
            _fail("canonical direct plan is outside the consumer schedule")
        runtime_verification = (
            direct.verify_registered_matched_direct_occurrence_result_v1(route)
        )
        if (
            runtime_verification != claimed.runtime_verification
            or route.authority_chain_id != authority_chain.chain_id
            or route.anchor_id != anchor_id
            or route.final_preregistration_id != final_preregistration_id
            or route.occurrence_plan_id != canonical_direct_plan.plan_id
            or route.context_id != context.context_id
            or route.crn_draw_discount != 0
        ):
            _fail("direct route was reused or transplanted")
        terminal_code = route.terminal_code.value
        certified = route.certified
        final_checkpoint = route.checkpoint_records[-1].inventory_checkpoint
        online = route.acquisition_sample_total
        replay = route.deterministic_verifier_replay_total
        operational_work_id = final_checkpoint.work.work_id
        operational_artifact_id = route.result_id
        route_result_id = route.result_id
        model_epoch_id = final_checkpoint.checkpoint_id
        planner_model_id = final_checkpoint.direct_snapshot.planner_model.model_id
    if terminal_code not in prereg.TERMINAL_CODES:
        _fail("route-native terminal code is outside preregistration")
    runtime_verification_id = runtime_verification.verification_id
    expected_terminal_class = (
        claimed_types.RegisteredReconciliationTerminalClassV1.PLAN_CERTIFICATE
        if certified
        else (
            claimed_types.RegisteredReconciliationTerminalClassV1
            .ATTEMPT_CLOSURE_NONCERTIFICATE
        )
    )
    if (
        claimed.terminal_class is not expected_terminal_class
        or claimed.terminal_code != terminal_code
        or claimed.final_model_epoch_id != model_epoch_id
        or claimed.final_planner_model_id != planner_model_id
    ):
        _fail("occurrence terminal or model identity differs")
    if certified:
        _check_certificate(
            anchor_id=anchor_id,
            plan=plan,
            operational_artifact_id=operational_artifact_id,
            runtime_verification_id=runtime_verification_id,
            authority=claimed.operational_terminal_authority,
            evaluation=claimed.exact_evaluation,
        )
        if (
            claimed.terminal_not_applicable is not None
            or claimed.evaluation_not_applicable is not None
        ):
            _fail("certificate carries a noncertificate typed N/A")
        terminal_na_id = None
        evaluation_na_id = None
        evaluation = claimed.exact_evaluation
    else:
        if (
            claimed.operational_terminal_authority is not None
            or claimed.exact_evaluation is not None
        ):
            _fail("noncertificate carries plan-only evidence")
        na_specs = (
            (
                claimed.terminal_not_applicable,
                "OPERATIONAL_PLAN_TERMINAL",
            ),
            (
                claimed.evaluation_not_applicable,
                "EXACT_PLAN_EVALUATION",
            ),
        )
        ids = []
        for value, role in na_specs:
            if (
                type(value)
                is not claimed_types.RegisteredReconciliationTypedNotApplicableV1
            ):
                _fail("noncertificate typed N/A is absent")
            payload = _typed_na_payload(
                occurrence_id=plan.occurrence_id,
                role=role,
                terminal_code=terminal_code,
            )
            expected_na_id = _hash(DOMAINS["typed_na"], payload)
            if (
                value.typed_na_id != expected_na_id
                or value.to_document()
                != {**payload, "typed_na_id": expected_na_id}
            ):
                _fail("noncertificate typed N/A differs")
            ids.append(expected_na_id)
        terminal_na_id, evaluation_na_id = ids
        evaluation = None
    evaluation_values = _evaluation_values(evaluation)
    work_payload = _work_payload(
        plan=plan,
        operational_work_id=operational_work_id,
        runtime_verification_id=runtime_verification_id,
        online=online,
        replay=replay,
        evaluation_values=evaluation_values,
    )
    work_id = _hash(DOMAINS["work"], work_payload)
    if (
        claimed.work.accounting_id != work_id
        or claimed.work.to_document()
        != {**work_payload, "accounting_id": work_id}
    ):
        _fail("occurrence online/replay/evaluation work differs")
    authority_result_id = (
        None
        if claimed.operational_terminal_authority is None
        else claimed.operational_terminal_authority.authority_result_id
    )
    operational_terminal_id = (
        None
        if claimed.operational_terminal_authority is None
        else (
            claimed.operational_terminal_authority.evaluator_bundle
            .operational_terminal.terminal_id
        )
    )
    selected_policy_id = (
        None
        if claimed.operational_terminal_authority is None
        else (
            claimed.operational_terminal_authority.evaluator_bundle
            .selected_policy.selected_policy_id
        )
    )
    evaluation_result_id = (
        None if evaluation is None else evaluation.result_id
    )
    occurrence_payload = {
        "schema": "acfqp.v072_registered_reconciled_occurrence.v1",
        "schema_version": claimed_types.SCHEMA_VERSION,
        "occurrence_id": plan.occurrence_id,
        "occurrence_ordinal": plan.template.occurrence_ordinal,
        "context_id": plan.template.context_id,
        "context_key": plan.template.context_key,
        "arm": plan.template.arm,
        "route_kind": plan.template.route_kind.value,
        "route_result_id": route_result_id,
        "runtime_verification_id": runtime_verification_id,
        "terminal_class": expected_terminal_class.value,
        "terminal_code": terminal_code,
        "final_model_epoch_id": model_epoch_id,
        "final_planner_model_id": planner_model_id,
        "operational_terminal_authority_result_id": authority_result_id,
        "operational_terminal_id": operational_terminal_id,
        "selected_policy_id": selected_policy_id,
        "exact_evaluation_result_id": evaluation_result_id,
        "terminal_not_applicable_id": terminal_na_id,
        "evaluation_not_applicable_id": evaluation_na_id,
        "work_accounting_id": work_id,
        "replacement_allowed": False,
        "crn_draw_discount": 0,
    }
    occurrence_id = _hash(DOMAINS["occurrence"], occurrence_payload)
    if claimed.occurrence_record_id != occurrence_id:
        _fail("occurrence reconciliation content ID differs")
    return {
        "occurrence_record_id": occurrence_id,
        "route_result_id": route_result_id,
        "runtime_verification_id": runtime_verification_id,
        "terminal_class": expected_terminal_class.value,
        "work": work_payload,
    }


TOTAL_FIELDS = (
    "online_acquisition_draws",
    "target_replay_draws",
    "exact_evaluation_atom_calls",
    "exact_evaluation_rows",
    "exact_evaluation_atoms",
    "exact_evaluation_candidate_extensions",
    "exact_evaluation_dominance_comparisons",
    "exact_evaluation_frontier_points",
    "exact_evaluation_policy_assignments",
)


def _totals_payload(
    *,
    scope: str,
    scope_key: str,
    facts: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.v072_registered_reconciliation_totals.v1",
        "schema_version": claimed_types.SCHEMA_VERSION,
        "scope": scope,
        "scope_key": scope_key,
        "occurrence_record_ids": [
            item["occurrence_record_id"] for item in facts
        ],
        **{
            field_name: sum(
                int(item["work"][field_name]) for item in facts
            )
            for field_name in TOTAL_FIELDS
        },
        "plan_certificate_count": sum(
            item["terminal_class"] == "PLAN_CERTIFICATE"
            for item in facts
        ),
        "noncertificate_count": sum(
            item["terminal_class"]
            == "ATTEMPT_CLOSURE_NONCERTIFICATE"
            for item in facts
        ),
        "crn_discount_draws": 0,
        "source_offline_draws_included": False,
    }


def _check_totals(
    *,
    claimed: claimed_types.RegisteredReconciliationTotalsV1,
    payload: dict[str, Any],
) -> str:
    expected_id = _hash(DOMAINS["totals"], payload)
    if (
        type(claimed)
        is not claimed_types.RegisteredReconciliationTotalsV1
        or claimed.totals_id != expected_id
        or claimed.to_document() != {**payload, "totals_id": expected_id}
    ):
        _fail("context/arm/campaign totals differ")
    return expected_id


@dataclass(frozen=True, slots=True)
class RegisteredCampaignReconciliationIndependentVerificationV1:
    authority_chain_id: str
    execution_plan_id: str
    reconciliation_id: str
    source_offline_accounting_id: str
    occurrence_record_ids: tuple[str, ...]
    context_totals_ids: tuple[str, ...]
    arm_totals_ids: tuple[str, ...]
    campaign_totals_id: str
    logical_occurrence_denominator: int = 15
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.authority_chain_id,
            self.execution_plan_id,
            self.reconciliation_id,
            self.source_offline_accounting_id,
            *self.occurrence_record_ids,
            *self.context_totals_ids,
            *self.arm_totals_ids,
            self.campaign_totals_id,
        ):
            _cid(value, "independent reconciliation identity")
        if (
            len(self.occurrence_record_ids) != 15
            or len(set(self.occurrence_record_ids)) != 15
            or len(self.context_totals_ids) != 3
            or len(self.arm_totals_ids) != 5
            or self.logical_occurrence_denominator != 15
        ):
            _fail("independent reconciliation verification is incomplete")
        object.__setattr__(
            self,
            "_verification_id",
            _hash(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_campaign_reconciliation_"
                "independent_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "execution_plan_id": self.execution_plan_id,
            "reconciliation_id": self.reconciliation_id,
            "source_offline_accounting_id": (
                self.source_offline_accounting_id
            ),
            "occurrence_record_ids": list(self.occurrence_record_ids),
            "context_totals_ids": list(self.context_totals_ids),
            "arm_totals_ids": list(self.arm_totals_ids),
            "campaign_totals_id": self.campaign_totals_id,
            "logical_occurrence_denominator": 15,
            "production_reconciliation_called": False,
            "online_replay_evaluation_source_lanes_replayed": True,
            "crn_draw_discount": 0,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_registered_v072_campaign_reconciliation_independently_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    execution_plan: consumer.RegisteredCampaignExecutionPlanV1,
    source_reconstruction_replay: source_recipe.SourceReconstructionReplayV1,
    claimed: claimed_types.RegisteredCampaignReconciliationV1,
) -> RegisteredCampaignReconciliationIndependentVerificationV1:
    """Independently replay one complete registered reconciliation bundle."""

    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(claimed)
        is not claimed_types.RegisteredCampaignReconciliationV1
    ):
        _fail("independent verifier requires exact production types")
    try:
        (
            source_recipe_id,
            manifest_id,
            final_preregistration_id,
            anchor_id,
            _anchor_attestation_id,
        ) = consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (ValueError, RuntimeError) as error:
        raise IndependentRegisteredCampaignReconciliationFailure(
            "independent authority-chain replay failed"
        ) from error
    expected_plan = _expected_plan(authority_chain.chain_id)
    if (
        type(execution_plan) is not consumer.RegisteredCampaignExecutionPlanV1
        or execution_plan != expected_plan
        or claimed.execution_plan != expected_plan
        or claimed.authority_chain_id != authority_chain.chain_id
        or claimed.anchor_id != anchor_id
        or claimed.source_reconstruction_recipe_id != source_recipe_id
        or claimed.manifest_id != manifest_id
        or claimed.final_preregistration_id != final_preregistration_id
        or claimed.logical_occurrence_denominator != 15
        or claimed.endpoint_claimed is not False
        or claimed.sample_efficiency_gate_status != "NOT_RUN"
    ):
        _fail("campaign authority/plan/lock identity differs")
    _replay_source(
        authority_chain=authority_chain,
        replay=source_reconstruction_replay,
        claimed=claimed.source_offline,
    )
    if (
        type(claimed.occurrences) is not tuple
        or len(claimed.occurrences) != 15
    ):
        _fail("campaign does not retain all 15 occurrences")
    contexts = {
        item.context_id: item
        for item in prereg.registered_heldout_public_contexts_v2()
    }
    facts = tuple(
        _replay_occurrence(
            authority_chain=authority_chain,
            anchor_id=anchor_id,
            final_preregistration_id=final_preregistration_id,
            plan=plan,
            context=contexts[plan.template.context_id],
            claimed=occurrence,
        )
        for plan, occurrence in zip(
            execution_plan.occurrences,
            claimed.occurrences,
            strict=True,
        )
    )
    if (
        len({item["occurrence_record_id"] for item in facts}) != 15
        or len({item["route_result_id"] for item in facts}) != 15
        or len({item["runtime_verification_id"] for item in facts}) != 15
    ):
        _fail("occurrence/result/runtime verification was reused")
    context_ids: list[str] = []
    for context, aggregate in zip(
        prereg.registered_heldout_public_contexts_v2(),
        claimed.context_totals,
        strict=True,
    ):
        subset = tuple(
            fact
            for fact, plan in zip(
                facts,
                execution_plan.occurrences,
                strict=True,
            )
            if plan.template.context_id == context.context_id
        )
        payload = _totals_payload(
            scope="CONTEXT",
            scope_key=context.context_key,
            facts=subset,
        )
        context_ids.append(_check_totals(claimed=aggregate, payload=payload))
    arm_ids: list[str] = []
    for arm, aggregate in zip(
        prereg.ARM_ORDER,
        claimed.arm_totals,
        strict=True,
    ):
        subset = tuple(
            fact
            for fact, plan in zip(
                facts,
                execution_plan.occurrences,
                strict=True,
            )
            if plan.template.arm == arm
        )
        payload = _totals_payload(
            scope="ARM",
            scope_key=arm,
            facts=subset,
        )
        arm_ids.append(_check_totals(claimed=aggregate, payload=payload))
    campaign_payload = _totals_payload(
        scope="CAMPAIGN",
        scope_key="REGISTERED_V072_CONTEXT_MAJOR_3_X_5",
        facts=facts,
    )
    campaign_totals_id = _check_totals(
        claimed=claimed.campaign_totals,
        payload=campaign_payload,
    )
    campaign_claim_payload = {
        "schema": "acfqp.v072_registered_campaign_reconciliation.v1",
        "schema_version": claimed_types.SCHEMA_VERSION,
        "proposed_contract_version": (
            claimed_types.PROPOSED_CONTRACT_VERSION
        ),
        "profile_key": claimed_types.PROFILE_KEY,
        "authority_chain_id": authority_chain.chain_id,
        "anchor_id": anchor_id,
        "source_reconstruction_recipe_id": source_recipe_id,
        "manifest_id": manifest_id,
        "final_preregistration_id": final_preregistration_id,
        "execution_plan_id": execution_plan.plan_id,
        "source_offline_accounting_id": (
            claimed.source_offline.accounting_id
        ),
        "occurrence_record_ids": [
            item["occurrence_record_id"] for item in facts
        ],
        "context_totals_ids": context_ids,
        "arm_totals_ids": arm_ids,
        "campaign_totals_id": campaign_totals_id,
        "logical_occurrence_denominator": 15,
        "all_occurrences_retained": True,
        "replacement_allowed": False,
        "campaign_early_stop_allowed": False,
        "crn_draw_discount": 0,
        "source_offline_in_online_totals": False,
        "endpoint_claimed": False,
        "sample_efficiency_gate_status": "NOT_RUN",
    }
    reconciliation_id = _hash(DOMAINS["campaign"], campaign_claim_payload)
    if claimed.reconciliation_id != reconciliation_id:
        _fail("campaign reconciliation content ID differs")
    return RegisteredCampaignReconciliationIndependentVerificationV1(
        authority_chain.chain_id,
        execution_plan.plan_id,
        reconciliation_id,
        claimed.source_offline.accounting_id,
        tuple(item["occurrence_record_id"] for item in facts),
        tuple(context_ids),
        tuple(arm_ids),
        campaign_totals_id,
    )


__all__ = [
    "IndependentRegisteredCampaignReconciliationFailure",
    "PROFILE_KEY",
    "RegisteredCampaignReconciliationIndependentVerificationV1",
    "SCHEMA_VERSION",
    "verify_registered_v072_campaign_reconciliation_independently_v1",
]
