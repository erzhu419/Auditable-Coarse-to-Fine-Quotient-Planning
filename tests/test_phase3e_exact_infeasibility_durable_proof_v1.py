from __future__ import annotations

import copy
import dataclasses
import hashlib
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import pytest

import acfqp.phase3e_exact_infeasibility_durable_proof_v1 as durable
from acfqp.core import Outcome, QuerySpec
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    run_ground_fallback_search_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"


@pytest.fixture(scope="module")
def proof_bytes() -> bytes:
    return durable.issue_phase3e_exact_infeasibility_durable_proof_v1(
        CANONICAL_BUNDLE
    )


def _document(proof_bytes: bytes) -> dict:
    document = loads_canonical_json(proof_bytes)
    assert type(document) is dict
    return document


def _resign(document: dict) -> bytes:
    payload = copy.deepcopy(document)
    payload.pop("durable_exact_infeasibility_proof_id", None)
    payload["durable_exact_infeasibility_proof_id"] = durable._id(
        durable.PROOF_DOMAIN, payload
    )
    return canonical_json_bytes(payload)


def _rebind_kernel_build_identity(document: dict) -> bytes:
    kernel_id = durable._id(durable.KERNEL_DOMAIN, document["kernel_profile"])
    document["build_epoch"]["kernel_id"] = kernel_id
    build_id = durable._id(durable.BUILD_EPOCH_DOMAIN, document["build_epoch"])
    identity = durable.DurableExactInfeasibilityIdentityV1(
        document["identity"]["structural_id"],
        document["identity"]["query_id"],
        build_id,
        kernel_id,
        document["identity"]["threshold_profile_id"],
        document["identity"]["reward_profile_id"],
        document["identity"]["policy_class_id"],
        document["identity"]["complete_search_profile_id"],
    )
    document["identity"] = identity.to_dict()
    return _resign(document)


def test_canonical_proof_is_self_contained_exact_and_keeps_all_gates_locked(
    proof_bytes: bytes,
) -> None:
    verified = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        proof_bytes
    )
    document = _document(proof_bytes)

    assert verified.result.outcome is durable.DurableProofVerificationOutcomeV1.IDENTICAL_MATCH
    assert verified.result.proof_semantically_valid is True
    assert verified.result.minimum_failure_probability == Fraction(383, 410)
    assert verified.result.minimum_failure_probability > Fraction(1, 20)
    assert document["complete_search_profile"] == {
        "schema": "acfqp.phase3e_exact_infeasibility_search_profile.v1",
        "schema_version": "1.0.0",
        "algorithm": "complete_h1_deterministic_markov_enumeration",
        "state_cap": 50000,
        "state_count": 46,
        "transition_count": 16,
        "positive_outcome_count": 96,
        "policy_count": 256,
        "cap_exhausted": False,
        "search_complete": True,
    }
    assert len(document["kernel_profile"]["state_catalogue"]) == 46
    assert len(document["kernel_profile"]["transition_rows"]) == 16
    assert document["claim"]["outcome"] == "INFEASIBLE_CERTIFIED"
    assert document["claim"]["selected_policy"] is None
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["workload_economics_gate"] == "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    assert document["counter_completeness_gate"] == "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    assert document["sample_efficiency_gate"] == "SAMPLE_EFFICIENCY_GATE_NOT_RUN"


def test_producer_and_independent_verifier_do_not_call_ground_solver_or_each_other(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
) -> None:
    import acfqp.phase3e_fallback_v1 as fallback
    import acfqp.phase3e_exact_infeasibility_durable_proof_v1 as module

    def forbidden(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("forbidden producer/ground solver call")

    monkeypatch.setattr(fallback, "run_ground_fallback_search_v1", forbidden)
    regenerated = module.issue_phase3e_exact_infeasibility_durable_proof_v1(
        CANONICAL_BUNDLE
    )
    assert regenerated == proof_bytes

    monkeypatch.setattr(
        module,
        "issue_phase3e_exact_infeasibility_durable_proof_v1",
        forbidden,
    )
    verified = module.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        proof_bytes
    )
    assert verified.result.outcome is module.DurableProofVerificationOutcomeV1.IDENTICAL_MATCH


