from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_cross_schema_factor_preregistration_v51 as pre
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS


def test_v51_preregistration_is_outcome_free_and_content_addressed() -> None:
    frozen = pre.freeze_cross_schema_factor_preregistration_v51()
    assert pre.verify_cross_schema_factor_preregistration_v51(frozen) is frozen
    assert frozen.preregistration_id == pre.PREREGISTRATION_ID
    assert len(frozen.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(frozen.canonical_bytes).hexdigest() == pre.EXPECTED_CANONICAL_SHA256
    document = frozen.to_document()
    assert document["fresh_v51_registered_outcome_execution_performed"] is False
    assert document["source_closure"]["frozen_before_any_v51_registered_outcome"] is True
    assert document["frozen_predecessor"]["v50r1_campaign_id"] == pre.V50R1_CAMPAIGN_ID


def test_v51_preregisters_fresh_factor_transfer_and_held_out_identities() -> None:
    document = pre.freeze_cross_schema_factor_preregistration_v51().to_document()
    target = document["target_domain"]
    seeds = target["source_seeds"] + target["target_seeds"]
    assert len(seeds) == len(set(seeds)) == 11
    assert all(seed // 1_000 == 511 for seed in seeds)
    assert target["raw_state_width"] == 10
    assert target["raw_action_field_width"] == 6
    assert document["cross_schema_library"]["source_schema_pairs"] == [[7, 5], [9, 6]]
    assert document["factor_boundary_discovery"]["predeclared_factor_roles"] == []
    assert document["program_construction"]["factor_prior_sample_savings_claimed_without_ablation"] is False


def test_v51_source_closure_domains_and_claim_locks_are_exact() -> None:
    document = pre.freeze_cross_schema_factor_preregistration_v51().to_document()
    facts = document["source_closure"]["source_facts"]
    assert [row["relative_path"] for row in facts] == list(pre.BOUND_SOURCE_PATHS)
    for row in facts:
        raw = (pre.SOURCE_ROOT / row["relative_path"]).read_bytes()
        assert len(raw) == row["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
    domains = list(pre.FUTURE_DOMAINS.values())
    assert len(domains) == len(set(domains)) == 13
    assert set(domains) <= PHASE3E_DOMAIN_TAGS
    boundary = document["claim_boundary"]
    assert boundary["official_execution_allowed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["official_N_break_even"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert boundary["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"


def test_v51_preregistration_rejects_foreign_values_and_mutation() -> None:
    frozen = pre.freeze_cross_schema_factor_preregistration_v51()
    with pytest.raises(pre.ConstructionK7CrossSchemaFactorPreregistrationV51Error):
        pre.CrossSchemaFactorPreregistrationV51(
            object(), frozen.canonical_bytes, frozen.preregistration_id
        )
    object.__setattr__(frozen, "preregistration_id", "f" * 64)
    with pytest.raises(pre.ConstructionK7CrossSchemaFactorPreregistrationV51Error):
        pre.verify_cross_schema_factor_preregistration_v51(frozen)
