"""Owner-accounted causal-promotion occurrence through budget closure.

This is the first production-shaped consumer of the V3 causal child,
promotion, and budget-closure chain.  It runs the same deterministic K7
occurrence inside the additive owner-accounting V2 lifecycle, including the
three incremental-acquisition instances and four checkpoint-replanning
instances.

The result retains exact stage-local CounterRecord/WorkVector/
ComparisonVector artifacts.  It deliberately does not aggregate them into an
occurrence WorkVector: shared resource measurement, ``io.output_bytes`` fixed
point, and all-site completeness are still open.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Iterable

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import construction_accounting_owned_runtime_v2 as accounting_v2
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_operational_context_v3 as operational_context
from acfqp import sequential_bernoulli_acquisition_v1 as bernoulli
from acfqp import v075_five_arm_acquisition_authority_v2 as acquisition
from acfqp import v075_live_batched_causal_budget_closure_v3 as budget
from acfqp import v075_live_batched_causal_child_authority_v3 as causal
from acfqp import v075_live_batched_causal_child_execution_v3 as execution
from acfqp import v075_live_batched_causal_promotion_v3 as promotion
from acfqp import v075_observer_signed_batch_control_authority_v2 as control
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as root_runner
from acfqp import v075_preopen_target_authorization_v2 as preopen
from acfqp import v075_private_observer_boundary_v2 as observer
from acfqp import v075_public_target_tape_namespace_v2 as namespace_v2


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.78"
PROFILE_KEY = "v075_live_batched_causal_accounted_occurrence_v1"
RESULT_DOMAIN = "acfqp:v075-live-batched-causal-accounted-occurrence:v1"

OCCURRENCE_WORK_VECTOR_ISSUED = False
SHARED_RESOURCE_MEASUREMENT_COMPLETE = False
ALL_SITE_COMPLETENESS_CLAIMED = False
OFFICIAL_EXECUTION_ALLOWED = False


class V075LiveBatchedCausalAccountedOccurrenceV1Error(RuntimeError):
    """The staged occurrence or one of its exact identity joins failed."""


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalAccountedOccurrenceV1:
    schedule: acquisition.V075InitialAcquisitionScheduleV2 = field(repr=False)
    schedule_verification: acquisition.V075InitialAcquisitionVerificationV2 = field(
        repr=False
    )
    root_execution: Any = field(repr=False)
    root_epoch: Any = field(repr=False)
    child_authorization: causal.V075LiveBatchedCausalChildAuthorizationV3 = field(
        repr=False
    )
    child_authorization_verification: (
        causal.V075LiveBatchedCausalChildVerificationV3
    ) = field(repr=False)
    child_execution: execution.V075LiveBatchedCausalExecutionBundleV3 = field(
        repr=False
    )
    promotion_bundle: promotion.V075LiveBatchedCausalPromotionBundleV3 = field(
        repr=False
    )
    budget_closure: budget.V075LiveBatchedCausalBudgetClosedOccurrenceV3 = field(
        repr=False
    )
    budget_closure_verification: (
        budget.V075LiveBatchedCausalBudgetClosureVerificationV3
    )
    accounting_result: accounting_v2.OwnedCausalPromotionAccountingResultV2

    def __post_init__(self) -> None:
        if (
            type(self.schedule)
            is not acquisition.V075InitialAcquisitionScheduleV2
            or type(self.schedule_verification)
            is not acquisition.V075InitialAcquisitionVerificationV2
            or type(self.child_authorization)
            is not causal.V075LiveBatchedCausalChildAuthorizationV3
            or type(self.child_authorization_verification)
            is not causal.V075LiveBatchedCausalChildVerificationV3
            or type(self.child_execution)
            is not execution.V075LiveBatchedCausalExecutionBundleV3
            or type(self.promotion_bundle)
            is not promotion.V075LiveBatchedCausalPromotionBundleV3
            or type(self.budget_closure)
            is not budget.V075LiveBatchedCausalBudgetClosedOccurrenceV3
            or type(self.budget_closure_verification)
            is not budget.V075LiveBatchedCausalBudgetClosureVerificationV3
            or type(self.accounting_result)
            is not accounting_v2.OwnedCausalPromotionAccountingResultV2
        ):
            raise V075LiveBatchedCausalAccountedOccurrenceV1Error(
                "accounted occurrence contains a foreign artifact"
            )
        if (
            self.schedule_verification.schedule.schedule_id
            != self.schedule.schedule_id
            or self.schedule_verification.schedule.canonical_bytes
            != self.schedule.canonical_bytes
            or self.child_authorization.source_closure.source_epoch
            is not self.root_epoch
            or self.child_execution.authorization.authorization_id
            != self.child_authorization.authorization_id
            or self.promotion_bundle.child_execution_bundle.bundle_id
            != self.child_execution.bundle_id
            or self.budget_closure.promotion_bundle.bundle_id
            != self.promotion_bundle.bundle_id
            or self.budget_closure_verification.closure_id
            != self.budget_closure.closure_id
            or self.accounting_result.occurrence_id
            != self.schedule.occurrence.occurrence_id
        ):
            raise V075LiveBatchedCausalAccountedOccurrenceV1Error(
                "accounted occurrence identity chain crossed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_batched_causal_accounted_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.schedule.occurrence.occurrence_id,
            "schedule_id": self.schedule.schedule_id,
            "schedule_verification_id": (
                self.schedule_verification.verification_id
            ),
            "root_execution_id": self.root_execution.execution_id,
            "root_model_epoch_id": self.root_epoch.model_epoch_id,
            "causal_child_authorization_id": (
                self.child_authorization.authorization_id
            ),
            "causal_child_authorization_verification_id": (
                self.child_authorization_verification.verification_id
            ),
            "causal_child_execution_bundle_id": self.child_execution.bundle_id,
            "causal_promotion_bundle_id": self.promotion_bundle.bundle_id,
            "budget_closure_id": self.budget_closure.closure_id,
            "budget_closure_verification_id": (
                self.budget_closure_verification.verification_id
            ),
            "owned_accounting_result_id": self.accounting_result.result_id,
            "stage_instance_count": len(
                self.accounting_result.recorded_stages
            ),
            "stage_local_counter_record_count": sum(
                len(item.work_vector.records)
                for item in self.accounting_result.recorded_stages
            ),
            "stage_local_work_vector_count": len(
                self.accounting_result.recorded_stages
            ),
            "stage_local_comparison_vector_count": len(
                self.accounting_result.recorded_stages
            ),
            "terminal_target_class": "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "terminal_target_code": "ATTEMPT_BUDGET_EXHAUSTED",
            "observer_closed_and_exactly_reconciled": True,
            "occurrence_work_vector_issued": OCCURRENCE_WORK_VECTOR_ISSUED,
            "shared_resource_measurement_complete": (
                SHARED_RESOURCE_MEASUREMENT_COMPLETE
            ),
            "all_site_completeness_claimed": ALL_SITE_COMPLETENESS_CLAIMED,
            "semantic_terminal_artifact_issued": False,
            "official_execution_allowed": OFFICIAL_EXECUTION_ALLOWED,
        }

    @property
    def result_id(self) -> str:
        return hashlib.sha256(
            RESULT_DOMAIN.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(self._payload())
        ).hexdigest()

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounted_occurrence_id": self.result_id}


def run_v075_live_batched_causal_accounted_occurrence_v1(
    *,
    namespace: namespace_v2.V075PublicTargetTapeNamespaceV2,
    schedule: acquisition.V075InitialAcquisitionScheduleV2,
    schedule_verification: acquisition.V075InitialAcquisitionVerificationV2,
    authority: preopen.V075ObserverOpenAuthorizationV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Any]]],
    observer_signer: observer.V075ObserverEvidenceSignerProtocolV2,
    session_external_id: str,
) -> V075LiveBatchedCausalAccountedOccurrenceV1:
    """Execute the exact causal budget-exhaustion occurrence under V2 stages."""

    try:
        with bernoulli.isolate_exact_bernoulli_math_cache_v1():
            bernoulli.clear_exact_bernoulli_math_cache_v1()
            with accounting_v2.activate_owned_causal_promotion_accounting_v2(
                occurrence_id=schedule.occurrence.occurrence_id
            ):
                with operational_context._activate_owned_no_full_replay_v3():  # noqa: SLF001
                    accounting_v2.enter_owned_causal_promotion_stage_v2(
                        registry_v6.ConstructionStageKindV6
                        .PREOPEN_COMMON_PREFIX
                    )
                    controller = (
                        control
                        .open_v075_construction_controlled_private_observer_v2(
                            authority=authority,
                            namespace=namespace,
                            private_salt=private_salt,
                            private_environment=private_environment,
                            observer_signer=observer_signer,
                            session_external_id=session_external_id,
                            occurrence_identity=schedule.occurrence,
                        )
                    )
                    accounting_v2.exit_owned_causal_promotion_stage_v2(
                        registry_v6.ConstructionStageKindV6
                        .PREOPEN_COMMON_PREFIX,
                        output_bindings=(
                            ("initial_schedule", schedule.schedule_id),
                            (
                                "initial_schedule_verification",
                                schedule_verification.verification_id,
                            ),
                            (
                                "controlled_observer_zero_head",
                                controller.current_signed_head.head_id,
                            ),
                        ),
                    )
                    accounting_v2.enter_owned_causal_promotion_stage_v2(
                        registry_v6.ConstructionStageKindV6
                        .INITIAL_ACQUISITION
                    )
                    root_execution = root_runner._execute_initial_root_schedule(  # noqa: SLF001
                        controller=controller,
                        namespace=namespace,
                        schedule=schedule,
                        verification=schedule_verification,
                    )
                    accounting_v2.exit_owned_causal_promotion_stage_v2(
                        registry_v6.ConstructionStageKindV6
                        .INITIAL_ACQUISITION,
                        output_bindings=(
                            ("root_execution", root_execution.execution_id),
                        ),
                    )
                    accounting_v2.enter_owned_causal_promotion_stage_v2(
                        registry_v6.ConstructionStageKindV6.INITIAL_MODEL_BUILD
                    )
                    root_epoch = root_runner._freeze_root_epoch(  # noqa: SLF001
                        controller=controller,
                        schedule=schedule,
                    )
                    accounting_v2.exit_owned_causal_promotion_stage_v2(
                        registry_v6.ConstructionStageKindV6.INITIAL_MODEL_BUILD,
                        output_bindings=(
                            ("root_model", root_epoch.model.model_id),
                            ("root_model_epoch", root_epoch.model_epoch_id),
                            ("root_proof", root_epoch.proof.proof_id),
                        ),
                    )
                    accounting_v2.enter_owned_causal_promotion_stage_v2(
                        registry_v6.ConstructionStageKindV6
                        .FAILED_ABSTRACT_PREFIX
                    )
                    (
                        child_authorization,
                        child_authorization_verification,
                    ) = (
                        causal
                        .authorize_and_attest_v075_live_batched_causal_children_owned_v3(
                            source_epoch=root_epoch,
                            namespace=namespace,
                        )
                    )
                    child_execution = (
                        execution.execute_v075_live_batched_causal_children_v3(
                            controller=controller,
                            namespace=namespace,
                            schedule=schedule,
                            authorization=child_authorization,
                            authorization_verification=(
                                child_authorization_verification
                            ),
                        )
                    )
                    promotion_bundle = (
                        promotion.execute_v075_live_batched_causal_promotions_v3(
                            controller=controller,
                            schedule=schedule,
                            child_execution_bundle=child_execution,
                        )
                    )
                    budget_closure, budget_verification = (
                        budget.close_v075_live_batched_causal_budget_exhausted_v3(
                            controller=controller,
                            promotion_bundle=promotion_bundle,
                        )
                    )
                    accounting_result = (
                        accounting_v2
                        .complete_owned_causal_promotion_occurrence_v2()
                    )
                    if accounting_result is None:  # pragma: no cover
                        raise V075LiveBatchedCausalAccountedOccurrenceV1Error(
                            "owned accounting result is absent"
                        )
            bernoulli.clear_exact_bernoulli_math_cache_v1()
    except Exception as error:
        if type(error) is V075LiveBatchedCausalAccountedOccurrenceV1Error:
            raise
        raise V075LiveBatchedCausalAccountedOccurrenceV1Error(
            "owned causal-promotion occurrence failed"
        ) from error
    return V075LiveBatchedCausalAccountedOccurrenceV1(
        schedule,
        schedule_verification,
        root_execution,
        root_epoch,
        child_authorization,
        child_authorization_verification,
        child_execution,
        promotion_bundle,
        budget_closure,
        budget_verification,
        accounting_result,
    )


__all__ = (
    "ALL_SITE_COMPLETENESS_CLAIMED",
    "OCCURRENCE_WORK_VECTOR_ISSUED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "SHARED_RESOURCE_MEASUREMENT_COMPLETE",
    "V075LiveBatchedCausalAccountedOccurrenceV1",
    "V075LiveBatchedCausalAccountedOccurrenceV1Error",
    "run_v075_live_batched_causal_accounted_occurrence_v1",
)
