from __future__ import annotations

import ast
from pathlib import Path

from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as subject


def test_public_surface_is_one_bytes_only_verifier() -> None:
    assert set(subject.__all__) == {
        "ConstructionK7QueryBoundCompleteBundleIndependentVerifierV1Error",
        "QueryBoundCompleteBundleVerificationV1",
        "verify_query_bound_complete_bundle_directory_v1",
    }
    assert subject._LOCAL_RECOVERY_PATH_PREFIXES == (
        "local.",
        "acquisition.",
        "build.",
    )


def test_verifier_source_does_not_import_any_bundle_producer() -> None:
    source_path = Path(subject.__file__).resolve()
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    forbidden = {
        "acfqp.construction_k7_query_bound_accounted_runtime_v1",
        "acfqp.construction_k7_query_bound_supervised_executor_v1",
        "acfqp.construction_k7_query_bound_occurrence_accounting_v1",
    }
    assert imported.isdisjoint(forbidden)


def test_verifier_result_is_issuer_only() -> None:
    try:
        subject.QueryBoundCompleteBundleVerificationV1(
            object(),
            "not-an-id",
            "not-an-id",
            "not-an-id",
            "not-an-id",
            "not-an-id",
            (),
            (),
            (),
            1,
            (),
        )
    except subject.ConstructionK7QueryBoundCompleteBundleIndependentVerifierV1Error:
        return
    raise AssertionError("caller-minted verification result was accepted")
