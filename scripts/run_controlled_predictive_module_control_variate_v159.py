"""Fixed spawn control variates on retained V158 paths; no new environment draws."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
from pathlib import Path
import sys
import shutil
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.run_controlled_predictive_paired_ntuple_v130 import load_parent
from scripts.run_controlled_predictive_contextual_ntuple_v134 import model_state as leaf_state
from scripts import run_controlled_predictive_module_precision_v158 as prior
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_module_control_variate_v159 import (
    branch_correction,build_adjusted_pairs,freeze_cv_selectors,evaluate_control,variance_report)

SOURCE=ROOT/'reports/controlled_predictive_module_precision_v158'
LIVES,QUERIES,WORKERS=prior.LIVES,prior.QUERIES,4
read,save,append=prior.read,prior.save,prior.append


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,roots=64,splits=['TRAIN','EVAL'],
        suffixes_per_split=32,modes=['H_GATE','M_GATE'],retained_branches=8192,
        window=8,beta=1.,p_four=.1,budgets=[8,16,32],primary_budget=32,workers=WORKERS,
        critic='frozen target-query SINGLE QueryTD DIRECT choose(state).value; analytic terminals; no H2 expansion',
        correction='sum first min(8,steps) of f(actual postspawn)-exact uniform-cell/.9/.1 expectation after chosen action',
        paired_label='CV=RAW-(C_M-C_H); scalar correction only; terminal objective unchanged',
        selection='strict positive TRAIN-prefix paired label mean; zero rejects; all budgets retained',
        evaluation='both selectors scored only on original V158 EVAL32 terminal utilities',
        primary='n32 CV-minus-RAW paired action utility and CV versus OLD/reject/accept; both queries',
        secondary='n8/n16 controls; TRAIN/EVAL within-root label variance, source/history strata and fixed coefficient covariance',
        uncertainty='exploratory inspected V158 paths; conditional suffix intervals fixed roots/training; no fresh confirmation',
        accounting='retain V158 acquisition4026405 and earlier refs; zero new samples/updates; all critic/enumeration/load work separate',
        freeze='configuration/code/source roots before correction; CV selectors use TRAIN only and freeze before EVAL corrections',
        incomplete='retain cutoffs and all costs; affected comparisons incomplete without replacements',
        forbidden_adaptation='no coefficient/window/critic/budget choice after outcomes; no automatic extra samples')


def extract_source():
    run,analysis,capsule,frozen=(read(SOURCE/name) for name in ('run.json','analysis.json','source_capsule.json','frozen_inputs.json'))
    if not (run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('audited V158 completion required')
    if capsule['roots']!=frozen['roots'] or len(capsule['roots'])!=64:
        raise ValueError('retained root roster differs')
    return dict(schema='acfqp.module_control_variate.v159.source',source_run_ref=str(SOURCE/'run.json'),
        source_analysis_ref=str(SOURCE/'analysis.json'),source_capsule_ref=str(SOURCE/'source_capsule.json'),
        source_frozen_ref=str(SOURCE/'frozen_inputs.json'),roots=deepcopy(capsule['roots']),snapshots=deepcopy(capsule['snapshots']),
        source_traces=[dict(life=l['life'],split=split,path=str(SOURCE/l['branch_trace']),outcomes_ref=str(SOURCE/l['outcomes_ref']))
            for split in ('TRAIN','EVAL') for l in run['phases'][split]['lifecycles']],
        raw_train_pairs_ref=str(SOURCE/'train_pairs.json'),raw_eval_pairs_ref=str(SOURCE/'eval_pairs.json'),
        raw_selectors_ref=str(SOURCE/'frozen_selectors.json'),raw_summary_ref=str(SOURCE/'summary.json'),
        inherited_new_environment_samples=analysis['costs']['new_environment_samples'],
        cost_refs=deepcopy(capsule['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'),fields=['costs'])]+[
            dict(path=str(ROOT/f'reports/v158_runtime_tmp/{n}_checks.json'),fields=['attempts']) for n in ('core','runner','analyzer')])


def load_critic(source,query,folder):
    parent,parent_load=load_parent(source,query,folder)
    reference=source['leaves'][query]['SINGLE']
    leaf=QueryTD.load(reference['model_ref'],parent,folder/'build');leaf.freeze()
    record=dict(query=query,reference=deepcopy(reference),parent_load=parent_load,
        leaf_load=dict(setup_counts=dict(leaf.setup_counts),setup_seconds=leaf.setup_seconds,
            load_counts=dict(leaf.load_counts),load_seconds=leaf.last_load_seconds),
        parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
    return parent,leaf,record


def lifecycle(source,trace,split,directory):
    started=perf_counter();life=source['life'];folder=directory/split.lower()/f'life_{life}';folder.mkdir(parents=True)
    parents,leaves,records,before={},{},{},{}
    for query in QUERIES:
        qfolder=folder/query;qfolder.mkdir()
        parent,leaf,record=load_critic(source,query,qfolder)
        parents[query],leaves[query],records[query],before[query]=parent,leaf,record,dict(leaf.counts)
    target=folder/'corrections.jsonl.gz';counts=Counter();rows=0;seconds_critic=0.;compact=[]
    with gzip.open(trace['path'],'rt') as stream,gzip.open(target,'wt') as output:
        import json
        for line in stream:
            row=json.loads(line)
            if row['life']!=life or row['split']!=split:raise ValueError('source phase identity differs')
            query=row['query']
            def value(board):
                nonlocal seconds_critic
                tick=perf_counter();result=leaves[query].choose(board,QUERIES[query])['value'];seconds_critic+=perf_counter()-tick
                return result
            correction=branch_correction(row,value);append(output,correction)
            compact.append({k:deepcopy(correction[k]) for k in ('branch_id','root_id','life','query','source_method','slot','split','suffix','mode','correction')})
            counts.update(correction['counts']);rows+=1
    for query in QUERIES:
        records[query].update(parent_after=leaf_state(parents[query],True),leaf_after=leaf_state(leaves[query]),
            counts={k:v-before[query].get(k,0) for k,v in leaves[query].counts.items() if v-before[query].get(k,0)})
    save(folder/'corrections.json',compact)
    data=dict(life=life,split=split,correction_trace=str(target.relative_to(directory)),
        corrections_ref=str((folder/'corrections.json').relative_to(directory)),critics=records,
        source_rows_read=rows,counts=dict(counts),critic_seconds=seconds_critic,new_environment_samples=0,
        new_training_updates=0,seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);print(dict(event='corrected_lifecycle',split=split,life=life,rows=rows),flush=True)
    return data


def correct_phase(split,capsule,directory):
    started=perf_counter();lifecycles=[]
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(lifecycle,s,next(t for t in capsule['source_traces'] if t['life']==s['life'] and t['split']==split),split,directory)
            for s in capsule['snapshots']]
        for task in as_completed(tasks):lifecycles.append(task.result())
    lifecycles.sort(key=lambda r:r['life'])
    return dict(split=split,lifecycles=lifecycles,seconds=perf_counter()-started)


def collect_corrections(phase,directory):
    return [row for life in phase['lifecycles'] for row in read(directory/life['corrections_ref'])]


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_module_control_variate_v159')
    files={Path(__file__).resolve(),ROOT/'specs/MODULE_CONTROL_VARIATE_V159.md',ROOT/'reports/v159_runtime_tmp/run_stage.py'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*module_control_variate*v159.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source();save(directory/'source_capsule.json',capsule);snapshot_code(directory)
    data=dict(schema='acfqp.module_control_variate.v159.run',status='frozen',settings=settings(),
        root_ids=[r['root_id'] for r in capsule['roots']],inherited_cost_refs=capsule['cost_refs'],phases={})
    save(directory/'frozen_inputs.json',deepcopy(data));save(directory/'run.json',data)
    raw_train,raw_eval,raw_selectors=(read(capsule[key]) for key in ('raw_train_pairs_ref','raw_eval_pairs_ref','raw_selectors_ref'))
    data['phases']['TRAIN']=correct_phase('TRAIN',capsule,directory)
    train=build_adjusted_pairs(raw_train,collect_corrections(data['phases']['TRAIN'],directory))
    save(directory/'adjusted_train_pairs.json',train)
    selected=freeze_cv_selectors(capsule['roots'],train);save(directory/'frozen_cv_selectors.json',selected)
    data.update(status='selectors_frozen',selectors=len(selected));save(directory/'run.json',data)
    data['phases']['EVAL']=correct_phase('EVAL',capsule,directory)
    evaluation=build_adjusted_pairs(raw_eval,collect_corrections(data['phases']['EVAL'],directory))
    save(directory/'adjusted_eval_pairs.json',evaluation)
    results=evaluate_control(raw_selectors,selected,raw_eval);save(directory/'evaluation.json',results)
    variance=variance_report(train+evaluation);save(directory/'variance.json',variance)
    data.update(status='complete',new_environment_samples=0,new_training_updates=0,seconds=perf_counter()-started)
    save(directory/'run.json',data);print(dict(status='complete',seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_module_control_variate_v159')
    run(parser.parse_args().output)
