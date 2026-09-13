"""Check exact retained-query preservation and paired cold-planning cost evidence."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
from statistics import mean, median
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
METHODS = ['LOOKAHEAD_1_ANALYTIC','LOOKAHEAD_2_ANALYTIC']
VARIANTS = ['BASELINE','REUSE']
IDS = list(range(630000,630064))
PREVIOUS = 'reports/lmta_graph_coverage_v63'
LIMITS = dict(max_planner_action_values=2000000,max_queries=100000,max_wall_seconds=60.)
PROTOCOL = dict(rounds=6,methods=METHODS,variants=VARIANTS,limits=LIMITS)
FIELDS = ('selected','planned_value','root_action_values')
LOGICAL = ('planner_calls','dp_states','action_value_evaluations','kernel_builds','kernel_cache_hits',
    'transition_outcomes','score_node_evaluations','immediate_expectation_terms','bellman_expectation_terms',
    'forced_choice','analytic_expectation_calls','analytic_probability_terms')
TERMINAL = ('terminal_base_parent_checks','terminal_base_states','terminal_selected_edge_checks',
    'terminal_selected_increments','terminal_probability_lookups','terminal_probability_cache_hits',
    'terminal_probability_cache_misses','terminal_zero_source_terms')


def occurrence(row):
    return row['graph_id'],row['method'],row['query_index']


def source_queries(trajectories):
    counts, result = Counter(), []
    for row in trajectories:
        identity = row['graph_id'],row['method']
        for decision in row['decisions']:
            result.append(dict(decision,graph_id=identity[0],method=identity[1],query_index=counts[identity]))
            counts[identity] += 1
    return result


def preserved_query(candidate,source):
    errors = Counter()
    for name in ('statuses','remaining_budget','remaining_days'):
        if candidate[name]!=source[name]:
            errors['source_query_binding'] += 1
    output_matches = all(candidate[name]==source[name] for name in FIELDS)
    left,right = candidate['decision_work'],source['decision_work']
    logical_matches = all(left.get(name,0)==right.get(name,0) for name in LOGICAL)
    if (any(not isinstance(v,int) or v<0 for v in left.values())
            or any(name not in left for name in TERMINAL)
            or left['terminal_probability_cache_hits']+left['terminal_probability_cache_misses']!=left['terminal_probability_lookups']
            or left['terminal_probability_lookups']+left['terminal_zero_source_terms']!=left['analytic_probability_terms']
            or left['target_probability_evaluations']!=right['target_probability_evaluations']-right['analytic_probability_terms']+left['terminal_probability_cache_misses']
            or left['terminal_selected_increments']>left['terminal_selected_edge_checks']):
        errors['probability_reuse_accounting'] += 1
    reported = Counter()
    if not output_matches: reported['retained_output_changed'] += 1
    if not logical_matches: reported['logical_search_changed'] += 1
    if errors: reported['probability_work_partition'] += 1
    return dict(errors=dict(errors),output_preserved=output_matches,logical_work_preserved=logical_matches,
        comparison_errors=dict(reported))


def close(a,b):
    return isinstance(a,(int,float)) and math.isfinite(a) and math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-10)


def sum_work(rows,name='decision_work'):
    result = Counter()
    for row in rows:
        result.update(row[name])
    return dict(result)


def time_summary(blocks):
    """Paired sums use every replayed occurrence; graph states are not reweighted."""
    result = {}
    for method in METHODS:
        selected = [b for b in blocks if b['method']==method]
        rounds = []
        for round_id in range(6):
            totals = {variant:sum(b['decision_total_seconds'] for b in selected if b['round']==round_id and b['variant']==variant)
                for variant in VARIANTS}
            rounds.append(dict(round=round_id,seconds=totals,reuse_over_baseline=totals['REUSE']/totals['BASELINE']))
        ratios = [r['reuse_over_baseline'] for r in rounds]
        order = []
        for first in VARIANTS:
            members = [b for b in selected if (b['variant'] if b['position']==0 else VARIANTS[1-VARIANTS.index(b['variant'])])==first]
            totals = {variant:sum(b['decision_total_seconds'] for b in members if b['variant']==variant) for variant in VARIANTS}
            order.append(dict(first_variant=first,paired_blocks=len(members)//2,seconds=totals,
                reuse_over_baseline=totals['REUSE']/totals['BASELINE']))
        result[method] = dict(rounds=rounds,ratio_median=median(ratios),ratio_minimum=min(ratios),ratio_maximum=max(ratios),
            order_strata=order,work={variant:sum_work([b for b in selected if b['variant']==variant]) for variant in VARIANTS})
    return result


def block_check(block,expected):
    errors = Counter()
    count = block['completed_queries']
    if block['requested_queries']!=96 or not 0<count<=96:
        errors['block_query_count'] += 1
    work = sum_work(expected[:count])
    if Counter(work)!=Counter(block['decision_work']):
        errors['block_work_sum'] += 1
    stop = ('max_planner_action_values' if work.get('action_value_evaluations',0)>=LIMITS['max_planner_action_values'] else
        'max_queries' if count>=LIMITS['max_queries'] else
        'max_wall_seconds' if block['last_limit_check_seconds']>=LIMITS['max_wall_seconds'] else None)
    if block['stop_reason']!=stop or block['status']!=('complete' if stop is None else 'resource_limit') or (stop is None and count!=96):
        errors['block_stop'] += 1
    actions = 0
    for row in expected[:max(0,count-1)]:
        actions += row['decision_work']['action_value_evaluations']
        if actions>=LIMITS['max_planner_action_values']:
            errors['continued_after_paid_limit'] += 1
    names = ('decision_seconds','loop_seconds','bookkeeping_seconds','prepare_gc_seconds','cleanup_seconds',
        'decision_total_seconds','block_seconds','serialization_seconds','last_limit_check_seconds')
    if (any(not close(block.get(n),block.get(n)) or block[n]<0 for n in names)
            or not close(block['bookkeeping_seconds'],block['loop_seconds']-block['decision_seconds'])
            or not close(block['decision_total_seconds'],block['decision_seconds']+block['cleanup_seconds'])
            or not close(block['block_seconds'],block['loop_seconds']+block['cleanup_seconds'])):
        errors['block_time_partition'] += 1
    return errors


def summarize(manifest,validation_blocks,queries,timing_blocks,warmup,source_manifest,source_analysis,source_rows):
    started, errors = perf_counter(), Counter()
    if (manifest.get('schema')!='acfqp.lmta_probability_reuse.v64' or manifest.get('status')!='complete'
            or manifest.get('protocol')!=PROTOCOL or manifest.get('previous_source')!=PREVIOUS
            or manifest.get('graphs')!=source_manifest['graphs'] or manifest.get('cold_decisions') is not True
            or manifest.get('runtime',{}).get('gc_enabled') is not True):
        errors['manifest_protocol'] += 1
    if (source_manifest['status']!='complete' or source_analysis['integrity']['passed'] is not True
            or source_analysis['complete_trajectory_evidence'] is not True
            or [g['graph_id'] for g in source_manifest['graphs']]!=IDS):
        errors['source_completed_evidence'] += 1
    source, observed = defaultdict(list), defaultdict(list)
    for row in source_rows:
        source[row['graph_id'],row['method']].append(row)
    for row in queries:
        observed[row['graph_id'],row['method']].append(row)
    identities = [(g,m) for g in IDS for m in METHODS]
    if (set(source)!=set(identities) or any([r['query_index'] for r in source[k]]!=list(range(96)) for k in source)
            or [(b['graph_id'],b['method']) for b in validation_blocks]!=identities):
        errors['validation_or_source_roster'] += 1
    preserved, validations = True, []
    for block in validation_blocks:
        identity = block['graph_id'],block['method']
        rows, old = observed[identity],source[identity]
        if (block['phase']!='validation' or block['round']!=-1 or block['variant']!='REUSE' or block['position']!=0
                or [r['query_index'] for r in rows]!=list(range(block['completed_queries']))):
            errors['validation_query_roster'] += 1
        comparisons = [preserved_query(row,reference) for row,reference in zip(rows,old)]
        for comparison in comparisons:
            errors.update(comparison['errors'])
        output_preserved = all(c['output_preserved'] for c in comparisons)
        work_preserved = all(c['logical_work_preserved'] for c in comparisons)
        errors.update(block_check(block,rows))
        if not close(block['decision_seconds'],sum(r['decision_seconds'] for r in rows)):
            errors['validation_decision_time_sum'] += 1
        mismatch = sum(bool(c['comparison_errors']) for c in comparisons)
        reported = Counter()
        for comparison in comparisons: reported.update(comparison['comparison_errors'])
        if block['candidate_mismatch_count']!=mismatch or Counter(block['comparison_errors'])!=reported:
            errors['validation_reported_mismatches'] += 1
        passed = block['status']=='complete' and output_preserved and work_preserved
        preserved = preserved and passed
        validations.append(dict(graph_id=identity[0],method=identity[1],output_preserved=output_preserved,
            logical_work_preserved=work_preserved,complete=block['status']=='complete',mismatches=mismatch))
    if set(observed)!=set(identities):
        errors['unbound_validation_queries'] += 1
    preservation = not errors and preserved and len(queries)==12288
    expected_timing = [(round_id,g,m,variant,position) for round_id in range(6) for gi,g in enumerate(IDS)
        for mi,m in enumerate(METHODS) for position,variant in enumerate(VARIANTS if (round_id+gi+mi)%2==0 else VARIANTS[::-1])]
    if manifest['timing_dispatched'] is not preservation:
        errors['conditional_timing_dispatch'] += 1
    if [(b['round'],b['graph_id'],b['method'],b['variant'],b['position']) for b in timing_blocks]!=(expected_timing if preservation else []):
        errors['paired_timing_roster'] += 1
    for block in timing_blocks:
        expected = (source if block['variant']=='BASELINE' else observed)[block['graph_id'],block['method']]
        errors.update(block_check(block,expected))
        if block['phase']!='timing' or not isinstance(block['candidate_mismatch_count'],int) or block['candidate_mismatch_count']<0:
            errors['timing_metadata'] += 1
    counts = dict(validation_blocks=len(validation_blocks),validation_queries=len(queries),
        timing_blocks=len(timing_blocks),timing_queries=sum(b['completed_queries'] for b in timing_blocks))
    if any(manifest.get(n)!=value for n,value in counts.items()):
        errors['manifest_counts'] += 1
    zeros = ('new_graphs','new_environment_calls','new_environment_samples','new_RL_updates','new_MCTS_calls','new_full_policy_evaluations')
    if any(manifest.get(n)!=0 for n in zeros):
        errors['new_work_scope'] += 1
    times = ('source_read_seconds','graph_reconstruction_seconds','data_output_seconds','whole_runner_seconds')
    if any(not close(manifest.get(n),manifest.get(n)) or manifest[n]<0 for n in times):
        errors['manifest_times'] += 1
    if preservation:
        if (warmup is None or [call['variant'] for call in warmup['calls']]!=VARIANTS
                or any(call['decision_work']['planner_calls']!=1 or not close(call['decision_seconds'],call['decision_seconds']) or call['decision_seconds']<0 for call in warmup['calls'])
                or any(not close(warmup.get(n),warmup.get(n)) or warmup[n]<0 for n in ('prepare_gc_seconds','cleanup_seconds','wall_seconds'))):
            errors['separate_warmup'] += 1
    elif warmup is not None:
        errors['warmup_without_preservation'] += 1
    performance = not errors and preservation and len(timing_blocks)==1536 and all(b['status']=='complete'
        and b['candidate_mismatch_count']==0 and not b['comparison_errors'] for b in timing_blocks)
    phases = {'warmup':warmup['calls'] if warmup else [],'validation':validation_blocks,'timing':timing_blocks}
    return dict(schema='acfqp.lmta_probability_reuse_analysis.v64',protocol=PROTOCOL,
        integrity=dict(passed=not errors,errors=dict(errors)),action_and_value_preservation=preservation,
        complete_performance_evidence=performance,validation=validations,timing=time_summary(timing_blocks) if performance else None,
        retained_V63_quality=source_analysis['cohort']['quality'] if preservation else None,
        accounting=dict(**counts,phase_work={phase:sum_work(records) for phase,records in phases.items()},
            warmup=warmup,runner={n:manifest[n] for n in times},
            phase_times={phase:{n:sum(b[n] for b in blocks) for n in ('decision_seconds','loop_seconds','bookkeeping_seconds','prepare_gc_seconds','cleanup_seconds','decision_total_seconds','block_seconds','serialization_seconds')}
                for phase,blocks in (('validation',validation_blocks),('timing',timing_blocks))},
            new_graphs=0,new_environment_calls=0,new_environment_samples=0,new_analysis_planner_calls=0,
            new_RL_updates=0,new_MCTS_calls=0,new_full_policy_evaluations=0,analysis_seconds_before_serialization=perf_counter()-started),
        limitations='Exact preservation refers to all retained V63 query occurrences. Reused trajectory quality does not prove equality on unvisited states. Performance uses six paired cold-replay rounds; warmup, validation and timing costs are separate. Timing serialization is included in runner data_output_seconds, not independently timed in each block.')


def read_jsonl(path):
    with path.open() as stream:
        return [json.loads(line) for line in stream]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'reports/lmta_probability_reuse_v64')
    args = parser.parse_args()
    with (args.output/'analysis_attempt.json').open('x') as attempt:
        started,error = perf_counter(),None
        try:
            manifest = json.loads((args.output/'manifest.json').read_text())
            validation,queries,timing = [read_jsonl(args.output/name) for name in
                ('validation_blocks.jsonl','validation_queries.jsonl','timing_blocks.jsonl')]
            path = args.output/'warmup.json'
            warmup = json.loads(path.read_text()) if path.exists() else None
            source_manifest = json.loads((ROOT/PREVIOUS/'manifest.json').read_text())
            source_analysis = json.loads((ROOT/PREVIOUS/'analysis.json').read_text())
            source = source_queries(read_jsonl(ROOT/PREVIOUS/'trajectories.jsonl'))
            analysis = summarize(manifest,validation,queries,timing,warmup,source_manifest,source_analysis,source)
            analysis['accounting']['analysis_wall_seconds_including_reads'] = perf_counter()-started
            (args.output/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
            print(json.dumps(dict(integrity=analysis['integrity'],preserved=analysis['action_and_value_preservation'],performance=analysis['complete_performance_evidence'])))
        except Exception as caught:
            error = f'{type(caught).__name__}: {caught}'
            raise
        finally:
            attempt.write(json.dumps(dict(wall_seconds=perf_counter()-started,exit_code=int(error is not None),error=error,
                new_planner_calls=0,new_environment_steps=0,new_random_draws=0),indent=2)+'\n')


if __name__=='__main__':
    main()
