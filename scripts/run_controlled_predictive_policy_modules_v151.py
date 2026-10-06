"""Learn conditional one/eight-step policy modules across four experience batches."""
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
from scripts import run_controlled_predictive_paired_advantage_v144 as old
from acfqp.science.controlled_predictive_policy_modules_v151 import RootConsequences, ModuleGate, run_module_branch

SOURCE=ROOT/'reports/controlled_predictive_crossfit_shrinkage_v150'
LIVES,QUERIES,DURATIONS,METHODS=(0,1,2,3),old.QUERIES,(1,8),('H2','ALT','LEARN1','LEARN8')
BASE,BATCHES,BUDGET,SUFFIXES,REPLICAS,MAX_STEPS,EPOCHS,ALPHA,WORKERS=151*100000000,4,65536,8,4,2000,32,.1,4
save,append,read_rows,load_teacher,leaf_state,delta=old.save,old.append,old.read_rows,old.load_teacher,old.leaf_state,old.delta
read=lambda path:json.loads(Path(path).read_text())


def source_seed(life,query,batch,replica):
    return BASE+10000000+life*1000000+list(QUERIES).index(query)*100000+batch*10000+replica


def branch_seed(life,query,batch,replica,slot,suffix):
    return BASE+20000000+life*1000000+list(QUERIES).index(query)*100000+batch*10000+replica*1000+slot*100+suffix


def evaluation_seed(life,checkpoint,replica):
    return BASE+90000000+life*1000000+checkpoint*10000+replica


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,durations=list(DURATIONS),methods=list(METHODS),
        checkpoints=list(range(BATCHES+1)),training_transition_cap_per_cell=BUDGET,source_games_per_batch=2,
        roots_per_game=4,root_selection='floor((2*slot+1)*steps/8); all active predecision boards',
        suffixes_per_root=SUFFIXES,triplet_order='suffix outer; source game then slot inner; branches 0,1,8',
        budget='source games plus all actual triplet transitions; both learners charged the entire shared pool',
        incomplete_triplet='retain all costs; fit neither learner unless all three branches terminate',
        learner='V147 boundary-aware unary/adjacent-pair ROOT features plus bias; separate weights for durations1/8',
        target='mean paired total reward/2048, failure, success differences versus own H2; no immediate subtraction',
        update='warm normalized LMS; 32 ordered passes over all accumulated root means per batch',epochs=EPOCHS,alpha=ALPHA,
        continuation='other frozen H2 for duration steps then own frozen H2',
        gate='strict positive learned total advantage; commit full duration; otherwise own H2 one step',
        no_learning_control='zero component model is exactly H2; ALT always uses the other query teacher',
        evaluation_replicas=REPLICAS,physical_evaluation_games=640,source_games=64,workers=WORKERS,
        representation='SINGLE',p_four=.1,max_steps=MAX_STEPS,version_base=BASE,
        primary='new complete-game utility per checkpoint; equal replicas within history then equal four histories',
        diagnostic='four roots from each fresh H2 evaluation game; predictions and exact training-board overlap only',
        frozen_policy='no evaluation-dependent refit, hyperparameter choice, root replacement or early stopping')


def extract_source(capsule,run,analysis):
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V150 must be complete')
    return dict(schema='acfqp.policy_modules.v151.source',snapshots=deepcopy(capsule['snapshots']),
        source_run_ref=str(SOURCE/'run.json'),cost_refs=deepcopy(capsule['cost_refs'])+[
            dict(path=str(SOURCE/'analysis.json'),fields=['costs']),
            dict(path=str(ROOT/'reports/v150_runtime_tmp/retained_label_preflight.json'),fields=['seconds','source_reads_per_implementation','implementations']),
            dict(path=str(ROOT/'reports/v150_runtime_tmp/provisional_summary.json'),fields=['work','seconds'])])


def compact_choice(choice,work):
    keys=('action','afterstate','score','value','tail_value','status','action_values','module_decision')
    return dict(**{key:deepcopy(choice[key]) for key in keys if key in choice},work=work)


def play_game(bank,query,method,duration,model,seed,max_steps=MAX_STEPS):
    mode=method if method in ('H2','ALT') else 'LEARNED'
    gate=ModuleGate(bank,query,duration,model=model,mode=mode);choices=[];decision_seconds=0.
    def act(board,step):
        nonlocal decision_seconds
        before=dict(gate.counts);started=perf_counter();choice=gate.choose(board,step)
        decision_seconds+=perf_counter()-started;choices.append(compact_choice(choice,delta(gate.counts,before)))
        return choice['action']
    game=old.old.run_episode(seed,act,.1,max_steps)
    result=old.old.game_result(game,query,dict(gate.counts),decision_seconds)
    if result['status']=='CUTOFF':result['utility']=None
    row=dict(seed=seed,query=query,method=method,duration=duration,max_steps=max_steps,choices=choices,
        result=result,**old.old.compact_trace(game))
    return row,game


