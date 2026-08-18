from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_universal_mixture_preregistration_v58 as pre


def test_v58_preregistration_identity_and_source_closure_are_frozen():
    value = pre.freeze_universal_mixture_preregistration_v58()
    document = value.to_document()
    assert value.preregistration_id == document["preregistration_id"]
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == (
        pre.EXPECTED_CANONICAL_SHA256
    )
    assert document["source_closure"]["frozen_before_any_v58_registered_outcome"]
    assert document["fresh_v58_registered_outcome_execution_performed"] is False
    assert document["frozen_predecessors"]["implementation_commit"] == "d72231f"


def test_v58_preregistration_removes_bet_and_epoch_base_but_not_mdl_conversion():
    document = pre.freeze_universal_mixture_preregistration_v58().to_document()
    contract = document["universal_mixture_stopping_contract"]
    assert contract["betting_fraction_selected"] is False
    assert contract["success_evalue_multiplier_selected"] is False
    assert contract["epoch_spending_base_selected"] is False
    assert contract["predictive_evidence_to_mdl_credit_inherited_from_v57"] is True
    assert document["claim_boundary"]["predictive_evidence_to_mdl_credit_removed"] is False
    assert document["claim_boundary"]["next_required_scaffold_removal"] == (
        "REPLACE_HEURISTIC_MDL_UNITS_WITH_TRUE_BIT_CODELENGTH"
    )


def test_v58_preregistration_fixes_fresh_disjoint_targets_and_caps():
    document = pre.freeze_universal_mixture_preregistration_v58().to_document()
    targets = document["target_families"]
    assert len(targets["BALANCED_BATCH_REFINEMENT"]["target_seeds"]) == 32
    assert len(targets["COUPLED_EXCHANGE"]["target_seeds"]) == 32
    assert len(targets["MAINTENANCE_CASCADE"]["target_seeds"]) == 32
    assert targets["BALANCED_BATCH_REFINEMENT"]["maximum_acquisition_labels"] == 192
    assert targets["COUPLED_EXCHANGE"]["maximum_acquisition_labels"] == 224
    assert targets["MAINTENANCE_CASCADE"]["maximum_acquisition_labels"] == 288
    assert document["source_closure"][
        "development_seed_identities_disjoint_from_registered_identities"
    ]


def test_v58_preregistration_preserves_claim_locks_and_rejects_foreign_values():
    document = pre.freeze_universal_mixture_preregistration_v58().to_document()
    boundary = document["claim_boundary"]
    assert boundary["registered_outcome_observed"] is False
    assert boundary["official_execution_allowed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["official_N_break_even"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert boundary["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
    with pytest.raises(ValueError):
        pre.verify_universal_mixture_preregistration_v58(object())
