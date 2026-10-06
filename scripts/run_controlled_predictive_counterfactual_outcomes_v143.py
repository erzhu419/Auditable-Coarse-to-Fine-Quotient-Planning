"""Collect paired first-action consequences under a common frozen H2 policy."""
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
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_h1_continuation_v142 as previous
from acfqp.science.controlled_predictive_counterfactual_outcomes_v143 import run_branch

SOURCE=ROOT/'reports/controlled_predictive_h1_continuation_v142'
LIVES,REPLICAS,WORKERS=previous.LIVES,8,4
QUERIES=previous.QUERIES
METHODS=('H2','SHALLOW','LEARNED64','H1_CONT')
ROOTS_PER_GAME,SUFFIXES,MAX_STEPS,BASE=4,8,2000,143*100000000
save,append,read_rows,leaf_state=previous.save,previous.append,previous.read_rows,previous.leaf_state
load_teacher=previous.previous.previous.old.load_teacher


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,replicas=REPLICAS,workers=WORKERS,
        methods=list(METHODS),roots_per_game=ROOTS_PER_GAME,suffixes=SUFFIXES,
        root_selection='sorted retained steps; index floor((2*j+1)*n/8), j=0..3',
        expected_roots=256,expected_source_roots=1973,representation='SINGLE',
        continuation='H2',p_four=.1,max_steps=MAX_STEPS,version_base=BASE,
        new_training_samples=0,branch_deduplication='one branch per distinct first action and suffix',
        suffix_seed='BASE+life*1000000+query_index*100000+replica*10000+slot*100+suffix',
        cutoff_rule='retain all costs; no terminal utility or replacement')


def root_key(row): return (row['life'],row['query'],row['replica'],row['step'])


def suffix_seed(life,query,replica,slot,suffix):
    return BASE+life*1000000+list(QUERIES).index(query)*100000+replica*10000+slot*100+suffix


