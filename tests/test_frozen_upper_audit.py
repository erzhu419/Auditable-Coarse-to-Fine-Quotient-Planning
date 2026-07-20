from __future__ import annotations

from fractions import Fraction

import pytest

import acfqp.local_recovery as local_recovery_module
import acfqp.planning.audit as audit_module
from acfqp.abstraction import Partition, build_quotient_models
from acfqp.core import Outcome, QuerySpec
from acfqp.local_recovery import HybridPolicyOverlay, audit_hybrid_policy
from acfqp.planning import FiniteHorizonPolicy, audit_abstract_policy


class OneStepRewardKernel:
    horizon = 1

    def actions(self, state):
        return ("act",) if state == "start" else ()

    def step(self, state, action):
        assert (state, action) == ("start", "act")
        return (
            Outcome(
                Fraction(1),
                "done",
                (("score", Fraction(1)),),
                terminal=True,
            ),
        )

    def is_terminal(self, state):
        return state == "done"


@pytest.fixture
def exact_case():
    kernel = OneStepRewardKernel()
    partition = Partition.from_mapping({"start": "active", "done": "terminal"})
    models = build_quotient_models(kernel, partition.states, partition)
    query = QuerySpec.from_state(
        "start",
        horizon=1,
        reward_weights=(("score", Fraction(1)),),
        delta=Fraction(0),
        normalizer=Fraction(1),
    )
    policy = FiniteHorizonPolicy.from_mapping({(1, "active"): "act"})
    return kernel, query, models.envelope, policy


def _forbidden(*_args, **_kwargs):
    raise AssertionError("unrestricted ground upper recomputation is forbidden")


def test_frozen_upper_skips_ground_upper_for_abstract_audit(
    exact_case, monkeypatch: pytest.MonkeyPatch
) -> None:
    kernel, query, envelope, policy = exact_case
    baseline = audit_abstract_policy(kernel, query, envelope, policy)
    monkeypatch.setattr(audit_module, "unrestricted_upper_envelope", _forbidden)

    frozen = audit_abstract_policy(
        kernel,
        query,
        envelope,
        policy,
        unrestricted_reward_upper=baseline.unrestricted_reward_upper,
    )

    assert frozen == baseline
    assert frozen.unrestricted_reward_upper == 1


def test_frozen_upper_skips_ground_upper_for_hybrid_audit(
    exact_case, monkeypatch: pytest.MonkeyPatch
) -> None:
    kernel, query, envelope, policy = exact_case
    overlay = HybridPolicyOverlay(policy, ())
    baseline = audit_hybrid_policy(kernel, query, envelope, overlay)
    monkeypatch.setattr(
        local_recovery_module, "unrestricted_upper_envelope", _forbidden
    )

    frozen = audit_hybrid_policy(
        kernel,
        query,
        envelope,
        overlay,
        unrestricted_reward_upper=baseline.unrestricted_reward_upper,
    )

    assert frozen == baseline
    assert frozen.unrestricted_reward_upper == 1


@pytest.mark.parametrize("bad", (True, 1.0, "1"))
@pytest.mark.parametrize("kind", ("abstract", "hybrid"))
def test_frozen_upper_rejects_inexact_inputs(exact_case, bad, kind) -> None:
    kernel, query, envelope, policy = exact_case
    if kind == "abstract":
        call = lambda: audit_abstract_policy(  # noqa: E731
            kernel,
            query,
            envelope,
            policy,
            unrestricted_reward_upper=bad,
        )
    else:
        overlay = HybridPolicyOverlay(policy, ())
        call = lambda: audit_hybrid_policy(  # noqa: E731
            kernel,
            query,
            envelope,
            overlay,
            unrestricted_reward_upper=bad,
        )
    with pytest.raises(TypeError, match="exact int or Fraction"):
        call()


@pytest.mark.parametrize("bad", (Fraction(-1), Fraction(0)))
@pytest.mark.parametrize("kind", ("abstract", "hybrid"))
def test_frozen_upper_rejects_negative_or_below_policy_lower(
    exact_case, bad, kind
) -> None:
    kernel, query, envelope, policy = exact_case
    overlay = HybridPolicyOverlay(policy, ())
    if kind == "abstract":
        call = lambda: audit_abstract_policy(  # noqa: E731
            kernel,
            query,
            envelope,
            policy,
            unrestricted_reward_upper=bad,
        )
    else:
        call = lambda: audit_hybrid_policy(  # noqa: E731
            kernel,
            query,
            envelope,
            overlay,
            unrestricted_reward_upper=bad,
        )
    expected = "nonnegative" if bad < 0 else "below the audited policy reward"
    with pytest.raises(ValueError, match=expected):
        call()
