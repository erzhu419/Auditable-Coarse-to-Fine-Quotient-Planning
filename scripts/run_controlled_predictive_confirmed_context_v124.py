"""Confirm changes on V123's exact block sufficient statistics; no game engine."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'src'))
from acfqp.science.controlled_predictive_confirmed_context_v124 import ConfirmedSpawnMemory
from acfqp.science.controlled_predictive_persistent_context_v123 import PersistentSpawnMemory
from scripts.run_controlled_predictive_persistent_context_v123 import (
    LIVES, QUERIES, PHASES, BLOCK, BUDGET, save, probability, empty_metrics, add_block)

METHODS = ('PERSISTENT', 'CONFIRMED')


def replay_blocks(warmup, rows, destination, final_payloads, budget=BUDGET):
    if len(warmup) != 256:
        raise ValueError('expected exact source warmup')
    routers = dict(PERSISTENT=PersistentSpawnMemory(), CONFIRMED=ConfirmedSpawnMemory())
    for router in routers.values():
        for rank in warmup:
            router.observe(rank)
    results, phase_index, seen, fours_seen = {}, 0, 0, warmup.count(2)
    metrics = {m: empty_metrics(r, PHASES[0]) for m, r in routers.items()}
    with gzip.open(destination, 'wt') as output:
        for row in rows:
            if phase_index >= 2 or row['phase'] != PHASES[phase_index]:
                raise ValueError('phase order differs')
            phase = row['phase']
            if row['phase_end'] != seen+BLOCK or seen+BLOCK > budget:
                raise ValueError('retained block budget differs')
            original = row['methods']['PERSISTENT']
            if original['n'] != BLOCK or not 0 <= original['fours'] <= BLOCK:
                raise ValueError('retained block counts differ')
            before = {m: dict(pre_module=r.module_id, pre_probability=probability(r))
                for m, r in routers.items()}
            if any(before['PERSISTENT'][key] != original[key] for key in before['PERSISTENT']):
                raise ValueError('control pre-block state differs')
            events = {}
            # Within-block order is irrelevant to these blockwise learners.
            # This expands retained sufficient statistics, not new samples.
            k = original['fours']
            for name, router in routers.items():
                emitted = []
                for rank in [2]*k+[1]*(BLOCK-k):
                    event = router.observe(rank)
                    if event is not None:
                        emitted.append(event)
                if len(emitted) != 1:
                    raise ValueError('one event per complete block required')
                events[name] = emitted[0]
            if (events['PERSISTENT'] != original['event']
                    or probability(routers['PERSISTENT'], 0) != original['source_probability']):
                raise ValueError('control retained event or source statistics differ')
            seen += BLOCK
            fours_seen += k
            paired = dict(phase=phase, phase_end=seen, methods={})
            for name, router in routers.items():
                event = events[name]
                if event['block_n'] != BLOCK or event['block_fours'] != k:
                    raise ValueError('event confuses current and committed block counts')
                rec = dict(before[name], n=BLOCK, fours=k, event=event,
                    source_probability=probability(router, 0))
                paired['methods'][name] = rec
                add_block(metrics[name], rec, phase, seen, rec['source_probability'])
            output.write(json.dumps(paired, separators=(',', ':'))+'\n')
            if seen == budget:
                if routers['PERSISTENT'].to_payload() != final_payloads[phase]:
                    raise ValueError('control final payload differs')
                results[phase] = {}
                for name, router in routers.items():
                    payload = router.to_payload()
                    pending = payload['pending']
                    quarantine = payload.get('quarantine', dict(n=0, fours=0))
                    committed_n = sum(m['alpha']+m['beta']-2 for m in payload['modules'])
                    committed_fours = sum(m['alpha']-1 for m in payload['modules'])
                    if (committed_n+pending['n']+quarantine['n'] != router.observations_seen
                            or committed_fours+pending['fours']+quarantine['fours'] != fours_seen):
                        raise ValueError('observations not conserved across quarantine')
                    value = metrics[name]
                    value.update(final_router=payload,
                        final_source_probability=probability(router, 0),
                        source_probability_change=probability(router, 0)-value['initial_source_probability'],
                        source_action_fraction=value['source_actions']/seen,
                        mean_log_loss=value['log_loss_sum']/seen,
                        mean_brier=value['brier_sum']/seen,
                        mean_absolute_probability_error=value['absolute_probability_error_sum']/seen)
                    results[phase][name] = value
                phase_index += 1
                seen = 0
                if phase_index < 2:
                    metrics = {m: empty_metrics(r, PHASES[phase_index]) for m, r in routers.items()}
    if phase_index != 2 or seen:
        raise ValueError('incomplete retained replay')
    return dict(phases=results, control_exact=True, observation_conservation=True,
        unique_reused_ranks=2*budget, unique_reused_warmup=len(warmup),
        processing_counts={m: dict(r.counts) for m, r in routers.items()})


def run_stream(task):
    source, output, life, query, warmup, payloads = task
    start = perf_counter()
    path = source/f'life_{life}'/query/'blocks.jsonl.gz'
    folder = output/f'life_{life}'/query
    folder.mkdir(parents=True)
    with gzip.open(path, 'rt') as handle:
        result = replay_blocks(warmup, (json.loads(line) for line in handle),
            folder/'blocks.jsonl.gz', payloads)
    result.update(life=life, query=query, source=str(path),
        source_trace_bytes=path.stat().st_size, seconds=perf_counter()-start)
    save(folder/'summary.json', result)
    return result


def processing_totals(streams, method):
    counts = sum((Counter(s['processing_counts'][method]) for s in streams), Counter())
    if 'max_uncommitted_observations' in counts:
        counts['max_uncommitted_observations'] = max(
            s['processing_counts'][method]['max_uncommitted_observations'] for s in streams)
    return dict(counts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path,
        default=ROOT/'reports/controlled_predictive_persistent_context_v123')
    parser.add_argument('--output', type=Path,
        default=ROOT/'reports/controlled_predictive_confirmed_context_v124')
    args = parser.parse_args()
    started = perf_counter()
    args.output.mkdir(parents=True, exist_ok=False)
    files = [Path(__file__), ROOT/'specs/CONFIRMED_CONTEXT_V124.md',
        ROOT/'src/acfqp/science/controlled_predictive_confirmed_context_v124.py',
        ROOT/'src/acfqp/science/controlled_predictive_persistent_context_v123.py',
        ROOT/'src/acfqp/science/controlled_predictive_regime_memory_v115.py',
        ROOT/'scripts/run_controlled_predictive_persistent_context_v123.py',
        ROOT/'tests/test_controlled_predictive_confirmed_context_v124.py',
        ROOT/'tests/test_controlled_predictive_confirmed_context_runner_v124.py']
    for path in files:
        target = args.output/'source'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    inputs = json.loads((args.source/'inputs.json').read_text())
    previous = json.loads((args.source/'run.json').read_text())
    initials = {(w['life'], w['query']): w['ranks'] for w in inputs['warmups']}
    snapshots = {(s['life'], s['query']): s for s in previous['streams']}
    tasks = [(args.source, args.output, life, query, initials[life, query],
        {phase: snapshots[life, query]['phases'][phase]['PERSISTENT']['final_router']
            for phase in PHASES}) for life in LIVES for query in QUERIES]
    save(args.output/'inputs.json', dict(source=str(args.source), budget=BUDGET,
        warmups=inputs['warmups'], within_block_order='expand exact counts; predictions constant within block'))
    with ProcessPoolExecutor(max_workers=4) as pool:
        streams = list(pool.map(run_stream, tasks))
    result = dict(schema='acfqp.confirmed_context.v124.replay', complete=True,
        streams=streams,
        costs=dict(new_environment_transitions=0, generated_samples=0, td_updates=0,
            weight_loads=0, weight_copies=0,
            unique_reused_training_ranks=sum(s['unique_reused_ranks'] for s in streams),
            unique_reused_warmup_ranks=sum(s['unique_reused_warmup'] for s in streams),
            source_trace_bytes=sum(s['source_trace_bytes'] for s in streams),
            inherited_v122_bank_training_acquisitions=8388608,
            inherited_v120_shared_training_acquisitions=22124667,
            method_processing_counts={m: processing_totals(streams, m) for m in METHODS},
            retained_trace_bytes=sum(p.stat().st_size for p in args.output.glob('life_*/*/blocks.jsonl.gz'))),
        seconds=perf_counter()-started)
    save(args.output/'run.json', result)
    print(json.dumps(dict(complete=True, seconds=result['seconds'], costs=result['costs'])))


if __name__ == '__main__':
    main()
