"""Independent discovery/validation of frozen H2 action continuation returns."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
from time import perf_counter, process_time

from .natural_action_components_v283 import ActionComponents
from .natural_model_revision_v281 import load_leaf, PHASES, MAX_STEPS
from .natural_continuation_analysis_v285 import select_indices, summarize

REPLICAS = 32
BATCHES = ('discovery', 'validation')


def continuation_seed(life, phase_index, slot, batch, replica):
    return 28500000000 + life*1000000 + phase_index*100000 + slot*1000 + batch*100 + replica


def select_states(records_path, changed_path):
    """Read current boards and current score-switch indices, never future labels."""
    competing = {}
    with gzip.open(changed_path, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if (row['episode_index'] == 0 and
                    row['full_actions']['ORACLE_P'] != row['short_actions']['ORACLE_P']):
                competing.setdefault((row['lifecycle'], row['phase']), []).append(row['decision'])
    states = []
    with gzip.open(records_path, 'rt') as stream:
        for line in stream:
            row = json.loads(line)
            if (row['kind'] != 'ONLINE' or row['arm'] != 'LIBRARY_H2'
                    or row['episode_index'] != 0):
                continue
            phase_index = next(i for i, (name, _) in enumerate(PHASES) if name == row['phase'])
            steps, decisions = row['episode']['steps'], row['decisions']
            indices = select_indices(len(steps), competing[row['lifecycle'], row['phase']])
            for group_index, group in enumerate(('uniform', 'competition')):
                for offset, index in enumerate(indices[group]):
                    step, saved = steps[index], decisions[index]
                    slot = group_index*4 + offset
                    states.append(dict(state_id=f"L{row['lifecycle']:02d}-{row['phase']}-{slot}",
                        lifecycle=row['lifecycle'], parent=row['parent'], phase=row['phase'],
                        phase_index=phase_index, p_four=PHASES[phase_index][1], group=group,
                        slot=slot, episode_index=0, carrier_seed=row['episode']['seed'],
                        decision=index, carrier_game_steps=len(steps), board=step['board'],
                        retained_action=saved['action'], retained_value=saved['value'],
                        retained_p_four=saved['p_four'],
                        observations_before=saved['observations_before']))
    if len(states) != 384 or len({s['state_id'] for s in states}) != 384:
        raise ValueError('V285 requires 16 complete lives, three phases, eight unique states per phase')
    return sorted(states, key=lambda s: (s['parent'], s['lifecycle'], s['phase_index'], s['slot']))


def prepare(source_summary, records_path, changed_path, output):
    """Freeze source pointers and selected roots before any new rollout."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = output/'selection.json'
    if manifest.exists():
        raise FileExistsError('V285 selection is already frozen')
    original = json.loads(Path(source_summary).read_text())
    states = select_states(records_path, changed_path)
    result = dict(schema='acfqp.natural_continuation_selection.v285',
        source_summary=str(Path(source_summary).resolve()),
        records_path=str(Path(records_path).resolve()), changed_path=str(Path(changed_path).resolve()),
        source_provenance=original['source_provenance'],
        inherited_v281_costs=original['summary']['accounting'], states=states,
        settings=dict(replicas_per_batch=REPLICAS, batches=BATCHES, max_steps=MAX_STEPS,
            groups=['uniform', 'competition'], phases=PHASES, bootstrap_draws=20000,
            bootstrap_seed=28500001, seed_base=28500000000,
            continuation='FIXED_TRUE_P_ORACLE_H2_WITH_UNCHANGED_SOURCE_LEAF'))
    manifest.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


def _run_parent(source, states, output):
    from .native_continuation_v285 import NativeContinuation
    cpu_started, started = process_time(), perf_counter()
    output = Path(output)
    runtime = output/'runtime'/f"parent_{source['parent']}"
    runtime.mkdir(parents=True, exist_ok=True)
    leaf, setup = load_leaf(source, runtime)
    engine = NativeContinuation(leaf, runtime)
    components = ActionComponents(leaf, runtime)
    results = []
    trace = output/f"parent_{source['parent']}_rollouts.jsonl.gz"
    with gzip.open(trace, 'xt', encoding='utf-8') as stream:
        for state in states:
            payload = components.components(state['board'])
            full = components.compose(payload, state['p_four'], 'full')
            short = components.compose(payload, state['p_four'], 'short')
            retained = components.compose(payload, state['retained_p_four'], 'full')
            if (retained['action'] != state['retained_action']
                    or retained['value'] != state['retained_value']):
                raise ValueError('Frozen source does not reproduce retained LIBRARY root choice')
            state = dict(state, legal_actions=sorted(full['action_values']),
                proxy_action=full['action'], short_action=short['action'],
                full_action_scores={a: v['value'] for a, v in full['action_values'].items()},
                immediate_scores={a: v['score'] for a, v in full['action_values'].items()},
                full_tail_scores={a: v['tail_value'] for a, v in full['action_values'].items()},
                short_action_scores={a: v['value'] for a, v in short['action_values'].items()})
            results.append(state)
            for batch_index, batch in enumerate(BATCHES):
                seeds = [continuation_seed(state['lifecycle'], state['phase_index'], state['slot'],
                    batch_index, replica) for replica in range(REPLICAS)]
                receipt = engine.evaluate(state['board'], state['legal_actions'],
                    state['p_four'], seeds, max_steps=MAX_STEPS)
                for sample in receipt['rollouts']:
                    sample = dict(sample, state_id=state['state_id'], batch=batch)
                    stream.write(json.dumps(sample, separators=(',', ':'), allow_nan=False)+'\n')
            stream.flush()
            print(json.dumps(dict(event='continuation_state_complete', parent=source['parent'],
                state_id=state['state_id'], states_done=len(results), states_total=len(states))), flush=True)
    if leaf.updates != 0:
        raise ValueError('Continuation evaluation changed frozen value weights')
    counters = {key: dict(value) for key, value in engine.counts.items()}
    return dict(parent=source['parent'], states=results,
        counts=counters, component_counts=dict(components.counts),
        setup=setup, native_setup_counts=dict(engine.setup_counts),
        native_setup_seconds=engine.setup_seconds,
        component_setup_counts=dict(components.setup_counts),
        component_setup_seconds=components.setup_seconds,
        new_leaf_updates=leaf.updates, trace_file=str(trace.resolve()), trace_bytes=trace.stat().st_size,
        cpu_seconds=process_time()-cpu_started, wall_seconds=perf_counter()-started)


