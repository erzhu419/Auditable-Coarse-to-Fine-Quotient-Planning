"""Certify observed short-window queries and summarize new-graph paired trajectories."""
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


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v61 = load('trajectory_physics_v61', 'analyze_lmta_trajectory_v61.py')
checker = load('trajectory_query_v62', 'lmta_trajectory_certificate_v62.py')
METHODS, LIMITS = v61.METHODS, v61.LIMITS
PANELS = [dict(nodes=n, stratum=s, expected_degree=d, p=d/(n-1), seeds=list(range(base,base+16)))
    for n,s,d,base in ((13,'sparse',1.5,620000),(13,'dense',4.5,620100),
                       (15,'sparse',1.5,620200),(15,'dense',4.5,620300))]
IDS = [g for panel in PANELS for g in panel['seeds']]
PROTOCOL = dict(budget=2,horizon=3,replicates=128,methods=METHODS,panels=PANELS,
    seed_base=61000000,seed_graph_stride=1000,limits=LIMITS,primary_family_size=4,primary_alpha=.05)
PREVIOUS = 'reports/lmta_trajectory_v61'
FIELDS = ('selected','planned_value','root_action_values','decision_work')


def graph_errors(graphs):
    errors = Counter()
    if [g['graph_id'] for g in graphs] != IDS:
        errors['graph_roster'] += 1
    panels = {g:panel for panel in PANELS for g in panel['seeds']}
    for graph in graphs:
        panel = panels.get(graph['graph_id'])
        if panel is None or any(graph.get(n) != panel[n] for n in ('nodes','stratum','expected_degree','p')):
            errors['graph_parameters'] += 1
        edges = [tuple(edge) for edge in graph['edges']]
        if len(edges) != len(set(edges)) or any(u==v or not (0<=u<graph['nodes'] and 0<=v<graph['nodes']) for u,v in edges):
            errors['directed_simple_graph_edges'] += 1
    return errors


def certify(rows, graphs, output, work):
    """Verify each observed query once; repeated queries must match its frozen result."""
    graph_index = {g['graph_id']:g for g in graphs}
    representatives, valid, errors, maximum = {}, {}, Counter(), 0.
    for row in rows:
        for decision in row['decisions']:
            identity = v61.key(dict(decision,graph_id=row['graph_id'],method=row['method']))
            reference = {name:decision[name] for name in FIELDS}
            if identity in representatives:
                if reference != representatives[identity]:
                    errors['repeated_query_result_differs'] += 1
                continue
            representatives[identity] = reference
            checked = checker.verify_decision(decision,graph_index[row['graph_id']],row['method'])
            work.update(checked['verification_work'])
            errors.update(checked['errors'])
            maximum = max(maximum,checked['maximum_Q_difference'])
            if checked['passed']:
                valid[identity] = reference
            output.write(json.dumps(dict(graph_id=identity[0],method=identity[1],statuses=list(identity[2]),
                remaining_budget=identity[3],remaining_days=identity[4],**checked))+'\n')
    return valid, dict(passed=not errors,errors=dict(errors),unique_queries=len(representatives),
        valid_queries=len(valid),maximum_Q_difference=maximum,verification_work=dict(work))


def block_check(case, rows, graph, certificates):
    errors, verification, work, environment = Counter(), Counter(), Counter(), Counter()
    decisions = 0
    completed = [row for row in rows if row['status']=='complete']
    if (case['nodes'] != graph['nodes'] or case['budget'] != 2 or case['horizon'] != 3
            or case['requested_replicates'] != 128 or [r['replicate'] for r in rows] != list(range(len(rows)))
            or case['trajectory_records'] != len(rows) or case['completed_replicates'] != len(completed)
            or case['total_return'] != sum(r['return'] for r in completed)):
        errors['block_binding_and_counts'] += 1
    for row in rows:
        checked = v61.replay(row,graph,certificates)
        errors.update(checked['errors']); verification.update(checked['verification'])
        environment.update(checked['environment_work'])
        for index, decision in enumerate(row['decisions']):
            work.update(decision['decision_work']); decisions += 1
            crossed = work['action_value_evaluations'] >= LIMITS['max_planner_action_values'] or decisions >= LIMITS['max_decisions']
            if crossed and not (row is rows[-1] and row['status']=='resource_limit' and index==len(row['decisions'])-1):
                errors['continued_after_charged_limit'] += 1
    full = case['status']=='complete'
    if ((full and (len(completed)!=128 or case['stop_reason'] is not None))
            or (not full and (case['status']!='resource_limit' or len(rows)-len(completed)!=1 or not rows
                or rows[-1]['status']!='resource_limit' or rows[-1]['stop_reason']!=case['stop_reason']))):
        errors['block_status'] += 1
    stop = ('max_planner_action_values' if work['action_value_evaluations']>=LIMITS['max_planner_action_values'] else
        'max_decisions' if decisions>=LIMITS['max_decisions'] else
        'max_wall_seconds' if case['last_limit_check_seconds']>=LIMITS['max_wall_seconds'] else None)
    if case['stop_reason'] != stop:
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


