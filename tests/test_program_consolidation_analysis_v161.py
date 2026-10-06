"""Train-only selection, paired uncertainty, and independent program replay."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_program_consolidation_v161 as audit
from acfqp.science.controlled_predictive_program_consolidation_v161 import canonical_word, run_branch
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

TEMP = Path(__file__).resolve().parents[1]/'reports/v161_runtime_tmp'
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
        scope='Synthetic train-only selection and fixed-root arithmetic; finite real program-prefix traces.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


def screening():
    candidates = [dict(heldout_life=0,query='risk1',candidates=[dict(candidate_id=f'P{i}',word=['LEFT']*4,occurrences=10-i) for i in range(4)])]
    roots = [dict(root_id=f'{life}:{slot}',life=life,query='risk1') for life in range(4) for slot in range(4)]
    rows = []
    for root in roots:
        for suffix in range(4):
            for mode,gain in [('H2',0),('P0',-3),('P1',-1),('P2',-1),('P3',-2)]:
                if root['life']==0 and mode=='P0': gain=999
                rows.append(dict(heldout_life=0,root_id=root['root_id'],suffix=suffix,mode=mode,
                    status='LOST',utility=10+gain,components=[11+gain,1.,0.]))
    return candidates,roots,rows


def test_train_selection_excludes_heldout_and_keeps_negative_winner():
    candidates,roots,rows = screening(); cell = audit.select_programs(candidates,roots,list(reversed(rows)))[0]
    assert audit.independent_selection(candidates,roots,rows)==[cell]
    assert cell['complete'] and cell['train_lives']==[1,2,3]
    assert cell['frequency_program']['candidate_id']=='P0'
    assert cell['selected_program']['candidate_id']=='P1'
    assert [r['mean'] for r in cell['candidate_scores']]==[-3.,-1.,-1.,-2.]
    assert cell['candidate_scores'][1]['components']==[-1.,0.,0.]
    assert [h['roots'] for h in cell['candidate_scores'][1]['per_history']]==[4]*3


def test_screen_cutoff_blocks_freeze_instead_of_filtering():
    candidates,roots,rows = screening()
    bad=next(r for r in rows if r['root_id']=='1:0' and r['mode']=='P3')
    bad.update(status='CUTOFF',utility=None)
    cell = audit.select_programs(candidates,roots,rows)[0]
    assert audit.independent_selection(candidates,roots,rows)==[cell]
    assert not cell['complete'] and cell['selected_program'] is None
    assert cell['candidate_scores'][3]['mean'] is None
    assert cell['candidate_scores'][3]['components']==[None]*3


def evaluation():
    roots=[dict(root_id=f'{life}:0',life=life,query='risk1',replica=0,slot=0) for life in range(4)]
    rows=[]
    for root in roots:
        for suffix in range(16):
            for mode,gain in [('H2',0),('FREQ',2),('BEST',suffix+root['life'])]:
                rows.append(dict(root_id=root['root_id'],suffix=suffix,mode=mode,status='LOST',
                    utility=10+gain,components=[11+gain,1.,0.],module=dict(prefix_steps=0 if mode=='H2' else 4,
                    attempts=0 if mode=='H2' else 4,exit_reason='baseline' if mode=='H2' else 'budget')))
    return roots,rows


def primary(summary,contrast='BEST-H2'):
    return next(r for r in summary['comparisons'] if r['query']=='risk1' and r['contrast']==contrast)


def test_pairing_and_equal_history_uncertainty():
    roots,rows=evaluation(); summary=audit.summarize_eval(roots,list(reversed(rows)))
    stat=primary(summary)['metrics']['utility']; se=math.sqrt((68/3)/(16*4))
    assert stat['mean']==9. and stat['conditional_suffix_se']==pytest.approx(se)
    assert stat['conditional_suffix_ci95']==pytest.approx([9-1.96*se,9+1.96*se])
    assert [h['metrics']['utility']['mean'] for h in primary(summary)['per_history']]==[7.5,8.5,9.5,10.5]
    assert stat['positive_histories']==4
    assert primary(summary,'BEST-FREQ')['metrics']['utility']['mean']==7.
    assert primary(summary,'FREQ-H2')['metrics']['utility']['mean']==2.
    assert primary(summary)['metrics']['failure']['mean']==0.


def test_eval_cutoff_retains_incomplete_cohort():
    roots,rows=evaluation(); bad=next(r for r in rows if r['mode']=='BEST')
    bad.update(status='CUTOFF',utility=None)
    item=primary(audit.summarize_eval(roots,rows))
    assert not item['complete'] and item['roots']==4
    assert item['metrics']['utility']['mean'] is None
    assert item['metrics']['utility']['conditional_suffix_ci95'] is None


class UnusedTeacher:
    def __init__(self): self.counts=Counter()
    def choose(self,*args): raise AssertionError('terminal program prefix cannot call H2')


def finite_branch(board,max_steps=2000):
    program=canonical_word(board,['LEFT']*4)
    row=run_branch(board,{q:UnusedTeacher() for q in audit.QUERIES},RULE,'risk1',program,31,max_steps=max_steps)
    ROWS.append(row); return row


def replay(row,max_steps=2000):
    checks,swipes=audit.replay_branch(row,max_steps); REPLAY_WORK.update(branches=1,swipes=swipes)
    return checks


def test_real_terminal_program_and_auditor_corruption_detection():
    row=finite_branch([10,10]+[0]*14)
    assert row['result']['status']=='WON' and all(replay(row).values())
    wrong=deepcopy(row); wrong['spawned_ranks'][0]=3
    assert not replay(wrong)['branch_rng']
    wrong=deepcopy(row); wrong['choices'][0]['program_action_attempt']['index']=2
    assert not replay(wrong)['branch_program_attempt']
    wrong=deepcopy(row); wrong['module']['transform']='identity'
    assert not replay(wrong)['branch_program_exit']
    wrong=deepcopy(row); wrong['result']['program_setup_counts']['program_board_transforms']+=1
    assert not replay(wrong)['branch_program_orientation']
    wrong=deepcopy(row); wrong['result']['environment_counts']['sampled_transitions']+=1
    assert not replay(wrong)['branch_environment']


def test_cutoff_prefix_preserves_physical_cost():
    row=finite_branch([1,1]+[0]*14,1)
    assert row['result']['status']=='CUTOFF' and row['result']['utility'] is None
    assert row['module']['exit_reason']=='cutoff' and row['result']['environment_counts']['sampled_transitions']==1
    assert all(replay(row,1).values())
