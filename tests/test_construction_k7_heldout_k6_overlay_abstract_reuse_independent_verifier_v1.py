from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_heldout_k6_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_k6_overlay_abstract_reuse_independent_verifier_v1 as verifier
from acfqp import construction_k7_heldout_k6_overlay_abstract_reuse_v1 as producer
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_RESULT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def canonical_result():
    source = source_v1.run_heldout_k6_checkpoint_recertification_v1()
    result = producer.run_heldout_k6_overlay_abstract_reuse_v1(
        source,
        logical_occurrence_id=_id("k6-independent-fresh-occurrence"),
        occurrence_ordinal=7,
    )
    return result, canonical_json_bytes(result.to_document())


def _resign_top(document: dict[str, object]) -> None:
    nested = {
        "source_result",
        "query",
        "plan",
        "final_quotient_model",
        "threshold",
        "result_id",
    }
    payload = {key: value for key, value in document.items() if key not in nested}
    document["result_id"] = content_id(
        CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_RESULT_V1_DOMAIN,
        payload,
    )


def test_import_surface_excludes_both_construction_producers() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    assert not any(
        name.endswith("construction_k7_heldout_k6_checkpoint_recertification_v1")
        for name in imported
    )
    assert not any(
        name.endswith("construction_k7_heldout_k6_overlay_abstract_reuse_v1")
        for name in imported
    )


def test_canonical_bytes_replay_source_model_query_and_plan(canonical_result) -> None:
    result, raw = canonical_result
    replay = verifier.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(raw)
    document = replay.to_document()
    assert document["valid"] is True
    assert document["result_id"] == result.result_id
    assert document["source_result_id"] == result.source.result_id
    assert document["query_id"] == result.query.query_id
    assert document["plan_id"] == result.plan.plan_id
    assert document["model_id"] == result.source.overlay.bridge.quotient_model.model_id
    assert document["audit_id"] == result.plan.audit.audit_id
    assert document["producer_import_count"] == 0
    assert document["source_recovery_independently_replayed"] is True
    assert document["independent_literal_model_rebuild"] is True
    assert document["independent_fresh_query_identity_replay"] is True
    assert document["independent_quotient_audit_replay"] is True


def test_independent_replay_preserves_zero_ground_fresh_occurrence(canonical_result) -> None:
    _result, raw = canonical_result
    document = verifier.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
        raw
    ).to_document()
    assert document["new_ground_draw_count"] == 0
    assert document["observer_call_count"] == 0
    assert document["model_build_invocations_in_fresh_occurrence"] == 0
    assert document["ground_solver_invocations"] == 0
    assert document["evaluation_exact_kernel_calls"] == 0


def test_verifier_does_not_call_same_implementation_producer_verifiers(
    canonical_result,
    monkeypatch,
) -> None:
    _result, raw = canonical_result

    def forbidden(*_args, **_kwargs):
        raise AssertionError("construction producer verifier was called")

    monkeypatch.setattr(
        source_v1, "verify_heldout_k6_checkpoint_recertification_v1", forbidden
    )
    monkeypatch.setattr(
        producer, "verify_heldout_k6_overlay_abstract_reuse_v1", forbidden
    )
    assert verifier.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
        raw
    ).to_document()["valid"] is True


def test_fully_resigned_official_claim_flip_is_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    document["official_execution_allowed"] = True
    _resign_top(document)
    with pytest.raises(
        verifier.ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error
    ):
        verifier.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
            canonical_json_bytes(document)
        )


def test_nested_audit_and_model_tampering_are_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    for path in ("audit", "model"):
        document = loads_canonical_json(raw)
        assert type(document) is dict
        if path == "audit":
            document["plan"]["audit"]["status"] = "FAILED_PROOF_FRONTIER"
        else:
            document["final_quotient_model"]["root_state_id"] = _id(
                "forged-root-state"
            )
        with pytest.raises(
            verifier.ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error
        ):
            verifier.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
                canonical_json_bytes(document)
            )


def test_source_recovery_tamper_is_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    document["source_result"]["delta"]["incremental_observer_draws"] = 8_191
    with pytest.raises(
        verifier.ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error
    ):
        verifier.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
            canonical_json_bytes(document)
        )


def test_unknown_field_and_noncanonical_json_are_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    document["unexpected"] = False
    _resign_top(document)
    with pytest.raises(
        verifier.ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error
    ):
        verifier.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
            canonical_json_bytes(document)
        )
    with pytest.raises(
        verifier.ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error
    ):
        verifier.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(b" " + raw)
