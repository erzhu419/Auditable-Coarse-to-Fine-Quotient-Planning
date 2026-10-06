"""Learn consequence-based state partitions before any autonomous deployment."""
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import run_controlled_predictive_causal_quotient_v171 as old
from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from acfqp.science.controlled_predictive_program_consolidation_v161 import canonical_frame, INVERSE
from acfqp.science.controlled_predictive_causal_quotient_v171 import run_episode
from acfqp.science.controlled_predictive_consequence_partition_v172 import fit_partition, choose_action, ACTIONS
from acfqp.science.controlled_predictive_consequence_generation_v168 import _moments, _pool

SOURCE = ROOT/'reports/controlled_predictive_causal_quotient_v171'
OUTPUT = ROOT/'reports/controlled_predictive_consequence_partition_v172'
BASE, MAX_STEPS, LIVES = 17200000000, 8192, tuple(range(4))
MODEL_MODES = ('PART_EARLY', 'PART_LATE', 'COARSE_LATE', 'ONE_LATE')
MODES = MODEL_MODES+('H2',)
CONTRASTS = {'PART_LATE-COARSE_LATE':('PART_LATE','COARSE_LATE'),
             'PART_LATE-H2':('PART_LATE','H2'),
             'PART_LATE-ONE_LATE':('PART_LATE','ONE_LATE'),
             'PART_LATE-PART_EARLY':('PART_LATE','PART_EARLY'),
             'COARSE_LATE-H2':('COARSE_LATE','H2')}
METRICS = ('utility', 'reward', 'failure', 'success')
read, save, append, read_rows = old.read, old.save, old.append, old.read_rows


def settings():
    return dict(lifecycles=list(LIVES), queries=['risk1'], workers=4, version_base=BASE,
        max_steps=MAX_STEPS, p_four=.1, inherited_training_roots=128, inherited_training_branches=1880,
        source_games_per_history=8, roots_per_source_game=8, source_games_per_phase=32,
        new_training_root_cap=256, validation_root_cap=256, suffixes=4,
        training_branch_cap=4096, validation_branch_cap=4096, new_physical_game_cap=8256,
        maximum_environment_transitions=67633152, modes=list(MODES),
        learner='independent same-teacher joint-legal action contrast Laplacian least squares; full R/F/S',
        representation='canonical cell0..15 rank<=threshold0..9; globally greedy paired-vector loss',
        min_child_roots=8, min_child_sources=2, max_leaves=16, min_action_roots=4, tie_tolerance=1e-12,
        reward='exact deterministic first-swipe reward kept as numeric parameter; tail reward contrast learned',
        primary='PART_LATE-COARSE_LATE; progression additionally PART_LATE-H2; both CI95 lower>0',
        uncertainty='source-game clusters within each of four fixed teachers; root/suffix not independent games',
        validation='new SOURCE middle quantiles; remove exact TRAIN canonical boards before labels, no replacement',
        incomplete='any required incomplete cohort or source cluster with no unseen root -> HOLD',
        new_parameter_updates=0, autonomous_evaluation=False,
        frozen_policy='no outcome-dependent partition vocabulary/capacity/threshold/depth/seeds/extra acquisition')


def source_roster(phase):
    offset = {'TRAIN_SOURCE':10000000, 'VALID_SOURCE':30000000}[phase]
    return [dict(source_id=f'{phase}:{life}:risk1:{replica}', phase=phase, life=life,
                 query='risk1', replica=replica, mode='H2', seed=BASE+offset+life*1000000+replica)
            for life in LIVES for replica in range(8)]


def branch_roster(roots, phase):
    offset = {'TRAIN':20000000, 'VALID':40000000}[phase]
    return [dict(branch_id=f'{phase}:{r["root_id"]}:{suffix}:{a["canonical_action"]}', phase=phase,
                 root_id=r['root_id'], life=r['life'], query='risk1', replica=r['replica'], slot=r['slot'],
                 suffix=suffix, seed=BASE+offset+r['life']*1000000+r['replica']*100000+r['slot']*1000+suffix, **a)
            for r in roots for suffix in range(4) for a in r['actions']]


