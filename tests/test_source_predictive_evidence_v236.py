from fractions import Fraction as F
from itertools import product

from acfqp.science import source_predictive_evidence_v236 as core


def tape(context):
    result = dict(case={'context': context}, changed_operator=core.OPERATORS[0],
                  operators={}, provenance={})
    for number, operator in enumerate(core.OPERATORS):
        if context == 'A':
            blocks = [('source', 'A', 0, 384, number*24),
                      ('target', 'A', 4, 16, 100+number),
                      ('target', 'A', 54, 16, 400+number)]
        elif operator == result['changed_operator']:
            blocks = [('source', 'B', 27, 128, 200+number*8),
                      ('target', 'B', 30, 16, 300+number)]
        else:
            blocks = [('source', 'A', 0, 384, number*24),
                      ('target', 'A', 4, 16, 100+number),
                      ('source', 'B', 27, 128, 200+number*8),
                      ('target', 'B', 30, 16, 300+number)]
        observations, segments = [], []
        for kind, source_context, index, amount, order in blocks:
            for offset in range(0, amount, 16):
                start = len(observations)
                observations.extend(core.ALPHABETS[operator][i % len(core.ALPHABETS[operator])]
                                    for i in range(offset, offset+16))
                segments.append(dict(kind=kind, context=source_context, index=index,
                    operator=operator, queue_start=start, queue_end=start+16,
                    draw_start=offset, draw_end=offset+16, availability_order=order+offset//16))
        result['operators'][operator], result['provenance'][operator] = observations, segments
    return result


def test_a_return_keeps_a_sources_in_training_and_all_targets_in_validation():
    original = tape('A')
    split = core.split_tape(original)
    for operator in core.OPERATORS:
        assert len(split['training'][operator]) == 384
        assert len(split['validation'][operator]) == 32
        assert {s['index'] for s in split['validation_segments'][operator]} == {4, 54}
        assert all(s['kind'] == 'source' and s['context'] == 'A'
                   for s in split['training_segments'][operator])
        assert split['training'][operator]+split['validation'][operator] == original['operators'][operator]


def test_b_unchanged_sources_enter_validation_once_and_changed_rows_train_only_on_b():
    original = tape('B')
    split = core.split_tape(original)
    changed = original['changed_operator']
    assert len(split['training'][changed]) == 128
    assert len(split['validation'][changed]) == 16
    assert all(s['context'] == 'B' for s in split['training_segments'][changed])
    for operator in core.OPERATORS[1:]:
        assert len(split['training'][operator]) == 384
        assert len(split['validation'][operator]) == 160
        assert {(s['kind'], s['context']) for s in split['validation_segments'][operator]} == {
            ('target', 'A'), ('source', 'B'), ('target', 'B')}
    for operator in core.OPERATORS:
        segments = split['training_segments'][operator]+split['validation_segments'][operator]
        assert sorted(s['queue_start'] for s in segments) == list(range(0, len(original['operators'][operator]), 16))
        assert len(split['training'][operator])+len(split['validation'][operator]) == len(original['operators'][operator])
        assert split['training'][operator]+split['validation'][operator] == original['operators'][operator]


def test_conditional_mixture_equals_independent_training_initialized_prediction():
    for dimension, trained in ((2, (3, 5)), (3, (3, 5, 2))):
        for sequence in product(range(dimension), repeat=4):
            current, validated, predictive = list(trained), [0]*dimension, F(1)
            for category in sequence:
                predictive *= F(2*current[category]+1, 2*sum(current)+dimension)
                current[category] += 1
                validated[category] += 1
            assert core.predictive_normalizer(trained, validated) == predictive
            assert predictive*core.mixture_normalizer(trained) == core.mixture_normalizer(tuple(current))


def test_training_outcomes_never_enter_membership_likelihood_and_boundary_is_retained():
    trained = {'S': {'DELIVERY': 384, 'LOST': 0}}
    validated = {'S': {'DELIVERY': 0, 'LOST': 16}}
    parameter = {'S': {'DELIVERY': F(0), 'LOST': F(1)}}
    # This parameter gives zero training likelihood but validation likelihood 1.
    member = core.membership(trained, validated, parameter)
    assert member['exact_inside'] and member['log_lr_upper'] != 'Infinity'
    no_validation = {'S': {'DELIVERY': 0, 'LOST': 0}}
    boundary = core.membership(trained, no_validation, parameter, threshold=1)
    assert boundary['exact_inside'] and boundary['log_lr_lower'] == boundary['log_lr_upper'] == '0'
    assert core.membership(trained, validated, {'S': {'DELIVERY': F(1), 'LOST': F(0)}})['excluded']


def test_coarsened_source_prior_is_binary_and_validation_mle_bounds_predictive():
    split = core.split_tape(tape('B'))
    trained = core.project_counts(split['training'], 'D_REC_R')
    validated = core.project_counts(split['validation'], 'D_REC_R')
    assert list(trained['D_REC']) == ['RECOVERY', 'OTHER']
    binary = core.predictive_normalizer(tuple(trained['D_REC'].values()), tuple(validated['D_REC'].values()))
    combined = tuple(s+t for s, t in zip(trained['D_REC'].values(), validated['D_REC'].values()))
    assert binary == core.mixture_normalizer(combined)/core.mixture_normalizer(tuple(trained['D_REC'].values()))
    mle = {name: {category: F(count, sum(row.values())) for category, count in row.items()}
           for name, row in validated.items()}
    assert core.membership(trained, validated, mle, threshold=1)['exact_inside']


def test_observed_geometry_preserves_joint_conditional_identity_and_validation_kl():
    trained = {'S': {'DELIVERY': 3, 'LOST': 1}}
    validated = {'S': {'DELIVERY': 1, 'LOST': 1}}
    parameters = {'S': {'DELIVERY': F(1, 2), 'LOST': F(1, 2)}}
    result = core.observed_geometry(trained, validated, parameters)
    assert result['exact_joint_equals_training_times_conditional']
    assert result['log_validation_mle_minus_log_bad'] == {'lower': '0', 'upper': '0'}
    assert result['per_row_kl_validation_to_bad']['S']['kl_lower'] == '0'
    member = core.membership(trained, validated, parameters)
    assert result['log_lr_conditional'] == {'lower': member['log_lr_lower'], 'upper': member['log_lr_upper']}
    joint, training, conditional = (result[key] for key in ('log_lr_joint', 'log_lr_training', 'log_lr_conditional'))
    assert F(joint['lower'])-F(training['upper']) <= F(conditional['upper'])
    assert F(joint['upper'])-F(training['lower']) >= F(conditional['lower'])
