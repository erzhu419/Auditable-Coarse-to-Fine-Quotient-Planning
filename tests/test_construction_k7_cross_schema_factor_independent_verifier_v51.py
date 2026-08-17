from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_cross_schema_factor_campaign_v51 as campaign
from acfqp import construction_k7_cross_schema_factor_independent_verifier_v51 as verifier
from acfqp import construction_k7_cross_schema_factor_preregistration_v51 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


@pytest.fixture(scope="module")
def campaign_bytes() -> bytes:
    return campaign.run_cross_schema_factor_campaign_v51().canonical_bytes


@pytest.fixture(scope="module")
def verification_document(campaign_bytes) -> dict:
    raw = verifier.freeze_cross_schema_factor_verification_v51(campaign_bytes)
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    return loads_canonical_json(raw)


def test_v51_producer_free_verification_is_frozen(verification_document) -> None:
    document = verification_document
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["predecessor_source_model_count"] == 2
    assert document["cross_schema_library_subprogram_count"] == 3
    assert document["target_reused_factor_count"] == 5
    assert document["new_domain_source_labels"] == 213
    assert document["structural_target_labels"] == 28
    assert document["strict_target_labels"] == 235
    assert document["cumulative_label_reduction"] == 154
    assert document["producer_or_campaign_core_module_imported"] is False


def test_v51_verifier_imports_neither_campaign_producer_nor_core() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("cross_schema_factor_campaign_v51" in name for name in imported)
    assert not any("cross_schema_factor_campaign_core_v51" in name for name in imported)
    assert not any("layout_factorization_campaign_v50r1" in name for name in imported)


@pytest.mark.parametrize(
    "attack",
    [
        "source",
        "library",
        "model",
        "calibration",
        "certificate",
        "distinction",
        "episode",
        "sample_tax",
        "accounting",
        "ood",
        "official",
    ],
)
def test_v51_independent_verifier_rejects_resigned_attacks(
    campaign_bytes, attack
) -> None:
    document = loads_canonical_json(campaign_bytes)
    if attack == "source":
        document["source_archives"][0]["raw_transitions"][0]["post_vector"][0] += 1
    elif attack == "library":
        document["inherited_factor_library"]["cross_schema_subprograms"][0][
            "origin_count"
        ] += 1
    elif attack == "model":
        document["higher_order_partial_stochastic_world_model"][
            "factor_composed_model"
        ]["reused_factor_count"] += 1
    elif attack == "calibration":
        document["target_layout_calibrations"][0]["support_labels"] += 1
    elif attack == "certificate":
        document["failed_certificates"][0][
            "ground_query_performed_before_failure"
        ] = True
    elif attack == "distinction":
        document["local_distinctions"][0]["relation_output"] += 1
    elif attack == "episode":
        document["structural_episodes"][0]["action_keys"][0] += 1
    elif attack == "sample_tax":
        document["sample_tax"]["cumulative_label_reduction"] += 1
    elif attack == "accounting":
        document["accounting"]["factor_boundary_compute_events"] += 1
    elif attack == "ood":
        document["ood_rejection"]["prior_transfer_attempted"] = True
    elif attack == "official":
        document["official_execution_allowed"] = True
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    with pytest.raises(
        verifier.ConstructionK7CrossSchemaFactorIndependentVerifierV51Error
    ):
        verifier.verify_cross_schema_factor_campaign_bytes_v51(
            canonical_json_bytes(document)
        )
