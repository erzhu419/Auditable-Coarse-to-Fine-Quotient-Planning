"""Fit one shared local consequence representation and evaluate fresh games."""
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
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_coverage_expansion_v145 as previous
from acfqp.science.controlled_predictive_paired_advantage_v144 import PairedAdvantage, AdvantagePlanner
from acfqp.science.controlled_predictive_shared_local_advantage_v147 import SharedLocalAdvantage, FEATURE_DEFINITION
from acfqp.science.controlled_predictive_h1_continuation_v142 import H1ContinuationPlanner

SOURCE=ROOT/'reports/controlled_predictive_coverage_expansion_v145'
DIAGNOSIS=ROOT/'reports/controlled_predictive_transfer_diagnosis_v146'
LIVES,QUERIES,REPLICAS,WORKERS=previous.LIVES,previous.QUERIES,8,4
METHODS=('H2','ZERO','UPDATED','SHARED');MODEL_METHODS=METHODS[1:]
EPOCHS,ALPHA,BASE,MAX_STEPS=32,.1,147*100000000,2000
save,append,read_rows,leaf_state=previous.save,previous.append,previous.read_rows,previous.leaf_state
load_teacher,delta,compact_choice,prediction=previous.load_teacher,previous.delta,previous.compact_choice,previous.prediction
old=previous.old


def evaluation_seed(life,replica):return BASE+90000000+life*100000+replica
def simulation_seed(life,replica,step):return BASE+80000000+life*1000000+replica*10000+step


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,replicas=REPLICAS,workers=WORKERS,
        methods=list(METHODS),train_replicas=[0,1,2,3],validation_replicas=[4,5,6,7],epochs=EPOCHS,alpha=ALPHA,
        training_order='old TRAIN then new TRAIN per pass; V145 UPDATED labels and order',
        feature_definition=deepcopy(FEATURE_DEFINITION),new_training_environment_samples=0,
        update='normalized LMS on signed multiplicities; denominator=sum(x*x)',
        target='retained eight-suffix H1_CONT minus H2 continuation components; exact immediate reward removed',
        representation='SINGLE',continuation='H2',gate='strict positive recomposed advantage; ties H2',
        terminal_pair_rule='keep H2 if either chosen afterstate reaches goal; no learned terminal extrapolation',
        p_four=.1,max_steps=MAX_STEPS,physical_games=256,version_base=BASE,
        diagnostic_policy='one fixed representation; no validation selection or refitting')


def extract_source(capsule,run,analysis,diagnosis,verification):
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']
           and diagnosis['complete'] and verification['complete']):
        raise ValueError('V145 and V146 must be complete before representation replacement')
    snapshots=deepcopy(capsule['snapshots']);trained={r['life']:r for r in run['lifecycles']}
    for source in snapshots:
        source['updated_models']={q:str((SOURCE/trained[source['life']]['queries'][q]['models']['UPDATED']['model_ref']).resolve()) for q in QUERIES}
    return dict(schema='acfqp.shared_local_advantage.v147.source',snapshots=snapshots,
        old_examples_ref=capsule['prior_examples_ref'],new_examples_ref=str((SOURCE/'examples.json').resolve()),
        source_run_ref=str((SOURCE/'run.json').resolve()),diagnosis_ref=str((DIAGNOSIS/'analysis.json').resolve()),
        cost_refs=[dict(path=str((SOURCE/'analysis.json').resolve()),fields=['costs','inherited_work']),
            dict(path=str((DIAGNOSIS/'analysis.json').resolve()),fields=['costs']),
            dict(path=str((DIAGNOSIS/'verification.json').resolve()),fields=['work'])])


def train_lifecycle(source,old_examples,new_examples,directory):
    started=perf_counter();folder=directory/f'train_{source["life"]}';folder.mkdir()
    data=dict(life=source['life'],queries={})
    for query in QUERIES:
        groups=dict(OLD=[e for e in old_examples if e['query']==query],NEW=[e for e in new_examples if e['query']==query])
        train={o:[e for e in rows if e['split']=='TRAIN'] for o,rows in groups.items()}
        validation={o:[e for e in rows if e['split']=='VALIDATION'] for o,rows in groups.items()}
        sequence=train['OLD']+train['NEW']
        qdata=dict(binding=dict(life=source['life'],query=query,continuation='H2',
            leaf_ref=source['leaves'][query]['SINGLE']['model_ref']),
            train_roots={o:[e['root_id'] for e in rows] for o,rows in train.items()},
            validation_roots={o:[e['root_id'] for e in rows] for o,rows in validation.items()},
            models={},validation={o:{} for o in groups},validation_work={o:{} for o in groups})
        models={}
        for method in MODEL_METHODS:
            model=(PairedAdvantage.from_payload(json.loads(Path(source['updated_models'][query]).read_text()))
                if method=='UPDATED' else SharedLocalAdvantage())
            before=model.state();rows=sequence if method=='SHARED' else []
            for _ in range(EPOCHS):
                for e in rows:model.update(e['candidate_after'],e['baseline_after'],e['target_tail'],ALPHA)
            fit_counts=dict(model.counts);model.freeze();state=model.state()
            path=folder/f'{query}_{method}.json';save(path,model.to_payload());models[method]=model
            qdata['models'][method]=dict(model_ref=str(path.relative_to(directory)),model_bytes=path.stat().st_size,
                before=before,frozen_state=state,fit_counts=fit_counts,setup_counts=dict(model.setup_counts),
                training_roots=[e['root_id'] for e in rows])
        for origin,rows in validation.items():
            for method,model in models.items():
                before=dict(model.counts);qdata['validation'][origin][method]=[prediction(model,e) for e in rows]
                qdata['validation_work'][origin][method]=delta(model.counts,before)
        for method,model in models.items():
            qdata['models'][method].update(after_validation=model.state(),total_counts=dict(model.counts))
        data['queries'][query]=qdata
        print(json.dumps(dict(event='models_frozen',life=source['life'],query=query,training_roots=len(sequence))),flush=True)
    data['seconds']=perf_counter()-started;save(folder/'lifecycle.json',data);return data


