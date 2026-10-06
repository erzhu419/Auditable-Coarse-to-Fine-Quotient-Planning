#!/usr/bin/env python3
"""Independent V320 terminal continuation physics and frozen-FIRST calibration."""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean

import numpy as np

from verify_closed_loop_v313 import (ACTIONS, HeadVersions, TileRandom, close, equal_tree,
    json_file, literal_choose, physical_status, read_source_weights, require, swipe,
    planning_counts, check_representation, sum_counts)
from verify_query_supervision_v319 import GROUP_FIELDS, artifact_arrays

TASKS = ('A', 'B')
ARMS = ('FACTUAL_LOCAL', 'QUERY_LOCAL')
GROUPS, REPLICAS, OLD_GROUPS = 64, 4, 16384
TRACE_COLUMNS = ['root_local_index', 'member', 'action_number_1based', 'action',
    'gained_score', 'new_spawn_cell', 'new_spawn_rank', 'ground_status_after_spawn']
DENSE_FIELDS = ('original_group_indices', 'rollout_seeds', 'scores', 'actions',
    'new_raw_tiles', 'status', 'final_boards', 'reward_return', 'win', 'utility')


def selected_groups(groups=GROUPS, old_groups=OLD_GROUPS):
    return np.linspace(0, old_groups-1, groups, dtype=np.int64)


def continuation_seed(life, task, number, original_group, member):
    return 320500000000+life*10000000+TASKS.index(task)*1000000+number*100000+original_group*4+member


def _status_code(board, radix):
    return {'ACTIVE': 0, 'WON': 1, 'LOST': -1}[physical_status(board, radix)]


