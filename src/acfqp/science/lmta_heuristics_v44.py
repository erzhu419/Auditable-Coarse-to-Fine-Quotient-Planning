"""Evaluation-only V44 average-budget policies, without simulated rewards.

Score uses each currently inactive outgoing target's inverse indegree and is
recomputed after every actual selection. Remaining old active nodes propagate
only through the shared environment's normal daily transition.
"""
from __future__ import annotations

from collections import Counter
import math

import numpy as np


class _AverageAgent:
    def __init__(self, graph, budget, horizon, seed, device="cpu"):
        self.rng = np.random.default_rng(seed)
        self.budget, self.horizon = budget, horizon
        self.training_episodes = self.total_train_updates = self.total_replay_draws = 0
        self.counts = Counter({"LL_gradient_steps": 0, "HL_gradient_steps": 0,
                               "LL_replay_samples": 0, "HL_replay_samples": 0})
        self.set_graph(graph)

    def set_graph(self, graph):
        self.graph = graph

    def choose(self, env):
        raise NotImplementedError

    def run_episode(self, env, training=False):
        """Execute the policy; no learning is performed, including warm-up."""
        self.set_graph(env.graph)
        before = dict(env.counters.get("evaluation", {}))
        env.reset()
        actions, days = [], []
        while not env.done:
            cap = min(env.remaining_budget, int(env.legal_mask().sum()))
            allocated = (cap if env.remaining_days == 1 else
                         min(cap, math.ceil(env.remaining_budget / env.remaining_days)))
            selected = []
            for _ in range(allocated):
                node = self.choose(env)
                env.select(node, phase="evaluation")
                selected.append(node)
            _, _, _, info = env.finish_day(phase="evaluation")
            days.append({"day": env.day - 1, **info})
            actions.append({"day": env.day - 1, "budget": allocated,
                            "selected": selected, "realized_duration": len(selected),
                            "reward": info["day_reward"]})
        increments = {k: v - before.get(k, 0)
                      for k, v in env.counters["evaluation"].items()}
        return {"arm": self.label, "raw_return": float(sum(d["day_reward"] for d in days)),
                **increments, "actions": actions, "day_history": days, "losses": [],
                "train_updates": 0, "replay_draws": 0, "update_counts": dict(self.counts),
                "total_train_updates": 0, "total_replay_draws": 0,
                "training_episodes": 0, "epsilon": 0.}


class AverageRandomAgent(_AverageAgent):
    label = "AVERAGE_RANDOM"

    def choose(self, env):
        return int(self.rng.choice(np.flatnonzero(env.legal_mask())))


class AverageScoreAgent(_AverageAgent):
    label = "AVERAGE_SCORE"

    def choose(self, env):
        legal = np.flatnonzero(env.legal_mask())
        scores = [math.fsum(1. / self.graph.in_degree(target)
                            for target in self.graph.successors(int(node))
                            if env.statuses[target] == 0)
                  for node in legal]
        return int(legal[np.argmax(scores)])


ARMS = {"AVERAGE_RANDOM": AverageRandomAgent, "AVERAGE_SCORE": AverageScoreAgent}
