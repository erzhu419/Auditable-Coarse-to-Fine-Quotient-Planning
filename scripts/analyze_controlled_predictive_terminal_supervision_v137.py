"""Reconcile retained-episode TD and terminal supervision without resampling."""
import argparse
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_bellman_consequences_v136 as previous

old, planning = previous.old, previous.planning
LIVES, REPRESENTATIONS, TEACHERS = tuple(range(4)), ('SINGLE', 'CAPACITY'), ('risk1', 'risk8')
METHODS, LEARNERS = ('TEACHER', 'INITIAL_H2', 'TD', 'TERMINAL'), ('TD', 'TERMINAL')
PHASES = ('INITIAL_H2', 'TD', 'TERMINAL')
REPLICAS, MAX_STEPS, BASE = 16, 2000, 137*100000000
QUERIES = {key: previous.QUERIES[key] for key in TEACHERS}
UPDATE_FIELDS = ('pre_raw_reward', 'pre_reward', 'pre_success', 'target_reward',
    'target_success', 'raw_reward_target', 'reward_error', 'success_error')
mean = previous.mean
diagnostic_targets = previous.diagnostic_targets
component_errors = previous.component_errors


def outer_seed(life, replica):
    return BASE+90000000+life*100000+replica


def full_game_comparison(indexed, valid):
    cells = []
    for representation in REPRESENTATIONS:
        for teacher in TEACHERS:
            methods, comparisons = {}, {}
            for method in METHODS:
                lives = []
                for life in LIVES:
                    keys = [(life, representation, teacher, method, replica) for replica in range(REPLICAS)]
                    rows = [indexed[key] for key in keys if key in indexed]
                    complete = all(key in indexed and valid.get(key, False)
                        and indexed[key]['result']['status'] in ('WON', 'LOST') for key in keys)
                    lives.append(dict(life=life, complete=complete, games=len(rows),
                        statuses=dict(Counter(row['result']['status'] for row in rows)),
                        wins=sum(row['result']['status'] == 'WON' for row in rows),
                        means={name: mean(row['result'][name] for row in rows) if complete else None
                            for name in ('utility', 'score', 'steps')}))
                methods[method] = dict(lifecycles=lives, complete=all(row['complete'] for row in lives),
                    means={name: mean(row['means'][name] for row in lives) for name in ('utility', 'score', 'steps')})
            for method, baseline in (('TD', 'TEACHER'), ('TERMINAL', 'TEACHER'), ('TERMINAL', 'TD')):
                lives = []
                for life in LIVES:
                    complete = methods[method]['lifecycles'][life]['complete'] and methods[baseline]['lifecycles'][life]['complete']
                    item = dict(life=life, complete=complete)
                    if complete:
                        deltas = [indexed[(life, representation, teacher, method, replica)]['result']['utility']-
                            indexed[(life, representation, teacher, baseline, replica)]['result']['utility']
                            for replica in range(REPLICAS)]
                        item.update(mean=mean(deltas), replica_deltas=deltas)
                    lives.append(item)
                comparisons[method+'_minus_'+baseline] = dict(lifecycles=lives,
                    complete=all(row['complete'] for row in lives), mean=mean(row.get('mean') for row in lives),
                    positive=sum(row.get('mean', 0) > 0 for row in lives),
                    negative=sum(row.get('mean', 0) < 0 for row in lives), zero=sum(row.get('mean') == 0 for row in lives))
            cells.append(dict(representation=representation, teacher_query=teacher, methods=methods, comparisons=comparisons))
    return dict(cells=cells, complete=all(method['complete'] for cell in cells for method in cell['methods'].values()))