def check_continuations(moves, roots, cells, ranks, selected_action, targetkind,
                        seeds, outcomes, probability, max_steps=8192, radix=11):
    """Replay every newly paid action/spawn; the saved first spawn consumes no new RNG."""
    roots = np.asarray(roots)
    n = len(roots); shape = n, REPLICAS
    require(roots.dtype == np.int32 and roots.shape == (n, 16), 'selected retained roots preserve exact physical board data')
    for value in (cells, ranks, selected_action, targetkind):
        require(value.dtype == np.int32 and value.shape == shape, 'each selected old root retains all four actual members')
    require(seeds.dtype == np.uint64 and seeds.shape == shape, 'every continuation retains its own exact paired fresh seed')
    require(moves.dtype == np.int32 and moves.ndim == 2 and moves.shape[1] == 8,
        'continuation trace has exactly the eight declared physical integer fields')
    for field in ('scores', 'actions', 'new_raw_tiles'):
        require(outcomes[field].dtype == np.int64 and outcomes[field].shape == shape, 'all dense continuation costs and scores retain exact int64 members')
    require(outcomes['status'].dtype == np.int32 and outcomes['status'].shape == shape
        and outcomes['final_boards'].dtype == np.int32 and outcomes['final_boards'].shape == (n, REPLICAS, 16),
        'all terminal or cutoff statuses retain their actual final board')
    cursor = 0; counts = Counter(); rewards = np.full(shape, np.nan); wins = np.full(shape, np.nan)
    probe_indices = set(range(min(8, n*REPLICAS))) | set(range(max(0, n*REPLICAS-8), n*REPLICAS))
    probe_boards = {}
    for group in range(n):
        root = roots[group].tolist()
        require(max(root) < radix, 'the diagnostic starts at saved nonWIN roots')
        for member in range(REPLICAS):
            board = root.copy(); cell = int(cells[group, member]); rank = int(ranks[group, member])
            require(0 <= cell < 16 and board[cell] == 0 and rank in (1, 2), 'the saved initial V319 spawn is physically placed once')
            board[cell] = rank; initial_status = _status_code(board, radix)
            action_count = score = 0; status = initial_status; rng = TileRandom(int(seeds[group, member]))
            first_probe = last_probe = None; first_score = 0
            if int(targetkind[group, member]) == 3:
                require(initial_status == -1 and int(selected_action[group, member]) == -1,
                    'saved DIRECT LOST members terminate without a fabricated action or paid continuation spawn')
            else:
                require(initial_status == 0 and 0 <= int(selected_action[group, member]) < 4,
                    'a saved selected DIRECT action begins at its actual active postspawn board')
            while cursor < len(moves) and tuple(moves[cursor, :2]) == (group, member):
                row = [int(value) for value in moves[cursor]]
                require(status == 0 and action_count < max_steps, 'no continuation executes an action after natural termination or its frozen cutoff')
                _, _, step, action, gained, spawn_cell, spawn_rank, after_status = row
                require(step == action_count+1 and 0 <= action < 4, 'every physical member retains chronological 1-based action numbering')
                if action_count == 0:
                    require(action == int(selected_action[group, member]), 'the prescribed first DIRECT action is the actual saved target branch')
                before = board.copy(); after, actual_score = swipe(board, ACTIONS[action])
                require(after != board and gained == actual_score, 'every recorded continuation action is legal and has its exact ground merge score')
                if action_count == 0:
                    first_score = gained
                    require(int(targetkind[group, member]) == (2 if max(after) >= radix else 1),
                        'saved bootstrap or analytic WIN kind agrees with the prescribed ground DIRECT branch')
                empty = [index for index, value in enumerate(after) if not value]
                require(empty, 'each executed physical action supplies a fresh spawn cell')
                expected_cell = empty[int(rng.random()*len(empty))]
                expected_rank = 1 if rng.random() < 1.-probability else 2
                require((spawn_cell, spawn_rank) == (expected_cell, expected_rank),
                    'all newly paid continuation spawns follow their exact seeded cell/rank stream')
                after[spawn_cell] = spawn_rank; status = _status_code(after, radix)
                require(after_status == status, 'every recorded post-spawn status agrees with its physical board, including winning-action spawn')
                action_count += 1; score += gained; board = after; cursor += 1
                if action_count >= 2 and group*REPLICAS+member in probe_indices:
                    probe = dict(step=action_count, preboard=before, chosen_action=ACTIONS[action], chosen_afterstate=swipe(before, ACTIONS[action])[0])
                    if first_probe is None: first_probe = probe
                    last_probe = probe
            if status == 0:
                require(action_count == max_steps, 'an active endpoint is an explicit full-horizon CUTOFF rather than an omitted tail')
            if action_count == 0:
                require(initial_status == -1, 'an active saved member cannot silently omit its prescribed DIRECT action')
            require(int(outcomes['scores'][group, member]) == score
                and int(outcomes['actions'][group, member]) == action_count
                and int(outcomes['new_raw_tiles'][group, member]) == action_count
                and int(outcomes['status'][group, member]) == status
                and np.array_equal(outcomes['final_boards'][group, member], board),
                'each dense endpoint is its complete replayed score, paid actions/spawns, natural status and final board')
            if status:
                rewards[group, member] = score/2048.; wins[group, member] = float(status == 1)
            counts.update(rollouts=1, actions=action_count, new_raw_tiles=action_count,
                new_random_draws=2*action_count, won=int(status == 1), lost=int(status == -1), cutoffs=int(status == 0),
                prescribed_direct_actions=int(action_count > 0), followup_h2_actions=max(0, action_count-1),
                first_action_score=first_score)
            if group*REPLICAS+member in probe_indices:
                probe_boards[group, member] = dict(first_h2_decision=first_probe, last_h2_decision=last_probe)
    require(cursor == len(moves), 'no extra, missing, reordered or out-of-cohort physical trace rows survive terminal replay')
    for field, actual in (('reward_return', rewards), ('win', wins), ('utility', rewards+8.*(wins-.5))):
        if field in outcomes:
            require(outcomes[field].dtype == np.float64 and outcomes[field].shape == shape
                and np.allclose(outcomes[field], actual, rtol=1e-12, atol=1e-12, equal_nan=True),
                'terminal returns include all prescribed and followup rewards while every cutoff truth remains NaN')
    return rewards, wins, counts, probe_boards


def check_probes(probes, expected, teacher, probability, radix=11):
    require(len(probes) == len(expected), 'all predeclared first-eight and last-eight rollout boundary probes remain present')
    checked = 0; observed = set()
    for row in probes:
        key = row['root_local_index'], row['member']
        require(key in expected and key not in observed, 'bounded teacher probes use the frozen rollout positions exactly once')
        observed.add(key)
        for field in ('first_h2_decision', 'last_h2_decision'):
            value, physical = row[field], expected[key][field]
            if physical is None:
                require(value is None, 'a DIRECT-only terminal member has no invented followup H2 teacher query')
                continue
            require(value is not None and all(value[key] == physical[key] for key in ('step','preboard','chosen_action','chosen_afterstate'))
                and value['p_model'] == probability, 'actual H2 boundary decisions bind the replayed board, action and immutable bank belief')
            actual = literal_choose(physical['preboard'], teacher.reward, teacher.terminal, 'LOCAL_RISK', probability, radix=radix)
            require(actual['action'] == physical['chosen_action'] and actual['afterstate'] == physical['chosen_afterstate'],
                'bounded followup decisions reproduce the exact unchanged FIRST H2 teacher')
            require(close(value['chosen_h2_value'], actual['value']), 'the saved chosen H2 value is its actual teacher candidate value')
            equal_tree(value['action_values'], actual['action_values'], 'all bounded teacher H2 candidate values use actual frozen FIRST weights')
            checked += 1
    require(observed == set(expected), 'both probe boundaries retain every prescribed rollout even when no H2 action occurs')
    return checked


