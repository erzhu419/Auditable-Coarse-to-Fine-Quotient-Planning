import ast
import copy
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_domain_registry_extension_v86 as domains
from acfqp.construction_k7_projected_target_independent_verifier_v86 import (
    VERIFICATION_ID,
    ConstructionK7ProjectedTargetIndependentVerifierV86Error,
    verify_projected_target_campaign_bytes_v86,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


def test_v86_independent_verifier_rejects_foreign_bytes():
    with pytest.raises(ConstructionK7ProjectedTargetIndependentVerifierV86Error):
        verify_projected_target_campaign_bytes_v86(b"{}")


def test_v86_independent_verifier_import_surface_excludes_producers():
    path = Path(
        "src/acfqp/construction_k7_projected_target_independent_verifier_v86.py"
    )
    tree = ast.parse(path.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = (
        "projected_target_campaign_v86",
        "projected_disagreement_target_campaign_core_v86",
        "generic_projected_disagreement_certificate_planner_v57",
        "generic_projected_disagreement_planner_v56",
        "true_bit_symmetric_three_domain_campaign_core_v59",
    )
    assert not any(any(name in row for name in forbidden) for row in imports)


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_PROJECTED_TARGET_V86") != "1",
    reason="explicit producer-free V86 reconstruction",
)
def test_v86_independent_verifier_reconstructs_frozen_campaign():
    raw = Path(".tmp/exact-freeze/v86_projected_target_campaign.json").read_bytes()
    verification = loads_canonical_json(
        verify_projected_target_campaign_bytes_v86(raw)
    )
    assert verification["target_occurrence_count"] == 6
    assert verification["completed_matched_target_count"] == 3
    assert verification["registered_target_gate_verified"] is True
    assert verification["matched_certificate_traces_replayed"] is True
    assert verification["actual_target_sample_reduction_observed"] is False
    assert verification["sample_tax_reduction_verified"] is False
    assert verification["multi_step_planning_primarily_in_abstract_model_claimed"] is False
    assert verification["official_scalar_cost"] is None
    assert verification["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_REAL_PROJECTED_TARGET_V86") != "1",
    reason="explicit producer-free V86 semantic attack",
)
def test_v86_independent_verifier_rejects_rehashed_certificate_order_attack():
    document = loads_canonical_json(
        Path(".tmp/exact-freeze/v86_projected_target_campaign.json").read_bytes()
    )
    attacked = copy.deepcopy(document)
    occurrence = attacked["target_occurrences"][0]
    ablation = occurrence["matched_ablation"]
    derived = ablation["arms"]["PROJECTED_DISAGREEMENT_WORLD_MODEL"]
    derived["local_distinctions"][0]["query_after_failed_certificate"] = False
    episode_payload = {key: value for key, value in derived.items() if key != "episode_id"}
    derived["episode_id"] = __import__("hashlib").sha256(
        b"acfqp:generic-projected-disagreement-certificate-episode:v57\x00"
        + canonical_json_bytes(episode_payload)
    ).hexdigest()
    ablation_payload = {key: value for key, value in ablation.items() if key != "ablation_id"}
    ablation["ablation_id"] = __import__("hashlib").sha256(
        b"acfqp:generic-projected-disagreement-ablation:v57\x00"
        + canonical_json_bytes(ablation_payload)
    ).hexdigest()
    occurrence_payload = {key: value for key, value in occurrence.items() if key != "occurrence_id"}
    occurrence["occurrence_id"] = domains.extension_content_id_v86(
        domains.CONSTRUCTION_K7_PROJECTED_TARGET_OCCURRENCE_V86_DOMAIN,
        occurrence_payload,
    )
    campaign_payload = {key: value for key, value in attacked.items() if key != "campaign_id"}
    attacked["campaign_id"] = domains.extension_content_id_v86(
        domains.CONSTRUCTION_K7_PROJECTED_TARGET_CAMPAIGN_V86_DOMAIN,
        campaign_payload,
    )
    with pytest.raises(ConstructionK7ProjectedTargetIndependentVerifierV86Error):
        verify_projected_target_campaign_bytes_v86(canonical_json_bytes(attacked))


def test_v86_verification_identity_is_frozen():
    assert VERIFICATION_ID == (
        "407284fb94ab6c2431bc99d9f7b706b84efdaac5f8f319209e6fb5596cebe0d0"
    )
