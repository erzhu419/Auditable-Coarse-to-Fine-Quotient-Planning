from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_lmb_difference_program_campaign_v44r1 as producer
from acfqp import (
    construction_k7_lmb_difference_program_independent_verifier_v44r1 as verifier,
)
from acfqp import (
    construction_k7_lmb_difference_grammar_successor_preregistration_v44r1 as pre,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


@pytest.fixture(scope="module")
def evidence():
    campaign = producer.run_lmb_difference_program_campaign_v44r1()
    verified = verifier.independently_verify_lmb_difference_program_campaign_v44r1(
        campaign.canonical_bytes
    )
    return campaign, verified


def test_v44r1_verifier_does_not_import_campaign_producer() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
    assert not any("difference_program_campaign_v44r1" in name for name in imported)


def test_v44r1_producer_free_identity_and_exact_replay(evidence) -> None:
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
    replay = verifier.independently_verify_lmb_difference_program_campaign_v44r1(
        campaign.canonical_bytes
    )
    assert replay.canonical_bytes == verified.canonical_bytes
    assert replay.verification_id == verified.verification_id


def test_v44r1_verification_reports_only_registered_scope(evidence) -> None:
    _campaign, verified = evidence
    document = verified.to_document()
    assert document["v44_failure_id"] == pre.V44_FAILURE_ID
    assert document["rewrite_cardinality_derived_from_raw_differences"] == 3
    assert document["numeric_program_grid_present"] is False
    assert document["inherited_offline_source_transition_label_count"] == 42
    assert document["additional_source_confirmation_label_count"] == 15
    assert document["total_offline_source_transition_label_count"] == 57
    assert document["structural_meta_prior_target_label_count"] == 18
    assert document["strict_no_prior_target_label_count"] == 108
    assert document["target_label_fraction"].numerator == 1
    assert document["target_label_fraction"].denominator == 6
    assert document["replayed_source_transition_count"] == 57
    assert document["replayed_target_execution_transition_count"] == 216
    assert document["replayed_certificate_count"] == 342
    assert document["verified_claim_scope"] == (
        "REGISTERED_RAW_DIFFERENCE_LMB_CROSS_CAPACITY_WORKLOAD_V44R1"
    )
    assert document["open_ended_grammar_invention_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.parametrize(
    "attack",
    (
        "numeric_grid",
        "rewrite_literal",
        "delete_source_row",
        "source_witness",
        "delete_target_distinction",
        "target_capacity",
    ),
)
def test_v44r1_independent_reconstruction_rejects_rehashed_attacks(
    evidence, monkeypatch, attack
) -> None:
    campaign, _verified = evidence
    document = loads_canonical_json(campaign.canonical_bytes)
    program = document["derived_program"]
    if attack == "numeric_grid":
        program["predeclared_numeric_program_grid_present"] = True
    elif attack == "rewrite_literal":
        program["rewrite_cardinality_derivation"]["derived_numeric_literal"] = 4
    elif attack == "delete_source_row":
        program["fresh_source_confirmation_observations"].pop()
    elif attack == "source_witness":
        program["source_generation_witness_access_count"] = 1
    elif attack == "delete_target_distinction":
        target = next(
            decision
            for episode in document["episodes"]
            for decision in episode["decisions"]
            if decision["local_distinction"] is not None
        )
        target["local_distinction"] = None
    else:
        document["episodes"][0]["instance_specification"]["capacity"] = 7
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    monkeypatch.setattr(verifier, "EXPECTED_CAMPAIGN_ID", "0" * 64)
    with pytest.raises(
        verifier.ConstructionK7LMBDifferenceProgramIndependentVerifierV44R1Error
    ):
        verifier.independently_verify_lmb_difference_program_campaign_v44r1(
            canonical_json_bytes(document)
        )
