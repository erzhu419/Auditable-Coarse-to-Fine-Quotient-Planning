from __future__ import annotations

from dataclasses import fields
from fractions import Fraction
import inspect

import pytest

from acfqp import v075_batch_native_total_lift_authority_v1 as bridge
from acfqp import v075_private_environment_generation_profile_v1 as private_env
from acfqp import v075_public_campaign_authority_v1 as public
from tests.test_v075_total_lift_authority_v1 import _exact_rows


def _rank_one_exact_rows():
    context = (
        public.freeze_v075_public_family_generation_v1()
        .replicate_contexts[0]
    )
    return context, _exact_rows(context, ((1, Fraction(1)),))


def test_readiness_records_passed_construction_e2e_but_stays_locked() -> None:
    result = (
        bridge.assess_v075_batch_native_total_lift_production_readiness_v1()
    )
    assert result.blockers == tuple(
        sorted(
            (
                bridge.PRODUCTION_RECONCILIATION_INTEGRATION_BLOCKER,
                bridge.PRODUCTION_WORKER_INTEGRATION_BLOCKER,
            )
        )
    )
    document = result.to_document()
    assert document["construction_multistage_e2e_gate_status"] == "PASSED"
    assert (
        document[
            "production_exact_replay_candidate_result_implemented"
        ]
        is True
    )
    assert document["production_worker_integration_complete"] is False
    assert document["campaign_reconciliation_complete"] is False
    assert document["production_total_lift_execution_allowed"] is False
    assert document["official_execution_allowed"] is False
    assert bridge.PRODUCTION_TOTAL_LIFT_EXECUTION_ALLOWED is False
    assert bridge.PER_DRAW_CAPABILITY_EXPANSION_ALLOWED is False
    assert "lifecycle_transcript_id" in (
        result.required_lifecycle_closure_fields
    )
    assert "underlying_session_closure_id" in (
        result.required_lifecycle_closure_fields
    )


def test_operational_bridge_has_no_backend_or_planner_reexecution() -> None:
    source = inspect.getsource(
        bridge.freeze_v075_batch_native_total_lift_lineage_v1
    )
    assert "compile_v075_batch_native_statistical_backend_v1" not in source
    assert "plan_v075_batch_native_route_v1" not in source
    assert "verify_v075_batch_native_backend_result_v1" not in source
    assert "verify_v075_abstract_planner_result_v1" not in source
    assert (
        bridge.CANONICAL_BACKEND_RECOMPUTATION_IN_OPERATIONAL_BRIDGE
        is False
    )
    assert (
        bridge.CANONICAL_PLANNER_RECOMPUTATION_IN_OPERATIONAL_BRIDGE
        is False
    )
    annotations = repr(
        {
            item.name: item.type
            for item in fields(bridge.V075BatchObservedRowBindingV1)
        }
    )
    assert "ObservationCapability" not in annotations


def test_h1_other_is_policy_abort_while_failure_stays_environmental() -> None:
    _context, rows = _rank_one_exact_rows()
    child = next(
        item
        for item in rows
        if item.row_binding.remaining_horizon == 1
        and any(not atom.atom.failure for atom in item.atoms)
    )
    environment, modeled, aborted, recurse = (
        bridge._partition_exact_row_atoms(
            exact_row=child,
            modeled_outcome_keys=(),
        )
    )
    assert set(environment) == {
        item.atom_id for item in child.atoms if item.atom.failure
    }
    assert set(aborted) == {
        item.atom_id for item in child.atoms if not item.atom.failure
    }
    assert modeled == ()
    assert recurse == {}

    full_nonfailure_support = tuple(
        sorted(
            {
                (
                    item.next_state_id,
                    item.atom.failure,
                    item.atom.terminal,
                )
                for item in child.atoms
                if not item.atom.failure
            }
        )
    )
    environment2, modeled2, aborted2, recurse2 = (
        bridge._partition_exact_row_atoms(
            exact_row=child,
            modeled_outcome_keys=full_nonfailure_support,
        )
    )
    assert environment2 == environment
    assert set(modeled2) == {
        item.atom_id for item in child.atoms if not item.atom.failure
    }
    assert aborted2 == ()
    assert recurse2 == {}


def test_ground_ties_use_action_triple_signature_not_action_objects() -> None:
    smaller = bridge._GroundPointV1(
        Fraction(1),
        Fraction(1, 10),
        (("0" * 64, 1, (0, 1, 0)),),
    )
    larger = bridge._GroundPointV1(
        Fraction(1),
        Fraction(1, 10),
        (("0" * 64, 1, (0, 1, 1)),),
    )
    assert bridge._pareto_ground((larger, smaller)) == (smaller,)
    context, rows = _rank_one_exact_rows()
    first = bridge._exact_ground_optimum(
        context=context,
        rows=rows,
        risk_tolerance=Fraction(1),
    )
    second = bridge._exact_ground_optimum(
        context=context,
        rows=rows,
        risk_tolerance=Fraction(1),
    )
    assert first == second
    assert first is not None
    assert all(
        type(action) is tuple and len(action) == 3
        for _state_id, _horizon, action in first.policy_signature
    )


def test_production_exact_replay_rejects_duck_and_construction_inputs() -> None:
    generated = private_env.generate_v075_private_environment_v1(
        profile=private_env.freeze_v075_private_environment_generation_profile_v1(),
        secret_generation_seed=bytes(range(32)),
    )
    with pytest.raises(
        bridge.V075BatchNativeTotalLiftInvariantViolation,
        match="exact reveal-attested",
    ):
        bridge.mint_v075_batch_native_production_exact_replay_v1(
            lineage=object(),  # type: ignore[arg-type]
            authority=object(),
            private_salt=b"x" * 32,
            private_environment=generated,
        )