def extract_source():
    run, audit, capsule, frozen = (read(SOURCE/n) for n in ('run.json','analysis.json','source_capsule.json','frozen_inputs.json'))
    if not(run['status']=='complete' and audit['valid'] and audit['primary_complete']):
        raise ValueError('audited V171 completion required')
    refs = deepcopy(capsule['cost_refs'])+[dict(path=str(SOURCE/'analysis.json'),fields=['costs'])]
    refs += [dict(path=str(ROOT/f'reports/v171_runtime_tmp/{kind}_checks.json'),fields=['attempts'])
             for kind in ('core','runner','analyzer','stage')]
    traces = [dict(life=c['life'], path=str(SOURCE/c['outcomes_ref'])) for c in run['phases']['TRAIN']['lifecycles']]
    return dict(schema='acfqp.consequence_partition.v172.source', snapshots=deepcopy(capsule['snapshots']),
        inherited_run_ref=str(SOURCE/'run.json'), inherited_analysis_ref=str(SOURCE/'analysis.json'),
        inherited_frozen_inputs_ref=str(SOURCE/'frozen_inputs.json'), train_outcomes=traces,
        inherited_v171_environment_samples=audit['costs']['new_environment_samples'], cost_refs=refs,
        this_stage_test_refs=[str(ROOT/f'reports/v172_runtime_tmp/{k}_checks.json') for k in ('core','runner','analyzer')]), frozen


def add_reward_parameters(root):
    result = deepcopy(root); rewards, legal = {}, []
    for label in ACTIONS:
        _, score, changed = ground.swipe_board_v1(tuple(root['canonical_board']), ground.Swipe2048Action(label))
        if changed: legal.append(label); rewards[label] = score/2048.
    if legal != [a['canonical_action'] for a in root['actions']]:
        raise ValueError('frozen root legal actions disagree')
    result.update(legal_actions=legal, immediate_rewards=rewards)
    return result


def roots_from_source(row):
    if row['result']['status'] not in ('WON','LOST') or row['query']!='risk1':
        raise ValueError('complete H2 SOURCE required')
    n=len(row['actions']); roots=[]
    if n<9: raise ValueError('SOURCE cannot supply eight distinct middle quantiles')
    for slot in range(8):
        step=(slot+1)*n//9
        board=list(row['choices'][step-1]['afterstate']); board[row['spawned_cells'][step-1]]=row['spawned_ranks'][step-1]
        canonical, frame=canonical_frame(board); actions=[]; rewards={}
        for label in ACTIONS:
            _,score,legal=ground.swipe_board_v1(canonical,ground.Swipe2048Action(label))
            if legal:
                actual=ground.transform_action_v1(ground.Swipe2048Action(label),INVERSE[D4Transform(frame)]).value
                actions.append(dict(canonical_action=label,actual_action=actual)); rewards[label]=score/2048.
        teacher=ground.transform_action_v1(ground.Swipe2048Action(row['actions'][step]),D4Transform(frame)).value
        if teacher not in rewards: raise ValueError('SOURCE H2 action is not legal in root frame')
        roots.append(dict(root_id=f'{row["source_id"]}:{slot}', phase=row['phase'], life=row['life'],query='risk1',
            replica=row['replica'], slot=slot, source_id=row['source_id'], source_seed=row['seed'],
            source_step=step,source_steps=n,board=board,canonical_board=list(canonical),transform=frame,
            actions=actions,legal_actions=[a['canonical_action'] for a in actions],immediate_rewards=rewards,teacher_action=teacher,
            generation_counts=dict(board_transforms=8,ground_legality_swipes=4,action_transports=len(actions)+1)))
    return roots


