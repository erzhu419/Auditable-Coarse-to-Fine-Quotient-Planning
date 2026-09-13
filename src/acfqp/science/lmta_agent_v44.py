"""V43 LMTA-RI with replay bound to each sample's original graph (V44)."""
from __future__ import annotations

from collections import Counter, deque
from copy import deepcopy
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .lmta_models_v43 import Encoder, NodeQ, adjacency, epsilon_action, features, masked_max, mlp, optimizer_step


class WorldModel(nn.Module):
    def __init__(self, budget):
        super().__init__()
        self.encoder = Encoder()
        self.goals = nn.Embedding(32, 128)
        self.dynamics = mlp(256, 128)
        self.reward = mlp(256, 1)
        self.policy = mlp(128, 32)
        self.value = mlp(128, 1)
        self.budget = mlp(256, budget + 1)
        self.budget_value = mlp(256, 1)
        self.margin = nn.Linear(128, 1)

    def goal(self, z):
        return F.normalize(self.goals(z), dim=-1)

    def recurrent(self, h, z):
        x = torch.cat((h, self.goal(z)), dim=-1)
        return F.normalize(self.dynamics(x), dim=-1), self.reward(x).squeeze(-1)


def mts_terms(micro_before, micro_after, macro_before, macro_predicted, margins, durations):
    pull = F.relu((micro_after - micro_before).norm(dim=-1) - .1).square().mean()
    distance = (macro_predicted - macro_before).norm(dim=-1)
    push = F.relu(margins - distance).mean()
    score = distance + margins
    sign = torch.sign(durations[:, None] - durations[None, :])
    order = F.relu(1. - sign * (score[:, None] - score[None, :])).mean()
    return pull, push, order


class Node:
    def __init__(self, h, prior, reward=0.):
        self.h, self.prior, self.reward = h, prior, reward
        self.visits = np.zeros(32, dtype=np.int64)
        self.sums = np.zeros(32, dtype=np.float64)
        self.children = {}


