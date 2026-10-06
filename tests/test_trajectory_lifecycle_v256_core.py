"""Comparison-specific reuse without mixing point kernels or execution data."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import pytest

from acfqp.science import trajectory_lifecycle_v256 as core

S,D,R = core.OPERATORS
CASE = dict(context='A',stage='A_RETURN',operating='low',retry_cost='17/20')


def append(state,context,identity,short='DELIVERY',detour='DELIVERY',retry=None):
    outcomes={S:short,D:detour,R:retry}
    for operator,outcome in outcomes.items():
        if outcome is not None:
            increments=dict.fromkeys(core.ALPHABETS[operator],0)
            increments[outcome]=1
            core.observe_row(state,context,identity,operator,increments)
    record=dict(round_id=len(state['round_log'])+1,context=context,identity=identity,phase='SOURCE',outcomes=outcomes)
    core.observe_round(state,record)
    return record


def banks(arm,changed):
    work=Counter()
    state=core.prepare(0,arm,work)
    append(state,'A',0)
    append(state,'A',1,'DELIVERY','RECOVERY','LOST')
    append(state,'A',2)
    core.freeze_sources(state,'A')
    core.begin_b(state,changed,[1,2,0],work)
    append(state,'B',0,'LOST','DELIVERY')
    append(state,'B',1)
    append(state,'B',2)
    core.freeze_sources(state,'B')
    return state,work


@pytest.mark.parametrize('changed,chosen,other',[(S,'WAIT','DETOUR_RETURN'),(D,'WAIT','SHORT'),(R,'SHORT','DETOUR_RETURN')])
def test_only_whole_required_row_compatible_rounds_transfer_in_both_directions(changed,chosen,other):
    state,_=banks('TRAJECTORY_REUSE',changed)
    spec=core.trajectory.direct.score_spec('goal',chosen,other,'17/20')
    assert changed not in spec.required_rows
    assert [r['round_id'] for r in core.admitted_rounds(state,'A',1,spec)]==[2,4]
    assert [r['round_id'] for r in core.admitted_rounds(state,'B',0,spec)]==[2,4]
    retry=core.trajectory.direct.score_spec('goal','SHORT','DETOUR_RETRY','17/20')
    assert [r['round_id'] for r in core.admitted_rounds(state,'A',1,retry)]==[2]
    assert [r['round_id'] for r in core.admitted_rounds(state,'B',0,retry)]==[4]
    append(state,'A',1)
    assert [r['round_id'] for r in core.admitted_rounds(state,'A',1,spec)]==[2,4,7]
    assert state['b']['pools'][0][S]['LOST']==1  # no inherited A written into native B


def test_rebuild_keeps_native_A_return_and_B_history_only():
    state,_=banks('TRAJECTORY_REBUILD',R)
    spec=core.trajectory.direct.score_spec('goal','SHORT','DETOUR_RETURN','17/20')
    assert [r['round_id'] for r in core.admitted_rounds(state,'A',1,spec)]==[2]
    assert [r['round_id'] for r in core.admitted_rounds(state,'B',0,spec)]==[4]
    append(state,'A',1)
    assert [r['round_id'] for r in core.admitted_rounds(state,'A',1,spec)]==[2,7]


def test_point_vectors_are_native_while_each_comparison_has_its_own_legal_prefix():
    state,work=banks('TRAJECTORY_REUSE',R)
    plan=core.query_plan(state,CASE,1,{},work)
    pure=core.trajectory.pure_vectors(state['trajectory']['A'][1],CASE)
    assert plan['query_pure_vectors']==pure and plan['queries']==core.trajectory.point_queries(pure)
    assert plan['native_round_ids']==[2] and plan['native_complete_rounds']==1
    goal=plan['query_evidence']['queries']['goal']
    assert goal['policy']=='SHORT'
    byother={c['other']:c for c in goal['comparisons']}
    assert byother['DETOUR_RETURN']['admitted_round_ids']==[2,4]
    assert byother['DETOUR_RETURN']['admitted_by_context']==dict(A=1,B=1)
    assert byother['DETOUR_RETRY']['admitted_round_ids']==[2]
    assert plan['query_evidence']['threshold']==4320
    for query,decision in plan['query_evidence']['queries'].items():
        assert plan['query_certificates'][query]['policy']==decision['policy']
        assert plan['query_certificates'][query]['certified']==decision['certified']
        assert plan['query_certificates'][query]['regret_upper']==(0 if query=='reward' else F(1,20) if decision['certified'] else 20)
        for policy,marker in plan['query_gap_bounds'][query].items():
            assert marker==int(policy in plan['query_blockers'][query])


def test_execution_rows_reuse_native_pools_once_while_query_rounds_ignore_member_and_feedback():
    reuse,_=banks('TRAJECTORY_REUSE',R)
    rebuild,_=banks('TRAJECTORY_REBUILD',R)
    before=deepcopy(reuse['trajectory'])
    for state in (reuse,rebuild):
        core.observe_row(state,'B',0,S,dict(DELIVERY=16,LOST=0))
    assert reuse['trajectory']==before and len(reuse['round_log'])==6
    reused=core.row_views.point_counts(CASE,reuse,1)
    native=core.row_views.point_counts(CASE,rebuild,1)
    assert sum(reused[S].values())==18 and sum(native[S].values())==1
    assert sum(reused[R].values())==sum(native[R].values())==1
    assert sum(reuse['b']['pools'][0][S].values())==17
    assert sum(reuse['a_at_switch']['pools'][1][S].values())==1


def test_execution_posterior_and_mix_are_separate_from_native_joint_query_policies():
    state,work=banks('TRAJECTORY_REBUILD',R)
    core.observe_row(state,'A',1,S,dict(DELIVERY=0,LOST=16))
    plan=core.make_plan(core.empty(),CASE,state,1,54,{},work)
    assert plan['pure_vectors']==core.native.mechanics.vectors(CASE,plan['posterior'])
    assert plan['query_pure_vectors']['SHORT'][2]==1
    assert plan['pure_vectors']['SHORT'][2]!=plan['query_pure_vectors']['SHORT'][2]
    assert plan['risk_upper']<=F(1,20)
    assert plan['query_evidence']['threshold']==4320 and plan['native_round_ids']==[2]
    assert core.ready(plan)==((plan['utility_lower']>=2 or plan['goal_impossible']) and plan['query_ready'])
