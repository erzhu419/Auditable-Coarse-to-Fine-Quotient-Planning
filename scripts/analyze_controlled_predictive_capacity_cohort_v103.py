"""Posthoc, zero-sampling comparison restricted to retained V103 reference roots."""
import argparse
import json
from math import fsum
from pathlib import Path


def analyze(directory):
    run = json.loads((directory / 'run.json').read_text())
    analysis = json.loads((directory / 'analysis.json').read_text())
    rows = []
    for replicas in (8, 4):
        for family in ('MEAN_SIGN', 'REPLICA', 'UNIFORM_SHRINK'):
            left, right = (f'R{replicas}_H{width}_{family}_DIRECT' for width in (4, 16))
            for query in run['settings']['queries']:
                histories = []
                for life in run['lifecycles']:
                    stage = life['evaluation']
                    indexed = {name: {game['replica']: game for game in stage['methods'][name]['games']
                        if game['query'] == query} for name in (left, right)}
                    retained = [row['root'] for row in stage['validation']['roots'] if row['root']['query'] == query]
                    deltas = [indexed[left][root['episode']]['utility'] - indexed[right][root['episode']]['utility']
                        for root in retained]
                    histories.append(dict(life=life['id'], episodes=[root['episode'] for root in retained],
                        natural_utility_delta=fsum(deltas) / len(deltas)))
                independent = {}
                for block in ('pool', 'A', 'B'):
                    methods = (analysis['validation']['methods'] if block == 'pool' else
                        analysis['validation']['independent_blocks'][block]['methods'])
                    independent[block] = (methods[left][query]['primary']['selected_reference_utility'] -
                        methods[right][query]['primary']['selected_reference_utility'])
                rows.append(dict(replicas=replicas, family=family, query=query, left=left, right=right,
                    reference_cohort_natural_utility_delta=fsum(row['natural_utility_delta'] for row in histories) / len(histories),
                    all_natural_utility_delta=analysis['natural']['comparisons'][left + '_minus_' + right][query]['mean_utility_delta'],
                    independent_reference_utility_delta=independent, histories=histories))
    return dict(scope='Posthoc descriptive comparison of frozen full-model choices on exactly the existing reference roots. '
        'Natural utility uses its original single suffix; independent values use the retained pool32/A/B16. '
        'No new sampling, fitting or predictions; primary analysis remains unchanged.',
        new_environment_transitions=0, new_model_transitions=0, new_model_fits=0, new_candidate_predictions=0,
        comparisons=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = analyze(args.directory)
    with (args.directory / 'matched_cohort_descriptive.json').open('x') as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write('\n')
    print(json.dumps(dict(comparisons=len(result['comparisons']), new_environment_transitions=0,
        new_model_transitions=0, new_model_fits=0, new_candidate_predictions=0)))
