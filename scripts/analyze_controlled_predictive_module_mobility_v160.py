"""Replay bounded mobility interventions and report fixed-root paired effects."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import analyze_controlled_predictive_module_diagnosis_v153 as diagnosis
from scripts import analyze_controlled_predictive_module_split_half_v157 as arithmetic

prior = diagnosis.prior
LIVES, QUERIES = prior.LIVES, prior.QUERIES
SOURCES = ('H2', 'LEARN8')
MODES = ('H2', 'OTHER8', 'MOBILITY')
CONTRASTS = {'MOBILITY-H2': ('MOBILITY', 'H2'),
             'MOBILITY-OTHER8': ('MOBILITY', 'OTHER8'), 'OTHER8-H2': ('OTHER8', 'H2')}
METRICS = ('utility', 'reward', 'failure', 'success')
BASE, SUFFIXES, MAX_STEPS, WORKERS = 160*100000000, 32, 2000, 4
read, mean, close, add_checks = prior.read, prior.mean, prior.close, prior.add_checks


def branch_seed(root, suffix):
    return (BASE+20000000+root['life']*1000000+list(QUERIES).index(root['query'])*100000
            +SOURCES.index(root['source_method'])*10000+root['slot']*100+suffix)


def branch_roster(roots):
    return [dict(branch_id=f'{r["root_id"]}:{suffix}:{mode}', root_id=r['root_id'],
                 suffix=suffix, mode=mode, seed=branch_seed(r, suffix))
            for r in roots for suffix in range(SUFFIXES) for mode in MODES]


def moments(values):
    values = list(values)
    average = mean(values); complete = average is not None
    variance = (sum((x-average)**2 for x in values)/(len(values)-1)
                if complete and len(values)>1 else (0. if complete else None))
    return dict(n=len(values), complete=complete, mean=average, sample_variance=variance,
                mean_variance=variance/len(values) if complete else None)


def interval(average, variance, complete):
    se = math.sqrt(variance) if complete else None
    return dict(complete=complete, mean=average, conditional_suffix_se=se,
                conditional_suffix_ci95=None if se is None else [average-1.96*se, average+1.96*se])


def root_pool(stats):
    complete = bool(stats) and all(s['complete'] for s in stats)
    variance = sum(s['mean_variance'] for s in stats)/len(stats)**2 if complete else None
    return interval(mean(s['mean'] for s in stats), variance, complete)


def history_pool(stats):
    complete = len(stats)==4 and all(s['complete'] for s in stats)
    variance = sum(s['conditional_suffix_se']**2 for s in stats)/16 if complete else None
    result = interval(mean(s['mean'] for s in stats), variance, complete)
    result['positive_histories'] = sum(s['mean'] is not None and s['mean']>0 for s in stats)
    return result


def outcome_values(row):
    if row is None or row['status'] not in ('WON', 'LOST'):
        return {key: None for key in METRICS}
    return dict(zip(METRICS, [row['utility'], *row['components']]))


def summarize(roots, outcomes):
    """Pair suffixes first; average roots within each of four fixed histories."""
    index = {(r['root_id'], r['suffix'], r['mode']): r for r in outcomes}
    root_rows = []
    for root in roots:
        item = {key: root[key] for key in ('root_id', 'life', 'query', 'source_method', 'slot')}
        item.update(initial_empty=root['board'].count(0), stratum='TIGHT' if root['board'].count(0)<=2 else 'ROOMY')
        modes = {mode: [outcome_values(index.get((root['root_id'], suffix, mode)))
                       for suffix in range(SUFFIXES)] for mode in MODES}
        item['modes'] = {mode: {key: moments(v[key] for v in values) for key in METRICS}
                         for mode, values in modes.items()}
        item['contrasts'] = {name: {key: moments(None if a[key] is None or b[key] is None else a[key]-b[key]
                                               for a, b in zip(modes[left], modes[right])) for key in METRICS}
                             for name, (left, right) in CONTRASTS.items()}
        item['complete'] = all(m['complete'] for mode in item['modes'].values() for m in mode.values())
        root_rows.append(item)
    comparisons, mode_summaries, module_diagnostics = [], [], []
    for query in QUERIES:
        for source in ('ALL', *SOURCES):
            for stratum in ('ALL', 'TIGHT', 'ROOMY'):
                selected = [r for r in root_rows if r['query']==query and
                            (source=='ALL' or r['source_method']==source) and (stratum=='ALL' or r['stratum']==stratum)]
                for kind, names, output in (('contrasts', CONTRASTS, comparisons), ('modes', MODES, mode_summaries)):
                    for name in names:
                        histories = [dict(life=life, roots=sum(r['life']==life for r in selected),
                            metrics={key: root_pool([r[kind][name][key] for r in selected if r['life']==life])
                                     for key in METRICS}) for life in LIVES]
                        metrics = {key: history_pool([h['metrics'][key] for h in histories]) for key in METRICS}
                        output.append(dict(query=query, source_method=source, stratum=stratum,
                            **{('contrast' if kind=='contrasts' else 'mode'): name}, roots=len(selected),
                            complete=all(m['complete'] for m in metrics.values()), metrics=metrics, per_history=histories))
                for mode in MODES:
                    histories = []
                    for life in LIVES:
                        local = [r for r in selected if r['life']==life]
                        values = [[index.get((r['root_id'], s, mode)) for s in range(SUFFIXES)] for r in local]
                        complete = bool(local) and all(row is not None for rows in values for row in rows)
                        means = {name: mean(mean((row['module'][name] if name!='empty_gain' else
                                                row['module']['exit_empty']-row['module']['initial_empty'])
                                               for row in rows) for rows in values)
                                 for name in ('prefix_steps', 'completion', 'empty_gain')} if complete else {}
                        reasons = {reason: mean(mean(int(row['module']['exit_reason']==reason) for row in rows)
                                               for rows in values) for reason in ('baseline','target','budget','terminal','cutoff')} if complete else {}
                        histories.append(dict(life=life, roots=len(local), complete=complete, means=means, exit_rates=reasons))
                    complete = all(h['complete'] for h in histories)
                    module_diagnostics.append(dict(query=query, source_method=source, stratum=stratum, mode=mode,
                        roots=len(selected), complete=complete, means={name: mean(h['means'].get(name) for h in histories)
                        for name in ('prefix_steps','completion','empty_gain')}, exit_rates={name: mean(h['exit_rates'].get(name) for h in histories)
                        for name in ('baseline','target','budget','terminal','cutoff')}, per_history=histories))
    return dict(root_rows=root_rows, comparisons=comparisons, modes=mode_summaries, module_diagnostics=module_diagnostics)


def compact_outcome(row):
    return dict(**{key: row[key] for key in ('branch_id','root_id','life','query','source_method','slot','suffix','mode','seed')},
                **{key: row['result'][key] for key in ('score','steps','status','components','utility')}, module=row['module'])


def replay_branch(row, max_steps=MAX_STEPS):
    result = row['result']; n = result['steps']; query = row['query']; mode = row['mode']
    other = 'risk8' if query=='risk1' else 'risk1'
    checks = dict(branch_arrays=n>0 and all(len(row[k])==n for k in ('actions','choices','scores','spawned_cells','spawned_ranks')),
        branch_settings=row['p_four']==.1 and row['max_steps']==max_steps and mode in MODES,
        branch_actions=True, branch_rng=True, branch_terminal=True, branch_returns=True,
        branch_environment=True, branch_phases=True, branch_forced_query=True, branch_mobility_choice=True,
        branch_mobility_work=True, branch_module_exit=True, branch_policy_totals=True,
        branch_no_learning=not any(result['learning_counts'].values()),
        branch_seconds=math.isfinite(result['seconds']) and math.isfinite(result['decision_seconds']) and 0<=result['decision_seconds']<=result['seconds'])
    if not checks['branch_arrays']: return checks, 0
    board = tuple(row['root_board']); status, exits, swipes = prior.previous.legal_exits(board); replayed = swipes
    checks['branch_terminal'] &= status=='ACTIVE'
    environment = Counter(ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes, ground_swipe_calls=swipes)
    phases = {p: Counter() for p in ('prefix','continuation')}; teachers = {q: Counter() for q in QUERIES}
    initial_empty = board.count(0); target_empty = initial_empty+2; prefix_active = mode!='H2'
    module = dict(initial_empty=initial_empty,target_empty=target_empty,prefix_steps=0,
        exit_reason='baseline' if mode=='H2' else None,exit_empty=initial_empty if mode=='H2' else None,completion=False)
    rng = random.Random(row['seed']); score_total = 0
    for step, choice in enumerate(row['choices']):
        phase = 'prefix' if prefix_active else 'continuation'; work = Counter(choice['work']); phases[phase].update(work)
        checks['branch_phases'] &= choice['step']==step and choice['phase']==phase and choice['module_decision'] is None
        if phase=='prefix' and mode=='MOBILITY':
            options = {action:dict(afterstate=list(after),score=score,expected_postspawn_empty=after.count(0)-1)
                       for action,(after,score) in sorted(exits.items())}
            selected = min(options, key=lambda action:(-options[action]['expected_postspawn_empty'],action)) if options else None
            checks['branch_mobility_choice'] &= choice['policy_key']=='MOBILITY' and choice['action_values']==options and choice['action']==selected
            checks['branch_mobility_choice'] &= selected is not None and all(choice[k]==options[selected][k] for k in options[selected])
            expected = Counter(mobility_choose_calls=1,mobility_action_evaluations=4,mobility_learned_swipe_calls=4,
                mobility_learned_line_rewrites=16,mobility_legal_actions=len(exits),mobility_empty_cell_inspections=16*len(exits))
            checks['branch_mobility_work'] &= work==expected
        else:
            policy = other if phase=='prefix' else query
            native = {k[len(f'policy_{policy}_'):]:v for k,v in work.items() if k.startswith(f'policy_{policy}_')}
            expected = Counter(forced_decisions=1); expected.update({f'policy_{policy}_{k}':v for k,v in native.items()})
            checks['branch_forced_query'] &= choice['policy_key']==policy and work==expected
            checks['branch_forced_query'] &= prior.planning.planning_counts_valid(native,'H2','SINGLE',1,len(exits)) and prior.local.compact_choice_valid(choice,exits,policy)
            add_checks(checks,prior.h1.root_choice_checks(board,choice,policy)); replayed += 4
        prior.add_policy_work(teachers,work)
        action = choice['action']; checks['branch_actions'] &= status=='ACTIVE' and action in exits and row['actions'][step]==action
        if action not in exits: return checks, replayed
        after, score = exits[action]; score_total += score; checks['branch_actions'] &= row['scores'][step]==score
        empty = [i for i,v in enumerate(after) if not v]
        cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random()<.9 else 2
        checks['branch_rng'] &= (row['spawned_cells'][step],row['spawned_ranks'][step])==(cell,rank)
        board = list(after); board[cell]=rank; status, exits, swipes = prior.previous.legal_exits(tuple(board)); replayed += swipes
        environment.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1+swipes,environment_random_draws=2,sampled_transitions=1,
                           ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes)
        if phase=='prefix':
            module['prefix_steps'] += 1
            reason = ('terminal' if status!='ACTIVE' else 'target' if mode=='MOBILITY' and board.count(0)>=target_empty
                      else 'budget' if module['prefix_steps']==8 else None)
            if reason is not None:
                module.update(exit_reason=reason,exit_empty=board.count(0),completion=mode=='MOBILITY' and board.count(0)>=target_empty)
                prefix_active = False
    final = 'CUTOFF' if status=='ACTIVE' else status
    if prefix_active: module.update(exit_reason='cutoff',exit_empty=board.count(0))
    components = [score_total/2048.,float(final=='LOST'),float(final=='WON')]
    checks['branch_module_exit'] &= row['module']==module
    checks['branch_terminal'] &= row['final_board']==board and result['status']==final and n<=max_steps and (final!='CUTOFF' or n==max_steps)
    checks['branch_returns'] &= result['score']==score_total and result['components']==components and result['utility']==(None if final=='CUTOFF' else prior.utility(components,query))
    checks['branch_environment'] &= Counter(result['environment_counts'])==environment
    checks['branch_policy_totals'] &= Counter(result['prefix_counts'])==phases['prefix'] and Counter(result['continuation_counts'])==phases['continuation'] and Counter(result['policy_counts'])==sum(phases.values(),Counter())
    checks['branch_policy_totals'] &= set(result['policy_counts_by_query'])==set(QUERIES) and all(Counter(result['policy_counts_by_query'][q])==teachers[q] for q in QUERIES)
    return checks, replayed


def new_cost():
    return dict(physical_branches=0, environment_counts=Counter(), policy_counts=Counter(), statuses=Counter(), decision_seconds=0.)


def add_branch_cost(cost, result):
    cost['physical_branches'] += 1; cost['statuses'][result['status']] += 1
    cost['decision_seconds'] += result['decision_seconds']
    for name in ('environment_counts','policy_counts'): cost[name].update(result[name])


def audit_lifecycle(lifecycle, source, roots, directory):
    directory = Path(directory); life = lifecycle['life']; root_map = {r['root_id']:r for r in roots}
    seen, outcomes = [], []; teacher_counts = {q:Counter() for q in QUERIES}
    checks = dict(branch_identity=True,branch_roster=True,compact_outcomes=True,physical_accounting=True,
                  teacher_bank=True,teacher_totals=True,
                  rule_frozen=lifecycle['rule_before']==lifecycle['rule_after']==source['rule'])
    costs = new_cost(); costs.update(analysis_replay_swipes=0,physical_cells={},teacher_accounting=[])
    for row in prior.old.read_rows(directory/lifecycle['branch_trace']):
        root = root_map[row['root_id']]; query = root['query']; mode = row['mode']; suffix = row['suffix']; seen.append(row['branch_id'])
        checks['branch_identity'] &= all(row[k]==v for k,v in dict(branch_id=f'{root["root_id"]}:{suffix}:{mode}',life=life,
            query=query,source_method=root['source_method'],slot=root['slot'],root_board=root['board'],seed=branch_seed(root,suffix)).items())
        local_checks, swipes = replay_branch(row); add_checks(checks,local_checks); costs['analysis_replay_swipes'] += swipes
        outcomes.append(compact_outcome(row)); result = row['result']; add_branch_cost(costs,result)
        for q in QUERIES: teacher_counts[q].update(result['policy_counts_by_query'][q])
        cell = costs['physical_cells'].setdefault(f'{query}:{root["source_method"]}:{mode}',dict(query=query,source_method=root['source_method'],mode=mode,**new_cost()))
        add_branch_cost(cell,result)
    checks['branch_roster'] &= seen==[r['branch_id'] for r in branch_roster(roots)] and len(seen)==1536
    checks['compact_outcomes'] &= read(directory/lifecycle['outcomes_ref'])==outcomes
    checks['physical_accounting'] &= lifecycle['physical_branches']==costs['physical_branches'] and all(Counter(lifecycle[k])==costs[k] for k in ('environment_counts','policy_counts','statuses'))
    checks['teacher_bank'] &= set(lifecycle['teacher_bank'])==set(QUERIES)
    for query in QUERIES:
        teacher = lifecycle['teacher_bank'][query]
        checks['teacher_bank'] &= prior.h1.teacher_analysis.teacher_loads_valid(teacher['loads'],source,'SINGLE',query)
        checks['teacher_bank'] &= teacher['parent_before']==teacher['parent_after']==prior.planning.previous.model_state(source,query,'PARENT',0)
        checks['teacher_bank'] &= teacher['leaf_before']==teacher['leaf_after']==prior.planning.expected_model_state(source,query,'SINGLE')
        checks['teacher_totals'] &= Counter(teacher['total_counts'])==teacher_counts[query]
        costs['teacher_accounting'].append(dict(life=life,query=query,**teacher))
    print(json.dumps(dict(event='audited_lifecycle',life=life,physical_branches=costs['physical_branches'],replayed_swipes=costs['analysis_replay_swipes'])),flush=True)
    return dict(life=life,checks=checks,outcomes=outcomes,costs=costs)


def settings_valid(settings):
    expected = dict(lifecycles=list(LIVES),queries=QUERIES,source_methods=list(SOURCES),modes=list(MODES),roots=64,
                    suffixes=32,physical_branches=6144,max_steps=2000,maximum_environment_transitions=12288000,
                    p_four=.1,workers=4,version_base=BASE,prefix_budget=8,empty_gain=2,new_training_updates=0)
    return all(settings.get(k)==v for k,v in expected.items())


def analyze(directory):
    started = perf_counter(); directory = Path(directory).resolve()
    run, capsule, frozen = (read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json'))
    source_run, source_analysis = read(capsule['source_run_ref']), read(capsule['source_analysis_ref'])
    original = read(Path(capsule['source_run_ref']).parent/'source_capsule.json')
    roots = capsule['roots']; inherited = {ref['path']:read(ref['path']) for ref in capsule['cost_refs']}
    checks = dict(settings=settings_valid(run['settings']),frozen_inputs=frozen['status']=='frozen' and
        frozen['settings']==run['settings'] and frozen['roots']==roots and frozen['branch_roster']==branch_roster(roots),
        root_roster=len(roots)==64 and len({r['root_id'] for r in roots})==64 and {r['root_id'] for r in roots}==
            {f'{l}:{q}:{s}:{slot}' for l in LIVES for q in QUERIES for s in SOURCES for slot in range(4)},
        frozen_roots=read(directory/'roots.json')==roots,source_complete=source_run['status']=='complete' and source_analysis['complete'] and source_analysis['primary_complete'],
        source_binding=roots==original['roots'] and capsule['snapshots']==original['snapshots'],
        inherited_costs=run['inherited_cost_refs']==capsule['cost_refs'],
        inherited_fields=all(all(field in inherited[ref['path']] for field in ref['fields']) for ref in capsule['cost_refs']),
        inherited_physical_cost=capsule['inherited_new_environment_samples']==source_analysis['costs']['inherited_new_environment_samples']==4026405,
        lifecycle_roster=len(run['lifecycles'])==4 and {r['life'] for r in run['lifecycles']}==set(LIVES))
    sources = {s['life']:s for s in capsule['snapshots']}; results = []
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks = [pool.submit(audit_lifecycle,life,sources[life['life']],[r for r in roots if r['life']==life['life']],directory) for life in run['lifecycles']]
        for task in as_completed(tasks): results.append(task.result())
    results.sort(key=lambda r:r['life']); outcomes = []; costs = new_cost()
    costs.update(analysis_replay_swipes=0,physical_cells={},teacher_accounting=[],new_training_updates=0,
                 inherited_new_environment_samples=4026405,analysis_inherited_files_read=len(inherited))
    for result in results:
        add_checks(checks,result['checks']); outcomes.extend(result['outcomes']); local = result['costs']
        for name in ('physical_branches','decision_seconds','analysis_replay_swipes'): costs[name] += local[name]
        for name in ('environment_counts','policy_counts','statuses'): costs[name].update(local[name])
        costs['teacher_accounting'].extend(local['teacher_accounting'])
        for key,cell in local['physical_cells'].items():
            target = costs['physical_cells'].setdefault(key,dict(query=cell['query'],source_method=cell['source_method'],mode=cell['mode'],**new_cost()))
            for name in ('physical_branches','decision_seconds'): target[name] += cell[name]
            for name in ('environment_counts','policy_counts','statuses'): target[name].update(cell[name])
    metrics = summarize(roots,outcomes)
    checks['summary_values'] = arithmetic.equivalent(read(directory/'summary.json'),metrics)
    checks['full_branch_roster'] = costs['physical_branches']==6144 and len(outcomes)==len({r['branch_id'] for r in outcomes})==6144
    costs['new_environment_samples'] = costs['environment_counts'].get('sampled_transitions',0)
    complete = run['status']=='complete' and all(checks.values())
    primary = [r for r in metrics['comparisons'] if r['contrast']=='MOBILITY-H2' and r['source_method']=='ALL' and r['stratum']=='ALL']
    return dict(schema='acfqp.module_mobility.v160.analysis',complete=complete,primary_complete=complete and all(r['complete'] for r in primary),
        checks=checks,metrics=metrics,costs=costs,inherited_cost_refs=capsule['cost_refs'],seconds=perf_counter()-started,
        uncertainty='Pointwise conditional suffix intervals for fixed roots and four fixed histories; no population-history interval.',
        limitations='Mobility completion is descriptive. Hand-designed vacancy restoration does not establish general strategy learning. Empty-history strata and cutoffs remain incomplete.')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_module_mobility_v160')
    directory = parser.parse_args().input
    result = analyze(directory)
    (directory/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
                         failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
