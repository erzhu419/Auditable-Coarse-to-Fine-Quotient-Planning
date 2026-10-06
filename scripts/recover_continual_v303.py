#!/usr/bin/env python3
"""Recover the actual interrupted V303 attempt without changing its freeze."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

from acfqp.science import continual_v303 as core
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.natural_online_value_v286 import memory_state
from acfqp.science.retained_actor_data_v287 import _Replay


def recovered_stages(path,ledger):
    """Read the retained gzip prefix once, yielding only completed stages."""
    rows=[]; replay=None; warm_memory=None; started=None
    with gzip.open(path,'rt') as stream:
        try:
            for line in stream:
                if not line.endswith('\n'):
                    ledger['unretained_trailing_line']=True
                    break
                row=json.loads(line); ledger['canonical_rows_read']+=1
                if not rows:
                    started=process_time(); phase=row['phase']
                    expected=dict(lifecycle=row['lifecycle'],parent=row['parent'],warmup={},
                        arms={'FROZEN':dict(phases={phase:dict(training={},snapshot={})})})
                    replay=_Replay(expected,phase); warm_memory=SpawnMemory('LIBRARY')
                    warm=dict(game_summaries=[],raw_tiles=0,environment_counts=Counter(),direct_counts=Counter(),memory_events=[])
                rows.append(row)
                if row['kind']=='WARMUP':
                    replay.warmup(row)
                    for spawn in row['raw_spawns']:
                        event=warm_memory.observe(spawn['rank'])
                        if event is not None: warm['memory_events'].append(event)
                    warm['game_summaries'].append(row['summary']);warm['raw_tiles']+=len(row['raw_spawns'])
                    warm['environment_counts'].update(row['counts']['environment']);warm['direct_counts'].update(row['counts']['direct'])
                    ledger['retained_warmup_raw_tiles']+=len(row['raw_spawns'])
                    ledger['retained_environment_counts'].update(row['counts']['environment'])
                    continue
                phase_receipt=expected['arms']['FROZEN']['phases'][phase]
                if row['kind']=='TRAIN':
                    if replay.state is None:
                        warm.update(memory_counts=dict(warm_memory.counts),final_memory=memory_state(warm_memory))
                        warm['environment_counts']=dict(warm['environment_counts']);warm['direct_counts']=dict(warm['direct_counts'])
                        expected['warmup']=warm
                        phase_receipt['training']['before_stream']=row['start']
                    replay.train(row)
                    ledger['retained_actor_raw_tiles']+=len(row['raw_spawns'])
                    ledger['retained_environment_counts'].update(row['counts']['environment'])
                    ledger['retained_actor_native_cpu_seconds']+=row['cpu_seconds']
                    continue
                if row['kind']!='ACQUISITION_SNAPSHOT': raise ValueError('Unexpected interrupted canonical kind')
                phase_receipt.update(training=row['training'],snapshot=row['snapshot']);replay.checkpoint(row)
                dataset=replay.finish(); replay.cpu_seconds=process_time()-started
                dataset['costs']['processing_cpu_seconds']=replay.cpu_seconds
                acquisition=dict(warmup=warm,training=row['training'],snapshot=row['snapshot'],
                    native_setup_counts={},native_setup_seconds=0.,
                    reconstruction=dict(counts=dict(replay.processing),memory_counts=dict(replay.memory.counts),
                        chunks=replay.chunks,cpu_seconds=replay.cpu_seconds),
                    cpu_seconds=replay.cpu_seconds,new_value_updates=0,physical_acquisitions=1,new_evaluation_games=0,
                    execution_scope='Canonical acquisition reused; current CPU is reconstruction only; original setup/warmup CPU unavailable.')
                ledger['reused_complete_stages'].append(dict(lifecycle=row['lifecycle'],stage=phase,
                    raw_tiles=warm['raw_tiles']+row['training']['raw_tiles'],
                    retained_training_loop_cpu_seconds=row['training']['cpu_seconds']))
                yield row['lifecycle'],phase,dict(dataset=dataset,acquisition=acquisition),rows
                rows=[];replay=None
        except EOFError:
            ledger['truncated_gzip_footer']=True
    ledger['discarded_incomplete_prefix_raw_tiles']=sum(len(row.get('raw_spawns',[])) for row in rows)


def recover_parent(source,output,old_events):
    output=Path(output);parent=source['parent'];runtime=output/'runtime'/f'parent_{parent}'
    started,cpu_started=perf_counter(),process_time();children_before=resource.getrusage(resource.RUSAGE_CHILDREN)
    ledger=dict(canonical_rows_read=0,retained_warmup_raw_tiles=0,retained_actor_raw_tiles=0,
        retained_environment_counts=Counter(),retained_actor_native_cpu_seconds=0.,reused_complete_stages=[],
        new_acquisition_raw_tiles=0,regenerated_logged_arm_receipts=0,original_logged_evaluation_counts={k:Counter() for k in ('environment','planning')})
    preserved=output/'interrupted'/f'parent_{parent}_records.jsonl.gz'
    generator=recovered_stages(preserved,ledger);original_acquire=core.acquire_dataset
    exhausted=False
    def acquire(template,life,pid,emit,build,**kw):
        nonlocal exhausted
        if not exhausted:
            try:
                recovered_life,stage,acquired,canonical=next(generator)
            except StopIteration: exhausted=True
            else:
                if (recovered_life,stage)!=(life,kw['phase']): raise ValueError('Interrupted stage order differs from freeze')
                for record in canonical: emit(record)
                return acquired
        acquired=original_acquire(template,life,pid,emit,build,**kw)
        ledger['new_acquisition_raw_tiles']+=acquired['acquisition']['warmup']['raw_tiles']+acquired['acquisition']['training']['raw_tiles']
        return acquired
    core.acquire_dataset=acquire
    template,setup=core.load_leaf(source,runtime)
    engine=core.NativeValueStream(template,core.evaluation_seed(parent,'A',0),runtime)
    trace=output/f'parent_{parent}_records.jsonl.gz';lives=[]
    receipts=output/'lifecycle_receipts';receipts.mkdir(exist_ok=True)
    try:
        with gzip.open(trace,'xt') as stream:
            def emit(row):stream.write(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n')
            for life in range(parent,64,4):
                row=core._run_lifecycle(template,life,parent,runtime,engine,emit)
                for stage in core.STAGES:
                    for arm in core.ARMS:
                        key=f'{life}:{stage}:{arm}'
                        if key not in old_events: continue
                        saved=old_events[key]; value=row['stages'][stage]['arms'][arm]
                        replayed=dict(event='continual_arm_complete',lifecycle=life,stage=stage,arm=arm,
                            updates_before=value['head_updates_before'],updates_after=value['head_updates_after'],
                            utilities={t:sum(g['utility'] for g in e['game_summaries'])/32 for t,e in value['evaluations'].items()})
                        if replayed!=saved: raise ValueError('Recovered fit/evaluation differs from its retained original receipt')
                        ledger['regenerated_logged_arm_receipts']+=1
                        for e in value['evaluations'].values():
                            for kind in ledger['original_logged_evaluation_counts']:
                                ledger['original_logged_evaluation_counts'][kind].update(e['counts'][kind])
                (receipts/f'life_{life:02d}.json').write_text(json.dumps(row,allow_nan=False)+'\n')
                lives.append(row);stream.flush()
                print(json.dumps(dict(event='recovered_sequence_complete',lifecycle=life)),flush=True)
        if not exhausted:
            try:next(generator)
            except StopIteration:pass
            else:raise ValueError('Unused interrupted complete acquisition')
    finally:
        engine.close();core.acquire_dataset=original_acquire
    children_after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=lives,source_setup=setup,trace_file=str(trace.resolve()),trace_bytes=trace.stat().st_size,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts),seconds=engine.setup_seconds),recovery=ledger,
        cpu_seconds=process_time()-cpu_started,wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=children_after.ru_utime+children_after.ru_stime-children_before.ru_utime-children_before.ru_stime)


def run(output):
    output=Path(output);settings=json.loads((output/'configuration.json').read_text())
    if settings!=json.loads(json.dumps(core.configuration(settings['source_summary']))):
        raise ValueError('Recovery must preserve the original configuration')
    if (output/'summary.json').exists():raise FileExistsError('Complete V303 summary already exists')
    old=json.loads(Path(settings['source_summary']).read_text())
    events=[json.loads(line) for line in (output/'interrupted'/'stdout.log').read_text().splitlines()]
    old_events={f"{r['lifecycle']}:{r['stage']}:{r['arm']}":r for r in events}
    started,cpu_started=perf_counter(),process_time();parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(recover_parent,source,output,old_events) for source in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            parent=job.result();parents.append(parent)
            (output/f"parent_{parent['parent']}_receipt.json").write_text(json.dumps(parent,allow_nan=False)+'\n')
    parents.sort(key=lambda row:row['parent'])
    lives=sorted([life for p in parents for life in p['lifecycles']],key=lambda row:row['lifecycle'])
    analysis=core.summarize(lives);account=core.build_accounting(old,lives,parents,process_time()-cpu_started,perf_counter()-started)
    ledgers=[p['recovery'] for p in parents]
    recovery=dict(status='RECOVERED_SAME_FROZEN_COHORT',original_exit_code=143,original_completed_arm_receipts=len(events),
        regenerated_logged_arm_receipts=sum(l['regenerated_logged_arm_receipts'] for l in ledgers),
        reused_complete_acquisition_stages=sum(len(l['reused_complete_stages']) for l in ledgers),
        current_new_acquisition_raw_tiles=sum(l['new_acquisition_raw_tiles'] for l in ledgers),
        interrupted_retained_raw_tiles=sum(l['retained_actor_raw_tiles']+l['retained_warmup_raw_tiles'] for l in ledgers),
        additional_retained_incomplete_prefix_raw_tiles=sum(l['discarded_incomplete_prefix_raw_tiles'] for l in ledgers),
        interrupted_retained_environment_counts=core.sum_counts(l['retained_environment_counts'] for l in ledgers),
        interrupted_logged_evaluation_counts={k:core.sum_counts(l['original_logged_evaluation_counts'][k] for l in ledgers)
            for k in ('environment','planning')},
        retained_original_native_actor_cpu_seconds=sum(l['retained_actor_native_cpu_seconds'] for l in ledgers),
        retained_original_training_loop_cpu_seconds=sum(s['retained_training_loop_cpu_seconds'] for l in ledgers for s in l['reused_complete_stages']),
        historical_total_compute_closed=False,
        unavailable='Original warmup/setup, fitted-head/scoring/evaluation and process CPU were not persisted; '
            'unflushed work or a running evaluation at termination is also unavailable. Known ledgers are lower bounds.',
        scope='Each frozen life appears once. Complete original acquisitions reused, unfinished acquisitions use the same seeds. '
            'All original logged head updates/utility means reproduced exactly. Extra original evaluation is additional physical '
            'work, never additional independent statistical evidence; current worker/compiler CPU is measured separately.')
    if recovery['regenerated_logged_arm_receipts']!=len(events):raise ValueError('Not all interrupted arm receipts reproduced')
    recovery['training_raw_tiles_physical_lower_bound']=(recovery['interrupted_retained_raw_tiles']+
        recovery['current_new_acquisition_raw_tiles'])
    recovery['economic_training_raw_tiles_lower_bound_per_arm']={arm:value+
        recovery['additional_retained_incomplete_prefix_raw_tiles']
        for arm,value in account['economic_training_raw_tiles_per_arm'].items()}
    account['accounting_scope']+=' Recovery acquisition CPU on reused stages measures reconstruction only; original execution '
    account['accounting_scope']+='costs are separate in recovery and historical total compute remains unclosed.'
    result=dict(schema='acfqp.continual.v303',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',settings=settings,
        source_provenance=old['source_provenance'],by_lifecycle=lives,summary=analysis,accounting=account,recovery=recovery,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents])
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='continual_complete',primary_sequence_gain_supported=analysis['primary_sequence_gain_supported'],
        primary=analysis['final_ab_contrasts']['LOCAL_RISK_minus_SOURCE'],recovery=recovery)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try:
        run(args.output)
    except Exception:
        (Path(args.output)/'recovery_execution.json').write_text(json.dumps({'status':'FAILED'})+'\n')
        raise
    else:
        (Path(args.output)/'recovery_execution.json').write_text(json.dumps({'status':'COMPLETE'})+'\n')
