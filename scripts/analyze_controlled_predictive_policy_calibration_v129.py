"""Independent source-offset fitting, candidate selection and fresh validation."""
import argparse
from collections import Counter
from itertools import zip_longest
import json
import math
from pathlib import Path
import sys
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_policy_consequences_v126 as old
from scripts import analyze_controlled_predictive_forced_actions_v128 as previous
from acfqp.domains import standard_2048 as ground

LIVES, POLICIES, QUERIES = old.LIVES, old.POLICIES, previous.QUERIES
MODES = ('LEARNED', 'CONSTANT')
METHODS = ('UNCAL_LEARNED', 'CAL_LEARNED', 'UNCAL_CONSTANT', 'CAL_CONSTANT')
FROZEN = old.FROZEN
REPLICAS, MAX_STEPS, BASE = 8, 2000, 129*100000000
read_rows, mean, paired_summary = old.read_rows, old.mean, previous.paired_summary


def root_seed(life, replica):
    return BASE+10000000+life*100000+replica


def suffix_seed(root, replica):
    return BASE+50000000+root*1000+replica


def outer_seed(life, replica):
    return BASE+90000000+life*100000+replica


def calibration_targets(scores, status, policy):
    if status == 'CUTOFF':
        return np.empty(0)
    q = old.QUERIES[policy]
    targets = np.cumsum(np.asarray(scores, dtype=float)[::-1])[::-1]/2048.
    targets += -q['failure_penalty']*(status == 'LOST')+q['goal_bonus']*(status == 'WON')
    return targets[:len(targets)-int(status == 'WON')]


def fixed_candidates(root, query, mode, constants):
    result = []
    for index, policy in enumerate(POLICIES):
        actions = {}
        for action, prediction in root['predictions'][policy].items():
            pred = dict(prediction)
            if mode == 'CONSTANT':
                pred['success_probability'] = 1. if max(pred['afterstate']) >= 11 else constants[policy]
            actions[action] = dict(action=action, policy=policy, policy_index=index,
                value=previous.anchored_value(pred, policy, query), score=pred['score'], afterstate=pred['afterstate'],
                anchor_value=pred['value'], success_probability=pred['success_probability'])
        result.append(min(actions.values(), key=lambda r: (-r['value'], r['action'])))
    return result


def candidate_choice(candidates, offsets):
    result = []
    for candidate in candidates:
        offset = offsets[candidate['policy']] if max(candidate['afterstate']) < 11 else 0.
        result.append(dict(candidate, applied_offset=offset, comparison_value=candidate['value']+offset))
    return min(result, key=lambda r: (-r['comparison_value'], r['action'], r['policy_index']))


def branch_key(row):
    return row['root_id'], row['forced_action'], row['policy'], row['replica']


def full_branch(indexed, valid, root, action, policy):
    keys = [(root, action, policy, r) for r in range(REPLICAS)]
    if not all(k in indexed and valid.get(k, False) and indexed[k]['result']['status'] in ('WON', 'LOST') for k in keys):
        return None
    return [indexed[k] for k in keys]


def utilities(rows, query):
    return np.asarray([old.utility(r['result']['score'], r['result']['status'], query) for r in rows])


def panel_selection(root, query, mode, constants, offsets, indexed, valid):
    proposals = fixed_candidates(root, query, mode, constants)
    uncal = candidate_choice(proposals, {p: 0. for p in POLICIES})
    cal = candidate_choice(proposals, offsets)
    rows = {name: full_branch(indexed, valid, root['root_id'], c['action'], c['policy'])
        for name, c in (('uncal', uncal), ('cal', cal))}
    result = dict(root_id=root['root_id'], life=root['life'], query=query, mode=mode,
        candidates=proposals, uncal=uncal, cal=cal, complete=all(r is not None for r in rows.values()),
        policy_changed=uncal['policy'] != cal['policy'], action_changed=uncal['action'] != cal['action'])
    if result['complete']:
        a, b = utilities(rows['uncal'], query), utilities(rows['cal'], query)
        result.update(replica_values=dict(uncal_utility=a.tolist(), cal_utility=b.tolist(), cal_minus_uncal=(b-a).tolist()),
            paired=dict(uncal_utility=paired_summary(a), cal_utility=paired_summary(b), cal_minus_uncal=paired_summary(b-a)))
    return result


