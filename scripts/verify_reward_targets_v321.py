#!/usr/bin/env python3
"""Independent V321 reward-only n-step intervention, saved controls and paid work."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
from statistics import mean

import numpy as np

from verify_closed_loop_v313 import (ACTIONS, HeadVersions, close, equal_tree,
    json_file, literal_choose, physical_status, read_source_weights, require, swipe,
    planning_counts, check_representation, sum_counts)
from verify_greedy_targets_v317 import feature_addresses
from verify_query_supervision_v319 import (GROUP_FIELDS, artifact_arrays, check_group_fit,
    effect_status)
from verify_teacher_calibration_v320 import check_probes
from reward_rng_audit_v321 import first_six_uniforms

TASKS = ('A', 'B')
DISTRIBUTIONS = ('FACTUAL_LOCAL', 'QUERY_LOCAL')
UPDATING_ARMS = ('OLD_FACTUAL', 'OLD_QUERY', 'NSTEP_FACTUAL', 'NSTEP_QUERY')
ARMS = ('SOURCE', 'FIRST_LOCAL')+UPDATING_ARMS
GROUPS, REPLICAS, HORIZON = 16384, 4, 4
TRACE_COLUMNS = ['root_local_index', 'member', 'action_number_1based', 'action',
    'gained_score', 'new_spawn_cell', 'new_spawn_rank', 'ground_status_after_optional_spawn', 'endpoint_kind']
DENSE_FIELDS = ('target_reward','scores','actions','new_raw_tiles','status','tail_reward',
    'bootstrap_afterstates','final_boards','last_preboards','last_afterstates','rollout_seeds')


def continuation_seed(life, task, number, group, member):
    return 321500000000+life*10000000+TASKS.index(task)*1000000+number*100000+group*4+member


def evaluation_seed(life, task, episode):
    return 321900000000+life*1000000+TASKS.index(task)*100000+episode


def reward_values(boards, teacher, radix=11):
    addresses = feature_addresses(boards, radix)
    values = np.zeros(len(addresses), dtype=np.float64)
    for occurrence in range(32): values += teacher.reward[addresses[:, occurrence]]
    return values


def check_nstep(moves, roots, cells, ranks, selected_action, targetkind, seeds,
                outcomes, teacher, probability, horizon=HORIZON, radix=11):
    """All paid physics is replayed; a live final afterstate reads only frozen FIRST_R."""
    n = len(roots); shape = n, REPLICAS
    require(roots.dtype == np.int32 and roots.shape == (n,16), 'all original ordered rootgroups retain their exact boards')
    for value in (cells,ranks,selected_action,targetkind):
        require(value.dtype == np.int32 and value.shape == shape, 'all four saved V319 members remain present per rootgroup')
    require(seeds.dtype == np.uint64 and seeds.shape == shape, 'every member has its exact paired fresh V321 stream seed')
    require(moves.dtype == np.int32 and moves.ndim == 2 and moves.shape[1] == 9,
        'all executed reward actions retain the nine declared physical trace fields')
    for field in ('scores','actions','new_raw_tiles'):
        require(outcomes[field].dtype == np.int64 and outcomes[field].shape == shape, 'dense score action and paid spawn counts retain exact integer members')
    require(outcomes['status'].dtype == np.int32 and outcomes['status'].shape == shape,
        'every member endpoint is explicit WON LOST or bootstrapped')
    for field in ('bootstrap_afterstates','final_boards','last_preboards','last_afterstates'):
        require(outcomes[field].dtype == np.int32 and outcomes[field].shape == (n,REPLICAS,16), 'reward endpoints retain exact declared physical afterstate boards')
    cursor = 0; counts = Counter(); tails = np.zeros(shape); rewards = np.zeros(shape)
    uniforms = first_six_uniforms(seeds)
    probe_indices = set(range(min(8,n*REPLICAS)))|set(range(max(0,n*REPLICAS-8),n*REPLICAS)); expected_probes = {}
    bootstraps = []; bootstrap_positions = []
    for group in range(n):
        root = roots[group].tolist(); require(max(root) < radix, 'all saved reset roots are nonWIN')
        for member in range(REPLICAS):
            board = root.copy(); cell, rank = int(cells[group,member]), int(ranks[group,member])
            require(0 <= cell < 16 and board[cell] == 0 and rank in (1,2), 'the retained already-paid initial spawn is placed exactly once')
            board[cell] = rank; physical = physical_status(board,radix)
            actions = raw = score = 0
            last_pre = last_after = board.copy(); endpoint = -1 if physical == 'LOST' else None
            first_probe = last_probe = None
            if int(targetkind[group,member]) == 3:
                require(physical == 'LOST' and int(selected_action[group,member]) == -1,
                    'saved initial LOST has no invented DIRECT action or reward tail')
            else:
                require(physical == 'ACTIVE' and 0 <= int(selected_action[group,member]) < 4,
                    'the saved DIRECT starts at its actual active postspawn board')
            while cursor < len(moves) and tuple(moves[cursor,:2]) == (group,member):
                row = [int(value) for value in moves[cursor]]
                require(endpoint is None and actions < horizon, 'no action follows a natural or bootstrapped endpoint')
                _,_,step,action,gained,spawn_cell,spawn_rank,after_status,kind = row
                require(step == actions+1 and 0 <= action < 4, 'reward trace preserves chronological one-based action numbering')
                if actions == 0:
                    require(action == int(selected_action[group,member]), 'the saved DIRECT branch cannot be reselected by H2')
                before = board.copy(); after, actual_gain = swipe(board,ACTIONS[action])
                require(after != board and gained == actual_gain, 'each recorded reward action is legal with its exact ground merge score')
                if actions == 0:
                    require(int(targetkind[group,member]) == (2 if max(after) >= radix else 1), 'the prescribed first target kind agrees with its actual DIRECT branch')
                actions += 1; score += gained; last_pre, last_after = before,after.copy()
                if max(after) >= radix:
                    endpoint = 1; require((spawn_cell,spawn_rank,after_status,kind) == (-1,-1,1,1),
                        'analytic WIN stops at its afterstate and acquires no unneeded spawn or bootstrap')
                elif actions == horizon:
                    endpoint = 0; require((spawn_cell,spawn_rank,after_status,kind) == (-1,-1,0,2),
                        'the horizon stops before the final spawn and preserves an explicit frozen reward bootstrap')
                    bootstraps.append(after.copy()); bootstrap_positions.append((group,member))
                else:
                    empty = [i for i,value in enumerate(after) if not value]
                    require(empty, 'every continued reward action has an available physical spawn cell')
                    expected_cell = empty[int(uniforms[group,member,2*raw]*len(empty))]
                    expected_rank = 1 if uniforms[group,member,2*raw+1] < 1.-probability else 2
                    require((spawn_cell,spawn_rank) == (expected_cell,expected_rank), 'each newly paid spawn follows its independent exact seeded cell/rank stream')
                    after[spawn_cell] = spawn_rank; raw += 1; physical = physical_status(after,radix)
                    expected_status = -1 if physical == 'LOST' else 0
                    require(after_status == expected_status and kind == (-1 if physical == 'LOST' else 0),
                        'the optional-spawn endpoint follows the actual physical LOST or continuing board')
                    if physical == 'LOST': endpoint = -1
                board = after; cursor += 1
                if actions >= 2 and group*REPLICAS+member in probe_indices:
                    probe = dict(step=actions,preboard=before,chosen_action=ACTIONS[action],chosen_afterstate=last_after)
                    if first_probe is None: first_probe = probe
                    last_probe = probe
            require(endpoint is not None, 'every active member retains its full prescribed horizon or natural terminal endpoint')
            if actions == 0: require(endpoint == -1, 'an active member cannot omit its prescribed DIRECT action')
            expected_bootstrap = last_after if endpoint == 0 else [0]*16
            require(int(outcomes['scores'][group,member]) == score and int(outcomes['actions'][group,member]) == actions
                and int(outcomes['new_raw_tiles'][group,member]) == raw and int(outcomes['status'][group,member]) == endpoint
                and np.array_equal(outcomes['final_boards'][group,member],board)
                and np.array_equal(outcomes['last_preboards'][group,member],last_pre)
                and np.array_equal(outcomes['last_afterstates'][group,member],last_after)
                and np.array_equal(outcomes['bootstrap_afterstates'][group,member],expected_bootstrap),
                'dense endpoint score actions paid spawns and all final afterstates match complete independent replay')
            rewards[group,member] = score/2048.
            counts.update(rollouts=1,actions=actions,new_raw_tiles=raw,new_random_draws=2*raw,
                won=int(endpoint == 1),lost=int(endpoint == -1),bootstrapped=int(endpoint == 0),
                prescribed_direct_actions=int(actions > 0),followup_h2_actions=max(0,actions-1))
            if group*REPLICAS+member in probe_indices:
                expected_probes[group,member] = dict(first_h2_decision=first_probe,last_h2_decision=last_probe)
    require(cursor == len(moves), 'the trace retains all members exactly once without extra omitted or reordered reward actions')
    for begin in range(0,len(bootstraps),4096):
        values = reward_values(bootstraps[begin:begin+4096],teacher,radix)
        for (group,member),value in zip(bootstrap_positions[begin:begin+4096],values): tails[group,member] = value
    rewards += tails
    for field,expected in (('tail_reward',tails),('target_reward',rewards)):
        require(outcomes[field].dtype == np.float64 and outcomes[field].shape == shape
            and np.allclose(outcomes[field],expected,rtol=1e-12,atol=1e-12),
            'every n-step reward is observed immediate scores plus the literal unchanged FIRST_R afterstate bootstrap only')
    return rewards,counts,expected_probes


def sparse_equal(actual, reference, names=('reward','terminal')):
    """Exact existing arrays, without replaying model updates or changing ownership metadata."""
    with np.load(actual['file'],allow_pickle=False) as new, np.load(reference['file'],allow_pickle=False) as old:
        for component in names:
            for suffix in ('indices','values'):
                key = component+'_'+suffix
                require(np.array_equal(new[key],old[key]), 'actual old reward/risk deltas reproduce V319 exactly and reward-only intervention leaves exact risk deltas unchanged')
        return sum(new[component+'_'+suffix].size for component in names for suffix in ('indices','values'))


def check_evaluation(value,life,task,belief,version):
    require(value['estimated_p_four'] == belief and value['planner'] == 'H2'
        and value['head_version'] == version and value['static_evaluation_valid'],
        'all final six arms execute their actual immutable own head and bank belief')
    games = value['game_summaries']
    require(len(games) == 32 and [game['seed'] for game in games] == [evaluation_seed(life,task,i) for i in range(32)],
        'all final evaluation games use thirty-two fresh paired V321 task seeds')
    for game in games:
        require(1 <= game['steps'] <= 8192, 'every natural evaluation uses the frozen full-game horizon')
        if game['status'] == 'CUTOFF':
            require(game['steps'] == 8192 and physical_status(game['final_board']) == 'ACTIVE', 'a real active game cutoff remains explicit')
            bonus = 0.
        else:
            require(game['status'] in ('WON','LOST') and physical_status(game['final_board']) == game['status'], 'each natural evaluation terminal label agrees with its actual final board')
            bonus = 4. if game['status'] == 'WON' else -4.
        require(game['utility'] == game['score']/2048.+bonus, 'fresh whole-game utility uses actual game score and terminal status')
    steps = sum(game['steps'] for game in games); wins = sum(game['status']=='WON' for game in games)
    environment = dict(sampled_transitions=steps,post_action_spawns=steps,initial_spawns=64,
        raw_tile_productions=steps+64,environment_random_draws=2*(steps+64),ground_explicit_swipe_calls=steps,
        ground_state_status_calls=steps+32,ground_status_internal_swipe_calls=4*(steps+32-wins),
        ground_swipe_calls=steps+4*(steps+32-wins))
    require(Counter(value['counts']['environment']) == Counter(environment), 'all final natural game actions initial tiles and winning-action spawns are paid')
    planning_counts(value['counts']['planning'],steps,depth=2)
    if version is not None: check_representation(value['representation_counts'],'LOCAL_RISK',value['counts']['planning'].get('value_predictions',0))
    require(not value['counts'].get('learning',{}), 'final evaluation never updates any fitted head')
    return mean(game['utility'] for game in games)


def check_acquisition_work(value,counts,outcomes,teacher_version,p_model,p_true):
    require(value['status_codes'] == {'WON':1,'LOST':-1,'BOOTSTRAPPED':0}
        and value['horizon'] == 4 and value['p_model'] == p_model and value['p_true'] == p_true
        and value['teacher_updates'] == teacher_version['updates']
        and value['continuation_rule'] == 'SAVED_DIRECT_THEN_FROZEN_FIRST_H2_LAST_AFTERSTATE_REWARD_BOOTSTRAP',
        'the bounded reward acquisition uses the actual unchanged FIRST bank and planned bootstrap horizon')
    raw,n,actions,won = counts['new_raw_tiles'],counts['rollouts'],counts['actions'],counts['won']
    calls = n+actions+raw
    environment = dict(sampled_transitions=actions,post_action_spawns=raw,raw_tile_productions=raw,
        environment_random_draws=2*raw,ground_explicit_swipe_calls=actions,
        ground_state_status_calls=calls,ground_status_internal_swipe_calls=4*(calls-won),
        ground_swipe_calls=actions+4*(calls-won))
    require(Counter(value['environment_counts']) == Counter(environment), 'executed actions and intermediate new spawns are distinct paid costs; last WIN/bootstrap requires no final spawn')
    snapshots = 0; flat = outcomes['actions'].reshape(-1)
    for index in set(range(min(8,n)))|set(range(max(0,n-8),n)):
        h2 = max(0,int(flat[index])-1); snapshots += h2+int(h2 > 0)
    expected = dict(rollouts_started=n,reused_start_spawns=n,rollout_rng_starts=n,
        prescribed_direct_actions=counts['prescribed_direct_actions'],h2_choose_calls=counts['followup_h2_actions'],
        terminal_wins=won,terminal_losses=counts['lost'],reward_bootstrap_predictions=counts['bootstrapped'],
        reward_bootstrap_table_lookups=32*counts['bootstrapped'],trace_rows_written=actions,
        trace_uncompressed_bytes_written=36*actions,boundary_probe_snapshots=snapshots,boundary_probe_bytes_copied=440*snapshots)
    require(Counter(value['counts']) == Counter(expected), 'all executed reward actions bounded H2 copies and FIRST_R bootstrap table reads are charged')
    planning_counts(value['planning_counts'],counts['followup_h2_actions'],depth=2)
    check_representation(value['representation_counts'],'LOCAL_RISK',value['planning_counts'].get('value_predictions',0))
    require(value['cpu_seconds'] >= 0. and value['seconds'] >= 0., 'bounded acquisition includes its actual physics planning and trace packing CPU')


def label_shift(arrays,target):
    delta = target-arrays['targetreward']
    return dict(mean_old_reward=float(np.mean(arrays['targetreward'])),mean_new_reward=float(np.mean(target)),
        mean_delta=float(np.mean(delta)),replica_delta_rms=float(np.sqrt(np.mean(delta*delta))),win_targets_changed=0)


def check_lifecycle(row,old,source_weights,checkpoint):
    life,parent = row['lifecycle'],row['parent']; teachers = {}; learners = {}; counts = Counter()
    require(life == old['lifecycle'] and parent == old['parent'] == life%4, 'all reward-intervention lives retain their actual frozen SOURCE parent')
    for task in TASKS:
        first,previous = row['initial'][task],old['initial'][task]
        require(first['head_version'] == previous['head_version'] and first['context_id'] == previous['context_id'], 'reward intervention begins at actual audited FIRST v0 of its own task')
        equal_tree(first['planning_belief'],previous['planning_belief'], 'every fitted and teacher head retains its immutable observed bank belief')
        identity = dict(lifecycle=life,parent=parent,context_id=first['context_id'],arm='FIRST_LOCAL')
        teacher = HeadVersions(source_weights,checkpoint,identity,'LOCAL_RISK'); teacher.apply(first['head_version']); teachers[task] = teacher
        learners[task] = {}
        for arm in UPDATING_ARMS:
            head = HeadVersions(source_weights,checkpoint,dict(identity,arm=arm),'LOCAL_RISK'); head.apply(first['head_version']); learners[task][arm] = head
    for number in (1,2):
        for task in TASKS:
            stage = row['rounds'][str(number)][task]; first = row['initial'][task]; teacher = teachers[task]
            require(stage['groups'] == GROUPS and stage['replicas'] == REPLICAS and stage['teacher_unchanged']
                and stage['teacher_version'] == first['head_version'] and set(stage['distributions']) == set(DISTRIBUTIONS)
                and set(stage['arms']) == set(UPDATING_ARMS), 'all roots members four arms and immutable teacher remain complete across both rounds')
            p_model = first['planning_belief']['estimated_p_four']; p_true = .1 if task=='A' else .5
            seeds = np.asarray([[continuation_seed(life,task,number,g,m) for m in range(REPLICAS)] for g in range(GROUPS)],dtype=np.uint64)
            for distribution,suffix in (('FACTUAL_LOCAL','FACTUAL'),('QUERY_LOCAL','QUERY')):
                item = stage['distributions'][distribution]; prior = old['rounds'][str(number)][task]['arms'][distribution]
                receipt = prior['supervision']['group_artifact']
                equal_tree(item['source_group_artifact'],receipt, 'both reward label arms share the exact audited V319 roots spawns DIRECT actions and old labels')
                arrays = artifact_arrays(receipt,GROUP_FIELDS,receipt['metadata'])
                require(arrays['roots'].shape == (GROUPS,16) and arrays['targetreward'].shape == arrays['targetwin'].shape == (GROUPS,REPLICAS)
                    and np.array_equal(arrays['mean_reward'],np.mean(arrays['targetreward'],axis=1))
                    and np.array_equal(arrays['mean_win'],np.mean(arrays['targetwin'],axis=1)), 'all complete original group labels retain actual means in original update order')
                read = item['source_read']
                read_names = ('roots','targetreward','targetwin','selected_action','targetkind','spawn_cells','spawn_ranks')
                require(read['file'] == receipt['file'] and read['source_file_bytes'] == receipt['saved_bytes'] and read['new_raw_tiles'] == 0,
                    'restoring existing roots labels and first spawns adds no new acquisition')
                require(read['array_bytes'] == sum(arrays[name].nbytes for name in read_names)
                    and stage['control_source_reads'][distribution]['array_bytes'] == read['array_bytes']
                    and stage['control_source_reads'][distribution]['file'] == receipt['file']
                    and stage['control_source_reads'][distribution]['source_file_bytes'] == receipt['saved_bytes']
                    and stage['control_source_reads'][distribution]['new_raw_tiles'] == 0,
                    'both actual control and acquisition source reads retain exactly the restored array-byte costs')
                metadata = dict(schema='acfqp.reward_targets_outcome.v321',lifecycle=life,parent=parent,task=task,round=number,
                    distribution=distribution,groups=GROUPS,replicas=REPLICAS,horizon=4,teacher_version=first['head_version'],
                    p_model=p_model,p_true=p_true,source_group_file=receipt['file'])
                outcomes = artifact_arrays(item['outcome_artifact'],DENSE_FIELDS,metadata)
                require(np.array_equal(outcomes['rollout_seeds'],seeds), 'all original groups use paired V321 fresh continuation seeds')
                acquisition = item['acquisition']; trace = acquisition['trace_artifact']; path = Path(trace['file'])
                require(trace['columns'] == TRACE_COLUMNS and trace['dtype'] == 'int32'
                    and trace['packing_rule'] == 'GROUP_MEMBER_CHRONOLOGICAL_EXECUTED_ACTIONS'
                    and not trace['reused_start_spawn_included'] and trace['all_new_spawns_included']
                    and trace['endpoint_codes'] == {'CONTINUE':0,'WON':1,'LOST':-1,'BOOTSTRAPPED':2}
                    and path.stat().st_size == trace['compressed_bytes'], 'every newly executed reward action retains complete compact physics including planned no-spawn endpoints')
                with np.load(path,allow_pickle=False) as saved:
                    require(saved.files == ['moves'], 'reward trace stores exactly its actual executed physical rows'); moves = saved['moves']
                require(len(moves) == trace['rows'] and moves.nbytes == trace['uncompressed_bytes'], 'new trace rows and compressed/uncompressed byte receipts agree')
                target,physical,probes = check_nstep(moves,arrays['roots'],arrays['spawn_cells'],arrays['spawn_ranks'],
                    arrays['selected_action'],arrays['targetkind'],seeds,outcomes,teacher,p_true)
                check_acquisition_work(acquisition,physical,outcomes,first['head_version'],p_model,p_true)
                counts['literal_first_H2_boundary_probes'] += check_probes(acquisition['boundary_probes'],probes,teacher,p_model)
                equal_tree(item['label_shift'],label_shift(arrays,target), 'new reward shift moments use all members while old WIN labels remain unchanged')
                for mode in ('OLD','NSTEP'):
                    arm = mode+'_'+suffix; learned = stage['arms'][arm]; head = learners[task][arm]
                    require(learned['updates_before'] == head.receipts[-1]['updates']
                        and learned['updates_after'] == learned['head_version']['updates'] == learned['updates_before']+GROUPS,
                        'each private learner commits once per ordered rootgroup from its own previous version')
                    fit_arrays = dict(arrays)
                    if mode == 'NSTEP':
                        fit_arrays.update(targetreward=target,mean_reward=np.mean(target,axis=1))
                        require(learned['fit']['sampling_unit'] == 'ROOTGROUP_MEAN_OF_FROZEN_FIRST_NSTEP_REWARD_AND_OLD_WIN_REPLICAS', 'changed reward targets keep planned bootstrap semantics and old WIN labels')
                    fit = deepcopy(learned['fit']); fit['sampling_unit'] = 'ROOTGROUP_MEAN_OF_FIXED_TEACHER_ONE_STEP_REPLICAS'
                    counts['actual_parameter_writes_per_head'] += check_group_fit(fit,fit_arrays,head)
                    head.apply(learned['head_version'])
                    if mode == 'OLD':
                        match = learned['control_match']; compared = sparse_equal(learned['head_version'],prior['head_version'])
                        require(match['exact'] and match['file'] == prior['head_version']['file'] and match['arrays_compared'] == 4
                            and match['array_values_compared'] == compared, 'every old-label control round exactly reproduces the real V319 reward and risk sparse deltas before new acquisition')
                    else:
                        control = stage['arms']['OLD_'+suffix]; match = learned['risk_match']; compared = sparse_equal(learned['head_version'],control['head_version'],('terminal',))
                        require(match['exact'] and match['file'] == control['head_version']['file'] and match['arrays_compared'] == 2
                            and match['array_values_compared'] == compared
                            and np.array_equal(head.terminal,learners[task]['OLD_'+suffix].terminal), 'reward-only fitting preserves the exact complete OLD-arm risk head across all rounds')
                    counts.update(fitted_rootgroups=GROUPS,new_head_versions=1)
                counts.update(physical); counts.update(source_group_files=1,trace_files=1,outcome_files=1,
                    trace_array_bytes=moves.nbytes,outcome_array_bytes=item['outcome_artifact']['array_bytes'],
                    old_controls_exact=1,reward_only_risk_exact=1)
    means = {}
    for task in TASKS:
        evaluations = row['final_evaluations'][task]; require(set(evaluations) == set(ARMS), 'all six final SOURCE FIRST old and reward-only arms remain present')
        means[task] = {}
        for arm,value in evaluations.items():
            version = None if arm=='SOURCE' else row['initial'][task]['head_version'] if arm=='FIRST_LOCAL' else learners[task][arm].receipts[-1]
            means[task][arm] = check_evaluation(value,life,task,row['initial'][task]['planning_belief']['estimated_p_four'],version)
            counts.update(evaluation_games=32,evaluation_new_raw_tiles=value['counts']['environment']['raw_tile_productions'])
    return dict(lifecycle=life,parent=parent,cells=means),counts

PAIRS = (('NSTEP_QUERY','OLD_QUERY'),('NSTEP_QUERY','FIRST_LOCAL'),('NSTEP_QUERY','SOURCE'),
    ('NSTEP_QUERY','NSTEP_FACTUAL'),('NSTEP_FACTUAL','OLD_FACTUAL'),('OLD_FACTUAL','FIRST_LOCAL'),('OLD_QUERY','FIRST_LOCAL'))
INTERACTION = 'NSTEP_QUERY_minus_OLD_QUERY_minus_NSTEP_FACTUAL_plus_OLD_FACTUAL'


def check_interval(value,values):
    require(len(values) == 16 and close(value['mean'],mean(values)), 'paired effect intervals preserve all sixteen signed lifecycle means')
    equal_tree(value['lifecycle_values'],{str(i):x for i,x in enumerate(values)}, 'every favorable equal and adverse lifecycle is retained in its paired effect vector')
    equal_tree(value['parent_mean_values'],{str(p):mean(values[p::4]) for p in range(4)}, 'all four actual fixed SOURCE groups retain their conditional paired mean')
    require(value['positive_equal_negative'] == [sum(x>0 for x in values),sum(x==0 for x in values),sum(x<0 for x in values)], 'no adverse lifecycle is removed from the effect directions')
    low,high = value['ci95']; minimum = mean(min(values[p::4]) for p in range(4)); maximum = mean(max(values[p::4]) for p in range(4))
    require(minimum-1e-10 <= low <= high <= maximum+1e-10
        and value['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_REUSED_FIRST_COHORT'
        and value['status95'] == effect_status(value,True), 'reported interval stays within actual fixed-parent bootstrap bounds and keeps its supported sign')


def check_analysis(summary,records,lives):
    cutoffs = []; actual_records = []
    for row,record in zip(lives,records):
        endpoints = {}
        for task in TASKS:
            endpoints[task] = {}
            for arm in ARMS:
                games = row['final_evaluations'][task][arm]['game_summaries']
                endpoints[task][arm] = {status:sum(g['status']==status for g in games) for status in ('WON','LOST','CUTOFF')}
                cutoffs.extend(dict(lifecycle=row['lifecycle'],task=task,arm=arm,seed=g['seed']) for g in games if g['status']=='CUTOFF')
        actual_records.append(dict(record,retained_endpoint_counts=endpoints))
    equal_tree(summary['by_lifecycle'],actual_records, 'all final six-arm actual game means and endpoint counts are retained')
    complete = not cutoffs
    require(summary['primary_contrast'] == 'NSTEP_QUERY_minus_OLD_QUERY_FINAL_AB'
        and summary['physical_evaluation_games'] == 6144 and summary['cutoffs'] == cutoffs
        and summary['complete_game_endpoints'] == complete and summary['bootstrap_executed'] == complete
        and summary['bootstrap_seed'] == 32100001 and summary['bootstrap_draws'] == 20000
        and summary['bootstrap_unit'] == 'PAIRED_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT',
        'sole reward-intervention primary and whole-cohort cutoff HOLD use paired lifecycles rather than individual game replicates')
    names = {a+'_minus_'+b for a,b in PAIRS}|{INTERACTION}
    require(set(summary['final_ab_contrasts']) == names and set(summary['task_contrasts']) == set(TASKS), 'all frozen final and task secondary contrasts remain explicit')
    def view(value,tasks):
        require(set(value) == names, 'each frozen contrast view retains all planned pairs and the interaction')
        means = {arm:[mean(r['cells'][task][arm] for task in tasks) for r in records] for arm in ARMS}
        vectors = {left+'_minus_'+right:[a-b for a,b in zip(means[left],means[right])] for left,right in PAIRS}
        vectors[INTERACTION] = [q-o-f+c for q,o,f,c in zip(means['NSTEP_QUERY'],means['OLD_QUERY'],means['NSTEP_FACTUAL'],means['OLD_FACTUAL'])]
        for name,values in vectors.items():
            if complete: check_interval(value[name],values)
            else: require(value[name] is None, 'any natural cutoff suppresses every terminal-benefit interval without imputing unfinished WIN truth')
    view(summary['final_ab_contrasts'],TASKS)
    for task in TASKS: view(summary['task_contrasts'][task],(task,))
    final = summary['final_ab_contrasts']; primary = final['NSTEP_QUERY_minus_OLD_QUERY']
    equal_tree(summary['primary'],primary, 'the sole primary remains the final query reward-label intervention rather than a favorable secondary')
    def status(value,retention=False): return effect_status(value,complete,retention)
    primary_status = status(primary); self_status = status(final['NSTEP_QUERY_minus_FIRST_LOCAL'])
    retention = {task:status(summary['task_contrasts'][task]['NSTEP_QUERY_minus_FIRST_LOCAL'],True) for task in TASKS}
    retained = self_status == 'SUPPORTED_GAIN' and all(x == 'SUPPORTED_NONDECREASE' for x in retention.values())
    expected = dict(primary_status=primary_status,primary_intervention_supported=primary_status == 'SUPPORTED_GAIN',
        primary_self_improvement_status=self_status,primary_self_improvement_supported=self_status == 'SUPPORTED_GAIN',
        final_net_gain_status=status(final['NSTEP_QUERY_minus_SOURCE']),factual_intervention_status=status(final['NSTEP_FACTUAL_minus_OLD_FACTUAL']),
        interaction_status=status(final[INTERACTION]),task_retention_status=retention,
        retained_improvement_supported=retained,repaired_query_supported=retained and primary_status == 'SUPPORTED_GAIN')
    equal_tree({name:summary[name] for name in expected},expected, 'query target repair own-FIRST learning and both-bank retention are separate evidence requirements')
    require(summary['secondary_interval_scope'] == 'NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM'
        and 'not terminal truth' in summary['evidence_scope'] and 'costs can differ' in summary['evidence_scope'], 'reward intervention keeps planned-bootstrap and unmatched acquisition-cost scientific scope')


def expected_configuration(source):
    return dict(schema='acfqp.reward_targets_freeze.v321',source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[1]/'specs/REWARD_TARGETS_V321.md'),
        lifecycles=list(range(16)),parents=4,workers=4,tasks=list(TASKS),arms=list(UPDATING_ARMS),
        distributions=list(DISTRIBUTIONS),rounds=[1,2],groups=GROUPS,replicas=REPLICAS,horizon=4,alpha=.0025,
        true_probabilities={'A':.1,'B':.5},teacher='ACTUAL_IMMUTABLE_V317_FIRST_LOCAL_V0',
        planning_belief='ACTUAL_IMMUTABLE_V319_FIRST_BANK_BELIEF',
        controls='ALL_SIXTEEN_LIVES_ALL_ROUND_DELTAS_EXACT_V319_BEFORE_ANY_NEW_ACQUISITION',
        reward='SAVED_DIRECT_THEN_FIRST_H2_SCORE_PLUS_FIRST_REWARD_LAST_AFTERSTATE_BEFORE_SPAWN',
        win='UNCHANGED_V319_MEMBER_TARGETS_AND_EXACT_MATCHED_RISK_PARAMETERS',
        bootstrap='PLANNED_NONTERMINAL_TARGET_NOT_TERMINAL_TRUTH_OR_CUTOFF',
        seed_continuation=321500000000,life_stride=10000000,task_stride=1000000,round_stride=100000,group_stride=4,
        expected_rollouts=8388608,maximum_new_training_raw_tiles=25165824,evaluation_games_per_cell=32,
        evaluation_arms=list(ARMS),evaluation_checkpoints=['FINAL'],seed_evaluation=321900000000,
        expected_evaluation_games=6144,max_steps=8192,primary='NSTEP_QUERY_minus_OLD_QUERY_FINAL_AB',bootstrap_draws=20000,bootstrap_seed=32100001,
        stop_rule='CONTROL_MISMATCH_NO_ACQUISITION_ANY_NATURAL_EVALUATION_CUTOFF_GLOBAL_HOLD',
        cost_scope='NEW_TARGETS_PHYSICAL_ONCE_CHARGED_TO_NSTEP_NOT_MATCHED_RAW_BUDGET_WITH_OLD')


def check_control_phase(directory,lives):
    phase = json_file(directory/'control_phase.json')
    require(phase == dict(status='ALL_CONTROLS_EXACT',matched_versions=128,new_raw_tiles=0,lifecycles=list(range(16)),
        control_receipts=[str(directory/'control_receipts'/f'life_{i}.json') for i in range(16)]),
        'all 128 exact old-label controls complete globally before any new acquisition')
    for row,path in zip(lives,phase['control_receipts']):
        saved = json_file(path)
        require(saved['lifecycle'] == row['lifecycle'] and saved['parent'] == row['parent']
            and saved['initial'] == row['initial'] and saved['control_head_setups'] == row['control_head_setups'], 'every immutable saved control phase belongs to its actual FIRST lifecycle')
        for number in ('1','2'):
            for task in TASKS:
                stage,actual = saved['rounds'][number][task],row['rounds'][number][task]
                require(set(stage['arms']) == {'OLD_FACTUAL','OLD_QUERY'} and 'distributions' not in stage, 'completed control phase has no new reward acquisition or n-step fits')
                equal_tree(stage['arms'],{arm:actual['arms'][arm] for arm in ('OLD_FACTUAL','OLD_QUERY')}, 'final old heads preserve the globally precompleted exact control fits')
                equal_tree(stage['control_source_reads'],actual['control_source_reads'], 'both actual old-label source read costs remain preserved')


def check_accounting(document,inherited,diagnostic,physical,execution):
    account = document['accounting']; lives = document['by_lifecycle']
    stages = [s for row in lives for tasks in row['rounds'].values() for s in tasks.values()]
    distributions = [s['distributions'][d] for s in stages for d in DISTRIBUTIONS]
    evaluations = [e for row in lives for tasks in row['final_evaluations'].values() for e in tasks.values()]
    fit_items = [s['arms'][a] for s in stages for a in UPDATING_ARMS]
    reads = [r for s in stages for r in s['control_source_reads'].values()]+[d['source_read'] for d in distributions]
    expected_arms = {}
    for arm in UPDATING_ARMS:
        cells = [s['arms'][arm] for s in stages]
        acquisitions = [s['distributions'][arm.split('_')[1]+'_LOCAL']['acquisition'] for s in stages] if arm.startswith('NSTEP') else []
        expected_arms[arm] = dict(rootgroups=sum(i['fit']['fitted_rootgroups'] for i in cells),fit_counts=sum_counts(i['fit']['learning_counts'] for i in cells),
            fit_cpu_seconds=sum(i['fit']['cpu_seconds'] for i in cells),economic_new_training_raw_tiles=sum(v['environment_counts'].get('raw_tile_productions',0) for v in acquisitions),
            economic_acquisition_cpu_seconds=sum(v['cpu_seconds'] for v in acquisitions))
    equal_tree(account['per_arm'],expected_arms, 'old controls receive no new target raw and each changed-label arm pays its full physically shared acquisition once')
    expected = dict(control_matched_versions=128,new_training_raw_tiles=sum(d['acquisition']['environment_counts'].get('raw_tile_productions',0) for d in distributions),
        training_environment_counts=sum_counts(d['acquisition']['environment_counts'] for d in distributions),
        acquisition_counts=sum_counts(d['acquisition']['counts'] for d in distributions),training_planning_counts=sum_counts(d['acquisition']['planning_counts'] for d in distributions),
        training_representation_counts=sum_counts(d['acquisition']['representation_counts'] for d in distributions),
        source_group_reads=len(reads),source_file_bytes_referenced=sum(r['source_file_bytes'] for r in reads),source_array_bytes_read=sum(r['array_bytes'] for r in reads),
        source_read_cpu_seconds=sum(r['cpu_seconds'] for r in reads),trace_files=len(distributions),trace_saved_bytes=sum(d['acquisition']['trace_artifact']['compressed_bytes'] for d in distributions),
        outcome_files=len(distributions),outcome_saved_bytes=sum(d['outcome_artifact']['saved_bytes'] for d in distributions),new_head_files=len(fit_items),
        new_head_saved_bytes=sum(i['head_version']['saved_bytes'] for i in fit_items),new_evaluation_games=sum(len(e['game_summaries']) for e in evaluations),
        new_evaluation_environment_counts=sum_counts(e['counts']['environment'] for e in evaluations),new_evaluation_cpu_seconds=sum(e['cpu_seconds'] for e in evaluations))
    equal_tree({name:account[name] for name in expected},expected, 'all source reads training physics fitting storage and new natural evaluations reconcile actual receipts')
    require(not account['source_training_repeated'] and not account['first_adaptation_repeated'] and not account['prior_full_audit_repeated']
        and account['new_training_raw_tiles'] == physical['new_raw_tiles'] <= 25165824
        and account['new_evaluation_games'] == physical['evaluation_games'] == 6144
        and account['new_evaluation_environment_counts']['raw_tile_productions'] == physical['evaluation_new_raw_tiles'],
        'prior training evidence is inherited once and actual new physical targets and evaluations match independent read counts')
    require([(r['phase'],r['parent']) for r in document['parent_receipts']] == [(phase,p) for phase in ('control','intervention') for p in range(4)], 'all four parent workers remain present in both globally separated phases')
    worker = sum(p['cpu_seconds'] for p in document['parent_receipts']); compiler = sum(p['compiler_cpu_seconds'] for p in document['parent_receipts'])
    require(close(account['worker_cpu_seconds'],worker) and close(account['compiler_cpu_seconds'],compiler)
        and close(account['new_experiment_component_cpu_seconds'],worker+compiler+account['coordinator_cpu_seconds'])
        and close(account['inherited_successful_source_v317_v319_full_cpu_seconds'],inherited)
        and close(account['economic_source_v317_v319_and_experiment_component_cpu_seconds'],inherited+account['new_experiment_component_cpu_seconds'])
        and close(account['preceding_v320_diagnostic_full_cpu_seconds'],diagnostic), 'completed two-phase worker compiler and coordinator costs include old controls and physical generation once; prior diagnostic remains separate')
    require(execution['exit_code'] == 0 and execution['process_tree_cpu_seconds']+1e-6 >= account['new_experiment_component_cpu_seconds'],
        'full original process-tree CPU includes final serialization and shutdown beyond component receipts')


def check_parent(source,rows,old):
    checkpoint = source['checkpoint']; weights = read_source_weights(checkpoint)
    physical = Counter(); records = []
    for row in rows:
        record,counts = check_lifecycle(row,old[row['lifecycle']],weights,checkpoint)
        records.append(record); physical.update(counts)
        print(json.dumps(dict(event='independent_reward_targets_life_checked',lifecycle=row['lifecycle'])),flush=True)
    return records,physical


def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    require(document['schema'] == 'acfqp.reward_targets.v321' and document['status'] in ('EXPERIMENT_COMPLETE','HOLD_CUTOFF')
        and document['scientific_gate'] == 'EXPLORATORY_REWARD_TARGET_INTERVENTION_NO_U006_AUTHORIZATION', 'new intervention retains its exploratory gate and explicit possible scientific failure')
    source = Path(document['source_summary']).resolve(); previous = json_file(source); prior = json_file(source.parent/'audit.json')
    require(previous['schema'] == 'acfqp.query_supervision.v319' and previous['status'] == 'EXPERIMENT_COMPLETE'
        and prior['status'] == 'PASS' and prior['independent_valid'] and json_file(source.parent/'audit_execution.json')['exit_code'] == 0,
        'reward intervention inherits the already independently audited complete V319 groups without rerunning prior audits')
    configuration = expected_configuration(source)
    equal_tree(json_file(directory/'configuration.json'),configuration, 'all rootgroups WIN labels horizon alpha seeds and sole primary are frozen before new acquisition')
    equal_tree(document['settings'],configuration, 'the complete result retains the exact frozen intervention configuration')
    equal_tree(document['source_provenance'],previous['source_provenance'], 'the four frozen SOURCE parents remain unchanged')
    lives = document['by_lifecycle']; require([r['lifecycle'] for r in lives] == list(range(16)), 'all sixteen original FIRST lifecycles remain without selection')
    check_control_phase(directory,lives)
    old = {r['lifecycle']:r for r in previous['by_lifecycle']}; sources = {r['parent']:r for r in previous['source_provenance']['parents']}
    physical = Counter(); records = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(check_parent,sources[parent],[row for row in lives if row['parent'] == parent],
            {life:row for life,row in old.items() if row['parent'] == parent}) for parent in range(4)]
        for job in as_completed(jobs):
            parent_records,parent_physical = job.result(); records.extend(parent_records); physical.update(parent_physical)
    records.sort(key=lambda row:row['lifecycle'])
    check_analysis(document['summary'],records,lives)
    require(document['status'] == ('EXPERIMENT_COMPLETE' if document['summary']['complete_game_endpoints'] else 'HOLD_CUTOFF'), 'any retained natural cutoff holds the entire terminal-benefit conclusion')
    inherited = json_file(source.parent/'audit_costs.json')['full_economic_source_v317_and_experiment_cpu_seconds']
    diagnostic = json_file(source.parent.parent/'teacher_calibration_v320/execution.json')['process_tree_cpu_seconds']
    execution = json_file(directory/'execution.json'); require((directory/'stderr.log').stat().st_size == 0, 'original completed reward intervention has empty stderr')
    check_accounting(document,inherited,diagnostic,physical,execution)
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,**dict(physical),
        prior_v319_audit_status='PASS',prior_full_audit_repeated=False,
        every_new_physical_swipe_spawn_rng_and_reward_target_checked=True,
        frozen_FIRST_reward_bootstrap_and_boundary_H2_probes_valid=True,
        old_controls_exact_before_acquisition=True,reward_only_WIN_targets_and_risk_parameters_unchanged=True,
        all_final_natural_game_summaries_and_paired_effects_valid=True,
        complete_game_endpoints=document['summary']['complete_game_endpoints'],primary_status=document['summary']['primary_status'],
        new_experiment_component_cpu_seconds=document['accounting']['new_experiment_component_cpu_seconds'],
        new_experiment_full_cpu_seconds=execution['process_tree_cpu_seconds'],full_economic_source_v317_v319_and_experiment_cpu_seconds=inherited+execution['process_tree_cpu_seconds'],
        preceding_v320_diagnostic_full_cpu_seconds=diagnostic,
        limitations='All new reward-label physics RNG scores and frozen FIRST_R bootstrap reads are independently replayed; H2 decisions use fixed first/last probes. '
            'Final natural game summaries, actual head versions, paired lifecycle vectors and interval bounds are checked; natural games, fits and bootstrap draws are not rerun. '
            'Evidence is conditional on the existing cohort/four fixed parents and arbitrary-afterstate reset access. '
            'Short targets remain bootstrapped and acquisition costs differ from old labels. No U006 authorization or general strategic-learning claim.')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('directory',type=Path); parser.add_argument('--output',type=Path)
    args = parser.parse_args(); result = audit(args.directory)
    target = args.output or args.directory/'audit.json'; target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='independent_reward_targets_audit_complete',status=result['status'],primary_status=result['primary_status'])),flush=True)


if __name__ == '__main__': main()
