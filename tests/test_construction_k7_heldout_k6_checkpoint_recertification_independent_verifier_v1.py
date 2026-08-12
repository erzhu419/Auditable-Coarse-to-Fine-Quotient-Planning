from __future__ import annotations

import ast
from fractions import Fraction
from pathlib import Path

import pytest

from acfqp import construction_k7_heldout_k6_checkpoint_recertification_independent_verifier_v1 as verifier
from acfqp import construction_k7_heldout_k6_checkpoint_recertification_v1 as producer
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_K6_CAUSAL_ROW_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_EPOCH_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_RECOVERY_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_VALIDATION_DELTA_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


_TOP_NESTED = {
    "context", "coordinate_profile", "threshold", "base_quotient_model",
    "preregistration", "checkpoint", "causal_evidence", "request", "delta",
    "overlay", "result_id",
}


@pytest.fixture(scope="module")
def canonical_result():
    result = producer.run_heldout_k6_checkpoint_recertification_v1()
    return result, canonical_json_bytes(result.to_document())


def _resign(
    document: dict[str, object],
    *,
    domain: str,
    identity_key: str,
    nested: set[str] = frozenset(),
) -> None:
    payload = {
        key: value
        for key, value in document.items()
        if key != identity_key and key not in nested
    }
    document[identity_key] = content_id(domain, payload)


def _resign_top(document: dict[str, object]) -> None:
    _resign(
        document,
        domain=CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_RESULT_V1_DOMAIN,
        identity_key="result_id",
        nested=_TOP_NESTED - {"result_id"},
    )


def _resign_recovery_chain(document: dict[str, object]) -> None:
    evidence = document["causal_evidence"]
    request = document["request"]
    delta = document["delta"]
    overlay = document["overlay"]
    assert all(type(item) is dict for item in (evidence, request, delta, overlay))
    _resign(
        evidence,
        domain=CONSTRUCTION_K7_HELDOUT_K6_CAUSAL_ROW_EVIDENCE_V1_DOMAIN,
        identity_key="evidence_id",
    )
    document["causal_evidence_id"] = evidence["evidence_id"]
    request["causal_evidence_id"] = evidence["evidence_id"]
    _resign(
        request,
        domain=CONSTRUCTION_K7_HELDOUT_K6_RECOVERY_REQUEST_V1_DOMAIN,
        identity_key="request_id",
    )
    document["recovery_request_id"] = request["request_id"]
    delta["request_id"] = request["request_id"]
    _resign(
        delta,
        domain=CONSTRUCTION_K7_HELDOUT_K6_VALIDATION_DELTA_V1_DOMAIN,
        identity_key="delta_id",
    )
    document["validation_delta_id"] = delta["delta_id"]
    overlay["delta_id"] = delta["delta_id"]
    overlay["delta"] = delta
    _resign(
        overlay,
        domain=CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_EPOCH_V1_DOMAIN,
        identity_key="overlay_id",
        nested={"delta", "final_quotient_model", "audit"},
    )
    document["final_overlay_id"] = overlay["overlay_id"]
    _resign_top(document)


def test_import_surface_excludes_k6_checkpoint_producer() -> None:
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


def test_canonical_bytes_rebuild_base_failure_causal_screen_and_certificate(
    canonical_result,
) -> None:
    result, raw = canonical_result
    replay = verifier.verify_heldout_k6_checkpoint_recertification_bytes_v1(raw)
    document = replay.to_document()

    assert document["valid"] is True
    assert document["result_id"] == result.result_id
    assert document["base_model_id"] == result.base_bridge.quotient_model.model_id
    assert document["base_audit_id"] == result.base_audit.audit_id
    assert document["causal_evidence_id"] == result.causal_evidence.evidence_id
    assert document["final_model_id"] == result.overlay.bridge.quotient_model.model_id
    assert document["final_audit_id"] == result.overlay.audit.audit_id
    assert document["validated_coordinate_registry_count"] == 10
    assert document["replayed_causal_candidate_count"] == 20
    assert document["new_observer_draw_count"] == 0
    assert document["producer_import_count"] == 0
    assert document["independent_base_failure_replay"] is True
    assert document["independent_coordinate_candidate_model_replay"] is False
    assert document["physical_row_projection_independently_reconstructed"] is False
    assert document["independent_final_certificate_replay"] is True


def test_verifier_calls_neither_producer_verifier_nor_exact_access(
    canonical_result,
    monkeypatch,
) -> None:
    _result, raw = canonical_result

    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden producer or exact boundary was called")

    monkeypatch.setattr(
        producer, "verify_heldout_k6_checkpoint_recertification_v1", forbidden
    )
    monkeypatch.setattr(observer, "evaluation_exact_atoms_v1", forbidden)
    monkeypatch.setattr(observer, "evaluation_exact_ground_search_v1", forbidden)
    assert verifier.verify_heldout_k6_checkpoint_recertification_bytes_v1(
        raw
    ).to_document()["valid"] is True


def test_fully_resigned_official_claim_flip_is_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    document["official_execution_allowed"] = True
    _resign_top(document)
    with pytest.raises(
        verifier.ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error
    ):
        verifier.verify_heldout_k6_checkpoint_recertification_bytes_v1(
            canonical_json_bytes(document)
        )


def test_fully_resigned_causal_slack_tamper_is_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    evidence = document["causal_evidence"]
    candidate = evidence["candidates"][0]
    forged = candidate["minimum_certificate_slack"] + Fraction(1, 10_000)
    candidate["minimum_certificate_slack"] = forged
    evidence["selected_minimum_certificate_slack"] = forged
    _resign_recovery_chain(document)
    with pytest.raises(
        verifier.ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error
    ):
        verifier.verify_heldout_k6_checkpoint_recertification_bytes_v1(
            canonical_json_bytes(document)
        )


def test_nested_final_model_tamper_is_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    document["overlay"]["final_quotient_model"]["rows"][0]["reward_lower"] = (
        Fraction(1, 2)
    )
    with pytest.raises(
        verifier.ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error
    ):
        verifier.verify_heldout_k6_checkpoint_recertification_bytes_v1(
            canonical_json_bytes(document)
        )


def test_unknown_field_and_noncanonical_bytes_are_rejected(canonical_result) -> None:
    _result, raw = canonical_result
    document = loads_canonical_json(raw)
    assert type(document) is dict
    document["causal_evidence"]["unknown"] = True
    with pytest.raises(
        verifier.ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error
    ):
        verifier.verify_heldout_k6_checkpoint_recertification_bytes_v1(
            canonical_json_bytes(document)
        )
    with pytest.raises(
        verifier.ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error
    ):
        verifier.verify_heldout_k6_checkpoint_recertification_bytes_v1(b" " + raw)
