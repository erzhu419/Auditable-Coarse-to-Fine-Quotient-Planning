from collections import Counter
from decimal import Decimal, localcontext
from fractions import Fraction as F
from itertools import combinations, product

from acfqp.science import joint_query_evidence_v235 as core
from scripts import probe_joint_query_evidence_v235 as runner


def test_exact_mixture_matches_independent_predictive_updates():
    for categories in (2, 3):
        for sequence in product(range(categories), repeat=5):
            counts, mixture = Counter(), F(1)
            for index, category in enumerate(sequence):
                mixture *= F(2*counts[category]+1, 2*index+categories)
                counts[category] += 1
            assert core.mixture_normalizer(tuple(counts[k] for k in range(categories))) == mixture


def test_canonical_families_cover_directions_without_extra_cost_events():
    expected = ('S', 'D_DEL', 'D_FULL_R', 'S_D_DEL', 'S_D_FULL_R', 'D_REC_R')
    for query in ('goal', 'risk'):
        for pair, name in zip(combinations(core.POLICIES, 2), expected):
            name = name.replace('D_DEL', 'D_FULL') if query == 'risk' else name
            assert core.canonical_family(query, *pair) == name
            assert core.canonical_family(query, *reversed(pair)) == name
    assert 2*3*len(core.FAMILIES) == 48
    assert F(48, core.THRESHOLD) == F(1, 20)


def test_projection_keeps_unequal_paid_rows_and_only_merges_needed_labels():
    rows = {core.S: ['DELIVERY', 'LOST'], core.D: ['DELIVERY', 'RECOVERY', 'LOST', 'RECOVERY'],
            core.R: ['DELIVERY']*7+['LOST']*3}
    shared = core.project_counts(rows, 'D_REC_R')
    assert shared == {'D_REC': {'RECOVERY': 2, 'OTHER': 2}, 'R': {'DELIVERY': 7, 'LOST': 3}}
    assert core.project_counts(rows, 'S_D_DEL') == {
        'S': {'DELIVERY': 1, 'LOST': 1}, 'D_DEL': {'DELIVERY': 1, 'OTHER': 3}}
    assert core.project_counts(rows, 'D_FULL')['D_FULL'] == {'DELIVERY': 1, 'RECOVERY': 2, 'LOST': 1}


def test_membership_exact_boundary_and_zero_likelihood():
    counts = {'S': {'DELIVERY': 0, 'LOST': 0}}
    parameters = {'S': {'DELIVERY': F(1, 3), 'LOST': F(2, 3)}}
    boundary = core.membership(counts, parameters, threshold=1)
    assert boundary['exact_inside'] and not boundary['excluded']
    assert boundary['log_lr_lower'] == boundary['log_lr_upper'] == '0'
    counts['S']['DELIVERY'] = 3
    parameters['S'] = {'DELIVERY': F(0), 'LOST': F(1)}
    excluded = core.membership(counts, parameters)
    assert excluded['excluded'] and excluded['log_lr_lower'] == 'Infinity'


def test_log_bounds_enclose_rational_ratio_with_independent_precision():
    for value in (F(1, 7), F(960), F(10**250+7, 10**40+3)):
        lower, upper = map(Decimal, core.log_bounds(value))
        with localcontext() as context:
            context.prec = 160
            actual = (Decimal(value.numerator)/Decimal(value.denominator)).ln()
        assert lower <= actual <= upper
        assert len(str(lower)) < 100 and len(str(upper)) < 100


def test_projected_gaps_equal_independent_route_utilities():
    kernel = {core.S: {'DELIVERY': F(3, 5), 'LOST': F(2, 5)},
              core.D: {'DELIVERY': F(1, 2), 'RECOVERY': F(1, 3), 'LOST': F(1, 6)},
              core.R: {'DELIVERY': F(4, 5), 'LOST': F(1, 5)}}
    for query, operating, retry in product(('goal', 'risk'), ('low', 'high'), ('17/20', '19/20')):
        case = dict(operating=operating, retry_cost=retry)
        short, detour = ((F(1, 10), F(1, 20)) if operating == 'low' else (F(3, 25), F(7, 100)))
        weight = 0 if query == 'goal' else 4
        utilities = {'WAIT': F(0), 'SHORT': -short+4*F(3, 5)-weight*F(2, 5),
            'DETOUR_RETURN': -detour+4*F(1, 2)-weight*F(1, 6),
            'DETOUR_RETRY': -detour-F(1, 3)*F(retry)
                +4*(F(1, 2)+F(1, 3)*F(4, 5))-weight*(F(1, 6)+F(1, 3)*F(1, 5))}
        for chosen, other in product(core.POLICIES, repeat=2):
            if chosen == other:
                continue
            projected = core.project_parameters(kernel, core.canonical_family(query, chosen, other))
            assert core.gap(case, query, chosen, other, projected) == utilities[other]-utilities[chosen]


def test_prefix_equivalence_requires_full_mask_and_exact_counts():
    raw = {core.S: {'DELIVERY': 3, 'LOST': 2},
           core.D: {'DELIVERY': 4, 'RECOVERY': 2, 'LOST': 1}}
    prefix = dict(name='inherited_pool', threshold=480, operators=list(raw), counts=raw)
    full = core.project_counts(raw, 'S_D_FULL')
    equivalent = core.compare_prefix_data(full, 'S_D_FULL', [prefix])[0]
    assert equivalent['equivalent_evidence'] and not equivalent['same_region']
    coarsened = core.compare_prefix_data(core.project_counts(raw, 'S_D_DEL'), 'S_D_DEL', [prefix])[0]
    assert coarsened['same_projected_counts'] and not coarsened['same_projection_mask']
    full['S']['DELIVERY'] += 1
    assert not core.compare_prefix_data(full, 'S_D_FULL', [prefix])[0]['equivalent_evidence']


def test_classification_retains_bad_witness_but_does_not_claim_a_certificate():
    row = dict(case={'operating': 'low', 'retry_cost': '17/20'}, query='risk',
        chosen='DETOUR_RETURN', other='DETOUR_RETRY', previously_reported_gap=F(7, 20),
        projected_counts={'D_REC': {'RECOVERY': 0, 'OTHER': 0}, 'R': {'DELIVERY': 0, 'LOST': 0}},
        parameters={'D_REC': {'RECOVERY': F(1, 5), 'OTHER': F(4, 5)},
                    'R': {'DELIVERY': F(33, 40), 'LOST': F(7, 40)}})
    # .2*(8*.825-4-.85) = .35, so the empty-data region admits a bad query gap.
    result = runner.classify(row)
    assert result['gap'] == F(7, 20) and result['membership']['exact_inside']
    assert result['interpretation'] == 'admitted_bad_witness_prevents_this_query_certificate'
    assert 'query_ready' not in result and 'membership' not in row
