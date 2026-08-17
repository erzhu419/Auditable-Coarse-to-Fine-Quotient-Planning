from __future__ import annotations

import hashlib
from fractions import Fraction

from acfqp import construction_k7_calibrated_mdl_preregistration_v57 as pre


def test_v57_preregistration_is_content_addressed_and_outcome_free():
    value = pre.freeze_calibrated_mdl_preregistration_v57()
    assert pre.verify_calibrated_mdl_preregistration_v57(value) is value
    assert value.preregistration_id == pre.PREREGISTRATION_ID
    assert len(value.canonical_bytes) == pre.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(value.canonical_bytes).hexdigest() == (
        pre.EXPECTED_CANONICAL_SHA256
    )
    document = value.to_document()
    assert document["fresh_v57_registered_outcome_execution_performed"] is False
    assert document["claim_boundary"]["registered_outcome_observed"] is False


def test_v57_preregisters_calibrated_stop_without_frontier_fallback():
    document = pre.freeze_calibrated_mdl_preregistration_v57().to_document()
    contract = document["calibrated_stopping_contract"]
    assert contract["fixed_minimum_candidate_label_floor"] is None
    assert contract["fixed_confirmation_block_size"] is None
    assert contract["fixed_confidence_reserve"] is None
    assert contract["reachable_frontier_exhaustion_stop_available"] is False
    assert contract["global_alpha"] == Fraction(1, 20)
    assert contract["anytime_valid_for_registered_predictive_null"]


def test_v57_source_closure_seeds_and_third_family_are_current():
    document = pre.freeze_calibrated_mdl_preregistration_v57().to_document()
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
    assert actual == document["source_closure"]["source_facts"]
    assert document["source_closure"][
        "development_seed_identities_disjoint_from_registered_identities"
    ]
    assert document["target_families"]["MAINTENANCE_CASCADE"][
        "new_third_partial_stochastic_family"
    ]


def test_v57_claims_remain_locked():
    boundary = pre.freeze_calibrated_mdl_preregistration_v57().to_document()[
        "claim_boundary"
    ]
    assert boundary["official_execution_allowed"] is False
    assert boundary["official_scalar_cost"] is None
    assert boundary["official_N_break_even"] is None
    assert boundary["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
    assert boundary["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
