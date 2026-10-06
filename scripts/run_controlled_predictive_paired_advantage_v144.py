"""Learn paired terminal consequences, then test a frozen action gate in new games."""
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
from scripts import run_controlled_predictive_counterfactual_outcomes_v143 as previous
from acfqp.science.controlled_predictive_paired_advantage_v144 import PairedAdvantage, AdvantagePlanner
from acfqp.science.controlled_predictive_h1_continuation_v142 import H1ContinuationPlanner

SOURCE=ROOT/'reports/controlled_predictive_counterfactual_outcomes_v143'
LIVES,QUERIES,REPLICAS,WORKERS=previous.LIVES,previous.QUERIES,8,4
METHODS=('H2','ZERO','LEARNED')
TRAIN_REPLICAS=(0,1,2,3)
VALIDATION_REPLICAS=(4,5,6,7)
EPOCHS,ALPHA,BASE=32,.1,144*100000000
save,append,read_rows,leaf_state=previous.save,previous.append,previous.read_rows,previous.leaf_state
load_teacher=previous.load_teacher
old=previous.previous.previous.previous.old


def delta(after,before): return {k:v-before.get(k,0) for k,v in after.items() if v!=before.get(k,0)}
def evaluation_seed(life,replica): return BASE+90000000+life*100000+replica
def simulation_seed(life,replica,step): return BASE+80000000+life*1000000+replica*10000+step


def settings():
    return dict(lifecycles=list(LIVES),queries=QUERIES,replicas=REPLICAS,workers=WORKERS,
        methods=list(METHODS),train_replicas=list(TRAIN_REPLICAS),validation_replicas=list(VALIDATION_REPLICAS),
        roots_per_game=4,suffixes_per_root=8,epochs=EPOCHS,alpha=ALPHA,
        update='normalized LMS on exact signed n-tuple multiplicities; denominator=sum(x*x)',
        target='mean paired H1_CONT minus H2 reward/failure/success; subtract immediate reward difference',
        representation='SINGLE',continuation='H2',gate='strict positive recomposed advantage; ties H2',
        terminal_pair_rule='keep H2 if either chosen afterstate reaches goal; no learned terminal extrapolation',
        p_four=.1,max_steps=2000,physical_games=192,version_base=BASE,new_training_environment_samples=0,
        diagnostic_policy='no validation-dependent selection, refitting or early stopping')


