"""Confirm fixed discovery partitions with independent SOURCE-game consequences."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import gzip
import importlib
from itertools import combinations
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import run_controlled_predictive_consequence_partition_v172 as prior
from acfqp.science.controlled_predictive_confirmed_partition_v173 import propose_partition, freeze_node_choices, confirm_and_prune
from acfqp.science.controlled_predictive_consequence_partition_v172 import fit_partition, choose_action, ACTIONS

SOURCE = ROOT/'reports/controlled_predictive_consequence_partition_v172'
OUTPUT = ROOT/'reports/controlled_predictive_confirmed_partition_v173'
BASE, MAX_STEPS, LIVES = 17300000000, 8192, tuple(range(4))
MODEL_MODES = ('PART_CONFIRMED','PART_UNPRUNED','ONE_LATE','COARSE_LATE')
MODES = MODEL_MODES+('H2',)
METRICS = ('utility','reward','failure','success')
CONTRASTS = {'PART_CONFIRMED-PART_UNPRUNED':('PART_CONFIRMED','PART_UNPRUNED'),
             'PART_CONFIRMED-H2':('PART_CONFIRMED','H2'),
             'PART_CONFIRMED-ONE_LATE':('PART_CONFIRMED','ONE_LATE'),
             'PART_CONFIRMED-COARSE_LATE':('PART_CONFIRMED','COARSE_LATE'),
             'PART_UNPRUNED-H2':('PART_UNPRUNED','H2')}
PHASE_ORDER = ['INPUTS_FROZEN','DISCOVERY_MODELS_FROZEN','CONFIRM_SOURCE','CONFIRM_CHOICES_FROZEN',
               'CONFIRM','ALL_MODELS_FROZEN','VALID_SOURCE','VALID_CHOICES_FROZEN','VALID']
read,save,append,read_rows = prior.read,prior.save,prior.append,prior.read_rows


def settings():
    return dict(lifecycles=list(LIVES),queries=['risk1'],workers=4,version_base=BASE,
        max_steps=MAX_STEPS,p_four=.1,discovery_roots=384,discovery_branches=5580,
        source_games_per_history=8,roots_per_source_game=8,suffixes=4,
        confirmation_root_cap=256,validation_root_cap=256,confirmation_branch_cap=4096,
        validation_branch_cap=4096,new_physical_game_cap=8256,maximum_environment_transitions=67633152,
        modes=list(MODES),min_child_roots=8,min_child_sources=2,max_leaves=16,min_action_roots=4,
        tie_tolerance=1e-12,confirmation_alpha=.05,min_confirmation_child_sources=2,
        min_changed_model_sources=2,confirmation='frozen direct-child vs collapsed-parent policies; all8 SOURCE clusters and zero outside node; Bonferroni global candidate K',
        primary='PART_CONFIRMED-PART_UNPRUNED; progression additionally PART_CONFIRMED-H2; both CI95 lower>0 and at least one retained split',
        incomplete='required incomplete cohort or SOURCE with no unseen root -> HOLD; no replacement',
        new_parameter_updates=0,autonomous_evaluation=False)


def source_roster(phase):
    offset={'CONFIRM_SOURCE':10000000,'VALID_SOURCE':30000000}[phase]
    return [dict(source_id=f'{phase}:{life}:risk1:{replica}',phase=phase,life=life,query='risk1',
        replica=replica,mode='H2',seed=BASE+offset+life*1000000+replica) for life in LIVES for replica in range(8)]


def branch_roster(roots,phase):
    offset={'CONFIRM':20000000,'VALID':40000000}[phase]
    return [dict(branch_id=f'{phase}:{root["root_id"]}:{suffix}:{action["canonical_action"]}',
        phase=phase,root_id=root['root_id'],life=root['life'],query='risk1',replica=root['replica'],
        slot=root['slot'],suffix=suffix,seed=BASE+offset+root['life']*1000000+root['replica']*100000+root['slot']*1000+suffix,
        **action) for root in roots for suffix in range(4) for action in root['actions']]


def extract_source(directory=SOURCE):
    directory=Path(directory)
    run,capsule,frozen,audit,equivalence=(read(directory/name) for name in
        ('run.json','source_capsule.json','frozen_inputs.json','analysis.json','equivalence_analysis.json'))
    if not (run['status']=='complete' and audit['training_complete'] and equivalence['observed_equivalence']):
        raise ValueError('completed V172 training and retained observable equivalence required')
    inherited_inputs=read(capsule['inherited_frozen_inputs_ref'])
    old_roots=deepcopy(frozen['inherited_roots'])
    old_outcomes=[row for ref in capsule['train_outcomes'] for row in read(ref['path'])]
    old_examples=prior.assemble_examples(old_roots,inherited_inputs['train_roster'],old_outcomes)
    new_roots=read(directory/'training_roots.json');new_roster=read(directory/'training_roster.json')
    refs=[dict(life=row['life'],path=str(directory/row['outcomes_ref'])) for row in run['phases']['TRAIN']['lifecycles']]
    new_outcomes=[row for ref in refs for row in read(ref['path'])]
    new_examples=prior.assemble_examples(new_roots,new_roster,new_outcomes)
    cost_refs=deepcopy(capsule['cost_refs'])+[dict(path=str(directory/'analysis.json'),fields=['costs']),
        dict(path=str(directory/'equivalence_analysis.json'),fields=['costs'])]
    cost_refs += [dict(path=str(ROOT/f'reports/v172_runtime_tmp/{kind}_checks.json'),fields=['attempts'])
                  for kind in ('core','runner','analyzer','equivalence','stage')]
    cost_refs += [dict(path=str(ROOT/'reports/v172_runtime_tmp/readonly_diagnosis.json'),fields=['costs']),
                  dict(path=str(ROOT/'reports/v172_runtime_tmp/numerical_maintenance.json'),fields=['scope'])]
    manifest=dict(inherited_frozen_inputs_ref=capsule['inherited_frozen_inputs_ref'],
        inherited_roots_ref=str(directory/'frozen_inputs.json'),old_train_outcomes=deepcopy(capsule['train_outcomes']),
        v172_training_roots_ref=str(directory/'training_roots.json'),v172_training_roster_ref=str(directory/'training_roster.json'),
        v172_train_outcomes=refs,old_roots=len(old_roots),new_roots=len(new_roots),
        old_outcomes=len(old_outcomes),new_outcomes=len(new_outcomes),
        old_assembly=old_examples['counts'],new_assembly=new_examples['counts'])
    source=dict(schema='acfqp.confirmed_partition.v173.source',snapshots=deepcopy(capsule['snapshots']),
        inherited_run_ref=str(directory/'run.json'),inherited_analysis_ref=str(directory/'analysis.json'),
        inherited_equivalence_ref=str(directory/'equivalence_analysis.json'),
        original_zero_sum_contract_failed=equivalence['original_zero_sum_contract_failed'],
        inherited_v172_environment_samples=audit['costs']['new_environment_samples'],cost_refs=cost_refs,
        this_stage_test_refs=[str(ROOT/f'reports/v173_runtime_tmp/{kind}_checks.json') for kind in ('core','runner','analyzer')])
    discovery=dict(roots=old_roots+new_roots,examples=old_examples['examples']+new_examples['examples'],
        complete=old_examples['complete'] and new_examples['complete'],manifest=manifest)
    return source,discovery


def fresh_roots(candidates,seen_roots,phase):
    seen={tuple(root['canonical_board']) for root in seen_roots}
    roots=[root for root in candidates if tuple(root['canonical_board']) not in seen]
    excluded=[dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],
        canonical_board=root['canonical_board'],reason='canonical_board_already_in_learning')
        for root in candidates if tuple(root['canonical_board']) in seen]
    complete={root['source_id'] for root in roots}=={plan['source_id'] for plan in source_roster(phase+'_SOURCE')}
    return dict(roots=roots,excluded=excluded,complete=complete)


def physical_lifecycle(source,phase,roots,directory):
    begun=perf_counter();life=source['life'];folder=directory/phase.lower()/f'life_{life}';folder.mkdir(parents=True)
    bank,parents,leaves,records=prior.old.prior.teachers(source,folder)
    is_source=phase.endswith('_SOURCE')
    plans=source_roster(phase) if is_source else branch_roster(roots,phase)
    index={root['root_id']:root for root in roots};outcomes=[];environment,policy,statuses=Counter(),Counter(),Counter()
    trace=folder/'branches.jsonl.gz'
    with gzip.open(trace,'wt') as stream:
        for plan in plans:
            if plan['life']!=life:continue
            if is_source:row=prior.run_episode(bank,[],life,'H2',plan['seed'],MAX_STEPS,.1)
            else:row=prior.old.run_forced_branch(bank,index[plan['root_id']]['board'],plan['actual_action'],life,plan['seed'],MAX_STEPS,.1)
            row.update(plan);append(stream,row)
            outcomes.append(prior.compact_source(row) if is_source else prior.old.compact_outcome(row))
            result=row['result'];environment.update(result['environment_counts']);policy.update(result['policy_counts']);statuses[result['status']]+=1
    prior.old.prior.finish_teachers(bank,parents,leaves,records);save(folder/'outcomes.json',outcomes)
    result=dict(phase=phase,life=life,branch_trace=str(trace.relative_to(directory)),
        outcomes_ref=str((folder/'outcomes.json').relative_to(directory)),teacher_bank=records,
        physical_branches=len(outcomes),environment_counts=dict(environment),policy_counts=dict(policy),
        program_setup_counts={},statuses=dict(statuses),seconds=perf_counter()-begun)
    save(folder/'lifecycle.json',result);print(dict(event='games_completed',phase=phase,life=life,games=len(outcomes)),flush=True)
    return result


def frozen_choices(roots,models):
    choices=[];work=Counter()
    for root in roots:
        actuals={row['canonical_action']:row['actual_action'] for row in root['actions']}
        for mode in MODES:
            decision=(dict(canonical_action=root['teacher_action'],fallback=False,leaf=None,reason='source_teacher',
                predicted_components={},predicted_pairs={},support={},work={}) if mode=='H2'
                else choose_action(models[root['life'],mode],root))
            work.update(decision['work'])
            choices.append(dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],mode=mode,
                canonical_action=decision['canonical_action'],actual_action=actuals[decision['canonical_action']],
                fallback=decision['fallback'],decision=decision))
    return choices,dict(work)


def summarize(outcomes,roots,choices,retained_splits):
    plans=branch_roster(roots,'VALID');index={(row['root_id'],row['suffix'],row['canonical_action']):row for row in outcomes}
    selected={(row['root_id'],row['mode']):row for row in choices};expected={(root['root_id'],mode) for root in roots for mode in MODES}
    complete=prior.old.complete_cohort(outcomes,plans) and len(selected)==len(choices)==len(expected) and set(selected)==expected
    complete=complete and all(selected[root['root_id'],mode]['canonical_action'] in root['legal_actions'] for root in roots for mode in MODES)
    groups=defaultdict(list)
    for root in roots:groups[root['life'],root['source_id']].append(root)
    comparisons=[];all_clusters=[]
    for label,(left,right) in CONTRASTS.items():
        clusters=[];histories=[]
        for life in LIVES:
            local=[]
            for (history,source),game_roots in sorted(groups.items()):
                if history!=life:continue
                vectors=[]
                for root in game_roots:
                    differences=[]
                    if complete:
                        for suffix in range(4):
                            a=index[root['root_id'],suffix,selected[root['root_id'],left]['canonical_action']]['components']
                            b=index[root['root_id'],suffix,selected[root['root_id'],right]['canonical_action']]['components']
                            differences.append([x-y for x,y in zip(a,b)])
                    vectors.append([sum(row[k] for row in differences)/4 for k in range(3)] if complete else None)
                vector=[sum(row[k] for row in vectors)/len(vectors) for k in range(3)] if complete else None
                item=dict(life=life,source_id=source,roots=len(game_roots),suffixes=4,
                    metrics=dict(zip(METRICS,[vector[0]-vector[1]+vector[2],*vector] if vector is not None else [None]*4)))
                local.append(item);clusters.append(item)
            histories.append(dict(life=life,source_clusters=len(local),metrics={metric:prior._moments(
                [item['metrics'][metric] if complete and len(local)==8 else None for item in local]) for metric in METRICS}))
        metrics={metric:prior._pool([history['metrics'][metric] for history in histories],4) for metric in METRICS}
        for stat in metrics.values():
            stat['conditional_source_se']=stat.pop('conditional_suffix_se');stat['conditional_source_ci95']=stat.pop('conditional_suffix_ci95')
        comparisons.append(dict(contrast=label,complete=complete,metrics=metrics,per_history=histories,clusters=clusters))
        all_clusters.extend(dict(contrast=label,**item) for item in clusters)
    decision_diagnostics=[];prediction_diagnostics=[]
    for mode in MODES:
        rows=[selected[root['root_id'],mode] for root in roots if (root['root_id'],mode) in selected]
        decision_diagnostics.append(dict(mode=mode,roots=len(rows),fallbacks=sum(row['fallback'] for row in rows),
            h2_agreements=sum(row['canonical_action']==selected[row['root_id'],'H2']['canonical_action'] for row in rows),
            action_counts=dict(Counter(row['canonical_action'] for row in rows))))
        losses=[];trials=0
        for root in roots:
            decision=selected.get((root['root_id'],mode),{}).get('decision',{})
            if not complete or not decision.get('support',{}).get('complete') or len(root['legal_actions'])<2:continue
            errors=[]
            for first,second in combinations(root['legal_actions'],2):
                prediction=decision['predicted_pairs'].get(first+'|'+second)
                if prediction is None:continue
                for suffix in range(4):
                    a=index[root['root_id'],suffix,first]['components'];b=index[root['root_id'],suffix,second]['components']
                    errors.append([(a[k]-b[k]-prediction[k])**2 for k in range(3)]);trials+=1
            if errors:losses.append([sum(row[k] for row in errors)/len(errors) for k in range(3)])
        prediction_diagnostics.append(dict(mode=mode,supported_roots=len(losses),pair_suffix_trials=trials,
            mean_supported_root_pair_component_mse=[sum(row[k] for row in losses)/len(losses) for k in range(3)] if losses else None))
    stats={row['contrast']:row['metrics']['utility'] for row in comparisons}
    labels=['PART_CONFIRMED-PART_UNPRUNED','PART_CONFIRMED-H2']
    evaluable=complete and all(stats[label]['complete'] for label in labels)
    passed=sum(stats[label]['conditional_source_ci95'][0]>0 for label in labels) if evaluable else 0
    progression=dict(status=('PASS' if passed==2 and retained_splits>0 else 'FAIL') if evaluable else 'HOLD',
        passed=passed,required=2,contrasts=labels,retained_splits=retained_splits,structure_eligible=retained_splits>0)
    return dict(schema='acfqp.confirmed_partition.v173.summary',complete=complete,comparisons=comparisons,
        clusters=all_clusters,progression=progression,decision_diagnostics=decision_diagnostics,
        prediction_diagnostics=prediction_diagnostics,scope='new SOURCE-cluster conditional CI; confirmed fixed first action then H2')


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_confirmed_partition_v173')
    files={Path(__file__).resolve(),ROOT/'specs/CONFIRMED_PARTITION_V173.md',
           ROOT/'reports/v173_runtime_tmp/run_stage.py',ROOT/'reports/v173_runtime_tmp/run_checks.py'}
    files.update((ROOT/'tests').glob('*confirmed_partition*v173.py'))
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
    capsule,discovery=extract_source();save(directory/'source_capsule.json',capsule)
    save(directory/'discovery_roots.json',discovery['roots']);save(directory/'discovery_manifest.json',discovery['manifest'])
    save(directory/'frozen_inputs.json',dict(settings=settings(),source_rosters={phase:source_roster(phase) for phase in ('CONFIRM_SOURCE','VALID_SOURCE')}))
    data=dict(schema='acfqp.confirmed_partition.v173.run',status='frozen',settings=settings(),phases={},phase_order=['INPUTS_FROZEN'],
        frozen_source_files=snapshot_code(directory),new_parameter_updates=0,inherited_cost_refs=capsule['cost_refs'])
    save(directory/'run.json',data)
    def stop(reason):
        data.update(status='HOLD',reason=reason,seconds=perf_counter()-begun);save(directory/'run.json',data)
        print(dict(status='HOLD',reason=reason),flush=True)
    def acquire(phase,roots):
        data['status']=phase.lower();save(directory/'run.json',data)
        data['phases'][phase]=prior.old.prior.parallel_phase(physical_lifecycle,capsule['snapshots'],phase,roots,directory)
        data['phase_order'].append(phase);save(directory/'run.json',data)
        return [row for lc in data['phases'][phase]['lifecycles'] for row in read(directory/lc['outcomes_ref'])]
    def source_roots_for(phase):
        return [root for lc in data['phases'][phase]['lifecycles'] for row in read_rows(directory/lc['branch_trace']) for root in prior.roots_from_source(row)]
    def save_model(payload,seconds,**extra):
        path=directory/'models'/f'life_{payload["life"]}'/f'{payload["mode"]}.json';path.parent.mkdir(parents=True,exist_ok=True)
        save(path,dict(payload=payload,fit_seconds=seconds,**extra))
        return dict(life=payload['life'],mode=payload['mode'],model_ref=str(path.relative_to(directory)))
    if not discovery['complete']:stop('incomplete_discovery');return
    proposals={};controls={};proposal_manifest=[];control_manifest=[];fit_counts=Counter();node_fit_counts=Counter()
    for life in LIVES:
        start=perf_counter();payload=propose_partition(discovery['examples'],life);seconds=perf_counter()-start
        proposals[life]=payload;proposal_manifest.append(save_model(payload,seconds))
        fit_counts.update(payload['fit_counts']);node_fit_counts.update(payload['node_fit_counts'])
        for mode in ('ONE_LATE','COARSE_LATE'):
            start=perf_counter();payload=fit_partition(discovery['examples'],life,mode);seconds=perf_counter()-start
            controls[life,mode]=payload;control_manifest.append(save_model(payload,seconds));fit_counts.update(payload['fit_counts'])
    candidate_count=sum(sum(node['kind']=='split' for node in payload['nodes']) for payload in proposals.values())
    save(directory/'proposal_models.json',proposal_manifest);save(directory/'control_models.json',control_manifest)
    data.update(total_candidates=candidate_count,discovery_fit_counts=dict(fit_counts),discovery_node_fit_counts=dict(node_fit_counts))
    data['phase_order'].append('DISCOVERY_MODELS_FROZEN');save(directory/'run.json',data)
    outcomes=acquire('CONFIRM_SOURCE',[])
    if not prior.complete_source_cohort(outcomes,source_roster('CONFIRM_SOURCE')):stop('incomplete_confirmation_source');return
    candidates=source_roots_for('CONFIRM_SOURCE');confirmation=fresh_roots(candidates,discovery['roots'],'CONFIRM')
    save(directory/'confirmation_roots.json',dict(roots=confirmation['roots'],excluded=confirmation['excluded']))
    if not confirmation['complete']:stop('confirmation_SOURCE_has_no_unseen_root');return
    roots=confirmation['roots'];choices,work=freeze_node_choices(proposals,roots)
    save(directory/'confirmation_node_choices.json',choices);save(directory/'confirmation_roster.json',branch_roster(roots,'CONFIRM'))
    data['confirmation_choice_work']=work;data['confirmation_root_counts']=dict(candidates=len(candidates),unseen=len(roots),excluded=len(confirmation['excluded']))
    data['phase_order'].append('CONFIRM_CHOICES_FROZEN');save(directory/'run.json',data)
    outcomes=acquire('CONFIRM',roots)
    if not prior.old.complete_cohort(outcomes,branch_roster(roots,'CONFIRM')):stop('incomplete_confirmation');return
    models={**controls,**{(life,'PART_UNPRUNED'):payload for life,payload in proposals.items()}}
    final_manifest=proposal_manifest+control_manifest;records=[];confirmation_seconds=0.
    for life in LIVES:
        start=perf_counter();payload,record=confirm_and_prune(proposals[life],roots,choices,outcomes,candidate_count);seconds=perf_counter()-start
        if not record['complete']:save(directory/'pruning_records.json',records+[record]);stop('incomplete_confirmation_vectors');return
        models[life,'PART_CONFIRMED']=payload;records.append(record);confirmation_seconds+=seconds
        final_manifest.append(save_model(payload,0.,confirmation_seconds=seconds))
    save(directory/'pruning_records.json',records);save(directory/'frozen_models.json',final_manifest)
    retained_splits=sum(sum(node['retained'] for node in record['nodes']) for record in records)
    data.update(confirmation_seconds=confirmation_seconds,retained_splits=retained_splits)
    data['phase_order'].append('ALL_MODELS_FROZEN');save(directory/'run.json',data)
    outcomes=acquire('VALID_SOURCE',[])
    if not prior.complete_source_cohort(outcomes,source_roster('VALID_SOURCE')):stop('incomplete_validation_source');return
    candidates=source_roots_for('VALID_SOURCE');validation=fresh_roots(candidates,discovery['roots']+roots,'VALID')
    save(directory/'validation_roots.json',dict(roots=validation['roots'],excluded=validation['excluded']))
    if not validation['complete']:stop('validation_SOURCE_has_no_unseen_root');return
    valid_roots=validation['roots'];choices,work=frozen_choices(valid_roots,models)
    save(directory/'frozen_choices.json',choices);save(directory/'validation_roster.json',branch_roster(valid_roots,'VALID'))
    data['choice_work']=work;data['validation_root_counts']=dict(candidates=len(candidates),unseen=len(valid_roots),excluded=len(validation['excluded']))
    data['phase_order'].append('VALID_CHOICES_FROZEN');save(directory/'run.json',data)
    outcomes=acquire('VALID',valid_roots)
    if not prior.old.complete_cohort(outcomes,branch_roster(valid_roots,'VALID')):stop('incomplete_validation');return
    save(directory/'summary.json',summarize(outcomes,valid_roots,choices,retained_splits))
    data.update(status='complete',seconds=perf_counter()-begun);save(directory/'run.json',data)
    print(dict(status='complete',seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    run(parser.parse_args().output)

