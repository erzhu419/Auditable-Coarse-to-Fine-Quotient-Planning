"""Policy-conditioned joint consequences, with one observed mechanism feature."""
from collections import Counter
from copy import deepcopy
from time import perf_counter
import numpy as np
from .controlled_predictive_lifelong_v77 import (
    FEATURE_NAMES as BASE_FEATURE_NAMES, POLICIES, features, _fit, _predict)

MODES = ('MIXED', 'CONTEXT')
FEATURE_NAMES = BASE_FEATURE_NAMES + ('context_p4',)
TREE_PARAMETERS = dict(max_depth=8, min_samples_leaf=16, random_state=7701)


def _array(records, mode, counts, context_p4=None):
    """Fit uses each retained causal context; prediction binds the supplied context."""
    rows = []
    for row in records:
        context = .5 if mode == 'MIXED' else row['context_p4'] if context_p4 is None else context_p4
        rows.append(features(row['board'], row['horizon']) + (float(context),))
    counts['feature_rows'] += len(rows)
    counts['context_feature_rows' if mode == 'CONTEXT' else 'constant_context_feature_rows'] += len(rows)
    return np.asarray(rows, dtype=np.float32).reshape((-1, len(FEATURE_NAMES)))


class ConsequenceKnowledge:
    """One multi-output tree per fixed policy; each leaf stores a joint R/F/S mean."""
    def __init__(self, mode, trees, context_p4, counts=None):
        if mode not in MODES:
            raise ValueError(f'unknown consequence context mode {mode}')
        self.mode, self.trees, self.context_p4 = mode, trees, float(context_p4)
        self.counts = Counter(counts or {})

    @classmethod
    def fit(cls, records, mode, context_p4):
        """Use all supplied completed-game records under the same fixed tree recipe."""
        if mode not in MODES:
            raise ValueError(f'unknown consequence context mode {mode}')
        start = perf_counter()
        records = list(records)
        if any(row['policy'] not in POLICIES for row in records):
            raise ValueError('consequence records require an actually executed fixed policy')
        counts = Counter(metadata_rows_read=len(records))
        trees, policies = {}, {}
        for policy in POLICIES:
            selected = [row for row in records if row['policy'] == policy]
            if not selected:
                raise ValueError(f'completed training prefix has no records for {policy}')
            counts['training_rows_read'] += len(selected)
            x = _array(selected, mode, counts)
            y = np.asarray([row['target'] for row in selected], dtype=float)
            if y.shape != (len(selected), 3):
                raise ValueError('consequences must jointly contain reward, failure and success')
            tree = trees[policy] = _fit(x, y, counts)
            policies[policy] = dict(training_rows=len(selected), nodes=len(tree['left']),
                leaves=sum(node < 0 for node in tree['left']), target_mean=y.mean(axis=0).tolist())
        roster = [{key: row[key] for key in ('episode', 'policy', 'anchor_step', 'horizon')}
            for row in records]
        model = cls(mode, trees, context_p4)
        return model, dict(mode=mode, context_p4=float(context_p4), feature_names=list(FEATURE_NAMES),
            feature_dim=len(FEATURE_NAMES), tree_parameters=TREE_PARAMETERS.copy(),
            training_records=len(records), training_roster=roster, policies=policies,
            counts=dict(counts), seconds=perf_counter() - start)

    def predict_many(self, boards, horizon):
        """V77 planning interface: N boards by three policies by joint R/F/S."""
        boards = list(boards)
        self.counts['predict_many_calls'] += 1
        self.counts['prediction_boards'] += len(boards)
        self.counts['policy_prediction_rows'] += len(boards) * len(POLICIES)
        rows = [dict(board=board, horizon=horizon) for board in boards]
        x = _array(rows, self.mode, self.counts, context_p4=self.context_p4)
        return np.stack([_predict(self.trees[policy], x, self.counts) for policy in POLICIES], axis=1)

    def predict_records(self, records, context_p4):
        """Predict each recorded policy/horizon at a fixed evaluation context."""
        records = list(records)
        if any(row['policy'] not in POLICIES for row in records):
            raise ValueError('prediction records require a supported fixed policy')
        self.counts['predict_records_calls'] += 1
        self.counts['record_prediction_rows'] += len(records)
        self.counts['policy_prediction_rows'] += len(records)
        x = _array(records, self.mode, self.counts, context_p4=context_p4)
        result = np.empty((len(records), 3), dtype=float)
        for policy in POLICIES:
            positions = [i for i, row in enumerate(records) if row['policy'] == policy]
            if positions:
                result[positions] = _predict(self.trees[policy], x[positions], self.counts)
        return result

    def to_payload(self):
        return dict(schema='acfqp.context_consequences.v116', mode=self.mode, context_p4=self.context_p4,
            policies=list(POLICIES), feature_names=list(FEATURE_NAMES), tree_parameters=TREE_PARAMETERS.copy(),
            trees=deepcopy(self.trees), counts=dict(self.counts))

    @classmethod
    def from_payload(cls, payload):
        if (payload['schema'] != 'acfqp.context_consequences.v116'
                or payload['policies'] != list(POLICIES) or payload['feature_names'] != list(FEATURE_NAMES)
                or payload['tree_parameters'] != TREE_PARAMETERS):
            raise ValueError('retained consequence model has a different fixed representation or tree recipe')
        return cls(payload['mode'], deepcopy(payload['trees']), payload['context_p4'], payload['counts'])
