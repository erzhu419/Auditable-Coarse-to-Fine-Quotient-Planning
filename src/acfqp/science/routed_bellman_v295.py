"""Observed expert births and isolated Bellman writes on retained natural games."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from pathlib import Path
import resource
from time import perf_counter, process_time

import numpy as np

from .conditional_bellman_v294 import (_totals, _add_fit, _evaluate, clone_parameters,
                                      factual_suffix, score_heldout)
from .native_conditional_bellman_v294 import ResidualHead, fit_episode, predict
from .native_routed_bellman_v295 import fit_routed_episode
from .native_value_stream_v286 import NativeValueStream
from .natural_model_revision_v281 import load_leaf, QUERY, MAX_STEPS
from .online_episode_stream_v292 import _accumulate
from .routed_carrier_data_v295 import load_parent
from .routed_bellman_analysis_v295 import ARMS, analyze, evaluation_seed

PHASES = (('A', .1), ('B', .5), ('A_prime', .1))
EVALUATION_GAMES = 32


def configuration(source_summary, finite_test_passes):
    return dict(schema='acfqp.routed_bellman_freeze.v295',
        protocol=str(Path(__file__).resolve().parents[3]/'specs/ROUTED_BELLMAN_V295.md'),
        source_summary=str(Path(source_summary).resolve()),lifecycles=list(range(16)),parents=4,
        arms=ARMS,phases=PHASES,alpha=.0025,fit_fraction=.8,query=QUERY,max_steps=MAX_STEPS,
        evaluation_games=EVALUATION_GAMES,seed_evaluation=295900010000,
        bootstrap_seed=29500001,bootstrap_draws=20000,
        primary='ROUTED_BELLMAN_minus_FROZEN_THREE_PHASE_COMPLETE_GAME_UTILITY',
        target='EXPECTED_MAX_CONTROL_GAME_START_FROZEN_OBSERVED_PROBABILITY',
        representation='SOURCE_PLUS_UNIT_NORMALIZED_TWO_BANK_RESIDUAL_PER_OBSERVED_LIBRARY_MODULE',
        denominator='WHOLE_GAME_ORIGINAL_ADDRESS_OCCURRENCES_ACROSS_ALL_MODULES',
        expert_birth='COPY_PREVIOUS_EXPERT_AT_OBSERVED_CREATION_BEFORE_CURRENT_GAME_COMMIT',
        correction_reference='A_LIBRARY_FOLLOWS_SAME_B_OBSERVED_BIRTHS_WITHOUT_B_VALUE_UPDATES',
        split='V294_PURE_PHASE_COMPLETE_GAMES_CHRONOLOGICAL_80_20_LABEL_HOLDOUT',
        scientific_games=8704,logical_scientific_game_references=10752,
        new_training_raw_tiles=0,new_ranking_rollouts=0,finite_test_passes=finite_test_passes)


def _new_head(template,runtime):
    cpu=process_time()
    head=ResidualHead(template,True,runtime)
    return head,dict(setup_counts=dict(head.setup_counts),residual_bytes_created=head.residuals.nbytes,
                    setup_seconds=head.setup_seconds,cpu_seconds=process_time()-cpu)


def score_routed_heldout(template, experts, games, runtime):
    started,cpu = perf_counter(),process_time(); rows=[];counts={};batches=0
    for game in games:
        boards,p,modules = game['afterstates'],game['model_p_four'],game['module_ids']
        mask = np.max(boards,axis=1)<template.radix
        targets = factual_suffix(game)[mask]; selected_modules = modules[mask]
        predictions = np.empty(len(targets),dtype=np.float64)
        for module in np.unique(selected_modules):
            selection = selected_modules==module;head = experts[int(module)];before = head.updates
            result = predict(head,boards[mask][selection],p[mask][selection],runtime)
            if head.updates!=before:
                raise ValueError('Factual heldout labels changed an expert')
            predictions[selection]=result['predictions'];_accumulate(counts,result['counts']);batches+=1
        error=predictions-targets
        rows.append(dict(metadata=game['metadata'],count=len(targets),bias=float(np.mean(error)),
            mse=float(np.mean(error**2)),mae=float(np.mean(np.abs(error))),
            mean_prediction=float(np.mean(predictions)),mean_factual_future_utility=float(np.mean(targets))))
    return dict(game_metrics=rows,metrics={k:sum(r[k] for r in rows)/len(rows) for k in ('bias','mse','mae')},
        prediction_counts=counts,target_counts=dict(suffix_games=len(games),
            suffix_target_assignments=sum(len(g['rewards']) for g in games),
            suffix_reward_additions=sum(len(g['rewards']) for g in games),
            skipped_winning_afterstates=sum(g['terminal_code']==1 for g in games)),
        routing_prediction_batches=batches,routing_prediction_samples=sum(r['count'] for r in rows),
        seconds=perf_counter()-started,cpu_seconds=process_time()-cpu)


def _science(engine,template,head,p,env_p,seeds,runtime,materializations,purpose,module=None):
    return dict(_evaluate(engine,template,head,p,env_p,seeds,runtime,materializations,purpose),
                selected_value_module_id=module)


def _run_lifecycle(template,data,life,parent,runtime,engine,emit):
    started,cpu=perf_counter(),process_time()
    smooth,setup=_new_head(template,runtime)
    experts={};initializations=[dict(arm='SMOOTH_BELLMAN',module_id=None,**setup)]
    for module in data['warmup_module_ids']:
        experts[module],setup=_new_head(template,runtime)
        initializations.append(dict(arm='ROUTED_BELLMAN',module_id=module,**setup))
    arms={a:dict(phases={},fit_totals=_totals()) for a in ARMS}
    births,copies,no_update_births,materializations=[],[],[],[]
    saved_smooth,no_update_library,module_a,p_a=None,None,None,None
    processed=0;phase_route_counts={}
    for phase_index,(phase,env_p) in enumerate(PHASES):
        inventory=data['phases'][phase];fits={a:_totals() for a in ARMS}
        fit_games={g['metadata']['episode']:g for g in inventory['fit_games']}
        route_counts=dict(created=0,reactivated=0,game_complete=0,fit_game_complete=0)
        for event in data['routing_timeline'][phase]:
            current_birth,no_update_birth=None,None
            if event['kind']=='created':
                module,previous=event['module_id'],event['previous_module_id']
                if module in experts:
                    raise ValueError('Observed expert creation replaced an existing persistent expert')
                experts[module],receipt=clone_parameters(experts[previous],runtime)
                experts[module].residuals.flags.writeable=True
                current_birth=dict(phase=phase,event=event,receipt=receipt);births.append(current_birth)
                if phase=='B':
                    no_update_library[module],reference_receipt=clone_parameters(no_update_library[previous],runtime)
                    no_update_birth=dict(phase=phase,event=event,receipt=reference_receipt)
                    no_update_births.append(no_update_birth)
                route_counts['created']+=1
            elif event['kind']=='reactivated':
                if event['module_id'] not in experts:
                    raise ValueError('Observed reactivation lacks its preserved expert')
                route_counts['reactivated']+=1
            else:
                route_counts['game_complete']+=1
            emit(dict(kind='ROUTE_EVENT',lifecycle=life,phase=phase,original_event=event,
                current_birth=current_birth,no_update_birth=no_update_birth))
            if event['kind']=='GAME_COMPLETE' and event['fit']:
                game=fit_games.pop(event['metadata']['episode'])
                if game['metadata']!=event['metadata']:
                    raise ValueError('Expert fitting must use exactly the chronological retained game')
                smooth_fit=fit_episode(smooth,game,'EXPECTED_CONTROL',runtime)
                routed_fit=fit_routed_episode(experts,game,runtime)
                processed+=routed_fit['trained_afterstates'];route_counts['fit_game_complete']+=1
                for arm,receipt,updates in (('SMOOTH_BELLMAN',smooth_fit,smooth.updates),
                    ('ROUTED_BELLMAN',routed_fit,processed)):
                    _add_fit(fits[arm],receipt)
                    emit(dict(kind='FIT_GAME',lifecycle=life,phase=phase,arm=arm,
                        completion=game['metadata'],fit=receipt,value_updates=updates))
        if fit_games:
            raise ValueError('A pure-phase fit game was lost from its actual completion timeline')
        phase_route_counts[phase]=route_counts
        observed=data['carrier_snapshots'][phase];p=observed['estimated_p_four']
        module=observed['memory']['active_module_id']
        if phase_index==0:
            module_a,p_a=module,p
        seeds=[evaluation_seed(life,phase_index,e) for e in range(EVALUATION_GAMES)]
        for arm in ARMS:
            head=None if arm=='FROZEN' else smooth if arm=='SMOOTH_BELLMAN' else experts[module]
            selected=module if arm=='ROUTED_BELLMAN' else None
            heldout=(score_routed_heldout(template,experts,inventory['heldout_games'],runtime)
                if arm=='ROUTED_BELLMAN' else score_heldout(template,head,inventory['heldout_games'],runtime))
            evaluated=_science(engine,template,head,p,env_p,seeds,runtime,materializations,
                arm+'_'+phase+'_CURRENT',selected)
            if phase_index==0:
                probe=dict(evaluated,shared_with_current=True,
                    counts={k:{} for k in evaluated['counts']},seconds=0.,cpu_seconds=0.)
            else:
                old_context=experts[module_a] if arm=='ROUTED_BELLMAN' else head
                probe=_science(engine,template,old_context,p_a,.1,
                    [evaluation_seed(life,0,e) for e in range(EVALUATION_GAMES)],runtime,materializations,
                    arm+'_'+phase+'_FIXED_A',module_a if arm=='ROUTED_BELLMAN' else None)
            result=dict(fit=fits[arm],heldout=heldout,game_summaries=evaluated['game_summaries'],
                evaluation_counts=evaluated['counts'],evaluation_seconds=evaluated['seconds'],
                evaluation_cpu_seconds=evaluated['cpu_seconds'],retention_probe=probe,
                snapshot=dict(estimated_p_four=p,active_module_id=module,selected_value_module_id=selected,
                    value_updates=0 if arm=='FROZEN' else smooth.updates if arm=='SMOOTH_BELLMAN' else processed,
                    routed_expert_module_ids=sorted(experts) if arm=='ROUTED_BELLMAN' else [],
                    expert_value_updates={str(m):h.updates for m,h in experts.items()} if arm=='ROUTED_BELLMAN' else {}))
            if phase=='B':
                if arm=='FROZEN':
                    ahead=dict(evaluated,shared_with_current=True,
                        counts={k:{} for k in evaluated['counts']},seconds=0.,cpu_seconds=0.)
                else:
                    reference=saved_smooth if arm=='SMOOTH_BELLMAN' else no_update_library[module]
                    ahead=_science(engine,template,reference,p,env_p,seeds,runtime,materializations,
                        arm+'_B_NO_VALUE_UPDATES',selected)
                result['a_head_on_B']=ahead
            arms[arm]['phases'][phase]=result;_add_fit(arms[arm]['fit_totals'],fits[arm])
            emit(dict(kind='CHECKPOINT',lifecycle=life,phase=phase,arm=arm,**result))
            print(json.dumps(dict(event='routed_bellman_phase_complete',lifecycle=life,arm=arm,phase=phase,
                samples=fits[arm]['trained_afterstates'],active_module=module,experts=len(experts),
                mean_utility=sum(g['utility'] for g in evaluated['game_summaries'])/EVALUATION_GAMES)),flush=True)
        if phase=='A':
            saved_smooth,receipt=clone_parameters(smooth,runtime)
            copies.append(dict(arm='SMOOTH_BELLMAN',module_id=None,receipt=receipt))
            no_update_library={}
            for m,head in experts.items():
                no_update_library[m],receipt=clone_parameters(head,runtime)
                copies.append(dict(arm='ROUTED_BELLMAN',module_id=m,receipt=receipt))
        elif phase=='B':
            saved_smooth,no_update_library=None,None
    if template.updates!=0:
        raise ValueError('Routed learning modified the immutable SOURCE')
    compact=dict(costs=data['costs'],snapshots=data['carrier_snapshots'],
        initial_active_module_id=data['initial_active_module_id'],warmup_modules=data['warmup_modules'],
        warmup_module_ids=data['warmup_module_ids'],routing_timeline=data['routing_timeline'],
        phases={p:dict(fit_games=[g['metadata'] for g in v['fit_games']],
            heldout_games=[g['metadata'] for g in v['heldout_games']],anchors=v['anchors']) for p,v in data['phases'].items()})
    return dict(lifecycle=life,parent=parent,dataset=compact,arms=arms,head_initializations=initializations,
        expert_births=births,retained_A_copies=copies,no_update_births=no_update_births,
        materializations=materializations,phase_route_counts=phase_route_counts,
        costs=dict(cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-started))


def _run_parent(source,receipt,expected,output):
    started,cpu=perf_counter(),process_time();child=resource.getrusage(resource.RUSAGE_CHILDREN)
    parent=source['parent'];runtime=Path(output)/'runtime'/f'parent_{parent}';runtime.mkdir(parents=True,exist_ok=True)
    template,setup=load_leaf(source,runtime);datasets=load_parent(receipt['trace_file'],expected)
    engine=NativeValueStream(template,0,runtime);lives=[];trace=Path(output)/f'parent_{parent}_records.jsonl.gz'
    try:
        with gzip.open(trace,'xt') as stream:
            def emit(row):stream.write(json.dumps(dict(row,parent=parent),separators=(',',':'),allow_nan=False)+'\n')
            for life in range(parent,16,4):
                lives.append(_run_lifecycle(template,datasets.pop(life),life,parent,runtime,engine,emit));stream.flush()
    finally:engine.close()
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=lives,source_setup=setup,trace_file=str(trace.resolve()),trace_bytes=trace.stat().st_size,
        native_evaluation_setup=dict(counts=dict(engine.setup_counts),seconds=engine.setup_seconds),
        cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-started,
        compiler_cpu_seconds=after.ru_utime+after.ru_stime-child.ru_utime-child.ru_stime)


def build_accounting(old,lives,parents,cpu,wall):
    def summed(values):
        result={}
        for value in values:_accumulate(result,value)
        return result
    inherited=old['accounting']['inherited_costs_per_arm']['FROZEN_H2']
    carrier=sum(l['dataset']['costs']['reused_carrier_raw_tiles'] for l in lives)
    warm=sum(l['dataset']['costs']['warmup_raw_tiles'] for l in lives)
    economic=inherited['source_training_raw_tiles']+inherited['dynamics_raw_tiles']+carrier+warm
    components={a:{part:{kind:summed(l['arms'][a]['phases'][p]['evaluation_counts'][kind] if part=='current'
        else l['arms'][a]['phases'][p][part]['counts'][kind] for l in lives for p,_ in PHASES
        if part!='a_head_on_B' or p=='B') for kind in ('environment','planning')}
        for part in ('current','retention_probe','a_head_on_B')} for a in ARMS}
    evaluation={a:{kind:summed(c[kind] for c in parts.values()) for kind in ('environment','planning')}
        for a,parts in components.items()}
    initial=[r for l in lives for r in l['head_initializations']]
    births=[r['receipt'] for l in lives for r in l['expert_births']]
    copies=[r['receipt'] for l in lives for r in l['retained_A_copies']]
    counter_births=[r['receipt'] for l in lives for r in l['no_update_births']]
    materializations=[r for l in lives for r in l['materializations']]
    result=dict(new_training_environment_raw_tiles=0,new_ranking_rollouts=0,reused_carrier_raw_tiles=carrier,
        reused_warmup_raw_tiles=warm,economic_training_raw_tiles_per_arm=dict.fromkeys(ARMS,economic),
        inherited_costs_per_arm=dict.fromkeys(ARMS,inherited),
        reused_carrier_counts={k:summed(l['dataset']['costs']['carrier_acquisition_counts'][k] for l in lives)
            for k in ('environment','planning','learning')},
        reused_warmup_counts={k:summed(l['dataset']['costs']['warmup_'+k+'_counts'] for l in lives)
            for k in ('environment','direct','memory')},
        processed_training_samples_per_arm={a:sum(l['arms'][a]['fit_totals']['trained_afterstates'] for l in lives) for a in ARMS},
        fit_counts_per_arm={a:{k:summed(l['arms'][a]['fit_totals'][k] for l in lives)
            for k in ('learning_counts','target_counts','consolidation_counts','prediction_counts','setup_counts')} for a in ARMS},
        physical_evaluation_games=sum(len(l['arms'][a]['phases'][p]['game_summaries'])+
            (0 if l['arms'][a]['phases'][p]['retention_probe']['shared_with_current'] else
            len(l['arms'][a]['phases'][p]['retention_probe']['game_summaries']))+
            (0 if p!='B' or l['arms'][a]['phases'][p]['a_head_on_B']['shared_with_current'] else
            len(l['arms'][a]['phases'][p]['a_head_on_B']['game_summaries'])) for l in lives for a in ARMS for p,_ in PHASES),
        logical_evaluation_game_references=sum(len(l['arms'][a]['phases'][p]['game_summaries'])+
            len(l['arms'][a]['phases'][p]['retention_probe']['game_summaries'])+
            (len(l['arms'][a]['phases'][p]['a_head_on_B']['game_summaries']) if p=='B' else 0)
            for l in lives for a in ARMS for p,_ in PHASES),
        evaluation_components_per_arm=components,evaluation_counts_per_arm=evaluation,
        evaluation_counts={k:summed(v[k] for v in evaluation.values()) for k in ('environment','planning')},
        heldout_prediction_counts_per_arm={a:summed(l['arms'][a]['phases'][p]['heldout']['prediction_counts']
            for l in lives for p,_ in PHASES) for a in ARMS},
        heldout_target_counts_per_arm={a:summed(l['arms'][a]['phases'][p]['heldout']['target_counts']
            for l in lives for p,_ in PHASES) for a in ARMS},
        routed_heldout_prediction_batches=sum(l['arms']['ROUTED_BELLMAN']['phases'][p]['heldout']['routing_prediction_batches']
            for l in lives for p,_ in PHASES),
        reconstruction_counts=summed(l['dataset']['costs']['processing_counts'] for l in lives),
        reconstruction_memory_counts=summed(l['dataset']['costs']['processing_memory_counts'] for l in lives),
        reconstruction_cpu_seconds=sum(l['dataset']['costs']['processing_cpu_seconds'] for l in lives),
        observed_route_counts=summed(l['dataset']['costs']['routing_event_inventory'] for l in lives),
        observed_phase_route_counts={p:summed(l['phase_route_counts'][p] for l in lives) for p,_ in PHASES},
        actual_experts_created=len(births),initial_residual_heads=len(initial),no_update_experts_created=len(counter_births),
        materialization_count=len(materializations),
        materialization_setup_counts=summed(r['setup_counts'] for r in materializations),
        materialization_blending_counts=summed(r['blending_counts'] for r in materializations),
        materialization_private_weight_bytes_created=sum(r['private_weight_bytes'] for r in materializations),
        materialization_cpu_seconds=sum(r['cpu_seconds'] for r in materializations),
        native_evaluation_setup_counts=summed(p['native_evaluation_setup']['counts'] for p in parents),
        native_evaluation_setup_seconds=sum(p['native_evaluation_setup']['seconds'] for p in parents),
        fit_cpu_seconds_per_arm={a:sum(l['arms'][a]['fit_totals']['cpu_seconds'] for l in lives) for a in ARMS},
        excluded_mixed_games=sum(g['reason']=='MIXED_PHASE' for l in lives for g in l['dataset']['costs']['excluded_games']),
        excluded_complete_game_raw_tiles=sum(g['raw_tiles'] for l in lives for g in l['dataset']['costs']['excluded_games']),
        excluded_tail_raw_tiles=sum(l['dataset']['costs']['excluded_tail']['raw_tiles'] for l in lives),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=cpu,wall_seconds=wall,canonical_trace_bytes=sum(p['trace_bytes'] for p in parents),
        accounting_scope='Retained SOURCE-only training facts, including all paid excluded labels. Observed expert creation '
            'is processed even without fit labels. Actual acquisition shared physically; residual capacity and compute differ. '
            'No-B-update library copies/creations and science are paid. Allocation/copy bytes cumulative; buffer peaks maxima.')
    for scope,receipts in (('initial_residual',initial),('expert_birth',births),('retained_A',copies),('no_update_birth',counter_births)):
        result[scope+'_setup_counts']=summed(r['setup_counts'] for r in receipts)
        result[scope+'_residual_bytes_created']=sum(r['residual_bytes_created'] for r in receipts)
        result[scope+'_cpu_seconds']=sum(r['cpu_seconds'] for r in receipts)
    return result


def run(source_summary,output,finite_test_passes):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V295 already has frozen acquisition or results')
    old=json.loads(Path(source_summary).read_text())
    if not json.loads(Path(source_summary).with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V295 requires the independently valid retained carrier evidence')
    settings=configuration(source_summary,finite_test_passes)
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started,cpu=perf_counter(),process_time();parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,s,old['parent_receipts'][s['parent']],
            {l['lifecycle']:l for l in old['by_lifecycle'] if l['parent']==s['parent']},output)
            for s in old['source_provenance']['parents']]
        for job in as_completed(jobs):parents.append(job.result())
    parents.sort(key=lambda p:p['parent']);lives=sorted([l for p in parents for l in p['lifecycles']],key=lambda l:l['lifecycle'])
    summary=analyze(lives)
    result=dict(schema='acfqp.routed_bellman.v295',status='EXPERIMENT_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings,source_provenance=old['source_provenance'],by_lifecycle=lives,summary=summary,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},
            lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents],
        accounting=build_accounting(old,lives,parents,process_time()-cpu,perf_counter()-started))
    (output/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='routed_bellman_complete',primary=summary['paired_contrasts']['ROUTED_BELLMAN_minus_FROZEN'])),flush=True)
    return result
