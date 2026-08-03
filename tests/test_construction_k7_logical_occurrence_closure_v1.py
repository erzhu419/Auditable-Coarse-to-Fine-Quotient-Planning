from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

import pytest

from acfqp import campaign_v1
from acfqp import construction_k7_logical_occurrence_closure_v1 as closure_v1
from acfqp import (
    construction_k7_production_complete_bundle_independent_verifier_v1
    as complete_verifier_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json
from tests.test_construction_k7_root_cap_terminal_authority_v1 import terminal_case


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _rehash_outer(document: dict[str, Any]) -> bytes:
    result = deepcopy(document)
    payload = dict(result)
    payload.pop("logical_occurrence_closure_bundle_id", None)
    result["logical_occurrence_closure_bundle_id"] = closure_v1._local_id(  # noqa: SLF001
        closure_v1.K7_LOGICAL_OCCURRENCE_CLOSURE_BUNDLE_V1_DOMAIN,
        payload,
    )
    return canonical_json_bytes(result)


@pytest.fixture(scope="module")
def occurrence_closure_case(terminal_case):
    inputs, semantic_closure, formal, terminal_bundle = terminal_case
    complete_verification = (
        complete_verifier_v1
        .verify_k7_production_complete_bundle_independently_v1(
            semantic_closure_raw=semantic_closure.canonical_bytes,
            formal_materialization_raw=formal.canonical_bytes,
            terminal_accounting_bundle_raw=terminal_bundle.canonical_bytes,
            closure_replay_inputs=inputs,
        )
    )
    route = inputs["replay_roots"]["request_replay"].request.route_identity
    bundle = closure_v1.issue_k7_logical_occurrence_closure_bundle_v1(
        complete_bundle_verification=complete_verification,
        terminal_accounting_bundle_raw=terminal_bundle.canonical_bytes,
        request_route_identity=route,
        rebuild_policy=campaign_v1.RebuildPolicyV1(),
    )
    return (
        inputs,
        semantic_closure,
        formal,
        terminal_bundle,
        complete_verification,
        route,
        bundle,
    )


def test_id_only_closure_is_rejected_before_production_replay() -> None:
    with pytest.raises(
        closure_v1.ConstructionK7LogicalOccurrenceClosureV1Error,
        match="production complete bundle failed independent replay",
    ):
        closure_v1.verify_k7_logical_occurrence_closure_bundle_bytes_v1(
            raw=canonical_json_bytes(
                {"logical_occurrence_closure_bundle_id": _id("id-only")}
            ),
            complete_bundle_verification_raw=canonical_json_bytes(
                {"production_complete_bundle_verification_id": _id("verification")}
            ),
            semantic_closure_raw=b"{}",
            formal_materialization_raw=b"{}",
            terminal_accounting_bundle_raw=b"{}",
            closure_replay_inputs={},
        )


def test_closure_authority_cannot_be_caller_minted() -> None:
    with pytest.raises(
        closure_v1.ConstructionK7LogicalOccurrenceClosureV1Error,
        match="caller-minted",
    ):
        closure_v1.K7LogicalOccurrenceClosureV1(
            object(),
            *(_id(f"forged-{index}") for index in range(12)),
        )


def test_nonretryable_occurrence_closure_preserves_all_work_and_denominators(
    occurrence_closure_case,
) -> None:
    (
        inputs,
        semantic_closure,
        formal,
        terminal_bundle,
        complete_verification,
        _route,
        bundle,
    ) = occurrence_closure_case
    document = bundle.to_document()
    work_sum = bundle.occurrence_work_sum
    closure = bundle.occurrence_closure

    assert len(work_sum.counter_record_ids) == 202
    assert work_sum.counter_record_ids == tuple(
        row.record_id for row in formal.work_vector.records
    )
    assert work_sum.work_vector is complete_verification.verified_work_vector
    assert work_sum.comparison_vector is complete_verification.verified_comparison_vector
    assert work_sum.aggregate_values == formal.comparison_vector.values
    assert closure.logical_occurrence_id == formal.work_vector.subject_id
    assert closure.rebuild_policy_id == campaign_v1.RebuildPolicyV1().rebuild_policy_id
    assert document["logical_occurrence_closure"]["route_attempt_count"] == 1
    assert document["logical_occurrence_closure"]["rebuild_count"] == 0
    assert document["logical_occurrence_closure"]["terminal_class"] == (
        "ATTEMPT_CLOSURE_NONCERTIFICATE"
    )
    assert document["logical_occurrence_closure"]["terminal_code"] == (
        "ATTEMPT_BUDGET_EXHAUSTED"
    )
    assert document["logical_occurrence_closure"]["certificate_covered"] is False
    assert (
        document["logical_occurrence_closure"]["closure_denominator_included"]
        is True
    )
    assert (
        document["logical_occurrence_closure"][
            "certification_denominator_included"
        ]
        is True
    )
    assert (
        document["logical_occurrence_closure"]["economics_denominator_included"]
        is True
    )
    assert document["logical_occurrence_closure"]["closure_denominator_count"] == 1
    assert (
        document["logical_occurrence_closure"]
        ["certification_coverage_denominator_count"]
        == 1
    )
    assert (
        document["logical_occurrence_closure"]["economics_cost_denominator_count"]
        == 1
    )
    assert document["logical_occurrence_closure"]["plan_certificate_count"] == 0
    assert (
        document["logical_occurrence_closure"]["infeasibility_certificate_count"]
        == 0
    )
    assert document["logical_occurrence_closure"]["noncertificate_count"] == 1
    assert document["campaign_closure_issued"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None

    replayed = closure_v1.verify_k7_logical_occurrence_closure_bundle_bytes_v1(
        raw=bundle.canonical_bytes,
        complete_bundle_verification_raw=complete_verification.canonical_bytes,
        semantic_closure_raw=semantic_closure.canonical_bytes,
        formal_materialization_raw=formal.canonical_bytes,
        terminal_accounting_bundle_raw=terminal_bundle.canonical_bytes,
        closure_replay_inputs=inputs,
    )
    assert replayed.verified_bundle.to_document() == document
    assert replayed.to_document()["all_202_records_and_provenance_replayed"] is True
    assert replayed.to_document()["three_denominators_replayed"] is True


def test_retryable_or_arbitrary_rebuild_policy_is_rejected(
    occurrence_closure_case,
) -> None:
    (
        _inputs,
        _semantic_closure,
        _formal,
        terminal_bundle,
        complete_verification,
        route,
        _bundle,
    ) = occurrence_closure_case
    with pytest.raises(
        closure_v1.ConstructionK7LogicalOccurrenceClosureV1Error,
        match="canonical non-retryable policy",
    ):
        closure_v1.issue_k7_logical_occurrence_closure_bundle_v1(
            complete_bundle_verification=complete_verification,
            terminal_accounting_bundle_raw=terminal_bundle.canonical_bytes,
            request_route_identity=route,
            rebuild_policy=campaign_v1.RebuildPolicyV1.allowing_one(
                _id("registered-rebuild-recipe")
            ),
        )


def test_hidden_terminal_work_cannot_be_joined_to_genuine_verification(
    occurrence_closure_case,
) -> None:
    (
        _inputs,
        _semantic_closure,
        _formal,
        terminal_bundle,
        complete_verification,
        route,
        _bundle,
    ) = occurrence_closure_case
    document = terminal_bundle.to_document()
    document["formal_accounting_materialization_bundle"]["work_vector"][
        "records"
    ].pop()
    with pytest.raises(
        closure_v1.ConstructionK7LogicalOccurrenceClosureV1Error,
        match="terminal bytes do not match",
    ):
        closure_v1.issue_k7_logical_occurrence_closure_bundle_v1(
            complete_bundle_verification=complete_verification,
            terminal_accounting_bundle_raw=canonical_json_bytes(document),
            request_route_identity=route,
            rebuild_policy=campaign_v1.RebuildPolicyV1(),
        )


@pytest.mark.parametrize(
    "attack",
    [
        "arbitrary_policy_id",
        "retryable_policy",
        "attempt_transplant",
        "hidden_work",
        "cap_to_infeasible",
        "closure_denominator_deleted",
        "certification_denominator_deleted",
        "economics_denominator_deleted",
        "certificate_covered",
    ],
)
def test_portable_closure_attack_is_rejected_without_repeating_root_replay(
    occurrence_closure_case,
    attack: str,
) -> None:
    (
        _inputs,
        _semantic_closure,
        _formal,
        terminal_bundle,
        complete_verification,
        route,
        bundle,
    ) = occurrence_closure_case
    document = bundle.to_document()
    closure = document["logical_occurrence_closure"]
    work_sum = document["logical_occurrence_work_sum"]
    if attack == "arbitrary_policy_id":
        document["rebuild_policy"]["rebuild_policy_id"] = _id("arbitrary-policy")
    elif attack == "retryable_policy":
        document["rebuild_policy"] = campaign_v1.RebuildPolicyV1.allowing_one(
            _id("retry-recipe")
        ).to_dict()
    elif attack == "attempt_transplant":
        closure["route_attempts"][0]["route_attempt_id"] = _id(
            "transplanted-attempt"
        )
    elif attack == "hidden_work":
        work_sum["counter_record_ids"].pop()
        work_sum["counter_record_count"] -= 1
    elif attack == "cap_to_infeasible":
        closure["terminal_class"] = "INFEASIBILITY_CERTIFICATE"
        closure["terminal_code"] = "FULL_GROUND_EXACT_INFEASIBLE"
        closure["infeasibility_certificate"] = True
    elif attack == "closure_denominator_deleted":
        closure["closure_denominator_included"] = False
        closure["closure_denominator_count"] = 0
    elif attack == "certification_denominator_deleted":
        closure["certification_denominator_included"] = False
        closure["certification_coverage_denominator_count"] = 0
    elif attack == "economics_denominator_deleted":
        closure["economics_denominator_included"] = False
        closure["economics_cost_denominator_count"] = 0
    elif attack == "certificate_covered":
        closure["certificate_covered"] = True
        closure["plan_certificate_count"] = 1
        closure["noncertificate_count"] = 0
    else:  # pragma: no cover
        raise AssertionError(attack)

    with pytest.raises(
        closure_v1.ConstructionK7LogicalOccurrenceClosureV1Error,
        match="differs from verified roots",
    ):
        closure_v1.verify_k7_logical_occurrence_closure_claim_bytes_v1(
            raw=_rehash_outer(document),
            complete_bundle_verification=complete_verification,
            terminal_accounting_bundle_raw=terminal_bundle.canonical_bytes,
            request_route_identity=route,
            rebuild_policy=campaign_v1.RebuildPolicyV1(),
        )


def test_portable_closure_is_strict_canonical_json(occurrence_closure_case) -> None:
    *_, terminal_bundle, complete_verification, route, bundle = occurrence_closure_case
    assert loads_canonical_json(bundle.canonical_bytes) == bundle.to_document()
    with pytest.raises(
        closure_v1.ConstructionK7LogicalOccurrenceClosureV1Error,
        match="noncanonical",
    ):
        closure_v1.verify_k7_logical_occurrence_closure_claim_bytes_v1(
            raw=bundle.canonical_bytes + b" ",
            complete_bundle_verification=complete_verification,
            terminal_accounting_bundle_raw=terminal_bundle.canonical_bytes,
            request_route_identity=route,
            rebuild_policy=campaign_v1.RebuildPolicyV1(),
        )
