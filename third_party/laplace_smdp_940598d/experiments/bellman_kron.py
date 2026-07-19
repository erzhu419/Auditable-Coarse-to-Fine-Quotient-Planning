from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, Dict, Iterable, List, Mapping, Sequence, Tuple

import thread_limits  # noqa: F401
import networkx as nx
import numpy as np
from scipy.linalg import eigh


Action = str
State = int

ACTIONS: Tuple[Action, ...] = ("N", "S", "W", "E")
DELTAS: Mapping[Action, Tuple[int, int]] = {
    "N": (-1, 0),
    "S": (1, 0),
    "W": (0, -1),
    "E": (0, 1),
}
OPPOSITE: Mapping[Action, Action] = {"N": "S", "S": "N", "W": "E", "E": "W"}


@dataclass(frozen=True)
class GridWorld:
    rows: Tuple[str, ...]
    step_reward: float = -1.0
    wall: str = "#"

    def __post_init__(self) -> None:
        widths = {len(r) for r in self.rows}
        if len(widths) != 1:
            raise ValueError("All grid rows must have the same width.")

    @property
    def height(self) -> int:
        return len(self.rows)

    @property
    def width(self) -> int:
        return len(self.rows[0])

    @property
    def open_cells(self) -> List[Tuple[int, int]]:
        return [
            (r, c)
            for r, row in enumerate(self.rows)
            for c, ch in enumerate(row)
            if ch != self.wall
        ]

    @property
    def n_states(self) -> int:
        return len(self.open_cells)

    @lru_cache(maxsize=None)
    def index_maps(self) -> Tuple[Dict[Tuple[int, int], State], Dict[State, Tuple[int, int]]]:
        cells = self.open_cells
        coord_to_idx = {coord: i for i, coord in enumerate(cells)}
        idx_to_coord = {i: coord for i, coord in enumerate(cells)}
        return coord_to_idx, idx_to_coord

    def char_at(self, state: State) -> str:
        _, idx_to_coord = self.index_maps()
        r, c = idx_to_coord[state]
        return self.rows[r][c]

    def symbol_states(self, symbols: Iterable[str]) -> List[State]:
        symbols = set(symbols)
        coord_to_idx, _ = self.index_maps()
        out: List[State] = []
        for coord, idx in coord_to_idx.items():
            if self.rows[coord[0]][coord[1]] in symbols:
                out.append(idx)
        return out

    def legal_actions(self, state: State) -> List[Action]:
        coord_to_idx, idx_to_coord = self.index_maps()
        r, c = idx_to_coord[state]
        legal: List[Action] = []
        for action, (dr, dc) in DELTAS.items():
            if (r + dr, c + dc) in coord_to_idx:
                legal.append(action)
        return legal

    def next_state(self, state: State, action: Action) -> State:
        coord_to_idx, idx_to_coord = self.index_maps()
        r, c = idx_to_coord[state]
        dr, dc = DELTAS[action]
        return coord_to_idx.get((r + dr, c + dc), state)


@dataclass(frozen=True)
class BellmanKronReduction:
    boundary: np.ndarray
    interior: np.ndarray
    gamma: float
    gamma_terminal: np.ndarray
    reward: np.ndarray
    laplacian: np.ndarray
    hit_probability: np.ndarray
    expected_tau: np.ndarray
    used_steps: int = 0
    tail_mass: float = 0.0
    tail_bound: float = 0.0
    q_bound: float = 1.0


@dataclass(frozen=True)
class FirstHitReduction:
    terminals: np.ndarray
    gamma_terminal: np.ndarray
    reward: float
    hit_probability: np.ndarray
    expected_tau: np.ndarray
    used_steps: int = 0
    tail_mass: float = 0.0
    tail_bound: float = 0.0
    q_bound: float = 1.0


@dataclass(frozen=True)
class FirstHitGreenState:
    terminals: np.ndarray
    interior: np.ndarray
    fundamental: np.ndarray
    hit_probability: np.ndarray


def default_map() -> Tuple[str, ...]:
    return (
        "#####################",
        "#S....#.......#.....#",
        "#.###.#.#####.#.###.#",
        "#...#...#...#...#...#",
        "###.#####.#.#####.###",
        "#...#.....#.....#...#",
        "#.###.#.#####.#.###.#",
        "#.....#.......#....G#",
        "#####################",
    )


def corridor_map() -> Tuple[str, ...]:
    return (
        "#############",
        "#S.........G#",
        "#############",
    )


def open_room_map() -> Tuple[str, ...]:
    return (
        "#########",
        "#S......#",
        "#.......#",
        "#.......#",
        "#.......#",
        "#......G#",
        "#########",
    )


def four_rooms_map() -> Tuple[str, ...]:
    return (
        "#############",
        "#S....#.....#",
        "#.....#.....#",
        "#...........#",
        "#.....#.....#",
        "#.....#....G#",
        "#############",
    )


def decision_boundary_states(grid: GridWorld, keep_symbols: str = "SG") -> List[State]:
    """Keep endpoints, junctions, turns, and explicit symbolic states as graph nodes."""

    keep = set(grid.symbol_states(keep_symbols))
    boundaries: List[State] = []
    for s in range(grid.n_states):
        actions = grid.legal_actions(s)
        degree = len(actions)
        is_straight_corridor = degree == 2 and actions[0] == OPPOSITE.get(actions[1])
        if s in keep or degree != 2 or not is_straight_corridor:
            boundaries.append(s)
    return sorted(set(boundaries))


