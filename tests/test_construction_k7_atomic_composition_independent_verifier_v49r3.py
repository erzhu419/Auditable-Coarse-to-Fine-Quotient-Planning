from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_atomic_composition_campaign_v49r3 as campaign
from acfqp import construction_k7_atomic_composition_independent_verifier_v49r3 as verifier
from acfqp import construction_k7_atomic_composition_preregistration_v49r3 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


@pytest.fixture(scope="module")
def campaign_bytes() -> bytes:
    return campaign.run_atomic_composition_campaign_v49r3().canonical_bytes


def _resign(document: dict) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "atomic_composition_campaign_id"
    }
    document["atomic_composition_campaign_id"] = content_id(
        pre.FUTURE_DOMAINS["campaign"], payload
    )
    return canonical_json_bytes(document)


def test_v49r3_producer_free_verification_is_frozen(campaign_bytes) -> None:
    raw = verifier.freeze_atomic_composition_verification_v49r3(campaign_bytes)
    document = loads_canonical_json(raw)
    assert document["atomic_composition_verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["source_support_labels"] == 209
    assert document["local_support_labels"] == 4
    assert document["strict_support_labels"] == 617
    assert document["registered_support_label_savings"] == 404
    assert document["structural_episode_count"] == 12
    assert document["ast_complete_transport_certificate_reconstructed"] is True
    assert document["local_relation_exemplars_and_overlay_reconstructed"] is True
    assert document["producer_module_imported"] is False


def test_v49r3_verifier_imports_no_campaign_producer() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("atomic_composition_campaign_v49r3" in name for name in imported)


@pytest.mark.parametrize(
    "attack",
    [
        "source",
        "program",
        "dependency",
        "certificate",
        "distinction",
        "episode",
        "sample",
        "accounting",
        "ood",
        "official",
    ],
)
def test_v49r3_independent_verifier_rejects_resigned_attacks(
    campaign_bytes, attack
) -> None:
    document = loads_canonical_json(campaign_bytes)
    if attack == "source":
        document["source_archives"][0]["raw_transitions"][0]["post_vector"][0] += 1
    elif attack == "program":
        document["compiled_program"]["specialized_discovery_pattern_count"] = 1
    elif attack == "dependency":
        document["dependency_support"]["predeclared_semantic_support_names"] = ["forged"]
    elif attack == "certificate":
        document["failed_certificates"][0]["changed_E00_columns"] = []
    elif attack == "distinction":
        document["local_distinctions"][0]["relation_output_value"] += 1
    elif attack == "episode":
        document["structural_episodes"][0]["action_keys"][0] += 1
    elif attack == "sample":
        document["sample_tax"]["registered_support_label_savings"] += 1
    elif attack == "accounting":
        document["accounting"]["structural_planning_compute_events"] += 1
    elif attack == "ood":
        document["ood_rejection"]["prior_transfer_attempted"] = True
    elif attack == "official":
        document["official_execution_allowed"] = True
    with pytest.raises(
        verifier.ConstructionK7AtomicCompositionIndependentVerifierV49R3Error
    ):
        verifier.verify_atomic_composition_campaign_bytes_v49r3(
            _resign(document)
        )