def check_continuation_work(value, counts, outcomes, teacher_version, probability, true_probability):
    require(value['status_codes'] == {'WON':1, 'LOST':-1, 'CUTOFF':0}
        and value['max_steps'] == 8192 and value['p_model'] == probability and value['p_true'] == true_probability
        and value['teacher_updates'] == teacher_version['updates']
        and value['continuation_rule'] == 'SAVED_DIRECT_THEN_FROZEN_FIRST_H2_TRUE_WORLD',
        'every continuation executes the actual immutable FIRST teacher and frozen true/model probabilities')
    raw, n, won = counts['new_raw_tiles'], counts['rollouts'], counts['won']
    environment = dict(sampled_transitions=raw, post_action_spawns=raw, raw_tile_productions=raw,
        environment_random_draws=2*raw, ground_explicit_swipe_calls=raw,
        ground_state_status_calls=n+raw, ground_status_internal_swipe_calls=4*(n+raw-won),
        ground_swipe_calls=raw+4*(n+raw-won))
    require(Counter(value['environment_counts']) == Counter(environment),
        'only new executed continuation actions generate paid ground spawns, including WIN; saved initial spawns are reused')
    snapshots = 0
    linear = outcomes['actions'].reshape(-1)
    for index in set(range(min(8, n))) | set(range(max(0, n-8), n)):
        h2 = max(0, int(linear[index])-1)
        snapshots += h2+int(h2 > 0)
    expected = dict(rollouts_started=n, reused_start_spawns=n, rollout_rng_starts=n,
        prescribed_direct_actions=counts['prescribed_direct_actions'], h2_choose_calls=counts['followup_h2_actions'],
        terminal_wins=won, terminal_losses=counts['lost'], action_cutoffs=counts['cutoffs'],
        trace_rows_written=raw, trace_uncompressed_bytes_written=32*raw,
        boundary_probe_snapshots=snapshots, boundary_probe_bytes_copied=440*snapshots)
    require(Counter(value['counts']) == Counter(expected), 'all actual prescribed/H2 actions, full traces and boundary snapshot copies are charged')
    planning_counts(value['planning_counts'], counts['followup_h2_actions'], depth=2)
    check_representation(value['representation_counts'], 'LOCAL_RISK', value['planning_counts'].get('value_predictions', 0))
    require(value['cpu_seconds'] >= 0. and value['seconds'] >= 0., 'actual continuation CPU includes native physics/planning and trace compression')


def calibration_stats(groups):
    """Independent scalar aggregation of actual paired members, not production inference."""
    names = ('reward', 'win', 'combined')
    teacher = [[(x['teacher_reward'], x['teacher_win'], x['teacher_reward']+8.*x['teacher_win'])
        for x in group['replicas']] for group in groups]
    actual = [[(x['actual_reward'], x['actual_win'], x['actual_reward']+8.*x['actual_win'])
        for x in group['replicas']] for group in groups]
    output = {key:{} for key in ('mean_teacher','mean_actual','signed_error','mean_absolute_error','rms_error','centered_replica_error_rms')}
    for component, name in enumerate(names):
        truth = [x[component] for group in actual for x in group]
        predicted = [x[component] for group in teacher for x in group]
        errors = [[p[component]-a[component] for p, a in zip(pg, ag)] for pg, ag in zip(teacher, actual)]
        flat = [x for group in errors for x in group]
        output['mean_teacher'][name] = mean(predicted); output['mean_actual'][name] = mean(truth)
        output['signed_error'][name] = mean(flat); output['mean_absolute_error'][name] = mean(abs(x) for x in flat)
        output['rms_error'][name] = mean(x*x for x in flat)**.5
        output['centered_replica_error_rms'][name] = mean((x-mean(group))**2 for group in errors for x in group)**.5
    return output


