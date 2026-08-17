from __future__ import annotations

import pytest

from acfqp import construction_k7_layout_factorization_preregistration_v50 as pre
from acfqp.layout_factorized_campaign_core_v50 import (
    build_layout_factorized_campaign_document_v50,
)


@pytest.fixture(scope="module")
def development_campaign():
    config = pre.campaign_config_v50()
    config.update(
        {
            "modular_source_seeds": (599_101, 599_102, 599_103),
            "modular_target_seeds": tuple(range(599_301, 599_309)),
            "inventory_source_seeds": (599_201, 599_202, 599_203),
            "inventory_target_seeds": tuple(range(599_401, 599_409)),
        }
    )
    return build_layout_factorized_campaign_document_v50(config, "d" * 64)


def test_development_campaign_synthesizes_two_exact_stochastic_world_models(
    development_campaign,
) -> None:
    models = development_campaign["world_models"]
    assert set(models) == {
        "STOCHASTIC_MODULAR_ROUTING",
        "STOCHASTIC_INVENTORY_ASSEMBLY",
    }
    assert {"E06", "E07", "E12"} <= set(
        models["STOCHASTIC_MODULAR_ROUTING"]["compiled_program"]["used_opcode_names"]
    )
    assert {"E05", "E07", "E12"} <= set(
        models["STOCHASTIC_INVENTORY_ASSEMBLY"]["compiled_program"]["used_opcode_names"]
    )
    assert all(
        model["specialized_layout_discovery_pattern_count"] == 0
        and model["predeclared_layout_or_factor_roles"] == []
        for model in models.values()
    )


def test_development_campaign_layout_calibration_is_bounded_and_name_blind(
    development_campaign,
) -> None:
    calibrations = development_campaign["target_layout_calibrations"]
    assert len(calibrations) == 16
    assert max(row["support_labels"] for row in calibrations) <= pre.MAXIMUM_TARGET_LAYOUT_LABELS
    assert all(row["hidden_adapter_layout_accessed"] is False for row in calibrations)
    assert all(
        row["numeric_relation_outputs_reused_as_local_distinctions"] is False
        for row in calibrations
    )


def test_development_campaign_plans_all_matched_episodes_in_compiled_models(
    development_campaign,
) -> None:
    structural = development_campaign["structural_episodes"]
    strict = development_campaign["strict_episodes"]
    assert len(structural) == len(strict) == 16
    assert all(row["success"] for row in structural + strict)
    assert sum(row["execution_steps"] for row in structural) == sum(
        row["execution_steps"] for row in strict
    )
    assert all(row["planning_compute_events"] > 0 for row in structural + strict)


def test_development_campaign_local_ground_work_is_certificate_first(
    development_campaign,
) -> None:
    # The source modulus changes at the modular target, invalidating all four
    # relation inputs before any local raw support is queried.
    campaign = development_campaign
    assert len(campaign["failed_certificates"]) == 4
    assert len(campaign["local_distinctions"]) == 4
    assert all(
        row["ground_query_performed_before_failure"] is False
        for row in campaign["failed_certificates"]
    )
    assert all(
        row["query_after_failed_certificate"] is True
        for row in campaign["local_distinctions"]
    )
    assert sorted(next(iter(campaign["relation_overlay"].values()))) == [
        [8_001, 1],
        [8_009, 2],
        [8_021, 4],
        [8_039, 5],
    ]


def test_development_campaign_amortizes_sample_tax_and_keeps_gates_locked(
    development_campaign,
) -> None:
    sample = development_campaign["sample_tax"]
    assert sample["structural_total_support_labels"] < sample["strict_target_support_labels"]
    assert sample["strict_target_label_savings"] > 0
    assert sample["diagnostic_break_even_occurrences"] <= 16
    assert development_campaign["ood_rejection"]["prior_transfer_attempted"] is False
    assert development_campaign["ood_rejection"]["ood_outcome_execution_performed"] is False
    assert development_campaign["official_execution_allowed"] is False
    assert development_campaign["official_scalar_cost"] is None
    assert development_campaign["official_N_break_even"] is None
    assert development_campaign["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert development_campaign["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