def tail_calibration(state_results):
    """Descriptive full-tail bias against independent validation suffixes."""
    groups = {}
    for group in ('uniform', 'competition'):
        rows = [s for s in state_results if s['group'] == group]
        biases = {s['state_id']: s['full_tail_scores'][s['proxy_action']]
            - (s['validation_means'][s['proxy_action']]
               - s['immediate_scores'][s['proxy_action']]/2048.) for s in rows}
        groups[group] = dict(mean_proxy_tail_bias=sum(biases.values())/len(rows),
            by_lifecycle={str(life): sum(biases[s['state_id']] for s in rows
                if s['lifecycle'] == life)/sum(s['lifecycle'] == life for s in rows)
                for life in sorted({s['lifecycle'] for s in rows})},
            phases={phase: sum(biases[s['state_id']] for s in rows if s['phase'] == phase)
                /sum(s['phase'] == phase for s in rows) for phase, _ in PHASES})
    return groups


def run(manifest_path, output):
    output = Path(output)
    summary_path = output/'summary.json'
    if summary_path.exists() or list(output.glob('parent_*_rollouts.jsonl.gz')):
        raise FileExistsError('V285 continuation receipts already exist')
    manifest = json.loads(Path(manifest_path).read_text())
    started, cpu_started = perf_counter(), process_time()
    parents = []
    with ProcessPoolExecutor(max_workers=4) as workers:
        futures = [workers.submit(_run_parent, source,
            [s for s in manifest['states'] if s['parent'] == source['parent']], output)
            for source in manifest['source_provenance']['parents']]
        for future in as_completed(futures):
            parents.append(future.result())
    parents.sort(key=lambda row: row['parent'])
    states, rollouts = [], []
    for parent in parents:
        states.extend(parent['states'])
        with gzip.open(parent['trace_file'], 'rt') as stream:
            rollouts.extend(json.loads(line) for line in stream)
    parent_of = {s['lifecycle']: s['parent'] for s in states}
    analysis = summarize(states, rollouts, parent_of)
    analysis['tail_calibration'] = tail_calibration(analysis['state_results'])
    result = dict(schema='acfqp.natural_continuation_value.v285', status='DIAGNOSTIC_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE', selection=str(Path(manifest_path).resolve()),
        settings=manifest['settings'], source_provenance=manifest['source_provenance'],
        summary=analysis, parent_receipts=parents,
        accounting=dict(new_evaluation_rollouts=len(rollouts),
            new_evaluation_transitions=sum(r['steps'] for r in rollouts),
            terminal_counts=dict(Counter(r['status'] for r in rollouts)),
            new_training_observations=0, new_value_updates=sum(p['new_leaf_updates'] for p in parents),
            environment_counts=dict(sum((Counter(p['counts']['environment']) for p in parents), Counter())),
            planning_counts=dict(sum((Counter(p['counts']['planning']) for p in parents), Counter())),
            component_counts=dict(sum((Counter(p['component_counts']) for p in parents), Counter())),
            inherited_source_training_transitions=sum(s['inherited_training_costs']['environment_counts']['sampled_transitions']
                for s in manifest['source_provenance']['parents']),
            inherited_dynamics_costs=manifest['source_provenance']['inherited_dynamics_costs'],
            inherited_v281_costs=manifest['inherited_v281_costs'],
            worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),
            worker_setup_seconds=sum(p['native_setup_seconds']+p['component_setup_seconds'] for p in parents),
            coordinator_cpu_seconds=process_time()-cpu_started,
            wall_seconds=perf_counter()-started,
            trace_bytes=sum(p['trace_bytes'] for p in parents)),
        limitations=['Q of fixed true-p H2 continuation, not optimal Q or a newly trained policy.',
            'First games of retained LIBRARY lives; uniform and competition states reported separately.',
            'Intervals condition on four frozen source parents; finite rollout error remains.',
            'Diagnostic rollout observations are not consumed by any learner.'])
    summary_path.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='continuation_complete', status=result['status'],
        accounting=result['accounting'])), flush=True)
    return result
