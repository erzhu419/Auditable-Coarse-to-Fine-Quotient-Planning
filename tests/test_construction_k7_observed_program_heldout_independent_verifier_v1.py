from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_observed_program_heldout_campaign_v1 as producer
from acfqp import construction_k7_observed_program_heldout_independent_verifier_v1 as subject
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def campaign_bytes() -> bytes:
    return canonical_json_bytes(
        producer.run_observed_program_heldout_campaign_v1().to_document()
    )


def test_independent_verifier_replays_source_lattice_and_heldout_decisions(
    campaign_bytes: bytes,
) -> None:
    verification = subject.verify_observed_program_heldout_campaign_bytes_independently_v1(
        campaign_bytes
    )
    document = verification.to_document()
    assert document["source_candidate_lattice_replayed"] is True
    assert document["heldout_topology_features_replayed"] is True
    assert document["transfer_and_no_transfer_decisions_replayed"] is True
    assert document["constructor_or_model_execution_verified"] is False
    assert document["official_execution_allowed"] is False


def test_independent_verifier_imports_no_program_or_campaign_producer() -> None:
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    assert imported.isdisjoint(
        {
            "acfqp.construction_k7_observed_program_heldout_campaign_v1",
            "acfqp.construction_k7_observed_capability_program_synthesis_v1",
            "acfqp.construction_k7_observed_constructor_capability_v1",
            "acfqp.transition_tuple_observer_v1",
        }
    )


def test_fully_resigned_feature_attack_is_rejected(campaign_bytes: bytes) -> None:
    document = __import__("json").loads(campaign_bytes)
    attacked = copy.deepcopy(document)
    observation = attacked["preregistration"]["ordered_cases"][1]["observation"]
    edge_feature = next(
        row for row in observation["observed_feature_rows"] if row["primitive"] == "edge_count"
    )
    edge_feature["value"] += 1
    observation_payload = {
        key: value for key, value in observation.items() if key != "heldout_observation_id"
    }
    observation["heldout_observation_id"] = content_id(
        producer.OBSERVATION_DOMAIN, observation_payload
    )
    prereg = attacked["preregistration"]
    prereg_payload = {
        key: value for key, value in prereg.items() if key != "heldout_preregistration_id"
    }
    prereg["heldout_preregistration_id"] = content_id(
        producer.PREREGISTRATION_DOMAIN, prereg_payload
    )
    attacked["heldout_preregistration_id"] = prereg["heldout_preregistration_id"]
    for index, evaluation in enumerate(attacked["heldout_evaluations"]):
        evaluation["heldout_preregistration_id"] = prereg["heldout_preregistration_id"]
        if index == 1:
            evaluation["heldout_observation_id"] = observation["heldout_observation_id"]
        payload = {
            key: value for key, value in evaluation.items() if key != "heldout_evaluation_id"
        }
        evaluation["heldout_evaluation_id"] = content_id(
            producer.EVALUATION_DOMAIN, payload
        )
    attacked["ordered_heldout_evaluation_ids"] = [
        row["heldout_evaluation_id"] for row in attacked["heldout_evaluations"]
    ]
    root_payload = {
        key: value
        for key, value in attacked.items()
        if key
        not in {
            "preregistration",
            "source_program_grammar",
            "source_program_corpus",
            "source_program_proposals",
            "heldout_evaluations",
            "heldout_program_campaign_id",
        }
    }
    attacked["heldout_program_campaign_id"] = content_id(
        producer.CAMPAIGN_DOMAIN, root_payload
    )
    with pytest.raises(
        subject.ConstructionK7ObservedProgramHeldoutIndependentVerifierV1Error
    ):
        subject.verify_observed_program_heldout_campaign_bytes_independently_v1(
            canonical_json_bytes(attacked)
        )
