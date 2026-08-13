from __future__ import annotations

import copy

import pytest

from acfqp import construction_k7_standard_2048_coordinate_basis_v13 as basis_v13
from acfqp import construction_k7_standard_2048_coordinate_preregistration_v13 as prereg_v13
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def evidence() -> basis_v13.Standard2048CoordinateBasisEvidenceV13:
    return basis_v13.build_standard_2048_coordinate_basis_v13()


def test_raw_archives_and_source_selected_basis_are_frozen(
    evidence: basis_v13.Standard2048CoordinateBasisEvidenceV13,
) -> None:
    assert basis_v13.verify_standard_2048_coordinate_basis_v13(evidence) is evidence
    document = evidence.to_document()
    source = document["source_archive"]
    validation = document["validation_archive"]
    selected = document["basis"]
    assert source["coordinate_observation_archive_id"] == basis_v13.SOURCE_ARCHIVE_ID
    assert validation["coordinate_observation_archive_id"] == basis_v13.VALIDATION_ARCHIVE_ID
    assert source["observation_count"] == 512
    assert validation["observation_count"] == 256
    assert source["stream_seed"] != validation["stream_seed"]
    assert selected["coordinate_basis_id"] == basis_v13.COORDINATE_BASIS_ID
    assert tuple(selected["selected_candidate_keys"]) == ("rank_histogram",)
    assert selected["selected_basis_cardinality"] == 1
    assert selected["heldout_validation_passed"] is True
    assert selected["result_classification"] == (
        "POSITIVE_REGISTERED_COORDINATE_SYNTHESIS_RESULT"
    )


def test_finite_congruence_is_not_promoted_to_a_sound_certificate(
    evidence: basis_v13.Standard2048CoordinateBasisEvidenceV13,
) -> None:
    selected = evidence.to_document()["basis"]
    assert selected["source_congruence_witness"] == {
        "observation_count": 512,
        "distinct_condition_count": 508,
        "duplicate_condition_count": 4,
        "transition_congruence_contradiction_count": 0,
        "first_contradiction": None,
    }
    assert selected["validation_congruence_witness"] == {
        "observation_count": 256,
        "distinct_condition_count": 256,
        "duplicate_condition_count": 0,
        "transition_congruence_contradiction_count": 0,
        "first_contradiction": None,
    }
    assert selected["finite_observation_congruence_not_global_lumpability_proof"] is True
    assert selected["statistical_basis_can_issue_sound_plan_certificate"] is False
    assert selected["exact_local_obligation_closure_still_required"] is True
    assert selected["target_execution_performed"] is False
    assert selected["sample_tax_reduction_claimed"] is False


def test_selector_does_not_call_the_ground_kernel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observations = basis_v13.acquire_standard_2048_coordinate_observations_v13()

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("selector touched the exact ground kernel")

    monkeypatch.setattr(basis_v13, "step_v1", forbidden)
    selected = basis_v13.synthesize_standard_2048_coordinate_basis_v13(observations)
    assert selected.selected_candidate_keys == ("rank_histogram",)


def test_validation_failure_cannot_change_source_selection() -> None:
    observations = basis_v13.acquire_standard_2048_coordinate_observations_v13()
    attacked = observations.to_document()
    validation = attacked["validation_archive"]
    first = validation["rows"][0]
    conflicting = validation["rows"][1]
    conflicting["pre_state"] = copy.deepcopy(first["pre_state"])
    conflicting["action"] = first["action"]
    conflicting["spawned_cell"] = first["spawned_cell"]
    conflicting["spawned_rank"] = first["spawned_rank"]
    conflicting["merge_score"] = first["merge_score"] + 1
    payload = {
        key: value
        for key, value in validation.items()
        if key != "coordinate_observation_archive_id"
    }
    validation["coordinate_observation_archive_id"] = content_id(
        prereg_v13.FUTURE_DOMAINS["observation_archive"], payload
    )
    forged = basis_v13.Standard2048CoordinateObservationEvidenceV13(
        basis_v13._OBSERVATION_ISSUER,
        canonical_json_bytes(attacked),
        attacked["source_archive"]["coordinate_observation_archive_id"],
        validation["coordinate_observation_archive_id"],
    )
    selected = basis_v13.synthesize_standard_2048_coordinate_basis_v13(forged)
    result = selected.to_document()["basis"]
    assert tuple(result["selected_candidate_keys"]) == ("rank_histogram",)
    assert result["heldout_validation_passed"] is False
    assert result["result_classification"] == (
        "NEGATIVE_REGISTERED_COORDINATE_SYNTHESIS_RESULT"
    )


def test_archive_tampering_and_fully_resigned_replay_are_rejected() -> None:
    observations = basis_v13.acquire_standard_2048_coordinate_observations_v13()
    forged = copy.copy(observations)
    attacked = observations.to_document()
    attacked["source_archive"]["rows"][0]["merge_score"] += 1
    object.__setattr__(forged, "canonical_bytes", canonical_json_bytes(attacked))
    with pytest.raises(basis_v13.ConstructionK7Standard2048CoordinateBasisV13Error):
        basis_v13.synthesize_standard_2048_coordinate_basis_v13(forged)

    source = attacked["source_archive"]
    payload = {
        key: value
        for key, value in source.items()
        if key != "coordinate_observation_archive_id"
    }
    source["coordinate_observation_archive_id"] = content_id(
        prereg_v13.FUTURE_DOMAINS["observation_archive"], payload
    )
    resigned = basis_v13.Standard2048CoordinateObservationEvidenceV13(
        basis_v13._OBSERVATION_ISSUER,
        canonical_json_bytes(attacked),
        source["coordinate_observation_archive_id"],
        attacked["validation_archive"]["coordinate_observation_archive_id"],
    )
    with pytest.raises(basis_v13.ConstructionK7Standard2048CoordinateBasisV13Error):
        basis_v13.verify_standard_2048_coordinate_observations_v13(resigned)


def test_basis_object_and_official_gate_locks_reject_tampering(
    evidence: basis_v13.Standard2048CoordinateBasisEvidenceV13,
) -> None:
    document = evidence.to_document()
    selected = document["basis"]
    assert selected["official_execution_allowed"] is False
    assert selected["official_scalar_cost"] is None
    assert selected["official_N_break_even"] is None
    assert selected["counter_completeness_gate_status"] == "NOT_RUN"
    assert selected["workload_economics_gate_status"] == "NOT_RUN"

    forged = copy.copy(evidence)
    object.__setattr__(forged, "coordinate_basis_id", "f" * 64)
    with pytest.raises(basis_v13.ConstructionK7Standard2048CoordinateBasisV13Error):
        basis_v13.verify_standard_2048_coordinate_basis_v13(forged)
    with pytest.raises(basis_v13.ConstructionK7Standard2048CoordinateBasisV13Error):
        basis_v13.Standard2048CoordinateBasisEvidenceV13(
            object(),
            evidence.canonical_bytes,
            evidence.source_archive_id,
            evidence.validation_archive_id,
            evidence.coordinate_basis_id,
            evidence.selected_candidate_keys,
        )
