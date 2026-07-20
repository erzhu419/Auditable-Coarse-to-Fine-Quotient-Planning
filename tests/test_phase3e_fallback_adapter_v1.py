from __future__ import annotations

import hashlib

import pytest

from acfqp.access_protocol_v1 import FailClosedAccessController
from acfqp.accounting_v1 import RouteKindEnum
from acfqp.actual_accounting_v1 import ActualWorkScope
from acfqp.domains.g2048 import safe_chain_fixture
from acfqp.native_recorder_v1 import NativeCounterRecorderV1
from acfqp.phase3e_fallback_adapter_v1 import (
    AuthorizedGroundFallbackExecutorV1,
    GroundFallbackExecutorInputsV1,
    Phase3EFallbackAdapterV1Error,
    adapt_ground_fallback_execution_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackCapProfileV1,
    GroundFallbackOutcome,
    run_ground_fallback_search_v1,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _cap(**overrides: int) -> GroundFallbackCapProfileV1:
    values = {
        "max_states_expanded": 1_000,
        "max_actions_evaluated": 2_000,
        "max_ground_steps": 1_000,
        "max_outcome_rows": 6_000,
        "max_bellman_backups": 10,
        "max_composed_candidates": 1,
        "max_cap_checks": 20_000,
        "max_positive_outcomes_per_step": 6,
    }
    values.update(overrides)
    return GroundFallbackCapProfileV1(**values)


def test_raw_cap_exhaustion_cannot_adapt_without_selected_route_authority() -> None:
    kernel, query = safe_chain_fixture()
    execution = run_ground_fallback_search_v1(
        kernel,
        query,
        route_decision_context_id=_id("context"),
        decision_point_id=_id("point"),
        route_decision_id=_id("decision"),
        selected_upper_id=_id("upper"),
        route_attempt_id=_id("attempt"),
        query_id=_id("query"),
        cap_profile=_cap(),
    )
    assert execution.result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED

    with pytest.raises(
        Phase3EFallbackAdapterV1Error,
        match="lacks selected-route semantic authority",
    ):
        adapt_ground_fallback_execution_v1(execution)


class _NeverAuthorizedKernel:
    def __init__(self) -> None:
        self.step_calls = 0

    def step(self, *_args):
        self.step_calls += 1
        raise AssertionError("unauthorized adapter touched kernel.step")


def _unbound_adapter(kernel: object) -> AuthorizedGroundFallbackExecutorV1:
    # Runtime semantic objects are intentionally absent.  The post-freeze
    # guard must reject before the authority-gated fallback sees them.
    inputs = GroundFallbackExecutorInputsV1(
        kernel=kernel,
        query=object(),
        context=object(),  # type: ignore[arg-type]
        decision_point=object(),  # type: ignore[arg-type]
        fallback_upper=object(),  # type: ignore[arg-type]
        cardinality=object(),  # type: ignore[arg-type]
        cardinality_bound=object(),  # type: ignore[arg-type]
        cap_profile=object(),  # type: ignore[arg-type]
        route_decision_result=object(),
        fallback_upper_result=object(),
        cardinality_result=object(),
    )
    return AuthorizedGroundFallbackExecutorV1(inputs)


def test_unfrozen_or_unauthorized_adapter_cannot_touch_kernel() -> None:
    kernel = _NeverAuthorizedKernel()
    adapter = _unbound_adapter(kernel)
    controller = FailClosedAccessController(_id("attempt"), _id("point"))
    recorder = NativeCounterRecorderV1(
        subject_id=_id("attempt"),
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    with pytest.raises(Phase3EFallbackAdapterV1Error, match="frozen FALLBACK"):
        adapter(object(), controller, recorder)  # type: ignore[arg-type]
    assert kernel.step_calls == 0
    assert controller.snapshot().events == ()


def test_adapter_refuses_to_mix_owned_and_runner_native_counters() -> None:
    kernel = _NeverAuthorizedKernel()
    adapter = _unbound_adapter(kernel)
    controller = FailClosedAccessController(_id("attempt"), _id("point"))
    recorder = NativeCounterRecorderV1(
        subject_id=_id("attempt"),
        route_kind=RouteKindEnum.DIRECT_FALLBACK,
        work_scope=ActualWorkScope.MARGINAL_ROUTE_EXECUTION,
    )
    recorder.add("fallback.ground_steps")
    with pytest.raises(Phase3EFallbackAdapterV1Error, match="cannot be mixed"):
        adapter(object(), controller, recorder)  # type: ignore[arg-type]
    assert kernel.step_calls == 0
