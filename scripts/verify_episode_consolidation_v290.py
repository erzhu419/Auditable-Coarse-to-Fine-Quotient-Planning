#!/usr/bin/env python3
"""Independent compact receipt audit for the frozen episodic-update comparison."""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean

from verify_cumulative_critic_v289 import (
    check_dataset, close, equal_tree, factual_targets, json_file,
    read_retained_scores, require, sum_counts,
)
from verify_natural_online_value_v286 import terminal, planning_counts
from verify_retained_critic_v287 import check_holdout

ARMS=('FROZEN','EPISODIC_MC','NORMALIZED_SEQUENTIAL_MC','EPISODE_MEAN_MC')
PAIRS=(('EPISODE_MEAN_MC','FROZEN'),('NORMALIZED_SEQUENTIAL_MC','FROZEN'),
    ('EPISODIC_MC','FROZEN'),('EPISODE_MEAN_MC','NORMALIZED_SEQUENTIAL_MC'),
    ('EPISODE_MEAN_MC','EPISODIC_MC'))


def episode_math(weights,features,targets,method,offset=0.,alpha=.0025):
    """Small independent finite fixture, not a replay of experimental weights."""
    require(method in ('NORMALIZED_SEQUENTIAL_MC','EPISODE_MEAN_MC'),'episodic normalization method')
    multiplicities=[Counter(row) for row in features]
    exposure=sum(multiplicities,Counter())
    current=dict(weights);pending=Counter();examples=[]
    for counts,target in zip(multiplicities,targets):
        source=current if method=='NORMALIZED_SEQUENTIAL_MC' else weights
        prediction=sum(count*source[address] for address,count in counts.items())+offset
        error=target-prediction
        examples.append(dict(prediction=prediction,error=error))
        for address,count in counts.items():
            delta=alpha*count*error/exposure[address]
            if method=='NORMALIZED_SEQUENTIAL_MC':current[address]+=delta
            else:pending[address]+=count*error
    if method=='EPISODE_MEAN_MC':
        for address,total in pending.items():current[address]+=alpha*total/exposure[address]
    return dict(weights=current,exposure=dict(exposure),examples=examples,
        sample_addresses=sum(len(c) for c in multiplicities),episode_addresses=len(exposure))


def evaluation_seed(life,episode):
    return 290500000000+life*1000000+episode


