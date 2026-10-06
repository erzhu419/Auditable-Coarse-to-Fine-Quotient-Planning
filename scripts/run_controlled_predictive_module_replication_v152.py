"""Replicate all frozen V151 checkpoints on common fresh full-game seeds."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_policy_modules_v151 as prior

SOURCE=ROOT/'reports/controlled_predictive_policy_modules_v151'
LIVES,QUERIES,METHODS,DURATIONS=prior.LIVES,prior.QUERIES,prior.METHODS,prior.DURATIONS
BASE,REPLICAS,CHECKPOINTS,MAX_STEPS,WORKERS=152*100000000,16,tuple(range(5)),2000,4
save,append,read,load_teacher,leaf_state=prior.save,prior.append,prior.read,prior.load_teacher,prior.leaf_state
RootConsequences,play_game=prior.RootConsequences,prior.play_game


def evaluation_seed(life,replica):
    return BASE+90000000+life*1000000+replica


def physical_key(life,query,checkpoint,method,replica):
    if method=='H2' or (checkpoint==0 and method.startswith('LEARN')):
        return life,query,-1,'H2',replica
    if method=='ALT':
        return life,('risk8' if query=='risk1' else 'risk1'),-1,'H2',replica
    return life,query,checkpoint,method,replica


def physical_id(life,query,checkpoint,method,replica):
    return f'{life}:{query}:{checkpoint}:{method}:{replica}'


def zero_checkpoint_valid(payload):
    return payload['frozen'] and payload['updates']==0 and payload['weights']==[]


def model_state(payload):
    return {key:deepcopy(payload[key]) for key in ('radix','updates','frozen','weights')}


def rosters():
    physical=[];logical=[]
    for life in LIVES:
        for query in QUERIES:
            for checkpoint,methods in [(-1,('H2',))]+[(c,('LEARN1','LEARN8')) for c in CHECKPOINTS if c]:
                for method in methods:
                    for replica in range(REPLICAS):
                        physical.append(dict(physical_id=physical_id(life,query,checkpoint,method,replica),
                            life=life,query=query,checkpoint=checkpoint,method=method,
                            duration=int(method[-1]) if method.startswith('LEARN') else 0,
                            replica=replica,seed=evaluation_seed(life,replica)))
            for checkpoint in CHECKPOINTS:
                for method in METHODS:
                    for replica in range(REPLICAS):
                        logical.append(dict(physical_id=physical_id(*physical_key(life,query,checkpoint,method,replica)),
                            life=life,query=query,checkpoint=checkpoint,method=method,
                            duration=int(method[-1]) if method.startswith('LEARN') else int(method=='ALT'),
                            replica=replica,seed=evaluation_seed(life,replica)))
    return physical,logical


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,durations=list(DURATIONS),methods=list(METHODS),
        checkpoints=list(CHECKPOINTS),evaluation_replicas=REPLICAS,physical_evaluation_games=1152,
        logical_evaluation_games=2560,physical_baseline_games=128,physical_learned_games=1024,
        frozen_models=80,loaded_learned_models=64,new_training_transitions=0,new_training_updates=0,
        representation='SINGLE',p_four=.1,max_steps=MAX_STEPS,workers=WORKERS,version_base=BASE,
        seed_rule='BASE+90000000+life*1000000+replica; identical across queries, methods and checkpoints',
        learner='unchanged frozen V151 RootConsequences; no fitting or new labels',
        gate='strict positive learned total advantage; commit full duration; otherwise own H2 one step',
        baseline_reuse='one physical H2 per life/query/replica; ALT references other policy and rescores target utility',
        checkpoint_zero_reuse='alias own H2 only after verifying frozen empty weights and zero updates',
        accounting='charge physical traces once; aliases carry no extra environment or policy work; no claimed runtime for skipped zero-model predictions',
        primary='all five checkpoints; equal 16 replicas within each of four frozen histories then equal histories',
        contrasts=['LEARN1-H2','LEARN8-H2','LEARN8-LEARN1','ALT-H2','LEARN1-ALT','LEARN8-ALT'],
        increments=['0->1','1->2','2->3','3->4','0->4'],
        blocks=[[0,3],[4,7],[8,11],[12,15]],
        conditional_seed_ci95='paired mean +/-1.96*sqrt(sum_l(sample_variance(delta_l)/16)/16); conditional on four frozen histories',
        incomplete='retain every cutoff and its cost; affected comparisons and intervals incomplete, no replacement',
        frozen_policy='no evaluation-dependent refit, hyperparameter choice, checkpoint choice or early stopping')


def extract_source(capsule,run,analysis,directory):
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V151 must be complete')
    models=[]
    for lifecycle in run['lifecycles']:
        life=lifecycle['life']
        for checkpoint in lifecycle['checkpoints']:
            cp=checkpoint['checkpoint']
            for query in QUERIES:
                for duration in DURATIONS:
                    original=checkpoint['models'][query][str(duration)]
                    source=SOURCE/original['model_ref'];payload=read(source)
                    if model_state(payload)!=original['frozen_state'] or not payload['frozen']:
                        raise ValueError('V151 model does not match its frozen checkpoint')
                    if cp==0 and not zero_checkpoint_valid(payload):
                        raise ValueError('checkpoint zero is not exactly the frozen zero model')
                    target=directory/f'frozen_models/life_{life}/checkpoint_{cp}/{query}/module_{duration}.json'
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
                    models.append(dict(life=life,query=query,checkpoint=cp,duration=duration,
                        source_model_ref=str(source),model_ref=str(target.relative_to(directory)),
                        frozen_state=model_state(payload),model_bytes=target.stat().st_size))
    expected={(life,q,cp,d) for life in LIVES for q in QUERIES for cp in CHECKPOINTS for d in DURATIONS}
    if len(models)!=80 or {(m['life'],m['query'],m['checkpoint'],m['duration']) for m in models}!=expected:
        raise ValueError('all 80 frozen models are required')
    return dict(schema='acfqp.module_replication.v152.source',snapshots=deepcopy(capsule['snapshots']),models=models,
        source_run_ref=str(SOURCE/'run.json'),cost_refs=deepcopy(capsule['cost_refs'])+[
            dict(path=str(SOURCE/'analysis.json'),fields=['costs']),
            dict(path=str(ROOT/'reports/v151_runtime_tmp/provisional_summary.json'),fields=['work','seconds']),
            dict(path=str(ROOT/'reports/v151_runtime_tmp/runner_checks.json'),fields=['attempts']),
            dict(path=str(ROOT/'reports/v151_runtime_tmp/analyzer_checks.json'),fields=['work_refs','attempts'])])


def lifecycle(source,capsule_models,directory):
    started=perf_counter();life=source['life'];folder=directory/f'life_{life}';folder.mkdir()
    bank={};parents={};leaves={};data=dict(life=life,teacher_bank={},models=[])
    for query in QUERIES:
        qfolder=folder/query;qfolder.mkdir()
        parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,qfolder)
        bank[query]=teacher;parents[query]=parent;leaves[query]=leaf
        data['teacher_bank'][query]=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
    environment=Counter();policy=Counter();statuses=Counter();games=0
    trace=folder/'control.jsonl.gz'
    def record(output,query,checkpoint,method,duration,model,replica):
        nonlocal games
        row,_=play_game(bank,query,method,duration,model,evaluation_seed(life,replica),MAX_STEPS)
        row.update(physical_id=physical_id(life,query,checkpoint,method,replica),
            life=life,checkpoint=checkpoint,replica=replica)
        append(output,row);games+=1;statuses[row['result']['status']]+=1
        environment.update(row['result']['environment_counts']);policy.update(row['result']['policy_counts'])
    with gzip.open(trace,'wt') as output:
        for query in QUERIES:
            for replica in range(REPLICAS):record(output,query,-1,'H2',0,None,replica)
        for entry in capsule_models:
            if entry['life']!=life or entry['checkpoint']==0:continue
            model=RootConsequences.from_payload(read(directory/entry['model_ref']));before=model.state()
            query,cp,duration=entry['query'],entry['checkpoint'],entry['duration']
            for replica in range(REPLICAS):record(output,query,cp,f'LEARN{duration}',duration,model,replica)
            data['models'].append(dict(query=query,checkpoint=cp,duration=duration,model_ref=entry['model_ref'],
                before=before,after=model.state(),counts=dict(model.counts),
                setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds))
            print(json.dumps(dict(event='frozen_model_evaluated',life=life,query=query,checkpoint=cp,duration=duration)),flush=True)
    for query in QUERIES:
        data['teacher_bank'][query].update(parent_after=leaf_state(parents[query],True),leaf_after=leaf_state(leaves[query]),
            total_counts=dict(bank[query].counts))
    data.update(control_trace=str(trace.relative_to(directory)),physical_games=games,
        environment_counts=dict(environment),policy_counts=dict(policy),statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_module_replication_v152')
    files={Path(__file__).resolve(),ROOT/'specs/MODULE_REPLICATION_V152.md',ROOT/'reports/v152_runtime_tmp/run_stage.py'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*module_replication_v152.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    source=extract_source(*(read(SOURCE/name) for name in ('source_capsule.json','run.json','analysis.json')),directory)
    save(directory/'source_capsule.json',source);snapshot_code(directory)
    physical,logical=rosters()
    data=dict(schema='acfqp.module_replication.v152.run',status='frozen',settings=settings(),
        inherited_cost_refs=source['cost_refs'],lifecycles=[])
    save(directory/'frozen_inputs.json',dict(**deepcopy(data),physical_roster=physical,logical_roster=logical))
    save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        data['status']='running';save(directory/'run.json',data)
        futures=[pool.submit(lifecycle,s,source['models'],directory) for s in source['snapshots']]
        for future in as_completed(futures):
            data['lifecycles'].append(future.result());data['lifecycles'].sort(key=lambda r:r['life'])
            save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_module_replication_v152')
    run(parser.parse_args().output)
