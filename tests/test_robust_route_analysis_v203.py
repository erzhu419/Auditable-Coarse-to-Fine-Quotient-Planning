"""Four synthetic fixtures; no retained data, producer or experiment runs."""
from copy import deepcopy
from fractions import Fraction
from itertools import combinations, product

from scripts import analyze_robust_route_planning_v203 as audit

F = Fraction


def test_rare_event_and_unobserved_intervals_retain_uncertainty():
    assert audit.interval(0, 0) == (F(0), F(1))
    lower, upper = audit.interval(0, 256)
    assert lower == 0 and F(1, 100) < upper < F(1, 20)
    assert 256 * audit.bernoulli_kl(0, float(upper)) >= audit.BETA - 1e-10
    left, right = audit.interval(256, 256)
    assert right == 1 and abs(left - (1 - upper)) <= F(1, audit.GRID)
    lower, upper = audit.interval(37, 128)
    assert lower < F(37, 128) < upper
    assert (lower * audit.GRID).denominator == (upper * audit.GRID).denominator == 1


def synthetic_tables():
    tables = {operator: [] for operator in audit.OPERATORS}
    for weather, lost in (('normal', 0), ('wet', 100)):
        case = dict(id='synthetic_' + weather, operating='low', retry_cost='17/20', weather=weather)
        tables['SHORT_PASS'].append(dict(context=case, counts=dict(DELIVERY=100 - lost, LOST=lost)))
    return tables


def test_shared_leaf_does_not_cover_unequal_members_or_unseen_context():
    tables = synthetic_tables(); first, second = (row['context'] for row in tables['SHORT_PASS'])
    normal = audit.make_envelopes(tables, first)
    wet = audit.make_envelopes(tables, second)
    pooled = audit.make_envelopes(tables, first, {operator: [] for operator in audit.OPERATORS})
    assert normal['SHORT_PASS']['bounds']['LOST'][1] < wet['SHORT_PASS']['bounds']['LOST'][0]
    assert pooled['SHORT_PASS']['n'] == 200 and normal['SHORT_PASS']['n'] == 100
    assert 0 < pooled['SHORT_PASS']['bounds']['LOST'][0] < pooled['SHORT_PASS']['bounds']['LOST'][1] < 1
    unseen = dict(first, operating='high')
    assert audit.make_envelopes(tables, unseen)['SHORT_PASS'] == dict(
        n=0, counts=dict(DELIVERY=0, LOST=0), bounds=dict(DELIVERY=(F(0), F(1)), LOST=(F(0), F(1))))
    assert audit.make_envelopes(tables, unseen, {operator: [] for operator in audit.OPERATORS})['SHORT_PASS']['n'] == 200


def fixture():
    envelopes = {
        'SHORT_PASS': dict(bounds=dict(DELIVERY=(F(7, 10), F(9, 10)), LOST=(F(1, 10), F(3, 10)))),
        'DETOUR_PASS': dict(bounds=dict(DELIVERY=(F(1, 2), F(7, 10)), LOST=(F(1, 20), F(1, 5)),
                                        RECOVERY=(F(1, 10), F(3, 10)))),
        'RECOVERY_RETRY': dict(bounds=dict(DELIVERY=(F(1, 5), F(2, 5)), LOST=(F(3, 5), F(4, 5))))}
    laws = {'SHORT_PASS': dict(DELIVERY=F(9, 10), LOST=F(1, 10)),
            'DETOUR_PASS': dict(DELIVERY=F(4, 5), LOST=F(1, 100), RECOVERY=F(19, 100)),
            'RECOVERY_RETRY': dict(DELIVERY=F(2, 5), LOST=F(3, 5))}
    pure = audit.vectors_from_laws(dict(operating='low', retry_cost='17/20'), laws)
    return envelopes, pure


def test_one_common_kernel_attains_all_mixture_risks_and_keeps_joint_point():
    envelopes, pure = fixture(); upper = audit.risks(envelopes)
    assert upper['SHORT'] == F(3, 10) and upper['DETOUR_RETURN'] == F(1, 5)
    assert upper['DETOUR_RETRY'] == F(11, 25)
    bounds = envelopes['DETOUR_PASS']['bounds']; names = sorted(bounds); vertices = set()
    for fixed in combinations(names, 2):
        remaining = next(name for name in names if name not in fixed)
        for endpoints in product(*(bounds[name] for name in fixed)):
            vertex = dict(zip(fixed, endpoints)); vertex[remaining] = 1 - sum(endpoints)
            if bounds[remaining][0] <= vertex[remaining] <= bounds[remaining][1]:
                vertices.add(tuple(vertex[name] for name in names))
    weights = dict(SHORT=F(3, 10), DETOUR_RETURN=F(1, 5), DETOUR_RETRY=F(2, 5), WAIT=F(1, 10))
    computed = sum(weights[name] * value for name, value in upper.items())
    explicit = max(weights['SHORT'] * F(3, 10) + (weights['DETOUR_RETURN'] + weights['DETOUR_RETRY']) * dict(zip(names, v))['LOST']
                   + weights['DETOUR_RETRY'] * dict(zip(names, v))['RECOVERY'] * F(4, 5) for v in vertices)
    assert computed == explicit
    chosen = audit.optimize(pure, upper)
    assert chosen['risk_upper'] <= audit.DELTA
    assert chosen['predicted'] == audit.joint(chosen['mix'], pure)
    assert chosen['predicted'][1] != chosen['risk_upper']


def test_changed_decision_or_true_joint_result_is_rejected():
    envelopes, pure = fixture(); expected = audit.optimize(pure, audit.risks(envelopes))
    saved = audit.exact_json(expected)
    assert audit.plan_matches(saved, expected)
    changed = deepcopy(saved); changed['mix'][0][1] = '1'
    assert not audit.plan_matches(changed, expected)
    laws = {'SHORT_PASS': dict(DELIVERY=F(4, 5), LOST=F(1, 5)),
            'DETOUR_PASS': dict(DELIVERY=F(3, 5), LOST=F(1, 10), RECOVERY=F(3, 10)),
            'RECOVERY_RETRY': dict(DELIVERY=F(3, 10), LOST=F(7, 10))}
    case = dict(operating='low', retry_cost='17/20')
    true_pure = audit.vectors_from_laws(case, laws)
    result = audit.score_mix(expected['mix'], true_pure, F(3), envelopes, laws)
    saved_result = deepcopy(result)
    assert audit.equal_numbers(saved_result, result)
    saved_result['actual_fractions'][1] = '0'
    assert not audit.equal_numbers(saved_result, result)
    assert result['coverage'] and F(result['actual_fractions'][1]) <= expected['risk_upper']
