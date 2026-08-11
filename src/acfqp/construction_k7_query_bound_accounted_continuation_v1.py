"""Execute the complete query-bound continuation under five stage ledgers.

The runner starts from an already failed reusable abstract query.  It performs
two bounded local ground transactions, recompiles and replans after each, and
then executes the exact direct-ground fallback required by the exhausted
certificate frontier.  The scientific result and every stage-local V6 vector
remain joined, while occurrence-wide shared-resource accounting stays
explicitly pending.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_direct_ground_fallback_v1 as fallback_v1
from acfqp import construction_k7_query_bound_final_local_replanning_v1 as final_v1
from acfqp import construction_k7_query_bound_ground_transaction_v1 as ground_v1
from acfqp import construction_k7_query_bound_overlay_replanning_v1 as replan_v1
from acfqp import construction_k7_query_bound_recovery_request_v1 as request_v1
from acfqp import construction_k7_query_bound_second_ground_transaction_v1 as ground2_v1
from acfqp import construction_k7_query_bound_second_recovery_request_v1 as request2_v1
from acfqp import construction_k7_query_bound_stage_accounting_v1 as accounting_v1
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTED_CONTINUATION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.96"
PROFILE_KEY = "construction_k7_query_bound_accounted_continuation_v1"
RESULT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_ACCOUNTED_CONTINUATION_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESULT_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound accounted-continuation domain is not central")

_ISSUER = object()
_S = registry_v6.ConstructionStageKindV6


class ConstructionK7QueryBoundAccountedContinuationV1Error(ValueError):
    """The scientific chain and its stage accounting diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundAccountedContinuationV1Error(message)


