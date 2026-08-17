from __future__ import annotations

import pytest

from acfqp import construction_k7_layout_factorization_preregistration_v50 as v50
from acfqp import phase3e_ids as ids
from acfqp.layout_factorized_campaign_core_v50r1 import (
    V50_FAILURE_ID,
    build_layout_factorized_campaign_document_v50r1,
)


def _domains() -> dict[str, str]:
    return {
        "preregistration": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PREREGISTRATION_V50R1_DOMAIN,
        "observation": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RAW_OBSERVATION_V50R1_DOMAIN,
        "layout": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LAYOUT_V50R1_DOMAIN,
        "program": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_PROGRAM_V50R1_DOMAIN,
        "support": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_DEPENDENCY_SUPPORT_V50R1_DOMAIN,
        "failed_certificate": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_FAILED_CERTIFICATE_V50R1_DOMAIN,
        "distinction": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_LOCAL_DISTINCTION_V50R1_DOMAIN,
        "episode": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_RECEDING_EPISODE_V50R1_DOMAIN,
        "sample_tax": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_SAMPLE_TAX_V50R1_DOMAIN,
        "ood": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_OOD_REJECTION_V50R1_DOMAIN,
        "campaign": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_CAMPAIGN_V50R1_DOMAIN,
        "verification": ids.CONSTRUCTION_K7_LAYOUT_FACTORIZATION_VERIFICATION_V50R1_DOMAIN,
    }


@pytest.fixture(scope="module")
def development_successor():
    config = v50.campaign_config_v50()
    config.update(
        {
            "domains": _domains(),
            "modular_source_seeds": (599_101, 599_102, 599_103),
            "modular_target_seeds": tuple(range(599_301, 599_309)),
            "inventory_source_seeds": (599_201, 599_202, 599_203),
            "inventory_target_seeds": tuple(range(599_401, 599_409)),
        }
    )
    return build_layout_factorized_campaign_document_v50r1(config, "d" * 64)


def test_v50r1_preserves_failure_and_applies_only_safe_terminal_correction(
    development_successor,
) -> None:
    correction = development_successor["successor_correction"]
    assert development_successor["frozen_failed_predecessor_id"] == V50_FAILURE_ID
    assert correction["predecessor_orchestration_code_reused_without_mutation"] is True
    assert correction["rebound_dependency_count"] == 1
    assert correction["caller_supplied_callback_present"] is False
    assert all(
        model["terminal_next_status_column_candidates_excluded"] is True
        and model["terminal_self_next_dependency_count"] == 0
        for model in development_successor["world_models"].values()
    )


def test_v50r1_development_campaign_retains_mainline_positive_conditions(
    development_successor,
) -> None:
    episodes = (
        development_successor["structural_episodes"]
        + development_successor["strict_episodes"]
    )
    assert len(episodes) == 32
    assert all(row["success"] for row in episodes)
    assert development_successor["sample_tax"]["strict_target_label_savings"] > 0
    assert all(
        row["query_after_failed_certificate"] is True
        for row in development_successor["local_distinctions"]
    )
    assert development_successor["ood_rejection"]["prior_transfer_attempted"] is False
    assert development_successor["official_execution_allowed"] is False
    assert development_successor["official_scalar_cost"] is None
    assert development_successor["official_N_break_even"] is None
    assert development_successor["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert development_successor["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
