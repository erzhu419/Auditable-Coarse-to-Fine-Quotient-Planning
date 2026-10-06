"""Replay fixed-policy evidence, anchor existing value, test fresh query transfer."""
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.run_controlled_predictive_policy_consequences_v126 import (
    POLICIES, QUERIES, LIVES, AGES, TRAIN_EPISODES, REPLICAS, MAX_STEPS, WORKERS,
    BLOCK_SIZE, save, append, compact_trace, counter_delta, result)
from scripts.analyze_controlled_predictive_ntuple_learning_v120 import read_rows
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue

BASE=127*100000000
METHODS=tuple(f'{mode}_{policy}' for mode in ('LEARNED','CONSTANT')
              for policy in (*POLICIES,'GPI'))
SOURCE=ROOT/'reports/controlled_predictive_policy_consequences_v126'


def settings():
    return dict(lifecycles=list(LIVES),policies=POLICIES,queries=QUERIES,ages=list(AGES),
        train_episodes=TRAIN_EPISODES,replicas=REPLICAS,max_steps=MAX_STEPS,
        workers=WORKERS,block_size=BLOCK_SIZE,p_four=.1,version_base=BASE,prior_strength=1.)


def evaluation_seed(life,replica):
    return BASE+90000000+life*100000+replica


def extract_source(previous,analysis):
    if not analysis['complete']:
        raise ValueError('V127 needs the completed V126 retained training data')
    snapshots=[]
    for row in previous['snapshots']:
        item={k:deepcopy(row[k]) for k in ('life','rule','models')}
        item['training_trace']=str(SOURCE/f"life_{row['life']}"/'training.jsonl.gz')
        snapshots.append(item)
    return dict(schema='acfqp.anchored_success.v127.source',snapshots=snapshots,
        inherited_costs=dict(**deepcopy(previous['inherited_costs']),
            v126_training=deepcopy(analysis['costs']['training'])))


def source_game(actor,life,policy,replica):
    before=dict(actor.counts);updates=actor.updates
    game=run_episode(evaluation_seed(life,replica),
        lambda board,step:actor.choose(board,POLICIES[policy])['action'],.1,MAX_STEPS)
    row=dict(life=life,policy=policy,query=policy,method='FROZEN_'+policy,checkpoint=None,
        replica=replica,seed=game['seed'],eval_id=f'{life}/FROZEN_{policy}/{replica}',
        result=result(game,policy,policy_counts=counter_delta(actor.counts,before)))
    row['result'].update(source_updates_before=updates,source_updates_after=actor.updates)
    return row,game


def replay_game(model,source):
    started=perf_counter();before=dict(model.counts);updates=model.updates;successes=model.successes
    afterstates=model.replay(source)
    fit=model.train_episode(afterstates,source['result']['status'])
    r=source['result']
    return dict(life=source['life'],policy=source['policy'],episode_index=source['episode_index'],
        source_seed=source['seed'],fit=fit,result=dict(steps=r['steps'],status=r['status'],
            score=r['score'],retained_transitions=r['steps'],environment_counts={},
            learning_counts=counter_delta(model.counts,before),updates_before=updates,
            updates_after=model.updates,successes_before=successes,successes_after=model.successes,
            seconds=perf_counter()-started))


def learned_game(models,life,query,method,age,replica):
    from acfqp.science.controlled_predictive_anchored_success_v127 import choose_gpi
    mode,policy=method.split('_',1);names=list(POLICIES)
    active=models if policy=='GPI' else [models[names.index(policy)]]
    before=[dict(m.counts) for m in models];updates=[m.updates for m in models]
    successes=[m.successes for m in models]
    probabilities,anchors,values,indices=[],[],[],[]
    def act(board,step):
        chosen=choose_gpi(active,board,QUERIES[query],mode=mode)
        probabilities.append(chosen['success_probability']);anchors.append(chosen['anchor_value'])
        values.append(chosen['value'])
        indices.append(chosen['policy_index'] if policy=='GPI' else names.index(policy))
        return chosen['action']
    game=run_episode(evaluation_seed(life,replica),act,.1,MAX_STEPS)
    counts=Counter()
    for m,b in zip(models,before):counts.update(counter_delta(m.counts,b))
    row=dict(life=life,policy=None,query=query,method=method,checkpoint=age,replica=replica,
        seed=game['seed'],eval_id=f'{life}/{method}/{query}/{age}/{replica}',
        result=result(game,query,learning_counts=dict(counts)))
    row['result'].update(updates_before=updates,updates_after=[m.updates for m in models],
        successes_before=successes,successes_after=[m.successes for m in models])
    return dict(**row,**compact_trace(game),chosen_success_probabilities=probabilities,
        chosen_anchor_values=anchors,chosen_values=values,policy_indices=indices)


