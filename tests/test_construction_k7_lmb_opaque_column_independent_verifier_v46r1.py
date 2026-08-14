from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_lmb_opaque_column_campaign_v46r1 as producer
from acfqp import construction_k7_lmb_opaque_column_independent_verifier_v46r1 as verifier
from acfqp import (
    construction_k7_lmb_opaque_column_successor_preregistration_v46r1 as pre,
)
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


@pytest.fixture(scope="module")
def evidence():
    campaign = producer.freeze_lmb_opaque_column_campaign_v46r1()
    verified = verifier.independently_verify_lmb_opaque_column_campaign_v46r1(
        campaign.canonical_bytes
    )
    return campaign, verified


def test_v46r1_verifier_does_not_import_campaign_producer() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
    assert not any("opaque_column_campaign_v46r1" in name for name in imported)


def test_v46r1_producer_free_identity_and_exact_replay(evidence) -> None:
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
    replay = verifier.independently_verify_lmb_opaque_column_campaign_v46r1(
        campaign.canonical_bytes
    )
    assert replay.canonical_bytes == verified.canonical_bytes
    assert replay.verification_id == verified.verification_id


def test_v46r1_verification_reports_factorization_program_support_ood_and_plans(
    evidence,
) -> None:
    _campaign, verified = evidence
    document = verified.to_document()
    assert document["selected_anonymous_action_field_index"] == 1
    assert document["cyclic_cardinality"] == 3
    assert document["source_occurrence_factorization_count"] == 1
    assert document["all_compiled_constructors_belong_to_registered_meta_grammar"] is True
    assert set(pre.ADDED_CONSTRUCTORS) <= set(document["used_constructor_names"])
    assert document["unregistered_constructor_names"] == []
    assert document["dependency_derived_minimal_support_signature"] == [
        "selected_count",
        "capacity_slack",
        "will_remove_last_action",
    ]
    assert document["support_signature_fields_predeclared"] == []
    assert document["source_acquisition_transition_label_count"] == 11
    assert document["source_confirmation_transition_label_count"] == 21
    assert document["total_source_transition_label_count"] == 32
    assert document["derived_factorized_target_label_count"] == 70
    assert document["strict_exact_context_target_label_count"] == 144
    assert document["replayed_target_execution_transition_count"] == 288
    assert document["replayed_certificate_count"] == 502
    assert document["factorization_relation_program_dependency_compute_events"] == 405
    assert document["ood_decision"] == "OOD_SCHEMA_REJECTED_NO_TRANSFER"
    assert document["ood_prior_access_count"] == 0
    assert document["ood_transition_outcome_access_count"] == 0
    assert document["ood_environment_step_count"] == 0
    assert document["all_episodes_cold_replayed_to_success"] is True
    assert document["all_local_labels_follow_failed_certificates"] is True
    assert document["state_column_roles_predeclared"] is False
    assert document["coordinate_token_equality_scaffold_present"] is False
    assert document["verification_imports_campaign_producer"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


@pytest.mark.parametrize(
    "attack",
    (
        "selected_field",
        "column_role",
        "constructor_list",
        "support_signature",
        "delete_distinction",
        "ood_flip",
        "claim_flip",
    ),
)
def test_v46r1_independent_reconstruction_rejects_rehashed_attacks(
    evidence, monkeypatch, attack
) -> None:
    campaign, _verified = evidence
    document = loads_canonical_json(campaign.canonical_bytes)
    program = document["derived_program"]
    cross = program["cross_occurrence_factorization"]
    if attack == "selected_field":
        cross["selected_anonymous_action_field_index"] = 0
    elif attack == "column_role":
        cross["source_confirmation_factorization"]["capacity_column_index"] += 1
    elif attack == "constructor_list":
        program["used_constructor_names"].remove("RELATION_VECTOR_UPDATE")
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
    elif attack == "ood_flip":
        document["ood_no_transfer"]["decision"] = "TRANSFER_ALLOWED"
    else:
        document["official_execution_allowed"] = True
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(pre.FUTURE_DOMAINS["campaign"], payload)
    monkeypatch.setattr(verifier, "EXPECTED_CAMPAIGN_ID", "0" * 64)
    with pytest.raises(
        verifier.ConstructionK7LMBOpaqueColumnIndependentVerifierV46R1Error
    ):
        verifier.independently_verify_lmb_opaque_column_campaign_v46r1(
            canonical_json_bytes(document)
        )