def extract_source(capsule,run,analysis):
    if not (run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V143 paired outcomes must be complete')
    sources=deepcopy(capsule['snapshots']); evaluations={r['life']:r for r in run['eval_lifecycles']}
    for s in sources:
        s['paired_consequences_trace']=str((SOURCE/evaluations[s['life']]['consequences_trace']).resolve())
    return dict(schema='acfqp.paired_advantage.v144.source',snapshots=sources,
        cohort_ref=str((SOURCE/'cohort.json').resolve()),
        inherited_costs={**deepcopy(capsule['inherited_costs']),'v143_experiment':deepcopy(analysis['costs'])},
        required_inputs='V143 paired terminal branches, original root choices, frozen H2/H1 leaves and final factored dynamics')


def build_examples(source):
    cohort=json.loads(Path(source['cohort_ref']).read_text()); roots={r['root_id']:r for r in cohort['roots']}
    grouped={key:[] for key in roots}; reads=Counter()
    for s in source['snapshots']:
        for row in read_rows(s['paired_consequences_trace']):
            root=roots[row['root_id']]; a=root['choices']['H1_CONT']; b=root['choices']['H2']
            ca,cb=row['branches'][a],row['branches'][b]
            if root['life']!=s['life'] or row['continuation']!='H2' or row['seed']!=root['suffix_seeds'][row['suffix']]:
                raise ValueError('paired source identity differs')
            if any(c['result']['status'] not in ('WON','LOST') for c in (ca,cb)):
                raise ValueError('paired terminal supervision is incomplete')
            immediate=(ca['scores'][0]-cb['scores'][0])/2048.
            total=[x-y for x,y in zip(ca['result']['components'],cb['result']['components'])]
            grouped[row['root_id']].append(dict(suffix=row['suffix'],immediate_difference=immediate,
                candidate_after=ca['first_afterstate'],baseline_after=cb['first_afterstate'],
                target_total=total,target_tail=[total[0]-immediate,*total[1:]]))
            reads.update(paired_records=1,physical_branches=len(row['branches']))
    examples=[]
    for key,root in roots.items():
        rows=sorted(grouped[key],key=lambda r:r['suffix'])
        if [r['suffix'] for r in rows]!=list(range(8)): raise ValueError('paired suffix roster differs')
        first=rows[0]
        for r in rows:
            if any(r[k]!=first[k] for k in ('immediate_difference','candidate_after','baseline_after')):
                raise ValueError('paired first-action exits differ across suffixes')
        if max(first['candidate_after']+first['baseline_after'])>=11:
            raise ValueError('V143 declared nonterminal afterstate cohort differs')
        examples.append(dict(root_id=key,life=root['life'],query=root['query'],replica=root['replica'],
            slot=root['slot'],step=root['step'],split='TRAIN' if root['replica'] in TRAIN_REPLICAS else 'VALIDATION',
            candidate_action=root['choices']['H1_CONT'],baseline_action=root['choices']['H2'],
            **{k:deepcopy(first[k]) for k in ('immediate_difference','candidate_after','baseline_after')},
            target_total=[sum(r['target_total'][i] for r in rows)/8 for i in range(3)],
            target_tail=[sum(r['target_tail'][i] for r in rows)/8 for i in range(3)],suffixes=8))
    if len(examples)!=256 or reads['paired_records']!=2048: raise ValueError('incomplete V143 supervision roster')
    examples.sort(key=lambda e:(e['life'],list(QUERIES).index(e['query']),e['replica'],e['slot']))
    return dict(schema='acfqp.paired_advantage.v144.examples',examples=examples,source_rows_read=dict(reads))


def prediction(model,example):
    tail=[0.,0.,0.] if example['candidate_action']==example['baseline_action'] else model.predict(example['candidate_after'],example['baseline_after'])
    q=QUERIES[example['query']]
    advantage=example['immediate_difference']+tail[0]-q['failure_penalty']*tail[1]+q['goal_bonus']*tail[2]
    return dict(root_id=example['root_id'],predicted_tail=tail,estimated_advantage=advantage,selected_h1=advantage>0)


def train_lifecycle(source,examples,directory):
    started=perf_counter(); folder=directory/f'train_{source["life"]}'; folder.mkdir()
    data=dict(life=source['life'],queries={})
    for query in QUERIES:
        train=[e for e in examples if e['query']==query and e['split']=='TRAIN']
        validation=[e for e in examples if e['query']==query and e['split']=='VALIDATION']
        model=PairedAdvantage(); before=model.state()
        for _ in range(EPOCHS):
            for e in train: model.update(e['candidate_after'],e['baseline_after'],e['target_tail'],ALPHA)
        fit_counts=dict(model.counts); model.freeze(); state=model.state()
        path=folder/f'{query}.json'; payload=model.to_payload(); save(path,payload)
        zero=PairedAdvantage(); zero.freeze(); baseline_counts=dict(model.counts)
        diagnostics={name:[prediction(m,e) for e in validation] for name,m in [('ZERO',zero),('LEARNED',model)]}
        data['queries'][query]=dict(binding=dict(life=source['life'],query=query,continuation='H2',
            leaf_ref=source['leaves'][query]['SINGLE']['model_ref']),
            train_roots=[e['root_id'] for e in train],validation_roots=[e['root_id'] for e in validation],
            model_ref=str(path.relative_to(directory)),model_bytes=path.stat().st_size,
            before=before,frozen_state=state,after_validation=model.state(),fit_counts=fit_counts,
            setup_counts=dict(model.setup_counts),validation=diagnostics,
            validation_work=dict(ZERO=dict(zero.counts),LEARNED=delta(model.counts,baseline_counts)),
            total_counts=dict(model.counts))
        print(json.dumps(dict(event='learner_frozen',life=source['life'],query=query,train_roots=len(train))),flush=True)
    data['seconds']=perf_counter()-started;save(folder/'lifecycle.json',data);return data


def compact_choice(choice):
    keys=('action','afterstate','score','value','tail_value','status','value_kind','action_values')
    return {k:deepcopy(choice[k]) for k in keys if k in choice}


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
            for k in ('baseline_choice','candidate_choice'): row['selection'][k]=compact_choice(choice['selection'][k])
        choices.append(row);prior=choice['action'];return prior
    game=old.run_episode(evaluation_seed(life,replica),act,.1,2000)
    result=old.game_result(game,query,delta(planner.counts,before),decision_seconds)
    if result['status']=='CUTOFF': result['utility']=None
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
                if method=='H2': planner=teacher
                else:
                    model=PairedAdvantage() if method=='ZERO' else PairedAdvantage.from_payload(json.loads((directory/trained['queries'][query]['model_ref']).read_text()))
                    model.freeze();planner=AdvantagePlanner(teacher,candidate,model,QUERIES[query])
                before=dict(planner.counts);state=None if model is None else model.state()
                for replica in range(REPLICAS): append(output,play(planner,life,query,method,replica))
                output.flush()
                qdata['planners'][method]=dict(counts=delta(planner.counts,before),model_before=state,
                    model_after=None if model is None else model.state(),
                    setup_counts={} if model is None else dict(model.setup_counts))
                print(json.dumps(dict(event='control_complete',life=life,query=query,method=method)),flush=True)
            qdata.update(parent_after=leaf_state(parent,True),leaf_after=leaf_state(leaf),
                teacher_total_counts=dict(teacher.counts),candidate_total_counts=dict(candidate.counts))
    data['seconds']=perf_counter()-started;save(folder/'lifecycle.json',data);return data


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_paired_advantage_v144')
    files={Path(__file__).resolve(),ROOT/'specs/PAIRED_ADVANTAGE_V144.md'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            p=Path(filename).resolve()
            if p.is_relative_to(ROOT/'src') or p.is_relative_to(ROOT/'scripts'):files.add(p)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135',
                 'program_planning_v140','shallow_sampling_v141','h1_continuation_v142'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    files.update((ROOT/'tests').glob('*paired_advantage*v144.py'))
    for p in files:
        target=directory/'source'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    read=lambda n:json.loads((SOURCE/n).read_text())
    source=extract_source(read('source_capsule.json'),read('run.json'),read('analysis.json'));examples=build_examples(source)
    save(directory/'source_capsule.json',source);save(directory/'examples.json',examples);snapshot_code(directory)
    data=dict(schema='acfqp.paired_advantage.v144.run',status='frozen',settings=settings(),
        inherited_costs=source['inherited_costs'],lifecycles=[],eval_lifecycles=[])
    save(directory/'frozen_inputs.json',deepcopy(data));save(directory/'run.json',data)
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(train_lifecycle,s,[e for e in examples['examples'] if e['life']==s['life']],directory) for s in source['snapshots']]
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
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_paired_advantage_v144')
    run(parser.parse_args().output)
