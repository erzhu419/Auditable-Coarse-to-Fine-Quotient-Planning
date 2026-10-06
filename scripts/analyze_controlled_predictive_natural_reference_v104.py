"""Match frozen natural decisions with full-cohort independent suffix references."""
from collections import Counter
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_fragments_v83 import OPTIONS, QUERIES, _utility
from scripts.analyze_controlled_predictive_query_ranking_v100 import ranking_error
from scripts.analyze_controlled_predictive_capacity_ranking_v103 import CONTRASTS, CURRENT

METHODS = ('H2_ONLY', 'PREFIX_ONLY_DIRECT') + CURRENT + tuple(name + '_FROZEN_HALF' for name in CURRENT)
BLOCKS = ('pooled', 'A', 'B')
ZERO_COHORT_WORK = ('new_environment_transitions', 'new_synthetic_transitions', 'neural_model_fits',
                    'new_selector_calls', 'neural_candidate_predictions')
TERMINAL = ('WON', 'LOST')


def mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def reference_values(log, query, replicas):
    result = {}
    for name, start, stop in (('pooled', 0, replicas), ('A', 0, replicas // 2), ('B', replicas // 2, replicas)):
        result[name] = dict(H2=0., **{option: _utility([mean(row[index]
            for row in log['pair_deltas'][option][start:stop]) for index in range(3)], QUERIES[query])
            for option in OPTIONS[1:]})
    return result


def root_metrics(root, values):
    result = {}
    for block, utility in values.items():
        result[block] = {}
        for method, natural in root['natural'].items():
            if method == 'H2_ONLY':
                result[block][method] = dict(selected_reference_utility=0.,
                    selected_reference_regret=max(utility.values()), pairwise_weighted_error=None)
                continue
            event = root['predictions'][method]
            scores = {option: event['predictions'][option]['value'] for option in OPTIONS}
            result[block][method] = ranking_error(scores, utility, event['option'])
    return result


def method_history(rows, methods):
    paired = [row for row in rows if row['reference_complete']]
    result = {}
    for method in methods:
        result[method] = dict(
            natural_mean_score=mean(row['natural'][method]['score'] for row in rows),
            natural_mean_utility=mean(row['natural'][method]['utility'] for row in rows),
            natural_mean_h2_advantage=mean(row['natural'][method]['utility'] - row['natural']['H2_ONLY']['utility'] for row in rows),
            references={block: {field: mean(row['reference_metrics'][block][method][field] for row in paired)
                for field in ('selected_reference_utility', 'selected_reference_regret', 'pairwise_weighted_error')}
                for block in BLOCKS})
    return result


def contrast_history(rows, left, right):
    paired = [row for row in rows if row['reference_complete']]
    return dict(roots=len(rows), paired_reference_roots=len(paired),
        natural_mean_score_delta=mean(row['natural'][left]['score'] - row['natural'][right]['score'] for row in rows),
        natural_mean_utility_delta=mean(row['natural'][left]['utility'] - row['natural'][right]['utility'] for row in rows),
        available_paired_natural_mean_score_delta=mean(row['natural'][left]['score'] - row['natural'][right]['score'] for row in paired),
        available_paired_natural_mean_utility_delta=mean(row['natural'][left]['utility'] - row['natural'][right]['utility'] for row in paired),
        references={block: dict(
            selected_utility_delta=mean(row['reference_metrics'][block][left]['selected_reference_utility']
                - row['reference_metrics'][block][right]['selected_reference_utility'] for row in paired),
            pairwise_weighted_error_delta=mean(row['reference_metrics'][block][left]['pairwise_weighted_error']
                - row['reference_metrics'][block][right]['pairwise_weighted_error'] for row in paired
                if row['reference_metrics'][block][left]['pairwise_weighted_error'] is not None
                and row['reference_metrics'][block][right]['pairwise_weighted_error'] is not None)) for block in BLOCKS})


def contrast_across(histories):
    return dict(histories=len(histories),
        natural_mean_score_delta=mean(row['natural_mean_score_delta'] for row in histories),
        natural_mean_utility_delta=mean(row['natural_mean_utility_delta'] for row in histories),
        available_paired_natural_mean_score_delta=mean(row['available_paired_natural_mean_score_delta'] for row in histories),
        available_paired_natural_mean_utility_delta=mean(row['available_paired_natural_mean_utility_delta'] for row in histories),
        references={block: {field: mean(row['references'][block][field] for row in histories)
            for field in ('selected_utility_delta', 'pairwise_weighted_error_delta')} for block in BLOCKS})


def summarize_cohort(rows, settings, origin=None):
    methods, comparisons = {}, {}
    expected = settings['validation_roots_per_query'] if origin is None else 2 if origin == 'inherited' else settings['validation_roots_per_query'] - 2
    selected = [row for row in rows if origin is None or row['reference_origin'] == origin]
    for query in settings['queries']:
        by_life = {life: [row for row in selected if row['life'] == life and row['query'] == query]
            for life in settings['lifecycles']}
        method_lives = {life: method_history(group, settings['methods']) for life, group in by_life.items()}
        complete = all(len(group) == expected and all(row['reference_complete'] for row in group) for group in by_life.values())
        for method in settings['methods']:
            histories = [dict(id=life, roots=len(by_life[life]),
                paired_reference_roots=sum(row['reference_complete'] for row in by_life[life]), **values[method])
                for life, values in method_lives.items()]
            average = dict(natural_mean_score=mean(row['natural_mean_score'] for row in histories),
                natural_mean_utility=mean(row['natural_mean_utility'] for row in histories),
                natural_mean_h2_advantage=mean(row['natural_mean_h2_advantage'] for row in histories),
                references={block: {field: mean(row['references'][block][field] for row in histories)
                    for field in ('selected_reference_utility', 'selected_reference_regret', 'pairwise_weighted_error')}
                    for block in BLOCKS})
            methods.setdefault(method, {})[query] = dict(primary_estimable=complete, lifecycles=histories,
                primary=average if complete else None, available=average)
        for left, right in settings['contrasts']:
            histories = [dict(id=life, **contrast_history(group, left, right)) for life, group in by_life.items()]
            average = contrast_across(histories)
            comparisons.setdefault(left + '_minus_' + right, {})[query] = dict(primary_estimable=complete,
                lifecycles=histories, primary=average if complete else None, available=average)
    return dict(root_records=len(selected), expected_roots_per_query_history=expected, methods=methods, comparisons=comparisons)


def analyze_run(run):
    settings, cohort = run['settings'], run['cohort']
    roots, logs = cohort['roots'], cohort['log']
    references, replicas = run['references'], settings['reference_replicas']
    index = {row['root_id']: row for row in references}
    counts = logs['counts']
    expected = {(life, query, episode) for life in settings['lifecycles'] for query in settings['queries']
        for episode in range(settings['validation_roots_per_query'])}
    observed = {(root['life'], root['query'], root['episode']) for root in roots}
    new_ids = {root['id'] for root in roots if root['reference_origin'] == 'new'}
    checks = dict(run_terminal=run['status'] == 'complete', frozen_full_root_roster=len(observed) == len(roots) == len(expected)
        and observed == expected and len({root['id'] for root in roots}) == len(roots),
        frozen_method_and_contrast_rosters=settings['methods'] == list(METHODS)
            and settings['contrasts'] == [list(pair) for pair in CONTRASTS]
            and logs['methods'] == settings['methods'] and logs['contrasts'] == settings['contrasts'],
        new_reference_roster_complete=len(index) == len(references) == len(new_ids) and set(index) == new_ids,
        frozen_prediction_events_match=True, inherited_reference_binding=True, inherited_and_new_partition=True,
        fixed_reference_blocks=replicas == 32 and settings['reference_block_size'] == 16,
        no_new_training_natural_prefix_or_candidate_scoring=all(counts[key] == 0 for key in ZERO_COHORT_WORK),
        reference_trajectory_rosters=True, reference_work_accounted=True, reference_execution_wiring=True,
        reference_delta_rosters=True, all_natural_games_terminal=True, all_reference_trajectories_terminal=True)
    work = {origin: dict(ground_work=Counter(), planning_counts=Counter(), outcomes=Counter(), trajectories=0, seconds=0.)
        for origin in ('inherited', 'new')}
    rows, reference_status, missing = [], [], []
    # New reference logs are charged once, including missing-cohort or duplicated records if a run is malformed.
    for record in references:
        log = record['log']
        for name in ('ground_work', 'planning_counts', 'outcomes'):
            work['new'][name].update(log[name])
        work['new']['trajectories'] += log['trajectories']
        work['new']['seconds'] += record['seconds']
    for root in roots:
        origin = root['reference_origin']
        checks['inherited_and_new_partition'] &= origin == ('inherited' if root['episode'] < 2 else 'new')
        checks['frozen_prediction_events_match'] &= set(root['natural']) == set(METHODS) and set(root['predictions']) == set(METHODS[1:])
        for method, natural in root['natural'].items():
            checks['all_natural_games_terminal'] &= natural['status'] in TERMINAL
            checks['frozen_prediction_events_match'] &= (natural['seed'] == root['source_seed']
                and natural['query'] == root['query'] and natural['replica'] == root['episode'])
            if method == 'H2_ONLY':
                continue
            event = root['predictions'][method]
            checks['frozen_prediction_events_match'] &= (event['board'] == root['board']
                and event['step'] == root['step'] == natural['initiation_step']
                and event['option'] == natural['selected_option'] and set(event['predictions']) == set(OPTIONS)
                and event['score_semantics'] == ('prefix_utility' if method == 'PREFIX_ONLY_DIRECT' else 'rank_score'))
        row = dict(root_id=root['id'], life=root['life'], query=root['query'], episode=root['episode'],
            reference_origin=origin, natural=root['natural'], reference_complete=False, reference_metrics={})
        rows.append(row)
        if origin == 'inherited':
            inherited = root['inherited_reference']
            checks['inherited_reference_binding'] &= (inherited is not None
                and inherited['predictions'] == root['predictions']
                and all(inherited['root'][name] == root[name] for name in ('life', 'query', 'episode', 'board', 'step', 'source_seed')))
            if inherited is None:
                missing.append(root['id'])
                continue
            log = dict(inherited['terminal_log'], pair_deltas=inherited['paired_reference'])
            checks['inherited_reference_binding'] &= inherited['reference_complete'] is True
            for name in ('ground_work', 'planning_counts', 'outcomes'):
                work['inherited'][name].update(log[name])
            work['inherited']['trajectories'] += log['trajectories']
            work['inherited']['seconds'] += log['seconds']
        else:
            checks['inherited_reference_binding'] &= root['inherited_reference'] is None
            if root['id'] not in index:
                missing.append(root['id'])
                continue
            record = index[root['id']]
            log = record['log']
            checks['reference_execution_wiring'] &= bool(record['checks']) and all(value is True for value in record['checks'].values())
        checks['reference_trajectory_rosters'] &= log['trajectories'] == replicas * len(OPTIONS)
        checks['reference_work_accounted'] &= (sum(log['outcomes'].values()) == log['trajectories']
            and log['planning_counts'].get('model_uniform_draws', 0) == 4 * log['ground_work'].get('sampled_transitions', 0))
        terminal = not log['censored_root'] and set(log['outcomes']) <= set(TERMINAL)
        delta_complete = set(log['pair_deltas']) == set(OPTIONS[1:]) and all(
            len(log['pair_deltas'][option]) == replicas and all(len(value) == 3 for value in log['pair_deltas'][option])
            for option in OPTIONS[1:])
        checks['reference_delta_rosters'] &= delta_complete if terminal else not log['pair_deltas']
        checks['all_reference_trajectories_terminal'] &= terminal
        row['reference_complete'] = terminal and delta_complete
        reference_status.append(dict(root_id=root['id'], origin=origin, complete=row['reference_complete'],
            trajectories=log['trajectories'], outcomes=log['outcomes']))
        if not row['reference_complete']:
            missing.append(root['id'])
            continue
        values = reference_values(log, root['query'], replicas)
        row.update(reference_utility_means=values, reference_metrics=root_metrics(root, values))
    for group in work.values():
        for name in ('ground_work', 'planning_counts', 'outcomes'):
            group[name] = dict(group[name])
    checks['cohort_extraction_accounted'] = (counts['roots'] == len(roots)
        and counts['inherited_reference_roots'] == sum(root['reference_origin'] == 'inherited' for root in roots)
        and counts['new_reference_roots'] == len(new_ids)
        and counts['source_natural_games'] == len(roots) * len(METHODS)
        and counts['retained_prediction_events'] == len(roots) * (len(METHODS) - 1))
    complete = all(value for name, value in checks.items() if name not in ('all_reference_trajectories_terminal', 'all_natural_games_terminal'))
    return dict(schema='acfqp.natural_reference_analysis.v104', complete=complete,
        primary_complete=complete and all(checks.values()) and not missing, checks=checks,
        cohort=dict(roots=len(roots), inherited_reference_roots=len(roots) - len(new_ids), new_reference_roots=len(new_ids),
            missing_or_censored_reference_roots=missing), roots=rows, reference_status=reference_status,
        matched=summarize_cohort(rows, settings),
        descriptive_subcohorts={origin: summarize_cohort(rows, settings, origin) for origin in ('inherited', 'new')},
        actual_executed_work=dict(new_reference_work=work['new'], inherited_reference_work=work['inherited'],
            newly_sampled_environment_transitions=work['new']['ground_work'].get('sampled_transitions', 0),
            new_training_environment_transitions=counts['new_environment_transitions'], new_natural_transitions=0,
            new_model_prefix_transitions=counts['new_synthetic_transitions'], new_neural_model_fits=counts['neural_model_fits'],
            new_selector_calls=counts['new_selector_calls'], new_neural_candidate_predictions=counts['neural_candidate_predictions'],
            cohort_extraction_counts=counts, cohort_extraction_seconds=logs['seconds'], actual_wall_seconds=run['actual_wall_seconds']),
        inherited_v103_total_work=logs['inherited_v103_work'],
        evidence_scope='All 32 frozen natural decision roots use the same per-root and equal-history weights '
            'for 40 contrasts. Natural utility differences include one observed suffix; reference differences '
            'average 32 paired suffixes. Common pre-trigger returns cancel in each method contrast. The old8/new24 '
            'partition is descriptive only and contributes one quarter/three quarters within each history/query '
            'to the full cohort. A/B16 are independent suffix blocks, not model-selection data. Frozen H2 has '
            'zero reference advantage and no invented action-ranking estimate. No candidate model is fitted or '
            'rescored and no candidate prefix is simulated; reference H2 planning still performs model calculations '
            'and is retained in planning counts. The inherited eight reference roots are included in the referenced '
            'V103 total cost and must not be added to it again. Missing/censored references retain costs and '
            'the frozen natural cohort, while full-cohort reference estimates are unavailable. Two histories '
            'remain a pilot; no efficacy interval or scientific Gate.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = analyze_run(json.loads((args.directory / 'run.json').read_text()))
    (args.directory / 'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(complete=result['complete'], primary_complete=result['primary_complete'],
        checks=result['checks'], cohort=result['cohort'], actual_executed_work=result['actual_executed_work']), allow_nan=False))


if __name__ == '__main__':
    main()
