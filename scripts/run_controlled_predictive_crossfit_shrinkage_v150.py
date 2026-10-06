"""Cross-fit a fixed tail shrinkage rule before independent paired evaluation."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import importlib
from pathlib import Path
import shutil
import sys
from time import perf_counter
import json

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_label_precision_v149 as previous
from acfqp.science.controlled_predictive_paired_advantage_v144 import PairedAdvantage
from acfqp.science.controlled_predictive_shared_local_advantage_v147 import SharedLocalAdvantage

SOURCE=ROOT/'reports/controlled_predictive_label_precision_v149'
LIVES,QUERIES=previous.LIVES,previous.QUERIES
METHODS=('ZERO','TRAIN32','CF')
BASE,SUFFIXES,MAX_STEPS,WORKERS,EPOCHS,ALPHA=150*100000000,32,2000,4,32,.1
save,read,read_rows=previous.save,previous.read,previous.read_rows
prediction,delta,root_order=previous.prediction,previous.delta,previous.root_order
acquire_lifecycle=previous.acquire_lifecycle


def suffix_seed(life,query,origin,replica,slot,suffix):
    return BASE+life*1000000+list(QUERIES).index(query)*100000+('OLD','NEW').index(origin)*50000+replica*10000+slot*100+suffix


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,methods=list(METHODS),folds=[list(range(8*f,8*f+8)) for f in range(4)],
        train_replicas=[0,1,2,3],origins=['OLD','NEW'],total_train_roots=256,disagreement_roots=173,same_action_roots=83,
        epochs=EPOCHS,alpha=ALPHA,training_order='OLD16 then NEW16 per pass; zero initialization per 24-suffix fold',
        learner_representation='V144 six-cell signed n-tuple differences; unchanged TRAIN32 representation',
        update='three-component normalized LMS; denominator=sum(x*x)',
        calibration='per life/query beta=clip(sum(predicted_tail_utility*heldout_tail_utility)/sum(predicted_tail_utility**2),0,1); zero denominator gives zero',
        final_model='scale retained V149 TRAIN32 three-component weights by beta; leave immediate reward unscaled',
        training_update_attempts=32768,out_of_fold_prediction_records=1024,scalar_calibrations=8,new_training_environment_samples=0,
        suffixes_per_root=SUFFIXES,paired_records=5536,physical_branches=11072,workers=WORKERS,
        continuation='H2',representation='SINGLE',p_four=.1,max_steps=MAX_STEPS,version_base=BASE,full_policy_games=0,
        gate='strict positive recomposed advantage; ties H2',
        acquisition_rule='skip fresh sampling iff CF and TRAIN32 choose identically on all256 roots; otherwise fixed32 suffixes per disagreement',
        primary='equal history means; OLD16 and NEW16 separately and combined32; same-action exact zeros retained',
        comparison='CF versus TRAIN32 and ZERO: MSE reduction and fixed-gate value; H2 gate baseline',
        cutoff_rule='retain all branches and costs; any cutoff blocks complete-cohort scientific claims',
        diagnostic_policy='one fixed rule using V148 training suffixes only; freeze folds, beta and predictions before fresh labels')


def extract_source(capsule,run,analysis):
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):raise ValueError('V149 must be complete')
    source=deepcopy(capsule);source['schema']='acfqp.crossfit_shrinkage.v150.source'
    source['control_run_ref']=str(SOURCE/'run.json')
    trained={r['life']:r for r in run['training_lifecycles']}
    for snapshot in source['snapshots']:
        snapshot['control_models']={q:{m:str(SOURCE/trained[snapshot['life']]['queries'][q]['models'][m]['model_ref'])
            for m in ('ZERO','TRAIN32')} for q in QUERIES}
    source['cost_refs'] += [dict(path=str(SOURCE/'analysis.json'),fields=['costs']),
        dict(path=str(ROOT/'reports/v149_runtime_tmp/retained_label_preflight.json'),fields=['seconds','source_reads_per_implementation','implementations']),
        dict(path=str(ROOT/'reports/v149_runtime_tmp/provisional_summary.json'),fields=['work'])]
    return source


def build_examples(source,cohort):
    roots={r['root_id']:r for r in cohort['roots']+cohort['same_action_roots']}
    values={r['root_id']:{} for r in cohort['roots']};reads=Counter()
    for snapshot in source['snapshots']:
        reads['trace_files']+=1
        for row in read_rows(snapshot['training_trace_ref']):
            root=roots[row['root_id']];suffix=row['suffix'];e=root['example']
            if (root['life']!=snapshot['life'] or suffix not in range(32) or row['seed']!=root['suffix_seeds'][suffix]
                or row['continuation']!='H2' or set(row['branches'])!=set(root['actions']) or suffix in values[root['root_id']]):
                raise ValueError('retained suffix identity differs')
            a,b=(row['branches'][e[k]]['result'] for k in ('candidate_action','baseline_action'))
            if any(x['status'] not in ('WON','LOST') for x in (a,b)):raise ValueError('retained target not terminal')
            values[root['root_id']][suffix]=[a['components'][k]-b['components'][k] for k in range(3)]
            reads.update(paired_records=1,branch_results=2)
    if any(sorted(v)!=list(range(32)) for v in values.values()):raise ValueError('retained suffix roster differs')
    folds=[]
    for fold in range(4):
        heldout=list(range(8*fold,8*fold+8));train=[s for s in range(32) if s not in heldout]
        cell=dict(fold=fold,train=[],heldout=[])
        for root in sorted(roots.values(),key=root_order):
            for name,indices in (('train',train),('heldout',heldout)):
                total=[sum(values[root['root_id']][s][k] for s in indices)/len(indices) for k in range(3)] if len(root['actions'])==2 else [0.,0.,0.]
                e=deepcopy(root['example']);e.update(origin=root['origin'],fold=fold,fold_role=name,
                    suffix_indices=indices if len(root['actions'])==2 else [],suffixes=len(indices) if len(root['actions'])==2 else 0,
                    target_total=total,target_tail=[total[0]-e['immediate_difference'],*total[1:]])
                cell[name].append(e)
        folds.append(cell)
    if any(len(f[name])!=256 for f in folds for name in ('train','heldout')):raise ValueError('TRAIN root roster differs')
    return dict(schema='acfqp.crossfit_shrinkage.v150.examples',folds=folds,source_rows_read=dict(reads))


def tail_utility(tail,query):
    q=QUERIES[query];return q['reward_weight']*tail[0]-q['failure_penalty']*tail[1]+q['goal_bonus']*tail[2]


def calibration(rows):
    numerator=sum(x*y for x,y in rows);denominator=sum(x*x for x,y in rows)
    return dict(numerator=numerator,denominator=denominator,beta=min(1.,max(0.,numerator/denominator)) if denominator else 0.,rows=len(rows))


def shrink_model(model,beta):
    """Create new PairedAdvantage weights; the retained model stays untouched."""
    shrunk=PairedAdvantage(model.radix);shrunk.updates=model.updates
    scaled={key:tuple(beta*x for x in vector) for key,vector in model.weights.items()}
    shrunk._weights={key:vector for key,vector in scaled.items() if any(vector)}
    shrunk.freeze()
    return shrunk,dict(source_weight_addresses=len(model.weights),scaled_component_parameters=3*len(model.weights),
        output_weight_addresses=len(shrunk.weights))


def store_model(model,path,directory,before,fit_counts,training_roots):
    model.freeze();state=model.state();save(path,model.to_payload())
    return dict(model_ref=str(path.relative_to(directory)),model_bytes=path.stat().st_size,before=before,
        frozen_state=state,fit_counts=fit_counts,setup_counts=dict(model.setup_counts),training_roots=training_roots,total_counts=dict(model.counts))


def train_lifecycle(source,examples,directory):
    started=perf_counter();life=source['life'];folder=directory/f'train_{life}';folder.mkdir();result=dict(life=life,queries={})
    for query in QUERIES:
        qdata=dict(binding=dict(life=life,query=query,continuation='H2',leaf_ref=source['leaves'][query]['SINGLE']['model_ref']),folds=[],models={});pairs=[]
        for fold in examples['folds']:
            train=[e for e in fold['train'] if e['life']==life and e['query']==query]
            heldout=[e for e in fold['heldout'] if e['life']==life and e['query']==query]
            model=PairedAdvantage();before=model.state()
            for _ in range(EPOCHS):
                for e in train:model.update(e['candidate_after'],e['baseline_after'],e['target_tail'],ALPHA)
            counts=dict(model.counts);data=store_model(model,folder/f'{query}_fold{fold["fold"]}.json',directory,before,counts,[e['root_id'] for e in train])
            before_counts=dict(model.counts);preds=[prediction(model,e) for e in heldout]
            for e,p in zip(heldout,preds):pairs.append((tail_utility(p['predicted_tail'],query),tail_utility(e['target_tail'],query)))
            data.update(fold=fold['fold'],predictions=preds,prediction_counts=delta(model.counts,before_counts),after_prediction=model.state(),
                after_prediction_counts=dict(model.counts))
            qdata['folds'].append(data);qdata['train_roots']=[e['root_id'] for e in train]
        qdata['calibration']=calibration(pairs)
        for method in ('ZERO','TRAIN32'):
            cls=SharedLocalAdvantage if method=='ZERO' else PairedAdvantage
            model=cls.from_payload(read(source['control_models'][query][method]));before=model.state()
            qdata['models'][method]=store_model(model,folder/f'{query}_{method}.json',directory,before,dict(model.counts),[])
            if method=='TRAIN32':base=model
        model,work=shrink_model(base,qdata['calibration']['beta'])
        qdata['models']['CF']=store_model(model,folder/f'{query}_CF.json',directory,base.state(),{},[])
        qdata['models']['CF']['parameter_work']=work
        result['queries'][query]=qdata
        print(json.dumps(dict(event='calibration_frozen',life=life,query=query,beta=qdata['calibration']['beta'])),flush=True)
    result['seconds']=perf_counter()-started;save(folder/'lifecycle.json',result);return result


def build_evaluation_cohort(cohort,trained,directory):
    result=deepcopy(cohort);result['schema']='acfqp.crossfit_shrinkage.v150.cohort';result['prediction_work']=[]
    rows=result['roots']+result['same_action_roots'];indexed={r['life']:r for r in trained};changes=[]
    for life in LIVES:
        for query in QUERIES:
            selected=[r for r in rows if r['life']==life and r['query']==query]
            for root in selected:root['predictions']={}
            for method in METHODS:
                path=directory/indexed[life]['queries'][query]['models'][method]['model_ref']
                cls=SharedLocalAdvantage if method=='ZERO' else PairedAdvantage
                model=cls.from_payload(read(path));state=model.state()
                for root in selected:root['predictions'][method]=prediction(model,root['example'])
                if model.state()!=state:raise ValueError('prediction changed frozen model')
                result['prediction_work'].append(dict(life=life,query=query,method=method,model_ref=str(path),counts=dict(model.counts),setup_counts=dict(model.setup_counts),state_unchanged=True))
            changes.append(dict(life=life,query=query,**{f'vs_{m.lower()}':sum(r['predictions']['CF']['selected_h1']!=r['predictions'][m]['selected_h1'] for r in selected) for m in ('TRAIN32','ZERO')}))
    for root in rows:
        root['training_suffix_seeds']=root['suffix_seeds']
        root['suffix_seeds']=[suffix_seed(root['life'],root['query'],root['origin'],root['replica'],root['slot'],s) for s in range(32)] if len(root['actions'])==2 else []
    result['gate_changes']=dict(total_vs_train32=sum(r['vs_train32'] for r in changes),total_vs_zero=sum(r['vs_zero'] for r in changes),by_life_query=changes)
    return result


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_crossfit_shrinkage_v150')
    files={Path(__file__).resolve(),ROOT/'specs/CROSSFIT_SHRINKAGE_V150.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*crossfit_shrinkage_v150.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    source=extract_source(read(SOURCE/'source_capsule.json'),read(SOURCE/'run.json'),read(SOURCE/'analysis.json'))
    cohort=read(source['training_cohort_ref']);examples=build_examples(source,cohort)
    save(directory/'source_capsule.json',source);save(directory/'examples.json',examples);snapshot_code(directory)
    data=dict(schema='acfqp.crossfit_shrinkage.v150.run',status='frozen',settings=settings(),inherited_cost_refs=source['cost_refs'],training_lifecycles=[],lifecycles=[])
    save(directory/'frozen_inputs.json',deepcopy(data));save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        data['status']='training';save(directory/'run.json',data)
        for future in as_completed([pool.submit(train_lifecycle,s,examples,directory) for s in source['snapshots']]):
            data['training_lifecycles'].append(future.result());data['training_lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
        evaluation=build_evaluation_cohort(cohort,data['training_lifecycles'],directory);save(directory/'cohort.json',evaluation)
        data.update(status='trained_frozen',gate_changes=evaluation['gate_changes']);save(directory/'frozen_training.json',deepcopy(data));save(directory/'run.json',data)
        if not evaluation['gate_changes']['total_vs_train32']:
            data.update(status='no_action_change',seconds=perf_counter()-started);save(directory/'run.json',data);return
        data['status']='acquisition';save(directory/'run.json',data)
        for future in as_completed([pool.submit(acquire_lifecycle,s,[r for r in evaluation['roots'] if r['life']==s['life']],directory) for s in source['snapshots']]):
            data['lifecycles'].append(future.result());data['lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_crossfit_shrinkage_v150')
    run(parser.parse_args().output)