def calibration_summary(games):
    metrics = ('reward_mse', 'success_brier', 'source_query_mse', 'reward_bias', 'success_bias', 'source_query_bias')
    cells = []
    for representation in REPRESENTATIONS:
        for teacher in TEACHERS:
            lives = []
            for life in LIVES:
                selected = [row for row in games if (row['representation'], row['teacher_query'], row['life']) == (representation, teacher, life)]
                complete = (len(selected) == REPLICAS and {row['replica'] for row in selected} == set(range(REPLICAS))
                    and all(row[phase]['complete'] for row in selected for phase in PHASES))
                phases = {phase: {metric: mean(row[phase][metric] for row in selected) if complete else None
                    for metric in metrics} for phase in PHASES}
                changes = {method+'_minus_'+baseline: {metric: phases[method][metric]-phases[baseline][metric] if complete else None
                    for metric in metrics} for method, baseline in (('TD','INITIAL_H2'), ('TERMINAL','INITIAL_H2'), ('TERMINAL','TD'))}
                lives.append(dict(life=life, complete=complete, games=len(selected), phases=phases,
                    eligible_afterstates=sum(row['INITIAL_H2']['eligible_afterstates'] for row in selected), changes=changes))
            cells.append(dict(representation=representation, teacher_query=teacher,
                complete=all(row['complete'] for row in lives), lifecycles=lives,
                means={phase: {metric: mean(row['phases'][phase][metric] for row in lives) for metric in metrics} for phase in PHASES},
                changes={comparison: {metric: mean(row['changes'][comparison][metric] for row in lives) for metric in metrics}
                    for comparison in ('TD_minus_INITIAL_H2','TERMINAL_minus_INITIAL_H2','TERMINAL_minus_TD')}))
    return dict(cells=cells, complete=all(cell['complete'] for cell in cells),
        weighting='eligible afterstates within each game, then equally weighted games and four histories')


def update_valid(values, target_reward, target_success, intercept):
    if set(values) != set(UPDATE_FIELDS): return False
    update = values
    return (all(math.isfinite(value) for value in values.values())
        and update['target_reward'] == target_reward and update['target_success'] == target_success
        and update['raw_reward_target'] == target_reward-intercept
        and update['pre_reward'] == update['pre_raw_reward']+intercept
        and update['reward_error'] == update['raw_reward_target']-update['pre_raw_reward']
        and update['success_error'] == target_success-update['pre_success']
        and 0 <= target_success <= 1 and 0 <= update['pre_success'] <= 1)


def replay_checks(row, source, method, intercept, representation, updates_before):
    """Targets are independently derived from source scores and terminal labels."""
    steps, won = len(source['scores']), source['status'] == 'WON'
    count = steps-int(won)
    checks = dict(replay_roster=(row['method'] == method and source['status'] in ('WON','LOST')
        and all(row[key] == source[key] for key in ('episode','seed','status')) and row['steps'] == steps),
        matched_updates=(row['eligible_updates'] == count and row['updates_before'] == updates_before
            and row['updates_after'] == updates_before+count and len(row['updates']) == count),
        replay_targets=True, exact_td_reproduction=True, replay_model_counts=True, replay_accounting=True)
    predictions, recorded = row['predictions'], row['updates']
    if not checks['matched_updates']: checks['replay_targets'] = False; return checks
    if method == 'TERMINAL':
        targets = diagnostic_targets(source['scores'],source['status'])
        checks['replay_targets'] &= predictions == []
        checks['replay_targets'] &= all(update_valid(values,target['reward'],target['success'],intercept)
            for values,target in zip(recorded,targets))
        checks['exact_td_reproduction'] &= row['td_source_comparison'] is None
    else:
        checks['replay_targets'] &= len(predictions) == steps and all(len(p) == 2 and math.isfinite(p[0])
            and math.isfinite(p[1]) and 0 <= p[1] <= 1 for p in predictions)
        if len(predictions) == steps:
            targets = [(source['scores'][i]/2048.+predictions[i][0],predictions[i][1]) for i in range(1,steps)]
            if not won: targets.append((0.,0.))
            checks['replay_targets'] &= all(update_valid(values,*target,intercept) for values,target in zip(recorded,targets))
            expected_predictions = [[p['reward'],p['success']] for p in source['next_components']]
            expected_updates = [{key:u[key] for key in UPDATE_FIELDS} for u in source['joint_updates'] if u is not None]
            if source['terminal_update'] is not None: expected_updates.append({key:source['terminal_update'][key] for key in UPDATE_FIELDS})
            comparison = row['td_source_comparison']
            checks['exact_td_reproduction'] &= (predictions == expected_predictions and recorded == expected_updates
                and comparison['prediction_values_compared'] == comparison['prediction_values_matched'] == 2*steps
                and comparison['update_values_compared'] == comparison['update_values_matched'] == len(UPDATE_FIELDS)*count
                and comparison['mismatches'] == 0 and comparison.get('first_mismatch') is None)
            if won: checks['replay_targets'] &= predictions[-1] == [0.,1.]
    counts = row['model_counts']
    checks['replay_model_counts'] &= (previous.component_counts_valid(counts,representation,count)
        and counts.get('choose_calls',0) == 0 and counts.get('value_calls',0) == (steps if method == 'TD' else 0)
        and counts.get('joint_predictions',0) == count*(2 if method == 'TD' else 1))
    work, targets = row['replay_counts'], row['target_counts']
    checks['replay_accounting'] &= (work.get('replay_swipes') == work.get('replayed_transitions') == work.get('replayed_spawn_events') == steps
        and work.get('newly_sampled_environment_transitions',0) == work.get('newly_sampled_model_transitions',0) == 0
        and targets.get('eligible_targets') == count)
    if method == 'TD':
        checks['replay_accounting'] &= targets.get('reward_target_additions') == steps-1 and targets.get('terminal_boundary_targets',0) == int(not won)
    else:
        checks['replay_accounting'] &= targets.get('suffix_score_additions') == steps and targets.get('terminal_labels') == count
    return {key: bool(value) for key,value in checks.items()}