def select_roots(game,life,query,batch,replica):
    n=len(game['steps']);roots=[]
    for slot in range(4):
        step=((2*slot+1)*n)//8
        roots.append(dict(root_id=f'{life}:{query}:{batch}:{replica}:{slot}',life=life,query=query,
            batch=batch,replica=replica,slot=slot,step=step,source_steps=n,board=list(game['steps'][step]['board'])))
    return roots


def root_means(roots,triplets):
    examples=[]
    for root in roots:
        rows=[r for r in triplets if r['root_id']==root['root_id'] and r['complete']]
        if not rows:continue
        targets={str(d):[sum(r['branches'][str(d)]['result']['components'][k]-
            r['branches']['0']['result']['components'][k] for r in rows)/len(rows) for k in range(3)] for d in DURATIONS}
        examples.append(dict(**deepcopy(root),triplet_ids=[r['triplet_id'] for r in rows],samples=len(rows),targets=targets))
    return examples


def acquire_batch(bank,life,query,batch,folder,directory):
    started=perf_counter();used=0;roots=[];triplets=[];environment=Counter();statuses=Counter()
    source_path=folder/'source_games.jsonl.gz';branch_path=folder/'triplets.jsonl.gz'
    with gzip.open(source_path,'wt') as output:
        for replica in range(2):
            limit=min(MAX_STEPS,BUDGET-used)
            row,game=play_game(bank,query,'H2',0,None,source_seed(life,query,batch,replica),limit)
            row.update(life=life,batch=batch,replica=replica);selected=select_roots(game,life,query,batch,replica)
            row['roots']=selected;roots.extend(selected);append(output,row)
            used+=row['result']['steps'];environment.update(row['result']['environment_counts']);statuses[row['result']['status']]+=1
    with gzip.open(branch_path,'wt') as output:
        for suffix in range(SUFFIXES):
            for root in roots:
                if used>=BUDGET:break
                seed=branch_seed(life,query,batch,root['replica'],root['slot'],suffix)
                row=dict(triplet_id=f'{root["root_id"]}:{suffix}',root_id=root['root_id'],life=life,query=query,
                    batch=batch,suffix=suffix,seed=seed,branches={})
                for duration in (0,1,8):
                    if used>=BUDGET:break
                    limit=min(MAX_STEPS,BUDGET-used)
                    branch=run_module_branch(root['board'],bank,query,duration,seed,max_steps=limit,p_four=.1)
                    branch['max_steps']=limit;row['branches'][str(duration)]=branch
                    used+=branch['result']['steps'];environment.update(branch['result']['environment_counts'])
                    statuses[branch['result']['status']]+=1
                row['complete']=len(row['branches'])==3 and all(b['result']['status'] in ('WON','LOST') for b in row['branches'].values())
                triplets.append(row);append(output,row)
            if used>=BUDGET:break
    examples=root_means(roots,triplets);save(folder/'examples.json',examples)
    data=dict(life=life,query=query,batch=batch,roots=roots,source_trace=str(source_path.relative_to(directory)),
        triplet_trace=str(branch_path.relative_to(directory)),examples_ref=str((folder/'examples.json').relative_to(directory)),
        actual_training_transitions=used,budget_cap=BUDGET,environment_counts=dict(environment),statuses=dict(statuses),
        attempted_triplets=len(triplets),complete_triplets=sum(r['complete'] for r in triplets),
        physical_branches=sum(len(r['branches']) for r in triplets),training_roots=len(examples),
        matched_budget_views={str(d):used for d in DURATIONS},seconds=perf_counter()-started)
    print(json.dumps(dict(event='batch_acquired',life=life,query=query,batch=batch,transitions=used,
        complete_triplets=data['complete_triplets'])),flush=True)
    return data,examples


def fit_models(models,examples,folder,directory):
    result={}
    for duration in DURATIONS:
        model=models[duration];before=model.state();counts=dict(model.counts);model.frozen=False
        for _ in range(EPOCHS):
            for e in examples:model.update(e['board'],e['targets'][str(duration)],ALPHA)
        fit_counts=delta(model.counts,counts);model.freeze();state=model.state();path=folder/f'module_{duration}.json'
        save(path,model.to_payload())
        result[str(duration)]=dict(model_ref=str(path.relative_to(directory)),model_bytes=path.stat().st_size,
            before=before,frozen_state=state,fit_counts=fit_counts,total_counts=dict(model.counts),
            setup_counts=dict(model.setup_counts),training_roots=[e['root_id'] for e in examples],
            training_triplet_ids=[t for e in examples for t in e['triplet_ids']])
    return result


