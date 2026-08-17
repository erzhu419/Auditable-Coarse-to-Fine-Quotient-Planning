from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_cross_schema_factor_independent_verifier_v51 as v51verify
from acfqp import construction_k7_factor_prior_ablation_campaign_v52 as campaign
from acfqp import construction_k7_factor_prior_ablation_independent_verifier_v52 as verifier
from acfqp import construction_k7_factor_prior_ablation_preregistration_v52 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


@pytest.fixture(scope="module")
def campaign_bytes() -> bytes:
    return campaign.run_factor_prior_ablation_campaign_v52().canonical_bytes


@pytest.fixture(scope="module")
def verification_document(campaign_bytes) -> dict:
    raw = verifier.freeze_factor_prior_ablation_verification_v52(campaign_bytes)
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    return loads_canonical_json(raw)


def test_v52_producer_free_verification_is_frozen(verification_document) -> None:
    document = verification_document
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["preregistration_id"] == pre.PREREGISTRATION_ID
    assert document["matched_occurrence_count"] == 16
    assert document["factor_prior_cumulative_labels"] == 633
    assert document["no_prior_cumulative_labels"] == 11_387
    assert document["cumulative_label_reduction"] == 10_754
    assert document["registered_break_even_occurrence_count"] == 1
    assert document["v52_producer_or_campaign_core_module_imported"] is False


def test_v52_verifier_imports_no_v52_or_v51_producer_core() -> None:
    for path in (Path(verifier.__file__), Path(v51verify.__file__)):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert not any("factor_prior_ablation_campaign_v52" in name for name in imported)
        assert not any("factor_prior_acquisition_ablation_core_v52" in name for name in imported)
        assert not any("cross_schema_factor_campaign_v51" in name for name in imported)
        assert not any("cross_schema_factor_campaign_core_v51" in name for name in imported)


@pytest.mark.parametrize(
    "attack",
    [
        "prior_acquisition",
        "no_prior_acquisition",
        "certificate",
        "distinction",
        "prior_episode",
        "no_prior_episode",
        "overlay",
        "sample_tax",
        "accounting",
        "predecessor",
        "claim",
        "official",
    ],
)
def test_v52_independent_verifier_rejects_resigned_attacks(
    campaign_bytes, attack
) -> None:
    document = loads_canonical_json(campaign_bytes)
    if attack == "prior_acquisition":
        document["factor_prior_acquisitions"][0]["total_ground_support_labels"] += 1
    elif attack == "no_prior_acquisition":
        document["no_prior_acquisitions"][0]["factor_library_accessed"] = True
    elif attack == "certificate":
        document["failed_certificates"][0][
            "ground_query_performed_before_failure"
        ] = True
    elif attack == "distinction":
        document["local_distinctions"][0]["relation_output"] += 1
    elif attack == "prior_episode":
        document["factor_prior_episodes"][0]["action_keys"][0] += 1
    elif attack == "no_prior_episode":
        document["no_prior_episodes"][0]["ground_support_labels"] += 1
    elif attack == "overlay":
        document["relation_overlay"][next(iter(document["relation_overlay"]))][0][1] += 1
    elif attack == "sample_tax":
        document["sample_tax"]["historical_factor_prior_labels"] -= 1
    elif attack == "accounting":
        document["accounting"]["factor_prior_planning_compute_events"] += 1
    elif attack == "predecessor":
        document["frozen_v51_factor_composed_program_id"] = "f" * 64
    elif attack == "claim":
        document["claim_boundary"]["individual_factor_only_causal_effect_claimed"] = True
    elif attack == "official":
        document["official_execution_allowed"] = True
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    with pytest.raises(
        verifier.ConstructionK7FactorPriorAblationIndependentVerifierV52Error
    ):
        verifier.verify_factor_prior_ablation_campaign_bytes_v52(
            canonical_json_bytes(document)
        )