def control_valid(row, source, updates):
    # The V136 numerical/readout checks remain valid; only seed and method names change.
    adapted = dict(row, seed=previous.outer_seed(row['life'],row['replica']))
    if row['method'] in LEARNERS: adapted['method'] = 'LEARNED_H2'
    checks = previous.control_valid(adapted,source,updates)
    checks['control_trace'] &= row['seed'] == outer_seed(row['life'],row['replica']) and row['query'] == row['teacher_query']
    return checks


def inspect_diagnostic(row, updates):
    diagnostic = row['diagnostic']; n = row['result']['steps']-int(row['result']['status'] == 'WON')
    representation, teacher = row['representation'], row['teacher_query']
    checks = dict(diagnostic_roster=all(set(diagnostic[key]) == set(PHASES) for key in ('predictions','counts','before','after')),
        diagnostic_frozen=True, diagnostic_predictions=True, diagnostic_counters=True)
    item = {key: row[key] for key in ('life','representation','teacher_query','replica')}
    targets = diagnostic_targets(row['scores'],row['result']['status'])
    for method in PHASES:
        predictions, counts = diagnostic['predictions'][method], diagnostic['counts'][method]
        expected = previous.component_state(representation,0 if method == 'INITIAL_H2' else updates[method])
        checks['diagnostic_frozen'] &= diagnostic['before'][method] == diagnostic['after'][method] == expected
        checks['diagnostic_predictions'] &= len(predictions) == n and all(math.isfinite(p['reward'])
            and math.isfinite(p['success']) and 0 <= p['success'] <= 1 for p in predictions)
        checks['diagnostic_counters'] &= (counts.get('value_calls') == counts.get('joint_predictions') == n
            and counts.get('choose_calls',0) == 0 and previous.component_counts_valid(counts,representation,0))
        item[method] = component_errors(predictions,targets,teacher)
    return checks,item


def replay_cost():
    return dict(episodes=0, transitions=0, updates=0, seconds=0., statuses=Counter(),
        model_counts=Counter(), replay_counts=Counter(), target_counts=Counter(), td_source_comparison=Counter())


