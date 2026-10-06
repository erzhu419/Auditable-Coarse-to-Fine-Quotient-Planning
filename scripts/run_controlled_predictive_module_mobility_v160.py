"""Fresh paired test of a bounded vacancy-restoration module."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import importlib
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_module_diagnosis_v153 as prior
from acfqp.science.controlled_predictive_module_mobility_v160 import run_branch, MODES
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics

SOURCE=ROOT/'reports/controlled_predictive_module_control_variate_v159'
LIVES,QUERIES,SOURCE_METHODS=prior.LIVES,prior.QUERIES,prior.SOURCE_METHODS
BASE,SUFFIXES,MAX_STEPS,WORKERS=160*100000000,32,2000,4
save,append,read,load_teacher,leaf_state=prior.save,prior.append,prior.read,prior.load_teacher,prior.leaf_state


def branch_seed(life,query,source_method,slot,suffix):
    return BASE+20000000+life*1000000+list(QUERIES).index(query)*100000+SOURCE_METHODS.index(source_method)*10000+slot*100+suffix


def branch_roster(roots):
    return [dict(branch_id=f'{r["root_id"]}:{suffix}:{mode}',root_id=r['root_id'],suffix=suffix,mode=mode,
        seed=branch_seed(r['life'],r['query'],r['source_method'],r['slot'],suffix))
        for r in roots for suffix in range(SUFFIXES) for mode in MODES]


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,source_methods=list(SOURCE_METHODS),modes=list(MODES),
        roots=64,suffixes=SUFFIXES,physical_branches=6144,max_steps=MAX_STEPS,
        maximum_environment_transitions=12288000,p_four=.1,workers=WORKERS,
        version_base=BASE,prefix_budget=8,empty_gain=2,new_training_updates=0,
        roots_policy='all 64 frozen V153 roots, unchanged and outcome-independent; inherited through audited V159',
        seeds='BASE+20000000+life*1000000+query_index*100000+source_index*10000+slot*100+suffix; shared across three modes',
        module='MOBILITY: legal frozen learned swipes; maximize afterstate vacancy count minus one; lexical action ties',
        exit='after actual spawn: terminal first, then observed vacancies >= root vacancies+2, then eight-prefix-step budget; no reentry',
        controls='H2 own target H2 throughout; OTHER8 other-query H2 for eight steps or terminal; all continue with own H2',
        horizon='2000 transitions per branch; no initial spawns; winning swipe still spawns',
        primary='MOBILITY minus H2 terminal utility, separately risk1 and risk8, ALL sources and ALL roots',
        secondary='MOBILITY minus OTHER8 and OTHER8 minus H2; per-source and fixed vacancy strata TIGHT <=2 / ROOMY >2',
        aggregation='mean suffixes within root; equal selected roots within history; equal all four histories',
        intervals='pointwise mean +/-1.96*SE from paired suffix sample variances; fixed roots and four histories, no population-history inference',
        incompleteness='retain cutoffs and all costs; affected statistics incomplete; no replacements or omitted histories',
        accounting='all physical transitions, decision work, rule work, frozen teacher loads and inherited costs; completion is diagnostic',
        frozen_policy='no fitting, learned caller, outcome-selected root/subgroup/budget, extra suffixes or gate changes')


def extract_source():
    run,analysis,capsule=(read(SOURCE/n) for n in ('run.json','analysis.json','source_capsule.json'))
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('audited V159 completion required')
    roots=deepcopy(capsule['roots'])
    expected={f'{l}:{q}:{m}:{s}' for l in LIVES for q in QUERIES for m in SOURCE_METHODS for s in range(4)}
    if len(roots)!=64 or {r['root_id'] for r in roots}!=expected:
        raise ValueError('all 64 frozen roots are required')
    return dict(schema='acfqp.module_mobility.v160.source',roots=roots,snapshots=deepcopy(capsule['snapshots']),
        source_run_ref=str(SOURCE/'run.json'),source_analysis_ref=str(SOURCE/'analysis.json'),
        source_capsule_ref=str(SOURCE/'source_capsule.json'),
        inherited_new_environment_samples=capsule['inherited_new_environment_samples'],
        cost_refs=deepcopy(capsule['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'),fields=['costs'])]+[
            dict(path=str(ROOT/f'reports/v159_runtime_tmp/{name}_checks.json'),fields=['attempts'])
            for name in ('core','runner','analyzer')])


def compact_outcome(row):
    keys=('branch_id','root_id','life','query','source_method','slot','suffix','mode','seed')
    data={key:row[key] for key in keys}
    data.update({key:deepcopy(row['result'][key]) for key in ('score','steps','status','components','utility')})
    data['module']=deepcopy(row['module']);return data


def lifecycle(source,roots,directory):
    started=perf_counter();life=source['life'];folder=directory/f'life_{life}';folder.mkdir()
    bank,parents,leaves={},{},{};data=dict(life=life,teacher_bank={})
    for query in QUERIES:
        qfolder=folder/query;qfolder.mkdir()
        parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,qfolder)
        bank[query],parents[query],leaves[query]=teacher,parent,leaf
        data['teacher_bank'][query]=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf))
    rule=LearnedDynamics.from_payload(source['rule']);rule_before=rule.to_payload()
    trace=folder/'branches.jsonl.gz';environment,policy,statuses=Counter(),Counter(),Counter();outcomes=[]
    with gzip.open(trace,'wt') as output:
        for root in roots:
            if root['life']!=life:continue
            for suffix in range(SUFFIXES):
                seed=branch_seed(life,root['query'],root['source_method'],root['slot'],suffix)
                for mode in MODES:
                    row=run_branch(root['board'],bank,rule,root['query'],mode,seed,MAX_STEPS,.1)
                    row.update(branch_id=f'{root["root_id"]}:{suffix}:{mode}',root_id=root['root_id'],
                        life=life,source_method=root['source_method'],slot=root['slot'],suffix=suffix)
                    append(output,row);outcomes.append(compact_outcome(row));result=row['result']
                    environment.update(result['environment_counts']);policy.update(result['policy_counts']);statuses[result['status']]+=1
            print(dict(event='root_completed',life=life,root_id=root['root_id'],branches=SUFFIXES*len(MODES)),flush=True)
    for query in QUERIES:
        data['teacher_bank'][query].update(parent_after=leaf_state(parents[query],True),leaf_after=leaf_state(leaves[query]),total_counts=dict(bank[query].counts))
    save(folder/'outcomes.json',outcomes)
    data.update(branch_trace=str(trace.relative_to(directory)),outcomes_ref=str((folder/'outcomes.json').relative_to(directory)),
        rule_before=rule_before,rule_after=rule.to_payload(),physical_branches=len(outcomes),
        environment_counts=dict(environment),policy_counts=dict(policy),statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_module_mobility_v160')
    files={Path(__file__).resolve(),ROOT/'specs/MODULE_MOBILITY_V160.md',ROOT/'reports/v160_runtime_tmp/run_stage.py'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*module_mobility*v160.py'))
    for path in sorted(files):
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source();roots=capsule['roots'];save(directory/'source_capsule.json',capsule)
    save(directory/'roots.json',roots);snapshot_code(directory)
    data=dict(schema='acfqp.module_mobility.v160.run',status='frozen',settings=settings(),
        inherited_cost_refs=capsule['cost_refs'],lifecycles=[])
    save(directory/'frozen_inputs.json',dict(**deepcopy(data),roots=roots,branch_roster=branch_roster(roots)))
    save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        data['status']='running';save(directory/'run.json',data)
        tasks=[pool.submit(lifecycle,s,roots,directory) for s in capsule['snapshots']]
        for task in as_completed(tasks):
            data['lifecycles'].append(task.result());data['lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
    from scripts.analyze_controlled_predictive_module_mobility_v160 import summarize
    outcomes=[row for life in data['lifecycles'] for row in read(directory/life['outcomes_ref'])]
    save(directory/'summary.json',summarize(roots,outcomes))
    data.update(status='complete',seconds=perf_counter()-started,new_training_updates=0)
    save(directory/'run.json',data);print(dict(status='complete',seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_module_mobility_v160')
    run(parser.parse_args().output)