def paired_estimate(groups):
    graph_means = [mean(values) for values in groups]
    center, count = mean(graph_means), len(groups)
    se = stdev(graph_means)/math.sqrt(count)
    mc_se = math.sqrt(sum(variance(values)/len(values) for values in groups)/count**2)
    interval = lambda z,s: [center-z*s,center+z*s]
    return dict(mean=center,graph_standard_error=se,degrees_of_freedom=count-1,
        graph_nominal_95_interval=interval(float(t.ppf(.975,count-1)),se),
        graph_simultaneous_interval=interval(float(t.ppf(1-.05/8,count-1)),se),
        fixed_panel_mc_standard_error=mc_se,fixed_panel_mc_nominal_95_interval=interval(v61.Z95,mc_se),
        graph_means=graph_means)


def panel_summary(panel, cases, rows, integrity):
    selected = [case for case in cases if case['graph_id'] in panel['seeds']]
    complete = integrity and len(selected)==32 and all(case['status']=='complete' for case in selected)
    costs = {}
    for method in METHODS:
        blocks = [case for case in selected if case['method']==method]
        work, environment = Counter(), Counter()
        for case in blocks:
            work.update(case['decision_work']); environment.update(case['environment_work'])
        costs[method] = dict(decision_work=dict(work),environment_work=dict(environment),
            completed_trajectories=sum(case['completed_replicates'] for case in blocks),
            resource_limited_blocks=sum(case['status']=='resource_limit' for case in blocks),
            decision_seconds=sum(case['decision_seconds'] for case in blocks),
            mean_trajectory_work={name:work[name]/2048 for name in work} if complete else None)
    quality = None
    if complete:
        values = {(r['graph_id'],r['method'],r['replicate']):r['return'] for r in rows if r['graph_id'] in panel['seeds']}
        groups = [[values[g,METHODS[1],rep]-values[g,METHODS[0],rep] for rep in range(128)] for g in panel['seeds']]
        quality = dict(method_means={m:mean(values[g,m,rep] for g in panel['seeds'] for rep in range(128)) for m in METHODS},
            paired_two_minus_one=paired_estimate(groups))
    ratios = {name:costs[METHODS[1]]['decision_work'].get(name,0)/costs[METHODS[0]]['decision_work'][name]
        if costs[METHODS[0]]['decision_work'].get(name,0) else None
        for name in ('action_value_evaluations','transition_outcomes','target_probability_evaluations')} if complete else None
    return dict(nodes=panel['nodes'],stratum=panel['stratum'],p=panel['p'],graph_ids=panel['seeds'],
        complete_quality_evidence=complete,quality=quality,costs=costs,two_over_one_work_ratios=ratios)


