"""Acquire visited disagreement outcomes, freeze fixed learners, test fresh games."""
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
from scripts import run_controlled_predictive_paired_advantage_v144 as previous
from acfqp.science.controlled_predictive_coverage_expansion_v145 import build_cohort, build_examples
from acfqp.science.controlled_predictive_counterfactual_outcomes_v143 import run_branch
from acfqp.science.controlled_predictive_paired_advantage_v144 import PairedAdvantage, AdvantagePlanner
from acfqp.science.controlled_predictive_h1_continuation_v142 import H1ContinuationPlanner

SOURCE=ROOT/'reports/controlled_predictive_paired_advantage_v144'
LIVES,QUERIES,REPLICAS,WORKERS=previous.LIVES,previous.QUERIES,8,4
METHODS=('H2','PRIOR','REPLAY','UPDATED')
MODEL_METHODS=METHODS[1:]
EPOCHS,ALPHA,BASE,SUFFIXES,MAX_STEPS=32,.1,145*100000000,8,2000
save,append,read_rows,leaf_state=previous.save,previous.append,previous.read_rows,previous.leaf_state
load_teacher,delta,compact_choice,prediction=previous.load_teacher,previous.delta,previous.compact_choice,previous.prediction
old=previous.old


def evaluation_seed(life,replica): return BASE+90000000+life*100000+replica
def simulation_seed(life,replica,step): return BASE+80000000+life*1000000+replica*10000+step


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,replicas=REPLICAS,workers=WORKERS,
        methods=list(METHODS),train_replicas=[0,1,2,3],validation_replicas=[4,5,6,7],
        roots_per_game=4,suffixes_per_root=SUFFIXES,expected_roots=256,physical_branches=4096,
        root_selection='V144 LEARNED nonterminal candidate disagreements; floor((2*j+1)*n/8), j=0..3',
        epochs=EPOCHS,alpha=ALPHA,training_order=dict(PRIOR='retained V144 frozen model',
            REPLAY='old TRAIN then old TRAIN per pass',UPDATED='old TRAIN then new TRAIN per pass'),
        update='normalized LMS on exact signed n-tuple multiplicities; denominator=sum(x*x)',
        target='mean paired H1_CONT minus H2 reward/failure/success; subtract immediate reward difference',
        representation='SINGLE',continuation='H2',gate='strict positive recomposed advantage; ties H2',
        terminal_pair_rule='keep H2 if either chosen afterstate reaches goal; no learned terminal extrapolation',
        p_four=.1,max_steps=MAX_STEPS,physical_games=256,version_base=BASE,
        cutoff_rule='retain all costs; incomplete supervision blocks fitting; no replacement',
        diagnostic_policy='no validation-dependent selection, refitting or early stopping')


def extract_source(capsule,run,analysis,analysis_history):
    if not (run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V144 must be complete before coverage expansion')
    sources=deepcopy(capsule['snapshots'])
    evaluations={r['life']:r for r in run['eval_lifecycles']}
    trained={r['life']:r for r in run['lifecycles']}
    for source in sources:
        life=source['life']
        source['advantage_control_trace']=str((SOURCE/evaluations[life]['control_trace']).resolve())
        source['prior_models']={q:str((SOURCE/trained[life]['queries'][q]['model_ref']).resolve()) for q in QUERIES}
    return dict(schema='acfqp.coverage_expansion.v145.source',snapshots=sources,
        prior_examples_ref=str((SOURCE/'examples.json').resolve()),prior_run_ref=str((SOURCE/'run.json').resolve()),
        inherited_costs={**deepcopy(capsule['inherited_costs']),'v144_experiment':deepcopy(analysis['costs']),
            'v144_analysis_history':deepcopy(analysis_history)})


def acquire_lifecycle(source,roots,directory):
    started=perf_counter();life=source['life'];folder=directory/f'acquire_{life}';folder.mkdir()
    trace=str((folder/'paired_consequences.jsonl.gz').relative_to(directory))
    data=dict(life=life,consequences_trace=trace,queries={})
    with gzip.open(directory/trace,'wt') as output:
        for query in QUERIES:
            qfolder=folder/query;qfolder.mkdir()
            parent,leaf,teacher,loads=load_teacher(source,'SINGLE',query,qfolder)
            qroots=[r for r in roots if r['query']==query]
            qdata=dict(loads=loads,parent_before=leaf_state(parent,True),leaf_before=leaf_state(leaf),
                spawn_probabilities=list(teacher.spawn_probabilities),roots=len(qroots))
            data['queries'][query]=qdata;work=Counter();branches=0;statuses=Counter()
            for index,root in enumerate(qroots):
                for suffix,seed in enumerate(root['suffix_seeds']):
                    outcomes={}
                    for action in root['actions']:
                        branch=run_branch(root['board'],action,teacher,QUERIES[query],seed,MAX_STEPS,.1)
                        outcomes[action]=branch;branches+=1
                        work.update(branch['result']['environment_counts']);statuses[branch['result']['status']]+=1
                    append(output,dict(root_id=root['root_id'],suffix=suffix,seed=seed,continuation='H2',branches=outcomes))
                if (index+1)%8==0:
                    output.flush();print(json.dumps(dict(event='acquired_roots',life=life,query=query,roots=index+1,branches=branches)),flush=True)
            qdata.update(physical_branches=branches,paired_records=len(qroots)*SUFFIXES,statuses=dict(statuses),
                environment_counts=dict(work),policy_counts=dict(teacher.counts),
                parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf))
    data['seconds']=perf_counter()-started;save(folder/'lifecycle.json',data);return data


