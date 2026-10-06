#!/usr/bin/env python3
"""Independent retained WIN-target, root-prediction and terminal-continuation reader."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from statistics import mean

import numpy as np

from verify_closed_loop_v313 import (HeadVersions, close, equal_tree, json_file,
    read_source_weights, require, sum_counts)
from verify_greedy_targets_v317 import feature_addresses, predict_components
from verify_query_supervision_v319 import GROUP_FIELDS, artifact_arrays
from verify_teacher_calibration_v320 import (TRACE_COLUMNS, DENSE_FIELDS,
    check_continuations, check_continuation_work, check_probes)

TASKS = ('A', 'B')
ARMS = ('FACTUAL_WIN', 'QUERY_WIN')
PREDICTIONS = ('FIRST', 'before', 'after', 'FINAL')
SNAPSHOTS = ('FIRST', 'v1', 'v2')
GROUPS, MEMBERS, OLD_GROUPS = 64, 4, 16384
INTERVAL_SCOPE = 'CONDITIONAL_ON_FOUR_FROZEN_SOURCE_PARENTS_AND_64_FIXED_EQUIDISTANT_V324_ROOTGROUPS'


def selected_groups():
    return np.linspace(0, OLD_GROUPS-1, GROUPS, dtype=np.int64)


def continuation_seed(life, task, number, original_group, member):
    return 325500000000+life*10000000+TASKS.index(task)*1000000+number*100000+int(original_group)*4+member


def restore_chain(source_weights, checkpoint, identity, versions):
    head = HeadVersions(source_weights, checkpoint, identity, 'LOCAL_RISK')
    first_reward = None
    for version in versions:
        head.apply(version)
        if first_reward is None:
            first_reward = head.reward.copy()
        require(np.array_equal(head.reward, first_reward),
            'every restored complete WIN-only reward table equals its actual FIRST table')
    return head


def literal_root_predictions(roots, head):
    reward, probability = predict_components(roots, head)
    addresses = feature_addresses(roots)
    logit = np.zeros(len(roots), dtype=np.float64)
    for occurrence in range(32):
        logit += head.terminal[addresses[:, occurrence]]
    return dict(reward=reward, win=probability, logit=logit,
        combined=reward+8.*(probability-.5))


def check_root_predictions(arrays, heads):
    roots = arrays['roots']
    require(roots.dtype == np.int32 and roots.shape == (GROUPS, 16),
        'root predictions retain all exact selected physical roots')
    for key in ('prediction_probabilities', 'prediction_logits'):
        require(arrays[key].dtype == np.float64 and arrays[key].shape == (3, GROUPS),
            'all three unique immutable root snapshots retain exact float64 grids')
    for index, label in enumerate(SNAPSHOTS):
        expected = literal_root_predictions(roots, heads[label])
        require(np.array_equal(arrays['prediction_probabilities'][index], expected['win'])
            and np.array_equal(arrays['prediction_logits'][index], expected['logit']),
            'each native root component is its literal actual immutable head prediction')


def check_prediction_work(value, version):
    n = GROUPS
    require(value['roots'] == n and value['updates_before'] == value['updates_after'] == version['updates']
        and value['readonly'] and value['prediction_rule'] == 'ACTUAL_V301_NATIVE_COMPONENT_PREDICTOR_UNCHANGED_STABLE_SIGMOID',
        'root prediction reads its declared actual frozen version without a fit')
    expected = dict(win_predictions=n, reward_predictions=n, win_table_lookups=32*n,
        reward_table_lookups=32*n, feature_extractions=n, feature_occurrences=32*n,
        feature_digit_reads=192*n, feature_address_multiply_adds=192*n, fit_updates=0, parameter_writes=0)
    require(Counter(value['counts']) == Counter(expected),
        'existing native root API charges actual WIN and reward reads without uncharged fitting')
    require(Counter(value['representation_counts']) == Counter(risk_sigmoid_evaluations=n,
        local_risk_table_lookups=32*n, combined_value_additions=2*n, combined_value_multiplications=n),
        'actual root native sigmoid and combined-value operations are counted')
    require(value['cpu_seconds'] >= 0. and value['seconds'] >= 0.,
        'all saved-root prediction CPU and wall work remain explicit')


def scalar_moments(groups):
    """Equal members within roots, then equal roots; teacher member labels stay distinct."""
    output = {}
    for label in PREDICTIONS:
        residuals = [group['predictions'][label]-member['actual_win']
            for group in groups for member in group['replicas']]
        output[label] = dict(mean_probability=mean(group['predictions'][label] for group in groups),
            signed_bias=mean(residuals), brier=mean(x*x for x in residuals))
    teacher_errors = [member['teacher_win']-member['actual_win']
        for group in groups for member in group['replicas']]
    teacher = dict(mean_probability=mean(member['teacher_win']
        for group in groups for member in group['replicas']),
        signed_bias=mean(teacher_errors), brier=mean(x*x for x in teacher_errors))
    changes = {metric:{left+'_minus_'+right:output[left][metric]-output[right][metric]
        for left, right in (('after','before'), ('FINAL','FIRST'))} for metric in ('brier','signed_bias')}
    return dict(root_prediction=output, member_teacher=teacher,
        terminal_win_rate=mean(member['actual_win'] for group in groups for member in group['replicas']),
        root_brier_change=changes['brier'], root_signed_bias_change=changes['signed_bias'])


def check_interval(saved, values, kind=None):
    require(len(values) == 16 and close(saved['mean'], mean(values)),
        'terminal interval preserves all sixteen actual equal-weight lifecycle values')
    equal_tree(saved['lifecycle_values'], {str(i):value for i, value in enumerate(values)},
        'all favorable equal and adverse terminal-diagnostic lifecycles remain present')
    equal_tree(saved['parent_mean_values'], {str(p):mean(values[p::4]) for p in range(4)},
        'all four frozen SOURCE parents retain their actual paired diagnostic means')
    require(saved['positive_equal_negative'] == [sum(x > 0 for x in values),
        sum(x == 0 for x in values), sum(x < 0 for x in values)],
        'diagnostic direction counts do not omit adverse lifecycle values')
    low, high = saved['ci95']
    minimum = mean(min(values[p::4]) for p in range(4))
    maximum = mean(max(values[p::4]) for p in range(4))
    require(minimum-1e-10 <= low <= high <= maximum+1e-10,
        'terminal interval stays within its actual fixed-parent bootstrap feasible range')
    require(saved['interval_scope'] == INTERVAL_SCOPE
        and (kind is None or saved['status95'] == interval_status(low, high, kind)),
        'diagnostic interval retains its frozen scope and direction interpretation')


def interval_status(low, high, kind):
    if kind == 'brier_change':
        return 'SUPPORTED_WORSE_PREDICTION' if low > 0 else 'SUPPORTED_BETTER_PREDICTION' if high < 0 else 'UNRESOLVED'
    if kind == 'bias':
        return 'SUPPORTED_OPTIMISTIC_BIAS' if low > 0 else 'SUPPORTED_PESSIMISTIC_BIAS' if high < 0 else 'UNRESOLVED'
    return 'SUPPORTED_MORE_OPTIMISTIC' if low > 0 else 'SUPPORTED_MORE_PESSIMISTIC' if high < 0 else 'UNRESOLVED'


def check_analysis(saved, lives):
    cells = ('R1_A', 'R1_B', 'R2_A', 'R2_B')
    cutoffs, records = [], []
    for row in lives:
        record = dict(lifecycle=row['lifecycle'], parent=row['parent'], cells={}, retained_endpoint_counts={})
        for number in ('1', '2'):
            for task in TASKS:
                cell = 'R'+number+'_'+task
                record['cells'][cell], record['retained_endpoint_counts'][cell] = {}, {}
                for arm in ARMS:
                    groups = row['stages'][number][task]['arms'][arm]['groups']
                    replicas = [member for group in groups for member in group['replicas']]
                    count = {status:sum(member['status'] == status for member in replicas)
                        for status in ('WON', 'LOST', 'CUTOFF')}
                    record['retained_endpoint_counts'][cell][arm] = dict(rootgroups=GROUPS, replicas=GROUPS*MEMBERS, **count)
                    for group in groups:
                        for member, item in enumerate(group['replicas']):
                            if item['status'] == 'CUTOFF':
                                cutoffs.append(dict(lifecycle=row['lifecycle'], task=task, round=int(number),
                                    arm=arm, group_index=group['index'], member=member, seed=item['seed']))
                    record['cells'][cell][arm] = None if count['CUTOFF'] else scalar_moments(groups)
        records.append(record)
    hold = bool(cutoffs)
    if hold:
        for record in records:
            record['cells'] = {cell:{arm:None for arm in ARMS} for cell in cells}
    equal_tree(saved['by_lifecycle'], records,
        'all root Brier and member-target moments use the actual equal-weight terminal observations separately')
    require(saved['primary_contrast'] == 'FINAL_QUERY_WIN_MINUS_FIRST_BRIER_ON_QUERY_ROOTS'
        and saved['cutoffs'] == cutoffs and saved['complete_terminal_endpoints'] == (not hold)
        and saved['physical_conditional_rollouts'] == 32768
        and saved['selected_group_indices'] == selected_groups().tolist() and saved['replicas_per_rootgroup'] == 4
        and saved['bootstrap_seed'] == 32500001 and saved['bootstrap_draws'] == 20000
        and saved['bootstrap_executed'] == (not hold)
        and saved['bootstrap_unit'] == 'PAIRED_EXISTING_V324_TARGET_LEARNING_LIFECYCLE_WITHIN_EACH_FIXED_SOURCE_PARENT'
        and saved['estimator'] == 'EQUAL_TASKS_THEN_ROUNDS_THEN_ROOTGROUPS_THEN_MEMBERS_THEN_LIFECYCLES',
        'the sole frozen root-prediction primary retains all terminal labels and whole-cohort cutoff HOLD')
    if hold:
        require(all(saved[key] is None for key in ('primary','overall','by_task','by_round','by_stage'))
            and saved['primary_status'] == 'HOLD_CUTOFF' and not saved['updated_prediction_worse_supported']
            and not saved['updated_prediction_better_supported'],
            'any cutoff suppresses every terminal statistic without imputed truth or inference')
        return

    def view(value, selected):
        require(set(value) == {'root_prediction','member_teacher','root_brier_change','root_signed_bias_change','terminal_win_rate'},
            'all views keep root predictions and conditional member teacher targets distinct')

        def check(path, saved_interval, kind=None):
            values = []
            for record in records:
                items = []
                for cell in selected:
                    item = record['cells'][cell][arm]
                    for key in path:
                        item = item[key]
                    items.append(item)
                values.append(mean(items))
            check_interval(saved_interval, values, kind)

        for arm in ARMS:
            for label in PREDICTIONS:
                for metric in ('mean_probability','signed_bias','brier'):
                    check(('root_prediction',label,metric), value['root_prediction'][arm][label][metric],
                        'bias' if metric == 'signed_bias' else None)
            for metric in ('mean_probability','signed_bias','brier'):
                check(('member_teacher',metric), value['member_teacher'][arm][metric],
                    'bias' if metric == 'signed_bias' else None)
            for key, kind in (('root_brier_change','brier_change'), ('root_signed_bias_change','bias_change')):
                for contrast in ('after_minus_before','FINAL_minus_FIRST'):
                    check((key,contrast), value[key][arm][contrast], kind)
            check(('terminal_win_rate',), value['terminal_win_rate'][arm])

    view(saved['overall'], cells)
    require(set(saved['by_task']) == set(TASKS) and set(saved['by_round']) == {'1','2'}
        and set(saved['by_stage']) == set(cells), 'all frozen secondary task round and stage views remain present')
    for task in TASKS:
        view(saved['by_task'][task], ('R1_'+task,'R2_'+task))
    for number in ('1','2'):
        view(saved['by_round'][number], ('R'+number+'_A','R'+number+'_B'))
    for cell in cells:
        view(saved['by_stage'][cell], (cell,))
    equal_tree(saved['primary'], saved['overall']['root_brier_change']['QUERY_WIN']['FINAL_minus_FIRST'],
        'the primary compares FINAL QUERY and its own FIRST on the same QUERY roots and terminal member labels')
    status = interval_status(*saved['primary']['ci95'], 'brier_change')
    require(saved['primary_status'] == status
        and saved['updated_prediction_worse_supported'] == (status == 'SUPPORTED_WORSE_PREDICTION')
        and saved['updated_prediction_better_supported'] == (status == 'SUPPORTED_BETTER_PREDICTION'),
        'lower Brier means better prediction without relabeling this fixed-policy diagnostic as learning benefit')
    require(saved['secondary_interval_scope'] == 'NOMINAL_95_PERCENT_DESCRIPTIVE_SECONDARY_NO_MULTIPLICITY_CLAIM'
        and 'Root prediction error and conditional' in saved['evidence_scope']
        and 'not ' in saved['evidence_scope'] and 'No new fits' in saved['evidence_scope'],
        'terminal calibration preserves separate teacher/root information and its diagnostic scientific scope')


def check_cell(item, receipt, heads, versions, seeds, metadata, probability, true_probability, number):
    indices = selected_groups()
    equal_tree(item['source_group_artifact'], receipt,
        'selected starts and original member WIN targets retain their actual audited V324 group receipt')
    names = ('roots','spawn_cells','spawn_ranks','selected_action','targetkind','targetreward','targetwin')
    path = Path(receipt['file'])
    require(path.stat().st_size == receipt['saved_bytes'],
        'retained V324 roots and member labels retain their actual saved physical size')
    with np.load(path, allow_pickle=False) as saved:
        require(set(saved.files) == set(GROUP_FIELDS)|{'metadata_json'},
            'retained actual group source preserves its already audited array schema')
        equal_tree(json.loads(str(saved['metadata_json'])), receipt['metadata'],
            'retained old root/member arrays have their audited V324 ownership')
        data = {name:saved[name][indices] for name in names}
    read = item['source_read']
    require(read['file'] == receipt['file'] and read['source_file_bytes'] == receipt['saved_bytes']
        and read['selected_array_bytes'] == sum(data[name].nbytes for name in names)
        and read['new_raw_tiles'] == 0 and read['cpu_seconds'] >= 0. and read['wall_seconds'] >= 0.,
        'selected old-array reading reports actual bytes and CPU while acquiring no new raw')
    outcomes = artifact_arrays(item['outcome_artifact'],
        (*DENSE_FIELDS,'prediction_probabilities','prediction_logits'), metadata)
    require(outcomes['original_group_indices'].dtype == np.int64
        and np.array_equal(outcomes['original_group_indices'], indices)
        and np.array_equal(outcomes['rollout_seeds'], seeds),
        'every terminal continuation retains the frozen old position and new paired member seed')
    check_root_predictions(dict(outcomes, roots=data['roots']), heads)
    require(set(item['prediction_receipts']) == set(SNAPSHOTS),
        'each root distribution predicts only the three unique actual saved snapshots')
    for label, version in zip(SNAPSHOTS, versions):
        check_prediction_work(item['prediction_receipts'][label], version)
    native = item['continuation']; trace = native['trace_artifact']; path = Path(trace['file'])
    require(trace['columns'] == TRACE_COLUMNS and trace['dtype'] == 'int32'
        and trace['packing_rule'] == 'GROUP_MEMBER_CHRONOLOGICAL_EXECUTED_ACTIONS'
        and not trace['reused_start_spawn_included'] and trace['all_new_spawns_included']
        and path.stat().st_size == trace['compressed_bytes'],
        'every newly paid physical action and spawn remains in its complete compact trace')
    with np.load(path, allow_pickle=False) as saved:
        require(saved.files == ['moves'], 'complete trace contains only the actual chronological physical rows')
        moves = saved['moves']
    require(len(moves) == trace['rows'] and moves.nbytes == trace['uncompressed_bytes'],
        'all retained chronological trace rows reconcile compressed and uncompressed bytes')
    reward, win, physical, probes = check_continuations(moves, data['roots'],data['spawn_cells'],data['spawn_ranks'],
        data['selected_action'],data['targetkind'],seeds,outcomes,true_probability)
    check_continuation_work(native, physical, outcomes, versions[0],probability,true_probability)
    physical['literal_first_H2_boundary_probes'] += check_probes(native['boundary_probes'],probes,heads['FIRST'],probability)
    groups = []
    for local, index in enumerate(indices):
        replicas = []
        for member in range(MEMBERS):
            status = int(outcomes['status'][local,member]); hold = status == 0
            replicas.append(dict(teacher_reward=float(data['targetreward'][local,member]),
                teacher_win=float(data['targetwin'][local,member]), actual_reward=None if hold else float(reward[local,member]),
                actual_win=None if hold else int(win[local,member]),status={1:'WON',-1:'LOST',0:'CUTOFF'}[status],
                seed=int(seeds[local,member]),score=int(outcomes['scores'][local,member]),
                actions=int(outcomes['actions'][local,member]),new_raw_tiles=int(outcomes['new_raw_tiles'][local,member])))
        groups.append(dict(index=int(index),predictions={label:float(outcomes['prediction_probabilities'][position,local])
            for label, position in zip(PREDICTIONS,(0,number-1,number,2))},replicas=replicas))
    equal_tree(item['groups'],groups,
        'all JSON root predictions and original teacher targets use the same independently replayed terminal members')
    physical.update(group_files_read=1,trace_files=1,outcome_files=1,root_predictions=3*GROUPS,
        new_trace_array_bytes=moves.nbytes,new_outcome_array_bytes=item['outcome_artifact']['array_bytes'])
    return physical


def expected_configuration(source):
    return dict(schema='acfqp.win_terminal_freeze.v325', source_summary=str(Path(source).resolve()),
        protocol=str(Path(__file__).resolve().parents[1]/'specs/WIN_TERMINAL_V325.md'),
        lifecycles=list(range(16)),parents=4,workers=4,tasks=list(TASKS),arms=list(ARMS),rounds=[1,2],
        original_groups=OLD_GROUPS,groups=GROUPS,members=MEMBERS,selected_group_indices=selected_groups().tolist(),
        selection='PREDECLARED_COMMON_EQUIDISTANT_ORIGINAL_GROUP_POSITIONS',
        teacher='ACTUAL_IMMUTABLE_V324_FIRST_LOCAL_V0',planning_belief='ACTUAL_IMMUTABLE_V324_FIRST_BANK_BELIEF',
        true_probabilities={'A':.1,'B':.5},targets='V324_SAVED_FIRST_ONE_STEP_DIRECT_WIN',
        continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2',
        prediction='ACTUAL_V301_NATIVE_COMPONENT_PREDICTOR_UNCHANGED_STABLE_SIGMOID',
        prediction_snapshots=list(SNAPSHOTS),prediction_reads='THREE_UNIQUE_SNAPSHOTS_PER_CELL_BEFORE_AFTER_FINAL_ALIASES',
        own_versions='SOURCE_THEN_ACTUAL_FIRST_V0_THEN_OWN_WIN_V1_THEN_V2_REWARD_UNCHANGED',
        terminal_truth='COMMON_FROZEN_FIRST_POLICY_MEMBER_WIN_NOT_UPDATED_POLICY_VALUE',
        return_definition='PRESCRIBED_DIRECT_AND_LATER_REWARDS_EXCLUDING_ORIGINATING_ROOT_ACTION',
        spawn='NEW_SPAWN_AFTER_EVERY_EXECUTED_ACTION_INCLUDING_WIN',max_steps=8192,
        seed_continuation=325500000000,life_stride=10000000,task_stride=1000000,round_stride=100000,group_stride=4,
        seed_pairing='SAME_ORIGINAL_GROUP_MEMBER_SEEDS_BOTH_ARMS',expected_rollouts=32768,fit_updates=0,
        primary='FINAL_QUERY_WIN_MINUS_FIRST_BRIER_ON_QUERY_ROOTS',primary_direction='LOWER_IS_BETTER',
        bootstrap_draws=20000,bootstrap_seed=32500001,
        stop_rule='ANY_CUTOFF_WHOLE_COHORT_HOLD_NO_REPLACEMENT_OR_TERMINAL_WIN_IMPUTATION',
        evidence_scope='FIXED_V324_TRAINING_ROOTS_FRESH_SUFFIXES_FIRST_POLICY_PREDICTION_DIAGNOSTIC_NOT_LEARNING_CAUSAL_TEST')


def check_lifecycle(row, old, source_weights, checkpoint):
    life, parent = row['lifecycle'], row['parent']; counts = Counter()
    require(life == old['lifecycle'] and parent == old['parent'] == life%4,
        'every retained V324 learning history belongs to its actual fixed SOURCE parent')
    for task in TASKS:
        original, initial = old['initial'][task], row['initial'][task]
        version = original['head_version']; setup = row['head_setups'][task]
        equal_tree(initial, dict(teacher_version=version,planning_belief=original['planning_belief']),
            'both root distributions retain their actual FIRST teacher and immutable A/B bank belief')
        require(setup['FIRST']['restored_version'] == version
            and setup['FIRST']['restore_cpu_seconds'] >= 0.,
            'the FIRST restore receipt names its actual unchanged initial teacher version')
        identity = dict(lifecycle=life,parent=parent,context_id=original['context_id'])
        first = restore_chain(source_weights,checkpoint,dict(identity,arm='FIRST_LOCAL'),[version])
        probability = initial['planning_belief']['estimated_p_four']; true_probability = .1 if task == 'A' else .5
        require(set(setup['arms']) == set(ARMS), 'all actual WIN learner restore chains remain present')
        for arm in ARMS:
            versions = [version]+[old['rounds'][str(number)][task]['arms'][arm]['head_version'] for number in (1,2)]
            v1 = restore_chain(source_weights,checkpoint,dict(identity,arm=arm),versions[:2])
            v2 = restore_chain(source_weights,checkpoint,dict(identity,arm=arm),versions)
            # Complete reward equality was proved while reading every chain; share the immutable table thereafter.
            v1.reward = v2.reward = first.reward
            heads = dict(FIRST=first,v1=v1,v2=v2)
            delta = setup['arms'][arm]['delta_restores']
            require(len(delta) == 2 and [receipt['file'] for receipt in delta] == [value['file'] for value in versions[1:]]
                and all(receipt['cpu_seconds'] >= 0. and receipt['wall_seconds'] >= 0. for receipt in delta),
                'each actual private learner restores its own v1 and v2 once without a fit')
            for number in (1,2):
                stage = row['stages'][str(number)][task]
                require(stage['teacher_version'] == version and stage['teacher_unchanged']
                    and stage['groups'] == GROUPS and stage['replicas'] == MEMBERS
                    and stage['selected_group_indices'] == selected_groups().tolist() and set(stage['arms']) == set(ARMS),
                    'all stages retain the frozen teacher and complete paired fixed root/member grid')
                item = stage['arms'][arm]
                expected_versions = dict(FIRST=version,before=versions[number-1],after=versions[number],FINAL=versions[2])
                equal_tree(item['prediction_versions'], expected_versions,
                    'before after and FINAL probabilities read their actual saved own-arm checkpoints')
                seeds = np.asarray([[continuation_seed(life,task,number,group,member) for member in range(MEMBERS)]
                    for group in selected_groups()],dtype=np.uint64)
                receipt = old['rounds'][str(number)][task]['arms'][arm]['supervision']['group_artifact']
                metadata = dict(schema='acfqp.win_terminal_outcome.v325',lifecycle=life,parent=parent,task=task,round=number,
                    arm=arm,groups=GROUPS,members=MEMBERS,selected_group_indices=selected_groups().tolist(),
                    source_group_file=receipt['file'],teacher_version=version,prediction_snapshots=list(SNAPSHOTS),
                    prediction_versions=expected_versions,p_model=probability,p_true=true_probability,max_steps=8192,
                    return_definition='PRESCRIBED_DIRECT_AND_LATER_REWARDS_EXCLUDING_ORIGINATING_ROOT_ACTION',
                    continuation='SAVED_START_SPAWN_AND_PRESCRIBED_DIRECT_THEN_FROZEN_FIRST_H2')
                counts.update(check_cell(item,receipt,heads,versions,seeds,metadata,probability,true_probability,number))
            del heads, v1, v2
        del first
    return counts


def check_parent(source, lives, old):
    source_weights = read_source_weights(source['checkpoint']); counts = Counter()
    for row in lives:
        counts.update(check_lifecycle(row,old[row['lifecycle']],source_weights,source['checkpoint']))
        print(json.dumps(dict(event='independent_win_terminal_life_checked',lifecycle=row['lifecycle'])),flush=True)
    return counts


def check_accounting(document, inherited, physical, execution):
    account = document['accounting']; expected = {}
    for arm in ARMS:
        cells = [row['stages'][number][task]['arms'][arm] for row in document['by_lifecycle']
            for number in ('1','2') for task in TASKS]
        members = [item for cell in cells for group in cell['groups'] for item in group['replicas']]
        predictions = [item for cell in cells for item in cell['prediction_receipts'].values()]
        expected[arm] = dict(rollouts=len(members),new_raw_tiles=sum(item['new_raw_tiles'] for item in members),
            reused_first_spawns=len(members),actions=sum(item['actions'] for item in members),
            terminal_counts={status:sum(item['status']==status for item in members) for status in ('WON','LOST','CUTOFF')},
            environment_counts=sum_counts(cell['continuation']['environment_counts'] for cell in cells),
            planning_counts=sum_counts(cell['continuation']['planning_counts'] for cell in cells),
            representation_counts=sum_counts(cell['continuation']['representation_counts'] for cell in cells),
            continuation_counts=sum_counts(cell['continuation']['counts'] for cell in cells),source_files_read=len(cells),
            source_file_bytes_referenced=sum(cell['source_read']['source_file_bytes'] for cell in cells),
            source_read_cpu_seconds=sum(cell['source_read']['cpu_seconds'] for cell in cells),
            continuation_cpu_seconds=sum(cell['continuation']['cpu_seconds'] for cell in cells),
            prediction_counts=sum_counts(item['counts'] for item in predictions),
            prediction_representation_counts=sum_counts(item['representation_counts'] for item in predictions),
            prediction_cpu_seconds=sum(item['cpu_seconds'] for item in predictions),unique_snapshot_cells=len(predictions),
            trace_files=len(cells),trace_saved_bytes=sum(cell['continuation']['trace_artifact']['compressed_bytes'] for cell in cells),
            outcome_files=len(cells),outcome_saved_bytes=sum(cell['outcome_artifact']['saved_bytes'] for cell in cells))
    equal_tree(account['per_arm'],expected,
        'all actual root native reads terminal suffixes old-array reads trace/outcome files and CPU are charged once')
    require(account['new_raw_tiles'] == physical['new_raw_tiles'] == sum(value['new_raw_tiles'] for value in expected.values())
        and account['rollouts'] == account['reused_first_spawns'] == physical['rollouts'] == 32768
        and account['fit_updates'] == account['new_head_files'] == account['new_evaluation_games'] == 0
        and not account['source_training_repeated'] and not account['first_adaptation_repeated']
        and not account['prior_full_audit_repeated'],
        'only actual fresh diagnostic suffixes acquire raw while every saved first spawn and fit is reused')
    workers = sum(parent['cpu_seconds'] for parent in document['parent_receipts'])
    compilers = sum(parent['compiler_cpu_seconds'] for parent in document['parent_receipts'])
    component = workers+compilers+account['coordinator_cpu_seconds']
    require(close(account['worker_cpu_seconds'],workers) and close(account['compiler_cpu_seconds'],compilers)
        and close(account['new_calibration_component_cpu_seconds'],component)
        and close(account['inherited_successful_source_v324_full_cpu_seconds'],inherited)
        and close(account['economic_source_v324_and_calibration_component_cpu_seconds'],inherited+component)
        and execution['exit_code'] == 0 and execution['process_tree_cpu_seconds']+1e-6 >= component,
        'successful SOURCE/V324 CPU is inherited once and complete new execution includes final serialization/shutdown')


def audit(directory):
    directory = Path(directory).resolve(); document = json_file(directory/'summary.json')
    require(document['schema'] == 'acfqp.win_terminal.v325'
        and document['status'] in ('DIAGNOSTIC_COMPLETE','HOLD_CUTOFF')
        and document['scientific_gate'] == 'WIN_TERMINAL_CALIBRATION_NOT_LEARNING_OR_U006_GATE',
        'V325 preserves its terminal-prediction diagnostic scientific scope')
    source = Path(document['source_summary']).resolve(); previous = json_file(source)
    prior = json_file(source.parent/'audit.json'); prior_execution = json_file(source.parent/'audit_execution.json')
    require(previous['schema'] == 'acfqp.win_learning.v324' and previous['status'] == 'EXPERIMENT_COMPLETE'
        and prior['status'] == 'PASS' and prior['independent_valid'] and prior_execution['exit_code'] == 0,
        'V325 reads already independently audited actual V324 learning data without rerunning its audit')
    config = expected_configuration(source)
    equal_tree(json_file(directory/'configuration.json'),config,
        'the fixed root grid saved versions fresh streams sole Brier primary and cutoff rule were frozen before acquisition')
    equal_tree(document['settings'],config,'the completed terminal diagnostic preserves every frozen setting')
    equal_tree(document['source_provenance'],previous['source_provenance'],
        'all four actual SOURCE parents remain unchanged inherited evidence')
    lives = document['by_lifecycle']; old = {row['lifecycle']:row for row in previous['by_lifecycle']}
    require([row['lifecycle'] for row in lives] == list(range(16))
        and [row['parent'] for row in document['parent_receipts']] == list(range(4)),
        'all sixteen V324 histories and four parent workers remain present without selection')
    sources = {row['parent']:row for row in previous['source_provenance']['parents']}; physical = Counter()
    with ProcessPoolExecutor(max_workers=4) as pool:
        jobs = [pool.submit(check_parent,sources[parent],[row for row in lives if row['parent']==parent],old)
            for parent in range(4)]
        for job in as_completed(jobs):
            physical.update(job.result())
    check_analysis(document['summary'],lives)
    require(document['status'] == ('HOLD_CUTOFF' if physical['cutoffs'] else 'DIAGNOSTIC_COMPLETE'),
        'any actual retained cutoff holds the whole terminal diagnostic')
    execution = json_file(directory/'execution.json')
    inherited = json_file(source.parent/'audit_costs.json')['full_economic_source_and_experiment_cpu_seconds']
    require((directory/'stderr.log').stat().st_size == 0,
        'the completed original terminal producer has empty stderr')
    check_accounting(document,inherited,physical,execution)
    return dict(status='PASS',independent_valid=True,lifecycles=16,fixed_source_parents=4,**dict(physical),
        prior_v324_audit_status=prior['status'],prior_full_audit_repeated=False,
        every_new_physical_swipe_spawn_rng_and_endpoint_checked=True,
        prescribed_saved_direct_actions_and_frozen_FIRST_boundary_H2_probes_valid=True,
        complete_actual_FIRST_reward_invariance_both_own_WIN_chains_valid=True,
        all_actual_native_root_probabilities_logits_versions_and_paid_reads_valid=True,
        separate_root_prediction_and_member_teacher_terminal_moments_valid=True,
        complete_terminal_endpoints=not physical['cutoffs'],primary_status=document['summary']['primary_status'],
        new_calibration_component_cpu_seconds=document['accounting']['new_calibration_component_cpu_seconds'],
        new_calibration_full_cpu_seconds=execution['process_tree_cpu_seconds'],
        full_economic_source_v324_and_calibration_cpu_seconds=inherited+execution['process_tree_cpu_seconds'],
        limitations='All newly paid physical traces RNG and endpoints are independently replayed; all root probabilities/logits '
            'and complete unchanged reward tables are read literally. Actual FIRST H2 actions are checked at the fixed '
            'first/last continuation boundary probes. Old audits, every H2 action, fits, continuations and bootstrap draws '
            'are not rerun. Interval vectors counts scope and feasible fixed-parent range are checked. The fixed-grid '
            'existing-cohort FIRST-policy terminal diagnostic establishes no new learning utility or causal explanation; '
            'historical dynamics and failed-attempt CPU remain unknown.',errors=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('directory',type=Path)
    args = parser.parse_args(); result = audit(args.directory)
    (args.directory/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(event='independent_win_terminal_audit_complete',status=result['status'],
        primary_status=result['primary_status'])),flush=True)


if __name__ == '__main__':
    main()

