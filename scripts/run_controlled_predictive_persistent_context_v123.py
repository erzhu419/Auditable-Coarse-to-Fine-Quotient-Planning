"""Paired causal router replay on retained V122 observations; no game engine."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
from math import log
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from acfqp.science.controlled_predictive_regime_memory_v115 import SpawnMemory
from acfqp.science.controlled_predictive_persistent_context_v123 import PersistentSpawnMemory

LIVES, QUERIES = range(4), ('reward', 'risk_goal')
PHASES, P_FOUR = ('B', 'A_RETURN'), {'B': .5, 'A_RETURN': .1}
BUDGET, BLOCK = 524288, 64
METHODS = ('BASELINE', 'PERSISTENT')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def probability(router, module=None):
    value = router.modules[router.module_id if module is None else module]
    return value['alpha'] / (value['alpha'] + value['beta'])


def expected(module, phase):
    return module != 0 if phase == 'B' else module == 0


def empty_metrics(router, phase):
    return dict(observations=0, blocks=0, source_actions=0, switches=0,
        creations=0, reactivations=0, log_loss_sum=0., brier_sum=0.,
        absolute_probability_error_sum=0.,
        first_expected_activation=0 if expected(router.module_id, phase) else None,
        last_wrong_action=0, switches_after_first_expected=0,
        initial_source_probability=probability(router, 0),
        max_source_probability_deviation=0.)


def add_block(metrics, record, phase, end, source_probability):
    """All predictions in this completed block precede its observations."""
    n, k, p = record['n'], record['fours'], record['pre_probability']
    event, active = record['event'], record['pre_module']
    metrics['observations'] += n
    metrics['blocks'] += 1
    metrics['source_actions'] += n * (active == 0)
    metrics['log_loss_sum'] -= k * log(p) + (n-k) * log(1-p)
    metrics['brier_sum'] += k * (1-p)**2 + (n-k) * p**2
    metrics['absolute_probability_error_sum'] += n * abs(p-P_FOUR[phase])
    if not expected(active, phase):
        metrics['last_wrong_action'] = end
    changed = event['previous_module_id'] != event['module_id']
    metrics['switches'] += changed
    metrics['creations'] += event['kind'] == 'created'
    metrics['reactivations'] += event['kind'] == 'reactivated'
    if metrics['first_expected_activation'] is not None:
        metrics['switches_after_first_expected'] += changed
    elif expected(event['module_id'], phase):
        metrics['first_expected_activation'] = end
    metrics['max_source_probability_deviation'] = max(
        metrics['max_source_probability_deviation'],
        abs(source_probability-metrics['initial_source_probability']))


def replay_stream(initial_ranks, rows, destination, budget=BUDGET, expected_payloads=None):
    """Small-budget fixtures exercise the same replay; CLI uses the fixed budget."""
    routers = dict(BASELINE=SpawnMemory('LIBRARY'), PERSISTENT=PersistentSpawnMemory())
    for router in routers.values():
        for rank in initial_ranks:
            router.observe(rank)
    if len(initial_ranks) != 256:
        raise ValueError('exactly 256 source observations required')
    phases, phase_index, seen, row_count, block_pre = {}, 0, 0, 0, {}
    metrics = {name: empty_metrics(router, PHASES[0]) for name, router in routers.items()}
    with gzip.open(destination, 'wt') as output:
        for row in rows:
            if phase_index >= len(PHASES) or row['phase'] != PHASES[phase_index]:
                raise ValueError('retained phase order differs')
            phase = PHASES[phase_index]
            ranks = row['spawned_ranks']
            if (row['transitions_before'] != seen
                    or row['transitions_after'] != seen+len(ranks)
                    or seen+len(ranks) > budget
                    or len(row['bank_ids']) != len(ranks)):
                raise ValueError('retained observation budget or action roster differs')
            events = []
            for index, rank in enumerate(ranks):
                if seen % BLOCK == 0:
                    block_pre = {name: dict(pre_module=router.module_id,
                        pre_probability=probability(router)) for name, router in routers.items()}
                if routers['BASELINE'].module_id != row['bank_ids'][index]:
                    raise ValueError('baseline causal bank ID differs')
                emitted = {name: router.observe(rank) for name, router in routers.items()}
                seen += 1
                if emitted['BASELINE'] is not None:
                    events.append(dict(emitted['BASELINE'], observed_action_index=index))
                    paired = dict(phase=phase, phase_end=seen, methods={})
                    for name, router in routers.items():
                        event = emitted[name]
                        if event is None or event['block_n'] != BLOCK:
                            raise ValueError('paired block alignment differs')
                        rec = dict(block_pre[name], n=event['block_n'],
                            fours=event['block_fours'], event=event,
                            source_probability=probability(router, 0))
                        paired['methods'][name] = rec
                        add_block(metrics[name], rec, phase, seen, rec['source_probability'])
                    output.write(json.dumps(paired, separators=(',', ':')) + '\n')
            row_count += 1
            if events != row['routing_events'] or routers['BASELINE'].module_id != row['final_bank_id']:
                raise ValueError('baseline retained routing events differ')
            if seen == budget:
                if expected_payloads is not None and routers['BASELINE'].to_payload() != expected_payloads[phase]:
                    raise ValueError('baseline final retained payload differs')
                phases[phase] = {}
                for name, router in routers.items():
                    value = metrics[name]
                    value.update(final_router=router.to_payload(),
                        final_source_probability=probability(router, 0),
                        source_probability_change=probability(router, 0)-value['initial_source_probability'],
                        source_action_fraction=value['source_actions']/seen,
                        mean_log_loss=value['log_loss_sum']/seen,
                        mean_brier=value['brier_sum']/seen,
                        mean_absolute_probability_error=value['absolute_probability_error_sum']/seen)
                    phases[phase][name] = value
                phase_index += 1
                seen = 0
                if phase_index < len(PHASES):
                    metrics = {name: empty_metrics(router, PHASES[phase_index])
                        for name, router in routers.items()}
    if phase_index != 2 or seen:
        raise ValueError('incomplete retained stream')
    return dict(phases=phases, rows_read=row_count,
        unique_reused_ranks=2*budget, unique_reused_warmup=len(initial_ranks),
        processing_counts={name: dict(router.counts) for name, router in routers.items()},
        baseline_exact=True)


def run_stream(task):
    source, output, life, query, warmup = task
    start = perf_counter()
    path = source / f'life_{life}' / query / 'training.jsonl.gz'
    folder = output / f'life_{life}' / query
    folder.mkdir(parents=True)
    manifests = [source / f'life_{life}' / query / phase / 'BANK' /
        'checkpoint_524288/manifest.json' for phase in PHASES]
    payloads = {phase: json.loads(path.read_text())['router']
        for phase, path in zip(PHASES, manifests)}
    with gzip.open(path, 'rt') as handle:
        def records():
            for line in handle:
                row = json.loads(line)
                if row['life'] != life or row['query'] != query or row['method'] != 'BANK':
                    raise ValueError('retained stream roster differs')
                yield row
        result = replay_stream(warmup, records(), folder / 'blocks.jsonl.gz',
            expected_payloads=payloads)
    result.update(life=life, query=query, source=str(path),
        source_file_bytes=path.stat().st_size+sum(p.stat().st_size for p in manifests),
        seconds=perf_counter()-start)
    save(folder / 'summary.json', result)
    return result


def aggregate(streams):
    """Report each query separately; four histories, not eight independent lives."""
    contrasts = {}
    for phase in PHASES:
        contrasts[phase] = {}
        for query in QUERIES:
            rows = [s for s in streams if s['query'] == query]
            fields = ('source_action_fraction', 'source_probability_change', 'switches',
                'mean_log_loss', 'mean_brier', 'mean_absolute_probability_error',
                'first_expected_activation', 'last_wrong_action')
            contrasts[phase][query] = {field: [
                dict(life=s['life'], baseline=s['phases'][phase]['BASELINE'][field],
                    persistent=s['phases'][phase]['PERSISTENT'][field]) for s in rows]
                for field in fields}
    return contrasts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path,
        default=ROOT/'reports/controlled_predictive_context_bank_v122')
    parser.add_argument('--output', type=Path,
        default=ROOT/'reports/controlled_predictive_persistent_context_v123')
    args = parser.parse_args()
    started = perf_counter()
    args.output.mkdir(parents=True, exist_ok=False)
    files = [Path(__file__), ROOT/'specs/PERSISTENT_CONTEXT_V123.md',
        ROOT/'src/acfqp/science/controlled_predictive_regime_memory_v115.py',
        ROOT/'src/acfqp/science/controlled_predictive_persistent_context_v123.py',
        ROOT/'tests/test_controlled_predictive_persistent_context_v123.py',
        ROOT/'tests/test_controlled_predictive_persistent_context_runner_v123.py']
    for path in files:
        target = args.output/'source'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    capsule_path = args.source/'source_capsule.json'
    capsule = json.loads(capsule_path.read_text())
    snapshots = {row['life']: row for row in capsule['snapshots']}
    tasks = [(args.source, args.output, life, query, snapshots[life]['initial_ranks'][query])
        for life in LIVES for query in QUERIES]
    save(args.output/'inputs.json', dict(source=str(args.source), budget=BUDGET,
        warmups=[dict(life=l, query=q, ranks=r) for _, _, l, q, r in tasks]))
    with ProcessPoolExecutor(max_workers=4) as pool:
        streams = list(pool.map(run_stream, tasks))
    result = dict(schema='acfqp.persistent_context.v123.replay', complete=True,
        streams=streams, contrasts=aggregate(streams),
        costs=dict(new_environment_transitions=0, generated_samples=0, td_updates=0,
            weight_loads=0, weight_copies=0, unique_reused_training_ranks=sum(
                s['unique_reused_ranks'] for s in streams),
            unique_reused_warmup_ranks=sum(s['unique_reused_warmup'] for s in streams),
            source_rows_read=sum(s['rows_read'] for s in streams),
            source_file_bytes=capsule_path.stat().st_size+sum(s['source_file_bytes'] for s in streams),
            inherited_v122_bank_training_acquisitions=8388608,
            inherited_v120_shared_training_acquisitions=22124667,
            method_processing_counts={name: dict(sum((Counter(s['processing_counts'][name])
                for s in streams), Counter())) for name in METHODS},
            retained_trace_bytes=sum(p.stat().st_size for p in args.output.glob('life_*/*/blocks.jsonl.gz'))),
        seconds=perf_counter()-started)
    save(args.output/'run.json', result)
    print(json.dumps(dict(complete=True, seconds=result['seconds'], costs=result['costs'])))


if __name__ == '__main__':
    main()
