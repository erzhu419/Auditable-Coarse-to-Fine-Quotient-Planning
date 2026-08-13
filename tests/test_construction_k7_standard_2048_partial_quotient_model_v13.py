from __future__ import annotations

import ast
import copy
from fractions import Fraction
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_partial_quotient_model_v13 as model_v13


@pytest.fixture(scope="module")
def model() -> model_v13.Standard2048PartialQuotientModelV13:
    return model_v13.build_standard_2048_partial_quotient_model_v13()


def test_source_only_partial_model_is_content_addressed_and_replayable(model) -> None:
    assert model_v13.verify_standard_2048_partial_quotient_model_v13(model) is model
    document = model.to_document()
    assert model.partial_quotient_model_id == model_v13.PARTIAL_QUOTIENT_MODEL_ID
    assert document["selected_candidate_keys"] == ["rank_histogram"]
    assert document["partial_row_count"] == 508
    assert document["represented_coordinate_count"] == 439
    assert document["source_observation_count"] == 512
    assert document["source_duplicate_condition_observation_count"] == 4
    assert document["source_transition_congruence_contradiction_count"] == 0
    assert document["source_rows_only_construct_model"] is True
    assert document["validation_rows_added_to_model"] is False


def test_low_heldout_coverage_is_reported_instead_of_hidden(model) -> None:
    document = model.to_document()
    assert document["validation_observation_count"] == 256
    assert document["validation_covered_condition_count"] == 1
    assert document["validation_matching_covered_condition_count"] == 1
    assert document["validation_conflicting_covered_condition_count"] == 0
    assert document["validation_uncovered_condition_count"] == 255
    assert document["validation_coverage_fraction"] == Fraction(1, 256)
    assert document["finite_heldout_coverage_is_not_global_lumpability"] is True


def test_unknown_conditions_and_successor_mass_remain_explicit(model) -> None:
    document = model.to_document()
    assert document["unknown_conditions_retained_as_unknown"] is True
    assert document["unobserved_successor_mass_retained_as_unknown"] is True
    assert document["model_can_guide_planning_and_acquisition"] is True
    assert document["model_can_issue_sound_plan_certificate"] is False
    assert document["exact_local_obligation_closure_still_required"] is True
    assert all(
        row["unobserved_successor_mass_retained_as_unknown"] is True
        and row["probability_assignment_present"] is False
        and row["sound_certificate_authority_present"] is False
        for row in document["rows"]
    )


def test_model_constructor_does_not_import_target_campaign_or_ground_kernel() -> None:
    tree = ast.parse(Path(model_v13.__file__).read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "acfqp.domains.standard_2048" not in imports
    assert all("campaign" not in (name or "") for name in imports)


def test_model_and_gate_claim_tampering_is_rejected(model) -> None:
    document = model.to_document()
    assert document["target_execution_performed"] is False
    assert document["local_ground_refinement_performed"] is False
    assert document["sample_tax_reduction_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"

    forged = copy.copy(model)
    object.__setattr__(forged, "partial_quotient_model_id", "f" * 64)
    with pytest.raises(
        model_v13.ConstructionK7Standard2048PartialQuotientModelV13Error
    ):
        model_v13.verify_standard_2048_partial_quotient_model_v13(forged)
    with pytest.raises(
        model_v13.ConstructionK7Standard2048PartialQuotientModelV13Error
    ):
        model_v13.Standard2048PartialQuotientModelV13(
            object(),
            model.canonical_bytes,
            model.partial_quotient_model_id,
            model.coordinate_basis_id,
        )
