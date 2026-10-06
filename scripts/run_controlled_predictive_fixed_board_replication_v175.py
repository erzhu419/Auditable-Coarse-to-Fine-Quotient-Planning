"""Replicate V174 frozen TREE/ONE policies on retained TRAIN and VALID boards."""
import argparse
from collections import Counter
from copy import deepcopy
import gzip
import importlib
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_utility_partition_v174 as parent
from acfqp.science.controlled_predictive_fixed_board_replication_v175 import freeze_selections, summarize_replication

SOURCE=ROOT/'reports/controlled_predictive_utility_partition_v174'
OUTPUT=ROOT/'reports/controlled_predictive_fixed_board_replication_v175'
BASE,SUFFIXES,MAX_STEPS,LIVES=17500000000,16,8192,tuple(range(4))
COHORTS=('TRAIN','FRESH')
PHASES=('TRAIN_REPL','FRESH_REPL')
MODES={'TREE':'PART_UTILITY_UNPRUNED','ONE':'ONE_LATE'}
PHASE_ORDER=['INPUTS_FROZEN','POLICIES_FROZEN',*PHASES]
read,save,append=parent.read,parent.save,parent.append


def settings():
    return dict(lifecycles=list(LIVES),queries=['risk1'],workers=4,version_base=BASE,
        max_steps=MAX_STEPS,p_four=.1,cohorts=list(COHORTS),train_roots=384,fresh_roots=256,
        source_clusters_per_history=dict(TRAIN=12,FRESH=8),roots_per_source=8,
        suffixes=SUFFIXES,reference_suffixes=4,modes=MODES,
        physical_branch_cap=20480,maximum_environment_transitions=167772160,
        new_source_games=0,new_model_fits=0,new_parameter_updates=0,
        same_action='zero difference and no physical branch; retain root and SOURCE denominator',
        ordinal='cohort/history complete root_id order before skipping same-action roots',
        uncertainty='SOURCE-cluster and fixed-board paired-suffix normal CI95; old observed reference fixed; cohort variance sums',
        diagnostic_questions=['TRAIN_NEW positive','TRAIN_NEW-OLD negative','FRESH_NEW direction','FRESH_NEW-TRAIN_NEW negative'],
        incomplete='missing, duplicate, nonterminal, misbound or unsupported -> HOLD; no replacement',
        autonomous_evaluation=False,strategy_promotion=False)


def extract_source(directory=SOURCE):
    directory=Path(directory);counts=Counter()
    def load(path):
        counts['json_read_operations']+=1
        return read(path)
    run=load(directory/'run.json');audit=load(directory/'analysis.json')
    capsule=load(directory/'source_capsule.json');stage=load(ROOT/'reports/v174_runtime_tmp/stage_checks.json')
    if not (run['status']=='complete' and audit['valid'] and audit['primary_complete'] and stage['valid']):
        raise ValueError('completed independently audited V174 required, irrespective of scientific FAIL')
    models={life:{} for life in LIVES};records={};model_refs=[];training={}
    for life in LIVES:
        for mode,source_mode in MODES.items():
            path=directory/f'models/life_{life}/{source_mode}.json';record=load(path)
            models[life][mode]=record['payload'];records[life,mode]=record
            model_refs.append(dict(life=life,mode=mode,source_mode=source_mode,source_ref=str(path),
                model_ref=f'models/life_{life}/{mode}.json'))
        for example in models[life]['TREE']['training_outcomes']:
            training[example['root_id']]=example
    old_roots=load(directory/'discovery_roots.json')
    fresh_roots=load(directory/'validation_roots.json')['roots']
    old_choices=load(directory/'frozen_choices.json')
    outcome_refs=[dict(life=row['life'],path=str(directory/row['outcomes_ref'])) for row in run['phases']['VALID']['lifecycles']]
    outcomes=[row for ref in outcome_refs for row in load(ref['path'])]
    counts.update(training_reference_root_records=len(training),fresh_reference_outcome_records=len(outcomes))
    index={(row['root_id'],row['suffix'],row['canonical_action']):row for row in outcomes}
    roots=[];issues=[]
    for cohort,rows in (('TRAIN',old_roots),('FRESH',fresh_roots)):
        for life in LIVES:
            ordered=sorted((row for row in rows if row['life']==life),key=lambda row:row['root_id'])
            for ordinal,root in enumerate(ordered):
                record=deepcopy(root);trials=[]
                if cohort=='TRAIN':
                    example=training[root['root_id']]
                    if any(example[key]!=root[key] for key in ('life','source_id','canonical_board','legal_actions','immediate_rewards')):
                        issues.append('training_reference_root_binding')
                    trials=deepcopy(example['suffix_trials'])
                else:
                    for suffix in range(4):
                        selected=[index[root['root_id'],suffix,action] for action in root['legal_actions']]
                        if len({row['seed'] for row in selected})!=1 or any(row['status'] not in ('WON','LOST') for row in selected):
                            issues.append('fresh_reference_binding')
                        trials.append(dict(suffix=suffix,seed=selected[0]['seed'],
                            action_components={row['canonical_action']:deepcopy(row['components']) for row in selected}))
                record.update(cohort=cohort,ordinal=ordinal,reference_trials=trials)
                roots.append(record);counts['reference_roots_assembled']+=1
    for cohort,total,source_count in (('TRAIN',384,12),('FRESH',256,8)):
        local=[root for root in roots if root['cohort']==cohort]
        if len(local)!=total:issues.append('fixed_root_count:'+cohort)
        for life in LIVES:
            groups=Counter(root['source_id'] for root in local if root['life']==life)
            if len(groups)!=source_count or set(groups.values())!={8}:issues.append('fixed_source_roots:'+cohort)
    cost_refs=deepcopy(capsule['cost_refs'])+[dict(path=str(directory/'analysis.json'),fields=['costs'])]
    cost_refs += [dict(path=str(ROOT/f'reports/v174_runtime_tmp/{kind}_checks.json'),fields=['attempts'])
        for kind in ('core','runner','analyzer','stage')]
    cost_refs += [dict(path=str(ROOT/'reports/v174_runtime_tmp/discovery_diagnosis.json'),
        fields=['costs','full_tree_training_effect.costs'])]
    source=dict(schema='acfqp.fixed_board_replication.v175.source',snapshots=deepcopy(capsule['snapshots']),
        inherited_run_ref=str(directory/'run.json'),inherited_analysis_ref=str(directory/'analysis.json'),
        inherited_stage_ref=str(ROOT/'reports/v174_runtime_tmp/stage_checks.json'),
        inherited_v174_environment_samples=audit['costs']['new_environment_samples'],cost_refs=cost_refs,
        this_stage_test_refs=[str(ROOT/f'reports/v175_runtime_tmp/{kind}_checks.json') for kind in ('core','runner','analyzer')])
    manifest=dict(model_refs=model_refs,train_roots_ref=str(directory/'discovery_roots.json'),
        fresh_roots_ref=str(directory/'validation_roots.json'),fresh_choices_ref=str(directory/'frozen_choices.json'),
        fresh_outcome_refs=outcome_refs,train_reference='audited TREE payload.training_outcomes',
        roots=dict(TRAIN=len(old_roots),FRESH=len(fresh_roots)),counts=dict(counts))
    return dict(source=source,manifest=manifest,roots=roots,models=models,model_records=records,
        old_fresh_choices=old_choices,complete=not issues,issues=issues)


