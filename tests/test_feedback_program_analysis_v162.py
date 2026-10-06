"""TRAIN-only feedback selection, paired intervals, and physical feedback replay."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_feedback_program_v162 as audit
from acfqp.science.controlled_predictive_feedback_program_v162 import generate_candidates, run_branch
from acfqp.science.controlled_predictive_program_consolidation_v161 import canonical_word
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

TEMP = Path(__file__).resolve().parents[1]/'reports/v162_runtime_tmp'
ROWS, REPLAY_WORK, GENERATION_WORK = [], Counter(), Counter()
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
        analysis_replay_work=dict(REPLAY_WORK),generation_counts=dict(GENERATION_WORK),native_planner_calls=0,
        scope='Synthetic selection/paired uncertainty and finite real feedback traces.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


def candidate(identifier='P0'):
    return dict(candidate_id=identifier,first_action='LEFT',probe_action='DOWN',
        fixed_suffix=['RIGHT']*3,true_suffix=['DOWN']*3,false_suffix=['RIGHT']*3,
        occurrences=10,condition_counts={'true':5,'false':5})


def screening():
    candidates=[dict(heldout_life=0,query='risk1',candidates=[candidate('P0'),candidate('P1')])]
    roots=[dict(root_id=f'{life}:{slot}',life=life,query='risk1') for life in range(4) for slot in range(4)]
    rows=[]
    for root in roots:
        for suffix in range(4):
            for mode,gain in [('H2',0),('P0_FIXED',9),('P0_FEEDBACK',-1),('P1_FIXED',-2),('P1_FEEDBACK',-1)]:
                if root['life']==0 and mode=='P1_FEEDBACK': gain=999
                rows.append(dict(heldout_life=0,root_id=root['root_id'],suffix=suffix,mode=mode,
                    status='LOST',utility=10+gain,components=[11+gain,1.,0.]))
    return candidates,roots,rows


def test_negative_tie_train_selection_uses_feedback_and_matches_fixed_twin():
    candidates,roots,rows=screening(); cell=audit.select_programs(candidates,roots,list(reversed(rows)))[0]
    assert audit.independent_selection(candidates,roots,rows)==[cell]
    assert cell['complete'] and cell['train_lives']==[1,2,3]
    assert cell['selected_program']['candidate_id']=='P0'
    assert [r['mean'] for r in cell['candidate_scores']]==[-1.,-1.]
    assert cell['candidate_scores'][0]['components']==[-1.,0.,0.]
    assert cell['candidate_scores'][0]['diagnostics']['FIXED-H2']['mean']==9.
    assert cell['candidate_scores'][0]['diagnostics']['FEEDBACK-FIXED']['mean']==-10.
    assert [h['roots'] for h in cell['candidate_scores'][0]['per_history']]==[4]*3


def test_screen_cutoff_or_empty_grammar_blocks_evaluation():
    candidates,roots,rows=screening(); bad=next(r for r in rows if r['root_id']=='1:0' and r['mode']=='P1_FIXED')
    bad.update(status='CUTOFF',utility=None)
    cell=audit.select_programs(candidates,roots,rows)[0]
    assert audit.independent_selection(candidates,roots,rows)==[cell]
    assert not cell['complete'] and cell['selected_program'] is None
    assert cell['candidate_scores'][1]['diagnostics']['FIXED-H2']['components']==[None]*3
    candidates[0]['candidates']=[]
    assert not audit.select_programs(candidates,roots,rows)[0]['complete']


def evaluation():
    roots=[dict(root_id=f'{life}:0',life=life,query='risk1',replica=0,slot=0) for life in range(4)]
    rows=[]
    for root in roots:
        for suffix in range(16):
            for mode,gain in [('H2',0),('FIXED',2),('FEEDBACK',suffix+root['life'])]:
                rows.append(dict(root_id=root['root_id'],suffix=suffix,mode=mode,status='LOST',
                    utility=10+gain,components=[11+gain,1.,0.],module=dict(program=candidate() if mode!='H2' else None,
                    predicate=bool(suffix%2) if mode=='FEEDBACK' else None,
                    prefix_steps=0 if mode=='H2' else 4,attempts=0 if mode=='H2' else 4,
                    exit_reason='baseline' if mode=='H2' else 'budget')))
    return roots,rows


def comparison(summary,contrast='FEEDBACK-FIXED'):
    return next(r for r in summary['comparisons'] if r['query']=='risk1' and r['contrast']==contrast)


def test_pairing_equal_history_intervals_and_feedback_exposure():
    roots,rows=evaluation(); summary=audit.summarize_eval(roots,list(reversed(rows)))
    stat=comparison(summary)['metrics']['utility']; se=math.sqrt((68/3)/(16*4))
    assert stat['mean']==7. and stat['conditional_suffix_se']==pytest.approx(se)
    assert stat['conditional_suffix_ci95']==pytest.approx([7-1.96*se,7+1.96*se])
    assert [h['metrics']['utility']['mean'] for h in comparison(summary)['per_history']]==[5.5,6.5,7.5,8.5]
    assert stat['positive_histories']==4
    assert comparison(summary,'FEEDBACK-H2')['metrics']['utility']['mean']==9.
    diagnostic=next(d for d in summary['program_diagnostics'] if d['query']=='risk1' and d['mode']=='FEEDBACK')
    assert diagnostic['predicate_counts']=={'true':32,'false':32}
    assert diagnostic['roots_with_both_predicates']==4 and diagnostic['selected_suffix_differs_fixed']==32


def test_eval_cutoff_keeps_incomplete_cohort():
    roots,rows=evaluation(); bad=next(r for r in rows if r['mode']=='FEEDBACK')
    bad.update(status='CUTOFF',utility=None)
    item=comparison(audit.summarize_eval(roots,rows))
    assert not item['complete'] and item['roots']==4
    assert item['metrics']['utility']['mean'] is None and item['metrics']['utility']['conditional_suffix_ci95'] is None


class UnusedTeacher:
    def __init__(self): self.counts=Counter()
    def choose(self,*args): raise AssertionError('finite prefix cannot call H2')


def physical_program(board):
    words={name:canonical_word(board,actions) for name,actions in dict(first=['LEFT'],probe=['DOWN'],
        fixed=['RIGHT']*3,true=['DOWN']*3,false=['RIGHT']*3).items()}
    return dict(candidate_id='P0',first_action=words['first'][0],probe_action=words['probe'][0],
        fixed_suffix=list(words['fixed']),true_suffix=list(words['true']),false_suffix=list(words['false']),
        occurrences=10,condition_counts={'true':5,'false':5})


def finite_branch(board,arm='FEEDBACK',steps=2,seed=31,program=None):
    row=run_branch(board,{q:UnusedTeacher() for q in audit.QUERIES},RULE,'risk1',program or physical_program(board),arm,seed,max_steps=steps)
    ROWS.append(row); return row


def replay(row,max_steps=2):
    checks,swipes=audit.replay_branch(row,max_steps);REPLAY_WORK.update(branches=1,swipes=swipes)
    return checks


def test_feedback_replay_probes_observed_spawn_and_detects_event_corruption():
    row=finite_branch([1,1]+[0]*14)
    assert row['module']['predicate'] is not None and all(replay(row).values())
    event=row['choices'][1]['feedback_event']; assert event is not None
    wrong=deepcopy(row);wrong['choices'][1]['feedback_event']['predicate']=not event['predicate']
    assert not replay(wrong)['branch_feedback_observed_state']
    wrong=deepcopy(row);wrong['choices'][1]['feedback_event']['afterstate'][0]+=1
    assert not replay(wrong)['branch_feedback_event']
    wrong=deepcopy(row);wrong['result']['policy_counts']['feedback_probe_checks']+=1
    assert not replay(wrong)['branch_policy_totals']
    wrong=deepcopy(row);wrong['module']['actual_probe']='UP'
    assert not replay(wrong)['branch_program_exit']
    wrong=deepcopy(row);wrong['spawned_ranks'][0]=3
    assert not replay(wrong)['branch_rng']


def test_fixed_pair_shares_first_transition_and_feedback_cost_retained():
    board=[1,1]+[0]*14
    fixed=finite_branch(board,'FIXED');feedback=finite_branch(board)
    assert fixed['actions'][0]==feedback['actions'][0]
    assert fixed['spawned_cells'][0]==feedback['spawned_cells'][0]
    assert fixed['spawned_ranks'][0]==feedback['spawned_ranks'][0]
    assert all(replay(fixed).values()) and all(replay(feedback).values())
    assert feedback['result']['status']=='CUTOFF' and feedback['result']['utility'] is None
    assert feedback['result']['environment_counts']['sampled_transitions']==2
    assert feedback['result']['policy_counts']['feedback_probe_checks']==1
    assert 'feedback_probe_checks' not in fixed['result']['policy_counts']


def test_generation_matches_independent_physics_and_ignores_heldout_before_access():
    rows=[]
    board=[1]+[0]*15
    for life,seed,word in [(1,7,['DOWN','DOWN','RIGHT','UP']),
                          (2,10,['DOWN','DOWN','RIGHT','UP']),
                          (3,1,['DOWN','RIGHT','UP','LEFT'])]:
        program=physical_program(board)
        encoded=canonical_word(board,word)
        program['first_action']=encoded[0]; program['fixed_suffix']=list(encoded[1:])
        row=finite_branch(board,'FIXED',4,seed=seed,program=program)
        assert row['actions']==word
        source=dict(initial_board=row['root_board'],choices=row['choices'],spawned_cells=row['spawned_cells'],
            spawned_ranks=row['spawned_ranks'],actions=row['actions'],result=row['result'],life=life,query='risk1',replica=0,seed=seed)
        rows.append(source)
    rows.append(dict(life=0,query='risk1'))
    rows.append(dict(life=9,query='risk8'))
    actual=generate_candidates(rows,{1:RULE,2:RULE,3:RULE},0,'risk1');GENERATION_WORK.update(actual['counts'])
    independent=audit.generation_cell(rows,0,'risk1')
    REPLAY_WORK.update(generation_swipes=independent['counts']['source_state_reconstructions']+independent['counts']['probe_checks'])
    assert actual==independent
    assert actual['counts']['fragment_windows']==3 and actual['counts']['probe_checks']==3
    assert actual['training_lives']==[1,2,3]
    assert len(actual['candidates'])==1 and actual['candidates'][0]['condition_counts']=={'true':2,'false':1}
    assert actual['candidates'][0]['true_suffix']!=actual['candidates'][0]['false_suffix']
