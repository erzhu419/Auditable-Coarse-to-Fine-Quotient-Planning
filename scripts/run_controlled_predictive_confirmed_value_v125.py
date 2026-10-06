"""Fresh-stream value learning with confirmed contexts and a delay control."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
import json
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts.run_controlled_predictive_ntuple_learning_v120 import (
    QUERIES, ALPHA, LIVES, REPLICAS, MAX_STEPS, WORKERS, save, append,
    counter_delta, compact_trace, game_result)
from scripts.run_controlled_predictive_ntuple_regime_v121 import (
    PHASES, TRAIN_TRANSITIONS, BLOCK_EPISODES, empty_block, add_training)
from scripts.run_controlled_predictive_context_bank_v122 import make_model
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode, observed_rank
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_confirmed_value_v125 import ConfirmedValueBank

SOURCE = ROOT/'reports/controlled_predictive_context_bank_v122'
METHODS, LABELS, BASE = ('CONT', 'DELAY', 'BANK'), (0,524288), 125*100000000


def train_seed(life, query, phase, episode):
    return (BASE+1000000+life*10000000+list(QUERIES).index(query)*4000000
        +list(PHASES).index(phase)*1000000+episode)


def evaluation_seed(life, phase, replica):
    return BASE+90000000+life*100000+list(PHASES).index(phase)*10000+replica


def td_game(model, life, query, phase, method, *, episode=None,
            transitions_before=0, checkpoint=None, replica=None, max_steps=MAX_STEPS):
    training, delayed = episode is not None, method in ('DELAY','BANK')
    seed = train_seed(life,query,phase,episode) if training else evaluation_seed(life,phase,replica)
    q = QUERIES[query]
    before = dict(model.counts) if training or not delayed else {}
    setup_before = dict(model.setup_counts)
    updates_before, setup_seconds = model.updates, model.setup_seconds
    last, last_context = None, None
    contexts, banks, events, commits, targets, target_contexts = [], [], [], [], [], []
    pending_before = len(model.pending_transitions) if delayed else 0
    router_before = model.router.observations_seen if delayed else None

    def observe(board, index):
        event = model.observe(observed_rank(dict(afterstate=last, next_board=board)))
        if event is not None:
            events.append(dict(event, observed_action_index=index))

    def finish(target, target_context, index):
        # Even analytic goals and cutoffs consume an observed no-target row.
        record = model.finish_transition(last if target is not None else None,
            last_context, target, target_context)
        targets.append(target); target_contexts.append(target_context)
        if record is not None:
            commits.append(dict(record, observed_action_index=index))

    def act(board, step):
        nonlocal last, last_context
        if delayed and last is not None:
            observe(board,step-1)
        chosen = model.choose(board,q)
        if training and last is not None:
            eligible = max(last) < model.rule.goal_rank
            if delayed:
                finish(chosen['value'] if eligible else None,
                    chosen['context_id'] if eligible else None,step-1)
            elif eligible:
                model.update(last,chosen['value'],ALPHA)
        last, last_context = chosen['afterstate'], chosen.get('context_id')
        if delayed:
            contexts.append(chosen['context_id']); banks.append(chosen['bank_id'])
        return chosen['action']

    game = run_episode(seed,act,PHASES[phase],max_steps)
    started = perf_counter()
    if delayed and last is not None:
        observe(game['final_board'],game['steps_count']-1)
    eligible_terminal = training and game['status']=='LOST' and last is not None
    if training and last is not None:
        if delayed:
            finish(-q['failure_penalty'] if eligible_terminal else None,None,game['steps_count']-1)
        elif eligible_terminal:
            model.update(last,-q['failure_penalty'],ALPHA)
    game['seconds'] += perf_counter()-started
    learn = counter_delta(model.counts,before)
    if delayed:
        if model.router.observations_seen-router_before != game['steps_count']:
            raise AssertionError('each post-action rank must be observed once')
        if training and len(targets)!=game['steps_count']:
            raise AssertionError('each observed transition needs one queue row')
    elif model.updates-updates_before != (game['steps_count']-int(game['status'] in ('WON','CUTOFF')) if training else 0):
        raise AssertionError('immediate TD terminal count differs')
    result = game_result(game,query,learn)
    result.update(updates_before=updates_before, updates_after=model.updates,
        setup_counts=counter_delta(model.setup_counts,setup_before),
        setup_seconds=model.setup_seconds-setup_seconds,
        pending_before=pending_before,
        pending_after=len(model.pending_transitions) if delayed else 0,
        router_observations_before=router_before,
        router_observations_after=model.router.observations_seen if delayed else None)
    row = dict(life=life,query=query,phase=phase,method=method,checkpoint=checkpoint,
        replica=replica,seed=seed,max_steps=max_steps,result=result)
    if training:
        row.update(episode_index=episode,transitions_before=transitions_before,
            transitions_after=transitions_before+game['steps_count'],
            terminal_target=eligible_terminal,analytic_terminal=game['status']=='WON',
            censored_last_update=game['status']=='CUTOFF')
    else:
        row.update(eval_id=f'{life}/{query}/{phase}/{method}/{checkpoint}/{replica}',reused_from=None)
    return row,dict(**row,**compact_trace(game),context_ids=contexts,bank_ids=banks,
        final_context_id=model.context_id if delayed else None,
        routing_events=events,commit_events=commits,td_targets=targets,target_context_ids=target_contexts)


def evaluate(model, life, query, phase, method, label, stream, reuse=None):
    if reuse is not None:
        rows=deepcopy(reuse)
        for row in rows:
            row['reused_from']=row['eval_id']
            row.update(method=method,checkpoint=label,eval_id=f'{life}/{query}/{phase}/{method}/{label}/{row["replica"]}')
        return rows
    rows=[]
    for replica in range(REPLICAS):
        started=perf_counter()
        actor=model.evaluation_copy() if method in ('DELAY','BANK') else model
        copy_seconds=perf_counter()-started if method in ('DELAY','BANK') else 0.
        row,raw=td_game(actor,life,query,phase,method,checkpoint=label,replica=replica)
        row['result']['evaluation_copy_seconds']=copy_seconds
        rows.append(row); append(stream,raw)
    stream.flush()
    return rows


def checkpoint(model, life, query, phase, method, label, reference, folder, directory, stream, reuse=None):
    cp=dict(label=label,transitions=label,updates=model.updates,model_ref=reference)
    if method in ('DELAY','BANK'):
        cp['bank_manifest']=model.to_payload()
    if label:
        started=perf_counter(); before=dict(model.counts)
        if method in ('DELAY','BANK'):
            destination=folder/f'checkpoint_{label}'
            manifest=model.save(destination)
            for entry in manifest['model_files']:
                entry['path']=str(Path(entry['path']).relative_to(directory))
            save(destination/'manifest.json',manifest)
            cp.update(model_ref=str((destination/'manifest.json').relative_to(directory)),
                bank_manifest=manifest,model_bytes=sum(entry['bytes'] for entry in manifest['model_files']))
        else:
            path=folder/f'checkpoint_{label}.npz'
            metadata=model.save(path)
            cp.update(model_ref=str(path.relative_to(directory)),model_metadata=metadata,model_bytes=metadata['bytes'])
        cp.update(save_seconds=perf_counter()-started,save_counts=counter_delta(model.counts,before))
    cp['evaluations']=evaluate(model,life,query,phase,method,label,stream,reuse)
    return cp


def train_phase(model, life, query, phase, method, result, stream, persist):
    transitions=episode=0
    block=empty_block(0,0)
    while transitions<TRAIN_TRANSITIONS:
        row,raw=td_game(model,life,query,phase,method,episode=episode,
            transitions_before=transitions,max_steps=min(MAX_STEPS,TRAIN_TRANSITIONS-transitions))
        if row['result']['steps']<=0:
            raise AssertionError('fresh game must perform an action')
        append(stream,raw); add_training(block,row)
        block.setdefault('setup_counts',Counter()).update(row['result']['setup_counts'])
        block['setup_seconds']=block.get('setup_seconds',0.)+row['result']['setup_seconds']
        transitions,episode=row['transitions_after'],episode+1
        if episode%BLOCK_EPISODES==0 or transitions==TRAIN_TRANSITIONS:
            stream.flush();result['training_blocks'].append(block)
            block=empty_block(episode,transitions)
            persist()
            print(json.dumps(dict(event='training_block_complete',life=life,query=query,phase=phase,
                method=method,transitions=transitions,episodes=episode,updates=model.updates)),flush=True)
    result.update(final_updates=model.updates,final_transitions=transitions,training_episodes=episode)


def lifecycle_run(source,directory):
    started=perf_counter();life=source['life']
    folder=directory/f'life_{life}';folder.mkdir()
    build=folder/'build';build.mkdir()
    lifecycle=dict(life=life,queries={})
    def persist(): save(folder/'lifecycle.json',lifecycle)
    for query in QUERIES:
        qfolder=folder/query;qfolder.mkdir()
        rule=LearnedDynamics.from_payload(source['rule']);origin=source['models'][query]
        result=dict(training_trace=str((qfolder/'training.jsonl.gz').relative_to(directory)),
            control_trace=str((qfolder/'control.jsonl.gz').relative_to(directory)),
            model_setup=[],context_initialization={},phases={})
        lifecycle['queries'][query]=result
        models={}
        for method in ('FROZEN_A',)+METHODS:
            model,setup=make_model(rule,build,method,'B',origin)
            result['model_setup'].append(setup)
            if method in ('DELAY','BANK'):
                context_start=perf_counter()
                model=ConfirmedValueBank(model,source['initial_ranks'][query],build,method=method)
                result['context_initialization'][method]=dict(seconds=perf_counter()-context_start,
                    router=model.router.to_payload(),source=source['initial_rank_sources'][query])
            models[method]=model
        refs={method:origin['path'] for method in models}
        with gzip.open(directory/result['training_trace'],'wt') as training, \
                gzip.open(directory/result['control_trace'],'wt') as controls:
            for phase,p_four in PHASES.items():
                pfolder=qfolder/phase;pfolder.mkdir()
                phase_result=dict(p_four=p_four,methods={})
                result['phases'][phase]=phase_result
                frozen=checkpoint(models['FROZEN_A'],life,query,phase,'FROZEN_A',0,
                    refs['FROZEN_A'],pfolder,directory,controls)
                phase_result['methods']['FROZEN_A']=dict(checkpoints=[frozen])
                for method in METHODS:
                    mfolder=pfolder/method;mfolder.mkdir()
                    value=dict(training_blocks=[],checkpoints=[])
                    phase_result['methods'][method]=value
                    value['checkpoints'].append(checkpoint(models[method],life,query,phase,method,0,
                        refs[method],mfolder,directory,controls,
                        frozen['evaluations'] if phase=='B' and method=='CONT' else None))
                    persist()
                    train_phase(models[method],life,query,phase,method,value,training,persist)
                    final=checkpoint(models[method],life,query,phase,method,TRAIN_TRANSITIONS,
                        refs[method],mfolder,directory,controls)
                    value['checkpoints'].append(final);refs[method]=final['model_ref']
                    persist()
        del models
    lifecycle['seconds']=perf_counter()-started;persist()
    return lifecycle


def snapshot(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_confirmed_value_v125')
    files={Path(__file__),ROOT/'specs/CONFIRMED_VALUE_V125.md',
        ROOT/'src/acfqp/science/controlled_predictive_ntuple_kernel_v120.cpp',
        ROOT/'tests/test_controlled_predictive_confirmed_value_v125.py',
        ROOT/'tests/test_controlled_predictive_confirmed_value_runner_v125.py',
        ROOT/'tests/test_analyze_controlled_predictive_confirmed_value_v125.py'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):
                files.add(path)
    for path in files:
        target=directory/'source'/path.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory.mkdir(parents=True,exist_ok=False)
    old=json.loads((SOURCE/'source_capsule.json').read_text())
    capsule=dict(schema='acfqp.confirmed_value.v125.source',
        snapshots=[{k:deepcopy(s[k]) for k in ('life','rule','models','initial_ranks','initial_rank_sources')}
            for s in old['snapshots']],inherited_costs=deepcopy(old['inherited_costs']['shared_v120']))
    save(directory/'source_capsule.json',capsule);snapshot(directory)
    result=dict(schema='acfqp.confirmed_value.v125.run',status='running',
        settings=dict(lifecycles=list(LIVES),queries=QUERIES,phases=PHASES,methods=METHODS,
            checkpoints=LABELS,train_transitions=TRAIN_TRANSITIONS,replicas=REPLICAS,
            max_steps=MAX_STEPS,workers=WORKERS,alpha=ALPHA,version_base=BASE),
        inherited_costs=capsule['inherited_costs'],lifecycles=[],executable=sys.executable,platform=platform.platform())
    save(directory/'run.json',result)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for future in as_completed([pool.submit(lifecycle_run,s,directory) for s in capsule['snapshots']]):
            result['lifecycles'].append(future.result());result['lifecycles'].sort(key=lambda x:x['life'])
            save(directory/'run.json',result)
    result.update(status='complete',seconds=perf_counter()-started)
    save(directory/'run.json',result)
    print(json.dumps(dict(status='complete',seconds=result['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_confirmed_value_v125')
    run(parser.parse_args().output)
