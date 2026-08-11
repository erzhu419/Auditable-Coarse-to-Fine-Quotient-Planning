from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_positive_promoted_overlay_independent_verifier_v1 as verifier
from acfqp import construction_k7_positive_promoted_overlay_v1 as producer
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, canonical_json_bytes
from tests.test_construction_k7_positive_promoted_overlay_v1 import (
    positive_promoted,
)
from tests.test_v075_batched_causal_occurrence_successor_v1 import (
    positive_batched_occurrence,
)


def test_independent_surface_and_import_boundary_are_narrow() -> None:
    assert verifier.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(verifier.LOCAL_DOMAINS) == 1
    assert set(verifier.__all__) == {
        "ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error",
        "LOCAL_DOMAINS",
        "PositivePromotedOverlayIndependentVerificationV1",
        "verify_positive_promoted_overlay_bytes_independently_v1",
    }
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    assert not any(
        "construction_k7_positive_promoted_overlay_v1" in item
        for item in imported
    )


@pytest.fixture(scope="module")
def independent_positive(positive_promoted):
    source, lineage, exact_replay, source_verification, result = positive_promoted
    verification = (
        verifier.verify_positive_promoted_overlay_bytes_independently_v1(
            source=source,
            lineage=lineage,
            exact_replay=exact_replay,
            source_verification=source_verification,
            result_bytes=canonical_json_bytes(result.to_document()),
        )
    )
    return positive_promoted, verification


def test_independent_replay_closes_projection_plan_and_exact_lift(
    independent_positive,
) -> None:
    values, verification = independent_positive
    result = values[-1]
    document = verification.to_document()
    assert document["positive_promoted_overlay_result_id"] == result.result_id
    assert document["promoted_numerical_model_id"] == result.epoch.model.model_id
    assert document["fresh_numerical_proof_id"] == result.plan.proof.proof_id
    assert document["fresh_policy_id"] == result.plan.proof.policy.policy_id
    assert document["fresh_selected_expected_reward"] == {
        "numerator": 3,
        "denominator": 64,
    }
    assert document["fresh_selected_failure_probability"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert document["fresh_exact_normalized_regret"] == {
        "numerator": 0,
        "denominator": 1,
    }
    assert document["v1_to_v2_projection_independently_replayed"] is True
    assert document["fresh_abstract_planner_independently_replayed"] is True
    assert document["fresh_policy_exact_lift_independently_recomputed"] is True
    assert document["producer_module_imported"] is False
    assert document["operational_new_ground_draw_count"] == 0
    assert document["construction_scope_plan_certificate_verified"] is True
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["official_execution_allowed"] is False
    assert document["valid"] is True


def test_independent_replay_does_not_call_positive_producer(
    independent_positive,
    monkeypatch,
) -> None:
    values, prior = independent_positive
    source, lineage, exact_replay, source_verification, result = values

    def forbidden(*_args, **_kwargs):
        raise AssertionError("independent verifier called the producer")

    monkeypatch.setattr(producer, "run_positive_promoted_overlay_v1", forbidden)
    replayed = verifier.verify_positive_promoted_overlay_bytes_independently_v1(
        source=source,
        lineage=lineage,
        exact_replay=exact_replay,
        source_verification=source_verification,
        result_bytes=canonical_json_bytes(result.to_document()),
    )
    assert replayed.verification_id == prior.verification_id


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("official_execution_allowed", True),
        ("scientific_endpoint_credit_allowed", True),
        ("fresh_occurrence_new_ground_draw_count", 1),
        ("counter_completeness_gate_status", "PASSED"),
    ),
)
def test_outer_claim_flip_is_rejected_before_authority_replay(
    positive_promoted,
    monkeypatch,
    field,
    replacement,
) -> None:
    source, lineage, exact_replay, source_verification, result = positive_promoted
    document = result.to_document()
    document[field] = replacement

    def forbidden(*_args, **_kwargs):
        raise AssertionError("cheap claim gate ran expensive source replay")

    monkeypatch.setattr(
        verifier.successor_v1,
        "verify_v075_batched_causal_occurrence_successor_v1",
        forbidden,
    )
    with pytest.raises(
        verifier.ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error,
        match="claim locks",
    ):
        verifier.verify_positive_promoted_overlay_bytes_independently_v1(
            source=source,
            lineage=lineage,
            exact_replay=exact_replay,
            source_verification=source_verification,
            result_bytes=canonical_json_bytes(document),
        )


def test_nested_operational_or_projection_tampering_is_rejected(
    positive_promoted,
) -> None:
    source, lineage, exact_replay, source_verification, result = positive_promoted
    document = result.to_document()
    document["fresh_abstract_plan"]["operational_new_ground_draw_count"] = 1
    with pytest.raises(
        verifier.ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error,
        match="differ",
    ):
        verifier.verify_positive_promoted_overlay_bytes_independently_v1(
            source=source,
            lineage=lineage,
            exact_replay=exact_replay,
            source_verification=source_verification,
            result_bytes=canonical_json_bytes(document),
        )


def test_noncanonical_bytes_are_rejected(positive_promoted) -> None:
    source, lineage, exact_replay, source_verification, result = positive_promoted
    raw = canonical_json_bytes(result.to_document()) + b"\n"
    with pytest.raises(
        verifier.ConstructionK7PositivePromotedOverlayIndependentVerifierV1Error,
        match="canonical",
    ):
        verifier.verify_positive_promoted_overlay_bytes_independently_v1(
            source=source,
            lineage=lineage,
            exact_replay=exact_replay,
            source_verification=source_verification,
            result_bytes=raw,
        )
