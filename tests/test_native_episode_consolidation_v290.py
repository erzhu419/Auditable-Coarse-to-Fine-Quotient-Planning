"""Literal V120-address references for the two fixed consolidation methods."""
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from acfqp.science.native_episode_consolidation_v290 import fit_consolidated, METHODS
from acfqp.science.controlled_predictive_ntuple_td_v120 import NtupleValue, ALPHA
from acfqp.science.controlled_predictive_online_query_td_v131 import QueryTD
from acfqp.science.controlled_predictive_paired_ntuple_v130 import QueryParent
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

BUILD = Path(__file__).resolve().parents[1] / 'reports/episode_consolidation_v290/runtime/tests'
QUERY = dict(reward_weight=1., failure_penalty=4., goal_bonus=4.)


def make_leaf(offset=False):
    rule = LearnedDynamics(RewriteProgram(True, 'equal', 1, 'once', 'output_value'),
        ((1,Fraction(9,10)), (2,Fraction(1,10))), 'uniform', 4)
    source = NtupleValue(rule, BUILD)
    source.weights[:] = np.arange(source.weights.size).reshape(source.weights.shape) % 11 * .001
    source_query = dict(reward_weight=1., failure_penalty=0., goal_bonus=0.) if offset else QUERY
    return QueryTD(QueryParent(source, source_query, QUERY, .25 if offset else .5), 'PRIOR', BUILD)


def dataset():
    return dict(afterstates=np.asarray([[2]+[0]*15,[2,1]+[0]*14,[1,2,1,2]*3+[2,1,2,0],
        [3,3]+[0]*14,[4]+[0]*15,[1,1]+[0]*14,[2,1]+[0]*14,
        [3,3]+[0]*14,[4]+[0]*15],dtype=np.int32),
        rewards=np.asarray([4,8,0,8,16,0,4,8,16],dtype=np.float64)/2048.,
        ends=np.asarray([3,5,7,9],dtype=np.int64),
        terminal_codes=np.asarray([-1,1,-1,1],dtype=np.int32),fit_game_count=3,fit_step_end=7)


def literal_fit(leaf, data, method):
    flat = leaf.weights.reshape(-1); start = 0
    examples, stats, masses = [], Counter(), []
    for game in range(data['fit_game_count']):
        end = int(data['ends'][game]); suffix = 4. if data['terminal_codes'][game] == 1 else -4.
        targets = {}
        for step in range(end-1,start-1,-1):
            targets[step] = suffix
            suffix += float(data['rewards'][step])
        features = {step:Counter(map(int,leaf.model.feature_indices(data['afterstates'][step])))
                    for step in range(start,end) if max(data['afterstates'][step]) < leaf.radix}
        denominators = Counter()
        for addresses in features.values():
            denominators.update(addresses)
        mass = {address:sum(row.get(address,0)/count for row in features.values())
                for address,count in denominators.items()}
        masses.append(mass)
        stats['samples'] += len(features)
        stats['sample_unique'] += sum(len(row) for row in features.values())
        stats['game_unique'] += len(denominators)
        stats['features'] += sum(sum(row.values()) for row in features.values())
        errors = {}
        gradients = {address:0. for address in denominators}
        for step,row in features.items():
            before = leaf.model.value(data['afterstates'][step])
            raw_target = targets[step]-leaf.offset
            error = raw_target-before
            examples.append(dict(episode=game,step=step,target=targets[step],raw_target=raw_target,
                                 error=error,raw_prediction_before_update=before))
            errors[step] = error
            if method == 'NORMALIZED_SEQUENTIAL_MC':
                for address,count in row.items():
                    flat[address] += ALPHA*count*error/denominators[address]
        if method == 'EPISODE_MEAN_MC':
            for step,row in features.items():
                for address,count in row.items():
                    gradients[address] += count*errors[step]
            for address,gradient in gradients.items():
                flat[address] += ALPHA*gradient/denominators[address]
        start = end
    return examples,stats,masses


