"""Learn fixed-policy outcome vectors and reuse them under unseen queries."""
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'src'))
from scripts.run_controlled_predictive_ntuple_learning_v120 import (
    QUERIES as POLICIES, save, append, compact_trace, counter_delta)
from acfqp.science.controlled_predictive_regime_experience_v115 import run_episode
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue

QUERIES = dict(**POLICIES,
    risk1=dict(reward_weight=1., failure_penalty=1., goal_bonus=1.),
    risk8=dict(reward_weight=1., failure_penalty=8., goal_bonus=8.))
LIVES, AGES, TRAIN_EPISODES, REPLICAS = (0,1,2,3), (256,1024), 1024, 8
MAX_STEPS, WORKERS, BLOCK_SIZE, ALPHA, BASE = 2000, 4, 256, .0025, 126*100000000
METHODS = ('POLICY_reward','POLICY_risk_goal','GPI')
SOURCE = ROOT/'reports/controlled_predictive_confirmed_value_v125/source_capsule.json'


def settings():
    return dict(lifecycles=list(LIVES), policies=POLICIES, queries=QUERIES,
        ages=list(AGES), train_episodes=TRAIN_EPISODES, replicas=REPLICAS,
        max_steps=MAX_STEPS, workers=WORKERS, block_size=BLOCK_SIZE,
        alpha=ALPHA, p_four=.1, version_base=BASE)


def train_seed(life, policy, episode):
    return BASE+1000000+life*100000+list(POLICIES).index(policy)*10000+episode


def evaluation_seed(life, replica):
    return BASE+90000000+life*100000+replica


def extract_source(previous):
    return dict(schema='acfqp.policy_consequences.v126.source',
        snapshots=[{k:deepcopy(row[k]) for k in ('life','rule','models')}
                   for row in previous['snapshots']],
        inherited_costs=deepcopy(previous['inherited_costs']))


def result(game, query, policy_counts=None, learning_counts=None):
    components = [game['return_score']/2048., float(game['status']=='LOST'),
                  float(game['status']=='WON')]
    q = QUERIES[query]
    return dict(score=game['return_score'], status=game['status'], steps=game['steps_count'],
        components=components, utility=q['reward_weight']*components[0]
            -q['failure_penalty']*components[1]+q['goal_bonus']*components[2],
        environment_counts=game['work'], policy_counts=policy_counts or {},
        learning_counts=learning_counts or {}, seconds=game['seconds'])


def source_game(actor, life, policy, *, episode=None, replica=None):
    training = episode is not None
    seed = train_seed(life,policy,episode) if training else evaluation_seed(life,replica)
    before, updates = dict(actor.counts), actor.updates
    game = run_episode(seed, lambda board,step: actor.choose(board,POLICIES[policy])['action'], .1, MAX_STEPS)
    row = dict(life=life, policy=policy, query=policy,
        method='TRAIN' if training else 'FROZEN_'+policy,
        episode_index=episode, checkpoint=None, replica=replica, seed=seed,
        result=result(game,policy,counter_delta(actor.counts,before)))
    row['result'].update(source_updates_before=updates,source_updates_after=actor.updates)
    if not training: row['eval_id']=f'{life}/FROZEN_{policy}/{replica}'
    return row, game


def fit_game(model, row, game):
    before, updates, started = dict(model.counts), model.updates, perf_counter()
    row['fit'] = model.train_episode([step['afterstate'] for step in game['steps']],
                                     [step['score'] for step in game['steps']], game['status'])
    row['result'].update(learning_counts=counter_delta(model.counts,before),
        updates_before=updates, updates_after=model.updates)
    row['result']['seconds'] += perf_counter()-started
    return dict(**row,**compact_trace(game))