def train_lifecycle(source,old_examples,new_examples,directory):
    started=perf_counter();folder=directory/f'train_{source["life"]}';folder.mkdir()
    data=dict(life=source['life'],queries={})
    for query in QUERIES:
        old_train=[e for e in old_examples if e['query']==query and e['split']=='TRAIN']
        new_train=[e for e in new_examples if e['query']==query and e['split']=='TRAIN']
        validation={label:[e for e in examples if e['query']==query and e['split']=='VALIDATION']
            for label,examples in [('OLD',old_examples),('NEW',new_examples)]}
        qdata=dict(binding=dict(life=source['life'],query=query,continuation='H2',
            leaf_ref=source['leaves'][query]['SINGLE']['model_ref']),
            old_train_roots=[e['root_id'] for e in old_train],new_train_roots=[e['root_id'] for e in new_train],
            validation_roots={k:[e['root_id'] for e in rows] for k,rows in validation.items()},
            models={},validation={k:{} for k in validation},validation_work={k:{} for k in validation})
        models={}
        for method in MODEL_METHODS:
            train=[] if method=='PRIOR' else old_train+(old_train if method=='REPLAY' else new_train)
            model=(PairedAdvantage.from_payload(json.loads(Path(source['prior_models'][query]).read_text()))
                if method=='PRIOR' else PairedAdvantage())
            before=model.state()
            for _ in range(EPOCHS):
                for e in train:model.update(e['candidate_after'],e['baseline_after'],e['target_tail'],ALPHA)
            fit_counts=dict(model.counts);model.freeze();state=model.state()
            path=folder/f'{query}_{method}.json';save(path,model.to_payload());models[method]=model
            qdata['models'][method]=dict(model_ref=str(path.relative_to(directory)),model_bytes=path.stat().st_size,
                before=before,frozen_state=state,fit_counts=fit_counts,setup_counts=dict(model.setup_counts),
                training_roots=[e['root_id'] for e in train])
        for label,examples in validation.items():
            for method,model in models.items():
                counts=dict(model.counts)
                qdata['validation'][label][method]=[prediction(model,e) for e in examples]
                qdata['validation_work'][label][method]=delta(model.counts,counts)
        for method,model in models.items():
            qdata['models'][method].update(after_validation=model.state(),total_counts=dict(model.counts))
        data['queries'][query]=qdata
        print(json.dumps(dict(event='models_frozen',life=source['life'],query=query,old_roots=len(old_train),new_roots=len(new_train))),flush=True)
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
                    model=PairedAdvantage.from_payload(json.loads(path.read_text()));model.freeze()
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
    importlib.import_module('scripts.analyze_controlled_predictive_coverage_expansion_v145')
    files={Path(__file__).resolve(),ROOT/'specs/COVERAGE_EXPANSION_V145.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            p=Path(filename).resolve()
            if p.is_relative_to(ROOT/'src') or p.is_relative_to(ROOT/'scripts'):files.add(p)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135',
                 'program_planning_v140','shallow_sampling_v141','h1_continuation_v142'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*coverage_expansion*v145.py'))
    for p in files:
        target=directory/'source'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    read=lambda n:json.loads((SOURCE/n).read_text())
    initial_costs=read('analysis_initial_fail/analysis.json')['costs']
    history=dict(extra_initial_work={k:initial_costs[k] for k in ('analysis_replay_swipes','analysis_lms_attempts')},
        attempts=[{k:record[k] for k in ('status','seconds','stderr_bytes')} for record in
            (read('analysis_initial_fail/analysis_attempt.json'),read('analysis_attempt2.json'))])
    source=extract_source(read('source_capsule.json'),read('run.json'),read('analysis.json'),history)
    cohort=build_cohort(source['snapshots']);old_examples=json.loads(Path(source['prior_examples_ref']).read_text())['examples']
    save(directory/'source_capsule.json',source);save(directory/'cohort.json',cohort);snapshot_code(directory)
    data=dict(schema='acfqp.coverage_expansion.v145.run',status='frozen',settings=settings(),
        inherited_costs=source['inherited_costs'],acquisition_lifecycles=[],lifecycles=[],eval_lifecycles=[])
    save(directory/'frozen_inputs.json',deepcopy(data));save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        data['status']='acquisition';save(directory/'run.json',data)
        tasks=[pool.submit(acquire_lifecycle,s,[r for r in cohort['roots'] if r['life']==s['life']],directory) for s in source['snapshots']]
        for future in as_completed(tasks):
            data['acquisition_lifecycles'].append(future.result());data['acquisition_lifecycles'].sort(key=lambda r:r['life']);save(directory/'run.json',data)
        records=(r for life in data['acquisition_lifecycles'] for r in read_rows(directory/life['consequences_trace']))
        try:examples=build_examples(cohort,records)
        except ValueError as error:
            data.update(status='supervision_incomplete',error=str(error),seconds=perf_counter()-started)
            save(directory/'run.json',data);raise
        save(directory/'examples.json',examples);data['status']='training';save(directory/'run.json',data)
        tasks=[pool.submit(train_lifecycle,s,[e for e in old_examples if e['life']==s['life']],
            [e for e in examples['examples'] if e['life']==s['life']],directory) for s in source['snapshots']]
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
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_coverage_expansion_v145')
    run(parser.parse_args().output)
