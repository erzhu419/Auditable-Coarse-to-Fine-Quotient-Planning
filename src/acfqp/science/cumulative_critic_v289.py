"""Replay the original MC chronology and inspect fixed prediction/readout panels."""
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from math import ceil
from pathlib import Path
import resource
from statistics import mean
from time import perf_counter, process_time

from .controlled_predictive_online_query_td_v131 import QueryTD
from .controlled_predictive_regime_memory_v115 import SpawnMemory
from .natural_action_components_v283 import ActionComponents
from .natural_model_revision_v281 import load_leaf
from .native_retained_critic_v287 import score_retained
from .retained_actor_data_v287 import load_retained_parent
from .retained_critic_v287 import compact_dataset

FRACTIONS = (0., .25, .5, .75, 1.)


def h2_prefixes(n_games):
    return sorted({ceil(fraction*n_games) for fraction in FRACTIONS})


def configuration(source_summary, query_trace):
    return dict(schema='acfqp.cumulative_critic_freeze.v289',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/CUMULATIVE_CRITIC_V289.md'),
        source_summary=str(Path(source_summary).resolve()),
        query_trace=str(Path(query_trace).resolve()), lifecycles=list(range(16)), parents=4,
        alpha=.0025, fit='ORIGINAL_COMPLETE_GAME_MC_CHRONOLOGY',
        anchors_per_heldout_game=4, anchor_selection='EQUALLY_SPACED_NONWINNING_TIME_INDICES',
        snapshots='ZERO_AND_EVERY_FIT_GAME_END', h2_fractions=FRACTIONS,
        h2_cohort='V288_UNIFORM_A_PREACTION_BOARDS', h2_boards_per_lifecycle=4,
        h2_belief='FIXED_V287_FIT_PREFIX_MEMORY',
        reference='IMMEDIATE_SCORE_PLUS_V285_VALIDATION_ORACLE_H2_SUFFIX_MEAN',
        primary='FINAL_MINUS_SOURCE_ANCHOR_MSE', bootstrap_draws=20000,
        bootstrap_seed=28900001, new_environment_observations=0,
        finite_test_passes=dict(replay=4,analysis=10,driver=4))


def load_h2_panel(query_trace):
    """Reuse only the independently scored uniform preaction-board cohort."""
    lives = defaultdict(dict)
    counts = Counter()
    with gzip.open(query_trace, 'rt') as stream:
        for line in stream:
            query = json.loads(line)
            counts['compact_queries_read'] += 1
            if query['group'] != 'uniform':
                continue
            life, state_id = query['lifecycle'], query['state_id']
            row = lives[life].setdefault(state_id, dict(state_id=state_id,
                board=query['board'], reference_q={}, immediate_scores={}))
            if row['board'] != query['board'] or query['action'] in row['reference_q']:
                raise ValueError('The fixed H2 board/action panel is inconsistent')
            row['reference_q'][query['action']] = query['first_score']/2048.+mean(query['validation'])
            row['immediate_scores'][query['action']] = query['first_score']
            counts.update(reference_action_means=1, reused_validation_labels=len(query['validation']))
    if set(lives) != set(range(16)) or any(len(rows) != 4 for rows in lives.values()):
        raise ValueError('V289 requires the original four uniform A boards per lifecycle')
    return {life: list(rows.values()) for life, rows in lives.items()}, dict(counts)


def anchor_metrics(rows, predictions):
    if len(rows) != len(predictions):
        raise ValueError('Every fixed anchor needs one direct prediction')
    games = defaultdict(list)
    for row, prediction in zip(rows, predictions):
        error = prediction-row['target']
        games[row['episode']].append(dict(bias=error, mse=error*error, mae=abs(error)))
    per_game = [dict(episode=episode, count=len(values),
        **{key: mean(v[key] for v in values) for key in ('bias','mse','mae')})
        for episode, values in sorted(games.items())]
    return dict(metrics={key: mean(g[key] for g in per_game) for key in ('bias','mse','mae')},
        game_metrics=per_game)


