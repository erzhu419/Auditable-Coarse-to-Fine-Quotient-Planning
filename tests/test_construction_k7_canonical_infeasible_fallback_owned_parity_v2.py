from __future__ import annotations

from pathlib import Path

import pytest

from acfqp import construction_k7_canonical_infeasible_fallback_acquisition_v1 as acquisition_v1
from acfqp.construction_k7_canonical_infeasible_fallback_owned_parity_v2 import (
    ConstructionK7OwnedFallbackParityV2Error,
    evaluate_owned_fallback_parity_v2,
    verify_owned_fallback_runner_bytes_v2,
)
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    issue_phase3e_exact_infeasibility_durable_proof_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_BUNDLE = ROOT / "artifacts" / "phase05" / "g2048"


@pytest.fixture(scope="module")
def proof_bytes() -> bytes:
    return issue_phase3e_exact_infeasibility_durable_proof_v1(CANONICAL_BUNDLE)


@pytest.fixture(scope="module")
def current_identity(proof_bytes: bytes):
    identity = DurableExactInfeasibilityIdentityV1.from_dict(
        loads_canonical_json(proof_bytes)["identity"]
    )
    return acquisition_v1.build_current_canonical_fallback_identity_v1(
        CANONICAL_BUNDLE,
        build_epoch_id=identity.build_epoch_id,
        threshold_profile_id=identity.threshold_profile_id,
        reward_profile_id=identity.reward_profile_id,
        policy_class_id=identity.policy_class_id,
        complete_search_profile_id=identity.complete_search_profile_id,
    )


@pytest.fixture(scope="module")
def parity(proof_bytes: bytes, current_identity):
    return evaluate_owned_fallback_parity_v2(
        proof_bytes, current_identity=current_identity
    )


def test_evaluation_only_parity_matches_exact_math_and_native_values(parity) -> None:
    document = parity.to_document()
    assert document["mathematical_result_equal"] is True
    assert document["native_counter_values_equal"] is True
    assert document["execution_lane"] == "EVALUATION"
    assert document["charged_as_operational_route_work"] is False
    assert document["terminal_artifact_issued"] is False
    assert document["official_execution_allowed"] is False


def test_operational_owned_runner_does_not_call_historical_v1_solver(
    monkeypatch: pytest.MonkeyPatch,
    proof_bytes: bytes,
    current_identity,
) -> None:
    import acfqp.phase3e_fallback_v1 as fallback_v1
    from acfqp.construction_k7_canonical_infeasible_fallback_owned_runner_v2 import (
        run_canonical_infeasible_fallback_owned_v2,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("historical V1 search was called")

    monkeypatch.setattr(fallback_v1, "run_ground_fallback_search_v1", forbidden)
    result = run_canonical_infeasible_fallback_owned_v2(
        proof_bytes, current_identity=current_identity
    )
    assert result.outcome == "OWNED_EXACT_INFEASIBILITY_SEGMENT_VERIFIED"


def test_independent_runner_byte_replay_and_tamper_rejection(
    parity, proof_bytes: bytes, current_identity
) -> None:
    raw = canonical_json_bytes(parity.owned.to_document())
    replay = verify_owned_fallback_runner_bytes_v2(
        raw=raw,
        proof_bytes=proof_bytes,
        current_identity=current_identity,
    )
    assert replay.to_document()["mathematical_result_equal"] is True

    document = loads_canonical_json(raw)
    document["exact_event_count"] = 207
    with pytest.raises(
        ConstructionK7OwnedFallbackParityV2Error,
        match="independent replay",
    ):
        verify_owned_fallback_runner_bytes_v2(
            raw=canonical_json_bytes(document),
            proof_bytes=proof_bytes,
            current_identity=current_identity,
        )
