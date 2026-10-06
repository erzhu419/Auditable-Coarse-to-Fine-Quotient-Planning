"""Paired uncertainty, incomplete cohorts, and independent physical replay."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_module_mobility_v160 as audit
from acfqp.science.controlled_predictive_module_mobility_v160 import run_branch
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

TEMP = Path(__file__).resolve().parents[1]/'reports/v160_runtime_tmp'
ROWS, REPLAY_WORK = [], Counter()
RULE = LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
    ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform')


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True); before = request.session.testsfailed
    yield
    path = TEMP/'analyzer_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__==__name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        environment_counts=dict(sum((Counter(r['result']['environment_counts']) for r in ROWS),Counter())),
        new_environment_samples=sum(r['result']['steps'] for r in ROWS),new_training_updates=0,
        analysis_replay_work=dict(REPLAY_WORK),native_planner_calls=0,
        scope='Synthetic paired arithmetic and finite real mobility-prefix traces; no source games or learned fitting.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


def synthetic():
    roots = [dict(root_id=f'{life}:risk1:H2:0',life=life,query='risk1',source_method='H2',slot=0,
                  board=[1,1]+[0]*14) for life in range(4)]
    outcomes = []
    for root in roots:
        for suffix in range(32):
            for mode, gain in (('H2',0),('OTHER8',2),('MOBILITY',suffix+root['life'])):
                outcomes.append(dict(root_id=root['root_id'],suffix=suffix,mode=mode,
                    status='LOST',utility=10+gain,components=[11+gain,1.,0.],
                    module=dict(initial_empty=14,target_empty=16,prefix_steps=0 if mode=='H2' else 8,
                        exit_empty=14,completion=False,exit_reason='baseline' if mode=='H2' else 'budget')))
    return roots,outcomes


def primary(summary,contrast='MOBILITY-H2'):
    return next(row for row in summary['comparisons'] if row['query']=='risk1' and
        row['source_method']=='ALL' and row['stratum']=='ALL' and row['contrast']==contrast)


def test_pairing_variance_and_history_weights():
    roots,outcomes = synthetic(); summary = audit.summarize(roots,list(reversed(outcomes)))
    row = primary(summary); stat = row['metrics']['utility']
    assert row['complete'] and stat['mean']==17.
    assert stat['conditional_suffix_se']==pytest.approx(math.sqrt(88/(32*4)))
    assert stat['conditional_suffix_ci95']==pytest.approx([17-1.96*math.sqrt(88/128),17+1.96*math.sqrt(88/128)])
    assert [h['metrics']['utility']['mean'] for h in row['per_history']]==[15.5,16.5,17.5,18.5]
    assert stat['positive_histories']==4
    assert row['metrics']['failure']['mean']==row['metrics']['success']['mean']==0.
    assert primary(summary,'MOBILITY-OTHER8')['metrics']['utility']['mean']==15.
    assert primary(summary,'OTHER8-H2')['metrics']['utility']['mean']==2.


def test_cutoff_does_not_turn_into_filtered_terminal_mean():
    roots,outcomes = synthetic(); bad = next(r for r in outcomes if r['mode']=='MOBILITY')
    bad.update(status='CUTOFF',utility=None)
    row = primary(audit.summarize(roots,outcomes))
    assert not row['complete'] and row['metrics']['utility']['mean'] is None
    assert row['metrics']['utility']['conditional_suffix_ci95'] is None
    assert row['roots']==4 and len(row['per_history'])==4


def test_missing_stratum_history_stays_incomplete():
    roots,outcomes = synthetic(); roots[0]['board']=[1]*15+[0]
    summary = audit.summarize(roots,outcomes)
    row = next(r for r in summary['comparisons'] if r['query']=='risk1' and
               r['source_method']=='ALL' and r['stratum']=='TIGHT' and r['contrast']=='MOBILITY-H2')
    assert row['roots']==1 and not row['complete']
    assert row['metrics']['utility']['mean'] is None
    assert [h['roots'] for h in row['per_history']]==[1,0,0,0]


def test_equal_history_weight_with_unequal_root_counts():
    stats = [audit.root_pool([audit.moments([life]*32)]*(life+1)) for life in range(4)]
    result = audit.history_pool(stats)
    assert result['mean']==1.5 and result['conditional_suffix_se']==0.


class UnusedTeacher:
    def __init__(self): self.counts = Counter()
    def choose(self,*args): raise AssertionError('terminal mobility prefix must not call a teacher')


def finite_branch(board,max_steps=2000):
    row = run_branch(board,{q:UnusedTeacher() for q in audit.QUERIES},RULE,'risk1','MOBILITY',31,max_steps=max_steps)
    ROWS.append(row)
    return row


def replay(row,max_steps=2000):
    checks,swipes = audit.replay_branch(row,max_steps)
    REPLAY_WORK.update(branches=1,swipes=swipes)
    return checks


def test_terminal_mobility_replay_and_corruptions():
    row = finite_branch([10,10]+[0]*14)
    assert row['result']['status']=='WON' and row['module']['exit_reason']=='terminal'
    assert all(replay(row).values())
    wrong = deepcopy(row); wrong['spawned_ranks'][0]=3
    assert not replay(wrong)['branch_rng']
    wrong = deepcopy(row); wrong['choices'][0]['expected_postspawn_empty']+=1
    assert not replay(wrong)['branch_mobility_choice']
    wrong = deepcopy(row); wrong['module']['exit_reason']='target'
    assert not replay(wrong)['branch_module_exit']
    wrong = deepcopy(row); wrong['choices'][0]['phase']='continuation'
    assert not replay(wrong)['branch_phases']
    wrong = deepcopy(row); wrong['result']['environment_counts']['sampled_transitions']+=1
    assert not replay(wrong)['branch_environment']


def test_interrupted_prefix_costs_retained():
    row = finite_branch([1,1]+[0]*14,1)
    assert row['result']['status']=='CUTOFF' and row['module']['exit_reason']=='cutoff'
    assert row['result']['utility'] is None and row['result']['steps']==1
    assert all(replay(row,1).values())
