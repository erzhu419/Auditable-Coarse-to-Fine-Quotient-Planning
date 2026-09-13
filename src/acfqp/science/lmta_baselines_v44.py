"""Independent V44 baselines with collection-graph-aware ordinary DQN replay.

BUDGET_HRL is an independently specified budget/selection hierarchy, not the
original WS-option: it has no wake/sleep cycle or sampled counterfactual credit.
Both target networks use hard copies every 100 updates of their own learner.
Every graph has a runner-assigned integer replay_id; transitions retain that
identifier while adjacency tensors are shared in the agent's graph cache.
"""
from __future__ import annotations

from collections import Counter, deque
from copy import deepcopy
import math

import numpy as np
import torch
from torch import nn

from .lmta_models_v43 import (Encoder, NodeQ, adjacency, epsilon_action,
                              features, masked_max, mlp, optimizer_step)


class BudgetQ(nn.Module):
    def __init__(self, budget):
        super().__init__()
        self.encoder = Encoder()
        self.head = mlp(128, budget + 1)

    def forward(self, x, a):
        return self.head(self.encoder(x, a))


class _Agent:
    def __init__(self, graph, budget, horizon, seed, device="cpu"):
        torch.manual_seed(seed)
        self.rng = np.random.default_rng(seed)
        self.device = device
        self.n, self.budget, self.horizon = len(graph), budget, horizon
        self.graph_adjacencies = {}
        self.set_graph(graph)
        self.training_episodes = 0
        self.counts = Counter({"LL_gradient_steps": 0, "HL_gradient_steps": 0,
                               "LL_replay_samples": 0, "HL_replay_samples": 0})
        self.total_train_updates = self.total_replay_draws = 0
        self.ll_replay = deque(maxlen=10000)

    @property
    def epsilon(self):
        return max(.05, .9 * .995 ** self.training_episodes)

    def set_graph(self, graph):
        self.graph_id = graph.graph["replay_id"]
        if self.graph_id not in self.graph_adjacencies:
            self.graph_adjacencies[self.graph_id] = adjacency(graph, self.device)
        self.a = self.graph_adjacencies[self.graph_id]

    def _learner(self, network):
        network = network.to(self.device)
        target = deepcopy(network).eval()
        optimizer = torch.optim.Adam(network.parameters(), lr=.001,
                                     weight_decay=.00001)
        return network, target, optimizer

    def _act(self, network, observation, legal, training):
        with torch.no_grad():
            q = network(features(observation, self.device), self.a)
        if not training:
            valid = np.flatnonzero(legal)
            return int(valid[np.argmax(q.cpu().numpy()[valid])])
        return epsilon_action(q, legal, self.epsilon, self.rng)

    def _update(self, replay, network, target, optimizer, level):
        if len(replay) < 8:
            return None
        batch = [replay[int(i)] for i in self.rng.choice(len(replay), 8, replace=False)]
        x, actions, rewards, nxt, legal, terminal, graph_ids = zip(*batch)
        batch_a = torch.stack([self.graph_adjacencies[g] for g in graph_ids])
        x = torch.as_tensor(np.stack(x), device=self.device)
        nxt = torch.as_tensor(np.stack(nxt), device=self.device)
        actions = torch.as_tensor(actions, device=self.device)
        rewards = torch.as_tensor(rewards, dtype=torch.float32, device=self.device)
        terminal = torch.as_tensor(terminal, dtype=torch.bool, device=self.device)
        with torch.no_grad():
            value = masked_max(target(nxt, batch_a), np.stack(legal))
            expected = rewards + .997 * value.masked_fill(terminal, 0.)
        predicted = network(x, batch_a).gather(1, actions[:, None]).squeeze(1)
        loss = (predicted - expected).square().mean()
        optimizer_step(optimizer, loss, network.parameters())
        self.counts[level.upper() + "_gradient_steps"] += 1
        self.counts[level.upper() + "_replay_samples"] += 8
        self.total_train_updates += 1
        self.total_replay_draws += 8
        if self.counts[level.upper() + "_gradient_steps"] % 100 == 0:
            target.load_state_dict(network.state_dict())
        return float(loss.detach())

    def _learn_ll(self):
        return self._update(self.ll_replay, self.ll, self.ll_target, self.ll_optimizer, "ll")

    def _begin(self, env, training):
        phase = "train" if training else "evaluation"
        before = dict(env.counters.get(phase, {}))
        self.set_graph(env.graph)
        env.reset()
        return phase, before, dict(self.counts), [], []

    def _finish_day(self, env, phase, days):
        observation, reward, terminal, info = env.finish_day(phase=phase)
        days.append({"day": env.day - 1, **info})
        return observation, reward, terminal

    def _result(self, env, training, phase, before, counters, actions, days, losses):
        used_epsilon = self.epsilon if training else 0.
        if training:
            self.training_episodes += 1
        increments = {k: v - before.get(k, 0) for k, v in env.counters[phase].items()}
        updates = {k: v - counters[k] for k, v in self.counts.items()}
        return {"arm": self.label, "raw_return": float(sum(d["day_reward"] for d in days)),
                **increments, "actions": actions, "day_history": days, "losses": losses,
                "train_updates": updates["LL_gradient_steps"] + updates["HL_gradient_steps"],
                "replay_draws": updates["LL_replay_samples"] + updates["HL_replay_samples"],
                "update_counts": updates,
                "total_train_updates": self.total_train_updates,
                "total_replay_draws": self.total_replay_draws,
                "training_episodes": self.training_episodes,
                "epsilon": used_epsilon}


