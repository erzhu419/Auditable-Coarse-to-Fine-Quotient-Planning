"""Matched-branch experiment for probability-weighted first-spawn evidence."""
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_fixed_board_replication_v175 as previous
from acfqp.science.controlled_predictive_spawn_stratification_v176 import joint_support,allocation,analyze_batches

physical=previous.parent.prior.old
ground,read,save,append=physical.ground,previous.read,previous.save,previous.append
SOURCE=ROOT/'reports/controlled_predictive_fixed_board_replication_v175'
OUTPUT=ROOT/'reports/controlled_predictive_spawn_stratification_v176'
BASE,BLOCKS,MAX_STEPS,LIVES=17600000000,8,8192,tuple(range(4))
METHODS,MODES,COHORTS=('IID','STRAT'),('TREE','ONE'),('TRAIN','FRESH')


def settings():
    return dict(blocks=BLOCKS,lifecycles=list(LIVES),cohorts=list(COHORTS),methods=list(METHODS),
        modes=list(MODES),selected_roots=8,roots_per_cohort_history=1,workers=4,max_steps=MAX_STEPS,
        p_four=.1,version_base=BASE,minimum_stratum_replicates=2,draws_per_support_entry=4,
        selection='median support cardinality among changed roots per cohort/history; cardinality then root_id',
        allocation='two per stratum then probability-only marginal variance reduction allocation to 4*S',
        coupling='joint cell-uniform support and common rank; independent first-spawn and tail RNG; shared tail seeds across methods/actions',
        estimator='STRAT probability-weighted stratum means; IID paired arithmetic mean; equal eight-board block means',
        primary='conditional utility block variance STRAT-IID; paired delete-block jackknife normal CI95 upper<0',
        secondary='descriptive variance ratios, full vectors and variance times mean block transition cost',
        incomplete='missing, duplicate, nonterminal or misbound required branch -> HOLD; no replacement',
        new_source_games=0,new_model_fits=0,new_parameter_updates=0,autonomous_evaluation=False,
        strategy_promotion=False,matched_budget='physical branch counts; actual transitions and all other paid costs reported')