def complete_source_cohort(outcomes, plans):
    index={r['source_id']:r for r in outcomes}
    return len(index)==len(outcomes)==len(plans) and set(index)=={p['source_id'] for p in plans} and all(
        all(index[p['source_id']][k]==v for k,v in p.items()) and index[p['source_id']]['status'] in ('WON','LOST') and
        index[p['source_id']]['components']==[index[p['source_id']]['score']/2048.,
            float(index[p['source_id']]['status']=='LOST'),float(index[p['source_id']]['status']=='WON')]
        for p in plans)


def assemble_examples(roots, roster, outcomes):
    issues=[]; counts=Counter(root_records_read=len(roots),branch_records_read=len(outcomes))
    if not old.complete_cohort(outcomes,roster): issues.append('incomplete_branch_cohort')
    if len({r['root_id'] for r in roots})!=len(roots): issues.append('duplicate_root')
    index={(r['root_id'],r['suffix'],r['canonical_action']):r for r in outcomes}; examples=[]
    if issues:return dict(examples=[],counts=dict(counts),complete=False,issues=issues)
    for root in roots:
        trials=[]
        for suffix in range(4):
            rows=[index.get((root['root_id'],suffix,action)) for action in root['legal_actions']]
            if any(r is None for r in rows) or len({r['seed'] for r in rows})!=1:
                issues.append('root_action_pairing');continue
            trials.append(dict(suffix=suffix,seed=rows[0]['seed'],
                action_components={r['canonical_action']:deepcopy(r['components']) for r in rows}))
            counts.update(paired_root_suffixes=1,component_label_reads=3*len(rows))
        examples.append(dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],
            canonical_board=deepcopy(root['canonical_board']),legal_actions=list(root['legal_actions']),
            immediate_rewards=deepcopy(root['immediate_rewards']),suffix_trials=trials))
    return dict(examples=examples,counts=dict(counts),complete=not issues,issues=sorted(set(issues)))


def compact_source(row):
    keys=('source_id','phase','life','query','replica','mode','seed')
    return dict(**{k:row[k] for k in keys},**{k:deepcopy(row['result'][k]) for k in
        ('score','steps','status','components','utility')},module=deepcopy(row['module']))


def physical_lifecycle(source, phase, roots, directory):
    started=perf_counter();life=source['life'];folder=directory/phase.lower()/f'life_{life}';folder.mkdir(parents=True)
    bank,parents,leaves,records=old.prior.teachers(source,folder)
    source_phase=phase.endswith('_SOURCE')
    plans=source_roster(phase) if source_phase else branch_roster(roots,phase)
    lookup={r['root_id']:r for r in roots}; outcomes=[]; environment,policy,statuses=Counter(),Counter(),Counter()
    trace=folder/'branches.jsonl.gz'
    with gzip.open(trace,'wt') as output:
        for plan in plans:
            if plan['life']!=life:continue
            if source_phase:row=run_episode(bank,[],life,'H2',plan['seed'],MAX_STEPS,.1)
            else:row=old.run_forced_branch(bank,lookup[plan['root_id']]['board'],plan['actual_action'],life,plan['seed'],MAX_STEPS,.1)
            row.update(plan);append(output,row);outcomes.append(compact_source(row) if source_phase else old.compact_outcome(row))
            result=row['result'];environment.update(result['environment_counts']);policy.update(result['policy_counts']);statuses[result['status']]+=1
    old.prior.finish_teachers(bank,parents,leaves,records);save(folder/'outcomes.json',outcomes)
    data=dict(phase=phase,life=life,branch_trace=str(trace.relative_to(directory)),outcomes_ref=str((folder/'outcomes.json').relative_to(directory)),
        teacher_bank=records,physical_branches=len(outcomes),environment_counts=dict(environment),policy_counts=dict(policy),
        program_setup_counts={},statuses=dict(statuses),seconds=perf_counter()-started)
    save(folder/'lifecycle.json',data);print(dict(event='games_completed',phase=phase,life=life,games=len(outcomes)),flush=True)
    return data


