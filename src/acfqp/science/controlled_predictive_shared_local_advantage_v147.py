"""Boundary-aware unary and adjacent-pair differences shared across positions."""
from collections import Counter
from copy import deepcopy
from time import perf_counter

import numpy as np

from .controlled_predictive_paired_advantage_v144 import PairedAdvantage


SCHEMA = 'acfqp.shared_local_advantage.v147'
FEATURE_DEFINITION = dict(
    radix=11, cell_class='number_of_boundary_coordinates',
    unary_address='cell_class*11+rank',
    pair_address='33+min(unary_i,unary_j)*33+max(unary_i,unary_j)',
    adjacency='horizontal_or_vertical_undirected',
    unary_occurrences=16, pair_occurrences=24)


class SharedLocalAdvantage(PairedAdvantage):
    def __init__(self, radix=11):
        started = perf_counter()
        if radix != 11:
            raise ValueError('V147 shared local features use radix 11')
        self.radix = 11
        self.cell_classes = tuple(int(row in (0, 3))+int(column in (0, 3))
                                  for row in range(4) for column in range(4))
        self.edges = tuple((4*row+column, 4*row+column+1)
                           for row in range(4) for column in range(3)) + tuple(
                               (4*row+column, 4*(row+1)+column)
                               for row in range(3) for column in range(4))
        self._weights = {}
        self.updates, self.frozen = 0, False
        self.counts = Counter()
        self.setup_counts = Counter(topology_integer_cells=64)
        self.setup_seconds = perf_counter()-started

    def _features(self, board):
        board = np.asarray(board, dtype=np.int32)
        if board.shape != (16,) or np.any(board < 0):
            raise ValueError('afterstates must have 16 nonnegative ranks')
        self.counts['feature_board_reads'] += 16
        if np.any(board >= self.radix):
            raise ValueError('V147 shared local features require nonterminal afterstates')
        features = Counter()
        for index, cell_class in enumerate(self.cell_classes):
            features[cell_class*11+int(board[index])] += 1
        for first, second in self.edges:
            left = self.cell_classes[first]*11+int(board[first])
            right = self.cell_classes[second]*11+int(board[second])
            features[33+min(left, right)*33+max(left, right)] += 1
        self.counts.update(feature_rank_reads=64, feature_occurrences=40,
                           unary_feature_occurrences=16, pair_feature_occurrences=24)
        return features

    def to_payload(self):
        payload = super().to_payload()
        payload.update(schema=SCHEMA, feature_definition=deepcopy(FEATURE_DEFINITION))
        return payload

    @classmethod
    def from_payload(cls, payload):
        if payload['schema'] != SCHEMA:
            raise ValueError('unsupported shared local advantage schema')
        model = cls(payload['radix'])
        model._weights = {int(row[0]): tuple(map(float, row[1:])) for row in payload['weights']}
        model.updates, model.frozen = int(payload['updates']), bool(payload['frozen'])
        model.setup_counts.update(loaded_weight_addresses=len(model._weights),
            loaded_weight_parameters=3*len(model._weights), loaded_numeric_weight_bytes=24*len(model._weights))
        return model
