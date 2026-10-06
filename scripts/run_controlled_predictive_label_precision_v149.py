"""Fit nested eight/32-suffix targets, then independently evaluate fixed roots."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import importlib
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_independent_labels_v148 as previous
from acfqp.science.controlled_predictive_paired_advantage_v144 import PairedAdvantage
from acfqp.science.controlled_predictive_shared_local_advantage_v147 import SharedLocalAdvantage

SOURCE=ROOT/'reports/controlled_predictive_independent_labels_v148'
LIVES,QUERIES=previous.LIVES,previous.QUERIES
METHODS=('ZERO','UPDATED','TRAIN8','TRAIN32');TRAIN_METHODS=('TRAIN8','TRAIN32')
BASE,SUFFIXES,MAX_STEPS,WORKERS,EPOCHS,ALPHA=149*100000000,32,2000,4,32,.1
save,read=previous.save,previous.read
read_rows=previous.previous.read_rows
prediction,delta=previous.previous.prediction,previous.previous.delta
acquire_lifecycle=previous.acquire_lifecycle


def suffix_seed(life,query,origin,replica,slot,suffix):
    return BASE+life*1000000+list(QUERIES).index(query)*100000+('OLD','NEW').index(origin)*50000+replica*10000+slot*100+suffix


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,methods=list(METHODS),train_methods=list(TRAIN_METHODS),
        train_replicas=[0,1,2,3],origins=['OLD','NEW'],total_train_roots=256,disagreement_roots=173,same_action_roots=83,
        training_suffixes=dict(TRAIN8=list(range(8)),TRAIN32=list(range(32))),epochs=EPOCHS,alpha=ALPHA,
        training_order='OLD16 then NEW16 per pass; zero initialization for each new learner',
        learner_representation='V144 six-cell signed n-tuple differences; unchanged UPDATED representation',
        update='three-component normalized LMS; denominator=sum(x*x)',
        target='paired H1_CONT minus H2 terminal components; exact immediate reward difference removed once',
        suffixes_per_root=SUFFIXES,paired_records=5536,physical_branches=11072,workers=WORKERS,
        continuation='H2',representation='SINGLE',p_four=.1,max_steps=MAX_STEPS,version_base=BASE,
        new_training_environment_samples=0,training_update_attempts=16384,full_policy_games=0,
        gate='strict positive recomposed advantage; ties H2',
        primary='equal history means; OLD16 and NEW16 separately and combined32; same-action exact zeros retained',
        comparison='TRAIN32 versus TRAIN8 MSE reduction and fixed-gate value; each versus ZERO and H2',
        cutoff_rule='retain all branches and costs; any cutoff blocks complete-cohort scientific claims',
        diagnostic_policy='freeze all fits and predictions before fresh labels; no refit, selection or early stopping')


def extract_source(capsule,run,analysis):
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V148 independent labels must be complete')
    result=deepcopy(capsule);result['schema']='acfqp.label_precision.v149.source'
    result['reference_run_ref']=capsule['source_run_ref'];result['source_run_ref']=str(SOURCE/'run.json')
    result['training_cohort_ref']=str(SOURCE/'cohort.json')
    lifecycles={r['life']:r for r in run['lifecycles']}
    for source in result['snapshots']:
        source['reference_models']={q:{m:source['advantage_models'][q][m] for m in ('ZERO','UPDATED')} for q in QUERIES}
        del source['advantage_models']
        source['training_trace_ref']=str(SOURCE/lifecycles[source['life']]['consequences_trace'])
    result['cost_refs'] += [dict(path=str(SOURCE/'analysis.json'),fields=['costs']),
        dict(path=str(ROOT/'reports/v148_runtime_tmp/provisional_summary.json'),fields=['work','seconds'])]
    return result


def root_order(root):
    return root['life'],list(QUERIES).index(root['query']),('OLD','NEW').index(root['origin']),root['replica'],root['slot']


def build_examples(source,cohort):
    roots={r['root_id']:r for r in cohort['roots']+cohort['same_action_roots']}
    values={r['root_id']:{} for r in cohort['roots']};reads=Counter()
    budgets={m:Counter() for m in TRAIN_METHODS}
    for snapshot in source['snapshots']:
        reads['trace_files']+=1
        for row in read_rows(snapshot['training_trace_ref']):
            root=roots[row['root_id']];suffix=row['suffix'];example=root['example']
            if (root['life']!=snapshot['life'] or suffix not in range(32) or row['seed']!=root['suffix_seeds'][suffix]
                    or row['continuation']!='H2' or set(row['branches'])!=set(root['actions'])
                    or suffix in values[root['root_id']]):raise ValueError('retained paired identity differs')
            candidate,baseline=(row['branches'][example[key]] for key in ('candidate_action','baseline_action'))
            if any(branch['result']['status'] not in ('WON','LOST') for branch in (candidate,baseline)):
                raise ValueError('retained label is not terminal')
            values[root['root_id']][suffix]=[a-b for a,b in zip(candidate['result']['components'],baseline['result']['components'])]
            reads.update(paired_records=1,branch_results=2)
            for method,n in (('TRAIN8',8),('TRAIN32',32)):
                if suffix<n:
                    budgets[method].update(paired_records=1,physical_branches=2,
                        sampled_transitions=sum(b['result']['environment_counts']['sampled_transitions'] for b in (candidate,baseline)))
    if any(sorted(rows)!=list(range(32)) for rows in values.values()):raise ValueError('retained suffix roster differs')
    methods={m:[] for m in TRAIN_METHODS}
    for root in sorted(roots.values(),key=root_order):
        for method,n in (('TRAIN8',8),('TRAIN32',32)):
            same=len(root['actions'])==1
            total=[0.,0.,0.] if same else [sum(values[root['root_id']][s][k] for s in range(n))/n for k in range(3)]
            example=deepcopy(root['example']);immediate=example['immediate_difference']
            example.update(origin=root['origin'],target_total=total,target_tail=[total[0]-immediate,*total[1:]],
                suffixes=0 if same else n,training_method=method)
            methods[method].append(example)
    if any(len(rows)!=256 for rows in methods.values()):raise ValueError('TRAIN root roster differs')
    return dict(schema='acfqp.label_precision.v149.examples',methods=methods,source_rows_read=dict(reads),
        training_budget_views={m:dict(v) for m,v in budgets.items()},
        budget_note='Nested portions of the same already-acquired V148 data; not new acquisition or additive costs')


def train_lifecycle(source,examples,directory):
    started=perf_counter();life=source['life'];folder=directory/f'train_{life}';folder.mkdir()
    result=dict(life=life,queries={})
    for query in QUERIES:
        groups={m:[e for e in examples['methods'][m] if e['life']==life and e['query']==query] for m in TRAIN_METHODS}
        qdata=dict(binding=dict(life=life,query=query,continuation='H2',leaf_ref=source['leaves'][query]['SINGLE']['model_ref']),
            train_roots=[e['root_id'] for e in groups['TRAIN8']],models={})
        for method in METHODS:
            model=(SharedLocalAdvantage.from_payload(read(source['reference_models'][query][method])) if method=='ZERO' else
                PairedAdvantage.from_payload(read(source['reference_models'][query][method])) if method=='UPDATED' else PairedAdvantage())
            before=model.state();sequence=groups[method] if method in TRAIN_METHODS else []
            for _ in range(EPOCHS):
                for e in sequence:model.update(e['candidate_after'],e['baseline_after'],e['target_tail'],ALPHA)
            fit_counts=dict(model.counts);model.freeze();state=model.state()
            path=folder/f'{query}_{method}.json';save(path,model.to_payload())
            qdata['models'][method]=dict(model_ref=str(path.relative_to(directory)),model_bytes=path.stat().st_size,
                before=before,frozen_state=state,fit_counts=fit_counts,setup_counts=dict(model.setup_counts),
                training_roots=[e['root_id'] for e in sequence],total_counts=dict(model.counts))
        result['queries'][query]=qdata
        print(json.dumps(dict(event='models_frozen',life=life,query=query,roots=len(groups['TRAIN8']))),flush=True)
    result['seconds']=perf_counter()-started;save(folder/'lifecycle.json',result);return result


def build_evaluation_cohort(cohort,trained,directory):
    result=deepcopy(cohort);result['schema']='acfqp.label_precision.v149.cohort';result['prediction_work']=[]
    rows=result['roots']+result['same_action_roots'];index={r['life']:r for r in trained}
    for life in LIVES:
        for query in QUERIES:
            selected=[r for r in rows if r['life']==life and r['query']==query]
            for r in selected:r['predictions']={}
            for method in METHODS:
                path=directory/index[life]['queries'][query]['models'][method]['model_ref']
                cls=SharedLocalAdvantage if method=='ZERO' else PairedAdvantage
                model=cls.from_payload(read(path));before=model.state()
                for root in selected:root['predictions'][method]=prediction(model,root['example'])
                if model.state()!=before:raise ValueError('prediction modified frozen model')
                result['prediction_work'].append(dict(life=life,query=query,method=method,model_ref=str(path),
                    counts=dict(model.counts),setup_counts=dict(model.setup_counts),state_unchanged=True))
    for root in rows:
        root['training_suffix_seeds']=root['suffix_seeds']
        root['suffix_seeds']=[suffix_seed(root['life'],root['query'],root['origin'],root['replica'],root['slot'],s)
            for s in range(SUFFIXES)] if len(root['actions'])==2 else []
    return result


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_label_precision_v149')
    files={Path(__file__).resolve(),ROOT/'specs/LABEL_PRECISION_V149.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*label_precision_v149.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    source=extract_source(read(SOURCE/'source_capsule.json'),read(SOURCE/'run.json'),read(SOURCE/'analysis.json'))
    cohort=read(source['training_cohort_ref']);examples=build_examples(source,cohort)
    save(directory/'source_capsule.json',source);save(directory/'examples.json',examples);snapshot_code(directory)
    data=dict(schema='acfqp.label_precision.v149.run',status='frozen',settings=settings(),
        inherited_cost_refs=source['cost_refs'],training_lifecycles=[],lifecycles=[])
    save(directory/'frozen_inputs.json',deepcopy(data));save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        data['status']='training';save(directory/'run.json',data)
        for future in as_completed([pool.submit(train_lifecycle,s,examples,directory) for s in source['snapshots']]):
            data['training_lifecycles'].append(future.result());data['training_lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
        evaluation=build_evaluation_cohort(cohort,data['training_lifecycles'],directory);save(directory/'cohort.json',evaluation)
        data['status']='trained_frozen';save(directory/'frozen_training.json',deepcopy(data));save(directory/'run.json',data)
        data['status']='acquisition';save(directory/'run.json',data)
        for future in as_completed([pool.submit(acquire_lifecycle,s,[r for r in evaluation['roots'] if r['life']==s['life']],directory) for s in source['snapshots']]):
            data['lifecycles'].append(future.result());data['lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_label_precision_v149')
    run(parser.parse_args().output)
