"""Shared networks for the explicitly independent V43 implementation."""
from __future__ import annotations

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


def adjacency(graph, device):
    """Outgoing-neighbor mean with self loops; a recorded implementation choice."""
    a = np.eye(len(graph), dtype=np.float32)
    for u, v in graph.edges:
        a[u, v] = 1.0
    a /= a.sum(axis=1, keepdims=True)
    return torch.as_tensor(a, device=device)


class Encoder(nn.Module):
    def __init__(self, width=128):
        super().__init__()
        self.first = nn.Linear(5, width)
        self.second = nn.Linear(width, width)
        self.project = nn.Linear(width, width)

    def nodes(self, x, a):
        x = F.relu(self.first(a @ x))
        return F.relu(self.second(a @ x))

    def forward(self, x, a):
        return F.normalize(self.project(self.nodes(x, a).mean(dim=-2)), dim=-1)


def mlp(inputs, outputs, width=128):
    return nn.Sequential(nn.Linear(inputs, width), nn.ReLU(), nn.Linear(width, outputs))


class NodeQ(nn.Module):
    def __init__(self, goal_size=0, width=128, wait=False):
        super().__init__()
        self.encoder = Encoder(width)
        self.head = mlp(width + goal_size, 1, width)
        self.wait_head = mlp(width, 1, width) if wait else None

    def forward(self, x, a, goal=None):
        nodes = self.encoder.nodes(x, a)
        if goal is not None:
            goal = goal.unsqueeze(-2).expand(*nodes.shape[:-1], goal.shape[-1])
            inputs = torch.cat((nodes, goal), dim=-1)
        else:
            inputs = nodes
        q = self.head(inputs).squeeze(-1)
        if self.wait_head is not None:
            q = torch.cat((q, self.wait_head(nodes.mean(dim=-2))), dim=-1)
        return q


def features(observation, device):
    return torch.as_tensor(observation['features'], dtype=torch.float32, device=device)


def epsilon_action(q, legal, epsilon, rng):
    indices = np.flatnonzero(legal)
    if not len(indices):
        raise ValueError('No legal action at a decision point')
    if rng.random() < epsilon:
        return int(rng.choice(indices))
    scores = q.detach().cpu().numpy()
    return int(indices[np.argmax(scores[indices])])


def masked_max(q, legal):
    legal = torch.as_tensor(legal, dtype=torch.bool, device=q.device)
    values = q.masked_fill(~legal, -torch.inf).max(dim=-1).values
    return torch.where(legal.any(dim=-1), values, torch.zeros_like(values))


def optimizer_step(optimizer, loss, parameters):
    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(parameters, 5.0)
    optimizer.step()
