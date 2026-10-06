from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
from itertools import permutations, product

from acfqp.science import scoped_union_v228 as core


def _counts(short, detour, retry):
    return {op: dict(zip(core.ALPHABETS[op], values))
            for op, values in zip(core.OPERATORS, (short, detour, retry))}


def _sources():
    return [_counts((24, 8), (20, 8, 4), (20, 12)),
            _counts((30, 2), (28, 2, 2), (28, 4)),
            _counts((16, 16), (16, 8, 8), (12, 20))]


def _exact_branches(state):
    """Enumerate assignments rather than using the producer's marginal DP."""
    member_boxes = [core.union._project_simplex(core.boxes(row, Counter()))
                    for row in state['members']]
    masks = [[i for i, prior in enumerate(state['priors'])
              if core.union._intersection(prior, [box]) is not None]
             for box in member_boxes]
    result = []
    for assignment in product(*masks):
        blocks = []
        for i, prior in enumerate(state['priors']):
            pooled = deepcopy(state['anchor_counts'][i])
            assigned = []
            for j, chosen in enumerate(assignment):
                if chosen == i:
                    core.union._add(pooled, state['members'][j])
                    assigned.append(member_boxes[j])
            block = core.union._intersection(prior, assigned +
                        [core.boxes(pooled, Counter(), core.POOL_THRESHOLD)])
            if block is None:
                break
            blocks.append(block)
        if len(blocks) == len(state['priors']):
            result.append((assignment, blocks))
    return result


def test_source_scope_uses_only_explicit_pool_cs_and_initial_simplex():
    anchors = _sources()
    before = deepcopy(anchors)
    state = core.initial_state(anchors, Counter())
    expected = [core.union._project_simplex(core.boxes(row, Counter(), 1680))
                for row in anchors]
    assert state['priors'] == state['bounds'] == expected
    assert state['members'] == [] and state['changed_op'] is None
    assert anchors == before
    assert core.MEMBER_THRESHOLD == 20160 and core.POOL_THRESHOLD == 1680
    # The legacy module remains unchanged; its intervals are reused explicitly.
    assert core.mixture.MEMBER_THRESHOLD == 14784
    assert core.mixture.POOL_THRESHOLD == 840


def test_outer_dp_contains_every_feasible_full_assignment_in_a_and_b_scopes():
    a = core.initial_state(_sources(), Counter())
    for state in (a, core.branch_state(a['bounds'], 'SHORT_PASS', Counter())):
        member = core.empty()
        member['SHORT_PASS'].update(DELIVERY=8, LOST=8)
        member['DETOUR_PASS'].update(DELIVERY=12, LOST=2, RECOVERY=2)
        core.advance(state, core.empty(), Counter())
        core.advance(state, member, Counter())
        exact = _exact_branches(state)
        assert len(exact) > 1 and not state['no_feasible']
        for assignment, blocks in exact:
            assert all(chosen in state['masks'][j] for j, chosen in enumerate(assignment))
            for i, block in enumerate(blocks):
                for op in core.OPERATORS:
                    for cat, (lo, hi) in block[op]['bounds'].items():
                        outer_lo, outer_hi = state['bounds'][i][op]['bounds'][cat]
                        assert outer_lo <= lo <= hi <= outer_hi


def test_true_changed_branch_retains_b_only_estimates_and_wrong_branch_is_rejected():
    anchors = []
    for category in core.ALPHABETS['DETOUR_PASS']:
        row = core.empty()
        row['SHORT_PASS']['DELIVERY'] = 1024
        row['DETOUR_PASS'][category] = 1024
        row['RECOVERY_RETRY']['LOST'] = 1024
        anchors.append(row)
    a = core.initial_state(anchors, Counter())
    a_before = deepcopy(a)
    member = core.empty()
    member['SHORT_PASS']['LOST'] = 128
    member['DETOUR_PASS']['DELIVERY'] = 128
    member['RECOVERY_RETRY']['LOST'] = 128
    changed = core.branch_state(a['bounds'], 'SHORT_PASS', Counter())
    assert all(row == core.empty() for row in changed['anchor_counts'])
    assert all(op['n'] == 0 and not any(op['counts'].values())
               for prior in changed['priors'] for op in prior.values())
    assert changed['priors'][0]['SHORT_PASS']['bounds']['LOST'] == [F(0), F(1)]
    core.advance(changed, member, Counter())
    assert not changed['no_feasible'] and changed['masks'] == [[0]]
    # The B pool uses 128 failures, never A's 1024 successes.
    expected = core.union._project_simplex(core.boxes(member, Counter(), 1680))
    assert changed['bounds'][0]['SHORT_PASS']['bounds'] == expected['SHORT_PASS']['bounds']
    assert changed['bounds'][0]['SHORT_PASS']['bounds']['LOST'][1] == 1
    for wrong_op in ('DETOUR_PASS', 'RECOVERY_RETRY'):
        wrong = core.branch_state(a['bounds'], wrong_op, Counter())
        core.advance(wrong, member, Counter())
        assert wrong['no_feasible'] and wrong['bounds'] == []
    assert a == a_before
    member['SHORT_PASS']['DELIVERY'] = 1
    assert changed['members'][0]['SHORT_PASS']['DELIVERY'] == 0


