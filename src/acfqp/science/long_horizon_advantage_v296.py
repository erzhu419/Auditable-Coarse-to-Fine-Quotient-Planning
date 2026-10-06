"""Independent SOURCE-H2 continuations for three actions selected on old data."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import json
from pathlib import Path
import resource
from statistics import mean
from time import perf_counter, process_time

from .native_continuation_v285 import NativeContinuation
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS

PHASES = (('A', .1), ('B', .5), ('A_prime', .1))
REPLICAS = 32
SEED_BASE = 296600010000
PRIMARY = 'DISCOVERY_minus_SOURCE'


def validation_seed(life, phase, anchor, replica):
    return SEED_BASE+life*1000000+phase*100000+anchor*1000+replica


def freeze_selection(original, source_summary):
    """Read only OLD complete utilities; preserve every predetermined anchor."""
    lives = []
    for old in sorted(original['by_lifecycle'], key=lambda row: row['lifecycle']):
        phases = {}
        for phase_index, (phase, _) in enumerate(PHASES):
            anchors = []
            for anchor_index, anchor in enumerate(old['ranking'][phase]['anchors']):
                reference = anchor['reference']
                legal = sorted(anchor['choices']['FROZEN']['action_values'])
                means = {action: mean(row['total_utility'] for row in reference['rollouts']
                    if row['action'] == action) for action in legal}
                discovery = min(legal, key=lambda action: (-means[action], action))
                source = anchor['choices']['FROZEN']['action']
                bellman = anchor['choices']['BELLMAN_CONDITIONED']['action']
                row = {key: deepcopy(value) for key, value in anchor.items()
                       if key not in ('reference', 'choice_counts')}
                row.update(lifecycle=old['lifecycle'], parent=old['parent'], phase=phase,
                    phase_index=phase_index, anchor_index=anchor_index,
                    discovery_reference=deepcopy(reference), discovery_action=discovery,
                    discovery_action_means=means, source_action=source, bellman_action=bellman,
                    legal_actions=legal, validation_actions=sorted({source, bellman, discovery}))
                anchors.append(row)
            phases[phase] = dict(anchors=anchors)
        lives.append(dict(lifecycle=old['lifecycle'], parent=old['parent'], phases=phases))
    anchors = [a for life in lives for phase in life['phases'].values() for a in phase['anchors']]
    unions = Counter(len(a['validation_actions']) for a in anchors)
    accounting = original['accounting']
    reused = dict(
        economic_source_and_training_input_raw_tiles=accounting['economic_training_raw_tiles_per_arm']['FROZEN'],
        inherited_source_and_input_costs=deepcopy(accounting['inherited_costs_per_arm']['FROZEN']),
        carrier_raw_tiles=accounting['reused_carrier_raw_tiles'],
        carrier_counts=deepcopy(accounting['reused_carrier_counts']),
        warmup_raw_tiles=accounting['reused_warmup_raw_tiles'],
        warmup_environment_counts=deepcopy(accounting['reused_warmup_environment_counts']),
        warmup_direct_counts=deepcopy(accounting['reused_warmup_direct_counts']),
        warmup_memory_counts=deepcopy(accounting['reused_warmup_memory_counts']),
        discovery_rollouts=accounting['physical_ranking_rollouts'],
        discovery_counts=deepcopy(accounting['ranking_reference_counts']),
        discovery_cpu_seconds=accounting['ranking_reference_cpu_seconds'],
        selection_choice_counts={key: deepcopy(accounting['ranking_choice_counts_per_arm'][arm])
            for key, arm in (('SOURCE', 'FROZEN'), ('BELLMAN', 'BELLMAN_CONDITIONED'))},
        bellman_fit_counts=deepcopy(accounting['fit_counts_per_arm']['BELLMAN_CONDITIONED']),
        bellman_fit_cpu_seconds=accounting['fit_cpu_seconds_per_arm']['BELLMAN_CONDITIONED'],
        bellman_training_samples=accounting['processed_training_samples_per_arm']['BELLMAN_CONDITIONED'])
    return dict(schema='acfqp.long_horizon_advantage_selection.v296',
        source_summary=str(Path(source_summary).resolve()),
        source_provenance=deepcopy(original['source_provenance']), by_lifecycle=lives,
        anchor_count=len(anchors), union_size_counts={str(k): v for k, v in sorted(unions.items())},
        physical_validation_rollouts=REPLICAS*sum(len(a['validation_actions']) for a in anchors),
        paired_replica_seedstreams=REPLICAS*len(anchors),
        logical_candidate_references=3*REPLICAS*len(anchors), reused_selection_costs=reused)


def configuration(source_summary, finite_test_passes):
    return dict(schema='acfqp.long_horizon_advantage_freeze.v296',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/LONG_HORIZON_ADVANTAGE_V296.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(16)), parents=4,
        phases=PHASES, candidates=('SOURCE', 'BELLMAN', 'DISCOVERY'), replicas=REPLICAS,
        max_steps=MAX_STEPS, seed_validation=SEED_BASE, bootstrap_seed=29600001,
        bootstrap_draws=20000, query=QUERY, primary=PRIMARY,
        selection='OLD_ALL_LEGAL_TOTAL_UTILITY_MEAN_LEXICAL_TIE',
        validation='FROZEN_THREE_ACTION_UNION_SHARED_REPLICA_SEEDS',
        continuation='READONLY_SOURCE_H2_ANCHOR_OBSERVED_P_GROUND_PHASE_P',
        finite_test_passes=finite_test_passes)


def _run_parent(source, selected_lives, output, replicas=REPLICAS, max_steps=MAX_STEPS):
    started, cpu = perf_counter(), process_time()
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    output = Path(output)
    if not (output/'selection.json').is_file():
        raise ValueError('The complete old-data selection must be saved before new streams')
    parent = source['parent']; runtime = output/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True, exist_ok=True)
    leaf, setup = load_leaf(source, runtime)
    engine = NativeContinuation(leaf, runtime)
    source_updates = leaf.updates
    trace = output/f'parent_{parent}_records.jsonl.gz'
    lives = []
    with gzip.open(trace, 'xt', encoding='utf-8') as stream:
        for old_life in sorted(selected_lives, key=lambda row: row['lifecycle']):
            life = old_life['lifecycle']; phases = {}
            for phase_index, (phase, environment_p) in enumerate(PHASES):
                anchors = []
                for anchor_index, selected in enumerate(old_life['phases'][phase]['anchors']):
                    seeds = [validation_seed(life, phase_index, anchor_index, i) for i in range(replicas)]
                    evaluated = engine.evaluate(selected['board_before_action'], selected['validation_actions'],
                        selected['model_p_four'], seeds, max_steps=max_steps,
                        environment_p_four=environment_p)
                    anchor = dict(selected, validation_reference=dict(evaluated,
                        model_p_four=selected['model_p_four'], environment_p_four=environment_p))
                    anchors.append(anchor)
                    stream.write(json.dumps(dict(anchor, kind='VALIDATION_ANCHOR'),
                        separators=(',', ':'), allow_nan=False)+'\n')
                phases[phase] = dict(anchors=anchors)
                stream.flush()
                print(json.dumps(dict(event='long_horizon_validation_phase_complete',
                    lifecycle=life, parent=parent, phase=phase, anchors=len(anchors))), flush=True)
            lives.append(dict(lifecycle=life, parent=parent, phases=phases))
    if leaf.updates != source_updates or leaf.weights.flags.writeable:
        raise ValueError('Continuation evaluation changed the frozen SOURCE learner')
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent, lifecycles=lives, source_setup=setup,
        native_continuation_setup=dict(counts=dict(engine.setup_counts), seconds=engine.setup_seconds),
        source_updates_before=source_updates, source_updates_after=leaf.updates,
        trace_file=str(trace.resolve()), trace_bytes=trace.stat().st_size,
        cpu_seconds=process_time()-cpu, wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=after.ru_utime+after.ru_stime-child.ru_utime-child.ru_stime)


def build_accounting(selection, lives, parents, cpu, wall):
    references = [a['validation_reference'] for life in lives for p in life['phases'].values()
                  for a in p['anchors']]
    counts = {kind: dict(sum((Counter(ref['counts'][kind]) for ref in references), Counter()))
              for kind in ('environment', 'planning', 'rollout')}
    rollouts = [r for ref in references for r in ref['rollouts']]
    paired_streams = sum(len({r['replica_index'] for r in ref['rollouts']}) for ref in references)
    return dict(new_training_environment_raw_tiles=0, new_value_updates=0,
        physical_validation_anchors=len(references), physical_validation_rollouts=len(rollouts),
        paired_replica_seedstreams=paired_streams, logical_candidate_references=3*paired_streams,
        new_environment_raw_tiles=counts['environment'].get('sampled_transitions', 0),
        new_environment_random_draws=counts['environment'].get('environment_random_draws', 0),
        validation_counts=counts, validation_cutoffs=sum(r['status']=='CUTOFF' for r in rollouts),
        validation_cpu_seconds=sum(ref['cpu_seconds'] for ref in references),
        validation_seconds=sum(ref['seconds'] for ref in references),
        reused_selection_costs=selection['reused_selection_costs'],
        new_source_setup_counts=dict(sum((Counter(p['source_setup']['setup_counts']) for p in parents), Counter())),
        new_source_setup_cpu_seconds=sum(p['source_setup']['cpu_seconds'] for p in parents),
        native_continuation_setup_counts=dict(sum((Counter(p['native_continuation_setup']['counts']) for p in parents), Counter())),
        native_continuation_setup_seconds=sum(p['native_continuation_setup']['seconds'] for p in parents),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),
        compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu, wall_seconds=wall,
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),
        accounting_scope='Old source/input/Bellman fitting and discovery are retained reference costs, not new physical work. '
            'New continuation raw equals actual post-action spawns; supplied root boards have no new initial spawns. '
            'Identical candidate actions share one physical receipt. This is an independent diagnostic, not an equal-total-budget online comparison.')


def run(source_summary, output, finite_test_passes=None):
    started, cpu = perf_counter(), process_time()
    from .long_horizon_advantage_analysis_v296 import analyze
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    if any((output/name).exists() for name in ('configuration.json', 'selection.json', 'summary.json')):
        raise FileExistsError('V296 frozen selection or results already exist')
    original = json.loads(Path(source_summary).read_text())
    if not json.loads(Path(source_summary).with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V296 requires independently valid retained V294 anchors')
    selection = freeze_selection(original, source_summary)
    if (selection['anchor_count'] != 144 or selection['union_size_counts'] != {'1': 58, '2': 80, '3': 6}
            or selection['physical_validation_rollouts'] != 7552):
        raise ValueError('V296 must retain the frozen complete V294 anchor roster and candidate union')
    settings = configuration(source_summary, finite_test_passes or {})
    (output/'configuration.json').write_text(json.dumps(settings, indent=2)+'\n')
    (output/'selection.json').write_text(json.dumps(selection, separators=(',', ':'), allow_nan=False)+'\n')
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_run_parent, source,
            [life for life in selection['by_lifecycle'] if life['parent'] == source['parent']], output)
            for source in selection['source_provenance']['parents']]
        for job in as_completed(jobs):
            parents.append(job.result())
    parents.sort(key=lambda parent: parent['parent'])
    lives = sorted([life for parent in parents for life in parent['lifecycles']], key=lambda life: life['lifecycle'])
    summary = analyze(lives)
    result = dict(schema='acfqp.long_horizon_advantage.v296', status='EXPERIMENT_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE', settings=settings,
        selection_file=str((output/'selection.json').resolve()), source_provenance=selection['source_provenance'],
        by_lifecycle=lives, parent_receipts=[dict({k: v for k, v in parent.items() if k != 'lifecycles'},
            lifecycle_ids=[life['lifecycle'] for life in parent['lifecycles']]) for parent in parents],
        summary=summary, accounting=build_accounting(selection, lives, parents,
            process_time()-cpu, perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(event='long_horizon_advantage_complete',
        primary=summary['paired_contrasts'][PRIMARY])), flush=True)
    return result
