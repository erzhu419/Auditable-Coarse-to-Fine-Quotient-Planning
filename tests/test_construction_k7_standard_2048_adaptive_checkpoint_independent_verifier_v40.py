from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_adaptive_checkpoint_campaign_v40 as campaign
from acfqp import construction_k7_standard_2048_adaptive_checkpoint_independent_verifier_v40 as verifier


@pytest.fixture(scope="module")
def verified():
    produced = campaign.run_standard_2048_adaptive_checkpoint_campaign_v40()
    return verifier.verify_standard_2048_adaptive_checkpoint_bytes_independently_v40(
        produced.canonical_bytes
    )


def test_checkpoint_binding_is_reconstructed_without_producer() -> None:
    binding = verifier._binding_expected()
    assert binding["target_probability_query_count_in_segment"] == 0
    assert len(binding["source_facts"]) == 4
    assert binding["maximum_concurrent_worker_processes"] == 2
    assert binding["same_resource_schedule_as_verified_v39"] is True


def test_independent_verifier_does_not_import_campaign_producer() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any("adaptive_checkpoint_campaign_v40" in name for name in imported)


def test_checkpoint_campaign_replays_independently(verified) -> None:
    document = verified.to_document()
    assert document["all_checkpoint_h3_certificates_independently_replayed"] is True
    assert document["all_global_index_seeded_transitions_independently_replayed"] is True
    assert document["all_registered_cold_target_checkpoints_independently_replayed"] is True
    assert document["v35_proof_and_overlay_binding_verified"] is True
    assert document["zero_additional_model_labels_verified"] is True
    assert document["producer_module_imported"] is False
    assert document["retained_campaign_bytes_replayed"] is True
    assert document["verified_v39_predecessor_and_resource_schedule_reused"] is True
    assert document["verification_resource_schedule"] == {
        "maximum_concurrent_worker_processes": 2,
        "execution_wave_count": 2,
        "episode_tasks_per_wave": 2,
        "fresh_executor_used_for_each_wave": True,
    }
    assert document["official_execution_allowed"] is False


def test_campaign_semantic_tamper_is_rejected() -> None:
    document = campaign.run_standard_2048_adaptive_checkpoint_campaign_v40().to_document()
    forged = copy.deepcopy(document)
    forged["episodes"][0]["decisions"][0]["global_decision_index"] = 127
    from acfqp.phase3e_ids import canonical_json_bytes

    with pytest.raises(
        verifier.ConstructionK7Standard2048AdaptiveCheckpointIndependentVerifierV40Error
    ):
        verifier.verify_standard_2048_adaptive_checkpoint_bytes_independently_v40(
            canonical_json_bytes(forged)
        )