def inspect_replays(source_rows, replay_rows, reference, life, representation, teacher, source):
    checks = dict(source_complete_prefix=True, source_manifest=True, replay_rosters=True,
        matched_complete_data=True, no_new_training_samples=True)
    costs = {method: replay_cost() for method in LEARNERS}
    counts = dict(episodes=0,transitions=0,eligible_episodes=0,eligible_transitions=0,
        eligible_updates=0,excluded_episodes=0,excluded_transitions=0)
    excluded, statuses = [], Counter()
    updates, last_source_updates = 0, 0
    streams = {method: iter(replay_rows[method]) for method in LEARNERS}
    intercept = previous.reward_intercept(source,teacher)
    for record in source_rows:
        n = len(record['actions']); status = record['status']
        checks['source_complete_prefix'] &= (record['episode'] == counts['episodes'] and record['start_step'] == 0
            and record['pending_before'] is None and record['updates_before'] == last_source_updates
            and record['seed'] == previous.train_seed(life,representation,teacher,record['episode'])
            and (record['life'],record['representation'],record['teacher_query']) == (life,representation,teacher))
        last_source_updates = record['updates_after']; counts['episodes'] += 1; counts['transitions'] += n
        statuses[status] += 1
        checks['source_complete_prefix'] &= record['cumulative_transitions'] == counts['transitions']
        if status not in ('WON','LOST'):
            checks['source_complete_prefix'] &= status == 'ACTIVE' and not excluded
            excluded.append({key:record[key] for key in ('episode','seed','status','start_step','end_step')})
            counts['excluded_episodes'] += 1; counts['excluded_transitions'] += n
            continue
        checks['source_complete_prefix'] &= not excluded and record['pending_after'] is None
        count = n-int(status == 'WON')
        counts['eligible_episodes'] += 1; counts['eligible_transitions'] += n; counts['eligible_updates'] += count
        for method in LEARNERS:
            row = next(streams[method],None)
            if row is None:
                checks['replay_rosters'] = False; continue
            checks['replay_rosters'] &= (row['life'],row['representation'],row['teacher_query']) == (life,representation,teacher)
            for name,value in replay_checks(row,record,method,intercept,representation,updates).items():
                checks[name] = checks.get(name,True) and value
            cost = costs[method]
            cost['episodes'] += 1; cost['transitions'] += n; cost['updates'] += row['eligible_updates']
            cost['seconds'] += row['seconds']; cost['statuses'][status] += 1
            for name in ('model_counts','replay_counts','target_counts'): cost[name].update(row[name])
            if row['td_source_comparison'] is not None:
                cost['td_source_comparison'].update({key:value for key,value in row['td_source_comparison'].items()
                    if key != 'first_mismatch'})
        updates += count
    checks['replay_rosters'] &= all(next(stream,None) is None for stream in streams.values())
    checks['source_manifest'] &= (counts['transitions'] == reference['source_transitions'] == 524288
        and statuses == reference['source_statuses'] and last_source_updates == reference['source_updates'])
    checks['matched_complete_data'] &= all(costs[method]['updates'] == updates == counts['eligible_updates']
        and costs[method]['episodes'] == counts['eligible_episodes']
        and costs[method]['transitions'] == counts['eligible_transitions'] for method in LEARNERS)
    checks['no_new_training_samples'] &= all(cost['replay_counts'].get('newly_sampled_environment_transitions',0) == 0
        and cost['replay_counts'].get('newly_sampled_model_transitions',0) == 0
        and not any(amount for key,amount in cost['model_counts'].items() if key.endswith('model_spawn_samples'))
        for cost in costs.values())
    return dict(checks={key:bool(value) for key,value in checks.items()},costs=costs,
        source_counts=counts,source_statuses=statuses,excluded=excluded,updates=updates)


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    read = lambda name: json.loads((directory/name).read_text())
    run,capsule,frozen = (read(name) for name in ('run.json','source_capsule.json','frozen_training.json'))
    sources = {source['life']:source for source in capsule['snapshots']}
    settings = dict(lifecycles=list(LIVES),representations=list(REPRESENTATIONS),teacher_queries=list(TEACHERS),
        queries=QUERIES,arms=list(LEARNERS),methods=list(METHODS),replicas=REPLICAS,max_steps=MAX_STEPS,
        workers=4,alpha=.0025,passes=1,episode_order='retained_chronological',eligible_statuses=['WON','LOST'],
        initial_success=.5,p_four=.1,planner_spawn_law='frozen_identified_distribution',version_base=BASE,
        physical_control_games=768,logical_control_rows=1024)
    checks = dict(frozen_settings=run['settings'] == settings,
        source_roster=len(sources) == len(capsule['snapshots']) == 4 and set(sources) == set(LIVES),
        stage_rosters=all(len(run[key]) == 4 and {row['life'] for row in run[key]} == set(LIVES)
            for key in ('lifecycles','eval_lifecycles')),
        inherited_costs=run['inherited_costs'] == capsule['inherited_costs'],
        all_training_frozen_before_evaluation=frozen['status'] == 'frozen' and frozen['eval_lifecycles'] == []
            and all(frozen[key] == run[key] for key in ('settings','lifecycles','inherited_costs')),
        learner_roster=True,teacher_immutable=True,source_references=True,source_accounting=True,
        model_loads=True,initialization=True,checkpoint_states=True,checkpoint_metadata=True,saved_work=True,
        control_roster=True,physical_logical_rosters=True)
    costs = dict(training={method:replay_cost() for method in LEARNERS},source_counts=Counter(),
        source_statuses=Counter(),control=old.new_cost(),control_by_cell={},zero_equivalence_counts=Counter(),
        diagnostic_counts={method:Counter() for method in PHASES},model_accounting=[])
    learners,trained,updates = [],{},{}
    for lifecycle in run['lifecycles']:
        life = lifecycle['life']; source = sources[life]
        checks['learner_roster'] &= set(lifecycle['representations']) == set(REPRESENTATIONS)
        for rep,teachers in lifecycle['representations'].items():
            checks['learner_roster'] &= set(teachers) == set(TEACHERS)
            for teacher,data in teachers.items():
                key = life,rep,teacher; trained[key] = data
                reference = source['training_sources'][rep][teacher]
                checks['source_references'] &= data['source_ref'] == reference
                checks['learner_roster'] &= set(data['methods']) == set(LEARNERS)
                inspected = inspect_replays(old.read_rows(Path(reference['training_trace'])),
                    {method:old.read_rows(directory/data['methods'][method]['training_trace']) for method in LEARNERS},
                    reference,life,rep,teacher,source)
                for name,value in inspected['checks'].items(): checks[name] = checks.get(name,True) and value
                updates[key] = {method:inspected['updates'] for method in LEARNERS}
                checks['source_accounting'] &= data['source_counts'] == inspected['source_counts'] and data['excluded'] == inspected['excluded']
                parent_state = planning.previous.model_state(source,teacher,'PARENT',0)
                checks['teacher_immutable'] &= (data['parent_before'] == data['parent_after'] == parent_state
                    and data['teacher_before'] == data['teacher_after'] == planning.expected_model_state(source,teacher,rep)
                    and not any(data['teacher_counts'].values()))
                checks['model_loads'] &= previous.teacher_loads_valid(data['loads'],source,rep,teacher)
                head_size = planning.previous.parameter_count(rep)
                for method,arm in data['methods'].items():
                    init = arm['initialization']; checkpoint = arm['checkpoint']; count = inspected['updates']
                    checks['initialization'] &= (init['state'] == previous.component_state(rep,0,False) and init['counts'] == {}
                        and init['setup_counts'].get('allocated_weight_parameters') == 2*head_size
                        and init['setup_counts'].get('source_parameters_copied') == head_size
                        and init['setup_counts'].get('source_weight_bytes_copied') == 8*head_size)
                    checks['checkpoint_states'] &= (arm['final_state'] == previous.component_state(rep,count)
                        and checkpoint['updates'] == checkpoint['metadata']['updates'] == count
                        and checkpoint['metadata']['parameter_count'] == 2*head_size)
                    metadata = read(checkpoint['model_ref']+'.components.json')
                    checks['checkpoint_metadata'] &= (metadata['schema'] == 'acfqp.bellman_consequences.v136'
                        and metadata['representation'] == rep and metadata['teacher_query'] == QUERIES[teacher]
                        and metadata['teacher_updates'] == source['leaves'][teacher][rep]['updates']
                        and metadata['prior_success'] == .5 and metadata['alpha'] == .0025
                        and metadata['reward_intercept'] == previous.reward_intercept(source,teacher)
                        and metadata['parameter_count'] == 2*head_size and metadata['updates'] == count and metadata['frozen'])
                    checks['saved_work'] &= (checkpoint['save_counts'].get('checkpoint_saves') == 1
                        and checkpoint['save_counts'].get('checkpoint_scanned_parameters') == 2*head_size
                        and Counter(arm['final_counts']) == inspected['costs'][method]['model_counts']+Counter(checkpoint['save_counts'])
                        and arm['final_counts'] == metadata['counts'])
                    for name in ('episodes','transitions','updates','seconds'): costs['training'][method][name] += inspected['costs'][method][name]
                    for name in ('statuses','model_counts','replay_counts','target_counts','td_source_comparison'):
                        costs['training'][method][name].update(inspected['costs'][method][name])
                costs['source_counts'].update(inspected['source_counts']); costs['source_statuses'].update(inspected['source_statuses'])
                costs['model_accounting'].append(dict(phase='training',life=life,representation=rep,teacher_query=teacher,
                    loads=data['loads'],methods={method:{name:arm[name] for name in ('initialization','checkpoint','final_counts')}
                        for method,arm in data['methods'].items()}))
                learners.append(dict(life=life,representation=rep,teacher_query=teacher,**inspected))
    indexed,valid,diagnostics = {},{},[]
    for lifecycle in run['eval_lifecycles']:
        life = lifecycle['life']; source = sources[life]; seen,teacher_totals = set(),{}
        for row in old.read_rows(directory/lifecycle['control_trace']):
            rep,teacher,method,replica = (row[name] for name in ('representation','teacher_query','method','replica'))
            key = life,rep,teacher,method,replica
            checks['control_roster'] &= key not in seen and row['life'] == life; seen.add(key)
            row_checks = control_valid(row,source,0 if method == 'TEACHER' else updates[(life,rep,teacher)][method])
            for name,value in row_checks.items(): checks[name] = checks.get(name,True) and value
            indexed[key],valid[key] = dict(result=row['result']),all(row_checks.values())
            old.add_cost(costs['control'],row)
            cell = f'{rep}:{teacher}:{method}'; costs['control_by_cell'].setdefault(cell,old.new_cost())
            old.add_cost(costs['control_by_cell'][cell],row)
            if method == 'TEACHER':
                teacher_totals.setdefault((rep,teacher),Counter()).update(row['result']['policy_counts'])
                costs['zero_equivalence_counts'].update(row['zero_equivalence']['counts'])
                diagnostic_checks,diagnostic = inspect_diagnostic(row,updates[(life,rep,teacher)])
                for name,value in diagnostic_checks.items(): checks[name] = checks.get(name,True) and value
                diagnostics.append(diagnostic)
                for name,counts in row['diagnostic']['counts'].items(): costs['diagnostic_counts'][name].update(counts)
                alias = life,rep,teacher,'INITIAL_H2',replica
                indexed[alias],valid[alias] = indexed[key],valid[key]
        expected = {(life,rep,teacher,method,replica) for rep in REPRESENTATIONS for teacher in TEACHERS
            for method in ('TEACHER',)+LEARNERS for replica in range(REPLICAS)}
        checks['control_roster'] &= seen == expected and len(seen) == 192
        checks['learner_roster'] &= set(lifecycle['representations']) == set(REPRESENTATIONS)
        for rep,teachers in lifecycle['representations'].items():
            checks['learner_roster'] &= set(teachers) == set(TEACHERS)
            for teacher,data in teachers.items():
                key = life,rep,teacher; parent_state = planning.previous.model_state(source,teacher,'PARENT',0)
                checks['teacher_immutable'] &= (data['parent_before'] == data['parent_after'] == parent_state
                    and data['teacher_before'] == data['teacher_after'] == planning.expected_model_state(source,teacher,rep)
                    and Counter(data['teacher_counts']) == teacher_totals[(rep,teacher)])
                checks['model_loads'] &= previous.teacher_loads_valid(data['loads'],source,rep,teacher)
                init = data['initialization']; head_size = planning.previous.parameter_count(rep)
                checks['initialization'] &= (init['state'] == data['final_model_states']['INITIAL_H2'] == previous.component_state(rep,0)
                    and init['setup_counts'].get('allocated_weight_parameters') == 2*head_size
                    and init['setup_counts'].get('source_parameters_copied') == head_size
                    and init['setup_counts'].get('source_weight_bytes_copied') == 8*head_size)
                checks['model_loads'] &= len(data['model_loads']) == 2 and {item['method'] for item in data['model_loads']} == set(LEARNERS)
                for item in data['model_loads']:
                    method = item['method']; checkpoint = trained[key]['methods'][method]['checkpoint']
                    checks['model_loads'] &= (item['model_ref'] == checkpoint['model_ref']
                        and item['state'] == data['final_model_states'][method] == previous.component_state(rep,updates[key][method])
                        and item['load_counts'].get('checkpoint_loads') == 1
                        and item['setup_counts'].get('allocated_weight_parameters') == previous.parameter_count(rep))
                costs['model_accounting'].append(dict(phase='evaluation',life=life,representation=rep,teacher_query=teacher,**data))
    checks['physical_logical_rosters'] &= costs['control']['games'] == 768 and len(indexed) == 1024 and len(diagnostics) == 256
    checks['retained_source_roster'] = (costs['source_counts']['episodes'] == 8598
        and costs['source_counts']['eligible_episodes'] == 8582 and costs['source_counts']['excluded_episodes'] == 16
        and costs['source_counts']['transitions'] == 8388608 and costs['source_statuses']['ACTIVE'] == 16
        and costs['source_statuses'].get('CUTOFF',0) == 0)
    costs['new_training_environment_samples'] = sum(cost['replay_counts'].get('newly_sampled_environment_transitions',0) for cost in costs['training'].values())
    costs['new_environment_samples'] = costs['new_training_environment_samples']+costs['control']['environment_counts']['sampled_transitions']
    work = costs['control']['policy_counts']+costs['zero_equivalence_counts']
    for cost in costs['training'].values(): work.update(cost['model_counts'])
    for counts in costs['diagnostic_counts'].values(): work.update(counts)
    costs['new_model_samples'] = sum(value for key,value in work.items() if key.endswith('model_spawn_samples'))
    costs['generated_model_outcomes'] = work.get('generated_spawn_outcomes',0)
    checks['no_stochastic_model_samples'] = costs['new_model_samples'] == 0
    control,calibration = full_game_comparison(indexed,valid),calibration_summary(diagnostics)
    complete = run['status'] == 'complete' and all(checks.values())
    return dict(schema='acfqp.terminal_supervision.v137.analysis',complete=complete,
        primary_complete=complete and control['complete'],checks={key:bool(value) for key,value in checks.items()},
        learners=learners,control=control,calibration=calibration,diagnostic_games=diagnostics,costs=costs,
        inherited_work=run['inherited_costs'],required_inputs=capsule['required_inputs'],seconds=run['seconds'],
        analysis_seconds=perf_counter()-started,
        scope='Independent target and exact TD source comparison; each retained complete episode fits both arms once, with no new training samples. Teacher comparisons and diagnostics use frozen models on paired new evaluation games, without resampling or replaying checkpoint weights.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'reports/controlled_predictive_terminal_supervision_v137')
    args = parser.parse_args(); result = analyze(args.input)
    (args.input/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=result['checks'])))
