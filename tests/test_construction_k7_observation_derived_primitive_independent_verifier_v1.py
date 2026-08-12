from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_observation_derived_primitive_basis_v1 as producer
from acfqp import construction_k7_observation_derived_primitive_independent_verifier_v1 as subject
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def campaign_bytes() -> bytes:
    return canonical_json_bytes(
        producer.run_observation_derived_primitive_campaign_v1().to_document()
    )


def test_independent_verifier_replays_relations_columns_and_heldout(campaign_bytes) -> None:
    verification = subject.verify_observation_derived_primitive_campaign_bytes_independently_v1(campaign_bytes)
    document = verification.to_document()
    assert document["raw_relation_expressions_replayed"] is True
    assert document["source_observation_columns_replayed"] is True
    assert document["heldout_observation_columns_replayed"] is True
    assert document["program_obligation_basis_selection_replayed"] is True
    assert document["constructor_or_ground_execution_verified"] is False


def test_verifier_imports_no_producer_or_observer() -> None:
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
            "acfqp.construction_k7_observation_derived_primitive_basis_v1",
            "acfqp.construction_k7_observed_program_heldout_campaign_v1",
            "acfqp.transition_tuple_observer_v1",
        }
    )


def test_fully_resigned_candidate_column_attack_is_rejected(campaign_bytes) -> None:
    document = __import__("json").loads(campaign_bytes)
    attacked = copy.deepcopy(document)
    candidate = attacked["basis"]["primitive_candidates"][1]
    candidate["source_observation_column"][0] = 9
    payload = {key: value for key, value in candidate.items() if key != "primitive_candidate_id"}
    candidate["primitive_candidate_id"] = content_id(producer.CANDIDATE_DOMAIN, payload)
    with pytest.raises(subject.ConstructionK7ObservationDerivedPrimitiveIndependentVerifierV1Error):
        subject.verify_observation_derived_primitive_campaign_bytes_independently_v1(
            canonical_json_bytes(attacked)
        )

