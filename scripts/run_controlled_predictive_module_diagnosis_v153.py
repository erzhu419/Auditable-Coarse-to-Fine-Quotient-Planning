"""Diagnose frozen module estimates under H2 and repeated-gate continuation."""
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
from scripts import run_controlled_predictive_module_replication_v152 as prior
from acfqp.science.controlled_predictive_module_diagnosis_v153 import run_branch
from acfqp.science.controlled_predictive_policy_modules_v151 import utility

SOURCE=ROOT/'reports/controlled_predictive_module_replication_v152'
LIVES,QUERIES=prior.LIVES,prior.QUERIES
SOURCE_METHODS,MODES=('H2','LEARN8'),('H_H2','M_H2','H_GATE','M_GATE')
BASE,SUFFIXES,MAX_STEPS,WORKERS=153*100000000,16,2000,4
REPLICAS=(0,4,8,12)
save,append,read,load_teacher,leaf_state=prior.save,prior.append,prior.read,prior.load_teacher,prior.leaf_state
RootConsequences=prior.RootConsequences


def branch_seed(life,query,source_method,slot,suffix):
    return BASE+20000000+life*1000000+list(QUERIES).index(query)*100000+SOURCE_METHODS.index(source_method)*10000+slot*100+suffix


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,source_methods=list(SOURCE_METHODS),modes=list(MODES),
        checkpoint=4,duration=8,source_replicas=list(REPLICAS),roots_per_source_cell=4,roots=64,suffixes=SUFFIXES,
        physical_branches=4096,max_steps=MAX_STEPS,p_four=.1,workers=WORKERS,version_base=BASE,
        root_selection='replica=4*slot; boundary index=floor((2*slot+1)*boundary_count/8); slot=0..3',
        seeds='BASE+20000000+life*1000000+query_index*100000+source_index*10000+slot*100+suffix; shared across modes',
        continuation='H_H2: own forever; M_H2: other8 then own; H_GATE: own1 then gate; M_GATE: other8 then gate',
        gate='unchanged frozen cp4 LEARN8; fresh gate at prefix end; branch absolute step; own query for each teacher',
        horizon='2000 transitions from each root for all modes; no initial spawns; winning swipe spawns',
        prediction='all root components, utility advantages and strict-positive decisions frozen before sampling',
        new_training_updates=0,primary='equal four roots within history then equal four histories; separate query/source',
        estimands=['delta_h2','delta_gate','continuation_shift','error_h2','error_gate','mse_excess_h2','mse_excess_gate','policy_gain_h2','policy_gain_gate'],
        intervals='pointwise conditional seed CI: mean +/-1.96*sqrt(sum_root(weight_root^2*sample_variance(metric_suffix)/16)); fixed histories and roots',
        accepted_subset='equal accepted roots within history then equal four histories; empty-history subset incomplete',
        blocks=[[0,3],[4,7],[8,11],[12,15]],
        mse='mse_excess=p^2-2*p*delta; plug-in squared error of root mean includes Monte Carlo variance',
        incomplete='retain cutoff branches and all costs; incomplete root/comparison excluded from complete-cohort claims; no replacements',
        frozen_policy='no fitting, checkpoint selection, extra favorable suffixes, or gate changes')


def select_root(row,slot,source_ref):
    boundaries=[i for i,c in enumerate(row['choices']) if c['module_decision']['boundary']]
    index=((2*slot+1)*len(boundaries))//8;step=boundaries[index]
    board=list(row['initial_board'] if step==0 else row['choices'][step-1]['afterstate'])
    if step:board[row['spawned_cells'][step-1]]=row['spawned_ranks'][step-1]
    life,query,method=row['life'],row['query'],row['method']
    return dict(root_id=f'{life}:{query}:{method}:{slot}',life=life,query=query,source_method=method,
        slot=slot,replica=row['replica'],source_ref=str(source_ref),source_physical_id=row['physical_id'],
        source_seed=row['seed'],source_step=step,source_boundary_count=len(boundaries),selected_boundary_index=index,board=board)


def branch_roster(roots):
    return [dict(branch_id=f'{r["root_id"]}:{suffix}:{mode}',root_id=r['root_id'],suffix=suffix,mode=mode,
        seed=branch_seed(r['life'],r['query'],r['source_method'],r['slot'],suffix))
        for r in roots for suffix in range(SUFFIXES) for mode in MODES]


def extract_source(capsule,run,analysis,directory):
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V152 must be complete')
    models=[]
    for entry in capsule['models']:
        if entry['checkpoint']!=4 or entry['duration']!=8:continue
        life,query=entry['life'],entry['query'];source=SOURCE/entry['model_ref'];payload=read(source)
        if prior.model_state(payload)!=entry['frozen_state'] or not payload['frozen']:
            raise ValueError('source model differs from frozen V152 checkpoint')
        target=directory/f'frozen_models/life_{life}/{query}/module_8.json'
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        models.append(dict(life=life,query=query,checkpoint=4,duration=8,source_model_ref=str(source),
            model_ref=str(target.relative_to(directory)),frozen_state=prior.model_state(payload),model_bytes=target.stat().st_size))
    if len(models)!=8 or {(m['life'],m['query']) for m in models}!={(l,q) for l in LIVES for q in QUERIES}:
        raise ValueError('all eight final eight-step models are required')
    return dict(schema='acfqp.module_diagnosis.v153.source',snapshots=deepcopy(capsule['snapshots']),models=models,
        source_run_ref=str(SOURCE/'run.json'),
        source_traces=[dict(life=l['life'],path=str(SOURCE/l['control_trace'])) for l in run['lifecycles']],
        cost_refs=deepcopy(capsule['cost_refs'])+[
            dict(path=str(SOURCE/'analysis.json'),fields=['costs']),
            dict(path=str(ROOT/'reports/v152_runtime_tmp/runner_checks.json'),fields=['attempts']),
            dict(path=str(ROOT/'reports/v152_runtime_tmp/analyzer_checks.json'),fields=['attempts'])])


