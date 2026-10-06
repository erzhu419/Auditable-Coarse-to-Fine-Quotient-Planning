from fractions import Fraction as F
from math import prod

from acfqp.science import joint_query_evidence_v235 as joint
from acfqp.science import life_end_query_evidence_v238 as conditional
from acfqp.science import source_predictive_evidence_v236 as predictive


def test_source_384_with_no_validation_can_certify_only_when_source_evidence_is_retained():
    training = {operator: [] for operator in joint.OPERATORS}
    training[joint.S] = ['DELIVERY']*310+['LOST']*74
    validation = {operator: [] for operator in joint.OPERATORS}
    case = {'operating': 'low', 'retry_cost': '17/20'}
    retained = joint.certificate(training, case, 'goal', 'SHORT', 'WAIT')
    discarded = conditional.certificate(training, validation, case, 'goal', 'SHORT', 'WAIT')
    assert retained['projected_counts'] == {'S': {'DELIVERY': 310, 'LOST': 74}}
    assert retained['certified'] and retained['log_e_lower'] > retained['log_threshold_upper']
    assert discarded['validation_counts'] == {'S': {'DELIVERY': 0, 'LOST': 0}}
    assert discarded['log_predictive_lower'] == 0 and not discarded['certified']
    # With zero validation, the conditional region includes even this bad
    # alternative. Source outcomes can rule it out in the joint region.
    bad = {'S': {'DELIVERY': F(0), 'LOST': F(1)}}
    assert predictive.membership(discarded['training_counts'], discarded['validation_counts'], bad)['exact_inside']
    assert joint.gap(case, 'goal', 'SHORT', 'WAIT', bad) > F(1, 20)
    assert joint.membership(retained['projected_counts'], bad)['excluded']


def test_source_times_posterior_predictive_exactly_recovers_joint_evidence_for_a_and_b_rows():
    # A sources have 384 entries per row. In this supported B scope, the
    # changed S row trains on 128 B entries; unchanged rows train on A's384
    # and include the 128 B-source entries among their validation evidence.
    a_training = {'S': {'DELIVERY': 310, 'LOST': 74},
        'D_FULL': {'DELIVERY': 270, 'RECOVERY': 80, 'LOST': 34},
        'R': {'DELIVERY': 296, 'LOST': 88}}
    a_validation = {'S': {'DELIVERY': 80, 'LOST': 16},
        'D_FULL': {'DELIVERY': 64, 'RECOVERY': 25, 'LOST': 7},
        'R': {'DELIVERY': 75, 'LOST': 21}}
    b_training = dict(a_training, S={'DELIVERY': 49, 'LOST': 79})
    b_validation = {'S': {'DELIVERY': 31, 'LOST': 33},
        'D_FULL': {'DELIVERY': 130, 'RECOVERY': 45, 'LOST': 17},
        'R': {'DELIVERY': 103, 'LOST': 25}}
    probabilities = {'S': {'DELIVERY': F(4, 5), 'LOST': F(1, 5)},
        'D_FULL': {'DELIVERY': F(7, 10), 'RECOVERY': F(1, 5), 'LOST': F(1, 10)},
        'R': {'DELIVERY': F(3, 4), 'LOST': F(1, 4)}}

    def mixture(counts):
        return prod(joint.mixture_normalizer(tuple(row.values())) for row in counts.values())

    def likelihood(counts):
        return prod(probabilities[name][category]**count
                    for name, row in counts.items() for category, count in row.items())

    for source, validation in ((a_training, a_validation), (b_training, b_validation)):
        combined = {name: {category: source[name][category]+count for category, count in row.items()}
                    for name, row in validation.items()}
        source_evidence = mixture(source)/likelihood(source)
        predictive_evidence = predictive._predictive(source, validation)/likelihood(validation)
        joint_evidence = mixture(combined)/likelihood(combined)
        assert predictive._predictive(source, validation) == mixture(combined)/mixture(source)
        assert source_evidence*predictive_evidence == joint_evidence
