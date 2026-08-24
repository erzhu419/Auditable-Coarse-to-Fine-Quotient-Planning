"""Persistent receding abstract planning with a decreasing terminal rank.

V181r3 certified that a terminal state was reachable within a reset horizon,
but selected the first winning action.  An action could consume one unit of the
proof horizon while leaving the same state; resetting the horizon at the next
decision then allowed indefinite procrastination.  V181r5 computes the minimum
worst-case terminal distance, selects only an action whose every abstract
successor has a strictly smaller certified rank, and retains exact subproblem
results while the same compiled-model identity remains current.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from acfqp import construction_k7_domain_registry_extension_v181r5 as domains
from acfqp.open_world_compiled_model_v181r5 import CompiledWorldModelV181R5


class OpenWorldRankDecreasingPlannerV181R5Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RankDecreasingPlanCertificateV181R5:
    compiled_model_id: str
    state: tuple[int, ...]
    horizon: int
    certified: bool
    selected_action: tuple[int, ...] | None
    terminal_distance_rank: int | None
    selected_successor_rank_upper_bound: int | None
    strict_rank_decrease_proved: bool
    persistent_model_bound_rank_cache_used: bool
    planning_compute_events: int
    certificate_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_rank_certificate.v181r5",
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
            "strict_rank_decrease_proved": self.strict_rank_decrease_proved,
            "persistent_model_bound_rank_cache_used": (
                self.persistent_model_bound_rank_cache_used
            ),
            "planning_compute_events": self.planning_compute_events,
            "certificate_failure_requires_local_ground_distinction": not self.certified,
            "certificate_id": self.certificate_id,
        }


class RankDecreasingPlannerSessionV181R5:
    """Reuse exact rank subproblems while one compiled model remains current."""

    def __init__(
        self,
        model: CompiledWorldModelV181R5,
        *,
        legal_actions: Sequence[Sequence[int]],
        horizon: int,
    ) -> None:
        if (
            type(model) is not CompiledWorldModelV181R5
            or type(horizon) is not int
            or horizon <= 0
            or type(legal_actions) not in {tuple, list}
            or not legal_actions
        ):
            raise OpenWorldRankDecreasingPlannerV181R5Error("planner input changed")
        actions = tuple(tuple(row) for row in legal_actions)
        if any(len(row) != model.action_width for row in actions):
            raise OpenWorldRankDecreasingPlannerV181R5Error(
                "planner action width changed"
            )
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

    def certify(
        self,
        state: Sequence[int],
    ) -> RankDecreasingPlanCertificateV181R5:
        if len(state) != self._model.state_width:
            raise OpenWorldRankDecreasingPlannerV181R5Error("planner state width changed")
        events = 0

        def minimum_rank(
            current: tuple[int, ...],
            limit: int,
        ) -> tuple[int | None, tuple[int, ...] | None, int | None]:
            nonlocal events
            events += 1
            if self._model.terminal(current):
                return 0, None, None
            if limit == 0:
                return None, None, None
            key = (current, limit)
            if key in self._memo:
                return self._memo[key]
            candidates: list[tuple[int, tuple[int, ...], int]] = []
            for action in self._actions:
                successor_ranks = [
                    minimum_rank(successor, limit - 1)[0]
                    for successor in self._model.predict_support(current, action)
                ]
                if any(rank is None for rank in successor_ranks):
                    continue
                upper_bound = max(int(rank) for rank in successor_ranks)
                candidates.append((upper_bound + 1, action, upper_bound))
            if not candidates:
                self._memo[key] = (None, None, None)
            else:
                self._memo[key] = min(candidates)
            return self._memo[key]

        frozen_state = tuple(state)
        rank, action, successor_upper_bound = minimum_rank(
            frozen_state,
            self._horizon,
        )
        certified = rank is not None and rank > 0 and action is not None
        strict_decrease = (
            certified
            and successor_upper_bound is not None
            and successor_upper_bound < rank
        )
        if certified and not strict_decrease:
            raise OpenWorldRankDecreasingPlannerV181R5Error(
                "certified action lacks a strict terminal-rank decrease"
            )
        payload = {
            "schema": "acfqp.open_world_rank_certificate.v181r5",
            "compiled_model_id": self._model.compiled_model_id,
            "state": list(frozen_state),
            "horizon": self._horizon,
            "certified": certified,
            "selected_action": list(action) if action is not None else None,
            "terminal_distance_rank": rank,
            "selected_successor_rank_upper_bound": successor_upper_bound,
            "strict_rank_decrease_proved": strict_decrease,
            "planning_compute_events": events,
            "persistent_model_bound_rank_cache_used": True,
            "certificate_failure_requires_local_ground_distinction": not certified,
        }
        certificate_id = domains.extension_content_id_v181r5(
            domains.CONSTRUCTION_K7_CERTIFICATE_V181R5_DOMAIN,
            payload,
        )
        return RankDecreasingPlanCertificateV181R5(
            self._model.compiled_model_id,
            frozen_state,
            self._horizon,
            certified,
            action,
            rank,
            successor_upper_bound,
            strict_decrease,
            True,
            events,
            certificate_id,
        )


def certify_rank_decreasing_action_v181r5(
    model: CompiledWorldModelV181R5,
    *,
    state: Sequence[int],
    legal_actions: Sequence[Sequence[int]],
    horizon: int,
) -> RankDecreasingPlanCertificateV181R5:
    return RankDecreasingPlannerSessionV181R5(
        model,
        legal_actions=legal_actions,
        horizon=horizon,
    ).certify(state)


__all__ = (
    "OpenWorldRankDecreasingPlannerV181R5Error",
    "RankDecreasingPlannerSessionV181R5",
    "RankDecreasingPlanCertificateV181R5",
    "certify_rank_decreasing_action_v181r5",
)
