"""Learn finite action successor models and compare same-data planning depths."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import importlib
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_program_consolidation_v161 as prior
from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from acfqp.science.controlled_predictive_lifelong_experience_v77 import _status
from acfqp.science.controlled_predictive_regime_experience_v115 import _spawn
from acfqp.science.controlled_predictive_policy_modules_v151 import QUERIES,counter_delta,utility
from acfqp.science.controlled_predictive_program_consolidation_v161 import canonical_frame,INVERSE,CHOICE_KEYS
from acfqp.science.controlled_predictive_causal_quotient_v171 import fit_model,compile_model,load_compiled,run_episode,state_key
from acfqp.science.controlled_predictive_consequence_generation_v168 import _moments,_pool

SOURCE = ROOT/'reports/controlled_predictive_persistent_strategy_v170'
OUTPUT = ROOT/'reports/controlled_predictive_causal_quotient_v171'
BASE,MAX_STEPS,LIVES = 17100000000,8192,tuple(range(4))
MODES = ('H2','SAME_D1','SAME_D3','XFER_D1','XFER_D3')
CONTRASTS = {'SAME_D3-SAME_D1':('SAME_D3','SAME_D1'),'SAME_D3-H2':('SAME_D3','H2'),
    'XFER_D3-XFER_D1':('XFER_D3','XFER_D1'),'XFER_D3-H2':('XFER_D3','H2'),
    'XFER_D3-SAME_D3':('XFER_D3','SAME_D3')}
read,save,append,read_rows = prior.read,prior.save,prior.append,prior.read_rows


def settings():
    return dict(lifecycles=list(LIVES),queries=['risk1'],source_games_reused=16,roots_per_source_game=8,
        roots=128,train_suffixes=4,valid_suffixes=2,training_branch_cap=2048,validation_branch_cap=1024,
        evaluation_games=640,new_physical_game_cap=3712,maximum_environment_transitions=30408704,
        max_steps=MAX_STEPS,p_four=.1,workers=4,version_base=BASE,eval_episodes=32,
        active_states=18,terminal_states=2,min_row_count=8,depths=[1,3],modes=list(MODES),
        representation='maxrank<=8/9/10 xempty0/1/>=2 xcompressedlinepositive_mergebit;goal beforeloss',
        actions='four primitive directions in CURRENT D4 canonical frame; four exact legal checks explicitly paid',
        kernel='empirical observed action successors and immediate reward/firstterminal event; edge aggregation by nextstate/status',
        tail='separate fixed source teacher H2 remaining components; SOURCEallsteps,forcedTRAINsteps>=1 only',
        planning='depth1/3 same data; select complete wholevector by risk1; terminalleaf0; unsupportedfuture early sameH2tail',
        same='own model',transfer='max separate model/action among other three histories, sourceID/action ties; never blend tails',
        acquisition='all legal root firstactions then own H2;paired seeds exclude action;ordinary initial EVAL seeds exclude arm',
        primary='SAME_D3-SAME_D1 and SAME_D3-H2 CI95 lower>0; no automatic caller promotion',
        uncertainty='paired ordinary whole episodes,32new seeds/history,fourfixedteachers; conditional frozen data/representation/models',
        incomplete='any required TRAIN/VALID missing,duplicate,cutoff,null,identity error stops downstream;no replacements',
        costs='all inherited/source/teacher/feature/fit/compile/lookup/fallback/physical/test costs retained;no efficiencyclaim',
        new_parameter_updates=0,frozen_policy='no outcome-dependent representation/depth/support/seeds/extra acquisition/U006')


def extract_source():
    run,analysis,capsule = (read(SOURCE/name) for name in ('run.json','analysis.json','source_capsule.json'))
    if not (run['status']=='complete' and analysis['valid'] and analysis['primary_complete']):
        raise ValueError('audited V170 completion required')
    traces = [dict(life=lc['life'],path=str(SOURCE/lc['source_trace'])) for lc in run['phases']['SOURCE']['lifecycles']]
    refs = deepcopy(capsule['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'),fields=['costs'])]
    refs += [dict(path=str(ROOT/f'reports/v170_runtime_tmp/{kind}_checks.json'),fields=['attempts'])
             for kind in ('core','runner','analyzer','stage')]
    return dict(schema='acfqp.causal_quotient.v171.source',snapshots=deepcopy(capsule['snapshots']),source_traces=traces,
        source_run_ref=str(SOURCE/'run.json'),source_analysis_ref=str(SOURCE/'analysis.json'),
        inherited_v170_environment_samples=analysis['costs']['new_environment_samples'],cost_refs=refs,
        this_stage_test_refs=[str(ROOT/f'reports/v171_runtime_tmp/{kind}_checks.json') for kind in ('core','runner','analyzer')])


def roots_from_source(row):
    if row['phase']!='SOURCE' or row['query']!='risk1' or row['result']['status'] not in ('WON','LOST') or len(row['actions'])<8:
        raise ValueError('complete eight-step audited H2 source required')
    n = len(row['actions']); roots=[]
    for slot in range(8):
        step = slot*n//8
        board = list(row['initial_board'] if not step else row['choices'][step-1]['afterstate'])
        if step: board[row['spawned_cells'][step-1]] = row['spawned_ranks'][step-1]
        canonical,frame = canonical_frame(board); actions=[]
        for label in ('DOWN','LEFT','RIGHT','UP'):
            _,_,legal = ground.swipe_board_v1(canonical,ground.Swipe2048Action(label))
            if legal:
                actual = ground.transform_action_v1(ground.Swipe2048Action(label),INVERSE[D4Transform(frame)]).value
                actions.append(dict(canonical_action=label,actual_action=actual))
        roots.append(dict(root_id=f'{row["source_id"]}:{slot}',life=row['life'],query='risk1',replica=row['replica'],slot=slot,
            source_id=row['source_id'],source_seed=row['seed'],source_step=step,source_steps=n,board=board,
            canonical_board=list(canonical),transform=frame,actions=actions,
            generation_counts=dict(board_transforms=8,ground_legality_swipes=4,action_transports=len(actions))))
    return roots


def branch_roster(roots,phase):
    return [dict(branch_id=f'{phase}:{r["root_id"]}:{suffix}:{a["canonical_action"]}',phase=phase,root_id=r['root_id'],
        life=r['life'],query='risk1',replica=r['replica'],slot=r['slot'],suffix=suffix,
        seed=BASE+dict(TRAIN=10000000,VALID=20000000)[phase]+r['life']*1000000+r['replica']*100000+r['slot']*1000+suffix,**a)
        for r in roots for suffix in range(4 if phase=='TRAIN' else 2) for a in r['actions']]


def eval_roster():
    return [dict(branch_id=f'EVAL:{life}:{episode}:{mode}',phase='EVAL',life=life,query='risk1',episode=episode,
        mode=mode,seed=BASE+50000000+life*1000000+episode) for life in LIVES for episode in range(32) for mode in MODES]


def run_forced_branch(bank,board,first_action,life,seed,max_steps=8192,p_four=.1):
    started=perf_counter();rng=random.Random(seed);environment,policy=Counter(),Counter()
    before={query:dict(bank[query].counts) for query in QUERIES}
    board=tuple(board);initial=board;status=_status(board,environment)
    if status!='ACTIVE':raise ValueError('forced root must be active')
    actions,cells,ranks,scores,choices=[],[],[],[],[];decision_seconds=0.
    for step in range(max_steps):
        work=Counter();decision_started=perf_counter()
        if not step:
            after,score,legal=ground.swipe_board_v1(board,ground.Swipe2048Action(first_action))
            work['forced_root_legality_swipes']+=1
            if not legal:raise ValueError('illegal forced first action')
            choice=dict(action=first_action,afterstate=list(after),score=score)
            phase,key='forced','FORCED';work['forced_root_actions']+=1
        else:
            old=dict(bank['risk1'].counts);choice=bank['risk1'].choose(board,QUERIES['risk1'])
            work['forced_decisions']+=1
            work.update({f'policy_risk1_{k}':v for k,v in counter_delta(bank['risk1'].counts,old).items()})
            phase,key='teacher','risk1'
        decision_seconds+=perf_counter()-decision_started;policy.update(work)
        compact={k:deepcopy(choice[k]) for k in CHOICE_KEYS if k in choice}
        compact.update(step=step,phase=phase,policy_key=key,work=dict(work));choices.append(compact)
        environment.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1)
        after,score,legal=ground.swipe_board_v1(board,ground.Swipe2048Action(choice['action']))
        if not legal:raise ValueError('illegal executed action')
        board,cell,rank=_spawn(after,rng,environment,p_four);environment['sampled_transitions']+=1
        status=_status(board,environment)
        actions.append(choice['action']);cells.append(cell);ranks.append(rank);scores.append(score)
        if status!='ACTIVE':break
    status='CUTOFF' if status=='ACTIVE' else status
    components=[sum(scores)/2048.,float(status=='LOST'),float(status=='WON')]
    module=dict(mode='FORCED_H2',life=life,forced_decisions=1,h2_calls=len(actions)-1)
    result=dict(score=sum(scores),steps=len(actions),status=status,components=components,
        utility=None if status=='CUTOFF' else utility(components,'risk1'),environment_counts=dict(environment),
        policy_counts=dict(policy),policy_counts_by_query={q:counter_delta(bank[q].counts,before[q]) for q in QUERIES},
        program_setup_counts={},learning_counts={},decision_seconds=decision_seconds,seconds=perf_counter()-started)
    return dict(seed=seed,root_board=list(initial),first_action=first_action,max_steps=max_steps,p_four=p_four,
        initial_spawns=[],actions=actions,spawned_cells=cells,spawned_ranks=ranks,scores=scores,choices=choices,
        final_board=list(board),module=module,result=result)


def compact_outcome(row):
    keys=('branch_id','phase','life','query','seed','mode','episode') if row['phase']=='EVAL' else (
        'branch_id','phase','root_id','life','query','replica','slot','suffix','seed','canonical_action','actual_action')
    return dict(**{k:row[k] for k in keys},**{k:deepcopy(row['result'][k]) for k in ('score','steps','status','components','utility')},module=deepcopy(row['module']))


def physical_lifecycle(source,phase,roots,model_records,directory):
    started=perf_counter();life=source['life'];folder=directory/phase.lower()/f'life_{life}';folder.mkdir(parents=True)
    bank,parents,leaves,records=prior.teachers(source,folder)
    models=[load_compiled(item['payload'],item['tables']) for item in model_records] if phase=='EVAL' else None
    plans=eval_roster() if phase=='EVAL' else branch_roster(roots,phase);lookup={r['root_id']:r for r in roots}
    trace=folder/'branches.jsonl.gz';outcomes=[];environment,policy,statuses=Counter(),Counter(),Counter()
    with gzip.open(trace,'wt') as output:
        for plan in plans:
            if plan['life']!=life:continue
            if phase=='EVAL':row=run_episode(bank,models,life,plan['mode'],plan['seed'],MAX_STEPS,.1)
            else:row=run_forced_branch(bank,lookup[plan['root_id']]['board'],plan['actual_action'],life,plan['seed'],MAX_STEPS,.1)
            row.update(plan);append(output,row);outcomes.append(compact_outcome(row))
            result=row['result'];environment.update(result['environment_counts']);policy.update(result['policy_counts']);statuses[result['status']]+=1
    prior.finish_teachers(bank,parents,leaves,records);save(folder/'outcomes.json',outcomes)
    data=dict(phase=phase,life=life,branch_trace=str(trace.relative_to(directory)),outcomes_ref=str((folder/'outcomes.json').relative_to(directory)),
        teacher_bank=records,physical_branches=len(outcomes),environment_counts=dict(environment),policy_counts=dict(policy),
        program_setup_counts={},statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);print(dict(event='games_completed',phase=phase,life=life,games=len(outcomes)),flush=True)
    return data


def fit_lifecycle(source,phase,source_traces,directory):
    life=source['life'];source_trace=next(r['path'] for r in source_traces if r['life']==life)
    started=perf_counter();payload=fit_model(read_rows(source_trace),read_rows(directory/'train'/f'life_{life}'/'branches.jsonl.gz'),life)
    fit_seconds=perf_counter()-started;started=perf_counter();compiled=compile_model(payload)
    data=dict(payload=payload,tables=compiled.tables,compile_counts=compiled.counts,fit_seconds=fit_seconds,compile_seconds=perf_counter()-started)
    folder=directory/'models';folder.mkdir(exist_ok=True);path=folder/f'life_{life}.json';save(path,data)
    return dict(life=life,model_ref=str(path.relative_to(directory)),training_lives=[life])


def complete_cohort(outcomes,plans):
    indexed={r['branch_id']:r for r in outcomes}
    return len(indexed)==len(outcomes)==len(plans) and set(indexed)=={p['branch_id'] for p in plans} and all(
        all(indexed[p['branch_id']][k]==v for k,v in p.items()) and indexed[p['branch_id']]['status'] in ('WON','LOST') and
        indexed[p['branch_id']]['components']==[indexed[p['branch_id']]['score']/2048.,float(indexed[p['branch_id']]['status']=='LOST'),float(indexed[p['branch_id']]['status']=='WON')] and
        indexed[p['branch_id']]['utility']==utility(indexed[p['branch_id']]['components'],'risk1') for p in plans)


def eval_summary(outcomes):
    plans=eval_roster();complete=complete_cohort(outcomes,plans);index={r['branch_id']:r for r in outcomes};comparisons=[]
    for name,(left,right) in CONTRASTS.items():
        histories=[]
        for life in LIVES:
            values={metric:[] for metric in ('utility','reward','failure','success')}
            for episode in range(32):
                rows=[index.get(f'EVAL:{life}:{episode}:{mode}') for mode in (left,right)]
                valid=all(r is not None and r['status'] in ('WON','LOST') and r['utility'] is not None for r in rows) and complete
                delta=[a-b for a,b in zip(rows[0]['components'],rows[1]['components'])] if valid else None
                for metric,value in zip(values,[utility(delta,'risk1'),*delta] if valid else [None]*4):values[metric].append(value)
            histories.append(dict(life=life,episodes=32,metrics={metric:_moments(v) for metric,v in values.items()}))
        metrics={metric:_pool([h['metrics'][metric] for h in histories],4) for metric in values}
        for stat in metrics.values():
            stat['conditional_episode_se']=stat.pop('conditional_suffix_se');stat['conditional_episode_ci95']=stat.pop('conditional_suffix_ci95')
        comparisons.append(dict(query='risk1',contrast=name,episodes=128,complete=complete,metrics=metrics,per_history=histories))
    diagnostics=[]
    for mode in MODES:
        rows=[r for r in outcomes if r.get('mode')==mode];counts=Counter()
        for r in rows:counts.update({k:v for k,v in r['module'].items() if k not in ('life','depth') and isinstance(v,int)})
        steps=sum(r['steps'] for r in rows)
        diagnostics.append(dict(mode=mode,present_episodes=len(rows),steps=steps,module_counts=dict(counts),
            source_counts=[sum(r['module'].get('source_counts',[0]*4)[j] for r in rows) for j in LIVES],
            model_fraction=counts.get('model_decisions',0)/steps if steps else None,h2_fraction=counts.get('h2_calls',0)/steps if steps else None))
    return dict(schema='acfqp.causal_quotient.v171.summary',complete=complete,comparisons=comparisons,policy_diagnostics=diagnostics)


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_causal_quotient_v171')
    importlib.import_module('scripts.causal_quotient_diagnostics_v171')
    files={Path(__file__).resolve(),ROOT/'specs/CAUSAL_QUOTIENT_PLANNING_V171.md',ROOT/'reports/v171_runtime_tmp/run_stage.py'}
    files.update((ROOT/'tests').glob('*causal_quotient*v171.py'))
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    for path in sorted(files):
        dest=directory/'source_code'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    return len(files)


def run(directory=OUTPUT):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule=extract_source();save(directory/'source_capsule.json',capsule)
    source_rows=[row for ref in capsule['source_traces'] for row in read_rows(ref['path'])]
    if len(source_rows)!=16 or sorted((r['life'],r['replica']) for r in source_rows)!=[(l,r) for l in LIVES for r in range(4)]:
        raise ValueError('SOURCE16 roster required')
    roots=[root for row in source_rows for root in roots_from_source(row)];del source_rows
    plans={phase:branch_roster(roots,phase) for phase in ('TRAIN','VALID')};plans['EVAL']=eval_roster()
    frozen=dict(settings=settings(),roots=roots,**{f'{p.lower()}_roster':rows for p,rows in plans.items()})
    save(directory/'frozen_inputs.json',frozen)
    data=dict(schema='acfqp.causal_quotient.v171.run',status='frozen',settings=settings(),phases={},phase_order=['INPUTS_FROZEN'],
        frozen_source_files=snapshot_code(directory),new_parameter_updates=0,inherited_cost_refs=capsule['cost_refs'])
    save(directory/'run.json',data)
    def acquire(phase,models):
        data['status']=phase.lower();save(directory/'run.json',data)
        data['phases'][phase]=prior.parallel_phase(physical_lifecycle,capsule['snapshots'],phase,roots,models,directory)
        data['phase_order'].append(phase);save(directory/'run.json',data)
        return [r for lc in data['phases'][phase]['lifecycles'] for r in read(directory/lc['outcomes_ref'])]
    def stop():
        data.update(status='incomplete_training',seconds=perf_counter()-started);save(directory/'run.json',data)
        print(dict(status=data['status'],phase_order=data['phase_order']),flush=True)
    outcomes=acquire('TRAIN',None)
    if not complete_cohort(outcomes,plans['TRAIN']):stop();return
    fitted=prior.parallel_phase(fit_lifecycle,capsule['snapshots'],'FIT',capsule['source_traces'],directory)
    save(directory/'frozen_models.json',fitted['lifecycles']);data['model_fit']=fitted
    model_records=[read(directory/r['model_ref']) for r in fitted['lifecycles']]
    data['phase_order'].append('MODELS_FROZEN');save(directory/'run.json',data)
    outcomes=acquire('VALID',None)
    if not complete_cohort(outcomes,plans['VALID']):stop();return
    from scripts.causal_quotient_diagnostics_v171 import prediction_report
    models=[load_compiled(r['payload'],r['tables']) for r in model_records]
    valid_rows=(row for lc in data['phases']['VALID']['lifecycles'] for row in read_rows(directory/lc['branch_trace']))
    start=perf_counter();save(directory/'prediction_diagnostics.json',prediction_report(models,valid_rows));data['diagnostic_seconds']=perf_counter()-start
    outcomes=acquire('EVAL',model_records);save(directory/'summary.json',eval_summary(outcomes))
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(dict(status='complete',seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    run(parser.parse_args().output)