def fit_models(examples, directory, modes):
    fitted=[];started=perf_counter()
    for life in LIVES:
        for mode in modes:
            begun=perf_counter();payload=fit_partition(examples,life,mode)
            path=directory/'models'/f'life_{life}'/f'{mode}.json';path.parent.mkdir(parents=True,exist_ok=True)
            save(path,dict(payload=payload,fit_seconds=perf_counter()-begun))
            fitted.append(dict(life=life,mode=mode,model_ref=str(path.relative_to(directory))))
            print(dict(event='partition_fitted',life=life,mode=mode,leaves=len(payload['leaves'])),flush=True)
    return fitted, perf_counter()-started


def frozen_choices(roots, models):
    output=[];counts=Counter()
    for root in roots:
        actuals={a['canonical_action']:a['actual_action'] for a in root['actions']}
        for mode in MODES:
            if mode=='H2':
                decision=dict(canonical_action=root['teacher_action'],fallback=False,leaf=None,reason='source_teacher',
                              predicted_components={},predicted_pairs={},support={},work={})
            else:decision=choose_action(models[root['life'],mode],root)
            counts.update(decision['work'])
            output.append(dict(root_id=root['root_id'],life=root['life'],source_id=root['source_id'],mode=mode,
                canonical_action=decision['canonical_action'],actual_action=actuals[decision['canonical_action']],
                fallback=decision['fallback'],decision=decision))
    return output,dict(counts)


def summarize(outcomes, roots, choices):
    """Evaluate already frozen choices; average independent SOURCE game clusters."""
    plans=branch_roster(roots,'VALID');complete=old.complete_cohort(outcomes,plans)
    index={(r['root_id'],r['suffix'],r['canonical_action']):r for r in outcomes}
    chosen={(r['root_id'],r['mode']):r for r in choices}
    expected={(r['root_id'],mode) for r in roots for mode in MODES}
    complete &= len(chosen)==len(choices)==len(expected) and set(chosen)==expected
    complete &= all(chosen[r['root_id'],m]['canonical_action'] in r['legal_actions'] for r in roots for m in MODES) if complete else False
    groups=defaultdict(list)
    for root in roots:groups[root['life'],root['source_id']].append(root)
    comparisons=[];all_clusters=[]
    for contrast,(left,right) in CONTRASTS.items():
        clusters=[];histories=[]
        for life in LIVES:
            life_clusters=[]
            for (j,source_id),selected_roots in sorted(groups.items()):
                if j!=life:continue
                root_vectors=[]
                for root in selected_roots:
                    deltas=[]
                    for suffix in range(4):
                        if complete:
                            a=index[root['root_id'],suffix,chosen[root['root_id'],left]['canonical_action']]['components']
                            b=index[root['root_id'],suffix,chosen[root['root_id'],right]['canonical_action']]['components']
                            deltas.append([x-y for x,y in zip(a,b)])
                    root_vectors.append([sum(v[k] for v in deltas)/4 for k in range(3)] if complete else None)
                vector=[sum(v[k] for v in root_vectors)/len(root_vectors) for k in range(3)] if complete else None
                vals=[vector[0]-vector[1]+vector[2],*vector] if vector is not None else [None]*4
                item=dict(source_id=source_id,life=life,roots=len(selected_roots),suffixes=4,
                          metrics=dict(zip(METRICS,vals)))
                clusters.append(item);life_clusters.append(item)
            valid=complete and len(life_clusters)>=2
            histories.append(dict(life=life,source_clusters=len(life_clusters),metrics={m:_moments(
                [c['metrics'][m] if valid else None for c in life_clusters]) for m in METRICS}))
        metrics={m:_pool([h['metrics'][m] for h in histories],4) for m in METRICS}
        for stat in metrics.values():
            stat['conditional_source_se']=stat.pop('conditional_suffix_se')
            stat['conditional_source_ci95']=stat.pop('conditional_suffix_ci95')
        comparisons.append(dict(contrast=contrast,complete=complete,metrics=metrics,per_history=histories,clusters=clusters))
        all_clusters.extend(dict(contrast=contrast,**c) for c in clusters)
    diagnostics=[];predictions=[]
    for mode in MODES:
        selected=[chosen[r['root_id'],mode] for r in roots if (r['root_id'],mode) in chosen]
        diagnostics.append(dict(mode=mode,roots=len(selected),fallbacks=sum(r['fallback'] for r in selected),
            h2_agreements=sum(r['canonical_action']==chosen[r['root_id'],'H2']['canonical_action'] for r in selected if (r['root_id'],'H2') in chosen),
            action_counts=dict(Counter(r['canonical_action'] for r in selected))))
        losses=[];pair_trials=0
        for root in roots:
            row=chosen.get((root['root_id'],mode));decision={} if row is None else row.get('decision',{})
            if not complete or not decision.get('support',{}).get('complete') or len(root['legal_actions'])<2:continue
            errors=[]
            for a,b in combinations(root['legal_actions'],2):
                key=a+'|'+b;prediction=decision['predicted_pairs'].get(key)
                if prediction is None:continue
                for suffix in range(4):
                    left=index[root['root_id'],suffix,a]['components'];right=index[root['root_id'],suffix,b]['components']
                    errors.append([(left[k]-right[k]-prediction[k])**2 for k in range(3)]);pair_trials+=1
            if errors:losses.append([sum(v[k] for v in errors)/len(errors) for k in range(3)])
        predictions.append(dict(mode=mode,supported_roots=len(losses),pair_suffix_trials=pair_trials,
            mean_supported_root_pair_component_mse=[sum(v[k] for v in losses)/len(losses) for k in range(3)] if losses else None))
    primary=[c for c in comparisons if c['contrast'] in ('PART_LATE-COARSE_LATE','PART_LATE-H2')]
    evaluable=complete and all(c['metrics']['utility']['complete'] for c in primary)
    passed=sum(c['metrics']['utility']['conditional_source_ci95'][0]>0 for c in primary) if evaluable else 0
    progression=dict(status=('PASS' if passed==2 else 'FAIL') if evaluable else 'HOLD',passed=passed,required=2,
                     contrasts=[c['contrast'] for c in primary])
    return dict(schema='acfqp.consequence_partition.v172.summary',complete=complete,comparisons=comparisons,progression=progression,
        decision_diagnostics=diagnostics,prediction_diagnostics=predictions,clusters=all_clusters,
        scope='source-cluster conditional CI; pair MSE descriptive supported-root mean; forcedfirst then H2, no autonomous performance claim')