@pytest.mark.parametrize('method', METHODS)
@pytest.mark.parametrize('offset', [False,True])
def test_native_weights_exactly_match_literal_actual_feature_reference(method,offset):
    actual, reference = make_leaf(offset), make_leaf(offset)
    data = dataset()
    result = fit_consolidated(actual,data,method,BUILD)
    examples,stats,masses = literal_fit(reference,data,method)
    np.testing.assert_array_equal(actual.weights,reference.weights)
    assert result['first_sample'] == examples[0] and result['last_sample'] == examples[-1]
    assert result['trained_afterstates'] == actual.updates == 6
    learning,work = result['learning_counts'],result['consolidation_counts']
    assert learning['td_updates'] == learning['value_predictions'] == stats['samples'] == 6
    assert learning['table_lookups'] == learning['table_update_occurrences'] == stats['features'] == 192
    writes = stats['sample_unique'] if method == METHODS[0] else stats['game_unique']
    assert learning['table_updates'] == work['parameter_write_events'] == writes
    assert work['feature_extractions'] == 6 and work['feature_occurrences'] == 192
    assert work['address_occurrence_count_visits'] == 192
    assert work['sample_unique_addresses'] == work['address_denominator_searches'] == stats['sample_unique']
    assert work['game_unique_addresses'] == stats['game_unique']
    assert work['normalization_divisions'] == writes
    assert result['target_counts']['skipped_winning_afterstates'] == 1
    assert result['target_counts']['suffix_reward_additions'] == 7
    assert result['target_counts']['raw_target_subtractions'] == 6
    assert result['first_sample']['target'] == -4.+8/2048.
    assert actual.counts['td_updates'] == actual.counts['inner_td_updates'] == 6
    assert actual.parent.source.updates == 0
    for mass in masses:
        assert all(value == pytest.approx(1.,abs=1e-15) for value in mass.values())
    if method == METHODS[0]:
        assert work['sample_parameter_commits'] == 6
        assert work.get('game_parameter_commits',0) == 0
        assert work.get('weighted_residual_accumulations',0) == 0
        assert work.get('error_buffer_doubles_peak',0) == 0
        assert work['parameter_update_multiplications'] == 2*writes
    else:
        assert work['game_parameter_commits'] == 3
        assert work.get('sample_parameter_commits',0) == 0
        assert work['weighted_residual_accumulations'] == stats['sample_unique']
        assert work['error_buffer_doubles_peak'] == 3
        assert work['parameter_update_multiplications'] == writes


def test_frozen_game_residuals_produce_a_different_table_than_current_residuals():
    sequential, mean = make_leaf(), make_leaf()
    data = dataset()
    seq = fit_consolidated(sequential,data,METHODS[0],BUILD)
    batched = fit_consolidated(mean,data,METHODS[1],BUILD)
    assert not np.array_equal(sequential.weights,mean.weights)
    assert seq['first_sample'] == batched['first_sample']
    assert seq['last_sample']['error'] != batched['last_sample']['error']
    assert seq['learning_counts']['table_updates'] > batched['learning_counts']['table_updates']


@pytest.mark.parametrize('method', METHODS)
def test_heldout_changes_do_not_enter_denominators_or_training(method):
    actual,reference = make_leaf(),make_leaf()
    first,second = dataset(),dataset()
    second['afterstates'][7:] = 0
    second['rewards'][7:] += 100.
    left = fit_consolidated(actual,first,method,BUILD)
    right = fit_consolidated(reference,second,method,BUILD)
    np.testing.assert_array_equal(actual.weights,reference.weights)
    assert left['first_sample'] == right['first_sample'] and left['last_sample'] == right['last_sample']
    assert left['learning_counts'] == right['learning_counts']
    assert left['consolidation_counts'] == right['consolidation_counts']
