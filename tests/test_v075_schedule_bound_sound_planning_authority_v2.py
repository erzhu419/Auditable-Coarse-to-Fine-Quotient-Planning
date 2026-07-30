from __future__ import annotations

from dataclasses import fields
import hashlib
from pathlib import Path

import pytest

from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_schedule_bound_sound_planning_authority_v2 as bridge
from tests import test_v075_private_observer_boundary_v2 as observer_fixture
from tests import (
    test_v075_schedule_bound_acquisition_lifecycle_v2 as lifecycle_fixture,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-schedule-bound-planning-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


def _clone(value):
    forged = object.__new__(type(value))
    for item in fields(type(value)):
        if hasattr(value, item.name):
            object.__setattr__(forged, item.name, getattr(value, item.name))
    return forged


def _arguments(upstream, initial):
    return {
        "repository_root": REPOSITORY_ROOT,
        "profile": upstream["profile"],
        "expected_slot": upstream["slot"],
        "schedule": upstream["schedule"],
        "lineage": upstream["lineage"],
        "construction_authority": upstream["construction_authority"],
        "current_lifecycle": upstream["current"],
        "initial_lifecycle": initial,
    }


@pytest.fixture(scope="module")
def exact_graph():
    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture("schedule-bound-sound-planning")
    )
    return {
        "generated": generated,
        "salt": salt,
        "namespace": namespace,
        "authorization": authorization,
        "signer": signer,
    }


@pytest.fixture(scope="module")
def adaptive_upstream(exact_graph):
    upstream = lifecycle_fixture._build_upstream(
        exact_graph,
        arm=worker.V075WorkerArmV1.NO_PRIOR,
        marker="schedule-bound-sound-planning-adaptive",
    )
    return upstream, lifecycle_fixture._freeze(upstream)


@pytest.fixture(scope="module")
def direct_upstream(exact_graph):
    upstream = lifecycle_fixture._build_upstream(
        exact_graph,
        arm=worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND,
        marker="schedule-bound-sound-planning-direct",
    )
    return upstream, lifecycle_fixture._freeze(upstream)


@pytest.fixture(scope="module")
def adaptive_result(adaptive_upstream):
    upstream, initial = adaptive_upstream
    return bridge.freeze_v075_schedule_bound_sound_planning_authority_v2(
        **_arguments(upstream, initial)
    )


@pytest.fixture(scope="module")
def direct_result(direct_upstream):
    upstream, initial = direct_upstream
    return bridge.freeze_v075_schedule_bound_sound_planning_authority_v2(
        **_arguments(upstream, initial)
    )


def test_contract_and_production_flags_remain_locked():
    assert bridge.PROPOSED_CONTRACT_VERSION == "1.50.0"
    assert bridge.OFFICIAL_EXECUTION_ALLOWED is False
    assert bridge.PRODUCTION_AUTHORIZING is False
    assert bridge.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert bridge.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert bridge.PRIVATE_LAW_ACCESS_ALLOWED is False
    assert bridge.PER_DRAW_REPLAY_ALLOWED is False
    assert bridge.TARGET_ACCESS_ALLOWED is False


def test_adaptive_compiler_feeds_prior_free_planner_and_remains_noncertificate(
    adaptive_upstream,
    adaptive_result,
):
    upstream, initial = adaptive_upstream
    result = adaptive_result
    assert result.initial_lifecycle.result_id == initial.result_id
    assert result.compiler_output is not None
    assert result.numerical_proof is not None
    assert result.compiler_output.model == result.numerical_proof.model
    assert result.compiler_output.schedule_id == upstream["schedule"].schedule_id
    assert result.compiler_output.lineage_id == upstream["lineage"].lineage_id
    assert result.compiler_output.route is (
        planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
    )
    assert result.proposal_view_id == (
        upstream["schedule"].proposal_view.proposal_view_id
    )
    expected_terminal = (
        (
            bridge.V075ScheduleBoundPlanningTerminalCodeV2
            .CANDIDATE_AWAITING_INDEPENDENT_TOTAL_LIFT
        )
        if result.numerical_proof.outcome
        is planning_v2.V075NumericalOutcomeV2.CANDIDATE
        else (
            bridge.V075ScheduleBoundPlanningTerminalCodeV2
            .FAILED_FRONTIER_AWAITING_DYNAMIC_ACQUISITION
        )
    )
    assert result.terminal_code is expected_terminal
    document = result.to_document()
    assert document["terminal_scope"] == "CONSTRUCTION_ONLY"
    assert document["terminal_class"] == "ATTEMPT_CLOSURE_NONCERTIFICATE"
    assert document["initial_schedule_bound"] is True
    assert document["proposal_bound_in_occurrence_wrapper"] is True
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False
    assert document["official_execution_allowed"] is False
    assert document["private_law_access"] is False
    assert document["per_draw_records_read"] == 0
    if result.numerical_proof.outcome is (
        planning_v2.V075NumericalOutcomeV2.CANDIDATE
    ):
        assert document["candidate_awaiting_independent_total_lift"] is True
        assert document["candidate_is_not_certificate"] is True