def panel_policy_error(root, action, query, offsets, indexed, valid):
    rows = {p: full_branch(indexed, valid, root['root_id'], action, p) for p in POLICIES}
    result = dict(root_id=root['root_id'], life=root['life'], action=action, query=query,
        complete=all(r is not None for r in rows.values()))
    if not result['complete']:
        return result
    values, predicted = {}, {}
    for p in POLICIES:
        pred = root['predictions'][p][action]; offset = offsets[p] if max(pred['afterstate']) < 11 else 0.
        source_actual = utilities(rows[p], p)
        values[p+'_uncal_anchor_error'] = pred['value']-source_actual
        values[p+'_cal_anchor_error'] = pred['value']+offset-source_actual
        predicted[p] = previous.anchored_value(pred, p, query)
    actual_gap = utilities(rows['risk_goal'], query)-utilities(rows['reward'], query)
    gap = predicted['risk_goal']-predicted['reward']
    terminal = max(root['predictions']['reward'][action]['afterstate']) >= 11
    shifted_gap = gap + (0. if terminal else offsets['risk_goal']-offsets['reward'])
    values.update(actual_policy_gap=actual_gap, uncal_policy_gap_error=gap-actual_gap,
        cal_policy_gap_error=shifted_gap-actual_gap)
    result.update(predicted_uncal_gap=gap, predicted_cal_gap=shifted_gap,
        replica_values={k: v.tolist() for k, v in values.items()}, paired={k: paired_summary(v) for k, v in values.items()})
    return result


def aggregate_panel(cases, rows, group_fields):
    """Average within case before life; never count reused branch aliases twice."""
    groups = []
    labels = sorted({tuple(r[k] for k in group_fields) for r in rows})
    for label in labels:
        for life in LIVES:
            slots = [c for c in cases if c['life'] == life]
            available = [c for c in slots if c['available']]
            item = dict(zip(group_fields, label), life=life, case_slots=len(slots),
                available_cases=len(available), missing_cases=len(slots)-len(available), complete=len(slots) == 8)
            case_arrays = []
            for case in available:
                members = [r for r in rows if r['root_id'] == case['root_id'] and tuple(r[k] for k in group_fields) == label]
                item['complete'] &= bool(members) and all(r['complete'] for r in members)
                if members and all(r['complete'] for r in members):
                    case_arrays.append({k: np.mean([r['replica_values'][k] for r in members], axis=0) for k in members[0]['replica_values']})
            if item['complete'] and case_arrays:
                values = {k: np.mean([r[k] for r in case_arrays], axis=0) for k in case_arrays[0]}
                item.update(paired={k: paired_summary(v) for k, v in values.items()}, replica_values={k: v.tolist() for k, v in values.items()})
            groups.append(item)
    overall = []
    for label in labels:
        members = [r for r in groups if tuple(r[k] for k in group_fields) == label]
        item = dict(zip(group_fields, label), complete=all(r['complete'] and 'paired' in r for r in members))
        if item['complete']:
            values = {k: np.mean([r['replica_values'][k] for r in members], axis=0) for k in members[0]['replica_values']}
            item['paired'] = {k: paired_summary(v) for k, v in values.items()}
        overall.append(item)
    return dict(lifecycles=groups, four_life_means=overall)


def expected_state(source):
    return [dict(source_updates=source['models'][p]['updates'], count_updates=source['counts'][p]['updates'],
        count_successes=source['counts'][p]['successes']) for p in POLICIES]


