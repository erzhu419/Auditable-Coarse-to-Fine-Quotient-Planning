"""Support and training-span diagnostics for signed paired n-tuple features.

Zero-initialized LMS weights remain in the span of their training differences.
Projection measures which part of a new difference can affect those weights;
it does not attribute a fraction of utility error to feature coverage.
"""
from collections import Counter

import numpy as np


RANK_RELATIVE_TOLERANCE = 1e-10
PROJECTION_RELATIVE_TOLERANCE = 1e-8


def _sparse_dot(left, right):
    if len(left) > len(right):
        left, right = right, left
    return sum(value*right.get(address, 0) for address, value in left.items())


class TrainingGeometry:
    def __init__(self, training_differences):
        self.training = [{address: int(value) for address, value in row.items() if value}
                         for row in training_differences]
        self.addresses = set().union(*(row.keys() for row in self.training))
        self.norms2 = [_sparse_dot(row, row) for row in self.training]
        n = len(self.training)
        self.counts = Counter(gram_dot_products=0, eigendecompositions=0,
                              query_measures=0, query_dot_products=0)
        gram = np.zeros((n, n), dtype=np.float64)
        for i, left in enumerate(self.training):
            for j in range(i+1):
                gram[i, j] = gram[j, i] = _sparse_dot(left, self.training[j])
                self.counts['gram_dot_products'] += 1
        if any(self.norms2):
            eigenvalues, eigenvectors = np.linalg.eigh(gram)
            self.counts['eigendecompositions'] += 1
            retained = eigenvalues > eigenvalues[-1]*RANK_RELATIVE_TOLERANCE
            self.eigenvalues = eigenvalues[retained]
            self.eigenvectors = eigenvectors[:, retained]
        else:
            self.eigenvalues = np.empty(0, dtype=np.float64)
            self.eigenvectors = np.empty((n, 0), dtype=np.float64)
        self.rank = len(self.eigenvalues)

    def measure(self, difference):
        difference = {address: int(value) for address, value in difference.items() if value}
        norm2 = _sparse_dot(difference, difference)
        covered = {address: value for address, value in difference.items()
                   if address in self.addresses}
        covered_norm2 = _sparse_dot(covered, covered)
        kernel = [_sparse_dot(row, difference) for row in self.training]
        self.counts.update(query_measures=1, query_dot_products=len(self.training))
        coordinates = self.eigenvectors.T @ np.asarray(kernel, dtype=np.float64)
        projection = float(np.sum(coordinates*coordinates/self.eigenvalues))
        tolerance = PROJECTION_RELATIVE_TOLERANCE*max(1, norm2)
        if not np.isfinite(projection) or projection < -tolerance or projection > norm2+tolerance:
            raise ValueError('training-span projection is outside the squared-norm bounds')
        projection = min(float(norm2), max(0., projection))
        cosine = max((abs(dot)/np.sqrt(float(norm2)*row_norm2)
                      for dot, row_norm2 in zip(kernel, self.norms2)
                      if norm2 and row_norm2), default=0.)
        if cosine > 1.+PROJECTION_RELATIVE_TOLERANCE:
            raise ValueError('training cosine exceeds one')
        return dict(
            train_roots=len(self.training),
            nonzero_train_roots=sum(value != 0 for value in self.norms2),
            train_rank=self.rank, train_addresses=len(self.addresses),
            query_addresses=len(difference), query_norm2=norm2,
            covered_addresses=len(covered), covered_norm2=covered_norm2,
            covered_norm_fraction=covered_norm2/norm2 if norm2 else None,
            projection_norm2=projection,
            projection_fraction=projection/norm2 if norm2 else None,
            max_abs_cosine=float(min(1., cosine)), zero_feature=not bool(norm2),
            orthogonal_to_training=all(dot == 0 for dot in kernel))
