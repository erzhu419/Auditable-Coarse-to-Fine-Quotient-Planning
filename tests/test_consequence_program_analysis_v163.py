"""Paid-pair mapping arithmetic, matched controls and six-arm uncertainty."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json
import math
from pathlib import Path

import pytest

from scripts import analyze_controlled_predictive_consequence_program_v163 as audit
from acfqp.science.controlled_predictive_consequence_program_v163 import learn_programs
from acfqp.science.controlled_predictive_feedback_program_v162 import run_branch
from acfqp.science.controlled_predictive_program_consolidation_v161 import canonical_word
from acfqp.science.controlled_predictive_relational_dynamics_v69 import LearnedDynamics, RewriteProgram

TEMP=Path(__file__).resolve().parents[1]/'reports/v163_runtime_tmp'
ROWS, REPLAY_WORK, SYMBOLIC_WORK=[],Counter(),Counter()
RULE=LearnedDynamics(RewriteProgram(True,'equal',1,'once','output_value'),
    ((1,Fraction(9,10)),(2,Fraction(1,10))),'uniform')


@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True,exist_ok=True);before=request.session.testsfailed
    yield
    path=TEMP/'analyzer_checks.json';payload=json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__==__name__ for item in request.session.items),
        failures=request.session.testsfailed-before,environment_counts=dict(sum((Counter(r['result']['environment_counts']) for r in ROWS),Counter())),
        new_environment_samples=sum(r['result']['steps'] for r in ROWS),weight_updates=0,
        symbolic_learning_counts=dict(SYMBOLIC_WORK),analysis_replay_work=dict(REPLAY_WORK),native_planner_calls=0,
        scope='Synthetic mapping/selection and six-arm paired intervals; one finite physical feedback branch.'))
    path.write_text(json.dumps(payload,indent=2)+'\n')


def candidate(identifier='P0'):
    return dict(candidate_id=identifier,first_action='LEFT',probe_action='DOWN',fixed_suffix=['RIGHT']*3,
        true_suffix=['DOWN']*3,false_suffix=['RIGHT']*3,occurrences=10,condition_counts={'true':5,'false':5})


def screening(query='risk1'):
    cells=[dict(heldout_life=0,query=query,candidates=[candidate('P0'),candidate('P1')])]
    roots=[dict(root_id=f'{life}:{slot}',life=life,query=query) for life in range(4) for slot in range(4)]
    rows=[]
    for root in roots:
        for suffix in range(4):
            predicate=True if suffix==0 else False if suffix==1 else None
            pairs={'P0':((-4,4) if predicate is True else (4,-4) if predicate is False else (0,0)),
                   'P1':((1,0) if predicate is True else (0,1) if predicate is False else (0,0))}
            values=[('H2',0)]+[(key+'_'+arm,pair[i]) for key,pair in pairs.items() for i,arm in enumerate(('A','B'))]
            for mode,gain in values:
                if root['life']==0 and mode!='H2':gain=999
                components=[11+gain,1.,0.]
                rows.append(dict(heldout_life=0,query=query,root_id=root['root_id'],suffix=suffix,mode=mode,
                    status='LOST',utility=audit.prior.utility(components,query),components=components,module={'predicate':predicate}))
    return cells,roots,rows


def checked_learn(cells,roots,rows):
    result=learn_programs(cells,roots,rows);SYMBOLIC_WORK.update(sum((Counter(c['learning_counts']) for c in result),Counter()))
    independent=audit.independent_selection(cells,roots,list(reversed(rows)))
    assert audit.mobility.arithmetic.equivalent(result,independent)
    return independent[0]


def test_outcomes_invert_source_mapping_and_separate_pair_selection():
    cells,roots,rows=screening();cell=checked_learn(cells,roots,rows)
    assert cell['complete'] and cell['train_lives']==[1,2,3]
    assert cell['candidate_scores'][0]['condition_counts']=={'true':12,'false':12,'none':24}
    assert [m['train_gain'] for m in cell['candidate_scores'][0]['mapping_scores']]==[0.,-2.,2.,0.]
    assert cell['candidate_scores'][0]['learned_mapping']=='BA' and cell['candidate_scores'][0]['global_mapping']=='AA'
    assert cell['programs']['MODAL']['candidate_id']=='P1'
    assert cell['programs']['LEARNED']['candidate_id']=='P0'
    assert cell['programs']['LEARNED']['mapping']=={'true':'B','false':'A'}
    assert cell['programs']['LEARNED']['train_gain']==2.
    assert cell['programs']['MATCH_MODAL']['candidate_id']=='P0' and cell['programs']['MATCH_MODAL']['train_gain']==-2.
    assert cell['programs']['GLOBAL']['candidate_id']=='P0' and cell['programs']['GLOBAL']['mapping']=={'true':'A','false':'A'}
    assert cell['programs']['FIXED']['program']==cells[0]['candidates'][0] and cell['programs']['FIXED']['train_gain'] is None
    assert cell['learning_counts']==dict(weight_updates=0,candidate_pairs_examined=96,mapping_vector_selections=384,
        mapping_root_means=96,mapping_history_means=24,mapping_scores=8,learned_branch_tables=1)


def test_sparse_predicate_uses_full_roster_weight_not_conditional_normalization():
    cells,roots,rows=screening();cells[0]['candidates']=cells[0]['candidates'][:1]
    for row in rows:
        if row['mode'].startswith('P1'):continue
        keep=row['root_id']=='1:0' and row['suffix'] in (0,1)
        if not keep:
            row['module']['predicate']=None;row['components']=[11.,1.,0.];row['utility']=10.
    cell=checked_learn(cells,roots,rows)
    assert cell['complete'] and cell['candidate_scores'][0]['condition_counts']=={'true':1,'false':1,'none':46}
    learned=cell['candidate_scores'][0]['mapping_scores'][2]
    assert learned['train_gain']==pytest.approx(8/48)
    assert [h['train_gain'] for h in learned['history_gains']]==[.5,0.,0.]


def test_negative_ties_keep_first_map_and_candidate():
    cells,roots,rows=screening()
    for row in rows:
        if row['mode']!='H2':row.update(components=[10.,1.,0.],utility=9.)
    cell=checked_learn(cells,roots,rows)
    assert cell['programs']['LEARNED']['candidate_id']=='P0'
    assert cell['programs']['LEARNED']['mapping']=={'true':'A','false':'A'}
    assert cell['programs']['LEARNED']['train_gain']==-1.
    assert cell['programs']['MODAL']['candidate_id']=='P0'


@pytest.mark.parametrize('corruption,issue',[('cutoff','nonterminal_pair'),('predicate','predicate_mismatch'),('none_vector','none_outcome_mismatch')])
def test_pair_corruption_blocks_all_evaluation(corruption,issue):
    cells,roots,rows=screening();bad=next(r for r in rows if r['root_id']=='1:0' and r['mode']=='P0_B' and r['suffix']==2)
    if corruption=='cutoff':bad.update(status='CUTOFF',utility=None)
    elif corruption=='predicate':bad['module']['predicate']=True
    else:bad.update(components=[99.,1.,0.],utility=98.)
    cell=checked_learn(cells,roots,rows)
    assert not cell['complete'] and cell['programs']=={}
    assert issue in cell['candidate_scores'][0]['issues'] and not cell['candidate_scores'][0]['mapping_scores']


def evaluation():
    roots=[dict(root_id=f'{life}:0',life=life,query='risk1',replica=0,slot=0) for life in range(4)]
    rows=[]
    for root in roots:
        for suffix in range(16):
            gains={'H2':0,'MODAL':2,'LEARNED':suffix+root['life'],'MATCH_MODAL':3,'GLOBAL':4,'FIXED':1}
            for mode,gain in gains.items():
                rows.append(dict(root_id=root['root_id'],suffix=suffix,mode=mode,status='LOST',utility=10+gain,
                    components=[11+gain,1.,0.],module=dict(program=candidate() if mode!='H2' else None,
                    predicate=bool(suffix%2) if mode not in ('H2','FIXED') else None,
                    prefix_steps=0 if mode=='H2' else 4,attempts=0 if mode=='H2' else 4,
                    exit_reason='baseline' if mode=='H2' else 'budget')))
    return roots,rows


def comparison(summary,contrast='LEARNED-MODAL'):
    return next(r for r in summary['comparisons'] if r['query']=='risk1' and r['contrast']==contrast)


def test_six_arm_pairing_history_weight_and_cutoff_retention():
    roots,rows=evaluation();summary=audit.summarize_eval(roots,list(reversed(rows)));stat=comparison(summary)['metrics']['utility']
    se=math.sqrt((68/3)/(16*4))
    assert stat['mean']==7. and stat['conditional_suffix_ci95']==pytest.approx([7-1.96*se,7+1.96*se])
    assert [h['metrics']['utility']['mean'] for h in comparison(summary)['per_history']]==[5.5,6.5,7.5,8.5]
    expected={'LEARNED-MATCH_MODAL':6.,'LEARNED-GLOBAL':5.,'LEARNED-H2':9.,'MATCH_MODAL-MODAL':1.,'LEARNED-FIXED':8.}
    assert {name:comparison(summary,name)['metrics']['utility']['mean'] for name in expected}==expected
    diagnostic=next(d for d in summary['program_diagnostics'] if d['query']=='risk1' and d['mode']=='LEARNED')
    assert diagnostic['roots_with_both_predicates']==4 and diagnostic['selected_suffix_differs_fixed']==32
    bad=next(r for r in rows if r['mode']=='LEARNED');bad.update(status='CUTOFF',utility=None)
    incomplete=comparison(audit.summarize_eval(roots,rows))
    assert not incomplete['complete'] and incomplete['roots']==4 and incomplete['metrics']['utility']['mean'] is None


class UnusedTeacher:
    def __init__(self):self.counts=Counter()
    def choose(self,*args):raise AssertionError('finite prefix cannot call H2')


def test_existing_physical_feedback_replay_and_mapping_binding():
    board=[1,1]+[0]*14;original=candidate()
    original['first_action']=canonical_word(board,['LEFT'])[0];original['probe_action']=canonical_word(board,['DOWN'])[0]
    original['true_suffix']=list(canonical_word(board,['DOWN']*3));original['false_suffix']=list(canonical_word(board,['RIGHT']*3))
    original['fixed_suffix']=list(original['false_suffix'])
    program=audit.mapped_program(original,'BB')
    row=run_branch(board,{q:UnusedTeacher() for q in audit.QUERIES},RULE,'risk1',program,'FEEDBACK',31,max_steps=2)
    ROWS.append(row);checks,swipes=audit.replay_branch(row,2);REPLAY_WORK.update(branches=1,swipes=swipes)
    assert all(checks.values()) and row['module']['actual_true_suffix']==row['module']['actual_false_suffix']
    wrong=deepcopy(row);wrong['choices'][1]['feedback_event']['predicate']=not wrong['choices'][1]['feedback_event']['predicate']
    checks,swipes=audit.replay_branch(wrong,2);REPLAY_WORK.update(branches=1,swipes=swipes)
    assert not checks['branch_feedback_event'] and row['result']['environment_counts']['sampled_transitions']==2
