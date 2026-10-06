from fractions import Fraction as F

from acfqp.science import joint_gap_v230 as gap
from acfqp.science import joint_witness_v230 as primal


def fixture():
    counts = ({'DELIVERY': 36, 'LOST': 4},
              {'DELIVERY': 34, 'LOST': 1, 'RECOVERY': 5},
              {'DELIVERY': 12, 'LOST': 28})
    regions = {op: [gap.region(row, 720)] for op, row in zip(gap.OPERATORS, counts)}
    kernel = {op: {cat: F(value, sum(row.values())) for cat, value in row.items()}
              for op, row in zip(gap.OPERATORS, counts)}
    return regions, kernel


def test_known_feasible_counterexample_and_exact_membership():
    # Detects an invalid accepted witness or a mismatched route gap.
    regions, kernel = fixture()
    assert primal.verify_kernel(regions, kernel)['valid']
    answer = primal.witness(dict(operating='high', retry_cost='17/20'),
                            regions, 'goal', 'WAIT', kernel)
    assert answer['valid'] and answer['found']
    assert answer['regret'] > F(1, 20)
    assert primal.verify_kernel(regions, answer['kernel'])['valid']
    wrong = {op: dict(row) for op,row in kernel.items()}
    wrong[gap.OPERATORS[0]] = {'DELIVERY': F(0), 'LOST': F(1)}
    assert not primal.verify_kernel(regions, wrong)['valid']


def test_optimizer_must_return_verified_full_kernel():
    # True point is optimal for goal, yet its confidence region admits a
    # different winning policy. A dual upper alone would not establish this.
    regions, kernel = fixture()
    vectors = gap.route.vectors(dict(operating='high', retry_cost='17/20'), kernel)
    selected = max(gap.POLICIES, key=lambda p: primal._utility(vectors[p], gap.WEIGHTS['goal']))
    answer = primal.witness(dict(operating='high', retry_cost='17/20'),
                            regions, 'goal', selected, kernel)
    assert answer['found'] and answer['valid']
    assert primal.verify_kernel(regions, answer['kernel'])['valid']
    actual = gap.route.vectors(dict(operating='high', retry_cost='17/20'), answer['kernel'])
    difference = (primal._utility(actual[answer['alternative_policy']],gap.WEIGHTS['goal'])
                  -primal._utility(actual[selected],gap.WEIGHTS['goal']))
    assert difference == answer['regret'] > F(1, 20)