def empty_block(start):
    return dict(start=start,end=start,games=0,retained_transitions=0,seconds=0.,
        statuses=Counter(),learning_counts=Counter(),updates=0,success_afterstates=0,
        unique_feature_updates=0,analytic_goals=0,censored_afterstates=0)


def add_training(block,row):
    r,fit=row['result'],row['fit'];block['end']=row['episode_index']+1;block['games']+=1
    block['retained_transitions']+=r['steps'];block['seconds']+=r['seconds']
    block['statuses'][r['status']]+=1;block['learning_counts'].update(r['learning_counts'])
    for key in ('updates','success_afterstates','unique_feature_updates','analytic_goals','censored_afterstates'):
        block[key]+=fit[key]


def checkpoint_save(model,folder,directory,age):
    before=dict(model.counts);path=folder/f'checkpoint_{age}.npz';meta=model.save(path)
    return dict(age=age,model_ref=str(path.relative_to(directory)),model_bytes=meta['bytes'],
        updates=model.updates,successes=model.successes,constant=model.global_success_rate,
        save_counts=counter_delta(model.counts,before),save_seconds=meta['seconds'])


def diagnostic(model,row,game,checkpoint):
    started=perf_counter();before=dict(model.counts)
    probabilities=model.probabilities([step['afterstate'] for step in game['steps']])
    return dict(life=row['life'],policy=row['policy'],checkpoint=checkpoint['age'],
        replica=row['replica'],eval_id=row['eval_id'],probabilities=list(probabilities),
        constant=checkpoint['constant'],prefix_updates=checkpoint['updates'],
        prefix_successes=checkpoint['successes'],learning_counts=counter_delta(model.counts,before),
        seconds=perf_counter()-started)


