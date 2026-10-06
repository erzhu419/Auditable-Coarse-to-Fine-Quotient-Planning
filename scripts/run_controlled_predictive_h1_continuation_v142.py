"""Replace tree priorities by query-specific H1 choices in matched rollouts."""
import argparse
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
from scripts import run_controlled_predictive_shallow_sampling_v141 as previous
from acfqp.science.controlled_predictive_h1_continuation_v142 import H1ContinuationPlanner

SOURCE=ROOT/'reports/controlled_predictive_shallow_sampling_v141'
LIVES,REPLICAS,WORKERS=previous.LIVES,8,4
QUERIES=previous.QUERIES
METHODS=('H2','SHALLOW','LEARNED64','H1_CONT')
save,append,delta,leaf_state,read_rows=previous.save,previous.append,previous.delta,previous.leaf_state,previous.read_rows


def settings():
    return dict(lifecycles=list(LIVES),replicas=REPLICAS,workers=WORKERS,queries=QUERIES,
        methods=list(METHODS),representation='SINGLE',p_four=.1,max_steps=2000,
        new_physical_games=64,inherited_physical_games=192,logical_games=256,
        seed_version_base=previous.previous.BASE,model_budget=previous.settings()['model_budget'],
        first_spawn_count='max(1,(8*empty)//16)',continuation_rule='query-specific complete H1 action maximization',
        stopping_rule='same V140 allowance; remaining>=8 to start; at most3 continuation actions',
        planner_spawn_law='frozen_identified_distribution',diagnostic_source='all1973 retained V141 diagnostic roots',
        new_training_samples=0)


def extract_source(capsule,run,analysis):
    if not (run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V141 must be complete')
    evaluation={row['life']:row for row in run['eval_lifecycles']}; sources=deepcopy(capsule['snapshots'])
    for source in sources:
        data=evaluation[source['life']]
        source['shallow_control_trace']=str((SOURCE/data['control_trace']).resolve())
        source['diagnostic_source_trace']=str((SOURCE/data['diagnostics_trace']).resolve())
    return dict(schema='acfqp.h1_continuation.v142.source',snapshots=sources,
        inherited_costs={**deepcopy(capsule['inherited_costs']),'v141_experiment':deepcopy(analysis['costs'])},
        required_inputs='retained H2/SHALLOW/LEARNED64 games and V141 diagnostic roots, final V139 local programs, frozen query-specific SINGLE leaves')


def diagnostic_probe(planner,record):
    # Reuse the original root and original simulated stream, independently of new control trajectories.
    before=dict(planner.counts); started=perf_counter()
    choice=planner.choose(record['board'],QUERIES[record['query']],
        simulation_seed=record['simulation_seed'],previous_action=record['previous_action'])
    result={key:deepcopy(choice[key]) for key in ('action','value','status','value_kind','action_values')}
    result.update(work=delta(planner.counts,before),seconds=perf_counter()-started)
    keys=('life','query','replica','seed','step','board','previous_action','simulation_seed')
    return dict(**{key:deepcopy(record[key]) for key in keys},probes={'H1_CONT':result})


def evaluate_lifecycle(source,directory):
    started=perf_counter(); life=source['life']; folder=directory/f'eval_{life}'; folder.mkdir()
    factors=json.loads(Path(source['factored_ref']).read_text()); original_factors=deepcopy(factors)
    records=list(read_rows(source['diagnostic_source_trace']))
    trace=str((folder/'control.jsonl.gz').relative_to(directory)); diag=str((folder/'diagnostics.jsonl.gz').relative_to(directory))
    data=dict(life=life,control_trace=trace,diagnostics_trace=diag,
        diagnostic_source_trace=source['diagnostic_source_trace'],source_diagnostic_rows_read=len(records),
        baseline_refs=dict(H2=source['baseline_control_trace'],LEARNED64=source['baseline_control_trace'],
            SHALLOW=source['shallow_control_trace']),queries={})
    with gzip.open(directory/trace,'wt') as output,gzip.open(directory/diag,'wt') as diagnostics:
        for query in QUERIES:
            qfolder=folder/query; qfolder.mkdir()
            parent,leaf,unused_teacher,loads=previous.previous.old.load_teacher(source,'SINGLE',query,qfolder)
            planner=H1ContinuationPlanner(leaf,factors,build_dir=qfolder/'build')
            qdata=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf),
                setup_counts=dict(planner.setup_counts),setup_seconds=planner.setup_seconds,
                spawn_probabilities=list(planner.spawn_probabilities))
            data['queries'][query]=qdata; before=dict(planner.counts)
            for replica in range(REPLICAS):
                append(output,previous.previous.play(planner,life,query,'H1_CONT',replica))
            qdata['control_work']=delta(planner.counts,before); output.flush()
            print(json.dumps(dict(event='h1_control_complete',life=life,query=query)),flush=True)
            before=dict(planner.counts); n=0
            for record in records:
                if record['query']!=query: continue
                append(diagnostics,diagnostic_probe(planner,record)); n+=1
            qdata.update(diagnostic_windows=n,diagnostic_work=delta(planner.counts,before),counts=dict(planner.counts),
                parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf),unused_teacher_counts=dict(unused_teacher.counts))
            diagnostics.flush(); print(json.dumps(dict(event='diagnostics_complete',life=life,query=query,windows=n)),flush=True)
    data.update(factored_payload_unchanged=factors==original_factors,seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data); return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_h1_continuation_v142')
    files={Path(__file__).resolve(),ROOT/'specs/H1_CONTINUATION_V142.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'): files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135',
                 'program_planning_v140','shallow_sampling_v141','h1_continuation_v142'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*h1_continuation*v142.py'))
    for path in files:
        target=directory/'source'/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,target)


def run(directory):
    started=perf_counter(); directory=directory.resolve(); directory.mkdir(parents=True,exist_ok=False)
    read=lambda name:json.loads((SOURCE/name).read_text())
    source=extract_source(read('source_capsule.json'),read('run.json'),read('analysis.json'))
    save(directory/'source_capsule.json',source); snapshot_code(directory)
    data=dict(schema='acfqp.h1_continuation.v142.run',status='frozen',settings=settings(),
        inherited_costs=source['inherited_costs'],eval_lifecycles=[])
    save(directory/'frozen_inputs.json',deepcopy(data)); save(directory/'run.json',data)
    data['status']='evaluation'; save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        for future in as_completed([pool.submit(evaluate_lifecycle,s,directory) for s in source['snapshots']]):
            data['eval_lifecycles'].append(future.result()); data['eval_lifecycles'].sort(key=lambda row:row['life']); save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started); save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_h1_continuation_v142')
    run(parser.parse_args().output)
