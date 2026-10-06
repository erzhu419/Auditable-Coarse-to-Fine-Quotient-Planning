#!/usr/bin/env python3
"""Independent new V315 paired component experiment, without old tape/target replay."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from statistics import mean
from types import SimpleNamespace

import numpy as np

from verify_closed_loop_v313 import (HeadVersions, TileRandom, literal_choose, physical_status,
    read_source_weights, close, equal_tree, json_file, require, sum_counts,
    planning_counts, check_representation)

TASKS = ('A', 'B')
PROBABILITIES = {'A': .1, 'B': .5}
ARMS = ('MC_MC', 'TD_MC', 'MC_TD', 'TD_TD', 'FIRST_LOCAL')
COMBINATIONS = {'MC_MC':('MC_LOCAL','MC_LOCAL'), 'TD_MC':('TD_LOCAL','MC_LOCAL'),
    'MC_TD':('MC_LOCAL','TD_LOCAL'), 'TD_TD':('TD_LOCAL','TD_LOCAL'), 'FIRST_LOCAL':('FIRST_LOCAL','FIRST_LOCAL')}
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_REALIZED_V314_HEADS'


def evaluation_seed(life, task, episode):
    return 315900000000+life*1000000+(100000 if task == 'B' else 0)+episode


def initial_state(seed, p_four):
    """Independent actual two initial cell/rank draws from each evaluation stream."""
    rng = TileRandom(seed); board = [0]*16; spawns = []
    for _ in range(2):
        empty = [cell for cell,value in enumerate(board) if value == 0]
        cell = empty[min(int(rng.random()*len(empty)), len(empty)-1)]
        rank = 1 if rng.random() < 1.-p_four else 2
        board[cell] = rank; spawns.append(dict(kind='INITIAL',cell=cell,rank=rank))
    return board, spawns


def initial_board(seed, p_four):
    return initial_state(seed, p_four)[0]


def expected_components(previous, task, arm):
    old = previous['initial'][task]['head_versions']['FIRST_LOCAL']
    versions = {'FIRST_LOCAL':old, **{name:previous['rounds']['2'][task]['arms'][name]['head_version']
        for name in ('MC_LOCAL', 'TD_LOCAL')}}
    reward, win = COMBINATIONS[arm]
    return dict(reward_version=versions[reward], win_version=versions[win])


def check_component_link(saved, previous, task, arm):
    expected = expected_components(previous, task, arm)
    equal_tree(saved, expected, 'actual reward/WIN components address the declared audited V314 arm versions')
    return expected


def check_probe(probe, life, task, belief, reward_head, win_head):
    seed = evaluation_seed(life, task, 0)
    board, spawns = initial_state(seed, PROBABILITIES[task])
    require(probe['episode'] == 0 and probe['seed'] == seed
        and probe['board'] == board and probe['initial_spawns'] == spawns
        and probe['origin'] == 'NATIVE_NEW_EVALUATION_INITIAL_STATE_SAME_H2_ENTRYPOINT'
        and probe['repeated_initial_random_draws'] == 4,
        'the sole predeclared probe is the actual seeded initial board of the first new evaluation game')
    chosen = literal_choose(probe['board'], reward_head.reward, win_head.terminal,
        'LOCAL_RISK', belief, depth='H2')
    equal_tree({key:probe['chosen'][key] for key in chosen}, chosen,
        'all literal H2 candidate actions and values use the declared actual reward/WIN components')
    require(probe['chosen']['status'] == 'ACTIVE', 'actual two-tile initial game board is active')
    planning_counts(probe['chosen']['counts'], 1, depth=2)
    check_representation(probe['chosen']['representation_counts'], 'LOCAL_RISK',
        probe['chosen']['counts'].get('value_predictions', 0))
    return chosen


def check_evaluation(value, life, task, belief):
    require(value['estimated_p_four'] == belief and value['planner'] == 'H2', 'all five new component arms use their actual immutable V314 bank probability')
    games = value['game_summaries']
    require(len(games) == 32 and [game['seed'] for game in games] == [evaluation_seed(life,task,i) for i in range(32)],
        'all component cells use the new V315 paired whole-game task seeds')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'new component evaluation preserves the actual game horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and physical_status(game['final_board']) == 'ACTIVE', 'component evaluation never relabels an early artificial cutoff')
            bonus = 0.
        else:
            require(game['status'] in ('WON','LOST') and physical_status(game['final_board']) == game['status'],
                'component game terminal label matches its physical final board')
            bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'new paired utility retains the unchanged natural WIN/LOST terminal value')
    steps = sum(game['steps'] for game in games); wins = sum(game['status'] == 'WON' for game in games)
    environment = dict(sampled_transitions=steps,post_action_spawns=steps,initial_spawns=64,raw_tile_productions=steps+64,
        environment_random_draws=2*(steps+64),ground_explicit_swipe_calls=steps,ground_state_status_calls=steps+32,
        ground_status_internal_swipe_calls=4*(steps+32-wins),ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(value['counts']['environment']) == Counter(environment), 'every new component evaluation initial and action tile is paid once')
    planning_counts(value['counts']['planning'],steps,depth=2)
    check_representation(value['representation_counts'],'LOCAL_RISK',value['counts']['planning'].get('value_predictions',0))
    require(not value['counts'].get('learning',{}), 'component experiment evaluates fixed borrowed tables without any new fit')
    return dict(games=32,mean_game_utility=mean(game['utility'] for game in games),wins=wins,
        losses=sum(game['status']=='LOST' for game in games),cutoffs=sum(game['status']=='CUTOFF' for game in games),
        cutoff_episodes=[i for i,game in enumerate(games) if game['status']=='CUTOFF'],steps=steps)

MECHANISMS = {
    'reward_given_MC_WIN':(('TD_MC',1.),('MC_MC',-1.)),
    'reward_given_TD_WIN':(('TD_TD',1.),('MC_TD',-1.)),
    'WIN_given_MC_reward':(('MC_TD',1.),('MC_MC',-1.)),
    'WIN_given_TD_reward':(('TD_TD',1.),('TD_MC',-1.)),
    'interaction':(('TD_TD',1.),('TD_MC',-1.),('MC_TD',-1.),('MC_MC',1.)),
}
SECONDARY_PAIRS = (('TD_TD','MC_MC'),)+tuple((arm,'FIRST_LOCAL') for arm in ARMS[:4])


def check_contrast(saved, values, family=False):
    require(len(values) == 16 and close(saved['mean'],mean(values)), 'all realized signed component effect lifecycle inputs retain their actual mean')
    equal_tree(saved['lifecycle_deltas'],{str(i):value for i,value in enumerate(values)},'all paired V315 component lifecycle effects')
    groups = [values[parent::4] for parent in range(4)]
    equal_tree(saved['parent_mean_deltas'],{str(parent):mean(group) for parent,group in enumerate(groups)},'four realized parent groups condition on their frozen V314 heads')
    require(saved['interval_scope'] == INTERVAL_SCOPE, 'component intervals retain their realized-head conditional scope')
    minimum, maximum = mean(min(group) for group in groups), mean(max(group) for group in groups)
    low, high = saved['ci95']
    require(minimum-1e-10 <= low <= high <= maximum+1e-10, 'pointwise component intervals stay within their fixed-parent bootstrap feasible range')
    if family:
        lower, upper = saved['ci99']
        require(minimum-1e-10 <= lower <= low <= high <= upper <= maximum+1e-10,
            'family Bonferroni 99% intervals enclose the pointwise 95% intervals from the same draws')
    else:
        require('ci99' not in saved and 'family_status' not in saved, 'task and secondary pointwise intervals do not acquire family decisions')
    require(saved['improved_equal_worse'] == [sum(value>0 for value in values),sum(value==0 for value in values),sum(value<0 for value in values)]
        and saved['adverse_lifecycles'] == [i for i,value in enumerate(values) if value<0], 'all adverse realized component effects remain in the new paired results')


def aggregate(values):
    return dict(games=sum(value['games'] for value in values),wins=sum(value['wins'] for value in values),
        losses=sum(value['losses'] for value in values),cutoffs=sum(value['cutoffs'] for value in values),
        steps=sum(value['steps'] for value in values),mean_game_utility=mean(value['mean_game_utility'] for value in values))


def effect_status(interval, complete, retention=False):
    if not complete:
        return 'INCOMPLETE_GAME_ENDPOINTS'
    low, high = interval
    if retention:
        return 'SUPPORTED_NONDECREASE' if low>=0 else 'SUPPORTED_LOSS' if high<0 else 'UNRESOLVED'
    return 'SUPPORTED_POSITIVE' if low>0 else 'SUPPORTED_NEGATIVE' if high<0 else 'UNRESOLVED'


def check_analysis(summary, records):
    equal_tree(summary['by_lifecycle'],records,'all new component endpoints and actual frozen head component links')
    metadata = dict(bootstrap_draws=20000,bootstrap_seed=31500001,interval_scope=INTERVAL_SCOPE,
        estimator='EQUAL_TASKS_THEN_EVALUATION_GAMES_THEN_LIFECYCLES',primary_family=list(MECHANISMS),
        mechanism_family_size=5,family_error_rate=.05,family_interval_level=.99,
        family_adjustment='BONFERRONI_FIVE_TWO_SIDED_EFFECTS')
    equal_tree({key:summary[key] for key in metadata},metadata,'exact five prespecified equal-task Bonferroni mechanism effects and paired bootstrap contract')
    require(set(summary['mechanism_contrasts']) == set(MECHANISMS)
        and set(summary['secondary_contrasts']) == {left+'_minus_'+right for left,right in SECONDARY_PAIRS},
        'new component primary family and secondary comparisons retain every prespecified effect')
    def effect(row,task,terms):
        return sum(coefficient*row['cells'][task]['arms'][arm]['mean_game_utility'] for arm,coefficient in terms)
    for name,terms in MECHANISMS.items():
        check_contrast(summary['mechanism_contrasts'][name],[mean(effect(row,task,terms) for task in TASKS) for row in records],True)
        for task in TASKS:
            check_contrast(summary['cells'][task]['mechanism_contrasts'][name],[effect(row,task,terms) for row in records])
    for left,right in SECONDARY_PAIRS:
        name=left+'_minus_'+right;terms=((left,1.),(right,-1.))
        check_contrast(summary['secondary_contrasts'][name],[mean(effect(row,task,terms) for task in TASKS) for row in records])
        for task in TASKS:
            check_contrast(summary['cells'][task]['secondary_contrasts'][name],[effect(row,task,terms) for row in records])
    for task in TASKS:
        equal_tree(summary['cells'][task]['arms'],{arm:aggregate([row['cells'][task]['arms'][arm] for row in records]) for arm in ARMS},
            'all five physically new task evaluation arm aggregates')
    arms={arm:aggregate([row['cells'][task]['arms'][arm] for row in records for task in TASKS]) for arm in ARMS}
    equal_tree(summary['arms'],arms,'each of the 5120 physically new component evaluation endpoints is counted once')
    complete=not any(value['cutoffs'] for value in arms.values())
    require(summary['complete_game_endpoints'] == complete, 'all component effect support retains every evaluation cutoff')
    family={name:effect_status(value['ci99'],complete) for name,value in summary['mechanism_contrasts'].items()}
    equal_tree(summary['mechanism_family_status'],family,'primary mechanism decisions use the family 99% intervals')
    require(all(summary['mechanism_contrasts'][name]['family_status']==value for name,value in family.items()),
        'each declared family status agrees with its own multiplicity-adjusted interval')
    retention={arm:{task:effect_status(summary['cells'][task]['secondary_contrasts'][arm+'_minus_FIRST_LOCAL']['ci95'],complete,True)
        for task in TASKS} for arm in ARMS[:4]}
    equal_tree(summary['task_retention_status'],retention,'descriptive actual task FIRST contrasts use their pointwise retention intervals')
    equal_tree(summary['task_retention_supported'],{arm:all(value=='SUPPORTED_NONDECREASE' for value in tasks.values()) for arm,tasks in retention.items()},
        'each frozen component retains both task nondecreases before descriptive preservation support')
    return dict(mechanism_family_status=family,task_retention_status=retention,complete_game_endpoints=complete)


def check_component_state(state, components):
    before=dict(reward_updates=components['reward_version']['updates'],win_updates=components['win_version']['updates'])
    expected=dict(before=before,after=before,weight_copy_parameters=0,allocated_weight_bytes=0,
        weight_files_saved=0,new_fit_states=0,new_parameter_writes=0)
    equal_tree(state,expected,'actual combinations share immutable references without fitting parameter copies or new weight files')


def check_compute(account, prior_account):
    total=sum(account[key] for key in ('worker_cpu_seconds','compiler_cpu_seconds','coordinator_cpu_seconds'))
    require(close(account['new_evaluation_total_cpu_seconds'],total)
        and close(account['economic_source_and_target_and_new_cpu_seconds'],prior_account['economic_source_and_target_cpu_seconds']+total),
        'audited prior SOURCE/V314 CPU is inherited once; restoration probe and evaluation work stays contained in new physical CPU')
def expected_configuration(prior_summary):
    return dict(schema='acfqp.component_target_freeze.v315',
        protocol=str(Path(__file__).resolve().parents[1]/'specs/COMPONENT_TARGETS_V315.md'),
        prior_summary=str(Path(prior_summary).resolve()),lifecycles=list(range(16)),parents=4,workers=4,
        tasks=list(TASKS),arms=list(ARMS),components={key:list(value) for key,value in COMBINATIONS.items()},
        true_probabilities=PROBABILITIES,source_versions='V314_FIRST_V0_MC_V2_TD_V2',
        planning_probability='V314_IMMUTABLE_FIRST_FIT_BANK_BELIEF',combination='EXACT_IMMUTABLE_ARRAY_REFERENCES_ZERO_WEIGHT_COPY',
        new_training_raw_tiles=0,new_fit_states=0,new_parameter_writes=0,
        query=dict(reward_weight=1.,failure_penalty=4.,goal_bonus=4.),planner='H2',max_steps=8192,
        evaluation_games_per_cell=32,seed_evaluation=315900000000,expected_evaluation_games=5120,
        action_probes='FIRST_NEW_GAME_INITIAL_BOARD_PER_CELL',bootstrap_draws=20000,bootstrap_seed=31500001,
        mechanism_family=list(MECHANISMS),mechanism_family_ci=.99,pointwise_ci=.95,multiplicity='BONFERRONI_FIVE_AB_CONTRASTS',
        evidence_scope='FROZEN_V314_TRAINING_INSTANCES_NEW_PAIRED_EVALUATION_ONLY',
        stop_rule='NO_ARM_SEED_FIT_BUDGET_OR_INTERVAL_SELECTION_RETAIN_ALL_ENDPOINTS')


def require_prior(prior_path):
    prior_path=Path(prior_path); prior=json_file(prior_path)
    result=json_file(prior_path.parent/'audit.json'); execution=json_file(prior_path.parent/'audit_execution.json')
    require(prior['schema']=='acfqp.local_targets.v314' and prior['status']=='EXPERIMENT_COMPLETE'
        and result['status']=='PASS' and result['independent_valid'] and execution['exit_code']==0
        and result['every_native_td_target_checked'] and result['fixed_first_collector_valid']
        and result['identical_factual_states_and_writes_valid'],
        'component experiment requires the actual complete independently audited V314 training instances')
    require([life['lifecycle'] for life in prior['by_lifecycle']]==list(range(16))
        and all(life['parent']==life['lifecycle']%4 for life in prior['by_lifecycle']),
        'all realized prior V314 heads remain under their original four fixed parents')
    return prior,result


def check_restoration(receipt, head, selected):
    chain=head.receipts
    require(receipt['source_checkpoint']==head.source_checkpoint and receipt['selected_head']==selected,
        'every physically restored native head reads its own declared actual SOURCE and selected V314 head')
    metadata_keys=('schema','head_kind','lifecycle','parent','context_id','arm','version','updates','file',
        'base_file','source_checkpoint','default_terminal','parameter_count','reward_indices_count','terminal_indices_count')
    equal_tree(receipt['version_chain'],[{key:row[key] for key in metadata_keys} for row in chain],
        'actual restoration visits its complete own sparse SOURCE-relative version ancestry')
    counts=dict(version_files_loaded=len(chain),version_file_bytes_read=sum(row['saved_bytes'] for row in chain),
        reward_sparse_parameter_writes=sum(row['reward_indices_count'] for row in chain),
        win_sparse_parameter_writes=sum(row['terminal_indices_count'] for row in chain))
    require(Counter(receipt['counts'])==Counter(counts), 'sparse restoration reads and non-fit assignment writes retain their actual inventory')
    size=head.reward.size; setup=receipt['setup_counts']
    require(setup['source_parameters_copied']==size and setup['source_weight_bytes_copied']==8*size
        and setup['allocated_weight_parameters']==2*size and setup['allocated_weight_bytes']==16*size
        and setup['initialized_zero_risk_parameters']==size and receipt['private_weight_bytes']==16*size,
        'all three actual restored LOCAL heads charge their real SOURCE copy zero initialization and allocation')


def check_lifecycle(life, previous, source_weights, checkpoint):
    require(life['lifecycle']==previous['lifecycle'] and life['parent']==previous['parent'],
        'fresh component evaluation keeps each realized V314 lifecycle and parent identity')
    require(set(life['tasks'])==set(TASKS), 'both immutable actual task banks remain in the component experiment')
    cells={}; probes=0; files=0
    for task in TASKS:
        item=life['tasks'][task]; initial=previous['initial'][task]
        belief=initial['planning_belief']['estimated_p_four']; context=initial['context_id']
        require(item['context_id']==context and item['estimated_p_four']==belief,
            'component selection preserves the observed actual task bank and its immutable first-FIT planning belief')
        require(set(item['head_components'])==set(item['evaluations'])==set(item['component_states'])==set(item['action_probes'])==set(ARMS)
            and set(item['head_restorations'])=={'FIRST_LOCAL','MC_LOCAL','TD_LOCAL'},
            'only the five frozen component combinations and three actual parent heads are present')
        heads={}
        for arm in ('FIRST_LOCAL','MC_LOCAL','TD_LOCAL'):
            identity=dict(lifecycle=life['lifecycle'],parent=life['parent'],context_id=context,arm=arm)
            head=HeadVersions(source_weights,checkpoint,identity,'LOCAL_RISK')
            v0=initial['head_versions']['FIRST_LOCAL'];head.apply(v0)
            if arm!='FIRST_LOCAL':
                for r in ('1','2'):
                    head.apply(previous['rounds'][r][task]['arms'][arm]['head_version'])
            check_restoration(item['head_restorations'][arm],head,head.receipts[-1]);files+=len(head.receipts)
            heads[arm]=head
        arms={}
        for arm,(reward,win) in COMBINATIONS.items():
            components=check_component_link(item['head_components'][arm],previous,task,arm)
            check_component_state(item['component_states'][arm],components)
            require(len(item['action_probes'][arm])==1,'one predeclared actual first-game action probe is retained per new cell')
            check_probe(item['action_probes'][arm][0],life['lifecycle'],task,belief,heads[reward],heads[win]);probes+=1
            arms[arm]=check_evaluation(item['evaluations'][arm],life['lifecycle'],task,belief)
        cells[task]=dict(task=task,context_id=context,estimated_p_four=belief,head_components=item['head_components'],arms=arms)
        del heads
    return dict(lifecycle=life['lifecycle'],parent=life['parent'],cells=cells),probes,files


def check_accounting(document, prior):
    account=document['accounting'];lives=document['by_lifecycle'];parents=document['parent_receipts']
    tasks=[task for life in lives for task in life['tasks'].values()]
    evaluations=[value for task in tasks for value in task['evaluations'].values()]
    probes=[value for task in tasks for values in task['action_probes'].values() for value in values]
    restorations=[value for task in tasks for value in task['head_restorations'].values()]
    inherited=prior['accounting']
    expected=dict(inherited_v314_accounting=inherited,prior_training_physical_repeated=False,
        new_training_raw_tiles=0,new_fit_states=0,new_parameter_writes=0,
        economic_training_raw_tiles_per_arm={arm:inherited['economic_training_raw_tiles_per_arm'][
            'FIRST_LOCAL' if arm=='FIRST_LOCAL' else 'TD_LOCAL'] for arm in ARMS},
        new_combination_weight_copy_parameters=0,new_combination_weight_bytes=0,new_weight_files=0,
        restored_head_instances=96,head_reconstruction_counts=sum_counts(item['counts'] for item in restorations),
        head_reconstruction_setup_counts=sum_counts(item['setup_counts'] for item in restorations),
        private_head_weight_bytes_peak=max(sum(item['private_weight_bytes'] for item in task['head_restorations'].values()) for task in tasks),
        head_reconstruction_cpu_seconds=sum(item['cpu_seconds'] for item in restorations),
        new_evaluation_games=5120,evaluation_cpu_seconds=sum(value['cpu_seconds'] for value in evaluations),
        evaluation_environment_counts=sum_counts(value['counts']['environment'] for value in evaluations),
        evaluation_planning_counts=sum_counts(value['counts']['planning'] for value in evaluations),
        evaluation_representation_counts=sum_counts(value['representation_counts'] for value in evaluations),
        action_probes=160,probe_repeated_initial_random_draws=640,probe_cpu_seconds=sum(value['cpu_seconds'] for value in probes),
        probe_planning_counts=sum_counts(value['chosen']['counts'] for value in probes),
        probe_representation_counts=sum_counts(value['chosen']['representation_counts'] for value in probes),
        worker_cpu_seconds=sum(row['cpu_seconds'] for row in parents),compiler_cpu_seconds=sum(row['compiler_cpu_seconds'] for row in parents),
        new_compute_closed=True)
    require(len(tasks)==32 and len(evaluations)==len(probes)==160 and len(restorations)==96,
        'all thirty-two banks restore three heads and execute each of their five paired cells exactly once')
    equal_tree({key:account[key] for key in expected},expected,'all new component allocation restoration probe evaluation and zero learning costs close exactly')
    check_compute(account,inherited)
    source={row['parent']:row for row in prior['source_provenance']['parents']}
    require([row['parent'] for row in parents]==list(range(4)) and all(row['source_setup']['checkpoint_loads']==1
        and row['source_setup']['new_leaf_updates']==0 and row['source_setup']['inherited_updates']==source[row['parent']]['updates'] for row in parents),
        'each new component worker loads one fixed audited SOURCE checkpoint without fitting or source retraining')


def audit(directory):
    directory=Path(directory).resolve();document=json_file(directory/'summary.json');frozen=json_file(directory/'configuration.json')
    require(document['schema']=='acfqp.component_targets.v315' and document['status']=='EXPERIMENT_COMPLETE'
        and document['scientific_gate']=='NOT_A_FORMAL_GATE','complete new paired V315 component-evaluation terminal schema')
    equal_tree(frozen,expected_configuration(frozen['prior_summary']),'frozen new V315 component and evaluation contract')
    equal_tree(document['settings'],frozen,'all new component evaluations preserve their frozen contract')
    require(document['prior_summary']==frozen['prior_summary'],'component input is the original frozen V314 summary path')
    prior,prior_audit=require_prior(frozen['prior_summary'])
    equal_tree(document['source_provenance'],prior['source_provenance'],'new evaluations keep the same four realized audited SOURCE parents')
    require([life['lifecycle'] for life in document['by_lifecycle']]==list(range(16))
        and all(life['parent']==life['lifecycle']%4 for life in document['by_lifecycle']),
        'all sixteen realized V314 lifecycles contribute new component evidence without replacement')
    sources={row['parent']:row for row in prior['source_provenance']['parents']}
    weights={parent:read_source_weights(row['checkpoint']) for parent,row in sources.items()}
    records=[];probes=files=0
    for life,old in zip(document['by_lifecycle'],prior['by_lifecycle']):
        record,count,read=check_lifecycle(life,old,weights[life['parent']],sources[life['parent']]['checkpoint'])
        records.append(record);probes+=count;files+=read
    support=check_analysis(document['summary'],records);check_accounting(document,prior)
    require(probes==160 and files==224,'all predeclared component probes and complete sparse head ancestries are independently reconstructed')
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,
        prior_v314_audit_status=prior_audit['status'],prior_raw_and_targets_replayed=False,
        immutable_component_links_valid=True,immutable_bank_probabilities_valid=True,
        reconstructed_head_instances=96,sparse_version_files_read=files,literal_initial_board_probes=probes,
        new_evaluation_games=5120,new_training_raw_tiles=0,new_fit_states=0,new_parameter_writes=0,
        mechanism_family_size=5,family_interval_level=.99,
        new_evaluation_total_cpu_seconds=document['accounting']['new_evaluation_total_cpu_seconds'],
        economic_source_and_target_and_new_cpu_seconds=document['accounting']['economic_source_and_target_and_new_cpu_seconds'],**support,
        mechanism_contrasts=document['summary']['mechanism_contrasts'],
        method='Read completed V314 independent PASS without replaying old tapes or target arrays; independently reconstruct only the actual SOURCE-relative sparse head versions, verify exact frozen reward/WIN component ownership and unchanged update counts, independent seeded initial boards and all candidate native H2 actions for each new cell, all new paired natural endpoint utilities and counts, signed lifecycle effects with family 99%/pointwise 95% interval decisions and complete new/cumulative physical-economic compute.',
        limitations='New evaluation evidence is conditional on the same sixteen realized V314 training instances and four frozen SOURCE parents. Five family effects describe realized component utility contributions and interaction; they do not establish a new-training-population effect, microscopic learning cause or independent growth confirmation. Complete evaluation actions and bootstrap draws are not rerun; only the declared initial-board probes are recomputed. Historical dynamics CPU remains unknown.',errors=[])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=audit(args.output)
    except (ValueError,KeyError,FileNotFoundError,IndexError) as error:
        result=dict(status='FAIL',independent_valid=False,errors=[str(error)])
    (args.output/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False))
    return 0 if result['independent_valid'] else 1


if __name__=='__main__':
    raise SystemExit(main())