@dataclass(frozen=True, slots=True)
class QueryBoundAccountedContinuationV1:
    _issuer: InitVar[object]
    transaction_1: ground_v1.QueryBoundGroundTransactionV1 = field(repr=False)
    replanning_1: replan_v1.QueryBoundOverlayReplanningV1 = field(repr=False)
    request_2: request2_v1.SecondQueryBoundRecoveryRequestV1 = field(repr=False)
    transaction_2: ground2_v1.SecondQueryBoundGroundTransactionV1 = field(repr=False)
    final_local_replanning: final_v1.QueryBoundFinalLocalReplanningV1 = field(
        repr=False
    )
    direct_fallback: fallback_v1.QueryBoundDirectGroundFallbackV1 = field(
        repr=False
    )
    accounting: accounting_v1.QueryBoundStageAccountingResultV1 = field(
        repr=False
    )
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _ISSUER
            or type(self.transaction_1) is not ground_v1.QueryBoundGroundTransactionV1
            or type(self.replanning_1) is not replan_v1.QueryBoundOverlayReplanningV1
            or type(self.request_2) is not request2_v1.SecondQueryBoundRecoveryRequestV1
            or type(self.transaction_2)
            is not ground2_v1.SecondQueryBoundGroundTransactionV1
            or type(self.final_local_replanning)
            is not final_v1.QueryBoundFinalLocalReplanningV1
            or type(self.direct_fallback)
            is not fallback_v1.QueryBoundDirectGroundFallbackV1
            or type(self.accounting)
            is not accounting_v1.QueryBoundStageAccountingResultV1
        ):
            _fail("query-bound accounted continuation is caller-minted")
        ground_v1.verify_query_bound_ground_transaction_v1(self.transaction_1)
        identity_pairs = (
            (
                self.replanning_1.transaction.transaction_id,
                self.transaction_1.transaction_id,
                "replanning-1 predecessor",
            ),
            (
                self.request_2.predecessor_replanning_id,
                self.replanning_1.result_id,
                "transaction-2 request predecessor",
            ),
            (
                self.transaction_2.predecessor.result_id,
                self.replanning_1.result_id,
                "transaction-2 predecessor",
            ),
            (
                self.transaction_2.request.request_id,
                self.request_2.request_id,
                "transaction-2 request",
            ),
            (
                self.final_local_replanning.transaction.transaction_id,
                self.transaction_2.transaction_id,
                "final-local predecessor",
            ),
            (
                self.direct_fallback.predecessor.result_id,
                self.final_local_replanning.result_id,
                "direct-fallback predecessor",
            ),
            (
                self.accounting.occurrence_id,
                self.transaction_1.request.logical_occurrence_id,
                "accounting occurrence",
            ),
        )
        for actual, expected, label in identity_pairs:
            if actual != expected:
                _fail(f"query-bound accounted continuation crossed {label}")
        expected_outputs = (
            (("GROUND_TRANSACTION_1", self.transaction_1.transaction_id),),
            (
                ("RECOVERY_REQUEST_2", self.request_2.request_id),
                ("REPLANNING_1", self.replanning_1.result_id),
            ),
            (("GROUND_TRANSACTION_2", self.transaction_2.transaction_id),),
            (("FINAL_LOCAL_REPLANNING", self.final_local_replanning.result_id),),
            (("DIRECT_GROUND_FALLBACK", self.direct_fallback.result_id),),
        )
        if self.accounting.stage_output_bindings != expected_outputs:
            _fail("query-bound accounted continuation crossed stage outputs")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_accounted_continuation.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "logical_occurrence_id": self.transaction_1.request.logical_occurrence_id,
            "reusable_abstract_query_id": self.transaction_1.request.reusable_abstract_query_id,
            "transaction_1_id": self.transaction_1.transaction_id,
            "replanning_1_id": self.replanning_1.result_id,
            "transaction_2_request_id": self.request_2.request_id,
            "transaction_2_id": self.transaction_2.transaction_id,
            "final_local_replanning_id": self.final_local_replanning.result_id,
            "direct_ground_fallback_id": self.direct_fallback.result_id,
            "stage_accounting_result_id": self.accounting.result_id,
            "stage_plan": [
                row.value for row in accounting_v1.CANONICAL_QUERY_BOUND_STAGE_PLAN_V1
            ],
            "local_transaction_count": 2,
            "maximum_local_transactions_per_logical_occurrence": 2,
            "transaction_3_created": False,
            "cumulative_local_ground_draw_count": (
                self.transaction_1.total_ground_draw_count
                + self.transaction_2.total_ground_draw_count
            ),
            "certificate_failure_triggered_only_local_ground_recovery": True,
            "unrequested_ground_rows_recovered": 0,
            "immutable_query_local_overlays_compiled": 2,
            "abstract_replanning_after_each_local_transaction": True,
            "fallback_executed_only_after_local_budget_exhaustion": True,
            "terminal_class": self.direct_fallback.terminal_class.value,
            "terminal_code": self.direct_fallback.terminal_code.value,
            "plan_certificate_issued": (
                self.direct_fallback.terminal_class
                is fallback_v1.QueryBoundDirectFallbackTerminalClassV1.PLAN_CERTIFICATE
            ),
            "infeasibility_certificate_issued": (
                self.direct_fallback.terminal_class
                is (
                    fallback_v1.QueryBoundDirectFallbackTerminalClassV1
                    .INFEASIBILITY_CERTIFICATE
                )
            ),
            "stage_local_counter_record_chain_present": True,
            "stage_local_work_vectors_present": True,
            "stage_local_comparison_vectors_present": True,
            "shared_resource_receipts_present": False,
            "occurrence_counter_record_chain_present": False,
            "occurrence_work_vector_present": False,
            "occurrence_comparison_vector_present": False,
            "campaign_closure_issued": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_execution_allowed": False,
            "next_required_action": (
                "SUPERVISE_SHARED_RESOURCES_AND_MATERIALIZE_OCCURRENCE_VECTOR"
            ),
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("query-bound accounted continuation changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "stage_accounting": self.accounting.to_document(),
            "direct_ground_fallback": self.direct_fallback.to_document(),
            "query_bound_accounted_continuation_id": self.result_id,
        }