def check_contrast(saved,values,direction=None):
    require(close(saved['mean'],mean(values)),'signed paired mean')
    equal_tree(saved['lifecycle_deltas'],{str(i):value for i,value in enumerate(values)},'signed lifecycle deltas')
    groups=[values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'],{str(p):mean(g) for p,g in enumerate(groups)},'fixed parent means')
    require(saved['interval_scope']=='CONDITIONAL_ON_FOUR_FROZEN_PARENTS','bootstrap source scope')
    low,high=saved['ci95']
    require(mean(min(g) for g in groups)-1e-10<=low<=high<=mean(max(g) for g in groups)+1e-10,
        'CI possible conditional resampling range')
    if direction:
        losses=values if direction=='lower_is_better' else [-v for v in values]
        require(saved['improved_equal_worse']==[sum(v<0 for v in losses),sum(v==0 for v in losses),sum(v>0 for v in losses)]
            and saved['adverse_lifecycles']==[i for i,v in enumerate(losses) if v>0],'paired quality/adverse direction')
    else:require('improved_equal_worse' not in saved and 'adverse_lifecycles' not in saved,'signed bias assigned quality')
    if direction!='higher_is_better':require(saved['positive_equal_negative']==[
        sum(v>0 for v in values),sum(v==0 for v in values),sum(v<0 for v in values)],'literal signed counts')


def check_evaluation(games,life,counts):
    require(len(games)==16 and [g['seed'] for g in games]==[evaluation_seed(life,i) for i in range(16)],
        'registered fresh paired evaluation seeds')
    for game in games:
        require(1<=game['steps']<=8192,'new evaluation cap')
        if game['status']=='CUTOFF':
            require(game['steps']==8192 and max(game['final_board'])<11,'premature cutoff or goal cutoff')
            bonus=0.
        else:
            terminal(game['final_board'],game['status']);bonus=4. if game['status']=='WON' else -4.
        require(game['utility']==game['score']/2048.+bonus,'new complete-game utility')
    steps,wins=sum(g['steps'] for g in games),sum(g['status']=='WON' for g in games)
    env=dict(sampled_transitions=steps,post_action_spawns=steps,initial_spawns=32,
        raw_tile_productions=steps+32,environment_random_draws=2*(steps+32),ground_explicit_swipe_calls=steps,
        ground_state_status_calls=steps+16,ground_status_internal_swipe_calls=4*(steps+16-wins),
        ground_swipe_calls=steps+4*(steps+16-wins))
    require(Counter(counts['environment'])==Counter(env),'new evaluation environment counts including initial spawns')
    planning_counts(counts['planning'],steps)
    return dict(games=16,mean_game_utility=mean(g['utility'] for g in games),wins=wins,
        losses=sum(g['status']=='LOST' for g in games),cutoffs=sum(g['status']=='CUTOFF' for g in games),steps=steps)


def check_normalized_fit(fit,games,dataset,scores,method):
    samples=sum(g['steps']-(g['status']=='WON') for g in games)
    steps=sum(g['steps'] for g in games);wins=sum(g['status']=='WON' for g in games)
    learning=Counter(fit['learning_counts']);work=Counter(fit['consolidation_counts']);targets=Counter(fit['target_counts'])
    require(fit['method']==method and fit['alpha']==.0025 and fit['fitted_games']==len(games)
        and fit['fitted_steps']==dataset['fit_step_end']==steps and fit['trained_afterstates']==samples,
        'normalized complete-game sample/fit inventory')
    require(learning['td_updates']==learning['value_predictions']==samples
        and learning['table_lookups']==learning['table_update_occurrences']==32*samples,
        'normalized sample/prediction/occurrence counter semantics')
    target_expected=dict(goal_checks=steps,suffix_games=len(games),suffix_target_assignments=steps,
        suffix_reward_additions=steps,raw_target_subtractions=samples,skipped_winning_afterstates=wins)
    require(Counter({k:v for k,v in targets.items() if k!='target_buffer_doubles_peak'})==Counter(target_expected),
        'normalized factual MC target work')
    require(targets['target_buffer_doubles_peak']>=max(g['steps'] for g in games),'normalized target buffer peak')
    expected=dict(games_processed=len(games),feature_extractions=samples,feature_occurrences=32*samples,
        feature_digit_reads=192*samples,feature_address_multiply_adds=192*samples,
        game_sort_calls=len(games),game_sort_items=32*samples,address_occurrence_count_visits=32*samples,
        address_occurrence_count_comparisons=32*samples-len(games),sample_sort_calls=samples,sample_sort_items=32*samples)
    require(all(work[k]==v for k,v in expected.items()),'normalized all-occurrence address preparation')
    sample_unique,game_unique=work['sample_unique_addresses'],work['game_unique_addresses']
    require(4*samples<=sample_unique<=32*samples and 4*len(games)<=game_unique<=sample_unique
        and work['address_denominator_searches']==sample_unique,'real address multiplicity/denominator searches')
    writes=game_unique if method=='EPISODE_MEAN_MC' else sample_unique
    require(learning['table_updates']==work['parameter_write_events']==writes
        and work['normalization_divisions']==writes,'actual normalized parameter writes')
    if method=='EPISODE_MEAN_MC':
        require(work['game_parameter_commits']==len(games) and work['sample_parameter_commits']==0
            and work['weighted_residual_multiplications']==work['weighted_residual_accumulations']==sample_unique
            and work['parameter_update_multiplications']==writes,'MEAN frozen-residual aggregation/write work')
    else:
        require(work['game_parameter_commits']==0 and work['sample_parameter_commits']==samples
            and work['weighted_residual_multiplications']==work['weighted_residual_accumulations']==0
            and work['parameter_update_multiplications']==2*writes,'NSEQ per-sample current-residual/write work')
    max_samples=max(g['steps']-(g['status']=='WON') for g in games)
    require(work['feature_index_buffer_int64_peak']>=32*max_samples
        and work['sorted_feature_buffer_int64_peak']>=32*max_samples
        and work['sample_step_buffer_int64_peak']>=max_samples
        and work['sample_end_buffer_int64_peak']>=max_samples,'actual sample/feature buffer peak')
    mean_buffers=('error_buffer_doubles_peak','raw_prediction_buffer_doubles_peak','address_gradient_buffer_doubles_peak')
    if method=='EPISODE_MEAN_MC':require(work[mean_buffers[0]]>=max_samples and work[mean_buffers[1]]>=max_samples
        and work[mean_buffers[2]]>=game_unique/len(games),'MEAN actual residual/gradient buffers')
    else:require(all(work[k]==0 for k in mean_buffers),'NSEQ charged unused MEAN buffers')
    vector_peaks=[v for k,v in work.items() if k.endswith('_peak') and k!='native_buffer_bytes_peak']
    require(8*max(vector_peaks+[targets['target_buffer_doubles_peak']])<=work['native_buffer_bytes_peak']
        <=8*(sum(vector_peaks)+targets['target_buffer_doubles_peak']),'joint native buffer peak scope')
    offsets=[];cursor=0
    for game in games:offsets.append(cursor);cursor+=game['steps']
    for example,index in ((fit['first_sample'],0),(fit['last_sample'],len(games)-1)):
        game=games[index];values=scores[game['episode']]
        require(len(values)==game['steps'] and sum(values)==game['score'],'canonical normalized fit score inventory')
        labels=factual_targets(values,game['status']);position=0 if index==0 else len(labels)-1
        require((example['episode'],example['step'],example['target'])==(index,offsets[index]+position,labels[position]),
            'normalized global first/last sample or after-current-action target')
        require(example['raw_target']==example['target']
            and close(example['error'],example['raw_target']-example['raw_prediction_before_update']),
            'normalized query offset/sample residual')
    require('Nonwinning training samples' in fit['count_semantics']['td_updates']
        and 'not parameter writes' in fit['count_semantics']['table_update_occurrences'],'published processed sample/write distinction')
    return writes


def audit(directory):
    directory=Path(directory);d=json_file(directory/'summary.json');settings=d['settings']
    require(settings==json_file(directory/'configuration.json'),'frozen configuration changed')
    expected_settings=dict(lifecycles=list(range(16)),parents=4,arms=list(ARMS),phase='A',fit_fraction=.8,
        alpha=.0025,query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),evaluation_games=16,
        seed_evaluation=290500000000,max_steps=8192,bootstrap_draws=20000,bootstrap_seed=29000001,
        primary='EPISODE_MEAN_MC_minus_FROZEN_COMPLETE_GAME_UTILITY',
        primary_prediction='EPISODE_MEAN_MC_minus_FROZEN_COMPLETE_HELDOUT_MSE',
        address_counts='ALL_NONWINNING_FEATURE_OCCURRENCES_IN_ONE_COMPLETE_GAME',
        evaluation='STATIC_SAME_FIT_PREFIX_BELIEF_WITHOUT_VALUE_OR_MEMORY_UPDATES')
    for key,value in expected_settings.items():require(settings[key]==value,'registered '+key)
    require(d['schema']=='acfqp.episode_consolidation.v290' and d['status']=='EXPERIMENT_COMPLETE'
        and d['scientific_gate']=='NOT_A_FORMAL_GATE','experimental status')
    old=json_file(settings['source_summary']);require(json_file(Path(settings['source_summary']).with_name('audit.json'))
        ['independent_valid'],'existing retained critic audit')
    require(d['source_provenance']==old['source_provenance'],'source provenance changed')
    lives=d['by_lifecycle'];old_lives={l['lifecycle']:l for l in old['by_lifecycle']}
    require([l['lifecycle'] for l in lives]==list(range(16))
        and all(l['parent']==l['lifecycle']%4 for l in lives),'complete fixed source cohort')
    original=json_file(old['settings']['source_summary']);scores=read_retained_scores(original)
    records=[];processed=Counter();cutoffs=0
    for life in lives:
        lid=life['lifecycle'];ds=life['dataset'];previous=old_lives[lid]
        check_dataset(ds,previous['dataset'])
        require(life['evaluation_snapshot']==previous['evaluation_snapshot'],'fixed fit-prefix p/memory')
        require(life['original_frozen_and_mc_heldout_exact'] and life['original_mc_fit_exact'],'producer original reproduction')
        n=ds['fit_game_count'];fit_games=ds['games'][:n];heldout_games=ds['games'][n:]
        fit_samples=sum(g['steps']-(g['status']=='WON') for g in fit_games)
        score_rows=[scores[lid][g['episode']] for g in heldout_games]
        require(all(len(row)==g['steps'] and sum(row)==g['score'] for g,row in zip(heldout_games,score_rows)),
            'canonical full heldout scores')
        arms={}
        for arm in ARMS:
            value=life['arms'][arm];fit=value['fit']
            expected_samples=0 if arm=='FROZEN' else fit_samples
            require(value['processed_training_samples']==value['sample_counter']==fit['trained_afterstates']==expected_samples,
                'same nonwinning processed training sample inventory')
            processed[arm]+=expected_samples
            if arm=='FROZEN':
                require(fit['method']=='NONE' and not fit['learning_counts'] and not fit['target_counts']
                    and not fit['consolidation_counts'] and value['head_setup']['private_weight_bytes']==0,
                    'frozen value source was fitted/copied')
            elif arm=='EPISODIC_MC':
                expected=previous['arms'][arm]['fit']
                for key in ('learning_counts','target_counts','first_update','last_update'):
                    require(fit[key]==expected[key],'original sequential MC '+key)
                require(not fit['consolidation_counts'],'ordinary MC extra consolidation work')
            else:
                check_normalized_fit(fit,fit_games,ds,scores[lid],arm)
                first=fit['first_sample'];expected=previous['arms']['EPISODIC_MC']['fit']['first_update']
                equal_tree(first,expected,'original source first sample prediction/target')
            if arm in ('FROZEN','EPISODIC_MC'):
                expected=previous['arms'][arm]['heldout']
                for key in ('game_metrics','metrics','prediction_counts','target_counts'):
                    require(value['heldout'][key]==expected[key],'original full heldout reproduction '+arm+' '+key)
            heldout=check_holdout(value['heldout'],heldout_games,score_rows,ds['fit_step_end'])
            arms[arm]=dict(check_evaluation(value['game_summaries'],lid,value['evaluation_counts']),heldout=heldout)
            cutoffs+=arms[arm]['cutoffs']
        left,right=(life['arms'][a]['fit']['consolidation_counts'] for a in ARMS[2:])
        for key in ('feature_extractions','feature_occurrences','feature_digit_reads','feature_address_multiply_adds',
            'game_sort_calls','game_sort_items','game_sort_comparisons','address_occurrence_count_visits',
            'address_occurrence_count_comparisons','sample_sort_calls','sample_sort_items','sample_sort_comparisons',
            'address_denominator_searches','address_denominator_search_comparisons','sample_unique_addresses','game_unique_addresses'):
            require(left[key]==right[key],'same full addresses/exposures for both normalized methods')
        records.append(dict(lifecycle=lid,parent=lid%4,arms=arms))
    summary=d['summary'];equal_tree(summary['by_lifecycle'],records,'complete game/heldout means')
    require(summary['primary_contrast']==summary['primary_prediction_contrast']=='EPISODE_MEAN_MC_minus_FROZEN'
        and summary['primary_prediction_metric']=='mse' and summary['bootstrap_draws']==20000
        and summary['bootstrap_seed']==29000001
        and summary['estimator']=='EQUAL_EVALUATION_GAMES_THEN_LIFECYCLES'
        and summary['heldout_estimator']=='EQUAL_COMPLETE_HELDOUT_GAMES_THEN_LIFECYCLES'
        and summary['complete_game_endpoints']==(cutoffs==0),'endpoint/weighting/complete terminal scope')
    for arm in ARMS:
        arm_rows=[r['arms'][arm] for r in records];heldout=[r['heldout'] for r in arm_rows]
        equal_tree(summary['arms'][arm],dict(mean_game_utility=mean(r['mean_game_utility'] for r in arm_rows),
            **{key:sum(r[key] for r in arm_rows) for key in ('games','wins','losses','cutoffs','steps')},
            heldout=dict(games=sum(r['games'] for r in heldout),samples=sum(r['samples'] for r in heldout),
                **{key:mean(r[key] for r in heldout) for key in ('bias','mse','mae')})),'equal life mean '+arm)
    require(set(summary['paired_contrasts'])==set(summary['heldout_contrasts'])==
        {left+'_minus_'+right for left,right in PAIRS},'registered contrasts')
    for left,right in PAIRS:
        name=left+'_minus_'+right
        check_contrast(summary['paired_contrasts'][name],
            [r['arms'][left]['mean_game_utility']-r['arms'][right]['mean_game_utility'] for r in records],'higher_is_better')
        for key in ('bias','mse','mae'):
            check_contrast(summary['heldout_contrasts'][name][key],
                [r['arms'][left]['heldout'][key]-r['arms'][right]['heldout'][key] for r in records],
                None if key=='bias' else 'lower_is_better')
    account=d['accounting'];inherited=old['accounting']['inherited_costs_per_arm']['FROZEN']
    economic=old['accounting']['economic_training_raw_tiles_per_arm']['FROZEN']
    require(account['new_training_environment_observations']==0
        and account['processed_training_samples']==dict(processed),'new training observations or different samples')
    require(account['retained_physical_A_raw_tiles']==old['accounting']['retained_physical_A_raw_tiles']
        and account['retained_physical_A_counts']==old['accounting']['retained_physical_A_counts'],'physical retained acquisition')
    require(account['reconstruction_costs_by_lifecycle']=={str(l['lifecycle']):l['dataset']['costs'] for l in lives},
        'new reconstruction work omitted')
    for arm in ARMS:
        require(account['inherited_costs_per_arm'][arm]==inherited
            and account['economic_training_raw_tiles_per_arm'][arm]==economic,'full source and excluded tail economic costs')
        for field,section,name in (('fit_counts','fit','learning_counts'),('heldout_prediction_counts','heldout','prediction_counts')):
            require(account[field][arm]==sum_counts(l['arms'][arm][section][name] for l in lives),'actual '+field)
        for section in ('fit','heldout'):
            targets=[l['arms'][arm][section]['target_counts'] for l in lives]
            require(account[section+'_target_counts'][arm]==sum_counts(
                {k:v for k,v in counts.items() if k!='target_buffer_doubles_peak'} for counts in targets),
                'actual target work')
            require(account[section+'_target_buffer_doubles_peak'][arm]==max(c.get('target_buffer_doubles_peak',0) for c in targets),
                'target buffer peaks accumulated')
        counts=[l['arms'][arm]['fit']['consolidation_counts'] for l in lives]
        require(account['consolidation_counts'][arm]==sum_counts(
            {k:v for k,v in c.items() if not k.endswith('_peak')} for c in counts),'actual consolidation work')
        peaks={key:max(c.get(key,0) for c in counts) for key in {k for c in counts for k in c if k.endswith('_peak')}}
        require(account['consolidation_buffer_peaks'][arm]==peaks,'consolidation buffer peaks accumulated')
        require(account['private_head_weight_bytes_created'][arm]==sum(l['arms'][arm]['head_setup']['private_weight_bytes'] for l in lives),
            'private head allocation cost')
        for kind in ('environment','planning'):
            require(account['evaluation_counts_per_arm'][arm][kind]==sum_counts(l['arms'][arm]['evaluation_counts'][kind] for l in lives),
                'per-arm new evaluation cost')
    for kind in ('environment','planning'):
        require(account['evaluation_counts'][kind]==sum_counts(l['arms'][a]['evaluation_counts'][kind] for l in lives for a in ARMS),
            'physical new evaluation cost')
    require([p['parent'] for p in d['parent_receipts']]==list(range(4)),'source physical loads')
    for p in d['parent_receipts']:
        require(p['lifecycle_ids']==list(range(p['parent'],16,4)) and p['source_setup']['checkpoint_loads']==1
            and p['source_setup']['new_leaf_updates']==0,'source once/shared frozen initialization')
    for field in ('worker_cpu_seconds','compiler_cpu_seconds'):
        require(close(account[field],sum(p['cpu_seconds' if field=='worker_cpu_seconds' else field] for p in d['parent_receipts'])),
            'actual process CPU aggregate')
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,
        new_training_environment_observations=0,processed_training_samples=dict(processed),evaluation_games=1024,
        evaluation_cutoffs=cutoffs,economic_training_raw_tiles_per_arm=economic,
        actual_parameter_writes={a:account['fit_counts'][a].get('table_updates',0) for a in ARMS},
        primary_utility=summary['paired_contrasts']['EPISODE_MEAN_MC_minus_FROZEN'],
        primary_full_heldout_mse=summary['heldout_contrasts']['EPISODE_MEAN_MC_minus_FROZEN']['mse'],
        contrasts={name:{key:value[key] for key in ('mean','ci95','improved_equal_worse','adverse_lifecycles')}
            for name,value in summary['paired_contrasts'].items()},
        method='Canonical full-game factual suffix labels, original FROZEN/MC closure, normalized sample/write inventories, '
            'all terminal/utility/fresh seed receipts, equal-game/life signed endpoints and complete acquisition/processing costs.',
        limitations='No formal source-weight reload or re-fitting, intermediate board/weight replay or 20000-draw CI regeneration. '
            'Finite native normalization tests and compact address/sample/write counters define the verified update scope. '
            'Conditional on four existing sources and one retained actor dataset; normalization changes effective step sizes.',errors=[])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    directory=parser.parse_args().input
    try:result=audit(directory)
    except ValueError as error:result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False));raise SystemExit(not result['independent_valid'])


if __name__=='__main__':main()