def summarize(manifest,cases,rows,certificates,query_check,previous):
    started, errors, verification = perf_counter(), Counter(), Counter()
    graphs = manifest['graphs']; errors.update(graph_errors(graphs))
    if (manifest.get('schema')!='acfqp.lmta_trajectory_scale.v62' or manifest.get('status')!='complete'
            or manifest.get('protocol')!=PROTOCOL or manifest.get('previous_source')!=PREVIOUS
            or manifest.get('cold_decisions') is not True or manifest.get('runtime',{}).get('gc_enabled') is not True):
        errors['manifest_protocol'] += 1
    if previous.get('integrity',{}).get('passed') is not True or previous.get('complete_trajectory_evidence') is not True:
        errors['historical_evidence'] += 1
    errors.update(query_check['errors'])
    if query_check['passed'] is not True:
        errors['independent_query_validation'] += 1
    expected_order = [(g,m) for index,g in enumerate(IDS) for m in (METHODS if index%2==0 else METHODS[::-1])]
    if [(c['graph_id'],c['method']) for c in cases] != expected_order:
        errors['case_roster_and_order'] += 1
    grouped, graph_index = defaultdict(list), {g['graph_id']:g for g in graphs}
    for row in rows:
        grouped[row['graph_id'],row['method']].append(row)
    for case in cases:
        checked = block_check(case,grouped[case['graph_id'],case['method']],graph_index[case['graph_id']],certificates)
        errors.update(checked['errors']); verification.update(checked['verification'])
    if set(grouped) != set(expected_order):
        errors['trajectory_roster'] += 1
    counts = dict(completed_blocks=len(cases),successful_blocks=sum(c['status']=='complete' for c in cases),
        resource_limited_blocks=sum(c['status']=='resource_limit' for c in cases),trajectory_records=len(rows),
        completed_trajectories=sum(r['status']=='complete' for r in rows),decision_records=sum(len(r['decisions']) for r in rows))
    if any(manifest.get(n)!=value for n,value in counts.items()):
        errors['manifest_counts'] += 1
    if manifest.get('new_graphs')!=64 or any(manifest.get(n)!=0 for n in ('new_full_policy_evaluations','new_RL_updates','new_MCTS_calls')):
        errors['new_work_scope'] += 1
    times = ('source_read_seconds','graph_generation_seconds','data_output_seconds','whole_runner_seconds')
    if any(not v61.close(manifest.get(n),manifest.get(n)) or manifest[n]<0 for n in times):
        errors['runner_times'] += 1
    panels = [panel_summary(panel,cases,rows,not errors) for panel in PANELS]
    total_work, total_env = Counter(), Counter()
    for case in cases:
        total_work.update(case['decision_work']); total_env.update(case['environment_work'])
    historical = [dict(nodes=p['nodes'],stratum=p['stratum'],mean_trajectory_work={m:{n:v['actual']/2048
        for n,v in p['work'][m].items()} for m in METHODS}) for p in previous['panels']]
    return dict(schema='acfqp.lmta_trajectory_scale_analysis.v62',protocol=PROTOCOL,
        integrity=dict(passed=not errors,errors=dict(errors)),complete_trajectory_evidence=not errors and counts['successful_blocks']==128,
        observed_query_validation=query_check,panels=panels,historical_V61_work=historical,
        uncertainty_scope='Primary: graph-level paired t intervals, 16 new graphs per panel, Bonferroni four comparisons. Fixed-panel Monte Carlo intervals are secondary.',
        accounting=dict(**counts,decision_work=dict(total_work),environment_work=dict(total_env),
            independent_query_work=query_check['verification_work'],trajectory_verification=dict(verification),
            runner={n:manifest[n] for n in times},new_graphs=64,new_full_policy_evaluations=0,new_analysis_production_planner_calls=0,
            new_RL_updates=0,new_MCTS_calls=0,missing_complete_trajectories=16384-counts['completed_trajectories'],
            block_times={n:sum(c[n] for c in cases) for n in ('decision_seconds','environment_seconds','wall_seconds','prepare_gc_seconds','cleanup_seconds','block_seconds','serialization_seconds')},
            analysis_seconds_before_serialization=perf_counter()-started),
        limitations='New graphs have no exact full-policy values. Incomplete panels retain costs with null quality; none are completed by dropping graphs. Historical work comparisons are descriptive and timings are not paired speedups.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'reports/lmta_trajectory_scale_v62')
    args = parser.parse_args()
    with (args.output/'analysis_attempt.json').open('x') as attempt:
        started, error, work, stage = perf_counter(), None, Counter(), 'read'
        try:
            manifest = json.loads((args.output/'manifest.json').read_text())
            cases, rows = v61.read_jsonl(args.output/'cases.jsonl'), v61.read_jsonl(args.output/'trajectories.jsonl')
            stage = 'query_certificates'
            with (args.output/'certificates.jsonl').open('x') as output:
                certificates, checked = certify(rows,manifest['graphs'],output,work)
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
