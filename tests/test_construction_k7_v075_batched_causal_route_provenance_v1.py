from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from acfqp import construction_k7_v075_batched_causal_route_provenance_v1 as provenance
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, content_id
from acfqp.routing_v1 import TerminalClass, TerminalCode
from tests.test_v075_batched_causal_occurrence_successor_v1 import (
    positive_batched_occurrence,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def positive_route_binding(positive_batched_occurrence):
    result, values, sealed, lineage, exact_replay, lift_verification = (
        positive_batched_occurrence
    )
    binding = provenance.issue_v075_batched_causal_route_provenance_v1(
        repository_root=ROOT,
        namespace=values[0],
        plan=values[1],
        plan_entry=values[2],
        occurrence_result=result,
        sealed_lifecycle=sealed,
        lineage=lineage,
        exact_replay=exact_replay,
        total_lift_verification=lift_verification,
    )
    return result, values, binding


def test_domains_are_central_and_role_separated() -> None:
    domains = frozenset({provenance.PROVENANCE_DOMAIN, provenance.BINDING_DOMAIN})
    assert domains <= PHASE3E_DOMAIN_TAGS
    assert len({content_id(item, {"same": "payload"}) for item in domains}) == 2


def test_positive_batched_route_selects_abstract_certified_only(
    positive_route_binding,
) -> None:
    result, _values, binding = positive_route_binding
    route = binding.provenance
    assert route.planner_result_id == result.final_planner_result.result_id
    assert route.quotient_id == result.final_planner_result.quotient.quotient_id
    assert route.policy_id == result.final_planner_result.policy.policy_id
    assert route.selected_causal_candidate_count > 1
    assert route.materialized_child_row_count <= 19
    assert route.incremental_draw_count <= 160_960
    assert binding.normalization_evidence.route_kind is (
        RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE
    )
    assert binding.normalization_result.fq9_terminal_class is (
        TerminalClass.PLAN_CERTIFICATE
    )
    assert binding.normalization_result.fq9_terminal_code is (
        TerminalCode.ABSTRACT_CERTIFIED
    )


def test_positive_route_remains_construction_only_and_unaccounted(
    positive_route_binding,
) -> None:
    document = positive_route_binding[-1].to_document()
    route = document["route_provenance"]
    assert route["failed_proof_frontier_after_operator_count"] == 0
    assert route["observation_driven_quotient_present"] is True
    assert route["multi_step_contingent_policy_present"] is True
    assert route["exact_total_lift_chain_present"] is True
    assert route["production_evidence"] is False
    assert route["scientific_endpoint_credit_allowed"] is False
    assert route["terminal_artifact_issued"] is False
    assert route["counter_records_issued"] == 0
    assert route["work_vector_id"] is None
    assert route["comparison_vector_id"] is None
    assert route["official_execution_allowed"] is False
    assert route["counter_completeness_gate_status"] == (
        provenance.COUNTER_COMPLETENESS_GATE_STATUS
    )


def test_route_or_normalization_relabel_fails_closed(
    positive_route_binding,
) -> None:
    binding = positive_route_binding[-1]
    with pytest.raises(
        provenance.ConstructionK7V075BatchedCausalRouteProvenanceV1Error
    ):
        replace(
            binding.provenance,
            _issuer=object(),
            selected_causal_candidate_count=1,
        )
    with pytest.raises(
        provenance.ConstructionK7V075BatchedCausalRouteProvenanceV1Error
    ):
        replace(
            binding,
            _issuer=object(),
        )
