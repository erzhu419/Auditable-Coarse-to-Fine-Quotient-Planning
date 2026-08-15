from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_generic_bytecode_campaign_v47r1 as campaign
from acfqp import construction_k7_generic_bytecode_independent_verifier_v47r1 as verifier
from acfqp import construction_k7_generic_bytecode_successor_preregistration_v47r1 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


@pytest.fixture(scope="module")
def campaign_bytes() -> bytes:
    return campaign.freeze_generic_bytecode_campaign_v47r1().canonical_bytes


def _resign(document: dict) -> bytes:
    payload = {key: value for key, value in document.items() if key != "generic_cross_domain_campaign_id"}
    document["generic_cross_domain_campaign_id"] = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    return canonical_json_bytes(document)


def test_v47r1_producer_free_verification_is_frozen(campaign_bytes) -> None:
    raw = verifier.freeze_generic_bytecode_verification_v47r1(campaign_bytes)
    document = loads_canonical_json(raw)
    assert document["generic_cross_domain_verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["programs_reconstructed_from_raw_observations"] is True
    assert document["target_bindings_and_plans_reconstructed"] is True
    assert document["accounting_reconstructed"] is True
    assert document["registered_label_saving"] == 900
    assert document["producer_module_imported"] is False


def test_v47r1_verifier_imports_no_campaign_producer() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("generic_bytecode_campaign_v47r1" in name for name in imported)


@pytest.mark.parametrize(
    "attack",
    [
        "unknown_top",
        "program",
        "support",
        "partial",
        "ood",
        "accounting",
        "official",
    ],
)
def test_v47r1_independent_verifier_rejects_fully_resigned_attacks(
    campaign_bytes, attack
) -> None:
    document = loads_canonical_json(campaign_bytes)
    if attack == "unknown_top":
        document["forged"] = True
    elif attack == "program":
        document["programs"][0]["compiled_bytecode"][0].append("FORGED")
        program_payload = {
            key: value
            for key, value in document["programs"][0].items()
            if key != "program_id"
        }
        document["programs"][0]["program_id"] = content_id(
            pre.FUTURE_DOMAINS["program"], program_payload
        )
    elif attack == "support":
        document["dependency_support_signatures"][0]["predeclared_semantic_support_names"] = ["FORGED"]
        support_payload = {
            key: value
            for key, value in document["dependency_support_signatures"][0].items()
            if key != "support_signature_id"
        }
        document["dependency_support_signatures"][0]["support_signature_id"] = content_id(
            pre.FUTURE_DOMAINS["distinction"], support_payload
        )
    elif attack == "partial":
        document["stochastic_partial_model"]["exact_probability_authority"] = True
        partial_payload = {
            key: value
            for key, value in document["stochastic_partial_model"].items()
            if key != "partial_model_id"
        }
        document["stochastic_partial_model"]["partial_model_id"] = content_id(
            pre.FUTURE_DOMAINS["stochastic"], partial_payload
        )
    elif attack == "ood":
        document["strict_ood_control"]["environment_outcome_count"] = 1
    elif attack == "accounting":
        document["accounting_axes"]["offline_source_labels"] += 1
    elif attack == "official":
        document["official_execution_allowed"] = True
    with pytest.raises(verifier.ConstructionK7GenericBytecodeIndependentVerifierV47R1Error):
        verifier.verify_generic_bytecode_campaign_bytes_v47r1(_resign(document))