def all_boundary_states(grid: GridWorld, keep_symbols: str = "SG") -> List[State]:
    return list(range(grid.n_states))


def endpoint_boundary_states(grid: GridWorld, keep_symbols: str = "SG") -> List[State]:
    return sorted(set(grid.symbol_states(keep_symbols)))


def junction_boundary_states(grid: GridWorld, keep_symbols: str = "SG") -> List[State]:
    keep = set(grid.symbol_states(keep_symbols))
    boundaries: List[State] = []
    for s in range(grid.n_states):
        degree = len(grid.legal_actions(s))
        if s in keep or degree != 2:
            boundaries.append(s)
    return sorted(set(boundaries))


def graph_adjacency(grid: GridWorld) -> np.ndarray:
    n = grid.n_states
    A = np.zeros((n, n), dtype=float)
    for s in range(n):
        for action in grid.legal_actions(s):
            ns = grid.next_state(s, action)
            A[s, ns] = 1.0
            A[ns, s] = 1.0
    return A


def graph_nx(grid: GridWorld) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(range(grid.n_states))
    for s in range(grid.n_states):
        for action in grid.legal_actions(s):
            G.add_edge(s, grid.next_state(s, action))
    return G


def spectral_boundary_states(
    grid: GridWorld,
    keep_symbols: str = "SG",
    fraction: float = 0.35,
    n_vectors: int = 6,
) -> List[State]:
    """Select high local spectral-energy states as candidate graph landmarks."""

    n = grid.n_states
    keep = set(grid.symbol_states(keep_symbols))
    if n <= len(keep):
        return sorted(keep)
    A = graph_adjacency(grid)
    D = np.diag(A.sum(axis=1))
    L = D - A
    n_vec = max(1, min(n_vectors, n - 1))
    vals, vecs = eigh(L)
    nontrivial = vecs[:, 1 : n_vec + 1]
    lambdas = vals[1 : n_vec + 1]
    score = np.zeros(n, dtype=float)
    for s in range(n):
        for ns in np.flatnonzero(A[s] > 0):
            diff = nontrivial[s] - nontrivial[ns]
            score[s] += float(np.sum((lambdas + 1e-9) * diff * diff))
    k = max(len(keep), int(round(fraction * n)))
    chosen = set(np.argsort(score)[-k:].tolist())
    chosen.update(keep)
    return sorted(chosen)


def action_distribution(action: Action, slip: float = 0.0) -> Dict[Action, float]:
    """Directional option policy with optional uniform slippage to other actions."""

    if not 0.0 <= slip < 1.0:
        raise ValueError("slip must be in [0, 1).")
    other = [a for a in ACTIONS if a != action]
    dist = {a: slip / len(other) for a in other}
    dist[action] = 1.0 - slip
    return dist


def mix_slip(action: Action, slip: float = 0.0) -> Dict[Action, float]:
    return action_distribution(action, slip=slip)


def transition_matrix_for_direction(
    grid: GridWorld,
    action: Action,
    slip: float = 0.0,
    absorbing: Sequence[State] = (),
) -> Tuple[np.ndarray, np.ndarray]:
    """One-step primitive dynamics induced by a directional option."""

    n = grid.n_states
    absorbing_set = set(absorbing)
    P = np.zeros((n, n), dtype=float)
    r = np.full(n, grid.step_reward, dtype=float)
    dist = action_distribution(action, slip=slip)
    for s in range(n):
        if s in absorbing_set:
            P[s, s] = 1.0
            r[s] = 0.0
            continue
        for a, p in dist.items():
            ns = grid.next_state(s, a)
            P[s, ns] += p
    return P, r


PolicyFn = Callable[[State], Mapping[Action, float]]


def constant_policy(action: Action, slip: float = 0.0) -> PolicyFn:
    def policy(state: State) -> Mapping[Action, float]:
        return action_distribution(action, slip=slip)

    return policy


def transition_matrix_for_policy(
    grid: GridWorld,
    policy: PolicyFn,
    absorbing: Sequence[State] = (),
) -> Tuple[np.ndarray, np.ndarray]:
    n = grid.n_states
    absorbing_set = set(absorbing)
    P = np.zeros((n, n), dtype=float)
    r = np.full(n, grid.step_reward, dtype=float)
    for s in range(n):
        if s in absorbing_set:
            P[s, s] = 1.0
            r[s] = 0.0
            continue
        dist = dict(policy(s))
        total = sum(dist.values())
        if total <= 0:
            raise ValueError(f"Policy has no mass at state {s}.")
        for a, p in dist.items():
            ns = grid.next_state(s, a)
            P[s, ns] += p / total
    return P, r


def shortest_path_distances_to_target(grid: GridWorld, target: State) -> np.ndarray:
    coord_to_idx, idx_to_coord = grid.index_maps()
    target_coord = idx_to_coord[target]
    distances: Dict[Tuple[int, int], int] = {target_coord: 0}
    frontier = [target_coord]
    while frontier:
        coord = frontier.pop(0)
        for dr, dc in DELTAS.values():
            prev = (coord[0] + dr, coord[1] + dc)
            if prev in coord_to_idx and prev not in distances:
                distances[prev] = distances[coord] + 1
                frontier.append(prev)
    out = np.full(grid.n_states, np.inf, dtype=float)
    for coord, distance in distances.items():
        out[coord_to_idx[coord]] = float(distance)
    return out