def extract_source(directory=SOURCE):
    directory=Path(directory)
    run,audit,stage,capsule,roots,choices=[read(path) for path in (
        directory/'run.json',directory/'analysis.json',ROOT/'reports/v175_runtime_tmp/stage_checks.json',
        directory/'source_capsule.json',directory/'roots.json',directory/'frozen_choices.json')]
    if not(run['status']=='complete' and audit['valid'] and audit['complete'] and stage['valid']):
        raise ValueError('independently completed V175 required')
    index={root['root_id']:root for root in roots};candidates=[]
    for choice in choices['choices']:
        if not choice['changed']:continue
        original=index[choice['root_id']];actuals={row['canonical_action']:row['actual_action'] for row in original['actions']}
        row={key:deepcopy(original[key]) for key in ('root_id','cohort','life','source_id','board','canonical_board')}
        row.update(source_root_ordinal=original['ordinal'],actions={},afterstates={})
        for mode in MODES:
            action=choice['decisions'][mode]['canonical_action'];actual=actuals[action]
            after,score,legal=ground.swipe_board_v1(tuple(row['board']),ground.Swipe2048Action(actual))
            if not legal:raise ValueError('frozen action is illegal')
            row['actions'][mode]=dict(canonical_action=action,actual_action=actual)
            row['afterstates'][mode]=dict(board=list(after),score=score,empty=[i for i,value in enumerate(after) if not value])
        row['support']=joint_support(row['afterstates']['TREE']['empty'],row['afterstates']['ONE']['empty'])
        row['allocation']={str(key):value for key,value in allocation(row['support']).items()}
        row['draws_per_block']=4*len(row['support']);candidates.append(row)
    selected=[]
    for cohort in COHORTS:
        for life in LIVES:
            local=sorted((row for row in candidates if row['cohort']==cohort and row['life']==life),
                key=lambda row:(len(row['support']),row['root_id']))
            row=deepcopy(local[len(local)//2]);row['probe_ordinal']=len(selected);selected.append(row)
    manifest=dict(source_roots_ref=str(directory/'roots.json'),source_choices_ref=str(directory/'frozen_choices.json'),
        work=dict(json_read_operations=6,changed_root_records=len(candidates),support_ground_swipe_calls=2*len(candidates),
            joint_support_builds=len(candidates),selected_roots=8),
        candidates=[dict(root_id=row['root_id'],cohort=row['cohort'],life=row['life'],support_entries=len(row['support'])) for row in candidates])
    refs=deepcopy(capsule['cost_refs'])+[dict(path=str(directory/'analysis.json'),fields=['costs'])]
    refs += [dict(path=str(ROOT/f'reports/v175_runtime_tmp/{kind}_checks.json'),fields=['attempts']) for kind in ('core','runner','analyzer','stage')]
    refs += [dict(path=str(ROOT/'reports/v175_runtime_tmp/engineering_recovery.json'),fields=['failed_stage_ref','extra_failed_teacher_loads'])]
    refs += [dict(path=str(ROOT/'reports/v176_runtime_tmp/preflight_checks.json'),fields=['attempts'])]
    source=dict(schema='acfqp.spawn_stratification.v176.source',snapshots=deepcopy(capsule['snapshots']),
        inherited_run_ref=str(directory/'run.json'),inherited_analysis_ref=str(directory/'analysis.json'),
        inherited_stage_ref=str(ROOT/'reports/v175_runtime_tmp/stage_checks.json'),
        inherited_v175_environment_samples=audit['costs']['new_environment_samples'],cost_refs=refs,
        this_stage_test_refs=[str(ROOT/f'reports/v176_runtime_tmp/{kind}_checks.json') for kind in ('core','runner','analyzer')])
    return dict(source=source,manifest=manifest,roots=selected)


def branch_roster(roots):
    plans=[]
    for root in roots:
        schedule=[(entry['stratum'],replicate) for entry in root['support']
            for replicate in range(root['allocation'][str(entry['stratum'])])]
        if len(schedule)!=root['draws_per_block']:raise ValueError('allocation does not match budget')
        for block in range(BLOCKS):
            for method in METHODS:
                for draw in range(root['draws_per_block']):
                    stratum,replicate=schedule[draw] if method=='STRAT' else (None,None)
                    offset=root['probe_ordinal']*100000+block*1000+draw
                    for mode in MODES:
                        plans.append(dict(branch_id=f'PROBE:{root["root_id"]}:{block}:{method}:{draw}:{mode}',
                            phase='PROBE',root_id=root['root_id'],cohort=root['cohort'],life=root['life'],
                            source_id=root['source_id'],probe_ordinal=root['probe_ordinal'],query='risk1',method=method,block=block,suffix=draw,
                            mode=mode,stratum=stratum,replicate=replicate,seed=BASE+10000000+offset,
                            spawn_seed=BASE+20000000+offset,**root['actions'][mode]))
    return plans


def run_conditional_branch(bank,root,plan,max_steps=MAX_STEPS):
    started=perf_counter();tail_rng=random.Random(plan['seed']);first_rng=random.Random(plan['spawn_seed'])
    environment,policy=Counter(),Counter();before={query:dict(bank[query].counts) for query in physical.QUERIES}
    board=tuple(root['board']);initial=board;status=physical._status(board,environment)
    if status!='ACTIVE':raise ValueError('forced root must be active')
    actions,cells,ranks,scores,choices=[],[],[],[],[];decision_seconds=0.
    for step in range(max_steps):
        work=Counter();decision_started=perf_counter()
        if not step:
            after,score,legal=ground.swipe_board_v1(board,ground.Swipe2048Action(plan['actual_action']))
            if not legal:raise ValueError('illegal first action')
            choice=dict(action=plan['actual_action'],afterstate=list(after),score=score)
            phase,key='forced','FORCED';work.update(forced_root_legality_swipes=1,forced_root_actions=1)
        else:
            old=dict(bank['risk1'].counts);choice=bank['risk1'].choose(board,physical.QUERIES['risk1'])
            work['forced_decisions']+=1
            work.update({f'policy_risk1_{key}':value for key,value in physical.counter_delta(bank['risk1'].counts,old).items()})
            phase,key='teacher','risk1'
        decision_seconds+=perf_counter()-decision_started;policy.update(work)
        compact={key:deepcopy(choice[key]) for key in physical.CHOICE_KEYS if key in choice}
        compact.update(step=step,phase=phase,policy_key=key,work=dict(work));choices.append(compact)
        environment.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1)
        after,score,legal=ground.swipe_board_v1(board,ground.Swipe2048Action(choice['action']))
        if not legal:raise ValueError('illegal executed action')
        if not step and plan['method']=='STRAT':
            support=root['support'][plan['stratum']]
            cell=support['tree_cell' if plan['mode']=='TREE' else 'one_cell'];rank=support['rank']
            if after[cell]!=0:raise ValueError('conditional spawn cell is occupied')
            new=list(after);new[cell]=rank;board=tuple(new)
            environment['conditioned_first_spawn_assignments']+=1
        else:
            board,cell,rank=physical._spawn(after,first_rng if not step else tail_rng,environment,.1)
        environment['sampled_transitions']+=1;status=physical._status(board,environment)
        actions.append(choice['action']);cells.append(cell);ranks.append(rank);scores.append(score)
        if status!='ACTIVE':break
    status='CUTOFF' if status=='ACTIVE' else status;vector=[sum(scores)/2048.,float(status=='LOST'),float(status=='WON')]
    result=dict(score=sum(scores),steps=len(actions),status=status,components=vector,
        utility=None if status=='CUTOFF' else physical.utility(vector,'risk1'),environment_counts=dict(environment),
        policy_counts=dict(policy),policy_counts_by_query={query:physical.counter_delta(bank[query].counts,before[query]) for query in physical.QUERIES},
        program_setup_counts={},learning_counts={},decision_seconds=decision_seconds,seconds=perf_counter()-started)
    return dict(**plan,root_board=list(initial),first_action=plan['actual_action'],max_steps=max_steps,p_four=.1,
        initial_spawns=[],actions=actions,spawned_cells=cells,spawned_ranks=ranks,scores=scores,choices=choices,
        final_board=list(board),module=dict(mode='FORCED_H2',life=plan['life'],forced_decisions=1,h2_calls=len(actions)-1),result=result)


def compact_outcome(row):
    keys=('branch_id','phase','root_id','cohort','life','source_id','probe_ordinal','query','method','block','suffix','mode',
        'stratum','replicate','seed','spawn_seed','canonical_action','actual_action')
    return dict(**{key:deepcopy(row[key]) for key in keys},
        **{key:deepcopy(row['result'][key]) for key in ('score','steps','status','components','utility')},module=deepcopy(row['module']))


def physical_lifecycle(source,inputs,directory):
    started=perf_counter();life=source['life'];folder=directory/'probe'/f'life_{life}';folder.mkdir(parents=True)
    bank,parents,leaves,records=physical.prior.teachers(source,folder)
    roots={row['root_id']:row for row in inputs['roots']};outcomes=[]
    environment,policy,statuses=Counter(),Counter(),Counter();trace=folder/'branches.jsonl.gz'
    with gzip.open(trace,'wt') as stream:
        for plan in inputs['plans']:
            if plan['life']!=life:continue
            row=run_conditional_branch(bank,roots[plan['root_id']],plan);append(stream,row);outcomes.append(compact_outcome(row))
            result=row['result'];environment.update(result['environment_counts']);policy.update(result['policy_counts']);statuses[result['status']]+=1
    physical.prior.finish_teachers(bank,parents,leaves,records);save(folder/'outcomes.json',outcomes)
    result=dict(phase='PROBE',life=life,branch_trace=str(trace.relative_to(directory)),
        outcomes_ref=str((folder/'outcomes.json').relative_to(directory)),teacher_bank=records,
        physical_branches=len(outcomes),environment_counts=dict(environment),policy_counts=dict(policy),
        program_setup_counts={},statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',result);print(dict(event='probe_completed',life=life,branches=len(outcomes)),flush=True)
    return result


def construct_batches(roots,plans,outcomes):
    if not physical.complete_cohort(outcomes,plans):raise ValueError('incomplete frozen branch roster')
    index={(row['root_id'],row['method'],row['block'],row['suffix'],row['mode']):row for row in outcomes}
    batches=[]
    for root in roots:
        for block in range(BLOCKS):
            for method in METHODS:
                pairs=[];cost=0
                for draw in range(root['draws_per_block']):
                    left,right=[index[root['root_id'],method,block,draw,mode] for mode in MODES]
                    pair=[a-b for a,b in zip(left['components'],right['components'])]
                    if method=='STRAT':
                        support=root['support'][left['stratum']]
                        weight=support['probability']/root['allocation'][str(left['stratum'])]
                    else:weight=1/root['draws_per_block']
                    pairs.append((weight,pair));cost+=left['steps']+right['steps']
                batches.append(dict(method=method,block=block,root_id=root['root_id'],cohort=root['cohort'],life=root['life'],
                    components=[sum(weight*pair[k] for weight,pair in pairs) for k in range(3)],
                    physical_branches=2*root['draws_per_block'],environment_samples=cost))
    return batches


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_spawn_stratification_v176')
    files={Path(__file__).resolve(),ROOT/'specs/SPAWN_STRATIFICATION_V176.md',
        ROOT/'reports/v176_runtime_tmp/run_checks.py',ROOT/'reports/v176_runtime_tmp/run_stage.py'}
    files.update((ROOT/'tests').glob('*spawn_stratification*v176.py'))
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    for path in sorted(files):
        target=directory/'source_code'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    return len(files)


def run(directory=OUTPUT):
    begun=perf_counter();directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    inputs=extract_source();plans=branch_roster(inputs['roots'])
    save(directory/'source_capsule.json',inputs['source']);save(directory/'source_manifest.json',inputs['manifest'])
    save(directory/'selected_roots.json',inputs['roots']);save(directory/'branch_roster.json',plans)
    save(directory/'frozen_inputs.json',dict(settings=settings()))
    counts=Counter(plan['method'] for plan in plans)
    print(dict(event='roster_frozen',branches=len(plans),by_method=dict(counts)),flush=True)
    data=dict(schema='acfqp.spawn_stratification.v176.run',status='frozen',settings=settings(),
        phase_order=['INPUTS_FROZEN','ROSTER_FROZEN'],phases={},physical_roster_counts=dict(counts),
        physical_branch_cap=len(plans),maximum_environment_transitions=len(plans)*MAX_STEPS,
        new_model_fits=0,new_parameter_updates=0,inherited_cost_refs=inputs['source']['cost_refs'],
        frozen_source_files=snapshot_code(directory))
    save(directory/'run.json',data)
    data['status']='probe';save(directory/'run.json',data)
    data['phases']['PROBE']=physical.prior.parallel_phase(physical_lifecycle,inputs['source']['snapshots'],
        dict(roots=inputs['roots'],plans=plans),directory)
    data['phase_order'].append('PROBE');outcomes=[row for lifecycle in data['phases']['PROBE']['lifecycles']
        for row in read(directory/lifecycle['outcomes_ref'])]
    if not physical.complete_cohort(outcomes,plans):
        data.update(status='HOLD',reason='incomplete_probe',seconds=perf_counter()-begun);save(directory/'run.json',data);return
    started=perf_counter();batches=construct_batches(inputs['roots'],plans,outcomes);summary=analyze_batches(batches)
    save(directory/'batches.json',batches);save(directory/'summary.json',summary)
    data.update(status='complete' if summary['complete'] else 'HOLD',summary_seconds=perf_counter()-started,seconds=perf_counter()-begun)
    save(directory/'run.json',data);print(dict(status=data['status'],seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    run(parser.parse_args().output)
