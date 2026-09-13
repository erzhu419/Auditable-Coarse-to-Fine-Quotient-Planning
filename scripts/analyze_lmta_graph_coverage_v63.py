"""Independent trajectory evidence for a fixed new sparse-graph cohort."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import importlib.util
import json
import math
from pathlib import Path
from statistics import mean, stdev, variance
from time import perf_counter

from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('coverage_queries_v62',Path(__file__).with_name('analyze_lmta_trajectory_scale_v62.py'))
v62 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v62)
v61 = v62.v61
METHODS, IDS = v61.METHODS, list(range(630000,630064))
BLOCK_LIMITS = dict(max_planner_action_values=2000000,max_decisions=100000,max_wall_seconds=60.)
CAMPAIGN_LIMITS = dict(max_planner_action_values=4000000,max_wall_seconds=300.)
PREVIOUS = 'reports/lmta_trajectory_scale_v62'
CALIBRATION = 'reports/lmta_trajectory_v61'
PROTOCOL = dict(nodes=15,stratum='sparse',expected_degree=1.5,p=1.5/14,graph_ids=IDS,
    budget=2,horizon=3,replicates=32,methods=METHODS,seed_base=61000000,seed_graph_stride=1000,
    limits=BLOCK_LIMITS,campaign_limits=CAMPAIGN_LIMITS,primary_alpha=.05,reference_family_size=4)


def campaign_check(manifest,cases):
    errors, used, last_elapsed = Counter(), 0, 0.
    roster = [(g,m) for index,g in enumerate(IDS) for m in (METHODS if index%2==0 else METHODS[::-1])]
    if [(c['graph_id'],c['method']) for c in cases] != roster[:len(cases)]:
        errors['executed_prefix_roster'] += 1
    if manifest['skipped_blocks'] != [dict(graph_id=g,method=m) for g,m in roster[len(cases):]]:
        errors['skipped_suffix_roster'] += 1
    for index,case in enumerate(cases):
        elapsed = case['campaign_elapsed_before']
        remaining = dict(max_planner_action_values=4000000-used,max_wall_seconds=300.-elapsed)
        expected = dict(BLOCK_LIMITS,**{n:min(BLOCK_LIMITS[n],value) for n,value in remaining.items()})
        if (case['campaign_actions_before']!=used or not v61.close(elapsed,elapsed) or elapsed<last_elapsed
                or any(value<=0 for value in remaining.values())
                or any(not v61.close(case['effective_limits'].get(n),value) for n,value in expected.items())):
            errors['effective_campaign_limits'] += 1
        stop = case['stop_reason']
        scope = None if stop is None else ('campaign' if stop in remaining and remaining[stop]<=BLOCK_LIMITS[stop] else 'block')
        if case['stop_scope']!=scope or (scope=='campaign' and index!=len(cases)-1):
            errors['stop_scope_or_continued_campaign'] += 1
        used += case['decision_work']['action_value_evaluations']; last_elapsed = elapsed
    if manifest['campaign_action_values']!=used:
        errors['campaign_action_sum'] += 1
    reason, elapsed = manifest['campaign_stop_reason'], manifest['campaign_elapsed_at_stop']
    if manifest['terminal_reason']=='finished_roster':
        if len(cases)!=128 or reason is not None or elapsed is not None or any(c['stop_scope']=='campaign' for c in cases):
            errors['finished_roster_terminal'] += 1
    elif manifest['terminal_reason']=='campaign_resource_limit':
        if (not v61.close(elapsed,elapsed) or elapsed<last_elapsed or elapsed>manifest['whole_runner_seconds']+1e-10
                or reason not in CAMPAIGN_LIMITS or (reason=='max_planner_action_values' and used<4000000)
                or (reason=='max_wall_seconds' and (elapsed<300. or used>=4000000))
                or (cases and cases[-1]['stop_scope']=='campaign' and reason!=cases[-1]['stop_reason'])):
            errors['campaign_terminal'] += 1
    else:
        errors['terminal_reason'] += 1
    return errors


def paired_estimate(groups):
    graph_means = [mean(values) for values in groups]
    center, n = mean(graph_means), len(groups)
    se = stdev(graph_means)/math.sqrt(n)
    mc_se = math.sqrt(sum(variance(values)/len(values) for values in groups)/n**2)
    interval = lambda z,s: [center-z*s,center+z*s]
    return dict(mean=center,graph_standard_error=se,degrees_of_freedom=n-1,
        graph_primary_95_interval=interval(float(t.ppf(.975,n-1)),se),
        graph_historical_four_comparison_interval=interval(float(t.ppf(1-.05/8,n-1)),se),
        fixed_panel_mc_standard_error=mc_se,fixed_panel_mc_nominal_95_interval=interval(v61.Z95,mc_se),
        graph_means=graph_means)


def cohort_summary(cases,rows,integrity):
    complete = integrity and len(cases)==128 and all(case['status']=='complete' for case in cases)
    costs = {}
    for method in METHODS:
        blocks = [case for case in cases if case['method']==method]
        work, environment = Counter(), Counter()
        for case in blocks:
            work.update(case['decision_work']); environment.update(case['environment_work'])
        costs[method] = dict(decision_work=dict(work),environment_work=dict(environment),
            completed_trajectories=sum(case['completed_replicates'] for case in blocks),
            attempted_blocks=len(blocks),resource_limited_blocks=sum(case['status']=='resource_limit' for case in blocks),
            decision_seconds=sum(case['decision_seconds'] for case in blocks),
            mean_trajectory_work={name:work[name]/2048 for name in work} if complete else None)
    quality = None
    if complete:
        values = {(r['graph_id'],r['method'],r['replicate']):r['return'] for r in rows}
        groups = [[values[g,METHODS[1],rep]-values[g,METHODS[0],rep] for rep in range(32)] for g in IDS]
        quality = dict(method_means={m:mean(values[g,m,rep] for g in IDS for rep in range(32)) for m in METHODS},
            paired_two_minus_one=paired_estimate(groups))
    ratios = {name:costs[METHODS[1]]['decision_work'].get(name,0)/costs[METHODS[0]]['decision_work'][name]
        if costs[METHODS[0]]['decision_work'].get(name,0) else None
        for name in ('action_value_evaluations','transition_outcomes','target_probability_evaluations')} if complete else None
    return dict(nodes=15,stratum='sparse',p=1.5/14,graph_ids=IDS,complete_quality_evidence=complete,
        quality=quality,costs=costs,two_over_one_work_ratios=ratios)


def block_check(case,rows,graph,certificates):
    errors, verification, work, environment = Counter(), Counter(), Counter(), Counter()
    decisions = 0
    completed = [row for row in rows if row['status']=='complete']
    if (case['nodes']!=graph['nodes'] or case['budget']!=2 or case['horizon']!=3 or case['requested_replicates']!=32
            or [r['replicate'] for r in rows]!=list(range(len(rows))) or case['trajectory_records']!=len(rows)
            or case['completed_replicates']!=len(completed) or case['total_return']!=sum(r['return'] for r in completed)):
        errors['block_binding_and_counts'] += 1
    limits = case['effective_limits']
    for row in rows:
        checked = v61.replay(row,graph,certificates)
        errors.update(checked['errors']); verification.update(checked['verification'])
        environment.update(checked['environment_work'])
        for index,decision in enumerate(row['decisions']):
            work.update(decision['decision_work']); decisions += 1
            crossed = work['action_value_evaluations']>=limits['max_planner_action_values'] or decisions>=limits['max_decisions']
            if crossed and not (row is rows[-1] and row['status']=='resource_limit' and index==len(row['decisions'])-1):
                errors['continued_after_charged_limit'] += 1
    full = case['status']=='complete'
    if ((full and (len(completed)!=32 or case['stop_reason'] is not None)) or (not full and (
            case['status']!='resource_limit' or len(rows)-len(completed)!=1 or not rows
            or rows[-1]['status']!='resource_limit' or rows[-1]['stop_reason']!=case['stop_reason']))):
        errors['block_status'] += 1
    stop = ('max_planner_action_values' if work['action_value_evaluations']>=limits['max_planner_action_values'] else
        'max_decisions' if decisions>=limits['max_decisions'] else
        'max_wall_seconds' if case['last_limit_check_seconds']>=limits['max_wall_seconds'] else None)
    if case['stop_reason']!=stop:
        errors['resource_limit_priority'] += 1
    if dict(work)!=case['decision_work'] or environment!=Counter(case['environment_work']) or decisions!=case['decision_records']:
        errors['block_work_accounting'] += 1
    for kind in ('decision','environment'):
        if not v61.close(case[kind+'_seconds'],sum(d[kind+'_seconds'] for r in rows for d in r['decisions'])):
            errors['block_time_sums'] += 1
    names = ('decision_seconds','environment_seconds','wall_seconds','prepare_gc_seconds','cleanup_seconds',
        'decision_total_seconds','block_seconds','serialization_seconds','last_limit_check_seconds')
    if (any(not v61.close(case.get(n),case.get(n)) or case[n]<0 for n in names)
            or not v61.close(case['decision_total_seconds'],case['decision_seconds']+case['cleanup_seconds'])
            or not v61.close(case['block_seconds'],case['wall_seconds']+case['cleanup_seconds'])
            or case['wall_seconds']+1e-10<case['decision_seconds']+case['environment_seconds']):
        errors['block_time_accounting'] += 1
    return dict(errors=dict(errors),verification=dict(verification))


def summarize(manifest,cases,rows,certificates,query_check,previous):
    started, errors, verification = perf_counter(), Counter(), Counter()
    graphs = manifest['graphs']
    if (manifest.get('schema')!='acfqp.lmta_graph_coverage.v63' or manifest.get('status')!='complete'
            or manifest.get('protocol')!=PROTOCOL or manifest.get('previous_source')!=PREVIOUS
            or manifest.get('calibration_source')!=CALIBRATION or manifest.get('cold_decisions') is not True
            or manifest.get('runtime',{}).get('gc_enabled') is not True):
        errors['manifest_protocol'] += 1
    if [g['graph_id'] for g in graphs]!=IDS or any(g.get(n)!=PROTOCOL[n] for g in graphs for n in ('nodes','stratum','expected_degree','p')):
        errors['new_graph_binding'] += 1
    for graph in graphs:
        edges = [tuple(edge) for edge in graph['edges']]
        if len(edges)!=len(set(edges)) or any(u==v or not (0<=u<15 and 0<=v<15) for u,v in edges):
            errors['directed_simple_graph_edges'] += 1
    historical = next(p for p in previous['panels'] if p['nodes']==15 and p['stratum']=='sparse')
    if previous.get('integrity',{}).get('passed') is not True or not historical['complete_quality_evidence']:
        errors['historical_sparse_panel_evidence'] += 1
    errors.update(query_check['errors'])
    if query_check['passed'] is not True:
        errors['independent_query_validation'] += 1
    errors.update(campaign_check(manifest,cases))
    grouped, graph_index = defaultdict(list), {g['graph_id']:g for g in graphs}
    for row in rows:
        grouped[row['graph_id'],row['method']].append(row)
    for case in cases:
        checked = block_check(case,grouped[case['graph_id'],case['method']],graph_index[case['graph_id']],certificates)
        errors.update(checked['errors']); verification.update(checked['verification'])
    if set(grouped)!={(c['graph_id'],c['method']) for c in cases}:
        errors['trajectory_roster'] += 1
    counts = dict(completed_blocks=len(cases),successful_blocks=sum(c['status']=='complete' for c in cases),
        resource_limited_blocks=sum(c['status']=='resource_limit' for c in cases),trajectory_records=len(rows),
        completed_trajectories=sum(r['status']=='complete' for r in rows),decision_records=sum(len(r['decisions']) for r in rows))
    if any(manifest.get(n)!=value for n,value in counts.items()):
        errors['manifest_counts'] += 1
    if manifest.get('new_graphs')!=64 or any(manifest.get(n)!=0 for n in ('new_full_policy_evaluations','new_RL_updates','new_MCTS_calls')):
        errors['new_work_scope'] += 1
    times = ('source_read_seconds','graph_generation_seconds','data_output_seconds','whole_runner_seconds','unexecuted_prepare_gc_seconds')
    if any(not v61.close(manifest.get(n),manifest.get(n)) or manifest[n]<0 for n in times):
        errors['runner_times'] += 1
    cohort = cohort_summary(cases,rows,not errors)
    total_work, total_env = Counter(), Counter()
    for case in cases:
        total_work.update(case['decision_work']); total_env.update(case['environment_work'])
    old_work = sum(c['decision_work']['action_value_evaluations'] for c in historical['costs'].values())
    comparison = None
    if cohort['complete_quality_evidence']:
        old, new = historical['quality']['paired_two_minus_one'], cohort['quality']['paired_two_minus_one']
        comparison = dict(graph_standard_error_ratio=new['graph_standard_error']/old['graph_standard_error'],
            fixed_panel_mc_standard_error_ratio=new['fixed_panel_mc_standard_error']/old['fixed_panel_mc_standard_error'],
            action_value_work_ratio=total_work['action_value_evaluations']/old_work)
    return dict(schema='acfqp.lmta_graph_coverage_analysis.v63',protocol=PROTOCOL,
        integrity=dict(passed=not errors,errors=dict(errors)),complete_trajectory_evidence=cohort['complete_quality_evidence'],
        observed_query_validation=query_check,cohort=cohort,historical_V62_sparse_15=dict(quality=historical['quality'],costs=historical['costs']),
        descriptive_comparison=comparison,terminal_reason=manifest['terminal_reason'],campaign_stop_reason=manifest['campaign_stop_reason'],
        skipped_blocks=manifest['skipped_blocks'],
        accounting=dict(**counts,decision_work=dict(total_work),environment_work=dict(total_env),
            independent_query_work=query_check['verification_work'],trajectory_verification=dict(verification),
            runner={n:manifest[n] for n in times},new_graphs=64,new_full_policy_evaluations=0,new_analysis_production_planner_calls=0,
            new_RL_updates=0,new_MCTS_calls=0,missing_complete_trajectories=4096-counts['completed_trajectories'],
            campaign_action_overshoot=max(0,total_work['action_value_evaluations']-4000000),
            campaign_runner_wall_overshoot=max(0.,manifest['whole_runner_seconds']-300.),
            limited_blocks=[dict(graph_id=c['graph_id'],method=c['method'],stop_scope=c['stop_scope'],stop_reason=c['stop_reason'],
                action_overshoot=max(0,c['decision_work']['action_value_evaluations']-c['effective_limits']['max_planner_action_values']),
                trigger_decision_work=grouped[c['graph_id'],c['method']][-1]['decisions'][-1]['decision_work'])
                for c in cases if c['status']=='resource_limit'],
            block_times={n:sum(c[n] for c in cases) for n in ('decision_seconds','environment_seconds','wall_seconds','prepare_gc_seconds','cleanup_seconds','block_seconds','serialization_seconds')},
            analysis_seconds_before_serialization=perf_counter()-started),
        uncertainty_scope='Primary: 64 new-graph paired means, df63 two-sided 95 percent t interval. Four-comparison reference and fixed-panel Monte Carlo intervals are separate.',
        limitations='No exact full-policy values, pooling with old graphs, or sampling-efficiency claim. Any limited or skipped block makes whole-cohort quality null. Historical costs and uncertainty comparisons are descriptive. Campaign caps cover the main run; validation and development are charged separately.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'reports/lmta_graph_coverage_v63')
    args = parser.parse_args()
    with (args.output/'analysis_attempt.json').open('x') as attempt:
        started, error, work, stage = perf_counter(), None, Counter(), 'read'
        try:
            manifest = json.loads((args.output/'manifest.json').read_text())
            cases, rows = v61.read_jsonl(args.output/'cases.jsonl'), v61.read_jsonl(args.output/'trajectories.jsonl')
            stage = 'query_certificates'
            with (args.output/'certificates.jsonl').open('x') as output:
                certificates, checked = v62.certify(rows,manifest['graphs'],output,work)
            stage = 'replay_and_summary'
            previous = json.loads((ROOT/PREVIOUS/'analysis.json').read_text())
            analysis = summarize(manifest,cases,rows,certificates,checked,previous)
            analysis['accounting']['analysis_wall_seconds_including_reads'] = perf_counter()-started
            (args.output/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
            stage = 'complete'
            print(json.dumps(dict(integrity=analysis['integrity'],complete=analysis['complete_trajectory_evidence'])))
        except Exception as caught:
            error = f'{type(caught).__name__}: {caught}'
            raise
        finally:
            attempt.write(json.dumps(dict(wall_seconds=perf_counter()-started,exit_code=int(error is not None),
                error=error,stage=stage,independent_query_work=dict(work)),indent=2)+'\n')


if __name__=='__main__':
    main()