def prepare_roots(capsule,directory):
    started=perf_counter();roots=[];rows_read=0;models={};records=[]
    for entry in capsule['models']:
        model=RootConsequences.from_payload(read(directory/entry['model_ref']));key=entry['life'],entry['query']
        models[key]=model;records.append(dict(life=key[0],query=key[1],model_ref=entry['model_ref'],before=model.state(),
            setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds))
    refs={(r['life'],r['query']):r['model_ref'] for r in records}
    selected={}
    for trace in capsule['source_traces']:
        wanted={(q,m,r) for q in QUERIES for m in SOURCE_METHODS for r in REPLICAS};found=set()
        for row in prior.prior.read_rows(trace['path']):
            rows_read+=1;key=row['query'],row['method'],row['replica']
            if key not in wanted:continue
            if row['checkpoint']!=(-1 if row['method']=='H2' else 4):continue
            selected[(trace['life'],*key)]=select_root(row,REPLICAS.index(row['replica']),trace['path']);found.add(key)
            if found==wanted:break
        if found!=wanted:raise ValueError('required frozen source games are missing')
    for life in LIVES:
        for query in QUERIES:
            for method in SOURCE_METHODS:
                for slot,replica in enumerate(REPLICAS):
                    root=selected[(life,query,method,replica)];model=models[life,query];before=dict(model.counts)
                    components=model.predict(root['board']);advantage=utility(components,query)
                    root.update(model_ref=refs[life,query],prediction=dict(components=components,advantage=advantage,accept=advantage>0),
                        prediction_counts=prior.prior.delta(model.counts,before))
                    roots.append(root)
    for record in records:
        model=models[record['life'],record['query']]
        record.update(after=model.state(),counts=dict(model.counts))
    return roots,dict(prediction_models=records,source_rows_read=rows_read,source_games_selected=len(selected),seconds=perf_counter()-started)


def lifecycle(source,models,roots,directory):
    started=perf_counter();life=source['life'];folder=directory/f'life_{life}';folder.mkdir()
    bank={};parents={};leaves={};learners={};data=dict(life=life,teacher_bank={},models=[])
    for query in QUERIES:
        qfolder=folder/query;qfolder.mkdir();parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,qfolder)
        bank[query]=teacher;parents[query]=parent;leaves[query]=leaf
        data['teacher_bank'][query]=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
        entry=next(m for m in models if m['life']==life and m['query']==query)
        model=RootConsequences.from_payload(read(directory/entry['model_ref']));learners[query]=model
        data['models'].append(dict(query=query,model_ref=entry['model_ref'],before=model.state(),
            setup_counts=dict(model.setup_counts),setup_seconds=model.setup_seconds))
    trace=folder/'branches.jsonl.gz';environment=Counter();policy=Counter();statuses=Counter();physical=0
    with gzip.open(trace,'wt') as output:
        for root in roots:
            if root['life']!=life:continue
            for suffix in range(SUFFIXES):
                seed=branch_seed(life,root['query'],root['source_method'],root['slot'],suffix)
                for mode in MODES:
                    row=run_branch(root['board'],bank,root['query'],mode,learners[root['query']],seed,MAX_STEPS,.1)
                    row.update(branch_id=f'{root["root_id"]}:{suffix}:{mode}',root_id=root['root_id'],
                        life=life,source_method=root['source_method'],slot=root['slot'],suffix=suffix)
                    append(output,row);result=row['result'];physical+=1
                    environment.update(result['environment_counts']);policy.update(result['policy_counts']);statuses[result['status']]+=1
            print(json.dumps(dict(event='root_completed',life=life,root_id=root['root_id'],branches=SUFFIXES*len(MODES))),flush=True)
    for query in QUERIES:
        data['teacher_bank'][query].update(parent_after=leaf_state(parents[query],True),leaf_after=leaf_state(leaves[query]),total_counts=dict(bank[query].counts))
    for record in data['models']:
        model=learners[record['query']];record.update(after=model.state(),counts=dict(model.counts))
    data.update(branch_trace=str(trace.relative_to(directory)),physical_branches=physical,
        environment_counts=dict(environment),policy_counts=dict(policy),statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_module_diagnosis_v153')
    files={Path(__file__).resolve(),ROOT/'specs/MODULE_DIAGNOSIS_V153.md',ROOT/'reports/v153_runtime_tmp/run_stage.py'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*module_diagnosis_v153.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source(*(read(SOURCE/n) for n in ('source_capsule.json','run.json','analysis.json')),directory)
    save(directory/'source_capsule.json',capsule);snapshot_code(directory)
    roots,preparation=prepare_roots(capsule,directory)
    data=dict(schema='acfqp.module_diagnosis.v153.run',status='frozen',settings=settings(),
        inherited_cost_refs=capsule['cost_refs'],lifecycles=[])
    save(directory/'frozen_inputs.json',dict(**deepcopy(data),roots=roots,preparation=preparation,branch_roster=branch_roster(roots)))
    save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        data['status']='running';save(directory/'run.json',data)
        futures=[pool.submit(lifecycle,s,capsule['models'],roots,directory) for s in capsule['snapshots']]
        for future in as_completed(futures):
            data['lifecycles'].append(future.result());data['lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_module_diagnosis_v153')
    run(parser.parse_args().output)
