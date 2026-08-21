import ast
import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_persistent_second_domain_independent_verifier_v95 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v95_persistent_second_domain_campaign.json"
)


def test_v95_independent_verifier_replays_persistent_sample_tax_gate():
    raw = CAMPAIGN_PATH.read_bytes()
    document = verifier.verify_persistent_second_domain_campaign_bytes_v95(raw)
    assert document["verification_status"] == (
        "REGISTERED_PERSISTENT_SECOND_DOMAIN_SAMPLE_TAX_REDUCTION_VERIFIED"
    )
    assert document["verified_accounting"][
        "meta_prior_lifetime_unique_target_labels"
    ] == 78
    assert document["verified_accounting"][
        "no_prior_lifetime_unique_target_labels"
    ] == 90
    assert document["verified_accounting"][
        "strict_cold_direct_lifetime_target_labels"
    ] == 310
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False


def test_v95_frozen_verification_bytes_are_exact_and_producer_free():
    campaign_raw = CAMPAIGN_PATH.read_bytes()
    verification_raw = verifier.freeze_persistent_second_domain_verification_v95(
        campaign_raw
    )
    assert len(verification_raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(verification_raw).hexdigest() == (
        verifier.EXPECTED_CANONICAL_SHA256
    )
    assert loads_canonical_json(verification_raw)["verification_id"] == (
        verifier.VERIFICATION_ID
    )
    source = Path(verifier.__file__).read_text()
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(
        forbidden in module
        for module in imports
        for forbidden in (
            "persistent_second_domain_campaign_v95",
            "persistent_second_domain_campaign_core_v95",
            "generic_projected_low_label_applicability_v76",
            "generic_projected_persistent_sequence_v78",
        )
    )


def test_v95_independent_semantic_replay_rejects_resigned_overlay_tamper():
    document = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    forged = copy.deepcopy(document)
    overlay = forged["target_occurrences"][0][
        "meta_prior_persistent_sequence"
    ]["overlay_epochs"][1]
    overlay["total_unique_ground_support_labels_paid"] += 1
    overlay_payload = {
        key: value for key, value in overlay.items() if key != "overlay_epoch_id"
    }
    overlay["overlay_epoch_id"] = hashlib.sha256(
        verifier._OVERLAY_DOMAIN + canonical_json_bytes(overlay_payload)  # noqa: SLF001
    ).hexdigest()
    with pytest.raises(
        verifier.ConstructionK7PersistentSecondDomainIndependentVerifierV95Error
    ):
        verifier._verify_campaign_document(forged)  # noqa: SLF001


def test_v95_independent_verifier_rejects_nonexact_campaign_bytes():
    raw = CAMPAIGN_PATH.read_bytes()
    with pytest.raises(
        verifier.ConstructionK7PersistentSecondDomainIndependentVerifierV95Error
    ):
        verifier.verify_persistent_second_domain_campaign_bytes_v95(raw + b"\n")
