from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_lmb_anonymous_descriptor_campaign_v45 as producer
from acfqp import construction_k7_lmb_anonymous_descriptor_independent_verifier_v45 as verifier
from acfqp import construction_k7_lmb_anonymous_descriptor_preregistration_v45 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


@pytest.fixture(scope="module")
def evidence():
    campaign = producer.run_lmb_anonymous_descriptor_campaign_v45()
    verified = verifier.independently_verify_lmb_anonymous_descriptor_campaign_v45(
        campaign.canonical_bytes
    )
    return campaign, verified


def test_v45_verifier_does_not_import_campaign_producer() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
    assert not any("anonymous_descriptor_campaign_v45" in name for name in imported)


def test_v45_producer_free_identity_and_exact_replay(evidence) -> None:
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
    replay = verifier.independently_verify_lmb_anonymous_descriptor_campaign_v45(
        campaign.canonical_bytes
    )
    assert replay.canonical_bytes == verified.canonical_bytes
    assert replay.verification_id == verified.verification_id


def test_v45_verification_reports_only_registered_scope(evidence) -> None:
    _campaign, verified = evidence
    document = verified.to_document()
    assert document["selected_anonymous_descriptor_field_index"] == 1
    assert document["valid_anonymous_descriptor_field_indices"] == [1]
    assert document["rewrite_cardinality_derived_from_raw_differences"] == 3
    assert document["numeric_program_grid_present"] is False
    assert document["dependency_derived_minimal_support_signature"] == [
        "selected_count",
        "capacity_slack",
        "will_remove_last_tile",
    ]
    assert document["support_signature_fields_predeclared"] == []
    assert document["source_projection_transition_label_count"] == 13
    assert document["source_confirmation_transition_label_count"] == 18
    assert document["total_source_transition_label_count"] == 31
    assert document["structural_meta_prior_target_label_count"] == 21
    assert document["strict_no_prior_target_label_count"] == 126
    assert document["target_label_fraction"].numerator == 1
    assert document["target_label_fraction"].denominator == 6
    assert document["replayed_source_transition_count"] == 31
    assert document["replayed_projection_field_evaluation_count"] == 93
    assert document["replayed_dependency_deletion_trial_count"] == 3
    assert document["replayed_target_execution_transition_count"] == 252
    assert document["replayed_certificate_count"] == 399
    assert document["projection_program_dependency_derivation_compute_events"] == 374
    assert document["source_target_descriptor_value_namespaces_disjoint"] is True
    assert document["source_target_coordinate_token_namespaces_disjoint"] is True
    assert document["verification_imports_campaign_producer"] is False
    assert document["verified_claim_scope"] == (
        "REGISTERED_ANONYMOUS_DESCRIPTOR_PERMUTED_LMB_WORKLOAD_V45"
    )
    assert document["named_action_class_scaffold_present"] is False
    assert document["hand_written_structural_support_key_present"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None


@pytest.mark.parametrize(
    "attack",
    (
        "selected_field",
        "descriptor_token",
        "descriptor_field",
        "support_signature",
        "delete_distinction",
        "target_layout",
        "claim_flip",
    ),
)
def test_v45_independent_reconstruction_rejects_rehashed_attacks(
    evidence, monkeypatch, attack
) -> None:
    campaign, _verified = evidence
    document = loads_canonical_json(campaign.canonical_bytes)
    program = document["derived_program"]
    if attack == "selected_field":
        program["selected_anonymous_descriptor_field_index"] = 0
    elif attack == "descriptor_token":
        program["projection_acquisition_observations"][0]["coordinate_tokens"][0] += 1
    elif attack == "descriptor_field":
        program["source_confirmation_observations"][0]["action_descriptor_fields"][1] += 1
    elif attack == "support_signature":
        program["dependency_derived_support_signature"]["minimal_support_signature"].pop()
    elif attack == "delete_distinction":
        decision = next(
            decision
            for episode in document["episodes"]
            for decision in episode["decisions"]
            if decision["local_distinction"] is not None
        )
        decision["local_distinction"] = None
    elif attack == "target_layout":
        document["episodes"][0]["anonymous_layout"]["coordinate_tokens"].reverse()
    else:
        document["official_execution_allowed"] = True
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    monkeypatch.setattr(verifier, "EXPECTED_CAMPAIGN_ID", "0" * 64)
    with pytest.raises(
        verifier.ConstructionK7LMBAnonymousDescriptorIndependentVerifierV45Error
    ):
        verifier.independently_verify_lmb_anonymous_descriptor_campaign_v45(
            canonical_json_bytes(document)
        )
