"""Receding abstract planning with a strictly decreasing terminal rank.

V181r3 certified that a terminal state was reachable within a reset horizon,
but selected the first winning action.  An action could consume one unit of the
proof horizon while leaving the same state; resetting the horizon at the next
decision then allowed indefinite procrastination.  V181r4 computes the minimum
worst-case terminal distance and selects only an action whose every abstract
successor has a strictly smaller certified rank.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from acfqp import construction_k7_domain_registry_extension_v181r4 as domains
from acfqp.open_world_compiled_model_v181r3 import CompiledWorldModelV181R3


class OpenWorldRankDecreasingPlannerV181R4Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RankDecreasingPlanCertificateV181R4:
    compiled_model_id: str
    state: tuple[int, ...]
    horizon: int
    certified: bool
    selected_action: tuple[int, ...] | None
    terminal_distance_rank: int | None
    selected_successor_rank_upper_bound: int | None
    strict_rank_decrease_proved: bool
    planning_compute_events: int
    certificate_id: str

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.open_world_rank_certificate.v181r4",
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
            "planning_compute_events": self.planning_compute_events,
            "certificate_failure_requires_local_ground_distinction": not self.certified,
            "certificate_id": self.certificate_id,
        }


def certify_rank_decreasing_action_v181r4(
    model: CompiledWorldModelV181R3,
    *,
    state: Sequence[int],
    legal_actions: Sequence[Sequence[int]],
    horizon: int,
) -> RankDecreasingPlanCertificateV181R4:
    if (
        type(model) is not CompiledWorldModelV181R3
        or len(state) != model.state_width
        or type(horizon) is not int
        or horizon <= 0
        or type(legal_actions) not in {tuple, list}
        or not legal_actions
    ):
        raise OpenWorldRankDecreasingPlannerV181R4Error("planner input changed")
    actions = tuple(tuple(row) for row in legal_actions)
    if any(len(row) != model.action_width for row in actions):
        raise OpenWorldRankDecreasingPlannerV181R4Error("planner action width changed")
    memo: dict[
        tuple[tuple[int, ...], int],
        tuple[int | None, tuple[int, ...] | None, int | None],
    ] = {}
    events = 0

    def minimum_rank(
        current: tuple[int, ...],
        limit: int,
    ) -> tuple[int | None, tuple[int, ...] | None, int | None]:
        nonlocal events
        events += 1
        if model.terminal(current):
            return 0, None, None
        if limit == 0:
            return None, None, None
        key = (current, limit)
        if key in memo:
            return memo[key]
        candidates: list[tuple[int, tuple[int, ...], int]] = []
        for action in actions:
            successor_ranks = [
                minimum_rank(successor, limit - 1)[0]
                for successor in model.predict_support(current, action)
            ]
            if any(rank is None for rank in successor_ranks):
                continue
            upper_bound = max(int(rank) for rank in successor_ranks)
            candidates.append((upper_bound + 1, action, upper_bound))
        if not candidates:
            memo[key] = (None, None, None)
        else:
            rank, action, upper_bound = min(candidates)
            memo[key] = (rank, action, upper_bound)
        return memo[key]

    rank, action, successor_upper_bound = minimum_rank(tuple(state), horizon)
    certified = rank is not None and rank > 0 and action is not None
    strict_decrease = (
        certified
        and successor_upper_bound is not None
        and successor_upper_bound < rank
    )
    if certified and not strict_decrease:
        raise OpenWorldRankDecreasingPlannerV181R4Error(
            "certified action lacks a strict terminal-rank decrease"
        )
    payload = {
        "schema": "acfqp.open_world_rank_certificate.v181r4",
        "compiled_model_id": model.compiled_model_id,
        "state": list(state),
        "horizon": horizon,
        "certified": certified,
        "selected_action": list(action) if action is not None else None,
        "terminal_distance_rank": rank,
        "selected_successor_rank_upper_bound": successor_upper_bound,
        "strict_rank_decrease_proved": strict_decrease,
        "planning_compute_events": events,
        "certificate_failure_requires_local_ground_distinction": not certified,
    }
    certificate_id = domains.extension_content_id_v181r4(
        domains.CONSTRUCTION_K7_CERTIFICATE_V181R4_DOMAIN,
        payload,
    )
    return RankDecreasingPlanCertificateV181R4(
        model.compiled_model_id,
        tuple(state),
        horizon,
        certified,
        action,
        rank,
        successor_upper_bound,
        strict_decrease,
        events,
        certificate_id,
    )


__all__ = (
    "OpenWorldRankDecreasingPlannerV181R4Error",
    "RankDecreasingPlanCertificateV181R4",
    "certify_rank_decreasing_action_v181r4",
)
