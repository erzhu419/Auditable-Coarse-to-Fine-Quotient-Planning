"""Compare original and probability-reuse two-day control on fixed new graphs."""
from __future__ import annotations

import argparse
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
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.lmta_aim_v43 import generate_graph
from acfqp.science.lmta_probability_execution_v65 import run_block

VARIANTS = ['BASELINE', 'REUSE']
PROTOCOL = dict(nodes=15, stratum='sparse', expected_degree=1.5, p=1.5/14,
    graph_ids=list(range(650000,650064)), budget=2, horizon=3, replicates=32,
    method='LOOKAHEAD_2_ANALYTIC', variants=VARIANTS,
    seed_base=61000000, seed_graph_stride=1000,
    limits=dict(max_planner_action_values=2000000, max_decisions=100000, max_wall_seconds=60.),
    campaign_limits=dict(max_planner_action_values=6000000, max_wall_seconds=300.),
    primary_alpha=.05)
PREVIOUS = 'reports/lmta_probability_reuse_v64'
FROZEN = {path: 'reports/lmta_graph_coverage_v63/source/'+path for path in (
    'src/acfqp/science/lmta_aim_v43.py', 'src/acfqp/science/lmta_trajectory_v61.py',
    'scripts/analyze_lmta_trajectory_v61.py', 'scripts/analyze_lmta_trajectory_scale_v62.py',
    'scripts/lmta_trajectory_certificate_v62.py', 'scripts/analyze_lmta_graph_coverage_v63.py')}
FROZEN.update({path: PREVIOUS+'/source/'+path for path in (
    'src/acfqp/science/lmta_exact_v52.py', 'src/acfqp/science/lmta_analytic_short_v59.py',
    'src/acfqp/science/lmta_probability_reuse_v64.py', 'scripts/analyze_lmta_probability_reuse_v64.py')})
SOURCES = list(FROZEN) + ['src/acfqp/science/lmta_probability_execution_v65.py',
    'scripts/run_lmta_probability_execution_v65.py',
    'scripts/analyze_lmta_probability_execution_v65.py', 'specs/LMTA_PROBABILITY_EXECUTION_V65.md']


def require_previous():
    previous = json.loads((ROOT/PREVIOUS/'manifest.json').read_text())
    analysis = json.loads((ROOT/PREVIOUS/'analysis.json').read_text())
    if (previous['status'] != 'complete' or not analysis['integrity']['passed']
            or not analysis['action_and_value_preservation'] or not analysis['complete_performance_evidence']):
        raise AssertionError('Completed V64 preservation and paired cost evidence are required')
    for relative, frozen in FROZEN.items():
        if (ROOT/relative).read_bytes() != (ROOT/frozen).read_bytes():
            raise AssertionError(f'Frozen dependency changed: {relative}')


