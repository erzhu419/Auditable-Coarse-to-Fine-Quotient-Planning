from copy import deepcopy
from fractions import Fraction as F

from scripts import audit_source_predictive_evidence_v236 as audit


def b_tape():
    """B changed D has a B anchor; unchanged S/R inherit A history."""
    tape = dict(case={'context': 'B'}, changed_operator=audit.evidence.D,
                arm='ORACLE_GAP', operators={}, provenance={})
    for op in audit.OPERATORS:
        phases = [('source', 'B'), ('target', 'B')] if op == audit.evidence.D else [
            ('source', 'A'), ('target', 'A'), ('source', 'B'), ('target', 'B')]
        tape['operators'][op] = ['DELIVERY' if i % 2 == 0 else 'LOST' for i in range(len(phases))]
        tape['provenance'][op] = [dict(kind=kind, context=context, queue_start=i,
            queue_end=i+1, draw_start=0, draw_end=1, availability_order=i,
            **({'arm': tape['arm']} if kind == 'target' else {}))
            for i, (kind, context) in enumerate(phases)]
    return tape


def test_direct_posterior_prediction_matches_hand_conditionals():
    # Source (2,1) gives Beta(5/2,3/2): D then L has (5/8)*(3/10).
    assert audit.posterior_predictive((2, 1), (1, 1)) == F(3, 16)
    assert audit.posterior_predictive((2, 1, 0), (1, 0, 1)) == F(5, 99)


def test_source_counts_do_not_leak_back_into_validation_likelihood():
    values = audit.predictive_values({'S': {'DELIVERY': 2, 'LOST': 1}},
        {'S': {'DELIVERY': 1, 'LOST': 1}}, {'S': {'DELIVERY': '1/2', 'LOST': '1/2'}})
    assert values['validation_likelihood'] == F(1, 4)
    assert values['conditional_ratio'] == F(3, 4)
    assert values['joint_ratio'] == values['source_ratio']*values['conditional_ratio']


def test_audit_rejects_training_again_on_unchanged_b_source():
    split = audit.split_tape(b_tape())
    saved = {field: deepcopy(split[field]) for field in ('training_segments', 'validation_segments')}
    saved.update(training_lengths={op: len(values) for op, values in split['training'].items()},
                 validation_lengths={op: len(values) for op, values in split['validation'].items()})
    assert audit.saved_split_matches(saved, split)
    # The B source exists after inherited A validation and must stay validation.
    b_source = saved['validation_segments'][audit.evidence.S].pop(1)
    saved['training_segments'][audit.evidence.S].append(b_source)
    saved['training_lengths'][audit.evidence.S] += 1
    saved['validation_lengths'][audit.evidence.S] -= 1
    assert not audit.saved_split_matches(saved, split)


def test_changed_b_row_does_not_train_on_a_source():
    split = audit.split_tape(b_tape())
    assert [segment['context'] for segment in split['training_segments'][audit.evidence.D]] == ['B']
    assert [segment['context'] for segment in split['validation_segments'][audit.evidence.S]] == ['A', 'B', 'B']


def test_prior_independent_obstruction_uses_validation_mle_not_chosen_predictor():
    training = {'S': {'DELIVERY': 2, 'LOST': 1}}
    validation = {'S': {'DELIVERY': 1, 'LOST': 1}}
    near = audit.predictive_values(training, validation,
        {'S': {'DELIVERY': '1/2', 'LOST': '1/2'}})
    far = audit.predictive_values(training, validation,
        {'S': {'DELIVERY': '1/10000', 'LOST': '9999/10000'}})
    assert near['validation_mle'] == F(1, 4)
    assert near['prior_independent_mixture_obstruction']
    assert not far['prior_independent_mixture_obstruction']
