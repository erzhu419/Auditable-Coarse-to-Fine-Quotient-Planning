"""Repair frozen module advantages against H2 or fixed-gate continuation."""
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
from scripts import run_controlled_predictive_module_diagnosis_v153 as prior
from scripts import run_controlled_predictive_policy_modules_v151 as modules

SOURCE=ROOT/'reports/controlled_predictive_module_diagnosis_v153'
LIVES,QUERIES=modules.LIVES,modules.QUERIES
ARMS=('H2','ALT','OLD','REPAIR_H2','REPAIR_GATE')
REPAIRS=('REPAIR_H2','REPAIR_GATE')
BASE,REPLICAS,MAX_STEPS,WORKERS,EPOCHS,ALPHA=154*100000000,16,2000,4,32,.1
save,append,read,read_rows=modules.save,modules.append,modules.read,modules.read_rows
load_teacher,leaf_state,RootConsequences,play_game=modules.load_teacher,modules.leaf_state,modules.RootConsequences,modules.play_game


def evaluation_seed(life,replica):
    return BASE+90000000+life*1000000+replica


def physical_id(life,query,arm,replica):
    return f'{life}:{query}:{arm}:{replica}'


def rosters():
    physical=[];logical=[]
    for life in LIVES:
        for query in QUERIES:
            for arm in ARMS:
                for replica in range(REPLICAS):
                    seed=evaluation_seed(life,replica)
                    q=('risk8' if query=='risk1' else 'risk1') if arm=='ALT' else query
                    source_arm='H2' if arm=='ALT' else arm
                    logical.append(dict(life=life,query=query,arm=arm,replica=replica,seed=seed,
                        physical_id=physical_id(life,q,source_arm,replica)))
                    if arm!='ALT':
                        physical.append(dict(life=life,query=query,arm=arm,replica=replica,seed=seed,
                            physical_id=physical_id(life,query,arm,replica),method='H2' if arm=='H2' else 'LEARN8',
                            duration=0 if arm=='H2' else 8))
    return physical,logical


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,arms=list(ARMS),repairs=list(REPAIRS),
        reference='V151 final LEARN8; unchanged through V153 label generation and this single update',
        training_roots=64,roots_per_history_query=8,suffixes_per_root=16,retained_training_branches=4096,
        root_order='V153 frozen order: history, query, H2 then LEARN8 source, slot0..3; all accepted and declined roots',
        targets={'REPAIR_H2':'mean components(M_H2-H_H2)','REPAIR_GATE':'mean components(M_GATE-H_GATE)'},
        initialization='each repair independently loads the same OLD cp4 weights and historical update count',
        learner='unchanged V151 RootConsequences with root unary/pair features plus bias',
        epochs=EPOCHS,alpha=ALPHA,update='warm normalized LMS over all eight root means per history/query; no old V151 labels',
        new_training_updates=4096,new_training_environment_samples=0,
        accounting='both repair views charge the entire retained V153 physical pool; do not double count physical acquisition',
        evaluation_replicas=REPLICAS,physical_evaluation_games=512,logical_evaluation_games=640,
        frozen_old_models=8,frozen_repair_models=16,
        seed_rule='BASE+90000000+life*1000000+replica; common across queries and arms',
        baseline_reuse='ALT uses opposite-query H2 physical trajectory; utility recomputed under target query',
        gate='unchanged strict positive advantage; other policy for eight committed steps, otherwise own H2 for one step',
        representation='SINGLE',p_four=.1,max_steps=MAX_STEPS,workers=WORKERS,version_base=BASE,
        primary='fresh full-game utility; equal16 replicas within history then equal four histories',
        contrasts=['REPAIR_H2-OLD','REPAIR_GATE-OLD','REPAIR_GATE-REPAIR_H2','OLD-H2','OLD-ALT',
            'REPAIR_H2-H2','REPAIR_H2-ALT','REPAIR_GATE-H2','REPAIR_GATE-ALT','ALT-H2'],
        blocks=[[0,3],[4,7],[8,11],[12,15]],
        conditional_seed_ci95='paired mean +/-1.96*sqrt(sum_l(sample_variance(delta_l)/16)/16); conditional on four frozen histories',
        incomplete='retain all cutoff games and costs; affected comparisons incomplete, no replacement',
        frozen_policy='protocol and rosters before fitting; all24 models frozen before evaluation; no tuning or optional stopping')


