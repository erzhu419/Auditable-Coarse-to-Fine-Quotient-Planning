from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_lmb_witness_blind_campaign_v43 as producer
from acfqp import construction_k7_lmb_witness_blind_independent_verifier_v43 as verifier
from acfqp import construction_k7_lmb_witness_blind_preregistration_v43 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


@pytest.fixture(scope="module")
def evidence():
    campaign = producer.run_lmb_witness_blind_campaign_v43()
    verified = verifier.independently_verify_lmb_witness_blind_campaign_v43(
        campaign.canonical_bytes
    )
    return campaign, verified


def test_v43_verifier_does_not_import_campaign_producer() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
    assert not any("lmb_witness_blind_campaign_v43" in name for name in imported)


def test_v43_producer_free_identity_and_exact_replay(evidence) -> None:
    campaign, verified = evidence
    assert campaign.campaign_id == verifier.EXPECTED_CAMPAIGN_ID
    assert len(campaign.canonical_bytes) == verifier.EXPECTED_CAMPAIGN_BYTE_COUNT
    assert hashlib.sha256(campaign.canonical_bytes).hexdigest() == (
        verifier.EXPECTED_CAMPAIGN_SHA256
    )
    assert verified.verification_id == verifier.EXPECTED_VERIFICATION_ID
    assert len(verified.canonical_bytes) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(verified.canonical_bytes).hexdigest() == (
        verifier.EXPECTED_CANONICAL_SHA256
    )
    replay = verifier.independently_verify_lmb_witness_blind_campaign_v43(
        campaign.canonical_bytes
    )
    assert replay.canonical_bytes == verified.canonical_bytes
    assert replay.verification_id == verified.verification_id


def test_v43_verification_reports_registered_cross_cardinality_scope(evidence) -> None:
    _campaign, verified = evidence
    document = verified.to_document()
    assert document["selected_candidate"] == [2, 0]
    assert document["offline_source_transition_label_count"] == 6
    assert document["structural_meta_prior_target_label_count"] == 33
    assert document["strict_no_prior_target_label_count"] == 90
    assert document["target_label_fraction"].numerator == 11
    assert document["target_label_fraction"].denominator == 30
    assert document["execution_environment_step_count_per_arm"] == 90
    assert document["replayed_execution_transition_count"] == 180
    assert document["replayed_certificate_count"] == 303
    assert document["source_generation_witness_access_count"] == 0
    assert document["target_generation_witness_access_count"] == 0
    assert document["verified_claim_scope"] == (
        "REGISTERED_WITNESS_BLIND_LMB_CROSS_CARDINALITY_WORKLOAD_V43"
    )
    assert document["open_ended_operator_invention_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.parametrize(
    "attack",
    (
        "claim_flip",
        "delete_distinction",
        "witness_access",
        "target_action",
        "source_observation",
    ),
)
def test_v43_independent_reconstruction_rejects_rehashed_attacks(
    evidence, monkeypatch, attack
) -> None:
    campaign, _verified = evidence
    document = loads_canonical_json(campaign.canonical_bytes)
    if attack == "claim_flip":
        document["official_execution_allowed"] = True
    elif attack == "delete_distinction":
        target = next(
            decision
            for episode in document["episodes"]
            for decision in episode["decisions"]
            if decision["local_distinction"] is not None
        )
        target["local_distinction"] = None
    elif attack == "witness_access":
        document["proposal"]["source_generation_witness_access_count"] = 1
    elif attack == "target_action":
        document["episodes"][0]["decisions"][0]["selected_action"]["tile"] += 1
    else:
        document["proposal"]["source_observation_rows"][0]["candidate_count_after"] += 1
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    monkeypatch.setattr(verifier, "EXPECTED_CAMPAIGN_ID", "0" * 64)
    with pytest.raises(
        verifier.ConstructionK7LMBWitnessBlindIndependentVerifierV43Error
    ):
        verifier.independently_verify_lmb_witness_blind_campaign_v43(
            canonical_json_bytes(document)
        )
