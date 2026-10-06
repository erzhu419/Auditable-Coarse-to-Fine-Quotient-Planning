from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import pytest
from acfqp.science import strong_reference_v224 as core
from scripts.run_conditioned_mechanisms_v205 import exact_json

ROOT = Path(__file__).resolve().parents[1]


def saved_form(value):
    return json.loads(json.dumps(exact_json(value)))


@pytest.fixture(scope='module')
def retained():
    libraries = json.loads((ROOT/'reports/persistent_evidence_v221/libraries.json').read_text())
    rows = json.loads((ROOT/'reports/persistent_evidence_v221/records.json').read_text())
    return libraries, [r for r in rows if r['arm']=='FROZEN']


def test_original_replays_actual_strong_baseline_plans_choices_and_fallback(retained):
    libraries, rows = retained
    cases = [next(r for r in rows if r['life']==0 and r['index']==3),
             next(r for r in rows if r['stop']=='query_set'),
             next(r for r in rows if r['fallback'])]
    for row in cases:
        source = libraries[row['life']]['anchors']; member = core.empty(); work = Counter()
        state = core.prepare(source, 'ORIGINAL', work); before = deepcopy(state)
        plan = core.make_plan(member, source, row['case'], 'ORIGINAL', work, state)
        assert saved_form(plan)==row['initial_plan']
        for batch in row['batches']:
            choice = core.choose(member, source, row['case'], 'ORIGINAL', plan,
                                 batch['spent']-16, work, state)
            assert saved_form(choice)==batch['choice']
            for cat,k in batch['increments'].items():
                member[batch['operator']][cat] += k
            plan = core.make_plan(member, source, row['case'], 'ORIGINAL', work, state)
            assert saved_form(plan)==batch['plan']
        assert core.choose(member, source, row['case'], 'ORIGINAL', plan,row['spent'],work,state) is None
        if row['fallback']:
            plan = core.make_plan(member, source, row['case'], 'ORIGINAL', work, state, force_member=True)
        assert saved_form(plan)==row['terminal_plan'] and state==before
        assert core.advance(state, member, source, 'ORIGINAL', work) is None


def test_source_endpoints_are_original_for_every_arm_and_beta_does_not_leak(retained):
    libraries,_ = retained; source = libraries[0]['anchors']
    old_beta = core.evidence.BETA
    original = [core.evidence.boxes(anchor,Counter()) for anchor in source]
    states = {arm:core.prepare(source,arm,Counter()) for arm in core.ARMS}
    assert all(state['bounds']==original for state in states.values())
    problem = core.raw_problem(source,[core.empty()],Counter())
    assert problem['source_boxes']==original
    assert core.SOURCE_BETA==old_beta and core.MEMBER_BETA>old_beta
    core.make_plan(core.empty(),source,dict(operating='low',retry_cost='17/20'),
                   'FIXED',Counter(),states['FIXED'])
    assert core.evidence.BETA==old_beta


def test_all_terminal_evidence_is_retained_after_planning_without_point_pooling(retained):
    libraries,rows = retained; source = libraries[4]['anchors']
    failed = next(r for r in rows if r['life']==4 and not r['certified'])
    ambiguous = next(r for r in rows if r['life']==4 and r['stop']=='query_set')
    state = core.prepare(source,'UNION',Counter()); work = Counter()
    initial_source = deepcopy(source)
    for row in (failed, ambiguous):
        before = deepcopy(state)
        terminal = core.make_plan(row['member'],source,row['case'],'UNION',work,state)
        saved = deepcopy(terminal)
        assert state==before
        pre = core.make_plan(core.empty(),source,row['case'],'UNION',work,state)
        core.advance(state,row['member'],source,'UNION',work)
        post = core.make_plan(core.empty(),source,row['case'],'UNION',work,state)
        assert terminal==saved
        assert pre['candidates']==post['candidates']==[0,1,2]
        assert pre['pure_vectors']==post['pure_vectors'] and pre['query_proxy']==post['query_proxy']
    assert state['members']==[failed['member'],ambiguous['member']]
    assert work['union_retained_targets']==2 and work['union_retained_samples']==failed['spent']+ambiguous['spent']
    assert work['controlled_samples']==0 and source==initial_source
    assert not state['no_feasible']


def test_fixed_and_union_are_matched_except_for_terminal_accumulation(retained):
    libraries,rows = retained; source = libraries[0]['anchors']
    row = next(r for r in rows if r['life']==0 and r['index']==3)
    states = {a:core.prepare(source,a,Counter()) for a in ('FIXED','UNION')}
    plans = {a:core.make_plan(row['member'],source,row['case'],a,Counter(),states[a]) for a in states}
    assert plans['FIXED']==plans['UNION']
    for arm in states:
        assert core.choose(row['member'],source,row['case'],arm,plans[arm],row['spent'],Counter(),states[arm]) == core.prior.choose(
            row['member'],source,row['case'],'SET',plans[arm],row['spent'],Counter())
    before = deepcopy(states['FIXED'])
    assert core.advance(states['FIXED'],row['member'],source,'FIXED',Counter()) is None
    assert states['FIXED']==before
