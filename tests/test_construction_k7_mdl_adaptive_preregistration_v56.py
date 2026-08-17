from __future__ import annotations

import hashlib

from acfqp import construction_k7_domain_registry_extension_v55 as domains_v55
from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp import construction_k7_mdl_adaptive_preregistration_v56 as pre


def test_v56_preregistration_is_frozen_content_addressed_and_outcome_free():
    value = pre.freeze_mdl_adaptive_preregistration_v56()
    assert pre.verify_mdl_adaptive_preregistration_v56(value) is value
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == (
        pre.EXPECTED_CANONICAL_SHA256
    )
    document = value.to_document()
    assert document["fresh_v56_registered_outcome_execution_performed"] is False
    assert document["claim_boundary"]["registered_outcome_observed"] is False


def test_v56_preregistration_removes_fixed_floor_and_block_before_outcomes():
    document = pre.freeze_mdl_adaptive_preregistration_v56().to_document()
    contract = document["mdl_adaptive_contract"]
    assert contract["fixed_minimum_candidate_label_floor"] is None
    assert contract["fixed_confirmation_block_size"] is None
    assert contract["candidate_synthesis_attempted_after_every_support_query"]
    assert document["matched_single_switch_arms"]["only_switched_variable"] == (
        "REGISTERED_FACTOR_CODE_CREDIT_UNITS"
    )
    assert set(document["target_families"]) == {
        "BALANCED_BATCH_REFINEMENT",
        "COUPLED_EXCHANGE",
        "generation_witness_available_to_constructor",
        "semantic_bridge_available_to_constructor",
    }


def test_v56_source_closure_and_seed_identity_are_current():
    document = pre.freeze_mdl_adaptive_preregistration_v56().to_document()
    expected = document["source_closure"]["source_facts"]
    actual = []
    for relative in pre.BOUND_SOURCE_PATHS:
        raw = (pre.SOURCE_ROOT / relative).read_bytes()
        actual.append(
            {
                "relative_path": relative,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    assert actual == expected
    assert document["source_closure"][
        "development_seed_identities_disjoint_from_registered_identities"
    ] is True
    assert domains_v56.K7_DOMAIN_TAG_EXTENSION_V56.isdisjoint(
        domains_v55.K7_DOMAIN_TAG_EXTENSION_V55
    )


def test_v56_preregistration_keeps_claims_locked():
    boundary = pre.freeze_mdl_adaptive_preregistration_v56().to_document()[
        "claim_boundary"
    ]
    assert boundary["arbitrary_domain_transfer_claimed"] is False
    assert boundary["global_exact_dynamics_claimed"] is False
    assert boundary["official_execution_allowed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["official_N_break_even"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert boundary["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