def interval_status(interval, difference):
    low, high = interval['ci95']
    if low > 0.: return 'SUPPORTED_MORE_OPTIMISTIC' if difference else 'SUPPORTED_OPTIMISTIC_BIAS'
    if high < 0.: return 'SUPPORTED_MORE_PESSIMISTIC' if difference else 'SUPPORTED_PESSIMISTIC_BIAS'
    return 'UNRESOLVED'


def check_interval(saved, values, difference):
    require(len(values) == 16 and close(saved['mean'], mean(values)), 'signed calibration interval preserves all sixteen actual lifecycle values')
    equal_tree(saved['lifecycle_values'], {str(i):x for i,x in enumerate(values)}, 'all positive, equal and adverse calibration lifecycle values remain present')
    equal_tree(saved['parent_mean_values'], {str(p):mean(values[p::4]) for p in range(4)}, 'all four fixed SOURCE groups retain paired calibration means')
    require(saved['positive_equal_negative'] == [sum(x > 0 for x in values), sum(x == 0 for x in values), sum(x < 0 for x in values)],
        'calibration directional counts do not omit adverse lifecycles')
    low, high = saved['ci95']; minimum = mean(min(values[p::4]) for p in range(4)); maximum = mean(max(values[p::4]) for p in range(4))
    require(minimum-1e-10 <= low <= high <= maximum+1e-10,
        'reported paired lifecycle interval stays within its realized fixed-parent bootstrap feasible range')
    require(saved['interval_scope'] == 'CONDITIONAL_ON_FOUR_FROZEN_PARENTS_AND_64_FIXED_EQUIDISTANT_V319_ROOTGROUPS'
        and saved['status95'] == interval_status(saved, difference), 'teacher bias interval retains its conditional scope and signed interpretation')


def check_analysis(summary, lives):
    cutoffs = []; records = []; cells = ('R1_A','R1_B','R2_A','R2_B')
    for row in lives:
        record = dict(lifecycle=row['lifecycle'], parent=row['parent'], cells={}, retained_endpoint_counts={})
        for number in ('1','2'):
            for task in TASKS:
                cell = 'R'+number+'_'+task; record['cells'][cell] = {}; record['retained_endpoint_counts'][cell] = {}
                for arm in ARMS:
                    groups = row['stages'][number][task]['arms'][arm]['groups']
                    count = sum(x['status'] == 'CUTOFF' for group in groups for x in group['replicas'])
                    record['retained_endpoint_counts'][cell][arm] = dict(rootgroups=GROUPS, replicas=GROUPS*REPLICAS, cutoff=count)
                    for group in groups:
                        for member, x in enumerate(group['replicas']):
                            if x['status'] == 'CUTOFF':
                                cutoffs.append(dict(lifecycle=row['lifecycle'], task=task, round=int(number),arm=arm,
                                    group_index=group['index'], member=member, seed=x['seed']))
                    record['cells'][cell][arm] = None if count else calibration_stats(groups)
        records.append(record)
    hold = bool(cutoffs)
    if hold:
        for record in records:
            record['cells'] = {cell:{arm:None for arm in ARMS} for cell in cells}
    equal_tree(summary['by_lifecycle'], records, 'all equal-weight root/member calibration moments and cutoff counts are the actual terminal data')
    require(summary['primary_contrast'] == 'QUERY_MINUS_FACTUAL_SIGNED_COMBINED_TEACHER_ERROR'
        and summary['cutoffs'] == cutoffs and summary['complete_terminal_endpoints'] == (not hold)
        and summary['physical_conditional_rollouts'] == 32768
        and summary['selected_group_indices'] == selected_groups().tolist() and summary['replicas_per_rootgroup'] == 4
        and summary['bootstrap_seed'] == 32000001 and summary['bootstrap_draws'] == 20000
        and summary['bootstrap_executed'] == (not hold)
        and summary['bootstrap_unit'] == 'PAIRED_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT',
        'the single fixed-grid calibration primary retains whole-cohort cutoff HOLD and paired lifecycle inference')
    views = ('primary','overall','by_task','by_round','by_stage')
    if hold:
        require(all(summary[name] is None for name in views) and summary['primary_status'] == 'HOLD_CUTOFF'
            and not summary['differential_teacher_bias_supported'], 'any cutoff suppresses all terminal-bias inference without deleting observations')
        return

    def view(value, selected):
        require(set(value['query_minus_factual']) == {'reward','win','combined'} and set(value['own_signed_bias']) == set(ARMS),
            'each prespecified view retains both own biases and the same three signed error components')
        for component in ('reward','win','combined'):
            biases = {arm:[mean(record['cells'][cell][arm]['signed_error'][component] for cell in selected) for record in records] for arm in ARMS}
            for arm in ARMS: check_interval(value['own_signed_bias'][arm][component], biases[arm], False)
            check_interval(value['query_minus_factual'][component], [q-f for q,f in zip(biases['QUERY_LOCAL'], biases['FACTUAL_LOCAL'])], True)

    view(summary['overall'], cells)
    require(set(summary['by_task']) == set(TASKS) and set(summary['by_round']) == {'1','2'} and set(summary['by_stage']) == set(cells),
        'all frozen secondary task, round and stage views remain explicit')
    for task in TASKS: view(summary['by_task'][task], ('R1_'+task,'R2_'+task))
    for number in ('1','2'): view(summary['by_round'][number], ('R'+number+'_A','R'+number+'_B'))
    for cell in cells: view(summary['by_stage'][cell], (cell,))
    equal_tree(summary['primary'], summary['overall']['query_minus_factual']['combined'], 'the primary uses the final overall signed combined teacher error difference')
    status = interval_status(summary['primary'], True)
    require(summary['primary_status'] == status and summary['differential_teacher_bias_supported'] == (status != 'UNRESOLVED'),
        'calibration detects optimism or pessimism and never relabels that diagnostic as learning improvement')
    require(summary['secondary_interval_scope'] == 'NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM'
        and 'No new fitting' in summary['evidence_scope'] and 'not an optimal-value error' in summary['evidence_scope'],
        'diagnostic calibration keeps its nominal secondary, policy-conditional and noncausal scientific scope')


