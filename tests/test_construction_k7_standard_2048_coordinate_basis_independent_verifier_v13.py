from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_coordinate_basis_independent_verifier_v13 as verifier
from acfqp import construction_k7_standard_2048_coordinate_basis_v13 as producer
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_BASIS_V13_DOMAIN,
    CONSTRUCTION_K7_STANDARD_2048_COORDINATE_OBSERVATION_ARCHIVE_V13_DOMAIN,
    canonical_json_bytes,
    content_id,
)


@pytest.fixture(scope="module")
def basis_and_verification():
    basis = producer.build_standard_2048_coordinate_basis_v13()
    verification = verifier.verify_standard_2048_coordinate_basis_bytes_independently_v13(
        basis.canonical_bytes
    )
    return basis, verification


def _resign(document: dict) -> bytes:
    for role in ("source_archive", "validation_archive"):
        archive = document[role]
        payload = {
            key: value
            for key, value in archive.items()
            if key != "coordinate_observation_archive_id"
        }
        archive["coordinate_observation_archive_id"] = content_id(
            CONSTRUCTION_K7_STANDARD_2048_COORDINATE_OBSERVATION_ARCHIVE_V13_DOMAIN,
            payload,
        )
    basis = document["basis"]
    basis["source_observation_archive_id"] = document["source_archive"][
        "coordinate_observation_archive_id"
    ]
    basis["validation_observation_archive_id"] = document["validation_archive"][
        "coordinate_observation_archive_id"
    ]
    payload = {key: value for key, value in basis.items() if key != "coordinate_basis_id"}
    basis["coordinate_basis_id"] = content_id(
        CONSTRUCTION_K7_STANDARD_2048_COORDINATE_BASIS_V13_DOMAIN, payload
    )
    return canonical_json_bytes(document)


def test_independent_verifier_does_not_import_producer_or_preregistration() -> None:
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.construction_k7_standard_2048_coordinate_basis_v13" not in imports
    assert (
        "acfqp.construction_k7_standard_2048_coordinate_preregistration_v13"
        not in imports
    )


def test_independent_replay_covers_archives_candidates_and_selection(
    basis_and_verification,
) -> None:
    basis, verification = basis_and_verification
    assert verification.coordinate_basis_id == basis.coordinate_basis_id
    document = verification.to_document()
    assert document["source_observation_rows_independently_replayed"] == 512
    assert document["validation_observation_rows_independently_replayed"] == 256
    assert document["selected_candidate_keys"] == ["rank_histogram"]
    assert document["sha_tape_board_action_and_outcome_replayed"] is True
    assert document["d4_transport_and_all_candidate_projections_replayed"] is True
    assert document["source_first_subset_enumeration_replayed"] is True
    assert document["heldout_validation_read_after_selection_replayed"] is True
    assert document["global_lumpability_or_sound_plan_certificate_verified"] is False
    assert document["sample_tax_reduction_verified"] is False


@pytest.mark.parametrize(
    "attack",
    (
        lambda row: row["source_archive"]["rows"][0].__setitem__("merge_score", 999),
        lambda row: row["validation_archive"]["rows"][0].__setitem__(
            "outcome_probability_not_disclosed_to_selector", False
        ),
        lambda row: row["basis"].__setitem__(
            "selected_candidate_keys", ["exact_d4_board_fallback_coordinate"]
        ),
        lambda row: row["basis"].__setitem__(
            "statistical_basis_can_issue_sound_plan_certificate", True
        ),
        lambda row: row["basis"].__setitem__("sample_tax_reduction_claimed", True),
    ),
)
def test_fully_resigned_observation_selection_and_claim_attacks_are_rejected(
    basis_and_verification, attack
) -> None:
    basis, _ = basis_and_verification
    document = basis.to_document()
    attack(document)
    with pytest.raises(
        verifier.ConstructionK7Standard2048CoordinateBasisIndependentVerifierV13Error
    ):
        verifier.verify_standard_2048_coordinate_basis_bytes_independently_v13(
            _resign(document)
        )
