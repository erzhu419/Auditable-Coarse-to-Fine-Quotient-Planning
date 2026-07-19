#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import thread_limits  # noqa: F401
import numpy as np

from bellman_kron import (
    ACTIONS,
    GridWorld,
    bellman_kron_reduce,
    bellman_preservation_error,
    boundary_signature,
    decision_boundary_states,
    default_map,
    edge_table,
    merge_by_signature,
    primitive_value_iteration,
    smdp_value_iteration,
    transition_matrix_for_direction,
)


def draw_graph(grid: GridWorld, edges, boundary, out_path: Path) -> None:
    coord_to_idx, idx_to_coord = grid.index_maps()
    G = nx.MultiDiGraph()
    boundary_set = set(boundary)
    for s in boundary:
        r, c = idx_to_coord[int(s)]
        G.add_node(int(s), pos=(c, -r))
    for edge in edges:
        if edge["src_state"] == edge["dst_state"]:
            continue
        G.add_edge(edge["src_state"], edge["dst_state"], option=edge["option"], weight=edge["hit_probability"])

    pos = nx.get_node_attributes(G, "pos")
    fig, ax = plt.subplots(figsize=(12, 6))
    for r, row in enumerate(grid.rows):
        for c, ch in enumerate(row):
            if ch == "#":
                ax.add_patch(plt.Rectangle((c - 0.45, -r - 0.45), 0.9, 0.9, color="#222222"))
            elif coord_to_idx[(r, c)] not in boundary_set:
                ax.scatter(c, -r, s=16, color="#c7c7c7")
    node_colors = []
    for n in G.nodes:
        ch = grid.char_at(n)
        node_colors.append("#2ca02c" if ch == "S" else "#d62728" if ch == "G" else "#1f77b4")
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=90, node_color=node_colors)
    nx.draw_networkx_edges(G, pos, ax=ax, arrows=True, alpha=0.28, width=0.8, connectionstyle="arc3,rad=0.08")
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Bellman-Kron SMDP boundary graph")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a tabular Bellman-Kron SMDP fusion experiment.")
    parser.add_argument("--gamma", type=float, default=0.97)
    parser.add_argument("--slip", type=float, default=0.0)
    parser.add_argument("--signature-threshold", type=float, default=1e-6)
    parser.add_argument("--out-dir", type=Path, default=Path("experiments/output/gridworld_bellman_kron"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    grid = GridWorld(default_map())
    boundary = decision_boundary_states(grid)
    start = grid.symbol_states("S")[0]
    goal = grid.symbol_states("G")[0]
    boundary_to_pos = {s: i for i, s in enumerate(boundary)}

    reductions = {}
    preservation = {}
    rng = np.random.default_rng(7)
    boundary_values = rng.normal(size=len(boundary))
    for action in ACTIONS:
        P, r = transition_matrix_for_direction(grid, action, slip=args.slip)
        red = bellman_kron_reduce(P, r, boundary=boundary, gamma=args.gamma)
        reductions[action] = red
        preservation[action] = bellman_preservation_error(P, r, red, boundary_values)

    edges = edge_table(reductions, grid, min_hit_probability=1e-5)
    with (args.out_dir / "edges.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(edges[0].keys()))
        writer.writeheader()
        writer.writerows(edges)

    V_smdp, policy_smdp = smdp_value_iteration(reductions, boundary_to_pos[goal])
    V_full = primitive_value_iteration(grid, goal_state=goal, gamma=args.gamma, slip=args.slip)
    boundary_full = V_full[np.array(boundary)]
    value_gap = np.abs(V_smdp - boundary_full)

    signatures = boundary_signature(reductions)
    groups = merge_by_signature(signatures, threshold=args.signature_threshold)

    summary = {
        "gamma": args.gamma,
        "slip": args.slip,
        "n_states": grid.n_states,
        "n_boundary": len(boundary),
        "n_interior": grid.n_states - len(boundary),
        "compression_ratio": len(boundary) / grid.n_states,
        "n_edges": len(edges),
        "bellman_preservation_max_error_by_option": preservation,
        "smdp_vs_primitive_value_max_abs_gap_on_boundaries": float(value_gap.max()),
        "smdp_value_at_start_boundary_if_boundary": float(V_smdp[boundary_to_pos[start]]) if start in boundary_to_pos else None,
        "primitive_value_at_start": float(V_full[start]),
        "signature_merge_group_count": len(groups),
        "signature_merge_groups_boundary_positions": groups,
    }
    with (args.out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    boundary_rows = []
    _, idx_to_coord = grid.index_maps()
    for i, s in enumerate(boundary):
        boundary_rows.append(
            {
                "boundary_pos": i,
                "state": int(s),
                "coord": idx_to_coord[int(s)],
                "char": grid.char_at(int(s)),
                "smdp_value": float(V_smdp[i]),
                "primitive_value": float(boundary_full[i]),
                "abs_gap": float(value_gap[i]),
                "best_option": policy_smdp[i],
            }
        )
    with (args.out_dir / "boundary_values.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(boundary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(boundary_rows)

    draw_graph(grid, edges, boundary, args.out_dir / "boundary_graph.png")

    print(json.dumps(summary, indent=2))
    print(f"Wrote {args.out_dir}")


if __name__ == "__main__":
    main()
