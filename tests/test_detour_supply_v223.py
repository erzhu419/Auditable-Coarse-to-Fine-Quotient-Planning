from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from acfqp.science import detour_supply_v223 as core
from acfqp.science import assignment_union_v222 as union

ROOT = Path(__file__).resolve().parents[1]
CASE = dict(id='unit_03', operating='low', retry_cost='17/20')


def anchors(life=0):
    return json.loads((ROOT/'reports/persistent_evidence_v221/libraries.json').read_text())[life]['anchors']


def test_detour_first_batch_is_paid_inside_the_same_cap_and_then_uses_set_rule():
    source, member = anchors(), core.empty()
    for arm in core.ARMS:
        work = Counter(); state = core.prepare(source, arm, work)
        plan = core.make_plan(member, source, CASE, arm, work, state)
        choice = core.choose(member, source, CASE, arm, plan, 0, work, state)
        if arm.endswith('DETOUR'):
            assert choice == dict(operator='DETOUR_PASS', reason='paid_detour_pilot', scope='TARGET', source_index=None)
        else:
            assert choice == core.prior.choose(member, source, CASE, 'SET', plan, 0, Counter())
        current = deepcopy(member); current['DETOUR_PASS']['DELIVERY'] = 16
        after = core.make_plan(current, source, CASE, arm, work, state)
        assert core.choose(current, source, CASE, arm, after, 16, work, state) == core.prior.choose(
            current, source, CASE, 'SET', after, 16, Counter())
        capped = deepcopy(current); capped['SHORT_PASS']['DELIVERY'] = 368
        final = core.make_plan(capped, source, CASE, arm, work, state)
        assert core.choose(capped, source, CASE, arm, final, 384, work, state) is None
        assert work['controlled_samples'] == 0


def test_terminal_update_retains_failed_and_ambiguous_targets_without_source_replication():
    source = anchors(4)
    old = json.loads((ROOT/'reports/persistent_evidence_v221/records.json').read_text())
    targets = [r for r in old if r['life']==4 and r['arm']=='FROZEN']
    members = [next(r['member'] for r in targets if not r['certified']),
               next(r['member'] for r in targets if r['stop']=='query_set')]
    before = deepcopy((source, members)); work = Counter()
    state = core.prepare(source, 'UNION_DETOUR', work)
    for prefix, member in enumerate(members, start=1):
        event = core.advance(state, member, source, 'UNION_DETOUR', work)
        assert state['members'] == members[:prefix] and len(state['masks']) == prefix
        problem = union.raw_problem(source, members[:prefix], Counter(), raw_beta=core.RAW_BETA)
        exact = union.exact_union(problem, source, members[:prefix], Counter(), pool_beta=core.POOL_BETA)
        assert not event['no_feasible'] and not exact['no_feasible']
        for i in range(3):
            for op in core.OPERATORS:
                assert state['bounds'][i][op]['counts'] == source[i][op]
                for cat in core.ALPHABETS[op]:
                    lo, hi = event['bounds'][i][op]['bounds'][cat]
                    a, b = exact['bounds'][i][op]['bounds'][cat]
                    assert lo <= a <= b <= hi
    assert work['union_retained_samples'] == sum(sum(row.values()) for m in members for row in m.values())
    assert work['union_retained_targets'] == 2 and work['controlled_samples'] == 0
    assert (source, members) == before


def test_current_plan_does_not_commit_or_use_cumulative_predictive_counts():
    source, work = anchors(), Counter()
    state = core.prepare(source, 'UNION_SET', work)
    member = dict(SHORT_PASS=dict(DELIVERY=130, LOST=78),
                  DETOUR_PASS=dict(DELIVERY=0, LOST=0, RECOVERY=0),
                  RECOVERY_RETRY=dict(DELIVERY=20, LOST=28))
    untouched = deepcopy(state)
    current = core.make_plan(member, source, CASE, 'UNION_SET', work, state)
    assert state == untouched
    saved_plan = deepcopy(current)
    before = core.make_plan(core.empty(), source, CASE, 'UNION_SET', work, state)
    core.advance(state, member, source, 'UNION_SET', work)
    after = core.make_plan(core.empty(), source, CASE, 'UNION_SET', work, state)
    assert current == saved_plan and len(state['members']) == 1
    assert before['candidates'] == after['candidates'] == [0,1,2]
    assert before['pure_vectors'] == after['pure_vectors']
    assert before['query_proxy'] == after['query_proxy']
    fallback = core.make_plan(member, source, CASE, 'UNION_SET', work, state, force_member=True)
    assert fallback['mode']=='member' and not fallback['candidates']
    assert fallback['pure_vectors']==core.vectors(CASE, union.evidence.posterior(member))


def test_all_arms_share_calibration_and_fixed_library_remains_unchanged():
    source, member = anchors(), core.empty()
    states = {a:core.prepare(source, a, Counter()) for a in core.ARMS}
    baseline = core.make_plan(member, source, CASE, 'FIXED_SET', Counter(), states['FIXED_SET'])
    for arm, state in states.items():
        assert core.make_plan(member, source, CASE, arm, Counter(), state)==baseline
    initial = deepcopy(states['FIXED_DETOUR'])
    observed = core.empty(); observed['DETOUR_PASS']['DELIVERY']=16
    assert core.advance(states['FIXED_DETOUR'], observed, source, 'FIXED_DETOUR', Counter()) is None
    assert states['FIXED_DETOUR']==initial
    raw = union.raw_problem(source, [], Counter(), raw_beta=core.RAW_BETA)['source_boxes']
    assert initial['bounds']==raw
    assert core.RAW_BETA>union.RAW_BETA and core.POOL_BETA>union.POOL_BETA
