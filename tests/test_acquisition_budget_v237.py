from decimal import Decimal, localcontext
from fractions import Fraction as F

from acfqp.science import acquisition_budget_v237 as core


def decimal(value):
    value = F(value)
    return Decimal(value.numerator)/Decimal(value.denominator)


def binary_kl(p, q):
    p, q = decimal(p), decimal(q)
    return p*(p/q).ln()+(1-p)*((1-p)/(1-q)).ln()


def rows():
    return ({'S': {'DELIVERY': F(3, 4), 'LOST': F(1, 4)}},
            {'S': {'DELIVERY': F(1, 4), 'LOST': F(3, 4)}})


def test_categorical_kl_outward_bounds_include_zero_true_probability():
    p = {'DELIVERY': F(3, 4), 'RECOVERY': F(0), 'LOST': F(1, 4)}
    q = {'DELIVERY': F(1, 4), 'RECOVERY': F(1, 4), 'LOST': F(1, 2)}
    lower, upper = core.categorical_kl_bounds(p, q)
    with localcontext() as context:
        context.prec = 160
        exact = decimal(F(3, 4))*Decimal(3).ln()+decimal(F(1, 4))*decimal(F(1, 2)).ln()
        assert decimal(lower) <= exact <= decimal(upper)
    assert core.categorical_kl_bounds(q, q) == (0, 0)


def test_e0_matches_independent_predictive_sequence_and_excludes_training_likelihood():
    training = {'S': {'DELIVERY': 3, 'LOST': 1},
                'D_FULL': {'DELIVERY': 2, 'RECOVERY': 1, 'LOST': 1}}
    validation = {'S': {'DELIVERY': 1, 'LOST': 1},
                  'D_FULL': {'DELIVERY': 1, 'RECOVERY': 0, 'LOST': 1}}
    parameters = {'S': {'DELIVERY': F(1, 3), 'LOST': F(2, 3)},
                  'D_FULL': {'DELIVERY': F(1, 2), 'RECOVERY': F(1, 3), 'LOST': F(1, 6)}}
    sequence = {'S': ('DELIVERY', 'LOST'), 'D_FULL': ('DELIVERY', 'LOST')}
    predictive, likelihood = F(1), F(1)
    for name, labels in sequence.items():
        current = dict(training[name])
        for label in labels:
            predictive *= F(2*current[label]+1, 2*sum(current.values())+len(current))
            current[label] += 1
            likelihood *= parameters[name][label]
    assert core.exact_e0(training, validation, parameters) == predictive/likelihood
    assert core.exact_e0({'S': {'DELIVERY': 384, 'LOST': 0}},
        {'S': {'DELIVERY': 0, 'LOST': 16}},
        {'S': {'DELIVERY': 0, 'LOST': 1}}) > 0


def test_expected_sample_lower_is_not_rounded_and_batch_cap_is_separate():
    p, q = rows()
    result = core.budget_bounds(120, p, q, budget=1)
    assert 1 < F(result['expected_samples_lower']) < 2
    assert result['required_batch_cap'] == 16 and result['budget_insufficient']
    with localcontext() as context:
        context.prec = 160
        exact = binary_kl(F(3, 4), F(1, 8))/binary_kl(F(3, 4), F(1, 4))
        lower = decimal(result['expected_samples_lower'])
        assert lower <= exact and exact-lower < Decimal('1e-70')


def test_power_upper_is_a_dyadic_excluded_boundary_with_a_legal_kl_bound():
    p, q = rows()
    result = core.budget_bounds(120, p, q, budget=1)
    upper = F(result['power_upper'])
    assert F(1, 8) < upper < F(3, 4)
    assert result['power_bisection_steps'] == 64 and (2**64) % upper.denominator == 0
    assert F(result['power_upper_kl_lower']) > F(result['information_budget_upper'])
    with localcontext() as context:
        context.prec = 160
        assert binary_kl(upper, F(1, 8)) > binary_kl(F(3, 4), F(1, 4))
    not_excluded = core.budget_bounds(120, p, q, budget=2)
    assert not not_excluded['budget_insufficient']
    assert F(not_excluded['power_upper']) > F(3, 4)


def test_no_information_and_zero_budget_do_not_create_positive_power():
    p, q = rows()
    equal = core.budget_bounds(96, q, q, budget=100)
    assert equal['expected_samples_lower'] == 'Infinity' and equal['required_batch_cap'] is None
    assert equal['budget_insufficient']
    zero = core.budget_bounds(96, p, q, budget=0)
    for result in (equal, zero):
        assert F(1, 10) <= F(result['power_upper']) <= F(1, 10)+F(1, 2**64)


def test_alpha_one_has_no_positive_information_requirement():
    p, q = rows()
    result = core.budget_bounds(960, p, q, budget=0)
    assert result['expected_samples_lower'] == '0' and result['required_batch_cap'] == 0
    assert not result['budget_insufficient'] and result['power_upper'] == '1'
    assert result['power_bisection_steps'] == 0
