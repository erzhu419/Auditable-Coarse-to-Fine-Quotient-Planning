"""Finite native replay trajectories and physical versus per-learner costs."""
from collections import Counter
from fractions import Fraction
import math
from pathlib import Path

import numpy as np
import pytest

from acfqp.science import terminal_win_run_v326 as driver
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram
from acfqp.science.native_split_risk_v301 import SplitLeaf

BUILD = Path(__file__).resolve().parents[1] / 'reports/terminal_win_v326/test_logs/native_runtime'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)
ROOTS = np.asarray([(1,) + (0,) * 15, (1,) + (0,) * 15,
    (1, 2, 0, 0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0)], dtype=np.int32)
TRUTH = np.asarray([[0., 1., 1., 1.], [1., 0., 0., 0.], [1., 1., 0., 1.]])
BOOTSTRAP = np.asarray([[.1, .2, .1, .2], [.4, .5, .4, .5], [.5, .6, .5, .6]])


def new_fixture():
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1, Fraction(9, 10)), (2, Fraction(1, 10))), 'uniform', 4)
    template = QueryTD(QueryParent(NtupleValue(rule, BUILD), QUERY, QUERY, .5), 'PRIOR', BUILD)
    template.freeze()
    teacher = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    index = np.arange(teacher.reward_weights.size).reshape(teacher.reward_weights.shape)
    teacher.reward_weights[:] = index % 7 * .003
    teacher.risk_weights[:] = -(index % 5) * .01
    teacher.updates = 7
    teacher.freeze()
    return template, teacher


def private(template, teacher):
    leaf = SplitLeaf(template, 'LOCAL_RISK', BUILD)
    np.copyto(leaf.reward_weights, teacher.reward_weights)
    np.copyto(leaf.risk_weights, teacher.risk_weights)
    leaf.updates = teacher.updates
    leaf.reward_weights.flags.writeable = False
    return leaf


