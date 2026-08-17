from __future__ import annotations

import pytest

from acfqp import phase3e_ids as ids
from acfqp.cross_schema_factor_campaign_core_v51 import (
    build_cross_schema_factor_campaign_document_v51,
)
from acfqp.generic_cross_schema_factor_library_v7 import (
    compile_cross_schema_factor_library_v7,
    discover_factor_boundaries_v7,
)
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def _domains() -> dict[str, str]:
    return {
        "preregistration": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_PREREGISTRATION_V51_DOMAIN,
        "observation": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_RAW_OBSERVATION_V51_DOMAIN,
        "factor_boundary": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_BOUNDARY_V51_DOMAIN,
        "factor_library": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_LIBRARY_V51_DOMAIN,
        "program": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_PROGRAM_V51_DOMAIN,
        "support": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_SUPPORT_V51_DOMAIN,
        "failed_certificate": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_FAILED_CERTIFICATE_V51_DOMAIN,
        "distinction": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_LOCAL_DISTINCTION_V51_DOMAIN,
        "episode": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_EPISODE_V51_DOMAIN,
        "sample_tax": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_SAMPLE_TAX_V51_DOMAIN,
        "ood": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_OOD_REJECTION_V51_DOMAIN,
        "campaign": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_CAMPAIGN_V51_DOMAIN,
        "verification": ids.CONSTRUCTION_K7_CROSS_SCHEMA_FACTOR_VERIFICATION_V51_DOMAIN,
    }


def _config() -> dict:
    return {
        "domains": _domains(),
        "terminal_tokens": {"A": 9_001, "F": 9_007, "S": 9_011},
        "source_stage_count": 6,
        "source_primary_base": 2,
        "source_seeds": (699_101, 699_102, 699_103),
        "target_stage_count": 7,
        "target_primary_base": 5,
        "target_seeds": tuple(range(699_301, 699_309)),
        "maximum_source_labels_per_occurrence": 512,
        "maximum_target_layout_labels": 32,
        "maximum_relation_output_candidate": 32,
        "minimum_reused_factor_count": 3,
    }


@pytest.fixture(scope="module")
def development_campaign():
    return build_cross_schema_factor_campaign_document_v51(_config(), "d" * 64)


def test_v51_domains_are_registered_and_unique() -> None:
    domains = list(_domains().values())
    assert len(domains) == len(set(domains)) == 13
    assert set(domains) <= PHASE3E_DOMAIN_TAGS


def test_factor_boundaries_and_library_are_anonymous_and_cross_schema() -> None:
    def model(name: str, width: int, fields: int) -> dict:
        program = {
            "program_id": name * 64,
            "state_width": width,
            "action_field_width": fields,
            "compiled_assignments": [
                {
                    "target_column": width - 1,
                    "result_type": "FINITE_INT_SUPPORT",
                    "expression": [
                        "E07",
                        ["E00", width - 1],
                        ["E05", ["E00", width - 1], ["E01", fields - 1]],
                    ],
                }
            ],
        }
        return {"compiled_program": program}

    models = {"M0": model("a", 7, 5), "M1": model("b", 9, 6)}
    library = compile_cross_schema_factor_library_v7(
        models, factor_domain=_domains()["factor_library"]
    )
    assert library["semantic_names_used"] is False
    assert library["caller_selected_factor_roles"] == []
    assert library["cross_schema_subprograms"][0]["source_schema_pairs"] == [
        [7, 5],
        [9, 6],
    ]
    boundary = discover_factor_boundaries_v7(
        models["M0"]["compiled_program"],
        factor_domain=_domains()["factor_boundary"],
    )
    assert boundary["predeclared_factor_roles"] == []


def test_v51_composes_factors_into_higher_order_stochastic_world_model(
    development_campaign,
) -> None:
    model = development_campaign["higher_order_partial_stochastic_world_model"]
    composed = model["factor_composed_model"]
    fallback = model["fallback_layout_model"]["compiled_program"]
    assert composed["reused_factor_count"] == 5
    assert composed["all_reused_factors_originated_in_multiple_source_schema_pairs"] is True
    assert max(row["selected_composition_depth"] for row in fallback["candidate_evaluations"]) >= 2
    assert "E07" in fallback["used_opcode_names"]


def test_v51_plans_held_out_episodes_and_recovers_only_after_failure(
    development_campaign,
) -> None:
    assert len(development_campaign["structural_episodes"]) == 8
    assert len(development_campaign["strict_episodes"]) == 8
    assert all(
        row["success"]
        for row in development_campaign["structural_episodes"]
        + development_campaign["strict_episodes"]
    )
    assert len(development_campaign["failed_certificates"]) == 6
    assert len(development_campaign["local_distinctions"]) == 6
    assert all(
        row["ground_query_performed_before_failure"] is False
        for row in development_campaign["failed_certificates"]
    )
    assert all(
        row["query_after_failed_certificate"] is True
        for row in development_campaign["local_distinctions"]
    )


def test_v51_preserves_ood_and_official_locks_and_cumulative_sample_reduction(
    development_campaign,
) -> None:
    tax = development_campaign["sample_tax"]
    assert tax["cumulative_structural_labels"] == 646
    assert tax["cumulative_strict_labels"] == 814
    assert tax["cumulative_label_reduction"] == 168
    assert development_campaign["ood_rejection"]["prior_transfer_attempted"] is False
    assert development_campaign["ood_rejection"]["ood_outcome_execution_performed"] is False
    assert development_campaign["official_execution_allowed"] is False
    assert development_campaign["official_scalar_cost"] is None
    assert development_campaign["official_N_break_even"] is None
    assert development_campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert development_campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