def lifecycle_run(source,directory):
    from acfqp.science.controlled_predictive_anchored_success_v127 import AnchoredSuccess
    started=perf_counter();life=source['life'];folder=directory/f'life_{life}';folder.mkdir()
    rule=LearnedDynamics.from_payload(source['rule']);build=folder/'build'
    data=dict(life=life,policies={},training_trace=str((folder/'replay.jsonl.gz').relative_to(directory)),
        control_trace=str((folder/'control.jsonl.gz').relative_to(directory)),
        diagnostic_trace=str((folder/'diagnostics.jsonl.gz').relative_to(directory)))
    actors,models,heldout,blocks={},{},{},{}
    with gzip.open(directory/data['training_trace'],'wt') as replay_stream, \
         gzip.open(directory/data['control_trace'],'wt') as outer_stream, \
         gzip.open(directory/data['diagnostic_trace'],'wt') as diag_stream:
        for policy in POLICIES:
            (folder/policy).mkdir();actor=NtupleValue.load(source['models'][policy]['path'],rule,build)
            actor.weights.flags.writeable=False;model=AnchoredSuccess(actor,POLICIES[policy],build)
            actors[policy],models[policy],heldout[policy],blocks[policy]=actor,model,[],empty_block(0)
            data['policies'][policy]=dict(source_updates_before=actor.updates,source_updates_after=actor.updates,
                source_load_counts={k:v for k,v in actor.counts.items() if k.startswith('checkpoint_load')},
                source_load_seconds=actor.last_load_seconds,source_setup_counts=dict(actor.setup_counts),
                source_setup_seconds=actor.setup_seconds,learner_setup_counts=dict(model.setup_counts),
                learner_setup_seconds=model.setup_seconds,training_blocks=[],checkpoints=[])
            for replica in range(REPLICAS):
                row,game=source_game(actor,life,policy,replica)
                append(outer_stream,dict(**row,**compact_trace(game)));heldout[policy].append((row,game))
        outer_stream.flush()
        for original in read_rows(Path(source['training_trace'])):
            policy=original['policy'];model=models[policy];done=original['episode_index']+1
            if original['episode_index']!=blocks[policy]['end']:
                raise ValueError('retained policy episode order changed')
            row=replay_game(model,original);append(replay_stream,row);add_training(blocks[policy],row)
            if done%BLOCK_SIZE==0:
                data['policies'][policy]['training_blocks'].append(blocks[policy]);blocks[policy]=empty_block(done)
                replay_stream.flush();save(folder/'lifecycle.json',data)
                print(json.dumps(dict(event='replay_block',life=life,policy=policy,episodes=done,
                    updates=model.updates,successes=model.successes)),flush=True)
            if done in AGES:
                data['policies'][policy]['checkpoints'].append(checkpoint_save(model,folder/policy,directory,done))
                if policy!=list(POLICIES)[-1]:continue
                if any(p['checkpoints'][-1]['age']!=done for p in data['policies'].values()):
                    raise ValueError('retained V126 checkpoint order changed')
                ordered=list(models.values())
                for m in ordered:m.visits.flags.writeable=False;m.wins.flags.writeable=False
                for p in POLICIES:
                    for outer,game in heldout[p]:
                        append(diag_stream,diagnostic(models[p],outer,game,data['policies'][p]['checkpoints'][-1]))
                diag_stream.flush()
                for query in QUERIES:
                    for method in METHODS:
                        for replica in range(REPLICAS):
                            append(outer_stream,learned_game(ordered,life,query,method,done,replica))
                    outer_stream.flush()
                    print(json.dumps(dict(event='outer_query_complete',life=life,query=query,age=done)),flush=True)
                for m in ordered:m.visits.flags.writeable=True;m.wins.flags.writeable=True
                save(folder/'lifecycle.json',data)
        for policy in POLICIES:
            data['policies'][policy]['source_updates_after']=actors[policy].updates
            if blocks[policy]['end']!=TRAIN_EPISODES:
                raise ValueError('retained training corpus incomplete')
        data['peak_weight_bytes']=sum(a.weights.nbytes for a in actors.values())+sum(m.visits.nbytes+m.wins.nbytes for m in models.values())
    data['seconds']=perf_counter()-started;save(folder/'lifecycle.json',data);return data


def snapshot(directory):
    importlib.import_module('acfqp.science.controlled_predictive_anchored_success_v127')
    importlib.import_module('scripts.analyze_controlled_predictive_anchored_success_v127')
    files={Path(__file__).resolve(),ROOT/'specs/ANCHORED_SUCCESS_V127.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    files.update((ROOT/'src/acfqp/science').glob('controlled_predictive_*v127.cpp'))
    files.add(ROOT/'src/acfqp/science/controlled_predictive_ntuple_kernel_v120.cpp')
    files.update((ROOT/'tests').glob('*anchored_success*v127.py'))
    files.add(ROOT/'tests/test_controlled_predictive_policy_consequences_runner_v126.py')
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)


def run(directory):
    directory=directory.resolve();started=perf_counter();directory.mkdir(parents=True,exist_ok=False)
    source=extract_source(json.loads((SOURCE/'source_capsule.json').read_text()),
                          json.loads((SOURCE/'analysis.json').read_text()))
    save(directory/'source_capsule.json',source);snapshot(directory)
    data=dict(schema='acfqp.anchored_success.v127.run',status='running',settings=settings(),
        inherited_costs=source['inherited_costs'],lifecycles=[],executable=sys.executable,platform=platform.platform())
    save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(lifecycle_run,s,directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['lifecycles'].append(future.result());data['lifecycles'].sort(key=lambda r:r['life'])
            save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_anchored_success_v127')
    run(parser.parse_args().output)
