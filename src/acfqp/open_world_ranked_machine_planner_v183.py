"""Persistent receding planning over a V183 ranked-total world model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v183 as domains
from acfqp.open_world_ranked_machine_v183 import (
    OpenWorldRankedMachineV183Error,
    RankedCompiledWorldModelV183,
)


class OpenWorldRankedMachinePlannerV183Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldRankedMachinePlannerV183Error(message)


@dataclass(frozen=True, slots=True)
class RankedMachinePlanCertificateV183:
    compiled_model_id: str
    state: tuple[int, ...]
    horizon: int
    certified: bool
    selected_action: tuple[int, ...] | None
    terminal_distance_rank: int | None
    selected_successor_rank_upper_bound: int | None
    failure_reason: str | None
    planning_compute_events: int
    persistent_cache_hit_count: int
    certificate_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.ranked_machine_plan_certificate.v183",
            "compiled_model_id": self.compiled_model_id,
            "state": list(self.state),
            "horizon": self.horizon,
            "certified": self.certified,
            "selected_action": (
                list(self.selected_action) if self.selected_action is not None else None
            ),
            "terminal_distance_rank": self.terminal_distance_rank,
            "selected_successor_rank_upper_bound": (
                self.selected_successor_rank_upper_bound
            ),
            "strict_rank_decrease_proved": (
                self.certified
                and self.terminal_distance_rank is not None
                and self.selected_successor_rank_upper_bound is not None
                and self.selected_successor_rank_upper_bound
                < self.terminal_distance_rank
            ),
            "failure_reason": self.failure_reason,
            "planning_compute_events": self.planning_compute_events,
            "persistent_cache_hit_count": self.persistent_cache_hit_count,
            "planner_consumed_only_ranked_total_compiled_model": True,
            "ground_transition_argument_present": False,
            "local_ground_distinction_permitted": (
                not self.certified and self.failure_reason == "NO_HORIZON_CERTIFICATE"
            ),
            "compute_cap_failure_is_not_a_ground_label_request": (
                self.failure_reason == "MODEL_EXECUTION_RESOURCE_CAP"
            ),
            "certificate_id": self.certificate_id,
        }


class RankedMachinePlannerSessionV183:
    def __init__(self, model: RankedCompiledWorldModelV183, *, horizon: int) -> None:
        if (
            type(model) is not RankedCompiledWorldModelV183
            or type(horizon) is not int
            or horizon <= 2
        ):
            _fail("V183 planner requires one ranked model and H>2")
        self._model = model
        self._horizon = horizon
        self._memo: dict[
            tuple[tuple[int, ...], int],
            tuple[int | None, tuple[int, ...] | None, int | None],
        ] = {}

    @property
    def compiled_model_id(self) -> str:
        return self._model.compiled_model_id

    @property
    def cached_subproblem_count(self) -> int:
        return len(self._memo)

    def certify(self, state: Sequence[int]) -> RankedMachinePlanCertificateV183:
        frozen_state = tuple(state)
        events = 0
        cache_hits = 0
        resource_failure = False

        def minimum_rank(
            current: tuple[int, ...], limit: int
        ) -> tuple[int | None, tuple[int, ...] | None, int | None]:
            nonlocal events, cache_hits, resource_failure
            events += 1
            try:
                if self._model.terminal(current):
                    return 0, None, None
            except OpenWorldRankedMachineV183Error:
                resource_failure = True
                return None, None, None
            if limit == 0:
                return None, None, None
            key = (current, limit)
            if key in self._memo:
                cache_hits += 1
                return self._memo[key]
            candidates: list[tuple[int, tuple[int, ...], int]] = []
            for action in self._model.legal_actions:
                try:
                    support = self._model.predict_support(current, action)
                except OpenWorldRankedMachineV183Error:
                    resource_failure = True
                    continue
                ranks = [minimum_rank(successor, limit - 1)[0] for successor in support]
                if any(rank is None for rank in ranks):
                    continue
                upper = max(int(rank) for rank in ranks)
                candidates.append((upper + 1, action, upper))
            self._memo[key] = min(candidates) if candidates else (None, None, None)
            return self._memo[key]

        rank, action, upper = minimum_rank(frozen_state, self._horizon)
        certified = rank is not None and rank > 0 and action is not None
        if certified and (upper is None or upper >= rank):
            _fail("V183 certificate lacks strict rank decrease")
        failure_reason = None
        if not certified:
            failure_reason = (
                "MODEL_EXECUTION_RESOURCE_CAP"
                if resource_failure
                else "NO_HORIZON_CERTIFICATE"
            )
        payload = {
            "schema": "acfqp.ranked_machine_plan_certificate.v183",
            "compiled_model_id": self._model.compiled_model_id,
            "state": list(frozen_state),
            "horizon": self._horizon,
            "certified": certified,
            "selected_action": list(action) if action is not None else None,
            "terminal_distance_rank": rank,
            "selected_successor_rank_upper_bound": upper,
            "strict_rank_decrease_proved": certified,
            "failure_reason": failure_reason,
            "planning_compute_events": events,
            "persistent_cache_hit_count": cache_hits,
            "planner_consumed_only_ranked_total_compiled_model": True,
            "ground_transition_argument_present": False,
            "local_ground_distinction_permitted": (
                not certified and failure_reason == "NO_HORIZON_CERTIFICATE"
            ),
            "compute_cap_failure_is_not_a_ground_label_request": (
                failure_reason == "MODEL_EXECUTION_RESOURCE_CAP"
            ),
        }
        return RankedMachinePlanCertificateV183(
            self._model.compiled_model_id,
            frozen_state,
            self._horizon,
            certified,
            action,
            rank,
            upper,
            failure_reason,
            events,
            cache_hits,
            domains.extension_content_id_v183(
                domains.CONSTRUCTION_K7_PLAN_CERTIFICATE_V183_DOMAIN,
                payload,
            ),
        )


__all__ = (
    "OpenWorldRankedMachinePlannerV183Error",
    "RankedMachinePlanCertificateV183",
    "RankedMachinePlannerSessionV183",
)