class FlatDQNAgent(_Agent):
    """Node actions plus END_DAY; exhausted seed choices advance the calendar."""
    label = "FLAT_DQN"

    def __init__(self, graph, budget, horizon, seed, device="cpu"):
        super().__init__(graph, budget, horizon, seed, device)
        self.ll, self.ll_target, self.ll_optimizer = self._learner(NodeQ(wait=True))

    def _mask(self, env):
        seeds = env.legal_mask()
        end_day = not env.done and not (env.remaining_days == 1 and seeds.any())
        return np.r_[seeds, end_day]

    def run_episode(self, env, training=True):
        phase, before, counters, actions, days = self._begin(env, training)
        losses = []
        while not env.done:
            if not env.legal_mask().any():
                while not env.done:
                    self._finish_day(env, phase, days)
                break
            observation, day = env.observation(), env.day
            action = self._act(self.ll, observation, self._mask(env), training)
            if action == self.n:
                nxt, reward, terminal = self._finish_day(env, phase, days)
            else:
                nxt, reward, terminal = env.select(action, phase=phase)
            # No further seeding decisions remain: the last real transition
            # carries all remaining daily propagation rewards to the horizon.
            if not env.done and not env.legal_mask().any():
                while not env.done:
                    nxt, extra, terminal = self._finish_day(env, phase, days)
                    reward += extra
            legal = np.zeros(self.n + 1, dtype=bool) if terminal else self._mask(env)
            actions.append({"day": day, "action": action, "reward": reward,
                            "terminal": terminal})
            if training:
                self.ll_replay.append((observation["features"], action, reward,
                                       nxt["features"], legal, terminal, self.graph_id))
                # One update opportunity per actual day transition, including
                # automatic residual days after the last seed decision.
                for _ in range(env.day - day):
                    value = self._learn_ll()
                    if value is not None:
                        losses.append(value)
        return self._result(env, training, phase, before, counters, actions, days, losses)


class BudgetHRLAgent(_Agent):
    """Daily budget DQN and a separate, unconditioned node-selection DQN."""
    label = "BUDGET_HRL"

    def __init__(self, graph, budget, horizon, seed, device="cpu"):
        super().__init__(graph, budget, horizon, seed, device)
        self.ll, self.ll_target, self.ll_optimizer = self._learner(NodeQ())
        self.hl, self.hl_target, self.hl_optimizer = self._learner(BudgetQ(budget))
        self.hl_replay = deque(maxlen=1000)

    def _mask(self, observation):
        cap = min(observation["remaining_budget"], int(observation["legal_mask"].sum()))
        legal = np.arange(self.budget + 1) <= cap
        if observation["remaining_days"] == 1:
            legal[:] = False
            legal[cap] = True
        if observation["remaining_days"] == 0:
            legal[:] = False
        return legal

    def run_episode(self, env, training=True):
        phase, before, counters, actions, days = self._begin(env, training)
        losses = []
        while not env.done:
            start, pending = env.observation(), []
            cap = min(env.remaining_budget, int(start["legal_mask"].sum()))
            if env.remaining_days == 1:
                allocated = cap
            elif training and self.training_episodes < 3:
                allocated = min(cap, math.ceil(env.remaining_budget / env.remaining_days))
            else:
                allocated = self._act(self.hl, start, self._mask(start), training)
            selected = []
            for _ in range(allocated):
                if not env.legal_mask().any():
                    break
                current = env.observation()
                action = self._act(self.ll, current, env.legal_mask(), training)
                nxt, reward, _ = env.select(action, phase=phase)
                selected.append(action)
                pending.append([current["features"], action, reward,
                                nxt["features"], env.legal_mask(), False])
            nxt, spread, terminal = self._finish_day(env, phase, days)
            if pending:
                pending[-1][2] += spread
                pending[-1][3:] = [nxt["features"], np.zeros(self.n, dtype=bool), True]
            day_reward = len(selected) + spread
            actions.append({"day": env.day - 1, "budget": allocated, "selected": selected,
                            "realized_duration": len(selected), "reward": day_reward})
            if training:
                self.ll_replay.extend((*row, self.graph_id) for row in pending)
                self.hl_replay.append((start["features"], allocated, day_reward,
                                       nxt["features"], self._mask(nxt), terminal, self.graph_id))
                ll = self._learn_ll()
                hl = self._update(self.hl_replay, self.hl, self.hl_target,
                                  self.hl_optimizer, "hl")
                losses.extend(value for value in (ll, hl) if value is not None)
        return self._result(env, training, phase, before, counters, actions, days, losses)


ARMS = {"FLAT_DQN": FlatDQNAgent, "BUDGET_HRL": BudgetHRLAgent}