def play(planner,life,query,method,replica):
    before=dict(planner.counts);choices=[];decision_seconds=0.;prior='DOWN'
    def act(board,step):
        nonlocal decision_seconds,prior
        counts=dict(planner.counts);started=perf_counter()
        choice=planner.choose(board,QUERIES[query]) if method=='H2' else planner.choose(board,QUERIES[query],
            simulation_seed=simulation_seed(life,replica,step),previous_action=prior)
        decision_seconds+=perf_counter()-started
        row=dict(**compact_choice(choice),work=delta(planner.counts,counts),previous_action=prior,
            simulation_seed=None if method=='H2' else simulation_seed(life,replica,step))
        if 'selection' in choice:
            row['selection']=deepcopy(choice['selection'])
            for k in ('baseline_choice','candidate_choice'):row['selection'][k]=compact_choice(choice['selection'][k])
        choices.append(row);prior=choice['action'];return prior
    game=old.run_episode(evaluation_seed(life,replica),act,.1,MAX_STEPS)
    result=old.game_result(game,query,delta(planner.counts,before),decision_seconds)
    if result['status']=='CUTOFF':result['utility']=None
    return dict(life=life,query=query,method=method,replica=replica,seed=game['seed'],choices=choices,
        result=result,**old.compact_trace(game))


def evaluate_lifecycle(source,trained,directory):
    started=perf_counter();life=source['life'];folder=directory/f'eval_{life}';folder.mkdir()
    trace=str((folder/'control.jsonl.gz').relative_to(directory));data=dict(life=life,control_trace=trace,queries={})
    factors=json.loads(Path(source['factored_ref']).read_text())
    with gzip.open(directory/trace,'wt') as output:
        for query in QUERIES:
            qfolder=folder/query;qfolder.mkdir()
            parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,qfolder)
            candidate=H1ContinuationPlanner(leaf,factors,build_dir=qfolder/'build')
            qdata=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf),
                candidate_setup_counts=dict(candidate.setup_counts),candidate_setup_seconds=candidate.setup_seconds,planners={})
            data['queries'][query]=qdata
            for method in METHODS:
                model=None
                if method=='H2':planner=teacher
                else:
                    path=directory/trained['queries'][query]['models'][method]['model_ref']
                    cls=PairedAdvantage if method=='UPDATED' else SharedLocalAdvantage
                    model=cls.from_payload(json.loads(path.read_text()));model.freeze()
                    planner=AdvantagePlanner(teacher,candidate,model,QUERIES[query])
                before=dict(planner.counts);state=None if model is None else model.state()
                for replica in range(REPLICAS):append(output,play(planner,life,query,method,replica))
                output.flush()
                qdata['planners'][method]=dict(counts=delta(planner.counts,before),model_before=state,
                    model_after=None if model is None else model.state(),setup_counts={} if model is None else dict(model.setup_counts))
                print(json.dumps(dict(event='control_complete',life=life,query=query,method=method)),flush=True)
            qdata.update(parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf),
                teacher_total_counts=dict(teacher.counts),candidate_total_counts=dict(candidate.counts))
    data['seconds']=perf_counter()-started;save(folder/'lifecycle.json',data);return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_shared_local_advantage_v147')
    files={Path(__file__).resolve(),ROOT/'specs/SHARED_LOCAL_ADVANTAGE_V147.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            p=Path(filename).resolve()
            if p.is_relative_to(ROOT/'src') or p.is_relative_to(ROOT/'scripts'):files.add(p)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135',
                 'program_planning_v140','shallow_sampling_v141','h1_continuation_v142'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*shared_local_advantage_v147.py'))
    for p in files:
        target=directory/'source'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    read=lambda path:json.loads(path.read_text())
    source=extract_source(read(SOURCE/'source_capsule.json'),read(SOURCE/'run.json'),read(SOURCE/'analysis.json'),
        read(DIAGNOSIS/'analysis.json'),read(DIAGNOSIS/'verification.json'))
    old_examples=read(Path(source['old_examples_ref']))['examples'];new_examples=read(Path(source['new_examples_ref']))['examples']
    save(directory/'source_capsule.json',source);snapshot_code(directory)
    data=dict(schema='acfqp.shared_local_advantage.v147.run',status='frozen',settings=settings(),
        inherited_cost_refs=source['cost_refs'],lifecycles=[],eval_lifecycles=[])
    save(directory/'frozen_inputs.json',deepcopy(data));save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(train_lifecycle,s,[e for e in old_examples if e['life']==s['life']],
            [e for e in new_examples if e['life']==s['life']],directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['lifecycles'].append(future.result());data['lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
        data['status']='trained_frozen';save(directory/'frozen_training.json',deepcopy(data));save(directory/'run.json',data)
        trained={r['life']:r for r in data['lifecycles']};data['status']='evaluation';save(directory/'run.json',data)
        for future in as_completed([pool.submit(evaluate_lifecycle,s,trained[s['life']],directory) for s in source['snapshots']]):
            data['eval_lifecycles'].append(future.result());data['eval_lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(json.dumps(dict(status='complete',seconds=data['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_shared_local_advantage_v147')
    run(parser.parse_args().output)
