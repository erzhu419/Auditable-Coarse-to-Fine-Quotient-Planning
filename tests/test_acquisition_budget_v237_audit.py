from fractions import Fraction as F

from scripts import audit_acquisition_budget_v237 as audit


def test_row_information_uses_true_to_bad_kl_direction():
    truth, bad = {'YES': F(9, 10), 'NO': F(1, 10)}, {'YES': F(1, 2), 'NO': F(1, 2)}
    forward, backward = audit.categorical_kl(truth, bad), audit.categorical_kl(bad, truth)
    assert forward[1] < backward[0]


def test_best_row_information_is_an_optimistic_adaptive_budget_rate():
    truth = {'S': {'D': F(3, 4), 'L': F(1, 4)},
             'D_FULL': {'D': F(1, 2), 'R': F(1, 4), 'L': F(1, 4)}}
    bad = {'S': {'D': F(1, 2), 'L': F(1, 2)},
           'D_FULL': {'D': F(1, 4), 'R': F(1, 4), 'L': F(1, 2)}}
    rows, maximum = audit.maximum_row_information(truth, bad)
    assert rows['D_FULL'][0] > rows['S'][1]
    assert maximum == rows['D_FULL']


def test_power_upper_requires_a_valid_outer_kl_witness():
    assert audit.valid_power_upper(F(3, 4), F(1, 4), 1, F(1, 10))
    assert not audit.valid_power_upper(F(3, 10), F(1, 4), 1, F(1, 10))
    assert audit.valid_power_upper(F(1), F(1, 4), 100, F(1, 10))


def test_batch_ceiling_changes_cap_not_expected_samples():
    expected = F(65, 2)
    assert audit.cap_batches(expected) == 48
    assert expected == F(65, 2)