def extract_source(capsule,run,analysis,frozen,directory):
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V153 must be complete')
    models=[]
    for item in capsule['models']:
        source=SOURCE/item['model_ref'];payload=read(source)
        if prior.prior.model_state(payload)!=item['frozen_state'] or not payload['frozen']:
            raise ValueError('OLD model differs from frozen reference')
        life,query=item['life'],item['query'];target=directory/f'frozen_models/life_{life}/{query}/OLD.json'
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        models.append(dict(life=life,query=query,arm='OLD',source_model_ref=str(source),
            model_ref=str(target.relative_to(directory)),frozen_state=deepcopy(item['frozen_state']),model_bytes=target.stat().st_size))
    if len(models)!=8 or {(m['life'],m['query']) for m in models}!={(l,q) for l in LIVES for q in QUERIES}:
        raise ValueError('all eight OLD models are required')
    return dict(schema='acfqp.module_repair.v154.source',snapshots=deepcopy(capsule['snapshots']),models=models,
        roots=deepcopy(frozen['roots']),source_run_ref=str(SOURCE/'run.json'),source_frozen_ref=str(SOURCE/'frozen_inputs.json'),
        source_traces=[dict(life=l['life'],path=str(SOURCE/l['branch_trace'])) for l in run['lifecycles']],
        cost_refs=deepcopy(capsule['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'),fields=['costs'])]+[
            dict(path=str(ROOT/f'reports/v153_runtime_tmp/{name}_checks.json'),fields=['attempts']) for name in ('core','runner','metrics','analyzer')])


def prepare_examples(capsule):
    grouped={r['root_id']:{} for r in capsule['roots']};rows=0;transitions=0
    for trace in capsule['source_traces']:
        for row in read_rows(trace['path']):
            root=grouped[row['root_id']];suffix=row['suffix'];mode=row['mode']
            root.setdefault(suffix,{})[mode]=dict(components=list(row['result']['components']),status=row['result']['status'])
            rows+=1;transitions+=row['result']['steps']
    examples=[]
    for root in capsule['roots']:
        samples=grouped[root['root_id']]
        if set(samples)!=set(range(16)) or any(set(v)!=set(prior.MODES) for v in samples.values()):
            raise ValueError('a training root lacks its complete four-branch suffix roster')
        if any(v['status'] not in ('WON','LOST') for sample in samples.values() for v in sample.values()):
            raise ValueError('incomplete V153 labels cannot enter either repair')
        targets={}
        for arm,suffix_name in (('REPAIR_H2','H2'),('REPAIR_GATE','GATE')):
            targets[arm]=[sum(samples[s][f'M_{suffix_name}']['components'][k]-
                samples[s][f'H_{suffix_name}']['components'][k] for s in range(16))/16 for k in range(3)]
        examples.append(dict(**{k:deepcopy(root[k]) for k in ('root_id','life','query','source_method','slot','board')},
            suffixes=16,targets=targets))
    if len(examples)!=64 or rows!=4096:raise ValueError('the complete V153 pool is required')
    return examples,dict(retained_rows_read=rows,retained_environment_transitions=transitions,
        new_training_environment_samples=0,matched_budget_views={arm:transitions for arm in REPAIRS})


def fit_models(capsule,examples,directory):
    result=[]
    for source in capsule['models']:
        life,query=source['life'],source['query'];path=directory/source['model_ref'];payload=read(path)
        selected=[e for e in examples if e['life']==life and e['query']==query]
        if len(selected)!=8:raise ValueError('every fit requires all eight same-sample roots')
        for arm in REPAIRS:
            started=perf_counter();model=RootConsequences.from_payload(payload);before=model.state();model.frozen=False
            for _ in range(EPOCHS):
                for example in selected:model.update(example['board'],example['targets'][arm],ALPHA)
            model.freeze();state=model.state();fit_counts=dict(model.counts)
            target=path.parent/f'{arm}.json';save(target,model.to_payload())
            result.append(dict(life=life,query=query,arm=arm,source_model_ref=source['model_ref'],
                model_ref=str(target.relative_to(directory)),before=before,frozen_state=state,fit_counts=fit_counts,
                total_counts=dict(model.counts),setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds,
                root_ids=[e['root_id'] for e in selected],new_updates=model.updates-before['updates'],
                model_bytes=target.stat().st_size,seconds=perf_counter()-started))
    return result


