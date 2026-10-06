"""Compare top-layer rankings with retained noisy paired terminal differences."""
from collections import Counter, defaultdict
import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_policy_advantage_v81 import (
    Policy, QUERIES, action_features,
)
from acfqp.science.controlled_predictive_lifelong_v77 import _predict
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics


def utility(target, query):
    return (query['reward_weight'] * target[0] - query['failure_penalty'] * target[1]
            + query['goal_bonus'] * target[2])


def summarize(roots):
    def mean(key):
        return sum(root[key] for root in roots) / len(roots) if roots else None
    overrides = [root for root in roots if root['override']]
    return dict(roots=len(roots), overrides=len(overrides),
        predicted_selected_advantage_mean=mean('predicted_selected_advantage'),
        observed_selected_advantage_mean=mean('observed_selected_advantage'),
        best_retained_advantage_mean=mean('best_retained_advantage'),
        regret_to_best_retained_mean=mean('regret_to_best_retained'),
        override_observed_positive=sum(root['observed_selected_advantage'] > 0 for root in overrides),
        override_observed_negative=sum(root['observed_selected_advantage'] < 0 for root in overrides),
        override_observed_zero=sum(root['observed_selected_advantage'] == 0 for root in overrides))


def diagnose_rows(rows, policy, rule):
    """Use the recorded reference action, without executing the parent policy."""
    grouped = defaultdict(list)
    counts = Counter()
    for row in rows:
        grouped[row['query'], row['episode'], row['root_index']].append(row)
    records = []
    for (query_name, episode, index), alternatives in sorted(grouped.items()):
        alternatives.sort(key=lambda row: row['action'])
        first = alternatives[0]
        reference = first['reference_action']
        query = QUERIES[query_name]
        x = np.asarray([action_features(row['board'], row['action'], reference, rule, counts)
                        for row in alternatives], dtype=np.float32)
        predictions = _predict(policy.trees[query_name], x, counts)
        counts['advantage_prediction_rows'] += len(alternatives)
        selected, predicted, observed = reference, 0.0, 0.0
        best = 0.0
        for row, vector in zip(alternatives, predictions):
            estimated = float(utility(vector, query))
            retained = float(utility(row['target'], query))
            best = max(best, retained)
            if estimated > predicted:
                selected, predicted, observed = row['action'], estimated, retained
        records.append(dict(query=query_name, episode=episode, root_index=index,
            step=first['step'], split='heldout' if episode % 5 == 4 else 'training',
            reference_action=reference, selected_action=selected, override=selected != reference,
            alternatives=len(alternatives), predicted_selected_advantage=predicted,
            observed_selected_advantage=observed, best_retained_advantage=best,
            regret_to_best_retained=best - observed))
    return dict(queries={query: {split: summarize([root for root in records
        if root['query'] == query and root['split'] == split])
        for split in ('training', 'heldout')} for query in QUERIES},
        roots=records, counts=dict(counts))


def run(directory):
    campaign = json.loads((directory / 'run.json').read_text())
    if campaign['status'] != 'complete':
        raise ValueError('ranking diagnosis requires the completed V81 campaign')
    rule = LearnedDynamics.from_payload(json.loads((directory / 'supplied_dynamics.json').read_text()))
    results = []
    total_counts = Counter()
    for lifecycle in campaign['lifecycles']:
        for stage in lifecycle['rounds']:
            iteration = stage['iteration']
            folder = directory / f"life_{lifecycle['id']}/iteration_{iteration}"
            policy = Policy.from_payload(json.loads((folder / 'current_policy.json').read_text()))
            with gzip.open(folder / 'advantage_rows.jsonl.gz', 'rt') as handle:
                rows = [json.loads(line) for line in handle]
            result = diagnose_rows(rows, policy, rule)
            results.append(dict(lifecycle=lifecycle['id'], iteration=iteration, **result))
            total_counts.update(result['counts'])
    report = dict(schema='acfqp.retained_advantage_ranking.v81',
        interpretation='Read-only fit/holdout ranking diagnostic on the actual retained reference action. '
            'Observed advantages and the best retained action use only two paired replicas; they are noisy '
            'training observations, not new evaluations or true-value oracles. No acceptance gate.',
        scope='Only labeled roots with at least one alternative; censored and single-legal-action roots '
            'do not appear. No parent decisions, RNG draws, refits or environment transitions.',
        results=results, counts=dict(total_counts), ground_calls=0, tree_fits=0,
        pooled={str(iteration): {query: {split: summarize([root
            for result in results if result['iteration'] == iteration
            for root in result['roots'] if root['query'] == query and root['split'] == split])
            for split in ('training', 'heldout')} for query in QUERIES}
            for iteration in campaign['settings']['iterations']})
    output = directory / 'ranking_diagnostic.json'
    output.write_text(json.dumps(report, allow_nan=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    report = run(args.directory)
    print(json.dumps(report['pooled']))