def probe_h2(leaf, boards, p_four, runtime):
    writable = leaf.weights.flags.writeable
    leaf.freeze()
    try:
        component = ActionComponents(leaf, runtime)
        rows = []
        for board in boards:
            choice = component.compose(component.components(board['board']), p_four)
            if set(choice['action_values']) != set(board['reference_q']):
                raise ValueError('H2 readout and retained reference must contain the same legal actions')
            rows.append(dict(state_id=board['state_id'], action=choice['action'],
                action_values={action: value['value'] for action, value in choice['action_values'].items()}))
        return dict(rows=rows, counts=dict(component.counts),
            setup_counts=dict(component.setup_counts), setup_seconds=component.setup_seconds)
    finally:
        leaf.weights.flags.writeable = writable


def h2_metrics(boards, frozen, current):
    rows = []
    for board, old, new in zip(boards, frozen['rows'], current['rows']):
        if old['state_id'] != board['state_id'] or new['state_id'] != board['state_id']:
            raise ValueError('H2 comparison must use the same ordered board panel')
        reference = board['reference_q']
        old_q, new_q, best_q = reference[old['action']], reference[new['action']], max(reference.values())
        alternatives = [value for action, value in new['action_values'].items() if action != old['action']]
        rows.append(dict(state_id=board['state_id'], board=board['board'], reference_q=reference,
            frozen_action=old['action'], mc_action=new['action'],
            frozen_action_values=old['action_values'], mc_action_values=new['action_values'],
            action_disagreement=int(old['action'] != new['action']),
            validation_utility_delta=new_q-old_q, frozen_reference_regret=best_q-old_q,
            mc_reference_regret=best_q-new_q,
            predicted_frozen_action_margin=new['action_values'][old['action']]-max(alternatives)))
    keys = ('action_disagreement','validation_utility_delta','frozen_reference_regret',
        'mc_reference_regret','predicted_frozen_action_margin')
    return dict(board_rows=rows, metrics={key: mean(row[key] for row in rows) for key in keys})


def compare_original_fit(replay, old_fit):
    for key in ('learning_counts','first_update','last_update'):
        if replay[key] != old_fit[key]:
            raise ValueError(f'The original V287 MC {key} was not reproduced')
    for key, value in old_fit['target_counts'].items():
        if key != 'target_buffer_doubles_peak' and replay['target_counts'].get(key,0) != value:
            raise ValueError('The chronological replay changed MC target construction')


