"""Shared AIM mechanics for the explicitly specified V43 reimplementation.

Status codes are inactive=0, active=1, removed=2. A day seeds nodes, then
executes one IC propagation step in sorted edge order. Every eligible edge
draws once, including edges to a target already reached by another parent.
"""
from __future__ import annotations

from typing import Any, MutableMapping, Sequence

import networkx as nx
import numpy as np


def generate_graph(n: int, seed: int, p: float = .01) -> nx.DiGraph:
    return nx.erdos_renyi_graph(n, p, seed=seed, directed=True)


class AIMEnvironment:
    def __init__(self, graph: nx.DiGraph, *, budget: int = 70,
                 horizon: int = 10, seed: int = 0):
        if not graph.is_directed() or sorted(graph.nodes()) != list(range(len(graph))):
            raise ValueError("AIM requires a directed graph labeled 0 through n-1")
        if budget < 0 or horizon < 1:
            raise ValueError("Budget must be nonnegative and horizon positive")
        copied = nx.DiGraph(graph)
        for source, target in copied.edges():
            copied[source][target]["weight"] = 1. / copied.in_degree(target)
        self.graph = nx.freeze(copied)
        self.n, self.budget, self.horizon = len(copied), int(budget), int(horizon)
        self._outgoing = tuple(tuple((target, copied[source][target]["weight"])
                                    for target in sorted(copied.successors(source)))
                               for source in range(self.n))
        self.rng = np.random.default_rng(seed)
        self.counters: dict[str, dict[str, int]] = {}
        self.reset()

    @property
    def done(self) -> bool:
        return self.day >= self.horizon

    @property
    def remaining_days(self) -> int:
        return self.horizon - self.day

    def reset(self, seed: int | None = None) -> dict[str, Any]:
        """Reset the episode; preserve total phase counters and, absent seed, RNG."""
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.statuses = np.zeros(self.n, dtype=np.int8)
        self.day_start_status = self.statuses.copy()
        self.day = 0
        self.remaining_budget = self.budget
        self.daily_selected: tuple[int, ...] = ()
        return self.observation()

    def legal_mask(self) -> np.ndarray:
        return (self.statuses == 0) & (self.remaining_budget > 0) & (not self.done)

    def features(self) -> np.ndarray:
        features = np.zeros((self.n, 5), dtype=np.float32)
        features[np.arange(self.n), self.statuses] = 1.
        features[:, 3] = self.remaining_days / self.horizon
        features[:, 4] = self.remaining_budget / self.budget if self.budget else 0.
        return features

    def observation(self) -> dict[str, Any]:
        return {"statuses": self.statuses.copy(), "remaining_days": self.remaining_days,
                "remaining_budget": self.remaining_budget,
                "daily_selected": self.daily_selected, "legal_mask": self.legal_mask(),
                "features": self.features()}

    def _count(self, phase: str, **increments: int) -> None:
        bucket = self.counters.setdefault(phase, {
            "primitive_selections": 0, "day_transitions": 0, "propagation_draws": 0})
        for name, amount in increments.items():
            bucket[name] += amount

    def select(self, node: int, *, phase: str = "train") -> tuple[dict[str, Any], float, bool]:
        """Seed one legal node; seeding succeeds deterministically and earns one."""
        if node < 0 or node >= self.n or not self.legal_mask()[node]:
            raise ValueError("Illegal AIM seed selection")
        self.statuses[node] = 1
        self.remaining_budget -= 1
        self.daily_selected += (int(node),)
        self._count(phase, primitive_selections=1)
        return self.observation(), 1., self.done

    def finish_day(self, *, phase: str = "train") -> tuple[dict[str, Any], float, bool, dict[str, Any]]:
        """Advance one day even with no allocation; seeds have already been paid."""
        if self.done:
            raise ValueError("The AIM episode has already ended")
        next_status, spread_reward, info = self.transition(self.statuses, (), self.rng)
        seed_reward = len(self.daily_selected)
        self.statuses = next_status
        self.day += 1
        self.daily_selected = ()
        self.day_start_status = self.statuses.copy()
        self._count(phase, day_transitions=1, propagation_draws=info["propagation_draws"])
        info = {**info, "seed_reward": seed_reward,
                "day_reward": seed_reward + spread_reward}
        return self.observation(), spread_reward, self.done, info

    def transition(self, state: np.ndarray, action: Sequence[int], rng: Any, *,
                   counters: MutableMapping[str, int] | None = None
                   ) -> tuple[np.ndarray, float, dict[str, Any]]:
        """Pure daily transition from passed status, with an explicit sampling RNG.

        This does not access or mutate the current episode or its RNG. Optional
        counters charge counterfactual oracle queries separately from execution.
        """
        start = np.asarray(state, dtype=np.int8)
        seeds = np.asarray(action, dtype=int)
        if start.shape != (self.n,) or np.any((start < 0) | (start > 2)):
            raise ValueError("State must contain one AIM status per graph node")
        if np.any(seeds < 0) or np.any(seeds >= self.n) or np.unique(seeds).size != seeds.size:
            raise ValueError("Seed nodes must be distinct graph nodes")
        if np.any(start[seeds] != 0):
            raise ValueError("Only inactive nodes can be seeded")
        selected = start.copy()
        selected[seeds] = 1
        active = selected == 1
        inactive = selected == 0
        activated = np.zeros(self.n, dtype=bool)
        draws = 0
        for source in np.flatnonzero(active):
            for target, probability in self._outgoing[source]:
                if inactive[target]:
                    activated[target] |= rng.random() < probability
                    draws += 1
        next_status = selected.copy()
        next_status[active] = 2
        next_status[activated] = 1
        spread = int(activated.sum())
        if counters is not None:
            for name, amount in {"oracle_day_transitions": 1,
                                 "oracle_seed_exposures": int(seeds.size),
                                 "oracle_propagation_draws": draws}.items():
                counters[name] = counters.get(name, 0) + amount
        return next_status, float(seeds.size + spread), {
            "seed_reward": int(seeds.size), "spread_reward": spread,
            "propagation_draws": draws}