def inspect_fit(rows, originals, life, episodes=1024):
    checks = dict(fit_roster=True, fit_source_targets=True, fit_counters=True, fit_residuals=True)
    totals = {p: dict(n=0, target_sum=0., anchor_sum=0., residual_sum=0., offset=0., counts=Counter()) for p in POLICIES}
    counts, replay_counts = Counter(), Counter()
    replay_seconds = fit_seconds = retained = 0
    for row, source in zip_longest(rows, originals):
        if row is None or source is None:
            checks['fit_roster'] = False
            continue
        policy = source['policy']; r = source['result']; fit = row['fit']; total = totals[policy]
        n = r['steps']; status = r['status']; targets = calibration_targets(source['scores'], status, policy)
        checks['fit_roster'] &= (row['life'], row['policy'], row['episode_index'], row['source_seed']) == (life, policy, counts[policy], old.train_seed(life, policy, counts[policy]))
        checks['fit_roster'] &= source['life'] == life and source['episode_index'] == counts[policy]
        checks['fit_source_targets'] &= (old.compact_valid(source) and source['seed'] == row['source_seed']
            and fit['status'] == status and fit['observed_afterstates'] == n and fit['n'] == len(targets)
            and fit['analytic_goals'] == int(status == 'WON')
            and fit['censored_afterstates'] == (n if status == 'CUTOFF' else 0)
            and math.isclose(fit['target_sum'], float(targets.sum()), rel_tol=0., abs_tol=1e-8))
        checks['fit_residuals'] &= (all(math.isfinite(fit[k]) for k in ('anchor_sum', 'residual_sum', 'offset_after'))
            and math.isclose(fit['residual_sum'], fit['target_sum']-fit['anchor_sum'], rel_tol=0., abs_tol=1e-8))
        expected = dict(calibration_games=1, calibration_observed_afterstates=n, calibration_samples=len(targets),
            source_tail_predictions=len(targets), source_table_lookups=32*len(targets),
            calibration_analytic_goals=int(status == 'WON'), censored_games=int(status == 'CUTOFF'),
            censored_afterstates=n if status == 'CUTOFF' else 0)
        checks['fit_counters'] &= all(fit['work'].get(k, 0) == v for k, v in expected.items())
        checks['fit_counters'] &= row['replay_counts'] == dict(replay_games=1, replay_swipe_calls=n,
            replay_line_table_lookups=4*n, replay_recorded_spawns=n)
        total['n'] += len(targets)
        for key in ('target_sum', 'anchor_sum', 'residual_sum'):
            total[key] += fit[key]
        total['offset'] = total['residual_sum']/total['n'] if total['n'] else 0.
        checks['fit_residuals'] &= fit['offset_after'] == total['offset']
        total['counts'].update(fit['work']); counts[policy] += 1; retained += n
        replay_counts.update(row['replay_counts']); replay_seconds += row['replay_seconds']; fit_seconds += fit['seconds']
    checks['fit_roster'] &= counts == Counter({p: episodes for p in POLICIES})
    return dict(checks=checks, policies=totals, episodes=dict(counts), replay_counts=dict(replay_counts),
        replay_seconds=replay_seconds, fit_seconds=fit_seconds, retained_transitions=retained)


def original_valid(row, source, root=False):
    r = row['result']; p = row['policy']
    return (old.compact_valid(row) and row['query'] == p and row['method'] == ('ROOT_' if root else 'FROZEN_')+p
        and row['seed'] == (root_seed if root else outer_seed)(row['life'], row['replica'])
        and r['utility'] == old.utility(r['score'], r['status'], p)
        and r['source_updates_before'] == r['source_updates_after'] == source['models'][p]['updates']
        and r['policy_counts'].get('choose_calls') == r['steps']
        and not r['policy_counts'].get('td_updates', 0) and not r['policy_counts'].get('model_spawn_samples', 0))


