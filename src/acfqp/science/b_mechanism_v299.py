"""Deterministic replay of V298 B data: local fitting, shared updates, H2 readout."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
from math import ceil
from pathlib import Path
import resource
from statistics import mean
from time import perf_counter, process_time

import numpy as np

from .controlled_predictive_ntuple_td_v120 import ACTIONS
from .controlled_predictive_online_query_td_v131 import QueryTD
from .native_episode_consolidation_v290 import fit_consolidated
from .native_retained_critic_v287 import score_retained
from .natural_model_revision_v281 import load_leaf
from .retained_actor_data_v287 import _Replay
from .retained_critic_v287 import compact_dataset

FRACTIONS = (0., .25, .5, .75, 1.)


def even_indices(n):
    m = min(4,n)
    return [0] if m==1 else [k*(n-1)//(m-1) for k in range(m)]


def roster(old):
    games, fit = old['dataset']['games'], old['dataset']['fit_game_count']
    ends = np.cumsum([g['steps'] for g in games])
    result = []
    for first,last in ((0,fit),(fit,len(games))):
        for k in even_indices(last-first):
            g = first+k
            start = int(ends[g-1]) if g else 0
            nonwinning = games[g]['steps']-int(games[g]['status']=='WON')
            result.extend(start+i for i in even_indices(nonwinning))
    return result


def load_parent(receipt, old_lives):
    """Reconstruct lawful B facts and only the preselected pre-action boards."""
    started = process_time()
    replays, roots, selected = {}, {}, {}
    for life in receipt['lifecycle_ids']:
        old = old_lives[life]
        expected = dict(lifecycle=life,parent=old['parent'],warmup=old['acquisition']['warmup'],
            arms=dict(FROZEN=dict(phases=dict(B=dict(training=old['acquisition']['training'],
                snapshot=old['acquisition']['snapshot'])))))
        replays[life] = _Replay(expected,phase='B')
        roots[life], selected[life] = {}, set(roster(old))
    rows_read = 0
    with gzip.open(receipt['trace_file'],'rt') as stream:
        for line in stream:
            row = json.loads(line); rows_read += 1
            life = row['lifecycle']; replay = replays[life]
            if row['phase']!='B' or row['true_p_four']!=.5:
                raise ValueError('Replay input is not the retained pure B acquisition')
            if row['kind']=='WARMUP':
                replay.warmup(row)
            elif row['kind']=='TRAIN':
                base = len(replay.afterstates)
                replay.train(row)
                n = len(row['actions'])
                if selected[life].intersection(range(base,base+n)):
                    board = list(row['start']['board']); episode = row['start']['episode']; action_index=0
                    for spawn in row['raw_spawns']:
                        if spawn['episode']!=episode:
                            board=[0]*16; episode=spawn['episode']
                        if spawn['kind']=='POST_ACTION':
                            step=base+action_index
                            if step in selected[life]:
                                roots[life][step]=dict(board_before_action=board[:],
                                    action=row['actions'][action_index], score=row['scores'][action_index],
                                    acquisition_model_p_four=row['model_p_four'])
                            board=list(replay.afterstates[step]); action_index+=1
                        board[spawn['cell']]=spawn['rank']
            elif row['kind']=='ACQUISITION_SNAPSHOT':
                replay.checkpoint(row)
            else:
                raise ValueError('Unexpected retained acquisition record')
    datasets = {life:r.finish() for life,r in replays.items()}
    return datasets,roots,dict(canonical_rows_read=rows_read,
        reconstruction_counts=sum_counts(r.processing for r in replays.values()),
        cpu_seconds=process_time()-started)


def sum_counts(values):
    return dict(sum((Counter(v) for v in values),Counter()))


def targets(dataset, goal, failure):
    result = np.empty(len(dataset['rewards']),dtype=np.float64)
    start = 0
    for end,code in zip(dataset['ends'],dataset['terminal_codes']):
        suffix = float(goal if code==1 else -failure)
        for step in range(int(end)-1,start-1,-1):
            result[step] = suffix
            suffix += float(dataset['rewards'][step])
        start=int(end)
    return result


def panel_metrics(panel, predictions):
    groups={split:[] for split in ('FIT','HELDOUT')}
    for row,value in zip(panel,predictions):
        error=float(value)-row['target']
        groups[row['split']].append((error,error*error,abs(error)))
    return {split:{metric:mean(v[i] for v in values) for i,metric in enumerate(('bias','mse','mae'))}
        for split,values in groups.items()}


def full_score(leaf,data,runtime):
    result=score_retained(leaf,dict(data,fit_game_count=0),runtime)
    for row,game in zip(result['game_metrics'],data['games']):
        row.update(split=game['split'],status=game['status'])
    return result


def original_heldout(result):
    return [{k:v for k,v in row.items() if k not in ('split','status')}
        for row in result['game_metrics'] if row['split']=='HELDOUT']


def h2_rows(result, panel):
    rows=[]
    for i,p in enumerate(panel):
        actions={name:{key:float(result[key][i,j]) for key in ('source_q','current_q','frozen_second_q')}
            for j,name in enumerate(ACTIONS) if result['legal'][i,j]}
        selected={key:ACTIONS[int(result[key][i])] for key in
            ('source_actions','current_actions','frozen_second_actions')}
        for q in actions.values():
            q['fixed_leaf_delta']=q['frozen_second_q']-q['source_q']
            q['reselection_delta']=q['current_q']-q['frozen_second_q']
            if q['reselection_delta'] < -1e-10:
                raise ValueError('H2 second-action reselection decreased its max value')
        rows.append(dict(step=p['step'],split=p['split'],actions=actions,**selected))
    return rows


def replay_life(template,data,roots,old,runtime,emit):
    from .b_mechanism_analysis_v299 import select_indices
    from .native_b_mechanism_v299 import predict, decompose_h2
    life=old['lifecycle']; parent=old['parent']; started=process_time()
    indices=select_indices(data,'FIT',template.radix)+select_indices(data,'HELDOUT',template.radix)
    if indices!=roster(old) or set(indices)!=set(roots):
        raise ValueError('The blind temporal panel roster changed during replay')
    labels=targets(data,template.target_query['goal_bonus'],template.target_query['failure_penalty'])
    episodes=np.searchsorted(data['ends'],indices,side='right')
    panel=[dict(step=int(step),episode=int(g),split=data['games'][g]['split'],
        status=data['games'][g]['status'],target=float(labels[step]),
        afterstate=data['afterstates'][step].tolist(),**roots[step]) for step,g in zip(indices,episodes)]
    boards=np.asarray([p['afterstate'] for p in panel],dtype=np.int32)
    root_boards=np.asarray([p['board_before_action'] for p in panel],dtype=np.int32)
    p=old['evaluation_snapshot']['estimated_p_four']
    baseline=full_score(template,data,runtime)
    if original_heldout(baseline)!=old['arms']['FROZEN']['heldout']['game_metrics']:
        raise ValueError('Original complete SOURCE heldout differs')
    leaf=QueryTD(template.parent,'PRIOR',runtime)
    private_setup=dict(counts=dict(leaf.setup_counts),seconds=leaf.setup_seconds,bytes=leaf.weights.nbytes)
    initial=predict(leaf,boards,runtime)
    before=initial['predictions']
    snapshots=[dict(completed_fit_games=0,metrics=panel_metrics(panel,before),predictions=before.tolist())]
    emit(dict(kind='PANEL',lifecycle=life,parent=parent,panel=panel,source_predictions=before.tolist(),
        estimated_p_four=p))
    nodes={ceil(f*data['fit_game_count']) for f in FRACTIONS}
    probe=decompose_h2(template,leaf,root_boards,p,runtime)
    h2=[dict(completed_fit_games=0,rows=h2_rows(probe,panel),counts=probe['counts'])]
    emit(dict(kind='H2',lifecycle=life,**h2[-1]))
    diagnostic_counts=Counter(initial['counts']); h2_counts=Counter(probe['counts'])
    native_setup=Counter(initial['setup_counts'])+Counter(probe['setup_counts'])
    fit_counts=Counter(); target_counts=Counter(); consolidation=Counter(); buffers={}
    updates=[]; first_sample=last_sample=None; start=0; fit_cpu=0.
    for g in range(data['fit_game_count']):
        end=int(data['ends'][g]); code=int(data['terminal_codes'][g])
        eligible=np.flatnonzero(np.max(data['afterstates'][start:end],axis=1)<leaf.radix)
        local_boards=data['afterstates'][start:end][eligible]
        local_targets=labels[start:end][eligible]
        current=predict(leaf,local_boards,runtime)
        diagnostic_counts.update(current['counts'])
        native_setup.update(current['setup_counts'])
        mse_before=float(np.mean((current['predictions']-local_targets)**2))
        one=dict(afterstates=data['afterstates'][start:end],rewards=data['rewards'][start:end],
            ends=np.asarray([end-start],dtype=np.int64),terminal_codes=np.asarray([code],dtype=np.int32),
            fit_game_count=1,fit_step_end=end-start)
        fitted=fit_consolidated(leaf,one,'EPISODE_MEAN_MC',runtime)
        native_setup.update(fitted['setup_counts'])
        fit_cpu+=fitted['cpu_seconds']; fit_counts.update(fitted['learning_counts'])
        target_counts.update({k:v for k,v in fitted['target_counts'].items() if not k.endswith('_peak')})
        consolidation.update({k:v for k,v in fitted['consolidation_counts'].items() if not k.endswith('_peak')})
        for k,v in {**fitted['target_counts'],**fitted['consolidation_counts']}.items():
            if k.endswith('_peak'): buffers[k]=max(buffers.get(k,0),v)
        for key in ('first_sample','last_sample'):
            sample=fitted[key]
            if sample is not None:
                sample=dict(sample,episode=g,step=sample['step']+start)
                if key=='first_sample' and first_sample is None: first_sample=sample
                if key=='last_sample': last_sample=sample
        after_local=predict(leaf,local_boards,runtime)
        diagnostic_counts.update(after_local['counts'])
        native_setup.update(after_local['setup_counts'])
        mse_after=float(np.mean((after_local['predictions']-local_targets)**2))
        if mse_after > mse_before+1e-10*max(1.,mse_before,mse_after):
            raise ValueError('Normalized MC increased its current-game squared loss')
        after=predict(leaf,boards,runtime)
        diagnostic_counts.update(after['counts'])
        native_setup.update(after['setup_counts'])
        delta=after['predictions']-before
        update=dict(game=g,status=data['games'][g]['status'],local_samples=len(eligible),
            local_mse_before=mse_before,local_mse_after=mse_after,delta_predictions=delta.tolist(),
            predictions_after=after['predictions'].tolist(),learning_counts=fitted['learning_counts'])
        updates.append(update)
        emit(dict(kind='GAME',lifecycle=life,**update))
        before=after['predictions']; start=end
        snapshots.append(dict(completed_fit_games=g+1,metrics=panel_metrics(panel,before),predictions=before.tolist()))
        if g+1 in nodes:
            probe=decompose_h2(template,leaf,root_boards,p,runtime)
            h2_counts.update(probe['counts'])
            native_setup.update(probe['setup_counts'])
            h2.append(dict(completed_fit_games=g+1,rows=h2_rows(probe,panel),counts=probe['counts']))
            emit(dict(kind='H2',lifecycle=life,**h2[-1]))
    original=old['arms']['EPISODE_MEAN_MC']['fit']
    if (dict(fit_counts)!=original['learning_counts'] or
        dict(target_counts)!={k:v for k,v in original['target_counts'].items() if not k.endswith('_peak')} or
        dict(consolidation)!={k:v for k,v in original['consolidation_counts'].items() if not k.endswith('_peak')} or
        first_sample!=original['first_sample'] or last_sample!=original['last_sample']):
        raise ValueError('Per-game replay did not reproduce original V298 counts/examples')
    leaf.freeze(); final=full_score(leaf,data,runtime)
    if original_heldout(final)!=old['arms']['EPISODE_MEAN_MC']['heldout']['game_metrics']:
        raise ValueError('Original full MEAN heldout predictions did not reproduce exactly')
    if leaf.updates!=original['trained_afterstates'] or template.updates!=0:
        raise ValueError('Replay update inventory differs from V298')
    return dict(lifecycle=life,parent=parent,dataset=compact_dataset(data),panel=panel,
        snapshots=snapshots,updates=updates,h2=h2,final_full=dict(SOURCE=baseline,MEAN=final),
        estimated_p_four=p,private_setup=private_setup,
        replay=dict(learning_counts=dict(fit_counts),target_counts=dict(target_counts),
            consolidation_counts=dict(consolidation),buffers=buffers,first_sample=first_sample,
            last_sample=last_sample,cpu_seconds=fit_cpu),diagnostic_counts=dict(diagnostic_counts),
        h2_counts=dict(h2_counts),native_setup_counts=dict(native_setup),
        label_counts=dict(suffix_games=len(data['games']),
            suffix_assignments=len(labels),suffix_additions=len(labels),buffer_bytes=labels.nbytes),
        reproduction=dict(original_fit_nonpeak_counts_and_examples_exact=True,
            original_source_and_mean_full_heldout_exact=True),cpu_seconds=process_time()-started)


def _run_parent(source,receipt,old_lives,output):
    started,cpu=perf_counter(),process_time(); child=resource.getrusage(resource.RUSAGE_CHILDREN)
    parent=source['parent']; runtime=Path(output)/'runtime'/f'parent_{parent}'
    runtime.mkdir(parents=True,exist_ok=True)
    datasets,roots,reconstruction=load_parent(receipt,old_lives)
    template,setup=load_leaf(source,runtime)
    lives=[]; path=Path(output)/f'parent_{parent}_records.jsonl.gz'
    with gzip.open(path,'xt') as stream:
        def emit(row): stream.write(json.dumps(row,separators=(',',':'),allow_nan=False)+'\n')
        for life in receipt['lifecycle_ids']:
            result=replay_life(template,datasets.pop(life),roots.pop(life),old_lives[life],runtime,emit)
            lives.append(result); stream.flush()
            print(json.dumps(dict(event='b_mechanism_life_complete',lifecycle=life,
                samples=result['replay']['learning_counts']['td_updates'])),flush=True)
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return dict(parent=parent,lifecycles=lives,reconstruction=reconstruction,source_setup=setup,
        trace_file=str(path.resolve()),trace_bytes=path.stat().st_size,cpu_seconds=process_time()-cpu,
        compiler_cpu_seconds=after.ru_utime+after.ru_stime-child.ru_utime-child.ru_stime,
        wall_seconds=perf_counter()-started)


def configuration(source_summary, finite_tests):
    return dict(schema='acfqp.b_mechanism_freeze.v299',protocol=str(Path(__file__).resolve().parents[3]/'specs/B_MECHANISM_V299.md'),
        source_summary=str(Path(source_summary).resolve()),lifecycles=list(range(64)),parents=4,
        method='EPISODE_MEAN_MC',alpha=.0025,phase='B',new_environment_observations=0,
        new_evaluation_games=0,selection='FOUR_TIME_GAMES_PER_SPLIT_AND_FOUR_NONWINNING_TIME_STEPS',
        fractions=FRACTIONS,belief='FIXED_V298_FIT_PREFIX',finite_test_passes=finite_tests)


def run(source_summary,output,finite_tests=None):
    from .b_mechanism_analysis_v299 import summarize
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if (output/'configuration.json').exists() or (output/'summary.json').exists():
        raise FileExistsError('V299 freeze or result already exists')
    old=json.loads(Path(source_summary).read_text())
    if not json.loads(Path(source_summary).with_name('audit.json').read_text())['independent_valid']:
        raise ValueError('V299 requires audited retained V298 B data')
    settings=configuration(source_summary,finite_tests or {})
    (output/'configuration.json').write_text(json.dumps(settings,indent=2)+'\n')
    started,cpu=perf_counter(),process_time(); old_lives={l['lifecycle']:l for l in old['by_lifecycle']}
    parents=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs=[pool.submit(_run_parent,s,old['parent_receipts'][s['parent']],old_lives,output)
            for s in old['source_provenance']['parents']]
        for job in as_completed(jobs): parents.append(job.result())
    parents.sort(key=lambda p:p['parent'])
    lives=sorted([l for p in parents for l in p['lifecycles']],key=lambda l:l['lifecycle'])
    analysis=summarize(lives)
    h2_summary={}
    for node,f in enumerate(FRACTIONS):
        values=[]
        for life in lives:
            rows=life['h2'][node]['rows']
            values.append(dict(disagreement=mean(r['source_actions']!=r['current_actions'] for r in rows),
                fixed_second_disagreement=mean(r['source_actions']!=r['frozen_second_actions'] for r in rows),
                reselection_changed_choice=mean(r['current_actions']!=r['frozen_second_actions'] for r in rows),
                reselection_premium=mean(mean(q['reselection_delta'] for q in r['actions'].values()) for r in rows)))
        h2_summary[str(f)]={k:mean(v[k] for v in values) for k in values[0]}
    accounting=dict(new_environment_observations=0,new_evaluation_games=0,
        inherited_training_raw_tiles=old['accounting']['new_training_environment_observations'],
        inherited_evaluation_counts=old['accounting']['evaluation_counts'],
        inherited_economic_training_raw_tiles=old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN'],
        canonical_input_rows_read=sum(p['reconstruction']['canonical_rows_read'] for p in parents),
        reconstruction_counts=sum_counts(p['reconstruction']['reconstruction_counts'] for p in parents),
        replay_learning_counts=sum_counts(l['replay']['learning_counts'] for l in lives),
        replay_target_counts=sum_counts(l['replay']['target_counts'] for l in lives),
        replay_consolidation_counts=sum_counts(l['replay']['consolidation_counts'] for l in lives),
        replay_buffer_peaks={k:max(l['replay']['buffers'].get(k,0) for l in lives)
            for k in {key for l in lives for key in l['replay']['buffers']}},
        diagnostic_prediction_counts=sum_counts(l['diagnostic_counts'] for l in lives),
        h2_counts=sum_counts(l['h2_counts'] for l in lives),
        native_setup_counts=sum_counts(l['native_setup_counts'] for l in lives),
        source_setup_counts=sum_counts(p['source_setup']['setup_counts'] for p in parents),
        host_label_counts=sum_counts({k:v for k,v in l['label_counts'].items() if k!='buffer_bytes'} for l in lives),
        host_label_buffer_bytes_peak=max(l['label_counts']['buffer_bytes'] for l in lives),
        full_scoring_prediction_counts=sum_counts(s['prediction_counts'] for l in lives for s in l['final_full'].values()),
        full_scoring_setup_counts=sum_counts(s['setup_counts'] for l in lives for s in l['final_full'].values()),
        private_head_setup_counts=sum_counts(l['private_setup']['counts'] for l in lives),
        full_scoring_target_counts=sum_counts({k:v for k,v in s['target_counts'].items() if not k.endswith('_peak')}
            for l in lives for s in l['final_full'].values()),
        full_scoring_target_buffer_doubles_peak=max(s['target_counts'].get('target_buffer_doubles_peak',0)
            for l in lives for s in l['final_full'].values()),
        private_weight_bytes=sum(l['private_setup']['bytes'] for l in lives),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        coordinator_cpu_seconds=process_time()-cpu,wall_seconds=perf_counter()-started,
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents))
    result=dict(schema='acfqp.b_mechanism.v299',status='DIAGNOSTIC_COMPLETE',scientific_gate='NOT_A_FORMAL_GATE',
        settings=settings,source_provenance=old['source_provenance'],by_lifecycle=lives,
        summary=analysis,h2_summary=h2_summary,accounting=accounting,
        parent_receipts=[dict({k:v for k,v in p.items() if k!='lifecycles'},
            lifecycle_ids=[l['lifecycle'] for l in p['lifecycles']]) for p in parents])
    (output/'summary.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps(dict(event='b_mechanism_complete',summary=analysis,h2=h2_summary)),flush=True)
    return result
