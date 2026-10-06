"""Check inverse mapping, native counts, original events and one planning call."""
from collections import Counter
from copy import deepcopy
import pytest

from acfqp.science import paid_return_views_v253 as core


def counts(amount):
    return {op: {category: amount+position for position, category in enumerate(core.ALPHABETS[op])} for op in core.OPERATORS}


def snapshot(changed='SHORT_PASS'):
    return dict(life=1,index=58,identity=0,case=dict(context='A',stage='A_RETURN',operating='low',retry_cost='17/20'),
        a_source=counts(10),a_pool=counts(20),b_source=counts(2),b_pool=counts(5),member=counts(3),
        mapped_b_identity=1,interface=dict(changed_operator=changed,b_to_a=[2,0,1]),
        one_way_plan=dict(original='untouched'),retained_fees=dict(total_reference_paid_samples=1000))


@pytest.mark.parametrize('changed',core.OPERATORS)
def test_inverse_map_adds_compatible_native_pool_once_and_keeps_source_separate(changed):
    saved=snapshot(changed)
    before=deepcopy(saved)
    observed,constraints,transfer=core.two_way_evidence(saved)
    eligible=tuple(op for op in core.OPERATORS if op!=changed)
    for op in core.OPERATORS:
        assert observed[op]=={cat:saved['a_pool'][op][cat]+(saved['b_pool'][op][cat] if op in eligible else 0)
            for cat in core.ALPHABETS[op]}
        assert constraints[op][:3]==[
            dict(counts=saved['a_source'][op],threshold=720,event=f'l1/A/pool0/{op}'),
            dict(counts=saved['a_pool'][op],threshold=720,event=f'l1/A/pool0/{op}'),
            dict(counts=saved['member'][op],threshold=8640,event=f'l1/member58/{op}')]
        if op in eligible:
            assert constraints[op][3:]==[
                dict(counts=saved['b_source'][op],threshold=720,event=f'l1/B/pool1/{op}'),
                dict(counts=saved['b_pool'][op],threshold=720,event=f'l1/B/pool1/{op}')]
        else:
            assert len(constraints[op])==3
    assert transfer==dict(a_identity=0,mapped_b_identity=1,operators=eligible,
        transferred_counts={op:saved['b_pool'][op] for op in eligible},
        total_samples=sum(sum(saved['b_pool'][op].values()) for op in eligible))
    assert saved==before
    observed[eligible[0]][next(iter(observed[eligible[0]]))]+=99
    assert saved==before


def test_one_new_plan_uses_unchanged_backend_and_attaches_v243_transfer(monkeypatch):
    saved,cache,work=snapshot(),{},Counter()
    expected=core.two_way_evidence(saved)
    calls=[]
    def plan(constraints,observed,case,actual_cache,actual_work):
        calls.append((constraints,observed,case))
        assert (observed,constraints)==expected[:2]
        assert actual_cache is cache and actual_work is work
        return dict(evidence_counts=observed,joint_constraints=constraints,case=case,new_plan=True)
    monkeypatch.setattr(core.planning,'plan_from_evidence',plan)
    result=core.make_two_way(saved,cache,work)
    assert len(calls)==1 and result['return_transfer']==expected[2]
    assert saved['one_way_plan']==dict(original='untouched')
    assert saved['retained_fees']==dict(total_reference_paid_samples=1000)