def evaluate_checkpoint(bank,models,accumulated,life,checkpoint,folder,directory):
    trace=folder/'control.jsonl.gz';diagnostics=folder/'fresh_roots.jsonl.gz';data={}
    with gzip.open(trace,'wt') as output,gzip.open(diagnostics,'wt') as diagnostic_output:
        for query in QUERIES:
            qmodels=models[query];before={str(d):m.state() for d,m in qmodels.items()};qdata={}
            seen={tuple(e['board']) for e in accumulated[query]};diagnostic_counts=Counter()
            for method in METHODS:
                duration=int(method[-1]) if method.startswith('LEARN') else (1 if method=='ALT' else 0)
                model=qmodels[duration] if method.startswith('LEARN') else None
                cell=dict(games=0,statuses=Counter(),environment_counts=Counter(),policy_counts=Counter())
                for replica in range(REPLICAS):
                    row,game=play_game(bank,query,method,duration,model,evaluation_seed(life,checkpoint,replica))
                    row.update(life=life,checkpoint=checkpoint,replica=replica);append(output,row)
                    cell['games']+=1;cell['statuses'][row['result']['status']]+=1
                    for key in ('environment_counts','policy_counts'):cell[key].update(row['result'][key])
                    if method=='H2':
                        for root in select_roots(game,life,query,checkpoint,replica):
                            predictions={}
                            for d,m in qmodels.items():
                                counts=dict(m.counts);components=m.predict(root['board']);diagnostic_counts.update(delta(m.counts,counts))
                                q=QUERIES[query];value=components[0]-q['failure_penalty']*components[1]+q['goal_bonus']*components[2]
                                predictions[str(d)]=dict(components=components,advantage=value,selected_module=value>0)
                            append(diagnostic_output,dict(**root,checkpoint=checkpoint,seen_in_training=tuple(root['board']) in seen,predictions=predictions))
                qdata[method]=cell
            data[query]=dict(methods=qdata,models_before=before,models_after={str(d):m.state() for d,m in qmodels.items()},
                diagnostic_counts=dict(diagnostic_counts),model_total_counts={str(d):dict(m.counts) for d,m in qmodels.items()})
            print(json.dumps(dict(event='checkpoint_evaluated',life=life,query=query,checkpoint=checkpoint)),flush=True)
    return dict(control_trace=str(trace.relative_to(directory)),diagnostics_trace=str(diagnostics.relative_to(directory)),queries=data)


def lifecycle(source,directory):
    started=perf_counter();life=source['life'];folder=directory/f'life_{life}';folder.mkdir()
    bank={};parents={};leaves={};data=dict(life=life,teacher_bank={},checkpoints=[])
    for query in QUERIES:
        qfolder=folder/query;qfolder.mkdir();parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,qfolder)
        bank[query]=teacher;parents[query]=parent;leaves[query]=leaf
        data['teacher_bank'][query]=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
    models={q:{d:RootConsequences() for d in DURATIONS} for q in QUERIES};accumulated={q:[] for q in QUERIES}
    for checkpoint in range(BATCHES+1):
        cfolder=folder/f'checkpoint_{checkpoint}';cfolder.mkdir();record=dict(checkpoint=checkpoint,training={},models={})
        for query in QUERIES:
            qfolder=cfolder/query;qfolder.mkdir()
            if checkpoint:
                acquired,examples=acquire_batch(bank,life,query,checkpoint,qfolder,directory)
                record['training'][query]=acquired;accumulated[query].extend(examples)
            record['models'][query]=fit_models(models[query],accumulated[query],qfolder,directory)
        save(cfolder/'frozen_models.json',deepcopy(record))
        record['evaluation']=evaluate_checkpoint(bank,models,accumulated,life,checkpoint,cfolder,directory)
        data['checkpoints'].append(record);save(folder/'lifecycle.json',data)
    for query in QUERIES:
        data['teacher_bank'][query].update(parent_after=leaf_state(parents[query],True),leaf_after=leaf_state(leaves[query]),
            total_counts=dict(bank[query].counts))
    data['seconds']=perf_counter()-started;save(folder/'lifecycle.json',data);return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_policy_modules_v151')
    files={Path(__file__).resolve(),ROOT/'specs/POLICY_MODULES_V151.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*policy_modules_v151.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    source=extract_source(*(read(SOURCE/name) for name in ('source_capsule.json','run.json','analysis.json')))
    save(directory/'source_capsule.json',source);snapshot_code(directory)
    data=dict(schema='acfqp.policy_modules.v151.run',status='frozen',settings=settings(),inherited_cost_refs=source['cost_refs'],lifecycles=[])
    save(directory/'frozen_inputs.json',deepcopy(data));save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        data['status']='running';save(directory/'run.json',data)
        for future in as_completed([pool.submit(lifecycle,s,directory) for s in source['snapshots']]):
            data['lifecycles'].append(future.result());data['lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_policy_modules_v151')
    run(parser.parse_args().output)