def run_query_bound_accounted_continuation_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
    root_query_result_bytes: bytes,
    overlay_bytes: bytes,
    request_bytes: bytes,
) -> QueryBoundAccountedContinuationV1:
    """Run the two-transaction recovery loop and exact fallback once."""

    initial_request = request_v1.verify_query_bound_recovery_request_bytes_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
        root_query_result_bytes=root_query_result_bytes,
        overlay_bytes=overlay_bytes,
        request_bytes=request_bytes,
    )
    transaction_1_preparation = ground_v1.prepare_query_bound_ground_transaction_v1(
        source_trace_bytes=source_trace_bytes,
        request=initial_request,
    )
    with accounting_v1.activate_query_bound_stage_accounting_v1(
        occurrence_id=initial_request.logical_occurrence_id
    ) as accounting:
        accounting.enter_stage(_S.OPEN_INCREMENTAL_ACQUISITION)
        transaction_1 = ground_v1.execute_prepared_query_bound_ground_transaction_v1(
            transaction_1_preparation,
        )
        accounting.exit_stage(
            _S.OPEN_INCREMENTAL_ACQUISITION,
            output_bindings=(("GROUND_TRANSACTION_1", transaction_1.transaction_id),),
        )

        accounting.enter_stage(_S.OPEN_CHECKPOINT_REPLANNING)
        replanning_1 = replan_v1.compile_and_replan_query_bound_ground_transaction_v1(
            source_trace_bytes=source_trace_bytes,
            transaction=transaction_1,
        )
        request_2 = request2_v1.prepare_second_query_bound_recovery_request_v1(
            replanning_1
        )
        accounting.exit_stage(
            _S.OPEN_CHECKPOINT_REPLANNING,
            output_bindings=(
                ("REPLANNING_1", replanning_1.result_id),
                ("RECOVERY_REQUEST_2", request_2.request_id),
            ),
        )

        accounting.enter_stage(_S.OPEN_INCREMENTAL_ACQUISITION)
        transaction_2 = ground2_v1.execute_second_query_bound_ground_transaction_v1(
            predecessor=replanning_1,
            request=request_2,
        )
        accounting.exit_stage(
            _S.OPEN_INCREMENTAL_ACQUISITION,
            output_bindings=(("GROUND_TRANSACTION_2", transaction_2.transaction_id),),
        )

        accounting.enter_stage(_S.OPEN_CHECKPOINT_REPLANNING)
        final_local = final_v1.compile_and_replan_final_local_transaction_v1(
            transaction_2
        )
        accounting.exit_stage(
            _S.OPEN_CHECKPOINT_REPLANNING,
            output_bindings=(("FINAL_LOCAL_REPLANNING", final_local.result_id),),
        )

        accounting.enter_stage(_S.DIRECT_FALLBACK)
        direct = fallback_v1.execute_query_bound_direct_ground_fallback_v1(
            final_local
        )
        accounting.exit_stage(
            _S.DIRECT_FALLBACK,
            output_bindings=(("DIRECT_GROUND_FALLBACK", direct.result_id),),
        )
        stage_result = accounting.complete_occurrence()

    return QueryBoundAccountedContinuationV1(
        _ISSUER,
        transaction_1,
        replanning_1,
        request_2,
        transaction_2,
        final_local,
        direct,
        stage_result,
    )


def verify_query_bound_accounted_continuation_v1(
    claimed: QueryBoundAccountedContinuationV1,
) -> QueryBoundAccountedContinuationV1:
    if type(claimed) is not QueryBoundAccountedContinuationV1:
        _fail("query-bound accounted continuation has a foreign type")
    claimed.__post_init__(_ISSUER)
    fallback_v1.verify_query_bound_direct_ground_fallback_v1(
        claimed.direct_fallback
    )
    return claimed


__all__ = (
    "ConstructionK7QueryBoundAccountedContinuationV1Error",
    "LOCAL_DOMAINS",
    "QueryBoundAccountedContinuationV1",
    "run_query_bound_accounted_continuation_v1",
    "verify_query_bound_accounted_continuation_v1",
)
