"""Same-carrier target/representation factors with independent natural games."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

import numpy as np

from .conditional_carrier_data_v294 import load_parent
from .conditional_bellman_analysis_v294 import analyze
from .controlled_predictive_frozen_leaf_planning_v135 import FrozenLeafPlanner
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS, delta
from .native_conditional_bellman_v294 import ResidualHead, fit_episode, predict, materialize, score_actions
from .native_continuation_v285 import NativeContinuation
from .native_value_stream_v286 import NativeValueStream
from .online_episode_stream_v292 import _accumulate

ARMS = ('FROZEN', 'MC_BOARD', 'MC_CONDITIONED', 'BELLMAN_BOARD', 'BELLMAN_CONDITIONED')
PHASES = (('A', .1), ('B', .5), ('A_prime', .1))
EVALUATION_GAMES, RANK_REPLICAS = 32, 32


def evaluation_seed(life, phase, game):
    return 294900010000+life*1000000+phase*100000+game


def ranking_seed(life, phase, anchor, replica):
    return 294600010000+life*1000000+phase*100000+anchor*1000+replica


def configuration(source_summary, finite_test_passes):
    return dict(schema='acfqp.conditional_bellman_freeze.v294',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/CONDITIONAL_BELLMAN_V294.md'),
        source_summary=str(Path(source_summary).resolve()), lifecycles=list(range(16)), parents=4,
        arms=ARMS, phases=PHASES, alpha=.0025, fit_fraction=.8, query=QUERY, max_steps=MAX_STEPS,
        evaluation_games=EVALUATION_GAMES, ranking_replicas=RANK_REPLICAS,
        anchor_quartiles=[.25,.5,.75], seed_evaluation=294900010000, seed_ranking=294600010000,
        bootstrap_seed=29400001, bootstrap_draws=20000,
        primary='BELLMAN_CONDITIONED_minus_FROZEN_THREE_PHASE_COMPLETE_GAME_UTILITY',
        bellman='EXPECTED_MAX_CONTROL_GAME_START_FROZEN_OBSERVED_PROBABILITY',
        representation='SOURCE_PLUS_ZERO_RESIDUAL_UNIT_NORMALIZED_BARYCENTRIC_PROBABILITY_BASIS',
        split='PURE_PHASE_COMPLETE_GAMES_CHRONOLOGICAL_80_20_LABEL_HOLDOUT',
        mixed_games='EXCLUDED_WITH_ALL_ACQUISITION_COSTS_RETAINED',
        conditional_A_reference='COPY_RESIDUAL_BANKS_THEN_READ_BOTH_OLD_AND_NEW_AT_CURRENT_B_PROBABILITY',
        scientific_games=14848, logical_scientific_game_references=17920,
        new_training_raw_tiles=0, finite_test_passes=finite_test_passes)


def _totals():
    return dict(fitted_games=0, fitted_steps=0, trained_afterstates=0,
        learning_counts={}, target_counts={}, consolidation_counts={}, prediction_counts={},
        setup_counts={}, seconds=0., cpu_seconds=0.)


def _add_fit(total, receipt):
    for key in ('fitted_games','fitted_steps','trained_afterstates','seconds','cpu_seconds'):
        total[key] += receipt[key]
    for key in ('learning_counts','target_counts','consolidation_counts','prediction_counts','setup_counts'):
        _accumulate(total[key], receipt[key])


def factual_suffix(game):
    labels = np.empty(len(game['rewards']), dtype=np.float64)
    tail = 4. if game['terminal_code']==1 else -4.
    for step in range(len(labels)-1, -1, -1):
        labels[step] = tail
        tail += game['rewards'][step]
    return labels


def score_heldout(template, head, games, runtime):
    started, cpu = perf_counter(), process_time()
    rows, counts = [], {}
    for game in games:
        boards, probs = game['afterstates'], game['model_p_four']
        selected = np.max(boards, axis=1)<template.radix
        targets = factual_suffix(game)[selected]
        if head is None:
            before = dict(template.model.counts)
            predictions = np.asarray([template.model.value(board)+template.offset for board in boards[selected]])
            work = delta(template.model.counts, before)
        else:
            before = head.updates
            scored = predict(head, boards[selected], probs[selected], runtime)
            predictions, work = scored['predictions'], scored['counts']
            if head.updates != before:
                raise ValueError('Heldout label evaluation updated residual parameters')
        _accumulate(counts, work)
        errors = predictions-targets
        rows.append(dict(metadata=game['metadata'], count=len(targets), bias=float(np.mean(errors)),
            mse=float(np.mean(errors**2)), mae=float(np.mean(np.abs(errors))),
            mean_prediction=float(np.mean(predictions)), mean_factual_future_utility=float(np.mean(targets))))
    return dict(game_metrics=rows, metrics={key:sum(r[key] for r in rows)/len(rows) for key in ('bias','mse','mae')},
        prediction_counts=counts, target_counts=dict(suffix_games=len(games),
            suffix_target_assignments=sum(len(g['rewards']) for g in games),
            suffix_reward_additions=sum(len(g['rewards']) for g in games),
            skipped_winning_afterstates=sum(g['terminal_code']==1 for g in games)),
        seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)


def clone_parameters(head, runtime):
    started, cpu = perf_counter(), process_time()
    saved = ResidualHead(head.template, head.conditioned, runtime)
    np.copyto(saved.residuals, head.residuals)
    saved.updates = head.updates
    saved.residuals.flags.writeable = False
    return saved, dict(setup_counts=dict(saved.setup_counts, residual_parameters_copied=head.residuals.size,
        residual_bytes_copied=head.residuals.nbytes), residual_bytes_created=saved.residuals.nbytes,
        origin_value_updates=head.updates, seconds=perf_counter()-started, cpu_seconds=process_time()-cpu)


def _evaluate(engine, template, head, p, env_p, seeds, runtime, snapshots, purpose):
    state = engine.state()
    if head is None:
        leaf = template
    else:
        leaf, receipt = materialize(head, p, runtime)
        snapshots.append(dict(receipt, purpose=purpose, model_p_four=p))
    result = engine.evaluate_games(leaf, p, env_p, seeds, depth=2, max_steps=MAX_STEPS)
    if engine.state()!=state or leaf.weights.flags.writeable or leaf.updates!=0:
        raise ValueError('Independent static games changed their actor or the evaluator stream')
    return dict(result, model_p_four=p, environment_p_four=env_p, depth=2, shared_with_current=False)


def _run_lifecycle(template, data, life, parent, runtime, engine, emit):
    started, cpu = perf_counter(), process_time()
    heads = {arm:ResidualHead(template, arm.endswith('CONDITIONED'), runtime) for arm in ARMS[1:]}
    setups = {arm:dict(setup_counts=dict(head.setup_counts), residual_bytes_created=head.residuals.nbytes,
        setup_seconds=head.setup_seconds) for arm,head in heads.items()}
    arms = {arm:dict(phases={}, fit_totals=_totals()) for arm in ARMS}
    materializations, saved, saved_setups, ranking = [], {}, {}, {}
    source_planner, reference = FrozenLeafPlanner(template, 2, runtime), NativeContinuation(template, runtime)
    saved_p_a = None
    for phase_index,(phase,env_p) in enumerate(PHASES):
        inventory = data['phases'][phase]
        p = data['carrier_snapshots'][phase]['estimated_p_four']
        current_seeds = [evaluation_seed(life,phase_index,e) for e in range(EVALUATION_GAMES)]
        for arm in ARMS:
            head = heads.get(arm); fit = _totals()
            if head is not None:
                for game in inventory['fit_games']:
                    receipt = fit_episode(head, game, 'MC' if arm.startswith('MC') else 'EXPECTED_CONTROL', runtime)
                    _add_fit(fit, receipt)
                    emit(dict(kind='FIT_GAME', lifecycle=life, arm=arm, phase=phase,
                        completion=game['metadata'], fit=receipt, value_updates=head.updates))
                _add_fit(arms[arm]['fit_totals'], fit)
            heldout = score_heldout(template, head, inventory['heldout_games'], runtime)
            evaluated = _evaluate(engine, template, head, p, env_p, current_seeds, runtime,
                materializations, arm+'_'+phase+'_CURRENT')
            if phase_index==0:
                saved_p_a = p
                probe = dict(evaluated, shared_with_current=True,
                    counts={kind:{} for kind in evaluated['counts']}, seconds=0., cpu_seconds=0.)
                if head is not None:
                    saved[arm], saved_setups[arm] = clone_parameters(head, runtime)
            else:
                probe = _evaluate(engine, template, head, saved_p_a, .1,
                    [evaluation_seed(life,0,e) for e in range(EVALUATION_GAMES)], runtime,
                    materializations, arm+'_'+phase+'_FIXED_A')
            result = dict(fit=fit, heldout=heldout, game_summaries=evaluated['game_summaries'],
                evaluation_counts=evaluated['counts'], evaluation_seconds=evaluated['seconds'],
                evaluation_cpu_seconds=evaluated['cpu_seconds'], retention_probe=probe,
                snapshot=dict(estimated_p_four=p, value_updates=0 if head is None else head.updates))
            if phase_index==1:
                if head is None:
                    ahead = dict(evaluated, shared_with_current=True,
                        counts={kind:{} for kind in evaluated['counts']}, seconds=0., cpu_seconds=0.)
                else:
                    ahead = _evaluate(engine, template, saved.pop(arm), p, env_p, current_seeds,
                        runtime, materializations, arm+'_B_A_PARAMETERS')
                result['a_head_on_B'] = ahead
            arms[arm]['phases'][phase] = result
            emit(dict(kind='CHECKPOINT', lifecycle=life, arm=arm, phase=phase, **result))
            print(json.dumps(dict(event='conditional_bellman_phase_complete', lifecycle=life,arm=arm,phase=phase,
                samples=fit['trained_afterstates'],heldout_mse=heldout['metrics']['mse'],
                mean_utility=sum(g['utility'] for g in evaluated['game_summaries'])/EVALUATION_GAMES)), flush=True)
        anchors = []
        for anchor_index, anchor in enumerate(inventory['anchors']):
            board, point_p = anchor['board_before_action'], anchor['model_p_four']
            source_planner.spawn_probabilities = (1-point_p,point_p)
            before = dict(source_planner.counts)
            choices = {'FROZEN':source_planner.choose(board)}
            choice_counts = {'FROZEN':delta(source_planner.counts,before)}
            for arm,head in heads.items():
                scored = score_actions(head, np.asarray([board],dtype=np.int32),
                    np.asarray([point_p],dtype=np.float64), runtime)
                choices[arm],choice_counts[arm] = scored['choices'][0],scored['counts']
            actions = sorted(choices['FROZEN']['action_values'])
            outcomes = reference.evaluate(board, actions, point_p,
                [ranking_seed(life,phase_index,anchor_index,i) for i in range(RANK_REPLICAS)],
                max_steps=MAX_STEPS, environment_p_four=env_p)
            anchor_result = dict(anchor, reference=dict(outcomes,model_p_four=point_p,environment_p_four=env_p),
                choices=choices, choice_counts=choice_counts)
            anchors.append(anchor_result)
            emit(dict(anchor_result,kind='RANKING_ANCHOR',lifecycle=life,phase=phase,anchor_index=anchor_index))
        ranking[phase] = dict(anchors=anchors)
    if template.updates!=0:
        raise ValueError('The anchored source received value updates')
    compact = dict(costs=data['costs'], snapshots=data['carrier_snapshots'], phases={phase:dict(
        fit_games=[g['metadata'] for g in value['fit_games']],heldout_games=[g['metadata'] for g in value['heldout_games']],
        anchors=value['anchors']) for phase,value in data['phases'].items()})
    return dict(lifecycle=life,parent=parent,dataset=compact,arms=arms,ranking=ranking,
        head_setups=setups,retained_A_setups=saved_setups,materializations=materializations,
        costs=dict(cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-started,
            source_planner_setup_counts=dict(source_planner.setup_counts),
            reference_setup_counts=dict(reference.setup_counts)))


def _run_parent(source, source_receipt, expected_lives, output):
    started, cpu = perf_counter(), process_time(); child = resource.getrusage(resource.RUSAGE_CHILDREN)
    parent = source['parent']; runtime = Path(output)/'runtime'/f'parent_{parent}'; runtime.mkdir(parents=True,exist_ok=True)
    template, setup = load_leaf(source, runtime)
    datasets = load_parent(source_receipt['trace_file'], expected_lives)
    engine = NativeValueStream(template, 0, runtime)  # Never advanced; each evaluation owns its declared seed.
    rows=[]; trace=Path(output)/f'parent_{parent}_records.jsonl.gz'
    try:
        with gzip.open(trace,'xt') as stream:
            def emit(row):
                stream.write(json.dumps(dict(row,parent=parent),separators=(',',':'),allow_nan=False)+'\n')
            for life in range(parent,16,4):
                rows.append(_run_lifecycle(template,datasets.pop(life),life,parent,runtime,engine,emit))
                stream.flush()
    finally:
        engine.close()
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=rows,source_setup=setup,trace_file=str(trace.resolve()),
        trace_bytes=trace.stat().st_size,cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-started,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts),seconds=engine.setup_seconds),
        compiler_cpu_seconds=after.ru_utime+after.ru_stime-child.ru_utime-child.ru_stime)


def build_accounting(old, lives, parents, cpu, wall):
    def summed(values):
        total={}
        for value in values:_accumulate(total,value)
        return total
    inherited=old['accounting']['inherited_costs_per_arm']['FROZEN_H2']
    carrier_raw=sum(l['dataset']['costs']['reused_carrier_raw_tiles'] for l in lives)
    warm_raw=sum(l['dataset']['costs']['warmup_raw_tiles'] for l in lives)
    economic=inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+carrier_raw+warm_raw
    evaluation={a:{part:{kind:summed(l['arms'][a]['phases'][p][part]['counts'][kind]
        if part!='current' else l['arms'][a]['phases'][p]['evaluation_counts'][kind]
        for l in lives for p,_ in PHASES if part!='a_head_on_B' or p=='B')
        for kind in ('environment','planning')} for part in ('current','retention_probe','a_head_on_B')} for a in ARMS}
    eval_per_arm={a:{kind:summed(component[kind] for component in parts.values())
        for kind in ('environment','planning')} for a,parts in evaluation.items()}
    references=[anchor['reference'] for l in lives for phase in l['ranking'].values() for anchor in phase['anchors']]
    copies=[copy for l in lives for copy in l['retained_A_setups'].values()]
    snapshots=[snapshot for l in lives for snapshot in l['materializations']]
    setups=[setup for l in lives for setup in l['head_setups'].values()]
    fit={a:{part:summed(l['arms'][a]['fit_totals'][part] for l in lives)
        for part in ('learning_counts','target_counts','consolidation_counts','prediction_counts','setup_counts')} for a in ARMS}
    return dict(new_training_environment_raw_tiles=0,reused_carrier_raw_tiles=carrier_raw,reused_warmup_raw_tiles=warm_raw,
        economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS,economic),inherited_costs_per_arm=dict.fromkeys(ARMS,inherited),
        reused_carrier_counts={kind:summed(l['dataset']['costs']['carrier_acquisition_counts'][kind] for l in lives)
            for kind in ('environment','planning','learning')},
        reused_warmup_environment_counts=summed(l['dataset']['costs']['warmup_environment_counts'] for l in lives),
        reused_warmup_direct_counts=summed(l['dataset']['costs']['warmup_direct_counts'] for l in lives),
        reused_warmup_memory_counts=summed(l['dataset']['costs']['warmup_memory_counts'] for l in lives),
        processed_training_samples_per_arm={a:sum(l['arms'][a]['fit_totals']['trained_afterstates'] for l in lives) for a in ARMS},
        fit_counts_per_arm=fit,
        physical_evaluation_games=sum(len(l['arms'][a]['phases'][p]['game_summaries'])+
            (0 if l['arms'][a]['phases'][p]['retention_probe']['shared_with_current'] else
            len(l['arms'][a]['phases'][p]['retention_probe']['game_summaries']))+
            (0 if p!='B' or l['arms'][a]['phases'][p]['a_head_on_B']['shared_with_current'] else
            len(l['arms'][a]['phases'][p]['a_head_on_B']['game_summaries'])) for l in lives for a in ARMS for p,_ in PHASES),
        logical_evaluation_game_references=sum(len(l['arms'][a]['phases'][p]['game_summaries'])+
            len(l['arms'][a]['phases'][p]['retention_probe']['game_summaries'])+
            (len(l['arms'][a]['phases'][p]['a_head_on_B']['game_summaries']) if p=='B' else 0)
            for l in lives for a in ARMS for p,_ in PHASES),
        evaluation_components_per_arm=evaluation,evaluation_counts_per_arm=eval_per_arm,
        evaluation_counts={kind:summed(part[kind] for part in eval_per_arm.values()) for kind in ('environment','planning')},
        physical_ranking_anchors=len(references),physical_ranking_rollouts=sum(len(ref['rollouts']) for ref in references),
        ranking_reference_counts={kind:summed(ref['counts'][kind] for ref in references) for kind in ('environment','planning','rollout')},
        ranking_choice_counts_per_arm={a:summed(anchor['choice_counts'][a] for l in lives
            for phase in l['ranking'].values() for anchor in phase['anchors']) for a in ARMS},
        heldout_prediction_counts_per_arm={a:summed(l['arms'][a]['phases'][p]['heldout']['prediction_counts']
            for l in lives for p,_ in PHASES) for a in ARMS},
        heldout_target_counts_per_arm={a:summed(l['arms'][a]['phases'][p]['heldout']['target_counts']
            for l in lives for p,_ in PHASES) for a in ARMS},
        reconstruction_counts=summed(l['dataset']['costs']['processing_counts'] for l in lives),
        reconstruction_cpu_seconds=sum(l['dataset']['costs']['processing_cpu_seconds'] for l in lives),
        excluded_mixed_games=sum(g['reason']=='MIXED_PHASE' for l in lives for g in l['dataset']['costs']['excluded_games']),
        excluded_complete_game_raw_tiles=sum(g['raw_tiles'] for l in lives for g in l['dataset']['costs']['excluded_games']),
        excluded_tail_raw_tiles=sum(l['dataset']['costs']['excluded_tail']['raw_tiles'] for l in lives),
        residual_head_setup_counts=summed(setup['setup_counts'] for setup in setups),
        residual_head_bytes_created=sum(setup['residual_bytes_created'] for setup in setups),
        retained_A_setup_counts=summed(copy['setup_counts'] for copy in copies),
        retained_A_residual_bytes_created=sum(copy['residual_bytes_created'] for copy in copies),
        materialization_setup_counts=summed(snapshot['setup_counts'] for snapshot in snapshots),
        materialization_blending_counts=summed(snapshot['blending_counts'] for snapshot in snapshots),
        materialization_count=len(snapshots),materialization_private_weight_bytes_created=sum(s['private_weight_bytes'] for s in snapshots),
        materialization_cpu_seconds=sum(snapshot['cpu_seconds'] for snapshot in snapshots),
        native_evaluation_setup_counts=summed(p['native_evaluation_setup']['counts'] for p in parents),
        native_evaluation_setup_seconds=sum(p['native_evaluation_setup']['seconds'] for p in parents),
        fit_cpu_seconds_per_arm={a:sum(l['arms'][a]['fit_totals']['cpu_seconds'] for l in lives) for a in ARMS},
        ranking_reference_cpu_seconds=sum(ref['cpu_seconds'] for ref in references),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu,wall_seconds=wall,canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),
        development_reference=dict(previous='V293',unused_validation_raw_tiles=old['accounting']['physical_validation_raw_tiles'],
            unused_deployment_raw_tiles=old['accounting']['physical_deployment_raw_tiles'],
            unused_scientific_evaluation_counts=old['accounting']['evaluation_counts']),
        accounting_scope='Only old SOURCE carrier and warmup reused as training facts; whole acquisition paid including mixed/tail. '
            'Same training samples, different model enumeration and residual computation. Ranking reference and independent '
            'science are new physical cost, never training inputs. Source B and A-end identical references shared once. '
            'Buffer peaks are maxima; allocation/copy bytes are cumulative.')


def run(source_summary, output, finite_test_passes):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V294 frozen acquisition or results already exist')
    old=json.loads(Path(source_summary).read_text())
    if not json.loads(Path(source_summary).with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V294 requires the independently valid V293 carrier evidence')
    settings=configuration(source_summary,finite_test_passes)
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started,cpu=perf_counter(),process_time();parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,source,old['parent_receipts'][source['parent']],
            {l['lifecycle']:l for l in old['by_lifecycle'] if l['parent']==source['parent']},output)
            for source in old['source_provenance']['parents']]
        for job in as_completed(jobs):parents.append(job.result())
    parents.sort(key=lambda p:p['parent'])
    lives=sorted([l for p in parents for l in p['lifecycles']],key=lambda l:l['lifecycle'])
    summary=analyze(lives)
    result=dict(schema='acfqp.conditional_bellman.v294',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings,source_provenance=old['source_provenance'],by_lifecycle=lives,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},
            lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],summary=summary,
        accounting=build_accounting(old,lives,parents,process_time()-cpu,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='conditional_bellman_complete',primary=summary['paired_contrasts']['BELLMAN_CONDITIONED_minus_FROZEN'])),flush=True)
    return result
