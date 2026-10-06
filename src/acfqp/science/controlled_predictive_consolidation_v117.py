"""Shared or mechanism-local joint policy consequences under one leaf budget."""
from collections import Counter
from copy import deepcopy
from time import perf_counter
import numpy as np
from .controlled_predictive_lifelong_v77 import FEATURE_NAMES, POLICIES, features, _predict

MODES = ('SHARED', 'SPLIT')
LEAF_BUDGET, NODE_BUDGET = 256, 511
TREE_PARAMETERS = dict(max_depth=8, min_samples_leaf=16, random_state=7701)


def _key(mode, module_id):
    return 'shared' if mode == 'SHARED' else str(module_id)


def _array(records, counts):
    counts['feature_rows'] += len(records)
    return np.asarray([features(row['board'], row['horizon']) for row in records],
        dtype=np.float32).reshape((-1, len(FEATURE_NAMES)))


def _fit_group(records, allowance, counts):
    y = np.asarray([row['target'] for row in records], dtype=float)
    if y.shape != (len(records), 3):
        raise ValueError('joint consequence targets require reward, failure and success')
    counts['fit_rows'] += len(records)
    if allowance == 1:
        counts['constant_leaf_models'] += 1
        return dict(left=[-1], right=[-1], feature=[-2], threshold=[-2.],
            values=[y.mean(axis=0).tolist()], samples=[len(records)])
    from sklearn.tree import DecisionTreeRegressor
    x = _array(records, counts)
    tree = DecisionTreeRegressor(**TREE_PARAMETERS, max_leaf_nodes=allowance).fit(x, y).tree_
    counts['tree_fits'] += 1
    return dict(left=tree.children_left.tolist(), right=tree.children_right.tolist(),
        feature=tree.feature.tolist(), threshold=tree.threshold.tolist(),
        values=tree.value[:, :, 0].tolist(), samples=tree.n_node_samples.tolist())