def test_candidate_reads_do_not_commit_and_a_return_keeps_its_bank():
    a = core.initial_state(_sources(), Counter())
    a_before = deepcopy(a)
    b = core.branch_state(a['bounds'], 'DETOUR_PASS', Counter())
    b_before = deepcopy(b)
    assert len(core.candidates(b, core.empty(), Counter())) == 3
    assert b == b_before
    member = _counts((8, 8), (4, 4, 8), (8, 8))
    core.advance(b, member, Counter())
    assert a == a_before
    returned = deepcopy(a)
    core.advance(returned, core.empty(), Counter())
    assert returned['anchor_counts'] == a['anchor_counts']
    assert returned['priors'] == a['priors']
    assert returned['members'] == [core.empty()]
    assert a['members'] == [] and b['members'] == [member]


def test_calibrated_repair_and_rebuild_both_contain_complete_assignment_unions():
    a = core.initial_state(_sources(), Counter())
    permutation = (2, 0, 1)
    b_anchors = [deepcopy(_sources()[i]) for i in permutation]
    for row, short in zip(b_anchors, ((8, 24), (24, 8), (16, 16))):
        row['SHORT_PASS'] = dict(zip(core.ALPHABETS['SHORT_PASS'], short))
    repair = core.calibrated_branch(a['bounds'], 'SHORT_PASS', permutation,
                                    b_anchors, Counter())
    rebuild = core.initial_state(b_anchors, Counter())
    assert repair['anchor_counts'] == rebuild['anchor_counts'] == b_anchors
    member = _counts((8, 8), (12, 2, 2), (8, 8))
    for state in (repair, rebuild):
        core.advance(state, core.empty(), Counter())
        core.advance(state, member, Counter())
        branches = _exact_branches(state)
        assert len(branches) > 1 and not state['no_feasible']
        for assignment, blocks in branches:
            assert all(chosen in state['masks'][j] for j, chosen in enumerate(assignment))
            for i, block in enumerate(blocks):
                for op in core.OPERATORS:
                    for cat, (lo, hi) in block[op]['bounds'].items():
                        outer_lo, outer_hi = state['bounds'][i][op]['bounds'][cat]
                        assert outer_lo <= lo <= hi <= outer_hi


def test_all_18_hypotheses_keep_the_true_permutation_and_changed_cs_is_b_only():
    a_anchors = []
    for category in core.ALPHABETS['DETOUR_PASS']:
        row = core.empty()
        row['SHORT_PASS']['DELIVERY'] = 1024
        row['DETOUR_PASS'][category] = 1024
        row['RECOVERY_RETRY']['LOST'] = 1024
        a_anchors.append(row)
    a = core.initial_state(a_anchors, Counter())
    a_before = deepcopy(a)
    true_permutation = (2, 0, 1)
    b_anchors = []
    for i in true_permutation:
        row = core.empty()
        row['SHORT_PASS']['LOST'] = 128
        for op in ('DETOUR_PASS', 'RECOVERY_RETRY'):
            for cat in core.ALPHABETS[op]:
                row[op][cat] = a_anchors[i][op][cat] // 8
        b_anchors.append(row)
    branches = [core.calibrated_branch(a['bounds'], changed_op, permutation,
                                       b_anchors, Counter())
                for changed_op in core.OPERATORS
                for permutation in permutations(range(3))]
    assert len(branches) == 18
    true = next(state for state in branches
                if state['changed_op'] == 'SHORT_PASS'
                and state['permutation'] == true_permutation)
    assert not true['no_feasible']
    assert sum(not state['no_feasible'] for state in branches) == 1
    assert true['anchor_counts'] == b_anchors
    for j, prior in enumerate(true['priors']):
        expected = core.union._project_simplex(core.boxes(b_anchors[j], Counter(), 1680))
        assert prior['SHORT_PASS']['bounds'] == expected['SHORT_PASS']['bounds']
        for op in core.OPERATORS:
            assert prior[op]['counts'] == b_anchors[j][op]
            assert prior[op]['n'] == sum(b_anchors[j][op].values())
            for cat in core.ALPHABETS[op]:
                probability = F(b_anchors[j][op][cat], 128)
                lo, hi = prior[op]['bounds'][cat]
                assert lo <= probability <= hi
    core.advance(true, b_anchors[0], Counter())
    assert not true['no_feasible'] and true['masks'] == [[0]]
    assert a == a_before
    b_anchors[0]['SHORT_PASS']['DELIVERY'] = 1
    assert true['anchor_counts'][0]['SHORT_PASS']['DELIVERY'] == 0
