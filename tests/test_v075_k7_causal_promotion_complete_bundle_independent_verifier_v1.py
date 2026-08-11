from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from acfqp import v075_k7_causal_promotion_complete_bundle_independent_verifier_v1 as subject


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_independent_verifier_domains_and_claims_are_bounded() -> None:
    assert {
        subject.VERIFICATION_PROFILE_DOMAIN,
        subject.SEMANTIC_VERIFIER_DOMAIN,
        subject.VERIFICATION_DOMAIN,
    }.issubset(PHASE3E_DOMAIN_TAGS)
    profile = subject._verification_profile_payload()  # noqa: SLF001
    assert profile["worker_reexecution_allowed"] is False
    assert profile["producer_renderer_import_allowed"] is False
    assert profile["evaluation_lane_only"] is True
    assert profile["official_execution_allowed"] is False


def test_independent_verifier_has_no_causal_producer_import() -> None:
    path = (
        REPOSITORY_ROOT
        / "src/acfqp/v075_k7_causal_promotion_complete_bundle_independent_verifier_v1.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(
                f"{node.module}.{alias.name}"
                for alias in node.names
                if node.module
            )
    forbidden = {
        "acfqp.v075_k7_causal_promotion_construction_fixture_v1",
        "acfqp.v075_k7_causal_promotion_accounted_runtime_v1",
        "acfqp.v075_k7_causal_promotion_accounted_executor_v1",
        "acfqp.v075_k7_causal_promotion_occurrence_accounting_v1",
        "acfqp.v075_k7_causal_promotion_terminal_authority_v1",
    }
    assert imported.isdisjoint(forbidden)


def test_bytes_verifier_rejects_missing_or_reordered_roles() -> None:
    with pytest.raises(
        subject.V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error
    ):
        subject.verify_v075_k7_causal_promotion_complete_bundle_bytes_v1({})
    reordered = {role: b"{}" for role in reversed(subject.REQUIRED_ROLES)}
    with pytest.raises(
        subject.V075K7CausalPromotionCompleteBundleIndependentVerifierV1Error
    ):
        subject.verify_v075_k7_causal_promotion_complete_bundle_bytes_v1(
            reordered
        )