def control_valid(row, source, offsets):
    if row['method'] in FROZEN:
        return original_valid(row, source)
    r = row['result']; n = r['steps']; state = expected_state(source)
    calibrated = row['method'].startswith('CAL_')
    keys = ('candidate_actions', 'candidate_values', 'comparison_values', 'candidate_goals')
    valid = (old.compact_valid(row) and row['seed'] == outer_seed(row['life'], row['replica'])
        and r['utility'] == old.utility(r['score'], r['status'], row['query'])
        and r['model_state_before'] == r['model_state_after'] == state
        and len(row['policy_indices']) == n and all(len(row[k]) == n for k in keys)
        and r['learning_counts'].get('choose_calls') == r['learning_counts'].get('source_choose_calls') == 2*n
        and all(not r['learning_counts'].get(k, 0) for k in ('source_td_updates', 'success_observation_updates', 'count_array_writes', 'model_spawn_samples')))
    if not valid:
        return False
    additions = 0
    for i in range(n):
        if any(len(row[k][i]) != 2 for k in keys):
            return False
        actions, values, compared, goals = (row[k][i] for k in keys)
        expected = [v+(offsets[p] if calibrated and not goals[j] else 0.) for j, (p, v) in enumerate(zip(POLICIES, values))]
        selected = min(range(2), key=lambda j: (-expected[j], actions[j], j))
        valid &= (all(math.isfinite(v) for v in values+compared) and compared == expected
            and row['policy_indices'][i] == selected and row['actions'][i] == actions[selected])
        additions += 2-sum(goals)
    valid &= r['controller_counts'] == dict(candidate_evaluations=2*n, policy_comparisons=n, offset_additions=additions)
    return bool(valid)


def same_prefix_proposals(left, right):
    if left['seed'] != right['seed'] or left['initial_board'] != right['initial_board']:
        return False
    for i in range(min(len(left['actions']), len(right['actions']))):
        if any(left[k][i] != right[k][i] for k in ('candidate_actions', 'candidate_values', 'candidate_goals')):
            return False
        if left['actions'][i] != right['actions'][i]:
            return True
        if any(left[k][i] != right[k][i] for k in ('scores', 'spawned_cells', 'spawned_ranks')):
            return False
    return len(left['actions']) == len(right['actions'])


def control_summary(indexed, valid):
    methods = {}
    for method in METHODS+FROZEN:
        methods[method] = {}
        for query in QUERIES:
            lives = []
            for life in LIVES:
                keys = [(life, method, method[7:] if method in FROZEN else query, r) for r in range(REPLICAS)]
                rows = [indexed[k] for k in keys if k in indexed]
                complete = len(rows) == REPLICAS and all(valid.get(k, False) for k in keys)
                lives.append(dict(life=life, complete=complete, games=len(rows),
                    means={k: mean(old.utility(r['result']['score'], r['result']['status'], query) if k == 'utility'
                        else r['result'][k] for r in rows) if complete else None for k in old.METRICS},
                    wins=sum(r['result']['status'] == 'WON' for r in rows),
                    statuses=dict(Counter(r['result']['status'] for r in rows))))
            methods[method][query] = dict(lifecycles=lives,
                lifecycle_mean={k: mean(r['means'][k] for r in lives) for k in old.METRICS},
                games=sum(r['games'] for r in lives), wins=sum(r['wins'] for r in lives), complete=all(r['complete'] for r in lives))
    comparisons = {}
    for mode in MODES:
        for right in ('UNCAL_'+mode,)+FROZEN:
            comparisons['CAL_'+mode+'_minus_'+right] = {q: old.old.comparisons(methods['CAL_'+mode][q], methods[right][q]) for q in QUERIES}
    return dict(methods=methods, comparisons=comparisons)


def forced_valid(row, root, source):
    # All retained forced-trace semantics are unchanged; verify the new namespace explicitly.
    checked = dict(row, seed=previous.suffix_seed(row['root_id'], row['replica']))
    return row['seed'] == suffix_seed(row['root_id'], row['replica']) and previous.branch_valid(
        checked, root, source['models'][row['policy']]['updates'])