def expected_configuration(source):
    return dict(schema='acfqp.teacher_calibration_freeze.v320', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[1]/'specs/TEACHER_CALIBRATION_V320.md'),
        lifecycles=list(range(16)),parents=4,workers=4,tasks=list(TASKS),arms=list(ARMS),rounds=[1,2],
        original_groups=OLD_GROUPS,groups=GROUPS,members=REPLICAS,selected_group_indices=selected_groups().tolist(),
        selection='PREDECLARED_COMMON_EQUIDISTANT_ORIGINAL_GROUP_POSITIONS',
        prefix_proposal='NOT_RUN_REPLACED_BEFORE_ACQUISITION_BY_EQUIDISTANT_DIAGNOSTIC_POSITIONS',
        teacher='ACTUAL_IMMUTABLE_V317_FIRST_LOCAL_V0',planning_belief='ACTUAL_IMMUTABLE_V319_FIRST_BANK_BELIEF',
        true_probabilities={'A':.1,'B':.5},targets='V319_SAVED_FIRST_ONE_STEP_DIRECT_R_AND_W',
        continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2',
        return_definition='PRESCRIBED_DIRECT_AND_LATER_REWARDS_EXCLUDING_ORIGINATING_ROOT_ACTION',
        spawn='NEW_SPAWN_AFTER_EVERY_EXECUTED_ACTION_INCLUDING_WIN',max_steps=8192,
        seed_continuation=320500000000,life_stride=10000000,task_stride=1000000,round_stride=100000,group_stride=4,
        seed_pairing='SAME_ORIGINAL_GROUP_MEMBER_SEEDS_BOTH_ARMS',expected_rollouts=32768,fit_updates=0,
        primary='QUERY_MINUS_FACTUAL_SIGNED_COMBINED_TEACHER_ERROR',bootstrap_draws=20000,bootstrap_seed=32000001,
        stop_rule='ANY_CUTOFF_WHOLE_COHORT_HOLD_NO_REPLACEMENT_OR_TERMINAL_WIN_IMPUTATION',
        evidence_scope='FIXED_EXISTING_FIRST_COHORT_AND_COMMON_POSITION_GRID_TEACHER_CALIBRATION_NOT_LEARNING_CAUSAL_TEST')