def reference_choices_match(frozen,old_choices):
    index={(row['root_id'],row['mode']):row for row in old_choices}
    return all((row['root_id'],source_mode) in index and
        row['decisions'][mode]['canonical_action']==index[row['root_id'],source_mode]['canonical_action']
        for row in frozen['choices'] if row['cohort']=='FRESH' for mode,source_mode in MODES.items())


def branch_roster(roots,frozen,phase):
    cohort={'TRAIN_REPL':'TRAIN','FRESH_REPL':'FRESH'}[phase]
    offset={'TRAIN_REPL':10000000,'FRESH_REPL':20000000}[phase]
    index={(row['cohort'],row['root_id']):row for row in frozen['choices']}
    plans=[]
    for root in roots:
        if root['cohort']!=cohort:continue
        choice=index[cohort,root['root_id']]
        if not choice['changed']:continue
        actuals={row['canonical_action']:row['actual_action'] for row in root['actions']}
        for suffix in range(SUFFIXES):
            for mode in ('TREE','ONE'):
                action=choice['decisions'][mode]['canonical_action']
                plans.append(dict(branch_id=f'{phase}:{root["root_id"]}:{suffix}:{action}',phase=phase,
                    cohort=cohort,root_id=root['root_id'],life=root['life'],query='risk1',
                    source_id=root['source_id'],ordinal=root['ordinal'],suffix=suffix,
                    seed=BASE+offset+root['life']*1000000+root['ordinal']*1000+suffix,
                    canonical_action=action,actual_action=actuals[action]))
    return plans


def compact_outcome(row):
    keys=('branch_id','phase','cohort','root_id','life','query','source_id','ordinal',
        'suffix','seed','canonical_action','actual_action')
    return dict(**{key:deepcopy(row[key]) for key in keys},
        **{key:deepcopy(row['result'][key]) for key in ('score','steps','status','components','utility')},
        module=deepcopy(row['module']))


