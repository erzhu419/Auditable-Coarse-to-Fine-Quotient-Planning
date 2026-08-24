from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_full_ground_fallback_execution_authorization_evidence_freeze_v180r7r1
    as evidence,
)


def test_post_prereg_evidence_stub_has_exact_cycle_free_boundary() -> None:
    assert evidence.AUTHORIZATION_EVIDENCE_DOMAIN == (
        "acfqp:construction-k7-full-ground-fallback-execution-authorization-"
        "evidence:v180r7r1p"
    )
    assert evidence.SOURCE_FACT_EXCLUSIONS == tuple(
        sorted(
            (
                (
                    "src/acfqp/construction_k7_full_ground_fallback_execution_"
                    "authorization_evidence_freeze_v180r7r1.py"
                ),
                (
                    "src/acfqp/construction_k7_full_ground_fallback_execution_"
                    "authorization_v180r7r1.py"
                ),
            )
        )
    )
    assert evidence.EXPECTED_AUTHORIZATION_EVIDENCE_ID == "0" * 64
    assert evidence.EXPECTED_AUTHORIZATION_ID == "0" * 64
    assert evidence.EXPECTED_CANONICAL_BYTE_COUNT == 0
    assert evidence.EXPECTED_CANONICAL_SHA256 == "0" * 64
    assert evidence.AUTHORIZATION_EVIDENCE_FIELDS == {
        "BREAK_EVEN_GATE",
        "COUNTER_COMPLETENESS_GATE",
        "SCALAR_CALIBRATION_GATE",
        "WORKLOAD_ECONOMICS_GATE",
        "authorization_canonical_byte_count",
        "authorization_canonical_sha256",
        "authorization_evidence_domain",
        "authorization_evidence_id",
        "authorization_preregistered_before_this_evidence",
        "authorization_self_source_bound_by_this_evidence",
        "authorization_source_fact",
        "evidence_wrapper_self_source_excluded_to_avoid_identity_cycle",
        "execution_chain_source_facts",
        "fallback_execution_authorization_id",
        "fallback_execution_protocol_id",
        "fresh_production_occurrence_count",
        "official_N_break_even",
        "official_execution_allowed",
        "official_scalar_cost",
        "outcome_free",
        "production_outcome_accessed",
        "schema",
        "source_fact_exclusions",
    }


def test_post_prereg_evidence_stub_fails_closed_before_freeze() -> None:
    freeze_evidence = (
        evidence
        .freeze_full_ground_fallback_execution_authorization_evidence_v180r7r1
    )
    freeze_evidence.cache_clear()
    with pytest.raises(
        evidence.FullGroundFallbackAuthorizationEvidenceV180r7r1Error,
        match="constants are not frozen",
    ):
        freeze_evidence()


def test_runners_are_prewired_before_any_outcome_access() -> None:
    root = Path(__file__).resolve().parents[1]
    production = ast.parse(
        (
            root / "scripts/run_v180r7r1_full_ground_fallback_occurrence.py"
        ).read_bytes()
    )
    production_main = next(
        node
        for node in production.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    first = production_main.body[0]
    assert isinstance(first, ast.Assign)
    assert isinstance(first.value, ast.Call)
    assert isinstance(first.value.func, ast.Attribute)
    assert first.value.func.attr == (
        "freeze_full_ground_fallback_execution_authorization_"
        "evidence_v180r7r1"
    )

    verification = ast.parse(
        (
            root / "scripts/verify_v180r7r1_full_ground_fallback_occurrence.py"
        ).read_bytes()
    )
    verification_main = next(
        node
        for node in verification.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    first = verification_main.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Call)
    assert isinstance(first.value.func, ast.Name)
    assert first.value.func.id == "_freeze_authorization_boundary"