class LMTAAgent:
    def __init__(self, graph, budget, horizon, seed, device='cpu', simulations=150):
        self.device = torch.device(device)
        torch.manual_seed(seed)
        self.rng = np.random.default_rng(seed)
        self.adjacency_cache = {}
        self.set_graph(graph)
        self.model = WorldModel(budget).to(self.device)
        self.low = NodeQ(goal_size=128).to(self.device)
        self.low.encoder = self.model.encoder
        self.target = deepcopy(self.low)
        self.optim = torch.optim.Adam(self.model.parameters(), lr=1e-3, weight_decay=1e-5)
        self.low_optim = torch.optim.Adam(self.low.parameters(), lr=1e-3, weight_decay=1e-5)
        self.games, self.low_replay = deque(maxlen=1000), deque(maxlen=10000)
        self.episodes, self.counts = 0, Counter()
        self.simulations, self.budget_limit, self.horizon = simulations, budget, horizon

    def set_graph(self, graph):
        # Runner-assigned seed identifiers are stable through AIM graph copies.
        self.graph_id = graph.graph['replay_id']
        if self.graph_id not in self.adjacency_cache:
            self.adjacency_cache[self.graph_id] = adjacency(graph, self.device)
        self.a = self.adjacency_cache[self.graph_id]

    @torch.no_grad()
    def search(self, observation, training):
        h = self.model.encoder(features(observation, self.device), self.a)
        prior = self.model.policy(h).softmax(-1).cpu().numpy()
        if training:
            prior = .7 * prior + .3 * self.rng.dirichlet(np.full(32, .3))
        root = Node(h, prior)
        q_min, q_max = math.inf, -math.inf
        depth_limit = int(observation['remaining_days'])
        for _ in range(self.simulations):
            node, path = root, []
            for depth in range(depth_limit):
                q = np.divide(node.sums, node.visits, out=np.zeros(32), where=node.visits > 0)
                if q_max > q_min:
                    q = np.where(node.visits > 0, (q - q_min) / (q_max - q_min), 0.)
                count = int(node.visits.sum())
                c = 2.5 + math.log((count + 19653.) / 19652.)
                score = q + c * node.prior * math.sqrt(count + 1.) / (1. + node.visits)
                z = int(np.argmax(score))
                path.append((node, z))
                if z not in node.children:
                    next_h, reward = self.model.recurrent(node.h, torch.tensor(z, device=self.device))
                    prior = self.model.policy(next_h).softmax(-1).cpu().numpy()
                    child = Node(next_h, prior, float(reward))
                    node.children[z] = child
                    self.counts['latent_recurrent_calls'] += 1
                    value = 0. if depth + 1 == depth_limit else float(self.model.value(next_h).squeeze())
                    break
                node = node.children[z]
                value = 0.
            for parent, z in reversed(path):
                value = parent.children[z].reward + .997 * value
                parent.visits[z] += 1
                parent.sums[z] += value
                updated_q = parent.sums[z] / parent.visits[z]
                q_min, q_max = min(q_min, updated_q), max(q_max, updated_q)
            self.counts['mcts_simulations'] += 1
        self.counts['root_searches'] += 1
        probabilities = root.visits / root.visits.sum()
        return probabilities, float(root.sums.sum() / root.visits.sum())

    def run_episode(self, env, training=True):
        self.set_graph(env.graph)
        env.reset()
        phase = 'train' if training else 'evaluation'
        self.model.train(training)
        self.low.train(training)
        game, total, selections = [], 0., 0
        losses = []
        epsilon = max(.05, .9 * .995 ** self.episodes) if training else 0.
        for day in range(env.horizon):
            obs = env.observation()
            policy, search_value = self.search(obs, training)
            z = int(self.rng.choice(32, p=policy)) if training else int(policy.argmax())
            remaining = int(obs['remaining_budget'])
            capacity = min(remaining, int(np.sum(obs['legal_mask'])))
            forced = day == env.horizon - 1 or capacity == 0
            warmup = training and self.episodes < 3
            with torch.no_grad():
                h = self.model.encoder(features(obs, self.device), self.a)
                goal = self.model.goal(torch.tensor(z, device=self.device))
                logits = self.model.budget(torch.cat((h, goal)))[:capacity + 1]
                probabilities = logits.softmax(-1).cpu().numpy()
            if forced:
                budget = capacity
            elif warmup:
                budget = min(capacity, math.ceil(remaining / obs['remaining_days']))
            else:
                budget = int(self.rng.choice(capacity + 1, p=probabilities)) if training else int(probabilities.argmax())
            transitions = []
            for _ in range(budget):
                before = env.observation()
                with torch.no_grad():
                    q = self.low(features(before, self.device), self.a, goal)
                action = epsilon_action(q, before['legal_mask'], epsilon, self.rng)
                after, reward, _ = env.select(action, phase=phase)
                transitions.append([before['features'], z, action, reward, after['features'], after['legal_mask'], False, self.graph_id])
            after, spread, _, _ = env.finish_day(phase=phase)
            if transitions:
                transitions[-1][3] += spread
                transitions[-1][4:7] = [after['features'], after['legal_mask'], True]
            reward = len(transitions) + spread
            total += reward
            selections += len(transitions)
            if game:
                game[-1]['next_search_value'] = search_value
            game.append(dict(features=obs['features'], next_features=after['features'], z=z, budget=budget,
                capacity=capacity, forced=forced, warmup=warmup, duration=len(transitions), reward=float(reward),
                policy=policy, search_value=search_value, next_search_value=0., graph_id=self.graph_id))
            if training:
                self.low_replay.extend(transitions)
                low_loss = self.update_low()
                if low_loss is not None:
                    losses.append(low_loss)
        if training:
            value = 0.
            for row in reversed(game):
                value = row['reward'] + .997 * value
                row['return'] = value
            self.games.append(game)
            loss = self.update_high()
            if loss is not None:
                losses.append(loss)
            self.episodes += 1
        day_history = [dict(day=day, **{key: row[key] for key in
            ('z', 'budget', 'duration', 'reward', 'search_value', 'capacity', 'forced')})
            for day, row in enumerate(game)]
        return dict(raw_return=total, primitive_selections=selections,
                    day_transitions=env.horizon, losses=losses, day_history=day_history)

    def update_low(self):
        if len(self.low_replay) < 8:
            return None
        indices = self.rng.choice(len(self.low_replay), 8, replace=False)
        batch = [self.low_replay[int(i)] for i in indices]
        s, z, action, reward, nxt, legal, done, graph_ids = zip(*batch)
        batch_adjacency = torch.stack([self.adjacency_cache[graph_id] for graph_id in graph_ids])
        states = torch.as_tensor(np.asarray(s), device=self.device)
        next_states = torch.as_tensor(np.asarray(nxt), device=self.device)
        goals = self.model.goal(torch.tensor(z, device=self.device)).detach()
        prediction = self.low(states, batch_adjacency, goals).gather(1, torch.tensor(action, device=self.device)[:, None]).squeeze(1)
        with torch.no_grad():
            continuation = masked_max(self.target(next_states, batch_adjacency, goals), np.asarray(legal))
            target = torch.tensor(reward, device=self.device) + .997 * continuation * (~torch.tensor(done, device=self.device))
        loss = F.mse_loss(prediction, target)
        optimizer_step(self.low_optim, loss, self.low.parameters())
        self.counts['LL_gradient_steps'] += 1
        self.counts['LL_replay_samples'] += 8
        if self.counts['LL_gradient_steps'] % 100 == 0:
            self.target.load_state_dict(self.low.state_dict())
        return float(loss.detach())

    def update_high(self):
        if len(self.games) < 8:
            return None
        games = [self.games[int(i)] for i in self.rng.choice(len(self.games), 8, replace=False)]
        prediction_losses, budget_losses, macro_before, macro_pred, margins, durations = [], [], [], [], [], []
        transitions = 0
        for game in games:
            start = int(self.rng.integers(len(game)))
            game_adjacency = self.adjacency_cache[game[start]['graph_id']]
            h = self.model.encoder(torch.as_tensor(game[start]['features'], device=self.device), game_adjacency)
            for row in game[start:start + 5]:
                z = torch.tensor(row['z'], device=self.device)
                predicted_policy = self.model.policy(h).log_softmax(-1)
                target_policy = torch.as_tensor(row['policy'], dtype=torch.float32, device=self.device)
                value_loss = (self.model.value(h).squeeze() - row['return']).square()
                next_h, predicted_reward = self.model.recurrent(h, z)
                prediction_losses.append(-(target_policy * predicted_policy).sum() + value_loss + (predicted_reward - row['reward']).square())
                # Budget actor-critic observes the real stored state, not imagined unroll states.
                actual_h = self.model.encoder(torch.as_tensor(row['features'], device=self.device), game_adjacency)
                goal = self.model.goal(z)
                joined = torch.cat((actual_h, goal))
                if not row['warmup']:
                    advantage = row['reward'] + .997 * row['next_search_value'] - self.model.budget_value(joined).squeeze()
                    logits = self.model.budget(joined)[:row['capacity'] + 1]
                    log_p = logits.log_softmax(-1)
                    actor = log_p.sum() * 0. if row['forced'] else -log_p[row['budget']] * advantage.detach() + .01 * (log_p.exp() * log_p).sum()
                    budget_losses.append(advantage.square() + actor)
                actual_pred, _ = self.model.recurrent(actual_h, z)
                macro_before.append(actual_h)
                macro_pred.append(actual_pred)
                margins.append(F.softplus(self.model.margin(goal)).squeeze())
                durations.append(row['duration'])
                transitions += 1
                h = next_h
        indices = self.rng.choice(len(self.low_replay), 8, replace=False)
        micro = [self.low_replay[int(i)] for i in indices]
        micro_adjacency = torch.stack([self.adjacency_cache[row[7]] for row in micro])
        before = self.model.encoder(torch.as_tensor(np.asarray([r[0] for r in micro]), device=self.device), micro_adjacency)
        after = self.model.encoder(torch.as_tensor(np.asarray([r[4] for r in micro]), device=self.device), micro_adjacency)
        pull, push, order = mts_terms(before, after, torch.stack(macro_before), torch.stack(macro_pred), torch.stack(margins), torch.tensor(durations, device=self.device))
        all_goals = self.model.goal(torch.arange(32, device=self.device))
        margin_penalty = 1e-4 * F.softplus(self.model.margin(all_goals)).square().sum()
        loss = torch.stack(prediction_losses).mean() + .1 * (pull + push + order) + margin_penalty
        if budget_losses:
            loss = loss + torch.stack(budget_losses).mean()
        optimizer_step(self.optim, loss, self.model.parameters())
        self.counts.update(HL_gradient_steps=1, HL_replay_games=8, HL_replay_transitions=transitions, MTS_micro_replay_samples=8)
        if budget_losses:
            self.counts['budget_gradient_steps'] += 1
        return float(loss.detach())