def learned_game(models, life, query, method, checkpoint, replica):
    from acfqp.science.controlled_predictive_policy_consequences_v126 import choose_gpi
    names = list(POLICIES)
    active = models if method=='GPI' else [models[names.index(method[7:])]]
    before = [dict(m.counts) for m in models]; updates = [m.updates for m in models]
    vectors, values, selected = [], [], []
    def act(board, step):
        chosen = choose_gpi(active,board,QUERIES[query])
        vectors.append(chosen['consequences']); values.append(chosen['value'])
        selected.append(chosen['policy_index'] if method=='GPI' else names.index(method[7:]))
        return chosen['action']
    game = run_episode(evaluation_seed(life,replica),act,.1,MAX_STEPS)
    counts = Counter()
    for model,previous in zip(models,before): counts.update(counter_delta(model.counts,previous))
    row = dict(life=life,method=method,query=query,policy=None,checkpoint=checkpoint,
        replica=replica,seed=game['seed'],eval_id=f'{life}/{method}/{query}/{checkpoint}/{replica}',
        result=result(game,query,learning_counts=dict(counts)))
    row['result'].update(updates_before=updates,updates_after=[m.updates for m in models])
    return dict(**row,**compact_trace(game),chosen_vectors=vectors,
                chosen_values=values,policy_indices=selected)


def empty_block(start):
    return dict(start=start,end=start,games=0,total_score=0,seconds=0.,
        statuses=Counter(),environment_counts=Counter(),policy_counts=Counter(),
        learning_counts=Counter(),updates=0,censored_afterstates=0,analytic_goals=0,
        target_sums=[0.,0.,0.])


def add_training(block,row):
    r,fit=row['result'],row['fit']
    block['end']=row['episode_index']+1;block['games']+=1
    block['total_score']+=r['score'];block['seconds']+=r['seconds']
    block['statuses'][r['status']]+=1
    for field in ('environment_counts','policy_counts','learning_counts'):
        block[field].update(r[field])
    for field in ('updates','censored_afterstates','analytic_goals'):block[field]+=fit[field]
    for i,value in enumerate(fit['target_sums']):block['target_sums'][i]+=value


def checkpoint_save(model,folder,directory,age,totals):
    before=dict(model.counts)
    metadata=model.save(folder/f'checkpoint_{age}.npz')
    return dict(age=age,model_ref=str((folder/f'checkpoint_{age}.npz').relative_to(directory)),
        model_bytes=metadata['bytes'],updates=model.updates,save_seconds=metadata['seconds'],
        save_counts=counter_delta(model.counts,before),
        constant=[v/model.updates if model.updates else 0. for v in totals])


def diagnostic(model, row, game, checkpoint):
    started=perf_counter();before=dict(model.counts)
    predictions=model.vectors([step['afterstate'] for step in game['steps']])
    if hasattr(predictions,'tolist'):predictions=predictions.tolist()
    return dict(life=row['life'],policy=row['policy'],checkpoint=checkpoint['age'],
        replica=row['replica'],eval_id=row['eval_id'],predictions=predictions,
        constant=checkpoint['constant'],prefix_updates=checkpoint['updates'],
        learning_counts=counter_delta(model.counts,before),seconds=perf_counter()-started)