@pytest.mark.parametrize(
    "coordinate",
    (
        "structural_id",
        "query_id",
        "build_epoch_id",
        "kernel_id",
        "threshold_profile_id",
        "reward_profile_id",
        "policy_class_id",
        "complete_search_profile_id",
    ),
)
def test_every_bound_identity_coordinate_has_ordinary_no_match_semantics(
    proof_bytes: bytes,
    coordinate: str,
) -> None:
    proof_identity = durable.DurableExactInfeasibilityIdentityV1.from_dict(
        _document(proof_bytes)["identity"]
    )
    current = dataclasses.replace(
        proof_identity,
        **{
            coordinate: hashlib.sha256(
                f"different:{coordinate}".encode("utf-8")
            ).hexdigest()
        },
    )
    verified = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        proof_bytes,
        current_identity=current,
    )
    assert verified.result.outcome is durable.DurableProofVerificationOutcomeV1.NO_MATCH
    assert verified.result.proof_semantically_valid is True
    assert verified.result.minimum_failure_probability == Fraction(383, 410)
    assert verified.result.proof_identity_id != verified.result.current_identity_id


def test_independent_replay_rejects_fully_resigned_transition_law_attack(
    proof_bytes: bytes,
) -> None:
    document = _document(proof_bytes)
    document["kernel_profile"]["transition_rows"][0]["outcomes"][0][
        "probability"
    ] = Fraction(1, 4)
    attacked = _rebind_kernel_build_identity(document)

    result = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        attacked
    ).result
    assert result.outcome is durable.DurableProofVerificationOutcomeV1.INVALID
    assert result.proof_semantically_valid is False
    assert "independent G2048 semantics" in result.reason_code


def test_independent_replay_rejects_fully_resigned_action_omission(
    proof_bytes: bytes,
) -> None:
    document = _document(proof_bytes)
    del document["kernel_profile"]["transition_rows"][0]
    document["complete_search_profile"]["transition_count"] = 15
    document["complete_search_profile"]["positive_outcome_count"] = 90
    search_id = durable._id(
        durable.SEARCH_PROFILE_DOMAIN, document["complete_search_profile"]
    )
    document["identity"]["complete_search_profile_id"] = search_id
    attacked = _rebind_kernel_build_identity(document)

    result = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        attacked
    ).result
    assert result.outcome is durable.DurableProofVerificationOutcomeV1.INVALID
    assert "action closure" in result.reason_code or "cardinality" in result.reason_code


@pytest.mark.parametrize(
    "attack",
    (
        "search_cap_exhausted",
        "source_cap_exhausted",
        "false_frontier",
        "unlock_gate",
        "claim_status_only",
    ),
)
def test_cap_status_frontier_and_gate_attacks_are_invalid(
    proof_bytes: bytes,
    attack: str,
) -> None:
    document = _document(proof_bytes)
    if attack == "search_cap_exhausted":
        document["complete_search_profile"]["cap_exhausted"] = True
    elif attack == "source_cap_exhausted":
        document["source_projection"]["cap_exceeded"] = True
        document["source_projection_id"] = durable._id(
            durable.SOURCE_PROJECTION_DOMAIN, document["source_projection"]
        )
        document["build_epoch"]["source_projection_id"] = document[
            "source_projection_id"
        ]
        document["identity"]["BuildEpoch_id"] = durable._id(
            durable.BUILD_EPOCH_DOMAIN, document["build_epoch"]
        )
        identity = durable.DurableExactInfeasibilityIdentityV1(
            document["identity"]["structural_id"],
            document["identity"]["query_id"],
            document["identity"]["BuildEpoch_id"],
            document["identity"]["kernel_id"],
            document["identity"]["threshold_profile_id"],
            document["identity"]["reward_profile_id"],
            document["identity"]["policy_class_id"],
            document["identity"]["complete_search_profile_id"],
        )
        document["identity"] = identity.to_dict()
    elif attack == "false_frontier":
        document["claimed_frontier"][0]["failure_probability"] = Fraction(1, 100)
    elif attack == "unlock_gate":
        document["official_execution_allowed"] = True
    else:
        document["kernel_profile"]["transition_rows"] = []
        document["kernel_profile"]["state_catalogue"] = []
        document["claim"]["outcome"] = "INFEASIBLE_CERTIFIED"
    result = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        _resign(document)
    ).result
    assert result.outcome is durable.DurableProofVerificationOutcomeV1.INVALID
    assert result.proof_semantically_valid is False


def test_noncanonical_or_malformed_current_identity_is_invalid_not_no_match(
    proof_bytes: bytes,
) -> None:
    whitespace = b" " + proof_bytes
    invalid_bytes = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        whitespace
    ).result
    assert invalid_bytes.outcome is durable.DurableProofVerificationOutcomeV1.INVALID

    malformed = _document(proof_bytes)["identity"]
    del malformed["kernel_id"]
    invalid_identity = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        proof_bytes, current_identity=malformed
    ).result
    assert invalid_identity.outcome is durable.DurableProofVerificationOutcomeV1.INVALID


