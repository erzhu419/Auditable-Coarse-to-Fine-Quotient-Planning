"""Paired action-gap and policy-offset analysis on the frozen divergence panel."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import sys
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_consequences_v126 as old
from acfqp.domains import standard_2048 as ground

LIVES, POLICIES = old.LIVES, old.POLICIES
QUERIES = {q: old.QUERIES[q] for q in ('risk1', 'risk8')}
REPLICAS, MAX_STEPS, BASE = 16, 2000, 128*100000000
read_rows, mean = old.read_rows, old.mean


def suffix_seed(root, replica):
    return BASE + 90000000 + root*1000 + replica


def paired_summary(values):
    values = np.asarray(values, dtype=float)
    return dict(mean=float(values.mean()), mc_se=float(values.std(ddof=1)/math.sqrt(len(values))), n=len(values))


def anchored_value(prediction, policy, query):
    src, q = old.QUERIES[policy], QUERIES[query]
    if max(prediction['afterstate']) >= 11:
        return prediction['score']/2048. + q['goal_bonus']
    return prediction['value'] + (src['failure_penalty'] - q['failure_penalty']) + (
        (q['failure_penalty'] + q['goal_bonus']) - (src['failure_penalty'] + src['goal_bonus'])) * prediction['success_probability']


def branch_key(row):
    return row['root_id'], row['forced_action'], row['policy'], row['replica']


def branch_valid(row, root, source_updates):
    r = row['result']; n = r['steps']; work = r['environment_counts']; prediction = root['predictions'][row['policy']][row['forced_action']]
    return (row['life'] == root['life'] and row['seed'] == suffix_seed(root['root_id'], row['replica'])
        and 0 < n <= MAX_STEPS and r['status'] in ('WON', 'LOST', 'CUTOFF')
        and (r['status'] != 'CUTOFF' or n == MAX_STEPS)
        and row['initial_board'] == root['board'] and row['initial_spawns'] == []
        and len(row['final_board']) == 16 and (max(row['final_board']) >= 11) == (r['status'] == 'WON')
        and all(len(row[key]) == n for key in ('actions', 'spawned_cells', 'spawned_ranks', 'scores'))
        and row['actions'][0] == row['forced_action'] and row['scores'][0] == prediction['score']
        and all(a in ('DOWN', 'LEFT', 'RIGHT', 'UP') for a in row['actions'])
        and all(0 <= c < 16 for c in row['spawned_cells']) and all(rank in (1, 2) for rank in row['spawned_ranks'])
        and sum(row['scores']) == r['score'] and r['components'] == old.components(r['score'], r['status'])
        and r['utility'] == old.utility(r['score'], r['status'], row['policy'])
        and work.get('sampled_transitions') == n and work.get('initial_spawns', 0) == 0
        and work.get('environment_random_draws') == 2*n and work.get('ground_explicit_swipe_calls') == n
        and work.get('forced_actions') == 1 and r['policy_counts'].get('choose_calls', 0) == n-1
        and r['source_updates_before'] == r['source_updates_after'] == source_updates
        and not r['policy_counts'].get('td_updates', 0) and not r['policy_counts'].get('model_spawn_samples', 0))


def completed_rows(indexed, valid, root_id, action, policy):
    keys = [(root_id, action, policy, r) for r in range(REPLICAS)]
    complete = all(k in indexed and valid.get(k, False) and indexed[k]['result']['status'] in ('WON', 'LOST') for k in keys)
    return [indexed[k] for k in keys] if complete else None


def outcome_arrays(rows, query):
    return dict(success=np.asarray([r['result']['status'] == 'WON' for r in rows], dtype=float),
        utility=np.asarray([old.utility(r['result']['score'], r['result']['status'], query) for r in rows]))


def action_gap(case, root, indexed, valid):
    """Use the same suffix replicate for both actions and every error term."""
    left, right = case['left_action'], case['right_action']
    result = {k: case[k] for k in ('case_id', 'life', 'query', 'replica', 'root_id', 'diverged')}
    if not case['diverged']:
        return dict(result, complete=True, measured=False)
    l = completed_rows(indexed, valid, root['root_id'], left, 'risk_goal')
    r = completed_rows(indexed, valid, root['root_id'], right, 'risk_goal')
    result.update(left_action=left, right_action=right, measured=True, complete=l is not None and r is not None)
    if not result['complete']:
        return result
    pred_l, pred_r = root['predictions']['risk_goal'][left], root['predictions']['risk_goal'][right]
    source_l, source_r = outcome_arrays(l, 'risk_goal'), outcome_arrays(r, 'risk_goal')
    new_l, new_r = outcome_arrays(l, case['query']), outcome_arrays(r, case['query'])
    q = QUERIES[case['query']]; coefficient = q['failure_penalty'] + q['goal_bonus'] - 8.
    anchor_gap = pred_l['value'] - pred_r['value']
    success_gap = pred_l['success_probability'] - pred_r['success_probability']
    predicted_gap = anchored_value(pred_l, 'risk_goal', case['query']) - anchored_value(pred_r, 'risk_goal', case['query'])
    ds = source_l['success'] - source_r['success']; du_source = source_l['utility'] - source_r['utility']
    du_new = new_l['utility'] - new_r['utility']
    samples = dict(success_gap=ds, source_utility_gap=du_source, new_utility_gap=du_new,
        anchor_gap_error=anchor_gap-du_source, success_correction_error=coefficient*(success_gap-ds),
        total_gap_error=predicted_gap-du_new)
    residual = samples['total_gap_error'] - samples['anchor_gap_error'] - samples['success_correction_error']
    result.update(coefficient=coefficient, predicted_anchor_gap=anchor_gap, predicted_success_gap=success_gap,
        predicted_new_gap=predicted_gap, decomposition_max_residual=float(np.abs(residual).max()),
        paired={k: paired_summary(v) for k, v in samples.items()},
        replica_values={k: v.tolist() for k, v in samples.items()},
        mc_mean_favors_constant=float(du_new.mean()) < 0)
    return result


def aggregate_cases(rows):
    """Aggregate each suffix index first; shared-root aliases retain covariance."""
    groups = []
    for life in LIVES:
        for query in QUERIES:
            group = [r for r in rows if r['life'] == life and r['query'] == query]
            measured = [r for r in group if r['measured']]
            complete = len(group) == 8 and all(r['complete'] for r in group)
            item = dict(life=life, query=query, cases=len(group), measured_cases=len(measured),
                no_divergence_cases=len(group)-len(measured), complete=complete)
            if complete and measured:
                keys = measured[0]['replica_values']
                replicas = {k: np.mean([r['replica_values'][k] for r in measured], axis=0) for k in keys}
                item.update(paired={k: paired_summary(v) for k, v in replicas.items()},
                    replica_values={k: v.tolist() for k, v in replicas.items()},
                    mc_mean_favors_constant=sum(r['mc_mean_favors_constant'] for r in measured),
                    mean_predicted_gap=mean(r['predicted_new_gap'] for r in measured))
            groups.append(item)
    overall = {}
    for query in QUERIES:
        group = [r for r in groups if r['query'] == query]
        ready = all(r['complete'] and r['measured_cases'] for r in group)
        overall[query] = dict(complete=bool(ready), measured_cases=sum(r['measured_cases'] for r in group))
        if ready:
            values = {k: np.mean([r['replica_values'][k] for r in group], axis=0) for k in group[0]['replica_values']}
            overall[query].update(paired={k: paired_summary(v) for k, v in values.items()},
                mc_mean_favors_constant=sum(r['mc_mean_favors_constant'] for r in group),
                mean_predicted_gap=mean(r['mean_predicted_gap'] for r in group))
    return dict(lifecycles=groups, four_life_means=overall)


def policy_comparisons(root, query, action, indexed, valid):
    rows = {p: completed_rows(indexed, valid, root['root_id'], action, p) for p in POLICIES}
    result = dict(root_id=root['root_id'], life=root['life'], query=query, action=action,
        complete=all(r is not None for r in rows.values()))
    if not result['complete']:
        return result
    predictions = {p: root['predictions'][p][action] for p in POLICIES}
    outcomes = {p: outcome_arrays(rows[p], query) for p in POLICIES}
    predicted = {p: anchored_value(predictions[p], p, query) for p in POLICIES}
    diagnostics, samples = {}, {}
    for policy in POLICIES:
        source_values = outcome_arrays(rows[policy], policy)['utility']
        samples[policy+'_anchor_error'] = predictions[policy]['value']-source_values
        samples[policy+'_success_error'] = predictions[policy]['success_probability']-outcomes[policy]['success']
        diagnostics[policy] = dict(source_anchor=predictions[policy]['value'],
            predicted_success=predictions[policy]['success_probability'], predicted_new_value=predicted[policy],
            source_utility=paired_summary(source_values),
            source_anchor_error=paired_summary(predictions[policy]['value']-source_values),
            success_error=paired_summary(predictions[policy]['success_probability']-outcomes[policy]['success']),
            new_utility=paired_summary(outcomes[policy]['utility']))
    delta = outcomes['risk_goal']['utility']-outcomes['reward']['utility']
    pred_delta = predicted['risk_goal']-predicted['reward']
    samples.update(mc_policy_gap=delta, policy_gap_error=pred_delta-delta,
        selected_policy_value_error=predicted['risk_goal' if pred_delta > 0 else 'reward'] -
            outcomes['risk_goal' if pred_delta > 0 else 'reward']['utility'])
    return dict(result, policies=diagnostics, predicted_policy_gap=pred_delta,
        replica_values={k: v.tolist() for k, v in samples.items()},
        mc_policy_gap=paired_summary(delta), policy_gap_error=paired_summary(pred_delta-delta),
        predicted_order_matches_mc_mean=pred_delta*float(delta.mean()) > 0,
        selected_policy='risk_goal' if pred_delta > 0 else 'reward',
        selected_policy_value_error=paired_summary(predicted['risk_goal' if pred_delta > 0 else 'reward'] -
            outcomes['risk_goal' if pred_delta > 0 else 'reward']['utility']))


def cross_policy_summary(cases, comparisons):
    indexed = {(r['root_id'], r['query'], r['action']): r for r in comparisons}
    groups = []
    for life in LIVES:
        for query in QUERIES:
            rows = [c for c in cases if c['life'] == life and c['query'] == query and c['diverged']]
            result = dict(life=life, query=query, measured_cases=len(rows), complete=True)
            paired_cases, predicted = [], []
            for case in rows:
                pair = [indexed[case['root_id'], query, case[k]] for k in ('left_action', 'right_action')]
                result['complete'] &= all(r['complete'] for r in pair)
                if all(r['complete'] for r in pair):
                    paired_cases.append({k: np.mean([r['replica_values'][k] for r in pair], axis=0) for k in pair[0]['replica_values']})
                    predicted.append(mean(r['predicted_policy_gap'] for r in pair))
            if result['complete'] and paired_cases:
                arrays = {k: np.mean([r[k] for r in paired_cases], axis=0) for k in paired_cases[0]}
                result.update(paired={k: paired_summary(v) for k, v in arrays.items()},
                    replica_values={k: v.tolist() for k, v in arrays.items()}, mean_predicted_policy_gap=mean(predicted))
            groups.append(result)
    totals = {}
    for query in QUERIES:
        rows = [r for r in groups if r['query'] == query]
        totals[query] = dict(complete=all(r['complete'] and r['measured_cases'] for r in rows))
        if totals[query]['complete']:
            arrays = {k: np.mean([r['replica_values'][k] for r in rows], axis=0) for k in rows[0]['replica_values']}
            totals[query].update(paired={k: paired_summary(v) for k, v in arrays.items()},
                mean_predicted_policy_gap=mean(r['mean_predicted_policy_gap'] for r in rows))
    return dict(lifecycles=groups, four_life_means=totals)


def inspect_prefix(left, right, counts):
    """Independent ground swipe replay; no source model or stochastic draws."""
    board = tuple(left['initial_board'])
    checks = dict(paired_history=left['seed'] == right['seed'] and left['initial_board'] == right['initial_board'],
        shared_prefix=True, recorded_prefix=True)
    for index, pair in enumerate(zip(left['actions'], right['actions'])):
        a, b = pair
        if a != b:
            return dict(diverged=True, index=index, board=list(board), left_action=a,
                right_action=b, shared_prefix_steps=index, checks=checks)
        checks['shared_prefix'] &= all(left[k][index] == right[k][index] for k in ('scores', 'spawned_cells', 'spawned_ranks'))
        afterstate, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(a))
        counts['audit_prefix_swipes'] += 1
        cell, rank = left['spawned_cells'][index], left['spawned_ranks'][index]
        checks['recorded_prefix'] &= changed and score == left['scores'][index] and afterstate[cell] == 0
        successor = list(afterstate); successor[cell] = rank; board = tuple(successor)
    checks['shared_prefix'] &= len(left['actions']) == len(right['actions'])
    checks['recorded_prefix'] &= list(board) == left['final_board'] == right['final_board']
    return dict(diverged=False, index=None, board=None, left_action=None, right_action=None,
        shared_prefix_steps=len(left['actions']), checks=checks)


def inspect_roster(roster, sources):
    checks = dict(case_roster=True, retained_case_history=True, independent_start_boards=True,
        first_encounter_roots=True, root_action_union=True, prediction_roster=True,
        retained_predictions=True, predicted_choice_reproduced=True, frozen_attempt_budget=True)
    counts, started = Counter(), perf_counter()
    retained = {}
    for life, source in sources.items():
        for row in read_rows(Path(source['control_trace'])):
            if row['method'] in ('LEARNED_risk_goal', 'CONSTANT_risk_goal') and row['checkpoint'] == 1024 and row['query'] in QUERIES:
                retained[life, row['query'], row['replica'], row['method']] = row
    expected = [(life, query, rep) for life in LIVES for query in QUERIES for rep in range(8)]
    checks['case_roster'] &= [(r['life'], r['query'], r['replica']) for r in roster['cases']] == expected
    checks['case_roster'] &= len({r['case_id'] for r in roster['cases']}) == len(expected)
    root_ids, unions, root_queries = {}, {}, {}
    roots = {r['root_id']: r for r in roster['roots']}
    logical = 0
    for case in roster['cases']:
        life, query, rep = case['life'], case['query'], case['replica']
        left = retained.get((life, query, rep, 'LEARNED_risk_goal'))
        right = retained.get((life, query, rep, 'CONSTANT_risk_goal'))
        if left is None or right is None:
            checks['retained_case_history'] = False
            continue
        checks['retained_case_history'] &= (case['left_eval_id'], case['right_eval_id']) == (left['eval_id'], right['eval_id'])
        found = inspect_prefix(left, right, counts)
        checks['independent_start_boards'] &= all(found['checks'].values())
        checks['retained_case_history'] &= all(case[k] == v for k, v in found.items() if k != 'checks')
        if not case['diverged']:
            checks['first_encounter_roots'] &= case['root_id'] is None
            continue
        key = life, tuple(found['board'])
        if key not in root_ids:
            root_ids[key] = len(root_ids)
        expected_id = root_ids[key]; root = roots.get(case['root_id'])
        checks['first_encounter_roots'] &= root is not None and case['root_id'] == expected_id
        if root is None:
            continue
        checks['independent_start_boards'] &= root['board'] == found['board'] and root['life'] == life
        unions.setdefault(expected_id, set()).update((case['left_action'], case['right_action']))
        root_queries.setdefault(expected_id, set()).add(query); logical += 2*len(POLICIES)*REPLICAS
        pred = root['predictions']['risk_goal']; i = case['index']
        lp, rp = pred[case['left_action']], pred[case['right_action']]
        checks['retained_predictions'] &= (lp['value'] == left['chosen_anchor_values'][i]
            and lp['success_probability'] == left['chosen_success_probabilities'][i]
            and rp['value'] == right['chosen_anchor_values'][i])
        learned_choice = min(pred, key=lambda a: (-anchored_value(pred[a], 'risk_goal', query), a))
        prior = sources[life]['counts']['risk_goal']['constant']
        def constant_value(action):
            p = dict(pred[action], success_probability=1. if max(pred[action]['afterstate']) >= 11 else prior)
            return anchored_value(p, 'risk_goal', query)
        constant_choice = min(pred, key=lambda a: (-constant_value(a), a))
        checks['retained_predictions'] &= (anchored_value(lp, 'risk_goal', query) == left['chosen_values'][i]
            and constant_value(case['right_action']) == right['chosen_values'][i]
            and right['chosen_success_probabilities'][i] == (1. if max(rp['afterstate']) >= 11 else prior))
        checks['predicted_choice_reproduced'] &= (learned_choice, constant_choice) == (case['left_action'], case['right_action'])
    checks['first_encounter_roots'] &= [r['root_id'] for r in roster['roots']] == list(range(len(root_ids)))
    for root in roster['roots']:
        ident = root['root_id']
        checks['root_action_union'] &= root['actions'] == sorted(unions.get(ident, ()))
        checks['prediction_roster'] &= set(root['predictions']) == set(POLICIES)
        legal = set(root['predictions']['reward'])
        checks['prediction_roster'] &= set(root['predictions']['risk_goal']) == legal and set(root['actions']) <= legal
        for action in legal:
            a, b = (root['predictions'][p][action] for p in POLICIES)
            checks['prediction_roster'] &= a['score'] == b['score'] and a['afterstate'] == b['afterstate']
            checks['prediction_roster'] &= all(math.isfinite(p['value']) and 0 <= p['success_probability'] <= 1 for p in (a, b))
    physical = sum(len(r['actions'])*len(POLICIES)*REPLICAS for r in roster['roots'])
    checks['frozen_attempt_budget'] &= roster['physical_attempts'] == physical <= 4096 and roster['logical_attempts'] == logical
    return dict(checks=checks, audit_counts=dict(counts), seconds=perf_counter()-started,
        root_queries=root_queries, physical_attempts=physical, logical_attempts=logical)


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    run = json.loads((directory/'run.json').read_text()); roster = json.loads((directory/'roster.json').read_text())
    source = json.loads((directory/'source_capsule.json').read_text()); sources = {r['life']: r for r in source['snapshots']}
    expected_settings = dict(lifecycles=list(LIVES), queries=QUERIES, policies={p: old.QUERIES[p] for p in POLICIES},
        retained_replicas=8, retained_checkpoint=1024, replicas=REPLICAS, max_steps=MAX_STEPS,
        workers=4, version_base=BASE, p_four=.1)
    checks = dict(frozen_settings=run['settings'] == expected_settings,
        source_roster=source['schema'] == 'acfqp.forced_actions.v128.source' and len(source['snapshots']) == 4
            and set(sources) == set(LIVES) and all(set(r) == {'life', 'rule', 'models', 'counts', 'control_trace'} for r in source['snapshots']),
        lifecycle_roster=len(run['lifecycles']) == 4 and {r['life'] for r in run['lifecycles']} == set(LIVES),
        inherited_costs=run['inherited_costs'] == source['inherited_costs'], preparation=run['preparation'] == roster['preparation'],
        source_origins=True, preparation_immutable=True, model_load_counts=True,
        continuation_immutable=True, branch_roster=True, branch_traces=True, branch_totals=True,
        full_terminal_branches=True, physical_attempts=True, error_decomposition=True)
    found = inspect_roster(roster, sources); checks.update(found['checks'])
    roots = {r['root_id']: r for r in roster['roots']}
    checks['preparation'] &= roster['preparation']['prefix_counts'].get('recorded_spawns_replayed', 0) == found['audit_counts'].get('audit_prefix_swipes', 0)
    checks['preparation'] &= len(roster['preparation']['lifecycles']) == 4
    for prepared in roster['preparation']['lifecycles']:
        life = prepared['life']; snapshot = sources[life]
        checks['source_origins'] &= (set(prepared['models']) == set(POLICIES)
            and snapshot['control_trace'] == str(ROOT/'reports/controlled_predictive_anchored_success_v127'/f'life_{life}'/'control.jsonl.gz'))
        for policy in POLICIES:
            data = prepared['models'][policy]; scalar, counts = snapshot['models'][policy], snapshot['counts'][policy]
            checks['source_origins'] &= scalar['path'] == str(ROOT/'reports/controlled_predictive_ntuple_learning_v120'/f'life_{life}'/policy/'checkpoint_4096.npz')
            checks['source_origins'] &= counts['path'] == str(ROOT/'reports/controlled_predictive_anchored_success_v127'/f'life_{life}'/policy/'checkpoint_1024.npz')
            checks['preparation_immutable'] &= (data['source_updates_before'] == data['source_updates_after'] == scalar['updates']
                and data['count_updates_before'] == data['count_updates_after'] == counts['updates']
                and data['constant'] == counts['constant']
                and all(not data['prediction_counts'].get(k, 0) for k in ('source_td_updates', 'success_observation_updates', 'count_array_writes', 'model_spawn_samples')))
            checks['model_load_counts'] &= (data['source_load_counts'].get('checkpoint_loads') == 1
                and data['source_load_counts'].get('checkpoint_loaded_parameters') == scalar['nonzero_weights']
                and data['count_load_counts'].get('checkpoint_loads') == 1
                and data['count_load_counts'].get('checkpoint_loaded_count_entries') == 2*data['count_load_counts'].get('checkpoint_loaded_addresses', -1))
    costs = dict(continuations=old.new_cost(), preparation=roster['preparation'],
        continuation_model_load_counts=Counter(), continuation_model_load_seconds=0.,
        continuation_model_setup_counts=Counter(), continuation_model_setup_seconds=0.,
        peak_continuation_weight_bytes_per_life=0, analysis_counts=found['audit_counts'], analysis_prefix_seconds=found['seconds'])
    indexed, valid = {}, {}
    for life in run['lifecycles']:
        ident = life['life']; snapshot = sources[ident]; cost = old.new_cost()
        rows = list(read_rows(directory/life['trace'])); keys = [branch_key(r) for r in rows]
        expected = {(r['root_id'], action, p, rep) for r in roster['roots'] if r['life'] == ident
            for action in r['actions'] for p in POLICIES for rep in range(REPLICAS)}
        checks['branch_roster'] &= len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
        for row in rows:
            key = branch_key(row); ready = branch_valid(row, roots[row['root_id']], snapshot['models'][row['policy']]['updates'])
            checks['branch_traces'] &= ready; checks['full_terminal_branches'] &= row['result']['status'] in ('WON', 'LOST')
            indexed[key], valid[key] = row, ready; old.add_cost(cost, row)
        checks['branch_totals'] &= (cost['games'] == life['games'] and cost['seconds'] == life['continuation_seconds']
            and all(cost[k] == life[k] for k in ('statuses', 'environment_counts', 'policy_counts')))
        old.merge_cost(costs['continuations'], cost)
        checks['continuation_immutable'] &= set(life['models']) == set(POLICIES)
        for policy in POLICIES:
            data = life['models'][policy]; scalar = snapshot['models'][policy]
            checks['continuation_immutable'] &= data['source_updates_before'] == data['source_updates_after'] == scalar['updates']
            checks['model_load_counts'] &= (data['source_load_counts'].get('checkpoint_loads') == 1
                and data['source_load_counts'].get('checkpoint_loaded_parameters') == scalar['nonzero_weights'])
            costs['continuation_model_load_counts'].update(data['source_load_counts']); costs['continuation_model_load_seconds'] += data['source_load_seconds']
            costs['continuation_model_setup_counts'].update(data['source_setup_counts']); costs['continuation_model_setup_seconds'] += data['source_setup_seconds']
        costs['peak_continuation_weight_bytes_per_life'] = max(costs['peak_continuation_weight_bytes_per_life'], life['peak_weight_bytes'])
    costs.update(physical_attempts=costs['continuations']['games'], logical_attempts=found['logical_attempts'],
        actual_new_environment_transitions=costs['continuations']['environment_counts'].get('sampled_transitions', 0),
        model_spawn_samples=costs['continuations']['policy_counts'].get('model_spawn_samples', 0), training_updates=0)
    checks['physical_attempts'] &= costs['physical_attempts'] == found['physical_attempts']
    cases = [action_gap(c, roots.get(c['root_id']), indexed, valid) for c in roster['cases']]
    checks['error_decomposition'] &= all(r.get('decomposition_max_residual', 0.) < 1e-10 for r in cases)
    comparisons = [policy_comparisons(r, q, action, indexed, valid) for r in roster['roots']
        for q in QUERIES if q in found['root_queries'].get(r['root_id'], ()) for action in r['actions']]
    panel = {}
    def distribution(values):
        return dict(min=min(values), median=float(np.median(values)), max=max(values)) if values else None
    for query in QUERIES:
        chosen = [c for c in roster['cases'] if c['query'] == query and c['diverged']]
        margins = [anchored_value(roots[c['root_id']]['predictions']['risk_goal'][c['left_action']], 'risk_goal', query)
            - anchored_value(roots[c['root_id']]['predictions']['risk_goal'][c['right_action']], 'risk_goal', query) for c in chosen]
        panel[query] = dict(divergent_cases=len(chosen), first_divergence_index=distribution([c['index'] for c in chosen]),
            predicted_new_gap=distribution(margins))
    complete = run['status'] == 'complete' and all(v for k, v in checks.items() if k != 'full_terminal_branches')
    return dict(schema='acfqp.forced_actions.v128.analysis', complete=bool(complete),
        primary_complete=bool(complete and checks['full_terminal_branches']), checks={k: bool(v) for k, v in checks.items()},
        action_gap_cases=cases, action_gap_summary=aggregate_cases(cases), same_action_policy_comparisons=comparisons,
        policy_offset_summary=cross_policy_summary(roster['cases'], comparisons), panel=panel,
        costs=costs, inherited_work=source['inherited_costs'], seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='A frozen first-disagreement panel with fixed continuation policies. Paired suffix SE is Monte Carlo uncertainty; these are not full adaptive-policy or population effects.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True, type=Path)
    args = parser.parse_args(); report = analyze(args.run_dir); output = args.run_dir/'analysis.json'
    output.write_text(json.dumps(report, allow_nan=False, indent=2)+'\n')
    print(json.dumps(dict(complete=report['complete'], primary_complete=report['primary_complete'], checks=report['checks'], output=str(output))))