def addresses(leaf, board):
    result = []
    for index, pattern in enumerate(leaf.model.patterns.reshape(-1, 6)):
        address = 0
        for cell in pattern:
            address = address * leaf.radix + int(board[cell])
        result.append((index // 8) * leaf.radix ** 6 + address)
    return result


def literal_replay(leaf, roots, targets):
    weights = leaf.risk_weights.reshape(-1).copy()
    samples = []
    for epoch in range(16):
        current = []
        for index, root in enumerate(roots):
            occurrences = addresses(leaf, root)
            logit = 0.
            for address in occurrences:
                logit += float(weights[address])
            if logit >= 0.:
                probability = 1. / (1. + math.exp(-logit))
            else:
                value = math.exp(logit)
                probability = value / (1. + value)
            target = sum(float(value) for value in targets[index]) / 4.
            error = target - probability
            current.append(dict(rootgroup=index, risk_target=target,
                risk_probability=probability, risk_error=error))
            for address, multiplicity in sorted(Counter(occurrences).items()):
                weights[address] += .0025 * (multiplicity * error) / multiplicity
        samples.append(current)
    return weights, samples


@pytest.fixture(scope='module')
def trained():
    template, teacher = new_fixture()
    leaf = private(template, teacher)
    expected, samples = literal_replay(leaf, ROOTS, TRUTH)
    teacher_before = (teacher.reward_weights.tobytes(), teacher.risk_weights.tobytes(), teacher.updates)
    result = driver.fit_replay(leaf, ROOTS, TRUTH, BUILD)
    return template, teacher, leaf, result, expected, samples, teacher_before


def test_sixteen_passes_match_literal_complete_win_table_and_current_predictions(trained):
    _, _, leaf, result, expected, samples, _ = trained
    np.testing.assert_array_equal(leaf.risk_weights.reshape(-1), expected)
    assert len(result['epoch_receipts']) == 16
    for receipt, current in zip(result['epoch_receipts'], samples):
        assert receipt['first_sample'] == current[0]
        assert receipt['last_sample'] == current[-1]
    assert samples[0][0]['risk_probability'] != samples[1][0]['risk_probability']
    assert samples[0][-1]['risk_probability'] != samples[-1][-1]['risk_probability']
    assert leaf.updates == 7 + 16 * len(ROOTS)


def test_replay_counts_distinguish_independent_roots_from_parameter_updates(trained):
    _, _, _, result, _, _, _ = trained
    assert result['distinct_rootgroups'] == 3
    assert result['epochs'] == 16 and result['fitted_rootgroups'] == 48
    assert result['replicates'] == 4 and result['alpha'] == .0025
    for field in ('learning_counts', 'normalization_counts', 'target_counts',
                  'representation_counts', 'setup_counts'):
        total = Counter()
        for receipt in result['epoch_receipts']:
            total.update(receipt[field])
        assert result[field] == dict(total)
    counts = result['learning_counts']
    assert counts['rootgroup_updates'] == counts['current_predictions'] == counts['win_predictions'] == 48
    assert counts['win_table_lookups'] == 48 * 32
    assert result['target_counts']['win_replica_reads'] == 48 * 8
    assert result['representation_counts']['risk_sigmoid_evaluations'] == 48
    assert not any('reward' in key for key in counts)


def test_bootstrap_and_binary_truth_change_private_win_without_reward_or_teacher_writes(trained):
    template, teacher, terminal, _, _, _, teacher_before = trained
    bootstrap = private(template, teacher)
    result = driver.fit_replay(bootstrap, ROOTS, BOOTSTRAP, BUILD)
    expected, _ = literal_replay(private(template, teacher), ROOTS, BOOTSTRAP)
    np.testing.assert_array_equal(bootstrap.risk_weights.reshape(-1), expected)
    assert not np.array_equal(bootstrap.risk_weights, terminal.risk_weights)
    for learner in (terminal, bootstrap):
        assert learner.reward_weights.tobytes() == teacher_before[0]
        assert not learner.reward_weights.flags.writeable
    assert (teacher.reward_weights.tobytes(), teacher.risk_weights.tobytes(), teacher.updates) == teacher_before
    assert not teacher.reward_weights.flags.writeable and not teacher.risk_weights.flags.writeable
    assert bootstrap.updates == terminal.updates and result['distinct_rootgroups'] == 3


def test_native_replay_keeps_supplied_root_order_instead_of_shuffling_or_merging(trained):
    template, teacher, terminal, _, _, _, _ = trained
    reversed_leaf = private(template, teacher)
    roots = np.ascontiguousarray(ROOTS[::-1])
    targets = np.ascontiguousarray(TRUTH[::-1])
    expected, samples = literal_replay(reversed_leaf, roots, targets)
    result = driver.fit_replay(reversed_leaf, roots, targets, BUILD)
    np.testing.assert_array_equal(reversed_leaf.risk_weights.reshape(-1), expected)
    assert not np.array_equal(reversed_leaf.risk_weights, terminal.risk_weights)
    assert result['distinct_rootgroups'] == 3  # The repeated board remains two independently sampled groups.
    assert result['epoch_receipts'][0]['first_sample'] == samples[0][0]


def test_frozen_protocol_has_1024_distinct_groups_four_members_and_16384_updates():
    settings = driver.configuration(BUILD / 'source_fixture.json')
    assert settings['groups_per_task_round'] == 1024
    assert settings['replicas_per_group'] == 4
    assert settings['epochs'] == 16 and settings['rootgroup_updates_per_arm_task_round'] == 16384
    assert settings['expected_shared_first_spawns'] == settings['expected_terminal_rollouts'] == 262144
    assert settings['expected_updates_per_arm'] == 1048576
    assert settings['target_fields'] == {'BOOTSTRAP_WIN': 'targetwin', 'TERMINAL_WIN': 'terminal_win'}
    assert settings['primary'] == 'TERMINAL_WIN_minus_FIRST_LOCAL_FINAL_AB'
    assert [driver.rollout_seed(5, 'B', 2, 3, member) for member in range(4)] == [
        3267000000000 + 50000000 + 1000000 + 200000 + 12 + member for member in range(4)]


def test_declared_seed_role_ranges_and_every_terminal_stage_are_disjoint():
    settings = driver.configuration(BUILD / 'source_fixture.json')
    intervals = []
    for life in settings['lifecycles']:
        for task in settings['tasks']:
            for number in settings['rounds']:
                intervals.append((driver.rollout_seed(life, task, number, 0, 0),
                    driver.rollout_seed(life, task, number, settings['groups_per_task_round'] - 1, 3)))
    intervals.sort()
    assert all(left[1] < right[0] for left, right in zip(intervals, intervals[1:]))
    assert all(end - start + 1 == 4096 for start, end in intervals)
    functions = {'seed_collection': driver.collection_seed, 'seed_selector': driver.selection_seed,
        'seed_ground': driver.draw_seed}
    role_ranges = [(intervals[0][0], intervals[-1][1])]
    for key, function in functions.items():
        seeds = [function(life, task, number) for life in settings['lifecycles']
            for task in settings['tasks'] for number in settings['rounds']]
        assert min(seeds) == settings[key] + 100000
        role_ranges.append((min(seeds), max(seeds)))
    role_ranges.append((driver.evaluation_seed(0, 'A', 0), driver.evaluation_seed(15, 'B', 63)))
    role_ranges.extend((settings[key], settings[key] + 15 * stride + 100000)
        for key, stride in (('seed_initial_warmup', 1000000), ('seed_initial_training', 10000000)))
    role_ranges.sort()
    assert all(left[1] < right[0] for left, right in zip(role_ranges, role_ranges[1:]))


def test_accounting_charges_shared_first_spawn_once_physically_and_suffix_only_to_terminal():
    endpoint = dict(game_summaries=[{'status': 'LOST'}], counts=dict(environment={}, planning={}), cpu_seconds=.2)
    version = dict(saved_bytes=5)
    fit = dict(distinct_rootgroups=2, fitted_rootgroups=32,
        learning_counts=dict(rootgroup_updates=32), normalization_counts={}, target_counts={},
        representation_counts={}, cpu_seconds=.1)
    stage = dict(collectors={'FIXED_FIRST': dict(acquisition=dict(cpu_seconds=.1))},
        census=dict(query=dict(counts={}, planning_counts={}, representation_counts={})),
        shared_supervision=dict(counts=dict(supervision_start_spawns=8),
            environment_counts=dict(raw_tile_productions=8), planning_counts={}, representation_counts={},
            cpu_seconds=.2, group_artifact=dict(saved_bytes=7)),
        continuation=dict(environment_counts=dict(raw_tile_productions=31),
            planning_counts={}, representation_counts={}, counts=dict(rollouts_started=8), cpu_seconds=.3,
            trace_artifact=dict(compressed_bytes=11), outcome_artifact=dict(saved_bytes=13)),
        terminal_status_counts=dict(WON=7, LOST=1, CUTOFF=0),
        arms={arm: dict(fit=fit, head_version=version, evaluations=endpoint) for arm in driver.UPDATING_ARMS})
    lives = [dict(initial={'A': dict(head_version=version,
        first_fits={'FIRST_LOCAL': dict(cpu_seconds=.1)}, acquisition=dict(cpu_seconds=.1),
        evaluations={'SOURCE': endpoint, 'FIRST_LOCAL': endpoint})}, rounds={'1': {'A': stage}})]
    parents = [dict(paid_factual_raw_tiles=18, paid_raw_by_phase={'A0': 11, 'A_R1': 7},
        cpu_seconds=1.1, compiler_cpu_seconds=.2, trace_bytes=17)]
    source = dict(source_training_raw_tiles=100, dynamics_raw_tiles=7,
        fresh_source_compute=dict(full_source_cpu_seconds=3.))
    result = driver.accounting(source, lives, parents, .4, 2.)
    assert result['new_initial_raw_tiles'] == 11 and result['new_post_factual_raw_tiles'] == 7
    assert result['shared_first_spawn_raw_tiles'] == 8 and result['additional_terminal_raw_tiles'] == 31
    assert result['new_training_raw_tiles'] == 18 + 8 + 31
    assert result['economic_training_raw_tiles_per_arm'] == dict(
        SOURCE=107, FIRST_LOCAL=118, BOOTSTRAP_WIN=133, TERMINAL_WIN=164)
    assert result['per_arm']['BOOTSTRAP_WIN']['additional_terminal_raw_tiles'] == 0
    assert result['per_arm']['TERMINAL_WIN']['additional_terminal_raw_tiles'] == 31
    for arm in driver.UPDATING_ARMS:
        assert result['per_arm'][arm]['economic_shared_first_spawn_raw_tiles'] == 8
        assert result['per_arm'][arm]['distinct_rootgroups'] == 2
        assert result['per_arm'][arm]['rootgroup_updates'] == 32
    assert result['new_evaluation_games'] == 4 and result['reused_evaluation_games'] == 0
    assert result['inherited_successful_source_full_cpu_seconds'] == 3.
    assert result['economic_source_and_experiment_component_cpu_seconds'] == pytest.approx(3. + 1.1 + .2 + .4)
    assert not result['old_target_data_reused'] and not result['source_training_repeated']
    assert not result['equal_total_raw_efficiency_test']