def run(output_dir):
    started, cpu_started = perf_counter(), process_time()
    tick = perf_counter()
    require_previous()
    source_seconds = perf_counter()-tick
    if not gc.isenabled():
        raise AssertionError('Automatic GC must remain enabled')
    output_dir.mkdir(parents=True, exist_ok=False)
    tick = perf_counter()
    for relative in SOURCES:
        target = output_dir/'source'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/relative, target)
    snapshot_seconds = perf_counter()-tick
    tick = perf_counter()
    graphs, metadata = {}, []
    for graph_id in PROTOCOL['graph_ids']:
        graph = generate_graph(PROTOCOL['nodes'], graph_id, p=PROTOCOL['p'])
        graphs[graph_id] = graph
        metadata.append(dict(graph_id=graph_id,
            **{key:PROTOCOL[key] for key in ('nodes','stratum','expected_degree','p')},
            edges=[list(edge) for edge in sorted(graph.edges())]))
    order = [dict(graph_id=graph_id, variant=variant) for index,graph_id in enumerate(PROTOCOL['graph_ids'])
             for variant in (VARIANTS if index%2==0 else VARIANTS[::-1])]
    manifest = dict(schema='acfqp.lmta_probability_execution.v65', status='running', protocol=PROTOCOL,
        previous_source=PREVIOUS, graphs=metadata, cold_decisions=True,
        source_snapshot_seconds=snapshot_seconds,
        source_read_seconds=source_seconds, graph_generation_seconds=perf_counter()-tick,
        data_output_seconds=0., unexecuted_prepare_gc_seconds=0.,
        completed_blocks=0, successful_blocks=0, resource_limited_blocks=0,
        trajectory_records=0, completed_trajectories=0, decision_records=0, campaign_action_values=0,
        terminal_reason=None, campaign_stop_reason=None, campaign_elapsed_at_stop=None, skipped_blocks=[],
        new_graphs=len(graphs), new_full_policy_evaluations=0, new_RL_updates=0, new_MCTS_calls=0,
        runtime=dict(python=platform.python_version(), networkx=nx.__version__, device='cpu',
                     arithmetic='float64', gc_enabled=gc.isenabled()))

    def save_manifest():
        manifest.update(whole_runner_seconds=perf_counter()-started,
            runner_cpu_seconds=process_time()-cpu_started,
            process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        (output_dir/'manifest.json').write_text(json.dumps(manifest, indent=2, allow_nan=False)+'\n')

    def stop_campaign(reason, next_index):
        manifest.update(terminal_reason='campaign_resource_limit', campaign_stop_reason=reason,
                        campaign_elapsed_at_stop=perf_counter()-started, skipped_blocks=order[next_index:])

    save_manifest()
    try:
        with (output_dir/'cases.jsonl').open('x') as ch, (output_dir/'trajectories.jsonl').open('x') as th:
            for index, identity in enumerate(order):
                tick = perf_counter()
                gc.collect()
                preparation = perf_counter()-tick
                before_actions = manifest['campaign_action_values']
                before_elapsed = perf_counter()-started
                remaining_actions = PROTOCOL['campaign_limits']['max_planner_action_values']-before_actions
                remaining_wall = PROTOCOL['campaign_limits']['max_wall_seconds']-before_elapsed
                if remaining_actions<=0 or remaining_wall<=0:
                    manifest['unexecuted_prepare_gc_seconds'] += preparation
                    stop_campaign('max_planner_action_values' if remaining_actions<=0 else 'max_wall_seconds', index)
                    break
                limits = {**PROTOCOL['limits'],
                    'max_planner_action_values': min(PROTOCOL['limits']['max_planner_action_values'],remaining_actions),
                    'max_wall_seconds': min(PROTOCOL['limits']['max_wall_seconds'],remaining_wall)}
                case, rows = run_block(graphs[identity['graph_id']], identity['graph_id'], identity['variant'],
                    PROTOCOL['replicates'], PROTOCOL['budget'], PROTOCOL['horizon'], limits)
                tick = perf_counter()
                gc.collect()
                cleanup = perf_counter()-tick
                reason = case['stop_reason']
                scope = None if case['status']=='complete' else 'block'
                if (reason=='max_planner_action_values' and remaining_actions<=PROTOCOL['limits']['max_planner_action_values']
                        or reason=='max_wall_seconds' and remaining_wall<=PROTOCOL['limits']['max_wall_seconds']):
                    scope = 'campaign'
                case.update(prepare_gc_seconds=preparation, cleanup_seconds=cleanup,
                    decision_total_seconds=case['decision_seconds']+cleanup,
                    block_seconds=case['wall_seconds']+cleanup, effective_limits=limits,
                    campaign_actions_before=before_actions, campaign_elapsed_before=before_elapsed, stop_scope=scope)
                tick = perf_counter()
                for row in rows:
                    th.write(json.dumps(row, allow_nan=False)+'\n')
                th.flush()
                case['serialization_seconds'] = perf_counter()-tick
                ch.write(json.dumps(case, allow_nan=False)+'\n')
                ch.flush()
                manifest['data_output_seconds'] += perf_counter()-tick
                manifest['campaign_action_values'] += case['decision_work'].get('action_value_evaluations',0)
                manifest['completed_blocks'] += 1
                manifest['successful_blocks'] += int(case['status']=='complete')
                manifest['resource_limited_blocks'] += int(case['status']=='resource_limit')
                manifest['trajectory_records'] += len(rows)
                manifest['completed_trajectories'] += case['completed_replicates']
                manifest['decision_records'] += case['decision_records']
                del rows
                print(json.dumps(dict(**identity, completed_blocks=manifest['completed_blocks'],
                    campaign_action_values=manifest['campaign_action_values'], stop_scope=scope)), flush=True)
                if scope=='campaign':
                    stop_campaign(reason, index+1)
                    break
                save_manifest()
        manifest['status'] = 'complete'
        if manifest['terminal_reason'] is None:
            manifest['terminal_reason'] = 'finished_roster'
    except Exception as error:
        manifest.update(status='failed', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        manifest['data_bytes'] = {name:(output_dir/name).stat().st_size for name in
            ('cases.jsonl','trajectories.jsonl') if (output_dir/name).exists()}
        save_manifest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'reports/lmta_probability_execution_v65')
    run(parser.parse_args().output_dir)