def snapshot_code(directory):
    importlib.import_module('scripts.analyze_controlled_predictive_consequence_partition_v172')
    files={Path(__file__).resolve(),ROOT/'specs/CONSEQUENCE_PARTITION_V172.md',ROOT/'reports/v172_runtime_tmp/run_stage.py'}
    files.update((ROOT/'tests').glob('*consequence_partition*v172.py'))
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
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    capsule,inherited=extract_source();save(directory/'source_capsule.json',capsule)
    inherited_roots=[add_reward_parameters(r) for r in inherited['roots']]
    inherited_outcomes=[r for ref in capsule['train_outcomes'] for r in read(ref['path'])]
    early=assemble_examples(inherited_roots,inherited['train_roster'],inherited_outcomes)
    frozen=dict(settings=settings(),inherited_roots=inherited_roots,
                source_rosters={p:source_roster(p) for p in ('TRAIN_SOURCE','VALID_SOURCE')})
    save(directory/'frozen_inputs.json',frozen)
    data=dict(schema='acfqp.consequence_partition.v172.run',status='frozen',settings=settings(),phases={},
        phase_order=['INPUTS_FROZEN'],frozen_source_files=snapshot_code(directory),new_parameter_updates=0,
        inherited_cost_refs=capsule['cost_refs'],inherited_assembly=early['counts'],
        inherited_reward_parameter_counts=dict(ground_legality_swipes=4*len(inherited_roots)))
    save(directory/'run.json',data)
    def stop(reason):
        data.update(status='HOLD',reason=reason,seconds=perf_counter()-started);save(directory/'run.json',data)
        print(dict(status='HOLD',reason=reason),flush=True)
    def acquire(phase,roots):
        data['status']=phase.lower();save(directory/'run.json',data)
        data['phases'][phase]=old.prior.parallel_phase(physical_lifecycle,capsule['snapshots'],phase,roots,directory)
        data['phase_order'].append(phase);save(directory/'run.json',data)
        return [r for lc in data['phases'][phase]['lifecycles'] for r in read(directory/lc['outcomes_ref'])]
    def source_roots_for(phase):
        return [root for lc in data['phases'][phase]['lifecycles'] for row in read_rows(directory/lc['branch_trace']) for root in roots_from_source(row)]
    if not early['complete']:stop('incomplete_inherited_training');return
    early_models,early_seconds=fit_models(early['examples'],directory,('PART_EARLY',))
    data['early_fit_seconds']=early_seconds;data['phase_order'].append('EARLY_MODELS_FROZEN');save(directory/'run.json',data)
    source_outcomes=acquire('TRAIN_SOURCE',[])
    if not complete_source_cohort(source_outcomes,source_roster('TRAIN_SOURCE')):stop('incomplete_training_source');return
    train_roots=source_roots_for('TRAIN_SOURCE');plans=branch_roster(train_roots,'TRAIN')
    save(directory/'training_roots.json',train_roots);save(directory/'training_roster.json',plans)
    outcomes=acquire('TRAIN',train_roots);late=assemble_examples(train_roots,plans,outcomes)
    if not late['complete']:stop('incomplete_training');return
    data['new_training_assembly']=late['counts'];data['training_root_counts']=dict(roots=len(train_roots),games=32)
    late_models,late_seconds=fit_models(early['examples']+late['examples'],directory,('PART_LATE','COARSE_LATE','ONE_LATE'))
    fitted=early_models+late_models;save(directory/'frozen_models.json',fitted)
    data['late_fit_seconds']=late_seconds;data['phase_order'].append('ALL_MODELS_FROZEN');save(directory/'run.json',data)
    source_outcomes=acquire('VALID_SOURCE',[])
    if not complete_source_cohort(source_outcomes,source_roster('VALID_SOURCE')):stop('incomplete_validation_source');return
    candidates=source_roots_for('VALID_SOURCE');seen={tuple(r['canonical_board']) for r in inherited_roots+train_roots}
    valid_roots=[r for r in candidates if tuple(r['canonical_board']) not in seen]
    excluded=[dict(root_id=r['root_id'],life=r['life'],source_id=r['source_id'],canonical_board=r['canonical_board'],
                   reason='canonical_board_already_in_TRAIN') for r in candidates if tuple(r['canonical_board']) in seen]
    save(directory/'validation_roots.json',dict(roots=valid_roots,excluded=excluded))
    if {r['source_id'] for r in valid_roots}!={p['source_id'] for p in source_roster('VALID_SOURCE')}:
        stop('validation_source_has_no_unseen_root');return
    models={(m['life'],m['mode']):read(directory/m['model_ref'])['payload'] for m in fitted}
    choices,choice_work=frozen_choices(valid_roots,models);save(directory/'frozen_choices.json',choices)
    plans=branch_roster(valid_roots,'VALID');save(directory/'validation_roster.json',plans)
    data['choice_work']=choice_work;data['validation_root_counts']=dict(candidates=len(candidates),unseen=len(valid_roots),excluded=len(excluded))
    data['phase_order'].append('VALID_CHOICES_FROZEN');save(directory/'run.json',data)
    outcomes=acquire('VALID',valid_roots)
    if not old.complete_cohort(outcomes,plans):stop('incomplete_validation');return
    save(directory/'summary.json',summarize(outcomes,valid_roots,choices))
    data.update(status='complete',seconds=perf_counter()-started);save(directory/'run.json',data)
    print(dict(status='complete',seconds=data['seconds']),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    run(parser.parse_args().output)