def _run_parent(source, parent_receipt, original_lives, old_lives, panel, output):
    from .cumulative_critic_analysis_v289 import select_anchor_indices
    from .cumulative_critic_replay_v289 import assemble_anchor_panel, replay_cumulative
    started, cpu_started = perf_counter(), process_time()
    before_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    parent = source['parent']
    runtime = Path(output)/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True, exist_ok=True)
    life_ids = parent_receipt['lifecycle_ids']
    datasets = load_retained_parent(parent_receipt['trace_file'], life_ids, original_lives)
    template, setup = load_leaf(source, runtime)
    lives = []
    trace_path = Path(output)/f'parent_{parent}_predictions.jsonl.gz'
    with gzip.open(trace_path, 'xt') as stream:
        for life in life_ids:
            dataset = datasets.pop(life)
            old = old_lives[life]
            for key in ('games','fit_game_count','fit_step_end','fit_end_raw','fit_memory'):
                if dataset[key] != old['dataset'][key]:
                    raise ValueError('The retained chronological dataset differs from V287')
            baseline = score_retained(template, dataset, runtime)
            if baseline['game_metrics'] != old['arms']['FROZEN']['heldout']['game_metrics']:
                raise ValueError('The original frozen full heldout predictions differ')
            p = SpawnMemory.from_payload(dataset['fit_memory']).predict()
            if p != old['evaluation_snapshot']['estimated_p_four']:
                raise ValueError('The fixed fit-prefix belief differs from V287')
            indices = select_anchor_indices(dataset, goal_rank=template.radix)
            anchors = assemble_anchor_panel(dataset, indices,
                goal=float(template.target_query['goal_bonus']),
                failure=float(template.target_query['failure_penalty']))
            stream.write(json.dumps(dict(kind='PANEL', lifecycle=life, anchors=anchors['rows']),
                separators=(',',':'), allow_nan=False)+'\n')
            fixed_h2 = probe_h2(template, panel[life], p, runtime)
            leaf = QueryTD(template.parent, 'PRIOR', runtime)
            head_setup = dict(counts=dict(leaf.setup_counts), seconds=leaf.setup_seconds,
                private_weight_bytes=leaf.weights.nbytes)
            probes = []
            nodes = set(h2_prefixes(dataset['fit_game_count']))
            def callback(completed, current):
                if completed in nodes:
                    actual = fixed_h2 if completed == 0 else probe_h2(current,panel[life],p,runtime)
                    probes.append(dict(completed_fit_games=completed, model_p_four=p,
                        **h2_metrics(panel[life],fixed_h2,actual),
                        planning_counts={} if completed == 0 else actual['counts'],
                        setup_counts={} if completed == 0 else actual['setup_counts'],
                        setup_seconds=0. if completed == 0 else actual['setup_seconds']))
            replay = replay_cumulative(leaf,dataset,indices,runtime,on_snapshot=callback)
            compare_original_fit(replay,old['arms']['EPISODIC_MC']['fit'])
            snapshots = replay.pop('snapshots')
            for snapshot in snapshots:
                predictions = snapshot.pop('predictions')
                stream.write(json.dumps(dict(kind='SNAPSHOT', lifecycle=life, **snapshot,
                    predictions=predictions), separators=(',',':'),allow_nan=False)+'\n')
                snapshot.update(anchor_metrics(anchors['rows'],predictions))
            updates_before = leaf.updates
            final = score_retained(leaf,dataset,runtime)
            if (final['game_metrics'] != old['arms']['EPISODIC_MC']['heldout']['game_metrics']
                    or leaf.updates != updates_before or leaf.updates != old['arms']['EPISODIC_MC']['new_value_updates']):
                raise ValueError('The cumulative replay did not reproduce the complete V287 heldout/updates')
            lives.append(dict(lifecycle=life,parent=parent,fit_game_count=dataset['fit_game_count'],
                dataset=compact_dataset(dataset), anchor_panel=anchors, snapshots=snapshots,
                h2_probes=probes, frozen_h2_costs=fixed_h2, estimated_p_four=p,
                replay=replay, head_setup=head_setup,
                full_heldout=dict(FROZEN=baseline,EPISODIC_MC=final),
                reproduction=dict(original_frozen_game_metrics_exact=True,
                    original_mc_game_metrics_exact=True,original_fit_counts_and_examples_exact=True)))
            print(json.dumps(dict(event='cumulative_critic_life_complete',lifecycle=life,
                fit_games=dataset['fit_game_count'],anchors=len(indices),updates=leaf.updates,
                final_anchor_mse_delta=snapshots[-1]['metrics']['mse']-snapshots[0]['metrics']['mse'],
                final_h2_reference_delta=probes[-1]['metrics']['validation_utility_delta'])),flush=True)
            del leaf
    after_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=lives,source_setup=setup,trace_file=str(trace_path.resolve()),
        trace_bytes=trace_path.stat().st_size,cpu_seconds=process_time()-cpu_started,
        compiler_cpu_seconds=after_child.ru_utime+after_child.ru_stime-before_child.ru_utime-before_child.ru_stime,
        wall_seconds=perf_counter()-started)