def check_lifecycle(row, old, source_weights, checkpoint):
    life, parent = row['lifecycle'], row['parent']; teachers = {}; counts = Counter()
    require(parent == life%4 == old['parent'] and life == old['lifecycle'], 'all reused FIRST lifecycles retain their actual frozen SOURCE parent')
    indices = selected_groups()
    for task in TASKS:
        first = row['initial'][task]; original = old['initial'][task]
        equal_tree(first, dict(teacher_version=original['head_version'], planning_belief=original['planning_belief']),
            'terminal continuations restore the actual old FIRST v0 and unchanged A/B planning belief')
        identity = dict(lifecycle=life,parent=parent,context_id=original['context_id'],arm='FIRST_LOCAL')
        teacher = HeadVersions(source_weights, checkpoint, identity, 'LOCAL_RISK'); teacher.apply(first['teacher_version']); teachers[task] = teacher
        require(row['head_setups'][task]['restored_version'] == first['teacher_version'], 'the worker restore receipt names the actual old FIRST head')
    for number in (1,2):
        for task in TASKS:
            stage = row['stages'][str(number)][task]; teacher = teachers[task]; first = row['initial'][task]
            require(stage['teacher_unchanged'] and stage['teacher_version'] == first['teacher_version'] and stage['groups'] == GROUPS
                and stage['replicas'] == REPLICAS and stage['selected_group_indices'] == indices.tolist(),
                'both arms use all members at the fixed common grid under the immutable teacher')
            require(set(stage['arms']) == set(ARMS), 'all stages preserve both diagnostic arms without selection')
            p_model = first['planning_belief']['estimated_p_four']; p_true = .1 if task=='A' else .5
            seeds = np.asarray([[continuation_seed(life,task,number,g,m) for m in range(REPLICAS)] for g in indices],dtype=np.uint64)
            for arm in ARMS:
                item = stage['arms'][arm]; receipt = old['rounds'][str(number)][task]['arms'][arm]['supervision']['group_artifact']
                equal_tree(item['source_group_artifact'], receipt, 'selected starts and original one-step labels retain their audited V319 artifact receipt')
                read = item['source_read']; selected_names = ('roots','spawn_cells','spawn_ranks','selected_action','targetkind','targetreward','targetwin')
                path = Path(receipt['file'])
                require(path.stat().st_size == receipt['saved_bytes'], 'selected old V319 group file retains its actual saved physical size')
                with np.load(path,allow_pickle=False) as saved:
                    require(set(saved.files) == set(GROUP_FIELDS)|{'metadata_json'}, 'selected prior artifact retains its already audited group schema')
                    equal_tree(json.loads(str(saved['metadata_json'])),receipt['metadata'],'selected prior root and target data retain the audited V319 ownership')
                    data = {key:saved[key][indices] for key in selected_names}
                require(read['file'] == receipt['file'] and read['source_file_bytes'] == receipt['saved_bytes'] and read['new_raw_tiles'] == 0
                    and read['selected_array_bytes'] == sum(data[key].nbytes for key in selected_names),
                    'reading retained selected roots and starts acquires no new raw and reports source file size and actual selected-array bytes')
                metadata = dict(schema='acfqp.teacher_calibration_outcome.v320', lifecycle=life,parent=parent,task=task,round=number,
                    arm=arm,groups=GROUPS,members=REPLICAS,selected_group_indices=indices.tolist(),source_group_file=receipt['file'],
                    teacher_version=first['teacher_version'],p_model=p_model,p_true=p_true,max_steps=8192,
                    return_definition='PRESCRIBED_DIRECT_AND_LATER_REWARDS_EXCLUDING_ORIGINATING_ROOT_ACTION',
                    continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2')
                outcomes = artifact_arrays(item['outcome_artifact'], DENSE_FIELDS, metadata)
                require(outcomes['original_group_indices'].dtype == np.int64 and np.array_equal(outcomes['original_group_indices'], indices)
                    and np.array_equal(outcomes['rollout_seeds'], seeds), 'new outcomes retain every frozen original position and paired member seed')
                native = item['continuation']; trace = native['trace_artifact']; path = Path(trace['file'])
                require(trace['columns'] == TRACE_COLUMNS and trace['dtype'] == 'int32'
                    and trace['packing_rule'] == 'GROUP_MEMBER_CHRONOLOGICAL_EXECUTED_ACTIONS'
                    and not trace['reused_start_spawn_included'] and trace['all_new_spawns_included']
                    and path.stat().st_size == trace['compressed_bytes'], 'all executed actions retain compact complete new-spawn trace storage')
                with np.load(path, allow_pickle=False) as saved:
                    require(saved.files == ['moves'], 'compact continuation trace stores only its actual physical rows')
                    moves = saved['moves']
                require(len(moves) == trace['rows'] and moves.nbytes == trace['uncompressed_bytes'], 'actual compressed and uncompressed trace bytes reconcile recorded rows')
                reward, win, physical, expected_probes = check_continuations(moves, data['roots'],data['spawn_cells'],data['spawn_ranks'],
                    data['selected_action'],data['targetkind'],seeds,outcomes,p_true)
                check_continuation_work(native, physical, outcomes, first['teacher_version'],p_model,p_true)
                counts['literal_first_H2_boundary_probes'] += check_probes(native['boundary_probes'],expected_probes,teacher,p_model)
                groups = []
                for local, index in enumerate(indices):
                    replicas = []
                    for member in range(REPLICAS):
                        status = int(outcomes['status'][local,member]); hold = not status
                        replicas.append(dict(teacher_reward=float(data['targetreward'][local,member]),teacher_win=float(data['targetwin'][local,member]),
                            actual_reward=None if hold else float(reward[local,member]), actual_win=None if hold else int(win[local,member]),
                            status={1:'WON',-1:'LOST',0:'CUTOFF'}[status],seed=int(seeds[local,member]),
                            score=int(outcomes['scores'][local,member]),actions=int(outcomes['actions'][local,member]),
                            new_raw_tiles=int(outcomes['new_raw_tiles'][local,member])))
                    groups.append(dict(index=int(index),replicas=replicas))
                equal_tree(item['groups'],groups, 'every JSON diagnostic member retains its actual old target and independently replayed terminal or null cutoff truth')
                counts.update(physical); counts.update(group_files_read=1,trace_files=1,outcome_files=1,
                    new_trace_array_bytes=moves.nbytes,new_outcome_array_bytes=item['outcome_artifact']['array_bytes'])
    return counts


def check_accounting(document, previous, inherited, physical, execution):
    account = document['accounting']; expected_arms = {}
    for arm in ARMS:
        cells = [row['stages'][number][task]['arms'][arm] for row in document['by_lifecycle'] for number in ('1','2') for task in TASKS]
        replicas = [x for cell in cells for group in cell['groups'] for x in group['replicas']]
        expected_arms[arm] = dict(rollouts=len(replicas),new_raw_tiles=sum(x['new_raw_tiles'] for x in replicas),
            reused_first_spawns=len(replicas),actions=sum(x['actions'] for x in replicas),
            terminal_counts={status:sum(x['status']==status for x in replicas) for status in ('WON','LOST','CUTOFF')},
            environment_counts=sum_counts(c['continuation']['environment_counts'] for c in cells),
            planning_counts=sum_counts(c['continuation']['planning_counts'] for c in cells),
            representation_counts=sum_counts(c['continuation']['representation_counts'] for c in cells),
            continuation_counts=sum_counts(c['continuation']['counts'] for c in cells),
            source_files_read=len(cells),source_file_bytes_referenced=sum(c['source_read']['source_file_bytes'] for c in cells),
            source_read_cpu_seconds=sum(c['source_read']['cpu_seconds'] for c in cells),
            continuation_cpu_seconds=sum(c['continuation']['cpu_seconds'] for c in cells),
            trace_files=len(cells),trace_saved_bytes=sum(c['continuation']['trace_artifact']['compressed_bytes'] for c in cells),
            outcome_files=len(cells),outcome_saved_bytes=sum(c['outcome_artifact']['saved_bytes'] for c in cells))
    equal_tree(account['per_arm'],expected_arms,'all variable-length continuations, read/trace/outcome bytes and actual arm work are charged')
    require(account['new_raw_tiles'] == physical['new_raw_tiles'] == sum(a['new_raw_tiles'] for a in expected_arms.values())
        and account['rollouts'] == account['reused_first_spawns'] == 32768
        and account['fit_updates'] == 0 and not account['source_training_repeated'] and not account['first_adaptation_repeated']
        and not account['prior_full_audit_repeated'], 'only new terminal diagnostic continuations incur acquisition; no learning or old source work is manufactured')
    worker = sum(row['cpu_seconds'] for row in document['parent_receipts']); compiler = sum(row['compiler_cpu_seconds'] for row in document['parent_receipts'])
    require(close(account['worker_cpu_seconds'],worker) and close(account['compiler_cpu_seconds'],compiler)
        and close(account['new_calibration_component_cpu_seconds'],worker+compiler+account['coordinator_cpu_seconds'])
        and close(account['inherited_successful_source_v317_v319_full_cpu_seconds'],inherited)
        and close(account['economic_source_v317_v319_and_calibration_component_cpu_seconds'],inherited+account['new_calibration_component_cpu_seconds']),
        'successful SOURCE/V317/V319 cost is inherited once and actual read/setup/rollout/IO/compiler/coordinator components are closed')
    require(execution['exit_code'] == 0
        and execution['process_tree_cpu_seconds']+1e-6 >= account['new_calibration_component_cpu_seconds'],
        'the completed original process-tree receipt includes final summary serialization and shutdown beyond producer components')


def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    require(document['schema'] == 'acfqp.teacher_calibration.v320' and document['status'] in ('DIAGNOSTIC_COMPLETE','HOLD_CUTOFF')
        and document['scientific_gate'] == 'TEACHER_CALIBRATION_NOT_LEARNING_OR_U006_GATE', 'terminal V320 receipt preserves its diagnostic scientific scope')
    source_path = Path(document['source_summary']).resolve(); previous = json_file(source_path)
    prior = json_file(source_path.parent/'audit.json'); prior_execution = json_file(source_path.parent/'audit_execution.json')
    require(previous['schema'] == 'acfqp.query_supervision.v319' and previous['status'] == 'EXPERIMENT_COMPLETE'
        and prior['status'] == 'PASS' and prior['independent_valid'] and prior_execution['exit_code'] == 0,
        'terminal calibration reuses the already audited complete V319 roots and labels without another old full audit')
    config = expected_configuration(source_path)
    equal_tree(json_file(directory/'configuration.json'),config,'all diagnostic grid, policy, reward, seeds, primary and horizon are frozen before new acquisition')
    equal_tree(document['settings'],config,'the terminal receipt retains exactly the frozen diagnostic settings')
    equal_tree(document['source_provenance'],previous['source_provenance'],'four actual SOURCE parents are unchanged inherited evidence')
    lives = document['by_lifecycle']; old = {row['lifecycle']:row for row in previous['by_lifecycle']}
    require([row['lifecycle'] for row in lives] == list(range(16)) and [row['parent'] for row in document['parent_receipts']] == list(range(4)),
        'all sixteen original FIRST lives and all four parent workers remain present without selection')
    sources = {row['parent']:row for row in previous['source_provenance']['parents']}; weights = {}; physical = Counter()
    for row in lives:
        source = sources[row['parent']]
        if row['parent'] not in weights: weights[row['parent']] = read_source_weights(source['checkpoint'])
        physical.update(check_lifecycle(row,old[row['lifecycle']],weights[row['parent']],source['checkpoint']))
        print(json.dumps(dict(event='independent_teacher_calibration_life_checked',lifecycle=row['lifecycle'])),flush=True)
    check_analysis(document['summary'],lives)
    require(document['status'] == ('HOLD_CUTOFF' if physical['cutoffs'] else 'DIAGNOSTIC_COMPLETE'), 'any retained cutoff holds the entire terminal calibration conclusion')
    execution = json_file(directory/'execution.json'); inherited = json_file(source_path.parent/'audit_costs.json')['full_economic_source_v317_and_experiment_cpu_seconds']
    require((directory/'stderr.log').stat().st_size == 0, 'original completed continuation acquisition has empty stderr')
    check_accounting(document,previous,inherited,physical,execution)
    return dict(status='PASS',independent_valid=True,prior_v319_audit_status=prior['status'],prior_full_audit_repeated=False,
        lifecycles=16,fixed_source_parents=4,selected_group_indices=selected_groups().tolist(),**dict(physical),
        every_new_physical_swipe_spawn_rng_and_endpoint_checked=True,prescribed_saved_direct_actions_valid=True,
        frozen_FIRST_versions_beliefs_and_boundary_H2_probes_valid=True,all_paired_group_and_terminal_calibration_moments_valid=True,
        complete_terminal_endpoints=not physical['cutoffs'],primary_status=document['summary']['primary_status'],
        new_calibration_component_cpu_seconds=document['accounting']['new_calibration_component_cpu_seconds'],
        new_calibration_full_cpu_seconds=execution['process_tree_cpu_seconds'],full_economic_source_v317_v319_and_calibration_cpu_seconds=inherited+execution['process_tree_cpu_seconds'],
        limitations='Calibration is conditional on the fixed 64-position grid, retained FIRST cohort and prescribed DIRECT-then-FIRST-H2 policy. '
            'All newly paid physics and outcomes are replayed independently; actual H2 teacher actions are checked at fixed first/last rollout boundary probes. '
            'Old source/V319 audits, all H2 decisions, continuations and bootstrap draws are not rerun. '
            'Intervals are checked against actual lifecycle vectors, directional counts and feasible fixed-parent ranges. '
            'The diagnostic establishes no learning improvement or causal explanation of V319 loss; historical dynamics and failed-attempt CPU remain unknown.',errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.output)
    except (ValueError, KeyError, FileNotFoundError, IndexError) as error:
        result = dict(status='FAIL', independent_valid=False, errors=[str(error)])
    (args.output/'audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['independent_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
