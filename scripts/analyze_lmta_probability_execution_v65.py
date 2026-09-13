"""Independent new-graph query, trajectory, and actual execution cost evidence."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import importlib.util
import json
import math
from pathlib import Path
from statistics import mean, stdev
from time import perf_counter

from scipy.stats import t

ROOT = Path(__file__).resolve().parents[1]


def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


v63=load('execution_block_v63','analyze_lmta_graph_coverage_v63.py')
v64=load('execution_preservation_v64','analyze_lmta_probability_reuse_v64.py')
v61,checker=v63.v61,v63.v62.checker
VARIANTS,IDS=['BASELINE','REUSE'],list(range(650000,650064))
METHOD='LOOKAHEAD_2_ANALYTIC'
PREVIOUS='reports/lmta_probability_reuse_v64'
BLOCK_LIMITS=dict(max_planner_action_values=2000000,max_decisions=100000,max_wall_seconds=60.)
CAMPAIGN_LIMITS=dict(max_planner_action_values=6000000,max_wall_seconds=300.)
PROTOCOL=dict(nodes=15,stratum='sparse',expected_degree=1.5,p=1.5/14,graph_ids=IDS,budget=2,horizon=3,
    replicates=32,method=METHOD,variants=VARIANTS,seed_base=61000000,seed_graph_stride=1000,
    limits=BLOCK_LIMITS,campaign_limits=CAMPAIGN_LIMITS,primary_alpha=.05)
FIELDS=(*v64.FIELDS,'decision_work')


def canonical(decision,variant):
    result=dict(decision)
    if variant=='REUSE':
        work={n:value for n,value in decision['decision_work'].items() if n not in v64.TERMINAL}
        work['target_probability_evaluations']+=work['analytic_probability_terms']-decision['decision_work']['terminal_probability_cache_misses']
        result['decision_work']=work
    return result


def certify(rows,graphs,output,work):
    graph_index={g['graph_id']:g for g in graphs}
    representatives,certificates=defaultdict(list),{variant:{} for variant in VARIANTS}
    errors,queries,shared_differences,maximum=Counter(),0,0,0.
    for row in rows:
        for decision in row['decisions']:
            identity=v61.key(dict(decision,graph_id=row['graph_id'],method=row['method']))
            normalized=canonical(decision,row['variant'])
            if row['variant']=='REUSE':
                checked=v64.preserved_query(decision,normalized)
                errors.update(checked['errors'])
            reference={n:normalized[n] for n in FIELDS}
            matching=next((old for old in representatives[identity] if old['reference']==reference),None)
            if matching is None:
                if representatives[identity]: shared_differences+=1
                checked=checker.verify_decision(normalized,graph_index[row['graph_id']],row['method'])
                work.update(checked['verification_work']);errors.update(checked['errors']);queries+=1
                maximum=max(maximum,checked['maximum_Q_difference'])
                matching=dict(reference=reference,passed=checked['passed'])
                representatives[identity].append(matching)
                output.write(json.dumps(dict(graph_id=row['graph_id'],method=row['method'],variant=row['variant'],
                    statuses=decision['statuses'],remaining_budget=decision['remaining_budget'],remaining_days=decision['remaining_days'],
                    canonical_decision_work=normalized['decision_work'],**checked))+'\n')
            if matching['passed']:
                actual={n:decision[n] for n in FIELDS}
                old=certificates[row['variant']].get(identity)
                if old is not None and old!=actual: errors['within_variant_repeated_query_changed']+=1
                certificates[row['variant']][identity]=actual
    return certificates,dict(passed=not errors,errors=dict(errors),distinct_input_queries=len(representatives),
        independent_queries=queries,distinct_result_differences=shared_differences,maximum_Q_difference=maximum,
        verification_work=dict(work),counter_normalization='REUSE removes eight terminal fields and restores target count as actual + analytic terms - cache misses before independent V62 validation.')


def trajectory_preservation(rows):
    paired=defaultdict(dict)
    for row in rows: paired[row['graph_id'],row['replicate']][row['variant']]=row
    errors=Counter()
    for pair in paired.values():
        if set(pair)!=set(VARIANTS): errors['unpaired_trajectory']+=1;continue
        left,right=pair['BASELINE'],pair['REUSE']
        if any(left[n]!=right[n] for n in ('status','stop_reason','seed','return')): errors['trajectory_outcome']+=1
        if len(left['decisions'])!=len(right['decisions']): errors['decision_length']+=1
        for a,b in zip(left['decisions'],right['decisions']):
            state_fields=('statuses','remaining_budget','remaining_days','next_statuses','reward')
            if any(a[n]!=b[n] for n in state_fields): errors['trajectory_state_or_reward']+=1
            if any(a[n]!=b[n] for n in v64.FIELDS): errors['exact_action_or_Q']+=1
            if canonical(b,'REUSE')['decision_work']!=a['decision_work']: errors['logical_work']+=1
    return dict(preserved=not errors and len(paired)==2048,errors=dict(errors),paired_trajectory_keys=len(paired))


def cost_summary(cases):
    points=[]
    for index,g in enumerate(IDS):
        pair={c['variant']:c for c in cases if c['graph_id']==g}
        costs={v:sum(pair[v][n] for n in ('prepare_gc_seconds','wall_seconds','cleanup_seconds','serialization_seconds')) for v in VARIANTS}
        decision={v:pair[v]['decision_total_seconds'] for v in VARIANTS}
        points.append(dict(graph_id=g,first_variant=VARIANTS[index%2],full_costs=costs,
            decision_costs=decision,full_cost_ratio=costs['REUSE']/costs['BASELINE']))
    logs=[math.log(p['full_cost_ratio']) for p in points]
    center,se=mean(logs),stdev(logs)/8
    half=float(t.ppf(.975,63))*se
    totals={v:sum(p['full_costs'][v] for p in points) for v in VARIANTS}
    decision={v:sum(p['decision_costs'][v] for p in points) for v in VARIANTS}
    orders=[]
    for first in VARIANTS:
        group=[p for p in points if p['first_variant']==first]
        costs={v:sum(p['full_costs'][v] for p in group) for v in VARIANTS}
        orders.append(dict(first_variant=first,graphs=len(group),full_costs=costs,ratio=costs['REUSE']/costs['BASELINE']))
    return dict(full_costs=totals,full_cost_ratio=totals['REUSE']/totals['BASELINE'],
        decision_costs=decision,decision_cost_ratio=decision['REUSE']/decision['BASELINE'],
        paired_geometric_cost_ratio=math.exp(center),paired_log_ratio_standard_error=se,
        paired_geometric_ratio_95_interval=[math.exp(center-half),math.exp(center+half)],degrees_of_freedom=63,
        faster_graphs=sum(p['full_cost_ratio']<1 for p in points),tied_graphs=sum(p['full_cost_ratio']==1 for p in points),
        slower_graphs=sum(p['full_cost_ratio']>1 for p in points),order_strata=orders,per_graph=points)


def campaign_check(manifest,cases):
    errors,used,last=Counter(),0,0.
    order=[(g,v) for index,g in enumerate(IDS) for v in (VARIANTS if index%2==0 else VARIANTS[::-1])]
    if [(c['graph_id'],c['variant']) for c in cases]!=order[:len(cases)]: errors['executed_prefix_roster']+=1
    if manifest['skipped_blocks']!=[dict(graph_id=g,variant=v) for g,v in order[len(cases):]]: errors['skipped_suffix_roster']+=1
    for index,case in enumerate(cases):
        elapsed=case['campaign_elapsed_before']
        remaining=dict(max_planner_action_values=6000000-used,max_wall_seconds=300.-elapsed)
        expected=dict(BLOCK_LIMITS,**{n:min(BLOCK_LIMITS[n],value) for n,value in remaining.items()})
        if (case['campaign_actions_before']!=used or not v61.close(elapsed,elapsed) or elapsed<last
                or any(value<=0 for value in remaining.values())
                or any(not v61.close(case['effective_limits'].get(n),value) for n,value in expected.items())):
            errors['effective_campaign_limits']+=1
        stop=case['stop_reason'];scope=None if stop is None else ('campaign' if stop in remaining and remaining[stop]<=BLOCK_LIMITS[stop] else 'block')
        if case['stop_scope']!=scope or (scope=='campaign' and index!=len(cases)-1): errors['stop_scope']+=1
        used+=case['decision_work']['action_value_evaluations'];last=elapsed
    if manifest['campaign_action_values']!=used: errors['campaign_action_sum']+=1
    reason,elapsed=manifest['campaign_stop_reason'],manifest['campaign_elapsed_at_stop']
    if manifest['terminal_reason']=='finished_roster':
        if len(cases)!=128 or reason is not None or elapsed is not None or any(c['stop_scope']=='campaign' for c in cases): errors['finished_roster_terminal']+=1
    elif manifest['terminal_reason']=='campaign_resource_limit':
        if (not v61.close(elapsed,elapsed) or elapsed<last or elapsed>manifest['whole_runner_seconds']+1e-10
                or reason not in CAMPAIGN_LIMITS or (reason=='max_planner_action_values' and used<6000000)
                or (reason=='max_wall_seconds' and (elapsed<300. or used>=6000000))
                or (cases and cases[-1]['stop_scope']=='campaign' and reason!=cases[-1]['stop_reason'])): errors['campaign_terminal']+=1
    else: errors['terminal_reason']+=1
    return errors


def summarize(manifest,cases,rows,certificates,query_check,previous):
    started,errors,verification=perf_counter(),Counter(),Counter()
    graphs=manifest['graphs']
    if (manifest.get('schema')!='acfqp.lmta_probability_execution.v65' or manifest.get('status')!='complete'
            or manifest.get('protocol')!=PROTOCOL or manifest.get('previous_source')!=PREVIOUS
            or manifest.get('cold_decisions') is not True or manifest.get('runtime',{}).get('gc_enabled') is not True): errors['manifest_protocol']+=1
    if [g['graph_id'] for g in graphs]!=IDS or any(g.get(n)!=PROTOCOL[n] for g in graphs for n in ('nodes','stratum','expected_degree','p')): errors['new_graph_binding']+=1
    for graph in graphs:
        edges=[tuple(edge) for edge in graph['edges']]
        if len(edges)!=len(set(edges)) or any(u==v or not (0<=u<15 and 0<=v<15) for u,v in edges): errors['directed_simple_graph_edges']+=1
    if previous.get('integrity',{}).get('passed') is not True or not previous['action_and_value_preservation'] or not previous['complete_performance_evidence']: errors['historical_evidence']+=1
    errors.update(query_check['errors'])
    if query_check['passed'] is not True: errors['independent_query_validation']+=1
    errors.update(campaign_check(manifest,cases))
    grouped,graph_index=defaultdict(list),{g['graph_id']:g for g in graphs}
    for row in rows:
        if row['method']!=METHOD or row['variant'] not in VARIANTS: errors['trajectory_identity']+=1
        grouped[row['graph_id'],row['variant']].append(row)
    for case in cases:
        if case['method']!=METHOD: errors['case_method']+=1
        checked=v63.block_check(case,grouped[case['graph_id'],case['variant']],graph_index[case['graph_id']],certificates[case['variant']])
        errors.update(checked['errors']);verification.update(checked['verification'])
    if set(grouped)!={(c['graph_id'],c['variant']) for c in cases}: errors['trajectory_roster']+=1
    counts=dict(completed_blocks=len(cases),successful_blocks=sum(c['status']=='complete' for c in cases),
        resource_limited_blocks=sum(c['status']=='resource_limit' for c in cases),trajectory_records=len(rows),
        completed_trajectories=sum(r['status']=='complete' for r in rows),decision_records=sum(len(r['decisions']) for r in rows))
    if any(manifest.get(n)!=value for n,value in counts.items()): errors['manifest_counts']+=1
    if manifest.get('new_graphs')!=64 or any(manifest.get(n)!=0 for n in ('new_full_policy_evaluations','new_RL_updates','new_MCTS_calls')): errors['new_work_scope']+=1
    times=('source_read_seconds','source_snapshot_seconds','graph_generation_seconds','data_output_seconds','whole_runner_seconds','unexecuted_prepare_gc_seconds')
    if any(not v61.close(manifest.get(n),manifest.get(n)) or manifest[n]<0 for n in times): errors['runner_times']+=1
    complete=not errors and len(cases)==128 and counts['successful_blocks']==128 and len(rows)==4096
    paired=trajectory_preservation(rows)
    preserved=complete and paired['preserved'] and query_check['distinct_result_differences']==0
    total_work,total_env=Counter(),Counter()
    variant_costs={}
    for variant in VARIANTS:
        selected=[c for c in cases if c['variant']==variant]
        work,environment=Counter(),Counter()
        for case in selected: work.update(case['decision_work']);environment.update(case['environment_work'])
        total_work.update(work);total_env.update(environment)
        variant_costs[variant]=dict(decision_work=dict(work),environment_work=dict(environment),
            times={n:sum(c[n] for c in selected) for n in ('decision_seconds','environment_seconds','wall_seconds','prepare_gc_seconds','cleanup_seconds','decision_total_seconds','block_seconds','serialization_seconds')})
    quality={v:mean(r['return'] for r in rows if r['variant']==v) for v in VARIANTS} if complete else None
    return dict(schema='acfqp.lmta_probability_execution_analysis.v65',protocol=PROTOCOL,
        integrity=dict(passed=not errors,errors=dict(errors)),complete_trajectory_evidence=complete,
        observed_query_validation=query_check,paired_trajectory_validation=paired,
        action_and_trajectory_preservation=preserved if complete else None,
        complete_performance_evidence=preserved,quality=quality,cost_comparison=cost_summary(cases) if preserved else None,
        historical_V64_timing=previous['timing'][METHOD],terminal_reason=manifest['terminal_reason'],
        campaign_stop_reason=manifest['campaign_stop_reason'],skipped_blocks=manifest['skipped_blocks'],
        accounting=dict(**counts,decision_work=dict(total_work),environment_work=dict(total_env),variant_costs=variant_costs,
            independent_query_work=query_check['verification_work'],trajectory_verification=dict(verification),
            runner={n:manifest[n] for n in times},new_graphs=64,new_full_policy_evaluations=0,new_analysis_production_planner_calls=0,
            primary_component_seconds=sum(c[n] for c in cases for n in ('prepare_gc_seconds','wall_seconds','cleanup_seconds','serialization_seconds')),
            common_unallocated_runner_seconds=manifest['whole_runner_seconds']-sum(c[n] for c in cases for n in ('prepare_gc_seconds','wall_seconds','cleanup_seconds','serialization_seconds')),
            new_RL_updates=0,new_MCTS_calls=0,missing_complete_trajectories=4096-counts['completed_trajectories'],
            campaign_action_overshoot=max(0,total_work['action_value_evaluations']-6000000),
            campaign_runner_wall_overshoot=max(0.,manifest['whole_runner_seconds']-300.),
            limited_blocks=[dict(graph_id=c['graph_id'],variant=c['variant'],stop_scope=c['stop_scope'],stop_reason=c['stop_reason'],
                action_overshoot=max(0,c['decision_work']['action_value_evaluations']-c['effective_limits']['max_planner_action_values']),
                trigger_decision_work=grouped[c['graph_id'],c['variant']][-1]['decisions'][-1]['decision_work'])
                for c in cases if c['status']=='resource_limit'],
            analysis_seconds_before_serialization=perf_counter()-started),
        limitations='Counter normalization is for independent logical-work verification; original actual counters remain charged. Paired costs include preparation, execution, cleanup and trajectory serialization. Case/manifest output and source/graph setup remain common runner costs. One execution pair per new graph does not repeat V64 six-round stability or establish exact full-policy values. The graph-level log-cost t interval is approximate and descriptive; limited/skipped cohorts have null quality and performance.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'reports/lmta_probability_execution_v65')
    args=parser.parse_args()
    with (args.output/'analysis_attempt.json').open('x') as attempt:
        started,error,work,stage=perf_counter(),None,Counter(),'read'
        try:
            manifest=json.loads((args.output/'manifest.json').read_text())
            cases,rows=v61.read_jsonl(args.output/'cases.jsonl'),v61.read_jsonl(args.output/'trajectories.jsonl')
            stage='query_certificates'
            with (args.output/'certificates.jsonl').open('x') as output:
                certificates,checked=certify(rows,manifest['graphs'],output,work)
            stage='replay_and_summary'
            previous=json.loads((ROOT/PREVIOUS/'analysis.json').read_text())
            analysis=summarize(manifest,cases,rows,certificates,checked,previous)
            analysis['accounting']['analysis_wall_seconds_including_reads']=perf_counter()-started
            (args.output/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
            stage='complete'
            print(json.dumps(dict(integrity=analysis['integrity'],complete=analysis['complete_trajectory_evidence'],preserved=analysis['action_and_trajectory_preservation'],performance=analysis['complete_performance_evidence'])))
        except Exception as caught:
            error=f'{type(caught).__name__}: {caught}';raise
        finally:
            attempt.write(json.dumps(dict(wall_seconds=perf_counter()-started,exit_code=int(error is not None),
                error=error,stage=stage,independent_query_work=dict(work)),indent=2)+'\n')


if __name__=='__main__': main()
