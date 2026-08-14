from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_lmb_reusable_world_model_campaign_v42 as producer
from acfqp import construction_k7_lmb_reusable_world_model_independent_verifier_v42 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json
from acfqp import construction_k7_lmb_reusable_world_model_preregistration_v42 as pre


@pytest.fixture(scope="module")
def evidence():
    campaign = producer.run_lmb_reusable_world_model_campaign_v42()
    verified = verifier.independently_verify_lmb_reusable_world_model_campaign_v42(
        campaign.canonical_bytes
    )
    return campaign, verified


def test_v42_verifier_does_not_import_campaign_producer() -> None:
    source_path = Path(verifier.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
    assert not any("lmb_reusable_world_model_campaign_v42" in name for name in imported)


def test_v42_producer_free_verification_identity_and_replay(evidence) -> None:
    campaign, verified = evidence
    assert campaign.campaign_id == verifier.EXPECTED_CAMPAIGN_ID
    assert verified.verification_id == verifier.EXPECTED_VERIFICATION_ID
    assert len(verified.canonical_bytes) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(verified.canonical_bytes).hexdigest() == (
        verifier.EXPECTED_CANONICAL_SHA256
    )
    replay = verifier.independently_verify_lmb_reusable_world_model_campaign_v42(
        campaign.canonical_bytes
    )
    assert replay.canonical_bytes == verified.canonical_bytes
    assert replay.verification_id == verified.verification_id


def test_v42_verification_reports_only_registered_workload(evidence) -> None:
    _campaign, verified = evidence
    document = verified.to_document()
    assert document["offline_source_transition_label_count"] == 49
    assert document["structural_meta_prior_target_label_count"] == 3
    assert document["strict_no_prior_target_label_count"] == 72
    assert document["target_label_fraction"].numerator == 1
    assert document["target_label_fraction"].denominator == 24
    assert document["execution_environment_step_count_per_arm"] == 72
    assert document["replayed_execution_transition_count"] == 144
    assert document["replayed_certificate_count"] == 219
    assert document["all_episodes_cold_replayed_to_success"] is True
    assert document["all_local_labels_bound_to_prior_failed_certificate"] is True
    assert document["verified_claim_scope"] == (
        "REGISTERED_SIX_INSTANCE_LMB_MATCHED_ACQUISITION_WORKLOAD_V42"
    )
    assert document["cross_domain_general_sample_efficiency_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.parametrize(
    "attack",
    ("claim_flip", "delete_failed_certificate", "axis_collapse", "proposal_tamper"),
)
def test_v42_independent_verifier_rejects_rehashed_attacks(evidence, attack) -> None:
    campaign, _verified = evidence
    document = loads_canonical_json(campaign.canonical_bytes)
    if attack == "claim_flip":
        document["official_execution_allowed"] = True
    elif attack == "delete_failed_certificate":
        target = next(
            decision
            for episode in document["episodes"]
            for decision in episode["decisions"]
            if decision["local_ground_distinction"] is not None
        )
        target["local_ground_distinction"] = None
    elif attack == "axis_collapse":
        document["matched_summary"]["labels_and_compute_axes_not_collapsed"] = False
    else:
        document["primitive_proposal"]["selected_expressions"][0]["expression"] = [
            "CARDINALITY",
            "RESOURCE_COUNT_VECTOR",
        ]
    payload = {
        key: value
        for key, value in document.items()
        if key != "lmb_reusable_world_model_campaign_id"
    }
    document["lmb_reusable_world_model_campaign_id"] = content_id(
        pre.FUTURE_DOMAINS["campaign"], payload
    )
    with pytest.raises(
        verifier.ConstructionK7LMBReusableWorldModelIndependentVerifierV42Error
    ):
        verifier.independently_verify_lmb_reusable_world_model_campaign_v42(
            canonical_json_bytes(document)
        )