def lifecycle_run(source,directory):
    from acfqp.science.controlled_predictive_policy_consequences_v126 import PolicyConsequences
    started=perf_counter();life=source['life'];folder=directory/f'life_{life}';folder.mkdir()
    rule=LearnedDynamics.from_payload(source['rule']);build=folder/'build'
    data=dict(life=life,policies={},training_trace=str((folder/'training.jsonl.gz').relative_to(directory)),
        control_trace=str((folder/'control.jsonl.gz').relative_to(directory)),
        diagnostic_trace=str((folder/'diagnostics.jsonl.gz').relative_to(directory)))
    actors,models,heldout,totals={},{},{},{}
    with gzip.open(directory/data['training_trace'],'wt') as train_stream, \
         gzip.open(directory/data['control_trace'],'wt') as outer_stream, \
         gzip.open(directory/data['diagnostic_trace'],'wt') as diag_stream:
        for policy in POLICIES:
            path=folder/policy;path.mkdir()
            actor=NtupleValue.load(source['models'][policy]['path'],rule,build)
            actor.weights.flags.writeable=False
            learner=PolicyConsequences(rule,build)
            actors[policy],models[policy],totals[policy]=actor,learner,[0.,0.,0.]
            data['policies'][policy]=dict(source_updates_before=actor.updates,source_updates_after=actor.updates,
                source_load_counts={k:v for k,v in actor.counts.items() if k.startswith('checkpoint_load')},
                source_load_seconds=actor.last_load_seconds,source_setup_counts=dict(actor.setup_counts),
                source_setup_seconds=actor.setup_seconds,learner_setup_counts=dict(learner.setup_counts),
                learner_setup_seconds=learner.setup_seconds,training_blocks=[],checkpoints=[])
            heldout[policy]=[]
            for replica in range(REPLICAS):
                row,game=source_game(actor,life,policy,replica=replica)
                append(outer_stream,dict(**row,**compact_trace(game)))
                heldout[policy].append((row,game))
        outer_stream.flush()
        previous=0
        for age in AGES:
            for policy in POLICIES:
                learner=models[policy];block=empty_block(previous)
                for episode in range(previous,age):
                    row,game=source_game(actors[policy],life,policy,episode=episode)
                    raw=fit_game(learner,row,game);append(train_stream,raw);add_training(block,row)
                    for i,value in enumerate(row['fit']['target_sums']):totals[policy][i]+=value
                    if (episode+1)%BLOCK_SIZE==0:
                        data['policies'][policy]['training_blocks'].append(block);train_stream.flush()
                        save(folder/'lifecycle.json',data)
                        print(json.dumps(dict(event='training_block',life=life,policy=policy,
                            episodes=episode+1,updates=learner.updates,seconds=block['seconds'])),flush=True)
                        block=empty_block(episode+1)
                cp=checkpoint_save(learner,folder/policy,directory,age,totals[policy])
                data['policies'][policy]['checkpoints'].append(cp)
                data['policies'][policy]['source_updates_after']=actors[policy].updates
            ordered=list(models.values())
            for model in ordered:model.weights.flags.writeable=False
            for policy in POLICIES:
                for row,game in heldout[policy]:
                    append(diag_stream,diagnostic(models[policy],row,game,data['policies'][policy]['checkpoints'][-1]))
            diag_stream.flush()
            for query in QUERIES:
                for method in METHODS:
                    for replica in range(REPLICAS):
                        append(outer_stream,learned_game(ordered,life,query,method,age,replica))
                outer_stream.flush()
                print(json.dumps(dict(event='outer_query_complete',life=life,query=query,age=age)),flush=True)
            for model in ordered:model.weights.flags.writeable=True
            previous=age;save(folder/'lifecycle.json',data)
        data['peak_weight_bytes']=sum(m.weights.nbytes for m in actors.values())+sum(m.weights.nbytes for m in models.values())
    data['seconds']=perf_counter()-started;save(folder/'lifecycle.json',data)
    return data


def snapshot(directory):
    importlib.import_module('acfqp.science.controlled_predictive_policy_consequences_v126')
    importlib.import_module('scripts.analyze_controlled_predictive_policy_consequences_v126')
    files={Path(__file__).resolve(),ROOT/'specs/POLICY_CONSEQUENCES_V126.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    files.update((ROOT/'src/acfqp/science').glob('controlled_predictive_*v126.cpp'))
    files.add(ROOT/'src/acfqp/science/controlled_predictive_ntuple_kernel_v120.cpp')
    files.update((ROOT/'tests').glob('*policy_consequences*v126.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)


def run(directory):
    directory=directory.resolve();started=perf_counter();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source(json.loads(SOURCE.read_text()));save(directory/'source_capsule.json',capsule)
    snapshot(directory)
    data=dict(schema='acfqp.policy_consequences.v126.run',status='running',settings=settings(),
        inherited_costs=capsule['inherited_costs'],lifecycles=[],executable=sys.executable,platform=platform.platform())
    save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(lifecycle_run,source,directory) for source in capsule['snapshots']]
        for future in as_completed(tasks):
            data['lifecycles'].append(future.result());data['lifecycles'].sort(key=lambda r:r['life'])
            save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_policy_consequences_v126')
    run(parser.parse_args().output)
