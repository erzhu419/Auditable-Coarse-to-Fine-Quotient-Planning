"""Compile finite observation support into an exact-membership decision DAG.

Every accepted path checks all 16 board ranks, in cell order. Identical suffix
subtrees share nodes, but equal labels never permit untested ranks to pass.
This is compilation of an existing finite mapping, not inference outside it.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class Encoder:
    # A decision node is (cell index, {observed rank: child node}); a leaf is
    # (16, contract cell). No concrete boards remain in the compiled object.
    nodes: tuple
    roots: dict
    counts: dict
    elapsed_seconds: float

    def encode(self, board, h, work=None):
        if work is not None:
            work['observations'] += 1
            work['horizon_tests'] += 1
        node = self.roots.get(h)
        if node is None or len(board) != 16:
            if work is not None:
                work['unsupported_observations'] += 1
            return None
        while True:
            position, data = self.nodes[node]
            if work is not None:
                work['node_visits'] += 1
            if position == 16:
                if work is not None:
                    work['supported_observations'] += 1
                return data
            if work is not None:
                work['rank_tests'] += 1
            node = data.get(board[position])
            if node is None:
                if work is not None:
                    work['unsupported_observations'] += 1
                return None
            if work is not None:
                work['edge_matches'] += 1

    def to_payload(self):
        return dict(roots=[[h, node] for h, node in sorted(self.roots.items())],
                    nodes=[[position, data if position == 16 else
                            [[rank, child] for rank, child in sorted(data.items())]]
                           for position, data in self.nodes])

    @classmethod
    def from_payload(cls, payload):
        started = perf_counter()
        nodes = tuple((position, data if position == 16 else dict(data))
                      for position, data in payload['nodes'])
        roots = dict(payload['roots'])
        counts = _size_counts(nodes, roots)
        counts['loaded_nodes'] = len(nodes)
        counts['loaded_edges'] = counts['dag_edges']
        return cls(nodes, roots, counts, perf_counter() - started)


def _size_counts(nodes, roots):
    return dict(dag_nodes=len(nodes), horizon_roots=len(roots),
                dag_leaves=sum(position == 16 for position, _ in nodes),
                dag_decisions=sum(position != 16 for position, _ in nodes),
                dag_edges=sum(len(data) for position, data in nodes if position != 16))


def compile_encoder(labels):
    """Compile (horizon, 16-rank board, contract cell) records exactly.

    Each temporary trie prefix is visited once. Bottom-up structural interning
    shares identical suffixes; no test is removed, even with one child or a
    constant label. Conflicting labels for the same observation are an error.
    """
    started = perf_counter()
    work, groups = Counter(), defaultdict(list)
    for horizon, board, cell in labels:
        concrete = tuple(board)
        if len(concrete) != 16:
            raise ValueError('V70 observation labels require exactly 16 ranks')
        groups[horizon].append((concrete, cell))
        work['input_labels'] += 1
        work['input_rank_slots'] += 16
    nodes, interned = [], {}

    def intern(key, data):
        if key in interned:
            work['shared_subtree_visits'] += 1
            return interned[key]
        node = len(nodes)
        interned[key] = node
        nodes.append((key[0], data))
        return node

    def visit(records, position):
        work['trie_prefix_visits'] += 1
        if position == 16:
            choices = {cell for _, cell in records}
            work['leaf_label_checks'] += len(records)
            if len(choices) != 1:
                raise ValueError('one observation has conflicting contract labels')
            cell = next(iter(choices))
            work['distinct_observations'] += 1
            work['duplicate_observations'] += len(records) - 1
            return intern((16, cell), cell)
        partition = defaultdict(list)
        for board, cell in records:
            partition[board[position]].append((board, cell))
            work['compile_rank_reads'] += 1
        children = tuple((rank, visit(rows, position + 1))
                         for rank, rows in sorted(partition.items()))
        work['trie_edges_visited'] += len(children)
        return intern((position, children), dict(children))

    roots = {horizon: visit(records, 0) for horizon, records in sorted(groups.items())}
    counts = dict(work)
    counts.update(_size_counts(nodes, roots))
    return Encoder(tuple(nodes), roots, counts, perf_counter() - started)