def test_plan_frozen_cache_can_only_consume_retained_verified_match(
    proof_bytes: bytes,
) -> None:
    verified = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        proof_bytes
    )
    plan_id = hashlib.sha256(b"real-selected-plan").hexdigest()
    consumed = durable.bind_verified_durable_exact_infeasibility_to_plan_v1(
        verified, selected_plan_id=plan_id
    )
    assert consumed.selected_plan_id == plan_id
    assert consumed.durable_proof_id == verified.result.durable_proof_id
    assert consumed.to_dict()["mints_exact_infeasibility_proof"] is False

    with pytest.raises(
        durable.DurableExactInfeasibilityV1Error,
        match="retained independent-verifier handle",
    ):
        durable.bind_verified_durable_exact_infeasibility_to_plan_v1(  # type: ignore[arg-type]
            proof_bytes, selected_plan_id=plan_id
        )
    copied = dataclasses.replace(verified)
    with pytest.raises(
        durable.DurableExactInfeasibilityV1Error,
        match="exact retained verifier handle",
    ):
        durable.bind_verified_durable_exact_infeasibility_to_plan_v1(
            copied, selected_plan_id=plan_id
        )

    identity = durable.DurableExactInfeasibilityIdentityV1.from_dict(
        _document(proof_bytes)["identity"]
    )
    no_match = durable.verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        proof_bytes,
        current_identity=dataclasses.replace(
            identity,
            query_id=hashlib.sha256(b"other-query").hexdigest(),
        ),
    )
    with pytest.raises(
        durable.DurableExactInfeasibilityV1Error,
        match="IDENTICAL_MATCH",
    ):
        durable.bind_verified_durable_exact_infeasibility_to_plan_v1(
            no_match, selected_plan_id=plan_id
        )


@dataclass(frozen=True)
class _State:
    label: str


class _TwoActionFailureKernel:
    horizon = 1
    registered_reward_features = ("reward",)
    registered_goals = ("default",)

    def __init__(self) -> None:
        self.start = _State("start")
        self.end = _State("failure")

    def reward_upper_bound(self, horizon, raw_weights, goal):  # type: ignore[no-untyped-def]
        return Fraction(horizon)

    def initial_distribution(self):  # type: ignore[no-untyped-def]
        return ((Fraction(1), self.start),)

    def actions(self, state):  # type: ignore[no-untyped-def]
        return ("a", "b") if state == self.start else ()

    def step(self, state, action):  # type: ignore[no-untyped-def]
        return (
            Outcome(
                Fraction(1),
                self.end,
                (("reward", Fraction(0)),),
                failure=True,
                terminal=True,
            ),
        )

    def is_terminal(self, state):  # type: ignore[no-untyped-def]
        return state == self.end


def _raw_fallback(max_actions: int):
    kernel = _TwoActionFailureKernel()
    query = QuerySpec.from_state(
        kernel.start,
        horizon=1,
        reward_weights=(("reward", Fraction(1)),),
        delta=Fraction(1, 20),
    )
    cap = GroundFallbackCapProfileV1(
        max_states_expanded=2,
        max_actions_evaluated=max_actions,
        max_ground_steps=max_actions,
        max_outcome_rows=max_actions,
        max_bellman_backups=4,
        max_composed_candidates=4,
        max_cap_checks=20,
        max_positive_outcomes_per_step=1,
    )
    ids = [hashlib.sha256(f"fallback:{index}".encode()).hexdigest() for index in range(6)]
    return run_ground_fallback_search_v1(
        kernel,
        query,
        route_decision_context_id=ids[0],
        decision_point_id=ids[1],
        route_decision_id=ids[2],
        selected_upper_id=ids[3],
        route_attempt_id=ids[4],
        query_id=ids[5],
        cap_profile=cap,
    ).result


def test_legacy_fallback_status_never_mints_durable_proof_and_cap_is_noncertificate() -> None:
    exact_but_opaque = durable.classify_legacy_ground_fallback_portability_v1(
        _raw_fallback(2)
    )
    capped = durable.classify_legacy_ground_fallback_portability_v1(
        _raw_fallback(1)
    )

    assert exact_but_opaque.source_outcome == "INFEASIBLE_CERTIFIED"
    assert exact_but_opaque.blocker_code == "OPAQUE_SEARCH_COMPLETENESS_NOT_DURABLE"
    assert exact_but_opaque.durable_proof_minted is False
    assert capped.source_outcome == "CAP_EXHAUSTED"
    assert capped.blocker_code == "CAP_EXHAUSTED_IS_NONCERTIFICATE"
    assert capped.durable_proof_minted is False
