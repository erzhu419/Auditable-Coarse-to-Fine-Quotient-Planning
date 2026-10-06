#!/usr/bin/env python3
"""Verify compact V285 receipts without executing models or environments."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from math import isclose, sqrt
from pathlib import Path
from statistics import mean, stdev

PHASES = ('A', 'B', 'A_prime')
GROUPS = ('uniform', 'competition')
BATCHES = ('discovery', 'validation')
CONTRASTS = ('winner_minus_proxy', 'short_minus_proxy', 'retained_minus_proxy')
REPLICAS, MAX_STEPS, GOAL_RANK = 32, 8192, 11


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(left, right):
    return isclose(left, right, rel_tol=1e-11, abs_tol=1e-12)


def expected_seed(state, batch, replica):
    return (28500000000 + state['lifecycle']*1000000 + state['phase_index']*100000
            + state['slot']*1000 + BATCHES.index(batch)*100 + replica)


def lost_board(board):
    return (0 not in board and max(board) < GOAL_RANK
            and all(board[4*r+c] != board[4*r+c+1] for r in range(4) for c in range(3))
            and all(board[4*r+c] != board[4*(r+1)+c] for r in range(3) for c in range(4)))


def validate_rollout(state, row):
    require(row['action'] in state['legal_actions'], 'rollout action absent from selected legal actions')
    require(row['batch'] in BATCHES and 0 <= row['replica_index'] < REPLICAS, 'rollout batch/replica differs from frozen budget')
    require(row['seed'] == expected_seed(state, row['batch'], row['replica_index']), 'rollout seed differs from frozen paired stream')
    require(1 <= row['steps'] <= MAX_STEPS, 'rollout horizon excludes forced first step or exceeds cap')
    require(row['first_score'] == state['immediate_scores'][row['action']], 'forced action immediate score differs')
    require(row['total_score'] >= row['first_score'] >= 0, 'total and first score ledger differs')
    board = row['final_board']
    require(len(board) == 16, 'terminal board size differs')
    if row['status'] == 'WON':
        require(max(board) >= GOAL_RANK, 'WON receipt has no goal tile')
        bonus = 4.
    elif row['status'] == 'LOST':
        require(lost_board(board), 'LOST receipt retains a goal or legal move')
        bonus = -4.
    else:
        require(row['status'] == 'CUTOFF' and row['steps'] == MAX_STEPS, 'unknown terminal status or premature cutoff')
        bonus = 0.
    require(row['total_utility'] == row['total_score']/2048.+bonus, 'total utility omits reward or terminal bonus')
    require(row['suffix_utility'] == (row['total_score']-row['first_score'])/2048.+bonus, 'suffix utility includes first reward or wrong terminal bonus')


def rebuild_state(state, rows):
    values = {batch: {action: {} for action in state['legal_actions']} for batch in BATCHES}
    for row in rows:
        validate_rollout(state, row)
        bucket = values[row['batch']][row['action']]
        require(row['replica_index'] not in bucket, 'duplicate state/action/batch/replica')
        bucket[row['replica_index']] = row['total_utility']
    require(all(set(bucket) == set(range(REPLICAS)) for batch in values.values() for bucket in batch.values()),
            'each legal action requires both complete 32-replica batches')
    discovery = {action: mean(bucket.values()) for action, bucket in values['discovery'].items()}
    validation = {action: mean(bucket.values()) for action, bucket in values['validation'].items()}
    winner = min(discovery, key=lambda action: (-discovery[action], action))
    contrasts = {}
    for name, action in zip(CONTRASTS, (winner, state['short_action'], state['retained_action'])):
        differences = [values['validation'][action][i]-values['validation'][state['proxy_action']][i]
                       for i in range(REPLICAS)]
        contrasts[name] = dict(mean=mean(differences), paired_mc_se=stdev(differences)/sqrt(REPLICAS))
    return dict(state, winner=winner, discovery_means=discovery, validation_means=validation, contrasts=contrasts)


def rebuild_groups(states):
    groups = {}
    for group in GROUPS:
        lives = []
        for life in range(16):
            phases = {}
            for phase in PHASES:
                selected = [s for s in states if (s['group'], s['lifecycle'], s['phase']) == (group, life, phase)]
                require(len(selected) == 4, 'four states per group/phase/lifecycle are required')
                phases[phase] = dict(states=4, contrasts={name: mean(s['contrasts'][name]['mean'] for s in selected)
                                                        for name in CONTRASTS})
            lives.append(dict(lifecycle=life, parent=life%4, phases=phases,
                contrasts={name: mean(p['contrasts'][name] for p in phases.values()) for name in CONTRASTS}))
        groups[group] = lives
    return groups


def check_contrast(saved, lives, name):
    deltas = {str(row['lifecycle']): row['contrasts'][name] for row in lives}
    require(saved['lifecycle_deltas'] == deltas, 'signed lifecycle deltas differ')
    require(saved['mean'] == mean(deltas.values()), 'equal-life mean differs')
    require(saved['improved_equal_worse'] == [sum(v > 0 for v in deltas.values()), sum(v == 0 for v in deltas.values()),
                                             sum(v < 0 for v in deltas.values())], 'positive/equal/negative lives filtered')
    require(saved['adverse_lifecycles'] == [int(life) for life, v in deltas.items() if v < 0], 'adverse lifecycle list differs')
    parent_values = {p: [row['contrasts'][name] for row in lives if row['parent'] == p] for p in range(4)}
    require(saved['parent_mean_deltas'] == {str(p): mean(v) for p, v in parent_values.items()}, 'fixed parent means differ')
    require(saved['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS', 'bootstrap scope differs')
    low, high = saved['ci95']
    require(mean(min(v) for v in parent_values.values()) <= low <= high <= mean(max(v) for v in parent_values.values()),
            'bootstrap interval outside possible within-parent resamples')


def check_counts(counts, rows, states):
    n, steps = len(rows), sum(row['steps'] for row in rows)
    wins = sum(row['status'] == 'WON' for row in rows)
    expected = dict(sampled_transitions=steps, environment_random_draws=2*steps,
        ground_explicit_swipe_calls=steps, ground_state_status_calls=steps,
        ground_status_internal_swipe_calls=4*(steps-wins), ground_swipe_calls=steps+4*(steps-wins))
    require(Counter(counts['environment']) == Counter(expected), 'actual environment transition/RNG/status costs differ')
    rollout = counts['rollout']
    require(rollout['completed_rollouts'] == rollout['rng_streams_started'] == n, 'physical branch streams or rollout count differs')
    require(rollout.get('continuation_choose_calls', 0) == steps-n, 'forced step incorrectly billed as H2 continuation')
    require(rollout['evaluate_calls'] == 2*len(states) and rollout['replica_streams'] == 64*len(states), 'two batch/replica budget differs')
    planning = Counter(counts['planning'])
    require(planning['root_swipe_calls'] == 4*(steps-n), 'H2 root work differs from continuation decisions')
    require(planning['learned_swipe_calls'] == planning['root_swipe_calls']+planning['second_ply_swipe_calls'], 'H2 swipe ledger differs')
    require(planning['leaf_choose_calls'] == planning['generated_spawn_outcomes'] == planning['expanded_postspawn_states'], 'successor/leaf work differs')
    require(planning['spawn_rank1_outcomes'] == planning['spawn_rank2_outcomes'] and
            planning['generated_spawn_outcomes'] == planning['spawn_rank1_outcomes']+planning['spawn_rank2_outcomes'], 'rank successor counts differ')
    require(planning['expectimax_probability_products'] == planning['expectimax_probability_sums'] == planning['generated_spawn_outcomes'], 'H2 probability work differs')
    require(planning['table_lookups'] == 32*planning['value_predictions'], 'value/table work differs')


def audit(directory):
    directory = Path(directory)
    document = json.loads((directory/'summary.json').read_text())
    selection = json.loads(Path(document['selection']).read_text())
    summary = document['summary']
    settings = document['settings']
    require(settings == selection['settings'], 'frozen selection settings changed')
    require(settings['replicas_per_batch'] == 32 and settings['max_steps'] == 8192 and settings['batches'] == list(BATCHES), 'frozen rollout budget changed')
    require(settings['bootstrap_draws'] == summary['bootstrap_draws'] == 20000 and
            settings['bootstrap_seed'] == summary['bootstrap_seed'] == 28500001, 'registered bootstrap settings differ')
    original = {s['state_id']: s for s in selection['states']}
    require(len(original) == 384, 'complete frozen state selection absent')
    buckets, rows, states = defaultdict(list), [], []
    for parent in document['parent_receipts']:
        path = Path(parent['trace_file'])
        require(path.stat().st_size == parent['trace_bytes'], 'compact rollout file size differs')
        current = []
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                require(row['state_id'] in original, 'rollout outside frozen selection')
                current.append(row)
                buckets[row['state_id']].append(row)
        for state in parent['states']:
            require(state['parent'] == parent['parent'] == state['lifecycle']%4, 'source-parent identity differs')
            require(all(state[key] == value for key, value in original[state['state_id']].items()), 'selected board or prefix metadata changed')
            require(state['proxy_action'] == min(state['full_action_scores'], key=lambda a: (-state['full_action_scores'][a], a)), 'fixed full proxy rank differs')
            require(state['short_action'] == min(state['short_action_scores'], key=lambda a: (-state['short_action_scores'][a], a)), 'short proxy rank differs')
            require(state['legal_actions'] == sorted(state['full_action_scores']), 'legal-action inventory differs')
            rebuilt = rebuild_state(state, buckets[state['state_id']])
            states.append(rebuilt)
        check_counts(parent['counts'], current, parent['states'])
        components = Counter(parent['component_counts'])
        require(components['component_calls'] == len(parent['states']) and components['compose_calls'] == 3*len(parent['states']), 'root extraction/reweight work differs')
        require(components['table_lookups'] == 32*components['value_predictions'], 'root value/table costs differ')
        require(parent['new_leaf_updates'] == parent['setup']['new_leaf_updates'] == 0, 'frozen value was trained')
        require(parent['setup']['checkpoint_loads'] == 1, 'parent checkpoint load billed repeatedly')
        rows.extend(current)
    require(len(states) == len({s['state_id'] for s in states}) == 384 and
            {s['state_id'] for s in states} == set(original), 'complete state inventory differs')
    require(sum(len(s['legal_actions']) for s in states) == 1418 and len(rows) == 90752, 'actual frozen action/rollout budget differs')
    saved_states = {s['state_id']: s for s in summary['state_results']}
    require(set(saved_states) == set(original) and len(summary['state_results']) == 384, 'analysis state inventory differs')
    for state in states:
        require(saved_states[state['state_id']] == state, 'independent discovery/validation state statistics differ')
    groups = rebuild_groups(states)
    group_results = {}
    for group, lives in groups.items():
        saved = summary['groups'][group]
        require(saved['states'] == 192 and saved['by_lifecycle'] == lives, 'separate group/phase/life weighting differs')
        for name in CONTRASTS:
            check_contrast(saved['contrasts'][name], lives, name)
            for phase in PHASES:
                phase_lives = [dict(lifecycle=s['lifecycle'], parent=s['parent'], contrasts=s['phases'][phase]['contrasts']) for s in lives]
                check_contrast(saved['contrasts'][name]['phases'][phase], phase_lives, name)
        group_results[group] = {name: {key: saved['contrasts'][name][key] for key in ('mean', 'ci95', 'improved_equal_worse', 'adverse_lifecycles')}
                                for name in CONTRASTS}
        subset = [s for s in states if s['group'] == group]
        bias = {s['state_id']: s['full_tail_scores'][s['proxy_action']]
                - (s['validation_means'][s['proxy_action']]-s['immediate_scores'][s['proxy_action']]/2048.) for s in subset}
        saved_tail = summary['tail_calibration'][group]
        require(close(saved_tail['mean_proxy_tail_bias'], mean(bias.values())), 'tail calibration full mean differs')
        for life in range(16):
            require(close(saved_tail['by_lifecycle'][str(life)], mean(bias[s['state_id']] for s in subset if s['lifecycle'] == life)), 'tail lifecycle weighting differs')
        for phase in PHASES:
            require(close(saved_tail['phases'][phase], mean(bias[s['state_id']] for s in subset if s['phase'] == phase)), 'tail phase weighting differs')
    accounting = document['accounting']
    require(accounting['new_evaluation_rollouts'] == summary['rollouts'] == len(rows), 'global rollout count differs')
    require(accounting['new_evaluation_transitions'] == sum(r['steps'] for r in rows), 'global sampled-transition count differs')
    terminals = dict(Counter(r['status'] for r in rows))
    require(accounting['terminal_counts'] == terminals, 'terminal counts differ')
    require(terminals.get('CUTOFF', 0) == 0, '8192/rank11 terminal mass bound violated')
    require(accounting['new_training_observations'] == accounting['new_value_updates'] == 0, 'diagnostic feedback credited as training')
    for key in ('environment', 'planning'):
        require(Counter(accounting[key+'_counts']) == sum((Counter(p['counts'][key]) for p in document['parent_receipts']), Counter()), 'global '+key+' costs differ')
    require(Counter(accounting['component_counts']) == sum((Counter(p['component_counts']) for p in document['parent_receipts']), Counter()), 'global component costs differ')
    require(close(accounting['worker_cpu_seconds'], sum(p['cpu_seconds'] for p in document['parent_receipts'])), 'worker CPU duplicated or omitted')
    require(accounting['trace_bytes'] == sum(p['trace_bytes'] for p in document['parent_receipts']), 'retained trace bytes differ')
    require(document['source_provenance'] == selection['source_provenance'] and
            accounting['inherited_v281_costs'] == selection['inherited_v281_costs'], 'inherited source/evaluation costs differ')
    require(accounting['inherited_source_training_transitions'] == sum(s['inherited_training_costs']['environment_counts']['sampled_transitions']
            for s in selection['source_provenance']['parents']), 'source training costs repeated or dropped')
    require(accounting['inherited_dynamics_costs'] == selection['source_provenance']['inherited_dynamics_costs'], 'inherited dynamics costs differ')
    return dict(status='PASS', independent_valid=True, selected_states=384, legal_action_queries=1418,
        continuation_rollouts=len(rows), independent_replica_streams=24576, terminal_counts=terminals,
        complete_signed_group_contrasts=group_results, new_training_observations=0, new_value_updates=0,
        sampled_transitions=accounting['new_evaluation_transitions'], retained_trace_bytes=accounting['trace_bytes'],
        bootstrap_audit='All signed lifecycle/phase deltas, fixed-parent means, registered scope and interval bounds checked; existing 20000-draw CI calculation was not rerun.',
        scope='Fixed true-p H2 continuation at separately reported uniform and competition states; discovery winner frozen before independent validation. Not optimal Q or new learned-policy performance.',
        method='Compact score/status/seed/inventory/counter and independent statistics audit. No model, environment or planning execution.', errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Completed V285 report directory')
    directory = parser.parse_args().input
    try:
        result = audit(directory)
    except ValueError as error:
        result = dict(status='FAIL', independent_valid=False, errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(not result['independent_valid'])


if __name__ == '__main__':
    main()