def shortest_path_policy_to_target(
    grid: GridWorld,
    target: State,
    slip: float = 0.0,
) -> PolicyFn:
    coord_to_idx, idx_to_coord = grid.index_maps()
    distances = shortest_path_distances_to_target(grid, target)

    def policy(state: State) -> Mapping[Action, float]:
        if state == target:
            return {"N": 1.0}
        r, c = idx_to_coord[state]
        best_action = "N"
        best_distance = float("inf")
        for action, (dr, dc) in DELTAS.items():
            nxt = (r + dr, c + dc)
            if nxt in coord_to_idx and distances[coord_to_idx[nxt]] < best_distance:
                best_distance = distances[coord_to_idx[nxt]]
                best_action = action
        return mix_slip(best_action, slip=slip)

    return policy


def shortest_path_distance_matrix(grid: GridWorld) -> np.ndarray:
    return np.stack([shortest_path_distances_to_target(grid, target) for target in range(grid.n_states)], axis=1)


def _sparsify_saliency(score: np.ndarray, top_fraction: float) -> np.ndarray:
    score = np.nan_to_num(score.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    score[score < 0.0] = 0.0
    if score.max() <= 0.0:
        return score
    if 0.0 < top_fraction < 1.0:
        positive = np.flatnonzero(score > 0.0)
        if len(positive) > 0:
            k = max(1, int(round(top_fraction * len(score))))
            keep = positive[np.argsort(score[positive])[-min(k, len(positive)) :]]
            sparse = np.zeros_like(score)
            sparse[keep] = score[keep]
            score = sparse
    max_score = score.max()
    if max_score > 0.0:
        score = score / max_score
    return score


def critical_saliency(
    grid: GridWorld,
    kind: str,
    goal_state: State | None = None,
    gamma: float = 0.97,
    slip: float = 0.0,
    top_fraction: float = 0.15,
) -> np.ndarray:
    """State saliency used to charge options for bypassing hidden structure."""

    if kind == "none":
        return np.zeros(grid.n_states, dtype=float)

    if kind == "decision":
        score = np.zeros(grid.n_states, dtype=float)
        score[decision_boundary_states(grid)] = 1.0
        return score

    if kind == "bottleneck":
        G = graph_nx(grid)
        articulation = set(nx.articulation_points(G))
        centrality = nx.betweenness_centrality(G, normalized=True)
        score = np.zeros(grid.n_states, dtype=float)
        for s in range(grid.n_states):
            actions = grid.legal_actions(s)
            is_straight_corridor = len(actions) == 2 and actions[0] == OPPOSITE.get(actions[1])
            if s in articulation and not is_straight_corridor:
                score[s] = 1.0 + centrality.get(s, 0.0)
            elif len(actions) <= 3 and not is_straight_corridor:
                score[s] = centrality.get(s, 0.0)
        if score.max() <= 0.0:
            return score
        if 0.0 < top_fraction < 1.0:
            positive = np.flatnonzero(score > 0.0)
            k = max(1, int(round(top_fraction * len(score))))
            keep = positive[np.argsort(score[positive])[-min(k, len(positive)) :]]
            sparse = np.zeros_like(score)
            sparse[keep] = score[keep]
            score = sparse
        return score

    if kind == "betweenness":
        G = graph_nx(grid)
        score = np.array([v for _, v in sorted(nx.betweenness_centrality(G, normalized=True).items())])
        return _sparsify_saliency(score, top_fraction=top_fraction)

    if kind == "value_gradient":
        if goal_state is None:
            raise ValueError("goal_state is required for value_gradient saliency.")
        V = primitive_value_iteration(grid, goal_state=goal_state, gamma=gamma, slip=slip)
        score = np.zeros(grid.n_states, dtype=float)
        for s in range(grid.n_states):
            diffs = [abs(float(V[s] - V[grid.next_state(s, action)])) for action in grid.legal_actions(s)]
            score[s] = max(diffs) if diffs else 0.0
        return _sparsify_saliency(score, top_fraction=top_fraction)

    if kind == "transition_entropy":
        score = np.zeros(grid.n_states, dtype=float)
        for s in range(grid.n_states):
            best_entropy = 0.0
            for action in ACTIONS:
                probs: Dict[int, float] = {}
                for a, p in action_distribution(action, slip=slip).items():
                    ns = grid.next_state(s, a)
                    probs[ns] = probs.get(ns, 0.0) + p
                p_vec = np.array(list(probs.values()), dtype=float)
                p_vec = p_vec[p_vec > 0.0]
                entropy = float(-np.sum(p_vec * np.log(p_vec)))
                best_entropy = max(best_entropy, entropy)
            score[s] = best_entropy
        return _sparsify_saliency(score, top_fraction=top_fraction)

    if kind == "combined":
        parts = [
            critical_saliency(grid, "bottleneck", goal_state, gamma, slip, top_fraction),
            critical_saliency(grid, "value_gradient", goal_state, gamma, slip, top_fraction),
            critical_saliency(grid, "transition_entropy", goal_state, gamma, slip, top_fraction),
        ]
        return _sparsify_saliency(np.maximum.reduce(parts), top_fraction=top_fraction)

    raise ValueError(f"Unknown critical saliency kind: {kind}")


def _policy_vector(policy: PolicyFn, state: State) -> np.ndarray:
    dist = dict(policy(state))
    total = sum(dist.values())
    if total <= 0:
        raise ValueError(f"Policy has no mass at state {state}.")
    return np.array([dist.get(action, 0.0) / total for action in ACTIONS], dtype=float)


def policy_complexity(grid: GridWorld, policy: PolicyFn) -> Dict[str, float]:
    """Cheap tabular option-policy complexity probes."""

    vectors = np.stack([_policy_vector(policy, s) for s in range(grid.n_states)], axis=0)
    greedy = vectors.argmax(axis=1)
    tv = 0.0
    undirected_edges: List[Tuple[int, int]] = []
    for s in range(grid.n_states):
        for action in grid.legal_actions(s):
            ns = grid.next_state(s, action)
            if s < ns:
                undirected_edges.append((s, ns))
                tv += float(np.sum(np.abs(vectors[s] - vectors[ns])))

    seen = np.zeros(grid.n_states, dtype=bool)
    regions = 0
    for start in range(grid.n_states):
        if seen[start]:
            continue
        regions += 1
        seen[start] = True
        stack = [start]
        while stack:
            s = stack.pop()
            for action in grid.legal_actions(s):
                ns = grid.next_state(s, action)
                if not seen[ns] and greedy[ns] == greedy[s]:
                    seen[ns] = True
                    stack.append(ns)

    return {
        "policy_tv": tv,
        "policy_regions": float(regions),
        "policy_tv_per_edge": tv / max(1, len(undirected_edges)),
    }


def _solve_or_pinv(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    try:
        return np.linalg.solve(A, B)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(A) @ B


def substochastic_q_bound(P_II: np.ndarray) -> float:
    if P_II.size == 0:
        return 0.0
    return float(np.max(np.sum(np.maximum(P_II, 0.0), axis=1), initial=0.0))


def geometric_tail_bound(q: float, steps_after_prefix: int) -> float:
    if q < 0.0:
        return 0.0
    if q >= 1.0:
        return float("inf")
    return float((q ** max(0, int(steps_after_prefix))) / max(1e-12, 1.0 - q))


def bellman_kron_reduce(
    P: np.ndarray,
    r: np.ndarray,
    boundary: Sequence[State],
    gamma: float,
) -> BellmanKronReduction:
    """Eliminate interior states for a fixed option-induced transition matrix.

    The reduced kernel is
        Gamma = gamma P_BB + gamma^2 P_BI (I - gamma P_II)^-1 P_IB
    and the reduced reward is
        Rbar = r_B + gamma P_BI (I - gamma P_II)^-1 r_I.
    """

    n = P.shape[0]
    B = np.array(sorted(boundary), dtype=int)
    B_set = set(B.tolist())
    I = np.array([s for s in range(n) if s not in B_set], dtype=int)

    P_BB = P[np.ix_(B, B)]
    P_BI = P[np.ix_(B, I)]
    P_IB = P[np.ix_(I, B)]
    P_II = P[np.ix_(I, I)]
    r_B = r[B]
    r_I = r[I]

    if len(I) == 0:
        gamma_terminal = gamma * P_BB
        reward = r_B.copy()
        hit_probability = P_BB.copy()
        expected_tau = np.ones_like(P_BB)
    else:
        A_gamma = np.eye(len(I)) - gamma * P_II
        N_gamma_PIB = _solve_or_pinv(A_gamma, P_IB)
        gamma_terminal = gamma * P_BB + (gamma**2) * P_BI @ N_gamma_PIB
        reward = r_B + gamma * P_BI @ _solve_or_pinv(A_gamma, r_I)

        A_one = np.eye(len(I)) - P_II
        N_one_PIB = _solve_or_pinv(A_one, P_IB)
        hit_probability = P_BB + P_BI @ N_one_PIB
        N_one_PII_N_one_PIB = _solve_or_pinv(A_one, P_II @ N_one_PIB)
        dgamma_at_one = P_BB + 2.0 * P_BI @ N_one_PIB + P_BI @ N_one_PII_N_one_PIB
        expected_tau = np.divide(
            dgamma_at_one,
            hit_probability,
            out=np.full_like(dgamma_at_one, np.nan),
            where=hit_probability > 1e-12,
        )

    laplacian = np.eye(len(B)) - gamma_terminal
    return BellmanKronReduction(
        boundary=B,
        interior=I,
        gamma=gamma,
        gamma_terminal=gamma_terminal,
        reward=reward,
        laplacian=laplacian,
        hit_probability=hit_probability,
        expected_tau=expected_tau,
    )


def bellman_kron_reduce_truncated(
    P: np.ndarray,
    r: np.ndarray,
    boundary: Sequence[State],
    gamma: float,
    k_steps: int,
    tail_tol: float = 0.0,
) -> BellmanKronReduction:
    """Truncated Neumann approximation to ``bellman_kron_reduce``.

    The exact reducer uses ``(I - gamma P_II)^-1`` and ``(I - P_II)^-1``.
    This approximation replaces both inverses by the finite prefix
    ``sum_{t=0}^K P_II^t``. It is substantially cheaper for repeated
    candidate scoring and is the executable counterpart of the truncated
    Green-kernel theorem in ``proof/``.
    """

    n = P.shape[0]
    B = np.array(sorted(boundary), dtype=int)
    B_set = set(B.tolist())
    I = np.array([s for s in range(n) if s not in B_set], dtype=int)

    P_BB = P[np.ix_(B, B)]
    P_BI = P[np.ix_(B, I)]
    P_IB = P[np.ix_(I, B)]
    P_II = P[np.ix_(I, I)]
    r_B = r[B]
    r_I = r[I]

    if len(I) == 0:
        gamma_terminal = gamma * P_BB
        reward = r_B.copy()
        hit_probability = P_BB.copy()
        expected_tau = np.ones_like(P_BB)
        used_steps = 0
        tail_mass = 0.0
        tail_bound = 0.0
        q_bound = 0.0
    else:
        k = max(0, int(k_steps))
        reward_extra = np.zeros(len(B), dtype=float)
        gamma_terminal_extra = np.zeros((len(B), len(B)), dtype=float)
        hit_extra = np.zeros((len(B), len(B)), dtype=float)
        tau_numerator = P_BB.copy()
        frontier = P_BI.copy()
        discount = 1.0
        used_steps = k
        tail_mass = float(np.max(np.sum(np.abs(frontier), axis=1), initial=0.0))
        tail_bound = float("inf")
        q_bound = substochastic_q_bound(P_II)
        for t in range(k + 1):
            terminal_flow = frontier @ P_IB
            reward_extra += discount * (frontier @ r_I)
            gamma_terminal_extra += discount * terminal_flow
            hit_extra += terminal_flow
            tau_numerator += float(t + 2) * terminal_flow
            frontier = frontier @ P_II
            used_steps = t
            tail_mass = float(np.max(np.sum(np.abs(frontier), axis=1), initial=0.0))
            hit_tail_bound = tail_mass
            reward_tail_bound = (
                (gamma * discount * gamma) * tail_mass / max(1e-12, 1.0 - gamma)
            )
            q_tail_bound = geometric_tail_bound(q_bound, t + 1)
            tail_bound = min(max(hit_tail_bound, reward_tail_bound), q_tail_bound)
            if tail_tol > 0.0 and tail_bound <= tail_tol:
                break
            discount *= gamma

        gamma_terminal = gamma * P_BB + (gamma**2) * gamma_terminal_extra
        reward = r_B + gamma * reward_extra
        hit_probability = P_BB + hit_extra
        expected_tau = np.divide(
            tau_numerator,
            hit_probability,
            out=np.full_like(tau_numerator, np.nan),
            where=hit_probability > 1e-12,
        )

    laplacian = np.eye(len(B)) - gamma_terminal
    return BellmanKronReduction(
        boundary=B,
        interior=I,
        gamma=gamma,
        gamma_terminal=gamma_terminal,
        reward=reward,
        laplacian=laplacian,
        hit_probability=hit_probability,
        expected_tau=expected_tau,
        used_steps=used_steps,
        tail_mass=tail_mass,
        tail_bound=tail_bound,
        q_bound=q_bound,
    )


def discounted_interior_occupancy(
    P: np.ndarray,
    boundary: Sequence[State],
    gamma: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return B, I, and gamma P_BI (I - gamma P_II)^-1."""

    n = P.shape[0]
    B = np.array(sorted(boundary), dtype=int)
    B_set = set(B.tolist())
    I = np.array([s for s in range(n) if s not in B_set], dtype=int)
    if len(I) == 0:
        return B, I, np.zeros((len(B), 0), dtype=float)
    P_BI = P[np.ix_(B, I)]
    P_II = P[np.ix_(I, I)]
    occupancy = gamma * P_BI @ _solve_or_pinv(np.eye(len(I)) - gamma * P_II, np.eye(len(I)))
    return B, I, occupancy


def first_hit_reduce(
    P: np.ndarray,
    r: np.ndarray,
    start_state: State,
    terminals: Sequence[State],
    gamma: float,
) -> FirstHitReduction:
    """Reduce a process from one start state to the first hit of a terminal set."""

    n = P.shape[0]
    T = np.array(sorted(set(terminals)), dtype=int)
    if start_state in set(T.tolist()):
        raise ValueError("start_state must not be in terminals.")
    if len(T) == 0:
        return FirstHitReduction(
            terminals=T,
            gamma_terminal=np.zeros(0, dtype=float),
            reward=0.0,
            hit_probability=np.zeros(0, dtype=float),
            expected_tau=np.zeros(0, dtype=float),
            used_steps=0,
            tail_mass=0.0,
            tail_bound=0.0,
            q_bound=0.0,
        )

    terminal_set = set(T.tolist())
    I = np.array([s for s in range(n) if s not in terminal_set], dtype=int)
    start_pos = int(np.flatnonzero(I == start_state)[0])
    P_II = P[np.ix_(I, I)]
    P_IT = P[np.ix_(I, T)]
    r_I = r[I]

    N_gamma = _solve_or_pinv(np.eye(len(I)) - gamma * P_II, np.eye(len(I)))
    reward = float((N_gamma @ r_I)[start_pos])
    gamma_terminal = gamma * N_gamma @ P_IT

    N_one = _solve_or_pinv(np.eye(len(I)) - P_II, np.eye(len(I)))
    hit_probability = N_one @ P_IT
    dgamma_at_one = N_one @ P_IT + N_one @ P_II @ N_one @ P_IT
    expected_tau = np.divide(
        dgamma_at_one,
        hit_probability,
        out=np.full_like(dgamma_at_one, np.nan),
        where=hit_probability > 1e-12,
    )

    return FirstHitReduction(
        terminals=T,
        gamma_terminal=gamma_terminal[start_pos],
        reward=reward,
        hit_probability=hit_probability[start_pos],
        expected_tau=expected_tau[start_pos],
    )


def first_hit_green_state(P: np.ndarray, terminals: Sequence[State]) -> FirstHitGreenState:
    """Exact non-discounted first-hit Green state for a terminal set.

    ``fundamental`` is ``(I - P_II)^-1`` and ``hit_probability`` is
    ``fundamental @ P_IT``. This state is intentionally policy-local: callers
    supply the transition matrix for one fixed option policy.
    """

    n = P.shape[0]
    T = np.array(sorted(set(int(state) for state in terminals)), dtype=int)
    terminal_set = set(T.tolist())
    I = np.array([state for state in range(n) if state not in terminal_set], dtype=int)
    if len(I) == 0:
        return FirstHitGreenState(
            terminals=T,
            interior=I,
            fundamental=np.zeros((0, 0), dtype=float),
            hit_probability=np.zeros((0, len(T)), dtype=float),
        )
    P_II = P[np.ix_(I, I)]
    P_IT = P[np.ix_(I, T)]
    N = _solve_or_pinv(np.eye(len(I)) - P_II, np.eye(len(I)))
    return FirstHitGreenState(
        terminals=T,
        interior=I,
        fundamental=N,
        hit_probability=N @ P_IT,
    )


def insert_first_hit_terminal(
    state: FirstHitGreenState,
    inserted_state: State,
    min_pivot: float = 1e-12,
) -> FirstHitGreenState:
    """Exact parent-to-child update when one interior state becomes terminal.

    If ``C`` is the old terminal set and ``x`` is an interior state, the child
    terminal set is ``C ∪ {x}``.  The fundamental matrix update is the Schur
    complement deletion identity

    ``N' = N_JJ - N_Jx N_xJ / N_xx``.

    The first-hit kernel update is

    ``H'(i, x) = N(i, x) / N(x, x)`` and
    ``H'(i, c) = H(i, c) - H'(i, x) H(x, c)`` for old terminals ``c``.
    """

    x = int(inserted_state)
    terminal_set = set(int(term) for term in state.terminals.tolist())
    if x in terminal_set:
        return state
    interior_positions = {int(s): pos for pos, s in enumerate(state.interior.tolist())}
    if x not in interior_positions:
        raise ValueError(f"inserted_state {x} is neither terminal nor interior.")
    x_pos = interior_positions[x]
    n_xx = float(state.fundamental[x_pos, x_pos])
    if abs(n_xx) <= min_pivot:
        raise np.linalg.LinAlgError(f"Boundary insertion pivot too small: {n_xx}")
    keep_positions = [pos for pos in range(len(state.interior)) if pos != x_pos]
    child_interior = state.interior[np.array(keep_positions, dtype=int)]
    n_jj = state.fundamental[np.ix_(keep_positions, keep_positions)]
    n_jx = state.fundamental[np.ix_(keep_positions, [x_pos])]
    n_xj = state.fundamental[np.ix_([x_pos], keep_positions)]
    child_fundamental = n_jj - (n_jx @ n_xj) / n_xx

    old_terminals = [int(term) for term in state.terminals.tolist()]
    child_terminals = sorted(terminal_set.union({x}))
    child_hit = np.zeros((len(child_interior), len(child_terminals)), dtype=float)
    p_hit_x = state.fundamental[keep_positions, x_pos] / n_xx
    h_x_old = state.hit_probability[x_pos]
    old_col = {term: pos for pos, term in enumerate(old_terminals)}
    child_col = {term: pos for pos, term in enumerate(child_terminals)}
    for term in old_terminals:
        child_hit[:, child_col[term]] = (
            state.hit_probability[keep_positions, old_col[term]]
            - p_hit_x * h_x_old[old_col[term]]
        )
    child_hit[:, child_col[x]] = p_hit_x
    return FirstHitGreenState(
        terminals=np.array(child_terminals, dtype=int),
        interior=child_interior,
        fundamental=child_fundamental,
        hit_probability=child_hit,
    )


def first_hit_reduce_truncated(
    P: np.ndarray,
    r: np.ndarray,
    start_state: State,
    terminals: Sequence[State],
    gamma: float,
    k_steps: int,
    tail_tol: float = 0.0,
) -> FirstHitReduction:
    """Truncated first-hit Green kernel from one start state.

    The prefix includes powers ``P_II^0`` through ``P_II^K``. Thus
    ``k_steps=0`` accounts for terminal hits after one primitive transition.
    Remaining non-terminal tail mass is deliberately dropped, making this a
    controlled approximation rather than an exact model.
    """

    n = P.shape[0]
    T = np.array(sorted(set(terminals)), dtype=int)
    if start_state in set(T.tolist()):
        raise ValueError("start_state must not be in terminals.")
    if len(T) == 0:
        return FirstHitReduction(
            terminals=T,
            gamma_terminal=np.zeros(0, dtype=float),
            reward=0.0,
            hit_probability=np.zeros(0, dtype=float),
            expected_tau=np.zeros(0, dtype=float),
        )

    terminal_set = set(T.tolist())
    I = np.array([s for s in range(n) if s not in terminal_set], dtype=int)
    start_pos = int(np.flatnonzero(I == start_state)[0])
    P_II = P[np.ix_(I, I)]
    P_IT = P[np.ix_(I, T)]
    r_I = r[I]

    current = np.zeros(len(I), dtype=float)
    current[start_pos] = 1.0
    gamma_terminal = np.zeros(len(T), dtype=float)
    hit_probability = np.zeros(len(T), dtype=float)
    tau_numerator = np.zeros(len(T), dtype=float)
    reward = 0.0
    discount = 1.0
    used_steps = max(0, int(k_steps))
    tail_mass = float(np.sum(current))
    tail_bound = float("inf")
    q_bound = substochastic_q_bound(P_II)
    for t in range(max(0, int(k_steps)) + 1):
        reward += discount * float(current @ r_I)
        terminal_flow = current @ P_IT
        hit_probability += terminal_flow
        gamma_terminal += discount * gamma * terminal_flow
        tau_numerator += float(t + 1) * terminal_flow
        current = current @ P_II
        used_steps = t
        tail_mass = float(np.sum(np.abs(current)))
        hit_tail_bound = tail_mass
        reward_tail_bound = (discount * gamma) * tail_mass / max(1e-12, 1.0 - gamma)
        q_tail_bound = geometric_tail_bound(q_bound, t + 1)
        tail_bound = min(max(hit_tail_bound, reward_tail_bound), q_tail_bound)
        if tail_tol > 0.0 and tail_bound <= tail_tol:
            break
        discount *= gamma

    expected_tau = np.divide(
        tau_numerator,
        hit_probability,
        out=np.full_like(tau_numerator, np.nan),
        where=hit_probability > 1e-12,
    )
    return FirstHitReduction(
        terminals=T,
        gamma_terminal=gamma_terminal,
        reward=float(reward),
        hit_probability=hit_probability,
        expected_tau=expected_tau,
        used_steps=used_steps,
        tail_mass=tail_mass,
        tail_bound=tail_bound,
        q_bound=q_bound,
    )


def first_hit_interior_occupancy(
    P: np.ndarray,
    start_state: State,
    terminals: Sequence[State],
    gamma: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return I and discounted occupancy over non-terminal states after leaving start."""

    n = P.shape[0]
    terminal_set = set(terminals)
    if start_state in terminal_set:
        raise ValueError("start_state must not be in terminals.")
    I = np.array([s for s in range(n) if s not in terminal_set], dtype=int)
    if len(I) == 0:
        return I, np.zeros(0, dtype=float)
    P_sI = P[np.ix_([start_state], I)]
    P_II = P[np.ix_(I, I)]
    occupancy = gamma * P_sI @ _solve_or_pinv(np.eye(len(I)) - gamma * P_II, np.eye(len(I)))
    return I, occupancy[0]


def first_hit_interior_occupancy_truncated(
    P: np.ndarray,
    start_state: State,
    terminals: Sequence[State],
    gamma: float,
    k_steps: int,
    tail_tol: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Truncated discounted occupancy over non-terminal states after leaving start."""

    n = P.shape[0]
    terminal_set = set(terminals)
    if start_state in terminal_set:
        raise ValueError("start_state must not be in terminals.")
    I = np.array([s for s in range(n) if s not in terminal_set], dtype=int)
    if len(I) == 0:
        return I, np.zeros(0, dtype=float)
    P_sI = P[np.ix_([start_state], I)]
    P_II = P[np.ix_(I, I)]
    current = gamma * P_sI[0]
    occupancy = np.zeros(len(I), dtype=float)
    discount = 1.0
    for _ in range(max(0, int(k_steps)) + 1):
        occupancy += discount * current
        current = current @ P_II
        if tail_tol > 0.0 and float(np.sum(current)) <= tail_tol:
            break
        discount *= gamma
    return I, occupancy


def first_hit_expected_interior_cost(
    P: np.ndarray,
    start_state: State,
    terminals: Sequence[State],
    gamma: float,
    state_cost: np.ndarray,
) -> float:
    """Expected discounted interior cost before first terminal hit from one start."""

    interior, occupancy = first_hit_interior_occupancy(P, start_state, terminals, gamma)
    if len(interior) == 0:
        return 0.0
    return float(occupancy @ state_cost[interior])


def expected_discounted_interior_cost(
    P: np.ndarray,
    boundary: Sequence[State],
    gamma: float,
    state_cost: np.ndarray,
) -> np.ndarray:
    """Expected discounted cost accumulated before hitting the next boundary.

    This is the same Schur-complement solve as the reduced reward, but without a
    boundary immediate cost term. It is useful for charging options that bypass
    hidden critical states not retained in the compact graph.
    """

    n = P.shape[0]
    B = np.array(sorted(boundary), dtype=int)
    B_set = set(B.tolist())
    I = np.array([s for s in range(n) if s not in B_set], dtype=int)
    if len(I) == 0:
        return np.zeros(len(B), dtype=float)
    _, _, occupancy = discounted_interior_occupancy(P, boundary, gamma)
    return occupancy @ state_cost[I]


def bellman_preservation_error(
    P: np.ndarray,
    r: np.ndarray,
    reduction: BellmanKronReduction,
    boundary_values: np.ndarray,
) -> float:
    """Compare reduced Bellman backup against the full system with fixed boundary values."""

    B = reduction.boundary
    I = reduction.interior
    gamma = reduction.gamma
    if len(I) == 0:
        full_q = r[B] + gamma * P[np.ix_(B, B)] @ boundary_values
    else:
        P_BB = P[np.ix_(B, B)]
        P_BI = P[np.ix_(B, I)]
        P_IB = P[np.ix_(I, B)]
        P_II = P[np.ix_(I, I)]
        r_I = r[I]
        V_I = _solve_or_pinv(
            np.eye(len(I)) - gamma * P_II,
            r_I + gamma * P_IB @ boundary_values,
        )
        full_q = r[B] + gamma * P_BB @ boundary_values + gamma * P_BI @ V_I
    reduced_q = reduction.reward + reduction.gamma_terminal @ boundary_values
    return float(np.max(np.abs(full_q - reduced_q)))


def smdp_value_iteration(
    reductions: Mapping[Action, BellmanKronReduction],
    goal_boundary_position: int,
    valid_actions: Mapping[Action, np.ndarray] | None = None,
    iterations: int = 10_000,
    tol: float = 1e-10,
) -> Tuple[np.ndarray, Dict[int, Action]]:
    """Solve max_o R_o + Gamma_o V on the boundary graph."""

    first = next(iter(reductions.values()))
    nB = len(first.boundary)
    V = np.zeros(nB, dtype=float)
    policy: Dict[int, Action] = {}
    for _ in range(iterations):
        old = V.copy()
        q_by_action = {}
        for action, red in reductions.items():
            q = red.reward + red.gamma_terminal @ old
            if valid_actions is not None and action in valid_actions:
                valid = np.asarray(valid_actions[action], dtype=bool)
                if valid.shape != (nB,):
                    raise ValueError(f"valid_actions[{action!r}] must have shape {(nB,)}.")
                q = q.copy()
                q[~valid] = -np.inf
            q_by_action[action] = q
        stacked = np.stack([q_by_action[a] for a in reductions], axis=0)
        best_values = stacked.max(axis=0)
        non_goal = np.ones(nB, dtype=bool)
        non_goal[goal_boundary_position] = False
        if np.any(~np.isfinite(best_values[non_goal])):
            bad = np.flatnonzero(non_goal & ~np.isfinite(best_values)).tolist()
            raise ValueError(f"No valid SMDP option available at boundary positions {bad}.")
        V = stacked.max(axis=0)
        best = stacked.argmax(axis=0)
        action_names = list(reductions.keys())
        policy = {i: action_names[int(best[i])] for i in range(nB)}
        V[goal_boundary_position] = 0.0
        policy[goal_boundary_position] = "TERMINAL"
        if np.max(np.abs(V - old)) < tol:
            break
    return V, policy


def primitive_value_iteration(
    grid: GridWorld,
    goal_state: State,
    gamma: float,
    slip: float = 0.0,
    iterations: int = 10_000,
    tol: float = 1e-10,
) -> np.ndarray:
    V = np.zeros(grid.n_states, dtype=float)
    for _ in range(iterations):
        old = V.copy()
        for s in range(grid.n_states):
            if s == goal_state:
                V[s] = 0.0
                continue
            qs = []
            for action in ACTIONS:
                dist = action_distribution(action, slip=slip)
                q = grid.step_reward
                q += gamma * sum(p * old[grid.next_state(s, a)] for a, p in dist.items())
                qs.append(q)
            V[s] = max(qs)
        if np.max(np.abs(V - old)) < tol:
            break
    return V


def edge_table(
    reductions: Mapping[Action, BellmanKronReduction],
    grid: GridWorld,
    min_hit_probability: float = 1e-8,
) -> List[Dict[str, object]]:
    _, idx_to_coord = grid.index_maps()
    rows: List[Dict[str, object]] = []
    for action, red in reductions.items():
        for i, src in enumerate(red.boundary):
            for j, dst in enumerate(red.boundary):
                prob = red.hit_probability[i, j]
                if prob <= min_hit_probability:
                    continue
                rows.append(
                    {
                        "src_state": int(src),
                        "dst_state": int(dst),
                        "src": idx_to_coord[int(src)],
                        "dst": idx_to_coord[int(dst)],
                        "option": action,
                        "hit_probability": float(prob),
                        "gamma_terminal": float(red.gamma_terminal[i, j]),
                        "expected_tau": float(red.expected_tau[i, j]),
                        "reward": float(red.reward[i]),
                    }
                )
    return rows


def boundary_signature(reductions: Mapping[Action, BellmanKronReduction]) -> np.ndarray:
    parts = []
    for red in reductions.values():
        parts.append(red.reward[:, None])
        parts.append(red.gamma_terminal)
        parts.append(np.nan_to_num(red.expected_tau, nan=0.0))
    return np.concatenate(parts, axis=1)


def merge_by_signature(signatures: np.ndarray, threshold: float) -> List[List[int]]:
    parent = list(range(len(signatures)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(signatures)):
        for j in range(i + 1, len(signatures)):
            if np.linalg.norm(signatures[i] - signatures[j]) <= threshold:
                union(i, j)
    groups: Dict[int, List[int]] = {}
    for i in range(len(signatures)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())