def lifecycle(source,all_models,directory):
    started=perf_counter();life=source['life'];folder=directory/f'life_{life}';folder.mkdir()
    bank={};parents={};leaves={};learners={};data=dict(life=life,teacher_bank={},models=[])
    for query in QUERIES:
        qfolder=folder/query;qfolder.mkdir();parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,qfolder)
        bank[query]=teacher;parents[query]=parent;leaves[query]=leaf
        data['teacher_bank'][query]=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
        for arm in ('OLD',*REPAIRS):
            entry=next(m for m in all_models if m['life']==life and m['query']==query and m['arm']==arm)
            model=RootConsequences.from_payload(read(directory/entry['model_ref']));learners[query,arm]=model
            data['models'].append(dict(query=query,arm=arm,model_ref=entry['model_ref'],before=model.state(),
                setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds))
    trace=folder/'control.jsonl.gz';environment=Counter();policy=Counter();statuses=Counter();games=0
    with gzip.open(trace,'wt') as output:
        for query in QUERIES:
            for arm in ARMS:
                if arm=='ALT':continue
                method='H2' if arm=='H2' else 'LEARN8';duration=0 if arm=='H2' else 8
                for replica in range(REPLICAS):
                    row,_=play_game(bank,query,method,duration,learners.get((query,arm)),evaluation_seed(life,replica),MAX_STEPS)
                    row.update(arm=arm,life=life,replica=replica,physical_id=physical_id(life,query,arm,replica));append(output,row)
                    games+=1;result=row['result'];statuses[result['status']]+=1
                    environment.update(result['environment_counts']);policy.update(result['policy_counts'])
                print(json.dumps(dict(event='arm_evaluated',life=life,query=query,arm=arm,games=REPLICAS)),flush=True)
    for query in QUERIES:
        data['teacher_bank'][query].update(parent_after=leaf_state(parents[query],True),leaf_after=leaf_state(leaves[query]),total_counts=dict(bank[query].counts))
    for record in data['models']:
        model=learners[record['query'],record['arm']];record.update(after=model.state(),counts=dict(model.counts))
    data.update(control_trace=str(trace.relative_to(directory)),physical_games=games,environment_counts=dict(environment),
        policy_counts=dict(policy),statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_module_repair_v154')
    files={Path(__file__).resolve(),ROOT/'specs/MODULE_REPAIR_V154.md',ROOT/'reports/v154_runtime_tmp/run_stage.py'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*module_repair_v154.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source(*(read(SOURCE/n) for n in ('source_capsule.json','run.json','analysis.json','frozen_inputs.json')),directory)
    save(directory/'source_capsule.json',capsule);snapshot_code(directory);physical,logical=rosters()
    data=dict(schema='acfqp.module_repair.v154.run',status='frozen',settings=settings(),
        inherited_cost_refs=capsule['cost_refs'],lifecycles=[])
    save(directory/'frozen_inputs.json',dict(**deepcopy(data),physical_roster=physical,logical_roster=logical,
        training_root_ids=[r['root_id'] for r in capsule['roots']]))
    save(directory/'run.json',data)
    preparation_started=perf_counter();examples,read_work=prepare_examples(capsule)
    read_work['seconds']=perf_counter()-preparation_started;save(directory/'training_examples.json',examples)
    data['training']=dict(examples_ref='training_examples.json',read_work=read_work,models=fit_models(capsule,examples,directory))
    save(directory/'frozen_training.json',deepcopy(data['training']));save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        data['status']='running';save(directory/'run.json',data)
        futures=[pool.submit(lifecycle,s,capsule['models']+data['training']['models'],directory) for s in capsule['snapshots']]
        for future in as_completed(futures):
            data['lifecycles'].append(future.result());data['lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_module_repair_v154')
    run(parser.parse_args().output)

