"""Validate retained-query preservation, then time six paired cold replays."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import json
from pathlib import Path
import platform
import resource
import shutil
import sys
from time import perf_counter, process_time

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science.lmta_analytic_short_v59 import plan as baseline
from acfqp.science.lmta_probability_reuse_v64 import plan as reuse

METHODS = ['LOOKAHEAD_1_ANALYTIC','LOOKAHEAD_2_ANALYTIC']
VARIANTS = ['BASELINE','REUSE']
PROTOCOL = dict(rounds=6,methods=METHODS,variants=VARIANTS,
    limits=dict(max_planner_action_values=2000000,max_queries=100000,max_wall_seconds=60.))
PREVIOUS = 'reports/lmta_graph_coverage_v63'
FROZEN = ['src/acfqp/science/lmta_exact_v52.py','src/acfqp/science/lmta_analytic_short_v59.py']
SOURCES = FROZEN+['src/acfqp/science/lmta_probability_reuse_v64.py',
    'scripts/run_lmta_probability_reuse_v64.py','scripts/analyze_lmta_probability_reuse_v64.py',
    'specs/LMTA_PROBABILITY_REUSE_V64.md']
OUTPUT_FIELDS = ('selected','planned_value','root_action_values')


def read_source():
    manifest = json.loads((ROOT/PREVIOUS/'manifest.json').read_text())
    analysis = json.loads((ROOT/PREVIOUS/'analysis.json').read_text())
    if (manifest['status']!='complete' or not analysis['integrity']['passed']
            or not analysis['complete_trajectory_evidence']):
        raise AssertionError('Completed and certified V63 evidence is required')
    for relative in FROZEN:
        if (ROOT/relative).read_bytes()!=(ROOT/PREVIOUS/'source'/relative).read_bytes():
            raise AssertionError(f'Frozen dependency changed: {relative}')
    queries = defaultdict(list)
    with (ROOT/PREVIOUS/'trajectories.jsonl').open() as handle:
        for line in handle:
            row = json.loads(line)
            queries[row['graph_id'],row['method']].extend(row['decisions'])
    if len(queries)!=128 or any(len(rows)!=96 for rows in queries.values()):
        raise AssertionError('Expected 128 frozen blocks of 96 queries')
    return manifest['graphs'],queries


def compare(output, source, variant, reference=None):
    errors = Counter()
    if any(output[name]!=source[name] for name in OUTPUT_FIELDS):
        errors['retained_output_changed'] += 1
    work = output['decision_work']
    expected = reference if reference is not None else source['decision_work']
    if variant=='BASELINE' or reference is not None:
        if work!=expected:
            errors['replay_work_changed'] += 1
    else:
        if any(work.get(name)!=value for name,value in expected.items() if name!='target_probability_evaluations'):
            errors['logical_search_changed'] += 1
        if (work['terminal_probability_cache_hits']+work['terminal_probability_cache_misses']!=work['terminal_probability_lookups']
                or work['terminal_probability_lookups']+work['terminal_zero_source_terms']!=work['analytic_probability_terms']
                or work['target_probability_evaluations']!=expected['target_probability_evaluations']-expected['analytic_probability_terms']+work['terminal_probability_cache_misses']):
            errors['probability_work_partition'] += 1
    return errors


def replay_block(graph, graph_id, method, variant, source, phase, round_index, position, references=None):
    tick = perf_counter(); gc.collect(); prepare = perf_counter()-tick
    started = perf_counter()
    work, errors, rows, seconds, mismatches, stop = Counter(),Counter(),[],[],0,None
    planner = baseline if variant=='BASELINE' else reuse
    depth = METHODS.index(method)+1
    for index, query in enumerate(source):
        tick = perf_counter()
        output = planner(graph,tuple(query['statuses']),query['remaining_budget'],query['remaining_days'],depth)
        elapsed = perf_counter()-tick
        row = dict(graph_id=graph_id,method=method,query_index=index,
            **{name:query[name] for name in ('statuses','remaining_budget','remaining_days')},
            **{name:output[name] for name in OUTPUT_FIELDS},
            decision_work=dict(planner_calls=1,**output['counters']),decision_seconds=elapsed)
        mismatch = compare(row,query,variant,references[index] if references is not None else None)
        errors.update(mismatch); mismatches += bool(mismatch)
        work.update(row['decision_work']); seconds.append(elapsed)
        if phase=='validation': rows.append(row)
        last = perf_counter()-started
        limits = PROTOCOL['limits']
        stop = ('max_planner_action_values' if work['action_value_evaluations']>=limits['max_planner_action_values'] else
            'max_queries' if len(seconds)>=limits['max_queries'] else
            'max_wall_seconds' if last>=limits['max_wall_seconds'] else None)
        if stop: break
    loop = perf_counter()-started
    tick = perf_counter(); gc.collect(); cleanup = perf_counter()-tick
    decision_seconds = sum(seconds)
    block = dict(phase=phase,round=round_index,graph_id=graph_id,method=method,variant=variant,position=position,
        status='resource_limit' if stop else 'complete',stop_reason=stop,requested_queries=len(source),
        completed_queries=len(seconds),decision_work=dict(work),candidate_mismatch_count=mismatches,
        comparison_errors=dict(errors),decision_seconds=decision_seconds,loop_seconds=loop,
        bookkeeping_seconds=loop-decision_seconds,prepare_gc_seconds=prepare,cleanup_seconds=cleanup,
        decision_total_seconds=decision_seconds+cleanup,block_seconds=loop+cleanup,
        last_limit_check_seconds=last)
    return block,rows


def run(output_dir):
    started,cpu = perf_counter(),process_time()
    tick = perf_counter(); metadata,queries = read_source(); read_seconds = perf_counter()-tick
    if not gc.isenabled(): raise AssertionError('Automatic GC must remain enabled')
    output_dir.mkdir(parents=True,exist_ok=False)
    for relative in SOURCES:
        target = output_dir/'source'/relative; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,target)
    tick = perf_counter(); graphs = {}
    for meta in metadata:
        graph = nx.DiGraph(); graph.add_nodes_from(range(meta['nodes'])); graph.add_edges_from(meta['edges'])
        graphs[meta['graph_id']] = graph
    manifest = dict(schema='acfqp.lmta_probability_reuse.v64',status='running',protocol=PROTOCOL,
        previous_source=PREVIOUS,graphs=metadata,cold_decisions=True,source_read_seconds=read_seconds,
        graph_reconstruction_seconds=perf_counter()-tick,data_output_seconds=0.,validation_blocks=0,
        validation_queries=0,timing_blocks=0,timing_queries=0,timing_dispatched=False,
        new_graphs=0,new_environment_calls=0,new_environment_samples=0,new_RL_updates=0,new_MCTS_calls=0,
        new_full_policy_evaluations=0,runtime=dict(python=platform.python_version(),networkx=nx.__version__,gc_enabled=True))

    def save():
        manifest.update(whole_runner_seconds=perf_counter()-started,runner_cpu_seconds=process_time()-cpu,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        (output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

    save()
    try:
        references, valid = {},True
        with (output_dir/'validation_blocks.jsonl').open('x') as bh, (output_dir/'validation_queries.jsonl').open('x') as qh:
            for meta in metadata:
                for method in METHODS:
                    key = meta['graph_id'],method
                    block,rows = replay_block(graphs[key[0]],*key,'REUSE',queries[key],'validation',-1,0)
                    references[key] = [r['decision_work'] for r in rows]
                    valid &= block['status']=='complete' and block['candidate_mismatch_count']==0
                    tick = perf_counter()
                    for row in rows: qh.write(json.dumps(row)+'\n')
                    qh.flush(); block['serialization_seconds'] = perf_counter()-tick
                    bh.write(json.dumps(block)+'\n'); bh.flush()
                    manifest['data_output_seconds'] += perf_counter()-tick
                    manifest['validation_blocks'] += 1; manifest['validation_queries'] += len(rows)
                save()
        manifest['timing_dispatched'] = bool(valid)
        with (output_dir/'timing_blocks.jsonl').open('x') as handle:
            if valid:
                tick = perf_counter(); gc.collect(); preparation = perf_counter()-tick
                tick = perf_counter(); warmgraph=nx.DiGraph([(0,1)]); warm=[]
                for variant,planner in [('BASELINE',baseline),('REUSE',reuse)]:
                    mark=perf_counter(); output=planner(warmgraph,(0,0),2,3,2); duration=perf_counter()-mark
                    warm.append(dict(variant=variant,decision_work=dict(planner_calls=1,**output['counters']),decision_seconds=duration))
                mark=perf_counter(); gc.collect(); cleanup=perf_counter()-mark
                (output_dir/'warmup.json').write_text(json.dumps(dict(calls=warm,prepare_gc_seconds=preparation,
                    cleanup_seconds=cleanup,wall_seconds=perf_counter()-tick),indent=2)+'\n')
                for round_index in range(PROTOCOL['rounds']):
                    for graph_index,meta in enumerate(metadata):
                        for method_index,method in enumerate(METHODS):
                            order=VARIANTS if (round_index+graph_index+method_index)%2==0 else VARIANTS[::-1]
                            key=meta['graph_id'],method
                            for position,variant in enumerate(order):
                                block,_=replay_block(graphs[key[0]],*key,variant,queries[key],'timing',round_index,position,
                                    references[key] if variant=='REUSE' else None)
                                tick=perf_counter(); block['serialization_seconds']=0.
                                handle.write(json.dumps(block)+'\n'); handle.flush()
                                manifest['data_output_seconds']+=perf_counter()-tick
                                manifest['timing_blocks']+=1; manifest['timing_queries']+=block['completed_queries']
                    save(); print(json.dumps(dict(round=round_index,timing_blocks=manifest['timing_blocks'])),flush=True)
        manifest['status']='complete'
    except Exception as error:
        manifest.update(status='failed',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        manifest['data_bytes']={p.name:p.stat().st_size for p in output_dir.iterdir() if p.suffix in ('.jsonl','.json') and p.name!='manifest.json'}
        save()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'reports/lmta_probability_reuse_v64')
    run(parser.parse_args().output_dir)
