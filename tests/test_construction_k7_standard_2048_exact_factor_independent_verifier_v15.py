from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_exact_factor_campaign_v15 as producer
from acfqp import construction_k7_standard_2048_exact_factor_independent_verifier_v15 as verifier
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CAMPAIGN_V15_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


@pytest.fixture(scope="module")
def campaign() -> producer.Standard2048ExactFactorCampaignV15:
    return producer.run_standard_2048_exact_factor_campaign_v15()


@pytest.fixture(scope="module")
def verification(
    campaign: producer.Standard2048ExactFactorCampaignV15,
) -> verifier.Standard2048ExactFactorIndependentVerificationV15:
    return verifier.verify_standard_2048_exact_factor_campaign_bytes_independently_v15(
        campaign.canonical_bytes
    )


def _resign_campaign(document: dict[str, object]) -> bytes:
    payload = {
        key: value
        for key, value in document.items()
        if key != "exact_factor_campaign_id"
    }
    document["exact_factor_campaign_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_EXACT_FACTOR_CAMPAIGN_V15_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_independent_verifier_imports_no_v13_v14_v15_producer() -> None:
    path = Path(verifier.__file__).resolve()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    forbidden = {
        "acfqp.construction_k7_standard_2048_coordinate_basis_v13",
        "acfqp.construction_k7_standard_2048_observation_proposed_program_v14",
        "acfqp.construction_k7_standard_2048_exact_factor_campaign_v15",
        "acfqp.construction_k7_standard_2048_exact_factor_preregistration_v15",
    }
    assert imported.isdisjoint(forbidden)
    source = path.read_text(encoding="utf-8")
    assert "program_v14._" not in source
    assert "basis_v13._" not in source


def test_full_campaign_is_replayed_from_independent_semantics(
    verification: verifier.Standard2048ExactFactorIndependentVerificationV15,
) -> None:
    document = verification.to_document()
    assert verification.campaign_id == verifier.EXPECTED_CAMPAIGN_ID
    assert verification.verification_id == verifier.EXPECTED_VERIFICATION_ID
    assert document["v13_observation_and_coordinate_selection_independently_replayed"] is True
    assert document["v14_program_proposal_and_160000_line_proof_independently_replayed"] is True
    assert document["source_closed_spawn_contract_independently_replayed"] is True
    assert document["all_64_factored_h3_certificates_independently_replayed"] is True
    assert document["all_64_target_transitions_independently_replayed"] is True
    assert document["matched_cold_ground_values_independently_replayed"] is True
    assert document["all_root_action_values_exactly_equal"] is True


def test_sample_tax_claim_remains_scoped(
    verification: verifier.Standard2048ExactFactorIndependentVerificationV15,
) -> None:
    document = verification.to_document()
    assert document["sample_tax_observation_axis_reduction_independently_verified"] is True
    assert document["total_operational_work_saving_verified"] is False
    assert document["broad_sample_efficiency_or_full_game_verified"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


@pytest.mark.parametrize(
    "attack",
    ("certificate", "route", "sample_tax", "source", "claim"),
)
def test_fully_resigned_semantic_attacks_are_rejected_before_replay(
    campaign: producer.Standard2048ExactFactorCampaignV15,
    attack: str,
) -> None:
    document = copy.deepcopy(campaign.to_document())
    if attack == "certificate":
        document["episodes"][0]["decisions"][0]["certificate"][
            "selected_expected_merge_score"
        ] = {"numerator": 999, "denominator": 1}
    elif attack == "route":
        document["episodes"][0]["decisions"][0]["route"] = "GROUND"
    elif attack == "sample_tax":
        document["offline_transition_observation_saving"] = 999999
    elif attack == "source":
        document["exact_factor_source_closure"]["source_bytes_hex"] = "00"
    else:
        document["full_standard_2048_game_completed"] = True
    forged_bytes = _resign_campaign(document)
    forged = loads_canonical_json(forged_bytes)
    assert forged["exact_factor_campaign_id"] != verifier.EXPECTED_CAMPAIGN_ID
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExactFactorIndependentVerifierV15Error
    ):
        verifier.verify_standard_2048_exact_factor_campaign_bytes_independently_v15(
            forged_bytes
        )


def test_verification_object_cannot_be_caller_minted(
    verification: verifier.Standard2048ExactFactorIndependentVerificationV15,
) -> None:
    with pytest.raises(
        verifier.ConstructionK7Standard2048ExactFactorIndependentVerifierV15Error
    ):
        verifier.Standard2048ExactFactorIndependentVerificationV15(
            object(),
            verification.canonical_bytes,
            verification.verification_id,
            verification.campaign_id,
        )
