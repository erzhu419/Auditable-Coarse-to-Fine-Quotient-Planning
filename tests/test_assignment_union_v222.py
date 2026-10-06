from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path

from acfqp.science import assignment_union_v222 as core
from scripts import analyze_assignment_union_v222 as independent


ROOT = Path(__file__).resolve().parents[1]
CASE = dict(id='unit_03', operating='low', retry_cost='17/20')


def retained(life):
    libraries = json.loads((ROOT/'reports/persistent_evidence_v221/libraries.json').read_text())
    rows = json.loads((ROOT/'reports/persistent_evidence_v221/records.json').read_text())
    return libraries[life]['anchors'], [r for r in rows if r['life'] == life and r['arm'] == 'FROZEN']


def test_subset_extrema_keeps_all_fixed_n_endpoints_of_the_full_subset_family():
    # Different subsets reach the same n with very different k; retaining a
    # representative count would wrongly shrink an uncertainty envelope.
    optional = [(0,16), (16,16), (8,32), (0,0), (11,16)]
    values = {}
    for bits in product((0,1), repeat=len(optional)):
        n = 96+sum(take*pair[1] for take,pair in zip(bits,optional))
        k = 73+sum(take*pair[0] for take,pair in zip(bits,optional))
        values.setdefault(n, []).append(k)
    actual = core.subset_extrema(73,96,optional,Counter())
    assert actual == {n:(min(v),max(v)) for n,v in values.items()}
    for n,ks in values.items():
        a,b = actual[n]
        envelope = (core.interval(a,n,Counter(),core.POOL_BETA)[0],
                    core.interval(b,n,Counter(),core.POOL_BETA)[1])
        assert all(envelope[0] <= core.interval(k,n,Counter(),core.POOL_BETA)[0]
                   <= core.interval(k,n,Counter(),core.POOL_BETA)[1] <= envelope[1] for k in ks)


def test_retained_complete_union_matches_branches_and_outer_retains_every_feasible_assignment():
    # Life3 has genuinely ambiguous query-ready members; life0 supplies a
    # different, nearly identified assignment structure.
    for life,prefix in ((0,4),(3,8)):
        anchors, rows = retained(life)
        members = [r['member'] for r in rows[:prefix]]
        problem = core.raw_problem(anchors,members,Counter())
        expected_problem = independent.raw_problem(anchors,members)
        assert problem == expected_problem
        exact = core.exact_union(problem,anchors,members,Counter())
        expected = independent.exact_union(expected_problem,anchors,members)
        assert exact == {k:v for k,v in expected.items() if k != 'admitted'}
        outer = core.outer_union(problem,anchors,members,Counter())
        assert independent.contains(outer['bounds'],exact['bounds'])
        assert all(all(index in outer['masks'][j] for j,index in enumerate(a))
                   for a in expected['admitted'])
        assert outer == independent.outer_union(expected_problem,anchors,members)


def test_failed_and_ambiguous_observations_are_retained_without_source_mutation_or_doublecount():
    anchors, rows = retained(4)
    failure = next(r for r in rows if not r['certified'])
    ambiguous = next(r for r in rows if r['stop'] == 'query_set')
    members = [failure['member'],ambiguous['member']]
    initial = deepcopy((anchors,members))
    problem = core.raw_problem(anchors,members,Counter())
    assert len(problem['member_boxes']) == 2
    assert [problem['member_boxes'][j][op]['counts'] for j in range(2) for op in core.OPERATORS] == [
        members[j][op] for j in range(2) for op in core.OPERATORS]
    assert sum(sum(problem['member_boxes'][0][op]['counts'].values()) for op in core.OPERATORS) == failure['spent'] == 384
    assert any(len(mask)>1 for mask in problem['masks'])
    exact = core.exact_union(problem,anchors,members,Counter())
    expected = independent.exact_union(independent.raw_problem(anchors,members),anchors,members)
    assert exact == {k:v for k,v in expected.items() if k != 'admitted'}
    assert (anchors,members) == initial
    # With no target observations, no pool gain or extra source replication is
    # available. An unobserved zero-count operator also retains [0,1].
    for constructor in (core.exact_union,core.outer_union):
        empty_problem = core.raw_problem(anchors,[],Counter())
        no_target = constructor(empty_problem,anchors,[],Counter())
        for i in range(3):
            for op in core.OPERATORS:
                assert no_target['bounds'][i][op]['bounds'] == empty_problem['source_boxes'][i][op]['bounds']
                assert no_target['bounds'][i][op]['counts'] == anchors[i][op]
        assert constructor(core.raw_problem([core.empty()]*3,[core.empty()],Counter()),
                           [core.empty()]*3,[core.empty()],Counter())['bounds'][0]['DETOUR_PASS']['bounds'] == {
                               cat:[F(0),F(1)] for cat in core.ALPHABETS['DETOUR_PASS']}


def test_only_safety_bounds_change_while_original_point_models_and_query_choices_stay_fixed():
    anchors, _ = retained(0)
    source = core.raw_problem(anchors,[],Counter())['source_boxes']
    narrower = deepcopy(source)
    for i,anchor in enumerate(anchors):
        probabilities = core.evidence.posterior(anchor)
        for op in core.OPERATORS:
            for cat in core.ALPHABETS[op]:
                p = probabilities[op][cat]
                narrower[i][op]['bounds'][cat] = [p,p]
    member = core.empty()
    before = core.plan(member,anchors,CASE,source,Counter())
    after = core.plan(member,anchors,CASE,narrower,Counter())
    assert before['candidates'] == after['candidates'] == [0,1,2]
    assert before['pure_vectors'] == after['pure_vectors']
    assert before['query_proxy'] == after['query_proxy']
    assert core.queries(before) == core.queries(after)
    assert before['risks'] != after['risks']
    assert before['goals_lower'] != after['goals_lower']
    assert source == core.raw_problem(anchors,[],Counter())['source_boxes']
