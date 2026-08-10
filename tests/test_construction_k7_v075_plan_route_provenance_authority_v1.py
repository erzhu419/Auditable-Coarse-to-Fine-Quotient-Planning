from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_v075_plan_route_provenance_authority_v1 as provenance_v1
from acfqp import v075_production_occurrence_authority_v1 as occurrence_v1
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes, content_id
from acfqp.routing_v1 import TerminalCode
from tests.test_v075_production_occurrence_authority_v1 import _open


ROOT = Path(__file__).resolve().parents[1]
RUN_REAL = os.environ.get("ACFQP_RUN_REAL_V075_ROUTE_PROVENANCE") == "1"


def test_three_route_provenance_domains_are_central_and_separated() -> None:
    assert len(provenance_v1.LOCAL_DOMAINS) == 3
    assert provenance_v1.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    payload = {"schema": "same-v075-route-provenance-payload"}
    assert len(
        {content_id(domain, payload) for domain in provenance_v1.LOCAL_DOMAINS}
    ) == 3


def test_route_mapping_is_explicit_and_never_promotes_direct_to_abstract() -> None:
    source = Path(provenance_v1.__file__).read_text(encoding="utf-8")
    assert "ADAPTIVE_QUOTIENT" in source
    assert "ABSTRACT_ONLY_CERTIFICATE" in source
    assert "MATCHED_DIRECT_GROUND" in source
    assert "DIRECT_FALLBACK" in source
    assert "terminal_artifact_issued\": False" in source
    assert "counter_records_issued\": 0" in source


@pytest.fixture(scope="module")
def positive_direct_case():
    if not RUN_REAL:
        pytest.skip("set ACFQP_RUN_REAL_V075_ROUTE_PROVENANCE=1")
    private_laws = tuple(((1, Fraction(1, 1)),) for _ in range(3))
    values = _open(
        "k7-route-provenance-positive-direct",
        scientific_ordinal=4,
        private_laws=private_laws,
    )
    result = occurrence_v1.execute_v075_construction_occurrence_fixture_v1(
        repository_root=ROOT,
        plan=values[1],
        entry=values[2],
        authority=values[3],
        private_environment=values[4],
        controller=values[5],
        ipc_profile=values[6],
    )
    binding = provenance_v1.issue_v075_plan_route_provenance_v1(
        repository_root=ROOT,
        namespace=values[0],
        occurrence_result=result,
    )
    return values, result, binding


def test_real_positive_direct_lift_selects_only_full_ground_fallback(
    positive_direct_case,
) -> None:
    _values, result, binding = positive_direct_case
    route = binding.provenance
    assert result.terminal_code is (
        occurrence_v1.V075ProductionOccurrenceTerminalCodeV1
        .EXACT_VALID_TOTAL_LIFT_PLAN_CERTIFICATE
    )
    assert route.route_kind is RouteKindEnum.DIRECT_FALLBACK
    assert route.quotient_id is None
    assert route.construction_fixture is True
    assert route.production_evidence is False
    assert binding.normalization_result.fq9_terminal_code is (
        TerminalCode.FULL_GROUND_FALLBACK
    )
    assert binding.normalization_result.fq9_terminal_code is not (
        TerminalCode.ABSTRACT_CERTIFIED
    )
    document = binding.to_document()
    assert document["normalization_only"] is True
    assert document["terminal_artifact_issued"] is False
    assert document["counter_records_issued"] == 0
    assert document["production_evidence"] is False


def test_real_positive_route_bytes_replay_without_host_search(
    positive_direct_case,
) -> None:
    values, result, binding = positive_direct_case
    replay = provenance_v1.verify_v075_plan_route_provenance_bytes_v1(
        binding.canonical_bytes,
        repository_root=ROOT,
        namespace=values[0],
        occurrence_result=result,
    )
    assert replay.outcome is (
        provenance_v1.V075PlanRouteProvenanceReplayOutcomeV1.VERIFIED
    )
    assert replay.route_normalization_binding_id == binding.binding_id
    assert replay.fq9_route_kind is RouteKindEnum.DIRECT_FALLBACK
    assert replay.selected_fq9_terminal_code is (
        TerminalCode.FULL_GROUND_FALLBACK
    )
    assert replay.blocker_codes == ()


def test_resigned_terminal_target_mutation_is_blocked(
    positive_direct_case,
) -> None:
    values, result, binding = positive_direct_case
    document = deepcopy(binding.to_document())
    document["selected_fq9_terminal_code"] = "ABSTRACT_CERTIFIED"
    payload = dict(document)
    payload.pop("route_normalization_binding_id")
    payload.pop("route_provenance")
    payload.pop("conditional_normalization_evidence")
    payload.pop("conditional_normalization_result")
    document["route_normalization_binding_id"] = content_id(
        provenance_v1.BINDING_DOMAIN,
        payload,
    )
    replay = provenance_v1.verify_v075_plan_route_provenance_bytes_v1(
        canonical_json_bytes(document),
        repository_root=ROOT,
        namespace=values[0],
        occurrence_result=result,
    )
    assert replay.outcome is (
        provenance_v1.V075PlanRouteProvenanceReplayOutcomeV1.DOCUMENT_BLOCKED
    )
    assert replay.route_normalization_binding_id is None


def test_caller_cannot_relabel_the_verified_planner_route(
    positive_direct_case,
) -> None:
    provenance = positive_direct_case[-1].provenance
    with pytest.raises(
        provenance_v1.ConstructionK7V075PlanRouteProvenanceV1Error
    ):
        replace(
            provenance,
            _issuer=object(),
            route_kind=RouteKindEnum.ABSTRACT_ONLY_CERTIFICATE,
        )