def build_accounting(old, suffix, lives, parents, panel_counts, cpu, wall):
    def summed(values):
        return dict(sum((Counter(value) for value in values),Counter()))
    def target_counts(values):
        return summed({k:v for k,v in value.items() if k!='target_buffer_doubles_peak'}
            for value in values)
    fit_targets=[life['replay']['target_counts'] for life in lives]
    heldout_targets=[score['target_counts'] for life in lives for score in life['full_heldout'].values()]
    return dict(new_environment_observations=0,new_evaluation_games=0,
        replay_value_updates=sum(life['replay']['learning_counts']['td_updates'] for life in lives),
        fit_counts=summed(life['replay']['learning_counts'] for life in lives),
        fit_target_counts=target_counts(fit_targets),
        fit_target_buffer_doubles_peak=max(value.get('target_buffer_doubles_peak',0) for value in fit_targets),
        anchor_prediction_counts=summed(life['replay']['anchor_scoring_counts'] for life in lives),
        anchor_label_counts=summed({k:v for k,v in life['anchor_panel']['counts'].items()
            if not k.endswith('_peak')} for life in lives),
        anchor_label_target_buffer_doubles_peak=max(life['anchor_panel']['counts']
            .get('target_buffer_doubles_peak',0) for life in lives),
        h2_planning_counts=summed([life['frozen_h2_costs']['counts'] for life in lives]+
            [probe['planning_counts'] for life in lives for probe in life['h2_probes']]),
        full_heldout_prediction_counts=summed(score['prediction_counts'] for life in lives
            for score in life['full_heldout'].values()),
        full_heldout_target_counts=target_counts(heldout_targets),
        full_heldout_target_buffer_doubles_peak=max(value.get('target_buffer_doubles_peak',0)
            for value in heldout_targets),
        private_head_weight_bytes_created=sum(life['head_setup']['private_weight_bytes'] for life in lives),
        inherited_retained_actor_acquisition=old['accounting']['inherited_costs_per_arm']['FROZEN'],
        inherited_retained_actor_economic_raw_tiles=old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN'],
        inherited_suffix_costs=suffix['accounting']['inherited_costs'],compact_panel_read_counts=panel_counts,
        historical_scope='The V287 acquisition and V285 independent suffix diagnostics are already paid. '
            'Their shared source/dynamics acquisition is charged once, and V285 subset/full scopes are '
            'alternatives. These provenance ledgers are not additive arm costs.',
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),
        compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu,wall_seconds=wall,
        prediction_trace_bytes=sum(p['trace_bytes'] for p in parents))


def run(source_summary, query_trace, output):
    from .cumulative_critic_analysis_v289 import summarize
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V289 formal freeze or results already exist')
    old = json.loads(Path(source_summary).read_text())
    suffix_path = Path(query_trace).with_name('summary.json')
    suffix = json.loads(suffix_path.read_text())
    for path in (Path(source_summary),suffix_path):
        if not json.loads(path.with_name('audit.json').read_text())['independent_valid']:
            raise ValueError('The original fixed actor and independent suffix data need their passing audits')
    settings = configuration(source_summary,query_trace)
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started,cpu_started = perf_counter(),process_time()
    panel,panel_counts = load_h2_panel(query_trace)
    original = json.loads(Path(old['settings']['source_summary']).read_text())
    original_lives = {life['lifecycle']:life for life in original['by_lifecycle']}
    old_lives = {life['lifecycle']:life for life in old['by_lifecycle']}
    parents = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(_run_parent,source,original['parent_receipts'][source['parent']],
            original_lives,old_lives,panel,output) for source in old['source_provenance']['parents']]
        for job in as_completed(jobs):
            parents.append(job.result())
    parents.sort(key=lambda row:row['parent'])
    lives = sorted([life for parent in parents for life in parent['lifecycles']],key=lambda row:row['lifecycle'])
    result = dict(schema='acfqp.cumulative_critic.v289',status='DIAGNOSTIC_COMPLETE',
        scientific_gate='NOT_A_FORMAL_GATE',settings=settings,source_provenance=old['source_provenance'],
        by_lifecycle=lives,parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},
            lifecycle_ids=[life['lifecycle'] for life in p['lifecycles']]) for p in parents],
        summary=summarize(lives),accounting=build_accounting(old,suffix,lives,parents,panel_counts,
            process_time()-cpu_started,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='cumulative_critic_complete',status=result['status'],
        primary=result['summary']['primary_final_anchor_mse_delta'])),flush=True)
    return result