def physical_lifecycle(source,phase,inputs,directory):
    started=perf_counter();life=source['life'];folder=directory/phase.lower()/f'life_{life}'
    folder.mkdir(parents=True);bank,parents,leaves,records=parent.prior.old.prior.teachers(source,folder)
    roots,plans=inputs['roots'],inputs['rosters'][phase]
    index={root['root_id']:root for root in roots}
    retained={row['branch_id']:row for row in inputs.get('retained_branches',[])}
    outcomes=[];environment,policy,statuses=Counter(),Counter(),Counter();trace=folder/'branches.jsonl.gz'
    with gzip.open(trace,'wt') as stream:
        for plan in plans:
            if plan['life']!=life:continue
            if plan['branch_id'] in retained:
                row=deepcopy(retained[plan['branch_id']])
                if any(row[key]!=value for key,value in plan.items()):raise ValueError('retained branch differs from frozen plan')
                for query in bank:bank[query].counts.update(row['result']['policy_counts_by_query'][query])
            else:
                row=parent.prior.old.run_forced_branch(bank,index[plan['root_id']]['board'],plan['actual_action'],
                    life,plan['seed'],MAX_STEPS,.1)
                row.update(plan)
            append(stream,row);outcomes.append(compact_outcome(row))
            result=row['result'];environment.update(result['environment_counts'])
            policy.update(result['policy_counts']);statuses[result['status']]+=1
    parent.prior.old.prior.finish_teachers(bank,parents,leaves,records);save(folder/'outcomes.json',outcomes)
    result=dict(phase=phase,life=life,branch_trace=str(trace.relative_to(directory)),
        outcomes_ref=str((folder/'outcomes.json').relative_to(directory)),teacher_bank=records,
        physical_branches=len(outcomes),environment_counts=dict(environment),policy_counts=dict(policy),
        program_setup_counts={},statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',result);print(dict(event='games_completed',phase=phase,life=life,games=len(outcomes)),flush=True)
    return result


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_fixed_board_replication_v175')
    files={Path(__file__).resolve(),ROOT/'specs/FIXED_BOARD_REPLICATION_V175.md',
        ROOT/'reports/v175_runtime_tmp/run_stage.py',ROOT/'reports/v175_runtime_tmp/run_checks.py'}
    files.update((ROOT/'tests').glob('*fixed_board_replication*v175.py'))
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):files.add(path)
    for name in ('ntuple_kernel_v120','contextual_ntuple_v134','frozen_leaf_planning_v135'):
        files.add(ROOT/f'src/acfqp/science/controlled_predictive_{name}.cpp')
    for path in sorted(files):
        target=directory/'source_code'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
    return len(files)


def run(directory=OUTPUT):
    begun=perf_counter();directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    inputs=extract_source();save(directory/'source_capsule.json',inputs['source'])
    save(directory/'source_manifest.json',inputs['manifest']);save(directory/'roots.json',inputs['roots'])
    for row in inputs['manifest']['model_refs']:
        path=directory/row['model_ref'];path.parent.mkdir(parents=True,exist_ok=True)
        save(path,inputs['model_records'][row['life'],row['mode']])
    save(directory/'models_manifest.json',inputs['manifest']['model_refs'])
    save(directory/'frozen_inputs.json',dict(settings=settings()))
    data=dict(schema='acfqp.fixed_board_replication.v175.run',status='frozen',settings=settings(),
        phase_order=['INPUTS_FROZEN'],phases={},frozen_source_files=snapshot_code(directory),
        new_model_fits=0,new_parameter_updates=0,inherited_cost_refs=inputs['source']['cost_refs'])
    save(directory/'run.json',data)
    def stop(reason):
        data.update(status='HOLD',reason=reason,seconds=perf_counter()-begun);save(directory/'run.json',data)
        print(dict(status='HOLD',reason=reason),flush=True)
    if not inputs['complete']:stop('incomplete_fixed_reference');return
    started=perf_counter();frozen=freeze_selections(inputs['roots'],inputs['models'])
    data['selection_seconds']=perf_counter()-started;save(directory/'frozen_choices.json',frozen)
    if not frozen['complete']:stop('unsupported_fixed_policy');return
    if not reference_choices_match(frozen,inputs['old_fresh_choices']):stop('historical_fresh_choice_mismatch');return
    rosters={phase:branch_roster(inputs['roots'],frozen,phase) for phase in PHASES}
    save(directory/'branch_roster.json',rosters)
    data.update(selection_work=frozen['work'],physical_roster_counts={phase:len(rows) for phase,rows in rosters.items()},
        changed_roots={cohort:sum(row['changed'] for row in frozen['choices'] if row['cohort']==cohort) for cohort in COHORTS})
    data['phase_order'].append('POLICIES_FROZEN');save(directory/'run.json',data)
    physical_inputs=dict(roots=inputs['roots'],rosters=rosters);outcomes=[]
    for phase in PHASES:
        data['status']=phase.lower();save(directory/'run.json',data)
        data['phases'][phase]=parent.prior.old.prior.parallel_phase(physical_lifecycle,inputs['source']['snapshots'],
            phase,physical_inputs,directory)
        data['phase_order'].append(phase);save(directory/'run.json',data)
        rows=[row for lifecycle in data['phases'][phase]['lifecycles'] for row in read(directory/lifecycle['outcomes_ref'])]
        outcomes.extend(rows)
        if not parent.prior.old.complete_cohort(rows,rosters[phase]):stop('incomplete_'+phase);return
    started=perf_counter();summary=summarize_replication(frozen,outcomes)
    data['summary_seconds']=perf_counter()-started;save(directory/'summary.json',summary)
    if not summary['complete']:stop('incomplete_replication_binding');return
    data.update(status='complete',seconds=perf_counter()-begun);save(directory/'run.json',data)
    print(dict(status='complete',seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    run(parser.parse_args().output)