def test_numerical_proof_does_not_contain_occurrence_or_proposal_identity(
    adaptive_upstream,
    adaptive_result,
):
    upstream, _initial = adaptive_upstream
    proof_bytes = adaptive_result.numerical_proof.canonical_bytes
    occurrence_id = upstream["schedule"].occurrence.occurrence_id.encode()
    proposal_id = (
        upstream["schedule"].proposal_view.proposal_view_id.encode()
    )
    assert occurrence_id not in proof_bytes
    assert proposal_id not in proof_bytes
    proof_document = adaptive_result.numerical_proof.to_document()
    assert proof_document["arm_field_present"] is False
    assert proof_document["proposal_field_present"] is False
    assert proof_document["source_provenance_field_present"] is False
    assert proof_document["occurrence_field_present"] is False


def test_direct_initial_stage_is_typed_deferral_without_model_or_validation(
    direct_upstream,
    direct_result,
):
    upstream, _initial = direct_upstream
    assert direct_result.terminal_code is (
        bridge.V075ScheduleBoundPlanningTerminalCodeV2
        .PLANNING_DEFERRED_AWAITING_CHILD_EXPANSION
    )
    assert direct_result.compiler_output is None
    assert direct_result.numerical_proof is None
    assert direct_result.proposal_view_id is None
    assert upstream["schedule"].proposal_view is None
    assert direct_result.initial_lifecycle.counters.validation_batch_count == 0
    document = direct_result.to_document()
    assert document["numerical_model_id"] is None
    assert document["numerical_proof_id"] is None
    assert document["planning_executed"] is False
    assert document["planning_deferred"] is True
    assert document["child_expansion_complete"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False


@pytest.mark.parametrize(
    "fixture_name,result_fixture_name",
    [
        ("adaptive_upstream", "adaptive_result"),
        ("direct_upstream", "direct_result"),
    ],
)
def test_bytes_verifier_rebuilds_all_upstream_witnesses(
    fixture_name,
    result_fixture_name,
    request,
):
    upstream, initial = request.getfixturevalue(fixture_name)
    result = request.getfixturevalue(result_fixture_name)
    replayed, verification = (
        bridge.verify_v075_schedule_bound_sound_planning_result_bytes_v2(
            **_arguments(upstream, initial),
            claimed_bytes=result.canonical_bytes,
        )
    )
    assert replayed.result_id == result.result_id
    assert verification.result_id == result.result_id
    assert verification.initial_lifecycle_id == initial.result_id
    assert verification.to_document()["canonical_result_bytes_replayed"] is True
    with pytest.raises(
        bridge.V075ScheduleBoundSoundPlanningV2InvariantViolation
    ):
        bridge.verify_v075_schedule_bound_sound_planning_result_bytes_v2(
            **_arguments(upstream, initial),
            claimed_bytes=result.canonical_bytes + b" ",
        )


def test_object_new_and_result_digest_attacks_fail_exact_byte_replay(
    direct_upstream,
    direct_result,
):
    upstream, initial = direct_upstream
    forged = _clone(direct_result)
    object.__setattr__(forged, "_result_id", _id("forged-result"))
    with pytest.raises(
        bridge.V075ScheduleBoundSoundPlanningV2InvariantViolation
    ):
        bridge.verify_v075_schedule_bound_sound_planning_result_bytes_v2(
            **_arguments(upstream, initial),
            claimed_bytes=forged.canonical_bytes,
        )


def test_lineage_digest_and_cross_arm_transplants_are_rejected(
    adaptive_upstream,
    direct_upstream,
    adaptive_result,
):
    adaptive, adaptive_initial = adaptive_upstream
    direct, direct_initial = direct_upstream

    forged_lineage = _clone(adaptive["lineage"])
    object.__setattr__(
        forged_lineage,
        "authorization_bytes_sha256",
        _id("foreign-authorization-digest"),
    )
    digest_attack = dict(adaptive)
    digest_attack["lineage"] = forged_lineage
    with pytest.raises(
        bridge.V075ScheduleBoundSoundPlanningV2InvariantViolation
    ):
        bridge.freeze_v075_schedule_bound_sound_planning_authority_v2(
            **_arguments(digest_attack, adaptive_initial)
        )

    with pytest.raises(
        bridge.V075ScheduleBoundSoundPlanningV2InvariantViolation
    ):
        bridge.verify_v075_schedule_bound_sound_planning_result_bytes_v2(
            **_arguments(direct, direct_initial),
            claimed_bytes=adaptive_result.canonical_bytes,
        )


def test_production_entry_is_unconditionally_not_ready(monkeypatch):
    monkeypatch.setattr(bridge, "OFFICIAL_EXECUTION_ALLOWED", True)
    monkeypatch.setattr(bridge, "PRODUCTION_AUTHORIZING", True)
    with pytest.raises(
        bridge.V075ScheduleBoundSoundPlanningProductionV2NotReady
    ):
        bridge.open_v075_production_schedule_bound_sound_planning_authority_v2()