def prefix_boards(row, counts):
    available = [i for i in (128, 512) if i < row['result']['steps']]
    result = {128: None, 512: None}
    if not available:
        return result, True
    board = tuple(row['initial_board']); valid = True
    for i in range(max(available)+1):
        if i in available:
            result[i] = list(board)
        if i == max(available):
            break
        afterstate, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(row['actions'][i]))
        cell, rank = row['spawned_cells'][i], row['spawned_ranks'][i]
        valid &= changed and score == row['scores'][i] and afterstate[cell] == 0
        board = list(afterstate); board[cell] = rank; board = tuple(board)
        counts['audit_prefix_swipes'] += 1
    return result, bool(valid)


def inspect_panel(roster, prepared, source, directory):
    checks = dict(root_games=True, panel_cases=True, panel_boards=True, panel_roots=True,
        panel_predictions=True, fixed_panel_candidates=True, panel_budget=True)
    counts, cost, start = Counter(), old.new_cost(), perf_counter()
    histories = {}; phases = {r['life']: r for r in prepared}
    for life in LIVES:
        data = phases[life]; rows = list(read_rows(directory/data['trace']))
        keys = [(r['policy'], r['replica']) for r in rows]
        checks['root_games'] &= len(keys) == len(set(keys)) == 4 and set(keys) == {(p, r) for p in POLICIES for r in range(2)}
        for row in rows:
            checks['root_games'] &= original_valid(row, source[life], root=True)
            boards, valid = prefix_boards(row, counts); checks['panel_boards'] &= valid
            histories[life, row['policy'], row['replica']] = row, boards
            old.add_cost(cost, row)
    expected = [(l, p, r, i) for l in LIVES for p in POLICIES for r in range(2) for i in (128, 512)]
    checks['panel_cases'] &= [(c['life'], c['policy'], c['replica'], c['index']) for c in roster['cases']] == expected
    checks['panel_cases'] &= [c['case_id'] for c in roster['cases']] == list(range(32))
    roots = {r['root_id']: r for r in roster['roots']}; ids = {}; logical = 0
    for case in roster['cases']:
        row, boards = histories[case['life'], case['policy'], case['replica']]
        board = boards[case['index']]; ready = board is not None
        checks['panel_cases'] &= case['source_eval_id'] == row['eval_id'] and case['available'] == ready
        checks['panel_boards'] &= case['board'] == board
        if not ready:
            checks['panel_roots'] &= case['root_id'] is None
            continue
        key = case['life'], tuple(board)
        if key not in ids:
            ids[key] = len(ids)
        checks['panel_roots'] &= case['root_id'] == ids[key] and case['root_id'] in roots
        root = roots[case['root_id']]
        checks['panel_boards'] &= root['board'] == board and root['life'] == case['life']
        logical += len(root['actions'])*len(POLICIES)*REPLICAS
    checks['panel_roots'] &= [r['root_id'] for r in roster['roots']] == list(range(len(ids)))
    for root in roster['roots']:
        constants = {p: source[root['life']]['counts'][p]['constant'] for p in POLICIES}
        checks['panel_predictions'] &= set(root['predictions']) == set(POLICIES)
        legal = set(root['predictions']['reward'])
        checks['panel_predictions'] &= set(root['predictions']['risk_goal']) == legal
        for action in legal:
            a, b = (root['predictions'][p][action] for p in POLICIES)
            checks['panel_predictions'] &= (a['score'] == b['score'] and a['afterstate'] == b['afterstate']
                and all(math.isfinite(p['value']) and 0 <= p['success_probability'] <= 1 for p in (a, b)))
        actions = set()
        for query in QUERIES:
            for mode in MODES:
                predicted = fixed_candidates(root, query, mode, constants)
                saved = root['candidates'][query][mode]
                checks['fixed_panel_candidates'] &= len(saved) == 2
                for actual, record in zip(predicted, saved):
                    checks['fixed_panel_candidates'] &= all(actual[k] == record[k] for k in ('action', 'policy_index', 'value', 'anchor_value', 'success_probability', 'score', 'afterstate'))
                    checks['fixed_panel_candidates'] &= record['comparison_value'] == record['value'] and record['applied_offset'] == 0.
                    actions.add(actual['action'])
        checks['fixed_panel_candidates'] &= root['actions'] == sorted(actions)
    physical = sum(len(r['actions'])*len(POLICIES)*REPLICAS for r in roster['roots'])
    checks['panel_budget'] &= roster['physical_attempts'] == physical <= 2048 and roster['logical_attempts'] == logical
    return dict(checks=checks, root_acquisition=cost, audit_counts=dict(counts), audit_seconds=perf_counter()-start,
        physical_attempts=physical, logical_attempts=logical)


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    run = json.loads((directory/'run.json').read_text()); source = json.loads((directory/'source_capsule.json').read_text())
    roster = json.loads((directory/'roster.json').read_text()); calibration = json.loads((directory/'calibration.json').read_text())
    sources = {r['life']: r for r in source['snapshots']}; shifts = {r['life']: r['offsets'] for r in calibration['lifecycles']}
    settings = dict(lifecycles=list(LIVES), policies={p: old.QUERIES[p] for p in POLICIES}, queries=QUERIES,
        training_games=1024, replicas=8, root_replicas=2, suffix_replicas=8, root_indices=[128, 512],
        methods=list(METHODS), max_steps=MAX_STEPS, workers=4, p_four=.1, version_base=BASE)
    checks = dict(frozen_settings=run['settings'] == settings,
        source_roster=source['schema'] == 'acfqp.policy_calibration.v129.source' and len(source['snapshots']) == 4
            and set(sources) == set(LIVES) and all(set(s) == {'life', 'rule', 'models', 'counts', 'training_trace'} for s in source['snapshots']),
        lifecycle_rosters=all(len(run[k]) == 4 and {r['life'] for r in run[k]} == set(LIVES)
            for k in ('fit_lifecycles', 'panel_lifecycles', 'lifecycles')),
        inherited_costs=run['inherited_costs'] == source['inherited_costs'], source_origins=True,
        frozen_calibration=calibration['schema'] == 'acfqp.policy_calibration.v129.frozen' and len(shifts) == 4 and set(shifts) == set(LIVES),
        fit_statistics=True, immutable_models=True, model_loads=True, source_fit_budget=True,
        forced_roster=True, forced_traces=True, control_roster=True, control_traces=True,
        unchanged_source_proposals=True, full_control_terminal=True, full_panel_terminal=True)
    costs = dict(fitting_counts=Counter(), fitting_seconds=0., replay_counts=Counter(), replay_seconds=0.,
        retained_training_transitions=0, source_load_counts=Counter(), source_load_seconds=0.,
        count_load_counts=Counter(), count_load_seconds=0., source_setup_counts=Counter(), source_setup_seconds=0.,
        count_setup_counts=Counter(), count_setup_seconds=0., calibrator_setup_counts=Counter(), calibrator_setup_seconds=0.,
        forced=old.new_cost(), control=old.new_cost(), controller_counts=Counter(),
        peak_resident_weight_bytes_per_life=0)
    fits = []
    for phase in ('fit_lifecycles', 'panel_lifecycles', 'lifecycles'):
        for data in run[phase]:
            snapshot = sources[data['life']]; state = expected_state(snapshot)
            checks['immutable_models'] &= data['model_state_before'] == data['model_state_after'] == state
            checks['model_loads'] &= set(data['loads']) == set(POLICIES)
            for p in POLICIES:
                load = data['loads'][p]; scalar, counts = snapshot['models'][p], snapshot['counts'][p]
                checks['model_loads'] &= (load['source_updates'] == scalar['updates']
                    and load['count_updates'] == counts['updates'] and load['count_successes'] == counts['successes']
                    and load['source_load_counts'].get('checkpoint_loads') == 1
                    and load['source_load_counts'].get('checkpoint_loaded_parameters') == scalar['nonzero_weights']
                    and load['count_load_counts'].get('checkpoint_loads') == 1
                    and load['count_load_counts'].get('checkpoint_loaded_count_entries') == 2*load['count_load_counts'].get('checkpoint_loaded_addresses', -1))
                for key in ('source_load', 'count_load', 'source_setup', 'count_setup'):
                    costs[key+'_counts'].update(load[key+'_counts']); costs[key+'_seconds'] += load[key+'_seconds']
    for data in run['fit_lifecycles']:
        life = data['life']; snapshot = sources[life]
        checks['source_origins'] &= snapshot['training_trace'] == str(ROOT/'reports/controlled_predictive_policy_consequences_v126'/f'life_{life}'/'training.jsonl.gz')
        for p in POLICIES:
            checks['source_origins'] &= (snapshot['models'][p]['path'] == str(ROOT/'reports/controlled_predictive_ntuple_learning_v120'/f'life_{life}'/p/'checkpoint_4096.npz')
                and snapshot['counts'][p]['path'] == str(ROOT/'reports/controlled_predictive_anchored_success_v127'/f'life_{life}'/p/'checkpoint_1024.npz'))
        found = inspect_fit(read_rows(directory/data['trace']), read_rows(Path(snapshot['training_trace'])), life)
        for k, v in found['checks'].items():
            checks[k] = checks.get(k, True) and v
        checks['fit_statistics'] &= (data['episodes'] == found['episodes'] and data['replay_counts'] == found['replay_counts'] and data['replay_seconds'] == found['replay_seconds'])
        for p in POLICIES:
            actual, saved = found['policies'][p], data['policies'][p]
            checks['fit_statistics'] &= all(saved[k] == actual[k] for k in actual)
            checks['frozen_calibration'] &= shifts[life][p] == actual['offset']
            costs['fitting_counts'].update(actual['counts']); costs['calibrator_setup_counts'].update(saved['setup_counts'])
            costs['calibrator_setup_seconds'] += saved['setup_seconds']
        costs['fitting_seconds'] += found['fit_seconds']; costs['replay_seconds'] += found['replay_seconds']
        costs['replay_counts'].update(found['replay_counts']); costs['retained_training_transitions'] += found['retained_transitions']
        fits.append(dict(life=life, **found))
    checks['source_fit_budget'] &= costs['retained_training_transitions'] == 6635452 and costs['fitting_counts']['calibration_games'] == 8192
    panel = inspect_panel(roster, run['panel_lifecycles'], sources, directory); checks.update(panel['checks'])
    costs.update(root_acquisition=panel['root_acquisition'], analysis_counts=panel['audit_counts'], analysis_prefix_seconds=panel['audit_seconds'])
    costs['panel_prediction_counts'] = Counter()
    for data in run['panel_lifecycles']:
        costs['panel_prediction_counts'].update(data['prediction_counts'])
        checks['immutable_models'] &= all(not data['prediction_counts'].get(k, 0) for k in ('source_td_updates', 'success_observation_updates', 'count_array_writes', 'model_spawn_samples'))
    roots = {r['root_id']: r for r in roster['roots']}; forced, forced_validity, outer, outer_validity = {}, {}, {}, {}
    for data in run['lifecycles']:
        life = data['life']; snapshot = sources[life]
        rows = list(read_rows(directory/data['forced_trace'])); keys = [branch_key(r) for r in rows]
        expected = {(r['root_id'], a, p, i) for r in roster['roots'] if r['life'] == life for a in r['actions'] for p in POLICIES for i in range(8)}
        checks['forced_roster'] &= len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
        for row in rows:
            ready = forced_valid(row, roots[row['root_id']], snapshot); key = branch_key(row)
            checks['forced_traces'] &= ready; checks['full_panel_terminal'] &= row['result']['status'] in ('WON', 'LOST')
            forced[key], forced_validity[key] = row, ready; old.add_cost(costs['forced'], row)
        rows = list(read_rows(directory/data['control_trace']))
        keys = [(r['life'], r['method'], r['query'], r['replica']) for r in rows]
        expected = {(life, m, q, i) for m in METHODS for q in QUERIES for i in range(8)}
        expected |= {(life, m, m[7:], i) for m in FROZEN for i in range(8)}
        checks['control_roster'] &= len(keys) == len(set(keys)) == len(expected) and set(keys) == expected
        for row, key in zip(rows, keys):
            ready = control_valid(row, snapshot, shifts[life]); terminal = row['result']['status'] in ('WON', 'LOST')
            checks['control_traces'] &= ready; checks['full_control_terminal'] &= terminal
            outer[key], outer_validity[key] = row, ready and terminal
            old.add_cost(costs['control'], row); costs['controller_counts'].update(row['result'].get('controller_counts', {}))
        for q in QUERIES:
            for mode in MODES:
                for rep in range(8):
                    a, b = (life, 'UNCAL_'+mode, q, rep), (life, 'CAL_'+mode, q, rep)
                    checks['unchanged_source_proposals'] &= a in outer and b in outer and same_prefix_proposals(outer[a], outer[b])
        costs['peak_resident_weight_bytes_per_life'] = max(costs['peak_resident_weight_bytes_per_life'], data['peak_weight_bytes'])
    costs['physical_forced_attempts'] = costs['forced']['games']; costs['logical_forced_attempts'] = panel['logical_attempts']
    costs['physical_control_games'] = costs['control']['games']; costs['logical_control_rows'] = len(outer)+64
    costs['actual_new_environment_transitions'] = sum(costs[k]['environment_counts'].get('sampled_transitions', 0) for k in ('root_acquisition', 'forced', 'control'))
    costs['model_spawn_samples'] = sum(costs[k][field].get('model_spawn_samples', 0) for k in ('root_acquisition', 'forced', 'control') for field in old.FIELDS)
    costs['fresh_training_environment_transitions'] = 0
    checks['physical_budgets'] = costs['physical_forced_attempts'] == panel['physical_attempts'] and costs['physical_control_games'] == 320 and costs['root_acquisition']['games'] == 16
    selections, errors = [], []
    for root in roster['roots']:
        constants = {p: sources[root['life']]['counts'][p]['constant'] for p in POLICIES}
        for q in QUERIES:
            for mode in MODES:
                selections.append(panel_selection(root, q, mode, constants, shifts[root['life']], forced, forced_validity))
            for action in root['actions']:
                errors.append(panel_policy_error(root, action, q, shifts[root['life']], forced, forced_validity))
    complete = run['status'] == 'complete' and all(v for k, v in checks.items() if k not in ('full_panel_terminal', 'full_control_terminal'))
    return dict(schema='acfqp.policy_calibration.v129.analysis', complete=bool(complete),
        primary_complete=bool(complete and checks['full_panel_terminal'] and checks['full_control_terminal']),
        checks={k: bool(v) for k, v in checks.items()}, calibration=fits, offsets=calibration['lifecycles'],
        control=control_summary(outer, outer_validity), panel_selections=selections, panel_policy_errors=errors,
        panel_selection_summary=aggregate_panel(roster['cases'], selections, ('query', 'mode')),
        panel_error_summary=aggregate_panel(roster['cases'], errors, ('query',)),
        panel_coverage=dict(case_slots=len(roster['cases']), available_cases=sum(c['available'] for c in roster['cases']), unique_roots=len(roster['roots'])),
        costs=costs, inherited_work=source['inherited_costs'], seconds=run['seconds'], analysis_seconds=perf_counter()-started,
        scope='Offsets fit source training only; fresh forced branches test comparability, and separate full games test repeated control. Within-policy success-gap error is unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--run-dir', required=True, type=Path)
    args = parser.parse_args(); report = analyze(args.run_dir); output = args.run_dir/'analysis.json'
    output.write_text(json.dumps(report, allow_nan=False, indent=2)+'\n')
    print(json.dumps(dict(complete=report['complete'], primary_complete=report['primary_complete'], checks=report['checks'], output=str(output))))
