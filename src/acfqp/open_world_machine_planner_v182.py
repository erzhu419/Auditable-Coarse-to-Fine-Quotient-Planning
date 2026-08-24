"""Persistent receding planning over a compiled V182 machine world model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v182 as domains
from acfqp.open_world_machine_compiled_model_v182 import (
    CompiledMachineWorldModelV182,
)


class OpenWorldMachinePlannerV182Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldMachinePlannerV182Error(message)


@dataclass(frozen=True, slots=True)
class MachinePlanCertificateV182:
    compiled_model_id: str
    state: tuple[int, ...]
    horizon: int
    certified: bool
    selected_action: tuple[int, ...] | None
    terminal_distance_rank: int | None
    selected_successor_rank_upper_bound: int | None
    planning_compute_events: int
    persistent_cache_hit_count: int
    certificate_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_machine_plan_certificate.v182",
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
            "planning_compute_events": self.planning_compute_events,
            "persistent_cache_hit_count": self.persistent_cache_hit_count,
            "planner_consumed_only_compiled_world_model": True,
            "ground_transition_argument_present": False,
            "certificate_failure_requires_local_ground_distinction": (
                not self.certified
            ),
            "certificate_id": self.certificate_id,
        }


class MachinePlannerSessionV182:
    def __init__(
        self,
        model: CompiledMachineWorldModelV182,
        *,
        legal_actions: Sequence[Sequence[int]],
        horizon: int,
    ) -> None:
        if (
            type(model) is not CompiledMachineWorldModelV182
            or type(legal_actions) not in {tuple, list}
            or not legal_actions
            or type(horizon) is not int
            or horizon <= 0
        ):
            _fail("V182 planner input changed")
        actions = tuple(tuple(row) for row in legal_actions)
        if any(
            len(row) != model.action_width
            or any(type(value) is not int or value < 0 for value in row)
            for row in actions
        ):
            _fail("V182 planner action schema changed")
        self._model = model
        self._actions = actions
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

    def certify(self, state: Sequence[int]) -> MachinePlanCertificateV182:
        if len(state) != self._model.state_width:
            _fail("V182 planner state width changed")
        events = 0
        cache_hits = 0

        def minimum_rank(
            current: tuple[int, ...], limit: int
        ) -> tuple[int | None, tuple[int, ...] | None, int | None]:
            nonlocal events, cache_hits
            events += 1
            if self._model.terminal(current):
                return 0, None, None
            if limit == 0:
                return None, None, None
            key = (current, limit)
            if key in self._memo:
                cache_hits += 1
                return self._memo[key]
            candidates: list[tuple[int, tuple[int, ...], int]] = []
            for action in self._actions:
                ranks = [
                    minimum_rank(successor, limit - 1)[0]
                    for successor in self._model.predict_support(current, action)
                ]
                if any(rank is None for rank in ranks):
                    continue
                upper = max(int(rank) for rank in ranks)
                candidates.append((upper + 1, action, upper))
            self._memo[key] = min(candidates) if candidates else (None, None, None)
            return self._memo[key]

        frozen_state = tuple(state)
        rank, action, upper = minimum_rank(frozen_state, self._horizon)
        certified = rank is not None and rank > 0 and action is not None
        if certified and (upper is None or upper >= rank):
            _fail("V182 certificate lacks a strict rank decrease")
        payload = {
            "schema": "acfqp.open_world_machine_plan_certificate.v182",
            "compiled_model_id": self._model.compiled_model_id,
            "state": list(frozen_state),
            "horizon": self._horizon,
            "certified": certified,
            "selected_action": list(action) if action is not None else None,
            "terminal_distance_rank": rank,
            "selected_successor_rank_upper_bound": upper,
            "strict_rank_decrease_proved": certified,
            "planning_compute_events": events,
            "persistent_cache_hit_count": cache_hits,
            "planner_consumed_only_compiled_world_model": True,
            "ground_transition_argument_present": False,
            "certificate_failure_requires_local_ground_distinction": not certified,
        }
        certificate_id = domains.extension_content_id_v182(
            domains.CONSTRUCTION_K7_CERTIFICATE_V182_DOMAIN,
            payload,
        )
        return MachinePlanCertificateV182(
            self._model.compiled_model_id,
            frozen_state,
            self._horizon,
            certified,
            action,
            rank,
            upper,
            events,
            cache_hits,
            certificate_id,
        )


__all__ = (
    "MachinePlanCertificateV182",
    "MachinePlannerSessionV182",
    "OpenWorldMachinePlannerV182Error",
)