class BankKnowledge:
    def __init__(self, mode, trees, module_id, counts=None):
        if mode not in MODES:
            raise ValueError(f'unknown consequence bank mode {mode}')
        self.mode, self.trees, self.module_id = mode, trees, module_id
        self.counts = Counter(counts or {})

    @classmethod
    def fit(cls, records, mode, module_id):
        """Fit only supplied source labels, preserving the saved causal module IDs."""
        if mode not in MODES:
            raise ValueError(f'unknown consequence bank mode {mode}')
        started = perf_counter()
        records = list(records)
        if any(row['policy'] not in POLICIES for row in records):
            raise ValueError('source records require one of the three executed policies')
        grouped = {}
        for policy in POLICIES:
            selected = [row for row in records if row['policy'] == policy]
            if not selected:
                raise ValueError(f'no completed source records for policy {policy}')
            modules = sorted({row['context_module_id'] for row in selected}) if mode == 'SPLIT' else [None]
            if len(modules) > LEAF_BUDGET:
                raise ValueError(f'leaf budget unavailable for {len(modules)} groups of {policy}')
            grouped[policy] = [(module, [row for row in selected if mode == 'SHARED'
                or row['context_module_id'] == module]) for module in modules]
        counts = Counter(metadata_rows_read=len(records), training_rows_read=len(records),
            tree_fits=0, constant_leaf_models=0, fit_rows=0, feature_rows=0)
        trees, allocations, totals = {}, {}, {}
        for policy in POLICIES:
            groups = grouped[policy]
            quotient, remainder = divmod(LEAF_BUDGET, len(groups))
            trees[policy], allocations[policy] = {}, []
            for position, (module, selected) in enumerate(groups):
                allowance = quotient + int(position < remainder)
                tree = _fit_group(selected, allowance, counts)
                trees[policy][_key(mode, module)] = tree
                allocations[policy].append(dict(module_id=module, training_rows=len(selected),
                    leaf_allowance=allowance, actual_leaves=sum(child < 0 for child in tree['left']),
                    actual_nodes=len(tree['left']), constant_leaf=allowance == 1))
            totals[policy] = dict(leaf_budget=LEAF_BUDGET, node_budget=NODE_BUDGET,
                allocated_leaves=sum(row['leaf_allowance'] for row in allocations[policy]),
                actual_leaves=sum(row['actual_leaves'] for row in allocations[policy]),
                actual_nodes=sum(row['actual_nodes'] for row in allocations[policy]),
                groups=len(groups), training_rows=sum(row['training_rows'] for row in allocations[policy]))
        roster = [{key: row[key] for key in ('episode', 'policy', 'anchor_step', 'horizon', 'context_module_id')}
            for row in records]
        return cls(mode, trees, module_id), dict(mode=mode, module_id=module_id,
            feature_names=list(FEATURE_NAMES), feature_dim=len(FEATURE_NAMES), tree_parameters=TREE_PARAMETERS.copy(),
            per_policy_leaf_budget=LEAF_BUDGET, per_policy_node_budget=NODE_BUDGET,
            training_records=len(records), training_roster=roster, group_allocations=allocations,
            policy_totals=totals, counts=dict(counts), seconds=perf_counter() - started)

    def can_route(self, module_id):
        key = _key(self.mode, module_id)
        return all(key in self.trees[policy] for policy in POLICIES)

    def predict_many(self, boards, horizon):
        """Return N x policy x joint R/F/S, or None for an unavailable planning branch."""
        boards = list(boards)
        self.counts['predict_many_calls'] += 1
        self.counts['prediction_boards'] += len(boards)
        if not self.can_route(self.module_id):
            self.counts['unavailable_planning_boards'] += len(boards)
            return None
        self.counts['policy_prediction_rows'] += len(boards) * len(POLICIES)
        x = _array([dict(board=board, horizon=horizon) for board in boards], self.counts)
        key = _key(self.mode, self.module_id)
        return np.stack([_predict(self.trees[policy][key], x, self.counts) for policy in POLICIES], axis=1)

    def predict_records(self, records):
        """Route each held-out record by its saved observed module, without fitting."""
        records = list(records)
        if any(row['policy'] not in POLICIES for row in records):
            raise ValueError('prediction records require an executed supported policy')
        self.counts['predict_records_calls'] += 1
        self.counts['prediction_record_requests'] += len(records)
        self.counts['record_route_lookups'] += len(records)
        result, groups = [None] * len(records), {}
        for index, row in enumerate(records):
            key = _key(self.mode, row['context_module_id'])
            if key not in self.trees[row['policy']]:
                self.counts['unavailable_record_rows'] += 1
            else:
                groups.setdefault((row['policy'], key), []).append(index)
        for (policy, key), positions in groups.items():
            x = _array([records[index] for index in positions], self.counts)
            predicted = _predict(self.trees[policy][key], x, self.counts)
            self.counts['predicted_record_rows'] += len(positions)
            self.counts['policy_prediction_rows'] += len(positions)
            for index, values in zip(positions, predicted):
                result[index] = values.tolist()
        return result

    def to_payload(self):
        return dict(schema='acfqp.consolidation.v117', mode=self.mode, module_id=self.module_id,
            policies=list(POLICIES), feature_names=list(FEATURE_NAMES), tree_parameters=TREE_PARAMETERS.copy(),
            per_policy_leaf_budget=LEAF_BUDGET, per_policy_node_budget=NODE_BUDGET,
            trees=deepcopy(self.trees), counts=dict(self.counts))

    @classmethod
    def from_payload(cls, payload):
        if (payload['schema'] != 'acfqp.consolidation.v117' or payload['policies'] != list(POLICIES)
                or payload['feature_names'] != list(FEATURE_NAMES) or payload['tree_parameters'] != TREE_PARAMETERS
                or payload['per_policy_leaf_budget'] != LEAF_BUDGET or payload['per_policy_node_budget'] != NODE_BUDGET):
            raise ValueError('retained bank differs from the frozen representation or tree budget')
        return cls(payload['mode'], deepcopy(payload['trees']), payload['module_id'], payload['counts'])
