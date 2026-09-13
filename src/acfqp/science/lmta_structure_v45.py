"""Zero-environment AIM structure diagnostics; fixed network weights are external.

Rows index source nodes and columns index target nodes. The candidate uses
W = I + B, with B[u,v] = 1 / indegree(v) on directed edges. It preserves the
one-step weighted-IC score in a first message from constant initial features.
"""
from __future__ import annotations

import math

import numpy as np
import torch


def weighted_adjacency(graph, device='cpu', dtype=torch.float64):
    """Self contribution plus outgoing target-influence weights, without averaging."""
    matrix = torch.eye(len(graph), dtype=dtype, device=device)
    for source, target in graph.edges:
        matrix[source, target] += 1. / graph.in_degree(target)
    return matrix


def mean_adjacency(graph, device='cpu', dtype=torch.float64):
    """V43 mean+self-loop formula, with all arithmetic in the requested dtype."""
    matrix = torch.eye(len(graph), dtype=dtype, device=device)
    for source, target in graph.edges:
        matrix[source, target] = 1.
    return matrix / matrix.sum(dim=1, keepdim=True)


def exact_one_step_score(graph):
    """Expected new neighbors from one seed in an all-inactive directed IC graph.

    This excludes the seed's own deterministic reward and uses no random draws.
    V45 graphs are the retained directed ER graphs on nodes 0..n-1, without loops.
    """
    return np.asarray([math.fsum(1. / graph.in_degree(target)
                                for target in graph.successors(source))
                       for source in range(len(graph))], dtype=np.float64)


def initial_features(n, device='cpu', dtype=torch.float64):
    """All inactive, with the full day and seed budgets remaining."""
    return torch.tensor([1., 0., 0., 1., 1.], dtype=dtype, device=device).repeat(n, 1)


def one_step_readout(first_message):
    """Recover the neighbor score by subtracting the deterministic self message."""
    return first_message[:, 0] - 1.


def spread_summary(values):
    """Node-row spread for a feature matrix or a vector of legal seed Q values."""
    values = torch.as_tensor(values).detach()
    coordinate_ranges = values.amax(dim=0) - values.amin(dim=0)
    row_range = float(coordinate_ranges.max())
    magnitude = float(values.abs().max())
    summary = dict(max_coordinate_row_range=row_range, max_abs=magnitude,
                   scaled_row_range=row_range / max(1., magnitude))
    if values.ndim == 1:
        summary['q_range'] = row_range
    return summary
