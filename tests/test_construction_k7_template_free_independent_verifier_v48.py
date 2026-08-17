from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_template_free_campaign_v48 as campaign
from acfqp import construction_k7_template_free_independent_verifier_v48 as verifier
from acfqp import construction_k7_template_free_preregistration_v48 as pre
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


@pytest.fixture(scope="module")
def campaign_bytes() -> bytes:
    return campaign.freeze_template_free_campaign_v48().canonical_bytes


def _replace_id(document: dict, field: str, domain: str) -> None:
    payload = {key: value for key, value in document.items() if key != field}
    document[field] = content_id(domain, payload)


def _resign_campaign(document: dict) -> bytes:
    _replace_id(
        document,
        "template_free_campaign_id",
        pre.FUTURE_DOMAINS["campaign"],
    )
    return canonical_json_bytes(document)


def test_v48_producer_free_verification_is_frozen(campaign_bytes) -> None:
    raw = verifier.freeze_template_free_verification_v48(campaign_bytes)
    document = loads_canonical_json(raw)
    assert document["template_free_verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["source_archives_replayed_from_preregistered_generators"] is True
    assert document["programs_reconstructed_from_raw_observations"] is True
    assert document["dependency_support_reconstructed_from_compiled_ast"] is True
    assert document["target_bindings_plans_and_execution_replayed"] is True
    assert document["failed_certificate_local_distinction_and_overlay_replayed"] is True
    assert document["accounting_reconstructed"] is True
    assert document["source_transition_count"] == 215
    assert document["target_local_ground_label_count"] == 1
    assert document["strict_ground_label_count"] == 695
    assert document["registered_label_saving"] == 479
    assert document["producer_module_imported"] is False


def test_v48_verifier_imports_no_campaign_producer() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any("template_free_campaign_v48" in name for name in imported)


@pytest.mark.parametrize(
    "attack",
    [
        "source",
        "program",
        "support",
        "partial",
        "local_distinction",
        "sample_tax",
        "accounting",
        "ood",
        "official",
    ],
)
def test_v48_independent_verifier_rejects_resigned_attacks(
    campaign_bytes, attack
) -> None:
    document = loads_canonical_json(campaign_bytes)
    if attack == "source":
        archive = document["source_archives"][0]
        archive["raw_transitions"][0]["post_vector"][0] += 1
        _replace_id(
            archive,
            "raw_observation_id",
            pre.FUTURE_DOMAINS["observation"],
        )
    elif attack == "program":
        program = document["programs"][0]
        program["compiled_assignments"][0]["expression"].append("FORGED")
        _replace_id(program, "program_id", pre.FUTURE_DOMAINS["program"])
    elif attack == "support":
        support = document["dependency_support_signatures"][0]
        support["predeclared_semantic_support_names"] = ["FORGED"]
        _replace_id(
            support,
            "support_signature_id",
            pre.FUTURE_DOMAINS["support"],
        )
    elif attack == "partial":
        partial = document["stochastic_partial_model"]
        partial["exact_probability_authority"] = True
        _replace_id(partial, "partial_model_id", pre.FUTURE_DOMAINS["partial"])
    elif attack == "local_distinction":
        episode = next(
            row
            for row in document["episodes"]
            if row["structural_target_local_labels"] == 1
        )
        decision = next(
            row for row in episode["decisions"] if row["local_distinction"]
        )
        distinction = decision["local_distinction"]
        distinction["observed_modular_delta"] += 1
        _replace_id(
            distinction,
            "distinction_id",
            pre.FUTURE_DOMAINS["distinction"],
        )
        _replace_id(episode, "episode_id", pre.FUTURE_DOMAINS["episode"])
    elif attack == "sample_tax":
        sample = document["sample_tax"]
        sample["registered_label_saving"] += 1
        _replace_id(sample, "sample_tax_id", pre.FUTURE_DOMAINS["sample_tax"])
    elif attack == "accounting":
        document["accounting_axes"]["planning_compute_events_structural"] += 1
    elif attack == "ood":
        ood = document["strict_ood_control"]
        ood["prior_access_count"] = 1
        _replace_id(ood, "ood_rejection_id", pre.FUTURE_DOMAINS["ood"])
    elif attack == "official":
        document["official_execution_allowed"] = True
    with pytest.raises(
        verifier.ConstructionK7TemplateFreeIndependentVerifierV48Error
    ):
        verifier.verify_template_free_campaign_bytes_v48(
            _resign_campaign(document)
        )
