#!/usr/bin/env python3
"""Independent fixed-selection continuation audit without world or value replay."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
from statistics import mean

from verify_cumulative_critic_v289 import close, equal_tree, json_file, require
from verify_conditional_bellman_v294 import add_counts, check_contrast
from verify_natural_online_value_v286 import planning_counts, terminal

PHASES=('A','B','A_prime')
LAWS=(.1,.5,.1)
CANDIDATES=('SOURCE','BELLMAN','DISCOVERY')
PAIRS=(('DISCOVERY','SOURCE'),('DISCOVERY','BELLMAN'),('BELLMAN','SOURCE'))


def validation_seed(life,phase,anchor,replica):
    return 296600010000+life*1000000+phase*100000+anchor*1000+replica


def old_action_means(anchor):
    grouped=defaultdict(list)
    for row in anchor['discovery_reference']['rollouts']:grouped[row['action']].append(row['total_utility'])
    require(sorted(grouped)==anchor['legal_actions'] and all(len(v)==32 for v in grouped.values()),
        'complete old all-legal discovery sample inventory')
    return {action:mean(values) for action,values in grouped.items()}


def check_selection(anchor,old):
    for key in ('anchor_id','lifecycle','parent','phase','phase_index','anchor_index','episode','step','board_before_action','model_p_four','choices'):
        require(anchor[key]==old[key],'frozen old anchor/choices '+key)
    require(anchor['discovery_reference']==old['reference'],'old discovery labels changed')
    legal=sorted(old['choices']['FROZEN']['action_values']);require(anchor['legal_actions']==legal,'original legal actions')
    q=old_action_means(anchor);winner=min(legal,key=lambda a:(-q[a],a))
    expected=dict(source_action=old['choices']['FROZEN']['action'],
        bellman_action=old['choices']['BELLMAN_CONDITIONED']['action'],discovery_action=winner)
    for key,value in expected.items():require(anchor[key]==value,'candidate must be fixed from old discovery/choice '+key)
    require(anchor['validation_actions']==sorted(set(expected.values())),'only frozen candidate union is acquired')
    equal_tree(anchor['discovery_action_means'],q,'frozen old total-return means')
    return q


def check_validation(anchor):
    life,phase,slot=anchor['lifecycle'],anchor['phase_index'],anchor['anchor_index']
    ref=anchor['validation_reference'];p=anchor['model_p_four'];actions=anchor['validation_actions']
    require(ref['model_p_four']==p and ref['environment_p_four']==LAWS[phase],
        'SOURCE planner observed p and actual environment law remain separate')
    grouped=defaultdict(list)
    for row in ref['rollouts']:grouped[row['action']].append(row)
    require(sorted(grouped)==actions,'physical new samples only for frozen deduplicated candidates')
    q={};steps=wins=cutoffs=0
    for action in actions:
        rows=grouped[action]
        require(len(rows)==32 and [r['replica_index'] for r in rows]==list(range(32))
            and [r['seed'] for r in rows]==[validation_seed(life,phase,slot,i) for i in range(32)],
            'all thirty-two fresh paired replicas without validation reselection')
        first_score=anchor['choices']['FROZEN']['action_values'][action]['score']
        for r in rows:
            require(1<=r['steps']<=8192,'forced first action included in continuation steps')
            if r['status']=='CUTOFF':
                require(r['steps']==8192 and max(r['final_board'])<11,'actual retained continuation cutoff');bonus=0.
            else:terminal(r['final_board'],r['status']);bonus=4. if r['status']=='WON' else -4.
            require(r['first_score']==first_score and r['total_utility']==r['total_score']/2048.+bonus
                and r['suffix_utility']==(r['total_score']-first_score)/2048.+bonus,
                'total first-action utility versus after-first-action suffix')
            require(r['steps']!=1 or r['total_score']==first_score,'one-step continuation has no later rewards')
            steps+=r['steps'];wins+=r['status']=='WON';cutoffs+=r['status']=='CUTOFF'
        q[action]=mean(r['total_utility'] for r in rows)
    n=len(ref['rollouts']);c=Counter(ref['counts']['rollout']);calls=steps-n
    expected=dict(sampled_transitions=steps,environment_random_draws=2*steps,
        ground_explicit_swipe_calls=steps,ground_swipe_calls=steps+4*(steps-wins),
        ground_state_status_calls=steps,ground_status_internal_swipe_calls=4*(steps-wins))
    require(Counter(ref['counts']['environment'])==Counter(expected),'all actual continuation spawn/draw/status costs')
    require(c['completed_rollouts']==c['rng_streams_started']==n and c['replica_streams']==32
        and c['evaluate_calls']==1 and c['continuation_choose_calls']==calls,
        'one forced first action per physical rollout and paired RNG streams')
    planning_counts(dict(ref['counts']['planning'],choose_calls=calls),calls,2)
    return dict(action_means=q,rollouts=n,steps=steps,cutoffs=cutoffs)


def recompute_records(lives):
    records=[];totals=Counter();inventory=Counter();same=Counter()
    names=[left+'_minus_'+right for left,right in PAIRS]
    fields=('discovery_values','validation_values','discovery_contrasts','validation_contrasts','discovery_validation_drop')
    for life in lives:
        lid=life['lifecycle'];phases={}
        for index,phase in enumerate(PHASES):
            anchors=life['phases'][phase]['anchors'];require(len(anchors)==3,'all fixed natural time anchors remain')
            rows=[]
            for slot,anchor in enumerate(anchors):
                require(anchor['anchor_id']==f'L{lid:02d}-{phase}-Q{slot}' and anchor['lifecycle']==lid
                    and anchor['parent']==lid%4 and anchor['phase']==phase and anchor['phase_index']==index
                    and anchor['anchor_index']==slot,'complete original anchor identities and order')
                old=old_action_means(anchor);new=check_validation(anchor)
                actions=dict(SOURCE=anchor['source_action'],BELLMAN=anchor['bellman_action'],DISCOVERY=anchor['discovery_action'])
                old_values={m:old[a] for m,a in actions.items()};new_values={m:new['action_means'][a] for m,a in actions.items()}
                old_deltas={name:old_values[left]-old_values[right] for name,(left,right) in zip(names,PAIRS)}
                new_deltas={name:new_values[left]-new_values[right] for name,(left,right) in zip(names,PAIRS)}
                rows.append(dict(anchor_id=anchor['anchor_id'],actions=actions,discovery_action_means=old,
                    validation_action_means=new['action_means'],discovery_values=old_values,validation_values=new_values,
                    discovery_contrasts=old_deltas,validation_contrasts=new_deltas,
                    discovery_validation_drop={name:old_deltas[name]-new_deltas[name] for name in names}))
                totals['anchors']+=1;totals['validation_physical_rollouts']+=new['rollouts']
                totals['validation_cutoffs']+=new['cutoffs'];totals['validation_steps']+=new['steps']
                totals['discovery_physical_rollouts']+=len(anchor['discovery_reference']['rollouts'])
                totals['discovery_cutoffs']+=sum(r['status']=='CUTOFF' for r in anchor['discovery_reference']['rollouts'])
                inventory[len(anchor['validation_actions'])]+=1
                for name,(left,right) in zip(names,PAIRS):same[name]+=actions[left]==actions[right]
            phases[phase]=dict(anchors=rows,**{field:{key:mean(r[field][key] for r in rows) for key in rows[0][field]} for field in fields})
        records.append(dict(lifecycle=lid,parent=lid%4,phases=phases,
            **{field:{key:mean(p[field][key] for p in phases.values()) for key in phases['A'][field]} for field in fields}))
    totals['validation_logical_candidate_references']=totals['anchors']*3*32
    totals['paired_replica_seed_streams']=totals['anchors']*32
    return records,totals,inventory,same


def check_summary(summary,records,totals,inventory,same):
    equal_tree(summary['by_lifecycle'],records,'all replica/anchor/phase/life equal-weight results')
    for left,right in PAIRS:
        name=left+'_minus_'+right
        for saved,field,signed in (('paired_contrasts','validation_contrasts',False),
            ('discovery_contrasts','discovery_contrasts',False),('discovery_validation_drop','discovery_validation_drop',True)):
            check_contrast(summary[saved][name],[r[field][name] for r in records],signed)
        for phase in PHASES:
            check_contrast(summary['phase_contrasts'][phase][name],[r['phases'][phase]['validation_contrasts'][name] for r in records])
            check_contrast(summary['phase_discovery_validation_drop'][phase][name],
                [r['phases'][phase]['discovery_validation_drop'][name] for r in records],True)
    expected={m:dict(discovery=mean(r['discovery_values'][m] for r in records),
        validation=mean(r['validation_values'][m] for r in records)) for m in CANDIDATES}
    equal_tree(summary['method_values'],expected,'fixed candidate utilities independent of validation maximum')
    expected={p:{m:dict(discovery=mean(r['phases'][p]['discovery_values'][m] for r in records),
        validation=mean(r['phases'][p]['validation_values'][m] for r in records)) for m in CANDIDATES} for p in PHASES}
    equal_tree(summary['phase_method_values'],expected,'stage/whole-life utility weighting')
    for key in ('anchors','discovery_physical_rollouts','validation_physical_rollouts','discovery_cutoffs',
        'validation_cutoffs','validation_logical_candidate_references','paired_replica_seed_streams'):
        require(summary[key]==totals[key],'actual physical or logical coverage '+key)
    require(summary['validation_unique_action_inventory']=={str(n):inventory[n] for n in (1,2,3)}
        and summary['same_action_anchors']==dict(same),'all shared candidate actions have one physical reference')
    complete=totals['discovery_cutoffs']+totals['validation_cutoffs']==0
    require(summary['complete_continuations']==complete and summary['observed_anchor_signal_supported']==
        (complete and summary['paired_contrasts']['DISCOVERY_minus_SOURCE']['ci95'][0]>0.),
        'old discovery or secondary comparisons substituted for independent fixed-action signal')
    require(summary['primary_contrast']=='DISCOVERY_minus_SOURCE' and summary['bootstrap_seed']==29600001
        and summary['bootstrap_draws']==20000 and summary['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS'
        and summary['estimator']=='EQUAL_REPLICAS_THEN_ANCHORS_THEN_PHASES_THEN_LIFECYCLES',
        'whole-life fixed-parent statistical scope')


def old_selection_costs(old):
    a=old['accounting']
    return dict(economic_source_and_training_input_raw_tiles=a['economic_training_raw_tiles_per_arm']['FROZEN'],
        inherited_source_and_input_costs=a['inherited_costs_per_arm']['FROZEN'],
        carrier_raw_tiles=a['reused_carrier_raw_tiles'],carrier_counts=a['reused_carrier_counts'],
        warmup_raw_tiles=a['reused_warmup_raw_tiles'],warmup_environment_counts=a['reused_warmup_environment_counts'],
        warmup_direct_counts=a['reused_warmup_direct_counts'],warmup_memory_counts=a['reused_warmup_memory_counts'],
        discovery_rollouts=a['physical_ranking_rollouts'],discovery_counts=a['ranking_reference_counts'],
        discovery_cpu_seconds=a['ranking_reference_cpu_seconds'],
        selection_choice_counts={m:a['ranking_choice_counts_per_arm'][arm] for m,arm in
            (('SOURCE','FROZEN'),('BELLMAN','BELLMAN_CONDITIONED'))},
        bellman_fit_counts=a['fit_counts_per_arm']['BELLMAN_CONDITIONED'],
        bellman_fit_cpu_seconds=a['fit_cpu_seconds_per_arm']['BELLMAN_CONDITIONED'],
        bellman_training_samples=a['processed_training_samples_per_arm']['BELLMAN_CONDITIONED'])


def check_frozen_selection(selection,old,settings):
    require(selection['schema']=='acfqp.long_horizon_advantage_selection.v296'
        and selection['source_summary']==settings['source_summary']
        and selection['source_provenance']==old['source_provenance'],'same previously audited source and old selection evidence')
    lives=selection['by_lifecycle'];require([r['lifecycle'] for r in lives]==list(range(16))
        and all(r['parent']==r['lifecycle']%4 for r in lives),'all original fixed-source lives selected')
    prior={r['lifecycle']:r for r in old['by_lifecycle']};union=Counter();n=0
    for life in lives:
        for index,phase in enumerate(PHASES):
            anchors=life['phases'][phase]['anchors'];old_anchors=prior[life['lifecycle']]['ranking'][phase]['anchors']
            require(len(anchors)==len(old_anchors)==3,'no favorable-anchor or future-utility selection')
            for slot,(anchor,previous) in enumerate(zip(anchors,old_anchors)):
                require(anchor['anchor_id']==f'L{life["lifecycle"]:02d}-{phase}-Q{slot}'
                    and anchor['phase_index']==index and anchor['anchor_index']==slot,'original anchor order')
                check_selection(anchor,previous);n+=1;union[len(anchor['validation_actions'])]+=1
    require(selection['anchor_count']==n==144 and selection['union_size_counts']==dict((str(k),union[k]) for k in (1,2,3))
        =={'1':58,'2':80,'3':6} and selection['physical_validation_rollouts']==32*sum(k*v for k,v in union.items())==7552
        and selection['paired_replica_seedstreams']==n*32==4608 and selection['logical_candidate_references']==n*3*32==13824,
        'frozen full candidate union and deduplicated physical budget')
    equal_tree(selection['reused_selection_costs'],old_selection_costs(old),'old source/input/fit/discovery acquisition is not free')


def read_canonical(d,selection):
    lives={r['lifecycle']:r for r in d['by_lifecycle']};frozen={r['lifecycle']:r for r in selection['by_lifecycle']}
    require(sorted(lives)==list(range(16)) and all(r['parent']==r['lifecycle']%4 for r in lives.values()),
        'complete new validation lives')
    seen=set();n=0
    for parent in d['parent_receipts']:
        pid=parent['parent'];require(parent['lifecycle_ids']==list(range(pid,16,4)),'actual parent/life roster')
        require(parent['source_updates_before']==parent['source_updates_after']==0
            and parent['source_setup']['new_leaf_updates']==0,'new continuation cannot update SOURCE')
        trace=Path(parent['trace_file']);require(trace.stat().st_size==parent['trace_bytes'],'actual compressed canonical trace storage')
        with gzip.open(trace,'rt') as stream:
            for line in stream:
                row=json.loads(line);n+=1;lid=row['lifecycle'];phase=row['phase'];slot=row['anchor_index'];key=(lid,phase,slot)
                require(row['kind']=='VALIDATION_ANCHOR' and row['parent']==lid%4==pid
                    and phase in PHASES and 0<=slot<3 and key not in seen,'one new canonical receipt per original anchor')
                seen.add(key);anchor={k:v for k,v in row.items() if k!='kind'}
                require(anchor==lives[lid]['phases'][phase]['anchors'][slot],'summary validation differs from physical canonical receipt')
                require({k:v for k,v in anchor.items() if k!='validation_reference'}==frozen[lid]['phases'][phase]['anchors'][slot],
                    'new observations altered an old-data selected candidate or anchor')
    require(n==len(seen)==144,'complete canonical anchors including shared and negative cases')
    return n


def check_accounting(d,selection,old,totals):
    lives=d['by_lifecycle'];parents=d['parent_receipts'];a=d['accounting']
    refs=[r['validation_reference'] for life in lives for p in PHASES for r in life['phases'][p]['anchors']]
    counts={k:add_counts(r['counts'][k] for r in refs) for k in ('environment','planning','rollout')}
    expected=dict(new_training_environment_raw_tiles=0,new_value_updates=0,physical_validation_anchors=144,
        physical_validation_rollouts=totals['validation_physical_rollouts'],paired_replica_seedstreams=4608,
        logical_candidate_references=13824,new_environment_raw_tiles=totals['validation_steps'],
        new_environment_random_draws=2*totals['validation_steps'],validation_counts=counts,
        validation_cutoffs=totals['validation_cutoffs'],validation_cpu_seconds=sum(r['cpu_seconds'] for r in refs),
        validation_seconds=sum(r['seconds'] for r in refs),reused_selection_costs=old_selection_costs(old),
        new_source_setup_counts=add_counts(p['source_setup']['setup_counts'] for p in parents),
        new_source_setup_cpu_seconds=sum(p['source_setup']['cpu_seconds'] for p in parents),
        native_continuation_setup_counts=add_counts(p['native_continuation_setup']['counts'] for p in parents),
        native_continuation_setup_seconds=sum(p['native_continuation_setup']['seconds'] for p in parents),
        worker_cpu_seconds=sum(p['cpu_seconds'] for p in parents),compiler_cpu_seconds=sum(p['compiler_cpu_seconds'] for p in parents),
        canonical_trace_bytes=sum(p['trace_bytes'] for p in parents))
    require(totals['validation_physical_rollouts']==7552 and totals['discovery_physical_rollouts']==16096
        and counts['environment']['sampled_transitions']==totals['validation_steps'],
        'same old selection inventory and actual new physical observations')
    for key,value in expected.items():equal_tree(a[key],value,'all actual new and reused cost receipts '+key)
    require(a['reused_selection_costs']==selection['reused_selection_costs']
        and a['reused_selection_costs']['discovery_counts']['environment']['sampled_transitions']==7064751,
        'full old discovery sample cost retained')
    for p in parents:
        setup=p['source_setup'];require(setup['checkpoint_loads']==1 and setup['leaf_weight_bytes']==8*4*11**6
            and setup['cpu_seconds']>=0 and setup['wall_seconds']>=0,'source load/setup actual scope')
    require(a['coordinator_cpu_seconds']>=0 and a['wall_seconds']>0,'actual run CPU/wall scope')


def audit(directory):
    directory=Path(directory);d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen configuration changed')
    expected=dict(lifecycles=list(range(16)),parents=4,phases=[['A',.1],['B',.5],['A_prime',.1]],
        candidates=list(CANDIDATES),replicas=32,max_steps=8192,seed_validation=296600010000,
        bootstrap_seed=29600001,bootstrap_draws=20000,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),
        primary='DISCOVERY_minus_SOURCE',selection='OLD_ALL_LEGAL_TOTAL_UTILITY_MEAN_LEXICAL_TIE',
        validation='FROZEN_THREE_ACTION_UNION_SHARED_REPLICA_SEEDS',
        continuation='READONLY_SOURCE_H2_ANCHOR_OBSERVED_P_GROUND_PHASE_P')
    for key,value in expected.items():require(settings[key]==value,'registered '+key)
    path=Path(settings['source_summary']);old=json_file(path)
    require(json_file(path.with_name('audit.json'))['independent_valid'],'previous V294 fixed-anchor evidence is valid')
    require(d['schema']=='acfqp.long_horizon_advantage.v296' and d['status']=='EXPERIMENT_COMPLETE'
        and d['scientific_gate']=='NOT_A_FORMAL_GATE' and d['source_provenance']==old['source_provenance'],
        'frozen source and exploratory one-action evidence scope')
    selection_path=directory/'selection.json';require(d['selection_file']==str(selection_path.resolve()),'actual frozen selection artifact')
    selection=json_file(selection_path);check_frozen_selection(selection,old,settings);rows=read_canonical(d,selection)
    records,totals,inventory,same=recompute_records(d['by_lifecycle']);check_summary(d['summary'],records,totals,inventory,same)
    check_accounting(d,selection,old,totals);s=d['summary'];a=d['accounting']
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,canonical_rows=rows,anchors=144,
        discovery_physical_rollouts=totals['discovery_physical_rollouts'],discovery_raw_tiles=7064751,
        validation_physical_rollouts=totals['validation_physical_rollouts'],paired_replica_seedstreams=4608,
        logical_candidate_references=13824,validation_unique_action_inventory=s['validation_unique_action_inventory'],
        new_environment_raw_tiles=a['new_environment_raw_tiles'],new_environment_random_draws=a['new_environment_random_draws'],
        new_training_environment_raw_tiles=0,new_value_updates=0,validation_cutoffs=totals['validation_cutoffs'],
        observed_anchor_signal_supported=s['observed_anchor_signal_supported'],primary=s['paired_contrasts']['DISCOVERY_minus_SOURCE'],
        canonical_trace_bytes=a['canonical_trace_bytes'],selection_json_bytes=selection_path.stat().st_size,
        summary_json_bytes=(directory/'summary.json').stat().st_size,errors=[],
        limitations='Independent old-data choice, canonical continuation terminal/total-utility, signed-input and cost audit. '
            'No old carrier/world or weight replay, new training, value fitting, or 20000-draw bootstrap regeneration. '
            'Observed-p SOURCE-H2 continuation is fixed after the forced first action. Positive anchor evidence does not '
            'establish learnability, repeated-policy net gain, optimal Q, or the cause of old Bellman failures. Four source parents are fixed.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()
