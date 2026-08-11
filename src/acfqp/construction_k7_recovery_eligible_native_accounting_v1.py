"""Execute and bind the recovery-eligible loop to three native stage chains.

This is the stage-local half of occurrence accounting.  It produces exact
V3 CounterRecord -> WorkVector -> ComparisonVector evidence for acquisition,
replanning, and fallback.  The nine occurrence-wide shared paths remain
explicit native-zero placeholders until a supervised outer measurement
replaces them; therefore this module does not issue an occurrence WorkVector.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_k7_recovery_eligible_checkpoint_fixture_v1 as checkpoint_v1
from acfqp import construction_k7_recovery_eligible_direct_ground_fallback_v1 as fallback_v1
from acfqp import construction_k7_recovery_eligible_stage_accounting_v1 as stage_v1
from acfqp import construction_k7_recovery_eligible_world_model_loop_v1 as loop_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NATIVE_ACCOUNTING_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.114"
PROFILE_KEY = "construction_k7_recovery_eligible_native_accounting_v1"
RESULT_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NATIVE_ACCOUNTING_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESULT_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("recovery native-accounting domain is not central")

_ISSUER = object()


class ConstructionK7RecoveryEligibleNativeAccountingV1Error(ValueError):
    """The scientific chain and its exact stage evidence diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleNativeAccountingV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleNativeAccountingV1Error(
            f"{label} must be one content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class RecoveryEligibleNativeAccountedOccurrenceV1:
    _issuer: InitVar[object]
    request: checkpoint_v1.RecoveryEligibleRecoveryRequestV1 = field(repr=False)
    world_model_loop: loop_v1.RecoveryEligibleWorldModelLoopV1 = field(repr=False)
    fallback: fallback_v1.RecoveryEligibleDirectGroundFallbackV1 = field(repr=False)
    stage_accounting: stage_v1.RecoveryEligibleStageAccountingResultV1
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or type(self.request)
            is not checkpoint_v1.RecoveryEligibleRecoveryRequestV1
            or type(self.world_model_loop)
            is not loop_v1.RecoveryEligibleWorldModelLoopV1
            or type(self.fallback)
            is not fallback_v1.RecoveryEligibleDirectGroundFallbackV1
            or type(self.stage_accounting)
            is not stage_v1.RecoveryEligibleStageAccountingResultV1
        ):
            _fail("recovery native-accounted occurrence is caller-minted")
        checkpoint_v1.require_recovery_eligible_recovery_request_v1(self.request)
        loop_v1.require_recovery_eligible_world_model_loop_v1(self.world_model_loop)
        stage_v1.verify_recovery_eligible_stage_accounting_v1(self.stage_accounting)
        query = self.request.consumption.query
        rows = self.stage_accounting.recorded_stages
        if (
            self.world_model_loop.transaction.request.request_id != self.request.request_id
            or self.fallback.predecessor.result_id != self.world_model_loop.result_id
            or self.stage_accounting.occurrence_id != query.logical_occurrence_id
            or self.stage_accounting.stage_output_bindings
            != (
                (("GROUND_TRANSACTION", self.world_model_loop.transaction.transaction_id),),
                (("WORLD_MODEL_LOOP", self.world_model_loop.result_id),),
                (
                    ("DIRECT_FALLBACK", self.fallback.result_id),
                    ("FALLBACK_INVENTORY", self.fallback.inventory_id),
                    ("FALLBACK_WORK", self.fallback.work.work_id),
                ),
            )
            or len(rows) != 3
        ):
            _fail("recovery scientific and accounting identities crossed")
        acquisition, replanning, fallback = (row.work_vector.values for row in rows)
        transaction = self.world_model_loop.transaction
        work = self.fallback.work
        expected_acquisition = {
            "acquisition.incremental_engine_ground_draws": transaction.total_ground_draw_count,
            "acquisition.incremental_engine_random_word_calls": transaction.total_ground_draw_count,
            "acquisition.incremental_engine_stream_initialization_merges": 2 * len(transaction.row_acquisitions),
            "acquisition.incremental_observer_accumulator_updates": transaction.total_ground_draw_count,
            "acquisition.incremental_outcome_aggregate_rows": sum(
                len(item.batch.outcomes) for item in transaction.observer_closure.appends
            ),
            "acquisition.incremental_signed_batches_committed": len(transaction.observer_closure.appends),
            "acquisition.incremental_signed_batches_materialized": len(transaction.observer_closure.appends),
            "acquisition.incremental_support_freezes": len(transaction.observer_closure.support_freezes),
        }
        expected_fallback = {
            "control.cap_checks": (
                work.states_expanded
                + work.actions_evaluated
                + work.ground_steps
                + work.actions_evaluated
                + work.bellman_backups
            ),
            "control.cap_rejections": 0,
            "fallback.states_expanded": work.states_expanded,
            "fallback.actions_evaluated": work.actions_evaluated,
            "fallback.ground_steps": work.ground_steps,
            "fallback.outcome_rows": work.outcome_rows,
            "fallback.bellman_backups": work.bellman_backups,
        }
        if (
            any(acquisition[path] != value for path, value in expected_acquisition.items())
            or any(fallback[path] != value for path, value in expected_fallback.items())
            or replanning["build.open_checkpoint_model_rows_built"]
            != len(self.world_model_loop.deltas)
            or replanning["build.open_checkpoint_batch_v2_frontier_obligations_built"]
            != len(self.world_model_loop.successor_proof.failed_frontier.obligations)
            or any(
                values[path] != 0
                for values in (acquisition, replanning, fallback)
                for path in stage_v1.SHARED_RESOURCE_PATHS
            )
        ):
            _fail("recovery native stage counters differ from scientific evidence")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        query = self.request.consumption.query
        rows = self.stage_accounting.recorded_stages
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_native_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": query.logical_occurrence_id,
            "recovery_request_id": self.request.request_id,
            "ground_transaction_id": self.world_model_loop.transaction.transaction_id,
            "world_model_loop_id": self.world_model_loop.result_id,
            "direct_ground_fallback_id": self.fallback.result_id,
            "fallback_work_id": self.fallback.work.work_id,
            "stage_accounting_id": self.stage_accounting.result_id,
            "stage_counter_record_counts": [
                len(row.work_vector.records) for row in rows
            ],
            "stage_work_vector_ids": [row.work_vector.work_vector_id for row in rows],
            "stage_comparison_vector_ids": [
                row.comparison_vector.comparison_vector_id for row in rows
            ],
            "stage_actual_projection_proof_ids": [
                row.actual_projection_proof.actual_projection_proof_id for row in rows
            ],
            "stage_count": len(rows),
            "counter_records_per_stage": registry_v6.EXPECTED_V6_REQUIRED_LEAF_COUNT,
            "all_182_operational_leaves_projected_exactly_once_per_stage": True,
            "local_ground_draw_count": self.world_model_loop.transaction.total_ground_draw_count,
            "changed_abstract_row_count": len(self.world_model_loop.changed_row_binding_ids),
            "fallback_ground_step_count": self.fallback.work.ground_steps,
            "terminal_class": self.fallback.terminal_class.value,
            "terminal_code": self.fallback.terminal_code.value,
            "cached_prefix_common_native_counters_materialized": False,
            "nine_shared_resource_receipts_present": False,
            "route_family_occurrence_vectors_issued": False,
            "campaign_denominator_closed": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
            "next_required_action": "SUPERVISE_NINE_SHARED_RESOURCES_AND_MATERIALIZE_OCCURRENCE_VECTORS",
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("recovery native-accounted occurrence changed")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "stage_accounting": self.stage_accounting.to_document(),
            "recovery_eligible_native_accounting_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def execute_recovery_eligible_native_accounted_occurrence_v1(
    request: checkpoint_v1.RecoveryEligibleRecoveryRequestV1,
) -> RecoveryEligibleNativeAccountedOccurrenceV1:
    request = checkpoint_v1.require_recovery_eligible_recovery_request_v1(request)
    occurrence_id = request.consumption.query.logical_occurrence_id
    with stage_v1.activate_recovery_eligible_stage_accounting_v1(
        occurrence_id=occurrence_id
    ) as accounting:
        accounting.enter_stage(registry_v6.ConstructionStageKindV6.OPEN_INCREMENTAL_ACQUISITION)
        transaction = loop_v1.execute_prepared_recovery_eligible_ground_transaction_v1(
            loop_v1.prepare_recovery_eligible_ground_transaction_v1(request)
        )
        accounting.exit_stage(
            output_bindings=(("GROUND_TRANSACTION", transaction.transaction_id),)
        )

        accounting.enter_stage(registry_v6.ConstructionStageKindV6.OPEN_CHECKPOINT_REPLANNING)
        world_model_loop = loop_v1.compile_recovery_eligible_world_model_loop_v1(
            transaction
        )
        accounting.exit_stage(
            output_bindings=(("WORLD_MODEL_LOOP", world_model_loop.result_id),)
        )

        accounting.enter_stage(registry_v6.ConstructionStageKindV6.DIRECT_FALLBACK)
        fallback = fallback_v1.execute_recovery_eligible_direct_ground_fallback_v1(
            world_model_loop
        )
        accounting.exit_stage(
            output_bindings=(
                ("DIRECT_FALLBACK", fallback.result_id),
                ("FALLBACK_INVENTORY", fallback.inventory_id),
                ("FALLBACK_WORK", fallback.work.work_id),
            )
        )
        stage_result = accounting.complete_occurrence()
    return RecoveryEligibleNativeAccountedOccurrenceV1(
        _ISSUER,
        request,
        world_model_loop,
        fallback,
        stage_result,
    )


def verify_recovery_eligible_native_accounting_v1(
    result: RecoveryEligibleNativeAccountedOccurrenceV1,
) -> RecoveryEligibleNativeAccountedOccurrenceV1:
    if type(result) is not RecoveryEligibleNativeAccountedOccurrenceV1:
        _fail("native accounting verifier received a foreign result")
    result.__post_init__(_ISSUER)
    loop_v1.verify_recovery_eligible_world_model_loop_v1(result.world_model_loop)
    stage_v1.verify_recovery_eligible_stage_accounting_v1(result.stage_accounting)
    return result


__all__ = (
    "ConstructionK7RecoveryEligibleNativeAccountingV1Error",
    "LOCAL_DOMAINS",
    "RecoveryEligibleNativeAccountedOccurrenceV1",
    "execute_recovery_eligible_native_accounted_occurrence_v1",
    "verify_recovery_eligible_native_accounting_v1",
)