def extract_source(capsule,run,analysis):
    if not (run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V142 must be complete before counterfactual collection')
    sources=deepcopy(capsule['snapshots']); evaluation={r['life']:r for r in run['eval_lifecycles']}
    for source in sources:
        source['h1_diagnostic_trace']=str((SOURCE/evaluation[source['life']]['diagnostics_trace']).resolve())
    return dict(schema='acfqp.counterfactual_outcomes.v143.source',snapshots=sources,
        inherited_costs={**deepcopy(capsule['inherited_costs']),'v142_experiment':deepcopy(analysis['costs'])},
        required_inputs='complete V141/V142 fixed-root decisions and frozen V134 SINGLE leaves; no new fitting')


def build_cohort(sources):
    roots=[]; reads=Counter()
    for source in sources:
        old=list(read_rows(source['diagnostic_source_trace'])); new=list(read_rows(source['h1_diagnostic_trace']))
        reads.update(v141=len(old),v142=len(new)); indexed={root_key(r):r for r in new}
        if len(indexed)!=len(new) or len(old)!=len(new) or set(indexed)!={root_key(r) for r in old}:
            raise ValueError('retained diagnostic identities differ')
        for query in QUERIES:
            for replica in range(REPLICAS):
                records=sorted((r for r in old if r['query']==query and r['replica']==replica),key=lambda r:r['step'])
                if len(records)<ROOTS_PER_GAME: raise ValueError('retained game lacks four diagnostic roots')
                for slot in range(ROOTS_PER_GAME):
                    ordinal=((2*slot+1)*len(records))//(2*ROOTS_PER_GAME)
                    row=records[ordinal]; h1=indexed[root_key(row)]
                    fields=('life','query','replica','seed','step','board','previous_action','simulation_seed')
                    if any(row[k]!=h1[k] for k in fields): raise ValueError('retained root payloads differ')
                    choices=dict(H2=row['reference']['action'],
                        SHALLOW=row['probes']['SHALLOW']['action'],LEARNED64=row['probes']['LEARNED64']['action'],
                        H1_CONT=h1['probes']['H1_CONT']['action'])
                    root=dict(**{k:deepcopy(row[k]) for k in fields},root_id=':'.join(map(str,root_key(row))),
                        slot=slot,source_ordinal=ordinal,source_game_roots=len(records),choices=choices,
                        actions=sorted(set(choices.values())),
                        suffix_seeds=[suffix_seed(source['life'],query,replica,slot,s) for s in range(SUFFIXES)])
                    roots.append(root)
    if len(roots)!=256 or reads!=Counter(v141=1973,v142=1973):
        raise ValueError('retained fixed cohort is incomplete')
    return dict(schema='acfqp.counterfactual_outcomes.v143.cohort',roots=roots,source_rows_read=dict(reads),
        physical_branches=sum(len(r['actions'])*SUFFIXES for r in roots),
        paired_records=len(roots)*SUFFIXES,logical_method_suffixes=len(roots)*len(METHODS)*SUFFIXES)


def evaluate_lifecycle(source,roots,directory):
    started=perf_counter(); life=source['life']; folder=directory/f'eval_{life}'; folder.mkdir()
    trace=str((folder/'paired_consequences.jsonl.gz').relative_to(directory))
    data=dict(life=life,consequences_trace=trace,queries={})
    with gzip.open(directory/trace,'wt') as output:
        for query in QUERIES:
            qfolder=folder/query; qfolder.mkdir()
            parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,qfolder)
            qroots=[r for r in roots if r['query']==query]
            qdata=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf),
                spawn_probabilities=list(teacher.spawn_probabilities),roots=len(qroots))
            data['queries'][query]=qdata; work=Counter(); branches=0; statuses=Counter()
            for index,root in enumerate(qroots):
                for suffix,seed in enumerate(root['suffix_seeds']):
                    outcomes={}
                    for action in root['actions']:
                        branch=run_branch(root['board'],action,teacher,QUERIES[query],seed,MAX_STEPS,.1)
                        outcomes[action]=branch; branches+=1
                        work.update(branch['result']['environment_counts']); statuses[branch['result']['status']]+=1
                    append(output,dict(root_id=root['root_id'],suffix=suffix,seed=seed,
                        continuation='H2',branches=outcomes))
                if (index+1)%4==0:
                    output.flush(); print(json.dumps(dict(event='roots_complete',life=life,query=query,
                        roots=index+1,branches=branches)),flush=True)
            qdata.update(physical_branches=branches,paired_records=len(qroots)*SUFFIXES,statuses=dict(statuses),
                environment_counts=dict(work),policy_counts=dict(teacher.counts),
                parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf))
    data['seconds']=perf_counter()-started; save(folder/'lifecycle.json',data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_counterfactual_outcomes_v143')
    files={Path(__file__).resolve(),ROOT/'specs/COUNTERFACTUAL_OUTCOMES_V143.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135',
                 'program_planning_v140','shallow_sampling_v141','h1_continuation_v142'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*counterfactual_outcomes*v143.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)


def run(directory):
    started=perf_counter(); directory=directory.resolve(); directory.mkdir(parents=True,exist_ok=False)
    read=lambda name:json.loads((SOURCE/name).read_text())
    source=extract_source(read('source_capsule.json'),read('run.json'),read('analysis.json'))
    cohort=build_cohort(source['snapshots'])
    save(directory/'source_capsule.json',source); save(directory/'cohort.json',cohort); snapshot_code(directory)
    data=dict(schema='acfqp.counterfactual_outcomes.v143.run',status='frozen',settings=settings(),
        inherited_costs=source['inherited_costs'],cohort_ref='cohort.json',eval_lifecycles=[])
    save(directory/'frozen_inputs.json',deepcopy(data)); save(directory/'run.json',data)
    data['status']='evaluation'; save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(evaluate_lifecycle,s,[r for r in cohort['roots'] if r['life']==s['life']],directory)
            for s in source['snapshots']]
        for future in as_completed(tasks):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda r:r['life']); save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started); save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_counterfactual_outcomes_v143')
    run(parser.parse_args().output)
