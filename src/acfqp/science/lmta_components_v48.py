"""Evaluation-only budget/selection crossings of the retained hierarchy."""
import math

import numpy as np
import torch

from .lmta_heuristics_v44 import AverageScoreAgent
from .lmta_models_v43 import epsilon_action, features


class ComponentPolicy:
    def __init__(self, agent, method, budget_rule, selection_rule):
        if method not in ('BUDGET_HRL', 'LMTA_RI'):
            raise ValueError('Component evaluation requires a hierarchical method')
        if budget_rule not in ('LEARNED', 'AVERAGE') or selection_rule not in ('LEARNED', 'SCORE'):
            raise ValueError('Unknown budget or selection rule')
        self.agent, self.method = agent, method
        self.budget_rule, self.selection_rule = budget_rule, selection_rule

    @property
    def device(self):
        return self.agent.device

    @property
    def counts(self):
        return self.agent.counts

    @torch.no_grad()
    def run_episode(self, env, training=False):
        if training:
            raise ValueError('ComponentPolicy only evaluates frozen weights')
        agent = self.agent
        agent.set_graph(env.graph)
        self.graph = env.graph  # AverageScoreAgent.choose reads this graph.
        before = dict(env.counters.get('evaluation', {}))
        env.reset()
        lmta = self.method == 'LMTA_RI'
        needs_goal = lmta and (self.budget_rule == 'LEARNED' or self.selection_rule == 'LEARNED')
        if lmta:
            agent.model.train(False)
            agent.low.train(False)
        actions, days, total = [], [], 0.
        while not env.done:
            day, obs = env.day, env.observation()
            capacity = min(int(obs['remaining_budget']), int(obs['legal_mask'].sum()))
            last_day = env.remaining_days == 1
            forced = last_day or capacity == 0
            z, search_value, goal = None, None, None
            if needs_goal:
                self.counts['component_search_requests'] += 1
                policy, search_value = agent.search(obs, False)
                z = int(policy.argmax())
                goal = agent.model.goal(torch.tensor(z, device=self.device))
                self.counts['component_goal_embedding_calls'] += 1

            if self.budget_rule == 'AVERAGE':
                allocated = capacity if last_day else min(capacity,
                    math.ceil(int(obs['remaining_budget']) / int(obs['remaining_days'])))
            elif lmta:
                # Keep the original evaluation arithmetic, including softmax
                # before argmax and its head call on forced/zero-capacity days.
                h = agent.model.encoder(features(obs, self.device), agent.a)
                logits = agent.model.budget(torch.cat((h, goal)))[:capacity + 1]
                probabilities = logits.softmax(-1).cpu().numpy()
                self.counts['component_budget_state_encoder_calls'] += 1
                self.counts['component_budget_head_calls'] += 1
                allocated = capacity if forced else int(probabilities.argmax())
            elif last_day:
                allocated = capacity
            else:
                allocated = agent._act(agent.hl, obs, agent._mask(obs), False)
                self.counts['component_budget_head_calls'] += 1

            selected = []
            for _ in range(allocated):
                if not env.legal_mask().any():
                    break
                if self.selection_rule == 'SCORE':
                    self.counts['component_score_calls'] += 1
                    self.counts['component_score_candidate_evaluations'] += int(env.legal_mask().sum())
                    action = AverageScoreAgent.choose(self, env)
                else:
                    current = env.observation()
                    if lmta:
                        q = agent.low(features(current, self.device), agent.a, goal)
                        action = epsilon_action(q, current['legal_mask'], 0., agent.rng)
                    else:
                        action = agent._act(agent.ll, current, current['legal_mask'], False)
                    self.counts['component_low_head_calls'] += 1
                env.select(action, phase='evaluation')
                selected.append(int(action))
            _, spread, _, info = env.finish_day(phase='evaluation')
            reward = float(len(selected) + spread)
            total += reward
            actions.append(dict(day=day, budget=allocated, selected=selected,
                realized_duration=len(selected), reward=reward))
            if lmta:
                days.append(dict(day=day, z=z, budget=allocated, duration=len(selected),
                    reward=reward, search_value=search_value, capacity=capacity, forced=forced))
            else:
                days.append(dict(day=day, **info))
        increments = {name: value - before.get(name, 0) for name, value in env.counters['evaluation'].items()}
        return dict(arm=self.method, budget_rule=self.budget_rule, selection_rule=self.selection_rule,
            raw_return=total, **increments, actions=actions, day_history=days, losses=[],
            train_updates=0, replay_draws=0, epsilon=0.)
