from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_overlay_abstract_reuse_independent_verifier_v1 as verifier
from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as producer
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_RESULT_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def canonical_result():
    source = source_v1.run_heldout_checkpoint_recertification_v1()
    result = producer.run_heldout_overlay_abstract_reuse_v1(
        source,
        logical_occurrence_id=_id("heldout-independent-fresh-occurrence-v1"),
        occurrence_ordinal=3,
    )
    return result, canonical_json_bytes(result.to_document())


def _resign_top(document: dict[str, object]) -> None:
    payload = {
        key: value
        for key, value in document.items()
        if key
        not in {
            "source_result",
            "query",
            "plan",
            "final_quotient_model",
            "threshold",
            "result_id",
        }
    }
    document["result_id"] = content_id(
        CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_RESULT_V1_DOMAIN,
        payload,
    )


def test_independent_verifier_import_surface_excludes_both_producers() -> None:
    path = Path(verifier.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    assert not any("heldout_checkpoint_recertification" in name for name in imported)
    assert not any("heldout_overlay_abstract_reuse_v1" in name for name in imported)


def test_canonical_bytes_rebuild_model_and_replay_quotient_audit(
    canonical_result,
) -> None:
    result, raw = canonical_result
    replay = verifier.verify_heldout_overlay_abstract_reuse_bytes_v1(raw)
    document = replay.to_document()
    assert document["valid"] is True
    assert document["result_id"] == result.result_id
    assert document["source_result_id"] == result.source.result_id
    assert document["model_id"] == result.source.final_overlay.bridge.quotient_model.model_id
    assert document["audit_id"] == result.plan.audit.audit_id
    assert document["producer_import_count"] == 0
    assert document["independent_literal_model_rebuild"] is True
    assert document["independent_quotient_audit_replay"] is True
    assert document["new_ground_draw_count"] == 0


def test_verifier_does_not_call_monkeypatched_producer_verifiers(
    canonical_result,
    monkeypatch,
) -> None:
    _result, raw = canonical_result

    def forbidden(*_args, **_kwargs):
        raise AssertionError("producer verifier was called")

    monkeypatch.setattr(source_v1, "verify_heldout_checkpoint_recertification_v1", forbidden)
    monkeypatch.setattr(producer, "verify_heldout_overlay_abstract_reuse_v1", forbidden)
    assert verifier.verify_heldout_overlay_abstract_reuse_bytes_v1(raw).to_document()[
        "valid"
    ] is True


def test_fully_resigned_official_claim_flip_is_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    document["official_execution_allowed"] = True
    _resign_top(document)
    with pytest.raises(
        verifier.ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error
    ):
        verifier.verify_heldout_overlay_abstract_reuse_bytes_v1(
            canonical_json_bytes(document)
        )


def test_nested_audit_tamper_is_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    document["plan"]["audit"]["status"] = "FAILED_PROOF_FRONTIER"
    with pytest.raises(
        verifier.ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error
    ):
        verifier.verify_heldout_overlay_abstract_reuse_bytes_v1(
            canonical_json_bytes(document)
        )


def test_source_recovery_chain_tamper_is_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    document["source_result"]["transactions"][0]["delta"][
        "incremental_observer_draws"
    ] = 2_047
    with pytest.raises(
        verifier.ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error
    ):
        verifier.verify_heldout_overlay_abstract_reuse_bytes_v1(
            canonical_json_bytes(document)
        )


def test_noncanonical_json_is_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    with pytest.raises(
        verifier.ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error
    ):
        verifier.verify_heldout_overlay_abstract_reuse_bytes_v1(b" " + raw)
