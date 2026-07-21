from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from acfqp.general_local_solver import CERTIFIED
from acfqp.phase3e_model_failure_consumer_v1 import (
    prepare_phase3e_from_model_failure_v1,
)
from acfqp.phase3e_transaction2_feasibility_v1 import (
    OUTCOME,
    REMAINING_OBLIGATION,
    REQUIRED_NEW_FIXTURE_PROPERTIES,
    GroundDerivedTransactionTwoFeasibilityAuditV1,
    TransactionTwoFeasibilityV1Error,
    audit_canonical_h2_transaction_two_feasibility_v1,
    verify_canonical_h2_transaction_two_feasibility_audit_v1,
)
from tests.test_phase3e_model_failure_consumer_v1 import failed_prefix_inputs


def _prepared(failed_prefix_inputs):
    _source, _execution, prefix, ground, cas, manifest, cardinality = (
        failed_prefix_inputs
    )
    return prepare_phase3e_from_model_failure_v1(
        prefix,
        ground,
        runtime_manifest=manifest,
        runtime_cardinality=cardinality,
        runtime_cas=cas,
    )


def test_canonical_h2_ground_replay_proves_transaction_two_is_unreachable(
    failed_prefix_inputs,
) -> None:
    prepared = _prepared(failed_prefix_inputs)
    assert prepared.selected_factory.construction_accounting is None

    audit = audit_canonical_h2_transaction_two_feasibility_v1(prepared)

    assert audit.outcome == OUTCOME
    assert audit.remaining_obligation == REMAINING_OBLIGATION
    assert audit.required_new_fixture_properties == REQUIRED_NEW_FIXTURE_PROPERTIES
    assert audit.solver_outcome == CERTIFIED
    assert audit.post_audit_outcome == "CERTIFIED"
    assert audit.risk_tolerance == Fraction(1, 20)
    assert audit.lifted_failure_upper == Fraction(397, 20000)
    assert audit.lifted_failure_upper < audit.risk_tolerance
    assert audit.regret_upper == 0
    assert audit.postaudit_issue_count == 0
    assert audit.unresolved_ground_distinction_count == 0
    assert audit.materialization_ground_steps == 16
    assert audit.materialization_positive_outcomes == 64
    assert audit.solver_policy_assignments == 257
    assert audit.patched_decision_count == 8
    assert audit.postaudit_ground_steps == 8
    assert audit.transaction_two_authorized is False
    assert audit.production_obligation_closed is False
    assert audit.evaluation_only is True
    assert audit.ground_replay_used is True
    assert audit.j0_used is False
    assert audit.test_only_semantic_finish_used is False
    assert audit.caller_supplied_hashes_used is False
    assert audit.official_execution_allowed is False
    # The feasibility audit evaluates the registered tail; it never consumes
    # the one-shot sealed route factory or manufactures an execution receipt.
    assert prepared.selected_factory.construction_accounting is None
    assert GroundDerivedTransactionTwoFeasibilityAuditV1.from_dict(
        audit.to_dict()
    ) == audit


def test_transaction_two_feasibility_verifier_replays_full_ground_evidence(
    failed_prefix_inputs,
) -> None:
    prepared = _prepared(failed_prefix_inputs)
    claimed = audit_canonical_h2_transaction_two_feasibility_v1(prepared)
    assert (
        verify_canonical_h2_transaction_two_feasibility_audit_v1(
            prepared, claimed
        )
        == claimed
    )

    attacked = claimed.to_dict()
    attacked["feasibility_audit_id"] = "0" * 64
    with pytest.raises(
        TransactionTwoFeasibilityV1Error,
        match="ID mismatch",
    ):
        GroundDerivedTransactionTwoFeasibilityAuditV1.from_dict(attacked)


def test_transaction_two_feasibility_artifact_cannot_hide_remaining_obligation(
    failed_prefix_inputs,
) -> None:
    prepared = _prepared(failed_prefix_inputs)
    audit = audit_canonical_h2_transaction_two_feasibility_v1(prepared)

    for attack in (
        {"transaction_two_authorized": True},
        {"production_obligation_closed": True},
        {"evaluation_only": False},
        {"j0_used": True},
        {"test_only_semantic_finish_used": True},
        {"caller_supplied_hashes_used": True},
        {"official_execution_allowed": True},
        {"required_new_fixture_properties": ()},
    ):
        with pytest.raises(
            TransactionTwoFeasibilityV1Error,
            match="overclaims",
        ):
            replace(audit, **attack)
