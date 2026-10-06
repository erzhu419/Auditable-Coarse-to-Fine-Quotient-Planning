"""Independent geometry, conditional first-spawn replay and block variance audit."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from fractions import Fraction
import argparse
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from scripts import analyze_controlled_predictive_fixed_board_replication_v175 as previous
from scripts import analyze_controlled_predictive_causal_quotient_v171 as replay
from scripts.analyze_controlled_predictive_fixed_program_v167 import _equal, _mean

prior = replay.prior
BASE = 17600000000
LIVES, COHORTS, METHODS = range(4), ('TRAIN', 'FRESH'), ('STRAT', 'IID')
METRICS = ('utility', 'reward', 'failure', 'success')


def joint_support(tree_empty, one_empty):
    sizes = len(tree_empty), len(one_empty)
    if not all(sizes):
        raise ValueError('both nonterminal actions need a nonempty spawn support')
    endpoints = sorted({Fraction(i, size) for size in sizes for i in range(size+1)})
    rows = []
    for left, right in zip(endpoints, endpoints[1:]):
        midpoint = (left+right)/2
        for rank, mass in ((1, Fraction(9, 10)), (2, Fraction(1, 10))):
            rows.append(dict(stratum=len(rows), lower=float(left), upper=float(right), rank=rank,
                tree_cell=tree_empty[int(midpoint*sizes[0])], one_cell=one_empty[int(midpoint*sizes[1])],
                probability=float((right-left)*mass)))
    return rows


def allocation(support):
    counts = {row['stratum']: 2 for row in support}
    probabilities = {row['stratum']: Fraction(row['probability']).limit_denominator(2560) for row in support}
    for _ in range(2*len(support)):
        selected = min(support, key=lambda row: (-probabilities[row['stratum']]**2/(counts[row['stratum']]*(counts[row['stratum']]+1)), row['stratum']))
        counts[selected['stratum']] += 1
    return {key: counts[key] for key in sorted(counts)}


def branch_roster(roots):
    plans = []
    for root in roots:
        strata = [(row['stratum'], replicate) for row in root['support'] for replicate in range(root['allocation'][str(row['stratum'])])]
        for block in range(8):
            for method in ('IID', 'STRAT'):
                for draw in range(root['draws_per_block']):
                    stratum, replicate = strata[draw] if method=='STRAT' else (None, None)
                    offset = root['probe_ordinal']*100000 + block*1000 + draw
                    for mode in ('TREE', 'ONE'):
                        plans.append(dict(branch_id=f"PROBE:{root['root_id']}:{block}:{method}:{draw}:{mode}", phase='PROBE', root_id=root['root_id'],
                            cohort=root['cohort'], life=root['life'], source_id=root['source_id'], query='risk1', method=method, block=block,
                            suffix=draw, mode=mode, stratum=stratum, replicate=replicate, probe_ordinal=root['probe_ordinal'], seed=BASE+10000000+offset,
                            spawn_seed=BASE+20000000+offset, **root['actions'][mode]))
    return plans


def _metrics(vector):
    return dict(zip(METRICS, [vector[0]-vector[1]+vector[2], *vector]))


def _variance(values):
    mean = _mean(values)
    return math.fsum((value-mean)**2 for value in values)/(len(values)-1)


def _series(rows, work):
    rows = sorted(rows, key=lambda row: row['block'])
    blocks = [dict(block=row['block'], components=list(row['components']), metrics=_metrics(row['components']),
        physical_branches=row['physical_branches'], environment_samples=row['environment_samples']) for row in rows]
    work['batch_utility_evaluations'] += len(blocks)
    mean_cost = _mean([row['environment_samples'] for row in blocks]); stats = {}
    for metric in METRICS:
        values = [row['metrics'][metric] for row in blocks]; variance = _variance(values)
        stats[metric] = dict(mean=_mean(values), block_estimate_variance=variance, mean_estimate_variance=variance/8,
            block_variance_environment_cost_product=variance*mean_cost)
        work['batch_metric_sample_variances'] += 1
    return dict(per_block=blocks, metrics=stats, mean_per_block_physical_branches=_mean([row['physical_branches'] for row in blocks]),
        mean_per_block_environment_samples=mean_cost, total_physical_branches=sum(row['physical_branches'] for row in blocks),
        total_environment_samples=sum(row['environment_samples'] for row in blocks))


def _contrast(strat, iid, work):
    stats = {}
    for metric in METRICS:
        a, b = [row['metrics'][metric] for row in strat['per_block']], [row['metrics'][metric] for row in iid['per_block']]
        av, bv = _variance(a), _variance(b); difference = av-bv
        deleted = [_variance(a[:i]+a[i+1:])-_variance(b[:i]+b[i+1:]) for i in range(8)]
        center = _mean(deleted); error = math.sqrt(7/8*math.fsum((value-center)**2 for value in deleted))
        stats[metric] = dict(variance_ratio=av/bv if bv>0 else None, block_variance_difference=difference, mean_variance_difference=difference/8,
            variance_difference_jackknife_se=error, variance_difference_jackknife_ci95=[difference-1.96*error, difference+1.96*error])
        work.update(variance_difference_leave_one_block_out_estimates=8, jackknife_metric_sample_variances=16)
    return stats


def analyze_batches(batches):
    batches = list(batches); issues, work, index, identities = [], Counter(), {}, {}
    for row in batches:
        work['batch_rows_indexed'] += 1
        identity = row['cohort'], row['root_id']; key = row['method'], row['block'], *identity
        if key in index:
            issues.append(f'duplicate_batch:{key}')
        index[key] = row
        if row['method'] not in METHODS or row['block'] not in range(8):
            issues.append(f'unexpected_batch:{key}')
        if row['cohort'] not in COHORTS or row['life'] not in LIVES:
            issues.append(f'unknown_fixed_board:{identity}')
        if identity in identities and identities[identity]!=row['life']:
            issues.append(f'board_history_mismatch:{identity}')
        identities[identity] = row['life']; vector = row['components']
        if len(vector)!=3 or not all(math.isfinite(value) for value in vector):
            issues.append(f'incomplete_batch_vector:{key}')
        work['batch_component_reads'] += len(vector)
        if row['physical_branches']<=0 or row['environment_samples']<=0:
            issues.append(f'incomplete_batch_cost:{key}')
        work['batch_cost_reads'] += 2
    roster = Counter((cohort, life) for (cohort, _), life in identities.items())
    if set(roster)!={(cohort, life) for cohort in COHORTS for life in LIVES} or any(value!=1 for value in roster.values()):
        issues.append('fixed_eight_board_roster_mismatch')
    expected = {(method, block, *identity) for method in METHODS for block in range(8) for identity in identities}
    if set(index)!=expected or len(batches)!=len(expected):
        issues.append('incomplete_batch_roster')
    if not issues:
        for identity in identities:
            for block in range(8):
                if index[('STRAT',block)+identity]['physical_branches']!=index[('IID',block)+identity]['physical_branches']:
                    issues.append(f'unmatched_physical_budget:{identity}:{block}')
    result = dict(schema='acfqp.spawn_stratification.v176', complete=not issues, issues=issues, blocks=8, roots=len(identities), methods={}, comparison={}, work=dict(work),
        scope='conditional variance on eight fixed boards and frozen TREE/ONE actions; paired variance-difference jackknife normal intervals approximate with eight blocks; no strategy gate')
    if issues:
        return result
    for method in METHODS:
        per_root = [dict(cohort=cohort, root_id=root_id, life=life, **_series([index[method, block, cohort, root_id] for block in range(8)], work))
            for (cohort, root_id), life in sorted(identities.items())]
        all_blocks, history_blocks = [], {life: [] for life in LIVES}
        for block in range(8):
            rows = [index[(method,block)+identity] for identity in identities]
            all_blocks.append(dict(block=block, components=[_mean([row['components'][k] for row in rows]) for k in range(3)],
                physical_branches=sum(row['physical_branches'] for row in rows), environment_samples=sum(row['environment_samples'] for row in rows)))
            work['fixed_board_component_mean_reads'] += 3*len(rows)
            for life in LIVES:
                local = [row for row in rows if row['life']==life]
                history_blocks[life].append(dict(block=block, components=[_mean([row['components'][k] for row in local]) for k in range(3)],
                    physical_branches=sum(row['physical_branches'] for row in local), environment_samples=sum(row['environment_samples'] for row in local)))
                work['fixed_history_component_mean_reads'] += 3*len(local)
        result['methods'][method] = dict(**_series(all_blocks, work), per_root=per_root,
            per_history=[dict(life=life, roots=2, **_series(history_blocks[life], work)) for life in LIVES])
    a, b = [result['methods'][method] for method in METHODS]
    result['comparison'] = dict(contrast='STRAT/IID', jackknife_blocks=8, metrics=_contrast(a, b, work),
        per_root=[dict(cohort=x['cohort'], root_id=x['root_id'], life=x['life'], metrics=_contrast(x, y, work)) for x,y in zip(a['per_root'], b['per_root'])],
        per_history=[dict(life=x['life'], metrics=_contrast(x, y, work)) for x,y in zip(a['per_history'], b['per_history'])])
    result['work'] = dict(work)
    return result


def construct_batches(roots, plans, outcomes):
    if not replay.complete_cohort(outcomes, plans):
        raise ValueError('incomplete frozen branch roster')
    index = {(row['root_id'],row['method'],row['block'],row['suffix'],row['mode']):row for row in outcomes}
    batches = []
    for root in roots:
        for block in range(8):
            for method in ('IID', 'STRAT'):
                totals, cost = [[], [], []], 0
                for draw in range(root['draws_per_block']):
                    a, b = [index[root['root_id'],method,block,draw,mode] for mode in ('TREE', 'ONE')]
                    weight = root['support'][a['stratum']]['probability']/root['allocation'][str(a['stratum'])] if method=='STRAT' else 1/root['draws_per_block']
                    for k in range(3):
                        totals[k].append(weight*(a['components'][k]-b['components'][k]))
                    cost += a['steps']+b['steps']
                batches.append(dict(method=method,block=block,root_id=root['root_id'],cohort=root['cohort'],life=root['life'],
                    components=[math.fsum(values) for values in totals],physical_branches=2*root['draws_per_block'],environment_samples=cost))
    return batches


def replay_branch(row, root):
    result, n = row['result'], row['result']['steps']
    checks = dict(arrays=n>0 and all(len(row[key])==n for key in ('actions','choices','scores','spawned_cells','spawned_ranks')),
        settings=row['max_steps']==8192 and row['p_four']==.1 and row['initial_spawns']==[] and row['query']=='risk1',actions=True,forced_choice=True,
        teacher_choices=True,work=True,rng=True,terminal=True,returns=True,environment=True,policy_totals=True,
        module=row['module']==dict(mode='FORCED_H2',life=row['life'],forced_decisions=1,h2_calls=n-1),
        no_learning=not any(result['learning_counts'].values()),seconds=math.isfinite(result['seconds']) and math.isfinite(result['decision_seconds']) and 0<=result['decision_seconds']<=result['seconds'])
    if not checks['arrays']:
        return checks,0
    board = tuple(row['root_board']); tail_rng, first_rng = random.Random(row['seed']), random.Random(row['spawn_seed'])
    status, exits, swipes = prior.prior.previous.legal_exits(board); replayed = swipes
    environment = Counter(ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes,ground_swipe_calls=swipes)
    policy, totals, score_total = Counter(), {q:Counter() for q in ('risk1','risk8')}, 0
    checks['actions'] &= status=='ACTIVE'
    for step, choice in enumerate(row['choices']):
        if step==0:
            work = Counter(forced_root_legality_swipes=1,forced_root_actions=1)
            after, score, legal = prior.ground.swipe_board_v1(board,prior.ground.Swipe2048Action(row['first_action'])); replayed += 1
            checks['forced_choice'] &= legal and choice['action']==row['first_action'] and choice['afterstate']==list(after) and choice['score']==score
            expected_phase, expected_policy = 'forced','FORCED'
        else:
            expected_phase, expected_policy = 'teacher','risk1'
            native = {key[len('policy_risk1_'):]:value for key,value in choice['work'].items() if key.startswith('policy_risk1_')}
            work = Counter(forced_decisions=1); work.update({f'policy_risk1_{key}':value for key,value in native.items()})
            checks['teacher_choices'] &= prior.prior.planning.planning_counts_valid(native,'H2','SINGLE',1,len(exits)) and prior.prior.local.compact_choice_valid(choice,exits,'risk1')
            prior.add_checks(checks,prior.prior.h1.root_choice_checks(board,choice,'risk1')); replayed += 4
        checks['work'] &= choice['step']==step and choice['phase']==expected_phase and choice['policy_key']==expected_policy and Counter(choice['work'])==work
        policy.update(choice['work']); prior.prior.add_policy_work(totals,choice['work'])
        action = choice['action']; checks['actions'] &= status=='ACTIVE' and action in exits and row['actions'][step]==action
        if action not in exits:
            return checks,replayed
        after, score = exits[action]; score_total += score; checks['actions'] &= row['scores'][step]==score
        empty = [i for i,value in enumerate(after) if not value]
        if step==0 and row['method']=='STRAT':
            support = root['support'][row['stratum']]
            cell, rank = support['tree_cell' if row['mode']=='TREE' else 'one_cell'], support['rank']
            checks['rng'] &= cell in empty
            environment['conditioned_first_spawn_assignments'] += 1
        else:
            rng = first_rng if step==0 else tail_rng
            cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random()<.9 else 2
            environment['environment_random_draws'] += 2
        checks['rng'] &= (row['spawned_cells'][step],row['spawned_ranks'][step])==(cell,rank)
        board = list(after); board[cell] = rank
        status, exits, swipes = prior.prior.previous.legal_exits(tuple(board)); replayed += swipes
        environment.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1+swipes,sampled_transitions=1,
            ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes)
    final = 'CUTOFF' if status=='ACTIVE' else status; vector = [score_total/2048.,float(final=='LOST'),float(final=='WON')]
    checks['terminal'] &= row['final_board']==board and result['status']==final and n<=8192 and (final!='CUTOFF' or n==8192)
    checks['returns'] &= result['score']==score_total and result['components']==vector and result['utility']==(None if final=='CUTOFF' else replay._utility(vector))
    checks['environment'] &= Counter(result['environment_counts'])==environment
    checks['policy_totals'] &= Counter(result['policy_counts'])==policy and Counter(result['program_setup_counts'])==Counter() and set(result['policy_counts_by_query'])==set(totals) and all(Counter(result['policy_counts_by_query'][q])==totals[q] for q in totals)
    return checks,replayed


def replay_lifecycle(task):
    directory, lifecycle, snapshot, plans, roots = task; directory = Path(directory)
    plans = {row['branch_id']:row for row in plans}; roots = {row['root_id']:row for row in roots}
    compact = json.loads((directory/lifecycle['outcomes_ref']).read_text()); index = {row['branch_id']:row for row in compact}
    observed, costs, checks = [], prior.new_cost(), {}; methods = {method:prior.new_cost() for method in METHODS}
    totals = {query:Counter() for query in ('risk1','risk8')}
    for row in prior.prior.old.read_rows(directory/lifecycle['branch_trace']):
        local, swipes = replay_branch(row,roots[row['root_id']]); plan = plans.get(row['branch_id']); observed.append(row['branch_id'])
        local['frozen_identity'] = plan is not None and _equal(row,plan)
        local['frozen_root'] = row['root_board']==roots[row['root_id']]['board'] and row['first_action']==plan['actual_action']
        expected = dict(plan or {})|{key:row['result'][key] for key in ('score','steps','status','components','utility')}|dict(module=row['module'])
        local['compact_matches_trace'] = _equal(index.get(row['branch_id']),expected)
        prior.add_checks(checks,local); prior.add_cost(costs,row['result'],'physical_branches'); costs['analysis_replay_swipes'] += swipes
        prior.add_cost(methods[row['method']],row['result'],'physical_branches'); methods[row['method']]['analysis_replay_swipes'] += swipes
        for query in totals:
            totals[query].update(row['result']['policy_counts_by_query'][query])
    prior.add_checks(checks,prior.teacher_checks(lifecycle,snapshot,totals))
    checks['physical_roster'] = len(observed)==len(set(observed))==len(plans) and set(observed)==set(plans)
    checks['compact_roster'] = len(compact)==len(index)==len(plans) and set(index)==set(plans)
    for key in ('physical_branches','environment_counts','policy_counts','program_setup_counts','statuses'):
        checks['cost:'+key] = _equal(lifecycle[key],dict(costs[key]) if isinstance(costs[key],Counter) else costs[key])
    return dict(life=lifecycle['life'],checks=checks,costs=costs,method_costs=methods,outcomes=compact)


def select_geometry(roots, choices):
    index = {row['root_id']:row for row in roots}; candidates = []
    for choice in choices['choices']:
        if not choice['changed']:
            continue
        original = index[choice['root_id']]; actuals = {row['canonical_action']:row['actual_action'] for row in original['actions']}
        row = {key:deepcopy(original[key]) for key in ('root_id','cohort','life','source_id','board','canonical_board')}
        row.update(source_root_ordinal=original['ordinal'],actions={},afterstates={})
        for mode in ('TREE','ONE'):
            action = choice['decisions'][mode]['canonical_action']; actual = actuals[action]
            after, score, legal = prior.ground.swipe_board_v1(tuple(row['board']),prior.ground.Swipe2048Action(actual))
            if not legal:
                raise ValueError('frozen action is illegal')
            row['actions'][mode] = dict(canonical_action=action,actual_action=actual)
            row['afterstates'][mode] = dict(board=list(after),score=score,empty=[i for i,value in enumerate(after) if not value])
        row['support'] = joint_support(row['afterstates']['TREE']['empty'],row['afterstates']['ONE']['empty'])
        row['allocation'] = {str(key):value for key,value in allocation(row['support']).items()}
        row['draws_per_block'] = 4*len(row['support']); candidates.append(row)
    selected = []
    for cohort in COHORTS:
        for life in LIVES:
            local = sorted((row for row in candidates if row['cohort']==cohort and row['life']==life),key=lambda row:(len(row['support']),row['root_id']))
            selected.append(dict(deepcopy(local[len(local)//2]),probe_ordinal=len(selected)))
    return selected,candidates


def extract_source(directory):
    directory = Path(directory)
    run,audit,stage,capsule,roots,choices = [json.loads(Path(path).read_text()) for path in (
        directory/'run.json',directory/'analysis.json',PROJECT/'reports/v175_runtime_tmp/stage_checks.json',directory/'source_capsule.json',directory/'roots.json',directory/'frozen_choices.json')]
    selected,candidates = select_geometry(roots,choices)
    manifest = dict(source_roots_ref=str(directory/'roots.json'),source_choices_ref=str(directory/'frozen_choices.json'),
        work=dict(json_read_operations=6,changed_root_records=len(candidates),support_ground_swipe_calls=2*len(candidates),joint_support_builds=len(candidates),selected_roots=8),
        candidates=[dict(root_id=row['root_id'],cohort=row['cohort'],life=row['life'],support_entries=len(row['support'])) for row in candidates])
    refs = capsule['cost_refs']+[dict(path=str(directory/'analysis.json'),fields=['costs'])]
    refs += [dict(path=str(PROJECT/f'reports/v175_runtime_tmp/{kind}_checks.json'),fields=['attempts']) for kind in ('core','runner','analyzer','stage')]
    refs += [dict(path=str(PROJECT/'reports/v175_runtime_tmp/engineering_recovery.json'),fields=['failed_stage_ref','extra_failed_teacher_loads'])]
    refs += [dict(path=str(PROJECT/'reports/v176_runtime_tmp/preflight_checks.json'),fields=['attempts'])]
    source = dict(schema='acfqp.spawn_stratification.v176.source',snapshots=capsule['snapshots'],inherited_run_ref=str(directory/'run.json'),
        inherited_analysis_ref=str(directory/'analysis.json'),inherited_stage_ref=str(PROJECT/'reports/v175_runtime_tmp/stage_checks.json'),
        inherited_v175_environment_samples=audit['costs']['new_environment_samples'],cost_refs=refs,
        this_stage_test_refs=[str(PROJECT/f'reports/v176_runtime_tmp/{kind}_checks.json') for kind in ('core','runner','analyzer')])
    return dict(source=source,manifest=manifest,roots=selected,parent_valid=run['status']=='complete' and audit['valid'] and audit['complete'] and stage['valid'])


def analyze(directory):
    started = perf_counter(); directory = Path(directory); read = lambda name:json.loads((directory/name).read_text())
    run,capsule,frozen = [read(name) for name in ('run.json','source_capsule.json','frozen_inputs.json')]
    inherited = extract_source(Path(capsule['inherited_run_ref']).parent); roots = inherited['roots']; plans = branch_roster(roots)
    checks,results,summary = [],[],None
    def check(name, passed):
        checks.append(dict(name=name,passed=bool(passed)))
    full_order = ['INPUTS_FROZEN','ROSTER_FROZEN','PROBE']
    check('frozen_phase_order',run['phase_order']==full_order[:len(run['phase_order'])] and set(run['phases'])=={'PROBE'})
    check('settled_v175_and_exact_capsule',inherited['parent_valid'] and capsule==inherited['source'] and run['inherited_cost_refs']==capsule['cost_refs'])
    check('fixed_geometry_only_source_manifest',read('source_manifest.json')==inherited['manifest'])
    check('independent_median_geometry_and_probability_allocation',_equal(read('selected_roots.json'),roots))
    check('independent_branch_roster_and_separate_paired_rng_seeds',read('branch_roster.json')==plans)
    check('frozen_settings',frozen['settings']==run['settings'])
    check('sampling_protocol',run['settings']==dict(blocks=8,lifecycles=list(LIVES),cohorts=list(COHORTS),methods=['IID','STRAT'],modes=['TREE','ONE'],
        selected_roots=8,roots_per_cohort_history=1,workers=4,max_steps=8192,p_four=.1,version_base=BASE,minimum_stratum_replicates=2,draws_per_support_entry=4,
        selection='median support cardinality among changed roots per cohort/history; cardinality then root_id',
        allocation='two per stratum then probability-only marginal variance reduction allocation to 4*S',
        coupling='joint cell-uniform support and common rank; independent first-spawn and tail RNG; shared tail seeds across methods/actions',
        estimator='STRAT probability-weighted stratum means; IID paired arithmetic mean; equal eight-board block means',
        primary='conditional utility block variance STRAT-IID; paired delete-block jackknife normal CI95 upper<0',
        secondary='descriptive variance ratios, full vectors and variance times mean block transition cost',
        incomplete='missing, duplicate, nonterminal or misbound required branch -> HOLD; no replacement',new_source_games=0,new_model_fits=0,new_parameter_updates=0,
        autonomous_evaluation=False,strategy_promotion=False,matched_budget='physical branch counts; actual transitions and all other paid costs reported'))
    counts = dict(Counter(plan['method'] for plan in plans))
    check('predeclared_physical_budget',run['physical_roster_counts']==counts and run['physical_branch_cap']==len(plans) and run['maximum_environment_transitions']==len(plans)*8192 and counts['STRAT']==counts['IID'])
    lifecycles = run['phases']['PROBE']['lifecycles']
    check('four_history_lifecycles',len(lifecycles)==4 and [row['life'] for row in lifecycles]==list(LIVES))
    with ProcessPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(replay_lifecycle,[(str(directory),row,capsule['snapshots'][row['life']],
            [plan for plan in plans if plan['life']==row['life']],roots) for row in lifecycles]))
    for result in results:
        for name,passed in result['checks'].items():
            check(f'life{result["life"]}:{name}',passed)
    outcomes = [row for result in results for row in result['outcomes']]; cohort = replay.complete_cohort(outcomes,plans)
    if cohort:
        batches = construct_batches(roots,plans,outcomes); summary = analyze_batches(batches)
        check('independent_probability_weighted_full_vectors_and_costs',_equal(read('batches.json'),batches))
        check('independent_eight_board_block_variance_jackknife_and_cost_product',_equal(read('summary.json'),summary))
    else:
        check('incomplete_probe_stops_summary',not (directory/'summary.json').exists() and not (directory/'batches.json').exists())
    costs = prior.aggregate_costs([result['costs'] for result in results])
    costs.update(method_costs={method:prior.aggregate_costs([result['method_costs'][method] for result in results]) for method in METHODS},
        source_geometry_work=inherited['manifest']['work'],summary_work={} if summary is None else summary['work'],summary_seconds=run.get('summary_seconds',0.),
        inherited_v175_environment_samples=capsule['inherited_v175_environment_samples'],inherited_cost_refs=capsule['cost_refs'],this_stage_test_refs=capsule['this_stage_test_refs'],
        new_source_games=0,new_model_fits=0,new_native_weight_updates=0,inherited_trajectory_replays=0,
        teacher_accounting=[dict(life=row['life'],query=query,**record) for row in lifecycles for query,record in row['teacher_bank'].items()])
    check('no_new_learning',run['new_model_fits']==run['new_parameter_updates']==0)
    check('physical_transition_and_branch_caps',costs['new_environment_samples']<=len(plans)*8192 and costs['physical_branches']<=len(plans))
    check('terminal_status',run['status']==('complete' if summary is not None and summary['complete'] else 'HOLD'))
    if run['status']=='complete':
        check('complete_phase_and_physical_roster',run['phase_order']==full_order and cohort and costs['physical_branches']==len(plans))
    valid = all(row['passed'] for row in checks); complete = valid and run['status']=='complete' and summary is not None and summary['complete']
    result = dict(schema='acfqp.spawn_stratification.v176.analysis',valid=valid,complete=complete,primary_complete=complete,checks=checks,
        passed_checks=sum(row['passed'] for row in checks),total_checks=len(checks),costs=costs,
        methods={} if summary is None else summary['methods'],comparison={} if summary is None else summary['comparison'],strategy_promotion=False,seconds=perf_counter()-started)
    (directory/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--directory',type=Path,default=PROJECT/'reports/controlled_predictive_spawn_stratification_v176')
    result = analyze(parser.parse_args().directory)
    print(json.dumps(dict(valid=result['valid'],primary_complete=result['primary_complete'],passed=result['passed_checks'],checks=result['total_checks'])))
    raise SystemExit(0 if result['valid'] else 1)


if __name__=='__main__':
    main()
